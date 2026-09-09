"""Redis Streams queue adapter for asynchronous Gamma jobs.

The database row remains the source of truth for a Gamma run. Redis carries the
dispatch signal, consumer-group ownership and operational queue counters. This
keeps the API contract stable while allowing local development to continue with
the existing database-backed polling worker when ``REDIS_URL`` is absent.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from redis import Redis
from redis.exceptions import RedisError, ResponseError

from rt_connect_api.core.config import Settings


class RedisQueueError(RuntimeError):
    """Raised when the Redis queue cannot be reached or contains invalid data."""


@dataclass(frozen=True)
class GammaQueueMessage:
    """A claimed Gamma dispatch message."""

    message_id: str
    run_id: UUID
    organization_id: UUID
    attempt: int


@dataclass(frozen=True)
class InvalidGammaQueueMessage:
    """A Redis entry that can be quarantined without trusting its payload."""

    message_id: str
    reason: str
    payload_keys: tuple[str, ...] = ()

    @property
    def error_code(self) -> str:
        return "GAMMA_QUEUE_MESSAGE_INVALID"


GammaQueueClaim = GammaQueueMessage | InvalidGammaQueueMessage


class RedisGammaQueue:
    """Redis Streams implementation used by the API and the Gamma worker."""

    def __init__(self, settings: Settings, consumer_name: str | None = None) -> None:
        if settings.redis_url is None:
            raise ValueError("REDIS_URL is required for the Redis Gamma queue")
        self.stream_name = settings.gamma_queue_stream
        self.dead_letter_stream_name = f"{self.stream_name}:dead-letter"
        self.group_name = settings.gamma_queue_group
        self.visibility_timeout_ms = settings.gamma_queue_visibility_timeout_seconds * 1000
        self.maxlen = settings.gamma_queue_maxlen
        generated_name = f"{socket.gethostname()}-{uuid4().hex[:12]}"
        self.consumer_name = consumer_name or f"gamma-{generated_name}"
        self.client: Any = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )

    def ensure_ready(self) -> None:
        """Verify Redis connectivity and create the consumer group if needed."""

        try:
            self.client.ping()
            try:
                self.client.xgroup_create(
                    name=self.stream_name,
                    groupname=self.group_name,
                    id="0-0",
                    mkstream=True,
                )
            except ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
        except RedisError as exc:
            raise RedisQueueError("Redis Gamma queue is unavailable") from exc

    def enqueue(self, run_id: UUID, organization_id: UUID, attempt: int) -> str:
        """Publish one dispatch signal, deduplicated by run and attempt."""

        self.ensure_ready()
        dispatch_key = f"{self.stream_name}:dispatch:{run_id}:{attempt}"
        try:
            created = self.client.set(
                dispatch_key,
                "1",
                nx=True,
                ex=self.visibility_timeout_ms // 1000,
            )
            if not created:
                return "deduplicated"
            message_id = self.client.xadd(
                self.stream_name,
                {
                    "job_type": "GAMMA",
                    "run_id": str(run_id),
                    "organization_id": str(organization_id),
                    "attempt": str(attempt),
                },
                maxlen=self.maxlen,
                approximate=True,
            )
            return str(message_id)
        except RedisError as exc:
            raise RedisQueueError("Gamma job could not be published to Redis") from exc

    def claim(self, block_ms: int = 2_000) -> GammaQueueClaim | None:
        """Claim a stale pending message first, then wait for a new message."""

        self.ensure_ready()
        try:
            reclaimed = self.client.xautoclaim(
                self.stream_name,
                self.group_name,
                self.consumer_name,
                self.visibility_timeout_ms,
                start_id="0-0",
                count=1,
            )
            if isinstance(reclaimed, list | tuple) and len(reclaimed) >= 2:
                message = self._parse_entries(reclaimed[1])
                if message is not None:
                    return message

            delivered = self.client.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_name: ">"},
                count=1,
                block=max(1, block_ms),
            )
            if not delivered:
                return None
            stream_entries = delivered[0][1]
            return self._parse_entries(stream_entries)
        except RedisError as exc:
            raise RedisQueueError("Gamma job could not be claimed from Redis") from exc

    def acknowledge(self, message_id: str) -> None:
        """Acknowledge a completed or permanently failed dispatch signal."""

        try:
            self.client.xack(self.stream_name, self.group_name, message_id)
        except RedisError as exc:
            raise RedisQueueError("Gamma job acknowledgement failed") from exc

    def dead_letter(self, message: GammaQueueClaim, error_code: str) -> str:
        """Persist a terminal dispatch failure before its source is acknowledged.

        The database remains authoritative for the run/result.  This stream is
        an operational quarantine record: it lets an operator inspect the
        message identity and terminal error without replaying a permanently
        failed job into the normal consumer group.
        """

        fields: dict[str, str] = {
            "job_type": "GAMMA",
            "source_message_id": message.message_id,
            "error_code": error_code,
        }
        if isinstance(message, GammaQueueMessage):
            fields.update(
                {
                    "run_id": str(message.run_id),
                    "organization_id": str(message.organization_id),
                    "attempt": str(message.attempt),
                }
            )
        else:
            fields.update(
                {
                    "diagnostic": message.reason,
                    "payload_keys": ",".join(message.payload_keys),
                }
            )
        try:
            return str(
                self.client.xadd(
                    self.dead_letter_stream_name,
                    fields,
                    maxlen=self.maxlen,
                    approximate=True,
                )
            )
        except RedisError as exc:
            raise RedisQueueError("Gamma dead-letter write failed") from exc

    def metrics(self) -> dict[str, int | str]:
        """Return non-secret queue counters for the authenticated operations view."""

        self.ensure_ready()
        try:
            stream_length = int(self.client.xlen(self.stream_name))
            pending = self.client.xpending(self.stream_name, self.group_name)
            pending_count = int(pending.get("pending", 0)) if isinstance(pending, dict) else 0
            groups = self.client.xinfo_groups(self.stream_name)
            consumer_count = 0
            for group in groups:
                if group.get("name") == self.group_name:
                    consumer_count = int(group.get("consumers", 0))
                    break
            return {
                "backend": "redis_stream",
                "stream_length": stream_length,
                "pending_count": pending_count,
                "consumer_count": consumer_count,
            }
        except RedisError as exc:
            raise RedisQueueError("Gamma queue metrics are unavailable") from exc

    @staticmethod
    def _parse_entries(entries: object) -> GammaQueueClaim | None:
        if not isinstance(entries, list | tuple) or not entries:
            return None
        entry = entries[0]
        if not isinstance(entry, list | tuple) or len(entry) != 2:
            return None
        message_id, payload = entry
        if not isinstance(message_id, str):
            return None
        if not isinstance(payload, dict):
            return InvalidGammaQueueMessage(message_id, "payload_not_mapping")
        payload_keys = tuple(sorted(str(key) for key in payload)[:20])
        if payload.get("job_type") not in (None, "GAMMA"):
            return InvalidGammaQueueMessage(message_id, "job_type_invalid", payload_keys)
        try:
            run_id = UUID(str(payload["run_id"]))
            organization_id = UUID(str(payload["organization_id"]))
            attempt = int(str(payload["attempt"]))
            if attempt < 0:
                raise ValueError("attempt_negative")
        except (KeyError, TypeError, ValueError):
            return InvalidGammaQueueMessage(message_id, "identity_or_attempt_invalid", payload_keys)
        return GammaQueueMessage(
            message_id=message_id,
            run_id=run_id,
            organization_id=organization_id,
            attempt=attempt,
        )


def get_gamma_queue(settings: Settings, consumer_name: str | None = None) -> RedisGammaQueue | None:
    """Return the configured Redis queue, or ``None`` for DB-only local mode."""

    if settings.redis_url is None:
        return None
    return RedisGammaQueue(settings, consumer_name=consumer_name)
