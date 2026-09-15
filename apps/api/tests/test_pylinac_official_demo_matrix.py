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
