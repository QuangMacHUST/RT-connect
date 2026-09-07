"""Generate the small synthetic RTDOSE fixture used by the P8 staging smoke."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, RTDoseStorage, generate_uid


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "docs" / "fixtures" / "gamma-rtdose-v1-smoke.dcm"
    sop_instance_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = RTDoseStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(output, {}, file_meta=file_meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = RTDoseStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = generate_uid()
    dataset.FrameOfReferenceUID = generate_uid()
    dataset.Modality = "RTDOSE"
    dataset.Rows = 2
    dataset.Columns = 2
    dataset.NumberOfFrames = 2
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelSpacing = [1.0, 1.0]
    dataset.GridFrameOffsetVector = [0.0, 1.0]
    dataset.ImagePositionPatient = [0.0, 0.0, 0.0]
    dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    dataset.DoseGridScaling = 1.0
    dataset.DoseUnits = "CGY"
    dataset.DoseType = "PHYSICAL"
    dataset.DoseSummationType = "PLAN"
    referenced_plan = Dataset()
    referenced_plan.ReferencedSOPClassUID = generate_uid()
    referenced_plan.ReferencedSOPInstanceUID = generate_uid()
    dataset.ReferencedRTPlanSequence = [referenced_plan]
    dataset.PixelData = np.asarray([100, 200, 300, 400, 500, 600, 700, 800], dtype=np.uint16).tobytes()
    dataset.save_as(output, write_like_original=False)
    print(output)


if __name__ == "__main__":
    main()
