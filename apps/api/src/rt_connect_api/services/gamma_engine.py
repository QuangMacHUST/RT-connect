"""Deterministic 2D Gamma engine for the first P8 measurement contract.

This module deliberately accepts only the validated ``gamma.measurement.v1`` JSON
contract. It does not infer units, reshape ambiguous arrays, or read DICOM pixel
data. Those adapters can be added later without changing the persisted Gamma
configuration/result contract.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
from numpy.typing import NDArray

ENGINE_VERSION = "gamma-2d-p8.1"
FloatArray = NDArray[np.float64]


class GammaEngineError(ValueError):
    """A deterministic input or configuration failure with a stable error code."""

    def __init__(self, code: str, message: str, details: list[dict[str, object]] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


@dataclass(frozen=True)
class GammaConfiguration:
    """Configuration snapshot used by one Gamma run."""

    dimensionality: str
    dose_difference_percent: float
    dose_difference_mode: str
    absolute_dose_difference_gy: float | None
    distance_to_agreement_mm: float
    dose_threshold_percent: float
    normalization: str
    interpolation: str
    pass_rate_threshold_percent: float
    histogram_bins: int


@dataclass(frozen=True)
class MeasurementDataset:
    dataset_id: str
    values: FloatArray
    spacing_mm: tuple[float, float]
    origin_mm: tuple[float, float]
    units: dict[str, str]


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise GammaEngineError("GAMMA_INPUT_INVALID", f"{field} must be an object.")
    return cast(Mapping[str, object], value)


def _finite_float(value: object, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GammaEngineError("GAMMA_INPUT_INVALID", f"{field} must be numeric.")
    converted = float(value)
    if not math.isfinite(converted) or (positive and converted <= 0):
        raise GammaEngineError("GAMMA_INPUT_INVALID", f"{field} must be finite and valid.")
    return converted


def _pair(value: object, field: str, *, positive: bool) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise GammaEngineError("GAMMA_GRID_INVALID", f"{field} must contain exactly two values.")
    first = _finite_float(value[0], f"{field}[0]", positive=positive)
    second = _finite_float(value[1], f"{field}[1]", positive=positive)
    return first, second


def load_measurement(path: Path) -> MeasurementDataset:
    """Load one unambiguous 2D measurement dataset from a JSON artifact."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GammaEngineError(
            "GAMMA_INPUT_UNREADABLE", "The measurement artifact is not readable UTF-8 JSON."
        ) from exc
    root = _mapping(payload, "measurement root")
    if root.get("schema_version") != "gamma.measurement.v1":
        raise GammaEngineError(
            "GAMMA_SCHEMA_UNSUPPORTED", "Only gamma.measurement.v1 is supported by the P8 engine."
        )
    if root.get("data_type") != "dose":
        raise GammaEngineError("GAMMA_DATA_TYPE_UNSUPPORTED", "Gamma input data_type must be dose.")
    dataset_id = root.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise GammaEngineError("GAMMA_DATASET_ID_MISSING", "Gamma input dataset_id is required.")

    units = _mapping(root.get("units"), "units")
    dose_unit = units.get("dose")
    position_unit = units.get("position")
    if dose_unit != "GY" or position_unit != "mm":
        raise GammaEngineError(
            "GAMMA_UNITS_UNSUPPORTED",
            "P8 requires dose=GY and position=mm; units are never inferred.",
        )

    grid = _mapping(root.get("grid"), "grid")
    shape_value = grid.get("shape")
    if (
        not isinstance(shape_value, list)
        or len(shape_value) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in shape_value)
    ):
        raise GammaEngineError(
            "GAMMA_GRID_INVALID", "grid.shape must contain two integer dimensions."
        )
    rows, columns = int(shape_value[0]), int(shape_value[1])
    if rows < 1 or columns < 1:
        raise GammaEngineError("GAMMA_GRID_INVALID", "grid.shape dimensions must be positive.")
    spacing = _pair(grid.get("spacing_mm"), "grid.spacing_mm", positive=True)
    origin = _pair(grid.get("origin_mm", [0.0, 0.0]), "grid.origin_mm", positive=False)

    values = _mapping(root.get("values"), "values")
    if values.get("encoding") != "inline-float32":
        raise GammaEngineError(
            "GAMMA_ENCODING_UNSUPPORTED", "P8 requires inline-float32 measurement values."
        )
    inline = values.get("inline")
    if not isinstance(inline, list) or len(inline) != rows * columns:
        raise GammaEngineError(
            "GAMMA_GRID_VALUE_COUNT_MISMATCH",
            "The number of dose values must exactly match grid.shape.",
        )
    numeric_values: list[float] = []
    for index, item in enumerate(inline):
        numeric_values.append(_finite_float(item, f"values.inline[{index}]"))
    array = np.asarray(numeric_values, dtype=np.float64).reshape((rows, columns))
    if np.any(array < 0):
        raise GammaEngineError("GAMMA_DOSE_NEGATIVE", "Dose values must be non-negative.")
    return MeasurementDataset(
        dataset_id=dataset_id,
        values=array,
        spacing_mm=spacing,
        origin_mm=origin,
        units={"dose": str(dose_unit), "position": str(position_unit)},
    )


def _configuration_from_mapping(payload: Mapping[str, object]) -> GammaConfiguration:
    dimensionality = payload.get("dimensionality", "2D")
    dose_mode = payload.get("dose_difference_mode", "RELATIVE")
    normalization = payload.get("normalization", "GLOBAL")
    interpolation = payload.get("interpolation", "GRID")
    if dimensionality != "2D":
        raise GammaEngineError("GAMMA_DIMENSIONALITY_UNSUPPORTED", "P8 supports 2D Gamma only.")
    if dose_mode not in {"ABSOLUTE", "RELATIVE"}:
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "dose_difference_mode is invalid.")
    if normalization not in {"GLOBAL", "LOCAL"}:
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "normalization is invalid.")
    if interpolation not in {"GRID", "BILINEAR"}:
        raise GammaEngineError("GAMMA_INTERPOLATION_UNSUPPORTED", "interpolation is invalid.")
    dd_percent = _finite_float(
        payload.get("dose_difference_percent"), "dose_difference_percent", positive=True
    )
    dta = _finite_float(
        payload.get("distance_to_agreement_mm"), "distance_to_agreement_mm", positive=True
    )
    threshold = _finite_float(payload.get("dose_threshold_percent"), "dose_threshold_percent")
    pass_rate = _finite_float(
        payload.get("pass_rate_threshold_percent"), "pass_rate_threshold_percent"
    )
    if threshold < 0 or threshold > 100 or pass_rate < 0 or pass_rate > 100:
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "Percentage values must be 0–100.")
    absolute_value = payload.get("absolute_dose_difference_gy")
    absolute = None if absolute_value is None else _finite_float(
        absolute_value, "absolute_dose_difference_gy", positive=True
    )
    if dose_mode == "ABSOLUTE" and absolute is None:
        raise GammaEngineError(
            "GAMMA_CONFIGURATION_INVALID",
            "absolute_dose_difference_gy is required for ABSOLUTE mode.",
        )
    bins_value = payload.get("histogram_bins", 10)
    if (
        isinstance(bins_value, bool)
        or not isinstance(bins_value, int)
        or not 2 <= bins_value <= 100
    ):
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "histogram_bins must be 2–100.")
    return GammaConfiguration(
        dimensionality=str(dimensionality),
        dose_difference_percent=dd_percent,
        dose_difference_mode=str(dose_mode),
        absolute_dose_difference_gy=absolute,
        distance_to_agreement_mm=dta,
        dose_threshold_percent=threshold,
        normalization=str(normalization),
        interpolation=str(interpolation),
        pass_rate_threshold_percent=pass_rate,
        histogram_bins=bins_value,
    )


def _sample_bilinear(
    dataset: MeasurementDataset, row_position: float, column_position: float
) -> float | None:
    row = (row_position - dataset.origin_mm[0]) / dataset.spacing_mm[0]
    column = (column_position - dataset.origin_mm[1]) / dataset.spacing_mm[1]
    if (
        row < 0
        or column < 0
        or row > dataset.values.shape[0] - 1
        or column > dataset.values.shape[1] - 1
    ):
        return None
    row0, column0 = int(math.floor(row)), int(math.floor(column))
    row1, column1 = min(row0 + 1, dataset.values.shape[0] - 1), min(
        column0 + 1, dataset.values.shape[1] - 1
    )
    row_weight, column_weight = row - row0, column - column0
    top = (1 - column_weight) * dataset.values[row0, column0] + column_weight * dataset.values[
        row0, column1
    ]
    bottom = (1 - column_weight) * dataset.values[row1, column0] + column_weight * dataset.values[
        row1, column1
    ]
    return float((1 - row_weight) * top + row_weight * bottom)


def _candidate_gammas(
    reference: MeasurementDataset,
    evaluation: MeasurementDataset,
    reference_row: int,
    reference_column: int,
    reference_value: float,
    configuration: GammaConfiguration,
) -> list[float]:
    ref_row_position = reference.origin_mm[0] + reference_row * reference.spacing_mm[0]
    ref_column_position = reference.origin_mm[1] + reference_column * reference.spacing_mm[1]
    if configuration.interpolation == "GRID":
        row_positions = evaluation.origin_mm[0] + np.arange(
            evaluation.values.shape[0]
        ) * evaluation.spacing_mm[0]
        column_positions = evaluation.origin_mm[1] + np.arange(
            evaluation.values.shape[1]
        ) * evaluation.spacing_mm[1]
        gammas: list[float] = []
        for row_index, row_position in enumerate(row_positions):
            for column_index, column_position in enumerate(column_positions):
                distance = math.hypot(
                    float(row_position) - ref_row_position,
                    float(column_position) - ref_column_position,
                )
                if distance > configuration.distance_to_agreement_mm:
                    continue
                evaluation_value = float(evaluation.values[row_index, column_index])
                dose_scale = _dose_scale(
                    reference_value, float(np.max(reference.values)), configuration
                )
                gammas.append(
                    math.sqrt(
                        ((evaluation_value - reference_value) / dose_scale) ** 2
                        + (distance / configuration.distance_to_agreement_mm) ** 2
                    )
                )
        return gammas

    step = min(*reference.spacing_mm, *evaluation.spacing_mm) / 2
    offsets = np.arange(
        -configuration.distance_to_agreement_mm,
        configuration.distance_to_agreement_mm + step / 2,
        step,
    )
    dose_scale = _dose_scale(reference_value, float(np.max(reference.values)), configuration)
    gammas = []
    for row_offset in offsets:
        for column_offset in offsets:
            distance = math.hypot(float(row_offset), float(column_offset))
            if distance > configuration.distance_to_agreement_mm:
                continue
            sampled_value = _sample_bilinear(
                evaluation,
                ref_row_position + float(row_offset),
                ref_column_position + float(column_offset),
            )
            if sampled_value is None:
                continue
            gammas.append(
                math.sqrt(
                    ((sampled_value - reference_value) / dose_scale) ** 2
                    + (distance / configuration.distance_to_agreement_mm) ** 2
                )
            )
    return gammas


def _dose_scale(
    reference_value: float, reference_max: float, configuration: GammaConfiguration
) -> float:
    base = reference_max if configuration.normalization == "GLOBAL" else abs(reference_value)
    scale = (
        configuration.absolute_dose_difference_gy
        if configuration.dose_difference_mode == "ABSOLUTE"
        else base * configuration.dose_difference_percent / 100
    )
    if scale is None or not math.isfinite(scale) or scale <= 0:
        raise GammaEngineError(
            "GAMMA_DOSE_SCALE_INVALID",
            "Dose-difference scale is zero or invalid for an evaluated point.",
        )
    return scale


def calculate_gamma(
    reference: MeasurementDataset,
    evaluation: MeasurementDataset,
    configuration: GammaConfiguration,
) -> dict[str, object]:
    """Calculate a reproducible 2D Gamma map and summary statistics."""

    reference_max = float(np.max(reference.values))
    if reference_max <= 0:
        raise GammaEngineError("GAMMA_REFERENCE_ZERO", "Reference dose maximum must be positive.")
    threshold = reference_max * configuration.dose_threshold_percent / 100
    map_items: list[dict[str, object]] = []
    gamma_values: list[float] = []
    excluded = 0
    no_candidate = 0
    for row_index, column_index in np.ndindex(reference.values.shape):
        reference_value = float(reference.values[row_index, column_index])
        if reference_value < threshold:
            excluded += 1
            continue
        candidates = _candidate_gammas(
            reference, evaluation, row_index, column_index, reference_value, configuration
        )
        if not candidates:
            no_candidate += 1
            map_items.append(
                {
                    "row": row_index,
                    "column": column_index,
                    "reference_dose_gy": reference_value,
                    "gamma": None,
                    "status": "NO_CANDIDATE",
                }
            )
            continue
        gamma = min(candidates)
        gamma_values.append(gamma)
        map_items.append(
            {
                "row": row_index,
                "column": column_index,
                "reference_dose_gy": reference_value,
                "gamma": gamma,
                "status": "PASS" if gamma <= 1 else "FAIL",
            }
        )

    if not gamma_values:
        raise GammaEngineError(
            "GAMMA_NO_EVALUATED_POINTS", "No reference dose point passed the threshold."
        )
    values = np.asarray(gamma_values, dtype=np.float64)
    passing = int(np.count_nonzero(values <= 1))
    pass_rate = passing / len(gamma_values) * 100
    percentile_values = {
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
    }
    histogram_counts, histogram_edges = np.histogram(
        values, bins=configuration.histogram_bins, range=(0, max(1.0, float(np.max(values))))
    )
    warnings: list[dict[str, object]] = []
    if excluded:
        warnings.append(
            {
                "code": "GAMMA_LOW_DOSE_EXCLUDED",
                "count": excluded,
                "message": "Reference points below the configured dose threshold were excluded.",
            }
        )
    if no_candidate:
        warnings.append(
            {
                "code": "GAMMA_NO_CANDIDATE_WITHIN_DTA",
                "count": no_candidate,
                "message": "Some evaluated points had no comparison point inside the DTA radius.",
            }
        )
    return {
        "algorithm": "deterministic-2d-node-search",
        "reference_dataset_id": reference.dataset_id,
        "evaluation_dataset_id": evaluation.dataset_id,
        "reference_grid": {
            "shape": list(reference.values.shape),
            "spacing_mm": list(reference.spacing_mm),
            "origin_mm": list(reference.origin_mm),
        },
        "evaluation_grid": {
            "shape": list(evaluation.values.shape),
            "spacing_mm": list(evaluation.spacing_mm),
            "origin_mm": list(evaluation.origin_mm),
        },
        "metrics": {
            "evaluated_points": len(gamma_values),
            "passing_points": passing,
            "excluded_points": excluded,
            "no_candidate_points": no_candidate,
            "pass_rate_percent": pass_rate,
            "percentiles": percentile_values,
            "histogram": {
                "counts": [int(item) for item in histogram_counts.tolist()],
                "edges": [float(item) for item in histogram_edges.tolist()],
            },
        },
        "gamma_map": map_items,
        "warnings": warnings,
        "overall_status": "PASS"
        if pass_rate >= configuration.pass_rate_threshold_percent
        else "FAIL",
    }


def calculate_gamma_from_paths(
    reference_path: Path, evaluation_path: Path, configuration_payload: Mapping[str, object]
) -> dict[str, object]:
    """Worker entry point: load both immutable artifacts and calculate the result."""

    configuration = _configuration_from_mapping(configuration_payload)
    reference = load_measurement(reference_path)
    evaluation = load_measurement(evaluation_path)
    result = calculate_gamma(reference, evaluation, configuration)
    result["configuration"] = dict(configuration_payload)
    result["engine_version"] = ENGINE_VERSION
    return result
