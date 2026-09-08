"""Add immutable P15 re-irradiation and fraction-compensation snapshots.

Revision ID: 20260908_0015
Revises: 20260908_0014
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0015"
down_revision: str | Sequence[str] | None = "20260908_0014"
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
        "biological_reirradiation_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("scenario_id", uuid_type, nullable=False),
        sa.Column("scenario_revision_id", uuid_type, nullable=False),
        sa.Column("operation_type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("model_key", sa.String(length=120), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="COMPLETED"),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("result_snapshot", sa.JSON(), nullable=False),
        sa.Column("warning_snapshot", sa.JSON(), nullable=False),
        sa.Column("error_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["biological_scenarios.id"]),
        sa.ForeignKeyConstraint(
            ["scenario_revision_id"], ["biological_scenario_revisions.id"]
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_biological_reirradiation_runs_organization_idempotency",
        ),
    )
    op.create_index(
        "ix_biological_reirradiation_runs_organization_id",
        "biological_reirradiation_runs",
        ["organization_id"],
    )
    op.create_index(
        "ix_biological_reirradiation_runs_scenario_id",
        "biological_reirradiation_runs",
        ["scenario_id"],
    )
    op.create_index(
        "ix_biological_reirradiation_runs_scenario_revision_id",
        "biological_reirradiation_runs",
        ["scenario_revision_id"],
    )
    op.create_index(
        "ix_biological_reirradiation_runs_organization_scenario",
        "biological_reirradiation_runs",
        ["organization_id", "scenario_id"],
    )
    op.create_index(
        "ix_biological_reirradiation_runs_organization_operation",
        "biological_reirradiation_runs",
        ["organization_id", "operation_type"],
    )
    op.create_index(
        "ix_biological_reirradiation_runs_organization_status",
        "biological_reirradiation_runs",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_biological_reirradiation_runs_created_by_user_identity_id",
        "biological_reirradiation_runs",
        ["created_by_user_identity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_biological_reirradiation_runs_created_by_user_identity_id",
        table_name="biological_reirradiation_runs",
    )
    op.drop_index(
        "ix_biological_reirradiation_runs_organization_status",
        table_name="biological_reirradiation_runs",
    )
    op.drop_index(
        "ix_biological_reirradiation_runs_organization_operation",
        table_name="biological_reirradiation_runs",
    )
    op.drop_index(
        "ix_biological_reirradiation_runs_organization_scenario",
        table_name="biological_reirradiation_runs",
    )
    op.drop_index(
        "ix_biological_reirradiation_runs_scenario_revision_id",
        table_name="biological_reirradiation_runs",
    )
    op.drop_index(
        "ix_biological_reirradiation_runs_scenario_id",
        table_name="biological_reirradiation_runs",
    )
    op.drop_index(
        "ix_biological_reirradiation_runs_organization_id",
        table_name="biological_reirradiation_runs",
    )
    op.drop_table("biological_reirradiation_runs")
