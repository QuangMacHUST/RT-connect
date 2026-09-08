# FastAPI dependency defaults are intentional for route injection.
# ruff: noqa: B008

"""P11 QA protocol library.

Protocol versions are the boundary between editable working material and a
reproducible clinical QA run.  A DRAFT can be edited, while ACTIVE and
ARCHIVED versions are immutable.  A new version or a clone is required for a
change; old runs continue to resolve the version they used.
"""

from __future__ import annotations

import re
from datetime import datetime
from math import isfinite
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.models import (
    AuditEvent,
    QAProtocolRule,
    QAProtocolVersion,
    UserIdentity,
)
from rt_connect_api.db.session import get_session
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.session_context import SessionContext, resolve_session_context

router = APIRouter(prefix="/organizations/{organization_id}/qa-protocols", tags=["qa-protocols"])

ProtocolStatus = Literal["DRAFT", "ACTIVE", "ARCHIVED"]
ProtocolSourceType = Literal["USER_DEFINED", "REFERENCE", "INTERNAL", "SITE_APPROVED"]

_PROTOCOL_KEY_RE = re.compile(r"^[A-Z0-9][A-Z0-9_.-]{0,119}$")
_RULE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,119}$")
_RULE_TYPES = {
    "RANGE",
    "MAX",
    "MIN",
    "ABSOLUTE_DEVIATION",
    "PERCENT_DEVIATION",
    "NA",
}
_SOURCE_TYPES = {"USER_DEFINED", "REFERENCE", "INTERNAL", "SITE_APPROVED"}
_APPLICABILITY_KEYS = {
    "site_ids",
    "machine_ids",
    "qa_cycles",
    "qa_types",
    "energies",
    "beam_qualities",
    "techniques",
    "detectors",
    "phantoms",
}


class ProtocolRuleInput(BaseModel):
    metric_key: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=240)
    unit: str = Field(min_length=1, max_length=40)
    rule_type: str = Field(min_length=1, max_length=40)
    target_value: float | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    tolerance: float | None = None
    action_level: float | None = None
    required: bool = True
    sort_order: int = Field(default=0, ge=0)
    note: str | None = Field(default=None, max_length=1000)
    reference: str | None = Field(default=None, max_length=1000)


class ProtocolDefinitionFields(BaseModel):
    protocol_key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    qa_type: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=4000)
    effective_note: str | None = Field(default=None, max_length=4000)
    applicability: dict[str, object] = Field(default_factory=dict)
    source_type: ProtocolSourceType = "USER_DEFINED"
    source_reference: str | None = Field(default=None, max_length=1000)
    rules: list[ProtocolRuleInput] = Field(min_length=1, max_length=500)


class ProtocolCreateRequest(ProtocolDefinitionFields):
    activate: bool = False


class ProtocolPatchRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    protocol_key: str | None = Field(default=None, min_length=1, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=240)
    qa_type: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=4000)
    effective_note: str | None = Field(default=None, max_length=4000)
    applicability: dict[str, object] | None = None
    source_type: ProtocolSourceType | None = None
    source_reference: str | None = Field(default=None, max_length=1000)
    rules: list[ProtocolRuleInput] | None = Field(default=None, min_length=1, max_length=500)


class ProtocolCloneRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=240)
    protocol_key: str | None = Field(default=None, min_length=1, max_length=120)
    activate: bool = False


class ProtocolTransitionRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class ProtocolValidationRequest(ProtocolDefinitionFields):
    pass


class ProtocolRuleResponse(BaseModel):
    id: UUID
    metric_key: str
    display_name: str
    unit: str
    rule_type: str
    target_value: float | None
    lower_limit: float | None
    upper_limit: float | None
    tolerance: float | None
    action_level: float | None
    required: bool
    sort_order: int
    note: str | None
    reference: str | None


class ProtocolResponse(BaseModel):
    id: UUID
    organization_id: UUID
    protocol_key: str
    name: str
    qa_type: str
    version_number: int
    status: ProtocolStatus
    revision: int
    description: str | None
    effective_note: str | None
    applicability: dict[str, object]
    source_type: str
    source_reference: str | None
    source_protocol_version_id: UUID | None
    created_by_user_identity_id: UUID | None
    created_at: datetime
    updated_at: datetime
    rules: list[ProtocolRuleResponse]


class ProtocolCollectionResponse(BaseModel):
    items: list[ProtocolResponse]
    total: int
    offset: int
    limit: int
    include_archived: bool


class ProtocolValidationIssue(BaseModel):
    code: str
    field: str | None = None
    message: str


class ProtocolValidationResponse(BaseModel):
    valid: bool
    errors: list[ProtocolValidationIssue]
    warnings: list[ProtocolValidationIssue]


class ProtocolDiffResponse(BaseModel):
    field: str
    left: object | None
    right: object | None


class ProtocolCompareResponse(BaseModel):
    left: ProtocolResponse
    right: ProtocolResponse
    same_family: bool
    metadata_diffs: list[ProtocolDiffResponse]
    rule_diffs: list[ProtocolDiffResponse]


def _context_for_organization(
    organization_id: UUID, identity: AuthenticatedIdentity, session: Session
) -> SessionContext:
    context = resolve_session_context(session, identity)
    if context.organization_id != organization_id:
        raise DomainError(
            "ORGANIZATION_SCOPE_MISMATCH",
            "The requested organization is outside the authenticated membership scope.",
            403,
        )
    return context


def _actor_id(session: Session, context: SessionContext) -> UUID | None:
    return session.scalar(
        select(UserIdentity.id).where(UserIdentity.supabase_user_id == context.subject)
    )


def _audit(
    session: Session,
    context: SessionContext,
    event_type: str,
    entity_id: UUID,
    payload: dict[str, object],
) -> None:
    session.add(
        AuditEvent(
            organization_id=context.organization_id,
            actor_user_identity_id=_actor_id(session, context),
            event_type=event_type,
            entity_type="QA_PROTOCOL_VERSION",
            entity_id=entity_id,
            payload=payload,
        )
    )


def _commit_or_raise(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError(
            "PROTOCOL_VERSION_CONFLICT",
            "The protocol version conflicts with a newer version or existing rule key.",
            409,
        ) from exc


def _protocol_rules(
    session: Session, protocol_id: UUID, organization_id: UUID
) -> list[QAProtocolRule]:
    return list(
        session.scalars(
            select(QAProtocolRule)
            .where(
                QAProtocolRule.protocol_version_id == protocol_id,
                QAProtocolRule.organization_id == organization_id,
            )
            .order_by(QAProtocolRule.sort_order, QAProtocolRule.metric_key)
        )
    )


def _rule_response(rule: QAProtocolRule) -> ProtocolRuleResponse:
    return ProtocolRuleResponse(
        id=rule.id,
        metric_key=rule.metric_key,
        display_name=rule.display_name,
        unit=rule.unit,
        rule_type=rule.rule_type,
        target_value=rule.target_value,
        lower_limit=rule.lower_limit,
        upper_limit=rule.upper_limit,
        tolerance=rule.tolerance,
        action_level=rule.action_level,
        required=rule.required,
        sort_order=rule.sort_order,
        note=rule.note,
        reference=rule.reference,
    )


def _protocol_response(
    protocol: QAProtocolVersion, rules: list[QAProtocolRule]
) -> ProtocolResponse:
    return ProtocolResponse(
        id=protocol.id,
        organization_id=protocol.organization_id,
        protocol_key=protocol.protocol_key,
        name=protocol.name,
        qa_type=protocol.qa_type,
        version_number=protocol.version_number,
        status=protocol.status,  # type: ignore[arg-type]
        revision=protocol.revision,
        description=protocol.description,
        effective_note=protocol.effective_note,
        applicability=protocol.applicability,
        source_type=protocol.source_type,
        source_reference=protocol.source_reference,
        source_protocol_version_id=protocol.source_protocol_version_id,
        created_by_user_identity_id=protocol.created_by_user_identity_id,
        created_at=protocol.created_at,
        updated_at=protocol.updated_at,
        rules=[_rule_response(rule) for rule in rules],
    )


def _issue(code: str, field: str | None, message: str) -> ProtocolValidationIssue:
    return ProtocolValidationIssue(code=code, field=field, message=message)


def _finite_rule_number(
    value: float | None, field: str, errors: list[ProtocolValidationIssue]
) -> None:
    if value is not None and not isfinite(value):
        errors.append(_issue("PROTOCOL_RULE_INVALID", field, "Numeric values must be finite."))


def _normalise_applicability(
    value: dict[str, object], errors: list[ProtocolValidationIssue]
) -> dict[str, object]:
    normalised: dict[str, object] = {}
    for key, raw_values in value.items():
        if key not in _APPLICABILITY_KEYS:
            errors.append(
                _issue(
                    "PROTOCOL_APPLICABILITY_INVALID",
                    f"applicability.{key}",
                    "Use a published applicability dimension.",
                )
            )
            continue
        if not isinstance(raw_values, list) or not all(
            isinstance(item, str) and item.strip() for item in raw_values
        ):
            errors.append(
                _issue(
                    "PROTOCOL_APPLICABILITY_INVALID",
                    f"applicability.{key}",
                    "Each applicability dimension must be a non-empty string list.",
                )
            )
            continue
        normalised[key] = sorted({item.strip() for item in raw_values})
    return normalised


def _validate_rule(
    rule: ProtocolRuleInput, index: int, seen_keys: set[str]
) -> tuple[dict[str, object], list[ProtocolValidationIssue]]:
    errors: list[ProtocolValidationIssue] = []
    prefix = f"rules.{index}"
    metric_key = rule.metric_key.strip().lower()
    if not _RULE_KEY_RE.fullmatch(metric_key):
        errors.append(
            _issue(
                "PROTOCOL_RULE_INVALID",
                f"{prefix}.metric_key",
                "Metric key must use lowercase letters, numbers, dot, dash or underscore.",
            )
        )
    if metric_key in seen_keys:
        errors.append(
            _issue(
                "PROTOCOL_VERSION_CONFLICT",
                f"{prefix}.metric_key",
                "Metric key is duplicated in this protocol version.",
            )
        )
    seen_keys.add(metric_key)
    display_name = rule.display_name.strip()
    unit = rule.unit.strip()
    rule_type = rule.rule_type.strip().upper()
    if not display_name:
        errors.append(
            _issue("PROTOCOL_RULE_INVALID", f"{prefix}.display_name", "Display name is required.")
        )
    if not unit:
        errors.append(_issue("PROTOCOL_RULE_INVALID", f"{prefix}.unit", "Unit is required."))
    if rule_type not in _RULE_TYPES:
        errors.append(
            _issue("PROTOCOL_RULE_INVALID", f"{prefix}.rule_type", "Rule type is not supported.")
        )

    numeric_fields = {
        "target_value": rule.target_value,
        "lower_limit": rule.lower_limit,
        "upper_limit": rule.upper_limit,
        "tolerance": rule.tolerance,
        "action_level": rule.action_level,
    }
    for field, value in numeric_fields.items():
        _finite_rule_number(value, f"{prefix}.{field}", errors)
        if (
            value is not None
            and isfinite(value)
            and field in {"tolerance", "action_level"}
            and value < 0
        ):
            errors.append(
                _issue(
                    "PROTOCOL_RULE_INVALID",
                    f"{prefix}.{field}",
                    "Tolerance and action level cannot be negative.",
                )
            )

    if rule_type == "RANGE":
        if rule.lower_limit is None or rule.upper_limit is None:
            errors.append(
                _issue("PROTOCOL_RULE_INVALID", prefix, "RANGE requires lower and upper limits.")
            )
        elif rule.lower_limit > rule.upper_limit:
            errors.append(
                _issue("PROTOCOL_RULE_INVALID", prefix, "Lower limit cannot exceed upper limit.")
            )
    elif rule_type == "MAX" and rule.upper_limit is None and rule.tolerance is None:
        errors.append(
            _issue("PROTOCOL_RULE_INVALID", prefix, "MAX requires an upper limit or tolerance.")
        )
    elif rule_type == "MIN" and rule.lower_limit is None and rule.tolerance is None:
        errors.append(
            _issue("PROTOCOL_RULE_INVALID", prefix, "MIN requires a lower limit or tolerance.")
        )
    elif rule_type in {"ABSOLUTE_DEVIATION", "PERCENT_DEVIATION"}:
        if rule.target_value is None or rule.tolerance is None:
            errors.append(
                _issue(
                    "PROTOCOL_RULE_INVALID", prefix, "Deviation rules require target and tolerance."
                )
            )
        if rule_type == "PERCENT_DEVIATION" and rule.target_value == 0:
            errors.append(
                _issue(
                    "PROTOCOL_RULE_INVALID",
                    f"{prefix}.target_value",
                    "Percent deviation target cannot be zero.",
                )
            )
        if (
            rule.action_level is not None
            and rule.tolerance is not None
            and rule.action_level < rule.tolerance
        ):
            errors.append(
                _issue(
                    "PROTOCOL_RULE_INVALID",
                    f"{prefix}.action_level",
                    "Action level must be at least the tolerance for deviation rules.",
                )
            )

    return (
        {
            "metric_key": metric_key,
            "display_name": display_name,
            "unit": unit,
            "rule_type": rule_type,
            "target_value": rule.target_value,
            "lower_limit": rule.lower_limit,
            "upper_limit": rule.upper_limit,
            "tolerance": rule.tolerance,
            "action_level": rule.action_level,
            "required": rule.required,
            "sort_order": rule.sort_order,
            "note": rule.note.strip() if rule.note else None,
            "reference": rule.reference.strip() if rule.reference else None,
        },
        errors,
    )


def _validate_definition(
    definition: ProtocolDefinitionFields,
) -> tuple[dict[str, object], list[ProtocolValidationIssue]]:
    errors: list[ProtocolValidationIssue] = []
    protocol_key = definition.protocol_key.strip().upper()
    if not _PROTOCOL_KEY_RE.fullmatch(protocol_key):
        errors.append(
            _issue(
                "PROTOCOL_RULE_INVALID",
                "protocol_key",
                "Protocol key must use uppercase letters, numbers, dot, dash or underscore.",
            )
        )
    name = definition.name.strip()
    qa_type = definition.qa_type.strip()
    if not name:
        errors.append(_issue("PROTOCOL_RULE_INVALID", "name", "Protocol name is required."))
    if not qa_type:
        errors.append(_issue("PROTOCOL_RULE_INVALID", "qa_type", "QA type is required."))
    source_type = str(definition.source_type).upper()
    if source_type not in _SOURCE_TYPES:
        errors.append(
            _issue("PROTOCOL_RULE_INVALID", "source_type", "Source type is not supported.")
        )
    source_reference = definition.source_reference.strip() if definition.source_reference else None
    if source_type == "REFERENCE" and not source_reference:
        errors.append(
            _issue(
                "REFERENCE_REQUIRED",
                "source_reference",
                "A reference source is required when source type is REFERENCE.",
            )
        )
    applicability = _normalise_applicability(definition.applicability, errors)
    seen_keys: set[str] = set()
    normalised_rules: list[dict[str, object]] = []
    for index, rule in enumerate(definition.rules):
        normalised_rule, rule_errors = _validate_rule(rule, index, seen_keys)
        normalised_rules.append(normalised_rule)
        errors.extend(rule_errors)
    return (
        {
            "protocol_key": protocol_key,
            "name": name,
            "qa_type": qa_type,
            "description": definition.description.strip() if definition.description else None,
            "effective_note": definition.effective_note.strip()
            if definition.effective_note
            else None,
            "applicability": applicability,
            "source_type": source_type,
            "source_reference": source_reference,
            "rules": normalised_rules,
        },
        errors,
    )


def _raise_if_invalid(normalised: dict[str, object], errors: list[ProtocolValidationIssue]) -> None:
    if errors:
        raise DomainError(
            errors[0].code,
            "The protocol definition is invalid.",
            409 if errors[0].code == "PROTOCOL_VERSION_CONFLICT" else 422,
            [{"field": item.field, "message": f"{item.code}: {item.message}"} for item in errors],
        )


def _definition_from_protocol(
    session: Session, protocol: QAProtocolVersion, organization_id: UUID
) -> ProtocolDefinitionFields:
    return ProtocolDefinitionFields(
        protocol_key=protocol.protocol_key,
        name=protocol.name,
        qa_type=protocol.qa_type,
        description=protocol.description,
        effective_note=protocol.effective_note,
        applicability=protocol.applicability,
        source_type=protocol.source_type,  # type: ignore[arg-type]
        source_reference=protocol.source_reference,
        rules=[
            ProtocolRuleInput(
                metric_key=rule.metric_key,
                display_name=rule.display_name,
                unit=rule.unit,
                rule_type=rule.rule_type,
                target_value=rule.target_value,
                lower_limit=rule.lower_limit,
                upper_limit=rule.upper_limit,
                tolerance=rule.tolerance,
                action_level=rule.action_level,
                required=rule.required,
                sort_order=rule.sort_order,
                note=rule.note,
                reference=rule.reference,
            )
            for rule in _protocol_rules(session, protocol.id, organization_id)
        ],
    )


def _next_version_number(session: Session, organization_id: UUID, protocol_key: str) -> int:
    current = session.scalar(
        select(func.max(QAProtocolVersion.version_number)).where(
            QAProtocolVersion.organization_id == organization_id,
            QAProtocolVersion.protocol_key == protocol_key,
        )
    )
    return int(current or 0) + 1


def _protocol_or_404(
    session: Session, organization_id: UUID, protocol_id: UUID
) -> QAProtocolVersion:
    protocol = session.scalar(
        select(QAProtocolVersion).where(
            QAProtocolVersion.id == protocol_id,
            QAProtocolVersion.organization_id == organization_id,
        )
    )
    if protocol is None:
        raise DomainError("PROTOCOL_NOT_FOUND", "The QA protocol version was not found.", 404)
    return protocol


def _check_revision(protocol: QAProtocolVersion, expected_revision: int) -> None:
    if protocol.revision != expected_revision:
        raise DomainError(
            "PROTOCOL_VERSION_CONFLICT",
            "The protocol changed; reload the latest version before continuing.",
            409,
        )


def _persist_rules(
    session: Session, protocol: QAProtocolVersion, normalised_rules: list[dict[str, object]]
) -> None:
    session.execute(
        delete(QAProtocolRule).where(
            QAProtocolRule.protocol_version_id == protocol.id,
            QAProtocolRule.organization_id == protocol.organization_id,
        )
    )
    session.flush()
    for rule in normalised_rules:
        session.add(
            QAProtocolRule(
                organization_id=protocol.organization_id,
                protocol_version_id=protocol.id,
                **rule,
            )
        )


def _new_protocol(
    session: Session,
    context: SessionContext,
    normalised: dict[str, object],
    *,
    status_value: ProtocolStatus,
    source_protocol_version_id: UUID | None = None,
    actor_id: UUID | None,
) -> QAProtocolVersion:
    protocol = QAProtocolVersion(
        organization_id=context.organization_id,
        protocol_key=str(normalised["protocol_key"]),
        name=str(normalised["name"]),
        qa_type=str(normalised["qa_type"]),
        version_number=_next_version_number(
            session, context.organization_id, str(normalised["protocol_key"])
        ),
        status=status_value,
        description=normalised["description"],
        effective_note=normalised["effective_note"],
        applicability=normalised["applicability"],
        source_type=str(normalised["source_type"]),
        source_reference=normalised["source_reference"],
        source_protocol_version_id=source_protocol_version_id,
        revision=1,
        created_by_user_identity_id=actor_id,
    )
    session.add(protocol)
    session.flush()
    _persist_rules(
        session, protocol, normalised["rules"] if isinstance(normalised["rules"], list) else []
    )
    return protocol


@router.post("/validate", response_model=ProtocolValidationResponse)
def validate_protocol(
    payload: ProtocolValidationRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolValidationResponse:
    _context_for_organization(organization_id, identity, session)
    _, errors = _validate_definition(payload)
    return ProtocolValidationResponse(valid=not errors, errors=errors, warnings=[])


@router.get("", response_model=ProtocolCollectionResponse)
def list_protocols(
    organization_id: UUID,
    q: str | None = Query(default=None, max_length=120),
    protocol_status: ProtocolStatus | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolCollectionResponse:
    _context_for_organization(organization_id, identity, session)
    conditions = [QAProtocolVersion.organization_id == organization_id]
    if not include_archived:
        conditions.append(QAProtocolVersion.status != "ARCHIVED")
    if protocol_status:
        conditions.append(QAProtocolVersion.status == protocol_status)
    if q and q.strip():
        search = f"%{q.strip()}%"
        conditions.append(
            QAProtocolVersion.protocol_key.ilike(search)
            | QAProtocolVersion.name.ilike(search)
            | QAProtocolVersion.qa_type.ilike(search)
        )
    total = int(session.scalar(select(func.count(QAProtocolVersion.id)).where(*conditions)) or 0)
    protocols = list(
        session.scalars(
            select(QAProtocolVersion)
            .where(*conditions)
            .order_by(
                QAProtocolVersion.protocol_key,
                QAProtocolVersion.version_number.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
    )
    return ProtocolCollectionResponse(
        items=[
            _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))
            for protocol in protocols
        ],
        total=total,
        offset=offset,
        limit=limit,
        include_archived=include_archived,
    )


@router.post("", response_model=ProtocolResponse, status_code=status.HTTP_201_CREATED)
def create_protocol(
    payload: ProtocolCreateRequest,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolResponse:
    context = _context_for_organization(organization_id, identity, session)
    normalised, errors = _validate_definition(payload)
    _raise_if_invalid(normalised, errors)
    protocol = _new_protocol(
        session,
        context,
        normalised,
        status_value="ACTIVE" if payload.activate else "DRAFT",
        actor_id=_actor_id(session, context),
    )
    _audit(
        session,
        context,
        "QA_PROTOCOL_CREATED",
        protocol.id,
        {
            "protocol_key": protocol.protocol_key,
            "version_number": protocol.version_number,
            "status": protocol.status,
        },
    )
    _commit_or_raise(session)
    session.refresh(protocol)
    return _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))


@router.get("/{protocol_id}", response_model=ProtocolResponse)
def get_protocol(
    protocol_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolResponse:
    _context_for_organization(organization_id, identity, session)
    protocol = _protocol_or_404(session, organization_id, protocol_id)
    return _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))


@router.patch("/{protocol_id}", response_model=ProtocolResponse)
def update_protocol(
    payload: ProtocolPatchRequest,
    protocol_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolResponse:
    context = _context_for_organization(organization_id, identity, session)
    protocol = _protocol_or_404(session, organization_id, protocol_id)
    _check_revision(protocol, payload.expected_revision)
    if protocol.status != "DRAFT":
        raise DomainError(
            "PROTOCOL_VERSION_IMMUTABLE",
            "Only a DRAFT protocol version can be edited; clone it to make a new version.",
            409,
        )
    fields = payload.model_fields_set
    protocol_key = (
        payload.protocol_key if payload.protocol_key is not None else protocol.protocol_key
    )
    name = payload.name if payload.name is not None else protocol.name
    qa_type = payload.qa_type if payload.qa_type is not None else protocol.qa_type
    definition = ProtocolDefinitionFields(
        protocol_key=protocol_key,
        name=name,
        qa_type=qa_type,
        description=payload.description if "description" in fields else protocol.description,
        effective_note=payload.effective_note
        if "effective_note" in fields
        else protocol.effective_note,
        applicability=payload.applicability
        if "applicability" in fields and payload.applicability is not None
        else protocol.applicability,
        source_type=payload.source_type
        if "source_type" in fields and payload.source_type is not None
        else protocol.source_type,  # type: ignore[arg-type]
        source_reference=payload.source_reference
        if "source_reference" in fields
        else protocol.source_reference,
        rules=payload.rules
        if "rules" in fields and payload.rules is not None
        else [
            ProtocolRuleInput.model_validate(rule)
            for rule in _protocol_rules(session, protocol.id, organization_id)
        ],
    )
    normalised, errors = _validate_definition(definition)
    _raise_if_invalid(normalised, errors)
    protocol.protocol_key = str(normalised["protocol_key"])
    protocol.name = str(normalised["name"])
    protocol.qa_type = str(normalised["qa_type"])
    protocol.description = normalised["description"]  # type: ignore[assignment]
    protocol.effective_note = normalised["effective_note"]  # type: ignore[assignment]
    protocol.applicability = normalised["applicability"]  # type: ignore[assignment]
    protocol.source_type = str(normalised["source_type"])
    protocol.source_reference = normalised["source_reference"]  # type: ignore[assignment]
    protocol.revision += 1
    _persist_rules(
        session, protocol, normalised["rules"] if isinstance(normalised["rules"], list) else []
    )
    _audit(
        session,
        context,
        "QA_PROTOCOL_DRAFT_UPDATED",
        protocol.id,
        {"revision": protocol.revision, "fields": sorted(fields)},
    )
    _commit_or_raise(session)
    session.refresh(protocol)
    return _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))


@router.post(
    "/{protocol_id}/clone", response_model=ProtocolResponse, status_code=status.HTTP_201_CREATED
)
def clone_protocol(
    payload: ProtocolCloneRequest,
    protocol_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolResponse:
    context = _context_for_organization(organization_id, identity, session)
    source = _protocol_or_404(session, organization_id, protocol_id)
    definition = _definition_from_protocol(session, source, organization_id)
    if payload.name is not None:
        definition.name = payload.name
    if payload.protocol_key is not None:
        definition.protocol_key = payload.protocol_key
    normalised, errors = _validate_definition(definition)
    _raise_if_invalid(normalised, errors)
    cloned = _new_protocol(
        session,
        context,
        normalised,
        status_value="ACTIVE" if payload.activate else "DRAFT",
        source_protocol_version_id=source.id,
        actor_id=_actor_id(session, context),
    )
    _audit(
        session,
        context,
        "QA_PROTOCOL_CLONED",
        cloned.id,
        {
            "source_protocol_version_id": str(source.id),
            "protocol_key": cloned.protocol_key,
            "version_number": cloned.version_number,
        },
    )
    _commit_or_raise(session)
    session.refresh(cloned)
    return _protocol_response(cloned, _protocol_rules(session, cloned.id, organization_id))


@router.post("/{protocol_id}/activate", response_model=ProtocolResponse)
def activate_protocol(
    payload: ProtocolTransitionRequest,
    protocol_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolResponse:
    context = _context_for_organization(organization_id, identity, session)
    protocol = _protocol_or_404(session, organization_id, protocol_id)
    _check_revision(protocol, payload.expected_revision)
    if protocol.status == "ARCHIVED":
        raise DomainError(
            "PROTOCOL_NOT_AVAILABLE", "An archived protocol cannot be activated.", 409
        )
    if protocol.status == "ACTIVE":
        return _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))
    definition = _definition_from_protocol(session, protocol, organization_id)
    normalised, errors = _validate_definition(definition)
    _raise_if_invalid(normalised, errors)
    protocol.status = "ACTIVE"
    protocol.revision += 1
    _audit(session, context, "QA_PROTOCOL_ACTIVATED", protocol.id, {"revision": protocol.revision})
    _commit_or_raise(session)
    session.refresh(protocol)
    return _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))


@router.post("/{protocol_id}/archive", response_model=ProtocolResponse)
def archive_protocol(
    payload: ProtocolTransitionRequest,
    protocol_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolResponse:
    context = _context_for_organization(organization_id, identity, session)
    protocol = _protocol_or_404(session, organization_id, protocol_id)
    _check_revision(protocol, payload.expected_revision)
    if protocol.status != "ARCHIVED":
        protocol.status = "ARCHIVED"
        protocol.revision += 1
        _audit(
            session, context, "QA_PROTOCOL_ARCHIVED", protocol.id, {"revision": protocol.revision}
        )
        _commit_or_raise(session)
        session.refresh(protocol)
    return _protocol_response(protocol, _protocol_rules(session, protocol.id, organization_id))


@router.get("/{protocol_id}/compare", response_model=ProtocolCompareResponse)
def compare_protocols(
    protocol_id: UUID,
    other_id: UUID,
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),
    session: Session = Depends(get_session),
) -> ProtocolCompareResponse:
    _context_for_organization(organization_id, identity, session)
    left = _protocol_or_404(session, organization_id, protocol_id)
    right = _protocol_or_404(session, organization_id, other_id)
    left_rules = _protocol_rules(session, left.id, organization_id)
    right_rules = _protocol_rules(session, right.id, organization_id)
    left_response = _protocol_response(left, left_rules)
    right_response = _protocol_response(right, right_rules)
    metadata_fields = (
        "protocol_key",
        "name",
        "qa_type",
        "version_number",
        "status",
        "revision",
        "description",
        "effective_note",
        "applicability",
        "source_type",
        "source_reference",
        "source_protocol_version_id",
    )
    metadata_diffs = [
        ProtocolDiffResponse(
            field=field, left=getattr(left_response, field), right=getattr(right_response, field)
        )
        for field in metadata_fields
        if getattr(left_response, field) != getattr(right_response, field)
    ]
    left_by_key = {rule.metric_key: rule for rule in left_rules}
    right_by_key = {rule.metric_key: rule for rule in right_rules}
    rule_diffs: list[ProtocolDiffResponse] = []
    for metric_key in sorted(set(left_by_key) | set(right_by_key)):
        left_rule = left_by_key.get(metric_key)
        right_rule = right_by_key.get(metric_key)
        left_value = left_rule and _rule_response(left_rule).model_dump(mode="json")
        right_value = right_rule and _rule_response(right_rule).model_dump(mode="json")
        if left_value != right_value:
            rule_diffs.append(
                ProtocolDiffResponse(field=metric_key, left=left_value, right=right_value)
            )
    return ProtocolCompareResponse(
        left=left_response,
        right=right_response,
        same_family=left.protocol_key == right.protocol_key,
        metadata_diffs=metadata_diffs,
        rule_diffs=rule_diffs,
    )
