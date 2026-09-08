# RT-CONNECT — Đặc tả hành vi, dữ liệu và nghiệm thu

- File: specification.md; version **1.1**; ngày 2026-09-08.
- Nguồn nghiệp vụ: business-analysis.md v0.7.
- Kế hoạch triển khai: plan.md v2.1, P0–P20.
- Kiến trúc nền: technical-specification.md v1.0.
- Đây là hợp đồng mục tiêu. Những nội dung chưa có code được ghi TARGET; kiểm source không thay bằng chứng runtime.

## 1. Quyền sở hữu tài liệu và phạm vi

| Tài liệu | Sở hữu | Không được suy ra |
| :--- | :--- | :--- |
| business-analysis.md | Người dùng, chức năng, BR/FR và kết quả nghiệp vụ | Có requirement không có nghĩa đã triển khai. |
| specification.md | Validation, data/API semantics, error/recovery, thuật toán và acceptance target | Code chưa tương thích phải tạo gap, không đổi requirement theo output hiện tại. |
| technical-specification.md | Kiến trúc, entities nền, topology, lịch sử adapter | Ví dụ/roadmap cũ không phải danh sách endpoint đang có. |
| plan.md | Dependencies, work packages, S/E test cases, exit gate | Checkboxes chưa phải evidence. |
| implementation-progress.md | Evidence có ngày, SHA, môi trường, kết quả trước đây | Snapshot cũ không khẳng định trạng thái cloud hiện tại. |
| Google Stitch | Design system, màn hình và visual states | Thiết kế không thay nghiệp vụ hoặc validation. |

Khi contract mới ở tài liệu này khác ví dụ cũ trong technical-specification, mục mới được ghi là target cần migrate/test, không tự đổi response API đang phục vụ. Bất kỳ thay đổi nghiệp vụ nào vẫn phải đồng bộ business-analysis và plan.

Giữ mô hình thành viên ngang quyền. Không bổ sung workflow APPROVED/FINAL cho QA case/report hay canonical report bắt buộc. Draft, revision và job status là cơ chế lưu/tính kỹ thuật. Giới hạn truy cập organization áp dụng như nhau cho mọi thành viên.

Release features: R0 nền tảng; R1 QA; R2 Biological; R3 Visual Dose/DVH; R4 public release/operations. P17 là bắt buộc cho bàn giao toàn dự án nhưng không ngăn R1 sớm.

## 2. Hợp đồng chung

### 2.1. Kiểu dữ liệu và validation

| Nhóm | Quy tắc mục tiêu |
| :--- | :--- |
| ID | UUID cho resource; server tạo; source/reference IDs giữ nguyên qua rename/move. |
| Tên | Trim hai đầu, Unicode NFC; required 1–200 ký tự; reject control characters. Không dùng tên làm path object thật. |
| Nội dung dài | Note plain text tối đa 20.000 ký tự; rich content phải qua schema/sanitizer; giới hạn configurable nhưng công bố rõ. |
| Numeric | Finite; null/empty khác 0; không nhận NaN/Infinity; đơn vị được khai báo và chuyển explicit. |
| Date/time | Timestamp ISO 8601 timezone-aware lưu UTC; date-only giữ date. UI dùng timezone organization và hiển thị timezone khi export. |
| Khoảng thời gian | Query từ start inclusive đến end exclusive; UI ngày kết thúc inclusive được chuyển sang đầu ngày kế tiếp ở timezone đã chọn. |
| Pagination | Hiện có offset/limit; target default 25, max 100; sort stable theo field + ID; vượt range trả collection rỗng, không 500. |
| Optional field | Omitted = không đổi trong PATCH; null = xóa nếu field nullable; empty string không tự biến thành null cho numeric/date. |
| Unknown fields | Input mutation từ user reject hoặc explicit schema version adapter; không nhận rồi bỏ cấu hình có ý nghĩa tính toán. |
| Units | Canonical physical dose Gy; position mm; volume cc hoặc % theo metric; BED/EQD2 kèm alpha/beta context. |
| Rounding | Tính bằng precision engine đã khóa; chỉ round khi display. Export numeric giữ full precision và display_precision metadata. |
| Reference | Kiểm resource thuộc organization, trạng thái và quan hệ cha-con trong cùng transaction mutation. |

Các giới hạn tên/size/page/range mới là target; code hiện có khác phải ghi migration/compatibility trước khi áp dụng, không cắt dữ liệu cũ.

### 2.2. Error envelope: khớp API hiện tại

`apps/api/src/rt_connect_api/core/errors.py` hiện dùng flat envelope:

~~~json
{
  "code": "REQUEST_VALIDATION_FAILED",
  "message": "Request validation failed.",
  "correlation_id": "opaque-request-id",
  "details": [
    {"field": "body.configuration.distance_to_agreement_mm", "message": "Must be greater than zero."}
  ]
}
~~~

Không thêm wrapper `error` hoặc đổi sang `request_id` âm thầm. Detail gồm field + message; thêm property machine-readable trong tương lai phải version/test tương thích. Browser không suy loại lỗi từ chuỗi message.

| HTTP | Ý nghĩa | Client xử lý |
| :--- | :--- | :--- |
| 400 | Command sai nghĩa nghiệp vụ không thuộc validation field cụ thể | Hiển thị lỗi, không retry tự động. |
| 401 | Bearer thiếu/sai/hết hạn | Một refresh single-flight nếu có refresh session; sau đó yêu cầu login. |
| 403 | Identity hợp lệ nhưng context/membership không cho truy cập | Phân biệt onboarding với inactive context; không auto-create organization thay thế. |
| 404 | Resource không có trong scope hoặc route sai | Resource lỗi hiển thị not found; route mismatch là deployment diagnostic. |
| 409 | Version/idempotency/unique/lifecycle conflict | Giữ draft, fetch bản mới hoặc đối soát operation. |
| 413 | File/payload quá lớn | Dừng upload, không retry nguyên payload. |
| 415 | Media/format unsupported | Chọn profile/adapter đúng. |
| 422 | Schema/range/unit/geometry/config sai | Field findings; không retry cho tới khi sửa input. |
| 429 | Rate/capacity limit | Tôn trọng Retry-After; không spam request. |
| 500 | Lỗi không dự đoán | Mã hỗ trợ; log phía server đã redaction; không expose stack trace. |
| 502/503/504 | Dependency/upstream unavailable/timeout | Retry bounded nếu an toàn; giữ accepted operation ID. |

Client GET retry tối đa 2 lần thêm sau lần đầu, exponential backoff có jitter; timeout metadata request 30 giây baseline. Mutation không auto-retry nếu không có idempotency contract. Upload/export/job có deadline riêng. Không hiển thị trạng thái “đang kết nối” vô hạn.

Các mã uppercase trong plan là **scenario taxonomy TARGET**, không phải danh sách code đã triển khai. Không tạo code ghép “A_OR_B”: triển khai A/B riêng nếu hai nguyên nhân. Existing code cùng nghĩa được giữ và map vào test. Endpoint chưa làm phải ghi TARGET trong OpenAPI proposal, không làm API consumers tin đã có.

### 2.3. Idempotency và sửa đồng thời

- Tạo resource/job/report revision dùng operation key ổn định cho cùng thao tác. Scope key = organization + operation type + key; fingerprint gồm canonical payload và source revision/checksum.
- Same key/same fingerprint: trả cùng resource/result. Same key/different fingerprint: 409 IDEMPOTENCY_CONFLICT. Thời gian giữ key phải >= retry window; baseline 24 giờ cho CRUD, theo lifetime run cho analysis.
- Run có retry hạ tầng vẫn cùng input/config/engine snapshot; mỗi lần retry có attempt ID mới. Đổi input/config/engine là rerun với run ID mới.
- Record editable có revision integer. Update phải kèm expected revision; UPDATE theo ID + organization + expected revision. Zero affected row → distinguish conflict/not-found theo scope, không overwrite.
- Audit event và transaction nghiệp vụ commit cùng nhau. DB commit thành công nhưng response mất: client query operation trước retry; không suy thất bại chỉ từ browser timeout.
- Long-running accepted job không bị hủy do đóng browser. API cancellation chưa có thì UI không đặt nút Cancel giả.

### 2.4. Organization và Auth

- Supabase xác thực identity; RT-CONNECT DB map subject→membership→organization.
- First resource read phải có organization scope. Không lấy global UUID rồi mới kiểm tenant ở bước sau. Worker message scope phải khớp run scope trước đọc input.
- Auth lifecycle: unknown→loading→authenticated/anonymous/configuration-error; organization bootstrap là bước riêng. Không gộp lỗi API 404 hoặc outage thành “bạn chưa có tổ chức”.
- Cache key theo identity + organization; logout/identity change hủy request cũ và clear query/cache dữ liệu nghiệp vụ.
- Onboarding create organization+identity projection+membership transaction và concurrent-create uniqueness.
- Invitation TARGET P4: mọi thành viên có thể tạo invitation; nhận bằng verified identity khớp lời mời. Token invitation random, hash-at-rest, một lần, expiry baseline 7 ngày; accept tạo membership idempotent. Không join bằng email domain, không auto-promote quyền.
- Membership active/inactive không tạo doctor/physicist roles. Không tự mất quyền từ logout access token: JWT revocation behavior phải kiểm theo cấu hình thực và TTL; API kiểm membership active ở request.
- Supabase unavailable/JWKS rotate có cached-key policy hữu hạn, request timeout; không bypass signature.

### 2.5. UI và input feedback

Mọi trang có loading/empty/ready/error; form thêm validation/saving/saved/conflict; async job thêm queued/running/failed/retrying/completed. Warning chỉ khi có nội dung cảnh báo thật. Error boundary phải render được ngay cả khi env/schema bootstrap sai.

Form có label, unit cạnh value, keyboard focus theo lỗi đầu tiên; không chỉ dùng màu. Khi chọn file phải thấy filename/size; upload reset file input sau success là bình thường, vì vậy “No file chosen” sau upload không chứng minh upload thất bại: phải refresh danh sách/server và tìm artifact/checksum.

Dates/decimal input phải hỗ trợ giao diện tiếng Việt có quy tắc rõ, không hiểu “1,000” lúc là 1 lúc là 1000. Bảng/chart có data-table alternative; route deep-link và back/forward giữ selection/filter.

## 3. Lưu trữ, provenance và validation dữ liệu

### 3.1. Schema và revision nền

| Entity | Dữ liệu và constraints mục tiêu |
| :--- | :--- |
| Organization / Membership | Subject projection unique; một active context theo scope hiện tại; invitation không tạo context ngoài ý muốn. |
| Site / Machine | Scoped code unique theo policy; stable_machine_id giữ lịch sử; rename không tạo machine mới. |
| Folder / QACase | Parent scoped cùng organization; cycle guard; một primary folder; active parent khi tạo; archive/history giữ IDs. |
| Artifact | object_key opaque, SHA256 server, byte_size, declared/detected type, immutable original, organization/case/biological namespace. |
| InputManifest / ValidationRun | Source UID/geometry/units/acquisition/roles/validator version và findings; validation mới không xóa bản cũ. |
| Analysis / Attempt | Immutable input/config/engine; mutable technical lifecycle; attempts riêng, lease/fencing; result commit một lần. |
| Protocol/Template/Report versions | Version độc lập mutable draft; saved version/source snapshot không update ngược. |
| TrendPoint | Unique organization+source_run+metric+projection version; rebuild không thay source. |
| BiologicalScenario / CalculationRun | Không FK QACase bắt buộc; input/tissue/model/source/assumptions/results versioned. |
| Knowledge versions | Applicability/metric/unit/source/external citation; library update không đổi calculation cũ. |

Tất cả entity mới cần migration, index/query contract, archive/history behavior và test upgrade từ schema trước. Generic AnalysisRun hoặc /jobs là kiến trúc target, không giả định đã thay thế MachineQARun/GammaAnalysisRun hiện tại.

### 3.2. Upload và object storage

1. Client gửi file + type + role + case context + operation key; server kiểm scope trước ghi.
2. Streaming: đọc chunk, kiểm max bytes và hash; không tin Content-Length hoặc extension.
3. Lưu object durable có key generated, không dùng original filename làm đường dẫn thực.
4. Commit Artifact/Manifest/Audit và operation result; chỉ trả success khi DB và object durable.
5. Nếu object PUT xong nhưng DB fail: operation journal để reconcile hoặc cleanup object chưa tham chiếu sau grace period. Không xóa object đã được artifact khác reuse.
6. Batch upload: từng file một operation, tổng progress có terminal status riêng; không làm lại file đã thành công.
7. Dedup trong organization/case/type phù hợp; same bytes+type có thể reuse, new role tạo manifest thiếu đúng một lần. Same bytes different declared type không auto-reuse.
8. Download phải kiểm scope và signed URL expiry. Test tải lại tính SHA256, không chỉ click nút.
9. File lớn và derived arrays đưa object storage, metadata/API response không nhúng toàn bộ ảnh hoặc gamma map millions of points.
10. Original checksum khác source.sha256 do user khai trong measurement: server SHA256 là artifact identity. Source hash trong JSON là external provenance, không yêu cầu self-hash bất khả thi; phải đánh dấu trusted/unverified.

Upload limit baseline hiện config 104.857.600 byte (100 MiB); test đúng limit và limit+1. Inline JSON target ≤5 MiB; lớn hơn cần managed array artifact contract mới. Không đọc arbitrary object_key do người dùng chèn trong JSON.

### 3.3. Hai mức validation

- File-level: có parse được, đúng profile/type, finite values, units, shape/UID và metadata đủ.
- Dataset/workflow-level: reference links, frame/registration, physical quantities, required inputs và engine capabilities.
- VALID file không có nghĩa một cặp file hợp lệ cho Gamma/DVH.
- ERROR critical → INVALID, chặn phép tính liên quan. WARNING → thông tin thiếu không-critical có rule rõ; user có thể tiếp tục nếu capability cho phép và acknowledgement được snapshot. Không có “accept all warnings” để bỏ qua unit/geometry critical.
- Finding: code, severity, field/location, message, expected/actual summaries, ảnh hưởng workflow, recovery action. Không đưa PHI/secret thừa vào lỗi.
- Extension và MIME chỉ là hint: DICOM declared + JSON content phải có ARTIFACT_TYPE_MISMATCH, không VALID dưới nhãn DICOM.
- Archive không hard-delete; dữ liệu đã được result pin vẫn tải/xem từ history theo quyền organization.

### 3.4. DICOM dose và geometry

RTDOSE chuẩn cần xác định DoseUnits/DoseType/DoseSummationType, DoseGridScaling, pixel format, transfer syntax, rows/columns/frames, spacing/position/orientation, grid frame offsets và references điều kiện. Source file đúng cú pháp không đủ xác nhận liều/hình học phù hợp. DICOM hiện hành liệt kê DoseUnits GY, RELATIVE, CODED; chuỗi CGY trực tiếp không phải giá trị enumerated chuẩn. [DICOM RT Dose Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.3.html)

Profile P8 chuẩn trước mắt: PHYSICAL + GY, pixel_data×DoseGridScaling→Gy, axial regular grid đã test. RELATIVE chỉ dùng nếu có calibration/normalization explicit phù hợp; CODED cần adapter nhận sequence mã đơn vị, không suy cGy từ text. Unsupported profile trả lỗi cụ thể. JSON measurement có thể khai CGY và chuyển ×0,01 sang Gy với provenance.

Fixture golden chuẩn phải dùng GY, scale 0,01 nếu pixel 100..800 biểu diễn 1..8 Gy; referenced RTPLAN dùng RTPlanStorage SOP Class UID đúng và instance UID riêng. Fixture CGY cũ chỉ chứng minh extension conversion của code, không là bằng chứng DICOM conformity; cần giữ dưới negative/compatibility fixture nếu hữu ích.

GridFrameOffsetVector có biểu diễn offset tương đối hoặc patient-z tuyệt đối khi thỏa điều kiện chuẩn; phải decode theo trường hợp chứ không luôn cộng origin.z. [DICOM Grid Frame Offset Vector](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.3.2.html)

Coordinate contract TARGET:
- DICOM positions thuộc patient coordinate frame, không gọi mảng DICOM tự động là IEC phantom frame.
- Storage order [z,row/y,column/x] khác physical basis; lưu axis order và affine/direction riêng.
- PixelSpacing = row spacing rồi column spacing. Physical voxel center từ ImagePositionPatient, row/column directions và offset; không đảo row/column bằng tên biến.
- Same FrameOfReference là điều kiện liên kết, không đủ bỏ kiểm orientation/spacing/origin.
- Measurement IEC/phantom frame cần declared basis + explicit transform về reference frame; transform có direction, units, source/version và checksum.
- Unsupported nonuniform/oblique không “sửa” thành uniform/axial im lặng. Adapter mới phải có test, hoặc chặn capability và mô tả rõ phạm vi.

## 4. Job, queue và phục hồi

### 4.1. State machine kỹ thuật TARGET

~~~text
request validation fail → rejected (không có accepted job)
accepted → QUEUED → RUNNING → COMPLETED
                        └→ FAILED → RETRYING → RUNNING
                  stale lease → RETRYING (attempt cũ kết thúc lỗi)
~~~

COMPLETED chỉ là hoàn thành tính toán; quality có thể PASS/WARNING/FAIL. INVALID_INPUT khác failed do hạ tầng. N/A không là PASS. Không dùng job states làm quy trình phê duyệt lâm sàng.

| Sự kiện | Hành vi transaction/queue |
| :--- | :--- |
| API accept | Commit run+immutable inputs+outbox cùng transaction. Trả run ID cho client. |
| Dispatch Redis | Outbox dispatcher at-least-once; mark published sau enqueue; dispatcher retry khi Redis mất. |
| Worker claim | Atomically lấy lease/fencing token và attempt trong DB trên organization/run/version. |
| Tính dài | Heartbeat độc lập vòng tính; progress stage+% không báo 100 trước terminal commit. |
| Commit result | Conditional update trên current lease/attempt; result và artifacts manifest durable. |
| Ack | Sau durable terminal state; ack lỗi có thể redeliver, consumer nhận completed thì không tính lại. |
| Worker chết | Lease timeout, finalize attempt cũ interrupted, requeue bằng policy; không giữ RUNNING vô hạn. |
| Old worker quay lại | Fencing mismatch → không được commit result từ lease cũ. |
| Poison/malformed message | Quarantine/dead-letter + diagnostic; không retry vô hạn hoặc expose payload thừa. |
| Retry | Chỉ lỗi transient theo allowlist; input/config invalid phải sửa rồi tạo run mới. |

Baseline target: heartbeat mỗi 10 s, lease 120 s, supervisor scan 30 s; worker thực thi deadline theo workload. Retry tự động tối đa 3 attempts (gồm attempt đầu), backoff có jitter. P8 implementation hiện đã đưa lease, visibility, retry limit, backoff, execution deadline và voxel/candidate budget vào `Settings`; các giá trị phải được ghi trong release manifest và chỉ thay sau benchmark/failure-injection. Lease hết hạn không được do chính thread tính không gửi được heartbeat.

Slice implementation P8 hiện đã có `GammaRunAttempt`, `GammaDispatchOutbox`, lease token/expiry và conditional update để fencing stale worker. Local tests đã bao phủ exhaustive node oracle, bounded recoverable-storage retry, lease expiry/reclaim, candidate/voxel preflight và replay sau commit trước ack; staging crash/ack injection, dead-letter/resource benchmark vẫn là exit gate P8.

DB là source of truth. Redis transport failure/replay không mất accepted run. Reconciliation định kỳ đối soát outbox/queued/stale attempts; không lấy global resource UUID để đọc tenant artifact. Metrics stream toàn cục chỉ dành operational view phù hợp; user workspace counters phải organization-scoped, không cho suy dữ liệu tổ chức khác.

## 5. Gamma contract và oracle

### 5.1. Input profile và capability

| Field | Contract mục tiêu |
| :--- | :--- |
| workflow_profile | PSQA_GAMMA bắt RTDOSE reference + comparison; ENGINE_TEST cho JSON-only, có nhãn, không tự thành report PSQA. API hiện đã enforce preflight này. |
| dimensionality | 2D/3D khớp datasets; muốn slice 3D thành plane cần explicit plane origin/basis/isocenter selection artifact. |
| dose_difference_mode | ABSOLUTE dùng positive delta Gy; RELATIVE dùng positive percent với global/local scale. |
| normalization | GLOBAL dùng reference level explicit hoặc max reference; LOCAL dùng reference dose tại điểm. |
| dose_threshold_percent | [0,100], reference threshold basis snapshot; điểm đúng ngưỡng được tính (>=). |
| DTA | Positive mm, independent grid spacing; không pixel-distance. |
| interpolation | GRID discrete, LINEAR bilinear ở 2D/trilinear ở 3D; spacing/step/convergence snapshot. Legacy BILINEAR API cần mapping version khi đổi tên. |
| alignment | Identity transform phải có frame justification; manual rigid/shift có direction/units/version, không chỉ note. |
| search / max_gamma | Search radius `max_gamma × DTA`; kết quả vượt bound là censored, phải phân biệt với exact. API hiện nhận `max_gamma` trong [1,10]. |
| mask/ROI | Mask source checksum, alignment/coverage, counted/excluded points và selection rule. |
| field/composite | Composite hoặc explicit beam identity + RTPLAN links khi per-field; không trộn beam chỉ từ filename. |
| threshold PASS | [0,100] do user/protocol chọn, snapshot; không tự coi preset là giới hạn áp dụng cho mọi bệnh viện. |
| dose quantity | Dose-to-water/medium/relative/effective context explicit nếu nguồn có; mismatch không được bỏ qua. |

`workflow_profile`, `coverage_policy` (`FULL_ROI`/`OVERLAP_ONLY`) và `max_gamma` đã có trong request/config snapshot và UI slice hiện tại. Các control còn lại đã mô tả trong business-analysis §11.2 thuộc backlog P8; không coi UI field hiện có là toàn bộ cấu hình đã hoàn thiện. Field/mask/shift/isocenter chưa triển khai phải thể hiện capability chưa sẵn sàng và vẫn giữ task mở.

### 5.2. Định nghĩa tính toán mục tiêu

Với điểm reference r, dose R(r), vị trí evaluation e và dose E(e):

~~~text
gamma(r) = min_e sqrt(
  ( ||e-r|| / DTA )^2 +
  ( (E(e)-R(r)) / delta_D(r) )^2
)

ABSOLUTE: delta_D(r) = absolute_dose_difference_gy
RELATIVE GLOBAL: delta_D(r) = percent/100 * global_reference_gy
RELATIVE LOCAL: delta_D(r) = percent/100 * abs(R(r))
~~~

Absolute/relative ở đây là tiêu chí dose difference, không tự rescale dataset evaluation. Chuẩn hóa dataset relative→Gy là bước riêng cần nguồn. Reference/evaluation đảo chiều có thể cho kết quả khác; không giả tính đối xứng.

Threshold theo reference; mask selection xác định reference set. Local reference bằng 0 ở threshold=0: reject config/run với mã dose-scale undefined hoặc explicit exclude-zero policy đã chọn có reason/count; không tự lấy epsilon để biến thành PASS.

### 5.3. Search, denominator và percentile

- Full numeric gamma cần search đủ radius gamma_max×DTA, convergence theo sampling/interpolation; GRID cho kết quả discrete phải ghi rõ.
- Chỉ search radius DTA có thể phân loại pass/fail trong phạm vi sampling, nhưng không đảm bảo gamma numeric/percentile >1 là giá trị minimum đúng.
- Target không loại point không có candidate khỏi denominator để tăng pass rate. Denominator = reference points trong ROI/threshold hợp lệ theo policy đã công bố.
- Phân biệt OUTSIDE_EVALUATION_COVERAGE (không biết dose) với GAMMA_ABOVE_SEARCH_LIMIT (đã có coverage nhưng không tìm gamma <= bound).
- Coverage thiếu: default PSQA full-ROI result INVALID_INPUT, pass_rate null. User explicit chọn overlap-only ROI tạo config/run mới, kèm fraction coverage và excluded reasons. Không silently chuyển overlap-only.
- Censored gamma trên gamma_max được tính nonpassing nếu gamma_max>=1; numeric gamma có thể null với lower bound/status, không thay bằng 0.
- Percentile chỉ xuất exact nếu đủ uncensored values; nếu dữ liệu censored thì biểu diễn interval/lower-bound hoặc null có reason, không in percentile giả.
- Total counts phải reconcile: selected + excluded = reference total; passing + nonpassing + invalid coverage = selected; khi invalid không phát hành overall PASS.
- No evaluated points: pass_rate null và invalid reason, không 0%/100% theo tiện triển khai.
- Histogram phải có overflow/censored bucket và loại excluded riêng. Map/profiles cùng orientation và source config.

Implementation note cho P8.2: `FULL_ROI` trả `INVALID`/`pass_rate=null` khi có điểm `NO_CANDIDATE`; `OVERLAP_ONLY` loại các điểm đó khỏi mẫu số nhưng phải trả `coverage_fraction` và số điểm bị loại. Điểm vượt `max_gamma` có status `CENSORED`, bị tính non-passing và làm percentile `exact=false`; không biến thành gamma bằng đúng max bound.

PyMedPhys cung cấp API Gamma với lựa chọn interpolation, lower-dose cutoff, global/local và max_gamma; có thể dùng làm reference implementation khi khóa version/config phù hợp. Đây là lựa chọn đối chiếu kỹ thuật, không phải bằng chứng hai engine hiện tương đương. [PyMedPhys Gamma API](https://docs.pymedphys.com/en/stable/users/ref/lib/gamma.html)

### 5.4. Golden tests và numeric budgets TARGET

| ID | Fixture/When | Expected |
| :--- | :--- | :--- |
| G01 | Identical 2D/3D grids, dose positive, full coverage | Gamma≈0; 100%; histogram/counts đúng. |
| G02 | Uniform reference=1 Gy, evaluation=1,03 Gy, absolute DD=0,03 Gy, vị trí trùng | Gamma≈1; pass tại inclusive boundary trong tolerance numeric đã khóa. |
| G03 | Uniform reference=1 Gy, evaluation=1,06 Gy, DD=0,03 Gy | Gamma≈2; fail; full-search numeric phải đúng, không percentile bị truncate vô nhãn. |
| G04 | Reference có 4 selected points, evaluation chỉ cover 2 | Default full-ROI invalid/null; overlap explicit tính 2 với coverage 50%. |
| G05 | Reference zero/local threshold=0 | Dose scale undefined được reject/explicit excluded theo config, không chia 0. |
| G06 | Known shift, unequal spacing, axis transpose trap | So với analytical small-grid exhaustive oracle cùng policy; không dùng bản copy code production làm oracle. |
| G07 | Dose exactly cutoff, below cutoff, ROI empty | >= cutoff included, below excluded, empty invalid. |
| G08 | RTDOSE GY scaled pixels vs JSON Gy/cGy equivalent | Chuẩn hóa dose đúng; same frame/transform đảm bảo 8/8 golden 3D. |
| G09 | Oblique/nonuniform/frame mismatch/unsupported codec | Capability error rõ, không giả pose/grid. |
| G10 | Two workers + crash after commit before ack | Một durable result, attempt history và queue state nhất quán. |
| G11 | 2D/3D × GLOBAL/LOCAL × ABSOLUTE/RELATIVE × GRID/LINEAR, data nonzero | Chạy đủ 16 combinations; ABSOLUTE không phụ thuộc chọn GLOBAL/LOCAL, RELATIVE thì dùng đúng reference level. |
| G12 | GLOBAL explicit normalization khác max reference | DD scale dùng giá trị explicit đã chọn; threshold basis vẫn đúng config; result snapshot ghi cả hai. |
| G13 | ROI mask một phần/empty/misaligned | Một phần đếm đúng selected/excluded; empty invalid; misaligned yêu cầu transform, không auto-resize mask. |
| G14 | Per-field có hai beam/thiếu RTPLAN link, composite tương đương | Field chọn đúng beam identity; thiếu liên kết chặn per-field, composite không tự suy beam assignment. |
| G15 | 3D RTDOSE chọn plane/isocenter và shift theo frame explicit | Plane dose/profile cùng basis/origin; shift đúng dấu và đơn vị; note không thay transform. |
| G16 | Search gamma_max=1 vs 2 vs 3 trên điểm gamma thật >1 | Classification nhất quán; số/percentile chỉ exact khi search đủ, trường hợp khác có bound/censored flag. |
| G17 | Sampling step giảm một nửa qua ba mức trên shifted grid | Báo convergence; không đổi tolerance sau khi biết observed chỉ để PASS. |
| G18 | Một hàng finite, một hàng NaN/Infinity/negative physical dose | Invalid input đúng field/index; không bỏ điểm lỗi để tăng pass rate. |
| G19 | Reference/evaluation đổi vai trên distribution không đối xứng | Hai run/config/roles riêng; không reuse result fingerprint của chiều trước. |
| G20 | Nhiều point gần gamma=1 và pass-rate threshold bằng đúng tỷ lệ thực | Compare trên giá trị chưa display-round; inclusive policy và numeric tolerance được công bố, boundary classification có oracle. |

Small analytic same-grid budget: abs gamma error ≤1e-6; normalized dose error ≤1e-6 Gy cho fixture được lưu đủ precision. Oracle interpolation comparison target: abs gamma ≤0,02 và pass-rate chênh ≤0,5 điểm phần trăm trên reference suite có cấu hình/coverage identical; điểm near gamma=1 phải phân tích riêng và chạy convergence, không dùng tolerance để che lệch classification. Đây là engineering targets cần đo ở P8, không phải clinical dose thresholds. Thay tolerance phải giải thích method/input precision và version suite trước khi đổi expected.

## 6. Biological contract

### 6.1. LQ và lịch fraction

Input mode chọn đúng hai trong D,n,d. Nếu user nhập ba, consistency target abs(D−n*d) ≤ max(1e-6 Gy, 1e-6×abs(D)); input lớn/precision nguồn cần record rounding policy. n là số nguyên >0; d,D>=0; alpha/beta a>0, finite. LQ cơ bản:

~~~text
uniform fractions: BED = n*d*(1 + d/a)
nonuniform fractions: BED = sum_j d_j*(1 + d_j/a)
EQD2 = BED/(1 + 2/a)
~~~

Mỗi calculation lưu tissue, alpha-beta value/unit/source/version hoặc user override, model version, assumptions và input revision. Không suy OAR dose từ prescription target.

Known answers: 60/30, a=10 → BED 72, EQD2 60; 30/5, a=3 → BED 90, EQD2 54. Numeric budget small analytic abs error ≤1e-9 hoặc rel≤1e-9. Hiển thị Gy10/Gy3 hoặc metadata alpha-beta cạnh Gy để không cộng khác context.

Model ngoài LQ mặc định không được tính từ ô note; time/repopulation model chỉ khả dụng khi formula, parameters, units, applicability/source, version và known-answer suite đã định nghĩa.

### 6.2. Curve và comparison

Fixed-n mặc định: BED(D)=D*(1+D/(n*a)), EQD2 chia (1+2/a). Fixed-d tạo các điểm D=n*d với n nguyên; không vẽ đường continuous mà giả n lẻ là schedule thực.

Curve range min≤max, step>0, alpha-beta list finite positive, giới hạn target 2.000 điểm/series và 10 series. Bao gồm endpoint max theo quy tắc explicit nếu step không chia hết; không lặp điểm endpoint. Chart/table/export chung dataset.

Comparison giữa các **phương án thay thế** không cộng dose tổng. Khi một phương án có nhiều course, tổng trong phương án theo cùng tissue/model contract. delta=B−A; percent=100*(B−A)/A, A=0 → null+reason. Khác tissue/model/alpha-beta cần group/compatibility warning, không auto-rank “tốt nhất”.

### 6.3. Re-irradiation scalar

- Chọn tissue/dose metric: target prescription, OAR Dmean/Dmax/Dxcc phải gắn metric; không coi tất cả là cùng quantity.
- For a fixed tissue/alpha-beta model: BED_i từ từng course; no-recovery BED_total=sum BED_i; EQD2_total=BED_total/(1+2/a).
- Recovery profile baseline **user-defined fraction at evaluation date**, không khẳng định là mô hình recovery sinh lý đã xác minh.
- Mỗi course trước có r_i ∈ [0,1] tại cùng evaluation date; residual BED_i=(1−r_i)*BED_i. Course mới r=0. Sum residual một lần. Không tự áp recovery theo khoảng thời gian nếu user chưa chọn model.
- Course dates dùng để trình bày timeline và validate chronology; khi recovery/time model phụ thuộc ngày, missing interval chặn model đó.
- Hiển thị no-recovery và recovery cạnh nhau, từng contribution, alpha-beta source, evaluation date và giả định.
- Cộng Dmax hoặc Dxcc của nhiều course chỉ là scalar comparison của metric được chọn; các điểm/volume đạt max có thể khác nhau. Không gắn nhãn cumulative anatomical Dmax/Dxcc.
- Sensitivity: user chọn alpha-beta/recovery ranges, tính scenario grid; không giả các range là clinical confidence interval.
- Không tự suy ra “còn được phép thêm bao nhiêu Gy” thành prescription. Nếu có inverse calculator tương lai phải có explicit target/model và integer fraction re-evaluation.

### 6.4. Fraction Compensation

Delivered schedule immutable trong calculation snapshot. planned, delivered, missed và remaining phải được phân biệt theo fraction IDs/ngày; planned=delivered+remaining chỉ khi planned schedule chưa bị thay đổi và missed được phân loại nằm trong remaining, không cộng missed hai lần.

Tổng alternative = delivered prefix + user-proposed remaining. Fractions không đều dùng sum BED_j. Không time model: gián đoạn chỉ ảnh hưởng calendar display, không tự thêm dose compensation. Time model optional cần parameter source (ví dụ unit Gy/day nếu dùng loss rate), reference duration và sign convention rõ trong version riêng; chưa định nghĩa đủ thì disabled.

Date end<start, overlapping duplicate fraction, negative count/dose, missing delivered dose hoặc option khiến n không nguyên: field error, không auto-correct schedule.

### 6.5. Spatial capability

P15 scalar không tự nhận chỉ một note “registered” để bật spatial. Spatial extension cần: dose grids và fractions per course, source/target frames, transform artifact direction/units/checksum, registration provenance, common grid, interpolation/coverage và uncertainty policy; khóa thứ tự biological conversion vs resampling/accumulation vì hai phép không mặc định giao hoán.

P17 Visual Dose/DVH không tự chứng minh deformable dose accumulation đã có. Không có spatial capability thì UI chỉ cho scalar, vẫn giữ task extension được mô tả rõ; không quảng cáo cumulative 3D.

### 6.6. Dose limits và knowledge

DoseLimit là typed entry: disease/subtype, treatment intent, technique, fractionation range, structure, metric parameters, comparison operator, limit, dose/volume units, source type/citation/version/applicability. Unknown fractionation không tự match mọi phác đồ.

Dmax khác D0.03cc; V20Gy[%] khác V20Gy[cc]; physical Gy khác EQD2(a). Không chuyển constraint giữa số fractions bằng BED/EQD2 tự động. User chọn entry mới đưa vào calculator và preview changes; source revision được snapshot. Nội dung không có nguồn external phải ghi internal/user-defined, không giả nhãn guideline.

## 7. Report, Trend, DVH và yêu cầu vận hành

### 7.1. Report revision và export

- User tự thêm/ẩn/xóa/rename/reorder mọi block, kể cả warning/provenance. System lineage vẫn giữ ngoài report layout.
- Source binding theo metric/run/revision IDs; đổi label không sửa actual calculated value. User text/override content được lưu như report edit, không rewrite source result.
- Snapshot bao gồm input manifest, result, protocol/config/template, block config, assets/fonts/renderer/version/locale/timezone.
- Preview và export cùng snapshot. Save revision optimistic; export key=revision+format+render options+renderer version.
- PDF gốc lưu artifact/hash để tải lại byte-identical. Re-render có thể khác metadata bytes; semantic/layout repeatability kiểm separately, không hứa SHA giống nếu không khóa timestamp/metadata/render nondeterminism.
- CSV/JSON là structured data + source metadata, không giả giữ nguyên layout PDF. CSV escape formula-leading strings để không mở thành công thức ngoài ý muốn.
- Font tiếng Việt, chart scale/legend, page breaks, table headers, long notes và missing image có visual tests.
- Rich text được sanitize; renderer không thực thi arbitrary script hoặc fetch URL nội bộ. Full customization không đòi arbitrary code execution.

### 7.2. Trend

Series compatibility signature gồm metric meaning/unit, machine, energy/mode, detector/phantom và protocol/rule context. Chuyển unit equivalent phải explicit. Maintenance/baseline là versioned annotations, không rewrite raw points.

Baseline effective date và source snapshot; outlier không bị loại âm thầm. Downsample phải báo method/count/time-buckets, giữ min/max để thấy cực trị; export raw/aggregated chọn rõ. Drill-down source run/report revision, không link report mới nhất không tương ứng.

### 7.3. DVH numeric contract

Dose grid và ROI mask cùng physical frame. CT bắt buộc chỉ cho anatomy overlay; dose-only có thể không CT. DVH bắt RTDOSE+RTSTRUCT.

Volume weights từ geometry; 1 cc = 1.000 mm³. Mask/rasterization, holes/disjoint contours, voxel center/partial volume policy và coverage versioned. Không tự gán dose=0 cho vùng ngoài grid. Full-ROI metrics bị invalid nếu coverage không đủ; overlap-only phải user chọn và được ghi rõ.

Cumulative DVH convention Vx = volume có dose >= x. Vx unit cc hoặc % explicit. Dx = dose quantile ứng với x% volume nhận ít nhất dose đó, interpolation/bin convention pinned. Dxcc đổi x cc/ROI volume rồi dùng cùng quantile; x>ROI volume invalid. Dmin/Dmax của sampled volume khác point-dose physics; Dmean weighted sum/volume. Empty ROI/zero volume cho null+reason.

Analytic fixtures: uniform dose box, unequal voxel sizes, sphere convergence, donut hole, disjoint ROI, duplicated ROI names, structures outside grid, frame transpose/flip. Uniform-grid Dmean error ≤1e-6 Gy; analytic box volume đúng trong tolerance encoding. Sphere/rasterization tolerance phải theo resolution/partial-volume method và convergence report; không đặt một tolerance che mọi grid.

### 7.4. Workload và engineering SLO mục tiêu

Những số dưới là budget nghiệm thu ban đầu, **chưa đo đạt**, cần ghi hardware/resources, software version, cold/warm cache, network và concurrent users trong P8/P18. Không coi gói 5 USD là bảo đảm capacity.

| Nhóm | Workload chuẩn để đo | Target/gate |
| :--- | :--- | :--- |
| Metadata API | 20 virtual users, 10.000 case, 100.000 trend points | p95≤1 s server-side, error rate<1% không tính invalid requests chủ đích. |
| Web initial/loading | Desktop/laptop/mobile; controlled network profile | Loading state ngay; request timeout hữu hạn, không trắng trang. |
| Upload | 1 MiB, 10 MiB, 100 MiB và limit+1 | Checksum đúng; streamed; limit+1 →413; RSS không tăng theo toàn bộ số file batch. |
| Gamma small | 64×64, identical + shifted, GRID/LINEAR | correctness gate + complete≤30 s trên worker 2 vCPU/2 GiB reference benchmark. |
| Gamma large | 128×128×64 (~1 triệu voxels), 2 concurrent accepted jobs | Target≤10 phút/job, worker RSS<80% limit; serialized nếu cần; API vẫn đạt response budget. |
| Gamma deadline | 15 phút baseline/job | Timeout error+attempt state, không RUNNING vô hạn; dài hơn cần config/benchmark. |
| Queue recovery | Kill worker mid-run và after DB commit-before-ack | Recover theo lease policy; một durable result; accepted job không mất. |
| Report | 20 trang/500 rows/10 charts và stress 100 trang | Normal≤30 s, stress≤120 s target; thiếu memory báo lỗi có retry. |
| Trend | 100.000 points/machine | Query≤2 s p95 target; downsample rõ, raw drill-down đầy đủ. |
| Backup | DB+objects+manifests có writes liên quan | Target RPO≤24 h, RTO≤4 h; đo qua restore drill, không dựa log backup alone. |
| Monitoring | Synthetic API/worker/backup fault | Alert trong 5 phút target; xác nhận kênh nhận thật. |

Nếu resource Railway thấp hơn benchmark profile: ghi cấu hình và kết quả thật, đề xuất optimize/resource adjustment hoặc thay workload bằng quyết định scope có ghi nhận; không bỏ case lớn để đóng P8. Backup phải kiểm consistency giữa DB và object inventory; không restore DB sang thời điểm có object chưa phục hồi.

## 8. Contract theo từng phase

Các operation dưới đây nói rõ “target” khi chưa có. Mỗi phase kế thừa contract chung; error scenarios có ID duy nhất trong plan. Field list là schema design input, không tự động đồng nghĩa tất cả field là required.

<a id="spec-p00"></a>

### SPEC-P00 — Baseline, phạm vi và truy vết

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-00–MOD-16; FR-P00-01 đến FR-P00-04 |
| Input và dữ liệu hiển thị | Phiên bản tài liệu; BR/MOD/FR; route; API operation; test ID; trạng thái evidence; design project/screen/version. |
| Model/storage | Registry trong Markdown; không migration. |
| Operation/API surface | Không API sản phẩm; đọc source, Git và metadata hạ tầng khi cần. |
| Transaction/invariant | Bản cập nhật tài liệu có version chung; không ghi secret vào evidence. |
| Output bàn giao | Bộ ba tài liệu, registry và gap list; bản plan trước được lưu lịch sử. |
| Success oracle | TC-P00-S01 đến TC-P00-S03 trong plan |
| Error/recovery oracle | TC-P00-E01 đến TC-P00-E04 trong plan |
| Exit | 100% FR trong catalogue được gán phase/test; không còn xung đột phạm vi chưa có quyết định. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** DOCUMENT_CONFLICT; DESIGN_REFERENCE_STALE; EVIDENCE_MISSING; ENVIRONMENT_MISMATCH. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p01"></a>

### SPEC-P01 — Runtime local, repository và CI

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-16; FR-P01-01 đến FR-P01-04 |
| Input và dữ liệu hiển thị | Python/Node version; lockfiles; API/web build SHA; schema head; môi trường local; tên biến cấu hình. |
| Model/storage | Alembic revision có forward path; synthetic seed idempotent. |
| Operation/API surface | GET /api/v1/health, /ready, /version; kiểm tra schema response thực tế trước khi đổi. |
| Transaction/invariant | Startup không tự seed production; migration thất bại không bị bỏ qua. |
| Output bàn giao | Setup README, Compose, CI jobs và artifact build. |
| Success oracle | TC-P01-S01 đến TC-P01-S03 trong plan |
| Error/recovery oracle | TC-P01-E01 đến TC-P01-E05 trong plan |
| Exit | Clean setup và restart pass; CI bắt buộc xanh; migration DB rỗng/upgrade có evidence. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** DEPENDENCY_MISMATCH; PORT_IN_USE; MIGRATION_FAILED; CONFIGURATION_MISSING; BUILD_CONTRACT_FAILED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p02"></a>

### SPEC-P02 — Railway staging, PostgreSQL và nền tảng Supabase Auth

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-00, MOD-16; FR-P02-01 đến FR-P02-04 |
| Input và dữ liệu hiển thị | Project/environment/service IDs; branch/SHA; Dockerfile/root; PORT; API URL; DB service reference; issuer/audience/JWKS; Auth redirect allowlist. |
| Model/storage | PostgreSQL staging riêng; Supabase chỉ identity/session; secret qua service variables. |
| Operation/API surface | Health/ready/version public tối thiểu; API nghiệp vụ yêu cầu Bearer; Auth do Supabase. |
| Transaction/invariant | Pre-deploy thất bại không thay bản release đang hoạt động; cấu hình không ghi password vào log. |
| Output bàn giao | Deployment/env manifest, migration evidence, Auth contract checks. |
| Success oracle | TC-P02-S01 đến TC-P02-S03 trong plan |
| Error/recovery oracle | TC-P02-E01 đến TC-P02-E06 trong plan |
| Exit | Đúng source và environment; health, schema, JWT hợp lệ/lỗi pass; không dùng production DB cho smoke staging. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** BUILD_SOURCE_INVALID; DATABASE_DRIVER_MISMATCH; SERVICE_NOT_LISTENING; SCHEMA_NOT_READY; AUTH_VERIFICATION_FAILED; DEPLOYMENT_CONFIG_DRIFT. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p03"></a>

### SPEC-P03 — App Shell, đăng nhập, onboarding và Home Dashboard

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-00, MOD-01; FR-P03-01 đến FR-P03-04 |
| Input và dữ liệu hiển thị | Email/identity; return path nội bộ; organization context; widget counters/recent QA/jobs; loading/empty/error; module availability. |
| Model/storage | UserIdentity, OrganizationMembership; dashboard read model; membership xác định scope, không role hierarchy. |
| Operation/API surface | GET /session/bootstrap; POST /organizations; GET /organizations/{id}/dashboard; routes /auth/*, /app. |
| Transaction/invariant | Onboarding cùng transaction; two-tab submit tạo tối đa một context active; cache key theo identity/organization. |
| Output bàn giao | Auth/AppShell/dashboard hoạt động và recovery/empty/error screens. |
| Success oracle | TC-P03-S01 đến TC-P03-S04 trong plan |
| Error/recovery oracle | TC-P03-E01 đến TC-P03-E06 trong plan |
| Exit | Happy path, first-use, expiry, offline, deep-link và logout cache tests pass trên staging. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** SIGN_IN_FAILED; RECOVERY_LINK_INVALID; SESSION_UNAVAILABLE; ORGANIZATION_MEMBERSHIP_REQUIRED; AUTH_CONFIGURATION_MISSING; WORKSPACE_LOAD_FAILED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p04"></a>

### SPEC-P04 — Organization, Site, Machine và thành viên ngang hàng

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-02; FR-P04-01 đến FR-P04-04 |
| Input và dữ liệu hiển thị | Organization name/timezone; site name/code; machine stable ID/name/code/manufacturer/model/energy/mode/status; membership identity/status; revision. |
| Model/storage | Organization/Site/Machine + revision; Membership/Invitation target P4 bổ sung; invite hash, expiry và accepted identity. |
| Operation/API surface | CRUD organization/site/machine đã có một phần; /organizations/{id}/invitations và accept là target mới. |
| Transaction/invariant | Accept invitation và membership commit cùng transaction; archive không hard-delete; lịch sử nguồn giữ nguyên. |
| Output bàn giao | Management screens, membership onboarding, history và contract tests. |
| Success oracle | TC-P04-S01 đến TC-P04-S04 trong plan |
| Error/recovery oracle | TC-P04-E01 đến TC-P04-E06 trong plan |
| Exit | Hai identity cùng organization dùng được nghiệp vụ; isolate organization khác; rename/archive/restore/concurrent edit pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** MACHINE_CODE_CONFLICT; PARENT_NOT_AVAILABLE; REVISION_CONFLICT; INVITATION_INVALID; LAST_MEMBERSHIP_CONFLICT; MUTATION_RESULT_UNKNOWN. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p05"></a>

### SPEC-P05 — QA Archive, Folder và QA Case

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-03; FR-P05-01 đến FR-P05-04 |
| Input và dữ liệu hiển thị | Folder name/parent/path/revision; case title/type/cycle/performed_at/site/machine/folder/protocol reference/tags/note; include_archived; search filters. |
| Model/storage | Folder tree + stable UUID; QACase metadata; archive flags, revision, audit. |
| Operation/API surface | /organizations/{id}/folders/tree; /folders/{id}; /organizations/{id}/qa-cases; /qa-cases/{id}; case history target. |
| Transaction/invariant | Move subtree transaction; case một primary folder; archived ancestor ngăn tạo dữ liệu mới mặc định. |
| Output bàn giao | Archive/detail/filter/move/restore UI và database constraints. |
| Success oracle | TC-P05-S01 đến TC-P05-S04 trong plan |
| Error/recovery oracle | TC-P05-E01 đến TC-P05-E06 trong plan |
| Exit | Nested move, archive/restore, combined search, cross-scope và deep-link tests có evidence. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** FOLDER_CYCLE; FOLDER_NAME_CONFLICT; PARENT_NOT_AVAILABLE; CASE_HIERARCHY_INVALID; PAGE_OUT_OF_RANGE; RESTORE_CONFLICT. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p06"></a>

### SPEC-P06 — Upload, Artifact, Manifest và Validation

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-04; FR-P06-01 đến FR-P06-04 |
| Input và dữ liệu hiển thị | Filename/type/media type/size/SHA256; artifact ID; logical roles; SOP/Study/Series/Frame UIDs; grid/scaling/units; detector/phantom/acquisition; validator version/findings. |
| Model/storage | Artifact immutable bytes; InputManifest versioned roles/metadata; ValidationRun findings severity/code/field; dataset selection snapshot. |
| Operation/API surface | POST/GET /qa-cases/{id}/artifacts; /artifacts/{id}/validate, /download, /manifest, /validations. |
| Transaction/invariant | Object PUT và DB không có distributed transaction: pending operation + compensation/reconciliation; success chỉ sau durable object + DB commit. |
| Output bàn giao | Upload/manifest/validation/detail UI; format fixtures; round-trip checksum evidence. |
| Success oracle | TC-P06-S01 đến TC-P06-S04 trong plan |
| Error/recovery oracle | TC-P06-E01 đến TC-P06-E07 trong plan |
| Exit | Real browser upload→validate→download checksum, duplicate/type/role, interrupted upload và storage failure tests pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** FILE_REQUIRED_OR_EMPTY; UPLOAD_TOO_LARGE; UPLOAD_INTERRUPTED; ARTIFACT_PERSISTENCE_FAILED; ARTIFACT_TYPE_MISMATCH; INPUT_METADATA_INVALID; DOWNLOAD_LINK_EXPIRED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p07"></a>

### SPEC-P07 — Machine QA checklist, rule engine và history

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-05; FR-P07-01 đến FR-P07-04 |
| Input và dữ liệu hiển thị | Protocol version/rules; metric key/value/unit/required/N-A reason; baseline/tolerance/action; notes/artifact; measurement revision; result actual/limit/margin/status. |
| Model/storage | QAProtocolVersion/Rule, MachineQARun, TrendPoint; identity snapshot và audit. |
| Operation/API surface | /qa-cases/{id}/machine-qa-runs; /machine-qa-runs/{id}/measurements, /evaluate, /rerun, /compare. |
| Transaction/invariant | Measurement revision được khóa tại evaluate; result + trend projection commit nhất quán hoặc reconciliation idempotent. |
| Output bàn giao | Checklist/result/history/compare; known-answer rule tests; staging evidence. |
| Success oracle | TC-P07-S01 đến TC-P07-S04 trong plan |
| Error/recovery oracle | TC-P07-E01 đến TC-P07-E06 trong plan |
| Exit | Boundary PASS/WARNING/FAIL/N-A, unit/baseline errors và rerun/projection uniqueness đều pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** MEASUREMENT_REQUIRED; MEASUREMENT_INVALID; BASELINE_ZERO; REVISION_CONFLICT; DUPLICATE_OPERATION; PROTOCOL_NOT_AVAILABLE. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p08"></a>

### SPEC-P08 — PSQA Gamma, RTDOSE, worker và kết quả 2D/3D

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-06; FR-P08-01 đến FR-P08-04 |
| Input và dữ liệu hiển thị | Workflow PSQA hoặc ENGINE_TEST; reference/evaluation artifact+role; 2D/3D; DD mode/value; DTA; global/local; threshold/reference level; alignment/frame; interpolation/search/max gamma; ROI; field/composite; run/attempt/engine. |
| Model/storage | GammaAnalysisRun + `GammaRunAttempt`/lease/`GammaDispatchOutbox`; artifact input/config fingerprint; result manifest and plot artifacts. Bounded retry/dead-letter và plot artifacts đầy đủ vẫn là target còn mở. |
| Operation/API surface | POST/GET /qa-cases/{id}/gamma-runs; GET /gamma-runs/{id}; POST /gamma-runs/{id}/retry; GET compare; /gamma/queue-metrics. |
| Transaction/invariant | At-least-once dispatch + unique run operation + conditional lease commit; ack chỉ sau durable terminal state; stale worker không được ghi đè. |
| Output bàn giao | RTDOSE/measurement fixtures, independent oracle, maps, job diagnostics, benchmark và staged E2E. |
| Success oracle | TC-P08-S01 đến TC-P08-S05 trong plan |
| Error/recovery oracle | TC-P08-E01 đến TC-P08-E10 trong plan |
| Exit | Tất cả profile được công bố có golden/error tests; RTDOSE+measurement 3D staging, worker crash/retry/concurrency và large workload đạt budget. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** `RTDOSE_REQUIRED`; `COMPARISON_REQUIRED`; `GAMMA_INPUT_NOT_VALIDATED`; `GAMMA_ARTIFACT_SCOPE_MISMATCH`; `GAMMA_GRID_METADATA_MISSING`; `GAMMA_WORKFLOW_PROFILE_INVALID`; `GAMMA_ENGINE_TEST_INPUT_INVALID`; `GAMMA_QUEUE_UNAVAILABLE`; engine result warnings `GAMMA_NO_CANDIDATE_WITHIN_DTA` và `GAMMA_SEARCH_CENSORED`; cùng các taxonomy target `GAMMA_INPUT_INCOMPATIBLE`, `GAMMA_RESOURCE_LIMIT` và `GAMMA_SOURCE_CHANGED` khi capability tương ứng được hoàn thiện. Không dùng chuỗi OR làm một code API; mapping phải được giữ trong contract test.

<a id="spec-p09"></a>

### SPEC-P09 — Report Builder, revision, preview và export

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-07; FR-P09-01 đến FR-P09-04 |
| Input và dữ liệu hiển thị | Report/title/source refs; template version; block stable IDs/type/label/order/visible/config; notes; revision; render options/font/locale; export format/status/hash. |
| Model/storage | ReportTemplateVersion, ReportRevision, ReportBlockConfig, ExportJob/Artifact; immutable source bindings. |
| Operation/API surface | Target /report-templates; /reports/{id}/revisions; POST revision exports, GET export status/download; không render side-effect qua GET. |
| Transaction/invariant | Save revision chỉ một lần trên expected revision; export failure không mutate result; giữ file gốc export để byte reproducibility. |
| Output bàn giao | Builder/viewer/history/compare/renderer; visual export fixtures. |
| Success oracle | TC-P09-S01 đến TC-P09-S04 trong plan |
| Error/recovery oracle | TC-P09-E01 đến TC-P09-E06 trong plan |
| Exit | Tùy chỉnh đầy đủ, old revision reproducibility, tiếng Việt/bảng dài, concurrent edit và render retry pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** REPORT_REVISION_CONFLICT; REPORT_SOURCE_UNAVAILABLE; REPORT_CONTENT_INVALID; REPORT_RENDER_FAILED; EXPORT_FORMAT_UNSUPPORTED; DOWNLOAD_LINK_EXPIRED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p10"></a>

### SPEC-P10 — Trend, baseline và sự kiện bảo trì

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-08; FR-P10-01 đến FR-P10-04 |
| Input và dữ liệu hiển thị | Machine/metric/time range/timezone; unit/energy/detector/phantom/protocol/QA cycle; baseline source/effective time; tolerance/action; maintenance events; raw/aggregate series. |
| Model/storage | TrendPoint derived immutable source; BaselineVersion, MaintenanceEvent; filter snapshot. |
| Operation/API surface | Target GET /trend; /trend/{machine_id}; /trend/events; /trend/baselines; scoped export job. |
| Transaction/invariant | Trend là projection tái dựng từ snapshot, không source of truth; event edit có revision. |
| Output bàn giao | Trend dashboard/filter/drill-down và export/large-data checks. |
| Success oracle | TC-P10-S01 đến TC-P10-S04 trong plan |
| Error/recovery oracle | TC-P10-E01 đến TC-P10-E06 trong plan |
| Exit | Không trộn máy/unit; baseline/outlier/timezone/filter/export/drill-down và rebuild pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** TREND_SERIES_INCOMPATIBLE; DATE_RANGE_INVALID; TREND_EMPTY; TREND_BASELINE_INVALID; TREND_DUPLICATE_SOURCE; TREND_SOURCE_ARCHIVED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p11"></a>

### SPEC-P11 — QA Protocol Library và rule version

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-09; FR-P11-01 đến FR-P11-04 |
| Input và dữ liệu hiển thị | Protocol code/title/type/cycle/applicability; version/changelog; rule key/type/unit/baseline/limits/required; reference citation/source type; archive flag. |
| Model/storage | Protocol family + immutable version/rules/reference version; explicit bindings to runs. |
| Operation/API surface | Target /qa-protocols, /qa-protocols/{id}/versions, compare/archive; tương thích endpoint Machine QA hiện có. |
| Transaction/invariant | Version number cấp transaction; clone không chia mutable child; không update snapshot đã dùng. |
| Output bàn giao | Library/editor/version compare/source panel; tích hợp R1 end-to-end. |
| Success oracle | TC-P11-S01 đến TC-P11-S04 trong plan |
| Error/recovery oracle | TC-P11-E01 đến TC-P11-E05 trong plan |
| Exit | Create/clone/version/use/archive và report-old-version tests pass; R1 còn gap phải ghi riêng. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** PROTOCOL_RULE_INVALID; PROTOCOL_VERSION_CONFLICT; REFERENCE_REQUIRED; PROTOCOL_NOT_AVAILABLE; PROTOCOL_CAPABILITY_MISMATCH. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p12"></a>

### SPEC-P12 — Biological Hub và calculation history độc lập

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-10; FR-P12-01 đến FR-P12-04 |
| Input và dữ liệu hiển thị | Scenario name/type/tissue/context/source/assumptions; scenario revision; calculation model/version/input/result; search/history/bookmark. |
| Model/storage | BiologicalScenario, ScenarioRevision, CalculationRun; namespace độc lập QA. |
| Operation/API surface | Target /biological/scenarios, /biological/calculations; /biological/reports; scoped history. |
| Transaction/invariant | Save input không đồng nghĩa đã tính; result liên kết đúng input revision; clone transaction. |
| Output bàn giao | Biological Hub/history/base contracts và independent report integration. |
| Success oracle | TC-P12-S01 đến TC-P12-S04 trong plan |
| Error/recovery oracle | TC-P12-E01 đến TC-P12-E05 trong plan |
| Exit | Không automatic QA linkage; scenario save/reopen/clone/history/export và scoped errors pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** SCENARIO_NOT_FOUND; BIOLOGICAL_CONTEXT_INVALID; SCENARIO_REVISION_CONFLICT; MODEL_VERSION_UNAVAILABLE; MODULE_UNAVAILABLE. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p13"></a>

### SPEC-P13 — BED, EQD2 và đồ thị theo tổng liều

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-11; FR-P13-01 đến FR-P13-04 |
| Input và dữ liệu hiển thị | D [Gy], n nguyên dương, d [Gy/fraction], alpha/beta [Gy], tissue/source/user override; input pair; graph Dmin/Dmax/step, fixed-n hoặc fixed-d, point limit. |
| Model/storage | CalculationRun with input/normalization/model/source/result; ChartDataset snapshot, not pixels only. |
| Operation/API surface | Target POST scenario calculations/charts; GET calculation; chart/download export. |
| Transaction/invariant | Tính từ input revision đã chọn; thay input làm kết quả hiện tại stale, không đổi history. |
| Output bàn giao | Calculator, curves, table/marker, known-answer fixtures và exports. |
| Success oracle | TC-P13-S01 đến TC-P13-S04 trong plan |
| Error/recovery oracle | TC-P13-E01 đến TC-P13-E06 trong plan |
| Exit | Known answers/invalid/curve equality/history/export pass; limits/model assumptions có nguồn hoặc user-defined. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** BIOLOGICAL_INPUT_INVALID; FRACTIONATION_INCONSISTENT; CALCULATION_NONFINITE; CURVE_RANGE_INVALID; ALPHA_BETA_SOURCE_REQUIRED; CALCULATION_PERSISTENCE_FAILED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p14"></a>

### SPEC-P14 — So sánh phác đồ xạ trị

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-12; FR-P14-01 đến FR-P14-04 |
| Input và dữ liệu hiển thị | 2–10 phương án ban đầu; name, D/n/d, tissue/alpha-beta/source/model; baseline option; disease/context/technique/time; absolute/% deltas. |
| Model/storage | ComparisonScenario with stable option IDs, baseline ID, calculation/source snapshots. |
| Operation/API surface | Target POST /biological/comparisons; revision/get/export routes cùng namespace. |
| Transaction/invariant | Một comparison dùng cùng revision của toàn bộ options; không ghép result cũ/mới. |
| Output bàn giao | Multi-option editor/table/chart/compatibility/history/export. |
| Success oracle | TC-P14-S01 đến TC-P14-S04 trong plan |
| Error/recovery oracle | TC-P14-E01 đến TC-P14-E06 trong plan |
| Exit | Known delta, zero baseline, mismatched context và baseline reorder/delete tests pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** COMPARISON_OPTIONS_REQUIRED; COMPARISON_PERCENT_UNDEFINED; COMPARISON_OPTION_INVALID; COMPARISON_CONTEXT_MISMATCH; COMPARISON_BASELINE_REQUIRED; COMPARISON_LIMIT_EXCEEDED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p15"></a>

### SPEC-P15 — Re-irradiation, recovery và bù fraction

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-13; FR-P15-01 đến FR-P15-04 |
| Input và dữ liệu hiển thị | Course IDs/date ranges/D/n/d hoặc fraction list; tissue dose metric/unit/alpha-beta; recovery per prior course/evaluation time/source; no-recovery comparator; planned/delivered/remaining fractions; interruption duration; optional time model. |
| Model/storage | Course/fraction/tissue dose inputs, recovery assumptions, model version, evaluation date; immutable scenario calculations. |
| Operation/API surface | Target /biological/re-irradiation; /biological/fraction-compensation; same scenario version/export contracts. |
| Transaction/invariant | Input snapshot gồm delivered schedule và assumptions; calculation không mutate treatment records. |
| Output bàn giao | Re-irradiation + compensation screens, model contract, timeline, sensitivity/compare, golden/error suite. |
| Success oracle | TC-P15-S01 đến TC-P15-S05 trong plan |
| Error/recovery oracle | TC-P15-E01 đến TC-P15-E08 trong plan |
| Exit | No-recovery/recovery, nonuniform fractions, missing time/context, compensation schedule và independent export pass; spatial không giả lập. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** COURSE_INTERVAL_REQUIRED; RECOVERY_ASSUMPTION_INVALID; CUMULATIVE_CONTEXT_MISMATCH; FRACTION_SCHEDULE_INVALID; SPATIAL_ACCUMULATION_UNAVAILABLE; TISSUE_DOSE_REQUIRED; INTERRUPTION_OVERLAP; FRACTION_COUNT_NONINTEGER. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p16"></a>

### SPEC-P16 — Dose limits, phác đồ điều trị và Knowledge Library

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-14; FR-P16-01 đến FR-P16-04 |
| Input và dữ liệu hiển thị | Disease/subtype/anatomy/intent/technique/fractions; tissue/OAR; metric Dmax/Dmean/Dxcc/Vx/operator/limit/unit; source type/citation/DOI/URL/version/date/evidence/applicability; content/alpha-beta/model. |
| Model/storage | DoseLimitEntryVersion, TreatmentProtocolVersion, KnowledgeEntryVersion, AlphaBetaEntryVersion and citation bindings. |
| Operation/API surface | Target /biological/dose-limits, /treatment-protocols, /knowledge, /alpha-beta; version/search/import/export. |
| Transaction/invariant | Published version immutable; reference selection copied to calculation snapshot, not live pointer only. |
| Output bàn giao | Library/editor/version comparison/source preview; schema fixtures và calculator integration. |
| Success oracle | TC-P16-S01 đến TC-P16-S04 trong plan |
| Error/recovery oracle | TC-P16-E01 đến TC-P16-E06 trong plan |
| Exit | Filter/context/source/version/import/override pass; không seed bảng giới hạn lâm sàng không nguồn. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** KNOWLEDGE_SOURCE_REQUIRED; DOSE_LIMIT_UNIT_INVALID; REFERENCE_LINK_UNAVAILABLE; KNOWLEDGE_IMPORT_INVALID; DOSE_LIMIT_NOT_APPLICABLE; KNOWLEDGE_CONTENT_INVALID. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p17"></a>

### SPEC-P17 — Visual Dose, DVH và structure review

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-15; FR-P17-01 đến FR-P17-04 |
| Input và dữ liệu hiển thị | RTDOSE/RTSTRUCT/CT refs; Frame/series/contour UIDs; patient LPS geometry; ROI ID/name mapping; rasterization/resampling method; dose bins/volume weights/coverage; Dmean/Dx/Vx. |
| Model/storage | Dataset/ROI mapping, TransformArtifact, DVHRun/result/coverage, derived masks/artifacts; raw DICOM immutable. |
| Operation/API surface | Target POST /qa-cases/{id}/dvh-runs; GET run/results; dataset/slice metadata API; Biological dataset namespace riêng. |
| Transaction/invariant | Transform + rasterization + source checksum pinned in one run; result commit sau all required artifacts. |
| Output bàn giao | Dose/DVH viewer, affine/rasterization tests, report integration và benchmarks. |
| Success oracle | TC-P17-S01 đến TC-P17-S04 trong plan |
| Error/recovery oracle | TC-P17-E01 đến TC-P17-E07 trong plan |
| Exit | Geometry, uniform/box/sphere/holes/coverage, Dx/Vx units và staging DVH E2E pass. P17 bắt buộc cho mục tiêu toàn dự án, tùy chọn chỉ cho R1 sớm. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** DVH_INPUT_REQUIRED; DICOM_FRAME_MISMATCH; DVH_EMPTY_STRUCTURE; DVH_INCOMPLETE_COVERAGE; CONTOUR_GEOMETRY_INVALID; DICOM_CAPABILITY_UNSUPPORTED; ANATOMY_INPUT_REQUIRED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p18"></a>

### SPEC-P18 — Kiểm thử tích hợp, độ bền và pilot

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-16; FR-P18-01 đến FR-P18-04 |
| Input và dữ liệu hiển thị | Release manifest; workload/fixture versions; test IDs; failure injection; expected/observed; latency/memory/job counts; restore time/checksum; pilot issue severity. |
| Model/storage | Evidence registry, immutable release manifest, backup inventory, issues/regression fixtures. |
| Operation/API surface | Dùng API sản phẩm thật; không bypass auth hoặc sửa DB để làm E2E thành công. |
| Transaction/invariant | Fault test có điều kiện bắt đầu/kết thúc, tài nguyên mục tiêu và cleanup; không thử lỗi phá dữ liệu trên production. |
| Output bàn giao | Integrated test pack, benchmark report, restore/pilot report, RC manifest. |
| Success oracle | TC-P18-S01 đến TC-P18-S04 trong plan |
| Error/recovery oracle | TC-P18-E01 đến TC-P18-E06 trong plan |
| Exit | Toàn bộ MUST tests pass, không còn SEV0/1; restore/rollback/performance evidence; remaining limitations không vi phạm exit scope. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** RESULT_REGRESSION; RESTORE_INCOMPLETE; DUPLICATE_RESULT; PERFORMANCE_GATE_FAILED; PILOT_CAPABILITY_GAP; RELEASE_EVIDENCE_MISMATCH. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p19"></a>

### SPEC-P19 — Production website và truy cập từ xa

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-16; FR-P19-01 đến FR-P19-04 |
| Input và dữ liệu hiển thị | Approved RC SHA/image digests; API/web/worker/renderer/schema/engine versions; env service IDs; domain/TLS/CORS/Auth URLs; backups; rollback image/schema compatibility. |
| Model/storage | Production DB/object backup, release manifest and deployment evidence; synthetic smoke records marked. |
| Operation/API surface | Public web/API; private DB/Redis/worker. Object store HTTPS signed downloads được phép; bucket không anonymous. |
| Transaction/invariant | Migration expand/contract; không rollback DB bằng destructive downgrade tự động; release gate trên từng service. |
| Output bàn giao | Production URL, remote test evidence, deployment/rollback/runbook và user guide. |
| Success oracle | TC-P19-S01 đến TC-P19-S04 trong plan |
| Error/recovery oracle | TC-P19-E01 đến TC-P19-E06 trong plan |
| Exit | HTTPS + remote workflows + Auth + private dependencies + versions + backup/rollback/alerts đều kiểm chứng. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** PUBLIC_DOMAIN_NOT_READY; PUBLIC_BUILD_CONFIG_MISMATCH; RELEASE_SCHEMA_FAILED; RELEASE_VERSION_MISMATCH; REMOTE_E2E_FAILED; RESOURCE_BUDGET_EXCEEDED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

<a id="spec-p20"></a>

### SPEC-P20 — Gói vận hành ban đầu và cải tiến liên tục

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-16; FR-P20-01 đến FR-P20-04 |
| Input và dữ liệu hiển thị | Owner/contact; monitoring thresholds; backup schedule/retention/restore drill; cost budget; incident severity; release notes; engine version; maintenance calendar. |
| Model/storage | Operations config, backup manifests, runbooks, incident and release records. |
| Operation/API surface | Status/metrics phù hợp đối tượng; alert/backup tích hợp hạ tầng theo cấu hình được triển khai. |
| Transaction/invariant | Maintenance không rewrite history; backup cleanup chỉ sau retention và có bản phục hồi đã kiểm. |
| Output bàn giao | Monitoring+backup cấu hình, alert/restore evidence, guides, ownership và maintenance backlog. |
| Success oracle | TC-P20-S01 đến TC-P20-S04 trong plan |
| Error/recovery oracle | TC-P20-E01 đến TC-P20-E05 trong plan |
| Exit | Gói vận hành ban đầu có config thực, alert test, backup+restore evidence và người phụ trách; vận hành liên tục không có trạng thái hoàn tất vĩnh viễn. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** BACKUP_POLICY_FAILED; ALERT_DELIVERY_FAILED; CAPACITY_WARNING; ENGINE_RESULT_CHANGED; RECURRING_INCIDENT. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

## 9. API hiện có và API mục tiêu

Đối chiếu source ngày sửa tài liệu; phải regenerate/check OpenAPI khi thực hiện code. Base API prefix /api/v1.

| Surface | Đã thấy trong source | Target còn phải kiểm/hoàn thiện |
| :--- | :--- | :--- |
| Health/Auth | health/ready/version, Bearer verifier, session/bootstrap | Schema readiness riêng, refresh/config/error UI và invitation lifecycle. |
| Organization/archive | organization/site/machine, folder/case handlers | Complete restore, membership invitation, optimistic conflicts/filter/history. |
| Artifact | Upload/list/metadata/validate/download/manifest/history | Type mismatch, interrupted/batch, atomic object/DB reconciliation, checksum round-trip evidence. |
| Machine QA | Protocol seed, run create/measurements/evaluate/rerun/compare | Autosave races, full library and boundary coverage. |
| Gamma | Run enqueue/list/detail/retry/compare; queue metrics | PSQA profile, extra config capabilities, denominator/search, leases/outbox, proper DICOM fixtures. |
| Report/trend/protocol library | Có schema/roadmap nền hoặc trend projection | UI/API đầy đủ ở P9–P11, không coi generic endpoints trong technical spec là live. |
| Biological/knowledge/DVH | Requirement/architecture | P12–P17 target; cần source, schema, API, UI và tests. |

Mutation mới phải có typed request/response, operation ID, error mapping, organization scope và idempotency/revision khi phù hợp. Async create trả 202 + run/export ID khi chưa xong; synchronous create có thể 201. List response giữ collection metadata; server không nhúng dump DB/raw patient payload.

Không đổi endpoint existing chỉ để trùng bảng target. Nếu unify generic /analysis-runs hay /jobs, cần adapter/compatibility và client migration; plan không yêu cầu refactor lớn chỉ vì muốn tên đẹp.

## 10. Evidence, traceability và cách xử lý phát hiện mới

Mỗi FR trong business-analysis §21.3 có phase SPEC-Pxx và bộ S/E trong plan. Trước đóng phase, maintainer điền mapping cụ thể FR→S/E/assertion; group mapping ở tài liệu là điểm bắt đầu, không thay acceptance evidence.

| Evidence field | Bắt buộc ghi |
| :--- | :--- |
| Identity | testcase ID, FR, contract version, severity khi fail |
| Setup | fixture version/hash, organization A/B synthetic, input/config exact |
| Execution | command/browser flow, environment, timestamp, SHA/schema/engine/renderer |
| Assertion | expected, observed, precision/coverage policy, counts/checksum/state |
| Output | run/request/export ID, file path/screenshot/log redacted |
| Outcome | PASS/FAIL/BLOCKED/NOT_RUN/N-A + lý do |
| Recovery | cleanup, retry/restore evidence và remaining issue |

Mọi error scenario cần chứng minh cả phản hồi và invariant dữ liệu. HTTP 4xx đúng nhưng DB đã tạo record sai vẫn FAIL. HTTP 200 với map/report sai nguồn vẫn FAIL.

Bug triage: SEV0 mất/cross-org dữ liệu hoặc sai kết quả nghiêm trọng không phát hiện; SEV1 core workflow không dùng được/sai kết quả; SEV2 có workaround trong scope; SEV3 cosmetic. Không tự downgrade severity để release. Release full scope không có SEV0/1; SEV2 vẫn phải kiểm có vi phạm MUST exit không.

Danh sách errors là baseline có giới hạn, không chứng minh bao phủ mọi lỗi tương lai. Khi có dataset/vendor/concurrency pattern mới: tạo test ID mới, link FR, ghi expected bằng reference độc lập, sửa code, run affected regression và version nếu output thay đổi.

## 11. Trình tự thực hiện sau cập nhật tài liệu

1. Đối soát FR mới và evidence cũ; đánh dấu NEEDS_REVALIDATION cho phạm vi chưa đủ.
2. Đã có local closure cho GAP-01/GAP-02/GAP-03/GAP-04/GAP-07 và implementation slice GAP-05; giữ các gate staging/oracle/benchmark mở.
3. Hoàn thiện mapping error flat cho GAP-08 và release/build manifest cho GAP-09; schema revision readiness cho GAP-06 đã có local implementation, cần chứng minh trên staging.
4. Kiểm tra staging đang chạy đúng migration `20260908_0008`; RTDOSE+measurement 3D end-to-end với source đúng frame/profile đã PASS trên run `df38e7d5-bb4b-4e2b-b949-2310acb1875c`, còn queue/outbox và stale-worker negative behavior cần evidence tương ứng.
5. Bổ sung staging crash/ack/dead-letter và resource/large-input benchmark trước khi đóng P8; oracle độc lập, bounded retry và preflight đã có local test.
6. Chỉ sau khi P8 exit đạt mới tiếp tục P9 theo dependency; không triển khai hoặc thay cấu hình cloud chỉ vì tài liệu có checklist.

## 12. Nguồn kỹ thuật đã kiểm tra khi viết

- DICOM RT Dose Module, bản current hiển thị PS3.3 2026c: units, pixel scaling, dose type/summation và references. Link ở §3.4.
- DICOM Grid Frame Offset Vector: hai biểu diễn frame positions. Link ở §3.4.
- PyMedPhys Gamma API: tham số/normalization/cutoff/search, dùng làm ứng viên oracle version-pinned. Link ở §5.3.
- Source repository: core/errors.py, db/session.py, alembic/env.py, api/gamma.py, services/gamma_engine.py, services/artifact_validation.py, worker.py, web env/routes và fixture generator.
- Công thức LQ cơ bản xuất phát từ business-analysis §15.3; recovery profile ở §6.3 là giả định user-defined của sản phẩm, không phải bảng hướng dẫn điều trị.
