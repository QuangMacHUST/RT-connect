from fastapi.testclient import TestClient


def test_session_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/session")

    assert response.status_code == 401
    assert response.json()["code"] == "HTTP_ERROR"
    assert response.json()["message"] == "AUTHENTICATION_REQUIRED"


def test_session_reports_missing_auth_configuration(client: TestClient) -> None:
    response = client.get("/api/v1/auth/session", headers={"Authorization": "Bearer placeholder"})

    assert response.status_code == 503
    assert response.json()["code"] == "HTTP_ERROR"
    assert response.json()["message"] == "AUTH_CONFIGURATION_UNAVAILABLE"
