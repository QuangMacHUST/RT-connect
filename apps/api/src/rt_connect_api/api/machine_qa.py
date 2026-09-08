"""P7 Machine QA protocol, evaluation and history endpoints."""

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    MachineQARun,
    QACase,
    QAProtocolRule,
    QAProtocolVersion,
    TrendPoint,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["machine-qa"])


class MeasurementInput(BaseModel):
    metric_key: str = Field(min_length=1, max_length=120)
    value: float | None = None
    unit: str = Field(min_length=1, max_length=40)
    note: str | None = Field(default=None, max_length=1000)
    context: dict[str, str] = Field(default_factory=dict)


class MeasurementPatchRequest(BaseModel):
    measurements: list[MeasurementInput] = Field(default_factory=list)
    expected_revision: int | None = Field(default=None, ge=0)


class MachineQARunCreateRequest(BaseModel):
    protocol_version_id: UUID | None = None
    measurements: list[MeasurementInput] = Field(default_factory=list)


class ProtocolRuleResponse(BaseModel):
    id: UUID
    metric_key: str
    display_name: str
    unit: str
    rule_type: str
    target_value: float | None
    lower_limit: float | None
    upper_limit: float | None
    tolerance: float | None
    action_level: float | None
    required: bool
    sort_order: int
    note: str | None
    reference: str | None


class ProtocolResponse(BaseModel):
    id: UUID
    organization_id: UUID
    protocol_key: str
    name: str
    qa_type: str
    version_number: int
    status: str
    revision: int
    description: str | None
    effective_note: str | None
    applicability: dict[str, object]
    source_type: str
    source_reference: str | None
    source_protocol_version_id: UUID | None
    created_by_user_identity_id: UUID | None
    created_at: datetime
    updated_at: datetime
    rules: list[ProtocolRuleResponse]


class MachineQARunResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qa_case_id: UUID
    machine_id: UUID
    protocol_version_id: UUID
    status: str
    overall_status: str | None
    measurement_revision: int
    measurements: list[dict[str, object]]
    result_snapshot: dict[str, object]
    error_snapshot: list[dict[str, object]]
    supersedes_run_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    protocol: ProtocolResponse


class RunCollectionResponse(BaseModel):
    items: list[MachineQARunResponse]
    total: int


class ProtocolCollectionResponse(BaseModel):
    items: list[ProtocolResponse]
    total: int


class CompareMetricResponse(BaseModel):
    metric_key: str
    left: dict[str, object] | None
    right: dict[str, object] | None


class CompareResponse(BaseModel):
    left_run_id: UUID
    right_run_id: UUID
    items: list[CompareMetricResponse]


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


def _actor(session: Session, context: SessionContext) -> UUID | None:
    identity = session.scalar(
        select(UserIdentity).where(UserIdentity.supabase_user_id == context.subject)
    )
    return identity.id if identity else None


def _protocol_rules(
    session: Session, protocol_id: UUID, organization_id: UUID
) -> list[QAProtocolRule]:
    return list(
        session.scalars(
            select(QAProtocolRule)
            .where(
                QAProtocolRule.protocol_version_id == protocol_id,
                QAProtocolRule.organization_id == organization_id,
            )
            .order_by(QAProtocolRule.sort_order, QAProtocolRule.metric_key)
        )
    )


def _protocol_response(
    protocol: QAProtocolVersion, rules: list[QAProtocolRule] | None = None
) -> ProtocolResponse:
    return ProtocolResponse(
        id=protocol.id,
        organization_id=protocol.organization_id,
        protocol_key=protocol.protocol_key,
        name=protocol.name,
        qa_type=protocol.qa_type,
        version_number=protocol.version_number,
        status=protocol.status,
        revision=protocol.revision,
        description=protocol.description,
        effective_note=protocol.effective_note,
        applicability=protocol.applicability,
        source_type=protocol.source_type,
        source_reference=protocol.source_reference,
        source_protocol_version_id=protocol.source_protocol_version_id,
        created_by_user_identity_id=protocol.created_by_user_identity_id,
        created_at=protocol.created_at,
        updated_at=protocol.updated_at,
        rules=[
            ProtocolRuleResponse(
                id=rule.id,
                metric_key=rule.metric_key,
                display_name=rule.display_name,
                unit=rule.unit,
                rule_type=rule.rule_type,
                target_value=rule.target_value,
                lower_limit=rule.lower_limit,
                upper_limit=rule.upper_limit,
                tolerance=rule.tolerance,
                action_level=rule.action_level,
                required=rule.required,
                sort_order=rule.sort_order,
                note=rule.note,
                reference=rule.reference,
            )
            for rule in rules or []
        ],
    )


def _run_response(session: Session, run: MachineQARun) -> MachineQARunResponse:
    protocol = session.scalar(
        select(QAProtocolVersion).where(
            QAProtocolVersion.id == run.protocol_version_id,
            QAProtocolVersion.organization_id == run.organization_id,
        )
    )
    if protocol is None:
        raise DomainError("QA_PROTOCOL_NOT_FOUND", "The run protocol no longer exists.", 500)
    return MachineQARunResponse(
        id=run.id,
        organization_id=run.organization_id,
        qa_case_id=run.qa_case_id,
        machine_id=run.machine_id,
        protocol_version_id=run.protocol_version_id,
        status=run.status,
        overall_status=run.overall_status,
        measurement_revision=run.measurement_revision,
        measurements=run.measurements,
        result_snapshot=run.result_snapshot,
        error_snapshot=run.error_snapshot,
        supersedes_run_id=run.supersedes_run_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        protocol=_protocol_response(
            protocol, _protocol_rules(session, protocol.id, run.organization_id)
        ),
    )


def _normalise_measurements(measurements: list[MeasurementInput]) -> list[dict[str, object]]:
    allowed_context_keys = {"energy", "detector", "phantom", "beam_quality", "acquisition_mode"}
    keys: set[str] = set()
    normalised: list[dict[str, object]] = []
    for measurement in measurements:
        if measurement.metric_key in keys:
            raise DomainError(
                "MACHINE_QA_DUPLICATE_METRIC",
                f"Metric {measurement.metric_key} is present more than once.",
                422,
            )
        keys.add(measurement.metric_key)
        if measurement.value is not None and not isfinite(measurement.value):
            raise DomainError(
                "MACHINE_QA_VALUE_INVALID",
                f"Metric {measurement.metric_key} must contain a finite numeric value.",
                422,
            )
        unknown_context = set(measurement.context) - allowed_context_keys
        if unknown_context:
            raise DomainError(
                "MACHINE_QA_CONTEXT_INVALID",
                f"Metric {measurement.metric_key} contains unsupported context fields.",
                422,
                details=[
                    {"field": "context", "message": "Use the published trend context fields."}
                ],
            )
        normalised.append(
            {
                "metric_key": measurement.metric_key,
                "value": measurement.value,
                "unit": measurement.unit,
                "note": measurement.note,
                "context": dict(sorted(measurement.context.items())),
            }
        )
    return normalised


def _seed_protocol(
    session: Session, context: SessionContext, actor_id: UUID | None
) -> QAProtocolVersion:
    existing = session.scalar(
        select(QAProtocolVersion).where(
            QAProtocolVersion.organization_id == context.organization_id,
            QAProtocolVersion.protocol_key == "MACHINE_QA_BASELINE",
            QAProtocolVersion.version_number == 1,
        )
    )
    if existing is not None:
        return existing
    protocol = QAProtocolVersion(
        organization_id=context.organization_id,
        protocol_key="MACHINE_QA_BASELINE",
        name="Machine QA baseline",
        qa_type="Machine QA",
        version_number=1,
        status="ACTIVE",
        effective_note="Synthetic seed protocol for P7; create governed versions in P11.",
        created_by_user_identity_id=actor_id,
    )
    session.add(protocol)
    session.flush()
    seed_rules = [
        {
            "metric_key": "output_factor",
            "display_name": "Output factor",
            "unit": "%",
            "rule_type": "RANGE",
            "lower_limit": 98.0,
            "upper_limit": 102.0,
            "action_level": 1.0,
            "note": "Pass band 98–102%; warning band expands by 1%. ",
        },
        {
            "metric_key": "symmetry",
            "display_name": "Symmetry",
            "unit": "%",
            "rule_type": "ABSOLUTE_DEVIATION",
            "target_value": 0.0,
            "tolerance": 2.0,
            "action_level": 3.0,
            "note": "Absolute deviation from zero.",
        },
        {
            "metric_key": "flatness",
            "display_name": "Flatness",
            "unit": "%",
            "rule_type": "RANGE",
            "lower_limit": 95.0,
            "upper_limit": 105.0,
            "action_level": 2.0,
            "note": "Synthetic seed rule; replace with site-approved protocol.",
        },
    ]
    for order, values in enumerate(seed_rules):
        session.add(
            QAProtocolRule(
                organization_id=context.organization_id,
                protocol_version_id=protocol.id,
                sort_order=order,
                **values,
            )
        )
    session.commit()
    session.refresh(protocol)
    return protocol


def _protocol_or_error(
    session: Session, organization_id: UUID, protocol_id: UUID | None
) -> QAProtocolVersion:
    if protocol_id is None:
        raise DomainError("QA_PROTOCOL_REQUIRED", "A QA protocol version is required.", 422)
    protocol = session.scalar(
        select(QAProtocolVersion).where(
            QAProtocolVersion.id == protocol_id,
            QAProtocolVersion.organization_id == organization_id,
        )
    )
    if protocol is None:
        raise DomainError("QA_PROTOCOL_NOT_FOUND", "The QA protocol version was not found.", 404)
    if protocol.status != "ACTIVE":
        raise DomainError("QA_PROTOCOL_INACTIVE", "The selected QA protocol is not active.", 409)
    return protocol


def _case_or_error(session: Session, case_id: UUID, organization_id: UUID) -> QACase:
    case = session.scalar(
        select(QACase).where(QACase.id == case_id, QACase.organization_id == organization_id)
    )
    if case is None:
        raise DomainError(
            "QA_CASE_NOT_FOUND", "The QA case was not found in this organization.", 404
        )
    if case.is_archived:
        raise DomainError(
            "QA_CASE_ARCHIVED", "Archived QA cases cannot create a Machine QA run.", 409
        )
    return case


def _run_or_error(
    session: Session, run_id: UUID, identity: AuthenticatedIdentity
) -> tuple[MachineQARun, SessionContext]:
    context = resolve_session_context(session, identity)
    run = session.scalar(
        select(MachineQARun).where(
            MachineQARun.id == run_id,
            MachineQARun.organization_id == context.organization_id,
        )
    )
    if run is None:
        raise DomainError("MACHINE_QA_RUN_NOT_FOUND", "The Machine QA run was not found.", 404)
    return run, context


def _rule_snapshot(rule: QAProtocolRule) -> dict[str, object]:
    return {
        "id": str(rule.id),
        "metric_key": rule.metric_key,
        "display_name": rule.display_name,
        "unit": rule.unit,
        "rule_type": rule.rule_type,
        "target_value": rule.target_value,
        "lower_limit": rule.lower_limit,
        "upper_limit": rule.upper_limit,
        "tolerance": rule.tolerance,
        "action_level": rule.action_level,
        "required": rule.required,
        "sort_order": rule.sort_order,
        "note": rule.note,
    }


def _evaluate_rule(rule: QAProtocolRule, measurement: dict[str, object]) -> dict[str, object]:
    raw_value = measurement.get("value")
    value = float(raw_value) if isinstance(raw_value, int | float) else None
    result: dict[str, object] = {
        "metric_key": rule.metric_key,
        "display_name": rule.display_name,
        "actual": value,
        "unit": measurement.get("unit"),
        "baseline": rule.target_value,
        "tolerance": rule.tolerance,
        "action_level": rule.action_level,
        "margin": None,
        "status": "REVIEW",
        "rule_snapshot": _rule_snapshot(rule),
    }
    if rule.rule_type == "NA":
        result["status"] = "NA"
        return result
    if value is None:
        return result

    if rule.rule_type == "RANGE":
        if rule.lower_limit is None or rule.upper_limit is None:
            result["status"] = "REVIEW"
            return result
        margin = min(value - rule.lower_limit, rule.upper_limit - value)
        result["margin"] = margin
        if margin >= 0:
            result["status"] = "PASS"
        elif rule.action_level is not None and margin >= -rule.action_level:
            result["status"] = "WARNING"
        else:
            result["status"] = "FAIL"
        return result

    if rule.rule_type == "MAX":
        limit = rule.upper_limit if rule.upper_limit is not None else rule.tolerance
        if limit is None:
            return result
        margin = limit - value
        result["margin"] = margin
        result["status"] = (
            "PASS"
            if margin >= 0
            else (
                "WARNING"
                if rule.action_level is not None and margin >= -rule.action_level
                else "FAIL"
            )
        )
        return result

    if rule.rule_type == "MIN":
        limit = rule.lower_limit if rule.lower_limit is not None else rule.tolerance
        if limit is None:
            return result
        margin = value - limit
        result["margin"] = margin
        result["status"] = (
            "PASS"
            if margin >= 0
            else (
                "WARNING"
                if rule.action_level is not None and margin >= -rule.action_level
                else "FAIL"
            )
        )
        return result

    if rule.rule_type in {"ABSOLUTE_DEVIATION", "PERCENT_DEVIATION"}:
        if rule.target_value is None or rule.tolerance is None:
            return result
        denominator = abs(rule.target_value)
        deviation = abs(value - rule.target_value)
        if rule.rule_type == "PERCENT_DEVIATION":
            if denominator == 0:
                return result
            deviation = deviation / denominator * 100
        margin = rule.tolerance - deviation
        result["margin"] = margin
        result["deviation"] = deviation
        result["status"] = (
            "PASS"
            if margin >= 0
            else (
                "WARNING"
                if rule.action_level is not None and deviation <= rule.action_level
                else "FAIL"
            )
        )
        return result

    return result


def _evaluate_run(
    session: Session, run: MachineQARun, case: QACase, protocol: QAProtocolVersion
) -> None:
    rules = _protocol_rules(session, protocol.id, run.organization_id)
    if not rules:
        run.status = "FAILED"
        run.error_snapshot = [
            {"code": "MACHINE_QA_RULES_EMPTY", "message": "Protocol has no rules."}
        ]
        run.completed_at = datetime.now(UTC)
        return

    by_key = {str(item.get("metric_key")): item for item in run.measurements}
    errors: list[dict[str, object]] = []
    metrics: list[dict[str, object]] = []
    for rule in rules:
        measurement = by_key.get(rule.metric_key)
        if measurement is None:
            if rule.required:
                errors.append(
                    {
                        "code": "MACHINE_QA_MEASUREMENT_MISSING",
                        "metric_key": rule.metric_key,
                        "message": f"Required metric {rule.display_name} is missing.",
                    }
                )
            continue
        if measurement.get("unit") != rule.unit:
            errors.append(
                {
                    "code": "MACHINE_QA_UNIT_MISMATCH",
                    "metric_key": rule.metric_key,
                    "expected": rule.unit,
                    "actual": measurement.get("unit"),
                    "message": f"Metric {rule.display_name} has an incompatible unit.",
                }
            )
            continue
        if measurement.get("value") is None and rule.required and rule.rule_type != "NA":
            errors.append(
                {
                    "code": "MACHINE_QA_VALUE_MISSING",
                    "metric_key": rule.metric_key,
                    "message": f"Required metric {rule.display_name} has no value.",
                }
            )
            continue
        metric_result = _evaluate_rule(rule, measurement)
        metric_result["context"] = measurement.get("context", {})
        metrics.append(metric_result)

    run.started_at = run.started_at or datetime.now(UTC)
    run.completed_at = datetime.now(UTC)
    run.error_snapshot = errors
    run.result_snapshot = {
        "protocol_snapshot": {
            "id": str(protocol.id),
            "protocol_key": protocol.protocol_key,
            "name": protocol.name,
            "version_number": protocol.version_number,
            "rules": [_rule_snapshot(rule) for rule in rules],
        },
        "metrics": metrics,
        "evaluated_at": run.completed_at.isoformat(),
    }
    if errors:
        run.status = "FAILED"
        run.overall_status = None
        return

    statuses = {str(metric["status"]) for metric in metrics}
    run.overall_status = (
        "FAIL" if "FAIL" in statuses else "WARNING" if "WARNING" in statuses else "PASS"
    )
    run.status = "COMPLETED"
    for metric in metrics:
        actual = metric.get("actual")
        if isinstance(actual, int | float) and isfinite(float(actual)):
            metric_context = metric.get("context")
            context_snapshot: dict[str, object] = {
                "qa_type": case.qa_type,
                "qa_cycle": case.qa_cycle,
                "protocol_key": protocol.protocol_key,
                "protocol_version": protocol.version_number,
            }
            if isinstance(metric_context, dict):
                context_snapshot.update(
                    {
                        str(key): value
                        for key, value in metric_context.items()
                        if isinstance(value, str)
                    }
                )
            session.add(
                TrendPoint(
                    organization_id=run.organization_id,
                    machine_id=run.machine_id,
                    qa_case_id=run.qa_case_id,
                    source_run_id=run.id,
                    metric_key=str(metric["metric_key"]),
                    value=float(actual),
                    unit=str(metric["unit"]),
                    status=str(metric["status"]),
                    measured_at=case.performed_at,
                    context_snapshot=context_snapshot,
                )
            )


def _metric_items(snapshot: dict[str, object]) -> list[dict[str, object]]:
    raw_metrics = snapshot.get("metrics", [])
    if not isinstance(raw_metrics, list):
        return []
    return [item for item in raw_metrics if isinstance(item, dict)]


@router.get(
    "/organizations/{organization_id}/machine-qa/protocols",
    response_model=ProtocolCollectionResponse,
)
def list_protocols(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    protocols = list(
        session.scalars(
            select(QAProtocolVersion)
            .where(QAProtocolVersion.organization_id == organization_id)
            .where(QAProtocolVersion.status == "ACTIVE")
            .order_by(QAProtocolVersion.protocol_key, QAProtocolVersion.version_number.desc())
        )
    )
    return ProtocolCollectionResponse(
        items=[
            _protocol_response(item, _protocol_rules(session, item.id, organization_id))
            for item in protocols
        ],
        total=len(protocols),
    )


@router.post(
    "/organizations/{organization_id}/machine-qa/protocols/seed",
    response_model=ProtocolResponse,
    status_code=status.HTTP_201_CREATED,
)
def seed_protocol(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolResponse:
    context = _context_for_organization(organization_id, identity, session)
    protocol = _seed_protocol(session, context, _actor(session, context))
    return _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))


@router.post(
    "/qa-cases/{case_id}/machine-qa-runs",
    response_model=MachineQARunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_run(
    case_id: UUID,
    payload: MachineQARunCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> MachineQARunResponse:
    context = resolve_session_context(session, identity)
    case = _case_or_error(session, case_id, context.organization_id)
    protocol = _protocol_or_error(session, context.organization_id, payload.protocol_version_id)
    measurements = _normalise_measurements(payload.measurements)
    run = MachineQARun(
        organization_id=context.organization_id,
        qa_case_id=case.id,
        machine_id=case.machine_id,
        protocol_version_id=protocol.id,
        measurements=measurements,
        result_snapshot={},
        error_snapshot=[],
        created_by_user_identity_id=_actor(session, context),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return _run_response(session, run)


@router.get("/qa-cases/{case_id}/machine-qa-runs", response_model=RunCollectionResponse)
def list_runs(
    case_id: UUID,
    include_failed: bool = Query(default=True),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> RunCollectionResponse:
    context = resolve_session_context(session, identity)
    _case_or_error(session, case_id, context.organization_id)
    query = select(MachineQARun).where(
        MachineQARun.qa_case_id == case_id,
        MachineQARun.organization_id == context.organization_id,
    )
    if not include_failed:
        query = query.where(MachineQARun.status != "FAILED")
    runs = list(session.scalars(query.order_by(MachineQARun.created_at.desc())))
    return RunCollectionResponse(
        items=[_run_response(session, run) for run in runs], total=len(runs)
    )


@router.get("/machine-qa-runs/{run_id}", response_model=MachineQARunResponse)
def get_run(
    run_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> MachineQARunResponse:
    run, _ = _run_or_error(session, run_id, identity)
    return _run_response(session, run)


@router.patch("/machine-qa-runs/{run_id}/measurements", response_model=MachineQARunResponse)
def update_measurements(
    run_id: UUID,
    payload: MeasurementPatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> MachineQARunResponse:
    run, _ = _run_or_error(session, run_id, identity)
    if run.status != "DRAFT":
        raise DomainError(
            "MACHINE_QA_RUN_IMMUTABLE",
            "Completed or failed runs cannot be edited.",
            409,
        )
    if (
        payload.expected_revision is not None
        and payload.expected_revision != run.measurement_revision
    ):
        raise DomainError(
            "MACHINE_QA_REVISION_CONFLICT",
            "The measurement draft has changed; reload before saving.",
            409,
        )
    run.measurements = _normalise_measurements(payload.measurements)
    run.measurement_revision += 1
    session.commit()
    session.refresh(run)
    return _run_response(session, run)


@router.post("/machine-qa-runs/{run_id}/evaluate", response_model=MachineQARunResponse)
def evaluate_run(
    run_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> MachineQARunResponse:
    run, _ = _run_or_error(session, run_id, identity)
    if run.status == "COMPLETED":
        return _run_response(session, run)
    if run.status != "DRAFT":
        raise DomainError("MACHINE_QA_RUN_IMMUTABLE", "This run cannot be evaluated again.", 409)
    context = resolve_session_context(session, identity)
    case = _case_or_error(session, run.qa_case_id, context.organization_id)
    protocol = _protocol_or_error(session, context.organization_id, run.protocol_version_id)
    _evaluate_run(session, run, case, protocol)
    session.commit()
    session.refresh(run)
    return _run_response(session, run)


@router.post(
    "/machine-qa-runs/{run_id}/rerun", response_model=MachineQARunResponse, status_code=201
)
def rerun(
    run_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> MachineQARunResponse:
    source, context = _run_or_error(session, run_id, identity)
    if source.status == "DRAFT":
        raise DomainError("MACHINE_QA_RUN_NOT_COMPLETED", "Only a completed run can be rerun.", 409)
    case = _case_or_error(session, source.qa_case_id, context.organization_id)
    protocol = _protocol_or_error(session, context.organization_id, source.protocol_version_id)
    new_run = MachineQARun(
        organization_id=context.organization_id,
        qa_case_id=case.id,
        machine_id=case.machine_id,
        protocol_version_id=protocol.id,
        measurements=list(source.measurements),
        result_snapshot={},
        error_snapshot=[],
        supersedes_run_id=source.id,
        created_by_user_identity_id=_actor(session, context),
    )
    session.add(new_run)
    session.commit()
    session.refresh(new_run)
    return _run_response(session, new_run)


@router.get("/machine-qa-runs/{run_id}/compare", response_model=CompareResponse)
def compare_runs(
    run_id: UUID,
    other_run_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> CompareResponse:
    left, context = _run_or_error(session, run_id, identity)
    right = session.scalar(
        select(MachineQARun).where(
            MachineQARun.id == other_run_id,
            MachineQARun.organization_id == context.organization_id,
        )
    )
    if right is None:
        raise DomainError("MACHINE_QA_RUN_NOT_FOUND", "The comparison run was not found.", 404)
    left_metrics = {
        str(item.get("metric_key")): item
        for item in _metric_items(left.result_snapshot)
        if isinstance(item, dict) and item.get("metric_key")
    }
    right_metrics = {
        str(item.get("metric_key")): item
        for item in _metric_items(right.result_snapshot)
        if isinstance(item, dict) and item.get("metric_key")
    }
    return CompareResponse(
        left_run_id=left.id,
        right_run_id=right.id,
        items=[
            CompareMetricResponse(
                metric_key=key,
                left=left_metrics.get(key),
                right=right_metrics.get(key),
            )
            for key in sorted(set(left_metrics) | set(right_metrics))
        ],
    )
