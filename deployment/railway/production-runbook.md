# RT-CONNECT — Production promotion and rollback runbook

This runbook is a production release procedure. It is not permission to promote the
current staging candidate. Execute it only after P18 release-candidate, backup/restore,
remote E2E and P19 entry gates are recorded as PASS in the release manifest.

## 1. Required release packet

The operator must have one immutable packet containing:

- approved candidate source commit and image/artifact digests;
- API, web, worker and renderer version labels;
- current and target Alembic schema revisions;
- effective environment/service IDs, root directories and start commands;
- redacted Auth issuer/audience/JWKS and exact web redirect origins;
- CORS origins and public domain/TLS evidence;
- PostgreSQL backup/snapshot ID and object-storage inventory/checksum;
- P18 integrated, golden, fault/load and restore evidence;
- P19 remote browser evidence and rollback decision;
- operator, timestamp, correlation IDs and known limitations.

Never put `DATABASE_URL`, Railway tokens, Supabase service-role keys, S3 secret keys,
passwords, cookies or patient data in this packet.

## 2. Preflight

1. Confirm the Railway environment is production and the selected services are the intended
   API, web and worker; do not operate on staging by URL similarity.
2. Confirm the candidate SHA is the same artifact tested in staging. A public build label
   alone is insufficient.
3. Confirm PostgreSQL and object-storage backup points are complete and queryable.
4. Confirm the migration is expand/contract compatible with the currently running web and
   worker. Do not plan a destructive automatic downgrade.
5. Confirm worker has no public domain or HTTP healthcheck; only the API is checked through
   HTTP.
6. Confirm production CORS contains only the intended HTTPS web origin and Supabase
   redirect configuration has no staging origin unless explicitly required.
7. Confirm no secret or database credential is present in the frontend artifact.
8. Record the pre-release `/health`, `/ready`, `/version`, service status and backup IDs.

If any check is uncertain, stop with `RELEASE_EVIDENCE_MISMATCH` or
`PUBLIC_BUILD_CONFIG_MISMATCH`; do not continue based on a green Railway status badge.

## 3. Promotion order

Use the order below only when the release packet says it is compatible:

1. Apply the expand migration through the single designated migration runner.
2. Verify schema/readiness before starting dependent consumers.
3. Deploy API candidate and verify health, readiness, version and effective configuration.
4. Deploy worker candidate with the same engine/schema compatibility and private dependencies.
5. Deploy/rebuild frontend with production `VITE_API_BASE_URL`, Supabase URL/key and build
   label. Frontend must never receive private backend credentials.
6. Run public smoke, then authenticated remote E2E from an external network:
   login/callback, deep-link, organization context, QA case, upload, validation, job,
   reconnect/refresh, report/download and independent Biological Toolkit workflow.
7. Check API/worker/web/schema/engine/renderer parity against the manifest.
8. Record final URLs, deployment IDs, request/correlation IDs, observed results and
   monitoring state.

## 4. Rollback decision

Rollback is required when any of these occurs:

- public domain/TLS/CORS/Auth is not ready;
- migration/readiness fails or schema is incompatible;
- web/API/worker/build labels or source digests are inconsistent;
- health is green but a required remote workflow fails;
- accepted jobs are lost, duplicated or cannot be reconciled;
- resource/cost boundary is exceeded without a controlled mitigation;
- backup/restore or evidence checksum does not match the packet.

### 4.1. Application rollback

1. Stop new promotion and keep the last-good release packet.
2. Prevent new workload only through the documented maintenance mechanism; do not delete
   existing runs or objects.
3. Restore the last-good API/web/worker artifact that is compatible with the already applied
   schema.
4. Verify health/readiness/version, Auth/CORS and one read-only history/download workflow.
5. Reconcile accepted jobs by operation/idempotency key; do not enqueue duplicates blindly.
6. Record rollback deployment IDs, observed errors, data-integrity checks and next action.

### 4.2. Schema/data incompatibility

Do not run an automatic destructive migration downgrade. Keep the database backup and
last-good data untouched, isolate the incompatible candidate, and choose one of:

- deploy a compatible application that understands the expanded schema;
- restore to an isolated copy, verify counts/checksums/lineage, then follow the separately
  approved recovery decision;
- fix the migration/application and create a new candidate with new evidence.

## 5. Post-release checks

Run the same checks after a quiet period and after the first synthetic workflow:

- public HTTPS and SPA deep-link;
- `/health`, `/ready`, `/version` and schema revision;
- Supabase sign-in/refresh/logout and redirect origin;
- API CORS and no public database/Redis/worker/bucket;
- queue pending/failed/retry metrics;
- synthetic report download and checksum;
- old report/result/history readback;
- backup schedule and alert delivery;
- cost/resource snapshot.

If the only successful observation is `HTTP 200`, the release remains unverified.

## 6. Handoff record

```text
release_id: REL-<date>-<sequence>
environment: production
candidate_sha:
api_deployment_id:
web_deployment_id:
worker_deployment_id:
schema_revision:
engine_version:
renderer_version:
public_web_url:
public_api_url:
backup_id:
remote_e2e_evidence:
rollback_packet:
monitoring_alert_evidence:
known_limitations:
operator:
handoff_time_utc:
```

The current RT-CONNECT repository has public staging smoke evidence, but this production
runbook remains a target handoff artifact until P18/P19 gates and P20 operations evidence
are complete.
