from __future__ import annotations

import math

import pytest

from rt_connect_api.services.plan_comparison_engine import (
    ComparisonOption,
    PlanComparisonEngineError,
    calculate_plan_comparison,
)


def _option(
    option_id: str,
    *,
    label: str | None = None,
    dose: float = 60.0,
    fractions: int = 30,
    dose_per_fraction: float = 2.0,
    alpha_beta: float = 10.0,
    scenario_id: str = "scenario-1",
    revision_id: str = "revision-1",
    model_version: str = "p13-lq-1.0.0",
    tissue_context: str = "Lung; synthetic context",
) -> ComparisonOption:
    return ComparisonOption(
        option_id=option_id,
        label=label or option_id,
        calculation_id=f"calculation-{option_id}",
        scenario_id=scenario_id,
        scenario_revision_id=revision_id,
        model_key="biological.bed-eqd2",
        model_version=model_version,
        tissue_context=tissue_context,
        total_dose_gy=dose,
        fractions=fractions,
        dose_per_fraction_gy=dose_per_fraction,
        alpha_beta_gy=alpha_beta,
        alpha_beta_source_type="USER_DEFINED",
        alpha_beta_source_reference="Synthetic fixture",
        bed_gy=dose * 1.2,
        eqd2_gy=dose,
    )


def test_same_options_are_zero_delta_and_order_is_preserved() -> None:
    result = calculate_plan_comparison(
        options=[_option("A"), _option("B")],
        baseline_option_id="A",
    )

    rows = result["table_rows"]
    assert isinstance(rows, list)
    assert [row["option_id"] for row in rows] == ["A", "B"]
    assert all(row["delta_bed_gy"] == 0 for row in rows)
    assert all(row["delta_eqd2_gy"] == 0 for row in rows)
    chart = result["chart_dataset"]
    assert isinstance(chart, dict)
    assert chart["point_count"] == 2
    assert result["ranking"] is None


def test_baseline_change_recomputes_signed_absolute_and_percent_deltas() -> None:
    result = calculate_plan_comparison(
        options=[_option("A", dose=60), _option("B", dose=70)],
        baseline_option_id="B",
    )

    rows = result["table_rows"]
    assert isinstance(rows, list)
    baseline, alternative = rows
    assert baseline["is_baseline"] is False
    assert alternative["is_baseline"] is True
    assert math.isclose(float(baseline["delta_eqd2_gy"]), -10.0)
    assert math.isclose(float(baseline["delta_eqd2_percent"]), -100.0 / 7.0)
    assert alternative["delta_eqd2_gy"] == 0
    assert alternative["delta_eqd2_percent"] == 0


def test_three_options_are_compared_independently_without_summing_courses() -> None:
    result = calculate_plan_comparison(
        options=[_option("A", dose=60), _option("B", dose=70), _option("C", dose=80)],
        baseline_option_id="A",
    )

    rows = result["table_rows"]
    assert isinstance(rows, list)
    assert [row["eqd2_gy"] for row in rows] == [60.0, 70.0, 80.0]
    assert all("total_option_dose" not in row for row in rows)
    assert result["compatibility"]["alpha_beta_comparable"] is True  # type: ignore[index]


def test_zero_baseline_keeps_absolute_delta_and_marks_percent_undefined() -> None:
    result = calculate_plan_comparison(
        options=[_option("A", dose=0, fractions=1, dose_per_fraction=0), _option("B", dose=60)],
        baseline_option_id="A",
    )

    rows = result["table_rows"]
    assert isinstance(rows, list)
    zero, nonzero = rows
    assert zero["delta_bed_gy"] == 0
    assert nonzero["delta_bed_gy"] == 72.0
    assert nonzero["delta_bed_percent"] is None
    assert nonzero["delta_bed_percent_reason"] == "BASELINE_ZERO"
    assert nonzero["delta_eqd2_percent"] is None
    assert nonzero["delta_eqd2_percent_reason"] == "BASELINE_ZERO"
    assert all(value not in (float("inf"), float("-inf")) for row in rows for value in row.values())


def test_alpha_beta_mismatch_is_a_warning_and_disables_automatic_ranking() -> None:
    result = calculate_plan_comparison(
        options=[_option("A", alpha_beta=10), _option("B", alpha_beta=3)],
        baseline_option_id="A",
    )

    warnings = result["warnings"]
    assert isinstance(warnings, list)
    assert warnings[0]["code"] == "COMPARISON_ALPHA_BETA_MISMATCH"
    assert result["compatibility"]["alpha_beta_comparable"] is False  # type: ignore[index]
    assert result["compatibility"]["ranking_allowed"] is False  # type: ignore[index]
    assert result["ranking"] is None


@pytest.mark.parametrize(
    ("options", "baseline", "code"),
    [
        ([_option("A")], "A", "COMPARISON_OPTIONS_REQUIRED"),
        ([_option("A"), _option("B"), _option("C")], "missing", "COMPARISON_BASELINE_REQUIRED"),
        ([_option("A"), _option("A")], "A", "COMPARISON_OPTION_INVALID"),
        (
            [_option("A"), _option("B", scenario_id="scenario-2")],
            "A",
            "COMPARISON_CONTEXT_MISMATCH",
        ),
    ],
)
def test_invalid_comparison_contracts_are_explicit(
    options: list[ComparisonOption], baseline: str, code: str
) -> None:
    with pytest.raises(PlanComparisonEngineError) as raised:
        calculate_plan_comparison(options=options, baseline_option_id=baseline)
    assert raised.value.code == code


def test_option_numeric_values_must_be_finite_and_nonnegative() -> None:
    with pytest.raises(PlanComparisonEngineError) as raised:
        calculate_plan_comparison(
            options=[_option("A", dose=math.nan), _option("B")],
            baseline_option_id="A",
        )
    assert raised.value.code == "COMPARISON_OPTION_INVALID"


def test_comparison_option_limit_is_explicit_and_never_truncates() -> None:
    with pytest.raises(PlanComparisonEngineError) as raised:
        calculate_plan_comparison(
            options=[_option(str(index)) for index in range(11)],
            baseline_option_id="0",
        )
    assert raised.value.code == "COMPARISON_LIMIT_EXCEEDED"
