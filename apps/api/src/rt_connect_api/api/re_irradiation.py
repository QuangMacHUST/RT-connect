"""P15 scalar re-irradiation and fraction-compensation API.

The API resolves a saved biological scenario revision inside the authenticated
organization before invoking the pure P15 engine.  Validate-only requests do
not write a run.  Saved runs contain the exact request, engine result, model
version, warning list, and checksum needed to reproduce an independent
scenario estimate.
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
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rt_connect_api.api.biological import _actor_id, _context_for_organization, _get_scenario
from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    BiologicalReirradiationRun,
    BiologicalScenario,
    BiologicalScenarioRevision,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.re_irradiation_engine import (
    FRACTION_COMPENSATION_ENGINE_KEY,
    FRACTION_COMPENSATION_ENGINE_VERSION,
    REIRRADIATION_ENGINE_KEY,
    REIRRADIATION_ENGINE_VERSION,
    ReIrradiationEngineError,
    calculate_fraction_compensation,
    calculate_re_irradiation,
    request_fingerprint,
)
from rt_connect_api.services.session_context import SessionContext

router = APIRouter(prefix="/organizations/{organization_id}/biological", tags=["biological"])


def _default_recovery_model() -> dict[str, object]:
    return {"mode": "NONE"}


def _default_time_model() -> dict[str, object]:
    return {"mode": "NONE"}


class ReIrradiationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    scenario_revision_id: UUID
    name: str = Field(default="P15 re-irradiation scenario", min_length=1, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=200)
    courses: list[dict[str, object]] = Field(min_length=2, max_length=20)
    recovery_model: dict[str, object] = Field(default_factory=_default_recovery_model)
    sensitivity_recovery_fractions: list[float] = Field(
        default_factory=lambda: [0.0, 0.25, 0.5, 0.75, 1.0], max_length=21
    )
    spatial: dict[str, object] = Field(default_factory=dict)

    @field_validator("name", "idempotency_key")
    @classmethod
    def _trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class FractionCompensationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    scenario_revision_id: UUID
    name: str = Field(default="P15 fraction compensation scenario", min_length=1, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=200)
    planned_fraction_doses_gy: list[float] = Field(min_length=1, max_length=10_000)
    delivered_fraction_doses_gy: list[float] = Field(default_factory=list, max_length=10_000)
    consistency_tolerance_gy: float = Field(default=0.01, gt=0.0, le=100.0)
    alpha_beta_gy: float = Field(gt=0.0)
    alpha_beta_source_type: Literal["USER_DEFINED", "REFERENCE"]
    alpha_beta_source_reference: str = Field(min_length=1, max_length=1000)
    alternatives: list[dict[str, object]] = Field(min_length=1, max_length=20)
    interruptions: list[dict[str, object]] = Field(default_factory=list)
    time_model: dict[str, object] = Field(default_factory=_default_time_model)

    @field_validator("name", "idempotency_key", "alpha_beta_source_reference")
    @classmethod
    def _trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be blank")
        return value


class P15ValidationResponse(BaseModel):
    valid: bool
    errors: list[dict[str, str | None]]
    warnings: list[dict[str, str | None]]
    normalized_input: dict[str, object] | None = None
    preview: dict[str, object] | None = None


class P15RunResponse(BaseModel):
    id: UUID
    organization_id: UUID
    scenario_id: UUID
    scenario_revision_id: UUID
    operation_type: str
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


class P15CollectionResponse(BaseModel):
    items: list[P15RunResponse]
    total: int
    offset: int
    limit: int


def _engine_error(exc: ReIrradiationEngineError) -> DomainError:
    details = exc.details or ([{"field": exc.field, "message": exc.message}] if exc.field else [])
    return DomainError(exc.code, exc.message, 422, details)


def _validation_errors(exc: ReIrradiationEngineError | DomainError) -> list[dict[str, str | None]]:
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


def _warnings(result: dict[str, object]) -> list[dict[str, object]]:
    raw = result.get("warnings")
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _validation_warnings(result: dict[str, object]) -> list[dict[str, str | None]]:
    warnings: list[dict[str, str | None]] = []
    for item in _warnings(result):
        raw_code = item.get("code")
        raw_field = item.get("field")
        raw_message = item.get("message")
        warnings.append(
            {
                "code": raw_code if isinstance(raw_code, str) else "P15_WARNING",
                "field": raw_field if isinstance(raw_field, str) else None,
                "message": raw_message
                if isinstance(raw_message, str)
                else "P15 calculation warning.",
            }
        )
    return warnings


def _revision(
    session: Session,
    context: SessionContext,
    scenario: BiologicalScenario,
    revision_id: UUID,
) -> BiologicalScenarioRevision:
    if scenario.status == "ARCHIVED":
        raise DomainError(
            "SCENARIO_IMMUTABLE",
            "Archived scenarios cannot start a P15 calculation; clone them first.",
            409,
        )
    if scenario.status != "SAVED":
        raise DomainError(
            "SCENARIO_SAVED_REQUIRED",
            "P15 calculations require a SAVED biological scenario.",
            409,
        )
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
    if revision.status != "SAVED":
        raise DomainError(
            "SCENARIO_REVISION_NOT_SAVED",
            "P15 calculations require a SAVED scenario revision.",
            409,
        )
    return revision


def _resolve(
    session: Session,
    context: SessionContext,
    scenario_id: UUID,
    revision_id: UUID,
) -> tuple[BiologicalScenario, BiologicalScenarioRevision]:
    scenario = _get_scenario(session, context, scenario_id)
    return scenario, _revision(session, context, scenario, revision_id)


def _calculate(operation: str, payload: dict[str, object]) -> tuple[dict[str, object], str, str]:
    try:
        if operation == "REIRRADIATION":
            return (
                calculate_re_irradiation(payload),
                REIRRADIATION_ENGINE_KEY,
                REIRRADIATION_ENGINE_VERSION,
            )
        return (
            calculate_fraction_compensation(payload),
            FRACTION_COMPENSATION_ENGINE_KEY,
            FRACTION_COMPENSATION_ENGINE_VERSION,
        )
    except ReIrradiationEngineError as exc:
        raise _engine_error(exc) from exc


def _request_payload(request: BaseModel) -> dict[str, object]:
    raw = request.model_dump(mode="json")
    if not isinstance(raw, dict):
        raise DomainError(
            "REIRRADIATION_INPUT_INVALID", "The request payload must be an object.", 422
        )
    return raw


def _input_snapshot(
    *,
    scenario: BiologicalScenario,
    revision: BiologicalScenarioRevision,
    payload: dict[str, object],
) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "schema_version": "biological-p15-input.v1",
        "scenario_id": str(scenario.id),
        "scenario_revision_id": str(revision.id),
        "scenario_revision_number": revision.revision_number,
        "request": payload,
    }
    snapshot["request_fingerprint"] = request_fingerprint(snapshot)
    return snapshot


def _response(run: BiologicalReirradiationRun) -> P15RunResponse:
    return P15RunResponse(
        id=run.id,
        organization_id=run.organization_id,
        scenario_id=run.scenario_id,
        scenario_revision_id=run.scenario_revision_id,
        operation_type=run.operation_type,
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


def _audit(
    session: Session,
    context: SessionContext,
    run: BiologicalReirradiationRun,
) -> None:
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor_id(session, context),
            event_type=f"BIOLOGICAL_{run.operation_type}_CALCULATED",
            entity_type="BiologicalReirradiationRun",
            entity_id=run.id,
            payload={
                "scenario_id": str(run.scenario_id),
                "scenario_revision_id": str(run.scenario_revision_id),
                "operation_type": run.operation_type,
                "model_key": run.model_key,
                "model_version": run.model_version,
            },
        )
    )


def _commit(
    session: Session,
    *,
    organization_id: UUID,
    idempotency_key: str,
    fingerprint: str,
) -> BiologicalReirradiationRun | None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        existing = session.scalar(
            select(BiologicalReirradiationRun).where(
                BiologicalReirradiationRun.organization_id == organization_id,
                BiologicalReirradiationRun.idempotency_key == idempotency_key,
            )
        )
        if (
            existing is not None
            and existing.input_snapshot.get("request_fingerprint") == fingerprint
        ):
            return existing
        raise DomainError(
            "REIRRADIATION_PERSISTENCE_FAILED",
            "The P15 snapshot could not be persisted safely.",
            503,
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DomainError(
            "REIRRADIATION_PERSISTENCE_FAILED",
            "The P15 snapshot could not be persisted.",
            503,
        ) from exc
    return None


def _existing_or_conflict(
    session: Session,
    context: SessionContext,
    idempotency_key: str,
    fingerprint: str,
) -> BiologicalReirradiationRun | None:
    existing = session.scalar(
        select(BiologicalReirradiationRun).where(
            BiologicalReirradiationRun.organization_id == context.organization_id,
            BiologicalReirradiationRun.idempotency_key == idempotency_key,
        )
    )
    if existing is None:
        return None
    if existing.input_snapshot.get("request_fingerprint") == fingerprint:
        return existing
    raise DomainError(
        "P15_IDEMPOTENCY_CONFLICT",
        "The idempotency key is already associated with different P15 inputs.",
        409,
    )


def _create_run(
    *,
    operation: str,
    request: BaseModel,
    organization_id: UUID,
    scenario_id: UUID,
    response: Response,
    identity: AuthenticatedIdentity,
    session: Session,
) -> P15RunResponse:
    context = _context_for_organization(organization_id, identity, session)
    payload = _request_payload(request)
    revision_raw = payload.get("scenario_revision_id")
    if not isinstance(revision_raw, str):
        raise DomainError(
            "SCENARIO_REVISION_NOT_FOUND", "The selected scenario revision is invalid.", 422
        )
    scenario, revision = _resolve(session, context, scenario_id, UUID(revision_raw))
    result, model_key, model_version = _calculate(operation, payload)
    snapshot = _input_snapshot(scenario=scenario, revision=revision, payload=payload)
    fingerprint = str(snapshot["request_fingerprint"])
    idempotency_key = str(payload["idempotency_key"])
    existing = _existing_or_conflict(session, context, idempotency_key, fingerprint)
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return _response(existing)
    run = BiologicalReirradiationRun(
        organization_id=context.organization_id,
        scenario_id=scenario.id,
        scenario_revision_id=revision.id,
        operation_type=operation,
        name=str(payload["name"]),
        idempotency_key=idempotency_key,
        model_key=model_key,
        model_version=model_version,
        status="COMPLETED",
        input_snapshot=snapshot,
        result_snapshot=result,
        warning_snapshot=_warnings(result),
        error_snapshot=[],
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(run)
    session.flush()
    _audit(session, context, run)
    concurrent = _commit(
        session,
        organization_id=context.organization_id,
        idempotency_key=idempotency_key,
        fingerprint=fingerprint,
    )
    if concurrent is not None:
        response.status_code = status.HTTP_200_OK
    return _response(concurrent or run)


def _validate(
    *,
    operation: str,
    request: BaseModel,
    organization_id: UUID,
    scenario_id: UUID,
    identity: AuthenticatedIdentity,
    session: Session,
) -> P15ValidationResponse:
    context = _context_for_organization(organization_id, identity, session)
    payload = _request_payload(request)
    revision_raw = payload.get("scenario_revision_id")
    if not isinstance(revision_raw, str):
        raise DomainError(
            "SCENARIO_REVISION_NOT_FOUND", "The selected scenario revision is invalid.", 422
        )
    scenario, revision = _resolve(session, context, scenario_id, UUID(revision_raw))
    try:
        result, _, _ = _calculate(operation, payload)
    except DomainError as exc:
        return P15ValidationResponse(valid=False, errors=_validation_errors(exc), warnings=[])
    snapshot = _input_snapshot(scenario=scenario, revision=revision, payload=payload)
    raw_groups = result.get("groups")
    raw_alternatives = result.get("alternatives")
    return P15ValidationResponse(
        valid=True,
        errors=[],
        warnings=_validation_warnings(result),
        normalized_input=snapshot,
        preview={
            "operation": operation,
            "result_sha256": result.get("result_sha256"),
            "group_count": len(raw_groups) if isinstance(raw_groups, list) else None,
            "alternative_count": len(raw_alternatives)
            if isinstance(raw_alternatives, list)
            else None,
        },
    )


def _run_for_scope(
    session: Session,
    context: SessionContext,
    run_id: UUID,
    operation: str,
) -> BiologicalReirradiationRun:
    run = session.scalar(
        select(BiologicalReirradiationRun).where(
            BiologicalReirradiationRun.id == run_id,
            BiologicalReirradiationRun.organization_id == context.organization_id,
            BiologicalReirradiationRun.operation_type == operation,
        )
    )
    if run is None:
        raise DomainError(
            "P15_RUN_NOT_FOUND",
            "The P15 calculation was not found in the current organization.",
            404,
        )
    return run


def _list_runs(
    *,
    operation: str,
    organization_id: UUID,
    scenario_id: UUID | None,
    offset: int,
    limit: int,
    identity: AuthenticatedIdentity,
    session: Session,
) -> P15CollectionResponse:
    context = _context_for_organization(organization_id, identity, session)
    query = select(BiologicalReirradiationRun).where(
        BiologicalReirradiationRun.organization_id == context.organization_id,
        BiologicalReirradiationRun.operation_type == operation,
    )
    count_query = (
        select(func.count())
        .select_from(BiologicalReirradiationRun)
        .where(
            BiologicalReirradiationRun.organization_id == context.organization_id,
            BiologicalReirradiationRun.operation_type == operation,
        )
    )
    if scenario_id is not None:
        query = query.where(BiologicalReirradiationRun.scenario_id == scenario_id)
        count_query = count_query.where(BiologicalReirradiationRun.scenario_id == scenario_id)
    runs = session.scalars(
        query.order_by(BiologicalReirradiationRun.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return P15CollectionResponse(
        items=[_response(run) for run in runs],
        total=session.scalar(count_query) or 0,
        offset=offset,
        limit=limit,
    )


def _export(
    run: BiologicalReirradiationRun,
    export_format: Literal["JSON", "CSV"],
) -> Response:
    root = f"rt-connect-p15-{run.operation_type.lower()}-{run.id}"
    if export_format == "JSON":
        content = json.dumps(
            {
                "schema_version": "biological-p15-export.v1",
                "id": str(run.id),
                "organization_id": str(run.organization_id),
                "scenario_id": str(run.scenario_id),
                "scenario_revision_id": str(run.scenario_revision_id),
                "operation_type": run.operation_type,
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
        )
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{root}.json"'},
        )
    output = io.StringIO()
    writer = csv.writer(output)
    result = run.result_snapshot
    if run.operation_type == "REIRRADIATION":
        writer.writerow(
            [
                "operation_type",
                "row_type",
                "group_key",
                "tissue_key",
                "bed_no_recovery_gy",
                "bed_with_recovery_gy",
                "eqd2_no_recovery_gy",
                "eqd2_with_recovery_gy",
                "result_sha256",
            ]
        )
        groups = result.get("groups")
        if isinstance(groups, list):
            for item in groups:
                if isinstance(item, dict):
                    writer.writerow(
                        [
                            run.operation_type,
                            "GROUP",
                            item.get("group_key"),
                            item.get("tissue_key"),
                            item.get("bed_no_recovery_gy"),
                            item.get("bed_with_recovery_gy"),
                            item.get("eqd2_no_recovery_gy"),
                            item.get("eqd2_with_recovery_gy"),
                            result.get("result_sha256"),
                        ]
                    )
    else:
        writer.writerow(
            [
                "operation_type",
                "row_type",
                "alternative_id",
                "label",
                "bed_lq_gy",
                "eqd2_lq_gy",
                "bed_after_time_model_gy",
                "eqd2_after_time_model_gy",
                "result_sha256",
            ]
        )
        alternatives = result.get("alternatives")
        if isinstance(alternatives, list):
            for item in alternatives:
                if isinstance(item, dict):
                    writer.writerow(
                        [
                            run.operation_type,
                            "ALTERNATIVE",
                            item.get("alternative_id"),
                            item.get("label"),
                            item.get("bed_lq_gy"),
                            item.get("eqd2_lq_gy"),
                            item.get("bed_after_time_model_gy"),
                            item.get("eqd2_after_time_model_gy"),
                            result.get("result_sha256"),
                        ]
                    )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{root}.csv"'},
    )


@router.post(
    "/scenarios/{scenario_id}/re-irradiation/validate",
    response_model=P15ValidationResponse,
)
def validate_re_irradiation(
    request: ReIrradiationRequest,
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15ValidationResponse:
    return _validate(
        operation="REIRRADIATION",
        request=request,
        organization_id=organization_id,
        scenario_id=scenario_id,
        identity=identity,
        session=session,
    )


@router.post(
    "/scenarios/{scenario_id}/re-irradiation",
    response_model=P15RunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_re_irradiation(
    request: ReIrradiationRequest,
    scenario_id: UUID,
    organization_id: UUID,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15RunResponse:
    return _create_run(
        operation="REIRRADIATION",
        request=request,
        organization_id=organization_id,
        scenario_id=scenario_id,
        response=response,
        identity=identity,
        session=session,
    )


@router.get("/re-irradiation", response_model=P15CollectionResponse)
def list_re_irradiation(
    organization_id: UUID,
    scenario_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15CollectionResponse:
    return _list_runs(
        operation="REIRRADIATION",
        organization_id=organization_id,
        scenario_id=scenario_id,
        offset=offset,
        limit=limit,
        identity=identity,
        session=session,
    )


@router.get("/re-irradiation/{run_id}", response_model=P15RunResponse)
def get_re_irradiation(
    run_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15RunResponse:
    context = _context_for_organization(organization_id, identity, session)
    return _response(_run_for_scope(session, context, run_id, "REIRRADIATION"))


@router.get("/re-irradiation/{run_id}/export")
def export_re_irradiation(
    run_id: UUID,
    organization_id: UUID,
    export_format: Literal["JSON", "CSV"] = Query(default="JSON"),  # noqa: B008
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> Response:
    context = _context_for_organization(organization_id, identity, session)
    return _export(_run_for_scope(session, context, run_id, "REIRRADIATION"), export_format)


@router.post(
    "/scenarios/{scenario_id}/fraction-compensation/validate",
    response_model=P15ValidationResponse,
)
def validate_fraction_compensation(
    request: FractionCompensationRequest,
    scenario_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15ValidationResponse:
    return _validate(
        operation="FRACTION_COMPENSATION",
        request=request,
        organization_id=organization_id,
        scenario_id=scenario_id,
        identity=identity,
        session=session,
    )


@router.post(
    "/scenarios/{scenario_id}/fraction-compensation",
    response_model=P15RunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_fraction_compensation(
    request: FractionCompensationRequest,
    scenario_id: UUID,
    organization_id: UUID,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15RunResponse:
    return _create_run(
        operation="FRACTION_COMPENSATION",
        request=request,
        organization_id=organization_id,
        scenario_id=scenario_id,
        response=response,
        identity=identity,
        session=session,
    )


@router.get("/fraction-compensation", response_model=P15CollectionResponse)
def list_fraction_compensation(
    organization_id: UUID,
    scenario_id: UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15CollectionResponse:
    return _list_runs(
        operation="FRACTION_COMPENSATION",
        organization_id=organization_id,
        scenario_id=scenario_id,
        offset=offset,
        limit=limit,
        identity=identity,
        session=session,
    )


@router.get("/fraction-compensation/{run_id}", response_model=P15RunResponse)
def get_fraction_compensation(
    run_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> P15RunResponse:
    context = _context_for_organization(organization_id, identity, session)
    return _response(_run_for_scope(session, context, run_id, "FRACTION_COMPENSATION"))


@router.get("/fraction-compensation/{run_id}/export")
def export_fraction_compensation(
    run_id: UUID,
    organization_id: UUID,
    export_format: Literal["JSON", "CSV"] = Query(default="JSON"),  # noqa: B008
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> Response:
    context = _context_for_organization(organization_id, identity, session)
    return _export(_run_for_scope(session, context, run_id, "FRACTION_COMPENSATION"), export_format)
