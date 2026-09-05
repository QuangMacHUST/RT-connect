# P2 staging deployment runbook

This runbook is intentionally scoped to staging. It must not be applied to the existing
production environment.

## Prerequisites

- A Railway account credential with write access to project `prolific-learning`.
- A selected non-production Supabase Auth project.
- The current API source committed and pushed to the connected GitHub repository. Railway
  cannot build uncommitted files on the developer workstation.
- Synthetic data only.

## GitHub source and monorepo configuration

The old failed deployment analyzed commit `aa5dce6` (`set up enviroment`), which predates the
`apps/api` source tree. The current `origin/main` commit `dc6ee79` contains the application
source and deployment files. Before triggering another deployment, confirm that the Railway
service is connected to `main` and that its CI check suite is green. Confirm that the selected
deployment commit contains `apps/api/Dockerfile`, `apps/api/railway.toml`,
`apps/api/requirements.lock`, `apps/api/alembic.ini` and `apps/api/src`.

For the API service, set these Railway build settings:

| Setting | Value |
| :--- | :--- |
| Root Directory | `/apps/api` |
| Config-as-code path | `/apps/api/railway.toml` |
| Watch paths | `/apps/api/**` |
| Dockerfile | `Dockerfile` relative to `/apps/api` |

Railway's monorepo behavior requires a service root directory. Its config file path is specified
as an absolute repository path when the file is outside the default root configuration lookup.

## Railway steps

1. Create an environment named `staging`; do not duplicate production runtime variables.
2. Create a staging PostgreSQL service named `Postgres`. Record its resource limits and the
   usage snapshot before and after provisioning.
3. Create or configure a staging API service from the existing repository. Set source root to
   `apps/api`, use its `railway.toml`, and configure the required variables from
   `deployment/railway/env.example` in Railway's secret store.
4. Use the private variable reference `${{Postgres.DATABASE_URL}}` for `DATABASE_URL`.
5. Generate a Railway public domain for the API. Configure the web staging origin in
   `CORS_ALLOWED_ORIGINS` only after its exact HTTPS URL is known.
6. Deploy the API. The pre-deploy command applies the Alembic baseline. Review logs for the
   migration and healthcheck, then run the five post-provision checks in `services.md`.

## Supabase handoff

Set the staging Site URL and redirect URLs to the future staging web origin. Supply the API with
the Supabase Auth issuer and JWKS URL. The frontend may receive only the project URL and
publishable key. Configure no business tables in Supabase.

## Rollback for this phase

Before any later staging schema revision, record the current migration revision and take the
provider-supported PostgreSQL backup/snapshot. For the P2 initial schema, a failed empty
staging deployment is rolled back by stopping the failed API deployment and correcting the
configuration; production remains untouched.
