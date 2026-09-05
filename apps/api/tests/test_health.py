import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from rt_connect_api.core.config import Settings
from rt_connect_api.db import session


def test_comma_separated_cors_origins_are_supported() -> None:
    settings = Settings(cors_allowed_origins="http://localhost:5173, https://staging.example.test")

    assert settings.cors_allowed_origins == ["http://localhost:5173", "https://staging.example.test"]


def test_plain_postgres_urls_are_normalized_for_psycopg_v3() -> None:
    settings = Settings(database_url="postgresql://user:password@postgres.internal:5432/rt_connect")

    assert settings.database_url == "postgresql+psycopg://user:password@postgres.internal:5432/rt_connect"


def test_health_returns_correlation_id(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "p1-health-test"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["correlation_id"] == "p1-health-test"
    assert response.headers["X-Correlation-ID"] == "p1-health-test"


def test_readiness_is_not_ready_without_database(client: TestClient) -> None:
    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["reason"] == "DATABASE_URL is not configured"


def test_database_readiness_handles_engine_initialization_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_engine_error() -> None:
        raise RuntimeError("database driver initialization failed")

    monkeypatch.setattr(session, "get_engine", raise_engine_error)

    assert session.database_ready() == (False, "Database connection failed")


def test_database_readiness_requires_an_applied_migration(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite://")
    monkeypatch.setattr(session, "get_engine", lambda: engine)

    try:
        assert session.database_ready() == (False, "Database migration is not applied")

        with engine.begin() as connection:
            connection.execute(
                text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
            )
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES ('20260905_0001')")
            )

        assert session.database_ready() == (True, None)
    finally:
        engine.dispose()


def test_version_exposes_release_metadata_without_secrets(client: TestClient) -> None:
    response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {
        "application": "rt-connect-api",
        "version": "test-version",
        "environment": "test",
        "engine_version": "unavailable-in-p1",
        "renderer_version": "unavailable-in-p1",
    }
