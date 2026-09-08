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
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260908_0008_gamma_reliability.py"
    )
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260908_0008"' in source
    assert 'down_revision: str | Sequence[str] | None = "20260907_0007"' in source
    assert '"gamma_run_attempts"' in source
    assert '"gamma_dispatch_outbox"' in source
    assert '"lease_token"' in source
    assert '"lease_expires_at"' in source
    assert "def downgrade()" in source
