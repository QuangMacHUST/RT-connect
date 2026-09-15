"""End-to-end smoke coverage for the locked Pylinac contrib capabilities.

The Quasar fixture is derived from Pylinac's official FC-2 demo image and
adds only four synthetic central markers in a temporary copy.  The Jaw image
is a synthetic rectangular RTIMAGE.  Neither fixture contains patient data;
clinical commissioning still requires representative machine data.
"""

from __future__ import annotations

import warnings
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import matplotlib
import numpy as np
import pydicom
import pylinac
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

from rt_connect_api.services.pylinac_adapter import execute_pylinac

matplotlib.use("Agg")


def _run_without_pylinac_stderr(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
):
    with (
        warnings.catch_warnings(),
        patch("warnings.showwarning"),
        redirect_stderr(StringIO()),
    ):
        warnings.simplefilter("ignore")
        return execute_pylinac(catalog_key, source_path, parameters)


def _write_quasar_fixture(path: Path) -> None:
    demo_path = Path(pylinac.__file__).resolve().parent / "demo_files" / "fc2.dcm"
    dataset = pydicom.dcmread(demo_path)
    pixels = dataset.pixel_array.copy()
    center_y, center_x = (dimension // 2 for dimension in pixels.shape)
    pixel_spacing = float(dataset.ImagePlanePixelSpacing[0])
    sid = float(dataset.RTImageSID)
    sad = float(dataset.RadiationMachineSAD)
    dpmm = (1 / pixel_spacing) * (sid / sad)

    # The locked FC-2 sample already has one central marker.  Four additional
    # markers make the temporary image satisfy Quasar's five-marker contract.
    central_window = pixels[center_y - 20 : center_y + 20, center_x - 20 : center_x + 20]
    marker_value = int(np.percentile(central_window, 99.5))
    yy, xx = np.ogrid[: pixels.shape[0], : pixels.shape[1]]
    for x_mm, y_mm in ((-10, -10), (10, -10), (-10, 10), (10, 10)):
        x = int(round(center_x + x_mm * dpmm))
        y = int(round(center_y + y_mm * dpmm))
        marker = (xx - x) ** 2 + (yy - y) ** 2 <= 8**2
        pixels[marker] = marker_value

    dataset.PixelData = pixels.astype(dataset.pixel_array.dtype).tobytes()
    dataset.save_as(path, write_like_original=False)


def _write_jaw_fixture(path: Path) -> None:
    pixels = np.zeros((256, 256), dtype=np.uint16)
    pixels[64:192, 64:192] = 50000
    meta = FileMetaDataset()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.ImplementationClassUID = generate_uid()
    dataset = FileDataset(str(path), {}, file_meta=meta, preamble=b"\0" * 128)
    dataset.is_little_endian = True
    dataset.is_implicit_VR = False
    dataset.SOPClassUID = SecondaryCaptureImageStorage
    dataset.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    dataset.Modality = "RTIMAGE"
    dataset.PatientName = "SYNTHETIC"
    dataset.PatientID = "SYNTHETIC"
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = generate_uid()
    dataset.Rows = pixels.shape[0]
    dataset.Columns = pixels.shape[1]
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelData = pixels.tobytes()
    dataset.save_as(path, write_like_original=False)


def test_quasar_contrib_reaches_locked_pylinac_engine(tmp_path: Path) -> None:
    source = tmp_path / "quasar.dcm"
    _write_quasar_fixture(source)

    result = _run_without_pylinac_stderr(
        "CONTRIB_QUASAR_LIGHT_RAD_SCALING",
        source,
        {"normalize": True, "invert": False, "fwxm": 50, "bb_edge_threshold_mm": 10},
    )

    assert result.catalog_key == "CONTRIB_QUASAR_LIGHT_RAD_SCALING"
    assert result.engine_class == "QuasarLightRadScaling"
    assert result.engine_version == "3.47.0"
    assert result.result_snapshot["engine"] == "pylinac"
    assert result.result_snapshot["result_source"] == "results_data"
    assert result.result_snapshot["metrics"]
    assert result.overlay_bytes is not None
    assert result.overlay_media_type == "image/png"


def test_jaw_orthogonality_contrib_reaches_locked_pylinac_engine(
    tmp_path: Path,
) -> None:
    source = tmp_path / "jaw.dcm"
    _write_jaw_fixture(source)

    result = _run_without_pylinac_stderr(
        "CONTRIB_JAW_ORTHOGONALITY", source, {}
    )

    assert result.catalog_key == "CONTRIB_JAW_ORTHOGONALITY"
    assert result.engine_class == "JawOrthogonality"
    assert result.engine_version == "3.47.0"
    assert result.result_snapshot["engine"] == "pylinac"
    assert result.result_snapshot["result_source"] == "results"
    assert set(result.result_snapshot["metrics"]) == {
        "top_left",
        "top_right",
        "bottom_left",
        "bottom_right",
    }
    assert result.overlay_bytes is not None
    assert result.overlay_media_type == "image/png"
