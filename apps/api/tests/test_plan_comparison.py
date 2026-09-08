from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from test_bed_eqd2 import _request, _saved_scenario, _scenario
from test_workspace import _workspace_client


def _create_calculation(
    client, organization, scenario_id: str, body: dict[str, object]
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/organizations/{organization.id}/biological/scenarios/{scenario_id}/calculations",
        json=body,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _comparison_body(
    calculation_a: dict[str, object],
    calculation_b: dict[str, object],
    *,
    key: str = "p14-api-idempotency-01",
) -> dict[str, object]:
    return {
        "name": "Synthetic plan comparison",
        "idempotency_key": key,
        "baseline_option_id": "A",
        "options": [
            {
                "option_id": "A",
                "label": "Option A · 60 Gy / 30 fx",
                "calculation_id": calculation_a["id"],
            },
            {
                "option_id": "B",
                "label": "Option B · 70 Gy / 35 fx",
                "calculation_id": calculation_b["id"],
            },
        ],
    }


def test_p14_validate_create_replay_history_chart_clone_and_export_are_snapshot_based() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        p13_a = _request(revision_id, "p13-p14-option-a-01")
        p13_b = _request(revision_id, "p13-p14-option-b-01")
        p13_b.update({"total_dose_gy": 70, "fractions": 35, "dose_per_fraction_gy": 2})
        calculation_a = _create_calculation(client, organization, scenario["id"], p13_a)
        calculation_b = _create_calculation(client, organization, scenario["id"], p13_b)
        base = f"/api/v1/organizations/{organization.id}/biological"
        body = _comparison_body(calculation_a, calculation_b)

        validation = client.post(f"{base}/comparisons/validate", json=body)
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True
        assert validation.json()["preview"]["point_count"] == 2
        assert client.get(f"{base}/comparisons").json()["total"] == 0

        created = client.post(f"{base}/comparisons", json=body)
        assert created.status_code == 201, created.text
        comparison = created.json()
        assert comparison["status"] == "COMPLETED"
        assert comparison["model_key"] == "biological.plan-comparison"
        assert comparison["result_snapshot"]["baseline_option_id"] == "A"
        assert comparison["result_snapshot"]["table_rows"][1]["delta_eqd2_gy"] == 10
        assert comparison["result_snapshot"]["chart_dataset"]["dataset_sha256"]

        replay = client.post(f"{base}/comparisons", json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == comparison["id"]
        assert client.get(f"{base}/comparisons").json()["total"] == 1

        conflict = deepcopy(body)
        conflict["name"] = "Changed input with reused key"
        conflict_response = client.post(f"{base}/comparisons", json=conflict)
        assert conflict_response.status_code == 409, conflict_response.text
        assert conflict_response.json()["code"] == "COMPARISON_IDEMPOTENCY_CONFLICT"

        detail = client.get(f"{base}/comparisons/{comparison['id']}")
        assert detail.status_code == 200, detail.text
        assert detail.json()["id"] == comparison["id"]

        chart = client.post(
            f"{base}/comparisons/{comparison['id']}/charts",
            json={"option_order": ["B", "A"]},
        )
        assert chart.status_code == 200, chart.text
        assert chart.json()["persisted"] is False
        assert chart.json()["option_order"] == ["B", "A"]
        assert [row["option_id"] for row in chart.json()["table_rows"]] == ["B", "A"]
        assert chart.json()["baseline_option_id"] == "A"
        assert (
            client.get(f"{base}/comparisons/{comparison['id']}").json()["result_snapshot"][
                "baseline_option_id"
            ]
            == "A"
        )

        bad_order = client.post(
            f"{base}/comparisons/{comparison['id']}/charts",
            json={"option_order": ["A", "A"]},
        )
        assert bad_order.status_code == 422, bad_order.text
        assert bad_order.json()["code"] == "COMPARISON_OPTION_INVALID"

        exported_json = client.get(
            f"{base}/comparisons/{comparison['id']}/export?export_format=JSON"
        )
        assert exported_json.status_code == 200
        assert exported_json.headers["content-type"].startswith("application/json")
        assert exported_json.json()["result_snapshot"]["chart_dataset"]["dataset_sha256"]

        exported_csv = client.get(f"{base}/comparisons/{comparison['id']}/export?export_format=CSV")
        assert exported_csv.status_code == 200
        assert exported_csv.headers["content-type"].startswith("text/csv")
        assert "delta_eqd2_percent_reason" in exported_csv.text
        assert exported_csv.text.count("\n") == 3

        cloned = client.post(
            f"{base}/comparisons/{comparison['id']}/clone",
            json={
                "idempotency_key": "p14-clone-idempotency-01",
                "name": "Synthetic comparison clone",
                "baseline_option_id": "B",
                "option_order": ["B", "A"],
            },
        )
        assert cloned.status_code == 201, cloned.text
        clone = cloned.json()
        assert clone["id"] != comparison["id"]
        assert clone["result_snapshot"]["baseline_option_id"] == "B"
        assert [row["option_id"] for row in clone["result_snapshot"]["table_rows"]] == ["B", "A"]
        assert client.get(f"{base}/comparisons").json()["total"] == 2


def test_p14_zero_baseline_and_alpha_beta_warning_are_explicit() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        zero = _request(revision_id, "p13-p14-zero-01")
        zero.update({"total_dose_gy": 0, "fractions": 1, "dose_per_fraction_gy": 0})
        other = _request(revision_id, "p13-p14-other-01")
        other["alpha_beta_gy"] = 3
        other["alpha_beta_source_reference"] = "Synthetic alpha/beta mismatch fixture"
        calculation_zero = _create_calculation(client, organization, scenario["id"], zero)
        calculation_other = _create_calculation(client, organization, scenario["id"], other)
        base = f"/api/v1/organizations/{organization.id}/biological"
        body = _comparison_body(calculation_zero, calculation_other, key="p14-zero-baseline-01")

        validation = client.post(f"{base}/comparisons/validate", json=body)
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True
        assert validation.json()["warnings"][0]["code"] == "COMPARISON_ALPHA_BETA_MISMATCH"
        rows = validation.json()["preview"]["table_rows"]
        assert rows[1]["delta_eqd2_percent"] is None
        assert rows[1]["delta_eqd2_percent_reason"] == "BASELINE_ZERO"

        created = client.post(f"{base}/comparisons", json=body)
        assert created.status_code == 201, created.text
        result = created.json()["result_snapshot"]
        assert result["compatibility"]["ranking_allowed"] is False
        assert result["ranking"] is None
        assert result["warnings"][0]["code"] == "COMPARISON_ALPHA_BETA_MISMATCH"


def test_p14_context_scope_and_order_errors_do_not_create_a_comparison() -> None:
    with _workspace_client() as (client, organization):
        scenario_a, revision_a = _saved_scenario(client, organization)
        created_other = client.post(
            f"/api/v1/organizations/{organization.id}/biological/scenarios",
            json=_scenario(key="P14_OTHER_SCENARIO"),
        )
        assert created_other.status_code == 201, created_other.text
        scenario_b = created_other.json()
        saved_other = client.post(
            f"/api/v1/organizations/{organization.id}/biological/scenarios/{scenario_b['id']}/save",
            json={"expected_revision": 1},
        )
        assert saved_other.status_code == 200, saved_other.text
        revision_b = client.get(
            f"/api/v1/organizations/{organization.id}/biological/scenarios/{scenario_b['id']}/revisions"
        ).json()[0]["id"]
        calculation_a = _create_calculation(
            client, organization, scenario_a["id"], _request(revision_a, "p13-p14-context-a-01")
        )
        calculation_b = _create_calculation(
            client, organization, scenario_b["id"], _request(revision_b, "p13-p14-context-b-01")
        )
        base = f"/api/v1/organizations/{organization.id}/biological"
        mismatch = _comparison_body(calculation_a, calculation_b, key="p14-context-mismatch-01")
        mismatch_result = client.post(f"{base}/comparisons/validate", json=mismatch)
        assert mismatch_result.status_code == 200, mismatch_result.text
        assert mismatch_result.json()["valid"] is False
        assert mismatch_result.json()["errors"][0]["code"] == "COMPARISON_CONTEXT_MISMATCH"
        assert client.get(f"{base}/comparisons").json()["total"] == 0

        duplicate = _comparison_body(calculation_a, calculation_a, key="p14-duplicate-01")
        duplicate_result = client.post(f"{base}/comparisons/validate", json=duplicate)
        assert duplicate_result.status_code == 200, duplicate_result.text
        assert duplicate_result.json()["valid"] is False
        assert duplicate_result.json()["errors"][0]["code"] == "COMPARISON_OPTION_INVALID"

        missing = _comparison_body(calculation_a, calculation_b, key="p14-order-missing-01")
        missing["options"][1]["calculation_id"] = str(uuid4())
        missing_result = client.post(f"{base}/comparisons/validate", json=missing)
        assert missing_result.status_code == 200, missing_result.text
        assert missing_result.json()["valid"] is False
        assert missing_result.json()["errors"][0]["code"] == "COMPARISON_OPTION_INVALID"

        invalid_order = client.post(
            f"{base}/comparisons/{uuid4()}/charts",
            json={"option_order": ["A", "B"]},
        )
        assert invalid_order.status_code == 404
        assert invalid_order.json()["code"] == "COMPARISON_NOT_FOUND"

        outsider = client.get(f"/api/v1/organizations/{uuid4()}/biological/comparisons")
        assert outsider.status_code == 403
        assert outsider.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"


def test_p14_request_shape_errors_use_shared_validation_envelope() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        calculation_a = _create_calculation(
            client, organization, scenario["id"], _request(revision_id, "p13-p14-shape-a-01")
        )
        calculation_b = _create_calculation(
            client, organization, scenario["id"], _request(revision_id, "p13-p14-shape-b-01")
        )
        body = _comparison_body(calculation_a, calculation_b, key="p14-shape-01")
        body["options"] = body["options"][:1]
        response = client.post(
            f"/api/v1/organizations/{organization.id}/biological/comparisons/validate",
            json=body,
        )
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "REQUEST_VALIDATION_FAILED"
