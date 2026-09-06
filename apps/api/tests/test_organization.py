from uuid import uuid4

from test_workspace import _workspace_client


def test_site_and_machine_lifecycle_is_scoped_and_archivable() -> None:
    with _workspace_client() as (client, organization):
        sites = client.get(f"/api/v1/organizations/{organization.id}/sites")
        assert sites.status_code == 200
        assert sites.json()["total"] == 1

        created_site = client.post(
            f"/api/v1/organizations/{organization.id}/sites",
            json={"name": "Synthetic Satellite Campus"},
        )
        assert created_site.status_code == 201
        site_id = created_site.json()["id"]

        created_machine = client.post(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines",
            json={
                "stable_machine_id": "SYN-LINAC-02",
                "display_name": "Synthetic Linac 02",
                "manufacturer": "Synthetic Medical",
                "model": "RT-2000",
            },
        )
        assert created_machine.status_code == 201
        machine = created_machine.json()
        assert machine["status"] == "ACTIVE"
        assert machine["is_archived"] is False

        updated_machine = client.patch(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines/{machine['id']}",
            json={"status": "MAINTENANCE", "display_name": "Synthetic Linac 02A"},
        )
        assert updated_machine.status_code == 200
        assert updated_machine.json()["id"] == machine["id"]
        assert updated_machine.json()["stable_machine_id"] == "SYN-LINAC-02"
        assert updated_machine.json()["status"] == "MAINTENANCE"

        archived_machine = client.patch(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines/{machine['id']}",
            json={"is_archived": True},
        )
        assert archived_machine.status_code == 200
        assert archived_machine.json()["is_archived"] is True

        active_machines = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines"
        )
        archived_machines = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines",
            params={"include_archived": True},
        )
        assert active_machines.json()["total"] == 0
        assert archived_machines.json()["total"] == 1


def test_organization_routes_reject_scope_mismatch_before_resource_lookup() -> None:
    with _workspace_client() as (client, organization):
        response = client.get(f"/api/v1/organizations/{uuid4()}/sites")

    assert response.status_code == 403
    assert response.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"


def test_create_organization_assigns_first_membership_when_identity_has_none() -> None:
    with _workspace_client(with_membership=False) as (client, _):
        response = client.post(
            "/api/v1/organizations",
            json={"name": "New Synthetic Oncology Center"},
        )

        assert response.status_code == 201
        organization = response.json()
        assert organization["name"] == "New Synthetic Oncology Center"
        assert organization["is_archived"] is False

        fetched = client.get(f"/api/v1/organizations/{organization['id']}")

    assert fetched.status_code == 200
    assert fetched.json() == organization


def test_create_organization_does_not_create_ambiguous_second_context() -> None:
    with _workspace_client() as (client, _):
        response = client.post(
            "/api/v1/organizations",
            json={"name": "Ambiguous Synthetic Center"},
        )

    assert response.status_code == 409
    assert response.json()["code"] == "ORGANIZATION_CONTEXT_ALREADY_ASSIGNED"


def test_machine_stable_identifier_conflict_is_explicit() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        response = client.post(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines",
            json={
                "stable_machine_id": "SYN-LINAC-01",
                "display_name": "Duplicate Synthetic Linac",
            },
        )

    assert response.status_code == 409
    assert response.json()["code"] == "MACHINE_ID_CONFLICT"
