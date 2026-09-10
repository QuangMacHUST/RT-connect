from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from rt_connect_api.api.artifacts import _storage as artifact_storage
from rt_connect_api.api.gamma import _storage as gamma_storage
from rt_connect_api.api.gamma import _validate_coordinate_frames
from rt_connect_api.core.errors import DomainError
from rt_connect_api.services.gamma_engine import (
    GammaConfiguration,
    GammaEngineError,
    MeasurementDataset,
    calculate_gamma,
    calculate_gamma_from_paths,
    load_measurement,
)
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from test_workspace import _workspace_client


def _measurement_bytes(
    dataset_id: str,
    values: list[float],
    *,
    frame_id: str = "1.2.826.0.1.3680043.8.498.999.4",
) -> bytes:
    payload: dict[str, Any] = {
        "schema_version": "gamma.measurement.v1",
        "dataset_id": dataset_id,
        "data_type": "dose",
        "units": {"dose": "GY", "position": "mm"},
        "grid": {"shape": [2, 2], "spacing_mm": [1.0, 1.0]},
        "coordinate_frame": {
            "basis": "PATIENT_LPS",
            "frame_id": frame_id,
            "frame_of_reference_uid": frame_id,
            "axis_order": ["y", "x"],
            "transform_to_reference": {
                "direction": "SOURCE_TO_REFERENCE",
                "units": "mm",
                "matrix": [
                    [1.0, 0.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                "source": {
                    "type": "synthetic-shared-frame",
                    "version": "fixture-v1",
                    "sha256": "d" * 64,
                },
            },
        },
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


def test_gamma_engine_rejects_mismatched_coordinate_frames(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.json"
    evaluation_path = tmp_path / "evaluation.json"
    reference_path.write_bytes(_measurement_bytes("reference", [1.0, 2.0, 3.0, 4.0]))
    evaluation_path.write_bytes(
        _measurement_bytes(
            "evaluation",
            [1.0, 2.0, 3.0, 4.0],
            frame_id="1.2.826.0.1.3680043.8.498.999.5",
        )
    )

    with pytest.raises(GammaEngineError) as error:
        calculate_gamma_from_paths(
            reference_path,
            evaluation_path,
            {
                "dimensionality": "2D",
                "dose_difference_percent": 3.0,
                "dose_difference_mode": "RELATIVE",
                "distance_to_agreement_mm": 3.0,
                "dose_threshold_percent": 0.0,
                "normalization": "GLOBAL",
                "interpolation": "GRID",
                "pass_rate_threshold_percent": 95.0,
                "histogram_bins": 10,
            },
        )

    assert error.value.code == "GAMMA_INPUT_INCOMPATIBLE"


def test_gamma_api_preflight_rejects_mismatched_transform() -> None:
    identity = {
        "basis": "PATIENT_LPS",
        "frame_id": "frame-1",
        "axis_order": ["y", "x"],
        "transform_to_reference": {
            "direction": "SOURCE_TO_REFERENCE",
            "units": "mm",
            "matrix": [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
        },
    }
    translated = json.loads(json.dumps(identity))
    translated["transform_to_reference"]["matrix"][0][3] = 1.0
    reference = SimpleNamespace(
        artifact_type="MEASUREMENT",
        modality=None,
        frame_of_reference_uid=None,
        sha256="a" * 64,
        metadata_snapshot={"coordinate_frame": identity},
    )
    evaluation = SimpleNamespace(
        artifact_type="MEASUREMENT",
        modality=None,
        frame_of_reference_uid=None,
        sha256="b" * 64,
        metadata_snapshot={"coordinate_frame": translated},
    )

    with pytest.raises(DomainError) as error:
        _validate_coordinate_frames(reference, evaluation)

    assert error.value.code == "GAMMA_INPUT_INCOMPATIBLE"
    assert error.value.details[0]["field"] == "coordinate_frame.transform_to_reference"


def test_gamma_api_rejects_missing_measurement_transform() -> None:
    frame = {
        "basis": "IEC_PHANTOM",
        "frame_id": "phantom-1",
        "axis_order": ["y", "x"],
    }
    artifact = SimpleNamespace(
        artifact_type="MEASUREMENT",
        modality=None,
        frame_of_reference_uid=None,
        sha256="a" * 64,
        metadata_snapshot={"coordinate_frame": frame},
    )

    with pytest.raises(DomainError) as error:
        _validate_coordinate_frames(artifact, artifact)

    assert error.value.code == "GAMMA_COORDINATE_FRAME_INVALID"


def test_gamma_engine_does_not_mix_legacy_grid_with_explicit_frame(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.json"
    evaluation_path = tmp_path / "evaluation.json"
    reference_path.write_bytes(_measurement_bytes("reference", [1.0, 2.0, 3.0, 4.0]))
    evaluation_path.write_bytes(_measurement_bytes("evaluation", [1.0, 2.0, 3.0, 4.0]))
    explicit = load_measurement(reference_path)
    legacy = type(explicit)(
        dataset_id=explicit.dataset_id,
        values=explicit.values,
        spacing_mm=explicit.spacing_mm,
        origin_mm=explicit.origin_mm,
        units=explicit.units,
    )

    with pytest.raises(GammaEngineError) as error:
        calculate_gamma(
            explicit,
            legacy,
            GammaConfiguration(
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
            ),
        )

    assert error.value.code == "GAMMA_INPUT_INCOMPATIBLE"


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
        coordinate_frame=evaluation.coordinate_frame,
        frame_id=evaluation.frame_id,
        axis_order=evaluation.axis_order,
        transform_to_reference=evaluation.transform_to_reference,
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


def test_gamma_full_roi_does_not_drop_points_without_comparison_coverage() -> None:
    reference = MeasurementDataset(
        dataset_id="reference",
        values=np.ones((2, 2), dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
    )
    evaluation = MeasurementDataset(
        dataset_id="evaluation",
        values=np.ones((2, 2), dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(100.0, 100.0),
        units={"dose": "GY", "position": "mm"},
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
        coverage_policy="FULL_ROI",
        max_gamma=2.0,
    )

    result = calculate_gamma(reference, evaluation, configuration)

    metrics = result["metrics"]
    assert result["overall_status"] == "INVALID"
    assert metrics["selected_points"] == 4
    assert metrics["invalid_coverage_points"] == 4
    assert metrics["pass_rate_percent"] is None
    assert metrics["passing_points"] == 0


def test_gamma_overlap_only_reports_coverage_instead_of_inflating_sample() -> None:
    reference = MeasurementDataset(
        dataset_id="reference",
        values=np.ones((1, 2), dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
    )
    evaluation = MeasurementDataset(
        dataset_id="evaluation",
        values=np.ones((1, 1), dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
    )
    configuration = GammaConfiguration(
        dimensionality="2D",
        dose_difference_percent=3.0,
        dose_difference_mode="RELATIVE",
        absolute_dose_difference_gy=None,
        distance_to_agreement_mm=0.4,
        dose_threshold_percent=0.0,
        normalization="GLOBAL",
        interpolation="GRID",
        pass_rate_threshold_percent=95.0,
        histogram_bins=10,
        coverage_policy="OVERLAP_ONLY",
        max_gamma=2.0,
    )

    result = calculate_gamma(reference, evaluation, configuration)

    metrics = result["metrics"]
    assert result["overall_status"] == "PASS"
    assert metrics["evaluated_points"] == 1
    assert metrics["coverage_excluded_points"] == 1
    assert metrics["coverage_fraction"] == 0.5
    assert metrics["pass_rate_percent"] == 100.0


def test_gamma_max_limit_marks_high_gamma_as_censored() -> None:
    reference = MeasurementDataset(
        dataset_id="reference",
        values=np.ones((1, 1), dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
    )
    evaluation = MeasurementDataset(
        dataset_id="evaluation",
        values=np.full((1, 1), 1.06, dtype=np.float64),
        spacing_mm=(1.0, 1.0),
        origin_mm=(0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
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
        coverage_policy="FULL_ROI",
        max_gamma=1.0,
    )

    result = calculate_gamma(reference, evaluation, configuration)

    metrics = result["metrics"]
    assert result["overall_status"] == "FAIL"
    assert metrics["censored_points"] == 1
    assert metrics["nonpassing_points"] == 1
    assert metrics["pass_rate_percent"] == 0.0
    assert metrics["percentiles"]["exact"] is False
    assert metrics["percentiles"]["reason"] == "GAMMA_CENSORED_POINTS"


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
            "workflow_profile": "ENGINE_TEST",
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


def test_psqa_profile_rejects_json_only_inputs_before_enqueue() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[gamma_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        ids = []
        for role, dataset_id in (("REFERENCE", "reference"), ("EVALUATION", "evaluation")):
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
            validation = client.post(f"/api/v1/artifacts/{artifact_id}/validate")
            assert validation.json()["result"] == "VALID"
            ids.append(artifact_id)

        rejected = client.post(
            f"/api/v1/qa-cases/{case_id}/gamma-runs",
            json={
                "reference_artifact_id": ids[0],
                "evaluation_artifact_id": ids[1],
                "idempotency_key": "psqa-requires-rtdose-001",
            },
        )
        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["code"] == "RTDOSE_REQUIRED"


def test_gamma_resource_preflight_rejects_oversized_validated_grid() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.state.settings.gamma_max_voxels = 3
        client.app.dependency_overrides[artifact_storage] = lambda: storage
        client.app.dependency_overrides[gamma_storage] = lambda: storage
        case_id = _case(client, str(organization.id))
        ids = []
        for role, dataset_id in (("REFERENCE", "reference"), ("EVALUATION", "evaluation")):
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
            validation = client.post(f"/api/v1/artifacts/{artifact_id}/validate")
            assert validation.json()["result"] == "VALID"
            ids.append(artifact_id)

        rejected = client.post(
            f"/api/v1/qa-cases/{case_id}/gamma-runs",
            json={
                "reference_artifact_id": ids[0],
                "evaluation_artifact_id": ids[1],
                "idempotency_key": "gamma-resource-limit-001",
                "workflow_profile": "ENGINE_TEST",
            },
        )

        assert rejected.status_code == 422, rejected.text
        assert rejected.json()["code"] == "GAMMA_RESOURCE_LIMIT"
        assert rejected.json()["details"][0]["field"] == "reference_voxels"
