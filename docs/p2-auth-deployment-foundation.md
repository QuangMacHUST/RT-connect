# P2 AUTH AND DEPLOYMENT FOUNDATION

## Implemented locally

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

## Local verification on 2026-09-05

| Check | Result |
| :--- | :--- |
| API auth contract and JWT verifier tests | PASS — valid RSA token is accepted; missing/expired/wrong issuer/wrong audience/wrong role/wrong signature/JWKS failure paths are rejected |
| API suite | PASS — 17 tests |
| Ruff and strict mypy | PASS — 19 source files |
| Full Docker regression | PASS — rebuilt API image, all Compose services healthy, clean migration/seed/readiness/web health passed |
| Post-change complete local verifier | PASS — API tests, lint, strict typing, PostgreSQL migration SQL, web lint/type-check/test/build, Compose health, in-container migration and synthetic seed all passed |

## Remaining verification before P2 can close

The local verifier security contract has passed. Live Supabase verification is still pending:
the URL, publishable key and issuer/JWKS configuration are not yet available in `.env`.

1. Railway credentials are already present and verified live from root `.env` on 2026-09-05.
   The account token can read the target project, but Railway CLI rejects environment-link/create
   operations with `UNAUTHORIZED`; a credential with project write access is required for
   staging provisioning.
2. Create or select a **non-production** Supabase Auth project, then configure its site and
   callback URLs and place only its publishable browser configuration plus backend issuer/JWKS
   values in local/deployment secret stores.
3. Create Railway staging and its PostgreSQL service, connect `DATABASE_URL` privately, deploy
   the API, run the clean migration, and prove HTTPS health from outside Railway.
4. Use a dedicated staging test account to prove a valid Supabase access token reaches
   `/api/v1/auth/session`; run invalid/expired/wrong-issuer/wrong-audience token tests against
   the deployed API.

No Railway token, database URL, Supabase service-role key, or real user/patient data is recorded
in this document or source tree.
