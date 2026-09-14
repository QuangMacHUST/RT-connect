"""Add durable execution snapshots for pylinac Machine QA."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260914_0023"
down_revision: str | Sequence[str] | None = "20260913_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "pylinac_qa_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("qa_case_id", uuid_type, nullable=False),
        sa.Column("machine_id", uuid_type, nullable=False),
        sa.Column("catalog_key", sa.String(length=120), nullable=False),
        sa.Column("engine_class", sa.String(length=160), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("package_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="RUNNING"),
        sa.Column("assessment_status", sa.String(length=20), nullable=True),
        sa.Column("parameters_snapshot", sa.JSON(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("result_snapshot", sa.JSON(), nullable=False),
        sa.Column("warning_snapshot", sa.JSON(), nullable=False),
        sa.Column("error_snapshot", sa.JSON(), nullable=False),
        sa.Column("overlay_artifact_id", uuid_type, nullable=True),
        sa.Column("supersedes_run_id", uuid_type, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["qa_case_id"], ["qa_cases.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["overlay_artifact_id"], ["artifacts.id"]),
        sa.ForeignKeyConstraint(["supersedes_run_id"], ["pylinac_qa_runs.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
    )
    op.create_index(
        "ix_pylinac_qa_runs_organization_id", "pylinac_qa_runs", ["organization_id"]
    )
    op.create_index("ix_pylinac_qa_runs_qa_case_id", "pylinac_qa_runs", ["qa_case_id"])
    op.create_index("ix_pylinac_qa_runs_machine_id", "pylinac_qa_runs", ["machine_id"])
    op.create_index(
        "ix_pylinac_qa_runs_organization_case",
        "pylinac_qa_runs",
        ["organization_id", "qa_case_id"],
    )
    op.create_index(
        "ix_pylinac_qa_runs_organization_status",
        "pylinac_qa_runs",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_pylinac_qa_runs_organization_catalog",
        "pylinac_qa_runs",
        ["organization_id", "catalog_key"],
    )
    op.create_index(
        "ix_pylinac_qa_runs_overlay_artifact_id", "pylinac_qa_runs", ["overlay_artifact_id"]
    )
    op.create_index(
        "ix_pylinac_qa_runs_supersedes_run_id", "pylinac_qa_runs", ["supersedes_run_id"]
    )
    op.create_index(
        "ix_pylinac_qa_runs_created_by_user_identity_id",
        "pylinac_qa_runs",
        ["created_by_user_identity_id"],
    )


def downgrade() -> None:
    for name in (
        "ix_pylinac_qa_runs_created_by_user_identity_id",
        "ix_pylinac_qa_runs_supersedes_run_id",
        "ix_pylinac_qa_runs_overlay_artifact_id",
        "ix_pylinac_qa_runs_organization_catalog",
        "ix_pylinac_qa_runs_organization_status",
        "ix_pylinac_qa_runs_organization_case",
        "ix_pylinac_qa_runs_machine_id",
        "ix_pylinac_qa_runs_qa_case_id",
        "ix_pylinac_qa_runs_organization_id",
    ):
        op.drop_index(name, table_name="pylinac_qa_runs")
    op.drop_table("pylinac_qa_runs")
