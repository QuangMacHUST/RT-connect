from uuid import uuid4

from rt_connect_api.core.config import Settings
from rt_connect_api.services.redis_queue import (
    InvalidGammaQueueMessage,
    RedisGammaQueue,
    get_gamma_queue,
)


class FakeRedis:
    def __init__(self) -> None:
        self.dispatch_seen = False
        self.acknowledged: list[str] = []
        self.xadd_calls: list[tuple[str, dict[str, str]]] = []

    def ping(self) -> bool:
        return True

    def xgroup_create(self, **_: object) -> None:
        return None

    def set(self, *_: object, **__: object) -> bool:
        if self.dispatch_seen:
            return False
        self.dispatch_seen = True
        return True

    def xadd(self, stream: str, fields: dict[str, str], **_: object) -> str:
        self.xadd_calls.append((stream, fields))
        return "1-0"

    def xautoclaim(self, *_: object, **__: object) -> list[object]:
        return [
            "0-0",
            [
                (
                    "1-0",
                    {
                        "run_id": str(RUN_ID),
                        "organization_id": str(ORGANIZATION_ID),
                        "attempt": "0",
                    },
                )
            ],
            [],
        ]

    def xack(self, *_: str) -> int:
        self.acknowledged.append(_[-1])
        return 1

    def xlen(self, *_: str) -> int:
        return 1

    def xpending(self, *_: str) -> dict[str, int]:
        return {"pending": 1}

    def xinfo_groups(self, *_: str) -> list[dict[str, object]]:
        return [{"name": "test-group", "consumers": 1}]


RUN_ID = uuid4()
ORGANIZATION_ID = uuid4()


def _queue() -> tuple[RedisGammaQueue, FakeRedis]:
    settings = Settings(
        redis_url="redis://localhost:6379/15",
        gamma_queue_stream="test-stream",
        gamma_queue_group="test-group",
    )
    queue = RedisGammaQueue(settings, consumer_name="test-consumer")
    client = FakeRedis()
    queue.client = client
    return queue, client


def test_redis_queue_enqueue_claim_ack_and_metrics() -> None:
    queue, client = _queue()

    assert queue.enqueue(RUN_ID, ORGANIZATION_ID, 0) == "1-0"
    assert queue.enqueue(RUN_ID, ORGANIZATION_ID, 0) == "deduplicated"
    message = queue.claim(block_ms=10)

    assert message is not None
    assert message.run_id == RUN_ID
    assert message.organization_id == ORGANIZATION_ID
    assert message.attempt == 0
    assert queue.metrics() == {
        "backend": "redis_stream",
        "stream_length": 1,
        "pending_count": 1,
        "consumer_count": 1,
    }
    queue.acknowledge(message.message_id)
    assert client.acknowledged == ["1-0"]

    dead_letter_id = queue.dead_letter(message, "GAMMA_STORAGE_UNAVAILABLE")
    assert dead_letter_id == "1-0"


def test_redis_queue_classifies_invalid_message_for_quarantine() -> None:
    message = RedisGammaQueue._parse_entries(
        [
            (
                "1-0",
                {
                    "run_id": "not-a-uuid",
                    "organization_id": str(ORGANIZATION_ID),
                    "attempt": "0",
                    "secret_value": "must-not-be-copied",
                },
            )
        ]
    )
    assert isinstance(message, InvalidGammaQueueMessage)
    assert message.error_code == "GAMMA_QUEUE_MESSAGE_INVALID"
    assert message.reason == "identity_or_attempt_invalid"
    assert "secret_value" in message.payload_keys


def test_redis_queue_dead_letter_keeps_malformed_payload_values_out_of_quarantine() -> None:
    queue, client = _queue()
    message = InvalidGammaQueueMessage(
        message_id="2-0",
        reason="identity_or_attempt_invalid",
        payload_keys=("attempt", "run_id", "secret_value"),
    )

    assert queue.dead_letter(message, message.error_code) == "1-0"
    stream, fields = client.xadd_calls[-1]
    assert stream == "test-stream:dead-letter"
    assert fields == {
        "job_type": "GAMMA",
        "source_message_id": "2-0",
        "error_code": "GAMMA_QUEUE_MESSAGE_INVALID",
        "diagnostic": "identity_or_attempt_invalid",
        "payload_keys": "attempt,run_id,secret_value",
    }
    assert "must-not-be-copied" not in str(fields)


def test_get_gamma_queue_keeps_db_fallback_when_unconfigured() -> None:
    assert get_gamma_queue(Settings(redis_url=None)) is None
