import hashlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from rt_connect_api.db.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMembership,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
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


def test_member_invitation_is_email_bound_one_time_and_idempotent() -> None:
    with _workspace_client() as (client, organization):
        created = client.post(
            f"/api/v1/organizations/{organization.id}/invitations",
            json={"email": "Invitee@example.com", "expires_in_days": 7},
        )
        assert created.status_code == 201, created.text
        invitation = created.json()
        assert invitation["invited_email"] == "invitee@example.com"
        assert invitation["status"] == "PENDING"
        token = invitation["token"]
        assert len(token) >= 20

        listed = client.get(f"/api/v1/organizations/{organization.id}/invitations")
        assert listed.status_code == 200
        assert listed.json()["items"][0]["invited_email"] == "invitee@example.com"
        assert "token" not in listed.json()["items"][0]

        dependency = client.app.dependency_overrides[get_session]
        session_generator = dependency()
        session = next(session_generator)
        try:
            stored = session.get(OrganizationInvitation, UUID(invitation["id"]))
            assert stored is not None
            assert stored.token_hash != token
            assert len(stored.token_hash) == 64
        finally:
            session_generator.close()

        client.app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
            subject="synthetic-invitee-subject",
            email="invitee@example.com",
            claims={"sub": "synthetic-invitee-subject"},
        )
        accepted = client.post(
            "/api/v1/organizations/invitations/accept",
            json={"token": token},
        )
        assert accepted.status_code == 200, accepted.text
        member_id = accepted.json()["id"]
        assert accepted.json()["email"] == "invitee@example.com"

        repeated = client.post(
            "/api/v1/organizations/invitations/accept",
            json={"token": token},
        )
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["id"] == member_id

        members = client.get(
            f"/api/v1/organizations/{organization.id}/members",
            params={"include_inactive": True},
        )
        assert members.status_code == 200
        assert members.json()["total"] == 2


def test_invitation_rejects_wrong_identity_and_duplicate_pending() -> None:
    with _workspace_client() as (client, organization):
        payload = {"email": "invitee@example.com"}
        created = client.post(
            f"/api/v1/organizations/{organization.id}/invitations", json=payload
        )
        assert created.status_code == 201
        duplicate = client.post(
            f"/api/v1/organizations/{organization.id}/invitations", json=payload
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "INVITATION_ALREADY_PENDING"

        client.app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
            subject="synthetic-wrong-subject",
            email="wrong@example.com",
            claims={"sub": "synthetic-wrong-subject"},
        )
        rejected = client.post(
            "/api/v1/organizations/invitations/accept",
            json={"token": created.json()["token"]},
        )
        assert rejected.status_code == 403
        assert rejected.json()["code"] == "INVITATION_INVALID"


def test_membership_lifecycle_keeps_last_active_member() -> None:
    with _workspace_client() as (client, organization):
        members = client.get(f"/api/v1/organizations/{organization.id}/members").json()["items"]
        assert len(members) == 1
        last = client.patch(
            f"/api/v1/organizations/{organization.id}/members/{members[0]['id']}",
            json={"is_active": False},
        )
        assert last.status_code == 409
        assert last.json()["code"] == "LAST_MEMBERSHIP_CONFLICT"


def test_invitation_does_not_create_a_second_active_organization_context() -> None:
    with _workspace_client() as (client, organization):
        dependency = client.app.dependency_overrides[get_session]
        session_generator = dependency()
        session = next(session_generator)
        token = "cross-context-invitation-token-123456789"
        try:
            identity = session.scalar(
                select(UserIdentity).where(
                    UserIdentity.supabase_user_id == "synthetic-supabase-subject"
                )
            )
            assert identity is not None
            second = Organization(name="Second Synthetic Oncology Center")
            session.add(second)
            session.flush()
            session.add(
                OrganizationInvitation(
                    organization_id=second.id,
                    invited_email="synthetic.user@example.invalid",
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
            )
            session.commit()
        finally:
            session_generator.close()

        response = client.post(
            "/api/v1/organizations/invitations/accept",
            json={"token": token},
        )

        assert response.status_code == 409
        assert response.json()["code"] == "ORGANIZATION_CONTEXT_ALREADY_ASSIGNED"

        session_generator = dependency()
        session = next(session_generator)
        try:
            memberships = session.scalars(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_identity_id == identity.id
                )
            ).all()
            assert len(memberships) == 1
            assert memberships[0].organization_id == organization.id
        finally:
            session_generator.close()
