from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from rt_connect_api.api.reports import _storage as report_storage
from rt_connect_api.services.object_storage import InMemoryObjectStorage, ObjectStorageError
from test_workspace import _workspace_client


class _CleanupFailingStorage(InMemoryObjectStorage):
    def delete_object(self, key: str) -> None:
        raise ObjectStorageError("synthetic cleanup failure")


def _qa_case(client: TestClient, organization_id: str) -> str:
    folder = client.post(
        f"/api/v1/organizations/{organization_id}/folders",
        json={"name": "P9 reports"},
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
            "qa_type": "Machine QA",
            "qa_cycle": "CUSTOM",
            "performed_at": "2026-09-08T00:00:00Z",
            "title": "P9 source case",
        },
    )
    assert case.status_code == 201, case.text
    return str(case.json()["id"])


def _blocks(label: str = "Summary") -> list[dict[str, object]]:
    return [
        {
            "stable_block_id": "summary",
            "block_type": "TEXT",
            "label": label,
            "config": {"content": "A user-defined report section."},
            "source_binding": {},
        },
        {
            "stable_block_id": "warning",
            "block_type": "WARNING",
            "label": "Warnings",
            "is_visible": False,
            "config": {"show_empty": False},
            "source_binding": {"path": "source_snapshot.payload.error_snapshot"},
        },
    ]


def test_report_revision_snapshots_source_and_supports_full_block_customization() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[report_storage] = lambda: storage
        case_id = _qa_case(client, str(organization.id))
        created = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "QA_CASE",
                "source_id": case_id,
                "title": "Source report",
                "blocks": _blocks(),
                "render_options": {"orientation": "landscape"},
            },
        )
        assert created.status_code == 201, created.text
        revision = created.json()
        report_key = revision["report_key"]
        assert revision["revision_number"] == 1
        assert revision["blocks"][1]["is_visible"] is False
        assert revision["source_snapshot"]["payload"]["title"] == "P9 source case"

        changed = client.patch(
            f"/api/v1/qa-cases/{case_id}",
            json={"title": "Changed after report"},
        )
        assert changed.status_code == 200, changed.text
        old_revision = client.get(f"/api/v1/reports/{report_key}/revisions/{revision['id']}")
        assert old_revision.status_code == 200, old_revision.text
        assert old_revision.json()["source_snapshot"]["payload"]["title"] == "P9 source case"

        updated = client.post(
            f"/api/v1/reports/{report_key}/revisions",
            json={
                "expected_revision": 1,
                "title": "Source report v2",
                "blocks": _blocks("Renamed section"),
            },
        )
        assert updated.status_code == 201, updated.text
        assert updated.json()["revision_number"] == 2
        assert updated.json()["supersedes_revision_id"] == revision["id"]
        assert updated.json()["source_snapshot"]["payload"]["title"] == "Changed after report"


def test_report_templates_versioning_and_revision_conflict_are_scoped() -> None:
    with _workspace_client() as (client, organization):
        template = client.post(
            f"/api/v1/organizations/{organization.id}/report-templates",
            json={
                "template_key": "site-template",
                "name": "Site template",
                "blocks": _blocks(),
            },
        )
        assert template.status_code == 201, template.text
        version = client.post(
            f"/api/v1/report-templates/{template.json()['id']}/versions",
            json={"name": "Site template v2", "blocks": _blocks("V2")},
        )
        assert version.status_code == 201, version.text
        assert version.json()["version_number"] == 2
        templates = client.get(f"/api/v1/organizations/{organization.id}/report-templates")
        assert templates.status_code == 200
        assert templates.json()["total"] == 2

        report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "CUSTOM",
                "title": "Conflict report",
                "template_version_id": version.json()["id"],
            },
        )
        assert report.status_code == 201, report.text
        conflict = client.post(
            f"/api/v1/reports/{report.json()['report_key']}/revisions",
            json={"expected_revision": 99, "blocks": _blocks("stale")},
        )
        assert conflict.status_code == 409, conflict.text
        assert conflict.json()["code"] == "REPORT_REVISION_CONFLICT"
        revisions = client.get(f"/api/v1/reports/{report.json()['report_key']}/revisions")
        assert len(revisions.json()) == 1

        outside = client.get(f"/api/v1/organizations/{uuid4()}/reports")
        assert outside.status_code == 403
        assert outside.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"


def test_report_rejects_executable_content_and_missing_scoped_source() -> None:
    with _workspace_client() as (client, organization):
        missing = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "QA_CASE",
                "source_id": str(uuid4()),
                "title": "Missing source",
            },
        )
        assert missing.status_code == 404, missing.text
        assert missing.json()["code"] == "REPORT_SOURCE_UNAVAILABLE"

        dangerous = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "CUSTOM",
                "title": "Unsafe report",
                "blocks": [
                    {
                        "stable_block_id": "unsafe",
                        "block_type": "TEXT",
                        "label": "Unsafe",
                        "config": {"content": "<script>alert(1)</script>"},
                    }
                ],
            },
        )
        assert dangerous.status_code == 422, dangerous.text
        assert dangerous.json()["code"] == "REPORT_CONTENT_INVALID"


def test_report_exports_are_deterministic_idempotent_and_downloadable() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[report_storage] = lambda: storage
        report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "BIOLOGICAL",
                "title": "Independent calculation report",
                "blocks": _blocks(),
            },
        )
        assert report.status_code == 201, report.text
        revision = report.json()
        report_key = revision["report_key"]
        revision_id = revision["id"]

        for export_format, prefix in (
            ("JSON", b"{"),
            ("CSV", b"section,key,value"),
            ("PDF", b"%PDF-1.4"),
            ("PNG", b"\x89PNG\r\n\x1a\n"),
        ):
            exported = client.post(
                f"/api/v1/reports/{report_key}/revisions/{revision_id}/exports",
                json={
                    "export_format": export_format,
                    "idempotency_key": f"p9-{export_format.lower()}-001",
                },
            )
            assert exported.status_code == 201, exported.text
            job = exported.json()
            assert job["status"] == "COMPLETED"
            assert job["sha256"]
            assert job["byte_size"] > 0
            if export_format != "PDF":
                assert job["warning_snapshot"] == []
            assert storage.objects[job["object_key"]].startswith(prefix)

            repeated = client.post(
                f"/api/v1/reports/{report_key}/revisions/{revision_id}/exports",
                json={
                    "export_format": export_format,
                    "idempotency_key": f"p9-{export_format.lower()}-001",
                },
            )
            assert repeated.status_code == 200, repeated.text
            assert repeated.json()["id"] == job["id"]

            download = client.get(f"/api/v1/report-exports/{job['id']}/download")
            assert download.status_code == 200, download.text
            assert download.json()["sha256"] == job["sha256"]

        conflict = client.post(
            f"/api/v1/reports/{report_key}/revisions/{revision_id}/exports",
            json={"export_format": "JSON", "idempotency_key": "p9-json-001"},
        )
        assert conflict.status_code == 200
        different_payload = client.post(
            f"/api/v1/reports/{report_key}/revisions/{revision_id}/exports",
            json={"export_format": "CSV", "idempotency_key": "p9-json-001"},
        )
        assert different_payload.status_code == 409, different_payload.text
        assert different_payload.json()["code"] == "EXPORT_IDEMPOTENCY_CONFLICT"


def test_report_export_metadata_failure_compensates_rendered_object(
    monkeypatch,
) -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[report_storage] = lambda: storage
        report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={"source_type": "BIOLOGICAL", "title": "Retryable export"},
        )
        assert report.status_code == 201, report.text
        report_key = report.json()["report_key"]
        revision_id = report.json()["id"]
        original_commit = Session.commit
        commit_count = 0

        def fail_once(session: Session) -> None:
            nonlocal commit_count
            commit_count += 1
            if commit_count == 2:
                raise RuntimeError("synthetic final metadata commit failure")
            original_commit(session)

        monkeypatch.setattr(Session, "commit", fail_once)
        failed = client.post(
            f"/api/v1/reports/{report_key}/revisions/{revision_id}/exports",
            json={"export_format": "JSON", "idempotency_key": "p9-compensate-001"},
        )
        assert failed.status_code == 503, failed.text
        assert failed.json()["code"] == "REPORT_EXPORT_PERSISTENCE_FAILED"
        assert storage.objects == {}

        retried = client.post(
            f"/api/v1/reports/{report_key}/revisions/{revision_id}/exports",
            json={"export_format": "JSON", "idempotency_key": "p9-compensate-001"},
        )
        assert retried.status_code == 200, retried.text
        assert retried.json()["status"] == "COMPLETED"
        assert len(storage.objects) == 1


def test_report_export_cleanup_failure_returns_reconciliation_signal(monkeypatch) -> None:
    storage = _CleanupFailingStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[report_storage] = lambda: storage
        report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={"source_type": "BIOLOGICAL", "title": "Reconciliation export"},
        )
        assert report.status_code == 201, report.text
        original_commit = Session.commit
        commit_count = 0

        def fail_final_commit(session: Session) -> None:
            nonlocal commit_count
            commit_count += 1
            if commit_count == 2:
                raise RuntimeError("synthetic final metadata commit failure")
            original_commit(session)

        monkeypatch.setattr(Session, "commit", fail_final_commit)
        failed = client.post(
            f"/api/v1/reports/{report.json()['report_key']}/revisions/"
            f"{report.json()['id']}/exports",
            json={"export_format": "JSON", "idempotency_key": "p9-reconcile-001"},
        )
        assert failed.status_code == 503, failed.text
        assert failed.json()["code"] == "REPORT_EXPORT_PERSISTENCE_FAILED"
        assert len(storage.objects) == 1
