"""Run a bounded local PostgreSQL and MinIO backup/restore verification.

The verifier is deliberately local-only.  It snapshots the local Compose
database and object bucket, restores both into disposable local resources, and
compares row/object inventories.  It never accepts a remote database or S3
endpoint, and it does not persist the dump or copied objects after the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from minio import Minio


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"
SOURCE_DATABASE = "rt_connect"
SOURCE_DB_USER = "rt_connect"
SOURCE_BUCKET = "rt-connect-artifacts"
S3_ENDPOINT = "127.0.0.1:9000"
S3_ACCESS_KEY = "local-development-only"
S3_SECRET_KEY = "local-development-only"
TABLES = (
    "organizations",
    "organization_memberships",
    "sites",
    "machines",
    "folders",
    "qa_cases",
    "artifacts",
    "input_manifests",
    "validation_runs",
    "machine_qa_runs",
    "gamma_analysis_runs",
    "dvh_analysis_runs",
    "report_revisions",
    "export_jobs",
    "trend_points",
    "biological_scenarios",
    "biological_calculation_runs",
    "biological_comparison_runs",
    "biological_reirradiation_runs",
    "audit_events",
)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_stream(response: Any) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        while chunk := response.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    finally:
        response.close()
        response.release_conn()
    return size, digest.hexdigest()


def _run_compose(*arguments: str, input_bytes: bytes | None = None) -> bytes:
    if shutil.which("docker") is None:
        raise RuntimeError("Docker CLI is not available on PATH.")
    command = ["docker", "compose", "-f", str(COMPOSE_FILE), *arguments]
    completed = subprocess.run(
        command,
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Docker Compose command failed ({arguments[0]}): {detail}")
    return completed.stdout


def _psql(database: str, sql: str) -> str:
    output = _run_compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        SOURCE_DB_USER,
        "-d",
        database,
        "-At",
        "-F",
        "\t",
        "-c",
        sql,
    )
    return output.decode("utf-8", errors="replace").strip()


def _row_counts(database: str) -> dict[str, int]:
    query = " UNION ALL ".join(
        f"SELECT '{table}', count(*)::bigint FROM {table}" for table in TABLES
    )
    rows = _psql(database, query)
    result: dict[str, int] = {}
    for line in rows.splitlines():
        table, count = line.split("\t", maxsplit=1)
        result[table] = int(count)
    missing = sorted(set(TABLES) - set(result))
    if missing:
        raise RuntimeError(f"Row-count query omitted tables: {', '.join(missing)}")
    return result


def _inventory_hash(counts: dict[str, int]) -> str:
    payload = json.dumps(counts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(payload)


def _object_inventory(client: Minio, bucket: str) -> tuple[dict[str, dict[str, Any]], str]:
    if not client.bucket_exists(bucket):
        raise RuntimeError(f"Object bucket does not exist: {bucket}")
    inventory: dict[str, dict[str, Any]] = {}
    for item in client.list_objects(bucket, recursive=True):
        size, digest = _sha256_stream(client.get_object(bucket, item.object_name))
        inventory[item.object_name] = {"bytes": size, "sha256": digest}
    payload = json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return inventory, _sha256_bytes(payload)


def _copy_bucket(
    client: Minio,
    source_bucket: str,
    restore_bucket: str,
    source_inventory: dict[str, dict[str, Any]],
    temp_root: Path,
) -> tuple[dict[str, dict[str, Any]], str]:
    restored_files = temp_root / "objects"
    restored_files.mkdir()
    for index, object_name in enumerate(sorted(source_inventory)):
        local_path = restored_files / f"object-{index:06d}.bin"
        client.fget_object(source_bucket, object_name, str(local_path))
        client.fput_object(
            restore_bucket,
            object_name,
            str(local_path),
            content_type="application/octet-stream",
        )

    return _object_inventory(client, restore_bucket)


def _restore_bucket_cleanup(client: Minio, bucket: str) -> None:
    for item in client.list_objects(bucket, recursive=True):
        client.remove_object(bucket, item.object_name)
    client.remove_bucket(bucket)


def _build_report(
    *,
    passed: bool,
    source_counts: dict[str, int] | None = None,
    restored_counts: dict[str, int] | None = None,
    dump_bytes: int = 0,
    dump_sha256: str | None = None,
    source_objects: int = 0,
    restored_objects: int = 0,
    source_object_inventory_sha256: str | None = None,
    restored_object_inventory_sha256: str | None = None,
    restore_database: str | None = None,
    restore_database_dropped: bool = False,
    restore_bucket: str | None = None,
    restore_bucket_removed: bool = False,
    error: str | None = None,
) -> dict[str, Any]:
    source_counts = source_counts or {}
    restored_counts = restored_counts or {}
    checks = [
        {
            "name": "database.row_inventory",
            "ok": bool(source_counts) and source_counts == restored_counts,
            "details": {
                "source_sha256": _inventory_hash(source_counts) if source_counts else None,
                "restored_sha256": _inventory_hash(restored_counts) if restored_counts else None,
            },
        },
        {
            "name": "object.inventory",
            "ok": (
                source_objects == restored_objects
                and source_object_inventory_sha256 is not None
                and source_object_inventory_sha256 == restored_object_inventory_sha256
            ),
            "details": {
                "source_count": source_objects,
                "restored_count": restored_objects,
                "source_sha256": source_object_inventory_sha256,
                "restored_sha256": restored_object_inventory_sha256,
            },
        },
        {
            "name": "disposable-resource-cleanup",
            "ok": restore_database_dropped and restore_bucket_removed,
            "details": {
                "restore_database": restore_database,
                "database_dropped": restore_database_dropped,
                "restore_bucket": restore_bucket,
                "bucket_removed": restore_bucket_removed,
            },
        },
    ]
    if error:
        checks.append({"name": "execution", "ok": False, "details": error})
    return {
        "schema_version": "rt-connect.local-backup-restore.v1",
        "captured_at_utc": _utc_now(),
        "environment": "local-compose-only",
        "compose_file": "docker-compose.yml",
        "source_database": SOURCE_DATABASE,
        "restore_database": restore_database,
        "database_dump": {"bytes": dump_bytes, "sha256": dump_sha256},
        "source_row_counts": source_counts,
        "restored_row_counts": restored_counts,
        "source_object_count": source_objects,
        "restored_object_count": restored_objects,
        "source_object_inventory_sha256": source_object_inventory_sha256,
        "restored_object_inventory_sha256": restored_object_inventory_sha256,
        "passed": passed and all(check["ok"] for check in checks),
        "checks": checks,
        "contains_patient_data": False,
        "error": error,
    }


def verify() -> dict[str, Any]:
    running_services = _run_compose("ps", "--services", "--filter", "status=running")
    services = set(running_services.decode("utf-8", errors="replace").split())
    required_services = {"postgres", "minio"}
    if not required_services.issubset(services):
        missing = ", ".join(sorted(required_services - services))
        raise RuntimeError(f"Required local Compose services are not running: {missing}")

    client = Minio(S3_ENDPOINT, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY, secure=False)
    restore_database = f"rt_connect_restore_{uuid4().hex[:12]}"
    restore_bucket = f"rt-connect-restore-{uuid4().hex[:16]}"
    restore_database_created = False
    restore_bucket_created = False
    source_counts: dict[str, int] = {}
    restored_counts: dict[str, int] = {}
    source_objects: dict[str, dict[str, Any]] = {}
    restored_objects: dict[str, dict[str, Any]] = {}
    source_object_hash: str | None = None
    restored_object_hash: str | None = None
    dump_bytes = b""
    database_dropped = False
    bucket_removed = False

    try:
        source_counts = _row_counts(SOURCE_DATABASE)
        source_objects, source_object_hash = _object_inventory(client, SOURCE_BUCKET)
        dump_bytes = _run_compose(
            "exec",
            "-T",
            "postgres",
            "pg_dump",
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "-U",
            SOURCE_DB_USER,
            "-d",
            SOURCE_DATABASE,
        )
        _run_compose("exec", "-T", "postgres", "createdb", "-U", SOURCE_DB_USER, restore_database)
        restore_database_created = True
        _run_compose(
            "exec",
            "-T",
            "postgres",
            "pg_restore",
            "--no-owner",
            "--no-acl",
            "-U",
            SOURCE_DB_USER,
            "-d",
            restore_database,
            input_bytes=dump_bytes,
        )
        restored_counts = _row_counts(restore_database)
        with tempfile.TemporaryDirectory(prefix="rt-connect-backup-") as temporary_directory:
            client.make_bucket(restore_bucket)
            restore_bucket_created = True
            restored_objects, restored_object_hash = _copy_bucket(
                client,
                SOURCE_BUCKET,
                restore_bucket,
                source_objects,
                Path(temporary_directory),
            )
            restore_bucket_created = True
    finally:
        if restore_bucket_created:
            try:
                _restore_bucket_cleanup(client, restore_bucket)
                bucket_removed = True
            except Exception as cleanup_error:  # pragma: no cover - defensive cleanup reporting
                print(f"WARNING: restore bucket cleanup failed: {cleanup_error}", file=sys.stderr)
        if restore_database_created:
            try:
                _run_compose(
                    "exec",
                    "-T",
                    "postgres",
                    "dropdb",
                    "--if-exists",
                    "-U",
                    SOURCE_DB_USER,
                    restore_database,
                )
                database_dropped = True
            except Exception as cleanup_error:  # pragma: no cover - defensive cleanup reporting
                print(f"WARNING: restore database cleanup failed: {cleanup_error}", file=sys.stderr)

    passed = (
        source_counts == restored_counts
        and source_objects == restored_objects
        and bucket_removed
        and database_dropped
    )
    return _build_report(
        passed=passed,
        source_counts=source_counts,
        restored_counts=restored_counts,
        dump_bytes=len(dump_bytes),
        dump_sha256=_sha256_bytes(dump_bytes) if dump_bytes else None,
        source_objects=len(source_objects),
        restored_objects=len(restored_objects),
        source_object_inventory_sha256=source_object_hash,
        restored_object_inventory_sha256=restored_object_hash,
        restore_database=restore_database,
        restore_database_dropped=database_dropped,
        restore_bucket=restore_bucket,
        restore_bucket_removed=bucket_removed,
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON evidence path relative to the repository root.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    try:
        report = verify()
    except Exception as error:
        report = _build_report(passed=False, error=str(error))

    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if arguments.output:
        target = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
