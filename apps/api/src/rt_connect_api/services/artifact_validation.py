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

VALIDATOR_VERSION = "p6.1"
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
    if dose_units not in {"GY", "CGY"}:
        _check(
            checks,
            "RTDOSE_DOSE_UNITS_INVALID",
            "ERROR",
            "DoseUnits must be GY or CGY.",
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
    metadata = {
        "schema_version": payload.get("schema_version"),
        "dataset_id": dataset_id,
        "data_type": payload.get("data_type"),
        "grid": dict(grid) if grid else {},
        "units": dict(units) if units else {},
    }
    return _result(checks, metadata)


def validate_artifact(
    path: Path, artifact_type: str, media_type: str, filename: str
) -> ValidationResult:
    lower_name = filename.lower()
    if (
        artifact_type == "MEASUREMENT"
        or media_type == "application/json"
        or lower_name.endswith(".json")
    ):
        return validate_measurement(path)
    if (
        artifact_type == "DICOM"
        or media_type == "application/dicom"
        or lower_name.endswith((".dcm", ".dicom"))
    ):
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
