from __future__ import annotations

from uuid import uuid4

from test_workspace import _workspace_client


def _dose_limit(
    *, key: str = "LUNG_CORD_DMAX", name: str = "Spinal cord Dmax"
) -> dict[str, object]:
    return {
        "entry_key": key,
        "entry_type": "DOSE_LIMIT",
        "name": name,
        "description": "Reference-only OAR constraint for a synthetic library fixture.",
        "disease": "Lung cancer",
        "disease_subtype": "NSCLC",
        "anatomy_site": "Thorax",
        "treatment_intent": "Definitive",
        "technique": "VMAT",
        "fractions": 30,
        "tissue_or_oar": "Spinal cord",
        "metric_key": "DMAX",
        "operator": "MAX",
        "limit_value": 45.0,
        "unit": "Gy",
        "applicability": {
            "diseases": ["Lung cancer"],
            "subtypes": ["NSCLC"],
            "anatomy_sites": ["Thorax"],
            "techniques": ["VMAT"],
            "tissue_or_oars": ["Spinal cord"],
            "fractions": [30],
        },
        "content": {"summary": "Synthetic source; replace with an approved reference."},
        "source_type": "REFERENCE",
        "source_reference": "https://example.invalid/synthetic-dose-limit",
        "reference_status": "UNVERIFIED",
        "source_date": "2026-09-08",
        "evidence_level": "Synthetic fixture",
        "citation": {"title": "Synthetic dose-limit fixture", "year": 2026},
    }


def _alpha_beta() -> dict[str, object]:
    return {
        "entry_key": "SPINAL_CORD_ALPHA_BETA",
        "entry_type": "ALPHA_BETA",
        "name": "Spinal cord alpha/beta reference",
        "tissue_or_oar": "Spinal cord",
        "alpha_beta_gy": 2.0,
        "source_type": "USER_DEFINED",
        "source_reference": "Synthetic user-defined assumption",
        "content": {"note": "Independent calculator reference only."},
    }


def test_library_lifecycle_filter_use_snapshot_and_version_lineage() -> None:
    with _workspace_client() as (client, organization):
        base = f"/api/v1/organizations/{organization.id}/biological/library"
        definition = _dose_limit()

        validation = client.post(f"{base}/validate", json=definition)
        assert validation.status_code == 200, validation.text
        assert validation.json()["valid"] is True
        assert validation.json()["normalized_entry"]["entry_key"] == "LUNG_CORD_DMAX"
        assert any(
            item["code"] == "REFERENCE_NOT_VERIFIED"
            for item in validation.json()["warnings"]
        )

        created = client.post(base, json=definition)
        assert created.status_code == 201, created.text
        draft = created.json()
        assert draft["status"] == "DRAFT"
        assert draft["version_number"] == 1
        assert draft["revision"] == 1
        assert draft["applicability"]["fractions"] == [30]

        patched = client.patch(
            f"{base}/{draft['id']}",
            json={"expected_revision": 1, "effective_note": "Updated synthetic note"},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["revision"] == 2

        stale = client.patch(
            f"{base}/{draft['id']}",
            json={"expected_revision": 1, "name": "stale edit"},
        )
        assert stale.status_code == 409
        assert stale.json()["code"] == "KNOWLEDGE_REVISION_CONFLICT"

        published = client.post(
            f"{base}/{draft['id']}/publish", json={"expected_revision": 2}
        )
        assert published.status_code == 200, published.text
        active = published.json()
        assert active["status"] == "PUBLISHED"
        assert active["revision"] == 3

        immutable = client.patch(
            f"{base}/{draft['id']}",
            json={"expected_revision": 3, "name": "must clone"},
        )
        assert immutable.status_code == 409
        assert immutable.json()["code"] == "KNOWLEDGE_VERSION_IMMUTABLE"

        clone = client.post(
            f"{base}/{draft['id']}/clone", json={"name": "Spinal cord Dmax local copy"}
        )
        assert clone.status_code == 201, clone.text
        copy = clone.json()
        assert copy["status"] == "DRAFT"
        assert copy["version_number"] == 2
        assert copy["source_entry_id"] == draft["id"]
        assert copy["content_sha256"] != active["content_sha256"]

        matching = client.get(
            base,
            params={
                "entry_type": "DOSE_LIMIT",
                "disease": "Lung cancer",
                "anatomy_site": "Thorax",
                "technique": "VMAT",
                "tissue_or_oar": "Spinal cord",
                "metric_key": "DMAX",
                "fractions": 30,
            },
        )
        assert matching.status_code == 200
        assert matching.json()["total"] == 2
        assert all(item["entry_key"] == "LUNG_CORD_DMAX" for item in matching.json()["items"])

        unknown = client.get(base, params={"disease": "Brain tumor"})
        assert unknown.status_code == 200
        assert unknown.json()["total"] == 0

        use = client.post(
            f"{base}/{draft['id']}/use",
            json={
                "target_tool": "P17_DVH",
                "override": {"limit_value": 46.0},
            },
        )
        assert use.status_code == 200, use.text
        use_body = use.json()
        assert use_body["source_snapshot"]["version_number"] == 1
        assert use_body["source_snapshot"]["status"] == "PUBLISHED"
        assert use_body["effective_values"]["limit_value"] == 46.0
        assert use_body["override_label"] == "USER_OVERRIDE"
        assert len(use_body["snapshot_sha256"]) == 64

        revisions = client.get(f"{base}/{draft['id']}/revisions")
        assert revisions.status_code == 200
        assert [item["version_number"] for item in revisions.json()] == [2, 1]

        archived = client.post(
            f"{base}/{draft['id']}/archive", json={"expected_revision": 3}
        )
        assert archived.status_code == 200
        assert archived.json()["status"] == "ARCHIVED"
        assert client.get(base).json()["total"] == 1
        assert client.get(base, params={"include_archived": True}).json()["total"] == 2

        exported = client.get(f"{base}/{copy['id']}/export?export_format=CSV")
        assert exported.status_code == 200
        assert "entry_key" in exported.text
        assert "LUNG_CORD_DMAX" in exported.text


def test_library_import_preview_is_row_scoped_and_rejects_unsafe_content() -> None:
    with _workspace_client() as (client, organization):
        base = f"/api/v1/organizations/{organization.id}/biological/library"
        invalid = _dose_limit(key="BAD_CONTENT")
        invalid["content"] = {"html": "<script>alert('x')</script>"}
        duplicate = _alpha_beta()
        duplicate["entry_key"] = "IMPORT_DUPLICATE"
        duplicate_again = dict(duplicate)
        preview = client.post(
            f"{base}/import/validate",
            json={"rows": [_dose_limit(key="IMPORT_DOSE"), invalid, duplicate, duplicate_again]},
        )
        assert preview.status_code == 200, preview.text
        body = preview.json()
        assert body["dry_run"] is True
        assert body["committed_count"] == 0
        assert body["rejected_count"] == 2
        assert body["rows"][0]["valid"] is True
        assert body["rows"][1]["errors"][0]["code"] == "KNOWLEDGE_CONTENT_INVALID"
        assert body["rows"][3]["errors"][0]["code"] == "KNOWLEDGE_IMPORT_INVALID"
        assert client.get(base).json()["total"] == 0

        committed = client.post(
            f"{base}/import",
            json={"rows": [_dose_limit(key="IMPORT_DOSE"), invalid], "commit_valid": True},
        )
        assert committed.status_code == 200, committed.text
        assert committed.json()["dry_run"] is False
        assert committed.json()["committed_count"] == 1
        assert committed.json()["rejected_count"] == 1
        assert client.get(base).json()["total"] == 1


def test_library_rejects_bad_unit_missing_reference_archived_use_and_cross_scope() -> None:
    with _workspace_client() as (client, organization):
        base = f"/api/v1/organizations/{organization.id}/biological/library"
        bad_unit = _dose_limit(key="BAD_UNIT")
        bad_unit["unit"] = "%"
        bad_unit["source_type"] = "REFERENCE"
        bad_unit["source_reference"] = None
        validation = client.post(f"{base}/validate", json=bad_unit)
        assert validation.status_code == 200
        codes = {item["code"] for item in validation.json()["errors"]}
        assert {"DOSE_LIMIT_UNIT_INVALID", "KNOWLEDGE_SOURCE_REQUIRED"} <= codes

        alpha = client.post(base, json=_alpha_beta())
        assert alpha.status_code == 201, alpha.text
        archived = client.post(
            f"{base}/{alpha.json()['id']}/archive", json={"expected_revision": 1}
        )
        assert archived.status_code == 200
        unavailable = client.post(
            f"{base}/{alpha.json()['id']}/use", json={"target_tool": "P13_BED_EQD2"}
        )
        assert unavailable.status_code == 409
        assert unavailable.json()["code"] == "KNOWLEDGE_NOT_AVAILABLE"

        outsider = client.get(f"/api/v1/organizations/{uuid4()}/biological/library")
        assert outsider.status_code == 403
        assert outsider.json()["code"] == "ORGANIZATION_SCOPE_MISMATCH"
