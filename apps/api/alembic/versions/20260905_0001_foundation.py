"""P1 foundation: organization, site and machine seed boundaries.

Revision ID: 20260905_0001
Revises:
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260905_0001"
down_revision: Union[str, Sequence[str], None] = None
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
        "organizations",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
    )
    op.create_table(
        "sites",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_index("ix_sites_organization_id", "sites", ["organization_id"])
    op.create_table(
        "machines",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("site_id", uuid_type, nullable=False),
        sa.Column("stable_machine_id", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.UniqueConstraint("stable_machine_id", name="uq_machines_stable_machine_id"),
    )
    op.create_index("ix_machines_organization_id", "machines", ["organization_id"])
    op.create_index("ix_machines_site_id", "machines", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_machines_site_id", table_name="machines")
    op.drop_index("ix_machines_organization_id", table_name="machines")
    op.drop_table("machines")
    op.drop_index("ix_sites_organization_id", table_name="sites")
    op.drop_table("sites")
    op.drop_table("organizations")
