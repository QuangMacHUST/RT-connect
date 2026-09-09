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
