# RT-CONNECT API

Run commands from this directory after following the repository setup guide.

The API is a FastAPI service. P1 supplies only the platform boundaries: configuration,
health/readiness/version, correlation IDs, redacted structured logging, SQLAlchemy and
an Alembic baseline. Clinical modules are added in later phases.

## Deployment source parity

The public `/api/v1/version` response is the source of truth for the running API
commit. When the web service receives a web-only change, Railway may legitimately
skip the API deployment because of path filters. A release candidate is not
considered integrated until the API and web service report the same Git SHA and
schema revision in the staging smoke evidence.

The parity marker is intentionally kept under the API service root so a
web-only documentation commit cannot leave the API on an older candidate.
Every staging release must run the exact-SHA public verifier after both
service deployments settle.

P17 release marker: DVH explicit P16/P11 binding UI is released against the
same API contract; validate the selected source and result provenance in staging.

P19 evidence marker: the `ddfb434` public verifier result is recorded in the
repository progress log; keep API/web/worker source parity on the next release.
