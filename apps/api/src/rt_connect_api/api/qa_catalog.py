"""QA test catalogue endpoint for the organization-scoped QA workspace."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from rt_connect_api.core.errors import DomainError
from rt_connect_api.db.session import get_session
from rt_connect_api.qa_catalog import (
    CATALOGUE_VERSION,
    QA_TEST_CATALOG,
    QATestDefinition,
    QATestDefinitionCollection,
)
from rt_connect_api.security.supabase_jwt import AuthenticatedIdentity, require_identity
from rt_connect_api.services.pylinac_registry import registry_summary
from rt_connect_api.services.session_context import resolve_session_context

router = APIRouter(tags=["qa-catalog"])


class PylinacCapabilityStatus(BaseModel):
    """User-safe runtime status for one catalogue capability."""

    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    family: str = Field(min_length=1)
    input_profile: str = Field(min_length=1)
    source_tier: str = Field(min_length=1)
    fixture_status: Literal["OFFICIAL_DEMO", "SYNTHETIC_CONTRACT", "COMMISSIONING_REQUIRED"]
    fixture_reference: str = Field(min_length=1)
    fixture_note: str = Field(min_length=1)
    runtime_available: bool
    has_analyze: bool
    has_results_data: bool


class PylinacCapabilityCollection(BaseModel):
    """The locked engine inventory used by the QA workspace."""

    catalogue_version: str = Field(min_length=1)
    pylinac_version: str = Field(min_length=1)
    wheel_sha256: str = Field(min_length=64, max_length=64)
    package_fingerprint: str = Field(min_length=64, max_length=64)
    total_bindings: int = Field(ge=0)
    runtime_available: int = Field(ge=0)
    unresolved_catalog_keys: list[str]
    input_profile_contract_mismatches: list[dict[str, str | None]]
    fixture_coverage_counts: dict[str, int]
    capabilities: list[PylinacCapabilityStatus]


@router.get(
    "/organizations/{organization_id}/qa-test-definitions",
    response_model=QATestDefinitionCollection,
)
def list_qa_test_definitions(
    organization_id: UUID,
    q: str | None = Query(default=None, max_length=200),
    family: str | None = Query(default=None, max_length=120),
    include_planned: bool = Query(default=True),
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> QATestDefinitionCollection:
    """Return every catalogue entry visible to an active organization member.

    The endpoint intentionally includes planned entries by default.  This keeps
    the menu complete while the client disables execution until the corresponding
    adapter and input wizard are released.
    """

    context = resolve_session_context(session, identity)
    if context.organization_id != organization_id:
        raise DomainError(
            "ORGANIZATION_SCOPE_MISMATCH",
            "The requested organization is outside the authenticated membership scope.",
            403,
        )
    normalized_query = q.strip().casefold() if q else None
    normalized_family = family.strip().casefold() if family else None
    items: list[QATestDefinition] = []
    for definition in QA_TEST_CATALOG:
        if not include_planned and definition.implementation_status == "PLANNED":
            continue
        if normalized_family and definition.family.casefold() != normalized_family:
            continue
        if normalized_query and normalized_query not in " ".join(
            (definition.name, definition.family, definition.description)
        ).casefold():
            continue
        items.append(definition)
    return QATestDefinitionCollection(
        items=items,
        total=len(items),
        catalogue_version=CATALOGUE_VERSION,
    )


@router.get(
    "/organizations/{organization_id}/pylinac-capabilities",
    response_model=PylinacCapabilityCollection,
)
def get_pylinac_capabilities(
    organization_id: UUID,
    identity: AuthenticatedIdentity = Depends(require_identity),  # noqa: B008
    session: Session = Depends(get_session),  # noqa: B008
) -> PylinacCapabilityCollection:
    """Return the locked engine inventory to an active organization member."""

    context = resolve_session_context(session, identity)
    if context.organization_id != organization_id:
        raise DomainError(
            "ORGANIZATION_SCOPE_MISMATCH",
            "The requested organization is outside the authenticated membership scope.",
            403,
        )

    summary = registry_summary()
    capabilities = [
        PylinacCapabilityStatus(
            key=item["catalog_key"],
            name=item["display_name"],
            family=item["module_family"],
            input_profile=item["input_profile"],
            source_tier=item["source_tier"],
            fixture_status=item["fixture_status"],
            fixture_reference=item["fixture_reference"],
            fixture_note=item["fixture_note"],
            runtime_available=item["runtime_available"],
            has_analyze=item["has_analyze"],
            has_results_data=item["has_results_data"],
        )
        for item in summary["capabilities"]
    ]
    return PylinacCapabilityCollection(
        catalogue_version=summary["catalogue_version"],
        pylinac_version=summary["pylinac_version"],
        wheel_sha256=summary["wheel_sha256"],
        package_fingerprint=summary["package_fingerprint"],
        total_bindings=summary["total_bindings"],
        runtime_available=summary["runtime_available"],
        unresolved_catalog_keys=summary["unresolved_catalog_keys"],
        input_profile_contract_mismatches=summary["input_profile_contract_mismatches"],
        fixture_coverage_counts=summary["fixture_coverage_counts"],
        capabilities=capabilities,
    )
