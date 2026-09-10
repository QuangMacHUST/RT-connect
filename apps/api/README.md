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

Latest staging parity evidence: `p19-staging-public-smoke-20260910-85ecb0e.json`
records API, worker and web source SHA `85ecb0ebb025220a79cc82977049d2e16340efb0`
with schema `20260909_0019`; keep this marker aligned when progress/evidence changes.

Current P17 staging fixture marker: the authenticated case recheck keeps the
synthetic RTDOSE/RTSTRUCT/CT set and saved DVH run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`.
This marker is intentionally duplicated under the API service root so a release
commit that records P17 evidence rebuilds API and worker together with the web.

P17-W06 resource-evidence parity marker: local workload verification pins the API
container to 1 CPU/768 MiB and records process RSS plus API responsiveness. Keep
this marker aligned with the web service root so a release candidate rebuilds all
three services from the same source commit.

P8 staging marker: the existing synthetic RTDOSE reference was rechecked through
the authenticated Gamma workspace with the 3D measurement fixture; the saved run
reported `8/8 PASS`. The corresponding browser evidence is
`p8-staging-rtdose-browser-20260910-85ecb0e.json`, and the local independent-oracle
evidence is `p8-independent-gamma-oracle.json` with `6/6` cases PASS.

Local queue marker: `docker-compose.yml` includes a separate bounded `worker` service. The
disposable verifier `scripts/verify-local-gamma-queue.py` exercises Redis Stream dispatch,
durable result persistence, terminal replay protection, three bounded storage-failure attempts,
dead-letter quarantine and queue acknowledgement. Evidence is local Compose support only; it
does not replace staging fault injection, Railway capacity evidence or clinical release gates.

Final staging parity marker (2026-09-10): API, worker and web must be rebuilt
from the commit carrying this marker before a public exact-SHA check is recorded.
P19 candidate rebuild marker (2026-09-10): this line is intentionally under
`/apps/api` so Railway services rooted at `/apps/api` cannot remain on an older
source SHA when the release evidence changes at repository root.
Staging manifest checkpoint: `d2a5a6b22267d153f26764596b36c78118f67ffa`
was verified across API, web and worker; keep this service-root marker aligned
with the next release evidence commit.

Parity follow-up checkpoint (2026-09-10): documentation evidence commit
`e1336b7ed3ad49b6683f9234bde3d9c22d1a885f` caused the web service to rebuild
before the API/worker services. Rebuild all three services from the next
commit carrying this marker and reissue the release manifest only after exact
SHA parity is observed.

Current staging parity checkpoint (2026-09-10): the artifact-upload compensation
fix is carried by `ebf1e664c55974b6bc418ff05791edfa5ace93f7`. The public verifier
recorded health/readiness/schema `20260909_0019`, organization boundary checks,
CT/membership markers and source parity at 15/15. Any later documentation or
evidence commit must rebuild API, worker and web before being called the current
candidate; the synthetic RTDOSE in the staging case is already present and must
not be duplicated.

P10 trend budget marker (2026-09-10): raw trend reads are bounded by
`TREND_MAX_RAW_POINTS`, while day/week aggregation has the separate
`TREND_MAX_AGGREGATE_SOURCE_POINTS` budget. Count-preflight happens before ORM
materialization; oversized requests return `TREND_QUERY_TOO_LARGE`, and aggregate
CSV rows preserve bucket statistics plus source point/run lineage. Rebuild all
three services from the commit carrying this marker before reusing P10 evidence.

P10 bounded-error UX marker (2026-09-10): the structured trend budget details
(`aggregate`, `matched_points`, `max_points`) remain part of the client-visible
error contract. Keep API, worker and web on the same candidate when this contract
or its user guidance changes.

P10 SQL preflight marker (2026-09-10): trend context filters are applied during
the bounded SQL source read as well as in the final Python compatibility matcher;
`qa_cycle` and `protocol_key` retain authoritative case/protocol fallbacks for
legacy projections. Rebuild all three services when this read path changes.

P09 export compensation marker (2026-09-10): export metadata persistence now has
an exact-key object cleanup/reconciliation contract and regression coverage for
final-commit failure. The commit carrying this marker must rebuild API, worker and
web before staging parity is rechecked; local evidence is not a provider restore
or clinical-readiness claim.

Current staging evidence marker (2026-09-10): release manifest
`docs/evidence/release-manifest-staging-4c9bc1b.json` records the exact staging
candidate `4c9bc1bb4838e2864e605ab4fa69c698ecd0759e` and the existing synthetic
RTDOSE/RTSTRUCT/CT fixture hashes. This marker intentionally lives under
`/apps/api` so API, worker and web are rebuilt before the evidence is reused.

P07 explicit-N/A marker (2026-09-10): Machine QA now carries an explicit
`is_not_applicable` flag and trimmed `na_reason`; the N/A metric is excluded from
trend projection and cannot turn an overall failed run into PASS. Rebuild all
three services from the commit carrying this marker before reusing the P07
staging candidate.

P11 consumer-snapshot marker (2026-09-10): Machine QA run creation pins
`p11.protocol-snapshot.v1` with source, applicability, capability and rule
references; evaluation is fail-closed on definition mismatch while allowing the
accepted ACTIVE snapshot to be evaluated after archive. Trend and report keep
the pinned protocol lineage. Rebuild API, worker and web from the same commit
before reusing a P11 staging candidate.
