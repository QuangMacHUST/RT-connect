"""Request-scoped correlation and structured request outcome logging."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        header = request.app.state.settings.correlation_id_header
        correlation_id = request.headers.get(header) or str(uuid4())
        request.state.correlation_id = correlation_id
        started = perf_counter()
        logger = structlog.get_logger("http")
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request_failed",
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
            )
            raise
        response.headers[header] = correlation_id
        logger.info(
            "request_completed",
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
        return response
