# P2 AUTH AND DEPLOYMENT FOUNDATION

## Current staging recheck — 2026-09-13

The staging configuration and public boundary are now verified against the current Railway
service settings:

- Railway effective settings passed all checks, including `/apps/api`, the API Dockerfile,
  `/api/v1/health`, `alembic upgrade head`, `PORT=8000`, private PostgreSQL/Redis host
  classification, Supabase issuer/JWKS variable names, CORS origin and the absence of
  forbidden frontend/backend credential names. The effective `railwayConfigFile` is `null`;
  this is expected for the current direct-service configuration and is not a deployment error.
- Staging public health, readiness, schema revision, API version, OpenAPI routes and web bundle
  checks passed. Unauthenticated organization routes return `401`, and the invalid-token probe
  is required to return the same boundary response.
- A real existing staging browser session recovered successfully at `/app`. The home page read
  the organization dashboard, and `/app/organization` read the organization, one site, one
  machine and one active membership from the API-backed staging data. No password, access token,
  patient data or database URL was recorded.

Evidence:

- `docs/evidence/p2-railway-effective-settings-20260913.json`
- `docs/evidence/p2-staging-public-recheck-20260913.json`
- `docs/evidence/p2-staging-authenticated-browser-20260913-7a7e4ec.json`
- `docs/evidence/p2-staging-public-recheck-20260913-after-api-deploy.json`

The API was then deployed as Railway deployment
`173c5be1-a366-4410-8d5e-088bd8f72020` at the same candidate SHA as the web. The after-deploy
public verifier reports `passed=true`, API version `7a7e4ec8698f348e6921c69c4b4e212aab425977`,
schema `20260911_0020`, and zero failed checks. The authenticated browser recheck also reads the
organization, site, machine and active membership from the API-backed staging environment.
P2 is therefore closed for development. Production is not aligned: the current production
project has the legacy `RT-connect` API service only, with no matching production web/worker/Auth
configuration in the current effective-settings packet. That remains an explicit P19 release
gate, not a reason to mix production deployment work into P3.

## Historical local implementation baseline

- Backend configuration now accepts `SUPABASE_JWT_ISSUER`,
  `SUPABASE_JWT_AUDIENCE`, and an optional explicit `SUPABASE_JWKS_URL`. When an issuer is
  supplied without an explicit JWKS URL, the standard `/.well-known/jwks.json` location is used.
- `GET /api/v1/auth/session` is a protected session-verification contract. It returns only the
  verified subject and optional email; it does not accept an organization ID from the browser.
- The verifier uses Supabase's JWKS and accepts only asymmetric `RS256`, `ES256`, or `EdDSA`
  tokens. It requires `sub`, `iat`, and `exp`, and validates issuer and audience. A missing,
  malformed, expired, wrong-issuer, wrong-audience, or invalid-signature token cannot be used as
  an authenticated identity.
- If Auth has not yet been configured, protected routes return a controlled
  `503 AUTH_CONFIGURATION_UNAVAILABLE`; they never fall back to anonymous access.
- `PyJWT[crypto]` and its explicit transitive dependencies are pinned in the Python lockfile;
  no Supabase service-role key is required by this implementation.

## Historical local verification on 2026-09-05

| Check | Result |
| :--- | :--- |
| API auth contract and JWT verifier tests | PASS — valid RSA token is accepted; missing/expired/wrong issuer/wrong audience/wrong role/wrong signature/JWKS failure paths are rejected |
| API suite | PASS — 17 tests |
| Ruff and strict mypy | PASS — 19 source files |
| Full Docker regression | PASS — rebuilt API image, all Compose services healthy, clean migration/seed/readiness/web health passed |
| Post-change complete local verifier | PASS — API tests, lint, strict typing, PostgreSQL migration SQL, web lint/type-check/test/build, Compose health, in-container migration and synthetic seed all passed |

## Remaining verification before production release at P19

The local verifier and the current staging Auth/deployment slice have passed. Before production
release at P19, the deployed production services must represent one exact candidate:

1. Deploy the API staging service at the same SHA currently embedded in the web staging bundle,
   then rerun the public verifier with that exact expected version and schema revision.
2. Prepare a production packet containing a current web service, API service, private PostgreSQL,
   private worker, Supabase issuer/JWKS, CORS/redirect origins, `PORT=8000`, migration command
   and source-identifiable version metadata. The current production gap is recorded in
   `docs/evidence/p2-production-foundation-gap-20260913.json`.
3. Deploy one exact production candidate only after the packet is complete; verify health,
   readiness, version, OpenAPI route presence and web deep-link before any later phase.
4. Repeat an authenticated organization readback and a controlled invalid/expired-token check
   on the exact candidate in each environment. Do not record an access token or patient data.

No Railway token, database URL, Supabase service-role key, or real user/patient data is recorded
in this document or source tree.
