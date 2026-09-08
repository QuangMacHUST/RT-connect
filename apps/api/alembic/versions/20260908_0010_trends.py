"""Add compatible trend series, versioned baselines and maintenance markers.

Revision ID: 20260908_0010
Revises: 20260908_0009
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0010"
down_revision: str | Sequence[str] | None = "20260908_0009"
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

    # P7 trend points remain valid for old runs.  The JSON context is additive;
    # the application treats an absent optional dimension as an explicit unknown
    # rather than silently combining it with a named detector/energy/phantom.
    op.add_column(
        "trend_points",
        sa.Column(
            "context_snapshot",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.create_unique_constraint(
        "uq_trend_points_source_metric",
        "trend_points",
        ["organization_id", "source_run_id", "metric_key"],
    )
    op.create_index(
        "ix_trend_points_organization_measured_at",
        "trend_points",
        ["organization_id", "measured_at"],
    )

    op.create_table(
        "baseline_versions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("machine_id", uuid_type, nullable=False),
        sa.Column("metric_key", sa.String(length=120), nullable=False),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("tolerance", sa.Float(), nullable=True),
        sa.Column("action_level", sa.Float(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="MANUAL"),
        sa.Column("source_id", uuid_type, nullable=True),
        sa.Column("context_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint(
            "organization_id",
            "machine_id",
            "metric_key",
            "version_number",
            name="uq_baseline_versions_machine_metric_version",
        ),
    )
    op.create_index(
        "ix_baseline_versions_organization_id",
        "baseline_versions",
        ["organization_id"],
    )
    op.create_index(
        "ix_baseline_versions_machine_id", "baseline_versions", ["machine_id"]
    )
    op.create_index(
        "ix_baseline_versions_created_by_user_identity_id",
        "baseline_versions",
        ["created_by_user_identity_id"],
    )
    op.create_index(
        "ix_baseline_versions_organization_lookup",
        "baseline_versions",
        ["organization_id", "machine_id", "metric_key", "status"],
    )

    op.create_table(
        "maintenance_events",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("machine_id", uuid_type, nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=True),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
    )
    op.create_index(
        "ix_maintenance_events_organization_id",
        "maintenance_events",
        ["organization_id"],
    )
    op.create_index(
        "ix_maintenance_events_machine_id", "maintenance_events", ["machine_id"]
    )
    op.create_index(
        "ix_maintenance_events_organization_machine_time",
        "maintenance_events",
        ["organization_id", "machine_id", "started_at"],
    )
    op.create_index(
        "ix_maintenance_events_organization_status",
        "maintenance_events",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_maintenance_events_created_by_user_identity_id",
        "maintenance_events",
        ["created_by_user_identity_id"],
    )

    op.create_table(
        "maintenance_event_revisions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("maintenance_event_id", uuid_type, nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.String(length=4000), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["maintenance_event_id"], ["maintenance_events.id"]),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint(
            "maintenance_event_id",
            "revision_number",
            name="uq_maintenance_event_revisions_event_number",
        ),
    )
    op.create_index(
        "ix_maintenance_event_revisions_organization_id",
        "maintenance_event_revisions",
        ["organization_id"],
    )
    op.create_index(
        "ix_maintenance_event_revisions_maintenance_event_id",
        "maintenance_event_revisions",
        ["maintenance_event_id"],
    )
    op.create_index(
        "ix_maintenance_event_revisions_organization_event",
        "maintenance_event_revisions",
        ["organization_id", "maintenance_event_id"],
    )
    op.create_index(
        "ix_maintenance_event_revisions_created_by_user_identity_id",
        "maintenance_event_revisions",
        ["created_by_user_identity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maintenance_event_revisions_created_by_user_identity_id",
        table_name="maintenance_event_revisions",
    )
    op.drop_index(
        "ix_maintenance_event_revisions_organization_event",
        table_name="maintenance_event_revisions",
    )
    op.drop_index(
        "ix_maintenance_event_revisions_maintenance_event_id",
        table_name="maintenance_event_revisions",
    )
    op.drop_index(
        "ix_maintenance_event_revisions_organization_id",
        table_name="maintenance_event_revisions",
    )
    op.drop_table("maintenance_event_revisions")

    op.drop_index(
        "ix_maintenance_events_created_by_user_identity_id",
        table_name="maintenance_events",
    )
    op.drop_index(
        "ix_maintenance_events_organization_status",
        table_name="maintenance_events",
    )
    op.drop_index(
        "ix_maintenance_events_organization_machine_time",
        table_name="maintenance_events",
    )
    op.drop_index("ix_maintenance_events_machine_id", table_name="maintenance_events")
    op.drop_index("ix_maintenance_events_organization_id", table_name="maintenance_events")
    op.drop_table("maintenance_events")

    op.drop_index(
        "ix_baseline_versions_organization_lookup", table_name="baseline_versions"
    )
    op.drop_index(
        "ix_baseline_versions_created_by_user_identity_id",
        table_name="baseline_versions",
    )
    op.drop_index("ix_baseline_versions_machine_id", table_name="baseline_versions")
    op.drop_index("ix_baseline_versions_organization_id", table_name="baseline_versions")
    op.drop_table("baseline_versions")

    op.drop_index(
        "ix_trend_points_organization_measured_at", table_name="trend_points"
    )
    op.drop_constraint(
        "uq_trend_points_source_metric", "trend_points", type_="unique"
    )
    op.drop_column("trend_points", "context_snapshot")
