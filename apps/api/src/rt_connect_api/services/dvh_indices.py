"""Explicit, source-neutral HI/CI calculations for the P17 DVH profile.

The module intentionally computes only formulas that have been selected by the
user.  It never decides whether an index is clinically acceptable: thresholds,
clinical context and source matching belong to the knowledge/limit layer.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np

INDEX_DEFINITIONS = (
    "HI_D2_D98_OVER_D50",
    "HI_D5_OVER_D95",
    "CI_RTOG_95",
    "CI_PADDICK_95",
)


class DvhIndexError(ValueError):
    """Stable validation error for an explicitly requested HI/CI formula."""

    def __init__(self, code: str, message: str, *, field: str | None = None) -> None:
        self.code = code
        self.message = message
        self.field = field
        super().__init__(message)


def normalize_index_definitions(values: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for index, value in enumerate(values):
        definition = str(value).strip().upper()
        if definition not in INDEX_DEFINITIONS:
            raise DvhIndexError(
                "DVH_INDEX_DEFINITION_UNSUPPORTED",
                f"Unsupported HI/CI definition: {definition or '<empty>'}.",
                field=f"index_definitions[{index}]",
            )
        if definition not in normalized:
            normalized.append(definition)
    return tuple(normalized)


def _finite_positive(value: object, field: str) -> float:
    try:
        number = float(str(value))
    except (TypeError, ValueError) as exc:
        raise DvhIndexError(
            "DVH_INDEX_INPUT_INVALID", f"{field} must be numeric.", field=field
        ) from exc
    if not math.isfinite(number) or number <= 0:
        raise DvhIndexError(
            "DVH_INDEX_INPUT_INVALID", f"{field} must be positive and finite.", field=field
        )
    return number


def _not_computed(
    definition: str,
    formula: str,
    missing: list[str],
    parameters: Mapping[str, object],
) -> dict[str, object]:
    return {
        "formula_id": definition,
        "formula": formula,
        "status": "NOT_COMPUTED",
        "value": None,
        "unit": "RATIO",
        "parameters": dict(parameters),
        "missing_inputs": missing,
        "source": "Không đủ dữ liệu hình học/liều để tính; không suy đoán.",
    }


def _computed(
    definition: str,
    formula: str,
    value: float,
    parameters: Mapping[str, object],
) -> dict[str, object]:
    if not math.isfinite(value):
        return _not_computed(definition, formula, ["finite_result"], parameters)
    return {
        "formula_id": definition,
        "formula": formula,
        "status": "COMPUTED",
        "value": float(value),
        "unit": "RATIO",
        "parameters": dict(parameters),
        "missing_inputs": [],
        "source": "Liều vật lý trên lưới RTDOSE và vùng cấu trúc đã chọn.",
    }


def calculate_dvh_indices(
    definitions: Sequence[str],
    *,
    selected_dose_gy: np.ndarray,
    selected_volume_cc: np.ndarray,
    all_dose_gy: np.ndarray,
    all_volume_cc: np.ndarray,
    quantile,
    prescription_dose_gy: float | None = None,
) -> dict[str, object]:
    """Calculate explicitly requested indices and preserve their formulas.

    ``quantile`` is injected from the DVH engine so HI uses the same
    volume-weighted Dxx definition as the rest of the result.  CI uses the
    complete selected RTDOSE grid for the prescription isodose volume; that
    assumption is recorded in the returned parameters and is not a clinical
    pass/fail decision.
    """

    normalized = normalize_index_definitions(definitions)
    if not normalized:
        return {"status": "NOT_REQUESTED", "items": []}

    selected_dose = np.asarray(selected_dose_gy, dtype=np.float64).reshape(-1)
    selected_volume = np.asarray(selected_volume_cc, dtype=np.float64).reshape(-1)
    all_dose = np.asarray(all_dose_gy, dtype=np.float64).reshape(-1)
    all_volume = np.asarray(all_volume_cc, dtype=np.float64).reshape(-1)
    if (
        selected_dose.size == 0
        or selected_dose.shape != selected_volume.shape
        or all_dose.size == 0
        or all_dose.shape != all_volume.shape
        or np.any(~np.isfinite(selected_dose))
        or np.any(~np.isfinite(selected_volume))
        or np.any(selected_volume <= 0)
        or np.any(~np.isfinite(all_dose))
        or np.any(~np.isfinite(all_volume))
        or np.any(all_volume <= 0)
    ):
        raise DvhIndexError(
            "DVH_INDEX_INPUT_INVALID",
            "HI/CI input dose and volume arrays must be finite and positive.",
            field="index_definitions",
        )

    prescription = None
    if any(item.startswith("CI_") for item in normalized):
        if prescription_dose_gy is None:
            prescription = None
        else:
            prescription = _finite_positive(prescription_dose_gy, "prescription_dose_gy")

    items: list[dict[str, object]] = []
    for definition in normalized:
        if definition == "HI_D2_D98_OVER_D50":
            formula = "(D2 - D98) / D50"
            parameters = {"D2_percent": 2.0, "D98_percent": 98.0, "D50_percent": 50.0}
            d2 = float(quantile(selected_dose, selected_volume, 2.0))
            d98 = float(quantile(selected_dose, selected_volume, 98.0))
            d50 = float(quantile(selected_dose, selected_volume, 50.0))
            parameters.update({"D2_gy": d2, "D98_gy": d98, "D50_gy": d50})
            if d50 <= 0:
                items.append(_not_computed(definition, formula, ["D50_gy_positive"], parameters))
            else:
                items.append(_computed(definition, formula, (d2 - d98) / d50, parameters))
        elif definition == "HI_D5_OVER_D95":
            formula = "D5 / D95"
            parameters = {"D5_percent": 5.0, "D95_percent": 95.0}
            d5 = float(quantile(selected_dose, selected_volume, 5.0))
            d95 = float(quantile(selected_dose, selected_volume, 95.0))
            parameters.update({"D5_gy": d5, "D95_gy": d95})
            if d95 <= 0:
                items.append(_not_computed(definition, formula, ["D95_gy_positive"], parameters))
            else:
                items.append(_computed(definition, formula, d5 / d95, parameters))
        else:
            formula = "PIV95 / TV" if definition == "CI_RTOG_95" else "(TV95 × TV95) / (TV × PIV95)"
            ci_parameters: dict[str, object] = {
                "isodose_percent": 95.0,
                "prescription_dose_gy": prescription,
                "isodose_volume_source": "entire RTDOSE grid",
            }
            if prescription is None:
                items.append(
                    _not_computed(definition, formula, ["prescription_dose_gy"], ci_parameters)
                )
                continue
            threshold = prescription * 0.95
            piv_mask = all_dose >= threshold
            target_mask = selected_dose >= threshold
            piv95 = float(np.sum(all_volume[piv_mask]))
            tv95 = float(np.sum(selected_volume[target_mask]))
            target_volume = float(np.sum(selected_volume))
            ci_parameters.update(
                {
                    "isodose_threshold_gy": threshold,
                    "PIV95_cc": piv95,
                    "TV95_cc": tv95,
                    "TV_cc": target_volume,
                }
            )
            if piv95 <= 0 or target_volume <= 0:
                items.append(
                    _not_computed(
                        definition,
                        formula,
                        ["PIV95_cc_positive", "TV_cc_positive"],
                        ci_parameters,
                    )
                )
            elif definition == "CI_RTOG_95":
                items.append(_computed(definition, formula, piv95 / target_volume, ci_parameters))
            elif tv95 <= 0:
                items.append(
                    _not_computed(
                        definition,
                        formula,
                        ["TV95_cc_positive"],
                        ci_parameters,
                    )
                )
            else:
                items.append(
                    _computed(
                        definition,
                        formula,
                        (tv95 * tv95) / (target_volume * piv95),
                        ci_parameters,
                    )
                )

    return {
        "status": "COMPUTED"
        if any(item["status"] == "COMPUTED" for item in items)
        else "NOT_COMPUTED",
        "items": items,
    }
