"""Add the P16 biological knowledge and dose-limit library.

Revision ID: 20260908_0016
Revises: 20260908_0015
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0016"
down_revision: str | Sequence[str] | None = "20260908_0015"
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
        "biological_library_entries",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("entry_type", sa.String(length=40), nullable=False),
        sa.Column("entry_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("effective_note", sa.String(length=4000), nullable=True),
        sa.Column("disease", sa.String(length=240), nullable=True),
        sa.Column("disease_subtype", sa.String(length=240), nullable=True),
        sa.Column("anatomy_site", sa.String(length=240), nullable=True),
        sa.Column("treatment_intent", sa.String(length=160), nullable=True),
        sa.Column("technique", sa.String(length=160), nullable=True),
        sa.Column("fractions", sa.Integer(), nullable=True),
        sa.Column("tissue_or_oar", sa.String(length=240), nullable=True),
        sa.Column("metric_key", sa.String(length=80), nullable=True),
        sa.Column("operator", sa.String(length=20), nullable=True),
        sa.Column("limit_value", sa.Float(), nullable=True),
        sa.Column("lower_limit", sa.Float(), nullable=True),
        sa.Column("upper_limit", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("volume_cc", sa.Float(), nullable=True),
        sa.Column("metric_parameter", sa.Float(), nullable=True),
        sa.Column("alpha_beta_gy", sa.Float(), nullable=True),
        sa.Column("model_key", sa.String(length=120), nullable=True),
        sa.Column("model_version", sa.String(length=80), nullable=True),
        sa.Column("applicability", sa.JSON(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="USER_DEFINED"),
        sa.Column("source_reference", sa.String(length=1000), nullable=True),
        sa.Column("reference_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("source_date", sa.String(length=40), nullable=True),
        sa.Column("evidence_level", sa.String(length=120), nullable=True),
        sa.Column("citation", sa.JSON(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("source_entry_id", uuid_type, nullable=True),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["source_entry_id"], ["biological_library_entries.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
        sa.UniqueConstraint(
            "organization_id",
            "entry_type",
            "entry_key",
            "version_number",
            name="uq_biological_library_entries_family_version",
        ),
    )
    op.create_index(
        "ix_biological_library_entries_organization_id",
        "biological_library_entries",
        ["organization_id"],
    )
    op.create_index(
        "ix_biological_library_entries_organization_type_status",
        "biological_library_entries",
        ["organization_id", "entry_type", "status"],
    )
    op.create_index(
        "ix_biological_library_entries_organization_key",
        "biological_library_entries",
        ["organization_id", "entry_key"],
    )
    op.create_index(
        "ix_biological_library_entries_organization_updated",
        "biological_library_entries",
        ["organization_id", "updated_at"],
    )
    op.create_index(
        "ix_biological_library_entries_source_entry_id",
        "biological_library_entries",
        ["source_entry_id"],
    )
    op.create_index(
        "ix_biological_library_entries_created_by_user_identity_id",
        "biological_library_entries",
        ["created_by_user_identity_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_biological_library_entries_created_by_user_identity_id",
        table_name="biological_library_entries",
    )
    op.drop_index(
        "ix_biological_library_entries_source_entry_id",
        table_name="biological_library_entries",
    )
    op.drop_index(
        "ix_biological_library_entries_organization_updated",
        table_name="biological_library_entries",
    )
    op.drop_index(
        "ix_biological_library_entries_organization_key",
        table_name="biological_library_entries",
    )
    op.drop_index(
        "ix_biological_library_entries_organization_type_status",
        table_name="biological_library_entries",
    )
    op.drop_index(
        "ix_biological_library_entries_organization_id",
        table_name="biological_library_entries",
    )
    op.drop_table("biological_library_entries")
