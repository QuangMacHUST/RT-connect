from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from test_bed_eqd2 import _saved_scenario
from test_workspace import _workspace_client


def _reirradiation_body(revision_id: str, key: str = "p15-reirradiation-01") -> dict[str, object]:
    tissue = {
        "tissue_key": "TARGET",
        "dose_metric": "TOTAL",
        "dose_unit": "Gy",
        "total_dose_gy": 60,
        "fractions": 30,
        "dose_per_fraction_gy": 2,
        "alpha_beta_gy": 10,
        "alpha_beta_source_type": "USER_DEFINED",
        "alpha_beta_source_reference": "Synthetic P15 alpha/beta fixture",
    }
    current_tissue = {**tissue, "total_dose_gy": 50, "fractions": 25}
    return {
        "scenario_revision_id": revision_id,
        "name": "Synthetic P15 re-irradiation",
        "idempotency_key": key,
        "courses": [
            {
                "course_id": "course-prior",
                "label": "Prior course",
                "is_prior": True,
                "start_date": "2020-01-01",
                "end_date": "2020-02-15",
                "tissue_doses": [tissue],
            },
            {
                "course_id": "course-current",
                "label": "Current course",
                "is_prior": False,
                "start_date": "2026-01-01",
                "end_date": "2026-02-15",
                "tissue_doses": [current_tissue],
            },
        ],
        "recovery_model": {"mode": "NONE"},
        "sensitivity_recovery_fractions": [0, 0.5, 1],
        "spatial": {"requested": True},
    }


def _compensation_body(revision_id: str, key: str = "p15-compensation-01") -> dict[str, object]:
    return {
        "scenario_revision_id": revision_id,
        "name": "Synthetic P15 fraction compensation",
        "idempotency_key": key,
        "planned_fraction_doses_gy": [2, 2, 2, 2, 2],
        "delivered_fraction_doses_gy": [2, 2],
        "alpha_beta_gy": 10,
        "alpha_beta_source_type": "USER_DEFINED",
        "alpha_beta_source_reference": "Synthetic P15 compensation fixture",
        "alternatives": [
            {
                "alternative_id": "baseline-remaining",
                "label": "Continue original schedule",
                "remaining_fraction_doses_gy": [2, 2, 2],
            },
            {
                "alternative_id": "conservative",
                "label": "Alternative remaining schedule",
                "remaining_fraction_doses_gy": [2.5, 2.5, 1],
            },
        ],
        "interruptions": [
            {"start_date": "2026-01-10", "end_date": "2026-01-12", "label": "Machine service"}
        ],
        "time_model": {"mode": "NONE"},
    }


def test_p15_reirradiation_validate_save_replay_detail_history_and_export() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        base = f"/api/v1/organizations/{organization.id}/biological"
        body = _reirradiation_body(revision_id)
        validation = client.post(
            f"{base}/scenarios/{scenario['id']}/re-irradiation/validate", json=body
        )
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True
        assert validation.json()["preview"]["group_count"] == 1
        assert validation.json()["warnings"][0]["code"] == "SPATIAL_ACCUMULATION_UNAVAILABLE"
        assert client.get(f"{base}/re-irradiation").json()["total"] == 0

        created = client.post(f"{base}/scenarios/{scenario['id']}/re-irradiation", json=body)
        assert created.status_code == 201, created.text
        run = created.json()
        assert run["operation_type"] == "REIRRADIATION"
        assert run["model_key"] == "biological.re-irradiation"
        group = run["result_snapshot"]["groups"][0]
        assert group["bed_no_recovery_gy"] == 132
        assert group["eqd2_no_recovery_gy"] == 110
        assert run["result_snapshot"]["capability"]["spatial_result"] is None

        replay = client.post(f"{base}/scenarios/{scenario['id']}/re-irradiation", json=body)
        assert replay.status_code == 200, replay.text
        assert replay.json()["id"] == run["id"]
        assert client.get(f"{base}/re-irradiation").json()["total"] == 1

        conflict = deepcopy(body)
        conflict["name"] = "Changed P15 input"
        conflict_response = client.post(
            f"{base}/scenarios/{scenario['id']}/re-irradiation", json=conflict
        )
        assert conflict_response.status_code == 409, conflict_response.text
        assert conflict_response.json()["code"] == "P15_IDEMPOTENCY_CONFLICT"

        detail = client.get(f"{base}/re-irradiation/{run['id']}")
        assert detail.status_code == 200
        assert detail.json()["result_snapshot"]["result_sha256"]
        exported_json = client.get(f"{base}/re-irradiation/{run['id']}/export?export_format=JSON")
        assert exported_json.status_code == 200
        assert exported_json.json()["result_snapshot"]["result_sha256"]
        exported_csv = client.get(f"{base}/re-irradiation/{run['id']}/export?export_format=CSV")
        assert exported_csv.status_code == 200
        assert "bed_with_recovery_gy" in exported_csv.text


def test_p15_reirradiation_recovery_and_context_warnings_are_explicit() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        base = f"/api/v1/organizations/{organization.id}/biological"
        body = _reirradiation_body(revision_id, "p15-recovery-01")
        body["recovery_model"] = {"mode": "USER_DEFINED", "evaluation_date": "2026-03-01"}
        courses = body["courses"]
        assert isinstance(courses, list)
        prior = courses[0]
        assert isinstance(prior, dict)
        prior["recovery_fraction"] = 0.5
        prior["recovery_source_type"] = "USER_DEFINED"
        prior["recovery_source_reference"] = "Synthetic 50 percent recovery assumption"
        current = courses[1]
        assert isinstance(current, dict)
        current_tissue = current["tissue_doses"]
        assert isinstance(current_tissue, list)
        current_row = current_tissue[0]
        assert isinstance(current_row, dict)
        current_row["alpha_beta_gy"] = 3
        current_row["alpha_beta_source_reference"] = "Synthetic alpha/beta mismatch"
        response = client.post(
            f"{base}/scenarios/{scenario['id']}/re-irradiation/validate", json=body
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["valid"] is True
        warning_codes = {item["code"] for item in payload["warnings"]}
        assert "CUMULATIVE_CONTEXT_MISMATCH" in warning_codes
        assert len(payload["preview"]) > 0

        # A recovery assumption outside [0, 1] is a validation error, not a
        # silently clamped value.
        prior["recovery_fraction"] = 1.1
        invalid = client.post(
            f"{base}/scenarios/{scenario['id']}/re-irradiation/validate", json=body
        )
        assert invalid.status_code == 200
        assert invalid.json()["valid"] is False
        assert invalid.json()["errors"][0]["code"] == "RECOVERY_ASSUMPTION_INVALID"


def test_p15_reirradiation_rejects_missing_explicit_tissue_rows_and_scope() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        base = f"/api/v1/organizations/{organization.id}/biological"
        body = _reirradiation_body(revision_id, "p15-tissue-required-01")
        courses = body["courses"]
        assert isinstance(courses, list)
        first = courses[0]
        assert isinstance(first, dict)
        first.pop("tissue_doses")
        invalid = client.post(
            f"{base}/scenarios/{scenario['id']}/re-irradiation/validate", json=body
        )
        assert invalid.status_code == 200
        assert invalid.json()["valid"] is False
        assert invalid.json()["errors"][0]["code"] == "TISSUE_DOSE_REQUIRED"

        outsider = client.get(f"{base}/re-irradiation?scenario_id={uuid4()}")
        assert outsider.status_code == 200
        forbidden = client.get(f"/api/v1/organizations/{uuid4()}/biological/re-irradiation")
        assert forbidden.status_code == 403
        assert forbidden.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"


def test_p15_fraction_compensation_preserves_delivered_prefix_and_is_idempotent() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        base = f"/api/v1/organizations/{organization.id}/biological"
        body = _compensation_body(revision_id)
        validation = client.post(
            f"{base}/scenarios/{scenario['id']}/fraction-compensation/validate", json=body
        )
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True
        assert validation.json()["preview"]["alternative_count"] == 2

        created = client.post(f"{base}/scenarios/{scenario['id']}/fraction-compensation", json=body)
        assert created.status_code == 201, created.text
        run = created.json()
        assert run["operation_type"] == "FRACTION_COMPENSATION"
        alternatives = run["result_snapshot"]["alternatives"]
        assert all(item["delivered_prefix_unchanged"] for item in alternatives)
        assert run["result_snapshot"]["warnings"][0]["code"] == "NO_REPOPULATION_CORRECTION"

        replay = client.post(f"{base}/scenarios/{scenario['id']}/fraction-compensation", json=body)
        assert replay.status_code == 200
        assert replay.json()["id"] == run["id"]
        assert client.get(f"{base}/fraction-compensation").json()["total"] == 1
        exported = client.get(f"{base}/fraction-compensation/{run['id']}/export?export_format=CSV")
        assert exported.status_code == 200
        assert "ALTERNATIVE" in exported.text


def test_p15_fraction_compensation_rejects_prefix_overlap_and_missing_time_model_fields() -> None:
    with _workspace_client() as (client, organization):
        scenario, revision_id = _saved_scenario(client, organization)
        base = f"/api/v1/organizations/{organization.id}/biological"
        overlap = _compensation_body(revision_id, "p15-overlap-01")
        overlap["interruptions"] = [
            {"start_date": "2026-01-01", "end_date": "2026-01-04"},
            {"start_date": "2026-01-03", "end_date": "2026-01-05"},
        ]
        response = client.post(
            f"{base}/scenarios/{scenario['id']}/fraction-compensation/validate", json=overlap
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False
        assert response.json()["errors"][0]["code"] == "INTERRUPTION_OVERLAP"

        time_model = _compensation_body(revision_id, "p15-time-model-01")
        time_model["time_model"] = {"mode": "USER_DEFINED_LINEAR"}
        response = client.post(
            f"{base}/scenarios/{scenario['id']}/fraction-compensation/validate",
            json=time_model,
        )
        assert response.status_code == 200
        assert response.json()["valid"] is False
        assert response.json()["errors"][0]["code"] == "TIME_MODEL_SOURCE_REQUIRED"
