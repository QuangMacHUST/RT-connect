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
`railway.toml`: that file runs the HTTP healthcheck and Alembic pre-deploy command. The repo
contains `/apps/api/railway.worker.toml` as a declarative reference, but the current Railway
API rejects the legacy `railwayConfigFile` mutation because config-as-code is deprecated.
Therefore the effective staging worker settings are applied directly to the service instance:
root `/apps/api`, start command `python -m rt_connect_api.worker`, empty healthcheck and no
pre-deploy migration. If Railway later accepts the file through its supported IaC workflow,
the effective settings must remain identical.

| Resource | Railway name | Exposure | Purpose |
| :--- | :--- | :--- | :--- |
| API | `Railway-API-staging` | Public HTTPS | Authenticated REST API, migrations and job enqueue/poll |
| Worker | `RT-connect-gamma-worker-staging` | Private only | Redis Streams Gamma queue consumer; PostgreSQL remains source of truth |
| PostgreSQL | `Postgres-Q1Hc` | Private only | Gamma run rows and application data |
| Bucket | `orderly-pail` | Private only | Validated Gamma input artifacts |
| Redis | `Redis` | Private only | Redis Streams dispatch, consumer groups, pending/reclaim and queue metrics |

The worker must receive the same `DATABASE_URL`, Supabase JWT settings and S3-compatible
storage settings as the API. Set `GAMMA_WORKER_POLL_SECONDS` to a small staging value such as
`2`; leave `GAMMA_WORKER_ONCE` unset for the long-running worker. API and worker must both
receive `REDIS_URL=${{Redis.REDIS_URL}}` (or the equivalent Railway private reference), with
the same stream/group defaults from `apps/api/.env.example`. Do not generate a public domain
or healthcheck for this service. `REDIS_URL` selects the Redis Streams path; when it is absent
only local development may use the persisted database-polling fallback.

The queue contract is intentionally split: PostgreSQL owns run status, attempt count,
heartbeat, result and error snapshots; Redis only dispatches work. A worker acknowledges a
message only after the database update succeeds. Stale pending messages are reclaimed with
the configured visibility timeout, and the authenticated API endpoint
`GET /api/v1/gamma/queue-metrics` exposes non-patient operational counters.

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
