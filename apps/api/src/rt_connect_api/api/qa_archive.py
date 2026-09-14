"""P5 QA Archive, nested folders and organization-scoped QA cases."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    Artifact,
    AuditEvent,
    DVHAnalysisRun,
    Folder,
    GammaAnalysisRun,
    Machine,
    MachineQARun,
    QACase,
    ReportRevision,
    Site,
    TrendPoint,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.qa_catalog import get_qa_test_definition
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["qa-archive"])

QACycle = Literal["DAILY", "MONTHLY", "ANNUAL", "CUSTOM"]
CaseStatus = Literal["OPEN", "IN_REVIEW", "COMPLETED", "CANCELLED"]


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_folder_id: UUID | None = None


class FolderPatchRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    parent_folder_id: UUID | None = None
    is_archived: bool | None = None


class FolderResponse(BaseModel):
    id: UUID
    organization_id: UUID
    parent_folder_id: UUID | None
    name: str
    path: str
    depth: int
    is_archived: bool


class FolderTreeResponse(BaseModel):
    items: list[FolderResponse]
    total: int
    include_archived: bool


class QACaseCreateRequest(BaseModel):
    site_id: UUID
    machine_id: UUID
    primary_folder_id: UUID
    qa_type: str | None = Field(default=None, min_length=1, max_length=100)
    qa_definition_key: str | None = Field(default=None, min_length=1, max_length=120)
    qa_cycle: QACycle
    performed_at: datetime
    scheduled_at: datetime | None = None
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    protocol_version_id: UUID | None = None
    status_note: str | None = Field(default=None, max_length=4000)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class QACasePatchRequest(BaseModel):
    primary_folder_id: UUID | None = None
    qa_type: str | None = Field(default=None, min_length=1, max_length=100)
    qa_definition_key: str | None = Field(default=None, min_length=1, max_length=120)
    qa_cycle: QACycle | None = None
    performed_at: datetime | None = None
    scheduled_at: datetime | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    protocol_version_id: UUID | None = None
    status_note: str | None = Field(default=None, max_length=4000)
    case_status: CaseStatus | None = None
    is_archived: bool | None = None


class QACaseResponse(BaseModel):
    id: UUID
    organization_id: UUID
    site_id: UUID
    machine_id: UUID
    primary_folder_id: UUID
    qa_definition_key: str | None
    qa_type: str
    qa_cycle: str
    performed_at: datetime
    scheduled_at: datetime | None
    title: str
    description: str | None
    protocol_version_id: UUID | None
    status_note: str | None
    case_status: str
    is_archived: bool


class QACaseCollectionResponse(BaseModel):
    items: list[QACaseResponse]
    total: int
    offset: int
    limit: int
    include_archived: bool


class QACasePurgeReferenceResponse(BaseModel):
    source: str
    count: int = Field(ge=1)


class QACasePurgePreviewResponse(BaseModel):
    case_id: UUID
    title: str
    site_name: str
    machine_name: str
    performed_at: datetime
    is_archived: bool
    can_purge: bool
    references: list[QACasePurgeReferenceResponse]


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


def _commit_or_raise(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "QA_ARCHIVE_CONFLICT",
            "The requested QA archive change conflicts with existing data.",
            409,
        ) from exc


def _safe_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: str(value)
        if isinstance(value, UUID)
        else value.isoformat()
        if isinstance(value, datetime)
        else value
        for key, value in payload.items()
    }


def _folder_path(folder: Folder, folders_by_id: dict[UUID, Folder]) -> tuple[str, int]:
    parts: list[str] = []
    current: Folder | None = folder
    visited: set[UUID] = set()
    while current is not None and current.id not in visited:
        visited.add(current.id)
        parts.append(current.name)
        current = folders_by_id.get(current.parent_folder_id) if current.parent_folder_id else None
    parts.reverse()
    return "/".join(parts), max(len(parts) - 1, 0)


def _folder_response(folder: Folder, folders_by_id: dict[UUID, Folder]) -> FolderResponse:
    path, depth = _folder_path(folder, folders_by_id)
    return FolderResponse(
        id=folder.id,
        organization_id=folder.organization_id,
        parent_folder_id=folder.parent_folder_id,
        name=folder.name,
        path=path,
        depth=depth,
        is_archived=folder.is_archived,
    )


def _folder_or_error(session: Session, organization_id: UUID, folder_id: UUID) -> Folder:
    folder = session.scalar(
        select(Folder).where(Folder.id == folder_id, Folder.organization_id == organization_id)
    )
    if folder is None:
        raise DomainError("FOLDER_NOT_FOUND", "Folder was not found in this organization.", 404)
    return folder


def _active_parent_or_error(
    session: Session, organization_id: UUID, parent_folder_id: UUID | None
) -> Folder | None:
    if parent_folder_id is None:
        return None
    parent = _folder_or_error(session, organization_id, parent_folder_id)
    if parent.is_archived:
        raise DomainError(
            "FOLDER_PARENT_ARCHIVED", "An archived folder cannot contain new data.", 409
        )
    return parent


def _descendant_ids(folders: Sequence[Folder], root_id: UUID) -> set[UUID]:
    children_by_parent: dict[UUID, list[UUID]] = {}
    for folder in folders:
        if folder.parent_folder_id is not None:
            children_by_parent.setdefault(folder.parent_folder_id, []).append(folder.id)
    descendants: set[UUID] = set()
    pending = list(children_by_parent.get(root_id, []))
    while pending:
        child_id = pending.pop()
        if child_id in descendants:
            continue
        descendants.add(child_id)
        pending.extend(children_by_parent.get(child_id, []))
    return descendants


def _case_response(case: QACase) -> QACaseResponse:
    return QACaseResponse(
        id=case.id,
        organization_id=case.organization_id,
        site_id=case.site_id,
        machine_id=case.machine_id,
        primary_folder_id=case.primary_folder_id,
        qa_definition_key=case.qa_definition_key,
        qa_type=case.qa_type,
        qa_cycle=case.qa_cycle,
        performed_at=case.performed_at,
        scheduled_at=case.scheduled_at,
        title=case.title,
        description=case.description,
        protocol_version_id=case.protocol_version_id,
        status_note=case.status_note,
        case_status=case.case_status,
        is_archived=case.is_archived,
    )


@router.get("/organizations/{organization_id}/folders/tree", response_model=FolderTreeResponse)
def list_folder_tree(
    organization_id: UUID,
    include_archived: bool = Query(default=False),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> FolderTreeResponse:
    _context_for_organization(organization_id, identity, session)
    query = select(Folder).where(Folder.organization_id == organization_id)
    if not include_archived:
        query = query.where(Folder.is_archived.is_(False))
    folders = session.scalars(query.order_by(Folder.name)).all()
    folders_by_id = {folder.id: folder for folder in folders}
    items = [_folder_response(folder, folders_by_id) for folder in folders]
    items.sort(key=lambda item: item.path.casefold())
    return FolderTreeResponse(items=items, total=len(items), include_archived=include_archived)


@router.post(
    "/organizations/{organization_id}/folders",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_folder(
    organization_id: UUID,
    request: FolderCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> FolderResponse:
    context = _context_for_organization(organization_id, identity, session)
    name = request.name.strip()
    if not name:
        raise DomainError("FOLDER_NAME_REQUIRED", "Folder name cannot be blank.", 400)
    parent = _active_parent_or_error(session, organization_id, request.parent_folder_id)
    existing = session.scalar(
        select(Folder).where(
            Folder.organization_id == organization_id,
            Folder.parent_folder_id == request.parent_folder_id,
            Folder.name == name,
            Folder.is_archived.is_(False),
        )
    )
    if existing is not None:
        raise DomainError(
            "FOLDER_NAME_CONFLICT",
            "An active folder with this name already exists here.",
            409,
        )
    folder = Folder(
        organization_id=organization_id,
        parent_folder_id=parent.id if parent else None,
        name=name,
        created_by_user_identity_id=session.scalar(
            select(UserIdentity.id).where(UserIdentity.supabase_user_id == context.subject)
        ),
    )
    session.add(folder)
    session.flush()
    _audit(session, context, "FOLDER_CREATED", "Folder", folder.id, {"name": folder.name})
    _commit_or_raise(session)
    folders = session.scalars(select(Folder).where(Folder.organization_id == organization_id)).all()
    return _folder_response(folder, {item.id: item for item in folders})


@router.get("/folders/{folder_id}", response_model=FolderResponse)
def get_folder(
    folder_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> FolderResponse:
    context = resolve_session_context(session, identity)
    folder = _folder_or_error(session, context.organization_id, folder_id)
    folders = session.scalars(
        select(Folder).where(Folder.organization_id == folder.organization_id)
    ).all()
    return _folder_response(folder, {item.id: item for item in folders})


@router.patch("/folders/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: UUID,
    request: FolderPatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> FolderResponse:
    context = resolve_session_context(session, identity)
    folder = _folder_or_error(session, context.organization_id, folder_id)
    if not request.model_fields_set:
        raise DomainError("NO_CHANGES", "At least one folder field is required.", 400)
    if request.name is not None:
        name = request.name.strip()
        if not name:
            raise DomainError("FOLDER_NAME_REQUIRED", "Folder name cannot be blank.", 400)
        conflict = session.scalar(
            select(Folder).where(
                Folder.organization_id == folder.organization_id,
                Folder.parent_folder_id == folder.parent_folder_id,
                Folder.name == name,
                Folder.id != folder.id,
                Folder.is_archived.is_(False),
            )
        )
        if conflict is not None:
            raise DomainError(
                "FOLDER_NAME_CONFLICT",
                "An active folder with this name already exists here.",
                409,
            )
        folder.name = name
    if "parent_folder_id" in request.model_fields_set:
        parent = _active_parent_or_error(session, folder.organization_id, request.parent_folder_id)
        all_folders = session.scalars(
            select(Folder).where(Folder.organization_id == folder.organization_id)
        ).all()
        if request.parent_folder_id == folder.id or (
            request.parent_folder_id is not None
            and request.parent_folder_id in _descendant_ids(all_folders, folder.id)
        ):
            raise DomainError(
                "FOLDER_CYCLE",
                "A folder cannot be moved into itself or its descendants.",
                409,
            )
        folder.parent_folder_id = parent.id if parent else None
    if request.is_archived is not None:
        folder.is_archived = request.is_archived
        if request.is_archived:
            all_folders = session.scalars(
                select(Folder).where(Folder.organization_id == folder.organization_id)
            ).all()
            archived_ids = _descendant_ids(all_folders, folder.id) | {folder.id}
            for candidate in all_folders:
                if candidate.id in archived_ids:
                    candidate.is_archived = True
    _audit(
        session,
        context,
        "FOLDER_UPDATED",
        "Folder",
        folder.id,
        _safe_payload(request.model_dump(exclude_none=True)),
    )
    _commit_or_raise(session)
    folders = session.scalars(
        select(Folder).where(Folder.organization_id == folder.organization_id)
    ).all()
    return _folder_response(folder, {item.id: item for item in folders})


def _validate_case_references(
    session: Session,
    organization_id: UUID,
    site_id: UUID,
    machine_id: UUID,
    folder_id: UUID,
) -> None:
    site = session.scalar(
        select(Site).where(
            Site.id == site_id,
            Site.organization_id == organization_id,
            Site.is_archived.is_(False),
        )
    )
    if site is None:
        raise DomainError("SITE_NOT_FOUND", "Site was not found or is archived.", 404)
    machine = session.scalar(
        select(Machine).where(
            Machine.id == machine_id,
            Machine.organization_id == organization_id,
            Machine.site_id == site_id,
            Machine.is_archived.is_(False),
        )
    )
    if machine is None:
        raise DomainError(
            "MACHINE_NOT_FOUND", "Machine was not found for this organization/site.", 404
        )
    folder = _folder_or_error(session, organization_id, folder_id)
    if folder.is_archived:
        raise DomainError(
            "FOLDER_ARCHIVED", "A QA case cannot be placed in an archived folder.", 409
        )


@router.get("/organizations/{organization_id}/qa-cases", response_model=QACaseCollectionResponse)
def list_qa_cases(
    organization_id: UUID,
    q: str | None = Query(default=None, max_length=200),
    site_id: UUID | None = None,
    machine_id: UUID | None = None,
    folder_id: UUID | None = None,
    qa_type: str | None = Query(default=None, max_length=100),
    qa_cycle: QACycle | None = None,
    performed_from: datetime | None = None,
    performed_to: datetime | None = None,
    include_archived: bool = Query(default=False),
    archived_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QACaseCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    conditions = [QACase.organization_id == organization_id]
    if archived_only:
        conditions.append(QACase.is_archived.is_(True))
    elif not include_archived:
        conditions.append(QACase.is_archived.is_(False))
    if q:
        pattern = f"%{q}%"
        conditions.append(QACase.title.ilike(pattern) | QACase.description.ilike(pattern))
    if site_id is not None:
        conditions.append(QACase.site_id == site_id)
    if machine_id is not None:
        conditions.append(QACase.machine_id == machine_id)
    if folder_id is not None:
        conditions.append(QACase.primary_folder_id == folder_id)
    if qa_type:
        conditions.append(QACase.qa_type == qa_type)
    if qa_cycle:
        conditions.append(QACase.qa_cycle == qa_cycle)
    if performed_from:
        conditions.append(QACase.performed_at >= performed_from)
    if performed_to:
        conditions.append(QACase.performed_at <= performed_to)
    query = select(QACase).where(*conditions)
    count_query = select(func.count()).select_from(QACase).where(*conditions)
    cases = session.scalars(
        query.order_by(QACase.performed_at.desc(), QACase.title).offset(offset).limit(limit)
    ).all()
    return QACaseCollectionResponse(
        items=[_case_response(case) for case in cases],
        total=session.scalar(count_query) or 0,
        offset=offset,
        limit=limit,
        include_archived=include_archived,
    )


def _case_request_fingerprint(request: QACaseCreateRequest) -> str:
    payload = json.dumps(
        request.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return sha256(payload.encode("utf-8")).hexdigest()


@router.post(
    "/organizations/{organization_id}/qa-cases",
    response_model=QACaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_qa_case(
    organization_id: UUID,
    request: QACaseCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QACaseResponse:
    context = _context_for_organization(organization_id, identity, session)
    _validate_case_references(
        session, organization_id, request.site_id, request.machine_id, request.primary_folder_id
    )
    definition = (
        get_qa_test_definition(request.qa_definition_key)
        if request.qa_definition_key is not None
        else None
    )
    if request.qa_definition_key is not None and definition is None:
        raise DomainError(
            "QA_DEFINITION_NOT_FOUND",
            "The selected QA test is not in the current catalogue.",
            422,
        )
    request_fingerprint = _case_request_fingerprint(request)
    if request.idempotency_key is not None:
        existing = session.scalar(
            select(QACase).where(
                QACase.organization_id == organization_id,
                QACase.idempotency_key == request.idempotency_key.strip(),
            )
        )
        if existing is not None:
            if existing.idempotency_fingerprint == request_fingerprint:
                return _case_response(existing)
            raise DomainError(
                "QA_CASE_IDEMPOTENCY_CONFLICT",
                "The same request key was already used with different QA case data.",
                409,
            )
    title = request.title.strip()
    if not title:
        raise DomainError("QA_CASE_TITLE_REQUIRED", "QA case title cannot be blank.", 400)
    qa_type = (request.qa_type or (definition.name if definition else "")).strip()
    if not qa_type:
        raise DomainError("QA_TYPE_REQUIRED", "QA type cannot be blank.", 400)
    case = QACase(
        organization_id=organization_id,
        site_id=request.site_id,
        machine_id=request.machine_id,
        primary_folder_id=request.primary_folder_id,
        idempotency_key=request.idempotency_key.strip() if request.idempotency_key else None,
        idempotency_fingerprint=request_fingerprint if request.idempotency_key else None,
        qa_definition_key=definition.key if definition else None,
        qa_type=qa_type,
        qa_cycle=request.qa_cycle,
        performed_at=request.performed_at,
        scheduled_at=request.scheduled_at,
        title=title,
        description=request.description,
        protocol_version_id=request.protocol_version_id,
        status_note=request.status_note,
        created_by_user_identity_id=session.scalar(
            select(UserIdentity.id).where(UserIdentity.supabase_user_id == context.subject)
        ),
    )
    session.add(case)
    session.flush()
    _audit(session, context, "QA_CASE_CREATED", "QACase", case.id, {"title": case.title})
    _commit_or_raise(session)
    return _case_response(case)


@router.get("/qa-cases/{case_id}", response_model=QACaseResponse)
def get_qa_case(
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QACaseResponse:
    context = resolve_session_context(session, identity)
    case = session.scalar(
        select(QACase).where(
            QACase.id == case_id, QACase.organization_id == context.organization_id
        )
    )
    if case is None:
        raise DomainError("QA_CASE_NOT_FOUND", "QA case was not found in this organization.", 404)
    return _case_response(case)


@router.patch("/qa-cases/{case_id}", response_model=QACaseResponse)
def update_qa_case(
    case_id: UUID,
    request: QACasePatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QACaseResponse:
    context = resolve_session_context(session, identity)
    case = session.scalar(
        select(QACase).where(
            QACase.id == case_id, QACase.organization_id == context.organization_id
        )
    )
    if case is None:
        raise DomainError("QA_CASE_NOT_FOUND", "QA case was not found in this organization.", 404)
    changes = request.model_dump(exclude_none=True)
    if not changes:
        raise DomainError("NO_CHANGES", "At least one QA case field is required.", 400)
    if request.primary_folder_id is not None:
        folder = _folder_or_error(session, case.organization_id, request.primary_folder_id)
        if folder.is_archived:
            raise DomainError(
                "FOLDER_ARCHIVED", "A QA case cannot be moved into an archived folder.", 409
            )
        case.primary_folder_id = request.primary_folder_id
    if request.qa_definition_key is not None:
        definition = get_qa_test_definition(request.qa_definition_key)
        if definition is None:
            raise DomainError(
                "QA_DEFINITION_NOT_FOUND",
                "The selected QA test is not in the current catalogue.",
                422,
            )
        case.qa_definition_key = definition.key
        if request.qa_type is None:
            case.qa_type = definition.name
    for field in (
        "qa_definition_key",
        "qa_type",
        "qa_cycle",
        "performed_at",
        "scheduled_at",
        "title",
        "description",
        "protocol_version_id",
        "status_note",
        "case_status",
        "is_archived",
    ):
        value = getattr(request, field)
        if value is not None:
            setattr(case, field, value.strip() if isinstance(value, str) else value)
    _audit(session, context, "QA_CASE_UPDATED", "QACase", case.id, _safe_payload(changes))
    _commit_or_raise(session)
    return _case_response(case)


@router.post("/qa-cases/{case_id}/restore", response_model=QACaseResponse)
def restore_qa_case(
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QACaseResponse:
    """Restore a case from the archive without changing its history."""

    context = resolve_session_context(session, identity)
    case = session.scalar(
        select(QACase).where(
            QACase.id == case_id, QACase.organization_id == context.organization_id
        )
    )
    if case is None:
        raise DomainError("QA_CASE_NOT_FOUND", "QA case was not found in this organization.", 404)
    if not case.is_archived:
        return _case_response(case)
    case.is_archived = False
    _audit(session, context, "QA_CASE_RESTORED", "QACase", case.id, {})
    _commit_or_raise(session)
    return _case_response(case)


@router.delete("/qa-cases/{case_id}", response_model=QACaseResponse)
def archive_qa_case(
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QACaseResponse:
    """Move a case to the archive; the default delete is recoverable."""

    context = resolve_session_context(session, identity)
    case = session.scalar(
        select(QACase).where(
            QACase.id == case_id, QACase.organization_id == context.organization_id
        )
    )
    if case is None:
        raise DomainError("QA_CASE_NOT_FOUND", "QA case was not found in this organization.", 404)
    if not case.is_archived:
        case.is_archived = True
        _audit(session, context, "QA_CASE_ARCHIVED", "QACase", case.id, {})
        _commit_or_raise(session)
    return _case_response(case)


def _case_reference_counts(session: Session, case_id: UUID) -> dict[str, int]:
    """Find durable objects that would become orphaned by a permanent purge."""

    counts: dict[str, int] = {}
    for name, model, column in (
        ("machine_qa_runs", MachineQARun, MachineQARun.qa_case_id),
        ("gamma_analysis_runs", GammaAnalysisRun, GammaAnalysisRun.qa_case_id),
        ("dvh_analysis_runs", DVHAnalysisRun, DVHAnalysisRun.qa_case_id),
        ("trend_points", TrendPoint, TrendPoint.qa_case_id),
        ("artifacts", Artifact, Artifact.qa_case_id),
    ):
        counts[name] = int(
            session.scalar(select(func.count()).select_from(model).where(column == case_id)) or 0
        )
    counts["reports"] = int(
        session.scalar(
            select(func.count())
            .select_from(ReportRevision)
            .where(ReportRevision.source_id == case_id)
        )
        or 0
    )
    return {name: count for name, count in counts.items() if count}


@router.get(
    "/qa-cases/{case_id}/purge-preview",
    response_model=QACasePurgePreviewResponse,
)
def preview_qa_case_purge(
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QACasePurgePreviewResponse:
    """Return a user-facing, read-only eligibility check before permanent purge."""

    context = resolve_session_context(session, identity)
    case = session.scalar(
        select(QACase).where(
            QACase.id == case_id, QACase.organization_id == context.organization_id
        )
    )
    if case is None:
        raise DomainError("QA_CASE_NOT_FOUND", "QA case was not found in this organization.", 404)
    site_name = session.scalar(
        select(Site.name).where(
            Site.id == case.site_id, Site.organization_id == context.organization_id
        )
    ) or "Cơ sở không còn hoạt động"
    machine_name = session.scalar(
        select(Machine.display_name).where(
            Machine.id == case.machine_id, Machine.organization_id == context.organization_id
        )
    ) or "Máy không còn hoạt động"
    references = _case_reference_counts(session, case.id)
    return QACasePurgePreviewResponse(
        case_id=case.id,
        title=case.title,
        site_name=site_name,
        machine_name=machine_name,
        performed_at=case.performed_at,
        is_archived=case.is_archived,
        can_purge=case.is_archived and not references,
        references=[
            QACasePurgeReferenceResponse(source=name, count=count)
            for name, count in references.items()
        ],
    )


@router.post("/qa-cases/{case_id}/purge", response_model=dict[str, object])
def purge_qa_case(
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> dict[str, object]:
    """Permanently remove only an archived, unreferenced case.

    Results, files and reports are immutable and remain the source of truth.
    Therefore a case with any downstream reference is refused rather than
    cascading into silent data loss.
    """

    context = resolve_session_context(session, identity)
    # Keep the reference check and delete in one serialized transaction. On
    # PostgreSQL this row lock also prevents a new FK-linked child from being
    # inserted between the check and the purge.
    case = session.scalar(
        select(QACase).where(
            QACase.id == case_id, QACase.organization_id == context.organization_id
        ).with_for_update()
    )
    if case is None:
        already_purged = session.scalar(
            select(AuditEvent).where(
                AuditEvent.organization_id == context.organization_id,
                AuditEvent.event_type == "QA_CASE_PURGED",
                AuditEvent.entity_type == "QACase",
                AuditEvent.entity_id == case_id,
            )
        )
        if already_purged is not None:
            return {"status": "PURGED", "case_id": case_id}
        raise DomainError("QA_CASE_NOT_FOUND", "QA case was not found in this organization.", 404)
    if not case.is_archived:
        raise DomainError(
            "QA_CASE_PURGE_REQUIRES_ARCHIVE",
            "Only an archived QA case can be permanently removed.",
            409,
        )
    references = _case_reference_counts(session, case.id)
    if references:
        raise DomainError(
            "QA_CASE_REFERENCED",
            "The QA case is still referenced by results, files or reports.",
            409,
            details=[{"source": name, "count": count} for name, count in references.items()],
        )
    _audit(session, context, "QA_CASE_PURGED", "QACase", case.id, {})
    session.delete(case)
    _commit_or_raise(session)
    return {"status": "PURGED", "case_id": case_id}
