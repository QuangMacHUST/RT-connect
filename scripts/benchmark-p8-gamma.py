"""Benchmark the deterministic P8 Gamma engine with disposable synthetic grids.

This benchmark is intentionally independent of the API, database, object store,
Railway and patient data.  It measures the worker-side numerical engine on a
repeatable 3D workload, records candidate/resource configuration and keeps an
oracle assertion that identical grids produce zero Gamma and PASS.  The result
is local performance evidence only; it does not claim staging capacity or
clinical commissioning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = REPOSITORY_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SOURCE))

from rt_connect_api.services.gamma_engine import (  # noqa: E402
    ENGINE_VERSION,
    GammaConfiguration,
    MeasurementDataset,
    calculate_gamma,
)


def _parse_shape(value: str) -> tuple[int, ...]:
    parts = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if len(parts) != 3 or any(part < 2 for part in parts):
        raise argparse.ArgumentTypeError("shape must contain three dimensions >= 2, e.g. 16,32,32")
    return parts


def _synthetic_dataset(dataset_id: str, shape: tuple[int, ...]) -> MeasurementDataset:
    total = int(np.prod(shape))
    # A deterministic non-flat dose field prevents the benchmark from only
    # exercising a trivial constant-value branch while identical grids keep
    # the expected Gamma result exactly PASS with gamma 0.
    values = np.linspace(1.0, 4.0, total, dtype=np.float64).reshape(shape)
    frame_id = "1.2.826.0.1.3680043.8.498.999.4"
    return MeasurementDataset(
        dataset_id=dataset_id,
        values=values,
        spacing_mm=(3.0, 3.0, 3.0),
        origin_mm=(0.0, 0.0, 0.0),
        units={"dose": "GY", "position": "mm"},
        source_format="synthetic_benchmark",
        coordinate_frame="PATIENT_LPS",
        frame_id=frame_id,
        axis_order=("z", "y", "x"),
        transform_to_reference=(
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
        ),
    )


def _configuration(candidate_limit: int) -> GammaConfiguration:
    return GammaConfiguration(
        dimensionality="3D",
        dose_difference_percent=3.0,
        dose_difference_mode="RELATIVE",
        absolute_dose_difference_gy=None,
        distance_to_agreement_mm=3.0,
        dose_threshold_percent=0.0,
        normalization="GLOBAL",
        interpolation="GRID",
        pass_rate_threshold_percent=95.0,
        histogram_bins=20,
        coverage_policy="FULL_ROI",
        max_gamma=2.0,
        max_candidate_evaluations=candidate_limit,
    )


def _git_revision() -> str | None:
    try:
        import subprocess

        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def benchmark(shape: tuple[int, ...], iterations: int, candidate_limit: int) -> dict[str, Any]:
    reference = _synthetic_dataset("p8-benchmark-reference", shape)
    evaluation = _synthetic_dataset("p8-benchmark-evaluation", shape)
    configuration = _configuration(candidate_limit)
    elapsed_seconds: list[float] = []
    peak_bytes: list[int] = []
    result: dict[str, Any] | None = None

    for _ in range(iterations):
        tracemalloc.start()
        started = time.perf_counter()
        observed = calculate_gamma(reference, evaluation, configuration)
        elapsed_seconds.append(time.perf_counter() - started)
        _, peak = tracemalloc.get_traced_memory()
        peak_bytes.append(int(peak))
        tracemalloc.stop()
        result = observed

    if result is None:
        raise RuntimeError("benchmark produced no result")
    metrics = result["metrics"]
    if not isinstance(metrics, dict):
        raise RuntimeError("Gamma result metrics are not an object")
    oracle_pass = (
        result.get("overall_status") == "PASS"
        and metrics.get("evaluated_points") == int(np.prod(shape))
        and metrics.get("passing_points") == int(np.prod(shape))
        and metrics.get("pass_rate_percent") == 100.0
        and metrics.get("censored_points") == 0
        and metrics.get("no_candidate_points") == 0
        and float(metrics["percentiles"]["max"]) == 0.0
    )
    return {
        "shape": list(shape),
        "voxel_count": int(np.prod(shape)),
        "iterations": iterations,
        "engine_version": ENGINE_VERSION,
        "configuration": {
            "dimensionality": configuration.dimensionality,
            "interpolation": configuration.interpolation,
            "distance_to_agreement_mm": configuration.distance_to_agreement_mm,
            "max_gamma": configuration.max_gamma,
            "max_candidate_evaluations": configuration.max_candidate_evaluations,
        },
        "timing_seconds": {
            "min": min(elapsed_seconds),
            "median": float(np.median(elapsed_seconds)),
            "max": max(elapsed_seconds),
            "samples": elapsed_seconds,
        },
        "python_traced_peak_bytes": {
            "max": max(peak_bytes),
            "samples": peak_bytes,
        },
        "oracle": {
            "passed": oracle_pass,
            "overall_status": result.get("overall_status"),
            "evaluated_points": metrics.get("evaluated_points"),
            "passing_points": metrics.get("passing_points"),
            "pass_rate_percent": metrics.get("pass_rate_percent"),
            "max_gamma": metrics.get("percentiles", {}).get("max"),
        },
        "data_boundary": "Synthetic identical grids only; no patient, PACS or treatment data.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shape", type=_parse_shape, default=(16, 32, 32))
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--candidate-limit", type=int, default=50_000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be >= 1")
    if args.candidate_limit < 10_000:
        parser.error("--candidate-limit must be >= 10000")

    report = benchmark(args.shape, args.iterations, args.candidate_limit)
    report.update(
        {
            "evidence_id": "P08-LOCAL-GAMMA-WORKLOAD-20260911",
            "phase": "P08",
            "status": "LOCAL_PERFORMANCE_AND_ORACLE",
            "verified_at": datetime.now(UTC).isoformat(),
            "source_commit": _git_revision(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "platform": {"os": os.name, "python": sys.version.split()[0]},
        }
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["oracle"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
