from fastapi.testclient import TestClient

from rt_connect_api.core.config import Settings


def test_comma_separated_cors_origins_are_supported() -> None:
    settings = Settings(cors_allowed_origins="http://localhost:5173, https://staging.example.test")

    assert settings.cors_allowed_origins == ["http://localhost:5173", "https://staging.example.test"]


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
