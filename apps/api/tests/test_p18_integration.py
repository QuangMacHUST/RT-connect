"""P18 release-candidate journeys across the real API boundaries.

These tests intentionally use the same FastAPI routes that the web client uses,
then inspect the persisted run through the worker boundary where an asynchronous
Gamma job is involved.  They are a deterministic local integration pack for
P18; they do not replace staging, pilot, backup/restore or production evidence.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from rt_connect_api.api.artifacts import _storage as artifact_storage
from rt_connect_api.api.gamma import _storage as gamma_storage
from rt_connect_api.api.gamma import process_gamma_run
from rt_connect_api.api.reports import _storage as report_storage
from rt_connect_api.db.models import GammaAnalysisRun
from rt_connect_api.db.session import get_session
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from test_bed_eqd2 import _request, _saved_scenario
from test_biological_library import _dose_limit
from test_gamma import _measurement_bytes
from test_machine_qa import _measurements
from test_plan_comparison import _comparison_body, _create_calculation
from test_re_irradiation import _reirradiation_body
from test_workspace import _workspace_client


@contextmanager
def _database_session(client: TestClient) -> Generator[Session]:
    """Open the same overridden database session used by the API test client."""

    dependency = client.app.dependency_overrides[get_session]
    session_generator = dependency()
    session = next(session_generator)
    try:
        yield session
    finally:
        session_generator.close()


def _qa_case(client: TestClient, organization_id: str) -> str:
    site = client.get(f"/api/v1/organizations/{organization_id}/sites").json()["items"][0]
    machine = client.get(
        f"/api/v1/organizations/{organization_id}/sites/{site['id']}/machines"
    ).json()["items"][0]
    root = client.post(
        f"/api/v1/organizations/{organization_id}/folders",
        json={"name": "P18 integrated QA"},
    )
    assert root.status_code == 201, root.text
    child = client.post(
        f"/api/v1/organizations/{organization_id}/folders",
        json={"name": "September run", "parent_folder_id": root.json()["id"]},
    )
    assert child.status_code == 201, child.text
    case = client.post(
        f"/api/v1/organizations/{organization_id}/qa-cases",
        json={
            "site_id": site["id"],
            "machine_id": machine["id"],
            "primary_folder_id": child.json()["id"],
            "qa_type": "PSQA Gamma",
            "qa_cycle": "CUSTOM",
            "performed_at": "2026-09-09T00:00:00Z",
            "title": "P18 integrated synthetic QA journey",
        },
    )
    assert case.status_code == 201, case.text
    return str(case.json()["id"])


def _report_blocks() -> list[dict[str, object]]:
    return [
        {
            "stable_block_id": "summary",
            "block_type": "TEXT",
            "label": "Integrated summary",
            "config": {"content": "P18 deterministic synthetic release journey."},
            "source_binding": {},
        },
        {
            "stable_block_id": "provenance",
            "block_type": "PROVENANCE",
            "label": "Provenance",
            "config": {"show_checksums": True},
            "source_binding": {"path": "source_snapshot.payload"},
        },
    ]


def test_p18_qa_journey_crosses_auth_case_artifact_gamma_machineqa_report_and_trend() -> None:
    """Exercise P18-S01 with a real route-to-persistence path."""

    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[gamma_storage] = lambda: storage
        client.app.dependency_overrides[report_storage] = lambda: storage

        bootstrap = client.get("/api/v1/session/bootstrap")
        assert bootstrap.status_code == 200, bootstrap.text
        assert bootstrap.json()["organization"]["id"] == str(organization.id)

        case_id = _qa_case(client, str(organization.id))
        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        )
        assert protocol.status_code == 201, protocol.text

        machine_run = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={
                "protocol_version_id": protocol.json()["id"],
                "measurements": _measurements(),
            },
        )
        assert machine_run.status_code == 201, machine_run.text
        evaluated = client.post(
            f"/api/v1/machine-qa-runs/{machine_run.json()['id']}/evaluate"
        )
        assert evaluated.status_code == 200, evaluated.text
        assert evaluated.json()["overall_status"] == "PASS"

        artifact_ids: dict[str, str] = {}
        for role, dataset_id in (("REFERENCE", "p18-reference"), ("EVALUATION", "p18-evaluation")):
            uploaded = client.post(
                f"/api/v1/qa-cases/{case_id}/artifacts",
                files={
                    "file": (
                        f"{dataset_id}.json",
                        _measurement_bytes(dataset_id, [1, 2, 3, 4]),
                        "application/json",
                    )
                },
                data={"artifact_type": "MEASUREMENT", "logical_role": role},
            )
            assert uploaded.status_code == 201, uploaded.text
            artifact_id = uploaded.json()["id"]
            artifact_ids[role] = artifact_id
            validation = client.post(f"/api/v1/artifacts/{artifact_id}/validate")
            assert validation.status_code == 200, validation.text
            assert validation.json()["result"] == "VALID"

        gamma = client.post(
            f"/api/v1/qa-cases/{case_id}/gamma-runs",
            json={
                "reference_artifact_id": artifact_ids["REFERENCE"],
                "evaluation_artifact_id": artifact_ids["EVALUATION"],
                "idempotency_key": "p18-integrated-gamma-001",
                "workflow_profile": "ENGINE_TEST",
                "configuration": {"dose_threshold_percent": 0},
            },
        )
        assert gamma.status_code == 201, gamma.text
        gamma_id = UUID(gamma.json()["id"])
        assert gamma.json()["status"] == "QUEUED"

        with _database_session(client) as session:
            gamma_row = session.get(GammaAnalysisRun, gamma_id)
            assert gamma_row is not None
            process_gamma_run(session, gamma_row, storage, retry_delay_seconds=0)

        completed_gamma = client.get(f"/api/v1/gamma-runs/{gamma_id}")
        assert completed_gamma.status_code == 200, completed_gamma.text
        assert completed_gamma.json()["status"] == "COMPLETED"
        assert completed_gamma.json()["result_snapshot"]["overall_status"] == "PASS"

        machine_report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "GAMMA",
                "source_id": str(gamma_id),
                "title": "P18 Gamma integrated report",
                "blocks": _report_blocks(),
            },
        )
        assert machine_report.status_code == 201, machine_report.text
        report = machine_report.json()
        assert report["source_snapshot"]["payload"]["status"] == "COMPLETED"

        exported = client.post(
            f"/api/v1/reports/{report['report_key']}/revisions/{report['id']}/exports",
            json={
                "export_format": "JSON",
                "idempotency_key": "p18-integrated-report-json-001",
            },
        )
        assert exported.status_code == 201, exported.text
        assert exported.json()["status"] == "COMPLETED"
        downloaded = client.get(f"/api/v1/report-exports/{exported.json()['id']}/download")
        assert downloaded.status_code == 200, downloaded.text
        assert downloaded.json()["sha256"] == exported.json()["sha256"]

        trend = client.get(f"/api/v1/organizations/{organization.id}/trend")
        assert trend.status_code == 200, trend.text
        assert trend.json()["total_points"] == 3
        assert {item["metric_key"] for item in trend.json()["series"]} == {
            "output_factor",
            "symmetry",
            "flatness",
        }
        rebuilt = client.post(f"/api/v1/organizations/{organization.id}/trend/rebuild")
        assert rebuilt.status_code == 200, rebuilt.text
        assert rebuilt.json()["created_points"] == 0
        assert rebuilt.json()["existing_points"] == 3


def test_p18_biological_journey_remains_independent_from_qa_namespace() -> None:
    """Exercise P18-S02 from library through calculation/comparison/re-irradiation."""

    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[report_storage] = lambda: storage
        base = f"/api/v1/organizations/{organization.id}/biological"

        library = client.post(
            f"{base}/library",
            json=_dose_limit(key="P18_SYNTHETIC_DOSE_LIMIT"),
        )
        assert library.status_code == 201, library.text
        published = client.post(
            f"{base}/library/{library.json()['id']}/publish",
            json={"expected_revision": 1},
        )
        assert published.status_code == 200, published.text
        used = client.post(
            f"{base}/library/{library.json()['id']}/use",
            json={"target_tool": "KNOWLEDGE_REFERENCE"},
        )
        assert used.status_code == 200, used.text
        assert used.json()["source_snapshot"]["status"] == "PUBLISHED"

        scenario, revision_id = _saved_scenario(client, organization)
        calculation_a = _create_calculation(
            client,
            organization,
            scenario["id"],
            _request(revision_id, "p18-biological-option-a-001"),
        )
        option_b = _request(revision_id, "p18-biological-option-b-001")
        option_b.update({"total_dose_gy": 70, "fractions": 35, "dose_per_fraction_gy": 2})
        calculation_b = _create_calculation(client, organization, scenario["id"], option_b)

        comparison = client.post(
            f"{base}/comparisons",
            json=_comparison_body(calculation_a, calculation_b, key="p18-comparison-001"),
        )
        assert comparison.status_code == 201, comparison.text
        assert comparison.json()["result_snapshot"]["table_rows"][1]["delta_eqd2_gy"] == 10

        reirradiation = client.post(
            f"{base}/scenarios/{scenario['id']}/re-irradiation",
            json=_reirradiation_body(revision_id, key="p18-reirradiation-001"),
        )
        assert reirradiation.status_code == 201, reirradiation.text
        assert reirradiation.json()["operation_type"] == "REIRRADIATION"

        report = client.post(
            f"/api/v1/organizations/{organization.id}/reports",
            json={
                "source_type": "BIOLOGICAL",
                "source_id": str(comparison.json()["id"]),
                "title": "P18 independent biological report",
                "blocks": _report_blocks(),
            },
        )
        assert report.status_code == 201, report.text
        source_payload = report.json()["source_snapshot"]["payload"]
        assert source_payload["namespace"] == "BIOLOGICAL_TOOLKIT"
        assert source_payload["source_id"] == str(comparison.json()["id"])
        assert "qa_case_id" not in source_payload

        biological_summary = client.get(f"{base}/summary")
        assert biological_summary.status_code == 200, biological_summary.text
        assert biological_summary.json()["completed_calculations"] == 2
