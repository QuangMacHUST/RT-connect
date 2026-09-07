"""P8 Gamma analysis jobs, snapshots and result lifecycle.

Revision ID: 20260907_0007
Revises: 20260907_0006
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260907_0007"
down_revision: str | Sequence[str] | None = "20260907_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid() -> postgresql.UUID:
    return postgresql.UUID(as_uuid=True)


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    ]


def upgrade() -> None:
    uuid_type = _uuid()
    op.create_table(
        "gamma_analysis_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("qa_case_id", uuid_type, nullable=False),
        sa.Column("reference_artifact_id", uuid_type, nullable=False),
        sa.Column("evaluation_artifact_id", uuid_type, nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="QUEUED"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engine_version", sa.String(length=100), nullable=False),
        sa.Column("config_snapshot", sa.JSON(), nullable=False),
        sa.Column("input_manifest_snapshot", sa.JSON(), nullable=False),
        sa.Column("result_snapshot", sa.JSON(), nullable=False),
        sa.Column("error_snapshot", sa.JSON(), nullable=False),
        sa.Column("warning_snapshot", sa.JSON(), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["qa_case_id"], ["qa_cases.id"]),
        sa.ForeignKeyConstraint(["reference_artifact_id"], ["artifacts.id"]),
        sa.ForeignKeyConstraint(["evaluation_artifact_id"], ["artifacts.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_gamma_analysis_runs_organization_idempotency",
        ),
    )
    op.create_index("ix_gamma_analysis_runs_organization_id", "gamma_analysis_runs", ["organization_id"])
    op.create_index("ix_gamma_analysis_runs_qa_case_id", "gamma_analysis_runs", ["qa_case_id"])
    op.create_index(
        "ix_gamma_analysis_runs_reference_artifact_id",
        "gamma_analysis_runs",
        ["reference_artifact_id"],
    )
    op.create_index(
        "ix_gamma_analysis_runs_evaluation_artifact_id",
        "gamma_analysis_runs",
        ["evaluation_artifact_id"],
    )
    op.create_index(
        "ix_gamma_analysis_runs_created_by_user_identity_id",
        "gamma_analysis_runs",
        ["created_by_user_identity_id"],
    )
    op.create_index(
        "ix_gamma_analysis_runs_organization_case",
        "gamma_analysis_runs",
        ["organization_id", "qa_case_id"],
    )
    op.create_index(
        "ix_gamma_analysis_runs_organization_status",
        "gamma_analysis_runs",
        ["organization_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_gamma_analysis_runs_organization_status", table_name="gamma_analysis_runs")
    op.drop_index("ix_gamma_analysis_runs_organization_case", table_name="gamma_analysis_runs")
    op.drop_index(
        "ix_gamma_analysis_runs_created_by_user_identity_id", table_name="gamma_analysis_runs"
    )
    op.drop_index(
        "ix_gamma_analysis_runs_evaluation_artifact_id", table_name="gamma_analysis_runs"
    )
    op.drop_index(
        "ix_gamma_analysis_runs_reference_artifact_id", table_name="gamma_analysis_runs"
    )
    op.drop_index("ix_gamma_analysis_runs_qa_case_id", table_name="gamma_analysis_runs")
    op.drop_index("ix_gamma_analysis_runs_organization_id", table_name="gamma_analysis_runs")
    op.drop_table("gamma_analysis_runs")
