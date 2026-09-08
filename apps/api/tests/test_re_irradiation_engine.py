from __future__ import annotations

from copy import deepcopy

import pytest

from rt_connect_api.services.re_irradiation_engine import (
    ReIrradiationEngineError,
    calculate_fraction_compensation,
    calculate_re_irradiation,
    request_fingerprint,
)


def _tissue(
    *,
    tissue_key: str = "TARGET",
    alpha_beta: float = 10.0,
    total: float | None = 60.0,
    fractions: int | float | None = 30,
    dose: float | None = 2.0,
    fraction_doses: list[float] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "tissue_key": tissue_key,
        "dose_metric": "TOTAL" if tissue_key == "TARGET" else "MEAN",
        "dose_unit": "Gy",
        "alpha_beta_gy": alpha_beta,
        "alpha_beta_source_type": "USER_DEFINED",
        "alpha_beta_source_reference": "Synthetic P15 engine fixture",
    }
    if fraction_doses is not None:
        payload["fraction_doses_gy"] = fraction_doses
    else:
        payload.update(
            {
                "total_dose_gy": total,
                "fractions": fractions,
                "dose_per_fraction_gy": dose,
            }
        )
    return payload


def _course(
    course_id: str,
    *,
    is_prior: bool,
    tissue: dict[str, object] | None = None,
    recovery: float | None = None,
) -> dict[str, object]:
    return {
        "course_id": course_id,
        "label": course_id,
        "is_prior": is_prior,
        "start_date": "2020-01-01" if is_prior else "2026-01-01",
        "end_date": "2020-02-15" if is_prior else "2026-02-15",
        "tissue_doses": [tissue or _tissue()],
        "recovery_fraction": recovery,
        "recovery_source_type": "USER_DEFINED" if recovery is not None else None,
        "recovery_source_reference": (
            "Synthetic recovery assumption" if recovery is not None else None
        ),
    }


def _reirradiation_body() -> dict[str, object]:
    return {
        "courses": [
            _course("prior", is_prior=True),
            _course(
                "current",
                is_prior=False,
                tissue=_tissue(total=50, fractions=25, dose=2),
            ),
        ],
        "recovery_model": {"mode": "NONE"},
        "sensitivity_recovery_fractions": [0.0, 0.5, 1.0],
        "spatial": {"requested": False},
    }


def _compensation_body() -> dict[str, object]:
    return {
        "planned_fraction_doses_gy": [2.0, 2.0, 3.0, 2.0],
        "delivered_fraction_doses_gy": [2.0, 2.0],
        "alpha_beta_gy": 10.0,
        "alpha_beta_source_type": "USER_DEFINED",
        "alpha_beta_source_reference": "Synthetic compensation fixture",
        "alternatives": [
            {
                "alternative_id": "baseline",
                "label": "Original remaining schedule",
                "remaining_fraction_doses_gy": [3.0, 2.0],
            },
            {
                "alternative_id": "compressed",
                "label": "Compressed remaining schedule",
                "remaining_fraction_doses_gy": [2.5, 2.5],
            },
        ],
        "interruptions": [],
        "time_model": {"mode": "NONE"},
    }


def _assert_engine_error(
    body: dict[str, object], code: str, *, compensation: bool = False
) -> None:
    function = calculate_fraction_compensation if compensation else calculate_re_irradiation
    with pytest.raises(ReIrradiationEngineError) as raised:
        function(body)
    assert raised.value.code == code
    assert raised.value.details


def test_reirradiation_known_answer_and_nonuniform_lq_are_exact_and_repeatable() -> None:
    body = _reirradiation_body()
    first = calculate_re_irradiation(body)
    second = calculate_re_irradiation(deepcopy(body))

    assert first == second
    assert first["result_sha256"] == second["result_sha256"]
    groups = first["groups"]
    assert isinstance(groups, list)
    assert len(groups) == 1
    group = groups[0]
    assert isinstance(group, dict)
    assert group["bed_no_recovery_gy"] == 132.0
    assert group["eqd2_no_recovery_gy"] == 110.0
    assert group["bed_with_recovery_gy"] == 132.0

    nonuniform = _reirradiation_body()
    courses = nonuniform["courses"]
    assert isinstance(courses, list)
    prior = courses[0]
    assert isinstance(prior, dict)
    prior["tissue_doses"] = [_tissue(total=None, fractions=None, dose=None, fraction_doses=[2, 4])]
    result = calculate_re_irradiation(nonuniform)
    rows = result["course_contributions"]
    assert isinstance(rows, list)
    prior_row = rows[0]
    assert isinstance(prior_row, dict)
    tissue_rows = prior_row["tissue_doses"]
    assert isinstance(tissue_rows, list)
    assert tissue_rows[0]["schedule"]["schedule_type"] == "NONUNIFORM"
    assert tissue_rows[0]["bed_raw_gy"] == 8.0


def test_reirradiation_recovery_is_applied_once_and_contexts_are_not_mixed() -> None:
    body = _reirradiation_body()
    body["recovery_model"] = {"mode": "USER_DEFINED", "evaluation_date": "2026-03-01"}
    courses = body["courses"]
    assert isinstance(courses, list)
    prior = courses[0]
    assert isinstance(prior, dict)
    prior["recovery_fraction"] = 0.5
    prior["recovery_source_type"] = "USER_DEFINED"
    prior["recovery_source_reference"] = "Synthetic 50% recovery"
    current = courses[1]
    assert isinstance(current, dict)
    current["tissue_doses"] = [_tissue(alpha_beta=3.0)]
    body["spatial"] = {"requested": True}

    result = calculate_re_irradiation(body)
    warnings = result["warnings"]
    assert isinstance(warnings, list)
    warning_codes = {item["code"] for item in warnings}
    assert warning_codes == {"CUMULATIVE_CONTEXT_MISMATCH", "SPATIAL_ACCUMULATION_UNAVAILABLE"}
    groups = result["groups"]
    assert isinstance(groups, list)
    assert len(groups) == 2
    by_alpha = {float(item["alpha_beta_gy"]): item for item in groups}
    assert by_alpha[10.0]["bed_with_recovery_gy"] == 36.0
    assert by_alpha[3.0]["bed_with_recovery_gy"] == pytest.approx(100.0)
    sensitivity = result["sensitivity"]
    assert isinstance(sensitivity, list)
    points = sensitivity[0]["points"]
    assert [point["bed_gy"] for point in points] == [72.0, 36.0, 0.0]
    assert result["capability"]["spatial_result"] is None


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (lambda body: body["courses"].pop(), "COURSE_COUNT_INVALID"),
        (
            lambda body: body["courses"].append(deepcopy(body["courses"][0])),
            "COURSE_ID_DUPLICATE",
        ),
        (lambda body: body["courses"][0].pop("tissue_doses"), "TISSUE_DOSE_REQUIRED"),
        (
            lambda body: body["courses"][0]["tissue_doses"][0].update({"dose_unit": "cGy"}),
            "DOSE_UNIT_INVALID",
        ),
        (
            lambda body: body["courses"][0]["tissue_doses"][0].update(
                {"alpha_beta_source_reference": ""}
            ),
            "ALPHA_BETA_SOURCE_REQUIRED",
        ),
        (
            lambda body: body["courses"][0]["tissue_doses"][0].update({"fractions": 30.5}),
            "FRACTION_COUNT_NONINTEGER",
        ),
        (
            lambda body: body["courses"][0]["tissue_doses"][0].update({"total_dose_gy": 61}),
            "FRACTION_SCHEDULE_INCONSISTENT",
        ),
        (
            lambda body: body["courses"][0].update({"end_date": "2019-01-01"}),
            "COURSE_INTERVAL_INVALID",
        ),
        (
            lambda body: body.update({"sensitivity_recovery_fractions": [1.1]}),
            "RECOVERY_ASSUMPTION_INVALID",
        ),
        (
            lambda body: body["courses"][1].update({"is_prior": True}),
            "COURSE_ROLE_REQUIRED",
        ),
        (
            lambda body: body["courses"][0].update({"is_prior": False}),
            "COURSE_ROLE_REQUIRED",
        ),
    ],
)
def test_reirradiation_rejects_invalid_course_schedule_and_context_inputs(
    mutator, code: str
) -> None:
    body = _reirradiation_body()
    mutator(body)
    _assert_engine_error(body, code)


def test_compensation_preserves_delivered_prefix_and_applies_optional_time_model() -> None:
    body = _compensation_body()
    body["interruptions"] = [{"start_date": "2026-01-10", "end_date": "2026-01-12"}]
    body["time_model"] = {
        "mode": "USER_DEFINED_LINEAR",
        "treatment_start_date": "2026-01-01",
        "evaluation_date": "2026-01-11",
        "kickoff_days": 1,
        "repopulation_rate_bed_gy_per_day": 0.5,
        "source_reference": "Synthetic linear repopulation fixture",
    }
    result = calculate_fraction_compensation(body)
    alternatives = result["alternatives"]
    assert isinstance(alternatives, list)
    assert all(item["delivered_prefix_unchanged"] is True for item in alternatives)
    assert result["time_model"]["repopulation_penalty_bed_gy"] == 4.5
    assert result["interruptions"][0]["start_date"] == "2026-01-10"
    assert result["planned_schedule"]["total_dose_gy"] == 9.0
    assert result["delivered_prefix"]["total_dose_gy"] == 4.0

    # A fingerprint is an identity, not a display hash; key ordering must not change it.
    assert request_fingerprint({"a": 1, "b": [2, 3]}) == request_fingerprint({"b": [2, 3], "a": 1})


@pytest.mark.parametrize(
    ("mutator", "code"),
    [
        (
            lambda body: body.update({"planned_fraction_doses_gy": []}),
            "FRACTION_SCHEDULE_REQUIRED",
        ),
        (
            lambda body: body.update({"delivered_fraction_doses_gy": [2, 2, 2, 2, 2]}),
            "FRACTION_SCHEDULE_INVALID",
        ),
        (
            lambda body: body.update({"delivered_fraction_doses_gy": [1]}),
            "FRACTION_SCHEDULE_INVALID",
        ),
        (lambda body: body.update({"alternatives": []}), "ALTERNATIVE_SCHEDULE_REQUIRED"),
        (
            lambda body: body["alternatives"].append(deepcopy(body["alternatives"][0])),
            "ALTERNATIVE_ID_DUPLICATE",
        ),
        (
            lambda body: body.update(
                {
                    "interruptions": [
                        {"start_date": "2026-01-01", "end_date": "2026-01-04"},
                        {"start_date": "2026-01-03", "end_date": "2026-01-05"},
                    ]
                }
            ),
            "INTERRUPTION_OVERLAP",
        ),
        (
            lambda body: body.update({"time_model": {"mode": "USER_DEFINED_LINEAR"}}),
            "TIME_MODEL_SOURCE_REQUIRED",
        ),
        (
            lambda body: body.update({"time_model": {"mode": "UNKNOWN"}}),
            "TIME_MODEL_INVALID",
        ),
    ],
)
def test_compensation_rejects_invalid_prefix_alternatives_and_time_inputs(
    mutator, code: str
) -> None:
    body = _compensation_body()
    mutator(body)
    _assert_engine_error(body, code, compensation=True)
