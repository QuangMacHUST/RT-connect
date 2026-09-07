"""FastAPI application factory for RT-CONNECT."""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from rt_connect_api.api.artifacts import router as artifacts_router
from rt_connect_api.api.auth import router as auth_router
from rt_connect_api.api.health import router as health_router
from rt_connect_api.api.organization import router as organization_router
from rt_connect_api.api.qa_archive import router as qa_archive_router
from rt_connect_api.api.workspace import router as workspace_router
from rt_connect_api.core.config import Settings, get_settings
from rt_connect_api.core.errors import (
    DomainError,
    domain_error_handler,
    http_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)
from rt_connect_api.core.logging import configure_logging
from rt_connect_api.core.middleware import CorrelationIdMiddleware


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings.log_level)
    app = FastAPI(
        title="RT-CONNECT API",
        version=runtime_settings.app_version,
        description="Clinical QA and independent biological calculation platform API.",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs" if runtime_settings.app_env != "production" else None,
        redoc_url=None,
    )
    app.state.settings = runtime_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", runtime_settings.correlation_id_header],
        expose_headers=[runtime_settings.correlation_id_header],
    )
    app.add_middleware(CorrelationIdMiddleware)
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(workspace_router, prefix="/api/v1")
    app.include_router(organization_router, prefix="/api/v1")
    app.include_router(qa_archive_router, prefix="/api/v1")
    app.include_router(artifacts_router, prefix="/api/v1")
    return app


app = create_app()
