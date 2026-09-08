"""Add immutable report revisions, block configs and export jobs.

Revision ID: 20260908_0009
Revises: 20260908_0008
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0009"
down_revision: str | Sequence[str] | None = "20260908_0008"
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
        "report_template_versions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("template_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("blocks_snapshot", sa.JSON(), nullable=False),
        sa.Column("render_options", sa.JSON(), nullable=False),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint(
            "organization_id",
            "template_key",
            "version_number",
            name="uq_report_template_versions_key_version",
        ),
    )
    op.create_index(
        "ix_report_template_versions_organization_id",
        "report_template_versions",
        ["organization_id"],
    )
    op.create_index(
        "ix_report_template_versions_organization_status",
        "report_template_versions",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_report_template_versions_created_by_user_identity_id",
        "report_template_versions",
        ["created_by_user_identity_id"],
    )

    op.create_table(
        "report_revisions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("report_key", uuid_type, nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", uuid_type, nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("template_version_id", uuid_type, nullable=True),
        sa.Column("source_snapshot", sa.JSON(), nullable=False),
        sa.Column("render_options", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="SAVED"),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["template_version_id"], ["report_template_versions.id"]
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"], ["report_revisions.id"]
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint(
            "organization_id",
            "report_key",
            "revision_number",
            name="uq_report_revisions_key_number",
        ),
    )
    op.create_index(
        "ix_report_revisions_organization_id", "report_revisions", ["organization_id"]
    )
    op.create_index(
        "ix_report_revisions_report_key", "report_revisions", ["report_key"]
    )
    op.create_index(
        "ix_report_revisions_template_version_id",
        "report_revisions",
        ["template_version_id"],
    )
    op.create_index(
        "ix_report_revisions_supersedes_revision_id",
        "report_revisions",
        ["supersedes_revision_id"],
    )
    op.create_index(
        "ix_report_revisions_created_by_user_identity_id",
        "report_revisions",
        ["created_by_user_identity_id"],
    )
    op.create_index(
        "ix_report_revisions_organization_source",
        "report_revisions",
        ["organization_id", "source_type", "source_id"],
    )
    op.create_index(
        "ix_report_revisions_organization_created",
        "report_revisions",
        ["organization_id", "created_at"],
    )

    op.create_table(
        "report_block_configs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("report_revision_id", uuid_type, nullable=False),
        sa.Column("stable_block_id", sa.String(length=120), nullable=False),
        sa.Column("block_type", sa.String(length=60), nullable=False),
        sa.Column("label", sa.String(length=240), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("source_binding", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["report_revision_id"], ["report_revisions.id"]),
        sa.UniqueConstraint(
            "report_revision_id",
            "stable_block_id",
            name="uq_report_block_configs_revision_block",
        ),
    )
    op.create_index(
        "ix_report_block_configs_organization_id",
        "report_block_configs",
        ["organization_id"],
    )
    op.create_index(
        "ix_report_block_configs_report_revision_id",
        "report_block_configs",
        ["report_revision_id"],
    )
    op.create_index(
        "ix_report_block_configs_revision_order",
        "report_block_configs",
        ["report_revision_id", "sort_order"],
    )

    op.create_table(
        "export_jobs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("report_revision_id", uuid_type, nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("export_format", sa.String(length=20), nullable=False),
        sa.Column("render_options", sa.JSON(), nullable=False),
        sa.Column("renderer_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="QUEUED"),
        sa.Column("object_key", sa.String(length=768), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("media_type", sa.String(length=255), nullable=True),
        sa.Column("error_snapshot", sa.JSON(), nullable=False),
        sa.Column("warning_snapshot", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["report_revision_id"], ["report_revisions.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_export_jobs_organization_idempotency",
        ),
        sa.UniqueConstraint("object_key", name="uq_export_jobs_object_key"),
    )
    op.create_index(
        "ix_export_jobs_organization_id", "export_jobs", ["organization_id"]
    )
    op.create_index(
        "ix_export_jobs_report_revision_id", "export_jobs", ["report_revision_id"]
    )
    op.create_index(
        "ix_export_jobs_organization_revision",
        "export_jobs",
        ["organization_id", "report_revision_id"],
    )
    op.create_index(
        "ix_export_jobs_organization_status",
        "export_jobs",
        ["organization_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_export_jobs_organization_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_organization_revision", table_name="export_jobs")
    op.drop_index("ix_export_jobs_report_revision_id", table_name="export_jobs")
    op.drop_index("ix_export_jobs_organization_id", table_name="export_jobs")
    op.drop_table("export_jobs")

    op.drop_index(
        "ix_report_block_configs_revision_order", table_name="report_block_configs"
    )
    op.drop_index(
        "ix_report_block_configs_report_revision_id", table_name="report_block_configs"
    )
    op.drop_index(
        "ix_report_block_configs_organization_id", table_name="report_block_configs"
    )
    op.drop_table("report_block_configs")

    op.drop_index(
        "ix_report_revisions_organization_created", table_name="report_revisions"
    )
    op.drop_index(
        "ix_report_revisions_organization_source", table_name="report_revisions"
    )
    op.drop_index(
        "ix_report_revisions_created_by_user_identity_id", table_name="report_revisions"
    )
    op.drop_index(
        "ix_report_revisions_supersedes_revision_id", table_name="report_revisions"
    )
    op.drop_index(
        "ix_report_revisions_template_version_id", table_name="report_revisions"
    )
    op.drop_index("ix_report_revisions_report_key", table_name="report_revisions")
    op.drop_index("ix_report_revisions_organization_id", table_name="report_revisions")
    op.drop_table("report_revisions")

    op.drop_index(
        "ix_report_template_versions_created_by_user_identity_id",
        table_name="report_template_versions",
    )
    op.drop_index(
        "ix_report_template_versions_organization_status",
        table_name="report_template_versions",
    )
    op.drop_index(
        "ix_report_template_versions_organization_id",
        table_name="report_template_versions",
    )
    op.drop_table("report_template_versions")
