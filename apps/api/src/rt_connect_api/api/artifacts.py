"""P6 artifact upload, provenance manifest and metadata validation endpoints."""

from __future__ import annotations

import hashlib
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    Artifact,
    AuditEvent,
    InputManifest,
    QACase,
    UserIdentity,
    ValidationRun,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.artifact_validation import (
    VALIDATOR_VERSION,
    validate_artifact,
)
from rt_connect_api.services.object_storage import (
    ObjectStorage,
    ObjectStorageError,
    get_storage,
)
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["artifacts"])

ArtifactType = Literal["DICOM", "MEASUREMENT", "CSV", "JSON", "IMAGE", "PDF", "OTHER"]
LogicalRole = Literal["REFERENCE", "EVALUATION", "CT", "RTSTRUCT", "RTPLAN", "MEASUREMENT", "OTHER"]


class ArtifactResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qa_case_id: UUID | None
    artifact_type: str
    modality: str | None
    original_filename: str
    byte_size: int
    media_type: str
    sha256: str
    sop_class_uid: str | None
    sop_instance_uid: str | None
    study_instance_uid: str | None
    series_instance_uid: str | None
    frame_of_reference_uid: str | None
    source_system: str | None
    uploaded_at: datetime
    data_status: str
    parent_artifact_id: UUID | None
    metadata_snapshot: dict[str, object]
    logical_roles: list[str] = Field(default_factory=list)


class ArtifactUploadResponse(ArtifactResponse):
    duplicate: bool = False


class ArtifactCollectionResponse(BaseModel):
    items: list[ArtifactResponse]
    total: int
    offset: int
    limit: int


class DownloadResponse(BaseModel):
    artifact_id: UUID
    url: str
    expires_at: datetime


class ValidationRunResponse(BaseModel):
    id: UUID
    subject_type: str
    subject_id: UUID
    validation_type: str
    validator_version: str
    started_at: datetime
    completed_at: datetime | None
    result: str
    checks: list[dict[str, object]]
    warnings: list[dict[str, object]]
    errors: list[dict[str, object]]
    input_manifest_snapshot: dict[str, object]


class ValidationCollectionResponse(BaseModel):
    items: list[ValidationRunResponse]
    total: int


class InputManifestResponse(BaseModel):
    id: UUID
    organization_id: UUID
    analysis_run_id: UUID | None
    artifact_id: UUID
    logical_role: str
    checksum_at_use: str
    selected_metadata: dict[str, object]
    geometry_summary: dict[str, object]
    unit_summary: dict[str, object]
    validation_summary: dict[str, object]
    created_at: datetime


def _storage(request: Request) -> ObjectStorage:
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


def _identity_id(session: Session, subject: str) -> UUID | None:
    return session.scalar(select(UserIdentity.id).where(UserIdentity.supabase_user_id == subject))


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
        raise DomainError(
            "QA_CASE_ARCHIVED", "Archived QA cases cannot receive new artifacts.", 409
        )
    return case


def _artifact_or_error(session: Session, context: SessionContext, artifact_id: UUID) -> Artifact:
    artifact = session.scalar(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.organization_id == context.organization_id,
        )
    )
    if artifact is None:
        raise DomainError("ARTIFACT_NOT_FOUND", "Artifact was not found in this organization.", 404)
    return artifact


def _artifact_response(
    artifact: Artifact,
    duplicate: bool = False,
    logical_roles: list[str] | None = None,
) -> ArtifactUploadResponse:
    return ArtifactUploadResponse(
        id=artifact.id,
        organization_id=artifact.organization_id,
        qa_case_id=artifact.qa_case_id,
        artifact_type=artifact.artifact_type,
        modality=artifact.modality,
        original_filename=artifact.original_filename,
        byte_size=artifact.byte_size,
        media_type=artifact.media_type,
        sha256=artifact.sha256,
        sop_class_uid=artifact.sop_class_uid,
        sop_instance_uid=artifact.sop_instance_uid,
        study_instance_uid=artifact.study_instance_uid,
        series_instance_uid=artifact.series_instance_uid,
        frame_of_reference_uid=artifact.frame_of_reference_uid,
        source_system=artifact.source_system,
        uploaded_at=artifact.uploaded_at,
        data_status=artifact.data_status,
        parent_artifact_id=artifact.parent_artifact_id,
        metadata_snapshot=artifact.metadata_snapshot,
        logical_roles=logical_roles or [],
        duplicate=duplicate,
    )


def _artifact_roles(
    session: Session, organization_id: UUID, artifact_ids: list[UUID]
) -> dict[UUID, list[str]]:
    if not artifact_ids:
        return {}
    roles: dict[UUID, list[str]] = {}
    rows = session.execute(
        select(InputManifest.artifact_id, InputManifest.logical_role)
        .where(
            InputManifest.organization_id == organization_id,
            InputManifest.artifact_id.in_(artifact_ids),
        )
        .order_by(InputManifest.created_at)
    )
    for artifact_id, logical_role in rows:
        roles.setdefault(artifact_id, [])
        if logical_role not in roles[artifact_id]:
            roles[artifact_id].append(logical_role)
    return roles


def _validation_response(run: ValidationRun) -> ValidationRunResponse:
    return ValidationRunResponse(
        id=run.id,
        subject_type=run.subject_type,
        subject_id=run.subject_id,
        validation_type=run.validation_type,
        validator_version=run.validator_version,
        started_at=run.started_at,
        completed_at=run.completed_at,
        result=run.result,
        checks=run.checks,
        warnings=run.warnings,
        errors=run.errors,
        input_manifest_snapshot=run.input_manifest_snapshot,
    )


def _manifest_response(manifest: InputManifest) -> InputManifestResponse:
    return InputManifestResponse(
        id=manifest.id,
        organization_id=manifest.organization_id,
        analysis_run_id=manifest.analysis_run_id,
        artifact_id=manifest.artifact_id,
        logical_role=manifest.logical_role,
        checksum_at_use=manifest.checksum_at_use,
        selected_metadata=manifest.selected_metadata,
        geometry_summary=manifest.geometry_summary,
        unit_summary=manifest.unit_summary,
        validation_summary=manifest.validation_summary,
        created_at=manifest.created_at,
    )


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
            actor_user_identity_id=_identity_id(session, context.subject),
            event_type=event_type,
            entity_type="Artifact",
            entity_id=entity_id,
            payload=payload,
        )
    )


def _commit_or_raise(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "ARTIFACT_CONFLICT", "Artifact metadata conflicted with existing data.", 409
        ) from exc


@router.post(
    "/qa-cases/{case_id}/artifacts",
    response_model=ArtifactUploadResponse,
)
def upload_artifact(
    case_id: UUID,
    response: Response,
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    artifact_type: ArtifactType = Form(default="OTHER"),  # noqa: B008
    logical_role: LogicalRole = Form(default="OTHER"),  # noqa: B008
    source_system: str | None = Form(default=None, max_length=200),  # noqa: B008
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
    storage: ObjectStorage = Depends(_storage),  # noqa: B008
) -> ArtifactUploadResponse:
    context = _context(identity, session)
    case = _case_or_error(session, context, case_id)
    original_filename = (file.filename or "uploaded-artifact").strip() or "uploaded-artifact"
    with tempfile.NamedTemporaryFile(
        prefix="rt-connect-upload-", suffix=".bin", delete=False
    ) as handle:
        temp_path = Path(handle.name)
        digest = hashlib.sha256()
        byte_size = 0
        while chunk := file.file.read(1024 * 1024):
            byte_size += len(chunk)
            if byte_size > request.app.state.settings.max_upload_bytes:
                temp_path.unlink(missing_ok=True)
                raise DomainError(
                    "UPLOAD_TOO_LARGE", "Uploaded artifact exceeds the configured size limit.", 413
                )
            digest.update(chunk)
            handle.write(chunk)
    sha256 = digest.hexdigest()
    # A checksum identifies the bytes, but the declared artifact type is part of
    # the input contract.  The same bytes can be uploaded once as a raw DICOM
    # object and once as a validated JSON/measurement representation.  Reusing
    # an artifact across those declarations would make the UI appear to accept
    # JSON while Gamma later sees the old DICOM metadata.
    existing = session.scalar(
        select(Artifact)
        .where(
            Artifact.organization_id == context.organization_id,
            Artifact.qa_case_id == case.id,
            Artifact.sha256 == sha256,
            Artifact.artifact_type == artifact_type,
        )
        .order_by(Artifact.created_at.desc())
    )
    if existing is not None:
        temp_path.unlink(missing_ok=True)
        manifest = session.scalar(
            select(InputManifest)
            .where(
                InputManifest.organization_id == context.organization_id,
                InputManifest.artifact_id == existing.id,
                InputManifest.logical_role == logical_role,
            )
            .order_by(InputManifest.created_at.desc())
        )
        if manifest is None:
            source_manifest = session.scalar(
                select(InputManifest)
                .where(
                    InputManifest.organization_id == context.organization_id,
                    InputManifest.artifact_id == existing.id,
                )
                .order_by(InputManifest.created_at.desc())
            )
            session.add(
                InputManifest(
                    organization_id=context.organization_id,
                    artifact_id=existing.id,
                    logical_role=logical_role,
                    checksum_at_use=sha256,
                    selected_metadata=existing.metadata_snapshot,
                    geometry_summary=(
                        source_manifest.geometry_summary if source_manifest is not None else {}
                    ),
                    unit_summary=(
                        source_manifest.unit_summary if source_manifest is not None else {}
                    ),
                    validation_summary=(
                        source_manifest.validation_summary
                        if source_manifest is not None
                        else {"state": "PENDING"}
                    ),
                )
            )
            _commit_or_raise(session)
        response.status_code = status.HTTP_200_OK
        return _artifact_response(existing, duplicate=True, logical_roles=[logical_role])

    artifact_id = uuid4()
    media_type = file.content_type or "application/octet-stream"
    try:
        preliminary = validate_artifact(temp_path, artifact_type, media_type, original_filename)
        metadata = preliminary.metadata
        object_key = (
            f"organizations/{context.organization_id}/qa-cases/{case.id}/artifacts/"
            f"{artifact_id}/{sha256}"
        )
        storage.ensure_bucket()
        with temp_path.open("rb") as source:
            storage.put_object(object_key, source, byte_size, media_type)
    except ObjectStorageError as exc:
        raise DomainError(
            "OBJECT_STORAGE_UNAVAILABLE", "Artifact storage is temporarily unavailable.", 503
        ) from exc
    finally:
        temp_path.unlink(missing_ok=True)

    artifact = Artifact(
        id=artifact_id,
        organization_id=context.organization_id,
        qa_case_id=case.id,
        artifact_type=artifact_type,
        modality=metadata.get("modality") if isinstance(metadata.get("modality"), str) else None,
        original_filename=original_filename,
        object_key=object_key,
        byte_size=byte_size,
        media_type=media_type,
        sha256=sha256,
        sop_class_uid=metadata.get("sop_class_uid")
        if isinstance(metadata.get("sop_class_uid"), str)
        else None,
        sop_instance_uid=metadata.get("sop_instance_uid")
        if isinstance(metadata.get("sop_instance_uid"), str)
        else None,
        study_instance_uid=metadata.get("study_instance_uid")
        if isinstance(metadata.get("study_instance_uid"), str)
        else None,
        series_instance_uid=metadata.get("series_instance_uid")
        if isinstance(metadata.get("series_instance_uid"), str)
        else None,
        frame_of_reference_uid=metadata.get("frame_of_reference_uid")
        if isinstance(metadata.get("frame_of_reference_uid"), str)
        else None,
        source_system=source_system,
        uploaded_by_user_identity_id=_identity_id(session, context.subject),
        data_status="UPLOADED",
        metadata_snapshot=metadata,
    )
    session.add(artifact)
    session.add(
        InputManifest(
            organization_id=context.organization_id,
            artifact_id=artifact.id,
            logical_role=logical_role,
            checksum_at_use=sha256,
            selected_metadata=metadata,
            geometry_summary=metadata.get("grid", {})
            if isinstance(metadata.get("grid", {}), dict)
            else {},
            unit_summary={"dose_units": metadata.get("dose_units")}
            if metadata.get("dose_units")
            else {},
            validation_summary={"state": "PENDING"},
        )
    )
    try:
        session.flush()
        _audit(
            session,
            context,
            "ARTIFACT_UPLOADED",
            artifact.id,
            {"sha256": sha256, "byte_size": byte_size},
        )
        _commit_or_raise(session)
    except Exception:
        # The object was already written, but the database transaction did
        # not commit.  Remove the unreferenced object before returning the
        # original failure.  If compensation fails, expose a stable
        # reconciliation signal rather than claiming that the upload failed
        # cleanly while leaving an orphan in durable storage.
        session.rollback()
        try:
            storage.delete_object(object_key)
        except ObjectStorageError as cleanup_exc:
            raise DomainError(
                "ARTIFACT_PERSISTENCE_FAILED",
                "Artifact metadata could not be committed and storage cleanup "
                "requires reconciliation.",
                503,
            ) from cleanup_exc
        raise
    response.status_code = status.HTTP_201_CREATED
    return _artifact_response(artifact, logical_roles=[logical_role])


@router.get("/qa-cases/{case_id}/artifacts", response_model=ArtifactCollectionResponse)
def list_artifacts(
    case_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> ArtifactCollectionResponse:
    context = _context(identity, session)
    _case_or_error(session, context, case_id)
    query = select(Artifact).where(
        Artifact.organization_id == context.organization_id,
        Artifact.qa_case_id == case_id,
    )
    items = session.scalars(
        query.order_by(Artifact.created_at.desc()).offset(offset).limit(limit)
    ).all()
    roles = _artifact_roles(session, context.organization_id, [item.id for item in items])
    total = (
        session.scalar(
            select(func.count())
            .select_from(Artifact)
            .where(
                Artifact.organization_id == context.organization_id,
                Artifact.qa_case_id == case_id,
            )
        )
        or 0
    )
    return ArtifactCollectionResponse(
        items=[_artifact_response(item, logical_roles=roles.get(item.id, [])) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(
    artifact_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> ArtifactResponse:
    context = _context(identity, session)
    artifact = _artifact_or_error(session, context, artifact_id)
    roles = _artifact_roles(session, context.organization_id, [artifact.id])
    return _artifact_response(artifact, logical_roles=roles.get(artifact.id, []))


@router.get("/artifacts/{artifact_id}/download", response_model=DownloadResponse)
def get_download_url(
    artifact_id: UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
    storage: ObjectStorage = Depends(_storage),  # noqa: B008
) -> DownloadResponse:
    context = _context(identity, session)
    artifact = _artifact_or_error(session, context, artifact_id)
    try:
        url = storage.presigned_get(
            artifact.object_key, request.app.state.settings.s3_signed_url_ttl_seconds
        )
    except ObjectStorageError as exc:
        raise DomainError(
            "OBJECT_STORAGE_UNAVAILABLE", "Artifact storage is temporarily unavailable.", 503
        ) from exc
    expires_at = datetime.now(UTC) + timedelta(
        seconds=request.app.state.settings.s3_signed_url_ttl_seconds
    )
    return DownloadResponse(artifact_id=artifact.id, url=url, expires_at=expires_at)


@router.post("/artifacts/{artifact_id}/validate", response_model=ValidationRunResponse)
def validate_uploaded_artifact(
    artifact_id: UUID,
    request: Request,
    force: bool = Query(default=False),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
    storage: ObjectStorage = Depends(_storage),  # noqa: B008
) -> ValidationRunResponse:
    context = _context(identity, session)
    artifact = _artifact_or_error(session, context, artifact_id)
    latest = session.scalar(
        select(ValidationRun)
        .where(
            ValidationRun.organization_id == context.organization_id,
            ValidationRun.subject_type == "Artifact",
            ValidationRun.subject_id == artifact.id,
        )
        .order_by(ValidationRun.created_at.desc())
    )
    if latest is not None and latest.completed_at is not None and not force:
        return _validation_response(latest)
    artifact.data_status = "VALIDATING"
    _commit_or_raise(session)
    with tempfile.NamedTemporaryFile(
        prefix="rt-connect-validation-", suffix=".bin", delete=False
    ) as handle:
        temp_path = Path(handle.name)
    try:
        try:
            storage.download_to_path(artifact.object_key, temp_path)
        except ObjectStorageError as exc:
            artifact.data_status = "INVALID"
            _commit_or_raise(session)
            raise DomainError(
                "OBJECT_STORAGE_UNAVAILABLE", "Artifact storage is temporarily unavailable.", 503
            ) from exc
        result = validate_artifact(
            temp_path, artifact.artifact_type, artifact.media_type, artifact.original_filename
        )
    finally:
        temp_path.unlink(missing_ok=True)
    now = datetime.now(UTC)
    run = ValidationRun(
        id=uuid4(),
        organization_id=context.organization_id,
        subject_type="Artifact",
        subject_id=artifact.id,
        validation_type="DICOM_METADATA"
        if artifact.artifact_type == "DICOM"
        else "MEASUREMENT_SCHEMA"
        if artifact.artifact_type == "MEASUREMENT"
        else "FILE_METADATA",
        validator_version=VALIDATOR_VERSION,
        started_at=now,
        completed_at=now,
        result=result.result,
        checks=result.checks,
        warnings=result.warnings,
        errors=result.errors,
        input_manifest_snapshot={"sha256": artifact.sha256, "byte_size": artifact.byte_size},
    )
    artifact.data_status = result.result
    artifact.metadata_snapshot = result.metadata
    for key in (
        "modality",
        "sop_class_uid",
        "sop_instance_uid",
        "study_instance_uid",
        "series_instance_uid",
        "frame_of_reference_uid",
    ):
        value = result.metadata.get(key)
        if isinstance(value, str):
            setattr(artifact, key, value)
    manifest = session.scalar(
        select(InputManifest)
        .where(
            InputManifest.artifact_id == artifact.id,
            InputManifest.organization_id == context.organization_id,
        )
        .order_by(InputManifest.created_at.desc())
    )
    if manifest is not None:
        manifest.selected_metadata = result.metadata
        grid_value = result.metadata.get("grid", {})
        manifest.geometry_summary = grid_value if isinstance(grid_value, dict) else {}
        manifest.unit_summary = (
            {"dose_units": result.metadata.get("dose_units")}
            if result.metadata.get("dose_units")
            else {}
        )
        manifest.validation_summary = {
            "result": result.result,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    session.add(run)
    session.flush()
    _audit(
        session,
        context,
        "ARTIFACT_VALIDATED",
        artifact.id,
        {"result": result.result, "validator_version": VALIDATOR_VERSION},
    )
    _commit_or_raise(session)
    return _validation_response(run)


@router.get("/artifacts/{artifact_id}/validations", response_model=ValidationCollectionResponse)
def list_validations(
    artifact_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> ValidationCollectionResponse:
    context = _context(identity, session)
    artifact = _artifact_or_error(session, context, artifact_id)
    items = session.scalars(
        select(ValidationRun)
        .where(
            ValidationRun.organization_id == context.organization_id,
            ValidationRun.subject_id == artifact.id,
        )
        .order_by(ValidationRun.created_at.desc())
    ).all()
    return ValidationCollectionResponse(
        items=[_validation_response(item) for item in items], total=len(items)
    )


@router.get("/artifacts/{artifact_id}/manifest", response_model=InputManifestResponse)
def get_manifest(
    artifact_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> InputManifestResponse:
    context = _context(identity, session)
    artifact = _artifact_or_error(session, context, artifact_id)
    manifest = session.scalar(
        select(InputManifest)
        .where(
            InputManifest.organization_id == context.organization_id,
            InputManifest.artifact_id == artifact.id,
        )
        .order_by(InputManifest.created_at.desc())
    )
    if manifest is None:
        raise DomainError(
            "INPUT_MANIFEST_NOT_FOUND", "No input manifest exists for this artifact.", 404
        )
    return _manifest_response(manifest)
