"""P3 session bootstrap and dashboard read endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import Machine, Site
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["workspace"])


class OrganizationContextResponse(BaseModel):
    id: UUID
    name: str


class SessionBootstrapResponse(BaseModel):
    subject: str
    email: str | None
    organization: OrganizationContextResponse


class DashboardSummaryResponse(BaseModel):
    organization: OrganizationContextResponse
    site_count: int
    machine_count: int
    recent_qa_count: int = 0
    active_job_count: int = 0
    warnings: list[str] = []


def _context(
    identity: AuthenticatedIdentity, session: Session
) -> SessionContext:
    return resolve_session_context(session, identity)


@router.get("/session/bootstrap", response_model=SessionBootstrapResponse)
def session_bootstrap(
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> SessionBootstrapResponse:
    context = _context(identity, session)
    return SessionBootstrapResponse(
        subject=context.subject,
        email=context.email,
        organization=OrganizationContextResponse(
            id=context.organization_id, name=context.organization_name
        ),
    )


@router.get("/organizations/{organization_id}/dashboard", response_model=DashboardSummaryResponse)
def organization_dashboard(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> DashboardSummaryResponse:
    context = _context(identity, session)
    if organization_id != context.organization_id:
        raise DomainError(
            "ORGANIZATION_SCOPE_MISMATCH",
            "The requested organization is outside the authenticated membership scope.",
            403,
        )
    site_count = session.scalar(
        select(func.count())
        .select_from(Site)
        .where(Site.organization_id == context.organization_id, Site.is_archived.is_(False))
    )
    machine_count = session.scalar(
        select(func.count())
        .select_from(Machine)
        .where(Machine.organization_id == context.organization_id, Machine.is_archived.is_(False))
    )
    return DashboardSummaryResponse(
        organization=OrganizationContextResponse(
            id=context.organization_id, name=context.organization_name
        ),
        site_count=site_count or 0,
        machine_count=machine_count or 0,
    )
