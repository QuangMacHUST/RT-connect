"""Deterministic BED/EQD2 calculations for the independent P13 toolkit.

The module deliberately has no database, HTTP or patient-data dependency.  It
accepts an explicit fractionation snapshot, validates it, and returns one
JSON-serialisable result containing the primary value and the complete chart
dataset.  The API layer is responsible for scoping and persisting that
snapshot; this module is the numerical authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Literal

BED_EQD2_ENGINE_KEY = "biological.bed-eqd2"
BED_EQD2_ENGINE_VERSION = "p13-lq-1.0.0"
MAX_FRACTIONS = 1_000_000
MAX_ALPHA_BETA_VALUES = 10
MAX_CURVE_POINTS = 5_001

CurveMode = Literal["FIXED_N", "FIXED_D"]


class BedEqd2EngineError(ValueError):
    """A stable, field-addressable numerical validation failure."""

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
class NormalizedFractionation:
    total_dose_gy: float
    fractions: int
    dose_per_fraction_gy: float
    supplied_total_dose_gy: float | None
    supplied_fractions: int | None
    supplied_dose_per_fraction_gy: float | None
    consistency_delta_gy: float
    consistency_tolerance_gy: float

    def as_dict(self) -> dict[str, object]:
        return {
            "total_dose_gy": self.total_dose_gy,
            "fractions": self.fractions,
            "dose_per_fraction_gy": self.dose_per_fraction_gy,
            "supplied_total_dose_gy": self.supplied_total_dose_gy,
            "supplied_fractions": self.supplied_fractions,
            "supplied_dose_per_fraction_gy": self.supplied_dose_per_fraction_gy,
            "consistency_delta_gy": self.consistency_delta_gy,
            "consistency_tolerance_gy": self.consistency_tolerance_gy,
        }


@dataclass(frozen=True)
class CurveSpec:
    mode: CurveMode = "FIXED_N"
    dose_min_gy: float = 0.0
    dose_max_gy: float = 100.0
    dose_step_gy: float = 1.0
    fixed_n: int | None = None
    fixed_d_gy: float | None = None
    alpha_beta_values_gy: tuple[float, ...] = ()
    point_limit: int = 501

    def as_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "dose_min_gy": self.dose_min_gy,
            "dose_max_gy": self.dose_max_gy,
            "dose_step_gy": self.dose_step_gy,
            "fixed_n": self.fixed_n,
            "fixed_d_gy": self.fixed_d_gy,
            "alpha_beta_values_gy": list(self.alpha_beta_values_gy),
            "point_limit": self.point_limit,
        }


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            "A numeric finite value is required.",
            field=field,
        )
    number = float(value)
    if not math.isfinite(number):
        raise BedEqd2EngineError(
            "CALCULATION_NONFINITE",
            "The supplied value must be finite; NaN and Infinity are not accepted.",
            field=field,
        )
    return number


def _nonnegative(value: object, field: str) -> float:
    number = _finite_number(value, field)
    if number < 0:
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            "The value cannot be negative.",
            field=field,
        )
    return number


def _positive(value: object, field: str) -> float:
    number = _finite_number(value, field)
    if number <= 0:
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            "The value must be greater than zero.",
            field=field,
        )
    return number


def _integer_fractions(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            "The number of fractions must be an integer.",
            field=field,
        )
    number = float(value)
    if not math.isfinite(number) or not number.is_integer():
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            "The number of fractions must be a finite integer.",
            field=field,
        )
    result = int(number)
    if result <= 0 or result > MAX_FRACTIONS:
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            f"The number of fractions must be between 1 and {MAX_FRACTIONS}.",
            field=field,
        )
    return result


def normalize_fractionation(
    *,
    total_dose_gy: float | int | None,
    fractions: int | float | None,
    dose_per_fraction_gy: float | int | None,
    consistency_tolerance_gy: float = 0.01,
) -> NormalizedFractionation:
    """Normalize any valid pair of D, n and d without silently fixing a mismatch."""

    tolerance = _positive(consistency_tolerance_gy, "consistency_tolerance_gy")
    total = None if total_dose_gy is None else _nonnegative(total_dose_gy, "total_dose_gy")
    count = None if fractions is None else _integer_fractions(fractions, "fractions")
    dose = (
        None
        if dose_per_fraction_gy is None
        else _nonnegative(dose_per_fraction_gy, "dose_per_fraction_gy")
    )
    supplied_count = sum(value is not None for value in (total, count, dose))
    if supplied_count < 2:
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            "At least two of total dose, fractions and dose per fraction are required.",
            details=[
                {
                    "field": "fractionation",
                    "message": (
                        "Provide any two of total_dose_gy, fractions and "
                        "dose_per_fraction_gy."
                    ),
                }
            ],
        )

    if total is not None and count is not None and dose is not None:
        expected_total = count * dose
        delta = abs(total - expected_total)
        if delta > tolerance:
            raise BedEqd2EngineError(
                "FRACTIONATION_INCONSISTENT",
                "Total dose is not consistent with fractions multiplied by dose per fraction.",
                details=[
                    {
                        "field": "total_dose_gy",
                        "message": f"Difference is {delta:g} Gy; tolerance is {tolerance:g} Gy.",
                    },
                    {
                        "field": "dose_per_fraction_gy",
                        "message": "Check D = n × d or provide only two independent values.",
                    },
                ],
            )
        normalized_total = total
        normalized_dose = dose
        return NormalizedFractionation(
            total_dose_gy=normalized_total,
            fractions=count,
            dose_per_fraction_gy=normalized_dose,
            supplied_total_dose_gy=total,
            supplied_fractions=count,
            supplied_dose_per_fraction_gy=dose,
            consistency_delta_gy=delta,
            consistency_tolerance_gy=tolerance,
        )

    if total is not None and count is not None:
        normalized_dose = total / count
        normalized_total = total
        normalized_count = count
        delta = 0.0
    elif total is not None and dose is not None:
        if dose == 0:
            if total != 0:
                raise BedEqd2EngineError(
                    "FRACTIONATION_INCONSISTENT",
                    "A positive total dose cannot be paired with zero dose per fraction.",
                    field="dose_per_fraction_gy",
                )
            raise BedEqd2EngineError(
                "BIOLOGICAL_INPUT_INVALID",
                (
                    "When total dose and dose per fraction are both zero, "
                    "provide a positive fraction count."
                ),
                field="fractions",
            )
        raw_count = total / dose
        normalized_count = int(round(raw_count))
        if normalized_count <= 0 or abs(total - normalized_count * dose) > tolerance:
            raise BedEqd2EngineError(
                "FRACTIONATION_INCONSISTENT",
                (
                    "Total dose divided by dose per fraction must produce a "
                    "positive integer fraction count."
                ),
                details=[
                    {
                        "field": "fractions",
                        "message": (
                            "The derived fraction count is not an integer within "
                            "the selected tolerance."
                        ),
                    }
                ],
            )
        normalized_total = total
        normalized_dose = dose
        delta = abs(total - normalized_count * dose)
    else:
        assert count is not None and dose is not None
        normalized_count = count
        normalized_dose = dose
        normalized_total = count * dose
        delta = 0.0

    if not math.isfinite(normalized_total) or not math.isfinite(normalized_dose):
        raise BedEqd2EngineError(
            "CALCULATION_NONFINITE",
            "Fractionation normalization produced a non-finite value.",
            field="fractionation",
        )
    return NormalizedFractionation(
        total_dose_gy=normalized_total,
        fractions=normalized_count,
        dose_per_fraction_gy=normalized_dose,
        supplied_total_dose_gy=total,
        supplied_fractions=count,
        supplied_dose_per_fraction_gy=dose,
        consistency_delta_gy=delta,
        consistency_tolerance_gy=tolerance,
    )


def _validate_alpha_beta(alpha_beta_gy: object) -> float:
    value = _positive(alpha_beta_gy, "alpha_beta_gy")
    if not math.isfinite(1.0 + 2.0 / value):
        raise BedEqd2EngineError(
            "CALCULATION_NONFINITE",
            "The EQD2 denominator is not finite.",
            field="alpha_beta_gy",
        )
    return value


def _validate_source(source_type: str, source_reference: str | None) -> None:
    if source_type not in {"USER_DEFINED", "REFERENCE"}:
        raise BedEqd2EngineError(
            "BIOLOGICAL_INPUT_INVALID",
            "Alpha/beta source type must be USER_DEFINED or REFERENCE.",
            field="alpha_beta_source_type",
        )
    if source_reference is None or not source_reference.strip():
        raise BedEqd2EngineError(
            "ALPHA_BETA_SOURCE_REQUIRED",
            "An explicit alpha/beta source or user-defined note is required.",
            field="alpha_beta_source_reference",
        )


def _primary_point(
    *,
    total_dose_gy: float,
    fractions: int,
    dose_per_fraction_gy: float,
    alpha_beta_gy: float,
) -> dict[str, object]:
    bed = total_dose_gy * (1.0 + dose_per_fraction_gy / alpha_beta_gy)
    eqd2 = bed / (1.0 + 2.0 / alpha_beta_gy)
    values = (total_dose_gy, dose_per_fraction_gy, bed, eqd2)
    if not all(math.isfinite(value) for value in values):
        raise BedEqd2EngineError(
            "CALCULATION_NONFINITE",
            "BED/EQD2 calculation produced a non-finite result.",
            field="calculation",
        )
    return {
        "total_dose_gy": total_dose_gy,
        "fractions": fractions,
        "dose_per_fraction_gy": dose_per_fraction_gy,
        "alpha_beta_gy": alpha_beta_gy,
        "bed_gy": bed,
        "eqd2_gy": eqd2,
    }


def _curve_doses(
    normalized: NormalizedFractionation,
    curve: CurveSpec,
) -> tuple[list[tuple[float, int, float]], dict[str, object]]:
    minimum = _nonnegative(curve.dose_min_gy, "curve.dose_min_gy")
    maximum = _nonnegative(curve.dose_max_gy, "curve.dose_max_gy")
    step = _positive(curve.dose_step_gy, "curve.dose_step_gy")
    if maximum < minimum:
        raise BedEqd2EngineError(
            "CURVE_RANGE_INVALID",
            "Curve maximum dose must be greater than or equal to the minimum dose.",
            field="curve.dose_max_gy",
        )
    if curve.point_limit < 1 or curve.point_limit > MAX_CURVE_POINTS:
        raise BedEqd2EngineError(
            "CURVE_RANGE_INVALID",
            f"Curve point limit must be between 1 and {MAX_CURVE_POINTS}.",
            field="curve.point_limit",
        )

    mode = curve.mode
    if mode not in {"FIXED_N", "FIXED_D"}:
        raise BedEqd2EngineError(
            "CURVE_RANGE_INVALID",
            "Curve mode must be FIXED_N or FIXED_D.",
            field="curve.mode",
        )

    values: list[tuple[float, int, float]] = []
    parameters: dict[str, object] = {
        "mode": mode,
        "dose_min_gy": minimum,
        "dose_max_gy": maximum,
        "requested_step_gy": step,
    }
    epsilon = max(1e-12, abs(maximum) * 1e-12)

    if mode == "FIXED_N":
        fixed_n = normalized.fractions if curve.fixed_n is None else _integer_fractions(
            curve.fixed_n, "curve.fixed_n"
        )
        index = 0
        while True:
            dose_value = minimum + index * step
            if dose_value > maximum + epsilon:
                break
            if dose_value > maximum:
                dose_value = maximum
            values.append((dose_value, fixed_n, dose_value / fixed_n))
            if len(values) > curve.point_limit:
                raise BedEqd2EngineError(
                    "CURVE_RANGE_INVALID",
                    "The selected range exceeds the curve point limit.",
                    field="curve.point_limit",
                )
            index += 1
        parameters.update({"fixed_n": fixed_n, "effective_step_gy": step})
    else:
        fixed_d = (
            normalized.dose_per_fraction_gy
            if curve.fixed_d_gy is None
            else _nonnegative(curve.fixed_d_gy, "curve.fixed_d_gy")
        )
        if fixed_d <= 0:
            raise BedEqd2EngineError(
                "CURVE_RANGE_INVALID",
                "FIXED_D requires a positive fixed dose per fraction.",
                field="curve.fixed_d_gy",
            )
        step_ratio = step / fixed_d
        integer_step = int(round(step_ratio))
        if integer_step < 1 or abs(step_ratio - integer_step) > 1e-9:
            raise BedEqd2EngineError(
                "CURVE_RANGE_INVALID",
                "In FIXED_D mode, curve step must be an integer multiple of fixed d.",
                field="curve.dose_step_gy",
            )
        first_n = max(1, int(math.ceil(minimum / fixed_d - 1e-12)))
        last_n = int(math.floor(maximum / fixed_d + 1e-12))
        if last_n < first_n:
            raise BedEqd2EngineError(
                "CURVE_RANGE_INVALID",
                "The selected dose range contains no positive integer fraction point for fixed d.",
                field="curve",
            )
        count = ((last_n - first_n) // integer_step) + 1
        if count > curve.point_limit:
            raise BedEqd2EngineError(
                "CURVE_RANGE_INVALID",
                "The selected range exceeds the curve point limit.",
                field="curve.point_limit",
            )
        for current_n in range(first_n, last_n + 1, integer_step):
            dose_value = current_n * fixed_d
            values.append((dose_value, current_n, fixed_d))
        parameters.update(
            {
                "fixed_d_gy": fixed_d,
                "fraction_min": first_n,
                "fraction_max": last_n,
                "fraction_step": integer_step,
                "effective_step_gy": integer_step * fixed_d,
            }
        )

    if not values:
        raise BedEqd2EngineError(
            "CURVE_RANGE_INVALID",
            "The selected curve range contains no points.",
            field="curve",
        )
    return values, parameters


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def calculate_bed_eqd2(
    *,
    fractionation: NormalizedFractionation,
    alpha_beta_gy: float | int,
    alpha_beta_source_type: str,
    alpha_beta_source_reference: str,
    curve: CurveSpec,
) -> dict[str, object]:
    """Calculate primary BED/EQD2 and a reproducible chart/table snapshot."""

    alpha_beta = _validate_alpha_beta(alpha_beta_gy)
    source_reference = alpha_beta_source_reference.strip()
    _validate_source(alpha_beta_source_type, source_reference)

    alpha_values: list[float] = []
    raw_alpha_values = curve.alpha_beta_values_gy or (alpha_beta,)
    if len(raw_alpha_values) > MAX_ALPHA_BETA_VALUES:
        raise BedEqd2EngineError(
            "CURVE_RANGE_INVALID",
            f"At most {MAX_ALPHA_BETA_VALUES} alpha/beta curves are allowed.",
            field="curve.alpha_beta_values_gy",
        )
    for index, value in enumerate(raw_alpha_values):
        validated = _validate_alpha_beta(value)
        if validated in alpha_values:
            raise BedEqd2EngineError(
                "CURVE_RANGE_INVALID",
                "Alpha/beta curve values must be unique.",
                field=f"curve.alpha_beta_values_gy[{index}]",
            )
        alpha_values.append(validated)

    curve_values, curve_parameters = _curve_doses(fractionation, curve)
    total_points = len(curve_values) * len(alpha_values)
    if total_points > curve.point_limit:
        raise BedEqd2EngineError(
            "CURVE_RANGE_INVALID",
            "The total dose-by-alpha/beta dataset exceeds the curve point limit.",
            field="curve.point_limit",
        )

    primary = _primary_point(
        total_dose_gy=fractionation.total_dose_gy,
        fractions=fractionation.fractions,
        dose_per_fraction_gy=fractionation.dose_per_fraction_gy,
        alpha_beta_gy=alpha_beta,
    )
    series: list[dict[str, object]] = []
    table_rows: list[dict[str, object]] = []
    for curve_alpha_beta in alpha_values:
        points = [
            _primary_point(
                total_dose_gy=dose_value,
                fractions=fraction_count,
                dose_per_fraction_gy=dose_per_fraction,
                alpha_beta_gy=curve_alpha_beta,
            )
            for dose_value, fraction_count, dose_per_fraction in curve_values
        ]
        series.append(
            {
                "series_key": f"alpha-beta-{curve_alpha_beta:g}-gy",
                "alpha_beta_gy": curve_alpha_beta,
                "points": points,
            }
        )
        table_rows.extend(points)

    chart_without_hash: dict[str, object] = {
        "schema_version": "biological-chart-dataset.v1",
        "parameters": {
            **curve_parameters,
            "alpha_beta_values_gy": alpha_values,
            "point_limit": curve.point_limit,
        },
        "series": series,
        "point_count": total_points,
    }
    chart_dataset = {
        **chart_without_hash,
        "dataset_sha256": _canonical_sha256(chart_without_hash),
    }
    return {
        "schema_version": "biological-bed-eqd2-result.v1",
        "engine": {"key": BED_EQD2_ENGINE_KEY, "version": BED_EQD2_ENGINE_VERSION},
        "formula": {
            "bed": "BED = D × (1 + d / (alpha/beta))",
            "eqd2": "EQD2 = BED / (1 + 2 / (alpha/beta))",
            "rounding": (
                "No rounding before calculation; display rounding is a "
                "presentation concern."
            ),
        },
        "fractionation": fractionation.as_dict(),
        "alpha_beta": {
            "value_gy": alpha_beta,
            "source_type": alpha_beta_source_type,
            "source_reference": source_reference,
        },
        "primary": primary,
        "table_rows": table_rows,
        "chart_dataset": chart_dataset,
    }


def request_fingerprint(request_snapshot: dict[str, object]) -> str:
    """Return a stable identity for an idempotent P13 request."""

    return _canonical_sha256(request_snapshot)
