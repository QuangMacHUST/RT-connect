"""User-facing execution and history endpoints for pylinac Machine QA."""

from __future__ import annotations

import hashlib
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from rt_connect_api.api.artifacts import _storage
from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    Artifact,
    AuditEvent,
    InputManifest,
    PylinacQARun,
    QACase,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.qa_catalog import QATestDefinition, get_qa_test_definition
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.object_storage import ObjectStorage, ObjectStorageError
from rt_connect_api.services.pylinac_adapter import PylinacAdapterError, execute_pylinac
from rt_connect_api.services.pylinac_registry import (
    PYLINAC_VERSION,
    RuntimeBinding,
    package_fingerprint,
    runtime_binding,
)
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["pylinac-qa"])

AssessmentStatus = Literal["PASS", "WARNING", "FAIL", "REVIEW", "NOT_ASSESSED"]


class PylinacQARunCreateRequest(BaseModel):
    catalog_key: str = Field(min_length=1, max_length=120)
    artifact_ids: list[UUID] = Field(min_length=0, max_length=8)
    parameters: dict[str, object] = Field(default_factory=dict)


class PylinacAssessmentRequest(BaseModel):
    assessment_status: AssessmentStatus
    note: str | None = Field(default=None, max_length=2000)


class PylinacInputFileResponse(BaseModel):
    filename: str
    artifact_type: str
    modality: str | None
    byte_size: int
    sha256: str
    logical_role: str


class PylinacQARunResponse(BaseModel):
    id: UUID
    catalog_key: str
    name: str
    family: str
    status: str
    assessment_status: str | None
    engine_class: str
    engine_version: str
    package_fingerprint: str
    parameters: dict[str, object]
    input_files: list[PylinacInputFileResponse]
    result_snapshot: dict[str, object]
    warning_snapshot: list[dict[str, object]]
    error_snapshot: list[dict[str, object]]
    overlay_artifact_id: UUID | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PylinacRunCollectionResponse(BaseModel):
    items: list[PylinacQARunResponse]
    total: int


def _context(
    session: Session, identity: AuthenticatedIdentity, organization_id: UUID
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
        raise DomainError("QA_CASE_NOT_FOUND", "Không tìm thấy bài kiểm tra trong đơn vị.", 404)
    if case.is_archived:
        raise DomainError("QA_CASE_ARCHIVED", "Bài kiểm tra đã lưu trữ không thể chạy lại.", 409)
    return case


def _definition_or_error(catalog_key: str) -> tuple[QATestDefinition, RuntimeBinding]:
    definition = get_qa_test_definition(catalog_key)
    if definition is None or definition.engine_name != "pylinac":
        raise DomainError(
            "PYLINAC_CAPABILITY_NOT_FOUND", "Không tìm thấy bài QA Pylinac đã chọn.", 404
        )
    binding = runtime_binding(definition.key)
    if binding is None:
        raise DomainError(
            "PYLINAC_CAPABILITY_NOT_FOUND", "Bài QA này chưa có liên kết bộ tính.", 409
        )
    return definition, binding


def _artifact_inputs(
    session: Session,
    context: SessionContext,
    case: QACase,
    artifact_ids: list[UUID],
) -> list[Artifact]:
    if len(set(artifact_ids)) != len(artifact_ids):
        raise DomainError("PYLINAC_INPUT_DUPLICATE", "Không được chọn trùng tệp đầu vào.", 422)
    artifacts = list(
        session.scalars(
            select(Artifact).where(
                Artifact.organization_id == context.organization_id,
                Artifact.qa_case_id == case.id,
                Artifact.id.in_(artifact_ids),
            )
        )
    )
    by_id = {artifact.id: artifact for artifact in artifacts}
    if len(by_id) != len(artifact_ids):
        raise DomainError(
            "PYLINAC_INPUT_NOT_FOUND",
            "Một hoặc nhiều tệp không thuộc bài kiểm tra hiện tại.",
            404,
        )
    selected = [by_id[artifact_id] for artifact_id in artifact_ids]
    if any(artifact.data_status != "VALID" for artifact in selected):
        raise DomainError(
            "PYLINAC_INPUT_NOT_VALIDATED",
            "Tất cả tệp đầu vào phải được kiểm tra hợp lệ trước khi phân tích. "
            "Hãy bấm “Kiểm tra dữ liệu” rồi thử lại.",
            422,
        )
    return selected


_NON_IMAGE_MODALITIES = frozenset({"RTDOSE", "RTSTRUCT", "RTPLAN"})
_IMAGE_INPUT_PROFILES = frozenset(
    {"image", "image_pair", "image_series", "image_or_profile", "dicom_series", "nuclear"}
)


def _validate_artifact_profile(
    input_profile: str, artifacts: list[Artifact]
) -> None:
    """Reject a validated artifact whose semantic modality cannot feed the QA class.

    Validation answers whether a file is readable and safe to store. It does not
    answer whether that file is the right input for the selected Pylinac family.
    Keep the second check at the API boundary so a stale or overly broad client
    filter cannot send an RTDOSE to an image-analysis class such as Starshot.
    """

    if input_profile not in _IMAGE_INPUT_PROFILES:
        return
    wrong_inputs = [
        artifact
        for artifact in artifacts
        if artifact.artifact_type == "MEASUREMENT"
        or (artifact.modality or "").upper() in _NON_IMAGE_MODALITIES
    ]
    if wrong_inputs:
        raise DomainError(
            "PYLINAC_INPUT_PROFILE_MISMATCH",
            "Bài kiểm tra đã chọn cần ảnh hoặc chuỗi ảnh phù hợp; không thể dùng "
            "tệp liều, cấu trúc RT hoặc kế hoạch xạ trị.",
            422,
        )


def _input_snapshot(artifacts: list[Artifact]) -> dict[str, object]:
    return {
        "schema_version": "p7.pylinac-input.v1",
        "files": [
            {
                "artifact_id": str(artifact.id),
                "filename": artifact.original_filename,
                "artifact_type": artifact.artifact_type,
                "modality": artifact.modality,
                "byte_size": artifact.byte_size,
                "sha256": artifact.sha256,
            }
            for artifact in artifacts
        ],
    }


def _manifest_role(artifact: Artifact) -> str:
    if artifact.modality == "RTDOSE":
        return "EVALUATION"
    return "REFERENCE"


def _run_input_files(session: Session, run: PylinacQARun) -> list[PylinacInputFileResponse]:
    raw_files = run.input_snapshot.get("files", [])
    if not isinstance(raw_files, list):
        return []
    manifests = list(
        session.scalars(
            select(InputManifest).where(
                InputManifest.organization_id == run.organization_id,
                InputManifest.analysis_run_id == run.id,
            )
        )
    )
    roles = {manifest.artifact_id: manifest.logical_role for manifest in manifests}
    response: list[PylinacInputFileResponse] = []
    for item in raw_files:
        if not isinstance(item, dict):
            continue
        try:
            artifact_id = UUID(str(item.get("artifact_id")))
        except (ValueError, TypeError):
            continue
        response.append(
            PylinacInputFileResponse(
                filename=str(item.get("filename", "Tệp đầu vào")),
                artifact_type=str(item.get("artifact_type", "OTHER")),
                modality=str(item["modality"]) if item.get("modality") else None,
                byte_size=int(item.get("byte_size", 0)),
                sha256=str(item.get("sha256", "")),
                logical_role=roles.get(artifact_id, "REFERENCE"),
            )
        )
    return response


def _run_response(session: Session, run: PylinacQARun) -> PylinacQARunResponse:
    definition = get_qa_test_definition(run.catalog_key)
    if definition is None:
        raise DomainError(
            "PYLINAC_CAPABILITY_NOT_FOUND", "Danh mục của lượt chạy không còn tồn tại.", 500
        )
    return PylinacQARunResponse(
        id=run.id,
        catalog_key=run.catalog_key,
        name=definition.name,
        family=definition.family,
        status=run.status,
        assessment_status=run.assessment_status,
        engine_class=run.engine_class,
        engine_version=run.engine_version,
        package_fingerprint=run.package_fingerprint,
        parameters=run.parameters_snapshot,
        input_files=_run_input_files(session, run),
        result_snapshot=run.result_snapshot,
        warning_snapshot=run.warning_snapshot,
        error_snapshot=run.error_snapshot,
        overlay_artifact_id=run.overlay_artifact_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _fail_run(session: Session, run: PylinacQARun, code: str, message: str) -> None:
    run.status = "FAILED"
    run.completed_at = datetime.now(UTC)
    run.error_snapshot = [{"code": code, "message": message}]
    run.warning_snapshot = []
    session.commit()
    session.refresh(run)


@router.post(
    "/qa-cases/{case_id}/pylinac-runs",
    response_model=PylinacQARunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pylinac_run(
    case_id: UUID,
    payload: PylinacQARunCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
    storage: ObjectStorage = Depends(_storage),  # noqa: B008
) -> PylinacQARunResponse:
    """Run a registered pylinac capability synchronously and persist its snapshot.

    The object-storage dependency is supplied by the application at startup in
    production and by a test override.  It is kept separate from database
    access so a failed engine call never creates a phantom result.
    """

    context = resolve_session_context(session, identity)
    case = _case_or_error(session, context, case_id)
    definition, binding = _definition_or_error(payload.catalog_key)
    calibration_run = definition.key.startswith("CALIBRATION_")
    artifacts = (
        []
        if calibration_run
        else _artifact_inputs(session, context, case, payload.artifact_ids)
    )
    _validate_artifact_profile(binding.input_profile, artifacts)
    if calibration_run and payload.artifact_ids:
        raise DomainError(
            "PYLINAC_INPUT_COUNT_INVALID",
            "Bài hiệu chuẩn chỉ nhận số đo, không cần tệp đầu vào.",
            422,
        )
    if definition.key in {
        "PICKET_FENCE",
        "STARSHOT",
        "WINSTON_LUTZ",
        "WINSTON_LUTZ_MULTI_TARGET",
        "CATPHAN_503",
        "CATPHAN_504",
        "CATPHAN_600",
        "CATPHAN_604",
        "CATPHAN_700",
        "ACR_CT_464",
        "ACR_MRI_LARGE",
        "ACR_MRI_MEDIUM",
        "CHEESE_TOMO",
        "CHEESE_CIRS_062M",
        "GE_HELIOS",
        "QUART_DVT",
        "QUART_HYPERSIGHT",
        "CONTRIB_QUASAR_LIGHT_RAD_SCALING",
        "CONTRIB_JAW_ORTHOGONALITY",
    } and len(artifacts) != 1:
        raise DomainError(
            "PYLINAC_INPUT_COUNT_INVALID", "Bài QA này yêu cầu đúng một tệp đầu vào.", 422
        )
    nuclear_keys = {
        "NUCLEAR_MCR",
        "NUCLEAR_PU",
        "NUCLEAR_COR",
        "NUCLEAR_TR",
        "NUCLEAR_SS",
        "NUCLEAR_FBR",
        "NUCLEAR_QR",
        "NUCLEAR_TU",
        "NUCLEAR_TC",
    }
    if definition.key in nuclear_keys:
        expected_counts = {"NUCLEAR_SS": {1, 2}}
        if len(artifacts) not in expected_counts.get(definition.key, {1}):
            message = (
                "Bài độ nhạy đơn giản nhận một ảnh phantom và nền tùy chọn."
                if definition.key == "NUCLEAR_SS"
                else "Bài kiểm tra hạt nhân này yêu cầu đúng một tệp DICOM."
            )
            raise DomainError("PYLINAC_INPUT_COUNT_INVALID", message, 422)
        if any(
            Path(artifact.original_filename).suffix.lower() != ".dcm"
            for artifact in artifacts
        ):
            raise DomainError(
                "PYLINAC_INPUT_FORMAT_INVALID",
                "Bài kiểm tra hạt nhân chỉ nhận tệp DICOM có đuôi DCM.",
                422,
            )
    if definition.key in {"VMAT_DRGS", "VMAT_DRMLC", "VMAT_DRCS"} and len(artifacts) != 2:
        raise DomainError(
            "PYLINAC_INPUT_COUNT_INVALID", "Bài VMAT yêu cầu đúng hai ảnh đầu vào.", 422
        )
    if definition.key == "LOG_DYNALOG" and len(artifacts) != 2:
        raise DomainError(
            "PYLINAC_INPUT_COUNT_INVALID", "Dynalog yêu cầu đúng hai tệp A và B.", 422
        )
    if definition.key.startswith("LOG_TRAJECTORY_") and len(artifacts) not in {1, 2}:
        raise DomainError(
            "PYLINAC_INPUT_COUNT_INVALID",
            "Trajectory Log cần một tệp BIN, có thể kèm tệp TXT.",
            422,
        )
    if definition.key == "LOG_DYNALOG" and any(
        Path(artifact.original_filename).suffix.lower() != ".dlg" for artifact in artifacts
    ):
        raise DomainError(
            "PYLINAC_INPUT_FORMAT_INVALID", "Dynalog chỉ nhận hai tệp có đuôi DLG.", 422
        )
    if definition.key.startswith("LOG_TRAJECTORY_") and not any(
        Path(artifact.original_filename).suffix.lower() in {".bin", ".tlog"}
        for artifact in artifacts
    ):
        raise DomainError(
            "PYLINAC_INPUT_FORMAT_INVALID", "Trajectory Log cần ít nhất một tệp BIN hoặc TLOG.", 422
        )
    if definition.key.startswith("PLANAR_") and len(artifacts) != 1:
        raise DomainError(
            "PYLINAC_INPUT_COUNT_INVALID", "Bài ảnh phẳng yêu cầu đúng một tệp đầu vào.", 422
        )
    if (
        definition.key in {"WINSTON_LUTZ", "WINSTON_LUTZ_MULTI_TARGET"}
        and Path(artifacts[0].original_filename).suffix.lower() != ".zip"
    ):
        raise DomainError(
            "PYLINAC_INPUT_FORMAT_INVALID",
            "Bài Winston–Lutz yêu cầu một tệp ZIP chứa bộ ảnh.",
            422,
        )
    if (
        definition.key in {
            "CATPHAN_503",
            "CATPHAN_504",
            "CATPHAN_600",
            "CATPHAN_604",
            "CATPHAN_700",
            "ACR_CT_464",
            "ACR_MRI_LARGE",
            "ACR_MRI_MEDIUM",
            "CHEESE_TOMO",
            "CHEESE_CIRS_062M",
            "GE_HELIOS",
            "QUART_DVT",
            "QUART_HYPERSIGHT",
        }
        and Path(artifacts[0].original_filename).suffix.lower() != ".zip"
    ):
        raise DomainError(
            "PYLINAC_INPUT_FORMAT_INVALID",
            "Bài CatPhan yêu cầu một tệp ZIP chứa chuỗi DICOM.",
            422,
        )
    if (
        definition.key in {"ACR_CT_464", "ACR_MRI_LARGE", "ACR_MRI_MEDIUM"}
        and Path(artifacts[0].original_filename).suffix.lower() != ".zip"
    ):
        raise DomainError(
            "PYLINAC_INPUT_FORMAT_INVALID",
            "Bài ACR yêu cầu một tệp ZIP chứa chuỗi DICOM.",
            422,
        )
    started_at = datetime.now(UTC)
    run = PylinacQARun(
        organization_id=context.organization_id,
        qa_case_id=case.id,
        machine_id=case.machine_id,
        catalog_key=definition.key,
        engine_class=definition.engine_class or binding.import_path.rsplit(".", 1)[-1],
        engine_version=PYLINAC_VERSION,
        package_fingerprint=package_fingerprint(),
        status="RUNNING",
        parameters_snapshot=dict(payload.parameters),
        input_snapshot=_input_snapshot(artifacts),
        result_snapshot={"schema_version": "p7.pylinac-result.v1", "metrics": []},
        warning_snapshot=[],
        error_snapshot=[],
        started_at=started_at,
        created_by_user_identity_id=_actor(session, context),
    )
    session.add(run)
    session.flush()
    for artifact in artifacts:
        session.add(
            InputManifest(
                organization_id=context.organization_id,
                analysis_run_id=run.id,
                artifact_id=artifact.id,
                logical_role=_manifest_role(artifact),
                checksum_at_use=artifact.sha256,
                selected_metadata=artifact.metadata_snapshot,
                geometry_summary={},
                unit_summary={},
                validation_summary={"state": artifact.data_status},
            )
        )
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor(session, context),
            event_type="PYLINAC_QA_RUN_STARTED",
            entity_type="PylinacQARun",
            entity_id=run.id,
            payload={"catalog_key": definition.key, "input_count": len(artifacts)},
        )
    )
    session.commit()
    session.refresh(run)

    overlay_key: str | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="rt-connect-pylinac-") as directory:
            if definition.key.startswith("LOG_"):
                source_path = Path(directory)
                for artifact in artifacts:
                    safe_filename = (
                        Path(artifact.original_filename).name.strip() or "input.log"
                    )
                    destination = source_path / safe_filename
                    if destination.exists():
                        destination = source_path / f"{artifact.id.hex}-{safe_filename}"
                    storage.download_to_path(artifact.object_key, destination)
            elif len(artifacts) == 1:
                safe_filename = Path(artifacts[0].original_filename).name.strip() or "input.dcm"
                source_path = Path(directory) / safe_filename
                storage.download_to_path(artifacts[0].object_key, source_path)
            else:
                source_path = Path(directory)
                for index, artifact in enumerate(artifacts):
                    safe_filename = (
                        Path(artifact.original_filename).name.strip() or f"input-{index}.dcm"
                    )
                    destination = source_path / f"{index:02d}-{safe_filename}"
                    storage.download_to_path(artifact.object_key, destination)
            execution = execute_pylinac(definition.key, source_path, payload.parameters)
            overlay_artifact_id: UUID | None = None
            if execution.overlay_bytes is not None:
                overlay_key = (
                    f"organizations/{context.organization_id}/qa-cases/{case.id}/"
                    f"pylinac-runs/{run.id}/{execution.overlay_filename or 'analysis.png'}"
                )
                storage.put_object(
                    overlay_key,
                    source=BytesIO(execution.overlay_bytes),
                    length=len(execution.overlay_bytes),
                    content_type=execution.overlay_media_type or "application/octet-stream",
                )
                overlay_artifact = Artifact(
                    organization_id=context.organization_id,
                    qa_case_id=case.id,
                    artifact_type="IMAGE",
                    modality="DERIVED",
                    original_filename=execution.overlay_filename or "analysis.png",
                    object_key=overlay_key,
                    byte_size=len(execution.overlay_bytes),
                    media_type=execution.overlay_media_type or "application/octet-stream",
                    sha256=hashlib.sha256(execution.overlay_bytes).hexdigest(),
                    source_system=f"pylinac {execution.engine_version}",
                    parent_artifact_id=artifacts[0].id,
                    metadata_snapshot={
                        "derived_from_run_id": str(run.id),
                        "catalog_key": definition.key,
                        "engine_class": execution.engine_class,
                    },
                    uploaded_by_user_identity_id=_actor(session, context),
                    data_status="DERIVED",
                )
                session.add(overlay_artifact)
                session.flush()
                overlay_artifact_id = overlay_artifact.id
            run.status = "COMPLETED"
            run.completed_at = datetime.now(UTC)
            run.result_snapshot = execution.result_snapshot
            run.warning_snapshot = execution.warnings
            run.error_snapshot = []
            run.overlay_artifact_id = overlay_artifact_id
            session.add(
                AuditEvent(
                    organization_id=context.organization_id,
                    actor_user_identity_id=_actor(session, context),
                    event_type="PYLINAC_QA_RUN_COMPLETED",
                    entity_type="PylinacQARun",
                    entity_id=run.id,
                    payload={"catalog_key": definition.key, "status": "COMPLETED"},
                )
            )
            session.commit()
            session.refresh(run)
    except ObjectStorageError:
        _fail_run(
            session,
            run,
            "PYLINAC_INPUT_NOT_AVAILABLE",
            "Không thể đọc tệp đầu vào từ kho lưu trữ. Hãy thử lại sau.",
        )
    except PylinacAdapterError as exc:
        _fail_run(session, run, exc.code, exc.message)
    except Exception:
        session.rollback()
        if overlay_key is not None:
            # The reconciliation job will surface an object that could not
            # be compensated after a failed database transaction.
            with suppress(ObjectStorageError):
                storage.delete_object(overlay_key)
        _fail_run(
            session,
            run,
            "PYLINAC_EXECUTION_FAILED",
            "Không thể hoàn tất phân tích Pylinac. Hãy kiểm tra tệp và tham số rồi thử lại.",
        )
    return _run_response(session, run)


@router.get("/qa-cases/{case_id}/pylinac-runs", response_model=PylinacRunCollectionResponse)
def list_pylinac_runs(
    case_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PylinacRunCollectionResponse:
    context = resolve_session_context(session, identity)
    _case_or_error(session, context, case_id)
    runs = list(
        session.scalars(
            select(PylinacQARun)
            .where(
                PylinacQARun.organization_id == context.organization_id,
                PylinacQARun.qa_case_id == case_id,
            )
            .order_by(PylinacQARun.created_at.desc())
        )
    )
    return PylinacRunCollectionResponse(
        items=[_run_response(session, run) for run in runs], total=len(runs)
    )


@router.get("/pylinac-qa-runs/{run_id}", response_model=PylinacQARunResponse)
def get_pylinac_run(
    run_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PylinacQARunResponse:
    context = resolve_session_context(session, identity)
    run = session.scalar(
        select(PylinacQARun).where(
            PylinacQARun.id == run_id,
            PylinacQARun.organization_id == context.organization_id,
        )
    )
    if run is None:
        raise DomainError("PYLINAC_RUN_NOT_FOUND", "Không tìm thấy lượt phân tích.", 404)
    return _run_response(session, run)


@router.post("/pylinac-qa-runs/{run_id}/assessment", response_model=PylinacQARunResponse)
def assess_pylinac_run(
    run_id: UUID,
    payload: PylinacAssessmentRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PylinacQARunResponse:
    context = resolve_session_context(session, identity)
    run = session.scalar(
        select(PylinacQARun).where(
            PylinacQARun.id == run_id,
            PylinacQARun.organization_id == context.organization_id,
        )
    )
    if run is None:
        raise DomainError("PYLINAC_RUN_NOT_FOUND", "Không tìm thấy lượt phân tích.", 404)
    if run.status != "COMPLETED":
        raise DomainError(
            "PYLINAC_RUN_NOT_COMPLETED",
            "Chỉ có thể đánh giá một lượt phân tích đã hoàn tất.",
            409,
        )
    run.assessment_status = payload.assessment_status
    result = dict(run.result_snapshot)
    result["assessment"] = {
        "status": payload.assessment_status,
        "note": payload.note,
        "assessed_at": datetime.now(UTC).isoformat(),
    }
    run.result_snapshot = result
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor(session, context),
            event_type="PYLINAC_QA_RUN_ASSESSED",
            entity_type="PylinacQARun",
            entity_id=run.id,
            payload={"assessment_status": payload.assessment_status},
        )
    )
    session.commit()
    session.refresh(run)
    return _run_response(session, run)
