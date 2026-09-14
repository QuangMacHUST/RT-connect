from __future__ import annotations

import numpy as np
import pytest

from rt_connect_api.services.gamma_engine import GammaEngineError, MeasurementDataset
from rt_connect_api.services.pylinac_gamma_adapter import calculate_pylinac_gamma


def _dataset(
    values: list[float] | list[list[float]], *, spacing: tuple[float, ...]
) -> MeasurementDataset:
    array = np.asarray(values, dtype=np.float64)
    return MeasurementDataset(
        dataset_id="fixture",
        values=array,
        spacing_mm=spacing,
        origin_mm=(0.0,) * len(spacing),
        units={"dose": "GY", "position": "mm"},
        source_format="synthetic_fixture",
    )


def _configuration(**overrides: object) -> dict[str, object]:
    configuration: dict[str, object] = {
        "dimensionality": "1D",
        "dose_difference_percent": 3.0,
        "dose_difference_mode": "RELATIVE",
        "distance_to_agreement_mm": 3.0,
        "dose_threshold_percent": 0.0,
        "normalization": "GLOBAL",
        "interpolation": "GRID",
        "coverage_policy": "FULL_ROI",
        "max_gamma": 2.0,
        "pass_rate_threshold_percent": 95.0,
        "histogram_bins": 10,
        "resolution_factor": 3,
    }
    configuration.update(overrides)
    return configuration


def test_pylinac_1d_is_the_executed_engine() -> None:
    reference = _dataset([10, 20, 30, 40, 50], spacing=(1.0,))
    evaluation = _dataset([10, 20, 30, 40, 50], spacing=(1.0,))

    result = calculate_pylinac_gamma(reference, evaluation, _configuration())

    assert result["engine"] == "pylinac"
    assert result["engine_class"] == "gamma_1d"
    assert result["algorithm"] == "pylinac.core.gamma.gamma_1d"
    assert result["overall_status"] == "PASS"
    assert result["metrics"]["pass_rate_percent"] == 100.0
    assert result["metrics"]["histogram"]["counts"]
    assert result["gamma_map"][0]["coordinate_mm"] == 0.0


def test_pylinac_2d_converts_dta_mm_to_integer_grid_distance() -> None:
    reference = _dataset([[10, 20, 30], [20, 30, 40], [30, 40, 50]], spacing=(1.0, 1.0))
    evaluation = _dataset([[10, 20, 30], [20, 30, 40], [30, 40, 50]], spacing=(1.0, 1.0))

    result = calculate_pylinac_gamma(
        reference,
        evaluation,
        _configuration(dimensionality="2D"),
    )

    assert result["engine_class"] == "gamma_2d"
    assert result["algorithm"] == "pylinac.core.gamma.gamma_2d"
    assert result["overall_status"] == "PASS"
    assert result["metrics"]["evaluated_points"] == 9
    assert len(result["gamma_map"]) == 9


def test_pylinac_2d_rejects_dta_not_aligned_to_grid() -> None:
    reference = _dataset([[10, 20], [20, 30]], spacing=(2.0, 2.0))
    evaluation = _dataset([[10, 20], [20, 30]], spacing=(2.0, 2.0))

    with pytest.raises(GammaEngineError) as error:
        calculate_pylinac_gamma(
            reference,
            evaluation,
            _configuration(dimensionality="2D", distance_to_agreement_mm=3.0),
        )

    assert error.value.code == "GAMMA_DTA_GRID_INCOMPATIBLE"


@pytest.mark.parametrize(
    ("key", "value", "code"),
    [
        ("dimensionality", "3D", "GAMMA_PYLINAC_DIMENSIONALITY_UNSUPPORTED"),
        ("dose_difference_mode", "ABSOLUTE", "GAMMA_PYLINAC_ABSOLUTE_UNSUPPORTED"),
        ("interpolation", "BILINEAR", "GAMMA_PYLINAC_INTERPOLATION_UNSUPPORTED"),
    ],
)
def test_pylinac_adapter_rejects_unsupported_new_configuration(
    key: str, value: object, code: str
) -> None:
    reference = _dataset([10, 20, 30], spacing=(1.0,))
    evaluation = _dataset([10, 20, 30], spacing=(1.0,))

    with pytest.raises(GammaEngineError) as error:
        calculate_pylinac_gamma(reference, evaluation, _configuration(**{key: value}))

    assert error.value.code == code
