from __future__ import annotations

from pathlib import Path
from typing import cast

import matplotlib
from pylinac.core.geometry import Point
from pylinac.winston_lutz import BBConfig

matplotlib.use("Agg")

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


def test_winston_lutz_adapter_uses_zip_loader_and_pylinac_overlay(monkeypatch) -> None:
    class FakeFigure:
        def savefig(self, stream, **kwargs: object) -> None:
            assert kwargs == {"format": "png", "dpi": 120}
            stream.write(b"winston-lutz-png")

        def clf(self) -> None:
            return None

    class FakeWinstonLutz:
        @classmethod
        def from_zip(cls, path: str, **kwargs: object):
            assert path.endswith("winston-lutz.zip")
            assert kwargs == {"sid": 1000.0}
            return cls()

        def analyze(self, **kwargs: object) -> None:
            assert kwargs["bb_size_mm"] == 5.0
            assert kwargs["snap_tolerance"] == 3.0
            assert kwargs["open_field"] is False

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {
                "max_2d_cax_to_bb_mm": 0.31,
                "gantry_3d_iso_diameter_mm": 0.48,
                "warnings": [],
            }

        def plot_images(self, *, show: bool, split: bool):
            assert show is False
            assert split is False
            return [FakeFigure()], ["image"]

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakeWinstonLutz, None) if key == "WINSTON_LUTZ" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "WINSTON_LUTZ",
        Path("winston-lutz.zip"),
        {"sid": 1000, "bb_size_mm": 5, "snap_tolerance": 3, "open_field": False},
    )
    assert result.catalog_key == "WINSTON_LUTZ"
    assert result.result_snapshot["engine_class"] == "WinstonLutz"
    assert result.overlay_filename == "winston-lutz-phan-tich.png"
    assert result.overlay_bytes == b"winston-lutz-png"


def test_winston_lutz_adapter_requires_zip_input() -> None:
    try:
        execute_pylinac("WINSTON_LUTZ", Path("winston-lutz.dcm"), {})
    except PylinacAdapterError as exc:
        assert exc.code == "PYLINAC_INPUT_FORMAT_INVALID"
    else:
        raise AssertionError("Winston–Lutz phải yêu cầu bộ ảnh ZIP")


def test_winston_lutz_multi_target_adapter_maps_bb_arrangement(monkeypatch) -> None:
    class FakeFigure:
        def savefig(self, stream, **kwargs: object) -> None:
            assert kwargs == {"format": "png", "dpi": 120}
            stream.write(b"winston-lutz-multi-png")

        def clf(self) -> None:
            return None

    class FakeMultiTarget:
        @classmethod
        def from_zip(cls, path: str, **kwargs: object):
            assert path.endswith("winston-lutz-multi.zip")
            assert kwargs == {"sid": 1000.0, "use_filenames": False}
            return cls()

        def analyze(self, **kwargs: object) -> None:
            arrangement = cast(tuple[BBConfig, ...], kwargs["bb_arrangement"])
            assert len(arrangement) == 2
            assert arrangement[0].name == "Iso"
            assert arrangement[1].offset_in_mm == 30.0
            assert kwargs["is_open_field"] is False
            assert kwargs["bb_proximity_mm"] == 10.0

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {
                "num_total_images": 19,
                "max_2d_field_to_bb_mm": 0.94,
                "bb_shift_vector": {"x": 0.1, "y": 0.2, "z": 0.3},
                "warnings": [],
            }

        def plot_images(self, **kwargs: object):
            assert kwargs == {"show": False, "zoomed": False, "legend": True}
            return [FakeFigure()], ["RT000001.dcm"]

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (
            (FakeMultiTarget, None) if key == "WINSTON_LUTZ_MULTI_TARGET" else (None, "missing")
        ),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "WINSTON_LUTZ_MULTI_TARGET",
        Path("winston-lutz-multi.zip"),
        {
            "sid": 1000,
            "use_filenames": False,
            "bb_proximity_mm": 10,
            "is_open_field": False,
            "bb_arrangement": [
                {
                    "name": "Iso",
                    "offset_left_mm": 0,
                    "offset_up_mm": 0,
                    "offset_in_mm": 0,
                    "bb_size_mm": 5,
                    "rad_size_mm": 20,
                },
                {
                    "name": "1",
                    "offset_left_mm": 0,
                    "offset_up_mm": 0,
                    "offset_in_mm": 30,
                    "bb_size_mm": 5,
                    "rad_size_mm": 20,
                },
            ],
        },
    )
    assert result.catalog_key == "WINSTON_LUTZ_MULTI_TARGET"
    assert result.result_snapshot["engine_class"] == "WinstonLutzMultiTargetMultiField"
    assert result.overlay_filename == "winston-lutz-nhieu-bi-phan-tich.png"
    assert result.overlay_bytes == b"winston-lutz-multi-png"


def test_winston_lutz_multi_target_rejects_invalid_arrangement() -> None:
    try:
        execute_pylinac(
            "WINSTON_LUTZ_MULTI_TARGET",
            Path("winston-lutz-multi.zip"),
            {"bb_arrangement": [{"name": "Iso"}]},
        )
    except PylinacAdapterError as exc:
        assert exc.code == "PYLINAC_PARAMETER_INVALID"
    else:
        raise AssertionError("Cấu hình bi thiếu trường phải bị từ chối")


def test_vmat_adapter_uses_two_image_pair_and_drcs_specific_parameters(
    tmp_path, monkeypatch
) -> None:
    first = tmp_path / "open.dcm"
    second = tmp_path / "dynamic.dcm"
    first.write_bytes(b"open")
    second.write_bytes(b"dynamic")

    class FakeVmat:
        def __init__(self, paths, **kwargs: object) -> None:
            assert [Path(path).name for path in paths] == ["dynamic.dcm", "open.dcm"]
            assert kwargs == {"ground": True, "check_inversion": True}

        def analyze(self, **kwargs: object) -> None:
            assert kwargs["tolerance"] == 1.5
            assert kwargs["segment_size_mm"] == (5.0, 100.0)
            assert kwargs["invert_image_order"] is False
            assert kwargs["collimator_radial_distances"] == (30.0, 70.0)

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {"passed": True, "max_deviation_percent": 0.8, "warnings": []}

        def plot_analyzed_image(self, *, show: bool, show_text: bool) -> None:
            assert show is False
            assert show_text is True

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakeVmat, None) if key == "VMAT_DRCS" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "VMAT_DRCS",
        tmp_path,
        {
            "ground": True,
            "check_inversion": True,
            "tolerance": 1.5,
            "segment_size_mm": [5, 100],
            "invert_image_order": False,
            "collimator_radial_distances": [30, 70],
        },
    )
    assert result.catalog_key == "VMAT_DRCS"
    assert result.result_snapshot["engine_passed"] is True
    assert result.overlay_filename == "drcs-phan-tich.png"
    assert len(result.overlay_bytes or b"") > 0


def test_vmat_adapter_rejects_single_image(tmp_path) -> None:
    (tmp_path / "only.dcm").write_bytes(b"only")
    try:
        execute_pylinac("VMAT_DRGS", tmp_path, {})
    except PylinacAdapterError as exc:
        assert exc.code == "PYLINAC_INPUT_COUNT_INVALID"
    else:
        raise AssertionError("Bài VMAT phải yêu cầu cặp ảnh")


def test_field_profile_adapter_passes_manual_profile_controls(tmp_path, monkeypatch) -> None:
    source = tmp_path / "profile.dcm"
    source.write_bytes(b"profile")

    from matplotlib import pyplot as plt

    class FakeProfile:
        def __init__(self, path: str) -> None:
            assert path.endswith("profile.dcm")

        def analyze(self, **kwargs: object) -> None:
            assert kwargs["centering"] == "MANUAL"
            assert kwargs["position"] == (0.4, 0.6)
            assert kwargs["x_width"] == 20.0
            assert kwargs["normalization"] == "MAX"
            assert kwargs["edge_type"] == "FWHM"

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {"x_metrics": {"flatness": 1.2}, "warnings": []}

        def plot_analyzed_images(self, *, show: bool) -> list[object]:
            assert show is False
            return [plt.figure(), plt.figure(), plt.figure()]

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakeProfile, None) if key == "FIELD_PROFILE_ANALYSIS" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter._enum_value",
        lambda _module, _enum, value: value,
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "FIELD_PROFILE_ANALYSIS",
        source,
        {
            "centering": "MANUAL",
            "position": [0.4, 0.6],
            "x_width": 20,
            "normalization": "MAX",
            "edge_type": "FWHM",
        },
    )
    assert result.engine_class == "FieldProfileAnalysis"
    assert result.overlay_filename == "field-profile-analysis-phan-tich.png"
    assert len(result.overlay_bytes or b"") > 0


def test_legacy_field_analysis_adapter_passes_protocol_controls(tmp_path, monkeypatch) -> None:
    source = tmp_path / "field.dcm"
    source.write_bytes(b"field")

    from matplotlib import pyplot as plt

    class FakeLegacy:
        def __init__(self, path: str) -> None:
            assert path.endswith("field.dcm")

        def analyze(self, **kwargs: object) -> None:
            assert kwargs["protocol"] == "ELEKTA"
            assert kwargs["centering"] == "GEOMETRIC_CENTER"
            assert kwargs["interpolation"] == "SPLINE"

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {"protocol_results": {"flatness": 1.1}, "warnings": []}

        def plot_analyzed_image(
            self, *, show: bool, split_plots: bool
        ) -> tuple[list[object], list[str]]:
            assert show is False
            assert split_plots is True
            return [plt.figure()], ["Image"]

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakeLegacy, None) if key == "FIELD_ANALYSIS_LEGACY" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter._enum_value",
        lambda _module, _enum, value: value,
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "FIELD_ANALYSIS_LEGACY",
        source,
        {"protocol": "ELEKTA", "centering": "GEOMETRIC_CENTER", "interpolation": "SPLINE"},
    )
    assert result.engine_class == "FieldAnalysis"
    assert result.overlay_filename == "field-analysis-phan-tich.png"
    assert len(result.overlay_bytes or b"") > 0


def test_catphan_adapter_passes_zip_and_analysis_controls(tmp_path, monkeypatch) -> None:
    source = tmp_path / "catphan.zip"
    source.write_bytes(b"dicom-zip")

    from matplotlib import pyplot as plt

    class FakeCatPhan:
        def __init__(self, path: str, **kwargs: object) -> None:
            assert path.endswith("catphan.zip")
            assert kwargs["check_uid"] is True
            assert kwargs["is_zip"] is True

        def analyze(self, **kwargs: object) -> None:
            assert kwargs["hu_tolerance"] == 40.0
            assert kwargs["cnr_threshold"] == 15.0
            assert kwargs["origin_slice"] == 12
            assert kwargs["x_adjustment"] == 1.5

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {"passed": True, "ctp404": {"hu": 3.2}, "warnings": []}

        def plot_analyzed_image(self, *, show: bool) -> None:
            assert show is False
            plt.figure()

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakeCatPhan, None) if key == "CATPHAN_503" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "CATPHAN_503",
        source,
        {"hu_tolerance": 40, "cnr_threshold": 15, "origin_slice": 12, "x_adjustment": 1.5},
    )
    assert result.engine_class == "CatPhan503"
    assert result.result_snapshot["engine_passed"] is True
    assert result.overlay_filename == "catphan_503-phan-tich.png"
    assert len(result.overlay_bytes or b"") > 0


def test_acr_adapter_supports_ct_and_mri_controls(tmp_path, monkeypatch) -> None:
    source = tmp_path / "acr.zip"
    source.write_bytes(b"dicom-zip")

    from matplotlib import pyplot as plt

    class FakeACR:
        def __init__(self, path: str, **kwargs: object) -> None:
            assert path.endswith("acr.zip")
            assert kwargs == {"check_uid": True, "memory_efficient_mode": False, "is_zip": True}

        def analyze(self, **kwargs: object) -> None:
            assert kwargs["x_adjustment"] == 1.5
            assert kwargs["origin_slice"] == 4
            assert kwargs["echo_number"] == 2
            assert kwargs["low_contrast_method"] == "Weber"

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {"passed": True, "geometric_accuracy": 0.4, "warnings": []}

        def plot_analyzed_image(self, *, show: bool) -> object:
            assert show is False
            return plt.figure()

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakeACR, None) if key == "ACR_MRI_LARGE" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "ACR_MRI_LARGE",
        source,
        {
            "check_uid": True,
            "is_zip": True,
            "x_adjustment": 1.5,
            "origin_slice": 4,
            "echo_number": 2,
            "low_contrast_method": "Weber",
        },
    )
    assert result.engine_class == "ACRMRILarge"
    assert result.result_snapshot["engine_passed"] is True
    assert result.overlay_filename == "acr_mri_large-phan-tich.png"
    assert len(result.overlay_bytes or b"") > 0


def test_acr_adapter_rejects_non_zip_input(tmp_path, monkeypatch) -> None:
    source = tmp_path / "acr.dcm"
    source.write_bytes(b"dicom")
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (object, None) if key == "ACR_CT_464" else (None, "missing"),
    )
    try:
        execute_pylinac("ACR_CT_464", source, {})
    except PylinacAdapterError as exc:
        assert exc.code == "PYLINAC_INPUT_FORMAT_INVALID"
    else:
        raise AssertionError("Bài ACR phải từ chối tệp không phải ZIP")


def test_planar_adapter_uses_common_pylinac_image_controls(tmp_path, monkeypatch) -> None:
    source = tmp_path / "planar.dcm"
    source.write_bytes(b"planar")

    from matplotlib import pyplot as plt

    class FakePlanar:
        def __init__(self, path: str, **kwargs: object) -> None:
            assert path.endswith("planar.dcm")
            assert kwargs == {"normalize": True}

        def analyze(self, **kwargs: object) -> None:
            assert kwargs["low_contrast_threshold"] == 0.05
            assert kwargs["high_contrast_threshold"] == 0.5
            assert kwargs["center_override"] == (100.0, 120.0)
            assert kwargs["invert"] is False

        def results_data(self, *, as_dict: bool) -> dict[str, object]:
            assert as_dict is True
            return {"low_contrast": {"visibility": 90}, "warnings": []}

        def plot(self, *, show: bool) -> tuple[list[object], list[str]]:
            assert show is False
            return [plt.figure()], ["Image"]

    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.resolve_runtime_symbol",
        lambda key: (FakePlanar, None) if key == "PLANAR_LEEDS_TOR_18" else (None, "missing"),
    )
    monkeypatch.setattr(
        "rt_connect_api.services.pylinac_adapter.package_fingerprint", lambda: "f" * 64
    )
    result = execute_pylinac(
        "PLANAR_LEEDS_TOR_18",
        source,
        {
            "normalize": True,
            "low_contrast_threshold": 0.05,
            "high_contrast_threshold": 0.5,
            "center_override": [100, 120],
            "invert": False,
        },
    )
    assert result.engine_class == "LeedsTOR"
    assert result.result_snapshot["engine_passed"] is None
    assert result.overlay_filename == "planar_leeds_tor_18-phan-tich.png"
    assert len(result.overlay_bytes or b"") > 0
