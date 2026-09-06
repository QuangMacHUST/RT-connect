"""P4 organization, site and machine lifecycle fields and audit events.

Revision ID: 20260906_0003
Revises: 20260906_0002
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0003"
down_revision: Union[str, Sequence[str], None] = "20260906_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "sites", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("machines", sa.Column("manufacturer", sa.String(length=200), nullable=True))
    op.add_column("machines", sa.Column("model", sa.String(length=200), nullable=True))
    op.add_column(
        "machines",
        sa.Column("status", sa.String(length=40), nullable=False, server_default="ACTIVE"),
    )
    op.add_column(
        "machines",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "audit_events",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=True),
        sa.Column("actor_user_identity_id", uuid_type, nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", uuid_type, nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["actor_user_identity_id"], ["user_identities.id"]),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index(
        "ix_audit_events_actor_user_identity_id", "audit_events", ["actor_user_identity_id"]
    )
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_user_identity_id", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_column("machines", "is_archived")
    op.drop_column("machines", "status")
    op.drop_column("machines", "model")
    op.drop_column("machines", "manufacturer")
    op.drop_column("sites", "is_archived")
    op.drop_column("organizations", "is_archived")
