"""Dependency ports. Concrete Railway/Supabase adapters arrive in later phases."""

from __future__ import annotations

from typing import Protocol


class ObjectStoragePort(Protocol):
    def put(self, object_key: str, content: bytes, checksum_sha256: str) -> None: ...

    def get(self, object_key: str) -> bytes: ...


class QueuePort(Protocol):
    def enqueue(self, job_type: str, payload: dict[str, object], idempotency_key: str) -> str: ...


class AuthVerifierPort(Protocol):
    def verify_access_token(self, token: str) -> dict[str, object]: ...


class AnalysisEnginePort(Protocol):
    engine_version: str

    def run(
        self, input_manifest_id: str, configuration: dict[str, object]
    ) -> dict[str, object]: ...
