"""P3 identity projection and organization membership.

Revision ID: 20260906_0002
Revises: 20260905_0001
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0002"
down_revision: Union[str, Sequence[str], None] = "20260905_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    ]


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "user_identities",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("supabase_user_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.UniqueConstraint("supabase_user_id", name="uq_user_identities_supabase_user_id"),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("user_identity_id", uuid_type, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_identity_id"], ["user_identities.id"]),
        sa.UniqueConstraint(
            "organization_id", "user_identity_id", name="uq_organization_memberships_identity"
        ),
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_memberships_user_identity_id",
        "organization_memberships",
        ["user_identity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_organization_memberships_user_identity_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_organization_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")
    op.drop_table("user_identities")
