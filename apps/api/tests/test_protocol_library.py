from __future__ import annotations

from uuid import uuid4

from test_workspace import _workspace_client


def _rule(
    metric_key: str = "output_factor",
    *,
    lower_limit: float = 98.0,
    upper_limit: float = 102.0,
) -> dict[str, object]:
    return {
        "metric_key": metric_key,
        "display_name": "Output factor",
        "unit": "%",
        "rule_type": "RANGE",
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "action_level": 1.0,
        "required": True,
        "sort_order": 0,
        "reference": "Synthetic site QA handbook, section 2",
    }


def _definition(*, activate: bool = False) -> dict[str, object]:
    return {
        "protocol_key": "SITE_MACHINE_QA",
        "name": "Site machine QA",
        "qa_type": "Machine QA",
        "description": "A versioned site protocol used by the Machine QA workspace.",
        "effective_note": "Synthetic test definition; replace with site source.",
        "applicability": {"qa_cycles": ["DAILY"], "energies": ["6X"]},
        "source_type": "REFERENCE",
        "source_reference": "https://example.invalid/site-machine-qa",
        "rules": [_rule()],
        "activate": activate,
    }


def test_protocol_library_validates_creates_clones_archives_and_compares() -> None:
    with _workspace_client() as (client, organization):
        organization_id = str(organization.id)
        base_url = f"/api/v1/organizations/{organization_id}/qa-protocols"

        validation = client.post(f"{base_url}/validate", json=_definition())
        assert validation.status_code == 200, validation.text
        assert validation.json() == {"valid": True, "errors": [], "warnings": []}

        created = client.post(base_url, json=_definition())
        assert created.status_code == 201, created.text
        draft = created.json()
        assert draft["status"] == "DRAFT"
        assert draft["version_number"] == 1
        assert draft["revision"] == 1
        assert draft["applicability"] == {"energies": ["6X"], "qa_cycles": ["DAILY"]}
        assert draft["rules"][0]["reference"] == "Synthetic site QA handbook, section 2"

        patched = client.patch(
            f"{base_url}/{draft['id']}",
            json={
                "expected_revision": 1,
                "effective_note": "Updated source note",
                "rules": [_rule(upper_limit=101.0)],
            },
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["revision"] == 2
        assert patched.json()["rules"][0]["upper_limit"] == 101.0

        stale = client.patch(
            f"{base_url}/{draft['id']}",
            json={"expected_revision": 1, "name": "stale edit"},
        )
        assert stale.status_code == 409, stale.text
        assert stale.json()["code"] == "PROTOCOL_VERSION_CONFLICT"

        activated = client.post(f"{base_url}/{draft['id']}/activate", json={"expected_revision": 2})
        assert activated.status_code == 200, activated.text
        active = activated.json()
        assert active["status"] == "ACTIVE"
        assert active["revision"] == 3

        immutable = client.patch(
            f"{base_url}/{draft['id']}",
            json={"expected_revision": 3, "name": "must not mutate active"},
        )
        assert immutable.status_code == 409, immutable.text
        assert immutable.json()["code"] == "PROTOCOL_VERSION_IMMUTABLE"

        cloned = client.post(f"{base_url}/{draft['id']}/clone", json={"name": "Site machine QA v2"})
        assert cloned.status_code == 201, cloned.text
        clone = cloned.json()
        assert clone["status"] == "DRAFT"
        assert clone["version_number"] == 2
        assert clone["source_protocol_version_id"] == draft["id"]
        assert clone["rules"][0]["id"] != active["rules"][0]["id"]

        comparison = client.get(
            f"{base_url}/{draft['id']}/compare", params={"other_id": clone["id"]}
        )
        assert comparison.status_code == 200, comparison.text
        assert comparison.json()["same_family"] is True
        assert any(item["field"] == "status" for item in comparison.json()["metadata_diffs"])

        archived = client.post(f"{base_url}/{draft['id']}/archive", json={"expected_revision": 3})
        assert archived.status_code == 200, archived.text
        assert archived.json()["status"] == "ARCHIVED"

        listed = client.get(base_url)
        assert listed.status_code == 200, listed.text
        assert [item["id"] for item in listed.json()["items"]] == [clone["id"]]
        listed_with_archive = client.get(base_url, params={"include_archived": True})
        assert listed_with_archive.status_code == 200
        assert {item["id"] for item in listed_with_archive.json()["items"]} == {
            draft["id"],
            clone["id"],
        }


def test_protocol_library_rejects_bad_rules_and_reference_without_mutation() -> None:
    with _workspace_client() as (client, organization):
        base_url = f"/api/v1/organizations/{organization.id}/qa-protocols"
        bad = _definition()
        bad["source_reference"] = None
        bad["rules"] = [_rule(lower_limit=105.0, upper_limit=100.0), _rule()]

        validation = client.post(f"{base_url}/validate", json=bad)
        assert validation.status_code == 200
        body = validation.json()
        assert body["valid"] is False
        assert {item["code"] for item in body["errors"]} >= {
            "REFERENCE_REQUIRED",
            "PROTOCOL_RULE_INVALID",
            "PROTOCOL_VERSION_CONFLICT",
        }

        created = client.post(base_url, json=bad)
        assert created.status_code == 422
        assert created.json()["code"] == "REFERENCE_REQUIRED"
        assert client.get(base_url).json()["total"] == 0


def test_protocol_library_scope_and_machine_qa_only_accept_active_versions() -> None:
    with _workspace_client() as (client, organization):
        base_url = f"/api/v1/organizations/{organization.id}/qa-protocols"
        protocol = client.post(base_url, json=_definition(activate=True))
        assert protocol.status_code == 201, protocol.text
        active = protocol.json()

        machine_qa_url = f"{base_url.replace('/qa-protocols', '')}/machine-qa/protocols"
        machine_protocols = client.get(machine_qa_url)
        assert machine_protocols.status_code == 200, machine_protocols.text
        assert [item["id"] for item in machine_protocols.json()["items"]] == [active["id"]]

        outsider = client.get(f"/api/v1/organizations/{uuid4()}/qa-protocols")
        assert outsider.status_code == 403, outsider.text
        assert outsider.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"

        archived = client.post(f"{base_url}/{active['id']}/archive", json={"expected_revision": 1})
        assert archived.status_code == 200, archived.text
        assert client.get(machine_qa_url).json()["total"] == 0
