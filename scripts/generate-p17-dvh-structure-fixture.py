"""Generate the deterministic synthetic RTSTRUCT used by the P17 DVH smoke.

The fixture is intentionally non-patient data.  Its FrameOfReferenceUID and
geometry match ``gamma-rtdose-v1-smoke.dcm`` so that the staging browser smoke
can exercise the real upload, validation, ROI selection and DVH workflow.
"""

from __future__ import annotations

from pathlib import Path

from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, RTStructureSetStorage


FIXTURE_UID_ROOT = "1.2.826.0.1.3680043.8.498.999"
FRAME_OF_REFERENCE_UID = f"{FIXTURE_UID_ROOT}.4"


def _contour(points: list[tuple[float, float, float]]) -> Dataset:
    item = Dataset()
    item.ContourGeometricType = "CLOSED_PLANAR"
    item.NumberOfContourPoints = len(points)
    item.ContourData = [coordinate for point in points for coordinate in point]
    return item


def _dose_grid_point(row: float, column: float, z: float) -> tuple[float, float, float]:
    # The committed P8 RTDOSE fixture has 1 mm row/column spacing.  The
    # rectangle below encloses all four pixel centres in the second frame.
    return (column, row, z)


def build_dataset() -> FileDataset:
    sop_instance_uid = f"{FIXTURE_UID_ROOT}.7"
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = RTStructureSetStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = f"{FIXTURE_UID_ROOT}.5"

    dataset = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = RTStructureSetStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = f"{FIXTURE_UID_ROOT}.2"
    dataset.SeriesInstanceUID = f"{FIXTURE_UID_ROOT}.8"
    dataset.FrameOfReferenceUID = FRAME_OF_REFERENCE_UID
    dataset.Modality = "RTSTRUCT"
    dataset.StructureSetLabel = "P17_SYNTHETIC"

    referenced_frame = Dataset()
    referenced_frame.FrameOfReferenceUID = FRAME_OF_REFERENCE_UID
    dataset.ReferencedFrameOfReferenceSequence = [referenced_frame]

    roi_definition = Dataset()
    roi_definition.ROINumber = 1
    roi_definition.ReferencedFrameOfReferenceUID = FRAME_OF_REFERENCE_UID
    roi_definition.ROIName = "P17_TARGET"
    roi_definition.ROIGenerationAlgorithm = "MANUAL"
    dataset.StructureSetROISequence = [roi_definition]

    contour_group = Dataset()
    contour_group.ReferencedROINumber = 1
    contour_group.ContourSequence = [
        _contour(
            [
                _dose_grid_point(-0.5, -0.5, 1.0),
                _dose_grid_point(-0.5, 1.5, 1.0),
                _dose_grid_point(1.5, 1.5, 1.0),
                _dose_grid_point(1.5, -0.5, 1.0),
            ]
        )
    ]
    dataset.ROIContourSequence = [contour_group]
    return dataset


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "docs" / "fixtures" / "p17-rtstruct-v1-smoke.dcm"
    dataset = build_dataset()
    dataset.save_as(output, write_like_original=False)
    print(output)


if __name__ == "__main__":
    main()
