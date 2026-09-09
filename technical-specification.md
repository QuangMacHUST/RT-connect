# ĐẶC TẢ KỸ THUẬT

## Dự án RT-CONNECT

- **Tên file:** technical-specification.md
- **Phiên bản:** 1.15 — đồng bộ specification.md v1.17, plan.md v4.3 và business-analysis.md v0.22; bổ sung entity/migration/API membership-invitation P4, unique pending invitation và active-context invariant; giữ reference tới feature-card/handoff, operation/error/evidence record, dependency graph, change-impact gate và status/readiness surface P20 (2026-09-09)
- **Nguồn yêu cầu:** business-analysis.md phiên bản 0.22
- **Trạng thái:** Bản đặc tả kỹ thuật cơ sở để triển khai
- **Ngôn ngữ giao diện ưu tiên:** Tiếng Việt, có thể mở rộng tiếng Anh
- **Mô hình triển khai mặc định:** Web truy cập từ xa qua HTTPS; Supabase Auth quản lý identity/session; Railway triển khai backend API, PostgreSQL, worker, renderer và queue. Frontend là static web riêng hoặc được API phục vụ tùy phương án phát hành

Tài liệu này giữ kiến trúc và thiết kế kỹ thuật nền. [specification.md](specification.md) là hợp đồng hành vi/validation/error/transaction/thuật toán chi tiết mới; [plan.md](plan.md) là kế hoạch P0–P20 và testcase/exit gate; [business-analysis.md](business-analysis.md) sở hữu nghiệp vụ. Tài liệu không đưa thêm phân cấp bác sĩ–kỹ sư hoặc phân quyền theo từng hành động.

> Đồng bộ v1.15: các bảng API/entity trong tài liệu này không đồng nghĩa mọi endpoint đã có code. Baseline cloud ngày 2026-09-04 và adapter cũ là snapshot lịch sử; trạng thái source mới nhất nằm trong implementation-progress.md và plan.md §1.3. Contract chi tiết ở specification.md §2–§14 là authority cho hành vi/validation/error/thuật toán/phase handoff. P6–P17 hiện đã có các slice code được ghi rõ trong mục 0.4; P4 đã bổ sung local membership/invitation slice trên migration `20260909_0018` và public staging đã migrate/deploy/readiness/version-parity pass, nhưng Auth browser và persistence vẫn phải revalidate trước khi gọi available. P17 có CT pixel preview local nhưng explicit P11/P16 binding, DVH report source và CT/staging evidence vẫn phải kiểm theo candidate. P18 có local route-to-persistence và local backup/restore support nhưng chưa thay fault/restore/pilot staging gate. Phần còn lại vẫn là TARGET cho đến khi có evidence. Không thêm commissioning approval gate ngoài test/reference dataset ở phase phát triển và pilot P18 đã thống nhất.

---

## 0. Baseline tích hợp đang có

Baseline dưới đây được kiểm tra trực tiếp ngày 2026-09-04. ID hạ tầng được ghi để tránh nối nhầm project; trạng thái deployment/service phải được truy vấn lại trước mỗi lần triển khai.

### 0.1. Google Stitch

| Thuộc tính | Giá trị |
| :--- | :--- |
| Project title | `RT-connect` |
| Project ID | `14242591911141046021` |
| Visibility hiện tại | `PUBLIC` |
| Device baseline | `DESKTOP` |
| Nguồn truy cập | Google Stitch MCP |

`list_screens` hiện trả sáu screen resource đang hoạt động: bốn application screen và hai image asset (logo, avatar). Chỉ bốn application screen dưới đây được map thành route sản phẩm:

| Screen ID | Title | Module |
| :--- | :--- | :--- |
| `70b9f1d256884221ae20e63b5244db11` | Trang chủ - Home Dashboard | MOD-01 |
| `4c9ec57310fd404cbae3b53b0bab2368` | Kho lưu trữ QA & Thư mục | MOD-03 |
| `ffb87901b3194bd3aff8760c54c2f9f4` | Phân tích PSQA Gamma Workspace | MOD-04, MOD-06 |
| `a1478466ace843c5aaf9a15dfc58273e` | Trình biên soạn Báo cáo - Report Builder Studio | MOD-07 |

Logo và avatar không phải route. `get_project` vẫn có thể trả bốn instance Biological cũ ở trạng thái `hidden`; chúng là legacy/deprecated sau khi user loại khỏi canvas hoạt động, không phải nguồn thiết kế hiện hành và không được tự khôi phục. MOD-10 đến MOD-13 phải dùng các screen implementation hiện hành theo thứ tự Biological Hub → BED/EQD2 → Plan Comparison → Re-irradiation/Fraction Compensation, kế thừa Design System `Clinical Precision Interface` và AppShell của bốn screen đang hoạt động. Một screen Stitch riêng chỉ là nguồn tham khảo tùy chọn, không phải điều kiện để route có code.

Các resource tài liệu cũ trên Stitch không phải bản canonical trong repository. `UI-UX.md` không còn được duy trì; việc thiết kế mới hoặc sửa thiết kế được thực hiện trực tiếp trong project Stitch qua MCP.

Vì project Stitch hiện là `PUBLIC`, chỉ được dùng dữ liệu giả lập. Không upload DICOM thật, PatientID, token, database URL, secret hoặc dữ liệu vận hành vào prompt, image, HTML hay metadata của Stitch.

### 0.2. Railway

| Thuộc tính | Giá trị kiểm tra hiện tại |
| :--- | :--- |
| Railway project name | `prolific-learning` |
| Railway project ID | `339f2c50-ddd7-491f-8c4e-da2a2d169502` |
| Environment hiện có | `production` và `staging` |
| Environment ID | `910dff25-75b6-42b2-bf6b-e2601ba9d7d2` |
| Service hiện có | `RT-connect` |
| Service ID | `9544c3e6-c8bd-4c29-b62e-c6172eb51af3` |
| Latest deployment tại thời điểm kiểm tra | `FAILED` |
| PostgreSQL service | Có service riêng cho production và staging |
| Worker/Redis/Renderer service | Staging đã có Gamma worker và Redis; renderer chưa provision |
| Ngân sách/credit khởi điểm do user cung cấp | 5 USD; usage/cost phải được kiểm tra theo service và environment |

Project Token hiện trỏ đúng vào environment `production`. Token cấp rộng hơn có thể liệt kê project và được dùng để provisioning environment/service nếu phạm vi Railway thực tế cho phép. Không ghi giá trị token vào tài liệu, source, log hoặc Railway runtime variables của ứng dụng.

Repository `.env` dùng hai tên nội bộ:

- `RAILWAY_PROJECT_TOKEN`: ánh xạ tạm thành `RAILWAY_TOKEN` khi Railway CLI cần thao tác project/environment hiện tại.
- `RAILWAY_ACCOUNT_TOKEN`: ánh xạ tạm thành `RAILWAY_API_TOKEN` khi Railway CLI cần thao tác account/workspace.

Chỉ đặt một biến xác thực CLI chính thức tại một thời điểm. Hai token là credential phục vụ deployment/automation, không phải secret mà backend RT-CONNECT cần khi chạy. `.env` phải tiếp tục bị Git ignore và không được đưa vào image build.

### 0.3. Supabase và repository

- Supabase được chọn làm Auth/Identity/Session plane nhưng repository chưa có biến cấu hình Supabase tại baseline này.
- Cần tạo/chọn Supabase project cho development/staging trước khi MOD-00 được triển khai.
- Repository hiện chỉ có tài liệu Markdown, chưa có frontend, backend, migration, test hoặc deployment manifest.
- Các file `UI-UX.md`, `DESIGN.md` và `Biological-toolkit.html` đã được user xóa; không tự khôi phục. Thiết kế UI được truy xuất qua Stitch MCP.
- Không triển khai trực tiếp production từ baseline tài liệu. Trước hết phải tạo staging, sửa nguyên nhân deployment thất bại và chạy health/migration/smoke test.

### 0.4. Addendum repository hiện tại — 2026-09-08

Phần 0.1–0.3 là baseline lịch sử ngày 2026-09-04 và không được đọc như trạng thái source hiện tại. Repository hiện đã có backend FastAPI, frontend React/Vite, Alembic migrations, Redis worker và object-storage adapter. Các mốc code đã được kiểm local gồm:

| Slice | Thành phần hiện có | Schema/check |
| :--- | :--- | :--- |
| P6 | Artifact, Input Manifest, validation, checksum/signed download | `20260907_0005` |
| P7 | QA protocol seed, Machine QA run/rule/result/rerun/compare, TrendPoint projection | `20260907_0006` |
| P8 | Gamma 2D/3D adapter, RTDOSE GY/scaling, Redis Streams, lease/attempt/outbox, retry/dead-letter/resource guard | `20260907_0007` + `20260908_0008` |
| P9 | Report template/revision/block/export renderer | `20260908_0009` |
| P10 | Trend query/aggregate/export/rebuild, BaselineVersion, MaintenanceEvent/Revisions, source drill-down | `20260908_0010` |
| P11 | QA Protocol Library, rule validation, lifecycle, clone/compare and active-only Machine QA consumer | `20260908_0011` |
| P12 | Biological Hub, independent scenario/revision/history, capability discovery and scoped calculation read model | `20260908_0012` |
| P13 | BED/EQD2 pure engine, calculation snapshot, idempotency, chart dataset and JSON/CSV export | `20260908_0013` |
| P14 | Plan Comparison engine, immutable comparison snapshot, baseline/delta table-chart, clone and JSON/CSV export | `20260908_0014` |
| P15 | Re-irradiation/fraction-compensation scalar engine, recovery/sensitivity, schedule alternatives, immutable snapshot and JSON/CSV export | `20260908_0015` |
| P16 | Organization-scoped Biological Knowledge Library: dose limits, treatment-protocol references, knowledge/alpha-beta entries, validation, import, versioning, explicit-use snapshots and export | `20260908_0016` |
| P17 | RTDOSE/RTSTRUCT physical-dose DVH engine, bounded CT HU/slice/dose/ROI overlay in patient LPS, coverage/metrics, immutable run snapshots, API/UI and JSON/CSV export | `20260908_0017` |
| P4 addendum | Organization member list/toggle and email-bound one-time invitation lifecycle | `20260909_0018` |

Ngày 2026-09-08, P11–P17 đã bổ sung model/API/UI và migrations `20260908_0011`/`20260908_0012`/`20260908_0013`/`20260908_0014`/`20260908_0015`/`20260908_0016`/`20260908_0017`; ngày 2026-09-09 bổ sung P4 membership/invitation và migration `20260909_0018`. P12–P16 giữ Biological như bounded context độc lập, không có FK bắt buộc tới QACase/patient; P17 thuộc QA case và giữ raw DICOM immutable; P4 invitation chỉ lưu token hash và không tạo role hierarchy. Checkpoint local phải ghi đủ full suite, focused phase tests, Ruff/mypy, frontend lint/typecheck/Vitest/build và migration head trên cùng SHA; build warning không được coi là lỗi chức năng nhưng phải theo dõi bundle budget. Đây là implementation evidence, chưa phải staging/production clinical readiness. Staging phải kiểm lại đúng SHA, environment, schema, Auth, object storage, worker và browser workflow trước khi đổi trạng thái phase.

---

## 1. Mục đích và phạm vi

### 1.1. Mục đích

RT-CONNECT là hệ thống web gồm:

1. Khu vực QA Management để lưu trữ, kiểm tra, phân tích, report và theo dõi trend QA xạ trị.
2. Khu vực Biological Toolkit để tính BED/EQD2, so sánh phác đồ, tạo re-irradiation scenario và tra cứu kiến thức điều trị độc lập với QA case và ca bệnh.

### 1.2. Nguyên tắc kỹ thuật bắt buộc

- Business requirement trong business-analysis.md là nguồn yêu cầu chính.
- Không lưu hoặc xử lý file gốc theo cách làm thay đổi nội dung nguồn.
- Dữ liệu dẫn xuất, analysis result, report và scenario phải có lineage về input và phiên bản đã dùng.
- Người dùng trong cùng organization được sử dụng nghiệp vụ ngang nhau.
- Không tạo module phân cấp bác sĩ–kỹ sư hoặc ma trận quyền theo hành động.
- Report Builder cho phép tùy chỉnh toàn diện.
- Biological Toolkit là bounded context riêng, không tự liên kết với QA case hoặc ca bệnh.
- Không tự sửa RT Plan, prescription, TPS hoặc PACS.
- Không tự phát hành clinical order.
- Engine phân tích phải có kết quả xác định được từ input, configuration và engine version.
- Giai đoạn phát triển nghiệm thu bằng test/reference dataset; dataset thật được đưa vào pilot và cải tiến tiếp theo.

### 1.3. Ngoài phạm vi kỹ thuật

- Thay thế TPS, PACS, OIS hoặc bệnh án điện tử.
- Điều khiển trực tiếp máy điều trị.
- Thay đổi treatment plan hoặc prescription.
- Tự động ra quyết định điều trị.
- Tự động cộng liều re-irradiation khi thiếu geometry hoặc registration hợp lệ.
- Tự động đoán format, đơn vị hoặc ý nghĩa cột dữ liệu mơ hồ.

---

## 2. Kiến trúc tổng thể

### 2.1. Mô hình triển khai

Kiến trúc mục tiêu gồm các lớp:

~~~text
[Browser]
    |
    +--> HTTPS --> [Frontend static host]
    |
    +--> HTTPS --> [Railway Public API: Domain + TLS + Edge]
                              |
                              +--> [Supabase Auth]
                              +--> [Railway PostgreSQL]
                              +--> [Object Storage]
                              +--> [Railway Private Redis]
                                      |
                                      v
                              [Railway Worker/Renderer]
                                      |
                                      v
                              [Derived Artifacts]

[Optional DICOM Gateway: Orthanc/DICOMweb]
    |
    v
[Ingestion Service] ---> [Object Storage + Manifest]
~~~

Người dùng truy cập frontend qua HTTPS của static host hoặc frontend do API phục vụ; API public backend chạy qua Railway public networking và HTTPS. Supabase Auth là dịch vụ quản lý danh tính/session, còn Railway PostgreSQL là database mục tiêu; API RT-CONNECT phải tự xác minh token và kết nối database từ backend qua private networking/reference variable, không để browser giữ database credential. Redis, object storage, worker và Orthanc không được mở trực tiếp ra Internet; chúng chỉ nhận kết nối từ các service hoặc mạng riêng đã cấu hình. “Truy cập từ xa” trong tài liệu này nghĩa là truy cập website bằng URL công khai có kiểm soát, không phải mở dữ liệu cho người dùng ẩn danh.

### 2.2. Thành phần chính

| Thành phần | Công nghệ tham chiếu | Trách nhiệm |
| :--- | :--- | :--- |
| Web frontend | React, TypeScript, Vite trên static web host hoặc bundle được backend phục vụ | Giao diện QA, report, trend và Biological Toolkit |
| API/backend server | Python, FastAPI, Pydantic trên Railway | API nghiệp vụ, validation request/response, OpenAPI |
| Identity/Auth | Supabase Auth, `@supabase/supabase-js` | Đăng ký/đăng nhập, session, access token, password recovery và email/OTP theo cấu hình; không lưu password trong RT-CONNECT |
| ORM/migration | SQLAlchemy, Alembic | Truy cập dữ liệu và quản lý schema |
| Database | Railway PostgreSQL service | Metadata, quan hệ nghiệp vụ, cấu hình, provenance và audit |
| Object storage | S3-compatible/MinIO bên ngoài hoặc service được chỉ định | File DICOM, measurement, map, plot, PDF và artifact lớn; không dùng filesystem ephemeral của Railway làm kho chính |
| Job queue | Redis service trên Railway hoặc Redis tương thích | Hàng đợi và trạng thái job; không phải nguồn dữ liệu nghiệp vụ chính |
| Worker | Celery hoặc worker tương đương trên Railway | Phân tích bất đồng bộ, render report, import và export |
| DICOM parser | pydicom, NumPy | Đọc metadata, pixel data và DICOM RT objects |
| Gamma engine | Wrapper engine riêng, PyMedPhys/reference implementation | Tính Gamma và bảo toàn configuration |
| DVH engine | Module tính riêng với NumPy/SciPy/SimpleITK khi cần | Voxelization, interpolation và metric DVH |
| Plot/render | Matplotlib, Pillow, HTML template, Chromium/Playwright | Gamma map, DVH, profile, trend và PDF |
| DICOM gateway | Orthanc/DICOMweb, giai đoạn mở rộng | Nhận/truy vấn DICOM khi bệnh viện cần tích hợp |
| Public web edge | Railway Public Networking; Nginx/Caddy chỉ dùng khi cần edge riêng | Public domain, automatic TLS của Railway, routing và giới hạn request theo topology |
| Observability | Structured logging, metrics và health checks | Theo dõi job, lỗi, hiệu năng và tình trạng dịch vụ |

Phiên bản package phải được khóa trong lockfile và image build. Không dùng giá trị latest trong triển khai.

### 2.3. Môi trường

| Môi trường | Mục đích | Database | Dữ liệu |
| :--- | :--- | :--- | :--- |
| Development | Phát triển tính năng | PostgreSQL/Redis cục bộ hoặc Railway dev environment; Supabase Auth dev project | Fixture/synthetic |
| Test/CI | Chạy unit, integration và golden test | PostgreSQL container hoặc Railway test database; Supabase Auth test project | Test fixture |
| Staging | Kiểm tra deployment và remote access trước production | Railway staging environment + Railway PostgreSQL staging service + Supabase Auth staging project | Synthetic hoặc dataset pilot đã được phê duyệt |
| Pilot | Chạy thử workflow thực tế | Railway pilot environment + Railway PostgreSQL pilot service + Supabase Auth pilot project + Redis | Dataset bệnh viện theo kế hoạch pilot |
| Production | Vận hành thường xuyên | Railway production services + Railway PostgreSQL production service + Supabase Auth production project + Redis được backup | Dữ liệu vận hành |

SQLite chỉ được phép dùng cho demo hoặc development đơn giản. Không dùng SQLite làm database mục tiêu của pilot hoặc production.

Mỗi environment phải có biến cấu hình riêng cho Railway và Supabase; không dùng nhầm Railway PostgreSQL service/connection URL, Supabase Auth project, redirect URL, publishable key hoặc secret giữa dev, staging, pilot và production.

### 2.4. Nguyên tắc tách dịch vụ

- API không thực hiện phép tính Gamma/DVH lớn trên request đồng bộ.
- Worker nhận job có mã định danh và idempotency key.
- File lớn được đọc từ object storage theo stream hoặc vùng cần thiết.
- Worker không ghi đè artifact nguồn.
- Render report không được làm thay đổi analysis result.
- Biological Toolkit có namespace và API riêng, dù được triển khai chung trong giai đoạn đầu.

### 2.5. Thiết kế UX/UI và handoff bằng Google Stitch

Google Stitch là design source truy cập trực tiếp qua MCP, không còn phụ thuộc vào `UI-UX.md` hoặc `DESIGN.md` trong repository. Stitch vẫn chỉ là công cụ design-time/handoff; production frontend không gọi Stitch API và không phụ thuộc MCP để chạy.

#### 2.5.1. Quy trình đọc design trước khi triển khai một module

1. Gọi `list_projects` và xác nhận project ID `14242591911141046021`, title `RT-connect`.
2. Gọi `list_screens` và phân loại application screen với asset/tài liệu hỗ trợ.
3. Gọi `get_screen` cho screen của module để lấy metadata, screenshot và HTML hiện hành.
4. Ghi `stitch_project_id`, `stitch_screen_id`, title và thời điểm đọc design trong issue/PR của module.
5. Lập mapping screen → route → component → API → entity → event → trạng thái.
6. Chỉ sau khi mapping được review mới chuyển HTML/design thành React component.

#### 2.5.2. Quy trình bổ sung screen còn thiếu

Trước khi code frontend của module chưa có screen, dùng MCP để tạo hoặc chỉnh screen trong cùng project `RT-connect`. Tối thiểu còn thiếu các nhóm:

- Login, password recovery và auth callback.
- Organization/site/machine management.
- QA case detail, upload queue, Input Manifest và validation detail.
- Machine QA checklist/editor/result.
- Trend dashboard và drill-down.
- QA Protocol Library và version comparison.
- Report viewer/revision history ngoài Report Builder.
- Dose-limit, treatment protocol và knowledge library.
- Global empty/error/offline/404/maintenance states.
- Responsive variants cho tablet/mobile của các workflow được phát hành.

Mỗi screen mới phải dùng synthetic data và có ít nhất loading, empty, success, warning/invalid, error/retry và disabled/running state phù hợp. Nếu module có job bất đồng bộ, thiết kế phải thể hiện queued/running/succeeded/failed/retry và trạng thái sau khi browser refresh.

#### 2.5.3. Handoff và implementation contract

- Screenshot là visual reference; HTML do Stitch tạo là implementation reference, không phải code production mặc định.
- Không sao chép inline secret, remote tracking script hoặc dependency không được review từ HTML export.
- Chuyển màu, typography, spacing, radius, shadow, chart palette và breakpoint thành design tokens trong source frontend.
- Component chung phải được tách khỏi page-specific markup: AppShell, Sidebar, Header, DataTable, FilterBar, FileUploader, StatusBadge, WarningPanel, JobProgress, ChartCard, RevisionPanel và ReportBlock.
- Event handler phải gọi typed API client; không giữ mock result trong production path.
- Accessibility tối thiểu: keyboard navigation, focus visibility, label/form association, semantic table, chart fallback table, color contrast và trạng thái không chỉ biểu diễn bằng màu.
- Frontend route phải hỗ trợ deep-link/reload và organization context.
- Thay đổi design sau khi module đã implement phải được đánh giá ảnh hưởng tới component, API contract, screenshot test và acceptance test.

#### 2.5.4. Tiêu chí design-to-code hoàn thành

- Screen ID và route mapping tồn tại.
- Component inventory và design tokens được implement trong source, không chỉ mô tả.
- Dữ liệu mock được thay bằng API thật hoặc fixture test có nhãn rõ.
- Loading/empty/error/warning/success được kiểm thử.
- Desktop baseline khớp design; responsive behavior không làm mất chức năng.
- Screenshot/visual regression được lưu trong test artifact của CI hoặc release, không bắt buộc tạo lại `UI-UX.md`.
- Frontend build và runtime hoạt động khi MCP/Stitch không khả dụng.

### 2.6. Route và screen map ban đầu

| Route đề xuất | Screen Stitch | Module | Ghi chú triển khai |
| :--- | :--- | :--- | :--- |
| `/app` | Home Dashboard | MOD-01 | Tổng quan organization, quick action, job và cảnh báo |
| `/app/qa` | Kho lưu trữ QA & Thư mục | MOD-03 | Folder tree, search, case list |
| `/app/qa/cases/:caseId/gamma` | PSQA Gamma Workspace | MOD-04, MOD-06 | Upload/manifest/config/job/result |
| `/app/reports/:reportId/edit` | Report Builder Studio | MOD-07 | Builder, preview, revision và export |
| `/app/biological` | Active implementation trong P12; kế thừa Clinical Precision Interface | MOD-10 | Hub độc lập với QA case |
| `/app/biological/bed-eqd2` | Active Clinical Precision Interface implementation; Stitch generation unavailable at P13 attempt | MOD-11 | Calculator, chart, history, immutable snapshot and export |
| `/app/biological/compare` | Active implementation trong P14; kế thừa Clinical Precision Interface | MOD-12 | Multi-option P13 snapshot comparison |
| `/app/biological/re-irradiation` | Active implementation trong P15; shared ReIrradiationPage | MOD-13 | Multi-course/recovery/scenario |

Các route chưa có Stitch screen được tạo trong phase module tương ứng. Route cuối cùng được khóa trong typed route registry; không hardcode URL rải rác trong component.

### 2.7. Topology Railway theo giai đoạn và giới hạn chi phí

Để không tạo nhiều service trước khi có workload thật, topology được mở rộng theo phase:

| Giai đoạn | Service tối thiểu | Ghi chú |
| :--- | :--- | :--- |
| Foundation/staging | `RT-connect` hoặc `api-web`, `postgres` | API có thể phục vụ frontend build; chưa chạy Gamma đồng bộ trong request |
| Machine QA | API/web + Postgres | Job nhẹ có thể dùng background adapter phát triển nhưng result vẫn persisted |
| PSQA Gamma | Thêm `worker` và `redis` | Analysis chạy bất đồng bộ; API chỉ enqueue và đọc trạng thái |
| Report Builder | Renderer là capability của worker; tách `renderer` khi benchmark yêu cầu | Tránh service riêng nếu chưa có tải đủ lớn |
| Production scale | API/web, Postgres, Redis, worker pool, renderer tùy tải | Quyết định bằng benchmark và queue depth |

Khoản thanh toán hoặc credit Railway không được dùng làm giả định rằng mọi service sẽ luôn nằm trong ngân sách. Trước khi thêm service hoặc tăng resource, phải xem usage/cost hiện tại, benchmark workload và đặt giới hạn/alert phù hợp. Không giảm tính toàn vẹn dữ liệu chỉ để tiết kiệm chi phí; có thể trì hoãn module hoặc scale-to-zero ở môi trường không dùng.

---

## 3. Cấu trúc source code đề xuất

Đặc tả này không khóa tên thư mục tuyệt đối, nhưng source code nên tách theo domain:

~~~text
rt-connect/
├── apps/
│   ├── web/
│   └── api/
├── services/
│   ├── ingestion/
│   ├── analysis/
│   ├── reporting/
│   └── biological/
├── packages/
│   ├── contracts/
│   ├── dicom/
│   ├── gamma/
│   ├── dvh/
│   ├── biological-models/
│   └── rendering/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   ├── fixtures/
│   └── e2e/
├── deployment/
│   ├── web/
│   │   └── README.md
│   ├── railway/
│   │   ├── README.md
│   │   ├── services.md
│   │   └── env.example
│   ├── supabase/
│   │   ├── README.md
│   │   └── env.example
├── docs/
└── pyproject.toml / package manifests
~~~

Nguyên tắc:

- Domain logic không phụ thuộc giao diện.
- Engine tính toán không phụ thuộc database hoặc HTTP.
- API gọi application service.
- Worker gọi cùng application service với API nhưng chạy bất đồng bộ.
- Contract input/output được dùng chung cho backend, frontend và test.
- Không đặt logic tính liều trong component giao diện.

### 3.1. Quy ước deployment files

- `deployment/railway/services.md` mô tả Railway service `api`, `postgres`, `worker`, `renderer` và Redis nếu dùng Railway cho queue.
- `deployment/web/README.md` hoặc tài liệu tương đương mô tả nơi phát hành static frontend nếu frontend không được backend phục vụ.
- `deployment/supabase/README.md` mô tả Supabase Auth project, provider, site/redirect URL và JWT verification; không dùng Supabase làm database nghiệp vụ.
- `deployment/railway/env.example` chỉ chứa tên biến và giá trị mẫu không nhạy cảm.
- Railway reference variables được ưu tiên cho kết nối giữa các service trong cùng project/environment.
- Supabase Auth URL, publishable/anon key, JWKS URL, audience và redirect URL được ghi theo environment; Railway PostgreSQL connection URL/private reference variable và secret chỉ cấu hình trong Railway dashboard hoặc secret store.
- Deployment manifest phải ghi image/commit, migration version, engine version, renderer version và biến cấu hình bắt buộc.
- Không commit Railway PostgreSQL password, Redis password, S3 secret, Supabase service role key hoặc token thật.

### 3.2. Module boundaries dùng chung với plan.md

| Module | Frontend boundary | Backend/domain boundary | Worker/engine |
| :--- | :--- | :--- | :--- |
| MOD-00 Identity | auth routes, session bootstrap, organization selector | token verifier, UserIdentity, OrganizationMembership | Không |
| MOD-01 Dashboard | dashboard route/widgets | dashboard read model/query service | Chỉ aggregate job status |
| MOD-02 Organization/Site/Machine | management pages/forms | organization/site/machine services | Không |
| MOD-03 QA Archive | folder tree, case list/detail shell | Folder, QACase, search service | Không |
| MOD-04 Artifact/Validation | upload, manifest, warning panels | Artifact, ValidationRun, InputManifest | ingestion/validation job |
| MOD-05 Machine QA | checklist/editor/result | protocol application, metric/rule evaluation | Có thể chạy nhẹ, vẫn qua analysis contract |
| MOD-06 PSQA Gamma | Gamma workspace/result | AnalysisRun/GammaConfiguration | GammaEngine worker |
| MOD-07 Report | builder/viewer/revision | report snapshot/template services | renderer/export worker |
| MOD-08 Trend | chart/filter/drill-down | TrendPoint/query/read model | projection/rebuild job khi cần |
| MOD-09 QA Protocol | library/version/rule editor | QAProtocol/Version/Rule/Reference | Không |
| MOD-10 Biological Hub | hub/history/report entry | BiologicalScenario/read model | Không |
| MOD-11 BED/EQD2 | calculator/chart/history | BiologicalCalculationRun | BiologicalEngine |
| MOD-12 Comparison | multi-course editor/chart | course comparison service | BiologicalEngine |
| MOD-13 Re-irradiation | course/scenario/recovery UI | re-irradiation scenario service | BiologicalEngine; spatial worker chỉ phase mở rộng |
| MOD-14 Knowledge | dose-limit/protocol/knowledge pages | versioned knowledge repositories | Import/index job khi cần |
| MOD-15 Dose/DVH | dose viewer/DVH workspace | DICOM linkage/DVH contracts | DVHEngine worker |
| MOD-16 Operations | status/history/diagnostic UI cần thiết | AuditEvent, health, backup manifest | monitoring/maintenance jobs |

Cross-module import phải đi qua public application interface hoặc shared contract; không truy cập trực tiếp table của module khác từ frontend. Biological module không được thêm foreign key bắt buộc tới QA case hoặc patient record.

---

## 4. Mô hình dữ liệu nghiệp vụ

### 4.1. Quy ước chung

- Khóa chính dùng UUID hoặc định danh không đoán được.
- Thời gian lưu ở UTC; giao diện hiển thị theo timezone đã chọn.
- Mỗi entity có created_at và updated_at.
- Entity có version phải có version number, parent revision và created_by.
- File lớn không lưu trực tiếp trong PostgreSQL; chỉ lưu metadata và object key.
- Các cấu hình phân tích lưu dưới dạng JSON có schema version.
- Các metric lưu giá trị số, đơn vị, rule, margin và trạng thái riêng.
- Không có bảng role hierarchy hoặc action permission trong domain model.

### 4.1.1. Identity và organization membership

Supabase Auth là nguồn identity bên ngoài của RT-CONNECT. Database ứng dụng chỉ lưu mapping và membership cần cho nghiệp vụ, không lưu password hoặc secret xác thực của user.

`UserIdentity` tối thiểu gồm:

- `supabase_user_id`: giá trị `sub` trong Supabase access token, unique.
- `email` hoặc email snapshot nếu cần hiển thị.
- `display_name`/profile snapshot nếu cần hiển thị.
- `status` ở mức tài khoản ứng dụng.
- `last_seen_at`.
- `created_at`, `updated_at`.

`OrganizationMembership` tối thiểu gồm:

- `organization_id`.
- `supabase_user_id` hoặc `user_identity_id`.
- `membership_status`.
- `joined_at`, `updated_at`.

Membership chỉ dùng để xác định user thuộc organization nào và áp dụng organization isolation. Không có role hierarchy, không có permission matrix theo hành động và không có nhánh bác sĩ–kỹ sư trong mô hình này. Worker lưu actor snapshot/correlation ID của request tạo job, không giữ user access token lâu dài.

`OrganizationInvitation` là entity P4 bổ sung cho membership onboarding:

| Field | Mapping kỹ thuật | Quy tắc |
| :--- | :--- | :--- |
| `id` | UUID primary key | Không dùng làm secret hoặc token. |
| `organization_id` | FK `organizations.id`, indexed | Mọi truy vấn/repository method phải có organization scope đã resolve. |
| `invited_email` | `VARCHAR(320)`, required | Trim + Unicode case-fold ở request boundary; dùng để so với verified email claim. |
| `token_hash` | `VARCHAR(64)`, unique | SHA-256 hex của token random; raw token chỉ tồn tại trong memory/response create. |
| `status` | `VARCHAR(20)` | `PENDING`, `ACCEPTED`, `REVOKED`, `EXPIRED`; terminal state không mở lại. |
| `expires_at` | timezone-aware UTC | Default 7 ngày, range 1–30 ngày. |
| `accepted_at`, `revoked_at` | nullable UTC | Chỉ set ở transition tương ứng. |
| `created_by_user_identity_id`, `accepted_by_user_identity_id` | nullable FK `user_identities.id` | Provenance actor; không phải role hoặc action permission. |
| `created_at`, `updated_at` | timestamp mixin | Dùng cho audit/history và ordering. |

Migration `20260909_0018_organization_invitations.py` tạo bảng, foreign keys, index lookup/expiry và partial unique index `uq_organization_invitations_pending_email` trên `(organization_id, invited_email)` với điều kiện `status='PENDING'`. Partial index là lớp bảo vệ cuối cùng cho hai request invite đồng thời; service vẫn phải kiểm trước để trả lỗi dễ hiểu.

Luồng accept tạo `UserIdentity` projection nếu subject chưa có, nhưng chỉ khi request có verified identity. Nó không lưu password, access token hoặc raw invitation token. Trước khi tạo membership, service kiểm một active membership ở organization khác; nếu có trả `ORGANIZATION_CONTEXT_ALREADY_ASSIGNED` để giữ session context đơn trị. Accept membership, chuyển invitation sang `ACCEPTED` và `AuditEvent` phải cùng transaction. Retry cùng token và cùng subject sau commit trả membership đã tồn tại; token của subject khác bị từ chối.

Mọi member active đều gọi được các operation P4; backend không được đọc claim `role` để rẽ nhánh. `PATCH membership` chỉ thay `is_active`, bảo vệ last-active invariant và ghi audit. Đây là lifecycle/scope operation, không phải hệ thống cấp quyền.

### 4.2. Organization

Các trường chính:

- id.
- name.
- code.
- description.
- status.
- created_at.
- updated_at.

Quan hệ:

- Một organization có nhiều site.
- Một organization có nhiều member.
- Một organization có folder, QA protocol, report template và knowledge content.

### 4.3. Site

Các trường chính:

- id.
- organization_id.
- name.
- code.
- address_label.
- timezone.
- status.
- created_at.
- updated_at.

Một site thuộc đúng một organization và có nhiều machine.

### 4.4. Machine

Các trường chính:

- id.
- site_id.
- display_name.
- machine_code.
- manufacturer.
- model.
- serial_number nếu có.
- treatment_device_uid nếu có.
- room_name.
- modalities.
- energy_modes.
- lifecycle_note.
- status.
- created_at.
- updated_at.

machine_id phải ổn định. Đổi tên hiển thị không tạo machine mới và không làm tách trend.

### 4.5. Folder

Các trường chính:

- id.
- organization_id.
- parent_folder_id.
- name.
- path materialized hoặc path queryable.
- status: ACTIVE hoặc ARCHIVED.
- created_by.
- created_at.
- updated_at.

Quy tắc:

- Cho phép folder lồng nhau.
- Tên do user đặt.
- Đổi tên hoặc di chuyển không làm thay đổi QA case.
- Folder archive không xóa dữ liệu con.
- Folder không quyết định kết quả phân tích.

### 4.6. QA Case

Các trường chính:

- id.
- organization_id.
- site_id.
- machine_id.
- primary_folder_id.
- qa_type.
- qa_cycle.
- performed_at.
- scheduled_at nếu có.
- title.
- description.
- protocol_version_id nếu có.
- status_note do user ghi nhận nếu cần.
- created_by.
- created_at.
- updated_at.

Một QA case có thể có:

- Nhiều input artifact.
- Nhiều validation run.
- Nhiều analysis run.
- Nhiều report revision.
- Nhiều trend point.

### 4.7. Artifact

Các trường chính:

- id.
- organization_id.
- qa_case_id nullable khi artifact thuộc Biological Toolkit.
- artifact_type: DICOM, MEASUREMENT, CSV, JSON, IMAGE, PDF, OTHER.
- modality nullable.
- original_filename.
- object_key.
- byte_size.
- media_type.
- sha256.
- sop_class_uid nullable.
- sop_instance_uid nullable.
- study_instance_uid nullable.
- series_instance_uid nullable.
- frame_of_reference_uid nullable.
- source_system.
- uploaded_by.
- uploaded_at.
- data_status: UPLOADED, VALIDATING, VALID, WARNING, INVALID, ARCHIVED.
- parent_artifact_id nullable.
- metadata_snapshot.
- created_at.

Artifact gốc không bị sửa. Artifact dẫn xuất phải tham chiếu parent_artifact_id.

### 4.8. Input Manifest

Các trường chính:

- id.
- analysis_run_id.
- artifact_id.
- logical_role: REFERENCE, EVALUATION, CT, RTSTRUCT, RTPLAN, MEASUREMENT, OTHER.
- checksum_at_use.
- selected_metadata.
- geometry_summary.
- unit_summary.
- validation_summary.

Input Manifest là bản ghi chính xác dữ liệu đã được dùng trong một analysis run.

### 4.9. Validation Run

Các trường chính:

- id.
- subject_type.
- subject_id.
- validation_type.
- validator_version.
- started_at.
- completed_at.
- result: VALID, WARNING hoặc INVALID.
- checks.
- warnings.
- errors.
- input_manifest_snapshot.

Validation run không thay đổi file gốc.

### 4.10. QA Protocol

Các entity:

- QAProtocol.
- QAProtocolVersion.
- QAProtocolRule.
- QAProtocolReference.

QAProtocolVersion phải chứa:

- Tên protocol.
- Loại QA.
- Machine scope.
- Tần suất.
- Test items.
- Metric keys.
- Tolerance.
- Action level.
- Unit.
- Rule expression.
- Reference/source.
- Effective note.
- Changelog.

Một report cũ tham chiếu đúng QAProtocolVersion đã dùng.

#### 4.10.1. P11 implementation contract

P11 hiện thực protocol theo `QAProtocolVersion` trong một organization; `protocol_key` là
stable family key còn `version_number` là số tăng dần trong family. Version có các trạng thái:

- `DRAFT`: mutable, dùng để nhập và validate; không được consumer coi là protocol đang áp dụng.
- `ACTIVE`: immutable và được chọn cho run mới.
- `ARCHIVED`: immutable, không được chọn cho run mới nhưng vẫn đọc được trong history.

Các trường P11 đã có trong model là `description`, `applicability`, `source_type`,
`source_reference`, `source_protocol_version_id` và `revision`; `QAProtocolRule` có thêm
`reference`. Applicability chỉ nhận các dimension được công bố (site, machine, cycle, QA type,
energy, beam quality, technique, detector, phantom), mỗi dimension là string list explicit.
Source type gồm `USER_DEFINED`, `REFERENCE`, `INTERNAL`, `SITE_APPROVED`; `REFERENCE` phải có
source reference. Rule types gồm `RANGE`, `MIN`, `MAX`, `ABSOLUTE_DEVIATION`,
`PERCENT_DEVIATION` và `NA`. Backend kiểm finite numeric, duplicate key, unit/type,
min/max, target/tolerance/action ordering và reference trước khi commit.

Migration `20260908_0011_protocol_library.py` thêm các field/index/self-reference lineage.
Create/update/clone/transition ghi header, child rule và audit trong một transaction; PATCH và
transition dùng `expected_revision`. Clone deep-copy child rule và ghi source version. Các
consumer mới phải pin `protocol_version_id` và snapshot rule/limit/source; không resolve lại
version live khi mở run/report/trend cũ.

API implementation P11 (base prefix `/api/v1`):

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| POST | `/organizations/{id}/qa-protocols/validate` | Validate-only, không mutation |
| GET/POST | `/organizations/{id}/qa-protocols` | List hoặc tạo version |
| GET/PATCH | `/organizations/{id}/qa-protocols/{protocol_id}` | Detail hoặc sửa DRAFT với revision |
| POST | `/organizations/{id}/qa-protocols/{protocol_id}/clone` | Clone version, deep-copy rules |
| POST | `/organizations/{id}/qa-protocols/{protocol_id}/activate` | DRAFT thành ACTIVE |
| POST | `/organizations/{id}/qa-protocols/{protocol_id}/archive` | Chuyển ARCHIVED |
| GET | `/organizations/{id}/qa-protocols/{protocol_id}/compare?other_id=...` | So sánh metadata/rule |

`GET /organizations/{id}/machine-qa/protocols` chỉ trả version `ACTIVE` cho run mới; detail
protocol vẫn có thể trả version archived nếu caller thuộc đúng organization. Các mã lỗi chính
được định nghĩa trong `specification.md` SPEC-P11.2. P11 local code/test không tự chứng minh
staging consumer E2E hay clinical readiness; các bằng chứng đó thuộc plan P11/P18/P19.

### 4.11. Analysis Configuration

Các trường chính:

- id.
- analysis_type.
- schema_version.
- configuration_json.
- protocol_version_id nullable.
- created_by.
- created_at.
- label.

Cấu hình không bị thay đổi sau khi được dùng; chỉnh sửa tạo configuration mới.

### 4.12. Analysis Run

Các trường chính:

- id.
- organization_id.
- qa_case_id nullable.
- analysis_type.
- configuration_id.
- engine_name.
- engine_version.
- job_id.
- input_manifest_id.
- started_at.
- completed_at.
- execution_status: QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELED.
- result_status: PASS, FAIL, REVIEW_REQUIRED, INVALID_INPUT, NOT_APPLICABLE nếu có.
- result_artifact_id nullable.
- summary_json.
- error_json.
- warnings_json.
- created_by.

Analysis Run là bất biến sau khi hoàn tất về mặt nội dung; chạy lại tạo run mới.

### 4.13. Metric Result

Các trường chính:

- id.
- analysis_run_id.
- metric_key.
- display_label_snapshot.
- value_numeric nullable.
- value_text nullable.
- unit.
- limit_value nullable.
- action_value nullable.
- margin nullable.
- status.
- rule_snapshot.
- explanation.
- source_pointer.
- created_at.

Metric phải giữ label và rule snapshot để report cũ không thay đổi khi protocol mới được cập nhật.

### 4.14. Warning

Các trường chính:

- id.
- analysis_run_id.
- code.
- severity: INFO, WARNING, ERROR.
- message.
- evidence.
- source_pointer.
- blocking_for_calculation boolean.
- created_at.

Warning không bị xóa khi user chạy lại analysis.

### 4.15. Report Template và Report Revision

Các entity:

- ReportTemplate.
- ReportTemplateVersion.
- Report.
- ReportRevision.
- ReportBlockConfig.
- ReportArtifact.

ReportBlockConfig gồm:

- block_type.
- block_key.
- title.
- visible.
- order_index.
- selected_metric_keys.
- conditional_expression nếu có.
- layout_config.
- display_options.

Report revision phải lưu snapshot của:

- Input Manifest.
- Analysis Run.
- Protocol version.
- Analysis Configuration.
- Report Template Version.
- Block configuration.
- Render options.
- User note.
- Rendered artifacts.

Report Builder không áp đặt block bắt buộc; user toàn quyền tùy chỉnh nội dung hiển thị.

### 4.16. Trend Point

Các trường chính của projection đang triển khai:

- id.
- organization_id.
- machine_id.
- qa_case_id.
- source_run_id (`MachineQARun`).
- metric_key.
- value.
- unit.
- status.
- measured_at.
- context_snapshot: qa_type, qa_cycle, protocol key/version và context đo (energy, detector, phantom, beam quality, acquisition mode).
- created_at.

Unique key của projection là `organization_id + source_run_id + metric_key`; index phục vụ organization/machine/metric và organization/measured_at. Trend point không được tự động xóa khi có outlier, machine/case archive hoặc rebuild. Baseline không nằm trong point: `BaselineVersion` được chọn theo effective interval và context khi query. `MaintenanceEvent` là marker hiện tại, còn `MaintenanceEventRevision` là lịch sử append-only. Chi tiết field/API/error nằm trong `specification.md` SPEC-P10.

### 4.17. Biological Toolkit entities

Các entity chính:

- BiologicalScenario.
- BiologicalCourse.
- BiologicalCalculationRun.
- BiologicalMetric.
- BiologicalChart.
- DoseLimitEntry.
- TreatmentProtocolReference.
- KnowledgeEntry.
- AlphaBetaEntry.
- BiologicalReport.

Các entity này không có qa_case_id mặc định. Nếu user xuất kết quả, tạo BiologicalReport độc lập.

### 4.17.1. P12 implementation contract

Slice P12 hiện thực ba bảng nền tảng trong namespace nghiệp vụ riêng:

- `biological_scenarios`: organization-scoped stable key, tên/loại/context, source/reference, finite assumptions, trạng thái `DRAFT|SAVED|ARCHIVED`, revision và lineage tới source scenario revision khi clone.
- `biological_scenario_revisions`: snapshot append-only của từng revision, unique theo scenario + revision number; dùng để mở lại đúng input đã lưu.
- `biological_calculation_runs`: model/version, input/result/warning/error snapshot và liên kết scenario revision; P12 cung cấp read contract, P13 tạo calculation BED/EQD2 bất biến, P14 đọc các snapshot này để so sánh. P15 dùng namespace `biological_reirradiation_runs` riêng cho re-irradiation/fraction compensation để không trộn semantics với một calculation BED/EQD2 đơn.

Tất cả query đầu tiên đều kèm `organization_id` sau khi resolve membership. Mutation create/update/save/clone/archive ghi header, snapshot và audit trong một transaction. `PATCH` bắt `expected_revision`; chỉ DRAFT sửa trực tiếp; clone tạo ID/key mới và không sửa nguồn. `validate` là validate-only. `ARCHIVED` bị loại khỏi list mặc định nhưng history/detail vẫn đọc được.

API implementation prefix là `/api/v1/organizations/{organization_id}/biological` với các nhóm `/tools`, `/summary`, `/scenarios`, `/scenarios/{id}/revisions`, `/calculations`, `/comparisons`, `/re-irradiation`, `/fraction-compensation` và `/library`. P13–P16 đã có engine/API/UI contract và test local; P16 library không tạo calculation giả và chỉ trả explicit-use snapshot khi user chủ động yêu cầu. P17 thuộc QA case với prefix `/api/v1/organizations/{organization_id}/qa-cases/{case_id}/dvh`; P17 local slice không đọc trực tiếp bảng Biological. Staging/release availability vẫn phải kiểm theo evidence tương ứng.

### 4.17.2. P13 BED/EQD2 implementation contract

P13 dùng engine thuần `services/bed_eqd2_engine.py`, không phụ thuộc database, HTTP hoặc patient data. API route được đăng ký tại `/api/v1/organizations/{organization_id}/biological` và UI route tại `/app/biological/bed-eqd2`.

- **Schema/migration:** `biological_calculation_runs.idempotency_key` nullable cho các row read-model P12 cũ, unique theo `(organization_id, idempotency_key)` cho calculation P13; migration `20260908_0013_bed_eqd2_calculations.py`.
- **Engine identity:** key `biological.bed-eqd2`; version `p13-lq-1.0.0`. Engine chuẩn hóa D/n/d, kiểm finite/nonnegative/positive/integer, tolerance, source và point budget; không làm tròn trước phép tính.
- **Primary result:** LQ BED/EQD2 với D [Gy], n [fraction], d [Gy/fraction], alpha/beta [Gy]. Kết quả JSON chứa formula, fractionation normalized, alpha/beta provenance, primary, table rows và chart dataset canonical có SHA-256.
- **Curve modes:** `FIXED_N` giữ số fraction và tạo d=D/n; `FIXED_D` giữ d và chỉ tạo D=n×d với n nguyên. Point limit tính trên toàn bộ alpha/beta series; range/step không hợp lệ chặn toàn bộ operation.
- **API operations:** validate-only không mutation; create calculation commit + audit; replay idempotent trả snapshot đã lưu; chart preview chỉ đọc/rebuild từ input snapshot với `persisted=false`; JSON/CSV export đọc result snapshot. Mọi route resolve membership trước rồi mới query resource bằng organization scope.
- **Failure boundary:** input/domain errors trả `valid=false` ở validate hoặc error envelope 422; idempotency conflict 409; scenario/revision/calculation scope lỗi 403/404/409; persistence lỗi 503. Không tạo calculation COMPLETED một phần và không liên kết mặc định với QA/patient/TPS/PACS.
- **Evidence local:** engine/API focused tests, full backend, Ruff/mypy, frontend lint/typecheck/Vitest/build và Alembic head `20260908_0013` đã pass trên candidate. Staging browser/API/PostgreSQL/checksum/export evidence vẫn là gate tiếp theo và được ghi trong `implementation-progress.md`.

### 4.17.3. P14 Plan Comparison implementation contract

P14 là bounded context đọc các P13 `BiologicalCalculationRun` đã `COMPLETED`. P14 không đọc raw browser form sau khi đã resolve request, không nhận treatment/patient record ngầm và không thay đổi source calculation. Engine thuần nằm tại `services/plan_comparison_engine.py`; API adapter chịu trách nhiệm organization scope, snapshot lookup, persistence và export; UI route nằm tại `/app/biological/compare`.

- **Schema/migration:** migration `20260908_0014_plan_comparison.py` tạo `biological_comparison_runs`, có UUID/organization/scenario/revision foreign keys, unique `(organization_id, idempotency_key)`, status, input/result/warning/error snapshots, actor và timestamps; index theo organization/scenario và organization/status. Không có FK bắt buộc tới QA case/patient.
- **Source resolution:** request chỉ gửi `calculation_id`; API thực hiện lookup ban đầu với `organization_id`, yêu cầu `calculation_type=BED_EQD2` và `status=COMPLETED`, lấy scenario cùng scope rồi copy D/n/d, alpha/beta/source, tissue, model key/version và primary BED/EQD2 vào immutable option snapshot. Calculation ID bị trùng giữa hai option là invalid.
- **Engine identity:** key `biological.plan-comparison`; version `p14-comparison-1.0.0`. Engine nhận 2–10 `ComparisonOption`, kiểm stable option ID/label, numeric finite/nonnegative, positive integer fractions, model/context/provenance, baseline và unique calculation IDs.
- **Compatibility:** mọi option phải cùng `scenario_id`, `scenario_revision_id`, `tissue_context`, `model_key`, `model_version`. Alpha/beta khác nhau tạo warning `COMPARISON_ALPHA_BETA_MISMATCH`, giữ kết quả riêng và đặt `ranking_allowed=false`; P14 không auto-rank.
- **Delta/chart:** baseline được resolve theo option ID; `delta=value-baseline`, `percent=delta/baseline*100`; baseline zero trả percent `null` và reason `BASELINE_ZERO`. `table_rows` và chart categories được tạo từ cùng result; chart dataset có SHA-256 canonical. Reorder preview tính lại presentation order với `persisted=false`, không mutation.
- **API operations:** `POST /comparisons/validate` validate-only; `POST /comparisons` create/replay idempotent; `GET /comparisons` list; `GET /comparisons/{id}` detail; `POST /comparisons/{id}/charts` reorder preview; `POST /comparisons/{id}/clone` clone snapshot; `GET /comparisons/{id}/export?export_format=JSON|CSV` export result snapshot.
- **Transaction/error boundary:** create/clone thêm comparison và audit trong một transaction; same key + same fingerprint trả row cũ, same key + khác fingerprint trả `409 COMPARISON_IDEMPOTENCY_CONFLICT`; validation `422`, scope `403`, missing `404`, persistence `503`. Validate/preview không ghi database. Error response dùng shared flat envelope và correlation ID.
- **Frontend behavior:** nếu không có hai P13 snapshot `COMPLETED`, hiển thị empty state; form chỉ chọn source snapshot có thật; warning/error/zero-percent có text và reason; history sau refresh đọc lại từ API; export/clone chỉ thực hiện từ persisted comparison. Không coi HTTP 200 là tính toán thành công nếu schema parse thất bại.
- **Evidence:** migration `0014`, full backend suite, focused P14 engine/API/biological tests, Ruff, strict mypy, frontend lint/typecheck/Vitest/build và OpenAPI check đã pass trên candidate. Staging browser/API smoke trên candidate `31a5900` cũng đã pass validate-only, save, reorder preview, clone, JSON/CSV export và refresh readback; direct PostgreSQL row/checksum, organization-scope negative probe và release manifest vẫn là gate kế tiếp. Đây chưa phải tuyên bố clinical readiness.

### 4.17.4. P15 Re-irradiation và Fraction Compensation implementation contract

P15 là hai operation synchronous trong Biological bounded context. Engine thuần không import FastAPI/SQLAlchemy/Auth/QA data; API adapter chịu trách nhiệm resolve organization membership, saved scenario revision, idempotency và persistence. UI chỉ gửi input đã nhập, hiển thị field error/warning và đọc immutable snapshot.

#### Engine và dữ liệu chuẩn hóa

- `services/re_irradiation_engine.py` công bố hai engine identity: `biological.re-irradiation / p15-lq-reirradiation-1.0.0` và `biological.fraction-compensation / p15-lq-compensation-1.0.0`.
- Re-irradiation parser chuẩn hóa lịch uniform từ D/n/d hoặc giữ nguyên `fraction_doses_gy[]` nếu nonuniform. Mọi số được kiểm finite; dose không âm; alpha/beta dương; fraction count nguyên trong giới hạn. `BED` được tính theo từng fraction, `EQD2` tính từ BED chưa làm tròn.
- Course phải có ID duy nhất, explicit prior/current role và tissue rows độc lập. Engine từ chối scenario không có đủ một prior và một current. Cùng tissue với alpha/beta khác nhau được group bằng `tissue_key|alpha-beta={value} Gy` và trả warning thay vì cộng khác context.
- Recovery là scalar user-defined. `NONE` không giảm BED; `USER_DEFINED` yêu cầu evaluation date và source cho từng prior course, áp dụng `(1-recovery_fraction)` đúng một lần. Sensitivity chỉ là bảng giả định, không phải uncertainty interval.
- Fraction compensation kiểm `delivered_fraction_doses_gy[]` là prefix khớp `planned_fraction_doses_gy[]` trong tolerance. Alternative được ghép từ prefix + remaining; output chứa prefix unchanged, total/BED/EQD2 và delta so với planned. Interruption được parse thành interval không overlap. `USER_DEFINED_LINEAR` tính penalty BED theo rate sau kickoff và luôn lưu source; không có model thì warning `NO_REPOPULATION_CORRECTION`.
- `spatial.requested=true` chỉ tạo capability/warning `SPATIAL_ACCUMULATION_UNAVAILABLE`; không đọc DICOM, không resample, không đăng ký geometry và không tạo voxel result trong P15.

#### Model và migration

Migration `20260908_0015_reirradiation.py` tạo `biological_reirradiation_runs` với:

| Cột/constraint | Mục đích |
| :--- | :--- |
| `id`, `organization_id`, `scenario_id`, `scenario_revision_id` | Identity và tenant/scenario lineage; foreign key tới resource hiện hữu. |
| `operation_type` | `REIRRADIATION` hoặc `FRACTION_COMPENSATION`; list/detail luôn lọc operation. |
| `name`, `idempotency_key` | Tên hiển thị và retry identity; unique theo `(organization_id, idempotency_key)`. |
| `model_key`, `model_version`, `status` | Provenance engine và terminal state; hiện calculation synchronous `COMPLETED`. |
| `input_snapshot`, `result_snapshot`, `warning_snapshot`, `error_snapshot` | Snapshot JSON immutable, đủ để export/reproduce; không trỏ live form. |
| `created_by_user_identity_id`, timestamps | Actor/audit lineage và thời gian. |

Indexes gồm organization, scenario, scenario revision, organization+operation, organization+status và actor. Không có FK tới QA case/patient/TPS/PACS; calculation P15 là namespace Biological độc lập.

#### API transaction và error mapping

API prefix là `/api/v1/organizations/{organization_id}/biological`. Mọi read đầu tiên resolve identity/membership rồi mới query với `organization_id`; detail/list của organization khác trả scope-safe error. Validate-only không commit. Create tính trước, tạo run + audit rồi commit; `IntegrityError` sau concurrent insert chỉ trả existing nếu fingerprint trùng, ngược lại `P15_IDEMPOTENCY_CONFLICT`.

| Tình huống | Mapping |
| :--- | :--- |
| Pydantic extra field, type, UUID, finite/range | HTTP `422`, shared error envelope; không tạo run. |
| Engine input error | Validate route HTTP `200` + `valid=false`; create route HTTP `422` + code/field details. |
| Missing/archived/unsaved scenario revision | `404` resource hoặc `409` lifecycle; không chạy engine. |
| Organization mismatch | `403`, query không lấy resource ngoài scope. |
| Same key/same fingerprint | `200` replay row cũ, không insert row thứ hai. |
| Same key/different fingerprint | `409 P15_IDEMPOTENCY_CONFLICT`. |
| DB/transaction failure | `503 REIRRADIATION_PERSISTENCE_FAILED`; rollback và query key trước retry. |
| Export | JSON/CSV đọc snapshot; không tính lại, không mutation; run thiếu trả `404`. |

#### Frontend route và trạng thái

`/app/biological/re-irradiation` và `/app/biological/fraction-compensation` dùng cùng `ReIrradiationPage` nhưng hai form mode. UI có scenario/revision selector chỉ lấy `SAVED`, course×tissue matrix, recovery/sensitivity, planned/delivered prefix, alternatives, interruptions, optional time model, validate-only, save, history và JSON/CSV export. Các trạng thái bắt buộc là loading, no saved scenario, validation error, warning, persisted result, export error và API/session error. Kết quả luôn có model/version/checksum và nhãn `SCENARIO / ESTIMATE ONLY`.

#### Local verification checkpoint

Working-tree candidate đã kiểm: P15 API tests `5/5`, pure engine/error tests `22/22`, full backend `133 passed`, Ruff, strict mypy, frontend lint/typecheck/build, OpenAPI regenerate/check và Alembic PostgreSQL head `20260908_0015`. Đây chỉ là local implementation evidence; staging deploy, authenticated browser smoke, direct PostgreSQL row/checksum/scope query và release manifest vẫn là gate riêng.

### 4.17.5. P16 Biological Knowledge Library implementation contract

P16 là một bounded context thư viện tham khảo trong Biological Toolkit. Một bảng versioned duy nhất được dùng cho bốn loại entry để giữ chung search, provenance và lifecycle; các màn hình dose limit, treatment protocol, knowledge note và alpha/beta là các view/entry type của cùng namespace, không phải bốn nguồn dữ liệu không liên quan.

#### Thành phần triển khai

- **Engine thuần:** `services/biological_library_engine.py` thực hiện canonicalization, validation field/cross-field, applicability matching, search text, snapshot và fingerprint. Engine không truy cập database, Auth, URL external hoặc patient data.
- **API adapter:** `api/biological_library.py` dùng prefix `/api/v1/organizations/{organization_id}/biological/library`; route resolve membership trước mọi query, ghi audit cho mutation và rollback khi persistence thất bại.
- **Entity/migration:** `BiologicalLibraryEntry` và migration `20260908_0016_biological_library.py`; unique family/version `(organization_id, entry_type, entry_key, version_number)`, `source_entry_id` cho clone, revision optimistic, content/citation/applicability JSON và hash.
- **Frontend:** `KnowledgeLibraryPage` tại `/app/biological/knowledge`, dùng AppShell/Clinical Precision Interface hiện có; có list/filter, editor, validation, import, history/compare, explicit-use và JSON/CSV export.

#### Schema và validation

`entry_type` nhận `DOSE_LIMIT`, `TREATMENT_PROTOCOL`, `KNOWLEDGE`, `ALPHA_BETA`; `source_type` nhận `USER_DEFINED`, `REFERENCE`, `INTERNAL`, `SITE_APPROVED`; `reference_status` nhận `UNVERIFIED`, `AVAILABLE`, `UNAVAILABLE`. Key được uppercase canonical; mọi số phải finite và mọi JSON phải là object hữu hạn.

- `DOSE_LIMIT` bắt buộc metric/unit/operator. `MAX|MIN|TARGET` dùng `limit_value`; `RANGE` dùng lower/upper và lower ≤ upper. DMAX/DMEAN/Dxcc dùng dose-like unit; Dxcc bắt buộc volume dương; Vx bắt buộc metric parameter dương và `%|cc|cm3`.
- `ALPHA_BETA` yêu cầu alpha/beta dương, chuẩn hóa unit `Gy`, có thể dùng `limit_value` làm alias; thiếu tissue/OAR chỉ tạo warning `DOSE_LIMIT_NOT_APPLICABLE`, không auto-apply.
- Direct context được sao chép vào applicability arrays. Search disease/anatomy/technique/tissue/metric/fractions là exact case-insensitive match; context thiếu không phải wildcard.
- `REFERENCE` không có source identifier là lỗi `KNOWLEDGE_SOURCE_REQUIRED`. Link external chỉ là metadata; service không tự fetch/private URL và `UNVERIFIED` không thành `AVAILABLE` bằng việc lưu URL.
- Content/citation không được chứa script/iframe/object/embed/style, event attribute, `javascript:` hoặc `data:text/html`; formula text không được chạy như code.

#### API operation và transaction

| Operation | Hành vi kỹ thuật |
| :--- | :--- |
| `POST /validate` | Validate-only; trả normalized entry/fingerprint/errors/warnings, không insert. |
| `GET /` | Organization-scoped list; filter q/type/status/context/fractions, mặc định loại ARCHIVED, offset/limit tối đa 500. |
| `POST /` | Validate lại server-side, tạo DRAFT hoặc PUBLISHED theo request, assign next family version và audit trong transaction. |
| `PATCH /{id}` | Chỉ DRAFT; bắt `expected_revision`; cập nhật normalized fields, revision và hash atomically. |
| `POST /{id}/clone` | Copy definition thành family version mới, lưu `source_entry_id`; key/name override phải validate lại. |
| `POST /{id}/publish` / `archive` | Optimistic revision; publish validate đầy đủ; archive giữ read/history/export nhưng loại khỏi list/use mặc định. |
| `GET /{id}/revisions` / `compare` | Read-only family history và field-level metadata/content diff; không sửa entry. |
| `POST /{id}/use` | Tạo response snapshot với target tool, source snapshot, effective values, override label và SHA; không ghi trực tiếp vào calculator/QA. |
| `POST /import/validate` / `POST /import` | Preview/commit 1–500 rows; duplicate family trong batch là row error; commit row hợp lệ và audit, rollback nếu DB lỗi. |
| `GET /{id}/export` | JSON/CSV serialize đúng row đã chọn; không tự resolve latest version và không tính lại. |

Explicit-use override whitelist chỉ gồm `limit_value`, `lower_limit`, `upper_limit`, `unit`, `alpha_beta_gy`, `fractions`, `metric_parameter`. Entry ARCHIVED bị chặn; DRAFT được preview nhưng trả warning `KNOWLEDGE_DRAFT_SELECTED`. Target không phù hợp tạo warning, không tạo rule/PASS.

#### Error, observability và capability boundary

`REQUEST_VALIDATION_FAILED`/field schema là 422; engine validation trên validate-only là 200 với `valid=false`, còn mutation là 422; source/unit/content/applicability dùng các mã `KNOWLEDGE_SOURCE_REQUIRED`, `DOSE_LIMIT_UNIT_INVALID`, `DOSE_LIMIT_NOT_APPLICABLE`, `KNOWLEDGE_CONTENT_INVALID`; import dùng `KNOWLEDGE_IMPORT_INVALID`; reference warning là `REFERENCE_NOT_VERIFIED`/`REFERENCE_LINK_UNAVAILABLE`; revision/lifecycle dùng `KNOWLEDGE_REVISION_CONFLICT`, `KNOWLEDGE_VERSION_IMMUTABLE`, `KNOWLEDGE_NOT_AVAILABLE`; scope/not-found dùng shared `ORGANIZATION_SCOPE_MISMATCH`/`KNOWLEDGE_ENTRY_NOT_FOUND`; DB/unique failure dùng `KNOWLEDGE_VERSION_CONFLICT`/`KNOWLEDGE_PERSISTENCE_FAILED` với 409/503.

Every mutation audit payload tối thiểu có organization, actor, entry ID, type/key/version/status và source lineage. Log không ghi content nhạy cảm hoặc token. Snapshot use/export phải có schema version, source version/hash và correlation ID trong response envelope. P16 chỉ cung cấp reference snapshot; P13/P14/P15/P17 phải có adapter riêng nếu muốn prefill, không được đọc trực tiếp bảng P16. P17 hiện có adapter riêng cho explicit source binding; P13/P14/P15 vẫn chưa được coi là đã prefill chỉ vì P16 snapshot tồn tại.

#### Local verification checkpoint

Candidate commit `7377aad` đã pass P16 focused tests `3/3`, P17 DVH/CT engine/API/report-source/binding suite `27 passed`, P18 integrated journey suite `2 passed`, full backend `169 passed`, Ruff, strict mypy, frontend lint/typecheck/Vitest/build. Migration/OpenAPI đã được regenerate/check trên cùng SHA; staging readiness `20260909_0018` là schema head hiện hành (P17 migration `20260908_0017` đã nằm trong lịch sử), browser lifecycle, import/use/export, explicit binding/report source, direct PostgreSQL row/hash/scope và full negative matrix vẫn là gate trước STAGING_VERIFIED.

### 4.18. Audit Event

Các trường chính:

- id.
- organization_id.
- actor_user_id.
- event_type.
- subject_type.
- subject_id.
- occurred_at.
- before_snapshot nullable.
- after_snapshot nullable.
- reason nullable.
- request_id.
- source: UI, API, WORKER, IMPORT, EXPORT.
- metadata.

Audit Event append-only. Không dùng audit event để tạo phân cấp người dùng.

---

## 5. Luồng kỹ thuật chính

### 5.1. Luồng tạo QA case và upload

~~~text
User tạo QA case
    -> chọn organization/site/machine/folder/QA type
    -> upload file
    -> object storage nhận file
    -> tạo Artifact metadata + checksum
    -> tạo Input Manifest sơ bộ
    -> chạy validation job
    -> cập nhật data_status
    -> user xem lỗi/cảnh báo
    -> user chọn configuration
    -> tạo Analysis Run
~~~

### 5.2. Luồng phân tích bất đồng bộ

~~~text
POST analysis request
    -> kiểm tra request schema
    -> tạo Analysis Run QUEUED
    -> enqueue job vào Redis
    -> worker lấy job
    -> đọc immutable input
    -> validate lại tại thời điểm chạy
    -> normalize input
    -> execute engine
    -> lưu result + metrics + warnings
    -> cập nhật trend nếu đủ điều kiện
    -> report đọc snapshot của run
~~~

Nếu worker lỗi:

- Job được retry theo policy.
- Không tạo kết quả một phần được coi là hợp lệ.
- Log có correlation ID.
- User xem được lỗi kỹ thuật và có thể chạy lại bằng run mới.

### 5.3. Luồng report

~~~text
User chọn analysis run
    -> chọn report template version
    -> chỉnh ReportBlockConfig tùy ý
    -> tạo Report Revision
    -> renderer đọc snapshot
    -> tạo HTML/PDF/PNG
    -> lưu Report Artifact
    -> report viewer hiển thị nội dung và provenance
~~~

### 5.4. Luồng Biological Toolkit

~~~text
User mở Biological Toolkit
    -> tạo scenario độc lập
    -> nhập course/alpha-beta/assumption
    -> validate input
    -> chạy calculation
    -> lưu Biological Calculation Run
    -> hiển thị bảng/đồ thị
    -> export Biological Report độc lập
~~~

Không có bước tự động tìm hoặc gắn QA case/ca bệnh.

---

## 6. API kỹ thuật

### 6.1. Quy ước API

- Base path: /api/v1.
- JSON UTF-8.
- Thời gian dùng ISO 8601 UTC.
- API trả request_id hoặc correlation_id.
- Job bất đồng bộ trả analysis_run_id và job status.
- Pagination dùng limit, cursor hoặc page token.
- File upload hỗ trợ upload multipart và signed object upload khi cần.
- API schema được công bố bằng OpenAPI.
- Mọi request có organization context hợp lệ.

### 6.1.1. Authentication bằng Supabase Auth

- Frontend dùng `@supabase/supabase-js` để đăng nhập, duy trì session, refresh token, logout và password recovery theo cấu hình Supabase project.
- Frontend chỉ được chứa Supabase Auth project URL và publishable/anon key phù hợp; không đưa `service_role` key, Railway PostgreSQL credential hoặc secret Railway vào bundle.
- Request tới RT-CONNECT API gửi `Authorization: Bearer <Supabase access token>`.
- API middleware kiểm tra chữ ký, `iss`, `aud`, `exp`, `nbf` nếu có, `sub` và token type bằng thư viện JWT chuẩn hoặc cơ chế xác minh được Supabase khuyến nghị.
- Khi dùng asymmetric signing keys, API lấy public keys từ JWKS endpoint của đúng Supabase project và cache có thời hạn; phải xử lý key rotation. Khi cấu hình signing key yêu cầu introspection, API dùng endpoint xác minh phù hợp thay vì tự đoán.
- `sub` được map tới `UserIdentity`; sau đó API kiểm tra `OrganizationMembership` trước khi truy cập mọi record có `organization_id`.
- Không dùng claim `role` để tạo phân cấp bác sĩ–kỹ sư hoặc action permission. Claim/membership chỉ phục vụ identity và organization isolation theo phạm vi nghiệp vụ đã thống nhất.
- Job bất đồng bộ lưu `created_by`, `supabase_user_id` snapshot và correlation ID; worker không dùng lại access token của user để chạy về sau.
- Token hết hạn, user bị logout/revoke hoặc Supabase Auth không khả dụng phải trả error contract rõ ràng; không fallback sang user giả hoặc anonymous access cho dữ liệu QA.
- Redirect URL, site URL, email template/provider và provider được phép phải tách theo dev, staging, pilot và production.
- Test phải bao gồm token hợp lệ, hết hạn, sai issuer/audience, sai signature, user không thuộc organization và membership bị vô hiệu hóa.

#### 6.1.1. First-use organization onboarding

- `GET /session/bootstrap` chỉ trả context khi identity đã có `UserIdentity`, membership active và organization chưa archive.
- Nếu identity hợp lệ nhưng chưa có membership, API trả error contract `ORGANIZATION_MEMBERSHIP_REQUIRED` với HTTP 403; không trả organization giả hoặc dữ liệu synthetic trong production path.
- Frontend hiển thị Session Error onboarding form để người dùng nhập tên organization.
- `POST /organizations` tạo organization, tạo hoặc cập nhật `UserIdentity`, tạo `OrganizationMembership` active cho identity hiện tại và ghi audit event trong cùng transaction.
- Identity đã có membership active bị từ chối với `ORGANIZATION_CONTEXT_ALREADY_ASSIGNED`; không tự động tạo organization thứ hai.
- Sau khi tạo thành công, frontend loại cache bootstrap lỗi, gọi lại bootstrap và mở Home Dashboard.
- Membership là organization scope; không có role hierarchy hoặc action-level permission giữa các thành viên trong organization.

### 6.1.2. Session bootstrap và Home Dashboard

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| GET | `/session/bootstrap` | Trả identity snapshot, organization membership và feature/module availability |
| GET | `/organizations/{id}/dashboard` | Read model cho Home Dashboard: machine summary, recent QA, warning, job và quick links |
| GET | `/jobs/{id}` | Trạng thái job bất đồng bộ dùng chung |
| GET | `/jobs` | Danh sách job gần đây theo organization và filter |

Dashboard endpoint là read model tổng hợp; không chạy analysis khi render trang và không trả file lớn. Widget không có dữ liệu phải trả collection rỗng/metadata rõ ràng, không coi là lỗi server.

### 6.2. Organization, site và machine

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| GET | /organizations | Liệt kê organization của user |
| POST | /organizations | Tạo organization |
| GET | /organizations/{id} | Xem organization |
| GET | /organizations/{id}/sites | Liệt kê site |
| POST | /organizations/{id}/sites | Tạo site |
| GET | /sites/{id}/machines | Liệt kê machine |
| POST | /sites/{id}/machines | Tạo machine |
| PATCH | /machines/{id} | Cập nhật thông tin hiển thị machine |

P4 membership/invitation routes dùng prefix thực tế `/api/v1/organizations` và không có
action-level role. Các route organization-scoped resolve context trước khi lookup `id`:

| Method | Path | Mục đích và response |
| :--- | :--- | :--- |
| GET | `/organizations/{organization_id}/members` | List active members mặc định; `include_inactive=true` để xem lifecycle đầy đủ; có `offset/limit`. |
| PATCH | `/organizations/{organization_id}/members/{membership_id}` | Toggle `is_active`; bảo vệ last active member; trả member snapshot + audit. |
| POST | `/organizations/{organization_id}/invitations` | Chuẩn hóa email, tạo token random và trả raw token đúng một lần cùng invitation metadata. |
| GET | `/organizations/{organization_id}/invitations` | List invitation metadata; mặc định PENDING; `include_closed=true` để xem terminal history; không bao giờ trả raw token. |
| POST | `/organizations/{organization_id}/invitations/{invitation_id}/revoke` | Chuyển PENDING → REVOKED; token cũ không thể accept. |
| POST | `/organizations/invitations/accept` | Hash token, kiểm verified email/context/expiry và tạo hoặc reactivate membership trong một transaction. |

Error mapping tối thiểu: request schema → `REQUEST_VALIDATION_FAILED`/422; scope →
`ORGANIZATION_SCOPE_MISMATCH`/403; chưa có membership → `ORGANIZATION_MEMBERSHIP_REQUIRED`/403;
duplicate member/pending → `INVITATION_ALREADY_MEMBER` hoặc `INVITATION_ALREADY_PENDING`/409;
invalid token → `INVITATION_INVALID`/403 hoặc 409 theo nhánh; active context khác →
`ORGANIZATION_CONTEXT_ALREADY_ASSIGNED`/409; last member → `LAST_MEMBERSHIP_CONFLICT`/409.
Commit race dùng `INVITATION_CONFLICT` hoặc `MEMBERSHIP_CONFLICT`/409; không trả stack trace,
secret hay raw token trong error/log.

### 6.3. Folder và QA case

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| GET | /organizations/{id}/folders/tree | Xem cây folder |
| POST | /organizations/{id}/folders | Tạo folder |
| PATCH | /folders/{id} | Đổi tên, di chuyển hoặc archive folder |
| GET | /organizations/{id}/qa-cases | Tìm kiếm QA case |
| POST | /organizations/{id}/qa-cases | Tạo QA case |
| GET | /qa-cases/{id} | Xem chi tiết case |
| PATCH | /qa-cases/{id} | Cập nhật metadata nghiệp vụ |
| GET | /qa-cases/{id}/history | Xem artifact, run, report và lịch sử |

### 6.4. Artifact và validation

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| POST | /qa-cases/{id}/artifacts | Upload artifact |
| GET | /qa-cases/{id}/artifacts | Liệt kê artifact trong QA case |
| GET | /artifacts/{id} | Xem metadata |
| GET | /artifacts/{id}/download | Tải file theo organization |
| POST | /artifacts/{id}/validate | Chạy validation |
| GET | /artifacts/{id}/validations | Xem validation history |
| GET | /artifacts/{id}/manifest | Xem metadata DICOM/measurement đã chuẩn hóa |

### 6.5. QA analysis

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| GET | /qa-protocols | Tìm QA protocol |
| POST | /qa-protocols | Tạo protocol |
| POST | /qa-protocols/{id}/versions | Tạo protocol version |
| GET | /analysis-configurations | Tìm configuration |
| POST | /qa-cases/{id}/analysis-runs | Tạo analysis run |
| GET | /analysis-runs/{id} | Xem trạng thái và kết quả |
| POST | /analysis-runs/{id}/rerun | Chạy lại bằng configuration mới |
| GET | /analysis-runs/{id}/metrics | Xem metrics |
| GET | /analysis-runs/{id}/warnings | Xem warnings |
| GET | /analysis-runs/{id}/artifacts | Xem map, plot và result artifact |

Machine QA dùng cùng Analysis Run contract nhưng có endpoint nghiệp vụ rõ:

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| POST | `/qa-cases/{id}/machine-qa-runs` | Tạo lần nhập/chạy Machine QA từ protocol version |
| PATCH | `/machine-qa-runs/{id}/measurements` | Lưu draft measurement/value/unit/note theo idempotency/version |
| POST | `/machine-qa-runs/{id}/evaluate` | Evaluate rule và tạo immutable result run |
| GET | `/machine-qa-runs/{id}` | Xem checklist, measurement, metric, warning và provenance |

P7 triển khai thêm các endpoint và snapshot contract sau:

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| GET | `/organizations/{id}/machine-qa/protocols` | Liệt kê protocol version trong organization, kèm rule đã sắp thứ tự |
| POST | `/organizations/{id}/machine-qa/protocols/seed` | Tạo protocol seed `MACHINE_QA_BASELINE` v1 cho staging/local khi organization chưa có protocol |
| GET | `/qa-cases/{id}/machine-qa-runs` | Liệt kê các lượt Machine QA theo QA case |
| POST | `/machine-qa-runs/{id}/rerun` | Tạo lượt mới từ measurement của run đã hoàn tất; không sửa hoặc xóa run nguồn |
| GET | `/machine-qa-runs/{id}/compare?other_run_id=...` | So sánh metric snapshot của hai run cùng organization |

P7 lưu bốn nhóm dữ liệu: `qa_protocol_versions` và `qa_protocol_rules` là cấu hình có version; `machine_qa_runs` là measurement draft và kết quả đã chốt; `trend_points` là projection từ metric thực tế của run hoàn tất. Khi evaluate, result snapshot giữ lại protocol/rule snapshot, actual, baseline, tolerance, action level, margin, status và thời điểm đánh giá. Run `COMPLETED` hoặc `FAILED` không được sửa; rerun luôn sinh `machine_qa_runs` mới với `supersedes_run_id`. Mọi lookup đầu tiên đều kèm `organization_id` lấy từ membership của identity, không dùng truy vấn resource-ID toàn cục rồi mới kiểm tra scope.

Rule engine P7 hỗ trợ `RANGE`, `MIN`, `MAX`, `ABSOLUTE_DEVIATION`, `PERCENT_DEVIATION` và `NA`. Thiếu metric bắt buộc, sai unit hoặc giá trị không hợp lệ làm run `FAILED` và lưu `error_snapshot`; lệch trong action band tạo metric `WARNING`; kết quả nằm trong tolerance tạo `PASS`. Protocol seed chỉ là fixture kỹ thuật cho vertical slice, không phải giới hạn lâm sàng mặc định; thư viện protocol được quản trị/version hóa đầy đủ ở P11.

P8 local implementation slice hiện có migration `20260907_0007` cho Gamma run và
`20260908_0008` cho lease/attempt/outbox. Các entity reliability hiện có là
`gamma_analysis_runs`, `gamma_run_attempts` và `gamma_dispatch_outbox`. Các endpoint thực tế là:

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| POST | `/qa-cases/{id}/gamma-runs` | Preflight input, snapshot configuration/manifest và enqueue job bằng idempotency key |
| GET | `/qa-cases/{id}/gamma-runs` | Liệt kê job/result theo QA case và organization |
| GET | `/gamma-runs/{id}` | Poll status, progress, heartbeat, errors, warnings và result snapshot |
| POST | `/gamma-runs/{id}/retry` | Đưa job `FAILED` trở lại queue mà không đổi input/config snapshot |
| GET | `/gamma-runs/{id}/compare?other_run_id=...` | So sánh result snapshots của hai run cùng organization |
| GET | `/gamma/queue-metrics` | Kiểm tra backend queue, Redis stream/pending/consumer metrics và số run theo organization |

API không gọi engine trong request. `rt_connect_api.worker` publish các dispatch intent từ
`gamma_dispatch_outbox`, claim message, lấy lease/fencing token có điều kiện trong PostgreSQL,
đọc object storage, cập nhật `RUNNING`/heartbeat/progress rồi lưu `COMPLETED` hoặc `FAILED`.
Mỗi lần thực thi có `gamma_run_attempts`; worker cũ mất lease không được commit. Khi
`REDIS_URL` được cấu hình, API/dispatcher dùng Redis Stream consumer group; worker dùng
`XREADGROUP`, reclaim message quá visibility timeout bằng `XAUTOCLAIM`, rồi `XACK` sau khi
PostgreSQL đã có terminal state. PostgreSQL vẫn là nguồn dữ liệu nghiệp vụ, giữ retry count,
lease, attempt, heartbeat, result và error snapshot; Redis không phải nguồn dữ liệu duy nhất.
Khi không có `REDIS_URL`, local worker dùng database polling để giữ môi trường phát triển đơn
giản. Queue metrics không trả payload bệnh nhân; các bộ đếm stream là operational metrics,
còn bộ đếm Gamma run trong response được scope theo organization. Implementation hiện dùng
lease/visibility 120 s, tối đa 3 automatic attempts, exponential backoff có jitter, execution
deadline 900 s, voxel limit và candidate-evaluation limit từ `Settings`; release manifest phải
ghi giá trị effective của từng environment và benchmark/failure injection phải chứng minh chúng
không gây mất job hoặc chạy vô hạn.

Staging phải chứng minh cả hai service API và worker nhận cùng reference `REDIS_URL`, worker
log khởi động bằng Redis Streams thay vì polling, một run Gamma đi qua queue thật, message
được acknowledge sau khi hoàn tất, và pending count trở về 0. Nếu Redis không khả dụng, API
không âm thầm chạy phân tích trong HTTP request: nó trả lỗi queue rõ ràng, lưu trạng thái run
phù hợp và cho phép retry có kiểm soát.

Engine `gamma-nd-p8.2` nhận profile đã khóa của `gamma.measurement.v1` và DICOM RTDOSE:

- JSON measurement có `data_type=dose` hoặc `PLANAR_DOSE`, dose `GY`/`CGY`, position
  `mm`, grid 2D hoặc 3D và giá trị inline finite theo row-major shape. `CGY` được
  chuẩn hóa rõ ràng sang `GY`; engine không đoán đơn vị, không tự đổi shape và không
  tự đọc `object_key` trong JSON ở slice này.
- DICOM RTDOSE được đọc pixel data sau khi artifact đã qua metadata validation. Profile
  chuẩn P8 yêu cầu `DoseUnits=GY`; adapter kiểm tra modality, pixel data, `DoseGridScaling`,
  `DoseUnits`, `PixelSpacing`,
  `ImagePositionPatient`, `ImageOrientationPatient`, `NumberOfFrames` và
  `GridFrameOffsetVector`; chỉ nhận orientation axial IEC-aligned và grid z-spacing
  đều. JSON measurement có thể khai CGY và được chuyển đổi có provenance; DICOM CGY trực tiếp
  không phải fixture chuẩn P8 và phải bị chặn hoặc được gắn compatibility profile riêng.
- Grid 3D dùng thứ tự `(frame/z, row/y, column/x)` với spacing và origin cùng thứ tự.
  Reference và evaluation phải cùng số chiều, còn configuration `2D`/`3D` phải khớp
  grid. Measurement JSON và RTDOSE DICOM có thể là hai input của cùng một run.
- Gamma node search dùng bán kính `max_gamma × DTA`; interpolation `GRID` và
  multidimensional linear interpolation được snapshot trong configuration. `FULL_ROI` không
  bỏ điểm thiếu candidate khỏi mẫu số; `OVERLAP_ONLY` phải ghi coverage fraction; gamma vượt
  max bound là censored và percentile phải mang nhãn không exact.

Kết quả lưu dimensionality, source format, grid summary, map điểm, số điểm
evaluated/passing/nonpassing/excluded/no-candidate/censored, pass rate, coverage fraction,
percentile exactness, histogram, warning, configuration, input checksum và engine version.
Đây là deterministic engineering/golden slice; test local hiện có exhaustive independent node
oracle và các guard resource/retry, nhưng không thay thế benchmark theo phần cứng hoặc
commissioning. Gate phát triển, pilot và release theo plan.md v4.3. Coordinate frame mở rộng,
crash/ack/dead-letter injection, large workload benchmark và evidence effective schema/release
trên staging vẫn là điều kiện đóng P8.

### 6.6. Report và trend

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| GET | /report-templates | Liệt kê template |
| POST | /report-templates | Tạo template |
| POST | /report-templates/{id}/versions | Tạo template version |
| POST | /analysis-runs/{id}/reports | Tạo report revision |
| GET | /reports/{id} | Xem report |
| GET | /reports/{id}/revisions | Xem các revision |
| GET | /reports/{id}/export | Export report |
| GET | /trend | Truy vấn trend |
| GET | /trend/{machine_id} | Trend theo machine |
| POST | /trend/events | Ghi sự kiện bảo trì/thay đổi |

### 6.7. Biological Toolkit

API target và implementation phải dùng organization-scoped prefix `/api/v1/organizations/{organization_id}/biological`; bảng dưới đây mô tả target toàn bộ, còn route lifecycle P12 đã hiện thực được ghi trong `specification.md` SPEC-P12. Không gọi các target endpoint là available trước khi phase tương ứng có test và evidence.

| Method | Path | Mục đích |
| :--- | :--- | :--- |
| GET | /biological/alpha-beta | Tra cứu alpha/beta |
| POST | /biological/scenarios | Tạo scenario |
| GET | /biological/scenarios | Tìm scenario |
| GET | /biological/scenarios/{id} | Xem scenario |
| POST | /biological/scenarios/{id}/calculations | Chạy calculation |
| GET | /biological/calculations/{id} | Xem kết quả |
| POST | /biological/calculations/{id}/charts | Tạo đồ thị |
| POST | /biological/comparisons | So sánh hai hoặc nhiều course/phác đồ |
| POST | /biological/re-irradiation | Tạo và tính re-irradiation scenario |
| POST | /biological/fraction-compensation | Tạo các phương án bù fraction/gián đoạn |
| POST | /biological/library/validate | Validate-only một entry, không mutation |
| GET | /biological/library | Tìm/lọc entry theo type/status/context/fractions |
| POST | /biological/library | Tạo DRAFT/PUBLISHED entry |
| PATCH | /biological/library/{id} | Sửa DRAFT bằng optimistic revision |
| GET | /biological/library/{id}/revisions | Lịch sử family version |
| POST | /biological/library/{id}/clone | Clone sang version/key mới |
| POST | /biological/library/{id}/publish | Publish entry đã validate |
| POST | /biological/library/{id}/archive | Archive, giữ history |
| GET | /biological/library/{id}/compare | So sánh metadata/content |
| POST | /biological/library/{id}/use | Tạo explicit-use source snapshot |
| POST | /biological/library/import/validate | Preview import theo từng row |
| POST | /biological/library/import | Commit row hợp lệ của import |
| GET | /biological/library/{id}/export | Export JSON/CSV đúng version |
| POST | /biological/reports | Tạo calculation report độc lập |

### 6.8. API error contract

~~~json
{
  "code": "RTDOSE_REQUIRED",
  "message": "Workflow PSQA Gamma cần RTDOSE.",
  "correlation_id": "opaque-request-id",
  "details": [
    {"field": "body.reference_artifact_id", "message": "Required RTDOSE reference."}
  ]
}
~~~

Envelope phẳng khớp `core/errors.py`. `RTDOSE_REQUIRED`, `COMPARISON_REQUIRED`,
`GAMMA_WORKFLOW_PROFILE_INVALID` và `GAMMA_QUEUE_UNAVAILABLE` đã có trong P8 API slice;
engine warning `GAMMA_NO_CANDIDATE_WITHIN_DTA`/`GAMMA_SEARCH_CENSORED` được lưu trong result.
Các mã còn lại là target và phải được map bằng contract test, không được coi là đã triển khai chỉ vì xuất hiện trong tài liệu (xem specification.md §2.2):

- ORGANIZATION_NOT_FOUND.
- MACHINE_NOT_FOUND.
- FOLDER_NOT_FOUND.
- ARTIFACT_NOT_FOUND.
- UNSUPPORTED_MODALITY.
- INVALID_DICOM.
- GEOMETRY_MISMATCH.
- UNIT_MISSING.
- RTDOSE_REQUIRED.
- COMPARISON_REQUIRED.
- MEASUREMENT_REQUIRED.
- DVH_INPUT_REQUIRED.
- GAMMA_CONFIG_INVALID.
- GAMMA_WORKFLOW_PROFILE_INVALID.
- GAMMA_QUEUE_UNAVAILABLE.
- GAMMA_INPUT_NOT_VALIDATED.
- GAMMA_ARTIFACT_SCOPE_MISMATCH.
- BIOLOGICAL_INPUT_INVALID.
- CALCULATION_FAILED.
- REPORT_RENDER_FAILED.
- EXPORT_FAILED.

P17 hiện đã có các mã engine/API cụ thể sau và phải giữ nguyên khi mở rộng UI hoặc worker: `DVH_INPUT_MANIFEST_REQUIRED`, `DVH_INPUT_NOT_VALIDATED`, `DVH_INPUT_MANIFEST_INVALID`, `DVH_INPUT_SCOPE_MISMATCH`, `DVH_INPUTS_MUST_DIFFER`, `DVH_DOSE_ARTIFACT_INVALID`, `DVH_STRUCTURE_ARTIFACT_INVALID`, `DVH_ANATOMY_ARTIFACT_INVALID`, `DICOM_GEOMETRY_INVALID`, `DICOM_CAPABILITY_UNSUPPORTED`, `DICOM_FRAME_MISMATCH`, `DVH_DOSE_UNITS_UNSUPPORTED`, `DVH_DOSE_VALUES_INVALID`, `DVH_ROI_INVALID`, `CONTOUR_GEOMETRY_INVALID`, `DVH_EMPTY_STRUCTURE`, `DVH_INCOMPLETE_COVERAGE`, `DVH_PARTIAL_COVERAGE`, `DVH_COVERAGE_POLICY_INVALID`, `DVH_METRIC_INVALID`, `DVH_RESOURCE_LIMIT`, `DVH_SOURCE_CHANGED`, `DVH_IDEMPOTENCY_CONFLICT`, `DVH_STORAGE_UNAVAILABLE`, `DVH_EXECUTION_FAILED`, `DVH_PERSISTENCE_FAILED`, `DVH_RUN_NOT_FOUND`, `DVH_LIMIT_BINDING_CONFLICT`, `DVH_LIMIT_OVERRIDE_INVALID`, `DVH_LIMIT_ENTRY_NOT_FOUND`, `DVH_LIMIT_NOT_AVAILABLE`, `DVH_LIMIT_ENTRY_INVALID`, `DVH_PROTOCOL_NOT_FOUND`, `DVH_PROTOCOL_NOT_AVAILABLE`, `DVH_PROTOCOL_RULE_REQUIRED`, `DVH_PROTOCOL_RULE_NOT_FOUND`, `DVH_PROTOCOL_RULE_UNSUPPORTED`, `DVH_PROTOCOL_RULE_INVALID`, `DVH_LIMIT_METRIC_NOT_COMPUTED`, `DVH_LIMIT_METRIC_UNSUPPORTED`, `DVH_LIMIT_UNIT_MISMATCH` và `DVH_LIMIT_DEFINITION_INVALID`. `DVH_DOSE_ONLY_MODE` là warning; CT preview bổ sung warning `CT_RESCALE_DEFAULTED`, `CT_WINDOW_DEFAULTED`, `CT_SLICE_SPACING_DEFAULTED`, `CT_DOSE_NO_OVERLAP`. `QA_CASE_ARCHIVED` và `ORGANIZATION_SCOPE_MISMATCH` là boundary/lifecycle errors dùng chung. Mọi code mới phải có mapping HTTP, field details, UI message, recovery và test ID trong specification/plan.

---

## 7. DICOM ingestion và validation

### 7.1. DICOM hỗ trợ

Giai đoạn đầu hỗ trợ các nhóm:

- CT Image.
- RTDOSE.
- RTSTRUCT.
- RTPLAN.
- RTIMAGE nếu workflow cần.
- RTRECORD hoặc object delivery chỉ khi được đặc tả riêng.

Mỗi SOP Class được hỗ trợ phải có fixture và validation rule tương ứng.

### 7.2. Nguyên tắc đọc file

- Đọc metadata trước khi đọc pixel data lớn.
- Xác định Transfer Syntax.
- Kiểm tra Pixel Data khi workflow cần.
- Không sửa dataset trong object storage.
- Khi cần de-identification hoặc chuẩn hóa, tạo artifact dẫn xuất và ghi parent.
- Không dùng tên file làm định danh chính.

### 7.3. Validation RTDOSE

Tối thiểu kiểm tra:

- Modality là RTDOSE.
- SOP Instance UID không rỗng.
- Rows, Columns, Number of Frames hợp lệ.
- Pixel Spacing hợp lệ.
- Grid Frame Offset Vector hợp lệ nếu có.
- Image Position Patient và Image Orientation Patient hợp lệ khi có grid.
- Dose Grid Scaling hợp lệ.
- Dose Units được đọc và ghi nhận.
- Dose Type và Dose Summation Type được ghi nhận.
- Referenced RTPLAN hoặc RTSTRUCT/Referenced Image được kiểm tra khi có.
- Giá trị dose sau scaling không chứa giá trị bất hợp lệ ngoài rule.

### 7.4. Validation RTSTRUCT

Tối thiểu kiểm tra:

- Modality là RTSTRUCT.
- Structure Set ROI Sequence có ROI Number duy nhất.
- ROI có Referenced Frame of Reference UID.
- Contour sequence có tọa độ hợp lệ.
- Referenced Series/Images được truy ra khi cần.
- ROI name, ROI number và geometry được lưu vào normalized manifest.
- Structure không được ghép với dose chỉ dựa trên tên ROI.

### 7.5. Validation RTPLAN

Khi workflow dùng RTPLAN, kiểm tra:

- Modality là RTPLAN.
- Plan UID và referenced fraction/beam group.
- Beam number, beam name và control point nếu có.
- Machine/beam device reference.
- Isocenter và coordinate system.
- Liên kết với RTDOSE theo UID hoặc explicit user selection.
- Prescription chỉ được đọc và hiển thị; không được tự sửa.

### 7.6. Liên kết dataset

Hệ thống không tự ghép dataset chỉ vì cùng PatientID hoặc cùng tên file. Việc ghép phải dựa trên:

- UID reference hợp lệ.
- Frame of Reference phù hợp.
- User selection rõ ràng.
- Geometry validation.
- Workflow requirement.

Nếu có nhiều dataset phù hợp, hiển thị danh sách để user chọn.

### 7.7. Measurement import

Measurement contract phải mô tả:

- schema_version.
- Dataset id.
- Data type.
- Dose unit.
- Position unit.
- Grid dimensions.
- Grid spacing.
- Origin.
- Orientation.
- Values hoặc points.
- Detector/array.
- Phantom.
- Acquisition timestamp.
- Reference metadata.
- Source file checksum.

Dữ liệu không có đơn vị, spacing hoặc ý nghĩa cột rõ ràng bị từ chối hoặc yêu cầu bổ sung.

---

## 8. Gamma Analysis Engine

### 8.1. Định nghĩa dữ liệu

Mỗi Gamma run có:

- Reference dataset.
- Evaluation/comparison dataset.
- Dose difference criterion.
- Distance-to-agreement criterion.
- Dose normalization.
- Dose threshold.
- Global/local mode.
- Absolute/relative mode.
- 2D/3D mode.
- Per-field/composite mode.
- ROI/mask.
- Alignment/shift.
- Interpolation/resampling.
- Search distance.
- Maximum gamma.
- Engine version.
- Input checksums.

### 8.2. Contract gamma.measurement.v1

Ví dụ contract kỹ thuật:

~~~json
{
  "schema_version": "gamma.measurement.v1",
  "dataset_id": "measurement-001",
  "data_type": "PLANAR_DOSE",
  "units": {
    "dose": "cGy",
    "position": "mm"
  },
  "grid": {
    "shape": [128, 128],
    "spacing_mm": [2.5, 2.5],
    "origin_mm": [-160.0, -160.0],
    "orientation": "IEC_XY",
    "values_order": "row-major"
  },
  "values": {
    "encoding": "float32",
    "object_key": "measurements/measurement-001.npy"
  },
  "acquisition": {
    "detector": "example-array",
    "phantom": "example-phantom",
    "measured_at": "2026-01-01T00:00:00Z"
  },
  "source": {
    "filename": "measurement.json",
    "sha256": "..."
  }
}
~~~

Ví dụ object_key phía trên là thiết kế mục tiêu, không phải profile được adapter hiện tại hỗ trợ. Values lớn chỉ được trỏ tới managed artifact đã kiểm organization/checksum; không đọc arbitrary object_key từ input. Contract phải có schema validator và fixture.

Adapter 2D ban đầu là snapshot lịch sử. Code `gamma-nd-p8.2` đã mở rộng inline 2D/3D và RTDOSE như mô tả §6.5, nhưng chưa chứng minh toàn bộ contract target. Profile production, DICOM chuẩn, coordinate frame, denominator/search và oracle được khóa ở specification.md §3.4/§5; các gap P8 vẫn phải được kiểm thử trước đóng phase.

### 8.3. Pipeline

~~~text
Load input
  -> validate contract and DICOM
  -> resolve reference/evaluation roles
  -> normalize units
  -> validate geometry
  -> apply explicit alignment/resampling
  -> calculate gamma
  -> calculate summary metrics
  -> generate map/histogram
  -> persist result and provenance
~~~

### 8.4. Kết quả Gamma

Tối thiểu lưu:

- Pass rate.
- Number of valid points.
- Number of points passing.
- Number of points failing.
- Mean gamma.
- Maximum gamma hoặc capped maximum.
- Percentiles.
- Dose cutoff.
- Gamma map.
- Histogram.
- Reference/evaluation summary.
- Configuration snapshot.
- Input checksums.
- Warnings.
- Execution duration.
- Engine version.
- Result status.

### 8.5. Điều kiện không được tính

- Thiếu RTDOSE khi workflow yêu cầu RTDOSE.
- Thiếu comparison dataset.
- Thiếu measurement contract.
- Dose unit không xác định.
- Geometry không xác định.
- Array shape không phù hợp.
- Cấu hình có criterion không dương.
- Không thể xác định reference/evaluation role.
- Dữ liệu có lỗi không thể xử lý.

### 8.6. Tính tái lập

Cùng một input checksum, configuration snapshot và engine version phải tạo kết quả tương đương trong sai số số học đã công bố. Random subset không dùng cho kết quả clinical summary mặc định; nếu có dùng cho preview, phải ghi rõ là preview và lưu random seed.

---

## 9. DVH và Plan Review

### 9.1. Input

DVH review yêu cầu:

- RTDOSE.
- RTSTRUCT.
- Liên kết structure–dose hợp lệ.
- Frame of Reference phù hợp hoặc transform rõ ràng.
- Dose unit và scaling hợp lệ.

CT chỉ bắt buộc khi cần hiển thị dose trên anatomy hoặc kiểm tra trực quan.

### 9.2. Pipeline DVH

~~~text
Read RTDOSE grid
  -> read RTSTRUCT contours
  -> resolve Frame of Reference
  -> rasterize structure mask
  -> resample dose only with explicit method
  -> calculate voxel dose distribution
  -> build cumulative/differential DVH
  -> calculate requested metrics
  -> compare protocol rules
  -> save metric + plot + provenance
~~~

### 9.3. Metric hỗ trợ

Giai đoạn đầu có thể hỗ trợ:

- Dmin.
- Dmax.
- Dmean.
- Dmedian.
- D2, D5, D50, D95, D98.
- Vx.
- Volume.
- Integral dose nếu được đặc tả.
- Homogeneity index nếu protocol định nghĩa.
- Conformity index nếu protocol định nghĩa.

Mỗi metric phải có định nghĩa, percentile convention, interpolation method và unit.

### 9.4. Structure mapping

- Ưu tiên ROI Number và Referenced Frame of Reference.
- ROI name chỉ dùng làm label hiển thị.
- Mapping thủ công được lưu trong configuration snapshot.
- Nếu ROI không map được, trả `DVH_ROI_INVALID`, `DVH_STRUCTURE_ARTIFACT_INVALID` hoặc `DVH_EMPTY_STRUCTURE` tùy tình trạng; không dùng `ROIName` thay cho ROINumber.
- Không tự gộp hai ROI cùng tên nhưng khác structure set.

### 9.5. P17 implementation contract — current code

P17 hiện được hiện thực bởi bốn lớp tách biệt, để phần số học không phụ thuộc HTTP hay database và việc gắn giới hạn không làm thay đổi engine thuần:

| Lớp | Thành phần | Trách nhiệm |
| :--- | :--- | :--- |
| Domain engine | `apps/api/src/rt_connect_api/services/dose_dvh_engine.py` | Đọc RTDOSE/RTSTRUCT, giải affine patient LPS, rasterize ROI, tính coverage/metrics/curve/preview và hash kết quả. Không biết organization, auth hay storage. |
| Limit adapter | `apps/api/src/rt_connect_api/services/dvh_limit_adapter.py` | Resolve đúng một P16 `DOSE_LIMIT` hoặc P11 rule `ACTIVE` theo organization; validate override/metric/unit; tạo source/effective snapshot và tính actual/limit/margin. Không tự search, rank hoặc auto-apply. |
| API/persistence | `apps/api/src/rt_connect_api/api/dvh.py`, `DVHAnalysisRun`, migration `20260908_0017_dvh_analysis.py` | Resolve scope trước query, kiểm artifact/manifest/checksum, tải object, gọi engine, idempotency, audit, snapshot và export. |
| CT preview/web | `create_ct_preview`, `GET .../dvh/ct-preview`, `apps/web/src/pages/DVHPage.tsx` | Đọc CT bounded single-file/multi-frame, rescale HU, window/level, chọn frame, map dose/ROI bằng patient LPS nearest-neighbor, vẽ grayscale/overlay/crosshair. Read-only, không tạo DVH run. |
| Report integration/web | `apps/api/src/rt_connect_api/api/reports.py`, `apps/web/src/pages/ReportBuilderPage.tsx`, route `/app/qa/cases/:caseId/dvh` | DVH route chọn input/ROI/policy, validate-preview, save, hiển thị metric/curve/dose-native mask/CT preview/history/provenance và JSON/CSV; Report Builder chọn run DVH theo case và lưu source snapshot. Route DVH không nằm trong global sidebar. |

**Engine identity:** `visual-dose.dvh` / `p17-dvh-1.1.0`. Bản `1.1.0` pin volume-weighted cumulative-DVH interpolation cho `D(x)` và phải được lưu trong mọi result snapshot; không đọc lại run cũ bằng engine mới rồi ghi đè kết quả cũ.

#### 9.5.1. Input resolution và boundary

1. `organization_id` trong URL phải khớp membership của JWT; `case_id` phải thuộc organization và chưa archive.
2. Artifact phải đồng thời thuộc organization/case, `artifact_type=DICOM`, đúng modality (`RTDOSE`, `RTSTRUCT`, tùy chọn `CT`) và `data_status=VALID`.
3. Mỗi artifact phải có `InputManifest` mới nhất với `validation_summary.result=VALID` và checksum 64 ký tự hex thường. Trước khi engine đọc, bytes tải từ object storage được hash lại và phải khớp cả `Artifact.sha256` lẫn `InputManifest.checksum_at_use`.
4. Không dùng global artifact lookup, filename, ROIName, dữ liệu do browser tự tính hoặc database pointer “latest” làm authority cho một run.

#### 9.5.2. DICOM geometry algorithm

- RTDOSE pixel array được đổi sang Gy bằng `pixel_array * DoseGridScaling`; chỉ chấp nhận `DoseUnits=GY`, pixel finite và không âm.
- `ImageOrientationPatient` gồm direction của columns trước, direction của rows sau. `PixelSpacing` giữ thứ tự `(row_spacing, column_spacing)`. Normal là tích có hướng `row × column`; điểm contour patient LPS được chiếu về frame/row/column theo affine này.
- `GridFrameOffsetVector` được chuẩn hóa thành một vector kể cả trường hợp single-frame pydicom trả scalar. Slice thickness lấy metadata hợp lệ hoặc request override dương cho single-frame; nhiều frame phải có spacing/thickness hợp lệ.
- ROI contour được chọn bằng `ROINumber`; polygon kín rasterize trên frame gần z-offset nhất. Contour `CLOSED_PLANAR_XOR` và hole/disjoint dùng parity; không phụ thuộc contour winding. Contour ngoài grid được đếm để áp dụng coverage policy, không silently clip thành zero dose.
- Voxel volume dùng `row_spacing × column_spacing × slice_thickness / 1000` cc. `Dmean` là weighted average; `D(x)` gom các dose quan sát bằng nhau, sắp dose giảm dần, cộng dồn `voxel_volume_cc` và nội suy tuyến tính giữa hai điểm cumulative-volume kề nhau; `D0=Dmax`, `D100=Dmin`, ngoài khoảng quan sát không ngoại suy. `V(x)` cộng volume của voxel có dose `>= x` và trả cả cc/%. Quy ước này phải nằm trong engine version/result snapshot.

#### 9.5.2a. CT preview và patient-LPS overlay

CT preview dùng chung dose loader/geometry của P17 nhưng là operation riêng, không đưa pixel CT vào phép tính DVH:

1. `load_ct_volume()` chỉ nhận CT DICOM single-file hoặc multi-frame có `Modality=CT`, top-level `ImagePositionPatient`/`ImageOrientationPatient`/`PixelSpacing`, frame offsets tăng dần, `SamplesPerPixel=1` và photometric `MONOCHROME1` hoặc `MONOCHROME2`. `CTGeometry` giữ shape `(frames, rows, columns)`, direction cosines, origin, spacing, offsets, thickness, Frame UID và photometric.
2. Pixel array được giới hạn bởi `Settings.dvh_max_ct_pixels` (`DVH_MAX_CT_PIXELS`, mặc định 8,000,000). `create_ct_preview()` giới hạn số pixel output bởi `Settings.dvh_max_ct_preview_pixels` (`DVH_MAX_CT_PREVIEW_PIXELS`, mặc định 65,536; API cho phép 256–262,144 nhưng không được vượt cấu hình). Vượt ngưỡng trả `DVH_RESOURCE_LIMIT` trước khi cấp output lớn.
3. Giá trị hiển thị là HU: `stored × RescaleSlope + RescaleIntercept`. Slope/intercept thiếu hoàn toàn có default `1/0` kèm warning `CT_RESCALE_DEFAULTED`; field sai kiểu, non-finite hoặc slope bằng 0 là lỗi. Thiếu cả window center/width dùng percentile 1–99 cho display và warning `CT_WINDOW_DEFAULTED`; width không dương là lỗi. Các default này chỉ dành cho preview, không được ghi ngược thành metadata DICOM.
4. `_grid_points()` tạo patient-LPS point cho từng pixel output của lát `frame_index`; `DoseGeometry.world_to_continuous_indices()` map point về dose continuous `(frame,row,column,normal)`. Dose và ROI dùng nearest-neighbor với kiểm tra bounds; pixel ngoài dose là `null/false`, không clip và không gán 0.
5. `registration` luôn ghi `mode=SHARED_FRAME_OF_REFERENCE`, `patient_coordinate_system=LPS`, `overlay_algorithm=NEAREST_NEIGHBOR_IN_PATIENT_LPS`, source/target Frame UID, selected dose frame, mapping matrix và crosshair từ tâm dose grid. Đây là rigid shared-frame mapping, không phải deformable registration, image registration tối ưu hay dose accumulation.
6. `CT_PREVIEW_SCHEMA_VERSION=visual-dose-ct-preview.v1`, `CT_PREVIEW_ENGINE_KEY=visual-dose.ct-preview` và `CT_PREVIEW_ENGINE_VERSION=p17-ct-preview-1.0.0` được trả trong response. `result_sha256` hash canonical JSON gồm CT display, registration, overlay, ROI và warnings. Endpoint không insert DB, không enqueue worker, không tạo audit mutation và không được dùng làm source để tính DVH.

API adapter tải dose/CT/structure bằng `_download_resolved_artifact()`, kiểm `Artifact.sha256` và `InputManifest.checksum_at_use` trước khi gọi engine. Nếu structure/ROI được gửi, hai tham số phải cùng tồn tại; nếu không, `DVH_ROI_INVALID`. CT cùng Frame UID là điều kiện bắt buộc; không có overlap trả `CT_DOSE_NO_OVERLAP` warning với `overlay_available=false`, vẫn cho hiển thị CT grayscale.

#### 9.5.3. Persistence và API sequence

```text
JWT -> resolve membership/org -> resolve case
    -> resolve VALID artifacts/manifests
    -> download + checksum verify
    -> engine preflight/calculation
    -> validate response OR transaction(run + audit)
    -> read snapshot for history/export
```

`POST .../dvh/validate` không mutation. `POST .../dvh/runs` tính xong mới flush `DVHAnalysisRun` và audit; unique `(organization_id, idempotency_key)` cùng request fingerprint bảo vệ double-click/retry. Nếu race commit gặp unique conflict, API query key và trả run cùng fingerprint với HTTP 200; fingerprint khác trả HTTP 409. Export JSON/CSV lấy dữ liệu đã lưu, không rerun engine.

`DVHAnalysisRun` lưu `organization_id`, `qa_case_id`, dose/structure/CT artifact IDs, `roi_number`, idempotency key/fingerprint, engine key/version, status, input/result/warning/error snapshots, actor và timestamps. Snapshot phải giữ source artifact/manifest IDs, filename/type/modality/byte size/SHA, selected metadata, validation summary, normalized request, geometry, coverage, metrics, curve, preview và result SHA. Khi user chọn limit source, `input_snapshot.limit_binding` pin source type/id, version/status/hash, effective values, override, warnings và binding hash; `result_snapshot.limit_evaluation` pin actual/limit/margin/rule status và giữ `engine_result_sha256` trước lớp binding.

#### 9.5.4. Explicit P11/P16 limit binding

`resolve_dvh_limit_binding()` là boundary duy nhất nối P17 với P11/P16 trong candidate hiện tại:

1. Không có `limit_entry_id` và `protocol_version_id`: chạy pure DVH, không có comparison evaluation. `protocol_metric_key` hoặc `limit_override` đi kèm không source là lỗi.
2. Có `limit_entry_id`: lookup bằng `(organization_id, id)`, yêu cầu `entry_type=DOSE_LIMIT`, không archived; chỉ override whitelist được nhận và phải qua validator P16. Draft/reference chưa available tạo warning được snapshot, không tự chặn nếu definition vẫn hợp lệ.
3. Có `protocol_version_id`: lookup bằng `(organization_id, id)`, yêu cầu `status=ACTIVE`, `protocol_metric_key` bắt buộc và rule được lookup trong cùng organization/protocol. Chỉ `MAX`, `MIN`, `RANGE`, `TARGET` có limit rõ ràng được evaluate; protocol không nhận override tự do.
4. Metric mapping: DMIN/DMEAN/DMAX đọc scalar; `Dxx` đọc key trong `Dx_gy`; `Vx` đọc `Vx_percent` hoặc `Vx_cc` theo unit và kiểm tra `metric_parameter`; Dxcc chưa được bật. Actual/limit unit mismatch hoặc metric không có trong request là lỗi rõ ràng.
5. Evaluation dùng margin có dấu: MAX=`limit-actual`, MIN=`actual-limit`, RANGE=`min(actual-lower,upper-actual)`, TARGET=`-abs(actual-target)`. `rule_status` là PASS/FAIL của rule; source warning làm display `status=REVIEW_REQUIRED`, không làm mất rule status. `auto_applied=false` luôn được lưu.

`Report Builder` cho phép `source_type=DVH` với `source_id` là một run đã lưu. API report lookup phải có `organization_id`; payload source snapshot chứa run/input/result/warning/error snapshot và engine/fingerprint. Report revision không rerun DVH, không đọc latest pointer và không làm thay đổi run.

#### 9.5.5. Capability boundary và phần chưa hoàn tất

- P17 current slice là synchronous, physical-dose, dose-native grid; CT preview cũng synchronous/read-only. Đã có explicit P11/P16 actual/limit/margin adapter, DVH report source và CT pixel renderer/crosshair/LPS registration payload ở local candidate; chưa có worker queue cho DVH/CT workload lớn, deformable registration, CT series aggregation hoặc staging evidence đầy đủ cho binding/report/CT.
- CT preview chỉ là bounded visual overlay trên shared Frame of Reference. Không suy ra image registration thành công từ UID giống nhau, không dùng default window/rescale làm clinical metadata, không cho phép output vượt resource policy và không biến overlay warning thành QA result.
- P17 không tính deformable cumulative dose, không tự cộng dose giữa course, không sửa prescription/RTPLAN/TPS/PACS và không tự tạo QA PASS.
- Các phần mở phải có package/test/evidence riêng ở P17/P18; không dùng ảnh Stitch hoặc `/ready` 200 làm bằng chứng thay thế.

---

## 10. Machine QA và Trend

### 10.1. Machine QA

Machine QA cho phép:

- Tạo checklist theo Daily/Monthly/Annual/Custom.
- Nhập giá trị đo.
- Gắn unit.
- Gắn baseline.
- Gắn tolerance/action level.
- Tính margin.
- Ghi chú và artifact liên quan.
- Đưa metric hợp lệ vào trend.

### 10.2. Rule engine

Rule engine cần hỗ trợ:

- value <= limit.
- value >= limit.
- Khoảng min–max.
- Sai lệch tuyệt đối so với baseline.
- Sai lệch phần trăm so với baseline.
- Nhiều metric trong một test.
- Rule không áp dụng.
- Metric cần user review.

Rule snapshot được lưu trong Analysis Run và Report Revision.

### 10.3. Trend normalization

Trend key/projection hiện tại gồm:

- machine_id.
- qa_type.
- qa_cycle.
- metric_key.
- unit.
- energy.
- detector.
- phantom.
- beam_quality.
- acquisition_mode.
- protocol_key.
- protocol_version.
- measured_at.

Projection lưu `context_snapshot` cùng `organization_id`, `source_run_id`, `qa_case_id`, value, unit, status và measured_at. Unique constraint hiện tại là organization + source run + metric; đây là read model có thể rebuild từ Machine QA result snapshot, không phải source of truth. Nếu unit/context khác nhau, compatibility signature tạo series riêng; không vẽ chung và không tự quy đổi.

API P10 hiện triển khai các surface sau: trend raw/day/week; filter machine/metric/unit/timezone/context; baseline list/create/update có version; maintenance event list/create/update có revision và revision history; rebuild projection; source drill-down; CSV/JSON export. Khoảng thời gian API là `[from, to)`, bucket day/week theo IANA timezone, còn timestamp/source ID canonical theo UTC.

Baseline chọn theo machine/metric/unit/context và effective interval của từng point. `delta = value - baseline`; outlier dùng action level nếu có, nếu không dùng tolerance. Thiếu baseline chỉ tạo warning. Aggregate luôn giữ count, mean, min, max, first/last, status counts, source point IDs và source run IDs để không mất khả năng điều tra.

### 10.4. Maintenance event

Maintenance event gồm:

- machine_id.
- event_type.
- title.
- started_at/ended_at.
- notes.
- metadata snapshot.
- revision_number.
- status.
- created_by.
- append-only revision snapshots.

Trend chỉ hiển thị sự kiện; không tự suy luận nguyên nhân. Update phải có `expected_revision`; conflict không overwrite bản hiện tại. Marker không sửa `TrendPoint`, `MachineQARun` hoặc report.

---

## 11. Report Builder và rendering

### 11.1. Kiến trúc report

Report gồm:

1. Data snapshot.
2. Template version.
3. Block configuration.
4. Render context.
5. Output artifacts.
6. Provenance manifest.

### 11.2. Full customization

User được tùy chỉnh:

- Thêm, bớt, ẩn block.
- Đổi tên title/label.
- Chọn metric.
- Chọn biểu đồ.
- Đổi thứ tự.
- Đổi khoảng thời gian trend.
- Thêm nhận xét.
- Chọn điều kiện hiển thị.
- Tạo nhiều template theo mục đích.

Hệ thống không áp đặt một mẫu report bắt buộc. Nội dung do user ẩn hoặc thay đổi vẫn được giữ trong snapshot của revision và lịch sử.

### 11.3. Block types

Block registry tối thiểu:

- OrganizationInfo.
- SiteInfo.
- MachineInfo.
- QACaseInfo.
- InputManifest.
- ValidationSummary.
- MetricTable.
- WarningTable.
- GammaMap.
- GammaHistogram.
- DoseProfile.
- DVHPlot.
- TrendChart.
- ComparisonTable.
- BiologicalCalculationSummary.
- UserNotes.
- RevisionHistory.
- ProvenanceSummary.

### 11.4. Rendering

- Render HTML trước khi render PDF.
- Dùng font và locale được cấu hình.
- Hình ảnh plot lưu riêng và có checksum.
- PDF/PNG render lỗi phải trả REPORT_RENDER_FAILED.
- Output lưu engine/render version.
- Tái render từ snapshot không đọc dữ liệu đang thay đổi.
- Export CSV/JSON dùng schema version rõ ràng.

---

## 12. Biological Toolkit

### 12.1. Bounded context

Biological Toolkit có database namespace hoặc logical module riêng:

- Không có foreign key bắt buộc tới QA case.
- Không tự truy cập patient list.
- Không tự lấy RT Plan.
- User chủ động upload hoặc nhập dataset.
- Biological Report là report độc lập.
- Có thể dùng chung object storage và audit infrastructure.

### 12.2. BED/EQD2 engine

Input:

- Tổng liều D.
- Số fraction n.
- Liều mỗi fraction d.
- Alpha/beta.
- Đơn vị.
- Tissue label.
- Model name.
- Source.
- Assumptions.

Công thức LQ cơ bản:

~~~text
BED = n*d*(1 + d/(alpha/beta))
EQD2 = BED/(1 + 2/(alpha/beta))
~~~

Validation:

- n > 0.
- d >= 0.
- D >= 0.
- Alpha/beta > 0.
- D phải nhất quán với n*d nếu user nhập cả hai.
- Cảnh báo nếu input dùng fraction rất lớn hoặc model không phù hợp với scenario được chọn.
- Không tự chọn alpha/beta mặc định khi user chưa xác nhận context.

### 12.3. Đồ thị theo tổng liều D

Tham số:

- D min/max/step.
- n.
- alpha/beta list.
- tissue/target/OAR label.
- BED hoặc EQD2.
- Unit.
- Model.
- Source.

Output:

- Line chart.
- Data table.
- Marker theo D user chọn.
- Legend alpha/beta.
- Export PNG/SVG/CSV.
- Calculation snapshot.

### 12.4. So sánh phác đồ

Mỗi course:

- Tên.
- Bệnh lý/scenario.
- D.
- n.
- d.
- Overall treatment time nếu có.
- Tissue.
- Alpha/beta.
- Source.
- Assumption.

Output:

- BED/EQD2 từng course.
- Chênh lệch tuyệt đối.
- Chênh lệch phần trăm.
- Bảng.
- Đồ thị.
- Warnings về khác biệt model hoặc context.

### 12.5. Bảng giới hạn liều

DoseLimitEntry gồm:

- Disease.
- Anatomy.
- Structure/OAR.
- Technique.
- Fractionation.
- Metric.
- Limit.
- Unit.
- Context.
- Source type.
- Citation.
- Evidence level.
- Applicability.
- Notes.
- Updated date.

Bảng chỉ phục vụ tra cứu và tính toán, không biến thành prescription.

### 12.6. Protocol điều trị và knowledge library

KnowledgeEntry có:

- Title.
- Disease.
- Anatomy.
- Topic.
- Summary.
- Formula.
- Assumptions.
- Reference.
- DOI/URL.
- Evidence level.
- Applicability limits.
- User note.
- Version.

TreatmentProtocolReference có:

- Tên phác đồ.
- Bệnh lý.
- Vị trí.
- Kỹ thuật.
- Tổng liều.
- Số fraction.
- Target/OAR notes.
- Planning notes.
- Dose constraints.
- BED/EQD2 reference.
- Source.
- Applicability limit.

Các entry chỉ là kiến thức và công cụ tính toán, không tự link với ca lâm sàng.

P16 hiện thực các loại entry trên bằng `biological_library_entries` trong một
organization-scoped namespace. `entry_type` phân biệt `DOSE_LIMIT`,
`TREATMENT_PROTOCOL`, `KNOWLEDGE` và `ALPHA_BETA`; `version_number`,
`source_entry_id`, `revision`, `source_type`, `reference_status`,
`applicability`, `citation` và `content_sha256` tạo lineage. API/UI không dùng
những entry này để tự động prefill hay thay đổi một calculation; việc sử dụng
phải qua explicit-use snapshot theo SPEC-P16.

### 12.7. Re-irradiation calculator

Input nhiều course:

- Course name.
- Treatment date/range.
- Total dose.
- Fractions.
- Dose per fraction.
- Tissue/OAR/target.
- Alpha/beta.
- Source.
- Recovery assumption.
- Time interval.
- Spatial dataset nếu user chủ động cung cấp.
- Registration/transform note nếu có.

Output:

- BED/EQD2 từng course.
- Cumulative scalar BED/EQD2.
- Scenario comparison.
- Recovery/no-recovery comparison.
- Graph theo course và thời gian.
- Assumption table.
- Warnings.
- Calculation report độc lập.

Spatial accumulation:

- Chỉ thực hiện khi geometry và registration đáp ứng contract.
- Không cộng dose theo không gian chỉ từ tên structure hoặc PatientID.
- Nếu thiếu geometry, chỉ cho scalar calculation và hiển thị rõ giới hạn.
- Không tự lấy dữ liệu từ QA case hoặc treatment record.

### 12.8. Bù fraction

Input:

- Lịch ban đầu.
- Số fraction đã thực hiện.
- Liều đã thực hiện.
- Fraction bị thiếu.
- Fraction còn lại.
- Khoảng gián đoạn.
- Overall treatment time.
- Các phương án user muốn so sánh.

Output là scenario/proposal tính toán, không phải prescription.

---

## 13. Provenance và audit

### 13.1. Lineage bắt buộc

~~~text
Report Revision
  -> Report Template Version
  -> Analysis Run / Biological Calculation Run
  -> Analysis Configuration
  -> Protocol Version hoặc Model
  -> Input Manifest
  -> Artifact checksum
  -> User + timestamp
  -> Engine version
~~~

### 13.2. Hash và snapshot

- File gốc có SHA-256.
- Configuration có canonical JSON hash.
- Input Manifest có hash.
- Result payload có hash.
- Report render có hash.
- Biological scenario có snapshot trước khi tính.
- Hash chỉ phục vụ kiểm tra tính toàn vẹn, không dùng để khóa tùy chỉnh report.

### 13.3. Audit event

Audit event được tạo khi:

- Tạo/sửa/archive folder.
- Upload/import/export artifact.
- Chạy validation.
- Tạo/chỉnh configuration.
- Chạy analysis.
- Tạo/chỉnh report.
- Tạo/chỉnh protocol.
- Tạo/chỉnh biological scenario.
- Thay đổi knowledge hoặc dose limit.

Audit history không bị xóa cứng.

---

## 14. Bảo mật và vận hành dữ liệu

Phần này chỉ mô tả bảo vệ dữ liệu và tính ổn định vận hành, không tạo phân cấp nghiệp vụ.

### 14.1. Organization isolation

- Mọi record nghiệp vụ có organization_id hoặc truy ra organization.
- API luôn kiểm tra organization context.
- Không cho truy vấn chéo organization.
- Background job giữ organization context.
- Export ghi organization context vào manifest.

### 14.2. Authentication

- Supabase Auth quản lý user identity, password/OTP/magic link theo provider được bật và session.
- RT-CONNECT không lưu password; chỉ lưu `supabase_user_id`/profile snapshot và membership cần cho nghiệp vụ.
- API luôn xác minh Supabase access token ở server; không tin dữ liệu user hoặc organization do frontend tự gửi mà chưa đối chiếu database.
- Có logout, refresh/revoke session theo khả năng của Supabase Auth và timeout cấu hình được.
- Supabase publishable/anon key có thể xuất hiện ở frontend theo mô hình của Supabase; service key, Railway PostgreSQL URL/password và Railway secrets tuyệt đối không xuất hiện ở frontend hoặc log.
- Các service-to-service token tách khỏi user token; worker không giữ access token của user.
- Supabase Auth project, redirect URL, email provider và Railway database connection/secrets được tách theo environment.
- Khi key rotation hoặc Auth provider lỗi, hệ thống có error handling và runbook tương ứng; không tự chuyển sang anonymous access.

### 14.3. File safety

- Giới hạn dung lượng và loại file.
- Kiểm tra media type thực tế.
- Quét file theo khả năng hạ tầng.
- Object key không dùng trực tiếp tên file từ user.
- Signed URL có thời hạn.
- Download ghi audit event.

### 14.4. Backup và khôi phục

Backup tối thiểu gồm:

- Railway PostgreSQL database/schema/data.
- Object storage.
- Configuration và deployment manifest.
- Secrets reference, không ghi secret plaintext vào backup log.

Phải có bài kiểm tra restore định kỳ và ghi kết quả vào vận hành.

Local support harness hiện thực hóa một phép kiểm bounded tại
`scripts/verify-local-backup-restore.py`. Harness dùng `pg_dump --format=custom`,
restore vào database tạm, inventory mọi object MinIO theo kích thước và SHA-256,
copy sang bucket tạm, so sánh inventory rồi dọn tài nguyên tạm. Harness chỉ được
chạy với topology `docker-compose.yml` local và không phải provider backup,
staging restore, RPO/RTO hoặc production runbook. Evidence của nó ghi row/object
inventory hash, dump size/hash và trạng thái cleanup nhưng không ghi dump/object
content hay secret. P18 vẫn phải kiểm provider backup/restore, isolated restore,
lineage/checksum và thời gian RPO/RTO trên candidate thật.

### 14.5. Bảo vệ public web

- Chỉ public endpoint cần thiết cho web/API qua HTTPS; database, Redis, object storage, worker và DICOM gateway nằm trong private network.
- Không dùng public bucket. File được tải xuống qua API hoặc signed URL có thời hạn.
- Cấu hình CORS theo domain triển khai, không dùng wildcard trong production nếu không có lý do được ghi nhận.
- Bật HSTS sau khi đã xác nhận HTTPS hoạt động ổn định; chuyển hướng HTTP sang HTTPS.
- Giới hạn request body, thời gian upload, số request và số job để tránh làm nghẽn dịch vụ.
- Dùng secure cookie hoặc token có thời hạn; chống CSRF nếu dùng cookie-based session.
- Không đưa PatientID, token, secret hoặc nội dung DICOM nhạy cảm vào URL, log public hay thông báo lỗi phía client.
- Health/readiness endpoint không trả secret, metadata bệnh nhân hoặc thông tin nội bộ không cần thiết.
- Có cơ chế cập nhật và thu hồi certificate, secret, session và service token.
- Thực hiện kiểm tra từ một mạng bên ngoài hạ tầng trước khi mở public release.

---

## 15. Non-functional requirements

### 15.1. Tính đúng và toàn vẹn

- Không mất file gốc khi import.
- Không thay đổi result cũ khi chạy result mới.
- Report cũ tái hiện từ snapshot.
- Analysis failure không tạo result hợp lệ một phần.
- Dữ liệu thiếu bị cảnh báo hoặc từ chối theo validation rule.

### 15.2. Hiệu năng mục tiêu ban đầu

Các mục tiêu này là target kỹ thuật để đo trong phase triển khai, có thể điều chỉnh sau benchmark:

- API metadata p95 dưới 500 ms trong tải thông thường.
- Trang danh sách hỗ trợ pagination và không tải toàn bộ artifact.
- Upload file lớn có progress và retry.
- Gamma/DVH chạy bất đồng bộ.
- Worker có thể xử lý nhiều job theo queue.
- Render report không khóa API.
- Trend query có index theo machine_id, metric_key và measured_at.

### 15.3. Khả năng mở rộng

- Object storage tách khỏi database.
- Job queue có thể mở rộng worker.
- Analysis engine có interface plugin.
- Metric key có namespace.
- Report block registry mở rộng được.
- Protocol rule có schema version.
- Biological module có thể thêm model mới mà không sửa QA engine.

### 15.4. Tính quan sát

Health check:

- API health.
- Database connectivity.
- Redis connectivity.
- Object storage connectivity.
- Worker heartbeat.
- Queue depth.
- Failed job count.
- Render failure count.
- Validation failure count.

Mọi log job phải có request_id, job_id, organization_id và subject_id phù hợp; không ghi dữ liệu nhạy cảm vào message log không cần thiết.

---

## 16. Kiểm thử và xác minh

### 16.1. Unit test

Bao phủ:

- Domain model.
- Folder path.
- Organization scoping.
- DICOM metadata parser.
- Dose scaling.
- Geometry checks.
- Gamma configuration.
- BED/EQD2 formulas.
- DVH metrics.
- Rule evaluation.
- Report block selection.
- Snapshot hash.

### 16.2. Contract test

- API request/response.
- gamma.measurement.v1.
- Export CSV/JSON.
- Input Manifest.
- Report template schema.
- Biological scenario schema.

### 16.3. DICOM fixture test

Fixture phải có:

- RTDOSE hợp lệ.
- RTDOSE thiếu scaling.
- RTDOSE sai grid.
- RTSTRUCT đúng Frame of Reference.
- RTSTRUCT không map được.
- RTPLAN có nhiều beam.
- CT và dose khác orientation.
- Dataset có giá trị bất thường.
- DICOM compressed và uncompressed nếu hỗ trợ.

### 16.4. Golden/reference test

Gamma:

- 2D/3D.
- Global/local.
- Absolute/relative.
- Grid khác nhau.
- Dịch chuyển có kiểm soát.
- Vùng dose thấp.
- Biên trường.
- Dữ liệu lỗi.
- Expected pass rate và expected map characteristics.

DVH:

- Hình học đơn giản có kết quả tính bằng tay.
- Structure hình cầu/hộp.
- Dose uniform.
- Dose gradient.
- Dose grid khác spacing.
- Contour ngoài grid.
- Nhiều ROI.

Biological:

- Bộ giá trị BED/EQD2 biết trước.
- So sánh hai phác đồ.
- Đồ thị D.
- Nhiều alpha/beta.
- Recovery/no-recovery scenario.
- Re-irradiation nhiều course.
- Invalid input.

### 16.5. Integration test

- Upload → checksum → validation.
- Validation → analysis queue.
- Worker → result → metrics.
- Result → report snapshot.
- Report → PDF/PNG/CSV.
- Trend point → query → source case.
- Biological scenario → calculation → chart → independent report.
- Archive folder → data remains available.
- Rerun → old result remains.

### 16.6. End-to-end test

Một workflow hoàn chỉnh phải kiểm tra:

1. Tạo organization/site/machine.
2. Tạo folder và QA case.
3. Upload RTDOSE + measurement.
4. Validation.
5. Chọn Gamma configuration.
6. Chạy analysis.
7. Xem map/pass rate/warning.
8. Tạo report tùy chỉnh.
9. Export report.
10. Chạy lại với configuration khác.
11. So sánh revision.
12. Xem trend.

### 16.7. Test-first và dataset thật

- Engine chỉ được merge khi bộ test/reference dataset đạt.
- Dataset thật không phải điều kiện để hoàn thành code phase ban đầu.
- Dataset thật được dùng ở pilot hoặc vận hành có kiểm soát để bổ sung fixture và test case.
- Mỗi lỗi phát hiện từ dataset thật phải được chuyển thành regression test trước khi sửa được coi là hoàn tất.
- Không dùng kết quả test đơn lẻ để tuyên bố toàn bộ hệ thống đã được thẩm định lâm sàng.

---

## 17. CI/CD và triển khai

### 17.1. CI pipeline

Mỗi change chạy:

1. Format/lint.
2. Type check.
3. Unit test.
4. Contract test.
5. DICOM fixture test.
6. Golden test.
7. Integration test.
8. Frontend build.
9. API schema generation.
10. Migration check.
11. Diff/document check.

### 17.2. Build artifact

- Frontend static bundle.
- API image.
- Worker image.
- Render image.
- Migration package.
- Configuration template.
- Test report.
- Dependency inventory.

### 17.3. Migration

- Migration được review bằng test database.
- Migration không làm mất dữ liệu cũ.
- Có backup trước migration pilot/production.
- Có kế hoạch rollback hoặc forward-fix.
- Version schema lưu cùng release.
- Application schema migration chạy trên Railway PostgreSQL bằng Alembic hoặc migration workflow đã chọn ở P0; chỉ dùng một nguồn migration chính thức.
- Không tự sửa các schema/bảng nội bộ do Supabase Auth quản lý.
- API/worker dùng Railway PostgreSQL connection string hoặc private reference variable từ Railway secret; migration không chạy từ frontend.
- Kiểm tra kết nối private networking, TLS, connection limit và pool sizing của Railway PostgreSQL với Railway runtime trước khi chốt production.

### 17.4. Release

Mỗi release ghi:

- Application version.
- API version.
- Engine version.
- DICOM validator version.
- Report renderer version.
- Database schema version.
- Dependency lock hash.
- Test result summary.
- Known limitations.

### 17.5. Public Web Deployment và remote access

#### 17.5.0. Bootstrap từ Railway project hiện có

Không tạo project Railway mới khi chưa có lý do. Dùng project `prolific-learning` (`339f2c50-ddd7-491f-8c4e-da2a2d169502`) làm project triển khai RT-CONNECT và thực hiện theo thứ tự:

1. Cài hoặc dùng Railway CLI phiên bản được pin; không giả định CLI đã có trên máy.
2. Dùng Account/Workspace token để kiểm tra quyền, tạo environment `staging` và provisioning service; không xuất token ra terminal/log.
3. Dùng Project Token hiện có chỉ cho thao tác environment `production` mà token trỏ tới.
4. Điều tra deployment `FAILED` của service `RT-connect`; lưu nguyên nhân và regression/smoke check trước khi deploy lại.
5. Tạo Railway PostgreSQL trong staging, chạy migration baseline và kiểm tra private connection từ backend.
6. Deploy health-only/API shell lên staging trước; chưa deploy production khi source/test/migration chưa tồn tại.
7. Tạo Redis/worker ở phase PSQA Gamma; renderer tách service chỉ khi benchmark hoặc failure isolation yêu cầu.
8. Chỉ promote release đã có manifest từ staging sang production.

Tên biến `.env` nội bộ không được copy nguyên xi vào runtime. Script deployment đọc chúng cục bộ rồi ánh xạ một token tại một thời điểm sang biến mà Railway CLI hỗ trợ. Token Railway không được đưa vào frontend, backend runtime image hoặc bảng database.

#### 17.5.1. Mục tiêu triển khai

RT-CONNECT phải có một URL web để người dùng được tổ chức cho phép truy cập từ xa bằng desktop hoặc mobile browser. Phương án triển khai mục tiêu là Supabase cho Auth, Railway cho PostgreSQL, backend server/API, worker, renderer, queue và public API networking; frontend là static web riêng hoặc được backend phục vụ tùy phương án phát hành; object storage dùng S3-compatible/MinIO được chỉ định.

Railway project được tổ chức tối thiểu thành các backend service:

1. `api`: FastAPI public HTTP service.
2. `postgres`: Railway PostgreSQL service cho database nghiệp vụ, chỉ nhận kết nối private.
3. `worker`: Celery/analysis worker, không public domain.
4. `renderer`: report-render service hoặc worker capability, không public domain.
5. `redis`: Redis Railway service hoặc Redis tương thích cho job queue.

Supabase project cung cấp:

- Supabase Auth cho user identity/session.
- Cấu hình provider, site URL, redirect URL và JWT verification cho đúng environment.

Railway project cung cấp:

- Railway PostgreSQL cho metadata, quan hệ nghiệp vụ, provenance và audit.
- Database connection/private reference variable được cấu hình cho API/worker; không kết nối trực tiếp từ browser.

Mỗi environment dùng Railway environment và Railway PostgreSQL service riêng, cùng với Supabase Auth project riêng hoặc cấu hình được cô lập tương đương. Frontend production phải dùng đúng API URL của environment tương ứng. Nếu bệnh viện yêu cầu không có public inbound trực tiếp, Railway có thể được đặt sau VPN/zero-trust gateway hoặc mô hình private connectivity do tổ chức lựa chọn; đây là biến thể triển khai, không thay đổi contract ứng dụng.

#### 17.5.2. Sơ đồ public edge

~~~text
[Remote browser]
      | HTTPS
      v
[Frontend static host hoặc frontend bundle được API phục vụ]
      | HTTPS
      v
[Railway public API domain + automatic TLS]
      |                         \
      v                          v
[Supabase Auth]          [Railway API service]
                               |
                               v
                      [Railway private network]
                         |       |       |
                         v       v       v
                      [Redis] [Worker] [Renderer]
                               |
                               v
                   [Railway PostgreSQL]
                               |
                               v
                    [S3-compatible object storage]

[Optional Orthanc/DICOMweb] --> [Railway API/Ingestion]

~~~

Frontend và API là các endpoint được public qua HTTPS theo nhu cầu của browser. Railway là application/backend/data plane; PostgreSQL, worker, renderer, Redis, object storage và Orthanc admin không có public domain của RT-CONNECT. API/worker kết nối tới Railway PostgreSQL qua private networking hoặc reference variable được giữ trong Railway secret. Supabase chỉ cung cấp Auth; browser không kết nối trực tiếp tới PostgreSQL, Redis, MinIO/S3, Celery monitor hoặc Orthanc admin. Nếu cần truy cập DICOM từ xa, phải đi qua API/gateway đã kiểm soát, không cấp URL quản trị nội bộ cho browser.

#### 17.5.3. Hợp đồng hạ tầng tối thiểu

- Public domain/custom domain cho frontend; Railway public domain hoặc custom domain cho API. Có thể dùng cùng domain qua path nếu frontend được API phục vụ.
- Railway automatic TLS/custom-domain provisioning hoặc edge riêng nếu topology yêu cầu; certificate phải được kiểm tra và theo dõi.
- Railway private domains/reference variables cho kết nối service-to-service; browser không gọi Railway private domain.
- Environment variables/secrets được cấu hình trong Railway environment hoặc secret store, không commit vào source code.
- Railway PostgreSQL dùng service/database có retention, backup và restore phù hợp; phải xác nhận restore thực tế trước production.
- Redis dùng Railway service hoặc Redis tương thích; queue state không được coi là nguồn dữ liệu nghiệp vụ duy nhất.
- Object storage dùng S3-compatible/MinIO có persistence; không dùng filesystem ephemeral của Railway làm kho artifact chính.
- Upload file lớn đi qua streaming/chunking hoặc cơ chế upload phù hợp, tránh giữ toàn bộ file trong memory của API.
- Job Gamma/DVH/render chạy worker; client theo dõi bằng job status/polling hoặc cơ chế realtime đã được kiểm thử.
- Signed download URL có thời hạn; object storage không anonymous-read.
- Supabase Auth URL, publishable/anon key, JWKS URL/audience và redirect URL tách theo environment; Railway PostgreSQL URL/secret cũng phải tách theo environment.
- API public có rate limit, body limit, request timeout và CORS theo domain thật.
- Migration chạy trước release theo quy trình backup và kiểm tra schema.
- Có staging domain hoặc môi trường staging tách dữ liệu production trước public release.

#### 17.5.4. CI/CD và phát hành public

Pipeline public release tối thiểu:

1. Build frontend/API/worker/render image với version cố định.
2. Chạy test và scan dependency/image theo năng lực hạ tầng.
3. Deploy các service vào Railway staging environment.
4. Chạy smoke test từ browser và API client; `scripts/verify-public-deployment.ps1` có thể tạo public-contract evidence JSON cho health/readiness/schema/version/OpenAPI/web bundle, nhưng không thay authenticated E2E.
5. Kiểm tra Supabase Auth config, Railway PostgreSQL migration/health, queue, upload, analysis và export.
6. Backup Railway PostgreSQL/object storage trước production migration.
7. Deploy Railway production environment theo version manifest và environment variables đã review.
8. Kiểm tra từ mạng ngoài: đăng nhập, tạo case, upload, xem validation, chạy job, xem report, tải export và truy cập Biological Toolkit.
9. Theo dõi log/metrics sau phát hành.
10. Rollback về image/version trước nếu smoke test hoặc monitoring không đạt.

`scripts/create-release-manifest.py` và `scripts/release_manifest.py` là implementation
support cho P19-W01. Tool nhận metadata đã được operator thu thập, hash fixture nằm trong
repository, loại bỏ secret-like value và tạo manifest canonical có `manifest_sha256`.
Manifest ghi riêng SHA nguồn của API/web/worker; nếu working tree bẩn hoặc service SHA
không đồng nhất với `source_sha`, output vẫn được giữ để điều tra nhưng có
`release_gate=RELEASE_BLOCKED` và exit code khác 0. Validator tự tính lại service parity và
gate reasons thay vì tin cờ có sẵn. `--verify-manifest` kiểm tra schema, secret scan và
canonical hash; hash này không phải chữ ký chống giả mạo, nên artifact lưu trữ phải được
bảo toàn qua cơ chế review/retention phù hợp. Tool không gọi Railway, Supabase hoặc PostgreSQL và không thể
thay thế remote E2E, backup/restore, rollback rehearsal hay production promotion.

#### 17.5.5. Kiểm thử remote access

Phải kiểm tra tối thiểu trên một mạng ngoài bệnh viện/server và trên desktop/mobile browser:

- DNS phân giải đúng.
- HTTPS certificate và redirect hoạt động.
- Người dùng có thể mở frontend/public API, đăng nhập/đăng xuất Supabase Auth và truy cập organization của mình.
- Access token Supabase được API xác minh; token hết hạn hoặc sai signature bị từ chối.
- Không thể truy cập dữ liệu organization khác.
- Upload artifact và file lớn không lỗi do proxy timeout/body limit.
- Validation và worker job hoàn thành sau khi browser refresh hoặc mất kết nối tạm thời.
- Report, biểu đồ và file export tải được qua signed URL.
- Biological Toolkit hoạt động độc lập với QA case.
- Reload/deep-link frontend không trả 404 sai route.
- Cảnh báo lỗi không làm lộ stack trace, secret hoặc định danh không cần thiết.
- Restart một service không làm mất dữ liệu hoặc tạo result trùng.
- Backup/restore đã được kiểm tra ở đúng topology triển khai.

#### 17.5.6. Tiêu chí không được coi là public-ready

- Chỉ mở được web trong localhost hoặc mạng LAN.
- Chưa có domain/TLS hoặc certificate hết hạn.
- Database/object storage/Redis/Orthanc bị expose trực tiếp.
- Upload được ở local nhưng timeout trên mạng ngoài.
- Worker hoặc report renderer chỉ chạy bằng tay.
- Không có backup/restore evidence và rollback version.
- Không biết bản release đang chạy gồm engine, schema và frontend version nào.
- Supabase Auth dùng nhầm project/redirect URL/key hoặc Railway PostgreSQL service/URL với environment khác.

---

## 18. Traceability từ nghiệp vụ sang kỹ thuật

| Nhóm nghiệp vụ | Thành phần kỹ thuật |
| :--- | :--- |
| Organization → site → machine → QA case | Organization, Site, Machine, QACase models và API |
| Folder lồng nhau | Folder parent_id, tree API, archive metadata |
| File gốc không đổi | Object storage, SHA-256, Artifact parent lineage |
| PSQA RTDOSE + measurement | Workflow validator, gamma.measurement.v1, Gamma service |
| RTSTRUCT tùy workflow | DICOM role resolution và workflow-specific validator |
| Gamma configuration đầy đủ | AnalysisConfiguration schema và snapshot |
| Metric actual/limit/margin/status | MetricResult và Rule evaluator |
| Report tùy chỉnh | ReportTemplateVersion, ReportBlockConfig, renderer |
| Report revision | ReportRevision và snapshot |
| Trend theo machine | TrendPoint và indexed query |
| QA protocol version | QAProtocolVersion và QAProtocolRule |
| BED/EQD2 | BiologicalCalculationRun và biological engine |
| Đồ thị theo D | BiologicalChart service |
| So sánh phác đồ | Course comparison service |
| Giới hạn liều | DoseLimitEntry |
| Re-irradiation | BiologicalScenario, BiologicalCourse, assumptions |
| Không gắn Biological với QA | Bounded context và API namespace riêng |
| Audit/provenance | AuditEvent, hash và lineage |
| Bộ test engine | Unit, fixture, golden, integration và E2E suite |
| Truy cập web từ xa qua HTTPS | Public web edge, DNS/TLS, reverse proxy, private service network và remote smoke test |
| Google Stitch là nguồn thiết kế | Stitch MCP adapter/workflow, screen ID map, design-to-code checklist; không runtime dependency |
| Supabase chỉ làm Auth | Supabase session/JWT verifier + UserIdentity mapping; không dùng Supabase database cho domain |
| Railway backend và PostgreSQL | Railway API/web/worker/renderer topology, Railway PostgreSQL, private reference variables và migration |
| Hoàn thiện theo module | MOD-00 đến MOD-16, mỗi module có route/API/entity/test/exit criteria trong plan.md |
| Không lộ deployment secret | `.env` ignored, secret store, log redaction và frontend bundle scan |

---

## 19. Quyết định kỹ thuật và điểm cần khóa ở phase 0

### 19.1. Đã chọn làm kiến trúc tham chiếu

- React + TypeScript + Vite.
- Python + FastAPI + Pydantic.
- Supabase Auth cho identity, session và access token; không tự xây password store.
- Railway làm nền tảng triển khai target cho backend API, worker, renderer và Redis/queue nếu dùng Railway cho queue.
- Railway PostgreSQL cho metadata/provenance, schema ứng dụng và audit.
- API/worker kết nối Railway PostgreSQL qua private networking/reference variable và secret phù hợp; không kết nối từ frontend.
- S3-compatible/MinIO được chỉ định cho artifact; không dùng filesystem ephemeral của Railway làm kho chính.
- pydicom + NumPy cho DICOM.
- Gamma engine được bọc qua interface riêng.
- Biological Toolkit tách module và API namespace.
- Docker-based deployment cho development, pilot và production khi phù hợp.
- Railway public networking qua domain/TLS; Railway private networking cho service nội bộ.
- Google Stitch chỉ là công cụ design-time/handoff, không phải runtime dependency.

### 19.2. Cần khóa bằng PoC trước khi triển khai sâu

- Lựa chọn Celery hoặc worker tương đương.
- Cách render PDF tiếng Việt và biểu đồ lớn.
- DICOM compressed transfer syntax cần hỗ trợ.
- DICOM gateway có cần ngay trong pilot hay chỉ upload.
- DVH rasterization/resampling method.
- Cách lưu grid values lớn.
- Benchmark Gamma trên dataset kích thước lớn.
- Quy ước metric key và rule expression.
- Mức hỗ trợ nhiều site/machine trong một organization.

### 19.3. Không được tự ý quyết định trong code

- Không tự đặt tolerance lâm sàng nếu chưa có protocol.
- Không tự chọn alpha/beta mặc định không có source.
- Không tự ghép RTDOSE/RTSTRUCT chỉ bằng PatientID.
- Không tự đổi đơn vị khi thiếu metadata.
- Không tự biến Biological scenario thành prescription.
- Không tự xóa result, report revision hoặc audit history.

---

## 20. Tài liệu tham chiếu kỹ thuật

- DICOM RT Dose Module: https://dicom.nema.org/medical/dicom/2024e/output/chtml/part03/sect_C.8.8.3.html
- DICOM Structure Set Module: https://dicom.nema.org/medical/DICOM/current/output/chtml/part03/sect_C.8.8.5.html
- AAPM TG-142: https://www.aapm.org/pubs/reports/detail.asp?docid=125
- AAPM TG-198: https://www.aapm.org/pubs/reports/detail.asp?docid=215
- AAPM TG-218: https://www.aapm.org/pubs/reports/detail.asp?docid=173
- IAEA Quality Management System for Radiotherapy: https://www.iaea.org/resources/hhc/medical-physics/radiotherapy/quality-management-system
- FastAPI documentation: https://fastapi.tiangolo.com/
- pydicom documentation: https://pydicom.github.io/pydicom/stable/
- PyMedPhys Gamma documentation: https://docs.pymedphys.com/en/stable/users/ref/lib/gamma.html
- Orthanc DICOMweb documentation: https://orthanc.uclouvain.be/book/plugins/dicomweb.html
- Supabase Auth documentation: https://supabase.com/docs/guides/auth
- Supabase JWT and signing keys: https://supabase.com/docs/guides/auth/jwts
- Railway database services: https://docs.railway.com/databases
- Railway public networking and custom domains: https://docs.railway.com/networking/public-networking
- Railway private domains: https://docs.railway.com/networking/domains/working-with-domains
- Railway Redis/databases overview (queue reference): https://docs.railway.com/databases
- Google Stitch overview: https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/
- Google Developers — Introducing Stitch: https://developers.googleblog.com/en/stitch-a-new-way-to-design-uis/

---

## 21. Kết luận

`technical-specification.md` định nghĩa RT-CONNECT thành một hệ thống web gồm hai bounded context:

1. QA Management cho machine QA, PSQA Gamma, DICOM workflow, report và trend.
2. Biological Toolkit độc lập cho các phép tính sinh học, scenario, phác đồ và knowledge library.

Kiến trúc giữ nguyên quyền sử dụng nghiệp vụ ngang nhau, không xây dựng phân quyền theo hành động, đồng thời vẫn giữ provenance, version, checksum và audit để tái hiện kết quả. Việc triển khai phải đi theo test-first, sau đó dùng dataset thật ở pilot và vận hành để bổ sung regression test và hoàn thiện workflow.

Hệ thống được thiết kế để phát hành qua public web edge cho truy cập từ xa, nhưng chỉ frontend/API được expose qua HTTPS; dữ liệu và các service nội bộ vẫn nằm trong private network. Google Stitch project `RT-connect` được đọc/chỉnh qua MCP ở design-time; screen ID là đầu mối traceability, không phải thành phần runtime hay nguồn thay thế cho API contract, kiểm thử và review frontend. Repository không cần tái tạo `UI-UX.md`.

Trong deployment target, Supabase là auth/identity plane cho Supabase Auth, còn Railway là application/backend/data plane cho backend API/server, PostgreSQL, worker, renderer và queue. Frontend là static web host riêng hoặc static bundle được backend phục vụ. Không kết nối browser trực tiếp tới Railway PostgreSQL; mọi truy cập database đi qua backend/private networking.

Baseline Railway hiện có mới gồm project/environment/service và một deployment thất bại; chưa có PostgreSQL hoặc source application. Vì vậy phase đầu phải dựng staging, migration, health endpoint và CI/CD trước khi sử dụng production token để deploy release thật.
