#!/usr/bin/env python3
"""Verify the published Gamma profiles against an independent node oracle.

The oracle deliberately does not call the production candidate-search helper.
It reads the JSON fixture contract itself, enumerates comparison nodes (or the
specified bilinear sampling lattice), and compares both point statuses and
summary metrics with the public ``calculate_gamma`` result.

This is an engineering regression/evidence tool for synthetic data.  It is not
vendor commissioning evidence and must not be used to claim clinical readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

from rt_connect_api.services.gamma_engine import (  # noqa: E402
    ENGINE_VERSION,
    GammaConfiguration,
    MeasurementDataset,
    calculate_gamma,
)


@dataclass(frozen=True)
class OracleDataset:
    """Minimal dataset parsed independently from the production loader."""

    dataset_id: str
    values: np.ndarray
    spacing_mm: tuple[float, ...]
    origin_mm: tuple[float, ...]


def _mapping(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return cast(dict[str, object], value)


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _independent_load(path: Path) -> OracleDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = _mapping(payload, "root")
    if root.get("schema_version") != "gamma.measurement.v1":
        raise ValueError("unsupported fixture schema")
    dataset_id = root.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ValueError("dataset_id is required")

    units = _mapping(root.get("units"), "units")
    dose_unit = units.get("dose")
    if dose_unit not in {"GY", "CGY"} or units.get("position") != "mm":
        raise ValueError("fixture units must explicitly declare GY/CGY and mm")
    dose_scale = 1.0 if dose_unit == "GY" else 0.01

    grid = _mapping(root.get("grid"), "grid")
    raw_shape = grid.get("shape")
    if not isinstance(raw_shape, list) or len(raw_shape) not in {2, 3}:
        raise ValueError("grid.shape must be 2D or 3D")
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in raw_shape):
        raise ValueError("grid.shape must contain positive integers")
    shape = tuple(int(item) for item in raw_shape)

    raw_spacing = grid.get("spacing_mm")
    raw_origin = grid.get("origin_mm", [0.0] * len(shape))
    if not isinstance(raw_spacing, list) or not isinstance(raw_origin, list):
        raise ValueError("grid spacing/origin must be arrays")
    if len(raw_spacing) != len(shape) or len(raw_origin) != len(shape):
        raise ValueError("grid spacing/origin dimensionality mismatch")
    spacing = tuple(_finite(item, f"spacing_mm[{index}]") for index, item in enumerate(raw_spacing))
    origin = tuple(_finite(item, f"origin_mm[{index}]") for index, item in enumerate(raw_origin))
    if any(item <= 0 for item in spacing):
        raise ValueError("grid spacing must be positive")

    values = _mapping(root.get("values"), "values")
    inline = values.get("inline")
    expected = math.prod(shape)
    if not isinstance(inline, list) or len(inline) != expected:
        raise ValueError("values.inline does not match grid.shape")
    numeric = np.asarray(
        [_finite(item, f"values.inline[{index}]") for index, item in enumerate(inline)],
        dtype=np.float64,
    ).reshape(shape)
    numeric *= dose_scale
    if np.any(numeric < 0):
        raise ValueError("dose values must be non-negative")
    return OracleDataset(dataset_id, numeric, spacing, origin)


def _to_engine(dataset: OracleDataset) -> MeasurementDataset:
    return MeasurementDataset(
        dataset_id=dataset.dataset_id,
        values=np.asarray(dataset.values, dtype=np.float64),
        spacing_mm=dataset.spacing_mm,
        origin_mm=dataset.origin_mm,
        units={"dose": "GY", "position": "mm"},
    )


def _position(dataset: OracleDataset, indices: tuple[int, ...]) -> tuple[float, ...]:
    return tuple(
        dataset.origin_mm[axis] + indices[axis] * dataset.spacing_mm[axis]
        for axis in range(dataset.values.ndim)
    )


def _sample_linear(dataset: OracleDataset, position: tuple[float, ...]) -> float | None:
    coordinates = [
        (position[axis] - dataset.origin_mm[axis]) / dataset.spacing_mm[axis]
        for axis in range(dataset.values.ndim)
    ]
    if any(
        coordinate < 0 or coordinate > dataset.values.shape[axis] - 1
        for axis, coordinate in enumerate(coordinates)
    ):
        return None
    lower = [int(math.floor(coordinate)) for coordinate in coordinates]
    upper = [min(index + 1, dataset.values.shape[axis] - 1) for axis, index in enumerate(lower)]
    weights = [
        coordinate - index for coordinate, index in zip(coordinates, lower, strict=True)
    ]
    total = 0.0
    for corner in itertools.product((0, 1), repeat=dataset.values.ndim):
        indices = tuple(
            upper[axis] if corner[axis] else lower[axis]
            for axis in range(dataset.values.ndim)
        )
        weight = 1.0
        for axis, bit in enumerate(corner):
            weight *= weights[axis] if bit else 1.0 - weights[axis]
        total += float(dataset.values[indices]) * weight
    return total


def _dose_scale(
    reference_value: float,
    reference_max: float,
    configuration: GammaConfiguration,
) -> float:
    base = reference_max if configuration.normalization == "GLOBAL" else abs(reference_value)
    if configuration.dose_difference_mode == "ABSOLUTE":
        if configuration.absolute_dose_difference_gy is None:
            raise ValueError("absolute dose difference is required")
        return configuration.absolute_dose_difference_gy
    return base * configuration.dose_difference_percent / 100.0


def _gamma(reference_value: float, evaluation_value: float, distance: float, scale: float, dta: float) -> float:
    return math.sqrt(((evaluation_value - reference_value) / scale) ** 2 + (distance / dta) ** 2)


def _independent_oracle(
    reference: OracleDataset,
    evaluation: OracleDataset,
    configuration: GammaConfiguration,
) -> dict[str, Any]:
    if reference.values.ndim != evaluation.values.ndim:
        raise ValueError("dataset dimensionality mismatch")
    reference_max = float(np.max(reference.values))
    if reference_max <= 0:
        raise ValueError("reference maximum must be positive")
    threshold = reference_max * configuration.dose_threshold_percent / 100.0
    search_radius = configuration.distance_to_agreement_mm * configuration.max_gamma
    gamma_values: list[float] = []
    statuses: dict[tuple[int, ...], str] = {}
    excluded = 0
    no_candidate = 0
    censored = 0

    for raw_indices in np.ndindex(reference.values.shape):
        reference_indices = tuple(int(index) for index in raw_indices)
        reference_value = float(reference.values[reference_indices])
        if reference_value < threshold:
            excluded += 1
            continue
        reference_position = _position(reference, reference_indices)
        scale = _dose_scale(reference_value, reference_max, configuration)
        candidates: list[float] = []
        if configuration.interpolation == "GRID":
            candidate_indices = np.ndindex(evaluation.values.shape)
            for raw_evaluation_indices in candidate_indices:
                evaluation_indices = tuple(int(index) for index in raw_evaluation_indices)
                evaluation_position = _position(evaluation, evaluation_indices)
                distance = math.sqrt(
                    sum(
                        (evaluation_position[axis] - reference_position[axis]) ** 2
                        for axis in range(reference.values.ndim)
                    )
                )
                if distance <= search_radius:
                    candidates.append(
                        _gamma(
                            reference_value,
                            float(evaluation.values[evaluation_indices]),
                            distance,
                            scale,
                            configuration.distance_to_agreement_mm,
                        )
                    )
        else:
            step = min(*reference.spacing_mm, *evaluation.spacing_mm) / 2.0
            offsets = np.arange(-search_radius, search_radius + step / 2.0, step)
            for offset_tuple in itertools.product(offsets, repeat=reference.values.ndim):
                distance = math.sqrt(sum(float(offset) ** 2 for offset in offset_tuple))
                if distance > search_radius:
                    continue
                position = tuple(
                    reference_position[axis] + float(offset_tuple[axis])
                    for axis in range(reference.values.ndim)
                )
                sampled = _sample_linear(evaluation, position)
                if sampled is not None:
                    candidates.append(
                        _gamma(
                            reference_value,
                            sampled,
                            distance,
                            scale,
                            configuration.distance_to_agreement_mm,
                        )
                    )

        if not candidates:
            no_candidate += 1
            statuses[reference_indices] = "NO_CANDIDATE"
            continue
        minimum = min(candidates)
        if minimum > configuration.max_gamma:
            censored += 1
            statuses[reference_indices] = "CENSORED"
            continue
        gamma_values.append(minimum)
        statuses[reference_indices] = "PASS" if minimum <= 1.0 else "FAIL"

    denominator = len(gamma_values) + censored
    invalid_coverage = no_candidate if configuration.coverage_policy == "FULL_ROI" else 0
    coverage_excluded = no_candidate if configuration.coverage_policy == "OVERLAP_ONLY" else 0
    passing = sum(value <= 1.0 for value in gamma_values)
    return {
        "selected_points": reference.values.size - excluded,
        "excluded_points": excluded,
        "evaluated_points": len(gamma_values),
        "passing_points": passing,
        "nonpassing_points": denominator - passing,
        "coverage_excluded_points": coverage_excluded,
        "invalid_coverage_points": invalid_coverage,
        "no_candidate_points": no_candidate,
        "censored_points": censored,
        "pass_rate_percent": (
            None
            if invalid_coverage or denominator == 0
            else passing / denominator * 100.0
        ),
        "statuses": statuses,
        "gamma_values": gamma_values,
    }


def _configuration(dimensionality: str, **overrides: Any) -> GammaConfiguration:
    values: dict[str, Any] = {
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
    return GammaConfiguration(**values)


def _serialise_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in summary.items() if key not in {"statuses", "gamma_values"}}


def _compare_case(
    case_id: str,
    reference: OracleDataset,
    evaluation: OracleDataset,
    configuration: GammaConfiguration,
    *,
    reference_path: str,
    evaluation_path: str,
) -> dict[str, Any]:
    expected = _independent_oracle(reference, evaluation, configuration)
    actual = calculate_gamma(_to_engine(reference), _to_engine(evaluation), configuration)
    actual_metrics = cast(dict[str, Any], actual["metrics"])
    scalar_keys = (
        "selected_points",
        "excluded_points",
        "evaluated_points",
        "passing_points",
        "nonpassing_points",
        "coverage_excluded_points",
        "invalid_coverage_points",
        "no_candidate_points",
        "censored_points",
    )
    mismatches: list[str] = []
    for key in scalar_keys:
        if actual_metrics.get(key) != expected[key]:
            mismatches.append(f"{key}: expected={expected[key]!r} observed={actual_metrics.get(key)!r}")
    actual_pass_rate = actual_metrics.get("pass_rate_percent")
    expected_pass_rate = expected["pass_rate_percent"]
    if actual_pass_rate is None or expected_pass_rate is None:
        if actual_pass_rate != expected_pass_rate:
            mismatches.append(
                f"pass_rate_percent: expected={expected_pass_rate!r} observed={actual_pass_rate!r}"
            )
    elif not math.isclose(float(actual_pass_rate), float(expected_pass_rate), rel_tol=0.0, abs_tol=1e-12):
        mismatches.append(
            f"pass_rate_percent: expected={expected_pass_rate!r} observed={actual_pass_rate!r}"
        )

    actual_statuses = {
        tuple(int(index) for index in item["index"]): str(item["status"])
        for item in cast(list[dict[str, Any]], actual["gamma_map"])
    }
    if actual_statuses != expected["statuses"]:
        mismatches.append("point status map differs")
    actual_gamma_values = [
        float(item["gamma"])
        for item in cast(list[dict[str, Any]], actual["gamma_map"])
        if item.get("gamma") is not None
    ]
    if len(actual_gamma_values) != len(expected["gamma_values"]):
        mismatches.append("finite gamma value count differs")
    else:
        for index, (observed, expected_value) in enumerate(
            zip(actual_gamma_values, expected["gamma_values"], strict=True)
        ):
            if not math.isclose(observed, expected_value, rel_tol=0.0, abs_tol=1e-12):
                mismatches.append(
                    f"gamma[{index}]: expected={expected_value!r} observed={observed!r}"
                )
                break

    return {
        "case_id": case_id,
        "reference": reference_path,
        "evaluation": evaluation_path,
        "configuration": {
            "dimensionality": configuration.dimensionality,
            "dose_difference_percent": configuration.dose_difference_percent,
            "dose_difference_mode": configuration.dose_difference_mode,
            "absolute_dose_difference_gy": configuration.absolute_dose_difference_gy,
            "distance_to_agreement_mm": configuration.distance_to_agreement_mm,
            "dose_threshold_percent": configuration.dose_threshold_percent,
            "normalization": configuration.normalization,
            "interpolation": configuration.interpolation,
            "coverage_policy": configuration.coverage_policy,
            "max_gamma": configuration.max_gamma,
        },
        "expected": _serialise_summary(expected),
        "observed": {
            **_serialise_summary(actual_metrics),
            "overall_status": actual["overall_status"],
        },
        "mismatches": mismatches,
        "result": "PASS" if not mismatches else "FAIL",
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_case(
    case_id: str,
    reference_path: Path,
    evaluation_path: Path,
    configuration: GammaConfiguration,
) -> tuple[str, OracleDataset, OracleDataset, GammaConfiguration, str, str]:
    return (
        case_id,
        _independent_load(reference_path),
        _independent_load(evaluation_path),
        configuration,
        str(reference_path.relative_to(REPO_ROOT)),
        str(evaluation_path.relative_to(REPO_ROOT)),
    )


def _in_memory_case(
    case_id: str,
    reference_values: list[float],
    evaluation_values: list[float],
    shape: tuple[int, ...],
    configuration: GammaConfiguration,
    *,
    evaluation_origin: tuple[float, ...] | None = None,
    evaluation_shape: tuple[int, ...] | None = None,
) -> tuple[str, OracleDataset, OracleDataset, GammaConfiguration, str, str]:
    reference = OracleDataset(
        f"{case_id}-reference",
        np.asarray(reference_values, dtype=np.float64).reshape(shape),
        (1.0,) * len(shape),
        (0.0,) * len(shape),
    )
    evaluation = OracleDataset(
        f"{case_id}-evaluation",
        np.asarray(evaluation_values, dtype=np.float64).reshape(evaluation_shape or shape),
        (1.0,) * len(evaluation_shape or shape),
        evaluation_origin or (0.0,) * len(evaluation_shape or shape),
    )
    return case_id, reference, evaluation, configuration, "synthetic:inline", "synthetic:inline"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "docs" / "evidence" / "p8-independent-gamma-oracle.json",
    )
    args = parser.parse_args()
    fixture_dir = REPO_ROOT / "docs" / "fixtures"
    reference_2d = fixture_dir / "gamma-reference-v1-smoke.json"
    evaluation_2d = fixture_dir / "gamma-evaluation-v1-smoke.json"
    fixture_3d = fixture_dir / "gamma-measurement-3d-v1-smoke.json"

    cases = [
        _fixture_case(
            "2d-global-relative-grid",
            reference_2d,
            evaluation_2d,
            _configuration("2D", distance_to_agreement_mm=3.0),
        ),
        _fixture_case(
            "3d-global-relative-grid",
            fixture_3d,
            fixture_3d,
            _configuration("3D", distance_to_agreement_mm=1.5),
        ),
        _fixture_case(
            "3d-local-absolute-grid",
            fixture_3d,
            fixture_3d,
            _configuration(
                "3D",
                normalization="LOCAL",
                dose_difference_mode="ABSOLUTE",
                absolute_dose_difference_gy=0.1,
                distance_to_agreement_mm=1.5,
            ),
        ),
        _in_memory_case(
            "2d-overlap-only-grid",
            [1.0, 1.0],
            [1.0],
            (1, 2),
            _configuration(
                "2D",
                distance_to_agreement_mm=0.4,
                coverage_policy="OVERLAP_ONLY",
            ),
            evaluation_shape=(1, 1),
        ),
        _in_memory_case(
            "2d-censored-global-grid",
            [1.0],
            [1.06],
            (1, 1),
            _configuration("2D", max_gamma=1.0, distance_to_agreement_mm=3.0),
        ),
        _in_memory_case(
            "2d-bilinear-global-grid",
            [1.0, 2.0, 3.0, 4.0],
            [1.0, 2.0, 3.0, 4.0],
            (2, 2),
            _configuration("2D", interpolation="BILINEAR", distance_to_agreement_mm=1.5),
            evaluation_origin=(0.25, 0.25),
        ),
    ]

    case_results: list[dict[str, Any]] = []
    for case_id, reference, evaluation, configuration, reference_path, evaluation_path in cases:
        try:
            case_results.append(
                _compare_case(
                    case_id,
                    reference,
                    evaluation,
                    configuration,
                    reference_path=reference_path,
                    evaluation_path=evaluation_path,
                )
            )
        except Exception as exc:  # noqa: BLE001 - evidence must record a closed failure.
            case_results.append(
                {
                    "case_id": case_id,
                    "reference": reference_path,
                    "evaluation": evaluation_path,
                    "result": "FAIL",
                    "mismatches": [f"oracle execution failed: {type(exc).__name__}: {exc}"],
                }
            )

    fixture_hashes = {
        str(path.relative_to(REPO_ROOT)): _sha256(path)
        for path in (reference_2d, evaluation_2d, fixture_3d)
    }
    failed = [item for item in case_results if item["result"] != "PASS"]
    evidence = {
        "schema_version": "rt-connect.p8-independent-gamma-oracle.v1",
        "captured_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "verification_level": "LOCAL_INDEPENDENT_ORACLE",
        "engine_version_observed": ENGINE_VERSION,
        "data_boundary": "Synthetic JSON fixtures and in-memory synthetic arrays only; no patient, PACS or treatment data.",
        "oracle_boundary": "Expected values are generated by this independent exhaustive node/sampling implementation before comparing the public calculate_gamma result; production candidate-search helpers are not imported.",
        "fixture_sha256": fixture_hashes,
        "case_count": len(case_results),
        "failed_case_count": len(failed),
        "passed": not failed,
        "cases": case_results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": not failed, "case_count": len(case_results), "failed_case_count": len(failed), "output": str(args.output)}, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
