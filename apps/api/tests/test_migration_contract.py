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
