"""Metadata-first validation for P6 DICOM artifacts and gamma measurements."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pydicom
from pydicom.dataset import Dataset

VALIDATOR_VERSION = "p6.2"
SUPPORTED_MODALITIES = {"CT", "RTDOSE", "RTSTRUCT", "RTPLAN"}


@dataclass(frozen=True)
class ValidationResult:
    result: str
    checks: list[dict[str, object]]
    warnings: list[dict[str, object]]
    errors: list[dict[str, object]]
    metadata: dict[str, object]


def _check(
    checks: list[dict[str, object]],
    code: str,
    status: str,
    message: str,
    field: str | None = None,
) -> None:
    checks.append({"code": code, "status": status, "field": field, "message": message})


def _result(checks: list[dict[str, object]], metadata: dict[str, object]) -> ValidationResult:
    warnings = [item for item in checks if item["status"] == "WARNING"]
    errors = [item for item in checks if item["status"] == "ERROR"]
    return ValidationResult(
        result="INVALID" if errors else "WARNING" if warnings else "VALID",
        checks=checks,
        warnings=warnings,
        errors=errors,
        metadata=metadata,
    )


def _value(dataset: Dataset, name: str) -> Any:
    return getattr(dataset, name, None)


def _string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive_numbers(value: Any) -> list[float] | None:
    if value is None:
        return None
    try:
        values = [_number(item) for item in value]
    except TypeError:
        return None
    if not values or any(item is None or item <= 0 for item in values):
        return None
    return [item for item in values if item is not None]


def _uid_metadata(dataset: Dataset) -> dict[str, object]:
    """Return only linkage metadata; patient identifiers are intentionally excluded."""

    return {
        "modality": _string(_value(dataset, "Modality")),
        "sop_class_uid": _string(_value(dataset, "SOPClassUID")),
        "sop_instance_uid": _string(_value(dataset, "SOPInstanceUID")),
        "study_instance_uid": _string(_value(dataset, "StudyInstanceUID")),
        "series_instance_uid": _string(_value(dataset, "SeriesInstanceUID")),
        "frame_of_reference_uid": _string(_value(dataset, "FrameOfReferenceUID")),
    }


def _common_dicom_checks(dataset: Dataset, checks: list[dict[str, object]]) -> dict[str, object]:
    metadata = _uid_metadata(dataset)
    modality = metadata["modality"]
    if modality not in SUPPORTED_MODALITIES:
        _check(
            checks,
            "DICOM_MODALITY_UNSUPPORTED",
            "ERROR",
            "Modality is not supported for P6 validation.",
            "Modality",
        )
    else:
        _check(
            checks,
            "DICOM_MODALITY_PRESENT",
            "PASS",
            "Supported DICOM modality is present.",
            "Modality",
        )
    for key, field in (
        ("sop_class_uid", "SOPClassUID"),
        ("sop_instance_uid", "SOPInstanceUID"),
        ("study_instance_uid", "StudyInstanceUID"),
        ("series_instance_uid", "SeriesInstanceUID"),
    ):
        if metadata[key]:
            _check(checks, f"DICOM_{field.upper()}_PRESENT", "PASS", f"{field} is present.", field)
        else:
            _check(
                checks, f"DICOM_{field.upper()}_MISSING", "ERROR", f"{field} is required.", field
            )
    if metadata["frame_of_reference_uid"]:
        _check(
            checks,
            "DICOM_FRAME_OF_REFERENCE_PRESENT",
            "PASS",
            "Frame of Reference UID is present.",
            "FrameOfReferenceUID",
        )
    elif modality in SUPPORTED_MODALITIES:
        _check(
            checks,
            "DICOM_FRAME_OF_REFERENCE_MISSING",
            "ERROR",
            "Frame of Reference UID is required for spatial linkage.",
            "FrameOfReferenceUID",
        )
    return metadata


def _validate_ct(
    dataset: Dataset, checks: list[dict[str, object]], metadata: dict[str, object]
) -> None:
    rows = _value(dataset, "Rows")
    columns = _value(dataset, "Columns")
    if not isinstance(rows, int) or rows <= 0 or not isinstance(columns, int) or columns <= 0:
        _check(
            checks,
            "CT_GRID_INVALID",
            "ERROR",
            "CT Rows and Columns must be positive integers.",
            "Rows/Columns",
        )
    else:
        metadata["grid"] = {"rows": rows, "columns": columns}
        _check(checks, "CT_GRID_VALID", "PASS", "CT grid dimensions are valid.", "Rows/Columns")
    spacing = _positive_numbers(_value(dataset, "PixelSpacing"))
    if spacing is None or len(spacing) != 2:
        _check(
            checks,
            "CT_PIXEL_SPACING_INVALID",
            "ERROR",
            "CT PixelSpacing must contain two positive values.",
            "PixelSpacing",
        )
    else:
        metadata["pixel_spacing_mm"] = spacing
        _check(
            checks, "CT_PIXEL_SPACING_VALID", "PASS", "CT PixelSpacing is valid.", "PixelSpacing"
        )
    if (
        _value(dataset, "ImagePositionPatient") is None
        or _value(dataset, "ImageOrientationPatient") is None
    ):
        _check(
            checks,
            "CT_GEOMETRY_INCOMPLETE",
            "ERROR",
            "CT ImagePositionPatient and ImageOrientationPatient are required.",
            "geometry",
        )
    else:
        _check(checks, "CT_GEOMETRY_PRESENT", "PASS", "CT image geometry is present.", "geometry")


def _validate_rtdose(
    dataset: Dataset, checks: list[dict[str, object]], metadata: dict[str, object]
) -> None:
    rows = _value(dataset, "Rows")
    columns = _value(dataset, "Columns")
    frames_value = _value(dataset, "NumberOfFrames")
    frames = frames_value if isinstance(frames_value, int) else 0
    if (
        not isinstance(rows, int)
        or rows <= 0
        or not isinstance(columns, int)
        or columns <= 0
        or not isinstance(frames, int)
        or frames <= 0
    ):
        _check(
            checks,
            "RTDOSE_GRID_INVALID",
            "ERROR",
            "RTDOSE grid dimensions must be positive integers.",
            "Rows/Columns/NumberOfFrames",
        )
    else:
        metadata["grid"] = {"rows": rows, "columns": columns, "frames": frames}
        _check(
            checks,
            "RTDOSE_GRID_VALID",
            "PASS",
            "RTDOSE grid dimensions are valid.",
            "Rows/Columns/NumberOfFrames",
        )
    spacing = _positive_numbers(_value(dataset, "PixelSpacing"))
    if spacing is None or len(spacing) != 2:
        _check(
            checks,
            "RTDOSE_PIXEL_SPACING_INVALID",
            "ERROR",
            "RTDOSE PixelSpacing must contain two positive values.",
            "PixelSpacing",
        )
    else:
        metadata["pixel_spacing_mm"] = spacing
        _check(
            checks,
            "RTDOSE_PIXEL_SPACING_VALID",
            "PASS",
            "RTDOSE PixelSpacing is valid.",
            "PixelSpacing",
        )
    offsets = _value(dataset, "GridFrameOffsetVector")
    if offsets is None:
        _check(
            checks,
            "RTDOSE_GRID_OFFSETS_MISSING",
            "ERROR",
            "GridFrameOffsetVector is required for RTDOSE geometry.",
            "GridFrameOffsetVector",
        )
    else:
        try:
            values = [_number(item) for item in offsets]
        except TypeError:
            values = None
        valid_values = values is not None and all(item is not None for item in values)
        numeric_values = [item for item in values if item is not None] if values else []
        if (
            not valid_values
            or len(numeric_values) != frames
            or numeric_values != sorted(numeric_values)
        ):
            _check(
                checks,
                "RTDOSE_GRID_OFFSETS_INVALID",
                "ERROR",
                "GridFrameOffsetVector must be finite, monotonic and match NumberOfFrames.",
                "GridFrameOffsetVector",
            )
        else:
            metadata["grid_frame_offset_vector_mm"] = numeric_values
            _check(
                checks,
                "RTDOSE_GRID_OFFSETS_VALID",
                "PASS",
                "RTDOSE frame offsets are valid.",
                "GridFrameOffsetVector",
            )
    image_position = _value(dataset, "ImagePositionPatient")
    image_orientation = _value(dataset, "ImageOrientationPatient")
    try:
        position_values = [_number(item) for item in image_position] if image_position else None
        orientation_values = (
            [_number(item) for item in image_orientation] if image_orientation else None
        )
    except TypeError:
        position_values = None
        orientation_values = None
    if (
        position_values is None
        or len(position_values) != 3
        or any(item is None for item in position_values)
        or orientation_values is None
        or len(orientation_values) != 6
        or any(item is None for item in orientation_values)
    ):
        _check(
            checks,
            "RTDOSE_GEOMETRY_INVALID",
            "ERROR",
            "RTDOSE ImagePositionPatient and ImageOrientationPatient are required and finite.",
            "geometry",
        )
    else:
        metadata["image_position_patient"] = position_values
        metadata["image_orientation_patient"] = orientation_values
        _check(
            checks,
            "RTDOSE_GEOMETRY_VALID",
            "PASS",
            "RTDOSE patient geometry is present.",
            "geometry",
        )
    scaling = _number(_value(dataset, "DoseGridScaling"))
    if scaling is None or scaling <= 0:
        _check(
            checks,
            "RTDOSE_DOSE_GRID_SCALING_INVALID",
            "ERROR",
            "DoseGridScaling must be finite and positive.",
            "DoseGridScaling",
        )
    else:
        metadata["dose_grid_scaling"] = scaling
        _check(
            checks,
            "RTDOSE_DOSE_GRID_SCALING_VALID",
            "PASS",
            "DoseGridScaling is valid.",
            "DoseGridScaling",
        )
    dose_units = _string(_value(dataset, "DoseUnits"))
    if dose_units != "GY":
        _check(
            checks,
            "RTDOSE_DOSE_UNITS_UNSUPPORTED",
            "ERROR",
            "DICOM RTDOSE DoseUnits must be GY for the supported physical-dose profile.",
            "DoseUnits",
        )
    else:
        metadata["dose_units"] = dose_units
        _check(checks, "RTDOSE_DOSE_UNITS_VALID", "PASS", "DoseUnits is supported.", "DoseUnits")
    if _value(dataset, "DoseType") is None:
        _check(
            checks,
            "RTDOSE_DOSE_TYPE_MISSING",
            "WARNING",
            "DoseType is absent; confirm interpretation before analysis.",
            "DoseType",
        )
    if _value(dataset, "DoseSummationType") is None:
        _check(
            checks,
            "RTDOSE_SUMMATION_TYPE_MISSING",
            "WARNING",
            "DoseSummationType is absent; confirm intended summation.",
            "DoseSummationType",
        )
    if not _value(dataset, "ReferencedRTPlanSequence"):
        _check(
            checks,
            "RTDOSE_REFERENCED_PLAN_MISSING",
            "WARNING",
            "No referenced RTPLAN was found in this upload.",
            "ReferencedRTPlanSequence",
        )
    frame_uid = metadata.get("frame_of_reference_uid")
    if not isinstance(frame_uid, str) or not frame_uid.strip():
        _check(
            checks,
            "RTDOSE_FRAME_OF_REFERENCE_MISSING",
            "ERROR",
            "RTDOSE FrameOfReferenceUID is required for Gamma/DVH alignment.",
            "FrameOfReferenceUID",
        )
    else:
        dimension = 3 if isinstance(frames, int) and frames > 1 else 2
        metadata["coordinate_frame"] = {
            "basis": "PATIENT_LPS",
            "frame_id": frame_uid.strip(),
            "frame_of_reference_uid": frame_uid.strip(),
            "axis_order": ["z", "y", "x"] if dimension == 3 else ["y", "x"],
        }
        _check(
            checks,
            "RTDOSE_COORDINATE_FRAME_VALID",
            "PASS",
            "RTDOSE patient coordinate frame is identified by FrameOfReferenceUID.",
            "FrameOfReferenceUID",
        )


def _validate_rtstruct(
    dataset: Dataset, checks: list[dict[str, object]], metadata: dict[str, object]
) -> None:
    rois = _value(dataset, "StructureSetROISequence")
    if not rois:
        _check(
            checks,
            "RTSTRUCT_ROI_SEQUENCE_MISSING",
            "ERROR",
            "RTSTRUCT must contain StructureSetROISequence.",
            "StructureSetROISequence",
        )
        return
    numbers = [getattr(item, "ROINumber", None) for item in rois]
    if any(not isinstance(number, int) for number in numbers) or len(set(numbers)) != len(numbers):
        _check(
            checks,
            "RTSTRUCT_ROI_NUMBERS_INVALID",
            "ERROR",
            "RTSTRUCT ROI numbers must be present and unique.",
            "ROINumber",
        )
    else:
        metadata["roi_count"] = len(numbers)
        _check(
            checks,
            "RTSTRUCT_ROI_NUMBERS_VALID",
            "PASS",
            "RTSTRUCT ROI numbers are unique.",
            "ROINumber",
        )
    contour_count = 0
    for contour in _value(dataset, "ROIContourSequence") or []:
        for item in getattr(contour, "ContourSequence", []) or []:
            points = getattr(item, "ContourData", [])
            if len(points) % 3 != 0 or any(_number(point) is None for point in points):
                _check(
                    checks,
                    "RTSTRUCT_CONTOUR_INVALID",
                    "ERROR",
                    "RTSTRUCT contour coordinates must be finite XYZ triples.",
                    "ContourData",
                )
            else:
                contour_count += 1
    if contour_count == 0:
        _check(
            checks,
            "RTSTRUCT_CONTOURS_EMPTY",
            "WARNING",
            "No contour geometry was found in the upload.",
            "ROIContourSequence",
        )
    else:
        metadata["contour_count"] = contour_count
        _check(
            checks,
            "RTSTRUCT_CONTOURS_VALID",
            "PASS",
            "RTSTRUCT contour coordinates are valid.",
            "ContourData",
        )
    if not _value(dataset, "ReferencedFrameOfReferenceSequence"):
        _check(
            checks,
            "RTSTRUCT_REFERENCES_MISSING",
            "ERROR",
            "RTSTRUCT must reference its Frame of Reference and image series.",
            "ReferencedFrameOfReferenceSequence",
        )


def _validate_rtplan(
    dataset: Dataset, checks: list[dict[str, object]], metadata: dict[str, object]
) -> None:
    fraction_groups = _value(dataset, "FractionGroupSequence")
    beams = _value(dataset, "BeamSequence")
    if not fraction_groups:
        _check(
            checks,
            "RTPLAN_FRACTION_GROUP_MISSING",
            "ERROR",
            "RTPLAN must contain FractionGroupSequence.",
            "FractionGroupSequence",
        )
    else:
        metadata["fraction_group_count"] = len(fraction_groups)
        _check(
            checks,
            "RTPLAN_FRACTION_GROUP_PRESENT",
            "PASS",
            "RTPLAN fraction groups are present.",
            "FractionGroupSequence",
        )
    if not beams:
        _check(
            checks,
            "RTPLAN_BEAM_SEQUENCE_MISSING",
            "ERROR",
            "RTPLAN must contain BeamSequence.",
            "BeamSequence",
        )
    else:
        numbers = [getattr(item, "BeamNumber", None) for item in beams]
        if any(not isinstance(number, int) for number in numbers) or len(set(numbers)) != len(
            numbers
        ):
            _check(
                checks,
                "RTPLAN_BEAM_NUMBERS_INVALID",
                "ERROR",
                "RTPLAN beam numbers must be present and unique.",
                "BeamNumber",
            )
        else:
            metadata["beam_count"] = len(numbers)
            _check(
                checks,
                "RTPLAN_BEAM_SEQUENCE_VALID",
                "PASS",
                "RTPLAN beam numbers are unique.",
                "BeamNumber",
            )
    if not _value(dataset, "RTPlanLabel"):
        _check(checks, "RTPLAN_LABEL_MISSING", "WARNING", "RTPlanLabel is absent.", "RTPlanLabel")


def validate_dicom(path: Path) -> ValidationResult:
    checks: list[dict[str, object]] = []
    try:
        dataset = pydicom.dcmread(path, stop_before_pixels=True, force=False)
    except Exception:
        _check(checks, "INVALID_DICOM", "ERROR", "The file is not a readable DICOM dataset.")
        return _result(checks, {})
    metadata = _common_dicom_checks(dataset, checks)
    modality = metadata.get("modality")
    if modality == "CT":
        _validate_ct(dataset, checks, metadata)
    elif modality == "RTDOSE":
        _validate_rtdose(dataset, checks, metadata)
    elif modality == "RTSTRUCT":
        _validate_rtstruct(dataset, checks, metadata)
    elif modality == "RTPLAN":
        _validate_rtplan(dataset, checks, metadata)
    return _result(checks, metadata)


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _validate_measurement_coordinate_frame(
    payload: Mapping[str, Any], shape: list[int] | None, checks: list[dict[str, object]]
) -> dict[str, object] | None:
    """Validate the physical frame required before a measurement enters Gamma.

    ``gamma.measurement.v1`` remains the file schema for compatibility, but a
    measurement without this block is not a usable PSQA comparison input.  It
    is deliberately reported as an ERROR so a new upload cannot be marked
    VALID while the engine would have to guess its physical basis.
    """

    raw_frame = payload.get("coordinate_frame")
    frame = _mapping(raw_frame)
    if frame is None:
        _check(
            checks,
            "MEASUREMENT_COORDINATE_FRAME_MISSING",
            "ERROR",
            "coordinate_frame is required before a measurement can enter Gamma.",
            "coordinate_frame",
        )
        return None

    basis = frame.get("basis")
    frame_id = frame.get("frame_id")
    valid = True
    if basis not in {"PATIENT_LPS", "IEC_PHANTOM"}:
        _check(
            checks,
            "MEASUREMENT_COORDINATE_FRAME_INVALID",
            "ERROR",
            "coordinate_frame.basis must be PATIENT_LPS or IEC_PHANTOM.",
            "coordinate_frame.basis",
        )
        valid = False
    if not isinstance(frame_id, str) or not frame_id.strip():
        _check(
            checks,
            "MEASUREMENT_COORDINATE_FRAME_INVALID",
            "ERROR",
            "coordinate_frame.frame_id is required.",
            "coordinate_frame.frame_id",
        )
        valid = False

    expected_axis: list[str] = (
        ["y", "x"] if shape is not None and len(shape) == 2 else ["z", "y", "x"]
    )
    axis_order = frame.get("axis_order")
    if axis_order != expected_axis:
        _check(
            checks,
            "MEASUREMENT_AXIS_ORDER_UNSUPPORTED",
            "ERROR",
            f"coordinate_frame.axis_order must be {expected_axis} for this grid.",
            "coordinate_frame.axis_order",
        )
        valid = False

    if basis == "PATIENT_LPS":
        frame_uid = frame.get("frame_of_reference_uid")
        if (
            not isinstance(frame_uid, str)
            or not frame_uid.strip()
            or not isinstance(frame_id, str)
            or frame_uid.strip() != frame_id.strip()
        ):
            _check(
                checks,
                "MEASUREMENT_FRAME_OF_REFERENCE_INVALID",
                "ERROR",
                "PATIENT_LPS requires frame_id equal to frame_of_reference_uid.",
                "coordinate_frame.frame_of_reference_uid",
            )
            valid = False

    transform = _mapping(frame.get("transform_to_reference"))
    if transform is None:
        _check(
            checks,
            "MEASUREMENT_TRANSFORM_MISSING",
            "ERROR",
            "transform_to_reference is required and must be explicit.",
            "coordinate_frame.transform_to_reference",
        )
        valid = False
    else:
        if transform.get("direction") != "SOURCE_TO_REFERENCE":
            _check(
                checks,
                "MEASUREMENT_TRANSFORM_INVALID",
                "ERROR",
                "transform_to_reference.direction must be SOURCE_TO_REFERENCE.",
                "coordinate_frame.transform_to_reference.direction",
            )
            valid = False
        if transform.get("units") != "mm":
            _check(
                checks,
                "MEASUREMENT_TRANSFORM_UNITS_INVALID",
                "ERROR",
                "transform_to_reference.units must be mm.",
                "coordinate_frame.transform_to_reference.units",
            )
            valid = False
        matrix = transform.get("matrix")
        flattened: list[float] = []
        if not isinstance(matrix, list) or len(matrix) != 4:
            valid = False
        else:
            for row in matrix:
                if not isinstance(row, list) or len(row) != 4:
                    valid = False
                    break
                numeric_row = [_number(item) for item in row]
                if any(item is None for item in numeric_row):
                    valid = False
                    break
                flattened.extend(item for item in numeric_row if item is not None)
        identity = [
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ]
        if len(flattened) != 16:
            _check(
                checks,
                "MEASUREMENT_TRANSFORM_INVALID",
                "ERROR",
                "transform_to_reference.matrix must be a finite 4x4 matrix.",
                "coordinate_frame.transform_to_reference.matrix",
            )
            valid = False
        elif any(
            abs(actual - expected) > 1e-9
            for actual, expected in zip(flattened, identity, strict=True)
        ):
            _check(
                checks,
                "MEASUREMENT_TRANSFORM_UNSUPPORTED",
                "ERROR",
                "Only an explicitly declared identity transform is supported by P8.",
                "coordinate_frame.transform_to_reference.matrix",
            )
            valid = False
        source = _mapping(transform.get("source"))
        if source is None or any(
            not isinstance(source.get(key), str) or not source.get(key, "").strip()
            for key in ("type", "version", "sha256")
        ):
            _check(
                checks,
                "MEASUREMENT_TRANSFORM_SOURCE_INVALID",
                "ERROR",
                "Transform source type, version and SHA-256 are required.",
                "coordinate_frame.transform_to_reference.source",
            )
            valid = False
        elif len(str(source.get("sha256"))) != 64 or any(
            character not in "0123456789abcdefABCDEF" for character in str(source.get("sha256"))
        ):
            _check(
                checks,
                "MEASUREMENT_TRANSFORM_SOURCE_INVALID",
                "ERROR",
                "Transform source.sha256 must be a hexadecimal SHA-256 string.",
                "coordinate_frame.transform_to_reference.source.sha256",
            )
            valid = False

    if not valid:
        return None
    source_metadata: dict[str, object] = {}
    if transform is not None:
        raw_source = transform.get("source")
        if isinstance(raw_source, Mapping):
            source_metadata = {str(key): value for key, value in raw_source.items()}
    sanitized: dict[str, object] = {
        "basis": str(basis),
        "frame_id": str(frame_id).strip(),
        "axis_order": expected_axis,
        "transform_to_reference": {
            "direction": "SOURCE_TO_REFERENCE",
            "units": "mm",
            "matrix": [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            "source": source_metadata,
        },
    }
    if basis == "PATIENT_LPS":
        sanitized["frame_of_reference_uid"] = str(frame.get("frame_of_reference_uid")).strip()
    _check(
        checks,
        "MEASUREMENT_COORDINATE_FRAME_VALID",
        "PASS",
        "Measurement coordinate basis, axis order and explicit transform are valid.",
        "coordinate_frame",
    )
    return sanitized


def validate_measurement(path: Path) -> ValidationResult:
    checks: list[dict[str, object]] = []
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _check(
            checks, "MEASUREMENT_JSON_INVALID", "ERROR", "Measurement file is not valid UTF-8 JSON."
        )
        return _result(checks, {})
    if not isinstance(payload, Mapping):
        _check(
            checks, "MEASUREMENT_ROOT_INVALID", "ERROR", "Measurement root must be a JSON object."
        )
        return _result(checks, {})
    if payload.get("schema_version") != "gamma.measurement.v1":
        _check(
            checks,
            "MEASUREMENT_SCHEMA_INVALID",
            "ERROR",
            "schema_version must be gamma.measurement.v1.",
            "schema_version",
        )
    else:
        _check(
            checks,
            "MEASUREMENT_SCHEMA_VALID",
            "PASS",
            "gamma.measurement.v1 schema is declared.",
            "schema_version",
        )
    dataset_id = payload.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        _check(
            checks,
            "MEASUREMENT_DATASET_ID_MISSING",
            "ERROR",
            "dataset_id is required.",
            "dataset_id",
        )
    units = _mapping(payload.get("units"))
    if (
        units is None
        or not isinstance(units.get("dose"), str)
        or not isinstance(units.get("position"), str)
    ):
        _check(
            checks,
            "MEASUREMENT_UNITS_MISSING",
            "ERROR",
            "units.dose and units.position are required.",
            "units",
        )
    else:
        _check(
            checks,
            "MEASUREMENT_UNITS_VALID",
            "PASS",
            "Dose and position units are explicit.",
            "units",
        )
    grid = _mapping(payload.get("grid"))
    shape = grid.get("shape") if grid else None
    spacing = grid.get("spacing_mm") if grid else None
    if (
        not isinstance(shape, list)
        or len(shape) not in {2, 3}
        or any(not isinstance(item, int) or item <= 0 for item in shape)
    ):
        _check(
            checks,
            "MEASUREMENT_GRID_INVALID",
            "ERROR",
            "grid.shape must contain two or three positive integers.",
            "grid.shape",
        )
    elif not isinstance(spacing, list) or len(spacing) != len(shape):
        _check(
            checks,
            "MEASUREMENT_SPACING_INVALID",
            "ERROR",
            "grid.spacing_mm must match shape with positive finite values.",
            "grid.spacing_mm",
        )
    else:
        numeric_spacing = [_number(item) for item in spacing]
        if any(item is None or item <= 0 for item in numeric_spacing if item is not None) or any(
            item is None for item in numeric_spacing
        ):
            _check(
                checks,
                "MEASUREMENT_SPACING_INVALID",
                "ERROR",
                "grid.spacing_mm must contain positive finite values.",
                "grid.spacing_mm",
            )
        else:
            _check(
                checks,
                "MEASUREMENT_GRID_VALID",
                "PASS",
                "Measurement grid shape and spacing are valid.",
                "grid",
            )
    values = _mapping(payload.get("values"))
    if values is None or not isinstance(values.get("encoding"), str):
        _check(
            checks, "MEASUREMENT_VALUES_MISSING", "ERROR", "values.encoding is required.", "values"
        )
    elif not values.get("object_key") and not isinstance(values.get("inline"), list):
        _check(
            checks,
            "MEASUREMENT_VALUES_REFERENCE_MISSING",
            "ERROR",
            "values must contain object_key or inline values.",
            "values",
        )
    else:
        _check(
            checks,
            "MEASUREMENT_VALUES_REFERENCE_VALID",
            "PASS",
            "Measurement values have an explicit encoding and source.",
            "values",
        )
    acquisition = _mapping(payload.get("acquisition"))
    if acquisition is None or not acquisition.get("detector") or not acquisition.get("measured_at"):
        _check(
            checks,
            "MEASUREMENT_ACQUISITION_INCOMPLETE",
            "WARNING",
            "Detector and measured_at should be recorded for traceability.",
            "acquisition",
        )
    source = _mapping(payload.get("source"))
    if (
        source is None
        or not isinstance(source.get("sha256"), str)
        or len(source.get("sha256", "")) != 64
    ):
        _check(
            checks,
            "MEASUREMENT_SOURCE_CHECKSUM_MISSING",
            "WARNING",
            "source.sha256 is recommended for byte-level provenance.",
            "source.sha256",
        )
    coordinate_frame = _validate_measurement_coordinate_frame(payload, shape, checks)
    metadata = {
        "schema_version": payload.get("schema_version"),
        "dataset_id": dataset_id,
        "data_type": payload.get("data_type"),
        "grid": dict(grid) if grid else {},
        "units": dict(units) if units else {},
    }
    if coordinate_frame is not None:
        metadata["coordinate_frame"] = coordinate_frame
    return _result(checks, metadata)


def validate_artifact(
    path: Path, artifact_type: str, media_type: str, filename: str
) -> ValidationResult:
    """Validate content without allowing filename/MIME hints to override type.

    ``artifact_type`` is part of the upload contract.  A browser may report a
    misleading MIME type and a file can be renamed, so content detection is
    only used to explain an obvious DICOM/JSON mismatch.  In particular, a
    JSON file declared as DICOM must never be routed through the measurement
    validator and later appear to be a usable RTDOSE input.
    """

    def mismatch(expected: str, detected: str) -> ValidationResult:
        check: dict[str, object] = {
            "code": "ARTIFACT_TYPE_MISMATCH",
            "status": "ERROR",
            "field": "artifact_type",
            "message": f"Artifact is declared as {expected} but its content is {detected}.",
        }
        return _result([check], {})

    def is_json_content() -> bool:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return False
        return True

    def is_dicom_content() -> bool:
        try:
            pydicom.dcmread(path, stop_before_pixels=True, force=False)
        except Exception:
            return False
        return True

    # Explicit declarations are authoritative.  MIME type and filename are
    # deliberately not allowed to change the validator selected here.
    if artifact_type == "DICOM":
        if is_json_content():
            return mismatch("DICOM", "JSON")
        return validate_dicom(path)
    if artifact_type in {"MEASUREMENT", "JSON"}:
        if is_dicom_content():
            return mismatch(artifact_type, "DICOM")
        return validate_measurement(path)
    if artifact_type in {"CSV", "IMAGE", "PDF"}:
        explicit_warning: dict[str, object] = {
            "code": "VALIDATION_NOT_APPLICABLE",
            "status": "WARNING",
            "field": None,
            "message": (
                "This explicitly declared artifact type is stored with provenance "
                "but has no P6 content validator yet."
            ),
        }
        return ValidationResult(
            result="WARNING",
            checks=[explicit_warning],
            warnings=[explicit_warning],
            errors=[],
            metadata={},
        )

    lower_name = filename.lower()
    if media_type == "application/json" or lower_name.endswith(".json"):
        return validate_measurement(path)
    if media_type == "application/dicom" or lower_name.endswith((".dcm", ".dicom")):
        return validate_dicom(path)
    warning_message = (
        "This artifact type is stored with provenance but has no P6 content validator yet."
    )
    warning: dict[str, object] = {
        "code": "VALIDATION_NOT_APPLICABLE",
        "status": "WARNING",
        "field": None,
        "message": warning_message,
    }
    return ValidationResult(
        result="WARNING", checks=[warning], warnings=[warning], errors=[], metadata={}
    )
