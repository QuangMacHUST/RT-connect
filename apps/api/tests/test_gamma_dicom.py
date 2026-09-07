from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, RTDoseStorage, generate_uid

from rt_connect_api.services.artifact_validation import validate_dicom
from rt_connect_api.services.gamma_engine import calculate_gamma_from_paths, load_gamma_dataset


def _configuration(dimensionality: str) -> dict[str, object]:
    return {
        "dimensionality": dimensionality,
        "dose_difference_percent": 3.0,
        "dose_difference_mode": "RELATIVE",
        "absolute_dose_difference_gy": None,
        "distance_to_agreement_mm": 3.0,
        "dose_threshold_percent": 0.0,
        "normalization": "GLOBAL",
        "interpolation": "GRID",
        "pass_rate_threshold_percent": 95.0,
        "histogram_bins": 10,
    }


def _measurement_bytes(dataset_id: str, values: list[float]) -> bytes:
    payload: dict[str, Any] = {
        "schema_version": "gamma.measurement.v1",
        "dataset_id": dataset_id,
        "data_type": "dose",
        "units": {"dose": "GY", "position": "mm"},
        "grid": {
            "shape": [2, 2, 2],
            "spacing_mm": [1.0, 1.0, 1.0],
            "origin_mm": [0.0, 0.0, 0.0],
        },
        "values": {"encoding": "inline-float32", "inline": values},
    }
    return json.dumps(payload).encode("utf-8")


def _write_rtdose(path: Path, values: list[int]) -> None:
    sop_instance_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = RTDoseStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(path, {}, file_meta=file_meta, preamble=b"\0" * 128)
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
    dataset.PixelData = np.asarray(values, dtype=np.uint16).tobytes()
    dataset.save_as(path, write_like_original=False)


def test_3d_measurement_grid_is_golden_pass(tmp_path: Path) -> None:
    reference = tmp_path / "reference.json"
    evaluation = tmp_path / "evaluation.json"
    values = [float(index) for index in range(1, 9)]
    reference.write_bytes(_measurement_bytes("reference-3d", values))
    evaluation.write_bytes(_measurement_bytes("evaluation-3d", values))

    result = calculate_gamma_from_paths(reference, evaluation, _configuration("3D"))

    assert result["engine_version"] == "gamma-nd-p8.2"
    assert result["dimensionality"] == "3D"
    assert result["overall_status"] == "PASS"
    assert result["metrics"]["evaluated_points"] == 8
    assert result["metrics"]["passing_points"] == 8
    assert result["reference_grid"]["shape"] == [2, 2, 2]


def test_rtdose_cgy_is_scaled_and_can_be_compared_with_3d_measurement(tmp_path: Path) -> None:
    rtdose = tmp_path / "reference.dcm"
    measurement = tmp_path / "evaluation.json"
    _write_rtdose(rtdose, [100, 200, 300, 400, 500, 600, 700, 800])
    measurement.write_bytes(
        _measurement_bytes("evaluation-json", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
    )

    loaded = load_gamma_dataset(rtdose)
    assert loaded.source_format == "dicom_rtdose"
    assert loaded.values.shape == (2, 2, 2)
    assert loaded.values.tolist() == [[[1.0, 2.0], [3.0, 4.0]], [[5.0, 6.0], [7.0, 8.0]]]
    result = calculate_gamma_from_paths(rtdose, measurement, _configuration("3D"))

    assert result["overall_status"] == "PASS"
    assert result["reference_grid"]["source_format"] == "dicom_rtdose"
    assert result["evaluation_grid"]["source_format"] == "measurement_json"
    assert result["metrics"]["pass_rate_percent"] == 100.0


def test_rtdose_metadata_validation_is_strict_enough_for_gamma(tmp_path: Path) -> None:
    rtdose = tmp_path / "validated-reference.dcm"
    _write_rtdose(rtdose, [100, 200, 300, 400, 500, 600, 700, 800])

    validation = validate_dicom(rtdose)

    assert validation.result == "VALID"
    codes = {item["code"] for item in validation.checks}
    assert {"RTDOSE_GRID_VALID", "RTDOSE_GEOMETRY_VALID", "RTDOSE_DOSE_UNITS_VALID"}.issubset(
        codes
    )
