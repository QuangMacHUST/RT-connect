from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from rt_connect_api.api.gamma import acquire_gamma_run_lease, process_gamma_run
from rt_connect_api.db.base import Base
from rt_connect_api.db.models import (
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
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from rt_connect_api.worker import recover_stale_runs


def _dataset(dataset_id: str, values: list[float]) -> bytes:
    return json.dumps(
        {
            "schema_version": "gamma.measurement.v1",
            "dataset_id": dataset_id,
            "data_type": "dose",
            "units": {"dose": "GY", "position": "mm"},
            "grid": {"shape": [2, 2], "spacing_mm": [1.0, 1.0]},
            "values": {"encoding": "inline-float32", "inline": values},
        }
    ).encode("utf-8")


def _run_fixture() -> tuple[Session, InMemoryObjectStorage, GammaAnalysisRun]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine, expire_on_commit=False)
    organization = Organization(name=f"Gamma Worker {uuid4()}")
    site = Site(name="Synthetic Site", organization=organization)
    session.add_all([organization, site])
    session.flush()
    machine = Machine(
        organization_id=organization.id,
        site_id=site.id,
        stable_machine_id=f"GAMMA-{uuid4()}",
        display_name="Synthetic Gamma Machine",
    )
    folder = Folder(organization_id=organization.id, name="Gamma")
    session.add_all([machine, folder])
    session.flush()
    case = QACase(
        organization_id=organization.id,
        site_id=site.id,
        machine_id=machine.id,
        primary_folder_id=folder.id,
        qa_type="PSQA Gamma",
        qa_cycle="CUSTOM",
        performed_at=datetime(2026, 9, 7),
        title="Synthetic Gamma worker case",
    )
    session.add(case)
    session.flush()
    storage = InMemoryObjectStorage()
    reference_payload = _dataset("reference", [1, 2, 3, 4])
    evaluation_payload = _dataset("evaluation", [1, 2, 3, 4])
    reference = Artifact(
        organization_id=organization.id,
        qa_case_id=case.id,
        artifact_type="MEASUREMENT",
        original_filename="reference.json",
        object_key="reference-key",
        byte_size=len(reference_payload),
        media_type="application/json",
        sha256=hashlib.sha256(reference_payload).hexdigest(),
        data_status="VALID",
        metadata_snapshot={"grid": {"shape": [2, 2]}},
    )
    evaluation = Artifact(
        organization_id=organization.id,
        qa_case_id=case.id,
        artifact_type="MEASUREMENT",
        original_filename="evaluation.json",
        object_key="evaluation-key",
        byte_size=len(evaluation_payload),
        media_type="application/json",
        sha256=hashlib.sha256(evaluation_payload).hexdigest(),
        data_status="VALID",
        metadata_snapshot={"grid": {"shape": [2, 2]}},
    )
    session.add_all([reference, evaluation])
    session.flush()
    session.add_all(
        [
            InputManifest(
                organization_id=organization.id,
                artifact_id=reference.id,
                logical_role="REFERENCE",
                checksum_at_use=reference.sha256,
                selected_metadata=reference.metadata_snapshot,
                geometry_summary={"shape": [2, 2]},
                unit_summary={"dose_units": "GY"},
                validation_summary={"result": "VALID"},
            ),
            InputManifest(
                organization_id=organization.id,
                artifact_id=evaluation.id,
                logical_role="EVALUATION",
                checksum_at_use=evaluation.sha256,
                selected_metadata=evaluation.metadata_snapshot,
                geometry_summary={"shape": [2, 2]},
                unit_summary={"dose_units": "GY"},
                validation_summary={"result": "VALID"},
            ),
        ]
    )
    session.flush()
    storage.objects[reference.object_key] = reference_payload
    storage.objects[evaluation.object_key] = evaluation_payload
    run = GammaAnalysisRun(
        organization_id=organization.id,
        qa_case_id=case.id,
        reference_artifact_id=reference.id,
        evaluation_artifact_id=evaluation.id,
        idempotency_key="worker-test-001",
        request_fingerprint="c" * 64,
        status="QUEUED",
        engine_version="gamma-2d-p8.1",
        config_snapshot={
            "dimensionality": "2D",
            "dose_difference_percent": 3.0,
            "dose_difference_mode": "RELATIVE",
            "absolute_dose_difference_gy": None,
            "distance_to_agreement_mm": 3.0,
            "dose_threshold_percent": 0.0,
            "normalization": "GLOBAL",
            "interpolation": "GRID",
            "pass_rate_threshold_percent": 95.0,
            "histogram_bins": 10,
        },
        input_manifest_snapshot={
            "reference": {
                "artifact_id": str(reference.id),
                "sha256": reference.sha256,
            },
            "evaluation": {
                "artifact_id": str(evaluation.id),
                "sha256": evaluation.sha256,
            },
        },
        result_snapshot={},
        error_snapshot=[],
        warning_snapshot=[],
    )
    session.add(run)
    session.commit()
    return session, storage, run


def test_worker_completes_queued_gamma_run_and_persists_result() -> None:
    session, storage, run = _run_fixture()
    try:
        process_gamma_run(session, run, storage)
        assert run.status == "COMPLETED"
        assert run.progress_percent == 100
        assert run.attempt_count == 1
        assert run.result_snapshot["overall_status"] == "PASS"
        assert run.result_snapshot["metrics"]["pass_rate_percent"] == 100.0
    finally:
        session.close()


def test_worker_records_deterministic_engine_failure() -> None:
    session, storage, run = _run_fixture()
    invalid_payload = b"{}"
    storage.objects["evaluation-key"] = invalid_payload
    run.input_manifest_snapshot = {
        **run.input_manifest_snapshot,
        "evaluation": {
            **run.input_manifest_snapshot["evaluation"],
            "sha256": hashlib.sha256(invalid_payload).hexdigest(),
        },
    }
    session.commit()
    try:
        process_gamma_run(session, run, storage)
        assert run.status == "FAILED"
        assert run.error_snapshot[0]["code"] == "GAMMA_SCHEMA_UNSUPPORTED"
    finally:
        session.close()


def test_only_one_worker_can_hold_a_gamma_lease() -> None:
    session, storage, run = _run_fixture()
    try:
        first_token = acquire_gamma_run_lease(session, run, "worker-a")
        assert first_token is not None
        assert acquire_gamma_run_lease(session, run, "worker-b") is None

        process_gamma_run(session, run, storage, lease_token=first_token, worker_id="worker-a")
        assert run.status == "COMPLETED"
        attempts = list(
            session.scalars(
                select(GammaRunAttempt).where(GammaRunAttempt.gamma_run_id == run.id)
            )
        )
        assert len(attempts) == 1
        assert attempts[0].status == "COMPLETED"

        # A stale completion callback cannot reopen or overwrite a terminal run.
        process_gamma_run(session, run, storage, lease_token=first_token, worker_id="worker-a")
        assert run.status == "COMPLETED"
    finally:
        session.close()


def test_stale_worker_is_fenced_and_requeued_with_a_new_outbox_intent() -> None:
    session, storage, run = _run_fixture()
    del storage
    try:
        token = acquire_gamma_run_lease(session, run, "worker-a")
        assert token is not None
        run.heartbeat_at = datetime.now(UTC) - timedelta(minutes=30)
        session.commit()

        assert recover_stale_runs(session, timeout_seconds=60) == 1
        session.refresh(run)
        assert run.status == "RETRYING"
        assert run.lease_token is None
        attempt = session.scalar(
            select(GammaRunAttempt).where(GammaRunAttempt.gamma_run_id == run.id)
        )
        assert attempt is not None
        assert attempt.status == "FAILED"
        outbox = session.scalar(
            select(GammaDispatchOutbox).where(GammaDispatchOutbox.gamma_run_id == run.id)
        )
        assert outbox is not None
        assert outbox.attempt_number == run.attempt_count
        assert outbox.status == "PENDING"
    finally:
        session.close()
