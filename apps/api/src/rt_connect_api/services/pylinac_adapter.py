"""Pylinac execution boundary for image-based Machine QA.

The web application owns the form, parameter validation and user assessment.
This module owns only the call into the locked pylinac wheel and conversion of
its public result/overlay into a durable, JSON-safe contract.  It deliberately
does not reimplement pylinac metrics or silently fall back to another engine.
"""

from __future__ import annotations

import json
import tempfile
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


def _number_or_array(
    parameters: dict[str, object], key: str, *, minimum: float | None = None
) -> float | tuple[float, ...]:
    value = parameters.get(key)
    if isinstance(value, bool):
        raise PylinacAdapterError("PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải là số.")
    if isinstance(value, int | float):
        result = float(value)
        if minimum is not None and result < minimum:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải lớn hơn hoặc bằng {minimum}."
            )
        return result
    if isinstance(value, (list, tuple)) and value:
        values: list[float] = []
        for item in value:
            if isinstance(item, bool) or not isinstance(item, int | float):
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải là số hoặc dãy số."
                )
            number = float(item)
            if minimum is not None and number < minimum:
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải lớn hơn hoặc bằng {minimum}."
                )
            values.append(number)
        return tuple(values)
    raise PylinacAdapterError(
        "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải là số hoặc dãy số không rỗng."
    )


def _optional_number_or_array(
    parameters: dict[str, object], key: str, *, minimum: float | None = None
) -> float | tuple[float, ...] | None:
    if parameters.get(key) is None:
        return None
    return _number_or_array(parameters, key, minimum=minimum)


def _required_text(parameters: dict[str, object], key: str) -> str:
    value = parameters.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Tham số {key} không được để trống."
        )
    return value.strip()


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
            from pylinac.core.geometry import Point

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


def _winston_lutz_parameters(
    parameters: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Validate and split ZIP loading and Winston–Lutz analysis options."""

    constructor_keys = {"use_filenames", "dpi", "sid"}
    analysis_keys = {
        "bb_size_mm",
        "low_density_bb",
        "open_field",
        "apply_virtual_shift",
        "snap_tolerance",
        "gantry_reference",
        "collimator_reference",
        "couch_reference",
        "bb_proximity_mm",
    }
    unknown = set(parameters) - constructor_keys - analysis_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho bài Winston–Lutz.",
        )

    constructor: dict[str, object] = {}
    if "use_filenames" in parameters:
        constructor["use_filenames"] = _bool(parameters, "use_filenames")
    for key in ("dpi", "sid"):
        if key in parameters and parameters[key] is not None:
            constructor[key] = _number(parameters, key, minimum=0)

    analysis: dict[str, object] = {}
    if "bb_size_mm" in parameters:
        analysis["bb_size_mm"] = _number(parameters, "bb_size_mm", minimum=0)
    for key in ("snap_tolerance", "gantry_reference", "collimator_reference", "couch_reference"):
        if key in parameters:
            analysis[key] = _number(parameters, key)
    if "bb_proximity_mm" in parameters:
        analysis["bb_proximity_mm"] = _number(parameters, "bb_proximity_mm", minimum=0)
    for key in ("low_density_bb", "open_field", "apply_virtual_shift"):
        if key in parameters:
            analysis[key] = _bool(parameters, key)
    return constructor, analysis


def _execute_winston_lutz(
    source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol("WINSTON_LUTZ")
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích Winston–Lutz chưa sẵn sàng."
        )
    if source_path.suffix.lower() != ".zip":
        raise PylinacAdapterError(
            "PYLINAC_INPUT_FORMAT_INVALID",
            "Winston–Lutz yêu cầu một tệp ZIP chứa bộ ảnh theo các góc máy.",
        )
    constructor, analysis = _winston_lutz_parameters(parameters)
    try:
        engine = symbol.from_zip(str(source_path), **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả không hợp lệ."
            )
        figures, _ = engine.plot_images(show=False, split=False)
        overlay_bytes: bytes | None = None
        if figures:
            overlay = BytesIO()
            figures[0].savefig(overlay, format="png", dpi=120)
            overlay_bytes = overlay.getvalue()
            for figure in figures:
                figure.clf()
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key="WINSTON_LUTZ",
            engine_class="WinstonLutz",
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": "WinstonLutz",
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png" if overlay_bytes is not None else None,
            overlay_filename="winston-lutz-phan-tich.png" if overlay_bytes is not None else None,
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích bộ ảnh Winston–Lutz. Hãy kiểm tra tệp ZIP, "
            "tên góc máy và các tham số rồi thử lại.",
        ) from exc


def _winston_lutz_multi_target_parameters(
    parameters: dict[str, object],
) -> tuple[dict[str, object], dict[str, object], tuple[object, ...]]:
    """Validate MT/MF loading options and build Pylinac BBConfig objects."""

    constructor_keys = {"use_filenames", "dpi", "sid", "axes_precision"}
    analysis_keys = {"bb_arrangement", "is_open_field", "is_low_density", "bb_proximity_mm"}
    unknown = set(parameters) - constructor_keys - analysis_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho bài Winston–Lutz nhiều bi.",
        )

    constructor: dict[str, object] = {}
    if "use_filenames" in parameters:
        constructor["use_filenames"] = _bool(parameters, "use_filenames")
    for key in ("dpi", "sid"):
        if key in parameters and parameters[key] is not None:
            constructor[key] = _number(parameters, key, minimum=0)
    if "axes_precision" in parameters:
        constructor["axes_precision"] = _integer(parameters, "axes_precision", minimum=0)

    arrangement = parameters.get("bb_arrangement")
    if not isinstance(arrangement, list) or not arrangement:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", "Cần khai báo ít nhất một bi chuẩn cho bài kiểm tra."
        )
    if len(arrangement) > 32:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", "Số bi chuẩn vượt quá giới hạn cho phép."
        )
    try:
        from pylinac.winston_lutz import BBConfig

        bb_configs: list[object] = []
        for item in arrangement:
            if not isinstance(item, dict):
                raise TypeError
            name = item.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("name")
            values = {
                key: _number(item, key)
                for key in (
                    "offset_left_mm",
                    "offset_up_mm",
                    "offset_in_mm",
                    "bb_size_mm",
                    "rad_size_mm",
                )
            }
            if values["bb_size_mm"] <= 0 or values["rad_size_mm"] <= 0:
                raise ValueError("size")
            bb_configs.append(BBConfig(name=name.strip(), **values))
    except PylinacAdapterError:
        raise
    except (TypeError, ValueError, KeyError) as exc:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID",
            "Cấu hình vị trí bi chuẩn chưa đầy đủ hoặc có giá trị không hợp lệ.",
        ) from exc

    analysis: dict[str, object] = {"bb_arrangement": tuple(bb_configs)}
    for key in ("is_open_field", "is_low_density"):
        if key in parameters:
            analysis[key] = _bool(parameters, key)
    if "bb_proximity_mm" in parameters:
        analysis["bb_proximity_mm"] = _number(parameters, "bb_proximity_mm", minimum=0)
    return constructor, analysis, tuple(bb_configs)


def _execute_winston_lutz_multi_target(
    source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol("WINSTON_LUTZ_MULTI_TARGET")
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE",
            "Bộ phân tích Winston–Lutz nhiều bi chưa sẵn sàng.",
        )
    if source_path.suffix.lower() != ".zip":
        raise PylinacAdapterError(
            "PYLINAC_INPUT_FORMAT_INVALID",
            "Winston–Lutz nhiều bi yêu cầu một tệp ZIP chứa bộ ảnh.",
        )
    constructor, analysis, _ = _winston_lutz_multi_target_parameters(parameters)
    try:
        engine = symbol.from_zip(str(source_path), **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả không hợp lệ."
            )
        figures, _ = engine.plot_images(show=False, zoomed=False, legend=True)
        overlay_bytes: bytes | None = None
        if figures:
            overlay = BytesIO()
            figures[0].savefig(overlay, format="png", dpi=120)
            overlay_bytes = overlay.getvalue()
            for figure in figures:
                figure.clf()
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key="WINSTON_LUTZ_MULTI_TARGET",
            engine_class="WinstonLutzMultiTargetMultiField",
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": "WinstonLutzMultiTargetMultiField",
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png" if overlay_bytes is not None else None,
            overlay_filename=(
                "winston-lutz-nhieu-bi-phan-tich.png" if overlay_bytes is not None else None
            ),
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích bộ ảnh Winston–Lutz nhiều bi. Hãy kiểm tra tệp ZIP, "
            "cấu hình bi chuẩn và các tham số rồi thử lại.",
        ) from exc


def _pair_of_numbers(parameters: dict[str, object], key: str) -> tuple[float, float]:
    value = parameters.get(key)
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải có đúng hai giá trị số."
        )
    first, second = value
    if (
        isinstance(first, bool)
        or isinstance(second, bool)
        or not isinstance(first, int | float)
        or not isinstance(second, int | float)
    ):
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải có đúng hai giá trị số."
        )
    return float(first), float(second)


def _vmat_parameters(
    catalog_key: str, parameters: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    constructor_keys = {"ground", "check_inversion"}
    analysis_keys = {"tolerance", "segment_size_mm", "invert_image_order"}
    if catalog_key == "VMAT_DRCS":
        analysis_keys.add("collimator_radial_distances")
    unknown = set(parameters) - constructor_keys - analysis_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED", "Có tham số không được hỗ trợ cho bài VMAT đã chọn."
        )

    constructor: dict[str, object] = {}
    for key in constructor_keys:
        if key in parameters:
            constructor[key] = _bool(parameters, key)
    analysis: dict[str, object] = {}
    if "tolerance" in parameters:
        analysis["tolerance"] = _number(parameters, "tolerance", minimum=0)
    if "segment_size_mm" in parameters:
        width, length = _pair_of_numbers(parameters, "segment_size_mm")
        if width <= 0 or length <= 0:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Kích thước đoạn phân tích phải lớn hơn 0."
            )
        analysis["segment_size_mm"] = (width, length)
    if "invert_image_order" in parameters:
        analysis["invert_image_order"] = _bool(parameters, "invert_image_order")
    if catalog_key == "VMAT_DRCS" and "collimator_radial_distances" in parameters:
        first, second = _pair_of_numbers(parameters, "collimator_radial_distances")
        if first < 0 or second < first:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID",
                "Khoảng cách xuyên tâm chuẩn trực chưa hợp lệ.",
            )
        analysis["collimator_radial_distances"] = (first, second)
    return constructor, analysis


def _execute_vmat(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích VMAT chưa sẵn sàng trên máy chủ."
        )
    if not source_path.is_dir():
        raise PylinacAdapterError(
            "PYLINAC_INPUT_COUNT_INVALID", "Bài VMAT yêu cầu một cặp ảnh mở và ảnh động."
        )
    image_paths = sorted(path for path in source_path.iterdir() if path.is_file())
    if len(image_paths) != 2:
        raise PylinacAdapterError(
            "PYLINAC_INPUT_COUNT_INVALID", "Bài VMAT yêu cầu đúng hai ảnh đầu vào."
        )
    constructor, analysis = _vmat_parameters(catalog_key, parameters)
    try:
        engine = symbol(image_paths, **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả không hợp lệ."
            )
        from matplotlib import pyplot as plt

        engine.plot_analyzed_image(show=False, show_text=True)
        figure = plt.gcf()
        overlay = BytesIO()
        figure.savefig(overlay, format="png", dpi=120)
        plt.close(figure)
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        engine_class = {
            "VMAT_DRGS": "DRGS",
            "VMAT_DRMLC": "DRMLC",
            "VMAT_DRCS": "DRCS",
        }[catalog_key]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=engine_class,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": engine_class,
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay.getvalue(),
            overlay_media_type="image/png",
            overlay_filename=f"{engine_class.lower()}-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích cặp ảnh VMAT. Hãy kiểm tra ảnh mở, ảnh động "
            "và các tham số rồi thử lại.",
        ) from exc


def _choice(
    parameters: dict[str, object], key: str, allowed: set[str], default: str
) -> str:
    value = parameters.get(key, default)
    if not isinstance(value, str) or value not in allowed:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Tham số {key} chưa được chọn đúng giá trị."
        )
    return value


def _pair_range(
    parameters: dict[str, object], key: str, *, minimum: float = 0
) -> tuple[float, float]:
    first, second = _pair_of_numbers(parameters, key)
    if first < minimum or second <= first:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Khoảng {key} chưa hợp lệ."
        )
    return first, second


def _field_profile_parameters(
    parameters: dict[str, object], *, legacy: bool
) -> dict[str, object]:
    if legacy:
        allowed = {
            "protocol",
            "centering",
            "vert_position",
            "horiz_position",
            "vert_width",
            "horiz_width",
            "in_field_ratio",
            "slope_exclusion_ratio",
            "invert",
            "is_FFF",
            "penumbra",
            "interpolation",
            "interpolation_resolution_mm",
            "ground",
            "normalization_method",
            "edge_detection_method",
            "edge_smoothing_ratio",
            "hill_window_ratio",
        }
    else:
        allowed = {
            "centering",
            "position",
            "x_width",
            "y_width",
            "normalization",
            "edge_type",
            "invert",
            "ground",
        }
    unknown = set(parameters) - allowed
    if unknown:
        label = "Field Analysis" if legacy else "Field Profile Analysis"
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            f"Có tham số không được hỗ trợ cho bài {label}.",
        )

    if legacy:
        protocol = _choice(
            parameters, "protocol", {"NONE", "VARIAN", "SIEMENS", "ELEKTA"}, "VARIAN"
        )
        centering = _choice(
            parameters,
            "centering",
            {"MANUAL", "BEAM_CENTER", "GEOMETRIC_CENTER"},
            "BEAM_CENTER",
        )
        interpolation = _choice(
            parameters, "interpolation", {"NONE", "LINEAR", "SPLINE"}, "LINEAR"
        )
        normalization = _choice(
            parameters,
            "normalization_method",
            {"NONE", "GEOMETRIC_CENTER", "BEAM_CENTER", "MAX"},
            "BEAM_CENTER",
        )
        edge = _choice(
            parameters,
            "edge_detection_method",
            {"FWHM", "INFLECTION_DERIVATIVE", "INFLECTION_HILL"},
            "INFLECTION_DERIVATIVE",
        )
        result: dict[str, object] = {
            "protocol": protocol,
            "centering": centering,
            "interpolation": interpolation,
            "normalization_method": normalization,
            "edge_detection_method": edge,
        }
        for key in ("vert_position", "horiz_position", "in_field_ratio", "slope_exclusion_ratio"):
            if key in parameters:
                value = _number(parameters, key, minimum=0)
                if value > 1:
                    raise PylinacAdapterError(
                        "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải nằm trong khoảng 0 đến 1."
                    )
                result[key] = value
        for key in (
            "vert_width",
            "horiz_width",
            "interpolation_resolution_mm",
            "edge_smoothing_ratio",
        ):
            if key in parameters:
                result[key] = _number(parameters, key, minimum=0)
        if "hill_window_ratio" in parameters:
            result["hill_window_ratio"] = _number(parameters, "hill_window_ratio", minimum=0)
        if "penumbra" in parameters:
            result["penumbra"] = _pair_range(parameters, "penumbra")
        for key in ("invert", "is_FFF", "ground"):
            if key in parameters:
                result[key] = _bool(parameters, key)
        return result

    centering = _choice(
        parameters,
        "centering",
        {"MANUAL", "BEAM_CENTER", "GEOMETRIC_CENTER"},
        "BEAM_CENTER",
    )
    normalization = _choice(
        parameters,
        "normalization",
        {"NONE", "GEOMETRIC_CENTER", "BEAM_CENTER", "MAX"},
        "NONE",
    )
    edge = _choice(
        parameters,
        "edge_type",
        {"FWHM", "INFLECTION_DERIVATIVE", "INFLECTION_HILL"},
        "INFLECTION_DERIVATIVE",
    )
    result = {"centering": centering, "normalization": normalization, "edge_type": edge}
    if "position" in parameters:
        x, y = _pair_of_numbers(parameters, "position")
        if not 0 <= x <= 1 or not 0 <= y <= 1:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Vị trí biên dạng phải nằm trong khoảng 0 đến 1."
            )
        result["position"] = (x, y)
    for key in ("x_width", "y_width"):
        if key in parameters:
            result[key] = _number(parameters, key, minimum=0)
    for key in ("invert", "ground"):
        if key in parameters:
            result[key] = _bool(parameters, key)
    return result


def _enum_value(module_name: str, enum_name: str, value: str) -> object:
    module = __import__(module_name, fromlist=[enum_name])
    enum_type = getattr(module, enum_name)
    return getattr(enum_type, value)


def _save_figure(figure: Any) -> bytes:
    overlay = BytesIO()
    figure.savefig(overlay, format="png", dpi=120)
    return overlay.getvalue()


def _catphan_parameters(
    source_path: Path, parameters: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    constructor_keys = {"check_uid", "memory_efficient_mode", "is_zip"}
    analysis_keys = {
        "hu_tolerance",
        "scaling_tolerance",
        "thickness_tolerance",
        "low_contrast_tolerance",
        "cnr_threshold",
        "zip_after",
        "contrast_method",
        "visibility_threshold",
        "thickness_slice_straddle",
        "expected_hu_values",
        "x_adjustment",
        "y_adjustment",
        "angle_adjustment",
        "roi_size_factor",
        "scaling_factor",
        "origin_slice",
        "roll_slice_offset",
    }
    unknown = set(parameters) - constructor_keys - analysis_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED", "Có tham số không được hỗ trợ cho bài CatPhan."
        )
    constructor: dict[str, object] = {
        "check_uid": _bool(parameters, "check_uid", True),
        "memory_efficient_mode": _bool(parameters, "memory_efficient_mode", False),
        "is_zip": _bool(parameters, "is_zip", source_path.suffix.lower() == ".zip"),
    }
    analysis: dict[str, object] = {}
    for key in (
        "hu_tolerance",
        "scaling_tolerance",
        "thickness_tolerance",
        "low_contrast_tolerance",
        "cnr_threshold",
    ):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    for key in (
        "x_adjustment",
        "y_adjustment",
        "angle_adjustment",
        "roi_size_factor",
        "scaling_factor",
        "roll_slice_offset",
    ):
        if key in parameters:
            minimum = (
                0 if key in {"roi_size_factor", "scaling_factor"} else None
            )
            analysis[key] = _number(parameters, key, minimum=minimum)
    if "visibility_threshold" in parameters:
        visibility_threshold = _number(parameters, "visibility_threshold", minimum=0)
        if visibility_threshold > 1:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Ngưỡng nhìn thấy phải nằm trong khoảng 0 đến 1."
            )
        analysis["visibility_threshold"] = visibility_threshold
    if "origin_slice" in parameters:
        value = parameters["origin_slice"]
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, int):
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", "Lát gốc phải là số nguyên hoặc để trống."
                )
            analysis["origin_slice"] = value
    if "zip_after" in parameters:
        analysis["zip_after"] = _bool(parameters, "zip_after")
    if "contrast_method" in parameters:
        value = parameters["contrast_method"]
        if not isinstance(value, str) or not value.strip():
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Phương pháp tương phản không hợp lệ."
            )
        analysis["contrast_method"] = value.strip()
    if "thickness_slice_straddle" in parameters:
        value = parameters["thickness_slice_straddle"]
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Cách chọn lát độ dày không hợp lệ."
            )
        analysis["thickness_slice_straddle"] = value
    if "expected_hu_values" in parameters:
        value = parameters["expected_hu_values"]
        if not isinstance(value, dict) or any(
            isinstance(item, bool) or not isinstance(item, int | float) for item in value.values()
        ):
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Bảng giá trị HU kỳ vọng không hợp lệ."
            )
        analysis["expected_hu_values"] = value
    return constructor, analysis


def _execute_catphan(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích CatPhan chưa sẵn sàng."
        )
    if not source_path.is_file() or source_path.suffix.lower() != ".zip":
        raise PylinacAdapterError(
            "PYLINAC_INPUT_FORMAT_INVALID", "Bài CatPhan cần một tệp ZIP DICOM."
        )
    constructor, analysis = _catphan_parameters(source_path, parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả CatPhan không hợp lệ."
            )
        from matplotlib import pyplot as plt

        engine.plot_analyzed_image(show=False)
        figure = plt.gcf()
        overlay_bytes = _save_figure(figure)
        plt.close(figure)
        engine_class = {
            "CATPHAN_503": "CatPhan503",
            "CATPHAN_504": "CatPhan504",
            "CATPHAN_600": "CatPhan600",
            "CATPHAN_604": "CatPhan604",
            "CATPHAN_700": "CatPhan700",
        }[catalog_key]
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=engine_class,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": engine_class,
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png",
            overlay_filename=f"{catalog_key.lower()}-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích bộ ảnh CatPhan. Hãy kiểm tra tệp ZIP và tham số "
            "rồi thử lại.",
        ) from exc


_ACR_KEYS = {"ACR_CT_464", "ACR_MRI_LARGE", "ACR_MRI_MEDIUM"}


def _acr_parameters(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    constructor_keys = {"check_uid", "memory_efficient_mode", "is_zip"}
    common_analysis_keys = {
        "x_adjustment",
        "y_adjustment",
        "angle_adjustment",
        "roi_size_factor",
        "scaling_factor",
        "origin_slice",
    }
    mri_analysis_keys = {
        "echo_number",
        "low_contrast_method",
        "low_contrast_visibility_threshold",
        "low_contrast_visibility_sanity_multiplier",
    }
    allowed = constructor_keys | common_analysis_keys
    if catalog_key in {"ACR_MRI_LARGE", "ACR_MRI_MEDIUM"}:
        allowed |= mri_analysis_keys
    unknown = set(parameters) - allowed
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED", "Có tham số không được hỗ trợ cho bài ACR."
        )
    constructor: dict[str, object] = {
        "check_uid": _bool(parameters, "check_uid", True),
        "memory_efficient_mode": _bool(parameters, "memory_efficient_mode", False),
        "is_zip": _bool(parameters, "is_zip", source_path.suffix.lower() == ".zip"),
    }
    analysis: dict[str, object] = {}
    for key in ("x_adjustment", "y_adjustment", "angle_adjustment"):
        if key in parameters:
            analysis[key] = _number(parameters, key)
    for key in ("roi_size_factor", "scaling_factor"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    if "origin_slice" in parameters and parameters["origin_slice"] is not None:
        analysis["origin_slice"] = _integer(parameters, "origin_slice", minimum=0)
    if catalog_key in {"ACR_MRI_LARGE", "ACR_MRI_MEDIUM"}:
        if "echo_number" in parameters and parameters["echo_number"] is not None:
            analysis["echo_number"] = _integer(parameters, "echo_number", minimum=1)
        for key in (
            "low_contrast_visibility_threshold",
            "low_contrast_visibility_sanity_multiplier",
        ):
            if key in parameters:
                analysis[key] = _number(parameters, key, minimum=0)
        if "low_contrast_method" in parameters:
            method = parameters["low_contrast_method"]
            if not isinstance(method, str) or not method.strip():
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", "Phương pháp tương phản thấp không hợp lệ."
                )
            analysis["low_contrast_method"] = method.strip()
    return constructor, analysis


def _execute_acr(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích ACR chưa sẵn sàng."
        )
    if not source_path.is_file() or source_path.suffix.lower() != ".zip":
        raise PylinacAdapterError(
            "PYLINAC_INPUT_FORMAT_INVALID", "Bài ACR cần một tệp ZIP chứa chuỗi DICOM."
        )
    constructor, analysis = _acr_parameters(catalog_key, source_path, parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả ACR không hợp lệ."
            )
        from matplotlib import pyplot as plt

        figure = engine.plot_analyzed_image(show=False)
        overlay_bytes = _save_figure(figure)
        plt.close(figure)
        engine_class = {
            "ACR_CT_464": "ACRCT",
            "ACR_MRI_LARGE": "ACRMRILarge",
            "ACR_MRI_MEDIUM": "ACRMRIMedium",
        }[catalog_key]
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=engine_class,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": engine_class,
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png",
            overlay_filename=f"{catalog_key.lower()}-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích bộ ảnh ACR. Hãy kiểm tra tệp ZIP và tham số rồi thử lại.",
        ) from exc


_CHEESE_KEYS = {"CHEESE_TOMO", "CHEESE_CIRS_062M"}


def _cheese_parameters(
    source_path: Path, parameters: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    constructor_keys = {"check_uid", "memory_efficient_mode", "is_zip"}
    analysis_keys = {
        "roi_config",
        "x_adjustment",
        "y_adjustment",
        "angle_adjustment",
        "roi_size_factor",
        "scaling_factor",
        "origin_slice",
    }
    unknown = set(parameters) - constructor_keys - analysis_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED", "Có tham số không được hỗ trợ cho bài phantom đo liều."
        )
    constructor: dict[str, object] = {
        "check_uid": _bool(parameters, "check_uid", True),
        "memory_efficient_mode": _bool(parameters, "memory_efficient_mode", False),
        "is_zip": _bool(parameters, "is_zip", source_path.suffix.lower() == ".zip"),
    }
    analysis: dict[str, object] = {}
    if "roi_config" in parameters:
        roi_config = parameters["roi_config"]
        if not isinstance(roi_config, dict):
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Bảng mật độ tham chiếu của ROI không hợp lệ."
            )
        normalized_config: dict[str, dict[str, float]] = {}
        for roi_number, roi_data in roi_config.items():
            if not isinstance(roi_number, str) or not roi_number.isdigit():
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", "Số ROI tham chiếu không hợp lệ."
                )
            if not isinstance(roi_data, dict) or set(roi_data) != {"density"}:
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID",
                    "Mỗi ROI tham chiếu phải có đúng một giá trị mật độ.",
                )
            density = roi_data["density"]
            if isinstance(density, bool) or not isinstance(density, int | float):
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", "Mật độ tham chiếu phải là số."
                )
            normalized_config[roi_number] = {"density": float(density)}
        analysis["roi_config"] = normalized_config
    for key in ("x_adjustment", "y_adjustment", "angle_adjustment"):
        if key in parameters:
            analysis[key] = _number(parameters, key)
    for key in ("roi_size_factor", "scaling_factor"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    if "origin_slice" in parameters and parameters["origin_slice"] is not None:
        analysis["origin_slice"] = _integer(parameters, "origin_slice", minimum=0)
    return constructor, analysis


def _execute_cheese(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích phantom đo liều chưa sẵn sàng."
        )
    if not source_path.is_file() or source_path.suffix.lower() != ".zip":
        raise PylinacAdapterError(
            "PYLINAC_INPUT_FORMAT_INVALID", "Bài phantom đo liều cần một tệp ZIP chứa chuỗi DICOM."
        )
    constructor, analysis = _cheese_parameters(source_path, parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả phantom đo liều không hợp lệ."
            )
        from matplotlib import pyplot as plt

        engine.plot_analyzed_image(show=False)
        figure = plt.gcf()
        overlay_bytes = _save_figure(figure)
        plt.close(figure)
        engine_class = {
            "CHEESE_TOMO": "TomoCheese",
            "CHEESE_CIRS_062M": "CIRS062M",
        }[catalog_key]
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=engine_class,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": engine_class,
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png",
            overlay_filename=f"{catalog_key.lower()}-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích phantom đo liều. Hãy kiểm tra tệp ZIP và tham số "
            "rồi thử lại.",
        ) from exc


_CT_PHANTOM_KEYS = {"GE_HELIOS", "QUART_DVT", "QUART_HYPERSIGHT"}


def _ct_phantom_parameters(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    constructor_keys = {"check_uid", "memory_efficient_mode", "is_zip"}
    common_analysis_keys = {
        "x_adjustment",
        "y_adjustment",
        "angle_adjustment",
        "roi_size_factor",
        "scaling_factor",
        "origin_slice",
    }
    quart_analysis_keys = {
        "hu_tolerance",
        "scaling_tolerance",
        "thickness_tolerance",
        "cnr_threshold",
        "roll_slice_offset",
    }
    allowed = constructor_keys | common_analysis_keys
    if catalog_key in {"QUART_DVT", "QUART_HYPERSIGHT"}:
        allowed |= quart_analysis_keys
    unknown = set(parameters) - allowed
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED", "Có tham số không được hỗ trợ cho bài phantom CT."
        )
    constructor: dict[str, object] = {
        "check_uid": _bool(parameters, "check_uid", True),
        "memory_efficient_mode": _bool(parameters, "memory_efficient_mode", False),
        "is_zip": _bool(parameters, "is_zip", source_path.suffix.lower() == ".zip"),
    }
    analysis: dict[str, object] = {}
    for key in ("x_adjustment", "y_adjustment", "angle_adjustment"):
        if key in parameters:
            analysis[key] = _number(parameters, key)
    for key in ("roi_size_factor", "scaling_factor"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    if "origin_slice" in parameters and parameters["origin_slice"] is not None:
        analysis["origin_slice"] = _integer(parameters, "origin_slice", minimum=0)
    if catalog_key in {"QUART_DVT", "QUART_HYPERSIGHT"}:
        for key in ("hu_tolerance", "scaling_tolerance", "thickness_tolerance", "cnr_threshold"):
            if key in parameters:
                analysis[key] = _number(parameters, key, minimum=0)
        if "roll_slice_offset" in parameters:
            analysis["roll_slice_offset"] = _number(parameters, "roll_slice_offset")
    return constructor, analysis


def _execute_ct_phantom(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    # Pylinac 3.47 keeps HypersightQuartDVT as a deprecated compatibility
    # class whose constructor no longer accepts the input path.  QuartDVT is
    # the supported replacement and now handles the same water-vial variant.
    if catalog_key == "QUART_HYPERSIGHT":
        try:
            from pylinac.quart import QuartDVT as symbol
        except (ImportError, AttributeError):
            symbol = None
    else:
        symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích phantom CT chưa sẵn sàng."
        )
    if not source_path.is_file() or source_path.suffix.lower() != ".zip":
        raise PylinacAdapterError(
            "PYLINAC_INPUT_FORMAT_INVALID", "Bài phantom CT cần một tệp ZIP chứa chuỗi DICOM."
        )
    constructor, analysis = _ct_phantom_parameters(catalog_key, source_path, parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả phantom CT không hợp lệ."
            )
        from matplotlib import pyplot as plt

        plotted = engine.plot_analyzed_image(show=False)
        figure = plotted if hasattr(plotted, "savefig") else plt.gcf()
        overlay_bytes = _save_figure(figure)
        plt.close(figure)
        engine_class = {
            "GE_HELIOS": "GEHeliosCTDaily",
            "QUART_DVT": "QuartDVT",
            "QUART_HYPERSIGHT": "QuartDVT",
        }[catalog_key]
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=engine_class,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": engine_class,
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png",
            overlay_filename=f"{catalog_key.lower()}-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích phantom CT. Hãy kiểm tra tệp ZIP và tham số rồi thử lại.",
        ) from exc


_PLANAR_PROFILE_KEYS = {
    "PLANAR_LEEDS_TOR_18",
    "PLANAR_LEEDS_TOR_BLUE",
    "PLANAR_STANDARD_IMAGING_QC3",
    "PLANAR_STANDARD_IMAGING_QC_KV",
    "PLANAR_LAS_VEGAS",
    "PLANAR_ELEKTA_LAS_VEGAS",
    "PLANAR_DOSELAB_MC2_MV",
    "PLANAR_DOSELAB_MC2_KV",
    "PLANAR_SNC_MV",
    "PLANAR_SNC_MV_12510",
    "PLANAR_SNC_KV",
    "PLANAR_PTW_EPID_QC",
    "PLANAR_IBA_PRIMUS_A",
}
_PLANAR_FIELD_KEYS = {
    "PLANAR_STANDARD_IMAGING_FC2",
    "PLANAR_IMT_LRAD",
    "PLANAR_DOSELAB_RLF",
    "PLANAR_PTW_ISO_ALIGN",
    "PLANAR_SNC_FSQA",
}


def _optional_planar_number(
    parameters: dict[str, object], key: str, *, minimum: float | None = None
) -> float | None:
    value = parameters.get(key)
    if value is None:
        return None
    return _number(parameters, key, minimum=minimum)


def _planar_point(parameters: dict[str, object], key: str) -> tuple[float, float] | None:
    if parameters.get(key) is None:
        return None
    return _pair_of_numbers(parameters, key)


def _planar_parameters(
    catalog_key: str, parameters: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    constructor_keys = {"normalize"}
    common_keys = {
        "low_contrast_threshold",
        "high_contrast_threshold",
        "invert",
        "angle_override",
        "center_override",
        "size_override",
        "ssd",
        "low_contrast_method",
        "visibility_threshold",
        "x_adjustment",
        "y_adjustment",
        "angle_adjustment",
        "roi_size_factor",
        "scaling_factor",
    }
    field_keys = {"fwxm", "bb_edge_threshold_mm", "kernel_size_multiplier"}
    acr_keys = {
        "low_contrast_visibility_threshold",
        "speck_group_contrast_method",
        "speck_group_visibility_threshold",
        "speck_group_half_thresh",
        "speck_group_full_thresh",
        "fiber_sigmas_ratio",
        "fiber_max_gap",
        "fiber_len_half_thresh",
        "fiber_len_full_thresh",
        "fiber_orientation_tolerance",
    }
    allowed = constructor_keys | common_keys
    if catalog_key in _PLANAR_FIELD_KEYS:
        allowed |= field_keys
    elif catalog_key == "PLANAR_ACR_DIGITAL_MAMMOGRAPHY":
        allowed = constructor_keys | {
            "low_contrast_threshold",
            "invert",
            "angle_override",
            "center_override",
            "size_override",
            "ssd",
            "low_contrast_method",
            "x_adjustment",
            "y_adjustment",
            "angle_adjustment",
            "roi_size_factor",
            "scaling_factor",
        } | acr_keys
    unknown = set(parameters) - allowed
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED", "Có tham số không được hỗ trợ cho bài ảnh phẳng."
        )
    constructor: dict[str, object] = {"normalize": _bool(parameters, "normalize", True)}
    analysis: dict[str, object] = {}
    for key in ("low_contrast_threshold", "high_contrast_threshold", "visibility_threshold"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    if "low_contrast_threshold" in parameters and "high_contrast_threshold" in parameters:
        low_threshold = _number(parameters, "low_contrast_threshold", minimum=0)
        high_threshold = _number(parameters, "high_contrast_threshold", minimum=0)
        if high_threshold < low_threshold:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Ngưỡng tương phản cao phải lớn hơn ngưỡng thấp."
            )
    if "invert" in parameters:
        analysis["invert"] = _bool(parameters, "invert")
    for key in (
        "angle_override",
        "size_override",
        "x_adjustment",
        "y_adjustment",
        "angle_adjustment",
    ):
        numeric_value = _optional_planar_number(parameters, key)
        if numeric_value is not None:
            analysis[key] = numeric_value
    point = _planar_point(parameters, "center_override")
    if point is not None:
        analysis["center_override"] = point
    if "ssd" in parameters:
        ssd_value = parameters["ssd"]
        if ssd_value != "auto" and (
            isinstance(ssd_value, bool) or not isinstance(ssd_value, int | float)
        ):
            raise PylinacAdapterError("PYLINAC_PARAMETER_INVALID", "SSD không hợp lệ.")
        analysis["ssd"] = ssd_value
    for key in ("low_contrast_method", "speck_group_contrast_method"):
        if key in parameters:
            method_value = parameters[key]
            if not isinstance(method_value, str) or not method_value.strip():
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", f"Tham số {key} không hợp lệ."
                )
            analysis[key] = method_value.strip()
    for key in ("roi_size_factor", "scaling_factor"):
        if key in parameters:
            analysis[key] = _number(parameters, key, minimum=0)
    if catalog_key in _PLANAR_FIELD_KEYS:
        analysis["fwxm"] = _integer(parameters, "fwxm", minimum=1) if "fwxm" in parameters else 50
        for key in ("bb_edge_threshold_mm", "kernel_size_multiplier"):
            if key in parameters:
                analysis[key] = _number(parameters, key, minimum=0)
    if catalog_key == "PLANAR_ACR_DIGITAL_MAMMOGRAPHY":
        for key in (
            "low_contrast_visibility_threshold",
            "speck_group_visibility_threshold",
            "fiber_max_gap",
            "fiber_len_half_thresh",
            "fiber_len_full_thresh",
            "fiber_orientation_tolerance",
        ):
            if key in parameters:
                analysis[key] = _number(parameters, key, minimum=0)
        for key in ("speck_group_half_thresh", "speck_group_full_thresh"):
            if key in parameters:
                analysis[key] = _integer(parameters, key, minimum=1)
        if "fiber_sigmas_ratio" in parameters:
            first, second = _pair_of_numbers(parameters, "fiber_sigmas_ratio")
            if first <= 0 or second <= 0:
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", "Tỷ lệ sigma của sợi không hợp lệ."
                )
            analysis["fiber_sigmas_ratio"] = (first, second)
    return constructor, analysis


def _execute_planar(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích ảnh phẳng chưa sẵn sàng."
        )
    if not source_path.is_file():
        raise PylinacAdapterError(
            "PYLINAC_INPUT_FORMAT_INVALID", "Bài ảnh phẳng cần một tệp ảnh đầu vào."
        )
    constructor, analysis = _planar_parameters(catalog_key, parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        engine.analyze(**analysis)
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả ảnh phẳng không hợp lệ."
            )
        from matplotlib import pyplot as plt

        # Pylinac 3.47 exposes the Matplotlib result renderer for planar
        # phantoms as ``plot_analyzed_image``.  ``plot`` belongs to the
        # Plotly-facing API and is not present on classes such as LeedsTOR.
        plotted = engine.plot_analyzed_image(show=False)
        figures = plotted[0] if isinstance(plotted, tuple) and plotted else []
        if not isinstance(figures, (list, tuple)):
            figures = [figures]
        figure = figures[0] if figures else plt.gcf()
        overlay_bytes = _save_figure(figure)
        for plotted_figure in figures:
            plt.close(plotted_figure)
        binding = runtime_binding(catalog_key)
        engine_class = binding.import_path.rsplit(".", 1)[-1] if binding else catalog_key
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=engine_class,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": engine_class,
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png",
            overlay_filename=f"{catalog_key.lower()}-phan-tich.png",
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích ảnh phẳng. Hãy kiểm tra đúng phantom, ảnh và tham số "
            "rồi thử lại.",
        ) from exc


def _execute_field_profile(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích biên dạng trường chưa sẵn sàng."
        )
    legacy = catalog_key == "FIELD_ANALYSIS_LEGACY"
    analysis = _field_profile_parameters(parameters, legacy=legacy)
    try:
        engine = symbol(str(source_path))
        if legacy:
            analysis["protocol"] = _enum_value(
                "pylinac.field_analysis", "Protocol", str(analysis["protocol"])
            )
            analysis["centering"] = _enum_value(
                "pylinac.field_analysis", "Centering", str(analysis["centering"])
            )
            analysis["interpolation"] = _enum_value(
                "pylinac.field_analysis", "Interpolation", str(analysis["interpolation"])
            )
            analysis["normalization_method"] = _enum_value(
                "pylinac.field_analysis", "Normalization", str(analysis["normalization_method"])
            )
            analysis["edge_detection_method"] = _enum_value(
                "pylinac.field_analysis", "Edge", str(analysis["edge_detection_method"])
            )
            figures, _ = engine.analyze(**analysis) or ([], [])
            _ = figures
            result_figures, _ = engine.plot_analyzed_image(show=False, split_plots=True)
            figure = result_figures[0]
            engine_class = "FieldAnalysis"
            overlay_filename = "field-analysis-phan-tich.png"
        else:
            analysis["centering"] = _enum_value(
                "pylinac.field_profile_analysis", "Centering", str(analysis["centering"])
            )
            analysis["normalization"] = _enum_value(
                "pylinac.field_profile_analysis", "Normalization", str(analysis["normalization"])
            )
            analysis["edge_type"] = _enum_value(
                "pylinac.field_profile_analysis", "Edge", str(analysis["edge_type"])
            )
            engine.analyze(**analysis)
            result_figures = engine.plot_analyzed_images(show=False)
            figure = result_figures[-1]
            engine_class = "FieldProfileAnalysis"
            overlay_filename = "field-profile-analysis-phan-tich.png"
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả biên dạng không hợp lệ."
            )
        overlay_bytes = _save_figure(figure)
        from matplotlib import pyplot as plt

        for plotted in result_figures:
            plt.close(plotted)
        warnings = result.get("warnings", [])
        warning_items = warnings if isinstance(warnings, list) else [warnings]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=engine_class,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-result.v1",
                "engine": "pylinac",
                "engine_class": engine_class,
                "metrics": result,
                "engine_passed": result.get("passed"),
                "parameters": _json_safe(parameters),
            },
            warnings=[
                {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
                for item in warning_items
                if item
            ],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png",
            overlay_filename=overlay_filename,
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích biên dạng trường. Hãy kiểm tra ảnh và tham số "
            "rồi thử lại.",
        ) from exc


_CALIBRATION_KEYS = {
    "CALIBRATION_TG51_PHOTON",
    "CALIBRATION_TG51_ELECTRON_LEGACY",
    "CALIBRATION_TG51_ELECTRON_MODERN",
    "CALIBRATION_TRS398_PHOTON",
    "CALIBRATION_TRS398_ELECTRON",
}
_CALIBRATION_COMMON_KEYS = {
    "institution",
    "physicist",
    "unit",
    "measurement_date",
    "electrometer",
    "temp",
    "press",
    "chamber",
    "n_dw",
    "p_elec",
    "k_elec",
    "energy",
    "voltage_reference",
    "voltage_reduced",
    "m_reference",
    "m_opposite",
    "m_reduced",
    "mu",
    "tissue_correction",
    "m_reference_adjusted",
}


def _calibration_parameters(
    catalog_key: str, parameters: dict[str, object]
) -> dict[str, object]:
    if catalog_key == "CALIBRATION_TG51_PHOTON":
        specific_keys = {"measured_pdd10", "lead_foil", "clinical_pdd10", "fff"}
    elif catalog_key == "CALIBRATION_TG51_ELECTRON_LEGACY":
        specific_keys = {"k_ecal", "clinical_pdd", "m_gradient", "cone", "i_50"}
    elif catalog_key == "CALIBRATION_TG51_ELECTRON_MODERN":
        specific_keys = {"clinical_pdd", "cone", "i_50"}
    elif catalog_key == "CALIBRATION_TRS398_PHOTON":
        specific_keys = {
            "setup",
            "tpr2010",
            "fff",
            "clinical_pdd_zref",
            "clinical_tmr_zref",
        }
    elif catalog_key == "CALIBRATION_TRS398_ELECTRON":
        specific_keys = {"cone", "i_50", "clinical_pdd_zref"}
    else:
        raise PylinacAdapterError("PYLINAC_CAPABILITY_NOT_FOUND", "Không tìm thấy bài hiệu chuẩn.")

    allowed_common_keys = _CALIBRATION_COMMON_KEYS - {
        "p_elec",
        "k_elec",
        "m_reference_adjusted",
    }
    if catalog_key.startswith("CALIBRATION_TG51_"):
        allowed_common_keys |= {"p_elec", "m_reference_adjusted"}
    else:
        allowed_common_keys.add("k_elec")
    unknown = set(parameters) - allowed_common_keys - specific_keys
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho bài hiệu chuẩn đã chọn.",
        )

    constructor: dict[str, object] = {}
    for key in ("institution", "physicist", "unit", "measurement_date", "electrometer"):
        if key in parameters:
            constructor[key] = _required_text(parameters, key)
    for key in ("temp", "press", "n_dw", "p_elec", "k_elec", "tissue_correction"):
        if key in parameters:
            constructor[key] = _number(parameters, key)
    for key in ("m_reference", "m_opposite", "m_reduced"):
        if key in parameters:
            constructor[key] = _number_or_array(parameters, key)
    if catalog_key == "CALIBRATION_TG51_ELECTRON_LEGACY":
        constructor["m_gradient"] = _number_or_array(parameters, "m_gradient")
    if "m_reference_adjusted" in parameters:
        constructor["m_reference_adjusted"] = _optional_number_or_array(
            parameters, "m_reference_adjusted"
        )
    for key in ("voltage_reference", "voltage_reduced", "mu"):
        if key in parameters:
            constructor[key] = _integer(parameters, key, minimum=1)

    if catalog_key.startswith("CALIBRATION_TG51_"):
        constructor["energy"] = _integer(parameters, "energy", minimum=1)
    else:
        constructor["energy"] = _required_text(parameters, "energy")
    for key in ("chamber", "cone"):
        if key in parameters:
            constructor[key] = _required_text(parameters, key)

    if catalog_key == "CALIBRATION_TG51_PHOTON":
        if parameters.get("lead_foil") is not None:
            constructor["lead_foil"] = _required_text(parameters, "lead_foil")
        # RT-CONNECT always exposes PDDx/kQ and dose outputs for this class.
        # Although Pylinac's constructor accepts None, those public properties
        # require a measured PDD and would otherwise fail later as an opaque
        # execution error.  Validate it at the user-input boundary instead.
        constructor["measured_pdd10"] = _number(parameters, "measured_pdd10", minimum=0)
        constructor["clinical_pdd10"] = _number(parameters, "clinical_pdd10", minimum=0)
        constructor["fff"] = _bool(parameters, "fff", False)
    elif catalog_key == "CALIBRATION_TG51_ELECTRON_LEGACY":
        constructor["k_ecal"] = _number(parameters, "k_ecal", minimum=0)
        constructor["clinical_pdd"] = _number(parameters, "clinical_pdd", minimum=0)
        constructor["i_50"] = _number(parameters, "i_50", minimum=0)
        constructor["cone"] = _required_text(parameters, "cone")
    elif catalog_key == "CALIBRATION_TG51_ELECTRON_MODERN":
        constructor["clinical_pdd"] = _number(parameters, "clinical_pdd", minimum=0)
        constructor["i_50"] = _number(parameters, "i_50", minimum=0)
        constructor["cone"] = _required_text(parameters, "cone")
        constructor["tissue_correction"] = _number(parameters, "tissue_correction", minimum=0)
    elif catalog_key == "CALIBRATION_TRS398_PHOTON":
        constructor["setup"] = _required_text(parameters, "setup")
        constructor["tpr2010"] = _number(parameters, "tpr2010", minimum=0)
        constructor["fff"] = _bool(parameters, "fff")
        pdd = _optional_number(parameters, "clinical_pdd_zref", minimum=0)
        tmr = _optional_number(parameters, "clinical_tmr_zref", minimum=0)
        if pdd is None and tmr is None:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Cần nhập PDD hoặc TMR tại độ sâu tham chiếu."
            )
        constructor["clinical_pdd_zref"] = pdd
        constructor["clinical_tmr_zref"] = tmr
    else:
        constructor["i_50"] = _number(parameters, "i_50", minimum=0)
        constructor["clinical_pdd_zref"] = _number(parameters, "clinical_pdd_zref", minimum=0)
        constructor["tissue_correction"] = _number(parameters, "tissue_correction", minimum=0)
        constructor["cone"] = _required_text(parameters, "cone")
    return constructor


_CALIBRATION_RESULT_PROPERTIES: dict[str, tuple[str, ...]] = {
    "CALIBRATION_TG51_PHOTON": (
        "p_tp",
        "p_ion",
        "p_pol",
        "m_corrected",
        "pddx",
        "kq",
        "dose_mu_10",
        "dose_mu_dmax",
    ),
    "CALIBRATION_TG51_ELECTRON_LEGACY": (
        "p_tp",
        "p_ion",
        "p_pol",
        "m_corrected",
        "r_50",
        "dref",
        "pq_gr",
        "kq",
        "dose_mu_dref",
        "dose_mu_dmax",
    ),
    "CALIBRATION_TG51_ELECTRON_MODERN": (
        "p_tp",
        "p_ion",
        "p_pol",
        "m_corrected",
        "r_50",
        "dref",
        "kq",
        "dose_mu_dref",
        "dose_mu_dmax",
    ),
    "CALIBRATION_TRS398_PHOTON": (
        "k_tp",
        "k_s",
        "k_pol",
        "m_corrected",
        "kq",
        "dose_mu_zref",
        "dose_mu_zmax",
    ),
    "CALIBRATION_TRS398_ELECTRON": (
        "k_tp",
        "k_s",
        "k_pol",
        "m_corrected",
        "r_50",
        "zref",
        "kq",
        "dose_mu_zref",
        "dose_mu_zmax",
    ),
}


def _execute_calibration(
    catalog_key: str, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ tính hiệu chuẩn chưa sẵn sàng trên máy chủ."
        )
    constructor = _calibration_parameters(catalog_key, parameters)
    try:
        engine = symbol(**constructor)
        metrics: dict[str, object] = {}
        for property_name in _CALIBRATION_RESULT_PROPERTIES[catalog_key]:
            metrics[property_name] = _json_safe(getattr(engine, property_name))
        metrics["output_was_adjusted"] = _json_safe(engine.output_was_adjusted)
        if bool(metrics["output_was_adjusted"]):
            for property_name in (
                "m_corrected_adjustment",
                "dose_mu_10_adjusted",
                "dose_mu_dmax_adjusted",
                "dose_mu_dref_adjusted",
                "dose_mu_zref_adjusted",
                "dose_mu_zmax_adjusted",
            ):
                if hasattr(type(engine), property_name):
                    metrics[property_name] = _json_safe(getattr(engine, property_name))
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=type(engine).__name__,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-calibration-result.v1",
                "engine": "pylinac",
                "engine_class": type(engine).__name__,
                "metrics": metrics,
                "engine_passed": None,
                "parameters": _json_safe(parameters),
            },
            warnings=[],
            overlay_bytes=None,
            overlay_media_type=None,
            overlay_filename=None,
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể tính hiệu chuẩn. Hãy kiểm tra số đo, đơn vị và tham số rồi thử lại.",
        ) from exc


_LOG_KEYS = {
    "LOG_DYNALOG",
    "LOG_TRAJECTORY_2_1",
    "LOG_TRAJECTORY_3",
    "LOG_TRAJECTORY_4",
}


def _log_parameters(parameters: dict[str, object]) -> dict[str, object]:
    allowed = {
        "exclude_beam_off",
        "calc_gamma",
        "dose_tolerance",
        "distance_tolerance",
        "threshold",
        "resolution",
        "calc_individual_maps",
        "rms_percentile",
        "error_percentile",
    }
    unknown = set(parameters) - allowed
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho bài phân tích nhật ký.",
        )
    normalized: dict[str, object] = {
        "exclude_beam_off": _bool(parameters, "exclude_beam_off", True),
        "calc_gamma": _bool(parameters, "calc_gamma", False),
        "calc_individual_maps": _bool(parameters, "calc_individual_maps", False),
    }
    for key in ("dose_tolerance", "distance_tolerance", "threshold", "resolution"):
        if key in parameters:
            normalized[key] = _number(parameters, key, minimum=0)
    for key in ("rms_percentile", "error_percentile"):
        if key in parameters:
            value = _number(parameters, key, minimum=0)
            if value > 100:
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải nằm trong khoảng 0 đến 100."
                )
            normalized[key] = value
    if normalized["calc_gamma"]:
        for key in ("dose_tolerance", "distance_tolerance"):
            gamma_value = normalized.get(key)
            if not isinstance(gamma_value, (int, float)) or gamma_value <= 0:
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID",
                    "Muốn tạo bản đồ Gamma cần nhập dung sai liều và khoảng cách lớn hơn 0.",
                )
        normalized.setdefault("threshold", 0.1)
        normalized.setdefault("resolution", 0.1)
    return normalized


def _log_source_file(source_path: Path, catalog_key: str) -> Path:
    if not source_path.is_dir():
        return source_path
    candidates = sorted(source_path.iterdir())
    if catalog_key == "LOG_DYNALOG":
        dynalogs = [item for item in candidates if item.suffix.lower() == ".dlg"]
        if len(dynalogs) != 2:
            raise PylinacAdapterError(
                "PYLINAC_INPUT_COUNT_INVALID", "Dynalog cần đúng cặp tệp A và B có đuôi DLG."
            )
        selected = next(
            (item for item in dynalogs if item.name.upper().startswith("A")), dynalogs[0]
        )
    else:
        binaries = [item for item in candidates if item.suffix.lower() in {".bin", ".tlog"}]
        if not binaries:
            raise PylinacAdapterError(
                "PYLINAC_INPUT_FORMAT_INVALID", "Trajectory Log cần tệp nhị phân BIN hoặc TLOG."
            )
        selected = binaries[0]
    return selected


def _axis_difference_summary(axis: object) -> float | None:
    expected = getattr(axis, "expected", None)
    if expected is None:
        return None
    import numpy as np

    difference = getattr(axis, "difference", None)
    if difference is None:
        return None
    values = np.asarray(difference, dtype=float)
    if values.size == 0:
        return None
    return float(np.nanmax(np.abs(values)))


def _execute_log(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích nhật ký chưa sẵn sàng trên máy chủ."
        )
    options = _log_parameters(parameters)
    log_path = _log_source_file(source_path, catalog_key)
    try:
        engine = symbol(str(log_path), exclude_beam_off=options["exclude_beam_off"])
        if catalog_key != "LOG_DYNALOG":
            expected_version = {
                "LOG_TRAJECTORY_2_1": 2.1,
                "LOG_TRAJECTORY_3": 3.0,
                "LOG_TRAJECTORY_4": 4.0,
            }[catalog_key]
            actual_version = float(engine.header.version)
            if abs(actual_version - expected_version) > 0.001:
                raise PylinacAdapterError(
                    "PYLINAC_INPUT_FORMAT_INVALID",
                    f"Tệp Trajectory Log là phiên bản {actual_version:g}, không khớp bài đã chọn.",
                )
        import numpy as np

        axis_data = engine.axis_data
        mlc = axis_data.mlc
        snapshot_count = getattr(axis_data, "num_snapshots", None)
        if snapshot_count is None:
            snapshot_count = getattr(engine.header, "num_snapshots", None)
        metrics: dict[str, object] = {
            "log_version": _json_safe(engine.header.version),
            "snapshot_count": _json_safe(snapshot_count),
            "beam_hold_count": _json_safe(engine.num_beamholds),
            "mlc_leaf_count": _json_safe(mlc.num_leaves),
            "mlc_moving_leaf_count": _json_safe(mlc.num_moving_leaves),
            "mlc_rms_average": _json_safe(mlc.get_RMS_avg()),
            "mlc_rms_maximum": _json_safe(mlc.get_RMS_max()),
            "mlc_error_percentile": _json_safe(
                mlc.get_error_percentile(options.get("error_percentile", 95))
            ),
            "mlc_rms_percentile": _json_safe(
                mlc.get_RMS_percentile(options.get("rms_percentile", 95))
            ),
        }
        for axis_name in ("gantry", "collimator", "mu", "beam_hold"):
            axis = getattr(axis_data, axis_name, None)
            if axis is not None:
                summary = _axis_difference_summary(axis)
                if summary is not None:
                    metrics[f"{axis_name}_difference_maximum"] = _json_safe(summary)
        if options["calc_gamma"]:
            gamma = engine.fluence.gamma
            gamma_map = gamma.calc_map(
                doseTA=options["dose_tolerance"],
                distTA=options["distance_tolerance"],
                threshold=options["threshold"],
                resolution=options["resolution"],
                calc_individual_maps=options["calc_individual_maps"],
            )
            gamma_array = np.asarray(gamma_map, dtype=float)
            valid = gamma_array[np.isfinite(gamma_array)]
            metrics["gamma_map_shape"] = list(gamma_array.shape)
            metrics["gamma_valid_count"] = int(valid.size)
            metrics["gamma_maximum"] = _json_safe(float(np.max(valid))) if valid.size else None
            metrics["gamma_mean"] = _json_safe(float(np.mean(valid))) if valid.size else None
        overlay_bytes: bytes | None = None
        with tempfile.TemporaryDirectory(prefix="rt-connect-log-overlay-") as directory:
            overlay_path = Path(directory) / "log-mlc-phan-tich.png"
            mlc.save_mlc_error_hist(str(overlay_path))
            if overlay_path.exists():
                overlay_bytes = overlay_path.read_bytes()
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=type(engine).__name__,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-log-result.v1",
                "engine": "pylinac",
                "engine_class": type(engine).__name__,
                "metrics": metrics,
                "engine_passed": None,
                "parameters": _json_safe(parameters),
            },
            warnings=[],
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png" if overlay_bytes else None,
            overlay_filename="log-mlc-phan-tich.png" if overlay_bytes else None,
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể đọc nhật ký máy. Hãy kiểm tra đúng cặp tệp, phiên bản "
            "và dữ liệu rồi thử lại.",
        ) from exc


_CONTRIB_KEYS = {
    "CONTRIB_QUASAR_LIGHT_RAD_SCALING",
    "CONTRIB_JAW_ORTHOGONALITY",
}


def _contrib_parameters(
    catalog_key: str, parameters: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    if catalog_key == "CONTRIB_JAW_ORTHOGONALITY":
        if parameters:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_UNSUPPORTED",
                "Bài kiểm tra vuông góc hàm không nhận tham số bổ sung.",
            )
        return {}, {}
    allowed = {"normalize", "invert", "fwxm", "bb_edge_threshold_mm"}
    unknown = set(parameters) - allowed
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho mô-đun đóng góp Quasar.",
        )
    constructor: dict[str, object] = {
        "normalize": _bool(parameters, "normalize", True),
    }
    analysis: dict[str, object] = {
        "invert": _bool(parameters, "invert", False),
        "fwxm": _integer(parameters, "fwxm", minimum=1),
        "bb_edge_threshold_mm": _number(
            parameters, "bb_edge_threshold_mm", minimum=0.000001
        ),
    }
    return constructor, analysis


def _contrib_overlay(engine: Any) -> tuple[bytes | None, list[dict[str, object]]]:
    try:
        if hasattr(engine, "plot_analyzed_image"):
            plotted = engine.plot_analyzed_image(show=False)
            candidates: list[Any] = []
            if isinstance(plotted, tuple) and plotted:
                first = plotted[0]
                candidates.extend(first if isinstance(first, (list, tuple)) else [first])
            elif isinstance(plotted, (list, tuple)):
                candidates.extend(plotted)
            if candidates:
                return _save_figure(candidates[0]), []
            from matplotlib import pyplot as plt

            figure = plt.gcf()
            if figure.axes:
                return _save_figure(figure), []
        return None, []
    except Exception:
        return None, [
            {
                "code": "PYLINAC_OVERLAY_UNAVAILABLE",
                "message": "Pylinac đã trả kết quả nhưng không tạo được ảnh minh họa "
                "cho mô-đun đóng góp.",
            }
        ]
    finally:
        from matplotlib import pyplot as plt

        plt.close("all")


def _execute_contrib(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Mô-đun đóng góp chưa sẵn sàng trên máy chủ."
        )
    constructor, analysis = _contrib_parameters(catalog_key, parameters)
    try:
        engine = symbol(str(source_path), **constructor)
        engine.analyze(**analysis)
        if catalog_key == "CONTRIB_JAW_ORTHOGONALITY":
            raw_result = engine.results()
            result_source = "results"
        else:
            raw_result = engine.results_data(as_dict=True)
            result_source = "results_data"
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả mô-đun đóng góp không hợp lệ."
            )
        overlay_bytes, overlay_warnings = _contrib_overlay(engine)
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=type(engine).__name__,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-contrib-result.v1",
                "engine": "pylinac",
                "engine_class": type(engine).__name__,
                "source_tier": "PYLINAC_CONTRIB",
                "result_source": result_source,
                "metrics": result,
                "engine_passed": None,
                "parameters": _json_safe(parameters),
            },
            warnings=overlay_warnings,
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png" if overlay_bytes else None,
            overlay_filename=f"{catalog_key.lower()}-phan-tich.png" if overlay_bytes else None,
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích mô-đun đóng góp. Hãy kiểm tra ảnh và tham số rồi thử lại.",
        ) from exc


_NUCLEAR_KEYS = {
    "NUCLEAR_MCR",
    "NUCLEAR_PU",
    "NUCLEAR_COR",
    "NUCLEAR_TR",
    "NUCLEAR_SS",
    "NUCLEAR_FBR",
    "NUCLEAR_QR",
    "NUCLEAR_TU",
    "NUCLEAR_TC",
}


def _nuclear_ratio(parameters: dict[str, object], key: str) -> float:
    value = _number(parameters, key, minimum=0)
    if not 0 < value <= 1:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_INVALID", f"Tham số {key} phải lớn hơn 0 và không vượt quá 1."
        )
    return value


def _nuclear_parameters(
    catalog_key: str, parameters: dict[str, object]
) -> dict[str, object]:
    allowed_by_key = {
        "NUCLEAR_MCR": {"frame_duration"},
        "NUCLEAR_PU": {"ufov_ratio", "cfov_ratio", "window_size", "threshold"},
        "NUCLEAR_COR": set(),
        "NUCLEAR_TR": set(),
        "NUCLEAR_SS": {"activity_mbq", "nuclide"},
        "NUCLEAR_FBR": {"separation_mm", "roi_width_mm"},
        "NUCLEAR_QR": {"bar_widths", "roi_diameter_mm", "distance_from_center_mm"},
        "NUCLEAR_TU": {
            "first_frame",
            "last_frame",
            "ufov_ratio",
            "cfov_ratio",
            "center_ratio",
            "threshold",
            "window_size",
        },
        "NUCLEAR_TC": {
            "sphere_diameters_mm",
            "sphere_angles",
            "ufov_ratio",
            "search_window_px",
            "search_slices",
        },
    }
    allowed = allowed_by_key[catalog_key]
    unknown = set(parameters) - allowed
    if unknown:
        raise PylinacAdapterError(
            "PYLINAC_PARAMETER_UNSUPPORTED",
            "Có tham số không được hỗ trợ cho bài kiểm tra hạt nhân.",
        )
    normalized: dict[str, object] = {}
    if catalog_key == "NUCLEAR_MCR" and "frame_duration" in parameters:
        normalized["frame_duration"] = _number(parameters, "frame_duration", minimum=0.000001)
    elif catalog_key == "NUCLEAR_PU":
        if "ufov_ratio" in parameters:
            normalized["ufov_ratio"] = _nuclear_ratio(parameters, "ufov_ratio")
        if "cfov_ratio" in parameters:
            normalized["cfov_ratio"] = _nuclear_ratio(parameters, "cfov_ratio")
        if "window_size" in parameters:
            normalized["window_size"] = _integer(parameters, "window_size", minimum=1)
        if "threshold" in parameters:
            normalized["threshold"] = _nuclear_ratio(parameters, "threshold")
    elif catalog_key == "NUCLEAR_SS":
        normalized["activity_mbq"] = _number(parameters, "activity_mbq", minimum=0.000001)
        normalized["nuclide"] = _required_text(parameters, "nuclide")
        if normalized["nuclide"] not in {
            "Tc99m",
            "Y90",
            "I131",
            "Ga67",
            "In111",
            "Lu177",
        }:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Chỉ hỗ trợ các đồng vị có trong danh mục Pylinac."
            )
    elif catalog_key == "NUCLEAR_FBR":
        if "separation_mm" in parameters:
            normalized["separation_mm"] = _number(
                parameters, "separation_mm", minimum=0.000001
            )
        if "roi_width_mm" in parameters:
            normalized["roi_width_mm"] = _number(
                parameters, "roi_width_mm", minimum=0.000001
            )
    elif catalog_key == "NUCLEAR_QR":
        if "bar_widths" not in parameters:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Bài độ phân giải bốn góc cần bốn kích thước vạch."
            )
        bar_widths = _number_or_array(parameters, "bar_widths", minimum=0.000001)
        if not isinstance(bar_widths, tuple) or len(bar_widths) != 4:
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID",
                "Bài độ phân giải bốn góc cần đúng bốn kích thước vạch.",
            )
        normalized["bar_widths"] = bar_widths
        if "roi_diameter_mm" in parameters:
            normalized["roi_diameter_mm"] = _number(
                parameters, "roi_diameter_mm", minimum=0.000001
            )
        if "distance_from_center_mm" in parameters:
            normalized["distance_from_center_mm"] = _number(
                parameters, "distance_from_center_mm", minimum=0.000001
            )
    elif catalog_key == "NUCLEAR_TU":
        if "first_frame" in parameters:
            normalized["first_frame"] = _integer(parameters, "first_frame", minimum=0)
        if "last_frame" in parameters:
            normalized["last_frame"] = _integer(parameters, "last_frame", minimum=-1)
        for key in ("ufov_ratio", "cfov_ratio", "center_ratio", "threshold"):
            if key in parameters:
                normalized[key] = _nuclear_ratio(parameters, key)
        if "window_size" in parameters:
            normalized["window_size"] = _integer(parameters, "window_size", minimum=1)
    elif catalog_key == "NUCLEAR_TC":
        for key, expected_length in (("sphere_diameters_mm", 6), ("sphere_angles", 6)):
            if key not in parameters:
                continue
            values = _number_or_array(parameters, key)
            if not isinstance(values, tuple) or len(values) != expected_length:
                raise PylinacAdapterError(
                    "PYLINAC_PARAMETER_INVALID",
                    f"Tham số {key} phải có đúng {expected_length} giá trị.",
                )
            normalized[key] = values
        if "ufov_ratio" in parameters:
            normalized["ufov_ratio"] = _nuclear_ratio(parameters, "ufov_ratio")
        for key in ("search_window_px", "search_slices"):
            if key in parameters:
                normalized[key] = _integer(parameters, key, minimum=1)
    return normalized


def _nuclear_source_paths(source_path: Path) -> list[Path]:
    if not source_path.is_dir():
        return [source_path]
    paths = sorted(item for item in source_path.iterdir() if item.is_file())
    if not paths:
        raise PylinacAdapterError(
            "PYLINAC_INPUT_COUNT_INVALID", "Chưa có tệp dữ liệu hạt nhân để phân tích."
        )
    return paths


def _nuclear_overlay(engine: Any) -> tuple[bytes | None, list[dict[str, object]]]:
    if not hasattr(engine, "plot"):
        return None, []
    try:
        plotted = engine.plot(show=False)
        candidates: list[Any] = []
        if isinstance(plotted, tuple) and plotted:
            first = plotted[0]
            candidates.extend(first if isinstance(first, (list, tuple)) else [first])
        elif isinstance(plotted, (list, tuple)):
            candidates.extend(plotted)
        elif plotted is not None:
            candidates.append(plotted)
        if not candidates:
            return None, []
        return _save_figure(candidates[0]), []
    except Exception:
        return None, [
            {
                "code": "PYLINAC_OVERLAY_UNAVAILABLE",
                "message": "Pylinac đã trả kết quả nhưng không tạo được ảnh minh họa cho bài này.",
            }
        ]
    finally:
        from matplotlib import pyplot as plt

        plt.close("all")


def _execute_nuclear(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    symbol, _ = resolve_runtime_symbol(catalog_key)
    if symbol is None:
        raise PylinacAdapterError(
            "PYLINAC_RUNTIME_UNAVAILABLE", "Bộ phân tích hạt nhân chưa sẵn sàng trên máy chủ."
        )
    options = _nuclear_parameters(catalog_key, parameters)
    paths = _nuclear_source_paths(source_path)
    if catalog_key == "NUCLEAR_SS":
        if len(paths) not in {1, 2}:
            raise PylinacAdapterError(
                "PYLINAC_INPUT_COUNT_INVALID",
                "Bài độ nhạy đơn giản nhận một ảnh phantom và nền tùy chọn.",
            )
        engine = symbol(str(paths[0]), str(paths[1]) if len(paths) == 2 else None)
        nuclear_module = __import__("pylinac.nuclear", fromlist=["Nuclide"])
        nuclide_name = options["nuclide"]
        if not isinstance(nuclide_name, str):
            raise PylinacAdapterError(
                "PYLINAC_PARAMETER_INVALID", "Đồng vị hạt nhân không hợp lệ."
            )
        nuclide = getattr(nuclear_module.Nuclide, nuclide_name)
        engine.analyze(activity_mbq=options["activity_mbq"], nuclide=nuclide)
    else:
        if len(paths) != 1:
            raise PylinacAdapterError(
                "PYLINAC_INPUT_COUNT_INVALID", "Bài kiểm tra hạt nhân này nhận đúng một tệp ảnh."
            )
        engine = symbol(str(paths[0]))
        engine.analyze(**options)
    try:
        raw_result = engine.results_data(as_dict=True)
        result = _json_safe(raw_result)
        if not isinstance(result, dict):
            raise PylinacAdapterError(
                "PYLINAC_RESULT_INVALID", "Pylinac trả về kết quả hạt nhân không hợp lệ."
            )
        raw_warnings = result.get("warnings", [])
        warning_items = raw_warnings if isinstance(raw_warnings, list) else [raw_warnings]
        overlay_bytes, overlay_warnings = _nuclear_overlay(engine)
        engine_warnings: list[dict[str, object]] = [
            {"code": "PYLINAC_ENGINE_WARNING", "message": str(item)}
            for item in warning_items
            if item
        ]
        return PylinacExecutionResult(
            catalog_key=catalog_key,
            engine_class=type(engine).__name__,
            engine_version=PYLINAC_VERSION,
            package_fingerprint=package_fingerprint(),
            result_snapshot={
                "schema_version": "p7.pylinac-nuclear-result.v1",
                "engine": "pylinac",
                "engine_class": type(engine).__name__,
                "metrics": result,
                "engine_passed": None,
                "parameters": _json_safe(parameters),
            },
            warnings=engine_warnings + overlay_warnings,
            overlay_bytes=overlay_bytes,
            overlay_media_type="image/png" if overlay_bytes else None,
            overlay_filename=f"{catalog_key.lower()}-phan-tich.png" if overlay_bytes else None,
        )
    except PylinacAdapterError:
        raise
    except Exception as exc:
        raise PylinacAdapterError(
            "PYLINAC_EXECUTION_FAILED",
            "Pylinac không thể phân tích bài kiểm tra hạt nhân. Hãy kiểm tra tệp "
            "và tham số rồi thử lại.",
        ) from exc


def execute_pylinac(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
) -> PylinacExecutionResult:
    """Execute a registered capability; no custom-engine fallback is allowed."""

    binding = runtime_binding(catalog_key)
    if binding is None:
        raise PylinacAdapterError("PYLINAC_CAPABILITY_NOT_FOUND", "Không tìm thấy bài QA đã chọn.")
    if catalog_key in _CALIBRATION_KEYS:
        return _execute_calibration(catalog_key, parameters)
    if catalog_key in _LOG_KEYS:
        return _execute_log(catalog_key, source_path, parameters)
    if catalog_key in _NUCLEAR_KEYS:
        return _execute_nuclear(catalog_key, source_path, parameters)
    if catalog_key in _CONTRIB_KEYS:
        return _execute_contrib(catalog_key, source_path, parameters)
    if catalog_key == "PICKET_FENCE":
        return _execute_picket_fence(source_path, parameters)
    if catalog_key == "STARSHOT":
        return _execute_starshot(source_path, parameters)
    if catalog_key == "WINSTON_LUTZ":
        return _execute_winston_lutz(source_path, parameters)
    if catalog_key == "WINSTON_LUTZ_MULTI_TARGET":
        return _execute_winston_lutz_multi_target(source_path, parameters)
    if catalog_key in {"VMAT_DRGS", "VMAT_DRMLC", "VMAT_DRCS"}:
        return _execute_vmat(catalog_key, source_path, parameters)
    if catalog_key in {"FIELD_PROFILE_ANALYSIS", "FIELD_ANALYSIS_LEGACY"}:
        return _execute_field_profile(catalog_key, source_path, parameters)
    if catalog_key in {"CATPHAN_503", "CATPHAN_504", "CATPHAN_600", "CATPHAN_604", "CATPHAN_700"}:
        return _execute_catphan(catalog_key, source_path, parameters)
    if catalog_key in _ACR_KEYS:
        return _execute_acr(catalog_key, source_path, parameters)
    if catalog_key in _CHEESE_KEYS:
        return _execute_cheese(catalog_key, source_path, parameters)
    if catalog_key in _CT_PHANTOM_KEYS:
        return _execute_ct_phantom(catalog_key, source_path, parameters)
    if catalog_key.startswith("PLANAR_"):
        return _execute_planar(catalog_key, source_path, parameters)
    raise PylinacAdapterError(
        "PYLINAC_ADAPTER_NOT_READY",
        "Bộ giao diện cho bài QA này chưa được mở; chưa chạy bằng bộ tính khác.",
    )
