"""Database lifecycle; a database URL is always injected by environment."""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from rt_connect_api.core.config import Settings, get_settings


def normalize_database_url(database_url: str) -> str:
    """Use the application's pinned psycopg 3 driver for PostgreSQL URLs.

    Railway reference variables commonly use ``postgresql://`` while some
    environments explicitly use SQLAlchemy's ``postgresql+psycopg://`` form.
    SQLAlchemy interprets the former as its legacy default driver, which makes
    a deployment depend on whichever optional adapter happened to be present.
    RT-CONNECT pins psycopg 3, so normalise only the plain PostgreSQL scheme.
    Other URL schemes (including SQLite used by focused tests) are untouched.
    """

    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


@lru_cache
def get_engine() -> Engine | None:
    database_url = get_settings().database_url
    if database_url is None:
        return None
    return create_engine(normalize_database_url(database_url), pool_pre_ping=True)


def get_session() -> Generator[Session]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session


def database_ready(settings: Settings | None = None) -> tuple[bool, str | None]:
    # Health/readiness must inspect the settings attached to the current app.
    # Falling back to the process-wide cached settings is appropriate for the
    # normal server entrypoint, but would make app-factory tests (and any
    # embedded deployment) probe a different database than the app uses.
    engine = get_engine() if settings is None else _engine_for_settings(settings)
    if engine is None:
        return False, "DATABASE_URL is not configured"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return False, "Database connection failed"
    return True, None


def _engine_for_settings(settings: Settings) -> Engine | None:
    if settings.database_url is None:
        return None
    return create_engine(normalize_database_url(settings.database_url), pool_pre_ping=True)
