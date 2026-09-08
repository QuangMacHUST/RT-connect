"""P9 report templates, immutable revisions, preview and export endpoints."""

# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

from __future__ import annotations

import hashlib
import io
import math
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    ExportJob,
    GammaAnalysisRun,
    MachineQARun,
    QACase,
    ReportBlockConfig,
    ReportRevision,
    ReportTemplateVersion,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.object_storage import (
    ObjectStorage,
    ObjectStorageError,
    get_storage,
)
from rt_connect_api.services.report_renderer import (
    RENDERER_VERSION,
    SUPPORTED_EXPORT_FORMATS,
    ExportFormat,
    ReportRenderError,
    canonical_json,
    render_report,
)
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(tags=["reports"])

ReportSourceType = Literal["CUSTOM", "QA_CASE", "MACHINE_QA", "GAMMA", "BIOLOGICAL"]
ReportBlockType = Literal[
    "TEXT",
    "METADATA",
    "METRICS",
    "GAMMA_MAP",
    "DOSE_PROFILE",
    "DVH",
    "TREND_CHART",
    "COMPARISON",
    "BIOLOGICAL",
    "COMMENTS",
    "PROVENANCE",
    "TABLE",
    "IMAGE",
    "WARNING",
]

_BLOCK_TYPES: frozenset[str] = frozenset(
    {
        "TEXT",
        "METADATA",
        "METRICS",
        "GAMMA_MAP",
        "DOSE_PROFILE",
        "DVH",
        "TREND_CHART",
        "COMPARISON",
        "BIOLOGICAL",
        "COMMENTS",
        "PROVENANCE",
        "TABLE",
        "IMAGE",
        "WARNING",
    }
)
_SOURCE_IDS_REQUIRED: frozenset[str] = frozenset({"QA_CASE", "MACHINE_QA", "GAMMA"})


class ReportBlockInput(BaseModel):
    stable_block_id: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$",
    )
    block_type: ReportBlockType
    label: str = Field(min_length=1, max_length=240)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_visible: bool = True
    config: dict[str, object] = Field(default_factory=dict)
    source_binding: dict[str, object] = Field(default_factory=dict)

    @field_validator("label")
    @classmethod
    def _trim_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("label cannot be blank")
        return value


class ReportTemplateCreateRequest(BaseModel):
    template_key: str = Field(
        min_length=1,
        max_length=120,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$",
    )
    name: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] = "ACTIVE"
    blocks: list[ReportBlockInput] = Field(default_factory=list, max_length=200)
    render_options: dict[str, object] = Field(default_factory=dict)


class ReportTemplateVersionCreateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] | None = None
    blocks: list[ReportBlockInput] | None = Field(default=None, max_length=200)
    render_options: dict[str, object] | None = None


class ReportCreateRequest(BaseModel):
    source_type: ReportSourceType
    source_id: UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    template_version_id: UUID | None = None
    blocks: list[ReportBlockInput] | None = Field(default=None, max_length=200)
    render_options: dict[str, object] = Field(default_factory=dict)


class ReportRevisionCreateRequest(BaseModel):
    expected_revision: int | None = Field(default=None, ge=1)
    source_type: ReportSourceType | None = None
    source_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    template_version_id: UUID | None = None
    blocks: list[ReportBlockInput] | None = Field(default=None, max_length=200)
    render_options: dict[str, object] | None = None


class ReportExportRequest(BaseModel):
    export_format: Literal["JSON", "CSV", "PDF", "PNG"]
    idempotency_key: str = Field(min_length=8, max_length=200)
    render_options: dict[str, object] = Field(default_factory=dict)


class ReportBlockResponse(BaseModel):
    id: UUID
    stable_block_id: str
    block_type: str
    label: str
    sort_order: int
    is_visible: bool
    config: dict[str, object]
    source_binding: dict[str, object]


class ReportTemplateVersionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    template_key: str
    name: str
    version_number: int
    status: str
    description: str | None
    blocks_snapshot: list[dict[str, object]]
    render_options: dict[str, object]
    created_by_user_identity_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ReportRevisionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    report_key: UUID
    revision_number: int
    source_type: str
    source_id: UUID | None
    title: str
    template_version_id: UUID | None
    source_snapshot: dict[str, object]
    render_options: dict[str, object]
    content_sha256: str
    status: str
    supersedes_revision_id: UUID | None
    created_by_user_identity_id: UUID | None
    created_at: datetime
    updated_at: datetime
    blocks: list[ReportBlockResponse]


class ReportResponse(BaseModel):
    report_key: UUID
    organization_id: UUID
    title: str
    source_type: str
    source_id: UUID | None
    latest_revision_id: UUID
    latest_revision_number: int
    status: str
    content_sha256: str
    created_at: datetime
    updated_at: datetime


class ReportCollectionResponse(BaseModel):
    items: list[ReportResponse]
    total: int
    offset: int
    limit: int


class TemplateCollectionResponse(BaseModel):
    items: list[ReportTemplateVersionResponse]
    total: int


class ExportJobResponse(BaseModel):
    id: UUID
    organization_id: UUID
    report_revision_id: UUID
    idempotency_key: str
    export_format: str
    render_options: dict[str, object]
    renderer_version: str
    status: str
    object_key: str | None
    sha256: str | None
    byte_size: int | None
    media_type: str | None
    error_snapshot: list[dict[str, object]]
    warning_snapshot: list[dict[str, object]]
    download_url: str | None = None
    download_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ExportDownloadResponse(BaseModel):
    export_job_id: UUID
    report_revision_id: UUID
    url: str
    expires_at: datetime
    sha256: str
    media_type: str


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


def _actor_id(session: Session, context: SessionContext) -> UUID | None:
    return session.scalar(
        select(UserIdentity.id).where(UserIdentity.supabase_user_id == context.subject)
    )


def _storage(request: Request) -> ObjectStorage:
    try:
        return get_storage(request.app.state.settings)
    except ObjectStorageError as exc:
        raise DomainError(
            "OBJECT_STORAGE_NOT_CONFIGURED",
            "Durable report storage is not configured for this environment.",
            503,
        ) from exc


def _commit_or_raise(session: Session, code: str, message: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(code, message, 409) from exc


def _audit(
    session: Session,
    context: SessionContext,
    event_type: str,
    entity_type: str,
    entity_id: UUID | None,
    payload: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor_id(session, context),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
    )


def _validate_json_tree(value: object, field: str, depth: int = 0) -> None:
    if depth > 8:
        raise DomainError(
            "REPORT_CONTENT_INVALID",
            "Report customization is nested too deeply.",
            422,
            [{"field": field, "message": "Maximum nesting depth is 8."}],
        )
    if value is None or isinstance(value, bool | int | str):
        if isinstance(value, str):
            if len(value) > 64_000:
                raise DomainError(
                    "REPORT_CONTENT_INVALID",
                    "A report text value is too large.",
                    422,
                    [
                        {
                            "field": field,
                            "message": "String values are limited to 64,000 characters.",
                        }
                    ],
                )
            lowered = value.lower()
            if "<script" in lowered or "javascript:" in lowered:
                raise DomainError(
                    "REPORT_CONTENT_INVALID",
                    "Executable script content is not supported in report blocks.",
                    422,
                    [{"field": field, "message": "Remove script or javascript content."}],
                )
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DomainError(
                "REPORT_CONTENT_INVALID",
                "Report customization cannot contain NaN or infinite values.",
                422,
                [{"field": field, "message": "Use a finite JSON number."}],
            )
        return
    if isinstance(value, Mapping):
        if len(value) > 200:
            raise DomainError(
                "REPORT_CONTENT_INVALID",
                "A report object has too many properties.",
                422,
                [{"field": field, "message": "At most 200 properties are supported."}],
            )
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 240:
                raise DomainError(
                    "REPORT_CONTENT_INVALID",
                    "Report object keys must be short strings.",
                    422,
                    [{"field": field, "message": "Object keys are limited to 240 characters."}],
                )
            _validate_json_tree(child, f"{field}.{key}", depth + 1)
        return
    if isinstance(value, list):
        if len(value) > 2_000:
            raise DomainError(
                "REPORT_CONTENT_INVALID",
                "A report list contains too many items.",
                422,
                [{"field": field, "message": "At most 2,000 items are supported."}],
            )
        for index, child in enumerate(value):
            _validate_json_tree(child, f"{field}[{index}]", depth + 1)
        return
    raise DomainError(
        "REPORT_CONTENT_INVALID",
        "Report customization contains a value that is not JSON serializable.",
        422,
        [{"field": field, "message": "Use only JSON values."}],
    )


def _normalise_blocks(blocks: list[ReportBlockInput]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    seen_orders: set[int] = set()
    for index, block in enumerate(blocks):
        if block.block_type not in _BLOCK_TYPES:
            raise DomainError(
                "REPORT_CONTENT_INVALID",
                "Report block type is not supported.",
                422,
                [{"field": f"blocks[{index}].block_type", "message": "Unknown block type."}],
            )
        if block.stable_block_id in seen_ids:
            raise DomainError(
                "REPORT_CONTENT_INVALID",
                "Report block IDs must be unique within a revision.",
                422,
                [{"field": f"blocks[{index}].stable_block_id", "message": "Duplicate block ID."}],
            )
        seen_ids.add(block.stable_block_id)
        sort_order = block.sort_order if block.sort_order is not None else index
        if sort_order in seen_orders:
            raise DomainError(
                "REPORT_CONTENT_INVALID",
                "Report block order values must be unique.",
                422,
                [{"field": f"blocks[{index}].sort_order", "message": "Duplicate sort order."}],
            )
        seen_orders.add(sort_order)
        block_data: dict[str, object] = {
            "stable_block_id": block.stable_block_id,
            "block_type": block.block_type,
            "label": block.label,
            "sort_order": sort_order,
            "is_visible": block.is_visible,
            "config": block.config,
            "source_binding": block.source_binding,
        }
        _validate_json_tree(block_data, f"blocks[{index}]")
        result.append(block_data)
    result.sort(key=_block_sort_order)
    if len(canonical_json(result)) > 2_000_000:
        raise DomainError(
            "REPORT_CONTENT_INVALID",
            "Report block configuration exceeds the supported size.",
            422,
            [{"field": "blocks", "message": "The block snapshot is limited to 2 MB."}],
        )
    return result


def _block_sort_order(block: Mapping[str, object]) -> int:
    value = block.get("sort_order")
    if not isinstance(value, int) or isinstance(value, bool):
        raise DomainError(
            "REPORT_CONTENT_INVALID",
            "Every report block must have a numeric sort order.",
            422,
            [{"field": "blocks.sort_order", "message": "Use a non-negative integer."}],
        )
    return value


def _validate_options(
    options: Mapping[str, object], field: str = "render_options"
) -> dict[str, object]:
    _validate_json_tree(options, field)
    normalised = dict(options)
    if len(canonical_json(normalised)) > 256_000:
        raise DomainError(
            "REPORT_CONTENT_INVALID",
            "Report render options exceed the supported size.",
            422,
            [{"field": field, "message": "Render options are limited to 256 KB."}],
        )
    return normalised


def _template_blocks(template: ReportTemplateVersion | None) -> list[dict[str, object]]:
    if template is None:
        return [
            {
                "stable_block_id": "metadata",
                "block_type": "METADATA",
                "label": "Report metadata",
                "sort_order": 0,
                "is_visible": True,
                "config": {},
                "source_binding": {},
            },
            {
                "stable_block_id": "provenance",
                "block_type": "PROVENANCE",
                "label": "Provenance",
                "sort_order": 1,
                "is_visible": True,
                "config": {},
                "source_binding": {},
            },
        ]
    raw = template.blocks_snapshot
    result: list[dict[str, object]] = []
    for item in raw:
        if isinstance(item, Mapping):
            result.append(dict(item))
    return result


def _template_or_error(
    session: Session, context: SessionContext, template_id: UUID | None
) -> ReportTemplateVersion | None:
    if template_id is None:
        return None
    template = session.scalar(
        select(ReportTemplateVersion).where(
            ReportTemplateVersion.id == template_id,
            ReportTemplateVersion.organization_id == context.organization_id,
        )
    )
    if template is None:
        raise DomainError(
            "REPORT_TEMPLATE_NOT_FOUND", "Report template version was not found.", 404
        )
    return template


def _template_response(template: ReportTemplateVersion) -> ReportTemplateVersionResponse:
    return ReportTemplateVersionResponse(
        id=template.id,
        organization_id=template.organization_id,
        template_key=template.template_key,
        name=template.name,
        version_number=template.version_number,
        status=template.status,
        description=template.description,
        blocks_snapshot=template.blocks_snapshot,
        render_options=template.render_options,
        created_by_user_identity_id=template.created_by_user_identity_id,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _block_response(block: ReportBlockConfig) -> ReportBlockResponse:
    return ReportBlockResponse(
        id=block.id,
        stable_block_id=block.stable_block_id,
        block_type=block.block_type,
        label=block.label,
        sort_order=block.sort_order,
        is_visible=block.is_visible,
        config=block.config,
        source_binding=block.source_binding,
    )


def _blocks_for_revision(
    session: Session, revision_id: UUID, organization_id: UUID
) -> list[ReportBlockConfig]:
    return list(
        session.scalars(
            select(ReportBlockConfig)
            .where(
                ReportBlockConfig.report_revision_id == revision_id,
                ReportBlockConfig.organization_id == organization_id,
            )
            .order_by(ReportBlockConfig.sort_order, ReportBlockConfig.stable_block_id)
        )
    )


def _revision_response(
    session: Session, revision: ReportRevision
) -> ReportRevisionResponse:
    return ReportRevisionResponse(
        id=revision.id,
        organization_id=revision.organization_id,
        report_key=revision.report_key,
        revision_number=revision.revision_number,
        source_type=revision.source_type,
        source_id=revision.source_id,
        title=revision.title,
        template_version_id=revision.template_version_id,
        source_snapshot=revision.source_snapshot,
        render_options=revision.render_options,
        content_sha256=revision.content_sha256,
        status=revision.status,
        supersedes_revision_id=revision.supersedes_revision_id,
        created_by_user_identity_id=revision.created_by_user_identity_id,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
        blocks=[
            _block_response(block)
            for block in _blocks_for_revision(session, revision.id, revision.organization_id)
        ],
    )


def _report_response(revision: ReportRevision) -> ReportResponse:
    return ReportResponse(
        report_key=revision.report_key,
        organization_id=revision.organization_id,
        title=revision.title,
        source_type=revision.source_type,
        source_id=revision.source_id,
        latest_revision_id=revision.id,
        latest_revision_number=revision.revision_number,
        status=revision.status,
        content_sha256=revision.content_sha256,
        created_at=revision.created_at,
        updated_at=revision.updated_at,
    )


def _jsonable(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(child) for child in value]
    return value


def _case_payload(case: QACase) -> dict[str, object]:
    return {
        "id": str(case.id),
        "organization_id": str(case.organization_id),
        "site_id": str(case.site_id),
        "machine_id": str(case.machine_id),
        "primary_folder_id": str(case.primary_folder_id),
        "qa_type": case.qa_type,
        "qa_cycle": case.qa_cycle,
        "performed_at": case.performed_at.isoformat(),
        "scheduled_at": case.scheduled_at.isoformat() if case.scheduled_at else None,
        "title": case.title,
        "description": case.description,
        "protocol_version_id": str(case.protocol_version_id) if case.protocol_version_id else None,
        "status_note": case.status_note,
        "case_status": case.case_status,
        "is_archived": case.is_archived,
    }


def _source_snapshot(
    session: Session,
    context: SessionContext,
    source_type: str,
    source_id: UUID | None,
) -> dict[str, object]:
    if source_type in _SOURCE_IDS_REQUIRED and source_id is None:
        raise DomainError(
            "REPORT_SOURCE_REQUIRED",
            f"A source_id is required for {source_type} reports.",
            422,
            [{"field": "source_id", "message": "Choose a source record in this organization."}],
        )

    payload: dict[str, object]
    if source_type == "QA_CASE":
        case = session.scalar(
            select(QACase).where(
                QACase.id == source_id,
                QACase.organization_id == context.organization_id,
            )
        )
        if case is None:
            raise DomainError("REPORT_SOURCE_UNAVAILABLE", "The QA case source was not found.", 404)
        payload = _case_payload(case)
    elif source_type == "MACHINE_QA":
        machine_run = session.scalar(
            select(MachineQARun).where(
                MachineQARun.id == source_id,
                MachineQARun.organization_id == context.organization_id,
            )
        )
        if machine_run is None:
            raise DomainError(
                "REPORT_SOURCE_UNAVAILABLE", "The Machine QA source was not found.", 404
            )
        payload = {
            "id": str(machine_run.id),
            "organization_id": str(machine_run.organization_id),
            "qa_case_id": str(machine_run.qa_case_id),
            "machine_id": str(machine_run.machine_id),
            "protocol_version_id": str(machine_run.protocol_version_id),
            "status": machine_run.status,
            "overall_status": machine_run.overall_status,
            "measurement_revision": machine_run.measurement_revision,
            "measurements": machine_run.measurements,
            "result_snapshot": machine_run.result_snapshot,
            "error_snapshot": machine_run.error_snapshot,
            "supersedes_run_id": (
                str(machine_run.supersedes_run_id) if machine_run.supersedes_run_id else None
            ),
            "started_at": machine_run.started_at.isoformat() if machine_run.started_at else None,
            "completed_at": (
                machine_run.completed_at.isoformat() if machine_run.completed_at else None
            ),
            "created_at": machine_run.created_at.isoformat(),
            "updated_at": machine_run.updated_at.isoformat(),
        }
    elif source_type == "GAMMA":
        gamma_run = session.scalar(
            select(GammaAnalysisRun).where(
                GammaAnalysisRun.id == source_id,
                GammaAnalysisRun.organization_id == context.organization_id,
            )
        )
        if gamma_run is None:
            raise DomainError("REPORT_SOURCE_UNAVAILABLE", "The Gamma source was not found.", 404)
        payload = {
            "id": str(gamma_run.id),
            "organization_id": str(gamma_run.organization_id),
            "qa_case_id": str(gamma_run.qa_case_id),
            "status": gamma_run.status,
            "workflow_profile": gamma_run.config_snapshot.get("workflow_profile"),
            "attempt_count": gamma_run.attempt_count,
            "engine_version": gamma_run.engine_version,
            "config_snapshot": gamma_run.config_snapshot,
            "input_manifest_snapshot": gamma_run.input_manifest_snapshot,
            "result_snapshot": gamma_run.result_snapshot,
            "error_snapshot": gamma_run.error_snapshot,
            "warning_snapshot": gamma_run.warning_snapshot,
            "queued_at": gamma_run.queued_at.isoformat(),
            "started_at": gamma_run.started_at.isoformat() if gamma_run.started_at else None,
            "completed_at": gamma_run.completed_at.isoformat() if gamma_run.completed_at else None,
            "created_at": gamma_run.created_at.isoformat(),
            "updated_at": gamma_run.updated_at.isoformat(),
        }
    elif source_type == "BIOLOGICAL":
        payload = {
            "namespace": "BIOLOGICAL_TOOLKIT",
            "source_id": str(source_id) if source_id else None,
            "note": "Biological calculation is an independent scenario source.",
        }
    else:
        payload = {
            "namespace": "CUSTOM_REPORT",
            "source_id": str(source_id) if source_id else None,
        }
    return {
        "source_type": source_type,
        "source_id": str(source_id) if source_id else None,
        "captured_at": datetime.now(UTC).isoformat(),
        "payload": _jsonable(payload),
    }


def _template_snapshot(template: ReportTemplateVersion | None) -> dict[str, object] | None:
    if template is None:
        return None
    return {
        "id": str(template.id),
        "template_key": template.template_key,
        "name": template.name,
        "version_number": template.version_number,
        "status": template.status,
        "description": template.description,
        "blocks_snapshot": template.blocks_snapshot,
        "render_options": template.render_options,
    }


def _snapshot_for_revision(
    session: Session, revision: ReportRevision
) -> dict[str, object]:
    blocks = _blocks_for_revision(session, revision.id, revision.organization_id)
    template: ReportTemplateVersion | None = None
    if revision.template_version_id is not None:
        template = session.scalar(
            select(ReportTemplateVersion).where(
                ReportTemplateVersion.id == revision.template_version_id,
                ReportTemplateVersion.organization_id == revision.organization_id,
            )
        )
    snapshot: dict[str, object] = {
        "report_key": str(revision.report_key),
        "revision_number": revision.revision_number,
        "title": revision.title,
        "source_type": revision.source_type,
        "source_id": str(revision.source_id) if revision.source_id else None,
        "source_snapshot": revision.source_snapshot,
        "template_snapshot": _template_snapshot(template),
        "render_options": revision.render_options,
        "content_sha256": revision.content_sha256,
        "renderer_version": RENDERER_VERSION,
        "status": revision.status,
        "blocks": [
            {
                "stable_block_id": block.stable_block_id,
                "block_type": block.block_type,
                "label": block.label,
                "sort_order": block.sort_order,
                "is_visible": block.is_visible,
                "config": block.config,
                "source_binding": block.source_binding,
            }
            for block in blocks
        ],
    }
    return snapshot


def _content_hash(material: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(material)).hexdigest()


def _create_revision(
    session: Session,
    context: SessionContext,
    *,
    report_key: UUID,
    revision_number: int,
    source_type: str,
    source_id: UUID | None,
    title: str,
    template: ReportTemplateVersion | None,
    blocks: list[dict[str, object]],
    render_options: dict[str, object],
    supersedes_revision_id: UUID | None,
) -> ReportRevision:
    source_snapshot = _source_snapshot(session, context, source_type, source_id)
    material: dict[str, object] = {
        "report_key": str(report_key),
        "revision_number": revision_number,
        "title": title,
        "source_type": source_type,
        "source_id": str(source_id) if source_id else None,
        "source_snapshot": source_snapshot,
        "template_snapshot": _template_snapshot(template),
        "render_options": render_options,
        "blocks": blocks,
        "renderer_version": RENDERER_VERSION,
    }
    revision = ReportRevision(
        report_key=report_key,
        organization_id=context.organization_id,
        revision_number=revision_number,
        source_type=source_type,
        source_id=source_id,
        title=title,
        template_version_id=template.id if template else None,
        source_snapshot=source_snapshot,
        render_options=render_options,
        content_sha256=_content_hash(material),
        status="SAVED",
        supersedes_revision_id=supersedes_revision_id,
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(revision)
    session.flush()
    for block in blocks:
        session.add(
            ReportBlockConfig(
                organization_id=context.organization_id,
                report_revision_id=revision.id,
                stable_block_id=str(block["stable_block_id"]),
                block_type=str(block["block_type"]),
                label=str(block["label"]),
                sort_order=_block_sort_order(block),
                is_visible=bool(block["is_visible"]),
                config=block["config"] if isinstance(block["config"], dict) else {},
                source_binding=(
                    block["source_binding"]
                    if isinstance(block["source_binding"], dict)
                    else {}
                ),
            )
        )
    return revision


def _export_response(
    job: ExportJob,
    storage: ObjectStorage | None = None,
    ttl_seconds: int = 900,
) -> ExportJobResponse:
    url: str | None = None
    expires_at: datetime | None = None
    if job.status == "COMPLETED" and job.object_key and storage is not None:
        try:
            url = storage.presigned_get(job.object_key, ttl_seconds)
            expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        except ObjectStorageError:
            url = None
            expires_at = None
    return ExportJobResponse(
        id=job.id,
        organization_id=job.organization_id,
        report_revision_id=job.report_revision_id,
        idempotency_key=job.idempotency_key,
        export_format=job.export_format,
        render_options=job.render_options,
        renderer_version=job.renderer_version,
        status=job.status,
        object_key=job.object_key,
        sha256=job.sha256,
        byte_size=job.byte_size,
        media_type=job.media_type,
        error_snapshot=job.error_snapshot,
        warning_snapshot=job.warning_snapshot,
        download_url=url,
        download_expires_at=expires_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _export_or_error(
    session: Session, context: SessionContext, job_id: UUID
) -> ExportJob:
    job = session.scalar(
        select(ExportJob).where(
            ExportJob.id == job_id,
            ExportJob.organization_id == context.organization_id,
        )
    )
    if job is None:
        raise DomainError("REPORT_EXPORT_NOT_FOUND", "Report export was not found.", 404)
    return job


def _required_text(value: str, field: str) -> str:
    result = value.strip()
    if not result:
        raise DomainError(
            "REPORT_CONTENT_INVALID",
            "Report text fields cannot be blank.",
            422,
            [{"field": field, "message": "Provide a non-blank value."}],
        )
    return result


def _blocks_from_snapshot(raw: object, field: str) -> list[dict[str, object]]:
    if not isinstance(raw, list):
        raise DomainError(
            "REPORT_CONTENT_INVALID",
            "Report template blocks must be a JSON list.",
            422,
            [{"field": field, "message": "Expected a list of block definitions."}],
        )
    parsed: list[ReportBlockInput] = []
    for index, item in enumerate(raw):
        try:
            parsed.append(ReportBlockInput.model_validate(item))
        except Exception as exc:
            raise DomainError(
                "REPORT_CONTENT_INVALID",
                "Report template contains an invalid block definition.",
                422,
                [{"field": f"{field}[{index}]", "message": "Block schema is invalid."}],
            ) from exc
    return _normalise_blocks(parsed)


def _block_snapshot_from_rows(blocks: list[ReportBlockConfig]) -> list[dict[str, object]]:
    return [
        {
            "stable_block_id": block.stable_block_id,
            "block_type": block.block_type,
            "label": block.label,
            "sort_order": block.sort_order,
            "is_visible": block.is_visible,
            "config": block.config,
            "source_binding": block.source_binding,
        }
        for block in blocks
    ]


def _latest_report_revisions(
    session: Session,
    organization_id: UUID,
    query_text: str | None = None,
    source_type: str | None = None,
) -> list[ReportRevision]:
    revisions = list(
        session.scalars(
            select(ReportRevision)
            .where(ReportRevision.organization_id == organization_id)
            .order_by(ReportRevision.created_at.desc(), ReportRevision.revision_number.desc())
        )
    )
    latest: dict[UUID, ReportRevision] = {}
    for revision in revisions:
        if revision.report_key in latest:
            continue
        if query_text and query_text.lower() not in revision.title.lower():
            continue
        if source_type and revision.source_type != source_type:
            continue
        latest[revision.report_key] = revision
    return list(latest.values())


@router.get(
    "/organizations/{organization_id}/report-templates",
    response_model=TemplateCollectionResponse,
)
def list_report_templates(
    organization_id: UUID,
    include_archived: bool = Query(default=True),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> TemplateCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    query = select(ReportTemplateVersion).where(
        ReportTemplateVersion.organization_id == organization_id
    )
    if not include_archived:
        query = query.where(ReportTemplateVersion.status != "ARCHIVED")
    templates = list(
        session.scalars(
            query.order_by(
                ReportTemplateVersion.template_key,
                ReportTemplateVersion.version_number.desc(),
            )
        )
    )
    return TemplateCollectionResponse(
        items=[_template_response(template) for template in templates], total=len(templates)
    )


@router.post(
    "/organizations/{organization_id}/report-templates",
    response_model=ReportTemplateVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report_template(
    organization_id: UUID,
    payload: ReportTemplateCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ReportTemplateVersionResponse:
    context = _context_for_organization(organization_id, identity, session)
    template_key = _required_text(payload.template_key, "template_key")
    name = _required_text(payload.name, "name")
    blocks = _normalise_blocks(payload.blocks)
    render_options = _validate_options(payload.render_options)
    existing = session.scalar(
        select(ReportTemplateVersion).where(
            ReportTemplateVersion.organization_id == organization_id,
            ReportTemplateVersion.template_key == template_key,
            ReportTemplateVersion.version_number == 1,
        )
    )
    if existing is not None:
        raise DomainError(
            "REPORT_TEMPLATE_CONFLICT",
            "A report template with this key already exists.",
            409,
        )
    template = ReportTemplateVersion(
        organization_id=organization_id,
        template_key=template_key,
        name=name,
        version_number=1,
        status=payload.status,
        description=payload.description,
        blocks_snapshot=blocks,
        render_options=render_options,
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(template)
    session.flush()
    _audit(
        session,
        context,
        "REPORT_TEMPLATE_CREATED",
        "ReportTemplateVersion",
        template.id,
        {"template_key": template.template_key, "version_number": 1},
    )
    _commit_or_raise(
        session,
        "REPORT_TEMPLATE_CONFLICT",
        "A report template with this key already exists.",
    )
    return _template_response(template)


@router.post(
    "/report-templates/{template_id}/versions",
    response_model=ReportTemplateVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report_template_version(
    template_id: UUID,
    payload: ReportTemplateVersionCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ReportTemplateVersionResponse:
    context = resolve_session_context(session, identity)
    template = session.scalar(
        select(ReportTemplateVersion).where(
            ReportTemplateVersion.id == template_id,
            ReportTemplateVersion.organization_id == context.organization_id,
        )
    )
    if template is None:
        raise DomainError(
            "REPORT_TEMPLATE_NOT_FOUND", "Report template version was not found.", 404
        )
    current_version = session.scalar(
        select(func.max(ReportTemplateVersion.version_number)).where(
            ReportTemplateVersion.organization_id == context.organization_id,
            ReportTemplateVersion.template_key == template.template_key,
        )
    )
    version_number = int(current_version or 0) + 1
    blocks = (
        _normalise_blocks(payload.blocks)
        if payload.blocks is not None
        else _blocks_from_snapshot(template.blocks_snapshot, "blocks_snapshot")
    )
    render_options = (
        _validate_options(payload.render_options)
        if payload.render_options is not None
        else _validate_options(template.render_options)
    )
    name = _required_text(payload.name or template.name, "name")
    new_template = ReportTemplateVersion(
        organization_id=context.organization_id,
        template_key=template.template_key,
        name=name,
        version_number=version_number,
        status=payload.status or template.status,
        description=(
            payload.description if payload.description is not None else template.description
        ),
        blocks_snapshot=blocks,
        render_options=render_options,
        created_by_user_identity_id=_actor_id(session, context),
    )
    session.add(new_template)
    session.flush()
    _audit(
        session,
        context,
        "REPORT_TEMPLATE_VERSION_CREATED",
        "ReportTemplateVersion",
        new_template.id,
        {"template_key": new_template.template_key, "version_number": version_number},
    )
    _commit_or_raise(
        session,
        "REPORT_TEMPLATE_CONFLICT",
        "The next report template version conflicted with another update.",
    )
    return _template_response(new_template)


@router.get(
    "/organizations/{organization_id}/reports",
    response_model=ReportCollectionResponse,
)
def list_reports(
    organization_id: UUID,
    q: str | None = Query(default=None, max_length=240),
    source_type: ReportSourceType | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ReportCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    latest = _latest_report_revisions(session, organization_id, q, source_type)
    return ReportCollectionResponse(
        items=[_report_response(item) for item in latest[offset : offset + limit]],
        total=len(latest),
        offset=offset,
        limit=limit,
    )


@router.post(
    "/organizations/{organization_id}/reports",
    response_model=ReportRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report(
    organization_id: UUID,
    payload: ReportCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ReportRevisionResponse:
    context = _context_for_organization(organization_id, identity, session)
    title = _required_text(payload.title, "title")
    template = _template_or_error(session, context, payload.template_version_id)
    blocks = (
        _normalise_blocks(payload.blocks)
        if payload.blocks is not None
        else _template_blocks(template)
    )
    render_options = _validate_options(
        {**(template.render_options if template else {}), **payload.render_options}
    )
    revision = _create_revision(
        session,
        context,
        report_key=uuid4(),
        revision_number=1,
        source_type=payload.source_type,
        source_id=payload.source_id,
        title=title,
        template=template,
        blocks=blocks,
        render_options=render_options,
        supersedes_revision_id=None,
    )
    _audit(
        session,
        context,
        "REPORT_REVISION_CREATED",
        "ReportRevision",
        revision.id,
        {
            "report_key": str(revision.report_key),
            "revision_number": revision.revision_number,
            "source_type": revision.source_type,
        },
    )
    _commit_or_raise(session, "REPORT_REVISION_CONFLICT", "The report could not be saved.")
    return _revision_response(session, revision)


def _report_latest_or_error(
    session: Session, context: SessionContext, report_key: UUID
) -> ReportRevision:
    revision = session.scalar(
        select(ReportRevision)
        .where(
            ReportRevision.report_key == report_key,
            ReportRevision.organization_id == context.organization_id,
        )
        .order_by(ReportRevision.revision_number.desc())
    )
    if revision is None:
        raise DomainError("REPORT_NOT_FOUND", "Report was not found in this organization.", 404)
    return revision


def _revision_or_error(
    session: Session,
    context: SessionContext,
    report_key: UUID,
    revision_id: UUID,
) -> ReportRevision:
    revision = session.scalar(
        select(ReportRevision).where(
            ReportRevision.id == revision_id,
            ReportRevision.report_key == report_key,
            ReportRevision.organization_id == context.organization_id,
        )
    )
    if revision is None:
        raise DomainError("REPORT_REVISION_NOT_FOUND", "Report revision was not found.", 404)
    return revision


@router.get("/reports/{report_key}", response_model=ReportResponse)
def get_report(
    report_key: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ReportResponse:
    context = resolve_session_context(session, identity)
    return _report_response(_report_latest_or_error(session, context, report_key))


@router.get("/reports/{report_key}/revisions", response_model=list[ReportRevisionResponse])
def list_report_revisions(
    report_key: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> list[ReportRevisionResponse]:
    context = resolve_session_context(session, identity)
    _report_latest_or_error(session, context, report_key)
    revisions = list(
        session.scalars(
            select(ReportRevision)
            .where(
                ReportRevision.report_key == report_key,
                ReportRevision.organization_id == context.organization_id,
            )
            .order_by(ReportRevision.revision_number.desc())
        )
    )
    return [_revision_response(session, revision) for revision in revisions]


@router.get(
    "/reports/{report_key}/revisions/{revision_id}",
    response_model=ReportRevisionResponse,
)
def get_report_revision(
    report_key: UUID,
    revision_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ReportRevisionResponse:
    context = resolve_session_context(session, identity)
    revision = _revision_or_error(session, context, report_key, revision_id)
    return _revision_response(session, revision)


@router.post(
    "/reports/{report_key}/revisions",
    response_model=ReportRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_report_revision(
    report_key: UUID,
    payload: ReportRevisionCreateRequest,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ReportRevisionResponse:
    context = resolve_session_context(session, identity)
    current = _report_latest_or_error(session, context, report_key)
    if (
        payload.expected_revision is not None
        and payload.expected_revision != current.revision_number
    ):
        raise DomainError(
            "REPORT_REVISION_CONFLICT",
            "The report changed while it was being edited; reload before saving.",
            409,
            [
                {
                    "field": "expected_revision",
                    "message": f"Current revision is {current.revision_number}.",
                }
            ],
        )

    source_type = payload.source_type or current.source_type
    source_id = payload.source_id if payload.source_type is not None else current.source_id
    title = _required_text(payload.title or current.title, "title")
    template_id = (
        payload.template_version_id
        if payload.template_version_id is not None
        else current.template_version_id
    )
    template = _template_or_error(session, context, template_id)
    if payload.blocks is not None:
        blocks = _normalise_blocks(payload.blocks)
    else:
        blocks = _block_snapshot_from_rows(
            _blocks_for_revision(session, current.id, context.organization_id)
        )
    options = (
        _validate_options(payload.render_options)
        if payload.render_options is not None
        else _validate_options(current.render_options)
    )
    revision = _create_revision(
        session,
        context,
        report_key=report_key,
        revision_number=current.revision_number + 1,
        source_type=source_type,
        source_id=source_id,
        title=title,
        template=template,
        blocks=blocks,
        render_options=options,
        supersedes_revision_id=current.id,
    )
    _audit(
        session,
        context,
        "REPORT_REVISION_CREATED",
        "ReportRevision",
        revision.id,
        {
            "report_key": str(report_key),
            "revision_number": revision.revision_number,
            "supersedes_revision_id": str(current.id),
        },
    )
    _commit_or_raise(
        session,
        "REPORT_REVISION_CONFLICT",
        "The report changed while it was being edited; reload before saving.",
    )
    return _revision_response(session, revision)


@router.post(
    "/reports/{report_key}/revisions/{revision_id}/exports",
    response_model=ExportJobResponse,
)
def create_report_export(
    report_key: UUID,
    revision_id: UUID,
    payload: ReportExportRequest,
    request: Request,
    response: Response,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(_storage),
) -> ExportJobResponse:
    context = resolve_session_context(session, identity)
    revision = _revision_or_error(session, context, report_key, revision_id)
    export_format: ExportFormat = payload.export_format
    if export_format not in SUPPORTED_EXPORT_FORMATS:
        raise DomainError(
            "EXPORT_FORMAT_UNSUPPORTED",
            "The requested report export format is not supported.",
            422,
        )
    render_options = _validate_options(
        {**revision.render_options, **payload.render_options}, "render_options"
    )
    fingerprint_material = {
        "report_key": str(report_key),
        "revision_id": str(revision.id),
        "content_sha256": revision.content_sha256,
        "export_format": export_format,
        "render_options": render_options,
        "renderer_version": RENDERER_VERSION,
    }
    request_fingerprint = _content_hash(fingerprint_material)
    job = session.scalar(
        select(ExportJob).where(
            ExportJob.organization_id == context.organization_id,
            ExportJob.idempotency_key == payload.idempotency_key,
        )
    )
    is_new = job is None
    if job is not None:
        if job.request_fingerprint != request_fingerprint:
            raise DomainError(
                "EXPORT_IDEMPOTENCY_CONFLICT",
                "The export idempotency key was already used for another request.",
                409,
            )
        if job.status == "COMPLETED" and job.object_key:
            response.status_code = status.HTTP_200_OK
            return _export_response(
                job,
                storage,
                request.app.state.settings.s3_signed_url_ttl_seconds,
            )
        job.status = "QUEUED"
        job.error_snapshot = []
        job.warning_snapshot = []
    else:
        job = ExportJob(
            organization_id=context.organization_id,
            report_revision_id=revision.id,
            idempotency_key=payload.idempotency_key,
            request_fingerprint=request_fingerprint,
            export_format=export_format,
            render_options=render_options,
            renderer_version=RENDERER_VERSION,
            status="QUEUED",
            error_snapshot=[],
            warning_snapshot=[],
        )
        session.add(job)
        session.flush()
    _commit_or_raise(
        session,
        "EXPORT_IDEMPOTENCY_CONFLICT",
        "The export idempotency key was claimed by another request.",
    )
    session.refresh(job)

    snapshot = _snapshot_for_revision(session, revision)
    try:
        rendered, media_type, extension, warnings = render_report(snapshot, export_format)
    except ReportRenderError as exc:
        job.status = "FAILED"
        job.error_snapshot = [{"code": "REPORT_RENDER_FAILED", "message": str(exc)}]
        session.commit()
        raise DomainError(
            "REPORT_RENDER_FAILED",
            "The report could not be rendered from its immutable snapshot.",
            422,
        ) from exc

    object_key = (
        f"organizations/{context.organization_id}/reports/{report_key}/"
        f"revisions/{revision.revision_number}/exports/{job.id}.{extension}"
    )
    try:
        storage.ensure_bucket()
        storage.put_object(object_key, io.BytesIO(rendered), len(rendered), media_type)
    except ObjectStorageError as exc:
        job.status = "FAILED"
        job.error_snapshot = [
            {
                "code": "REPORT_STORAGE_UNAVAILABLE",
                "message": "The rendered report could not be stored durably.",
            }
        ]
        session.commit()
        raise DomainError(
            "REPORT_STORAGE_UNAVAILABLE",
            "The rendered report could not be stored durably; retry the export.",
            503,
        ) from exc
    job.status = "COMPLETED"
    job.object_key = object_key
    job.sha256 = hashlib.sha256(rendered).hexdigest()
    job.byte_size = len(rendered)
    job.media_type = media_type
    job.warning_snapshot = [
        {"code": "REPORT_RENDER_WARNING", "message": warning} for warning in warnings
    ]
    session.commit()
    session.refresh(job)
    response.status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
    return _export_response(
        job,
        storage,
        request.app.state.settings.s3_signed_url_ttl_seconds,
    )


@router.get("/report-exports/{job_id}", response_model=ExportJobResponse)
def get_report_export(
    job_id: UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ExportJobResponse:
    context = resolve_session_context(session, identity)
    job = _export_or_error(session, context, job_id)
    storage: ObjectStorage | None = None
    try:
        storage = get_storage(request.app.state.settings)
    except ObjectStorageError:
        storage = None
    return _export_response(
        job,
        storage,
        request.app.state.settings.s3_signed_url_ttl_seconds,
    )


@router.get("/report-exports/{job_id}/download", response_model=ExportDownloadResponse)
def download_report_export(
    job_id: UUID,
    request: Request,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
    storage: ObjectStorage = Depends(_storage),
) -> ExportDownloadResponse:
    context = resolve_session_context(session, identity)
    job = _export_or_error(session, context, job_id)
    if job.status != "COMPLETED" or not job.object_key or not job.sha256 or not job.media_type:
        raise DomainError(
            "REPORT_EXPORT_NOT_READY",
            "The report export is not ready for download.",
            409,
        )
    ttl_seconds = request.app.state.settings.s3_signed_url_ttl_seconds
    try:
        url = storage.presigned_get(job.object_key, ttl_seconds)
    except ObjectStorageError as exc:
        raise DomainError(
            "DOWNLOAD_LINK_UNAVAILABLE",
            "A download link could not be created for this report export.",
            503,
        ) from exc
    return ExportDownloadResponse(
        export_job_id=job.id,
        report_revision_id=job.report_revision_id,
        url=url,
        expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        sha256=job.sha256,
        media_type=job.media_type,
    )
