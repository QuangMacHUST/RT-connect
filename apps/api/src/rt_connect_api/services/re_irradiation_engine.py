"""Deterministic P15 re-irradiation and fraction-compensation calculations.

The P15 engine is deliberately independent from HTTP, SQLAlchemy, Supabase,
and QA/patient records.  It accepts explicit course/tissue/schedule snapshots
and returns a JSON-serialisable estimate with the assumptions that were used.
The API layer is responsible for organization scope and immutable persistence.

This module is a scalar LQ/BED/EQD2 scenario calculator.  It never fabricates
voxel dose, dose registration, dose accumulation, prescription, or an
automatic clinical recommendation.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

REIRRADIATION_ENGINE_KEY = "biological.re-irradiation"
REIRRADIATION_ENGINE_VERSION = "p15-lq-reirradiation-1.0.0"
FRACTION_COMPENSATION_ENGINE_KEY = "biological.fraction-compensation"
FRACTION_COMPENSATION_ENGINE_VERSION = "p15-lq-compensation-1.0.0"

MAX_COURSES = 20
MAX_TISSUE_DOSES_PER_COURSE = 40
MAX_FRACTIONS = 10_000
MAX_ALTERNATIVES = 20
MAX_SENSITIVITY_POINTS = 21


class ReIrradiationEngineError(ValueError):
    """A stable, field-addressable P15 numerical validation failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        details: list[dict[str, object]] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.field = field
        self.details = details or ([] if field is None else [{"field": field, "message": message}])
        super().__init__(message)


@dataclass(frozen=True)
class NormalizedSchedule:
    doses_gy: tuple[float, ...]
    total_dose_gy: float
    fraction_count: int
    schedule_type: Literal["UNIFORM", "NONUNIFORM"]

    @property
    def dose_per_fraction_gy(self) -> float | None:
        if self.schedule_type == "UNIFORM":
            return self.doses_gy[0]
        return None

    def as_dict(self) -> dict[str, object]:
        return {
            "fraction_doses_gy": list(self.doses_gy),
            "total_dose_gy": self.total_dose_gy,
            "fractions": self.fraction_count,
            "dose_per_fraction_gy": self.dose_per_fraction_gy,
            "schedule_type": self.schedule_type,
        }


@dataclass(frozen=True)
class TissueSchedule:
    tissue_key: str
    dose_metric: str
    dose_unit: str
    alpha_beta_gy: float
    alpha_beta_source_type: str
    alpha_beta_source_reference: str
    schedule: NormalizedSchedule


@dataclass(frozen=True)
class CourseInput:
    course_id: str
    label: str
    start_date: date | None
    end_date: date | None
    is_prior: bool
    recovery_fraction: float
    recovery_source_type: str | None
    recovery_source_reference: str | None
    tissues: tuple[TissueSchedule, ...]


def _fail(
    code: str,
    message: str,
    *,
    field: str | None = None,
    details: list[dict[str, object]] | None = None,
) -> ReIrradiationEngineError:
    return ReIrradiationEngineError(code, message, field=field, details=details)


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise _fail("REIRRADIATION_INPUT_INVALID", "An object is required.", field=field)
    return value


def _text(value: object, field: str, *, max_length: int = 240) -> str:
    if not isinstance(value, str):
        raise _fail(
            "REIRRADIATION_INPUT_INVALID", "A non-empty text value is required.", field=field
        )
    result = value.strip()
    if not result or len(result) > max_length:
        raise _fail(
            "REIRRADIATION_INPUT_INVALID",
            "Text must be non-empty and within the allowed length.",
            field=field,
        )
    return result


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _fail(
            "REIRRADIATION_INPUT_INVALID", "A finite numeric value is required.", field=field
        )
    number = float(value)
    if not math.isfinite(number):
        raise _fail("CALCULATION_NONFINITE", "NaN and Infinity are not accepted.", field=field)
    return number


def _nonnegative(value: object, field: str) -> float:
    number = _finite(value, field)
    if number < 0:
        raise _fail("REIRRADIATION_INPUT_INVALID", "The value cannot be negative.", field=field)
    return number


def _positive(value: object, field: str) -> float:
    number = _finite(value, field)
    if number <= 0:
        raise _fail(
            "REIRRADIATION_INPUT_INVALID", "The value must be greater than zero.", field=field
        )
    return number


def _integer(value: object, field: str, *, minimum: int = 0, maximum: int = MAX_FRACTIONS) -> int:
    number = _finite(value, field)
    if not number.is_integer():
        raise _fail(
            "FRACTION_COUNT_NONINTEGER", "The fraction count must be an integer.", field=field
        )
    result = int(number)
    if result < minimum or result > maximum:
        raise _fail(
            "FRACTION_SCHEDULE_INVALID",
            f"The fraction count must be between {minimum} and {maximum}.",
            field=field,
        )
    return result


def _date_value(value: object, field: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise _fail(
            "COURSE_INTERVAL_REQUIRED", "An ISO date is required for this time model.", field=field
        )
    raw = value.strip().replace("Z", "+00:00")
    try:
        if "T" in raw:
            return datetime.fromisoformat(raw).date()
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise _fail(
            "COURSE_INTERVAL_INVALID", "The date must be ISO-8601 formatted.", field=field
        ) from exc


def _optional_date(value: object, field: str) -> date | None:
    if value is None:
        return None
    return _date_value(value, field)


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _array(value: object, field: str, *, max_length: int) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise _fail(
            "FRACTION_SCHEDULE_INVALID", "An array of fraction doses is required.", field=field
        )
    if len(value) > max_length:
        raise _fail("FRACTION_SCHEDULE_INVALID", "The supplied schedule is too long.", field=field)
    return value


def _schedule(raw: Mapping[str, object], field_prefix: str) -> NormalizedSchedule:
    raw_doses = raw.get("fraction_doses_gy")
    supplied_total = raw.get("total_dose_gy")
    supplied_count = raw.get("fractions")
    supplied_dose = raw.get("dose_per_fraction_gy")
    tolerance = _positive(
        raw.get("consistency_tolerance_gy", 0.01), f"{field_prefix}.consistency_tolerance_gy"
    )

    if raw_doses is not None:
        values = tuple(
            _nonnegative(item, f"{field_prefix}.fraction_doses_gy[{index}]")
            for index, item in enumerate(
                _array(raw_doses, f"{field_prefix}.fraction_doses_gy", max_length=MAX_FRACTIONS)
            )
        )
        if not values:
            raise _fail(
                "FRACTION_SCHEDULE_INVALID",
                "At least one fraction dose is required.",
                field=f"{field_prefix}.fraction_doses_gy",
            )
        total_from_list = sum(values)
        if (
            supplied_total is not None
            and abs(total_from_list - _nonnegative(supplied_total, f"{field_prefix}.total_dose_gy"))
            > tolerance
        ):
            raise _fail(
                "FRACTION_SCHEDULE_INCONSISTENT",
                "The fraction list does not match total dose.",
                field=f"{field_prefix}.total_dose_gy",
            )
        if supplied_count is not None and _integer(
            supplied_count, f"{field_prefix}.fractions", minimum=1
        ) != len(values):
            raise _fail(
                "FRACTION_SCHEDULE_INCONSISTENT",
                "The fraction list does not match the fraction count.",
                field=f"{field_prefix}.fractions",
            )
        if supplied_dose is not None:
            dose_from_list = _nonnegative(supplied_dose, f"{field_prefix}.dose_per_fraction_gy")
            if any(abs(item - dose_from_list) > tolerance for item in values):
                raise _fail(
                    "FRACTION_SCHEDULE_INCONSISTENT",
                    "A non-uniform fraction list cannot be labelled with a different uniform dose.",
                    field=f"{field_prefix}.dose_per_fraction_gy",
                )
        uniform = all(abs(item - values[0]) <= 1e-12 for item in values)
        return NormalizedSchedule(
            values, total_from_list, len(values), "UNIFORM" if uniform else "NONUNIFORM"
        )

    present = sum(item is not None for item in (supplied_total, supplied_count, supplied_dose))
    if present < 2:
        raise _fail(
            "FRACTION_SCHEDULE_REQUIRED",
            (
                "Provide fraction_doses_gy or at least two of total_dose_gy, "
                "fractions, and dose_per_fraction_gy."
            ),
            field=field_prefix,
        )
    total: float | None = (
        None
        if supplied_total is None
        else _nonnegative(supplied_total, f"{field_prefix}.total_dose_gy")
    )
    count: int | None = (
        None
        if supplied_count is None
        else _integer(supplied_count, f"{field_prefix}.fractions", minimum=1)
    )
    dose: float | None = (
        None
        if supplied_dose is None
        else _nonnegative(supplied_dose, f"{field_prefix}.dose_per_fraction_gy")
    )
    if total is not None and count is not None and dose is not None:
        expected = count * dose
        if abs(total - expected) > tolerance:
            raise _fail(
                "FRACTION_SCHEDULE_INCONSISTENT",
                "D must equal n × d within the selected tolerance.",
                field=f"{field_prefix}.total_dose_gy",
            )
    if total is not None and count is not None:
        assert count is not None
        effective_dose = total / count
    elif total is not None and dose is not None:
        assert dose is not None
        raw_count = total / dose if dose != 0 else float("nan")
        if not math.isfinite(raw_count) or not raw_count.is_integer():
            raise _fail(
                "FRACTION_COUNT_NONINTEGER",
                "Total dose divided by dose per fraction must produce an integer count.",
                field=f"{field_prefix}.fractions",
            )
        count = int(raw_count)
        if count < 1 or count > MAX_FRACTIONS:
            raise _fail(
                "FRACTION_SCHEDULE_INVALID",
                "The derived fraction count is outside the allowed range.",
                field=f"{field_prefix}.fractions",
            )
        effective_dose = dose
    else:
        assert count is not None and dose is not None
        effective_dose = dose
        total = count * dose
    assert total is not None and count is not None
    values = tuple(effective_dose for _ in range(count))
    return NormalizedSchedule(values, total, count, "UNIFORM")


def _alpha_beta(raw: Mapping[str, object], field_prefix: str) -> tuple[float, str, str]:
    def field(name: str) -> str:
        return f"{field_prefix}.{name}" if field_prefix else name

    value = _positive(raw.get("alpha_beta_gy"), field("alpha_beta_gy"))
    source_type = str(raw.get("alpha_beta_source_type", "")).strip()
    if source_type not in {"USER_DEFINED", "REFERENCE"}:
        raise _fail(
            "ALPHA_BETA_SOURCE_REQUIRED",
            "Alpha/beta source type must be USER_DEFINED or REFERENCE.",
            field=field("alpha_beta_source_type"),
        )
    reference = raw.get("alpha_beta_source_reference")
    if not isinstance(reference, str) or not reference.strip():
        raise _fail(
            "ALPHA_BETA_SOURCE_REQUIRED",
            "An alpha/beta source or user-defined note is required.",
            field=field("alpha_beta_source_reference"),
        )
    return value, source_type, reference.strip()


def _bed(doses: Sequence[float], alpha_beta_gy: float) -> float:
    value = sum(dose * (1.0 + dose / alpha_beta_gy) for dose in doses)
    if not math.isfinite(value):
        raise _fail("CALCULATION_NONFINITE", "The BED result is not finite.", field="calculation")
    return value


def _eqd2(bed: float, alpha_beta_gy: float) -> float:
    value = bed / (1.0 + 2.0 / alpha_beta_gy)
    if not math.isfinite(value):
        raise _fail("CALCULATION_NONFINITE", "The EQD2 result is not finite.", field="calculation")
    return value


def _parse_courses(request: Mapping[str, object]) -> tuple[CourseInput, ...]:
    """Parse courses in a second small wrapper so error paths stay explicit."""
    raw_courses = request.get("courses")
    if (
        not isinstance(raw_courses, Sequence)
        or isinstance(raw_courses, (str, bytes, bytearray))
        or not raw_courses
    ):
        raise _fail(
            "COURSE_REQUIRED", "At least one treatment course is required.", field="courses"
        )
    if len(raw_courses) < 2:
        raise _fail(
            "COURSE_COUNT_INVALID",
            "Re-irradiation requires at least a prior and a current course.",
            field="courses",
        )
    recovery_raw = _mapping(request.get("recovery_model", {}), "recovery_model")
    recovery_mode = str(recovery_raw.get("mode", "NONE")).strip().upper()
    if recovery_mode not in {"NONE", "USER_DEFINED"}:
        raise _fail(
            "RECOVERY_ASSUMPTION_INVALID",
            "Recovery mode must be NONE or USER_DEFINED.",
            field="recovery_model.mode",
        )
    if recovery_mode == "USER_DEFINED":
        _date_value(recovery_raw.get("evaluation_date"), "recovery_model.evaluation_date")
    seen: set[str] = set()
    result: list[CourseInput] = []
    for index, raw in enumerate(raw_courses):
        prefix = f"courses[{index}]"
        course = _mapping(raw, prefix)
        course_id = _text(course.get("course_id"), f"{prefix}.course_id", max_length=80)
        if course_id in seen:
            raise _fail(
                "COURSE_ID_DUPLICATE",
                "Course identifiers must be unique.",
                field=f"{prefix}.course_id",
            )
        seen.add(course_id)
        label = _text(course.get("label", course_id), f"{prefix}.label", max_length=240)
        start = _optional_date(course.get("start_date"), f"{prefix}.start_date")
        end = _optional_date(course.get("end_date"), f"{prefix}.end_date")
        if start is not None and end is not None and end < start:
            raise _fail(
                "COURSE_INTERVAL_INVALID",
                "Course end date cannot precede its start date.",
                field=f"{prefix}.end_date",
            )
        is_prior = course.get("is_prior", index < len(raw_courses) - 1)
        if not isinstance(is_prior, bool):
            raise _fail(
                "REIRRADIATION_INPUT_INVALID",
                "is_prior must be boolean.",
                field=f"{prefix}.is_prior",
            )
        raw_tissues = course.get("tissue_doses")
        if (
            not isinstance(raw_tissues, Sequence)
            or isinstance(raw_tissues, (str, bytes, bytearray))
            or not raw_tissues
        ):
            raise _fail(
                "TISSUE_DOSE_REQUIRED",
                (
                    "Each course needs explicit tissue/OAR dose rows; do not copy "
                    "target prescription to every OAR."
                ),
                field=f"{prefix}.tissue_doses",
            )
        if len(raw_tissues) > MAX_TISSUE_DOSES_PER_COURSE:
            raise _fail(
                "TISSUE_DOSE_LIMIT_EXCEEDED",
                "Too many tissue dose rows were supplied.",
                field=f"{prefix}.tissue_doses",
            )
        tissue_result: list[TissueSchedule] = []
        tissue_seen: set[str] = set()
        for tissue_index, raw_tissue in enumerate(raw_tissues):
            tissue_prefix = f"{prefix}.tissue_doses[{tissue_index}]"
            tissue = _mapping(raw_tissue, tissue_prefix)
            tissue_key = _text(
                tissue.get("tissue_key"), f"{tissue_prefix}.tissue_key", max_length=120
            )
            if tissue_key in tissue_seen:
                raise _fail(
                    "TISSUE_DOSE_DUPLICATE",
                    "A course cannot contain duplicate tissue keys.",
                    field=f"{tissue_prefix}.tissue_key",
                )
            tissue_seen.add(tissue_key)
            metric = _text(tissue.get("dose_metric"), f"{tissue_prefix}.dose_metric", max_length=80)
            unit = _text(tissue.get("dose_unit", ""), f"{tissue_prefix}.dose_unit", max_length=20)
            if unit.lower() != "gy":
                raise _fail(
                    "DOSE_UNIT_INVALID",
                    "P15 scalar calculations require explicit Gy units.",
                    field=f"{tissue_prefix}.dose_unit",
                )
            alpha_beta, source_type, source_reference = _alpha_beta(tissue, tissue_prefix)
            tissue_result.append(
                TissueSchedule(
                    tissue_key,
                    metric,
                    "Gy",
                    alpha_beta,
                    source_type,
                    source_reference,
                    _schedule(tissue, tissue_prefix),
                )
            )
        raw_recovery = course.get("recovery_fraction")
        if recovery_mode == "NONE":
            recovery_fraction = 0.0
            if (
                raw_recovery is not None
                and _nonnegative(raw_recovery, f"{prefix}.recovery_fraction") > 0
            ):
                raise _fail(
                    "RECOVERY_ASSUMPTION_INVALID",
                    "Non-zero recovery requires USER_DEFINED recovery mode.",
                    field=f"{prefix}.recovery_fraction",
                )
            recovery_type = None
            recovery_reference = None
        else:
            if is_prior and raw_recovery is None:
                raise _fail(
                    "RECOVERY_ASSUMPTION_INVALID",
                    "Every prior course requires an explicit recovery fraction.",
                    field=f"{prefix}.recovery_fraction",
                )
            recovery_fraction = (
                0.0
                if raw_recovery is None
                else _nonnegative(raw_recovery, f"{prefix}.recovery_fraction")
            )
            if recovery_fraction > 1.0:
                raise _fail(
                    "RECOVERY_ASSUMPTION_INVALID",
                    "Recovery fraction must be between 0 and 1.",
                    field=f"{prefix}.recovery_fraction",
                )
            if not is_prior and recovery_fraction > 0:
                raise _fail(
                    "RECOVERY_ASSUMPTION_INVALID",
                    "Recovery is applied only to prior courses.",
                    field=f"{prefix}.recovery_fraction",
                )
            recovery_type_raw = course.get("recovery_source_type")
            recovery_reference_raw = course.get("recovery_source_reference")
            if is_prior:
                recovery_type = str(recovery_type_raw or "").strip().upper()
                if (
                    recovery_type not in {"USER_DEFINED", "REFERENCE"}
                    or not isinstance(recovery_reference_raw, str)
                    or not recovery_reference_raw.strip()
                ):
                    raise _fail(
                        "RECOVERY_ASSUMPTION_INVALID",
                        "Recovery requires source type and source reference.",
                        field=f"{prefix}.recovery_source_reference",
                    )
                recovery_reference = recovery_reference_raw.strip()
            else:
                recovery_type = None
                recovery_reference = None
        result.append(
            CourseInput(
                course_id,
                label,
                start,
                end,
                is_prior,
                recovery_fraction,
                recovery_type,
                recovery_reference,
                tuple(tissue_result),
            )
        )
    if len(result) > MAX_COURSES:
        raise _fail(
            "COURSE_LIMIT_EXCEEDED",
            f"At most {MAX_COURSES} courses are supported.",
            field="courses",
        )
    if not any(course.is_prior for course in result) or all(course.is_prior for course in result):
        raise _fail(
            "COURSE_ROLE_REQUIRED",
            "At least one prior course and one current course are required.",
            field="courses",
        )
    return tuple(result)


def _spatial_capability(
    request: Mapping[str, object],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    raw = request.get("spatial", {})
    spatial = _mapping(raw, "spatial")
    requested = spatial.get("requested", False)
    if not isinstance(requested, bool):
        raise _fail(
            "REIRRADIATION_INPUT_INVALID",
            "spatial.requested must be boolean.",
            field="spatial.requested",
        )
    warning: list[dict[str, object]] = []
    if requested:
        warning.append(
            {
                "code": "SPATIAL_ACCUMULATION_UNAVAILABLE",
                "field": "spatial",
                "message": (
                    "P15 currently returns scalar scenario estimates only; no voxel "
                    "dose or registration was calculated."
                ),
            }
        )
    return {
        "scalar_cumulative": True,
        "spatial_accumulation": "UNAVAILABLE",
        "spatial_requested": requested,
        "spatial_result": None,
        "spatial_unavailable_code": "SPATIAL_ACCUMULATION_UNAVAILABLE",
    }, warning


def _group_key(tissue_key: str, alpha_beta_gy: float) -> str:
    return f"{tissue_key}|alpha-beta={alpha_beta_gy:g} Gy"


def calculate_re_irradiation(request: Mapping[str, object]) -> dict[str, object]:
    """Calculate per-course and cumulative scalar BED/EQD2 contributions."""

    courses = _parse_courses(request)
    recovery_raw = _mapping(request.get("recovery_model", {}), "recovery_model")
    recovery_mode = str(recovery_raw.get("mode", "NONE")).strip().upper()
    evaluation_date = (
        None
        if recovery_mode == "NONE"
        else _date_value(recovery_raw.get("evaluation_date"), "recovery_model.evaluation_date")
    )
    capability, warnings = _spatial_capability(request)

    groups: dict[str, dict[str, object]] = {}
    course_rows: list[dict[str, object]] = []
    contexts_by_tissue: defaultdict[str, set[float]] = defaultdict(set)
    for course in courses:
        tissue_rows: list[dict[str, object]] = []
        for tissue in course.tissues:
            contexts_by_tissue[tissue.tissue_key].add(tissue.alpha_beta_gy)
            raw_bed = _bed(tissue.schedule.doses_gy, tissue.alpha_beta_gy)
            applied_recovery = course.recovery_fraction if course.is_prior else 0.0
            contribution = raw_bed * (1.0 - applied_recovery)
            row = {
                "course_id": course.course_id,
                "course_label": course.label,
                "is_prior": course.is_prior,
                "tissue_key": tissue.tissue_key,
                "dose_metric": tissue.dose_metric,
                "dose_unit": tissue.dose_unit,
                "alpha_beta_gy": tissue.alpha_beta_gy,
                "alpha_beta_source_type": tissue.alpha_beta_source_type,
                "alpha_beta_source_reference": tissue.alpha_beta_source_reference,
                "schedule": tissue.schedule.as_dict(),
                "bed_raw_gy": raw_bed,
                "recovery_fraction_applied": applied_recovery,
                "bed_contribution_gy": contribution,
                "eqd2_contribution_gy": _eqd2(contribution, tissue.alpha_beta_gy),
            }
            tissue_rows.append(row)
            key = _group_key(tissue.tissue_key, tissue.alpha_beta_gy)
            group = groups.setdefault(
                key,
                {
                    "group_key": key,
                    "tissue_key": tissue.tissue_key,
                    "alpha_beta_gy": tissue.alpha_beta_gy,
                    "alpha_beta_source_type": tissue.alpha_beta_source_type,
                    "alpha_beta_source_reference": tissue.alpha_beta_source_reference,
                    "course_ids": [],
                    "course_contributions": [],
                    "total_dose_gy": 0.0,
                    "bed_no_recovery_gy": 0.0,
                    "bed_with_recovery_gy": 0.0,
                },
            )
            course_ids = group["course_ids"]
            contributions = group["course_contributions"]
            if isinstance(course_ids, list) and course.course_id not in course_ids:
                course_ids.append(course.course_id)
            if isinstance(contributions, list):
                contributions.append(row)
            group["total_dose_gy"] = (
                _finite(group["total_dose_gy"], f"groups[{key}].total_dose_gy")
                + tissue.schedule.total_dose_gy
            )
            group["bed_no_recovery_gy"] = (
                _finite(group["bed_no_recovery_gy"], f"groups[{key}].bed_no_recovery_gy") + raw_bed
            )
            group["bed_with_recovery_gy"] = (
                _finite(group["bed_with_recovery_gy"], f"groups[{key}].bed_with_recovery_gy")
                + contribution
            )
        course_rows.append(
            {
                "course_id": course.course_id,
                "label": course.label,
                "is_prior": course.is_prior,
                "start_date": course.start_date.isoformat() if course.start_date else None,
                "end_date": course.end_date.isoformat() if course.end_date else None,
                "recovery_fraction": course.recovery_fraction,
                "recovery_source_type": course.recovery_source_type,
                "recovery_source_reference": course.recovery_source_reference,
                "tissue_doses": tissue_rows,
            }
        )

    for tissue_key, alpha_values in contexts_by_tissue.items():
        if len(alpha_values) > 1:
            warnings.append(
                {
                    "code": "CUMULATIVE_CONTEXT_MISMATCH",
                    "field": tissue_key,
                    "message": (
                        "The same tissue has multiple alpha/beta contexts; P15 kept them "
                        "in separate groups and did not combine them."
                    ),
                }
            )

    sensitivity_raw = request.get("sensitivity_recovery_fractions", [0.0, 0.25, 0.5, 0.75, 1.0])
    sensitivity_values = [
        _nonnegative(item, f"sensitivity_recovery_fractions[{index}]")
        for index, item in enumerate(
            _array(
                sensitivity_raw, "sensitivity_recovery_fractions", max_length=MAX_SENSITIVITY_POINTS
            )
        )
    ]
    if not sensitivity_values:
        sensitivity_values = [0.0]
    if any(value > 1.0 for value in sensitivity_values):
        raise _fail(
            "RECOVERY_ASSUMPTION_INVALID",
            "Sensitivity recovery fractions must be between 0 and 1.",
            field="sensitivity_recovery_fractions",
        )

    group_results: list[dict[str, object]] = []
    sensitivity: list[dict[str, object]] = []
    for key, group in groups.items():
        alpha_beta = _finite(group["alpha_beta_gy"], f"groups[{key}].alpha_beta_gy")
        no_recovery = _finite(group["bed_no_recovery_gy"], f"groups[{key}].bed_no_recovery_gy")
        with_recovery = _finite(
            group["bed_with_recovery_gy"], f"groups[{key}].bed_with_recovery_gy"
        )
        group["eqd2_no_recovery_gy"] = _eqd2(no_recovery, alpha_beta)
        group["eqd2_with_recovery_gy"] = _eqd2(with_recovery, alpha_beta)
        group["recovery_delta_bed_gy"] = with_recovery - no_recovery
        group["recovery_delta_eqd2_gy"] = _eqd2(with_recovery, alpha_beta) - _eqd2(
            no_recovery, alpha_beta
        )
        group["cumulative_allowed"] = True
        group_results.append(group)
        points: list[dict[str, object]] = []
        course_contributions = group["course_contributions"]
        if not isinstance(course_contributions, list):
            course_contributions = []
        for sensitivity_recovery in sensitivity_values:
            bed_value = 0.0
            for contribution in course_contributions:
                if isinstance(contribution, Mapping):
                    raw = float(contribution["bed_raw_gy"])
                    bed_value += raw * (
                        1.0 - sensitivity_recovery if bool(contribution["is_prior"]) else 1.0
                    )
            points.append(
                {
                    "recovery_fraction": sensitivity_recovery,
                    "bed_gy": bed_value,
                    "eqd2_gy": _eqd2(bed_value, alpha_beta),
                }
            )
        sensitivity.append({"group_key": key, "points": points})

    assumptions = {
        "recovery_mode": recovery_mode,
        "evaluation_date": evaluation_date.isoformat() if evaluation_date else None,
        "recovery_applied_once_to_prior_courses": recovery_mode == "USER_DEFINED",
        "scalar_only": True,
        "prescription_generated": False,
        "qa_or_patient_linkage": False,
    }
    result_without_checksum: dict[str, object] = {
        "schema_version": "biological-reirradiation-result.v1",
        "operation": "REIRRADIATION",
        "model_key": REIRRADIATION_ENGINE_KEY,
        "model_version": REIRRADIATION_ENGINE_VERSION,
        "capability": capability,
        "assumptions": assumptions,
        "course_contributions": course_rows,
        "groups": group_results,
        "sensitivity": sensitivity,
        "warnings": warnings,
    }
    return {**result_without_checksum, "result_sha256": _canonical_sha256(result_without_checksum)}


def _intervals(request: Mapping[str, object]) -> list[dict[str, object]]:
    raw_intervals = request.get("interruptions", [])
    if not isinstance(raw_intervals, Sequence) or isinstance(
        raw_intervals, (str, bytes, bytearray)
    ):
        raise _fail(
            "INTERRUPTION_INTERVAL_INVALID",
            "interruptions must be an array.",
            field="interruptions",
        )
    parsed: list[dict[str, object]] = []
    for index, raw in enumerate(raw_intervals):
        prefix = f"interruptions[{index}]"
        item = _mapping(raw, prefix)
        start = _date_value(item.get("start_date"), f"{prefix}.start_date")
        end = _date_value(item.get("end_date"), f"{prefix}.end_date")
        if end <= start:
            raise _fail(
                "INTERRUPTION_INTERVAL_INVALID",
                "An interruption must have end_date after start_date.",
                field=f"{prefix}.end_date",
            )
        parsed.append(
            {
                "start_date": start,
                "end_date": end,
                "label": str(item.get("label", "")).strip() or None,
            }
        )
    ordered = sorted(parsed, key=lambda item: str(item["start_date"]))
    for previous, current in zip(ordered, ordered[1:], strict=False):
        previous_end = previous["end_date"]
        current_start = current["start_date"]
        if (
            isinstance(previous_end, date)
            and isinstance(current_start, date)
            and current_start < previous_end
        ):
            raise _fail(
                "INTERRUPTION_OVERLAP",
                "Interruption intervals must not overlap.",
                field="interruptions",
            )
    normalized: list[dict[str, object]] = []
    for item in parsed:
        start_value = item["start_date"]
        end_value = item["end_date"]
        assert isinstance(start_value, date) and isinstance(end_value, date)
        normalized.append(
            {
                **item,
                "start_date": start_value.isoformat(),
                "end_date": end_value.isoformat(),
            }
        )
    return normalized


def _compensation_point(doses: Sequence[float], alpha_beta: float) -> dict[str, object]:
    total = sum(doses)
    bed = _bed(doses, alpha_beta)
    return {
        "fraction_doses_gy": list(doses),
        "fraction_count": len(doses),
        "total_dose_gy": total,
        "bed_lq_gy": bed,
        "eqd2_lq_gy": _eqd2(bed, alpha_beta),
    }


def calculate_fraction_compensation(request: Mapping[str, object]) -> dict[str, object]:
    """Compare delivered-prefix-preserving alternative fraction schedules."""

    planned_raw = request.get("planned_fraction_doses_gy")
    planned = tuple(
        _nonnegative(item, f"planned_fraction_doses_gy[{index}]")
        for index, item in enumerate(
            _array(planned_raw, "planned_fraction_doses_gy", max_length=MAX_FRACTIONS)
        )
    )
    if not planned:
        raise _fail(
            "FRACTION_SCHEDULE_REQUIRED",
            "The planned fraction schedule cannot be empty.",
            field="planned_fraction_doses_gy",
        )
    delivered_raw = request.get("delivered_fraction_doses_gy", [])
    delivered = tuple(
        _nonnegative(item, f"delivered_fraction_doses_gy[{index}]")
        for index, item in enumerate(
            _array(delivered_raw, "delivered_fraction_doses_gy", max_length=MAX_FRACTIONS)
        )
    )
    if len(delivered) > len(planned):
        raise _fail(
            "FRACTION_SCHEDULE_INVALID",
            "Delivered fractions cannot exceed the planned schedule.",
            field="delivered_fraction_doses_gy",
        )
    tolerance = _positive(request.get("consistency_tolerance_gy", 0.01), "consistency_tolerance_gy")
    for index, dose in enumerate(delivered):
        if abs(dose - planned[index]) > tolerance:
            raise _fail(
                "FRACTION_SCHEDULE_INVALID",
                "The delivered prefix must match the original planned schedule.",
                field=f"delivered_fraction_doses_gy[{index}]",
            )
    alpha_beta, source_type, source_reference = _alpha_beta(request, "")
    interruptions = _intervals(request)
    raw_alternatives = request.get("alternatives")
    if (
        not isinstance(raw_alternatives, Sequence)
        or isinstance(raw_alternatives, (str, bytes, bytearray))
        or not raw_alternatives
    ):
        raise _fail(
            "ALTERNATIVE_SCHEDULE_REQUIRED",
            "At least one compensation alternative is required.",
            field="alternatives",
        )
    if len(raw_alternatives) > MAX_ALTERNATIVES:
        raise _fail(
            "ALTERNATIVE_LIMIT_EXCEEDED",
            f"At most {MAX_ALTERNATIVES} alternatives are supported.",
            field="alternatives",
        )
    remaining_baseline = planned[len(delivered) :]
    baseline_point = _compensation_point(planned, alpha_beta)
    seen: set[str] = set()
    alternatives: list[dict[str, object]] = []
    for index, raw in enumerate(raw_alternatives):
        prefix = f"alternatives[{index}]"
        alternative = _mapping(raw, prefix)
        alternative_id = _text(
            alternative.get("alternative_id"), f"{prefix}.alternative_id", max_length=80
        )
        if alternative_id in seen:
            raise _fail(
                "ALTERNATIVE_ID_DUPLICATE",
                "Alternative identifiers must be unique.",
                field=f"{prefix}.alternative_id",
            )
        seen.add(alternative_id)
        label = _text(alternative.get("label", alternative_id), f"{prefix}.label", max_length=240)
        remaining_raw = alternative.get("remaining_fraction_doses_gy")
        remaining = tuple(
            _nonnegative(item, f"{prefix}.remaining_fraction_doses_gy[{dose_index}]")
            for dose_index, item in enumerate(
                _array(
                    remaining_raw, f"{prefix}.remaining_fraction_doses_gy", max_length=MAX_FRACTIONS
                )
            )
        )
        full = delivered + remaining
        point = _compensation_point(full, alpha_beta)
        point.update(
            {
                "alternative_id": alternative_id,
                "label": label,
                "delivered_prefix_unchanged": list(full[: len(delivered)]) == list(delivered),
                "delivered_fraction_count": len(delivered),
                "remaining_fraction_count": len(remaining),
                "remaining_total_dose_gy": sum(remaining),
                "delta_total_dose_vs_planned_gy": _finite(
                    point["total_dose_gy"], f"{prefix}.total_dose_gy"
                )
                - _finite(baseline_point["total_dose_gy"], "planned.total_dose_gy"),
                "delta_bed_vs_planned_gy": _finite(point["bed_lq_gy"], f"{prefix}.bed_lq_gy")
                - _finite(baseline_point["bed_lq_gy"], "planned.bed_lq_gy"),
                "delta_eqd2_vs_planned_gy": _finite(point["eqd2_lq_gy"], f"{prefix}.eqd2_lq_gy")
                - _finite(baseline_point["eqd2_lq_gy"], "planned.eqd2_lq_gy"),
            }
        )
        if not bool(point["delivered_prefix_unchanged"]):
            raise _fail(
                "ALTERNATIVE_PREFIX_CHANGED",
                "An alternative may change only the remaining schedule.",
                field=f"{prefix}.remaining_fraction_doses_gy",
            )
        alternatives.append(point)

    warnings: list[dict[str, object]] = []
    time_model = _mapping(request.get("time_model", {"mode": "NONE"}), "time_model")
    time_mode = str(time_model.get("mode", "NONE")).strip().upper()
    if time_mode not in {"NONE", "USER_DEFINED_LINEAR"}:
        raise _fail(
            "TIME_MODEL_INVALID",
            "time_model.mode must be NONE or USER_DEFINED_LINEAR.",
            field="time_model.mode",
        )
    time_adjustment: dict[str, object] = {
        "mode": time_mode,
        "applied": False,
        "repopulation_penalty_bed_gy": None,
    }
    if time_mode == "NONE":
        warnings.append(
            {
                "code": "NO_REPOPULATION_CORRECTION",
                "field": "time_model",
                "message": (
                    "No time/repopulation model was applied; results are LQ schedule "
                    "estimates only."
                ),
            }
        )
    else:
        source = time_model.get("source_reference")
        if not isinstance(source, str) or not source.strip():
            raise _fail(
                "TIME_MODEL_SOURCE_REQUIRED",
                "A user-defined time model requires a source reference.",
                field="time_model.source_reference",
            )
        treatment_start = _date_value(
            time_model.get("treatment_start_date"), "time_model.treatment_start_date"
        )
        evaluation_date = _date_value(
            time_model.get("evaluation_date"), "time_model.evaluation_date"
        )
        if evaluation_date < treatment_start:
            raise _fail(
                "COURSE_INTERVAL_INVALID",
                "time_model evaluation date cannot precede treatment start.",
                field="time_model.evaluation_date",
            )
        rate = _nonnegative(
            time_model.get("repopulation_rate_bed_gy_per_day"),
            "time_model.repopulation_rate_bed_gy_per_day",
        )
        kickoff = _nonnegative(time_model.get("kickoff_days", 0), "time_model.kickoff_days")
        elapsed = float((evaluation_date - treatment_start).days)
        penalty = max(0.0, elapsed - kickoff) * rate
        time_adjustment = {
            "mode": time_mode,
            "applied": True,
            "source_reference": source.strip(),
            "treatment_start_date": treatment_start.isoformat(),
            "evaluation_date": evaluation_date.isoformat(),
            "elapsed_days": elapsed,
            "kickoff_days": kickoff,
            "repopulation_rate_bed_gy_per_day": rate,
            "repopulation_penalty_bed_gy": penalty,
        }
        for alternative in alternatives:
            bed_after = max(
                0.0, _finite(alternative["bed_lq_gy"], "alternative.bed_lq_gy") - penalty
            )
            alternative["bed_after_time_model_gy"] = bed_after
            alternative["eqd2_after_time_model_gy"] = _eqd2(bed_after, alpha_beta)

    for alternative in alternatives:
        alternative.setdefault("bed_after_time_model_gy", None)
        alternative.setdefault("eqd2_after_time_model_gy", None)
    result_without_checksum: dict[str, object] = {
        "schema_version": "biological-fraction-compensation-result.v1",
        "operation": "FRACTION_COMPENSATION",
        "model_key": FRACTION_COMPENSATION_ENGINE_KEY,
        "model_version": FRACTION_COMPENSATION_ENGINE_VERSION,
        "alpha_beta": {
            "value_gy": alpha_beta,
            "source_type": source_type,
            "source_reference": source_reference,
        },
        "planned_schedule": _compensation_point(planned, alpha_beta),
        "delivered_prefix": _compensation_point(delivered, alpha_beta)
        if delivered
        else {
            "fraction_doses_gy": [],
            "fraction_count": 0,
            "total_dose_gy": 0.0,
            "bed_lq_gy": 0.0,
            "eqd2_lq_gy": 0.0,
        },
        "remaining_baseline_schedule": {
            "fraction_doses_gy": list(remaining_baseline),
            "fraction_count": len(remaining_baseline),
            "total_dose_gy": sum(remaining_baseline),
        },
        "alternatives": alternatives,
        "interruptions": interruptions,
        "time_model": time_adjustment,
        "capability": {
            "scalar_schedule_comparison": True,
            "spatial_accumulation": "UNAVAILABLE",
            "prescription_generated": False,
        },
        "warnings": warnings,
    }
    return {**result_without_checksum, "result_sha256": _canonical_sha256(result_without_checksum)}


def request_fingerprint(snapshot: dict[str, object]) -> str:
    """Return a stable identity for an immutable P15 request snapshot."""

    return _canonical_sha256(snapshot)
