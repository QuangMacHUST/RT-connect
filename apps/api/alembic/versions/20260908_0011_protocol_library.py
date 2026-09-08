"""Add P11 protocol library metadata and draft revision controls.

Revision ID: 20260908_0011
Revises: 20260908_0010
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260908_0011"
down_revision: str | Sequence[str] | None = "20260908_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "qa_protocol_versions",
        sa.Column("description", sa.String(length=4000), nullable=True),
    )
    op.add_column(
        "qa_protocol_versions",
        sa.Column(
            "applicability",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "qa_protocol_versions",
        sa.Column(
            "source_type",
            sa.String(length=40),
            nullable=False,
            server_default="USER_DEFINED",
        ),
    )
    op.add_column(
        "qa_protocol_versions",
        sa.Column("source_reference", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "qa_protocol_versions",
        sa.Column(
            "source_protocol_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "qa_protocol_versions",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_qa_protocol_versions_source_protocol_version_id",
        "qa_protocol_versions",
        ["source_protocol_version_id"],
    )
    op.create_foreign_key(
        "fk_qa_protocol_versions_source_protocol_version",
        "qa_protocol_versions",
        "qa_protocol_versions",
        ["source_protocol_version_id"],
        ["id"],
    )
    op.add_column(
        "qa_protocol_rules",
        sa.Column("reference", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("qa_protocol_rules", "reference")
    op.drop_constraint(
        "fk_qa_protocol_versions_source_protocol_version",
        "qa_protocol_versions",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_qa_protocol_versions_source_protocol_version_id",
        table_name="qa_protocol_versions",
    )
    op.drop_column("qa_protocol_versions", "revision")
    op.drop_column("qa_protocol_versions", "source_protocol_version_id")
    op.drop_column("qa_protocol_versions", "source_reference")
    op.drop_column("qa_protocol_versions", "source_type")
    op.drop_column("qa_protocol_versions", "applicability")
    op.drop_column("qa_protocol_versions", "description")
