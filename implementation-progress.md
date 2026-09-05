# RT-CONNECT IMPLEMENTATION PROGRESS

## Current checkpoint

- **Goal:** Hoàn thiện RT-CONNECT theo `plan.md` từ P0 đến P19 và thiết lập baseline vận hành P20.
- **Current phase:** P2 — Railway staging, PostgreSQL và deployment foundation.
- **Current status:** IN_PROGRESS — P1 local gate closed; production API and Railway PostgreSQL now pass external health/readiness checks. Railway staging environment exists but its generated service has no source or deployment; Supabase public configuration remains absent.
- **Last authoritative check:** 2026-09-06T00:20:46+07:00.
- **Next exact step:** configure the existing empty staging service to deploy GitHub branch `codex/p2-runtime-resilience` using source root `/apps/api` and config path `/apps/api/railway.toml`; then obtain a cost/usage snapshot before creating any staging PostgreSQL resource.

## Source documents read

| Source | Version | Status |
| :--- | :--- | :--- |
| `business-analysis.md` | 0.5 | Read; business source |
| `technical-specification.md` | 0.7 | Read; technical contract |
| `plan.md` | 1.1 | Read; phase order and gates |

## Phase status

| Phase | Status | Evidence / next gate |
| :--- | :--- | :--- |
| P0 | DONE | Exit audit passed on 2026-09-05; baseline, traceability, module/route/environment registries and Railway failure issue recorded |
| P1 | DONE | Full local Compose build/health, in-container PostgreSQL migration, synthetic seed persistence, API readiness and web health passed on 2026-09-05 |
| P2 | IN_PROGRESS | Production API/PostgreSQL connectivity is verified; URL resilience and failure handling are covered locally. Staging environment exists, but its API source/service setup, PostgreSQL migration evidence, Supabase configuration and live Auth smoke remain required. |
| P3 | NOT_STARTED | Depends on P2 |
| P4 | NOT_STARTED | Depends on P3 |
| P5 | NOT_STARTED | Depends on P4 |
| P6 | NOT_STARTED | Depends on P5 |
| P7 | NOT_STARTED | Depends on P6 |
| P8 | NOT_STARTED | Depends on P6/P7 |
| P9 | NOT_STARTED | Depends on P7/P8 for Gamma blocks |
| P10 | NOT_STARTED | Depends on P7–P9 |
| P11 | NOT_STARTED | Depends on P7/P9 |
| P12 | NOT_STARTED | Biological screen must be regenerated |
| P13 | NOT_STARTED | Depends on P12 |
| P14 | NOT_STARTED | Depends on P13 |
| P15 | NOT_STARTED | Depends on P13/P14 |
| P16 | NOT_STARTED | Depends on P12/P13 |
| P17 | NOT_STARTED | Depends on P6/P8/P9 |
| P18 | NOT_STARTED | Integrated hardening and pilot |
| P19 | NOT_STARTED | Production remote web release |
| P20 | NOT_STARTED | Initial operations package after P19 |

## Live Google Stitch evidence

- Project: `RT-connect`.
- Project ID: `14242591911141046021`.
- Visibility: `PUBLIC`.
- Device baseline: `DESKTOP`.
- Design System: `Clinical Precision Interface`, asset `105b9f4e25334bbcbc6c94d588ee29f9`.
- `list_screens` returned six active resources: four application screens plus logo and avatar.

| Active application screen | Screen ID | Module |
| :--- | :--- | :--- |
| Trang chủ - Home Dashboard | `70b9f1d256884221ae20e63b5244db11` | MOD-01 |
| Kho lưu trữ QA & Thư mục | `4c9ec57310fd404cbae3b53b0bab2368` | MOD-03 |
| Phân tích PSQA Gamma Workspace | `ffb87901b3194bd3aff8760c54c2f9f4` | MOD-04/MOD-06 |
| Trình biên soạn Báo cáo - Report Builder Studio | `a1478466ace843c5aaf9a15dfc58273e` | MOD-07 |

`get_project` still exposes the four old Biological instances as `hidden`. They are deprecated and must not be restored or used as design-to-code sources. P12–P15 will create new screens one at a time in the same project.

## Live Railway evidence

- Project: `prolific-learning` (`339f2c50-ddd7-491f-8c4e-da2a2d169502`).
- Workspace: `Mạc Đăng Quang's Projects` (`53fb850d-a59c-4690-816f-01aea06f0645`).
- Environments: `production` (`910dff25-75b6-42b2-bf6b-e2601ba9d7d2`) and `staging` (`b0ab34e5-0ff4-479d-8232-659d175e9e2f`).
- Services: `RT-connect` (`9544c3e6-c8bd-4c29-b62e-c6172eb51af3`) and private `Postgres` (`5709f18d-c92d-461a-9f73-478dd7748d80`).
- API latest deployment: `SUCCESS`, deployment `c52cd2c5-2063-443b-a92a-6917c6239156`, instance `RUNNING`, source commit `0d3a503d33e3f9dbbdb21d5b50acb034048be601`.
- Railway generated public API domain: `https://rt-connect-production.up.railway.app` on target port 8000; no custom domain exists.
- External check at 2026-09-05T16:57Z: `/api/v1/health` returned 200 `ok`; `/api/v1/ready` returned 200 `ready` after the production API was connected to private Railway PostgreSQL.
- PostgreSQL runs privately with a Railway-managed 5 GB volume. No public PostgreSQL domain was reported.
- Staging was verified live on 2026-09-06. It contains generated service `gleaming-cooperation` (`9b35bf0b-0419-4679-8af0-e639e5a84713`) with no source, deployment, domain or volume; it is safe to configure as the staging API rather than create a second empty service.
- The deployment metadata still reports no applied `healthcheckPath` or `preDeployCommand`; migration execution on the Railway database remains unproven and must not be inferred from readiness.
- Railway documentation was rechecked on 2026-09-06: config-as-code does not follow a monorepo root directory. The API service must explicitly set config path `/apps/api/railway.toml`; this explains the null healthcheck/pre-deploy fields in the current production deployment metadata.
- Account and project token scopes were verified without printing token values.
- Railway CLI was not installed globally; `npx @railway/cli` version `5.49.1` was used read-only.
- Workspace usage query returned `UNAUTHORIZED`; exact billing/usage remains unavailable with the supplied token scope and must not be guessed.

Failed deployment root cause from build log: Railpack could not determine a build because the deployed commit contained only documents/static files and no `start.sh`, Dockerfile, Python/Node application manifest or supported runnable source. No redeploy was attempted.

## Repository evidence

- Repository contained only the four canonical Markdown files before P0 artifact creation.
- `.env` is Git-ignored and untracked.
- Secret values were not read into output; only key names were inventoried.
- User-owned deletions are preserved: `UI-UX.md`, `DESIGN.md`, `Biological-toolkit.html`.
- User-owned rename is preserved: `technical.md` → `technical-specification.md`.
- No reset, checkout or restoration of deleted files was performed.

## P0 deliverables

| Deliverable | Location | Status |
| :--- | :--- | :--- |
| Baseline snapshot | `docs/p0-baseline.md` | Verified |
| Traceability matrix | `docs/traceability-matrix.md` | Verified |
| Module registry | `docs/module-registry.md` | Verified |
| Route registry | `docs/route-registry.md` | Verified |
| Environment/secret inventory | `docs/environment-inventory.md` | Verified |
| Railway failed-deployment issue | `docs/issues/railway-failed-deployment.md` | Verified |

## Tests and checks

- P0 live Stitch project/screen/design-system check: PASS.
- Railway account-token project query: PASS.
- Railway project-token scope query: PASS.
- Railway status query: PASS.
- Railway failed deployment log retrieval: PASS.
- Railway workspace usage query: UNAVAILABLE (`UNAUTHORIZED`), recorded without guessing cost.
- Documentation consistency scan: PASS — source hashes equal recorded baseline; legacy hidden Biological IDs have no active mapping; all 17 modules occur in registry and traceability matrix.
- Secret scan: PASS — no `.env` value was found in tracked Markdown; inventory contains variable names only.
- Git diff check: PASS — only CRLF conversion notices were emitted; no whitespace error was reported.
- P0 exit audit: PASS — canonical technical filename, no UI-UX dependency, all four active application screens have owners, all other module screen gaps are explicit, Stitch/Railway IDs are recorded.
- P1 API pytest: PASS — 7 tests; FastAPI health/version/error/correlation contracts verified.
- P1 API quality: PASS — Ruff and strict mypy on 15 source files.
- P1 migration contract: PASS — Alembic revision `20260905_0001` renders PostgreSQL DDL successfully; up/down functions are present.
- P1 OpenAPI: PASS — generated contract at `docs/openapi.json` verifies reproducibly.
- P1 API process smoke: PASS — temporary local Uvicorn process returned `health=ok`, a correlation ID and version metadata; process was stopped and port released.
- P1 web quality: PASS — lint, TypeScript type check, 1 component test and production Vite build.
- P1 web E2E: PASS — 1 Playwright Chromium test against production preview build.
- P1 dependency checks: PASS — Python `pip check`; production Node `npm audit --omit=dev --audit-level=high` found no vulnerability.
- P1 source secret scan: PASS — no value from local `.env` appeared outside ignored environment files.
- P1 Compose verification: PASS — Docker Desktop Linux engine built the complete stack; all five services healthy; clean PostgreSQL migration, synthetic seed persistence, API readiness and web health passed. The scoped test stack and volumes were removed by the verifier.
- P2 JWT security contract: PASS — 17 API tests cover missing Bearer, missing configuration, valid asymmetric token, expiry, issuer, audience, role, signature and JWKS-client failure; Ruff and strict mypy pass. This is local cryptographic evidence, not a live Supabase sign-in result.
- P2 deployment preparation: PASS — `apps/api/railway.toml` now applies the baseline migration before deploy; staging Railway/Supabase variable contracts and runbooks are in `deployment/`.
- P2 Railway permission audit: account token can read production status but `railway link`/environment mutation is rejected with `UNAUTHORIZED`; usage query is also unauthorized. No Railway resource was created or changed.
- P2 Railway source audit: the old failed deployment analyzed `aa5dce6`, but `origin/main` now points to `dc6ee79` and contains the API/web source. The deployment for `dc6ee79` was skipped because the GitHub secret-guard job failed; API and web jobs passed. The CI guard has been corrected to allow `.env.example` templates while rejecting private environment files and credentials.
- P2 post-change local regression: PASS — full `scripts/verify-p1.ps1 -WithContainers` completed after JWT, CORS and Railway manifest changes: 17 API tests, lint/type checks, migration SQL, web checks, five healthy Compose services, in-container migration, synthetic seed persistence, API readiness and web health. The scoped stack and test volumes were removed.
- P2 Stitch recheck: PASS — project `RT-connect` remains public with the Clinical Precision Interface design system, the four active QA application screens, and four hidden/deprecated Biological screen instances. No Stitch design was altered during P2.
- P2 public infrastructure smoke: PASS — the generated Railway domain is reachable over HTTPS; API health and database readiness both returned 200 from an external network.
- P2 PostgreSQL URL resilience: PASS locally — plain `postgres://`/`postgresql://` URLs are normalized to the bundled psycopg v3 dialect; invalid engine initialization is surfaced as controlled 503 readiness failure instead of an unhandled 500. Focused API tests (6), Ruff, strict mypy and Alembic PostgreSQL SQL rendering pass.
- P2 migration-aware readiness: PASS locally — `/api/v1/ready` now requires a reachable database and an applied Alembic version row. Against a fresh Docker PostgreSQL database it returned 503 `Database migration is not applied`; after in-container `alembic upgrade head` it returned `ready`, and the synthetic seed persisted one machine. The scoped API/web/PostgreSQL/Redis/MinIO test stack and its two newly created volumes were removed after verification. Focused tests (7), Ruff, strict mypy and Alembic PostgreSQL SQL rendering pass.
- P2 local regression after connection hardening: PASS — 19 API tests, Ruff, strict mypy, Alembic PostgreSQL SQL render, web lint/typecheck/production build and the web component test pass. Vitest is pinned to one worker for deterministic local/CI completion; the prior default parallel runner left an orphan worker after the test had passed.

## Blockers

- Correction on 2026-09-05: both Railway tokens are present in root `.env` and authenticate successfully through the Railway API. Account-token access resolves project `prolific-learning`; project-token scope resolves its production environment. The earlier missing-token report was incorrect. Standard dotenv parsing supports spaces around `=` and quoted values.
- Supabase URL and publishable key are present as names but have empty values. This is the remaining Auth configuration dependency.
- Actual credentials were found in `.env.example` and replaced with empty placeholders; the user's `.env` was preserved.
- Supabase URL and publishable key are still empty; a Supabase Auth project/configuration is required before live sign-in and JWT verification can be tested.
- Railway staging now exists, but account-token CLI calls still cannot link or mutate service source/configuration. The generated staging service must be connected to the GitHub source through Railway UI or a project-write credential before deployment. Railway cost/usage remains unavailable with the current account token scope, so a billable staging PostgreSQL service must not be provisioned until its resource/cost gate can be reviewed.
- Revalidated 2026-09-06: the supplied Railway account token can read explicit project/environment status but `railway link --project 339f2c50-ddd7-491f-8c4e-da2a2d169502` is rejected as `Unauthorized`; therefore it cannot create or link the required staging environment. No Railway resource was created by this attempt.
- The running production API uses `apps/api` and its Dockerfile correctly, but its live deployment metadata does not show `healthcheckPath` or `preDeployCommand` applied. The baseline Alembic migration therefore lacks Railway execution evidence.

## Known limitations

- No staging PostgreSQL service exists yet; this belongs to P2 after the staging API source/configuration gate.
- No Supabase configuration values are present in `.env`; Auth project/configuration is required by P2/P3.
- Four Biological designs must be regenerated in P12–P15.
