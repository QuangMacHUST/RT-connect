# ENVIRONMENT AND SECRET NAME INVENTORY

This document records variable names and ownership only. It must never contain real values.

## Local deployment tooling only

| Name | Scope | Runtime application may read it? |
| :--- | :--- | :--- |
| `RAILWAY_PROJECT_TOKEN` | Local/CI deployment for one Railway environment | No |
| `RAILWAY_ACCOUNT_TOKEN` | Local/CI workspace provisioning | No |
| `GOOGLE_STITCH_API_KEY_MCP` | Local Codex/MCP configuration | No |

Only one official Railway CLI auth variable is mapped at a time in the calling process: project token → `RAILWAY_TOKEN`, account/workspace token → `RAILWAY_API_TOKEN`.

## Backend runtime

| Name | Environments | Secret |
| :--- | :--- | :--- |
| `APP_ENV` | all | No |
| `APP_VERSION` | all | No |
| `LOG_LEVEL` | all | No |
| `DATABASE_URL` | dev/test/staging/pilot/production | Yes |
| `REDIS_URL` | P8+ environments | Yes |
| `SUPABASE_URL` | dev/staging/pilot/production | No |
| `SUPABASE_JWT_ISSUER` | dev/staging/pilot/production | No |
| `SUPABASE_JWT_AUDIENCE` | dev/staging/pilot/production | No |
| `SUPABASE_JWKS_URL` | dev/staging/pilot/production | No |
| `SUPABASE_INTROSPECTION_SECRET` | only if selected verification mode requires it | Yes |
| `S3_ENDPOINT` | dev/staging/pilot/production | Usually no |
| `S3_REGION` | dev/staging/pilot/production | No |
| `S3_BUCKET` | dev/staging/pilot/production | No |
| `S3_ACCESS_KEY_ID` | dev/staging/pilot/production | Yes |
| `S3_SECRET_ACCESS_KEY` | dev/staging/pilot/production | Yes |
| `S3_SIGNED_URL_TTL_SECONDS` | dev/staging/pilot/production | No |
| `CORS_ALLOWED_ORIGINS` | dev/staging/pilot/production | No |
| `MAX_UPLOAD_BYTES` | all | No |
| `TREND_MAX_RAW_POINTS` | P10+ | No |
| `TREND_MAX_AGGREGATE_SOURCE_POINTS` | P10+ | No |
| `REQUEST_TIMEOUT_SECONDS` | all | No |
| `CORRELATION_ID_HEADER` | all | No |
| `ENGINE_VERSION` | all | No |
| `RENDERER_VERSION` | all | No |

## Frontend build/runtime configuration

| Name | Browser-visible | Notes |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Yes | Public RT-CONNECT API URL |
| `VITE_SUPABASE_URL` | Yes | Supabase Auth project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Yes | Publishable/anon key only; never service role |
| `VITE_APP_VERSION` | Yes | Release version |

## Environment separation

- Development/test use synthetic fixtures and isolated databases.
- Staging uses a Railway staging environment, Railway PostgreSQL staging service and Supabase Auth staging configuration.
- Pilot is isolated from production when real datasets are introduced.
- Production receives only a tested release manifest promoted from staging.
- Database URLs, Auth issuers/audiences/redirects, storage buckets and credentials are never reused across environments unless the isolation decision is explicitly documented.

## Secret handling checks

- `.env` remains ignored and untracked.
- Example files contain placeholders only.
- Frontend bundle scan rejects database, Railway, service-role and S3 secrets.
- Structured logs redact token, authorization header, cookie, database URL and object-storage credentials.
- Deployment documentation records secret names and reference-variable wiring, never plaintext values.
