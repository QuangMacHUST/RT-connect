"""P4 organization, site and machine lifecycle endpoints.

All write actions require an active organization membership, but the API does
not introduce an action-level doctor/engineer hierarchy. Organization scope is
resolved from the verified identity before any resource query is performed.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    Machine,
    Organization,
    OrganizationMembership,
    Site,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(prefix="/organizations", tags=["organization"])

MachineStatus = Literal["ACTIVE", "OFFLINE", "MAINTENANCE", "RETIRED"]


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class OrganizationPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_archived: bool | None = None


class SiteCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class SitePatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_archived: bool | None = None


class MachineCreateRequest(BaseModel):
    stable_machine_id: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    status: MachineStatus = "ACTIVE"


class MachinePatchRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    status: MachineStatus | None = None
    is_archived: bool | None = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    is_archived: bool


class SiteResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    is_archived: bool


class MachineResponse(BaseModel):
    id: UUID
    organization_id: UUID
    site_id: UUID
    stable_machine_id: str
    display_name: str
    manufacturer: str | None
    model: str | None
    status: str
    is_archived: bool


class SiteCollectionResponse(BaseModel):
    items: list[SiteResponse]
    total: int
    offset: int
    limit: int


class MachineCollectionResponse(BaseModel):
    items: list[MachineResponse]
    total: int
    offset: int
    limit: int


def _context_for_organization(
    organization_id: UUID, identity: AuthenticatedIdentity, session: Session
) -> SessionContext:
    context = resolve_session_context(session, identity)
    if context.organization_id != organization_id:
        raise DomainError(
            "ORGANIZATION_SCOPE_MISMATCH",
            "The requested organization is outside the authenticated membership scope.",
            403,
        )
    return context


def _audit(
    session: Session,
    context: SessionContext,
    event_type: str,
    entity_type: str,
    entity_id: UUID | None,
    payload: dict[str, object],
) -> None:
    actor = session.scalar(
        select(UserIdentity).where(UserIdentity.supabase_user_id == context.subject)
    )
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=actor.id if actor else None,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
    )


def _commit_or_raise(session: Session, code: str, message: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(code, message, 409) from exc


def _organization_response(organization: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id, name=organization.name, is_archived=organization.is_archived
    )


def _site_response(site: Site) -> SiteResponse:
    return SiteResponse(
        id=site.id,
        organization_id=site.organization_id,
        name=site.name,
        is_archived=site.is_archived,
    )


def _machine_response(machine: Machine) -> MachineResponse:
    return MachineResponse(
        id=machine.id,
        organization_id=machine.organization_id,
        site_id=machine.site_id,
        stable_machine_id=machine.stable_machine_id,
        display_name=machine.display_name,
        manufacturer=machine.manufacturer,
        model=machine.model,
        status=machine.status,
        is_archived=machine.is_archived,
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    request: OrganizationCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationResponse:
    """Create an organization and make the verified caller its first member."""

    user_identity = session.scalar(
        select(UserIdentity).where(UserIdentity.supabase_user_id == identity.subject)
    )
    if user_identity is None:
        user_identity = UserIdentity(supabase_user_id=identity.subject, email=identity.email)
        session.add(user_identity)
        session.flush()
    if (
        session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.user_identity_id == user_identity.id,
                OrganizationMembership.is_active.is_(True),
            )
        )
        is not None
    ):
        raise DomainError(
            "ORGANIZATION_CONTEXT_ALREADY_ASSIGNED",
            "This identity already has an active organization context.",
            409,
        )
    if session.scalar(select(Organization).where(Organization.name == request.name)) is not None:
        raise DomainError("ORGANIZATION_NAME_CONFLICT", "Organization name already exists.", 409)
    organization = Organization(name=request.name)
    session.add(organization)
    session.flush()
    session.add(
        OrganizationMembership(organization_id=organization.id, user_identity_id=user_identity.id)
    )
    session.add(
        AuditEvent(
            organization_id=organization.id,
            actor_user_identity_id=user_identity.id,
            event_type="ORGANIZATION_CREATED",
            entity_type="Organization",
            entity_id=organization.id,
            payload={"name": organization.name},
        )
    )
    _commit_or_raise(session, "ORGANIZATION_NAME_CONFLICT", "Organization name already exists.")
    return _organization_response(organization)


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationResponse:
    _context_for_organization(organization_id, identity, session)
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise DomainError("ORGANIZATION_NOT_FOUND", "Organization was not found.", 404)
    return _organization_response(organization)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: UUID,
    request: OrganizationPatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationResponse:
    context = _context_for_organization(organization_id, identity, session)
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise DomainError("ORGANIZATION_NOT_FOUND", "Organization was not found.", 404)
    if request.name is None and request.is_archived is None:
        raise DomainError("NO_CHANGES", "At least one organization field is required.", 400)
    if request.name is not None:
        organization.name = request.name
    if request.is_archived is not None:
        organization.is_archived = request.is_archived
    _audit(
        session,
        context,
        "ORGANIZATION_UPDATED",
        "Organization",
        organization.id,
        request.model_dump(exclude_none=True),
    )
    _commit_or_raise(session, "ORGANIZATION_NAME_CONFLICT", "Organization name already exists.")
    return _organization_response(organization)


@router.get("/{organization_id}/sites", response_model=SiteCollectionResponse)
def list_sites(
    organization_id: UUID,
    q: str | None = Query(default=None, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    include_archived: bool = Query(default=False),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> SiteCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    query = select(Site).where(Site.organization_id == organization_id)
    count_query = (
        select(func.count()).select_from(Site).where(Site.organization_id == organization_id)
    )
    if not include_archived:
        query = query.where(Site.is_archived.is_(False))
        count_query = count_query.where(Site.is_archived.is_(False))
    if q:
        query = query.where(Site.name.ilike(f"%{q}%"))
        count_query = count_query.where(Site.name.ilike(f"%{q}%"))
    sites = session.scalars(query.order_by(Site.name).offset(offset).limit(limit)).all()
    total = session.scalar(count_query) or 0
    return SiteCollectionResponse(
        items=[_site_response(site) for site in sites], total=total, offset=offset, limit=limit
    )


@router.post(
    "/{organization_id}/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED
)
def create_site(
    organization_id: UUID,
    request: SiteCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> SiteResponse:
    context = _context_for_organization(organization_id, identity, session)
    existing = session.scalar(
        select(Site).where(
            Site.organization_id == organization_id,
            Site.name == request.name,
            Site.is_archived.is_(False),
        )
    )
    if existing is not None:
        raise DomainError(
            "SITE_NAME_CONFLICT", "Site name already exists in this organization.", 409
        )
    site = Site(organization_id=organization_id, name=request.name)
    session.add(site)
    session.flush()
    _audit(session, context, "SITE_CREATED", "Site", site.id, {"name": site.name})
    _commit_or_raise(
        session, "SITE_NAME_CONFLICT", "Site name already exists in this organization."
    )
    return _site_response(site)


@router.patch("/{organization_id}/sites/{site_id}", response_model=SiteResponse)
def update_site(
    organization_id: UUID,
    site_id: UUID,
    request: SitePatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> SiteResponse:
    context = _context_for_organization(organization_id, identity, session)
    site = session.scalar(
        select(Site).where(Site.id == site_id, Site.organization_id == organization_id)
    )
    if site is None:
        raise DomainError("SITE_NOT_FOUND", "Site was not found in this organization.", 404)
    if request.name is None and request.is_archived is None:
        raise DomainError("NO_CHANGES", "At least one site field is required.", 400)
    if request.name is not None:
        conflict = session.scalar(
            select(Site).where(
                Site.organization_id == organization_id,
                Site.name == request.name,
                Site.id != site_id,
                Site.is_archived.is_(False),
            )
        )
        if conflict is not None:
            raise DomainError(
                "SITE_NAME_CONFLICT", "Site name already exists in this organization.", 409
            )
        site.name = request.name
    if request.is_archived is not None:
        site.is_archived = request.is_archived
    _audit(session, context, "SITE_UPDATED", "Site", site.id, request.model_dump(exclude_none=True))
    _commit_or_raise(
        session, "SITE_NAME_CONFLICT", "Site name already exists in this organization."
    )
    return _site_response(site)


@router.get("/{organization_id}/sites/{site_id}/machines", response_model=MachineCollectionResponse)
def list_machines(
    organization_id: UUID,
    site_id: UUID,
    q: str | None = Query(default=None, max_length=200),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    include_archived: bool = Query(default=False),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> MachineCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    if (
        session.scalar(
            select(Site.id).where(Site.id == site_id, Site.organization_id == organization_id)
        )
        is None
    ):
        raise DomainError("SITE_NOT_FOUND", "Site was not found in this organization.", 404)
    query = select(Machine).where(
        Machine.organization_id == organization_id, Machine.site_id == site_id
    )
    count_query = (
        select(func.count())
        .select_from(Machine)
        .where(Machine.organization_id == organization_id, Machine.site_id == site_id)
    )
    if not include_archived:
        query = query.where(Machine.is_archived.is_(False))
        count_query = count_query.where(Machine.is_archived.is_(False))
    if q:
        pattern = f"%{q}%"
        query = query.where(
            Machine.display_name.ilike(pattern) | Machine.stable_machine_id.ilike(pattern)
        )
        count_query = count_query.where(
            Machine.display_name.ilike(pattern) | Machine.stable_machine_id.ilike(pattern)
        )
    machines = session.scalars(
        query.order_by(Machine.display_name).offset(offset).limit(limit)
    ).all()
    total = session.scalar(count_query) or 0
    return MachineCollectionResponse(
        items=[_machine_response(machine) for machine in machines],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{organization_id}/sites/{site_id}/machines",
    response_model=MachineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_machine(
    organization_id: UUID,
    site_id: UUID,
    request: MachineCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> MachineResponse:
    context = _context_for_organization(organization_id, identity, session)
    if (
        session.scalar(
            select(Site.id).where(Site.id == site_id, Site.organization_id == organization_id)
        )
        is None
    ):
        raise DomainError("SITE_NOT_FOUND", "Site was not found in this organization.", 404)
    if (
        session.scalar(
            select(Machine).where(Machine.stable_machine_id == request.stable_machine_id)
        )
        is not None
    ):
        raise DomainError("MACHINE_ID_CONFLICT", "Stable machine ID already exists.", 409)
    machine = Machine(organization_id=organization_id, site_id=site_id, **request.model_dump())
    session.add(machine)
    session.flush()
    _audit(session, context, "MACHINE_CREATED", "Machine", machine.id, request.model_dump())
    _commit_or_raise(session, "MACHINE_ID_CONFLICT", "Stable machine ID already exists.")
    return _machine_response(machine)


@router.patch(
    "/{organization_id}/sites/{site_id}/machines/{machine_id}", response_model=MachineResponse
)
def update_machine(
    organization_id: UUID,
    site_id: UUID,
    machine_id: UUID,
    request: MachinePatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> MachineResponse:
    context = _context_for_organization(organization_id, identity, session)
    machine = session.scalar(
        select(Machine).where(
            Machine.id == machine_id,
            Machine.organization_id == organization_id,
            Machine.site_id == site_id,
        )
    )
    if machine is None:
        raise DomainError(
            "MACHINE_NOT_FOUND", "Machine was not found in this organization/site.", 404
        )
    changes = request.model_dump(exclude_none=True)
    if not changes:
        raise DomainError("NO_CHANGES", "At least one machine field is required.", 400)
    for field, value in changes.items():
        setattr(machine, field, value)
    _audit(session, context, "MACHINE_UPDATED", "Machine", machine.id, changes)
    _commit_or_raise(session, "MACHINE_ID_CONFLICT", "Stable machine ID already exists.")
    return _machine_response(machine)
