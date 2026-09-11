"""Add optimistic revisions to organization hierarchy entities.

Revision ID: 20260911_0020
Revises: 20260909_0019
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0020"
down_revision: str | Sequence[str] | None = "20260909_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("organizations", "sites", "machines"):
        op.add_column(
            table_name,
            sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    for table_name in ("machines", "sites", "organizations"):
        op.drop_column(table_name, "revision")
