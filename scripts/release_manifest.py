"""Build and validate redacted RT-CONNECT release manifests.

The manifest is deliberately independent from Railway and Supabase APIs.  It records
the evidence that an operator has supplied, computes fixture hashes locally, and fails
closed when a candidate is not safe to promote.  It never accepts or persists secrets.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping


MANIFEST_SCHEMA_VERSION = "rt-connect.release-manifest.v1"
REQUIRED_SERVICES = ("api", "web", "worker")
REQUIRED_ENGINES = ("gamma", "dvh", "biological")
SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,64}$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
SENSITIVE_PATTERN = re.compile(
    r"(?:password|passwd|secret|token|authorization|bearer|database_url|"
    r"supabase_service|s3_secret|postgres(?:ql)?://)",
    re.IGNORECASE,
)


class ManifestError(ValueError):
    """Raised when a release manifest cannot be safely built or validated."""


def canonical_json(value: Mapping[str, Any]) -> str:
    """Return the canonical JSON representation used for the manifest hash."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _validate_identifier(value: str, field: str) -> str:
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ManifestError(f"{field} has an invalid identifier format")
    return value


def _validate_sha(value: str, field: str) -> str:
    if not SHA_PATTERN.fullmatch(value):
        raise ManifestError(f"{field} must be a hexadecimal git SHA")
    return value.lower()


def _validate_safe_text(value: str, field: str) -> str:
    if not value or value.startswith("<") or value.endswith(">"):
        raise ManifestError(f"{field} must be a concrete non-placeholder value")
    if SENSITIVE_PATTERN.search(value):
        raise ManifestError(f"{field} contains a secret-like value and was rejected")
    return value


def _validate_json_strings(value: Any, path: str = "manifest") -> None:
    if isinstance(value, str):
        if SENSITIVE_PATTERN.search(value):
            raise ManifestError(f"{path} contains a secret-like value and was rejected")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _validate_json_strings(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_json_strings(child, f"{path}[{index}]")


def _git_value(repo_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ManifestError("unable to read git metadata") from exc
    return result.stdout.strip()


def _git_metadata(repo_root: Path) -> dict[str, Any]:
    source_sha = _validate_sha(_git_value(repo_root, "rev-parse", "HEAD"), "source_sha")
    branch = _git_value(repo_root, "branch", "--show-current") or "DETACHED_HEAD"
    clean = not bool(_git_value(repo_root, "status", "--porcelain"))
    return {"source_sha": source_sha, "branch": branch, "working_tree_clean": clean}


def _resolve_fixture(repo_root: Path, fixture: str) -> dict[str, Any]:
    candidate = Path(fixture)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(repo_root.resolve()).as_posix()
    except (FileNotFoundError, ValueError) as exc:
        raise ManifestError(f"fixture is missing or outside repository: {fixture}") from exc
    if not resolved.is_file():
        raise ManifestError(f"fixture is not a file: {fixture}")
    content = resolved.read_bytes()
    return {"path": relative, "bytes": len(content), "sha256": _sha256_bytes(content)}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _service(service: str, deployment_id: str, sha: str) -> dict[str, str]:
    return {
        "deployment_id": _validate_safe_text(deployment_id, f"services.{service}.deployment_id"),
        "sha": _validate_sha(sha, f"services.{service}.sha"),
    }


def build_manifest(
    *,
    repo_root: Path,
    release_id: str,
    environment: str,
    schema_revision: str,
    auth_environment: str,
    database_environment: str,
    source_sha: str | None,
    services: Mapping[str, Mapping[str, str]],
    renderer_version: str,
    engine_versions: Mapping[str, str],
    fixture_paths: list[str],
    tests: Mapping[str, list[str]],
    backup_before_change: str,
    rollback_target: str,
) -> dict[str, Any]:
    """Build a manifest and explicitly calculate whether it is promotable."""

    if environment not in {"staging", "production"}:
        raise ManifestError("environment must be staging or production")
    if auth_environment != environment or database_environment != environment:
        raise ManifestError("auth_environment and database_environment must match environment")
    _validate_identifier(release_id, "release_id")
    _validate_safe_text(schema_revision, "schema_revision")
    _validate_safe_text(renderer_version, "services.renderer.version")
    _validate_safe_text(backup_before_change, "backup_before_change")
    _validate_safe_text(rollback_target, "rollback_target")

    git_metadata = _git_metadata(repo_root)
    effective_source_sha = _validate_sha(source_sha, "source_sha") if source_sha else git_metadata["source_sha"]
    normalized_services: dict[str, dict[str, str]] = {}
    for service_name in REQUIRED_SERVICES:
        service_values = services.get(service_name)
        if service_values is None:
            raise ManifestError(f"missing service metadata: {service_name}")
        deployment_id = service_values.get("deployment_id")
        service_sha = service_values.get("sha")
        if not deployment_id or not service_sha:
            raise ManifestError(f"incomplete service metadata: {service_name}")
        normalized_services[service_name] = _service(service_name, deployment_id, service_sha)

    normalized_engines: dict[str, str] = {}
    for engine_name in REQUIRED_ENGINES:
        version = engine_versions.get(engine_name)
        if not version:
            raise ManifestError(f"missing engine version: {engine_name}")
        normalized_engines[engine_name] = _validate_safe_text(version, f"engine_versions.{engine_name}")

    normalized_tests: dict[str, list[str]] = {}
    for environment_name in ("local", "staging", "production"):
        values = tests.get(environment_name, [])
        if not all(value and not SENSITIVE_PATTERN.search(value) for value in values):
            raise ManifestError(f"tests.{environment_name} contains an invalid value")
        normalized_tests[environment_name] = _unique(values)

    service_shas = {service["sha"] for service in normalized_services.values()}
    service_sha_parity = len(service_shas) == 1 and next(iter(service_shas)) == effective_source_sha
    gate_reasons: list[str] = []
    if not git_metadata["working_tree_clean"]:
        gate_reasons.append("WORKING_TREE_DIRTY")
    if not service_sha_parity:
        gate_reasons.append("SERVICE_SOURCE_SHA_MISMATCH")
    release_gate = "ELIGIBLE" if not gate_reasons else "RELEASE_BLOCKED"

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "release_id": release_id,
        "environment": environment,
        "source_sha": effective_source_sha,
        "source_state": {
            "branch": git_metadata["branch"],
            "working_tree_clean": git_metadata["working_tree_clean"],
        },
        "services": {
            **normalized_services,
            "renderer": {"version": renderer_version},
        },
        "schema_revision": schema_revision,
        "engine_versions": normalized_engines,
        "auth_environment": auth_environment,
        "database_environment": database_environment,
        "fixture_hashes": [_resolve_fixture(repo_root, fixture) for fixture in sorted(fixture_paths)],
        "tests": normalized_tests,
        "backup_before_change": backup_before_change,
        "rollback_target": rollback_target,
        "service_sha_parity": service_sha_parity,
        "release_gate": release_gate,
        "gate_reasons": gate_reasons,
    }
    _validate_json_strings(manifest)
    manifest["manifest_sha256"] = _sha256_bytes(canonical_json(manifest).encode("utf-8"))
    return manifest


def validate_manifest(manifest: Mapping[str, Any]) -> list[str]:
    """Return all structural/integrity violations without mutating the input."""

    errors: list[str] = []
    if not isinstance(manifest, Mapping):
        return ["manifest must be an object"]
    try:
        _validate_json_strings(manifest)
    except ManifestError as exc:
        errors.append(str(exc))

    required = (
        "schema_version",
        "release_id",
        "environment",
        "source_sha",
        "services",
        "schema_revision",
        "engine_versions",
        "auth_environment",
        "database_environment",
        "fixture_hashes",
        "tests",
        "backup_before_change",
        "rollback_target",
        "service_sha_parity",
        "release_gate",
        "gate_reasons",
        "manifest_sha256",
    )
    for field in required:
        if field not in manifest:
            errors.append(f"missing field: {field}")

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append("schema_version is unsupported")
    environment = manifest.get("environment")
    if environment not in {"staging", "production"}:
        errors.append("environment must be staging or production")
    if manifest.get("auth_environment") != environment:
        errors.append("auth_environment does not match environment")
    if manifest.get("database_environment") != environment:
        errors.append("database_environment does not match environment")

    source_sha = manifest.get("source_sha")
    if not isinstance(source_sha, str) or not SHA_PATTERN.fullmatch(source_sha):
        errors.append("source_sha is invalid")

    services = manifest.get("services")
    service_shas: set[str] = set()
    if not isinstance(services, Mapping):
        errors.append("services must be an object")
    else:
        for service_name in REQUIRED_SERVICES:
            value = services.get(service_name)
            if not isinstance(value, Mapping):
                errors.append(f"services.{service_name} must be an object")
                continue
            if not isinstance(value.get("deployment_id"), str) or not value.get("deployment_id"):
                errors.append(f"services.{service_name}.deployment_id is missing")
            service_sha = value.get("sha")
            if not isinstance(service_sha, str) or not SHA_PATTERN.fullmatch(service_sha):
                errors.append(f"services.{service_name}.sha is invalid")
            else:
                service_shas.add(service_sha.lower())
        renderer = services.get("renderer")
        if not isinstance(renderer, Mapping) or not isinstance(renderer.get("version"), str):
            errors.append("services.renderer.version is missing")

    if service_shas and isinstance(source_sha, str) and SHA_PATTERN.fullmatch(source_sha):
        expected_parity = len(service_shas) == 1 and next(iter(service_shas)) == source_sha.lower()
        if manifest.get("service_sha_parity") is not expected_parity:
            errors.append("service_sha_parity does not match service/source SHAs")

    engine_versions = manifest.get("engine_versions")
    if not isinstance(engine_versions, Mapping):
        errors.append("engine_versions must be an object")
    else:
        for engine_name in REQUIRED_ENGINES:
            if not isinstance(engine_versions.get(engine_name), str) or not engine_versions.get(engine_name):
                errors.append(f"engine_versions.{engine_name} is missing")

    tests = manifest.get("tests")
    if not isinstance(tests, Mapping):
        errors.append("tests must be an object")
    else:
        for environment_name in ("local", "staging", "production"):
            if not isinstance(tests.get(environment_name), list):
                errors.append(f"tests.{environment_name} must be an array")

    if isinstance(manifest.get("manifest_sha256"), str):
        unsigned = dict(manifest)
        unsigned.pop("manifest_sha256", None)
        expected_hash = _sha256_bytes(canonical_json(unsigned).encode("utf-8"))
        if manifest["manifest_sha256"] != expected_hash:
            errors.append("manifest_sha256 does not match canonical content")

    if manifest.get("release_gate") == "ELIGIBLE" and manifest.get("gate_reasons") != []:
        errors.append("ELIGIBLE manifest must have no gate_reasons")
    if manifest.get("release_gate") == "RELEASE_BLOCKED" and not isinstance(manifest.get("gate_reasons"), list):
        errors.append("RELEASE_BLOCKED manifest must have gate_reasons")
    return errors
