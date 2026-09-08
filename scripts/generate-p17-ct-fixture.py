"""Generate the deterministic synthetic CT fixture used by the P17 smoke.

The fixture is intentionally non-patient data.  It shares the Frame of
Reference and patient geometry of ``gamma-rtdose-v1-smoke.dcm`` so the
staging browser smoke can exercise CT decoding, HU/window display, dose
overlay, ROI overlay and the explicit no-overlap warning without relying on
an untracked local file.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian

FIXTURE_UID_ROOT = "1.2.826.0.1.3680043.8.498.999"
FRAME_OF_REFERENCE_UID = f"{FIXTURE_UID_ROOT}.4"


def build_dataset(output: Path) -> FileDataset:
    """Build a three-slice, two-by-two CT volume with stable DICOM metadata."""

    sop_instance_uid = f"{FIXTURE_UID_ROOT}.9"
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = f"{FIXTURE_UID_ROOT}.5"

    dataset = FileDataset(output, {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = CTImageStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = f"{FIXTURE_UID_ROOT}.2"
    dataset.SeriesInstanceUID = f"{FIXTURE_UID_ROOT}.10"
    dataset.FrameOfReferenceUID = FRAME_OF_REFERENCE_UID
    dataset.Modality = "CT"
    dataset.SeriesDescription = "P17 SYNTHETIC CT PREVIEW"
    dataset.Rows = 2
    dataset.Columns = 2
    dataset.NumberOfFrames = 3
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelSpacing = [1.0, 1.0]
    dataset.SliceThickness = 1.0
    dataset.SpacingBetweenSlices = 1.0
    dataset.ImagePositionPatient = [0.0, 0.0, 0.0]
    dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    dataset.RescaleSlope = 1.0
    dataset.RescaleIntercept = -1000.0
    dataset.WindowCenter = 100.0
    dataset.WindowWidth = 400.0
    # The three frames become HU values [0..60], [100..160] and [200..260].
    # Frame 1 overlaps the second RTDOSE plane; frame 2 is intentionally
    # outside the two-plane dose grid for the CT_DOSE_NO_OVERLAP smoke.
    raw_pixels = np.asarray(
        [
            1000,
            1020,
            1040,
            1060,
            1100,
            1120,
            1140,
            1160,
            1200,
            1220,
            1240,
            1260,
        ],
        dtype=np.uint16,
    )
    dataset.PixelData = raw_pixels.tobytes()
    return dataset


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "docs" / "fixtures" / "p17-ct-v1-smoke.dcm"
    dataset = build_dataset(output)
    dataset.save_as(output, write_like_original=False)
    print(output)


if __name__ == "__main__":
    main()
