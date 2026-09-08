#!/usr/bin/env python3
"""Create or validate a redacted RT-CONNECT release manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_manifest import ManifestError, build_manifest, validate_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a fail-closed RT-CONNECT release manifest without secrets."
    )
    parser.add_argument("--verify-manifest", type=Path, help="validate an existing manifest")
    parser.add_argument("--release-id")
    parser.add_argument("--environment", choices=("staging", "production"))
    parser.add_argument("--source-sha")
    parser.add_argument("--schema-revision")
    parser.add_argument("--auth-environment")
    parser.add_argument("--database-environment")
    parser.add_argument("--api-deployment-id")
    parser.add_argument("--api-sha")
    parser.add_argument("--web-deployment-id")
    parser.add_argument("--web-sha")
    parser.add_argument("--worker-deployment-id")
    parser.add_argument("--worker-sha")
    parser.add_argument("--renderer-version")
    parser.add_argument("--gamma-engine-version")
    parser.add_argument("--dvh-engine-version")
    parser.add_argument("--biological-engine-version")
    parser.add_argument("--fixture", action="append", default=[])
    parser.add_argument("--local-test", action="append", default=[])
    parser.add_argument("--staging-test", action="append", default=[])
    parser.add_argument("--production-test", action="append", default=[])
    parser.add_argument("--backup-before-change")
    parser.add_argument("--rollback-target")
    parser.add_argument("--output", type=Path)
    return parser


def _required(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    required = (
        "release_id",
        "environment",
        "schema_revision",
        "auth_environment",
        "database_environment",
        "api_deployment_id",
        "api_sha",
        "web_deployment_id",
        "web_sha",
        "worker_deployment_id",
        "worker_sha",
        "renderer_version",
        "gamma_engine_version",
        "dvh_engine_version",
        "biological_engine_version",
        "backup_before_change",
        "rollback_target",
        "output",
    )
    missing = [name for name in required if getattr(args, name) in (None, "")]
    if missing:
        parser.error("missing required arguments: " + ", ".join(f"--{name.replace('_', '-')}" for name in missing))


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    if args.verify_manifest:
        try:
            manifest = json.loads(args.verify_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"manifest could not be read: {exc}", file=sys.stderr)
            return 2
        errors = validate_manifest(manifest)
        result = {"valid": not errors, "error_count": len(errors), "errors": errors}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not errors else 2

    _required(parser, args)
    try:
        manifest = build_manifest(
            repo_root=REPO_ROOT,
            release_id=args.release_id,
            environment=args.environment,
            source_sha=args.source_sha,
            schema_revision=args.schema_revision,
            auth_environment=args.auth_environment,
            database_environment=args.database_environment,
            services={
                "api": {"deployment_id": args.api_deployment_id, "sha": args.api_sha},
                "web": {"deployment_id": args.web_deployment_id, "sha": args.web_sha},
                "worker": {"deployment_id": args.worker_deployment_id, "sha": args.worker_sha},
            },
            renderer_version=args.renderer_version,
            engine_versions={
                "gamma": args.gamma_engine_version,
                "dvh": args.dvh_engine_version,
                "biological": args.biological_engine_version,
            },
            fixture_paths=args.fixture,
            tests={
                "local": args.local_test,
                "staging": args.staging_test,
                "production": args.production_test,
            },
            backup_before_change=args.backup_before_change,
            rollback_target=args.rollback_target,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ManifestError, OSError, TypeError) as exc:
        print(f"release manifest failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["release_gate"] == "ELIGIBLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
