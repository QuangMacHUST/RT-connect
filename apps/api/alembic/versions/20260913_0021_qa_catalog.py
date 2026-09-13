"""Attach QA cases to the versioned pylinac catalogue."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0021"
down_revision: str | Sequence[str] | None = "20260911_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "qa_cases",
        sa.Column("qa_definition_key", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_qa_cases_qa_definition_key", "qa_cases", ["qa_definition_key"]
    )


def downgrade() -> None:
    op.drop_index("ix_qa_cases_qa_definition_key", table_name="qa_cases")
    op.drop_column("qa_cases", "qa_definition_key")
