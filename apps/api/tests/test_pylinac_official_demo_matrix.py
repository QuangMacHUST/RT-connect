"""Run every currently available official Pylinac demo through the RT-CONNECT adapter.

This is a runtime smoke matrix, not clinical commissioning evidence.  The
important property is that the same adapter used by the API reaches the locked
Pylinac engine, returns a non-empty structured result, and renders an overlay
where the engine exposes one.  The matrix intentionally excludes capabilities
whose official demo data is not shipped in the locked wheel; those gaps remain
explicit P7 fixture work.
"""

from __future__ import annotations

import shutil
import warnings
import zipfile
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import matplotlib
import pylinac
import pytest

from rt_connect_api.services.pylinac_adapter import PylinacExecutionResult, execute_pylinac

matplotlib.use("Agg")


DEMO_ROOT = Path(pylinac.__file__).resolve().parent / "demo_files"


def _multi_target_demo_arrangement() -> list[dict[str, object]]:
    """Return the six-bi arrangement documented by Pylinac's demo runner."""

    return [
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
        {
            "name": "2",
            "offset_left_mm": -30,
            "offset_up_mm": 0,
            "offset_in_mm": 15,
            "bb_size_mm": 5,
            "rad_size_mm": 20,
        },
        {
            "name": "3",
            "offset_left_mm": 0,
            "offset_up_mm": 0,
            "offset_in_mm": -30,
            "bb_size_mm": 5,
            "rad_size_mm": 20,
        },
        {
            "name": "4",
            "offset_left_mm": 30,
            "offset_up_mm": 0,
            "offset_in_mm": -50,
            "bb_size_mm": 5,
            "rad_size_mm": 20,
        },
        {
            "name": "5",
            "offset_left_mm": 0,
            "offset_up_mm": 0,
            "offset_in_mm": -70,
            "bb_size_mm": 5,
            "rad_size_mm": 20,
        },
    ]


def _official_cases() -> tuple[tuple[str, str, str, dict[str, object]], ...]:
    planar = (
        ("PLANAR_LEEDS_TOR_18", "leeds.dcm"),
        ("PLANAR_LEEDS_TOR_BLUE", "leeds.dcm"),
        ("PLANAR_STANDARD_IMAGING_QC3", "qc3.dcm"),
        ("PLANAR_STANDARD_IMAGING_QC_KV", "SI-QC-kV.dcm"),
        ("PLANAR_LAS_VEGAS", "lasvegas.dcm"),
        ("PLANAR_ELEKTA_LAS_VEGAS", "elekta_las_vegas.dcm"),
        ("PLANAR_DOSELAB_MC2_MV", "Doselab_MV.dcm"),
        ("PLANAR_DOSELAB_MC2_KV", "Doselab_kV.dcm"),
        ("PLANAR_SNC_MV", "SNC-MV.dcm"),
        ("PLANAR_SNC_MV_12510", "SNC_MV_12510.dcm"),
        ("PLANAR_SNC_KV", "SNC-kV.dcm"),
        ("PLANAR_PTW_EPID_QC", "PTW-EPID-QC.dcm"),
        ("PLANAR_IBA_PRIMUS_A", "iba_primus.dcm"),
        ("PLANAR_STANDARD_IMAGING_FC2", "fc2.dcm"),
        ("PLANAR_IMT_LRAD", "imtlrad.dcm"),
        ("PLANAR_DOSELAB_RLF", "Doselab_RLf.dcm"),
        ("PLANAR_PTW_ISO_ALIGN", "ptw_isoalign.dcm"),
        ("PLANAR_SNC_FSQA", "FSQA_15x15.dcm"),
        ("PLANAR_ACR_DIGITAL_MAMMOGRAPHY", "ACRDigitalMammography.dcm"),
    )
    return (
        ("PICKET_FENCE", "AS1200.dcm", "file", {}),
        ("STARSHOT", "starshot.tif", "file", {"sid": 1000}),
        ("WINSTON_LUTZ", "winston_lutz.zip", "zip", {"sid": 1000}),
        (
            "WINSTON_LUTZ_MULTI_TARGET",
            "SNC_MTWL_demo.zip",
            "zip",
            {"bb_arrangement": _multi_target_demo_arrangement()},
        ),
        ("VMAT_DRGS", "drgs.zip", "vmat", {}),
        ("VMAT_DRMLC", "drmlc.zip", "vmat", {}),
        ("VMAT_DRCS", "drcs.zip", "vmat", {}),
        ("CATPHAN_503", "CatPhan503.zip", "zip", {}),
        ("CATPHAN_504", "CatPhan504.zip", "zip", {}),
        ("CATPHAN_600", "CatPhan600.zip", "zip", {}),
        ("CATPHAN_604", "CatPhan604.zip", "zip", {}),
        ("CHEESE_TOMO", "TomoCheese.zip", "zip", {}),
        ("QUART_DVT", "quart.zip", "zip", {}),
        ("QUART_HYPERSIGHT", "quart.zip", "zip", {}),
        *tuple(
            (
                key,
                filename,
                "file",
                {"ssd": 1395} if key == "PLANAR_IBA_PRIMUS_A" else {},
            )
            for key, filename in planar
        ),
        ("FIELD_PROFILE_ANALYSIS", "AS1200.dcm", "file", {}),
        ("FIELD_ANALYSIS_LEGACY", "AS1200.dcm", "file", {}),
        ("LOG_DYNALOG", "dynalog", "dynalog", {}),
        ("LOG_TRAJECTORY_2_1", "Tlog.bin", "file", {}),
    )


def _source_for_case(tmp_path: Path, filename: str, profile: str) -> Path:
    if profile == "vmat":
        source = DEMO_ROOT / filename
        assert source.exists(), f"Thiếu tệp mẫu chính thức trong wheel: {filename}"
        destination = tmp_path / filename.removesuffix(".zip")
        destination.mkdir()
        with zipfile.ZipFile(source) as archive:
            archive.extractall(destination)
        return destination
    if profile == "dynalog":
        destination = tmp_path / "dynalog"
        destination.mkdir()
        for item in ("AQA.dlg", "BQA.dlg"):
            source = DEMO_ROOT / item
            assert source.exists(), f"Thiếu tệp mẫu chính thức trong wheel: {item}"
            shutil.copy2(source, destination / item)
        return destination
    source = DEMO_ROOT / filename
    assert source.exists(), f"Thiếu tệp mẫu chính thức trong wheel: {filename}"
    return source


@pytest.mark.parametrize(
    "catalog_key,filename,profile,parameters",
    _official_cases(),
    ids=lambda case: case[0] if isinstance(case, tuple) else str(case),
)
def test_official_demo_reaches_locked_pylinac_adapter(
    tmp_path: Path,
    catalog_key: str,
    filename: str,
    profile: str,
    parameters: dict[str, object],
) -> None:
    source = _source_for_case(tmp_path, filename, profile)
    with (
        warnings.catch_warnings(),
        patch("warnings.showwarning"),
        redirect_stderr(StringIO()),
    ):
        warnings.simplefilter("ignore")
        result = execute_pylinac(catalog_key, source, parameters)

    assert isinstance(result, PylinacExecutionResult)
    assert result.engine_version == "3.47.0"
    assert result.result_snapshot["engine"] == "pylinac"
    assert result.result_snapshot["engine_class"] == result.engine_class
    metrics = result.result_snapshot["metrics"]
    assert isinstance(metrics, dict) and metrics
    if result.overlay_bytes is not None:
        assert len(result.overlay_bytes) > 0
        assert result.overlay_media_type == "image/png"


@pytest.mark.parametrize(
    "catalog_key,filename,profile,parameters,metric_path,expected",
    (
        ("PICKET_FENCE", "AS1200.dcm", "file", {}, ("max_error_mm",), 0.08977424727657998),
        ("WINSTON_LUTZ", "winston_lutz.zip", "zip", {"sid": 1000}, ("max_2d_cax_to_bb_mm",), 1.2351661807567378),
        (
            "WINSTON_LUTZ_MULTI_TARGET",
            "SNC_MTWL_demo.zip",
            "zip",
            {"bb_arrangement": _multi_target_demo_arrangement()},
            ("max_2d_field_to_bb_mm",),
            0.9430396381696953,
        ),
        ("VMAT_DRGS", "drgs.zip", "vmat", {}, ("max_deviation_percent",), 1.7785989166030163),
        ("VMAT_DRMLC", "drmlc.zip", "vmat", {}, ("max_deviation_percent",), 0.8179036281768219),
        ("VMAT_DRCS", "drcs.zip", "vmat", {}, ("max_deviation_percent",), 0.3848613270427137),
        (
            "FIELD_PROFILE_ANALYSIS",
            "AS1200.dcm",
            "file",
            {},
            ("x_metrics", "Flatness (Difference) (%)"),
            44.77022249948014,
        ),
        (
            "FIELD_PROFILE_ANALYSIS",
            "AS1200.dcm",
            "file",
            {},
            ("y_metrics", "Flatness (Difference) (%)"),
            26.441515650741355,
        ),
        (
            "FIELD_ANALYSIS_LEGACY",
            "AS1200.dcm",
            "file",
            {},
            ("protocol_results", "flatness_horizontal"),
            44.78017532604955,
        ),
        (
            "FIELD_ANALYSIS_LEGACY",
            "AS1200.dcm",
            "file",
            {},
            ("protocol_results", "flatness_vertical"),
            20.294748024265772,
        ),
        ("CATPHAN_503", "CatPhan503.zip", "zip", {}, ("ctp404", "low_contrast_visibility"), 6.952952537530281),
        ("CATPHAN_504", "CatPhan504.zip", "zip", {}, ("ctp404", "low_contrast_visibility"), 3.468561072408424),
        ("CATPHAN_600", "CatPhan600.zip", "zip", {}, ("ctp404", "low_contrast_visibility"), 5.432720420862056),
        ("CATPHAN_604", "CatPhan604.zip", "zip", {}, ("ctp404", "low_contrast_visibility"), 3.3136010489079224),
        ("CHEESE_TOMO", "TomoCheese.zip", "zip", {}, ("phantom_roll",), -0.2360965372507735),
        ("QUART_DVT", "quart.zip", "zip", {}, ("phantom_roll_deg",), 0.18427310316724288),
        ("PLANAR_LEEDS_TOR_18", "leeds.dcm", "file", {}, ("percent_integral_uniformity",), 91.81275923121922),
        ("PLANAR_LAS_VEGAS", "lasvegas.dcm", "file", {}, ("percent_integral_uniformity",), 98.39548559127846),
        ("PLANAR_SNC_MV", "SNC-MV.dcm", "file", {}, ("median_cnr",), 81.18600407100408),
        ("PLANAR_ACR_DIGITAL_MAMMOGRAPHY", "ACRDigitalMammography.dcm", "file", {}, ("speck_group_score",), 4.5),
    ),
)
def test_official_demo_core_metric_matches_locked_reference(
    tmp_path: Path,
    catalog_key: str,
    filename: str,
    profile: str,
    parameters: dict[str, object],
    metric_path: tuple[str, ...],
    expected: float,
) -> None:
    """Protect the adapter's core metric mapping against silent drift.

    These are locked Pylinac demo references, not an independent clinical
    oracle.  They prove that the selected RT-CONNECT metric remains aligned
    with the pinned engine output while the full commissioning matrix is
    still open.
    """

    source = _source_for_case(tmp_path, filename, profile)
    with (
        warnings.catch_warnings(),
        patch("warnings.showwarning"),
        redirect_stderr(StringIO()),
    ):
        warnings.simplefilter("ignore")
        result = execute_pylinac(catalog_key, source, parameters)

    metrics = result.result_snapshot["metrics"]
    assert isinstance(metrics, dict)
    value: object = metrics
    for key in metric_path:
        assert isinstance(value, dict)
        value = value[key]
    assert value == pytest.approx(expected, rel=1e-7, abs=1e-7)
