from __future__ import annotations

from pathlib import Path
from typing import cast

from pylinac.core.geometry import Point

from rt_connect_api.api.artifacts import _storage
from rt_connect_api.services.object_storage import InMemoryObjectStorage
from rt_connect_api.services.pylinac_adapter import (
    PylinacAdapterError,
    PylinacExecutionResult,
    execute_pylinac,
)
from test_workspace import _workspace_client


def _case(client, organization_id: str, folder_name: str = "Picket Fence") -> str:
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
            "qa_definition_key": "PICKET_FENCE",
            "qa_cycle": "DAILY",
            "performed_at": "2026-09-14T00:00:00Z",
            "title": "Picket Fence tổng hợp",
        },
    )
    assert case.status_code == 201, case.text
    return case.json()["id"]


def test_pylinac_run_persists_input_result_overlay_and_separate_assessment(monkeypatch) -> None:
    storage = InMemoryObjectStorage()
    fake_result = PylinacExecutionResult(
        catalog_key="PICKET_FENCE",
        engine_class="PicketFence",
        engine_version="3.47.0",
        package_fingerprint="f" * 64,
        result_snapshot={
            "schema_version": "p7.pylinac-result.v1",
            "engine": "pylinac",
            "engine_class": "PicketFence",
            "metrics": {"passed": True, "percent_leaves_passing": 100.0},
            "engine_passed": True,
            "parameters": {},
        },
        warnings=[],
        overlay_bytes=b"synthetic-png",
        overlay_media_type="image/png",
        overlay_filename="picket-fence-phan-tich.png",
    )

    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        monkeypatch.setattr(
            "rt_connect_api.api.pylinac_qa.execute_pylinac", lambda *_args: fake_result
        )
        case_id = _case(client, str(organization.id))
        uploaded = client.post(
            f"/api/v1/qa-cases/{case_id}/artifacts",
            files={"file": ("picket-fence.dcm", b"synthetic-dicom", "application/dicom")},
            data={"artifact_type": "DICOM", "logical_role": "EVALUATION"},
        )
        assert uploaded.status_code == 201, uploaded.text
        artifact_id = uploaded.json()["id"]

        created = client.post(
            f"/api/v1/qa-cases/{case_id}/pylinac-runs",
            json={
                "catalog_key": "PICKET_FENCE",
                "artifact_ids": [artifact_id],
                "parameters": {"tolerance": 0.5},
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["status"] == "COMPLETED"
        assert body["assessment_status"] is None
        assert body["result_snapshot"]["engine_passed"] is True
        assert body["input_files"][0]["filename"] == "picket-fence.dcm"
        assert body["overlay_artifact_id"] is not None
        assert b"synthetic-png" in storage.objects.values()

        history = client.get(f"/api/v1/qa-cases/{case_id}/pylinac-runs")
        assert history.status_code == 200, history.text
        assert history.json()["total"] == 1

        assessment = client.post(
            f"/api/v1/pylinac-qa-runs/{body['id']}/assessment",
            json={"assessment_status": "WARNING", "note": "Cần xem lại hình chú thích."},
        )
        assert assessment.status_code == 200, assessment.text
        assert assessment.json()["assessment_status"] == "WARNING"
        assert assessment.json()["result_snapshot"]["metrics"]["passed"] is True


def test_pylinac_run_rejects_input_from_another_case() -> None:
    storage = InMemoryObjectStorage()
    with _workspace_client() as (client, organization):
        client.app.dependency_overrides[_storage] = lambda: storage
        first_case = _case(client, str(organization.id))
        second_case = _case(client, str(organization.id), "Picket Fence other case")
        uploaded = client.post(
            f"/api/v1/qa-cases/{first_case}/artifacts",
            files={"file": ("picket-fence.dcm", b"bytes", "application/dicom")},
            data={"artifact_type": "DICOM", "logical_role": "EVALUATION"},
        )
        assert uploaded.status_code == 201, uploaded.text
        response = client.post(
            f"/api/v1/qa-cases/{second_case}/pylinac-runs",
            json={"catalog_key": "PICKET_FENCE", "artifact_ids": [uploaded.json()["id"]]},
        )
        assert response.status_code == 404
        assert response.json()["code"] == "PYLINAC_INPUT_NOT_FOUND"


def test_starshot_adapter_uses_pylinac_contract_and_preserves_manual_center(monkeypatch) -> None:
    class FakeStarshot:
        def __init__(self, path: str, **kwargs: object) -> None:
            assert path.endswith("starshot.tif")
            assert kwargs == {"sid": 1000.0}

        def analyze(self, **kwargs: object) -> None:
            start_point = cast(Point, kwargs["start_point"])
            assert start_point.x == 101.0
            assert start_point.y == 202.0
            assert kwargs["tolerance"] == 1.0

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {
                "passed": True,
                "circle_diameter_mm": 0.42,
                "warnings": [],
            }

        def save_analyzed_image(self, stream) -> None:
            stream.write(b"starshot-png")

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakeStarshot, None) if key == "STARSHOT" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "STARSHOT",
        Path("starshot.tif"),
        {
            "sid": 1000,
            "start_point": {"x": 101, "y": 202},
            "tolerance": 1,
        },
    )
    assert result.catalog_key == "STARSHOT"
    assert result.result_snapshot["engine_passed"] is True
    assert result.overlay_filename == "kiem-tra-sao-phan-tich.png"
    assert result.overlay_bytes == b"starshot-png"


def test_starshot_adapter_rejects_invalid_manual_center() -> None:
    try:
        execute_pylinac("STARSHOT", Path("starshot.tif"), {"start_point": {"x": 1}})
    except PylinacAdapterError as exc:
        assert exc.code == "PYLINAC_PARAMETER_INVALID"
    else:
        raise AssertionError("Tâm thủ công không hợp lệ phải bị từ chối")
