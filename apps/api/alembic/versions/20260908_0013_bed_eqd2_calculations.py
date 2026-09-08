"""Add idempotency identity for executable biological calculations.

Revision ID: 20260908_0013
Revises: 20260908_0012
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_0013"
down_revision: str | Sequence[str] | None = "20260908_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "biological_calculation_runs",
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
    )
    op.create_index(
        "ix_biological_calculation_runs_organization_idempotency",
        "biological_calculation_runs",
        ["organization_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_biological_calculation_runs_organization_idempotency",
        table_name="biological_calculation_runs",
    )
    op.drop_column("biological_calculation_runs", "idempotency_key")
