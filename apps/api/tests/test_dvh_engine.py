from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import (
    CTImageStorage,
    ExplicitVRLittleEndian,
    RTDoseStorage,
    RTStructureSetStorage,
    generate_uid,
)

from rt_connect_api.services.dose_dvh_engine import (
    DVHEngineError,
    analyze_dvh,
    create_ct_preview,
    list_structure_rois,
)


def _write_dataset(dataset: FileDataset, path: Path) -> None:
    dataset.is_little_endian = True
    dataset.is_implicit_VR = False
    dataset.save_as(path, write_like_original=False)


def _dose_file(
    path: Path,
    *,
    frame_uid: str | None = None,
    shape: tuple[int, int, int] = (3, 5, 5),
    values: np.ndarray | None = None,
    pixel_spacing: tuple[float, float] = (2.0, 4.0),
    offsets: list[float] | None = None,
    dose_units: str = "GY",
    slice_thickness: float | None = None,
) -> str:
    frames, rows, columns = shape
    sop_instance_uid = generate_uid()
    frame_uid = frame_uid or generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = RTDoseStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = RTDoseStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = generate_uid()
    dataset.FrameOfReferenceUID = frame_uid
    dataset.Modality = "RTDOSE"
    dataset.Rows = rows
    dataset.Columns = columns
    dataset.NumberOfFrames = frames
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelSpacing = list(pixel_spacing)
    dataset.GridFrameOffsetVector = offsets or [float(index * 2) for index in range(frames)]
    dataset.ImagePositionPatient = [0.0, 0.0, 0.0]
    dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    dataset.DoseGridScaling = 0.01
    dataset.DoseUnits = dose_units
    dataset.DoseType = "PHYSICAL"
    dataset.DoseSummationType = "PLAN"
    if slice_thickness is not None:
        dataset.SliceThickness = slice_thickness
    referenced_plan = Dataset()
    referenced_plan.ReferencedSOPClassUID = generate_uid()
    referenced_plan.ReferencedSOPInstanceUID = generate_uid()
    dataset.ReferencedRTPlanSequence = [referenced_plan]
    raw_values = values if values is not None else np.full(shape, 200, dtype=np.uint16)
    dataset.PixelData = np.asarray(raw_values, dtype=np.uint16).tobytes()
    _write_dataset(dataset, path)
    return frame_uid


def _world_point(row: float, column: float, z: float) -> list[float]:
    # Axial DICOM orientation: the first direction is along columns and the
    # second direction is along rows.  PixelSpacing is row spacing, then
    # column spacing for the dose fixture (2 mm, 4 mm).
    return [column * 4.0, row * 2.0, z]


def _contour(points: list[list[float]], geometric_type: str = "CLOSED_PLANAR") -> Dataset:
    item = Dataset()
    item.ContourGeometricType = geometric_type
    item.NumberOfContourPoints = len(points)
    item.ContourData = [coordinate for point in points for coordinate in point]
    return item


def _structure_file(
    path: Path,
    frame_uid: str,
    *,
    roi_number: int = 1,
    contours: list[Dataset] | None = None,
    second_roi: bool = False,
    second_frame_uid: str | None = None,
) -> None:
    sop_instance_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = RTStructureSetStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = RTStructureSetStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = generate_uid()
    dataset.FrameOfReferenceUID = frame_uid
    dataset.Modality = "RTSTRUCT"
    dataset.StructureSetLabel = "SYNTHETIC"
    referenced_frame = Dataset()
    referenced_frame.FrameOfReferenceUID = second_frame_uid or frame_uid
    dataset.ReferencedFrameOfReferenceSequence = [referenced_frame]

    definition = Dataset()
    definition.ROINumber = roi_number
    definition.ReferencedFrameOfReferenceUID = frame_uid
    definition.ROIName = "TARGET"
    definition.ROIGenerationAlgorithm = "MANUAL"
    definitions = [definition]
    roi_contours: list[Dataset] = []
    selected_contours = contours or [
        _contour(
            [
                _world_point(1, 1, 2),
                _world_point(1, 4, 2),
                _world_point(4, 4, 2),
                _world_point(4, 1, 2),
            ]
        )
    ]
    contour_group = Dataset()
    contour_group.ReferencedROINumber = roi_number
    contour_group.ContourSequence = selected_contours
    roi_contours.append(contour_group)

    if second_roi:
        second_definition = Dataset()
        second_definition.ROINumber = roi_number + 1
        second_definition.ReferencedFrameOfReferenceUID = frame_uid
        second_definition.ROIName = "TARGET"
        second_definition.ROIGenerationAlgorithm = "MANUAL"
        definitions.append(second_definition)
        second_group = Dataset()
        second_group.ReferencedROINumber = roi_number + 1
        second_group.ContourSequence = [
            _contour(
                [
                    _world_point(0, 0, 0),
                    _world_point(0, 1, 0),
                    _world_point(1, 1, 0),
                    _world_point(1, 0, 0),
                ]
            )
        ]
        roi_contours.append(second_group)

    dataset.StructureSetROISequence = definitions
    dataset.ROIContourSequence = roi_contours
    _write_dataset(dataset, path)


def _ct_file(
    path: Path,
    frame_uid: str,
    *,
    shape: tuple[int, int, int] = (3, 5, 5),
    values: np.ndarray | None = None,
    window: tuple[float, float] | None = (0.0, 400.0),
    photometric: str = "MONOCHROME2",
) -> None:
    frames, rows, columns = shape
    sop_instance_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = CTImageStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = generate_uid()
    dataset.FrameOfReferenceUID = frame_uid
    dataset.Modality = "CT"
    dataset.Rows = rows
    dataset.Columns = columns
    if frames > 1:
        dataset.NumberOfFrames = frames
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = photometric
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelSpacing = [2.0, 4.0]
    dataset.SliceThickness = 2.0
    dataset.SpacingBetweenSlices = 2.0
    dataset.ImagePositionPatient = [0.0, 0.0, 0.0]
    dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    dataset.RescaleSlope = 1.0
    dataset.RescaleIntercept = -1000.0
    if window is not None:
        dataset.WindowCenter = window[0]
        dataset.WindowWidth = window[1]
    raw_values = (
        values if values is not None else np.arange(np.prod(shape), dtype=np.uint16).reshape(shape)
    )
    dataset.PixelData = np.asarray(raw_values, dtype=np.uint16).tobytes()
    _write_dataset(dataset, path)


def test_dvh_decodes_dicom_geometry_and_returns_physical_metrics(tmp_path: Path) -> None:
    dose_path = tmp_path / "dose.dcm"
    structure_path = tmp_path / "structures.dcm"
    frame_uid = _dose_file(dose_path)
    _structure_file(structure_path, frame_uid)

    analysis = analyze_dvh(
        dose_path,
        structure_path,
        roi_number=1,
        dx_percentages=[2, 50, 95],
        vx_doses_gy=[0, 2, 3],
    )

    assert analysis.result["schema_version"] == "visual-dose-dvh.result.v1"
    assert analysis.result["roi"] == {
        "roi_number": 1,
        "name": "TARGET",
        "contour_count": 1,
        "contour_plane_count": 1,
    }
    assert analysis.result["dose"]["mean_gy"] == 2.0
    assert analysis.result["metrics"]["Dmin_gy"] == 2.0
    assert analysis.result["metrics"]["Dmax_gy"] == 2.0
    assert analysis.result["metrics"]["Dx_gy"]["D95_gy"] == 2.0
    assert analysis.result["metrics"]["Vx_percent"]["V0_gy"] == 100.0
    assert analysis.result["metrics"]["Vx_percent"]["V3_gy"] == 0.0
    assert analysis.result["coverage"]["status"] == "FULL"
    assert analysis.result["geometry"]["pixel_spacing_mm"] == [2.0, 4.0]
    assert any(item["code"] == "DVH_DOSE_ONLY_MODE" for item in analysis.warnings)


def test_roi_selector_uses_number_when_names_are_duplicate(tmp_path: Path) -> None:
    dose_path = tmp_path / "dose.dcm"
    structure_path = tmp_path / "structures.dcm"
    frame_uid = _dose_file(dose_path)
    _structure_file(structure_path, frame_uid, second_roi=True)

    rois = list_structure_rois(structure_path)
    assert [(item["roi_number"], item["name"]) for item in rois] == [(1, "TARGET"), (2, "TARGET")]

    selected = analyze_dvh(dose_path, structure_path, roi_number=2)
    assert selected.result["roi"]["roi_number"] == 2
    assert selected.result["coverage"]["frame_counts"][0] > 0
    assert selected.result["coverage"]["frame_counts"][2] == 0


def test_multiple_contours_use_even_odd_parity_for_a_hole(tmp_path: Path) -> None:
    dose_path = tmp_path / "dose.dcm"
    structure_path = tmp_path / "structures.dcm"
    frame_uid = _dose_file(dose_path)
    outer = _contour(
        [
            _world_point(-0.5, -0.5, 2),
            _world_point(-0.5, 4.5, 2),
            _world_point(4.5, 4.5, 2),
            _world_point(4.5, -0.5, 2),
        ]
    )
    inner = _contour(
        [
            _world_point(1, 1, 2),
            _world_point(1, 4, 2),
            _world_point(4, 4, 2),
            _world_point(4, 1, 2),
        ]
    )
    _structure_file(structure_path, frame_uid, contours=[outer, inner])

    with_hole = analyze_dvh(dose_path, structure_path, roi_number=1)
    assert with_hole.result["roi"]["contour_count"] == 2
    assert 0 < with_hole.result["coverage"]["selected_voxel_count"] < 25


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("frame", "DICOM_FRAME_MISMATCH"),
        ("units", "DVH_DOSE_UNITS_UNSUPPORTED"),
        ("contour", "DICOM_CAPABILITY_UNSUPPORTED"),
        ("single_frame_spacing", "DVH_SLICE_SPACING_UNAVAILABLE"),
    ],
)
def test_dvh_rejects_unsafe_or_ambiguous_inputs(tmp_path: Path, case: str, code: str) -> None:
    dose_path = tmp_path / "dose.dcm"
    structure_path = tmp_path / "structures.dcm"
    dose_kwargs: dict[str, object] = {}
    if case == "units":
        dose_kwargs["dose_units"] = "RELATIVE"
    if case == "single_frame_spacing":
        dose_kwargs["shape"] = (1, 5, 5)
        dose_kwargs["offsets"] = [0.0]
    frame_uid = _dose_file(dose_path, **dose_kwargs)
    if case == "frame":
        other_frame_uid = generate_uid()
        _structure_file(structure_path, other_frame_uid, second_frame_uid=other_frame_uid)
    elif case == "contour":
        _structure_file(
            structure_path,
            frame_uid,
            contours=[
                _contour(
                    [
                        _world_point(1, 1, 2),
                        _world_point(1, 4, 2),
                        _world_point(4, 4, 2),
                    ],
                    geometric_type="OPEN_PLANAR",
                )
            ],
        )
    else:
        _structure_file(structure_path, frame_uid)

    with pytest.raises(DVHEngineError) as raised:
        analyze_dvh(dose_path, structure_path, roi_number=1)
    assert raised.value.code == code


def test_full_coverage_rejects_outside_contour_but_overlap_mode_is_explicit(
    tmp_path: Path,
) -> None:
    dose_path = tmp_path / "dose.dcm"
    structure_path = tmp_path / "structures.dcm"
    frame_uid = _dose_file(dose_path)
    outside = _contour(
        [
            _world_point(1, 3, 2),
            _world_point(1, 7, 2),
            _world_point(4, 7, 2),
            _world_point(4, 3, 2),
        ]
    )
    _structure_file(structure_path, frame_uid, contours=[outside])

    with pytest.raises(DVHEngineError) as raised:
        analyze_dvh(dose_path, structure_path, roi_number=1, coverage_policy="FULL_ROI")
    assert raised.value.code == "DVH_INCOMPLETE_COVERAGE"

    overlap = analyze_dvh(
        dose_path,
        structure_path,
        roi_number=1,
        coverage_policy="OVERLAP_ONLY",
    )
    assert overlap.result["coverage"]["status"] == "OVERLAP_ONLY"
    assert overlap.result["coverage"]["coverage_percent"] is None
    assert any(item["code"] == "DVH_PARTIAL_COVERAGE" for item in overlap.warnings)


def test_committed_staging_fixture_matches_the_dose_grid() -> None:
    root = Path(__file__).resolve().parents[3]
    analysis = analyze_dvh(
        root / "docs" / "fixtures" / "gamma-rtdose-v1-smoke.dcm",
        root / "docs" / "fixtures" / "p17-rtstruct-v1-smoke.dcm",
        roi_number=1,
    )

    assert analysis.result["roi"]["name"] == "P17_TARGET"
    assert analysis.result["coverage"]["status"] == "FULL"
    assert analysis.result["coverage"]["selected_voxel_count"] == 4
    assert analysis.result["dose"]["mean_gy"] == 6.5
    assert analysis.result["metrics"]["Dx_gy"]["D95_gy"] == 5.15


def test_ct_preview_returns_hu_slice_patient_lps_overlay_and_crosshair(tmp_path: Path) -> None:
    dose_path = tmp_path / "dose.dcm"
    structure_path = tmp_path / "structures.dcm"
    ct_path = tmp_path / "ct.dcm"
    frame_uid = _dose_file(dose_path)
    _structure_file(structure_path, frame_uid)
    _ct_file(ct_path, frame_uid)

    preview = create_ct_preview(
        ct_path,
        dose_path,
        frame_index=1,
        structure_path=structure_path,
        roi_number=1,
    )

    assert preview["schema_version"] == "visual-dose-ct-preview.v1"
    assert preview["ct"]["frame_count"] == 3
    assert preview["ct"]["value_unit"] == "HU"
    assert len(preview["ct"]["display_pixels"]) == 25
    assert preview["registration"]["mode"] == "SHARED_FRAME_OF_REFERENCE"
    assert preview["registration"]["overlay_available"] is True
    assert preview["registration"]["crosshair"]["visible"] is True
    assert preview["overlay"]["valid_pixel_count"] == 25
    assert any(preview["overlay"]["roi_mask"])
    assert (
        len(preview["registration"]["plane_mapping_matrix_dose_row_col_to_ct_frame_row_column"])
        == 3
    )
    assert preview["result_sha256"]


def test_ct_preview_defaults_window_and_rejects_unsafe_frame_or_resource(tmp_path: Path) -> None:
    dose_path = tmp_path / "dose.dcm"
    ct_path = tmp_path / "ct.dcm"
    frame_uid = _dose_file(dose_path)
    _ct_file(ct_path, frame_uid, window=None)

    preview = create_ct_preview(ct_path, dose_path, frame_index=2)
    assert preview["ct"]["frame_index"] == 2
    assert any(item["code"] == "CT_WINDOW_DEFAULTED" for item in preview["warnings"])

    with pytest.raises(DVHEngineError, match="outside the available frame range") as frame_error:
        create_ct_preview(ct_path, dose_path, frame_index=3)
    assert frame_error.value.code == "DICOM_GEOMETRY_INVALID"

    with pytest.raises(DVHEngineError) as resource_error:
        create_ct_preview(ct_path, dose_path, max_ct_pixels=10)
    assert resource_error.value.code == "DVH_RESOURCE_LIMIT"
