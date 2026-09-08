"""Gamma worker entrypoint for the P8 staging queue.

The API persists a QUEUED row and returns immediately. When REDIS_URL is set this
process claims Redis Stream messages and executes the deterministic engine outside
the HTTP request lifecycle; without it, local development retains DB polling.
"""

from __future__ import annotations

import logging
import os
import random
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from rt_connect_api.api.gamma import (
    _ensure_dispatch_outbox,
    acquire_gamma_run_lease,
    process_gamma_run,
)
from rt_connect_api.core.config import get_settings
from rt_connect_api.db.models import GammaAnalysisRun, GammaDispatchOutbox, GammaRunAttempt
from rt_connect_api.db.session import get_engine
from rt_connect_api.services.object_storage import ObjectStorage, get_storage
from rt_connect_api.services.redis_queue import (
    GammaQueueMessage,
    RedisGammaQueue,
    RedisQueueError,
    get_gamma_queue,
)

logger = logging.getLogger(__name__)


def _as_utc(value: datetime | None) -> datetime | None:
    """Normalize SQLite's naive timestamp round-trip to the UTC contract."""

    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _retry_delay_seconds(attempt_count: int, settings: object) -> float:
    """Return bounded exponential backoff with jitter for a next attempt."""

    base = float(getattr(settings, "gamma_retry_backoff_base_seconds", 5))
    maximum = float(getattr(settings, "gamma_retry_backoff_max_seconds", 300))
    exponential = min(maximum, base * (2 ** max(0, attempt_count - 1)))
    return random.uniform(0.0, exponential) if exponential else 0.0


def recover_stale_runs(
    session: Session,
    timeout_seconds: int = 120,
    *,
    max_attempts: int = 3,
    retry_delay_seconds: float = 0.0,
) -> int:
    """Return abandoned RUNNING rows to the queue after heartbeat/lease expiry."""

    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=timeout_seconds)
    stale_runs = list(
        session.scalars(
            select(GammaAnalysisRun).where(
                GammaAnalysisRun.status == "RUNNING",
                (
                    (
                        GammaAnalysisRun.heartbeat_at.is_not(None)
                        & (GammaAnalysisRun.heartbeat_at < cutoff)
                    )
                    | (
                        GammaAnalysisRun.lease_expires_at.is_not(None)
                        & (GammaAnalysisRun.lease_expires_at < now)
                    )
                ),
            )
        )
    )
    if not stale_runs:
        return 0
    for run in stale_runs:
        lease_expiry = _as_utc(run.lease_expires_at)
        lease_expired = lease_expiry is not None and lease_expiry < now
        error_code = "GAMMA_LEASE_EXPIRED" if lease_expired else "GAMMA_WORKER_HEARTBEAT_TIMEOUT"
        error_snapshot: list[dict[str, object]] = [
            {
                "code": error_code,
                "message": (
                    "The previous worker lease expired."
                    if lease_expired
                    else "The previous worker stopped reporting heartbeat."
                ),
            }
        ]
        retrying = run.attempt_count < max_attempts
        run.status = "RETRYING" if retrying else "FAILED"
        run.progress_percent = 0 if retrying else 100
        run.error_snapshot = error_snapshot
        run.heartbeat_at = None
        run.worker_id = None
        run.lease_token = None
        run.lease_expires_at = None
        run.completed_at = None if retrying else now
        session.execute(
            update(GammaRunAttempt)
            .where(
                GammaRunAttempt.gamma_run_id == run.id,
                GammaRunAttempt.organization_id == run.organization_id,
                GammaRunAttempt.attempt_number == run.attempt_count,
                GammaRunAttempt.status == "RUNNING",
            )
            .values(
                status="FAILED",
                completed_at=now,
                error_snapshot=error_snapshot,
            )
        )
        if retrying:
            outbox = _ensure_dispatch_outbox(session, run)
            outbox.status = "PENDING"
            outbox.available_at = now + timedelta(seconds=max(0.0, retry_delay_seconds))
            outbox.published_at = None
            outbox.last_error = error_code
    session.commit()
    return len(stale_runs)


def publish_pending_dispatches(
    session: Session, queue: RedisGammaQueue | None, limit: int = 20
) -> int:
    """Reconcile durable DB dispatch intents into Redis without duplicating jobs."""

    if queue is None:
        return 0
    now = datetime.now(UTC)
    pending = list(
        session.scalars(
            select(GammaDispatchOutbox)
            .where(
                GammaDispatchOutbox.status == "PENDING",
                GammaDispatchOutbox.available_at <= now,
            )
            .order_by(GammaDispatchOutbox.available_at, GammaDispatchOutbox.created_at)
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
    )
    published = 0
    for outbox in pending:
        try:
            queue.enqueue(outbox.gamma_run_id, outbox.organization_id, outbox.attempt_number)
        except RedisQueueError as exc:
            outbox.last_error = "GAMMA_QUEUE_UNAVAILABLE"
            logger.warning("Gamma outbox publish failed: %s", exc)
            continue
        outbox.status = "PUBLISHED"
        outbox.published_at = now
        outbox.last_error = None
        published += 1
    session.commit()
    return published


def process_next_gamma_run(
    session: Session,
    storage: ObjectStorage,
    *,
    lease_seconds: int = 120,
    max_attempts: int = 3,
    execution_deadline_seconds: int = 900,
    retry_delay_seconds: float = 0.0,
) -> bool:
    """Claim and process one queued/retrying Gamma run, if one exists."""

    run = session.scalar(
        select(GammaAnalysisRun)
        .where(GammaAnalysisRun.status.in_(["QUEUED", "RETRYING"]))
        .order_by(GammaAnalysisRun.queued_at, GammaAnalysisRun.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if run is None:
        return False
    process_gamma_run(
        session,
        run,
        storage,
        lease_seconds=lease_seconds,
        max_attempts=max_attempts,
        execution_deadline_seconds=execution_deadline_seconds,
        retry_delay_seconds=retry_delay_seconds,
    )
    return True


def process_gamma_queue_message(
    session: Session,
    storage: ObjectStorage,
    message: GammaQueueMessage,
    *,
    lease_seconds: int = 120,
    max_attempts: int = 3,
    execution_deadline_seconds: int = 900,
    retry_delay_seconds: float = 0.0,
) -> bool:
    """Process a Redis message only when its organization-scoped run is available."""

    run = session.scalar(
        select(GammaAnalysisRun).where(
            GammaAnalysisRun.id == message.run_id,
            GammaAnalysisRun.organization_id == message.organization_id,
        )
    )
    if run is None or run.status not in {"QUEUED", "RETRYING"}:
        return False
    if message.attempt != run.attempt_count:
        # A stale Redis message is safe to acknowledge because a recovery
        # cycle creates a new outbox intent for the current attempt.
        return False
    worker_id = os.getenv("GAMMA_QUEUE_CONSUMER", "gamma-worker")
    lease_token = acquire_gamma_run_lease(
        session,
        run,
        worker_id,
        expected_dispatch_attempt=message.attempt,
        lease_seconds=lease_seconds,
    )
    if lease_token is None:
        return False
    process_gamma_run(
        session,
        run,
        storage,
        lease_token=lease_token,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
        max_attempts=max_attempts,
        execution_deadline_seconds=execution_deadline_seconds,
        retry_delay_seconds=retry_delay_seconds,
    )
    return True


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured for the Gamma worker")
    storage = get_storage(settings)
    poll_seconds = max(0.5, float(os.getenv("GAMMA_WORKER_POLL_SECONDS", "2")))
    run_once = os.getenv("GAMMA_WORKER_ONCE", "0") == "1"
    factory = Session
    queue = get_gamma_queue(settings, consumer_name=os.getenv("GAMMA_QUEUE_CONSUMER"))
    logger.info(
        "Gamma worker starting queue_backend=%s stream=%s group=%s",
        "redis_stream" if queue is not None else "database_polling",
        settings.gamma_queue_stream,
        settings.gamma_queue_group,
    )
    if queue is not None:
        queue.ensure_ready()
        logger.info("Gamma worker using Redis Streams queue")
        while True:
            with factory(bind=engine) as session:
                recover_stale_runs(
                    session,
                    timeout_seconds=settings.gamma_lease_seconds,
                    max_attempts=settings.gamma_retry_max_attempts,
                    retry_delay_seconds=_retry_delay_seconds(1, settings),
                )
                publish_pending_dispatches(session, queue)
            try:
                message = queue.claim(block_ms=int(poll_seconds * 1000))
            except RedisQueueError:
                logger.exception("Gamma Redis queue is unavailable")
                time.sleep(poll_seconds)
                continue
            if message is None:
                if run_once:
                    return
                continue
            try:
                with factory(bind=engine) as session:
                    run = session.scalar(
                        select(GammaAnalysisRun).where(
                            GammaAnalysisRun.id == message.run_id,
                            GammaAnalysisRun.organization_id == message.organization_id,
                        )
                    )
                    retry_delay = (
                        _retry_delay_seconds(run.attempt_count, settings)
                        if run is not None
                        else 0.0
                    )
                    processed = process_gamma_queue_message(
                        session,
                        storage,
                        message,
                        lease_seconds=settings.gamma_lease_seconds,
                        max_attempts=settings.gamma_retry_max_attempts,
                        execution_deadline_seconds=settings.gamma_execution_deadline_seconds,
                        retry_delay_seconds=retry_delay,
                    )
                    if processed and run.status == "FAILED":
                        raw_error = (
                            run.error_snapshot[0].get("code") if run.error_snapshot else None
                        )
                        queue.dead_letter(
                            message,
                            raw_error if isinstance(raw_error, str) else "GAMMA_TERMINAL_FAILURE",
                        )
                queue.acknowledge(message.message_id)
            except Exception:
                logger.exception("Gamma queue message processing failed")
                # Leave the message pending so XAUTOCLAIM can retry it after the
                # visibility timeout. The database recovery path also returns a
                # stale RUNNING row to RETRYING.
            if run_once:
                return
    while True:
        with factory(bind=engine) as session:
            recover_stale_runs(
                session,
                timeout_seconds=settings.gamma_lease_seconds,
                max_attempts=settings.gamma_retry_max_attempts,
                retry_delay_seconds=_retry_delay_seconds(1, settings),
            )
            processed = process_next_gamma_run(
                session,
                storage,
                lease_seconds=settings.gamma_lease_seconds,
                max_attempts=settings.gamma_retry_max_attempts,
                execution_deadline_seconds=settings.gamma_execution_deadline_seconds,
                retry_delay_seconds=_retry_delay_seconds(1, settings),
            )
        if run_once or not processed:
            if run_once:
                return
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
