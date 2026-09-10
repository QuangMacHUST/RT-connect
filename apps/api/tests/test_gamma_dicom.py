from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pydicom
import pytest
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, RTDoseStorage, RTPlanStorage, generate_uid

from rt_connect_api.services.artifact_validation import validate_dicom
from rt_connect_api.services.gamma_engine import (
    GammaEngineError,
    calculate_gamma_from_paths,
    load_gamma_dataset,
)

FRAME_UID = "1.2.826.0.1.3680043.8.498.999.4"


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
        "coordinate_frame": {
            "basis": "PATIENT_LPS",
            "frame_id": FRAME_UID,
            "frame_of_reference_uid": FRAME_UID,
            "axis_order": ["z", "y", "x"],
            "transform_to_reference": {
                "direction": "SOURCE_TO_REFERENCE",
                "units": "mm",
                "matrix": [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                "source": {
                    "type": "synthetic-shared-frame",
                    "version": "fixture-v1",
                    "sha256": "d" * 64,
                },
            },
        },
        "values": {"encoding": "inline-float32", "inline": values},
    }
    return json.dumps(payload).encode("utf-8")


def _write_rtdose(path: Path, values: list[int], frame_uid: str = FRAME_UID) -> None:
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
    dataset.FrameOfReferenceUID = frame_uid
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
    dataset.DoseGridScaling = 0.01
    dataset.DoseUnits = "GY"
    dataset.DoseType = "PHYSICAL"
    dataset.DoseSummationType = "PLAN"
    referenced_plan = Dataset()
    referenced_plan.ReferencedSOPClassUID = RTPlanStorage
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


def test_standard_rtdose_gy_scaling_can_be_compared_with_3d_measurement(tmp_path: Path) -> None:
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
    assert {"RTDOSE_GRID_VALID", "RTDOSE_GEOMETRY_VALID", "RTDOSE_DOSE_UNITS_VALID"}.issubset(codes)


def test_rtdose_rejects_non_axial_orientation_before_gamma(tmp_path: Path) -> None:
    rtdose = tmp_path / "oblique-reference.dcm"
    _write_rtdose(rtdose, [100, 200, 300, 400, 500, 600, 700, 800])
    dataset = pydicom.dcmread(rtdose)
    dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    dataset.save_as(rtdose, write_like_original=False)

    with pytest.raises(GammaEngineError) as error:
        load_gamma_dataset(rtdose)

    assert error.value.code == "GAMMA_DICOM_ORIENTATION_UNSUPPORTED"


def test_rtdose_rejects_unsupported_dose_units_without_inference(tmp_path: Path) -> None:
    rtdose = tmp_path / "unknown-unit-reference.dcm"
    _write_rtdose(rtdose, [100, 200, 300, 400, 500, 600, 700, 800])
    dataset = pydicom.dcmread(rtdose)
    dataset.DoseUnits = "UNKNOWN"
    dataset.save_as(rtdose, write_like_original=False)

    with pytest.raises(GammaEngineError) as error:
        load_gamma_dataset(rtdose)

    assert error.value.code == "GAMMA_UNITS_UNSUPPORTED"


def test_rtdose_rejects_non_positive_spacing(tmp_path: Path) -> None:
    rtdose = tmp_path / "invalid-spacing-reference.dcm"
    _write_rtdose(rtdose, [100, 200, 300, 400, 500, 600, 700, 800])
    dataset = pydicom.dcmread(rtdose)
    dataset.PixelSpacing = [0.0, 1.0]
    dataset.save_as(rtdose, write_like_original=False)

    with pytest.raises(GammaEngineError) as error:
        load_gamma_dataset(rtdose)

    assert error.value.code == "GAMMA_DICOM_GRID_INVALID"


def test_rtdose_rejects_missing_frame_of_reference(tmp_path: Path) -> None:
    rtdose = tmp_path / "missing-frame-reference.dcm"
    _write_rtdose(rtdose, [100, 200, 300, 400, 500, 600, 700, 800])
    dataset = pydicom.dcmread(rtdose)
    del dataset.FrameOfReferenceUID
    dataset.save_as(rtdose, write_like_original=False)

    with pytest.raises(GammaEngineError) as error:
        load_gamma_dataset(rtdose)

    assert error.value.code == "GAMMA_COORDINATE_FRAME_MISSING"


def test_measurement_rejects_non_identity_transform_until_adapter_exists(tmp_path: Path) -> None:
    measurement = tmp_path / "translated.json"
    payload = json.loads(_measurement_bytes("translated", [1.0] * 8).decode("utf-8"))
    payload["coordinate_frame"]["transform_to_reference"]["matrix"][0][3] = 1.0
    measurement.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(GammaEngineError) as error:
        load_gamma_dataset(measurement)

    assert error.value.code == "GAMMA_TRANSFORM_UNSUPPORTED"
