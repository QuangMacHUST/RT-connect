# P2 staging deployment runbook

This runbook is intentionally scoped to staging. It must not be applied to the existing
production environment.

> **Cập nhật 2026-09-13:** Railway staging hiện dùng các cài đặt hiệu lực trực tiếp trên
> từng dịch vụ. `railwayConfigFile` đang là `null`; đường dẫn `/apps/api/railway.toml`
> không phải điều kiện bắt buộc và không cần nhập lại sau mỗi lần triển khai. Tệp
> `apps/api/railway.toml` vẫn được giữ trong mã nguồn làm tài liệu cấu hình chuẩn, nhưng
> khi có khác biệt thì cài đặt hiệu lực trong Railway và kết quả triển khai là nguồn đối
> chiếu. Bằng chứng hiện hành: `docs/evidence/p2-railway-effective-settings-20260913.json`.

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
| Config-as-code path | Không bắt buộc; để trống nếu Railway không áp dụng được đường dẫn này |
| Watch paths | `/apps/api/**` |
| Dockerfile | `Dockerfile` relative to `/apps/api` |

Railway's monorepo behavior requires a service root directory. Cấu hình hiệu lực hiện tại
đã xác nhận `Root Directory=/apps/api`, Dockerfile `/apps/api/Dockerfile`, healthcheck
`/api/v1/health` và pre-deploy `alembic upgrade head`. Không coi việc ô cấu hình đường dẫn
config-as-code tự biến mất là lỗi nếu các cài đặt hiệu lực và kết quả triển khai vẫn đúng.

## Railway steps

1. Create an environment named `staging`; do not duplicate production runtime variables.
2. Create a staging PostgreSQL service named `Postgres`. Record its resource limits and the
   usage snapshot before and after provisioning.
3. Create or configure a staging API service from the existing repository. Set source root to
   `apps/api`, apply the effective build/deploy settings above, and configure the required
   variables from `deployment/railway/env.example` in Railway's secret store. Do not repeatedly
   re-enter `/apps/api/railway.toml` after deployment; verify the effective settings instead.
4. Use the private variable reference `${{Postgres.DATABASE_URL}}` for `DATABASE_URL`.
5. Generate a Railway public domain for the API. Configure the web staging origin in
   `CORS_ALLOWED_ORIGINS` only after its exact HTTPS URL is known.
6. Deploy the API. The pre-deploy command applies the Alembic baseline. Review logs for the
   migration and healthcheck, then run the five post-provision checks in `services.md`.

## P8 Gamma worker

After the API has deployed the Gamma migration, create a separate service named
`RT-connect-gamma-worker-staging` from the same repository and staging branch. Configure:

| Setting | Value |
| :--- | :--- |
| Root Directory | `/apps/api` |
| Config-as-code path | Not set in the current staging service; Railway's legacy `railwayConfigFile` API is deprecated/rejected |
| Start command (effective config) | `python -m rt_connect_api.worker` |
| Public domain | None |
| Healthcheck | None; this is a non-HTTP worker |
| `GAMMA_WORKER_POLL_SECONDS` | `2` in staging |
| `GAMMA_WORKER_ONCE` | unset |
| `REDIS_URL` | Railway private reference `${{Redis.REDIS_URL}}`, same value source as API |

Apply the root/start/healthcheck settings directly in the worker service (or through the
supported Railway IaC mechanism when adopted); do not assume that merely committing
`railway.worker.toml` changes the service. Copy/reference the API's staging values for `DATABASE_URL`, `SUPABASE_JWT_*`, `S3_*` and
`MAX_UPLOAD_BYTES` without exposing their secret values. Do not add the API's
`/apps/api/railway.toml` to this worker: it would run the API healthcheck and could cause a
non-HTTP worker deployment to fail. With `REDIS_URL` set, verify worker logs show Redis
Streams/consumer-group startup rather than database polling, then verify a Gamma run moves
from `QUEUED` to `RUNNING` to `COMPLETED` and the Redis pending count is acknowledged.

## Supabase handoff

Set the staging Site URL and redirect URLs to the future staging web origin. Supply the API with
the Supabase Auth issuer and JWKS URL. The frontend may receive only the project URL and
publishable key. Configure no business tables in Supabase.

## Rollback for this phase

Before any later staging schema revision, record the current migration revision and take the
provider-supported PostgreSQL backup/snapshot. For the P2 initial schema, a failed empty
staging deployment is rolled back by stopping the failed API deployment and correcting the
configuration; production remains untouched.
