"""P5 QA archive folders and QA cases.

Revision ID: 20260906_0004
Revises: 20260906_0003
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260906_0004"
down_revision: Union[str, Sequence[str], None] = "20260906_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    op.create_table(
        "folders",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("parent_folder_id", uuid_type, nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
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
        sa.ForeignKeyConstraint(["parent_folder_id"], ["folders.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
    )
    op.create_index("ix_folders_organization_id", "folders", ["organization_id"])
    op.create_index("ix_folders_parent_folder_id", "folders", ["parent_folder_id"])
    op.create_index(
        "ix_folders_created_by_user_identity_id", "folders", ["created_by_user_identity_id"]
    )

    op.create_table(
        "qa_cases",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("site_id", uuid_type, nullable=False),
        sa.Column("machine_id", uuid_type, nullable=False),
        sa.Column("primary_folder_id", uuid_type, nullable=False),
        sa.Column("qa_type", sa.String(length=100), nullable=False),
        sa.Column("qa_cycle", sa.String(length=40), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("protocol_version_id", uuid_type, nullable=True),
        sa.Column("status_note", sa.String(length=4000), nullable=True),
        sa.Column("case_status", sa.String(length=40), nullable=False, server_default="OPEN"),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_identity_id", uuid_type, nullable=True),
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
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"]),
        sa.ForeignKeyConstraint(["primary_folder_id"], ["folders.id"]),
        sa.ForeignKeyConstraint(["created_by_user_identity_id"], ["user_identities.id"]),
    )
    op.create_index("ix_qa_cases_organization_id", "qa_cases", ["organization_id"])
    op.create_index("ix_qa_cases_site_id", "qa_cases", ["site_id"])
    op.create_index("ix_qa_cases_machine_id", "qa_cases", ["machine_id"])
    op.create_index("ix_qa_cases_primary_folder_id", "qa_cases", ["primary_folder_id"])
    op.create_index("ix_qa_cases_performed_at", "qa_cases", ["performed_at"])
    op.create_index("ix_qa_cases_qa_type", "qa_cases", ["qa_type"])
    op.create_index("ix_qa_cases_qa_cycle", "qa_cases", ["qa_cycle"])


def downgrade() -> None:
    op.drop_index("ix_qa_cases_qa_cycle", table_name="qa_cases")
    op.drop_index("ix_qa_cases_qa_type", table_name="qa_cases")
    op.drop_index("ix_qa_cases_performed_at", table_name="qa_cases")
    op.drop_index("ix_qa_cases_primary_folder_id", table_name="qa_cases")
    op.drop_index("ix_qa_cases_machine_id", table_name="qa_cases")
    op.drop_index("ix_qa_cases_site_id", table_name="qa_cases")
    op.drop_index("ix_qa_cases_organization_id", table_name="qa_cases")
    op.drop_table("qa_cases")
    op.drop_index("ix_folders_created_by_user_identity_id", table_name="folders")
    op.drop_index("ix_folders_parent_folder_id", table_name="folders")
    op.drop_index("ix_folders_organization_id", table_name="folders")
    op.drop_table("folders")
