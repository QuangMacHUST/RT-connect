"""P17 Visual Dose and DVH API.

The route layer performs the safety-critical bookkeeping around the pure DVH
engine: organization/case scoping, validated-artifact selection, byte checksum
verification, immutable input snapshots, idempotency and export.  It never
accepts a filename or a client-provided ROI name as authority.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    Artifact,
    AuditEvent,
    DVHAnalysisRun,
    InputManifest,
    QACase,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.dose_dvh_engine import (
    DEFAULT_DX_PERCENTAGES,
    DEFAULT_VX_DOSES_GY,
    DVH_ENGINE_KEY,
    DVH_ENGINE_VERSION,
    DVHAnalysis,
    DVHEngineError,
    analyze_dvh,
    list_structure_rois,
    request_fingerprint,
)
from rt_connect_api.services.dvh_limit_adapter import (
    DvhLimitAdapterError,
    DvhLimitBinding,
    evaluate_dvh_limit,
    resolve_dvh_limit_binding,
)
from rt_connect_api.services.object_storage import ObjectStorage, ObjectStorageError, get_storage
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

router = APIRouter(
    prefix="/organizations/{organization_id}/qa-cases/{case_id}/dvh",
    tags=["dvh"],
)

CoveragePolicy = Literal["FULL_ROI", "OVERLAP_ONLY"]
ExportFormat = Literal["JSON", "CSV"]


class DvhRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    dose_artifact_id: UUID
    structure_artifact_id: UUID
    ct_artifact_id: UUID | None = None
    roi_number: int = Field(gt=0)
    coverage_policy: CoveragePolicy = "FULL_ROI"
    slice_thickness_mm: float | None = Field(default=None, gt=0)
    dx_percentages: list[float] = Field(
        default_factory=lambda: list(DEFAULT_DX_PERCENTAGES), min_length=1, max_length=20
    )
    vx_doses_gy: list[float] = Field(
        default_factory=lambda: list(DEFAULT_VX_DOSES_GY), min_length=1, max_length=20
    )
    preview_limit: int = Field(default=4096, ge=64, le=16_384)
    limit_entry_id: UUID | None = None
    protocol_version_id: UUID | None = None
    protocol_metric_key: str | None = Field(default=None, min_length=1, max_length=120)
    limit_override: dict[str, object] = Field(default_factory=dict)


class DvhRunCreateRequest(DvhRequest):
    idempotency_key: str = Field(min_length=8, max_length=200)


class DvhValidationResponse(BaseModel):
    valid: bool
    errors: list[dict[str, object]]
    warnings: list[dict[str, object]]
    normalized_input: dict[str, object] | None = None
    preview: dict[str, object] | None = None


class DvhArtifactChoice(BaseModel):
    id: UUID
    artifact_type: str
    modality: str | None
    original_filename: str
    sha256: str
    byte_size: int
    data_status: str
    frame_of_reference_uid: str | None
    metadata: dict[str, object]


class DvhInputsResponse(BaseModel):
    case_id: UUID
    dose_artifacts: list[DvhArtifactChoice]
    structure_artifacts: list[DvhArtifactChoice]
    ct_artifacts: list[DvhArtifactChoice]
    rois: list[dict[str, object]]


class DvhRunResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qa_case_id: UUID
    dose_artifact_id: UUID
    structure_artifact_id: UUID
    ct_artifact_id: UUID | None
    roi_number: int
    idempotency_key: str
    engine_key: str
    engine_version: str
    status: str
    input_snapshot: dict[str, object]
    result_snapshot: dict[str, object]
    warning_snapshot: list[dict[str, object]]
    error_snapshot: list[dict[str, object]]
    created_by_user_identity_id: UUID | None
    created_at: str
    updated_at: str


class DvhRunCollectionResponse(BaseModel):
    items: list[DvhRunResponse]
    total: int


@dataclass(frozen=True)
class _ResolvedArtifact:
    artifact: Artifact
    manifest: InputManifest


@dataclass(frozen=True)
class _ResolvedInputs:
    dose: _ResolvedArtifact
    structure: _ResolvedArtifact
    ct: _ResolvedArtifact | None


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
        raise DomainError("QA_CASE_ARCHIVED", "Archived QA cases cannot run DVH analysis.", 409)
    return case


def _storage(request: Request) -> ObjectStorage:
    try:
        return get_storage(request.app.state.settings)
    except ObjectStorageError as exc:
        raise DomainError(
            "DVH_STORAGE_UNAVAILABLE",
            "Durable artifact storage is not configured for DVH analysis.",
            503,
        ) from exc


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
            "DVH_INPUT_MANIFEST_REQUIRED",
            "A validated Input Manifest is required before DVH analysis.",
            422,
        )
    if manifest.validation_summary.get("result") != "VALID":
        raise DomainError(
            "DVH_INPUT_NOT_VALIDATED",
            "Every DVH input must have a VALID artifact validation result.",
            422,
        )
    checksum = manifest.checksum_at_use
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
        raise DomainError(
            "DVH_INPUT_MANIFEST_INVALID",
            "The input manifest checksum is malformed.",
            422,
        )
    return manifest


def _resolve_artifact(
    session: Session,
    context: SessionContext,
    case: QACase,
    artifact_id: UUID,
    *,
    expected_modality: str,
    label: str,
) -> _ResolvedArtifact:
    artifact = session.scalar(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.organization_id == context.organization_id,
            Artifact.qa_case_id == case.id,
        )
    )
    if artifact is None:
        raise DomainError(
            "DVH_INPUT_SCOPE_MISMATCH",
            f"The selected {label} artifact is not part of this organization and QA case.",
            422,
        )
    if artifact.artifact_type != "DICOM" or artifact.modality != expected_modality:
        code = {
            "RTDOSE": "DVH_DOSE_ARTIFACT_INVALID",
            "RTSTRUCT": "DVH_STRUCTURE_ARTIFACT_INVALID",
            "CT": "DVH_ANATOMY_ARTIFACT_INVALID",
        }[expected_modality]
        raise DomainError(
            code,
            f"The selected {label} artifact must be a DICOM {expected_modality} dataset.",
            422,
        )
    if artifact.data_status != "VALID":
        raise DomainError(
            "DVH_INPUT_NOT_VALIDATED",
            f"The selected {label} artifact must have validation status VALID.",
            422,
        )
    return _ResolvedArtifact(
        artifact=artifact,
        manifest=_manifest_for_artifact(session, context.organization_id, artifact.id),
    )


def _resolve_inputs(
    session: Session, context: SessionContext, case: QACase, request: DvhRequest
) -> _ResolvedInputs:
    if request.dose_artifact_id == request.structure_artifact_id:
        raise DomainError(
            "DVH_INPUTS_MUST_DIFFER",
            "The RTDOSE and RTSTRUCT inputs must be different artifacts.",
            422,
        )
    dose = _resolve_artifact(
        session,
        context,
        case,
        request.dose_artifact_id,
        expected_modality="RTDOSE",
        label="dose",
    )
    structure = _resolve_artifact(
        session,
        context,
        case,
        request.structure_artifact_id,
        expected_modality="RTSTRUCT",
        label="structure",
    )
    ct = (
        _resolve_artifact(
            session,
            context,
            case,
            request.ct_artifact_id,
            expected_modality="CT",
            label="anatomy",
        )
        if request.ct_artifact_id is not None
        else None
    )
    return _ResolvedInputs(dose=dose, structure=structure, ct=ct)


def _artifact_snapshot(resolved: _ResolvedArtifact) -> dict[str, object]:
    artifact = resolved.artifact
    return {
        "artifact_id": str(artifact.id),
        "filename": artifact.original_filename,
        "artifact_type": artifact.artifact_type,
        "modality": artifact.modality,
        "sha256": artifact.sha256,
        "byte_size": artifact.byte_size,
        "frame_of_reference_uid": artifact.frame_of_reference_uid,
        "manifest_id": str(resolved.manifest.id),
        "manifest_checksum_at_use": resolved.manifest.checksum_at_use,
        "selected_metadata": resolved.manifest.selected_metadata,
        "geometry_summary": resolved.manifest.geometry_summary,
        "unit_summary": resolved.manifest.unit_summary,
        "validation_summary": resolved.manifest.validation_summary,
    }


def _input_snapshot(
    case: QACase, request: DvhRequest, inputs: _ResolvedInputs, analysis: DVHAnalysis
) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "schema_version": "visual-dose-dvh.input.v1",
        "qa_case_id": str(case.id),
        "dose": _artifact_snapshot(inputs.dose),
        "structure": _artifact_snapshot(inputs.structure),
        "ct": _artifact_snapshot(inputs.ct) if inputs.ct is not None else None,
        "analysis": analysis.normalized_input,
        "limit_binding": analysis.normalized_input.get("limit_binding"),
    }
    snapshot["request_fingerprint"] = request_fingerprint(snapshot)
    return snapshot


def _engine_details(exc: DVHEngineError) -> list[dict[str, object]]:
    return exc.details or ([{"field": exc.field, "message": exc.message}] if exc.field else [])


def _engine_errors(exc: DVHEngineError) -> list[dict[str, object]]:
    return [
        {
            "code": exc.code,
            "field": item.get("field") if isinstance(item.get("field"), str) else exc.field,
            "message": item.get("message") if isinstance(item.get("message"), str) else exc.message,
        }
        for item in _engine_details(exc)
    ] or [{"code": exc.code, "field": exc.field, "message": exc.message}]


def _limit_errors(exc: DvhLimitAdapterError) -> list[dict[str, object]]:
    return [
        {
            "code": exc.code,
            "field": item.get("field") if isinstance(item.get("field"), str) else exc.field,
            "message": item.get("message")
            if isinstance(item.get("message"), str)
            else exc.message,
        }
        for item in exc.details
    ] or [{"code": exc.code, "field": exc.field, "message": exc.message}]


def _apply_limit_binding(
    analysis: DVHAnalysis, binding: DvhLimitBinding | None
) -> DVHAnalysis:
    """Add explicit limit evaluation without changing the pure DVH engine."""

    if binding is None:
        return analysis
    evaluation = evaluate_dvh_limit(analysis.result, binding)
    warnings = [*analysis.warnings, *binding.warnings]
    result = dict(analysis.result)
    engine_result_sha = result.pop("result_sha256", None)
    if isinstance(engine_result_sha, str):
        result["engine_result_sha256"] = engine_result_sha
    result["limit_evaluation"] = evaluation
    result["warnings"] = warnings
    result["result_sha256"] = request_fingerprint(result)
    normalized = dict(analysis.normalized_input)
    normalized["limit_binding"] = binding.snapshot
    return DVHAnalysis(normalized_input=normalized, result=result, warnings=warnings)


@contextmanager
def _download_inputs(
    storage: ObjectStorage, inputs: _ResolvedInputs
) -> Iterator[tuple[Path, Path, Path | None]]:
    with tempfile.TemporaryDirectory(prefix="rt-connect-dvh-") as directory:
        root = Path(directory)
        dose_path = root / "input-0.dcm"
        structure_path = root / "input-1.dcm"
        ct_path = root / "input-2.dcm"
        for index, resolved in enumerate((inputs.dose, inputs.structure, inputs.ct)):
            if resolved is None:
                continue
            path = root / f"input-{index}.dcm"
            try:
                storage.download_to_path(resolved.artifact.object_key, path)
            except ObjectStorageError as exc:
                raise DomainError(
                    "DVH_STORAGE_UNAVAILABLE",
                    "A selected DVH artifact could not be read from durable storage.",
                    503,
                ) from exc
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != resolved.artifact.sha256 or digest != resolved.manifest.checksum_at_use:
                raise DomainError(
                    "DVH_SOURCE_CHANGED",
                    "A selected artifact no longer matches its stored checksum snapshot.",
                    409,
                    [{"field": "sha256", "message": resolved.artifact.original_filename}],
                )
        yield dose_path, structure_path, ct_path if inputs.ct is not None else None


def _analyze(
    request: DvhRequest,
    inputs: _ResolvedInputs,
    storage: ObjectStorage,
    max_voxels: int,
) -> DVHAnalysis:
    with _download_inputs(storage, inputs) as paths:
        try:
            return analyze_dvh(
                paths[0],
                paths[1],
                roi_number=request.roi_number,
                coverage_policy=request.coverage_policy,
                slice_thickness_mm=request.slice_thickness_mm,
                dx_percentages=request.dx_percentages,
                vx_doses_gy=request.vx_doses_gy,
                ct_path=paths[2],
                max_voxels=max_voxels,
                preview_limit=request.preview_limit,
            )
        except DVHEngineError:
            raise
        except (OSError, ValueError, TypeError) as exc:
            raise DomainError(
                "DVH_EXECUTION_FAILED",
                "The DVH engine could not complete the selected calculation.",
                422,
            ) from exc


def _actor_id(session: Session, context: SessionContext) -> UUID | None:
    return session.scalar(
        select(UserIdentity.id).where(UserIdentity.supabase_user_id == context.subject)
    )


def _run_response(run: DVHAnalysisRun) -> DvhRunResponse:
    return DvhRunResponse(
        id=run.id,
        organization_id=run.organization_id,
        qa_case_id=run.qa_case_id,
        dose_artifact_id=run.dose_artifact_id,
        structure_artifact_id=run.structure_artifact_id,
        ct_artifact_id=run.ct_artifact_id,
        roi_number=run.roi_number,
        idempotency_key=run.idempotency_key,
        engine_key=run.engine_key,
        engine_version=run.engine_version,
        status=run.status,
        input_snapshot=run.input_snapshot,
        result_snapshot=run.result_snapshot,
        warning_snapshot=run.warning_snapshot,
        error_snapshot=run.error_snapshot,
        created_by_user_identity_id=run.created_by_user_identity_id,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
    )


def _run_for_scope(
    session: Session, context: SessionContext, case_id: UUID, run_id: UUID
) -> DVHAnalysisRun:
    run = session.scalar(
        select(DVHAnalysisRun).where(
            DVHAnalysisRun.id == run_id,
            DVHAnalysisRun.organization_id == context.organization_id,
            DVHAnalysisRun.qa_case_id == case_id,
        )
    )
    if run is None:
        raise DomainError("DVH_RUN_NOT_FOUND", "The DVH run was not found in this QA case.", 404)
    return run


def _commit_run(
    session: Session, organization_id: UUID, idempotency_key: str, fingerprint: str
) -> DVHAnalysisRun | None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        existing = session.scalar(
            select(DVHAnalysisRun).where(
                DVHAnalysisRun.organization_id == organization_id,
                DVHAnalysisRun.idempotency_key == idempotency_key,
            )
        )
        if existing is not None and existing.request_fingerprint == fingerprint:
            return existing
        raise DomainError(
            "DVH_IDEMPOTENCY_CONFLICT",
            "The idempotency key is already associated with another DVH request.",
            409,
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DomainError(
            "DVH_PERSISTENCE_FAILED",
            "The DVH result could not be persisted safely.",
            503,
        ) from exc
    return None


def _choice(artifact: Artifact) -> DvhArtifactChoice:
    return DvhArtifactChoice(
        id=artifact.id,
        artifact_type=artifact.artifact_type,
        modality=artifact.modality,
        original_filename=artifact.original_filename,
        sha256=artifact.sha256,
        byte_size=artifact.byte_size,
        data_status=artifact.data_status,
        frame_of_reference_uid=artifact.frame_of_reference_uid,
        metadata=artifact.metadata_snapshot,
    )


@router.get("/inputs", response_model=DvhInputsResponse)
def list_dvh_inputs(
    organization_id: UUID,
    case_id: UUID,
    structure_artifact_id: UUID | None = Query(default=None),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(_storage),
) -> DvhInputsResponse:
    """List validated RTDOSE/RTSTRUCT/CT choices and, optionally, ROI IDs."""

    context = _context_for_organization(organization_id, identity, session)
    case = _case_or_error(session, context, case_id)
    artifacts = list(
        session.scalars(
            select(Artifact)
            .where(
                Artifact.organization_id == context.organization_id,
                Artifact.qa_case_id == case.id,
                Artifact.artifact_type == "DICOM",
                Artifact.data_status == "VALID",
                Artifact.modality.in_(["RTDOSE", "RTSTRUCT", "CT"]),
            )
            .order_by(Artifact.created_at.desc())
        )
    )
    rois: list[dict[str, object]] = []
    if structure_artifact_id is not None:
        structure = _resolve_artifact(
            session,
            context,
            case,
            structure_artifact_id,
            expected_modality="RTSTRUCT",
            label="structure",
        )
        with tempfile.TemporaryDirectory(prefix="rt-connect-dvh-rois-") as directory:
            path = Path(directory) / "structure.dcm"
            try:
                storage.download_to_path(structure.artifact.object_key, path)
            except ObjectStorageError as exc:
                raise DomainError(
                    "DVH_STORAGE_UNAVAILABLE",
                    "The RTSTRUCT artifact could not be read from durable storage.",
                    503,
                ) from exc
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != structure.artifact.sha256:
                raise DomainError(
                    "DVH_SOURCE_CHANGED",
                    "The selected RTSTRUCT no longer matches its stored checksum.",
                    409,
                )
            try:
                rois = list_structure_rois(path)
            except DVHEngineError as exc:
                raise DomainError(exc.code, exc.message, 422, _engine_details(exc)) from exc
    return DvhInputsResponse(
        case_id=case.id,
        dose_artifacts=[_choice(item) for item in artifacts if item.modality == "RTDOSE"],
        structure_artifacts=[_choice(item) for item in artifacts if item.modality == "RTSTRUCT"],
        ct_artifacts=[_choice(item) for item in artifacts if item.modality == "CT"],
        rois=rois,
    )


@router.post("/validate", response_model=DvhValidationResponse)
def validate_dvh(
    request: DvhRequest,
    organization_id: UUID,
    case_id: UUID,
    http_request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(_storage),
) -> DvhValidationResponse:
    """Run geometry and metric validation without creating a database row."""

    context = _context_for_organization(organization_id, identity, session)
    case = _case_or_error(session, context, case_id)
    inputs = _resolve_inputs(session, context, case, request)
    try:
        binding = resolve_dvh_limit_binding(
            session,
            context.organization_id,
            limit_entry_id=request.limit_entry_id,
            protocol_version_id=request.protocol_version_id,
            protocol_metric_key=request.protocol_metric_key,
            override=request.limit_override,
        )
        analysis = _analyze(
            request,
            inputs,
            storage,
            int(getattr(http_request.app.state.settings, "gamma_max_voxels", 2_000_000)),
        )
        analysis = _apply_limit_binding(analysis, binding)
    except DVHEngineError as exc:
        return DvhValidationResponse(
            valid=False,
            errors=_engine_errors(exc),
            warnings=[],
        )
    except DvhLimitAdapterError as exc:
        return DvhValidationResponse(
            valid=False,
            errors=_limit_errors(exc),
            warnings=[],
        )
    return DvhValidationResponse(
        valid=True,
        errors=[],
        warnings=[
            {
                "code": item.get("code") if isinstance(item.get("code"), str) else "DVH_WARNING",
                "field": item.get("field") if isinstance(item.get("field"), str) else None,
                "message": item.get("message")
                if isinstance(item.get("message"), str)
                else "Review the DVH warning.",
            }
            for item in analysis.warnings
        ],
        normalized_input=analysis.normalized_input,
        preview=analysis.result,
    )


@router.post("/runs", response_model=DvhRunResponse, status_code=status.HTTP_201_CREATED)
def create_dvh_run(
    request: DvhRunCreateRequest,
    organization_id: UUID,
    case_id: UUID,
    http_request: Request,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(_storage),
) -> DvhRunResponse:
    context = _context_for_organization(organization_id, identity, session)
    case = _case_or_error(session, context, case_id)
    inputs = _resolve_inputs(session, context, case, request)
    try:
        binding = resolve_dvh_limit_binding(
            session,
            context.organization_id,
            limit_entry_id=request.limit_entry_id,
            protocol_version_id=request.protocol_version_id,
            protocol_metric_key=request.protocol_metric_key,
            override=request.limit_override,
        )
        analysis = _analyze(
            request,
            inputs,
            storage,
            int(getattr(http_request.app.state.settings, "gamma_max_voxels", 2_000_000)),
        )
    except DVHEngineError as exc:
        raise DomainError(exc.code, exc.message, 422, _engine_details(exc)) from exc
    except DvhLimitAdapterError as exc:
        raise DomainError(exc.code, exc.message, 422, _limit_errors(exc)) from exc
    try:
        analysis = _apply_limit_binding(analysis, binding)
    except DvhLimitAdapterError as exc:
        raise DomainError(exc.code, exc.message, 422, _limit_errors(exc)) from exc
    snapshot = _input_snapshot(case, request, inputs, analysis)
    fingerprint = str(snapshot["request_fingerprint"])
    existing = session.scalar(
        select(DVHAnalysisRun).where(
            DVHAnalysisRun.organization_id == context.organization_id,
            DVHAnalysisRun.idempotency_key == request.idempotency_key,
        )
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise DomainError(
                "DVH_IDEMPOTENCY_CONFLICT",
                "The idempotency key is already associated with another DVH request.",
                409,
            )
        response.status_code = status.HTTP_200_OK
        return _run_response(existing)
    run = DVHAnalysisRun(
        organization_id=context.organization_id,
        qa_case_id=case.id,
        dose_artifact_id=inputs.dose.artifact.id,
        structure_artifact_id=inputs.structure.artifact.id,
        ct_artifact_id=inputs.ct.artifact.id if inputs.ct is not None else None,
        roi_number=request.roi_number,
        idempotency_key=request.idempotency_key,
        request_fingerprint=fingerprint,
        engine_key=DVH_ENGINE_KEY,
        engine_version=DVH_ENGINE_VERSION,
        status="COMPLETED",
        input_snapshot=snapshot,
        result_snapshot=analysis.result,
        warning_snapshot=analysis.warnings,
        error_snapshot=[],
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(run)
    session.flush()
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=run.created_by_user_identity_id,
            event_type="DVH_ANALYSIS_COMPLETED",
            entity_type="DVHAnalysisRun",
            entity_id=run.id,
            payload={
                "qa_case_id": str(case.id),
                "roi_number": request.roi_number,
                "engine_version": DVH_ENGINE_VERSION,
                "result_sha256": analysis.result.get("result_sha256"),
            },
        )
    )
    concurrent = _commit_run(
        session,
        context.organization_id,
        request.idempotency_key,
        fingerprint,
    )
    if concurrent is not None:
        response.status_code = status.HTTP_200_OK
        return _run_response(concurrent)
    return _run_response(run)


@router.get("/runs", response_model=DvhRunCollectionResponse)
def list_dvh_runs(
    organization_id: UUID,
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> DvhRunCollectionResponse:
    context = _context_for_organization(organization_id, identity, session)
    case = _case_or_error(session, context, case_id)
    runs = list(
        session.scalars(
            select(DVHAnalysisRun)
            .where(
                DVHAnalysisRun.organization_id == context.organization_id,
                DVHAnalysisRun.qa_case_id == case.id,
            )
            .order_by(DVHAnalysisRun.created_at.desc())
        )
    )
    return DvhRunCollectionResponse(items=[_run_response(item) for item in runs], total=len(runs))


@router.get("/runs/{run_id}/export")
def export_dvh_run(
    run_id: UUID,
    organization_id: UUID,
    case_id: UUID,
    export_format: ExportFormat = Query(default="JSON"),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> Response:
    context = _context_for_organization(organization_id, identity, session)
    _case_or_error(session, context, case_id)
    run = _run_for_scope(session, context, case_id, run_id)
    payload = _run_response(run).model_dump(mode="json")
    if export_format == "JSON":
        return Response(
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="rt-connect-dvh-{run.id}.json"'},
        )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "key", "value"])
    for section, values in (
        ("input", run.input_snapshot),
        ("result", run.result_snapshot),
        ("warning", {str(index): value for index, value in enumerate(run.warning_snapshot)}),
    ):
        for key, value in values.items():
            writer.writerow([section, key, json.dumps(value, ensure_ascii=False)])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="rt-connect-dvh-{run.id}.csv"'},
    )


@router.get("/runs/{run_id}", response_model=DvhRunResponse)
def get_dvh_run(
    run_id: UUID,
    organization_id: UUID,
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> DvhRunResponse:
    context = _context_for_organization(organization_id, identity, session)
    _case_or_error(session, context, case_id)
    return _run_response(_run_for_scope(session, context, case_id, run_id))
