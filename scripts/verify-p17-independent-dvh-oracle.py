"""Compare the P17 DVH engine with an independent known-answer oracle.

The reference calculation intentionally uses only the committed synthetic
fixture's declared four selected voxels and simple arithmetic. It does not
call the engine's geometry, masking, metric or interpolation helpers. This is
an engineering oracle for the fixture, not a clinical commissioning result.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pydicom

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

from rt_connect_api.services.dose_dvh_engine import DVH_ENGINE_VERSION, analyze_dvh  # noqa: E402


EXPECTED_INDICES = ((1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1))
EXPECTED_CONTOUR = (
    (-0.5, -0.5, 1.0),
    (1.5, -0.5, 1.0),
    (1.5, 1.5, 1.0),
    (-0.5, 1.5, 1.0),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_sha() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _dose_levels(dose_path: Path) -> tuple[np.ndarray, list[float]]:
    dataset = pydicom.dcmread(dose_path, force=False)
    if dataset.Modality != "RTDOSE" or dataset.DoseUnits != "GY":
        raise ValueError("The committed oracle fixture must be a physical-dose RTDOSE in Gy.")
    pixels = np.asarray(dataset.pixel_array, dtype=np.float64)
    if pixels.ndim == 2:
        pixels = pixels[np.newaxis, ...]
    scaling = float(dataset.DoseGridScaling)
    selected = np.asarray([pixels[index] * scaling for index in EXPECTED_INDICES], dtype=float)
    spacing = [float(value) for value in dataset.PixelSpacing]
    offsets = [float(value) for value in dataset.GridFrameOffsetVector]
    if spacing != [1.0, 1.0] or offsets != [0.0, 1.0]:
        raise ValueError("The committed oracle fixture geometry changed; refresh the oracle explicitly.")
    voxel_volumes = [spacing[0] * spacing[1] * (offsets[1] - offsets[0]) / 1000.0] * len(selected)
    return selected, voxel_volumes


def _assert_fixture_structure(structure_path: Path) -> None:
    dataset = pydicom.dcmread(structure_path, force=False)
    roi = next(
        item for item in dataset.StructureSetROISequence if int(item.ROINumber) == 1
    )
    contour_group = next(
        item for item in dataset.ROIContourSequence if int(item.ReferencedROINumber) == 1
    )
    contour = contour_group.ContourSequence[0]
    points = np.asarray(contour.ContourData, dtype=float).reshape(-1, 3)
    if not np.allclose(points, np.asarray(EXPECTED_CONTOUR), atol=1e-9, rtol=0):
        raise ValueError("The committed oracle structure contour changed; refresh the oracle explicitly.")
    if str(roi.ROIName) != "P17_TARGET":
        raise ValueError("The committed oracle ROI changed; refresh the oracle explicitly.")


def reference_oracle(dose_path: Path, structure_path: Path) -> dict[str, Any]:
    _assert_fixture_structure(structure_path)
    dose_values, voxel_volumes = _dose_levels(dose_path)
    values = dose_values.reshape(-1)
    volumes = np.asarray(voxel_volumes, dtype=np.float64)
    total_volume = float(volumes.sum())
    weighted_mean = float(np.sum(values * volumes) / total_volume)
    levels_and_volumes = sorted(zip(values.tolist(), volumes.tolist(), strict=True), reverse=True)
    levels = [float(level) for level, _volume in levels_and_volumes]
    level_volumes = [float(volume) for _level, volume in levels_and_volumes]
    cumulative = np.cumsum(level_volumes)

    def dx(percent: float) -> float:
        target_volume = total_volume * percent / 100.0
        if target_volume <= cumulative[0]:
            return levels[0]
        for index in range(1, len(levels)):
            if target_volume <= cumulative[index]:
                fraction = (target_volume - cumulative[index - 1]) / (
                    cumulative[index] - cumulative[index - 1]
                )
                return levels[index - 1] + fraction * (levels[index] - levels[index - 1])
        return levels[-1]

    return {
        "selected_voxel_count": int(values.size),
        "volume_cc": total_volume,
        "Dmin_gy": float(values.min()),
        "Dmean_gy": weighted_mean,
        "Dmax_gy": float(values.max()),
        "Dx_gy": {f"D{percent:g}_gy": dx(percent) for percent in (2.0, 50.0, 95.0, 98.0)},
        "Vx_percent": {
            f"V{dose:g}_gy": float(np.sum(volumes[values >= dose]) / total_volume * 100.0)
            for dose in (0.0, 5.0, 8.0, 20.0)
        },
    }


def _observed_metrics(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_voxel_count": result["coverage"]["selected_voxel_count"],
        "volume_cc": result["metrics"]["volume_cc"],
        "Dmin_gy": result["metrics"]["Dmin_gy"],
        "Dmean_gy": result["metrics"]["Dmean_gy"],
        "Dmax_gy": result["metrics"]["Dmax_gy"],
        "Dx_gy": result["metrics"]["Dx_gy"],
        "Vx_percent": result["metrics"]["Vx_percent"],
    }


def run(dose_path: Path, structure_path: Path) -> dict[str, Any]:
    expected = reference_oracle(dose_path, structure_path)
    analysis = analyze_dvh(
        dose_path,
        structure_path,
        roi_number=1,
        dx_percentages=[2.0, 50.0, 95.0, 98.0],
        vx_doses_gy=[0.0, 5.0, 8.0, 20.0],
    )
    observed = _observed_metrics(analysis.result)
    comparisons: list[dict[str, Any]] = []

    def compare(name: str, expected_value: Any, observed_value: Any) -> None:
        if isinstance(expected_value, dict):
            for key, value in expected_value.items():
                compare(f"{name}.{key}", value, observed_value.get(key))
            return
        if isinstance(expected_value, float):
            passed = observed_value is not None and bool(np.isclose(expected_value, observed_value, atol=1e-9, rtol=0))
        else:
            passed = expected_value == observed_value
        comparisons.append(
            {"name": name, "expected": expected_value, "observed": observed_value, "passed": passed}
        )

    for key, value in expected.items():
        compare(key, value, observed[key])

    return {
        "schema_version": "rt-connect.p17-independent-dvh-oracle.v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_sha": repository_sha(),
        "fixture_sha256": {
            "dose": sha256(dose_path),
            "structure": sha256(structure_path),
        },
        "engine": {"key": analysis.result["engine_key"], "version": DVH_ENGINE_VERSION},
        "reference_oracle": expected,
        "observed_engine_metrics": observed,
        "comparisons": comparisons,
        "passed": all(item["passed"] for item in comparisons),
        "limitations": [
            "The oracle is a committed synthetic known-answer fixture, not a vendor/reference implementation for arbitrary clinical data.",
            "This run is local engineering evidence and does not close staging, commissioning or clinical release gates.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dose",
        type=Path,
        default=ROOT / "docs" / "fixtures" / "gamma-rtdose-v1-smoke.dcm",
    )
    parser.add_argument(
        "--structure",
        type=Path,
        default=ROOT / "docs" / "fixtures" / "p17-rtstruct-v1-smoke.dcm",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "evidence" / "p17-independent-dvh-oracle-20260909.json",
    )
    args = parser.parse_args()
    report = run(args.dose.resolve(), args.structure.resolve())
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.resolve().write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
