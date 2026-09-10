"""P8 PSQA Gamma job, preflight and result endpoints."""

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

from __future__ import annotations

import hashlib
import json
import math
import tempfile
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    Artifact,
    GammaAnalysisRun,
    GammaDispatchOutbox,
    GammaRunAttempt,
    InputManifest,
    QACase,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.gamma_engine import (
    ENGINE_VERSION,
    IDENTITY_TRANSFORM,
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
    coverage_policy: Literal["FULL_ROI", "OVERLAP_ONLY"] = "FULL_ROI"
    max_gamma: float = Field(default=2.0, ge=1.0, le=10.0)
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
    # PSQA is the clinical-facing contract. JSON-only execution remains
    # available, but it must be explicitly labelled as an engineering test.
    workflow_profile: Literal["PSQA_GAMMA", "ENGINE_TEST"] = "PSQA_GAMMA"
    configuration: GammaConfigurationRequest = Field(default_factory=GammaConfigurationRequest)


class GammaRunResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qa_case_id: UUID
    reference_artifact_id: UUID
    evaluation_artifact_id: UUID
    idempotency_key: str
    workflow_profile: Literal["PSQA_GAMMA", "ENGINE_TEST"]
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
    workflow_profile: Literal["PSQA_GAMMA", "ENGINE_TEST"] = "ENGINE_TEST"
    if run.config_snapshot.get("workflow_profile") == "PSQA_GAMMA":
        workflow_profile = "PSQA_GAMMA"
    return GammaRunResponse(
        id=run.id,
        organization_id=run.organization_id,
        qa_case_id=run.qa_case_id,
        reference_artifact_id=run.reference_artifact_id,
        evaluation_artifact_id=run.evaluation_artifact_id,
        idempotency_key=run.idempotency_key,
        workflow_profile=workflow_profile,
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


def _coordinate_frame_summary(artifact: Artifact) -> Mapping[str, object] | None:
    """Return the validated frame summary used for dataset-level preflight."""

    raw = artifact.metadata_snapshot.get("coordinate_frame")
    if isinstance(raw, Mapping):
        return raw
    # Artifacts validated before the frame metadata addendum can still expose
    # the DICOM FrameOfReferenceUID on the Artifact row.  Reconstruct only this
    # unambiguous DICOM identity; never invent a frame for a JSON measurement.
    if (
        artifact.artifact_type == "DICOM"
        and artifact.modality == "RTDOSE"
        and isinstance(artifact.frame_of_reference_uid, str)
        and artifact.frame_of_reference_uid.strip()
    ):
        raw_grid = artifact.metadata_snapshot.get("grid")
        frame_count = raw_grid.get("frames") if isinstance(raw_grid, Mapping) else None
        axis_order = (
            ["z", "y", "x"]
            if isinstance(frame_count, int) and frame_count > 1
            else ["y", "x"]
        )
        return {
            "basis": "PATIENT_LPS",
            "frame_id": artifact.frame_of_reference_uid.strip(),
            "axis_order": axis_order,
            # A validated RTDOSE has native patient coordinates.  Make that
            # identity explicit so it can be compared with a measurement
            # carrying the same identity transform.
            "transform_to_reference": {
                "direction": "SOURCE_TO_REFERENCE",
                "units": "mm",
                "matrix": [
                    list(IDENTITY_TRANSFORM[index : index + 4]) for index in range(0, 16, 4)
                ],
                "source": {
                    "type": "dicom-native",
                    "version": "DICOM-RTDOSE",
                    "sha256": artifact.sha256,
                },
            },
        }
    return None


def _transform_signature(
    artifact: Artifact, frame: Mapping[str, object]
) -> tuple[float, ...] | None:
    """Return a normalized transform, treating only native RTDOSE as identity."""

    raw = frame.get("transform_to_reference")
    if raw is None:
        if artifact.artifact_type == "DICOM" and artifact.modality == "RTDOSE":
            return IDENTITY_TRANSFORM
        return None
    if not isinstance(raw, Mapping):
        return None
    if raw.get("direction") != "SOURCE_TO_REFERENCE" or raw.get("units") != "mm":
        return None
    matrix = raw.get("matrix")
    if not isinstance(matrix, list) or len(matrix) != 4:
        return None
    values: list[float] = []
    for row in matrix:
        if not isinstance(row, list) or len(row) != 4:
            return None
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int | float):
                return None
            number = float(value)
            if not math.isfinite(number):
                return None
            values.append(number)
    return tuple(values)


def _validate_coordinate_frames(reference: Artifact, evaluation: Artifact) -> None:
    """Reject mixed or mismatched frames before creating an async run."""

    reference_frame = _coordinate_frame_summary(reference)
    evaluation_frame = _coordinate_frame_summary(evaluation)
    if (
        reference_frame is None
        and evaluation_frame is None
        and reference.artifact_type != "DICOM"
        and evaluation.artifact_type != "DICOM"
    ):
        # Preserve old JSON-only ENGINE_TEST rows. Newly uploaded measurement
        # artifacts are required to contain the explicit block by P6 validation.
        return
    if reference_frame is None or evaluation_frame is None:
        raise DomainError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Both Gamma inputs must declare a compatible coordinate frame before enqueue.",
            422,
            details=[
                {
                    "field": label,
                    "message": "coordinate_frame is missing or was not captured by validation.",
                }
                for label, frame in (
                    ("reference.coordinate_frame", reference_frame),
                    ("evaluation.coordinate_frame", evaluation_frame),
                )
                if frame is None
            ],
        )
    reference_basis = reference_frame.get("basis")
    evaluation_basis = evaluation_frame.get("basis")
    reference_id = reference_frame.get("frame_id")
    evaluation_id = evaluation_frame.get("frame_id")
    reference_axis = reference_frame.get("axis_order")
    evaluation_axis = evaluation_frame.get("axis_order")
    reference_transform = _transform_signature(reference, reference_frame)
    evaluation_transform = _transform_signature(evaluation, evaluation_frame)
    if reference_transform is None or evaluation_transform is None:
        raise DomainError(
            "GAMMA_COORDINATE_FRAME_INVALID",
            "Both Gamma inputs must provide a valid transform to the comparison frame.",
            422,
            details=[
                {
                    "field": label,
                    "message": "transform_to_reference is missing or invalid.",
                }
                for label, transform in (
                    ("reference.coordinate_frame.transform_to_reference", reference_transform),
                    ("evaluation.coordinate_frame.transform_to_reference", evaluation_transform),
                )
                if transform is None
            ],
        )
    if (
        reference_basis != evaluation_basis
        or reference_id != evaluation_id
        or reference_axis != evaluation_axis
    ):
        raise DomainError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Reference and evaluation coordinate frames do not match.",
            422,
            details=[
                {
                    "field": "coordinate_frame",
                    "message": (
                        "Use the same physical basis, frame identifier and axis order, "
                        "or provide a tested adapter."
                    ),
                }
            ],
        )
    if len(reference_transform) != len(evaluation_transform) or any(
        not math.isclose(left, right, rel_tol=0, abs_tol=1e-9)
        for left, right in zip(reference_transform, evaluation_transform, strict=True)
    ):
        raise DomainError(
            "GAMMA_INPUT_INCOMPATIBLE",
            "Reference and evaluation transforms to the comparison frame do not match.",
            422,
            details=[
                {
                    "field": "coordinate_frame.transform_to_reference",
                    "message": "Use the same tested transform or provide a supported adapter.",
                }
            ],
        )


def _validate_workflow_profile(
    workflow_profile: str, reference: Artifact, evaluation: Artifact
) -> None:
    """Apply semantic input rules that are stronger than file validation."""

    _validate_coordinate_frames(reference, evaluation)

    if workflow_profile == "PSQA_GAMMA":
        if reference.artifact_type != "DICOM" or reference.modality != "RTDOSE":
            raise DomainError(
                "RTDOSE_REQUIRED",
                "PSQA Gamma requires the reference artifact to be a validated RTDOSE DICOM.",
                422,
            )
        if evaluation.artifact_type not in {"MEASUREMENT", "DICOM"} or (
            evaluation.artifact_type == "DICOM" and evaluation.modality != "RTDOSE"
        ):
            raise DomainError(
                "COMPARISON_REQUIRED",
                "PSQA Gamma requires a validated measurement or RTDOSE comparison artifact.",
                422,
            )
        return
    if workflow_profile == "ENGINE_TEST":
        if reference.artifact_type not in {"MEASUREMENT", "JSON", "DICOM"} or (
            evaluation.artifact_type not in {"MEASUREMENT", "JSON", "DICOM"}
        ):
            raise DomainError(
                "GAMMA_ENGINE_TEST_INPUT_INVALID",
                "ENGINE_TEST accepts only validated measurement, JSON or RTDOSE artifacts.",
                422,
            )
        return
    raise DomainError("GAMMA_WORKFLOW_PROFILE_INVALID", "Unsupported Gamma workflow profile.", 422)


def _grid_voxel_count(artifact: Artifact) -> int:
    """Return the validated voxel count used by the Gamma resource preflight."""

    raw_grid = artifact.metadata_snapshot.get("grid")
    if not isinstance(raw_grid, dict):
        raise DomainError(
            "GAMMA_GRID_METADATA_MISSING",
            "Gamma resource preflight requires validated grid dimensions.",
            422,
        )
    raw_shape = raw_grid.get("shape")
    if isinstance(raw_shape, list) and raw_shape:
        dimensions = raw_shape
    else:
        dimensions = [raw_grid.get("rows"), raw_grid.get("columns")]
        if raw_grid.get("frames") is not None:
            dimensions.append(raw_grid.get("frames"))
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in dimensions):
        raise DomainError(
            "GAMMA_GRID_METADATA_INVALID",
            "Gamma resource preflight found invalid validated grid dimensions.",
            422,
        )
    return int(math.prod(int(item) for item in dimensions))


def _resource_budget_snapshot(
    request: Request, reference: Artifact, evaluation: Artifact
) -> dict[str, object]:
    """Reject workloads that could exhaust the worker before they enter the queue."""

    settings = request.app.state.settings
    reference_voxels = _grid_voxel_count(reference)
    evaluation_voxels = _grid_voxel_count(evaluation)
    limit = int(settings.gamma_max_voxels)
    oversized = {
        label: count
        for label, count in (
            ("reference", reference_voxels),
            ("evaluation", evaluation_voxels),
        )
        if count > limit
    }
    if oversized:
        raise DomainError(
            "GAMMA_RESOURCE_LIMIT",
            "The selected Gamma grid exceeds the configured worker voxel limit.",
            422,
            details=[
                {
                    "field": f"{label}_voxels",
                    "message": f"{label} grid contains {count} voxels; the limit is {limit}.",
                }
                for label, count in oversized.items()
            ],
        )
    return {
        "max_voxels": limit,
        "reference_voxels": reference_voxels,
        "evaluation_voxels": evaluation_voxels,
        "total_voxels": reference_voxels + evaluation_voxels,
        "max_candidate_evaluations": int(settings.gamma_max_candidate_evaluations),
        "execution_deadline_seconds": int(settings.gamma_execution_deadline_seconds),
    }


def _fingerprint(payload: GammaRunCreateRequest) -> str:
    canonical = json.dumps(
        {
            "reference_artifact_id": str(payload.reference_artifact_id),
            "evaluation_artifact_id": str(payload.evaluation_artifact_id),
            "workflow_profile": payload.workflow_profile,
            "configuration": payload.configuration.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ensure_dispatch_outbox(session: Session, run: GammaAnalysisRun) -> GammaDispatchOutbox:
    outbox = session.scalar(
        select(GammaDispatchOutbox).where(
            GammaDispatchOutbox.organization_id == run.organization_id,
            GammaDispatchOutbox.gamma_run_id == run.id,
            GammaDispatchOutbox.attempt_number == run.attempt_count,
        )
    )
    if outbox is None:
        outbox = GammaDispatchOutbox(
            organization_id=run.organization_id,
            gamma_run_id=run.id,
            attempt_number=run.attempt_count,
            status="PENDING",
            last_error=None,
        )
        session.add(outbox)
        session.flush()
    return outbox


def _dispatch_gamma_run(request: Request, session: Session, run: GammaAnalysisRun) -> None:
    """Publish a run after its database row is committed.

    Local development can deliberately omit ``REDIS_URL`` and keep the DB polling
    worker. Staging/production configure Redis, so a publish failure is visible as
    a queued run with a durable pending dispatch intent that the worker can reconcile.
    """

    queue = get_gamma_queue(request.app.state.settings)
    if queue is None:
        return
    outbox = _ensure_dispatch_outbox(session, run)
    try:
        queue.enqueue(run.id, run.organization_id, outbox.attempt_number)
        outbox.status = "PUBLISHED"
        outbox.published_at = datetime.now(UTC)
        outbox.last_error = None
        session.commit()
    except RedisQueueError as exc:
        outbox.status = "PENDING"
        outbox.last_error = "GAMMA_QUEUE_UNAVAILABLE"
        session.commit()
        raise DomainError(
            "GAMMA_QUEUE_UNAVAILABLE",
            "The configured Gamma queue is unavailable; the dispatch intent will be retried.",
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
    _validate_workflow_profile(payload.workflow_profile, reference, evaluation)
    resource_budget = _resource_budget_snapshot(request, reference, evaluation)
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
        config_snapshot={
            **payload.configuration.model_dump(mode="json"),
            "workflow_profile": payload.workflow_profile,
            "resource_budget": resource_budget,
        },
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
        session.flush()
        _ensure_dispatch_outbox(session, run)
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
    run.worker_id = None
    run.lease_token = None
    run.lease_expires_at = None
    _ensure_dispatch_outbox(session, run)
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


class GammaLeaseLost(RuntimeError):
    """Raised when a worker no longer owns the fenced Gamma run lease."""


class GammaExecutionDeadline(RuntimeError):
    """Raised when a Gamma attempt exceeds its configured execution deadline."""


def acquire_gamma_run_lease(
    session: Session,
    run: GammaAnalysisRun,
    worker_id: str,
    *,
    expected_dispatch_attempt: int | None = None,
    lease_seconds: int = 120,
) -> str | None:
    """Atomically move a queued run to RUNNING and create its attempt record."""

    if run.status not in {"QUEUED", "RETRYING"}:
        return None
    if expected_dispatch_attempt is not None and expected_dispatch_attempt != run.attempt_count:
        return None
    now = datetime.now(UTC)
    lease_token = uuid4().hex
    attempt_number = run.attempt_count + 1
    result = session.execute(
        update(GammaAnalysisRun)
        .where(
            GammaAnalysisRun.id == run.id,
            GammaAnalysisRun.organization_id == run.organization_id,
            GammaAnalysisRun.status.in_(["QUEUED", "RETRYING"]),
            GammaAnalysisRun.lease_token.is_(None),
        )
        .values(
            status="RUNNING",
            progress_percent=5,
            attempt_count=attempt_number,
            started_at=now,
            heartbeat_at=now,
            worker_id=worker_id,
            lease_token=lease_token,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
        )
    )
    if int(getattr(result, "rowcount", 0)) != 1:
        session.rollback()
        return None
    session.add(
        GammaRunAttempt(
            organization_id=run.organization_id,
            gamma_run_id=run.id,
            attempt_number=attempt_number,
            worker_id=worker_id,
            lease_token=lease_token,
            status="RUNNING",
            error_snapshot=[],
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return None
    session.refresh(run)
    return lease_token


def _lease_update(
    session: Session, run: GammaAnalysisRun, lease_token: str, values: dict[str, object]
) -> None:
    result = session.execute(
        update(GammaAnalysisRun)
        .where(
            GammaAnalysisRun.id == run.id,
            GammaAnalysisRun.organization_id == run.organization_id,
            GammaAnalysisRun.status == "RUNNING",
            GammaAnalysisRun.lease_token == lease_token,
        )
        .values(**values)
    )
    if int(getattr(result, "rowcount", 0)) != 1:
        session.rollback()
        raise GammaLeaseLost("Gamma worker lease is no longer valid")
    session.refresh(run)


def _heartbeat_gamma_run(
    session: Session,
    run: GammaAnalysisRun,
    lease_token: str,
    progress_percent: int,
    *,
    lease_seconds: int = 120,
) -> None:
    now = datetime.now(UTC)
    _lease_update(
        session,
        run,
        lease_token,
        {
            "progress_percent": progress_percent,
            "heartbeat_at": now,
            "lease_expires_at": now + timedelta(seconds=lease_seconds),
        },
    )
    session.commit()


def _finish_gamma_attempt(
    session: Session,
    run: GammaAnalysisRun,
    lease_token: str,
    *,
    status: str,
    errors: list[dict[str, object]],
    result_snapshot: dict[str, object] | None = None,
    warning_snapshot: list[dict[str, object]] | None = None,
    retry_delay_seconds: float = 0.0,
) -> None:
    now = datetime.now(UTC)
    retrying = status == "RETRYING"
    values: dict[str, object] = {
        "status": status,
        "progress_percent": 0 if retrying else 100,
        "error_snapshot": errors,
        "completed_at": None if retrying else now,
        "heartbeat_at": now,
        "worker_id": None,
        "lease_token": None,
        "lease_expires_at": None,
    }
    if retrying:
        values["result_snapshot"] = {}
    if result_snapshot is not None:
        values["result_snapshot"] = result_snapshot
    if warning_snapshot is not None:
        values["warning_snapshot"] = warning_snapshot
    _lease_update(session, run, lease_token, values)
    session.execute(
        update(GammaRunAttempt)
        .where(
            GammaRunAttempt.gamma_run_id == run.id,
            GammaRunAttempt.organization_id == run.organization_id,
            GammaRunAttempt.lease_token == lease_token,
            GammaRunAttempt.status == "RUNNING",
        )
        .values(
            status="FAILED" if retrying else status,
            completed_at=now,
            error_snapshot=errors,
        )
    )
    if retrying:
        outbox = _ensure_dispatch_outbox(session, run)
        outbox.status = "PENDING"
        outbox.available_at = now + timedelta(seconds=max(0.0, retry_delay_seconds))
        outbox.published_at = None
        raw_code = errors[0].get("code") if errors else None
        outbox.last_error = raw_code if isinstance(raw_code, str) else "GAMMA_RETRY_SCHEDULED"
    session.commit()


def process_gamma_run(
    session: Session,
    run: GammaAnalysisRun,
    storage: ObjectStorage,
    *,
    lease_token: str | None = None,
    worker_id: str = "gamma-direct",
    lease_seconds: int = 120,
    max_attempts: int = 3,
    execution_deadline_seconds: int = 900,
    retry_delay_seconds: float = 0.0,
) -> None:
    """Execute one run under a database-fenced lease."""

    if lease_token is not None and run.status != "RUNNING":
        return
    if lease_token is None:
        lease_token = acquire_gamma_run_lease(session, run, worker_id, lease_seconds=lease_seconds)
    if lease_token is None:
        return
    started_monotonic = time.monotonic()

    def check_deadline() -> None:
        if time.monotonic() - started_monotonic > execution_deadline_seconds:
            raise GammaExecutionDeadline("Gamma execution exceeded its configured deadline.")

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
        check_deadline()
        _heartbeat_gamma_run(session, run, lease_token, 25, lease_seconds=lease_seconds)
        storage.download_to_path(
            _object_key_from_snapshot(run, "evaluation", session), evaluation_path
        )
        _verify_snapshot_checksum(run, "evaluation", evaluation_path)
        check_deadline()
        _heartbeat_gamma_run(session, run, lease_token, 45, lease_seconds=lease_seconds)
        result = calculate_gamma_from_paths(reference_path, evaluation_path, run.config_snapshot)
        check_deadline()
        raw_warnings = result.get("warnings", [])
        _finish_gamma_attempt(
            session,
            run,
            lease_token,
            status="COMPLETED",
            errors=[],
            result_snapshot=result,
            warning_snapshot=raw_warnings if isinstance(raw_warnings, list) else [],
        )
    except GammaLeaseLost:
        # A stale worker must leave the message pending for the queue/recovery
        # path. Calling the finish helper here would itself violate fencing.
        raise
    except GammaExecutionDeadline as exc:
        status_value = "RETRYING" if run.attempt_count < max_attempts else "FAILED"
        _finish_gamma_attempt(
            session,
            run,
            lease_token,
            status=status_value,
            errors=[
                {
                    "code": "GAMMA_EXECUTION_DEADLINE",
                    "message": str(exc),
                }
            ],
            retry_delay_seconds=retry_delay_seconds,
        )
    except GammaEngineError as exc:
        _finish_gamma_attempt(
            session,
            run,
            lease_token,
            status="FAILED",
            errors=[{"code": exc.code, "message": exc.message, "details": exc.details}],
        )
    except ObjectStorageError:
        status_value = "RETRYING" if run.attempt_count < max_attempts else "FAILED"
        _finish_gamma_attempt(
            session,
            run,
            lease_token,
            status=status_value,
            errors=[
                {
                    "code": "GAMMA_STORAGE_UNAVAILABLE",
                    "message": "Gamma input could not be read from object storage.",
                }
            ],
            retry_delay_seconds=retry_delay_seconds,
        )
    except Exception:
        _finish_gamma_attempt(
            session,
            run,
            lease_token,
            status="FAILED",
            errors=[
                {
                    "code": "GAMMA_EXECUTION_ERROR",
                    "message": "Gamma execution failed unexpectedly; inspect worker logs.",
                }
            ],
        )
    finally:
        if reference_path is not None:
            reference_path.unlink(missing_ok=True)
        if evaluation_path is not None:
            evaluation_path.unlink(missing_ok=True)


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
