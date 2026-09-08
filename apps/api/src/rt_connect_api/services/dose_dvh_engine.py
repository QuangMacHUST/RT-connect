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
DEFAULT_DX_PERCENTAGES = (2.0, 50.0, 95.0, 98.0)
DEFAULT_VX_DOSES_GY = (0.0, 20.0, 30.0, 40.0, 50.0)


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

        relative = points_mm - np.asarray(self.origin_mm, dtype=np.float64)
        # DICOM stores the direction of the first row (columns) first and
        # the direction of the first column (rows) second.  PixelSpacing is
        # ordered row spacing, then column spacing.
        column = relative @ np.asarray(self.row_cosine, dtype=np.float64)
        row = relative @ np.asarray(self.column_cosine, dtype=np.float64)
        normal = relative @ np.asarray(self.normal_cosine, dtype=np.float64)
        offsets = np.asarray(self.offsets_mm, dtype=np.float64)
        frame = np.asarray([int(np.argmin(np.abs(offsets - value))) for value in normal])
        return np.column_stack(
            (
                frame,
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


def validate_ct_frame(path: Path, dose: DoseVolume) -> dict[str, object]:
    """Validate optional CT linkage without making CT pixels part of DVH math."""

    try:
        dataset = pydicom.dcmread(path, stop_before_pixels=True, force=False)
    except Exception as exc:
        raise DVHEngineError(
            "DICOM_CAPABILITY_UNSUPPORTED", "The CT file could not be decoded."
        ) from exc
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
    rows = getattr(dataset, "Rows", None)
    columns = getattr(dataset, "Columns", None)
    spacing = _vector(getattr(dataset, "PixelSpacing", None), "CT.PixelSpacing", 2, positive=True)
    position = _vector(getattr(dataset, "ImagePositionPatient", None), "CT.ImagePositionPatient", 3)
    orientation = _vector(
        getattr(dataset, "ImageOrientationPatient", None), "CT.ImageOrientationPatient", 6
    )
    return {
        "modality": "CT",
        "frame_of_reference_uid": frame,
        "grid": {"rows": rows, "columns": columns},
        "pixel_spacing_mm": list(spacing),
        "image_position_patient": list(position),
        "image_orientation_patient": list(orientation),
        "overlay_mode": "DOSE_NATIVE_GRID",
    }


def _metric_quantile(values: np.ndarray, percent: float) -> float:
    return float(np.quantile(values, 1.0 - percent / 100.0, method="linear"))


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
    ct_summary = validate_ct_frame(ct_path, dose) if ct_path is not None else None
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
        f"D{int(value) if value.is_integer() else value:g}_gy": _metric_quantile(selected, value)
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
