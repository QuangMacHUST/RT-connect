# RT-CONNECT IMPLEMENTATION PROGRESS

## Documentation and implementation rebaseline — 2026-09-08

`business-analysis.md` v0.15, `specification.md` v1.9, `technical-specification.md` v1.6 và `plan.md` v2.9 bổ sung requirement, state contract, testcase và gap từ source. Bản plan trước ở `docs/history/plan-v1.5.md`. Slice P6/P8/P9/P10/P11/P12/P13/P14/P15 đã được sửa và kiểm thử local; staging E2E chỉ được ghi cho những workflow đã kiểm trực tiếp đúng candidate.

Các trạng thái/evidence bên dưới giữ nguyên phạm vi lịch sử trừ những dòng được ghi rõ là checkpoint mới. Không tự kế thừa DONE sang gate v2: invitation/restore/concurrent edits, RTDOSE/3D staging, independent Gamma oracle, resource/failure-injection, schema-readiness, staging Trend và staging Protocol consumer vẫn phải được đối soát theo plan §1.2–§1.6. Câu “only remaining gates” trong checkpoint cũ không còn là danh sách đầy đủ. Checkpoint trước đã xác minh browser staging P13/P14 trên candidate `31a5900`; PostgreSQL row query trực tiếp, organization-scope negative probe và release-manifest closure vẫn là gate riêng. P15 hiện đã có staging browser smoke trên candidate `09acb90`, nhưng direct PostgreSQL/scope/replay/release gates còn mở.

## Current checkpoint

- **Goal:** Hoàn thiện RT-CONNECT theo `plan.md` từ P0 đến P19 và thiết lập baseline vận hành P20.
- **Current phase:** P15 — Re-irradiation, recovery và bù fraction; P8/P9/P10/P11/P12/P13/P14 remaining release gates và các phase tích hợp sau vẫn mở.
- **Current status:** IN_PROGRESS — P15 local gates và authenticated staging browser happy paths đã pass trên candidate `09acb90`; replay cùng idempotency key, direct PostgreSQL checksum/scope, full error matrix và release-manifest closure chưa đóng.
- **Last authoritative check:** 2026-09-08 — staging API deployment `008ec1d1-3215-44c7-9d64-fb06dc024e58` báo successful; `/api/v1/ready` trả `schema_revision=20260908_0015`; P15 browser validate→save→refresh→export đã pass cho cả hai operation. Local backend `133 passed`, P15 API `5/5`, P15 engine/error `22/22`, Ruff/mypy, frontend lint/typecheck/build, OpenAPI và Alembic head cũng pass. Đây chưa phải P15 DONE-v2.
- **Next exact step:** dùng cùng request fingerprint để chứng minh idempotent replay của hai P15 operation, query PostgreSQL trực tiếp chỉ các aggregate/id/checksum redacted và chạy negative probe organization khác; sau đó cập nhật release manifest rồi tiếp tục P16.

## Source documents read

| Source | Version | Status |
| :--- | :--- | :--- |
| `business-analysis.md` | 0.15 | Business source; detailed workflow/error/recovery/state matrix, P12–P15 independent biological contracts and P0–P20 coverage index |
| `specification.md` | 1.9 | Behavior/data/error/state/numeric contracts; operation envelope, evidence schema and exact P10/P11/P12/P13/P14/P15 contracts |
| `technical-specification.md` | 1.6 | Architecture reference; P10/P11/P12 plus P13/P14/P15 bounded-context implementation addenda |
| `plan.md` | 2.9 | Phase/workflow/S-E/C/B tests, DoR/DoD, execution ledger, full coverage matrix, P10–P15 checkpoints and staging gates |

## Phase status

| Phase | Status | Evidence / next gate |
| :--- | :--- | :--- |
| P0 | DONE | Exit audit passed on 2026-09-05; baseline, traceability, module/route/environment registries and Railway failure issue recorded |
| P1 | DONE | Full local Compose build/health, in-container PostgreSQL migration, synthetic seed persistence, API readiness and web health passed on 2026-09-05 |
| P2 | FOUNDATION READY + LIVE SMOKE PASS | JWT contract, PostgreSQL, Railway staging/production deployment foundation, Supabase Auth configuration and public health/readiness smoke are evidenced; production promotion remains gated by later clinical modules |
| P3 | STAGING E2E PASS | Auth/API bootstrap, organization-scoped dashboard, first-use organization onboarding and protected web routes are deployed; authenticated staging session reached the real organization dashboard |
| P4 | STAGING E2E PASS | Organization/site/machine lifecycle is deployed; staging smoke created and displayed `Hong ngoc general hospital`, `Staging Synthetic Site` and `Synthetic QA Linac` |
| P5 | STAGING E2E PASS | Nested folder/QA case flow is deployed; staging smoke created `Staging P6 Smoke` and QA case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` |
| P6 | STAGING E2E PASS | Migration `20260907_0005`, artifact metadata/checksum, Input Manifest, duplicate upload, Railway S3-compatible storage, DICOM/measurement validator and QA Archive upload panel are deployed; authenticated synthetic upload created the manifest, validation returned `VALID` with 0 errors/0 warnings and the signed Download action was invoked |
| P7 | STAGING E2E PASS | Migration `20260907_0006`; protocol/rule seed, scoped Machine QA run lifecycle, draft revision, evaluation, immutable result/rerun/compare and trend projection are implemented; staging evaluate returned PASS for `output_factor=100`, `symmetry=1`, `flatness=100`, then rerun and compare preserved both histories |
| P8 | STAGING 2D/3D REDIS STREAM + FAILURE/RETRY PASS; FULL EXIT GATE OPEN | Migrations `20260907_0007` + reliability slice `20260908_0008`; organization/case-scoped preflight, PSQA/ENGINE_TEST profile, deterministic 2D/3D engine with standard-GY RTDOSE adapter, coverage/censor metrics, logical-role-aware artifact contract and database-fenced lease/attempt/outbox slice are implemented and locally tested. Staging has validated 2D and RTDOSE+measurement 3D PASS runs, compare/refresh persistence and controlled storage retry. Independent oracle, crash/ack/bounded retry/resource/large-input evidence and schema/release gates remain open. |
| P9 | STAGING E2E PARTIAL / LOCAL VERIFIED | Report revision/export browser smoke on staging; recheck current candidate, visual/export failure gate remains |
| P10 | STAGING SMOKE PARTIAL / EXIT OPEN | Migration `20260908_0010`, API/UI slice, 7 focused tests and authenticated staging trend smoke pass; large-series, complete negative matrix, visual/accessibility and release evidence remain |
| P11 | LOCAL VERIFIED / STAGING OPEN | Migration `20260908_0011`, library API/UI and local `3/3`; staging browser/consumer snapshot and full S/E/C evidence remain |
| P12 | STAGING E2E PASS / EXIT OPEN | Migration `20260908_0012`, Biological Hub route/API/UI, staging browser create/validate/edit/save/clone/archive/history đã chạy trên dữ liệu tổng hợp; PostgreSQL state, refresh/reconnect, renderer integration và full S/E/C remain |
| P13 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0013`, BED/EQD2 browser validate→save hai snapshot, history readback, chart/table và export đã chạy trên staging; direct PostgreSQL checksum/no-QA-linkage query và release manifest còn mở |
| P14 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0014`, browser validate-only/no mutation, save, preview reorder không persist, clone, JSON/CSV export và refresh history đã chạy; direct PostgreSQL row/checksum, organization-scope negative probe và release evidence còn mở |
| P15 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0015`, scalar re-irradiation/fraction-compensation engine/API/UI, recovery/sensitivity, nonuniform schedule, delivered-prefix alternatives, interruption/time model, immutable snapshot và JSON/CSV export; browser happy path đã pass trên deployment `008ec1d1-3215-44c7-9d64-fb06dc024e58`; replay/DB/scope/full S-E/release evidence còn mở |
| P16 | NOT_STARTED | Depends on P12/P13 |
| P17 | NOT_STARTED | Depends on P6/P8/P9 |
| P18 | NOT_STARTED | Integrated hardening and pilot |
| P19 | NOT_STARTED | Production remote web release |
| P20 | NOT_STARTED | Initial operations package after P19 |

## Live Google Stitch evidence

- Project: `RT-connect`.
- Project ID: `14242591911141046021`.
- Visibility: `PUBLIC`.
- Device baseline: `DESKTOP`.
- Design System: `Clinical Precision Interface`, asset `105b9f4e25334bbcbc6c94d588ee29f9`.
- `list_screens` returned six active resources: four application screens plus logo and avatar.

| Active application screen | Screen ID | Module |
| :--- | :--- | :--- |
| Trang chủ - Home Dashboard | `70b9f1d256884221ae20e63b5244db11` | MOD-01 |
| Kho lưu trữ QA & Thư mục | `4c9ec57310fd404cbae3b53b0bab2368` | MOD-03 |
| Phân tích PSQA Gamma Workspace | `ffb87901b3194bd3aff8760c54c2f9f4` | MOD-04/MOD-06 |
| Trình biên soạn Báo cáo - Report Builder Studio | `a1478466ace843c5aaf9a15dfc58273e` | MOD-07 |
| Biological Toolkit — Independent Calculation Hub | `b32ef9de691f48449ec23e491a6b634d` | MOD-10/P12 |

`get_project` still exposes the four old Biological instances as `hidden`. They are deprecated and must not be restored or used as design-to-code sources. P12 now has a new active design source; P13–P15 will create new screens one at a time in the same project. P12 screenshot asset is `50e2c49b3ec743a59f9d99e8b13e694f` and the generated HTML asset is `d79a76c00dd64ea4a8d7384095860552`.

## Live Railway evidence — verified 2026-09-06

- Project: `prolific-learning` (`339f2c50-ddd7-491f-8c4e-da2a2d169502`).
- Production: environment `910dff25-75b6-42b2-bf6b-e2601ba9d7d2`, API `RT-connect`, PostgreSQL `Postgres`.
- Staging: environment `b0ab34e5-0ff4-479d-8232-659d175e9e2f`, API `gleaming-cooperation`, PostgreSQL `Postgres-Q1Hc`.
- API region in both environments: `us-west2`; the obsolete `sfo` alias was removed from API service configuration after blocking a production deployment.
- Production deployment `ec813793-4e29-4edb-b5d7-f323264da403`: `SUCCESS`, commit `c52b61412c1e1e65b7fca53d7e4d600f85a2dd7e`.
- Staging deployment `2b5270d1-9704-49b3-b3d8-0f8be130d02e`: `SUCCESS`, commit `9bf96e92f6853d5650312c5fcd82ff67a7f85c1b`.
- Both API services use `/apps/api`, `/apps/api/Dockerfile`, `PORT=8000`, `/api/v1/health` and `alembic upgrade head`.
- Public smoke: production and staging both returned HTTP 200 with `status=ok` from `/api/v1/health` and `status=ready` from `/api/v1/ready`; correlation IDs were present.
- PostgreSQL services retain their current persistent-volume region configuration; no database region migration was performed without backup/restore evidence.

## Live Railway storage evidence — verified 2026-09-07

- A persistent Railway S3-compatible storage bucket was deployed in the staging environment for P6 artifact objects; it is not the API container filesystem.
- The bucket was provisioned in Railway's default US West region and exposes an S3-compatible endpoint with automatic region handling. The six staging API variables required by `MinioObjectStorage` were configured without printing their secret values, and the API service was redeployed afterward.
- A direct non-PHI storage probe passed for both path-style and virtual-host-style addressing: put, get, presigned URL generation and delete all succeeded. The bucket remained empty after the probe.
- Staging API health and readiness remained HTTP 200 after the storage-variable redeploy. The remaining evidence is the authenticated web upload → validation → signed download smoke test using the repository fixture.

## Live Railway P8 queue evidence — verified 2026-09-08

- Staging Redis service `Redis` (`ca18f134-82fb-44a1-ac5c-cde76fb33882`) is online and connected to both the API and private `RT-connect-gamma-worker-staging` service.
- Worker deployment `fb446c0e-2a1b-4a17-88f3-aeb8b5318e3c` from commit `5ec12fb` is active and successful. Its deployment log records `Gamma worker starting queue_backend=redis_stream stream=rt-connect:gamma group=rt-connect-gamma` followed by `Gamma worker using Redis Streams queue`.
- After the worker restart, the authenticated Gamma Workspace submitted run `e084529d-6bb1-4119-ae0a-f4da7d371cac`; the run reached `COMPLETED`, `PASS`, 100% (4/4 evaluated and passing points), target 95%, excluded 0 and Gamma P95 `0.0708333333333318`.
- Redis console evidence for the same staging queue: `XLEN rt-connect:gamma = 2`; consumer group `rt-connect-gamma` has 2 consumers, `pending = 0`, `entries-read = 2` and `lag = 0`. This proves publish → claim → analysis completion → acknowledge for the current 2D synthetic scope. It does not by itself close the authenticated queue-metrics API, failure/retry or RTDOSE/3D commissioning gates.
- The deployed web Status page called the authenticated `/api/v1/gamma/queue-metrics` endpoint successfully and displayed `redis_stream · available · configured`, stream `2`, pending `0`, consumers `3`, and organization run counts queued/running/retrying/failed all `0`.

## Live Railway P8 failure/retry evidence — verified 2026-09-08

- The test used the existing valid synthetic reference/evaluation artifacts in QA case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`; no patient data was used.
- To create a controlled staging failure, the private Gamma worker's object-storage bucket setting was temporarily pointed to a nonexistent staging-only bucket. The API accepted the job and run `26a54046-1f20-454c-b3f4-e766937f30d6` reached `FAILED`, progress `100%`, attempt `1`, with error `GAMMA_STORAGE_UNAVAILABLE` and message `Gamma input could not be read from object storage.`
- The real staging bucket setting was restored. Railway showed the worker Online with no staged variable changes remaining.
- From the authenticated Gamma Workspace, `Retry job` re-enqueued the same run. It reached `COMPLETED` / `PASS` at attempt `2`, with `100%` (4/4 evaluated and passing points), excluded `0` and Gamma P95 `0.0708333333333318`.
- This closes the live staging failure/retry/recovery evidence for the current 2D synthetic adapter. It does not close the RTDOSE/measurement, 3D, large-input or clinical commissioning gates.

## Live Railway P10 Trend evidence — verified 2026-09-08

- Commit `b8c7911` deployed the P10 API migration; public API `/api/v1/ready` returned `status=ready`, `schema_revision=20260908_0010`, and `/api/v1/version` returned `version=9262bfd`, `environment=staging`, `schema_revision=20260908_0010`.
- Web commit `d15738f` deployed successfully on `RT-connect-web-staging`; authenticated browser loaded `/app/trend` and showed Build `9262bfd`, `API THẬT`, six organization-scoped trend points and three compatible series for `Synthetic QA Linac`.
- Baseline workflow: a baseline with explicit effective time before the synthetic points was created and applied; flatness/output-factor displayed delta `0.0000`, while the deliberately mismatched symmetry value displayed `PASS · OUTLIER` and delta `-99.0000`. This is UI behavior evidence on synthetic data, not a clinical limit.
- Maintenance workflow: `Staging QA maintenance smoke` was created for the synthetic machine and appeared in the organization timeline as revision `1`, status `ACTIVE`; the trend point values were unchanged.
- Rebuild workflow: authenticated `Rebuild projection` returned `0` new and `6` existing points, demonstrating the current projection is idempotent for this staging dataset. Day aggregation displayed three buckets, each with count `2`, preserved min/max and two source runs.
- This evidence closes only the basic authenticated P10 staging smoke. Source drill-down/aggregate export download, large-series budget, full P10 S/E/C matrix, visual/accessibility review and P8/P9 remaining release gates must still be recorded before `DONE-v2`.

## Local P11 QA Protocol Library evidence — verified 2026-09-08

- Migration `20260908_0011_protocol_library.py` upgraded successfully on local PostgreSQL and is the current Alembic head. It adds protocol description/applicability/source/lineage/revision fields and rule references without changing the old P7 snapshot semantics.
- `tests/test_protocol_library.py` passed **3/3**. The focused suite covered validate-only with no mutation, create DRAFT, DRAFT edit with optimistic revision conflict, activation, immutable ACTIVE behavior, clone deep-copy and lineage, compare, archive, default archived filtering, organization scope and Machine QA active-only selection.
- Backend full suite passed **81/81**; Ruff and strict mypy passed. Frontend lint/typecheck/Vitest `1/1` and production build passed; the build emits only the known large-bundle warning.
- OpenAPI was regenerated after registering the P11 router. The P11 UI route is `/app/qa-protocols`; the API base surface is `/api/v1/organizations/{organization_id}/qa-protocols`.
- This is local evidence only. P11 staging still requires deployment with schema `20260908_0011`, authenticated browser lifecycle, active protocol consumed by a new Machine QA/Gamma run, old snapshot readback, negative scope/conflict/persistence/capability cases, and release-manifest evidence.

## Local P12 Biological Hub evidence — verified 2026-09-08

- Migration `20260908_0012_biological_scenarios.py` upgraded successfully on local PostgreSQL and is the current Alembic head. It adds organization-scoped `biological_scenarios`, append-only `biological_scenario_revisions` and the read model for `biological_calculation_runs` without a mandatory QA-case/patient relationship.
- P12 API routes are registered under `/api/v1/organizations/{organization_id}/biological`; validate-only, create DRAFT, DRAFT patch with optimistic revision, save to SAVED, clone with source lineage, archive, default archived filtering, revision history, summary/tools and scoped calculation reads are implemented.
- Focused `apps/api/tests/test_biological.py` passed; full backend suite passed after updating the expected schema revision to `20260908_0012`. Ruff/mypy passed, OpenAPI was regenerated, and frontend lint/typecheck/Vitest/build passed. The Vite build emits only the known large-bundle warning.
- The P12 web route is `/app/biological` and uses the generated Stitch screen `b32ef9de691f48449ec23e491a6b634d`. P13, P14 and P15 are now available; P16 remains explicitly `PLANNED`/disabled. The UI does not create fake calculation runs and does not link scenarios to QA cases automatically.
- P12 staging browser smoke: authenticated synthetic flow created `STAGING_P12_BIO`, validate-only returned no-mutation success, create/edit/save produced revisions, clone created `STAGING_P12_BIO_COPY_1D3A5958`, archive preserved history, and archived filtering displayed both states. PostgreSQL-state/query, refresh/reconnect, full negative matrix and P9 independent Biological report integration remain open.

## Local P13 BED/EQD2 evidence — verified 2026-09-08

- Migration `20260908_0013_bed_eqd2_calculations.py` upgraded successfully on local PostgreSQL; it adds nullable `idempotency_key` for legacy P12 read rows and an organization-scoped unique index for executable calculation retries. The API default/Compose example schema revision is `20260908_0013`.
- The pure engine `services/bed_eqd2_engine.py` implements finite/nonnegative/positive/integer validation, deterministic pair derivation, explicit `D ≈ n×d` tolerance, valid zero-dose handling, source/reference checks, fixed-n/fixed-d curve generation, duplicate-series/point-budget checks, unrounded LQ calculation and canonical chart checksum.
- P13 API routes are registered under `/api/v1/organizations/{organization_id}/biological`: validate-only, calculation create/replay, chart preview and JSON/CSV export. Every executable result stores scenario revision, raw/normalized input, source, curve, model key/version, result/table/chart checksum and idempotency identity; chart preview is non-persistent.
- The P13 UI route is `/app/biological/bed-eqd2`; it selects a SAVED scenario/revision, exposes fractionation/source/curve controls, displays primary values plus a synchronized chart/table/history, and labels the output as an independent estimate rather than QA/prescription. Stitch screen generation was attempted for the new route but the service returned unavailable; the UI therefore reuses the active Clinical Precision Interface design system and existing Biological Hub visual language.
- Focused P13 engine/API/biological tests passed **10/10**; full backend suite, Ruff, strict mypy, frontend lint, typecheck, Vitest **1/1**, production build and local PostgreSQL migration pass on the working tree candidate. The build emits only the known bundle-size warning.
- This is local evidence only. P13 staging still requires deploy on the candidate SHA, `/api/v1/ready` schema `20260908_0013`, authenticated browser validate→calculate→replay→chart preview→export, PostgreSQL snapshot/checksum/no-QA-linkage evidence, and release-manifest verification.

## Local P14 Plan Comparison evidence — verified 2026-09-08

- Migration `20260908_0014_plan_comparison.py` upgraded successfully on local PostgreSQL; `BiologicalComparisonRun` stores organization/scenario/revision scope, immutable ordered option/input/result snapshots, model/version, warning/error snapshots, idempotency key, actor and timestamps. The unique idempotency constraint is organization-scoped.
- P14 source resolution accepts only organization-scoped, `BED_EQD2` and `COMPLETED` P13 calculation snapshots. The pure engine compares 2–10 distinct options, validates common scenario/revision/tissue/model context, keeps alpha/beta mismatch as `COMPARISON_ALPHA_BETA_MISMATCH` warning with ranking disabled, computes signed absolute/percent delta and returns `null + BASELINE_ZERO` for a zero baseline denominator.
- API routes are registered under `/api/v1/organizations/{organization_id}/biological/comparisons`: validate-only, create/replay, list, detail, non-persistent chart reorder preview, clone and JSON/CSV export. Create/clone plus audit are transactional; retry with the same fingerprint returns the existing snapshot, while a different payload with the same key returns `COMPARISON_IDEMPOTENCY_CONFLICT`.
- The web route `/app/biological/compare` uses the active Clinical Precision Interface visual language. It has an empty state when fewer than two P13 snapshots exist, stable option IDs, baseline selector, compatibility notice, validate/save actions, result table, BED/EQD2 chart, non-persistent reorder preview, history, clone and export actions. It does not add QA/patient/TPS/PACS linkage.
- Focused P14 engine/API/biological tests passed **15/15**. Full backend pytest, Ruff, strict mypy, frontend lint, TypeScript typecheck, Vitest, Vite build and OpenAPI regenerate/check passed on the working tree candidate. Vite retains only the known bundle-size warning.
- This is local evidence only. P14 staging still requires the candidate deployment, readiness schema `20260908_0014`, two source P13 snapshots, authenticated browser validate→save/replay→refresh→reorder/clone/export flow, PostgreSQL row/fingerprint/checksum query and organization-scope negative check.

## Local P15 Re-irradiation/Fraction Compensation evidence — verified 2026-09-08

- Migration `20260908_0015_reirradiation.py` upgraded successfully on local PostgreSQL; Alembic reports `20260908_0015 (head)`. It creates `biological_reirradiation_runs` with organization/scenario/revision lineage, operation type, immutable input/result/warning/error snapshots, model/version, idempotency key, actor, timestamps and organization-scoped indexes/unique constraint.
- The pure P15 engine validates course roles, tissue/OAR dose rows, Gy units, finite numeric values, D/n/d or nonuniform schedules, alpha/beta provenance, recovery range/source, context mismatch, sensitivity, spatial capability and compensation prefix/alternative/interruption/time-model rules. It returns deterministic `result_sha256` snapshots and never produces voxel accumulation or prescription output.
- API routes are registered for validate-only, synchronous create/replay, list, detail and JSON/CSV export for both `REIRRADIATION` and `FRACTION_COMPENSATION`. Validate-only does not insert. Create commits run plus audit; same organization/key/fingerprint replays, different fingerprint conflicts, and persistence failures roll back.
- Frontend routes `/app/biological/re-irradiation` and `/app/biological/fraction-compensation` use the shared Clinical Precision Interface language. They expose saved scenario/revision selection, course×tissue matrix, recovery/sensitivity, planned/delivered prefix, alternatives, interruption/time model, validation, immutable result/history and export states. The page labels all outputs `SCENARIO / ESTIMATE ONLY`.
- Local verification: `tests/test_re_irradiation.py` **5/5**, `tests/test_re_irradiation_engine.py` **22/22**, full backend **133 passed**, Ruff, strict mypy, frontend lint/typecheck/build and OpenAPI regenerate/check passed. The Vite build retains only the existing bundle-size warning.
- This is local evidence only. Staging still requires the candidate deployment, schema/readiness check, authenticated browser workflow for both operations, remote export, direct PostgreSQL row/fingerprint/checksum, explicit out-of-organization negative probe and release manifest. P15 spatial accumulation remains intentionally unavailable.

## Live Railway P15 Biological smoke evidence — verified 2026-09-08

- Candidate `09acb90` deployed successfully to staging API deployment `008ec1d1-3215-44c7-9d64-fb06dc024e58`; the API readiness endpoint returned HTTP 200 with `schema_revision=20260908_0015`. The web bundle served the P15 routes `/app/biological/re-irradiation` and `/app/biological/fraction-compensation`.
- Re-irradiation browser flow used the saved synthetic scenario `Staging P12 Biological Scenario rev2 · STAGING_P12_BIO`, saved revision `3`, with prior/current courses `60 Gy / 30 fractions / 2 Gy` and alpha/beta `10 Gy`. Validate-only returned `valid` and did not create a snapshot. Save created snapshot `ebc07188-82f2-4d4d-b443-a86105efbc3f`, status `COMPLETED`, result checksum `c5d80c8a8a1250b4be683fcb7f2fb988545784e9b5d055e573627de843f88068`; the UI displayed no-recovery BED `144`, recovery BED `144` for `NONE`, and EQD2 `120`.
- After navigation/reload, the same re-irradiation snapshot remained in history with the same checksum. JSON export returned HTTP 200 and the UI reported a successful download. This demonstrates browser/API/readback/export for the scalar operation; it does not yet demonstrate same-key replay or direct SQL.
- Fraction-compensation browser flow used planned doses `[2,2,2,2,2]`, delivered prefix `[2,2]`, alternatives `[2,2,2]` and `[2.5,2.5,1]`, alpha/beta `10 Gy`. Validate-only did not mutate; save created snapshot `2e9f2767-daa4-4774-a48f-6f1ca47f8ad9`, status `COMPLETED`, result checksum `796fbc91e5b0cc2a7b3fc679c8acbbcd4026e9549858b1999dab407697ba86cf`. The UI showed planned BED `12`, two delivered prefix fractions locked, alternative deltas `0` and `0.15`, and warning `NO_REPOPULATION_CORRECTION` for the `NONE` time model.
- Fraction-compensation JSON and CSV export actions both returned HTTP 200 in the API console. The browser retained the result and history after the operation. Spatial accumulation was not requested as an available capability and no QA-case/patient/TPS/PACS linkage was created.
- **Evidence level:** `STAGING_SMOKE_VERIFIED` for deploy, readiness, authenticated validate-only/no-mutation, save, persisted readback and export of both operations. Still open before P15 `DONE-v2`: same-key idempotent replay, direct PostgreSQL aggregate/id/checksum query, explicit out-of-organization negative probe, full error/fault matrix, release manifest and any independent clinical/scientific validation required by intended use.

## Live Railway P13/P14 Biological smoke evidence — verified 2026-09-08

- Candidate: commit `31a5900`; API deployment `60f181b8-15b9-4377-be9f-7b0635a93127`; web deployment `bcac0a5e-ee4f-47b9-8b1e-40ac744a3a85`; web Build `9262bfd`; API `/api/v1/ready` reported schema `20260908_0014`. The browser used the authenticated staging URL `https://rt-connect-web-staging-staging.up.railway.app` and the existing synthetic organization/scenario only.
- P13 browser flow: the BED/EQD2 route created/read two immutable `COMPLETED` calculation snapshots in the same saved scenario revision `f9fafce0-e224-40b6-8b2a-a9952093f8dc`. Snapshot `4ca56a08-6929-472e-8740-fe15f4f439e6` used `D=60 Gy, n=30, d=2 Gy/fx, α/β=10 Gy`; snapshot `7c229a9c-dff2-4d2d-9eba-3a2bbd6acfbe` used `D=70 Gy, n=35, d=2 Gy/fx, α/β=10 Gy`. The second snapshot displayed `BED=84 Gy`, `EQD2=70 Gy`, history count `2`, and the route reloaded the persisted history after navigation.
- P14 `Validate only` returned `VALIDATION OK` and `Preview không ghi database`, with preview checksum `42885d2c53744a93afed582ba364b1a5b02ebe24cc953ea781d48d13d172927d`; history remained empty immediately before save. The comparison used stable options `option-a`/`option-b`, baseline `option-a`, and the two P13 snapshots above.
- P14 save created comparison `93e281f6-7c35-4f44-8af4-f280f3267c73`, status `COMPLETED`, model `biological.plan-comparison / p14-comparison-1.0.0`, result checksum `42885d2c53744a93afed582ba364b1a5b02ebe24cc953ea781d48d13d172927d`. The result table showed baseline `70 Gy / BED 84 / EQD2 70` and option B `60 Gy / BED 72 / EQD2 60`, with deltas `-12 Gy`, `-14.286%`, `-10 Gy`, `-14.286%`.
- P14 reorder preview returned `PREVIEW · NOT PERSISTED`; its presentation checksum was `81df25686dcf77e2a9237eec831ced5ce6913944c0480d4f720e1cd5367dfff0`, while persisted history retained checksum `42885d2c...` and baseline `option-a`. This demonstrates that presentation order is not used as the baseline and does not overwrite the saved result.
- Clone created `0cc43c7e-aa0f-4d76-bdc6-a3f05d4e5450` with name `P14 treatment plan comparison (clone)`, history count `2`, the same source option values and checksum `42885d2c...`. JSON and CSV export actions both returned the UI success message for the cloned persisted snapshot. A fresh navigation to the P14 route loaded both comparison rows from the API, confirming browser refresh/reconnect readback.
- Scope boundary: this smoke used only synthetic staging data and did not create any QA-case, patient, TPS or PACS linkage. It is browser/API smoke evidence, not a direct SQL query. Direct Railway PostgreSQL row/fingerprint/checksum verification, an explicit out-of-organization negative probe and the release manifest remain open before P13/P14 can be labeled `DONE-v2`.

## Historical Railway evidence (superseded)

> Snapshot superseded on 2026-09-06: staging and production now have separate API/PostgreSQL services, both deployments succeeded with `PORT=8000`, healthcheck `/api/v1/health`, pre-deploy `alembic upgrade head`, and public `/api/v1/health` plus `/api/v1/ready` returned HTTP 200. The older lines below are retained as historical P0/P2 evidence.

> Current deployment IDs: staging `bfc15784-6b59-418d-bba4-134f4a8154af` on `2754013`; production `85d1ba15-f45c-4958-8ebd-fcf09cbf75ef` on `a721cff` (runtime code from `5a5069f`).

- Project: `prolific-learning` (`339f2c50-ddd7-491f-8c4e-da2a2d169502`).
- Workspace: `Mạc Đăng Quang's Projects` (`53fb850d-a59c-4690-816f-01aea06f0645`).
- Only environment: `production` (`910dff25-75b6-42b2-bf6b-e2601ba9d7d2`).
- Only service: `RT-connect` (`9544c3e6-c8bd-4c29-b62e-c6172eb51af3`).
- Latest deployment: `FAILED`, deployment `b8037f6c-720c-407c-b5e4-34421358b4a3`, stopped.
- No service/custom domain and no Railway bucket were present in the status payload.
- Account and project token scopes were verified without printing token values.
- Railway CLI was not installed globally; `npx @railway/cli` version `5.49.1` was used read-only.
- Workspace usage query returned `UNAUTHORIZED`; exact billing/usage remains unavailable with the supplied token scope and must not be guessed.

Failed deployment root cause from build log: Railpack could not determine a build because the deployed commit contained only documents/static files and no `start.sh`, Dockerfile, Python/Node application manifest or supported runnable source. No redeploy was attempted.

## Repository evidence

- Repository contained only the four canonical Markdown files before P0 artifact creation.
- `.env` is Git-ignored and untracked.
- Secret values were not read into output; only key names were inventoried.
- User-owned deletions are preserved: `UI-UX.md`, `DESIGN.md`, `Biological-toolkit.html`.
- User-owned rename is preserved: `technical.md` → `technical-specification.md`.
- No reset, checkout or restoration of deleted files was performed.

## P0 deliverables

| Deliverable | Location | Status |
| :--- | :--- | :--- |
| Baseline snapshot | `docs/p0-baseline.md` | Verified |
| Traceability matrix | `docs/traceability-matrix.md` | Verified |
| Module registry | `docs/module-registry.md` | Verified |
| Route registry | `docs/route-registry.md` | Verified |
| Environment/secret inventory | `docs/environment-inventory.md` | Verified |
| Railway failed-deployment issue | `docs/issues/railway-failed-deployment.md` | Verified |

## Tests and checks

- P0 live Stitch project/screen/design-system check: PASS.
- Railway account-token project query: PASS.
- Railway project-token scope query: PASS.
- Railway status query: PASS.
- Railway failed deployment log retrieval: PASS.
- Railway workspace usage query: UNAVAILABLE (`UNAUTHORIZED`), recorded without guessing cost.
- Documentation consistency scan: PASS — source hashes equal recorded baseline; legacy hidden Biological IDs have no active mapping; all 17 modules occur in registry and traceability matrix.
- Secret scan: PASS — no `.env` value was found in tracked Markdown; inventory contains variable names only.
- Git diff check: PASS — only CRLF conversion notices were emitted; no whitespace error was reported.
- P0 exit audit: PASS — canonical technical filename, no UI-UX dependency, all four active application screens have owners, all other module screen gaps are explicit, Stitch/Railway IDs are recorded.
- P1 API pytest: PASS — 7 tests; FastAPI health/version/error/correlation contracts verified.
- P1 API quality: PASS — Ruff and strict mypy on 15 source files.
- P1 migration contract: PASS — Alembic revision `20260905_0001` renders PostgreSQL DDL successfully; up/down functions are present.
- P1 OpenAPI: PASS — generated contract at `docs/openapi.json` verifies reproducibly.
- P1 API process smoke: PASS — temporary local Uvicorn process returned `health=ok`, a correlation ID and version metadata; process was stopped and port released.
- P1 web quality: PASS — lint, TypeScript type check, 1 component test and production Vite build.
- P1 web E2E: PASS — 1 Playwright Chromium test against production preview build.
- P1 dependency checks: PASS — Python `pip check`; production Node `npm audit --omit=dev --audit-level=high` found no vulnerability.
- P1 source secret scan: PASS — no value from local `.env` appeared outside ignored environment files.
- P1 Compose verification: PASS — Docker Desktop Linux engine built the complete stack; all five services healthy; clean PostgreSQL migration, synthetic seed persistence, API readiness and web health passed. The scoped test stack and volumes were removed by the verifier.
- P2 JWT security contract: PASS — 17 API tests cover missing Bearer, missing configuration, valid asymmetric token, expiry, issuer, audience, role, signature and JWKS-client failure; Ruff and strict mypy pass. This is local cryptographic evidence, not a live Supabase sign-in result.
- P2 deployment preparation: PASS — `apps/api/railway.toml` now applies the baseline migration before deploy; staging Railway/Supabase variable contracts and runbooks are in `deployment/`.
- P2 Railway deployment foundation: PASS — effective settings were applied directly in staging and production; both deployments use `PORT=8000`, `/api/v1/health`, `alembic upgrade head`, and both public `/health` plus `/ready` smoke checks returned HTTP 200.
- P2 Railway permission audit: account token can read production status but `railway link`/environment mutation is rejected with `UNAUTHORIZED`; usage query is also unauthorized. No Railway resource was created or changed.
- The permission-audit snapshot above is historical; the current Railway service settings were successfully changed through the dashboard and are recorded in the superseding live evidence note above.
- P2 Railway source audit: the old failed deployment analyzed `aa5dce6`, but `origin/main` now points to `dc6ee79` and contains the API/web source. The deployment for `dc6ee79` was skipped because the GitHub secret-guard job failed; API and web jobs passed. The CI guard has been corrected to allow `.env.example` templates while rejecting private environment files and credentials.
- P2 post-change local regression: PASS — full `scripts/verify-p1.ps1 -WithContainers` completed after JWT, CORS and Railway manifest changes: 17 API tests, lint/type checks, migration SQL, web checks, five healthy Compose services, in-container migration, synthetic seed persistence, API readiness and web health. The scoped stack and test volumes were removed.
- P2 Stitch recheck: PASS — project `RT-connect` remains public with the Clinical Precision Interface design system, the four active QA application screens, and four hidden/deprecated Biological screen instances. No Stitch design was altered during P2.
- P3 design: Login screen `3b857ee77e7a434d8cfdcda32fd62cdb` generated in the active RT-connect Stitch project using the Clinical Precision Interface design system; no patient data or secret was sent to Stitch.
- P3 local implementation: PASS — `UserIdentity`/`OrganizationMembership`, session bootstrap and organization-scoped dashboard endpoints; migration `20260906_0002`; backend lint, strict mypy and 20 tests pass. Frontend Supabase session/auth routes, protected dashboard and API-backed empty/populated/error states lint/type-check/test/build successfully.
- P4 local implementation: PASS — migration `20260906_0003` adds organization/site/machine lifecycle fields and append-only audit events; all CRUD/list/archive mutations resolve organization scope from the verified identity before resource lookup. Rename preserves `stable_machine_id`; duplicate IDs and second ambiguous organization contexts return explicit conflicts. Backend Ruff, strict mypy and 26 tests pass; frontend organization management page, API client, lint, TypeScript check, Vitest and Vite build pass. No live Auth or staging P4 workflow has been claimed.
- P5 local implementation: PASS — migration `20260906_0004` adds nested organization folders and QA cases; folder rename/move/archive preserves QA case identity, archive does not hard-delete history, case references require an active site/machine/folder in the same organization, and searches support text, folder and QA-cycle filtering. Backend Ruff, strict mypy and 29 tests pass; frontend QA Archive route/API client, lint, TypeScript check, Vitest and Vite build pass. No live Auth or staging P5 workflow has been claimed.
- P6 local implementation: PASS — migration `20260907_0005` adds `artifacts`, `input_manifests` and `validation_runs`; MinIO/S3 storage port, byte-for-byte SHA-256 upload, duplicate detection, signed-download contract, metadata-first DICOM validation and `gamma.measurement.v1` validation are implemented. Focused artifact tests, full API regression, strict mypy, Ruff and frontend checks pass.
- P6 staging evidence: PARTIAL PASS — commit `5b6bf78` deployed successfully to `Railway-API-staging`; the live API exposes the artifact/upload/validation paths; the web staging bundle contains P6 upload UI; the authenticated dashboard, organization, site, machine, folder and QA case are reachable; the persistent Railway bucket is deployed and S3 operations pass. Live artifact upload/validation/download is pending the synthetic fixture selection in the browser.
- P6 authenticated staging evidence: PASS — the user-selected `docs/fixtures/gamma-measurement-v1-smoke.json` appeared as `gamma-measurement-v1-smoke.json` (572 bytes) in QA Archive; upload created the Input Manifest, validation displayed `VALID: 0 lỗi, 0 cảnh báo`, the artifact status changed to `VALID`, and the UI invoked its signed Download action.
- P7 local implementation: PASS — migration `20260907_0006` adds organization-scoped protocol versions/rules, `machine_qa_runs` and `trend_points`; the rule engine covers range/min/max/absolute or percent deviation and N/A, records missing/unit errors, snapshots protocol rules, prevents edits after evaluation, and projects numeric metrics to trend points. Focused P7 tests (3), full API regression (36), strict mypy, Ruff, OpenAPI regeneration/check, frontend lint/typecheck/test/build all pass.
- P7 staging evidence: PASS — deployments `483f1a30-af73-46ea-be9f-a70627802a3a` (API) and `b16a2e5c-f2ea-414e-9c92-d85bf1aea57c` (web) reported successful; authenticated Machine QA seeded `MACHINE_QA_BASELINE` v1, created run `9b18fa2f-7a02-4154-853a-270e890fcabe`, evaluated `100 / 1 / 100` as `PASS`, created rerun `5ac1a1c1-a985-4a40-97e4-0c8a8b6864c0`, evaluated it as `PASS`, and the compare table returned all three metric snapshots.
- P8 local implementation: PASS — migration `20260907_0007` adds `gamma_analysis_runs`; local unreleased migration `20260908_0008` adds fenced lease/attempt/outbox tables; preflight requires two organization/case-scoped validated artifacts; PSQA/ENGINE_TEST profile, idempotency, configuration/checksum/engine snapshots, coverage policy and max-gamma censoring are implemented. The deterministic 2D/3D engine supports the tested `gamma.measurement.v1` slice; result snapshots include map, histogram, pass rate/coverage metrics, percentiles and warnings; the worker persists heartbeat/progress/attempt/failure state. Redis Streams enqueue/claim/ack/reclaim and queue metrics remain available with DB polling fallback when `REDIS_URL` is absent. Full API suite (58), mypy/Ruff and frontend checks pass locally.
- P8 local RTDOSE/3D adapter: PASS — `gamma-nd-p8.2` accepts 2D/3D inline measurement JSON and axial IEC-aligned RTDOSE DICOM; the standard DICOM profile requires `DoseUnits=GY` with explicit `DoseGridScaling`, while JSON CGY conversion is an explicit extension. The adapter validates RTDOSE geometry/scaling and supports a mixed RTDOSE-reference plus measurement-evaluation 3D golden run. The focused adapter suite passed 3/3, including strict RTDOSE metadata validation; staging execution with a real uploaded RTDOSE + measurement pair, independent oracle and large-input behavior remain open.
- P8 staging infrastructure evidence: PASS — commit `310ec13` is deployed successfully to staging API (`d4991d54-2239-4c7d-a7bf-194c01cc4d66`) and web (`eff1f6ca-d9f1-4dec-aecd-955083ecd7ba`); a private `RT-connect-gamma-worker-staging` service (`a1e0c389-e527-4d4c-995e-2a48f4795dda`) uses `/apps/api`, `python -m rt_connect_api.worker`, no public domain and no HTTP healthcheck, with deployment `4c45c69a-457d-4e8f-b1d9-3deb8d48409b` reported `SUCCESS`. This proves infrastructure deployment only, not Gamma job completion.
- P8 authenticated staging golden smoke: PASS for the current 2D synthetic scope — after API deployment `e3d5a46b-7e8f-47fb-a65d-0c4e477c8f61` from commit `1ad0fc3`, `gamma-reference-v1-smoke.json` and `gamma-evaluation-v1-smoke.json` were uploaded as `JSON`, both validated `VALID` with 0 errors/0 warnings, and the private worker completed runs `9c607a9d-0698-4fc4-bf3f-0b50c3bc474f` and `dd82bdbd-c5af-4929-85fd-c4bea595cadd` with `COMPLETED`, `PASS`, `100%` (4/4 points), target `95%`, excluded `0`, and Gamma P95 `0.0708333333333318`. The second run was compared against the first; a full browser refresh restored both completed histories and the result snapshot.
- P8 corrective implementation: commit `1ad0fc3` makes artifact deduplication type-aware, preserves a manifest for a new logical role and makes readiness use the current app settings; commit `50c7917` adds `logical_roles` to artifact responses so Gamma can select Reference/Evaluation consistently after refresh. Backend `42/42`, Ruff, mypy and frontend typecheck/lint/test/build pass locally. The post-deploy browser smoke passed: after a full reload, Reference selected `gamma-reference-v1-smoke.json` and Evaluation selected `gamma-evaluation-v1-smoke.json`.
- P8 queue implementation: commit `4d09e64` adds `redis==6.4.0`, Redis Streams transport (`XREADGROUP`/`XAUTOCLAIM`/`XACK`), API dispatch and retry integration, authenticated `/api/v1/gamma/queue-metrics`, worker Redis mode and focused fake-client tests. Commit `5ec12fb` adds a non-secret worker startup log for the selected backend. Railway staging has a private `Redis` service and the API/worker service variables contain the private `REDIS_URL` reference; the deployed worker and live Redis-consumer smoke are now evidenced above.

## Current blockers and required gates

The older Railway-history bullets below are retained as evidence of earlier incidents. The current gates are:

- The authenticated staging user and organization onboarding path are working. A fresh browser test should still be repeated after session expiry before treating the auth path as operationally stable.
- P8 current remaining gates: the 2D synthetic worker flow, Redis Streams claim/ack, queue-metrics API, result snapshot, compare and browser refresh persistence are evidenced, as is a controlled staging `FAILED → retry → COMPLETED` recovery. The local RTDOSE/3D/profile/coverage/fencing slice is tested, but migration `20260908_0008` deployment, authenticated staging execution with a real RTDOSE + measurement pair, independent oracle, crash/ack/bounded retry/resource evidence and large-input behavior remain open; P8 is not complete until those gates are implemented and verified or the plan scope is explicitly revised.
- The P7 branch has not been promoted to production. Production promotion remains blocked until Gamma/report/trend/protocol gates, backup and rollback evidence exist.

- Correction on 2026-09-05: both Railway tokens are present in root `.env` and authenticate successfully through the Railway API. Account-token access resolves project `prolific-learning`; project-token scope resolves its production environment. The earlier missing-token report was incorrect. Standard dotenv parsing supports spaces around `=` and quoted values.
- Supabase URL and publishable key are present as names but have empty values. This is the remaining Auth configuration dependency.
- Current Supabase project `RT-connect` is the production `main` branch. Preview branching requires a paid Supabase Pro upgrade, so it is not a suitable free staging isolation mechanism. Do not silently use that production Auth project as the formal staging identity plane; create a separate staging project or explicitly accept a documented temporary shared-auth exception.
- Actual credentials were found in `.env.example` and replaced with empty placeholders; the user's `.env` was preserved.
- Railway account token lacks the write scope needed to create/link staging and the usage scope needed to view costs. A project-write credential is required before any billable Railway resource can be provisioned.
- The current Railway production service has not deployed `dc6ee79`; it still reports the old failed deployment and the new deployment as skipped. After the CI fix is pushed and green, verify Railway sees `dc6ee79` before any staging/production deployment decision.
- The live Railway service metadata still reports `rootDirectory=null` and `dockerfilePath=null`. Configure `/apps/api` on a staging service/environment before testing the Railway Dockerfile; do not use the current production service as the P2 test target.

## Known limitations

- Production has not yet received the P6 artifact branch; promotion remains intentionally gated by the staging artifact E2E and later clinical-module gates.
- The current browser automation cannot inject a local file into the file chooser; the final P6 web smoke therefore requires a manual selection of the repository's synthetic fixture or an equivalent user-driven browser action.
- Four Biological designs must be regenerated in P12–P15.
