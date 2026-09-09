"""P4 organization, site and machine lifecycle endpoints.

All write actions require an active organization membership, but the API does
not introduce an action-level doctor/engineer hierarchy. Organization scope is
resolved from the verified identity before any resource query is performed.
"""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    Machine,
    Organization,
    OrganizationInvitation,
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


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class OrganizationInvitationCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    expires_in_days: int = Field(default=7, ge=1, le=30)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().casefold()
        if not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("A valid email address is required.")
        return normalized


class OrganizationInvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=20, max_length=256)


class OrganizationMemberPatchRequest(BaseModel):
    is_active: bool


class OrganizationMemberResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str | None
    display_name: str | None
    is_active: bool


class OrganizationMemberCollectionResponse(BaseModel):
    items: list[OrganizationMemberResponse]
    total: int
    offset: int
    limit: int


class OrganizationInvitationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    invited_email: str
    status: str
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class OrganizationInvitationCreateResponse(OrganizationInvitationResponse):
    """The raw token is returned only on creation so the caller can share it."""

    token: str


class OrganizationInvitationCollectionResponse(BaseModel):
    items: list[OrganizationInvitationResponse]
    total: int
    offset: int
    limit: int


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


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_datetime(value: datetime) -> datetime:
    """Treat SQLite's naive test timestamps as UTC like PostgreSQL timestamps."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalized_identity_email(identity: AuthenticatedIdentity) -> str | None:
    if identity.email is None:
        return None
    normalized = identity.email.strip().casefold()
    return normalized if _EMAIL_PATTERN.fullmatch(normalized) else None


def _ensure_identity(session: Session, identity: AuthenticatedIdentity) -> UserIdentity:
    user_identity = session.scalar(
        select(UserIdentity).where(UserIdentity.supabase_user_id == identity.subject)
    )
    if user_identity is None:
        user_identity = UserIdentity(
            supabase_user_id=identity.subject,
            email=identity.email,
        )
        session.add(user_identity)
        session.flush()
    elif identity.email and user_identity.email != identity.email:
        # Keep the application projection aligned with the verified claim.  No
        # password or invitation token is copied into the projection.
        user_identity.email = identity.email
    return user_identity


def _invitation_status(invitation: OrganizationInvitation, now: datetime) -> str:
    if invitation.status == "PENDING" and _utc_datetime(invitation.expires_at) <= now:
        return "EXPIRED"
    return invitation.status


def _member_response(membership: OrganizationMembership) -> OrganizationMemberResponse:
    user_identity = membership.user_identity
    return OrganizationMemberResponse(
        id=membership.id,
        organization_id=membership.organization_id,
        email=user_identity.email,
        display_name=user_identity.display_name,
        is_active=membership.is_active,
    )


def _invitation_response(
    invitation: OrganizationInvitation,
    now: datetime,
) -> OrganizationInvitationResponse:
    return OrganizationInvitationResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        invited_email=invitation.invited_email,
        status=_invitation_status(invitation, now),
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
    )


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


@router.post(
    "/invitations/accept",
    response_model=OrganizationMemberResponse,
)
def accept_organization_invitation(
    request: OrganizationInvitationAcceptRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationMemberResponse:
    """Accept a one-time invitation with the currently verified identity.

    The invitation is looked up by a hash of the random token.  Before a
    membership is created, the verified email claim must match the invitation;
    an email-domain match or a client-supplied organization is never enough.
    Repeating the same token with the same identity returns the existing
    membership and does not create a second row.
    """

    token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
    invitation = session.scalar(
        select(OrganizationInvitation).where(OrganizationInvitation.token_hash == token_hash)
    )
    if invitation is None:
        raise DomainError(
            "INVITATION_INVALID",
            "The invitation is invalid, expired, revoked, or has already been used.",
            409,
        )

    user_identity = _ensure_identity(session, identity)
    now = _utc_now()
    organization = session.scalar(
        select(Organization).where(
            Organization.id == invitation.organization_id,
            Organization.is_archived.is_(False),
        )
    )
    if organization is None:
        session.rollback()
        raise DomainError(
            "INVITATION_INVALID",
            "The invitation organization is no longer available.",
            409,
        )

    if invitation.status == "ACCEPTED":
        if invitation.accepted_by_user_identity_id != user_identity.id:
            session.rollback()
            raise DomainError(
                "INVITATION_INVALID",
                "The invitation has already been used by another identity.",
                409,
            )
        membership = session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == invitation.organization_id,
                OrganizationMembership.user_identity_id == user_identity.id,
            )
        )
        if membership is None:
            session.rollback()
            raise DomainError(
                "INVITATION_INVALID",
                "The invitation membership record is unavailable.",
                409,
            )
        session.rollback()
        return _member_response(membership)

    if invitation.status != "PENDING" or _utc_datetime(invitation.expires_at) <= now:
        if invitation.status == "PENDING":
            invitation.status = "EXPIRED"
            session.commit()
        else:
            session.rollback()
        raise DomainError(
            "INVITATION_INVALID",
            "The invitation is invalid, expired, revoked, or has already been used.",
            409,
        )

    verified_email = _normalized_identity_email(identity)
    if verified_email is None or verified_email != invitation.invited_email:
        session.rollback()
        raise DomainError(
            "INVITATION_INVALID",
            "The verified identity does not match this invitation.",
            403,
        )

    existing_active_membership = session.scalar(
        select(OrganizationMembership)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_identity_id == user_identity.id,
            OrganizationMembership.is_active.is_(True),
            OrganizationMembership.organization_id != invitation.organization_id,
            Organization.is_archived.is_(False),
        )
    )
    if existing_active_membership is not None:
        session.rollback()
        raise DomainError(
            "ORGANIZATION_CONTEXT_ALREADY_ASSIGNED",
            "This identity already has an active organization context.",
            409,
        )

    membership = session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == invitation.organization_id,
            OrganizationMembership.user_identity_id == user_identity.id,
        )
    )
    if membership is None:
        membership = OrganizationMembership(
            organization_id=invitation.organization_id,
            user_identity_id=user_identity.id,
            is_active=True,
        )
        session.add(membership)
        session.flush()
    else:
        membership.is_active = True

    invitation.status = "ACCEPTED"
    invitation.accepted_at = now
    invitation.accepted_by_user_identity_id = user_identity.id
    _audit(
        session,
        SessionContext(
            subject=identity.subject,
            email=identity.email,
            organization_id=organization.id,
            organization_name=organization.name,
        ),
        "ORGANIZATION_INVITATION_ACCEPTED",
        "OrganizationInvitation",
        invitation.id,
        {"invited_email": invitation.invited_email},
    )
    _commit_or_raise(
        session,
        "INVITATION_CONFLICT",
        "The invitation could not be accepted because membership changed concurrently.",
    )
    return _member_response(membership)


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


@router.get(
    "/{organization_id}/members",
    response_model=OrganizationMemberCollectionResponse,
)
def list_organization_members(
    organization_id: UUID,
    include_inactive: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationMemberCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    conditions = [OrganizationMembership.organization_id == organization_id]
    if not include_inactive:
        conditions.append(OrganizationMembership.is_active.is_(True))
    query = (
        select(OrganizationMembership)
        .join(UserIdentity, UserIdentity.id == OrganizationMembership.user_identity_id)
        .where(*conditions)
        .order_by(func.lower(UserIdentity.email), OrganizationMembership.id)
    )
    count_query = select(func.count()).select_from(OrganizationMembership).where(*conditions)
    memberships = session.scalars(query.offset(offset).limit(limit)).all()
    total = session.scalar(count_query) or 0
    return OrganizationMemberCollectionResponse(
        items=[_member_response(item) for item in memberships],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.patch(
    "/{organization_id}/members/{membership_id}",
    response_model=OrganizationMemberResponse,
)
def update_organization_membership(
    organization_id: UUID,
    membership_id: UUID,
    request: OrganizationMemberPatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationMemberResponse:
    context = _context_for_organization(organization_id, identity, session)
    membership = session.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if membership is None:
        raise DomainError(
            "MEMBERSHIP_NOT_FOUND",
            "Membership was not found in this organization.",
            404,
        )
    if not request.is_active and membership.is_active:
        active_count = session.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.is_active.is_(True),
            )
        ) or 0
        if active_count <= 1:
            raise DomainError(
                "LAST_MEMBERSHIP_CONFLICT",
                "An organization must keep at least one active membership.",
                409,
            )
    membership.is_active = request.is_active
    _audit(
        session,
        context,
        "ORGANIZATION_MEMBERSHIP_UPDATED",
        "OrganizationMembership",
        membership.id,
        {"is_active": request.is_active},
    )
    _commit_or_raise(
        session,
        "MEMBERSHIP_CONFLICT",
        "The membership could not be updated because it changed concurrently.",
    )
    return _member_response(membership)


@router.post(
    "/{organization_id}/invitations",
    response_model=OrganizationInvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_invitation(
    organization_id: UUID,
    request: OrganizationInvitationCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationInvitationCreateResponse:
    context = _context_for_organization(organization_id, identity, session)
    email = request.email
    active_member = session.scalar(
        select(OrganizationMembership)
        .join(UserIdentity, UserIdentity.id == OrganizationMembership.user_identity_id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_active.is_(True),
            func.lower(UserIdentity.email) == email,
        )
    )
    if active_member is not None:
        raise DomainError(
            "INVITATION_ALREADY_MEMBER",
            "This verified email already has an active membership.",
            409,
        )

    now = _utc_now()
    pending = session.scalar(
        select(OrganizationInvitation)
        .where(
            OrganizationInvitation.organization_id == organization_id,
            OrganizationInvitation.invited_email == email,
            OrganizationInvitation.status == "PENDING",
        )
        .order_by(desc(OrganizationInvitation.created_at))
    )
    if pending is not None:
        if _utc_datetime(pending.expires_at) > now:
            raise DomainError(
                "INVITATION_ALREADY_PENDING",
                "An active invitation for this email already exists.",
                409,
            )
        pending.status = "EXPIRED"

    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=organization_id,
        invited_email=email,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        status="PENDING",
        expires_at=now + timedelta(days=request.expires_in_days),
        created_by_user_identity_id=session.scalar(
            select(UserIdentity.id).where(UserIdentity.supabase_user_id == identity.subject)
        ),
    )
    session.add(invitation)
    session.flush()
    _audit(
        session,
        context,
        "ORGANIZATION_INVITATION_CREATED",
        "OrganizationInvitation",
        invitation.id,
        {
            "invited_email": email,
            "expires_at": invitation.expires_at.isoformat(),
        },
    )
    _commit_or_raise(
        session,
        "INVITATION_CONFLICT",
        "The invitation could not be created because a concurrent invitation exists.",
    )
    return OrganizationInvitationCreateResponse(
        **_invitation_response(invitation, now).model_dump(),
        token=token,
    )


@router.get(
    "/{organization_id}/invitations",
    response_model=OrganizationInvitationCollectionResponse,
)
def list_organization_invitations(
    organization_id: UUID,
    include_closed: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationInvitationCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    conditions = [OrganizationInvitation.organization_id == organization_id]
    if not include_closed:
        conditions.append(OrganizationInvitation.status == "PENDING")
    query = (
        select(OrganizationInvitation)
        .where(*conditions)
        .order_by(desc(OrganizationInvitation.created_at), OrganizationInvitation.id)
    )
    count_query = select(func.count()).select_from(OrganizationInvitation).where(*conditions)
    now = _utc_now()
    invitations = session.scalars(query.offset(offset).limit(limit)).all()
    total = session.scalar(count_query) or 0
    return OrganizationInvitationCollectionResponse(
        items=[_invitation_response(item, now) for item in invitations],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post(
    "/{organization_id}/invitations/{invitation_id}/revoke",
    response_model=OrganizationInvitationResponse,
)
def revoke_organization_invitation(
    organization_id: UUID,
    invitation_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> OrganizationInvitationResponse:
    context = _context_for_organization(organization_id, identity, session)
    invitation = session.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == organization_id,
        )
    )
    if invitation is None:
        raise DomainError(
            "INVITATION_NOT_FOUND",
            "Invitation was not found in this organization.",
            404,
        )
    if invitation.status != "PENDING":
        raise DomainError("INVITATION_INVALID", "Only a pending invitation can be revoked.", 409)
    invitation.status = "REVOKED"
    invitation.revoked_at = _utc_now()
    _audit(
        session,
        context,
        "ORGANIZATION_INVITATION_REVOKED",
        "OrganizationInvitation",
        invitation.id,
        {"invited_email": invitation.invited_email},
    )
    _commit_or_raise(session, "INVITATION_CONFLICT", "The invitation could not be revoked.")
    return _invitation_response(invitation, _utc_now())


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
