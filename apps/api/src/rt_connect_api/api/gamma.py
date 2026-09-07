"""P8 PSQA Gamma job, preflight and result endpoints."""

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import Artifact, GammaAnalysisRun, InputManifest, QACase, UserIdentity
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.gamma_engine import (
    ENGINE_VERSION,
    GammaEngineError,
    calculate_gamma_from_paths,
)
from rt_connect_api.services.object_storage import ObjectStorage, ObjectStorageError
from rt_connect_api.services.redis_queue import RedisQueueError, get_gamma_queue
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["gamma"])


class GammaConfigurationRequest(BaseModel):
    dimensionality: Literal["2D", "3D"] = "2D"
    dose_difference_percent: float = Field(default=3.0, gt=0, le=100)
    dose_difference_mode: Literal["ABSOLUTE", "RELATIVE"] = "RELATIVE"
    absolute_dose_difference_gy: float | None = Field(default=None, gt=0)
    distance_to_agreement_mm: float = Field(default=3.0, gt=0)
    dose_threshold_percent: float = Field(default=10.0, ge=0, le=100)
    normalization: Literal["GLOBAL", "LOCAL"] = "GLOBAL"
    interpolation: Literal["GRID", "BILINEAR"] = "GRID"
    pass_rate_threshold_percent: float = Field(default=95.0, ge=0, le=100)
    histogram_bins: int = Field(default=10, ge=2, le=100)

    @model_validator(mode="after")
    def validate_absolute_mode(self) -> GammaConfigurationRequest:
        if self.dose_difference_mode == "ABSOLUTE" and self.absolute_dose_difference_gy is None:
            raise ValueError("absolute_dose_difference_gy is required in ABSOLUTE mode")
        return self


class GammaRunCreateRequest(BaseModel):
    reference_artifact_id: UUID
    evaluation_artifact_id: UUID
    idempotency_key: str = Field(min_length=8, max_length=200)
    configuration: GammaConfigurationRequest = Field(default_factory=GammaConfigurationRequest)


class GammaRunResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qa_case_id: UUID
    reference_artifact_id: UUID
    evaluation_artifact_id: UUID
    idempotency_key: str
    status: str
    progress_percent: int
    attempt_count: int
    engine_version: str
    config_snapshot: dict[str, object]
    input_manifest_snapshot: dict[str, object]
    result_snapshot: dict[str, object]
    error_snapshot: list[dict[str, object]]
    warning_snapshot: list[dict[str, object]]
    queued_at: datetime
    started_at: datetime | None
    heartbeat_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GammaRunCollectionResponse(BaseModel):
    items: list[GammaRunResponse]
    total: int


class GammaCompareItem(BaseModel):
    key: str
    left: object | None
    right: object | None


class GammaCompareResponse(BaseModel):
    left_run_id: UUID
    right_run_id: UUID
    items: list[GammaCompareItem]


class GammaQueueMetricsResponse(BaseModel):
    backend: str
    configured: bool
    available: bool
    stream_length: int | None = None
    pending_count: int | None = None
    consumer_count: int | None = None
    queued_runs: int
    running_runs: int
    retrying_runs: int
    failed_runs: int
    error: str | None = None


def _storage(request: Request) -> ObjectStorage:
    from rt_connect_api.services.object_storage import get_storage

    try:
        return get_storage(request.app.state.settings)
    except ObjectStorageError as exc:
        raise DomainError(
            "OBJECT_STORAGE_NOT_CONFIGURED",
            "Durable artifact storage is not configured for this environment.",
            503,
        ) from exc


def _context(identity: AuthenticatedIdentity, session: Session) -> SessionContext:
    return resolve_session_context(session, identity)


def _actor_id(session: Session, context: SessionContext) -> UUID | None:
    return session.scalar(
        select(UserIdentity.id).where(UserIdentity.supabase_user_id == context.subject)
    )


def _case_or_error(session: Session, context: SessionContext, case_id: UUID) -> QACase:
    case = session.scalar(
        select(QACase).where(
            QACase.id == case_id,
            QACase.organization_id == context.organization_id,
        )
    )
    if case is None:
        raise DomainError("QA_CASE_NOT_FOUND", "QA case was not found in this organization.", 404)
    if case.is_archived:
        raise DomainError("QA_CASE_ARCHIVED", "Archived QA cases cannot run Gamma analysis.", 409)
    return case


def _run_or_error(
    session: Session, identity: AuthenticatedIdentity, run_id: UUID
) -> GammaAnalysisRun:
    context = _context(identity, session)
    run = session.scalar(
        select(GammaAnalysisRun).where(
            GammaAnalysisRun.id == run_id,
            GammaAnalysisRun.organization_id == context.organization_id,
        )
    )
    if run is None:
        raise DomainError("GAMMA_RUN_NOT_FOUND", "Gamma analysis run was not found.", 404)
    return run


def _run_response(run: GammaAnalysisRun) -> GammaRunResponse:
    return GammaRunResponse(
        id=run.id,
        organization_id=run.organization_id,
        qa_case_id=run.qa_case_id,
        reference_artifact_id=run.reference_artifact_id,
        evaluation_artifact_id=run.evaluation_artifact_id,
        idempotency_key=run.idempotency_key,
        status=run.status,
        progress_percent=run.progress_percent,
        attempt_count=run.attempt_count,
        engine_version=run.engine_version,
        config_snapshot=run.config_snapshot,
        input_manifest_snapshot=run.input_manifest_snapshot,
        result_snapshot=run.result_snapshot,
        error_snapshot=run.error_snapshot,
        warning_snapshot=run.warning_snapshot,
        queued_at=run.queued_at,
        started_at=run.started_at,
        heartbeat_at=run.heartbeat_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _manifest_for_artifact(
    session: Session, organization_id: UUID, artifact_id: UUID
) -> InputManifest:
    manifest = session.scalar(
        select(InputManifest)
        .where(
            InputManifest.organization_id == organization_id,
            InputManifest.artifact_id == artifact_id,
        )
        .order_by(InputManifest.created_at.desc())
    )
    if manifest is None:
        raise DomainError(
            "INPUT_MANIFEST_NOT_FOUND",
            "A validated Input Manifest is required before Gamma analysis.",
            422,
        )
    return manifest


def _preflight_artifact(
    session: Session,
    context: SessionContext,
    case: QACase,
    artifact_id: UUID,
    label: str,
) -> tuple[Artifact, InputManifest]:
    artifact = session.scalar(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.organization_id == context.organization_id,
            Artifact.qa_case_id == case.id,
        )
    )
    if artifact is None:
        raise DomainError(
            "GAMMA_ARTIFACT_SCOPE_MISMATCH",
            f"The {label} artifact is not part of the selected QA case and organization.",
            422,
        )
    if artifact.artifact_type not in {"MEASUREMENT", "JSON", "DICOM"}:
        raise DomainError(
            "GAMMA_ARTIFACT_TYPE_INVALID",
            f"The {label} artifact must be a measurement JSON or RTDOSE DICOM artifact.",
            422,
        )
    if artifact.artifact_type == "DICOM" and artifact.modality != "RTDOSE":
        raise DomainError(
            "GAMMA_ARTIFACT_TYPE_INVALID",
            f"The {label} DICOM artifact must have Modality RTDOSE.",
            422,
        )
    if artifact.data_status != "VALID":
        raise DomainError(
            "GAMMA_INPUT_NOT_VALIDATED",
            f"The {label} artifact must have validation status VALID before it can enter Gamma.",
            422,
        )
    manifest = _manifest_for_artifact(session, context.organization_id, artifact.id)
    validation_summary = manifest.validation_summary
    if validation_summary.get("result") != "VALID":
        raise DomainError(
            "GAMMA_INPUT_NOT_VALIDATED",
            f"The {label} Input Manifest does not have a VALID validation result.",
            422,
        )
    if not isinstance(artifact.metadata_snapshot.get("grid"), dict):
        raise DomainError(
            "GAMMA_GRID_METADATA_MISSING",
            f"The {label} artifact has no validated dose grid metadata.",
            422,
        )
    return artifact, manifest


def _input_snapshot(artifact: Artifact, manifest: InputManifest) -> dict[str, object]:
    return {
        "artifact_id": str(artifact.id),
        "filename": artifact.original_filename,
        "artifact_type": artifact.artifact_type,
        "logical_role": manifest.logical_role,
        "sha256": artifact.sha256,
        "byte_size": artifact.byte_size,
        "data_status": artifact.data_status,
        "manifest_id": str(manifest.id),
        "selected_metadata": manifest.selected_metadata,
        "geometry_summary": manifest.geometry_summary,
        "unit_summary": manifest.unit_summary,
        "validation_summary": manifest.validation_summary,
    }


def _fingerprint(payload: GammaRunCreateRequest) -> str:
    canonical = json.dumps(
        {
            "reference_artifact_id": str(payload.reference_artifact_id),
            "evaluation_artifact_id": str(payload.evaluation_artifact_id),
            "configuration": payload.configuration.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dispatch_gamma_run(request: Request, session: Session, run: GammaAnalysisRun) -> None:
    """Publish a run after its database row is committed.

    Local development can deliberately omit ``REDIS_URL`` and keep the DB polling
    worker. Staging/production configure Redis, so a publish failure is visible as
    a failed run that can be retried instead of silently remaining queued forever.
    """

    queue = get_gamma_queue(request.app.state.settings)
    if queue is None:
        return
    try:
        queue.enqueue(run.id, run.organization_id, run.attempt_count)
    except RedisQueueError as exc:
        run.status = "FAILED"
        run.progress_percent = 100
        run.error_snapshot = [
            {
                "code": "GAMMA_QUEUE_UNAVAILABLE",
                "message": "The configured Gamma queue is unavailable.",
            }
        ]
        run.completed_at = datetime.now(UTC)
        run.heartbeat_at = run.completed_at
        session.commit()
        raise DomainError(
            "GAMMA_QUEUE_UNAVAILABLE",
            "The configured Gamma queue is unavailable; the run can be retried after recovery.",
            503,
        ) from exc


@router.post(
    "/qa-cases/{case_id}/gamma-runs",
    response_model=GammaRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_gamma_run(
    case_id: UUID,
    payload: GammaRunCreateRequest,
    request: Request,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> GammaRunResponse:
    context = _context(identity, session)
    case = _case_or_error(session, context, case_id)
    if payload.reference_artifact_id == payload.evaluation_artifact_id:
        raise DomainError(
            "GAMMA_INPUTS_MUST_DIFFER",
            "Reference and evaluation artifacts must be different files.",
            422,
        )
    reference, reference_manifest = _preflight_artifact(
        session, context, case, payload.reference_artifact_id, "reference"
    )
    evaluation, evaluation_manifest = _preflight_artifact(
        session, context, case, payload.evaluation_artifact_id, "evaluation"
    )
    request_fingerprint = _fingerprint(payload)
    existing = session.scalar(
        select(GammaAnalysisRun).where(
            GammaAnalysisRun.organization_id == context.organization_id,
            GammaAnalysisRun.idempotency_key == payload.idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_fingerprint != request_fingerprint:
            raise DomainError(
                "GAMMA_IDEMPOTENCY_CONFLICT",
                "The idempotency key was already used for a different Gamma request.",
                409,
            )
        if existing.status in {"QUEUED", "RETRYING"}:
            _dispatch_gamma_run(request, session, existing)
        response.status_code = status.HTTP_200_OK
        return _run_response(existing)

    run = GammaAnalysisRun(
        organization_id=context.organization_id,
        qa_case_id=case.id,
        reference_artifact_id=reference.id,
        evaluation_artifact_id=evaluation.id,
        idempotency_key=payload.idempotency_key,
        request_fingerprint=request_fingerprint,
        status="QUEUED",
        progress_percent=0,
        attempt_count=0,
        engine_version=ENGINE_VERSION,
        config_snapshot=payload.configuration.model_dump(mode="json"),
        input_manifest_snapshot={
            "reference": _input_snapshot(reference, reference_manifest),
            "evaluation": _input_snapshot(evaluation, evaluation_manifest),
        },
        result_snapshot={},
        error_snapshot=[],
        warning_snapshot=[],
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(run)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "GAMMA_IDEMPOTENCY_CONFLICT",
            "The idempotency key was claimed by another request; reload the run history.",
            409,
        ) from exc
    session.refresh(run)
    _dispatch_gamma_run(request, session, run)
    return _run_response(run)


@router.get("/qa-cases/{case_id}/gamma-runs", response_model=GammaRunCollectionResponse)
def list_gamma_runs(
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> GammaRunCollectionResponse:
    context = _context(identity, session)
    _case_or_error(session, context, case_id)
    runs = list(
        session.scalars(
            select(GammaAnalysisRun)
            .where(
                GammaAnalysisRun.organization_id == context.organization_id,
                GammaAnalysisRun.qa_case_id == case_id,
            )
            .order_by(GammaAnalysisRun.created_at.desc())
        )
    )
    return GammaRunCollectionResponse(items=[_run_response(run) for run in runs], total=len(runs))


@router.get("/gamma-runs/{run_id}", response_model=GammaRunResponse)
def get_gamma_run(
    run_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> GammaRunResponse:
    return _run_response(_run_or_error(session, identity, run_id))


@router.post("/gamma-runs/{run_id}/retry", response_model=GammaRunResponse)
def retry_gamma_run(
    run_id: UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> GammaRunResponse:
    run = _run_or_error(session, identity, run_id)
    if run.status != "FAILED":
        raise DomainError(
            "GAMMA_RETRY_NOT_ALLOWED",
            "Only a failed Gamma run can be retried.",
            409,
        )
    run.status = "QUEUED"
    run.progress_percent = 0
    run.error_snapshot = []
    run.warning_snapshot = []
    run.result_snapshot = {}
    run.started_at = None
    run.heartbeat_at = None
    run.completed_at = None
    session.commit()
    session.refresh(run)
    _dispatch_gamma_run(request, session, run)
    return _run_response(run)


@router.get("/gamma/queue-metrics", response_model=GammaQueueMetricsResponse)
def gamma_queue_metrics(
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> GammaQueueMetricsResponse:
    """Return organization-scoped queue counters without exposing Redis details."""

    context = _context(identity, session)
    count_rows = session.execute(
        select(GammaAnalysisRun.status, func.count())
        .where(GammaAnalysisRun.organization_id == context.organization_id)
        .group_by(GammaAnalysisRun.status)
    ).all()
    counts: dict[str, int] = {str(row[0]): int(row[1]) for row in count_rows}
    queue = get_gamma_queue(request.app.state.settings)
    if queue is None:
        return GammaQueueMetricsResponse(
            backend="database_polling",
            configured=False,
            available=True,
            queued_runs=int(counts.get("QUEUED", 0)),
            running_runs=int(counts.get("RUNNING", 0)),
            retrying_runs=int(counts.get("RETRYING", 0)),
            failed_runs=int(counts.get("FAILED", 0)),
        )
    try:
        metrics = queue.metrics()
    except RedisQueueError:
        return GammaQueueMetricsResponse(
            backend="redis_stream",
            configured=True,
            available=False,
            queued_runs=int(counts.get("QUEUED", 0)),
            running_runs=int(counts.get("RUNNING", 0)),
            retrying_runs=int(counts.get("RETRYING", 0)),
            failed_runs=int(counts.get("FAILED", 0)),
            error="GAMMA_QUEUE_UNAVAILABLE",
        )
    return GammaQueueMetricsResponse(
        backend=str(metrics["backend"]),
        configured=True,
        available=True,
        stream_length=int(metrics["stream_length"]),
        pending_count=int(metrics["pending_count"]),
        consumer_count=int(metrics["consumer_count"]),
        queued_runs=int(counts.get("QUEUED", 0)),
        running_runs=int(counts.get("RUNNING", 0)),
        retrying_runs=int(counts.get("RETRYING", 0)),
        failed_runs=int(counts.get("FAILED", 0)),
    )


@router.get("/gamma-runs/{run_id}/compare", response_model=GammaCompareResponse)
def compare_gamma_runs(
    run_id: UUID,
    other_run_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> GammaCompareResponse:
    left = _run_or_error(session, identity, run_id)
    context = _context(identity, session)
    right = session.scalar(
        select(GammaAnalysisRun).where(
            GammaAnalysisRun.id == other_run_id,
            GammaAnalysisRun.organization_id == context.organization_id,
        )
    )
    if right is None:
        raise DomainError("GAMMA_RUN_NOT_FOUND", "Comparison Gamma run was not found.", 404)
    keys = sorted(set(left.result_snapshot) | set(right.result_snapshot))
    return GammaCompareResponse(
        left_run_id=left.id,
        right_run_id=right.id,
        items=[
            GammaCompareItem(
                key=key,
                left=left.result_snapshot.get(key),
                right=right.result_snapshot.get(key),
            )
            for key in keys
        ],
    )


def process_gamma_run(session: Session, run: GammaAnalysisRun, storage: ObjectStorage) -> None:
    """Worker operation for one queued run; API routes only create/poll/retry jobs."""

    if run.status not in {"QUEUED", "RETRYING"}:
        return
    now = datetime.now(UTC)
    run.status = "RUNNING"
    run.progress_percent = 5
    run.attempt_count += 1
    run.started_at = now
    run.heartbeat_at = now
    session.commit()
    reference_path: Path | None = None
    evaluation_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="rt-connect-gamma-reference-", suffix=".bin", delete=False
        ) as reference_file:
            reference_path = Path(reference_file.name)
        with tempfile.NamedTemporaryFile(
            prefix="rt-connect-gamma-evaluation-", suffix=".bin", delete=False
        ) as evaluation_file:
            evaluation_path = Path(evaluation_file.name)
        storage.download_to_path(
            _object_key_from_snapshot(run, "reference", session), reference_path
        )
        _verify_snapshot_checksum(run, "reference", reference_path)
        run.progress_percent = 25
        run.heartbeat_at = datetime.now(UTC)
        session.commit()
        storage.download_to_path(
            _object_key_from_snapshot(run, "evaluation", session), evaluation_path
        )
        _verify_snapshot_checksum(run, "evaluation", evaluation_path)
        run.progress_percent = 45
        run.heartbeat_at = datetime.now(UTC)
        session.commit()
        result = calculate_gamma_from_paths(reference_path, evaluation_path, run.config_snapshot)
        run.result_snapshot = result
        raw_warnings = result.get("warnings", [])
        run.warning_snapshot = raw_warnings if isinstance(raw_warnings, list) else []
        run.error_snapshot = []
        run.progress_percent = 100
        run.status = "COMPLETED"
        run.completed_at = datetime.now(UTC)
        run.heartbeat_at = run.completed_at
    except GammaEngineError as exc:
        run.status = "FAILED"
        run.progress_percent = 100
        run.error_snapshot = [{"code": exc.code, "message": exc.message, "details": exc.details}]
        run.completed_at = datetime.now(UTC)
        run.heartbeat_at = run.completed_at
    except ObjectStorageError:
        run.status = "FAILED"
        run.progress_percent = 100
        run.error_snapshot = [
            {
                "code": "GAMMA_STORAGE_UNAVAILABLE",
                "message": "Gamma input could not be read from object storage.",
            }
        ]
        run.completed_at = datetime.now(UTC)
        run.heartbeat_at = run.completed_at
    finally:
        if reference_path is not None:
            reference_path.unlink(missing_ok=True)
        if evaluation_path is not None:
            evaluation_path.unlink(missing_ok=True)
        session.commit()


def _object_key_from_snapshot(run: GammaAnalysisRun, label: str, session: Session) -> str:
    raw_input = run.input_manifest_snapshot.get(label)
    if not isinstance(raw_input, dict):
        raise ObjectStorageError("Gamma input manifest snapshot is invalid")
    raw_id = raw_input.get("artifact_id")
    if not isinstance(raw_id, str):
        raise ObjectStorageError("Gamma input manifest snapshot has no artifact id")
    artifact = session.scalar(
        select(Artifact).where(
            Artifact.id == UUID(raw_id),
            Artifact.organization_id == run.organization_id,
        )
    )
    if artifact is None:
        raise ObjectStorageError("Gamma artifact metadata was not found")
    return artifact.object_key


def _verify_snapshot_checksum(run: GammaAnalysisRun, label: str, path: Path) -> None:
    raw_input = run.input_manifest_snapshot.get(label)
    if not isinstance(raw_input, dict) or not isinstance(raw_input.get("sha256"), str):
        raise GammaEngineError(
            "GAMMA_CHECKSUM_SNAPSHOT_INVALID",
            f"The {label} input snapshot has no SHA-256 checksum.",
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != raw_input["sha256"]:
        raise GammaEngineError(
            "GAMMA_INPUT_CHECKSUM_MISMATCH",
            f"The {label} artifact bytes do not match the snapshotted checksum.",
        )
