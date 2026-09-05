from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from rt_connect_api.core.config import Settings
from rt_connect_api.security.supabase_jwt import SupabaseTokenVerifier


class StaticSigningKeyClient:
    def __init__(self, public_key: rsa.RSAPublicKey) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        return SimpleNamespace(key=self._public_key)


def _settings() -> Settings:
    return Settings(
        supabase_jwt_issuer="https://auth.example.test",
        supabase_jwt_audience="authenticated",
        supabase_jwks_url="https://auth.example.test/.well-known/jwks.json",
    )


def _token(private_key: rsa.RSAPrivateKey, **overrides: object) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": "a0b4aa75-50ed-4cef-8979-b12ee61c62d6",
        "email": "synthetic.user@example.test",
        "role": "authenticated",
        "iss": "https://auth.example.test",
        "aud": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def _verifier(private_key: rsa.RSAPrivateKey) -> SupabaseTokenVerifier:
    return SupabaseTokenVerifier(_settings(), StaticSigningKeyClient(private_key.public_key()))


def test_verifies_valid_asymmetric_supabase_access_token() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    identity = _verifier(private_key).verify(_token(private_key))

    assert identity.subject == "a0b4aa75-50ed-4cef-8979-b12ee61c62d6"
    assert identity.email == "synthetic.user@example.test"


@pytest.mark.parametrize(
    ("claim", "value"),
    [
        ("exp", datetime.now(UTC) - timedelta(seconds=1)),
        ("iss", "https://other.example.test"),
        ("aud", "other-audience"),
        ("role", "service_role"),
    ],
)
def test_rejects_invalid_claims(claim: str, value: object) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(ValueError, match="Supabase access token"):
        _verifier(private_key).verify(_token(private_key, **{claim: value}))


def test_rejects_token_signed_by_another_key() -> None:
    expected_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(ValueError, match="Supabase access token"):
        _verifier(expected_private_key).verify(_token(other_private_key))


def test_rejects_jwks_client_failure() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FailingSigningKeyClient:
        def get_signing_key_from_jwt(self, token: str) -> object:
            raise jwt.PyJWKClientError("synthetic JWKS failure")

    with pytest.raises(ValueError, match="Supabase access token"):
        SupabaseTokenVerifier(_settings(), FailingSigningKeyClient()).verify(_token(private_key))
