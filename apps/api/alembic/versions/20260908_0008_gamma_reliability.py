"""Add fenced Gamma worker attempts and durable dispatch outbox.

Revision ID: 20260908_0008
Revises: 20260907_0007
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0008"
down_revision: str | Sequence[str] | None = "20260907_0007"
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
    op.add_column("gamma_analysis_runs", sa.Column("worker_id", sa.String(length=200)))
    op.add_column("gamma_analysis_runs", sa.Column("lease_token", sa.String(length=64)))
    op.add_column("gamma_analysis_runs", sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.create_unique_constraint(
        "uq_gamma_analysis_runs_lease_token", "gamma_analysis_runs", ["lease_token"]
    )

    op.create_table(
        "gamma_run_attempts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("gamma_run_id", uuid_type, nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=200), nullable=False),
        sa.Column("lease_token", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="RUNNING"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_snapshot", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["gamma_run_id"], ["gamma_analysis_runs.id"]),
        sa.UniqueConstraint(
            "gamma_run_id",
            "attempt_number",
            name="uq_gamma_run_attempts_run_number",
        ),
    )
    op.create_index(
        "ix_gamma_run_attempts_organization_id", "gamma_run_attempts", ["organization_id"]
    )
    op.create_index(
        "ix_gamma_run_attempts_gamma_run_id", "gamma_run_attempts", ["gamma_run_id"]
    )
    op.create_index(
        "ix_gamma_run_attempts_organization_run",
        "gamma_run_attempts",
        ["organization_id", "gamma_run_id"],
    )

    op.create_table(
        "gamma_dispatch_outbox",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("gamma_run_id", uuid_type, nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["gamma_run_id"], ["gamma_analysis_runs.id"]),
        sa.UniqueConstraint(
            "gamma_run_id",
            "attempt_number",
            name="uq_gamma_dispatch_outbox_run_attempt",
        ),
    )
    op.create_index(
        "ix_gamma_dispatch_outbox_status_available",
        "gamma_dispatch_outbox",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_gamma_dispatch_outbox_organization_id",
        "gamma_dispatch_outbox",
        ["organization_id"],
    )
    op.create_index(
        "ix_gamma_dispatch_outbox_gamma_run_id", "gamma_dispatch_outbox", ["gamma_run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_gamma_dispatch_outbox_gamma_run_id", table_name="gamma_dispatch_outbox")
    op.drop_index(
        "ix_gamma_dispatch_outbox_organization_id", table_name="gamma_dispatch_outbox"
    )
    op.drop_index(
        "ix_gamma_dispatch_outbox_status_available", table_name="gamma_dispatch_outbox"
    )
    op.drop_table("gamma_dispatch_outbox")

    op.drop_index(
        "ix_gamma_run_attempts_organization_run", table_name="gamma_run_attempts"
    )
    op.drop_index("ix_gamma_run_attempts_gamma_run_id", table_name="gamma_run_attempts")
    op.drop_index("ix_gamma_run_attempts_organization_id", table_name="gamma_run_attempts")
    op.drop_table("gamma_run_attempts")

    op.drop_constraint(
        "uq_gamma_analysis_runs_lease_token", "gamma_analysis_runs", type_="unique"
    )
    op.drop_column("gamma_analysis_runs", "lease_expires_at")
    op.drop_column("gamma_analysis_runs", "lease_token")
    op.drop_column("gamma_analysis_runs", "worker_id")
