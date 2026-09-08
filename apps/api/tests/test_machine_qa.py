from __future__ import annotations

from test_workspace import _workspace_client


def _case(client, organization_id: str, folder_name: str = "Machine QA") -> str:
    site = client.get(f"/api/v1/organizations/{organization_id}/sites").json()["items"][0]
    machine = client.get(
        f"/api/v1/organizations/{organization_id}/sites/{site['id']}/machines"
    ).json()["items"][0]
    folder = client.post(
        f"/api/v1/organizations/{organization_id}/folders", json={"name": folder_name}
    )
    assert folder.status_code == 201, folder.text
    case = client.post(
        f"/api/v1/organizations/{organization_id}/qa-cases",
        json={
            "site_id": site["id"],
            "machine_id": machine["id"],
            "primary_folder_id": folder.json()["id"],
            "qa_type": "Machine QA",
            "qa_cycle": "DAILY",
            "performed_at": "2026-09-07T00:00:00Z",
            "title": "Synthetic machine QA",
        },
    )
    assert case.status_code == 201, case.text
    return case.json()["id"]


def _measurements(output_factor: float = 100.0) -> list[dict[str, object]]:
    return [
        {"metric_key": "output_factor", "value": output_factor, "unit": "%"},
        {"metric_key": "symmetry", "value": 1.0, "unit": "%"},
        {"metric_key": "flatness", "value": 100.0, "unit": "%"},
    ]


def test_machine_qa_protocol_run_evaluate_rerun_and_compare() -> None:
    with _workspace_client() as (client, organization):
        protocol = client.post(f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed")
        assert protocol.status_code == 201, protocol.text
        assert len(protocol.json()["rules"]) == 3
        case_id = _case(client, str(organization.id))

        created = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={"protocol_version_id": protocol.json()["id"]},
        )
        assert created.status_code == 201, created.text
        run = created.json()
        assert run["status"] == "DRAFT"

        draft = client.patch(
            f"/api/v1/machine-qa-runs/{run['id']}/measurements",
            json={"expected_revision": 0, "measurements": _measurements()},
        )
        assert draft.status_code == 200, draft.text
        assert draft.json()["measurement_revision"] == 1

        evaluated = client.post(f"/api/v1/machine-qa-runs/{run['id']}/evaluate")
        assert evaluated.status_code == 200, evaluated.text
        assert evaluated.json()["status"] == "COMPLETED"
        assert evaluated.json()["overall_status"] == "PASS"
        assert {item["status"] for item in evaluated.json()["result_snapshot"]["metrics"]} == {
            "PASS"
        }

        rerun = client.post(f"/api/v1/machine-qa-runs/{run['id']}/rerun")
        assert rerun.status_code == 201, rerun.text
        assert rerun.json()["supersedes_run_id"] == run["id"]
        comparison = client.get(
            f"/api/v1/machine-qa-runs/{run['id']}/compare",
            params={"other_run_id": rerun.json()["id"]},
        )
        assert comparison.status_code == 200, comparison.text
        assert {item["metric_key"] for item in comparison.json()["items"]} == {
            "output_factor",
            "symmetry",
            "flatness",
        }

        history = client.get(f"/api/v1/qa-cases/{case_id}/machine-qa-runs")
        assert history.status_code == 200
        assert history.json()["total"] == 2


def test_machine_qa_explains_unit_and_required_measurement_failures() -> None:
    with _workspace_client() as (client, organization):
        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        ).json()
        case_id = _case(client, str(organization.id))
        created = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={
                "protocol_version_id": protocol["id"],
                "measurements": [{"metric_key": "output_factor", "value": 100, "unit": "Gy"}],
            },
        )
        assert created.status_code == 201, created.text
        evaluated = client.post(f"/api/v1/machine-qa-runs/{created.json()['id']}/evaluate")
        assert evaluated.status_code == 200, evaluated.text
        body = evaluated.json()
        assert body["status"] == "FAILED"
        assert {error["code"] for error in body["error_snapshot"]} == {
            "MACHINE_QA_UNIT_MISMATCH",
            "MACHINE_QA_MEASUREMENT_MISSING",
        }


def test_machine_qa_rule_boundary_returns_warning_and_fail() -> None:
    with _workspace_client() as (client, organization):
        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        ).json()
        case_id = _case(client, str(organization.id))
        created = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={
                "protocol_version_id": protocol["id"],
                "measurements": _measurements(102.5),
            },
        )
        assert created.status_code == 201, created.text
        warning = client.post(f"/api/v1/machine-qa-runs/{created.json()['id']}/evaluate")
        assert warning.json()["overall_status"] == "WARNING"

        case_2 = _case(client, str(organization.id), "Machine QA second")
        failed = client.post(
            f"/api/v1/qa-cases/{case_2}/machine-qa-runs",
            json={
                "protocol_version_id": protocol["id"],
                "measurements": _measurements(104),
            },
        )
        assert failed.status_code == 201, failed.text
        result = client.post(f"/api/v1/machine-qa-runs/{failed.json()['id']}/evaluate")
        assert result.json()["overall_status"] == "FAIL"
