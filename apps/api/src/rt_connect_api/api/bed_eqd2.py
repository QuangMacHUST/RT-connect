"""P13 BED/EQD2 calculator API.

The route layer owns organization and scenario scope, idempotent persistence,
and export.  The pure numerical implementation lives in
``services.bed_eqd2_engine`` so that the same known-answer contract is used by
the API and the focused unit tests.
"""

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

from __future__ import annotations

import csv
import io
import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rt_connect_api.api.biological import (
    BiologicalCalculationResponse,
    _actor_id,
    _calculation_response,
    _context_for_organization,
    _get_scenario,
)
from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    BiologicalCalculationRun,
    BiologicalScenario,
    BiologicalScenarioRevision,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.bed_eqd2_engine import (
    BED_EQD2_ENGINE_KEY,
    BED_EQD2_ENGINE_VERSION,
    BedEqd2EngineError,
    CurveSpec,
    NormalizedFractionation,
    calculate_bed_eqd2,
    normalize_fractionation,
    request_fingerprint,
)
from rt_connect_api.services.session_context import SessionContext

router = APIRouter(prefix="/organizations/{organization_id}/biological", tags=["biological"])

AlphaBetaSourceType = Literal["USER_DEFINED", "REFERENCE"]
CurveMode = Literal["FIXED_N", "FIXED_D"]


class BedEqd2CurveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    mode: CurveMode = "FIXED_N"
    dose_min_gy: float = Field(default=0.0, ge=0.0)
    dose_max_gy: float = Field(default=100.0, ge=0.0)
    dose_step_gy: float = Field(default=1.0, gt=0.0)
    fixed_n: int | None = Field(default=None, ge=1)
    fixed_d_gy: float | None = Field(default=None, ge=0.0)
    alpha_beta_values_gy: list[float] = Field(default_factory=list, max_length=10)
    point_limit: int = Field(default=501, ge=1, le=5001)


class BedEqd2CalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    scenario_revision_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=200)
    total_dose_gy: float | None = Field(default=None, ge=0.0)
    fractions: int | None = Field(default=None, ge=1)
    dose_per_fraction_gy: float | None = Field(default=None, ge=0.0)
    consistency_tolerance_gy: float = Field(default=0.01, gt=0.0, le=100.0)
    alpha_beta_gy: float = Field(gt=0.0)
    alpha_beta_source_type: AlphaBetaSourceType
    alpha_beta_source_reference: str = Field(min_length=1, max_length=1000)
    curve: BedEqd2CurveRequest = Field(default_factory=BedEqd2CurveRequest)

    @field_validator("idempotency_key", "alpha_beta_source_reference")
    @classmethod
    def _trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class BedEqd2ChartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    curve: BedEqd2CurveRequest = Field(default_factory=BedEqd2CurveRequest)


class BedEqd2ValidationResponse(BaseModel):
    valid: bool
    errors: list[dict[str, str | None]]
    warnings: list[dict[str, str | None]]
    normalized_input: dict[str, object] | None = None
    preview: dict[str, object] | None = None


class BedEqd2ChartResponse(BaseModel):
    calculation_id: UUID
    scenario_id: UUID
    scenario_revision_id: UUID
    model_key: str
    model_version: str
    persisted: bool
    chart_dataset: dict[str, object]
    table_rows: list[dict[str, object]]


def _engine_curve(request: BedEqd2CurveRequest) -> CurveSpec:
    return CurveSpec(
        mode=request.mode,
        dose_min_gy=request.dose_min_gy,
        dose_max_gy=request.dose_max_gy,
        dose_step_gy=request.dose_step_gy,
        fixed_n=request.fixed_n,
        fixed_d_gy=request.fixed_d_gy,
        alpha_beta_values_gy=tuple(request.alpha_beta_values_gy),
        point_limit=request.point_limit,
    )


def _engine_error(exc: BedEqd2EngineError) -> DomainError:
    details = exc.details or (
        [{"field": exc.field, "message": exc.message}] if exc.field else []
    )
    return DomainError(exc.code, exc.message, 422, details)


def _validation_errors(exc: BedEqd2EngineError) -> list[dict[str, str | None]]:
    errors: list[dict[str, str | None]] = []
    items: list[dict[str, object]] = exc.details or [
        {"field": exc.field, "message": exc.message}
    ]
    for item in items:
        raw_field = item.get("field")
        raw_message = item.get("message")
        errors.append(
            {
                "code": exc.code,
                "field": raw_field if isinstance(raw_field, str) else exc.field,
                "message": raw_message if isinstance(raw_message, str) else exc.message,
            }
        )
    return errors


def _domain_validation_errors(exc: DomainError) -> list[dict[str, str | None]]:
    errors: list[dict[str, str | None]] = []
    items: list[dict[str, object]] = exc.details or [{"message": exc.message}]
    for item in items:
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


def _input_snapshot(
    *,
    scenario: BiologicalScenario,
    revision: BiologicalScenarioRevision,
    request: BedEqd2CalculationRequest,
) -> dict[str, object]:
    return {
        "schema_version": "biological-bed-eqd2-input.v1",
        "scenario_id": str(scenario.id),
        "scenario_revision_id": str(revision.id),
        "scenario_revision_number": revision.revision_number,
        "fractionation": {
            "total_dose_gy": request.total_dose_gy,
            "fractions": request.fractions,
            "dose_per_fraction_gy": request.dose_per_fraction_gy,
            "consistency_tolerance_gy": request.consistency_tolerance_gy,
        },
        "alpha_beta": {
            "value_gy": request.alpha_beta_gy,
            "source_type": request.alpha_beta_source_type,
            "source_reference": request.alpha_beta_source_reference,
        },
        "curve": request.curve.model_dump(mode="json"),
    }


def _calculate(
    request: BedEqd2CalculationRequest,
) -> tuple[dict[str, object], dict[str, object]]:
    try:
        fractionation = normalize_fractionation(
            total_dose_gy=request.total_dose_gy,
            fractions=request.fractions,
            dose_per_fraction_gy=request.dose_per_fraction_gy,
            consistency_tolerance_gy=request.consistency_tolerance_gy,
        )
        result = calculate_bed_eqd2(
            fractionation=fractionation,
            alpha_beta_gy=request.alpha_beta_gy,
            alpha_beta_source_type=request.alpha_beta_source_type,
            alpha_beta_source_reference=request.alpha_beta_source_reference,
            curve=_engine_curve(request.curve),
        )
    except BedEqd2EngineError as exc:
        raise _engine_error(exc) from exc
    return fractionation.as_dict(), result


def _revision(
    session: Session,
    context: SessionContext,
    scenario: BiologicalScenario,
    revision_id: UUID,
) -> BiologicalScenarioRevision:
    revision = session.scalar(
        select(BiologicalScenarioRevision).where(
            BiologicalScenarioRevision.id == revision_id,
            BiologicalScenarioRevision.organization_id == context.organization_id,
            BiologicalScenarioRevision.scenario_id == scenario.id,
        )
    )
    if revision is None:
        raise DomainError(
            "SCENARIO_REVISION_NOT_FOUND",
            "The selected biological scenario revision was not found.",
            404,
        )
    if scenario.status == "ARCHIVED":
        raise DomainError(
            "SCENARIO_IMMUTABLE",
            "Archived scenarios cannot start a new calculation; clone them first.",
            409,
        )
    return revision


def _audit(
    session: Session,
    context: SessionContext,
    actor_id: UUID | None,
    calculation_id: UUID,
    payload: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=actor_id,
            event_type="BIOLOGICAL_BED_EQD2_CALCULATED",
            entity_type="BiologicalCalculationRun",
            entity_id=calculation_id,
            payload=payload,
        )
    )


def _commit_calculation(
    session: Session,
    *,
    organization_id: UUID,
    idempotency_key: str,
    fingerprint: str,
) -> BiologicalCalculationRun | None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        existing = session.scalar(
            select(BiologicalCalculationRun).where(
                BiologicalCalculationRun.organization_id == organization_id,
                BiologicalCalculationRun.idempotency_key == idempotency_key,
            )
        )
        if (
            existing is not None
            and existing.input_snapshot.get("request_fingerprint") == fingerprint
        ):
            return existing
        raise DomainError(
            "CALCULATION_PERSISTENCE_FAILED",
            "The BED/EQD2 calculation could not be persisted safely.",
            503,
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DomainError(
            "CALCULATION_PERSISTENCE_FAILED",
            "The BED/EQD2 calculation could not be persisted.",
            503,
        ) from exc
    return None


def _calculation_for_scope(
    session: Session,
    context: SessionContext,
    calculation_id: UUID,
) -> BiologicalCalculationRun:
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
    return calculation


def _rebuild_from_snapshot(
    calculation: BiologicalCalculationRun,
    curve: BedEqd2CurveRequest,
) -> dict[str, object]:
    raw_fractionation = calculation.input_snapshot.get("normalized_fractionation")
    raw_alpha_beta = calculation.input_snapshot.get("alpha_beta")
    if not isinstance(raw_fractionation, dict) or not isinstance(raw_alpha_beta, dict):
        raise DomainError(
            "CALCULATION_NONFINITE",
            "The stored calculation input snapshot is incomplete.",
            422,
        )
    try:
        fractionation = NormalizedFractionation(
            total_dose_gy=float(raw_fractionation["total_dose_gy"]),
            fractions=int(raw_fractionation["fractions"]),
            dose_per_fraction_gy=float(raw_fractionation["dose_per_fraction_gy"]),
            supplied_total_dose_gy=(
                float(raw_fractionation["supplied_total_dose_gy"])
                if raw_fractionation.get("supplied_total_dose_gy") is not None
                else None
            ),
            supplied_fractions=(
                int(raw_fractionation["supplied_fractions"])
                if raw_fractionation.get("supplied_fractions") is not None
                else None
            ),
            supplied_dose_per_fraction_gy=(
                float(raw_fractionation["supplied_dose_per_fraction_gy"])
                if raw_fractionation.get("supplied_dose_per_fraction_gy") is not None
                else None
            ),
            consistency_delta_gy=float(raw_fractionation["consistency_delta_gy"]),
            consistency_tolerance_gy=float(raw_fractionation["consistency_tolerance_gy"]),
        )
        result = calculate_bed_eqd2(
            fractionation=fractionation,
            alpha_beta_gy=float(raw_alpha_beta["value_gy"]),
            alpha_beta_source_type=str(raw_alpha_beta["source_type"]),
            alpha_beta_source_reference=str(raw_alpha_beta["source_reference"]),
            curve=_engine_curve(curve),
        )
    except (KeyError, TypeError, ValueError, BedEqd2EngineError) as exc:
        if isinstance(exc, BedEqd2EngineError):
            raise _engine_error(exc) from exc
        raise DomainError(
            "CALCULATION_NONFINITE",
            "The stored calculation input snapshot cannot be replayed.",
            422,
        ) from exc
    return result


@router.post(
    "/scenarios/{scenario_id}/calculations/validate",
    response_model=BedEqd2ValidationResponse,
)
def validate_bed_eqd2(
    request: BedEqd2CalculationRequest,
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BedEqd2ValidationResponse:
    context = _context_for_organization(organization_id, identity, session)
    scenario = _get_scenario(session, context, scenario_id)
    _revision(session, context, scenario, request.scenario_revision_id)
    try:
        normalized, result = _calculate(request)
    except DomainError as exc:
        return BedEqd2ValidationResponse(
            valid=False,
            errors=_domain_validation_errors(exc),
            warnings=[],
        )
    primary = result.get("primary")
    chart_dataset = result.get("chart_dataset")
    if not isinstance(chart_dataset, dict):
        raise DomainError(
            "CALCULATION_PERSISTENCE_FAILED",
            "The BED/EQD2 preview dataset is unavailable.",
            503,
        )
    return BedEqd2ValidationResponse(
        valid=True,
        errors=[],
        warnings=[],
        normalized_input=normalized,
        preview={
            "primary": primary,
            "chart_dataset_sha256": chart_dataset.get("dataset_sha256"),
            "point_count": chart_dataset.get("point_count"),
        },
    )


@router.post(
    "/scenarios/{scenario_id}/calculations",
    response_model=BiologicalCalculationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bed_eqd2_calculation(
    request: BedEqd2CalculationRequest,
    scenario_id: UUID,
    organization_id: UUID,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BiologicalCalculationResponse:
    context = _context_for_organization(organization_id, identity, session)
    scenario = _get_scenario(session, context, scenario_id)
    revision = _revision(session, context, scenario, request.scenario_revision_id)
    _, result = _calculate(request)
    snapshot = _input_snapshot(scenario=scenario, revision=revision, request=request)
    fingerprint = request_fingerprint(snapshot)
    snapshot["request_fingerprint"] = fingerprint
    existing = session.scalar(
        select(BiologicalCalculationRun).where(
            BiologicalCalculationRun.organization_id == context.organization_id,
            BiologicalCalculationRun.idempotency_key == request.idempotency_key,
        )
    )
    if existing is not None:
        if existing.input_snapshot.get("request_fingerprint") == fingerprint:
            # A replay is successful but does not create a new resource.  Keep
            # the first-call 201 contract while making retries observable as
            # ordinary idempotent reads.
            response.status_code = status.HTTP_200_OK
            return _calculation_response(existing)
        raise DomainError(
            "CALCULATION_IDEMPOTENCY_CONFLICT",
            "The idempotency key is already associated with different calculation inputs.",
            409,
        )
    # Store the normalized values alongside the raw request so a chart replay
    # never depends on a mutable scenario or on browser state.
    normalized = normalize_fractionation(
        total_dose_gy=request.total_dose_gy,
        fractions=request.fractions,
        dose_per_fraction_gy=request.dose_per_fraction_gy,
        consistency_tolerance_gy=request.consistency_tolerance_gy,
    )
    snapshot["normalized_fractionation"] = normalized.as_dict()
    run = BiologicalCalculationRun(
        organization_id=context.organization_id,
        scenario_id=scenario.id,
        scenario_revision_id=revision.id,
        calculation_type="BED_EQD2",
        idempotency_key=request.idempotency_key,
        model_key=BED_EQD2_ENGINE_KEY,
        model_version=BED_EQD2_ENGINE_VERSION,
        status="COMPLETED",
        input_snapshot=snapshot,
        result_snapshot=result,
        warning_snapshot=[],
        error_snapshot=[],
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(run)
    session.flush()
    _audit(
        session,
        context,
        run.created_by_user_identity_id,
        run.id,
        {
            "scenario_id": str(scenario.id),
            "scenario_revision_id": str(revision.id),
            "calculation_type": run.calculation_type,
            "model_version": run.model_version,
        },
    )
    concurrent = _commit_calculation(
        session,
        organization_id=context.organization_id,
        idempotency_key=request.idempotency_key,
        fingerprint=fingerprint,
    )
    if concurrent is not None:
        # Another request won the unique-key race.  Return its committed
        # snapshot and make the replay status explicit to the client.
        response.status_code = status.HTTP_200_OK
    return _calculation_response(concurrent or run)


@router.post(
    "/calculations/{calculation_id}/charts",
    response_model=BedEqd2ChartResponse,
)
def create_bed_eqd2_chart_preview(
    request: BedEqd2ChartRequest,
    calculation_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> BedEqd2ChartResponse:
    context = _context_for_organization(organization_id, identity, session)
    calculation = _calculation_for_scope(session, context, calculation_id)
    if calculation.calculation_type != "BED_EQD2":
        raise DomainError(
            "MODULE_UNAVAILABLE",
            "The selected calculation does not contain a BED/EQD2 dataset.",
            422,
        )
    result = _rebuild_from_snapshot(calculation, request.curve)
    raw_chart_dataset = result.get("chart_dataset")
    raw_table_rows = result.get("table_rows")
    if not isinstance(raw_chart_dataset, dict) or not isinstance(raw_table_rows, list):
        raise DomainError(
            "CALCULATION_PERSISTENCE_FAILED",
            "The BED/EQD2 chart dataset is unavailable.",
            503,
        )
    table_rows = [row for row in raw_table_rows if isinstance(row, dict)]
    return BedEqd2ChartResponse(
        calculation_id=calculation.id,
        scenario_id=calculation.scenario_id,
        scenario_revision_id=calculation.scenario_revision_id,
        model_key=calculation.model_key,
        model_version=calculation.model_version,
        persisted=False,
        chart_dataset=raw_chart_dataset,
        table_rows=table_rows,
    )


@router.get("/calculations/{calculation_id}/export")
def export_bed_eqd2(
    calculation_id: UUID,
    organization_id: UUID,
    export_format: Literal["JSON", "CSV"] = Query(default="JSON"),  # noqa: B008
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> Response:
    context = _context_for_organization(organization_id, identity, session)
    calculation = _calculation_for_scope(session, context, calculation_id)
    if calculation.calculation_type != "BED_EQD2":
        raise DomainError(
            "MODULE_UNAVAILABLE",
            "The selected calculation does not contain a BED/EQD2 dataset.",
            422,
        )
    filename_root = f"rt-connect-bed-eqd2-{calculation.id}"
    if export_format == "JSON":
        payload = {
            "schema_version": "biological-bed-eqd2-export.v1",
            "calculation_id": str(calculation.id),
            "organization_id": str(calculation.organization_id),
            "scenario_id": str(calculation.scenario_id),
            "scenario_revision_id": str(calculation.scenario_revision_id),
            "idempotency_key": calculation.idempotency_key,
            "model_key": calculation.model_key,
            "model_version": calculation.model_version,
            "input_snapshot": calculation.input_snapshot,
            "result_snapshot": calculation.result_snapshot,
        }
        content = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename_root}.json"'},
        )

    rows = calculation.result_snapshot.get("table_rows")
    if not isinstance(rows, list):
        raise DomainError(
            "CALCULATION_PERSISTENCE_FAILED",
            "The stored BED/EQD2 table is unavailable for export.",
            503,
        )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "calculation_id",
            "scenario_revision_id",
            "total_dose_gy",
            "fractions",
            "dose_per_fraction_gy",
            "alpha_beta_gy",
            "bed_gy",
            "eqd2_gy",
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    for row in rows:
        if isinstance(row, dict):
            writer.writerow(
                {
                    "calculation_id": str(calculation.id),
                    "scenario_revision_id": str(calculation.scenario_revision_id),
                    **row,
                }
            )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename_root}.csv"'},
    )
