"""P10 trend, baseline and maintenance-event workflows.

Trend points are a read model emitted by completed Machine QA runs.  The
source run/case remains authoritative; this module never rewrites a QA result.
Every query resolves the authenticated organization before looking up a point,
machine, baseline or event.
"""

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, time, timedelta
from math import isfinite
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.config import Settings, get_settings
from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    BaselineVersion,
    Machine,
    MachineQARun,
    MaintenanceEvent,
    MaintenanceEventRevision,
    QACase,
    TrendPoint,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["trend"])

TrendAggregate = Literal["raw", "day", "week"]
BaselineStatus = Literal["ACTIVE", "ARCHIVED"]
ExportFormat = Literal["CSV", "JSON"]

CONTEXT_KEYS = {
    "energy",
    "detector",
    "phantom",
    "beam_quality",
    "acquisition_mode",
}
SIGNATURE_KEYS = (
    "qa_type",
    "qa_cycle",
    "protocol_key",
    "protocol_version",
    "energy",
    "detector",
    "phantom",
    "beam_quality",
    "acquisition_mode",
)


class BaselineCreateRequest(BaseModel):
    machine_id: UUID
    metric_key: str = Field(min_length=1, max_length=120)
    unit: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=240)
    version_number: int | None = Field(default=None, ge=1)
    baseline_value: float
    tolerance: float | None = Field(default=None, ge=0)
    action_level: float | None = Field(default=None, ge=0)
    effective_from: datetime
    effective_to: datetime | None = None
    status: BaselineStatus = "ACTIVE"
    source_type: str = Field(default="MANUAL", min_length=1, max_length=40)
    source_id: UUID | None = None
    context: dict[str, str] = Field(default_factory=dict)


class BaselinePatchRequest(BaseModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=240)
    tolerance: float | None = Field(default=None, ge=0)
    action_level: float | None = Field(default=None, ge=0)
    effective_to: datetime | None = None
    status: BaselineStatus | None = None


class BaselineResponse(BaseModel):
    id: UUID
    organization_id: UUID
    machine_id: UUID
    metric_key: str
    unit: str
    name: str
    version_number: int
    baseline_value: float
    tolerance: float | None
    action_level: float | None
    effective_from: datetime
    effective_to: datetime | None
    status: str
    source_type: str
    source_id: UUID | None
    context: dict[str, object]
    created_at: datetime
    updated_at: datetime


class MaintenanceCreateRequest(BaseModel):
    machine_id: UUID
    event_type: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=240)
    started_at: datetime
    ended_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    metadata: dict[str, str] = Field(default_factory=dict)


class MaintenancePatchRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    event_type: str | None = Field(default=None, min_length=1, max_length=60)
    title: str | None = Field(default=None, min_length=1, max_length=240)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=4000)
    metadata: dict[str, str] | None = None
    status: Literal["ACTIVE", "ARCHIVED"] | None = None


class MaintenanceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    machine_id: UUID
    machine_name: str
    event_type: str
    title: str
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    revision_number: int
    status: str
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime


class MaintenanceRevisionResponse(BaseModel):
    id: UUID
    maintenance_event_id: UUID
    revision_number: int
    event_type: str
    title: str
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    status: str
    metadata: dict[str, object]
    created_at: datetime


class TrendPointResponse(BaseModel):
    id: UUID
    machine_id: UUID
    machine_name: str
    qa_case_id: UUID
    source_run_id: UUID
    metric_key: str
    value: float
    unit: str
    status: str
    measured_at: datetime
    context: dict[str, object]
    compatibility_signature: str
    source_archived: bool
    source_status: str
    baseline_value: float | None
    baseline_delta: float | None
    is_outlier: bool


class TrendBucketResponse(BaseModel):
    start_at: datetime
    end_at: datetime
    count: int
    mean: float
    minimum: float
    maximum: float
    first_value: float
    last_value: float
    statuses: dict[str, int]
    source_point_ids: list[UUID]
    source_run_ids: list[UUID]


class TrendSeriesResponse(BaseModel):
    machine_id: UUID
    machine_name: str
    metric_key: str
    unit: str
    context: dict[str, object]
    compatibility_signature: str
    baseline: BaselineResponse | None
    points: list[TrendPointResponse]
    buckets: list[TrendBucketResponse]


class TrendResponse(BaseModel):
    organization_id: UUID
    timezone: str
    aggregate: TrendAggregate
    from_at: datetime | None
    to_at: datetime | None
    total_points: int
    series: list[TrendSeriesResponse]
    maintenance_events: list[MaintenanceResponse]
    baselines: list[BaselineResponse]
    warnings: list[str]


class TrendRebuildResponse(BaseModel):
    organization_id: UUID
    scanned_runs: int
    created_points: int
    existing_points: int
    repaired_context_points: int


class _SourceRow:
    def __init__(
        self, point: TrendPoint, machine: Machine, case: QACase, run: MachineQARun
    ) -> None:
        self.point = point
        self.machine = machine
        self.case = case
        self.run = run


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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _as_utc(value).isoformat()


def _validate_timezone(value: str) -> ZoneInfo:
    try:
        return ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise DomainError(
            "TREND_TIMEZONE_INVALID", "The requested timezone is not available.", 422
        ) from exc


def _validate_context(context: dict[str, str], field: str = "context") -> dict[str, str]:
    unknown = set(context) - CONTEXT_KEYS
    if unknown:
        raise DomainError(
            "TREND_CONTEXT_INVALID",
            "The supplied context contains unsupported compatibility fields.",
            422,
            details=[
                {
                    "field": field,
                    "message": "Use energy, detector, phantom, beam_quality or acquisition_mode.",
                }
            ],
        )
    return dict(sorted(context.items()))


def _source_context(run: MachineQARun, case: QACase, unit: str) -> dict[str, object]:
    context: dict[str, object] = {
        "qa_type": case.qa_type,
        "qa_cycle": case.qa_cycle,
        "unit": unit,
    }
    snapshot = run.result_snapshot if isinstance(run.result_snapshot, dict) else {}
    protocol = snapshot.get("protocol_snapshot")
    if isinstance(protocol, dict):
        protocol_key = protocol.get("protocol_key")
        version = protocol.get("version_number")
        if isinstance(protocol_key, str):
            context["protocol_key"] = protocol_key
        if isinstance(version, int):
            context["protocol_version"] = version
    return context


def _effective_context(row: _SourceRow) -> dict[str, object]:
    context = _source_context(row.run, row.case, row.point.unit)
    raw = row.point.context_snapshot
    if isinstance(raw, dict):
        context.update({str(key): value for key, value in raw.items()})
    context["unit"] = row.point.unit
    return context


def _signature(context: dict[str, object]) -> str:
    payload = {key: context.get(key) for key in ("unit", *SIGNATURE_KEYS)}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _machine_ids(raw: str | None) -> list[UUID]:
    if not raw:
        return []
    values: list[UUID] = []
    for item in raw.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        try:
            values.append(UUID(candidate))
        except ValueError as exc:
            raise DomainError(
                "TREND_FILTER_INVALID", "machine_ids contains an invalid UUID.", 422
            ) from exc
    return list(dict.fromkeys(values))


def _context_filters(
    energy: str | None,
    detector: str | None,
    phantom: str | None,
    beam_quality: str | None,
    acquisition_mode: str | None,
    protocol_key: str | None,
    qa_cycle: str | None,
) -> dict[str, str]:
    values = {
        key: value
        for key, value in {
            "energy": energy,
            "detector": detector,
            "phantom": phantom,
            "beam_quality": beam_quality,
            "acquisition_mode": acquisition_mode,
            "protocol_key": protocol_key,
            "qa_cycle": qa_cycle,
        }.items()
        if value is not None
    }
    # protocol_key and qa_cycle are first-class compatibility fields, while
    # the user-authored measurement context is restricted by _validate_context.
    return values


def _matches_context(context: dict[str, object], filters: dict[str, str]) -> bool:
    return all(str(context.get(key)) == value for key, value in filters.items())


def _machine_or_error(session: Session, organization_id: UUID, machine_id: UUID) -> Machine:
    machine = session.scalar(
        select(Machine).where(Machine.id == machine_id, Machine.organization_id == organization_id)
    )
    if machine is None:
        raise DomainError(
            "TREND_SOURCE_UNAVAILABLE", "The machine is not in this organization.", 404
        )
    return machine


def _finite_or_error(value: float | None, field: str) -> None:
    if value is not None and not isfinite(value):
        raise DomainError(
            "TREND_BASELINE_INVALID",
            "Baseline values and limits must be finite numbers.",
            422,
            details=[{"field": field, "message": "The value must be finite."}],
        )


def _validate_interval(started_at: datetime, ended_at: datetime | None) -> None:
    if ended_at is not None and _as_utc(ended_at) < _as_utc(started_at):
        raise DomainError(
            "MAINTENANCE_INTERVAL_INVALID", "The event end must not precede its start.", 422
        )


def _baseline_response(baseline: BaselineVersion) -> BaselineResponse:
    return BaselineResponse(
        id=baseline.id,
        organization_id=baseline.organization_id,
        machine_id=baseline.machine_id,
        metric_key=baseline.metric_key,
        unit=baseline.unit,
        name=baseline.name,
        version_number=baseline.version_number,
        baseline_value=baseline.baseline_value,
        tolerance=baseline.tolerance,
        action_level=baseline.action_level,
        effective_from=baseline.effective_from,
        effective_to=baseline.effective_to,
        status=baseline.status,
        source_type=baseline.source_type,
        source_id=baseline.source_id,
        context=baseline.context_snapshot,
        created_at=baseline.created_at,
        updated_at=baseline.updated_at,
    )


def _maintenance_response(
    event: MaintenanceEvent, machine_name: str | None = None
) -> MaintenanceResponse:
    return MaintenanceResponse(
        id=event.id,
        organization_id=event.organization_id,
        machine_id=event.machine_id,
        machine_name=machine_name or "—",
        event_type=event.event_type,
        title=event.title,
        started_at=event.started_at,
        ended_at=event.ended_at,
        notes=event.notes,
        revision_number=event.revision_number,
        status=event.status,
        metadata=event.metadata_snapshot,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _maintenance_revision_response(
    revision: MaintenanceEventRevision,
) -> MaintenanceRevisionResponse:
    return MaintenanceRevisionResponse(
        id=revision.id,
        maintenance_event_id=revision.maintenance_event_id,
        revision_number=revision.revision_number,
        event_type=revision.event_type,
        title=revision.title,
        started_at=revision.started_at,
        ended_at=revision.ended_at,
        notes=revision.notes,
        status=revision.status,
        metadata=revision.metadata_snapshot,
        created_at=revision.created_at,
    )


def _write_event_revision(session: Session, event: MaintenanceEvent, actor_id: UUID | None) -> None:
    session.add(
        MaintenanceEventRevision(
            organization_id=event.organization_id,
            maintenance_event_id=event.id,
            revision_number=event.revision_number,
            event_type=event.event_type,
            title=event.title,
            started_at=event.started_at,
            ended_at=event.ended_at,
            notes=event.notes,
            status=event.status,
            metadata_snapshot=dict(event.metadata_snapshot),
            created_by_user_identity_id=actor_id,
        )
    )


def _baseline_for_point(
    baselines: Iterable[BaselineVersion], context: dict[str, object], measured_at: datetime
) -> BaselineVersion | None:
    candidates: list[BaselineVersion] = []
    measured = _as_utc(measured_at)
    for baseline in baselines:
        if baseline.status != "ACTIVE":
            continue
        if baseline.unit != context.get("unit"):
            continue
        baseline_context = (
            baseline.context_snapshot if isinstance(baseline.context_snapshot, dict) else {}
        )
        if any(context.get(key) != value for key, value in baseline_context.items()):
            continue
        if _as_utc(baseline.effective_from) > measured:
            continue
        if baseline.effective_to is not None and _as_utc(baseline.effective_to) <= measured:
            continue
        candidates.append(baseline)
    return max(
        candidates,
        key=lambda item: (_as_utc(item.effective_from), item.version_number),
        default=None,
    )


def _point_response(
    row: _SourceRow,
    context: dict[str, object],
    baseline: BaselineVersion | None,
) -> TrendPointResponse:
    delta = row.point.value - baseline.baseline_value if baseline is not None else None
    is_outlier = False
    if baseline is not None and delta is not None:
        limit = baseline.action_level if baseline.action_level is not None else baseline.tolerance
        is_outlier = limit is not None and abs(delta) > limit
    return TrendPointResponse(
        id=row.point.id,
        machine_id=row.point.machine_id,
        machine_name=row.machine.display_name,
        qa_case_id=row.point.qa_case_id,
        source_run_id=row.point.source_run_id,
        metric_key=row.point.metric_key,
        value=row.point.value,
        unit=row.point.unit,
        status=row.point.status,
        measured_at=row.point.measured_at,
        context=context,
        compatibility_signature=_signature(context),
        source_archived=bool(row.machine.is_archived or row.case.is_archived),
        source_status=row.run.status,
        baseline_value=baseline.baseline_value if baseline is not None else None,
        baseline_delta=delta,
        is_outlier=is_outlier,
    )


def _bucket_start(value: datetime, aggregate: TrendAggregate, zone: ZoneInfo) -> datetime:
    local = _as_utc(value).astimezone(zone)
    if aggregate == "day":
        local_start = datetime.combine(local.date(), time.min, tzinfo=zone)
    else:
        local_start = datetime.combine(
            local.date() - timedelta(days=local.weekday()), time.min, tzinfo=zone
        )
    return local_start.astimezone(UTC)


def _bucket_end(start: datetime, aggregate: TrendAggregate, zone: ZoneInfo) -> datetime:
    local = _as_utc(start).astimezone(zone)
    delta = timedelta(days=1 if aggregate == "day" else 7)
    return (local + delta).astimezone(UTC)


def _aggregate_points(
    points: list[TrendPointResponse], aggregate: TrendAggregate, zone: ZoneInfo
) -> list[TrendBucketResponse]:
    grouped: dict[datetime, list[TrendPointResponse]] = defaultdict(list)
    for point in points:
        grouped[_bucket_start(point.measured_at, aggregate, zone)].append(point)
    buckets: list[TrendBucketResponse] = []
    for start in sorted(grouped):
        values = grouped[start]
        ordered = sorted(values, key=lambda item: _as_utc(item.measured_at))
        statuses: dict[str, int] = defaultdict(int)
        for item in values:
            statuses[item.status] += 1
        numeric = [item.value for item in values]
        buckets.append(
            TrendBucketResponse(
                start_at=start,
                end_at=_bucket_end(start, aggregate, zone),
                count=len(values),
                mean=sum(numeric) / len(numeric),
                minimum=min(numeric),
                maximum=max(numeric),
                first_value=ordered[0].value,
                last_value=ordered[-1].value,
                statuses=dict(sorted(statuses.items())),
                source_point_ids=[item.id for item in ordered],
                source_run_ids=list(dict.fromkeys(item.source_run_id for item in ordered)),
            )
        )
    return buckets


def _load_source_rows(
    session: Session,
    organization_id: UUID,
    machine_ids: list[UUID],
    metric_key: str | None,
    from_at: datetime | None,
    to_at: datetime | None,
    unit: str | None,
    filters: dict[str, str],
) -> list[_SourceRow]:
    statement = (
        select(TrendPoint, Machine, QACase, MachineQARun)
        .join(
            Machine,
            and_(Machine.id == TrendPoint.machine_id, Machine.organization_id == organization_id),
        )
        .join(
            QACase,
            and_(QACase.id == TrendPoint.qa_case_id, QACase.organization_id == organization_id),
        )
        .join(
            MachineQARun,
            and_(
                MachineQARun.id == TrendPoint.source_run_id,
                MachineQARun.organization_id == organization_id,
            ),
        )
        .where(TrendPoint.organization_id == organization_id)
    )
    if machine_ids:
        statement = statement.where(TrendPoint.machine_id.in_(machine_ids))
    if metric_key:
        statement = statement.where(TrendPoint.metric_key == metric_key)
    if unit:
        statement = statement.where(TrendPoint.unit == unit)
    if from_at is not None:
        statement = statement.where(TrendPoint.measured_at >= _as_utc(from_at))
    if to_at is not None:
        statement = statement.where(TrendPoint.measured_at < _as_utc(to_at))
    rows = [
        _SourceRow(point, machine, case, run)
        for point, machine, case, run in session.execute(statement).all()
    ]
    rows.sort(key=lambda row: (_as_utc(row.point.measured_at), str(row.point.id)))
    matched = [row for row in rows if _matches_context(_effective_context(row), filters)]
    keys: set[tuple[UUID, str]] = set()
    for row in matched:
        key = (row.point.source_run_id, row.point.metric_key)
        if key in keys:
            raise DomainError(
                "TREND_DUPLICATE_SOURCE",
                "The trend projection contains more than one point for a source run and metric.",
                409,
            )
        keys.add(key)
    return matched


def _load_baselines(
    session: Session,
    organization_id: UUID,
    machine_ids: list[UUID],
    metric_key: str | None,
    include_archived: bool,
) -> list[BaselineVersion]:
    statement = select(BaselineVersion).where(BaselineVersion.organization_id == organization_id)
    if machine_ids:
        statement = statement.where(BaselineVersion.machine_id.in_(machine_ids))
    if metric_key:
        statement = statement.where(BaselineVersion.metric_key == metric_key)
    if not include_archived:
        statement = statement.where(BaselineVersion.status == "ACTIVE")
    return list(
        session.scalars(
            statement.order_by(
                BaselineVersion.machine_id,
                BaselineVersion.metric_key,
                BaselineVersion.effective_from,
                BaselineVersion.version_number,
            )
        )
    )


def _load_events(
    session: Session,
    organization_id: UUID,
    machine_ids: list[UUID],
    from_at: datetime | None,
    to_at: datetime | None,
    include_archived: bool,
) -> list[MaintenanceResponse]:
    statement = (
        select(MaintenanceEvent, Machine.display_name)
        .join(
            Machine,
            and_(
                Machine.id == MaintenanceEvent.machine_id,
                Machine.organization_id == organization_id,
            ),
        )
        .where(MaintenanceEvent.organization_id == organization_id)
    )
    if machine_ids:
        statement = statement.where(MaintenanceEvent.machine_id.in_(machine_ids))
    if not include_archived:
        statement = statement.where(MaintenanceEvent.status == "ACTIVE")
    if from_at is not None:
        statement = statement.where(
            MaintenanceEvent.ended_at.is_(None) | (MaintenanceEvent.ended_at > _as_utc(from_at))
        )
    if to_at is not None:
        statement = statement.where(MaintenanceEvent.started_at < _as_utc(to_at))
    rows = session.execute(statement.order_by(MaintenanceEvent.started_at)).all()
    return [_maintenance_response(event, name) for event, name in rows]


def _trend_payload(
    session: Session,
    organization_id: UUID,
    machine_ids: list[UUID],
    metric_key: str | None,
    from_at: datetime | None,
    to_at: datetime | None,
    timezone_name: str,
    aggregate: TrendAggregate,
    unit: str | None,
    filters: dict[str, str],
    include_archived: bool,
    settings: Settings,
) -> TrendResponse:
    zone = _validate_timezone(timezone_name)
    if from_at is not None and to_at is not None and _as_utc(from_at) > _as_utc(to_at):
        raise DomainError("DATE_RANGE_INVALID", "The trend start must not be after its end.", 422)
    for machine_id in machine_ids:
        _machine_or_error(session, organization_id, machine_id)

    source_count = _count_source_rows(
        session,
        organization_id,
        machine_ids,
        metric_key,
        from_at,
        to_at,
        unit,
        filters,
    )
    max_source_points = (
        settings.trend_max_raw_points
        if aggregate == "raw"
        else settings.trend_max_aggregate_source_points
    )
    if source_count > max_source_points:
        raise DomainError(
            "TREND_QUERY_TOO_LARGE",
            "The selected trend source is larger than the configured query budget.",
            413,
            details=[
                {
                    "field": "aggregate",
                    "message": (
                        "Choose day or week aggregation for a larger source set."
                        if aggregate == "raw"
                        else "Choose a narrower range or filter before retrying."
                    ),
                },
                {
                    "field": "matched_points",
                    "message": f"The query matched {source_count} source points.",
                },
                {
                    "field": "max_points",
                    "message": f"The selected mode allows at most {max_source_points} points.",
                },
            ],
        )
    rows = _load_source_rows(
        session,
        organization_id,
        machine_ids,
        metric_key,
        from_at,
        to_at,
        unit,
        filters,
    )
    # The SQL preflight uses the same organization and JSON compatibility
    # filters as the source read. Keep a second check after the Python-side
    # context matcher so a legacy row that cannot be represented by the SQL
    # JSON predicate can never bypass the budget.
    if len(rows) > max_source_points:
        raise DomainError(
            "TREND_QUERY_TOO_LARGE",
            "The selected trend source is larger than the configured query budget.",
            413,
            details=[
                {
                    "field": "aggregate",
                    "message": (
                        "Choose day or week aggregation for a larger source set."
                        if aggregate == "raw"
                        else "Choose a narrower range or filter before retrying."
                    ),
                },
                {
                    "field": "matched_points",
                    "message": f"The query matched {len(rows)} source points.",
                },
                {
                    "field": "max_points",
                    "message": f"The selected mode allows at most {max_source_points} points.",
                },
            ],
        )
    baselines = _load_baselines(session, organization_id, machine_ids, metric_key, include_archived)
    grouped: dict[tuple[UUID, str, str, str], list[TrendPointResponse]] = defaultdict(list)
    contexts: dict[tuple[UUID, str, str, str], dict[str, object]] = {}
    missing_baseline = False
    for row in rows:
        context = _effective_context(row)
        baseline = _baseline_for_point(baselines, context, row.point.measured_at)
        missing_baseline = missing_baseline or baseline is None
        point = _point_response(row, context, baseline)
        key = (point.machine_id, point.metric_key, point.unit, point.compatibility_signature)
        grouped[key].append(point)
        contexts.setdefault(key, context)

    series: list[TrendSeriesResponse] = []
    warnings: list[str] = []
    if aggregate != "raw" and source_count > settings.trend_max_raw_points:
        warnings.append(
            "TREND_AGGREGATED_LARGE_QUERY: source points exceed the raw-read budget; "
            "bucket lineage remains available for drill-down."
        )
    for key in sorted(grouped, key=lambda item: (str(item[0]), item[1], item[2], item[3])):
        values = grouped[key]
        baseline = _baseline_for_point(baselines, contexts[key], values[-1].measured_at)
        series.append(
            TrendSeriesResponse(
                machine_id=key[0],
                machine_name=values[0].machine_name,
                metric_key=key[1],
                unit=key[2],
                context=contexts[key],
                compatibility_signature=key[3],
                baseline=_baseline_response(baseline) if baseline is not None else None,
                points=values if aggregate == "raw" else [],
                buckets=_aggregate_points(values, aggregate, zone) if aggregate != "raw" else [],
            )
        )
    metric_groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for key in grouped:
        metric_groups[(key[1], key[2])].add(key[3])
    if any(len(signatures) > 1 for signatures in metric_groups.values()):
        warnings.append(
            "TREND_SERIES_INCOMPATIBLE: incompatible unit or clinical context "
            "is shown as separate series."
        )
    if rows and missing_baseline:
        warnings.append("TREND_BASELINE_INVALID: one or more points have no effective baseline.")
    if not rows:
        warnings.append("TREND_EMPTY: no compatible trend points match the selected filters.")
    events = _load_events(session, organization_id, machine_ids, from_at, to_at, include_archived)
    return TrendResponse(
        organization_id=organization_id,
        timezone=timezone_name,
        aggregate=aggregate,
        from_at=from_at,
        to_at=to_at,
        total_points=len(rows),
        series=series,
        maintenance_events=events,
        baselines=[_baseline_response(item) for item in baselines],
        warnings=warnings,
    )


def _count_source_rows(
    session: Session,
    organization_id: UUID,
    machine_ids: list[UUID],
    metric_key: str | None,
    from_at: datetime | None,
    to_at: datetime | None,
    unit: str | None,
    filters: dict[str, str],
) -> int:
    """Count bounded trend candidates before materialising ORM rows.

    Compatibility values are stored in the immutable point context snapshot.
    Counting in SQL prevents a large raw read from first allocating the full
    response in Python.  `_load_source_rows` still performs the authoritative
    context match and duplicate-source check afterwards.
    """

    statement = (
        select(func.count(TrendPoint.id))
        .join(
            Machine,
            and_(Machine.id == TrendPoint.machine_id, Machine.organization_id == organization_id),
        )
        .join(
            QACase,
            and_(QACase.id == TrendPoint.qa_case_id, QACase.organization_id == organization_id),
        )
        .join(
            MachineQARun,
            and_(
                MachineQARun.id == TrendPoint.source_run_id,
                MachineQARun.organization_id == organization_id,
            ),
        )
        .where(TrendPoint.organization_id == organization_id)
    )
    if machine_ids:
        statement = statement.where(TrendPoint.machine_id.in_(machine_ids))
    if metric_key:
        statement = statement.where(TrendPoint.metric_key == metric_key)
    if unit:
        statement = statement.where(TrendPoint.unit == unit)
    if from_at is not None:
        statement = statement.where(TrendPoint.measured_at >= _as_utc(from_at))
    if to_at is not None:
        statement = statement.where(TrendPoint.measured_at < _as_utc(to_at))
    for key, value in filters.items():
        statement = statement.where(TrendPoint.context_snapshot[key].as_string() == value)
    return int(session.scalar(statement) or 0)


def _request_settings(request: Request) -> Settings:
    configured = getattr(request.app.state, "settings", None)
    return configured if isinstance(configured, Settings) else get_settings()


@router.get("/organizations/{organization_id}/trend", response_model=TrendResponse)
def read_trend(
    organization_id: UUID,
    request: Request,
    machine_ids: str | None = Query(default=None, max_length=1000),
    metric_key: str | None = Query(default=None, max_length=120),
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    timezone: str = Query(default="UTC", max_length=80),
    aggregate: TrendAggregate = Query(default="raw"),
    unit: str | None = Query(default=None, max_length=40),
    energy: str | None = Query(default=None, max_length=80),
    detector: str | None = Query(default=None, max_length=120),
    phantom: str | None = Query(default=None, max_length=120),
    beam_quality: str | None = Query(default=None, max_length=80),
    acquisition_mode: str | None = Query(default=None, max_length=80),
    protocol_key: str | None = Query(default=None, max_length=120),
    qa_cycle: str | None = Query(default=None, max_length=40),
    include_archived: bool = Query(default=False),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> TrendResponse:
    _context_for_organization(organization_id, identity, session)
    return _trend_payload(
        session,
        organization_id,
        _machine_ids(machine_ids),
        metric_key,
        from_at,
        to_at,
        timezone,
        aggregate,
        unit,
        _context_filters(
            energy,
            detector,
            phantom,
            beam_quality,
            acquisition_mode,
            protocol_key,
            qa_cycle,
        ),
        include_archived,
        _request_settings(request),
    )


@router.get("/organizations/{organization_id}/trend/export")
def export_trend(
    organization_id: UUID,
    request: Request,
    export_format: ExportFormat = Query(default="CSV"),
    machine_ids: str | None = Query(default=None, max_length=1000),
    metric_key: str | None = Query(default=None, max_length=120),
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    timezone: str = Query(default="UTC", max_length=80),
    aggregate: TrendAggregate = Query(default="raw"),
    unit: str | None = Query(default=None, max_length=40),
    energy: str | None = Query(default=None, max_length=80),
    detector: str | None = Query(default=None, max_length=120),
    phantom: str | None = Query(default=None, max_length=120),
    beam_quality: str | None = Query(default=None, max_length=80),
    acquisition_mode: str | None = Query(default=None, max_length=80),
    protocol_key: str | None = Query(default=None, max_length=120),
    qa_cycle: str | None = Query(default=None, max_length=40),
    include_archived: bool = Query(default=False),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> Response:
    _context_for_organization(organization_id, identity, session)
    payload = _trend_payload(
        session,
        organization_id,
        _machine_ids(machine_ids),
        metric_key,
        from_at,
        to_at,
        timezone,
        aggregate,
        unit,
        _context_filters(
            energy,
            detector,
            phantom,
            beam_quality,
            acquisition_mode,
            protocol_key,
            qa_cycle,
        ),
        include_archived,
        _request_settings(request),
    )
    if export_format == "JSON":
        content = json.dumps(
            payload.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2
        )
        return Response(
            content=content,
            media_type="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=rt-connect-trend.json"},
        )
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "machine_id",
            "machine_name",
            "metric_key",
            "unit",
            "measured_at",
            "value",
            "status",
            "compatibility_signature",
            "source_run_id",
            "qa_case_id",
            "source_archived",
            "baseline_value",
            "baseline_delta",
            "is_outlier",
            "record_type",
            "bucket_start_at",
            "bucket_end_at",
            "bucket_count",
            "bucket_mean",
            "bucket_minimum",
            "bucket_maximum",
            "bucket_first_value",
            "bucket_last_value",
            "bucket_statuses",
            "bucket_source_point_ids",
            "bucket_source_run_ids",
        ]
    )
    for series_item in payload.series:
        for point in series_item.points:
            writer.writerow(
                [
                    str(point.machine_id),
                    point.machine_name,
                    point.metric_key,
                    point.unit,
                    _iso(point.measured_at),
                    point.value,
                    point.status,
                    point.compatibility_signature,
                    str(point.source_run_id),
                    str(point.qa_case_id),
                    point.source_archived,
                    point.baseline_value,
                    point.baseline_delta,
                    point.is_outlier,
                    "POINT",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
        for bucket in series_item.buckets:
            writer.writerow(
                [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "BUCKET",
                    _iso(bucket.start_at),
                    _iso(bucket.end_at),
                    bucket.count,
                    bucket.mean,
                    bucket.minimum,
                    bucket.maximum,
                    bucket.first_value,
                    bucket.last_value,
                    json.dumps(
                        bucket.statuses,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        [str(item) for item in bucket.source_point_ids],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    json.dumps(
                        [str(item) for item in bucket.source_run_ids],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                ]
            )
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=rt-connect-trend.csv"},
    )


@router.post(
    "/organizations/{organization_id}/trend/rebuild",
    response_model=TrendRebuildResponse,
    status_code=status.HTTP_200_OK,
)
def rebuild_trend(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> TrendRebuildResponse:
    context = _context_for_organization(organization_id, identity, session)
    rows = session.execute(
        select(MachineQARun, QACase)
        .join(
            QACase,
            and_(QACase.id == MachineQARun.qa_case_id, QACase.organization_id == organization_id),
        )
        .where(
            MachineQARun.organization_id == organization_id,
            MachineQARun.status == "COMPLETED",
        )
    ).all()
    created = 0
    existing = 0
    repaired = 0
    for run, case in rows:
        raw_metrics = (
            run.result_snapshot.get("metrics", []) if isinstance(run.result_snapshot, dict) else []
        )
        if not isinstance(raw_metrics, list):
            continue
        for raw_metric in raw_metrics:
            if not isinstance(raw_metric, dict):
                continue
            actual = raw_metric.get("actual")
            unit = raw_metric.get("unit")
            metric_key = raw_metric.get("metric_key")
            if not isinstance(actual, int | float) or not isfinite(float(actual)):
                continue
            if not isinstance(unit, str) or not isinstance(metric_key, str):
                continue
            point = session.scalar(
                select(TrendPoint).where(
                    TrendPoint.organization_id == organization_id,
                    TrendPoint.source_run_id == run.id,
                    TrendPoint.metric_key == metric_key,
                )
            )
            context_snapshot = _source_context(run, case, unit)
            metric_context = raw_metric.get("context")
            if isinstance(metric_context, dict):
                context_snapshot.update(
                    {
                        str(key): value
                        for key, value in metric_context.items()
                        if isinstance(value, str)
                    }
                )
            if point is not None:
                existing += 1
                if point.context_snapshot != context_snapshot:
                    point.context_snapshot = context_snapshot
                    repaired += 1
                continue
            session.add(
                TrendPoint(
                    organization_id=organization_id,
                    machine_id=run.machine_id,
                    qa_case_id=run.qa_case_id,
                    source_run_id=run.id,
                    metric_key=metric_key,
                    value=float(actual),
                    unit=unit,
                    status=str(raw_metric.get("status", "UNKNOWN")),
                    measured_at=case.performed_at,
                    context_snapshot=context_snapshot,
                )
            )
            created += 1
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "TREND_DUPLICATE_SOURCE",
            "The trend rebuild encountered a duplicate source point; "
            "no partial rebuild is accepted.",
            409,
        ) from exc
    return TrendRebuildResponse(
        organization_id=context.organization_id,
        scanned_runs=len(rows),
        created_points=created,
        existing_points=existing,
        repaired_context_points=repaired,
    )


@router.get(
    "/organizations/{organization_id}/trend/baselines", response_model=list[BaselineResponse]
)
def list_baselines(
    organization_id: UUID,
    machine_id: UUID | None = None,
    metric_key: str | None = Query(default=None, max_length=120),
    include_archived: bool = Query(default=True),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> list[BaselineResponse]:
    _context_for_organization(organization_id, identity, session)
    if machine_id is not None:
        _machine_or_error(session, organization_id, machine_id)
    return [
        _baseline_response(item)
        for item in _load_baselines(
            session,
            organization_id,
            [machine_id] if machine_id else [],
            metric_key,
            include_archived,
        )
    ]


@router.post(
    "/organizations/{organization_id}/trend/baselines",
    response_model=BaselineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_baseline(
    organization_id: UUID,
    request: BaselineCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> BaselineResponse:
    context = _context_for_organization(organization_id, identity, session)
    machine = _machine_or_error(session, organization_id, request.machine_id)
    if machine.is_archived:
        raise DomainError(
            "TREND_SOURCE_ARCHIVED", "An archived machine cannot receive a new baseline.", 409
        )
    _finite_or_error(request.baseline_value, "baseline_value")
    _finite_or_error(request.tolerance, "tolerance")
    _finite_or_error(request.action_level, "action_level")
    if request.effective_to is not None and _as_utc(request.effective_to) <= _as_utc(
        request.effective_from
    ):
        raise DomainError(
            "TREND_BASELINE_INVALID", "Baseline effective_to must be after effective_from.", 422
        )
    context_snapshot = _validate_context(request.context)
    version = request.version_number
    if version is None:
        latest = session.scalar(
            select(BaselineVersion.version_number)
            .where(
                BaselineVersion.organization_id == organization_id,
                BaselineVersion.machine_id == request.machine_id,
                BaselineVersion.metric_key == request.metric_key,
            )
            .order_by(BaselineVersion.version_number.desc())
            .limit(1)
        )
        version = (latest or 0) + 1
    baseline = BaselineVersion(
        organization_id=organization_id,
        machine_id=machine.id,
        metric_key=request.metric_key,
        unit=request.unit,
        name=request.name,
        version_number=version,
        baseline_value=request.baseline_value,
        tolerance=request.tolerance,
        action_level=request.action_level,
        effective_from=request.effective_from,
        effective_to=request.effective_to,
        status=request.status,
        source_type=request.source_type,
        source_id=request.source_id,
        context_snapshot=context_snapshot,
        created_by_user_identity_id=_actor(session, context),
    )
    session.add(baseline)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "TREND_BASELINE_VERSION_CONFLICT",
            "That baseline version already exists for the machine and metric.",
            409,
        ) from exc
    session.refresh(baseline)
    return _baseline_response(baseline)


@router.patch("/trend-baselines/{baseline_id}", response_model=BaselineResponse)
def update_baseline(
    baseline_id: UUID,
    request: BaselinePatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> BaselineResponse:
    context = resolve_session_context(session, identity)
    baseline = session.scalar(
        select(BaselineVersion).where(
            BaselineVersion.id == baseline_id,
            BaselineVersion.organization_id == context.organization_id,
        )
    )
    if baseline is None:
        raise DomainError(
            "TREND_BASELINE_NOT_FOUND", "The baseline was not found in this organization.", 404
        )
    if baseline.version_number != request.expected_version:
        raise DomainError(
            "TREND_BASELINE_VERSION_CONFLICT",
            "The baseline changed; reload before editing it.",
            409,
        )
    if request.effective_to is not None and _as_utc(request.effective_to) <= _as_utc(
        baseline.effective_from
    ):
        raise DomainError(
            "TREND_BASELINE_INVALID", "Baseline effective_to must be after effective_from.", 422
        )
    if request.name is not None:
        baseline.name = request.name
    if request.tolerance is not None:
        _finite_or_error(request.tolerance, "tolerance")
        baseline.tolerance = request.tolerance
    if request.action_level is not None:
        _finite_or_error(request.action_level, "action_level")
        baseline.action_level = request.action_level
    if request.effective_to is not None:
        baseline.effective_to = request.effective_to
    if request.status is not None:
        baseline.status = request.status
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "TREND_BASELINE_VERSION_CONFLICT",
            "The baseline update conflicts with current data.",
            409,
        ) from exc
    session.refresh(baseline)
    return _baseline_response(baseline)


@router.get(
    "/organizations/{organization_id}/trend/events", response_model=list[MaintenanceResponse]
)
def list_maintenance_events(
    organization_id: UUID,
    machine_id: UUID | None = None,
    from_at: datetime | None = Query(default=None, alias="from"),
    to_at: datetime | None = Query(default=None, alias="to"),
    include_archived: bool = Query(default=True),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> list[MaintenanceResponse]:
    _context_for_organization(organization_id, identity, session)
    if from_at is not None and to_at is not None and _as_utc(from_at) > _as_utc(to_at):
        raise DomainError(
            "DATE_RANGE_INVALID", "The event start filter must not be after its end.", 422
        )
    if machine_id is not None:
        _machine_or_error(session, organization_id, machine_id)
    return _load_events(
        session,
        organization_id,
        [machine_id] if machine_id else [],
        from_at,
        to_at,
        include_archived,
    )


@router.post(
    "/organizations/{organization_id}/trend/events",
    response_model=MaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance_event(
    organization_id: UUID,
    request: MaintenanceCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> MaintenanceResponse:
    context = _context_for_organization(organization_id, identity, session)
    machine = _machine_or_error(session, organization_id, request.machine_id)
    if machine.is_archived:
        raise DomainError(
            "TREND_SOURCE_ARCHIVED", "An archived machine cannot receive a new event.", 409
        )
    _validate_interval(request.started_at, request.ended_at)
    event = MaintenanceEvent(
        organization_id=organization_id,
        machine_id=machine.id,
        event_type=request.event_type,
        title=request.title,
        started_at=request.started_at,
        ended_at=request.ended_at,
        notes=request.notes,
        revision_number=1,
        status="ACTIVE",
        metadata_snapshot=dict(request.metadata),
        created_by_user_identity_id=_actor(session, context),
    )
    session.add(event)
    session.flush()
    _write_event_revision(session, event, _actor(session, context))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "MAINTENANCE_EVENT_CONFLICT", "The maintenance event could not be saved.", 409
        ) from exc
    session.refresh(event)
    return _maintenance_response(event, machine.display_name)


@router.patch("/trend-events/{event_id}", response_model=MaintenanceResponse)
def update_maintenance_event(
    event_id: UUID,
    request: MaintenancePatchRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> MaintenanceResponse:
    context = resolve_session_context(session, identity)
    row = session.execute(
        select(MaintenanceEvent, Machine)
        .join(
            Machine,
            and_(
                Machine.id == MaintenanceEvent.machine_id,
                Machine.organization_id == context.organization_id,
            ),
        )
        .where(
            MaintenanceEvent.id == event_id,
            MaintenanceEvent.organization_id == context.organization_id,
        )
    ).first()
    if row is None:
        raise DomainError(
            "MAINTENANCE_EVENT_NOT_FOUND", "The maintenance event was not found.", 404
        )
    event, machine = row
    if event.revision_number != request.expected_revision:
        raise DomainError(
            "MAINTENANCE_REVISION_CONFLICT",
            "The maintenance event changed; reload before editing it.",
            409,
        )
    next_start = request.started_at or event.started_at
    next_end = request.ended_at if request.ended_at is not None else event.ended_at
    _validate_interval(next_start, next_end)
    for field in ("event_type", "title", "started_at", "ended_at", "notes", "status"):
        value = getattr(request, field)
        if value is not None:
            setattr(event, field, value)
    if request.metadata is not None:
        event.metadata_snapshot = dict(request.metadata)
    event.revision_number += 1
    _write_event_revision(session, event, _actor(session, context))
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "MAINTENANCE_REVISION_CONFLICT", "The event update conflicts with current data.", 409
        ) from exc
    session.refresh(event)
    return _maintenance_response(event, machine.display_name)


@router.get("/trend-events/{event_id}/revisions", response_model=list[MaintenanceRevisionResponse])
def list_maintenance_revisions(
    event_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> list[MaintenanceRevisionResponse]:
    context = resolve_session_context(session, identity)
    event = session.scalar(
        select(MaintenanceEvent).where(
            MaintenanceEvent.id == event_id,
            MaintenanceEvent.organization_id == context.organization_id,
        )
    )
    if event is None:
        raise DomainError(
            "MAINTENANCE_EVENT_NOT_FOUND", "The maintenance event was not found.", 404
        )
    revisions = session.scalars(
        select(MaintenanceEventRevision)
        .where(
            MaintenanceEventRevision.maintenance_event_id == event_id,
            MaintenanceEventRevision.organization_id == context.organization_id,
        )
        .order_by(MaintenanceEventRevision.revision_number)
    ).all()
    return [_maintenance_revision_response(item) for item in revisions]


@router.get("/trend-points/{point_id}/source", response_model=dict[str, object])
def trend_point_source(
    point_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    context = resolve_session_context(session, identity)
    row = session.execute(
        select(TrendPoint, Machine, QACase, MachineQARun)
        .join(
            Machine,
            and_(
                Machine.id == TrendPoint.machine_id,
                Machine.organization_id == context.organization_id,
            ),
        )
        .join(
            QACase,
            and_(
                QACase.id == TrendPoint.qa_case_id,
                QACase.organization_id == context.organization_id,
            ),
        )
        .join(
            MachineQARun,
            and_(
                MachineQARun.id == TrendPoint.source_run_id,
                MachineQARun.organization_id == context.organization_id,
            ),
        )
        .where(TrendPoint.id == point_id, TrendPoint.organization_id == context.organization_id)
    ).first()
    if row is None:
        raise DomainError(
            "TREND_SOURCE_UNAVAILABLE", "The trend point was not found in this organization.", 404
        )
    point, machine, case, run = row
    return {
        "point_id": point.id,
        "organization_id": context.organization_id,
        "machine": {
            "id": machine.id,
            "name": machine.display_name,
            "archived": machine.is_archived,
        },
        "qa_case": {
            "id": case.id,
            "title": case.title,
            "qa_cycle": case.qa_cycle,
            "archived": case.is_archived,
        },
        "machine_qa_run": {
            "id": run.id,
            "status": run.status,
            "overall_status": run.overall_status,
            "protocol_version_id": run.protocol_version_id,
            "result_snapshot": run.result_snapshot,
        },
        "metric_key": point.metric_key,
        "value": point.value,
        "unit": point.unit,
        "measured_at": point.measured_at,
        "context": _effective_context(_SourceRow(point, machine, case, run)),
    }
