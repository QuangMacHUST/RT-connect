"""Add organization invitation lifecycle records.

Revision ID: 20260909_0018
Revises: 20260908_0017
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260909_0018"
down_revision: str | Sequence[str] | None = "20260908_0017"
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
        "organization_invitations",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("invited_email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
        sa.Column("accepted_by_user_identity_id", uuid_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["created_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_user_identity_id"], ["user_identities.id"]
        ),
        sa.UniqueConstraint("token_hash", name="uq_organization_invitations_token_hash"),
    )
    op.create_index(
        "uq_organization_invitations_pending_email",
        "organization_invitations",
        ["organization_id", "invited_email"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
        sqlite_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "ix_organization_invitations_organization_id",
        "organization_invitations",
        ["organization_id"],
    )
    op.create_index(
        "ix_organization_invitations_created_by_user_identity_id",
        "organization_invitations",
        ["created_by_user_identity_id"],
    )
    op.create_index(
        "ix_organization_invitations_accepted_by_user_identity_id",
        "organization_invitations",
        ["accepted_by_user_identity_id"],
    )
    op.create_index(
        "ix_organization_invitations_lookup",
        "organization_invitations",
        ["organization_id", "invited_email", "status"],
    )
    op.create_index(
        "ix_organization_invitations_expires",
        "organization_invitations",
        ["organization_id", "expires_at", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_organization_invitations_expires", table_name="organization_invitations")
    op.drop_index("ix_organization_invitations_lookup", table_name="organization_invitations")
    op.drop_index(
        "ix_organization_invitations_accepted_by_user_identity_id",
        table_name="organization_invitations",
    )
    op.drop_index(
        "ix_organization_invitations_created_by_user_identity_id",
        table_name="organization_invitations",
    )
    op.drop_index("ix_organization_invitations_organization_id", table_name="organization_invitations")
    op.drop_index(
        "uq_organization_invitations_pending_email", table_name="organization_invitations"
    )
    op.drop_table("organization_invitations")
