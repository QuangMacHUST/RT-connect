"""End-to-end smoke coverage for every locked Pylinac nuclear capability.

The fixture is intentionally synthetic and contains no patient data.  It is
used to prove that the adapter reaches the real Pylinac classes, preserves the
public result contract, and can render an overlay where that class supports
one.  Clinical acceptance still requires representative commissioning data.
"""

from __future__ import annotations

import warnings
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import matplotlib
import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

from rt_connect_api.services.pylinac_adapter import execute_pylinac

matplotlib.use("Agg")


def _gaussian(
    yy: np.ndarray,
    xx: np.ndarray,
    center_y: float,
    center_x: float,
    sigma_y: float,
    sigma_x: float,
    amplitude: float,
) -> np.ndarray:
    return amplitude * np.exp(
        -(((yy - center_y) / sigma_y) ** 2 + ((xx - center_x) / sigma_x) ** 2) / 2
    )


def _write_nm(
    path: Path,
    frames: np.ndarray,
    *,
    pixel_spacing: float,
    rotation: bool = False,
) -> None:
    array = np.asarray(frames, dtype=np.uint16)
    if array.ndim == 2:
        array = array[None, ...]
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
    dataset.Modality = "NM"
    dataset.PatientName = "SYNTHETIC"
    dataset.PatientID = "SYNTHETIC"
    dataset.StudyInstanceUID = generate_uid()
    dataset.SeriesInstanceUID = generate_uid()
    dataset.Rows = int(array.shape[1])
    dataset.Columns = int(array.shape[2])
    dataset.NumberOfFrames = int(array.shape[0])
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelSpacing = [pixel_spacing, pixel_spacing]
    dataset.ActualFrameDuration = 1000
    dataset.SpacingBetweenSlices = 5.0
    if rotation:
        rotation_info = Dataset()
        rotation_info.RotationDirection = "CC"
        rotation_info.StartAngle = 0.0
        rotation_info.AngularStep = 360.0 / array.shape[0]
        dataset.RotationInformationSequence = [rotation_info]
    dataset.PixelData = array.tobytes()
    dataset.save_as(path, write_like_original=False)


def _run_without_pylinac_stderr(
    catalog_key: str, source_path: Path, parameters: dict[str, object]
):
    # Pylinac 3.47.0 currently emits third-party deprecation warnings while
    # processing synthetic NM data.  They are not adapter warnings and should
    # not obscure the concise regression result.
    with (
        warnings.catch_warnings(),
        patch("warnings.showwarning"),
        redirect_stderr(StringIO()),
    ):
        warnings.simplefilter("ignore")
        return execute_pylinac(catalog_key, source_path, parameters)


def test_every_nuclear_capability_reaches_the_locked_pylinac_engine(tmp_path: Path) -> None:
    height = width = 512
    yy, xx = np.mgrid[:height, :width]
    center = height / 2
    base = np.full((height, width), 1000.0)

    moving_frames = []
    for index in range(16):
        angle = 2 * np.pi * index / 16
        moving_frames.append(
            base
            + _gaussian(
                yy,
                xx,
                center + 40 * np.sin(angle),
                center + 40 * np.cos(angle),
                12,
                12,
                12000,
            )
        )
    moving_path = tmp_path / "nuclear-moving.dcm"
    _write_nm(moving_path, np.asarray(moving_frames), pixel_spacing=2.0, rotation=True)

    single_path = tmp_path / "nuclear-single.dcm"
    _write_nm(
        single_path,
        base + _gaussian(yy, xx, center, center, 40, 40, 10000),
        pixel_spacing=1.0,
    )

    bars = np.full((height, width), 100.0)
    for offset in (-100, 100):
        bars += _gaussian(yy, xx, center, center + offset, 4, 6, 30000)
        bars += _gaussian(yy, xx, center + offset, center, 6, 4, 30000)
    four_bar_path = tmp_path / "nuclear-four-bar.dcm"
    _write_nm(four_bar_path, bars, pixel_spacing=1.0)

    quadrants = np.full((height, width), 1000.0)
    for angle in (45, -45, -135, 135):
        x_position = center + 130 * np.cos(np.radians(angle))
        y_position = center + 130 * np.sin(np.radians(angle))
        quadrants += (
            np.hypot(xx - x_position, yy - y_position) < 35
        ) * 2000
    quadrant_path = tmp_path / "nuclear-quadrants.dcm"
    _write_nm(quadrant_path, quadrants, pixel_spacing=1.0)

    spect_frames = np.full((16, height, width), 1000.0)
    sphere_angles = (-10, -70, -130, -190, 110, 50)
    sphere_diameters = (38, 31.8, 25.4, 19.1, 15.9, 12.7)
    for frame_index in range(4, 12):
        spect_frames[frame_index] += 1500
        for angle, diameter in zip(sphere_angles, sphere_diameters, strict=True):
            x_position = center + 94 * np.cos(np.radians(angle))
            y_position = center + 94 * np.sin(np.radians(angle))
            radius = diameter / 2
            depth = np.sqrt(max(radius**2 - (frame_index - 8) ** 2, 0))
            spect_frames[frame_index][
                np.hypot(xx - x_position, yy - y_position) < depth
            ] += 28000
    spect_path = tmp_path / "nuclear-spect.dcm"
    _write_nm(spect_path, spect_frames, pixel_spacing=1.0)

    cases: tuple[tuple[str, Path, dict[str, object]], ...] = (
        ("NUCLEAR_MCR", moving_path, {"frame_duration": 1.0}),
        (
            "NUCLEAR_PU",
            moving_path,
            {"ufov_ratio": 0.95, "cfov_ratio": 0.75, "window_size": 5, "threshold": 0.75},
        ),
        ("NUCLEAR_COR", moving_path, {}),
        ("NUCLEAR_TR", moving_path, {}),
        ("NUCLEAR_SS", single_path, {"activity_mbq": 10.0, "nuclide": "Tc99m"}),
        ("NUCLEAR_FBR", four_bar_path, {"separation_mm": 120.0, "roi_width_mm": 10.0}),
        (
            "NUCLEAR_QR",
            quadrant_path,
            {
                "bar_widths": [10.0, 12.0, 14.0, 16.0],
                "roi_diameter_mm": 50.0,
                "distance_from_center_mm": 130.0,
            },
        ),
        (
            "NUCLEAR_TU",
            spect_path,
            {
                "first_frame": 0,
                "last_frame": -1,
                "ufov_ratio": 0.8,
                "cfov_ratio": 0.75,
                "center_ratio": 0.4,
                "threshold": 0.75,
                "window_size": 5,
            },
        ),
        (
            "NUCLEAR_TC",
            spect_path,
            {
                "sphere_diameters_mm": list(sphere_diameters),
                "sphere_angles": list(sphere_angles),
                "ufov_ratio": 0.8,
                "search_window_px": 5,
                "search_slices": 3,
            },
        ),
    )

    for catalog_key, source_path, parameters in cases:
        result = _run_without_pylinac_stderr(catalog_key, source_path, parameters)
        assert result.catalog_key == catalog_key
        assert result.engine_version == "3.47.0"
        assert result.result_snapshot["engine"] == "pylinac"
        metrics = result.result_snapshot["metrics"]
        assert isinstance(metrics, dict)
        assert metrics
