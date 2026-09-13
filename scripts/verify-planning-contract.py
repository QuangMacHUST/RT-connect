"""Fail-closed consistency checks for the RT-CONNECT planning documents.

The verifier checks document versions, cross-references, phase coverage and the
required workflow/test sections. It does not infer implementation status from a
checkbox and never reads or prints secrets or patient data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


PHASES = range(21)


def _check(
    checks: list[dict[str, object]],
    name: str,
    ok: bool,
    details: str,
) -> None:
    checks.append({"name": name, "ok": ok, "details": details})


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.MULTILINE) is not None


def _version(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1) if match else None


def _phase_section(plan: str, phase: int) -> str:
    match = re.search(
        rf"^## P{phase} —[^\n]*\n(.*?)(?=^## |\Z)",
        plan,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1) if match else ""


def verify(root: Path) -> dict[str, object]:
    paths = {
        "business": root / "business-analysis.md",
        "specification": root / "docs/history/pre-ux-20260912/specification.md",
        "technical": root / "technical-specification.md",
        "plan": root / "plan.md",
        "progress": root / "implementation-progress.md",
        "pylinac_catalog": root / "docs" / "pylinac-qa-catalog.md",
    }
    texts: dict[str, str] = {}
    checks: list[dict[str, object]] = []

    for name, path in paths.items():
        exists = path.is_file()
        _check(checks, f"file.{name}", exists, str(path.relative_to(root)))
        if exists:
            texts[name] = path.read_text(encoding="utf-8")

    expected_versions = {
        "business": (r"\*\*Phiên bản tài liệu:\*\*\s*([0-9]+\.[0-9]+)", "1.3"),
        "specification": (r"version \*\*([0-9]+\.[0-9]+)\*\*", "1.29"),
        "technical": (r"\*\*Phiên bản:\*\*\s*([0-9]+\.[0-9]+)", "2.3"),
        "plan": (r"Phiên bản:\s*\*\*([0-9]+\.[0-9]+)\*\*", "5.3"),
        "pylinac_catalog": (r"\*\*Phiên bản danh mục:\*\*\s*([0-9]+\.[0-9]+)", "1.1"),
    }
    for name, (pattern, expected) in expected_versions.items():
        observed = _version(pattern, texts.get(name, ""))
        _check(
            checks,
            f"version.{name}",
            observed == expected,
            f"expected={expected}; observed={observed or 'missing'}",
        )

    references = {
        "business": "plan.md v5.3",
        "specification": "plan.md v5.3",
        "technical": "plan.md v5.3",
        "progress": "plan.md v5.3",
    }
    for name, reference in references.items():
        code_span_reference = f"`{reference.split()[0]}` {reference.split()[1]}"
        _check(
            checks,
            f"reference.{name}.plan",
            reference in texts.get(name, "") or code_span_reference in texts.get(name, ""),
            f"required={reference} or {code_span_reference}",
        )

    plan = texts.get("plan", "")
    business = texts.get("business", "")
    specification = texts.get("specification", "")
    technical = texts.get("technical", "")
    pylinac_catalog = texts.get("pylinac_catalog", "")

    required_markers = {
        "business.navigation": (business, "## 3. Cấu trúc điều hướng mới"),
        "business.no_technical_ui": (business, "### 3.3. Không yêu cầu kiến thức kỹ thuật"),
        "business.deletion": (business, "### 7.2. Xóa và khôi phục"),
        "business.biological": (business, "## 9. Công cụ sinh học — một trang, tính đơn giản trước"),
        "business.knowledge": (business, "## 10. Thư viện kiến thức"),
        "business.propagation": (business, "## 11. Yêu cầu liên kết và tính nhất quán"),
        "specification.legacy": (specification, "TÀI LIỆU KẾ THỪA"),
        "technical.operations": (technical, "### 5.2. Hợp đồng operation tối thiểu"),
        "technical.errors": (technical, "### 5.3. Error/recovery record chuẩn"),
        "technical.release": (technical, "### 13.2. Release manifest và rollback"),
        "technical.migration": (technical, "## 4. Mô hình nghiệp vụ đích và chuyển đổi dữ liệu"),
        "plan.dependencies": (plan, "### 2.1. Thứ tự bắt buộc, hoàn thành từng giai đoạn"),
        "plan.package_states": (plan, "### 2.2. Trạng thái công việc và bàn giao"),
        "plan.legacy_crosswalk": (plan, "## 3. Ma trận chuyển đổi phạm vi cũ sang UX1"),
    }
    for name, (document, marker) in required_markers.items():
        _check(checks, f"marker.{name}", marker in document, f"required={marker}")

    for phase in PHASES:
        phase_code = f"P{phase:02d}"
        phase_label = f"P{phase}"
        section = _phase_section(plan, phase)
        _check(
            checks,
            f"phase.{phase}.plan_heading",
            _has(rf"^## {phase_label} —", plan),
            f"heading=## {phase_label} —",
        )
        _check(
            checks,
            f"phase.{phase}.business_mapping",
            _has(rf"^\| {phase_label} \| FR-UX1-{phase_code}-01 \|", business),
            "UX1 requirement mapped in business table",
        )
        _check(
            checks,
            f"phase.{phase}.technical_mapping",
            _has(rf"^\| {phase_label} \|", technical),
            "phase mapped in current technical document, not legacy specification",
        )
        for heading in (
            f"### Trình tự triển khai {phase_label}",
            f"### Luồng thao tác {phase_label}",
            f"### Trường hợp chạy đúng {phase_label}",
            f"### Trường hợp lỗi và phục hồi {phase_label}",
            f"### Bất biến và điều kiện đóng {phase_label}",
        ):
            _check(
                checks,
                f"phase.{phase}.section.{heading[4:].lower().replace(' ', '_')}",
                heading in section,
                f"required={heading}",
            )
        if phase > 0:
            _check(
                checks,
                f"phase.{phase}.sequential_dependency",
                f"**Đầu vào/phụ thuộc:** P{phase - 1} đã hoàn thành và có bàn giao;" in section,
                "previous phase must be completed before the next phase starts",
            )
        _check(
            checks,
            f"phase.{phase}.success_tests",
            len(re.findall(rf"^- TC-UX1-{phase_code}-S\d+ — .+", section, re.MULTILINE)) >= 3,
            "at least 3 success scenarios inside the phase",
        )
        _check(
            checks,
            f"phase.{phase}.error_tests",
            len(re.findall(rf"^- TC-UX1-{phase_code}-E\d+ — .+", section, re.MULTILINE)) >= 3,
            "at least 3 error/recovery scenarios inside the phase",
        )
        _check(
            checks,
            f"phase.{phase}.fr_mapping",
            f"FR-UX1-{phase_code}-01" in section,
            "phase references its current business requirement",
        )
        for package in ("W01", "W02", "W03", "W04", "VERIFY", "HANDOFF"):
            _check(
                checks,
                f"phase.{phase}.package.{package.lower()}",
                _has(rf"^[-*] \[[ xX]\] {phase_code}-{package} — .+", section),
                f"package={phase_code}-{package}",
            )

    headings = re.findall(r"^## P(\d+) —", plan, re.MULTILINE)
    _check(checks, "phase.order_and_uniqueness",
           headings == [str(n) for n in PHASES], "P0..P20 appear exactly once in order")
    test_ids = re.findall(r"^- (TC-UX1-P\d{2}-[SE]\d+) —", plan, re.MULTILINE)
    _check(checks, "test_id.uniqueness", len(test_ids) == len(set(test_ids)),
           "each acceptance scenario has a distinct UX1 test id")
    pylinac_packages = (
        "P07-CAL", "P07-STAR", "P07-VMAT", "P07-CT", "P07-ACR",
        "P07-CHEESE", "P07-HELIOS", "P07-QUART", "P07-LOG", "P07-PF",
        "P07-WL", "P07-WLMT", "P07-PLANAR", "P07-FPA", "P07-FA",
        "P07-NUCLEAR", "P07-CONTRIB",
    )
    for child in pylinac_packages:
        _check(checks, f"pylinac_package.{child}", child in _phase_section(plan, 7),
               "all 16 main pylinac module families and public contrib QA are mandatory inside P7")
    for marker in ("PylinacAdapter", "PylinacCapabilityRegistry", "qa-image-worker", "pylinac_version"):
        _check(checks, f"pylinac.technical.{marker}", marker in technical,
               "pylinac integration boundary and provenance are explicit")
    _check(checks, "pylinac.plan.adapter", "PylinacAdapter" in _phase_section(plan, 7),
           "P7 implements pylinac through the RT-CONNECT adapter")
    for marker in (
        "Calibration", "Starshot", "VMAT", "CatPhan", "ACR Phantoms",
        "Cheese Phantoms", "GE Helios", "Quart", "Log Analyzer",
        "Picket Fence", "Winston–Lutz", "Winston–Lutz Multi-Target",
        "Planar Imaging", "Field Profile Analysis", "Field Analysis", "Nuclear",
        "One-Offs/Contrib QA", "QuasarLightRadScaling", "JawOrthogonality",
    ):
        _check(checks, f"pylinac.catalog.{marker}", marker in pylinac_catalog,
               "official pylinac main module family or public contrib QA is represented in the catalog")
    _check(checks, "pylinac.engine_policy",
           all("engine chính thức" in document for document in (business, technical, plan)),
           "business, technical and plan lock pylinac as the selected engine")
    _check(checks, "pylinac.gamma_ui",
           all("DTA (mm)" in document and "Chênh lệch liều (%)" in document
               for document in (business, technical, plan, pylinac_catalog)),
           "PSQA user interface exposes dose difference percent and DTA millimetres")
    _check(checks, "pylinac.gamma_3d_boundary",
           all("Gamma 3D" in document and "chỉ đọc" in document
               for document in (business, technical, plan, pylinac_catalog)),
           "new pylinac-only runs do not misrepresent legacy 3D Gamma")
    for name in ("business", "technical", "plan"):
        document = texts.get(name, "")
        for term in ("Picket Fence", "Starshot", "α/β", "105%/107%"):
            _check(checks, f"ux1.{name}.{term}", term in document,
                   "mandatory domain topic present; semantics require editorial review")
        for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document):
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith("#"):
                continue
            local_path = href.split("#", 1)[0]
            _check(checks, f"link.{name}.{href}", (root / local_path).is_file(),
                   "local link target exists")

    for marker in ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12", "B13", "B14"):
        _check(checks, f"coverage.{marker}", marker in plan and marker in business, "present in plan and business analysis")

    for gate in ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"):
        _check(checks, f"execution_gate.{gate}", gate in plan, "present in plan execution gates")

    required_artifacts = (
        root / "docs" / "runbooks" / "p20-initial-operations-package.md",
        root / "deployment" / "railway" / "production-runbook.md",
        root / "scripts" / "verify-public-deployment.ps1",
        root / "scripts" / "verify-local-backup-restore.py",
        root / "scripts" / "create-release-manifest.py",
        root / "scripts" / "release_manifest.py",
        root / "scripts" / "inspect-railway-provider-capabilities.ps1",
        root / "docs" / "pylinac-qa-catalog.md",
        root / "docs" / "design" / "knowledge-library.md",
        root / "docs" / "history" / "pre-ux-20260912" / "business-analysis.md",
        root / "docs" / "history" / "pre-ux-20260912" / "technical-specification.md",
        root / "docs" / "history" / "pre-ux-20260912" / "plan.md",
    )
    for path in required_artifacts:
        _check(
            checks,
            f"artifact.{path.relative_to(root).as_posix()}",
            path.is_file(),
            "required support artifact",
        )

    failed = [item for item in checks if not item["ok"]]
    return {
        "schema_version": "rt-connect.planning-contract-verification.v2",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(root),
        "document_versions": {
            name: _version(pattern, texts.get(name, ""))
            for name, (pattern, _expected) in expected_versions.items()
        },
        "phase_count": len(tuple(PHASES)),
        "acceptance_scenario_count": len(test_ids),
        "passed": not failed,
        "failed_check_count": len(failed),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    report = verify(root)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        output = args.output if args.output.is_absolute() else root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
