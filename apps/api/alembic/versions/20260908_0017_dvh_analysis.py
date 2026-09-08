"""Add the P17 visual-dose and DVH analysis snapshot table.

Revision ID: 20260908_0017
Revises: 20260908_0016
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0017"
down_revision: str | Sequence[str] | None = "20260908_0016"
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
        "dvh_analysis_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("qa_case_id", uuid_type, nullable=False),
        sa.Column("dose_artifact_id", uuid_type, nullable=False),
        sa.Column("structure_artifact_id", uuid_type, nullable=False),
        sa.Column("ct_artifact_id", uuid_type, nullable=True),
        sa.Column("roi_number", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("engine_key", sa.String(length=120), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="COMPLETED"),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("result_snapshot", sa.JSON(), nullable=False),
        sa.Column("warning_snapshot", sa.JSON(), nullable=False),
        sa.Column("error_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["qa_case_id"], ["qa_cases.id"]),
        sa.ForeignKeyConstraint(["dose_artifact_id"], ["artifacts.id"]),
        sa.ForeignKeyConstraint(["structure_artifact_id"], ["artifacts.id"]),
        sa.ForeignKeyConstraint(["ct_artifact_id"], ["artifacts.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_dvh_analysis_runs_organization_idempotency",
        ),
    )
    op.create_index(
        "ix_dvh_analysis_runs_organization_id",
        "dvh_analysis_runs",
        ["organization_id"],
    )
    op.create_index(
        "ix_dvh_analysis_runs_qa_case_id",
        "dvh_analysis_runs",
        ["qa_case_id"],
    )
    op.create_index(
        "ix_dvh_analysis_runs_dose_artifact_id",
        "dvh_analysis_runs",
        ["dose_artifact_id"],
    )
    op.create_index(
        "ix_dvh_analysis_runs_structure_artifact_id",
        "dvh_analysis_runs",
        ["structure_artifact_id"],
    )
    op.create_index(
        "ix_dvh_analysis_runs_ct_artifact_id",
        "dvh_analysis_runs",
        ["ct_artifact_id"],
    )
    op.create_index(
        "ix_dvh_analysis_runs_organization_case",
        "dvh_analysis_runs",
        ["organization_id", "qa_case_id"],
    )
    op.create_index(
        "ix_dvh_analysis_runs_organization_status",
        "dvh_analysis_runs",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_dvh_analysis_runs_created_by_user_identity_id",
        "dvh_analysis_runs",
        ["created_by_user_identity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dvh_analysis_runs_created_by_user_identity_id",
        table_name="dvh_analysis_runs",
    )
    op.drop_index(
        "ix_dvh_analysis_runs_organization_status",
        table_name="dvh_analysis_runs",
    )
    op.drop_index(
        "ix_dvh_analysis_runs_organization_case",
        table_name="dvh_analysis_runs",
    )
    op.drop_index("ix_dvh_analysis_runs_ct_artifact_id", table_name="dvh_analysis_runs")
    op.drop_index("ix_dvh_analysis_runs_structure_artifact_id", table_name="dvh_analysis_runs")
    op.drop_index("ix_dvh_analysis_runs_dose_artifact_id", table_name="dvh_analysis_runs")
    op.drop_index("ix_dvh_analysis_runs_qa_case_id", table_name="dvh_analysis_runs")
    op.drop_index("ix_dvh_analysis_runs_organization_id", table_name="dvh_analysis_runs")
    op.drop_table("dvh_analysis_runs")
