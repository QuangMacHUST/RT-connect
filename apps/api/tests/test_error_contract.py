from fastapi import APIRouter
from fastapi.testclient import TestClient

from rt_connect_api.core.errors import DomainError
from rt_connect_api.main import create_app


def test_validation_error_uses_shared_error_contract() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/test/{value}")
    def typed_endpoint(value: int) -> dict[str, int]:
        return {"value": value}

    app.include_router(router)
    response = TestClient(app).get(
        "/test/not-an-integer", headers={"X-Correlation-ID": "contract-id"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_FAILED"
    assert response.json()["correlation_id"] == "contract-id"


def test_domain_error_never_exposes_internal_exception() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/test/domain-error")
    def domain_error() -> None:
        raise DomainError("ARTIFACT_NOT_FOUND", "Artifact does not exist.", 404)

    app.include_router(router)
    response = TestClient(app).get("/test/domain-error")

    assert response.status_code == 404
    assert response.json()["code"] == "ARTIFACT_NOT_FOUND"
