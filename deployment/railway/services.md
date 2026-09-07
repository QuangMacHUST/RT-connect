# Railway service topology

## P2 staging

| Resource | Railway name | Exposure | Purpose |
| :--- | :--- | :--- | :--- |
| API | `RT-connect` or a clearly renamed `api` service | Public HTTPS | FastAPI application and later API surface |
| PostgreSQL | `Postgres` | Private only | Sole business-data database |

The API source root is `apps/api`. Its `railway.toml` uses the Dockerfile, applies
`alembic upgrade head` as a pre-deploy command, checks `/api/v1/health`, and restarts on
failure. `DATABASE_URL` must be set using Railway's private reference to Postgres; it must not
be copied into a browser build or committed environment file.

P2 deliberately does not create Redis, a worker, renderer, object-storage proxy, or a public
database domain. Those are introduced only in their scheduled phases after workload evidence.

## P8 Gamma staging topology

P8 adds a separate non-public worker service. It uses the same repository, image and private
staging database/object-storage variables as the API, but it must not reuse the API's
`railway.toml`: that file runs the HTTP healthcheck and Alembic pre-deploy command. Configure
the worker with `/apps/api/railway.worker.toml`, whose start command is
`python -m rt_connect_api.worker` and which deliberately has no HTTP healthcheck.

| Resource | Railway name | Exposure | Purpose |
| :--- | :--- | :--- | :--- |
| API | `Railway-API-staging` | Public HTTPS | Authenticated REST API, migrations and job enqueue/poll |
| Worker | `RT-connect-gamma-worker-staging` | Private only | Database-backed Gamma queue consumer |
| PostgreSQL | `Postgres-Q1Hc` | Private only | Gamma run rows and application data |
| Bucket | `orderly-pail` | Private only | Validated Gamma input artifacts |

The worker must receive the same `DATABASE_URL`, Supabase JWT settings and S3-compatible
storage settings as the API. Set `GAMMA_WORKER_POLL_SECONDS` to a small staging value such as
`2`; leave `GAMMA_WORKER_ONCE` unset for the long-running worker. Do not generate a public
domain or healthcheck for this service. P8 currently uses a persisted database queue; Redis
claim/metrics remain a later hardening gate documented in `plan.md`.

## Environment boundaries

`staging` is a distinct Railway environment. It uses only synthetic fixtures and a separate
Supabase Auth project/configuration. It must receive a separate API service instance and
PostgreSQL instance. Existing production service `RT-connect` is not modified during P2.

## Required post-provision checks

1. Public HTTPS `GET /api/v1/health` returns `status: ok`.
2. `GET /api/v1/ready` returns `status: ready` from the API service using its private database
   reference.
3. The deployment log confirms Alembic revision `20260905_0001` was applied on an empty
   staging database.
4. Service/domain status shows only the API public; PostgreSQL has no public domain.
5. Runtime variables do not include `RAILWAY_ACCOUNT_TOKEN`, `RAILWAY_PROJECT_TOKEN`, a
   Supabase service-role key, or any browser-prefixed database value.
