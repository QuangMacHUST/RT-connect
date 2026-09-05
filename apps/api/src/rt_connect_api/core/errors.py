"""Stable HTTP error contract used by every RT-CONNECT module."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ApiError(BaseModel):
    code: str
    message: str
    correlation_id: str
    details: list[ErrorDetail] = []


class DomainError(Exception):
    def __init__(
        self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _correlation_id(request: Request) -> str:
    return str(getattr(request.state, "correlation_id", "missing-correlation-id"))


def _response(
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    payload = ApiError(
        code=code,
        message=message,
        correlation_id=_correlation_id(request),
        details=details or [],
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return _response(request, exc.code, exc.message, exc.status_code)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        ErrorDetail(field=".".join(str(part) for part in error["loc"]), message=error["msg"])
        for error in exc.errors()
    ]
    return _response(
        request, "REQUEST_VALIDATION_FAILED", "Request validation failed.", 422, details
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    message = exc.detail if isinstance(exc.detail, str) else "HTTP request failed."
    return _response(request, "HTTP_ERROR", message, exc.status_code)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Diagnostics are logged server-side; stack traces never cross the public API boundary.
    return _response(request, "INTERNAL_ERROR", "An unexpected server error occurred.", 500)
