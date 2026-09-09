# RT-CONNECT

RT-CONNECT is a phased web platform for radiotherapy QA workflows and an independent
Biological Toolkit. It is being implemented from the business requirements in
`business-analysis.md`, the architecture in `technical-specification.md` and the release
gates in `plan.md`.

## Architecture decision

- **Supabase:** identity, authentication and browser session only.
- **Railway:** backend server and the sole target PostgreSQL database for business data.
- **Object storage:** durable S3-compatible storage for files and rendered artifacts; never
  Railway's ephemeral filesystem.
- **Google Stitch:** design-time visual source only. The running web application never
  calls Stitch.

No patient dataset, credential or token belongs in this repository or in the public Stitch
project. Fixtures and early seeds are synthetic only.

## P1 local setup

Prerequisites: Git, Python 3.13–3.14, Node 24, npm, and Docker Desktop for the full local
PostgreSQL/Redis/MinIO stack. The complete local Compose workflow has been verified on this
development machine with Docker Desktop's Linux engine.

1. Keep the existing repository-root `.env` untouched: it is local deployment tooling only and
   must never be passed to an application process or container. For a standalone API, copy
   `apps/api/.env.example` to `apps/api/.env`; for a standalone Vite web server, copy
   `apps/web/.env.example` to `apps/web/.env.local`. Keep every placeholder value local.
2. In `apps/api`, create a virtual environment and install the pinned dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.lock
   ```

3. In `apps/web`, install the lockfile and build:

   ```powershell
   npm install
   npm run build
   ```

4. For the complete local stack, use Docker Desktop from repository root:

   ```powershell
   docker compose up --build --wait
   ```

   This starts API, web, PostgreSQL, Redis, MinIO and the separate Gamma worker. The API health
   endpoint is `http://localhost:8000/api/v1/health`; the web shell is `http://localhost:5173`.
   A stack with API and Redis but without `worker` is not a complete local queue workflow: Gamma
   runs can be accepted and remain queued. Run `docker compose down -v` only when you
   intentionally want to remove local development database and object-storage volumes.

5. To run focused verification without containers, execute:

   ```powershell
   .\scripts\verify-p1.ps1
   ```

   Use `-WithContainers` only after Docker Desktop is installed and running.

6. To verify the real local Redis/worker path with disposable synthetic data, run:

   ```powershell
   .\apps\api\.venv\Scripts\python.exe `
     .\scripts\verify-local-gamma-queue.py `
     --output .\docs\evidence\p8-local-redis-worker-smoke-YYYYMMDD.json
   ```

   The verifier uses a temporary database, a unique Redis stream and a disposable MinIO bucket;
   it checks a successful job, duplicate dispatch, terminal replay, three bounded storage-failure
   attempts, dead-letter quarantine and zero pending messages, then removes those resources.
   Its result is local support evidence only and must not be read as staging or clinical-release
   approval.

## Current scope

P1 supplies the repeatable foundation: FastAPI health/readiness/version contracts,
correlation IDs, redacted structured logs, a versioned Alembic foundation migration,
React app shell, real typed API client, tests and CI. It does not yet expose authentication,
clinical workflow or biological calculation features; those are enabled only in their
scheduled phases after their own contracts and tests exist.

## Staging deployment preparation

P2 deployment contracts are prepared in `deployment/railway/` and
`deployment/supabase/`. They describe the separate staging environment, private Railway
PostgreSQL reference, Supabase Auth issuer/JWKS configuration and the required remote smoke
checks. Do not apply them to the existing production environment.
