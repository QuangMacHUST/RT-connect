"""P6 immutable artifacts, input manifests and validation runs.

Revision ID: 20260907_0005
Revises: 20260906_0004
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260907_0005"
down_revision: str | Sequence[str] | None = "20260906_0004"
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
        "artifacts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("qa_case_id", uuid_type, nullable=True),
        sa.Column("artifact_type", sa.String(length=30), nullable=False),
        sa.Column("modality", sa.String(length=20), nullable=True),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("object_key", sa.String(length=768), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("sop_class_uid", sa.String(length=128), nullable=True),
        sa.Column("sop_instance_uid", sa.String(length=128), nullable=True),
        sa.Column("study_instance_uid", sa.String(length=128), nullable=True),
        sa.Column("series_instance_uid", sa.String(length=128), nullable=True),
        sa.Column("frame_of_reference_uid", sa.String(length=128), nullable=True),
        sa.Column("source_system", sa.String(length=200), nullable=True),
        sa.Column("uploaded_by_user_identity_id", uuid_type, nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("data_status", sa.String(length=30), nullable=False, server_default="UPLOADED"),
        sa.Column("parent_artifact_id", uuid_type, nullable=True),
        sa.Column("metadata_snapshot", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["qa_case_id"], ["qa_cases.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_user_identity_id"], ["user_identities.id"]),
        sa.ForeignKeyConstraint(["parent_artifact_id"], ["artifacts.id"]),
        sa.UniqueConstraint("object_key", name="uq_artifacts_object_key"),
    )
    op.create_index("ix_artifacts_organization_id", "artifacts", ["organization_id"])
    op.create_index("ix_artifacts_qa_case_id", "artifacts", ["qa_case_id"])
    op.create_index(
        "ix_artifacts_uploaded_by_user_identity_id", "artifacts", ["uploaded_by_user_identity_id"]
    )
    op.create_index("ix_artifacts_parent_artifact_id", "artifacts", ["parent_artifact_id"])
    op.create_index("ix_artifacts_data_status", "artifacts", ["data_status"])
    op.create_index(
        "ix_artifacts_organization_checksum", "artifacts", ["organization_id", "sha256"]
    )
    op.create_index(
        "ix_artifacts_organization_status", "artifacts", ["organization_id", "data_status"]
    )

    op.create_table(
        "input_manifests",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("analysis_run_id", uuid_type, nullable=True),
        sa.Column("artifact_id", uuid_type, nullable=False),
        sa.Column("logical_role", sa.String(length=30), nullable=False),
        sa.Column("checksum_at_use", sa.String(length=64), nullable=False),
        sa.Column("selected_metadata", sa.JSON(), nullable=False),
        sa.Column("geometry_summary", sa.JSON(), nullable=False),
        sa.Column("unit_summary", sa.JSON(), nullable=False),
        sa.Column("validation_summary", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"]),
    )
    op.create_index("ix_input_manifests_organization_id", "input_manifests", ["organization_id"])
    op.create_index("ix_input_manifests_analysis_run_id", "input_manifests", ["analysis_run_id"])
    op.create_index("ix_input_manifests_artifact_id", "input_manifests", ["artifact_id"])
    op.create_index(
        "ix_input_manifests_organization_artifact",
        "input_manifests",
        ["organization_id", "artifact_id"],
    )

    op.create_table(
        "validation_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", uuid_type, nullable=False),
        sa.Column("validation_type", sa.String(length=60), nullable=False),
        sa.Column("validator_version", sa.String(length=80), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("input_manifest_snapshot", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_index("ix_validation_runs_organization_id", "validation_runs", ["organization_id"])
    op.create_index("ix_validation_runs_subject_id", "validation_runs", ["subject_id"])
    op.create_index(
        "ix_validation_runs_organization_subject",
        "validation_runs",
        ["organization_id", "subject_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_validation_runs_organization_subject", table_name="validation_runs")
    op.drop_index("ix_validation_runs_subject_id", table_name="validation_runs")
    op.drop_index("ix_validation_runs_organization_id", table_name="validation_runs")
    op.drop_table("validation_runs")
    op.drop_index("ix_input_manifests_organization_artifact", table_name="input_manifests")
    op.drop_index("ix_input_manifests_artifact_id", table_name="input_manifests")
    op.drop_index("ix_input_manifests_analysis_run_id", table_name="input_manifests")
    op.drop_index("ix_input_manifests_organization_id", table_name="input_manifests")
    op.drop_table("input_manifests")
    op.drop_index("ix_artifacts_organization_status", table_name="artifacts")
    op.drop_index("ix_artifacts_organization_checksum", table_name="artifacts")
    op.drop_index("ix_artifacts_data_status", table_name="artifacts")
    op.drop_index("ix_artifacts_parent_artifact_id", table_name="artifacts")
    op.drop_index("ix_artifacts_uploaded_by_user_identity_id", table_name="artifacts")
    op.drop_index("ix_artifacts_qa_case_id", table_name="artifacts")
    op.drop_index("ix_artifacts_organization_id", table_name="artifacts")
    op.drop_table("artifacts")
