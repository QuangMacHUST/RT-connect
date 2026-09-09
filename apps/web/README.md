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

Latest staging parity evidence: `p19-staging-public-smoke-20260909-38dec53.json`
records API, worker and web source SHA `38dec53d4e542bdf6c4f808283981b344cae3502`
with schema `20260909_0019`; keep this marker aligned when progress/evidence changes.

Current P17 staging fixture marker: the authenticated case recheck keeps the
synthetic RTDOSE/RTSTRUCT/CT set and saved DVH run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`.
This marker is intentionally duplicated under the web service root so the
release candidate is rebuilt with the same source commit across API, worker and web.
