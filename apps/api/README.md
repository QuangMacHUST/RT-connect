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

P19 evidence marker: the `dd14ef8` public verifier and P17 negative-path
recheck are recorded in the repository evidence/progress log. The current
production public gap is recorded separately; keep API/web/worker source
parity on the next release.

Latest staging parity evidence: `p19-staging-public-smoke-20260909-38dec53.json`
records API, worker and web source SHA `38dec53d4e542bdf6c4f808283981b344cae3502`
with schema `20260909_0019`; keep this marker aligned when progress/evidence changes.

Current P17 staging fixture marker: the authenticated case recheck keeps the
synthetic RTDOSE/RTSTRUCT/CT set and saved DVH run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`.
This marker is intentionally duplicated under the API service root so a release
commit that records P17 evidence rebuilds API and worker together with the web.

P17-W06 resource-evidence parity marker: local workload verification pins the API
container to 1 CPU/768 MiB and records process RSS plus API responsiveness. Keep
this marker aligned with the web service root so a release candidate rebuilds all
three services from the same source commit.

Final staging parity marker (2026-09-10): API, worker and web must be rebuilt
from the commit carrying this marker before a public exact-SHA check is recorded.
