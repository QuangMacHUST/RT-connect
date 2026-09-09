"""S3-compatible artifact storage ports and the local MinIO implementation."""

from __future__ import annotations

import shutil
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO, Protocol
from urllib.parse import urlparse

from minio import Minio

from rt_connect_api.core.config import Settings


class ObjectStorageError(RuntimeError):
    """Raised when durable artifact storage is not configured or unavailable."""


class ObjectStorage(Protocol):
    def ensure_bucket(self) -> None: ...

    def put_object(
        self,
        key: str,
        source: BinaryIO,
        length: int,
        content_type: str,
    ) -> None: ...

    def delete_object(self, key: str) -> None: ...

    def download_to_path(self, key: str, destination: Path) -> None: ...

    def presigned_get(self, key: str, expires_seconds: int) -> str: ...


class MinioObjectStorage:
    def __init__(self, settings: Settings) -> None:
        if not settings.s3_endpoint:
            raise ObjectStorageError("S3_ENDPOINT is not configured")
        if not settings.s3_access_key_id or not settings.s3_secret_access_key:
            raise ObjectStorageError("S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY are required")
        parsed = urlparse(settings.s3_endpoint)
        if not parsed.hostname:
            raise ObjectStorageError("S3_ENDPOINT must contain a hostname")
        endpoint = parsed.hostname
        if parsed.port:
            endpoint = f"{endpoint}:{parsed.port}"
        self.bucket = settings.s3_bucket
        self.region = settings.s3_region
        self.client = Minio(
            endpoint,
            access_key=settings.s3_access_key_id,
            secret_key=settings.s3_secret_access_key,
            secure=parsed.scheme == "https",
            region=settings.s3_region,
        )

    def ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket, location=self.region)
        except Exception as exc:  # MinIO exposes several transport exception types.
            raise ObjectStorageError("Could not prepare the configured artifact bucket") from exc

    def put_object(self, key: str, source: BinaryIO, length: int, content_type: str) -> None:
        try:
            self.client.put_object(
                self.bucket,
                key,
                source,
                length,
                content_type=content_type,
            )
        except Exception as exc:
            raise ObjectStorageError("Could not persist the uploaded artifact") from exc

    def delete_object(self, key: str) -> None:
        """Remove an object that has no committed database reference.

        Upload persistence is deliberately a two-resource operation: the
        object is written before the artifact/manifest transaction commits.
        Callers use this method only for compensation after that transaction
        fails.  A failure is surfaced instead of being silently ignored so an
        operator can reconcile a possible orphan object.
        """

        try:
            self.client.remove_object(self.bucket, key)
        except Exception as exc:
            raise ObjectStorageError("Could not remove the unreferenced artifact object") from exc

    def download_to_path(self, key: str, destination: Path) -> None:
        response = None
        try:
            response = self.client.get_object(self.bucket, key)
            with destination.open("wb") as target:
                shutil.copyfileobj(response, target)
        except Exception as exc:
            raise ObjectStorageError("Could not read the stored artifact") from exc
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    def presigned_get(self, key: str, expires_seconds: int) -> str:
        try:
            return self.client.presigned_get_object(
                self.bucket, key, expires=timedelta(seconds=expires_seconds)
            )
        except Exception as exc:
            raise ObjectStorageError("Could not create an artifact download URL") from exc


class InMemoryObjectStorage:
    """Deterministic storage double used by API tests; never used in production."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def ensure_bucket(self) -> None:
        return None

    def put_object(self, key: str, source: BinaryIO, length: int, content_type: str) -> None:
        payload = source.read()
        if len(payload) != length:
            raise ObjectStorageError("Uploaded object length did not match the declared length")
        self.objects[key] = payload

    def delete_object(self, key: str) -> None:
        self.objects.pop(key, None)

    def download_to_path(self, key: str, destination: Path) -> None:
        try:
            payload = self.objects[key]
        except KeyError as exc:
            raise ObjectStorageError("Stored artifact was not found") from exc
        destination.write_bytes(payload)

    def presigned_get(self, key: str, expires_seconds: int) -> str:
        if key not in self.objects:
            raise ObjectStorageError("Stored artifact was not found")
        return f"memory://artifact/{key}"


def get_storage(settings: Settings) -> ObjectStorage:
    return MinioObjectStorage(settings)
