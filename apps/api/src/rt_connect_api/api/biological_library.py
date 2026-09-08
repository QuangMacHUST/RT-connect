"""P16 organization-scoped biological knowledge library.

This module manages dose-limit references, treatment protocols, knowledge
notes, and alpha/beta references as independent versioned material.  It is
intentionally separate from QA cases and patient records.  A calculator can
request an explicit use snapshot, but a library entry never silently becomes
a prescription, a QA rule, or a PASS/FAIL decision.
"""

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rt_connect_api.api.biological import (
    _actor_id,
)
from rt_connect_api.api.biological import (
    _context_for_organization as _resolve_organization_context,
)
from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import AuditEvent, BiologicalLibraryEntry
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.biological_library_engine import (
    LIBRARY_USE_SCHEMA_VERSION,
    entry_matches,
    entry_search_text,
    library_snapshot,
    request_fingerprint,
    validate_library_entry,
)
from rt_connect_api.services.session_context import SessionContext

router = APIRouter(
    prefix="/organizations/{organization_id}/biological/library",
    tags=["biological-library"],
)

EntryType = Literal["DOSE_LIMIT", "TREATMENT_PROTOCOL", "KNOWLEDGE", "ALPHA_BETA"]
EntryStatus = Literal["DRAFT", "PUBLISHED", "ARCHIVED"]
SourceType = Literal["USER_DEFINED", "REFERENCE", "INTERNAL", "SITE_APPROVED"]
ReferenceStatus = Literal["UNVERIFIED", "AVAILABLE", "UNAVAILABLE"]
UseTool = Literal[
    "P13_BED_EQD2",
    "P14_PLAN_COMPARISON",
    "P15_REIRRADIATION",
    "P15_FRACTION_COMPENSATION",
    "P17_DVH",
    "KNOWLEDGE_REFERENCE",
]


class LibraryDefinitionFields(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    entry_key: str = Field(min_length=1, max_length=120)
    entry_type: EntryType
    name: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    effective_note: str | None = Field(default=None, max_length=4000)
    disease: str | None = Field(default=None, max_length=240)
    disease_subtype: str | None = Field(default=None, max_length=240)
    anatomy_site: str | None = Field(default=None, max_length=240)
    treatment_intent: str | None = Field(default=None, max_length=160)
    technique: str | None = Field(default=None, max_length=160)
    fractions: int | None = Field(default=None, ge=1)
    tissue_or_oar: str | None = Field(default=None, max_length=240)
    metric_key: str | None = Field(default=None, max_length=80)
    operator: str | None = Field(default=None, max_length=20)
    limit_value: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    volume_cc: float | None = Field(default=None, gt=0)
    metric_parameter: float | None = Field(default=None, gt=0)
    alpha_beta_gy: float | None = Field(default=None, gt=0)
    model_key: str | None = Field(default=None, max_length=120)
    model_version: str | None = Field(default=None, max_length=80)
    applicability: dict[str, object] = Field(default_factory=dict)
    content: dict[str, object] = Field(default_factory=dict)
    source_type: SourceType = "USER_DEFINED"
    source_reference: str | None = Field(default=None, max_length=1000)
    reference_status: ReferenceStatus = "UNVERIFIED"
    source_date: str | None = Field(default=None, max_length=40)
    evidence_level: str | None = Field(default=None, max_length=120)
    citation: dict[str, object] = Field(default_factory=dict)

    @field_validator(
        "entry_key",
        "name",
        "description",
        "effective_note",
        "disease",
        "disease_subtype",
        "anatomy_site",
        "treatment_intent",
        "technique",
        "tissue_or_oar",
        "metric_key",
        "operator",
        "unit",
        "model_key",
        "model_version",
        "source_reference",
        "source_date",
        "evidence_level",
    )
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class LibraryCreateRequest(LibraryDefinitionFields):
    publish: bool = False


class LibraryPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    expected_revision: int = Field(ge=1)
    entry_key: str | None = Field(default=None, min_length=1, max_length=120)
    entry_type: EntryType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    effective_note: str | None = Field(default=None, max_length=4000)
    disease: str | None = Field(default=None, max_length=240)
    disease_subtype: str | None = Field(default=None, max_length=240)
    anatomy_site: str | None = Field(default=None, max_length=240)
    treatment_intent: str | None = Field(default=None, max_length=160)
    technique: str | None = Field(default=None, max_length=160)
    fractions: int | None = Field(default=None, ge=1)
    tissue_or_oar: str | None = Field(default=None, max_length=240)
    metric_key: str | None = Field(default=None, max_length=80)
    operator: str | None = Field(default=None, max_length=20)
    limit_value: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    unit: str | None = Field(default=None, max_length=40)
    volume_cc: float | None = Field(default=None, gt=0)
    metric_parameter: float | None = Field(default=None, gt=0)
    alpha_beta_gy: float | None = Field(default=None, gt=0)
    model_key: str | None = Field(default=None, max_length=120)
    model_version: str | None = Field(default=None, max_length=80)
    applicability: dict[str, object] | None = None
    content: dict[str, object] | None = None
    source_type: SourceType | None = None
    source_reference: str | None = Field(default=None, max_length=1000)
    reference_status: ReferenceStatus | None = None
    source_date: str | None = Field(default=None, max_length=40)
    evidence_level: str | None = Field(default=None, max_length=120)
    citation: dict[str, object] | None = None

    @field_validator(
        "entry_key",
        "name",
        "description",
        "effective_note",
        "disease",
        "disease_subtype",
        "anatomy_site",
        "treatment_intent",
        "technique",
        "tissue_or_oar",
        "metric_key",
        "operator",
        "unit",
        "model_key",
        "model_version",
        "source_reference",
        "source_date",
        "evidence_level",
    )
    @classmethod
    def _trim_patch_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class LibraryCloneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_key: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=240)
    publish: bool = False

    @field_validator("entry_key", "name")
    @classmethod
    def _trim_clone_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class LibraryTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)


class LibraryUseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    target_tool: UseTool
    override: dict[str, object] = Field(default_factory=dict)


class LibraryImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, object]] = Field(min_length=1, max_length=500)
    commit_valid: bool = False


class LibraryValidationIssue(BaseModel):
    code: str
    field: str | None = None
    message: str


class LibraryValidationResponse(BaseModel):
    valid: bool
    errors: list[LibraryValidationIssue]
    warnings: list[LibraryValidationIssue]
    normalized_entry: dict[str, object] | None = None
    content_sha256: str | None = None


class LibraryEntryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    entry_type: EntryType
    entry_key: str
    name: str
    version_number: int
    status: EntryStatus
    revision: int
    description: str | None
    effective_note: str | None
    disease: str | None
    disease_subtype: str | None
    anatomy_site: str | None
    treatment_intent: str | None
    technique: str | None
    fractions: int | None
    tissue_or_oar: str | None
    metric_key: str | None
    operator: str | None
    limit_value: float | None
    lower_limit: float | None
    upper_limit: float | None
    unit: str | None
    volume_cc: float | None
    metric_parameter: float | None
    alpha_beta_gy: float | None
    model_key: str | None
    model_version: str | None
    applicability: dict[str, object]
    content: dict[str, object]
    source_type: SourceType
    source_reference: str | None
    reference_status: ReferenceStatus
    source_date: str | None
    evidence_level: str | None
    citation: dict[str, object]
    content_sha256: str
    source_entry_id: UUID | None
    created_by_user_identity_id: UUID | None
    created_at: datetime
    updated_at: datetime


class LibraryCollectionResponse(BaseModel):
    items: list[LibraryEntryResponse]
    total: int
    offset: int
    limit: int
    include_archived: bool


class LibraryCompareResponse(BaseModel):
    left: LibraryEntryResponse
    right: LibraryEntryResponse
    same_family: bool
    metadata_diffs: list[dict[str, object]]
    content_diffs: list[dict[str, object]]


class LibraryUseResponse(BaseModel):
    schema_version: str
    target_tool: UseTool
    entry: LibraryEntryResponse
    source_snapshot: dict[str, object]
    effective_values: dict[str, object]
    override: dict[str, object]
    override_label: str | None
    snapshot_sha256: str
    warnings: list[LibraryValidationIssue]


class LibraryImportRowResponse(BaseModel):
    row_number: int
    valid: bool
    errors: list[LibraryValidationIssue]
    warnings: list[LibraryValidationIssue]
    entry_id: UUID | None = None


class LibraryImportResponse(BaseModel):
    dry_run: bool
    committed_count: int
    rejected_count: int
    rows: list[LibraryImportRowResponse]
    entries: list[LibraryEntryResponse]


def _issue_response(item: dict[str, object]) -> LibraryValidationIssue:
    raw_code = item.get("code")
    raw_field = item.get("field")
    raw_message = item.get("message")
    return LibraryValidationIssue(
        code=raw_code if isinstance(raw_code, str) else "KNOWLEDGE_CONTENT_INVALID",
        field=raw_field if isinstance(raw_field, str) else None,
        message=raw_message if isinstance(raw_message, str) else "The value is invalid.",
    )


def _context_for_organization(
    organization_id: UUID, identity: AuthenticatedIdentity, session: Session
) -> SessionContext:
    # Keep one explicit scope check at the beginning of every route.  The
    # biological module owns the established implementation used by P12-P15.
    return _resolve_organization_context(organization_id, identity, session)


def _actor(session: Session, context: SessionContext) -> UUID | None:
    return _actor_id(session, context)


def _audit(
    session: Session,
    context: SessionContext,
    event_type: str,
    entry_id: UUID,
    payload: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor(session, context),
            event_type=event_type,
            entity_type="BiologicalLibraryEntry",
            entity_id=entry_id,
            payload=payload,
        )
    )


def _commit_or_raise(
    session: Session, *, conflict_code: str = "KNOWLEDGE_VERSION_CONFLICT"
) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            conflict_code,
            "The biological library version conflicts with another version or concurrent edit.",
            409,
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DomainError(
            "KNOWLEDGE_PERSISTENCE_FAILED",
            "The biological library change could not be persisted.",
            503,
        ) from exc


def _entry_or_404(
    session: Session, organization_id: UUID, entry_id: UUID
) -> BiologicalLibraryEntry:
    entry = session.scalar(
        select(BiologicalLibraryEntry).where(
            BiologicalLibraryEntry.id == entry_id,
            BiologicalLibraryEntry.organization_id == organization_id,
        )
    )
    if entry is None:
        raise DomainError(
            "KNOWLEDGE_ENTRY_NOT_FOUND",
            "The biological library entry was not found in the current organization.",
            404,
        )
    return entry


def _entry_dict(entry: BiologicalLibraryEntry) -> dict[str, object]:
    return {
        "id": str(entry.id),
        "organization_id": str(entry.organization_id),
        "entry_type": entry.entry_type,
        "entry_key": entry.entry_key,
        "name": entry.name,
        "version_number": entry.version_number,
        "status": entry.status,
        "revision": entry.revision,
        "description": entry.description,
        "effective_note": entry.effective_note,
        "disease": entry.disease,
        "disease_subtype": entry.disease_subtype,
        "anatomy_site": entry.anatomy_site,
        "treatment_intent": entry.treatment_intent,
        "technique": entry.technique,
        "fractions": entry.fractions,
        "tissue_or_oar": entry.tissue_or_oar,
        "metric_key": entry.metric_key,
        "operator": entry.operator,
        "limit_value": entry.limit_value,
        "lower_limit": entry.lower_limit,
        "upper_limit": entry.upper_limit,
        "unit": entry.unit,
        "volume_cc": entry.volume_cc,
        "metric_parameter": entry.metric_parameter,
        "alpha_beta_gy": entry.alpha_beta_gy,
        "model_key": entry.model_key,
        "model_version": entry.model_version,
        "applicability": entry.applicability,
        "content": entry.content,
        "source_type": entry.source_type,
        "source_reference": entry.source_reference,
        "reference_status": entry.reference_status,
        "source_date": entry.source_date,
        "evidence_level": entry.evidence_level,
        "citation": entry.citation,
        "entry_sha256": entry.content_sha256,
    }


def _entry_response(entry: BiologicalLibraryEntry) -> LibraryEntryResponse:
    return LibraryEntryResponse(
        id=entry.id,
        organization_id=entry.organization_id,
        entry_type=entry.entry_type,  # type: ignore[arg-type]
        entry_key=entry.entry_key,
        name=entry.name,
        version_number=entry.version_number,
        status=entry.status,  # type: ignore[arg-type]
        revision=entry.revision,
        description=entry.description,
        effective_note=entry.effective_note,
        disease=entry.disease,
        disease_subtype=entry.disease_subtype,
        anatomy_site=entry.anatomy_site,
        treatment_intent=entry.treatment_intent,
        technique=entry.technique,
        fractions=entry.fractions,
        tissue_or_oar=entry.tissue_or_oar,
        metric_key=entry.metric_key,
        operator=entry.operator,
        limit_value=entry.limit_value,
        lower_limit=entry.lower_limit,
        upper_limit=entry.upper_limit,
        unit=entry.unit,
        volume_cc=entry.volume_cc,
        metric_parameter=entry.metric_parameter,
        alpha_beta_gy=entry.alpha_beta_gy,
        model_key=entry.model_key,
        model_version=entry.model_version,
        applicability=entry.applicability,
        content=entry.content,
        source_type=entry.source_type,  # type: ignore[arg-type]
        source_reference=entry.source_reference,
        reference_status=entry.reference_status,  # type: ignore[arg-type]
        source_date=entry.source_date,
        evidence_level=entry.evidence_level,
        citation=entry.citation,
        content_sha256=entry.content_sha256,
        source_entry_id=entry.source_entry_id,
        created_by_user_identity_id=entry.created_by_user_identity_id,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def _definition_from_entry(entry: BiologicalLibraryEntry) -> LibraryDefinitionFields:
    data = _entry_dict(entry)
    data.pop("id", None)
    data.pop("organization_id", None)
    data.pop("version_number", None)
    data.pop("status", None)
    data.pop("revision", None)
    data.pop("entry_sha256", None)
    return LibraryDefinitionFields.model_validate(data)


def _validate_definition(
    request: LibraryDefinitionFields,
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    raw = request.model_dump(mode="json")
    return validate_library_entry(raw)


def _raise_if_invalid(errors: list[dict[str, object]]) -> None:
    if not errors:
        return
    first = _issue_response(errors[0])
    raise DomainError(
        first.code,
        "The biological library entry is invalid.",
        422,
        [
            {"field": item.field, "message": item.message}
            for item in [_issue_response(error) for error in errors]
        ],
    )


def _next_version(session: Session, organization_id: UUID, entry_type: str, entry_key: str) -> int:
    latest = session.scalar(
        select(func.max(BiologicalLibraryEntry.version_number)).where(
            BiologicalLibraryEntry.organization_id == organization_id,
            BiologicalLibraryEntry.entry_type == entry_type,
            BiologicalLibraryEntry.entry_key == entry_key,
        )
    )
    return int(latest or 0) + 1


def _new_entry(
    session: Session,
    context: SessionContext,
    normalised: dict[str, object],
    *,
    source_entry_id: UUID | None = None,
    publish: bool = False,
) -> BiologicalLibraryEntry:
    entry_type = str(normalised["entry_type"])
    entry_key = str(normalised["entry_key"])
    entry = BiologicalLibraryEntry(
        organization_id=context.organization_id,
        entry_type=entry_type,
        entry_key=entry_key,
        name=str(normalised["name"]),
        version_number=_next_version(session, context.organization_id, entry_type, entry_key),
        status="PUBLISHED" if publish else "DRAFT",
        revision=1,
        description=normalised["description"],
        effective_note=normalised["effective_note"],
        disease=normalised["disease"],
        disease_subtype=normalised["disease_subtype"],
        anatomy_site=normalised["anatomy_site"],
        treatment_intent=normalised["treatment_intent"],
        technique=normalised["technique"],
        fractions=normalised["fractions"],
        tissue_or_oar=normalised["tissue_or_oar"],
        metric_key=normalised["metric_key"],
        operator=normalised["operator"],
        limit_value=normalised["limit_value"],
        lower_limit=normalised["lower_limit"],
        upper_limit=normalised["upper_limit"],
        unit=normalised["unit"],
        volume_cc=normalised["volume_cc"],
        metric_parameter=normalised["metric_parameter"],
        alpha_beta_gy=normalised["alpha_beta_gy"],
        model_key=normalised["model_key"],
        model_version=normalised["model_version"],
        applicability=normalised["applicability"],
        content=normalised["content"],
        source_type=str(normalised["source_type"]),
        source_reference=normalised["source_reference"],
        reference_status=str(normalised["reference_status"]),
        source_date=normalised["source_date"],
        evidence_level=normalised["evidence_level"],
        citation=normalised["citation"],
        content_sha256=request_fingerprint(normalised),
        source_entry_id=source_entry_id,
        created_by_user_identity_id=_actor(session, context),
    )
    session.add(entry)
    session.flush()
    return entry


def _warnings_for(normalised: dict[str, object]) -> list[LibraryValidationIssue]:
    _, _, warnings = validate_library_entry(normalised)
    return [_issue_response(item) for item in warnings]


def _validate_request(
    request: LibraryDefinitionFields,
) -> tuple[dict[str, object], list[LibraryValidationIssue], list[LibraryValidationIssue]]:
    normalised, errors, warnings = _validate_definition(request)
    return (
        normalised,
        [_issue_response(item) for item in errors],
        [_issue_response(item) for item in warnings],
    )


def _create_and_audit(
    session: Session,
    context: SessionContext,
    normalised: dict[str, object],
    *,
    source_entry_id: UUID | None = None,
    publish: bool = False,
    event_type: str = "BIOLOGICAL_LIBRARY_CREATED",
) -> BiologicalLibraryEntry:
    entry = _new_entry(
        session,
        context,
        normalised,
        source_entry_id=source_entry_id,
        publish=publish,
    )
    _audit(
        session,
        context,
        event_type,
        entry.id,
        {
            "entry_type": entry.entry_type,
            "entry_key": entry.entry_key,
            "version_number": entry.version_number,
            "status": entry.status,
            "source_entry_id": str(source_entry_id) if source_entry_id else None,
        },
    )
    return entry


def _patch_definition(
    entry: BiologicalLibraryEntry, request: LibraryPatchRequest
) -> LibraryDefinitionFields:
    current = _definition_from_entry(entry).model_dump(mode="json")
    updates = request.model_dump(mode="json", exclude_unset=True)
    updates.pop("expected_revision", None)
    current.update(updates)
    return LibraryDefinitionFields.model_validate(current)


@router.post("/validate", response_model=LibraryValidationResponse)
def validate_library_entry_request(
    request: LibraryDefinitionFields,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryValidationResponse:
    _context_for_organization(organization_id, identity, session)
    normalised, errors, warnings = _validate_request(request)
    return LibraryValidationResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        normalized_entry=normalised if not errors else None,
        content_sha256=request_fingerprint(normalised) if not errors else None,
    )


def _import_row(
    row: dict[str, object], row_number: int, seen: set[tuple[str, str]]
) -> tuple[LibraryImportRowResponse, dict[str, object] | None]:
    try:
        request = LibraryDefinitionFields.model_validate(row)
    except ValidationError as exc:
        errors = [
            LibraryValidationIssue(
                code="REQUEST_VALIDATION_FAILED",
                field=".".join(str(part) for part in error["loc"]),
                message=str(error["msg"]),
            )
            for error in exc.errors()
        ]
        return LibraryImportRowResponse(
            row_number=row_number, valid=False, errors=errors, warnings=[]
        ), None
    normalised, errors, warnings = _validate_request(request)
    family = (str(normalised.get("entry_type", "")), str(normalised.get("entry_key", "")))
    if not errors and family in seen:
        errors.append(
            LibraryValidationIssue(
                code="KNOWLEDGE_IMPORT_INVALID",
                field="entry_key",
                message="The same entry family appears more than once in this import batch.",
            )
        )
    if not errors:
        seen.add(family)
    return (
        LibraryImportRowResponse(
            row_number=row_number,
            valid=not errors,
            errors=errors,
            warnings=warnings,
        ),
        normalised if not errors else None,
    )


def _import_rows(
    session: Session,
    context: SessionContext,
    request: LibraryImportRequest,
) -> LibraryImportResponse:
    rows: list[LibraryImportRowResponse] = []
    prepared: list[tuple[int, dict[str, object]]] = []
    seen: set[tuple[str, str]] = set()
    for row_number, raw_row in enumerate(request.rows, start=1):
        row_response, normalised = _import_row(raw_row, row_number, seen)
        rows.append(row_response)
        if normalised is not None:
            prepared.append((row_number, normalised))
    if not request.commit_valid:
        return LibraryImportResponse(
            dry_run=True,
            committed_count=0,
            rejected_count=len(rows) - len(prepared),
            rows=rows,
            entries=[],
        )

    entries: list[BiologicalLibraryEntry] = []
    by_row: dict[int, UUID] = {}
    for row_number, normalised in prepared:
        entry = _create_and_audit(
            session,
            context,
            normalised,
            event_type="BIOLOGICAL_LIBRARY_IMPORTED",
        )
        entries.append(entry)
        by_row[row_number] = entry.id
    _commit_or_raise(session)
    for row_result in rows:
        row_result.entry_id = by_row.get(row_result.row_number)
    return LibraryImportResponse(
        dry_run=False,
        committed_count=len(entries),
        rejected_count=len(rows) - len(prepared),
        rows=rows,
        entries=[_entry_response(entry) for entry in entries],
    )


@router.post("/import/validate", response_model=LibraryImportResponse)
def validate_library_import(
    request: LibraryImportRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryImportResponse:
    context = _context_for_organization(organization_id, identity, session)
    request = request.model_copy(update={"commit_valid": False})
    return _import_rows(session, context, request)


@router.post("/import", response_model=LibraryImportResponse)
def import_library(
    request: LibraryImportRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryImportResponse:
    context = _context_for_organization(organization_id, identity, session)
    return _import_rows(session, context, request)


@router.get("", response_model=LibraryCollectionResponse)
def list_library_entries(
    organization_id: UUID,
    q: str | None = Query(default=None, max_length=240),
    entry_type: EntryType | None = Query(default=None),
    entry_status: EntryStatus | None = Query(default=None, alias="status"),
    disease: str | None = Query(default=None, max_length=240),
    anatomy_site: str | None = Query(default=None, max_length=240),
    technique: str | None = Query(default=None, max_length=160),
    tissue_or_oar: str | None = Query(default=None, max_length=240),
    metric_key: str | None = Query(default=None, max_length=80),
    fractions: int | None = Query(default=None, ge=1),
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryCollectionResponse:
    context = _context_for_organization(organization_id, identity, session)
    conditions = [BiologicalLibraryEntry.organization_id == context.organization_id]
    if entry_type:
        conditions.append(BiologicalLibraryEntry.entry_type == entry_type)
    if entry_status:
        conditions.append(BiologicalLibraryEntry.status == entry_status)
    elif not include_archived:
        conditions.append(BiologicalLibraryEntry.status != "ARCHIVED")
    candidates = list(
        session.scalars(
            select(BiologicalLibraryEntry)
            .where(*conditions)
            .order_by(
                BiologicalLibraryEntry.entry_key,
                BiologicalLibraryEntry.version_number.desc(),
            )
        )
    )
    search = q.strip().casefold() if q else ""
    filtered: list[BiologicalLibraryEntry] = []
    for entry in candidates:
        item = _entry_dict(entry)
        if search and search not in entry_search_text(item):
            continue
        if not entry_matches(
            item,
            disease=disease,
            anatomy_site=anatomy_site,
            technique=technique,
            tissue_or_oar=tissue_or_oar,
            metric_key=metric_key,
            fractions=fractions,
        ):
            continue
        filtered.append(entry)
    total = len(filtered)
    return LibraryCollectionResponse(
        items=[_entry_response(entry) for entry in filtered[offset : offset + limit]],
        total=total,
        offset=offset,
        limit=limit,
        include_archived=include_archived or entry_status == "ARCHIVED",
    )


@router.post("", response_model=LibraryEntryResponse, status_code=status.HTTP_201_CREATED)
def create_library_entry(
    request: LibraryCreateRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryEntryResponse:
    context = _context_for_organization(organization_id, identity, session)
    normalised, errors, _ = _validate_request(request)
    _raise_if_invalid([item.model_dump() for item in errors])
    entry = _create_and_audit(session, context, normalised, publish=request.publish)
    _commit_or_raise(session)
    session.refresh(entry)
    return _entry_response(entry)


@router.get("/{entry_id}", response_model=LibraryEntryResponse)
def get_library_entry(
    entry_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryEntryResponse:
    _context_for_organization(organization_id, identity, session)
    return _entry_response(_entry_or_404(session, organization_id, entry_id))


@router.get("/{entry_id}/revisions", response_model=list[LibraryEntryResponse])
def list_library_revisions(
    entry_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> list[LibraryEntryResponse]:
    _context_for_organization(organization_id, identity, session)
    entry = _entry_or_404(session, organization_id, entry_id)
    entries = session.scalars(
        select(BiologicalLibraryEntry)
        .where(
            BiologicalLibraryEntry.organization_id == organization_id,
            BiologicalLibraryEntry.entry_type == entry.entry_type,
            BiologicalLibraryEntry.entry_key == entry.entry_key,
        )
        .order_by(BiologicalLibraryEntry.version_number.desc())
    ).all()
    return [_entry_response(item) for item in entries]


@router.patch("/{entry_id}", response_model=LibraryEntryResponse)
def update_library_entry(
    request: LibraryPatchRequest,
    entry_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryEntryResponse:
    context = _context_for_organization(organization_id, identity, session)
    entry = _entry_or_404(session, organization_id, entry_id)
    if entry.revision != request.expected_revision:
        raise DomainError(
            "KNOWLEDGE_REVISION_CONFLICT",
            "The library entry changed since it was loaded.",
            409,
            [{"field": "expected_revision", "message": f"Current revision is {entry.revision}."}],
        )
    if entry.status != "DRAFT":
        raise DomainError(
            "KNOWLEDGE_VERSION_IMMUTABLE",
            "Only a DRAFT entry can be edited; clone a published entry to create a new version.",
            409,
        )
    definition = _patch_definition(entry, request)
    normalised, errors, _ = _validate_request(definition)
    _raise_if_invalid([item.model_dump() for item in errors])
    for field in (
        "entry_key",
        "entry_type",
        "name",
        "description",
        "effective_note",
        "disease",
        "disease_subtype",
        "anatomy_site",
        "treatment_intent",
        "technique",
        "fractions",
        "tissue_or_oar",
        "metric_key",
        "operator",
        "limit_value",
        "lower_limit",
        "upper_limit",
        "unit",
        "volume_cc",
        "metric_parameter",
        "alpha_beta_gy",
        "model_key",
        "model_version",
        "applicability",
        "content",
        "source_type",
        "source_reference",
        "reference_status",
        "source_date",
        "evidence_level",
        "citation",
    ):
        setattr(entry, field, normalised[field])
    entry.revision += 1
    entry.content_sha256 = request_fingerprint(normalised)
    _audit(
        session, context, "BIOLOGICAL_LIBRARY_DRAFT_UPDATED", entry.id, {"revision": entry.revision}
    )
    _commit_or_raise(session)
    session.refresh(entry)
    return _entry_response(entry)


@router.post(
    "/{entry_id}/clone", response_model=LibraryEntryResponse, status_code=status.HTTP_201_CREATED
)
def clone_library_entry(
    request: LibraryCloneRequest,
    entry_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryEntryResponse:
    context = _context_for_organization(organization_id, identity, session)
    source = _entry_or_404(session, organization_id, entry_id)
    definition = _definition_from_entry(source)
    if request.entry_key is not None:
        definition.entry_key = request.entry_key
    if request.name is not None:
        definition.name = request.name
    normalised, errors, _ = _validate_request(definition)
    _raise_if_invalid([item.model_dump() for item in errors])
    clone = _create_and_audit(
        session,
        context,
        normalised,
        source_entry_id=source.id,
        publish=request.publish,
        event_type="BIOLOGICAL_LIBRARY_CLONED",
    )
    _commit_or_raise(session)
    session.refresh(clone)
    return _entry_response(clone)


@router.post("/{entry_id}/publish", response_model=LibraryEntryResponse)
def publish_library_entry(
    request: LibraryTransitionRequest,
    entry_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryEntryResponse:
    context = _context_for_organization(organization_id, identity, session)
    entry = _entry_or_404(session, organization_id, entry_id)
    if entry.revision != request.expected_revision:
        raise DomainError(
            "KNOWLEDGE_REVISION_CONFLICT",
            "The library entry changed since it was loaded.",
            409,
        )
    if entry.status == "ARCHIVED":
        raise DomainError("KNOWLEDGE_NOT_AVAILABLE", "An archived entry cannot be published.", 409)
    if entry.status == "PUBLISHED":
        return _entry_response(entry)
    definition = _definition_from_entry(entry)
    normalised, errors, _ = _validate_request(definition)
    _raise_if_invalid([item.model_dump() for item in errors])
    entry.status = "PUBLISHED"
    entry.revision += 1
    entry.content_sha256 = request_fingerprint(normalised)
    _audit(session, context, "BIOLOGICAL_LIBRARY_PUBLISHED", entry.id, {"revision": entry.revision})
    _commit_or_raise(session)
    session.refresh(entry)
    return _entry_response(entry)


@router.post("/{entry_id}/archive", response_model=LibraryEntryResponse)
def archive_library_entry(
    request: LibraryTransitionRequest,
    entry_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> LibraryEntryResponse:
    context = _context_for_organization(organization_id, identity, session)
    entry = _entry_or_404(session, organization_id, entry_id)
    if entry.revision != request.expected_revision:
        raise DomainError(
            "KNOWLEDGE_REVISION_CONFLICT", "The library entry changed since it was loaded.", 409
        )
    if entry.status == "ARCHIVED":
        return _entry_response(entry)
    entry.status = "ARCHIVED"
    entry.revision += 1
    _audit(session, context, "BIOLOGICAL_LIBRARY_ARCHIVED", entry.id, {"revision": entry.revision})
    _commit_or_raise(session)
    session.refresh(entry)
    return _entry_response(entry)


@router.get("/{entry_id}/compare", response_model=LibraryCompareResponse)
def compare_library_entries(
    entry_id: UUID,
    other_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> LibraryCompareResponse:
    _context_for_organization(organization_id, identity, session)
    left = _entry_or_404(session, organization_id, entry_id)
    right = _entry_or_404(session, organization_id, other_id)
    left_item = _entry_response(left)
    right_item = _entry_response(right)
    metadata_fields = (
        "entry_type",
        "entry_key",
        "name",
        "version_number",
        "status",
        "revision",
        "description",
        "effective_note",
        "disease",
        "disease_subtype",
        "anatomy_site",
        "treatment_intent",
        "technique",
        "fractions",
        "tissue_or_oar",
        "metric_key",
        "operator",
        "limit_value",
        "lower_limit",
        "upper_limit",
        "unit",
        "volume_cc",
        "metric_parameter",
        "alpha_beta_gy",
        "model_key",
        "model_version",
        "applicability",
        "source_type",
        "source_reference",
        "reference_status",
        "source_date",
        "evidence_level",
        "source_entry_id",
    )
    metadata_diffs = [
        {"field": field, "left": getattr(left_item, field), "right": getattr(right_item, field)}
        for field in metadata_fields
        if getattr(left_item, field) != getattr(right_item, field)
    ]
    content_diffs = [
        {"field": field, "left": getattr(left_item, field), "right": getattr(right_item, field)}
        for field in ("content", "citation", "content_sha256")
        if getattr(left_item, field) != getattr(right_item, field)
    ]
    return LibraryCompareResponse(
        left=left_item,
        right=right_item,
        same_family=left.entry_type == right.entry_type and left.entry_key == right.entry_key,
        metadata_diffs=metadata_diffs,
        content_diffs=content_diffs,
    )


_OVERRIDE_FIELDS = frozenset(
    {
        "limit_value",
        "lower_limit",
        "upper_limit",
        "unit",
        "alpha_beta_gy",
        "fractions",
        "metric_parameter",
    }
)


@router.post("/{entry_id}/use", response_model=LibraryUseResponse)
def use_library_entry(
    request: LibraryUseRequest,
    entry_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> LibraryUseResponse:
    _context_for_organization(organization_id, identity, session)
    entry = _entry_or_404(session, organization_id, entry_id)
    if entry.status == "ARCHIVED":
        raise DomainError(
            "KNOWLEDGE_NOT_AVAILABLE",
            "An archived library entry cannot be used for a new calculation.",
            409,
        )
    invalid_fields = sorted(set(request.override) - _OVERRIDE_FIELDS)
    if invalid_fields:
        raise DomainError(
            "KNOWLEDGE_CONTENT_INVALID",
            "Only explicit calculator override fields are supported.",
            422,
            [
                {"field": f"override.{field}", "message": "Override field is not supported."}
                for field in invalid_fields
            ],
        )
    try:
        json.dumps(request.override, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise DomainError(
            "KNOWLEDGE_CONTENT_INVALID", "Override must be finite JSON data.", 422
        ) from exc
    source = library_snapshot(_entry_dict(entry))
    effective: dict[str, object] = {}
    for field in _OVERRIDE_FIELDS:
        if field in request.override:
            effective[field] = request.override[field]
        elif field in source:
            effective[field] = source[field]
    warnings: list[LibraryValidationIssue] = []
    if entry.status == "DRAFT":
        warnings.append(
            LibraryValidationIssue(
                code="KNOWLEDGE_DRAFT_SELECTED",
                field="status",
                message="This is a draft reference; review it before using it in a calculation.",
            )
        )
    if entry.entry_type == "DOSE_LIMIT" and request.target_tool != "P17_DVH":
        warnings.append(
            LibraryValidationIssue(
                code="DOSE_LIMIT_NOT_APPLICABLE",
                field="target_tool",
                message="A dose-limit entry is reference material and is not automatically "
                "a rule for this tool.",
            )
        )
    binding: dict[str, object] = {
        "schema_version": LIBRARY_USE_SCHEMA_VERSION,
        "target_tool": request.target_tool,
        "source_snapshot": source,
        "effective_values": effective,
        "override": request.override,
        "override_label": "USER_OVERRIDE" if request.override else None,
    }
    return LibraryUseResponse(
        schema_version=LIBRARY_USE_SCHEMA_VERSION,
        target_tool=request.target_tool,
        entry=_entry_response(entry),
        source_snapshot=source,
        effective_values=effective,
        override=request.override,
        override_label="USER_OVERRIDE" if request.override else None,
        snapshot_sha256=request_fingerprint(binding),
        warnings=warnings,
    )


@router.get("/{entry_id}/export")
def export_library_entry(
    entry_id: UUID,
    organization_id: UUID,
    export_format: Literal["JSON", "CSV"] = Query(default="JSON"),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> Response:
    _context_for_organization(organization_id, identity, session)
    entry = _entry_or_404(session, organization_id, entry_id)
    payload = _entry_response(entry).model_dump(mode="json")
    if export_format == "JSON":
        return Response(
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="rt-connect-library-{entry.id}.json"'
            },
        )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(payload))
    writer.writeheader()
    writer.writerow(
        {
            key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
            for key, value in payload.items()
        }
    )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="rt-connect-library-{entry.id}.csv"'
        },
    )
