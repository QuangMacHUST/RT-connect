"""Unauthenticated operational endpoints; no secrets or topology details are returned."""

from datetime import UTC, datetime

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from rt_connect_api.db.session import database_ready

router = APIRouter(tags=["system"])


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    correlation_id: str
    schema_revision: str | None = None


class VersionResponse(BaseModel):
    application: str
    version: str
    environment: str
    engine_version: str
    renderer_version: str
    schema_revision: str


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(UTC),
        correlation_id=str(request.state.correlation_id),
    )


@router.get("/ready", response_model=HealthResponse)
def readiness(request: Request) -> HealthResponse | JSONResponse:
    is_ready, reason = database_ready(request.app.state.settings)
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": datetime.now(UTC).isoformat(),
                "correlation_id": str(request.state.correlation_id),
                "reason": reason,
            },
        )
    return HealthResponse(
        status="ready",
        timestamp=datetime.now(UTC),
        correlation_id=str(request.state.correlation_id),
        schema_revision=request.app.state.settings.schema_revision,
    )


@router.get("/version", response_model=VersionResponse)
def version(request: Request) -> VersionResponse:
    settings = request.app.state.settings
    return VersionResponse(
        application="rt-connect-api",
        version=settings.app_version,
        environment=settings.app_env,
        engine_version=settings.engine_version,
        renderer_version=settings.renderer_version,
        schema_revision=settings.schema_revision,
    )
