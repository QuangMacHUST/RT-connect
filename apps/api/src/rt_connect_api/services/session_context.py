"""Resolve verified identities to their only legitimate RT-CONNECT organization context."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import Organization, OrganizationMembership, UserIdentity
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity


@dataclass(frozen=True)
class SessionContext:
    subject: str
    email: str | None
    organization_id: UUID
    organization_name: str


def resolve_session_context(session: Session, identity: AuthenticatedIdentity) -> SessionContext:
    """Look up scope at the first database query; no client-provided organization is trusted."""

    row = session.execute(
        select(UserIdentity, OrganizationMembership, Organization)
        .join(OrganizationMembership, OrganizationMembership.user_identity_id == UserIdentity.id)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            UserIdentity.supabase_user_id == identity.subject,
            UserIdentity.is_active.is_(True),
            OrganizationMembership.is_active.is_(True),
            Organization.is_archived.is_(False),
        )
        .order_by(Organization.name)
    ).first()
    if row is None:
        raise DomainError(
            "ORGANIZATION_MEMBERSHIP_REQUIRED",
            "No active RT-CONNECT organization membership exists for this identity.",
            403,
        )
    user_identity, _, organization = row
    return SessionContext(
        subject=user_identity.supabase_user_id,
        email=user_identity.email or identity.email,
        organization_id=organization.id,
        organization_name=organization.name,
    )
