"""Verify Supabase access tokens without accepting a browser-supplied organization context."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError

from rt_connect_api.core.config import Settings

_bearer = HTTPBearer(auto_error=False)
_allowed_algorithms = ["RS256", "ES256", "EdDSA"]


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> SigningKey: ...


class SigningKey(Protocol):
    key: Any


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    """Retain the JWKS cache across requests while allowing normal key rotation."""
    return PyJWKClient(jwks_url)


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Identity claims accepted from a verified Supabase access token."""

    subject: str
    email: str | None
    claims: Mapping[str, object]


class SupabaseTokenVerifier:
    def __init__(self, settings: Settings, jwks_client: SigningKeyClient | None = None) -> None:
        self._issuer = settings.supabase_jwt_issuer
        self._audience = settings.supabase_jwt_audience
        self._jwks_url = settings.resolved_supabase_jwks_url
        self._client = jwks_client

    @property
    def configured(self) -> bool:
        return bool(self._issuer and self._jwks_url and self._audience)

    def verify(self, access_token: str) -> AuthenticatedIdentity:
        if not self._issuer or not self._jwks_url or not self._audience:
            raise RuntimeError("Supabase JWT verification is not configured")
        try:
            client = self._client or _jwks_client(self._jwks_url)
            signing_key = client.get_signing_key_from_jwt(access_token)
            claims = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=_allowed_algorithms,
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except (InvalidTokenError, PyJWKClientError, AttributeError) as exc:
            raise ValueError("Supabase access token is invalid") from exc

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise ValueError("Supabase access token has no subject")
        if claims.get("role") != "authenticated":
            raise ValueError("Supabase access token has an unsupported role")
        email = claims.get("email")
        return AuthenticatedIdentity(
            subject=subject,
            email=email if isinstance(email, str) else None,
            claims=claims,
        )


def require_identity(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
) -> AuthenticatedIdentity:
    """FastAPI dependency used by protected routes from P2 onward."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_REQUIRED")

    verifier = SupabaseTokenVerifier(request.app.state.settings)
    if not verifier.configured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "AUTH_CONFIGURATION_UNAVAILABLE")
    try:
        return verifier.verify(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "INVALID_ACCESS_TOKEN") from exc
