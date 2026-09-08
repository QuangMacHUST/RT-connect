"""Add independent biological scenarios and calculation history foundations.

Revision ID: 20260908_0012
Revises: 20260908_0011
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0012"
down_revision: str | Sequence[str] | None = "20260908_0011"
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

    # The revision table refers back to the scenario, while a clone records
    # the source revision. Create the first FK after both tables exist.
    op.create_table(
        "biological_scenarios",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("scenario_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("scenario_type", sa.String(length=80), nullable=False),
        sa.Column("tissue_context", sa.String(length=240), nullable=False),
        sa.Column("clinical_context", sa.String(length=4000), nullable=True),
        sa.Column(
            "source_type",
            sa.String(length=40),
            nullable=False,
            server_default="USER_DEFINED",
        ),
        sa.Column("source_reference", sa.String(length=1000), nullable=True),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint(
            "organization_id",
            "scenario_key",
            name="uq_biological_scenarios_organization_key",
        ),
    )
    op.create_index(
        "ix_biological_scenarios_organization_id",
        "biological_scenarios",
        ["organization_id"],
    )
    op.create_index(
        "ix_biological_scenarios_organization_status",
        "biological_scenarios",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_biological_scenarios_organization_updated",
        "biological_scenarios",
        ["organization_id", "updated_at"],
    )
    op.create_index(
        "ix_biological_scenarios_created_by_user_identity_id",
        "biological_scenarios",
        ["created_by_user_identity_id"],
    )

    op.create_table(
        "biological_scenario_revisions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("scenario_id", uuid_type, nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["scenario_id"], ["biological_scenarios.id"]
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint(
            "scenario_id",
            "revision_number",
            name="uq_biological_scenario_revisions_number",
        ),
    )
    op.create_index(
        "ix_biological_scenario_revisions_organization_id",
        "biological_scenario_revisions",
        ["organization_id"],
    )
    op.create_index(
        "ix_biological_scenario_revisions_scenario_id",
        "biological_scenario_revisions",
        ["scenario_id"],
    )
    op.create_index(
        "ix_biological_scenario_revisions_organization_scenario",
        "biological_scenario_revisions",
        ["organization_id", "scenario_id"],
    )
    op.create_index(
        "ix_biological_scenario_revisions_created_by_user_identity_id",
        "biological_scenario_revisions",
        ["created_by_user_identity_id"],
    )
    op.add_column(
        "biological_scenarios",
        sa.Column("source_scenario_revision_id", uuid_type, nullable=True),
    )
    op.create_index(
        "ix_biological_scenarios_source_scenario_revision_id",
        "biological_scenarios",
        ["source_scenario_revision_id"],
    )
    op.create_foreign_key(
        "fk_biological_scenarios_source_scenario_revision",
        "biological_scenarios",
        "biological_scenario_revisions",
        ["source_scenario_revision_id"],
        ["id"],
    )

    op.create_table(
        "biological_calculation_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("scenario_id", uuid_type, nullable=False),
        sa.Column("scenario_revision_id", uuid_type, nullable=False),
        sa.Column("calculation_type", sa.String(length=80), nullable=False),
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
    )
    op.create_index(
        "ix_biological_calculation_runs_organization_id",
        "biological_calculation_runs",
        ["organization_id"],
    )
    op.create_index(
        "ix_biological_calculation_runs_scenario_id",
        "biological_calculation_runs",
        ["scenario_id"],
    )
    op.create_index(
        "ix_biological_calculation_runs_scenario_revision_id",
        "biological_calculation_runs",
        ["scenario_revision_id"],
    )
    op.create_index(
        "ix_biological_calculation_runs_organization_scenario",
        "biological_calculation_runs",
        ["organization_id", "scenario_id"],
    )
    op.create_index(
        "ix_biological_calculation_runs_organization_status",
        "biological_calculation_runs",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_biological_calculation_runs_created_by_user_identity_id",
        "biological_calculation_runs",
        ["created_by_user_identity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_biological_calculation_runs_created_by_user_identity_id",
        table_name="biological_calculation_runs",
    )
    op.drop_index(
        "ix_biological_calculation_runs_organization_status",
        table_name="biological_calculation_runs",
    )
    op.drop_index(
        "ix_biological_calculation_runs_organization_scenario",
        table_name="biological_calculation_runs",
    )
    op.drop_index(
        "ix_biological_calculation_runs_scenario_revision_id",
        table_name="biological_calculation_runs",
    )
    op.drop_index(
        "ix_biological_calculation_runs_scenario_id",
        table_name="biological_calculation_runs",
    )
    op.drop_index(
        "ix_biological_calculation_runs_organization_id",
        table_name="biological_calculation_runs",
    )
    op.drop_table("biological_calculation_runs")

    op.drop_constraint(
        "fk_biological_scenarios_source_scenario_revision",
        "biological_scenarios",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_biological_scenarios_source_scenario_revision_id",
        table_name="biological_scenarios",
    )
    op.drop_column("biological_scenarios", "source_scenario_revision_id")

    op.drop_index(
        "ix_biological_scenario_revisions_created_by_user_identity_id",
        table_name="biological_scenario_revisions",
    )
    op.drop_index(
        "ix_biological_scenario_revisions_organization_scenario",
        table_name="biological_scenario_revisions",
    )
    op.drop_index(
        "ix_biological_scenario_revisions_scenario_id",
        table_name="biological_scenario_revisions",
    )
    op.drop_index(
        "ix_biological_scenario_revisions_organization_id",
        table_name="biological_scenario_revisions",
    )
    op.drop_table("biological_scenario_revisions")

    op.drop_index(
        "ix_biological_scenarios_created_by_user_identity_id",
        table_name="biological_scenarios",
    )
    op.drop_index(
        "ix_biological_scenarios_organization_updated",
        table_name="biological_scenarios",
    )
    op.drop_index(
        "ix_biological_scenarios_organization_status",
        table_name="biological_scenarios",
    )
    op.drop_index(
        "ix_biological_scenarios_organization_id",
        table_name="biological_scenarios",
    )
    op.drop_table("biological_scenarios")
