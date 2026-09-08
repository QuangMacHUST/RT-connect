"""Explicit P17 adapters for P11 protocol rules and P16 dose-limit entries.

The DVH engine is deliberately unaware of clinical reference material.  This
adapter is the boundary used when a user explicitly selects one compatible
rule for a DVH calculation.  It snapshots the selected source and evaluates a
single metric; it never searches for, ranks, or silently applies a limit.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from rt_connect_api.db.models import (
    BiologicalLibraryEntry,
    QAProtocolRule,
    QAProtocolVersion,
)
from rt_connect_api.services.biological_library_engine import (
    library_snapshot,
    request_fingerprint,
    validate_library_entry,
)

DVH_LIMIT_BINDING_SCHEMA_VERSION = "visual-dose-dvh.limit-binding.v1"
_OVERRIDE_FIELDS = frozenset(
    {
        "limit_value",
        "lower_limit",
        "upper_limit",
        "unit",
        "alpha_beta_gy",
        "fractions",
        "metric_parameter",
    }
)
_EFFECTIVE_FIELDS = (
    "metric_key",
    "operator",
    "limit_value",
    "lower_limit",
    "upper_limit",
    "unit",
    "volume_cc",
    "metric_parameter",
)
_NUMBER_RE = re.compile(r"^D(?P<percent>\d+(?:\.\d+)?)$")
_VOLUME_RE = re.compile(r"^V(?P<dose>\d+(?:\.\d+)?)$")


class DvhLimitAdapterError(ValueError):
    """Stable, field-addressable failure at the P17 limit boundary."""

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
class DvhLimitBinding:
    """Immutable source/effective-value snapshot used by one DVH operation."""

    snapshot: dict[str, object]
    effective_values: dict[str, object]
    warnings: list[dict[str, object]]


def _library_payload(entry: BiologicalLibraryEntry) -> dict[str, object]:
    """Return the P16 fields needed for validation and a reproducible snapshot."""

    return {
        "id": str(entry.id),
        "organization_id": str(entry.organization_id),
        "entry_type": entry.entry_type,
        "entry_key": entry.entry_key,
        "name": entry.name,
        "version_number": entry.version_number,
        "status": entry.status,
        "revision": entry.revision,
        "description": entry.description,
        "effective_note": entry.effective_note,
        "disease": entry.disease,
        "disease_subtype": entry.disease_subtype,
        "anatomy_site": entry.anatomy_site,
        "treatment_intent": entry.treatment_intent,
        "technique": entry.technique,
        "fractions": entry.fractions,
        "tissue_or_oar": entry.tissue_or_oar,
        "metric_key": entry.metric_key,
        "operator": entry.operator,
        "limit_value": entry.limit_value,
        "lower_limit": entry.lower_limit,
        "upper_limit": entry.upper_limit,
        "unit": entry.unit,
        "volume_cc": entry.volume_cc,
        "metric_parameter": entry.metric_parameter,
        "alpha_beta_gy": entry.alpha_beta_gy,
        "model_key": entry.model_key,
        "model_version": entry.model_version,
        "applicability": entry.applicability,
        "content": entry.content,
        "source_type": entry.source_type,
        "source_reference": entry.source_reference,
        "reference_status": entry.reference_status,
        "source_date": entry.source_date,
        "evidence_level": entry.evidence_level,
        "citation": entry.citation,
        "content_sha256": entry.content_sha256,
    }


def _effective_values(payload: Mapping[str, object]) -> dict[str, object]:
    return {
        field: payload[field]
        for field in _EFFECTIVE_FIELDS
        if field in payload and payload[field] is not None
    }


def _binding_snapshot(
    *,
    source_type: str,
    source_id: UUID,
    source_snapshot: dict[str, object],
    effective_values: dict[str, object],
    override: dict[str, object],
    warnings: list[dict[str, object]],
) -> dict[str, object]:
    material: dict[str, object] = {
        "schema_version": DVH_LIMIT_BINDING_SCHEMA_VERSION,
        "target_tool": "P17_DVH",
        "source_type": source_type,
        "source_id": str(source_id),
        "source_snapshot": source_snapshot,
        "effective_values": effective_values,
        "override": override,
        "override_label": "USER_OVERRIDE" if override else None,
        "warnings": warnings,
    }
    material["binding_sha256"] = request_fingerprint(material)
    return material


def _validate_override(override: dict[str, object]) -> None:
    invalid = sorted(set(override) - _OVERRIDE_FIELDS)
    if invalid:
        raise DvhLimitAdapterError(
            "DVH_LIMIT_OVERRIDE_INVALID",
            "Only explicit numeric/unit limit override fields are supported.",
            details=[
                {"field": f"limit_override.{field}", "message": "Override field is not supported."}
                for field in invalid
            ],
        )
    try:
        json.dumps(override, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise DvhLimitAdapterError(
            "DVH_LIMIT_OVERRIDE_INVALID",
            "Limit override must be finite JSON data.",
            field="limit_override",
        ) from exc


def _library_binding(
    session: Session,
    organization_id: UUID,
    entry_id: UUID,
    override: dict[str, object],
) -> DvhLimitBinding:
    # Tenant scope is part of the initial lookup; do not resolve globally and
    # check organization membership after reading the row.
    entry = session.scalar(
        select(BiologicalLibraryEntry).where(
            BiologicalLibraryEntry.id == entry_id,
            BiologicalLibraryEntry.organization_id == organization_id,
        )
    )
    if entry is None:
        raise DvhLimitAdapterError(
            "DVH_LIMIT_ENTRY_NOT_FOUND",
            "The selected dose-limit entry was not found in this organization.",
            field="limit_entry_id",
        )
    if entry.status == "ARCHIVED":
        raise DvhLimitAdapterError(
            "DVH_LIMIT_NOT_AVAILABLE",
            "An archived dose-limit entry cannot be selected for a new DVH calculation.",
            field="limit_entry_id",
        )
    if entry.entry_type != "DOSE_LIMIT":
        raise DvhLimitAdapterError(
            "DVH_LIMIT_ENTRY_INVALID",
            "P17 requires a DOSE_LIMIT library entry; other knowledge types are not rules.",
            field="limit_entry_id",
        )
    _validate_override(override)
    raw = _library_payload(entry)
    candidate = dict(raw)
    candidate.update(override)
    normalized, errors, source_warnings = validate_library_entry(candidate)
    if errors:
        raise DvhLimitAdapterError(
            "DVH_LIMIT_ENTRY_INVALID",
            "The selected dose-limit entry or explicit override is not valid for use.",
            details=[
                {
                    "field": item.get("field"),
                    "message": item.get("message", "The dose-limit definition is invalid."),
                }
                for item in errors
            ],
        )
    warnings: list[dict[str, object]] = [
        {
            "code": str(item.get("code", "DVH_LIMIT_REFERENCE_WARNING")),
            "field": item.get("field"),
            "message": str(item.get("message", "Review the selected reference.")),
        }
        for item in source_warnings
    ]
    if entry.status == "DRAFT":
        warnings.append(
            {
                "code": "DVH_LIMIT_DRAFT_SELECTED",
                "field": "limit_entry_id",
                "message": (
                    "The selected dose-limit entry is a draft; review it before relying "
                    "on the comparison."
                ),
            }
        )
    if entry.reference_status != "AVAILABLE":
        warnings.append(
            {
                "code": "DVH_LIMIT_REFERENCE_UNVERIFIED",
                "field": "reference_status",
                "message": "The selected limit source is not marked AVAILABLE in the library.",
            }
        )
    source_snapshot = {
        "source_kind": "BIOLOGICAL_LIBRARY",
        "entry_id": str(entry.id),
        "entry_key": entry.entry_key,
        "version_number": entry.version_number,
        "revision": entry.revision,
        "status": entry.status,
        "content_sha256": entry.content_sha256,
        "entry": library_snapshot(normalized),
    }
    effective = _effective_values(normalized)
    snapshot = _binding_snapshot(
        source_type="BIOLOGICAL_LIBRARY",
        source_id=entry.id,
        source_snapshot=source_snapshot,
        effective_values=effective,
        override=override,
        warnings=warnings,
    )
    return DvhLimitBinding(snapshot=snapshot, effective_values=effective, warnings=warnings)


def _protocol_binding(
    session: Session,
    organization_id: UUID,
    protocol_id: UUID,
    metric_key: str | None,
) -> DvhLimitBinding:
    protocol = session.scalar(
        select(QAProtocolVersion).where(
            QAProtocolVersion.id == protocol_id,
            QAProtocolVersion.organization_id == organization_id,
        )
    )
    if protocol is None:
        raise DvhLimitAdapterError(
            "DVH_PROTOCOL_NOT_FOUND",
            "The selected protocol version was not found in this organization.",
            field="protocol_version_id",
        )
    if protocol.status != "ACTIVE":
        raise DvhLimitAdapterError(
            "DVH_PROTOCOL_NOT_AVAILABLE",
            "Only an ACTIVE protocol version can be selected for a new DVH calculation.",
            field="protocol_version_id",
        )
    normalized_key = metric_key.strip().upper() if metric_key else ""
    if not normalized_key:
        raise DvhLimitAdapterError(
            "DVH_PROTOCOL_RULE_REQUIRED",
            "Select the metric rule to use from the selected protocol version.",
            field="protocol_metric_key",
        )
    rule = session.scalar(
        select(QAProtocolRule).where(
            QAProtocolRule.organization_id == organization_id,
            QAProtocolRule.protocol_version_id == protocol.id,
            QAProtocolRule.metric_key == normalized_key.lower(),
        )
    )
    if rule is None:
        raise DvhLimitAdapterError(
            "DVH_PROTOCOL_RULE_NOT_FOUND",
            "The selected metric rule was not found in this protocol version.",
            field="protocol_metric_key",
        )
    if rule.rule_type not in {"MAX", "MIN", "RANGE", "TARGET"}:
        raise DvhLimitAdapterError(
            "DVH_PROTOCOL_RULE_UNSUPPORTED",
            "This protocol rule type cannot be evaluated against a physical-dose DVH.",
            field="protocol_metric_key",
        )
    limit_value = rule.target_value
    if rule.rule_type == "MAX":
        limit_value = rule.upper_limit
    elif rule.rule_type == "MIN":
        limit_value = rule.lower_limit
    if rule.rule_type in {"MAX", "MIN", "TARGET"} and limit_value is None:
        raise DvhLimitAdapterError(
            "DVH_PROTOCOL_RULE_INVALID",
            "The selected protocol rule has no usable target or limit.",
            field="protocol_metric_key",
        )
    effective: dict[str, object] = {
        "metric_key": normalized_key,
        "operator": rule.rule_type,
        "limit_value": limit_value,
        "lower_limit": rule.lower_limit,
        "upper_limit": rule.upper_limit,
        "unit": rule.unit,
    }
    effective = {key: value for key, value in effective.items() if value is not None}
    source_snapshot = {
        "source_kind": "QA_PROTOCOL",
        "protocol_version_id": str(protocol.id),
        "protocol_key": protocol.protocol_key,
        "version_number": protocol.version_number,
        "revision": protocol.revision,
        "status": protocol.status,
        "source_type": protocol.source_type,
        "source_reference": protocol.source_reference,
        "protocol": {
            "name": protocol.name,
            "qa_type": protocol.qa_type,
            "applicability": protocol.applicability,
            "effective_note": protocol.effective_note,
        },
        "rule": {
            "id": str(rule.id),
            "metric_key": rule.metric_key,
            "display_name": rule.display_name,
            "unit": rule.unit,
            "rule_type": rule.rule_type,
            "target_value": rule.target_value,
            "lower_limit": rule.lower_limit,
            "upper_limit": rule.upper_limit,
            "tolerance": rule.tolerance,
            "action_level": rule.action_level,
            "required": rule.required,
            "note": rule.note,
            "reference": rule.reference,
        },
    }
    warnings: list[dict[str, object]] = []
    if protocol.source_type == "REFERENCE" and not protocol.source_reference:
        warnings.append(
            {
                "code": "DVH_PROTOCOL_REFERENCE_UNVERIFIED",
                "field": "protocol_version_id",
                "message": "The protocol is marked as a reference without a source identifier.",
            }
        )
    snapshot = _binding_snapshot(
        source_type="QA_PROTOCOL",
        source_id=protocol.id,
        source_snapshot=source_snapshot,
        effective_values=effective,
        override={},
        warnings=warnings,
    )
    return DvhLimitBinding(snapshot=snapshot, effective_values=effective, warnings=warnings)


def resolve_dvh_limit_binding(
    session: Session,
    organization_id: UUID,
    *,
    limit_entry_id: UUID | None,
    protocol_version_id: UUID | None,
    protocol_metric_key: str | None,
    override: dict[str, object],
) -> DvhLimitBinding | None:
    """Resolve one explicitly selected P16/P11 source, or no source."""

    if limit_entry_id is not None and protocol_version_id is not None:
        raise DvhLimitAdapterError(
            "DVH_LIMIT_BINDING_CONFLICT",
            "Select either a biological-library limit or a protocol rule, not both.",
            field="limit_entry_id",
        )
    if limit_entry_id is None and protocol_version_id is None:
        if override:
            raise DvhLimitAdapterError(
                "DVH_LIMIT_OVERRIDE_INVALID",
                "An explicit limit source is required before an override can be supplied.",
                field="limit_override",
            )
        if protocol_metric_key:
            raise DvhLimitAdapterError(
                "DVH_PROTOCOL_RULE_REQUIRED",
                "protocol_metric_key requires protocol_version_id.",
                field="protocol_metric_key",
            )
        return None
    if protocol_version_id is not None:
        if override:
            raise DvhLimitAdapterError(
                "DVH_LIMIT_OVERRIDE_INVALID",
                "Protocol rules do not accept a second limit override; create a new "
                "protocol version.",
                field="limit_override",
            )
        return _protocol_binding(session, organization_id, protocol_version_id, protocol_metric_key)
    return _library_binding(session, organization_id, limit_entry_id, override)  # type: ignore[arg-type]


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DvhLimitAdapterError(
            "DVH_LIMIT_DEFINITION_INVALID",
            "The selected limit contains a non-numeric value.",
            field=field,
        )
    number = float(value)
    if not math.isfinite(number):
        raise DvhLimitAdapterError(
            "DVH_LIMIT_DEFINITION_INVALID",
            "The selected limit contains a non-finite value.",
            field=field,
        )
    return number


def _metric_actual(
    result: Mapping[str, object], effective: Mapping[str, object]
) -> tuple[str, float, str]:
    metrics = result.get("metrics")
    if not isinstance(metrics, Mapping):
        raise DvhLimitAdapterError(
            "DVH_LIMIT_RESULT_INVALID",
            "The DVH result has no metric object.",
            field="result.metrics",
        )
    raw_metric = effective.get("metric_key")
    metric = str(raw_metric).strip().upper() if raw_metric is not None else ""
    if metric in {"DMIN", "DMEAN", "DMAX"}:
        field = {"DMIN": "Dmin_gy", "DMEAN": "Dmean_gy", "DMAX": "Dmax_gy"}[metric]
        return metric, _number(metrics.get(field), f"result.metrics.{field}"), "Gy"
    percent_match = _NUMBER_RE.fullmatch(metric)
    if percent_match:
        value = float(percent_match.group("percent"))
        key = f"D{value:g}_gy"
        values = metrics.get("Dx_gy")
        if not isinstance(values, Mapping) or key not in values:
            raise DvhLimitAdapterError(
                "DVH_LIMIT_METRIC_NOT_COMPUTED",
                f"The DVH request did not compute {metric}; include {value:g} in dx_percentages.",
                field="dx_percentages",
            )
        return metric, _number(values[key], f"result.metrics.Dx_gy.{key}"), "Gy"
    volume_match = _VOLUME_RE.fullmatch(metric)
    if volume_match:
        threshold = float(volume_match.group("dose"))
        parameter = _number(effective.get("metric_parameter"), "metric_parameter")
        if not math.isclose(threshold, parameter, rel_tol=0, abs_tol=1e-9):
            raise DvhLimitAdapterError(
                "DVH_LIMIT_DEFINITION_INVALID",
                "Vx metric_parameter must match the dose threshold encoded in metric_key.",
                field="metric_parameter",
            )
        key = f"V{threshold:g}_gy"
        unit = str(effective.get("unit", ""))
        values = metrics.get("Vx_percent" if unit == "%" else "Vx_cc")
        if not isinstance(values, Mapping) or key not in values:
            raise DvhLimitAdapterError(
                "DVH_LIMIT_METRIC_NOT_COMPUTED",
                f"The DVH request did not compute {metric}; include {threshold:g} in vx_doses_gy.",
                field="vx_doses_gy",
            )
        actual_unit = "%" if unit == "%" else "cc"
        return metric, _number(values[key], f"result.metrics.Vx_{actual_unit}.{key}"), actual_unit
    if metric.startswith("D") and metric.endswith("CC"):
        raise DvhLimitAdapterError(
            "DVH_LIMIT_METRIC_UNSUPPORTED",
            "Dxcc limits require a Dxcc calculation profile that is not enabled in "
            "this P17 engine.",
            field="metric_key",
        )
    raise DvhLimitAdapterError(
        "DVH_LIMIT_METRIC_UNSUPPORTED",
        "The selected limit metric is not supported by the physical-dose DVH engine.",
        field="metric_key",
    )


def evaluate_dvh_limit(
    result: Mapping[str, object], binding: DvhLimitBinding
) -> dict[str, object]:
    """Evaluate one explicit rule and return actual/limit/margin semantics."""

    metric, actual, actual_unit = _metric_actual(result, binding.effective_values)
    effective = binding.effective_values
    unit = str(effective.get("unit", ""))
    if unit != actual_unit:
        raise DvhLimitAdapterError(
            "DVH_LIMIT_UNIT_MISMATCH",
            f"The selected limit uses {unit or 'no unit'}, but {metric} is calculated "
            f"in {actual_unit}.",
            field="unit",
        )
    operator = str(effective.get("operator", "")).upper()
    if operator == "MAX":
        limit = _number(effective.get("limit_value"), "limit_value")
        margin = limit - actual
        limit_payload: dict[str, object] = {"value": limit}
        compliant = margin >= -1e-9
        margin_definition = "limit_value - actual; positive means below the maximum"
    elif operator == "MIN":
        limit = _number(effective.get("limit_value"), "limit_value")
        margin = actual - limit
        limit_payload = {"value": limit}
        compliant = margin >= -1e-9
        margin_definition = "actual - limit_value; positive means above the minimum"
    elif operator == "RANGE":
        lower = _number(effective.get("lower_limit"), "lower_limit")
        upper = _number(effective.get("upper_limit"), "upper_limit")
        if lower > upper:
            raise DvhLimitAdapterError(
                "DVH_LIMIT_DEFINITION_INVALID",
                "lower_limit cannot exceed upper_limit.",
                field="lower_limit",
            )
        margin = min(actual - lower, upper - actual)
        limit_payload = {"lower": lower, "upper": upper}
        compliant = margin >= -1e-9
        margin_definition = "minimum distance to either range boundary; positive means inside range"
    elif operator == "TARGET":
        target = _number(effective.get("limit_value"), "limit_value")
        margin = -abs(actual - target)
        limit_payload = {"value": target}
        compliant = math.isclose(actual, target, rel_tol=0, abs_tol=1e-9)
        margin_definition = "negative absolute distance from target; exact target is required"
    else:
        raise DvhLimitAdapterError(
            "DVH_LIMIT_DEFINITION_INVALID",
            "The selected limit operator is not supported.",
            field="operator",
        )
    rule_status = "PASS" if compliant else "FAIL"
    display_status = "REVIEW_REQUIRED" if binding.warnings else rule_status
    return {
        "schema_version": "visual-dose-dvh.limit-evaluation.v1",
        "source_type": binding.snapshot["source_type"],
        "source_id": binding.snapshot["source_id"],
        "metric_key": metric,
        "actual": actual,
        "actual_unit": actual_unit,
        "operator": operator,
        "limit": limit_payload,
        "limit_unit": unit,
        "margin": margin,
        "margin_unit": actual_unit,
        "margin_definition": margin_definition,
        "rule_status": rule_status,
        "status": display_status,
        "explicit_selection": True,
        "auto_applied": False,
        "warnings": binding.warnings,
    }
