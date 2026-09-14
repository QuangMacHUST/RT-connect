from __future__ import annotations

from rt_connect_api.qa_catalog import CATALOGUE_VERSION, QA_TEST_CATALOG
from rt_connect_api.services.pylinac_registry import (
    PYLINAC_VERSION,
    PYLINAC_WHEEL_SHA256,
    registry_summary,
    resolve_capabilities,
    unresolved_catalog_keys,
)
from test_workspace import _workspace_client


def test_registry_resolves_every_pylinac_catalogue_entry() -> None:
    pylinac_keys = {
        definition.key
        for definition in QA_TEST_CATALOG
        if definition.engine_name == "pylinac"
    }
    capabilities = resolve_capabilities()

    assert PYLINAC_VERSION == "3.47.0"
    assert len(PYLINAC_WHEEL_SHA256) == 64
    assert len(capabilities) == len(pylinac_keys) == 63
    assert {item.catalog_key for item in capabilities} == pylinac_keys
    assert all(item.runtime_available for item in capabilities)
    assert unresolved_catalog_keys() == ()


def test_registry_summary_contains_provenance_without_raw_error() -> None:
    summary = registry_summary()

    assert summary["pylinac_version"] == "3.47.0"
    assert summary["catalogue_version"] == CATALOGUE_VERSION
    assert summary["wheel_sha256"] == PYLINAC_WHEEL_SHA256
    assert summary["total_bindings"] == 63
    assert summary["runtime_available"] == 63
    assert summary["unresolved_catalog_keys"] == []
    assert len(summary["package_fingerprint"]) == 64
    assert all("traceback" not in str(item).casefold() for item in summary["capabilities"])


def test_capability_endpoint_is_organization_scoped() -> None:
    with _workspace_client() as (client, organization):
        response = client.get(
            f"/api/v1/organizations/{organization.id}/pylinac-capabilities"
        )
        outside = client.get(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000000/"
            "pylinac-capabilities"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["pylinac_version"] == "3.47.0"
    assert body["wheel_sha256"] == PYLINAC_WHEEL_SHA256
    assert body["catalogue_version"] == CATALOGUE_VERSION
    assert body["package_fingerprint"]
    assert body["total_bindings"] == 63
    assert body["runtime_available"] == 63
    assert body["unresolved_catalog_keys"] == []
    assert len(body["capabilities"]) == 63
    assert outside.status_code == 403
    assert outside.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"
