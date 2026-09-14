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

P5 parity rebuild marker (2026-09-14): root-level P5 implementation progress and
evidence updates must be accompanied by a change under this service root. This
marker exists to keep the web rebuild coupled to the API and Gamma worker
candidate. Do not record a new staging release until the web bundle, API and
worker report the same source SHA and schema.

P5 parity follow-up marker: the commit carrying the next root-level evidence
update must change this file together with the API service marker, then rerun the
public exact-SHA verifier after all three services settle.

P5 parity evidence checkpoint: the latest verifier result is recorded with the
root progress update in this commit; rebuild all three services and rerun the
verifier before treating this checkpoint as the current release candidate.

P5 parity recheck marker: the current evidence packet was verified against the
candidate that carried it. Any subsequent root-level progress update must again
touch both service-root markers and repeat the exact-SHA public check.

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

P10 bounded-error UX marker (2026-09-10): Trend displays the structured
`aggregate`/`matched_points`/`max_points` guidance returned by the API when a
query exceeds its budget; do not reduce this response to a code-only toast.

P10 SQL preflight marker (2026-09-10): the web relies on the API's bounded
context-filtered source read and does not implement a client-side large-series
fallback or silent truncation. Keep this marker aligned with `/apps/api`.

P07 explicit-N/A marker (2026-09-10): the Machine QA UI exposes the N/A checkbox,
requires a reason, disables the numeric field while selected, and displays the
reason/status in the result. Keep this marker aligned with the API service root
so all three services are rebuilt from the same source commit.

P11 consumer-snapshot marker (2026-09-10): the Machine QA source panel reads
protocol revision/source/applicability/rule count from the persisted run snapshot,
and the normal workflow links to QA Protocol Library instead of seeding a
synthetic protocol. Keep this marker aligned with the API service root so all
three services are rebuilt from the same source commit.

P11 staging parity rebuild marker (2026-09-10): the web is rebuilt together
with the API and worker after the watched API marker changes; verify exact
source SHA and the public bundle before reusing the staging candidate.

P5 purge-guard regression marker (2026-09-14): the API archive contract now
has an independent regression for a stored input artifact that blocks
permanent purge. Keep this marker aligned with `/apps/api` so all three
services are rebuilt from the same source commit before staging verification.

P5 input-artifact evidence checkpoint (2026-09-14): the repository evidence
records the independent stored-input purge guard and the 218-test API
regression. Keep this watched marker aligned with `/apps/api` so all three
services are rebuilt from the same source commit before staging verification.

P5 staging parity evidence commit (2026-09-14): the public recheck evidence
for the artifact-guard candidate is committed at repository root. Rebuild the
web together with API and worker from the same revision before staging review.

P5 current staging verification checkpoint (2026-09-14): the recorded public
verification belongs to the preceding source revision; rebuild web, API and
worker from the final repository revision before release review.

P5 read-only purge preview UI (2026-09-14): the web exposes a separate
preview action for archived cases so linked-data protection can be checked
without invoking permanent deletion. Keep this marker aligned with the API
service so all three services are rebuilt from the same revision.

P5 linked-case preview evidence (2026-09-14): staging verification confirms
the read-only preview reports linked results and trend points without issuing
a purge request. Keep this marker aligned with the API service revision.
