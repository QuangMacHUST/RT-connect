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
from rt_connect_api.core.errors import DomainError
from rt_connect_api.services.object_storage import InMemoryObjectStorage, ObjectStorageError
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


def test_same_bytes_with_different_declared_type_are_not_silently_reused() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        payload = _measurement_bytes(complete=True)

        stored_as_dicom = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("measurement.json", payload, "application/json")},
            data={"artifact_type": "DICOM", "logical_role": "REFERENCE"},
        )
        assert stored_as_dicom.status_code == 201, stored_as_dicom.text

        stored_as_json = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("measurement.json", payload, "application/json")},
            data={"artifact_type": "JSON", "logical_role": "REFERENCE"},
        )
        assert stored_as_json.status_code == 201, stored_as_json.text
        assert stored_as_json.json()["duplicate"] is False
        assert stored_as_json.json()["artifact_type"] == "JSON"
        assert stored_as_json.json()["id"] != stored_as_dicom.json()["id"]

        # The declared DICOM contract must win over the browser's JSON MIME
        # hint and filename.  The object may be stored for provenance, but it
        # must be rejected before it can enter Gamma.
        dicom_validation = client.post(f"/api/v1/artifacts/{stored_as_dicom.json()['id']}/validate")
        assert dicom_validation.status_code == 200, dicom_validation.text
        dicom_body = dicom_validation.json()
        assert dicom_body["result"] == "INVALID"
        assert any(item["code"] == "ARTIFACT_TYPE_MISMATCH" for item in dicom_body["errors"])


def test_declared_json_rejects_a_real_dicom_payload() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        uploaded = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("measurement.json", _ct_bytes(), "application/json")},
            data={"artifact_type": "JSON", "logical_role": "REFERENCE"},
        )
        assert uploaded.status_code == 201, uploaded.text

        validation = client.post(f"/api/v1/artifacts/{uploaded.json()['id']}/validate")
        assert validation.status_code == 200, validation.text
        body = validation.json()
        assert body["result"] == "INVALID"
        assert any(item["code"] == "ARTIFACT_TYPE_MISMATCH" for item in body["errors"])


def test_upload_commit_failure_compensates_object_storage(monkeypatch) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        case_id = _case(client, str(organization.id))

        def fail_commit(_session) -> None:
            raise DomainError("ARTIFACT_CONFLICT", "synthetic metadata conflict", 409)

        monkeypatch.setattr("rt_connect_api.api.artifacts._commit_or_raise", fail_commit)
        response = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("synthetic-ct.dcm", _ct_bytes(), "application/dicom")},
            data={"artifact_type": "DICOM", "logical_role": "CT"},
        )

        assert response.status_code == 409, response.text
        assert response.json()["code"] == "ARTIFACT_CONFLICT"
        assert storage.objects == {}
        assert client.get(f"/api/v1/qa-cases/{case_id}/artifacts").json()["total"] == 0


def test_upload_cleanup_failure_returns_reconciliation_error(monkeypatch) -> None:
    class CleanupFailureStorage(InMemoryObjectStorage):
        def delete_object(self, key: str) -> None:
            raise ObjectStorageError("synthetic cleanup outage")

    storage = CleanupFailureStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        case_id = _case(client, str(organization.id))

        def fail_commit(_session) -> None:
            raise DomainError("ARTIFACT_CONFLICT", "synthetic metadata conflict", 409)

        monkeypatch.setattr("rt_connect_api.api.artifacts._commit_or_raise", fail_commit)
        response = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("synthetic-ct.dcm", _ct_bytes(), "application/dicom")},
            data={"artifact_type": "DICOM", "logical_role": "CT"},
        )

        assert response.status_code == 503, response.text
        assert response.json()["code"] == "ARTIFACT_PERSISTENCE_FAILED"
        assert len(storage.objects) == 1
        assert client.get(f"/api/v1/qa-cases/{case_id}/artifacts").json()["total"] == 0
