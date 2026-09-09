# RT-CONNECT — Đặc tả hành vi, dữ liệu và nghiệm thu

- File: specification.md; version **1.19**; ngày 2026-09-09.
- Nguồn nghiệp vụ: business-analysis.md v0.22.
- Kế hoạch triển khai: plan.md v4.8, P0–P20.
- Kiến trúc nền: technical-specification.md v1.18.
- Đây là hợp đồng mục tiêu. Những nội dung chưa có code được ghi TARGET; kiểm source không thay bằng bằng chứng runtime. Bản 1.19 giữ toàn bộ contract v1.18, bổ sung record semantics cho cgroup memory observation của P17 local Docker workload đồng thời và làm rõ cả sampled container memory lẫn cgroup peak đều không phải peak RSS; đồng thời giữ contract thực thi P4 cho membership/invitation: thành viên ngang quyền, token hash-at-rest, email-bound, one-time, expiry, active-context invariant và các endpoint cụ thể.

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

### 2.6. State machine và operation envelope thống nhất

Mọi resource hoặc operation được triển khai mới phải phân biệt ba giá trị: `lifecycle_status`, `technical_status` và `quality_status`. Không được map trực tiếp HTTP `200` thành `PASS`, cũng không được map lỗi tính toán hợp lệ (`FAIL`) thành lỗi server.

| Trường | Giá trị/kiểu | Quy tắc |
| :--- | :--- | :--- |
| `operation_id` | UUID/string ổn định | Có từ lúc server chấp nhận mutation/job; dùng để query sau timeout. |
| `lifecycle_status` | `NOT_STARTED`, `DRAFT`, `VALIDATING`, `ACCEPTED`, `ARCHIVED`, `CONFLICT`, `UNAVAILABLE` | Trạng thái của resource hoặc command; `DRAFT` không được dùng làm output cuối. |
| `technical_status` | `NOT_STARTED`, `QUEUED`, `RUNNING`, `RETRYING`, `COMPLETED`, `FAILED` | Tiến trình tính/render/queue; chỉ `COMPLETED` mới có output kỹ thuật cuối. |
| `quality_status` | `PASS`, `WARNING`, `FAIL`, `N/A`, `INVALID`, `null` | Kết quả rule/metric; không thay thế `technical_status`. |
| `warnings` | mảng warning có `code`, `message`, `field/location`, `impact` | Warning phải xuất hiện cả ở UI và snapshot nếu output đã lưu. |
| `errors` | mảng error có `code`, `message`, `field/location`, `retryable` | Error không được chứa secret, PHI không cần thiết hoặc stack trace. |
| `provenance` | source IDs/checksum, revision, model/engine/renderer version | Có với calculation/report/export; không trỏ “latest” thay cho revision cụ thể. |
| `next_action` | hành động phục hồi dạng machine-readable/text | Nêu sửa field, refresh/query, retry, restore hoặc tạo revision mới; không phải nút giả. |

State transition chuẩn:

~~~text
NOT_STARTED → DRAFT → VALIDATING
VALIDATING → DRAFT | INVALID | CONFLICT | ACCEPTED
ACCEPTED → QUEUED | RUNNING | COMPLETED | FAILED
QUEUED → RUNNING | RETRYING | FAILED
RUNNING → COMPLETED | RETRYING | FAILED
RETRYING → QUEUED | RUNNING | FAILED
COMPLETED → SUPERSEDED | ARCHIVED
FAILED → RETRYING | DRAFT | ARCHIVED
~~~

`INVALID`, `CONFLICT`, `FAILED` và `UNAVAILABLE` phải có reason; `COMPLETED` phải có output hoặc lý do output rỗng hợp lệ. Không cho phép transition ngầm `FAILED → COMPLETED` bằng cách sửa cùng run; retry hạ tầng giữ nguyên input/config và attempt mới, còn input thay đổi tạo operation/run mới. `SUPERSEDED` là trạng thái lịch sử của resource có revision mới và không được dùng thay cho `ARCHIVED` nếu sản phẩm cần khôi phục.

Nếu client mất response sau khi gửi mutation, UI dùng trạng thái cục bộ `OUTCOME_UNKNOWN` và phải query `operation_id`/idempotency key trước khi báo thất bại hoặc gửi lại. `OUTCOME_UNKNOWN` không phải trạng thái thành công hay lỗi cuối trong database.

### 2.7. Error taxonomy và chính sách phục hồi

Mỗi mã lỗi thực thi phải thuộc một lớp dưới đây, có HTTP mapping, `retryable` và assertion về side effect. Một nguyên nhân chỉ dùng một mã chính; không ghép nhiều mã bằng chuỗi `A_OR_B`.

| Lớp | Ví dụ mã | Retry tự động | Invariant bắt buộc |
| :--- | :--- | :--- | :--- |
| Request/schema | `REQUEST_VALIDATION_FAILED`, `INVALID_FORMAT` | Không | Không tạo resource/job/result; field error giữ input. |
| Authentication | `AUTHENTICATION_REQUIRED`, `AUTH_VERIFICATION_FAILED` | Refresh một lần nếu có session | Không bypass signature; không render cache user cũ. |
| Organization/scope | `MEMBERSHIP_REQUIRED`, `RESOURCE_OUT_OF_SCOPE` | Không | Lookup đầu tiên đã lọc organization; không lộ tồn tại record. |
| Lifecycle/revision | `REVISION_CONFLICT`, `RESOURCE_ARCHIVED` | Không | Không overwrite; giữ draft và tải revision hiện hành. |
| Idempotency/unique | `IDEMPOTENCY_CONFLICT`, `UNIQUE_CONFLICT` | Không | Same fingerprint replay; khác fingerprint không tạo row thứ hai. |
| Dependency/transient | `SERVICE_UNAVAILABLE`, `UPSTREAM_TIMEOUT` | Có giới hạn | Accepted operation giữ ID; không ghi result terminal giả. |
| Persistence uncertain | `PERSISTENCE_UNCERTAIN`, `OBJECT_DB_MISMATCH` | Query/reconcile trước | Xác định DB/object/queue trước retry; không cleanup object đang được tham chiếu. |
| Numeric/geometry | `UNIT_INVALID`, `FRAME_MISMATCH`, `CALCULATION_NONFINITE` | Không | Không đoán unit/transform hoặc bỏ điểm lỗi để tăng PASS. |
| Capacity/security | `PAYLOAD_TOO_LARGE`, `RESOURCE_LIMIT`, `RATE_LIMITED` | Theo `Retry-After`/policy | Không OOM dây chuyền; không retry vô hạn. |
| Render/export | `RENDER_FAILED`, `EXPORT_FORMAT_UNSUPPORTED`, `DOWNLOAD_EXPIRED` | Render/download có điều kiện | Source revision và export cũ không bị sửa. |
| Release/config | `SCHEMA_NOT_READY`, `VERSION_MISMATCH`, `CONFIGURATION_DRIFT` | Không trong request user | Dừng promote/giữ last-good; health 200 không đủ để đóng. |

`retryable=true` chỉ là thuộc tính của error sau khi server xác định operation có thể retry an toàn. Client không được retry vô điều kiện mọi `5xx`. Với mutation không có idempotency, chỉ hiển thị query/reconcile; với async job, retry phải giữ snapshot và tăng attempt. Với warning, operation vẫn có thể `COMPLETED` nhưng `quality_status` hoặc capability phải phản ánh warning; warning không được biến thành error hoặc bị ẩn khỏi provenance.

### 2.8. Evidence record bắt buộc cho nghiệm thu

Mỗi kết quả test/e2e/release phải lưu record có schema tối thiểu sau; giá trị secret/PHI phải redaction trước khi commit:

~~~yaml
evidence_id: "EV-<phase>-<date>-<sequence>"
phase: "Pxx"
test_id: "TC-Pxx-Syy|TC-Pxx-Eyy|Cxx|Gxx"
requirements: ["FR-Pxx-yy"]
contract: "SPEC-Pxx"
environment: "local|staging|production"
source_sha: "<git-sha>"
schema_revision: "<alembic-or-null>"
engine_version: "<version-or-null>"
renderer_version: "<version-or-null>"
fixture_hashes: ["<sha256>"]
organization_scope: "<synthetic-org-id-or-redacted>"
input_fingerprint: "<sha256>"
expected: "<measurable assertion>"
observed: "<measurable result>"
state_assertions: ["<db/object/queue/ui assertions>"]
outcome: "PASS|FAIL|BLOCKED|NOT_RUN|NOT_APPLICABLE"
recovery: "<action and result>"
captured_at: "<ISO-8601>"
artifacts: ["<redacted-log/screenshot/response/path>"]
~~~

Evidence chỉ có HTTP status là `API_SMOKE`, không phải `E2E_PASS`. Với upload phải có checksum round-trip; job phải có attempt/lease/terminal state; calculation phải có known-answer hoặc oracle; report phải có snapshot/format/hash; trend phải có source equality; release phải có service/schema/config manifest. Nếu assertion không quan sát được do thiếu quyền hoặc dependency, ghi `BLOCKED` và next action cụ thể.

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
| TrendPoint | Unique organization+source_run+metric trong projection hiện tại, context snapshot và source lineage; rebuild không thay source. Nếu đổi thuật toán projection trong tương lai, phải tạo projection version/migration riêng trước khi coexist. |
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

DoseLimit là typed entry: disease/subtype, treatment intent, technique, fractionation, structure, metric parameters, comparison operator, limit, dose/volume units, source type/citation/version/applicability. Unknown fractionation không tự match mọi phác đồ. P16 implementation contract chi tiết ở SPEC-P16; implementation hiện dùng một bảng versioned theo `entry_type`, không tạo bốn bảng rời.

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

Query trend dùng khoảng thời gian `[from, to)`: `from` được lấy, `to` bị loại. Nếu UI cho phép chọn “đến hết ngày”, UI phải chuyển sang mốc đầu ngày kế tiếp theo timezone đang hiển thị rồi gửi làm `to`; API không tự đoán ý nghĩa ngày. `day` và `week` bucket theo IANA timezone, nhưng timestamp lưu và source ID vẫn giữ UTC/canonical.

Một series chỉ được nhóm khi cùng `machine_id`, metric meaning, unit và compatibility signature. Khi khác context, response trả nhiều series và warning `TREND_SERIES_INCOMPATIBLE`; không tính mean chung. Aggregate phải bảo toàn count, min/max, first/last, status counts, source point IDs và source run IDs. Baseline lookup dùng effective interval của từng point; thiếu baseline chỉ là warning để user xem raw, không thay bằng 0. Event overlap dùng cùng khoảng `[from,to)` và chỉ là annotation, không phải nguyên nhân tự động của outlier.

Baseline effective date và source snapshot; outlier không bị loại âm thầm. Downsample phải báo method/count/time-buckets, giữ min/max để thấy cực trị; export raw/aggregated chọn rõ. Drill-down source run/report revision, không link report mới nhất không tương ứng.

### 7.3. DVH numeric contract

Dose grid và ROI mask cùng physical frame. CT bắt buộc chỉ cho anatomy overlay; dose-only có thể không CT. DVH bắt RTDOSE+RTSTRUCT.

Volume weights từ geometry; 1 cc = 1.000 mm³. Mask/rasterization, holes/disjoint contours, voxel center/partial volume policy và coverage versioned. Không tự gán dose=0 cho vùng ngoài grid. Full-ROI metrics bị invalid nếu coverage không đủ; overlap-only phải user chọn và được ghi rõ.

Cumulative DVH convention Vx = volume có dose >= x. Vx unit cc hoặc % explicit. Dx = dose quantile ứng với x% volume nhận ít nhất dose đó, interpolation/bin convention pinned. Dxcc đổi x cc/ROI volume rồi dùng cùng quantile; x>ROI volume invalid. Dmin/Dmax của sampled volume khác point-dose physics; Dmean weighted sum/volume. Empty ROI/zero volume cho null+reason.

Analytic fixtures: uniform dose box, unequal voxel sizes, sphere convergence, donut hole, disjoint ROI, duplicated ROI names, structures outside grid, frame transpose/flip. Uniform-grid Dmean error ≤1e-6 Gy; analytic box volume đúng trong tolerance encoding. Sphere/rasterization tolerance phải theo resolution/partial-volume method và convergence report; không đặt một tolerance che mọi grid.

### 7.4. Workload và engineering SLO mục tiêu

Những số dưới là budget nghiệm thu ban đầu, **chưa đo đạt**, cần ghi hardware/resources, software version, cold/warm cache, network và concurrent users trong P8/P18. Không coi gói 5 USD là bảo đảm capacity. P17 đã có local support measurement trong `docs/evidence/p17-local-volume-benchmark-20260909.json` và Docker runtime measurement trong `docs/evidence/p17-local-docker-volume-benchmark-20260909.json`: synthetic `64×128×128` (`1,048,576` voxel), host median `1.2667533 s`, Docker API median `0.8206198 s`; các peak lần lượt là `69,235,606` và `69,237,022` Python-traced bytes. Bổ sung `docs/evidence/p17-local-docker-workload-20260909.json`: 2 Docker jobs đồng thời × 3 lần, cùng engine/oracle, sampled memory cao nhất `142,396,621 bytes` qua `1` mẫu và cgroup v1 peak `367,915,008 bytes` kể từ lúc container start. Cả ba evidence giữ `performance_gate=NOT_ASSESSED`: Python-traced allocation, `docker stats` sample và cgroup peak tích lũy không phải peak RSS; local cgroup không có limit hữu hạn, chưa có pinned service limit, API responsiveness, worker/fault và staging.

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
| Input và dữ liệu hiển thị | Organization name/timezone; site name/code; machine stable ID/name/code/manufacturer/model/energy/mode/status; membership identity/status; invitation email/status/expiry; revision. |
| Model/storage | Organization/Site/Machine + revision; `OrganizationMembership`; `OrganizationInvitation` với token hash, expiry, status và accepted identity; không lưu token thô/password. |
| Operation/API surface | CRUD organization/site/machine; `GET /organizations/{organization_id}/members`; `PATCH /organizations/{organization_id}/members/{membership_id}`; `POST/GET /organizations/{organization_id}/invitations`; `POST /organizations/{organization_id}/invitations/{invitation_id}/revoke`; `POST /organizations/invitations/accept`. |
| Transaction/invariant | Resolve active membership trước mọi organization query; accept tạo/reactivate membership và đánh dấu invitation ACCEPTED cùng transaction; unique pending invitation theo organization/email; một identity không có active context ở organization khác; archive không hard-delete; luôn giữ ít nhất một active member. |
| Output bàn giao | Management screens, `/invite` onboarding, member/invitation lifecycle, audit/history, migration `20260909_0018`, OpenAPI và contract tests. |
| Success oracle | `TC-P04-S01` đến `TC-P04-S08` trong plan |
| Error/recovery oracle | `TC-P04-E01` đến `TC-P04-E12` trong plan |
| Exit | Hai identity cùng organization dùng được nghiệp vụ ngang nhau; invitation email-bound/one-time/expiry/revoke/replay pass; isolate organization khác; rename/archive/restore/concurrent/timeout pass. |

#### SPEC-P04.1 — Quy tắc identity, scope và ngang quyền

1. Mọi endpoint nghiệp vụ P4 yêu cầu Supabase access token hợp lệ và resolve `UserIdentity → active OrganizationMembership → Organization` trước khi truy vấn resource theo ID. `organization_id` từ URL chỉ là assertion cần kiểm tra, không phải nguồn cấp quyền.
2. Một active identity có một active organization context trong baseline này. Invitation tới organization khác khi identity đã có context active bị từ chối bằng `ORGANIZATION_CONTEXT_ALREADY_ASSIGNED` HTTP 409; không tạo membership thứ hai.
3. Tất cả active member trong cùng organization dùng cùng nghiệp vụ. Không có `role`, `owner`, `admin`, `doctor`, `physicist` hoặc action permission branch trong request, model, UI hay endpoint.
4. `is_active` của membership chỉ là trạng thái vòng đời phạm vi. Organization không được rơi vào trạng thái không còn active member: chuyển active member cuối cùng sang inactive trả `LAST_MEMBERSHIP_CONFLICT` HTTP 409 và không đổi row.
5. Không được query global membership/resource rồi mới lọc organization. Với organization khác, endpoint phải trả boundary-safe 403/404 theo contract mà không lộ tên, email, count, invitation status hoặc lịch sử của organization đó.

#### SPEC-P04.2 — Entity và trạng thái invitation

`organization_invitations` có tối thiểu các trường:

| Field | Type/constraint | Semantics |
| :--- | :--- | :--- |
| `id` | UUID primary key | Định danh invitation, không chứa thông tin bí mật. |
| `organization_id` | UUID FK, required | Organization đích; mọi lookup phải kèm scope đã resolve. |
| `invited_email` | string ≤320, required, normalized | Email đã trim/case-fold, dùng đối chiếu với verified email claim. |
| `token_hash` | SHA-256 hex 64, unique, required | Chỉ lưu hash token; không lưu raw token. |
| `status` | `PENDING|ACCEPTED|REVOKED|EXPIRED` | Vòng đời một chiều từ PENDING tới terminal state. |
| `expires_at` | UTC datetime, required | Mặc định +7 ngày, cho phép 1–30 ngày. |
| `accepted_at`/`revoked_at` | UTC datetime nullable | Thời điểm terminal tương ứng. |
| `created_by_user_identity_id` | UUID FK nullable | Actor snapshot cho provenance, không phải role. |
| `accepted_by_user_identity_id` | UUID FK nullable | Verified identity đã nhận; chỉ set khi ACCEPTED. |
| `created_at`/`updated_at` | UTC datetime | Audit thời gian. |

Database phải có unique partial index cho `(organization_id, invited_email)` khi `status='PENDING'`, cùng index phục vụ expiry/organization lookup. `ACCEPTED`, `REVOKED` và `EXPIRED` không thể được accept/revoke lại. Khi đọc invitation PENDING quá hạn, response hiển thị `EXPIRED`; khi mutation kiểm tra quá hạn, backend phải persist trạng thái EXPIRED trước khi trả lỗi nếu transaction còn an toàn.

#### SPEC-P04.3 — API contract cụ thể

Tất cả response lỗi dùng error envelope chung §2.2 với `code`, `message`, `correlation_id`, `details[]`; không trả stack trace/token/password.

| Method/path | Request | Success | Side effect/notes |
| :--- | :--- | :--- | :--- |
| `GET /organizations/{organization_id}/members` | `include_inactive` (default false), `offset ≥0`, `limit 1..100` | 200 `{items,total,offset,limit}`; mỗi member có id/org/email/display_name/is_active | Scope lookup trước; mặc định chỉ active, không có token. |
| `PATCH /organizations/{organization_id}/members/{membership_id}` | `{is_active: boolean}` | 200 member snapshot | Audit + update transaction; chặn last active; mọi active member gọi được. |
| `POST /organizations/{organization_id}/invitations` | `{email, expires_in_days?: 1..30}` | 201 invitation metadata + `token` raw | Raw token chỉ trả response này; hash/row/audit commit cùng transaction. |
| `GET /organizations/{organization_id}/invitations` | `include_closed` (default false), `offset`, `limit` | 200 metadata collection, không có token | Default chỉ PENDING; closed chỉ trả khi gọi rõ. Status expiry được tính đúng UTC. |
| `POST /organizations/{organization_id}/invitations/{invitation_id}/revoke` | none | 200 invitation metadata status REVOKED | Chỉ PENDING; idempotent replay không mở lại token; audit cùng transaction. |
| `POST /organizations/invitations/accept` | `{token}`; Bearer identity phải có verified email | 200 membership `{id,organization_id,email,display_name,is_active}` | Hash token; kiểm status/expiry/org/email/context; membership + ACCEPTED + audit cùng transaction. Cùng token/cùng identity trả cùng member ID. |

Validation request trước transaction:

- Email được trim/case-fold và phải phù hợp format tối thiểu `local@domain`; không chấp nhận chuỗi chỉ có domain, whitespace hoặc vượt 320 ký tự.
- `expires_in_days` là integer 1–30; không làm tròn, clamp hoặc nhận số âm/float/string mơ hồ.
- Token accept phải là chuỗi 20–256 ký tự; token không hợp lệ không được dùng để suy ra organization.
- Invitation create kiểm active member cùng email trước; nếu có trả `INVITATION_ALREADY_MEMBER` 409. Nếu có PENDING chưa hết hạn trả `INVITATION_ALREADY_PENDING` 409. Partial unique index là lớp bảo vệ race cuối cùng.

#### SPEC-P04.4 — Workflow và state assertion

**Tạo invitation:** validate request → resolve active context → kiểm organization active → kiểm member/pending duplicate → tạo raw random token trong memory → lưu SHA-256 + expiry + creator → ghi audit → commit → trả metadata/token một lần. Nếu commit unknown, client query invitation list/operation theo context trước khi tạo lại; không hiển thị “đã tạo” chỉ vì request đã gửi.

**Accept:** nhận token → hash và lookup exact hash → kiểm organization active/status/expiry → resolve/create application identity từ verified subject → kiểm verified email exact normalized → kiểm active context khác → create hoặc reactivate membership → set ACCEPTED/accepted identity/time → audit → commit. Commit race phải rollback; request lặp cùng token và cùng identity chỉ replay membership đã accepted, không tạo row mới.

**Revoke/expire:** resolve context → lookup scoped invitation → chỉ PENDING mới revoke; expiry tự chuyển EXPIRED khi được phát hiện an toàn. Sau terminal status, token không được accept và không được cấp lại bằng cách sửa status; phải tạo invitation mới.

**Member toggle:** resolve context → lookup membership cùng organization → khi deactivate đếm active member → nếu count ≤1 trả conflict không side effect; nếu hợp lệ update + audit transaction → list sau refresh phản ánh status mới.

#### SPEC-P04.5 — Error/recovery mapping

| Condition | HTTP/code | Must not happen | Recovery |
| :--- | :--- | :--- | :--- |
| Identity chưa có active membership khi gọi organization endpoint | 403 `ORGANIZATION_MEMBERSHIP_REQUIRED` | Không auto-create organization, không trả dữ liệu demo. | Về onboarding hoặc accept invitation hợp lệ. |
| URL organization khác membership | 403 `ORGANIZATION_SCOPE_MISMATCH` | Không lộ existence/detail. | Chọn context hiện tại. |
| Email/token/expiry range sai | 422 `REQUEST_VALIDATION_FAILED` | Không tạo row/audit/token. | Sửa field; giữ input hợp lệ. |
| Token không tồn tại, revoked, expired, dùng bởi identity khác | 403/409 `INVITATION_INVALID` | Không tạo/reactivate membership. | Xin token mới hoặc đăng nhập đúng email. |
| Email đã là active member | 409 `INVITATION_ALREADY_MEMBER` | Không tạo invitation dư. | Dùng membership hiện có. |
| Pending cùng organization/email | 409 `INVITATION_ALREADY_PENDING` | Không tạo hai token active. | Dùng token đang có hoặc chờ expiry rồi tạo mới. |
| Identity có active context ở organization khác | 409 `ORGANIZATION_CONTEXT_ALREADY_ASSIGNED` | Không tạo membership thứ hai. | Dùng context hiện tại hoặc tạm ngưng theo workflow rõ ràng trước khi nhận. |
| Membership/invitation ID không thuộc organization | 404/403 boundary-safe `MEMBERSHIP_NOT_FOUND`/`INVITATION_NOT_FOUND` | Không query/return foreign record. | Reload danh sách đúng context. |
| Deactivate active member cuối | 409 `LAST_MEMBERSHIP_CONFLICT` | Không đổi `is_active`. | Giữ ít nhất một active member. |
| Concurrent pending create/update | 409 `INVITATION_CONFLICT`/`MEMBERSHIP_CONFLICT` | Không commit một phần hoặc silent overwrite. | Query current state rồi retry safe. |
| Timeout sau server commit | UI `OUTCOME_UNKNOWN` | Không submit lại mù, không duplicate. | Query ID/list/replay token theo contract. |
| Database/audit commit failure | 409/5xx mapped persistence error | Không báo success hoặc để invitation/membership một phần. | Rollback/reconcile rồi retry bounded. |

#### SPEC-P04.6 — UI, security và evidence contract

- `/app/organization` có các vùng organization/site/machine, Members và Invitations; mỗi vùng có loading, empty, ready, validation, conflict, offline và error state.
- `/invite?token=...` là route public để đọc token từ URL; nếu chưa login, chuyển tới `/auth/login?returnTo=/invite?...` bằng return path nội bộ. Sau login, gọi accept một lần; không lưu raw token vào localStorage, analytics, audit hoặc log.
- Sau create, UI cho copy token/link và nói rõ token chỉ xuất hiện trong phiên tạo. Sau refresh hoặc list, token biến mất khỏi response/list.
- UI phải phân biệt `INVITATION_INVALID`, `ORGANIZATION_CONTEXT_ALREADY_ASSIGNED`, `LAST_MEMBERSHIP_CONFLICT` và outage; không gom tất cả thành “không có organization”.
- Evidence tối thiểu: response đã redaction, invitation/member IDs, DB row kiểm `token_hash` không phải token raw, status transition, audit event, organization scope, migration/OpenAPI SHA, browser route và replay/negative result.

#### SPEC-P04.7 — Current implementation boundary

Local source đã có model/API/migration `20260909_0018`, frontend client, organization management member/invitation panels và public `/invite` route. Focused API, migration contract, Ruff/mypy và frontend checks phải được ghi trong progress packet. Đây chưa phải `STAGING_VERIFIED`: staging phải chạy migration head `20260909_0018`, deploy cùng candidate, kiểm Auth thực, browser accept/replay/revoke/expiry, PostgreSQL rows và scope/timeout evidence trước khi mở P5.

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** `MACHINE_CODE_CONFLICT`; `PARENT_NOT_AVAILABLE`; `REVISION_CONFLICT`; `INVITATION_INVALID`; `INVITATION_ALREADY_MEMBER`; `INVITATION_ALREADY_PENDING`; `INVITATION_CONFLICT`; `ORGANIZATION_CONTEXT_ALREADY_ASSIGNED`; `LAST_MEMBERSHIP_CONFLICT`; `MEMBERSHIP_NOT_FOUND`; `INVITATION_NOT_FOUND`; `MUTATION_RESULT_UNKNOWN`. Các mã đã có trong source là mapping hiện tại; mã chưa có route tương ứng vẫn là target và phải được ghi trong contract test trước khi tuyên bố phase hoàn tất.

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
| Model/storage | `report_template_versions`, `report_revisions`, `report_block_configs`, `export_jobs` trong migration `20260908_0009`; rendered bytes ở object storage qua `Artifact`-compatible storage contract; immutable source bindings. |
| Operation/API surface | **Đã có local:** `GET/POST /organizations/{organization_id}/report-templates`; `POST /report-templates/{template_id}/versions`; `GET/POST /organizations/{organization_id}/reports`; `GET /reports/{report_key}`; `GET /reports/{report_key}/revisions`; `GET/POST /reports/{report_key}/revisions`; `GET/POST /reports/{report_key}/revisions/{revision_id}/exports`; `GET /report-exports/{job_id}`; `GET /report-exports/{job_id}/download`. Không render side-effect qua GET. |
| Transaction/invariant | Save revision chỉ một lần trên expected revision; export failure không mutate result; giữ file gốc export để byte reproducibility. |
| Output bàn giao | Builder/viewer/history/compare/renderer; visual export fixtures. |
| Success oracle | TC-P09-S01 đến TC-P09-S04 trong plan |
| Error/recovery oracle | TC-P09-E01 đến TC-P09-E06 trong plan |
| Exit | Tùy chỉnh đầy đủ, old revision reproducibility, tiếng Việt/bảng dài, concurrent edit và render retry pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** REPORT_REVISION_CONFLICT; REPORT_SOURCE_UNAVAILABLE; REPORT_CONTENT_INVALID; REPORT_RENDER_FAILED; EXPORT_FORMAT_UNSUPPORTED; DOWNLOAD_LINK_EXPIRED. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

**P9 implementation contract hiện tại:** `ReportRevision.source_snapshot` là nguồn dữ liệu của revision, không phải live query khi mở lại. Khi tạo revision mới từ `QA_CASE`, backend đọc case hiện tại trong đúng organization rồi ghi snapshot mới; revision cũ không đổi. Block có stable ID, type, label, sort order, visibility, config và source binding; user có thể ẩn hoặc xóa warning/provenance khỏi layout theo quyết định sản phẩm, nhưng hệ thống vẫn giữ content hash, source snapshot, actor và timestamps ở lineage. Nội dung JSON tree bị giới hạn depth/size, số phải finite, block ID/order phải duy nhất; script, `javascript:` và payload nguy hiểm bị từ chối. Renderer hiện hỗ trợ JSON, CSV, PDF và PNG; output được hash, lưu object storage và trả signed URL. PDF fallback nếu không có font Unicode phù hợp phải ghi `warning_snapshot`, không được giả vờ rằng bản render tiếng Việt hoàn hảo. Cùng organization + idempotency key + fingerprint phải trả export cũ; cùng key khác request phải trả conflict.

<a id="spec-p10"></a>

### SPEC-P10 — Trend, baseline và sự kiện bảo trì

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-08; FR-P10-01 đến FR-P10-04 |
| Input và dữ liệu hiển thị | Machine/metric/time range/timezone; unit/energy/detector/phantom/beam_quality/acquisition_mode/protocol/QA cycle; baseline source/effective time; tolerance/action; maintenance events; raw/day/week series. |
| Model/storage | `TrendPoint` là projection immutable theo `organization_id + source_run_id + metric_key`, có `context_snapshot`; `BaselineVersion` versioned theo machine/metric; `MaintenanceEvent` có current revision và `MaintenanceEventRevision` append-only. |
| Operation/API surface | `GET /organizations/{organization_id}/trend`; `GET /organizations/{organization_id}/trend/export`; `POST /organizations/{organization_id}/trend/rebuild`; `GET/POST /organizations/{organization_id}/trend/baselines`; `PATCH /trend-baselines/{baseline_id}`; `GET/POST /organizations/{organization_id}/trend/events`; `PATCH /trend-events/{event_id}`; `GET /trend-events/{event_id}/revisions`; `GET /trend-points/{point_id}/source`. |
| Query contract | `machine_ids` là danh sách UUID phân tách bằng dấu phẩy; `metric_key`, `unit`, context và `protocol_key/qa_cycle` là filter exact; `aggregate ∈ {raw, day, week}`; `from` inclusive, `to` exclusive; timezone là IANA ZoneInfo; machine phải thuộc organization trước khi load points. |
| Compatibility contract | Mỗi point tạo signature SHA-256 rút gọn từ `unit, qa_type, qa_cycle, protocol_key, protocol_version, energy, detector, phantom, beam_quality, acquisition_mode`. Các signature khác nhau là series khác nhau; không nội suy hoặc quy đổi unit/context ngầm. |
| Baseline contract | Chọn baseline `ACTIVE` cùng machine/metric/unit/context, `effective_from ≤ measured_at < effective_to` (hoặc không có end), ưu tiên `effective_from` mới nhất rồi `version_number` cao nhất. `delta = value - baseline_value`; `is_outlier = abs(delta) > action_level` nếu có, nếu không dùng tolerance. Thiếu baseline chỉ tạo warning, không thay raw value. |
| Aggregate contract | `day/week` nhóm theo timezone đã chọn; mỗi bucket giữ `count`, mean, min, max, first/last, status counts, toàn bộ source point IDs và source run IDs. Raw series vẫn là nguồn drill-down; aggregate không được làm mất lineage. |
| Event contract | Tạo event ở revision 1; PATCH bắt buộc `expected_revision`; sửa thành công tăng revision và ghi snapshot mới; revision conflict trả 409, không overwrite. Event chỉ là marker trên trend, không sửa QA result. |
| Rebuild contract | Rebuild đọc completed Machine QA result snapshots cùng organization, tạo thiếu point hoặc sửa context projection, không tạo trùng nhờ uniqueness; trả số `scanned_runs/created_points/existing_points/repaired_context_points`. Source run/result là authority. |
| Export contract | CSV raw có header và source IDs; JSON chứa cùng `TrendResponse` gồm filter/timezone/aggregate/series/warnings; export phải tái hiện đúng query và không xuất điểm ngoài scope. |
| Output bàn giao | Trend dashboard/filter/drill-down, baseline/event history, raw/day/week aggregate, table fallback và export/large-data checks. |
| Success oracle | TC-P10-S01 đến TC-P10-S08 trong plan |
| Error/recovery oracle | TC-P10-E01 đến TC-P10-E12 trong plan |
| Exit | Không trộn máy/unit/context; baseline/outlier/timezone/filter/export/drill-down/rebuild, revision conflict và large-series behavior pass. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract hiện tại và target:** `TREND_SERIES_INCOMPATIBLE` là warning khi nhiều compatible signature; `DATE_RANGE_INVALID`, `TREND_TIMEZONE_INVALID`, `TREND_FILTER_INVALID`, `TREND_EMPTY`, `TREND_BASELINE_INVALID`, `TREND_BASELINE_NOT_FOUND`, `TREND_BASELINE_VERSION_CONFLICT`, `TREND_SOURCE_ARCHIVED`, `TREND_SOURCE_UNAVAILABLE`, `TREND_DUPLICATE_SOURCE`, `TREND_QUERY_TOO_LARGE`, `MAINTENANCE_INTERVAL_INVALID`, `MAINTENANCE_EVENT_CONFLICT`, `MAINTENANCE_EVENT_NOT_FOUND` và `MAINTENANCE_REVISION_CONFLICT` là các mã cần được kiểm qua response contract. Input invalid không được retry tự động; conflict phải reload/copy; query quá lớn phải chuyển aggregate; source archived vẫn được xem lịch sử với nhãn. Không biến `TREND_EMPTY` thành lỗi 500 và không tạo điểm 0 thay dữ liệu trống.

**P10 implementation status 2026-09-08:** schema `20260908_0010`, API và frontend trend slice đã có; Ruff/mypy, full backend `68/68` và P10 focused `7/7` pass local; migration đã chạy trên PostgreSQL local. Staging migration, authenticated browser trend workflow, large-series benchmark, event/baseline persistence và visual/accessibility evidence vẫn là TARGET/OPEN cho đến khi ghi vào progress log.

<a id="spec-p11"></a>

### SPEC-P11 — QA Protocol Library và rule version

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-09; FR-P11-01 đến FR-P11-04 |
| Mục đích | Quản lý protocol family/version/rule có nguồn và applicability; cho phép dùng version cụ thể cho run mới mà không thay đổi run/report/trend cũ. |
| Status | `DRAFT` có thể sửa; `ACTIVE` được chọn cho run mới; `ARCHIVED` chỉ đọc lịch sử và không được chọn cho run mới. `ACTIVE`/`ARCHIVED` immutable. |
| Input/header | `protocol_key`, `name`, `qa_type`, `description`, `effective_note`, `applicability`, `source_type`, `source_reference`, `rules[]`; create mặc định DRAFT, có thể activate sau validation. |
| Rule | `metric_key`, `display_name`, `unit`, `rule_type`, `target_value`, `lower_limit`, `upper_limit`, `tolerance`, `action_level`, `required`, `sort_order`, `note`, `reference`. Rule key lowercase ổn định và unique trong version. |
| Applicability | Chỉ nhận các dimension công bố: `site_ids`, `machine_ids`, `qa_cycles`, `qa_types`, `energies`, `beam_qualities`, `techniques`, `detectors`, `phantoms`; mỗi dimension là danh sách string không rỗng. Không có dimension nghĩa là không ràng buộc theo chiều đó, không tự suy ra machine/site. |
| Source | `USER_DEFINED`, `REFERENCE`, `INTERNAL`, `SITE_APPROVED`. `REFERENCE` bắt buộc `source_reference`; `SITE_APPROVED` là mô tả nội bộ, không tạo thêm cấp phê duyệt hay role. |
| Model/storage | `QAProtocolVersion` thuộc organization, có `version_number`, `revision`, status, actor/timestamps, lineage `source_protocol_version_id`; `QAProtocolRule` thuộc version và organization. Migration hiện thực `20260908_0011`. |
| Lineage/snapshot | Clone deep-copy rule thành ID mới và ghi source version. P7/P8/P9/P10 phải snapshot protocol/rule/limit/source lúc operation được accepted; không resolve lại live version khi mở history. |
| Transaction/invariant | Validate-only không ghi DB. Create/update/clone/activate/archive ghi header, rules và audit atomically. Version number monotonic trong family; optimistic `expected_revision` bắt buộc cho PATCH/transition. Không hard-delete version đã được dùng. |
| Operation/API surface | Xem bảng route bên dưới; base prefix là `/api/v1`. Existing Machine QA protocol list chỉ trả protocol `ACTIVE` cho run mới. |
| Output bàn giao | Library/editor, validate preview, clone, lifecycle command, compare diff, source/applicability panel, Machine QA consumer và history snapshot. |
| Success oracle | TC-P11-S01 đến TC-P11-S09 trong `plan.md`. |
| Error/recovery oracle | TC-P11-E01 đến TC-P11-E16 trong `plan.md`; đồng thời áp dụng C01–C11 và C15/C16 khi phù hợp. |
| Exit | Local migration/tests/build/OpenAPI pass; staging browser và consumer E2E chứng minh create→validate→save→activate→use→clone→compare→archive, old snapshot, scope, conflict, persistence uncertain và capability errors. |

#### SPEC-P11.1 — API routes và request/response contract

| Method | Route | Request chính | Response/side effect |
| :--- | :--- | :--- | :--- |
| POST | `/organizations/{organization_id}/qa-protocols/validate` | `ProtocolDefinitionFields` | `200 {valid, errors[], warnings[]}`; không tạo protocol/rule/audit. |
| GET | `/organizations/{organization_id}/qa-protocols` | `q`, `status`, `include_archived`, `offset`, `limit` | `ProtocolCollectionResponse`; list mặc định chỉ DRAFT/ACTIVE, archive chỉ khi explicit. |
| POST | `/organizations/{organization_id}/qa-protocols` | Definition + `activate?` | `201 ProtocolResponse`; version tiếp theo của family, DRAFT hoặc ACTIVE. |
| GET | `/organizations/{organization_id}/qa-protocols/{protocol_id}` | path ID | `200 ProtocolResponse`; kiểm organization trước lookup. |
| PATCH | `/organizations/{organization_id}/qa-protocols/{protocol_id}` | `expected_revision` + field muốn đổi | `200 ProtocolResponse`; chỉ DRAFT, revision tăng; field nullable đã gửi có thể clear. |
| POST | `/{protocol_id}/clone` | `name?`, `protocol_key?`, `activate?` | `201 ProtocolResponse`; version mới và child rules độc lập. |
| POST | `/{protocol_id}/activate` | `expected_revision` | `200 ProtocolResponse`; DRAFT hợp lệ thành ACTIVE, revision tăng. |
| POST | `/{protocol_id}/archive` | `expected_revision` | `200 ProtocolResponse`; ACTIVE/DRAFT thành ARCHIVED, detail/history vẫn đọc. |
| GET | `/{protocol_id}/compare?other_id={id}` | hai ID cùng organization | `ProtocolCompareResponse`; metadata/rule diff, không mutation. |

`ProtocolResponse` tối thiểu gồm: `id`, `organization_id`, `protocol_key`, `name`, `qa_type`, `version_number`, `status`, `revision`, `description`, `effective_note`, `applicability`, `source_type`, `source_reference`, `source_protocol_version_id`, actor/timestamps và `rules[]`. `ProtocolRuleResponse` phải trả stable rule ID, key, display/unit/type, numeric limits, required/order/note/reference.

#### SPEC-P11.2 — Validation và error mapping

| Điều kiện | Error/status | Invariant và phục hồi |
| :--- | :--- | :--- |
| Request shape, key/name/type/field whitespace hoặc format sai | `REQUEST_VALIDATION_FAILED` hoặc `PROTOCOL_RULE_INVALID` / 422 | Giữ form; không mutation. |
| Applicability key lạ, không phải string list, item rỗng | `PROTOCOL_APPLICABILITY_INVALID` / 422 | Chỉ rõ `applicability.<dimension>`; không coi là wildcard. |
| Rule key trùng/sai format, unit/display rỗng, type không support | `PROTOCOL_RULE_INVALID` hoặc duplicate là `PROTOCOL_VERSION_CONFLICT` / 422 | Không lưu một phần; giữ các rule hợp lệ trong draft UI. |
| RANGE thiếu lower/upper hoặc lower > upper | `PROTOCOL_RULE_INVALID` / 422 | Không tự đảo/clamp giới hạn. |
| MIN/MAX thiếu giới hạn; tolerance/action âm; deviation thiếu target/tolerance | `PROTOCOL_RULE_INVALID` / 422 | Field-level error; activate bị chặn. |
| Percent target bằng 0 hoặc numeric non-finite | `PROTOCOL_RULE_INVALID` / 422 | Không chia 0/serialize NaN/Infinity. |
| `REFERENCE` thiếu `source_reference` | `REFERENCE_REQUIRED` / 422 | Bổ sung citation hoặc đổi source type explicit. |
| Conflict version/key/unique hoặc request cùng operation khác payload | `PROTOCOL_VERSION_CONFLICT` / 409 | Reload/query kết quả; không overwrite. |
| `expected_revision` cũ hoặc hai tab cùng sửa | `PROTOCOL_VERSION_CONFLICT` / 409 | Giữ draft local, show diff/clone, retry với revision mới. |
| Edit ACTIVE/ARCHIVED | `PROTOCOL_VERSION_IMMUTABLE` / 409 | Clone hoặc tạo version mới; lịch sử vẫn đọc. |
| Activate ARCHIVED/chọn inactive cho run mới | `PROTOCOL_NOT_AVAILABLE` / 409 | Chọn ACTIVE explicit; không biến archive thành active bằng retry mù. |
| Consumer không hỗ trợ rule/capability | `PROTOCOL_CAPABILITY_MISMATCH` / 409 hoặc preflight error | Nêu rule/capability; không drop rule và không tạo PASS giả. |
| Organization ngoài membership hoặc ID không tồn tại | `ORGANIZATION_SCOPE_MISMATCH` / 403 hoặc `PROTOCOL_NOT_FOUND` / 404 | Không lộ existence/detail/rules ngoài scope. |
| DB/audit/rule persistence lỗi | `PROTOCOL_PERSISTENCE_FAILED` / 503 | Rollback header+rules+audit; retry bounded sau khi kiểm tra kết quả. |
| Mất mạng sau commit trước response | `MUTATION_RESULT_UNKNOWN` / client recovery | Tra list/detail bằng request context/ID trước khi gửi lại. |
| Timeout/session expired/response schema sai | `SERVICE_UNAVAILABLE` hoặc `SESSION_UNAVAILABLE` | Stop spinner, refresh session tối đa theo policy, giữ filter/draft và retry có giới hạn. |

#### SPEC-P11.3 — Consumer contract

1. Machine QA chỉ nhận protocol `ACTIVE`; endpoint library mặc định không đưa `ARCHIVED` vào danh sách lựa chọn run mới.
2. Run creation phải pin `protocol_version_id` và copy `protocol_key`, `version_number`, rule key/type/unit/limits, applicability, source và engine capability result vào snapshot. Không được chỉ lưu family key rồi resolve version mới khi evaluate.
3. Khi protocol bị archive hoặc có version mới, run/report/trend cũ vẫn mở đúng snapshot; run mới phải chọn lại version active explicit.
4. P8 Gamma chỉ dùng protocol rule nếu preflight capability xác nhận; rule không hỗ trợ là lỗi rõ ràng. P9 report có thể trình bày snapshot theo layout tùy người dùng nhưng không được đổi source snapshot. P10 trend giữ protocol version/context trong compatibility signature.
5. Mọi member active trong organization có cùng đường đi API/UI. `created_by`, audit và revision dùng cho provenance/concurrency, không phải phân quyền hành động.

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer phải recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** Các mã ở SPEC-P11.2 là taxonomy có thể kiểm chứng. Nếu code triển khai dùng tên tương đương, phải cập nhật OpenAPI, test mapping và plan cùng commit; không để tài liệu và response thực tế lệch nhau.

**P11 implementation status 2026-09-08:** migration `20260908_0011` đã ở head trên PostgreSQL local. Backend full suite `81/81`, focused `test_protocol_library.py` `3/3`, Ruff/mypy, frontend lint/typecheck/Vitest `1/1` và build đã pass local. Đây mới là local implementation evidence; staging browser, consumer snapshot qua P7/P8/P9/P10, complete error/boundary matrix, visual/accessibility và release manifest vẫn mở.

<a id="spec-p12"></a>

### SPEC-P12 — Biological Hub và calculation history độc lập

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-10; FR-P12-01 đến FR-P12-04 |
| Input và dữ liệu hiển thị | `scenario_key` uppercase stable key; name/type/tissue/clinical context; `source_type` + reference; finite JSON `assumptions`; status/revision/lineage; tool capability; calculation model/version/input/result; P13 BED/EQD2 fields khi calculator được mở. |
| Model/storage | `BiologicalScenario`, `BiologicalScenarioRevision`, `BiologicalCalculationRun`; namespace độc lập QA, không bắt buộc `qa_case_id`/patient FK. Migration implementation: `20260908_0012`; executable P13 idempotency field: `20260908_0013`. |
| Operation/API surface | `/api/v1/organizations/{organization_id}/biological/tools`, `/summary`, `/scenarios`, `/scenarios/{id}/revisions`, `/calculations` và `/calculations/{id}`; report Biological là integration target của P9/P12. |
| Transaction/invariant | Validate-only không mutation; create/update/transition ghi scenario + revision + audit atomic; save input không đồng nghĩa đã tính; calculation phải pin input revision; clone giữ source revision lineage; archived không bị xóa. |
| Output bàn giao | Biological Hub/history/base contracts và independent report integration. |
| Success oracle | TC-P12-S01 đến TC-P12-S09 trong plan |
| Error/recovery oracle | TC-P12-E01 đến TC-P12-E12 trong plan |
| Exit | Local + staging route/mutation/snapshot/scope evidence; không automatic QA linkage; report integration và capability state không được giả. |

#### SPEC-P12.1 — Canonical resource fields

| Resource | Required contract |
| :--- | :--- |
| `BiologicalScenario` | `id: UUID`; `organization_id: UUID`; `scenario_key: string` matching `^[A-Z][A-Z0-9_.-]{0,119}$`, unique within organization; `name` 1–240; `scenario_type` 1–80; `tissue_context` 1–240; nullable `clinical_context` ≤4000; `source_type ∈ {USER_DEFINED,REFERENCE,INTERNAL,SITE_APPROVED}`; nullable `source_reference` ≤1000; `assumptions: JSON object`; `status ∈ {DRAFT,SAVED,ARCHIVED}`; positive integer `revision`; optional `source_scenario_revision_id`; actor/timestamps. |
| `BiologicalScenarioRevision` | `id`, organization/scenario IDs, monotonic `revision_number`, copied status, immutable `snapshot`, actor and creation time. Unique by `(scenario_id, revision_number)`; every current scenario revision must have one snapshot. |
| `BiologicalCalculationRun` | `id`, organization/scenario/revision IDs, `calculation_type`, optional `idempotency_key`, `model_key`, `model_version`, technical status, immutable `input_snapshot`/`result_snapshot`, warning/error snapshots, actor/timestamps. P12 exposes the read contract; P13 owns BED/EQD2 creation; P14 consumes completed P13 snapshots in `BiologicalComparisonRun`; P15 owns later course/recovery calculations. |

`clinical_context` is a working note, not a patient record. The API/UI must not accept a patient identifier as a hidden lookup key. A user-provided dataset is a separate explicit source contract and must carry source identity/checksum before a later module can consume it.

#### SPEC-P12.2 — Exact operation contract

| Method and path | Request | `2xx` behavior | Side effect |
| :--- | :--- | :--- | :--- |
| `GET /organizations/{org}/biological/tools` | None | `200` list of six tools with `tool_key`, label, route, phase, status, description and `available` | No mutation; P13 and P14 are `AVAILABLE/true`, tools not implemented yet return `PLANNED/false`. |
| `GET /organizations/{org}/biological/summary` | None | `200` organization-scoped counts for total/draft/saved/archived scenarios, completed calculations and biological exports | No mutation. |
| `POST /organizations/{org}/biological/scenarios/validate` | Create-shaped scenario | `200 {valid, errors[], warnings[]}`; valid response does not mean persisted | None. Duplicate key is a validation result, not a partial create. |
| `GET /organizations/{org}/biological/scenarios` | `q`, `status`, `include_archived`, `offset`, `limit` | Typed collection, stable `updated_at DESC` order, total and effective archive flag | No mutation; archived excluded unless explicit status/include flag. |
| `POST /organizations/{org}/biological/scenarios` | Create-shaped scenario | `201` DRAFT scenario at revision 1 with initial snapshot | Scenario, revision and audit commit together. |
| `GET /organizations/{org}/biological/scenarios/{id}` | None | `200` detail with latest snapshot | No mutation; lookup is organization-scoped before detail. |
| `GET /organizations/{org}/biological/scenarios/{id}/revisions` | None | `200` newest-first immutable revision list | No mutation. |
| `PATCH /organizations/{org}/biological/scenarios/{id}` | `expected_revision` + one or more editable fields | `200` updated DRAFT with exactly one revision increment | Only DRAFT; update, revision snapshot and audit are atomic. |
| `POST /organizations/{org}/biological/scenarios/{id}/save` | `expected_revision` | `200` SAVED scenario with one new revision | Only DRAFT; saved content becomes immutable. |
| `POST /organizations/{org}/biological/scenarios/{id}/clone` | Optional valid new key/name | `201` new DRAFT rev 1 with source revision lineage | New ID/key; source unchanged; clone snapshot is independent. |
| `POST /organizations/{org}/biological/scenarios/{id}/archive` | `expected_revision` | `200` ARCHIVED scenario with one new revision | History remains readable; archive is not hard delete. |
| `GET /organizations/{org}/biological/calculations` | Optional `scenario_id`, `offset`, `limit` | Typed calculation collection scoped to org/scenario | No mutation. |
| `GET /organizations/{org}/biological/calculations/{id}` | None | `200` immutable calculation snapshot | No mutation; P12 reads and P13 persists only BED/EQD2 results under its own contract. |

#### SPEC-P12.3 — State and error mapping

| Condition | HTTP/contract | Required recovery and invariant |
| :--- | :--- | :--- |
| Missing/expired bearer or Auth outage | `401` `SESSION_UNAVAILABLE` or shared auth error | Reauthenticate/refresh once according to policy; never anonymous fallback; retain safe UI draft. |
| Organization mismatch | `403` `ORGANIZATION_SCOPE_MISMATCH` | Stop before resource lookup; do not reveal whether the ID exists. |
| Scenario/revision/calculation not found inside scope | `404` `SCENARIO_NOT_FOUND` or `CALCULATION_NOT_FOUND` | Generic not-found UI; no cross-org metadata. |
| Pydantic shape/key/range error | `422` shared validation envelope / `REQUEST_VALIDATION_FAILED` | Field-level messages; no mutation. Clone keys use the same regex as create. |
| Unsupported source or non-finite assumptions | `422` `BIOLOGICAL_CONTEXT_INVALID` | Correct field and retained form; no implicit conversion or citation. |
| `REFERENCE` has no citation | `422` `BIOLOGICAL_CONTEXT_INVALID` | Require `source_reference`; do not invent source. |
| Duplicate organization key | `409` `SCENARIO_KEY_CONFLICT` | Query/open existing item or choose another key; no second scenario. |
| Stale `expected_revision` | `409` `SCENARIO_REVISION_CONFLICT` | Reload current version or clone; never silently overwrite. |
| Edit/save already SAVED or ARCHIVED | `409` `SCENARIO_IMMUTABLE` | Preserve old snapshot; clone for a new working scenario. |
| Archive already ARCHIVED | `409` `SCENARIO_IMMUTABLE` | No extra revision or deletion. |
| No editable fields in PATCH | `400` `NO_CHANGES` | Keep current snapshot and ask for a real change. |
| Database/commit failure | `503` `SCENARIO_PERSISTENCE_FAILED` | Roll back transaction; retry only after checking whether the prior operation committed. |
| Client loses response after mutation | `409/503` `MUTATION_RESULT_UNKNOWN` target | Query by returned/request idempotency context before retry; do not assume “not created”. |
| Tool is not implemented | Capability response `PLANNED`/`available=false`; calculation command is not exposed | Show disabled CTA and preserve scenario; no fake RUNNING/COMPLETED calculation. |

Current P12 implementation provides the route/resource/lifecycle contract above. P13 creates BED/EQD2 calculation runs under SPEC-P13, P14 creates comparison snapshots and P15 creates separate re-irradiation/fraction-compensation run snapshots under SPEC-P15. Biological report integration remains a separate P9/P12 work package. A capability is not described as available until its own tests and evidence pass.

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract:** SPEC-P12.3 là mapping chi tiết. Những mã target chưa xuất hiện trong route lifecycle hiện tại (`MODEL_VERSION_UNAVAILABLE`, `MODULE_UNAVAILABLE`, `MUTATION_RESULT_UNKNOWN`) phải được dùng khi module/operation tương ứng được mở; không giả vờ đã kiểm chứng chúng ở local chỉ vì tài liệu đã liệt kê.

**P12 implementation status 2026-09-08:** migration `20260908_0012` đã upgrade tới head trên PostgreSQL local; route/API/UI và `test_biological.py` focused pass. Browser staging đã chạy create/validate/edit/save/clone/archive/history bằng dữ liệu tổng hợp; PostgreSQL-state, refresh/reconnect, P9 Biological renderer integration, complete negative matrix và release manifest vẫn mở.

<a id="spec-p13"></a>

### SPEC-P13 — BED, EQD2 và đồ thị theo tổng liều

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-11; FR-P13-01 đến FR-P13-04 |
| Input và dữ liệu hiển thị | `scenario_revision_id` của revision SAVED; D [Gy], n nguyên dương, d [Gy/fraction], alpha/beta [Gy], source type/reference; consistency tolerance; graph Dmin/Dmax/step, `FIXED_N` hoặc `FIXED_D`, fixed-n/fixed-d, tối đa 10 alpha/beta series và point limit. |
| Model/storage | `BiologicalCalculationRun` với idempotency key, request fingerprint, input/raw + normalized snapshots, model/source/result; `ChartDataset` snapshot gồm series/table/checksum, không chỉ lưu ảnh. |
| Operation/API surface | `POST .../scenarios/{id}/calculations/validate`; `POST .../scenarios/{id}/calculations`; `POST .../calculations/{id}/charts`; `GET .../calculations/{id}/export?export_format=JSON|CSV`; calculation history đọc qua P12 route. |
| Transaction/invariant | Tính từ revision SAVED đã chọn; validate-only không mutation; calculation đầu tiên 201, replay cùng key/input 200, key khác input 409; chart preview không mutation; thay input/scenario không đổi history. |
| Output bàn giao | Calculator, curves, table/marker, known-answer fixtures và exports. |
| Success oracle | TC-P13-S01 đến TC-P13-S08 trong plan |
| Error/recovery oracle | TC-P13-E01 đến TC-P13-E10 trong plan |
| Exit | Local engine/API/UI/migration gates pass; staging phải chứng minh DB snapshot, replay không duplicate, chart/table/export cùng checksum và no-QA linkage. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Failure contract đã map cho P13:** `BIOLOGICAL_INPUT_INVALID`, `FRACTIONATION_INCONSISTENT`, `CALCULATION_NONFINITE`, `CURVE_RANGE_INVALID`, `ALPHA_BETA_SOURCE_REQUIRED`, `CALCULATION_IDEMPOTENCY_CONFLICT`, `CALCULATION_PERSISTENCE_FAILED`, `SCENARIO_REVISION_NOT_FOUND`, `SCENARIO_IMMUTABLE`, `ORGANIZATION_SCOPE_MISMATCH`, `CALCULATION_NOT_FOUND` và lỗi schema 422 của FastAPI/Pydantic. Lỗi validation domain được trả trong response `valid=false` của validate-only; lỗi scope/resource/conflict/persistence dùng error envelope chung.

#### SPEC-P13.1 — Request và chuẩn hóa số học

| Trường | Quy tắc bắt buộc |
| :--- | :--- |
| `scenario_revision_id` | UUID thuộc đúng `scenario_id` và organization hiện tại; revision phải là snapshot SAVED được chọn. Scenario ARCHIVED không khởi tạo calculation mới. |
| `idempotency_key` | Chuỗi đã trim, dài 8–200 ký tự; duy nhất trong organization cho calculation P13. Cùng key phải có cùng fingerprint của input raw/scenario revision/curve. |
| D/n/d | Cần ít nhất hai trong ba. D và d không âm; n là số nguyên dương ≤ 1.000.000. Đủ cả ba thì kiểm `abs(D − n×d) ≤ tolerance`; ngoài tolerance trả `FRACTIONATION_INCONSISTENT`. |
| Suy đại lượng thiếu | D+n → d=D/n; n+d → D=n×d; D+d → n=D/d và phải là số nguyên trong tolerance. Trường hợp D=d=0 bắt buộc có n; zero dose hợp lệ khi n>0. Không clamp và không sửa ngầm giá trị đã nhập. |
| `consistency_tolerance_gy` | Số hữu hạn dương, mặc định 0.01 Gy, tối đa 100 Gy; tolerance được lưu trong normalized snapshot. |
| `alpha_beta_gy` | Số hữu hạn dương; source type chỉ `USER_DEFINED` hoặc `REFERENCE`; reference sau trim không được rỗng. Curve alpha/beta cũng phải dương, hữu hạn và không trùng. |
| Curve `FIXED_N` | D min/max không âm, max ≥ min, step > 0; giữ n từ `fixed_n` hoặc n normalized; tạo D từ min đến max, tối đa point limit trên toàn bộ series. |
| Curve `FIXED_D` | fixed d > 0 từ `fixed_d_gy` hoặc d normalized; chỉ tạo điểm D=n×d với n nguyên dương; step phải là bội nguyên dương của fixed d; range không có điểm thì lỗi. |
| Precision | Engine tính bằng giá trị hữu hạn chưa làm tròn; rounding chỉ ở UI/export presentation theo contract. Dataset checksum được tính trên payload canonical trước khi render. |

#### SPEC-P13.2 — Operation, response và persistence

1. `validate` resolve organization → scenario → revision trước khi tính; chạy engine trong memory; trả `valid`, field errors, normalized input và preview point count/checksum; không thêm `BiologicalCalculationRun` hoặc `AuditEvent`.
2. `calculate` resolve scope/revision → chạy cùng engine → tạo raw request snapshot, fingerprint, normalized fractionation và result snapshot → insert calculation + audit trong transaction. Chỉ sau commit mới trả `COMPLETED`.
3. Nếu key đã tồn tại và fingerprint giống, trả nguyên snapshot đã commit (HTTP 200). Nếu fingerprint khác, trả `409 CALCULATION_IDEMPOTENCY_CONFLICT`; không overwrite. Nếu race unique constraint xảy ra, query lại key và chỉ trả record khi fingerprint khớp.
4. `charts` chỉ đọc calculation thuộc organization, dựng preview từ normalized fractionation/alpha-beta/source trong snapshot với curve mới; `persisted=false`, không sửa result snapshot và không thêm history.
5. `export JSON` trả input/result/model/version/checksum; `export CSV` dùng chính `result_snapshot.table_rows`. Nếu snapshot thiếu/không finite, trả persistence error; không tự tính lại từ scenario hiện tại.

#### SPEC-P13.3 — Contract test mapping

| Test | Assertion chính | Error/recovery cần xác nhận |
| :--- | :--- | :--- |
| TC-P13-S01/S02 | 60/30/2 α/β10 → BED72/EQD260; 30/5/6 α/β3 → BED90/EQD254 | Không làm tròn sớm, unit/model version được lưu. |
| TC-P13-S03/S06 | Curve fixed-n, nhiều series, marker/table/chart | `table_rows` và chart points cùng dataset/checksum. |
| TC-P13-S04/S05 | Zero dose và input pair | Zero không bị coi là missing; derived field deterministic. |
| TC-P13-S07/S08 | Save/refresh/export và retry | Snapshot/history bền vững; replay không duplicate. |
| TC-P13-E01–E03 | Invalid n/alpha, D≠n×d, non-finite/overflow | 422 hoặc `valid=false`; không có completed run. |
| TC-P13-E04/E09 | Range/step/point/series lỗi | `CURVE_RANGE_INVALID`; không lưu chart một phần. |
| TC-P13-E05 | Missing source | `ALPHA_BETA_SOURCE_REQUIRED`; giữ form. |
| TC-P13-E07 | Key trùng payload khác | 409 conflict; record cũ không đổi. |
| TC-P13-E08 | Out-of-scope/archived revision | Scope/not-found/immutable; không lộ metadata hoặc tạo run. |
| TC-P13-E10 | Timeout sau commit/DB failure | Query key trước retry; không success giả/duplicate. |

<a id="spec-p14"></a>

### SPEC-P14 — So sánh phác đồ xạ trị

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-12; FR-P14-01 đến FR-P14-04 |
| Input và dữ liệu hiển thị | 2–10 option; mỗi option tham chiếu một P13 `COMPLETED` snapshot bằng `calculation_id`, có `option_id` ổn định và label; result hiển thị D/n/d, tissue, alpha/beta/source/model, baseline, absolute/% delta. |
| Model/storage | `BiologicalComparisonRun` với organization/scenario/revision IDs, idempotency key, model key/version, immutable input/result/warning/error snapshots và audit event. Option values được copy vào snapshot, không phải live pointer. |
| Operation/API surface | `/api/v1/organizations/{organization_id}/biological/comparisons`: validate, create/replay, list, detail, chart preview, clone và JSON/CSV export. UI route: `/app/biological/compare`. |
| Transaction/invariant | Tất cả option phải cùng scenario, scenario revision, tissue context, model key/version; calculation IDs khác nhau; baseline dùng stable option ID; validate/preview không mutation; create/clone commit một snapshot atomic. |
| Delta semantics | Với baseline A và option B: `delta = B − A`, `percent = 100 × delta / A`; A=0 giữ delta tuyệt đối và trả percent `null` + reason `BASELINE_ZERO`. Không phát ra Infinity/NaN hoặc giả zero. |
| Compatibility semantics | Khác alpha/beta được tính và hiển thị riêng nhưng warning `COMPARISON_ALPHA_BETA_MISMATCH`, `ranking_allowed=false`, `ranking=null`; không cộng các phương án thay thế và không auto-rank. |
| Presentation semantics | Table và chart lấy từ cùng result snapshot. Reorder chart trả `persisted=false`, không đổi baseline/history. Clone tạo ID/key mới, cho phép baseline/order mới và giữ source calculation snapshots. |
| Output bàn giao | Multi-option editor/table/chart/compatibility/history/clone/export với trạng thái empty/loading/warning/error/preview rõ ràng. |
| Success oracle | TC-P14-S01 đến TC-P14-S06 trong plan |
| Error/recovery oracle | TC-P14-E01 đến TC-P14-E10 trong plan |
| Exit | Local engine/API/UI/OpenAPI/migration tests pass; staging phải chứng minh validate/no-mutation, persisted replay, zero/warning, reorder, clone/export, PostgreSQL checksum và organization scope. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**P14 request schema:** `name` 1–240 ký tự; `idempotency_key` 8–200 ký tự; `baseline_option_id` theo stable ID; `options` 2–10 phần tử; mỗi option có `option_id` 1–40 ký tự theo `[A-Za-z][A-Za-z0-9_.-]{0,39}`, label 1–240 ký tự và UUID `calculation_id`. Unknown fields, thiếu field, UUID sai hoặc NaN/Infinity bị chặn bởi shared `REQUEST_VALIDATION_FAILED` trước mutation.

**P14 result schema:** `input_snapshot` có `schema_version=biological-plan-comparison-input.v1`, name, baseline, ordered option snapshots và request fingerprint. `result_snapshot` có `schema_version=biological-plan-comparison-result.v1`, engine key/version, baseline, compatibility, warnings, `ranking=null`, table rows và `chart_dataset` với `schema_version=biological-comparison-chart.v1`, categories, point count và SHA-256. `warning_snapshot` chỉ chứa warning objects; `error_snapshot` rỗng khi run `COMPLETED`.

**P14 operation matrix:**

| Method/path | Thành công | Side effect và recovery |
| :--- | :--- | :--- |
| `POST .../comparisons/validate` | `200 valid=true/false`, preview/warnings/errors | Không tạo row/audit mutation; lỗi field giữ form để sửa. |
| `POST .../comparisons` | `201` tạo mới; `200` replay cùng fingerprint | Commit comparison + audit; retry sau mất response query key trước khi gửi lại. |
| `GET .../comparisons`, `GET .../comparisons/{id}` | Collection/detail typed, organization-scoped | Chỉ đọc snapshot; out-of-scope không lộ metadata. |
| `POST .../{id}/charts` | `200 persisted=false`, option order/table/chart mới | Không sửa result; order phải chứa mọi option đúng một lần. |
| `POST .../{id}/clone` | `201` clone; `200` replay clone key | Tạo snapshot mới từ source snapshot; source không đổi. |
| `GET .../{id}/export?export_format=JSON\|CSV` | File đúng schema/row/checksum | Đọc snapshot đã lưu; snapshot hỏng trả persistence error, không export file giả. |

**Failure contract thực thi:** `COMPARISON_OPTIONS_REQUIRED`, `COMPARISON_LIMIT_EXCEEDED`, `COMPARISON_BASELINE_REQUIRED`, `COMPARISON_OPTION_INVALID`, `COMPARISON_CONTEXT_MISMATCH`, `COMPARISON_ALPHA_BETA_MISMATCH` (warning), `COMPARISON_IDEMPOTENCY_CONFLICT`, `COMPARISON_NOT_FOUND`, `COMPARISON_PERSISTENCE_FAILED`, cùng `REQUEST_VALIDATION_FAILED` cho lỗi Pydantic. `BASELINE_ZERO` là reason hợp lệ của percent `null`, không phải failure HTTP. HTTP mapping: request/engine `422`, scope `403`, missing resource `404`, idempotency `409`, persistence `503`.

<a id="spec-p15"></a>

### SPEC-P15 — Re-irradiation, recovery và bù fraction

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-13; FR-P15-01 đến FR-P15-04 |
| Input và dữ liệu hiển thị | Course IDs/date ranges/D/n/d hoặc fraction list; tissue dose metric/unit/alpha-beta; recovery per prior course/evaluation time/source; no-recovery comparator; planned/delivered/remaining fractions; interruption duration; optional time model. |
| Model/storage | Course/fraction/tissue dose inputs, recovery assumptions, model version, evaluation date; immutable scenario calculations. |
| Operation/API surface | Implemented `/biological/re-irradiation` and `/biological/fraction-compensation` validate/create/list/detail/export contracts; same scenario-version and scope rules. |
| Transaction/invariant | Input snapshot gồm delivered schedule và assumptions; calculation không mutate treatment records. |
| Output bàn giao | Re-irradiation + compensation screens, model contract, timeline, sensitivity/compare, golden/error suite. |
| Success oracle | TC-P15-S01 đến TC-P15-S08 trong plan |
| Error/recovery oracle | TC-P15-E01 đến TC-P15-E14 trong plan |
| Exit | No-recovery/recovery, nonuniform fractions, missing time/context, compensation schedule và independent export pass; spatial không giả lập. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Engine/renderer cần recheck snapshot/source và chỉ commit output hợp lệ; UI không tự suy PASS từ HTTP 200.

**Implementation contract P15 (slice `p15-lq-reirradiation-1.0.0` / `p15-lq-compensation-1.0.0`):**

1. **Request boundary.** `ReIrradiationRequest` nhận `scenario_revision_id`, `name`, organization-scoped `idempotency_key`, `courses[2..20]`, `recovery_model`, sensitivity fractions và `spatial.requested`. Mỗi course yêu cầu ID duy nhất, `is_prior`, date tùy model và `tissue_doses[1..40]`. Mỗi tissue dose yêu cầu tissue key duy nhất, metric, `dose_unit=Gy`, alpha/beta dương có source/reference và một trong hai biểu diễn lịch: `fraction_doses_gy[]` hoặc các giá trị đủ để suy ra D/n/d. P15 bắt buộc ít nhất một prior và một current course.
2. **Re-irradiation calculation.** Với mỗi dòng mô, engine tính `BED = Σ d_j × (1 + d_j/(α/β))`; `EQD2 = BED/(1+2/(α/β))`. Lịch không đều dùng từng `d_j`, không thay bằng liều trung bình. `NONE` trả baseline; `USER_DEFINED` chỉ áp dụng recovery `(1-r)` vào BED của prior course đúng một lần. Group key gồm tissue và alpha/beta; context khác nhau không được cộng.
3. **Fraction compensation boundary.** `planned_fraction_doses_gy[]` là nguồn lịch gốc; delivered là prefix phải khớp từng phần tử trong tolerance. Mỗi alternative chỉ chứa `remaining_fraction_doses_gy[]`; engine ghép `delivered + remaining`, lưu dấu `delivered_prefix_unchanged=true` và delta so với lịch gốc. Interruption không tự biến thành dose; time model `NONE` trả warning `NO_REPOPULATION_CORRECTION`, còn `USER_DEFINED_LINEAR` cần start/evaluation date, kickoff, rate và source.
4. **Persistence boundary.** `POST .../validate` chỉ chạy schema/context/engine và không insert. Create ghi `BiologicalReirradiationRun` gồm organization/scenario/revision, operation, request snapshot/fingerprint, result snapshot, warnings/errors, model key/version, actor và timestamps trong một transaction cùng audit. Replay cùng key + fingerprint trả row cũ; cùng key khác fingerprint trả conflict. JSON/CSV export lấy đúng snapshot đã lưu.
5. **Capability boundary.** Scalar cumulative và schedule comparison là capability hiện hành. `spatial.requested=true` không được trả voxel result; kết quả vẫn có `spatial_result=null`, capability `UNAVAILABLE` và warning `SPATIAL_ACCUMULATION_UNAVAILABLE`. P15 không sửa treatment record, QA case, patient record, prescription, TPS hoặc PACS.

**API routes:**

| Method | Route | Semantics |
| :--- | :--- | :--- |
| POST | `/organizations/{org}/biological/scenarios/{scenario}/re-irradiation/validate` | Validate-only, trả `valid`, field errors, warnings, normalized snapshot và preview; không ghi DB. |
| POST | `/organizations/{org}/biological/scenarios/{scenario}/re-irradiation` | Tính và lưu immutable scalar run; `201` lần đầu, `200` khi idempotent replay. |
| GET | `/organizations/{org}/biological/re-irradiation` và `/{run_id}` | List/detail theo organization và operation; không đọc xuyên scope. |
| GET | `/organizations/{org}/biological/re-irradiation/{run_id}/export?export_format=JSON|CSV` | Export snapshot, không tính lại và không mutation. |
| POST | `/organizations/{org}/biological/scenarios/{scenario}/fraction-compensation/validate` | Validate-only lịch gốc/prefix/alternatives/interruption/time model. |
| POST | `/organizations/{org}/biological/scenarios/{scenario}/fraction-compensation` | Tính và lưu alternatives; idempotency giống re-irradiation. |
| GET | `/organizations/{org}/biological/fraction-compensation` và `/{run_id}` | List/detail compensation snapshots theo organization. |
| GET | `/organizations/{org}/biological/fraction-compensation/{run_id}/export?export_format=JSON|CSV` | Export result snapshot. |

**Failure contract thực thi:**

| Boundary | Codes | HTTP/response và phục hồi |
| :--- | :--- | :--- |
| Course/context | `COURSE_REQUIRED`, `COURSE_COUNT_INVALID`, `COURSE_ROLE_REQUIRED`, `COURSE_ID_DUPLICATE`, `COURSE_LIMIT_EXCEEDED`, `COURSE_INTERVAL_INVALID`, `COURSE_INTERVAL_REQUIRED` | Engine error `422`; sửa field/course; không tạo run. |
| Tissue/dose | `TISSUE_DOSE_REQUIRED`, `TISSUE_DOSE_DUPLICATE`, `TISSUE_DOSE_LIMIT_EXCEEDED`, `DOSE_UNIT_INVALID`, `ALPHA_BETA_SOURCE_REQUIRED`, `CALCULATION_NONFINITE` | `422`; không copy target sang OAR, không clamp hoặc đổi unit ngầm. |
| Schedule | `FRACTION_SCHEDULE_REQUIRED`, `FRACTION_SCHEDULE_INVALID`, `FRACTION_SCHEDULE_INCONSISTENT`, `FRACTION_COUNT_NONINTEGER` | `422`; giữ draft, sửa D/n/d hoặc list; remaining không âm/không tự sửa. |
| Recovery/context | `RECOVERY_ASSUMPTION_INVALID`, `CUMULATIVE_CONTEXT_MISMATCH`, `SPATIAL_ACCUMULATION_UNAVAILABLE` | Recovery sai là `422`; context mismatch và spatial unavailable là warning trong valid result, group/capability phải giữ rõ. |
| Compensation | `ALTERNATIVE_SCHEDULE_REQUIRED`, `ALTERNATIVE_ID_DUPLICATE`, `ALTERNATIVE_LIMIT_EXCEEDED`, `ALTERNATIVE_PREFIX_CHANGED`, `INTERRUPTION_INTERVAL_INVALID`, `INTERRUPTION_OVERLAP`, `TIME_MODEL_INVALID`, `TIME_MODEL_SOURCE_REQUIRED` | `422`; chỉnh alternative/interval/time model và validate lại. |
| Scenario/scope | `SCENARIO_SAVED_REQUIRED`, `SCENARIO_REVISION_NOT_FOUND`, `SCENARIO_REVISION_NOT_SAVED`, `P15_RUN_NOT_FOUND` | `409` cho lifecycle, `403/404` cho scope/resource; chọn saved revision thuộc organization hiện tại. |
| Idempotency/persistence | `P15_IDEMPOTENCY_CONFLICT`, `REIRRADIATION_PERSISTENCE_FAILED` | `409` khi key khác payload; `503` khi persistence uncertain; query key/ID trước retry, không nhân bản. |

Validate-only dùng HTTP `200` để trả `valid=false` cho lỗi engine đã phân loại; lỗi request Pydantic `422`; scope `403`; resource thiếu `404`; lifecycle/idempotency conflict `409`; persistence `503`. `CUMULATIVE_CONTEXT_MISMATCH`, `SPATIAL_ACCUMULATION_UNAVAILABLE` và `NO_REPOPULATION_CORRECTION` là warning/capability state, không được biến thành `PASS` ngầm.

<a id="spec-p16"></a>

### SPEC-P16 — Dose limits, phác đồ điều trị và Knowledge Library

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-14; FR-P16-01 đến FR-P16-04 |
| Bounded context | Biological Toolkit độc lập; không có FK tới QA case, patient, RTPLAN, prescription, TPS hoặc PACS. |
| Model/storage | `biological_library_entries`: organization-scoped, `entry_type` ∈ `DOSE_LIMIT`, `TREATMENT_PROTOCOL`, `KNOWLEDGE`, `ALPHA_BETA`; family key `(organization_id, entry_type, entry_key)` và version number; content/citation/applicability JSON an toàn; source lineage, actor, revision và `content_sha256`. |
| Input | `entry_key`, type, name, disease/subtype/anatomy/intent/technique/fractions, tissue/OAR, metric/operator/limits/unit/volume/parameter, alpha/beta/model/version, applicability/content, source type/reference/status/date/evidence/citation. |
| API prefix | `/api/v1/organizations/{organization_id}/biological/library`; mọi route resolve identity/membership trước khi đọc entity. |
| API operations | `POST /validate`; `GET /`; `POST /`; `GET /{id}`; `GET /{id}/revisions`; `PATCH /{id}`; `POST /{id}/clone`; `POST /{id}/publish`; `POST /{id}/archive`; `GET /{id}/compare?other_id=`; `POST /{id}/use`; `POST /import/validate`; `POST /import`; `GET /{id}/export?export_format=JSON|CSV`. |
| Lifecycle | Create/clone → `DRAFT`; only DRAFT can be patched; publish → `PUBLISHED`; archive → `ARCHIVED`; published content is immutable in place; change requires clone/new version. Repeated publish/archive is safe and returns current snapshot where contract permits. |
| Transaction/invariant | All writes are organization-scoped and audited. Optimistic `revision` protects patch/publish/archive. Version uniqueness is enforced by DB. A validation preview never mutates; import commits only validated rows selected by request; calculator/use receives a copied source snapshot, not a live pointer only. |
| Output | Structured entry, source/citation/status, applicability, version/revision/hash, row-level import report, compare diff, JSON/CSV export and explicit-use snapshot. |
| Success oracle | TC-P16-S01 đến TC-P16-S04 trong plan |
| Error/recovery oracle | TC-P16-E01 đến TC-P16-E10 trong plan; generic B01–B12 and C03–C16 apply where relevant. |
| Exit | Local tests and static checks pass; staging schema/API/browser/DB/scope/negative evidence pass; no unsourced clinical-limit seed and no auto-apply. |

#### SPEC-P16.1 — Canonical validation and matching

1. **Key/type/text.** `entry_key` is normalized uppercase and must match `^[A-Z][A-Z0-9_.-]{0,119}$`; entry type must be one of the four enumerated types; text is trimmed and bounded. Dates use ISO date/datetime prefix.
2. **Source.** `REFERENCE` requires a non-empty source identifier (citation, DOI, URL or document ID). `UNVERIFIED` and `UNAVAILABLE` are retained as metadata/warnings; RT-CONNECT never fetches a URL or treats a link as independently verified.
3. **Dose metric.** A `DOSE_LIMIT` requires metric, unit and operator. `MAX`, `MIN`, `TARGET` require `limit_value`; `RANGE` requires `lower_limit` and `upper_limit` with lower ≤ upper. DMAX/DMEAN/Dxcc require dose-like units; Dxcc requires positive `volume_cc`; Vx requires positive `metric_parameter` and `%`, `cc` or `cm3`. Unknown metric/unit combinations are errors, not best-effort coercions.
4. **Alpha/beta.** An `ALPHA_BETA` entry requires finite positive alpha/beta, stores unit `Gy`, and can use `limit_value` as an input alias. Missing tissue/OAR produces a non-blocking `DOSE_LIMIT_NOT_APPLICABLE` warning that explicitly prevents automatic application.
5. **Applicability.** Direct context fields are copied into normalized applicability arrays. Search dimensions are exact case-insensitive membership; a missing/unknown dimension is not a wildcard. `fractions` is a positive integer and must agree with `applicability.fractions`.
6. **Content safety.** `content`, `citation` and `applicability` are finite JSON objects. Script/iframe/object/embed/style markup, event attributes, `javascript:` and `data:text/html` are rejected. Formula text is displayed as data and is never evaluated as executable code.

#### SPEC-P16.2 — Import, lifecycle and explicit-use contract

- **Validate-only:** `POST /validate` returns `200` with `valid`, field-level `errors`, non-blocking `warnings`, normalized entry and fingerprint. It creates no row. Request/schema errors remain HTTP `422`.
- **Import preview:** `POST /import/validate` accepts 1–500 rows and returns `row_number`, valid/errors/warnings and counts. Duplicate `(entry_type, entry_key)` within one batch is row-scoped `KNOWLEDGE_IMPORT_INVALID`; valid rows are not hidden by invalid rows.
- **Import commit:** `POST /import` repeats validation server-side, creates DRAFT rows for valid rows, assigns next family version and audit events, then commits. A persistence error rolls back the transaction; the caller queries the result before retrying.
- **Draft edit:** `PATCH /{id}` requires `expected_revision`; only DRAFT is mutable. The normalized content hash and revision are updated atomically. PUBLISHED/ARCHIVED returns `KNOWLEDGE_VERSION_IMMUTABLE`.
- **Clone/publish/archive:** Clone copies the source definition into a new family version with `source_entry_id`; name/key changes are revalidated. Publish validates the complete definition first. Archive keeps row/history/export readable but excludes it from default list and new use snapshots.
- **Explicit-use:** `POST /{id}/use` requires one enumerated target tool. Only override fields `limit_value`, `lower_limit`, `upper_limit`, `unit`, `alpha_beta_gy`, `fractions` and `metric_parameter` are accepted. The response includes `source_snapshot`, `effective_values`, `override_label`, schema version, warnings and a deterministic `snapshot_sha256`. It is a preview/binding payload; P13/P14/P15/P17 must explicitly integrate it in their own future contracts.
- **Compare/export:** Compare is read-only and reports metadata/content diffs plus family identity. JSON/CSV export serializes the selected row exactly; it does not resolve the latest version implicitly.

#### SPEC-P16.3 — Exact error mapping

| Condition | Code | HTTP/handling |
| :--- | :--- | :--- |
| Pydantic request/type/size violation | `REQUEST_VALIDATION_FAILED` | `422`; retain input and show field errors. |
| Missing reference for REFERENCE entry | `KNOWLEDGE_SOURCE_REQUIRED` | `422`; add source or label source as internal/user-defined. |
| Unsupported metric/unit/operator/shape | `DOSE_LIMIT_UNIT_INVALID`, `DOSE_LIMIT_NOT_APPLICABLE` | `422` on mutation, `valid=false` on validate-only. |
| Unsafe/non-finite/invalid JSON content | `KNOWLEDGE_CONTENT_INVALID` | `422`; no mutation or execution. |
| Reference unavailable/unverified | `REFERENCE_LINK_UNAVAILABLE`, `REFERENCE_NOT_VERIFIED` | Non-blocking warning; preserve citation and show status. |
| Import row invalid/duplicate | `KNOWLEDGE_IMPORT_INVALID` | Row-level error; valid rows can be committed explicitly. |
| Revision/lifecycle conflict | `KNOWLEDGE_REVISION_CONFLICT`, `KNOWLEDGE_VERSION_IMMUTABLE`, `KNOWLEDGE_NOT_AVAILABLE` | `409`; reload current row or clone a new version. |
| Wrong organization or missing entry | `ORGANIZATION_SCOPE_MISMATCH`, `KNOWLEDGE_ENTRY_NOT_FOUND` | `403/404`; do not reveal other-organization metadata. |
| Unsupported use override or invalid binding | `KNOWLEDGE_CONTENT_INVALID`; warning `KNOWLEDGE_DRAFT_SELECTED`/`DOSE_LIMIT_NOT_APPLICABLE` | `422` for invalid request; warning remains visible and never becomes PASS. |
| Concurrent version/DB failure | `KNOWLEDGE_VERSION_CONFLICT`, `KNOWLEDGE_PERSISTENCE_FAILED` | `409/503`; query ID/key before retry, reconcile, never report success from an uncertain commit. |

Validation errors are not QA `FAIL`; a valid dose-limit result is not a clinical PASS. The P16 UI must expose loading, empty/no-match, validation error, warning, persisted result, conflict, unavailable and export error states.

<a id="spec-p17"></a>

### SPEC-P17 — Visual Dose, DVH và structure review

| Hạng mục | Đặc tả |
| :--- | :--- |
| Module/requirement | MOD-15; FR-P17-01 đến FR-P17-07 |
| Bounded context | QA case scoped; không sửa raw DICOM, RTPLAN, prescription, TPS hoặc PACS. Biological Toolkit vẫn là namespace độc lập. |
| Input | `RTDOSE` bắt buộc và `RTSTRUCT` bắt buộc cho DVH; `CT` tùy chọn cho frame/anatomy context. Chỉ artifact thuộc cùng organization/case có `data_status=VALID` và latest manifest `VALID`. |
| DICOM authority | Modality, SOP/metadata, Rows/Columns/NumberOfFrames, PixelData, DoseUnits, DoseGridScaling, IOP/IPP, PixelSpacing, GridFrameOffsetVector, FrameOfReferenceUID và byte checksum. Filename/ROIName không phải khóa. |
| Geometry | Patient LPS; IOP first triplet là direction theo columns, second là direction theo rows; `PixelSpacing=(row,column)`; normal = row×column; frame gần z-offset nhất; single-frame cần `slice_thickness_mm` hoặc metadata hợp lệ. |
| ROI | Chọn theo positive unique `ROINumber`; CLOSED_PLANAR/CLOSEDPLANAR_XOR; disjoint/hole dùng parity; contour non-finite, self-intersection/unsupported hoặc ROI không tồn tại là lỗi rõ ràng. |
| Metrics | Physical dose Gy; weighted volume cc; Dmin/Dmean/Dmax, D(x) volume-weighted piecewise-linear inverse cumulative DVH, V(x) cc/% với `dose >= threshold`; preset D2/D50/D95/D98 và V0/V20/V30/V40/V50; input custom được normalize/deduplicate. |
| Coverage | `FULL_ROI` chặn contour ngoài dose grid; `OVERLAP_ONLY` trả result có warning `DVH_PARTIAL_COVERAGE`, selected volume/outside count/frame counts; không gán vùng ngoài grid bằng zero. |
| Operation/API surface | `/api/v1/organizations/{organization_id}/qa-cases/{case_id}/dvh/inputs`; `POST /validate`; `POST /runs`; `GET /runs`; `GET /runs/{run_id}`; `GET /runs/{run_id}/export?export_format=JSON|CSV`; `GET /dvh/ct-preview` for the independent bounded CT preview; Report Builder accepts a saved run as `source_type=DVH`. |
| Model/storage | `dvh_analysis_runs`: organization/case/input artifact IDs, ROI, idempotency key/fingerprint, engine/schema version, input/result/warning/error snapshots, actor/timestamps; migration `20260908_0017_dvh_analysis.py`. Raw DICOM remains immutable. |
| Transaction/invariant | Resolve scope before first resource query; validate/checksum before engine; validate-only creates no row; saved run pins all input/geometry/config/source hashes; unique `(organization_id,idempotency_key)` prevents duplicate; export serializes snapshot. After insert, `dvh_analysis_runs` is append-only: ORM update/delete is rejected and migration `20260909_0019` installs a PostgreSQL `BEFORE UPDATE OR DELETE` trigger; a changed input requires a new idempotency key and a new run. |
| Execution | DVH run hiện là synchronous API execution. CT preview là read-only synchronous operation, có resource limit riêng và không tạo `dvh_analysis_runs`. Explicit P11/P16 adapter có thể resolve một source được chọn, snapshot và evaluate actual/limit/margin; không search hoặc auto-apply. Async worker/large workload vẫn là package riêng. |
| Output | `DvhInputsResponse`, `DvhValidationResponse`, `DvhRunResponse`, dose-native visual preview, CT preview, curve, metrics, coverage, warning, provenance, optional `limit_binding`, optional `limit_evaluation` và JSON/CSV export. Without an explicit compatible source, `actual/limit/margin` is absent/N/A. A selected source warning may make display `status=REVIEW_REQUIRED` while `rule_status` remains PASS/FAIL. |
| Success oracle | TC-P17-S01 đến TC-P17-S18 trong plan |
| Error/recovery oracle | TC-P17-E01 đến TC-P17-E31 trong plan; generic B01–B12 and C03–C16 apply where relevant. |
| Exit | Local engine/API/UI/migration checks pass; staging browser→API→PostgreSQL/object storage, geometry/DVH oracle, scope/checksum/idempotency, negative/fault/volume/export evidence pass. |

#### SPEC-P17.1 — Request schema

`DvhRequest` (JSON, `extra=forbid`, no Infinity/NaN):

~~~json
{
  "dose_artifact_id": "uuid",
  "structure_artifact_id": "uuid",
  "ct_artifact_id": "uuid|null",
  "roi_number": 1,
  "coverage_policy": "FULL_ROI",
  "slice_thickness_mm": null,
  "dx_percentages": [2, 50, 95, 98],
  "vx_doses_gy": [0, 20, 30, 40, 50],
  "preview_limit": 4096,
  "limit_entry_id": "uuid|null",
  "protocol_version_id": "uuid|null",
  "protocol_metric_key": "D95|null",
  "limit_override": {}
}
~~~

Rules: dose and structure IDs are required and different; `roi_number > 0`; policy is `FULL_ROI|OVERLAP_ONLY`; optional thickness is positive; Dx values are finite `[0,100]`; Vx values are finite non-negative Gy; each list has 1–20 values; preview limit is 64–16384. `DvhRunCreateRequest` adds an idempotency key length 8–200. Pydantic/schema errors are HTTP 422 and create no side effect.

Limit binding is optional but explicit: send neither source for a pure DVH, or exactly one of `limit_entry_id` and `protocol_version_id`. `protocol_metric_key` requires `protocol_version_id`; `limit_override` requires `limit_entry_id` and accepts only `limit_value`, `lower_limit`, `upper_limit`, `unit`, `alpha_beta_gy`, `fractions` and `metric_parameter`. A P16 source must be a non-archived `DOSE_LIMIT`; a P11 source must be `ACTIVE` and its selected rule must be explicit. The initial source and rule lookups are organization-scoped. There is no fallback to another entry/rule.

The selected metric must be computable by the request: `DMIN`, `DMEAN` and `DMAX` use the corresponding scalar; `Dxx` (for example `D95`) must be present in `dx_percentages`; `Vx` must be present in `vx_doses_gy` and agree with `metric_parameter`. `Dxcc` is not enabled in this P17 slice. Actual and limit units must match. Invalid source, metric, operator, range, override or unit is a validation failure, not a null/zero comparison.

#### SPEC-P17.2 — Normal response and snapshot

`POST /validate` returns HTTP 200 even when the engine rejects a validly shaped request:

~~~json
{
  "valid": true,
  "errors": [],
  "warnings": [{"code": "DVH_DOSE_ONLY_MODE", "field": "ct_artifact_id", "message": "..."}],
  "normalized_input": {"schema_version": "visual-dose-dvh.input.v1", "roi_number": 1},
  "preview": {"schema_version": "visual-dose-dvh.result.v1", "metrics": {}, "coverage": {}, "result_sha256": "..."}
}
~~~

When `valid=false`, `errors` contains `{code, field, message}` and `preview`/normalized output may be null; no `dvh_analysis_runs` row is inserted. `POST /runs` returns HTTP 201 for a new completed run and HTTP 200 for an exact idempotent replay. `DvhRunResponse` must expose IDs, status, engine key/version, complete `input_snapshot`, `result_snapshot`, warning/error snapshots and timestamps. The input snapshot contains artifact filename/type/modality/size/hash, manifest ID/checksum, selected metadata/geometry/unit/validation summary, normalized request, optional `limit_binding` and request fingerprint. The result snapshot contains dose, ROI, geometry, coverage, metrics, curve, visual preview, CT summary, warnings and `result_sha256`.

When a binding is present, `result_snapshot.limit_evaluation` contains `source_type`, `source_id`, `metric_key`, `actual`, `actual_unit`, `operator`, `limit`, `limit_unit`, `margin`, `margin_unit`, `margin_definition`, `rule_status`, `status`, `explicit_selection=true`, `auto_applied=false` and source warnings. The pure engine hash is preserved as `engine_result_sha256`; the final `result_sha256` covers the evaluated result. The binding snapshot contains schema version, source identity/version/status/hash, effective values, user override (if any), warning list and `binding_sha256`. A saved DVH run used by Report Builder is copied into the report source snapshot; report rendering does not rerun DVH.

**P17 snapshot immutability guard:** `DVHAnalysisRun` has no edit or delete operation. The ORM mapper rejects accidental object mutation with `DVH_RUN_IMMUTABLE`; the PostgreSQL schema guard rejects direct SQL `UPDATE` and `DELETE` with the same code/message, including changes to `updated_at`. SQLite local fixtures install equivalent update/delete triggers when the migration is exercised. This is a data-integrity invariant and is independent of the equal-member organization model. Recovery is to query/reconcile the existing run and create a new run from a new input/config snapshot; no repair path may overwrite or remove the historical row. The staging evidence must include the migration revision, trigger existence and a negative mutation probe performed in a disposable or explicitly authorized fixture, never by mutating the retained clinical-like run.

#### SPEC-P17.3 — Metric and geometry semantics

1. Read RTDOSE with pydicom; reject non-RTDOSE, missing/invalid dimensions, unsupported transfer syntax/pixel data, missing geometry, non-positive spacing, invalid frame offsets, non-GY units, missing/invalid scaling, negative/non-finite/oversized values.
2. Convert stored integer pixels to Gy using `pixel_array * DoseGridScaling`; never treat raw integer as Gy and never silently convert `CGY`, `RELATIVE` or unknown units.
3. Project RTSTRUCT patient LPS points to `(frame,row,column)` using the dose affine. Rasterize each contour on its nearest dose plane; use even-odd parity for closed polygons and XOR where declared; report outside contours instead of clipping invisibly.
4. Build selected voxel volume from row spacing × column spacing × frame slice thickness / 1000. `Dmean` is volume-weighted. For `D(x)`, group equal observed dose values, sort dose levels descending, accumulate voxel volume, and linearly interpolate dose between the two bracketing cumulative-volume points for target volume `x%`; clamp `D0` to Dmax and `D100` to Dmin and never extrapolate beyond the observed dose range. `V(x)=sum(volume where dose>=x)` and percent is relative to selected ROI volume.
5. Result SHA is computed over canonical sorted JSON before adding the hash field. JSON/CSV export must return the persisted snapshot and the same result hash; it must not rerun the engine.

#### SPEC-P17.4 — Exact status/error/recovery mapping

| Condition | HTTP/status | Code | Recovery/invariant |
| :--- | :--- | :--- | :--- |
| Missing/malformed request | 422 | `REQUEST_VALIDATION_FAILED` | Field-level correction; no row/job. |
| Missing/invalid manifest | 422 | `DVH_INPUT_MANIFEST_REQUIRED`, `DVH_INPUT_NOT_VALIDATED`, `DVH_INPUT_MANIFEST_INVALID` | Run P6 validation and reconcile checksum. |
| Wrong type/modality or same input | 422 | `DVH_DOSE_ARTIFACT_INVALID`, `DVH_STRUCTURE_ARTIFACT_INVALID`, `DVH_ANATOMY_ARTIFACT_INVALID`, `DVH_INPUTS_MUST_DIFFER` | Select correct artifact; no engine call. |
| Wrong organization/case/archive | 403/404/409 | `ORGANIZATION_SCOPE_MISMATCH`, `DVH_INPUT_SCOPE_MISMATCH`, `QA_CASE_NOT_FOUND`, `QA_CASE_ARCHIVED` | Boundary-safe response; no metadata leak or implicit restore. |
| Object read/checksum drift | 503/409 | `DVH_STORAGE_UNAVAILABLE`, `DVH_SOURCE_CHANGED` | Reconcile object and stored hash; retry only after resolution. |
| DICOM geometry/capability failure | 422 | `DICOM_GEOMETRY_INVALID`, `DICOM_CAPABILITY_UNSUPPORTED` | Use valid export or add explicit capability; never guess transform. |
| Dose units/values/scaling | 422 | `DVH_DOSE_UNITS_UNSUPPORTED`, `DVH_DOSE_VALUES_INVALID` | Correct exporter/scale; never convert implicitly. |
| ROI/contour/empty mask | 422 | `DVH_ROI_INVALID`, `DVH_STRUCTURE_ARTIFACT_INVALID`, `CONTOUR_GEOMETRY_INVALID`, `DVH_EMPTY_STRUCTURE` | Correct RTSTRUCT/ROI; null reason is not zero dose. |
| Coverage | 422 or 200 warning | `DVH_INCOMPLETE_COVERAGE`, `DVH_PARTIAL_COVERAGE` | FULL blocks; OVERLAP_ONLY records warning and denominator. |
| Metrics/resource | 422 | `DVH_COVERAGE_POLICY_INVALID`, `DVH_METRIC_INVALID`, `DVH_RESOURCE_LIMIT` | Correct range/reduce workload; no OOM or side effect. |
| Idempotency | 409 or 200 replay | `DVH_IDEMPOTENCY_CONFLICT` | Same fingerprint replay; different fingerprint uses new key. |
| Persistence/export/run lookup | 503/404/422 | `DVH_PERSISTENCE_FAILED`, `DVH_RUN_NOT_FOUND`, `EXPORT_FORMAT_UNSUPPORTED` | Query/reconcile before retry; snapshot remains immutable. |
| Direct or ORM mutation of a saved run | 409/DB exception | `DVH_RUN_IMMUTABLE` | Reject `UPDATE`/`DELETE`, including timestamp-only changes; verify the saved row and hashes are unchanged, then create a new run for changed inputs. |
| Binding source conflict/no source for override | 200 `valid=false` on validate; 422 on run | `DVH_LIMIT_BINDING_CONFLICT`, `DVH_LIMIT_OVERRIDE_INVALID` | Select exactly one source; remove unsupported override; no engine/row on invalid binding. |
| P16 source unavailable/wrong type/archive/scope | 200 `valid=false` on validate; 422 on run | `DVH_LIMIT_ENTRY_NOT_FOUND`, `DVH_LIMIT_NOT_AVAILABLE`, `DVH_LIMIT_ENTRY_INVALID` | Select a non-archived `DOSE_LIMIT` in the current organization; never fallback to another entry. |
| P11 source/rule unavailable or unsupported | 200 `valid=false` on validate; 422 on run | `DVH_PROTOCOL_NOT_FOUND`, `DVH_PROTOCOL_NOT_AVAILABLE`, `DVH_PROTOCOL_RULE_REQUIRED`, `DVH_PROTOCOL_RULE_NOT_FOUND`, `DVH_PROTOCOL_RULE_UNSUPPORTED`, `DVH_PROTOCOL_RULE_INVALID` | Select an `ACTIVE` protocol and explicit compatible rule, or create a new version. |
| Limit metric not computed/unsupported or unit mismatch | 200 `valid=false` on validate; 422 on run | `DVH_LIMIT_METRIC_NOT_COMPUTED`, `DVH_LIMIT_METRIC_UNSUPPORTED`, `DVH_LIMIT_UNIT_MISMATCH` | Request the Dx/Vx value explicitly, choose a supported metric or correct the versioned source unit. |
| Limit numeric/operator/range invalid | 200 `valid=false` on validate; 422 on run | `DVH_LIMIT_DEFINITION_INVALID`, `DVH_LIMIT_ENTRY_INVALID` | Correct the definition; do not coerce null, NaN, range inversion or unsupported operator. |
| DVH source unavailable to Report Builder | 404 | `REPORT_SOURCE_UNAVAILABLE`, `DVH_RUN_NOT_FOUND` | Keep report draft; choose a DVH run in the current organization/case and do not reveal another source. |

`DVH_DOSE_ONLY_MODE` is a warning when CT is omitted; it is not an error. A valid result with `DVH_PARTIAL_COVERAGE` is not a full-ROI clinical conclusion. No P17 response may label a valid numeric result as QA PASS without a separate protocol rule evaluation.

#### SPEC-P17.5 — CT preview/overlay request và response

CT preview là operation riêng cho FR-P17-07. Nó phục vụ xem trực quan có giới hạn, không phải registration chẩn đoán, không thay thế CT viewer/PACS và không làm thay đổi DVH run.

**Route:**

```text
GET /api/v1/organizations/{organization_id}/qa-cases/{case_id}/dvh/ct-preview
  ?dose_artifact_id=<uuid>
  &ct_artifact_id=<uuid>
  [&structure_artifact_id=<uuid>&roi_number=<positive-int>]
  [&frame_index=<int>]
  [&dose_frame_index=<int>]
  [&preview_limit=<256..262144>]
```

Rules bắt buộc:

1. Identity/membership, organization và QA case được resolve trước mọi artifact query. Dose và CT phải thuộc cùng case/organization, là DICOM `VALID`, có manifest `VALID` và byte checksum khớp. Structure/ROI là cặp tùy chọn; gửi một mà thiếu một là lỗi `DVH_ROI_INVALID`.
2. `frame_index` mặc định `0`, phải nằm trong `[0, frame_count)`. `dose_frame_index` mặc định là frame giữa của dose grid, phải nằm trong `[0, dose_frame_count)`. `preview_limit` mặc định `65_536`, bị giới hạn bởi `DVH_MAX_CT_PREVIEW_PIXELS` và không vượt `[256,262144]`.
3. Phiên bản hiện tại chỉ hỗ trợ một file CT single-frame hoặc multi-frame có `Modality=CT`, `FrameOfReferenceUID`, `Rows`, `Columns`, `ImagePositionPatient`, `ImageOrientationPatient`, `PixelSpacing`, frame offsets hợp lệ, `SamplesPerPixel=1` và `PhotometricInterpretation=MONOCHROME1|MONOCHROME2`. CT series nhiều file, Enhanced CT chỉ có geometry trong functional groups, multi-sample và photometric khác phạm vi là capability unsupported.
4. Pixel CT được giải mã và chuẩn hóa HU bằng `HU = stored_pixel × RescaleSlope + RescaleIntercept`. Nếu slope/intercept thiếu hoàn toàn, default `1.0/0.0` chỉ được dùng cho preview và phải thêm warning `CT_RESCALE_DEFAULTED`; giá trị sai kiểu, non-finite hoặc slope bằng zero là lỗi. Window/level dùng `WindowCenter/WindowWidth`; nếu cả hai thiếu, dùng percentile 1–99 cho display và warning `CT_WINDOW_DEFAULTED`. Width không dương là lỗi.
5. CT và dose phải có cùng `FrameOfReferenceUID`. Mỗi pixel trên lát CT được đưa về patient LPS, sau đó nearest-neighbor map vào dose `(frame,row,column)`. Response phải ghi rõ `overlay_algorithm=NEAREST_NEIGHBOR_IN_PATIENT_LPS`, `valid_pixel_count`, `outside_pixel_count` và mapping matrix; matrix là phép map từ chỉ số row/column của dose reference plane sang chỉ số liên tục frame/row/column của CT, không phải deformable registration.
6. ROI overlay nếu được yêu cầu lấy mask đã rasterize theo cùng dose geometry và map lên lưới CT. Không có structure vẫn cho xem grayscale + dose overlay. Khi không có pixel dose giao với lát CT, CT vẫn có thể render nhưng `overlay_available=false`, dose array dùng `null` cho pixel ngoài dose và warning `CT_DOSE_NO_OVERLAP`.
7. Response không ghi DB, không tạo operation/job/report, không được dùng làm input authority cho DVH. `result_sha256` được tính trên canonical JSON trước khi thêm chính nó; đổi frame/window/limit phải tạo response/hash mới nhưng không sửa run cũ.

Response tối thiểu:

```json
{
  "schema_version": "visual-dose-ct-preview.v1",
  "engine_key": "visual-dose.ct-preview",
  "engine_version": "p17-ct-preview-1.0.0",
  "ct": {
    "frame_index": 0,
    "frame_count": 3,
    "value_unit": "HU",
    "display_range_hu": [-1000, 300],
    "source_grid": {"rows": 512, "columns": 512},
    "output_grid": {"rows": 256, "columns": 256, "stride": 2},
    "display_pixels": [0, 128, 255]
  },
  "registration": {
    "mode": "SHARED_FRAME_OF_REFERENCE",
    "status": "LINKED",
    "patient_coordinate_system": "LPS",
    "overlay_algorithm": "NEAREST_NEIGHBOR_IN_PATIENT_LPS",
    "overlay_available": true,
    "dose_frame_index": 0,
    "plane_mapping_matrix_dose_row_col_to_ct_frame_row_column": [[0, 0, 0], [0, 0, 0], [0, 0, 1]],
    "crosshair": {"source": "DOSE_GRID_CENTER", "patient_lps_mm": [0, 0, 0], "ct_index": [0, 0, 0], "nearest_pixel": [0, 0, 0], "visible": true}
  },
  "overlay": {"rows": 256, "columns": 256, "stride": 2, "dose_gy": [null], "roi_mask": null, "valid_pixel_count": 1, "outside_pixel_count": 0},
  "roi": null,
  "warnings": [],
  "result_sha256": "sha256"
}
```

Success/error semantics của CT preview:

| Tình huống | Kết quả | Invariant/phục hồi |
| :--- | :--- | :--- |
| CT hợp lệ, cùng Frame of Reference | `200`, response parse được, overlay/crosshair/hash đầy đủ | Không có DB mutation; chỉ dùng cho visual review, không gọi là registration chẩn đoán. |
| Đổi frame hợp lệ | `200`, frame/offset/pixels/mapping/hash đổi đúng | Request mới read-only; không sửa DVH/report. |
| Thiếu window hoặc single-slice spacing | `200` + warning `CT_WINDOW_DEFAULTED`/`CT_SLICE_SPACING_DEFAULTED` | Default chỉ dành cho display/navigation và phải hiển thị cho user. |
| Không giao dose | `200` + warning `CT_DOSE_NO_OVERLAP` | CT có thể xem; dose overlay rỗng, không gán zero và không tuyên bố linked overlay. |
| Artifacts/checksum/scope không hợp lệ | `403/404/409/422/503` tùy boundary | Không gọi engine; giữ dose-native fallback nếu workflow còn hợp lệ; sửa/reconcile/retry. |
| Geometry/frame/pixel/resource không hợp lệ | `422` với mã ổn định | Không render ảnh một phần; không đoán transform; giảm workload/chọn dataset/capability phù hợp. |

Mã CT preview phải được map như sau: `DVH_INPUT_SCOPE_MISMATCH`, `DVH_INPUT_NOT_VALIDATED`, `DVH_SOURCE_CHANGED`, `DVH_STORAGE_UNAVAILABLE`, `DVH_ANATOMY_ARTIFACT_INVALID`, `DICOM_GEOMETRY_INVALID`, `DICOM_FRAME_MISMATCH`, `DICOM_CAPABILITY_UNSUPPORTED`, `DVH_ROI_INVALID`, `DVH_RESOURCE_LIMIT`, `DVH_METRIC_INVALID`; warning codes là `CT_RESCALE_DEFAULTED`, `CT_WINDOW_DEFAULTED`, `CT_SLICE_SPACING_DEFAULTED`, `CT_DOSE_NO_OVERLAP`. Không dùng `DVH_ANATOMY_FRAME_MISMATCH` như một mã thứ hai cho cùng lỗi; API hiện tại dùng `DICOM_FRAME_MISMATCH`.

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
| Operation/API surface | `GET /api/v1/health` (liveness, không đọc DB); `GET /api/v1/ready` (database + `schema_revision`); `GET /api/v1/version` (release/environment/engine/renderer/schema); `GET /api/v1/gamma/queue-metrics` có Bearer và organization scope cho queue/job metrics; alert/backup tích hợp hạ tầng theo cấu hình được triển khai. Dashboard web phải hiển thị rõ từng contract, không gộp `health=ok` thành `ready`. |
| Transaction/invariant | Maintenance không rewrite history; backup cleanup chỉ sau retention và có bản phục hồi đã kiểm. |
| Output bàn giao | Monitoring+backup cấu hình, alert/restore evidence, guides, ownership và maintenance backlog. |
| Success oracle | TC-P20-S01 đến TC-P20-S04 trong plan |
| Error/recovery oracle | TC-P20-E01 đến TC-P20-E05 trong plan |
| Exit | Gói vận hành ban đầu có config thực, alert test, backup+restore evidence và người phụ trách; vận hành liên tục không có trạng thái hoàn tất vĩnh viễn. |

**Validation thực thi:** backend là authority cho schema/scope/consistency; frontend kiểm sớm để giữ input và hiển thị field errors. Không dùng response thành công của một bước để suy các dependency đã sẵn sàng.

**Failure contract:** BACKUP_POLICY_FAILED; ALERT_DELIVERY_FAILED; CAPACITY_WARNING; ENGINE_RESULT_CHANGED; RECURRING_INCIDENT. Đây là taxonomy target; mapping sang error codes thực tế phải được ghi trong contract test trước khi triển khai.

## 8.1. Hợp đồng thực thi xuyên phase

### 8.1.1. Phân loại kết quả

Mọi operation phải trả về một trong các nhóm kết quả sau, không suy diễn từ HTTP status đơn lẻ:

| Nhóm | Ý nghĩa | Quy tắc lưu và hiển thị |
| :--- | :--- | :--- |
| `REJECTED` | Request không hợp lệ trước khi được chấp nhận | Có error envelope; không tạo accepted job, không tạo artifact/result một phần. |
| `ACCEPTED` | Server đã commit operation/run và có ID | Client có thể mất response nhưng phải query ID/idempotency trước khi retry. |
| `RUNNING`/`RETRYING` | Job đang thực thi hoặc đang phục hồi dependency | Có attempt/progress/next action; không hiển thị PASS/FAIL tính toán sớm. |
| `COMPLETED` | Phép tính/render đã có output bền vững | Tách status kỹ thuật khỏi quality status `PASS`, `WARNING`, `FAIL`, `INVALID`. |
| `FAILED` | Attempt hoặc operation không hoàn tất | Có error snapshot và recovery action; không xóa input, result hoặc export cũ. |
| `CONFLICT` | Revision/idempotency/lifecycle không còn phù hợp | 409, tải bản hiện tại, giữ draft; không silently overwrite. |
| `OUT_OF_SCOPE` | Resource không thuộc organization/context hiện tại | 403/404 theo boundary; không suy ra resource tồn tại hay lộ metadata. |

### 8.1.2. Chuỗi xử lý chuẩn

1. **Resolve context:** xác minh identity, active membership và `organization_id` trước truy vấn resource đầu tiên.
2. **Validate command:** kiểm schema, type, unit, range, cross-field, source relationship và capability.
3. **Build snapshot:** chụp input, source checksum, config, protocol/model/template version và timezone/locale cần thiết.
4. **Commit acceptance:** transaction ghi resource/snapshot/audit và outbox hoặc export job; response thành công phải có ID.
5. **Execute:** synchronous engine chỉ được commit output sau khi kiểm snapshot; async worker dùng lease/attempt/fencing.
6. **Persist terminal state:** output, warning/error, hash, version và lineage commit atomic theo khả năng storage.
7. **Reconcile:** nếu queue/storage/response gặp lỗi, đối chiếu DB/object inventory trước retry; không tạo thao tác mới chỉ vì client timeout.
8. **Present:** UI hiển thị trạng thái loading, empty, warning, error, success, retry và stale/conflict; không tự tính lại business result từ payload đã round display.

### 8.1.3. Error/recovery matrix của toàn hệ thống

| Lớp lỗi | Ví dụ phase | Response chuẩn | Recovery bắt buộc | Bất biến cần kiểm |
| :--- | :--- | :--- | :--- | :--- |
| Request/schema | P0, P1, P6, P13 | 400/422 + field details | Sửa input và gửi lại; không auto-retry invalid request | Không tạo record/job/result |
| Authentication | P2, P3 | 401 + correlation ID | Refresh single-flight hoặc login lại; clear cache cũ | Không bypass signature, không cache sang user khác |
| Membership/scope | P3–P19 | 403 hoặc 404 | Chọn organization/context hợp lệ; không tự join/create thay thế | Query/worker đầu tiên đã có organization scope |
| Unique/revision | P4, P5, P7, P9, P11–P15 | 409 | Reload bản hiện tại, copy draft hoặc tạo revision/version mới | Không overwrite bản trước, không nhân đôi operation |
| Dependency transient | P2, P6, P8, P9, P19 | 502/503/504 | Retry bounded theo loại operation; accepted ID giữ nguyên | Không mất accepted job; error không ghi đè result cũ |
| Persistence uncertain | P4, P6, P8, P9, P13 | 409/503 tùy đã commit | Query idempotency/status/object inventory rồi mới retry | DB/object không có trạng thái “success giả” |
| Numeric/geometry | P8, P13–P17 | 422 hoặc completed warning | Sửa unit/frame/config hoặc dùng capability explicit | Không đoán unit, transform, dose=0 hay pass rate |
| Resource/capacity | P8, P9, P18–P20 | 413/429/503 | Giảm workload theo policy hoặc tăng capacity; giữ input | API không OOM dây chuyền, không retry vô hạn |
| Valid result with warning | P6, P8, P9, P15–P17 | 200/201 với warning snapshot | User xem warning/assumption và quyết định bước tiếp theo | Warning không bị đổi thành error hoặc giấu khỏi lineage |
| Release/config drift | P1, P2, P19, P20 | 503 hoặc release fail | Dừng promote, đối chiếu manifest, rollback last-good | Không gọi health-only là E2E pass |

### 8.1.4. Quy tắc kiểm thử và evidence

Một assertion chỉ được đánh dấu `PASS` khi đồng thời đúng response, DB state, object/queue state, UI state và provenance mà testcase yêu cầu. Ví dụ upload có HTTP 201 nhưng checksum download sai là `FAIL`; Gamma có `COMPLETED` nhưng denominator/censoring sai là `FAIL`; `/ready` trả 200 nhưng schema không đúng `SCHEMA_REVISION` là `FAIL`. Mỗi evidence phải ghi exact SHA, schema revision, engine/renderer version, fixture hash, organization context, request/run/export ID, expected/observed và cleanup. Không dùng screenshot thay query dữ liệu hoặc thay known-answer assertion.

## 8.2. Ma trận hợp đồng kỹ thuật P0–P20

Các phase contract ở mục 8 đã nêu trường chi tiết. Bảng dưới đây là checklist kỹ thuật để triển khai và review; các mã lỗi phải khớp testcase tương ứng trong `plan.md`, còn phần chưa có endpoint phải giữ chữ `TARGET`.

| Phase | Input/command chính | Output thành công | Lỗi bắt buộc và phục hồi | Điều kiện kỹ thuật chặn đóng |
| :--- | :--- | :--- | :--- | :--- |
| P0 | Tài liệu, source, design registry, evidence index | Baseline version, FR→contract→test→evidence map | `DOCUMENT_CONFLICT`, `DESIGN_REFERENCE_STALE`, `EVIDENCE_MISSING`, `ENVIRONMENT_MISMATCH`; quyết định và rebaseline | Không có FR orphan; không có xung đột chưa quyết định |
| P1 | Lockfile, env contract, Compose, migration, CI command | Runtime reproducible, schema head, health/build/test artifact | `DEPENDENCY_MISMATCH`, `PORT_IN_USE`, `MIGRATION_FAILED`, `CONFIGURATION_MISSING`, `BUILD_CONTRACT_FAILED`; sửa layer và rerun | Clean setup và upgrade từ DB rỗng/đang có đều có evidence |
| P2 | Railway service/env, PostgreSQL URL, Auth issuer/JWKS, public port | API/worker deploy, `/health`, `/ready`, schema/version manifest | `BUILD_SOURCE_INVALID`, `DATABASE_DRIVER_MISMATCH`, `SERVICE_NOT_LISTENING`, `SCHEMA_NOT_READY`, `AUTH_VERIFICATION_FAILED`, `DEPLOYMENT_CONFIG_DRIFT`; giữ last-good | `SCHEMA_REVISION`, source SHA, Auth và DB là effective config đã kiểm |
| P3 | Browser URL, Supabase session, return path, organization bootstrap | Authenticated shell và dashboard đúng context | `SIGN_IN_FAILED`, `RECOVERY_LINK_INVALID`, `SESSION_UNAVAILABLE`, `ORGANIZATION_MEMBERSHIP_REQUIRED`, `AUTH_CONFIGURATION_MISSING`, `WORKSPACE_LOAD_FAILED`; refresh/logout/login lại | Deep-link, expiry, empty onboarding và cache clear pass |
| P4 | Organization/site/machine/membership commands | Scoped hierarchy, stable IDs, membership/invitation history | `MACHINE_CODE_CONFLICT`, `PARENT_NOT_AVAILABLE`, `REVISION_CONFLICT`, `INVITATION_INVALID`, `LAST_MEMBERSHIP_CONFLICT`, `MUTATION_RESULT_UNKNOWN`; đối soát idempotency | Cross-org isolation, concurrent edit, archive/restore và ngang quyền pass |
| P5 | Folder/case create, tree move, search/filter/pagination | Atomic tree/case records và stable deep-links | `FOLDER_CYCLE`, `FOLDER_NAME_CONFLICT`, `PARENT_NOT_AVAILABLE`, `CASE_HIERARCHY_INVALID`, `PAGE_OUT_OF_RANGE`, `RESTORE_CONFLICT`; rollback mutation | Nested tree, archived lineage và combined filter pass |
| P6 | Multipart file, declared type/role, manifest, validation command | Artifact metadata + object + checksum + findings | `FILE_REQUIRED_OR_EMPTY`, `UPLOAD_TOO_LARGE`, `UPLOAD_INTERRUPTED`, `ARTIFACT_PERSISTENCE_FAILED`, `ARTIFACT_TYPE_MISMATCH`, `INPUT_METADATA_INVALID`, `DOWNLOAD_LINK_EXPIRED`; reconcile/retry | Byte/hash round-trip, DICOM relationship, duplicate role và invalid profile pass |
| P7 | Protocol version, metric draft, evaluate/rerun | Immutable measurement snapshot/result/trend projection | `MEASUREMENT_REQUIRED`, `MEASUREMENT_INVALID`, `BASELINE_ZERO`, `REVISION_CONFLICT`, `DUPLICATE_OPERATION`, `PROTOCOL_NOT_AVAILABLE`; tạo rerun/version | Known answer/boundary, N/A reason, result immutability và projection unique pass |
| P8 | Gamma profile, artifact roles, config, enqueue/outbox | Gamma result/plots/counts/attempt diagnostics | `RTDOSE_REQUIRED_OR_COMPARISON_REQUIRED`, `GAMMA_INPUT_INCOMPATIBLE`, `GAMMA_CONFIG_UNSUPPORTED`, `GAMMA_NO_EVALUATED_POINTS`, `GAMMA_LOCAL_ZERO_REFERENCE`, `GAMMA_DISPATCH_UNAVAILABLE`, `GAMMA_EXECUTION_INTERRUPTED`, `GAMMA_DICOM_UNSUPPORTED`, `GAMMA_RESOURCE_LIMIT`, `GAMMA_SOURCE_CHANGED`; bounded retry/dead-letter | Numeric oracle, coverage/denominator, DICOM 3D, lease fencing, crash/ack, large workload và schema staging pass |
| P9 | Template/report/revision/block/export command | Immutable report revision, deterministic output, object/hash/signed download | `REPORT_REVISION_CONFLICT`, `REPORT_SOURCE_UNAVAILABLE`, `REPORT_CONTENT_INVALID`, `REPORT_RENDER_FAILED`, `EXPORT_FORMAT_UNSUPPORTED`, `DOWNLOAD_LINK_EXPIRED`, `REPORT_STORAGE_UNAVAILABLE`, `EXPORT_IDEMPOTENCY_CONFLICT`; retry safe | Schema `20260908_0009`, full customization, snapshot immutability, 4-format export, visual and staging evidence |
| P10 | Trend query, compatibility signature, baseline/event | Raw/aggregate trend + source drill-down | `TREND_SERIES_INCOMPATIBLE`, `DATE_RANGE_INVALID`, `TREND_EMPTY`, `TREND_BASELINE_INVALID`, `TREND_DUPLICATE_SOURCE`, `TREND_SOURCE_ARCHIVED`; rebuild projection | Unit/timezone/filter/export equality and large query pass |
| P11 | Protocol/rule/reference editor and version command | Immutable internal version with applicability/source; schema `20260908_0011` | `REQUEST_VALIDATION_FAILED`, `PROTOCOL_APPLICABILITY_INVALID`, `PROTOCOL_RULE_INVALID`, `PROTOCOL_VERSION_CONFLICT`, `REFERENCE_REQUIRED`, `PROTOCOL_VERSION_IMMUTABLE`, `PROTOCOL_NOT_AVAILABLE`, `PROTOCOL_CAPABILITY_MISMATCH`, `PROTOCOL_NOT_FOUND`, `PROTOCOL_PERSISTENCE_FAILED`, `MUTATION_RESULT_UNKNOWN`; clone/version mới | Old run/report snapshot, active-only consumer, scope, deep-copy/version compare and uncertain mutation recovery pass |
| P12 | Biological scenario/tool selection and calculation request | Independent scenario/revision/history | `SCENARIO_NOT_FOUND`, `BIOLOGICAL_CONTEXT_INVALID`, `SCENARIO_REVISION_CONFLICT`, `MODEL_VERSION_UNAVAILABLE`, `MODULE_UNAVAILABLE`; giữ scenario và availability | No-QA-case namespace, scoped history, clone/export pass |
| P13 | SAVED revision + fractionation D/n/d + alpha/beta + curve range | BED/EQD2 values, normalized input, immutable calculation/chart dataset, table/export | `BIOLOGICAL_INPUT_INVALID`, `FRACTIONATION_INCONSISTENT`, `CALCULATION_NONFINITE`, `CURVE_RANGE_INVALID`, `ALPHA_BETA_SOURCE_REQUIRED`, `CALCULATION_IDEMPOTENCY_CONFLICT`, `CALCULATION_PERSISTENCE_FAILED`, `SCENARIO_REVISION_NOT_FOUND`, `SCENARIO_IMMUTABLE`; validate/replay/query before retry | Known answer, pair derivation/zero dose, precision, source/override, curve/checksum equality, snapshot/replay/persistence pass |
| P14 | Options 2–10 từ P13 `COMPLETED` snapshots, baseline, context | Absolute/% delta, chart/table/history, clone/export | `COMPARISON_OPTIONS_REQUIRED`, `COMPARISON_LIMIT_EXCEEDED`, `COMPARISON_BASELINE_REQUIRED`, `COMPARISON_OPTION_INVALID`, `COMPARISON_CONTEXT_MISMATCH`, `COMPARISON_IDEMPOTENCY_CONFLICT`, `COMPARISON_PERSISTENCE_FAILED`; `BASELINE_ZERO` là reason hợp lệ, alpha/beta mismatch là warning | Same model/context/revision, baseline mutation, zero handling, no auto-rank và no-truncate pass |
| P15 | Course/fraction/time/recovery/compensation scenario | Scalar cumulative, sensitivity, integer alternatives, assumptions, immutable run/export | `COURSE_REQUIRED`, `COURSE_ROLE_REQUIRED`, `COURSE_ID_DUPLICATE`, `COURSE_INTERVAL_REQUIRED`, `RECOVERY_ASSUMPTION_INVALID`, `CUMULATIVE_CONTEXT_MISMATCH`, `FRACTION_SCHEDULE_REQUIRED`, `FRACTION_SCHEDULE_INVALID`, `FRACTION_SCHEDULE_INCONSISTENT`, `FRACTION_COUNT_NONINTEGER`, `TISSUE_DOSE_REQUIRED`, `TISSUE_DOSE_DUPLICATE`, `ALTERNATIVE_PREFIX_CHANGED`, `INTERRUPTION_OVERLAP`, `SPATIAL_ACCUMULATION_UNAVAILABLE`, `P15_IDEMPOTENCY_CONFLICT`, `REIRRADIATION_PERSISTENCE_FAILED`; tách scalar | No-recovery/recovery, nonuniform fractions, prefix-preserving alternatives, no fake spatial dose, replay, refresh và export pass |
| P16 | Knowledge/dose-limit/protocol entry, citation/import | Searchable versioned library and snapshot binding | `KNOWLEDGE_SOURCE_REQUIRED`, `DOSE_LIMIT_UNIT_INVALID`, `REFERENCE_LINK_UNAVAILABLE`, `KNOWLEDGE_IMPORT_INVALID`, `DOSE_LIMIT_NOT_APPLICABLE`, `KNOWLEDGE_CONTENT_INVALID`; row-level repair | Source/applicability/version/import/override pass |
| P17 | RTDOSE/RTSTRUCT/CT and geometry selection | Dose-native preview/profile/DVH with coverage metadata, bounded CT HU/slice/dose/ROI overlay, immutable run and export | `DVH_INPUT_MANIFEST_REQUIRED`, `DVH_INPUT_NOT_VALIDATED`, `DVH_INPUT_MANIFEST_INVALID`, `DVH_DOSE_ARTIFACT_INVALID`, `DVH_STRUCTURE_ARTIFACT_INVALID`, `DVH_ANATOMY_ARTIFACT_INVALID`, `DVH_INPUTS_MUST_DIFFER`, `DICOM_GEOMETRY_INVALID`, `DICOM_CAPABILITY_UNSUPPORTED`, `DICOM_FRAME_MISMATCH`, `DVH_DOSE_UNITS_UNSUPPORTED`, `DVH_DOSE_VALUES_INVALID`, `DVH_ROI_INVALID`, `CONTOUR_GEOMETRY_INVALID`, `DVH_EMPTY_STRUCTURE`, `DVH_INCOMPLETE_COVERAGE`, `DVH_PARTIAL_COVERAGE`, `DVH_METRIC_INVALID`, `DVH_RESOURCE_LIMIT`, `DVH_SOURCE_CHANGED`, `DVH_IDEMPOTENCY_CONFLICT`, `DVH_STORAGE_UNAVAILABLE`, `DVH_PERSISTENCE_FAILED`, `DVH_RUN_IMMUTABLE`, `QA_CASE_ARCHIVED`; dose-only/CT-default/no-overlap warnings | Geometry/DVH/CT oracle, weighted volume, source/checksum/snapshot/idempotency/export and staging evidence; no guessed transform, zero outside grid, deformable registration or implicit series aggregation |
| P18 | Release candidate, golden/pilot dataset, fault/load scripts | Integrated test report, restore evidence, pilot issue log | `RESULT_REGRESSION`, `RESTORE_INCOMPLETE`, `DUPLICATE_RESULT`, `PERFORMANCE_GATE_FAILED`, `PILOT_CAPABILITY_GAP`, `RELEASE_EVIDENCE_MISMATCH`; giữ candidate và regression | No SEV0/1, exact SHA, backup/restore, workload and pilot matrix pass |
| P19 | Candidate manifest, domain/TLS/CORS/Auth, production DB | Public HTTPS website and remote E2E | `PUBLIC_DOMAIN_NOT_READY`, `PUBLIC_BUILD_CONFIG_MISMATCH`, `RELEASE_SCHEMA_FAILED`, `RELEASE_VERSION_MISMATCH`, `REMOTE_E2E_FAILED`, `RESOURCE_BUDGET_EXCEEDED`; no promote/rollback | All service versions, schema, Auth, private deps, backup and rollback verified |
| P20 | Monitoring/backup/alert/runbook/release configuration | Tested operational package and maintenance loop | `BACKUP_POLICY_FAILED`, `ALERT_DELIVERY_FAILED`, `CAPACITY_WARNING`, `ENGINE_RESULT_CHANGED`, `RECURRING_INCIDENT`; alert/restore/root cause/regression | Real alert, restore drill, owner, threshold, capacity and release evidence |

## 8.3. P9 report implementation field contract

Để không nhầm giữa thiết kế giao diện và dữ liệu thật, P9 phải giữ các quy tắc sau trong code, OpenAPI và test:

- `ReportTemplateVersion`: `organization_id`, `template_key`, `version_number`, `status`, `blocks_snapshot`, `render_options`, actor và timestamps; uniqueness theo organization + template key + version.
- `ReportRevision`: `report_key`, `revision_number`, `source_type`, `source_id`, title, `template_version_id`, `source_snapshot`, render options, content SHA-256, status và `supersedes_revision_id`; uniqueness theo organization + report key + revision number.
- `ReportBlockConfig`: stable block ID, type, label, order, visibility, config và source binding; uniqueness theo revision + stable block ID. Label chỉ là presentation, không phải source identity.
- `ExportJob`: revision, idempotency key, request fingerprint, format, renderer version, status, object key, SHA-256, byte size, media type, error/warning snapshots; cùng key khác fingerprint phải conflict.
- Source lookup `QA_CASE`, `MACHINE_QA`, `GAMMA` phải kiểm organization trước khi đọc; `BIOLOGICAL`/`CUSTOM` không được ép có QACase. Revision response trả snapshot và blocks, không trả live result thay thế snapshot.
- Renderer phải canonicalize JSON UTF-8, escape dữ liệu CSV có nguy cơ trở thành formula, không thực thi script/URL, giới hạn tree và số finite. PDF/PNG là presentation export; JSON/CSV là structured export, không hứa layout giống nhau.
- Signed download chỉ được tạo cho `COMPLETED` export có object/hash/media type; link mới có thể được cấp cho cùng job sau khi kiểm scope. Download fail không làm mất export đã hoàn tất.
- Migration `20260908_0009` và `SCHEMA_REVISION=20260908_0009` phải cùng xuất hiện trong release manifest trước khi gọi API ready. Đây là contract kỹ thuật, không phải tùy chọn config chỉ dành cho local.

## 8.4. Quy tắc nghiệm thu contract cho từng loại operation

Đây là quy tắc thực thi áp dụng cho mọi phase, dùng để review API, UI và worker trước khi ghi `PASS`:

| Loại operation | Trước khi thực hiện | Khi thành công | Khi lỗi | Kiểm tra sau refresh/retry |
| :--- | :--- | :--- | :--- | :--- |
| Read/list/query | Resolve identity + organization; validate filter/range/timezone | Response typed, stable sort, đúng scope, có empty/warning khi cần | 401/403/404/422/503 theo nguyên nhân; không trả partial sai scope | Query lại cùng filter cho cùng snapshot; filter mới không bị response cũ ghi đè |
| Create/edit resource | Kiểm parent/source/archived/revision; canonicalize payload | Commit resource + audit/snapshot atomically; trả ID/revision | Invalid không commit; conflict 409 giữ draft; dependency uncertain cần lookup | Same idempotency key không tạo bản thứ hai; stale revision không overwrite |
| Upload/manifest | Kiểm case/type/role/size; tính server checksum; stream object | Object + Artifact + Manifest + validation reference có thể truy nguyên | File invalid/duplicate/type mismatch/DB-object partial có recovery riêng | Download hash khớp; upload lại không làm mất artifact hoặc tạo role trùng |
| Synchronous calculation | Kiểm capability, unit, range, source và resource | Result snapshot + warnings + engine/model version | Invalid/unsupported/nonfinite không lưu result giả; dependency fail giữ input | Cùng input/config cho cùng result semantics; đổi config tạo revision/run mới |
| Async job | Commit accepted run + immutable snapshot + outbox trước dispatch | `QUEUED → RUNNING → terminal`; attempt/progress/result durable | Retry transient có giới hạn; poison/terminal vào error/dead-letter; old worker bị fencing | Reconnect thấy cùng run; ack redelivery không nhân đôi result |
| Report/export | Pin source revision/template/options/renderer | File có format, hash, size, version, signed download | Render/storage/link fail không sửa source/export cũ | Mở history tải đúng revision; cùng request idempotent |
| Projection/rebuild | Đọc source snapshot cùng organization; uniqueness | Rebuild tạo thiếu/sửa projection được phép, trả counters | Duplicate/source thiếu được ghi diagnostic, không commit partial | Chạy lại idempotent; source of truth không bị rewrite |

Một test chỉ được đánh dấu đạt khi kiểm đủ lớp mà contract yêu cầu: response/error envelope, state database, object/queue nếu có, giao diện và provenance. Nếu chỉ kiểm HTTP status thì chỉ được ghi `API_SMOKE`, không được ghi `E2E_PASS`.

### 8.5. Coverage contract cho từng phase

Mỗi phase kế thừa B01–B12 ở mục 2 và phải có các lớp kiểm tra dưới đây. `D` là domain/engine, `A` là API, `DB` là migration/database, `UI` là browser, `R` là failure/recovery, `V` là volume/performance và `P` là provenance/evidence. Phase chỉ đạt khi các lớp được yêu cầu có assertion tương ứng; mã `TC` là chỉ mục trong `plan.md`.

| Phase | Test success/error tối thiểu | Lớp | Assertion đặc thù |
| :--- | :--- | :--- | :--- |
| P0 | `TC-P00-S01..S03`, `E01..E04` | D, P | FR không orphan, conflict/gap có quyết định và evidence không bị sửa lịch sử. |
| P1 | `TC-P01-S01..S03`, `E01..E05` | D, A, DB, R, P | Clean setup, restart, migration rỗng/upgrade và CI cùng SHA. |
| P2 | `TC-P02-S01..S03`, `E01..E06` | A, DB, R, P | URL driver, PORT, schema readiness, JWT positive/negative và config drift. |
| P3 | `TC-P03-S01..S04`, `E01..E06` | A, UI, R, P | Deep-link, first-use, existing member, expiry, logout-cache và offline. |
| P4 | `TC-P04-S01..S04`, `E01..E06` | D, A, DB, UI, R, P | Stable IDs, equal-member scope, invite/lifecycle, concurrent edit và unknown mutation. |
| P5 | `TC-P05-S01..S04`, `E01..E06` | D, A, DB, UI, R, P | Cây không cycle, move atomic, combined filter/page và restore history. |
| P6 | `TC-P06-S01..S04`, `E01..E07` | D, A, DB, UI, R, P | Byte/hash round-trip, object/DB reconcile, type/role/UID/geometry và signed link. |
| P7 | `TC-P07-S01..S04`, `E01..E06` | D, A, DB, UI, R, P | Known-answer, rule boundary, N/A reason, immutable rerun và projection uniqueness. |
| P8 | `TC-P08-S01..S05`, `E01..E10` | D, A, DB, UI, R, V, P | Gamma oracle, coverage/denominator/censoring, DICOM 2D/3D, lease/fencing/crash/dead-letter. |
| P9 | `TC-P09-S01..S04`, `E01..E06` | D, A, DB, UI, R, V, P | Full block customization, snapshot, 4 format, Unicode/long report, render/storage retry. |
| P10 | `TC-P10-S01..S08`, `E01..E12` | D, A, DB, UI, R, V, P | Compatibility/timezone/aggregate equality, baseline/event, rebuild, source drill-down/export. |
| P11 | `TC-P11-S01..S09`, `E01..E16` | D, A, DB, UI, R, P | Immutable version/source, clone deep-copy, active consumer, stale conflict và scope. |
| P12 | `TC-P12-S01..S09`, `E01..E12` | D, A, DB, UI, R, P | Independent namespace, revision/history/clone/archive, capability và no-QA linkage. |
| P13 | `TC-P13-S01..S08`, `E01..E10` | D, A, DB, UI, R, V, P | LQ known-answer, D/n/d consistency, curve-table identity, replay/checksum/no mutation. |
| P14 | `TC-P14-S01..S06`, `E01..E10` | D, A, DB, UI, R, P | 2–10 options, baseline/zero policy, context warning, reorder preview, clone/export. |
| P15 | `TC-P15-S01..S08`, `E01..E14` | D, A, DB, UI, R, P | Course/tissue/recovery, nonuniform schedule, prefix alternative, spatial unavailable, export. |
| P16 | `TC-P16-S01..S04`, `E01..E06` | D, A, DB, UI, R, P | Source/applicability/version/import, no-match, link/content safety và explicit use. |
| P17 | `TC-P17-S01..S17`, `E01..E30` | D, A, DB, UI, R, V, P | Frame/grid/ROI/coverage, bounded CT HU/LPS overlay/no-overlap oracle, volume-weighted cumulative-DVH oracle, dose-only fallback, visual/table and source lineage. |
| P18 | `TC-P18-S01..S04`, `E01..E06` | D, A, DB, UI, R, V, P | Integrated RC, golden diff, restart/concurrency, load, backup/restore, pilot severity. |
| P19 | `TC-P19-S01..S04`, `E01..E06` | A, DB, UI, R, V, P | Public HTTPS, Auth/CORS, service/schema/config manifest, remote E2E and rollback. |
| P20 | `TC-P20-S01..S04`, `E01..E05` | A, DB, R, V, P | Real alert, backup/restore drill, owner/runbook, capacity and result-change regression. |

Nếu phase có output nhưng chưa có một lớp required, status cao nhất chỉ là `LOCAL_VERIFIED` hoặc `STAGING_VERIFIED` theo evidence thực tế. `DONE-v2` yêu cầu không có testcase MUST `NOT_RUN`, `BLOCKED` hoặc `FAIL`, không có SEV0/SEV1 và manifest phải chỉ ra đúng SHA/schema/config đã chạy.

## 9. API hiện có và API mục tiêu

Đối chiếu source ngày sửa tài liệu; phải regenerate/check OpenAPI khi thực hiện code. Base API prefix /api/v1.

| Surface | Đã thấy trong source | Target còn phải kiểm/hoàn thiện |
| :--- | :--- | :--- |
| Health/Auth | health/ready/version, Bearer verifier, session/bootstrap | Schema readiness riêng, refresh/config/error UI và invitation lifecycle. |
| Organization/archive | organization/site/machine, folder/case handlers | Complete restore, membership invitation, optimistic conflicts/filter/history. |
| Artifact | Upload/list/metadata/validate/download/manifest/history | Type mismatch, interrupted/batch, atomic object/DB reconciliation, checksum round-trip evidence. |
| Machine QA | Protocol seed, run create/measurements/evaluate/rerun/compare | Autosave races, full library and boundary coverage. |
| Gamma | Run enqueue/list/detail/retry/compare; queue metrics | PSQA profile, extra config capabilities, denominator/search, leases/outbox, proper DICOM fixtures. |
| Report/trend/protocol library | Report P9, Trend P10 và Protocol Library P11 đã có API/UI slice local; P11 migration `20260908_0011` | P9/P10/P11 phải revalidate staging theo schema mới; P11 vẫn cần library/version/consumer E2E và source snapshot evidence. |
| Biological/knowledge/DVH | Requirement/architecture | P12–P17; P17 có local source/schema/API/UI/test slice và explicit binding/report code, còn staging/renderer/binding-report evidence là gate. |

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
4. Kiểm tra staging chạy đúng migration `20260908_0011`; RTDOSE+measurement 3D end-to-end với source đúng frame/profile đã PASS trên run `df38e7d5-bb4b-4e2b-b949-2310acb1875c`, còn P8 queue/outbox/stale-worker negative behavior, P9 browser/export revalidation và P11 library/consumer evidence cần kiểm đúng candidate.
5. Bổ sung staging crash/ack/dead-letter và resource/large-input benchmark trước khi đóng P8; oracle độc lập, bounded retry và preflight đã có local test.
6. P9/P10/P11 implementation slice có thể được kiểm local song song, nhưng chỉ gọi phase hoàn tất sau staging schema `20260908_0011`, authenticated report/trend/protocol workflow, export/download/source drill-down, consumer snapshot và visual checks; không triển khai hoặc thay cấu hình cloud chỉ vì tài liệu có checklist.

**Cập nhật thực thi 2026-09-08:** các dòng lịch sử ở trên được giữ để truy nguyên. Checkpoint hiện hành phải dùng migration `20260908_0011`; P9/P10 có implementation slice và evidence staging từng phần, P11 đã verified local nhưng chưa có staging browser/consumer evidence; P8 negative/reliability, P10 complete matrix và visual/release checks vẫn mở.

## 12. Nguồn kỹ thuật đã kiểm tra khi viết

- DICOM RT Dose Module, bản current hiển thị PS3.3 2026c: units, pixel scaling, dose type/summation và references. Link ở §3.4.
- DICOM Grid Frame Offset Vector: hai biểu diễn frame positions. Link ở §3.4.
- PyMedPhys Gamma API: tham số/normalization/cutoff/search, dùng làm ứng viên oracle version-pinned. Link ở §5.3.
- Source repository: core/errors.py, db/session.py, alembic/env.py, api/gamma.py, services/gamma_engine.py, services/artifact_validation.py, worker.py, web env/routes và fixture generator.
- Công thức LQ cơ bản xuất phát từ business-analysis §15.3; recovery profile ở §6.3 là giả định user-defined của sản phẩm, không phải bảng hướng dẫn điều trị.

## 13. Ma trận contract ở cấp operation và tính năng (baseline v1.16, retained in v1.17–v1.19)

Mục này là lớp nối giữa yêu cầu `FR-Pxx-yy` trong `business-analysis.md` và testcase `TC-Pxx-*` trong `plan.md`. Nó quy định mỗi phase phải expose hành vi nào, điều gì được coi là thành công, lỗi nào phải phân biệt và dữ liệu nào phải được giữ. Đây vẫn là contract mục tiêu; nội dung chưa có trong source phải được ghi `TARGET`, không được đọc như bằng chứng đã triển khai.

### 13.1. Operation envelope chuẩn

Mọi command/mutation/calculation/export có side effect phải tuân theo chuỗi sau:

~~~text
identity → active membership → organization scope
        → request/schema validation
        → parent/source/capability validation
        → input/config/model/source snapshot
        → transaction commit + operation/audit/outbox (nếu có)
        → synchronous engine hoặc async worker/renderer
        → terminal output + warning/error + hash/provenance
        → UI history/replay/export/recovery
~~~

Contract tối thiểu cho response mutation:

~~~json
{
  "operation_id": "uuid-or-stable-key",
  "lifecycle_status": "ACCEPTED",
  "technical_status": "QUEUED",
  "quality_status": null,
  "data": {},
  "warnings": [],
  "errors": [],
  "provenance": {
    "organization_id": "uuid",
    "source_revision": "uuid-or-null",
    "input_fingerprint": "sha256-or-null",
    "engine_version": "version-or-null"
  },
  "next_action": "GET operation or open history"
}
~~~

Quy tắc bắt buộc:

1. `operation_id` hoặc resource ID phải có ngay khi server đã commit acceptance. Nếu response mất sau đó, client query theo ID/idempotency key trước khi gửi lại.
2. `data` của output tính toán/report là snapshot đã lưu; không query “latest” khi mở history hoặc export.
3. `warnings` có thể đi cùng `COMPLETED`; `errors` không được dùng để che một kết quả QA `FAIL`. `quality_status=FAIL` là output rule hợp lệ, còn `technical_status=FAILED` là phép tính/render không hoàn tất.
4. `retryable` chỉ do server quyết định sau khi xác định side effect và trạng thái commit. Request invalid, scope, conflict và unsupported capability không auto-retry.
5. Lookup đầu tiên sau khi xác minh membership luôn phải chứa `organization_id`; worker message cũng phải kiểm scope trước khi đọc run/input. Không dùng global resource UUID rồi mới lọc tenant.
6. Nếu operation có source file, phải lưu checksum tại thời điểm sử dụng. Nếu object/manifest/checksum thay đổi, không được commit output của bytes khác.

### 13.2. Contract operation của từng phase

| Phase | Operation/tính năng bắt buộc | Tiền điều kiện và input | Kết quả chạy đúng | Lỗi, trạng thái và phục hồi | Bất biến/persistence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0** | Baseline registry, FR/MOD/route/contract/test/evidence mapping và decision log. | Đọc đủ tài liệu, repository, Stitch/Railway inventory và evidence cũ. | Registry không orphan; requirement mới có revision, dependency và testcase. | `DOCUMENT_CONFLICT`, `DESIGN_REFERENCE_STALE`, `EVIDENCE_MISSING`, `ENVIRONMENT_MISMATCH`; tạo decision/gap, không xóa lịch sử. | Version tài liệu và evidence history không bị ghi đè; secret không vào registry. |
| **P1** | Clean setup, migration/seed, health/ready/version, CI/build/restart. | Lockfile, Docker/Compose, `.env.example`, DB/Redis/object storage local. | DB rỗng/upgrade pass; services start/restart; CI xanh trên đúng SHA. | Dependency/port/config/migration/build contract error; sửa layer tương ứng và chạy lại, không bỏ qua migration. | Seed synthetic idempotent; startup không seed production; migration chỉ forward an toàn. |
| **P2** | Deploy API/web/worker staging, database readiness và Supabase Auth verification. | Đúng Railway project/environment/service, root/source SHA, PORT, DB reference, Auth issuer/audience/JWKS. | Pre-deploy migration, health, ready/schema, version và JWT positive/negative đều pass; `postgresql://` được normalize sang psycopg3 khi cần. | `BUILD_SOURCE_INVALID`, `DATABASE_DRIVER_MISMATCH`, `SERVICE_NOT_LISTENING`, `SCHEMA_NOT_READY`, `AUTH_VERIFICATION_FAILED`, `DEPLOYMENT_CONFIG_DRIFT`; giữ last-good, sửa effective config và kiểm lại. | Staging không dùng production DB; secrets chỉ ở server/secret store; health không thay schema/Auth evidence. |
| **P3** | Sign-in, recovery, callback, bootstrap, first-use onboarding, existing workspace, Home và logout. | Public web config đúng environment; Supabase session; return URL nội bộ. | Session single-flight; member vào đúng org; identity chưa có membership thấy onboarding; dashboard empty/ready đúng dữ liệu. | `SIGN_IN_FAILED`, `RECOVERY_LINK_INVALID`, `SESSION_UNAVAILABLE`, `MEMBERSHIP_REQUIRED`, `AUTH_CONFIGURATION_MISSING`, `WORKSPACE_LOAD_FAILED`; giữ draft an toàn, login lại/retry bounded, không tự tạo org khi outage. | Cache/request gắn identity+organization; logout/identity đổi phải clear cache và hủy request cũ. |
| **P4** | Organization/site/machine CRUD, stable ID, member invitation, archive/restore/history. | Active identity và organization context; parent active; invitation có token/expiry. | Hierarchy scoped; rename không đổi source IDs; invitation accept idempotent; member cùng org dùng nghiệp vụ ngang nhau. | Unique/parent/revision/invitation/last-member/unknown outcome; 409 giữ draft, query trước retry, cấp invite mới, không hard-delete history. | Mutation + audit cùng transaction; stable IDs và old links không đổi; không có action-level role hierarchy. |
| **P5** | Folder tree, QA case, combined search/filter/page/deep-link, move/rename/archive/restore. | Site/machine đúng org; folder parent không archived khi tạo/move. | Nested tree đúng; case giữ machine/cycle/time; filter URL tái hiện; archive không xóa history. | `FOLDER_CYCLE`, `FOLDER_NAME_CONFLICT`, `PARENT_NOT_AVAILABLE`, `CASE_HIERARCHY_INVALID`, `PAGE_OUT_OF_RANGE`, `RESTORE_CONFLICT`; atomic rollback subtree và giữ case/run/report. | Move cập nhật path nguyên tử; case/source ID không đổi; archived resource chỉ bị hạn chế thao tác mới. |
| **P6** | Upload stream/batch, artifact role/type, object commit, manifest, DICOM/measurement validation, signed download. | Case scoped; size/media/type policy; file role; object store available. | Bytes/checksum round-trip; mỗi file có terminal state; manifest ghi UID/geometry/unit/source; duplicate được xử lý rõ. | `FILE_REQUIRED_OR_EMPTY`, `UPLOAD_TOO_LARGE`, `UPLOAD_INTERRUPTED`, `ARTIFACT_TYPE_MISMATCH`, `INPUT_METADATA_INVALID`, `ARTIFACT_PERSISTENCE_FAILED`, `DOWNLOAD_LINK_EXPIRED`; cleanup/reconcile rồi retry đúng operation. | Object và DB được đối soát; không tạo `VALID` giả; raw bytes immutable; signed URL không đổi scope. |
| **P7** | Machine QA run, measurement draft, N/A, rule evaluation, result/rerun/compare/trend projection. | Active protocol version và machine/case; metric schema/unit/baseline. | `COMPLETED` + quality `PASS/WARNING/FAIL/N/A` đúng rule; actual/limit/margin giải thích; rerun có snapshot mới. | `MEASUREMENT_REQUIRED`, `MEASUREMENT_INVALID`, `BASELINE_ZERO`, `REVISION_CONFLICT`, `DUPLICATE_OPERATION`, `PROTOCOL_NOT_AVAILABLE`; giữ draft/run cũ, tạo revision mới, không tạo trend point trùng. | Evaluate snapshot protocol/rule/measurement; result cũ không resolve live protocol. |
| **P8** | Gamma preflight, accepted/outbox, queue/lease/attempt/worker, 2D/3D calculation, map/statistics/profile, retry/compare. | Validated RTDOSE + comparison theo profile; configuration/capability/geometry hợp lệ; Redis/worker. | Operation từ `ACCEPTED` đến terminal; result lưu config/engine/input, denominator/coverage/censoring; reconnect đọc lại cùng run. | Missing input, frame/grid/unit/config/no-candidate/local-zero, dispatch/worker/lease/OOM/source drift; 422 hoặc FAILED/RETRYING bounded, dead-letter khi hết retry, không duplicate/worker cũ overwrite. | Lease fencing và attempt audit; `FULL_ROI`/`OVERLAP_ONLY` giữ denominator; JSON-only không giả PSQA. |
| **P9** | Template/block editor, source snapshot, report revision, preview/render/export/history. | Source thuộc org và operation đã có output; block schema; renderer/font/format capability. | Full customization; revision và bốn export format mở lại deterministic; Biological report giữ namespace độc lập. | Source/revision/content/renderer/storage/download/idempotency error; giữ draft/source/export cũ, retry render/download an toàn, không sửa source. | Revision pins source/config/template; block hidden/deleted không làm mất lineage; export hash thuộc revision. |
| **P10** | Trend query/raw/aggregate, compatibility, baseline, maintenance event, outlier, drill-down/export/rebuild. | Machine/metric/timezone/context; source result compatible. | Stable series; raw/aggregate có count/extrema/source IDs; baseline/event marker và export cùng filter/timezone. | Incompatible/date/timezone/filter/empty/baseline/duplicate/archive/large query/event conflict; trả warning/error phù hợp, aggregate hoặc tách series, không bịa zero. | Projection uniqueness; rebuild idempotent; source history không bị sửa bởi trend. |
| **P11** | Protocol search/detail/create/clone/validate/DRAFT/activate/archive/compare và consumer snapshot. | Organization; protocol/rule schema; reference/source; consumer capability. | Version immutable sau use; clone deep-copy; consumer chọn explicit active version; compare chỉ đọc. | Rule/source/version/applicability/persistence/capability/conflict error; field correction/clone/reload/reconcile; không drop unsupported rule hoặc đổi run cũ. | Protocol/rules và source snapshot cùng version; active selection không sửa historical run. |
| **P12** | Biological hub tools/capability, scenario/revision CRUD, calculation history và independent report/export. | Auth/membership; scenario key/context/source/assumptions; module capability. | Scenario/history lưu riêng; tool unavailable hiện rõ; clone và export giữ lineage; không cần QA case. | `BIOLOGICAL_SCENARIO_INVALID`, `SCENARIO_REVISION_NOT_FOUND`, `SCENARIO_IMMUTABLE`, `MODULE_UNAVAILABLE`, scope/session/persistence/export error; giữ form, query/retry hoặc tạo scenario mới. | Biological namespace không có automatic `qa_case_id`/patient linkage; assumptions/model/version snapshot. |
| **P13** | BED/EQD2 validate/calculate, curve, table/marker, save/replay/export. | Saved scenario revision; finite D/n/d/alpha-beta; source/override; curve bounds. | Known-answer; formula/context/source hiển thị; chart/table/export cùng result dataset/hash; zero là giá trị hợp lệ khi được khai báo. | Fraction/consistency/nonfinite/source/range/point/revision/idempotency/persistence error; `valid=false` hoặc 4xx, không clamp/đổi input/tạo chart một phần. | Lưu input/result/model version; export snapshot, không tính lại từ scenario hiện tại. |
| **P14** | Multi-option comparison, compatibility, baseline, absolute/% delta, chart/table/reorder/clone/export. | 2–10 completed P13 snapshots hoặc input hợp lệ; common context/model; stable option IDs. | Options giữ input; delta đúng; baseline zero trả `null` + reason; reorder chỉ đổi thứ tự. | Option/context/alpha-beta/baseline/idempotency/persistence/overflow error hoặc warning; giữ option hợp lệ, không phát hành ranking khi context không tương thích. | Snapshot copy values; no-QA linkage; same comparison replay same hash. |
| **P15** | Course/recovery/no-recovery, cumulative scalar, sensitivity, interruption, compensation alternatives/export. | Course dates/fractions/dose; tissue/alpha-beta; explicit recovery/time/source assumptions. | Mỗi course và tổng scalar giải thích được; delivered/remaining schedule và alternatives đúng integer; export independent. | Interval/schedule/recovery/context/spatial/persistence error; chặn field, warning assumption, `UNAVAILABLE` spatial, tạo scenario mới; không sửa prescription/RTPLAN. | Scalar result không được gọi là spatial cumulative dose; source/assumption/time model snapshot. |
| **P16** | Dose-limit/treatment-protocol/knowledge search, validate/import, draft/clone/publish/archive/compare, explicit-use binding. | Typed context/metric/operator/unit/volume; citation/source; safe content; import preview. | Entry version/citation/applicability rõ; published immutable; valid rows import; explicit-use snapshot được tool chọn chủ động. | Source/unit/operator/content/link/import/version/scope/persistence error; sửa row/clone/retry sau reconcile; không auto-select conflict/limit hoặc biến thành QA PASS. | Content hash, effective values và source revision lưu cùng snapshot; internal/user-defined label giữ nguyên. |
| **P17** | DVH input discovery, geometry/ROI validation, dose-native/CT overlay, preview/save/history/export, explicit P11/P16 limit evaluation và DVH report binding. | VALID RTDOSE + RTSTRUCT cùng case/org; CT chỉ khi overlay; checksum/manifest hợp lệ; limit source nếu có phải được user chọn rõ. | Dose-native không cần CT; ROI theo ROINumber; full/overlap policy; metrics/coverage/result hash tái hiện; actual/limit/margin và report source snapshot khi binding explicit. | Manifest/source/unit/grid/frame/ROI/contour/coverage/CT/resource/binding/idempotency/report-source error; FULL chặn coverage thiếu, OVERLAP warning; không clip/gán zero/đoán transform/fallback limit. | `dvh_analysis_runs` immutable, schema/engine/input/binding/result hash; ReportRevision sao chép DVH source snapshot và không rerun. |
| **P18** | RC manifest, integrated QA/Biological/P17 journeys, golden, fault/restart/concurrency/load, backup/restore, pilot/regression. | Candidate SHA/config/schema/fixtures locked; staging safe fault target; restore point. | E2E UI→service→storage/queue/worker; restore count/hash/source equality; workload measured; pilot issue becomes regression. | Regression/restore/duplicate/performance/capability/evidence mismatch; chặn RC, giữ artifact, RCA/fix/rerun, không sửa expected. | Test evidence immutable and tied to candidate; no destructive fault test on production. |
| **P19** | Production promotion, migration, DNS/TLS/CORS/Auth, public web/API, remote E2E, monitor/rollback. | Approved RC + backup + compatible schema; private DB/Redis/worker; public web config. | External HTTPS, login/deep-link/upload/job/report/toolkit, service version parity and rollback proof. | Domain/config/schema/version/remote/budget error; no partial promote, keep last-good, rollback or rebuild public config; health alone insufficient. | Expand/contract migration; public bundle never contains secret; backup precedes destructive/config-changing step. |
| **P20** | Monitor/alert, backup/restore runbook, support guide, incident/RCA, maintenance release/regression. | Production observability/config, owner/contact, retention/budget and staging path. | Alert received; restore drill meets recorded target; operator follows guide; old results remain after maintenance. | Backup/alert/capacity/engine-change/recurring incident; keep last-good, correct policy/channel, RCA + regression + runbook update. | Maintenance never rewrites history; backup cleanup only after valid retention/restore evidence. |

### 13.3. Quy tắc nghiệm thu một feature và một operation

Một `FR-Pxx-yy` chỉ đạt `FEATURE_COMPLETE` khi tất cả điều kiện sau cùng đúng trên candidate đang xét:

| Nhóm kiểm | Điều kiện bắt buộc |
| :--- | :--- |
| Happy path | Có testcase `S` chứng minh input tối thiểu và ít nhất một biến thể hợp lệ; output, ID, trạng thái cuối và next action đúng. |
| Boundary/empty | Có zero/optional/empty/min/max/dữ liệu dài phù hợp; không clamp/truncate hoặc tạo dữ liệu giả. |
| Validation | Có field và cross-field invalid; không side effect trước khi request được chấp nhận. |
| Scope/lifecycle | Có not-found, archived, inactive parent và organization khác; response boundary-safe, không lộ metadata. |
| Retry/concurrency | Có double-submit/idempotency, unknown outcome, concurrent revision; không duplicate hoặc silent overwrite. |
| Dependency | Có DB/object/Auth/Redis/worker/renderer failure phù hợp; retry bounded hoặc terminal FAILED, accepted ID và source vẫn tồn tại. |
| Restart/reconnect | Refresh browser và restart thành phần phù hợp vẫn đọc cùng operation/snapshot; không spinner vô hạn. |
| Output/provenance | History/drill-down/export trả đúng source, revision, version, unit, assumption, warning và hash. |
| UX/accessibility | Loading/empty/ready/warning/error/conflict/offline; label/unit/focus/keyboard/mobile/long Vietnamese text; không chỉ dùng màu. |
| Evidence/release | Record có test/FR/contract/SHA/schema/fixture/expected/observed/evidence/recovery; cùng candidate với code đang bàn giao. |

Không được gọi operation là `COMPLETED` nếu chưa có output bền vững hoặc empty output có reason hợp lệ. Không được gọi quality result là `PASS` nếu chỉ có HTTP 200 hoặc technical status `COMPLETED`. Không được gọi phase là `DONE-v2` nếu feature MUST bên trong còn `TARGET`, `NOT_RUN`, `BLOCKED`, `FAIL` hoặc evidence lệch SHA/schema/config.

### 13.4. Quy tắc mapping lỗi và version hóa contract

- Tên lỗi trong plan là taxonomy; khi triển khai phải chọn một mã chính, status HTTP, `retryable`, field/location, side effect và next action. Không trả chuỗi ghép kiểu `A_OR_B`.
- Thay đổi field, unit, calculation formula, DICOM geometry, error code, status transition, snapshot schema, route hoặc public configuration là contract change. Phải tạo version/revision, cập nhật OpenAPI và chạy affected tests.
- Thay đổi chỉ ở display label/layout không được làm đổi semantic field hoặc result hash. Nếu đổi label có thể gây hiểu sai metric, đó là change cần review và regression UI.
- Thay đổi source/config/model/protocol/template tạo output mới; không update ngược snapshot cũ. Rerun phải có operation/run/revision ID mới, trừ exact idempotent replay.
- Khi specification và source không khớp, đánh `DOCUMENT_CONFLICT` hoặc `IMPLEMENTATION_GAP`; không sửa specification theo response hiện tại chỉ để checkbox xanh. Sau quyết định phạm vi mới, đồng bộ BA → specification → technical → plan → progress.

### 13.5. Quy tắc riêng cho các nhóm có rủi ro tính đúng

1. **DICOM/Gamma/DVH:** metadata, pixel scaling, geometry, frame/UID, coverage và denominator là input có ý nghĩa; filename/ROIName/HTTP status không phải authority. Không auto-align hoặc bỏ điểm lỗi để tăng tỷ lệ pass.
2. **BED/EQD2/re-irradiation:** formula/model/alpha-beta/recovery/temporal assumption phải nằm trong snapshot; scalar không tự biến thành cumulative spatial dose; compensation không tự biến thành prescription.
3. **Report/export:** renderer chỉ đọc snapshot; export cũ không bị thay bởi live data; format không hỗ trợ phải báo rõ; byte/hash/determinism và Unicode/bảng dài là một phần acceptance.
4. **Trend:** chỉ aggregate các source có compatibility signature; điểm thiếu không được biến thành zero; drill-down phải quay về source run/case đúng organization.
5. **Public deployment:** web/API/worker/schema/Auth/queue phải được kiểm theo cùng release manifest; PostgreSQL, Redis, worker và object bucket private theo topology; URL public không chứng minh workflow đã pass.

## 14. Hợp đồng thực thi, bàn giao và kiểm soát thay đổi v1.19

Phần này biến các contract theo phase thành cấu trúc có thể dùng khi viết code, test và bàn giao. Nó không thay thế các field/algorithm contract ở mục 2–8; nó quy định cách chứng minh rằng các contract đó đã được thực thi trên một candidate cụ thể.

### 14.1. Hợp đồng operation tối thiểu

Mỗi operation có side effect hoặc tạo output phải có các trường sau trong response, database snapshot hoặc record tương đương. Với operation đồng bộ, `technical_status` có thể chuyển thẳng sang `COMPLETED` hoặc `FAILED`; với operation bất đồng bộ, phải giữ toàn bộ chuỗi trung gian.

| Trường | Required | Quy tắc |
| :--- | :---: | :--- |
| `operation_id` | Có | Ổn định sau khi server chấp nhận; được dùng để query sau timeout. |
| `organization_id` | Có với dữ liệu nghiệp vụ | Được resolve từ active membership; không lấy global resource rồi mới lọc. |
| `request_fingerprint` | Có với mutation/calculation/export | Hash của payload chuẩn hóa, source revision/checksum và config có ý nghĩa. |
| `lifecycle_status` | Có | Trạng thái resource/command; không đại diện cho chất lượng phép tính. |
| `technical_status` | Có với calculation/job/render | `NOT_STARTED`, `QUEUED`, `RUNNING`, `RETRYING`, `COMPLETED`, `FAILED`. |
| `quality_status` | Khi có rule/metric | `PASS`, `WARNING`, `FAIL`, `N/A`, `INVALID` hoặc `null`; `FAIL` không phải server error. |
| `input_snapshot` | Có với calculation/report/export | Input, unit, source ID, checksum, context và version tại thời điểm dùng. |
| `output_snapshot` | Có khi thành công | Kết quả đã lưu; history/export không được resolve dữ liệu `latest`. |
| `warnings` | Có khi có cảnh báo | Mỗi warning có code, field/location, impact và không bị rơi khi refresh/export. |
| `errors` | Có khi từ chối/thất bại | Mỗi error có code, field/location, retryable và next action; không có secret/stack trace. |
| `provenance` | Có với output | Engine/model/protocol/template/renderer version, source revision và hash. |
| `next_action` | Có khi chưa terminal hoặc recovery cần thiết | Hành động cụ thể: sửa field, query, retry, reconcile, restore, clone hoặc tạo revision. |

Không được coi `operation_id` là bằng chứng operation đã hoàn tất; nó chỉ chứng minh server đã có một điểm để truy vấn. Không được coi `technical_status=COMPLETED` là `quality_status=PASS`. Không được tạo `output_snapshot` trước khi kiểm tra source/checksum và commit thành công.

### 14.2. Error/recovery record chuẩn

Mọi testcase lỗi và mọi lỗi quan sát được trong staging/production phải có record có thể đối chiếu với operation. Cấu trúc tối thiểu:

~~~json
{
  "error_id": "EV-Pxx-Eyy-001",
  "operation_id": "uuid-or-null",
  "phase": "Pxx",
  "feature_ids": ["FR-Pxx-yy"],
  "code": "ONE_CANONICAL_ERROR_CODE",
  "http_status": 422,
  "retryable": false,
  "field_or_location": "body.input.field",
  "lifecycle_before": "DRAFT",
  "technical_before": "NOT_STARTED",
  "quality_status": null,
  "side_effect_expected": "no_resource_or_job",
  "side_effect_observed": "verified_no_row_no_object",
  "user_message": "Nêu dữ liệu cần sửa, không lộ chi tiết nội bộ",
  "recovery_action": "Sửa field và validate lại",
  "expected": "Không tạo side effect",
  "observed": "...",
  "fixture_hashes": ["sha256"],
  "source_sha": "git-sha",
  "schema_revision": "alembic-or-null",
  "evidence_paths": ["docs/evidence/..."],
  "outcome": "PASS"
}
~~~

`side_effect_expected` và `side_effect_observed` là bắt buộc vì HTTP 4xx/5xx đúng chưa đủ để chứng minh database, object store, queue hoặc worker không bị ghi một phần. Nếu response mất sau commit, `code` không được tự chuyển thành lỗi tạo mới; record phải thể hiện `OUTCOME_UNKNOWN` và hành động query/reconcile.

Đối với evidence workload P17 không tạo side effect, record phải tách rõ các loại số đo để không biến support measurement thành release gate:

| Trường | Quy tắc bắt buộc |
| :--- | :--- |
| `workload.shape` và `voxel_count` | Ghi shape theo thứ tự frame/row/column và số voxel thực tế; không gọi “large” nếu chưa nêu kích thước. |
| `concurrent_jobs` và `repeats_per_job` | Ghi số job thực sự chạy đồng thời và số lần lặp mỗi job; một lần chạy tuần tự không được ghi là concurrency. |
| `engine_version`, `source_sha`, `image_digest`, `schema_revision` | Pin runtime và source; evidence lệch engine/source phải bị coi là stale. |
| `result_oracle` | Mỗi job phải đối chiếu cùng expected Dmin/Dmean/Dmax/volume/selected count; thời gian nhanh không bù được sai oracle. |
| `peak_traced_bytes` | Chỉ là allocation do Python `tracemalloc` theo dõi, không phải RSS và không phải memory limit của service. |
| `sampled_container_memory` | Phải ghi `sample_count`, max sampled bytes và `is_peak_rss=false` nếu lấy từ `docker stats`; mẫu thưa không được gọi là peak. |
| `cgroup_memory_observation` | Nếu runner/container cho phép đọc cgroup, ghi `cgroup_version`, `memory_limit_bytes`, `memory_current_bytes`, `memory_peak_bytes`, `peak_metric`, `peak_scope` và `is_peak_rss=false`. `memory_peak_bytes` chỉ là peak theo metric/scope của cgroup, không tự trở thành peak RSS; `max`/giá trị sentinel phải ghi là không có limit hữu hạn. |
| `performance_gate` | Giữ `NOT_ASSESSED` cho đến khi có CPU/RAM/concurrency pin, peak RSS, API responsiveness, fault/retry và environment gate theo P8/P17/P18. |
| `patient_data` | Workload local phải ghi `false`; fixture synthetic phải có checksum và không ghi vào DB/object store production. |

P17 local Docker workload evidence `docs/evidence/p17-local-docker-workload-20260909.json` đã đáp ứng các trường trên cho 2 job × 3 lần, bổ sung cgroup v1 observation, nhưng chỉ là `LOCAL_DOCKER_CONCURRENCY_MEASURED`; không cho phép suy ra worker capacity, staging hoặc clinical readiness.

Known-answer oracle của fixture P17 được chạy riêng bằng `scripts/verify-p17-independent-dvh-oracle.py`: script tự kiểm tra contour/ROI, lấy bốn voxel theo fixture contract, tự tính volume, Dmin/Dmean/Dmax, D2/D50/D95/D98 và Vx rồi mới so sánh với engine. Evidence `docs/evidence/p17-independent-dvh-oracle-20260909.json` phải ghi fixture hashes, expected/observed và từng comparison; **13/13 comparisons PASS** là `LOCAL_INDEPENDENT_ORACLE_VERIFIED`. Đây chưa phải oracle độc lập cho mọi DICOM/vendor hoặc commissioning/reference acceptance, nên staging/reference gate vẫn mở.

Các lớp lỗi và hành vi thực thi:

| Lớp | HTTP thường dùng | `retryable` mặc định | Phải chứng minh |
| :--- | :---: | :---: | :--- |
| Request/schema/field | 400/422 | `false` | Không có resource/job/result mới; draft và field hợp lệ còn nguyên. |
| Auth/membership/scope | 401/403/404 | `false` | Không lộ tồn tại record ngoài scope; không tạo organization thay cho outage. |
| Lifecycle/revision/idempotency | 409 | `false` | Không overwrite; same fingerprint replay đúng, khác fingerprint conflict. |
| Source/geometry/unit/capability | 415/422 | `false` | Không đoán unit/transform, không bỏ điểm hoặc tạo output giả. |
| Dependency/timeout | 502/503/504 | Có giới hạn | Accepted ID và snapshot còn truy vấn được; retry/backoff/dead-letter bounded. |
| Persistence uncertain | 409/503 | Chỉ sau reconcile | DB/object/queue inventory được đối chiếu trước khi retry hoặc cleanup. |
| Resource/rate limit | 413/429/422 | Theo policy | Không OOM dây chuyền; Retry-After/deadline/giới hạn được hiển thị. |
| Render/export/download | 409/422/503 | Có điều kiện | Source revision/export cũ không đổi; output mới có format/hash/version. |
| Release/config/schema | 503 hoặc gate fail | Không trong request user | Promote bị dừng hoặc rollback về last-good; manifest ghi diff. |

Một request chỉ được `retryable=true` khi server đã biết side effect an toàn và có operation/idempotency contract. Client không được suy `retryable` từ việc status bắt đầu bằng `5`. Một mã error chỉ đại diện một nguyên nhân chính; các chuỗi dạng `A_OR_B` trong plan là taxonomy/nhóm test, phải được map thành code cụ thể trong implementation.

### 14.3. Hợp đồng đầy đủ của testcase và phase packet

Một testcase `S`, `E`, `C`, `B` hoặc `G` chỉ được xem là đã chạy khi record có đủ:

1. phase, FR, contract section và testcase ID;
2. branch/source SHA, schema revision, environment và service version;
3. organization/context synthetic hoặc redacted; fixture và checksum;
4. precondition, từng bước thực hiện và expected định lượng;
5. observed, response/error, UI state và state assertions ở DB/object/queue/worker nếu áp dụng;
6. recovery/cleanup, outcome và severity nếu assertion fail;
7. đường dẫn evidence không chứa token, password, database URL hoặc PHI không cần thiết;
8. `next_exact_action` nếu outcome không phải PASS hoặc NOT_APPLICABLE.

`NOT_RUN` là trạng thái trung thực cho testcase chưa thực hiện; không được đổi thành `NOT_APPLICABLE` chỉ vì khó dựng dependency. `NOT_APPLICABLE` phải có lý do nghiệp vụ và không được dùng để bỏ qua mutation, calculation, export, scope, persistence hoặc restart đang áp dụng. `BLOCKED` phải có owner/dependency; phần độc lập vẫn có thể chạy nhưng phase chưa đóng.

Phase packet chuẩn dùng các trường sau:

~~~yaml
phase: Pxx
document_versions:
  business_analysis: "0.21"
  specification: "1.15"
  technical_specification: "1.13"
  plan: "4.0"
candidate:
  source_sha: "git-sha"
  schema_revision: "alembic-or-null"
  environment: "local|staging|production"
entry_gate:
  dependencies: ["Pyy-DONE-v2-or-explicit-slice"]
  design_reference: "project/screen/version-or-null"
work_packages:
  - id: Pxx-W01
    requirements: [FR-Pxx-01]
    commit: "git-sha"
    status: "OPEN|PASS|BLOCKED"
test_summary:
  success: {pass: 0, fail: 0, blocked: 0, not_run: 0}
  error: {pass: 0, fail: 0, blocked: 0, not_run: 0}
  common: {pass: 0, fail: 0, blocked: 0, not_run: 0}
evidence_paths: []
open_issues: []
exit_decision: "OPEN|LOCAL_VERIFIED|STAGING_VERIFIED|DONE-v2|BLOCKED"
next_exact_action: "Một hành động cụ thể"
~~~

`test_summary` là số đếm để phát hiện testcase bị bỏ sót, không phải bằng chứng thay thế cho từng record. `DONE-v2` chỉ hợp lệ khi mọi testcase MUST có record PASS, không có SEV0/SEV1 và candidate/schema/config trong evidence trùng với candidate bàn giao.

### 14.4. Quy tắc tương thích và lan truyền thay đổi

Các thay đổi sau đều là contract change, phải tạo revision hoặc migration phù hợp, cập nhật OpenAPI và chạy affected tests:

| Thay đổi | Artefact phải cập nhật | Test tối thiểu phải chạy lại |
| :--- | :--- | :--- |
| Field, unit, null/range, metric semantics | BA, specification, API schema, UI, engine, export | C01/C02, feature S/E, calculation/round-trip nếu liên quan. |
| Error code/status/retry/state transition | Error envelope, client mapping, worker/UI | C04/C06/C08/C12 và mọi E case của operation. |
| Source role, DICOM geometry, transform, coverage | Manifest, validator, Gamma/DVH, fixture/oracle | C03/C09/C13/C14, geometry/denominator/no-overlap tests. |
| Formula/model/alpha-beta/recovery | Calculation contract, model version, source snapshot | Known-answer, curve/table, comparison, re-irradiation replay. |
| Template/renderer/export | Report snapshot, renderer metadata, format adapter | Unicode/long report, hash/replay, visual and download tests. |
| Auth/org/deployment topology | Scope lookup, cache/session, service manifest/runbook | C03/C07/C12/C15/C16, remote E2E and rollback. |
| Resource/timeout/retention policy | API/worker/renderer limits, alerts, runbook | C08/C14, fault/load, backup/restore and alert evidence. |

Thứ tự đồng bộ bắt buộc là **business-analysis → specification → technical-specification → implementation → tests → plan → implementation-progress/evidence**. Nếu code hiện tại khác contract, ghi `IMPLEMENTATION_GAP` hoặc `DOCUMENT_CONFLICT`; không sửa expected cũ, không xóa evidence và không hạ yêu cầu để làm cho build xanh. Thay đổi chỉ ở layout vẫn phải chạy visual/accessibility nếu có thể làm người dùng hiểu sai metric, unit hoặc status.

### 14.5. Quy tắc phát hành dựa trên manifest

Một candidate release phải có manifest bất biến với tối thiểu:

~~~json
{
  "release_id": "R4-candidate-YYYYMMDD-HHMM",
  "source_sha": "git-sha",
  "services": {
    "api": {"deployment_id": "...", "sha": "..."},
    "web": {"deployment_id": "...", "sha": "..."},
    "worker": {"deployment_id": "...", "sha": "..."},
    "renderer": {"version": "..."}
  },
  "schema_revision": "...",
  "engine_versions": {"gamma": "...", "dvh": "...", "biological": "..."},
  "auth_environment": "staging|production",
  "database_environment": "staging|production",
  "fixture_hashes": [],
  "tests": {"local": [], "staging": [], "production": []},
  "backup_before_change": "path-or-provider-id",
  "rollback_target": "last-good-release-id"
}
~~~

Manifest không được lưu secret. `source_sha`, service SHA, schema, engine/renderer version và Auth/database environment phải được đối chiếu trước khi gọi một workflow là staging hoặc production. Mismatch phải hạ trạng thái thành `NEEDS_REVALIDATION` hoặc `RELEASE_BLOCKED`; không sửa manifest sau khi test để che lệch candidate.
