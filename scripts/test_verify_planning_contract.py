"""Regression tests for UX1 document structure, including negative controls."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "planning_verifier", ROOT / "scripts" / "verify-planning-contract.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class PlanningContractTests(unittest.TestCase):
    def verify_with_change(self, filename: str, transform):
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            text = original_read(path, *args, **kwargs)
            if path == ROOT / filename:
                return transform(text)
            return text

        with patch.object(Path, "read_text", new=read):
            return VERIFIER.verify(ROOT)

    def assert_failed(self, report, name: str):
        self.assertFalse(report["passed"])
        self.assertIn(name, [c["name"] for c in report["checks"] if not c["ok"]])

    def test_current_documents_pass(self):
        result = VERIFIER.verify(ROOT)
        self.assertTrue(result["passed"], [c for c in result["checks"] if not c["ok"]])
        self.assertEqual(result["phase_count"], 21)
        self.assertEqual(result["acceptance_scenario_count"], 260)

    def test_stale_version_fails(self):
        result = self.verify_with_change(
            "plan.md", lambda text: text.replace("Phiên bản: **5.3**", "Phiên bản: **4.25**")
        )
        self.assert_failed(result, "version.plan")

    def test_stale_pylinac_catalog_version_fails(self):
        result = self.verify_with_change(
            "docs/pylinac-qa-catalog.md",
            lambda text: text.replace("**Phiên bản danh mục:** 1.1", "**Phiên bản danh mục:** 1.0"),
        )
        self.assert_failed(result, "version.pylinac_catalog")

    def test_missing_phase_fails(self):
        result = self.verify_with_change(
            "plan.md", lambda text: text.replace("## P7 —", "## Removed P7 —")
        )
        self.assert_failed(result, "phase.7.plan_heading")

    def test_error_cases_must_be_inside_their_phase(self):
        result = self.verify_with_change(
            "plan.md",
            lambda text: re.sub(r"^- TC-UX1-P07-E.*\n", "", text, flags=re.MULTILINE),
        )
        self.assert_failed(result, "phase.7.error_tests")

    def test_image_engine_package_cannot_be_omitted(self):
        result = self.verify_with_change(
            "plan.md", lambda text: text.replace("P07-NUCLEAR", "REMOVED-NUCLEAR")
        )
        self.assert_failed(result, "pylinac_package.P07-NUCLEAR")

    def test_pylinac_catalog_family_cannot_be_omitted(self):
        result = self.verify_with_change(
            "docs/pylinac-qa-catalog.md",
            lambda text: text.replace("Winston–Lutz Multi-Target", "REMOVED-MULTI-TARGET"),
        )
        self.assert_failed(result, "pylinac.catalog.Winston–Lutz Multi-Target")

    def test_pylinac_contrib_cannot_be_omitted(self):
        result = self.verify_with_change(
            "docs/pylinac-qa-catalog.md",
            lambda text: text.replace("QuasarLightRadScaling", "REMOVED-QUASAR"),
        )
        self.assert_failed(result, "pylinac.catalog.QuasarLightRadScaling")

    def test_pylinac_adapter_cannot_be_omitted(self):
        result = self.verify_with_change(
            "plan.md", lambda text: text.replace("PylinacAdapter", "RemovedAdapter")
        )
        self.assert_failed(result, "pylinac.plan.adapter")

    def test_duplicate_test_ids_fail(self):
        result = self.verify_with_change(
            "plan.md", lambda text: text.replace("TC-UX1-P00-S02", "TC-UX1-P00-S01")
        )
        self.assert_failed(result, "test_id.uniqueness")

    def test_missing_requirement_mapping_fails(self):
        result = self.verify_with_change(
            "business-analysis.md", lambda text: text.replace("FR-UX1-P16-01", "REMOVED")
        )
        self.assert_failed(result, "phase.16.business_mapping")

    def test_legacy_specification_must_not_claim_authority(self):
        result = self.verify_with_change(
            "docs/history/pre-ux-20260912/specification.md",
            lambda text: text.replace("TÀI LIỆU KẾ THỪA", "REMOVED"),
        )
        self.assert_failed(result, "marker.specification.legacy")

    def test_missing_local_link_fails(self):
        result = self.verify_with_change(
            "plan.md", lambda text: text + "\n[Missing](does-not-exist-ux1.md)\n"
        )
        self.assert_failed(result, "link.plan.does-not-exist-ux1.md")

    def test_skipping_previous_phase_fails(self):
        result = self.verify_with_change(
            "plan.md",
            lambda text: text.replace(
                "**Đầu vào/phụ thuộc:** P10 đã hoàn thành và có bàn giao;",
                "**Đầu vào/phụ thuộc:** P5 đã hoàn thành và có bàn giao;",
            ),
        )
        self.assert_failed(result, "phase.11.sequential_dependency")

    def test_missing_package_fails(self):
        result = self.verify_with_change(
            "plan.md", lambda text: text.replace("P09-W02 —", "REMOVED-W02 —")
        )
        self.assert_failed(result, "phase.9.package.w02")


if __name__ == "__main__":
    unittest.main()
