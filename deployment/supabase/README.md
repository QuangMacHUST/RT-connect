# Supabase Auth configuration

Supabase provides only identity, authentication and browser session for RT-CONNECT. Railway
PostgreSQL remains the exclusive store for organizations, QA records, reports, calculations,
audit data and every other business entity.

## Staging configuration

Create or select a Supabase project dedicated to development/staging. Configure:

| Setting | Value |
| :--- | :--- |
| Site URL | Staging web HTTPS origin once provisioned |
| Redirect URLs | Staging web origin plus `/auth/callback` and password-recovery route used by P3 |
| Provider | Email/password for the initial synthetic test account; additional providers only when explicitly configured |
| Frontend variables | `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` |
| Backend variables | `SUPABASE_JWT_ISSUER`, `SUPABASE_JWT_AUDIENCE=authenticated`, optional explicit `SUPABASE_JWKS_URL` |

Do not use a Supabase service-role key in the frontend, backend runtime for normal user
authentication, repository, test fixture, Google Stitch prompt, or documentation.

## Required evidence before closing P2

1. A synthetic staging test account can sign in and produce an access token.
2. `GET /api/v1/auth/session` accepts the valid staging token through the staging API URL.
3. Expired, wrong issuer, wrong audience and invalid-signature tokens return the documented
   rejection rather than an identity.
4. The browser bundle contains no Railway token, database URL or Supabase service-role key.
