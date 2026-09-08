from __future__ import annotations

from uuid import uuid4

from test_workspace import _workspace_client


def _scenario(key: str = "P13_SCENARIO") -> dict[str, object]:
    return {
        "scenario_key": key,
        "name": "P13 synthetic BED scenario",
        "scenario_type": "BED_EQD2",
        "tissue_context": "Synthetic tissue context",
        "clinical_context": "Development-only synthetic data; no patient identifiers.",
        "source_type": "USER_DEFINED",
        "source_reference": "Synthetic P13 fixture",
        "assumptions": {"purpose": "known-answer-test"},
    }


def _saved_scenario(client, organization) -> tuple[dict[str, object], str]:
    base = f"/api/v1/organizations/{organization.id}/biological"
    created = client.post(f"{base}/scenarios", json=_scenario())
    assert created.status_code == 201, created.text
    saved = client.post(
        f"{base}/scenarios/{created.json()['id']}/save",
        json={"expected_revision": 1},
    )
    assert saved.status_code == 200, saved.text
    revisions = client.get(f"{base}/scenarios/{created.json()['id']}/revisions")
    assert revisions.status_code == 200, revisions.text
    revision = next(item for item in revisions.json() if item["status"] == "SAVED")
    return saved.json(), revision["id"]


def _request(revision_id: str, key: str = "p13-api-idempotency-01") -> dict[str, object]:
    return {
        "scenario_revision_id": revision_id,
        "idempotency_key": key,
        "total_dose_gy": 60,
        "fractions": 30,
        "dose_per_fraction_gy": 2,
        "consistency_tolerance_gy": 0.01,
        "alpha_beta_gy": 10,
        "alpha_beta_source_type": "USER_DEFINED",
        "alpha_beta_source_reference": "Synthetic P13 fixture",
        "curve": {
            "mode": "FIXED_N",
            "dose_min_gy": 0,
            "dose_max_gy": 100,
            "dose_step_gy": 1,
            "alpha_beta_values_gy": [2, 3, 10],
            "point_limit": 501,
        },
    }


def test_p13_validate_calculate_replay_chart_and_export_are_snapshot_based() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        base = f"/api/v1/organizations/{organization.id}/biological"
        body = _request(revision_id)

        validation = client.post(
            f"{base}/scenarios/{scenario['id']}/calculations/validate", json=body
        )
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True
        assert validation.json()["preview"]["point_count"] == 303
        assert client.get(f"{base}/calculations?scenario_id={scenario['id']}").json()["total"] == 0

        created = client.post(f"{base}/scenarios/{scenario['id']}/calculations", json=body)
        assert created.status_code == 201, created.text
        calculation = created.json()
        assert calculation["calculation_type"] == "BED_EQD2"
        assert calculation["idempotency_key"] == body["idempotency_key"]
        assert calculation["result_snapshot"]["primary"]["bed_gy"] == 72
        assert calculation["result_snapshot"]["primary"]["eqd2_gy"] == 60
        assert calculation["result_snapshot"]["chart_dataset"]["point_count"] == 303

        replay = client.post(f"{base}/scenarios/{scenario['id']}/calculations", json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == calculation["id"]
        assert client.get(f"{base}/calculations?scenario_id={scenario['id']}").json()["total"] == 1

        conflict = dict(body)
        conflict["alpha_beta_gy"] = 3
        conflict_response = client.post(
            f"{base}/scenarios/{scenario['id']}/calculations", json=conflict
        )
        assert conflict_response.status_code == 409
        assert conflict_response.json()["code"] == "CALCULATION_IDEMPOTENCY_CONFLICT"

        chart = client.post(
            f"{base}/calculations/{calculation['id']}/charts",
            json={
                "curve": {
                    "mode": "FIXED_D",
                    "dose_min_gy": 0,
                    "dose_max_gy": 20,
                    "dose_step_gy": 2,
                    "alpha_beta_values_gy": [10],
                    "point_limit": 20,
                }
            },
        )
        assert chart.status_code == 200, chart.text
        assert chart.json()["persisted"] is False
        assert chart.json()["chart_dataset"]["point_count"] == 10
        assert len(chart.json()["table_rows"]) == 10

        exported_json = client.get(
            f"{base}/calculations/{calculation['id']}/export?export_format=JSON"
        )
        assert exported_json.status_code == 200
        assert exported_json.headers["content-type"].startswith("application/json")
        assert exported_json.json()["result_snapshot"]["chart_dataset"]["dataset_sha256"]

        exported_csv = client.get(
            f"{base}/calculations/{calculation['id']}/export?export_format=CSV"
        )
        assert exported_csv.status_code == 200
        assert "total_dose_gy" in exported_csv.text
        assert exported_csv.text.count("\n") == 304


def test_p13_validation_errors_scope_and_zero_dose_are_explicit() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        base = f"/api/v1/organizations/{organization.id}/biological"

        mismatch = _request(revision_id, "p13-mismatch-01")
        mismatch["dose_per_fraction_gy"] = 3
        mismatch_result = client.post(
            f"{base}/scenarios/{scenario['id']}/calculations/validate", json=mismatch
        )
        assert mismatch_result.status_code == 200
        assert mismatch_result.json()["valid"] is False
        assert mismatch_result.json()["errors"][0]["code"] == "FRACTIONATION_INCONSISTENT"

        zero = _request(revision_id, "p13-zero-dose-01")
        zero.update({"total_dose_gy": 0, "fractions": 10, "dose_per_fraction_gy": 0})
        zero_result = client.post(
            f"{base}/scenarios/{scenario['id']}/calculations/validate", json=zero
        )
        assert zero_result.status_code == 200
        assert zero_result.json()["valid"] is True
        assert zero_result.json()["preview"]["primary"]["bed_gy"] == 0

        bad_curve = _request(revision_id, "p13-curve-error-01")
        bad_curve["curve"] = {**bad_curve["curve"], "point_limit": 1}
        bad_curve_result = client.post(
            f"{base}/scenarios/{scenario['id']}/calculations/validate", json=bad_curve
        )
        assert bad_curve_result.status_code == 200
        assert bad_curve_result.json()["errors"][0]["code"] == "CURVE_RANGE_INVALID"

        outsider = client.get(f"/api/v1/organizations/{uuid4()}/biological/scenarios")
        assert outsider.status_code == 403
        assert outsider.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"
