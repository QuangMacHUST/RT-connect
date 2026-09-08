"""P12 independent biological scenarios and calculation-history contracts."""

from __future__ import annotations

import json
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    BiologicalCalculationRun,
    BiologicalScenario,
    BiologicalScenarioRevision,
    ExportJob,
    ReportRevision,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(prefix="/organizations/{organization_id}/biological", tags=["biological"])

SourceType = Literal["USER_DEFINED", "REFERENCE", "INTERNAL", "SITE_APPROVED"]
ScenarioStatus = Literal["DRAFT", "SAVED", "ARCHIVED"]

_SOURCE_TYPES = frozenset({"USER_DEFINED", "REFERENCE", "INTERNAL", "SITE_APPROVED"})
_SCENARIO_STATUSES = frozenset({"DRAFT", "SAVED", "ARCHIVED"})
_SCENARIO_KEY_PATTERN = r"^[A-Z][A-Z0-9_.-]{0,119}$"


class BiologicalScenarioCreateRequest(BaseModel):
    scenario_key: str = Field(min_length=1, max_length=120, pattern=_SCENARIO_KEY_PATTERN)
    name: str = Field(min_length=1, max_length=240)
    scenario_type: str = Field(min_length=1, max_length=80)
    tissue_context: str = Field(min_length=1, max_length=240)
    clinical_context: str | None = Field(default=None, max_length=4000)
    source_type: SourceType = "USER_DEFINED"
    source_reference: str | None = Field(default=None, max_length=1000)
    assumptions: dict[str, object] = Field(default_factory=dict)

    @field_validator("name", "scenario_type", "tissue_context")
    @classmethod
    def _required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value

    @field_validator("clinical_context", "source_reference")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BiologicalScenarioPatchRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=240)
    scenario_type: str | None = Field(default=None, min_length=1, max_length=80)
    tissue_context: str | None = Field(default=None, min_length=1, max_length=240)
    clinical_context: str | None = Field(default=None, max_length=4000)
    source_type: SourceType | None = None
    source_reference: str | None = Field(default=None, max_length=1000)
    assumptions: dict[str, object] | None = None

    @field_validator("name", "scenario_type", "tissue_context")
    @classmethod
    def _required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value

    @field_validator("clinical_context", "source_reference")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BiologicalScenarioTransitionRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class BiologicalScenarioCloneRequest(BaseModel):
    scenario_key: str | None = Field(
        default=None, min_length=1, max_length=120, pattern=_SCENARIO_KEY_PATTERN
    )
    name: str | None = Field(default=None, min_length=1, max_length=240)

    @field_validator("scenario_key")
    @classmethod
    def _scenario_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not value:
            raise ValueError("scenario_key cannot be blank")
        return value

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class BiologicalScenarioRevisionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    scenario_id: UUID
    revision_number: int
    status: str
    snapshot: dict[str, object]
    created_by_user_identity_id: UUID | None
    created_at: str


class BiologicalScenarioResponse(BaseModel):
    id: UUID
    organization_id: UUID
    scenario_key: str
    name: str
    scenario_type: str
    tissue_context: str
    clinical_context: str | None
    source_type: str
    source_reference: str | None
    assumptions: dict[str, object]
    status: str
    revision: int
    source_scenario_revision_id: UUID | None
    created_by_user_identity_id: UUID | None
    created_at: str
    updated_at: str
    latest_snapshot: dict[str, object] | None = None


class BiologicalScenarioCollectionResponse(BaseModel):
    items: list[BiologicalScenarioResponse]
    total: int
    offset: int
    limit: int
    include_archived: bool


class BiologicalCalculationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    scenario_id: UUID
    scenario_revision_id: UUID
    calculation_type: str
    idempotency_key: str | None
    model_key: str
    model_version: str
    status: str
    input_snapshot: dict[str, object]
    result_snapshot: dict[str, object]
    warning_snapshot: list[dict[str, object]]
    error_snapshot: list[dict[str, object]]
    created_by_user_identity_id: UUID | None
    created_at: str
    updated_at: str


class BiologicalCalculationCollectionResponse(BaseModel):
    items: list[BiologicalCalculationResponse]
    total: int
    offset: int
    limit: int


class BiologicalSummaryResponse(BaseModel):
    organization_id: UUID
    total_scenarios: int
    draft_scenarios: int
    saved_scenarios: int
    archived_scenarios: int
    completed_calculations: int
    exported_reports: int


class BiologicalToolResponse(BaseModel):
    tool_key: str
    label: str
    route: str
    phase: str
    status: str
    available: bool
    description: str


class BiologicalValidationResponse(BaseModel):
    valid: bool
    errors: list[dict[str, str | None]]
    warnings: list[dict[str, str | None]]


def _context_for_organization(
    organization_id: UUID,
    identity: AuthenticatedIdentity,
    session: Session,
) -> SessionContext:
    context = resolve_session_context(session, identity)
    if context.organization_id != organization_id:
        raise DomainError(
            "ORGANIZATION_SCOPE_MISMATCH",
            "The requested organization is outside the authenticated membership scope.",
            403,
        )
    return context


def _actor_id(session: Session, context: SessionContext) -> UUID | None:
    actor = session.scalar(
        select(UserIdentity).where(UserIdentity.supabase_user_id == context.subject)
    )
    return actor.id if actor else None


def _audit(
    session: Session,
    context: SessionContext,
    event_type: str,
    entity_id: UUID,
    payload: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor_id(session, context),
            event_type=event_type,
            entity_type="BiologicalScenario",
            entity_id=entity_id,
            payload=payload,
        )
    )


def _commit_or_raise(
    session: Session,
    integrity_code: str,
    message: str,
    *,
    persistence_code: str = "SCENARIO_PERSISTENCE_FAILED",
    persistence_message: str = "The biological scenario could not be persisted.",
) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(integrity_code, message, 409) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DomainError(
            persistence_code,
            persistence_message,
            503,
        ) from exc


def _validate_json_object(value: dict[str, object], field: str = "assumptions") -> None:
    try:
        json.dumps(value, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise DomainError(
            "BIOLOGICAL_CONTEXT_INVALID",
            "Biological context must be finite, JSON-serializable data.",
            422,
            [{"field": field, "message": "The object contains a non-finite or unsupported value."}],
        ) from exc


def _validate_source(source_type: str, source_reference: str | None) -> None:
    if source_type not in _SOURCE_TYPES:
        raise DomainError(
            "BIOLOGICAL_CONTEXT_INVALID",
            "The biological source type is not supported.",
            422,
            [{"field": "source_type", "message": "Choose a supported source type."}],
        )
    if source_type == "REFERENCE" and not source_reference:
        raise DomainError(
            "BIOLOGICAL_CONTEXT_INVALID",
            "A reference source requires a citation or reference URL.",
            422,
            [{"field": "source_reference", "message": "Reference is required."}],
        )


def _validate_create(request: BiologicalScenarioCreateRequest) -> None:
    _validate_json_object(request.assumptions)
    _validate_source(request.source_type, request.source_reference)


def _snapshot(
    scenario: BiologicalScenario, *, status_override: str | None = None
) -> dict[str, object]:
    return {
        "schema_version": "biological-scenario.v1",
        "scenario_id": str(scenario.id),
        "scenario_key": scenario.scenario_key,
        "name": scenario.name,
        "scenario_type": scenario.scenario_type,
        "tissue_context": scenario.tissue_context,
        "clinical_context": scenario.clinical_context,
        "source_type": scenario.source_type,
        "source_reference": scenario.source_reference,
        "assumptions": scenario.assumptions,
        "status": status_override or scenario.status,
        "revision": scenario.revision,
        "source_scenario_revision_id": (
            str(scenario.source_scenario_revision_id)
            if scenario.source_scenario_revision_id
            else None
        ),
    }


def _add_revision(session: Session, scenario: BiologicalScenario) -> BiologicalScenarioRevision:
    revision = BiologicalScenarioRevision(
        organization_id=scenario.organization_id,
        scenario_id=scenario.id,
        revision_number=scenario.revision,
        status=scenario.status,
        snapshot=_snapshot(scenario),
        created_by_user_identity_id=scenario.created_by_user_identity_id,
    )
    session.add(revision)
    return revision


def _revision_response(revision: BiologicalScenarioRevision) -> BiologicalScenarioRevisionResponse:
    return BiologicalScenarioRevisionResponse(
        id=revision.id,
        organization_id=revision.organization_id,
        scenario_id=revision.scenario_id,
        revision_number=revision.revision_number,
        status=revision.status,
        snapshot=revision.snapshot,
        created_by_user_identity_id=revision.created_by_user_identity_id,
        created_at=revision.created_at.isoformat(),
    )


def _scenario_response(
    session: Session,
    scenario: BiologicalScenario,
    *,
    include_snapshot: bool = False,
) -> BiologicalScenarioResponse:
    latest = session.scalar(
        select(BiologicalScenarioRevision).where(
            BiologicalScenarioRevision.organization_id == scenario.organization_id,
            BiologicalScenarioRevision.scenario_id == scenario.id,
            BiologicalScenarioRevision.revision_number == scenario.revision,
        )
    )
    return BiologicalScenarioResponse(
        id=scenario.id,
        organization_id=scenario.organization_id,
        scenario_key=scenario.scenario_key,
        name=scenario.name,
        scenario_type=scenario.scenario_type,
        tissue_context=scenario.tissue_context,
        clinical_context=scenario.clinical_context,
        source_type=scenario.source_type,
        source_reference=scenario.source_reference,
        assumptions=scenario.assumptions,
        status=scenario.status,
        revision=scenario.revision,
        source_scenario_revision_id=scenario.source_scenario_revision_id,
        created_by_user_identity_id=scenario.created_by_user_identity_id,
        created_at=scenario.created_at.isoformat(),
        updated_at=scenario.updated_at.isoformat(),
        latest_snapshot=latest.snapshot if include_snapshot and latest else None,
    )


def _get_scenario(
    session: Session, context: SessionContext, scenario_id: UUID
) -> BiologicalScenario:
    scenario = session.scalar(
        select(BiologicalScenario).where(
            BiologicalScenario.id == scenario_id,
            BiologicalScenario.organization_id == context.organization_id,
        )
    )
    if scenario is None:
        raise DomainError(
            "SCENARIO_NOT_FOUND",
            "The biological scenario was not found in the current organization.",
            404,
        )
    return scenario


def _check_revision(scenario: BiologicalScenario, expected_revision: int) -> None:
    if scenario.revision != expected_revision:
        raise DomainError(
            "SCENARIO_REVISION_CONFLICT",
            "The scenario changed since it was loaded.",
            409,
            [
                {
                    "field": "expected_revision",
                    "message": f"Current revision is {scenario.revision}.",
                }
            ],
        )


def _tools() -> list[BiologicalToolResponse]:
    return [
        BiologicalToolResponse(
            tool_key="BED_EQD2",
            label="BED & EQD2",
            route="/app/biological/bed-eqd2",
            phase="P13",
            status="AVAILABLE",
            available=True,
            description="Tính BED/EQD2 và đồ thị theo tổng liều D.",
        ),
        BiologicalToolResponse(
            tool_key="PLAN_COMPARISON",
            label="So sánh phác đồ",
            route="/app/biological/compare",
            phase="P14",
            status="AVAILABLE",
            available=True,
            description="So sánh nhiều phương án cùng bối cảnh sinh học.",
        ),
        BiologicalToolResponse(
            tool_key="RE_IRRADIATION",
            label="Tái xạ",
            route="/app/biological/re-irradiation",
            phase="P15",
            status="PLANNED",
            available=False,
            description="Scenario nhiều course, recovery và cumulative scalar.",
        ),
        BiologicalToolResponse(
            tool_key="FRACTION_COMPENSATION",
            label="Bù fraction",
            route="/app/biological/re-irradiation",
            phase="P15",
            status="PLANNED",
            available=False,
            description="So sánh các lịch bù fraction dưới dạng estimate.",
        ),
        BiologicalToolResponse(
            tool_key="DOSE_LIMITS_PROTOCOLS",
            label="Dose limits & protocols",
            route="/app/biological/knowledge",
            phase="P16",
            status="PLANNED",
            available=False,
            description="Thư viện tham khảo có source, applicability và version.",
        ),
        BiologicalToolResponse(
            tool_key="KNOWLEDGE_LIBRARY",
            label="Knowledge Library",
            route="/app/biological/knowledge",
            phase="P16",
            status="PLANNED",
            available=False,
            description="Tra cứu kiến thức và giả định tính toán độc lập.",
        ),
    ]


def _validation_errors(exc: DomainError) -> list[dict[str, str | None]]:
    errors: list[dict[str, str | None]] = []
    for item in exc.details:
        raw_field = item.get("field")
        raw_message = item.get("message")
        errors.append(
            {
                "code": exc.code,
                "field": raw_field if isinstance(raw_field, str) else None,
                "message": raw_message if isinstance(raw_message, str) else exc.message,
            }
        )
    return errors or [{"code": exc.code, "field": None, "message": exc.message}]


@router.get("/tools", response_model=list[BiologicalToolResponse])
def list_biological_tools(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> list[BiologicalToolResponse]:
    _context_for_organization(organization_id, identity, session)
    return _tools()


@router.get("/summary", response_model=BiologicalSummaryResponse)
def biological_summary(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalSummaryResponse:
    context = _context_for_organization(organization_id, identity, session)
    counts = {
        status_name.lower(): session.scalar(
            select(func.count())
            .select_from(BiologicalScenario)
            .where(
                BiologicalScenario.organization_id == context.organization_id,
                BiologicalScenario.status == status_name,
            )
        )
        or 0
        for status_name in _SCENARIO_STATUSES
    }
    total_scenarios = (
        session.scalar(
            select(func.count())
            .select_from(BiologicalScenario)
            .where(BiologicalScenario.organization_id == context.organization_id)
        )
        or 0
    )
    completed_calculations = (
        session.scalar(
            select(func.count())
            .select_from(BiologicalCalculationRun)
            .where(
                BiologicalCalculationRun.organization_id == context.organization_id,
                BiologicalCalculationRun.status == "COMPLETED",
            )
        )
        or 0
    )
    exported_reports = (
        session.scalar(
            select(func.count())
            .select_from(ExportJob)
            .join(ReportRevision, ExportJob.report_revision_id == ReportRevision.id)
            .where(
                ExportJob.organization_id == context.organization_id,
                ExportJob.status == "COMPLETED",
                ReportRevision.organization_id == context.organization_id,
                ReportRevision.source_type == "BIOLOGICAL",
            )
        )
        or 0
    )
    return BiologicalSummaryResponse(
        organization_id=context.organization_id,
        total_scenarios=total_scenarios,
        draft_scenarios=counts["draft"],
        saved_scenarios=counts["saved"],
        archived_scenarios=counts["archived"],
        completed_calculations=completed_calculations,
        exported_reports=exported_reports,
    )


@router.post("/scenarios/validate", response_model=BiologicalValidationResponse)
def validate_biological_scenario(
    request: BiologicalScenarioCreateRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalValidationResponse:
    _context_for_organization(organization_id, identity, session)
    try:
        _validate_create(request)
    except DomainError as exc:
        return BiologicalValidationResponse(
            valid=False,
            errors=_validation_errors(exc),
            warnings=[],
        )
    duplicate = session.scalar(
        select(BiologicalScenario.id).where(
            BiologicalScenario.organization_id == organization_id,
            BiologicalScenario.scenario_key == request.scenario_key,
        )
    )
    if duplicate is not None:
        return BiologicalValidationResponse(
            valid=False,
            errors=[
                {
                    "code": "SCENARIO_KEY_CONFLICT",
                    "field": "scenario_key",
                    "message": "Scenario key already exists in this organization.",
                }
            ],
            warnings=[],
        )
    return BiologicalValidationResponse(valid=True, errors=[], warnings=[])


@router.get("/scenarios", response_model=BiologicalScenarioCollectionResponse)
def list_biological_scenarios(
    organization_id: UUID,
    q: str | None = Query(default=None, max_length=240),
    status_filter: ScenarioStatus | None = Query(default=None, alias="status"),  # noqa: B008
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalScenarioCollectionResponse:
    context = _context_for_organization(organization_id, identity, session)
    query = select(BiologicalScenario).where(
        BiologicalScenario.organization_id == context.organization_id
    )
    count_query = (
        select(func.count())
        .select_from(BiologicalScenario)
        .where(BiologicalScenario.organization_id == context.organization_id)
    )
    if status_filter:
        query = query.where(BiologicalScenario.status == status_filter)
        count_query = count_query.where(BiologicalScenario.status == status_filter)
    elif not include_archived:
        query = query.where(BiologicalScenario.status != "ARCHIVED")
        count_query = count_query.where(BiologicalScenario.status != "ARCHIVED")
    if q:
        pattern = f"%{q}%"
        condition = or_(
            BiologicalScenario.scenario_key.ilike(pattern),
            BiologicalScenario.name.ilike(pattern),
            BiologicalScenario.scenario_type.ilike(pattern),
            BiologicalScenario.tissue_context.ilike(pattern),
        )
        query = query.where(condition)
        count_query = count_query.where(condition)
    scenarios = session.scalars(
        query.order_by(BiologicalScenario.updated_at.desc()).offset(offset).limit(limit)
    ).all()
    total = session.scalar(count_query) or 0
    return BiologicalScenarioCollectionResponse(
        items=[_scenario_response(session, item) for item in scenarios],
        total=total,
        offset=offset,
        limit=limit,
        include_archived=include_archived or status_filter == "ARCHIVED",
    )


@router.post(
    "/scenarios",
    response_model=BiologicalScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_biological_scenario(
    request: BiologicalScenarioCreateRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalScenarioResponse:
    context = _context_for_organization(organization_id, identity, session)
    _validate_create(request)
    if (
        session.scalar(
            select(BiologicalScenario.id).where(
                BiologicalScenario.organization_id == context.organization_id,
                BiologicalScenario.scenario_key == request.scenario_key,
            )
        )
        is not None
    ):
        raise DomainError(
            "SCENARIO_KEY_CONFLICT",
            "Scenario key already exists in this organization.",
            409,
        )
    actor_id = _actor_id(session, context)
    scenario = BiologicalScenario(
        organization_id=context.organization_id,
        scenario_key=request.scenario_key,
        name=request.name,
        scenario_type=request.scenario_type,
        tissue_context=request.tissue_context,
        clinical_context=request.clinical_context,
        source_type=request.source_type,
        source_reference=request.source_reference,
        assumptions=request.assumptions,
        status="DRAFT",
        revision=1,
        created_by_user_identity_id=actor_id,
    )
    session.add(scenario)
    session.flush()
    _add_revision(session, scenario)
    _audit(
        session,
        context,
        "BIOLOGICAL_SCENARIO_CREATED",
        scenario.id,
        {"scenario_key": scenario.scenario_key, "revision": scenario.revision},
    )
    _commit_or_raise(
        session,
        "SCENARIO_KEY_CONFLICT",
        "Scenario key already exists in this organization.",
        persistence_message="The biological scenario could not be created.",
    )
    return _scenario_response(session, scenario, include_snapshot=True)


@router.get("/scenarios/{scenario_id}", response_model=BiologicalScenarioResponse)
def get_biological_scenario(
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalScenarioResponse:
    context = _context_for_organization(organization_id, identity, session)
    scenario = _get_scenario(session, context, scenario_id)
    return _scenario_response(session, scenario, include_snapshot=True)


@router.get(
    "/scenarios/{scenario_id}/revisions",
    response_model=list[BiologicalScenarioRevisionResponse],
)
def list_biological_scenario_revisions(
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> list[BiologicalScenarioRevisionResponse]:
    context = _context_for_organization(organization_id, identity, session)
    _get_scenario(session, context, scenario_id)
    revisions = session.scalars(
        select(BiologicalScenarioRevision)
        .where(
            BiologicalScenarioRevision.organization_id == context.organization_id,
            BiologicalScenarioRevision.scenario_id == scenario_id,
        )
        .order_by(BiologicalScenarioRevision.revision_number.desc())
    ).all()
    return [_revision_response(item) for item in revisions]


@router.patch("/scenarios/{scenario_id}", response_model=BiologicalScenarioResponse)
def update_biological_scenario(
    request: BiologicalScenarioPatchRequest,
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalScenarioResponse:
    context = _context_for_organization(organization_id, identity, session)
    scenario = _get_scenario(session, context, scenario_id)
    _check_revision(scenario, request.expected_revision)
    if scenario.status != "DRAFT":
        raise DomainError(
            "SCENARIO_IMMUTABLE",
            "Only a DRAFT scenario can be edited; clone a saved scenario first.",
            409,
        )
    changes = request.model_dump(exclude_unset=True)
    changes.pop("expected_revision", None)
    if not changes:
        raise DomainError("NO_CHANGES", "At least one scenario field is required.", 400)
    candidate_source_type = str(changes.get("source_type", scenario.source_type))
    candidate_reference = changes.get("source_reference", scenario.source_reference)
    candidate_assumptions = changes.get("assumptions", scenario.assumptions)
    if not isinstance(candidate_assumptions, dict):
        raise DomainError(
            "BIOLOGICAL_CONTEXT_INVALID",
            "Assumptions must be a JSON object.",
            422,
            [{"field": "assumptions", "message": "Expected a JSON object."}],
        )
    _validate_json_object(candidate_assumptions)
    _validate_source(
        candidate_source_type,
        candidate_reference if isinstance(candidate_reference, str) else None,
    )
    for field, value in changes.items():
        setattr(scenario, field, value)
    scenario.revision += 1
    session.flush()
    _add_revision(session, scenario)
    _audit(
        session,
        context,
        "BIOLOGICAL_SCENARIO_UPDATED",
        scenario.id,
        {"revision": scenario.revision, "fields": sorted(changes)},
    )
    _commit_or_raise(session, "SCENARIO_PERSISTENCE_FAILED", "Scenario update failed.")
    return _scenario_response(session, scenario, include_snapshot=True)


@router.post("/scenarios/{scenario_id}/save", response_model=BiologicalScenarioResponse)
def save_biological_scenario(
    request: BiologicalScenarioTransitionRequest,
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalScenarioResponse:
    context = _context_for_organization(organization_id, identity, session)
    scenario = _get_scenario(session, context, scenario_id)
    _check_revision(scenario, request.expected_revision)
    if scenario.status != "DRAFT":
        raise DomainError(
            "SCENARIO_IMMUTABLE",
            "Only a DRAFT scenario can be saved.",
            409,
        )
    scenario.status = "SAVED"
    scenario.revision += 1
    session.flush()
    _add_revision(session, scenario)
    _audit(
        session,
        context,
        "BIOLOGICAL_SCENARIO_SAVED",
        scenario.id,
        {"revision": scenario.revision},
    )
    _commit_or_raise(session, "SCENARIO_PERSISTENCE_FAILED", "Scenario save failed.")
    return _scenario_response(session, scenario, include_snapshot=True)


@router.post(
    "/scenarios/{scenario_id}/clone",
    response_model=BiologicalScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
def clone_biological_scenario(
    request: BiologicalScenarioCloneRequest,
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalScenarioResponse:
    context = _context_for_organization(organization_id, identity, session)
    source = _get_scenario(session, context, scenario_id)
    source_revision = session.scalar(
        select(BiologicalScenarioRevision).where(
            BiologicalScenarioRevision.organization_id == context.organization_id,
            BiologicalScenarioRevision.scenario_id == source.id,
            BiologicalScenarioRevision.revision_number == source.revision,
        )
    )
    if source_revision is None:
        raise DomainError(
            "SCENARIO_NOT_FOUND",
            "The source scenario revision was not found.",
            404,
        )
    scenario_key = request.scenario_key or f"{source.scenario_key}_COPY_{uuid4().hex[:8].upper()}"
    if len(scenario_key) > 120:
        scenario_key = scenario_key[:120]
    if (
        session.scalar(
            select(BiologicalScenario.id).where(
                BiologicalScenario.organization_id == context.organization_id,
                BiologicalScenario.scenario_key == scenario_key,
            )
        )
        is not None
    ):
        raise DomainError(
            "SCENARIO_KEY_CONFLICT",
            "Scenario key already exists in this organization.",
            409,
        )
    actor_id = _actor_id(session, context)
    clone = BiologicalScenario(
        organization_id=context.organization_id,
        scenario_key=scenario_key,
        name=request.name or f"{source.name} (copy)",
        scenario_type=source.scenario_type,
        tissue_context=source.tissue_context,
        clinical_context=source.clinical_context,
        source_type=source.source_type,
        source_reference=source.source_reference,
        assumptions=dict(source.assumptions),
        status="DRAFT",
        revision=1,
        source_scenario_revision_id=source_revision.id,
        created_by_user_identity_id=actor_id,
    )
    session.add(clone)
    session.flush()
    _add_revision(session, clone)
    _audit(
        session,
        context,
        "BIOLOGICAL_SCENARIO_CLONED",
        clone.id,
        {"source_scenario_id": str(source.id), "source_revision_id": str(source_revision.id)},
    )
    _commit_or_raise(
        session,
        "SCENARIO_KEY_CONFLICT",
        "Scenario key already exists in this organization.",
        persistence_message="The biological scenario clone could not be created.",
    )
    return _scenario_response(session, clone, include_snapshot=True)


@router.post("/scenarios/{scenario_id}/archive", response_model=BiologicalScenarioResponse)
def archive_biological_scenario(
    request: BiologicalScenarioTransitionRequest,
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalScenarioResponse:
    context = _context_for_organization(organization_id, identity, session)
    scenario = _get_scenario(session, context, scenario_id)
    _check_revision(scenario, request.expected_revision)
    if scenario.status == "ARCHIVED":
        raise DomainError("SCENARIO_IMMUTABLE", "The scenario is already archived.", 409)
    scenario.status = "ARCHIVED"
    scenario.revision += 1
    session.flush()
    _add_revision(session, scenario)
    _audit(
        session,
        context,
        "BIOLOGICAL_SCENARIO_ARCHIVED",
        scenario.id,
        {"revision": scenario.revision},
    )
    _commit_or_raise(session, "SCENARIO_PERSISTENCE_FAILED", "Scenario archive failed.")
    return _scenario_response(session, scenario, include_snapshot=True)


@router.get("/calculations", response_model=BiologicalCalculationCollectionResponse)
def list_biological_calculations(
    organization_id: UUID,
    scenario_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalCalculationCollectionResponse:
    context = _context_for_organization(organization_id, identity, session)
    if scenario_id is not None:
        _get_scenario(session, context, scenario_id)
    query = select(BiologicalCalculationRun).where(
        BiologicalCalculationRun.organization_id == context.organization_id
    )
    count_query = (
        select(func.count())
        .select_from(BiologicalCalculationRun)
        .where(BiologicalCalculationRun.organization_id == context.organization_id)
    )
    if scenario_id is not None:
        query = query.where(BiologicalCalculationRun.scenario_id == scenario_id)
        count_query = count_query.where(BiologicalCalculationRun.scenario_id == scenario_id)
    calculations = session.scalars(
        query.order_by(BiologicalCalculationRun.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return BiologicalCalculationCollectionResponse(
        items=[_calculation_response(item) for item in calculations],
        total=session.scalar(count_query) or 0,
        offset=offset,
        limit=limit,
    )


def _calculation_response(run: BiologicalCalculationRun) -> BiologicalCalculationResponse:
    return BiologicalCalculationResponse(
        id=run.id,
        organization_id=run.organization_id,
        scenario_id=run.scenario_id,
        scenario_revision_id=run.scenario_revision_id,
        calculation_type=run.calculation_type,
        idempotency_key=run.idempotency_key,
        model_key=run.model_key,
        model_version=run.model_version,
        status=run.status,
        input_snapshot=run.input_snapshot,
        result_snapshot=run.result_snapshot,
        warning_snapshot=run.warning_snapshot,
        error_snapshot=run.error_snapshot,
        created_by_user_identity_id=run.created_by_user_identity_id,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
    )


@router.get("/calculations/{calculation_id}", response_model=BiologicalCalculationResponse)
def get_biological_calculation(
    calculation_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalCalculationResponse:
    context = _context_for_organization(organization_id, identity, session)
    calculation = session.scalar(
        select(BiologicalCalculationRun).where(
            BiologicalCalculationRun.id == calculation_id,
            BiologicalCalculationRun.organization_id == context.organization_id,
        )
    )
    if calculation is None:
        raise DomainError(
            "CALCULATION_NOT_FOUND",
            "The biological calculation was not found in the current organization.",
            404,
        )
    return _calculation_response(calculation)
