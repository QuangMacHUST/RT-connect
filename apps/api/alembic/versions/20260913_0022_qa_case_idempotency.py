"""Make repeated QA case creation safe across retries."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0022"
down_revision: str | Sequence[str] | None = "20260913_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("qa_cases", sa.Column("idempotency_key", sa.String(length=200), nullable=True))
    op.add_column(
        "qa_cases", sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True)
    )
    op.create_index(
        "ix_qa_cases_organization_idempotency",
        "qa_cases",
        ["organization_id", "idempotency_key"],
    )
    op.create_unique_constraint(
        "uq_qa_cases_organization_idempotency",
        "qa_cases",
        ["organization_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_qa_cases_organization_idempotency", "qa_cases", type_="unique")
    op.drop_index("ix_qa_cases_organization_idempotency", table_name="qa_cases")
    op.drop_column("qa_cases", "idempotency_fingerprint")
    op.drop_column("qa_cases", "idempotency_key")
