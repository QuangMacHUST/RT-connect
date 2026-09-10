"""Deterministic 2D/3D Gamma engine for the P8 input contract.

The engine accepts the validated ``gamma.measurement.v1`` JSON contract and
validated DICOM RTDOSE objects. JSON values are intentionally inline for this
worker slice; object-storage references are resolved by the API worker before
the engine is called. DICOM dose values are scaled to Gy and the supported
RTDOSE geometry is normalized to the same row-major ``(z, y, x)`` convention
used by the 3D measurement contract.

This is a deterministic engineering engine with explicit input and geometry
checks. It is not, by itself, evidence of clinical commissioning.
"""

from __future__ import annotations

import itertools
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pydicom
from numpy.typing import NDArray

ENGINE_VERSION = "gamma-nd-p8.2"
FloatArray = NDArray[np.float64]
Coordinate = tuple[float, ...]
AxisOrder = tuple[str, ...]
IDENTITY_TRANSFORM: tuple[float, ...] = (
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
)


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
    coverage_policy: str = "FULL_ROI"
    max_gamma: float = 2.0
    max_candidate_evaluations: int | None = None


@dataclass(frozen=True)
class MeasurementDataset:
    dataset_id: str
    values: FloatArray
    spacing_mm: Coordinate
    origin_mm: Coordinate
    units: dict[str, str]
    source_format: str = "measurement_json"
    coordinate_frame: str = "LEGACY_GRID"
    frame_id: str | None = None
    axis_order: AxisOrder = ()
    transform_to_reference: tuple[float, ...] | None = None


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


def _coordinate(value: object, field: str, dimension: int, *, positive: bool) -> Coordinate:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != dimension:
        raise GammaEngineError(
            "GAMMA_GRID_INVALID", f"{field} must contain exactly {dimension} values."
        )
    return tuple(
        _finite_float(item, f"{field}[{index}]", positive=positive)
        for index, item in enumerate(value)
    )


def _shape(value: object, field: str) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) not in {2, 3}:
        raise GammaEngineError(
            "GAMMA_GRID_INVALID", f"{field} must contain two or three integer dimensions."
        )
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in value):
        raise GammaEngineError("GAMMA_GRID_INVALID", f"{field} dimensions must be positive.")
    return tuple(int(item) for item in value)


def _dose_unit_scale(value: object, field: str) -> tuple[str, float]:
    if value == "GY":
        return "GY", 1.0
    if value == "CGY":
        return "GY", 0.01
    raise GammaEngineError(
        "GAMMA_UNITS_UNSUPPORTED", f"{field} must be GY or CGY; units are never inferred."
    )


def _canonical_axis_order(dimension: int) -> AxisOrder:
    return ("y", "x") if dimension == 2 else ("z", "y", "x")


def _parse_transform_to_reference(value: object, field: str) -> tuple[float, ...]:
    transform = _mapping(value, field)
    if transform.get("direction") != "SOURCE_TO_REFERENCE":
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_INVALID",
            f"{field}.direction must be SOURCE_TO_REFERENCE.",
        )
    if transform.get("units") != "mm":
        raise GammaEngineError(
            "GAMMA_UNITS_UNSUPPORTED",
            f"{field}.units must be mm; units are never inferred.",
        )
    matrix_value = transform.get("matrix")
    if not isinstance(matrix_value, list) or len(matrix_value) != 4:
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_INVALID",
            f"{field}.matrix must be a 4x4 finite matrix.",
        )
    matrix: list[float] = []
    for row_index, row in enumerate(matrix_value):
        if not isinstance(row, list) or len(row) != 4:
            raise GammaEngineError(
                "GAMMA_COORDINATE_FRAME_INVALID",
                f"{field}.matrix[{row_index}] must contain four values.",
            )
        matrix.extend(
            _finite_float(item, f"{field}.matrix[{row_index}][{column_index}]")
            for column_index, item in enumerate(row)
        )
    source = _mapping(transform.get("source"), f"{field}.source")
    for key in ("type", "version", "sha256"):
        source_value = source.get(key)
        if not isinstance(source_value, str) or not source_value.strip():
            raise GammaEngineError(
                "GAMMA_COORDINATE_FRAME_INVALID",
                f"{field}.source.{key} is required for transform provenance.",
            )
    if len(str(source.get("sha256"))) != 64:
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_INVALID",
            f"{field}.source.sha256 must be a SHA-256 hex string.",
        )
    parsed = tuple(matrix)
    if not np.allclose(parsed, IDENTITY_TRANSFORM, rtol=0, atol=1e-9):
        raise GammaEngineError(
            "GAMMA_TRANSFORM_UNSUPPORTED",
            "P8 currently supports only an explicitly declared identity transform; "
            "a non-identity transform needs a tested adapter.",
        )
    return parsed


def _parse_json_coordinate_frame(root: Mapping[str, object], dimension: int) -> tuple[
    str, str, AxisOrder, tuple[float, ...]
]:
    raw_frame = root.get("coordinate_frame")
    if raw_frame is None:
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_MISSING",
            "Measurement JSON must declare coordinate_frame before Gamma use.",
        )
    frame = _mapping(raw_frame, "coordinate_frame")
    basis = frame.get("basis")
    if basis not in {"PATIENT_LPS", "IEC_PHANTOM"}:
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_INVALID",
            "coordinate_frame.basis must be PATIENT_LPS or IEC_PHANTOM.",
        )
    frame_id = frame.get("frame_id")
    if not isinstance(frame_id, str) or not frame_id.strip():
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_INVALID",
            "coordinate_frame.frame_id is required.",
        )
    axis_value = frame.get("axis_order")
    expected_axis = _canonical_axis_order(dimension)
    if (
        not isinstance(axis_value, list)
        or any(not isinstance(item, str) for item in axis_value)
        or tuple(axis_value) != expected_axis
    ):
        raise GammaEngineError(
            "GAMMA_AXIS_ORDER_UNSUPPORTED",
            f"coordinate_frame.axis_order must be {list(expected_axis)} for P8.",
        )
    transform = _parse_transform_to_reference(
        frame.get("transform_to_reference"), "coordinate_frame.transform_to_reference"
    )
    if basis == "PATIENT_LPS":
        frame_uid = frame.get("frame_of_reference_uid")
        if not isinstance(frame_uid, str) or not frame_uid.strip() or frame_uid != frame_id:
            raise GammaEngineError(
                "GAMMA_COORDINATE_FRAME_INVALID",
                "PATIENT_LPS requires frame_id equal to frame_of_reference_uid.",
            )
    return str(basis), frame_id.strip(), expected_axis, transform


def _load_inline_measurement(path: Path) -> MeasurementDataset:
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
    if root.get("data_type") not in {"dose", "PLANAR_DOSE"}:
        raise GammaEngineError(
            "GAMMA_DATA_TYPE_UNSUPPORTED", "Gamma input data_type must be dose or PLANAR_DOSE."
        )
    dataset_id = root.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise GammaEngineError("GAMMA_DATASET_ID_MISSING", "Gamma input dataset_id is required.")

    units = _mapping(root.get("units"), "units")
    dose_unit, dose_scale = _dose_unit_scale(units.get("dose"), "units.dose")
    if units.get("position") != "mm":
        raise GammaEngineError(
            "GAMMA_UNITS_UNSUPPORTED", "units.position must be mm; units are never inferred."
        )

    grid = _mapping(root.get("grid"), "grid")
    shape = _shape(grid.get("shape"), "grid.shape")
    dimension = len(shape)
    coordinate_frame, frame_id, axis_order, transform = _parse_json_coordinate_frame(
        root, dimension
    )
    spacing = _coordinate(grid.get("spacing_mm"), "grid.spacing_mm", dimension, positive=True)
    origin = _coordinate(
        grid.get("origin_mm", [0.0] * dimension), "grid.origin_mm", dimension, positive=False
    )

    values = _mapping(root.get("values"), "values")
    if values.get("encoding") not in {"inline-float32", "float32"}:
        raise GammaEngineError(
            "GAMMA_ENCODING_UNSUPPORTED",
            "P8 requires inline float32 measurement values for the worker slice.",
        )
    inline = values.get("inline")
    expected_count = math.prod(shape)
    if not isinstance(inline, list) or len(inline) != expected_count:
        raise GammaEngineError(
            "GAMMA_GRID_VALUE_COUNT_MISMATCH",
            "The number of dose values must exactly match grid.shape.",
        )
    numeric_values = [
        _finite_float(item, f"values.inline[{index}]") for index, item in enumerate(inline)
    ]
    array = np.asarray(numeric_values, dtype=np.float64).reshape(shape) * dose_scale
    if np.any(array < 0):
        raise GammaEngineError("GAMMA_DOSE_NEGATIVE", "Dose values must be non-negative.")
    return MeasurementDataset(
        dataset_id=dataset_id,
        values=array,
        spacing_mm=spacing,
        origin_mm=origin,
        units={"dose": dose_unit, "position": "mm"},
        coordinate_frame=coordinate_frame,
        frame_id=frame_id,
        axis_order=axis_order,
        transform_to_reference=transform,
    )


def _uniform_spacing(offsets: Sequence[object], field: str) -> float:
    numeric = [_finite_float(item, f"{field}[{index}]") for index, item in enumerate(offsets)]
    if len(numeric) < 2:
        raise GammaEngineError("GAMMA_DICOM_GRID_INVALID", f"{field} needs at least two frames.")
    differences = np.diff(np.asarray(numeric, dtype=np.float64))
    if np.any(differences <= 0) or not np.allclose(
        differences, differences[0], rtol=1e-6, atol=1e-6
    ):
        raise GammaEngineError(
            "GAMMA_DICOM_GRID_INVALID",
            "RTDOSE GridFrameOffsetVector must be strictly increasing and uniformly spaced.",
        )
    return float(differences[0])


def _load_rtdose(path: Path) -> MeasurementDataset:
    try:
        dataset = pydicom.dcmread(path, force=False)
    except Exception as exc:
        raise GammaEngineError(
            "GAMMA_DICOM_UNREADABLE", "The RTDOSE artifact is not readable."
        ) from exc
    if getattr(dataset, "Modality", None) != "RTDOSE":
        raise GammaEngineError("GAMMA_DICOM_MODALITY_INVALID", "Gamma DICOM input must be RTDOSE.")
    try:
        pixel_array = np.asarray(dataset.pixel_array, dtype=np.float64)
    except Exception as exc:
        raise GammaEngineError(
            "GAMMA_DICOM_PIXEL_DATA_INVALID", "RTDOSE pixel data could not be decoded."
        ) from exc
    scaling = _finite_float(
        getattr(dataset, "DoseGridScaling", None), "DoseGridScaling", positive=True
    )
    dose_units, dose_scale = _dose_unit_scale(getattr(dataset, "DoseUnits", None), "DoseUnits")
    array = pixel_array * scaling * dose_scale
    if array.ndim not in {2, 3} or np.any(~np.isfinite(array)) or np.any(array < 0):
        raise GammaEngineError(
            "GAMMA_DICOM_PIXEL_DATA_INVALID", "RTDOSE pixel values must be finite and non-negative."
        )

    spacing_value = getattr(dataset, "PixelSpacing", None)
    try:
        spacing_xy = _coordinate(spacing_value, "PixelSpacing", 2, positive=True)
    except GammaEngineError as exc:
        raise GammaEngineError(
            "GAMMA_DICOM_GRID_INVALID",
            f"RTDOSE PixelSpacing is invalid: {exc.message}",
            exc.details,
        ) from exc
    position = _coordinate(
        getattr(dataset, "ImagePositionPatient", None),
        "ImagePositionPatient",
        3,
        positive=False,
    )
    orientation = _coordinate(
        getattr(dataset, "ImageOrientationPatient", None),
        "ImageOrientationPatient",
        6,
        positive=False,
    )
    if not np.allclose(orientation, (1.0, 0.0, 0.0, 0.0, 1.0, 0.0), rtol=0, atol=1e-6):
        raise GammaEngineError(
            "GAMMA_DICOM_ORIENTATION_UNSUPPORTED",
            "P8 RTDOSE adapter currently supports an axial IEC-aligned orientation only.",
        )
    frame_id = getattr(dataset, "FrameOfReferenceUID", None)
    if not isinstance(frame_id, str) or not frame_id.strip():
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_MISSING",
            "RTDOSE FrameOfReferenceUID is required for Gamma alignment.",
        )
    frames = int(getattr(dataset, "NumberOfFrames", 1))
    origin: Coordinate
    spacing: Coordinate
    if array.ndim == 3:
        if array.shape[0] != frames:
            raise GammaEngineError(
                "GAMMA_DICOM_GRID_INVALID", "NumberOfFrames does not match RTDOSE pixel data."
            )
        offsets_value = getattr(dataset, "GridFrameOffsetVector", None)
        if not isinstance(offsets_value, Sequence) or isinstance(offsets_value, str):
            raise GammaEngineError(
                "GAMMA_DICOM_GRID_INVALID", "RTDOSE GridFrameOffsetVector is required for 3D input."
            )
        if len(offsets_value) != frames:
            raise GammaEngineError(
                "GAMMA_DICOM_GRID_INVALID", "GridFrameOffsetVector must match NumberOfFrames."
            )
        z_spacing = _uniform_spacing(offsets_value, "GridFrameOffsetVector")
        origin = (
            position[2] + _finite_float(offsets_value[0], "GridFrameOffsetVector[0]"),
            position[1],
            position[0],
        )
        spacing = (z_spacing, spacing_xy[0], spacing_xy[1])
    else:
        origin = (position[1], position[0])
        spacing = spacing_xy
    return MeasurementDataset(
        dataset_id=str(getattr(dataset, "SOPInstanceUID", path.stem)),
        values=array,
        spacing_mm=spacing,
        origin_mm=origin,
        units={"dose": dose_units, "position": "mm"},
        source_format="dicom_rtdose",
        coordinate_frame="PATIENT_LPS",
        frame_id=frame_id.strip(),
        axis_order=_canonical_axis_order(array.ndim),
        transform_to_reference=IDENTITY_TRANSFORM,
    )


def load_measurement(path: Path) -> MeasurementDataset:
    """Load a validated JSON measurement dataset, including 2D or 3D grids."""

    return _load_inline_measurement(path)


def load_gamma_dataset(path: Path) -> MeasurementDataset:
    """Load either the JSON measurement contract or a DICOM RTDOSE artifact."""

    try:
        prefix = path.read_bytes()[:256]
    except OSError as exc:
        raise GammaEngineError("GAMMA_INPUT_UNREADABLE", "Gamma input could not be read.") from exc
    if prefix[128:132] == b"DICM" or not prefix.lstrip().startswith((b"{", b"[")):
        return _load_rtdose(path)
    return _load_inline_measurement(path)


def _configuration_from_mapping(payload: Mapping[str, object]) -> GammaConfiguration:
    dimensionality = payload.get("dimensionality", "2D")
    dose_mode = payload.get("dose_difference_mode", "RELATIVE")
    normalization = payload.get("normalization", "GLOBAL")
    interpolation = payload.get("interpolation", "GRID")
    if dimensionality not in {"2D", "3D"}:
        raise GammaEngineError("GAMMA_DIMENSIONALITY_UNSUPPORTED", "P8 supports 2D and 3D Gamma.")
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
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "Percentage values must be 0–100%.")
    coverage_policy = payload.get("coverage_policy", "FULL_ROI")
    if coverage_policy not in {"FULL_ROI", "OVERLAP_ONLY"}:
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "coverage_policy is invalid.")
    max_gamma = _finite_float(payload.get("max_gamma", 2.0), "max_gamma", positive=True)
    if max_gamma < 1 or max_gamma > 10:
        raise GammaEngineError("GAMMA_CONFIGURATION_INVALID", "max_gamma must be between 1 and 10.")
    resource_budget = payload.get("resource_budget")
    raw_candidate_limit: object = None
    if isinstance(resource_budget, Mapping):
        raw_candidate_limit = resource_budget.get("max_candidate_evaluations")
    if raw_candidate_limit is None:
        candidate_limit = None
    elif (
        isinstance(raw_candidate_limit, bool)
        or not isinstance(raw_candidate_limit, int)
        or raw_candidate_limit < 10_000
    ):
        raise GammaEngineError(
            "GAMMA_CONFIGURATION_INVALID",
            "resource_budget.max_candidate_evaluations must be an integer >= 10000.",
        )
    else:
        candidate_limit = raw_candidate_limit
    absolute_value = payload.get("absolute_dose_difference_gy")
    absolute = (
        None
        if absolute_value is None
        else _finite_float(absolute_value, "absolute_dose_difference_gy", positive=True)
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
        coverage_policy=str(coverage_policy),
        max_gamma=max_gamma,
        max_candidate_evaluations=candidate_limit,
    )


def _sample_linear(dataset: MeasurementDataset, position: Coordinate) -> float | None:
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
    weights = [coordinate - index for coordinate, index in zip(coordinates, lower, strict=True)]
    total = 0.0
    for corner in itertools.product((0, 1), repeat=dataset.values.ndim):
        indices = tuple(
            upper[axis] if corner[axis] else lower[axis] for axis in range(dataset.values.ndim)
        )
        weight = 1.0
        for axis, bit in enumerate(corner):
            weight *= weights[axis] if bit else 1.0 - weights[axis]
        total += float(dataset.values[indices]) * weight
    return total


def _point_position(dataset: MeasurementDataset, indices: tuple[int, ...]) -> Coordinate:
    return tuple(
        dataset.origin_mm[axis] + indices[axis] * dataset.spacing_mm[axis]
        for axis in range(dataset.values.ndim)
    )


def _candidate_gammas(
    reference: MeasurementDataset,
    evaluation: MeasurementDataset,
    reference_indices: tuple[int, ...],
    reference_value: float,
    configuration: GammaConfiguration,
) -> list[float]:
    reference_position = _point_position(reference, reference_indices)
    search_radius = configuration.distance_to_agreement_mm * configuration.max_gamma
    dose_scale = _dose_scale(reference_value, float(np.max(reference.values)), configuration)
    if configuration.interpolation == "GRID":
        index_ranges: list[range] = []
        for axis in range(evaluation.values.ndim):
            minimum = math.ceil(
                (reference_position[axis] - search_radius - evaluation.origin_mm[axis])
                / evaluation.spacing_mm[axis]
            )
            maximum = math.floor(
                (reference_position[axis] + search_radius - evaluation.origin_mm[axis])
                / evaluation.spacing_mm[axis]
            )
            start = max(0, minimum)
            stop = min(evaluation.values.shape[axis] - 1, maximum)
            index_ranges.append(range(start, stop + 1) if start <= stop else range(0))
        gammas: list[float] = []
        for evaluation_indices in itertools.product(*index_ranges):
            evaluation_position = _point_position(evaluation, tuple(evaluation_indices))
            distance = math.sqrt(
                sum(
                    (evaluation_position[axis] - reference_position[axis]) ** 2
                    for axis in range(reference.values.ndim)
                )
            )
            if distance > search_radius:
                continue
            evaluation_value = float(evaluation.values[tuple(evaluation_indices)])
            if (
                configuration.max_candidate_evaluations is not None
                and len(gammas) >= configuration.max_candidate_evaluations
            ):
                raise GammaEngineError(
                    "GAMMA_RESOURCE_LIMIT",
                    "Gamma candidate evaluation limit was exceeded for one reference point.",
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
        -search_radius,
        search_radius + step / 2,
        step,
    )
    gammas = []
    for offset_tuple in itertools.product(offsets, repeat=reference.values.ndim):
        distance = math.sqrt(sum(float(offset) ** 2 for offset in offset_tuple))
        if distance > search_radius:
            continue
        position = tuple(
            reference_position[axis] + float(offset_tuple[axis])
            for axis in range(reference.values.ndim)
        )
        sampled_value = _sample_linear(evaluation, position)
        if sampled_value is None:
            continue
        if (
            configuration.max_candidate_evaluations is not None
            and len(gammas) >= configuration.max_candidate_evaluations
        ):
            raise GammaEngineError(
                "GAMMA_RESOURCE_LIMIT",
                "Gamma candidate evaluation limit was exceeded for one reference point.",
            )
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


def _validate_coordinate_compatibility(
    reference: MeasurementDataset, evaluation: MeasurementDataset
) -> None:
    """Fail closed unless both datasets describe the same physical basis.

    The old JSON-only test contract had no physical frame metadata.  It remains
    usable when both inputs are explicitly legacy grids, but it must never be
    mixed with a DICOM RTDOSE or an explicitly framed measurement.  This keeps
    ENGINE_TEST compatibility without allowing PSQA to silently compare unlike
    coordinate systems.
    """

    legacy_reference = reference.coordinate_frame == "LEGACY_GRID"
    legacy_evaluation = evaluation.coordinate_frame == "LEGACY_GRID"
    if legacy_reference or legacy_evaluation:
        if legacy_reference and legacy_evaluation:
            return
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Reference and evaluation inputs must both declare a compatible coordinate frame.",
        )
    if reference.coordinate_frame != evaluation.coordinate_frame:
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Reference and evaluation coordinate-frame bases do not match.",
        )
    if reference.frame_id is None or evaluation.frame_id is None:
        raise GammaEngineError(
            "GAMMA_COORDINATE_FRAME_MISSING",
            "Both Gamma inputs require a non-empty coordinate-frame identifier.",
        )
    if reference.frame_id != evaluation.frame_id:
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Reference and evaluation coordinate-frame identifiers do not match.",
            details=[
                {
                    "field": "frame_id",
                    "message": (
                        "The two inputs must use the same Frame of Reference or declared "
                        "phantom frame."
                    ),
                }
            ],
        )
    if reference.axis_order != evaluation.axis_order:
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Reference and evaluation axis orders do not match.",
        )
    if (
        reference.transform_to_reference != evaluation.transform_to_reference
        or reference.transform_to_reference is None
        or evaluation.transform_to_reference is None
    ):
        raise GammaEngineError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Reference and evaluation transforms to the comparison frame do not match.",
        )


def calculate_gamma(
    reference: MeasurementDataset,
    evaluation: MeasurementDataset,
    configuration: GammaConfiguration,
) -> dict[str, object]:
    """Calculate a reproducible 2D or 3D Gamma map and summary statistics."""

    if reference.values.ndim != evaluation.values.ndim:
        raise GammaEngineError(
            "GAMMA_DIMENSIONALITY_MISMATCH",
            "Reference and evaluation grids must have the same dimension.",
        )
    expected_dimension = 2 if configuration.dimensionality == "2D" else 3
    if reference.values.ndim != expected_dimension:
        raise GammaEngineError(
            "GAMMA_DIMENSIONALITY_MISMATCH",
            f"Configuration {configuration.dimensionality} requires a {expected_dimension}D grid.",
        )
    _validate_coordinate_compatibility(reference, evaluation)
    if (
        len(reference.spacing_mm) != reference.values.ndim
        or len(evaluation.spacing_mm) != evaluation.values.ndim
    ):
        raise GammaEngineError(
            "GAMMA_GRID_INVALID", "Grid spacing dimensionality does not match values."
        )
    reference_max = float(np.max(reference.values))
    if reference_max <= 0:
        raise GammaEngineError("GAMMA_REFERENCE_ZERO", "Reference dose maximum must be positive.")
    threshold = reference_max * configuration.dose_threshold_percent / 100
    map_items: list[dict[str, object]] = []
    gamma_values: list[float] = []
    excluded = 0
    no_candidate = 0
    censored = 0
    for raw_indices in np.ndindex(reference.values.shape):
        reference_indices = tuple(int(index) for index in raw_indices)
        reference_value = float(reference.values[reference_indices])
        if reference_value < threshold:
            excluded += 1
            continue
        candidates = _candidate_gammas(
            reference, evaluation, reference_indices, reference_value, configuration
        )
        item: dict[str, object] = {
            "index": list(reference_indices),
            "reference_dose_gy": reference_value,
        }
        if reference.values.ndim == 2:
            item.update({"row": reference_indices[0], "column": reference_indices[1]})
        else:
            item.update(
                {
                    "frame": reference_indices[0],
                    "row": reference_indices[1],
                    "column": reference_indices[2],
                }
            )
        if not candidates:
            no_candidate += 1
            item.update(
                {
                    "gamma": None,
                    "status": "NO_CANDIDATE",
                    "coverage_status": "EXCLUDED"
                    if configuration.coverage_policy == "OVERLAP_ONLY"
                    else "INVALID",
                }
            )
            map_items.append(item)
            continue
        gamma = min(candidates)
        if gamma > configuration.max_gamma:
            censored += 1
            item.update(
                {
                    "gamma": None,
                    "gamma_lower_bound": configuration.max_gamma,
                    "status": "CENSORED",
                }
            )
            map_items.append(item)
            continue
        gamma_values.append(gamma)
        item.update({"gamma": gamma, "status": "PASS" if gamma <= 1 else "FAIL"})
        map_items.append(item)

    selected_points = reference.values.size - excluded
    if not selected_points or (
        configuration.coverage_policy == "OVERLAP_ONLY" and not gamma_values and not censored
    ):
        raise GammaEngineError(
            "GAMMA_NO_EVALUATED_POINTS", "No reference dose point passed the threshold."
        )
    coverage_excluded = no_candidate if configuration.coverage_policy == "OVERLAP_ONLY" else 0
    invalid_coverage = no_candidate if configuration.coverage_policy == "FULL_ROI" else 0
    denominator = len(gamma_values) + censored
    values = np.asarray(gamma_values, dtype=np.float64)
    passing = int(np.count_nonzero(values <= 1))
    pass_rate = None if invalid_coverage else passing / denominator * 100
    if censored or invalid_coverage:
        percentile_values: dict[str, object] = {
            "exact": False,
            "reason": "GAMMA_CENSORED_POINTS" if censored else "GAMMA_INCOMPLETE_COVERAGE",
            "p50": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "max": None,
        }
    else:
        percentile_values = {
            "exact": True,
            "p50": float(np.percentile(values, 50)),
            "p90": float(np.percentile(values, 90)),
            "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)),
            "max": float(np.max(values)),
        }
    histogram_counts, histogram_edges = np.histogram(
        values,
        bins=configuration.histogram_bins,
        range=(0, max(1.0, float(np.max(values)) if values.size else configuration.max_gamma)),
    )
    if invalid_coverage:
        overall_status = "INVALID"
    else:
        overall_status = (
            "PASS"
            if pass_rate is not None and pass_rate >= configuration.pass_rate_threshold_percent
            else "FAIL"
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
                "message": (
                    "Some reference points have no comparison point inside the configured "
                    "max-gamma search radius; they are invalid coverage or explicitly "
                    "excluded according to coverage_policy."
                ),
            }
        )
    if censored:
        warnings.append(
            {
                "code": "GAMMA_SEARCH_CENSORED",
                "count": censored,
                "max_gamma": configuration.max_gamma,
                "message": (
                    "Some Gamma values are lower bounds because the search limit was reached."
                ),
            }
        )
    return {
        "algorithm": "deterministic-nd-node-search",
        "dimensionality": configuration.dimensionality,
        "reference_dataset_id": reference.dataset_id,
        "evaluation_dataset_id": evaluation.dataset_id,
        "reference_grid": {
            "shape": list(reference.values.shape),
            "spacing_mm": list(reference.spacing_mm),
            "origin_mm": list(reference.origin_mm),
            "source_format": reference.source_format,
            "coordinate_frame": reference.coordinate_frame,
            "frame_id": reference.frame_id,
            "axis_order": list(reference.axis_order),
            "transform_to_reference": list(reference.transform_to_reference)
            if reference.transform_to_reference is not None
            else None,
        },
        "evaluation_grid": {
            "shape": list(evaluation.values.shape),
            "spacing_mm": list(evaluation.spacing_mm),
            "origin_mm": list(evaluation.origin_mm),
            "source_format": evaluation.source_format,
            "coordinate_frame": evaluation.coordinate_frame,
            "frame_id": evaluation.frame_id,
            "axis_order": list(evaluation.axis_order),
            "transform_to_reference": list(evaluation.transform_to_reference)
            if evaluation.transform_to_reference is not None
            else None,
        },
        "metrics": {
            "evaluated_points": len(gamma_values),
            "passing_points": passing,
            "nonpassing_points": denominator - passing,
            "excluded_points": excluded,
            "selected_points": selected_points,
            "coverage_excluded_points": coverage_excluded,
            "invalid_coverage_points": invalid_coverage,
            "coverage_fraction": (
                (len(gamma_values) + censored) / selected_points if selected_points else 0.0
            ),
            "censored_points": censored,
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
        "overall_status": overall_status,
    }


def calculate_gamma_from_paths(
    reference_path: Path, evaluation_path: Path, configuration_payload: Mapping[str, object]
) -> dict[str, object]:
    """Worker entry point: load immutable JSON/DICOM artifacts and calculate the result."""

    configuration = _configuration_from_mapping(configuration_payload)
    reference = load_gamma_dataset(reference_path)
    evaluation = load_gamma_dataset(evaluation_path)
    result = calculate_gamma(reference, evaluation, configuration)
    result["configuration"] = dict(configuration_payload)
    result["engine_version"] = ENGINE_VERSION
    return result
