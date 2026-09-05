"""Database lifecycle; a database URL is always injected by environment."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from rt_connect_api.core.config import get_settings


@lru_cache
def get_engine() -> Engine | None:
    database_url = get_settings().database_url
    if database_url is None:
        return None
    return create_engine(database_url, pool_pre_ping=True)


def get_session() -> Generator[Session]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session


def database_ready() -> tuple[bool, str | None]:
    try:
        engine = get_engine()
        if engine is None:
            return False, "DATABASE_URL is not configured"
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if not inspect(engine).has_table("alembic_version"):
                return False, "Database migration is not applied"
            schema_revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
    except Exception:
        return False, "Database connection failed"
    if schema_revision is None:
        return False, "Database migration is not applied"
    return True, None
