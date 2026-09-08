from __future__ import annotations

from uuid import uuid4

from test_workspace import _workspace_client


def _scenario(*, key: str = "BED_SCENARIO_01") -> dict[str, object]:
    return {
        "scenario_key": key,
        "name": "Independent BED scenario",
        "scenario_type": "BED_EQD2",
        "tissue_context": "Spinal cord, alpha/beta 2 Gy",
        "clinical_context": "Synthetic development context; no patient record.",
        "source_type": "USER_DEFINED",
        "assumptions": {"alpha_beta_gy": 2.0, "recovery": "not_applicable"},
    }


def test_biological_hub_scenario_lifecycle_is_independent_and_versioned() -> None:
    with _workspace_client() as (client, organization):
        base_url = f"/api/v1/organizations/{organization.id}/biological"

        tools = client.get(f"{base_url}/tools")
        assert tools.status_code == 200, tools.text
        assert len(tools.json()) == 6
        assert all(item["available"] is False for item in tools.json())

        summary = client.get(f"{base_url}/summary")
        assert summary.status_code == 200
        assert summary.json()["total_scenarios"] == 0

        validation = client.post(f"{base_url}/scenarios/validate", json=_scenario())
        assert validation.status_code == 200, validation.text
        assert validation.json() == {"valid": True, "errors": [], "warnings": []}
        assert client.get(f"{base_url}/scenarios").json()["total"] == 0

        created = client.post(f"{base_url}/scenarios", json=_scenario())
        assert created.status_code == 201, created.text
        draft = created.json()
        assert draft["status"] == "DRAFT"
        assert draft["revision"] == 1
        assert draft["latest_snapshot"]["scenario_key"] == "BED_SCENARIO_01"

        patched = client.patch(
            f"{base_url}/scenarios/{draft['id']}",
            json={
                "expected_revision": 1,
                "clinical_context": "Updated synthetic context",
                "assumptions": {"alpha_beta_gy": 3.0, "recovery": "not_applicable"},
            },
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["revision"] == 2
        assert patched.json()["latest_snapshot"]["assumptions"]["alpha_beta_gy"] == 3.0

        stale = client.patch(
            f"{base_url}/scenarios/{draft['id']}",
            json={"expected_revision": 1, "name": "stale"},
        )
        assert stale.status_code == 409, stale.text
        assert stale.json()["code"] == "SCENARIO_REVISION_CONFLICT"

        saved = client.post(
            f"{base_url}/scenarios/{draft['id']}/save",
            json={"expected_revision": 2},
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["status"] == "SAVED"
        assert saved.json()["revision"] == 3

        immutable = client.patch(
            f"{base_url}/scenarios/{draft['id']}",
            json={"expected_revision": 3, "name": "must clone"},
        )
        assert immutable.status_code == 409, immutable.text
        assert immutable.json()["code"] == "SCENARIO_IMMUTABLE"

        cloned = client.post(
            f"{base_url}/scenarios/{draft['id']}/clone",
            json={"scenario_key": "BED_SCENARIO_02", "name": "Independent BED copy"},
        )
        assert cloned.status_code == 201, cloned.text
        copy = cloned.json()
        assert copy["status"] == "DRAFT"
        assert copy["revision"] == 1
        assert copy["source_scenario_revision_id"] is not None
        assert copy["assumptions"] == saved.json()["assumptions"]

        archived = client.post(
            f"{base_url}/scenarios/{copy['id']}/archive",
            json={"expected_revision": 1},
        )
        assert archived.status_code == 200, archived.text
        assert archived.json()["status"] == "ARCHIVED"
        assert archived.json()["revision"] == 2

        visible = client.get(f"{base_url}/scenarios")
        assert visible.status_code == 200
        assert [item["id"] for item in visible.json()["items"]] == [draft["id"]]
        all_versions = client.get(f"{base_url}/scenarios?include_archived=true")
        assert all_versions.status_code == 200
        assert {item["id"] for item in all_versions.json()["items"]} == {
            draft["id"],
            copy["id"],
        }

        revisions = client.get(f"{base_url}/scenarios/{draft['id']}/revisions")
        assert revisions.status_code == 200
        assert [item["revision_number"] for item in revisions.json()] == [3, 2, 1]
        assert revisions.json()[0]["status"] == "SAVED"

        calculations = client.get(f"{base_url}/calculations?scenario_id={draft['id']}")
        assert calculations.status_code == 200
        assert calculations.json()["total"] == 0

        summary = client.get(f"{base_url}/summary").json()
        assert summary["total_scenarios"] == 2
        assert summary["saved_scenarios"] == 1
        assert summary["archived_scenarios"] == 1


def test_biological_hub_rejects_invalid_source_duplicate_and_scope() -> None:
    with _workspace_client() as (client, organization):
        base_url = f"/api/v1/organizations/{organization.id}/biological"
        missing_reference = _scenario(key="REFERENCE_SCENARIO")
        missing_reference["source_type"] = "REFERENCE"
        validation = client.post(f"{base_url}/scenarios/validate", json=missing_reference)
        assert validation.status_code == 200
        assert validation.json()["valid"] is False
        assert validation.json()["errors"][0]["code"] == "BIOLOGICAL_CONTEXT_INVALID"

        created = client.post(f"{base_url}/scenarios", json=_scenario())
        assert created.status_code == 201
        duplicate = client.post(f"{base_url}/scenarios", json=_scenario())
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "SCENARIO_KEY_CONFLICT"

        outsider = client.get(f"/api/v1/organizations/{uuid4()}/biological/scenarios")
        assert outsider.status_code == 403
        assert outsider.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"

        missing = client.get(f"{base_url}/calculations/{uuid4()}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "CALCULATION_NOT_FOUND"
