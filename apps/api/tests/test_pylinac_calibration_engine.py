"""End-to-end smoke coverage for all locked Pylinac calibration classes.

The readings are synthetic and are used only to prove that the adapter reaches
the real Pylinac calculation classes and maps their public properties.  They
are not calibration or commissioning evidence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from rt_connect_api.services.pylinac_adapter import PylinacAdapterError, execute_pylinac

_COMMON = {
    "institution": "Synthetic Hospital",
    "physicist": "Synthetic Physicist",
    "unit": "Synthetic Linac",
    "measurement_date": "2026-09-15",
    "electrometer": "Synthetic Electrometer",
    "temp": 22.0,
    "press": 101.3,
    "chamber": "A12",
    "n_dw": 0.05,
    "p_elec": 1.0,
    "voltage_reference": 300,
    "voltage_reduced": 150,
    "m_reference": [10.0, 10.1],
    "m_opposite": 10.1,
    "m_reduced": 9.9,
    "mu": 200,
    "tissue_correction": 1.0,
}


def _cases() -> tuple[tuple[str, dict[str, object], tuple[str, ...]], ...]:
    tg51_photon = {
        **_COMMON,
        "measured_pdd10": 73.0,
        "clinical_pdd10": 73.0,
        "energy": 6,
        "fff": False,
    }
    tg51_electron_legacy = {
        **_COMMON,
        "energy": 6,
        "k_ecal": 1.0,
        "clinical_pdd": 90.0,
        "m_gradient": 10.2,
        "cone": "10x10",
        "i_50": 6.0,
    }
    tg51_electron_modern = {
        **_COMMON,
        "energy": 6,
        "clinical_pdd": 90.0,
        "cone": "10x10",
        "i_50": 6.0,
    }
    trs398_common = {key: value for key, value in _COMMON.items() if key != "p_elec"}
    trs398_photon = {
        **trs398_common,
        "k_elec": 1.0,
        "energy": "6",
        "setup": "SAD",
        "tpr2010": 0.67,
        "fff": False,
        "clinical_tmr_zref": 0.67,
    }
    trs398_electron = {
        **trs398_common,
        "k_elec": 1.0,
        "energy": "6 MeV",
        "cone": "10x10",
        "i_50": 6.0,
        "clinical_pdd_zref": 90.0,
    }
    return (
        (
            "CALIBRATION_TG51_PHOTON",
            tg51_photon,
            ("p_tp", "p_ion", "p_pol", "m_corrected", "pddx", "kq", "dose_mu_10", "dose_mu_dmax"),
        ),
        (
            "CALIBRATION_TG51_ELECTRON_LEGACY",
            tg51_electron_legacy,
            (
                "p_tp",
                "p_ion",
                "p_pol",
                "m_corrected",
                "r_50",
                "dref",
                "pq_gr",
                "kq",
                "dose_mu_dref",
                "dose_mu_dmax",
            ),
        ),
        (
            "CALIBRATION_TG51_ELECTRON_MODERN",
            tg51_electron_modern,
            (
                "p_tp",
                "p_ion",
                "p_pol",
                "m_corrected",
                "r_50",
                "dref",
                "kq",
                "dose_mu_dref",
                "dose_mu_dmax",
            ),
        ),
        (
            "CALIBRATION_TRS398_PHOTON",
            trs398_photon,
            ("k_tp", "k_s", "k_pol", "m_corrected", "kq", "dose_mu_zref", "dose_mu_zmax"),
        ),
        (
            "CALIBRATION_TRS398_ELECTRON",
            trs398_electron,
            (
                "k_tp",
                "k_s",
                "k_pol",
                "m_corrected",
                "r_50",
                "zref",
                "kq",
                "dose_mu_zref",
                "dose_mu_zmax",
            ),
        ),
    )


@pytest.mark.parametrize("catalog_key, parameters, expected_properties", _cases())
def test_every_calibration_capability_reaches_locked_pylinac_engine(
    tmp_path: Path,
    catalog_key: str,
    parameters: dict[str, object],
    expected_properties: tuple[str, ...],
) -> None:
    result = execute_pylinac(catalog_key, tmp_path, parameters)

    assert result.catalog_key == catalog_key
    assert result.engine_version == "3.47.0"
    assert result.result_snapshot["engine"] == "pylinac"
    metrics = result.result_snapshot["metrics"]
    assert isinstance(metrics, dict)
    assert set(expected_properties).issubset(metrics)
    assert metrics["output_was_adjusted"] is False
    assert result.overlay_bytes is None


def test_calibration_missing_required_measurement_is_rejected_before_engine(
    tmp_path: Path,
) -> None:
    parameters = {
        **_COMMON,
        "energy": 6,
        "clinical_pdd10": 73.0,
        "voltage_reference": 300,
        "voltage_reduced": 150,
        "mu": 200,
        "fff": False,
    }

    with pytest.raises(PylinacAdapterError) as error:
        execute_pylinac("CALIBRATION_TG51_PHOTON", tmp_path, parameters)

    assert error.value.code == "PYLINAC_PARAMETER_INVALID"
    assert "measured_pdd10" in error.value.message
