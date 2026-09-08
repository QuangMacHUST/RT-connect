"""Independent known-answer checks for the published Gamma node-search contract.

This oracle intentionally does not call the production candidate-search helper.  It
enumerates every comparison grid node directly, which makes it useful for catching
regressions where the optimized search bounds or denominator change together with
the implementation under test.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from rt_connect_api.services.gamma_engine import (
    GammaConfiguration,
    MeasurementDataset,
    calculate_gamma,
)


def _position(dataset: MeasurementDataset, indices: tuple[int, ...]) -> tuple[float, ...]:
    return tuple(
        dataset.origin_mm[axis] + indices[axis] * dataset.spacing_mm[axis]
        for axis in range(dataset.values.ndim)
    )


def _dose_scale(
    reference_value: float,
    reference_max: float,
    configuration: GammaConfiguration,
) -> float:
    base = reference_max if configuration.normalization == "GLOBAL" else abs(reference_value)
    if configuration.dose_difference_mode == "ABSOLUTE":
        assert configuration.absolute_dose_difference_gy is not None
        return configuration.absolute_dose_difference_gy
    return base * configuration.dose_difference_percent / 100.0


def _independent_node_oracle(
    reference: MeasurementDataset,
    evaluation: MeasurementDataset,
    configuration: GammaConfiguration,
) -> dict[str, object]:
    """Return only the point-level facts needed to compare the engine result."""

    reference_max = float(np.max(reference.values))
    threshold = reference_max * configuration.dose_threshold_percent / 100.0
    selected = 0
    excluded = 0
    no_candidate = 0
    censored = 0
    gamma_values: list[float] = []
    statuses: dict[tuple[int, ...], str] = {}

    for raw_indices in np.ndindex(reference.values.shape):
        indices = tuple(int(index) for index in raw_indices)
        reference_value = float(reference.values[indices])
        if reference_value < threshold:
            excluded += 1
            continue
        selected += 1
        reference_position = _position(reference, indices)
        scale = _dose_scale(reference_value, reference_max, configuration)
        candidates: list[float] = []
        for evaluation_raw_indices in np.ndindex(evaluation.values.shape):
            evaluation_indices = tuple(int(index) for index in evaluation_raw_indices)
            evaluation_position = _position(evaluation, evaluation_indices)
            distance = math.sqrt(
                sum(
                    (evaluation_position[axis] - reference_position[axis]) ** 2
                    for axis in range(reference.values.ndim)
                )
            )
            if distance > configuration.distance_to_agreement_mm * configuration.max_gamma:
                continue
            evaluation_value = float(evaluation.values[evaluation_indices])
            candidates.append(
                math.sqrt(
                    ((evaluation_value - reference_value) / scale) ** 2
                    + (distance / configuration.distance_to_agreement_mm) ** 2
                )
            )

        if not candidates:
            no_candidate += 1
            statuses[indices] = "NO_CANDIDATE"
            continue
        gamma = min(candidates)
        if gamma > configuration.max_gamma:
            censored += 1
            statuses[indices] = "CENSORED"
            continue
        gamma_values.append(gamma)
        statuses[indices] = "PASS" if gamma <= 1.0 else "FAIL"

    denominator = len(gamma_values) + censored
    invalid_coverage = no_candidate if configuration.coverage_policy == "FULL_ROI" else 0
    coverage_excluded = no_candidate if configuration.coverage_policy == "OVERLAP_ONLY" else 0
    pass_rate = (
        None
        if invalid_coverage
        else (
            sum(value <= 1.0 for value in gamma_values) / denominator * 100.0
            if denominator
            else None
        )
    )
    return {
        "selected_points": selected,
        "excluded_points": excluded,
        "evaluated_points": len(gamma_values),
        "passing_points": sum(value <= 1.0 for value in gamma_values),
        "nonpassing_points": denominator - sum(value <= 1.0 for value in gamma_values),
        "coverage_excluded_points": coverage_excluded,
        "invalid_coverage_points": invalid_coverage,
        "no_candidate_points": no_candidate,
        "censored_points": censored,
        "pass_rate_percent": pass_rate,
        "statuses": statuses,
    }


def _configuration(dimensionality: str, **overrides: object) -> GammaConfiguration:
    values: dict[str, object] = {
        "dimensionality": dimensionality,
        "dose_difference_percent": 3.0,
        "dose_difference_mode": "RELATIVE",
        "absolute_dose_difference_gy": None,
        "distance_to_agreement_mm": 1.5,
        "dose_threshold_percent": 0.0,
        "normalization": "GLOBAL",
        "interpolation": "GRID",
        "pass_rate_threshold_percent": 95.0,
        "histogram_bins": 8,
        "coverage_policy": "FULL_ROI",
        "max_gamma": 2.0,
    }
    values.update(overrides)
    return GammaConfiguration(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("shape", "dimensionality"),
    [((3, 3), "2D"), ((2, 2, 2), "3D")],
)
def test_engine_matches_exhaustive_independent_node_oracle(
    shape: tuple[int, ...], dimensionality: str
) -> None:
    values = np.arange(1, math.prod(shape) + 1, dtype=np.float64).reshape(shape)
    evaluation_values = values * 1.01
    reference = MeasurementDataset(
        dataset_id="oracle-reference",
        values=values,
        spacing_mm=(1.0,) * len(shape),
        origin_mm=(0.0,) * len(shape),
        units={"dose": "GY", "position": "mm"},
    )
    evaluation = MeasurementDataset(
        dataset_id="oracle-evaluation",
        values=evaluation_values,
        spacing_mm=(1.0,) * len(shape),
        origin_mm=(0.25,) * len(shape),
        units={"dose": "GY", "position": "mm"},
    )
    configuration = _configuration(dimensionality)

    expected = _independent_node_oracle(reference, evaluation, configuration)
    actual = calculate_gamma(reference, evaluation, configuration)
    metrics = actual["metrics"]

    for key in (
        "selected_points",
        "excluded_points",
        "evaluated_points",
        "passing_points",
        "nonpassing_points",
        "coverage_excluded_points",
        "invalid_coverage_points",
        "no_candidate_points",
        "censored_points",
    ):
        assert metrics[key] == expected[key]
    assert metrics["pass_rate_percent"] == pytest.approx(expected["pass_rate_percent"])

    actual_statuses = {
        tuple(int(item) for item in point["index"]): point["status"]
        for point in actual["gamma_map"]
    }
    assert actual_statuses == expected["statuses"]


def test_independent_oracle_preserves_full_roi_and_censored_denominator() -> None:
    reference = MeasurementDataset(
        dataset_id="oracle-reference-edge",
        values=np.ones((1, 3), dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
    )
    evaluation = MeasurementDataset(
        dataset_id="oracle-evaluation-edge",
        values=np.asarray([[1.0, 1.20]], dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
    )
    configuration = _configuration("2D", max_gamma=1.0, distance_to_agreement_mm=0.4)
    expected = _independent_node_oracle(reference, evaluation, configuration)
    actual = calculate_gamma(reference, evaluation, configuration)
    metrics = actual["metrics"]

    assert expected["censored_points"] == 1
    assert expected["no_candidate_points"] == 1
    assert actual["overall_status"] == "INVALID"
    assert metrics["pass_rate_percent"] is None
    assert metrics["censored_points"] == expected["censored_points"]
    assert metrics["invalid_coverage_points"] == expected["invalid_coverage_points"]
