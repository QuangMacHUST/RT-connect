# RT-CONNECT IMPLEMENTATION PROGRESS

Revision hiện hành: `business-analysis.md` v0.26, `specification.md` v1.27,
`technical-specification.md` v1.26 và `plan.md` v4.23.

## P01 — clean Docker foundation re-verification — local verified — 2026-09-11 / `7d0cd51`

- `scripts/verify-p1.ps1 -WithContainers` đã chạy trên checkout sạch: backend **199 passed**, Ruff PASS, strict mypy PASS trên 47 source files, Alembic SQL render đến schema `20260909_0019` PASS; frontend lint/typecheck/Vitest **19/19**/8 files và production build PASS.
- Compose đã build và khởi động PostgreSQL, Redis, MinIO, API, worker và web ở trạng thái healthy; `alembic upgrade head`, seed synthetic, kiểm tra machine persistence qua PostgreSQL, API `/health`, API `/ready` và web `/health` đều PASS. Script đã cleanup container, network và named volumes test.
- Evidence: [p1-local-docker-verification-20260911-7d0cd51.json](docs/evidence/p1-local-docker-verification-20260911-7d0cd51.json). Đây là local foundation evidence; không đóng các gate authenticated staging, provider fault, backup/restore, rollback, release, pilot hoặc production/clinical readiness.

## P06 — staging RTDOSE signed-download round-trip — verified content / filename open — 2026-09-11 / `67cc42d`

- Từ case staging `ed7ddbe5-811a-4463-a270-b0386f64644d`, Download đã trả đủ 898 bytes của `gamma-rtdose-v1-smoke.dcm`; SHA-256 của content tải về khớp fixture gốc `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`.
- Edge giữ file ở tên `Unconfirmed 912860.crdownload` trong thời gian quan sát dù content đã đủ và hash khớp. Vì vậy content/hash round-trip là **PASS**, còn browser final filename rename là **UNVERIFIED**; không dùng filename để phủ nhận hoặc khẳng định tính đúng của content.
- Evidence: [p06-staging-rtdose-download-20260911-67cc42d.json](docs/evidence/p06-staging-rtdose-download-20260911-67cc42d.json). Đây là read-only download của fixture đã được cho phép; không upload, thay thế, xóa fixture hoặc tạo Gamma run.

## P12/P09 — Biological scenario to report integration — local verified — 2026-09-11

- API `POST /api/v1/organizations/{org}/reports` now resolves a `BIOLOGICAL` source by `scenario_id` inside the requested organization, reads the current `BiologicalScenarioRevision`, and pins scenario metadata plus the full scenario snapshot into `ReportRevision.source_snapshot`. Missing scenario/revision fails closed with `REPORT_SOURCE_UNAVAILABLE`; the initial lookup carries organization scope.
- Added regression coverage for current-revision snapshotting and an out-of-scope organization probe: focused report tests **8/8 PASS**. Existing generic biological report behavior remains covered.
- Biological Hub now has `Tạo report` for each scenario. The authenticated mutation opens `/app/reports?reportKey=...`; Report Builder selects the requested report from query state and clears that state when starting a new report.
- Frontend gates after this slice: lint, typecheck, Vitest **19/19**, and production build **PASS**. Build emits the existing Vite chunk-size advisory only.
- This is `LOCAL_VERIFIED_SLICE`, not P12/P09 staging completion. Staging report creation, PostgreSQL row/snapshot readback, refresh after source revision change, export/render evidence, complete negative matrix, and release manifest remain open. No additional RTDOSE was uploaded and no Gamma run/report was created on staging in this checkpoint.

## P08 — API transform/provenance fail-closed regression — local verified — 2026-09-11

- Bổ sung preflight kiểm tra `transform_to_reference` trước khi enqueue: ma trận 4×4 phải finite, đúng hướng/đơn vị, và transform của reference/evaluation phải giống nhau trong sai số `1e-9`. RTDOSE DICOM native được biểu diễn rõ bằng identity transform; transform non-identity vẫn fail-closed vì chưa có adapter đã kiểm thử.
- Bổ sung kiểm tra provenance SHA-256 ở engine: giá trị phải là chuỗi 64 ký tự hexadecimal, không chấp nhận chuỗi bất kỳ chỉ có độ dài 64.
- Regression test cho transform mismatch, measurement thiếu transform và provenance SHA-256 không phải hexadecimal đều fail đúng mã lỗi. Focused Gamma/DICOM/artifact/worker: **31/31 PASS**; Ruff và strict mypy: **PASS**. Full backend được chạy trong lúc worktree dirty và chỉ còn các test release-manifest cố ý chặn với `WORKING_TREE_DIRTY`; sẽ xác nhận lại release gate sau khi commit trên worktree sạch.
- Đây vẫn chỉ là local implementation evidence. Không upload thêm fixture RTDOSE, không tạo Gamma run mới và không nâng P08/P20 thành DONE; các gate staging geometry-negative, worker fault/retry/resource, oracle promotion, release và clinical readiness vẫn mở theo `plan.md`.

## P20-W01/P08 — staging parity after P8 implementation candidate — verified checkpoint — 2026-09-11 / `d64e64b`

- Sau khi push candidate `d64e64ba5ac2f17b91d35c231a70092a81101a9c` lên nhánh `codex/p4-org-site-machine`, API và web staging đã phục vụ đúng candidate đó; API `/api/v1/health`, `/api/v1/ready`, `/api/v1/version` đều trả hợp lệ, schema `20260909_0019` giữ đúng. Đây là checkpoint trước commit docs tiếp theo `20d34ba`.
- `scripts/verify-public-deployment.ps1` với exact SHA và schema đạt **15/15 PASS**, gồm public health/readiness/version, schema parity, OpenAPI CT preview + organization membership/invitation, unauthenticated 401 boundary, web index/bundle, UI markers và exact source marker. Evidence: [p20-staging-public-smoke-20260911-d64e64b.json](docs/evidence/p20-staging-public-smoke-20260911-d64e64b.json).
- Fixture RTDOSE tổng hợp đã được người dùng cho phép và đã tồn tại một lần trong case `ed7ddbe5-811a-4463-a270-b0386f64644d`; không tạo bản trùng, không upload thêm artifact và không tạo Gamma run mới trong checkpoint này. Evidence upload/readback: [p06-staging-rtdose-upload-20260911.json](docs/evidence/p06-staging-rtdose-upload-20260911.json).
- Đây là `STAGING_VERIFIED_SLICE` cho deployment/public contract. Không suy diễn thành authenticated P8 Gamma run, worker parity, queue/resource/fault matrix, storage reconciliation, backup/restore, rollback, pilot hoặc clinical readiness; các gate đó vẫn mở theo `plan.md`.

## P08 — coordinate-frame/axis-order/transform contract — local verified — 2026-09-11 / `23b88d0`

- Gamma measurement mới phải khai `PATIENT_LPS` hoặc `IEC_PHANTOM`, frame ID, canonical axis order, transform `SOURCE_TO_REFERENCE` bằng ma trận finite 4×4 và provenance type/version/SHA-256. RTDOSE thiếu `FrameOfReferenceUID` bị từ chối; DICOM native identity được phân biệt với legacy grid.
- API preflight kiểm basis/frame ID/axis order/transform compatibility trước enqueue; engine snapshot physical frame trong kết quả. Transform non-identity hiện chưa có adapter nên fail-closed; không auto-align, đổi trục hoặc suy luận từ tên file. JSON legacy chỉ giữ cho cặp ENGINE_TEST cũ và không được trộn vào PSQA với DICOM/explicit measurement.
- Evidence: focused Gamma/DICOM/artifact/worker **30/30 PASS**, full backend **195 passed**, strict mypy/Ruff PASS, independent oracle **6/6 PASS**, local Compose Redis/worker verifier `passed=true`. Files: `docs/evidence/p8-independent-gamma-oracle-20260911.json`, `docs/evidence/p8-local-redis-worker-smoke-20260911.json`.
- Đây là local implementation evidence trên synthetic fixture. Staging vẫn phải deploy đúng candidate, revalidate input đã tồn tại, kiểm negative geometry/axis/transform/scale, queue/resource và public parity; chưa upload thêm RTDOSE, chưa tạo Gamma run mới và chưa nâng P08 thành DONE.

## P07 — Machine QA revision/idempotency hardening — local verified — 2026-09-11 / `c6348c3`

- Evaluate hiện nhận `expected_revision` tùy chọn để không phá caller cũ; UI chính gửi revision mà API trả về sau autosave. Revision lệch trên DRAFT trả `MACHINE_QA_REVISION_CONFLICT` và không chạy rule engine.
- PostgreSQL finalize dùng row-lock để chỉ một transaction chuyển run sang trạng thái terminal. Evaluate lại run `COMPLETED` trả snapshot cũ, không tạo `TrendPoint` thứ hai; seed protocol lặp lại không tạo protocol/rule mới. Snapshot run giữ `p11.protocol-snapshot.v1` với source, capability và đầy đủ rule fields.
- Local checks: `test_machine_qa.py` + `test_trend.py` **15/15 PASS**, Ruff, mypy, web lint/typecheck và planning verifier **21 phase / 0 lỗi**. Evidence: [p07-machine-qa-revision-20260911-c6348c3.json](docs/evidence/p07-machine-qa-revision-20260911-c6348c3.json).
- Chỉ đóng local slice P07-W01/W02/W04. Authenticated staging mutation/concurrency, full S/E/C, release handoff và production/clinical gates vẫn mở.

## P07 — staging source parity/public smoke — 2026-09-11 / `093fe98`

- Sau khi push candidate `093fe987ffac835eb04cc98c570d6a659c4a21fe`, public verifier đạt `15/15`, `failed_check_count=0`; API health/readiness/version, schema `20260909_0019`, OpenAPI route và unauthenticated organization boundary đều PASS; web index/bundle và exact-SHA marker cũng PASS.
- Đây chỉ là bằng chứng API/web public đang phục vụ đúng source candidate. Không suy diễn thành authenticated Machine QA mutation, stale revision conflict, double-submit/concurrent PostgreSQL, worker parity, full P07 S/E/C hoặc clinical readiness.
- Evidence: [p07-staging-public-parity-20260911-093fe98.json](docs/evidence/p07-staging-public-parity-20260911-093fe98.json).

## P19 — effective-settings verifier URL normalization — local verified — 2026-09-11

- `scripts/verify-railway-effective-settings.ps1` hiện chuẩn hóa `ExpectedApiBaseUrl` từ API origin hoặc origin đã có `/api/v1` thành contract base URL của web client; không còn false negative khi người vận hành truyền origin thuần.
- Chạy read-only trên staging bằng origin thuần sau sửa: `passed=True`, `failed_check_count=0`; không ghi secret hoặc giá trị database URL vào output.
- Quy tắc vận hành: `VITE_API_BASE_URL` phải là public API HTTPS origin kèm `/api/v1`, còn `CORS_ALLOWED_ORIGINS` chỉ là web origin; hai giá trị không được hoán đổi.

## P08 — Gamma local regression và independent oracle — local verified — 2026-09-11 / `8ea19f4`

- Recheck hiện hành đạt `23 tests passed` cho Gamma API/engine/DICOM/worker; independent oracle đạt `6/6` case, planning verifier đạt `21 phase / 0 lỗi`.
- Phạm vi đã kiểm lại gồm 2D/3D, RTDOSE GY + `DoseGridScaling`, từ chối orientation không hỗ trợ, dose unit không hợp lệ và spacing không dương, coverage, max-gamma censoring, PSQA preflight/resource limit, lease/fencing, terminal replay, bounded retry/ACK recovery và oracle GRID/BILINEAR + GLOBAL/LOCAL + RELATIVE/ABSOLUTE.
- Evidence: [p08-local-regression-20260911-edf3daa.json](docs/evidence/p08-local-regression-20260911-edf3daa.json). P08 vẫn mở các gate staging fault/ACK/reclaim/dead-letter, large-input/resource budget, geometry/scale negative matrix, oracle promotion và release handoff.

## P08/P19 — current staging parity after DICOM validation hardening — staging verified slice — 2026-09-11 / `6769a85`

- Railway GraphQL readback xác nhận API, web và worker staging đều `SUCCESS`, cùng exact source SHA `6769a852b9c4f1d412e21cf0d9f0b288028e3b7c`; deployment IDs lần lượt `122ec654-970c-4192-8515-d83915f8c5dc`, `26b8a7a5-ea7c-4efc-8df9-4950c6891839` và `44888678-2a03-49a8-aa9f-7c832deb88b9`.
- Public verifier đạt `15/15`, `failed_check_count=0`, API version/schema `6769a85… / 20260909_0019`, web bundle exact-SHA và Auth boundary public đều PASS. Evidence: [p08-staging-parity-20260911-6769a85.json](docs/evidence/p08-staging-parity-20260911-6769a85.json).
- Đây là source/runtime parity slice cho hardening DICOM. Không tạo artifact/Gamma run/report mới; P08 vẫn mở authenticated mutation trên candidate này, fault/ACK/retry/dead-letter, large-input/resource, oracle promotion và release handoff.

## P06 — declared type và upload queue — local verified slice — 2026-09-11

- Artifact validator giữ declared `artifact_type` là hợp đồng chính: payload JSON được khai báo DICOM không đi vào measurement validator và trả `ARTIFACT_TYPE_MISMATCH`; test duplicate cùng checksum/type vẫn tái dùng artifact và thêm role thiếu theo organization scope.
- QA Archive đã chuyển từ upload đơn file sang queue theo case: có thể chọn nhiều file, snapshot `artifactType`/`logicalRole` lúc enqueue, upload tuần tự, giữ các file thành công khi một file lỗi và retry riêng file lỗi. Mỗi thao tác Download vẫn gọi API lấy URL mới thay vì giữ lại signed URL cũ.
- Local checks: backend `test_artifacts.py` `6 passed`; frontend lint, typecheck, Vitest `17/17` và production build PASS. Evidence: [p06-local-upload-queue-20260911.json](docs/evidence/p06-local-upload-queue-20260911.json).
- Đây là local implementation slice. Chưa đóng P06-W04/P06-VERIFY: staging browser queue với lỗi có chủ ý, storage fault/reconciliation, download byte re-hash và full S/E/C/release evidence còn phải thực hiện.

## P06-W04 — queue orchestration hardening — local verified — 2026-09-11 / `8c8f9bd`

- Tách điều phối upload queue khỏi `QAArchivePage`: batch dùng snapshot item, upload tuần tự, giữ success trước đó khi item sau lỗi, và retry chỉ nhận `FAILED` item thuộc case hiện hành; tránh stale lookup trong async state.
- Local checks trên commit `8c8f9bdb5fb903ebec80e0a3832e743b974398ee`: lint, typecheck, production build và Vitest `8 files / 19 tests` đều PASS. Evidence: [p06-local-upload-queue-helper-20260911.json](docs/evidence/p06-local-upload-queue-helper-20260911.json).
- Đây vẫn là local hardening slice; staging fault/retry có chủ ý, storage reconciliation, signed-download byte re-hash và full P06 S/E/C/release vẫn mở.

## P20-W01 — final documentation/runtime parity checkpoint — staging verified slice — 2026-09-11 / `06b818f`

- Sau khi ghi evidence, API `07f847c0-7e05-470a-a161-3758ca174302`, web `0bab32af-56cb-450d-9754-39c4f5b3847f` và worker `a37687b6-b192-44ab-9a47-7acb5f919d85` đều `SUCCESS` trên source SHA `06b818fc6edc0ebe4353c1fd018c519ccfc6f25f`.
- Public verifier đạt `15/15`, `failed_check_count=0`, schema `20260909_0019`; health/readiness/version, OpenAPI/Auth boundary và web bundle source marker đều PASS. Evidence: [p20-staging-public-parity-20260911-06b818f.json](docs/evidence/p20-staging-public-parity-20260911-06b818f.json).
- Mốc này thay thế checkpoint runtime `7ee71c8` về mặt current-candidate; không thay đổi kết luận rằng P06/P20 full fault, restore, rollback, alert và handoff vẫn mở.

## P06/P20 — authorized RTDOSE staging upload và current web parity — staging verified slice — 2026-09-11 / `0abba6e`

- Theo xác nhận trực tiếp của người dùng, fixture tổng hợp `docs/fixtures/gamma-rtdose-v1-smoke.dcm` (898 bytes, SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`) đã được upload một lần vào case `ed7ddbe5-811a-4463-a270-b0386f64644d` (`P11 E2E Synthetic QA 20260910 B7C3`) trên staging với `REFERENCE/DICOM`.
- UI xác nhận tạo artifact và input manifest; validate trả `VALID`, `0` lỗi, `0` cảnh báo; preflight hiện `1 RTDOSE · 0 RTSTRUCT · 0 CT VALID`. Không tạo QA run/report mới và không chạm production. Evidence: [p06-staging-rtdose-upload-20260911.json](docs/evidence/p06-staging-rtdose-upload-20260911.json).
- API `c57d438d-ab28-473f-8d2a-6da3499a3a59`, web `bfb89696-b666-48e3-8a3a-74c2e60cfde2` và worker `4617b9ab-771e-40fc-b351-5ac03c106191` đều `SUCCESS` trên cùng source SHA `0abba6e229208ac75a9657a9ffc962086553d01f`. Public verifier đạt `15/15`, schema `20260909_0019`, và web bundle đã chứa marker upload queue.
- Đây là `STAGING_VERIFIED_SLICE`, không đóng P06-W04/P06-VERIFY: queue fault/retry có chủ ý, storage fault/reconciliation, signed-download byte re-hash, full S/E/C và release/handoff vẫn mở.

## P06/P20 — queue hardening deployed and exact-SHA parity — staging verified slice — 2026-09-11 / `7ee71c8`

- Sau khi queue orchestration được harden local, API `6265b273-2f52-4bc1-a4c1-2803f4164a4b`, web `90b74c9d-e655-4024-9238-64d900c496d2` và worker `eb4f6c5e-034b-4775-8898-f63a7ef8ebc7` đều `SUCCESS` trên source SHA `7ee71c8a46cba67fde14516d2d566598f3313fc2`.
- Public verifier đạt `15/15`, `failed_check_count=0`, API version exact SHA, schema `20260909_0019`, OpenAPI/Auth boundary và web exact-SHA marker đều PASS. Evidence: [p20-staging-public-parity-20260911-7ee71c8.json](docs/evidence/p20-staging-public-parity-20260911-7ee71c8.json).
- Đây là parity/runtime evidence cho candidate mới; không thay thế staging queue fault/retry, signed-download byte re-hash, storage reconciliation hoặc full P06/P20 S/E/C.

## P20-W01 — Operational status auto-refresh — local verified — 2026-09-11 / `7df7cb8`

- Trang `/app/system/status` đã bổ sung polling 30 giây cho health, readiness, version và queue metrics khi có session; polling vẫn chạy khi tab ở nền.
- Khi đang refresh, UI giữ dữ liệu quan sát gần nhất và hiển thị `Đang cập nhật…`; khi không refresh, UI hiển thị thời điểm `dataUpdatedAt` gần nhất để tránh hiểu nhầm dashboard là dữ liệu realtime liên tục.
- Local evidence: test `7 files / 17 tests`, lint, typecheck và production build đều PASS. Evidence: [p20-local-status-auto-refresh-20260911-7df7cb8.json](docs/evidence/p20-local-status-auto-refresh-20260911-7df7cb8.json).
- Đây mới là `LOCAL_VERIFIED`; chưa phải staging deployment, authenticated queue probe hoặc alert delivery đến kênh vận hành thật. P20-W01 và các gate P20 khác vẫn mở.

## P20-W01 — Operational status auto-refresh — staging partial — 2026-09-11 / `3d764e4`

- API, web và worker staging đã được deploy cùng source SHA `3d764e40bcec98c229eb9992d4af85636c6cf784`; deployment tương ứng là API `3c94f3c7-fab0-464c-abb6-ea61fc0d9494`, web `6cff64bd-54d5-480b-bfc6-05c9e4a4c7d1`, worker `c9a87b51-e060-43ab-b6cb-bee7165dc0b3`, cả ba `SUCCESS`.
- `scripts/verify-public-deployment.ps1` với expected SHA và schema `20260909_0019` đạt `passed=true`, `failed_check_count=0`, `15/15` checks; health/readiness/version, OpenAPI/Auth boundary và web bundle exact-SHA đều PASS. Evidence: [p20-staging-status-refresh-public-20260911-3d764e4.json](docs/evidence/p20-staging-status-refresh-public-20260911-3d764e4.json).
- Đây là `STAGING_PARTIAL`: chứng minh candidate đã lên đúng source và public contract, không chứng minh authenticated queue metrics, alert delivery, backup/restore, rollback hoặc production readiness. P20-W01 vẫn mở.

## P18/P20 — Phân biệt terminal failure counter với active outage — staging readback — 2026-09-11 / `1e97663`

- Status page staging đọc được Redis `available/configured`, stream `11`, pending `0`, cùng `failed=2`. Đối chiếu Gamma history cho thấy hai run FAILED là các negative validation path đã lưu: `d902d9c0-3b15-4367-8df9-ca0a6274c3f3` (`2D` với evaluation grid `3D`) và `e33968e2-1ac3-4db7-953f-4e97f78b2d0e` (reference/evaluation khác dimensionality); cả hai trả `GAMMA_DIMENSIONALITY_MISMATCH` đúng expected contract.
- UI và runbook đã đổi cách diễn đạt thành `failed (terminal history)` và yêu cầu mở error snapshot/attempt trước khi triage. Không retry, xóa hoặc reset hai run này; chúng là evidence negative test, không phải sự cố worker mới.
- Đây là readback/semantics evidence, chưa phải alert delivery, fault injection hoặc full P18 recovery gate.

## P20-W01 — Operational probe và schema-parity check — staging partial — 2026-09-11 / `3102119`

- Đã bổ sung `scripts/verify-operational-probes.ps1`, một probe fail-closed có thể chạy lại với đúng `ApiBaseUrl`, `WebBaseUrl`, release SHA và schema revision. Probe đọc riêng `/api/v1/health`, `/api/v1/ready`, `/api/v1/version`, kiểm schema parity, kiểm web `/app` và dò secret marker trong HTML; queue metrics chỉ chạy khi caller chủ động cung cấp access token và token không được ghi vào output.
- Chạy trên staging candidate `31021192c5dd4b726d8da2183d7e01d26d4e0df2` với schema `20260909_0019`: `passed=true`, `failed_check_count=0`, health/readiness/version/web và secret-marker checks đều PASS. Queue probe ghi `NOT_RUN` có chủ đích vì lần chạy public không cung cấp session token. Evidence: [p20-staging-operational-probes-20260911-3102119.json](docs/evidence/p20-staging-operational-probes-20260911-3102119.json).
- Negative control với expected version cố ý sai trả exit code `1`, `passed=false` và chỉ fail `api.version.expected`; chứng minh probe không biến source drift thành PASS. Alert tới kênh thật, authenticated queue probe, backup/restore provider, owner handoff và các gate P20 còn lại vẫn chưa đóng.

## P17/P19 — RTDOSE authorization + CT overlay recheck — staging partial — 2026-09-11 / `3e46479`

- Người dùng đã xác nhận cho phép sử dụng/upload fixture RTDOSE tổng hợp trong case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`. Fixture `gamma-rtdose-v1-smoke.dcm` đã tồn tại, `RTDOSE/VALID`, checksum local và prefix trên UI khớp (`ca5c9168eb9b...`); hệ thống không tạo artifact trùng.
- Commit `3e46479c8784cebdc5fd4c41e865645b3da9ac63` đã được deploy exact SHA cho API, web và worker; ba deployment đều `SUCCESS`. Public verifier đạt `15/15`, `failed_check_count=0`, schema `20260909_0019`, health/ready/version/OpenAPI/Auth boundary và web source marker đều khớp: [p19-staging-public-recheck-20260911-3e46479.json](docs/evidence/p19-staging-public-recheck-20260911-3e46479.json).
- Browser authenticated sau reload đọc đúng build `3e46479`, preflight `2 dose · 1 structure`, RTDOSE fixture đang được chọn, RTSTRUCT/ROI `#1 · P17_TARGET` và saved DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` vẫn `COMPLETED`; không tạo run/artifact mới.
- CT preview trên candidate mới hiển thị lát cắt `#1` ở trạng thái `LPS LINKED`, overlay `NEAREST_NEIGHBOR_IN_PATIENT_LPS`, ROI và crosshair dose-grid center. Kiểm tra lát cắt `#3` cho `NO DOSE OVERLAP` với cảnh báo rõ ràng và overlay rỗng, sau đó đưa lại về lát cắt hợp lệ. Evidence: [p17-staging-rtdose-ct-browser-recheck-20260911-3e46479.json](docs/evidence/p17-staging-rtdose-ct-browser-recheck-20260911-3e46479.json).
- Đây là staging authenticated readback/compatibility evidence, chưa đóng toàn bộ P17/P19. Full negative/fault/resource/volume, independent-oracle promotion, two-identity mutation E2E, provider restore, rollback, alert/owner handoff, browser filename finalization và production promotion vẫn mở.

## P17/P19 — final current-candidate parity and RTDOSE readback — staging partial — 2026-09-10 / `19857bd`

- Commit `19857bd8515bfbc86835527aadc145278b837dc3` đã được deploy thành công đồng thời cho API, web và worker staging. Deployment IDs là API `60c4bcde-2ddc-4b6a-b586-d51385926c1c`, web `7cd043f4-854d-4399-bdb3-dd2ff0639003` và worker `74c69765-7440-4953-9e30-21338b31fe2d`; cả ba `SUCCESS` và cùng source SHA.
- Public verifier theo exact SHA đạt `15/15`, `failed_check_count=0`, API health/ready/version, schema `20260909_0019`, OpenAPI, Auth boundary và web bundle marker đều PASS: [p19-staging-public-recheck-20260910-19857bd.json](docs/evidence/p19-staging-public-recheck-20260910-19857bd.json).
- Browser authenticated sau reload đọc đúng build `19857bd`, case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`, preflight `2 dose · 1 structure`, RTDOSE `gamma-rtdose-v1-smoke.dcm` `VALID` với SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, RTSTRUCT/ROI `#1 · P17_TARGET`, saved DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` và result SHA `cf2799b8afeafa68cf60a330eac9adff123cca5c7ceacfc0eab78132b0c0359c` giữ nguyên. Không tạo run/artifact mới và không upload trùng: [p17-staging-rtdose-authenticated-recheck-20260910-19857bd.json](docs/evidence/p17-staging-rtdose-authenticated-recheck-20260910-19857bd.json).
- Planning contract sau khi sửa expected versions của verifier đạt `passed=true`, `failed_check_count=0`, đủ 21 phase; evidence được giữ tại [p0-planning-contract-20260910-e5197ce.json](docs/evidence/p0-planning-contract-20260910-e5197ce.json).
- Đây vẫn là current-candidate parity/readback partial. P17/P19/P20 còn mở các gate full negative/fault/resource/volume, two-identity mutation E2E, provider backup/restore, rollback, alert/owner handoff, pilot và production promotion.

## P17/P19 — current candidate parity and RTDOSE authenticated recheck — staging partial — 2026-09-10 / `e5197ce`

- Sau khi commit tài liệu `e5197ce4634f93b81267479d9b68382e97f7e4e9` được push, web staging tự nhận candidate mới trong khi API/worker vẫn phục vụ `380012e`; public verifier với expected `380012e` đã bắt đúng drift ở `web.bundle.expected_version` (`1` lỗi). Evidence drift được giữ tại [p19-staging-public-recheck-20260910.json](docs/evidence/p19-staging-public-recheck-20260910.json).
- Đã yêu cầu redeploy có kiểm soát API, web và worker staging cùng SHA `e5197ce`; deployment mới lần lượt là API `d3e6c135-6602-420e-9609-d4ba9098e5fe`, web `b670b3de-cecc-473c-960b-58a7374fb1da` và worker `675a146e-cace-4c63-bf28-fdf7eca25bef`, đều `SUCCESS`. Không xóa database/object và không tạo lại fixture.
- Public verifier sau khi đồng bộ đạt `15/15`, `failed_check_count=0`, API version/readiness và web bundle cùng `e5197ce`, schema `20260909_0019`: [p19-staging-public-recheck-20260910-e5197ce.json](docs/evidence/p19-staging-public-recheck-20260910-e5197ce.json).
- Authenticated browser trên đúng candidate `e5197ce` mở lại case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`: preflight `2 dose · 1 structure`, RTDOSE `gamma-rtdose-v1-smoke.dcm` `VALID` với SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, RTSTRUCT hợp lệ, ROI `#1 · P17_TARGET`, DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` và result SHA `cf2799b8afeafa68cf60a330eac9adff123cca5c7ceacfc0eab78132b0c0359c` được đọc lại; không tạo run/artifact mới và không upload trùng. Evidence: [p17-staging-rtdose-authenticated-recheck-20260910-e5197ce.json](docs/evidence/p17-staging-rtdose-authenticated-recheck-20260910-e5197ce.json).
- Đây là parity và authenticated readback partial gate. P17/P19 vẫn mở full negative/fault/resource/volume, two-identity mutation E2E, provider backup/restore, rollback, alert/owner handoff và production promotion.

## P9 — PDF Unicode renderer correction — local verified / staging revalidation required — 2026-09-10

- Visual inspection of the previous staging PDF export found corrupted Vietnamese glyphs (`?`) even though the payload had a valid PDF header. This was treated as a release-blocking visual defect, not as a cosmetic warning.
- The renderer is now `report-renderer-0.2`: it embeds the pinned `DejaVuSans.ttf` asset, emits a Type0/CIDFontType2 Unicode font with `Identity-H` encoding, `ToUnicode` mapping and deterministic CID-to-GID mapping. `fonttools==4.63.0` is pinned in both `pyproject.toml` and `requirements.lock`.
- Local evidence: focused report suite `7 passed`, Ruff pass, strict mypy pass, wheel build pass, wheel inspection confirms `rt_connect_api/assets/DejaVuSans.ttf` is packaged, and Poppler visual inspection shows Vietnamese title/block text without fallback replacement.
- This correction is not yet a staging release. The new commit must be deployed to API/web/worker with exact-SHA parity; Report Builder must regenerate PDF/PNG/JSON/CSV from the staging DVH report, and the new PDF must be rendered and visually inspected before P9 can advance beyond partial verification. Existing staging evidence remains historical and is not silently rewritten.
- Local checkpoint evidence was followed by staging revalidation below; the public exact-SHA record is [p9-staging-unicode-public-smoke-20260910-380012e.json](docs/evidence/p9-staging-unicode-public-smoke-20260910-380012e.json).

## P9 — renderer-aware export idempotency correction — local verified / staging revalidation required — 2026-09-10

- Sau khi API chạy `report-renderer-0.2`, browser Report Builder cũ dùng lại key `report-{revision}-{format}` và nhận `EXPORT_IDEMPOTENCY_CONFLICT` với export cũ của renderer `0.1`. Đây là lỗi namespace tương thích khi renderer đổi phiên bản.
- Frontend đã thêm namespace ngẫu nhiên theo phiên trang vào idempotency key; cùng phiên vẫn replay đúng, nhưng lần tải trang sau renderer migration không bị khóa bởi export cũ. Server fingerprint và conflict semantics vẫn giữ nguyên.
- Local evidence: web lint, typecheck, Vitest `17/17` và production build pass. Commit này phải được deploy exact SHA cho web (và đồng bộ API/worker theo release policy) trước khi tạo lại export. Chưa ghi staging export mới và chưa đóng P9 visual gate.

## P9/P19 — renderer 0.2 + idempotency namespace — staging verified partial — 2026-09-10 / `380012e`

- API, web và worker staging đã chạy đồng bộ exact SHA `380012ed3f2140efd4f1560c2f627176831e495f`, schema `20260909_0019`; public verifier đạt `15/15`, `failed_check_count=0`. Deployment IDs lần lượt là API `a3d68476-d635-4c6d-9b6a-8ee6f338096f`, web `29f2ce35-2e49-415c-911e-e5184bcd074b`, worker `00aaaca7-1ba4-4089-a920-b56448e2dbfe`.
- Browser reload nhận build mới, mở report `P17 staging bound DVH report` rev 1 từ DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` và tạo bốn export mới: JSON `15,582` bytes, CSV `1,190`, PDF `382,747`, PNG `2,243`. JSON/CSV parse pass và ghi renderer `report-renderer-0.2`; PDF header/EOF, embedded Unicode font, ToUnicode, UTF-16 stream check và visual inspection pass; PNG signature pass.
- PDF staging đã được render thành PNG bằng Poppler và kiểm tra trực quan: `P17 staging bound DVH report`, `DVH và đánh giá giới hạn explicit`, `Cảnh báo và trạng thái review` đều hiển thị đúng tiếng Việt, không còn `?`. Report revision và DVH run không bị mutation; RTDOSE `gamma-rtdose-v1-smoke.dcm` chỉ được reuse, không upload trùng.
- Evidence chi tiết: [p9-staging-unicode-export-20260910-380012e.json](docs/evidence/p9-staging-unicode-export-20260910-380012e.json). Đây là `STAGING_UNICODE_EXPORT_CONTENT_AND_VISUAL_PARTIAL`; `.crdownload` là giới hạn quan sát filename của CUA harness, còn storage fault/retry, provider restore, rollback, full P18/P19 và production promotion vẫn mở.

## P17/P19 — current staging DVH export content verification — partial verified — 2026-09-10 / `c11fca0`

- Trên web build `c11fca0451f0a16d3bdf178383d7a8f45889e770`, authenticated browser mở lại case tổng hợp `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`, preflight `VALID`, saved run `d8230d1d-badd-4c0c-b044-dcc4434215a6`, engine `p17-dvh-1.1.0` và result SHA `cf2799b8afeafa68cf60a330eac9adff123cca5c7ceacfc0eab78132b0c0359c`.
- JSON export tải được `24,673` bytes, parse thành công, `run_id` và `result_sha256` khớp provenance UI. CSV export tải được `15,901` bytes, parse thành công với `25` rows và đủ section `input/result/warning`.
- Edge/CUA giữ hậu tố tạm `.crdownload`; đây là giới hạn quan sát của harness, không phải nội dung export thiếu. Bằng chứng content-level completion được ghi tại [p17-p19-staging-dvh-export-current-20260910-c11fca.json](docs/evidence/p17-p19-staging-dvh-export-current-20260910-c11fca.json). Không tuyên bố filename rename độc lập, production readiness, backup/restore, rollback hoặc full P18/P19.

## P9/P19 — current staging Report Builder export content verification — partial verified — 2026-09-10 / `bd47925`

- API/web/worker staging đã được đồng bộ exact SHA `bd4792505acea66113953f1d525e571cbe8ca155`; public verifier đạt `15/15`, schema `20260909_0019`. Deployment IDs: API `0ffdee7b-ff82-47a5-966c-304b046a6728`, web `02c59a4c-d78c-4cb5-b790-2462566ec715`, worker `11124466-d67f-4d6e-975c-a6090a35f112`.
- Browser đã chọn revision hiện có `P17 staging bound DVH report`, rev 1, source run `d8230d1d-badd-4c0c-b044-dcc4434215a6`, không lưu revision mới. Bốn export đều được tạo: JSON `15,582` bytes parse PASS; CSV `1,190` bytes parse PASS/27 rows; PDF `1,046` bytes có magic `%PDF`; PNG `2,243` bytes có signature PNG.
- JSON content giữ `report_key`, `source_id`, `source_type=DVH`, renderer `report-renderer-0.1` và `content_sha256` đúng revision. Evidence: [p9-p19-staging-report-export-current-20260910-bd47925.json](docs/evidence/p9-p19-staging-report-export-current-20260910-bd47925.json). `.crdownload` filename rename, visual human review, provider fault/retry, backup/restore và production gate vẫn mở.

## P8/P18/P19 — authenticated Gamma staging mutation E2E — partial verified — 2026-09-10 / `1badb66`

- Trên web build `1badb6616d1a68f7178b2aefd10c71adc95a826b`, phiên authenticated đã reuse fixture RTDOSE/VALID `gamma-rtdose-v1-smoke.dcm` trong case tổng hợp `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`; không upload bản sao. Evaluation là `gamma-measurement-3d-v1-smoke.json`; preflight hiển thị `VALID`.
- Negative path: cấu hình `2D / FULL_ROI / max_gamma=2` với evaluation grid 3D tạo run `d902d9c0-3b15-4367-8df9-ca0a6274c3f3`, `FAILED`, mã `GAMMA_DIMENSIONALITY_MISMATCH`; không phát sinh PASS giả.
- Positive path: đổi dimensionality sang `3D` rồi submit tạo run `86cc4d5e-4a87-4dcb-a6f5-94c125029c60`, `COMPLETED/PASS`, attempt `1`, 8/8 điểm, coverage `1`, Gamma P95 `0`, engine `gamma-nd-p8.2`; kết quả hiển thị lại trên UI sau mutation qua API/worker thật.
- Evidence: [p8-p19-staging-authenticated-gamma-e2e-20260910-1badb66.json](docs/evidence/p8-p19-staging-authenticated-gamma-e2e-20260910-1badb66.json). Đây là `STAGING_AUTHENTICATED_MUTATION_E2E_GAMMA` cho một identity/case; không đóng two-identity membership/invitation, direct PostgreSQL/Redis/object assertion, full staging fault/resource, provider restore, rollback, alert hoặc production promotion.

## P18 — staging API restart/recovery subtest — partial verified — 2026-09-10 / `135a24f`

- API staging được yêu cầu redeploy có kiểm soát cùng SHA `135a24faf4e2659b8c4fe9a98920efb357b392bc`, không xóa database/object. Probe đầu tiên sau yêu cầu trả `ready`, schema `20260909_0019`, version đúng SHA; public verifier sau propagation đạt `15/15`, `failed_check_count=0`.
- Browser authenticated reload route Gamma trên cùng case giữ API thật, build `135a24f…`, RTDOSE reference, measurement evaluation và `PREFLIGHT VALID`. Evidence: [p18-staging-api-restart-recovery-20260910-135a24f.json](docs/evidence/p18-staging-api-restart-recovery-20260910-135a24f.json).
- Đây là `STAGING_PARTIAL_API_RESTART_RECOVERY`; chưa phải API in-flight crash/ack test và không đóng DB/Redis/storage/renderer fault injection, restore, rollback hoặc full P18.

## P19-W01 — current staging release manifest — support evidence verified — 2026-09-10 / `9f8378c`

- Manifest redacted `staging-9f8378c` dùng deployment ID thật của API `db38336d-649e-4e05-baa8-2c669d486c2b`, web `d00e2ac1-d16b-41a6-88ae-48f9185a7608` và worker `07068c3e-15af-439f-a837-e565e90b2f84`; source SHA ba service cùng `9f8378c171f8b220f3c5b4159f505479bcd662c0`, schema `20260909_0019`, fixture hash và engine/renderer version đều được ghi.
- `scripts/create-release-manifest.py --verify-manifest` trả `valid=true`, `error_count=0`, `service_sha_parity=true`: [release-manifest-staging-9f8378c.json](docs/evidence/release-manifest-staging-9f8378c.json).
- Manifest ghi rõ production promotion bị chặn bởi provider backup/restore/rollback chưa có; `release_gate=ELIGIBLE` chỉ là integrity/source-parity gate của manifest staging, không phải P19 DONE-v2.

## P19 — staging exact-SHA public parity after P18 documentation packet — partial verified — 2026-09-10 / `8dffbb9`

- API, web và worker staging đã được yêu cầu deploy cùng source SHA `8dffbb9f48906131e99143f11b14d2abecd9a233`; public verifier kiểm tra exact SHA và schema `20260909_0019` đạt `15/15 PASS`, `failed_check_count=0`.
- Các assertion PASS gồm health/readiness/version, OpenAPI CT preview và membership/invitation, unauthenticated organization boundary `401`, web index/bundle, CT/membership markers và source SHA marker. Evidence: [p19-staging-public-smoke-20260910-8dffbb9.json](docs/evidence/p19-staging-public-smoke-20260910-8dffbb9.json).
- Đây là `STAGING_SOURCE_PARITY_AND_PUBLIC_SMOKE`, không nâng P19 thành DONE-v2: authenticated remote E2E, direct PostgreSQL/Redis/object evidence, fault/resource, backup/restore, rollback rehearsal, alert/owner handoff và production promotion vẫn mở.

## P19 — effective settings and authenticated remote readback — partial verified — 2026-09-10 / `3e79f48`

- `scripts/verify-railway-effective-settings.ps1` đọc Railway GraphQL bằng token chỉ trong bộ nhớ, kiểm tra API/web/worker cùng environment/service IDs, root/Dockerfile/healthcheck/pre-deploy/start command, required variable names, forbidden secret/browser-database names, private DB/Redis host classification, external S3 endpoint classification, CORS origin, Vite API/Auth values và worker không có public-domain variable. Kết quả `passed=true`, `failed_check_count=0`; report không chứa secret/database URL/patient data: [p19-railway-effective-settings-20260910.json](docs/evidence/p19-railway-effective-settings-20260910.json).
- Browser Edge với authenticated session đã đọc `/app/organization`, `/app/qa`, case DVH, `/app/reports`, `/app/biological` và `/app/system/status` trên build `3e79f488...`; DVH deep-link/reload giữ run `d8230d1d...`, D95 `5.200 Gy`, input RTDOSE/RTSTRUCT và warning CT dose-native. Evidence: [p19-staging-authenticated-remote-readback-20260910-3e79f48.json](docs/evidence/p19-staging-authenticated-remote-readback-20260910-3e79f48.json).
- Status page vẫn hiển thị `failed=1` ở Gamma queue counter lịch sử; readback không che giấu hoặc reset counter. Đây là tín hiệu để P18 fault/incident triage tiếp tục, không được diễn giải là toàn bộ queue đã PASS. P19 vẫn thiếu two-identity/mutation E2E, export/download, rollback, alert/restore và production promotion.

## P18 — staging worker restart/recovery subtest — partial verified — 2026-09-10 / `1c0210c`

- Worker staging được redeploy cùng commit hiện hành để mô phỏng restart có kiểm soát; Railway deployment `b007ed76-f3c6-4ba8-b70d-9001503ad9db` báo `SUCCESS`, metadata giữ root `/apps/api`, start `python -m rt_connect_api.worker`, không healthcheck/pre-deploy.
- Trước/sau trên `/app/system/status`, health `OK`, readiness `READY`, schema `20260909_0019`, schema parity `MATCH`, Redis `available/configured`, stream `9`, pending `0`; không upload, calculation, report hoặc database/object deletion. Evidence: [p18-staging-worker-restart-recovery-20260910-1c0210c.json](docs/evidence/p18-staging-worker-restart-recovery-20260910-1c0210c.json).
- Đây chỉ là `STAGING_PARTIAL_RESTART_RECOVERY`; API/DB/Redis/storage/renderer fault injection, retry/dead-letter, restore plan execution, volume/failure budget và full P18 regression/pilot vẫn mở.

## P8/P18 — local Redis worker reliability recheck — verified locally — 2026-09-10 / `3fe1db2`

- Sau khi service Redis trong `docker-compose.yml` được khởi động lại, `scripts/verify-local-gamma-queue.py` chạy trên commit `3fe1db2ab3139dec97090d0660278e419c8c6177` đạt `passed=true`; evidence: [p8-local-redis-worker-smoke-20260910.json](docs/evidence/p8-local-redis-worker-smoke-20260910.json).
- Happy path, duplicate dispatch/terminal replay, ACK failure recovery (`pending 1 → 0`, durable result giữ nguyên, không tạo attempt thứ hai), bounded retry/dead-letter sau 3 output và malformed-message quarantine đều PASS; stream/key/bucket/database tạm được cleanup.
- Đây là `LOCAL_COMPOSE_REDIS_WORKER`, không thay cho staging fault injection, resource/large-input, Railway provider backup/restore, pilot hoặc production release gate.

## P13 — staging BED/EQD2 calculation, immutable readback and export — partial verified — 2026-09-10 / `b712a383`

- Trên web build `b712a383fb806188c794481720e7051e89168fe4`, browser authenticated đã chọn scenario SAVED `P12_STAGING_BIO_SCENARIO_E21`, revision `3` (`e3bcce19-d769-4873-b0e6-45a82e66ee32`) và validate-only thành công trước khi lưu snapshot.
- Known-answer fixture `D=60 Gy`, `n=30`, `d=2 Gy/fx`, `alpha/beta=10 Gy` cho snapshot `COMPLETED`: `BED=72 Gy10`, `EQD2=60 Gy`; model `biological.bed-eqd2`, version `p13-lq-1.0.0`, chart dataset `303` points, checksum `0d9dff8f381ca6dd3066d0606ea2a8ad452bcd47c25e5fa300bddf8d866c4c19`. Snapshot ID `12ba1966-e214-414a-a7a2-d6155fc856d8`; idempotency key `p13-a3dfbcd2-d9f9-4d46-affc-3c718df0ca88`.
- Fresh browser tab đọc lại đúng build, scenario revision, trạng thái `COMPLETED`, BED/EQD2, model và checksum dataset. Export JSON và CSV đều trả toast thành công. Negative `D=61` với `n=30`, `d=2` bị chặn bằng `FRACTIONATION_INCONSISTENT` trên hai field, validate-only không tạo snapshot.
- Evidence: [p13-staging-bed-eqd2-20260910-b712.json](docs/evidence/p13-staging-bed-eqd2-20260910-b712.json). RTDOSE tổng hợp đã được người dùng cho phép nhưng artifact đã tồn tại trong case staging và được reuse; không upload trùng, không gắn biological calculation với QA case.
- Đây là `STAGING_PARTIAL_PASS`, chưa phải `DONE-v2`: direct PostgreSQL/checksum, cross-organization scope, idempotency replay/conflict, đầy đủ S/E/C/fault, release manifest và production parity vẫn mở. Filename completion của browser download vẫn `UNVERIFIED` do harness giữ đuôi tạm.

## P14 — staging same-context comparison, negative context guard and export — partial verified — 2026-09-10 / `46121fe`

- Trên build `46121fe90d3161253b4ee181b70463f6c738e619`, browser authenticated đã dùng hai P13 snapshot cùng scenario `45550fa4-b635-4d9f-90bb-e0d2cd77c531`, revision `e3bcce19-d769-4873-b0e6-45a82e66ee32`, tissue/model context: `70 Gy/35×2` (`ed85e343-687b-4385-a7da-e909458cece5`) và `60 Gy/30×2` (`12ba1966-e214-414a-a7a2-d6155fc856d8`). Validate-only pass không mutation.
- Comparison `57c90796-22a4-4c44-80c8-99934a479b1d` lưu `COMPLETED`, model `biological.plan-comparison · p14-comparison-1.0.0`, baseline `option-a`: `BED=84/EQD2=70`; option B: `BED=72/EQD2=60`, delta `-12 Gy/-14,286%` và `-10 Gy/-14,286%`, result checksum `42885d2c53744a93afed582ba364b1a5b02ebe24cc953ea781d48d13d172927d`.
- Fresh tab đọc lại kết quả và history `4` comparison; JSON/CSV export pass. Negative context mismatch khi chọn snapshot khác scenario/revision/tissue bị chặn bằng `COMPARISON_CONTEXT_MISMATCH`, không tạo snapshot. Evidence: [p14-staging-browser-20260910-46121fe.json](docs/evidence/p14-staging-browser-20260910-46121fe.json).
- Đây là `STAGING_PARTIAL_PASS`: direct PostgreSQL/scope, idempotency replay/conflict, đầy đủ S/E/C/fault, release manifest và production gates vẫn mở; filename completion download vẫn `UNVERIFIED`.

## P15 — staging re-irradiation and fraction compensation — partial verified — 2026-09-10 / `8d20fc2`

- Trên build `8d20fc2bf7d38985875b0ed1a2eaa826bf30586c`, re-irradiation đã validate→save→fresh readback với scenario revision `e3bcce19-d769-4873-b0e6-45a82e66ee32`; run `68c005dc-5a56-4d87-b7e6-1101a470307e` `COMPLETED`, model `biological.re-irradiation · p15-lq-reirradiation-1.0.0`, checksum `b871ba88a1120e35637732f95ad6367cca843fd6eaffb0c4553ca44bb486fd8c`, synthetic OAR tổng `BED=133.3333 Gy3`, `EQD2=80 Gy`, sensitivity recovery và trạng thái `SPATIAL UNAVAILABLE` đọc đúng.
- Fraction compensation đã validate→save→fresh readback; run `1b7b5cec-0170-409d-81fd-58e1237e2059` `COMPLETED`, model `biological.fraction-compensation · p15-lq-compensation-1.0.0`, checksum `a3067598239035f549c55a70c07f3741f4771f2e5f020dfb1908b33ebd272dd0`. Delivered prefix `2` fraction được khóa; standard còn lại `BED=12/EQD2=10`, alternative `BED=12.2/EQD2=10.1667`, delta BED `+0.2`.
- JSON/CSV export của cả hai operation pass. Spatial request trả warning `SPATIAL_ACCUMULATION_UNAVAILABLE` và không tạo snapshot; delivered prefix không khớp bị chặn bằng `FRACTION_SCHEDULE_INVALID` và không tạo snapshot. Evidence: [p15-staging-browser-20260910-8d20fc2.json](docs/evidence/p15-staging-browser-20260910-8d20fc2.json).
- Đây là `STAGING_PARTIAL_PASS`: direct PostgreSQL/scope, idempotency replay/conflict, đầy đủ S/E/C/fault, release manifest và production gates vẫn mở; spatial accumulation vẫn cố ý `UNAVAILABLE`, filename completion download vẫn `UNVERIFIED`.

## P16 — staging Knowledge Library explicit-use boundary and export — partial verified — 2026-09-10 / `8db01c9`

- Trên build `8db01c982d7169cb250f5bf070c558bab408b7ee`, Knowledge Library đọc lại entry `STAGING_P16_D95_20260910 · v1`, `DOSE_LIMIT`, `PUBLISHED · rev 2`, `UNVERIFIED`, context synthetic `P17_TARGET`, `D95 MIN 5 Gy`, content SHA `818d74572b3ca7eb6c1f8ccd43721448a99dfa8488dcaac774ba1b9f9adde85b`.
- Explicit-use với target `P17_DVH` và override hợp lệ `lower_limit=4.5` tạo snapshot prefix `d5f37a51275f4116248c…`, hiển thị `USER_OVERRIDE` và thông báo chưa tự động áp dụng vào calculator. Export JSON/CSV pass; fresh readback giữ entry `PUBLISHED` và counts `1/1/0`.
- Override field không được hỗ trợ bị chặn bằng `KNOWLEDGE_CONTENT_INVALID`, không tạo snapshot. Evidence: [p16-staging-browser-20260910-8db01c9.json](docs/evidence/p16-staging-browser-20260910-8db01c9.json).
- Đây là `STAGING_PARTIAL_PASS`: direct DB/scope, complete lifecycle/import/clone/compare matrix, P17 current-release binding, fault/idempotency, release manifest và production gates vẫn mở; reference `UNVERIFIED` không được diễn giải thành guideline/clinical approval.

## P17 — current staging RTDOSE/DVH readback after P16 — partial verified — 2026-09-10 / `8db01c9`

- Browser read-only recheck trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đọc được hai RTDOSE, một RTSTRUCT; fixture `gamma-rtdose-v1-smoke.dcm` `RTDOSE/VALID`, SHA-256 đầy đủ `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, đã tồn tại trước readback và không upload/duplicate artifact.
- Run `d8230d1d-badd-4c0c-b044-dcc4434215a6` được đọc lại `FULL`, ROI `#1 · P17_TARGET`, `D95=5.200 Gy`, limit `MIN 5 Gy`, margin `+0.200 Gy`, `explicit_selection=true`, `auto_applied=false`; trạng thái vẫn `REVIEW_REQUIRED` vì source library chưa `AVAILABLE` và CT không được chọn. Không tạo run mới.
- Evidence: [p17-staging-current-readback-20260910-8db01c9.json](docs/evidence/p17-staging-current-readback-20260910-8db01c9.json). Đây là `STAGING_PARTIAL_PASS`; direct DB/scope, full error/fault/resource/volume, cloud report/release và clinical source review vẫn mở.

## P19 — staging exact-SHA public verifier after P13 evidence — partial verified — 2026-09-10 / `796e078`

- API, web và worker staging đều deploy thành công từ exact source SHA `796e078af7ff66f4a1f8645061183859420bf785`; deployment IDs lần lượt `02c0d58d-c892-4834-a3ac-26364586bdfa`, `e56ac637-d30c-4ef6-8cc7-46c76da5024f` và `ca73840b-56e6-4a47-a415-69cfe9c1af21`.
- Public verifier đạt `15/15 PASS`, `failed_check_count=0`; `/health`, `/ready`, `/version`, schema `20260909_0019`, OpenAPI, membership boundary, web index/bundle và source marker đều khớp. Evidence: [p19-staging-public-smoke-20260910-796e078.json](docs/evidence/p19-staging-public-smoke-20260910-796e078.json).
- Đây chỉ là public contract/source-parity sub-gate. Authenticated E2E đầy đủ, private DB/Redis, fault/retry, backup/restore, rollback, alerting và production promotion vẫn mở.

## P12 — staging Biological scenario lifecycle and report integration — partial verified — 2026-09-10 / `e21ad4b`

- Trên web build `e21ad4b7f46aa990ae0bf0d7915b4199e66d62b4`, browser authenticated đã validate scenario tổng hợp mà không tạo mutation; tạo `P12_STAGING_BIO_SCENARIO_E21` ở `DRAFT rev 1`, sửa thành `DRAFT rev 2`, lưu thành `SAVED rev 3`, rồi fresh navigation đọc lại đủ history `3/2/1` cùng snapshot context.
- Clone tạo key `P12_STAGING_BIO_SCENARIO_E21_COPY_8BBA0AF2`; archive chuyển clone sang `ARCHIVED rev 2`. Bộ lọc archived mặc định ẩn clone và khi bật filter đọc lại đúng trạng thái archived. Negative `REFERENCE` thiếu `source_reference` bị chặn bằng `BIOLOGICAL_CONTEXT_INVALID`, không tạo mutation.
- P12-W04 report integration đã chạy: Report Builder lưu report `P12 Biological renderer staging` rev 1 với `source_type=BIOLOGICAL`, source ID `45550fa4-b635-4d9f-90bb-e0d2cd77c531`, block `BIOLOGICAL` và snapshot SHA-256 `f7867b11e05095c049dedf153f39db958828722b7761b185da223b53ff492ce0`; fresh readback giữ source/revision/block và hiển thị export JSON/CSV/PDF/PNG. Evidence: `docs/evidence/p12-staging-browser-20260910-e21ad4b.json`.
- Đây là `STAGING_PARTIAL_PASS`, không phải `DONE-v2`: direct PostgreSQL row/checksum, cross-organization negative probe, đầy đủ S/E/C, resource/provider fault, release manifest và production/rollback vẫn mở. Không có patient data hoặc QA run mới.

## P18 — local backup/restore support recheck — verified locally, staging gate open — 2026-09-10

- `scripts/verify-local-backup-restore.py` đã được bổ sung timeout cho từng lệnh Docker Compose và cơ chế dừng process tree trên Windows. Mục đích là khi Docker CLI/daemon không phản hồi, verifier phải trả evidence có giới hạn thay vì treo vô hạn.
- Lần chạy với `--command-timeout-seconds 10` trả về đúng `passed=false`; lỗi là `Docker Compose command timed out after 10s: ps --services --filter status=running`. `restore_database=null`, `restore_bucket=null`, không tạo restore resource và không có dump/object content được lưu. Evidence: `docs/evidence/p18-local-backup-restore-timeout-20260910.json`.
- Sau khi Docker Desktop/Linux engine được khôi phục, chạy lại với `--command-timeout-seconds 30` đạt `passed=true`: dump `169,924` bytes, row counts/fingerprints khớp, object inventory nguồn/đích đều `0` và hash khớp, database/bucket tạm được cleanup. Evidence: `docs/evidence/p18-local-backup-restore-20260910.json`.
- Evidence timeout trước đó vẫn giữ nguyên để chứng minh verifier fail-closed khi daemon không phản hồi: `docs/evidence/p18-local-backup-restore-timeout-20260910.json`.
- Trạng thái hiện tại là `LOCAL_VERIFIED` cho P18-W03a support path; provider backup/restore, RPO/RTO staging/production, fault injection, pilot/regression, rollback và P18/P20 release gates vẫn mở. Next exact action là kiểm provider restore drill trên candidate được phép, không dùng local PASS để suy ra remote PASS.

## P10 Trend — baseline/maintenance lifecycle controls — local verified — 2026-09-10

- Bổ sung client contract `PATCH /trend-baselines/{baseline_id}` ở web và một panel lifecycle thật trên Trend workspace. Người dùng có thể đọc toàn bộ baseline versions, sửa name/tolerance/action level/effective-to, archive version và giữ `expected_version`; version conflict được hiển thị qua cùng structured-error path, không ghi đè silent.
- Bổ sung maintenance revision panel: sửa marker, archive marker và gửi `expected_revision`; các field thời gian được chuyển lại ISO trước khi gọi API, còn lịch sử revision vẫn do API làm nguồn sự thật.
- Frontend regression mới: `TrendPage.test.tsx` kiểm chứng save baseline với version `2` và archive maintenance với revision `3`; toàn bộ web suite **17/17 PASS**, typecheck, ESLint và production build PASS. Vite vẫn còn cảnh báo chunk >500 kB, không phải lỗi release.
- Đây là `LOCAL_VERIFIED` cho UI/client lifecycle slice. Chưa được coi là staging evidence: cần staging deploy exact-SHA, authenticated edit/archive, stale revision `409`, reload/readback và kiểm tra không rewrite các điểm trend lịch sử.

## P10 Trend — staging baseline/maintenance lifecycle — partial verified — 2026-09-10 / `7343189`

- Candidate `734318947b8ae51c9eebc5275e76e6bdc6478d18` đã được mở trên staging bằng browser đã xác thực tại `/app/trend`. Workspace đọc được `4` baseline versions, `2` maintenance markers trước thao tác, `7` raw points và `4` compatible series.
- Baseline version `4` được sửa với `expected_version=4`, đổi tên thành `P10 lifecycle baseline 7343189`; UI trả toast thành công. Sau thao tác không tạo, xóa hoặc rewrite trend point nào.
- Maintenance marker `P10 baseline maintenance smoke` được archive với `expected_revision=1`; sau reload marker có revision `2`, status `ARCHIVED`, active marker count giảm từ `2` xuống `1`.
- Kiểm thử optimistic concurrency trên marker `Staging QA maintenance smoke`: tab thắng lưu title `Staging QA maintenance concurrent winner` với revision `2`; tab giữ revision cũ `1` bị từ chối bằng `MAINTENANCE_REVISION_CONFLICT`, và title stale không được ghi. Reload xác nhận title thắng vẫn là nguồn sự thật.
- Evidence: `docs/evidence/p10-staging-lifecycle-20260910-7343189.json`. Đây là `STAGING_PARTIAL_PASS`: visual/accessibility, complete P10 S/E/C, large-series, effective-time/rebuild, provider fault/resource, release manifest và production/rollback evidence vẫn mở; P10 chưa `DONE`.

## P19 — staging exact-SHA public smoke after P10 evidence — 2026-09-10 / `6df4ed5`

- Sau khi push packet P10, API, web và worker staging đã được yêu cầu deploy cùng source SHA `6df4ed581be91f193fe1a07c0fc3ef23c18d70c0`. Public verifier kiểm tra candidate thực tế: `15/15 PASS`, `failed_check_count=0`, API version và web bundle cùng exact SHA, schema `20260909_0019`, `/health` `ok`, `/ready` `ready`, OpenAPI routes và unauthenticated organization boundary đều đúng.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260910-6df4ed5.json`. Đây chỉ là public contract/source-parity evidence cho staging; không đóng P19 vì authenticated remote E2E, private dependency, backup/restore, rollback, alert và production promotion vẫn chưa có bằng chứng.

## P11 — staging protocol library and Machine QA consumer readback — partial verified — 2026-09-10 / `27bf051`

- Trên candidate `27bf051`, QA Protocol Library đọc được `3` version không archive; filter archived đọc lại `5` version gồm `STAGING_P11_E2E_B7C3 v1` và `STAGING_P11_QA v1` ở trạng thái `ARCHIVED`. Detail ACTIVE `MACHINE_QA_BASELINE v1` hiển thị revision `1`, `3` rule, source `USER_DEFINED` và applicability `{}`.
- Trên cùng candidate, Machine QA case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đọc đúng protocol ACTIVE, source/revision/rule count và thông báo đã pin protocol snapshot. Hai run lịch sử vẫn `COMPLETED/PASS`, không tạo run mới, không upload fixture và không thay đổi protocol trong lần kiểm tra.
- Evidence: `docs/evidence/p11-staging-consumer-browser-20260910-27bf051.json`. Đây là authenticated consumer readback `STAGING_PARTIAL_PASS`; full P11 S/E/C, cross-consumer recheck, direct DB lineage, release and production gates vẫn mở.

## P8 — staging RTDOSE/Gamma read-only recheck — partial verified — 2026-09-10 / `c9bdfe9`

- Trên candidate `c9bdfe9`, Gamma workspace của case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đọc đúng workflow `PSQA_GAMMA`, fixture reference `gamma-rtdose-v1-smoke.dcm` với fingerprint `ca5c9168…`, evaluation `gamma-measurement-3d-v1-smoke.json` với fingerprint `3ca7a85e…` và trạng thái `PREFLIGHT VALID`.
- Existing run đang chọn là `ENGINE_TEST`, không phải run PSQA 3D mới: `COMPLETED`, engine `gamma-nd-p8.2`, `4/4` điểm đạt, coverage `1`, gamma P95 `0.0708333…`, target `95%`; history hiển thị cả một run `FAILED` để truy vết. Lần recheck không tạo run và không upload fixture.
- Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-c9bdfe9.json`. Đây là read-only partial evidence; không suy ra từ đó rằng PSQA 3D, worker fault/retry, resource gate, independent oracle hay P8 release đã đóng.

## P8 — staging PSQA Gamma 3D synthetic E2E — partial verified — 2026-09-10 / `37130ec`

- Trên candidate `37130ec`, đã chạy đúng một job `PSQA_GAMMA` 3D bằng RTDOSE `gamma-rtdose-v1-smoke.dcm` và measurement `gamma-measurement-3d-v1-smoke.json` đã có sẵn trong case staging. Queue acknowledgement được hiển thị; run `1ac9b02b-3b06-4351-9ee7-fc100ba91bd2` kết thúc `COMPLETED/PASS`, engine `gamma-nd-p8.2`, `8/8` điểm đạt, coverage `1`, gamma P95 `0`.
- Lịch sử tăng lên `10` run và run failed cũ vẫn còn hiển thị; không tạo artifact mới và không upload lại RTDOSE. Đây là staging synthetic E2E happy path, không phải bằng chứng fault/retry/resource/clinical commissioning.
- Evidence: `docs/evidence/p8-staging-psqa-gamma-3d-20260910-37130ec.json`. P8 vẫn mở các gate âm tính, crash-after-commit/ack, bounded retry/dead-letter, workload lớn, independent oracle, release và production.

## P8 — staging RTDOSE_REQUIRED negative input — partial verified — 2026-09-10 / `37130ec`

- Với profile `PSQA_GAMMA`, chọn JSON `gamma-reference-v1-smoke.json` làm Reference bị chặn trước queue bằng trạng thái `PROFILE INPUT MISSING`, message yêu cầu RTDOSE DICOM `VALID`; nút enqueue bị disable.
- Khôi phục lại `gamma-rtdose-v1-smoke.dcm` làm Reference đưa preflight về `PREFLIGHT VALID`, nút enqueue hoạt động và history vẫn giữ `10` run; negative test không tạo mutation.
- Evidence: `docs/evidence/p8-staging-negative-rtdose-required-20260910-37130ec.json`. Đây mới là negative input slice; geometry/frame/dose-scaling, worker fault/retry/resource và release gates vẫn mở.

## P19 — final staging public verifier packet before next handoff — 2026-09-10 / `9fb58ac`

- Exact-SHA public verifier trên candidate `9fb58acadc78938022ffc308181625e0f1596386` đạt `15/15 PASS`, `failed_check_count=0`; API version, web bundle marker và ba service release SHA được kiểm theo candidate, schema `20260909_0019`.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260910-9fb58ac.json`. Phạm vi chỉ là public contract/source parity; P19 vẫn mở authenticated remote E2E đầy đủ, private DB/Redis, backup/restore, rollback, alert và production promotion.

## P10 — staging negative/accessibility recheck — partial verified — 2026-09-10 / `a30e365`

- Trên candidate `a30e365`, Trend workspace đã được đọc bằng accessibility tree: lifecycle tables/actions, filter controls, source links và error/empty/retry states đều có semantic text/controls đọc được.
- Đã kiểm trực tiếp ba negative case bằng browser authenticated: effective interval sai bị chặn với `TREND_BASELINE_INVALID`; metric không tồn tại trả `TREND_EMPTY` với `0` point/series và không zero-fill; timezone sai trả `TREND_TIMEZONE_INVALID` cùng retry. Sau khi khôi phục filter, readback vẫn giữ `7` raw points, `4` series, `4` baselines và `1` active maintenance marker, không có mutation phát sinh từ negative test.
- Evidence: `docs/evidence/p10-staging-negative-accessibility-20260910-a30e365.json`. Accessibility đạt partial; screenshot visual review, full S/E/C/large-series/effective-time/rebuild và release/production gates vẫn mở.

## P10 Trend — staging export, drill-down và negative recheck — 2026-09-10 / `6426ceb`

- Candidate `6426ceb50665f1ceae01e011f2ee5bf6b8a16d65` đang có API/web cùng source SHA; API `/health`, `/ready`, `/version`, OpenAPI và web bundle đạt **15/15 public checks**, schema `20260909_0019`.
- Fresh authenticated browser mở `/app/trend`, đọc được `7` raw points, `4` compatible series, `3` baseline và `1` maintenance marker. Drill-down từ Trend về case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` mở đúng Machine QA source, run `COMPLETED/PASS`, protocol snapshot và source run đều đọc lại được.
- Export theo bộ lọc hiện tại đã được tải và parse: CSV `2,018` bytes, `7` records, có header và bucket lineage; JSON `15,064` bytes, parse được với `4` series, `aggregate=raw`, timezone `Asia/Ho_Chi_Minh`. SHA lần lượt `dfe34e256a0d58f0f790d7d4f04a2916f03402a151aa49cd05e39842d9814f75` và `e5ba525cc37696974fe384526472284adb4478aa4c1b988c79b01c3601d174a4`.
- Negative filter `metric_does_not_exist` trả `TREND_EMPTY`, `0` point/series và không zero-fill. Gộp theo ngày với `output_factor` giữ `2` series, `3` compatible points, mean/min/max `100%` và không trộn protocol context. Evidence: `docs/evidence/p10-staging-trend-browser-20260910-6426ceb.json`.
- Đây là `STAGING_PARTIAL`: browser vẫn quan sát hậu tố `.crdownload`, nên final filename completion, large-series benchmark, projection rebuild/baseline mutation, full S/E/C, fault, accessibility và release/production gates còn mở. Không tạo QA run mới, không upload artifact và không dùng dữ liệu bệnh nhân/PACS.
- Sau khi checkpoint được commit thành `05ff3d29e24cb15826e8335a5a66d6f4bd32f87b`, API/worker staging đã được redeploy đúng SHA để giữ parity với web; public verifier lại đạt **15/15 PASS**, schema `20260909_0019`. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-05ff3d2.json`.
- Trên đúng candidate `2a381ba78ade65e5468d730c46adc6856f7713b8`, Trend đã tạo được một baseline version synthetic cho `STAGING-LINAC-01/output_factor/%` (`100`, tolerance `2`, action level `3`); sau reload, baseline count tăng lên `4`, `7` raw points và `4` series vẫn còn nguyên, không có rewrite hồi tố. Evidence: `docs/evidence/p10-staging-baseline-lifecycle-20260910-2a381ba.json`. Đây mới là happy path create/readback; conflict/invalid/archive/concurrency và projection rebuild vẫn mở.

## P9 deterministic export filename — local verified — 2026-09-10 / `211d9f7`

- Signed report-export URLs now request a deterministic, header-safe `Content-Disposition` filename from the S3-compatible provider. The same contract is applied both when an export is created/replayed and when a download link is renewed; JSON/CSV/PDF/PNG object bytes, checksum, revision snapshot and idempotency behavior are unchanged.
- Local regression verifies all four formats and the download endpoint with `rt-connect-report-export-{export_job_id}.{extension}`. Backend full suite: **169 passed**; Ruff and strict mypy pass; frontend lint, typecheck, Vitest **15/15** and production build pass. Evidence: `docs/evidence/p9-export-filename-20260910-211d9f7.json`.
- This closes the implementation slice only. Staging signed-URL response headers, browser final filename, byte-level PDF/PNG visual review, provider fault/retry and release-manifest evidence remain open.

## P9 deterministic export filename — staging verified partial — 2026-09-10 / `fbbefd0`

- Candidate `fbbefd0d744dbb25bc36a0feaff887a853816a57` is running on staging API/web/worker; public verifier passes **15/15** with schema `20260909_0019`. Authenticated Report Builder loaded Build `fbbefd0…`, reopened report `3b51b1db…` revision 1 and created JSON `15,582`, CSV `1,190`, PDF `1,046` and PNG `2,243` byte exports without changing the report revision or rerunning DVH.
- Browser Downloads observed deterministic names with the new `rt-connect-report-export-{export_job_id}.{extension}` prefix for all four formats. JSON and CSV payloads were parsed; PDF header/EOF and PNG signature were verified; SHA-256 values and job IDs are recorded in `docs/evidence/p9-staging-export-filename-20260910-fbbefd0.json`.
- The browser kept the `.crdownload` suffix during observation, therefore final browser rename/completion is still `UNVERIFIED`. Visual PDF/PNG review, provider fault/retry and release-manifest closure remain open.

## RTDOSE authorization, P17 readback and P9 JSON export — staging verified — 2026-09-10 / `c17fe9a`

- Theo xác nhận của người dùng, fixture RTDOSE tổng hợp được phép dùng trong case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`. Kiểm tra lại trên candidate `c17fe9a1138da4b5b60fe8f070a0367e9e8a07f1` cho thấy `gamma-rtdose-v1-smoke.dcm` đã tồn tại đúng một artifact, checksum đầy đủ `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, `RTDOSE/VALID`, đang được chọn cùng RTSTRUCT hợp lệ; không tạo artifact trùng.
- P17 giữ run `d8230d1d-badd-4c0c-b044-dcc4434215a6`, `COMPLETED`, `FULL`, `P17_TARGET`, `D95=5.200 Gy`, `MIN 5 Gy`, margin `+0.200 Gy`, nhưng status đánh giá vẫn là `REVIEW_REQUIRED` vì không chọn CT và nguồn giới hạn tổng hợp còn `UNVERIFIED`. Đây là kết quả đúng theo boundary staging, không phải clinical PASS.
- Report `P17 staging bound DVH report` (`3b51b1db-1a6c-437b-8e43-dbaf1e9b73e7`, revision 1) được mở lại từ danh sách, editor hydrate đúng `DVH`, source run và 5 block. JSON export `764f8147-3401-4643-a906-e165a1343168` đọc được source snapshot, RTDOSE checksum, limit-binding snapshot và content SHA trùng revision (`2599b891…`).
- Public verifier của candidate c17 đạt `15/15 PASS`, `failed_check_count=0`, schema `20260909_0019`; evidence chi tiết: `docs/evidence/p16-p17-p9-rt-dose-export-20260910-c17.json`.
- Slice này chỉ đóng thêm authenticated readback/export evidence. P17 full negative/fault/resource/oracle/release, P9 các định dạng export còn lại và các release/production gate vẫn mở.

## P16 → P17 → P9 explicit binding/report — staging verified — 2026-09-10 / `a55f7cc`

- Trên staging, đã dùng dữ liệu tổng hợp để tạo P16 `DOSE_LIMIT` entry `STAGING_P16_D95_20260910`, validate-only đúng schema rồi lưu DRAFT và publish revision 2. Entry giữ `D95 MIN 5 Gy`, `USER_DEFINED · UNVERIFIED`, content SHA-256 `818d7457…`; một payload applicability sai đã bị từ chối bằng `KNOWLEDGE_APPLICABILITY_INVALID` trước khi validate thành công.
- P16 không tự áp dụng vào calculator. Sau khi chọn rõ nguồn `P16 · DOSE_LIMIT đã publish`, P17 đã validate và lưu run `d8230d1d-badd-4c0c-b044-dcc4434215a6` trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`: `COMPLETED`, engine `p17-dvh-1.1.0`, ROI `#1 · P17_TARGET`, `D95=5.200 Gy`, limit `MIN 5 Gy`, margin `+0.200 Gy`, `explicit_selection=true`, `auto_applied=false`.
- Vì source còn `UNVERIFIED` và không chọn CT, trạng thái đúng là `REVIEW_REQUIRED` cùng hai warning tương ứng; không nâng thành PASS và không coi đây là prescription/clinical approval. History tăng từ 1 lên 2, run có input fingerprint `8f525a5e…` và result SHA `cf2799b8…`.
- P9 Report Builder đã lưu report revision 1 `P17 staging bound DVH report` từ đúng run mới, source type `DVH`, snapshot SHA `2599b891…`, 5 block tùy chỉnh (`TEXT`, `METRICS`, `PROVENANCE`, `DVH`, `WARNING`) và không rerun/mutate DVH. Evidence đầy đủ: `docs/evidence/p16-p17-staging-binding-report-20260910-a55f.json`.
- Trên cùng report revision, staging Report Builder đã tạo đủ bốn loại export: JSON `15.582` bytes, CSV `1.190` bytes, PDF `1.046` bytes và PNG `2.243` bytes. CSV payload đã đọc lại và khớp report key, revision, source run và content SHA; không tạo revision hoặc rerun DVH. Evidence: `docs/evidence/p9-staging-export-format-20260910-54516.json`.
- Đây là staging authenticated mutation/readback slice PASS. Direct PostgreSQL probe cho entry/run mới, export byte/final filename, full negative/fault/resource matrix, independent oracle promotion, release manifest và production promotion vẫn mở.

## P11 consumer snapshot — local verified, staging open — 2026-09-10

- Machine QA run mới pin `p11.protocol-snapshot.v1` ngay khi tạo hoặc rerun. Snapshot giữ protocol identity/family/version, `status_at_use`, revision, source type/reference/lineage, applicability, engine capability và toàn bộ rule/limit/action/reference snapshot.
- Evaluation sau khi protocol chuyển `ARCHIVED` vẫn dùng snapshot ACTIVE đã chấp nhận; thay đổi định nghĩa ngoài lifecycle archive bị chặn fail-closed bằng `MACHINE_QA_PROTOCOL_SNAPSHOT_MISMATCH`, không tạo metric/trend/result mới. Legacy run chưa có snapshot chỉ được nâng cấp ở lần evaluate đầu theo compatibility policy.
- Trend source context giữ `protocol_version_id`; Machine QA report giữ source snapshot; UI source panel đọc revision/source/applicability/rule count từ snapshot của run và workflow thường không còn seed synthetic protocol.
- Local focused regression `apps/api/tests/test_protocol_library.py`: **4/4 PASS** cho protocol snapshot, archive behavior, Trend lineage và report source. API changed files đã qua Ruff/mypy; web lint/typecheck/build sẽ được kiểm lại trên candidate tài liệu này.
- Local implementation evidence đã được đối chiếu với public staging candidate `907b9d256d221e628a7d5e0b2b578c52b7dd6c14`: Railway API, web và worker đều `SUCCESS` cùng source SHA; API `/apps/api`, web `/apps/web`, worker `/apps/api` với start `python -m rt_connect_api.worker` và không HTTP healthcheck. API `/health`, `/ready`, `/version`, OpenAPI và web bundle exact-SHA đạt **15/15 PASS**, schema `20260909_0019`; evidence `docs/evidence/p11-public-probe-907b9d2.json` và `docs/evidence/p11-railway-parity-20260910-907b9d2.json`. Đây chỉ là source/runtime/public-contract evidence; chưa chạy authenticated browser create/use/archive/old-history E2E, complete S/E/C, visual/accessibility hoặc release-manifest gate. Không upload fixture RTDOSE trùng và không tạo QA run mới trong case staging đã có fixture hợp lệ.
- Fresh authenticated browser trên đúng candidate `0e30ff1ba768494649d9ce6105dacac9c703a4d4` đã mở route Machine QA của case staging và đọc được protocol ACTIVE `MACHINE_QA_BASELINE` v1, source/revision/rule count/applicability, nhãn run đã pin snapshot, existing PASS run và history count 2. Workflow thường không còn hiển thị hành động seed synthetic; không tạo run hoặc thay đổi protocol trong lần kiểm tra này. Evidence read-only: `docs/evidence/p11-staging-consumer-browser-20260910.json`.
- Sau khi buộc API rebuild bằng watched-file marker, đúng candidate `4486eb49c9838c8d9fb68be5627e58312626e79b` đã có API/web/worker `SUCCESS` cùng SHA; public verifier đạt **15/15 PASS**, schema `20260909_0019`, và browser recheck lại Machine QA trên cùng build vẫn đọc được protocol ACTIVE, source/revision/rule count, consumer snapshot marker, existing PASS run/history 2 mà không tạo mutation. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-4486eb4.json`, `docs/evidence/p11-staging-consumer-browser-20260910-4486eb4.json`.
- Fresh authenticated staging lifecycle trên candidate `b7c3c4a2dfd85d86c1097448ca0deddf6d41147f` đã chạy bằng dữ liệu tổng hợp: tạo case `ed7ddbe5-811a-4463-a270-b0386f64644d`, validate-only protocol `STAGING_P11_E2E_B7C3` không side effect, lưu DRAFT revision 2, activate revision 3, clone version 2 DRAFT và compare (metadata diff 4, rule diff 1, child rule deep-copy/lineage), rồi tạo Machine QA run `bc652ee9-0d25-474e-a414-13d23c04a231` với `output_factor=100%`, đạt `COMPLETED/PASS`. Sau khi archive version 1, active list không còn version này nhưng reload run cũ vẫn giữ snapshot revision 3, 1 rule, source/applicability và PASS; không seed action hoặc fixture upload được dùng trong workflow này. Evidence: `docs/evidence/p11-staging-lifecycle-20260910-b7c3c4a.json`. Đây là happy-path S01-S10 slice; P11 vẫn mở cho E01-E17, concurrent/uncertain/scope-negative, các consumer recheck còn thiếu và release manifest.

## P10 Trend query budget — candidate staging parity/public smoke verified — 2026-09-10 / `f4197d8`

- P10 API có `TREND_MAX_RAW_POINTS` mặc định `10.000` và `TREND_MAX_AGGREGATE_SOURCE_POINTS` mặc định `100.000`; count-preflight chạy theo organization/filter trước khi materialize source rows và có kiểm tra lần hai sau context matching.
- Raw vượt budget trả HTTP 413 `TREND_QUERY_TOO_LARGE` với aggregate/matched_points/max_points; day/week trong aggregate budget được phép chạy nhưng thêm `TREND_AGGREGATED_LARGE_QUERY`; aggregate vượt budget cũng trả 413.
- CSV export aggregate không còn rỗng: mỗi bucket là `record_type=BUCKET`, giữ count/statistics/statuses và JSON-encoded source point/run IDs. Đây là local implementation slice; large-series workload 100.000 điểm/máy, staging p95, visual/accessibility và complete S/E/C vẫn mở.
- Regression local đã đạt `test_trend.py` **8/8 PASS**, full backend **185/185 PASS**, Ruff, strict mypy, web lint/typecheck, Vitest **14/14 PASS** và production build (chỉ còn cảnh báo bundle >500 kB).
- Candidate backend `a089d2adb103b106bce7d6c96112e3c426d7e8bb` đã deploy thành công với source parity; public verifier đạt **15/15 PASS**, schema `20260909_0019`. Evidence: `docs/evidence/p10-trend-query-budget-20260910-a089d2a.json`. Follow-up web bounded-error UX candidate `a7c1ad4622bbb57599127b96d9ef27451a715ca0` cũng đã rebuild API/web/worker cùng SHA và đạt **15/15 PASS**; evidence: `docs/evidence/p10-bounded-error-ux-20260910-a7c1ad4.json`.
- Candidate `f4197d82bd287112d1aafae44088678cd967cecf` tiếp tục rebuild API/web/worker cùng SHA sau khi sửa SQL context filtering để không materialize rộng trước khi lọc; public verifier đạt **15/15 PASS** và backend full suite **185/185 PASS**. Evidence: `docs/evidence/p10-sql-filtered-preflight-20260910-f4197d8.json`.
- Đây mới là source/runtime/public-contract evidence. Chưa có authenticated large-series benchmark, complete P10 S/E/C current-candidate, export/source revalidation sau refresh hoặc visual/accessibility evidence; P10 chưa đóng.
- Quyền upload RTDOSE đã được xác nhận, nhưng fixture tổng hợp đã tồn tại và `VALID` trong case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`; không tạo artifact trùng và không tạo QA run mới.

## P07 explicit N/A contract — local + staging candidate — 2026-09-10 / `902b757`

- Đã triển khai P07 explicit N/A end-to-end ở local: measurement có `is_not_applicable` và `na_reason`; N/A bắt buộc có lý do sau trim, không nhận giá trị số, metric có reason nhưng không bật N/A bị từ chối; quality status là `NA`, overall aggregation dùng `FAIL > REVIEW > WARNING > NA > PASS`, và metric N/A không tạo `TrendPoint`.
- Backend regression `apps/api/tests/test_machine_qa.py`: **6/6 PASS**; frontend lint, typecheck, Vitest và production build: **PASS**. Đây mới là `LOCAL_VERIFIED`; chưa dùng để khẳng định candidate staging mới đã phục vụ contract này.
- Tài liệu tại checkpoint đó đã đồng bộ: `business-analysis.md` v0.23, `specification.md` v1.22, `technical-specification.md` v1.21 và `plan.md` v4.13. Đây là evidence lịch sử của P07; revision hiện hành nằm ở phần P10 phía trên và sẽ được kiểm lại sau candidate mới.
- Case staging đã có fixture RTDOSE tổng hợp đúng từ trước và đã ở trạng thái `VALID`; theo xác nhận upload của người dùng, không tạo artifact RTDOSE trùng.
- Railway read-only deployment metadata xác nhận API `1e9e8ab9-ad4b-438a-b5be-bd068700a1c6`, web `2e49f01d-023c-47ac-bd58-b7866baa2e14` và worker `0c0d1c47-2c86-4924-9396-a53f2729aed5` đều `SUCCESS`, cùng source SHA đầy đủ `902b75729c97b6927465d70b93225d5702bdc83f` trên branch `codex/p4-org-site-machine`. API giữ `/apps/api`, pre-deploy `alembic upgrade head`, healthcheck `/api/v1/health`; worker giữ `/apps/api` và `python -m rt_connect_api.worker`, không dùng HTTP healthcheck; web giữ `/apps/web`.
- Public exact-SHA verifier đạt **15/15 checks PASS** với schema `20260909_0019`; evidence: `docs/evidence/p19-staging-public-smoke-20260910-902b757.json`. Đây là source/runtime/public-contract evidence; authenticated Machine QA N/A browser mutation, fault injection và production promotion chưa được ghi nhận.

## Documentation and implementation rebaseline — 2026-09-09

Revision hiện hành của bộ tài liệu là `business-analysis.md` v0.23, `specification.md` v1.22,
`technical-specification.md` v1.21 và `plan.md` v4.13. Dòng rebaseline lịch sử ngay dưới đây
giữ nguyên để truy vết; không dùng các phiên bản cũ đó làm authority.

`business-analysis.md` v0.21, `specification.md` v1.15, `technical-specification.md` v1.13 và `plan.md` v4.0 bổ sung feature-card/handoff, operation/error/evidence record, dependency graph, change-impact gate, state contract, testcase, workflow, error/recovery contract và gap từ source. Bản plan trước ở `docs/history/plan-v1.5.md`. Slice P6/P8/P9/P10/P11/P12/P13/P14/P15/P16/P17 đã được sửa và kiểm thử local; staging E2E chỉ được ghi cho những workflow đã kiểm trực tiếp đúng candidate.

Các trạng thái/evidence bên dưới giữ nguyên phạm vi lịch sử trừ những dòng được ghi rõ là checkpoint mới. Không tự kế thừa DONE sang gate v2: invitation/restore/concurrent edits, P8 crash/ack/bounded retry/resource-large-input, schema-readiness, staging Trend và staging Protocol consumer vẫn phải được đối soát theo plan §1.2–§1.6. Câu “only remaining gates” trong checkpoint cũ không còn là danh sách đầy đủ. Checkpoint trước đã xác minh browser staging P13/P14 trên candidate `31a5900`; PostgreSQL row query trực tiếp, organization-scope negative probe và release-manifest closure vẫn là gate riêng của các phase đó. P8 hiện đã có staging RTDOSE + measurement 3D browser smoke và local independent oracle 6/6; crash/ack/resource/release gates còn mở. P17 hiện đã có targeted PostgreSQL row/checksum/scope probe và object-storage byte re-hash cho case staging; immutable snapshot/fault/resource/release gates còn mở.

## Current staging candidate and RTDOSE permission recheck — 2026-09-10 / `4c9bc1b`

- Railway read-only deployment metadata xác nhận API `753fc39b-244b-4022-aafe-40e634becd49`, web `de98215c-fada-4c29-9867-f757ca37348c` và worker `25c26ce3-6a8c-450d-a641-22a90654d601` đều `SUCCESS`, cùng source SHA đầy đủ `4c9bc1bb4838e2864e605ab4fa69c698ecd0759e`; API/web/worker vẫn giữ đúng root và start contract trong runbook.
- Public verifier chạy lại với exact SHA `4c9bc1bb4838e2864e605ab4fa69c698ecd0759e` và schema `20260909_0019` đạt **15/15 checks PASS**. Kết quả gồm health/readiness/version, OpenAPI, organization boundary unauthenticated `401`, web bundle, CT/membership marker và source marker.
- Fresh authenticated browser trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` hiển thị build hiện hành, `2 dose · 1 structure`, RTDOSE `gamma-rtdose-v1-smoke.dcm` fingerprint `ca5c9168…` ở trạng thái `VALID`, RTSTRUCT `p17-rtstruct-v1-smoke.dcm` fingerprint `16a79df3…`, CT tùy chọn `0b1d3bfd…` và saved DVH run `8000ff9b…`. Người dùng đã cho phép upload fixture RTDOSE; vì fixture đúng đã tồn tại và đang được chọn nên **không upload bản trùng**.
- Full backend regression trên candidate local đạt **100% pass**; planning contract ghi nhận 21 phase và `failed_check_count=0`; worktree sạch trước khi tạo evidence packet.
- Manifest redacted của candidate này ở `docs/evidence/release-manifest-staging-4c9bc1b.json`; `--verify-manifest` trả `valid=true`, service SHA parity `true`, release gate `ELIGIBLE`. Manifest chỉ mô tả consistency của candidate staging đã kiểm; không biến public smoke hoặc fixture hiện hữu thành bằng chứng production promotion, backup/restore provider, fault injection hay clinical readiness.

## Latest staging parity before P09 export change — 2026-09-10 / `b4e2446`

- Sau khi ghi nhận public smoke của `ebf1e66`, commit tài liệu/parity `b4e24468149f070dd77b80e0d2ada3fa20445ce4` đã được Railway rebuild đồng bộ. API `d922b60f-a538-4853-b558-60657a1fefef`, web `e7802242-47bb-4f98-8053-e8b3a3e384b6` và worker `5e0a7920-96af-4dca-b936-af633a3293a1` đều `SUCCESS`, cùng branch `codex/p4-org-site-machine`, root tương ứng `/apps/api`, `/apps/web`, `/apps/api`.
- Public verifier với expected source SHA `b4e24468149f070dd77b80e0d2ada3fa20445ce4` và schema `20260909_0019` đạt **15/15 checks PASS**. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-b4e2446.json`.
- Fresh browser sau cache-bust xác nhận build `b4e24468149f070dd77b80e0d2ada3fa20445ce4`, API `OK`, schema `READY/MATCH`; case staging vẫn có fixture RTDOSE tổng hợp đã cho phép sử dụng, không tạo bản trùng. Đây là mốc runtime trước khi P09 export-compensation code được đưa vào candidate kế tiếp.

## Staging parity and public recheck — 2026-09-10 / `ebf1e66`

- Commit `ebf1e664c55974b6bc418ff05791edfa5ace93f7` đã được push lên branch `codex/p4-org-site-machine`. Railway read-only metadata xác nhận API, web và worker staging đều chạy đúng commit này và đều `SUCCESS`: API `44fba031-2fa2-4d3b-9d42-9b1055a7bafd`, web `d744b68c-7b1b-4b35-aa0e-02eaa89e8b71`, worker `5aab77bc-f1fd-4db2-90bc-8b6b6a9913bf`. API giữ `/apps/api`, healthcheck `/api/v1/health`, pre-deploy `alembic upgrade head`; worker giữ `/apps/api` và `python -m rt_connect_api.worker`, không dùng HTTP healthcheck.
- Ba image digest khác nhau theo vai trò nhưng source commit, branch và runtime `V2` khớp. API image là `sha256:ec5d709b41bc06091594ef349b4eba2598ee8be300a337a481b1a14f8f24cf7d`, web `sha256:edb959b6a7bc9d7ee4584bfe96fbe30d762524d2727ace5cea73c4f3f6415c44`, worker `sha256:8e4801d12ea48b98ed9b9507ff40b85fbf50b1c9316d300f08b97021e41732ad`.
- Public verifier với expected full source SHA `ebf1e664c55974b6bc418ff05791edfa5ace93f7` và schema `20260909_0019` đạt **15/15 checks PASS**: health/readiness, schema, `/version`, OpenAPI CT-preview và organization routes, unauthenticated membership/invitation `401`, web index/bundle, CT/membership markers và source marker. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-ebf1e66.json`.
- Fresh navigation có query bust cache tới `/app/system/status` hiển thị `Build ebf1e664c55974b6bc418ff05791edfa5ace93f7`, API `OK`, schema `READY/MATCH`, queue Redis available và environment `staging`. Fresh navigation tới case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` vẫn đọc được **2 RTDOSE**, **1 RTSTRUCT**, CT tổng hợp và saved DVH history; RTDOSE `gamma-rtdose-v1-smoke.dcm` với fingerprint `ca5c9168…` đã tồn tại nên theo xác nhận upload của người dùng không tạo artifact trùng.
- Lần kiểm tra đầu tiên truyền nhầm `ExpectedVersion=0.1.0-dev` nên verifier báo 1 mismatch có chủ ý; chạy lại với full commit SHA là kết quả PASS. Đây là lỗi tham số kiểm tra, không phải lỗi Railway deployment.
- **Evidence level:** `STAGING_SOURCE_PARITY_AND_PUBLIC_SMOKE`. P19 mới đóng thêm source/runtime/public-contract slice cho candidate này; release manifest mới, authenticated E2E trên candidate mới, production promotion, remote fault/restore, rollback rehearsal và clinical readiness vẫn mở.

## Current staging parity and P14 recheck — 2026-09-10 / `0c0b5ff`

- Railway read-only metadata xác nhận ba service staging đang chạy cùng source commit `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b`, branch `codex/p4-org-site-machine`, và đều `SUCCESS`: API deployment `3766889f-6ff6-4aa9-bee1-2df1ca865af0`, web deployment `0cdaeee3-75ca-4115-a1f3-b23b99d26c9f`, worker deployment `f4db4c55-8afe-44c3-9393-7bc1ad50e9e6`. Worker start command là `python -m rt_connect_api.worker`; deploy log xác nhận `queue_backend=redis_stream`, stream `rt-connect:gamma`, group `rt-connect-gamma`.
- Public exact-SHA verifier sau parity rebuild đạt **15/15 checks PASS** tại `docs/evidence/p19-staging-public-smoke-20260910-0c0b5ff.json`: health/readiness, schema `20260909_0019`, `/version`, OpenAPI, unauthenticated organization boundary `401`, web index/bundle, CT/membership markers và full source marker.
- Release manifest `docs/evidence/release-manifest-staging-0c0b5ff.json` đã được tạo từ working tree sạch của source snapshot `0c0b5ff`, `--verify-manifest` trả `valid=true`, `service_sha_parity=true`, `release_gate=ELIGIBLE`, manifest hash `c071601aae12a28bd99adc5324f8857a8fce4fc5c718c3dee3743125ec5b06ab`. Manifest hiện đã ghi thêm các staging test ID của P14/P15. Manifest chỉ chứng minh consistency của staging snapshot; production promotion, remote fault/restore, full E2E và clinical readiness vẫn mở.
- Trên đúng build `0c0b5ff`, P14 route `/app/biological/compare` đã chạy `Validate only` thành công với hai P13 snapshot cùng scenario revision `f9fafce0-e224-40b6-8b2a-a9952093f8dc`, sau đó lưu comparison `77045b33-117b-4f21-90ec-352cba2f4bf4`. Baseline `option-a` cho `D=60 Gy, n=30, d=2 Gy/fx, α/β=10 Gy` có `BED=72 Gy`, `EQD2=60 Gy`; `option-b` cho `D=70 Gy, n=35, d=2 Gy/fx` có `BED=84 Gy`, `EQD2=70 Gy`, chênh lệch `+12 Gy BED`, `+10 Gy EQD2`, `+16.667%`.
- Reload browser giữ `COMPLETED`, comparison ID, option order, baseline option ID, checksum và history count `3`; history được hiển thị là immutable. JSON/CSV export đã tạo payload parse được, lần lượt `6852` và `673` bytes với SHA-256 được ghi trong evidence, nhưng Edge giữ hậu tố `.crdownload`, nên final filename vẫn `UNVERIFIED`. Evidence đầy đủ: `docs/evidence/p14-staging-browser-20260910-0c0b5ff.json`.
- P15 Re-irradiation trên cùng build đã chạy no-recovery và recovery explicit. Với hai course `60 Gy/30 × 2 Gy`, recovery `r=0.5` cho prior course, snapshot `2f66676e-b5b2-4b76-aa9f-e226e9984bae` đạt `COMPLETED`, BED no-recovery `144`, BED with recovery `108`, EQD2 with recovery `90`; sensitivity `r=0/0.25/0.5/0.75/1` cho BED `144/126/108/90/72`. Spatial request chỉ trả warning/capability `SPATIAL_ACCUMULATION_UNAVAILABLE`, không tạo voxel result. Reload giữ history count `3`, checksum và recovery assumptions. Evidence: `docs/evidence/p15-staging-reirradiation-browser-20260910-0c0b5ff.json`.
- P15 Fraction Compensation cũng đã chạy: planned `[2,2,2,2,2] Gy`, delivered prefix `[2,2] Gy`, original remaining và alternative `[2.5,2.5,1] Gy` đều giữ prefix `UNCHANGED`; snapshot `7d805462-9b3f-497e-90e9-640b11b7c377` đạt `COMPLETED`, BED LQ `12` và `12.15`, ΔBED `0` và `+0.15`. Prefix sai `[2,3]` bị từ chối bằng `FRACTION_SCHEDULE_INVALID`, không tạo snapshot; khôi phục lại thì `VALIDATION_OK`. Reload giữ history count `2`; export payload parse được nhưng final filename vẫn `UNVERIFIED` do `.crdownload`. Evidence: `docs/evidence/p15-staging-fraction-compensation-browser-20260910-0c0b5ff.json`.
- Fixture RTDOSE tổng hợp trong case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đã được xác nhận tồn tại từ trước với SHA-256 `ca5c9168…`; không upload trùng, không tạo patient/PACS/treatment linkage. P8/P13 evidence mang source `d2a5a6b` vẫn là snapshot lịch sử; không dùng chúng để mô tả candidate `0c0b5ff` nếu chưa rerun workflow tương ứng.
- Một tab browser cũ từng hiển thị bundle `e1336b7…` do giữ nội dung/cache của deployment trước. Sau fresh navigation tới `/app/system/status` và P17 DVH, web hiện hành hiển thị build `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b`; chỉ quan sát sau fresh navigation mới được dùng làm evidence parity.
- Ghi chú parity: commit evidence ở root có thể làm web tự rebuild trong khi API bị watch-path bỏ qua. Vì vậy mọi release evidence tiếp theo phải đi kèm parity marker dưới `/apps/api` hoặc được chốt như artifact của candidate đã kiểm, sau đó chạy lại exact-SHA verifier; không push manifest-only rồi kết luận parity còn đúng.

## P20 local backup/restore recheck — 2026-09-10

- Chạy `scripts/verify-local-backup-restore.py` trên Docker Compose đang hoạt động với phạm vi `local-compose-only`; verifier không nhận endpoint Railway/S3 từ xa và không ghi lại dump hay object tạm sau khi kết thúc.
- PostgreSQL custom dump có `169,924` bytes, SHA-256 `53a4ae120f8d596ffcab26d7eb3df87e4e014340ee0576b9a3f871d302adbca1`; restore vào database disposable `rt_connect_restore_39c1fea08247` giữ nguyên row count và row fingerprint của 21 bảng được kiểm.
- Object inventory local có `0` object ở bucket nguồn và bucket restore; inventory hash hai phía cùng là `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`.
- Database restore và bucket restore đã được cleanup thành công (`database_dropped=true`, `bucket_removed=true`); toàn bộ report đạt `passed=true`. Evidence: `docs/evidence/p20-local-backup-restore-20260910.json`.
- **Evidence level:** `LOCAL_SUPPORT_ONLY`. Đây là bằng chứng kiểm tra tính đúng của script/restore path với database local hiện tại; chưa chứng minh backup provider Railway, RPO/RTO, restore staging/production, alerting hoặc owner handoff. P18/P20 vẫn chưa đóng.

## P06 local upload compensation recheck — 2026-09-10

- Bổ sung `delete_object` vào object-storage adapter. Sau khi object đã được ghi, nếu transaction `Artifact` + `InputManifest` + audit không commit thì API rollback database và xóa đúng object key vừa tạo; không xóa theo filename hoặc prefix.
- Nhánh metadata conflict tổng hợp trả lại lỗi gốc `ARTIFACT_CONFLICT`, object storage không còn object và danh sách case không có artifact mồ côi. Nhánh cleanup storage lỗi trả `ARTIFACT_PERSISTENCE_FAILED` HTTP 503, giữ signal để reconciliation; không trả success khi chưa có metadata durable.
- Regression `tests/test_artifacts.py` và `tests/test_error_contract.py`: **8 passed**; `Ruff` sau sửa line length và `mypy src`: **PASS**. Evidence chi tiết: `docs/evidence/p6-local-upload-compensation-20260910.json`.
- **Evidence level:** `LOCAL_VERIFIED` cho compensation path và memory storage double. Provider retention/inventory reconciliation, interrupted multipart trên network thật và staging failure injection vẫn mở; không dùng checkpoint này để kết luận P06 hoặc P18/P20 đã đóng.

## P09 local export compensation recheck — 2026-09-10

- Export report hiện commit claim `QUEUED` trước, render từ revision snapshot, ghi object, sau đó mới commit metadata `COMPLETED` cùng hash/size/media/warnings. Nếu commit metadata cuối thất bại, API rollback session và xóa đúng object key; nếu cleanup thất bại, API trả HTTP 503 `REPORT_EXPORT_PERSISTENCE_FAILED` với signal reconciliation và không phát signed URL.
- `tests/test_reports.py`, `tests/test_artifacts.py` và `tests/test_error_contract.py` đạt **14 passed**; nhánh retry cùng idempotency key sau compensation tạo đúng một export, còn nhánh cleanup failure giữ object để reconciliation nhưng không trả success. Ruff và mypy đều PASS.
- Evidence: `docs/evidence/p9-local-export-compensation-20260910.json`. **Evidence level:** `LOCAL_VERIFIED` cho transaction/compensation path với in-memory storage; provider/network fault injection, orphan inventory, retention, restore và visual export vẫn mở.

## P10 staging Trend read-only recheck — 2026-09-10 / `0c0b5ff`

- Fresh authenticated browser navigation tới `/app/trend` trên web build `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b` hiển thị `API THẬT`, organization context `Hong ngoc general hospital`, machine `STAGING-LINAC-01 · Synthetic QA Linac`, metric `output_factor`, aggregate `raw` và timezone `Asia/Ho_Chi_Minh`.
- Current projection readback hiển thị `6` compatible points thuộc `3` series (`flatness`, `output_factor`, `symmetry`), `3` baseline và `1` maintenance marker. Các series giữ riêng protocol/unit/context; source case links và raw values vẫn được hiển thị.
- Hai series `flatness` và `output_factor` có điểm `100 %`, `PASS`, baseline delta `0`; series `symmetry` hiển thị điểm `1 %`, `PASS · OUTLIER`, baseline delta `-99`, chứng minh UI không nuốt trạng thái outlier vào một PASS không có dấu hiệu.
- Lần kiểm tra chỉ đọc; không bấm `Rebuild projection`, không export và không tạo mutation. Evidence: `docs/evidence/p10-staging-trend-browser-20260910-0c0b5ff.json`.
- **Evidence level:** `STAGING_SMOKE_READ_ONLY`. P10 chưa đóng: projection rebuild, update/archive baseline UI, complete negative matrix, large-series budget, export-content/hash và visual/accessibility evidence vẫn mở.

## Staging parity rebuild and release manifest — 2026-09-10 / `d2a5a6b`

- Read-only Railway deployment metadata first exposed source drift: API remained on the `c6252f7` successful deployment while web/worker had accepted the later documentation commit. A harmless parity marker was therefore added below `/apps/api`; it does not change application behavior, but makes API and worker participate in the same Git-triggered candidate rebuild.
- Candidate `d2a5a6b22267d153f26764596b36c78118f67ffa` is now served by all three staging services. Deployment IDs are API `c53678dc-c2c4-4c7a-9e24-137b949a5ff7`, web `2a78dd8a-414f-4e75-ab2e-c9c0631579fc` and worker `4dc90da0-2745-4f95-9575-18ab1264b8c2`; each Railway deployment is `SUCCESS` and the worker remains configured with `python -m rt_connect_api.worker`.
- The public exact-SHA verifier reached **15/15 checks PASS**: health/readiness/version, schema `20260909_0019`, OpenAPI CT-preview and organization routes, unauthenticated membership/invitation boundary `401`, web index/bundle, CT/membership UI markers and bundle source marker. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-d2a5a6b.json`.
- Release manifest `docs/evidence/release-manifest-staging-d2a5a6b.json` records all three deployment IDs, the four synthetic DICOM/measurement fixture hashes, engine/renderer versions, local/staging test IDs and rollback reference. `--verify-manifest` returned `valid=true`; `service_sha_parity=true` and `release_gate=ELIGIBLE` apply only to this staging candidate's manifest consistency, not to production promotion or clinical readiness.
- P8 2D negative/recovery evidence on the same candidate is recorded in `docs/evidence/p8-staging-gamma-2d-20260910-d2a5a6b.json`: intentional PSQA 3D RTDOSE plus 2D measurement mismatch failed explicitly as `GAMMA_DIMENSIONALITY_MISMATCH` (`e33968e2…`), then compatible `ENGINE_TEST` 2D JSON fixtures completed `PASS` (`5b5711c6…`, `4/4`, coverage `1`, attempt `1`, engine `gamma-nd-p8.2`). No failed job was counted as a passing result.
- P13 authenticated browser evidence on the same candidate is recorded in `docs/evidence/p13-staging-bed-eqd2-browser-20260910-d2a5a6b.json`: the saved synthetic scenario used `D=60 Gy, n=30, d=2 Gy/fx, α/β=10 Gy`; validate-only returned `VALIDATION OK` without a database side effect, save returned `COMPLETED` with `BED=72 Gy` and `EQD2=60 Gy` (`8fda6eb8…`), and a reload preserved the newest snapshot with history count `3`. An intentional `D=61 Gy` mismatch returned `FRACTIONATION_INCONSISTENT` on the two dependent fields and did not create a snapshot; restoring `D=60 Gy` returned `VALIDATION OK`. This is independent biological-tool evidence, not a QA/patient linkage or clinical-readiness claim.
- This checkpoint closes the P19 source-parity/manifest sub-slice for staging. It does not close P4 two-identity Auth/PostgreSQL lifecycle, P8 staging crash/ACK/failure/resource/oracle promotion, P9–P18 remaining gates, P19 production remote E2E/rollback, or P20 real alert/backup/restore evidence.

## Latest staging candidate checkpoint — 2026-09-10 / `c6252f7`

- Candidate `c6252f7557a5c2c893c5e3082035884e9f26c882` đã được push lên branch `codex/p4-org-site-machine` và Railway tự triển khai cho API, web và worker staging. API `/api/v1/version` và `/api/v1/ready` trả đúng full SHA/schema `20260909_0019`; web bundle cũng chứa đúng source marker.
- Public verifier exact-SHA đạt **15/15 checks PASS** tại `docs/evidence/p19-staging-public-smoke-20260910-c6252f7.json`: health/readiness/version, OpenAPI CT preview và organization membership, unauthenticated boundary 401, web index/bundle, UI markers và source parity đều đạt.
- Worker deployment `031ceef2-1260-4b0a-8353-4c80d6ae31ee` hiển thị `Deployment successful`, commit `c6252f7557a5c2c893c5e3082035884e9f26c882`, branch `codex/p4-org-site-machine`, root `/apps/api`, start command `python -m rt_connect_api.worker`, trạng thái `Online`.
- Local peer-membership regression đạt **12/12** sau khi bổ sung identity thứ hai tổng hợp: peer nhận invitation, đọc cùng organization context và thực hiện cùng thao tác site/machine/member; không có nhánh action-role theo chức danh. Evidence: `docs/evidence/p4-local-peer-membership-20260910.json`.
- Fixture RTDOSE tổng hợp đã được người dùng xác nhận cho phép sử dụng trên case staging; fixture hợp lệ đã tồn tại nên không upload trùng. Gamma 3D run mới `1d5ee035-28e0-461a-8a3d-15fef6b883bd` đạt `COMPLETED/PASS`, `8/8`, trên worker Redis staging. Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-2b1846a.json`.
- Local Compose queue verifier v2 bổ sung ACK transport-failure injection: message sau durable `COMPLETED` vẫn pending, eventual ACK dọn pending, result/attempt không đổi. Evidence: `docs/evidence/p8-local-redis-worker-smoke-20260910-v2.json`; toàn bộ happy path, bounded retry/dead-letter, malformed quarantine và ACK recovery đều PASS.
- Checkpoint này chỉ nâng source/runtime confidence và ghi nhận evidence có thể truy vết. Nó **không** đóng P4 two-identity Supabase/PostgreSQL lifecycle, P8 crash sau durable commit trước ACK/failure injection/resource-large-input/oracle promotion, các gate P9–P18 còn mở, hoặc P19 production promotion.

## Current continuation checkpoint — 2026-09-10

- Fresh authenticated browser recheck trên candidate `ec50990395e9bb4b7182ff48c3b2a8e4b2eeb1ca` xác nhận route `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh` đang phục vụ đúng build; case vẫn giữ RTDOSE tổng hợp `ca5c9168…`, RTSTRUCT `16a79df3…`, CT `0b1d3bfd…`, ROI `#1 · P17_TARGET` và saved run `8000ff9b…`.
- CT frame `#1` tiếp tục trả `LPS LINKED` với overlay `NEAREST_NEIGHBOR_IN_PATIENT_LPS`; frame `#3` trả `NO DOSE OVERLAP` đúng warning contract. Không tạo upload, DVH run hoặc mutation mới trong lần recheck này. Evidence: `docs/evidence/p17-staging-browser-recheck-20260910-ec50990.json`.
- P16/P11 binding được kiểm tra read-only: staging hiện có **0** P16 `DOSE_LIMIT` entry; các protocol ACTIVE chỉ cung cấp metric `output_factor`, `flatness` và `staging_output`, chưa có metric DVH tương thích. Vì vậy binding gate vẫn mở và hệ thống vẫn giữ `NO AUTO-APPLY`.
- JSON export có payload hoàn chỉnh, parse/hash khớp run (`17,738` bytes); Edge/CUA giữ hậu tố `.crdownload`, nên browser final filename vẫn `UNVERIFIED` và không được diễn giải thành lỗi byte payload.
- Validate-only sau khi chọn CT tổng hợp trả `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ`, CT frame `#1` hiển thị `LPS LINKED` và overlay `NEAREST_NEIGHBOR_IN_PATIENT_LPS`; không tạo upload/run/mutation mới.
- P17-W06 local resource evidence mới `docs/evidence/p17-local-docker-workload-20260910.json` đạt `LOCAL_RESOURCE_GATE_PASS`: API container `1 CPU/768 MiB`, 2 job × 3 lần, 6/6 process peak RSS, max `127,086,592 bytes`, max elapsed `2.0811 s`, p95 `/health` `166.016 ms`, 0 probe error, engine/oracle nhất quán; cgroup v1 peak `385,990,656 bytes` là quan sát tích lũy từ lúc container start và vẫn được gắn `is_peak_rss=false`.
- Public verifier exact-SHA trên candidate `ec50990395e9bb4b7182ff48c3b2a8e4b2eeb1ca` pass **15/15**; API, worker và web staging cùng source/schema. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-ec50990.json`. Probe accept invitation dùng POST không body để xác nhận auth boundary 401 trước validation; payload contract vẫn được test API kiểm. Đây là source-parity/public-boundary evidence, không phải production promotion hoặc clinical readiness.

## P4/P8 current staging candidate — 2026-09-10 / `2b1846a`

- Sau khi push các commit queue hardening và evidence lên `codex/p4-org-site-machine`, API, web và worker staging đều đã có deployment thành công từ full SHA `2b1846a44ca10091df3e043eb478f9ffb6b7bc3e`; API `/api/v1/version` và `/api/v1/ready` trả đúng SHA/schema `20260909_0019`, public smoke đạt **15/15** trong `docs/evidence/p19-staging-public-smoke-20260910-2b1846a.json`.
- Worker staging deployment `7fa7a9ba-c29d-4979-af97-e42f00dbb3f3` hiển thị commit `2b1846a44ca10091df3e043eb478f9ffb6b7bc3e`, start command `python -m rt_connect_api.worker`, trạng thái `Deployment successful`; logs xác nhận `queue_backend=redis_stream`, stream `rt-connect:gamma`, group `rt-connect-gamma`. API deployment là `d8a8dfc0-8562-4893-9fcd-4a6ba1137155`; web deployment là `eb08fb76-4ae3-4c3d-9193-56f111a9a6b7`.
- Authenticated browser `/app/organization` đã đọc được organization `Hong ngoc general hospital` `ACTIVE`, 1 site `Staging Synthetic Site`, 1 machine `STAGING-LINAC-01` và 1 active member ngang quyền; không tạo mutation trong lần kiểm tra. Evidence: `docs/evidence/p4-staging-auth-organization-browser-20260910-2b1846a.json`. Đây mới là read evidence của một identity, chưa đóng two-identity invitation lifecycle.
- Trên đúng candidate mới, RTDOSE `gamma-rtdose-v1-smoke.dcm` đã có sẵn nên không upload trùng; Gamma 3D synthetic run mới `1d5ee035-28e0-461a-8a3d-15fef6b883bd` đã đi qua enqueue → worker → persist và hiển thị `COMPLETED/PASS`, `8/8`, engine `gamma-nd-p8.2`, coverage `1`, P95 `0`. Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-2b1846a.json`.
- Local P4 peer-membership regression mới đạt `12/12`: identity nhận invitation có verified email, đọc cùng organization context và thực hiện cùng các thao tác site/machine/member; không có action-role branch. Evidence: `docs/evidence/p4-local-peer-membership-20260910.json`. Đây là local contract evidence, chưa thay cho hai tài khoản Supabase trên browser hoặc query PostgreSQL staging.
- Các evidence trên nâng source/runtime confidence của P4/P8 trên candidate hiện tại nhưng không đóng P4 two-identity/Auth/PostgreSQL lifecycle, P8 crash/ACK/failure injection/resource-large-input/oracle promotion hoặc P19 production promotion.

## P8 staging RTDOSE and independent-oracle continuation — 2026-09-10 / candidate `85ecb0e`

- Người dùng đã xác nhận cho phép upload fixture RTDOSE tổng hợp vào case staging. Kiểm tra read-only tại case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` cho thấy `gamma-rtdose-v1-smoke.dcm` đã tồn tại với UI hash prefix `ca5c9168…`; không upload trùng và không tạo artifact mới. Đây là cùng fixture synthetic đã được sử dụng cho các smoke trước, không có patient/PACS/treatment data.
- Gamma browser smoke trên candidate `85ecb0ebb025220a79cc82977049d2e16340efb0`: profile `PSQA_GAMMA`, RTDOSE reference `gamma-rtdose-v1-smoke.dcm`, measurement 3D evaluation `gamma-measurement-3d-v1-smoke.json`, `PREFLIGHT VALID`; run `df38e7d5-bb4b-4e2d-b949-2310acb1875c` `COMPLETED`, attempt `1`, engine `gamma-nd-p8.2`, `8/8` evaluated/passing, coverage `1`, P95 `0`, pass rate `100%` target `95%`. History vẫn hiển thị 6 completed runs; recheck không tạo run mới. Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-85ecb0e.json`.
- Script `scripts/verify-p8-independent-gamma-oracle.py` đã được kiểm bằng Ruff và chạy thành công. Oracle tự parse fixture contract, exhaustive GRID node và BILINEAR sampling lattice, sau đó đối chiếu public `calculate_gamma`; 6/6 case PASS, gồm 2D/3D, GRID/BILINEAR, GLOBAL/LOCAL, RELATIVE/ABSOLUTE, OVERLAP_ONLY và max-gamma censoring. Evidence: `docs/evidence/p8-independent-gamma-oracle.json`.
- `P8` vẫn chưa được đóng: local oracle không thay cho staging oracle promotion/commissioning; chưa có evidence staging cho worker crash sau durable commit trước ACK, bounded retry/dead-letter/failure injection, large-input/resource budget hoặc release manifest. Các gate này được giữ mở trong `plan.md`.

## P8 local Redis/worker queue smoke — 2026-09-10

- `docker-compose.yml` đã được bổ sung service `worker` riêng với cùng runtime contract với API: PostgreSQL, Redis, MinIO, Gamma lease/retry/resource settings. `docker compose config --quiet` PASS và container worker khởi động với `queue_backend=redis_stream`.
- `scripts/verify-local-gamma-queue.py` đã chạy thành công với `docs/evidence/p8-local-redis-worker-smoke-20260910.json`, `verification_level=LOCAL_COMPOSE_REDIS_WORKER`, `synthetic_only=true`, `passed=true` trên source commit `f8de071d171a017e5bb6124125414a4357cb5ddb` (evidence được ghi ở commit `a783c33`). Verifier tạo tài nguyên tạm và kiểm tra job `COMPLETED/PASS` 4/4, duplicate dispatch, terminal replay guard, storage failure bounded ở 3 attempts, dead-letter cho attempt cuối và Redis `pending_count=0` sau ACK.
- Kết quả này nâng P08-W03 từ `LOCAL_SLICE_ONLY` lên `LOCAL_COMPOSE_VERIFIED`, nhưng không nâng P8 thành `DONE-v2`: staging crash/ACK injection, staging resource/large-input, oracle promotion/convergence và release-manifest evidence vẫn mở.
- Reliability hardening tiếp theo đã được kiểm tra local: Redis entry malformed không còn làm parser ném lỗi rồi giữ poison message pending vô hạn. Worker phân loại `GAMMA_QUEUE_MESSAGE_INVALID`, ghi dead-letter diagnostic bounded (message id/reason/key summary, không copy payload value) và chỉ ACK sau khi quarantine thành công; terminal `FAILED` redelivery cũng thử dead-letter lại trước ACK. Đây là local contract/test evidence, chưa phải staging fault-injection evidence.
- Verifier integration của cùng checkpoint đã chạy malformed entry qua worker thật: `worker_completed`, `dead_letter_written`, `error_code`, `source_message_recorded`, `payload_value_not_copied` và `queue_acknowledged` đều PASS; Redis sau ACK có `pending_count=0`. Kết quả này chỉ mở rộng local Compose evidence, không đóng staging crash/ACK injection hoặc release gate.
- Verifier v2 chạy thêm ACK recovery probe trên worker/Redis thật của Compose: sau khi run đã durable `COMPLETED`, lần `XACK` đầu bị inject lỗi; pending count giữ `1`, lần ACK kế tiếp về `0`, `GammaRunAttempt` vẫn chỉ có một attempt và result không bị tính lại. Evidence: `docs/evidence/p8-local-redis-worker-smoke-20260910-v2.json` (`passed=true`). Đây là fault-injection local support, chưa thay staging crash sau commit trước ACK.

## P17 staging CT preview recheck — 2026-09-10 / candidate `85ecb0e`

- Trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`, fixture synthetic đã có sẵn: 2 RTDOSE VALID, 1 RTSTRUCT VALID, 1 CT VALID và ROI `#1 · P17_TARGET`. Không upload lại RTDOSE và không tạo run mới.
- Chọn CT `p17-ct-v1-smoke.dcm` rồi chạy `Validate & preview`: UI trả `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.` CT slice `#1` hiển thị `LPS LINKED`, `NEAREST_NEIGHBOR_IN_PATIENT_LPS`, ROI overlay đúng và crosshair tại dose grid center; saved run `8000ff9b…` giữ nguyên. Evidence: `docs/evidence/p17-staging-browser-recheck-20260910-85ecb0e.json`.
- Đây là authenticated browser read-only evidence trên candidate `85ecb0ebb025220a79cc82977049d2e16340efb0`; nó chỉ đóng thêm positive CT-preview/validate recheck, không đóng P17 binding P11/P16, failure/resource/volume, export filename hay release gate.

## P4 membership/invitation local slice — 2026-09-09

- Source working tree đã bổ sung migration `20260909_0018_organization_invitations`, `OrganizationInvitation`, partial unique index cho invitation PENDING theo organization/email, member list/toggle và các endpoint tạo/list/revoke/accept invitation.
- Contract giữ nguyên quyết định của người dùng: mọi active member trong cùng organization ngang quyền nghiệp vụ; không có action roles, owner/admin branch hoặc approval hierarchy. `is_active` chỉ là lifecycle/context state và không cho phép tắt member active cuối cùng.
- Invitation local contract: email trim/case-fold; token random 32 bytes chỉ trả ở response create; database chỉ lưu SHA-256; status `PENDING/ACCEPTED/REVOKED/EXPIRED`; accept kiểm verified email, organization archive, active context khác và hỗ trợ replay cùng token/cùng identity về cùng membership.
- Frontend đã có member/invitation panels trong `/app/organization` và public `/invite?token=...` route; login giữ return path nội bộ. Token không được đưa vào list/history/localStorage trong implementation slice.
- Local evidence mới: `test_organization.py` **9 passed**, `test_health.py` và `test_migration_contract.py` trong focused pack tổng **25 passed**, Ruff và strict mypy PASS; frontend lint/typecheck/**5 passed**/build PASS. Riêng `SessionErrorPage` onboarding có regression pack **3/3** tại `docs/evidence/p3-p4-frontend-onboarding-20260909.json`.
- Đây là `STAGING_DEPLOYED_AUTH_E2E_OPEN`, chưa phải `STAGING_VERIFIED`: candidate `2fcf065` đã lên branch staging; `/api/v1/ready` trả HTTP 200 với schema `20260909_0018`, `/api/v1/version` và web bundle cùng nhận diện `2fcf065`, `/api/v1/openapi.json` có member/invitation routes, và các route invitation/member mới trả HTTP 401 khi chưa xác thực. Còn phải kiểm Auth thật và hai identity trên browser, xác nhận PostgreSQL rows/hash/status/audit, replay/revoke/expiry/context/scope/concurrency/timeout trước khi đóng P04-W02/P04-W04/P04-VERIFY.

## P4 invitation lifecycle regression and staging parity — 2026-09-09

- Commit `38dec53d4e542bdf6c4f808283981b344cae3502` bổ sung regression cho hai nhánh còn thiếu ở local: invitation `REVOKED` là terminal, token revoked không accept được nhưng email có thể được mời lại; invitation quá hạn bị chuyển `EXPIRED`, token không accept được và email có thể được reissue. Token không được lưu trong list/closed projection.
- `apps/api/tests/test_organization.py` đạt **11 passed**; full backend suite trên clean tree đạt **172 passed**. Đây là local evidence cho contract revoke/expiry/reissue, không thay cho Auth thật, hai identity, PostgreSQL staging row/hash/audit hoặc concurrency evidence.
- Để tránh source drift do thay đổi chỉ trong `apps/api`, parity marker đã được đặt ở `apps/web/README.md`; Railway staging đã deploy API, worker và web cùng SHA `38dec53d4e542bdf6c4f808283981b344cae3502`, cả ba `SUCCESS`.
- Evidence công khai exact-SHA: `docs/evidence/p19-staging-public-smoke-20260909-38dec53.json` đạt **15/15 checks PASS**, schema `20260909_0019`; health/readiness/version, OpenAPI CT/member/invitation, unauthenticated boundary 401 và web bundle/source marker đều khớp. P4 Authenticated E2E vẫn `OPEN`.

## P4 staging deployment delta — 2026-09-09

- **Source/deploy:** candidate `2fcf065` đã được push lên `codex/p4-org-site-machine` và API/web/worker staging đều đã deploy từ candidate đó. API readiness hiện trả `status=ready`, schema `20260909_0018`; OpenAPI public trả HTTP 200 và chứa các operation `organizations/invitations` và `organizations/{organization_id}/members`.
- **Unauthenticated boundary:** `GET .../{organization_id}/members`, `GET .../{organization_id}/invitations` và `POST .../organizations/invitations/accept` đều trả HTTP 401 với envelope Auth phù hợp; chưa sử dụng dữ liệu bệnh nhân hay secret.
- **Web:** web root trả HTTP 200; bundle mới chứa marker giao diện `Nhận lời mời RT-CONNECT` và `Thành viên ngang quyền`, xác nhận route/UI P4 đã được build.
- **Config parity:** API `/api/v1/version`, web build label và Railway deployment metadata hiện cùng nhận diện `2fcf065`; staging version parity đã pass. Đây không thay cho release manifest production.
- **Evidence level:** `STAGING_DEPLOYED_AUTH_E2E_OPEN`. Chưa gọi `STAGING_VERIFIED` vì chưa có hai identity/Auth browser flow, direct PostgreSQL row/hash/status/audit query, replay/revoke/expiry/context/concurrency/timeout evidence.

- **Public smoke cập nhật:** `scripts/verify-public-deployment.ps1` đã chạy lại với timeout hữu hạn và bổ sung kiểm tra request thực tế không có Auth. Evidence `docs/evidence/p4-staging-public-smoke-20260909-2fcf065.json` ghi **14/14 checks PASS**: health/readiness HTTP 200, schema head `20260909_0018`, version `2fcf065`, OpenAPI có CT preview/member/invitation, ba route membership/invitation trả `401`, web/bundle và UI markers trả HTTP 200. Version parity đã đạt; Authenticated E2E vẫn mở.
- **Public smoke recheck trước đó:** chạy ngày 2026-09-09 với expected version `2fcf065` và schema `20260909_0018`; evidence `docs/evidence/p19-staging-public-smoke-20260909-current.json` đạt **15/15 checks PASS**. Đây là evidence lịch sử của candidate trước source-label fix, vẫn giữ để truy vết và không thay Authenticated E2E/DICOM upload/DVH run/DB row/release gate.

## P19 staging source-label recheck — 2026-09-09

- Candidate `62a7b5300e39b9e742bee0b7353ff86a559d4abe` đã được Railway staging deploy cho API/web; API `/api/v1/health` và `/api/v1/ready` đều HTTP 200 với `status=ok/ready`, schema `20260909_0018`, còn `/api/v1/version` trả đúng source SHA và environment `staging`.
- Web root và bundle mới (`assets/index-Dk9-li-i.js`) đều HTTP 200; bundle có nhúng source SHA. Browser `/app/system/status` hiển thị Build cùng SHA, `SẴN SÀNG`, API `OK`, `READY`, `MATCH`, queue `redis_stream · available · configured`, và organization runs đều bằng 0.
- Evidence: `docs/evidence/p19-staging-source-label-20260909.json`. Điều này đóng source-label API/web staging sub-gate của GAP-09; không chứng minh worker parity, Authenticated E2E, DICOM/DVH, direct PostgreSQL, rollback hoặc production promotion.

## P19 current public smoke after P17 snapshot regression — 2026-09-09

- Commit `71a110a74a2bf14fdc9b288b30decff807329b20` (snapshot regression test plus evidence/documentation) đã được Railway staging serve. `scripts/verify-public-deployment.ps1` chạy với expected version đầy đủ và schema head `20260909_0018` đạt **15/15 checks PASS**: health/readiness HTTP 200, version parity API, CT preview/member/invitation routes trong OpenAPI, ba unauthenticated boundary 401, web index/bundle HTTP 200, CT/membership UI markers và bundle chứa đúng source SHA.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260909-71a110a.json`. Đây là public deployment/source-parity evidence mới nhất; không thay Authenticated E2E, direct PostgreSQL/object probe của P17, worker parity, rollback hoặc production promotion.

## P19 current public smoke after DVH immutability guard — 2026-09-09

- Candidate `d04fb5a3561804bd3553b36886902e1c50b2f18f` đã được Railway staging phục vụ đồng thời cho API/web. `scripts/verify-public-deployment.ps1` với expected version đầy đủ và schema head `20260909_0019` đạt **15/15 checks PASS**: health/readiness HTTP 200, version parity, OpenAPI CT preview + membership/invitation routes, ba unauthenticated boundary 401, web index/bundle 200, CT/membership UI markers và bundle chứa đúng source SHA.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260909-d04fb5a.json`. Đây là public source/schema parity mới nhất; không thay Authenticated E2E, direct PostgreSQL/object probe, immutable-trigger probe, worker parity, rollback hoặc production promotion.

## P19 current public smoke after explicit DVH source-binding UI — 2026-09-09

- Candidate `ddfb43458ab57caa50387880f0f0538af0eb5ca8` đã được Railway staging phục vụ đồng thời cho `Railway-API-staging`, `RT-connect-web-staging` và `RT-connect-gamma-worker-staging`; cả ba deployment đều `SUCCESS`, cùng source SHA và schema `20260909_0019`.
- `scripts/verify-public-deployment.ps1` chạy với exact source SHA và schema head đạt **15/15 checks PASS**: health/readiness/version, schema parity, OpenAPI CT preview + membership/invitation, unauthenticated boundary 401, web index/bundle, CT/membership markers và source SHA trong bundle. Evidence: `docs/evidence/p19-staging-public-smoke-20260909-ddfb434.json`.
- Frontend local trên candidate này đạt **5 test files / 14 tests PASS**, lint, typecheck và production build PASS. Vùng `OPTIONAL EXPLICIT BINDING` đã được expose trong DVH: mặc định không dùng P16/P11; chỉ gửi `limit_entry_id` hoặc `protocol_version_id + protocol_metric_key` khi người dùng chọn rõ nguồn.
- Browser staging đã reload route `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh`, hiển thị build `ddfb43458ab57caa50387880f0f0538af0eb5ca8`, `2 dose · 1 structure`, RTDOSE/RTSTRUCT/ROI và control P16/P11. Preview import một reference P16 tổng hợp trả `hợp lệ 1, loại 0`, nhưng chưa commit entry mới; vì vậy live P16/P11 evaluation vẫn mở và không được ghi thành PASS.
- Đây là public parity/UI evidence, không đóng P17 binding/report cloud, full negative/fault/resource/volume, browser download finalization, worker/release manifest, P4 authenticated lifecycle hoặc production promotion.

## P17 current-candidate negative-path recheck — 2026-09-09

- Trên candidate `dd14ef84f16c66bba45851d98d17f2954ef35fc7`, browser staging chọn RTDOSE cũ có UI hash prefix `544f355fa286…` và chạy `Validate & preview`. API/UI trả đúng `DVH_DOSE_UNITS_UNSUPPORTED` với thông báo yêu cầu `DoseUnits=GY`; đây là validate-only nên lịch sử vẫn có `1` run và không tạo bản ghi mới.
- Sau đó chọn lại RTDOSE tổng hợp hợp lệ với UI hash prefix `ca5c9168eb9b…`; validate trả `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.` Saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4` vẫn giữ nguyên, không có mutation hoặc duplicate run.
- Evidence redacted: `docs/evidence/p17-staging-negative-recheck-20260909-dd14ef8.json`. Đây là bằng chứng negative-path trên current candidate; không đóng các gate fault/resource/volume, P11/P16 binding, browser final filename, release manifest hoặc production promotion.

## P19 production public gap recheck — 2026-09-09

- Read-only probe tới `https://rt-connect-production.up.railway.app` trả `/health` HTTP 200 `status=ok` và `/ready` HTTP 200 `status=ready`, nhưng `/version` vẫn trả `version=0.1.0-dev`, `environment=development`, không có source SHA/schema revision; OpenAPI chỉ có 4 route nền tảng P1 và chưa có CT/membership/clinical routes.
- Railway metadata cho production API ghi deployment `2d94daa6-ecda-4cc0-aaca-c7afd16cfc8d`, branch `main`, commit `fae82738786ef92577dd389711591390f6761741`, `SUCCESS`. Đây là baseline cũ, không phải candidate staging `a39bfa9`.
- Evidence redacted: `docs/evidence/p19-production-public-gap-20260909.json`. Quyết định hiện tại là `PRODUCTION_PROMOTION_BLOCKED`; không suy diễn production-ready từ health/readiness HTTP 200. Không có login, upload, database mutation hoặc dữ liệu lâm sàng production trong probe.

## Current checkpoint

- **Goal:** Hoàn thiện RT-CONNECT theo `plan.md` từ P0 đến P19 và thiết lập baseline vận hành P20.
- **Current phase:** P8/P17 — Gamma RTDOSE worker verification và Visual Dose/DVH structure review đang chạy song song. P8 đã có staging browser RTDOSE + measurement 3D smoke và local independent oracle; P17 staging case đã có RTDOSE/RTSTRUCT/CT và đã qua browser saved-run/CT/export-content, targeted PostgreSQL row/checksum/scope probe cùng object-storage byte re-hash. Các gate P8 crash/ack/retry/resource-large-input/oracle promotion, P17 live binding/report cloud/fault/container-RSS/concurrency và release chưa đóng. Guard ORM + migration PostgreSQL `20260909_0019` đã được deploy và probe trên fixture transaction-local; local synthetic volume measurement đã có nhưng chưa phải performance gate. Song song, P4 invitation/member slice vẫn cần Authenticated E2E/DB lifecycle.
- **Current status:** IN_PROGRESS — candidate `85ecb0ebb025220a79cc82977049d2e16340efb0` có public exact-SHA 15/15; P8 browser run `df38e7d5…` `COMPLETED`, `8/8 PASS`, independent oracle local `6/6 PASS`; P17 browser recheck giữ nguyên case/run và kiểm CT frame positive/no-overlap. P16/P11 chưa có committed compatible reference nên live evaluation vẫn mở. P4 Auth/two-identity/DB lifecycle, P8/P9/P10/P11/P12/P13/P14/P15/P16/P17 closure và production release vẫn mở.
- **Latest P4 regression:** invitation lifecycle local pack đạt **11 passed** trên commit `38dec53d4e542bdf6c4f808283981b344cae3502`; full backend clean-tree suite đạt **172 passed**. Staging source parity của API/worker/web đã được kiểm bằng evidence `docs/evidence/p19-staging-public-smoke-20260909-38dec53.json`.
- **Last authoritative check:** sau commit `85ecb0e`, full backend suite trên tree sạch PASS; Ruff, strict mypy, planning-contract 21 phase, independent Gamma oracle 6/6, frontend lint/typecheck, **5 test files / 14 tests** và production build đều PASS. Public evidence hiện hành: `docs/evidence/p19-staging-public-smoke-20260910-85ecb0e.json` đạt **15/15** với API/worker/web cùng source/schema; không dùng public parity hoặc browser UI để suy ra P4 invitation lifecycle đã staging-verified.
- **Next exact step:** sau khi có quyền tạo một P16 reference tổng hợp staging, commit reference qua workflow Preview → Commit, chạy DVH validate/save với explicit `limit_entry_id`, rồi kiểm PostgreSQL source/evaluation hash, result `actual/limit/margin/status` và report source cloud. Nếu chưa tạo reference, tiếp tục đóng các gate độc lập: browser export finalization, full negative/fault/resource/volume assertions, release manifest và P18 integrated candidate. Không chuyển P17 sang `DONE-v2` chỉ từ run ID, `/ready`, trigger metadata hoặc direct positive row probe.

## P18/P19 implementation support — 2026-09-09

- `apps/api/tests/test_p18_integration.py` bổ sung local integrated pack `P18-W00`: hai hành trình đi qua FastAPI route thật, organization membership scope, nested QA case, artifact/object storage, Machine QA, Gamma worker boundary, report export, trend projection và Biological Toolkit. Kết quả hiện tại: **2 passed**; đây là `LOCAL_VERIFIED` support evidence, không thay staging/pilot/backup-restore.
- `apps/web/playwright.config.ts` bổ sung local `P18-W01a` trên commit `4f9028f`: Chromium desktop VN timezone, mobile VN timezone và desktop UTC; `npm run test:e2e` đạt **3 passed**. Đây chỉ là responsive/timezone support evidence; tenant/dataset/Auth matrix trên staging và remote browser vẫn mở.
- `scripts/verify-public-deployment.ps1` bổ sung verifier không dùng credential: kiểm HTTP health/readiness, schema revision, release version, OpenAPI CT preview/member/invitation routes, unauthenticated boundary, public web index/bundle, CT preview marker và build label; có thể ghi JSON evidence bằng `-OutputPath`. Lần chạy lịch sử staging ngày 2026-09-09 với schema `20260908_0017` đạt **10/10 checks**; lần chạy trước sau migration P4 trên candidate `311abed` đạt **14/14 checks** tại `docs/evidence/p4-staging-public-smoke-20260909.json`; lần chạy hiện hành trên candidate `2fcf065` cũng đạt **14/14 checks** tại `docs/evidence/p4-staging-public-smoke-20260909-2fcf065.json`. Script chỉ là public smoke tool, không thay authenticated E2E, rollback rehearsal hoặc production gate.
- `scripts/verify-local-backup-restore.py` bổ sung P18-W03a: local PostgreSQL custom dump và MinIO object inventory được restore vào database/bucket tạm, row/object inventory hash khớp, rồi cleanup database/bucket đạt. Evidence tại `docs/evidence/p18-local-backup-restore-20260909.json`; đây là local support, không thay provider backup/restore staging hoặc RPO/RTO.
- Evidence tương ứng được lưu tại `docs/evidence/p19-staging-public-smoke-20260909.json`; file chỉ chứa public URL, HTTP/result metadata, bundle hash và không chứa credential, database URL hay dữ liệu bệnh nhân.
- `docs/runbooks/p20-initial-operations-package.md` và `deployment/railway/production-runbook.md` bổ sung P20-W00 support artifact: vận hành, thresholds target, backup/restore, incident, maintenance, promotion/rollback và handoff template. Đây là tài liệu hỗ trợ `LOCAL_SUPPORT_ONLY`; alert thật, provider restore/RPO-RTO, owner handoff và production release vẫn chưa có evidence.
- `scripts/verify-planning-contract.py` bổ sung verifier fail-closed cho P0: kiểm bốn version tài liệu, cross-reference plan, đủ 21 phase P0–P20 trong BA/spec/plan, workflow/success/error/exit section, FR mapping, testcase S/E, B01–B12, G0–G7 và các support artifact. Evidence `docs/evidence/p0-planning-contract-20260909.json` đạt **pass=true, failed_check_count=0**; đây là consistency evidence, không phải runtime/clinical evidence.
- P20-W01 local support slice: `apps/web/src/api/client.ts` có `ready()` và `PlatformStatusPage.tsx` đọc riêng `/health`, `/ready`, `/version` cùng authenticated `/gamma/queue-metrics`. Dashboard hiện có đánh giá tổng hợp độc lập: chỉ `health=ok` + `ready=ready` + schema parity mới là `SẴN SÀNG`; readiness failure/schema mismatch là `CẦN XEM XÉT`, health failure là `API KHÔNG KHẢ DỤNG`, và từng probe vẫn hiển thị riêng. Local frontend **4 test files / 11 tests** (gồm schema mismatch), lint, typecheck và production build PASS; đây chưa phải alert delivery hoặc P20 exit evidence.
- P20-W01 staging smoke lịch sử: sau khi deploy web descendant `03802e7`, authenticated `/app/system/status` đã hiển thị riêng health `OK`, schema readiness `READY`, schema `20260908_0017`, API version `65dd52b` và queue `available/configured`. Đây là dashboard/readiness evidence của candidate cũ; public metadata candidate hiện tại đã được cập nhật ở P4 smoke, nhưng chưa có alert delivery tới kênh thật, backup/restore provider, owner handoff hoặc maintenance evidence nên P20 vẫn `LOCAL_SUPPORT_ONLY`.
- P19-W01 local support slice: `scripts/create-release-manifest.py` và `scripts/release_manifest.py` tạo/kiểm manifest redacted, hash fixture trong repository, kiểm secret-like value, tự tính lại source/service SHA parity và fail-closed theo gate; test `apps/api/tests/test_release_manifest.py` đạt **4 passed**. `manifest_sha256` chỉ là canonical integrity hash, không phải chữ ký chống giả mạo. Tool đã sẵn sàng cho release packet nhưng chưa có production manifest; metadata deployment/backup/remote E2E thật vẫn là gate P18/P19.

## Source documents read

| Source | Version | Status |
| :--- | :--- | :--- |
| `business-analysis.md` | 0.22 | Business source; detailed feature behavior/workflow/error/recovery/state matrix, business feature cards, P4 membership/invitation addendum, phase handoff and P0–P20 contracts |
| `specification.md` | 1.21 | Behavior/data/error/state/numeric contracts; process-RSS/resource-policy/API-responsiveness evidence for P17 Docker workload, operation/evidence record, change-impact/release manifest, P20 status/readiness surface and exact P4/P10/P11/P12/P13/P14/P15/P16/P17 contracts including binding/report/CT preview and malformed Redis quarantine-before-ACK |
| `technical-specification.md` | 1.20 | Architecture reference; Railway source-identifiable release metadata, bounded-context implementation addenda, P4 invitation schema/API, P8 Redis malformed-message quarantine, P17 process-RSS workload verifier/resource policy/API responsiveness, P20 status/readiness dashboard boundary, CT preview adapter, P18 local backup/restore support and cross-document execution references |
| `plan.md` | 4.12 | Phase/workflow/S-E/C/B tests, DoR/DoD, dependency graph, execution gates, execution ledger, full coverage matrix, P4 invitation/member work packages, P8 local worker/quarantine evidence, P17 local resource-gate checkpoint with process RSS/API responsiveness, P20 status/readiness dashboard package, binding/report/CT work packages, backup/restore support, local browser matrix, source-parity recovery rule, operations runbooks and staging gates |

## Phase status

| Phase | Status | Evidence / next gate |
| :--- | :--- | :--- |
| P0 | DONE | Exit audit passed on 2026-09-05; baseline, traceability, module/route/environment registries and Railway failure issue recorded |
| P1 | DONE | Full local Compose build/health, in-container PostgreSQL migration, synthetic seed persistence, API readiness and web health passed on 2026-09-05 |
| P2 | FOUNDATION READY + LIVE SMOKE PASS | JWT contract, PostgreSQL, Railway staging/production deployment foundation, Supabase Auth configuration and public health/readiness smoke are evidenced; production promotion remains gated by later clinical modules |
| P3 | STAGING E2E PASS | Auth/API bootstrap, organization-scoped dashboard, first-use organization onboarding and protected web routes are deployed; authenticated staging session reached the real organization dashboard |
| P4 | STAGING CRUD PASS / INVITATION E2E OPEN | Organization/site/machine lifecycle remains evidenced; invitation/member migration `20260909_0018` and public routes are deployed/readiness-ready on latest candidate `c6252f7557a5c2c893c5e3082035884e9f26c882`, with API/web/worker source parity and public 15/15 smoke pass; Auth/two-identity browser lifecycle, direct PostgreSQL/hash/status/audit, replay/revoke/expiry/context/concurrency/timeout remain open |
| P5 | STAGING E2E PASS | Nested folder/QA case flow is deployed; staging smoke created `Staging P6 Smoke` and QA case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` |
| P6 | STAGING E2E PASS | Migration `20260907_0005`, artifact metadata/checksum, Input Manifest, duplicate upload, Railway S3-compatible storage, DICOM/measurement validator and QA Archive upload panel are deployed; authenticated synthetic upload created the manifest, validation returned `VALID` with 0 errors/0 warnings and the signed Download action was invoked |
| P7 | STAGING E2E PASS | Migration `20260907_0006`; protocol/rule seed, scoped Machine QA run lifecycle, draft revision, evaluation, immutable result/rerun/compare and trend projection are implemented; staging evaluate returned PASS for `output_factor=100`, `symmetry=1`, `flatness=100`, then rerun and compare preserved both histories |
| P8 | STAGING RTDOSE/MEASUREMENT 3D + LOCAL INDEPENDENT ORACLE PASS; FULL EXIT GATE OPEN | Migrations `20260907_0007` + reliability slice `20260908_0008`; organization/case-scoped preflight, PSQA/ENGINE_TEST profile, deterministic 2D/3D engine with standard-GY RTDOSE adapter, coverage/censor metrics, logical-role-aware artifact contract and database-fenced lease/attempt/outbox slice are implemented and locally tested. Latest staging candidate `c6252f7557a5c2c893c5e3082035884e9f26c882` has the authorized synthetic RTDOSE fixture and new Gamma 3D run `1d5ee035…` `COMPLETED/PASS`, `8/8`; independent oracle evidence has `6/6 PASS`. Staging crash/ack/bounded retry/dead-letter/resource/large-input and release gates remain open. |
| P9 | STAGING E2E PARTIAL / LOCAL VERIFIED | Report revision/export browser smoke on staging; recheck current candidate, visual/export failure gate remains |
| P10 | STAGING SMOKE PARTIAL / EXIT OPEN | Migration `20260908_0010`, API/UI slice, 7 focused tests and authenticated staging trend smoke pass; large-series, complete negative matrix, visual/accessibility and release evidence remain |
| P11 | LOCAL VERIFIED / STAGING OPEN | Migration `20260908_0011`, library API/UI and local `3/3`; staging browser/consumer snapshot and full S/E/C evidence remain |
| P12 | STAGING E2E PASS / EXIT OPEN | Migration `20260908_0012`, Biological Hub route/API/UI, staging browser create/validate/edit/save/clone/archive/history đã chạy trên dữ liệu tổng hợp; PostgreSQL state, refresh/reconnect, renderer integration và full S/E/C remain |
| P13 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0013`, BED/EQD2 browser validate→save hai snapshot, history readback, chart/table và export đã chạy trên staging; direct PostgreSQL checksum/no-QA-linkage query và release manifest còn mở |
| P14 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0014`; candidate `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b` đã chạy validate-only/no mutation, save, preview reorder không persist, refresh history và JSON/CSV payload parse; comparison `77045b33…`; direct PostgreSQL row/checksum và organization-scope negative probe còn mở, release-manifest test ID đã ghi |
| P15 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0015`; candidate `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b` đã chạy re-irradiation no-recovery/recovery/sensitivity/spatial-unavailable và fraction-compensation prefix/error recovery, refresh history và JSON/CSV payload parse; snapshots `2f66676e…`/`7d805462…`; same-key replay, direct PostgreSQL/scope, full S-E và final filename còn mở |
| P16 | STAGING SMOKE VERIFIED / EXIT OPEN | Migration `20260908_0016`, web build `9262bfd`; staging DRAFT/publish/archive, import row-level invalid, explicit-use snapshot đã pass; direct PostgreSQL/hash/scope, compare/history/export, full fault matrix và release evidence còn mở |
| P17 | STAGING IMMUTABILITY GUARD PASS / EXIT OPEN | Engine/API/UI/migration `20260908_0017`, ORM + database guard `20260909_0019`, bounded CT preview, explicit P11/P16 limit binding and DVH report-source local gates pass; staging `/ready`/`/version` match candidate `d04fb5a3561804bd3553b36886902e1c50b2f18f` and schema `20260909_0019`; target trigger exists, temporary probe rejects UPDATE/DELETE and retained run is untouched; browser RTDOSE/RTSTRUCT/CT run, export-content, direct PostgreSQL row/checksum/scope probe and object-storage byte re-hash pass; binding/report cloud, fault/volume and release evidence remain |
| P18 | LOCAL SUPPORT ONLY | `P18-W00` integrated API pack, `P18-W01a` local browser matrix và `P18-W03a` local backup/restore pass; authenticated tenant/dataset matrix, fault/load, provider restore/RPO/RTO và pilot remain open |
| P19 | SOURCE/SCHEMA STAGING VERIFIED / MANIFEST TOOL READY | API/web/worker source-label recheck trên candidate `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b`; public smoke đạt 15/15 health/readiness/schema/version/OpenAPI/unauthenticated/web parity checks với schema `20260909_0019`; release manifest `docs/evidence/release-manifest-staging-0c0b5ff.json` verify `valid=true`, `service_sha_parity=true`, `release_gate=ELIGIBLE`. Authenticated E2E, promotion, remote fault/restore, DNS/TLS/Auth và rollback remain open |
| P20 | LOCAL SUPPORT ONLY | Initial operations and production rollback runbooks exist; alert, provider backup/restore, owner handoff and maintenance regression evidence remain open |

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
- The P12 web route is `/app/biological` and uses the generated Stitch screen `b32ef9de691f48449ec23e491a6b634d`. P13, P14, P15 and the local P16 Knowledge Library route are now available in source; the P16 staging/release gate is still open. The UI does not create fake calculation runs and does not link scenarios to QA cases automatically.
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

## Local P16 Biological Knowledge Library evidence — verified 2026-09-08

- Migration `20260908_0016_biological_library.py` upgrades after `20260908_0015` and creates organization-scoped `biological_library_entries` with typed entry families, version uniqueness, clone lineage, optimistic revision, source status, JSON content/citation/applicability and content hash. The Biological bounded context remains independent from QA/patient/treatment records.
- Pure engine `services/biological_library_engine.py` normalizes key/context, validates dose-limit metric/operator/unit/volume/parameter, alpha/beta, source/citation, applicability and safe finite JSON; exact context matching does not treat missing values as wildcard and no external URL is fetched.
- API `api/biological_library.py` exposes validate-only, scoped list/detail/history, DRAFT create/patch, clone/publish/archive, compare, explicit-use snapshot, row-level import preview/commit and JSON/CSV export. Every organization read resolves membership before entity lookup; published entries are immutable and use snapshots pin source/version/hash/override.
- Frontend route `/app/biological/knowledge` provides search/filter, structured editor, validation/warnings, lifecycle/history/compare, import preview/commit, explicit target/override and export states. It reuses the active Clinical Precision Interface and is registered as MOD-14; P15 fraction compensation remains MOD-13.
- Local verification on the same working tree candidate: `tests/test_biological_library.py` **3/3**, full backend suite passed, Ruff, strict mypy, frontend lint/typecheck/Vitest/production build, migration head `20260908_0016` and OpenAPI regeneration/check passed. The Vite build retains only the known bundle-size warning.
- **Evidence level:** `STAGING_SMOKE_VERIFIED`. The authenticated staging browser route on web build `9262bfd` created `P16_STAGING_DMAX_0908` v1 (`DOSE_LIMIT`, `DMAX MAX 45 Gy`, content SHA-256 `9d6555e7403c698ab88a29f2d02f0683a2c24ac7cb772a1ff8bbed8bc2b7dd42`), published revision 2, created explicit-use snapshot `1de9704f6b061e354308…` with `DOSE_LIMIT_NOT_APPLICABLE` warning, and archived revision 3. Import preview reported 1 valid + 1 rejected row with `REQUEST_VALIDATION_FAILED`. Direct PostgreSQL row/hash/scope, compare/history/export, full negative/fault matrix and redacted release manifest remain open. Direct calculator prefill is intentionally a later integration package; explicit-use snapshot currently does not mutate P13–P15/P17.

## Live Railway P16 Biological Knowledge Library smoke evidence — verified 2026-09-08

- API staging `/api/v1/ready` returned HTTP 200 with `status=ready` and `schema_revision=20260908_0016`; the web route `https://rt-connect-web-staging-staging.up.railway.app/app/biological/knowledge` served Build `9262bfd` and exposed the P16 navigation item.
- Using the authenticated synthetic staging session, the browser created `P16_STAGING_DMAX_0908` as a `DOSE_LIMIT` with `DMAX MAX 45 Gy`, Lung cancer/Thorax/VMAT/Spinal cord context, and content SHA-256 `9d6555e7403c698ab88a29f2d02f0683a2c24ac7cb772a1ff8bbed8bc2b7dd42`. The UI/API reported DRAFT v1, then published it as revision 2 and displayed it as `PUBLISHED UNVERIFIED`.
- The import preview was exercised with two rows: one valid synthetic `DOSE_LIMIT` and one row without `entry_key`; the UI reported `Hợp lệ 1 · loại 1` and identified row 2 as `REQUEST_VALIDATION_FAILED`. No invalid row was committed.
- The published entry created explicit-use snapshot `1de9704f6b061e354308…` for `KNOWLEDGE_REFERENCE`; the UI reported `SOURCE_VALUES` and the expected `DOSE_LIMIT_NOT_APPLICABLE` warning, confirming no automatic application into P13–P15/P17. JSON/CSV/download/compare were not used as closure evidence in this smoke and remain to be checked.
- The synthetic entry was archived after the smoke, producing revision 3 and leaving the default active list empty; history/use snapshot remains retained. No patient identifier, QA case, TPS, PACS or clinical prescription was introduced.
- **Evidence level:** `STAGING_SMOKE_VERIFIED` only. P16 `DONE-v2` still requires direct Railway PostgreSQL row/version/hash query, explicit cross-organization negative probe, compare/history/export, full failure/persistence/reconnect matrix and a redacted deployment/config manifest. The browser smoke does not establish clinical validation or direct calculator binding.

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

## P17 Visual Dose / DVH local implementation evidence — verified 2026-09-09

- **Scope:** local synthetic DICOM only; no patient, PACS or clinical treatment data was used. This is implementation evidence, not clinical validation or production readiness.
- **Engine:** `apps/api/src/rt_connect_api/services/dose_dvh_engine.py` reads physical-dose RTDOSE in Gy with `DoseGridScaling`, normalizes single-frame z offsets, maps patient LPS coordinates using DICOM orientation, selects ROI by ROINumber, rasterizes closed polygons with parity, computes weighted Dmin/Dmean/Dmax/D(x)/V(x), coverage, cumulative curve, dose-native preview and deterministic result SHA. The same resource-bound path now validates `DVH_MAX_CT_PIXELS` for CT-backed DVH operations.
- **CT preview:** the bounded read-only path decodes single-file/supported multi-frame CT, applies HU and window/level semantics, selects CT/dose frames, maps dose and optional ROI masks with patient-LPS nearest-neighbor sampling, reports crosshair/mapping/valid-outside counts and a deterministic preview hash. It does not perform deformable registration, CT-series aggregation, spatial dose accumulation or a DB/job/report mutation.
- **API/storage:** migration `20260908_0017_dvh_analysis.py` adds immutable `dvh_analysis_runs`; `apps/api/src/rt_connect_api/api/dvh.py` provides scoped inputs, validate-only, save/replay, history/detail and JSON/CSV export plus the read-only `GET .../dvh/ct-preview` operation. Every saved run pins artifact/manifest IDs, byte checksums, normalized request, engine version, result/warning/error snapshots and actor; CT preview itself is not persisted as a run.
- **Web:** route `/app/qa/cases/:caseId/dvh` and QA Archive quick link provide input selection, ROI discovery, coverage policy, metric entry, validation preview, save, visual preview, CT frame/window/overlay controls, result/history/provenance and export. The route is case-specific and hidden from the global sidebar.
- **Local checks:** P17 DVH/CT engine/API/report-source/binding focused suite passed **28/28** (`14` DVH engine, `7` DVH API, `4` report-source, `3` Biological Library); the full backend suite passed **169 tests** with engine commit `cdf4372` (`p17-dvh-1.1.0`), được kiểm lại trên clean verification commit `50d890e`, cùng Ruff, strict mypy, frontend lint/typecheck/Vitest/build, migration và OpenAPI checks. The new oracle covers nonuniform slice thickness, volume-weighted Dmean/D(x)/V(x), and the pinned cumulative-DVH interpolation convention; the added regression confirms persisted detail/export remain snapshot-based after source-byte drift. Vite still reports the existing bundle-size warning; it is recorded as a performance follow-up, not treated as a functional pass. Evidence: `docs/evidence/p17-local-volume-weighted-dvh-20260909.json`.
- **P17-W06 local volume/concurrency checkpoint:** benchmark tổng hợp không có dữ liệu bệnh nhân với shape `64×128×128` (`1,048,576` voxel), ROI phủ toàn grid và bốn dose level `1–4 Gy` chạy trên `p17-dvh-1.1.0`; host có median `1.2667533 s`, max peak Python-traced allocation `69,235,606 bytes`; sau rebuild đúng source, API Docker container có median `0.8206198 s`, max peak traced `69,237,022 bytes`, `/health=ok`, `/ready=ready`, schema `20260909_0018`, oracle `Dmean=2.5 Gy`, `Dmin=1 Gy`, `Dmax=4 Gy`, selected volume `12,582.912 cc`. Verifier `scripts/verify-p17-docker-workload.ps1` chạy 2 job đồng thời × 3 lần; 6/6 kết quả giữ cùng engine/oracle, sampled container memory cao nhất `305,659,904 bytes` (291.5 MiB) qua 3 mẫu. Evidence `docs/evidence/p17-local-volume-benchmark-20260909.json`, `docs/evidence/p17-local-docker-volume-benchmark-20260909.json` và `docs/evidence/p17-local-docker-workload-20260909.json`; `performance_gate=NOT_ASSESSED`, vì sampled memory không phải peak RSS/service limit và fault/staging/API responsiveness chưa đo.
- **Local dependency checkpoint:** Docker PostgreSQL 17, Redis 7 và MinIO pinned image đã chạy; Alembic `upgrade head` lần đầu nâng `20260908_0017 → 20260909_0018`, lần chạy lặp lại không còn migration pending, `alembic current` xác nhận `20260909_0018 (head)`. Evidence: `docs/evidence/p1-p17-local-postgres-20260909.json`; không ghi connection string hoặc secret.
- **Configuration regression found and fixed:** Docker Compose từng parse `SCHEMA_REVISION: 20260909_0018` không nháy thành `202609090018`, làm `/api/v1/ready` báo `not_ready` dù DB đúng revision. Đã quote giá trị, thêm test `test_compose_keeps_schema_revision_as_the_exact_string`, recreate API container; readiness sau sửa trả `ready` với `20260909_0018`. Đây là lý do phải kiểm rendered effective config chứ không chỉ đọc file YAML.
- **Not yet evidenced:** deployment of this CT delta on staging, authenticated staging CT artifact upload and browser overlay, direct PostgreSQL row/checksum/scope query, object-storage drift/fault recovery, controlled container peak RSS/resource gate, full negative matrix, staging P11/P16 actual-limit binding/report source and an external/vendor/reference DVH oracle for arbitrary datasets. The committed-fixture independent oracle is now evidenced separately and remains local support only. Local 1M-voxel and 2-job Docker concurrency measurements are recorded separately and are not release gates.

## P17 independent known-answer oracle — local verified 2026-09-09

- `scripts/verify-p17-independent-dvh-oracle.py` validates the committed RTDOSE/RTSTRUCT fixture identity and calculates expected values outside the engine helpers before comparing the engine result. It checks 13 scalar/map comparisons covering selected voxel count, volume, Dmin/Dmean/Dmax, D2/D50/D95/D98 and V0/V5/V8/V20.
- Evidence `docs/evidence/p17-independent-dvh-oracle-20260909.json` records the dose/structure SHA-256 values, engine key/version, expected/observed metrics and all comparison outcomes; **13/13 PASS**. This is `LOCAL_INDEPENDENT_ORACLE_VERIFIED` for the known-answer fixture, not a generic vendor/reference oracle or a staging/clinical-release gate.

## P17 Docker cgroup memory observation — local support rerun 2026-09-09

- `scripts/verify-p17-docker-workload.ps1` now reads cgroup v1 `memory.current`, `memory.max_usage_in_bytes` and `memory.limit_in_bytes` when available, in addition to sparse `docker stats` samples. The rerun kept 2 concurrent jobs × 3 repeats, 6/6 identical engine/oracle results, `/health=ok`, `/ready=ready`, schema `20260909_0018`, and no patient data.
- The API container reported cgroup current `148,406,272` bytes and peak `367,915,008` bytes since container start; the local cgroup limit is unbounded/sentinel. These numbers are explicitly `is_peak_rss=false` and are not a performance pass. Evidence was refreshed at `docs/evidence/p17-local-docker-workload-20260909.json`; the contract wording is synchronized in `specification.md` v1.19, `technical-specification.md` v1.18 and `plan.md` v4.9.

## P17 explicit limit binding and Report Builder source — local candidate verified 2026-09-08

- `apps/api/src/rt_connect_api/services/dvh_limit_adapter.py` now provides the explicit boundary from P17 to P16 `DOSE_LIMIT` entries and P11 `ACTIVE` protocol rules. The adapter scopes the initial lookup by `organization_id`, rejects simultaneous sources, rejects override without a P16 source, validates P16 override fields, requires an explicit P11 metric rule, and never searches or auto-applies a different reference.
- The adapter evaluates supported DMIN/DMEAN/DMAX, Dx and Vx metrics against the already computed DVH result, checks request coverage of Dx/Vx and unit compatibility, preserves the pure engine hash as `engine_result_sha256`, and writes a separate binding/evaluation hash. Source warnings are preserved; `rule_status` is separate from display `status=REVIEW_REQUIRED`.
- `apps/api/src/rt_connect_api/api/reports.py` accepts a saved DVH run as `source_type=DVH` and snapshots it only when the run belongs to the current organization. `ReportBuilderPage.tsx` can select a QA case and its DVH history; report creation does not rerun DVH or resolve a different latest run.
- **Local evidence:** focused suite `26 passed` (13 DVH engine + 6 DVH API workflows + 4 report tests + 3 Biological Library tests), full backend suite `168 passed`, Ruff and strict mypy pass; frontend lint/typecheck/Vitest pass. Added coverage includes P16 D95 binding, P11 lowercase rule lookup, binding conflict, missing metric, invalid override, fail-closed DVH input discovery/validation when the manifest is pending, invalid, or does not match the artifact checksum, CT Frame of Reference mismatch, no-overlap read-only preview, CT resource guard, changed CT bytes, and the Compose schema-revision type regression.
- **Not yet evidenced:** authenticated browser selection of a real saved DVH run, PostgreSQL source/evaluation hash query, CT preview staging binding, resource/fault/volume gates and independent/reference DVH oracle. Deployment/readiness of the previous candidate is verified, but the local contract plus health/readiness are not a complete staging workflow or clinical-readiness claim.

## Live Railway P17 deployment/readiness evidence — verified 2026-09-08

- Staging API service `Railway-API-staging`, worker `RT-connect-gamma-worker-staging` and web service `RT-connect-web-staging` all redeployed from commit `a546bb15155baa6ce3b59a86d1f1e1240aaf6c5a` and report `SUCCESS`: API deployment `99daa470-cea3-4bd9-a265-6a13632e750d`, web deployment `fa69b146-1f4d-4972-83ec-c14a9bb11a6d`, worker deployment `b9d814d2-dd9d-4caa-9246-30fd377f0ae5`. The effective service roots remain `/apps/api` for API/worker and `/apps/web` for web; the existing API config-as-code path `/apps/api/railway.toml` is preserved.
- API `https://gleaming-cooperation-staging.up.railway.app/api/v1/health` returned HTTP 200 with correlation ID; `/api/v1/ready` returned HTTP 200 with `status=ready` and `schema_revision=20260908_0017`; `/api/v1/version` returned HTTP 200 with application build identifier `9262bfd` and the same schema revision. `/api/v1/openapi.json` returned HTTP 200 and exposed `limit_entry_id`, `protocol_version_id`, `protocol_metric_key`, `limit_override` and report `source_type=DVH`.
- Web `https://rt-connect-web-staging-staging.up.railway.app/` returned HTTP 200 and served the candidate bundle (`index-DOkYs2lH.js`, `index-Ks1ZYwE_.css`). Browser navigation can open `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh` and display the P17 workspace; authenticated saved-run selection is still pending because the case has no RTSTRUCT yet.
- The existing synthetic case currently exposes one valid RTDOSE and zero RTSTRUCT artifacts; the P17 controls therefore correctly show `1 dose · 0 structure` and keep `Validate & preview`/`Tính và lưu DVH run` disabled. This is an expected input-preflight state, not a server/deployment failure.
- The committed synthetic RTSTRUCT candidate is `docs/fixtures/p17-rtstruct-v1-smoke.dcm`, generated by `scripts/generate-p17-dvh-structure-fixture.py`. Local known-answer output is `FULL_ROI`, 4 selected voxels, mean `6.5 Gy`, D95 `5.20 Gy` under the volume-weighted piecewise-linear cumulative-DVH convention, SHA-256 `16a79df3129757d9df8b48bd095f0b4b70b24713ea5255e24719d46e6808d401`. It has not yet been uploaded to staging, so no staging DVH run ID is claimed here.

## P17 CT preview delta — staging deployment verified, CT data workflow pending — 2026-09-09

- **Implementation:** `apps/api/src/rt_connect_api/services/dose_dvh_engine.py` now accepts the configured CT pixel budget through both DVH validation/run and CT preview paths; `apps/api/src/rt_connect_api/api/dvh.py` exposes the read-only `GET .../dvh/ct-preview` contract. `apps/web/src/pages/DVHPage.tsx` renders CT grayscale/HU, dose/ROI overlays, frame/window controls and patient-LPS crosshair metadata.
- **Contract:** supported scope is a validated CT single file or supported multi-frame object with top-level geometry, same `FrameOfReferenceUID` as RTDOSE, single-channel MONOCHROME1/2, bounded preview pixels and nearest-neighbor overlay. CT series aggregation, Enhanced CT functional-group-only geometry, external/deformable registration and spatial accumulation remain unsupported.
- **Verification:** CT engine/API cases, full backend suite, Ruff, strict mypy, frontend lint/typecheck/Vitest/build, migration and OpenAPI checks passed on the working tree. The bundle-size warning remains a recorded performance follow-up.
- **Deployment state:** at the captured checkpoint, Railway API deployment `c5807acb-dd49-4279-8304-ecc95141543d` is `SUCCESS` from functional source `893ae2d46c197b80fc78e29cdea25ab19a54154c`; web `da3a82c5-8ec0-436c-a879-8acb118350a5` and worker `01191861-6bae-4b53-bef9-4aa41fc883b` are `SUCCESS` from documentation-only descendant `7c8ebe15152fb7017307c2ab2d337e051a04cfb4`. Public OpenAPI contains the CT route and the web bundle contains the CT controls. `/api/v1/version` still reports application build label `9262bfd`, so release metadata must later be made source-identifiable; do not treat the label alone as proof of source parity.
- **Next exact action:** use the committed synthetic CT/RTSTRUCT fixture only after the user confirms the browser file-selection step; upload and validate both in the staging case, then capture CT success S12–S16 and error/recovery E24–E30 evidence without using patient data.
- **Fixture readiness:** the committed CT fixture is now available at `docs/fixtures/p17-ct-v1-smoke.dcm`; its frame 1 is the positive overlay oracle and frame 2 is the explicit no-overlap oracle. The repository hash must be compared with the uploaded artifact manifest before any staging run is treated as evidence.

## P6/P17 Archive DVH preflight truthfulness — local verified 2026-09-09

- The QA Archive DVH shortcut no longer renders a static claim that `RTDOSE + RTSTRUCT` are already `VALID`. It now derives the banner from the current case artifact list and counts only `DICOM` artifacts whose `data_status` is `VALID`, split by `RTDOSE`, `RTSTRUCT` and `CT` modality.
- The empty/partial-input state is explicit: the staging case with one valid RTDOSE and zero RTSTRUCT is shown as `DVH preflight: 1 RTDOSE · 0 RTSTRUCT · 0 CT VALID`, with the DVH action remaining unavailable at the case workspace until the required inputs exist. The archive hint also states that RTDOSE and RTSTRUCT are required, CT is optional for anatomy overlay, and only validated DICOM artifacts participate in preflight.
- Loading and artifact-fetch failure have separate labels, so a transient API state is not presented as clinical input readiness. The summary helper is covered by frontend tests for valid/invalid/non-DICOM filtering and loading/error/ready labels.
- Local verification after the correction: ESLint PASS, TypeScript typecheck PASS, Vitest **8/8** PASS, production build PASS. The existing Vite bundle-size warning remains a performance follow-up only.
- **Staging runtime probe after push:** commit `558febf26335b3aa533989f0ceb9aebceee4ec6f` was pushed to the configured branch; the public web now serves bundle `assets/index-7zlr-Qxu.js` (SHA-256 `93b0fc4ce8e112b722babc9ea9f32330a281096e2fb4ab5f67dab2a65ab83c08`). Authenticated browser observation of case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` confirmed the dynamic partial-input label and absence of the old static claim. Evidence: `docs/evidence/p17-staging-archive-dvh-preflight-20260909.json`. This is a UI/runtime probe, not source-to-runtime release-manifest parity.
- This correction improves the evidence boundary but does not close P17: authenticated staging upload of the synthetic RTSTRUCT/CT, validation, DVH validate→save→replay→refresh/export, CT preview/overlay, direct database/hash/scope checks, fault/volume/resource gates and independent oracle remain open.

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
- The earlier pre-upload checkpoint requiring an explicit synthetic RTSTRUCT upload is superseded by the verified P17 staging RTDOSE/RTSTRUCT/CT browser smoke below; it remains in this section only as historical context. No patient or clinical dataset was used.
- Four Biological designs must be regenerated in P12–P15.

## P17 staging RTDOSE/RTSTRUCT/CT browser smoke — verified 2026-09-09

- **Scope and authorization:** after explicit user confirmation, only the repository-generated synthetic RTDOSE fixture was uploaded to the existing staging case; the case already contained the synthetic RTSTRUCT and CT fixtures uploaded earlier. No patient, PACS or treatment dataset was used.
- **Artifact evidence:** case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` exposes two valid RTDOSE artifacts, one valid RTSTRUCT and one valid CT. The selected RTDOSE is `gamma-rtdose-v1-smoke.dcm` with local SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`; staging UI shows the matching prefix `ca5c9168eb9b045e…`. RTSTRUCT and CT UI prefixes match local fixture hashes `16a79df3129757d9…` and `0b1d3bfd6adf33f1…` respectively. Artifact IDs and the complete redacted evidence record are in `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`.
- **Fresh browser workflow:** the current web build `4b6423e5efe8fb10a9832bd66ed051f259ccb01b` (functional correction from `fbbfa812feaa164197259f83e581e9271a2df670`, followed by the evidence-only docs push) was loaded from the pushed branch. On fresh navigation to `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh`, the default valid RTSTRUCT automatically loads ROI `#1 · P17_TARGET · 1 contour`; `Validate & preview` and `Tính và lưu DVH run` are enabled. The saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4` reappears after refresh with engine `p17-dvh-1.1.0`, `FULL` coverage, 4 voxels, volume `0.004 cc`, Dmean `6.500 Gy`, D95 `5.200 Gy`, input fingerprint and result SHA preserved.
- **CT browser workflow:** selecting CT frame `#1` returns `LPS LINKED`, `NEAREST_NEIGHBOR_IN_PATIENT_LPS`, ROI `#1 · P17_TARGET`, and crosshair `dose grid center`. Selecting frame `#3` (`frame_index=2`, the repository's no-overlap oracle) returns `NO DOSE OVERLAP` and the expected warning that the selected CT slice does not intersect the RTDOSE grid; the dose overlay is empty. This confirms both the positive overlay and the bounded warning path on staging.
- **Negative validation workflow:** selecting the older staging RTDOSE with UI hash prefix `544f355fa286…` and running `Validate & preview` produced the expected `DVH_DOSE_UNITS_UNSUPPORTED` error because its dose units were not `GY`; history remained at one saved run and no new run was created. Restoring the newly uploaded RTDOSE with UI hash prefix `ca5c9168eb9b…` and validating again produced `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.` This confirms the unit guard and the non-mutating validate-only path; the full P17 negative/fault/resource matrix remains open.
- **Direct PostgreSQL probe:** a read-only query executed inside the connected Railway staging API container returned the three artifact rows, three `input_manifests` rows and the saved DVH row for the case. All artifact/manifest/run organization and case scopes matched; all three artifacts and manifests were `VALID`; every manifest checksum matched its artifact SHA-256; the persisted run was `COMPLETED`, `p17-dvh-1.1.0`, with the expected dose/structure/CT IDs, request fingerprint and result SHA. Evidence is recorded in `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`; the follow-up object-storage byte re-hash and snapshot-field recheck also pass, while the stronger immutable-snapshot mutation guard remains open.
- **Snapshot recheck:** a second read-only query after the object re-hash returned the same DVH run fingerprint/result SHA, with `created_at == updated_at` and no mutation command issued. This is a direct persistence observation, not proof against privileged database tampering; the application-level source-drift/detail/export regression is covered by the local focused suite below.
- **Object-storage byte re-hash:** a read-only probe in the connected Railway staging API container downloaded the three case objects through the configured storage adapter. Observed byte sizes `898/866/842` and re-hashed SHA-256 values matched the corresponding artifact rows for RTDOSE/RTSTRUCT/CT; assertion `object_count=3`, `byte_rehash=True` passed. Evidence is recorded in `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`; this closes the object-byte integrity sub-gate only. The immutable-snapshot mutation guard and broader fault/resource/release gates remain open.
- **Frontend correction shipped with the smoke:** `apps/web/src/pages/DVHPage.tsx` now separates the initial input manifest from the structure-specific ROI request and renders `Chưa chọn CT` when the optional CT query is disabled; `apps/web/src/pages/DVHPage.test.tsx` pins both behaviors. Web typecheck, lint, Vitest **12/12** and production build pass; the existing Vite chunk-size warning remains a performance follow-up.
- **Export probe:** the JSON and CSV buttons were exercised for the saved run. The browser harness did not expose a download event, but both browser download contents were captured and parsed from the local Downloads directory: JSON `17,738` UTF-8 bytes, SHA-256 `9e1106e3a1e2a5e4964dd109f650c88ea9513d80ae1ec6b0d91b60014b656723`, valid JSON with matching run ID/input fingerprint/result SHA; CSV `10,478` UTF-8 bytes, SHA-256 `c626590dcb470d8d60a67d2f8d7a62c22928de40997d455c960ee22aeed15766`, 21 parsed rows with matching case/engine/result SHA. The browser harness retained the `.crdownload` suffix, so final filename finalization remains a browser/runtime observation rather than an application-content failure.
- **Boundary:** this closes the authenticated browser upload/validation/ROI/DVH/CT-preview, export-content, targeted direct PostgreSQL row/checksum/scope and object-storage byte-integrity sub-slices only. Immutable-snapshot mutation guard, full negative/fault/resource/volume gates, P11/P16 binding/report cloud evidence, browser finalization, release manifest and production promotion remain open. The older “fixture not uploaded” bullets above are historical checkpoints and are superseded by this section.
- **Local regression after this checkpoint:** the focused P17/P16/report/library suite (`test_dvh_engine.py`, `test_dvh.py`, `test_reports.py`, `test_biological_library.py`) passed **28 tests**, including saved-run detail/export stability after source-byte drift. This is local evidence and does not replace the staging fault/resource or release gates.

## P17/P19 latest source-parity and browser recheck — 2026-09-09

- Candidate `7a340b281f0bf8a91a5c72dc861c71c82009bce8` is now the current staging source-parity checkpoint. API, web and worker were redeployed from the documentation/source-parity commit; public verifier evidence `docs/evidence/p19-staging-public-smoke-20260909-7a340b2.json` reports **15/15 checks PASS**, schema `20260909_0019`, API version parity and web bundle/source marker parity.
- The authenticated browser was reloaded on that build at `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh`. It observed `2 dose · 1 structure`, the selected synthetic RTDOSE prefix `ca5c9168eb9b…`, selected synthetic RTSTRUCT/CT, ROI `#1 · P17_TARGET`, saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`, and CT overlay `LPS LINKED` / `NEAREST_NEIGHBOR_IN_PATIENT_LPS` with the expected crosshair. This is a recheck of the existing synthetic staging data, not a second upload.
- JSON/CSV export payloads were captured again from the browser Downloads directory. JSON (`17,738` bytes) parsed and matched the run/result SHA; CSV (`10,478` bytes, 21 rows) parsed and matched case/engine/result SHA. Both files remain `.crdownload` in the Edge/CUA harness, so final filename finalization is **UNVERIFIED**. The application-content sub-gate is PASS; the browser/runtime finalization observation remains open and is not silently promoted to PASS.
- Updated evidence: `docs/evidence/p17-staging-dvh-ct-browser-20260909.json` (`latest_runtime_recheck`) and `docs/evidence/p19-staging-public-smoke-20260909-7a340b2.json`. P17 remains `IN_PROGRESS`; remaining gates are browser finalization evidence, full negative/fault/resource/volume checks, binding/report staging evidence, worker/release manifest and production promotion.
- Report-source follow-up: Report Builder đã tạo revision 1 `P17 staging DVH report smoke` từ đúng saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`; snapshot SHA `fd99a61aed10191ae169155bfd645c02ef56ffda2ded03384efe43b22d01ea85`, input fingerprint và result SHA khớp run. JSON export object-storage document báo `10,536` bytes, renderer `report-renderer-0.1`, source ID và content SHA khớp; không rerun DVH và không mutation `DVHAnalysisRun`. Evidence nằm trong `report_builder_probe` của `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`. P11/P16 limit/protocol binding vẫn chưa được gắn và tiếp tục là gate riêng.

## P17/P19 source-parity recovery — 2026-09-09

- Public verifier phát hiện drift sau commit `0098cf1`: web đã nhận docs-only descendant, còn API vẫn ở `7a340b…` do path filter; đây là deployment/source-parity drift, không phải lỗi case, database hay DVH.
- Đã đặt parity marker trong cả `apps/api/README.md` và `apps/web/README.md`, push candidate `b0263c932c740d4f36f19867241d5c1e07014765`, chờ Railway deploy đồng bộ và chạy lại verifier với schema `20260909_0019`.
- Kết quả public **15/15 PASS**; evidence `docs/evidence/p19-staging-public-smoke-20260909-b0263c9.json`. API `/health`, `/ready`, `/version`, OpenAPI và unauthenticated membership boundary PASS; web index/bundle, CT/membership marker và exact source marker PASS.
- Evidence drift trước sửa được giữ tại `docs/evidence/p19-staging-public-smoke-20260909-drift-0098cf1.json` để truy vết. Quy tắc kế hoạch mới: commit docs/root hoặc chỉ một service phải kèm parity marker/watch-path change hoặc deploy thủ công service còn lại, sau đó exact-SHA verifier mới được phép ghi `source parity PASS`.
- Fixture RTDOSE tổng hợp được upload theo xác nhận của người dùng từ trước và không upload lại trong lần recovery này; case vẫn giữ `2 RTDOSE · 1 RTSTRUCT · 1 CT`, saved run và report snapshot hiện có.
