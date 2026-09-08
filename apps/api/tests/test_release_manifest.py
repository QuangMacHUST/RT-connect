from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "create-release-manifest.py"
SOURCE_SHA = "a" * 40


def _run_manifest(output: Path, fixture: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    arguments = [
        sys.executable,
        str(SCRIPT),
        "--release-id",
        "R-test-20260909-001",
        "--environment",
        "staging",
        "--source-sha",
        SOURCE_SHA,
        "--schema-revision",
        "20260908_0017",
        "--auth-environment",
        "staging",
        "--database-environment",
        "staging",
        "--api-deployment-id",
        "api-deployment",
        "--api-sha",
        SOURCE_SHA,
        "--web-deployment-id",
        "web-deployment",
        "--web-sha",
        SOURCE_SHA,
        "--worker-deployment-id",
        "worker-deployment",
        "--worker-sha",
        SOURCE_SHA,
        "--renderer-version",
        "renderer-test-1",
        "--gamma-engine-version",
        "gamma-test-1",
        "--dvh-engine-version",
        "dvh-test-1",
        "--biological-engine-version",
        "biological-test-1",
        "--fixture",
        str(fixture),
        "--local-test",
        "TC-P19-S01",
        "--staging-test",
        "TC-P19-S02",
        "--backup-before-change",
        "backup-test-1",
        "--rollback-target",
        "R-last-good",
        "--output",
        str(output),
        *extra,
    ]
    return subprocess.run(arguments, cwd=REPO_ROOT, capture_output=True, text=True, check=False)


def test_release_manifest_is_deterministic_and_valid(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text('{"fixture":"ok"}', encoding="utf-8")
    output = tmp_path / "manifest.json"

    result = _run_manifest(output, fixture)

    assert result.returncode == 0, result.stderr
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["release_gate"] == "ELIGIBLE"
    assert manifest["service_sha_parity"] is True
    assert manifest["fixture_hashes"][0]["bytes"] == 16

    verified = subprocess.run(
        [sys.executable, str(SCRIPT), "--verify-manifest", str(output)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["valid"] is True


def test_mixed_service_sha_is_written_but_blocks_promotion(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text("fixture", encoding="utf-8")
    output = tmp_path / "blocked.json"

    result = _run_manifest(output, fixture, "--web-sha", "b" * 40)

    assert result.returncode == 2
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["release_gate"] == "RELEASE_BLOCKED"
    assert manifest["gate_reasons"] == ["SERVICE_SOURCE_SHA_MISMATCH"]


def test_secret_like_backup_reference_is_rejected(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.json"
    fixture.write_text("fixture", encoding="utf-8")
    output = tmp_path / "rejected.json"

    result = _run_manifest(output, fixture, "--backup-before-change", "postgresql://secret")

    assert result.returncode == 2
    assert not output.exists()
    assert "secret-like" in result.stderr
