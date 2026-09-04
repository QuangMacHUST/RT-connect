# KẾ HOẠCH TRIỂN KHAI

## Dự án RT-CONNECT

**Tên file:** plan.md  
**Phiên bản:** 0.5  
**Nguồn:** business-analysis.md phiên bản 0.3, technical.md phiên bản 0.5 và UI-UX.md phiên bản 0.3  
**Mục tiêu:** triển khai RT-CONNECT theo phase có thể kiểm tra, bàn giao và mở rộng  
**Mô hình triển khai:** Supabase cho Auth; Railway cho PostgreSQL, backend API/server, worker, renderer và queue/public API networking; frontend là static web riêng hoặc được backend phục vụ; object storage S3-compatible/MinIO được chỉ định  
**Nguyên tắc:** hoàn thành từng vertical slice, test trước, không làm mất dữ liệu và giữ Biological Toolkit độc lập với QA/ca bệnh

---

## 1. Mục tiêu triển khai

Kế hoạch này chia RT-CONNECT thành các phase theo thứ tự phụ thuộc kỹ thuật:

1. Khóa yêu cầu và kiến trúc.
2. Dựng nền tảng chạy được.
3. Thiết kế UX/UI và design system bằng Google Stitch, sau đó handoff cho frontend.
4. Hoàn thiện Organization, Site, Machine, Folder và QA Case.
5. Hoàn thiện artifact storage, DICOM ingestion và validation.
6. Xây dựng analysis engine và Machine QA.
7. Xây dựng PSQA Gamma vertical slice.
8. Xây dựng Report Builder và export.
9. Xây dựng trend và QA Protocol Library.
10. Xây dựng Biological Toolkit độc lập.
11. Kiểm thử tích hợp, hardening, pilot và chuyển giao.
12. Đưa hệ thống lên public web, kết nối Supabase Auth và Railway PostgreSQL với backend Railway, mở truy cập từ xa và vận hành production.

Clinical MVP gồm P0–P7 và P1A, bao gồm cả design handoff. P8 là track Biological Toolkit riêng; P9 là tích hợp/hardening dùng chung. Public web là phase phát hành sau hardening/pilot, không được coi là hoàn tất chỉ vì hệ thống chạy được trên localhost hoặc LAN.

---

## 2. Nguyên tắc thực hiện

- business-analysis.md là nguồn nghiệp vụ.
- technical.md là nguồn kiến trúc và hợp đồng kỹ thuật.
- Không mở rộng sang thay TPS, PACS, OIS hoặc treatment control.
- Không xây dựng phân quyền theo hành động hoặc phân cấp bác sĩ–kỹ sư.
- Report Builder phải giữ toàn quyền tùy chỉnh.
- Biological Toolkit không tự liên kết với QA case hoặc ca bệnh.
- File gốc không bị ghi đè.
- Chạy lại analysis tạo kết quả mới.
- Mọi lỗi phát hiện trong dataset thật phải được chuyển thành regression test.
- Không đánh dấu một phase hoàn thành chỉ vì giao diện đã hiển thị; phải đạt cả test, dữ liệu và workflow end-to-end.
- Google Stitch chỉ dùng để thiết kế, prototype và handoff; code sinh ra phải được review và nối với API thật.
- Không đưa dữ liệu bệnh nhân hoặc DICOM thật vào Stitch.
- Truy cập từ xa qua public web chỉ expose frontend/API cần thiết qua HTTPS; Railway PostgreSQL chỉ được backend truy cập qua private networking/reference variable, còn Redis, object storage, worker và Orthanc không public trực tiếp.
- Public release phải có domain/DNS, TLS, backup/restore, monitoring, rollback và kiểm thử từ mạng bên ngoài.
- Supabase Auth chỉ là identity provider; RT-CONNECT không lưu password và API phải tự xác minh access token.
- Railway PostgreSQL là database nghiệp vụ duy nhất của môi trường mục tiêu; không triển khai database nghiệp vụ trên Supabase.
- Railway được dùng cho PostgreSQL, backend API/server, worker, renderer và queue; frontend có thể là static host riêng hoặc được backend phục vụ.
- Railway environment/PostgreSQL service, Supabase Auth project/config và secret phải tách riêng giữa development, staging, pilot và production.
- Railway filesystem ephemeral không được dùng làm kho artifact chính; artifact phải ở object storage có persistence và backup.

---

## 3. Lộ trình tổng thể

~~~text
P0  Baseline nghiệp vụ + kiến trúc
        |
P1  Nền tảng repository + runtime + CI
        |
P1A Thiết kế UX/UI + design system bằng Google Stitch
        |
P2  Organization / Site / Machine / Folder / QA Case
        |
P3  Artifact storage + DICOM ingestion + validation
        |
P4  Analysis foundation + Machine QA + metric/rule
        |
P5  PSQA Gamma vertical slice
        |
P6  Report Builder + render + export
        |
P7  Trend + QA Protocol Library
        |
        +--------------------+
        |                    |
P8  Biological Toolkit   P9  Integrated verification
        |                    |
        +-----------> P10 Pilot / hardening / handover
                                      |
                         P11 Public web + remote access
~~~

Thời lượng dưới đây là ước lượng tương đối theo tuần làm việc, dùng để lập kế hoạch chứ không phải cam kết lịch cố định. Một phase chỉ bắt đầu khi dependency chính của phase đó đã đạt.

---

## 4. Mốc chính

| Mốc | Kết quả |
| :--- | :--- |
| M0 | Business analysis và technical baseline được khóa |
| M1 | Repository, local runtime và CI chạy được |
| M1A | Screen map, design system và frontend handoff từ Google Stitch được duyệt |
| M2 | Có thể tạo organization/site/machine/folder/QA case |
| M3 | Upload artifact, checksum và DICOM validation hoạt động |
| M4 | Machine QA và metric/rule engine hoạt động |
| M5 | PSQA Gamma end-to-end hoạt động |
| M6 | Report tùy chỉnh và export hoạt động |
| M7 | Trend và QA Protocol Library hoạt động |
| M8 | Biological Toolkit độc lập hoạt động |
| M9 | Regression, performance, backup/restore và pilot checklist hoàn tất |
| M10 | Pilot hoàn tất, release candidate và hồ sơ vận hành sẵn sàng |
| M11 | Public URL/HTTPS, remote smoke test và production runbook hoàn tất |

---

# PHASE 0 — Khóa yêu cầu và kiến trúc

**Thời lượng tham chiếu:** 1–2 tuần  
**Mục tiêu:** biến business-analysis.md thành baseline có thể code và kiểm thử.

## 0.1. Công việc

### Nghiệp vụ

- Đọc và lập traceability cho 26 BR, trong đó có yêu cầu truy cập web từ xa.
- Xác định màn hình, workflow và output tương ứng với từng BR.
- Chốt danh sách QA type:
  - Machine QA.
  - PSQA Gamma.
  - Visual Dose Review.
  - DVH/Plan Review.
- Chốt các khu vực Biological Toolkit:
  - BED/EQD2.
  - Đồ thị theo tổng liều D.
  - So sánh phác đồ.
  - Bảng giới hạn liều.
  - Protocol/phác đồ điều trị.
  - Knowledge library.
  - Re-irradiation.
  - Bù fraction.
- Xác nhận Biological Toolkit không có liên kết mặc định tới QA case hoặc ca bệnh.
- Lập danh sách thuật ngữ thống nhất: organization, site, machine, QA case, artifact, analysis run, report revision, scenario.

### Kỹ thuật

- Khóa kiến trúc tham chiếu trong technical.md.
- Khóa API naming convention.
- Khóa ID, timestamp, checksum và version convention.
- Khóa data status của artifact.
- Khóa gamma.measurement.v1.
- Khóa metric key convention.
- Khóa các engine interface:
  - GammaEngine.
  - DVHEngine.
  - BiologicalEngine.
  - ReportRenderer.
- Khóa môi trường development, test/CI, staging, pilot và production.
- Xác định các package/version sẽ pin ở lockfile.
- Khóa Railway project/environment strategy:
  - API/backend service.
  - PostgreSQL service.
  - worker/renderer service.
  - Redis service nếu dùng Railway cho queue.
  - public API networking.
- Khóa Supabase Auth strategy:
  - project/config theo environment.
  - login provider.
  - redirect/site URL.
  - token validation và JWKS/introspection.
  - mapping `supabase_user_id` với organization membership.
- Khóa object storage artifact độc lập với filesystem ephemeral của Railway.
- Khóa Railway PostgreSQL là database nghiệp vụ mục tiêu; xác định migration tool, private networking/reference variable, backup và restore.

### Kiểm thử

- Tạo test matrix từ BR → test case.
- Tạo danh sách golden/reference fixture cần có.
- Tạo checklist DICOM fixture.
- Tạo checklist Biological formula fixture.
- Tạo checklist Report Builder.

## 0.2. Deliverables

- technical.md hoàn chỉnh.
- Traceability matrix.
- Domain glossary.
- API route inventory.
- Test matrix.
- Input contract draft.
- Architecture decision record cho các lựa chọn còn mở.

## 0.3. Tiêu chí hoàn thành

- Mọi BR có ít nhất một module kỹ thuật và một test/acceptance target.
- Không còn requirement kỹ thuật quan trọng chỉ mô tả bằng từ “hỗ trợ” mà không có output.
- Có danh sách input/output cho từng workflow.
- Có quyết định rõ phần nào thuộc Clinical MVP và phần nào thuộc phase sau.

## 0.4. Không làm trong phase này

- Không viết engine Gamma đầy đủ.
- Không viết giao diện hoàn chỉnh.
- Không nhập dataset thật vào hệ thống.
- Không xây dựng tích hợp PACS/TPS.

---

# PHASE 1 — Nền tảng repository, runtime và CI

**Thời lượng tham chiếu:** 1–2 tuần  
**Phụ thuộc:** P0  
**Mục tiêu:** mọi developer có thể chạy hệ thống bằng một quy trình giống nhau.

## 1.1. Backend

- Tạo Python project.
- Tạo FastAPI app.
- Tạo configuration layer theo environment.
- Tạo health endpoint.
- Tạo request_id/correlation_id middleware.
- Tạo error contract.
- Tạo OpenAPI base.
- Tạo logging JSON.
- Tạo database session layer.
- Tạo migration baseline.
- Tạo object storage adapter interface.
- Tạo Redis/queue adapter interface.
- Tạo Supabase Auth JWT verification middleware.
- Tạo `UserIdentity` và `OrganizationMembership` mapping.
- Tạo error contract cho token hết hạn, sai issuer/audience/signature và user không thuộc organization.

## 1.2. Frontend

- Tạo React + TypeScript + Vite app.
- Tạo routing.
- Tạo layout chung.
- Tạo organization context selector.
- Tạo API client.
- Tạo query/cache layer.
- Tạo form validation layer.
- Tạo error/empty/loading state.
- Tạo component library tối thiểu.
- Tích hợp `@supabase/supabase-js` cho sign-in, session refresh, logout và password recovery.
- Không đưa service key hoặc Railway secret vào frontend bundle.

## 1.3. Hạ tầng local

- Docker Compose cho:
  - API.
  - Web.
  - PostgreSQL.
  - Redis.
  - Object storage.
  - Worker placeholder.
- PostgreSQL local chỉ phục vụ development/test; database mục tiêu là Railway PostgreSQL.
- File environment example.
- Seed data cho organization/site/machine.
- Script khởi tạo database.
- Script chạy test.
- Template Railway service/environment và reference variables.
- Railway PostgreSQL migration configuration skeleton.
- File cấu hình Supabase Auth theo environment, không chứa secret thật.

## 1.4. CI

Pipeline:

1. Backend format/lint.
2. Backend type check.
3. Frontend type check.
4. Unit test.
5. Frontend build.
6. Migration check.
7. OpenAPI generation.
8. Diff/document check.
9. Auth contract test với Supabase test project/mock.

## 1.5. Deliverables

- Local stack chạy được.
- Health check.
- Empty web shell.
- CI pipeline.
- Migration baseline.
- README setup.
- Environment template.
- Test command chuẩn.
- Supabase Auth client/server adapter skeleton.
- Railway service/environment manifest draft.

## 1.6. Tiêu chí hoàn thành

- Một developer mới có thể khởi động local stack theo README.
- API health, database và Redis health trả về đúng.
- Frontend gọi được API health.
- Frontend đăng nhập được bằng Supabase Auth test project và API xác minh được access token.
- CI chạy thành công trên repository sạch.
- Không có secret thật trong source code.
- Railway reference variables hoặc cấu hình local tương đương không làm lộ database/Redis/object-storage secret.
- Railway PostgreSQL connection được kiểm tra từ backend/private network, không từ frontend.
- Railway deployment skeleton phải tạo Railway PostgreSQL service cho database nghiệp vụ; Supabase chỉ cấu hình Auth.

---

# PHASE 1A — Thiết kế UX/UI, design system và handoff bằng Google Stitch

**Thời lượng tham chiếu:** 1–2 tuần  
**Phụ thuộc:** P0; có thể chạy song song với P1 sau khi các workflow nghiệp vụ chính đã được khóa  
**Mục tiêu:** tạo bộ thiết kế có thể triển khai thật, làm đầu vào thống nhất cho frontend của các phase sau.

## 1A.1. Phạm vi thiết kế

Tạo prototype và thiết kế cho các luồng:

- Trang vào hệ thống, trạng thái truy cập và organization context.
- Organization, site, machine, folder, QA case và tìm kiếm.
- Upload artifact, tiến trình upload, Input Manifest và DICOM validation.
- Machine QA, PSQA Gamma, cấu hình phân tích, queue/job đang chạy, map/kết quả/cảnh báo.
- Report Builder, bố cục report, revision, preview và export.
- Trend dashboard, drill-down về QA case và QA Protocol Library.
- Biological Toolkit độc lập: BED/EQD2, đồ thị theo tổng liều D, so sánh phác đồ, giới hạn liều, protocol/knowledge library, re-irradiation và bù fraction.

Mỗi luồng phải có các trạng thái tối thiểu:

- Loading và job đang xử lý.
- Empty state khi chưa có dữ liệu.
- Validation warning và invalid input.
- Error/retry.
- Kết quả thành công và kết quả có cảnh báo.
- Responsive layout cho màn hình desktop, tablet và mobile browser.

## 1A.2. Công việc với Google Stitch

- Tạo project thiết kế bằng dữ liệu giả lập, không dùng PatientID, DICOM hoặc dữ liệu thật.
- Dùng prompt/reference phù hợp để tạo các màn hình và luồng tương tác.
- Lặp lại thiết kế theo business-analysis.md và các quy tắc Gamma/Biological Toolkit.
- Chuẩn hóa navigation, layout, form, table, chart, alert, modal, upload và report block.
- Chốt design tokens: màu, typography, spacing, grid, breakpoint và trạng thái.
- Lập component inventory và mapping component → màn hình → workflow → API contract.
- Lưu prototype link/export/screenshot và quyết định thiết kế vào repository.
- Review thủ công mọi code hoặc asset do Stitch sinh ra trước khi đưa vào source frontend.

## 1A.3. Deliverables

- `UI-UX.md` được khóa làm design brief và prompt đầu vào cho Google Stitch.
- Screen map và user-flow map.
- Prototype/design link hoặc export từ Google Stitch.
- Design token specification.
- Component inventory và trạng thái component.
- `docs/design/DESIGN.md` hoặc tài liệu tương đương.
- Danh sách route frontend và API cần cho từng màn hình.
- UX acceptance checklist.
- Danh sách điểm cần làm rõ trước khi frontend implementation.

## 1A.4. Tiêu chí hoàn thành

- Mọi workflow Clinical MVP có màn hình và luồng tương ứng.
- Biological Toolkit có tab/khu vực riêng, không bị trộn vào QA case.
- Có đủ loading, empty, error, invalid và warning state cho workflow bất đồng bộ.
- Thiết kế thể hiện được report tùy chỉnh toàn diện theo yêu cầu nghiệp vụ.
- Component và token có thể chuyển thành frontend component dùng chung.
- Prototype không chứa dữ liệu thật.
- Frontend team có thể triển khai màn hình mà không phải đoán event, field, navigation hoặc trạng thái API.
- Design handoff được version hóa; thay đổi sau handoff tạo revision mới.

## 1A.5. Không làm trong phase này

- Không coi prototype hoặc code export là production frontend.
- Không kết nối Stitch trực tiếp với database, DICOM storage hoặc API production.
- Không đưa dữ liệu bệnh nhân vào công cụ thiết kế.
- Không chốt những metric/tolerance lâm sàng chưa có trong business-analysis.md hoặc protocol đã chọn.

---

# PHASE 2 — Organization, Site, Machine, Folder và QA Case

**Thời lượng tham chiếu:** 2–3 tuần  
**Phụ thuộc:** P1  
**Mục tiêu:** hoàn thiện lõi quản lý dữ liệu QA chưa phân tích.

## 2.1. Database/domain

- Tạo Organization.
- Tạo Site.
- Tạo Machine.
- Tạo Folder với parent-child.
- Tạo QA Case.
- Tạo quan hệ primary_folder.
- Tạo audit event cơ bản.
- Tạo search indexes.
- Tạo machine stable identifier.

## 2.2. API

- CRUD organization.
- CRUD site.
- CRUD machine.
- CRUD folder.
- Folder tree.
- Rename/move/archive folder.
- CRUD QA case.
- Search QA case theo:
  - site.
  - machine.
  - QA type.
  - QA cycle.
  - folder.
  - thời gian.
  - protocol.
  - status dữ liệu.

## 2.3. Frontend

- Organization dashboard.
- Site list.
- Machine list.
- Folder tree.
- Folder create/rename/move/archive.
- QA case list.
- QA case create/edit.
- QA case detail shell.
- Search/filter/pagination.

## 2.4. Kiểm thử

- Folder lồng nhau.
- Di chuyển folder không mất QA case.
- Archive không xóa record.
- Machine rename không tách trend identity.
- Organization không truy vấn lẫn dữ liệu.
- Search đúng filter.
- Audit event được tạo.

## 2.5. Deliverables

- Mốc M2.
- UI quản lý archive.
- API và migration.
- Test suite domain/folder/search.
- Seed data.

## 2.6. Tiêu chí hoàn thành

- Tạo được organization → site → machine → QA case.
- Tạo folder con và đặt tên tự do.
- Đổi tên/di chuyển/archive folder không làm mất QA case.
- QA case hiển thị đúng machine và site.
- Có audit history cho các thay đổi chính.

---

# PHASE 3 — Artifact storage, upload và DICOM validation

**Thời lượng tham chiếu:** 3–4 tuần  
**Phụ thuộc:** P2  
**Mục tiêu:** lưu file nguyên trạng và biết file có đủ điều kiện cho workflow nào.

## 3.1. Object storage

- Tạo object storage adapter.
- Object key không dùng trực tiếp filename.
- Lưu byte size, media type và checksum.
- Hỗ trợ upload progress.
- Hỗ trợ retry.
- Hỗ trợ download signed URL.
- Tách original object và derived object.
- Tạo artifact lifecycle.

## 3.2. Artifact API

- Upload artifact cho QA case.
- Upload measurement.
- Xem metadata.
- Download file.
- Archive artifact.
- Tạo derived artifact.
- Xem parent lineage.
- Xem checksum.
- Xem validation history.

## 3.3. DICOM parser

- Đọc file meta.
- Detect modality.
- Đọc SOP/Study/Series/Frame UIDs.
- Đọc RTDOSE metadata.
- Đọc RTSTRUCT metadata.
- Đọc RTPLAN metadata.
- Đọc CT geometry.
- Đọc dose grid.
- Đọc structure contours.
- Không save lại file nguồn.

## 3.4. Validation service

Validation code tối thiểu:

- INVALID_DICOM.
- UNSUPPORTED_MODALITY.
- MISSING_UID.
- MISSING_PIXEL_DATA.
- MISSING_DOSE_SCALING.
- INVALID_DOSE_GRID.
- GEOMETRY_MISMATCH.
- STRUCTURE_REFERENCE_MISMATCH.
- RTDOSE_REQUIRED.
- COMPARE_DATASET_REQUIRED.
- MEASUREMENT_REQUIRED.
- DVH_INPUT_REQUIRED.
- UNIT_MISSING.

## 3.5. Input Manifest

- Tạo manifest sau upload.
- Cho phép user chọn logical role.
- Lưu metadata snapshot.
- Lưu geometry summary.
- Lưu unit summary.
- Lưu checksum at use.
- Hiển thị validation warnings.

## 3.6. Measurement contract

- Viết schema validator cho gamma.measurement.v1.
- Tạo JSON fixture hợp lệ.
- Tạo fixture thiếu unit.
- Tạo fixture sai shape.
- Tạo fixture mơ hồ.
- Từ chối đoán cột hoặc đơn vị.

## 3.7. Frontend

- Artifact list.
- Upload progress.
- Validation result panel.
- DICOM metadata panel.
- Input role selector.
- Missing/invalid warning panel.
- Artifact lineage view.

## 3.8. Deliverables

- Mốc M3.
- Object storage integration.
- DICOM validation service.
- Input Manifest.
- Measurement contract.
- DICOM fixture set.

## 3.9. Tiêu chí hoàn thành

- Upload xong có checksum.
- File gốc tải xuống đúng byte.
- RTDOSE/RTSTRUCT/RTPLAN đọc được metadata yêu cầu.
- File sai bị cảnh báo hoặc invalid đúng mã.
- Không ghép DICOM chỉ dựa trên filename hoặc PatientID.
- Measurement mơ hồ không được chạy Gamma.

---

# PHASE 4 — Analysis foundation, Machine QA và metric/rule engine

**Thời lượng tham chiếu:** 3–4 tuần  
**Phụ thuộc:** P3  
**Mục tiêu:** tạo khung analysis bất đồng bộ và hoàn thiện Machine QA trước PSQA Gamma.

## 4.1. Analysis infrastructure

- Tạo AnalysisConfiguration.
- Tạo AnalysisRun.
- Tạo job queue.
- Tạo worker lifecycle.
- Tạo retry policy.
- Tạo job log.
- Tạo MetricResult.
- Tạo Warning.
- Tạo result artifact.
- Tạo rerun flow.
- Tạo engine version snapshot.

## 4.2. Metric/rule engine

- Thiết kế metric key.
- Hỗ trợ numeric metric.
- Hỗ trợ unit.
- Hỗ trợ baseline.
- Hỗ trợ tolerance/action level.
- Hỗ trợ margin.
- Hỗ trợ PASS/FAIL/REVIEW_REQUIRED/INVALID_INPUT/NOT_APPLICABLE.
- Lưu rule snapshot.
- Không hardcode tolerance trong UI.

## 4.3. Machine QA workflow

- Tạo QA checklist từ protocol.
- Nhập measurement.
- Nhập unit.
- Nhập baseline.
- Tính deviation.
- Tính margin.
- Hiển thị cảnh báo.
- Tạo metrics.
- Ghi trend point khi đủ context.
- Gắn artifact đo.

## 4.4. Test

- Unit test rule.
- Test unit conversion được cho phép.
- Test baseline deviation.
- Test tolerance/action level.
- Test missing value.
- Test invalid unit.
- Test rerun không xóa run cũ.
- Test worker retry.
- Test job failure không tạo result hợp lệ.

## 4.5. Deliverables

- Mốc M4.
- Generic analysis runner.
- Machine QA vertical slice.
- Metric/rule engine.
- Worker dashboard cơ bản.
- Regression test.

## 4.6. Tiêu chí hoàn thành

- Một Machine QA case đi từ input tới metric.
- Kết quả có unit, actual, limit, margin và status.
- Có thể chạy lại với protocol/configuration khác.
- Run cũ vẫn xem được.
- Trend point có source pointer về analysis run.

---

# PHASE 5 — PSQA Gamma vertical slice

**Thời lượng tham chiếu:** 4–5 tuần  
**Phụ thuộc:** P4  
**Mục tiêu:** hoàn thiện workflow Gamma end-to-end trên test/reference dataset.

## 5.1. Gamma contract và configuration

- Implement gamma.measurement.v1.
- Tạo GammaConfiguration schema.
- Hỗ trợ:
  - Dose difference.
  - DTA.
  - Absolute/relative.
  - Global/local.
  - Dose threshold.
  - Pass threshold.
  - 2D/3D.
  - Per-field/composite.
  - ROI/mask.
  - Alignment/shift.
  - Interpolation.
  - Search distance.
  - Max gamma.
- Lưu configuration snapshot.
- Validate configuration trước khi enqueue.

## 5.2. Gamma engine adapter

- Tạo interface GammaEngine.
- Implement adapter đầu tiên.
- Chuẩn hóa axes và dose array.
- Chuẩn hóa unit.
- Validate shape.
- Validate alignment.
- Chạy deterministic mode.
- Ghi engine version.
- Tạo gamma map.
- Tạo histogram.
- Tính pass rate và summary.

## 5.3. DICOM workflow

- RTDOSE required.
- Measurement/comparison required.
- RTSTRUCT optional cho phantom/plane.
- RTPLAN optional theo selected mode.
- Reject missing critical input.
- Warning cho input không critical.
- Lưu input manifest.

## 5.4. Frontend

- Chọn reference/evaluation.
- Chọn preset.
- Chỉnh Gamma configuration.
- Hiển thị validation trước khi chạy.
- Hiển thị job progress.
- Hiển thị pass rate.
- Hiển thị gamma map.
- Hiển thị histogram.
- Hiển thị warnings.
- Hiển thị configuration.
- Rerun với configuration khác.
- So sánh hai Gamma run.

## 5.5. Test/reference dataset

Tạo test case:

- Uniform field.
- Known shift.
- Known dose scaling.
- Different grid spacing.
- Low dose cutoff.
- Edge of field.
- 2D.
- 3D.
- Global.
- Local.
- Absolute.
- Relative.
- Invalid measurement.
- Missing RTDOSE.
- Missing comparison dataset.
- NaN/invalid values.

## 5.6. Deliverables

- Mốc M5.
- PSQA Gamma vertical slice.
- gamma.measurement.v1 validator.
- Gamma output artifacts.
- Golden/reference tests.
- User guide cho Gamma.

## 5.7. Tiêu chí hoàn thành

- PSQA thiếu RTDOSE không chạy.
- PSQA thiếu RTSTRUCT nhưng workflow phantom/plane vẫn chạy.
- Measurement mơ hồ không chạy.
- Gamma configuration lưu đủ tham số.
- Gamma map/pass rate/reason/warning được lưu.
- Rerun không xóa result cũ.
- Golden test đạt.

---

# PHASE 6 — Report Builder, rendering và export

**Thời lượng tham chiếu:** 3–4 tuần  
**Phụ thuộc:** P4; Gamma output từ P5 để render block Gamma  
**Mục tiêu:** report có thể tùy chỉnh toàn diện và tái hiện từ snapshot.

## 6.1. Template model

- Tạo ReportTemplate.
- Tạo ReportTemplateVersion.
- Tạo ReportBlockConfig.
- Tạo block registry.
- Tạo layout config.
- Tạo conditional display.
- Tạo selected metric keys.
- Tạo template clone.

## 6.2. Report Builder UI

- Block palette.
- Drag/reorder.
- Add/remove.
- Hide/show.
- Rename title/label.
- Select metrics.
- Configure chart period.
- Add notes.
- Preview.
- Save template.
- Create report revision.

## 6.3. Renderer

- Render HTML.
- Render PNG blocks.
- Render PDF.
- Render CSV/JSON.
- Embed provenance summary.
- Embed input manifest.
- Embed warnings/metrics theo cấu hình user.
- Store render artifact checksum.
- Handle render failure.

## 6.4. Revision

- Mỗi save report tạo revision.
- Snapshot configuration.
- Snapshot analysis result.
- Snapshot protocol.
- Snapshot template.
- View old revision.
- Compare revision.
- Export selected revision.
- Không đọc dữ liệu live khi render old revision.

## 6.5. Test

- Add/remove/hide block.
- Reorder block.
- Rename title.
- Select metric.
- Conditional block.
- Gamma map render.
- Vietnamese font.
- Large table.
- Old revision render.
- Export corrupted/missing artifact.
- Snapshot repeatability.

## 6.6. Deliverables

- Mốc M6.
- Report Builder.
- HTML/PDF/PNG/CSV/JSON export.
- Revision viewer.
- Snapshot/provenance display.

## 6.7. Tiêu chí hoàn thành

- User toàn quyền chỉnh report.
- Report có thể export.
- Report revision cũ tái hiện đúng snapshot.
- Report chứa được metric, warning, map, plot và notes.
- Render lỗi được báo rõ.
- Không làm thay đổi analysis result.

---

# PHASE 7 — Trend và QA Protocol Library

**Thời lượng tham chiếu:** 2–3 tuần  
**Phụ thuộc:** P4, P6  
**Mục tiêu:** biến kết quả rời rạc thành theo dõi lịch sử theo machine và protocol.

## 7.1. Trend

- Tạo TrendPoint.
- Tạo trend query.
- Filter machine/QA type/metric/time.
- Filter energy/mode/detector/phantom.
- Chọn baseline.
- Hiển thị tolerance/action.
- Hiển thị outlier.
- Link point → QA case → analysis → report.
- Export trend.
- Tạo maintenance event.
- Hiển thị maintenance marker.

## 7.2. QA Protocol Library

- CRUD protocol.
- Tạo protocol version.
- Tạo protocol rule.
- Gắn reference.
- Clone protocol.
- So sánh version.
- Gắn protocol vào QA case.
- Giữ snapshot protocol trong analysis/report.
- Tìm kiếm theo QA type/machine/keyword.

## 7.3. Test

- Trend không trộn machine.
- Unit khác nhau không vẽ chung.
- Baseline đúng.
- Outlier không bị xóa.
- Maintenance event hiển thị đúng.
- Protocol version cũ không thay đổi report cũ.
- Rule snapshot không bị cập nhật ngược.

## 7.4. Deliverables

- Mốc M7.
- Trend dashboard.
- QA Protocol Library.
- Protocol version viewer.
- Trend export.

## 7.5. Tiêu chí hoàn thành

- Xem được trend theo machine.
- Drill-down về source QA case.
- Có tolerance/action/baseline.
- Có event marker.
- Protocol cũ vẫn tái hiện đúng trong report cũ.

---

# PHASE 8 — Biological Toolkit độc lập

**Thời lượng tham chiếu:** 4–6 tuần  
**Phụ thuộc:** P1, P3 cho artifact tùy chọn, P6 cho calculation report  
**Mục tiêu:** xây dựng tab tính toán sinh học độc lập, không gắn mặc định với QA hoặc ca bệnh.

## 8.1. Biological workspace

- Tạo route/module riêng.
- Tạo scenario list.
- Tạo scenario editor.
- Tạo calculation history.
- Tạo source/assumption panel.
- Tạo independent report export.
- Không hiển thị QA case selector mặc định.
- Không tự truy cập treatment course.

## 8.2. BED/EQD2

- Implement model cơ bản.
- Validate n, d, D, alpha/beta.
- Hiển thị formula.
- Hiển thị unit.
- Hiển thị source.
- Hiển thị assumptions.
- Lưu calculation run.
- Tạo test values known-answer.

## 8.3. Đồ thị theo tổng liều D

- D range.
- Step.
- N.
- Alpha/beta series.
- Target/OAR labels.
- BED/EQD2 selection.
- Data table.
- PNG/SVG/CSV export.
- Snapshot chart configuration.

## 8.4. So sánh phác đồ

- Nhập course A/B/multiple.
- Tính BED/EQD2.
- Tính difference.
- Vẽ chart.
- Warning khi context không tương đương.
- Export comparison report.

## 8.5. Bảng giới hạn liều

- Disease.
- Anatomy.
- OAR/target.
- Metric.
- Limit/unit.
- Fractionation.
- Source.
- Evidence.
- Applicability.
- Search/filter.
- Version.

## 8.6. Protocol và knowledge library

- Treatment protocol reference.
- Phác đồ điều trị.
- Theory article.
- Formula entry.
- Alpha/beta entry.
- DOI/URL.
- Internal summary.
- Version.
- Date update.
- Search by disease/anatomy/topic.

## 8.7. Re-irradiation

- Multi-course input.
- Dates/time interval.
- Dose/fractions.
- Tissue/OAR/target.
- Alpha/beta per tissue.
- Recovery assumption.
- Scenario copy/compare.
- Scalar cumulative BED/EQD2.
- Optional standalone RTDOSE/RTSTRUCT input.
- Geometry/registration note.
- No spatial accumulation when contract missing.
- Warnings and limitation display.
- Independent report.

## 8.8. Bù fraction

- Original schedule.
- Delivered fractions.
- Missing fractions.
- Remaining fractions.
- Gap duration.
- Overall treatment time.
- Compare alternatives.
- Export scenario.

## 8.9. Tests

- Formula unit tests.
- Known-answer tests.
- Invalid input tests.
- Graph values.
- Multi-course comparison.
- Recovery assumption.
- Re-irradiation no-link test.
- Biological report snapshot.
- No QA case foreign key by default.

## 8.10. Deliverables

- Mốc M8.
- Biological Toolkit tab.
- BED/EQD2 engine.
- Graphs.
- Plan comparison.
- Dose limit table.
- Treatment protocol/knowledge library.
- Re-irradiation calculator.
- Independent calculation report.

## 8.11. Tiêu chí hoàn thành

- Biological Toolkit hoạt động độc lập.
- Tính BED/EQD2 đúng bộ test.
- Có đồ thị theo D.
- Có so sánh phác đồ.
- Có re-irradiation nhiều course.
- Có assumptions/source/history.
- Không tự link QA case/ca bệnh.
- Không sửa RT Plan hoặc prescription.
- Export được report độc lập.

---

# PHASE 9 — Integrated verification và hardening

**Thời lượng tham chiếu:** 3–4 tuần  
**Phụ thuộc:** P5, P6, P7; P8 nếu release cùng Biological Toolkit  
**Mục tiêu:** kiểm tra toàn bộ hệ thống như một sản phẩm, không chỉ từng module.

## 9.1. Integration test

Chạy đầy đủ:

- Organization → machine → QA case.
- Folder create/move/archive.
- Upload → checksum → validation.
- RTDOSE + measurement → Gamma.
- Machine QA → metric → trend.
- Gamma → report → PDF.
- Rerun → compare revisions.
- Protocol update → old report remains.
- Biological scenario → calculation → graph → report.
- Backup → restore → verify artifact checksum.

## 9.2. End-to-end test

Tạo test script cho:

- PSQA valid.
- PSQA missing RTDOSE.
- PSQA missing measurement.
- PSQA missing RTSTRUCT but phantom mode.
- DVH missing RTSTRUCT.
- DICOM geometry mismatch.
- Report custom block.
- Biological multi-course.
- Re-irradiation without registration.
- Worker failure/retry.
- Export failure.

## 9.3. Performance test

Đo:

- API metadata p50/p95.
- Upload file lớn.
- DICOM parse time.
- Gamma 2D/3D time.
- DVH time.
- Report render time.
- Queue throughput.
- Concurrent user metadata requests.
- Object storage read/write.

## 9.4. Reliability test

- Restart API.
- Restart worker.
- Redis unavailable.
- Database unavailable.
- Object storage unavailable.
- Job retry.
- Job duplicate.
- Partial render.
- Restore backup.
- Re-run after failure.

## 9.5. Security/tenant isolation test

- Organization A không đọc được organization B.
- Signed URL hết hạn.
- Token hết hạn.
- Download event được ghi.
- Không lộ secret trong log.
- Không lộ patient identifiers trong error message không cần thiết.

## 9.6. Documentation

- Deployment guide.
- Backup/restore guide.
- User guide.
- Gamma guide.
- Biological Toolkit guide.
- Troubleshooting guide.
- Release notes.
- Known limitations.
- Test report.

## 9.7. Deliverables

- Mốc M9.
- Integrated test report.
- Performance report.
- Backup/restore evidence.
- Security/tenant isolation test.
- Release candidate checklist.

## 9.8. Tiêu chí hoàn thành

- Không còn lỗi P0/P1 chưa có quyết định xử lý.
- Tất cả regression test pass.
- Golden/reference test pass.
- E2E workflow pass.
- Restore test pass.
- Có deployment và rollback instruction.
- Có danh sách known limitations.

---

# PHASE 10 — Pilot, vận hành và chuyển giao

**Thời lượng tham chiếu:** 3–6 tuần tùy quy mô  
**Phụ thuộc:** P9  
**Mục tiêu:** đưa bản release candidate vào môi trường pilot, sử dụng dataset thật theo kế hoạch và biến lỗi thực tế thành regression test.

## 10.1. Chuẩn bị pilot

- Chọn site/machine pilot.
- Chọn workflow:
  - Machine QA.
  - PSQA Gamma.
  - Report.
  - Trend.
- Chuẩn bị test user.
- Chuẩn bị dataset thật theo phạm vi đã thống nhất.
- Chuẩn bị backup trước pilot.
- Chuẩn bị runbook.
- Chuẩn bị kênh ghi nhận lỗi.
- Chuẩn bị tiêu chí dừng pilot khi có lỗi nghiêm trọng.

## 10.2. Shadow/parallel use

Trong thời gian đầu:

- Lưu kết quả RT-CONNECT song song với workflow hiện tại.
- So sánh output.
- Ghi nhận sai khác.
- Chọn case đại diện.
- Bổ sung case sai khác vào regression fixture.
- Không xóa output cũ khi engine được sửa.
- Mỗi bản sửa tạo engine/application version mới.

## 10.3. Dataset thật

- Import dataset thật theo từng workflow.
- Theo dõi DICOM variation.
- Theo dõi detector/phantom variation.
- Theo dõi report format.
- Ghi nhận performance.
- Ghi nhận lỗi user input.
- Ghi nhận false warning/false invalid.
- Chuyển lỗi lặp lại thành test.

## 10.4. Biological Toolkit pilot

Biological Toolkit được pilot riêng:

- Dùng scenario không gắn ca bệnh mặc định.
- Kiểm tra công thức và đồ thị.
- Kiểm tra table nguồn.
- Kiểm tra re-irradiation multi-course.
- Kiểm tra report độc lập.
- Ghi nhận giới hạn model và yêu cầu bổ sung.
- Không dùng Biological output để tự động thay đổi plan.

## 10.5. Bàn giao

- Bàn giao deployment.
- Bàn giao backup/restore.
- Bàn giao user guide.
- Bàn giao test report.
- Bàn giao release manifest.
- Bàn giao known limitations.
- Bàn giao incident/change log.
- Xác nhận version đang chạy.
- Tạo kế hoạch release tiếp theo.

## 10.6. Tiêu chí hoàn thành

- Pilot workflow chạy ổn định trong phạm vi chọn.
- Không mất artifact hoặc report.
- Sai khác với workflow hiện tại được ghi nhận và giải thích.
- Lỗi thực tế đã có regression test nếu đã sửa.
- Có backup/restore thành công.
- Có tài liệu vận hành.
- Có backlog cải tiến sau pilot.

---

# PHASE 11 — Public Web Deployment và Remote Access

**Thời lượng tham chiếu:** 2–4 tuần  
**Phụ thuộc:** P10; P9 phải hoàn tất các kiểm thử tích hợp, performance, backup/restore và rollback  
**Mục tiêu:** phát hành RT-CONNECT thành website có URL public, truy cập được từ xa qua HTTPS và có đủ vận hành production.

## 11.1. Quyết định mô hình hạ tầng

- Tạo Railway project và tách tối thiểu các environment: staging, pilot và production.
- Tạo các Railway backend service:
  - `api` cho FastAPI.
  - `postgres` cho Railway PostgreSQL database nghiệp vụ.
  - `worker` cho Gamma/DVH/import/export.
  - `renderer` nếu report rendering tách service.
  - Redis nếu dùng Railway cho job queue.
- Dùng Railway public networking cho API; dùng Railway private networking/reference variables cho API → worker/renderer/Redis.
- Frontend là static web host riêng hoặc bundle được API Railway phục vụ; phải dùng đúng API URL của environment.
- Tạo Supabase Auth project/config riêng cho staging, pilot và production; không dùng nhầm redirect URL hoặc key giữa các environment.
- Chốt Railway PostgreSQL service/connection, private networking/reference variable, migration workflow, backup và restore.
- Chốt object storage S3-compatible/MinIO có persistence và backup; không dùng filesystem ephemeral của Railway làm kho artifact chính.
- Chốt domain/subdomain, DNS owner, nơi quản lý certificate và người phụ trách gia hạn.
- Chốt staging domain và production domain.
- Chốt nơi lưu log/metrics và cách truy cập log Railway.
- Chốt dung lượng, băng thông, giới hạn upload, retention, backup schedule và thời gian khôi phục mục tiêu.

## 11.2. Provisioning và network boundary

- Dựng và cấu hình Railway project/environment/service.
- Cấu hình Railway variables và reference variables; secret không nằm trong repository.
- Cấu hình Railway public domain/custom domain cho API endpoint cần thiết; cấu hình domain cho frontend theo static host hoặc API-serving topology.
- Chỉ expose frontend/API cần thiết qua HTTPS.
- Đặt Redis, worker, renderer và Orthanc ở private network; không public trực tiếp.
- Kết nối Railway API/worker tới Railway PostgreSQL qua private networking, TLS và connection string/reference variable trong secret; không đưa credential vào frontend.
- Cấu hình persistence/retention/backup/restore cho Railway PostgreSQL; Redis chỉ là queue state.
- Object storage phải có persistence riêng.
- Cấu hình Supabase Auth site URL, redirect URL, provider, email/OTP và JWT verification settings.
- Cấu hình log, metrics, health check và alert.

## 11.3. Domain, HTTPS và web delivery

- Tạo public domain/custom domain cho frontend và Railway public domain/custom domain cho API.
- Cấu hình DNS record theo static host/Railway cung cấp và xác nhận domain ownership.
- Kiểm tra Railway automatic TLS certificate và quy trình renewal.
- Redirect HTTP → HTTPS.
- Cấu hình CORS theo domain thật.
- Cấu hình secure cookie/token, session timeout và CSRF nếu dùng cookie session.
- Cấu hình frontend deep-link/reload không lỗi 404.
- Cấu hình cache static assets nhưng không cache nhầm dữ liệu QA/report riêng tư.
- Cấu hình body limit và timeout đủ cho upload DICOM/measurement lớn.
- Cấu hình signed URL có thời hạn cho download.

## 11.4. Deploy application

- Build frontend, API, worker và report renderer từ release manifest đã pin version.
- Deploy frontend lên static web host đã chọn hoặc đóng gói static bundle để API Railway phục vụ, theo đúng topology đã chốt.
- Deploy các service lên Railway staging environment trước production.
- Kiểm tra Railway private domain/reference variable giữa API, Redis, worker và renderer.
- Kiểm tra API/worker kết nối đúng Railway PostgreSQL service/environment qua private networking/TLS.
- Kiểm tra frontend gọi API qua public HTTPS endpoint; browser không gọi private Railway domain.
- Kiểm tra Supabase Auth sign-in, refresh, logout, redirect URL và access-token verification.
- Chạy application migration trên Railway PostgreSQL staging service và kiểm tra dữ liệu mẫu.
- Kiểm tra API, frontend, queue, worker, object storage và renderer.
- Backup Railway PostgreSQL/object storage trước production migration.
- Deploy Railway production environment theo version manifest và environment variables đã review.
- Smoke test sau deploy.
- Ghi application version, engine version, schema version, renderer version và commit/release identifier.

## 11.5. Kiểm thử truy cập từ xa

Thực hiện từ ít nhất một mạng ngoài hạ tầng (ví dụ mạng di động hoặc mạng Internet khác) trên desktop và mobile browser:

- Mở public URL, DNS, certificate và HTTPS hoạt động.
- Đăng nhập/đăng xuất và giữ session đúng.
- Truy cập đúng organization; không đọc chéo organization.
- Tạo folder/QA case và upload artifact.
- Upload file lớn không timeout do reverse proxy.
- Xem Input Manifest và validation.
- Tạo, theo dõi và hoàn tất job Gamma/DVH/render sau refresh browser.
- Xem biểu đồ, report, revision và tải export qua signed URL.
- Mở Biological Toolkit độc lập với QA case.
- Refresh/deep-link mọi route chính không lỗi.
- Mất kết nối tạm thời không làm mất artifact hoặc tạo analysis trùng.
- Error message không lộ stack trace, secret hoặc định danh không cần thiết.

## 11.6. Backup, monitoring và rollback

- Chạy backup đầu tiên và thử restore Railway PostgreSQL/object storage.
- Kiểm tra checksum artifact sau restore.
- Kiểm tra restart Railway API/worker/Redis mà không làm mất dữ liệu.
- Thiết lập alert cho API down, worker backlog, job failure, disk gần đầy, certificate sắp hết hạn, backup thất bại và error rate tăng.
- Xác định owner xử lý incident và thời gian phản hồi nội bộ.
- Thử rollback Railway deployment/image/version ở staging.
- Có runbook cho deploy, rollback, backup/restore, rotate secret và gia hạn certificate.

## 11.7. Deliverables

- Public URL và DNS record.
- TLS certificate và quy trình gia hạn.
- Staging/production deployment manifest.
- Railway project/service/environment map.
- Railway public/private networking configuration.
- Supabase Auth project/config checklist theo environment.
- Environment/secret/reference-variable template.
- Object storage persistence/backup configuration.
- Remote access smoke-test report.
- Backup/restore evidence.
- Monitoring/alert checklist.
- Rollback evidence.
- Production runbook.
- Release manifest và known limitations.

## 11.8. Tiêu chí hoàn thành

- Website truy cập được từ mạng ngoài bằng HTTPS.
- Chỉ web/API cần thiết được expose; service dữ liệu/nội bộ không public trực tiếp.
- Các workflow Clinical MVP và Biological Toolkit trong phạm vi release chạy được từ xa.
- Upload, worker job, report/export và signed download đã được kiểm tra.
- Backup/restore và rollback có bằng chứng thực thi.
- Monitoring và cảnh báo tối thiểu đã hoạt động.
- Có người phụ trách vận hành, domain, certificate và incident.
- Bản phát hành ghi rõ version frontend/API/engine/schema/renderer.
- Không public release nếu chỉ mới kiểm tra localhost/LAN.

---

## 5. Ma trận phase và deliverable

| Deliverable | Phase chính | Phase kiểm tra |
| :--- | :--- | :--- |
| Architecture baseline | P0 | P9 |
| Local runtime | P1 | P9 |
| UI/UX design brief and Stitch prompt | P1A | P2–P10 |
| Supabase Auth integration | P0, P1 | P9, P11 |
| Railway PostgreSQL schema/migrations | P0, P1, P11 | P9, P11 |
| Railway service topology | P0, P1, P11 | P9, P11 |
| UX/UI screen map và design system | P1A | P2–P10 |
| Google Stitch prototype/design handoff | P1A | P2–P10 |
| Organization/site/machine | P2 | P9 |
| Folder/archive | P2 | P9 |
| QA case | P2 | P9 |
| Artifact storage | P3 | P9 |
| DICOM validator | P3 | P5, P9 |
| Input Manifest | P3 | P5, P9 |
| Machine QA | P4 | P9 |
| Metric/rule engine | P4 | P5, P7 |
| PSQA Gamma | P5 | P9, P10 |
| Report Builder | P6 | P9, P10 |
| Trend | P7 | P9, P10 |
| QA Protocol Library | P7 | P9, P10 |
| Biological Toolkit | P8 | P9, P10 |
| Backup/restore | P9 | P10 |
| Pilot release | P10 | Ongoing |
| Public web/HTTPS deployment | P11 | P11, ongoing |
| Remote access smoke test | P11 | P11, ongoing |
| Production runbook/monitoring/rollback | P11 | P11, ongoing |

---

## 6. Backlog ưu tiên

### P0 — Bắt buộc cho nền tảng

- Organization/site/machine.
- Folder.
- QA case.
- Artifact.
- Checksum.
- DICOM metadata.
- Input Manifest.
- Validation.
- Analysis Run.
- Metric/rule.
- Report revision.
- Audit/provenance.
- Test harness.
- Backup/restore.

### P1 — Bắt buộc cho Clinical MVP

- Frontend foundation theo design handoff P1A.
- Machine QA.
- PSQA Gamma.
- gamma.measurement.v1.
- Gamma map/pass rate.
- Report export.
- Trend.
- QA Protocol Library.
- Worker monitoring.
- Performance baseline.

### P1A — Bắt buộc cho frontend implementation

- `UI-UX.md` design brief/prompt.
- Google Stitch screen map/prototype.
- Design tokens.
- Component inventory.
- Loading/empty/error/invalid/warning states.
- Responsive layouts.
- Route/API/component mapping.
- Design revision và handoff checklist.

### P2 — Mở rộng

- Visual Dose Review.
- DVH/Plan Review.
- Structure-level biological view.
- Orthanc/DICOMweb integration.
- More vendor measurement adapters.
- Advanced spatial re-irradiation.
- More report renderer formats.

### P11 — Bắt buộc cho public release

- Railway project và environment.
- Railway backend `api`, `worker`, `renderer` và Redis/queue services nếu dùng Railway cho queue.
- Railway public/private networking và reference variables.
- Frontend static host hoặc static bundle được backend phục vụ.
- Supabase Auth project/config theo environment.
- Railway PostgreSQL service, migration, private connection, backup và restore.
- Domain/DNS.
- HTTPS/TLS.
- Staging và production deployment.
- Private network cho Railway PostgreSQL, Redis/worker/renderer/Orthanc; database chỉ nhận kết nối qua private credential/reference variable của backend.
- Object storage persistence/backup ngoài filesystem ephemeral của Railway.
- Upload limit, timeout, signed URL và CORS.
- Monitoring/alert.
- Backup/restore.
- Rollback.
- Remote access smoke test trên mạng ngoài.

---

## 7. Bộ test bắt buộc theo release

### Release nền tảng

- Domain unit tests.
- Organization isolation tests.
- Folder tests.
- Artifact checksum tests.
- DICOM metadata tests.
- Migration tests.
- API contract tests.

### Release frontend/design handoff

- Screen-to-BR traceability check.
- Prototype navigation/flow check.
- Design token/component mapping check.
- Loading/empty/error/invalid/warning state check.
- Responsive desktop/tablet/mobile check.
- No real patient/DICOM data in design artifacts.
- Stitch export/code review check.

### Release Clinical MVP

- Machine QA golden tests.
- Gamma 2D/3D golden tests.
- Global/local tests.
- Absolute/relative tests.
- Geometry mismatch tests.
- Missing input tests.
- Report snapshot tests.
- Trend drill-down tests.
- Worker retry tests.
- Backup/restore tests.

### Release Biological Toolkit

- BED/EQD2 known-answer tests.
- D curve tests.
- Multi-course tests.
- Recovery assumption tests.
- Re-irradiation warning tests.
- Dose limit lookup tests.
- Knowledge/protocol version tests.
- Independent report tests.
- No automatic QA/patient linkage tests.

### Release public web

- Railway service health/deployment check.
- DNS and HTTPS certificate check.
- HTTP-to-HTTPS redirect check.
- Supabase Auth sign-in/refresh/logout/redirect/JWT validation check.
- Environment isolation check for Railway and Supabase projects/config.
- External-network login/session check.
- Organization isolation check from public endpoint.
- Upload large artifact and proxy timeout check.
- Queue/worker job after browser refresh or reconnect.
- Report/export/signed-download check.
- Frontend deep-link/reload check.
- Private service exposure scan/check.
- Backup/restore checksum check.
- Monitoring/alert check.
- Staging rollback check.

---

## 8. Rủi ro và cách xử lý

| Rủi ro | Ảnh hưởng | Cách xử lý |
| :--- | :--- | :--- |
| DICOM vendor variation | Validation/geometry sai | Fixture theo vendor, log metadata, adapter riêng |
| Gamma định nghĩa khác nhau | Pass rate không so sánh được | Lưu đầy đủ config và engine version |
| File lớn | Chậm/timeout | Object storage, async worker, streaming |
| Report tùy chỉnh quá linh hoạt | Khó render/reproduce | Block schema, snapshot, renderer test |
| Protocol thay đổi | Report cũ thay đổi | Protocol version + snapshot |
| Dữ liệu measurement mơ hồ | Kết quả sai | Contract bắt buộc, reject ambiguity |
| Worker lỗi | Thiếu result | Retry, idempotency, failed job visibility |
| DICOM geometry không khớp | DVH/Gamma sai | Blocking validation cho geometry critical |
| Model sinh học bị diễn giải quá mức | Hiểu sai scenario | Hiển thị source, assumptions, limitation |
| Re-irradiation thiếu spatial mapping | Cumulative dose sai | Chỉ scalar khi thiếu registration, không tự cộng spatial |
| Dataset thật phát hiện case mới | Regression gap | Chuyển case thành fixture trước khi sửa |
| SQLite bị dùng ngoài demo | Mất ổn định/concurrency | PostgreSQL bắt buộc ở pilot |
| Render PDF khác môi trường | Report không tái lập | Pin renderer/font/container |
| Stitch design và frontend implementation lệch nhau | UI không phản ánh workflow/API thật | Screen-to-BR mapping, component contract, design revision và review code export |
| Public web bị cấu hình như LAN-only | Người dùng ngoài không truy cập được | Staging/public smoke test từ mạng ngoài trước release |
| Service nội bộ bị expose ra Internet | Tăng nguy cơ mất dữ liệu và khó kiểm soát vận hành | Private network, firewall, chỉ expose HTTPS edge, signed URL |
| DNS/TLS/certificate hoặc proxy timeout | Website lỗi, upload/report thất bại từ xa | Owner, certificate monitoring, body limit/timeout test và runbook |
| Public release không có rollback/restore | Khó phục hồi khi deploy lỗi | Version manifest, backup trước migration, restore evidence và rollback rehearsal |
| Supabase Auth project/config bị dùng nhầm environment | Đăng nhập/redirect sai hoặc lộ nhầm dữ liệu | Tách project/config, biến môi trường, test issuer/audience/redirect và checklist release |
| Railway service dùng sai private/public networking | API không kết nối nội bộ hoặc database bị expose | Service map, private reference variables, chỉ public web/API và external exposure check |
| Railway filesystem ephemeral được dùng lưu artifact | Mất file khi redeploy/restart | S3-compatible/MinIO persistence, checksum và restore test |
| Railway resource/timeout không đủ cho Gamma, DVH hoặc render | Job chậm, bị kill hoặc backlog tăng | Benchmark sớm, worker riêng, resource/timeout target và monitoring backlog |

---

## 9. Definition of Done

Một task chỉ được đánh dấu hoàn thành khi:

- Có code hoặc tài liệu đúng phạm vi.
- Có test phù hợp.
- Có migration nếu thay đổi schema.
- Có API contract nếu thay đổi endpoint.
- Có fixture nếu thêm workflow/input.
- Có log/error handling.
- Có provenance nếu tạo result/report.
- Không ghi đè file/result cũ.
- Frontend có loading, error và empty state.
- Có cập nhật technical.md hoặc plan.md khi quyết định thay đổi.
- CI pass.
- Không có secret hoặc dữ liệu thật không cần thiết trong repository.
- Nếu là engine, có golden/reference test.
- Nếu là report, có snapshot/re-render test.
- Nếu là DICOM workflow, có fixture valid và invalid.
- Nếu là Biological Toolkit, có known-answer test.
- Nếu là frontend, có design handoff và screen-to-BR traceability.
- Nếu là public release, có remote smoke test qua HTTPS và bằng chứng service nội bộ không bị expose.
- Nếu dùng Auth, có test Supabase Auth token/session và không có secret trong frontend bundle.
- Nếu deploy Railway, có service/environment map, reference variables, persistence và rollback evidence.

---

## 10. Quy trình quản lý thay đổi

1. Ghi yêu cầu hoặc lỗi thành issue/task.
2. Xác định BR/technical section liên quan.
3. Xác định ảnh hưởng tới schema, API, engine, report và test.
4. Viết hoặc cập nhật test trước khi sửa engine nếu có thể.
5. Thực hiện thay đổi trong revision.
6. Chạy test liên quan và full suite.
7. Cập nhật technical.md/plan.md.
8. Ghi release note.
9. Nếu ảnh hưởng kết quả, tăng engine/application version.
10. Không sửa ngược report/result cũ.

---

## 11. Tiêu chí sẵn sàng theo phase

| Phase | Sẵn sàng khi |
| :--- | :--- |
| P0 | Baseline và traceability hoàn chỉnh |
| P1 | Stack chạy được và CI pass |
| P1A | Design handoff, component map và responsive state checklist hoàn tất |
| P2 | CRUD archive end-to-end pass |
| P3 | File gốc, checksum và validation pass |
| P4 | Machine QA tạo metric đúng |
| P5 | Gamma vertical slice + golden test pass |
| P6 | Report tùy chỉnh + snapshot render pass |
| P7 | Trend và protocol version pass |
| P8 | Biological known-answer và no-link test pass |
| P9 | Integrated, performance và restore test pass |
| P10 | Pilot checklist, runbook và release candidate hoàn tất |
| P11 | Public URL/HTTPS, remote test, monitoring, restore và rollback evidence hoàn tất |

---

## 12. Kết quả bàn giao cuối cùng

Bản bàn giao gồm:

- Source code.
- Database migrations.
- Container/deployment files.
- Configuration template.
- API/OpenAPI schema.
- Test suite.
- DICOM fixtures.
- Gamma golden/reference fixtures.
- Biological known-answer fixtures.
- User guide.
- Administrator/runbook.
- Backup/restore guide.
- Release manifest.
- Test report.
- Known limitations.
- Pilot findings.
- Post-pilot backlog.
- Public URL/domain và DNS/TLS configuration.
- Staging/production deployment manifest.
- Remote access smoke-test report.
- Monitoring and alert checklist.
- Backup/restore evidence cho topology public web.
- Rollback evidence và production runbook.
- Railway service/environment map và reference-variable guide.
- Supabase Auth configuration checklist (không bàn giao secret plaintext).

---

## 13. Kết luận

RT-CONNECT được triển khai theo vertical slice có thể chạy và kiểm thử ở từng phase. Clinical MVP đi từ archive và artifact integrity đến Machine QA, PSQA Gamma, report và trend. Biological Toolkit được triển khai thành track riêng, có engine, report và lịch sử riêng, không tự liên kết với QA case hoặc ca bệnh.

Test/reference dataset là căn cứ nghiệm thu trong giai đoạn phát triển. Dataset thật được đưa vào pilot và vận hành để mở rộng regression suite, phát hiện variation thực tế và cải tiến workflow. Mọi thay đổi ảnh hưởng kết quả phải có version mới, test mới và không làm mất lịch sử cũ.

Sau pilot, P11 đưa hệ thống lên public web để các thành viên được tổ chức cho phép truy cập từ xa qua HTTPS. Public web chỉ là lớp truy cập; Railway PostgreSQL chỉ được backend truy cập qua private networking/reference variable, còn object storage, Redis, worker và Orthanc không public trực tiếp, có backup/restore, monitoring và rollback. Google Stitch phục vụ thiết kế và handoff UI ở P1A, không phải dependency runtime của production.

Trong topology đã chọn, Supabase là auth/identity plane cho Supabase Auth, còn Railway là application/backend/data plane cho backend API/server, PostgreSQL, worker, renderer và queue. Frontend là static web host riêng hoặc static bundle được backend phục vụ. Việc dùng Railway/Supabase phải được kiểm tra theo từng environment, đặc biệt là public/private networking, kết nối Railway PostgreSQL, persistence của artifact, redirect URL, JWT validation, backup và rollback.
