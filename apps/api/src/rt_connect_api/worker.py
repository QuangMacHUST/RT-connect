"""Database-backed Gamma worker entrypoint for the first P8 staging slice.

The API persists a QUEUED row and returns immediately. This process claims queued
rows and executes the deterministic engine outside the HTTP request lifecycle. A
Redis adapter can replace the polling/claim loop without changing the Gamma run
contract.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from rt_connect_api.api.gamma import process_gamma_run
from rt_connect_api.core.config import get_settings
from rt_connect_api.db.models import GammaAnalysisRun
from rt_connect_api.db.session import get_engine
from rt_connect_api.services.object_storage import ObjectStorage, get_storage


def recover_stale_runs(session: Session, timeout_seconds: int = 900) -> int:
    """Return abandoned RUNNING rows to the queue after a heartbeat timeout."""

    cutoff = datetime.now(UTC) - timedelta(seconds=timeout_seconds)
    stale_ids = list(
        session.scalars(
            select(GammaAnalysisRun.id).where(
                GammaAnalysisRun.status == "RUNNING",
                GammaAnalysisRun.heartbeat_at.is_not(None),
                GammaAnalysisRun.heartbeat_at < cutoff,
            )
        )
    )
    if not stale_ids:
        return 0
    session.execute(
        update(GammaAnalysisRun)
        .where(GammaAnalysisRun.id.in_(stale_ids))
        .values(
            status="RETRYING",
            progress_percent=0,
            error_snapshot=[
                {
                    "code": "GAMMA_WORKER_HEARTBEAT_TIMEOUT",
                    "message": "The previous worker stopped reporting heartbeat.",
                }
            ],
            heartbeat_at=None,
        )
    )
    session.commit()
    return len(stale_ids)


def process_next_gamma_run(session: Session, storage: ObjectStorage) -> bool:
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
    process_gamma_run(session, run, storage)
    return True


def main() -> None:
    settings = get_settings()
    engine = get_engine()
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured for the Gamma worker")
    storage = get_storage(settings)
    poll_seconds = max(0.5, float(os.getenv("GAMMA_WORKER_POLL_SECONDS", "2")))
    run_once = os.getenv("GAMMA_WORKER_ONCE", "0") == "1"
    factory = Session
    while True:
        with factory(bind=engine) as session:
            recover_stale_runs(session)
            processed = process_next_gamma_run(session, storage)
        if run_once or not processed:
            if run_once:
                return
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
