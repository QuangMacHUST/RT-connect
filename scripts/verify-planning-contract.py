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


def verify(root: Path) -> dict[str, object]:
    paths = {
        "business": root / "business-analysis.md",
        "specification": root / "specification.md",
        "technical": root / "technical-specification.md",
        "plan": root / "plan.md",
        "progress": root / "implementation-progress.md",
    }
    texts: dict[str, str] = {}
    checks: list[dict[str, object]] = []

    for name, path in paths.items():
        exists = path.is_file()
        _check(checks, f"file.{name}", exists, str(path.relative_to(root)))
        if exists:
            texts[name] = path.read_text(encoding="utf-8")

    expected_versions = {
        "business": (r"\*\*Phiên bản tài liệu:\*\*\s*([0-9]+\.[0-9]+)", "0.22"),
        "specification": (r"version \*\*([0-9]+\.[0-9]+)\*\*", "1.19"),
        "technical": (r"\*\*Phiên bản:\*\*\s*([0-9]+\.[0-9]+)", "1.18"),
        "plan": (r"Phiên bản:\s*\*\*([0-9]+\.[0-9]+)\*\*", "4.8"),
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
        "business": "plan.md v4.8",
        "specification": "plan.md v4.8",
        "technical": "plan.md v4.8",
        "progress": "plan.md v4.8",
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

    required_markers = {
        "business.feature_card": (business, "## 23. Hợp đồng bàn giao nghiệp vụ v0.22"),
        "business.p4_addendum": (business, "## 24. Đặc tả nghiệp vụ bổ sung P4"),
        "business.change_propagation": (business, "### 23.5. Quy tắc lan truyền thay đổi"),
        "specification.operation_contract": (specification, "### 14.1. Hợp đồng operation tối thiểu"),
        "specification.error_record": (specification, "### 14.2. Error/recovery record chuẩn"),
        "specification.release_manifest": (specification, "### 14.5. Quy tắc phát hành dựa trên manifest"),
        "plan.dependency_graph": (plan, "### 2.1. Đồ thị phụ thuộc bắt buộc và các lane có thể chạy song song"),
        "plan.package_states": (plan, "### 2.2. Quy tắc phân rã và trạng thái work package"),
    }
    for name, (document, marker) in required_markers.items():
        _check(checks, f"marker.{name}", marker in document, f"required={marker}")

    for phase in PHASES:
        phase_code = f"P{phase:02d}"
        phase_label = f"P{phase}"
        _check(
            checks,
            f"phase.{phase}.plan_heading",
            _has(rf"^## {phase_label} —", plan),
            f"heading=## {phase_label} —",
        )
        _check(
            checks,
            f"phase.{phase}.business_heading",
            _has(rf"^#### {phase_label} —", business),
            f"heading=#### {phase_label} —",
        )
        _check(
            checks,
            f"phase.{phase}.spec_heading",
            _has(rf"^### SPEC-{phase_code} —", specification),
            f"heading=### SPEC-{phase_code} —",
        )
        for heading in (
            f"### Workflow {phase_label}",
            f"### Trường hợp chạy đúng {phase_label}",
            f"### Trường hợp lỗi và phục hồi {phase_label}",
            f"### Bất biến và điều kiện đóng {phase_label}",
        ):
            _check(
                checks,
                f"phase.{phase}.section.{heading[4:].lower().replace(' ', '_')}",
                heading in plan,
                f"required={heading}",
            )
        _check(
            checks,
            f"phase.{phase}.success_tests",
            _has(rf"TC-{phase_code}-S\d+", plan),
            f"pattern=TC-{phase_code}-Sxx",
        )
        _check(
            checks,
            f"phase.{phase}.error_tests",
            _has(rf"TC-{phase_code}-E\d+", plan),
            f"pattern=TC-{phase_code}-Exx",
        )
        _check(
            checks,
            f"phase.{phase}.fr_mapping",
            _has(rf"FR-{phase_code}-0[1-4]", business),
            f"pattern=FR-{phase_code}-01..04",
        )
        for package in ("W01", "W02", "W03", "W04", "VERIFY", "HANDOFF"):
            _check(
                checks,
                f"phase.{phase}.package.{package.lower()}",
                _has(rf"^[-*] \[[ xX]\] {phase_code}-{package}(?:\s|—|-)", plan),
                f"package={phase_code}-{package}",
            )

    for marker in ("B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "B10", "B11", "B12"):
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
        "schema_version": "rt-connect.planning-contract-verification.v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": str(root),
        "document_versions": {
            name: _version(pattern, texts.get(name, ""))
            for name, (pattern, _expected) in expected_versions.items()
        },
        "phase_count": len(tuple(PHASES)),
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
