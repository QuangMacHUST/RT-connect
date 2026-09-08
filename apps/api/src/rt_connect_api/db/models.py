"""Organization-scoped RT-CONNECT entities and lifecycle evidence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rt_connect_api.db.base import Base


class TimestampedIdMixin:
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Organization(TimestampedIdMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    sites: Mapped[list[Site]] = relationship(back_populates="organization")
    memberships: Mapped[list[OrganizationMembership]] = relationship(back_populates="organization")


class UserIdentity(TimestampedIdMixin, Base):
    """Application projection of a Supabase identity; password material is never stored here."""

    __tablename__ = "user_identities"

    supabase_user_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    memberships: Mapped[list[OrganizationMembership]] = relationship(back_populates="user_identity")


class OrganizationMembership(TimestampedIdMixin, Base):
    """Membership defines organization scope, not an action-level role hierarchy."""

    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_identity_id", name="uq_organization_memberships_identity"
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_identities.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    organization: Mapped[Organization] = relationship(back_populates="memberships")
    user_identity: Mapped[UserIdentity] = relationship(back_populates="memberships")


class Site(TimestampedIdMixin, Base):
    __tablename__ = "sites"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    organization: Mapped[Organization] = relationship(back_populates="sites")
    machines: Mapped[list[Machine]] = relationship(back_populates="site")


class Machine(TimestampedIdMixin, Base):
    __tablename__ = "machines"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)
    stable_machine_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="ACTIVE")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    site: Mapped[Site] = relationship(back_populates="machines")


class Folder(TimestampedIdMixin, Base):
    """User-defined organization folder; archive never deletes its records."""

    __tablename__ = "folders"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    parent_folder_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("folders.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )
    parent: Mapped[Folder | None] = relationship(
        "Folder", remote_side="Folder.id", back_populates="children"
    )
    children: Mapped[list[Folder]] = relationship("Folder", back_populates="parent")


class QACase(TimestampedIdMixin, Base):
    """A QA record that remains stable while folders are renamed or moved."""

    __tablename__ = "qa_cases"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)
    machine_id: Mapped[UUID] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    primary_folder_id: Mapped[UUID] = mapped_column(
        ForeignKey("folders.id"), nullable=False, index=True
    )
    qa_type: Mapped[str] = mapped_column(String(100), nullable=False)
    qa_cycle: Mapped[str] = mapped_column(String(40), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    protocol_version_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True
    )
    status_note: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    case_status: Mapped[str] = mapped_column(String(40), nullable=False, server_default="OPEN")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )


class QAProtocolVersion(TimestampedIdMixin, Base):
    """Immutable protocol header used to create a reproducible QA run."""

    __tablename__ = "qa_protocol_versions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "protocol_key",
            "version_number",
            name="uq_qa_protocol_versions_key_version",
        ),
        Index("ix_qa_protocol_versions_organization_status", "organization_id", "status"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    protocol_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    qa_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ACTIVE")
    effective_note: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    created_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )


class QAProtocolRule(TimestampedIdMixin, Base):
    """A versioned rule snapshot; child rows are never edited in place."""

    __tablename__ = "qa_protocol_rules"
    __table_args__ = (
        UniqueConstraint(
            "protocol_version_id", "metric_key", name="uq_qa_protocol_rules_metric"
        ),
        Index("ix_qa_protocol_rules_protocol_order", "protocol_version_id", "sort_order"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    protocol_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("qa_protocol_versions.id"), nullable=False, index=True
    )
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(240), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    lower_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    upper_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    tolerance: Mapped[float | None] = mapped_column(Float, nullable=True)
    action_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class MachineQARun(TimestampedIdMixin, Base):
    """Draft or completed Machine QA run with immutable result snapshots."""

    __tablename__ = "machine_qa_runs"
    __table_args__ = (
        Index("ix_machine_qa_runs_organization_case", "organization_id", "qa_case_id"),
        Index("ix_machine_qa_runs_organization_status", "organization_id", "status"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    qa_case_id: Mapped[UUID] = mapped_column(ForeignKey("qa_cases.id"), nullable=False, index=True)
    machine_id: Mapped[UUID] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    protocol_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("qa_protocol_versions.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="DRAFT")
    overall_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    measurement_revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    measurements: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    result_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    error_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    supersedes_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("machine_qa_runs.id"), nullable=True, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )


class TrendPoint(TimestampedIdMixin, Base):
    """Small read-model projection pointing back to a completed QA run."""

    __tablename__ = "trend_points"
    __table_args__ = (
        Index(
            "ix_trend_points_organization_machine_metric",
            "organization_id",
            "machine_id",
            "metric_key",
        ),
        Index("ix_trend_points_source_run", "source_run_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    machine_id: Mapped[UUID] = mapped_column(ForeignKey("machines.id"), nullable=False, index=True)
    qa_case_id: Mapped[UUID] = mapped_column(ForeignKey("qa_cases.id"), nullable=False, index=True)
    source_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("machine_qa_runs.id"), nullable=False, index=True
    )
    metric_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class GammaAnalysisRun(TimestampedIdMixin, Base):
    """Queued PSQA Gamma analysis with immutable input/config/result snapshots."""

    __tablename__ = "gamma_analysis_runs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_gamma_analysis_runs_organization_idempotency",
        ),
        Index("ix_gamma_analysis_runs_organization_case", "organization_id", "qa_case_id"),
        Index("ix_gamma_analysis_runs_organization_status", "organization_id", "status"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    qa_case_id: Mapped[UUID] = mapped_column(ForeignKey("qa_cases.id"), nullable=False, index=True)
    reference_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifacts.id"), nullable=False, index=True
    )
    evaluation_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifacts.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="QUEUED")
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    engine_version: Mapped[str] = mapped_column(String(100), nullable=False)
    config_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    input_manifest_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    result_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    error_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    warning_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )


class GammaRunAttempt(TimestampedIdMixin, Base):
    """Fenced execution attempt for one Gamma run."""

    __tablename__ = "gamma_run_attempts"
    __table_args__ = (
        UniqueConstraint(
            "gamma_run_id",
            "attempt_number",
            name="uq_gamma_run_attempts_run_number",
        ),
        Index("ix_gamma_run_attempts_organization_run", "organization_id", "gamma_run_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    gamma_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("gamma_analysis_runs.id"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_id: Mapped[str] = mapped_column(String(200), nullable=False)
    lease_token: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_snapshot: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )


class GammaDispatchOutbox(TimestampedIdMixin, Base):
    """Durable Redis dispatch intent used to reconcile DB/queue failures."""

    __tablename__ = "gamma_dispatch_outbox"
    __table_args__ = (
        UniqueConstraint(
            "gamma_run_id",
            "attempt_number",
            name="uq_gamma_dispatch_outbox_run_attempt",
        ),
        Index("ix_gamma_dispatch_outbox_status_available", "status", "available_at"),
        Index("ix_gamma_dispatch_outbox_organization", "organization_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    gamma_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("gamma_analysis_runs.id"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="PENDING")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ReportTemplateVersion(TimestampedIdMixin, Base):
    """Versioned report layout owned by one organization."""

    __tablename__ = "report_template_versions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "template_key",
            "version_number",
            name="uq_report_template_versions_key_version",
        ),
        Index(
            "ix_report_template_versions_organization_status",
            "organization_id",
            "status",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    template_key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="ACTIVE")
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    blocks_snapshot: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    render_options: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )


class ReportRevision(TimestampedIdMixin, Base):
    """Immutable report content and source snapshot for one report aggregate."""

    __tablename__ = "report_revisions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "report_key",
            "revision_number",
            name="uq_report_revisions_key_number",
        ),
        Index(
            "ix_report_revisions_organization_source",
            "organization_id",
            "source_type",
            "source_id",
        ),
        Index("ix_report_revisions_organization_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    report_key: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False, index=True, default=uuid4
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    template_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("report_template_versions.id"), nullable=True, index=True
    )
    source_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    render_options: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="SAVED")
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("report_revisions.id"), nullable=True, index=True
    )
    created_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )


class ReportBlockConfig(TimestampedIdMixin, Base):
    """Stable block identity and user layout for one immutable report revision."""

    __tablename__ = "report_block_configs"
    __table_args__ = (
        UniqueConstraint(
            "report_revision_id",
            "stable_block_id",
            name="uq_report_block_configs_revision_block",
        ),
        Index("ix_report_block_configs_revision_order", "report_revision_id", "sort_order"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    report_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("report_revisions.id"), nullable=False, index=True
    )
    stable_block_id: Mapped[str] = mapped_column(String(120), nullable=False)
    block_type: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    config: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    source_binding: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)


class ExportJob(TimestampedIdMixin, Base):
    """Idempotent report export with a durable object-storage result."""

    __tablename__ = "export_jobs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_export_jobs_organization_idempotency",
        ),
        Index("ix_export_jobs_organization_revision", "organization_id", "report_revision_id"),
        Index("ix_export_jobs_organization_status", "organization_id", "status"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    report_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("report_revisions.id"), nullable=False, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    export_format: Mapped[str] = mapped_column(String(20), nullable=False)
    render_options: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    renderer_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="QUEUED")
    object_key: Mapped[str | None] = mapped_column(String(768), nullable=True, unique=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_snapshot: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    warning_snapshot: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)


class Artifact(TimestampedIdMixin, Base):
    """Immutable source or derived file metadata; bytes live in object storage."""

    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifacts_organization_checksum", "organization_id", "sha256"),
        Index("ix_artifacts_organization_status", "organization_id", "data_status"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    qa_case_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("qa_cases.id"), nullable=True, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    modality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    object_key: Mapped[str] = mapped_column(String(768), nullable=False, unique=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    sop_class_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sop_instance_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    study_instance_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    series_instance_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    frame_of_reference_uid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_system: Mapped[str | None] = mapped_column(String(200), nullable=True)
    uploaded_by_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    data_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="UPLOADED", index=True
    )
    parent_artifact_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("artifacts.id"), nullable=True, index=True
    )
    metadata_snapshot: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)


class InputManifest(TimestampedIdMixin, Base):
    """Organization-scoped declaration of how an artifact may be used."""

    __tablename__ = "input_manifests"
    __table_args__ = (
        Index("ix_input_manifests_organization_artifact", "organization_id", "artifact_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True, index=True
    )
    artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifacts.id"), nullable=False, index=True
    )
    logical_role: Mapped[str] = mapped_column(String(30), nullable=False)
    checksum_at_use: Mapped[str] = mapped_column(String(64), nullable=False)
    selected_metadata: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    geometry_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    unit_summary: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    validation_summary: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )


class ValidationRun(TimestampedIdMixin, Base):
    """A reproducible validation result for one uploaded artifact or manifest."""

    __tablename__ = "validation_runs"
    __table_args__ = (
        Index("ix_validation_runs_organization_subject", "organization_id", "subject_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    validation_type: Mapped[str] = mapped_column(String(60), nullable=False)
    validator_version: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    checks: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    errors: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    input_manifest_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )


class AuditEvent(TimestampedIdMixin, Base):
    """Append-only lifecycle evidence for organization-scoped changes."""

    __tablename__ = "audit_events"

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    actor_user_identity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user_identities.id"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True, index=True
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
