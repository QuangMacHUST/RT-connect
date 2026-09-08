"""Deterministic multi-option BED/EQD2 comparison for the P14 toolkit.

The engine consumes already persisted P13 calculation snapshots.  It does not
read the database, treatment records, patient records, or a mutable browser
form.  The API layer resolves and scopes the source calculations; this module
only validates the comparison contract and computes deltas from immutable
numeric inputs.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

PLAN_COMPARISON_ENGINE_KEY = "biological.plan-comparison"
PLAN_COMPARISON_ENGINE_VERSION = "p14-comparison-1.0.0"
MIN_OPTIONS = 2
MAX_OPTIONS = 10


class PlanComparisonEngineError(ValueError):
    """A stable, field-addressable comparison validation failure."""

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
class ComparisonOption:
    """The immutable P13 values required to compare one treatment option."""

    option_id: str
    label: str
    calculation_id: str
    scenario_id: str
    scenario_revision_id: str
    model_key: str
    model_version: str
    tissue_context: str
    total_dose_gy: float
    fractions: int
    dose_per_fraction_gy: float
    alpha_beta_gy: float
    alpha_beta_source_type: str
    alpha_beta_source_reference: str
    bed_gy: float
    eqd2_gy: float

    def as_dict(self) -> dict[str, object]:
        return {
            "option_id": self.option_id,
            "label": self.label,
            "calculation_id": self.calculation_id,
            "scenario_id": self.scenario_id,
            "scenario_revision_id": self.scenario_revision_id,
            "model_key": self.model_key,
            "model_version": self.model_version,
            "tissue_context": self.tissue_context,
            "fractionation": {
                "total_dose_gy": self.total_dose_gy,
                "fractions": self.fractions,
                "dose_per_fraction_gy": self.dose_per_fraction_gy,
            },
            "alpha_beta": {
                "value_gy": self.alpha_beta_gy,
                "source_type": self.alpha_beta_source_type,
                "source_reference": self.alpha_beta_source_reference,
            },
            "primary": {
                "bed_gy": self.bed_gy,
                "eqd2_gy": self.eqd2_gy,
            },
        }


def _finite_nonnegative(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "A finite numeric value is required.",
            field=field,
        )
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "The value must be finite and non-negative.",
            field=field,
        )
    return number


def _validate_option(option: ComparisonOption, index: int) -> ComparisonOption:
    prefix = f"options[{index}]"
    if not option.option_id.strip() or not option.label.strip():
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "Every option needs a stable ID and a non-blank label.",
            field=prefix,
        )
    if not option.calculation_id.strip():
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "Every option must reference a persisted P13 calculation.",
            field=f"{prefix}.calculation_id",
        )
    if isinstance(option.fractions, bool) or not isinstance(option.fractions, int):
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "The fraction count must be a positive integer.",
            field=f"{prefix}.fractions",
        )
    if option.fractions <= 0:
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "The fraction count must be a positive integer.",
            field=f"{prefix}.fractions",
        )
    _finite_nonnegative(option.total_dose_gy, f"{prefix}.total_dose_gy")
    _finite_nonnegative(option.dose_per_fraction_gy, f"{prefix}.dose_per_fraction_gy")
    alpha_beta = _finite_nonnegative(option.alpha_beta_gy, f"{prefix}.alpha_beta_gy")
    if alpha_beta <= 0:
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "Alpha/beta must be greater than zero.",
            field=f"{prefix}.alpha_beta_gy",
        )
    _finite_nonnegative(option.bed_gy, f"{prefix}.bed_gy")
    _finite_nonnegative(option.eqd2_gy, f"{prefix}.eqd2_gy")
    if (
        not option.scenario_id.strip()
        or not option.scenario_revision_id.strip()
        or not option.tissue_context.strip()
    ):
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "The scenario, revision and tissue context are required in every source snapshot.",
            field=f"{prefix}.context",
        )
    if (
        not option.model_key.strip()
        or not option.model_version.strip()
        or not option.alpha_beta_source_type.strip()
        or not option.alpha_beta_source_reference.strip()
    ):
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "The model and alpha/beta provenance are required in every source snapshot.",
            field=f"{prefix}.model",
        )
    return option


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def request_fingerprint(snapshot: dict[str, object]) -> str:
    """Return a stable identity for an idempotent P14 request."""

    return _canonical_sha256(snapshot)


def calculate_plan_comparison(
    *,
    options: list[ComparisonOption] | tuple[ComparisonOption, ...],
    baseline_option_id: str,
) -> dict[str, object]:
    """Calculate absolute and baseline-relative percentage deltas.

    A zero baseline is a valid comparison input.  Its absolute deltas remain
    usable, while percentage deltas are explicitly ``None`` with a reason; no
    Infinity, NaN, or fabricated zero percentage is emitted.
    """

    if len(options) < MIN_OPTIONS:
        raise PlanComparisonEngineError(
            "COMPARISON_OPTIONS_REQUIRED",
            f"At least {MIN_OPTIONS} treatment options are required.",
            field="options",
        )
    if len(options) > MAX_OPTIONS:
        raise PlanComparisonEngineError(
            "COMPARISON_LIMIT_EXCEEDED",
            f"At most {MAX_OPTIONS} treatment options can be compared.",
            field="options",
        )

    checked = [_validate_option(option, index) for index, option in enumerate(options)]
    option_ids = [option.option_id for option in checked]
    if len(set(option_ids)) != len(option_ids):
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "Option IDs must be unique and stable within a comparison.",
            field="options.option_id",
        )
    calculation_ids = [option.calculation_id for option in checked]
    if len(set(calculation_ids)) != len(calculation_ids):
        raise PlanComparisonEngineError(
            "COMPARISON_OPTION_INVALID",
            "Each option must reference a different persisted calculation.",
            field="options.calculation_id",
        )
    if not baseline_option_id or baseline_option_id not in option_ids:
        raise PlanComparisonEngineError(
            "COMPARISON_BASELINE_REQUIRED",
            "The selected baseline must identify one of the comparison options.",
            field="baseline_option_id",
        )

    first = checked[0]
    mismatches: list[dict[str, object]] = []
    for index, option in enumerate(checked[1:], start=1):
        for field_name, expected, actual in (
            ("scenario_id", first.scenario_id, option.scenario_id),
            ("scenario_revision_id", first.scenario_revision_id, option.scenario_revision_id),
            ("model_key", first.model_key, option.model_key),
            ("model_version", first.model_version, option.model_version),
            ("tissue_context", first.tissue_context, option.tissue_context),
        ):
            if actual != expected:
                mismatches.append(
                    {
                        "field": f"options[{index}].{field_name}",
                        "message": f"Expected {expected!s}; received {actual!s}.",
                    }
                )
    if mismatches:
        raise PlanComparisonEngineError(
            "COMPARISON_CONTEXT_MISMATCH",
            "All options must use the same scenario revision, tissue context, and model version.",
            details=mismatches,
        )

    baseline = next(option for option in checked if option.option_id == baseline_option_id)
    alpha_beta_values = sorted({option.alpha_beta_gy for option in checked})
    warnings: list[dict[str, object]] = []
    alpha_beta_comparable = len(alpha_beta_values) == 1
    if not alpha_beta_comparable:
        warnings.append(
            {
                "code": "COMPARISON_ALPHA_BETA_MISMATCH",
                "field": "options.alpha_beta_gy",
                "message": (
                    "Options use different alpha/beta values; display each result separately "
                    "and do not rank options automatically."
                ),
            }
        )

    def delta(value: float, baseline_value: float) -> tuple[float, float | None, str | None]:
        absolute = value - baseline_value
        if baseline_value == 0:
            return absolute, None, "BASELINE_ZERO"
        return absolute, absolute / baseline_value * 100.0, None

    rows: list[dict[str, object]] = []
    for option in checked:
        delta_bed, delta_bed_percent, delta_bed_reason = delta(option.bed_gy, baseline.bed_gy)
        delta_eqd2, delta_eqd2_percent, delta_eqd2_reason = delta(option.eqd2_gy, baseline.eqd2_gy)
        rows.append(
            {
                "option_id": option.option_id,
                "label": option.label,
                "calculation_id": option.calculation_id,
                "total_dose_gy": option.total_dose_gy,
                "fractions": option.fractions,
                "dose_per_fraction_gy": option.dose_per_fraction_gy,
                "alpha_beta_gy": option.alpha_beta_gy,
                "bed_gy": option.bed_gy,
                "eqd2_gy": option.eqd2_gy,
                "is_baseline": option.option_id == baseline_option_id,
                "delta_bed_gy": delta_bed,
                "delta_bed_percent": delta_bed_percent,
                "delta_bed_percent_reason": delta_bed_reason,
                "delta_eqd2_gy": delta_eqd2,
                "delta_eqd2_percent": delta_eqd2_percent,
                "delta_eqd2_percent_reason": delta_eqd2_reason,
            }
        )

    chart_without_hash: dict[str, object] = {
        "schema_version": "biological-comparison-chart.v1",
        "baseline_option_id": baseline_option_id,
        "categories": [
            {
                "option_id": row["option_id"],
                "label": row["label"],
                "bed_gy": row["bed_gy"],
                "eqd2_gy": row["eqd2_gy"],
                "delta_bed_gy": row["delta_bed_gy"],
                "delta_eqd2_gy": row["delta_eqd2_gy"],
                "is_baseline": row["is_baseline"],
            }
            for row in rows
        ],
        "point_count": len(rows),
    }
    chart_dataset = {
        **chart_without_hash,
        "dataset_sha256": _canonical_sha256(chart_without_hash),
    }
    return {
        "schema_version": "biological-plan-comparison-result.v1",
        "engine": {
            "key": PLAN_COMPARISON_ENGINE_KEY,
            "version": PLAN_COMPARISON_ENGINE_VERSION,
        },
        "baseline_option_id": baseline_option_id,
        "compatibility": {
            "scenario_id": first.scenario_id,
            "scenario_revision_id": first.scenario_revision_id,
            "tissue_context": first.tissue_context,
            "model_key": first.model_key,
            "model_version": first.model_version,
            "alpha_beta_values_gy": alpha_beta_values,
            "alpha_beta_comparable": alpha_beta_comparable,
            "ranking_allowed": False,
        },
        "warnings": warnings,
        "ranking": None,
        "options": [option.as_dict() for option in checked],
        "table_rows": rows,
        "chart_dataset": chart_dataset,
    }
