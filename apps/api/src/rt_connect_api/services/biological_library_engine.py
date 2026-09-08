"""Pure validation and matching rules for the P16 biological library.

The library deliberately stores structured clinical knowledge as reference
material.  It is not a prescription engine and it never decides which of two
conflicting references is clinically preferred.  Keeping these rules outside
the HTTP layer makes validate-only, import preview, and the API use the same
contract.
"""

from __future__ import annotations

import hashlib
import json
import re
from math import isfinite

LIBRARY_SCHEMA_VERSION = "biological-library-entry.v1"
LIBRARY_USE_SCHEMA_VERSION = "biological-library-use.v1"

ENTRY_TYPES = frozenset({"DOSE_LIMIT", "TREATMENT_PROTOCOL", "KNOWLEDGE", "ALPHA_BETA"})
SOURCE_TYPES = frozenset({"USER_DEFINED", "REFERENCE", "INTERNAL", "SITE_APPROVED"})
REFERENCE_STATUSES = frozenset({"UNVERIFIED", "AVAILABLE", "UNAVAILABLE"})
OPERATORS = frozenset({"MAX", "MIN", "RANGE", "TARGET"})
DOSE_UNITS = frozenset({"Gy", "Gy2", "Gy3", "Gy10", "EQD2 Gy", "%", "cc", "cm3"})
TEXT_APPLICABILITY_KEYS = frozenset(
    {
        "diseases",
        "subtypes",
        "anatomy_sites",
        "intents",
        "techniques",
        "tissue_or_oars",
        "metric_keys",
        "units",
    }
)

_ENTRY_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_.-]{0,119}$")
_METRIC_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_.-]{0,79}$")
_DANGEROUS_CONTENT_RE = re.compile(
    r"(?is)<\s*(?:script|iframe|object|embed|style)|javascript\s*:|on[a-z]+\s*=|data:text/html"
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:$|T)")


class BiologicalLibraryEngineError(Exception):
    """A deterministic P16 validation error with field-level details."""

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
        self.details = details or []
        super().__init__(message)


def _issue(code: str, field: str | None, message: str) -> dict[str, object]:
    return {"code": code, "field": field, "message": message}


def request_fingerprint(value: dict[str, object]) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _safe_json(value: object, field: str) -> list[dict[str, object]]:
    errors: list[dict[str, object]] = []
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return [_issue("KNOWLEDGE_CONTENT_INVALID", field, "Value must be finite JSON data.")]
    if _DANGEROUS_CONTENT_RE.search(encoded):
        errors.append(
            _issue(
                "KNOWLEDGE_CONTENT_INVALID",
                field,
                "Markup or URL scheme could execute active content; use plain text "
                "or safe markdown.",
            )
        )
    return errors


def _text(value: object, field: str, errors: list[dict[str, object]]) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(_issue("KNOWLEDGE_CONTENT_INVALID", field, "Value must be text."))
        return None
    trimmed = value.strip()
    return trimmed or None


def _finite_number(
    value: object, field: str, errors: list[dict[str, object]], *, positive: bool = False
) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        errors.append(_issue("KNOWLEDGE_CONTENT_INVALID", field, "Numeric value must be finite."))
        return None
    result = float(value)
    if positive and result <= 0:
        errors.append(
            _issue("KNOWLEDGE_CONTENT_INVALID", field, "Value must be greater than zero.")
        )
    return result


def _normalise_applicability(value: object, errors: list[dict[str, object]]) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        errors.append(
            _issue(
                "KNOWLEDGE_APPLICABILITY_INVALID",
                "applicability",
                "Applicability must be an object.",
            )
        )
        return {}
    result: dict[str, object] = {}
    for raw_key, raw_values in value.items():
        key = str(raw_key).strip()
        if key not in TEXT_APPLICABILITY_KEYS and key != "fractions":
            errors.append(
                _issue(
                    "KNOWLEDGE_APPLICABILITY_INVALID",
                    f"applicability.{key}",
                    "Use a supported applicability dimension.",
                )
            )
            continue
        if not isinstance(raw_values, list) or not raw_values:
            errors.append(
                _issue(
                    "KNOWLEDGE_APPLICABILITY_INVALID",
                    f"applicability.{key}",
                    "Applicability values must be a non-empty list.",
                )
            )
            continue
        if key == "fractions":
            if not all(
                isinstance(item, int) and not isinstance(item, bool) and item > 0
                for item in raw_values
            ):
                errors.append(
                    _issue(
                        "KNOWLEDGE_APPLICABILITY_INVALID",
                        f"applicability.{key}",
                        "Fractions must be positive integers.",
                    )
                )
                continue
            result[key] = sorted({int(item) for item in raw_values})
            continue
        if not all(isinstance(item, str) and item.strip() for item in raw_values):
            errors.append(
                _issue(
                    "KNOWLEDGE_APPLICABILITY_INVALID",
                    f"applicability.{key}",
                    "Each value must be a non-empty string.",
                )
            )
            continue
        result[key] = sorted({str(item).strip() for item in raw_values}, key=str.casefold)
    return result


def _context_list(payload: dict[str, object], key: str, applicability_key: str) -> list[str]:
    value = payload.get(key)
    values: list[str] = []
    if isinstance(value, str) and value.strip():
        values.append(value.strip())
    extra = payload.get("applicability")
    if isinstance(extra, dict):
        raw = extra.get(applicability_key)
        if isinstance(raw, list):
            values.extend(item.strip() for item in raw if isinstance(item, str) and item.strip())
    return sorted(set(values), key=str.casefold)


def validate_library_entry(
    payload: dict[str, object],
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    """Return a canonical entry, errors, and non-blocking source warnings."""

    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    raw_key = payload.get("entry_key")
    entry_key = str(raw_key).strip().upper() if isinstance(raw_key, str) else ""
    if not _ENTRY_KEY_RE.fullmatch(entry_key):
        errors.append(
            _issue(
                "KNOWLEDGE_CONTENT_INVALID",
                "entry_key",
                "Entry key must start with an uppercase letter and use A-Z, 0-9, dot, "
                "dash or underscore.",
            )
        )

    entry_type = str(payload.get("entry_type", "")).strip().upper()
    if entry_type not in ENTRY_TYPES:
        errors.append(
            _issue("KNOWLEDGE_CONTENT_INVALID", "entry_type", "Entry type is not supported.")
        )

    name = _text(payload.get("name"), "name", errors)
    if not name:
        errors.append(_issue("KNOWLEDGE_CONTENT_INVALID", "name", "Display name is required."))

    description = _text(payload.get("description"), "description", errors)
    effective_note = _text(payload.get("effective_note"), "effective_note", errors)
    source_type = str(payload.get("source_type", "USER_DEFINED")).strip().upper()
    if source_type not in SOURCE_TYPES:
        errors.append(
            _issue("KNOWLEDGE_SOURCE_REQUIRED", "source_type", "Source type is not supported.")
        )
        source_type = "USER_DEFINED"
    source_reference = _text(payload.get("source_reference"), "source_reference", errors)
    if source_type == "REFERENCE" and not source_reference:
        errors.append(
            _issue(
                "KNOWLEDGE_SOURCE_REQUIRED",
                "source_reference",
                "A reference entry requires a citation, DOI, URL or document identifier.",
            )
        )

    reference_status = str(payload.get("reference_status", "UNVERIFIED")).strip().upper()
    if reference_status not in REFERENCE_STATUSES:
        errors.append(
            _issue(
                "REFERENCE_LINK_UNAVAILABLE",
                "reference_status",
                "Reference status must be UNVERIFIED, AVAILABLE or UNAVAILABLE.",
            )
        )
        reference_status = "UNVERIFIED"
    if reference_status == "UNAVAILABLE":
        warnings.append(
            _issue(
                "REFERENCE_LINK_UNAVAILABLE",
                "source_reference",
                "The citation was retained, but its link is marked unavailable; "
                "no content was deleted.",
            )
        )
    elif source_type == "REFERENCE":
        warnings.append(
            _issue(
                "REFERENCE_NOT_VERIFIED",
                "source_reference",
                "The source is recorded as metadata and was not fetched or independently "
                "verified by RT-CONNECT.",
            )
        )

    source_date = _text(payload.get("source_date"), "source_date", errors)
    if source_date and not _DATE_RE.match(source_date):
        errors.append(
            _issue("KNOWLEDGE_CONTENT_INVALID", "source_date", "Use an ISO date or datetime.")
        )
    evidence_level = _text(payload.get("evidence_level"), "evidence_level", errors)
    model_key = _text(payload.get("model_key"), "model_key", errors)
    model_version = _text(payload.get("model_version"), "model_version", errors)

    citation = payload.get("citation", {})
    if not isinstance(citation, dict):
        errors.append(
            _issue("KNOWLEDGE_CONTENT_INVALID", "citation", "Citation must be an object.")
        )
        citation = {}
    errors.extend(_safe_json(citation, "citation"))

    content = payload.get("content", {})
    if not isinstance(content, dict):
        errors.append(_issue("KNOWLEDGE_CONTENT_INVALID", "content", "Content must be an object."))
        content = {}
    errors.extend(_safe_json(content, "content"))

    applicability = _normalise_applicability(payload.get("applicability", {}), errors)
    context_fields = {
        "disease": "diseases",
        "disease_subtype": "subtypes",
        "anatomy_site": "anatomy_sites",
        "treatment_intent": "intents",
        "technique": "techniques",
        "tissue_or_oar": "tissue_or_oars",
    }
    contexts: dict[str, str | None] = {}
    for field, applicability_key in context_fields.items():
        value = _text(payload.get(field), field, errors)
        contexts[field] = value
        if value and applicability_key not in applicability:
            applicability[applicability_key] = [value]

    fractions = payload.get("fractions")
    if fractions is not None and (
        isinstance(fractions, bool) or not isinstance(fractions, int) or fractions <= 0
    ):
        errors.append(
            _issue(
                "KNOWLEDGE_APPLICABILITY_INVALID",
                "fractions",
                "Fractions must be a positive integer.",
            )
        )
        fractions = None
    if isinstance(fractions, int):
        existing_fractions = applicability.get("fractions")
        if isinstance(existing_fractions, list) and fractions not in existing_fractions:
            errors.append(
                _issue(
                    "KNOWLEDGE_APPLICABILITY_INVALID",
                    "fractions",
                    "Fractions must agree with applicability.fractions.",
                )
            )
        applicability.setdefault("fractions", [fractions])

    metric_key = _text(payload.get("metric_key"), "metric_key", errors)
    if metric_key:
        metric_key = metric_key.upper()
        if not _METRIC_KEY_RE.fullmatch(metric_key):
            errors.append(
                _issue("KNOWLEDGE_CONTENT_INVALID", "metric_key", "Metric key format is invalid.")
            )
    raw_operator = payload.get("operator")
    operator = (
        raw_operator.strip().upper()
        if isinstance(raw_operator, str) and raw_operator.strip()
        else None
    )
    if operator and operator not in OPERATORS:
        errors.append(
            _issue("DOSE_LIMIT_UNIT_INVALID", "operator", "Dose-limit operator is not supported.")
        )
        operator = None
    unit = _text(payload.get("unit"), "unit", errors)
    if unit and unit not in DOSE_UNITS:
        errors.append(
            _issue("DOSE_LIMIT_UNIT_INVALID", "unit", "Dose-limit unit is not supported.")
        )
        unit = None

    limit_value = _finite_number(payload.get("limit_value"), "limit_value", errors)
    lower_limit = _finite_number(payload.get("lower_limit"), "lower_limit", errors)
    upper_limit = _finite_number(payload.get("upper_limit"), "upper_limit", errors)
    volume_cc = _finite_number(payload.get("volume_cc"), "volume_cc", errors, positive=True)
    metric_parameter = _finite_number(
        payload.get("metric_parameter"), "metric_parameter", errors, positive=True
    )
    alpha_beta_gy = _finite_number(
        payload.get("alpha_beta_gy"), "alpha_beta_gy", errors, positive=True
    )

    if entry_type == "DOSE_LIMIT":
        if not metric_key:
            errors.append(
                _issue("DOSE_LIMIT_NOT_APPLICABLE", "metric_key", "A dose limit requires a metric.")
            )
        if not unit:
            errors.append(
                _issue("DOSE_LIMIT_UNIT_INVALID", "unit", "A dose limit requires a unit.")
            )
        if not operator:
            errors.append(
                _issue(
                    "DOSE_LIMIT_NOT_APPLICABLE", "operator", "A dose limit requires an operator."
                )
            )
        if (
            metric_key
            and re.match(r"^D(?:MAX|MEAN|\d+(?:\.\d+)?CC)$", metric_key)
            and unit in {"%", "cc", "cm3"}
        ):
            errors.append(
                _issue(
                    "DOSE_LIMIT_UNIT_INVALID",
                    "unit",
                    "Dose metrics require Gy or an explicit biologically equivalent dose unit.",
                )
            )
        if metric_key and metric_key.startswith("V") and unit not in {"%", "cc", "cm3"}:
            errors.append(
                _issue(
                    "DOSE_LIMIT_UNIT_INVALID",
                    "unit",
                    "Vx metrics must report percentage or volume units.",
                )
            )
        if operator == "RANGE":
            if lower_limit is None or upper_limit is None:
                errors.append(
                    _issue(
                        "DOSE_LIMIT_NOT_APPLICABLE",
                        "lower_limit",
                        "RANGE requires lower and upper limits.",
                    )
                )
            elif lower_limit > upper_limit:
                errors.append(
                    _issue(
                        "DOSE_LIMIT_NOT_APPLICABLE",
                        "lower_limit",
                        "Lower limit cannot exceed upper limit.",
                    )
                )
        elif operator in {"MAX", "MIN", "TARGET"} and limit_value is None:
            errors.append(
                _issue(
                    "DOSE_LIMIT_NOT_APPLICABLE",
                    "limit_value",
                    "This operator requires limit_value.",
                )
            )
        if (
            metric_key
            and re.match(r"^D(?:MAX|MEAN|\d+(?:\.\d+)?CC)$", metric_key)
            and metric_key.endswith("CC")
            and volume_cc is None
        ):
            errors.append(
                _issue(
                    "DOSE_LIMIT_NOT_APPLICABLE",
                    "volume_cc",
                    "A Dxcc metric requires a positive volume.",
                )
            )
        if metric_key and metric_key.startswith("V") and metric_parameter is None:
            errors.append(
                _issue(
                    "DOSE_LIMIT_NOT_APPLICABLE",
                    "metric_parameter",
                    "A Vx metric requires its dose or volume parameter.",
                )
            )
    elif entry_type == "ALPHA_BETA":
        if alpha_beta_gy is None:
            alpha_beta_gy = limit_value
        if alpha_beta_gy is None or alpha_beta_gy <= 0:
            errors.append(
                _issue("KNOWLEDGE_CONTENT_INVALID", "alpha_beta_gy", "Alpha/beta must be positive.")
            )
        if unit not in {None, "Gy"}:
            errors.append(_issue("DOSE_LIMIT_UNIT_INVALID", "unit", "Alpha/beta entries use Gy."))
        metric_key = metric_key or "ALPHA_BETA"
        unit = "Gy"

    if entry_type in {"DOSE_LIMIT", "ALPHA_BETA"} and not _context_list(
        {**payload, "applicability": applicability}, "tissue_or_oar", "tissue_or_oars"
    ):
        warnings.append(
            _issue(
                "DOSE_LIMIT_NOT_APPLICABLE",
                "tissue_or_oar",
                "No tissue/OAR context was supplied; the entry must not be auto-applied "
                "to a calculator.",
            )
        )

    normalised: dict[str, object] = {
        "schema_version": LIBRARY_SCHEMA_VERSION,
        "entry_key": entry_key,
        "entry_type": entry_type,
        "name": name or "",
        "description": description,
        "effective_note": effective_note,
        **contexts,
        "fractions": fractions,
        "tissue_or_oar": contexts["tissue_or_oar"],
        "metric_key": metric_key,
        "operator": operator,
        "limit_value": limit_value,
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "unit": unit,
        "volume_cc": volume_cc,
        "metric_parameter": metric_parameter,
        "alpha_beta_gy": alpha_beta_gy,
        "model_key": model_key,
        "model_version": model_version,
        "applicability": applicability,
        "content": content,
        "source_type": source_type,
        "source_reference": source_reference,
        "reference_status": reference_status,
        "source_date": source_date,
        "evidence_level": evidence_level,
        "citation": citation,
    }
    return normalised, errors, warnings


def entry_matches(
    entry: dict[str, object],
    *,
    disease: str | None = None,
    anatomy_site: str | None = None,
    technique: str | None = None,
    tissue_or_oar: str | None = None,
    metric_key: str | None = None,
    fractions: int | None = None,
) -> bool:
    filters = {
        "disease": (disease, "diseases"),
        "anatomy_site": (anatomy_site, "anatomy_sites"),
        "technique": (technique, "techniques"),
        "tissue_or_oar": (tissue_or_oar, "tissue_or_oars"),
        "metric_key": (metric_key, "metric_keys"),
    }
    applicability = entry.get("applicability")
    applicability_dict = applicability if isinstance(applicability, dict) else {}
    for field, (raw_filter, applicability_key) in filters.items():
        if raw_filter is None or not str(raw_filter).strip():
            continue
        wanted = str(raw_filter).strip().casefold()
        direct = entry.get(field)
        values: list[str] = []
        if isinstance(direct, str) and direct.strip():
            values.append(direct)
        raw_values = applicability_dict.get(applicability_key)
        if isinstance(raw_values, list):
            values.extend(item for item in raw_values if isinstance(item, str))
        if not any(value.strip().casefold() == wanted for value in values):
            return False
    if fractions is not None:
        raw_fractions = applicability_dict.get("fractions")
        if not isinstance(raw_fractions, list) or fractions not in raw_fractions:
            return False
    return True


def entry_search_text(entry: dict[str, object]) -> str:
    parts = [
        entry.get("entry_key"),
        entry.get("name"),
        entry.get("description"),
        entry.get("disease"),
        entry.get("disease_subtype"),
        entry.get("anatomy_site"),
        entry.get("treatment_intent"),
        entry.get("technique"),
        entry.get("tissue_or_oar"),
        entry.get("metric_key"),
        entry.get("source_reference"),
    ]
    content = entry.get("content")
    if isinstance(content, dict):
        parts.append(json.dumps(content, ensure_ascii=False, sort_keys=True))
    return " ".join(str(part) for part in parts if part is not None).casefold()


def library_snapshot(entry: dict[str, object]) -> dict[str, object]:
    """Create the immutable payload pinned by a calculator/use action."""

    snapshot = dict(entry)
    snapshot.pop("entry_sha256", None)
    snapshot["schema_version"] = LIBRARY_USE_SCHEMA_VERSION
    snapshot["entry_sha256"] = request_fingerprint(snapshot)
    return snapshot
