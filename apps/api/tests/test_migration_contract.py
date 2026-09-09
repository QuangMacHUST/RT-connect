from pathlib import Path

from rt_connect_api.db.session import normalize_database_url


def test_foundation_migration_is_versioned_and_reversible() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "20260905_0001_foundation.py"
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260905_0001"' in source
    assert "def upgrade()" in source
    assert "def downgrade()" in source
    assert '"organizations"' in source
    assert '"sites"' in source
    assert '"machines"' in source


def test_database_url_normalizer_pins_postgresql_to_psycopg3() -> None:
    assert (
        normalize_database_url("postgresql://user:password@db.example/rt_connect")
        == "postgresql+psycopg://user:password@db.example/rt_connect"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:password@db.example/rt_connect")
        == "postgresql+psycopg://user:password@db.example/rt_connect"
    )
    assert normalize_database_url("sqlite:///test.db") == "sqlite:///test.db"


def test_alembic_environment_uses_database_url_normalizer() -> None:
    env = Path(__file__).parents[1] / "alembic" / "env.py"
    source = env.read_text(encoding="utf-8")

    assert "normalize_database_url(database_url)" in source


def test_gamma_reliability_migration_declares_fenced_dispatch_schema() -> None:
    migration = (
        Path(__file__).parents[1] / "alembic" / "versions" / "20260908_0008_gamma_reliability.py"
    )
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260908_0008"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260907_0007"' in source
    assert '"gamma_run_attempts"' in source
    assert '"gamma_dispatch_outbox"' in source
    assert '"lease_token"' in source
    assert '"lease_expires_at"' in source
    assert "def downgrade()" in source


def test_report_migration_declares_immutable_revision_and_export_schema() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "20260908_0009_reports.py"
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260908_0009"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260908_0008"' in source
    assert '"report_template_versions"' in source
    assert '"report_revisions"' in source
    assert '"report_block_configs"' in source
    assert '"export_jobs"' in source
    assert '"warning_snapshot"' in source
    assert "def downgrade()" in source


def test_trend_migration_declares_projection_baseline_and_event_schema() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "20260908_0010_trends.py"
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260908_0010"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260908_0009"' in source
    assert '"context_snapshot"' in source
    assert '"baseline_versions"' in source
    assert '"maintenance_events"' in source
    assert '"maintenance_event_revisions"' in source
    assert '"uq_trend_points_source_metric"' in source
    assert "def downgrade()" in source


def test_protocol_library_migration_declares_version_source_and_revision_fields() -> None:
    migration = (
        Path(__file__).parents[1] / "alembic" / "versions" / "20260908_0011_protocol_library.py"
    )
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260908_0011"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260908_0010"' in source
    assert '"applicability"' in source
    assert '"source_protocol_version_id"' in source
    assert '"revision"' in source
    assert '"reference"' in source
    assert "def downgrade()" in source


def test_biological_library_migration_declares_context_source_and_immutable_lineage() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260908_0016_biological_library.py"
    )
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260908_0016"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260908_0015"' in source
    assert '"biological_library_entries"' in source
    assert '"entry_type"' in source
    assert '"applicability"' in source
    assert '"content_sha256"' in source
    assert '"source_entry_id"' in source
    assert "def downgrade()" in source


def test_organization_invitation_migration_declares_email_bound_one_time_schema() -> None:
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260909_0018_organization_invitations.py"
    )
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260909_0018"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260908_0017"' in source
    assert '"organization_invitations"' in source
    assert '"invited_email"' in source
    assert '"token_hash"' in source
    assert '"accepted_by_user_identity_id"' in source
    assert "uq_organization_invitations_pending_email" in source
    assert "def downgrade()" in source
