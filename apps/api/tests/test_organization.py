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
        assert machine["revision"] == 1

        updated_machine = client.patch(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines/{machine['id']}",
            json={
                "expected_revision": machine["revision"],
                "status": "MAINTENANCE",
                "display_name": "Synthetic Linac 02A",
            },
        )
        assert updated_machine.status_code == 200
        assert updated_machine.json()["id"] == machine["id"]
        assert updated_machine.json()["stable_machine_id"] == "SYN-LINAC-02"
        assert updated_machine.json()["status"] == "MAINTENANCE"
        assert updated_machine.json()["revision"] == 2

        archived_machine = client.patch(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines/{machine['id']}",
            json={"expected_revision": updated_machine.json()["revision"], "is_archived": True},
        )
        assert archived_machine.status_code == 200
        assert archived_machine.json()["is_archived"] is True
        assert archived_machine.json()["revision"] == 3

        active_machines = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines"
        )
        archived_machines = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines",
            params={"include_archived": True},
        )
        assert active_machines.json()["total"] == 0
        assert archived_machines.json()["total"] == 1


def test_organization_site_and_machine_updates_reject_stale_revisions() -> None:
    with _workspace_client() as (client, organization):
        organization_url = f"/api/v1/organizations/{organization.id}"
        current_organization = client.get(organization_url)
        assert current_organization.status_code == 200
        organization_revision = current_organization.json()["revision"]

        renamed_organization = client.patch(
            organization_url,
            json={
                "expected_revision": organization_revision,
                "name": "Synthetic Oncology Center Revised",
            },
        )
        assert renamed_organization.status_code == 200, renamed_organization.text
        assert renamed_organization.json()["revision"] == organization_revision + 1

        stale_organization = client.patch(
            organization_url,
            json={"expected_revision": organization_revision, "name": "Stale Organization Edit"},
        )
        assert stale_organization.status_code == 409
        assert stale_organization.json()["code"] == "REVISION_CONFLICT"

        site = client.get(f"{organization_url}/sites").json()["items"][0]
        site_url = f"{organization_url}/sites/{site['id']}"
        renamed_site = client.patch(
            site_url,
            json={"expected_revision": site["revision"], "name": "Synthetic Main Site Revised"},
        )
        assert renamed_site.status_code == 200, renamed_site.text
        assert renamed_site.json()["revision"] == site["revision"] + 1

        stale_site = client.patch(
            site_url,
            json={"expected_revision": site["revision"], "name": "Stale Site Edit"},
        )
        assert stale_site.status_code == 409
        assert stale_site.json()["code"] == "REVISION_CONFLICT"

        machine = client.get(f"{site_url}/machines").json()["items"][0]
        machine_url = f"{site_url}/machines/{machine['id']}"
        renamed_machine = client.patch(
            machine_url,
            json={
                "expected_revision": machine["revision"],
                "display_name": "Synthetic Linac Revised",
            },
        )
        assert renamed_machine.status_code == 200, renamed_machine.text
        assert renamed_machine.json()["revision"] == machine["revision"] + 1

        stale_machine = client.patch(
            machine_url,
            json={"expected_revision": machine["revision"], "display_name": "Stale Machine Edit"},
        )
        assert stale_machine.status_code == 409
        assert stale_machine.json()["code"] == "REVISION_CONFLICT"

        current_machine = client.get(f"{site_url}/machines").json()["items"][0]
        assert current_machine["display_name"] == "Synthetic Linac Revised"
        assert current_machine["revision"] == machine["revision"] + 1


def test_archived_organization_can_only_be_restored_by_an_active_member() -> None:
    with _workspace_client() as (client, organization):
        organization_url = f"/api/v1/organizations/{organization.id}"
        site = client.get(f"{organization_url}/sites").json()["items"][0]
        current = client.get(organization_url)
        archived = client.patch(
            organization_url,
            json={"expected_revision": current.json()["revision"], "is_archived": True},
        )
        assert archived.status_code == 200, archived.text
        assert archived.json()["is_archived"] is True

        fetched_archived = client.get(organization_url)
        assert fetched_archived.status_code == 200
        assert fetched_archived.json()["is_archived"] is True

        blocked_site = client.post(
            f"{organization_url}/sites", json={"name": "Blocked Archived Site"}
        )
        assert blocked_site.status_code == 409
        assert blocked_site.json()["code"] == "PARENT_NOT_AVAILABLE"

        blocked_machine = client.post(
            f"{organization_url}/sites/{site['id']}/machines",
            json={
                "stable_machine_id": "SYN-ARCHIVED-01",
                "display_name": "Blocked Archived Machine",
            },
        )
        assert blocked_machine.status_code == 409
        assert blocked_machine.json()["code"] == "PARENT_NOT_AVAILABLE"

        blocked_invitation = client.post(
            f"{organization_url}/invitations",
            json={"email": "blocked@example.invalid"},
        )
        assert blocked_invitation.status_code == 409
        assert blocked_invitation.json()["code"] == "PARENT_NOT_AVAILABLE"

        restored = client.patch(
            organization_url,
            json={"expected_revision": archived.json()["revision"], "is_archived": False},
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["is_archived"] is False

        created_site = client.post(
            f"{organization_url}/sites", json={"name": "Restored Organization Site"}
        )
        assert created_site.status_code == 201, created_site.text


def test_archived_site_blocks_machine_mutation_and_restore_is_explicit() -> None:
    with _workspace_client() as (client, organization):
        organization_url = f"/api/v1/organizations/{organization.id}"
        site = client.get(f"{organization_url}/sites").json()["items"][0]
        machine = client.get(f"{organization_url}/sites/{site['id']}/machines").json()["items"][0]
        site_url = f"{organization_url}/sites/{site['id']}"
        machine_url = f"{site_url}/machines/{machine['id']}"

        archived_site = client.patch(
            site_url,
            json={"expected_revision": site["revision"], "is_archived": True},
        )
        assert archived_site.status_code == 200, archived_site.text

        blocked_create = client.post(
            f"{site_url}/machines",
            json={
                "stable_machine_id": "SYN-ARCHIVED-SITE-01",
                "display_name": "Blocked Archived Site Machine",
            },
        )
        assert blocked_create.status_code == 409
        assert blocked_create.json()["code"] == "PARENT_NOT_AVAILABLE"

        blocked_update = client.patch(
            machine_url,
            json={"expected_revision": machine["revision"], "display_name": "Must Stay"},
        )
        assert blocked_update.status_code == 409
        assert blocked_update.json()["code"] == "PARENT_NOT_AVAILABLE"

        restored_site = client.patch(
            site_url,
            json={"expected_revision": archived_site.json()["revision"], "is_archived": False},
        )
        assert restored_site.status_code == 200, restored_site.text

        archived_machine = client.patch(
            machine_url,
            json={"expected_revision": machine["revision"], "is_archived": True},
        )
        assert archived_machine.status_code == 200, archived_machine.text
        blocked_archived_edit = client.patch(
            machine_url,
            json={
                "expected_revision": archived_machine.json()["revision"],
                "display_name": "Must Restore First",
            },
        )
        assert blocked_archived_edit.status_code == 409
        assert blocked_archived_edit.json()["code"] == "RESOURCE_ARCHIVED"

        restored_machine = client.patch(
            machine_url,
            json={
                "expected_revision": archived_machine.json()["revision"],
                "is_archived": False,
            },
        )
        assert restored_machine.status_code == 200, restored_machine.text
        assert restored_machine.json()["is_archived"] is False


def test_archived_machine_keeps_qa_history_but_blocks_new_cases() -> None:
    with _workspace_client() as (client, organization):
        organization_url = f"/api/v1/organizations/{organization.id}"
        site = client.get(f"{organization_url}/sites").json()["items"][0]
        machine = client.get(f"{organization_url}/sites/{site['id']}/machines").json()["items"][0]
        folder = client.post(
            f"/api/v1/organizations/{organization.id}/folders", json={"name": "QA history"}
        )
        assert folder.status_code == 201
        case = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder.json()["id"],
                "qa_type": "Machine Output",
                "qa_cycle": "DAILY",
                "performed_at": "2026-09-13T08:00:00Z",
                "title": "Lịch sử trước khi lưu trữ máy",
            },
        )
        assert case.status_code == 201, case.text

        archived = client.patch(
            f"{organization_url}/sites/{site['id']}/machines/{machine['id']}",
            json={"expected_revision": machine["revision"], "is_archived": True},
        )
        assert archived.status_code == 200, archived.text

        active_machines = client.get(
            f"{organization_url}/sites/{site['id']}/machines"
        )
        qa_history = client.get(f"/api/v1/organizations/{organization.id}/qa-cases")
        old_case = client.get(f"/api/v1/qa-cases/{case.json()['id']}")
        blocked_new_case = client.post(
            f"/api/v1/organizations/{organization.id}/qa-cases",
            json={
                "site_id": site["id"],
                "machine_id": machine["id"],
                "primary_folder_id": folder.json()["id"],
                "qa_type": "Machine Output",
                "qa_cycle": "DAILY",
                "performed_at": "2026-09-13T09:00:00Z",
                "title": "Không được tạo sau khi lưu trữ máy",
            },
        )

    assert active_machines.status_code == 200
    assert active_machines.json()["total"] == 0
    assert qa_history.status_code == 200
    assert qa_history.json()["total"] == 1
    assert qa_history.json()["items"][0]["id"] == case.json()["id"]
    assert old_case.status_code == 200
    assert old_case.json()["machine_id"] == machine["id"]
    assert blocked_new_case.status_code == 404
    assert blocked_new_case.json()["code"] == "MACHINE_NOT_FOUND"


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


def test_machine_stable_identifier_is_generated_when_omitted() -> None:
    with _workspace_client() as (client, organization):
        site = client.get(f"/api/v1/organizations/{organization.id}/sites").json()["items"][0]
        response = client.post(
            f"/api/v1/organizations/{organization.id}/sites/{site['id']}/machines",
            json={"display_name": "Máy xạ trị tự tạo mã"},
        )

    assert response.status_code == 201, response.text
    assert response.json()["display_name"] == "Máy xạ trị tự tạo mã"
    assert response.json()["stable_machine_id"].startswith("RTCONNECT-")


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


def test_invitation_revoke_is_terminal_and_allows_a_new_invitation() -> None:
    with _workspace_client() as (client, organization):
        created = client.post(
            f"/api/v1/organizations/{organization.id}/invitations",
            json={"email": "revoked@example.com"},
        )
        assert created.status_code == 201, created.text
        invitation = created.json()

        revoked = client.post(
            f"/api/v1/organizations/{organization.id}/invitations/{invitation['id']}/revoke"
        )
        assert revoked.status_code == 200, revoked.text
        assert revoked.json()["status"] == "REVOKED"
        assert revoked.json()["revoked_at"]

        client.app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
            subject="synthetic-revoked-invitee-subject",
            email="revoked@example.com",
            claims={"sub": "synthetic-revoked-invitee-subject"},
        )
        rejected = client.post(
            "/api/v1/organizations/invitations/accept",
            json={"token": invitation["token"]},
        )
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["code"] == "INVITATION_INVALID"

        client.app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
            subject="synthetic-supabase-subject",
            email="synthetic.user@example.invalid",
            claims={"sub": "synthetic-supabase-subject"},
        )
        recreated = client.post(
            f"/api/v1/organizations/{organization.id}/invitations",
            json={"email": "revoked@example.com"},
        )
        assert recreated.status_code == 201, recreated.text
        assert recreated.json()["id"] != invitation["id"]

        closed = client.get(
            f"/api/v1/organizations/{organization.id}/invitations",
            params={"include_closed": True},
        )
        assert closed.status_code == 200, closed.text
        statuses = {item["id"]: item["status"] for item in closed.json()["items"]}
        assert statuses[invitation["id"]] == "REVOKED"
        assert statuses[recreated.json()["id"]] == "PENDING"


def test_expired_invitation_is_rejected_and_can_be_reissued() -> None:
    with _workspace_client() as (client, organization):
        created = client.post(
            f"/api/v1/organizations/{organization.id}/invitations",
            json={"email": "expired@example.com", "expires_in_days": 1},
        )
        assert created.status_code == 201, created.text
        invitation = created.json()

        dependency = client.app.dependency_overrides[get_session]
        session_generator = dependency()
        session = next(session_generator)
        try:
            stored = session.get(OrganizationInvitation, UUID(invitation["id"]))
            assert stored is not None
            stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            session.commit()
        finally:
            session_generator.close()

        listed = client.get(
            f"/api/v1/organizations/{organization.id}/invitations",
            params={"include_closed": True},
        )
        assert listed.status_code == 200, listed.text
        assert listed.json()["items"][0]["status"] == "EXPIRED"

        client.app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
            subject="synthetic-expired-invitee-subject",
            email="expired@example.com",
            claims={"sub": "synthetic-expired-invitee-subject"},
        )
        rejected = client.post(
            "/api/v1/organizations/invitations/accept",
            json={"token": invitation["token"]},
        )
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["code"] == "INVITATION_INVALID"

        client.app.dependency_overrides[require_identity] = lambda: AuthenticatedIdentity(
            subject="synthetic-supabase-subject",
            email="synthetic.user@example.invalid",
            claims={"sub": "synthetic-supabase-subject"},
        )
        reissued = client.post(
            f"/api/v1/organizations/{organization.id}/invitations",
            json={"email": "expired@example.com"},
        )
        assert reissued.status_code == 201, reissued.text
        assert reissued.json()["id"] != invitation["id"]


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


def test_invited_peer_identity_has_the_same_organization_actions() -> None:
    """The membership boundary is shared; it is not an action-role boundary."""

    with _workspace_client() as (client, organization):
        invitation_response = client.post(
            f"/api/v1/organizations/{organization.id}/invitations",
            json={"email": "peer.engineer@example.invalid"},
        )
        assert invitation_response.status_code == 201, invitation_response.text
        invitation = invitation_response.json()

        peer = AuthenticatedIdentity(
            subject="synthetic-peer-engineer-subject",
            email="peer.engineer@example.invalid",
            claims={"sub": "synthetic-peer-engineer-subject"},
        )
        client.app.dependency_overrides[require_identity] = lambda: peer

        accepted = client.post(
            "/api/v1/organizations/invitations/accept",
            json={"token": invitation["token"]},
        )
        assert accepted.status_code == 200, accepted.text
        peer_membership_id = accepted.json()["id"]

        bootstrap = client.get("/api/v1/session/bootstrap")
        assert bootstrap.status_code == 200, bootstrap.text
        assert bootstrap.json()["organization"]["id"] == str(organization.id)

        sites = client.get(f"/api/v1/organizations/{organization.id}/sites")
        assert sites.status_code == 200, sites.text
        site_id = sites.json()["items"][0]["id"]
        machines = client.get(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines"
        )
        assert machines.status_code == 200, machines.text
        machine = machines.json()["items"][0]

        updated_machine = client.patch(
            f"/api/v1/organizations/{organization.id}/sites/{site_id}/machines/{machine['id']}",
            json={
                "expected_revision": machine["revision"],
                "display_name": "Peer-updated Synthetic Linac",
            },
        )
        assert updated_machine.status_code == 200, updated_machine.text
        assert updated_machine.json()["display_name"] == "Peer-updated Synthetic Linac"

        members = client.get(
            f"/api/v1/organizations/{organization.id}/members",
            params={"include_inactive": True},
        )
        assert members.status_code == 200, members.text
        assert members.json()["total"] == 2
        original_member = next(
            item for item in members.json()["items"] if item["id"] != peer_membership_id
        )

        deactivated = client.patch(
            f"/api/v1/organizations/{organization.id}/members/{original_member['id']}",
            json={"is_active": False},
        )
        assert deactivated.status_code == 200, deactivated.text
        assert deactivated.json()["is_active"] is False

        reactivated = client.patch(
            f"/api/v1/organizations/{organization.id}/members/{original_member['id']}",
            json={"is_active": True},
        )
        assert reactivated.status_code == 200, reactivated.text
        assert reactivated.json()["is_active"] is True
