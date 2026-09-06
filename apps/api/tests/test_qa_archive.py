from datetime import datetime
from uuid import uuid4

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
