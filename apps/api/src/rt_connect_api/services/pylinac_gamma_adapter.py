"""Pylinac-backed Gamma 1D/2D execution boundary for P8.

Pylinac owns the Gamma calculation.  This module only validates the already
validated measurement geometry, converts the RT-CONNECT configuration into
Pylinac's public function arguments, and maps the returned array to the
durable result contract.  The legacy n-dimensional engine remains separate
for historical 3D rows and is never used for a new PSQA run.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from rt_connect_api.services.gamma_engine import (
    GammaEngineError,
    MeasurementDataset,
    load_gamma_dataset,
)
from rt_connect_api.services.pylinac_registry import (
    PYLINAC_VERSION,
    package_fingerprint,
)

PYLINAC_GAMMA_ENGINE_VERSION = f"pylinac-gamma-{PYLINAC_VERSION}"


def _number(payload: Mapping[str, object], key: str, *, positive: bool = False) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", f"{key} must be numeric.")
    converted = float(value)
    if not math.isfinite(converted) or (positive and converted <= 0):
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", f"{key} must be finite and valid.")
    return converted


def _json_safe(value: Any) -> object:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _configuration(payload: Mapping[str, object]) -> dict[str, object]:
    dimensionality = payload.get("dimensionality", "2D")
    if dimensionality not in {"1D", "2D"}:
        raise GammaEngineError(
            "GAMMA_PYLINAC_DIMENSIONALITY_UNSUPPORTED",
            "Pylinac Gamma mới chỉ hỗ trợ cấu hình một chiều hoặc hai chiều.",
        )
    mode = payload.get("dose_difference_mode", "RELATIVE")
    if mode != "RELATIVE":
        raise GammaEngineError(
            "GAMMA_PYLINAC_ABSOLUTE_UNSUPPORTED",
            "Gamma Pylinac dùng chênh lệch liều theo phần trăm của liều cực đại tham chiếu.",
        )
    interpolation = payload.get("interpolation", "GRID")
    if interpolation != "GRID":
        raise GammaEngineError(
            "GAMMA_PYLINAC_INTERPOLATION_UNSUPPORTED",
            "Gamma Pylinac chỉ dùng phép tìm trên lưới đã kiểm định.",
        )
    distance = _number(payload, "distance_to_agreement_mm", positive=True)
    dose_difference = _number(payload, "dose_difference_percent", positive=True)
    threshold = _number(payload, "dose_threshold_percent")
    pass_target = _number(payload, "pass_rate_threshold_percent")
    max_gamma = _number(payload, "max_gamma", positive=True)
    if not 0 <= threshold <= 100 or not 0 <= pass_target <= 100 or not 1 <= max_gamma <= 10:
        raise GammaEngineError(
            "GAMMA_CONFIGURATION_INVALID",
            "Ngưỡng liều, ngưỡng đạt và Gamma tối đa nằm ngoài giới hạn cho phép.",
        )
    normalization = payload.get("normalization", "GLOBAL")
    if normalization not in {"GLOBAL", "LOCAL"}:
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "normalization is invalid.")
    coverage_policy = payload.get("coverage_policy", "FULL_ROI")
    if coverage_policy not in {"FULL_ROI", "OVERLAP_ONLY"}:
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "coverage_policy is invalid.")
    resolution_factor = payload.get("resolution_factor", 3)
    if (
        isinstance(resolution_factor, bool)
        or not isinstance(resolution_factor, int)
        or not 1 <= resolution_factor <= 10
    ):
        raise GammaEngineError(
            "GAMMA_CONFIGURATION_INVALID",
            "Hệ số lấy mẫu lại phải là số nguyên dương.",
        )
    histogram_bins = payload.get("histogram_bins", 10)
    if (
        isinstance(histogram_bins, bool)
        or not isinstance(histogram_bins, int)
        or not 2 <= histogram_bins <= 100
    ):
        raise GammaEngineError(
            "GAMMA_CONFIGURATION_INVALID",
            "Số khoảng biểu đồ phải là số nguyên từ 2 đến 100.",
        )
    return {
        "dimensionality": dimensionality,
        "dose_difference_percent": dose_difference,
        "distance_to_agreement_mm": distance,
        "dose_threshold_percent": threshold,
        "normalization": normalization,
        "coverage_policy": coverage_policy,
        "max_gamma": max_gamma,
        "pass_rate_threshold_percent": pass_target,
        "resolution_factor": resolution_factor,
        "histogram_bins": histogram_bins,
    }


def _finite_array(dataset: MeasurementDataset, label: str) -> np.ndarray:
    values = np.asarray(dataset.values, dtype=np.float64)
    if np.any(~np.isfinite(values)) or np.any(values < 0):
        raise GammaEngineError(
            "GAMMA_DOSE_INVALID",
            f"Dữ liệu {label} phải hữu hạn và không âm.",
        )
    if values.size == 0 or float(np.max(values)) <= 0:
        raise GammaEngineError(
            "GAMMA_DOSE_EMPTY",
            f"Dữ liệu {label} phải có ít nhất một giá trị liều dương.",
        )
    return values


def _coordinates(dataset: MeasurementDataset) -> np.ndarray:
    if len(dataset.spacing_mm) != 1 or len(dataset.origin_mm) != 1:
        raise GammaEngineError(
            "GAMMA_GRID_INVALID",
            "Gamma một chiều cần đúng một khoảng cách điểm và một gốc tọa độ.",
        )
    spacing = float(dataset.spacing_mm[0])
    origin = float(dataset.origin_mm[0])
    if not math.isfinite(spacing) or spacing <= 0 or not math.isfinite(origin):
        raise GammaEngineError("GAMMA_GRID_INVALID", "Hình học Gamma một chiều không hợp lệ.")
    return origin + np.arange(dataset.values.size, dtype=np.float64) * spacing


def _validate_1d_geometry(reference: MeasurementDataset, evaluation: MeasurementDataset) -> None:
    reference_coordinates = _coordinates(reference)
    evaluation_coordinates = _coordinates(evaluation)
    if reference_coordinates[0] < evaluation_coordinates[0] - 1:
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Miền tọa độ tham chiếu phải nằm trong miền dữ liệu đối chiếu.",
        )
    if reference_coordinates[-1] > evaluation_coordinates[-1] + 1:
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Miền tọa độ tham chiếu phải nằm trong miền dữ liệu đối chiếu.",
        )
    if reference.values.ndim != 1 or evaluation.values.ndim != 1:
        raise GammaEngineError(
            "GAMMA_DIMENSIONALITY_MISMATCH",
            "Gamma một chiều cần hai dãy liều một chiều.",
        )


def _validate_2d_geometry(
    reference: MeasurementDataset,
    evaluation: MeasurementDataset,
    distance_to_agreement_mm: float,
) -> int:
    if reference.values.ndim != 2 or evaluation.values.ndim != 2:
        raise GammaEngineError(
            "GAMMA_DIMENSIONALITY_MISMATCH",
            "Gamma hai chiều cần hai lưới liều hai chiều.",
        )
    if reference.values.shape != evaluation.values.shape:
        raise GammaEngineError(
            "GAMMA_GRID_INCOMPATIBLE",
            "Hai lưới liều phải có cùng số hàng và số cột.",
        )
    if len(reference.spacing_mm) != 2 or len(evaluation.spacing_mm) != 2:
        raise GammaEngineError("GAMMA_GRID_INVALID", "Hình học Gamma hai chiều không hợp lệ.")
    if not np.allclose(reference.spacing_mm, evaluation.spacing_mm, rtol=0, atol=1e-6):
        raise GammaEngineError(
            "GAMMA_GRID_INCOMPATIBLE",
            "Hai lưới liều phải có cùng kích thước điểm ảnh.",
        )
    if not np.allclose(reference.origin_mm, evaluation.origin_mm, rtol=0, atol=1e-6):
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Hai lưới liều phải có cùng gốc tọa độ trong hệ quy chiếu đã kiểm định.",
        )
    row_spacing, column_spacing = (float(item) for item in reference.spacing_mm)
    if not math.isclose(row_spacing, column_spacing, rel_tol=0, abs_tol=1e-6):
        raise GammaEngineError(
            "GAMMA_PYLINAC_GRID_NON_SQUARE",
            "Gamma hai chiều của Pylinac cần điểm ảnh vuông để đổi DTA sang số điểm ảnh.",
        )
    pixels = distance_to_agreement_mm / row_spacing
    rounded = round(pixels)
    if rounded < 1 or not math.isclose(pixels, rounded, rel_tol=0, abs_tol=1e-6):
        raise GammaEngineError(
            "GAMMA_DTA_GRID_INCOMPATIBLE",
            "DTA (mm) phải là bội số nguyên của kích thước điểm ảnh đối với Gamma hai chiều.",
        )
    return int(rounded)


def _metrics(
    gamma: np.ndarray, reference: np.ndarray, configuration: Mapping[str, object]
) -> dict[str, object]:
    threshold = float(np.max(reference)) * _number(configuration, "dose_threshold_percent") / 100
    selected_mask = np.isfinite(reference) & (reference >= threshold)
    finite_gamma = np.isfinite(gamma)
    selected_count = int(np.count_nonzero(selected_mask))
    excluded_count = int(reference.size - selected_count)
    evaluated_count = int(np.count_nonzero(finite_gamma & selected_mask))
    if selected_count == 0 or evaluated_count == 0:
        raise GammaEngineError(
            "GAMMA_NO_EVALUATED_POINTS",
            "Không có điểm liều nào đủ điều kiện để tính Gamma.",
        )
    values = np.asarray(gamma[finite_gamma & selected_mask], dtype=np.float64)
    passing_count = int(np.count_nonzero(values <= 1.0))
    pass_rate = passing_count / evaluated_count * 100.0
    invalid_coverage = (
        evaluated_count < selected_count and configuration["coverage_policy"] == "FULL_ROI"
    )
    percentiles: dict[str, object] = {
        "exact": True,
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
    }
    if invalid_coverage:
        percentiles.update({"exact": False, "reason": "GAMMA_INCOMPLETE_COVERAGE"})
    histogram_bins = configuration.get("histogram_bins")
    if not isinstance(histogram_bins, int):
        histogram_bins = 10
    histogram_counts, histogram_edges = np.histogram(
        values,
        bins=histogram_bins,
        range=(0, max(1.0, float(np.max(values)))),
    )
    return {
        "evaluated_points": evaluated_count,
        "passing_points": passing_count,
        "nonpassing_points": evaluated_count - passing_count,
        "excluded_points": excluded_count,
        "selected_points": selected_count,
        "invalid_coverage_points": selected_count - evaluated_count,
        "coverage_fraction": evaluated_count / selected_count,
        "pass_rate_percent": None if invalid_coverage else pass_rate,
        "percentiles": percentiles,
        "histogram": {
            "counts": [int(item) for item in histogram_counts.tolist()],
            "edges": [float(item) for item in histogram_edges.tolist()],
        },
    }


def _map_items(
    gamma: np.ndarray,
    reference: np.ndarray,
    *,
    coordinates: np.ndarray | None = None,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    if gamma.ndim == 1:
        for index, value in enumerate(gamma):
            item: dict[str, object] = {
                "index": index,
                "reference_dose_gy": float(reference[index]),
                "gamma": float(value) if math.isfinite(float(value)) else None,
                "status": (
                    "EXCLUDED"
                    if not math.isfinite(float(value))
                    else ("PASS" if value <= 1 else "FAIL")
                ),
            }
            if coordinates is not None:
                item["coordinate_mm"] = float(coordinates[index])
            items.append(item)
        return items
    for raw_index in np.ndindex(gamma.shape):
        value = float(gamma[raw_index])
        items.append(
            {
                "row": raw_index[0],
                "column": raw_index[1],
                "reference_dose_gy": float(reference[raw_index]),
                "gamma": value if math.isfinite(value) else None,
                "status": (
                    "EXCLUDED" if not math.isfinite(value) else ("PASS" if value <= 1 else "FAIL")
                ),
            }
        )
    return items


def calculate_pylinac_gamma(
    reference: MeasurementDataset,
    evaluation: MeasurementDataset,
    configuration_payload: Mapping[str, object],
) -> dict[str, object]:
    """Run Pylinac Gamma 1D or 2D and return a JSON-safe RT-CONNECT result."""

    configuration = _configuration(configuration_payload)
    reference_values = _finite_array(reference, "tham chiếu")
    evaluation_values = _finite_array(evaluation, "đối chiếu")
    dimensionality = configuration["dimensionality"]
    dose_difference = _number(configuration, "dose_difference_percent", positive=True)
    distance_mm = _number(configuration, "distance_to_agreement_mm", positive=True)
    dose_threshold = _number(configuration, "dose_threshold_percent")
    global_dose = configuration["normalization"] == "GLOBAL"
    max_gamma = _number(configuration, "max_gamma", positive=True)
    if not global_dose and np.any(reference_values <= 0):
        raise GammaEngineError(
            "GAMMA_LOCAL_NORMALIZATION_INVALID",
            "Chuẩn hóa cục bộ không thể dùng khi điểm tham chiếu có liều bằng không.",
        )

    try:
        if dimensionality == "1D":
            _validate_1d_geometry(reference, evaluation)
            from pylinac.core.gamma import gamma_1d  # type: ignore[import-untyped]

            reference_coordinates = _coordinates(reference)
            evaluation_coordinates = _coordinates(evaluation)
            gamma_values, resampled_reference, resampled_coordinates = gamma_1d(
                reference_values,
                evaluation_values,
                reference_coordinates=reference_coordinates,
                evaluation_coordinates=evaluation_coordinates,
                dose_to_agreement=dose_difference,
                distance_to_agreement=distance_mm,
                gamma_cap_value=max_gamma,
                global_dose=global_dose,
                dose_threshold=dose_threshold,
                resolution_factor=int(_number(configuration, "resolution_factor", positive=True)),
                fill_value=np.nan,
            )
            del resampled_reference, resampled_coordinates
            result_array = np.asarray(gamma_values, dtype=np.float64)
            map_coordinates = reference_coordinates
            algorithm = "pylinac.core.gamma.gamma_1d"
            engine_class = "gamma_1d"
        else:
            distance_pixels = _validate_2d_geometry(reference, evaluation, distance_mm)
            from pylinac.core.gamma import gamma_2d  # type: ignore[import-untyped]

            result_array = np.asarray(
                gamma_2d(
                    reference_values,
                    evaluation_values,
                    dose_to_agreement=dose_difference,
                    distance_to_agreement=distance_pixels,
                    gamma_cap_value=max_gamma,
                    global_dose=global_dose,
                    dose_threshold=dose_threshold,
                    fill_value=np.nan,
                ),
                dtype=np.float64,
            )
            map_coordinates = None
            algorithm = "pylinac.core.gamma.gamma_2d"
            engine_class = "gamma_2d"
    except GammaEngineError:
        raise
    except Exception as exc:
        raise GammaEngineError(
            "GAMMA_PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể tính Gamma với hai dữ liệu đã chọn.",
        ) from exc

    metrics = _metrics(result_array, reference_values, configuration)
    invalid_coverage_points = metrics["invalid_coverage_points"]
    if not isinstance(invalid_coverage_points, int):
        raise GammaEngineError("GAMMA_RESULT_INVALID", "Pylinac không trả về số điểm hợp lệ.")
    invalid_coverage = (
        invalid_coverage_points > 0 and configuration["coverage_policy"] == "FULL_ROI"
    )
    pass_rate = metrics["pass_rate_percent"]
    if invalid_coverage:
        overall_status = "INVALID"
    elif not isinstance(pass_rate, int | float):
        raise GammaEngineError("GAMMA_RESULT_INVALID", "Pylinac không trả về tỷ lệ đạt hợp lệ.")
    else:
        overall_status = (
            "PASS"
            if float(pass_rate) >= _number(configuration, "pass_rate_threshold_percent")
            else "FAIL"
        )
    warnings: list[dict[str, object]] = []
    if metrics["excluded_points"]:
        warnings.append(
            {
                "code": "GAMMA_LOW_DOSE_EXCLUDED",
                "count": metrics["excluded_points"],
                "message": "Các điểm dưới ngưỡng liều thấp đã được loại khỏi mẫu số.",
            }
        )
    if metrics["invalid_coverage_points"]:
        warnings.append(
            {
                "code": "GAMMA_INCOMPLETE_COVERAGE",
                "count": metrics["invalid_coverage_points"],
                "message": "Một phần vùng tham chiếu không có giá trị Gamma hữu hạn.",
            }
        )
    return {
        "schema_version": "p8.pylinac-gamma-result.v1",
        "engine": "pylinac",
        "engine_class": engine_class,
        "algorithm": algorithm,
        "engine_version": PYLINAC_GAMMA_ENGINE_VERSION,
        "package_fingerprint": package_fingerprint(),
        "dimensionality": dimensionality,
        "configuration": _json_safe(dict(configuration_payload)),
        "reference_grid": {
            "shape": list(reference_values.shape),
            "spacing_mm": list(reference.spacing_mm),
            "origin_mm": list(reference.origin_mm),
            "source_format": reference.source_format,
        },
        "evaluation_grid": {
            "shape": list(evaluation_values.shape),
            "spacing_mm": list(evaluation.spacing_mm),
            "origin_mm": list(evaluation.origin_mm),
            "source_format": evaluation.source_format,
        },
        "metrics": metrics,
        "gamma_map": _map_items(result_array, reference_values, coordinates=map_coordinates),
        "warnings": warnings,
        "overall_status": overall_status,
    }


def calculate_pylinac_gamma_from_paths(
    reference_path: Path,
    evaluation_path: Path,
    configuration_payload: Mapping[str, object],
) -> dict[str, object]:
    """Worker entry point for immutable object-storage artifacts."""

    reference = load_gamma_dataset(reference_path)
    evaluation = load_gamma_dataset(evaluation_path)
    return calculate_pylinac_gamma(reference, evaluation, configuration_payload)
