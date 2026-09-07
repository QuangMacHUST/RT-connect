"""P7 Machine QA protocols, runs and trend projection.

Revision ID: 20260907_0006
Revises: 20260907_0005
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260907_0006"
down_revision: str | Sequence[str] | None = "20260907_0005"
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
        "qa_protocol_versions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("protocol_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("qa_type", sa.String(length=100), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("effective_note", sa.String(length=4000), nullable=True),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "protocol_key",
            "version_number",
            name="uq_qa_protocol_versions_key_version",
        ),
    )
    op.create_index(
        "ix_qa_protocol_versions_organization_id", "qa_protocol_versions", ["organization_id"]
    )
    op.create_index(
        "ix_qa_protocol_versions_created_by_user_identity_id",
        "qa_protocol_versions",
        ["created_by_user_identity_id"],
    )
    op.create_index(
        "ix_qa_protocol_versions_organization_status",
        "qa_protocol_versions",
        ["organization_id", "status"],
    )

    op.create_table(
        "qa_protocol_rules",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("protocol_version_id", uuid_type, nullable=False),
        sa.Column("metric_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=240), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("rule_type", sa.String(length=40), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("lower_limit", sa.Float(), nullable=True),
        sa.Column("upper_limit", sa.Float(), nullable=True),
        sa.Column("tolerance", sa.Float(), nullable=True),
        sa.Column("action_level", sa.Float(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.String(length=1000), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["protocol_version_id"], ["qa_protocol_versions.id"]),
        sa.UniqueConstraint(
            "protocol_version_id", "metric_key", name="uq_qa_protocol_rules_metric"
        ),
    )
    op.create_index(
        "ix_qa_protocol_rules_organization_id", "qa_protocol_rules", ["organization_id"]
    )
    op.create_index(
        "ix_qa_protocol_rules_protocol_version_id",
        "qa_protocol_rules",
        ["protocol_version_id"],
    )
    op.create_index(
        "ix_qa_protocol_rules_protocol_order",
        "qa_protocol_rules",
        ["protocol_version_id", "sort_order"],
    )

    op.create_table(
        "machine_qa_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("qa_case_id", uuid_type, nullable=False),
        sa.Column("machine_id", uuid_type, nullable=False),
        sa.Column("protocol_version_id", uuid_type, nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("overall_status", sa.String(length=20), nullable=True),
        sa.Column("measurement_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("measurements", sa.JSON(), nullable=False),
        sa.Column("result_snapshot", sa.JSON(), nullable=False),
        sa.Column("error_snapshot", sa.JSON(), nullable=False),
        sa.Column("supersedes_run_id", uuid_type, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["qa_case_id"], ["qa_cases.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["protocol_version_id"], ["qa_protocol_versions.id"]),
        sa.ForeignKeyConstraint(["supersedes_run_id"], ["machine_qa_runs.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
    )
    op.create_index("ix_machine_qa_runs_organization_id", "machine_qa_runs", ["organization_id"])
    op.create_index("ix_machine_qa_runs_qa_case_id", "machine_qa_runs", ["qa_case_id"])
    op.create_index("ix_machine_qa_runs_machine_id", "machine_qa_runs", ["machine_id"])
    op.create_index(
        "ix_machine_qa_runs_protocol_version_id", "machine_qa_runs", ["protocol_version_id"]
    )
    op.create_index("ix_machine_qa_runs_supersedes_run_id", "machine_qa_runs", ["supersedes_run_id"])
    op.create_index(
        "ix_machine_qa_runs_created_by_user_identity_id",
        "machine_qa_runs",
        ["created_by_user_identity_id"],
    )
    op.create_index(
        "ix_machine_qa_runs_organization_case", "machine_qa_runs", ["organization_id", "qa_case_id"]
    )
    op.create_index(
        "ix_machine_qa_runs_organization_status", "machine_qa_runs", ["organization_id", "status"]
    )

    op.create_table(
        "trend_points",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("machine_id", uuid_type, nullable=False),
        sa.Column("qa_case_id", uuid_type, nullable=False),
        sa.Column("source_run_id", uuid_type, nullable=False),
        sa.Column("metric_key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["qa_case_id"], ["qa_cases.id"]),
        sa.ForeignKeyConstraint(["source_run_id"], ["machine_qa_runs.id"]),
    )
    op.create_index("ix_trend_points_organization_id", "trend_points", ["organization_id"])
    op.create_index("ix_trend_points_machine_id", "trend_points", ["machine_id"])
    op.create_index("ix_trend_points_qa_case_id", "trend_points", ["qa_case_id"])
    op.create_index("ix_trend_points_source_run_id", "trend_points", ["source_run_id"])
    op.create_index(
        "ix_trend_points_organization_machine_metric",
        "trend_points",
        ["organization_id", "machine_id", "metric_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_trend_points_organization_machine_metric", table_name="trend_points")
    op.drop_index("ix_trend_points_source_run_id", table_name="trend_points")
    op.drop_index("ix_trend_points_qa_case_id", table_name="trend_points")
    op.drop_index("ix_trend_points_machine_id", table_name="trend_points")
    op.drop_index("ix_trend_points_organization_id", table_name="trend_points")
    op.drop_table("trend_points")

    op.drop_index("ix_machine_qa_runs_organization_status", table_name="machine_qa_runs")
    op.drop_index("ix_machine_qa_runs_organization_case", table_name="machine_qa_runs")
    op.drop_index("ix_machine_qa_runs_created_by_user_identity_id", table_name="machine_qa_runs")
    op.drop_index("ix_machine_qa_runs_supersedes_run_id", table_name="machine_qa_runs")
    op.drop_index("ix_machine_qa_runs_protocol_version_id", table_name="machine_qa_runs")
    op.drop_index("ix_machine_qa_runs_machine_id", table_name="machine_qa_runs")
    op.drop_index("ix_machine_qa_runs_qa_case_id", table_name="machine_qa_runs")
    op.drop_index("ix_machine_qa_runs_organization_id", table_name="machine_qa_runs")
    op.drop_table("machine_qa_runs")

    op.drop_index("ix_qa_protocol_rules_protocol_order", table_name="qa_protocol_rules")
    op.drop_index("ix_qa_protocol_rules_protocol_version_id", table_name="qa_protocol_rules")
    op.drop_index("ix_qa_protocol_rules_organization_id", table_name="qa_protocol_rules")
    op.drop_table("qa_protocol_rules")

    op.drop_index(
        "ix_qa_protocol_versions_organization_status", table_name="qa_protocol_versions"
    )
    op.drop_index(
        "ix_qa_protocol_versions_created_by_user_identity_id", table_name="qa_protocol_versions"
    )
    op.drop_index("ix_qa_protocol_versions_organization_id", table_name="qa_protocol_versions")
    op.drop_table("qa_protocol_versions")
