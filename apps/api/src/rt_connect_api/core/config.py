"""Environment configuration with deliberately explicit production boundaries."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment; secrets never have defaults."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_version: str = "0.1.0-dev"
    schema_revision: str = "20260908_0011"
    log_level: str = "INFO"
    database_url: str | None = None
    redis_url: str | None = None
    gamma_queue_stream: str = "rt-connect:gamma"
    gamma_queue_group: str = "rt-connect-gamma"
    gamma_queue_visibility_timeout_seconds: int = Field(default=120, ge=30)
    gamma_queue_maxlen: int = Field(default=10_000, ge=100)
    gamma_lease_seconds: int = Field(default=120, ge=30, le=3600)
    gamma_retry_max_attempts: int = Field(default=3, ge=1, le=10)
    gamma_retry_backoff_base_seconds: int = Field(default=5, ge=0, le=3600)
    gamma_retry_backoff_max_seconds: int = Field(default=300, ge=0, le=86_400)
    gamma_execution_deadline_seconds: int = Field(default=900, ge=60, le=86_400)
    gamma_max_voxels: int = Field(default=2_000_000, ge=1_024, le=100_000_000)
    gamma_max_candidate_evaluations: int = Field(default=50_000_000, ge=10_000)
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"]
    )
    correlation_id_header: str = "X-Correlation-ID"
    request_timeout_seconds: int = 30
    max_upload_bytes: int = 104_857_600
    s3_endpoint: str | None = None
    s3_region: str = "us-east-1"
    s3_bucket: str = "rt-connect-artifacts"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_signed_url_ttl_seconds: int = 900
    engine_version: str = "unavailable-in-p1"
    renderer_version: str = "unavailable-in-p1"
    supabase_jwt_issuer: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: str | None = None

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def resolved_supabase_jwks_url(self) -> str | None:
        """Return the explicitly configured JWKS endpoint or the Supabase default."""
        if self.supabase_jwks_url:
            return self.supabase_jwks_url
        if self.supabase_jwt_issuer:
            return f"{self.supabase_jwt_issuer.rstrip('/')}/.well-known/jwks.json"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
