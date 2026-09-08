from math import isclose

import pytest

from rt_connect_api.services.bed_eqd2_engine import (
    BedEqd2EngineError,
    CurveSpec,
    calculate_bed_eqd2,
    normalize_fractionation,
)


def _result(*, total: float, fractions: int, dose: float, alpha: float = 10.0) -> dict[str, object]:
    return calculate_bed_eqd2(
        fractionation=normalize_fractionation(
            total_dose_gy=total,
            fractions=fractions,
            dose_per_fraction_gy=dose,
        ),
        alpha_beta_gy=alpha,
        alpha_beta_source_type="USER_DEFINED",
        alpha_beta_source_reference="Synthetic known-answer fixture",
        curve=CurveSpec(
            mode="FIXED_N",
            dose_min_gy=0,
            dose_max_gy=10,
            dose_step_gy=1,
            alpha_beta_values_gy=(alpha,),
            point_limit=100,
        ),
    )


def test_known_answer_60_gy_30_fractions_alpha_beta_10() -> None:
    result = _result(total=60, fractions=30, dose=2)
    primary = result["primary"]
    assert isinstance(primary, dict)
    assert isclose(float(primary["bed_gy"]), 72.0)
    assert isclose(float(primary["eqd2_gy"]), 60.0)


def test_known_answer_30_gy_5_fractions_alpha_beta_3_without_early_rounding() -> None:
    result = _result(total=30, fractions=5, dose=6, alpha=3)
    primary = result["primary"]
    assert isinstance(primary, dict)
    assert isclose(float(primary["bed_gy"]), 90.0)
    assert isclose(float(primary["eqd2_gy"]), 54.0)


def test_pair_inputs_derive_the_missing_value_and_zero_dose_is_valid() -> None:
    normalized = normalize_fractionation(total_dose_gy=60, fractions=30, dose_per_fraction_gy=None)
    assert normalized.dose_per_fraction_gy == 2
    zero = normalize_fractionation(total_dose_gy=0, fractions=10, dose_per_fraction_gy=0)
    assert zero.total_dose_gy == 0
    assert zero.dose_per_fraction_gy == 0
    result = _result(total=0, fractions=10, dose=0)
    primary = result["primary"]
    assert isinstance(primary, dict)
    assert primary["bed_gy"] == 0
    assert primary["eqd2_gy"] == 0


def test_mismatch_and_invalid_source_are_rejected_without_clamping() -> None:
    with pytest.raises(BedEqd2EngineError, match="not consistent") as mismatch:
        normalize_fractionation(total_dose_gy=60, fractions=30, dose_per_fraction_gy=3)
    assert mismatch.value.code == "FRACTIONATION_INCONSISTENT"
    with pytest.raises(BedEqd2EngineError) as missing_source:
        calculate_bed_eqd2(
            fractionation=normalize_fractionation(
                total_dose_gy=60, fractions=30, dose_per_fraction_gy=2
            ),
            alpha_beta_gy=10,
            alpha_beta_source_type="USER_DEFINED",
            alpha_beta_source_reference="",
            curve=CurveSpec(),
        )
    assert missing_source.value.code == "ALPHA_BETA_SOURCE_REQUIRED"


def test_fixed_n_curve_and_marker_use_the_same_unrounded_points() -> None:
    result = _result(total=60, fractions=30, dose=2)
    dataset = result["chart_dataset"]
    assert isinstance(dataset, dict)
    assert dataset["point_count"] == 11
    series = dataset["series"]
    assert isinstance(series, list)
    points = series[0]["points"]
    assert isinstance(points, list)
    assert points[0]["total_dose_gy"] == 0
    assert points[-1]["total_dose_gy"] == 10
    assert all(point["fractions"] == 30 for point in points)
    assert result["table_rows"] == points


def test_fixed_d_curve_requires_integer_fraction_points_and_respects_budget() -> None:
    result = calculate_bed_eqd2(
        fractionation=normalize_fractionation(
            total_dose_gy=60, fractions=30, dose_per_fraction_gy=2
        ),
        alpha_beta_gy=10,
        alpha_beta_source_type="USER_DEFINED",
        alpha_beta_source_reference="Synthetic known-answer fixture",
        curve=CurveSpec(
            mode="FIXED_D",
            dose_min_gy=0,
            dose_max_gy=10,
            dose_step_gy=2,
            alpha_beta_values_gy=(10,),
            point_limit=10,
        ),
    )
    dataset = result["chart_dataset"]
    assert isinstance(dataset, dict)
    assert dataset["point_count"] == 5
    with pytest.raises(BedEqd2EngineError) as bad_step:
        calculate_bed_eqd2(
            fractionation=normalize_fractionation(
                total_dose_gy=60, fractions=30, dose_per_fraction_gy=2
            ),
            alpha_beta_gy=10,
            alpha_beta_source_type="USER_DEFINED",
            alpha_beta_source_reference="Synthetic known-answer fixture",
            curve=CurveSpec(mode="FIXED_D", dose_min_gy=0, dose_max_gy=10, dose_step_gy=1),
        )
    assert bad_step.value.code == "CURVE_RANGE_INVALID"
