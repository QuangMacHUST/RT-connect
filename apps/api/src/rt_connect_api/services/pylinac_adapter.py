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
        from pylinac.winston_lutz import BBConfig  # type: ignore[import-untyped]

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
        from matplotlib import pyplot as plt  # type: ignore[import-untyped]

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
        from matplotlib import pyplot as plt  # type: ignore[import-untyped]

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
    if catalog_key == "WINSTON_LUTZ":
        return _execute_winston_lutz(source_path, parameters)
    if catalog_key == "WINSTON_LUTZ_MULTI_TARGET":
        return _execute_winston_lutz_multi_target(source_path, parameters)
    if catalog_key in {"VMAT_DRGS", "VMAT_DRMLC", "VMAT_DRCS"}:
        return _execute_vmat(catalog_key, source_path, parameters)
    if catalog_key in {"FIELD_PROFILE_ANALYSIS", "FIELD_ANALYSIS_LEGACY"}:
        return _execute_field_profile(catalog_key, source_path, parameters)
    raise PylinacAdapterError(
        "PYLINAC_ADAPTER_NOT_READY",
        "Bộ giao diện cho bài QA này chưa được mở; chưa chạy bằng bộ tính khác.",
    )
