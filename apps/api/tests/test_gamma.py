from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from rt_connect_api.api.artifacts import _storage as artifact_storage
from rt_connect_api.api.gamma import _storage as gamma_storage
from rt_connect_api.services.gamma_engine import (
    GammaConfiguration,
    calculate_gamma,
    load_measurement,
)
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from test_workspace import _workspace_client


def _measurement_bytes(dataset_id: str, values: list[float]) -> bytes:
    payload: dict[str, Any] = {
        "schema_version": "gamma.measurement.v1",
        "dataset_id": dataset_id,
        "data_type": "dose",
        "units": {"dose": "GY", "position": "mm"},
        "grid": {"shape": [2, 2], "spacing_mm": [1.0, 1.0]},
        "values": {"encoding": "inline-float32", "inline": values},
        "acquisition": {"detector": "synthetic", "measured_at": "2026-09-07T00:00:00Z"},
        "source": {"filename": f"{dataset_id}.json", "sha256": "a" * 64},
    }
    return json.dumps(payload).encode("utf-8")


def _case(client: TestClient, organization_id: str) -> str:
    folder = client.post(
        f"/api/v1/organizations/{organization_id}/folders", json={"name": "P8 fixtures"}
    )
    assert folder.status_code == 201, folder.text
    sites = client.get(f"/api/v1/organizations/{organization_id}/sites").json()["items"]
    machines = client.get(
        f"/api/v1/organizations/{organization_id}/sites/{sites[0]['id']}/machines"
    ).json()["items"]
    case = client.post(
        f"/api/v1/organizations/{organization_id}/qa-cases",
        json={
            "site_id": sites[0]["id"],
            "machine_id": machines[0]["id"],
            "primary_folder_id": folder.json()["id"],
            "qa_type": "PSQA Gamma",
            "qa_cycle": "CUSTOM",
            "performed_at": "2026-09-07T00:00:00Z",
            "title": "P8 synthetic Gamma case",
        },
    )
    assert case.status_code == 201, case.text
    return case.json()["id"]


def test_gamma_engine_identical_grid_is_golden_pass(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.json"
    evaluation_path = tmp_path / "evaluation.json"
    reference_path.write_bytes(_measurement_bytes("reference", [1.0, 2.0, 3.0, 4.0]))
    evaluation_path.write_bytes(_measurement_bytes("evaluation", [1.0, 2.0, 3.0, 4.0]))
    configuration = GammaConfiguration(
        dimensionality="2D",
        dose_difference_percent=3.0,
        dose_difference_mode="RELATIVE",
        absolute_dose_difference_gy=None,
        distance_to_agreement_mm=3.0,
        dose_threshold_percent=10.0,
        normalization="GLOBAL",
        interpolation="GRID",
        pass_rate_threshold_percent=95.0,
        histogram_bins=10,
    )

    result = calculate_gamma(
        load_measurement(reference_path), load_measurement(evaluation_path), configuration
    )

    assert result["overall_status"] == "PASS"
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["evaluated_points"] == 4
    assert metrics["passing_points"] == 4
    assert metrics["pass_rate_percent"] == 100.0
    assert metrics["percentiles"]["max"] == 0.0


def test_gamma_engine_known_dose_shift_stays_within_dta(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.json"
    evaluation_path = tmp_path / "evaluation.json"
    reference_path.write_bytes(_measurement_bytes("reference", [2.0, 2.0, 2.0, 2.0]))
    evaluation_path.write_bytes(_measurement_bytes("evaluation", [2.0, 2.0, 2.0, 2.0]))
    reference = load_measurement(reference_path)
    evaluation = load_measurement(evaluation_path)
    shifted = type(evaluation)(
        dataset_id=evaluation.dataset_id,
        values=evaluation.values,
        spacing_mm=evaluation.spacing_mm,
        origin_mm=(1.0, 0.0),
        units=evaluation.units,
    )
    configuration = GammaConfiguration(
        dimensionality="2D",
        dose_difference_percent=3.0,
        dose_difference_mode="RELATIVE",
        absolute_dose_difference_gy=None,
        distance_to_agreement_mm=3.0,
        dose_threshold_percent=0.0,
        normalization="GLOBAL",
        interpolation="GRID",
        pass_rate_threshold_percent=95.0,
        histogram_bins=10,
    )

    result = calculate_gamma(reference, shifted, configuration)

    assert result["overall_status"] == "PASS"
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["pass_rate_percent"] == 100.0
    assert metrics["percentiles"]["max"] == 1 / 3


def test_gamma_enqueue_requires_valid_inputs_and_is_idempotent() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[gamma_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        reference = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={
                "file": (
                    "reference.json",
                    _measurement_bytes("reference", [1, 2, 3, 4]),
                    "application/json",
                )
            },
            data={"artifact_type": "MEASUREMENT", "logical_role": "REFERENCE"},
        )
        evaluation = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={
                "file": (
                    "evaluation.json",
                    _measurement_bytes("evaluation", [1, 2, 3, 4]),
                    "application/json",
                )
            },
            data={"artifact_type": "MEASUREMENT", "logical_role": "EVALUATION"},
        )
        assert reference.status_code == 201, reference.text
        assert evaluation.status_code == 201, evaluation.text
        reference_id = reference.json()["id"]
        evaluation_id = evaluation.json()["id"]
        for artifact_id in (reference_id, evaluation_id):
            validation = client.post(f"/api/v1/artifacts/{artifact_id}/validate")
            assert validation.status_code == 200, validation.text
            assert validation.json()["result"] == "VALID"

        request = {
            "reference_artifact_id": reference_id,
            "evaluation_artifact_id": evaluation_id,
            "idempotency_key": "p8-golden-request-001",
            "configuration": {"dose_threshold_percent": 0},
        }
        queued = client.post(f"/api/v1/qa-cases/{case_id}/gamma-runs", json=request)
        assert queued.status_code == 201, queued.text
        assert queued.json()["status"] == "QUEUED"
        repeated = client.post(f"/api/v1/qa-cases/{case_id}/gamma-runs", json=request)
        assert repeated.status_code == 200, repeated.text
        assert repeated.json()["id"] == queued.json()["id"]

        conflict = {**request, "evaluation_artifact_id": reference_id}
        conflicted = client.post(f"/api/v1/qa-cases/{case_id}/gamma-runs", json=conflict)
        assert conflicted.status_code == 422, conflicted.text
