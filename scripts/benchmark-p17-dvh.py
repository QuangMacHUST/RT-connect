"""Benchmark the P17 DVH engine with a deterministic synthetic large workload.

This is an engine-only benchmark.  It creates temporary, non-patient RTDOSE and
RTSTRUCT files, measures wall-clock time and Python-traced allocations, and
never writes a database, queue message, report, or object-storage record.
The process also reports its operating-system peak resident set size when the
runtime exposes ``resource.getrusage``.  That is a measurement for this
short-lived benchmark process, not an inference from Docker sampling or a
container cgroup counter; the deployment/load runner still owns the
service-level CPU/RAM/concurrency gate.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, RTDoseStorage, RTStructureSetStorage

# Keep the benchmark runnable from a clean repository checkout without asking
# the operator to export a PYTHONPATH first.  The production package is under
# apps/api/src and this script intentionally imports the same engine used by
# the API; it does not install or mutate the application environment.
REPO_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = REPO_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SOURCE))

from rt_connect_api.services.dose_dvh_engine import DVH_ENGINE_VERSION, analyze_dvh  # noqa: E402

try:
    import resource as _resource
except ImportError:  # pragma: no cover - Windows does not expose resource.
    _resource = None

FIXTURE_UID_ROOT = "1.2.826.0.1.3680043.8.498.999.20"


def _repository_sha() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _peak_rss_bytes() -> int | None:
    """Return process peak RSS in bytes when the host runtime exposes it."""

    if _resource is None:
        return None
    usage = float(_resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss)
    if usage <= 0:
        return None
    # Linux and the other Unix implementations used by our containers report
    # ru_maxrss in KiB; macOS reports bytes.  Keep the evidence explicit so a
    # Windows/local run with no ``resource`` module is not mislabelled.
    multiplier = 1 if sys.platform == "darwin" else 1024
    return int(usage * multiplier)


def _parse_shape(value: str) -> tuple[int, int, int]:
    try:
        parts = tuple(int(item) for item in value.lower().split("x"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("shape must be FRAMESxROWSxCOLUMNS") from exc
    if len(parts) != 3 or any(item <= 0 for item in parts):
        raise argparse.ArgumentTypeError("shape must contain three positive integers")
    return parts  # type: ignore[return-value]


def _file_dataset(path: Path, storage_uid: str, sop_suffix: str) -> FileDataset:
    sop_uid = f"{FIXTURE_UID_ROOT}.{sop_suffix}"
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = storage_uid
    meta.MediaStorageSOPInstanceUID = sop_uid
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = f"{FIXTURE_UID_ROOT}.1"
    dataset = FileDataset(path, {}, file_meta=meta, preamble=b"\0" * 128)
    dataset.SOPClassUID = storage_uid
    dataset.SOPInstanceUID = sop_uid
    dataset.StudyInstanceUID = f"{FIXTURE_UID_ROOT}.2"
    dataset.SeriesInstanceUID = f"{FIXTURE_UID_ROOT}.{sop_suffix}0"
    return dataset


def _build_dose(path: Path, shape: tuple[int, int, int]) -> str:
    frames, rows, columns = shape
    frame_uid = f"{FIXTURE_UID_ROOT}.4"
    dataset = _file_dataset(path, RTDoseStorage, "5")
    dataset.FrameOfReferenceUID = frame_uid
    dataset.Modality = "RTDOSE"
    dataset.Rows = rows
    dataset.Columns = columns
    dataset.NumberOfFrames = frames
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    dataset.BitsAllocated = 16
    dataset.BitsStored = 16
    dataset.HighBit = 15
    dataset.PixelRepresentation = 0
    dataset.PixelSpacing = [2.0, 2.0]
    dataset.SliceThickness = 3.0
    dataset.SpacingBetweenSlices = 3.0
    dataset.ImagePositionPatient = [0.0, 0.0, 0.0]
    dataset.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    dataset.GridFrameOffsetVector = [float(index * 3) for index in range(frames)]
    dataset.DoseGridScaling = 0.01
    dataset.DoseUnits = "GY"
    dataset.DoseType = "PHYSICAL"
    dataset.DoseSummationType = "PLAN"
    # Four repeated physical-dose levels keep the benchmark deterministic and
    # exercise volume-weighted metrics without making the oracle depend on a
    # million distinct quantile levels.
    frame, row, column = np.indices(shape)
    raw_values = (((frame + row + column) % 4) + 1).astype(np.uint16) * 100
    dataset.PixelData = raw_values.tobytes()
    dataset.save_as(path, write_like_original=False)
    return frame_uid


def _build_structure(path: Path, shape: tuple[int, int, int], frame_uid: str) -> None:
    frames, rows, columns = shape
    dataset = _file_dataset(path, RTStructureSetStorage, "6")
    dataset.FrameOfReferenceUID = frame_uid
    dataset.Modality = "RTSTRUCT"
    # StructureSetLabel has VR SH (maximum 16 characters).
    dataset.StructureSetLabel = "P17_BENCHMARK"

    referenced_frame = Dataset()
    referenced_frame.FrameOfReferenceUID = frame_uid
    dataset.ReferencedFrameOfReferenceSequence = [referenced_frame]

    roi = Dataset()
    roi.ROINumber = 1
    roi.ReferencedFrameOfReferenceUID = frame_uid
    roi.ROIName = "P17_BENCHMARK_ROI"
    roi.ROIGenerationAlgorithm = "MANUAL"
    dataset.StructureSetROISequence = [roi]

    contour_group = Dataset()
    contour_group.ReferencedROINumber = 1
    max_row = rows * 2.0 - 1.0
    max_column = columns * 2.0 - 1.0
    contours: list[Dataset] = []
    for frame_index in range(frames):
        contour = Dataset()
        contour.ContourGeometricType = "CLOSED_PLANAR"
        contour.NumberOfContourPoints = 4
        z = float(frame_index * 3)
        contour.ContourData = [
            -1.0,
            -1.0,
            z,
            -1.0,
            max_row,
            z,
            max_column,
            max_row,
            z,
            max_column,
            -1.0,
            z,
        ]
        contours.append(contour)
    contour_group.ContourSequence = contours
    dataset.ROIContourSequence = [contour_group]
    dataset.save_as(path, write_like_original=False)


def _run_once(
    dose_path: Path, structure_path: Path
) -> tuple[float, int, int | None, dict[str, Any]]:
    tracemalloc.start()
    started = time.perf_counter()
    result = analyze_dvh(
        dose_path,
        structure_path,
        roi_number=1,
        dx_percentages=[50.0, 95.0],
        vx_doses_gy=[2.0],
        max_voxels=2_000_000,
        preview_limit=4096,
    )
    elapsed = time.perf_counter() - started
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, peak, _peak_rss_bytes(), result.result


def run_benchmark(shape: tuple[int, int, int], repeats: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="rt-connect-p17-benchmark-") as directory:
        root = Path(directory)
        dose_path = root / "dose.dcm"
        structure_path = root / "structure.dcm"
        frame_uid = _build_dose(dose_path, shape)
        _build_structure(structure_path, shape, frame_uid)

        observations: list[dict[str, Any]] = []
        result: dict[str, Any] = {}
        for index in range(repeats):
            elapsed, peak, peak_rss, result = _run_once(dose_path, structure_path)
            observations.append(
                {
                    "iteration": index + 1,
                    "elapsed_seconds": elapsed,
                    "peak_traced_bytes": peak,
                    "peak_rss_bytes": peak_rss,
                }
            )

    elapsed_values = [float(item["elapsed_seconds"]) for item in observations]
    peak_values = [int(item["peak_traced_bytes"]) for item in observations]
    rss_values = [
        int(item["peak_rss_bytes"])
        for item in observations
        if item["peak_rss_bytes"] is not None
    ]
    return {
        "schema_version": "rt-connect.p17-volume-benchmark.v1",
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "repository_sha": _repository_sha(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "workload": {
            "shape_frames_rows_columns": list(shape),
            "voxel_count": int(np.prod(shape)),
            "roi": "full grid, one closed contour per frame",
            "dose_levels_gy": [1.0, 2.0, 3.0, 4.0],
            "patient_data": False,
        },
        "engine_key": result["engine_key"],
        "engine_version": DVH_ENGINE_VERSION,
        "result_oracle": {
            "selected_voxel_count": result["coverage"]["selected_voxel_count"],
            "volume_cc": result["metrics"]["volume_cc"],
            "dmean_gy": result["metrics"]["Dmean_gy"],
            "dmin_gy": result["metrics"]["Dmin_gy"],
            "dmax_gy": result["metrics"]["Dmax_gy"],
        },
        "observations": observations,
        "summary": {
            "repeats": repeats,
            "elapsed_seconds_min": min(elapsed_values),
            "elapsed_seconds_median": statistics.median(elapsed_values),
            "elapsed_seconds_max": max(elapsed_values),
            "peak_traced_bytes_max": max(peak_values),
            "peak_rss_bytes_max": max(rss_values) if rss_values else None,
            "rss_measured": bool(rss_values),
            "rss_measurement_source": (
                "resource.getrusage(RUSAGE_SELF).ru_maxrss"
                if rss_values
                else "unavailable"
            ),
            "performance_gate": "NOT_ASSESSED",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", type=_parse_shape, default=(64, 128, 128))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repeats < 1 or arguments.repeats > 20:
        parser.error("repeats must be between 1 and 20")
    payload = run_benchmark(arguments.shape, arguments.repeats)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
