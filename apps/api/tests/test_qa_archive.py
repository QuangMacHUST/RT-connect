from datetime import datetime
from uuid import uuid4

from rt_connect_api.api.artifacts import _storage as artifact_storage
from rt_connect_api.api.gamma import _storage as gamma_storage
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from test_gamma import _measurement_bytes
from test_workspace import _workspace_client


def test_nested_folder_and_qa_case_lifecycle_preserves_case_identity() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]

        root = client.post(
            f"/api/v1/organizations/{organization.id}/folders",
            json={"name": "2026"},
        )
        assert root.status_code == 201
        root_id = root.json()["id"]
        assert root.json()["path"] == "2026"

        child = client.post(
            f"/api/v1/organizations/{organization.id}/folders",
            json={"name": "Daily QA", "parent_folder_id": root_id},
        )
        assert child.status_code == 201
        child_id = child.json()["id"]
        assert child.json()["path"] == "2026/Daily QA"
        assert child.json()["depth"] == 1

        qa_case = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": child_id,
                "qa_type": "Machine Output",
                "qa_cycle": "DAILY",
                "performed_at": "2026-09-06T08:00:00Z",
                "title": "Daily output check",
            },
        )
        assert qa_case.status_code == 201
        case_id = qa_case.json()["id"]

        research = client.post(
            f"/api/v1/organizations/{organization.id}/folders",
            json={"name": "Research"},
        )
        research_id = research.json()["id"]
        moved = client.patch(
            f"/api/v1/folders/{child_id}",
            json={"parent_folder_id": research_id},
        )
        assert moved.status_code == 200
        assert moved.json()["path"] == "Research/Daily QA"

        renamed = client.patch(
            f"/api/v1/folders/{research_id}",
            json={"name": "Research Archive"},
        )
        assert renamed.status_code == 200
        assert renamed.json()["path"] == "Research Archive"

        fetched_case = client.get(f"/api/v1/qa-cases/{case_id}")
        assert fetched_case.status_code == 200
        assert fetched_case.json()["id"] == case_id
        assert fetched_case.json()["primary_folder_id"] == child_id

        archived = client.patch(
            f"/api/v1/folders/{research_id}",
            json={"is_archived": True},
        )
        assert archived.status_code == 200

        active_tree = client.get(f"/api/v1/organizations/{organization.id}/folders/tree")
        history_tree = client.get(
            f"/api/v1/organizations/{organization.id}/folders/tree",
            params={"include_archived": True},
        )
        assert active_tree.json()["total"] == 1
        assert history_tree.json()["total"] == 3

        cases = client.get(f"/api/v1/organizations/{organization.id}/qa-cases")
        filtered = client.get(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            params={"qa_cycle": "DAILY", "q": "output"},
        )

    assert cases.status_code == 200
    assert cases.json()["total"] == 1
    assert filtered.json()["total"] == 1


def test_folder_cycle_duplicate_and_cross_organization_scope_are_rejected() -> None:
    with _workspace_client() as (client, organization):
        root = client.post(
            f"/api/v1/organizations/{organization.id}/folders", json={"name": "Root"}
        ).json()
        child = client.post(
            f"/api/v1/organizations/{organization.id}/folders",
            json={"name": "Child", "parent_folder_id": root["id"]},
        ).json()
        duplicate = client.post(
            f"/api/v1/organizations/{organization.id}/folders", json={"name": "Root"}
        )
        cycle = client.patch(
            f"/api/v1/folders/{root['id']}", json={"parent_folder_id": child["id"]}
        )
        cross_org = client.get(f"/api/v1/organizations/{uuid4()}/qa-cases")

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "FOLDER_NAME_CONFLICT"
    assert cycle.status_code == 409
    assert cycle.json()["code"] == "FOLDER_CYCLE"
    assert cross_org.status_code == 403
    assert cross_org.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"


def test_qa_case_references_must_match_the_same_site_and_active_folder() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders", json={"name": "QA"}
        ).json()
        invalid_machine = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": str(uuid4()),
                "primary_folder_id": folder["id"],
                "qa_type": "Machine Output",
                "qa_cycle": "DAILY",
                "performed_at": datetime(2026, 9, 6, 8, 0).isoformat(),
                "title": "Invalid machine reference",
            },
        )
        archived_folder = client.patch(
            f"/api/v1/folders/{folder['id']}", json={"is_archived": True}
        )
        invalid_folder = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder["id"],
                "qa_type": "Machine Output",
                "qa_cycle": "DAILY",
                "performed_at": "2026-09-06T08:00:00Z",
                "title": "Archived folder reference",
            },
        )

    assert invalid_machine.status_code == 404
    assert invalid_machine.json()["code"] == "MACHINE_NOT_FOUND"
    assert archived_folder.status_code == 200
    assert invalid_folder.status_code == 409
    assert invalid_folder.json()["code"] == "FOLDER_ARCHIVED"


def test_qa_catalog_is_complete_and_case_can_start_from_a_definition() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders", json={"name": "QA catalog"}
        ).json()

        catalogue = client.get(
            f"/api/v1/organizations/{organization.id}/qa-test-definitions"
        )
        started = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder["id"],
                "qa_definition_key": "STARSHOT",
                "qa_cycle": "MONTHLY",
                "performed_at": "2026-09-13T08:00:00Z",
                "title": "Kiểm tra sao tháng 9",
            },
        )

    assert catalogue.status_code == 200
    definitions = catalogue.json()["items"]
    keys = {item["key"] for item in definitions}
    assert len(definitions) >= 55
    assert len(keys) == len(definitions)
    assert {"STARSHOT", "PICKET_FENCE", "WINSTON_LUTZ", "PSQA_GAMMA_2D"} <= keys
    assert catalogue.json()["total"] == len(definitions)
    assert started.status_code == 201
    assert started.json()["qa_definition_key"] == "STARSHOT"
    assert started.json()["qa_type"] == "Kiểm tra sao"


def test_qa_case_archive_restore_and_purge_are_idempotent_and_recoverable() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders", json={"name": "QA history"}
        ).json()
        created = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder["id"],
                "qa_definition_key": "MANUAL_MACHINE_QA",
                "qa_cycle": "DAILY",
                "performed_at": "2026-09-13T08:00:00Z",
                "title": "Số đo đầu ngày",
            },
        )
        case_id = created.json()["id"]

        archived = client.delete(f"/api/v1/qa-cases/{case_id}")
        repeated_archive = client.delete(f"/api/v1/qa-cases/{case_id}")
        hidden = client.get(f"/api/v1/organizations/{organization.id}/qa-cases")
        trash = client.get(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            params={"include_archived": True},
        )
        trash_only = client.get(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            params={"include_archived": True, "archived_only": True},
        )
        restored = client.post(f"/api/v1/qa-cases/{case_id}/restore")
        repeated_restore = client.post(f"/api/v1/qa-cases/{case_id}/restore")
        archived_again = client.delete(f"/api/v1/qa-cases/{case_id}")
        purged = client.post(f"/api/v1/qa-cases/{case_id}/purge")
        repeated_purge = client.post(f"/api/v1/qa-cases/{case_id}/purge")
        after_purge = client.get(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            params={"include_archived": True},
        )

    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert repeated_archive.status_code == 200
    assert hidden.json()["total"] == 0
    assert trash.json()["total"] == 1
    assert trash_only.json()["total"] == 1
    assert all(item["is_archived"] for item in trash_only.json()["items"])
    assert restored.status_code == 200
    assert restored.json()["is_archived"] is False
    assert repeated_restore.status_code == 200
    assert archived_again.status_code == 200
    assert purged.status_code == 200
    assert purged.json()["status"] == "PURGED"
    assert repeated_purge.status_code == 200
    assert repeated_purge.json()["status"] == "PURGED"
    assert after_purge.json()["total"] == 0


def test_qa_case_creation_retries_are_idempotent_and_key_reuse_is_rejected() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders", json={"name": "Retry safe"}
        ).json()
        payload = {
            "site_id": site["id"],
            "machine_id": machine["id"],
            "primary_folder_id": folder["id"],
            "qa_definition_key": "MANUAL_MACHINE_QA",
            "qa_cycle": "DAILY",
            "performed_at": "2026-09-13T08:00:00Z",
            "title": "Bản ghi không trùng",
            "idempotency_key": "qa-create-retry-001",
        }
        first = client.post(f"/api/v1/organizations/{organization.id}/qa-cases", json=payload)
        repeated = client.post(f"/api/v1/organizations/{organization.id}/qa-cases", json=payload)
        changed = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={**payload, "title": "Dữ liệu khác"},
        )
        cases = client.get(f"/api/v1/organizations/{organization.id}/qa-cases")

    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    assert changed.status_code == 409
    assert changed.json()["code"] == "QA_CASE_IDEMPOTENCY_CONFLICT"
    assert cases.json()["total"] == 1


def test_qa_case_purge_requires_archive_and_rejects_referenced_history() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders",
            json={"name": "P5 purge guards"},
        ).json()
        created = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder["id"],
                "qa_definition_key": "MANUAL_MACHINE_QA",
                "qa_cycle": "DAILY",
                "performed_at": "2026-09-14T08:00:00Z",
                "title": "Hồ sơ còn lượt QA tham chiếu",
            },
        )
        case_id = created.json()["id"]
        active_purge = client.post(f"/api/v1/qa-cases/{case_id}/purge")

        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        )
        assert protocol.status_code == 201, protocol.text
        run = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={"protocol_version_id": protocol.json()["id"]},
        )
        assert run.status_code == 201, run.text
        archived = client.delete(f"/api/v1/qa-cases/{case_id}")
        referenced_purge = client.post(f"/api/v1/qa-cases/{case_id}/purge")
        still_present = client.get(f"/api/v1/qa-cases/{case_id}")

    assert active_purge.status_code == 409
    assert active_purge.json()["code"] == "QA_CASE_PURGE_REQUIRES_ARCHIVE"
    assert archived.status_code == 200
    assert referenced_purge.status_code == 409
    assert referenced_purge.json()["code"] == "QA_CASE_REFERENCED"
    assert referenced_purge.json()["details"][0]["source"] == "machine_qa_runs"
    assert referenced_purge.json()["details"][0]["count"] == 1
    assert still_present.status_code == 200
    assert still_present.json()["is_archived"] is True


def test_qa_case_purge_rejects_a_report_source_reference() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders",
            json={"name": "P5 report purge guard"},
        ).json()
        case = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder["id"],
                "qa_definition_key": "MANUAL_MACHINE_QA",
                "qa_cycle": "DAILY",
                "performed_at": "2026-09-14T08:00:00Z",
                "title": "Hồ sơ có báo cáo tham chiếu",
            },
        )
        assert case.status_code == 201, case.text
        case_id = case.json()["id"]

        report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "QA_CASE",
                "source_id": case_id,
                "title": "Báo cáo tham chiếu hồ sơ QA",
            },
        )
        assert report.status_code == 201, report.text
        archived = client.delete(f"/api/v1/qa-cases/{case_id}")
        preview = client.get(f"/api/v1/qa-cases/{case_id}/purge-preview")
        rejected = client.post(f"/api/v1/qa-cases/{case_id}/purge")
        still_present = client.get(f"/api/v1/qa-cases/{case_id}")

    assert archived.status_code == 200
    assert preview.status_code == 200
    assert preview.json()["title"] == "Hồ sơ có báo cáo tham chiếu"
    assert preview.json()["is_archived"] is True
    assert preview.json()["can_purge"] is False
    assert preview.json()["references"] == [{"source": "reports", "count": 1}]
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "QA_CASE_REFERENCED"
    references = {item["source"]: item["count"] for item in rejected.json()["details"]}
    assert references == {"reports": 1}
    assert still_present.status_code == 200
    assert still_present.json()["is_archived"] is True


def test_qa_case_purge_rejects_case_with_queued_gamma_job() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[gamma_storage] = lambda: storage
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        machine = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines"
        ).json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders",
            json={"name": "P5 worker guard"},
        ).json()
        case = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder["id"],
                "qa_definition_key": "PSQA_GAMMA_2D",
                "qa_cycle": "CUSTOM",
                "performed_at": "2026-09-14T08:00:00Z",
                "title": "Hồ sơ có tác vụ Gamma đang chờ",
            },
        )
        assert case.status_code == 201, case.text
        case_id = case.json()["id"]

        artifact_ids = []
        for logical_role, dataset_id in (("REFERENCE", "reference"), ("EVALUATION", "evaluation")):
            uploaded = client.post(
                f"/api/v1/qa-cases/{case_id}/artifacts",
                files={
                    "file": (
                        f"{dataset_id}.json",
                        _measurement_bytes(dataset_id, [1, 2, 3, 4]),
                        "application/json",
                    )
                },
                data={"artifact_type": "MEASUREMENT", "logical_role": logical_role},
            )
            assert uploaded.status_code == 201, uploaded.text
            artifact_ids.append(uploaded.json()["id"])
        for artifact_id in artifact_ids:
            validation = client.post(f"/api/v1/artifacts/{artifact_id}/validate")
            assert validation.status_code == 200, validation.text

        queued = client.post(
            f"/api/v1/qa-cases/{case_id}/gamma-runs",
            json={
                "reference_artifact_id": artifact_ids[0],
                "evaluation_artifact_id": artifact_ids[1],
                "idempotency_key": "p5-queued-worker-guard-001",
                "workflow_profile": "ENGINE_TEST",
                "configuration": {"dose_threshold_percent": 0},
            },
        )
        assert queued.status_code == 201, queued.text
        assert queued.json()["status"] == "QUEUED"
        archived = client.delete(f"/api/v1/qa-cases/{case_id}")
        rejected = client.post(f"/api/v1/qa-cases/{case_id}/purge")
        still_present = client.get(f"/api/v1/qa-cases/{case_id}")

    assert archived.status_code == 200
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "QA_CASE_REFERENCED"
    references = {item["source"]: item["count"] for item in rejected.json()["details"]}
    assert references["gamma_analysis_runs"] == 1
    assert still_present.status_code == 200
    assert still_present.json()["is_archived"] is True
