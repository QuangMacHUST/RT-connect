# P1 FOUNDATION EVIDENCE

## Scope delivered

- `apps/api`: FastAPI application factory, typed configuration, health/readiness/version
  endpoints, correlation-ID middleware, redacted JSON logging, common error contract,
  SQLAlchemy boundary, Alembic and adapter ports.
- `apps/web`: React/TypeScript/Vite app shell, typed route registry, typed API client with
  correlation ID, React Query status screen, error/retry state, component test and Chromium
  E2E harness.
- `docker-compose.yml`: local API/web/PostgreSQL/Redis/MinIO topology. Local object storage
  is development-only; it is not a production artifact store.
- `apps/api/alembic/versions/20260905_0001_foundation.py`: versioned, reversible foundation
  migration for the synthetic organization/site/machine boundary.
- `apps/api/railway.toml` and Dockerfiles: a deterministic build/start contract for the
  formerly document-only Railway service.
- `.env.example`, full Node lockfile and resolved Python lockfile contain placeholders and
  package versions only.

## Verification completed on 2026-09-05

| Check | Result |
| :--- | :--- |
| API pytest | PASS — 7 tests |
| API Ruff | PASS |
| API mypy strict | PASS — 15 source files |
| Alembic PostgreSQL SQL render | PASS — revision `20260905_0001` |
| OpenAPI export/check | PASS — `docs/openapi.json` |
| API process smoke | PASS — local `/api/v1/health` and `/api/v1/version` returned expected contracts and correlation IDs |
| Web lint | PASS |
| Web type check | PASS |
| Web component test | PASS — 1 test |
| Web production build | PASS |
| Playwright Chromium E2E | PASS — 1 test |
| Python dependency consistency | PASS — `pip check` |
| Production Node dependency audit | PASS — no vulnerability reported by `npm audit --omit=dev --audit-level=high` |
| Repository secret value scan | PASS — no value from local `.env` appeared outside ignored environment files |
| Docker Compose build and health checks | PASS — API, web, PostgreSQL, Redis and MinIO reached healthy state |
| PostgreSQL migration in API container | PASS — `20260905_0001` applied to a clean PostgreSQL 17 container |
| Synthetic seed in PostgreSQL container | PASS — organization/site/machine seed persisted and its machine count was verified |
| Complete Docker HTTP smoke | PASS — API health/readiness and web `/health` returned successfully |

## Controls verified

- The seed command refuses to run without `DATABASE_URL`; it cannot silently seed a default
  database.
- Compose does not import repository-root `.env`; Railway/Stitch tooling tokens are therefore
  not passed into the API or web container.
- API readiness returns a controlled `503` when no database is configured; liveness remains
  independent of database availability.
- No Railway token, Supabase service-role key, database credential or object-storage secret
  is included in source, OpenAPI, web bundle source or documentation.
- The web is not a static clinical mock: the P1 screen obtains its status and version from the
  API client and displays a retry/error state when the API cannot be reached.

## Container evidence and close condition

On 2026-09-05, `scripts/verify-p1.ps1 -WithContainers` was run against Docker Desktop's
Linux engine. It built the two application images, waited for all five services to become
healthy, applied the Alembic revision inside the API container, ran the synthetic seed command,
confirmed the persisted machine count through `psql`, then called API health/readiness and web
health over localhost. The script finally removed only the `rt-connect-local` test containers,
network and named volumes.

The first container run exposed a configuration defect: Pydantic Settings expects list-valued
environment variables as JSON, while Compose supplied `CORS_ALLOWED_ORIGINS` as a plain URL.
The Compose configuration now supplies a JSON list, and the successful rerun is the authoritative
result. Application Docker base images are pinned by digest and application-specific
`.dockerignore` files exclude local dependency directories and environment files.

P1 is complete. This local evidence does **not** authorize a Railway or production deployment;
P2 still requires a distinct staging environment and restored external configuration. P2's local
JWT foundation is recorded separately in `docs/p2-auth-deployment-foundation.md`.
