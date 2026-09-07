from __future__ import annotations

import hashlib
import json
from io import BytesIO
from typing import Any

import numpy as np
from fastapi.testclient import TestClient
from pydicom import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

from rt_connect_api.api.artifacts import _storage
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from test_workspace import _workspace_client


def _ct_bytes() -> bytes:
    sop_instance_uid = generate_uid()
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = CTImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(
        "ct.dcm",
        {},
        file_meta=file_meta,
        preamble=b"\0" * 128,
    )
    dataset.is_little_endian = True
    dataset.is_implicit_VR = False
    dataset.SOPClassUID = CTImageStorage
    dataset.SOPInstanceUID = sop_instance_uid
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = generate_uid()
    dataset.FrameOfReferenceUID = generate_uid()
    dataset.Modality = "CT"
    dataset.Rows = 2
    dataset.Columns = 2
    dataset.PixelSpacing = [1.0, 1.0]
    dataset.ImagePositionPatient = [0.0, 0.0, 0.0]
    dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelData = np.array([[1, 2], [3, 4]], dtype=np.uint16).tobytes()
    output = BytesIO()
    dataset.save_as(output, write_like_original=False)
    return output.getvalue()


def _measurement_bytes(*, complete: bool) -> bytes:
    payload: dict[str, Any] = {
        "schema_version": "gamma.measurement.v1",
        "dataset_id": "synthetic-measurement-001",
        "data_type": "dose",
        "values": {"encoding": "inline-float32", "inline": [1.0, 2.0, 3.0, 4.0]},
    }
    if complete:
        payload.update(
            {
                "units": {"dose": "GY", "position": "mm"},
                "grid": {"shape": [2, 2], "spacing_mm": [1.0, 1.0]},
                "acquisition": {"detector": "synthetic", "measured_at": "2026-09-07T00:00:00Z"},
                "source": {"filename": "measurement.json", "sha256": "a" * 64},
            }
        )
    return json.dumps(payload).encode("utf-8")


def _case(client: TestClient, organization_id: str) -> str:
    folder = client.post(
        f"/api/v1/organizations/{organization_id}/folders", json={"name": "P6 fixtures"}
    )
    assert folder.status_code == 201, folder.text
    sites = client.get(f"/api/v1/organizations/{organization_id}/sites").json()["items"]
    machines = client.get(
        f"/api/v1/organizations/{organization_id}/sites/{sites[0]['id']}/machines"
    ).json()["items"]
    case = client.post(
        f"/api/v1/organizations/{organization_id}/qa-cases",
        json={
            "site_id": sites[0]["id"],
            "machine_id": machines[0]["id"],
            "primary_folder_id": folder.json()["id"],
            "qa_type": "PSQA",
            "qa_cycle": "DAILY",
            "performed_at": "2026-09-07T00:00:00Z",
            "title": "P6 synthetic QA case",
        },
    )
    assert case.status_code == 201, case.text
    return case.json()["id"]


def test_upload_manifest_validate_and_duplicate_are_organization_scoped() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        payload = _ct_bytes()
        uploaded = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("synthetic-ct.dcm", payload, "application/dicom")},
            data={"artifact_type": "DICOM", "logical_role": "CT"},
        )
        assert uploaded.status_code == 201, uploaded.text
        artifact = uploaded.json()
        assert artifact["sha256"] == hashlib.sha256(payload).hexdigest()
        assert artifact["data_status"] == "UPLOADED"
        object_key = next(iter(storage.objects))
        assert storage.objects[object_key] == payload

        manifest = client.get(f"/api/v1/artifacts/{artifact['id']}/manifest")
        assert manifest.status_code == 200
        assert manifest.json()["checksum_at_use"] == artifact["sha256"]
        validation = client.post(f"/api/v1/artifacts/{artifact['id']}/validate")
        assert validation.status_code == 200, validation.text
        assert validation.json()["result"] == "VALID"
        assert client.get(f"/api/v1/artifacts/{artifact['id']}").json()["data_status"] == "VALID"

        download = client.get(f"/api/v1/artifacts/{artifact['id']}/download")
        assert download.status_code == 200
        assert download.json()["url"].startswith("memory://artifact/")

        duplicate = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("same-content.dcm", payload, "application/dicom")},
            data={"artifact_type": "DICOM", "logical_role": "REFERENCE"},
        )
        assert duplicate.status_code == 200, duplicate.text
        assert duplicate.json()["duplicate"] is True
        assert duplicate.json()["id"] == artifact["id"]


def test_measurement_validation_explains_missing_units_and_grid() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        uploaded = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={
                "file": ("ambiguous.json", _measurement_bytes(complete=False), "application/json")
            },
            data={"artifact_type": "MEASUREMENT", "logical_role": "MEASUREMENT"},
        )
        assert uploaded.status_code == 201, uploaded.text
        artifact_id = uploaded.json()["id"]
        validation = client.post(f"/api/v1/artifacts/{artifact_id}/validate")
        assert validation.status_code == 200, validation.text
        body = validation.json()
        assert body["result"] == "INVALID"
        codes = {item["code"] for item in body["errors"]}
        assert {"MEASUREMENT_UNITS_MISSING", "MEASUREMENT_GRID_INVALID"}.issubset(codes)
        assert client.get(f"/api/v1/artifacts/{artifact_id}").json()["data_status"] == "INVALID"
