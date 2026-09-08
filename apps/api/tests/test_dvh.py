from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from rt_connect_api.api.artifacts import _storage as artifact_storage
from rt_connect_api.api.dvh import _storage as dvh_storage
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from test_artifacts import _case
from test_dvh_engine import _dose_file, _structure_file
from test_workspace import _workspace_client


def _upload_dicom(
    client: TestClient, case_id: str, filename: str, payload: bytes, logical_role: str
) -> dict[str, object]:
    uploaded = client.post(
        f"/api/v1/qa-cases/{case_id}/artifacts",
        files={"file": (filename, payload, "application/dicom")},
        data={"artifact_type": "DICOM", "logical_role": logical_role},
    )
    assert uploaded.status_code == 201, uploaded.text
    artifact = uploaded.json()
    validation = client.post(f"/api/v1/artifacts/{artifact['id']}/validate")
    assert validation.status_code == 200, validation.text
    assert validation.json()["result"] == "VALID", validation.text
    return artifact


def _dvh_body(dose_id: str, structure_id: str, key: str = "dvh-api-001") -> dict[str, object]:
    return {
        "dose_artifact_id": dose_id,
        "structure_artifact_id": structure_id,
        "roi_number": 1,
        "coverage_policy": "FULL_ROI",
        "dx_percentages": [2, 50, 95],
        "vx_doses_gy": [0, 2, 3],
        "preview_limit": 4096,
        "idempotency_key": key,
    }


def _validation_body(body: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in body.items() if key != "idempotency_key"}


def test_dvh_api_validates_saves_replays_exports_and_scopes_inputs(tmp_path: Path) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[dvh_storage] = lambda: storage
        case_id = _case(client, str(organization.id))

        dose_path = tmp_path / "dose.dcm"
        structure_path = tmp_path / "structures.dcm"
        frame_uid = _dose_file(dose_path)
        _structure_file(structure_path, frame_uid)
        dose = _upload_dicom(
            client,
            case_id,
            "synthetic-dose.dcm",
            dose_path.read_bytes(),
            "REFERENCE",
        )
        structure = _upload_dicom(
            client,
            case_id,
            "synthetic-structures.dcm",
            structure_path.read_bytes(),
            "RTSTRUCT",
        )
        base = f"/api/v1/organizations/{organization.id}/qa-cases/{case_id}/dvh"

        inputs = client.get(f"{base}/inputs", params={"structure_artifact_id": structure["id"]})
        assert inputs.status_code == 200, inputs.text
        assert len(inputs.json()["dose_artifacts"]) == 1
        assert inputs.json()["rois"] == [{"roi_number": 1, "name": "TARGET", "contour_count": 1}]

        body = _dvh_body(str(dose["id"]), str(structure["id"]))
        validation = client.post(
            f"{base}/validate",
            json=_validation_body(body),
        )
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True
        assert validation.json()["preview"]["metrics"]["Dmean_gy"] == 2.0
        assert any(item["code"] == "DVH_DOSE_ONLY_MODE" for item in validation.json()["warnings"])

        created = client.post(f"{base}/runs", json=body)
        assert created.status_code == 201, created.text
        run = created.json()
        assert run["status"] == "COMPLETED"
        assert run["engine_version"] == "p17-dvh-1.0.0"
        assert run["result_snapshot"]["result_sha256"]
        assert run["input_snapshot"]["dose"]["manifest_checksum_at_use"] == dose["sha256"]

        replay = client.post(f"{base}/runs", json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == run["id"]
        assert client.get(f"{base}/runs").json()["total"] == 1
        assert client.get(f"{base}/runs/{run['id']}").json()["id"] == run["id"]

        conflict = deepcopy(body)
        conflict["dx_percentages"] = [50]
        conflict_response = client.post(f"{base}/runs", json=conflict)
        assert conflict_response.status_code == 409, conflict_response.text
        assert conflict_response.json()["code"] == "DVH_IDEMPOTENCY_CONFLICT"

        exported_json = client.get(f"{base}/runs/{run['id']}/export?export_format=JSON")
        assert exported_json.status_code == 200
        assert (
            exported_json.json()["result_snapshot"]["result_sha256"]
            == run["result_snapshot"]["result_sha256"]
        )
        exported_csv = client.get(f"{base}/runs/{run['id']}/export?export_format=CSV")
        assert exported_csv.status_code == 200
        assert "result_sha256" in exported_csv.text

        outsider = client.get(
            f"/api/v1/organizations/00000000-0000-0000-0000-000000000001/qa-cases/{case_id}/dvh/inputs"
        )
        assert outsider.status_code == 403
        assert outsider.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"


def test_dvh_api_rejects_archived_case_and_detects_changed_source(tmp_path: Path) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[dvh_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        dose_path = tmp_path / "dose.dcm"
        structure_path = tmp_path / "structures.dcm"
        frame_uid = _dose_file(dose_path)
        _structure_file(structure_path, frame_uid)
        dose_payload = dose_path.read_bytes()
        structure_payload = structure_path.read_bytes()
        dose = _upload_dicom(client, case_id, "dose.dcm", dose_payload, "REFERENCE")
        structure = _upload_dicom(client, case_id, "structures.dcm", structure_payload, "RTSTRUCT")
        base = f"/api/v1/organizations/{organization.id}/qa-cases/{case_id}/dvh"
        body = _dvh_body(str(dose["id"]), str(structure["id"]), "dvh-api-source-change")

        changed_key = next(key for key, value in storage.objects.items() if value == dose_payload)
        storage.objects[changed_key] = dose_payload + b"changed"
        changed = client.post(
            f"{base}/validate",
            json=_validation_body(body),
        )
        assert changed.status_code == 409, changed.text
        assert changed.json()["code"] == "DVH_SOURCE_CHANGED"

        archived = client.patch(f"/api/v1/qa-cases/{case_id}", json={"is_archived": True})
        assert archived.status_code == 200, archived.text
        blocked = client.post(
            f"{base}/validate",
            json=_validation_body(body),
        )
        assert blocked.status_code == 409, blocked.text
        assert blocked.json()["code"] == "QA_CASE_ARCHIVED"
