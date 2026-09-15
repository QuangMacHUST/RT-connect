from __future__ import annotations

from rt_connect_api.qa_catalog import CATALOGUE_VERSION, QA_TEST_CATALOG
from rt_connect_api.services.pylinac_fixture_matrix import (
    FIXTURE_COVERAGE,
    fixture_coverage_counts,
    fixture_coverage_diff,
)
from rt_connect_api.services.pylinac_registry import (
    PYLINAC_VERSION,
    PYLINAC_WHEEL_SHA256,
    RUNTIME_BINDINGS,
    pylinac_input_profile_diff,
    pylinac_inventory_diff,
    registry_summary,
    resolve_capabilities,
    resolve_runtime_symbol,
    runtime_binding,
    unresolved_catalog_keys,
)
from test_workspace import _workspace_client


def test_registry_resolves_every_pylinac_catalogue_entry() -> None:
    pylinac_keys = {
        definition.key for definition in QA_TEST_CATALOG if definition.engine_name == "pylinac"
    }
    capabilities = resolve_capabilities()

    assert PYLINAC_VERSION == "3.47.0"
    assert len(PYLINAC_WHEEL_SHA256) == 64
    assert len(capabilities) == len(pylinac_keys) == 63
    assert {item.catalog_key for item in capabilities} == pylinac_keys
    assert all(item.runtime_available for item in capabilities)
    assert unresolved_catalog_keys() == ()


def test_locked_pylinac_public_inventory_is_fully_bound() -> None:
    """A wheel change must not silently remove or add an unmapped QA capability."""

    assert pylinac_inventory_diff() == {
        "missing_symbols": [],
        "unexpected_symbols": [],
        "unbound_symbols": [],
    }


def test_catalogue_input_profiles_match_all_runtime_bindings() -> None:
    assert pylinac_input_profile_diff() == []


def test_fixture_matrix_covers_every_registered_capability_without_defaulting() -> None:
    registered_keys = {binding.catalog_key for binding in RUNTIME_BINDINGS}

    assert fixture_coverage_diff(registered_keys) == {
        "missing_catalog_keys": [],
        "unexpected_catalog_keys": [],
    }
    assert len(FIXTURE_COVERAGE) == 63
    assert fixture_coverage_counts() == {
        "OFFICIAL_DEMO": 37,
        "SYNTHETIC_CONTRACT": 13,
        "COMMISSIONING_REQUIRED": 13,
    }


def test_registry_exposes_fixture_status_and_preserves_commissioning_boundary() -> None:
    capabilities = {item.catalog_key: item for item in resolve_capabilities()}

    assert capabilities["CATPHAN_503"].fixture_status == "OFFICIAL_DEMO"
    assert capabilities["CATPHAN_503"].fixture_reference == "CatPhan503.zip"
    assert capabilities["ACR_CT_464"].fixture_status == "COMMISSIONING_REQUIRED"
    assert "chuỗi DICOM" in capabilities["ACR_CT_464"].fixture_note


def test_catalogue_engine_names_match_the_locked_runtime_symbols() -> None:
    definitions = {definition.key: definition for definition in QA_TEST_CATALOG}

    for capability in resolve_capabilities():
        definition = definitions[capability.catalog_key]
        binding = runtime_binding(capability.catalog_key)
        symbol, error = resolve_runtime_symbol(capability.catalog_key)

        assert binding is not None
        assert symbol is not None, error
        assert definition.engine_class == getattr(symbol, "__name__", None)


def test_registry_summary_contains_provenance_without_raw_error() -> None:
    summary = registry_summary()

    assert summary["pylinac_version"] == "3.47.0"
    assert summary["catalogue_version"] == CATALOGUE_VERSION
    assert summary["wheel_sha256"] == PYLINAC_WHEEL_SHA256
    assert summary["total_bindings"] == 63
    assert summary["runtime_available"] == 63
    assert summary["unresolved_catalog_keys"] == []
    assert summary["input_profile_contract_mismatches"] == []
    assert summary["fixture_coverage"] == {
        "missing_catalog_keys": [],
        "unexpected_catalog_keys": [],
    }
    assert summary["fixture_coverage_counts"] == {
        "OFFICIAL_DEMO": 37,
        "SYNTHETIC_CONTRACT": 13,
        "COMMISSIONING_REQUIRED": 13,
    }
    assert len(summary["package_fingerprint"]) == 64
    assert all("traceback" not in str(item).casefold() for item in summary["capabilities"])


def test_capability_endpoint_is_organization_scoped() -> None:
    with _workspace_client() as (client, organization):
        response = client.get(f"/api/v1/organizations/{organization.id}/pylinac-capabilities")
        outside = client.get(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000000/pylinac-capabilities"
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
    assert body["input_profile_contract_mismatches"] == []
    assert len(body["capabilities"]) == 63
    assert outside.status_code == 403
    assert outside.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"
