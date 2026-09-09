"""Verify the local Redis/worker Gamma path with disposable synthetic data.

The normal local Compose stack must exercise the same at-least-once boundary as
staging: a database-backed run and outbox, Redis Stream dispatch, a separate
worker process, durable result/attempt state, bounded retry, and dead-letter
quarantine.  This verifier uses a temporary SQLite database and a unique
MinIO bucket/Redis stream so it cannot touch the developer's existing local
records.  It never uses patient, PACS, or treatment data.

It deliberately does not claim staging or clinical readiness.  Its purpose is
to prevent a future Compose change from silently reverting to an API-only
stack, and to provide a reproducible local support artifact for P8/P18.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = REPOSITORY_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SOURCE))

from rt_connect_api.api.gamma import _ensure_dispatch_outbox  # noqa: E402
from rt_connect_api.core.config import Settings  # noqa: E402
from rt_connect_api.db.base import Base  # noqa: E402
from rt_connect_api.db.models import (  # noqa: E402
    Artifact,
    Folder,
    GammaAnalysisRun,
    GammaDispatchOutbox,
    GammaRunAttempt,
    InputManifest,
    Machine,
    Organization,
    QACase,
    Site,
)
from rt_connect_api.services.object_storage import MinioObjectStorage  # noqa: E402
from rt_connect_api.services.redis_queue import GammaQueueMessage, RedisGammaQueue  # noqa: E402
from rt_connect_api.worker import publish_pending_dispatches  # noqa: E402


def _measurement(dataset_id: str) -> bytes:
    return json.dumps(
        {
            "schema_version": "gamma.measurement.v1",
            "dataset_id": dataset_id,
            "data_type": "dose",
            "units": {"dose": "GY", "position": "mm"},
            "grid": {"shape": [2, 2], "spacing_mm": [1.0, 1.0]},
            "values": {"encoding": "inline-float32", "inline": [1, 2, 3, 4]},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _config() -> dict[str, object]:
    return {
        "dimensionality": "2D",
        "dose_difference_percent": 3.0,
        "dose_difference_mode": "RELATIVE",
        "absolute_dose_difference_gy": None,
        "distance_to_agreement_mm": 3.0,
        "dose_threshold_percent": 0.0,
        "normalization": "GLOBAL",
        "interpolation": "GRID",
        "coverage_policy": "FULL_ROI",
        "max_gamma": 2.0,
        "pass_rate_threshold_percent": 95.0,
        "histogram_bins": 10,
        "workflow_profile": "ENGINE_TEST",
        "resource_budget": {
            "max_candidate_evaluations": 50_000,
        },
    }


def _create_run(
    session: Session,
    organization: Organization,
    case: QACase,
    reference: Artifact,
    evaluation: Artifact,
    *,
    idempotency_key: str,
) -> GammaAnalysisRun:
    run = GammaAnalysisRun(
        organization_id=organization.id,
        qa_case_id=case.id,
        reference_artifact_id=reference.id,
        evaluation_artifact_id=evaluation.id,
        idempotency_key=idempotency_key,
        request_fingerprint=hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest(),
        status="QUEUED",
        engine_version="gamma-nd-p8.2",
        config_snapshot=_config(),
        input_manifest_snapshot={
            "reference": {"artifact_id": str(reference.id), "sha256": reference.sha256},
            "evaluation": {"artifact_id": str(evaluation.id), "sha256": evaluation.sha256},
        },
        result_snapshot={},
        error_snapshot=[],
        warning_snapshot=[],
    )
    session.add(run)
    session.flush()
    _ensure_dispatch_outbox(session, run)
    session.commit()
    session.refresh(run)
    return run


def _create_fixture(
    session: Session,
    storage: MinioObjectStorage,
    bucket_prefix: str,
) -> tuple[Organization, QACase, Artifact, Artifact, bytes]:
    organization = Organization(name=f"Local Gamma Queue Smoke {uuid4().hex[:10]}")
    site = Site(name="Synthetic Queue Site", organization=organization)
    session.add_all([organization, site])
    session.flush()
    machine = Machine(
        organization_id=organization.id,
        site_id=site.id,
        stable_machine_id=f"LOCAL-GAMMA-{uuid4().hex[:10]}",
        display_name="Synthetic Gamma Queue Machine",
    )
    folder = Folder(organization_id=organization.id, name="Queue Smoke")
    session.add_all([machine, folder])
    session.flush()
    case = QACase(
        organization_id=organization.id,
        site_id=site.id,
        machine_id=machine.id,
        primary_folder_id=folder.id,
        qa_type="PSQA Gamma",
        qa_cycle="CUSTOM",
        performed_at=datetime.now(UTC),
        title="Synthetic Redis worker queue smoke",
    )
    session.add(case)
    session.flush()

    payload = _measurement("local-queue-reference")
    reference_key = f"{bucket_prefix}/reference.json"
    evaluation_key = f"{bucket_prefix}/evaluation.json"
    digest = hashlib.sha256(payload).hexdigest()
    reference = Artifact(
        organization_id=organization.id,
        qa_case_id=case.id,
        artifact_type="MEASUREMENT",
        original_filename="reference.json",
        object_key=reference_key,
        byte_size=len(payload),
        media_type="application/json",
        sha256=digest,
        data_status="VALID",
        metadata_snapshot={"grid": {"shape": [2, 2]}},
    )
    evaluation = Artifact(
        organization_id=organization.id,
        qa_case_id=case.id,
        artifact_type="MEASUREMENT",
        original_filename="evaluation.json",
        object_key=evaluation_key,
        byte_size=len(payload),
        media_type="application/json",
        sha256=digest,
        data_status="VALID",
        metadata_snapshot={"grid": {"shape": [2, 2]}},
    )
    session.add_all([reference, evaluation])
    session.flush()
    for artifact, role in ((reference, "REFERENCE"), (evaluation, "EVALUATION")):
        session.add(
            InputManifest(
                organization_id=organization.id,
                artifact_id=artifact.id,
                logical_role=role,
                checksum_at_use=artifact.sha256,
                selected_metadata=artifact.metadata_snapshot,
                geometry_summary={"shape": [2, 2]},
                unit_summary={"dose_units": "GY"},
                validation_summary={"result": "VALID"},
            )
        )
    session.commit()
    storage.put_object(reference_key, BytesIO(payload), len(payload), "application/json")
    storage.put_object(evaluation_key, BytesIO(payload), len(payload), "application/json")
    return organization, case, reference, evaluation, payload


def _start_worker(environment: dict[str, str]) -> subprocess.Popen[str]:
    child_environment = os.environ.copy()
    child_environment.update(environment)
    child_environment["PYTHONPATH"] = str(API_SOURCE)
    return subprocess.Popen(  # noqa: S603 - executable and args are repository controlled
        [sys.executable, "-m", "rt_connect_api.worker"],
        cwd=REPOSITORY_ROOT,
        env=child_environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _run_worker_until_terminal(
    session: Session,
    run_id: UUID,
    worker_environment: dict[str, str],
    *,
    timeout_seconds: float = 30.0,
) -> tuple[GammaAnalysisRun, str]:
    process = _start_worker(worker_environment)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        session.expire_all()
        run = session.get(GammaAnalysisRun, run_id)
        if run is not None and run.status in {"COMPLETED", "RETRYING", "FAILED"}:
            break
        if process.poll() is not None:
            break
        time.sleep(0.25)
    try:
        output, _ = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate(timeout=5)
    run = session.get(GammaAnalysisRun, run_id)
    if run is None:
        raise RuntimeError("Worker smoke run disappeared from the temporary database")
    if run.status not in {"COMPLETED", "RETRYING", "FAILED"}:
        raise RuntimeError(f"Worker did not reach a terminal state: {run.status}; output={output}")
    return run, output


def _environment(database_path: Path, stream: str, group: str, bucket: str) -> dict[str, str]:
    return {
        "APP_ENV": "development",
        "APP_VERSION": "local-gamma-queue-smoke",
        "SCHEMA_REVISION": "local-smoke",
        "DATABASE_URL": f"sqlite+pysqlite:///{database_path.as_posix()}",
        "REDIS_URL": "redis://127.0.0.1:6379/0",
        "S3_ENDPOINT": "http://127.0.0.1:9000",
        "S3_REGION": "us-east-1",
        "S3_BUCKET": bucket,
        "S3_ACCESS_KEY_ID": "local-development-only",
        "S3_SECRET_ACCESS_KEY": "local-development-only",
        "GAMMA_QUEUE_STREAM": stream,
        "GAMMA_QUEUE_GROUP": group,
        "GAMMA_QUEUE_VISIBILITY_TIMEOUT_SECONDS": "30",
        "GAMMA_LEASE_SECONDS": "30",
        "GAMMA_RETRY_MAX_ATTEMPTS": "3",
        "GAMMA_RETRY_BACKOFF_BASE_SECONDS": "0",
        "GAMMA_RETRY_BACKOFF_MAX_SECONDS": "0",
        "GAMMA_WORKER_ONCE": "1",
        "GAMMA_WORKER_POLL_SECONDS": "1",
        "GAMMA_QUEUE_CONSUMER": f"local-smoke-{uuid4().hex[:8]}",
    }


def _publish_next_attempt(session: Session, queue: RedisGammaQueue) -> None:
    published = publish_pending_dispatches(session, queue)
    if published != 1:
        raise RuntimeError(f"Expected one retry dispatch, published {published}")


def _cleanup_storage(storage: MinioObjectStorage, bucket: str) -> None:
    try:
        objects = list(storage.client.list_objects(bucket, recursive=True))
        for item in objects:
            storage.client.remove_object(bucket, item.object_name)
        storage.client.remove_bucket(bucket)
    except Exception as exc:  # pragma: no cover - cleanup diagnostics are retained in failure text
        raise RuntimeError(f"Could not clean disposable MinIO bucket {bucket}") from exc


def _capture_commit() -> str | None:
    try:
        completed = subprocess.run(  # noqa: S603 - executable is repository controlled
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def verify(output_path: Path) -> dict[str, Any]:
    token = uuid4().hex
    stream = f"rt-connect:gamma:local-smoke:{token}"
    group = f"rt-connect-gamma-smoke-{token[:12]}"
    bucket = f"rt-connect-gamma-smoke-{token[:20]}"
    environment_base: dict[str, str] = {}
    storage: MinioObjectStorage | None = None
    queue: RedisGammaQueue | None = None
    database_path: Path | None = None
    database_engine: Any = None
    cleanup_run_ids: list[UUID] = []
    try:
        with tempfile.TemporaryDirectory(prefix="rt-connect-gamma-queue-") as temporary_directory:
            database_path = Path(temporary_directory) / "queue-smoke.sqlite3"
            database_engine = create_engine(
                f"sqlite+pysqlite:///{database_path}", poolclass=NullPool
            )
            Base.metadata.create_all(database_engine)
            settings = Settings(
                app_env="development",
                app_version="local-gamma-queue-smoke",
                database_url=None,
                redis_url="redis://127.0.0.1:6379/0",
                s3_endpoint="http://127.0.0.1:9000",
                s3_bucket=bucket,
                s3_access_key_id="local-development-only",
                s3_secret_access_key="local-development-only",
                gamma_queue_stream=stream,
                gamma_queue_group=group,
                gamma_queue_visibility_timeout_seconds=30,
                gamma_retry_backoff_base_seconds=0,
                gamma_retry_backoff_max_seconds=0,
            )
            storage = MinioObjectStorage(settings)
            storage.ensure_bucket()
            queue = RedisGammaQueue(settings, consumer_name=f"local-smoke-{token[:8]}")
            queue.ensure_ready()

            with Session(database_engine, expire_on_commit=False) as session:
                organization, case, reference, evaluation, payload = _create_fixture(
                    session, storage, token
                )
                good_run = _create_run(
                    session,
                    organization,
                    case,
                    reference,
                    evaluation,
                    idempotency_key=f"local-good-{token}",
                )
                good_outbox = session.scalar(
                    select(GammaDispatchOutbox).where(
                        GammaDispatchOutbox.gamma_run_id == good_run.id,
                        GammaDispatchOutbox.attempt_number == 0,
                    )
                )
                if good_outbox is None:
                    raise RuntimeError("Good run did not create a durable dispatch outbox")
                message_id = queue.enqueue(good_run.id, organization.id, 0)
                good_outbox.status = "PUBLISHED"
                good_outbox.published_at = datetime.now(UTC)
                session.commit()

                environment_base = _environment(database_path, stream, group, bucket)
                good_run, good_worker_output = _run_worker_until_terminal(
                    session, good_run.id, environment_base
                )
                cleanup_run_ids.append(good_run.id)
                session.refresh(good_run)
                good_attempts = list(
                    session.scalars(
                        select(GammaRunAttempt)
                        .where(GammaRunAttempt.gamma_run_id == good_run.id)
                        .order_by(GammaRunAttempt.attempt_number)
                    )
                )
                replay = GammaQueueMessage(
                    message_id=message_id,
                    run_id=good_run.id,
                    organization_id=organization.id,
                    attempt=0,
                )
                # A redelivery after durable terminal commit must be harmless;
                # the worker's run lookup rejects the already-completed row.
                from rt_connect_api.worker import process_gamma_queue_message  # noqa: PLC0415

                replay_processed = process_gamma_queue_message(session, storage, replay)
                duplicate_dispatch = queue.enqueue(good_run.id, organization.id, 0)
                good_checks = {
                    "status": good_run.status == "COMPLETED",
                    "overall_status": good_run.result_snapshot.get("overall_status") == "PASS",
                    "evaluated_points": good_run.result_snapshot.get("metrics", {}).get(
                        "evaluated_points"
                    )
                    == 4,
                    "attempt_count": good_run.attempt_count == 1,
                    "attempt_terminal": len(good_attempts) == 1
                    and good_attempts[0].status == "COMPLETED",
                    "replay_guard": replay_processed is False,
                    "duplicate_dispatch_deduplicated": duplicate_dispatch == "deduplicated",
                }

                bad_run = _create_run(
                    session,
                    organization,
                    case,
                    reference,
                    evaluation,
                    idempotency_key=f"local-failure-{token}",
                )
                missing_key = f"{token}/missing-evaluation.json"
                evaluation.object_key = missing_key
                session.commit()
                queue.enqueue(bad_run.id, organization.id, 0)
                bad_outbox = session.scalar(
                    select(GammaDispatchOutbox).where(
                        GammaDispatchOutbox.gamma_run_id == bad_run.id,
                        GammaDispatchOutbox.attempt_number == 0,
                    )
                )
                if bad_outbox is None:
                    raise RuntimeError("Failure run did not create a durable dispatch outbox")
                bad_outbox.status = "PUBLISHED"
                bad_outbox.published_at = datetime.now(UTC)
                session.commit()
                cleanup_run_ids.append(bad_run.id)

                retry_outputs: list[str] = []
                for expected_attempt in (1, 2, 3):
                    bad_run, worker_output = _run_worker_until_terminal(
                        session, bad_run.id, environment_base
                    )
                    retry_outputs.append(worker_output)
                    session.refresh(bad_run)
                    if expected_attempt < 3:
                        if bad_run.status != "RETRYING":
                            raise RuntimeError(
                                f"Expected RETRYING after attempt {expected_attempt}, "
                                f"got {bad_run.status}"
                            )
                        _publish_next_attempt(session, queue)
                    elif bad_run.status != "FAILED":
                        raise RuntimeError(
                            f"Expected FAILED after bounded retry, got {bad_run.status}"
                        )

                bad_attempts = list(
                    session.scalars(
                        select(GammaRunAttempt)
                        .where(GammaRunAttempt.gamma_run_id == bad_run.id)
                        .order_by(GammaRunAttempt.attempt_number)
                    )
                )
                dead_letter_entries = queue.client.xrange(queue.dead_letter_stream_name)
                queue_metrics = queue.metrics()
                failure_checks = {
                    "status": bad_run.status == "FAILED",
                    "bounded_attempts": bad_run.attempt_count == 3 and len(bad_attempts) == 3,
                    "attempts_terminal": all(item.status == "FAILED" for item in bad_attempts),
                    "dead_letter_written": len(dead_letter_entries) == 1,
                    "dead_letter_source": bool(
                        dead_letter_entries
                        and dead_letter_entries[0][1].get("source_message_id")
                        and dead_letter_entries[0][1].get("run_id") == str(bad_run.id)
                        and dead_letter_entries[0][1].get("attempt") == "2"
                    ),
                    "queue_acknowledged": int(queue_metrics["pending_count"]) == 0,
                }
                passed = all(good_checks.values()) and all(failure_checks.values())
                evidence: dict[str, Any] = {
                    "schema_version": "rt-connect.p8-local-redis-worker-smoke.v1",
                    "captured_at_utc": datetime.now(UTC).isoformat(),
                    "verification_level": "LOCAL_COMPOSE_REDIS_WORKER",
                    "synthetic_only": True,
                    "source_commit": _capture_commit(),
                    "topology": {
                        "database": "temporary SQLite file",
                        "queue": "local Redis 7 service",
                        "object_storage": "local MinIO disposable bucket",
                        "worker": "separate rt_connect_api.worker process",
                    },
                    "fixture": {
                        "payload_sha256": hashlib.sha256(payload).hexdigest(),
                        "grid_shape": [2, 2],
                        "organization_id": str(organization.id),
                        "case_id": str(case.id),
                    },
                    "happy_path": {
                        "run_id": str(good_run.id),
                        "checks": good_checks,
                    },
                    "bounded_retry_dead_letter": {
                        "run_id": str(bad_run.id),
                        "checks": failure_checks,
                        "worker_attempt_output_count": len(retry_outputs),
                    },
                    "queue_metrics_after_ack": queue_metrics,
                    "cleanup": (
                        "temporary database, stream, keys and MinIO bucket removed in finally"
                    ),
                    "passed": passed,
                }
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                if not passed:
                    raise RuntimeError(f"Local Gamma queue smoke failed: {evidence}")
                return evidence
    finally:
        if queue is not None:
            try:
                queue.client.delete(stream, queue.dead_letter_stream_name)
                dispatch_keys = [
                    f"{stream}:dispatch:{run_id}:{attempt}"
                    for run_id in cleanup_run_ids
                    for attempt in range(3)
                ]
                if dispatch_keys:
                    queue.client.delete(*dispatch_keys)
            except Exception:
                pass
        if storage is not None:
            _cleanup_storage(storage, bucket)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "docs" / "evidence" / "p8-local-redis-worker-smoke.json",
    )
    arguments = parser.parse_args()
    evidence = verify(arguments.output)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
