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
        protocol_body = protocol.json()
        assert len(protocol_body["rules"]) == 3
        seeded_again = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        )
        assert seeded_again.status_code == 201, seeded_again.text
        assert seeded_again.json()["id"] == protocol_body["id"]
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

        evaluated = client.post(
            f"/api/v1/machine-qa-runs/{run['id']}/evaluate",
            json={"expected_revision": 1},
        )
        assert evaluated.status_code == 200, evaluated.text
        assert evaluated.json()["status"] == "COMPLETED"
        assert evaluated.json()["overall_status"] == "PASS"
        assert {item["status"] for item in evaluated.json()["result_snapshot"]["metrics"]} == {
            "PASS"
        }
        snapshot = evaluated.json()["result_snapshot"]["protocol_snapshot"]
        assert snapshot["schema_version"] == "p11.protocol-snapshot.v1"
        assert snapshot["status_at_use"] == "ACTIVE"
        assert snapshot["source"] == {
            "type": protocol_body["source_type"],
            "reference": protocol_body["source_reference"],
            "source_protocol_version_id": protocol_body["source_protocol_version_id"],
        }
        assert snapshot["capability"]["status"] == "SUPPORTED"
        assert len(snapshot["rules"]) == 3
        assert all(
            {"metric_key", "unit", "rule_type", "target_value", "lower_limit", "upper_limit"}
            <= set(rule)
            for rule in snapshot["rules"]
        )

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


def test_machine_qa_evaluate_revision_conflict_and_idempotent_replay() -> None:
    with _workspace_client() as (client, organization):
        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        ).json()
        case_id = _case(client, str(organization.id), "Machine QA evaluate revision")
        created = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={"protocol_version_id": protocol["id"]},
        )
        assert created.status_code == 201, created.text
        run = created.json()

        stale = client.post(
            f"/api/v1/machine-qa-runs/{run['id']}/evaluate",
            json={"expected_revision": 1},
        )
        assert stale.status_code == 409, stale.text
        assert stale.json()["code"] == "MACHINE_QA_REVISION_CONFLICT"

        saved = client.patch(
            f"/api/v1/machine-qa-runs/{run['id']}/measurements",
            json={"expected_revision": 0, "measurements": _measurements()},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["measurement_revision"] == 1

        first = client.post(
            f"/api/v1/machine-qa-runs/{run['id']}/evaluate",
            json={"expected_revision": 1},
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["status"] == "COMPLETED"

        replay = client.post(
            f"/api/v1/machine-qa-runs/{run['id']}/evaluate",
            json={"expected_revision": 1},
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == first_body["id"]
        assert replay.json()["result_snapshot"] == first_body["result_snapshot"]

        trend = client.get(f"/api/v1/organizations/{organization.id}/trend")
        assert trend.status_code == 200, trend.text
        assert trend.json()["total_points"] == 3


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


def test_machine_qa_explicit_na_keeps_reason_and_excludes_metric_from_trend() -> None:
    with _workspace_client() as (client, organization):
        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        ).json()
        case_id = _case(client, str(organization.id), "Machine QA N/A")
        measurements = _measurements()
        measurements[0] = {
            "metric_key": "output_factor",
            "value": None,
            "unit": "%",
            "is_not_applicable": True,
            "na_reason": "Output detector was not available for this QA cycle.",
        }
        created = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={"protocol_version_id": protocol["id"], "measurements": measurements},
        )
        assert created.status_code == 201, created.text

        evaluated = client.post(f"/api/v1/machine-qa-runs/{created.json()['id']}/evaluate")
        assert evaluated.status_code == 200, evaluated.text
        body = evaluated.json()
        assert body["status"] == "COMPLETED"
        assert body["overall_status"] == "NA"
        output_factor = next(
            item
            for item in body["result_snapshot"]["metrics"]
            if item["metric_key"] == "output_factor"
        )
        assert output_factor["status"] == "NA"
        assert output_factor["actual"] is None
        assert output_factor["is_not_applicable"] is True
        assert output_factor["na_reason"] == (
            "Output detector was not available for this QA cycle."
        )

        replay = client.post(f"/api/v1/machine-qa-runs/{created.json()['id']}/evaluate")
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == body["id"]

        trend = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={"metric_key": "output_factor"},
        )
        assert trend.status_code == 200, trend.text
        assert trend.json()["total_points"] == 0
        assert trend.json()["series"] == []
        assert any(
            warning.startswith("TREND_EMPTY") for warning in trend.json()["warnings"]
        )

        numeric_trend = client.get(
            f"/api/v1/organizations/{organization.id}/trend",
            params={"metric_key": "symmetry"},
        )
        assert numeric_trend.status_code == 200, numeric_trend.text
        assert numeric_trend.json()["total_points"] == 1


def test_machine_qa_na_requires_reason_and_cannot_have_numeric_value() -> None:
    with _workspace_client() as (client, organization):
        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        ).json()
        case_id = _case(client, str(organization.id), "Machine QA N/A validation")

        missing_reason = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={
                "protocol_version_id": protocol["id"],
                "measurements": [
                    {
                        "metric_key": "output_factor",
                        "value": None,
                        "unit": "%",
                        "is_not_applicable": True,
                        "na_reason": "  ",
                    }
                ],
            },
        )
        assert missing_reason.status_code == 422, missing_reason.text
        assert missing_reason.json()["code"] == "MACHINE_QA_NA_REASON_REQUIRED"
        assert missing_reason.json()["details"][0]["field"] == (
            "measurements.0.na_reason"
        )

        numeric_value = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={
                "protocol_version_id": protocol["id"],
                "measurements": [
                    {
                        "metric_key": "output_factor",
                        "value": 100,
                        "unit": "%",
                        "is_not_applicable": True,
                        "na_reason": "Detector unavailable.",
                    }
                ],
            },
        )
        assert numeric_value.status_code == 422, numeric_value.text
        assert numeric_value.json()["code"] == "MACHINE_QA_NA_VALUE_CONFLICT"

        reason_without_flag = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={
                "protocol_version_id": protocol["id"],
                "measurements": [
                    {
                        "metric_key": "output_factor",
                        "value": None,
                        "unit": "%",
                        "na_reason": "Detector unavailable.",
                    }
                ],
            },
        )
        assert reason_without_flag.status_code == 422, reason_without_flag.text
        assert reason_without_flag.json()["code"] == "MACHINE_QA_NA_REASON_INVALID"


def test_machine_qa_fail_takes_precedence_over_explicit_na() -> None:
    with _workspace_client() as (client, organization):
        protocol = client.post(
            f"/api/v1/organizations/{organization.id}/machine-qa/protocols/seed"
        ).json()
        case_id = _case(client, str(organization.id), "Machine QA status precedence")
        measurements = _measurements()
        measurements[0] = {
            "metric_key": "output_factor",
            "value": None,
            "unit": "%",
            "is_not_applicable": True,
            "na_reason": "Output detector was not available for this QA cycle.",
        }
        measurements[1]["value"] = 6.0
        created = client.post(
            f"/api/v1/qa-cases/{case_id}/machine-qa-runs",
            json={"protocol_version_id": protocol["id"], "measurements": measurements},
        )
        assert created.status_code == 201, created.text

        evaluated = client.post(f"/api/v1/machine-qa-runs/{created.json()['id']}/evaluate")
        assert evaluated.status_code == 200, evaluated.text
        body = evaluated.json()
        assert body["status"] == "COMPLETED"
        assert body["overall_status"] == "FAIL"
        statuses = {
            item["metric_key"]: item["status"]
            for item in body["result_snapshot"]["metrics"]
        }
        assert statuses["output_factor"] == "NA"
        assert statuses["symmetry"] == "FAIL"
