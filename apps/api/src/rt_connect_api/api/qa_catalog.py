"""QA test catalogue endpoint for the organization-scoped QA workspace."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
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
from rt_connect_api.services.session_context import resolve_session_context

router = APIRouter(tags=["qa-catalog"])


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
