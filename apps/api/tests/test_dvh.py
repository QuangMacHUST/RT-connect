from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from pydicom.uid import generate_uid
from sqlalchemy import select

from rt_connect_api.api.artifacts import _storage as artifact_storage
from rt_connect_api.api.dvh import _storage as dvh_storage
from rt_connect_api.db.models import InputManifest
from rt_connect_api.db.session import get_session
from rt_connect_api.services.object_storage import InMemoryObjectStorage, ObjectStorageError
from test_artifacts import _case
from test_dvh_engine import _ct_file, _dose_file, _structure_file
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


class _UnavailableObjectStorage(InMemoryObjectStorage):
    """Storage fault double: metadata exists, but bytes cannot be downloaded."""

    def download_to_path(self, key: str, destination: Path) -> None:
        raise ObjectStorageError(f"synthetic storage outage for {key}")


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
        ct_path = tmp_path / "ct.dcm"
        _ct_file(ct_path, frame_uid)
        ct = _upload_dicom(client, case_id, "synthetic-ct.dcm", ct_path.read_bytes(), "CT")
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

        ct_preview = client.get(
            f"{base}/ct-preview",
            params={
                "dose_artifact_id": dose["id"],
                "ct_artifact_id": ct["id"],
                "structure_artifact_id": structure["id"],
                "roi_number": 1,
                "frame_index": 1,
            },
        )
        assert ct_preview.status_code == 200, ct_preview.text
        assert ct_preview.json()["schema_version"] == "visual-dose-ct-preview.v1"
        assert ct_preview.json()["registration"]["overlay_available"] is True
        assert ct_preview.json()["overlay"]["valid_pixel_count"] == 25

        created = client.post(f"{base}/runs", json=body)
        assert created.status_code == 201, created.text
        run = created.json()
        assert run["status"] == "COMPLETED"
        assert run["engine_version"] == "p17-dvh-1.0.0"
        assert run["result_snapshot"]["result_sha256"]
        assert run["input_snapshot"]["dose"]["manifest_checksum_at_use"] == dose["sha256"]

        ct_body = dict(body)
        ct_body.update(
            {
                "ct_artifact_id": ct["id"],
                "idempotency_key": "dvh-api-ct-001",
            }
        )
        ct_run_response = client.post(f"{base}/runs", json=ct_body)
        assert ct_run_response.status_code == 201, ct_run_response.text
        ct_run = ct_run_response.json()
        assert ct_run["ct_artifact_id"] == ct["id"]
        assert ct_run["input_snapshot"]["ct"]["artifact_id"] == ct["id"]
        assert (
            ct_run["result_snapshot"]["ct"]["frame_of_reference_uid"]
            == frame_uid
        )
        assert ct_run["result_snapshot"]["visual_preview"]["mode"] == (
            "DOSE_WITH_CT_FRAME_LINK"
        )

        limit = client.post(
            f"/api/v1/organizations/{organization.id}/biological/library",
            json={
                "entry_key": "TARGET_D95_LIMIT",
                "entry_type": "DOSE_LIMIT",
                "name": "Synthetic target D95 minimum",
                "tissue_or_oar": "Target",
                "metric_key": "D95",
                "operator": "MIN",
                "limit_value": 1.5,
                "unit": "Gy",
                "source_type": "INTERNAL",
                "reference_status": "AVAILABLE",
                "publish": True,
            },
        )
        assert limit.status_code == 201, limit.text
        limited_body = dict(body)
        limited_body.update(
            {
                "idempotency_key": "dvh-api-limit-001",
                "limit_entry_id": limit.json()["id"],
            }
        )
        limited_validation = client.post(
            f"{base}/validate",
            json=_validation_body(limited_body),
        )
        assert limited_validation.status_code == 200, limited_validation.text
        assert limited_validation.json()["valid"] is True
        assert limited_validation.json()["preview"]["limit_evaluation"]["actual"] == 2.0
        assert limited_validation.json()["preview"]["limit_evaluation"]["margin"] == 0.5
        assert limited_validation.json()["preview"]["limit_evaluation"]["status"] == "PASS"

        limited = client.post(f"{base}/runs", json=limited_body)
        assert limited.status_code == 201, limited.text
        limited_run = limited.json()
        assert limited_run["input_snapshot"]["limit_binding"]["source_type"] == (
            "BIOLOGICAL_LIBRARY"
        )
        assert limited_run["result_snapshot"]["limit_evaluation"]["rule_status"] == "PASS"
        assert limited_run["result_snapshot"]["engine_result_sha256"]
        assert (
            limited_run["result_snapshot"]["result_sha256"]
            != (limited_run["result_snapshot"]["engine_result_sha256"])
        )

        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/qa-protocols",
            json={
                "protocol_key": "DVH_TARGET_REVIEW",
                "name": "Synthetic DVH target review",
                "qa_type": "DVH",
                "source_type": "INTERNAL",
                "rules": [
                    {
                        "metric_key": "d95",
                        "display_name": "Target D95 minimum",
                        "unit": "Gy",
                        "rule_type": "MIN",
                        "lower_limit": 1.5,
                        "required": True,
                        "sort_order": 0,
                    }
                ],
                "activate": True,
            },
        )
        assert protocol.status_code == 201, protocol.text
        protocol_body = dict(body)
        protocol_body.update(
            {
                "idempotency_key": "dvh-api-protocol-001",
                "protocol_version_id": protocol.json()["id"],
                "protocol_metric_key": "D95",
            }
        )
        protocol_validation = client.post(
            f"{base}/validate",
            json=_validation_body(protocol_body),
        )
        assert protocol_validation.status_code == 200, protocol_validation.text
        assert protocol_validation.json()["valid"] is True
        assert protocol_validation.json()["preview"]["limit_evaluation"]["source_type"] == (
            "QA_PROTOCOL"
        )
        protocol_run = client.post(f"{base}/runs", json=protocol_body)
        assert protocol_run.status_code == 201, protocol_run.text
        assert protocol_run.json()["input_snapshot"]["limit_binding"]["source_type"] == (
            "QA_PROTOCOL"
        )

        conflict_binding = _validation_body(limited_body)
        conflict_binding["protocol_version_id"] = protocol.json()["id"]
        conflict_response = client.post(f"{base}/validate", json=conflict_binding)
        assert conflict_response.status_code == 200, conflict_response.text
        assert conflict_response.json()["valid"] is False
        assert conflict_response.json()["errors"][0]["code"] == "DVH_LIMIT_BINDING_CONFLICT"

        missing_metric = _validation_body(limited_body)
        missing_metric["dx_percentages"] = [2, 50]
        missing_metric_response = client.post(f"{base}/validate", json=missing_metric)
        assert missing_metric_response.status_code == 200, missing_metric_response.text
        assert missing_metric_response.json()["valid"] is False
        assert missing_metric_response.json()["errors"][0]["code"] == (
            "DVH_LIMIT_METRIC_NOT_COMPUTED"
        )

        invalid_override = _validation_body(limited_body)
        invalid_override["limit_override"] = {"operator": "MAX"}
        invalid_override_response = client.post(f"{base}/validate", json=invalid_override)
        assert invalid_override_response.status_code == 200, invalid_override_response.text
        assert invalid_override_response.json()["valid"] is False
        assert invalid_override_response.json()["errors"][0]["code"] == (
            "DVH_LIMIT_OVERRIDE_INVALID"
        )

        report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "DVH",
                "source_id": limited_run["id"],
                "title": "Synthetic DVH report",
            },
        )
        assert report.status_code == 201, report.text
        assert report.json()["source_snapshot"]["source_type"] == "DVH"
        assert report.json()["source_snapshot"]["payload"]["id"] == limited_run["id"]
        assert (
            report.json()["source_snapshot"]["payload"]["result_snapshot"]["limit_evaluation"][
                "margin"
            ]
            == 0.5
        )

        replay = client.post(f"{base}/runs", json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == run["id"]
        assert client.get(f"{base}/runs").json()["total"] == 4
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


def test_dvh_api_storage_outage_is_explicit_and_does_not_create_a_run(tmp_path: Path) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[dvh_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        dose_path = tmp_path / "dose.dcm"
        structure_path = tmp_path / "structures.dcm"
        frame_uid = _dose_file(dose_path)
        _structure_file(structure_path, frame_uid)
        dose = _upload_dicom(client, case_id, "dose.dcm", dose_path.read_bytes(), "REFERENCE")
        structure = _upload_dicom(
            client, case_id, "structures.dcm", structure_path.read_bytes(), "RTSTRUCT"
        )
        body = _dvh_body(
            str(dose["id"]), str(structure["id"]), "dvh-api-storage-outage"
        )
        failing_storage = _UnavailableObjectStorage()
        client.app.dependency_overrides[artifact_storage] = lambda: failing_storage
        client.app.dependency_overrides[dvh_storage] = lambda: failing_storage

        base = f"/api/v1/organizations/{organization.id}/qa-cases/{case_id}/dvh"
        response = client.post(f"{base}/validate", json=_validation_body(body))

        assert response.status_code == 503, response.text
        assert response.json()["code"] == "DVH_STORAGE_UNAVAILABLE"
        assert client.get(f"{base}/runs").json()["total"] == 0


def test_dvh_input_discovery_requires_valid_manifest_matching_artifact_checksum(
    tmp_path: Path,
) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[dvh_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        dose_path = tmp_path / "dose.dcm"
        structure_path = tmp_path / "structures.dcm"
        frame_uid = _dose_file(dose_path)
        _structure_file(structure_path, frame_uid)
        dose = _upload_dicom(client, case_id, "dose.dcm", dose_path.read_bytes(), "REFERENCE")
        structure = _upload_dicom(
            client, case_id, "structures.dcm", structure_path.read_bytes(), "RTSTRUCT"
        )
        dependency = client.app.dependency_overrides[get_session]
        session_generator = dependency()
        session = next(session_generator)
        try:
            manifest = session.scalar(
                select(InputManifest).where(InputManifest.artifact_id == UUID(str(dose["id"])))
            )
            assert manifest is not None
            manifest.validation_summary = {"result": "PENDING"}
            session.commit()
        finally:
            session_generator.close()

        base = f"/api/v1/organizations/{organization.id}/qa-cases/{case_id}/dvh"
        choices = client.get(f"{base}/inputs")
        assert choices.status_code == 200, choices.text
        assert choices.json()["dose_artifacts"] == []
        assert [item["id"] for item in choices.json()["structure_artifacts"]] == [
            structure["id"]
        ]

        session_generator = dependency()
        session = next(session_generator)
        try:
            manifest = session.scalar(
                select(InputManifest).where(InputManifest.artifact_id == UUID(str(dose["id"])))
            )
            assert manifest is not None
            manifest.validation_summary = {"result": "VALID"}
            manifest.checksum_at_use = "not-a-checksum"
            session.commit()
        finally:
            session_generator.close()

        body = _dvh_body(str(dose["id"]), str(structure["id"]), "dvh-manifest-checksum")
        malformed = client.post(f"{base}/validate", json=_validation_body(body))
        assert malformed.status_code == 422, malformed.text
        assert malformed.json()["code"] == "DVH_INPUT_MANIFEST_INVALID"

        session_generator = dependency()
        session = next(session_generator)
        try:
            manifest = session.scalar(
                select(InputManifest).where(InputManifest.artifact_id == UUID(str(dose["id"])))
            )
            assert manifest is not None
            manifest.checksum_at_use = "0" * 64
            session.commit()
        finally:
            session_generator.close()

        blocked = client.post(f"{base}/validate", json=_validation_body(body))
        assert blocked.status_code == 422, blocked.text
        assert blocked.json()["code"] == "DVH_INPUT_MANIFEST_INVALID"


def test_dvh_ct_preview_api_covers_frame_mismatch_no_overlap_and_resource_limit(
    tmp_path: Path,
) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[dvh_storage] = lambda: storage
        case_id = _case(client, str(organization.id))

        dose_path = tmp_path / "dose.dcm"
        frame_uid = _dose_file(dose_path)
        dose = _upload_dicom(client, case_id, "dose.dcm", dose_path.read_bytes(), "REFERENCE")
        base = f"/api/v1/organizations/{organization.id}/qa-cases/{case_id}/dvh"

        mismatch_ct_path = tmp_path / "mismatch-ct.dcm"
        _ct_file(mismatch_ct_path, generate_uid())
        mismatch_ct = _upload_dicom(
            client,
            case_id,
            "mismatch-ct.dcm",
            mismatch_ct_path.read_bytes(),
            "CT",
        )
        mismatch = client.get(
            f"{base}/ct-preview",
            params={
                "dose_artifact_id": dose["id"],
                "ct_artifact_id": mismatch_ct["id"],
                "frame_index": 0,
            },
        )
        assert mismatch.status_code == 422, mismatch.text
        assert mismatch.json()["code"] == "DICOM_FRAME_MISMATCH"

        matching_ct_path = tmp_path / "matching-ct.dcm"
        _ct_file(matching_ct_path, frame_uid, origin_z=20.0)
        matching_ct = _upload_dicom(
            client,
            case_id,
            "matching-ct.dcm",
            matching_ct_path.read_bytes(),
            "CT",
        )
        no_overlap = client.get(
            f"{base}/ct-preview",
            params={
                "dose_artifact_id": dose["id"],
                "ct_artifact_id": matching_ct["id"],
                "frame_index": 2,
            },
        )
        assert no_overlap.status_code == 200, no_overlap.text
        assert no_overlap.json()["registration"]["overlay_available"] is False
        assert no_overlap.json()["overlay"]["valid_pixel_count"] == 0
        assert any(
            item["code"] == "CT_DOSE_NO_OVERLAP" for item in no_overlap.json()["warnings"]
        )

        client.app.state.settings.dvh_max_ct_pixels = 10
        resource_limited = client.get(
            f"{base}/ct-preview",
            params={
                "dose_artifact_id": dose["id"],
                "ct_artifact_id": matching_ct["id"],
                "frame_index": 0,
            },
        )
        assert resource_limited.status_code == 422, resource_limited.text
        assert resource_limited.json()["code"] == "DVH_RESOURCE_LIMIT"
        assert client.get(f"{base}/runs").json()["total"] == 0


def test_dvh_ct_preview_rejects_changed_ct_bytes_after_validation(tmp_path: Path) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[dvh_storage] = lambda: storage
        case_id = _case(client, str(organization.id))

        dose_path = tmp_path / "dose.dcm"
        frame_uid = _dose_file(dose_path)
        dose = _upload_dicom(client, case_id, "dose.dcm", dose_path.read_bytes(), "REFERENCE")
        ct_path = tmp_path / "ct.dcm"
        _ct_file(ct_path, frame_uid)
        ct_payload = ct_path.read_bytes()
        ct = _upload_dicom(client, case_id, "ct.dcm", ct_payload, "CT")
        object_key = next(key for key, value in storage.objects.items() if value == ct_payload)
        storage.objects[object_key] = ct_payload + b"changed-after-validation"

        base = f"/api/v1/organizations/{organization.id}/qa-cases/{case_id}/dvh"
        response = client.get(
            f"{base}/ct-preview",
            params={
                "dose_artifact_id": dose["id"],
                "ct_artifact_id": ct["id"],
                "frame_index": 0,
            },
        )
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "DVH_SOURCE_CHANGED"
        assert client.get(f"{base}/runs").json()["total"] == 0
