from pathlib import Path


def test_foundation_migration_is_versioned_and_reversible() -> None:
    migration = Path(__file__).parents[1] / "alembic" / "versions" / "20260905_0001_foundation.py"
    source = migration.read_text(encoding="utf-8")

    assert 'revision: str = "20260905_0001"' in source
    assert "def upgrade()" in source
    assert "def downgrade()" in source
    assert '"organizations"' in source
    assert '"sites"' in source
    assert '"machines"' in source
