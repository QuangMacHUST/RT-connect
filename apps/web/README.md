# RT-CONNECT Web

The web app uses React, TypeScript and Vite. P1 deliberately exposes only the platform
status route; clinical workflows are added phase by phase after their backend contracts,
data migrations and tests exist.

## Deployment source parity

The rendered build exposes its Git SHA through the build footer and bundle metadata.
Railway may skip this service for API-only changes, so a staging release is accepted
only after the web bundle SHA, `/api/v1/version` SHA, and schema revision agree in
the public smoke evidence.

Keep the parity marker in this service root as well; the API and web staging
deployments must advance from the same release commit before public recheck.
The verifier result is a release gate, not just a visual browser check.

P17 release marker: DVH exposes explicit P16/P11 source binding against the
same API contract; validate the selected source and result provenance in staging.

P19 evidence marker: the `dd14ef8` public verifier and P17 negative-path
recheck are recorded in the repository evidence/progress log. The current
production public gap is recorded separately; keep API/web/worker source
parity on the next release.

P4 regression marker: the current backend candidate includes local coverage for
email-bound invitation revoke and expiry/reissue lifecycle. Keep this marker in
the web service root so the API, worker and web services are rebuilt from the
same commit before the next public source-parity check.

Latest staging parity evidence: `p19-staging-public-smoke-20260910-85ecb0e.json`
records API, worker and web source SHA `85ecb0ebb025220a79cc82977049d2e16340efb0`
with schema `20260909_0019`; keep this marker aligned when progress/evidence changes.

Current P17 staging fixture marker: the authenticated case recheck keeps the
synthetic RTDOSE/RTSTRUCT/CT set and saved DVH run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`.
This marker is intentionally duplicated under the web service root so the
release candidate is rebuilt with the same source commit across API, worker and web.

P17-W06 resource-evidence parity marker: local workload verification pins the API
container to 1 CPU/768 MiB and records process RSS plus API responsiveness. Keep
this marker aligned with the API service root so a release candidate rebuilds all
three services from the same source commit.

P8 staging marker: the existing synthetic RTDOSE reference was rechecked through
the authenticated Gamma workspace with the 3D measurement fixture; the saved run
reported `8/8 PASS`. The corresponding browser evidence is
`p8-staging-rtdose-browser-20260910-85ecb0e.json`, and the local independent-oracle
evidence is `p8-independent-gamma-oracle.json` with `6/6` cases PASS.

Local queue marker: the repository Compose stack now includes the separate Gamma worker needed
to consume Redis-dispatched runs. `scripts/verify-local-gamma-queue.py` records local-only
happy-path, replay, bounded-retry and dead-letter evidence; do not interpret it as staging or
production verification.

Final staging parity marker (2026-09-10): API, worker and web must be rebuilt
from the commit carrying this marker before a public exact-SHA check is recorded.

P10 trend budget marker (2026-09-10): the trend UI must surface raw versus
day/week aggregation limits and the large-query warning, while aggregate export
retains bucket statistics and source point/run lineage. Keep this marker aligned
with the API service root and recheck the public exact-SHA candidate after all
three services rebuild.

P07 explicit-N/A marker (2026-09-10): the Machine QA UI exposes the N/A checkbox,
requires a reason, disables the numeric field while selected, and displays the
reason/status in the result. Keep this marker aligned with the API service root
so all three services are rebuilt from the same source commit.
