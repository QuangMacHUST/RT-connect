"""Deterministic DICOM RT Dose/RT Structure Set DVH calculations.

The P17 engine deliberately has no database, HTTP or object-storage knowledge.
The API layer resolves organization/case scope and pins source checksums before
calling this module.  This separation makes the geometry and numerical rules
usable from focused tests as well as from the deployed service.

The supported profile is a physical-dose DVH on an RTDOSE grid.  RTSTRUCT
contours are transformed in patient LPS coordinates using the dose
ImageOrientationPatient, ImagePositionPatient and GridFrameOffsetVector.  A
single structure may contain disjoint polygons and holes; polygons are
rasterised with even-odd parity so those cases do not depend on contour name
or winding direction.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import Dataset

DVH_ENGINE_KEY = "visual-dose.dvh"
DVH_ENGINE_VERSION = "p17-dvh-1.0.0"
DVH_SCHEMA_VERSION = "visual-dose-dvh.result.v1"
CT_PREVIEW_ENGINE_KEY = "visual-dose.ct-preview"
CT_PREVIEW_ENGINE_VERSION = "p17-ct-preview-1.0.0"
CT_PREVIEW_SCHEMA_VERSION = "visual-dose-ct-preview.v1"
DEFAULT_DX_PERCENTAGES = (2.0, 50.0, 95.0, 98.0)
DEFAULT_VX_DOSES_GY = (0.0, 20.0, 30.0, 40.0, 50.0)
DEFAULT_CT_PREVIEW_LIMIT = 65_536


class DVHEngineError(ValueError):
    """Stable, field-addressable failure from the P17 geometry/metric engine."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        details: list[dict[str, object]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.field = field
        self.details = details or ([] if field is None else [{"field": field, "message": message}])
        super().__init__(message)


def _finite(value: object, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise DVHEngineError("DICOM_GEOMETRY_INVALID", f"{field} must be numeric.", field=field)
    try:
        converted = float(str(value))
    except (TypeError, ValueError) as exc:
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID", f"{field} must be numeric.", field=field
        ) from exc
    if not math.isfinite(converted) or (positive and converted <= 0):
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            f"{field} must be finite and valid.",
            field=field,
        )
    return converted


def _vector(value: object, field: str, length: int, *, positive: bool = False) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) != length:
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            f"{field} must contain exactly {length} values.",
            field=field,
        )
    return tuple(
        _finite(item, f"{field}[{index}]", positive=positive) for index, item in enumerate(value)
    )


def _string(value: object, field: str) -> str:
    if value is None:
        raise DVHEngineError("DICOM_CAPABILITY_UNSUPPORTED", f"{field} is required.", field=field)
    text = str(value).strip()
    if not text:
        raise DVHEngineError("DICOM_CAPABILITY_UNSUPPORTED", f"{field} is required.", field=field)
    return text


def _canonical_sha256(value: object) -> str:
    try:
        payload = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DVHEngineError(
            "DVH_RESULT_NONFINITE", "The DVH result contains unsupported JSON data."
        ) from exc
    return hashlib.sha256(payload).hexdigest()


def _continuous_frame_indices(
    normal_mm: np.ndarray,
    offsets_mm: tuple[float, ...],
    slice_thickness_mm: tuple[float, ...],
) -> np.ndarray:
    """Map normal distances to continuous frame coordinates without clamping."""

    normal = np.asarray(normal_mm, dtype=np.float64)
    offsets = np.asarray(offsets_mm, dtype=np.float64)
    if len(offsets) == 1:
        return np.asarray(
            (normal - offsets[0]) / float(slice_thickness_mm[0]), dtype=np.float64
        )
    frame = np.interp(normal, offsets, np.arange(len(offsets), dtype=np.float64))
    below = normal < offsets[0]
    above = normal > offsets[-1]
    frame[below] = (normal[below] - offsets[0]) / float(slice_thickness_mm[0])
    frame[above] = (len(offsets) - 1) + (
        (normal[above] - offsets[-1]) / float(slice_thickness_mm[-1])
    )
    return frame


def request_fingerprint(snapshot: Mapping[str, object]) -> str:
    """Create a deterministic idempotency fingerprint for a DVH request."""

    return _canonical_sha256(dict(snapshot))


@dataclass(frozen=True)
class DoseGeometry:
    """Patient-coordinate geometry for one RTDOSE voxel grid."""

    shape: tuple[int, int, int]
    row_cosine: tuple[float, float, float]
    column_cosine: tuple[float, float, float]
    normal_cosine: tuple[float, float, float]
    origin_mm: tuple[float, float, float]
    pixel_spacing_mm: tuple[float, float]
    offsets_mm: tuple[float, ...]
    slice_thickness_mm: tuple[float, ...]
    frame_of_reference_uid: str
    dose_units: str

    @property
    def oblique(self) -> bool:
        return not (
            np.allclose(self.row_cosine, (1.0, 0.0, 0.0), atol=1e-5, rtol=0)
            and np.allclose(self.column_cosine, (0.0, 1.0, 0.0), atol=1e-5, rtol=0)
        )

    @property
    def voxel_volume_cc(self) -> float:
        row_mm, column_mm = self.pixel_spacing_mm
        return row_mm * column_mm * float(np.mean(self.slice_thickness_mm)) / 1000.0

    def world_to_indices(self, points_mm: np.ndarray) -> np.ndarray:
        """Project patient LPS points to ``(frame,row,column)`` coordinates."""

        continuous = self.world_to_continuous_indices(points_mm)
        offsets = np.asarray(self.offsets_mm, dtype=np.float64)
        frame = np.asarray(
            [int(np.argmin(np.abs(offsets - value))) for value in continuous[:, 3]],
            dtype=np.float64,
        )
        result = continuous.copy()
        result[:, 0] = frame
        return result

    def world_to_continuous_indices(self, points_mm: np.ndarray) -> np.ndarray:
        """Project patient LPS points to continuous ``(frame,row,column,normal)``."""

        points = np.asarray(points_mm, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3:
            raise DVHEngineError(
                "DICOM_GEOMETRY_INVALID",
                "Patient coordinates must be an N by 3 array.",
                field="patient_coordinates",
            )
        relative = points - np.asarray(self.origin_mm, dtype=np.float64)
        # DICOM stores the direction of the first row (columns) first and
        # the direction of the first column (rows) second.  PixelSpacing is
        # ordered row spacing, then column spacing.
        column = relative @ np.asarray(self.row_cosine, dtype=np.float64)
        row = relative @ np.asarray(self.column_cosine, dtype=np.float64)
        normal = relative @ np.asarray(self.normal_cosine, dtype=np.float64)
        return np.column_stack(
            (
                _continuous_frame_indices(
                    normal,
                    self.offsets_mm,
                    self.slice_thickness_mm,
                ),
                row / self.pixel_spacing_mm[0],
                column / self.pixel_spacing_mm[1],
                normal,
            )
        )

    def summary(self) -> dict[str, object]:
        return {
            "shape": list(self.shape),
            "row_cosine": list(self.row_cosine),
            "column_cosine": list(self.column_cosine),
            "normal_cosine": list(self.normal_cosine),
            "origin_mm": list(self.origin_mm),
            "pixel_spacing_mm": list(self.pixel_spacing_mm),
            "offsets_mm": list(self.offsets_mm),
            "slice_thickness_mm": list(self.slice_thickness_mm),
            "frame_of_reference_uid": self.frame_of_reference_uid,
            "dose_units": self.dose_units,
            "oblique": self.oblique,
            "voxel_volume_cc_mean": self.voxel_volume_cc,
        }


@dataclass(frozen=True)
class DoseVolume:
    values_gy: np.ndarray
    geometry: DoseGeometry
    dose_type: str | None
    summation_type: str | None


@dataclass(frozen=True)
class CTGeometry:
    """Patient-coordinate geometry for one single-file CT image volume."""

    shape: tuple[int, int, int]
    row_cosine: tuple[float, float, float]
    column_cosine: tuple[float, float, float]
    normal_cosine: tuple[float, float, float]
    origin_mm: tuple[float, float, float]
    pixel_spacing_mm: tuple[float, float]
    offsets_mm: tuple[float, ...]
    slice_thickness_mm: tuple[float, ...]
    frame_of_reference_uid: str
    photometric_interpretation: str

    def world_to_continuous_indices(self, points_mm: np.ndarray) -> np.ndarray:
        points = np.asarray(points_mm, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3:
            raise DVHEngineError(
                "DICOM_GEOMETRY_INVALID",
                "Patient coordinates must be an N by 3 array.",
                field="patient_coordinates",
            )
        relative = points - np.asarray(self.origin_mm, dtype=np.float64)
        column = relative @ np.asarray(self.row_cosine, dtype=np.float64)
        row = relative @ np.asarray(self.column_cosine, dtype=np.float64)
        normal = relative @ np.asarray(self.normal_cosine, dtype=np.float64)
        return np.column_stack(
            (
                _continuous_frame_indices(
                    normal,
                    self.offsets_mm,
                    self.slice_thickness_mm,
                ),
                row / self.pixel_spacing_mm[0],
                column / self.pixel_spacing_mm[1],
                normal,
            )
        )

    def summary(self) -> dict[str, object]:
        return {
            "shape": list(self.shape),
            "row_cosine": list(self.row_cosine),
            "column_cosine": list(self.column_cosine),
            "normal_cosine": list(self.normal_cosine),
            "origin_mm": list(self.origin_mm),
            "pixel_spacing_mm": list(self.pixel_spacing_mm),
            "offsets_mm": list(self.offsets_mm),
            "slice_thickness_mm": list(self.slice_thickness_mm),
            "frame_of_reference_uid": self.frame_of_reference_uid,
            "photometric_interpretation": self.photometric_interpretation,
        }


@dataclass(frozen=True)
class CTVolume:
    values_hu: np.ndarray
    geometry: CTGeometry
    rescale_slope: float
    rescale_intercept: float
    window_center: float
    window_width: float
    warnings: list[dict[str, object]]


@dataclass(frozen=True)
class StructureROI:
    roi_number: int
    name: str
    contour_count: int
    mask: np.ndarray
    outside_contour_count: int
    contour_plane_count: int


@dataclass(frozen=True)
class DVHAnalysis:
    normalized_input: dict[str, object]
    result: dict[str, object]
    warnings: list[dict[str, object]]


def _parse_orientation(
    dataset: Dataset,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    orientation = _vector(
        getattr(dataset, "ImageOrientationPatient", None),
        "ImageOrientationPatient",
        6,
    )
    row = np.asarray(orientation[:3], dtype=np.float64)
    column = np.asarray(orientation[3:], dtype=np.float64)
    row_norm = float(np.linalg.norm(row))
    column_norm = float(np.linalg.norm(column))
    dot = float(np.dot(row, column))
    if abs(row_norm - 1.0) > 1e-4 or abs(column_norm - 1.0) > 1e-4 or abs(dot) > 1e-4:
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            "ImageOrientationPatient row and column vectors must be orthonormal.",
            field="ImageOrientationPatient",
        )
    normal = np.cross(row, column)
    normal_norm = float(np.linalg.norm(normal))
    if normal_norm < 1e-8:
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            "ImageOrientationPatient vectors do not define a plane.",
            field="ImageOrientationPatient",
        )
    normal /= normal_norm
    return (
        tuple(float(item) for item in row),
        tuple(float(item) for item in column),
        tuple(float(item) for item in normal),
    )


def _slice_thicknesses(
    offsets: tuple[float, ...], dataset: Dataset, explicit_mm: float | None
) -> tuple[float, ...]:
    if len(offsets) == 1:
        candidate = explicit_mm
        if candidate is None:
            raw = getattr(dataset, "SliceThickness", None)
            try:
                candidate = float(raw) if raw is not None else None
            except (TypeError, ValueError):
                candidate = None
        if candidate is None or not math.isfinite(candidate) or candidate <= 0:
            raise DVHEngineError(
                "DVH_SLICE_SPACING_UNAVAILABLE",
                "A single-frame RTDOSE needs a positive slice_thickness_mm or SliceThickness.",
                field="slice_thickness_mm",
            )
        return (float(candidate),)
    differences = np.diff(np.asarray(offsets, dtype=np.float64))
    if np.any(differences <= 0):
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            "GridFrameOffsetVector must be strictly increasing for a 3D DVH.",
            field="GridFrameOffsetVector",
        )
    thickness = np.empty(len(offsets), dtype=np.float64)
    thickness[0] = differences[0]
    thickness[-1] = differences[-1]
    if len(offsets) > 2:
        thickness[1:-1] = (differences[:-1] + differences[1:]) / 2.0
    return tuple(float(item) for item in thickness)


def load_rtdose(
    path: Path, *, max_voxels: int = 2_000_000, slice_thickness_mm: float | None = None
) -> DoseVolume:
    """Decode and validate an RTDOSE file, including dose scaling and geometry."""

    try:
        dataset = pydicom.dcmread(path, force=False)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED", "The RTDOSE file could not be decoded."
        ) from exc
    if getattr(dataset, "Modality", None) != "RTDOSE":
        raise DVHEngineError(
            "DVH_DOSE_ARTIFACT_INVALID",
            "The selected dose artifact is not an RTDOSE dataset.",
            field="dose_artifact_id",
        )
    try:
        raw_pixels = np.asarray(dataset.pixel_array, dtype=np.float64)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED",
            "The RTDOSE pixel data codec is not available or the pixel data is invalid.",
            field="PixelData",
        ) from exc
    if raw_pixels.ndim == 2:
        raw_pixels = raw_pixels[np.newaxis, ...]
    if raw_pixels.ndim != 3:
        raise DVHEngineError(
            "DVH_DOSE_ARTIFACT_INVALID",
            "RTDOSE pixel data must be a 2D or 3D grid.",
            field="PixelData",
        )
    rows = getattr(dataset, "Rows", None)
    columns = getattr(dataset, "Columns", None)
    frames = getattr(dataset, "NumberOfFrames", 1)
    if isinstance(frames, str):
        try:
            frames = int(frames)
        except ValueError as exc:
            raise DVHEngineError(
                "DVH_DOSE_ARTIFACT_INVALID", "NumberOfFrames is invalid.", field="NumberOfFrames"
            ) from exc
    if (
        isinstance(rows, bool)
        or not isinstance(rows, int)
        or rows <= 0
        or isinstance(columns, bool)
        or not isinstance(columns, int)
        or columns <= 0
        or isinstance(frames, bool)
        or not isinstance(frames, int)
        or frames <= 0
        or raw_pixels.shape != (frames, rows, columns)
    ):
        raise DVHEngineError(
            "DVH_DOSE_ARTIFACT_INVALID",
            "RTDOSE dimensions do not match the decoded pixel grid.",
            field="Rows/Columns/NumberOfFrames",
        )
    voxel_count = int(raw_pixels.size)
    if voxel_count > max_voxels:
        raise DVHEngineError(
            "DVH_RESOURCE_LIMIT",
            "The selected dose grid exceeds the configured DVH voxel limit.",
            field="dose_voxels",
            details=[
                {
                    "field": "dose_voxels",
                    "message": f"{voxel_count} voxels exceed limit {max_voxels}.",
                }
            ],
        )
    spacing = _vector(getattr(dataset, "PixelSpacing", None), "PixelSpacing", 2, positive=True)
    origin = _vector(getattr(dataset, "ImagePositionPatient", None), "ImagePositionPatient", 3)
    row_cosine, column_cosine, normal_cosine = _parse_orientation(dataset)
    raw_offsets = getattr(dataset, "GridFrameOffsetVector", None)
    offsets: tuple[float, ...]
    if raw_offsets is None:
        if frames != 1:
            raise DVHEngineError(
                "DICOM_GEOMETRY_INVALID",
                "GridFrameOffsetVector is required for a multi-frame RTDOSE.",
                field="GridFrameOffsetVector",
            )
        offsets = (0.0,)
    else:
        if frames == 1 and not isinstance(raw_offsets, (str, bytes, Sequence)):
            raw_offsets = (raw_offsets,)
        if isinstance(raw_offsets, (str, bytes)) or not isinstance(raw_offsets, Sequence):
            raise DVHEngineError(
                "DICOM_GEOMETRY_INVALID",
                "GridFrameOffsetVector must be a numeric sequence.",
                field="GridFrameOffsetVector",
            )
        offsets = tuple(
            _finite(item, f"GridFrameOffsetVector[{index}]")
            for index, item in enumerate(raw_offsets)
        )
        if len(offsets) != frames:
            raise DVHEngineError(
                "DICOM_GEOMETRY_INVALID",
                "GridFrameOffsetVector length must equal NumberOfFrames.",
                field="GridFrameOffsetVector",
            )
    thickness = _slice_thicknesses(offsets, dataset, slice_thickness_mm)
    dose_scaling = _finite(
        getattr(dataset, "DoseGridScaling", None), "DoseGridScaling", positive=True
    )
    dose_units = _string(getattr(dataset, "DoseUnits", None), "DoseUnits").upper()
    if dose_units != "GY":
        raise DVHEngineError(
            "DVH_DOSE_UNITS_UNSUPPORTED",
            "The P17 physical-dose profile requires DoseUnits=GY; units are never inferred.",
            field="DoseUnits",
        )
    values = raw_pixels * dose_scaling
    if np.any(~np.isfinite(values)) or np.any(values < 0):
        raise DVHEngineError(
            "DVH_DOSE_VALUES_INVALID",
            "RTDOSE scaled values must be finite and non-negative.",
            field="PixelData",
        )
    frame_uid = _string(getattr(dataset, "FrameOfReferenceUID", None), "FrameOfReferenceUID")
    geometry = DoseGeometry(
        shape=(frames, rows, columns),
        row_cosine=row_cosine,  # type: ignore[arg-type]
        column_cosine=column_cosine,  # type: ignore[arg-type]
        normal_cosine=normal_cosine,  # type: ignore[arg-type]
        origin_mm=origin,  # type: ignore[arg-type]
        pixel_spacing_mm=spacing,  # type: ignore[arg-type]
        offsets_mm=offsets,
        slice_thickness_mm=thickness,
        frame_of_reference_uid=frame_uid,
        dose_units=dose_units,
    )
    return DoseVolume(
        values_gy=values,
        geometry=geometry,
        dose_type=str(getattr(dataset, "DoseType", "")).strip() or None,
        summation_type=str(getattr(dataset, "DoseSummationType", "")).strip() or None,
    )


def _frame_uids(dataset: Dataset) -> set[str]:
    values: set[str] = set()
    direct = getattr(dataset, "FrameOfReferenceUID", None)
    if direct:
        values.add(str(direct).strip())
    for reference in getattr(dataset, "ReferencedFrameOfReferenceSequence", []) or []:
        value = getattr(reference, "FrameOfReferenceUID", None)
        if value:
            values.add(str(value).strip())
    return {item for item in values if item}


def list_structure_rois(path: Path) -> list[dict[str, object]]:
    """Return non-patient ROI descriptors for the UI input selector."""

    try:
        dataset = pydicom.dcmread(path, stop_before_pixels=True, force=False)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED", "The RTSTRUCT file could not be decoded."
        ) from exc
    if getattr(dataset, "Modality", None) != "RTSTRUCT":
        raise DVHEngineError(
            "DVH_STRUCTURE_ARTIFACT_INVALID", "The structure artifact is not RTSTRUCT."
        )
    sequence = getattr(dataset, "StructureSetROISequence", None) or []
    if not sequence:
        raise DVHEngineError(
            "DVH_STRUCTURE_ARTIFACT_INVALID", "RTSTRUCT contains no ROI definitions."
        )
    contour_counts: dict[int, int] = {}
    for roi_contour in getattr(dataset, "ROIContourSequence", []) or []:
        raw_number = getattr(roi_contour, "ReferencedROINumber", None)
        if raw_number is None:
            continue
        try:
            number = int(raw_number)
        except (TypeError, ValueError):
            continue
        contour_counts[number] = len(getattr(roi_contour, "ContourSequence", []) or [])
    result: list[dict[str, object]] = []
    seen: set[int] = set()
    for roi in sequence:
        try:
            number = int(roi.ROINumber)
        except (AttributeError, TypeError, ValueError) as exc:
            raise DVHEngineError(
                "DVH_STRUCTURE_ARTIFACT_INVALID", "RTSTRUCT ROI number is invalid."
            ) from exc
        if number in seen:
            raise DVHEngineError(
                "DVH_STRUCTURE_ARTIFACT_INVALID", "RTSTRUCT ROI numbers must be unique."
            )
        seen.add(number)
        name = str(getattr(roi, "ROIName", f"ROI {number}")).strip() or f"ROI {number}"
        result.append(
            {"roi_number": number, "name": name, "contour_count": contour_counts.get(number, 0)}
        )
    return result


def _rasterize_polygon(rows: int, columns: int, points: np.ndarray) -> np.ndarray:
    """Rasterise a polygon at pixel centres using vectorised even-odd parity."""

    x = points[:, 1]
    y = points[:, 0]
    grid_y, grid_x = np.indices((rows, columns), dtype=np.float64)
    inside = np.zeros((rows, columns), dtype=bool)
    previous = len(points) - 1
    for current in range(len(points)):
        x0, y0 = x[previous], y[previous]
        x1, y1 = x[current], y[current]
        crosses = (y0 > grid_y) != (y1 > grid_y)
        denominator = y1 - y0
        if abs(float(denominator)) > 1e-12:
            crossing_x = (x1 - x0) * (grid_y - y0) / denominator + x0
            inside ^= crosses & (grid_x < crossing_x)
        previous = current
    return inside


def _polygon_area(points: np.ndarray) -> float:
    return abs(
        float(
            np.dot(points[:, 1], np.roll(points[:, 0], 1))
            - np.dot(points[:, 0], np.roll(points[:, 1], 1))
        )
        / 2.0
    )


def _load_structure(path: Path, dose: DoseVolume, roi_number: int) -> StructureROI:
    try:
        dataset = pydicom.dcmread(path, stop_before_pixels=True, force=False)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED", "The RTSTRUCT file could not be decoded."
        ) from exc
    if getattr(dataset, "Modality", None) != "RTSTRUCT":
        raise DVHEngineError(
            "DVH_STRUCTURE_ARTIFACT_INVALID", "The selected structure artifact is not RTSTRUCT."
        )
    dose_frame = dose.geometry.frame_of_reference_uid
    structure_frames = _frame_uids(dataset)
    if not structure_frames or dose_frame not in structure_frames:
        raise DVHEngineError(
            "DICOM_FRAME_MISMATCH",
            "RTSTRUCT and RTDOSE do not share the selected Frame of Reference.",
            field="frame_of_reference_uid",
        )
    definitions = getattr(dataset, "StructureSetROISequence", None) or []
    selected_definition: Dataset | None = None
    for definition in definitions:
        try:
            number = int(definition.ROINumber)
        except (AttributeError, TypeError, ValueError) as exc:
            raise DVHEngineError(
                "DVH_STRUCTURE_ARTIFACT_INVALID", "RTSTRUCT ROI number is invalid."
            ) from exc
        if number == roi_number:
            if selected_definition is not None:
                raise DVHEngineError(
                    "DVH_STRUCTURE_ARTIFACT_INVALID", "RTSTRUCT ROI numbers must be unique."
                )
            selected_definition = definition
    if selected_definition is None:
        raise DVHEngineError(
            "DVH_EMPTY_STRUCTURE",
            "The selected ROI number is not present in RTSTRUCT.",
            field="roi_number",
        )
    name = (
        str(getattr(selected_definition, "ROIName", f"ROI {roi_number}")).strip()
        or f"ROI {roi_number}"
    )
    contours: list[Dataset] = []
    for roi_contour in getattr(dataset, "ROIContourSequence", []) or []:
        try:
            referenced_number = int(roi_contour.ReferencedROINumber)
        except (AttributeError, TypeError, ValueError):
            continue
        if referenced_number == roi_number:
            contours.extend(getattr(roi_contour, "ContourSequence", []) or [])
    if not contours:
        raise DVHEngineError(
            "DVH_EMPTY_STRUCTURE", "The selected ROI has no contour geometry.", field="roi_number"
        )
    mask = np.zeros(dose.geometry.shape, dtype=bool)
    outside_count = 0
    plane_count = 0
    rows, columns = dose.geometry.shape[1:]
    min_spacing = min(dose.geometry.pixel_spacing_mm)
    plane_tolerance = max(0.01, min_spacing * 0.75)
    for contour_index, contour in enumerate(contours, start=1):
        geometric_type = str(getattr(contour, "ContourGeometricType", "")).upper()
        if geometric_type not in {"CLOSED_PLANAR", "CLOSEDPLANAR_XOR"}:
            raise DVHEngineError(
                "DICOM_CAPABILITY_UNSUPPORTED",
                "Only CLOSED_PLANAR and CLOSEDPLANAR_XOR contours are supported.",
                field=f"contours[{contour_index}].ContourGeometricType",
            )
        raw_points = getattr(contour, "ContourData", None)
        if raw_points is None or len(raw_points) < 9 or len(raw_points) % 3 != 0:
            raise DVHEngineError(
                "CONTOUR_GEOMETRY_INVALID",
                "Each contour needs at least three finite XYZ points.",
                field=f"contours[{contour_index}].ContourData",
            )
        try:
            points_mm = np.asarray(
                [_finite(item, f"contours[{contour_index}].ContourData") for item in raw_points],
                dtype=np.float64,
            ).reshape((-1, 3))
        except DVHEngineError:
            raise
        projected = dose.geometry.world_to_indices(points_mm)
        frame = int(projected[0, 0])
        normal_distances = projected[:, 3]
        selected_offset = dose.geometry.offsets_mm[frame]
        if np.any(np.abs(normal_distances - selected_offset) > plane_tolerance):
            raise DVHEngineError(
                "CONTOUR_GEOMETRY_INVALID",
                "Contour points do not lie on one RTDOSE grid plane.",
                field=f"contours[{contour_index}].ContourData",
            )
        if not np.all(projected[:, 0] == frame):
            raise DVHEngineError(
                "CONTOUR_GEOMETRY_INVALID",
                "Contour points map to more than one dose plane.",
                field=f"contours[{contour_index}].ContourData",
            )
        points_index = projected[:, 1:3]
        if _polygon_area(points_index) <= 1e-8:
            raise DVHEngineError(
                "CONTOUR_GEOMETRY_INVALID",
                "Contour polygon area must be greater than zero.",
                field=f"contours[{contour_index}].ContourData",
            )
        # Pixel boundaries are at +/-0.5 around pixel centres.  A contour can
        # be valid but extend beyond the dose grid; keep its overlap for the
        # OVERLAP_ONLY policy and make that loss explicit in the result.
        if (
            np.any(points_index[:, 0] < -0.5)
            or np.any(points_index[:, 0] > rows - 0.5)
            or np.any(points_index[:, 1] < -0.5)
            or np.any(points_index[:, 1] > columns - 0.5)
        ):
            outside_count += 1
        if frame < 0 or frame >= dose.geometry.shape[0]:
            outside_count += 1
            continue
        mask[frame] ^= _rasterize_polygon(rows, columns, points_index)
        plane_count += 1
    if not np.any(mask):
        raise DVHEngineError(
            "DVH_EMPTY_STRUCTURE",
            "The selected ROI has no voxel overlap with the selected dose grid.",
            field="roi_number",
        )
    return StructureROI(
        roi_number=roi_number,
        name=name,
        contour_count=len(contours),
        mask=mask,
        outside_contour_count=outside_count,
        contour_plane_count=plane_count,
    )


def _positive_integer(value: object, field: str, *, default: int | None = None) -> int:
    if value is None and default is not None:
        return default
    if isinstance(value, bool):
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID", f"{field} must be a positive integer.", field=field
        )
    try:
        number = int(str(value))
    except (TypeError, ValueError) as exc:
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID", f"{field} must be a positive integer.", field=field
        ) from exc
    if number <= 0:
        raise DVHEngineError("DICOM_GEOMETRY_INVALID", f"{field} must be positive.", field=field)
    return number


def _first_numeric(value: object, field: str) -> float | None:
    if value is None:
        return None
    candidates: Sequence[object]
    if isinstance(value, (str, bytes)):
        candidates = (value,)
    elif isinstance(value, Sequence):
        candidates = value
    else:
        candidates = (value,)
    for candidate in candidates:
        try:
            number = float(str(candidate))
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            return number
    raise DVHEngineError(
        "DICOM_GEOMETRY_INVALID", f"{field} must contain a finite numeric value.", field=field
    )


def _ct_offsets(
    dataset: Dataset,
    frames: int,
    origin: tuple[float, float, float],
    normal_cosine: tuple[float, float, float],
) -> tuple[float, ...]:
    raw_offsets = getattr(dataset, "GridFrameOffsetVector", None)
    if raw_offsets is not None:
        if isinstance(raw_offsets, (str, bytes)) or not isinstance(raw_offsets, Sequence):
            raise DVHEngineError(
                "DICOM_GEOMETRY_INVALID",
                "CT GridFrameOffsetVector must be a numeric sequence.",
                field="GridFrameOffsetVector",
            )
        offsets = tuple(
            _finite(item, f"GridFrameOffsetVector[{index}]")
            for index, item in enumerate(raw_offsets)
        )
    else:
        per_frame = getattr(dataset, "PerFrameFunctionalGroupsSequence", None) or []
        positions: list[tuple[float, float, float]] = []
        if per_frame:
            if len(per_frame) != frames:
                raise DVHEngineError(
                    "DICOM_GEOMETRY_INVALID",
                    "PerFrameFunctionalGroupsSequence length must equal NumberOfFrames.",
                    field="PerFrameFunctionalGroupsSequence",
                )
            for index, group in enumerate(per_frame):
                plane_position = getattr(group, "PlanePositionSequence", None) or []
                if not plane_position:
                    raise DVHEngineError(
                        "DICOM_GEOMETRY_INVALID",
                        "Each CT frame needs PlanePositionSequence for slice navigation.",
                        field=f"PerFrameFunctionalGroupsSequence[{index}]",
                    )
                positions.append(
                    _vector(
                        getattr(plane_position[0], "ImagePositionPatient", None),
                        f"PerFrameFunctionalGroupsSequence[{index}].ImagePositionPatient",
                        3,
                    )  # type: ignore[arg-type]
                )
        if positions:
            offsets = tuple(
                float(
                    np.dot(
                        np.asarray(position, dtype=np.float64)
                        - np.asarray(origin, dtype=np.float64),
                        np.asarray(normal_cosine, dtype=np.float64),
                    )
                )
                for position in positions
            )
        elif frames == 1:
            offsets = (0.0,)
        else:
            spacing = _first_numeric(
                getattr(dataset, "SpacingBetweenSlices", None), "SpacingBetweenSlices"
            )
            if spacing is None:
                spacing = _first_numeric(getattr(dataset, "SliceThickness", None), "SliceThickness")
            if spacing is None or spacing <= 0:
                raise DVHEngineError(
                    "DVH_SLICE_SPACING_UNAVAILABLE",
                    (
                        "A multi-frame CT needs frame positions, SpacingBetweenSlices "
                        "or SliceThickness."
                    ),
                    field="SpacingBetweenSlices",
                )
            offsets = tuple(float(index * spacing) for index in range(frames))
    if len(offsets) != frames:
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            "CT slice offsets must match NumberOfFrames.",
            field="GridFrameOffsetVector",
        )
    if len(offsets) > 1 and np.any(np.diff(np.asarray(offsets, dtype=np.float64)) <= 0):
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            "CT slice offsets must be strictly increasing in frame order.",
            field="GridFrameOffsetVector",
        )
    return offsets


def _ct_slice_thicknesses(
    offsets: tuple[float, ...], dataset: Dataset
) -> tuple[tuple[float, ...], list[dict[str, object]]]:
    warnings: list[dict[str, object]] = []
    if len(offsets) == 1:
        thickness = _first_numeric(getattr(dataset, "SliceThickness", None), "SliceThickness")
        if thickness is None:
            thickness = _first_numeric(
                getattr(dataset, "SpacingBetweenSlices", None), "SpacingBetweenSlices"
            )
        if thickness is None or thickness <= 0:
            thickness = 1.0
            warnings.append(
                {
                    "code": "CT_SLICE_SPACING_DEFAULTED",
                    "field": "SliceThickness",
                    "message": (
                        "Single-slice CT has no positive slice spacing; 1 mm is used "
                        "for navigation only."
                    ),
                }
            )
        return (float(thickness),), warnings
    differences = np.diff(np.asarray(offsets, dtype=np.float64))
    thickness_values = np.empty(len(offsets), dtype=np.float64)
    thickness_values[0] = differences[0]
    thickness_values[-1] = differences[-1]
    if len(offsets) > 2:
        thickness_values[1:-1] = (differences[:-1] + differences[1:]) / 2.0
    return tuple(float(item) for item in thickness_values), warnings


def _ct_geometry_from_dataset(
    dataset: Dataset,
    dose: DoseVolume,
    *,
    max_pixels: int,
) -> tuple[CTGeometry, list[dict[str, object]]]:
    if getattr(dataset, "Modality", None) != "CT":
        raise DVHEngineError(
            "DVH_ANATOMY_ARTIFACT_INVALID", "The selected anatomy artifact is not CT."
        )
    frame = _string(getattr(dataset, "FrameOfReferenceUID", None), "FrameOfReferenceUID")
    if frame != dose.geometry.frame_of_reference_uid:
        raise DVHEngineError(
            "DICOM_FRAME_MISMATCH",
            "CT and RTDOSE do not share the selected Frame of Reference.",
            field="ct_frame_of_reference_uid",
        )
    rows = _positive_integer(getattr(dataset, "Rows", None), "Rows")
    columns = _positive_integer(getattr(dataset, "Columns", None), "Columns")
    frames = _positive_integer(
        getattr(dataset, "NumberOfFrames", None), "NumberOfFrames", default=1
    )
    pixel_count = frames * rows * columns
    if pixel_count > max_pixels:
        raise DVHEngineError(
            "DVH_RESOURCE_LIMIT",
            "The selected CT volume exceeds the configured preview pixel limit.",
            field="ct_pixels",
            details=[
                {
                    "field": "ct_pixels",
                    "message": f"{pixel_count} pixels exceed limit {max_pixels}.",
                }
            ],
        )
    spacing = _vector(getattr(dataset, "PixelSpacing", None), "CT.PixelSpacing", 2, positive=True)
    origin = _vector(getattr(dataset, "ImagePositionPatient", None), "CT.ImagePositionPatient", 3)
    row_cosine, column_cosine, normal_cosine = _parse_orientation(dataset)
    offsets = _ct_offsets(dataset, frames, origin, normal_cosine)  # type: ignore[arg-type]
    thickness, warnings = _ct_slice_thicknesses(offsets, dataset)
    photometric = str(getattr(dataset, "PhotometricInterpretation", "")).strip().upper()
    if photometric not in {"MONOCHROME1", "MONOCHROME2"}:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED",
            "CT preview supports MONOCHROME1 and MONOCHROME2 single-channel images only.",
            field="PhotometricInterpretation",
        )
    return (
        CTGeometry(
            shape=(frames, rows, columns),
            row_cosine=row_cosine,  # type: ignore[arg-type]
            column_cosine=column_cosine,  # type: ignore[arg-type]
            normal_cosine=normal_cosine,  # type: ignore[arg-type]
            origin_mm=origin,  # type: ignore[arg-type]
            pixel_spacing_mm=spacing,  # type: ignore[arg-type]
            offsets_mm=offsets,
            slice_thickness_mm=thickness,
            frame_of_reference_uid=frame,
            photometric_interpretation=photometric,
        ),
        warnings,
    )


def load_ct_volume(path: Path, dose: DoseVolume, *, max_pixels: int = 8_000_000) -> CTVolume:
    """Decode a bounded single-file CT volume and convert it to Hounsfield units."""

    try:
        dataset = pydicom.dcmread(path, force=False)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED", "The CT file could not be decoded."
        ) from exc
    geometry, warnings = _ct_geometry_from_dataset(dataset, dose, max_pixels=max_pixels)
    samples = _positive_integer(
        getattr(dataset, "SamplesPerPixel", None), "SamplesPerPixel", default=1
    )
    if samples != 1:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED",
            "CT preview supports one sample per pixel only.",
            field="SamplesPerPixel",
        )
    try:
        raw_pixels = np.asarray(dataset.pixel_array, dtype=np.float64)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED",
            "The CT pixel data codec is not available or the pixel data is invalid.",
            field="PixelData",
        ) from exc
    if raw_pixels.ndim == 2:
        raw_pixels = raw_pixels[np.newaxis, ...]
    if raw_pixels.ndim != 3 or raw_pixels.shape != geometry.shape:
        raise DVHEngineError(
            "DVH_ANATOMY_ARTIFACT_INVALID",
            "CT pixel data dimensions do not match Rows/Columns/NumberOfFrames.",
            field="Rows/Columns/NumberOfFrames",
        )
    slope = _first_numeric(getattr(dataset, "RescaleSlope", None), "RescaleSlope")
    intercept = _first_numeric(getattr(dataset, "RescaleIntercept", None), "RescaleIntercept")
    if slope is None:
        slope = 1.0
        warnings.append(
            {
                "code": "CT_RESCALE_DEFAULTED",
                "field": "RescaleSlope",
                "message": "RescaleSlope is absent; 1.0 is used for CT preview values.",
            }
        )
    if intercept is None:
        intercept = 0.0
        warnings.append(
            {
                "code": "CT_RESCALE_DEFAULTED",
                "field": "RescaleIntercept",
                "message": "RescaleIntercept is absent; 0.0 is used for CT preview values.",
            }
        )
    if abs(slope) < 1e-12:
        raise DVHEngineError(
            "DVH_ANATOMY_ARTIFACT_INVALID",
            "RescaleSlope must be finite and non-zero.",
            field="RescaleSlope",
        )
    values_hu = raw_pixels * slope + intercept
    if np.any(~np.isfinite(values_hu)):
        raise DVHEngineError(
            "DVH_ANATOMY_ARTIFACT_INVALID",
            "Rescaled CT values must be finite.",
            field="PixelData",
        )
    center_raw = getattr(dataset, "WindowCenter", None)
    width_raw = getattr(dataset, "WindowWidth", None)
    if center_raw is None and width_raw is None:
        low, high = np.percentile(values_hu, [1.0, 99.0]).tolist()
        warnings.append(
            {
                "code": "CT_WINDOW_DEFAULTED",
                "field": "WindowCenter/WindowWidth",
                "message": (
                    "No CT window was supplied; the 1st–99th percentile range is "
                    "used for preview only."
                ),
            }
        )
        center = float((low + high) / 2.0)
        width = float(high - low)
    else:
        parsed_center = _first_numeric(center_raw, "WindowCenter")
        parsed_width = _first_numeric(width_raw, "WindowWidth")
        if parsed_center is None or parsed_width is None or parsed_width <= 0:
            raise DVHEngineError(
                "DVH_ANATOMY_ARTIFACT_INVALID",
                "WindowCenter and WindowWidth must be a finite positive display window.",
                field="WindowCenter/WindowWidth",
            )
        center = float(parsed_center)
        width = float(parsed_width)
    if not math.isfinite(center) or not math.isfinite(width) or width <= 0:
        raise DVHEngineError(
            "DVH_ANATOMY_ARTIFACT_INVALID",
            "CT display window must be finite and have positive width.",
            field="WindowCenter/WindowWidth",
        )
    if width < 1e-9:
        width = 1.0
    return CTVolume(
        values_hu=values_hu,
        geometry=geometry,
        rescale_slope=float(slope),
        rescale_intercept=float(intercept),
        window_center=float(center),
        window_width=float(width),
        warnings=warnings,
    )


def _grid_points(
    geometry: CTGeometry, frame_index: int, stride: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rows, columns = geometry.shape[1:]
    row_indices = np.arange(0, rows, stride, dtype=np.float64)
    column_indices = np.arange(0, columns, stride, dtype=np.float64)
    grid_rows, grid_columns = np.meshgrid(row_indices, column_indices, indexing="ij")
    points = (
        np.asarray(geometry.origin_mm, dtype=np.float64)
        + grid_rows[..., np.newaxis]
        * np.asarray(geometry.column_cosine, dtype=np.float64)
        * geometry.pixel_spacing_mm[0]
    )
    # Apply the column axis and the selected slice offset explicitly.
    points += (
        grid_columns[..., np.newaxis]
        * np.asarray(geometry.row_cosine, dtype=np.float64)
        * geometry.pixel_spacing_mm[1]
    )
    points += (
        np.asarray(geometry.normal_cosine, dtype=np.float64) * geometry.offsets_mm[frame_index]
    )
    return points, row_indices, column_indices


def _plane_mapping_matrix(
    dose: DoseVolume,
    ct: CTVolume,
    dose_frame_index: int,
) -> list[list[float]]:
    dose_origin = (
        np.asarray(dose.geometry.origin_mm, dtype=np.float64)
        + np.asarray(dose.geometry.normal_cosine, dtype=np.float64)
        * dose.geometry.offsets_mm[dose_frame_index]
    )
    base = ct.geometry.world_to_continuous_indices(dose_origin.reshape(1, 3))[0]
    dose_row_step = (
        np.asarray(dose.geometry.column_cosine, dtype=np.float64)
        * dose.geometry.pixel_spacing_mm[0]
    )
    dose_column_step = (
        np.asarray(dose.geometry.row_cosine, dtype=np.float64) * dose.geometry.pixel_spacing_mm[1]
    )
    row_delta = (
        ct.geometry.world_to_continuous_indices((dose_origin + dose_row_step).reshape(1, 3))[0]
        - base
    )
    column_delta = (
        ct.geometry.world_to_continuous_indices((dose_origin + dose_column_step).reshape(1, 3))[0]
        - base
    )
    return [
        [float(row_delta[0]), float(column_delta[0]), float(base[0])],
        [float(row_delta[1]), float(column_delta[1]), float(base[1])],
        [float(row_delta[2]), float(column_delta[2]), float(base[2])],
    ]


def create_ct_preview(
    ct_path: Path,
    dose_path: Path,
    *,
    frame_index: int = 0,
    dose_frame_index: int | None = None,
    structure_path: Path | None = None,
    roi_number: int | None = None,
    max_ct_pixels: int = 8_000_000,
    max_dose_voxels: int = 2_000_000,
    preview_limit: int = DEFAULT_CT_PREVIEW_LIMIT,
) -> dict[str, object]:
    """Create a bounded CT slice preview with explicit patient-LPS mapping."""

    if preview_limit < 256 or preview_limit > 262_144:
        raise DVHEngineError(
            "DVH_METRIC_INVALID",
            "CT preview_limit must be between 256 and 262144 pixels.",
            field="preview_limit",
        )
    if (structure_path is None) != (roi_number is None):
        raise DVHEngineError(
            "DVH_ROI_INVALID",
            "structure_path and roi_number must be supplied together for ROI overlay.",
            field="roi_number",
        )
    dose = load_rtdose(dose_path, max_voxels=max_dose_voxels)
    ct = load_ct_volume(ct_path, dose, max_pixels=max_ct_pixels)
    if isinstance(frame_index, bool) or frame_index < 0 or frame_index >= ct.geometry.shape[0]:
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            "CT frame_index is outside the available frame range.",
            field="frame_index",
        )
    selected_dose_frame = (
        dose.geometry.shape[0] // 2 if dose_frame_index is None else dose_frame_index
    )
    if (
        isinstance(selected_dose_frame, bool)
        or selected_dose_frame < 0
        or selected_dose_frame >= dose.geometry.shape[0]
    ):
        raise DVHEngineError(
            "DICOM_GEOMETRY_INVALID",
            "dose_frame_index is outside the available dose frame range.",
            field="dose_frame_index",
        )
    structure: StructureROI | None = None
    if structure_path is not None and roi_number is not None:
        structure = _load_structure(structure_path, dose, roi_number)
    rows, columns = ct.geometry.shape[1:]
    stride = max(1, int(math.ceil(math.sqrt((rows * columns) / preview_limit))))
    points, row_indices, column_indices = _grid_points(ct.geometry, frame_index, stride)
    point_indices = dose.geometry.world_to_continuous_indices(points.reshape(-1, 3))
    dose_frames = np.floor(point_indices[:, 0] + 0.5).astype(np.int64)
    dose_rows = np.floor(point_indices[:, 1] + 0.5).astype(np.int64)
    dose_columns = np.floor(point_indices[:, 2] + 0.5).astype(np.int64)
    valid = (
        (dose_frames >= 0)
        & (dose_frames < dose.geometry.shape[0])
        & (dose_rows >= 0)
        & (dose_rows < dose.geometry.shape[1])
        & (dose_columns >= 0)
        & (dose_columns < dose.geometry.shape[2])
    )
    overlay = np.full(point_indices.shape[0], np.nan, dtype=np.float64)
    overlay[valid] = dose.values_gy[dose_frames[valid], dose_rows[valid], dose_columns[valid]]
    roi_overlay: list[bool] | None = None
    if structure is not None:
        roi_values = np.zeros(point_indices.shape[0], dtype=bool)
        roi_values[valid] = structure.mask[
            dose_frames[valid], dose_rows[valid], dose_columns[valid]
        ]
        roi_overlay = [bool(value) for value in roi_values]
    selected_plane = ct.values_hu[frame_index][::stride, ::stride]
    low = ct.window_center - ct.window_width / 2.0
    high = ct.window_center + ct.window_width / 2.0
    normalized = np.clip((selected_plane - low) / (high - low), 0.0, 1.0)
    if ct.geometry.photometric_interpretation == "MONOCHROME1":
        normalized = 1.0 - normalized
    display_pixels = np.rint(normalized * 255.0).astype(np.uint8)
    reference_point = (
        np.asarray(dose.geometry.origin_mm, dtype=np.float64)
        + np.asarray(dose.geometry.column_cosine, dtype=np.float64)
        * ((dose.geometry.shape[1] - 1) / 2.0)
        * dose.geometry.pixel_spacing_mm[0]
        + np.asarray(dose.geometry.row_cosine, dtype=np.float64)
        * ((dose.geometry.shape[2] - 1) / 2.0)
        * dose.geometry.pixel_spacing_mm[1]
        + np.asarray(dose.geometry.normal_cosine, dtype=np.float64)
        * dose.geometry.offsets_mm[selected_dose_frame]
    )
    crosshair = ct.geometry.world_to_continuous_indices(reference_point.reshape(1, 3))[0]
    nearest = np.floor(crosshair[:3] + 0.5).astype(np.int64)
    crosshair_visible = bool(
        0 <= nearest[0] < ct.geometry.shape[0]
        and 0 <= nearest[1] < ct.geometry.shape[1]
        and 0 <= nearest[2] < ct.geometry.shape[2]
    )
    warnings = list(ct.warnings)
    if not np.any(valid):
        warnings.append(
            {
                "code": "CT_DOSE_NO_OVERLAP",
                "field": "registration",
                "message": (
                    "The selected CT slice does not intersect the RTDOSE grid; "
                    "dose overlay is empty."
                ),
            }
        )
    result: dict[str, object] = {
        "schema_version": CT_PREVIEW_SCHEMA_VERSION,
        "engine_key": CT_PREVIEW_ENGINE_KEY,
        "engine_version": CT_PREVIEW_ENGINE_VERSION,
        "ct": {
            "modality": "CT",
            "frame_index": frame_index,
            "frame_count": ct.geometry.shape[0],
            "source_grid": {"rows": rows, "columns": columns},
            "output_grid": {
                "rows": int(selected_plane.shape[0]),
                "columns": int(selected_plane.shape[1]),
                "stride": stride,
            },
            "pixel_spacing_mm": list(ct.geometry.pixel_spacing_mm),
            "slice_offset_mm": ct.geometry.offsets_mm[frame_index],
            "slice_thickness_mm": ct.geometry.slice_thickness_mm[frame_index],
            "image_position_patient": list(ct.geometry.origin_mm),
            "image_orientation_patient": [
                *ct.geometry.row_cosine,
                *ct.geometry.column_cosine,
            ],
            "frame_of_reference_uid": ct.geometry.frame_of_reference_uid,
            "photometric_interpretation": ct.geometry.photometric_interpretation,
            "value_unit": "HU",
            "rescale_slope": ct.rescale_slope,
            "rescale_intercept": ct.rescale_intercept,
            "window_center": ct.window_center,
            "window_width": ct.window_width,
            "display_range_hu": [float(low), float(high)],
            "display_pixels": [int(value) for value in display_pixels.reshape(-1)],
        },
        "registration": {
            "mode": "SHARED_FRAME_OF_REFERENCE",
            "status": "LINKED",
            "patient_coordinate_system": "LPS",
            "source_frame_of_reference_uid": dose.geometry.frame_of_reference_uid,
            "target_frame_of_reference_uid": ct.geometry.frame_of_reference_uid,
            "overlay_algorithm": "NEAREST_NEIGHBOR_IN_PATIENT_LPS",
            "overlay_available": bool(np.any(valid)),
            "dose_frame_index": int(selected_dose_frame),
            "plane_mapping_matrix_dose_row_col_to_ct_frame_row_column": _plane_mapping_matrix(
                dose, ct, selected_dose_frame
            ),
            "crosshair": {
                "source": "DOSE_GRID_CENTER",
                "patient_lps_mm": [float(value) for value in reference_point],
                "ct_index": [float(value) for value in crosshair[:3]],
                "nearest_pixel": [int(value) for value in nearest],
                "visible": crosshair_visible,
            },
        },
        "overlay": {
            "rows": int(selected_plane.shape[0]),
            "columns": int(selected_plane.shape[1]),
            "stride": stride,
            "dose_gy": [None if not math.isfinite(value) else float(value) for value in overlay],
            "roi_mask": roi_overlay,
            "valid_pixel_count": int(np.count_nonzero(valid)),
            "outside_pixel_count": int(np.count_nonzero(~valid)),
        },
        "roi": (
            {
                "roi_number": structure.roi_number,
                "name": structure.name,
                "contour_count": structure.contour_count,
            }
            if structure is not None
            else None
        ),
        "warnings": warnings,
    }
    result["result_sha256"] = _canonical_sha256(result)
    return result


def validate_ct_frame(
    path: Path, dose: DoseVolume, *, max_pixels: int = 8_000_000
) -> dict[str, object]:
    """Validate optional CT linkage without making CT pixels part of DVH math."""

    try:
        dataset = pydicom.dcmread(path, stop_before_pixels=True, force=False)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED", "The CT file could not be decoded."
        ) from exc
    geometry, warnings = _ct_geometry_from_dataset(dataset, dose, max_pixels=max_pixels)
    return {
        "modality": "CT",
        "frame_of_reference_uid": geometry.frame_of_reference_uid,
        "grid": {
            "rows": geometry.shape[1],
            "columns": geometry.shape[2],
            "frames": geometry.shape[0],
        },
        "pixel_spacing_mm": list(geometry.pixel_spacing_mm),
        "image_position_patient": list(geometry.origin_mm),
        "image_orientation_patient": [*geometry.row_cosine, *geometry.column_cosine],
        "slice_offsets_mm": list(geometry.offsets_mm),
        "overlay_mode": "FRAME_LINK_ONLY",
        "warnings": warnings,
    }


def _metric_quantile(
    values: np.ndarray, weights: np.ndarray, percent: float
) -> float:
    """Return the dose covering ``percent`` of selected volume.

    The P17 contract uses a volume-weighted, piecewise-linear inverse
    cumulative DVH. Dose samples are grouped by observed dose, ordered from
    high to low, and cumulative selected volume is used as the independent
    axis. A requested percentile is linearly interpolated between adjacent
    observed dose levels; requests outside the observed range are clamped to
    the corresponding minimum/maximum dose rather than extrapolated.
    """

    dose_values = np.asarray(values, dtype=np.float64).reshape(-1)
    volume_weights = np.asarray(weights, dtype=np.float64).reshape(-1)
    if (
        dose_values.size == 0
        or dose_values.shape != volume_weights.shape
        or np.any(~np.isfinite(dose_values))
        or np.any(~np.isfinite(volume_weights))
        or np.any(volume_weights <= 0)
    ):
        raise DVHEngineError(
            "DVH_METRIC_INVALID",
            "Dose quantile values and volume weights must be finite and positive.",
        )

    dose_levels, inverse = np.unique(dose_values, return_inverse=True)
    level_weights = np.bincount(inverse, weights=volume_weights)
    order = np.argsort(dose_levels)[::-1]
    dose_levels = dose_levels[order]
    level_weights = level_weights[order]
    total_volume = float(np.sum(level_weights))
    target_volume = total_volume * (percent / 100.0)

    if target_volume <= 0:
        return float(dose_levels[0])
    if target_volume >= total_volume:
        return float(dose_levels[-1])

    cumulative_volume = 0.0
    previous_dose = float(dose_levels[0])
    previous_volume = 0.0
    for dose_level, level_volume in zip(dose_levels, level_weights, strict=True):
        cumulative_volume += float(level_volume)
        if target_volume <= cumulative_volume:
            current_dose = float(dose_level)
            span = cumulative_volume - previous_volume
            if span <= 0:
                return current_dose
            fraction = (target_volume - previous_volume) / span
            return previous_dose + fraction * (current_dose - previous_dose)
        previous_dose = float(dose_level)
        previous_volume = cumulative_volume

    return float(dose_levels[-1])


def _normalize_percentages(values: Sequence[float], field: str) -> tuple[float, ...]:
    result: list[float] = []
    for index, value in enumerate(values):
        number = _finite(value, f"{field}[{index}]")
        if number < 0 or number > 100:
            raise DVHEngineError(
                "DVH_METRIC_INVALID", f"{field} values must be between 0 and 100.", field=field
            )
        if number not in result:
            result.append(number)
    return tuple(result)


def _normalize_doses(values: Sequence[float], field: str) -> tuple[float, ...]:
    result: list[float] = []
    for index, value in enumerate(values):
        number = _finite(value, f"{field}[{index}]")
        if number < 0:
            raise DVHEngineError(
                "DVH_METRIC_INVALID", f"{field} values must be non-negative Gy.", field=field
            )
        if number not in result:
            result.append(number)
    return tuple(result)


def analyze_dvh(
    dose_path: Path,
    structure_path: Path,
    *,
    roi_number: int,
    coverage_policy: str = "FULL_ROI",
    slice_thickness_mm: float | None = None,
    dx_percentages: Sequence[float] = DEFAULT_DX_PERCENTAGES,
    vx_doses_gy: Sequence[float] = DEFAULT_VX_DOSES_GY,
    ct_path: Path | None = None,
    max_voxels: int = 2_000_000,
    max_ct_pixels: int = 8_000_000,
    preview_limit: int = 4096,
) -> DVHAnalysis:
    """Calculate a reproducible physical-dose DVH and compact visual preview."""

    if coverage_policy not in {"FULL_ROI", "OVERLAP_ONLY"}:
        raise DVHEngineError(
            "DVH_COVERAGE_POLICY_INVALID",
            "Unsupported DVH coverage policy.",
            field="coverage_policy",
        )
    if isinstance(roi_number, bool) or not isinstance(roi_number, int) or roi_number <= 0:
        raise DVHEngineError(
            "DVH_ROI_INVALID", "roi_number must be a positive integer.", field="roi_number"
        )
    if preview_limit < 1 or preview_limit > 16_384:
        raise DVHEngineError(
            "DVH_METRIC_INVALID",
            "preview_limit is outside the supported range.",
            field="preview_limit",
        )
    dose = load_rtdose(dose_path, max_voxels=max_voxels, slice_thickness_mm=slice_thickness_mm)
    structure = _load_structure(structure_path, dose, roi_number)
    dx_values = _normalize_percentages(dx_percentages, "dx_percentages")
    vx_values = _normalize_doses(vx_doses_gy, "vx_doses_gy")
    ct_summary = (
        validate_ct_frame(ct_path, dose, max_pixels=max_ct_pixels)
        if ct_path is not None
        else None
    )
    warnings: list[dict[str, object]] = []
    if ct_summary is None:
        warnings.append(
            {
                "code": "DVH_DOSE_ONLY_MODE",
                "field": "ct_artifact_id",
                "message": (
                    "No CT was supplied; DVH is calculated on the dose-native grid "
                    "and is not an anatomy overlay."
                ),
            }
        )
    if structure.outside_contour_count:
        if coverage_policy == "FULL_ROI":
            raise DVHEngineError(
                "DVH_INCOMPLETE_COVERAGE",
                "One or more selected ROI contours extend beyond the dose grid.",
                field="coverage_policy",
                details=[
                    {
                        "field": "outside_contour_count",
                        "message": str(structure.outside_contour_count),
                    }
                ],
            )
        warnings.append(
            {
                "code": "DVH_PARTIAL_COVERAGE",
                "field": "coverage_policy",
                "message": (
                    "Only the overlap between the ROI and dose grid is included; "
                    "total ROI coverage is incomplete."
                ),
            }
        )
    selected = dose.values_gy[structure.mask]
    if selected.size == 0 or np.any(~np.isfinite(selected)):
        raise DVHEngineError(
            "DVH_EMPTY_STRUCTURE", "No finite dose samples were selected for the ROI."
        )
    row_spacing, column_spacing = dose.geometry.pixel_spacing_mm
    voxel_area_cc = row_spacing * column_spacing / 1000.0
    voxel_volume_cc = np.asarray(dose.geometry.slice_thickness_mm, dtype=np.float64) * voxel_area_cc
    per_voxel_volume = np.broadcast_to(
        voxel_volume_cc[:, np.newaxis, np.newaxis], dose.values_gy.shape
    )
    selected_volumes = per_voxel_volume[structure.mask]
    volume_cc = float(np.sum(selected_volumes))
    if not math.isfinite(volume_cc) or volume_cc <= 0:
        raise DVHEngineError("DVH_EMPTY_STRUCTURE", "The rasterized ROI volume is not positive.")
    dx = {
        f"D{int(value) if value.is_integer() else value:g}_gy": _metric_quantile(
            selected, selected_volumes, value
        )
        for value in dx_values
    }
    vx_percent: dict[str, float] = {}
    vx_cc: dict[str, float] = {}
    for dose_threshold in vx_values:
        key = f"V{dose_threshold:g}_gy"
        included = selected >= dose_threshold
        included_cc = float(np.sum(selected_volumes[included]))
        vx_cc[key] = included_cc
        vx_percent[key] = float(included_cc / volume_cc * 100.0)
    dose_min = float(np.min(selected))
    dose_max = float(np.max(selected))
    curve_count = min(201, max(2, preview_limit // 16))
    if dose_max == dose_min:
        curve_doses = np.asarray([dose_min, dose_min], dtype=np.float64)
    else:
        curve_doses = np.linspace(dose_min, dose_max, curve_count, dtype=np.float64)
    cumulative_cc = [
        float(np.sum(selected_volumes[selected >= threshold])) for threshold in curve_doses
    ]
    cumulative_percent = [float(value / volume_cc * 100.0) for value in cumulative_cc]
    frame_counts = [
        int(np.count_nonzero(structure.mask[index])) for index in range(dose.geometry.shape[0])
    ]
    active_frames = [index for index, count in enumerate(frame_counts) if count]
    preview_frame = active_frames[len(active_frames) // 2]
    plane = dose.values_gy[preview_frame]
    plane_mask = structure.mask[preview_frame]
    stride = max(1, int(math.ceil(math.sqrt((plane.size) / preview_limit))))
    preview_plane = plane[::stride, ::stride]
    preview_mask = plane_mask[::stride, ::stride]
    normalized: dict[str, object] = {
        "schema_version": "visual-dose-dvh.input.v1",
        "roi_number": roi_number,
        "coverage_policy": coverage_policy,
        "slice_thickness_mm": slice_thickness_mm,
        "dx_percentages": list(dx_values),
        "vx_doses_gy": list(vx_values),
        "ct_supplied": ct_path is not None,
        "preview_limit": preview_limit,
    }
    result: dict[str, object] = {
        "schema_version": DVH_SCHEMA_VERSION,
        "engine_key": DVH_ENGINE_KEY,
        "engine_version": DVH_ENGINE_VERSION,
        "roi": {
            "roi_number": structure.roi_number,
            "name": structure.name,
            "contour_count": structure.contour_count,
            "contour_plane_count": structure.contour_plane_count,
        },
        "dose": {
            "units": dose.geometry.dose_units,
            "dose_type": dose.dose_type,
            "summation_type": dose.summation_type,
            "minimum_gy": dose_min,
            "maximum_gy": dose_max,
            "mean_gy": float(np.average(selected, weights=selected_volumes)),
        },
        "geometry": dose.geometry.summary(),
        "coverage": {
            "policy": coverage_policy,
            "status": "FULL" if structure.outside_contour_count == 0 else "OVERLAP_ONLY",
            "coverage_percent": 100.0 if structure.outside_contour_count == 0 else None,
            "selected_voxel_count": int(selected.size),
            "selected_volume_cc": volume_cc,
            "outside_contour_count": structure.outside_contour_count,
            "frame_counts": frame_counts,
        },
        "metrics": {
            "volume_cc": volume_cc,
            "Dmin_gy": dose_min,
            "Dmean_gy": float(np.average(selected, weights=selected_volumes)),
            "Dmax_gy": dose_max,
            "Dx_gy": dx,
            "Vx_percent": vx_percent,
            "Vx_cc": vx_cc,
        },
        "curve": {
            "dose_gy": [float(value) for value in curve_doses],
            "cumulative_volume_cc": cumulative_cc,
            "cumulative_volume_percent": cumulative_percent,
            "definition": "Volume receiving at least the dose threshold.",
        },
        "visual_preview": {
            "frame_index": preview_frame,
            "stride": stride,
            "rows": int(preview_plane.shape[0]),
            "columns": int(preview_plane.shape[1]),
            "dose_gy": [float(value) for value in preview_plane.reshape(-1)],
            "roi_mask": [bool(value) for value in preview_mask.reshape(-1)],
            "mode": "DOSE_NATIVE_GRID" if ct_summary is None else "DOSE_WITH_CT_FRAME_LINK",
        },
        "ct": ct_summary,
        "warnings": warnings,
    }
    result["result_sha256"] = _canonical_sha256(result)
    return DVHAnalysis(normalized_input=normalized, result=result, warnings=warnings)


def validate_dvh_paths(
    dose_path: Path,
    structure_path: Path,
    *,
    roi_number: int,
    coverage_policy: str,
    slice_thickness_mm: float | None,
    dx_percentages: Sequence[float],
    vx_doses_gy: Sequence[float],
    ct_path: Path | None,
    max_voxels: int,
    preview_limit: int,
) -> DVHAnalysis:
    """Validate-only entry point; it calculates a preview but persists nothing."""

    return analyze_dvh(
        dose_path,
        structure_path,
        roi_number=roi_number,
        coverage_policy=coverage_policy,
        slice_thickness_mm=slice_thickness_mm,
        dx_percentages=dx_percentages,
        vx_doses_gy=vx_doses_gy,
        ct_path=ct_path,
        max_voxels=max_voxels,
        preview_limit=preview_limit,
    )
