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
