# P0 BASELINE SNAPSHOT

## Scope

This snapshot records the authoritative repository, Google Stitch and Railway state checked on 2026-09-04 before application code is created. It contains identifiers and non-secret state only.

## Canonical source documents

| File | Version | SHA-256 at P0 update |
| :--- | :--- | :--- |
| `business-analysis.md` | 0.5 | `A49D3F221801D62A575B21004D92A1944AFDFE4F9E4DFAE6A96047EF5328BCB1` |
| `technical-specification.md` | 0.7 | `BFB15A17B6770C3B1CA4A8FA1610D8C7B8DE24291D7573E8055C891B20581B01` |
| `plan.md` | 1.1 | `631BB49A7062B8E4BCB0589CD60385B084D179894A9270FB9F65675BC7330D40` |

Hashes are a baseline reference, not a prohibition on later versioned updates.

## Repository

- Canonical files at start: `README.md`, `business-analysis.md`, `technical-specification.md`, `plan.md`.
- No frontend/backend source, migration, tests, Dockerfile, Railway manifest or CI pipeline existed at the start of P0.
- `.env` is ignored and not tracked by Git.
- Preserved user changes:
  - deleted `UI-UX.md`;
  - deleted `DESIGN.md`;
  - deleted `Biological-toolkit.html`;
  - renamed `technical.md` to `technical-specification.md`;
  - existing edits to the three canonical documents.

## Google Stitch

| Property | Live value |
| :--- | :--- |
| Project title | `RT-connect` |
| Project ID | `14242591911141046021` |
| Visibility | `PUBLIC` |
| Device | `DESKTOP` |
| Design System | `Clinical Precision Interface` |
| Design System asset | `105b9f4e25334bbcbc6c94d588ee29f9` |
| Active screen resources | 6 |
| Active application screens | 4 |
| Active image assets | 2 |

The active application screens are Home Dashboard, QA Archive, PSQA Gamma Workspace and Report Builder Studio. Four Biological instances remain visible only as hidden metadata in `get_project`; they are deprecated, absent from active `list_screens`, and must not be restored or used for implementation.

Because the project is public, every Stitch prompt and screen must use synthetic data only.

## Railway

| Property | Live value |
| :--- | :--- |
| Project | `prolific-learning` |
| Project ID | `339f2c50-ddd7-491f-8c4e-da2a2d169502` |
| Workspace ID | `53fb850d-a59c-4690-816f-01aea06f0645` |
| Environment | `production` |
| Environment ID | `910dff25-75b6-42b2-bf6b-e2601ba9d7d2` |
| Service | `RT-connect` |
| Service ID | `9544c3e6-c8bd-4c29-b62e-c6172eb51af3` |
| Latest deployment | `FAILED` |
| Deployment ID | `b8037f6c-720c-407c-b5e4-34421358b4a3` |
| Domains | None |
| PostgreSQL | None |
| Redis/worker/renderer | None |
| Railway bucket | None |

No Railway resource was created, changed, redeployed or deleted in P0. Exact workspace usage could not be read with the current token scope; cost is therefore unknown, not zero.

## Supabase

- Selected responsibility: Auth/Identity/Session only.
- No Supabase configuration key was present in the local `.env` at P0.
- No Supabase database is authorized as RT-CONNECT business storage.
- Development/staging Auth configuration remains a P2 prerequisite.

## P0 decisions

- Business source: `business-analysis.md`.
- Technical source: `technical-specification.md`.
- Phase/gate source: `plan.md`.
- Design source: live Google Stitch project above.
- Backend and business database target: Railway + Railway PostgreSQL.
- Identity/session target: Supabase Auth.
- Runtime must not depend on Stitch MCP.
- Active Biological screen mapping is empty until P12–P15 creates new screens.

