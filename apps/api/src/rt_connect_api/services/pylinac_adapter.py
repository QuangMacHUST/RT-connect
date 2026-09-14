"""Pylinac execution boundary for image-based Machine QA.

The web application owns the form, parameter validation and user assessment.
This module owns only the call into the locked pylinac wheel and conversion of
its public result/overlay into a durable, JSON-safe contract.  It deliberately
does not reimplement pylinac metrics or silently fall back to another engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from rt_connect_api.services.pylinac_registry import (
    PYLINAC_VERSION,
    package_fingerprint,
    resolve_runtime_symbol,
    runtime_binding,
)


class PylinacAdapterError(ValueError):
    """A user-safe error raised before or during a pylinac execution."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PylinacExecutionResult:
    """Immutable output of one engine call before persistence."""

    catalog_key: str
    engine_class: str
    engine_version: str
    package_fingerprint: str
    result_snapshot: dict[str, object]
    warnings: list[dict[str, object]]
    overlay_bytes: bytes | None
    overlay_media_type: str | None
    overlay_filename: str | None


def _json_safe(value: Any) -> object:
    """Convert pylinac's public result data to values accepted by JSON columns."""

    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    try:
        json.dumps(value)
    except (TypeError, ValueError):
        return str(value)
    return value


def _number(parameters: dict[str, object], key: str, *, minimum: float | None = None) -> float:
    value = parameters.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PylinacAdapterError("PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải là số.")
    result = float(value)
    if minimum is not None and result < minimum:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải lớn hơn hoặc bằng {minimum}."
        )
    return result


def _optional_number(
    parameters: dict[str, object], key: str, *, minimum: float | None = None
) -> float | None:
    if parameters.get(key) is None:
        return None
    return _number(parameters, key, minimum=minimum)


def _integer(parameters: dict[str, object], key: str, *, minimum: int | None = None) -> int:
    value = parameters.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PylinacAdapterError("PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải là số nguyên.")
    if minimum is not None and value < minimum:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải lớn hơn hoặc bằng {minimum}."
        )
    return value


def _bool(parameters: dict[str, object], key: str, default: bool = False) -> bool:
    value = parameters.get(key, default)
    if not isinstance(value, bool):
        raise PylinacAdapterError("PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải là đúng/sai.")
    return value


def _picket_fence_parameters(
    parameters: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    constructor_keys = {"filter", "use_filename", "mlc", "crop_mm"}
    analysis_keys = {
        "tolerance",
        "action_tolerance",
        "num_pickets",
        "sag_adjustment",
        "orientation",
        "invert",
        "leaf_analysis_width_ratio",
        "picket_spacing",
        "height_threshold",
        "edge_threshold",
        "peak_sort",
        "required_prominence",
        "fwxm",
        "separate_leaves",
        "nominal_gap_mm",
        "central_axis",
    }
    unknown = set(parameters) - constructor_keys - analysis_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho bài Picket Fence.",
        )

    constructor: dict[str, object] = {}
    if parameters.get("filter") is not None:
        constructor["filter"] = _integer(parameters, "filter", minimum=0)
    if "use_filename" in parameters:
        constructor["use_filename"] = _bool(parameters, "use_filename")
    if "mlc" in parameters:
        mlc = parameters["mlc"]
        if not isinstance(mlc, str) or not mlc.strip():
            raise PylinacAdapterError("PYLINAC_PARAMETER_INVALID", "Cấu hình MLC không hợp lệ.")
        constructor["mlc"] = mlc.strip()
    if "crop_mm" in parameters:
        constructor["crop_mm"] = _integer(parameters, "crop_mm", minimum=0)

    analysis: dict[str, object] = {}
    for key in ("tolerance", "sag_adjustment", "leaf_analysis_width_ratio", "picket_spacing"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0 if key != "sag_adjustment" else None)
    if "action_tolerance" in parameters:
        action_tolerance = _optional_number(parameters, "action_tolerance", minimum=0)
        analysis["action_tolerance"] = action_tolerance
    for key in ("height_threshold", "edge_threshold", "required_prominence", "nominal_gap_mm"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    for key in ("num_pickets", "fwxm"):
        if key in parameters:
            analysis[key] = _integer(parameters, key, minimum=1)
    for key in ("invert", "separate_leaves"):
        if key in parameters:
            analysis[key] = _bool(parameters, key)
    for key in ("orientation", "peak_sort"):
        if key in parameters:
            value = parameters[key]
            if not isinstance(value, str) or not value.strip():
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", f"Tham số {key} không hợp lệ."
                )
            analysis[key] = value.strip()
    if "central_axis" in parameters:
        point = parameters["central_axis"]
        if (
            not isinstance(point, dict)
            or not isinstance(point.get("x"), int | float)
            or not isinstance(point.get("y"), int | float)
        ):
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Tâm trục phải có tọa độ x và y hợp lệ."
            )
        analysis["central_axis"] = point
    return constructor, analysis


def _execute_picket_fence(
    source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, resolution_error = resolve_runtime_symbol("PICKET_FENCE")
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích Picket Fence chưa sẵn sàng."
        )
    constructor, analysis = _picket_fence_parameters(parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        if "central_axis" in analysis:
            from pylinac.core.geometry import Point  # type: ignore[import-untyped]

            point = analysis["central_axis"]
            assert isinstance(point, dict)
            analysis["central_axis"] = Point(float(point["x"]), float(point["y"]))
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả không hợp lệ."
            )
        overlay = BytesIO()
        engine.save_analyzed_image(overlay, show_text=True)
        return PylinacExecutionResult(
            catalog_key="PICKET_FENCE",
            engine_class="PicketFence",
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": "PicketFence",
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in result.get("warnings", [])
                if item
            ],
            overlay_bytes=overlay.getvalue(),
            overlay_media_type="image/png",
            overlay_filename="picket-fence-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        # The raw exception is intentionally not returned to the user.  Logs
        # can retain the correlation id while the persisted run gets a stable
        # error code and a remediation message.
        _ = resolution_error
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích tệp này. Hãy kiểm tra đúng loại ảnh "
            "và tham số rồi thử lại.",
        ) from exc


def _starshot_parameters(
    parameters: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Validate and split image-loading and analysis options for Starshot."""

    constructor_keys = {"dpi", "sid"}
    analysis_keys = {
        "radius",
        "min_peak_height",
        "max_wobble_diameter",
        "tolerance",
        "start_point",
        "fwhm",
        "recursive",
        "invert",
    }
    unknown = set(parameters) - constructor_keys - analysis_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho bài kiểm tra sao.",
        )

    constructor: dict[str, object] = {}
    for key in constructor_keys:
        if key in parameters and parameters[key] is not None:
            constructor[key] = _number(parameters, key, minimum=0)

    analysis: dict[str, object] = {}
    for key in ("radius", "min_peak_height"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    for key in ("max_wobble_diameter", "tolerance"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    for key in ("fwhm", "recursive", "invert"):
        if key in parameters:
            analysis[key] = _bool(parameters, key)
    if "start_point" in parameters and parameters["start_point"] is not None:
        point = parameters["start_point"]
        if (
            not isinstance(point, dict)
            or not isinstance(point.get("x"), int | float)
            or not isinstance(point.get("y"), int | float)
        ):
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID",
                "Tâm bắt đầu phải có tọa độ x và y hợp lệ.",
            )
        analysis["start_point"] = point
    return constructor, analysis


def _execute_starshot(
    source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol("STARSHOT")
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích kiểm tra sao chưa sẵn sàng."
        )
    constructor, analysis = _starshot_parameters(parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        if "start_point" in analysis:
            from pylinac.core.geometry import Point

            point = analysis["start_point"]
            assert isinstance(point, dict)
            analysis["start_point"] = Point(float(point["x"]), float(point["y"]))
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả không hợp lệ."
            )
        overlay = BytesIO()
        engine.save_analyzed_image(overlay)
        return PylinacExecutionResult(
            catalog_key="STARSHOT",
            engine_class="Starshot",
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": "Starshot",
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in result.get("warnings", [])
                if item
            ],
            overlay_bytes=overlay.getvalue(),
            overlay_media_type="image/png",
            overlay_filename="kiem-tra-sao-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích ảnh kiểm tra sao. Hãy kiểm tra thang đo, "
            "tâm bắt đầu và các tham số rồi thử lại.",
        ) from exc


def execute_pylinac(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    """Execute a registered capability; no custom-engine fallback is allowed."""

    binding = runtime_binding(catalog_key)
    if binding is None:
        raise PylinacAdapterError("PYLINAC_CAPABILITY_NOT_FOUND", "Không tìm thấy bài QA đã chọn.")
    if catalog_key == "PICKET_FENCE":
        return _execute_picket_fence(source_path, parameters)
    if catalog_key == "STARSHOT":
        return _execute_starshot(source_path, parameters)
    raise PylinacAdapterError(
        "PYLINAC_ADAPTER_NOT_READY",
        "Bộ giao diện cho bài QA này chưa được mở; chưa chạy bằng bộ tính khác.",
    )
