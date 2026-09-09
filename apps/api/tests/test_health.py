from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from rt_connect_api.core.config import Settings
from rt_connect_api.db.session import database_ready, normalize_database_url
from rt_connect_api.main import create_app


def test_comma_separated_cors_origins_are_supported() -> None:
    settings = Settings(cors_allowed_origins="http://localhost:5173, https://staging.example.test")

    assert settings.cors_allowed_origins == [
        "http://localhost:5173",
        "https://staging.example.test",
    ]


def test_plain_postgresql_url_uses_the_pinned_psycopg_driver() -> None:
    plain_url = "postgresql://postgres:example@postgres.internal:5432/railway"
    psycopg_url = "postgresql+psycopg://postgres:example@postgres.internal:5432/railway"

    assert normalize_database_url(plain_url) == psycopg_url
    assert normalize_database_url(psycopg_url) == psycopg_url
    assert normalize_database_url("sqlite+pysqlite:///:memory:") == "sqlite+pysqlite:///:memory:"


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


def test_database_readiness_requires_the_expected_alembic_revision(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'readiness.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('20260909_0018')")
        )
    engine.dispose()

    assert database_ready(Settings(database_url=database_url))[0] is True


def test_database_readiness_rejects_a_schema_revision_mismatch(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'readiness-mismatch.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('20260907_0007')")
        )
    engine.dispose()

    ready, reason = database_ready(Settings(database_url=database_url))

    assert ready is False
    assert reason == ("Database schema revision is 20260907_0007; expected 20260909_0018")


def test_version_exposes_release_metadata_without_secrets(client: TestClient) -> None:
    response = client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json() == {
        "application": "rt-connect-api",
        "version": "test-version",
        "environment": "test",
        "engine_version": "unavailable-in-p1",
        "renderer_version": "unavailable-in-p1",
        "schema_revision": "20260909_0018",
    }


def test_version_prefers_railway_commit_sha_when_available() -> None:
    settings = Settings(
        app_env="staging",
        app_version="stale-configured-label",
        railway_git_commit_sha="39a079c1234567890abcdef1234567890abcdef1",
        database_url=None,
        redis_url=None,
    )

    with TestClient(create_app(settings)) as test_client:
        response = test_client.get("/api/v1/version")

    assert response.status_code == 200
    assert response.json()["version"] == "39a079c1234567890abcdef1234567890abcdef1"
