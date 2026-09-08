# RT-CONNECT — Kế hoạch triển khai và nghiệm thu P0–P20

- Phiên bản: **2.6**, ngày 2026-09-08.
- Nghiệp vụ: [business-analysis.md](business-analysis.md) v0.12.
- Hợp đồng hành vi chi tiết: [specification.md](specification.md) v1.6.
- Kiến trúc tham chiếu: [technical-specification.md](technical-specification.md) v1.4.
- Evidence trước đợt cập nhật: [implementation-progress.md](implementation-progress.md).
- Bản kế hoạch trước: [plan v1.5 — lịch sử](docs/history/plan-v1.5.md).
- Phạm vi lần cập nhật này: chi tiết hóa workflow, trường hợp chạy đúng, lỗi, phục hồi, invariant, evidence và exit gate cho P0–P20; đồng bộ slice implementation P6/P8/P9/P10/P11/P12/P13, migration schema `20260908_0013`, BED/EQD2 engine/API/UI và kết quả kiểm thử local ngày 2026-09-08. Staging E2E sau slice này vẫn là gate riêng; không suy diễn từ test local.

## 1. Cách thực hiện kế hoạch

Kế hoạch là hợp đồng công việc và nghiệm thu, không phải bảng chứng nhận code đã chạy đúng. Một phase có smoke test cũ đạt vẫn có thể thiếu tính năng trong baseline chi tiết mới. Không xóa evidence cũ, nhưng chỉ ghi DONE-v2 khi đủ gate v2.

Thứ tự sử dụng: đọc FR trong nghiệp vụ → contract trong specification → entry gate và task của phase → chạy các test S/E và ma trận chung → ghi evidence → kiểm exit gate → cập nhật checkpoint.

Các quyết định giữ nguyên: bác sĩ/kỹ sư ngang quyền trong organization; không thêm action roles hoặc luồng phê duyệt case/report; report toàn quyền tùy chỉnh; Biological Toolkit độc lập. Bộ test là gate phát triển. Pilot P18 ghi nhận dataset thực tế và sai khác, không bổ sung phase pháp luật/FDI. Các chỗ commissioning trong tài liệu lịch sử không tự thêm một approval gate ngoài phạm vi này.

### 1.1. Trạng thái thực thi

| Trạng thái | Ý nghĩa |
| :--- | :--- |
| NOT_STARTED | Chưa triển khai gói công việc. |
| IN_PROGRESS | Đang có code/tài liệu, chưa đủ gate. |
| LOCAL_VERIFIED | Có test local trên SHA đã ghi. |
| STAGING_VERIFIED | Có luồng từ browser đến kết quả bền vững trên staging đúng release. |
| NEEDS_REVALIDATION | Có evidence cũ, nhưng yêu cầu/contract mới cần kiểm thêm. |
| BLOCKED | Ghi rõ dependency/input thiếu và phần độc lập có thể làm. |
| DONE-v2 | Tất cả MUST task/test/exit của phase đạt, có evidence tương ứng. |

Test chỉ dùng NOT_RUN / PASS / FAIL / BLOCKED / NOT_APPLICABLE. NOT_APPLICABLE phải có lý do theo phạm vi, không dùng để bỏ tính năng MUST. SEV0/SEV1 là mức nghiêm trọng bug, không nhầm mã phase P0/P1. Một gói có code local nhưng chưa đủ staging/oracle/benchmark vẫn giữ checkbox mở và ghi `LOCAL_SLICE_ONLY`, không đánh dấu DONE-v2.

### 1.2. Checkpoint hiện tại dựa trên repository

| Nhóm | Evidence trước đây | Việc còn phải làm theo v2 |
| :--- | :--- | :--- |
| P0–P1 | Có registry, CI, local Compose và migration evidence trong progress log | Đối soát toàn bộ FR mới, contract errors/version và clean setup nếu thay runtime. |
| P2–P3 | Có staged Auth/onboarding/dashboard và health smoke | Kiểm session expiry, runtime config, schema readiness và dashboard đầy đủ; không suy diễn từ session còn đăng nhập. |
| P4–P5 | CRUD hierarchy/folder/case có staged smoke | Invitation/member flow, restore, simultaneous edits, complete filter/history là gate bổ sung cần kiểm/triển khai. |
| P6–P7 | Synthetic upload/validation và Machine QA evaluate/rerun/compare đã được ghi | Round-trip checksum evidence, declared-type mismatch, interrupted upload, autosave/concurrency và broader boundary tests cần kiểm. |
| P8 | 2D JSON/Redis worker/retry và 3D PSQA RTDOSE + measurement đã có staging evidence; slice coverage policy và fenced dispatch đã có local code/test | Semantic/scientific independent oracle, lease/outbox failure injection, bounded retry/resource limits và large workload chưa được coi là hoàn tất. |
| P9 | Có implementation slice backend/frontend và local tests cho template, revision, block, snapshot, renderer, export và idempotency; authenticated browser smoke đã tạo revision và tải JSON/CSV/PDF/PNG trên staging | Recheck trên candidate mới; storage failure/retry, visual byte review và build manifest vẫn là gate riêng. |
| P10 | Có implementation slice backend/frontend, migration `20260908_0010`, test scope/error/rebuild/event/export và trend UI | Basic staging smoke đã có; large-series budget, complete negative matrix, source/export revalidation và visual/accessibility evidence còn phải làm. |
| P11 | Có implementation slice backend/frontend, migration `20260908_0011`, protocol lifecycle/validation/compare và active-only consumer | Staging migration/browser/consumer E2E, complete S/E/C evidence và release manifest còn phải làm. |
| P12 | Có implementation slice và staging browser evidence mới; release/report integration còn mở | Đối soát PostgreSQL state, refresh/reconnect, negative matrix và P9 Biological report integration trước `STAGING_VERIFIED`. |
| P13 | Có implementation slice local: migration `20260908_0013`, engine/API/UI, known-answer/API tests; staging chưa kiểm trên candidate này | Deploy đúng SHA, chạy browser validate→calculate/replay→chart preview→export, đối chiếu DB snapshot/checksum và cập nhật manifest. |
| P14–P17 | Chưa có evidence triển khai module đầy đủ | Thực hiện các gói công việc bên dưới. |
| P18–P20 | Chưa có evidence integrated release/operations đầy đủ | Không đóng bằng việc Railway báo Online hoặc /health trả 200. |

Các smoke run lịch sử giữ tại progress log: Gamma 2D `e084529d-6bb1-4119-ae0a-f4da7d371cac`; failure/retry `26a54046-1f20-454c-b3f4-e766937f30d6`. Đây là evidence đã ghi, không phải kết quả được chạy lại ngày sửa tài liệu.

### 1.3. Gap cụ thể thấy từ source ngày 2026-09-08

| Gap | Bằng chứng source hiện tại | Phase chịu trách nhiệm | Điều kiện đóng | Trạng thái sau kiểm tra 2026-09-08 |
| :--- | :--- | :--- | :--- | :--- |
| GAP-01: PSQA chưa bắt RTDOSE rõ theo profile | `gamma.py` đã có `workflow_profile`; PSQA kiểm reference RTDOSE và ENGINE_TEST được gắn nhãn riêng. | P8 | PSQA thiếu RTDOSE bị chặn, JSON-only kiểm thử có nhãn và namespace rõ. | `STAGING_VERIFIED` cho workflow PSQA 3D trên release `e71e8e1`; negative/profile cases vẫn phải giữ trong regression. |
| GAP-02: JSON khai báo DICOM vẫn được đọc như measurement | `artifact_validation.py::validate_artifact` hiện dùng declared type làm authority và trả `ARTIFACT_TYPE_MISMATCH` khi content sai. | P6 | Type/content mismatch có kết quả riêng, không tuyên bố DICOM VALID. | `LOCAL_VERIFIED`; cần revalidate sau deploy. |
| GAP-03: Gamma bỏ NO_CANDIDATE khỏi mẫu số | `calculate_gamma` có `FULL_ROI`/`OVERLAP_ONLY`, counts coverage và không loại điểm thiếu candidate khỏi FULL_ROI; independent oracle enumerates all comparison nodes. | P8 | Policy coverage/no-candidate theo specification §5; test chứng minh không tăng PASS giả. | `LOCAL_VERIFIED`; staging negative coverage/convergence còn mở. |
| GAP-04: Search giới hạn 1×DTA nhưng vẫn xuất percentile gamma | `_candidate_gammas` dùng `max_gamma × DTA`; điểm vượt bound được đánh dấu censored và percentile không giả exact; oracle kiểm tra denominator/status. | P8 | Full gamma search theo max_gamma hoặc output bound có nhãn; percentile không giả exact. | `LOCAL_VERIFIED`; benchmark large workload còn mở. |
| GAP-05: Lease/attempt/outbox chưa đủ hợp đồng v2 | Models/migration/API/worker đã có lease token, attempt history, dispatch outbox, conditional fencing, bounded retry, backoff và lease-expiry reclaim. | P8 | Hai worker/reclaim/commit/ack failure injection không duplicate hoặc mất accepted job. | `LOCAL_VERIFIED` cho race/reclaim/retry/replay; staging crash/ack/dead-letter/resource policy còn mở. |
| GAP-06: /ready chỉ kiểm DB connection | `db/session.py::database_ready` hiện kiểm `SELECT 1` và đối chiếu đúng một dòng `alembic_version` với `Settings.schema_revision`. | P2/P19 | Có kiểm schema revision riêng hoặc readiness mở rộng; không nói SELECT 1 xác minh migration. | `LOCAL_VERIFIED`; cần staging evidence với schema hiện hành `20260908_0013`. |
| GAP-07: Fixture RTDOSE sử dụng CGY và SOP Class tham chiếu ngẫu nhiên | Fixture generator đã chuyển sang GY + `DoseGridScaling=0.01`, RTPlanStorage SOP Class và UID ổn định; fixture tái tạo byte-identical. | P6/P8 | Tạo fixture chuẩn GY + DoseGridScaling tương ứng, RTPlanStorage SOP Class đúng; CGY raw fixture chỉ compatibility/negative test. | `STAGING_VERIFIED` cho fixture RTDOSE GY + measurement 3D trên run `df38e7d5-bb4b-4e2b-b949-2310acb1875c`; geometry/scale negative cases còn mở. |
| GAP-08: Old error example khác API thật | `core/errors.py`, `specification.md` và technical contract đang được đồng bộ về flat envelope. | P0/P1 | Tài liệu và consumer tests cùng schema flat, không còn ví dụ nested gây hiểu sai. | `DOC_SYNCED`; vẫn giữ contract test chống hồi quy. |
| GAP-09: Build label không chứng minh source deployed | VITE build label và deployment SHA vẫn là hai nguồn; chưa có release manifest bắt buộc nối chúng. | P3/P19 | Hiển thị build metadata đúng artifact và ghi SHA của từng service. | `OPEN`. |

Các trạng thái trên chỉ là checkpoint, không phải đóng phase. `LOCAL_VERIFIED` nghĩa là có code và test local tương ứng; chỉ `STAGING_VERIFIED` mới chứng minh luồng browser → API → database/object storage → worker → result trên release đang chạy. GAP-06/GAP-09 và phần staging/oracle/benchmark của P8 vẫn chặn DONE-v2.

### 1.4. Checkpoint implementation sau slice P6/P8/P9/P10/P11

- Backend: full suite **81/81 PASS** và test riêng P11 `test_protocol_library.py` **3/3 PASS** ngày 2026-09-08 trên working tree hiện tại; Ruff và strict mypy PASS. Đây là local evidence, chưa phải staging/production clinical readiness.
- Gamma-focused contract: `test_gamma.py` 8/8, `test_gamma_dicom.py` 3/3, `test_gamma_worker.py` 6/6 và `test_gamma_independent_oracle.py` 3/3 PASS; bao gồm declared-type mismatch, RTDOSE GY scaling, PSQA preflight, resource limit, coverage/no-candidate, censoring, single-holder lease, bounded retry và replay sau commit trước ack.
- Frontend: lint, typecheck, Vitest **1/1** và production build PASS; build chỉ còn cảnh báo bundle JavaScript >500 kB, không phải lỗi functional.
- P9 report slice: `test_reports.py` **4/4 PASS**; template/version, organization-scoped source snapshot, full block customization, optimistic revision conflict, dangerous-content validation, deterministic JSON/CSV/PDF/PNG export, warning snapshot và export idempotency đã được kiểm local. Migration `20260908_0009` đã upgrade thành công trên local PostgreSQL; authenticated staging browser đã tạo report revision và tải đủ bốn định dạng trên candidate P9.
- P10 trend slice: migration `20260908_0010` đã upgrade thành công trên local PostgreSQL; `TrendPoint` có context snapshot, uniqueness theo organization/source run/metric và index theo thời gian. Baseline version, maintenance event/revision, raw/day/week query, compatibility signature, outlier, rebuild idempotency, export và source drill-down đã có API/UI; P10 test riêng **7/7 PASS**.
- P11 protocol slice: migration `20260908_0011` đã ở head trên local PostgreSQL; `QAProtocolVersion`/`QAProtocolRule` có source, applicability, lineage, revision và rule reference. Validate-only, create/edit/activate/archive, clone deep-copy, compare, organization scope và Machine QA active-only selection đã được kiểm trong `test_protocol_library.py` **3/3 PASS**; staging browser/consumer snapshot và complete S/E/C evidence còn mở.
- Fixture: `gamma-rtdose-v1-smoke.dcm` được sinh lại hai lần với cùng SHA-256 `CA5C9168EB9B045E30A375EDC6B76118EFD754A35815C2860B17CA8944C4480B`.
- Staging slice mới đã chạy qua web/API/object storage/Redis worker: web deployment `7f104141-0fe4-4527-b455-a503beaceb20` từ commit `e71e8e1` thành công; run `df38e7d5-bb4b-4e2b-b949-2310acb1875c` dùng PSQA_GAMMA, RTDOSE GY reference + measurement 3D evaluation, cấu hình `3D · FULL_ROI · max γ 2`, đạt `COMPLETED/PASS`, 8/8 evaluated/passing, 0 excluded, coverage `1`, Gamma P95 `0`, attempt 1. Sau reload browser, run và config snapshot vẫn hiển thị đúng; đây là evidence cho staging 3D happy path, không đóng các gate oracle/failure/resource còn lại. P9 chưa có staging evidence trên schema `20260908_0009` ở thời điểm ghi tài liệu.

## 2. Dependency, release và cách chia task

| Release | Nội dung | Phase bắt buộc |
| :--- | :--- | :--- |
| R0 | Runtime, staging, Auth, app shell | P0–P3 |
| R1 | QA archive, Machine QA, PSQA, report, trend, QA protocol | P4–P11 |
| R2 | Biological Toolkit và knowledge | P12–P16 |
| R3 | Visual Dose/DVH | P17 |
| R4 | Integrated pilot, production, gói vận hành | P18–P20 |

P7 có protocol seed tối thiểu versioned; không chờ P11 để làm rule engine. P11 hoàn thiện quản trị library. P9 có thể làm block cơ bản từ P7, nhưng Gamma block/exit P9 cần P8. P12 cần report shell P9 và Auth P3; làm độc lập khi P8 chờ dataset không đồng nghĩa bỏ exit P8. P17 tùy chọn cho R1 sớm, bắt buộc trong mục tiêu hoàn thiện toàn dự án. P18 full-release cần R1+R2+R3.

Mỗi phase có bốn work package W01–W04. Có thể chia nhỏ package thành issue, nhưng mọi issue phải giữ phase/FR/contract/test reference. Không ước lượng ngày như cam kết khi chưa phân rã, đo tốc độ thực và đánh giá gap. Sau mỗi package, cập nhật remaining tasks; sau mỗi phase, tính lại thời lượng/cost dựa trên evidence.

## 3. Ma trận kiểm thử chung bắt buộc

Mỗi phase ghi test cụ thể S/E bên dưới và áp dụng các nhóm C phù hợp. Trường hợp không áp dụng cần ghi lý do ở evidence. Các biến thể biên phải dùng fixture có expected result độc lập.

| ID | Given / Khi thử | Then / Điều kiện đạt |
| :--- | :--- | :--- |
| C01 | Payload hợp lệ và required field thiếu, null, empty, whitespace | Valid được nhận; invalid trả field errors, không mất input và không commit một phần. |
| C02 | Số 0, âm, min−epsilon, min, max, max+epsilon, NaN/Infinity | Boundary/unit policy nhất quán frontend/backend/engine; không tự clamp dữ liệu người dùng. |
| C03 | UUID sai format, không tồn tại, khác organization, archived | 422/404/409 đúng nghĩa; không lộ record ngoài scope; archived history vẫn theo contract. |
| C04 | Double click, retry request sau commit nhưng trước response, key trùng khác payload | Một mutation/result; conflict khi payload khác cùng key. |
| C05 | Hai tab/user sửa cùng revision | Một commit thắng, phía còn lại thấy conflict và giữ draft. |
| C06 | Offline trước gửi, giữa upload, sau accepted job, khi download | Trạng thái hữu hạn, retry đúng thao tác; không tạo job/file trùng hoặc success giả. |
| C07 | Session hết hạn/đổi user trong lúc request đang trả về | Cache/request cũ không được render sang identity mới; bootstrap đúng context. |
| C08 | Timeout/429/5xx/response sai schema | Retry bounded; tôn trọng Retry-After; có correlation ID và nút phục hồi. |
| C09 | Đổi tên/move/archive/source/template/protocol/model sau khi có result | Old revision giữ nguồn và số liệu; rerun/version mới có identity riêng. |
| C10 | Empty, loading, populated, warning, error, pending; keyboard/mobile/long Vietnamese text | UI sử dụng được, focus hợp lý, không chỉ dùng màu; không kẹt spinner. |
| C11 | Page size 1/max/vượt max; sort tie; ngày/tháng/năm/timezone; search dấu tiếng Việt | Kết quả stable theo quy tắc, không trộn dữ liệu, filter/export khớp. |
| C12 | Restart DB/API/Redis/storage/worker/renderer trước và sau commit | Không lost accepted operation hoặc duplicate terminal result; lịch sử attempt phản ánh lỗi. |
| C13 | Export cùng revision/options và source file thiếu/hỏng | File đúng revision/hash hoặc fail có reason; không sửa source analysis. |
| C14 | Payload lớn/queue burst/chart nhiều điểm/nhiều bảng | Đạt workload budget hoặc fail limit có chủ đích, không OOM làm chết cả API. |
| C15 | Dữ liệu/secret trong logs, URL, error, public bundle và telemetry | Không lộ credential; dùng synthetic fixture và nội dung diagnostic tối thiểu. |
| C16 | Deployment web/API/worker lệch phiên bản, config build/runtime lệch | Detect incompatibility; không coi health 200 là toàn bộ E2E pass. |

### 3.1. Fixture và evidence contract

Fixture tối thiểu: hai organization A/B; hai thành viên A ngang quyền và một thành viên B; một identity chưa membership và một inactive membership; site/machine active/archived; folder 3 cấp; case rỗng/có file; protocol v1/v2; artifact valid/invalid/duplicate; source checksum; các dataset số học tại specification §5–§7. Không dùng password/token trong fixture tracked.

Mỗi testcase phải lưu: ID, FR liên quan, contract section, setup/data hash, thao tác cụ thể, expected, observed, PASS/FAIL, environment, service SHA, schema/engine/renderer version, timestamp, evidence path/run/request ID và cleanup. Screenshot là evidence UI, không thay query/assertion về checksum hoặc persistence.

Test S dưới mỗi phase dùng precondition: dependency đạt và fixture hợp lệ thuộc A; actor là thành viên A. Test E thay đúng điều kiện lỗi ghi ở cột trigger, giữ điều kiện khác hợp lệ. Với phase hạ tầng dùng environment staging/local được định danh. “Expected” là assertion, không phải kết quả đã đo.

### 3.2. Ma trận điều khiển thực thi P0–P20

Bảng này là bản đồ điều hành một trang. Các bảng `TC-Pxx-Syy` và `TC-Pxx-Eyy` ở từng phase là danh sách kiểm tra chi tiết bắt buộc; không được dùng bảng này để bỏ qua một testcase. Với mỗi dòng, thực hiện theo thứ tự **entry gate → workflow chuẩn → success cases → error/recovery cases → invariant → evidence → exit decision**. Nếu một lỗi thuộc nhiều phase, ghi nó ở phase sở hữu nguyên nhân và link sang phase phát hiện.

| Phase | Entry/dependency | Workflow chuẩn và trường hợp chạy đúng | Trường hợp lỗi phải kích hoạt và cách phục hồi | Bằng chứng bắt buộc và điều kiện chặn exit |
| :--- | :--- | :--- | :--- | :--- |
| P0 | Yêu cầu, source, design và evidence hiện có | Lập registry FR/MOD/P/contract/test; đối soát requirement với code và ghi gap | `DOCUMENT_CONFLICT`, `DESIGN_REFERENCE_STALE`, `EVIDENCE_MISSING`, `ENVIRONMENT_MISMATCH`; dừng baseline sai, không xóa lịch sử | Registry không orphan/trùng, quyết định phạm vi, evidence index; mọi mâu thuẫn chưa quyết định chặn P0 |
| P1 | Repository và lockfile | Clean setup → runtime → Compose services → migration/seed → health/build/test | `DEPENDENCY_MISMATCH`, `PORT_IN_USE`, `MIGRATION_FAILED`, `CONFIGURATION_MISSING`, `BUILD_CONTRACT_FAILED`; sửa đúng layer và chạy lại từ checkpoint | Log clean setup, schema head, test/build output; migration hoặc CI không reproducible chặn mọi phase sau |
| P2 | Railway project/service và Auth/DB config | Deploy API/worker đúng source → pre-deploy migration → readiness/schema → JWT smoke | `BUILD_SOURCE_INVALID`, `DATABASE_DRIVER_MISMATCH`, `SERVICE_NOT_LISTENING`, `SCHEMA_NOT_READY`, `AUTH_VERIFICATION_FAILED`, `DEPLOYMENT_CONFIG_DRIFT`; không coi process Online là đủ | Service/environment/SHA/DB/schema/Auth manifest redacted; `health` và `ready` phải tách biệt, schema mismatch chặn |
| P3 | API/Auth nền tảng đạt | Deep-link → session bootstrap → membership/onboarding → dashboard → logout/expiry | `SIGN_IN_FAILED`, `RECOVERY_LINK_INVALID`, `SESSION_UNAVAILABLE`, `ORGANIZATION_MEMBERSHIP_REQUIRED`, `AUTH_CONFIGURATION_MISSING`, `WORKSPACE_LOAD_FAILED`; retry bounded, không cache nhầm identity | Browser evidence của first-use, existing member, expiry, offline, deep-link; lỗi bootstrap hoặc route blank chặn |
| P4 | Organization context hợp lệ | Tạo site/machine → rename/archive/restore → invitation → xem history; mọi thành viên dùng cùng nghiệp vụ | `MACHINE_CODE_CONFLICT`, `PARENT_NOT_AVAILABLE`, `REVISION_CONFLICT`, `INVITATION_INVALID`, `LAST_MEMBERSHIP_CONFLICT`, `MUTATION_RESULT_UNKNOWN`; kiểm result trước retry | DB/query scope, stable ID, concurrent edit và invitation evidence; cross-org leak hoặc mutation trùng chặn |
| P5 | Site/machine và archive shell | Tạo folder lồng nhau → tạo case → search/filter/page → move/rename/archive/restore | `FOLDER_CYCLE`, `FOLDER_NAME_CONFLICT`, `PARENT_NOT_AVAILABLE`, `CASE_HIERARCHY_INVALID`, `PAGE_OUT_OF_RANGE`, `RESTORE_CONFLICT`; giữ cây/case cũ khi fail | Tree trước/sau, combined filters, deep-link, archived restore; mất lineage hoặc partial move chặn |
| P6 | Case và object storage | Chọn type/role → upload → checksum/object commit → manifest → validation → download | `FILE_REQUIRED_OR_EMPTY`, `UPLOAD_TOO_LARGE`, `UPLOAD_INTERRUPTED`, `ARTIFACT_PERSISTENCE_FAILED`, `ARTIFACT_TYPE_MISMATCH`, `INPUT_METADATA_INVALID`, `DOWNLOAD_LINK_EXPIRED`; reconcile object/DB và retry có kiểm | Hash round-trip, DICOM UID/geometry/unit, valid/invalid/duplicate/type mismatch, signed download; artifact mồ côi hoặc validate giả chặn |
| P7 | Protocol seed và case input | Chọn protocol version → draft metric → evaluate snapshot → result → rerun/compare/trend | `MEASUREMENT_REQUIRED`, `MEASUREMENT_INVALID`, `BASELINE_ZERO`, `REVISION_CONFLICT`, `DUPLICATE_OPERATION`, `PROTOCOL_NOT_AVAILABLE`; giữ draft, tạo rerun/version mới | Boundary known-answer, N/A reason, immutable result, projection uniqueness; PASS sai hoặc overwrite chặn |
| P8 | Validated artifacts, Redis, worker và schema | Preflight profile → enqueue idempotent → lease/heartbeat → compute → durable result → ack → compare/retry | `RTDOSE_REQUIRED_OR_COMPARISON_REQUIRED`, `GAMMA_INPUT_INCOMPATIBLE`, `GAMMA_CONFIG_UNSUPPORTED`, `GAMMA_NO_EVALUATED_POINTS`, `GAMMA_LOCAL_ZERO_REFERENCE`, `GAMMA_DISPATCH_UNAVAILABLE`, `GAMMA_EXECUTION_INTERRUPTED`, `GAMMA_DICOM_UNSUPPORTED`, `GAMMA_RESOURCE_LIMIT`, `GAMMA_SOURCE_CHANGED`; outbox/reclaim/fencing/bounded retry | Independent oracle, 2D/3D, FULL_ROI/OVERLAP_ONLY, censoring, crash/ack/retry/dead-letter, resource benchmark, staging evidence; denominator/source/duplicate sai chặn |
| P9 | P7/P8 contracts và schema `20260908_0009` | Chọn source/template → edit mọi block → snapshot revision → preview → export → reload/history/download | `REPORT_REVISION_CONFLICT`, `REPORT_SOURCE_UNAVAILABLE`, `REPORT_CONTENT_INVALID`, `REPORT_RENDER_FAILED`, `EXPORT_FORMAT_UNSUPPORTED`, `DOWNLOAD_LINK_EXPIRED`, cùng storage/idempotency conflict; giữ revision cũ, retry export | 4 format, UTF-8/PDF warning, hash/idempotency, browser storage download, visual review; source live làm đổi revision cũ chặn |
| P10 | P7 results và P9 report source | Chọn machine/metric/time → compatible series → baseline/markers → drill-down/export | `TREND_SERIES_INCOMPATIBLE`, `DATE_RANGE_INVALID`, `TREND_EMPTY`, `TREND_BASELINE_INVALID`, `TREND_DUPLICATE_SOURCE`, `TREND_SOURCE_ARCHIVED`; tách series và rebuild projection | Raw/aggregate equality, timezone, extrema, maintenance marker, source link; trộn unit/machine hoặc mất raw chặn |
| P11 | P7 protocol use và P9 source; migration `20260908_0011` | Resolve org → search/detail → new/clone → validate-only → save DRAFT → activate → consumer snapshot → compare/archive | `REQUEST_VALIDATION_FAILED`, `PROTOCOL_APPLICABILITY_INVALID`, `PROTOCOL_RULE_INVALID`, `PROTOCOL_VERSION_CONFLICT`, `REFERENCE_REQUIRED`, `PROTOCOL_VERSION_IMMUTABLE`, `PROTOCOL_NOT_AVAILABLE`, `PROTOCOL_CAPABILITY_MISMATCH`, `PROTOCOL_NOT_FOUND`, `PROTOCOL_PERSISTENCE_FAILED`, `MUTATION_RESULT_UNKNOWN`; giữ draft và query trước retry | Version/rule/reference lineage, active-only consumer, old-result snapshot, no cross-org leak; rule mơ hồ, update ngược hoặc partial transaction chặn |
| P12 | Auth/org và report shell | Mở Biological Hub → chọn tool → nhập scenario độc lập → save revision → history/clone/export | `SCENARIO_NOT_FOUND`, `BIOLOGICAL_CONTEXT_INVALID`, `SCENARIO_REVISION_CONFLICT`, `MODEL_VERSION_UNAVAILABLE`, `MODULE_UNAVAILABLE`; giữ scenario, nêu capability rõ | Không cần QA case/patient; scoped history, independent report; P13 available và P14–P16 planned đúng capability; automatic QA linkage hoặc route giả chặn |
| P13 | P12 scenario contract và known-answer set | Chọn SAVED revision → nhập D/n/d/alpha-beta → validate-only → BED/EQD2 → curve D → table/marker → save/replay/export/history | `BIOLOGICAL_INPUT_INVALID`, `FRACTIONATION_INCONSISTENT`, `CALCULATION_NONFINITE`, `CURVE_RANGE_INVALID`, `ALPHA_BETA_SOURCE_REQUIRED`, `CALCULATION_IDEMPOTENCY_CONFLICT`, `CALCULATION_PERSISTENCE_FAILED`, `SCENARIO_REVISION_NOT_FOUND`, `SCENARIO_IMMUTABLE`; sửa input/model, query idempotency trước retry, không clamp ngầm | Known answers, pair derivation/zero dose, unit/precision, curve equality, source/override, immutable snapshot, idempotency/persistence; số không finite hoặc mismatch chặn |
| P14 | P13 calculation engine | Tạo 2–10 options → chọn baseline → calculate deltas → chart/table → reorder/clone/export | `COMPARISON_OPTIONS_REQUIRED`, `COMPARISON_PERCENT_UNDEFINED`, `COMPARISON_OPTION_INVALID`, `COMPARISON_CONTEXT_MISMATCH`, `COMPARISON_BASELINE_REQUIRED`, `COMPARISON_LIMIT_EXCEEDED`; giữ option hợp lệ và % null khi không xác định | Same revision/context, absolute/% delta, baseline changes, history/export; ghép khác mô hình hoặc truncate im lặng chặn |
| P15 | P13/P14 và model assumptions | Chọn course/time/dose/fractions → recovery/no-recovery → cumulative scalar → sensitivity → compensation scenario/export | `COURSE_INTERVAL_REQUIRED`, `RECOVERY_ASSUMPTION_INVALID`, `CUMULATIVE_CONTEXT_MISMATCH`, `FRACTION_SCHEDULE_INVALID`, `SPATIAL_ACCUMULATION_UNAVAILABLE`, `TISSUE_DOSE_REQUIRED`, `INTERRUPTION_OVERLAP`, `FRACTION_COUNT_NONINTEGER`; tách scalar/spatial, không kê đơn tự động | Timeline, assumptions, nonuniform schedule, no-recovery comparator, integer alternatives; spatial giả lập hoặc thiếu OAR dose chặn |
| P16 | P12/P13 library contract | Search/filter source → create/clone/version dose-limit/protocol/knowledge → cite/import → dùng explicit trong scenario | `KNOWLEDGE_SOURCE_REQUIRED`, `DOSE_LIMIT_UNIT_INVALID`, `REFERENCE_LINK_UNAVAILABLE`, `KNOWLEDGE_IMPORT_INVALID`, `DOSE_LIMIT_NOT_APPLICABLE`, `KNOWLEDGE_CONTENT_INVALID`; row-level preview, version mới, giữ citation | Source/applicability/version snapshots, import report, override label; nguồn giả hoặc auto PASS/FAIL chặn |
| P17 | P6/P8/P9 và DICOM geometry | Chọn dose/structure/image → validate Frame/ROI → overlay/DVH/profile → review/export | `DVH_INPUT_REQUIRED`, `DICOM_FRAME_MISMATCH`, `DVH_EMPTY_STRUCTURE`, `DVH_INCOMPLETE_COVERAGE`, `CONTOUR_GEOMETRY_INVALID`, `DICOM_CAPABILITY_UNSUPPORTED`, `ANATOMY_INPUT_REQUIRED`; dose-only fallback có nhãn | Geometry/ROI coverage, known DVH, visual/table fallback, source links; overlay sai frame hoặc dose ngoài grid chặn |
| P18 | R1–R3 candidate và pilot dataset | Clean release → integration matrix → failure injection/load → restore → pilot feedback → regression | `RESULT_REGRESSION`, `RESTORE_INCOMPLETE`, `DUPLICATE_RESULT`, `PERFORMANCE_GATE_FAILED`, `PILOT_CAPABILITY_GAP`, `RELEASE_EVIDENCE_MISMATCH`; giữ candidate, issue + regression, không sửa expected | Full candidate matrix, measurements/latency, restore, pilot issue log và exact SHA; bất kỳ SEV0/1 hoặc evidence lệch SHA chặn |
| P19 | Candidate đã qua P18 và backup point | Promote API/web/worker/schema → domain/TLS/CORS/Auth → remote E2E → rollback rehearsal | `PUBLIC_DOMAIN_NOT_READY`, `PUBLIC_BUILD_CONFIG_MISMATCH`, `RELEASE_SCHEMA_FAILED`, `RELEASE_VERSION_MISMATCH`, `REMOTE_E2E_FAILED`, `RESOURCE_BUDGET_EXCEEDED`; giữ last-good/rollback theo runbook | Public HTTPS, service SHA/schema/engine manifest, remote workflow, backup/rollback; health-only hoặc service lệch version chặn |
| P20 | P19 release và owner vận hành | Monitor → alert test → backup/restore drill → runbook → incident/release regression loop | `BACKUP_POLICY_FAILED`, `ALERT_DELIVERY_FAILED`, `CAPACITY_WARNING`, `ENGINE_RESULT_CHANGED`, `RECURRING_INCIDENT`; alert owner, last-good backup, version mới và regression | Alert nhận được, restore evidence, threshold/cost/capacity, runbook và owner; không có backup/restore/alert thực chặn initial package |

Quy tắc quyết định: `PASS` của một success case chỉ đóng assertion đó; mọi error case chưa chạy là `NOT_RUN`, không phải PASS ngầm. Một phase chỉ chuyển `DONE-v2` khi tất cả MUST case, invariant, dependency và evidence của chính phase đạt; nếu code đã có nhưng staging/oracle/benchmark còn thiếu, dùng `LOCAL_VERIFIED` hoặc `NEEDS_REVALIDATION`.

### 3.3. Definition of Ready/Done và thứ tự quyết định cho một phase

Để tránh việc phase bị coi là xong chỉ vì một màn hình hoặc một endpoint chạy được, mỗi phase
phải có hai bộ điều kiện độc lập:

| Bộ điều kiện | Phải trả lời được trước khi chạy | Không đạt thì xử lý |
| :--- | :--- | :--- |
| Definition of Ready | Dependency nào đã sẵn sàng; source SHA/document version nào; schema/environment/fixture nào; workflow và expected output nào; dữ liệu synthetic nào được phép dùng | Chuyển `BLOCKED` hoặc `IN_PROGRESS`, ghi thiếu dependency; không chạy test như thể phase đã ready |
| Definition of Implementation | W01–W04 có code/config/migration/UI/engine artifact và unit/contract test tương ứng; error mapping và rollback đã mô tả | Mở issue theo package; không đánh dấu package chỉ từ compile/build |
| Definition of Verification | S/E/boundary/regression đã chạy; integration path đã đi qua các thành phần liên quan; database/object/queue/result state và UI/provenance đều được đối chiếu | Giữ `LOCAL_VERIFIED`/`NEEDS_REVALIDATION`; test chỉ HTTP không được nâng thành E2E |
| Definition of Staging | Đúng environment, SHA, schema, Auth, private dependency, browser và dữ liệu; output sau refresh/reconnect khớp | Chạy lại trên candidate đúng hoặc rollback; không kết luận từ Railway Online/health 200 |
| Definition of Done-v2 | Không còn MUST test `NOT_RUN`, không có SEV0/SEV1, invariant và evidence đủ, handoff/backlog/next action cập nhật | Phase còn mở; requirement không được nới hoặc expected không được sửa để ép PASS |

Thứ tự đóng phase bắt buộc là:

```text
ENTRY → IMPLEMENT → LOCAL S/E/C → INTEGRATION → STAGING (nếu áp dụng)
      → EVIDENCE REVIEW → EXIT DECISION → HANDOFF
```

Mỗi phase phải phân biệt ít nhất bốn loại output: **valid success**, **valid result with warning**,
**rejected input**, và **dependency/state failure**. Với job bất đồng bộ, phải thêm
`accepted/queued/running/retrying/completed/failed`; với library/revision phải thêm
`draft/active/archived` hoặc vòng đời tương ứng. Việc một testcase chưa áp dụng chỉ hợp lệ khi
phase packet ghi lý do, không có dependency che giấu và người review xác nhận.

Phase packet phải trả lời năm câu hỏi bàn giao: (1) người dùng bắt đầu từ route hoặc command nào,
(2) input/source nào được pin, (3) output nào được coi là thành công, (4) mỗi lỗi phục hồi bằng
thao tác nào, và (5) bằng chứng nằm ở đâu. Nếu không trả lời đủ năm câu hỏi, `HANDOFF` không đạt.

## 4. Phase contracts

<a id="phase-0"></a>

## P0 — Baseline, phạm vi và truy vết

- **Module:** MOD-00–MOD-16.
- **Requirement:** FR-P00-01 đến FR-P00-04, xem business-analysis §21.3.
- **Dependency/entry gate:** Baseline yêu cầu user có trong repository. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Một baseline tài liệu thống nhất, mọi yêu cầu có phase và tiêu chí kiểm chứng.
- **Contract:** specification §8 / SPEC-P00; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P0

1. Đọc nghiệp vụ và các quyết định đã thống nhất.
2. Đối chiếu source, route, migration, test và evidence cũ.
3. Gắn requirement vào module, phase và test case.
4. Ghi khác biệt giữa requirement và code thành gap có owner.
5. Khóa baseline tài liệu và chọn gói công việc chưa đạt đầu tiên.

### Work packages P0

- [ ] P00-W01 — Lập registry FR → P → S/E → evidence; kiểm tra không có mã trùng hoặc orphan.
- [ ] P00-W02 — Đối chiếu API thật với đề xuất; ghi gap RTDOSE, job concurrency, report và Biological.
- [ ] P00-W03 — Đọc screen registry; kiểm tra screen còn hoạt động khi bắt đầu làm UI tương ứng.
- [ ] P00-W04 — Định nghĩa template evidence, checkpoint và quy tắc mở lại phase khi phát hiện gap.
- [ ] P00-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P00-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P0

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P00-S01 | Baseline khớp | Mỗi FR có phase, contract và ít nhất một test thành công/lỗi; link nguồn tồn tại. |
| TC-P00-S02 | Tiếp tục sau gián đoạn | Đọc checkpoint xác định được task tiếp theo, commit và evidence thiếu mà không làm lại bước đã đạt. |
| TC-P00-S03 | Thêm requirement | Requirement mới có ID, dependency và acceptance; không đổi lịch sử PASS. |

### Trường hợp lỗi và phục hồi P0

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P00-E01 | Tài liệu mâu thuẫn | DOCUMENT_CONFLICT | Ghi quyết định giải quyết theo ý định user; đồng bộ các nguồn trước khi đóng P0. |
| TC-P00-E02 | Screen đã xóa/hidden | DESIGN_REFERENCE_STALE | Giữ design gap; không khôi phục screen legacy. |
| TC-P00-E03 | Test không có evidence | EVIDENCE_MISSING | Giữ NOT_RUN, không đánh dấu PASS từ lời mô tả. |
| TC-P00-E04 | Sai project hoặc environment | ENVIRONMENT_MISMATCH | Dừng thao tác triển khai; đọc ID và lập lại inventory đúng. |

### Bất biến và điều kiện đóng P0

- **Dữ liệu phải giữ/transaction:** Bản cập nhật tài liệu có version chung; không ghi secret vào evidence.
- **Bàn giao:** Bộ ba tài liệu, registry và gap list; bản plan trước được lưu lịch sử.
- **Exit gate:** 100% FR trong catalogue được gán phase/test; không còn xung đột phạm vi chưa có quyết định.
- **Kiểm tra chéo:** Registry/build consistency và ma trận C áp dụng.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-1"></a>

## P1 — Runtime local, repository và CI

- **Module:** MOD-16.
- **Requirement:** FR-P01-01 đến FR-P01-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P0 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Clone sạch có thể build, migrate, chạy và kiểm thử theo hướng dẫn.
- **Contract:** specification §8 / SPEC-P01; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P1

1. Chuẩn bị runtime theo lockfile.
2. Khởi động PostgreSQL, Redis và object storage local.
3. Chạy migration và seed synthetic.
4. Build web/API; kiểm tra health và route.
5. Chạy CI trên commit tương ứng, lưu kết quả và hướng dẫn khởi động.

### Work packages P1

- [ ] P01-W01 — Kiểm tra manifests, Compose, Dockerfile và README trên checkout sạch.
- [ ] P01-W02 — Thống nhất cấu hình, error envelope và version metadata.
- [ ] P01-W03 — Kiểm tra migration từ DB rỗng và DB revision trước; không dùng downgrade phá dữ liệu làm mặc định.
- [ ] P01-W04 — CI chạy backend/frontend contracts, build, migration/OpenAPI consistency và secret scan.
- [ ] P01-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P01-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P1

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P01-S01 | Clean setup | Các service cần thiết sẵn sàng, API/web truy cập được theo README. |
| TC-P01-S02 | Restart local | Dữ liệu đã lưu còn nguyên sau restart; không sinh seed trùng. |
| TC-P01-S03 | CI commit hợp lệ | Mọi job bắt buộc xanh trên đúng SHA; artifacts có version. |

### Trường hợp lỗi và phục hồi P1

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P01-E01 | Thiếu dependency/lockfile lệch | DEPENDENCY_MISMATCH | Báo runtime/dependency thiếu; cài từ lockfile, không sửa version ngẫu nhiên. |
| TC-P01-E02 | Cổng đã dùng | PORT_IN_USE | Chỉ rõ cổng; chọn cổng cấu hình hoặc dùng service đúng đang chạy. |
| TC-P01-E03 | Migration lỗi | MIGRATION_FAILED | Giữ log revision; không đánh dấu ready; sửa migration và chạy lại. |
| TC-P01-E04 | Thiếu biến môi trường | CONFIGURATION_MISSING | Fail có tên biến thiếu, không in giá trị secret. |
| TC-P01-E05 | Web build hoặc OpenAPI lệch | BUILD_CONTRACT_FAILED | CI chặn artifact release đến khi contract đồng bộ. |

### Bất biến và điều kiện đóng P1

- **Dữ liệu phải giữ/transaction:** Startup không tự seed production; migration thất bại không bị bỏ qua.
- **Bàn giao:** Setup README, Compose, CI jobs và artifact build.
- **Exit gate:** Clean setup và restart pass; CI bắt buộc xanh; migration DB rỗng/upgrade có evidence.
- **Kiểm tra chéo:** Registry/build consistency và ma trận C áp dụng.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-2"></a>

## P2 — Railway staging, PostgreSQL và nền tảng Supabase Auth

- **Module:** MOD-00, MOD-16.
- **Requirement:** FR-P02-01 đến FR-P02-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P1 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** API staging, database và xác minh identity hoạt động với cấu hình đúng môi trường.
- **Contract:** specification §8 / SPEC-P02; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P2

1. Đối chiếu service ID và môi trường.
2. Cấu hình DB reference, PORT và Auth staging.
3. Build đúng source; chạy pre-deploy migration.
4. Xác nhận liveness, DB connectivity và schema revision riêng.
5. Dùng token staging kiểm tra API; lưu deployment manifest không secret.

### Work packages P2

- [ ] P02-W01 — Kiểm tra API/web/worker source độc lập, effective settings và commit deploy.
- [ ] P02-W02 — Chuẩn hóa DATABASE_URL ở runtime và Alembic; kiểm thử credential có ký tự percent được URL-encode.
- [ ] P02-W03 — Xác minh JWT signature/issuer/audience/expiry và JWKS refresh có timeout.
- [ ] P02-W04 — Ghi private dependency map, health/ready/schema checks và usage thực tế nếu truy cập được.
- [ ] P02-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P02-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P2

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P02-S01 | Migration với hai scheme | postgresql:// và postgresql+psycopg:// đều dùng psycopg 3, giữ nguyên phần còn lại URL. |
| TC-P02-S02 | Staging healthy | Health 200, DB query thành công, schema revision đúng manifest; ba bằng chứng riêng. |
| TC-P02-S03 | Token staging hợp lệ | API xác minh identity và trả bootstrap hoặc onboarding theo membership. |

### Trường hợp lỗi và phục hồi P2

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P02-E01 | Railpack không nhận source | BUILD_SOURCE_INVALID | Kiểm tra commit, root và Dockerfile; deploy source ứng dụng đúng. |
| TC-P02-E02 | Không có psycopg2 | DATABASE_DRIVER_MISMATCH | Chuẩn hóa URL trước tạo engine cả API/Alembic; không thêm driver khác để che lệch. |
| TC-P02-E03 | Healthcheck 503 | SERVICE_NOT_LISTENING | Kiểm tra process log, bind 0.0.0.0, PORT và target port rồi path. |
| TC-P02-E04 | DB reachable nhưng thiếu bảng | SCHEMA_NOT_READY | Kiểm tra Alembic head riêng; connectivity 200 không đóng migration gate. |
| TC-P02-E05 | Sai issuer hoặc JWKS down | AUTH_VERIFICATION_FAILED | Token sai bị từ chối; outage có retry giới hạn, không tạo identity giả. |
| TC-P02-E06 | Cấu hình thực khác file repo | DEPLOYMENT_CONFIG_DRIFT | Đọc deployment effective settings và ghi diff; không kết luận chỉ từ config-as-code path. |

### Bất biến và điều kiện đóng P2

- **Dữ liệu phải giữ/transaction:** Pre-deploy thất bại không thay bản release đang hoạt động; cấu hình không ghi password vào log.
- **Bàn giao:** Deployment/env manifest, migration evidence, Auth contract checks.
- **Exit gate:** Đúng source và environment; health, schema, JWT hợp lệ/lỗi pass; không dùng production DB cho smoke staging.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-3"></a>

## P3 — App Shell, đăng nhập, onboarding và Home Dashboard

- **Module:** MOD-00, MOD-01.
- **Requirement:** FR-P03-01 đến FR-P03-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P2 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Bác sĩ/kỹ sư đăng nhập, vào đúng organization và hiểu trạng thái công việc.
- **Contract:** specification §8 / SPEC-P03; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P3

1. Mở URL hoặc deep-link.
2. Đăng nhập/khôi phục session và bootstrap identity.
3. Nếu chưa thuộc tổ chức, tạo organization đầu tiên; nếu đã có thì vào workspace.
4. Hiển thị dashboard dữ liệu thật và thao tác nhanh.
5. Logout hoặc hết session thì dọn cache và quay lại đúng luồng đăng nhập.

### Work packages P3

- [ ] P03-W01 — Đối chiếu Stitch Home/Auth và component hóa AppShell/loading/empty/error.
- [ ] P03-W02 — Hoàn thiện refresh single-flight, return URL nội bộ và xóa cache khi đổi identity.
- [ ] P03-W03 — Bootstrap phân biệt membership thiếu, inactive và outage; onboarding transaction idempotent.
- [ ] P03-W04 — Dashboard query độc lập từng widget; giới hạn timeout, retry và hiển thị dữ liệu cũ có timestamp.
- [ ] P03-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P03-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P3

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P03-S01 | Đăng nhập từ deep-link | Đến đúng route nội bộ sau auth; bootstrap dùng organization thật. |
| TC-P03-S02 | Onboarding lần đầu | Một organization + identity projection + membership; retry không tạo tổ chức thứ hai. |
| TC-P03-S03 | Dashboard rỗng | Số liệu 0/collection rỗng, có CTA tạo site/machine; không hiển thị dữ liệu giả. |
| TC-P03-S04 | Refresh và logout | Refresh giữ phiên hợp lệ; logout không còn cache dữ liệu tổ chức trên UI. |

### Trường hợp lỗi và phục hồi P3

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P03-E01 | Sai mật khẩu/email không tồn tại | SIGN_IN_FAILED | Thông báo trung tính; giữ email, không giữ mật khẩu. |
| TC-P03-E02 | Link recovery hết hạn/đã dùng | RECOVERY_LINK_INVALID | Cho yêu cầu link mới; không loop callback. |
| TC-P03-E03 | Session hết hạn/JWKS outage | SESSION_UNAVAILABLE | Phân biệt yêu cầu đăng nhập với lỗi dịch vụ; không refresh vô hạn. |
| TC-P03-E04 | Membership bị vô hiệu | ORGANIZATION_MEMBERSHIP_REQUIRED | Hiển thị ngữ cảnh không khả dụng; không tự gắn tổ chức khác. |
| TC-P03-E05 | Thiếu VITE biến lúc build | AUTH_CONFIGURATION_MISSING | Trang lỗi cấu hình có mã hỗ trợ; rebuild web với public config đúng. |
| TC-P03-E06 | API 404/CORS/offline | WORKSPACE_LOAD_FAILED | Giới hạn spinner; retry có nút; kiểm tra API base URL và deployment riêng web/API. |

### Bất biến và điều kiện đóng P3

- **Dữ liệu phải giữ/transaction:** Onboarding cùng transaction; two-tab submit tạo tối đa một context active; cache key theo identity/organization.
- **Bàn giao:** Auth/AppShell/dashboard hoạt động và recovery/empty/error screens.
- **Exit gate:** Happy path, first-use, expiry, offline, deep-link và logout cache tests pass trên staging.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-4"></a>

## P4 — Organization, Site, Machine và thành viên ngang hàng

- **Module:** MOD-02.
- **Requirement:** FR-P04-01 đến FR-P04-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P3 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Quản lý cấu trúc bệnh viện, thiết bị và đưa đồng nghiệp vào đúng tổ chức.
- **Contract:** specification §8 / SPEC-P04; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P4

1. Mở quản lý organization.
2. Tạo site, tạo machine thuộc site.
3. Đổi tên/thông tin máy và xem history.
4. Mời đồng nghiệp bằng luồng nhận lời mời xác thực vào đúng tổ chức.
5. Archive/restore đối tượng và kiểm tra QA/trend cũ còn đúng định danh.

### Work packages P4

- [ ] P04-W01 — Hoàn thiện CRUD/search/pagination và uniqueness scoped organization.
- [ ] P04-W02 — Tạo invitation một lần, expiry, accept đúng verified identity; không tự join bằng domain email.
- [ ] P04-W03 — Bổ sung optimistic revision cho sửa đồng thời và kiểm tra active parent.
- [ ] P04-W04 — Hoàn thiện archive/restore, membership lifecycle và audit; không xây action roles.
- [ ] P04-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P04-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P4

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P04-S01 | Tạo hierarchy | Site/machine thuộc đúng organization; list/search/detail nhất quán. |
| TC-P04-S02 | Đổi tên máy | stable_machine_id và mọi QA/trend/report source không đổi. |
| TC-P04-S03 | Đồng nghiệp nhận lời mời | Verified identity đúng nhận một membership, có cùng chức năng với thành viên khác. |
| TC-P04-S04 | Archive và restore | Lịch sử vẫn truy cập; tạo case mới chỉ khi parent đang active. |

### Trường hợp lỗi và phục hồi P4

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P04-E01 | Machine code trùng | MACHINE_CODE_CONFLICT | 409; chỉ rõ field, giữ dữ liệu form để sửa. |
| TC-P04-E02 | Site khác tổ chức hoặc inactive | PARENT_NOT_AVAILABLE | Không tạo/move record; query scoped trả 404/409 phù hợp. |
| TC-P04-E03 | Hai người sửa cùng revision | REVISION_CONFLICT | 409; hiển thị bản mới và phần đang sửa, không silently overwrite. |
| TC-P04-E04 | Invitation hết hạn/sai identity | INVITATION_INVALID | Không tạo membership; cấp lời mời mới qua luồng thành viên. |
| TC-P04-E05 | Xóa thành viên active cuối cùng | LAST_MEMBERSHIP_CONFLICT | Giữ ít nhất một thành viên active hoặc xử lý archive organization rõ ràng. |
| TC-P04-E06 | Mất phản hồi sau create | MUTATION_RESULT_UNKNOWN | Tra idempotency/result trước khi gửi lại, không tạo trùng. |

### Bất biến và điều kiện đóng P4

- **Dữ liệu phải giữ/transaction:** Accept invitation và membership commit cùng transaction; archive không hard-delete; lịch sử nguồn giữ nguyên.
- **Bàn giao:** Management screens, membership onboarding, history và contract tests.
- **Exit gate:** Hai identity cùng organization dùng được nghiệp vụ; isolate organization khác; rename/archive/restore/concurrent edit pass.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-5"></a>

## P5 — QA Archive, Folder và QA Case

- **Module:** MOD-03.
- **Requirement:** FR-P05-01 đến FR-P05-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P4 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Tổ chức hồ sơ như cây thư mục và tìm đúng case bằng metadata.
- **Contract:** specification §8 / SPEC-P05; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P5

1. Tạo cây folder và chọn vị trí.
2. Tạo case đúng site/machine/cycle/thời điểm.
3. Tìm bằng text và kết hợp filter, mở deep-link.
4. Rename/move subtree hoặc chuyển case.
5. Archive/restore và xem lại case/run/report theo ID cũ.

### Work packages P5

- [ ] P05-W01 — Hoàn thiện folder cycle detection, root uniqueness và transaction move subtree.
- [ ] P05-W02 — Case form dùng parent active cùng organization; versioned metadata và audit.
- [ ] P05-W03 — Thêm search/filter/index/sort stable tie-break ID, export metadata.
- [ ] P05-W04 — Thiết kế breadcrumb, move dialog, archived history và deep-link reload.
- [ ] P05-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P05-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P5

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P05-S01 | Move subtree | Path mọi descendant cập nhật nguyên tử; case ID và nguồn report không đổi. |
| TC-P05-S02 | Bộ lọc kết hợp | Site/machine/cycle/time/text cùng áp dụng; total và pagination nhất quán. |
| TC-P05-S03 | Archive history | Default list ẩn subtree đã archive; history vẫn mở được case/result. |
| TC-P05-S04 | Case không có file | Hiển thị empty input CTA; vẫn lưu case hợp lệ. |

### Trường hợp lỗi và phục hồi P5

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P05-E01 | Move vào chính nó/con cháu | FOLDER_CYCLE | 409; giữ cây cũ, không cập nhật một phần. |
| TC-P05-E02 | Trùng tên cùng parent | FOLDER_NAME_CONFLICT | 409; khác parent được dùng cùng tên. |
| TC-P05-E03 | Parent bị archive trong lúc thao tác | PARENT_NOT_AVAILABLE | Từ chối mutation; refresh cây và giữ lựa chọn có thể sửa. |
| TC-P05-E04 | Machine không thuộc site | CASE_HIERARCHY_INVALID | 422/404; không lưu case sai liên kết. |
| TC-P05-E05 | Trang phân trang vượt dữ liệu | PAGE_OUT_OF_RANGE | Collection rỗng hoặc đưa về trang hợp lệ có thông báo; không 500. |
| TC-P05-E06 | Restore gặp tên đã dùng | RESTORE_CONFLICT | Cho đổi tên/đích, giữ archived cho tới khi transaction thành công. |

### Bất biến và điều kiện đóng P5

- **Dữ liệu phải giữ/transaction:** Move subtree transaction; case một primary folder; archived ancestor ngăn tạo dữ liệu mới mặc định.
- **Bàn giao:** Archive/detail/filter/move/restore UI và database constraints.
- **Exit gate:** Nested move, archive/restore, combined search, cross-scope và deep-link tests có evidence.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-6"></a>

## P6 — Upload, Artifact, Manifest và Validation

- **Module:** MOD-04.
- **Requirement:** FR-P06-01 đến FR-P06-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P5 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Lưu nguyên byte, phân loại đúng và giải thích dữ liệu có dùng được cho workflow hay không.
- **Contract:** specification §8 / SPEC-P06; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P6

1. Chọn case và file, type/role; hiển thị tên và kích thước trước gửi.
2. Upload có progress; server kiểm size/checksum và lưu object.
3. Commit artifact + manifest; hiển thị thành công hoặc duplicate rõ ràng.
4. Validate nội dung và liên kết dataset; xem findings theo field.
5. Download file, xác nhận checksum; retry hoặc tạo derived revision khi cần sửa.

### Work packages P6

- [ ] P06-W01 — Hoàn thiện streaming size limit, object/DB compensation và cleanup orphan có retention.
- [ ] P06-W02 — Content detection phải đối chiếu declared type; JSON gắn DICOM không được VALID như DICOM.
- [ ] P06-W03 — Tách file validity với dataset/workflow readiness; geometry linking không dựa filename/PatientID.
- [ ] P06-W04 — Upload queue/retry, idempotent manifest role, signed URL renewal và checksum round-trip.
- [ ] P06-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P06-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P6

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P06-S01 | File hợp lệ | Byte count và server SHA256 khớp download; manifest đúng role/validator. |
| TC-P06-S02 | Trùng cùng byte/type | Reuse trong scope hợp lệ; thêm role thiếu đúng một lần. |
| TC-P06-S03 | Cùng tên khác byte/type | Tạo artifact riêng hoặc báo type mismatch; không ghi đè file cũ. |
| TC-P06-S04 | Upload một file lỗi trong batch | File còn lại giữ thành công; retry chỉ file lỗi, không rollback cả batch. |

### Trường hợp lỗi và phục hồi P6

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P06-E01 | Chưa chọn file/0 byte | FILE_REQUIRED_OR_EMPTY | Chặn trước upload; chỉ rõ ô file, không spinner vô hạn. |
| TC-P06-E02 | Vượt giới hạn | UPLOAD_TOO_LARGE | 413; dừng đọc khi vượt limit, dọn temp; không tạo VALID artifact. |
| TC-P06-E03 | Mất mạng giữa upload | UPLOAD_INTERRUPTED | Không tuyên bố đã lưu; query trạng thái/checksum rồi retry file. |
| TC-P06-E04 | Object store/DB commit lỗi | ARTIFACT_PERSISTENCE_FAILED | Không trả success; ghi cleanup/reconciliation task cho object chưa tham chiếu. |
| TC-P06-E05 | Type hoặc DICOM/JSON schema sai | ARTIFACT_TYPE_MISMATCH | Findings giải thích; không cho artifact sai profile vào engine. |
| TC-P06-E06 | Thiếu units/scaling/UID/geometry | INPUT_METADATA_INVALID | INVALID hoặc warning theo field và workflow; không tự đoán. |
| TC-P06-E07 | Signed URL hết hạn | DOWNLOAD_LINK_EXPIRED | Lấy link mới sau xác thực scope; không reupload file. |

### Bất biến và điều kiện đóng P6

- **Dữ liệu phải giữ/transaction:** Object PUT và DB không có distributed transaction: pending operation + compensation/reconciliation; success chỉ sau durable object + DB commit.
- **Bàn giao:** Upload/manifest/validation/detail UI; format fixtures; round-trip checksum evidence.
- **Exit gate:** Real browser upload→validate→download checksum, duplicate/type/role, interrupted upload và storage failure tests pass.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-7"></a>

## P7 — Machine QA checklist, rule engine và history

- **Module:** MOD-05.
- **Requirement:** FR-P07-01 đến FR-P07-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P6 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Nhập phép đo, áp protocol đã chọn, xem kết quả và so sánh các lần QA.
- **Contract:** specification §8 / SPEC-P07; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P7

1. Tạo run từ case và protocol version.
2. Nhập metric, unit và ghi chú; lưu draft.
3. Validate required/unit/baseline; evaluate một snapshot.
4. Xem từng metric và kết quả tổng, drill-down về rule.
5. Rerun tạo lượt mới; compare; đưa metric tương thích vào trend.

### Work packages P7

- [ ] P07-W01 — Tách seed synthetic với protocol nội bộ; snapshot đầy đủ rule/unit/baseline.
- [ ] P07-W02 — Optimistic measurement save và idempotent evaluate cùng expected revision.
- [ ] P07-W03 — Hoàn thiện boundary rules, zero baseline, missing required và total status aggregation.
- [ ] P07-W04 — Trend projection unique source metric; rerun không nhân đôi projection của run cũ.
- [ ] P07-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P07-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P7

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P07-S01 | Giá trị trong tolerance | Metric PASS với actual/unit/limit/margin và rule snapshot đúng. |
| TC-P07-S02 | Giá trị vượt action | Run tính toán hoàn tất, metric FAIL; không gán technical FAILED. |
| TC-P07-S03 | N/A hợp lệ | Metric NOT_APPLICABLE có reason; không coi là PASS hoặc đưa số giả vào trend. |
| TC-P07-S04 | Rerun và compare | Run mới riêng, run trước không thay; bảng so sánh theo metric key/unit. |

### Trường hợp lỗi và phục hồi P7

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P07-E01 | Thiếu metric bắt buộc | MEASUREMENT_REQUIRED | Giữ draft và đánh dấu field; không tạo valid result. |
| TC-P07-E02 | Sai unit/NaN | MEASUREMENT_INVALID | Không đoán unit hoặc ép thành 0; cho sửa input. |
| TC-P07-E03 | Percent deviation baseline 0 | BASELINE_ZERO | Không chia 0; yêu cầu baseline khác hoặc rule không dùng phần trăm. |
| TC-P07-E04 | Autosave muộn sau evaluate | REVISION_CONFLICT | Từ chối sửa completed snapshot; cho tạo rerun. |
| TC-P07-E05 | Evaluate double click | DUPLICATE_OPERATION | Trả cùng kết quả của snapshot; một tập trend points. |
| TC-P07-E06 | Protocol bị archive | PROTOCOL_NOT_AVAILABLE | Run mới không chọn; run cũ vẫn đọc snapshot. |

### Bất biến và điều kiện đóng P7

- **Dữ liệu phải giữ/transaction:** Measurement revision được khóa tại evaluate; result + trend projection commit nhất quán hoặc reconciliation idempotent.
- **Bàn giao:** Checklist/result/history/compare; known-answer rule tests; staging evidence.
- **Exit gate:** Boundary PASS/WARNING/FAIL/N-A, unit/baseline errors và rerun/projection uniqueness đều pass.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-8"></a>

## P8 — PSQA Gamma, RTDOSE, worker và kết quả 2D/3D

- **Module:** MOD-06.
- **Requirement:** FR-P08-01 đến FR-P08-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P6, P7 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Chạy PSQA từ RTDOSE + comparison qua worker, giữ cấu hình và kết quả tái hiện được.
- **Contract:** specification §8 / SPEC-P08; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** các test local được ghi ở checkpoint P8 dưới đây; các scenario staging/oracle/benchmark vẫn NOT_RUN cho đến khi có evidence đúng release, không kế thừa PASS tự động từ test cũ.

### Workflow P8

1. Chọn RTDOSE reference và comparison validated; optional RTPLAN/RTSTRUCT theo mục đích.
2. Preflight units/geometry/config/profile và ước lượng tài nguyên.
3. Enqueue idempotent, lưu input/config/engine snapshot; theo dõi trạng thái qua refresh.
4. Worker claim/heartbeat/tính/lưu result rồi ack.
5. Xem map/histogram/pass rate/profiles; compare, rerun config mới hoặc retry lỗi hạ tầng.

### Work packages P8

- [ ] P08-W01 — Đóng gap BR-007; explicit workflow profile, unit/frame/transform contracts và supported capabilities. `LOCAL_SLICE_ONLY`: profile/preflight đã có local, staging contract còn mở.
- [ ] P08-W02 — Khóa thuật toán search/interpolation/global/local/threshold theo specification §5; thêm oracle độc lập. `LOCAL_SLICE_ONLY`: coverage/max-gamma/censor đã có test, exhaustive oracle/convergence còn mở.
- [ ] P08-W03 — Bổ sung atomic lease/fencing, attempt history, outbox/reconciliation và giới hạn tài nguyên/retry. `LOCAL_SLICE_ONLY`: lease/attempt/outbox đã có local; bounded retry/resource/failure injection còn mở.
- [ ] P08-W04 — Hoàn thiện Gamma UI configuration/unsupported states, maps/profiles; E2E RTDOSE/3D và workload lớn. `LOCAL_SLICE_ONLY`: UI control đã có; staging upload/3D/large workload còn mở.
- [ ] P08-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P08-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P8

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P08-S01 | RTDOSE và measurement 3D golden | Fixture 2×2×2 tương đương 1–8 Gy: 8 evaluated/8 passing, gamma 0 trong sai số; lưu source formats. |
| TC-P08-S02 | RTSTRUCT không có | PSQA phantom vẫn chạy khi input khác hợp lệ; không bắt RTSTRUCT không cần thiết. |
| TC-P08-S03 | Thay cấu hình/rerun | Run mới có snapshot mới; run cũ và report cũ giữ nguyên. |
| TC-P08-S04 | Retry lỗi storage | Cùng run/config có attempt mới; sau phục hồi hoàn tất một result duy nhất. |
| TC-P08-S05 | Hai worker nhận cùng message | Chỉ holder lease được commit; duplicate ack không tạo result thứ hai. |

### Trường hợp lỗi và phục hồi P8

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P08-E01 | PSQA thiếu RTDOSE/comparison | RTDOSE_REQUIRED_OR_COMPARISON_REQUIRED | Chặn trước enqueue; JSON-only chỉ dùng ENGINE_TEST có nhãn riêng. |
| TC-P08-E02 | Sai Frame/geometry/đơn vị | GAMMA_INPUT_INCOMPATIBLE | Không auto-align/guess; yêu cầu transform/adapter được hỗ trợ. |
| TC-P08-E03 | Config ngoài capability | GAMMA_CONFIG_UNSUPPORTED | 422 với field; không bỏ qua shift/mask/field/interpolation không hỗ trợ. |
| TC-P08-E04 | Không có điểm đạt threshold | GAMMA_NO_EVALUATED_POINTS | INVALID_INPUT; pass rate null, không 100%. |
| TC-P08-E05 | Reference local normalization 0 | GAMMA_LOCAL_ZERO_REFERENCE | Không chia 0; xử lý exclusion policy có count/reason, không âm thầm pass. |
| TC-P08-E06 | Redis mất giữa DB commit/enqueue | GAMMA_DISPATCH_UNAVAILABLE | Outbox retry/reconciliation; không mất run hoặc chạy engine trong HTTP. |
| TC-P08-E07 | Worker chết/OOM/lease hết | GAMMA_EXECUTION_INTERRUPTED | Lưu attempt lỗi; reclaim có fencing, bounded retry và giữ input snapshot. |
| TC-P08-E08 | Dose scale/UID/codec unsupported | GAMMA_DICOM_UNSUPPORTED | Mã cụ thể; input còn nguyên, cho chọn adapter/cấu hình khác. |
| TC-P08-E09 | Vượt resource limit | GAMMA_RESOURCE_LIMIT | Từ chối preflight hoặc terminate có error; không treo API. |
| TC-P08-E10 | Checksum khác snapshot | GAMMA_SOURCE_CHANGED | Dừng attempt; không commit result từ input khác. |

### Checkpoint thực thi P8 ngày 2026-09-08

Slice implementation hiện tại đã được kiểm tra local nhưng chưa đóng phase:

- Backend: full suite **58/58 PASS**; Gamma API/engine/DICOM/worker lần lượt `7/7`, `3/3`, `4/4` PASS.
- Frontend: lint, typecheck, Vitest `1/1` và production build PASS.
- Covered locally: declared-type mismatch; DICOM RTDOSE chuẩn GY + scaling; PSQA/ENGINE_TEST profile; FULL_ROI/OVERLAP_ONLY; no-candidate; max-gamma censoring; single-holder lease và stale-worker fencing.
- Chưa covered đủ: staging schema `20260908_0009`; browser report create/edit/export/download; Gamma crash sau commit trước ack; bounded retry/dead-letter; resource/large-input benchmark; P9 visual export review và remote evidence.

Các dòng trên là evidence implementation, không thay cho `P08-VERIFY` và `P08-HANDOFF`.

### Bất biến và điều kiện đóng P8

- **Dữ liệu phải giữ/transaction:** At-least-once dispatch + unique run operation + conditional lease commit; ack chỉ sau durable terminal state; stale worker không được ghi đè.
- **Bàn giao:** RTDOSE/measurement fixtures, independent oracle, maps, job diagnostics, benchmark và staged E2E.
- **Exit gate:** Tất cả profile được công bố có golden/error tests; RTDOSE+measurement 3D staging, worker crash/retry/concurrency và large workload đạt budget.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-9"></a>

## P9 — Report Builder, revision, preview và export

- **Module:** MOD-07.
- **Requirement:** FR-P09-01 đến FR-P09-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P7, P8 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Người dùng tùy chỉnh toàn bộ report và xem lại đúng bản từng xuất.
- **Contract:** specification §8 / SPEC-P09; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** `LOCAL_VERIFIED` cho implementation slice trên schema `20260908_0009`; staging browser, object-storage, failure-injection và visual export vẫn `NOT_RUN` cho đến khi có evidence đúng release.

### Workflow P9

1. Chọn case/run hoặc tạo calculation report trong namespace Biological.
2. Chọn template, thêm/xóa/ẩn/đổi tên/sắp xếp block.
3. Preview từ snapshot và lưu revision.
4. Xuất PDF/PNG/CSV/JSON; theo dõi render job.
5. Mở revision cũ, compare hoặc tạo revision mới, tải đúng artifact đã render.

### Work packages P9

- [x] P09-W01 — Block schema + revision optimistic save; source_binding theo stable ID, không label. `LOCAL_VERIFIED`.
- [x] P09-W02 — Snapshot source/result/template/assets khi save; old revision không đọc live query. `LOCAL_VERIFIED`.
- [x] P09-W03 — Renderer font/assets pinned, sandbox rich text/URL và deterministic render options. JSON/CSV/PDF/PNG renderer đã có; font/visual fixture staging còn mở.
- [x] P09-W04 — Export jobs idempotent theo revision/options; checksum, retention và retry độc lập analysis. Durable export + idempotency đã có; retry/retention workload còn mở.
- [ ] P09-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P09-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P9

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P09-S01 | Tùy chỉnh toàn quyền | Thêm/ẩn/xóa/rename/reorder mọi block kể cả warning; source calculation snapshot không bị sửa. |
| TC-P09-S02 | Template đổi sau export | Mở revision cũ giữ nội dung cũ và tải nguyên file render đã lưu. |
| TC-P09-S03 | Tiếng Việt/bảng nhiều trang | Dấu/font không lỗi, heading lặp hợp lý, không cắt metric/chart. |
| TC-P09-S04 | Biological report độc lập | Không cần QACase; export cùng renderer với source namespace đúng. |

### Trường hợp lỗi và phục hồi P9

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P09-E01 | Hai người lưu cùng revision | REPORT_REVISION_CONFLICT | 409; giữ draft và cho so sánh/copy sang revision mới. |
| TC-P09-E02 | Source artifact thiếu/hỏng | REPORT_SOURCE_UNAVAILABLE | Chỉ rõ block; không xuất số 0 thay missing; giữ revision/source refs. |
| TC-P09-E03 | Rich text/script/URL nguy hiểm | REPORT_CONTENT_INVALID | Sanitize hoặc từ chối schema; vẫn cho tùy chỉnh qua block được hỗ trợ. |
| TC-P09-E04 | Renderer timeout/OOM | REPORT_RENDER_FAILED | Export failed có retry; không thay analysis hoặc bản export trước. |
| TC-P09-E05 | Định dạng không hỗ trợ/chart lỗi | EXPORT_FORMAT_UNSUPPORTED | Báo đúng block/format; không trả file trống là success. |
| TC-P09-E06 | Download hết hạn | DOWNLOAD_LINK_EXPIRED | Cấp link mới cho cùng revision sau kiểm scope. |

### Bất biến và điều kiện đóng P9

- **Dữ liệu phải giữ/transaction:** Save revision chỉ một lần trên expected revision; export failure không mutate result; giữ file gốc export để byte reproducibility.
- **Bàn giao:** Builder/viewer/history/compare/renderer; visual export fixtures.
- **Exit gate:** Tùy chỉnh đầy đủ, old revision reproducibility, tiếng Việt/bảng dài, concurrent edit và render retry pass.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

### Checkpoint implementation P9 ngày 2026-09-08

- Schema: migration `20260908_0009` tạo `report_template_versions`, `report_revisions`, `report_block_configs` và `export_jobs`; local PostgreSQL đã chạy `0008 -> 0009`.
- Backend: `test_reports.py` **4/4 PASS**, bao phủ source snapshot immutability, full customization, template version, optimistic conflict, organization scope, dangerous content, missing source, deterministic export và idempotency.
- Renderer: output JSON/CSV/PDF/PNG được hash và lưu object storage; PDF fallback ghi warning font Unicode thay vì coi là không có cảnh báo.
- Frontend: `/app/reports` đã có history, tạo report, chọn source/template, chỉnh block, preview snapshot và export actions; lint/typecheck/test/build PASS local.
- Chưa đóng P9: storage failure/retry, byte-level visual review và xác nhận build SHA trên staging candidate mới.
- Chưa đóng P10: complete current-candidate negative matrix, large-series budget, baseline/event update/archive UI, source drill-down/export verification sau refresh và visual/accessibility evidence.

<a id="phase-10"></a>

## P10 — Trend, baseline và sự kiện bảo trì

- **Module:** MOD-08.
- **Requirement:** FR-P10-01 đến FR-P10-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P7, P8, P9 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Theo dõi phép đo tương thích theo thời gian và drill-down đúng nguồn.
- **Contract:** specification §8 / SPEC-P10; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** `STAGING_SMOKE_PARTIAL` cho implementation slice trên schema `20260908_0010`; authenticated basic trend/baseline/maintenance/rebuild/day-aggregate smoke đã đạt trên candidate `d15738f`, nhưng large-series budget, complete S/E/C matrix và visual/accessibility evidence vẫn `NOT_RUN` cho đến khi có evidence đúng release.

### Workflow P10

1. Chọn machine, metric và khoảng thời gian.
2. Chọn filter và nhóm tương thích.
3. Hiển thị điểm raw, baseline/limits và maintenance markers.
4. Chọn điểm để mở case/run/report nguồn.
5. Export cùng bộ lọc, timezone và phương pháp aggregate.

### Work packages P10

- [x] P10-W01 — Projection unique source_run/metric; index organization/machine/time; rebuild idempotent. `LOCAL_VERIFIED`.
- [x] P10-W02 — Compatibility signature unit + energy + detector + protocol meaning; explicit normalization. `LOCAL_VERIFIED`.
- [x] P10-W03 — Raw versus day/week aggregate contract, extrema/source-ID preservation, timezone/range handling. `LOCAL_VERIFIED` cho contract và test; large-series budget còn mở.
- [x] P10-W04 — Baseline version/event CRUD; chart keyboard/table fallback/export metadata. `LOCAL_VERIFIED` cho API/UI và test; basic authenticated staging create/read smoke đạt, nhưng update/archive UI và visual/accessibility evidence staging còn mở.
- [ ] P10-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P10-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P10

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P10-S01 | Filter tương thích | Số điểm/trị số khớp query và export, machine ID không bị tên mới chia trend. |
| TC-P10-S02 | Outlier và maintenance | Outlier luôn truy lại được; marker không sửa dữ liệu trước/sau. |
| TC-P10-S03 | Drill-down | Điểm mở đúng run/protocol/revision, không mặc định report mới của case. |
| TC-P10-S04 | Dữ liệu lớn | Aggregate có nhãn, min/max và count; raw drill-down còn truy cập được. |

### Trường hợp lỗi và phục hồi P10

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P10-E01 | Unit/context không tương thích | TREND_SERIES_INCOMPATIBLE | Tách series hoặc yêu cầu chuyển đổi explicit; không nối thành một đường. |
| TC-P10-E02 | Khoảng ngày ngược | DATE_RANGE_INVALID | 422/field error; giữ filter để sửa. |
| TC-P10-E03 | Không có dữ liệu | TREND_EMPTY | Empty state đúng phạm vi; không tạo điểm 0. |
| TC-P10-E04 | Baseline thiếu/0 cho percent | TREND_BASELINE_INVALID | Hiển thị raw; không tính percent không xác định. |
| TC-P10-E05 | Projection bị lặp | TREND_DUPLICATE_SOURCE | Unique constraint/rebuild idempotent; không nhân đôi điểm. |
| TC-P10-E06 | Source đã archive | TREND_SOURCE_ARCHIVED | Vẫn mở lịch sử có nhãn archived, không mất lineage. |

### Kiểm thử bổ sung và phạm vi chưa được phép bỏ qua P10

| Test ID | Điều kiện | Expected |
| :--- | :--- | :--- |
| TC-P10-S05 | Hai điểm cùng ngày, khác timezone và khác trạng thái | Bucket day/week đúng biên timezone; `count`, mean, min, max, first/last, status counts và source IDs đúng với tập raw. |
| TC-P10-S06 | Baseline version mới có effective time nằm giữa hai điểm | Điểm trước dùng version cũ, điểm sau dùng version mới; không hồi tố điểm cũ. |
| TC-P10-S07 | Rebuild sau khi projection thiếu một metric | Chỉ tạo lại điểm thiếu; các điểm hiện có không nhân đôi và response thống kê created/existing/repaired rõ ràng. |
| TC-P10-S08 | Nhiều machine cùng metric nhưng machine được rename | Cùng `machine_id` giữ một series; tên hiển thị mới không tạo series thứ hai. |

| Test ID | Điều kiện lỗi bổ sung | Expected và phục hồi |
| :--- | :--- | :--- |
| TC-P10-E07 | Timezone không tồn tại hoặc filter machine UUID sai | 422 theo field, giữ filter để sửa, không query dữ liệu khác. |
| TC-P10-E08 | Baseline version trùng hoặc update sai revision | 409; bản hiện tại và draft được giữ, không overwrite. |
| TC-P10-E09 | Event end trước start hoặc machine archived | 422/409 đúng nguyên nhân; không tạo event một phần. |
| TC-P10-E10 | Source point thiếu case/run/machine cùng organization | 404/409; không trả điểm mồ côi như dữ liệu hợp lệ; rebuild ghi diagnostic. |
| TC-P10-E11 | Raw query vượt giới hạn hoặc export dependency fail | 413/503; gợi ý aggregate hoặc retry an toàn, không trả CSV/JSON bị cắt như success. |
| TC-P10-E12 | User đổi filter trong lúc request cũ trả về | Kết quả cũ không ghi đè filter mới; loading/request cancellation hoặc request identity được kiểm chứng. |

### Bất biến và điều kiện đóng P10

- **Dữ liệu phải giữ/transaction:** Trend là projection tái dựng từ snapshot, không source of truth; event edit có revision.
- **Bàn giao:** Trend dashboard/filter/drill-down và export/large-data checks.
- **Exit gate:** Không trộn máy/unit; baseline/outlier/timezone/filter/export/drill-down và rebuild pass; TC-P10-S01–S08 và TC-P10-E01–E12 phải có kết quả; riêng S04/S05–S08 phải có workload/evidence tương ứng chứ không được suy ra từ test unit nhỏ.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

### Checkpoint staging P10 ngày 2026-09-08

- API candidate từ commit `b8c7911` đã chạy migration `20260908_0010`; public `/api/v1/ready` trả `status=ready`, schema `20260908_0010`.
- Web candidate từ commit `d15738f` đã deploy thành công; authenticated `/app/trend` hiển thị Build `9262bfd`, API thật, 6 trend points và 3 compatible series.
- Smoke đã kiểm: baseline có mốc hiệu lực rõ ràng và outlier/delta, maintenance marker revision `1`, rebuild `0 mới/6 đã có`, aggregate day giữ 2 source runs mỗi bucket. Đây chỉ là `STAGING_SMOKE_PARTIAL`; chưa đánh dấu `DONE-v2`.

<a id="phase-11"></a>

## P11 — QA Protocol Library và rule version

- **Module:** MOD-09.
- **Requirement:** FR-P11-01 đến FR-P11-04, xem `business-analysis.md` §14 và §21.3.
- **Dependency/entry gate:** P7, P9 và P10 đã có contract ổn định cho protocol consumer, result snapshot, report source và trend source. Không dùng record/secret của environment khác.
- **Mục tiêu:** Cung cấp một thư viện protocol nội bộ có version, applicability, nguồn tham khảo và rule rõ ràng; thay đổi protocol không làm đổi ngược run/report/trend đã ghi.
- **Không thuộc phạm vi P11:** Không xây doctor/engineer role, action-level permission hoặc approval queue; không biến protocol tham khảo thành giới hạn lâm sàng mặc định; không sửa live snapshot của run cũ.
- **Contract:** `specification.md` §8 / SPEC-P11 và §8.4; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái hiện tại:** `LOCAL_VERIFIED` cho model, migration `20260908_0011`, validate/create/edit/clone/activate/archive/compare, organization scope và Machine QA active-only selection; staging browser/consumer E2E và release evidence còn mở.

### Workflow P11

1. Resolve identity và organization context trước khi đọc library; hiển thị trạng thái loading/empty/error đúng organization.
2. Tìm protocol theo `protocol_key`, tên, QA type, applicability, status và pagination; mặc định không đưa version `ARCHIVED` vào lựa chọn dùng cho run mới.
3. Mở detail để xem version, revision, source type/reference, applicability, rule order, unit, limit, note và lineage. Không dùng tên hiển thị làm stable identity.
4. Chọn **New** hoặc **Clone**. New bắt đầu ở `DRAFT`; clone tạo version mới, deep-copy rule, ghi `source_protocol_version_id` và không dùng chung child ID.
5. Nhập/sửa header, applicability và rule. Editor phải kiểm key, display name, unit, rule type, numeric finite, required/N/A reason, min/max, target, tolerance và action level.
6. Bấm **Validate** để kiểm tra mà không ghi DB. Lỗi phải trỏ tới field/index; warning không được biến thành lỗi hoặc bị mất khi save.
7. Save bằng transaction. Version number, rule rows và audit phải cùng thành công hoặc cùng rollback. Save DRAFT tăng `revision`; gửi revision cũ phải conflict.
8. Activate khi version đã hợp lệ. ACTIVE dùng được cho run mới nhưng không sửa tại chỗ; thay đổi phải clone hoặc tạo version mới. Archive chỉ chặn sử dụng mới, không chặn lịch sử.
9. Khi P7/P8 tạo run, consumer phải nhận **explicit protocol version** và snapshot toàn bộ rule/applicability/source. P9/P10 mở source cũ phải đọc snapshot, không load limit live thay thế.
10. Compare hai version cùng organization, xem diff metadata/rule/lineage; sau refresh hoặc mất mạng, tra cứu ID/result trước khi gửi lại mutation.

### State và dữ liệu bắt buộc P11

| Thành phần | Hợp đồng phải giữ |
| :--- | :--- |
| Protocol family | `organization_id + protocol_key`; key uppercase ổn định, không đổi để né conflict. |
| Protocol version | `version_number`, `status`, `revision`, name, QA type, description, effective note, applicability, source type/reference, actor và timestamps. |
| Rule | `metric_key`, display name, unit, rule type, target/lower/upper/tolerance/action, required, sort order, note, reference. Key không trùng trong một version. |
| Lineage | Clone ghi version nguồn; child rule là bản sao độc lập; compare cho biết field/rule thêm, xóa hoặc đổi. |
| Consumer snapshot | P7/P8/P9/P10 lưu version/rule/limit/source tại thời điểm run/report/trend được chấp nhận. |
| Audit | Create, draft update, clone, activate, archive; audit mô tả lịch sử, không tạo phân cấp thành viên. |

### Work packages P11

- [x] P11-W01 — Chuẩn hóa protocol family/version/rule stable keys, organization scope, uniqueness và migration `20260908_0011`. `LOCAL_VERIFIED`.
- [x] P11-W02 — Editor/validator kiểm finite limits, unit, rule type, min/max, target, tolerance/action ordering, duplicate key, source và applicability. `LOCAL_VERIFIED`.
- [x] P11-W03 — Clone deep-copy rule/reference bindings; lifecycle DRAFT/ACTIVE/ARCHIVED, optimistic revision và active-only consumer selection. `LOCAL_VERIFIED`.
- [ ] P11-W04 — Nối đầy đủ P7/P8/P9/P10 consumer snapshot, source panel và remove dependency vào seed synthetic trong workflow thường. `IN_PROGRESS`.
- [ ] P11-VERIFY — chạy ma trận S/E/C trên local và staging đúng SHA/schema; ghi result/evidence/linked FR; đối chiếu design/data/API.
- [ ] P11-HANDOFF — cập nhật contract/OpenAPI, migration/release notes, release manifest, staging browser evidence và backlog còn lại.

### Trường hợp chạy đúng P11

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P11-S01 | Validate payload hợp lệ trước khi lưu | `valid=true`, không tạo row/audit; normalized key/applicability được preview rõ. |
| TC-P11-S02 | Tạo protocol mới | Trả version `1`, `DRAFT`, revision `1`, rule order và source đúng; list cùng organization thấy đúng một version. |
| TC-P11-S03 | Sửa DRAFT với `expected_revision` hiện tại | Chỉ field gửi/được phép thay đổi; revision tăng một lần; rules cũ được thay nguyên tử. |
| TC-P11-S04 | Activate DRAFT hợp lệ | Chuyển `DRAFT → ACTIVE`; revision tăng; Machine QA list thấy version active. |
| TC-P11-S05 | Clone ACTIVE hoặc ARCHIVED | Version mới tăng đúng family; child rule ID khác; lineage/source và nội dung deep-copy đúng. |
| TC-P11-S06 | Compare hai version | `same_family` và metadata/rule diff phản ánh đúng thêm/xóa/đổi, không đổi DB. |
| TC-P11-S07 | Archive version đang active | Chuyển `ACTIVE → ARCHIVED`; version biến khỏi lựa chọn run mới nhưng detail/history vẫn đọc được. |
| TC-P11-S08 | Hai thành viên cùng organization thao tác | Cả hai dùng cùng workflow; không yêu cầu role bác sĩ/kỹ sư hoặc approval riêng. |
| TC-P11-S09 | Run/report cũ sau khi protocol đổi/archive | Snapshot cũ vẫn giữ limit/rule/source/version cũ; run mới chỉ dùng active version explicit. |

### Trường hợp lỗi và phục hồi P11

Mã ở cột “Phân loại” là contract code. Mọi lỗi phải có HTTP status, field/path, correlation ID và invariant DB tương ứng; không gửi chuỗi OR làm một code API. Lỗi input không retry tự động; conflict phải tải bản hiện tại hoặc clone; lỗi uncertain phải tra ID trước khi gửi lại.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P11-E01 | Protocol key trống/sai format hoặc tên/QA type chỉ whitespace | `REQUEST_VALIDATION_FAILED` / `PROTOCOL_RULE_INVALID` | 422 theo field; giữ form, không tạo version. |
| TC-P11-E02 | Applicability có key lạ, scalar thay vì string list hoặc item rỗng | `PROTOCOL_APPLICABILITY_INVALID` | 422 theo `applicability.*`; không bỏ dimension hoặc tự coi là wildcard. |
| TC-P11-E03 | Rule key trùng, sai format, display/unit trống hoặc rule type không hỗ trợ | `PROTOCOL_RULE_INVALID` / `PROTOCOL_VERSION_CONFLICT` | 422; chỉ rõ index/key; không lưu một phần. |
| TC-P11-E04 | RANGE thiếu min/max hoặc min lớn hơn max | `PROTOCOL_RULE_INVALID` | Chặn save/activate; không tự đảo hai giới hạn. |
| TC-P11-E05 | MIN/MAX thiếu giới hạn; tolerance/action âm hoặc deviation thiếu target/tolerance | `PROTOCOL_RULE_INVALID` | Trả field errors; giữ rule hợp lệ khác trong draft. |
| TC-P11-E06 | PERCENT_DEVIATION có target bằng 0; số là NaN/Infinity | `PROTOCOL_RULE_INVALID` | Không chia 0/không serialize non-finite; yêu cầu giá trị finite. |
| TC-P11-E07 | Source type `REFERENCE` nhưng thiếu citation/URL/DOI/reference | `REFERENCE_REQUIRED` | 422; bổ sung nguồn hoặc chọn `USER_DEFINED/INTERNAL` explicit. |
| TC-P11-E08 | Create/clone sinh trùng family version/key hoặc request lặp khác payload | `PROTOCOL_VERSION_CONFLICT` | 409; query kết quả/version hiện tại rồi đổi key hoặc tiếp tục bản đã tạo. |
| TC-P11-E09 | Save/activate/archive với revision cũ, hoặc hai tab cùng sửa | `PROTOCOL_VERSION_CONFLICT` | 409; giữ draft local, tải bản mới, cho compare/clone; không overwrite. |
| TC-P11-E10 | Edit/activate version `ACTIVE` hoặc `ARCHIVED` không qua clone | `PROTOCOL_VERSION_IMMUTABLE` / `PROTOCOL_NOT_AVAILABLE` | 409; detail vẫn đọc, hướng dẫn clone/version mới. |
| TC-P11-E11 | Chọn ARCHIVED/inactive cho Machine QA/Gamma run mới | `PROTOCOL_NOT_AVAILABLE` | 409 hoặc preflight error; yêu cầu active explicit; old run vẫn đọc snapshot. |
| TC-P11-E12 | Rule hợp lệ về cú pháp nhưng consumer engine không hỗ trợ | `PROTOCOL_CAPABILITY_MISMATCH` | Preflight nêu rule/capability; không silently drop rule và không tạo PASS giả. |
| TC-P11-E13 | Organization không thuộc membership hoặc protocol ID không tồn tại | `ORGANIZATION_SCOPE_MISMATCH` / `PROTOCOL_NOT_FOUND` | 403/404; không lộ existence/detail của organization khác. |
| TC-P11-E14 | Mất mạng sau commit trước khi nhận response | `MUTATION_RESULT_UNKNOWN` | Không gửi lại ngay; list/detail theo idempotency/request context, chỉ retry nếu chưa có kết quả. |
| TC-P11-E15 | DB lỗi/constraint lỗi trong lúc ghi header, rule hoặc audit | `PROTOCOL_PERSISTENCE_FAILED` / `PROTOCOL_VERSION_CONFLICT` | Rollback toàn transaction; không để protocol không có rule hoặc audit giả; retry bounded. |
| TC-P11-E16 | List/compare response lỗi schema, timeout hoặc session hết hạn | `SERVICE_UNAVAILABLE` / `SESSION_UNAVAILABLE` | Dừng spinner, giữ filter/draft, refresh session một lần hoặc retry có giới hạn; không hiển thị dữ liệu cache của identity khác. |

### Bất biến và điều kiện đóng P11

- **Scope:** mọi read/write/compare phải resolve membership trước lookup resource; query khác organization không được trả detail, rule hoặc source.
- **Version:** version number là monotonic trong family; `ACTIVE`/`ARCHIVED` immutable; không hard-delete version đã có consumer snapshot.
- **Atomicity:** validate-only không mutation; create/update/clone/transition ghi header, child rule và audit theo transaction; không có protocol nửa chừng.
- **Consumer:** P7/P8/P9/P10 phải pin explicit version và snapshot rule/limit/source; archived chỉ bị chặn cho run mới, không bị xóa khỏi history.
- **Member equality:** mọi thành viên active trong organization sử dụng cùng workflow; audit/created_by/revision chỉ là provenance, không phải action permission.
- **UI:** có loading/empty/populated/validation/conflict/offline/error states; field error không mất input; không có nút activate/archive giả.
- **Local exit:** migration `20260908_0011`, focused/full backend, lint/typecheck/build và OpenAPI pass trên cùng SHA.
- **Staging exit:** API ready đúng schema; browser create→validate→save→edit→activate→clone→compare→archive; consumer run mới dùng active explicit; old run/report mở đúng snapshot; scope/conflict/error matrix và release manifest có evidence.
- **Nếu gate fail:** mở issue gắn testcase/FR/contract/SHA, giữ payload và DB invariant evidence, sửa package liên quan rồi chạy regression; không thay expected để hợp thức hóa output. Phase vẫn mở và không tự kế thừa `DONE-v2`.

<a id="phase-12"></a>

## P12 — Biological Hub và calculation history độc lập

- **Module:** MOD-10.
- **Requirement:** FR-P12-01 đến FR-P12-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P3, P9 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Có không gian tính toán riêng với scenario/history/report không cần case QA.
- **Contract:** specification §8 / SPEC-P12; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P12

1. Vào tab Biological Toolkit.
2. Chọn công cụ hoặc mở scenario cũ.
3. Nhập dữ liệu thủ công hoặc dataset riêng do user chọn.
4. Lưu scenario và calculation revision.
5. Mở lại, clone hoặc export calculation report độc lập.

### Work packages P12

- [x] P12-W01 — Tạo lại Stitch Biological Hub từ bốn màn hình chuẩn; không dùng screen hidden cũ. Screen hiện hành: `b32ef9de691f48449ec23e491a6b634d`; asset screenshot `50e2c49b3ec743a59f9d99e8b13e694f`.
- [x] P12-W02 — Namespace `/app/biological` và scoped scenario/calculation data không FK QACase bắt buộc; migration `20260908_0012`.
- [x] P12-W03 — Scenario DRAFT/SAVED/ARCHIVED, revision snapshot, history, search, clone và archive API/UI.
- [ ] P12-W04 — Tái dùng renderer P9 bằng source_type BIOLOGICAL; placeholder module có availability rõ.
- [x] P12-LOCAL-VERIFY — focused `apps/api/tests/test_biological.py`, full backend, Ruff/mypy, frontend lint/typecheck/Vitest/build và local PostgreSQL migration head đều pass trên candidate hiện tại.
- [ ] P12-STAGING-VERIFY — deploy đúng SHA; browser create→validate→save→edit/clone/archive/filter/history; kiểm response/DB state và không có QA linkage.
- [ ] P12-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### API surface và trạng thái triển khai P12

| Operation | Contract cần giữ | Trạng thái hiện tại |
| :--- | :--- | :--- |
| `GET /organizations/{org}/biological/tools` | Trả capability P13–P16, route và `available`; module chưa có code phải là `PLANNED` | Implemented; P13 `AVAILABLE`, P14–P16 `PLANNED` |
| `GET /organizations/{org}/biological/summary` | Chỉ đếm scenario/calculation/report cùng organization | Implemented |
| `POST /organizations/{org}/biological/scenarios/validate` | Validate-only; không mutation; kiểm source/reference và JSON finite | Implemented |
| `GET /organizations/{org}/biological/scenarios` | Search/status/include archived/pagination; archived không hiện mặc định | Implemented |
| `POST /organizations/{org}/biological/scenarios` | Tạo DRAFT rev 1 + initial snapshot + audit theo transaction | Implemented |
| `GET /organizations/{org}/biological/scenarios/{id}` | Detail và latest snapshot theo scope | Implemented |
| `GET /organizations/{org}/biological/scenarios/{id}/revisions` | Append-only history, newest first | Implemented |
| `PATCH /organizations/{org}/biological/scenarios/{id}` | Chỉ DRAFT, bắt `expected_revision`, tăng revision đúng một lần | Implemented |
| `POST .../scenarios/{id}/save` | DRAFT→SAVED, tạo snapshot mới; không approval role | Implemented |
| `POST .../scenarios/{id}/clone` | ID/key mới, deep-copy context/assumptions và source revision lineage | Implemented; negative key pattern phải giữ trong contract test |
| `POST .../scenarios/{id}/archive` | Archive không xóa history; archived không sửa/được dùng implicit | Implemented |
| `GET /organizations/{org}/biological/calculations` và `/{id}` | Chỉ đọc calculation snapshot; P13–P15 tạo calculation theo contract riêng | Read contract implemented; P13 create/replay implemented, P14–P15 target |
| `POST .../scenarios/{id}/calculations/validate` | Validate-only D/n/d, alpha/beta, curve; không mutation | P13 implemented |
| `POST .../scenarios/{id}/calculations` | Commit immutable BED/EQD2 snapshot; first 201, idempotent replay 200, conflicting key 409 | P13 implemented; staging gate open |
| `POST .../calculations/{id}/charts` | Rebuild chart/table preview từ calculation snapshot; `persisted=false` | P13 implemented; staging gate open |
| `GET .../calculations/{id}/export` | JSON/CSV đọc từ result snapshot, cùng dataset checksum | P13 implemented; staging gate open |

P12 không được coi là hoàn tất chỉ vì hub mở được. Trước khi chuyển sang `STAGING_VERIFIED`, phải chứng minh đồng thời: route thật tải dữ liệu thật, mutation và revision state đúng trong PostgreSQL, scope không lộ organization khác, refresh/reconnect giữ snapshot, tool chưa mở không dẫn tới route chết và P9 report integration được ghi rõ là đã làm hoặc còn target.

### Trường hợp chạy đúng P12

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P12-S01 | Organization chưa có scenario | Empty state có CTA; không seed dữ liệu giả; sáu capability card vẫn hiển thị đúng trạng thái. |
| TC-P12-S02 | Validate scenario hợp lệ | HTTP/response hợp lệ nhưng số scenario trong DB không đổi; form không mất dữ liệu. |
| TC-P12-S03 | Tạo scenario hợp lệ không có QA | Tạo DRAFT rev 1, ID/timestamp/snapshot/source được trả; không yêu cầu patient/case. |
| TC-P12-S04 | Sửa DRAFT bằng revision hiện tại | Chỉ field yêu cầu đổi; revision tăng một; snapshot mới đọc lại được. |
| TC-P12-S05 | Save DRAFT | Chuyển SAVED, tạo snapshot revision mới; bản saved không còn sửa trực tiếp. |
| TC-P12-S06 | Clone SAVED/ARCHIVED | ID/key mới, source revision cũ, assumptions/context được sao chép; sửa clone không đổi nguồn. |
| TC-P12-S07 | Search/status/include archived/history | Lọc đúng, archived bị ẩn mặc định và hiện khi yêu cầu; revision list newest-first. |
| TC-P12-S08 | Refresh/reconnect sau create/save | API trả lại cùng snapshot/revision; UI không phụ thuộc state tạm trong browser. |
| TC-P12-S09 | P14–P16 chưa available, P13 available | P13 mở đúng calculator; P14–P16 ghi `PLANNED`, không dẫn route chết và không tạo calculation giả. |

### Trường hợp lỗi và phục hồi P12

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P12-E01 | Session hết hạn/Auth unavailable | SESSION_UNAVAILABLE | Dừng request, giữ draft/filter an toàn, đăng nhập lại; không fallback anonymous. |
| TC-P12-E02 | Scenario khác tổ chức | SCENARIO_NOT_FOUND / ORGANIZATION_SCOPE_MISMATCH | 404/403 theo boundary; không lộ nội dung hoặc metadata. |
| TC-P12-E03 | Tự mang QA/patient context hoặc assumptions không hợp lệ | BIOLOGICAL_CONTEXT_INVALID | 422 field-level; không tạo mutation; chỉ nhận context explicit có provenance. |
| TC-P12-E04 | `REFERENCE` thiếu citation | BIOLOGICAL_CONTEXT_INVALID | Chặn validate/create, giữ form và yêu cầu source; không tự chèn citation. |
| TC-P12-E05 | `scenario_key` trùng hoặc clone key sai pattern | SCENARIO_KEY_CONFLICT / REQUEST_VALIDATION_FAILED | 409/422, giữ các field còn lại; không tạo bản ghi thứ hai. |
| TC-P12-E06 | Sửa đồng thời/stale expected revision | SCENARIO_REVISION_CONFLICT | Giữ draft hiện tại, tải bản mới hoặc clone; không overwrite. |
| TC-P12-E07 | Sửa/save SAVED hoặc ARCHIVED | SCENARIO_IMMUTABLE | Không đổi snapshot; hướng dẫn clone để tạo revision độc lập. |
| TC-P12-E08 | Archive lại scenario đã archived | SCENARIO_IMMUTABLE | Không tạo revision giả; vẫn xem được history. |
| TC-P12-E09 | Scenario/revision không tồn tại | SCENARIO_NOT_FOUND | Trả not-found chung, quay về list; không suy đoán ID. |
| TC-P12-E10 | Model/version cũ không chạy lại được | MODEL_VERSION_UNAVAILABLE | Mở snapshot cũ; rerun dùng model mới và result ID mới. |
| TC-P12-E11 | Module route chưa sẵn sàng | MODULE_UNAVAILABLE | Hiển thị capability; không có nút tính giả hoặc record RUNNING giả. |
| TC-P12-E12 | Database/commit timeout hoặc mất response sau commit | SCENARIO_PERSISTENCE_FAILED / MUTATION_RESULT_UNKNOWN | Query lại trạng thái/idempotency trước retry; không nhân bản scenario và không xóa draft. |

### Bất biến và điều kiện đóng P12

- **Dữ liệu phải giữ/transaction:** Save input không đồng nghĩa đã tính; result liên kết đúng input revision; clone transaction; không có QACase/patient FK bắt buộc.
- **Bàn giao:** Biological Hub/history/base contracts, capability states và independent report integration hoặc issue target rõ ràng.
- **Exit gate:** Local gates pass; staging create→validate→save→edit/clone/archive/filter/history; scope/conflict/expired-session/persistence negative; P9 report integration; không automatic QA linkage.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; C10–C16 áp dụng cho UI/capability/export; C13 phải chứng minh provenance.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-13"></a>

## P13 — BED, EQD2 và đồ thị theo tổng liều

- **Module:** MOD-11.
- **Requirement:** FR-P13-01 đến FR-P13-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P12 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Tính LQ minh bạch, kiểm tính nhất quán và export đồ thị/data từ cùng snapshot.
- **Contract:** specification §8 / SPEC-P13; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** LOCAL_VERIFIED trên working tree ngày 2026-09-08; staging E2E và release-manifest evidence vẫn mở, không suy diễn từ test local.

### Workflow P13

1. Mở scenario `SAVED` và chọn đúng scenario revision `SAVED` trong Biological namespace.
2. Nhập đủ hoặc nhập một cặp trong D/n/d; ghi tolerance và kiểm consistency ở backend.
3. Chọn alpha/beta dương, source type/reference; hiển thị formula, unit và normalized input.
4. Chọn `FIXED_N` hoặc `FIXED_D`, range/step, alpha-beta series và point limit; dựng chart/table từ một dataset.
5. Chọn `Validate only` để kiểm tra không mutation, hoặc `Calculate & save snapshot` để commit calculation idempotent.
6. Mở marker/history sau refresh, tạo chart preview mới nếu cần và export JSON/CSV từ snapshot đã commit.

### Work packages P13

- [x] P13-W01 — Pure engine LQ với finite checks, integer fractions, units và rounding chỉ ở display.
- [x] P13-W02 — Input pair deterministic; D=n*d tolerance explicit; zero-dose được phép khi n>0.
- [x] P13-W03 — Curve generator fixed-n mặc định; fixed-d dùng điểm n nguyên, range/point budget.
- [x] P13-W04 — Snapshot model/source/curve parameters; charts dùng chính dữ liệu table/export.
- [x] P13-LOCAL-VERIFY — engine/API suite, full backend, Ruff/mypy, frontend lint/typecheck/Vitest/build và migration head local pass.
- [ ] P13-STAGING-VERIFY — deploy đúng SHA; browser validate→calculate→history→chart preview→export với PostgreSQL state và no-QA-linkage evidence.
- [ ] P13-HANDOFF — sau staging, cập nhật release manifest, OpenAPI, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P13

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P13-S01 | Known answer 60 Gy/30, alpha-beta 10 | BED=72 Gy10, EQD2=60 Gy; input/output snapshot chính xác. |
| TC-P13-S02 | Known answer 30 Gy/5, alpha-beta 3 | BED=90 Gy3, EQD2=54 Gy; không làm tròn trước phép chia. |
| TC-P13-S03 | Đồ thị fixed-n | Giữ n, d=D/n thay đổi theo D; điểm marker khớp calculator cùng input. |
| TC-P13-S04 | Dose bằng 0 | n>0 và alpha/beta>0 cho BED=EQD2=0; không nhầm với input thiếu. |
| TC-P13-S05 | Chỉ nhập một cặp trong D/n/d | Đại lượng còn thiếu được suy ra deterministic; supplied và normalized input khác nhau được lưu trong snapshot. |
| TC-P13-S06 | Nhiều alpha/beta và đổi metric BED/EQD2 | Các series dùng cùng D grid; table, marker và chart không tạo giá trị riêng lệch nhau. |
| TC-P13-S07 | Save → refresh → mở history → export | Calculation cũ giữ scenario revision/model/source/checksum; export không đọc form hiện tại. |
| TC-P13-S08 | Retry sau khi client mất response | Query idempotency trả cùng calculation; không tạo record thứ hai. |

### Trường hợp lỗi và phục hồi P13

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P13-E01 | n không nguyên/<=0 hoặc alpha-beta<=0 | BIOLOGICAL_INPUT_INVALID | Chặn field; không tự thay số fraction hoặc alpha-beta. |
| TC-P13-E02 | D không bằng n*d | FRACTIONATION_INCONSISTENT | Cho chọn input nào là nguồn; không sửa thầm cả ba. |
| TC-P13-E03 | NaN/Infinity/overflow | CALCULATION_NONFINITE | Không lưu result success; trả field/model error. |
| TC-P13-E04 | Range ngược/step<=0/quá nhiều điểm | CURVE_RANGE_INVALID | Chặn curve, giữ kết quả đơn; cho chỉnh step/range. |
| TC-P13-E05 | Thiếu alpha-beta source | ALPHA_BETA_SOURCE_REQUIRED | Chọn library source hoặc explicit user override. |
| TC-P13-E06 | Tải lại mất result | CALCULATION_PERSISTENCE_FAILED | Giữ draft; chỉ hiển thị saved khi server commit, retry idempotent. |
| TC-P13-E07 | Cùng idempotency key nhưng input/model khác | CALCULATION_IDEMPOTENCY_CONFLICT | Giữ calculation cũ; cấp key mới cho calculation khác. |
| TC-P13-E08 | Scenario/revision ngoài scope hoặc scenario đã archive | SCENARIO_REVISION_NOT_FOUND / ORGANIZATION_SCOPE_MISMATCH / SCENARIO_IMMUTABLE | Không tính; không lộ metadata; clone scenario nếu cần tạo context mới. |
| TC-P13-E09 | Alpha/beta curve trùng, curve không có điểm hoặc vượt point budget | CURVE_RANGE_INVALID | Chặn toàn bộ dataset; giữ form để sửa, không lưu một phần. |
| TC-P13-E10 | Commit xong nhưng response timeout/mất mạng | CALCULATION_PERSISTENCE_FAILED / MUTATION_RESULT_UNKNOWN | Query theo idempotency trước retry; không tự tạo success giả hoặc duplicate. |

### Bất biến và điều kiện đóng P13

- **Dữ liệu phải giữ/transaction:** Tính từ input revision đã chọn; thay input làm kết quả hiện tại stale, không đổi history.
- **Bàn giao:** Calculator, curves, table/marker, known-answer fixtures và exports.
- **Exit gate local:** Known answers/invalid/curve equality/history/export API pass; limits/model assumptions có nguồn hoặc user-defined; migration `20260908_0013` và schema contract đồng bộ.
- **Exit gate staging:** Browser → API → Railway PostgreSQL phải chứng minh validate-only không mutation, calculation commit/replay không duplicate, chart preview không ghi đè history, JSON/CSV đúng checksum và route không tạo liên kết QA/patient tự động. Chỉ khi gate này cùng với release manifest pass mới chuyển P13 sang `STAGING_VERIFIED`.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-14"></a>

## P14 — So sánh phác đồ xạ trị

- **Module:** MOD-12.
- **Requirement:** FR-P14-01 đến FR-P14-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P13 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** So sánh các phương án fractionation một cách nhất quán về mô, model và context.
- **Contract:** specification §8 / SPEC-P14; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P14

1. Tạo hai phương án hoặc clone từ library/calculation.
2. Chọn mô/model và phương án baseline.
3. Validate từng phương án và compatibility giữa các phương án.
4. Tính bảng BED/EQD2, delta và chart.
5. Lưu comparison snapshot; clone thêm phương án và export.

### Work packages P14

- [ ] P14-W01 — Tách treatment option với course trong một option; không cộng các phương án thay thế.
- [ ] P14-W02 — Tái dùng P13; same tissue/model/alpha-beta group cho delta có nghĩa.
- [ ] P14-W03 — Zero denominator policy null + reason; baseline selection by stable ID.
- [ ] P14-W04 — Comparison revision/chart/export source binding; column reorder không đổi baseline.
- [ ] P14-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P14-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P14

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P14-S01 | Hai phương án giống nhau | Delta BED/EQD2 bằng 0; đổi vị trí cột không đổi kết quả. |
| TC-P14-S02 | Đổi baseline | Delta đổi dấu đúng và % dùng mẫu số baseline mới. |
| TC-P14-S03 | Ba phương án | Bảng/chart cùng values; không cộng tổng các option. |
| TC-P14-S04 | Khác alpha-beta | Hiển thị từng result riêng, cảnh báo compatibility và không xếp hạng tự động. |

### Trường hợp lỗi và phục hồi P14

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P14-E01 | Ít hơn hai phương án | COMPARISON_OPTIONS_REQUIRED | Yêu cầu thêm option; không hiển thị compare giả. |
| TC-P14-E02 | Baseline 0 | COMPARISON_PERCENT_UNDEFINED | Delta tuyệt đối hợp lệ; % null, không Infinity. |
| TC-P14-E03 | Một option input sai | COMPARISON_OPTION_INVALID | Chỉ rõ cột/field, không dùng 0 thay input sai. |
| TC-P14-E04 | Model/tissue khác nhau | COMPARISON_CONTEXT_MISMATCH | Không tính delta như cùng quantity; group hoặc sửa context explicit. |
| TC-P14-E05 | Xóa option đang làm baseline | COMPARISON_BASELINE_REQUIRED | Yêu cầu chọn baseline mới trước lưu/tính. |
| TC-P14-E06 | Vượt số option | COMPARISON_LIMIT_EXCEEDED | Giới hạn rõ; không truncate im lặng. |

### Bất biến và điều kiện đóng P14

- **Dữ liệu phải giữ/transaction:** Một comparison dùng cùng revision của toàn bộ options; không ghép result cũ/mới.
- **Bàn giao:** Multi-option editor/table/chart/compatibility/history/export.
- **Exit gate:** Known delta, zero baseline, mismatched context và baseline reorder/delete tests pass.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-15"></a>

## P15 — Re-irradiation, recovery và bù fraction

- **Module:** MOD-13.
- **Requirement:** FR-P15-01 đến FR-P15-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P13, P14 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Tính scenario nhiều course và các lịch thay thế với giả định rõ ràng.
- **Contract:** specification §8 / SPEC-P15; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P15

1. Chọn Re-irradiation hoặc Fraction Compensation trong toolkit.
2. Nhập các course/đã thực hiện và phương án dự kiến cho đúng mô.
3. Chọn no-recovery hoặc recovery explicit; xác nhận thời gian nếu model cần.
4. Tính từng course và cumulative scalar/alternative schedule.
5. So sánh scenario, sensitivity và export assumptions/result; spatial chỉ khi contract dữ liệu đủ.

### Work packages P15

- [ ] P15-W01 — Course/tissue matrix; dose của mô/OAR explicit, không copy prescription target cho mọi OAR.
- [ ] P15-W02 — Khóa recovery model user-defined fraction tại evaluation time; không áp recovery hai lần.
- [ ] P15-W03 — LQ per-fraction sum khi nonuniform; schedule/time-model optional explicit có source/version.
- [ ] P15-W04 — UI scalar/spatial capability; không bật spatial bằng ghi chú registration; actual transform/resampling tests thuộc contract §6.
- [ ] P15-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P15-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P15

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P15-S01 | Hai course cùng alpha-beta, no recovery | BED_total=sum BED_i; EQD2_total=BED_total/(1+2/a); từng contribution hiển thị. |
| TC-P15-S02 | Recovery explicit | Course cũ nhân (1-r_i) đúng một lần; course mới r=0; baseline no-recovery vẫn hiện. |
| TC-P15-S03 | Fraction không đều | BED=sum d_j*(1+d_j/a), không dùng d trung bình để thay tổng. |
| TC-P15-S04 | Interruption không time model | Hiển thị lịch/thời gian và LQ; không tự thêm repopulation correction. |
| TC-P15-S05 | Clone alternative schedule | Delivered prefix giữ nguyên, chỉ remaining proposal thay; history cũ còn đủ. |

### Trường hợp lỗi và phục hồi P15

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P15-E01 | Thiếu ngày cho model phụ thuộc thời gian | COURSE_INTERVAL_REQUIRED | Chặn model đó; no-recovery LQ không phụ thuộc thời gian vẫn xem được. |
| TC-P15-E02 | Recovery ngoài 0–1/không source | RECOVERY_ASSUMPTION_INVALID | Chặn field hoặc yêu cầu user-defined source, không auto-preset. |
| TC-P15-E03 | Cộng EQD2 khác mô/alpha-beta | CUMULATIVE_CONTEXT_MISMATCH | Tách nhóm theo mô/alpha-beta, không cộng scalar sai nghĩa. |
| TC-P15-E04 | Delivered vượt planned/negative counts | FRACTION_SCHEDULE_INVALID | Yêu cầu chỉnh lịch; không sinh remaining âm. |
| TC-P15-E05 | Registration thiếu/sai hướng | SPATIAL_ACCUMULATION_UNAVAILABLE | Không trả cumulative voxel dose; giữ scalar scenario riêng có nhãn. |
| TC-P15-E06 | Dose mô thiếu, chỉ có target prescription | TISSUE_DOSE_REQUIRED | Không coi prescription là OAR dose; yêu cầu metric và dose explicit. |
| TC-P15-E07 | Gián đoạn bị đếm trùng | INTERRUPTION_OVERLAP | Kiểm ngày/fraction IDs; không cộng hai lần cùng thời đoạn. |
| TC-P15-E08 | Solver cho kết quả n không nguyên | FRACTION_COUNT_NONINTEGER | Hiển thị estimate nếu có; alternative thực tế phải do user chọn n nguyên và tính lại. |

### Bất biến và điều kiện đóng P15

- **Dữ liệu phải giữ/transaction:** Input snapshot gồm delivered schedule và assumptions; calculation không mutate treatment records.
- **Bàn giao:** Re-irradiation + compensation screens, model contract, timeline, sensitivity/compare, golden/error suite.
- **Exit gate:** No-recovery/recovery, nonuniform fractions, missing time/context, compensation schedule và independent export pass; spatial không giả lập.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-16"></a>

## P16 — Dose limits, phác đồ điều trị và Knowledge Library

- **Module:** MOD-14.
- **Requirement:** FR-P16-01 đến FR-P16-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P12, P13, P14, P15 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Tra cứu và tái sử dụng nội dung có nguồn, context và version trong công cụ tính toán.
- **Contract:** specification §8 / SPEC-P16; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P16

1. Lọc bệnh lý, kỹ thuật, fractions, mô và metric.
2. Mở entry để xem nguồn và phạm vi áp dụng.
3. Tạo nội dung nội bộ hoặc clone, chỉnh và lưu version.
4. User chọn dùng entry vào calculator, review values/source.
5. Cập nhật library hoặc archive, mở lại calculation cũ giữ source version.

### Work packages P16

- [ ] P16-W01 — Schema typed metric/unit/volume/context; validated citations không biến URL thành bằng chứng đã kiểm tra.
- [ ] P16-W02 — Search filters + version/clone/import preview/dedup/source quality states.
- [ ] P16-W03 — Ingestion rich text/attachments safe; link external source không tự fetch URL private.
- [ ] P16-W04 — Calculator prefill có preview/diff và pinned library version; no auto overwrite khi entry cập nhật.
- [ ] P16-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P16-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P16

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P16-S01 | Tìm constraint đúng context | Kết quả match disease/fractions/technique và metric unit; unknown không coi wildcard. |
| TC-P16-S02 | Dùng entry vào calculator | Chỉ sau user chọn; source version được snapshot, override có nhãn. |
| TC-P16-S03 | Version mới | Calculation/report cũ vẫn dùng nội dung version cũ. |
| TC-P16-S04 | Hai nguồn mâu thuẫn | Hiển thị riêng cùng applicability; không tự chọn giới hạn thấp nhất. |

### Trường hợp lỗi và phục hồi P16

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P16-E01 | Thiếu nguồn tham khảo | KNOWLEDGE_SOURCE_REQUIRED | Bổ sung citation hoặc đánh dấu nội bộ/user-defined, không gán guideline giả. |
| TC-P16-E02 | Gy/%/cc không tương thích | DOSE_LIMIT_UNIT_INVALID | Chặn phép so sánh; yêu cầu metric/unit rõ. |
| TC-P16-E03 | URL hỏng | REFERENCE_LINK_UNAVAILABLE | Giữ citation metadata và thông báo link; không xóa entry. |
| TC-P16-E04 | Import schema/duplicate lỗi | KNOWLEDGE_IMPORT_INVALID | Preview từng row, commit các row hợp lệ theo lựa chọn; giữ lỗi row. |
| TC-P16-E05 | Applicability không khớp | DOSE_LIMIT_NOT_APPLICABLE | Hiển thị tham khảo riêng, không gán PASS/FAIL tự động. |
| TC-P16-E06 | Script/markup không an toàn | KNOWLEDGE_CONTENT_INVALID | Sanitize content; không thực thi công thức text như code. |

### Bất biến và điều kiện đóng P16

- **Dữ liệu phải giữ/transaction:** Published version immutable; reference selection copied to calculation snapshot, not live pointer only.
- **Bàn giao:** Library/editor/version comparison/source preview; schema fixtures và calculator integration.
- **Exit gate:** Filter/context/source/version/import/override pass; không seed bảng giới hạn lâm sàng không nguồn.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-17"></a>

## P17 — Visual Dose, DVH và structure review

- **Module:** MOD-15.
- **Requirement:** FR-P17-01 đến FR-P17-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P6, P8, P9, P11 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Xem dose trên geometry đúng và tính DVH/metric có volume, unit, coverage.
- **Contract:** specification §8 / SPEC-P17; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P17

1. Chọn dataset: dose-only hoặc dose+CT; DVH cần dose+structures.
2. Preflight frame/geometry/reference/coverage.
3. Chọn ROI, manual mapping và rasterization/resampling.
4. Worker tạo DVH, metric, coverage/uncertainty và overlay.
5. Review slices/curve/metric, lưu snapshot và report.

### Work packages P17

- [ ] P17-W01 — Coordinate affine LPS, direction cosines, z offsets, transform direction và units.
- [ ] P17-W02 — Contour rasterization holes/disjoint/partial volume; explicit voxel weighting/convergence.
- [ ] P17-W03 — DVH bin/quantile definitions, Dxcc/Vx units/inequalities và coverage policy.
- [ ] P17-W04 — Viewport orientation/crosshair/legend, worker large payloads và report source binding.
- [ ] P17-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P17-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P17

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P17-S01 | Uniform dose box | ROI 10 cc trong dose 2 Gy: Dmean=2, D95=2 Gy, V2Gy=100% theo ≥ convention. |
| TC-P17-S02 | Dose-only view | Dose plane hiển thị không cần CT/RTSTRUCT; không gọi nó anatomy overlay. |
| TC-P17-S03 | Hai ROI trùng tên | Chọn theo ROI ID, giữ mapping riêng; không merge tự động. |
| TC-P17-S04 | Geometry đổi spacing | Resampling explicit và golden sai số trong budget theo fixture, ghi method. |

### Trường hợp lỗi và phục hồi P17

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P17-E01 | DVH thiếu RTSTRUCT | DVH_INPUT_REQUIRED | Chặn DVH; dose-only view vẫn có thể xem. |
| TC-P17-E02 | Frame/reference mismatch | DICOM_FRAME_MISMATCH | Không overlay mặc định; yêu cầu transform valid hoặc dataset đúng. |
| TC-P17-E03 | ROI rỗng/volume 0 | DVH_EMPTY_STRUCTURE | Metric null có reason; không PASS/0 Gy. |
| TC-P17-E04 | Contour ngoài dose grid | DVH_INCOMPLETE_COVERAGE | Hiển thị coverage, chặn kết luận full-ROI; không gán dose ngoài grid bằng 0. |
| TC-P17-E05 | Contour/self-intersection unsupported | CONTOUR_GEOMETRY_INVALID | Chỉ rõ ROI/slice; không silently drop contour. |
| TC-P17-E06 | Compressed codec/oblique unsupported | DICOM_CAPABILITY_UNSUPPORTED | Báo capability; không render geometry giả. |
| TC-P17-E07 | Thiếu CT cho anatomy | ANATOMY_INPUT_REQUIRED | Chỉ dose-only; không overlay lên ảnh không liên quan. |

### Bất biến và điều kiện đóng P17

- **Dữ liệu phải giữ/transaction:** Transform + rasterization + source checksum pinned in one run; result commit sau all required artifacts.
- **Bàn giao:** Dose/DVH viewer, affine/rasterization tests, report integration và benchmarks.
- **Exit gate:** Geometry, uniform/box/sphere/holes/coverage, Dx/Vx units và staging DVH E2E pass. P17 bắt buộc cho mục tiêu toàn dự án, tùy chọn chỉ cho R1 sớm.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-18"></a>

## P18 — Kiểm thử tích hợp, độ bền và pilot

- **Module:** MOD-16.
- **Requirement:** FR-P18-01 đến FR-P18-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P11, P16, P17 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Chứng minh các module phối hợp đúng, phục hồi được và có evidence cho release candidate.
- **Contract:** specification §8 / SPEC-P18; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P18

1. Khóa release candidate và data fixtures.
2. Chạy E2E các hành trình R1/R2/R3.
3. Thử offline/restart/concurrency/backup-restore trong staging.
4. Đo hiệu năng và ghi chi phí với workload cụ thể.
5. Pilot dữ liệu được phép; biến lỗi thành regression; chốt candidate đạt gate.

### Work packages P18

- [ ] P18-W01 — Test matrix theo browser/device/timezone/tenant/dataset, ưu tiên cross-boundary failures.
- [ ] P18-W02 — Fault injection API/DB/Redis/storage/worker/renderer trên staging có restore plan.
- [ ] P18-W03 — Backup database+objects+manifest, restore isolated và kiểm lineage/checksum.
- [ ] P18-W04 — Bug triage SEV0–3, regression before close, record limitations và candidate evidence.
- [ ] P18-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P18-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P18

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P18-S01 | QA journey đầy đủ | Auth→case→upload→validate→Gamma/Machine QA→report→trend→protocol version hoạt động. |
| TC-P18-S02 | Biological journey | Library→calculator→comparison→re-irradiation→report không tự liên kết QA. |
| TC-P18-S03 | Restore | Counts, checksums, source refs và old report download đúng; đo RPO/RTO thực. |
| TC-P18-S04 | Fault phục hồi | Không mất run đã accepted, không duplicate result; UI thoát spinner và hướng dẫn retry. |

### Trường hợp lỗi và phục hồi P18

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P18-E01 | Golden vượt tolerance | RESULT_REGRESSION | Chặn candidate; ghi input/engine diff, bổ sung regression và sửa trước rerun. |
| TC-P18-E02 | Restore thiếu object | RESTORE_INCOMPLETE | Không coi backup là đạt; đối soát manifest và phục hồi object missing. |
| TC-P18-E03 | Queue replay trùng result | DUPLICATE_RESULT | Sửa unique/fencing; replay lại cùng event sequence. |
| TC-P18-E04 | Tải vượt budget | PERFORMANCE_GATE_FAILED | Profile bottleneck, điều chỉnh thuật toán/limits, đo lại cùng workload. |
| TC-P18-E05 | Pilot dataset không hỗ trợ | PILOT_CAPABILITY_GAP | Báo profile cụ thể và giữ input; thêm adapter/test, không sửa fixture để ép PASS. |
| TC-P18-E06 | Bằng chứng khác release SHA | RELEASE_EVIDENCE_MISMATCH | Chạy lại phần chịu ảnh hưởng trên candidate đúng. |

### Bất biến và điều kiện đóng P18

- **Dữ liệu phải giữ/transaction:** Fault test có điều kiện bắt đầu/kết thúc, tài nguyên mục tiêu và cleanup; không thử lỗi phá dữ liệu trên production.
- **Bàn giao:** Integrated test pack, benchmark report, restore/pilot report, RC manifest.
- **Exit gate:** Toàn bộ MUST tests pass, không còn SEV0/1; restore/rollback/performance evidence; remaining limitations không vi phạm exit scope.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-19"></a>

## P19 — Production website và truy cập từ xa

- **Module:** MOD-16.
- **Requirement:** FR-P19-01 đến FR-P19-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P18 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Phát hành đúng release qua HTTPS và xác nhận hành trình người dùng ở production.
- **Contract:** specification §8 / SPEC-P19; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P19

1. Đối chiếu release manifest và production configuration.
2. Backup, kiểm restore point rồi chạy migration compatible.
3. Deploy các service đúng candidate và public build config production.
4. Kiểm health/schema/queue/Auth rồi remote E2E có synthetic data.
5. Ghi release/monitoring; rollback nếu gate lỗi theo điều kiện đã định.

### Work packages P19

- [ ] P19-W01 — Promote cùng source/artifact provenance; web public config khác environment phải rebuild và ghi digest riêng.
- [ ] P19-W02 — Effective settings matrix web/API/worker; migrations single runner, private DB/Redis.
- [ ] P19-W03 — DNS/TLS/CORS/SPA fallback/Supabase redirects/build-time vars smoke.
- [ ] P19-W04 — External browser/device journeys; version mismatch checks, rollback rehearsal and monitoring hooks.
- [ ] P19-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P19-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P19

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P19-S01 | Release đúng phiên bản | Web/API/worker schema/engine theo manifest; không chỉ xem Online. |
| TC-P19-S02 | Deep-link từ mạng ngoài | Login/callback/reload route/app và export/download hoạt động trên HTTPS. |
| TC-P19-S03 | Job qua reconnect | Accepted run tiếp tục; result/history nhìn thấy lại sau browser refresh. |
| TC-P19-S04 | Rollback compatible | Bản trước phục vụ schema đã migrate an toàn hoặc restore theo runbook; evidence rõ. |

### Trường hợp lỗi và phục hồi P19

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P19-E01 | Domain DNS/TLS chưa ready | PUBLIC_DOMAIN_NOT_READY | Không tuyên bố URL custom hoàn tất; dùng URL Railway đã kiểm hoặc sửa DNS/TLS. |
| TC-P19-E02 | Web config sai env | PUBLIC_BUILD_CONFIG_MISMATCH | Rebuild public config đúng; không copy secret vào VITE. |
| TC-P19-E03 | Migration hoặc schema không tương thích | RELEASE_SCHEMA_FAILED | Không promote các consumer không tương thích; giữ last good hoặc restore theo runbook. |
| TC-P19-E04 | API cũ/web mới 404 | RELEASE_VERSION_MISMATCH | Đối chiếu từng service SHA/API base; deploy tương thích hoặc rollback. |
| TC-P19-E05 | Health 200 nhưng workflow lỗi | REMOTE_E2E_FAILED | Release chưa đạt; phân loại lỗi bằng correlation/request và sửa. |
| TC-P19-E06 | Usage vượt budget | RESOURCE_BUDGET_EXCEEDED | Ghi usage thực/alert và điều chỉnh capacity; không tuyên bố credit 5 USD đủ cho mọi service. |

### Bất biến và điều kiện đóng P19

- **Dữ liệu phải giữ/transaction:** Migration expand/contract; không rollback DB bằng destructive downgrade tự động; release gate trên từng service.
- **Bàn giao:** Production URL, remote test evidence, deployment/rollback/runbook và user guide.
- **Exit gate:** HTTPS + remote workflows + Auth + private dependencies + versions + backup/rollback/alerts đều kiểm chứng.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

<a id="phase-20"></a>

## P20 — Gói vận hành ban đầu và cải tiến liên tục

- **Module:** MOD-16.
- **Requirement:** FR-P20-01 đến FR-P20-04, xem business-analysis §21.3.
- **Dependency/entry gate:** P19 đã có contract ổn định và evidence cho phần được sử dụng. Không dùng record/secret của môi trường khác.
- **Mục tiêu:** Bàn giao cách theo dõi, khôi phục và cập nhật hệ thống sau release.
- **Contract:** specification §8 / SPEC-P20; các contract chung §2–§7 áp dụng khi có liên quan.
- **Owner thực thi:** người/agent phụ trách module ghi tên trong checkpoint; người dùng cung cấp dữ liệu hoặc đánh giá workflow khi cần, không có cấp phê duyệt theo chức danh.
- **Trạng thái test v2:** NOT_RUN cho đến khi có evidence theo ID dưới đây; không kế thừa PASS tự động từ test cũ.

### Workflow P20

1. Thiết lập monitor và backup schedule đã chọn.
2. Thử một alert và một restore để xác nhận runbook dùng được.
3. Bàn giao hướng dẫn thường ngày và xử lý sự cố.
4. Triage bug/dataset mới thành issue + regression.
5. Release maintenance qua staging với manifest và ghi kết quả.

### Work packages P20

- [ ] P20-W01 — Tạo operational dashboard và alert test bằng sự kiện synthetic.
- [ ] P20-W02 — Thiết lập backup retention/runbook; restore schedule và evidence template.
- [ ] P20-W03 — User guides theo task, incident taxonomy và support correlation without secrets.
- [ ] P20-W04 — Dependency/engine updates có impact set, staging tests và compatibility rollback.
- [ ] P20-VERIFY — chạy ma trận S/E và C áp dụng, ghi result/evidence và linked FR; đối chiếu design/data/API.
- [ ] P20-HANDOFF — cập nhật contract/OpenAPI khi có thay đổi, migration/release notes, checkpoint và backlog còn lại.

### Trường hợp chạy đúng P20

| Test ID | Given/When — tình huống trong workflow | Then — kết quả phải kiểm chứng |
| :--- | :--- | :--- |
| TC-P20-S01 | Alert thử | Alert đến kênh đã cấu hình và người vận hành biết bước xử lý; ghi thời gian. |
| TC-P20-S02 | Backup định kỳ | Lần chạy thành công có manifest/checksum; restore drill đúng RPO/RTO mục tiêu. |
| TC-P20-S03 | Maintenance release | Bug có regression trước đóng; source/result version cũ vẫn truy cập. |
| TC-P20-S04 | Bàn giao | Người phụ trách thực hiện được runbook bằng hướng dẫn, không cần hỏi lại tác giả. |

### Trường hợp lỗi và phục hồi P20

Mã ở cột “Phân loại” là tên contract mục tiêu cho tình huống; không mặc định đã là error code trong API hiện tại. Khi hiện thực, dùng code cụ thể đã tồn tại nếu cùng nghĩa và cập nhật OpenAPI/mapping; không gửi chuỗi OR làm một code API.

| Test ID | Trigger — điều kiện lỗi | Phân loại | Expected và đường phục hồi |
| :--- | :--- | :--- | :--- |
| TC-P20-E01 | Backup failed/quá retention | BACKUP_POLICY_FAILED | Alert; chạy lại và kiểm restore point; không xóa last good backup. |
| TC-P20-E02 | Alert không được nhận | ALERT_DELIVERY_FAILED | Đổi cấu hình kênh đã cho phép và test lại; không coi dashboard màu xanh là đã alert. |
| TC-P20-E03 | Thiếu capacity/storage gần đầy | CAPACITY_WARNING | Đo và điều chỉnh retention/capacity theo kế hoạch, không xóa hồ sơ tùy ý. |
| TC-P20-E04 | Engine update đổi số | ENGINE_RESULT_CHANGED | Version mới + golden diff và release notes; không ghi đè old result. |
| TC-P20-E05 | Incident lặp lại | RECURRING_INCIDENT | Root-cause + regression + runbook update, không chỉ restart liên tục. |

### Bất biến và điều kiện đóng P20

- **Dữ liệu phải giữ/transaction:** Maintenance không rewrite history; backup cleanup chỉ sau retention và có bản phục hồi đã kiểm.
- **Bàn giao:** Monitoring+backup cấu hình, alert/restore evidence, guides, ownership và maintenance backlog.
- **Exit gate:** Gói vận hành ban đầu có config thực, alert test, backup+restore evidence và người phụ trách; vận hành liên tục không có trạng thái hoàn tất vĩnh viễn.
- **Kiểm tra chéo:** C03–C09 về scope, retry, đồng thời, mất mạng, session và version phải có evidence hoặc lý do không áp dụng; thêm C10–C16 theo module.
- **Nếu gate fail:** mở issue với testcase thất bại, giữ evidence/bản dữ liệu trước đó và sửa package liên quan; không thay expected để hợp thức hóa output. Có thể làm task độc lập tiếp theo, nhưng phase vẫn mở.

### 4.1. Protocol thực thi một phase (bắt buộc)

Một phase không được thực hiện theo kiểu “làm xong code rồi xem có chạy không”. Người thực thi phải tạo một phase packet và đi qua đủ các bước dưới đây. Có thể triển khai W01–W04 song song khi dependency không chồng chéo, nhưng `VERIFY` và `HANDOFF` chỉ chạy sau khi tất cả package liên quan đã có artifact.

1. **Khóa đầu vào:** ghi branch, commit/SHA, phiên bản `business-analysis.md`, `specification.md`, `technical-specification.md`, môi trường và fixture. Nếu tài liệu hoặc source thay đổi giữa chừng, tạo revision packet mới.
2. **Kiểm entry gate:** xác nhận dependency, database schema, Auth context, design screen, service và dữ liệu mẫu đúng phase. Entry fail thì phase `BLOCKED`/`IN_PROGRESS`, không chạy test như thể đã sẵn sàng.
3. **Đọc contract:** lấy FR từ business analysis, field/HTTP/error/transaction từ specification và boundary/module từ technical specification. Mọi điểm không khớp trở thành issue trước khi sửa code.
4. **Triển khai theo work package:** mỗi W phải có commit nhỏ có thể truy nguyên, test ID, migration/API/UI/engine artifact tương ứng và điều kiện rollback. Không gom thay đổi không liên quan vào một package.
5. **Kiểm local:** chạy success, error, boundary và regression của phase; chạy lint/typecheck/build/migration phù hợp. Test pass chỉ chứng minh assertion đã chạy trên environment đó.
6. **Kiểm tích hợp:** xác minh đường đi đầy đủ từ UI/API đến database/object storage/queue/worker/renderer nếu phase có các thành phần này. Không thay bằng gọi một endpoint đơn lẻ.
7. **Kiểm environment mục tiêu:** với P2–P3 và P6–P19, chạy lại trên service/environment đúng manifest; ghi service SHA, schema revision, engine/renderer version, request/run ID và thời điểm.
8. **Đối chiếu evidence:** so sánh expected với observed, lưu log/screenshot/response/hash có redaction; evidence không được chứa token, password, database URL hoặc dữ liệu patient không cần thiết.
9. **Quyết định exit:** chỉ chuyển trạng thái theo evidence thực tế. Thiếu một MUST case, còn SEV0/SEV1, migration chưa đúng, data scope chưa chứng minh hoặc workflow browser chưa đi hết thì phase vẫn mở.
10. **Handoff:** cập nhật ba tài liệu, `implementation-progress.md`, OpenAPI/migration/release notes, issue backlog và `next_exact_action`. Handoff phải đủ để người khác tiếp tục mà không đoán phase hoặc chạy lại bước đã đạt.

Template phase packet tối thiểu:

~~~yaml
phase: Pxx
phase_version: "2.5"
status: IN_PROGRESS
branch: "codex/<branch>"
source_commit: "<sha>"
business_analysis_version: "0.11"
specification_version: "1.5"
technical_specification_version: "1.3"
entry_gate:
  dependencies: []
  schema_revision: "<revision-or-null>"
  environment: "local|staging|production|not-applicable"
work_packages:
  - id: Pxx-W01
    commit: "<sha>"
    requirements: [FR-Pxx-01]
    tests: [TC-Pxx-S01, TC-Pxx-E01]
verified_tests:
  success: []
  error: []
  boundary: []
  regression: []
failed_tests: []
not_run_tests: []
deployment_manifest: null
evidence:
  - path: "<path>"
    kind: "test|api|browser|migration|log|hash|screenshot"
    redacted: true
    captured_at: "<ISO-8601>"
exit_decision: "OPEN|LOCAL_VERIFIED|STAGING_VERIFIED|DONE-v2|BLOCKED"
open_issues: []
next_exact_action: "<one concrete action>"
definition_of_ready:
  - "Entry dependencies, source SHA, schema and fixtures identified"
definition_of_done:
  - "Required S/E/C assertions, integration path, invariant and evidence pass"
rollback_or_recovery: "<safe recovery/rollback action and evidence>"
~~~

### 4.2. Phase packet và đầu ra bắt buộc P0–P20

| Phase | Artifact phải tạo/cập nhật | Hành trình tích hợp tối thiểu | Khi lỗi xảy ra | Phase sau chỉ được mở khi |
| :--- | :--- | :--- | :--- | :--- |
| P0 | Baseline snapshot, FR/MOD/route/contract/test registry, decision log, gap list | Source → registry → traceability → checkpoint | Dừng baseline sai; ghi `DOCUMENT_CONFLICT`/`EVIDENCE_MISSING`, không sửa lịch sử | Không còn xung đột phạm vi chưa có quyết định và mọi FR có link |
| P1 | Lock/runtime report, Compose run, migration report, CI result, setup guide | Clean clone → services → migrate/seed → API/web → tests/build | Sửa dependency/port/env/migration đúng layer; giữ log lỗi | Clean setup/restart/migration/CI tái lập được |
| P2 | Redacted deployment manifest, Auth/DB contract, schema/readiness evidence, rollback note | Railway source → build → pre-deploy migration → health/ready → JWT | Giữ last-good; phân biệt build/process/driver/schema/Auth/config drift | Staging dùng DB đúng environment, schema đúng và JWT negative/positive pass |
| P3 | App-shell route map, Auth state matrix, onboarding evidence, dashboard contract | Deep-link → session → bootstrap → membership/onboarding → dashboard → logout | Clear cache/refresh bounded; không biến outage thành no-organization | Existing member, first-use, expired/offline/deep-link đều có hành vi |
| P4 | Org/site/machine/member API/UI, migration, audit evidence | Create → rename/archive/restore/invite → history → cross-scope check | Conflict giữ draft; mutation unknown phải query trước retry | Stable ID, scope, equal-member workflow và lifecycle pass |
| P5 | Folder tree/case contract, cycle/name/move tests, search/page evidence | Nested folder → case → filter/search → move/archive/restore | Atomic move; không xóa history hoặc trả page giả | Tree, case, search, archive/restore và deep-link pass |
| P6 | Artifact/manifest/validation schema, fixture hashes, object probe, checksum evidence | Browser upload → object → DB manifest → validation → signed download | Reconcile object/DB; file invalid không vào engine; retry từng file | Byte round-trip, type/role/UID/geometry/negative upload pass |
| P7 | Protocol/rule snapshot, run/result schema, boundary report, trend projection | Case → protocol → draft → evaluate → result → rerun/compare | Giữ draft/run cũ; unit/rule error không tạo PASS | Rule boundary, N/A/missing/unit, immutable rerun/compare pass |
| P8 | Gamma profile/capability, DICOM fixtures, oracle report, queue/lease/attempt report | Validated input → preflight → queue → worker → result → retry/compare | Bounded retry/dead-letter/fencing; no-candidate và resource fail có chủ đích | 2D/3D/reference, oracle, failure injection, resource/large-input theo scope pass |
| P9 | Template/block/revision schema, renderer fixtures, exports/hash, visual review | Source/scenario → builder → snapshot → render → download/history | Revision conflict giữ draft; renderer/storage fail không sửa source | Full customization, Unicode/long report, deterministic export/retry pass |
| P10 | Trend schema/migration, projection/rebuild report, baseline/event history, chart/export evidence | Machine QA result → projection → filter/aggregate → marker/baseline → drill-down/export | Tách incompatible series; 413/409/422 đúng; rebuild idempotent | S01–S08/E01–E12, large-series budget, source/export revalidation và staging workflow pass |
| P11 | Protocol library models/version rules, source/citation fixtures, compare report, migration `20260908_0011` | Resolve org → search/detail → new/clone → validate-only → DRAFT → ACTIVE → consumer snapshot → compare/archive | Không cho version trùng/archived/unsupported; field error; conflict giữ draft; persistence uncertain query trước retry; old run giữ snapshot | S01–S09/E01–E16, C03–C16 áp dụng, P7/P8/P9/P10 consumer và staging browser/source evidence pass |
| P12 | Biological scenario namespace, hub routes, calculation history, capability states | Biological hub → tool → scenario → calculation → history/export | Không gắn QACase tự động; model unavailable có capability error | Scenario độc lập, context/source/model snapshot và route states pass |
| P13 | BED/EQD2 engine, model/input schema, curve dataset, known-answer report | SAVED scenario revision → D/n/d + alpha/beta → validate-only → calculate/replay → curve/table/marker → history/export | Không clamp hoặc đổi input; invalid range/precision, stale/archived revision, idempotency conflict hoặc persistence uncertainty không lưu success | Local engine/API/UI/migration gates đã pass; staging phải chứng minh DB snapshot, no duplicate, chart preview/export và no-QA linkage |
| P14 | Comparison model/options, delta rules, chart/table/export fixture | 2–10 options → common context → calculate → baseline/delta → export | Option/context/zero baseline fail rõ; null không biến thành zero | Absolute/percent comparison cùng revision/context và no-truncate pass |
| P15 | Course/recovery/interruption/scenario schema, assumptions/sensitivity, compensation report | Courses → tissue/model/recovery → cumulative → interruption → alternatives/export | Thiếu spatial data không giả lập voxel; lịch overlap/invalid bị chặn | Scalar/recovery/sensitivity/compensation error cases và warnings pass |
| P16 | Library schema/citation/import report, version/applicability matrix | Search → source/applicability → clone/publish → explicit scenario use | No source/invalid unit/script/link lỗi; không gán clinical PASS/FAIL | Search/no-match, citation, immutable version và explicit-use pass |
| P17 | Geometry capability matrix, dose/structure fixtures, DVH/profile result | Select datasets → frame/grid/ROI validation → overlay → metric/DVH/export | Dose-only fallback; frame/ROI/codec/coverage fail an toàn | Supported geometry, unsupported/coverage/ROI negative và source drill-down pass |
| P18 | Release candidate manifest, integrated test matrix, load/failure/restore/pilot log | RC → E2E → failure/load → backup/restore → pilot → regression | Giữ evidence/fixture; mở issue và không sửa expected | MUST E2E, restore, performance budget, pilot regression và no SEV0/1 |
| P19 | Production manifest, DNS/TLS/Auth/CORS check, promotion/rollback record | Backup → migrate → deploy services → remote E2E → monitor/rollback rehearsal | Không promote partial; rollback last-good và giữ data | Public HTTPS workflow, versions, dependencies, backup/rollback pass |
| P20 | Monitor/alert config, backup/restore runbook, guide, incident/regression log | Alert → triage → backup/restore → maintenance release → post-check | Không xóa last-good; incident lặp lại phải RCA + regression | Initial operations package có alert/restore/owner/evidence; backlog rõ |

### 4.3. Thứ tự kiểm thử và nguyên tắc mở lại phase

Mỗi phase chạy theo thứ tự: **schema/migration → unit/domain → API contract → integration/dependency → browser E2E → recovery/failure injection → performance/volume → evidence audit**. Không chạy load hoặc browser trên candidate chưa qua schema/API contract. Test failure phải ghi `expected`, `observed`, input/fixture hash, commit, environment và owner; không sửa expected để biến lỗi thành PASS.

Phase phải mở lại hoặc hạ trạng thái khi có một trong các sự kiện sau:

- thay đổi field, unit, error code, route, migration, engine/renderer hoặc Auth/DB topology;
- phát hiện cross-organization access, source lineage sai, duplicate result, mất dữ liệu hoặc kết quả không tái hiện;
- deployment chạy SHA/schema/config khác evidence đã ghi;
- một dependency downstream thay đổi làm invalid contract cũ;
- pilot/production phát hiện lỗi mới có thể ảnh hưởng cùng assertion.

Khi mở lại, giữ nguyên evidence cũ ở dạng lịch sử, tạo revalidation packet, chạy regression trực tiếp liên quan và chỉ nâng trạng thái sau khi candidate mới được xác minh. `DONE-v2` là trạng thái có thể bị thu hồi khi contract thay đổi; không dùng chữ DONE như một tuyên bố hệ thống không còn lỗi.

### 4.4. Execution ledger P0–P20 — bảng điều khiển để không bỏ sót phase

Bảng này là chỉ mục điều hành ngắn gọn; mỗi phase vẫn phải đọc đầy đủ `Workflow`, `Work packages`, `Trường hợp chạy đúng`, `Trường hợp lỗi và phục hồi` và `Bất biến/điều kiện đóng` ngay bên dưới. Người thực thi không được nhảy thẳng tới cột “đầu ra” mà bỏ qua negative test. Một dòng chỉ được đánh dấu hoàn tất khi có đủ cả happy-path evidence và failure/recovery evidence được yêu cầu.

| Phase | Entry gate và hành động đầu tiên | Workflow chạy đúng bắt buộc | Lỗi/biên bắt buộc phải cố ý kiểm | Evidence bắt buộc và cách phục hồi | Điều kiện mở khóa phase sau |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | Khóa phiên bản tài liệu, source, Stitch/Railway inventory và gap list | Đọc → lập FR/MOD/route → map contract/test/evidence → quyết định gap → checkpoint | `DOCUMENT_CONFLICT`, `DESIGN_REFERENCE_STALE`, `EVIDENCE_MISSING`, `ENVIRONMENT_MISMATCH` | Decision log, traceability, source hashes; giữ lịch sử và rebaseline, không sửa PASS cũ | 100% FR có phase/contract/test/owner; không còn scope conflict chưa quyết định |
| P1 | Clone sạch, đọc lockfile/env contract, kiểm Docker/runtime | Services → migration → synthetic seed → API/web → test/lint/build/OpenAPI → restart | Dependency/lock lệch, port bận, env thiếu, migration fail, build contract fail | Setup report, migration current, CI artifact; sửa đúng layer và chạy lại từ checkpoint | Clean setup, restart, DB upgrade và CI lặp lại được |
| P2 | Đối chiếu đúng Railway project/environment/service và Supabase project | Source/root/Dockerfile → pre-deploy migration → health → ready/schema → JWT/Auth → manifest | Railpack/source, psycopg scheme, bind/PORT, schema thiếu, JWKS/Auth, config drift | Redacted deployment manifest, health/ready/version, migration log; giữ last-good, không promote khi partial | Staging API/DB/Auth đúng environment; negative JWT và schema gate pass |
| P3 | Web build có public Auth/API config; Auth redirect đã allowlist | Deep-link → sign-in/recovery → bootstrap → onboarding hoặc workspace → dashboard → logout/expiry | Credential/recovery/session/membership/config/API/CORS/offline | Browser state matrix, bootstrap response, cache-clear evidence; refresh bounded, login lại, không tự gán org | Existing member, first-use, expired session, offline và deep-link pass |
| P4 | Organization context và schema hierarchy đã sẵn sàng | Create site/machine/member → rename → history → archive/restore/invite | Duplicate code, parent inactive, stale edit, invite invalid, last member, unknown mutation | API/UI/audit/idempotency/scope evidence; conflict giữ draft, query trước retry | Stable IDs, scoped data, lifecycle và ngang quyền pass |
| P5 | P4 hierarchy có dữ liệu synthetic và parent lookup | Folder lồng nhau → case → search/filter/page → move/rename → archive/restore | Cycle, child-parent, duplicate name, wrong machine/site, out-of-range page, restore conflict | Tree snapshots, atomic mutation and deep-link evidence; rollback subtree, không xóa history | Tree/case/deep-link/filter/archive/restore pass |
| P6 | Object store, size policy và file fixtures đã kiểm | Select role/type → upload → checksum/object → manifest → validator → signed download | Empty/large/interrupted, object/DB partial, duplicate, declared/detected mismatch, DICOM/measurement invalid, expired link | Byte/hash round-trip, object inventory, manifest/findings; reconcile rồi retry từng operation | File/role/UID/geometry/manifest và negative upload pass |
| P7 | Machine/protocol seed và P4/P5 case đã sẵn sàng | Select protocol → measurements/N-A → draft → evaluate → result → rerun/compare/trend | Missing/unit/NaN/zero baseline, autosave race, double submit, archived protocol | Known-answer, immutable result, projection uniqueness, browser evidence; tạo run/version mới | Rule boundary, N/A, history, compare và trend projection pass |
| P8 | P6 validated inputs, Redis/worker và profile capability đã sẵn sàng | Preflight → accepted run/outbox → queue → lease/worker → Gamma → persist → map/stats → retry/compare | Missing RTDOSE/comparison, frame/grid/unit/config, no candidates/coverage, local zero, Redis/worker/lease/crash/OOM, DICOM/resource/source drift | 2D/3D oracle, denominator/coverage, attempt/lease/fencing/dead-letter, large-input; bounded retry, không worker cũ ghi đè | Numeric oracle + DICOM + queue recovery + resource/schema staging pass |
| P9 | P7/P8 source snapshot và renderer baseline đã sẵn sàng | Source → template/block editor → preview → immutable revision → render → export/download/history | Revision/source/content/format/renderer/storage/download/idempotency | Four-format bytes/hash, deterministic repeat, long/Unicode/visual and storage-failure evidence; giữ source/export cũ | Full customization, snapshot, renderer/download/retry pass |
| P10 | P7 result projection có context/protocol version | Filter machine/metric/time → compatible series → raw/aggregate → baseline/event → drill-down/export/rebuild | Incompatible series, date/timezone, empty, zero baseline, duplicate/source archived, large query | Aggregate equality, rebuild counters/idempotency, source/export and browser evidence; tách series, không bịa zero | S/E/C, large-series budget và staging source drill-down pass |
| P11 | P7 consumer contract và P4 organization đã sẵn sàng | Search/detail → create/clone → validate-only → DRAFT → ACTIVE → consumer snapshot → compare/archive | Rule/applicability/reference/version/key/persistence/conflict/archived/capability errors | Migration `20260908_0011`, API/UI lifecycle, consumer snapshot and scope; query uncertain mutation, clone/version mới | Active-only consumer, old snapshot, full S/E/C và staging pass |
| P12 | P3 Auth, P9 report shell và migration environment đã sẵn sàng | Biological Hub → tool capability → scenario validate/create → edit/save → clone/archive → history/export | Session/scope/key/context/source/revision/immutable/module/persistence errors | Migration `20260908_0012`, scenario/revision DB state, no-QA linkage, browser refresh/reconnect, Stitch screen; retry sau query, không tạo calculation giả | P12 local + staging S/E/C, report integration và capability states pass |
| P13 | P12 scenario/revision contract và known-answer LQ set | SAVED revision → D/n/d/alpha-beta → normalize/validate-only → BED/EQD2 → curve/table/marker → immutable snapshot/replay/export | Noninteger/negative/nonfinite, D≠n×d, alpha-beta/source, range/step/point limit, duplicate curve, archived/out-of-scope revision, idempotency/persistence uncertainty | Formula/known-answer, pair derivation/zero dose, unit/precision, curve-table equality, model/source/checksum snapshot, validate no-mutation; staging browser/API/DB evidence | Local gates pass; staging graph/history/export/replay/no-QA linkage pass |
| P14 | P13 engine và common biological context đã stable | 2–10 options → common context/model → baseline → calculate delta/chart → reorder/clone/export | Missing/invalid option, context mismatch, baseline missing/zero, percent undefined, limit/truncate | Same revision/context, null percent reason, option IDs/order, no-truncate evidence; giữ options hợp lệ | Comparison known delta, zero handling, history/export pass |
| P15 | P13/P14 scalar result và time/course model đã stable | Courses → tissue/alpha-beta → no-recovery/recovery → cumulative/sensitivity → interruption → compensation alternatives → export | Interval/recovery/source/context, nonuniform schedule, overlap, noninteger, missing spatial registration/OAR dose | Assumption/source/sensitivity snapshot, scalar-vs-spatial capability, integer schedule; chặn nhánh unsupported, không sửa treatment | Scalar/recovery/compensation negative matrix và independent export pass |
| P16 | P12/P13 source/applicability contract đã stable | Search/filter → entry detail → create/clone/version → citation/import → explicit scenario use → archive | Missing source, unit/applicability, broken link, duplicate/import/script content | Version/citation/applicability snapshot and import report; row-level repair, không gán PASS/FAIL | Library no-match/source/version/explicit-use pass |
| P17 | P6 DICOM metadata và geometry fixtures đã stable | Dataset select → frame/grid/ROI preflight → overlay → DVH/profile → metric/export | Missing CT/RTSTRUCT, frame/grid/ROI/contour/codec/coverage; dose-only fallback | Geometry oracle, coverage denominator, source UID/checksum, visual/table fallback; không gán zero hoặc giả spatial | Supported/unsupported geometry, DVH and staging evidence pass |
| P18 | P0–P17 release contracts và candidate manifest đã khóa | RC → integrated E2E → golden → failure/restart/concurrency/load → backup/restore → pilot → regression | Result regression, restore incomplete, duplicate replay, capacity, unsupported pilot data, evidence mismatch | Immutable RC manifest, workload/log/restore/checksum/pilot issues; giữ candidate, mở issue/regression, không sửa expected | MUST E2E/restore/performance/pilot pass, không SEV0/1 |
| P19 | P18 RC, production backup, DNS/TLS/Auth/CORS và service IDs đã kiểm | Backup → migration compatible → API/worker/renderer/web → public smoke → remote E2E → monitor/rollback rehearsal | Domain/TLS, build config, schema/version mismatch, private dependency, remote E2E/resource | Promotion manifest, public URLs, service/schema/engine versions, rollback record; không promote partial, giữ last-good | Website HTTPS và workflow từ mạng ngoài pass, rollback/backup evidence pass |
| P20 | P19 release và owner/runbook inventory đã bàn giao | Monitor/alert → backup/restore drill → guide/support → incident triage → maintenance staging → regression | Backup/retention, alert delivery, capacity, engine result change, recurring incident | Alert/restore timestamps, runbook execution, incident/RCA/regression/release notes; không xóa last-good | Initial operations package có config thật, owner, alert/restore evidence và backlog |

**Luật dừng chung của execution ledger:**

1. `API_SMOKE` chỉ chứng minh endpoint phản hồi; không được ghi `E2E_PASS` nếu chưa kiểm database/object/queue/UI/provenance theo testcase.
2. Lỗi có thể phục hồi phải được thử phục hồi thật ít nhất một lần trong môi trường an toàn: retry có giới hạn, refresh/reconnect, restart worker, reload source, restore hoặc rollback tùy phase.
3. Mỗi mutation/async operation phải phân biệt `REJECTED`, `ACCEPTED`, `RUNNING`, `COMPLETED`, `FAILED`, `CONFLICT` và `OUT_OF_SCOPE`; không gộp “mất response” vào “chưa tạo”.
4. Không đánh dấu phase tiếp theo `DONE-v2` nếu phase trước chỉ có local evidence nhưng target gate yêu cầu staging, independent oracle, resource test hoặc browser workflow.
5. Khi phát hiện lỗi mới, thêm testcase/regression mới vào phase sở hữu lỗi và cập nhật cả `business-analysis.md`, `specification.md`, `plan.md` trong cùng change set nếu contract thay đổi.

## 5. Railway/Supabase deployment contract

Bảng dưới là mục tiêu cấu hình và ID đã có trong hồ sơ. Chỉ việc đọc deployment metadata tại thời điểm deploy mới chứng minh cấu hình đang áp dụng. Không suy diễn rằng Railway đã bỏ hỗ trợ config-as-code từ việc một ô path biến mất.

| Thành phần | Staging | Production | Kiểm chứng |
| :--- | :--- | :--- | :--- |
| Railway project | 339f2c50-ddd7-491f-8c4e-da2a2d169502 | Cùng project, khác environment | Đối chiếu ID trước mutation. |
| Environment ID | b0ab34e5-0ff4-479d-8232-659d175e9e2f | 910dff25-75b6-42b2-bf6b-e2601ba9d7d2 | Không dựa tên service dễ đổi. |
| API service ID | 9b35bf0b-0419-4679-8af0-e639e5a84713 | 9544c3e6-c8bd-4c29-b62e-c6172eb51af3 | Root /apps/api; effective Dockerfile/start command. |
| Database service ID | 8fc8201e-417d-4fd7-9a6d-17ad51b72dcf | 5709f18d-c92d-461a-9f73-478dd7748d80 | DATABASE_URL reference tới DB đúng environment. |
| Staging web ID | 9f23331c-8d5e-45fb-9f11-5aa5e69f76f6 | Ghi ID khi provision/verify | Build public env tại build time; pin actual SHA. |
| Staging worker ID | a1e0c389-e527-4d4c-995e-2a48f4795dda | Ghi ID khi provision/verify | /apps/api; python -m rt_connect_api.worker; private, không HTTP healthcheck. |
| Staging Redis ID | ca18f134-82fb-44a1-ac5c-cde76fb33882 | Theo topology P19 | API/worker cùng reference; durable queue recovery có test. |
| Source | Branch triển khai được xác minh; checkpoint repo codex/p4-org-site-machine | Release đã promote vào main hoặc ref đã khóa | Kiểm riêng web/API/worker SHA, không suy từ branch setting. |
| API PORT | 8000 baseline | 8000 baseline | Process 0.0.0.0:$PORT và domain target port khớp. |
| Pre-deploy | alembic upgrade head | alembic upgrade head | Log migration head và runner duy nhất. |
| Liveness | /api/v1/health | /api/v1/health | Không gọi DB; HTTP 200 sau bind thành công. |
| Readiness | /api/v1/ready + schema revision check | Tương tự | Code hiện /ready chỉ SELECT 1, schema là evidence riêng. |
| Database driver | psycopg 3 | psycopg 3 | Normalize scheme ở runtime/Alembic, giữ credentials nguyên vẹn. |
| Supabase | Auth project staging, URLs/issuer đúng staging | Auth production | Không lưu entity nghiệp vụ trong Supabase DB. |
| Secrets | Chỉ tên trong tài liệu; runtime/tool scope phù hợp | Tương tự | Railway tokens không đưa vào web/API runtime nếu không cần. |

Object storage là dịch vụ HTTPS được truy cập qua credential phía server hoặc signed URL ngắn hạn. Bucket private không có nghĩa chặn mọi kết nối HTTPS tới nhà cung cấp. Browser tải file qua signed URL đã cấp sau kiểm organization; database/Redis/worker không mở public nghiệp vụ.

Nếu dùng Service Settings: kiểm metadata effective của deployment; nếu dùng config-as-code: kiểm path/config resolution và override precedence theo dịch vụ thực tế. Chọn một nguồn cấu hình có owner, không ghi hai nguồn trái nhau rồi cho rằng file trong Git tự áp dụng.

### 5.1. Troubleshooting theo triệu chứng

| Triệu chứng | Kiểm tra theo thứ tự | Điều kiện xác nhận đã sửa |
| :--- | :--- | :--- |
| Railpack không build | Deployed SHA → contents → root → Dockerfile/build command | Build đúng ứng dụng thành công. |
| Alembic thiếu psycopg2 | URL normalization runtime và Alembic → lockfile psycopg3 → escaped URL | Pre-deploy và DB revision đúng, không in URL thật. |
| Healthcheck fail nhưng service Online | Start log → bind/PORT → target port → path | Deployment health pass và request ngoài mạng 200. |
| Web trắng/Auth chưa config | Web SHA → JS/network errors → build VITE vars → SPA fallback | Login/deep-link và error boundary hoạt động. |
| Organization Not Found | API base URL → API deployed SHA/routes → membership → schema | Bootstrap trả organization/onboarding đúng, không sửa DB ngẫu nhiên. |
| Job mãi queued | Outbox/stream → worker env/consumer → lease/heartbeat → DB state | Job đi tới terminal và ack/recovery được ghi. |
| Download lỗi | Artifact scope → signed URL expiry → object tồn tại/hash → CORS khi cần | File byte checksum khớp nguồn. |

## 6. Design-to-code theo Google Stitch

Project RT-connect: 14242591911141046021. Các ID trong registry/progress là evidence cũ phải re-query trước chỉnh design. Không gọi MCP hoặc regenerate thiết kế chỉ để hoàn thành việc sửa tài liệu này.

| Phase | Thiết kế cần đọc/tạo | Variant tối thiểu |
| :--- | :--- | :--- |
| P3 | Home, Login, Recovery, Callback, Onboarding/Session Error | Empty, populated, offline, expired/config error. |
| P4–P5 | Organization/Site/Machine/Member; QA Archive/detail/folder dialogs | Create/edit/move/archive/restore/conflict/search empty. |
| P6–P8 | Upload queue/Manifest/Findings; Checklist; Gamma Workspace | File chosen/uploading/failed/duplicate; input invalid; queued/running/failed/retry/result. |
| P9–P11 | Builder/Viewer/Revision/Export; Trend; Protocol Library | Long report, render failed, empty chart, version conflict. |
| P12–P15 | Tạo lại Biological Hub, BED/EQD2, comparison, re-irradiation và compensation | Cùng design tokens/AppShell; scalar/capability/source/assumption/error. |
| P16–P17 | Dose Limit/Knowledge/Protocol; Visual Dose/DVH | No match, source unavailable, mapping/geometry/coverage errors. |
| P18–P20 | Status/maintenance/support | Bounded loading, dependency degraded, recovery guidance. |

Trước code UI: ghi screen ID/revision, route, API event và FR. Sau code: đối chiếu desktop 1440×900, laptop 1280×800 và mobile 390×844; keyboard/tab focus, form labels, bảng dài và tiếng Việt. Không khôi phục bốn Biological legacy hidden. Nếu MCP chưa truy cập được: ghi gap; thực hiện contract/tests/backend độc lập, không đánh dấu visual acceptance PASS.

## 7. Checkpoint, issue và bằng chứng đóng phase

Template checkpoint (cần điền giá trị thật):

~~~yaml
plan_version: "2.0"
current_phase: P8
current_work_package: P08-W01
status: IN_PROGRESS
source_commit: "<actual-sha>"
implemented_requirements: []
verified_test_ids: []
failed_test_ids: []
not_run_test_ids: []
evidence_paths: []
deployment_manifest: "<path-or-not-deployed>"
next_exact_action: "<one executable next step>"
blocking_dependency: null
independent_next_work: []
~~~

Issue gồm: FR/MOD/P/W, triệu chứng, input fixture/hash, expected/observed, root cause, affected versions, fix scope, tests và release impact. Không gọi phase DONE chỉ vì checkpoint ghi thế; auditor phải tìm được evidence từng MUST test.

### 7.1. Điều kiện hoàn thành toàn dự án

1. P0–P19 DONE-v2; P20 initial package đạt exit, không yêu cầu vận hành tương lai đã diễn ra.
2. Mọi FR-P00-01 đến FR-P20-04 có mapping và acceptance evidence; không orphan feature hoặc test.
3. Known-answer/error/integration/remote E2E theo scope đều PASS trên đúng candidate; không còn lỗi SEV0/1.
4. Staging→production version manifest, schema, backup/restore/rollback được kiểm chứng.
5. Website HTTPS dùng được từ mạng ngoài; user guide, runbook và monitoring/backup đã cấu hình thực.
6. Tất cả GAP chưa đóng được giải quyết bằng code/test hoặc quyết định thay đổi phạm vi được ghi rõ; không tự loại bỏ requirement để đóng goal.
7. Bàn giao summary phân biệt feature completeness, test coverage, workload đã đo và giới hạn còn biết. Không hứa “không còn mọi lỗi có thể xảy ra”.

### 7.2. Kết quả lần sửa tài liệu này

Đã chi tiết hóa requirement/workflow/error/recovery/exit và xác định gap từ source. Slice P6/P8/P9 đã được sửa và kiểm thử local; tài liệu đã được rebaseline theo schema `20260908_0009`. P8 vẫn mở ở các gate oracle/failure/resource; P9 đã `LOCAL_VERIFIED` nhưng staging browser, export/download và visual evidence còn mở. Không phase nào được đánh dấu `DONE-v2` chỉ vì local test hoặc Railway báo Online.


## 8. Ma trận FR → contract → testcase ban đầu

Mỗi FR có testcase cụ thể dưới đây; Cxx là ma trận chung §3, Gxx là oracle Gamma trong specification §5.4. Cùng testcase có thể kiểm nhiều FR khi cùng hành trình. Đây là mapping kiểm thử, mọi outcome v2 vẫn NOT_RUN trước khi chạy. Nếu test thực hiện chưa đủ assertion cho FR, bổ sung testcase/assertion trước đóng gate; không chỉ gắn ID để đủ ô.

| Requirement | Contract | Test thành công/lỗi/biên phải kiểm |
| :--- | :--- | :--- |
| FR-P00-01 | SPEC-P00 | TC-P00-S01, TC-P00-S03, TC-P00-E01, TC-P00-E04, C15 |
| FR-P00-02 | SPEC-P00 | TC-P00-S01, TC-P00-E03 |
| FR-P00-03 | SPEC-P00 | TC-P00-S02, TC-P00-E02, TC-P00-E03 |
| FR-P00-04 | SPEC-P00 | TC-P00-S03, TC-P00-E01 |
| FR-P01-01 | SPEC-P01 | TC-P01-S01, TC-P01-E01, TC-P01-E02, TC-P01-E04 |
| FR-P01-02 | SPEC-P01 | TC-P01-S01, TC-P01-E03 |
| FR-P01-03 | SPEC-P01 | TC-P01-S02, TC-P01-E04, C16 |
| FR-P01-04 | SPEC-P01 | TC-P01-S03, TC-P01-E05 |
| FR-P02-01 | SPEC-P02 | TC-P02-S02, TC-P02-E01, TC-P02-E03 |
| FR-P02-02 | SPEC-P02 | TC-P02-S03, TC-P02-E05 |
| FR-P02-03 | SPEC-P02 | TC-P02-S01, TC-P02-E02, TC-P02-E04 |
| FR-P02-04 | SPEC-P02 | TC-P02-S02, TC-P02-E04, TC-P02-E06 |
| FR-P03-01 | SPEC-P03 | TC-P03-S01, TC-P03-S04, TC-P03-E01, TC-P03-E02, TC-P03-E03 |
| FR-P03-02 | SPEC-P03 | TC-P03-S02, TC-P03-E04 |
| FR-P03-03 | SPEC-P03 | TC-P03-S03, TC-P03-E06 |
| FR-P03-04 | SPEC-P03 | TC-P03-S01, TC-P03-E05, C10, C16 |
| FR-P04-01 | SPEC-P04 | TC-P04-S01, TC-P04-S04, TC-P04-E01, TC-P04-E02, TC-P04-E06 |
| FR-P04-02 | SPEC-P04 | TC-P04-S02, TC-P04-E03 |
| FR-P04-03 | SPEC-P04 | TC-P04-S03, TC-P04-E04, TC-P04-E05 |
| FR-P04-04 | SPEC-P04 | TC-P04-S04, TC-P04-E02, C09 |
| FR-P05-01 | SPEC-P05 | TC-P05-S01, TC-P05-E01, TC-P05-E02, TC-P05-E03 |
| FR-P05-02 | SPEC-P05 | TC-P05-S04, TC-P05-E04 |
| FR-P05-03 | SPEC-P05 | TC-P05-S02, TC-P05-E05, C11 |
| FR-P05-04 | SPEC-P05 | TC-P05-S03, TC-P05-E06, C09 |
| FR-P06-01 | SPEC-P06 | TC-P06-S01, TC-P06-S04, TC-P06-E01, TC-P06-E02, TC-P06-E03, TC-P06-E04 |
| FR-P06-02 | SPEC-P06 | TC-P06-S02, TC-P06-S03, TC-P06-E05 |
| FR-P06-03 | SPEC-P06 | TC-P06-S01, TC-P06-E06, C09 |
| FR-P06-04 | SPEC-P06 | TC-P06-S01, TC-P06-E07, C13 |
| FR-P07-01 | SPEC-P07 | TC-P07-S01, TC-P07-E01, TC-P07-E02, TC-P07-E06 |
| FR-P07-02 | SPEC-P07 | TC-P07-S03, TC-P07-E04, C05 |
| FR-P07-03 | SPEC-P07 | TC-P07-S01, TC-P07-S02, TC-P07-S03, TC-P07-E03 |
| FR-P07-04 | SPEC-P07 | TC-P07-S04, TC-P07-E05, C09 |
| FR-P08-01 | SPEC-P08 | TC-P08-S01, TC-P08-S02, TC-P08-E01, TC-P08-E02, TC-P08-E08 |
| FR-P08-02 | SPEC-P08 | TC-P08-S01, TC-P08-S03, TC-P08-E03, TC-P08-E04, TC-P08-E05, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20 |
| FR-P08-03 | SPEC-P08 | TC-P08-S04, TC-P08-S05, TC-P08-E06, TC-P08-E07, TC-P08-E09, TC-P08-E10 |
| FR-P08-04 | SPEC-P08 | TC-P08-S01, TC-P08-S03, C13, G01, G02, G03, G04, G05, G06, G07, G08, G09, G10 |
| FR-P09-01 | SPEC-P09 | TC-P09-S01, TC-P09-E03, C10 |
| FR-P09-02 | SPEC-P09 | TC-P09-S02, TC-P09-E01, C09 |
| FR-P09-03 | SPEC-P09 | TC-P09-S03, TC-P09-E04, TC-P09-E05, TC-P09-E06 |
| FR-P09-04 | SPEC-P09 | TC-P09-S04, TC-P09-E02, C13 |
| FR-P10-01 | SPEC-P10 | TC-P10-S01, TC-P10-S05, TC-P10-S08, TC-P10-E01, TC-P10-E02, TC-P10-E03, TC-P10-E07 |
| FR-P10-02 | SPEC-P10 | TC-P10-S02, TC-P10-S06, TC-P10-E04, TC-P10-E08, TC-P10-E09 |
| FR-P10-03 | SPEC-P10 | TC-P10-S01, TC-P10-S04, TC-P10-S05, TC-P10-S08, TC-P10-E01, C11 |
| FR-P10-04 | SPEC-P10 | TC-P10-S03, TC-P10-S07, TC-P10-E05, TC-P10-E06, TC-P10-E10, TC-P10-E11, TC-P10-E12, C13 |
| FR-P11-01 | SPEC-P11 | TC-P11-S01, TC-P11-E05, C11 |
| FR-P11-02 | SPEC-P11 | TC-P11-S02, TC-P11-E01, TC-P11-E02 |
| FR-P11-03 | SPEC-P11 | TC-P11-S03, TC-P11-E03, C09 |
| FR-P11-04 | SPEC-P11 | TC-P11-S01, TC-P11-S04, TC-P11-E04 |
| FR-P12-01 | SPEC-P12 | TC-P12-S04, TC-P12-E05 |
| FR-P12-02 | SPEC-P12 | TC-P12-S01, TC-P12-E01, TC-P12-E02 |
| FR-P12-03 | SPEC-P12 | TC-P12-S02, TC-P12-E03 |
| FR-P12-04 | SPEC-P12 | TC-P12-S03, TC-P12-E04, C13 |
| FR-P13-01 | SPEC-P13 | TC-P13-S01, TC-P13-S02, TC-P13-S04, TC-P13-S05, TC-P13-E01, TC-P13-E02, TC-P13-E03 |
| FR-P13-02 | SPEC-P13 | TC-P13-S01, TC-P13-S06, TC-P13-E05, TC-P13-E08 |
| FR-P13-03 | SPEC-P13 | TC-P13-S03, TC-P13-S06, TC-P13-E04, TC-P13-E09 |
| FR-P13-04 | SPEC-P13 | TC-P13-S03, TC-P13-S07, TC-P13-S08, TC-P13-E06, TC-P13-E07, TC-P13-E10, C13 |
| FR-P14-01 | SPEC-P14 | TC-P14-S01, TC-P14-S03, TC-P14-E01, TC-P14-E03, TC-P14-E06 |
| FR-P14-02 | SPEC-P14 | TC-P14-S02, TC-P14-E02, TC-P14-E05 |
| FR-P14-03 | SPEC-P14 | TC-P14-S04, TC-P14-E04 |
| FR-P14-04 | SPEC-P14 | TC-P14-S03, C09, C13 |
| FR-P15-01 | SPEC-P15 | TC-P15-S01, TC-P15-E03, TC-P15-E06 |
| FR-P15-02 | SPEC-P15 | TC-P15-S02, TC-P15-E01, TC-P15-E02 |
| FR-P15-03 | SPEC-P15 | TC-P15-S03, TC-P15-S04, TC-P15-S05, TC-P15-E04, TC-P15-E07, TC-P15-E08 |
| FR-P15-04 | SPEC-P15 | TC-P15-S05, TC-P15-E05, C09, C13 |
| FR-P16-01 | SPEC-P16 | TC-P16-S01, TC-P16-S04, TC-P16-E02, TC-P16-E05 |
| FR-P16-02 | SPEC-P16 | TC-P16-S03, TC-P16-E01 |
| FR-P16-03 | SPEC-P16 | TC-P16-S03, TC-P16-E03, TC-P16-E04, TC-P16-E06 |
| FR-P16-04 | SPEC-P16 | TC-P16-S02, C09, C13 |
| FR-P17-01 | SPEC-P17 | TC-P17-S02, TC-P17-E06, TC-P17-E07 |
| FR-P17-02 | SPEC-P17 | TC-P17-S01, TC-P17-E01, TC-P17-E03, TC-P17-E04 |
| FR-P17-03 | SPEC-P17 | TC-P17-S03, TC-P17-S04, TC-P17-E02, TC-P17-E05 |
| FR-P17-04 | SPEC-P17 | TC-P17-S04, C09, C13 |
| FR-P18-01 | SPEC-P18 | TC-P18-S01, TC-P18-S02, TC-P18-E01, TC-P18-E06 |
| FR-P18-02 | SPEC-P18 | TC-P18-S04, TC-P18-E03 |
| FR-P18-03 | SPEC-P18 | TC-P18-S03, TC-P18-E02 |
| FR-P18-04 | SPEC-P18 | TC-P18-S04, TC-P18-E04, TC-P18-E05 |
| FR-P19-01 | SPEC-P19 | TC-P19-S02, TC-P19-E01, TC-P19-E02 |
| FR-P19-02 | SPEC-P19 | TC-P19-S03, TC-P19-E04, TC-P19-E05 |
| FR-P19-03 | SPEC-P19 | TC-P19-S01, TC-P19-E03, TC-P19-E06 |
| FR-P19-04 | SPEC-P19 | TC-P19-S04, TC-P19-E03 |
| FR-P20-01 | SPEC-P20 | TC-P20-S01, TC-P20-E02, TC-P20-E03 |
| FR-P20-02 | SPEC-P20 | TC-P20-S02, TC-P20-E01 |
| FR-P20-03 | SPEC-P20 | TC-P20-S04, TC-P20-E05 |
| FR-P20-04 | SPEC-P20 | TC-P20-S03, TC-P20-E04 |
