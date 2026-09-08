"""P14 multi-option BED/EQD2 comparison API.

The endpoint accepts references to immutable P13 calculation snapshots.  It
never recalculates a browser form directly and never turns a comparison into a
prescription or a QA result.  All source calculations and the common scenario
revision are resolved inside the organization scope before the pure P14
engine is called.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rt_connect_api.api.biological import (
    _actor_id,
    _context_for_organization,
    _get_scenario,
)
from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    BiologicalCalculationRun,
    BiologicalComparisonRun,
    BiologicalScenario,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.plan_comparison_engine import (
    PLAN_COMPARISON_ENGINE_KEY,
    PLAN_COMPARISON_ENGINE_VERSION,
    ComparisonOption,
    PlanComparisonEngineError,
    calculate_plan_comparison,
    request_fingerprint,
)
from rt_connect_api.services.session_context import SessionContext

router = APIRouter(prefix="/organizations/{organization_id}/biological", tags=["biological"])

OPTION_ID_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]{0,39}$"


class PlanComparisonOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str = Field(min_length=1, max_length=40, pattern=OPTION_ID_PATTERN)
    label: str = Field(min_length=1, max_length=240)
    calculation_id: UUID

    @field_validator("option_id", "label")
    @classmethod
    def _trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class PlanComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    name: str = Field(min_length=1, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=200)
    baseline_option_id: str = Field(min_length=1, max_length=40, pattern=OPTION_ID_PATTERN)
    options: list[PlanComparisonOptionRequest] = Field(min_length=2, max_length=10)

    @field_validator("name", "idempotency_key", "baseline_option_id")
    @classmethod
    def _trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class PlanComparisonCloneRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=200)
    name: str | None = Field(default=None, min_length=1, max_length=240)
    baseline_option_id: str | None = Field(
        default=None, min_length=1, max_length=40, pattern=OPTION_ID_PATTERN
    )
    option_order: list[str] | None = Field(default=None, min_length=2, max_length=10)

    @field_validator("idempotency_key", "name")
    @classmethod
    def _trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class PlanComparisonChartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_order: list[str] | None = Field(default=None, min_length=2, max_length=10)


class PlanComparisonValidationResponse(BaseModel):
    valid: bool
    errors: list[dict[str, str | None]]
    warnings: list[dict[str, str | None]]
    normalized_input: dict[str, object] | None = None
    preview: dict[str, object] | None = None


class PlanComparisonResponse(BaseModel):
    id: UUID
    organization_id: UUID
    scenario_id: UUID
    scenario_revision_id: UUID
    name: str
    idempotency_key: str
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


class PlanComparisonCollectionResponse(BaseModel):
    items: list[PlanComparisonResponse]
    total: int
    offset: int
    limit: int


class PlanComparisonChartResponse(BaseModel):
    comparison_id: UUID
    scenario_id: UUID
    scenario_revision_id: UUID
    baseline_option_id: str
    model_key: str
    model_version: str
    persisted: bool
    option_order: list[str]
    chart_dataset: dict[str, object]
    table_rows: list[dict[str, object]]


def _engine_error(exc: PlanComparisonEngineError) -> DomainError:
    details = exc.details or ([{"field": exc.field, "message": exc.message}] if exc.field else [])
    return DomainError(exc.code, exc.message, 422, details)


def _validation_errors(exc: DomainError | PlanComparisonEngineError) -> list[dict[str, str | None]]:
    raw_details = exc.details or [{"field": getattr(exc, "field", None), "message": exc.message}]
    errors: list[dict[str, str | None]] = []
    for item in raw_details:
        raw_field = item.get("field")
        raw_message = item.get("message")
        errors.append(
            {
                "code": exc.code,
                "field": raw_field if isinstance(raw_field, str) else None,
                "message": raw_message if isinstance(raw_message, str) else exc.message,
            }
        )
    return errors


def _warning_snapshot(result: dict[str, object]) -> list[dict[str, object]]:
    """Return only structured warning objects from an engine result."""

    raw_warnings = result.get("warnings")
    if not isinstance(raw_warnings, list):
        return []
    return [item for item in raw_warnings if isinstance(item, dict)]


def _as_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "The source calculation contains a non-numeric value.",
            422,
            [{"field": field, "message": "A finite numeric value is required."}],
        )
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "The source calculation contains a non-finite value.",
            422,
            [{"field": field, "message": "NaN and Infinity are not accepted."}],
        )
    return number


def _as_int(value: object, field: str) -> int:
    number = _as_float(value, field)
    if not number.is_integer():
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "The source calculation contains a non-integer fraction count.",
            422,
            [{"field": field, "message": "The fraction count must be an integer."}],
        )
    return int(number)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "The source calculation snapshot is missing required text.",
            422,
            [{"field": field, "message": "A non-blank value is required."}],
        )
    return value.strip()


def _option_from_calculation(
    request: PlanComparisonOptionRequest,
    calculation: BiologicalCalculationRun,
    scenario: BiologicalScenario,
) -> ComparisonOption:
    if calculation.calculation_type != "BED_EQD2" or calculation.status != "COMPLETED":
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "Every comparison option must reference a completed P13 BED/EQD2 calculation.",
            422,
            [
                {
                    "field": f"options.{request.option_id}.calculation_id",
                    "message": "Use a completed BED/EQD2 snapshot.",
                }
            ],
        )
    result = calculation.result_snapshot
    primary = result.get("primary")
    alpha_beta = result.get("alpha_beta")
    fractionation = result.get("fractionation")
    if (
        not isinstance(primary, dict)
        or not isinstance(alpha_beta, dict)
        or not isinstance(fractionation, dict)
    ):
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "The source calculation snapshot is incomplete.",
            422,
            [
                {
                    "field": f"options.{request.option_id}",
                    "message": "Primary, fractionation and alpha/beta snapshots are required.",
                }
            ],
        )
    return ComparisonOption(
        option_id=request.option_id,
        label=request.label,
        calculation_id=str(calculation.id),
        scenario_id=str(calculation.scenario_id),
        scenario_revision_id=str(calculation.scenario_revision_id),
        model_key=_text(calculation.model_key, "model_key"),
        model_version=_text(calculation.model_version, "model_version"),
        tissue_context=_text(scenario.tissue_context, "tissue_context"),
        total_dose_gy=_as_float(
            primary.get("total_dose_gy"), f"options.{request.option_id}.total_dose_gy"
        ),
        fractions=_as_int(primary.get("fractions"), f"options.{request.option_id}.fractions"),
        dose_per_fraction_gy=_as_float(
            primary.get("dose_per_fraction_gy"), f"options.{request.option_id}.dose_per_fraction_gy"
        ),
        alpha_beta_gy=_as_float(
            alpha_beta.get("value_gy"), f"options.{request.option_id}.alpha_beta_gy"
        ),
        alpha_beta_source_type=_text(
            alpha_beta.get("source_type"), f"options.{request.option_id}.alpha_beta_source_type"
        ),
        alpha_beta_source_reference=_text(
            alpha_beta.get("source_reference"),
            f"options.{request.option_id}.alpha_beta_source_reference",
        ),
        bed_gy=_as_float(primary.get("bed_gy"), f"options.{request.option_id}.bed_gy"),
        eqd2_gy=_as_float(primary.get("eqd2_gy"), f"options.{request.option_id}.eqd2_gy"),
    )


def _resolve_options(
    session: Session,
    context: SessionContext,
    options: list[PlanComparisonOptionRequest],
) -> list[ComparisonOption]:
    calculation_ids = [item.calculation_id for item in options]
    if len(set(calculation_ids)) != len(calculation_ids):
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "Each comparison option must reference a different calculation snapshot.",
            422,
            [
                {
                    "field": "options.calculation_id",
                    "message": "Duplicate calculation IDs are not allowed.",
                }
            ],
        )
    calculations = session.scalars(
        select(BiologicalCalculationRun).where(
            BiologicalCalculationRun.organization_id == context.organization_id,
            BiologicalCalculationRun.id.in_(calculation_ids),
        )
    ).all()
    by_id = {item.id: item for item in calculations}
    scenarios: dict[UUID, BiologicalScenario] = {}
    resolved: list[ComparisonOption] = []
    for item in options:
        calculation = by_id.get(item.calculation_id)
        if calculation is None:
            raise DomainError(
                "COMPARISON_OPTION_INVALID",
                "A comparison option calculation was not found in the current organization.",
                404,
                [
                    {
                        "field": f"options.{item.option_id}.calculation_id",
                        "message": "The source snapshot is missing or out of scope.",
                    }
                ],
            )
        scenario = scenarios.get(calculation.scenario_id)
        if scenario is None:
            scenario = _get_scenario(session, context, calculation.scenario_id)
            scenarios[calculation.scenario_id] = scenario
        resolved.append(_option_from_calculation(item, calculation, scenario))
    return resolved


def _input_snapshot(
    request: PlanComparisonRequest,
    options: list[ComparisonOption],
) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "schema_version": "biological-plan-comparison-input.v1",
        "name": request.name,
        "baseline_option_id": request.baseline_option_id,
        "options": [option.as_dict() for option in options],
        "option_order": [option.option_id for option in options],
    }
    snapshot["request_fingerprint"] = request_fingerprint(snapshot)
    return snapshot


def _response(run: BiologicalComparisonRun) -> PlanComparisonResponse:
    return PlanComparisonResponse(
        id=run.id,
        organization_id=run.organization_id,
        scenario_id=run.scenario_id,
        scenario_revision_id=run.scenario_revision_id,
        name=run.name,
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


def _commit(
    session: Session,
    *,
    organization_id: UUID,
    idempotency_key: str,
    fingerprint: str,
) -> BiologicalComparisonRun | None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        existing = session.scalar(
            select(BiologicalComparisonRun).where(
                BiologicalComparisonRun.organization_id == organization_id,
                BiologicalComparisonRun.idempotency_key == idempotency_key,
            )
        )
        if (
            existing is not None
            and existing.input_snapshot.get("request_fingerprint") == fingerprint
        ):
            return existing
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The plan comparison could not be persisted safely.",
            503,
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The plan comparison could not be persisted.",
            503,
        ) from exc
    return None


def _audit(
    session: Session,
    context: SessionContext,
    comparison_id: UUID,
    source_calculation_ids: list[str],
) -> None:
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor_id(session, context),
            event_type="BIOLOGICAL_PLAN_COMPARISON_CALCULATED",
            entity_type="BiologicalComparisonRun",
            entity_id=comparison_id,
            payload={
                "calculation_ids": source_calculation_ids,
                "engine_key": PLAN_COMPARISON_ENGINE_KEY,
                "engine_version": PLAN_COMPARISON_ENGINE_VERSION,
            },
        )
    )


def _result_ordered(
    result: dict[str, object],
    option_order: list[str] | None,
) -> tuple[dict[str, object], list[dict[str, object]], list[str]]:
    raw_rows = result.get("table_rows")
    raw_chart = result.get("chart_dataset")
    raw_baseline = result.get("baseline_option_id")
    if (
        not isinstance(raw_rows, list)
        or not isinstance(raw_chart, dict)
        or not isinstance(raw_baseline, str)
    ):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The stored comparison dataset is incomplete.",
            503,
        )
    rows = [row for row in raw_rows if isinstance(row, dict)]
    available = [str(row.get("option_id")) for row in rows]
    if (
        len(rows) != len(raw_rows)
        or not available
        or "None" in available
        or len(set(available)) != len(available)
    ):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The stored comparison table contains invalid option identities.",
            503,
        )
    requested = available if option_order is None else option_order
    if len(requested) != len(available) or set(requested) != set(available):
        raise DomainError(
            "COMPARISON_OPTION_INVALID",
            "The requested option order must contain every option exactly once.",
            422,
            [
                {
                    "field": "option_order",
                    "message": "Reordering cannot add, remove, or duplicate options.",
                }
            ],
        )
    by_id = {str(row.get("option_id")): row for row in rows}
    ordered_rows = [by_id[option_id] for option_id in requested]
    categories = raw_chart.get("categories")
    if not isinstance(categories, list):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The stored comparison chart dataset is incomplete.",
            503,
        )
    category_by_id = {
        str(category.get("option_id")): category
        for category in categories
        if isinstance(category, dict)
    }
    if (
        len(category_by_id) != len(categories)
        or set(category_by_id) != set(available)
        or any(option_id == "None" for option_id in category_by_id)
    ):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The stored comparison chart categories do not match the table.",
            503,
        )
    ordered_categories = [category_by_id[option_id] for option_id in requested]
    chart_without_hash = {key: value for key, value in raw_chart.items() if key != "dataset_sha256"}
    chart_without_hash["categories"] = ordered_categories
    chart_without_hash["option_order"] = requested
    encoded = json.dumps(
        chart_without_hash,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    import hashlib

    chart = {
        **chart_without_hash,
        "dataset_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    ordered_result = {**result, "table_rows": ordered_rows, "chart_dataset": chart}
    return ordered_result, ordered_rows, requested


@router.post(
    "/comparisons/validate",
    response_model=PlanComparisonValidationResponse,
)
def validate_plan_comparison(
    request: PlanComparisonRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PlanComparisonValidationResponse:
    context = _context_for_organization(organization_id, identity, session)
    try:
        options = _resolve_options(session, context, request.options)
        result = calculate_plan_comparison(
            options=options,
            baseline_option_id=request.baseline_option_id,
        )
    except (DomainError, PlanComparisonEngineError) as exc:
        return PlanComparisonValidationResponse(
            valid=False,
            errors=_validation_errors(exc),
            warnings=[],
        )
    warnings = _warning_snapshot(result)
    chart = result.get("chart_dataset")
    return PlanComparisonValidationResponse(
        valid=True,
        errors=[],
        warnings=[
            {
                "code": str(item.get("code", "COMPARISON_WARNING")),
                "field": str(item.get("field")) if item.get("field") is not None else None,
                "message": str(item.get("message", "Comparison warning.")),
            }
            for item in warnings
        ],
        normalized_input={
            "option_order": [option.option_id for option in options],
            "baseline_option_id": request.baseline_option_id,
        },
        preview={
            "baseline_option_id": request.baseline_option_id,
            "point_count": chart.get("point_count") if isinstance(chart, dict) else None,
            "dataset_sha256": chart.get("dataset_sha256") if isinstance(chart, dict) else None,
            "table_rows": result.get("table_rows", []),
        },
    )


@router.post(
    "/comparisons",
    response_model=PlanComparisonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_plan_comparison(
    request: PlanComparisonRequest,
    organization_id: UUID,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PlanComparisonResponse:
    context = _context_for_organization(organization_id, identity, session)
    options = _resolve_options(session, context, request.options)
    result = calculate_plan_comparison(
        options=options,
        baseline_option_id=request.baseline_option_id,
    )
    input_snapshot = _input_snapshot(request, options)
    fingerprint = str(input_snapshot["request_fingerprint"])
    existing = session.scalar(
        select(BiologicalComparisonRun).where(
            BiologicalComparisonRun.organization_id == context.organization_id,
            BiologicalComparisonRun.idempotency_key == request.idempotency_key,
        )
    )
    if existing is not None:
        if existing.input_snapshot.get("request_fingerprint") == fingerprint:
            response.status_code = status.HTTP_200_OK
            return _response(existing)
        raise DomainError(
            "COMPARISON_IDEMPOTENCY_CONFLICT",
            "The comparison idempotency key is already associated with different inputs.",
            409,
        )
    first = options[0]
    run = BiologicalComparisonRun(
        organization_id=context.organization_id,
        scenario_id=UUID(first.scenario_id),
        scenario_revision_id=UUID(first.scenario_revision_id),
        name=request.name,
        idempotency_key=request.idempotency_key,
        model_key=PLAN_COMPARISON_ENGINE_KEY,
        model_version=PLAN_COMPARISON_ENGINE_VERSION,
        status="COMPLETED",
        input_snapshot=input_snapshot,
        result_snapshot=result,
        warning_snapshot=_warning_snapshot(result),
        error_snapshot=[],
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(run)
    session.flush()
    _audit(session, context, run.id, [option.calculation_id for option in options])
    concurrent = _commit(
        session,
        organization_id=context.organization_id,
        idempotency_key=request.idempotency_key,
        fingerprint=fingerprint,
    )
    if concurrent is not None:
        response.status_code = status.HTTP_200_OK
    return _response(concurrent or run)


@router.get("/comparisons", response_model=PlanComparisonCollectionResponse)
def list_plan_comparisons(
    organization_id: UUID,
    scenario_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PlanComparisonCollectionResponse:
    context = _context_for_organization(organization_id, identity, session)
    query = select(BiologicalComparisonRun).where(
        BiologicalComparisonRun.organization_id == context.organization_id
    )
    count_query = (
        select(func.count())
        .select_from(BiologicalComparisonRun)
        .where(BiologicalComparisonRun.organization_id == context.organization_id)
    )
    if scenario_id is not None:
        query = query.where(BiologicalComparisonRun.scenario_id == scenario_id)
        count_query = count_query.where(BiologicalComparisonRun.scenario_id == scenario_id)
    runs = session.scalars(
        query.order_by(BiologicalComparisonRun.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return PlanComparisonCollectionResponse(
        items=[_response(run) for run in runs],
        total=session.scalar(count_query) or 0,
        offset=offset,
        limit=limit,
    )


def _comparison_for_scope(
    session: Session,
    context: SessionContext,
    comparison_id: UUID,
) -> BiologicalComparisonRun:
    run = session.scalar(
        select(BiologicalComparisonRun).where(
            BiologicalComparisonRun.id == comparison_id,
            BiologicalComparisonRun.organization_id == context.organization_id,
        )
    )
    if run is None:
        raise DomainError(
            "COMPARISON_NOT_FOUND",
            "The plan comparison was not found in the current organization.",
            404,
        )
    return run


@router.get("/comparisons/{comparison_id}", response_model=PlanComparisonResponse)
def get_plan_comparison(
    comparison_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PlanComparisonResponse:
    context = _context_for_organization(organization_id, identity, session)
    return _response(_comparison_for_scope(session, context, comparison_id))


@router.post("/comparisons/{comparison_id}/charts", response_model=PlanComparisonChartResponse)
def create_plan_comparison_chart_preview(
    request: PlanComparisonChartRequest,
    comparison_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PlanComparisonChartResponse:
    context = _context_for_organization(organization_id, identity, session)
    run = _comparison_for_scope(session, context, comparison_id)
    result, rows, option_order = _result_ordered(run.result_snapshot, request.option_order)
    chart = result.get("chart_dataset")
    if not isinstance(chart, dict):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The plan comparison chart dataset is unavailable.",
            503,
        )
    baseline = result.get("baseline_option_id")
    if not isinstance(baseline, str):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The plan comparison baseline is unavailable.",
            503,
        )
    return PlanComparisonChartResponse(
        comparison_id=run.id,
        scenario_id=run.scenario_id,
        scenario_revision_id=run.scenario_revision_id,
        baseline_option_id=baseline,
        model_key=run.model_key,
        model_version=run.model_version,
        persisted=False,
        option_order=option_order,
        chart_dataset=chart,
        table_rows=rows,
    )


@router.post(
    "/comparisons/{comparison_id}/clone",
    response_model=PlanComparisonResponse,
    status_code=status.HTTP_201_CREATED,
)
def clone_plan_comparison(
    request: PlanComparisonCloneRequest,
    comparison_id: UUID,
    organization_id: UUID,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PlanComparisonResponse:
    context = _context_for_organization(organization_id, identity, session)
    source = _comparison_for_scope(session, context, comparison_id)
    raw_options = source.input_snapshot.get("options")
    raw_baseline = source.result_snapshot.get("baseline_option_id")
    if not isinstance(raw_options, list) or not isinstance(raw_baseline, str):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The source comparison snapshot is incomplete and cannot be cloned.",
            503,
        )
    options: list[ComparisonOption] = []
    for index, raw in enumerate(raw_options):
        if not isinstance(raw, dict):
            raise DomainError(
                "COMPARISON_PERSISTENCE_FAILED",
                "The source comparison option snapshot is invalid.",
                503,
                [{"field": f"options[{index}]", "message": "Expected an object."}],
            )
        fractionation = raw.get("fractionation")
        alpha_beta = raw.get("alpha_beta")
        primary = raw.get("primary")
        if (
            not isinstance(fractionation, dict)
            or not isinstance(alpha_beta, dict)
            or not isinstance(primary, dict)
        ):
            raise DomainError(
                "COMPARISON_PERSISTENCE_FAILED",
                "The source comparison option snapshot is incomplete.",
                503,
            )
        try:
            options.append(
                ComparisonOption(
                    option_id=_text(raw.get("option_id"), f"options[{index}].option_id"),
                    label=_text(raw.get("label"), f"options[{index}].label"),
                    calculation_id=_text(
                        raw.get("calculation_id"), f"options[{index}].calculation_id"
                    ),
                    scenario_id=_text(raw.get("scenario_id"), f"options[{index}].scenario_id"),
                    scenario_revision_id=_text(
                        raw.get("scenario_revision_id"), f"options[{index}].scenario_revision_id"
                    ),
                    model_key=_text(raw.get("model_key"), f"options[{index}].model_key"),
                    model_version=_text(
                        raw.get("model_version"), f"options[{index}].model_version"
                    ),
                    tissue_context=_text(
                        raw.get("tissue_context"), f"options[{index}].tissue_context"
                    ),
                    total_dose_gy=_as_float(
                        fractionation.get("total_dose_gy"), f"options[{index}].total_dose_gy"
                    ),
                    fractions=_as_int(
                        fractionation.get("fractions"), f"options[{index}].fractions"
                    ),
                    dose_per_fraction_gy=_as_float(
                        fractionation.get("dose_per_fraction_gy"),
                        f"options[{index}].dose_per_fraction_gy",
                    ),
                    alpha_beta_gy=_as_float(
                        alpha_beta.get("value_gy"), f"options[{index}].alpha_beta_gy"
                    ),
                    alpha_beta_source_type=_text(
                        alpha_beta.get("source_type"), f"options[{index}].alpha_beta_source_type"
                    ),
                    alpha_beta_source_reference=_text(
                        alpha_beta.get("source_reference"),
                        f"options[{index}].alpha_beta_source_reference",
                    ),
                    bed_gy=_as_float(primary.get("bed_gy"), f"options[{index}].bed_gy"),
                    eqd2_gy=_as_float(primary.get("eqd2_gy"), f"options[{index}].eqd2_gy"),
                )
            )
        except DomainError as exc:
            raise DomainError(
                "COMPARISON_PERSISTENCE_FAILED",
                "The source comparison option snapshot is invalid and cannot be cloned.",
                503,
            ) from exc
    selected_baseline = request.baseline_option_id or raw_baseline
    ordered = options
    if request.option_order is not None:
        by_id = {option.option_id: option for option in options}
        if len(request.option_order) != len(by_id) or set(request.option_order) != set(by_id):
            raise DomainError(
                "COMPARISON_OPTION_INVALID",
                "The requested option order must contain every option exactly once.",
                422,
                [
                    {
                        "field": "option_order",
                        "message": "Reordering cannot add, remove, or duplicate options.",
                    }
                ],
            )
        ordered = [by_id[item] for item in request.option_order]
    result = calculate_plan_comparison(options=ordered, baseline_option_id=selected_baseline)
    input_snapshot: dict[str, object] = {
        "schema_version": "biological-plan-comparison-input.v1",
        "name": request.name or f"{source.name} (clone)",
        "baseline_option_id": selected_baseline,
        "options": [option.as_dict() for option in ordered],
        "option_order": [option.option_id for option in ordered],
        "cloned_from_comparison_id": str(source.id),
    }
    input_snapshot["request_fingerprint"] = request_fingerprint(input_snapshot)
    fingerprint = str(input_snapshot["request_fingerprint"])
    existing = session.scalar(
        select(BiologicalComparisonRun).where(
            BiologicalComparisonRun.organization_id == context.organization_id,
            BiologicalComparisonRun.idempotency_key == request.idempotency_key,
        )
    )
    if existing is not None:
        if existing.input_snapshot.get("request_fingerprint") == fingerprint:
            response.status_code = status.HTTP_200_OK
            return _response(existing)
        raise DomainError(
            "COMPARISON_IDEMPOTENCY_CONFLICT",
            "The comparison idempotency key is already associated with different inputs.",
            409,
        )
    first = ordered[0]
    run = BiologicalComparisonRun(
        organization_id=context.organization_id,
        scenario_id=UUID(first.scenario_id),
        scenario_revision_id=UUID(first.scenario_revision_id),
        name=str(input_snapshot["name"]),
        idempotency_key=request.idempotency_key,
        model_key=PLAN_COMPARISON_ENGINE_KEY,
        model_version=PLAN_COMPARISON_ENGINE_VERSION,
        status="COMPLETED",
        input_snapshot=input_snapshot,
        result_snapshot=result,
        warning_snapshot=_warning_snapshot(result),
        error_snapshot=[],
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(run)
    session.flush()
    _audit(session, context, run.id, [option.calculation_id for option in ordered])
    concurrent = _commit(
        session,
        organization_id=context.organization_id,
        idempotency_key=request.idempotency_key,
        fingerprint=fingerprint,
    )
    if concurrent is not None:
        response.status_code = status.HTTP_200_OK
    return _response(concurrent or run)


@router.get("/comparisons/{comparison_id}/export")
def export_plan_comparison(
    comparison_id: UUID,
    organization_id: UUID,
    export_format: Literal["JSON", "CSV"] = Query(default="JSON"),  # noqa: B008
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> Response:
    context = _context_for_organization(organization_id, identity, session)
    run = _comparison_for_scope(session, context, comparison_id)
    filename_root = f"rt-connect-plan-comparison-{run.id}"
    if export_format == "JSON":
        content = json.dumps(
            {
                "schema_version": "biological-plan-comparison-export.v1",
                "comparison_id": str(run.id),
                "organization_id": str(run.organization_id),
                "scenario_id": str(run.scenario_id),
                "scenario_revision_id": str(run.scenario_revision_id),
                "name": run.name,
                "idempotency_key": run.idempotency_key,
                "model_key": run.model_key,
                "model_version": run.model_version,
                "input_snapshot": run.input_snapshot,
                "result_snapshot": run.result_snapshot,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_root}.json"'},
        )
    rows = run.result_snapshot.get("table_rows")
    if not isinstance(rows, list):
        raise DomainError(
            "COMPARISON_PERSISTENCE_FAILED",
            "The stored plan comparison table is unavailable for export.",
            503,
        )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "comparison_id",
            "scenario_revision_id",
            "option_id",
            "label",
            "calculation_id",
            "total_dose_gy",
            "fractions",
            "dose_per_fraction_gy",
            "alpha_beta_gy",
            "bed_gy",
            "eqd2_gy",
            "is_baseline",
            "delta_bed_gy",
            "delta_bed_percent",
            "delta_bed_percent_reason",
            "delta_eqd2_gy",
            "delta_eqd2_percent",
            "delta_eqd2_percent_reason",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        if isinstance(row, dict):
            writer.writerow(
                {
                    "comparison_id": str(run.id),
                    "scenario_revision_id": str(run.scenario_revision_id),
                    **row,
                }
            )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename_root}.csv"'},
    )
