# YÊU CẦU UI/UX

## Dự án RT-CONNECT

**Tên tài liệu:** UI-UX.md  
**Phiên bản:** 0.3  
**Mục đích:** Làm tài liệu đầu vào cho Google Stitch để thiết kế giao diện, prototype và design system của RT-CONNECT  
**Đối tượng sử dụng:** Bác sĩ xạ trị, kỹ sư vật lý xạ trị và các thành viên chuyên môn trong bệnh viện/tổ chức  
**Ngôn ngữ giao diện mặc định:** Tiếng Việt; chuẩn bị khả năng mở rộng tiếng Anh  
**Nền tảng:** Website desktop-first, responsive trên tablet và mobile browser  
**Kênh truy cập:** Website truy cập từ xa qua HTTPS; Supabase Auth dùng cho đăng nhập/session; Railway là nền tảng backend API/server, PostgreSQL, worker và renderer

Tài liệu này mô tả sản phẩm và trải nghiệm người dùng cần được thiết kế. Google Stitch dùng để tạo thiết kế và prototype; thiết kế sau đó phải được handoff cho frontend và kết nối với API thật. Không đưa dữ liệu bệnh nhân, DICOM thật hoặc thông tin nhận dạng thật vào Google Stitch.

---

## 1. Tóm tắt sản phẩm

RT-CONNECT là một website chuyên môn cho xạ trị, có hai khu vực lớn:

1. **QA Management:** quản lý hồ sơ QA, machine QA, PSQA Gamma, validation dữ liệu, report, trend và QA protocol.
2. **Biological Toolkit:** công cụ tính BED/EQD2, đồ thị, so sánh phác đồ, giới hạn liều, protocol/knowledge library, re-irradiation và bù fraction.

Biological Toolkit phải là một tab/khu vực độc lập, không tự liên kết với QA case, hồ sơ bệnh nhân, RT Plan hoặc clinical order.

Website phải tạo cảm giác là một công cụ chuyên môn đáng tin cậy, rõ ràng và hiệu quả cho công việc hằng ngày của bác sĩ và kỹ sư. Giao diện cần hỗ trợ người dùng xem nhanh tổng quan, đi sâu vào dữ liệu, hiểu cảnh báo và truy ngược kết quả về input/configuration/protocol.

### 1.1. Mục tiêu trải nghiệm

- Tìm được một QA case hoặc report trong vài thao tác.
- Nhìn thấy ngay organization, site, machine và folder hiện tại.
- Tạo case, upload dữ liệu, kiểm tra validation và chạy analysis theo một luồng tự nhiên.
- Không phải nhớ cấu trúc API hoặc tên file kỹ thuật để sử dụng hệ thống.
- Xem được cả kết quả tóm tắt lẫn chi tiết DICOM/measurement/configuration.
- Phân biệt rõ kết quả, cảnh báo, input thiếu và lỗi kỹ thuật.
- Tạo report theo cách riêng của bệnh viện.
- Theo dõi trend và đi ngược từ biểu đồ về QA case/report gốc.
- Sử dụng Biological Toolkit như một workspace tính toán độc lập.
- Làm việc từ xa trên desktop hoặc mobile browser mà không mất ngữ cảnh.

### 1.2. Không phải mục tiêu của UI

- Không thay thế TPS, PACS, OIS hoặc bệnh án điện tử.
- Không sửa RT Plan, prescription, MLC hoặc thông số máy điều trị.
- Không tạo clinical order.
- Không tự đưa ra quyết định điều trị.
- Không hiển thị Biological calculation như một prescription.
- Không thiết kế phân cấp bác sĩ–kỹ sư hoặc menu khác nhau theo chức danh.

---

## 2. Người dùng mục tiêu

### 2.1. Kỹ sư vật lý xạ trị

Nhu cầu chính:

- Tạo và tổ chức QA case.
- Upload DICOM và measurement.
- Kiểm tra Input Manifest và validation.
- Chọn protocol, cấu hình Gamma và chạy analysis.
- Xem map, pass rate, metric, warning và provenance.
- Theo dõi trend của machine.
- Tạo report và template tùy chỉnh.
- Xây dựng/tra cứu QA protocol.

### 2.2. Bác sĩ xạ trị

Nhu cầu chính:

- Xem nhanh tình trạng QA và report.
- Xem chi tiết metric, cảnh báo và trend.
- Tra cứu protocol, giới hạn và knowledge library.
- Sử dụng BED/EQD2, so sánh phác đồ và re-irradiation scenario.
- Export report hoặc calculation report để thảo luận chuyên môn.

### 2.3. Thành viên chuyên môn khác

Nhu cầu chính:

- Tìm kiếm dữ liệu, report, protocol và kiến thức.
- Xem các phép tính và giả định.
- Ghi chú, so sánh và export nội dung cần thiết.

### 2.4. Nguyên tắc chung về người dùng

- Các thành viên trong cùng organization có cùng navigation và cùng bộ chức năng nghiệp vụ. UI không được ẩn chức năng dựa trên chức danh bác sĩ hay kỹ sư.
- Supabase Auth chỉ cung cấp identity/session. UI không thiết kế role badge, role-based menu hoặc action permission matrix.
- Organization context dùng để xác định dữ liệu đang xem; không dùng để tạo phân cấp người dùng.

---

## 3. Định hướng hình ảnh và cảm giác giao diện

### 3.1. Phong cách tổng thể

Thiết kế theo hướng **clinical professional workspace**:

- Hiện đại, chính xác, gọn và có mật độ thông tin cao vừa phải.
- Tin cậy nhưng không nặng nề như phần mềm hành chính.
- Ưu tiên bảng, biểu đồ, filter, breadcrumb, panel và drill-down.
- Không dùng phong cách quảng cáo, mạng xã hội hoặc dashboard tài chính nhiều hiệu ứng.
- Không lạm dụng gradient, animation, glassmorphism hoặc màu neon.
- Cảnh báo phải nổi bật nhưng không biến toàn bộ màn hình thành màu đỏ.

### 3.2. Màu sắc đề xuất

Google Stitch có thể tinh chỉnh palette nhưng phải giữ ý nghĩa màu nhất quán:

| Ý nghĩa | Màu gợi ý | Cách sử dụng |
| :--- | :--- | :--- |
| Primary | Navy/blue đậm | Navigation, heading quan trọng, nút chính |
| Secondary | Teal/xanh ngọc | Phân tích, liên kết, trạng thái đang chọn |
| Surface | Trắng, xám rất nhạt | Nền, card, panel |
| Text | Slate/xám xanh đậm | Nội dung chính và metadata |
| Success | Xanh lá dịu | Kết quả đạt rule |
| Warning | Amber/vàng cam | Cảnh báo cần xem xét |
| Error | Đỏ trầm | Input invalid hoặc lỗi không thể tiếp tục |
| Info | Xanh dương nhạt | Giải thích, provenance, hướng dẫn |

Không dùng màu làm cách duy nhất để truyền đạt trạng thái; mọi badge/trạng thái phải có text hoặc icon kèm theo.

### 3.3. Typography và mật độ thông tin

- Ưu tiên font hỗ trợ tiếng Việt rõ ràng như Inter, Noto Sans hoặc font tương đương.
- Heading phân cấp rõ; không dùng quá nhiều cỡ chữ.
- Số liệu Gamma, metric, dose và BED/EQD2 cần hiển thị dễ đọc, căn chỉnh nhất quán.
- Dữ liệu kỹ thuật dài như UID, checksum, filename dùng kiểu chữ dễ copy và có nút copy.
- Desktop có thể hiển thị bảng và panel song song.
- Mobile chuyển bảng rộng thành card/stack hoặc cho phép cuộn ngang có chủ đích.
- Không ép toàn bộ metric vào một card nhỏ.
- Metric quan trọng cần có giá trị, đơn vị, limit, margin, status và giải thích ngắn.
- Nội dung nâng cao có thể nằm trong accordion/drawer nhưng không được xóa khỏi hệ thống thông tin.

---

## 4. Khung ứng dụng chung

### 4.1. Public landing page

Đây là trang giới thiệu sản phẩm trước khi đăng nhập; không hiển thị dữ liệu QA hoặc dữ liệu bệnh nhân.

Thành phần:

- Logo RT-CONNECT.
- Headline: **“Kết nối dữ liệu QA xạ trị, phân tích và tri thức chuyên môn trong một workspace.”**
- Subheadline giải thích QA Management và Biological Toolkit.
- Nút chính: **Đăng nhập**.
- Nút phụ: **Xem tổng quan tính năng**.
- Hình minh họa dashboard bằng dữ liệu synthetic.
- Bốn điểm nổi bật: QA archive; DICOM/input validation và Gamma; report/trend; Biological Toolkit.
- Phần giải thích truy cập từ xa qua HTTPS.
- Footer: phiên bản, tài liệu hướng dẫn, hỗ trợ và thông tin tổ chức nếu có.

Landing page không được đưa ra tuyên bố kiểu “đảm bảo an toàn điều trị” hoặc “tự động quyết định lâm sàng”.

### 4.2. Top bar sau đăng nhập

Top bar cố định gồm:

1. Logo RT-CONNECT và nút thu gọn sidebar.
2. Breadcrumb của trang hiện tại.
3. Organization selector.
4. Site selector khi trang cần site.
5. Machine selector hoặc machine context khi đang ở workflow theo máy.
6. Global search.
7. Job Center hiển thị analysis/render đang chạy.
8. Help/guide.
9. Avatar, tên hiển thị, profile và logout.

Organization/site/machine context phải luôn dễ nhìn. Nếu user chuyển context, giao diện phải hỏi xác nhận khi đang có form chưa lưu.

### 4.3. Sidebar navigation chính

Sidebar có các tab/khu vực sau:

1. **Trang chủ**
2. **QA Management**
   - Tổng quan QA.
   - QA Archive.
   - Machines.
   - Machine QA.
   - PSQA Gamma.
   - Reports.
3. **Trend**
4. **QA Protocol Library**
5. **Biological Toolkit**
   - Overview.
   - BED & EQD2.
   - Đồ thị theo tổng liều D.
   - So sánh phác đồ.
   - Re-irradiation.
   - Bù fraction.
   - Giới hạn liều.
   - Protocol điều trị.
   - Knowledge Library.
   - Lịch sử tính toán.
6. **Hoạt động và lịch sử**
7. **Cài đặt cá nhân / tổ chức**

Sidebar phải giữ cùng cấu trúc cho bác sĩ, kỹ sư và thành viên chuyên môn. Không tạo sidebar riêng theo chức danh.

### 4.4. Quick action và global search

Nút **Tạo mới** mở các lựa chọn: tạo QA case, upload artifact, tạo Machine QA, chạy PSQA Gamma, tạo report, tạo biological scenario và tạo folder.

Global search tìm được QA case, folder, machine/site, artifact filename/checksum, report/revision, QA protocol, biological scenario và knowledge content. Kết quả phải hiển thị loại record, organization/site/machine, thời gian, trạng thái dữ liệu và đường dẫn mở record.

---

## 5. Sitemap và danh sách trang

Tên route dưới đây là gợi ý để thống nhất thiết kế; frontend có thể điều chỉnh route nhưng không được bỏ màn hình nghiệp vụ.

```text
Public
├── Landing page
├── Login / Sign in
├── Password recovery / Magic link result
└── Auth error / Session expired

Application shell
├── Home dashboard
├── QA Management
│   ├── QA overview
│   ├── QA archive / folder browser
│   ├── New folder
│   ├── New QA case
│   ├── QA case detail
│   │   ├── Overview
│   │   ├── Inputs & Input Manifest
│   │   ├── Validation
│   │   ├── Analysis runs
│   │   ├── Reports
│   │   └── History / provenance
│   ├── Artifact upload/detail
│   ├── Machine list/detail
│   ├── Machine QA workspace
│   ├── PSQA Gamma setup/running/result
│   └── Report viewer / Report Builder
├── Trend dashboard
├── QA Protocol Library
├── Biological Toolkit
│   ├── Biological overview
│   ├── BED & EQD2 calculator
│   ├── BED/EQD2 graph by total dose D
│   ├── Treatment plan comparison
│   ├── Dose limit library
│   ├── Treatment protocol library
│   ├── Knowledge library
│   ├── Re-irradiation calculator
│   ├── Fraction compensation calculator
│   └── Biological calculation history/report
├── Activity / audit history
└── Settings / profile / help
```

---

## 6. Yêu cầu chi tiết từng trang

### 6.1. Login và authentication

Thiết kế các trạng thái:

- Login bằng email/password hoặc phương thức được bật trong Supabase Auth.
- Magic link/OTP nếu được bật.
- Password recovery.
- Email chưa xác thực nếu provider yêu cầu.
- Session expired.
- Sai email/password.
- Supabase Auth unavailable.
- Redirect về trang trước sau khi đăng nhập thành công.

Yêu cầu UI:

- Form đơn giản, rõ ràng, không đưa thông tin kỹ thuật Railway/Supabase vào giao diện người dùng.
- Hiển thị lỗi thân thiện, không lộ stack trace hoặc token.
- Có loading state khi submit.
- Có link trợ giúp và hướng dẫn liên hệ người phụ trách organization.
- Không có trường role bác sĩ/kỹ sư trong form login.

### 6.2. Trang chủ — Home Dashboard

Trang chủ là workspace tổng quan sau đăng nhập.

#### Bố cục

1. **Header context:** organization, site và khoảng thời gian.
2. **Quick actions:** tạo case, upload, chạy Gamma, mở Biological Toolkit.
3. **Summary cards:** QA case gần đây; analysis/job đang chạy; validation warning; report gần đây; số machine đang theo dõi.
4. **Trend snapshot:** biểu đồ ngắn của machine/metric được chọn.
5. **Recent activity:** upload, validation, analysis, report, protocol và calculation mới nhất.
6. **Shortcut modules:** QA Management, Trend, Protocol Library, Biological Toolkit.

#### Hành vi

- Click một summary card mở trang chi tiết tương ứng.
- Job đang chạy có progress/status và link tới Job Center.
- Warning hiển thị số lượng và loại; click mở đúng artifact/validation/analysis.
- Empty organization có hướng dẫn tạo site/machine/case đầu tiên.
- Không dùng điểm “health score” tổng hợp gây hiểu nhầm rằng hệ thống tự kết luận an toàn điều trị.

#### Dữ liệu mẫu cho Stitch

- Organization: `Bệnh viện Demo`.
- Site: `Cơ sở Trung tâm`.
- Machine: `Elekta Evo - Linac 01`.
- QA case: `QA-2026-001`.

Gắn nhãn dữ liệu mẫu là **Synthetic demo data**.

### 6.3. QA Overview

Trang này tóm tắt hoạt động QA theo organization/site/machine.

Thành phần:

- Bộ lọc site, machine, QA type, chu kỳ và khoảng thời gian.
- Số case Daily/Monthly/Annual/Custom.
- Số case có artifact thiếu hoặc warning.
- Số analysis gần đây.
- Trend summary.
- Nút tạo QA case và mở QA Archive.
- Table các case cần xem, có link drill-down.

### 6.4. QA Archive và Folder Browser

Đây là trang có mental model giống file manager nhưng có metadata nghiệp vụ.

#### Bố cục desktop

- **Cột trái:** cây folder lồng nhau.
- **Khu vực giữa:** danh sách folder/case/report.
- **Panel phải:** metadata record đang chọn.
- Breadcrumb phía trên.

#### Chức năng

- Tạo folder và folder con.
- Đặt tên tự do.
- Đổi tên.
- Di chuyển.
- Archive.
- Upload vào folder/case.
- Tạo QA case trong folder.
- Chuyển đổi list view và compact view.
- Search và filter theo site, machine, QA type, cycle, protocol, ngày và trạng thái dữ liệu.
- Sort theo tên, ngày, machine, loại QA hoặc lần cập nhật.
- Export danh sách.

#### Cột dữ liệu đề xuất

- Tên.
- Loại record.
- Machine/site.
- QA type.
- Ngày đo.
- Protocol version.
- Latest analysis.
- Latest report.
- Data status.
- Updated by/updated at.

Folder archive chỉ ẩn khỏi danh sách mặc định; không dùng wording “delete permanently”.

### 6.5. Tạo QA Case

Thiết kế dạng form nhiều bước để giảm lỗi nhập liệu. Đây là stepper UI, không phải clinical state machine.

#### Bước 1 — Basic information

- Organization, site/hospital và machine.
- QA type: Machine QA, PSQA Gamma, Visual Dose Review, DVH/Plan Review hoặc Custom.
- QA cycle: Daily, Monthly, Annual hoặc Custom.
- Tên case, ngày đo, ghi chú và folder lưu trữ.

#### Bước 2 — Protocol

- Chọn QA protocol và protocol version.
- Hiển thị mô tả, source, rule và giới hạn của version.
- Nếu workflow cho phép không chọn protocol, hiển thị rõ `No protocol selected`.

#### Bước 3 — Files/input

- Upload artifact.
- Chọn logical role.
- Hiển thị yêu cầu file theo QA type.
- Hiển thị RTDOSE/measurement bắt buộc cho PSQA Gamma.
- Hiển thị RTSTRUCT tùy chọn cho phantom/plane Gamma.

#### Bước 4 — Review

- Tóm tắt metadata.
- Danh sách file.
- Validation pre-check.
- Cảnh báo thiếu input.
- Nút tạo case.

Có thể quay lại bước trước và sửa metadata trước khi lưu.

### 6.6. QA Case Detail

Header của case gồm tên/case identifier, organization/site/machine, QA type/cycle, ngày đo, folder breadcrumb, protocol/version và các nút upload, run analysis, create report, export, archive.

Các tab trong case:

1. **Overview:** tóm tắt case, metric gần nhất, warning và report gần nhất.
2. **Inputs & Manifest:** artifact, role, metadata, checksum, DICOM summary và measurement summary.
3. **Validation:** lịch sử validation, warning và invalid reason.
4. **Analysis Runs:** các lần chạy, configuration, engine version, result và job status.
5. **Reports:** report revision, preview, export và template.
6. **History / Provenance:** timeline thay đổi và lineage.

Các tab chỉ là cách tổ chức thông tin; không tạo quy trình phê duyệt hoặc phân cấp người dùng.

### 6.7. Artifact Upload và Input Manifest

#### Khu vực upload

- Drag-and-drop và chọn file từ máy.
- Upload progress, pause/retry nếu phù hợp.
- Hiển thị filename, size, media type và upload time.
- Cho phép upload nhiều file.
- Báo file trùng hoặc checksum trùng.

#### Input Manifest panel

Hiển thị rõ file name, checksum, modality, SOP Instance UID, Study/Series UID, Frame of Reference UID, machine/phantom/detector, reference/comparison dataset, unit/dose scaling, grid spacing/origin/orientation, protocol version và logical role.

Metadata kỹ thuật dài phải có `Copy` và `View full value`.

#### Validation message

- `Valid` — đủ điều kiện theo workflow đã chọn.
- `Warning` — có vấn đề cần xem xét.
- `Invalid` — không được dùng để tạo kết quả phân tích hợp lệ.
- `Missing required input` — còn thiếu file hoặc metadata bắt buộc.

Không thiết kế nút `Auto fix` nếu hệ thống chưa có phép sửa an toàn và có thể tái hiện.

### 6.8. Validation Detail

Bố cục gồm summary banner; validation checks theo nhóm file, DICOM metadata, geometry, unit, reference/comparison và measurement; table `Check | Actual | Expected/Requirement | Result | Explanation`; technical details dạng expandable; link tới artifact; nút chạy lại validation và hướng dẫn sửa input.

Nếu dữ liệu chưa đủ, giao diện phải nói rõ thiếu gì; không dùng wording mơ hồ như “analysis failed” khi nguyên nhân là thiếu RTDOSE hoặc measurement.

### 6.9. Machine List và Machine Detail

#### Machine list

- Card/table theo site.
- Display name và machine stable identifier.
- Manufacturer/model nếu có.
- Số QA case và latest QA date.
- Trend shortcut và protocol đang dùng.

#### Machine detail

- Machine header.
- Summary metric.
- QA frequency summary.
- Trend preview.
- Maintenance/event marker.
- List QA case theo thời gian.
- Link tới Machine QA workspace.

Đổi display name không được làm mất continuity của trend; stable identifier nằm trong panel thông tin mở rộng.

### 6.10. Machine QA Workspace

Trang phục vụ Daily/Monthly/Annual/Custom Machine QA.

Thành phần:

- Chọn machine và protocol.
- Nhập hoặc import measurement.
- Bảng test item.
- Cột actual, unit, limit, margin, status và note.
- Có thể thêm/bớt test item theo protocol.
- Summary card cho số item đạt, warning và fail.
- Trend preview của item đang chọn.
- Nút lưu result, tạo report và export.

Status chỉ mô tả kết quả theo rule của protocol; UI không được biến thành kết luận an toàn tuyệt đối.

### 6.11. PSQA Gamma Setup

Thiết kế thành một workspace có stepper hoặc panel theo 4 phần:

1. **Inputs**
2. **Gamma Configuration**
3. **Review & Run**
4. **Result**

#### Inputs panel

- Reference dose.
- Evaluation/measurement dataset.
- Measurement contract `gamma.measurement.v1`.
- RTDOSE bắt buộc.
- Measurement/compare dataset bắt buộc.
- RTPLAN tùy chọn khi cần beam/isocenter/field context.
- RTSTRUCT tùy chọn cho phantom/plane; hiển thị là không bắt buộc trong workflow này.
- Geometry/reference summary.

#### Gamma Configuration panel

Cho phép user xem và tùy chỉnh:

- Dose difference.
- Distance-to-agreement.
- Absolute/relative dose.
- Global/local normalization.
- Reference dose level.
- Dose threshold.
- Pass threshold.
- 2D/3D.
- Per-field/composite.
- ROI/mask.
- Alignment/shift.
- Isocenter plane.
- Search distance.
- Interpolation/resampling.
- Maximum output gamma.

Các field cần có tooltip giải thích, unit rõ ràng và nút xem advanced options. Không chỉ hiển thị chuỗi `3%/3 mm` mà bỏ qua các tham số còn lại.

#### Review & Run panel

- Tóm tắt input.
- Tóm tắt configuration.
- Cảnh báo validation.
- Engine version.
- Protocol version.
- Ước lượng job state nếu có.
- Nút `Run analysis`.
- Xác nhận trước khi chạy nếu input có warning.

Không cho chạy khi thiếu RTDOSE hoặc measurement bắt buộc. Không tự đoán cột, unit, geometry hoặc reference/evaluation role.

### 6.12. PSQA Gamma Running

Trang trạng thái job cần có:

- Job identifier.
- Case name.
- Progress theo bước: preparing input, validating, calculating, rendering result.
- Thời gian bắt đầu.
- Nút quay lại case mà không hủy job.
- Nút refresh status.
- Thông báo nếu browser mất kết nối.
- Lỗi kỹ thuật dễ hiểu và correlation ID có nút copy.

Sau refresh browser, user vẫn xem được job đang chạy hoặc kết quả đã hoàn tất.

### 6.13. PSQA Gamma Result

#### Header

- Result status.
- Pass rate.
- Pass threshold.
- Reference/evaluation labels.
- 2D/3D, global/local, absolute/relative.
- Protocol/configuration/engine version.
- Created by/created at.
- Nút tạo report, export và rerun.

#### Nội dung chính

1. Gamma map lớn, zoom/pan và legend.
2. Dose map/reference map/evaluation map nếu có.
3. Profile hoặc slice selector.
4. Pass-rate summary.
5. Histogram/distribution nếu engine cung cấp.
6. Warning panel.
7. Input and geometry summary.
8. Configuration drawer.
9. Provenance/lineage drawer.
10. Compare với result/revision khác.

Map phải có color legend, unit, scale, mask/ROI và note về normalization. Không dùng màu map mà không có legend.

### 6.14. Analysis Run History và Compare

Table các run gồm:

- Run ID.
- Created time.
- Input manifest version.
- Configuration summary.
- Protocol version.
- Engine version.
- Result status.
- Pass rate/metric chính.
- Warning count.
- Report link.

Chức năng compare hiển thị configuration diff, input diff, engine/protocol version diff, metric diff, map side-by-side/overlay nếu phù hợp và warning diff.

Rerun tạo result mới; UI không được thể hiện như ghi đè result cũ.

### 6.15. Trend Dashboard

#### Bộ lọc

- Organization/site.
- Machine.
- QA type.
- Daily/Monthly/Annual/Custom.
- Metric.
- Protocol version.
- Detector/array/film.
- Phantom.
- Energy/mode.
- Khoảng thời gian.

#### Biểu đồ

- Line chart theo thời gian.
- Baseline/tolerance/action level nếu protocol cung cấp.
- Điểm warning/outlier.
- Sự kiện bảo trì/thay detector/thay protocol.
- Tooltip có actual, limit, margin, status, date và link case.
- Zoom khoảng thời gian.
- Export chart/data.

#### Bảng drill-down

- Mỗi điểm biểu đồ click được.
- Mở QA case, report hoặc analysis run tương ứng.
- Không xóa outlier khỏi biểu đồ; nếu user ẩn điểm, phải hiển thị filter đang áp dụng.

### 6.16. Report Library và Report Viewer

Report Library có template list, template version, mục đích sử dụng, organization/site/machine scope, last updated, recent report và nút create/copy/edit/preview.

Report Viewer có report title/metadata, nội dung report, input/protocol/configuration/engine version, revision selector, compare revision, export PDF/PNG/CSV/JSON khi được hỗ trợ và nút mở source QA case/analysis run.

### 6.17. Report Builder

Report Builder phải cho phép tùy chỉnh toàn diện theo yêu cầu nghiệp vụ.

#### Bố cục editor desktop

- **Panel trái:** block library.
- **Canvas giữa:** report page/canvas.
- **Panel phải:** properties của block đang chọn.
- **Top toolbar:** save revision, preview, compare, export, undo/redo, zoom.

#### Block library

- Title/text.
- Organization/site/machine.
- QA case metadata.
- Input file/manifest.
- Metric table.
- Actual/limit/margin/status.
- Gamma map.
- Dose profile.
- DVH.
- Trend chart.
- Comparison table.
- BED/EQD2.
- Fractionation scenario.
- Re-irradiation scenario.
- User note.
- Provenance/history.
- Image/attachment.

#### Tùy chỉnh

- Thêm/bớt block.
- Ẩn/hiện block.
- Đổi label/title.
- Di chuyển và resize block.
- Chọn metric.
- Chọn khoảng thời gian trend.
- Điều kiện hiển thị block.
- Đổi thứ tự và nhóm section.
- Chọn layout một hoặc nhiều cột.
- Lưu template version.
- Preview trước export.

UI phải cho user thấy rõ khi một block bị ẩn hoặc metric bị bỏ khỏi report. Không tự reset layout khi reload.

#### Revision

- Mỗi lần save thay đổi quan trọng tạo revision mới.
- Revision cũ xem lại được.
- Hiển thị người sửa, thời gian và summary thay đổi.
- Report cũ mở lại đúng snapshot.

### 6.18. QA Protocol Library

Trang gồm protocol catalog, search/filter theo QA type/machine/site/source, protocol detail, rule/metric table, source/reference, version timeline, diff giữa hai version và tạo version mới.

Protocol tham khảo và protocol nội bộ phải có badge/label khác nhau. UI không được làm user nhầm một reference thành protocol đang áp dụng.

### 6.19. Biological Toolkit Overview

Trang mở đầu của tab Biological Toolkit phải tách biệt về màu phụ, breadcrumb và navigation so với QA Management nhưng vẫn dùng chung design system.

Nội dung:

- Giới thiệu ngắn: công cụ tính toán và tra cứu.
- Quick cards: BED/EQD2; đồ thị theo tổng liều D; so sánh phác đồ; re-irradiation; bù fraction; giới hạn liều; protocol/knowledge.
- Recent calculations.
- Saved scenarios.
- Cảnh báo về assumptions.
- Nút tạo scenario mới.

Banner cố định: **“Kết quả là calculation/scenario tham khảo; không phải prescription hoặc clinical order.”**

### 6.20. BED & EQD2 Calculator

#### Input panel

- Tổng liều `D`.
- Số fraction `n`.
- Liều mỗi fraction `d`.
- Alpha/beta.
- Mô/tissue/OAR/target.
- Model.
- Source/reference.
- Ghi chú và assumption.

#### Result panel

- BED.
- EQD2.
- Công thức đã dùng.
- Đơn vị.
- Input summary.
- Source.
- Assumption.
- Cảnh báo khi input không hợp lý hoặc thiếu source.

Màn hình phải hiển thị công thức dễ đọc, không chỉ hiển thị con số cuối.

### 6.21. Đồ thị BED/EQD2 theo tổng liều D

Thành phần:

- Slider/input cho tổng liều D.
- Số fraction.
- Một hoặc nhiều alpha/beta.
- Chọn BED, EQD2 hoặc cả hai.
- Chart legend.
- Hover tooltip đọc giá trị tại D.
- So sánh target và OAR.
- Bảng dữ liệu bên dưới đồ thị.
- Export chart/data.

Đồ thị phải thể hiện rõ đơn vị, range, model và assumptions. Dữ liệu demo phải ghi là illustrative.

### 6.22. So sánh phác đồ điều trị

Thiết kế dạng hai hoặc nhiều cột phác đồ:

- Tên phác đồ.
- Clinical scenario/bệnh lý.
- Tổng liều.
- Số fraction.
- Liều mỗi fraction.
- Thời gian điều trị.
- Tissue/OAR/target.
- Alpha/beta.
- Source.

Kết quả:

- BED từng phác đồ.
- EQD2 từng phác đồ.
- Chênh lệch.
- Bảng so sánh.
- Đồ thị so sánh.
- Cảnh báo nếu hai phác đồ không phù hợp để so sánh trực tiếp.

### 6.23. Dose Limit Library

Table/card có filter theo bệnh lý, vị trí giải phẫu, OAR/target, kỹ thuật, metric, số fraction, mức độ bằng chứng và source/date.

Detail drawer hiển thị:

- Giá trị giới hạn.
- Đơn vị.
- Điều kiện áp dụng.
- Source paper/guideline.
- Ngày cập nhật.
- Loại nội dung: reference, internal hoặc user-entered.
- Limitation.

Không dùng từ “safe limit” nếu nguồn chỉ là giá trị tham khảo.

### 6.24. Treatment Protocol và Knowledge Library

#### Catalog page

- Search.
- Filter bệnh lý, vị trí, kỹ thuật, evidence level và date.
- Card có title, summary, tags, source và last updated.

#### Detail page

- Tên bệnh lý/scenario.
- Phác đồ tham khảo.
- Tổng liều/fraction.
- Contouring guidance.
- Target/OAR criteria.
- Alpha/beta.
- Công thức/lý thuyết.
- Paper/guideline/DOI/URL.
- Tóm tắt nội bộ.
- Mức độ bằng chứng.
- Giới hạn áp dụng.
- Version/history.

UI phải phân biệt rõ `reference knowledge` với `local protocol`; không hiển thị nội dung như một order cho bệnh nhân.

### 6.25. Re-irradiation Calculator

Đây là màn hình Biological Toolkit quan trọng, phải được thiết kế chi tiết nhưng vẫn tách khỏi QA case.

#### Bố cục desktop

- **Cột trái:** danh sách course.
- **Khu vực giữa:** timeline và bảng dose/fraction.
- **Cột phải:** tissue/alpha-beta/recovery assumptions.
- **Phần dưới:** kết quả, comparison và warnings.

#### Course editor

Mỗi course có course name, date hoặc interval, tổng liều, số fraction, liều mỗi fraction, tissue/OAR/target, alpha/beta, source, volume nếu có, spatial dataset/structure nếu user chủ động nhập và ghi chú.

#### Assumption panel

- Recovery assumption.
- Time interval.
- Repopulation assumption nếu model hỗ trợ.
- Volume effect nếu model hỗ trợ.
- Dose heterogeneity assumption.
- Registration/spatial mapping status.
- Scalar-only hoặc spatial mode.
- User note.

#### Result panel

- BED/EQD2 từng course.
- Tổng BED/EQD2 theo scenario.
- So sánh no-recovery và recovery.
- So sánh nhiều scenario.
- Chênh lệch giữa phương án.
- Cảnh báo thiếu time, volume, structure hoặc registration.
- Hiển thị model, source và limitation cạnh kết quả.

#### Quy tắc UI bắt buộc

- Nếu không có spatial registration hợp lệ, hiển thị banner **“Scalar comparison only — chưa thực hiện cộng liều theo không gian.”**
- Không hiển thị nút hoặc wording khiến user nghĩ hệ thống tự chọn phương án điều trị.
- Có thể save/export scenario độc lập.
- Không có trường chọn QA case hoặc patient case mặc định.
- Có thể nhập dataset riêng trong Biological Toolkit nhưng phải hiển thị nguồn và checksum nếu có.

### 6.26. Fraction Compensation / Bù fraction

Input:

- Lịch ban đầu.
- Số fraction đã thực hiện.
- Liều đã thực hiện.
- Fraction bị thiếu/gián đoạn.
- Fraction còn lại.
- Tổng thời gian điều trị.
- Mục tiêu tính toán.

Output:

- Các phương án scenario.
- BED/EQD2 so sánh.
- Thay đổi tổng liều/fraction/time.
- Assumptions.
- Warning.
- Export calculation report.

Banner cố định: **“Đây là scenario/proposal để thảo luận chuyên môn, không phải prescription.”**

### 6.27. Biological Calculation History và Report

Table gồm scenario name, created at/by, model, alpha/beta, number of courses, result summary, assumption count, warning count và version.

Calculation detail có input snapshot, formula/model, source, assumptions, result table/chart, revision/history và export independent report.

### 6.28. Activity và History

Timeline cho upload/import/export, folder change, validation, analysis run/rerun, report/template revision, protocol revision, biological scenario/calculation và knowledge/dose limit update.

Timeline phải có user, thời gian, object, hành động và link mở record. Đây là lịch sử giải trình, không phải UI phân quyền.

### 6.29. Settings và Help

Settings gồm profile/display name/timezone, organization context, site/machine metadata, default UI preferences, notification/job preferences và export preferences.

Không hiển thị secret Railway, service key Supabase hoặc database credential.

Help gồm hướng dẫn bắt đầu, DICOM/Input Manifest guide, Gamma configuration guide, Report Builder guide, Biological Toolkit guide, glossary, known limitations và contact/support.

---

## 7. Thành phần UI cần thiết

Google Stitch cần tạo component inventory gồm các component có biến thể:

- App shell, sidebar, top bar và breadcrumb.
- Organization/site/machine selector.
- Global search và Job Center.
- Button primary/secondary/ghost/danger.
- Icon button có tooltip.
- Tabs và stepper.
- Card và metric card.
- Data table, filter chips và pagination.
- Folder tree, file row và upload dropzone.
- Progress bar và job progress panel.
- Status badge, warning/error/success banner.
- Tooltip, popover, modal/confirm dialog và drawer.
- Form field, select, date picker và number input.
- Code/UID/checksum viewer.
- Chart container, Gamma map viewer, DVH viewer và timeline.
- Report block, drag-and-drop report canvas và revision selector.
- Diff view.
- Empty state, skeleton loading và error state có retry.
- Toast/notification và export menu.

Mỗi component phải có variant desktop, tablet/mobile khi cần; trạng thái default, hover, focus, disabled, loading, warning và error.

---

## 8. Trạng thái và microcopy

### 8.1. Trạng thái phải thiết kế

- Loading lần đầu và loading inline.
- Empty organization, empty folder và empty search result.
- Uploading, upload retry và upload failed.
- Validating, valid, warning, invalid và missing required input.
- Analysis queued, running, succeeded và failed.
- Export queued/running/failed/succeeded.
- Session expired, network unavailable và server error.

Không thiết kế clinical approval state machine. Các trạng thái trên chỉ mô tả file, job, input hoặc kết quả để user hiểu hệ thống đang ở đâu.

### 8.2. Microcopy đề xuất

- `Đang kiểm tra dữ liệu đầu vào...`
- `Thiếu RTDOSE — chưa thể chạy PSQA Gamma.`
- `Thiếu dữ liệu đo/đối chiếu — vui lòng bổ sung trước khi chạy.`
- `RTSTRUCT không bắt buộc trong workflow Gamma phantom/plane này.`
- `Kết quả có cảnh báo — mở chi tiết để xem nguyên nhân.`
- `Đang chạy phân tích; bạn có thể rời trang, job vẫn tiếp tục.`
- `Đã tạo kết quả mới; các kết quả trước vẫn được giữ nguyên.`
- `Đây là calculation/scenario tham khảo, không phải prescription.`
- `Chưa có registration phù hợp; chỉ hiển thị so sánh scalar.`
- `Không tìm thấy dữ liệu trong organization hiện tại.`

Microcopy phải ngắn, cụ thể và nói rõ hành động tiếp theo khi có thể.

---

## 9. Responsive và accessibility

### 9.1. Breakpoint cần thiết

- Desktop lớn: 1440px trở lên.
- Desktop chuẩn: 1280px.
- Tablet ngang: 1024px.
- Tablet dọc: 768px.
- Mobile: 390–430px.

### 9.2. Quy tắc responsive

- Sidebar có thể thu gọn thành icon rail trên desktop và drawer trên mobile.
- Top bar không làm mất organization context trên màn hình nhỏ.
- Table rộng chuyển thành card hoặc horizontal scroll có heading cố định.
- Gamma map và chart có zoom/pan phù hợp touch.
- Report Builder trên mobile ưu tiên xem/preview; editor dùng panel drawer khi cần.
- Upload hỗ trợ mobile file picker nhưng vẫn hiển thị rõ giới hạn file.
- Không đặt nút quan trọng quá sát cạnh màn hình.

### 9.3. Accessibility

- Keyboard navigation cho sidebar, tabs, form, table, modal và report editor.
- Focus ring rõ ràng.
- Contrast phù hợp cho text và status.
- Không truyền đạt trạng thái chỉ bằng màu.
- Tooltip không chứa thông tin duy nhất; nội dung quan trọng phải có text.
- Form error gắn với field cụ thể.
- Biểu đồ có bảng dữ liệu hoặc summary thay thế.
- Icon có accessible label.
- Hỗ trợ zoom trình duyệt.

---

## 10. Luồng prototype bắt buộc trong Google Stitch

Google Stitch cần tạo prototype có thể click qua tối thiểu các luồng sau.

### Flow A — Tạo QA case và upload

`Home → Quick action → New QA case → chọn machine/QA type → chọn folder/protocol → upload file → Input Manifest → validation → QA case detail`

### Flow B — PSQA Gamma

`QA case detail → Inputs → Gamma configuration → review warning → Run analysis → job progress → Gamma result → provenance → create report`

### Flow C — Machine QA và trend

`Machine detail → Machine QA → nhập/import measurement → metric table → save result → Trend → click point → QA case/report`

### Flow D — Report Builder

`Analysis result → Create report → chọn template → kéo block → chỉnh properties → preview → save revision → compare revision → export`

### Flow E — Biological BED/EQD2

`Biological Toolkit → BED & EQD2 → nhập D/n/d/alpha-beta → xem formula/result → mở graph → export calculation report`

### Flow F — So sánh phác đồ

`Biological Toolkit → Compare plans → nhập Plan A/B → xem BED/EQD2 → chart/table → warning/source → save scenario`

### Flow G — Re-irradiation

`Biological Toolkit → Re-irradiation → add course 1/2 → nhập interval/dose/fraction → assumptions → scalar/spatial warning → calculate → compare scenarios → export`

### Flow H — Truy cập từ xa

`Public landing → Login → Home → mở QA case → refresh browser → job/report vẫn truy cập được`

---

## 11. Dữ liệu mẫu cho thiết kế

Chỉ dùng dữ liệu synthetic. Có thể dùng bộ dữ liệu mẫu sau:

### QA sample

- Organization: `Bệnh viện Demo`.
- Site: `Cơ sở Trung tâm`.
- Machine: `Elekta Evo - Linac 01`.
- QA case: `PSQA-2026-001`.
- Folder: `2026 / PSQA / January`.
- Protocol: `PSQA Gamma - Demo v1.0`.
- Artifact: `reference_dose_demo.dcm`, `measurement_demo.json`.
- Warning sample: `Measurement grid spacing differs from reference grid; review resampling configuration.`

### Biological sample

- Scenario: `Demo head and neck re-irradiation`.
- Course 1: `Course A — 60 Gy / 30 fractions`.
- Course 2: `Course B — 30 Gy / 15 fractions`.
- Tissue: `Demo OAR`.
- Alpha/beta: `user-entered illustrative value`.

Tất cả màn hình chứa dữ liệu này phải có nhãn `Synthetic demo data` hoặc `Illustrative calculation`.

---

## 12. Deliverables Google Stitch cần trả về

1. Sitemap và screen map.
2. High-fidelity desktop screens.
3. Responsive screens cho tablet/mobile.
4. Clickable prototype của Flow A–H.
5. Design tokens.
6. Component inventory và component states.
7. Empty/loading/error/warning/invalid states.
8. Report Builder interaction prototype.
9. Gamma map/result viewer concept.
10. Trend chart/drill-down concept.
11. Biological Toolkit charts, tables và multi-course re-irradiation editor.
12. Copy/microcopy tiếng Việt.
13. Asset export và icon list.
14. Route-to-screen map.
15. API-data field mapping cho từng màn hình.
16. `DESIGN.md` hoặc handoff document tương đương.
17. Danh sách điểm còn cần xác nhận.

Google Stitch không cần tạo backend hoặc kết nối production. Code/asset export chỉ là điểm bắt đầu; frontend team phải review và triển khai lại theo component/API contract thật.

---

## 13. Tiêu chí nghiệm thu UI/UX

### 13.1. Phạm vi màn hình

- Có đủ landing, login, home, QA archive, QA case, artifact/manifest, validation, Machine QA, Gamma setup/running/result, trend, report, protocol library và toàn bộ Biological Toolkit.
- QA Management và Biological Toolkit được phân biệt rõ.
- Không có menu phân cấp theo bác sĩ/kỹ sư.

### 13.2. Luồng và trạng thái

- Flow A–H có thể click end-to-end.
- Mỗi workflow có loading, empty, error, warning và invalid state.
- Job chạy bất đồng bộ có progress và recovery sau refresh.
- Cảnh báo input có link tới nguyên nhân/record liên quan.

### 13.3. Dữ liệu và ngữ nghĩa

- RTDOSE và measurement được thể hiện là bắt buộc trong PSQA Gamma.
- RTSTRUCT được thể hiện đúng là tùy chọn trong Gamma phantom/plane và cần thiết cho workflow DVH khi áp dụng.
- Gamma configuration hiển thị đầy đủ, không rút gọn thành một label.
- Metric có actual, unit, limit, margin, status và explanation.
- Report Builder thể hiện toàn quyền thêm/bớt/ẩn/đổi tên/sắp xếp block.
- Biological result hiển thị formula, source, model, assumption và limitation.
- Re-irradiation phân biệt scalar với spatial calculation.

### 13.4. Responsive/accessibility

- Có desktop, tablet và mobile variant.
- Có keyboard/focus/contrast/accessibility review.
- Bảng và biểu đồ có cách đọc thay thế.

### 13.5. Handoff

- Mỗi BR trong business-analysis.md có screen hoặc flow tương ứng.
- Mỗi screen có route, input/output field, action và state.
- Design token map được tới frontend component.
- Prototype không chứa dữ liệu thật.
- Không có phụ thuộc runtime vào Google Stitch.

---

## 14. Prompt tổng hợp gửi Google Stitch

Dùng prompt dưới đây làm prompt khởi đầu. Có thể chia thành nhiều prompt nhỏ sau khi Stitch tạo screen map ban đầu.

```text
Design a high-fidelity desktop-first clinical professional web application called RT-CONNECT.

Target users are radiation oncologists, radiotherapy medical physicists, and other clinical team members. All members in the same organization use the same navigation and the same business functions. Do not create doctor-vs-engineer role menus, role badges, approval hierarchies, or action-permission matrices.

The UI language must be Vietnamese, with clear technical terms and future English extensibility. The product is a trustworthy radiotherapy QA and calculation workspace, not a consumer app. Use a calm navy/blue/teal clinical palette, warm white surfaces, slate text, amber warnings, deep red errors, and accessible success colors. Prefer clean dense tables, charts, panels, breadcrumbs, filters, drawers, and drill-down interactions. Avoid neon colors, excessive gradients, decorative animations, social-media patterns, and financial-dashboard styling.

Create a complete responsive web application with these major areas:

1. Public landing page with RT-CONNECT branding, a short product explanation, feature cards for QA Management, DICOM/input validation, PSQA Gamma, customizable reports, trends, and an independent Biological Toolkit. Include a Sign in button. Do not show patient or QA data on the landing page.
2. Authentication screens: sign in, password recovery, magic link/OTP result if enabled, session expired, auth error, and loading states. Authentication is powered by Supabase Auth, but do not show implementation details or secrets.
3. App shell after login: persistent top bar with logo, collapsible sidebar, breadcrumb, organization/site/machine context selectors, global search, job center, help, and profile/logout.
4. Main sidebar tabs: Home, QA Management, Trend, QA Protocol Library, Biological Toolkit, Activity/History, and Settings/Help. Keep the same navigation for all organization members.
5. Home dashboard with quick actions, recent QA cases, running analysis jobs, validation warnings, recent reports, machine/trend summaries, and activity feed. Use synthetic demo data and label it clearly.
6. QA Management: QA overview, nested folder/file-manager archive, new folder, new QA case, artifact upload, Input Manifest, DICOM validation detail, machine list/detail, Machine QA workspace, PSQA Gamma setup/running/result, analysis history, report viewer, and Report Builder.
7. QA archive must support nested folders, free naming, rename, move, archive, search, filters, breadcrumbs, list/compact views, and metadata columns for site, machine, QA type, date, protocol, latest analysis, report, and data status.
8. QA case detail must have tabs for Overview, Inputs & Manifest, Validation, Analysis Runs, Reports, and History/Provenance. These are information tabs, not a clinical approval state machine.
9. PSQA Gamma setup must clearly require RTDOSE and a measurement/comparison dataset. RTSTRUCT is optional for ordinary phantom/plane Gamma and is required only for workflows such as DVH when applicable. Show the full Gamma configuration: dose difference, DTA, absolute/relative, global/local, dose threshold, pass threshold, 2D/3D, per-field/composite, ROI/mask, alignment/shift, interpolation/resampling, search distance, and maximum gamma. Never infer missing units, columns, geometry, or roles.
10. PSQA Gamma result must include pass rate, threshold, Gamma map with legend and units, profile/slice tools, warnings, input/geometry summary, configuration drawer, engine/protocol versions, provenance, rerun, compare, report, and export actions.
11. Machine QA workspace must show test items with actual, unit, limit, margin, status, notes, protocol, and trend shortcut.
12. Trend dashboard must support filters by site, machine, QA type, cycle, metric, protocol, detector/phantom, energy/mode, and time. Show line charts, baseline/tolerance/action levels, warning points, maintenance events, tooltips, drill-down to the original case/report, and export.
13. Report Builder must be a full customization editor with a left block library, central report canvas, and right properties panel. Support adding, removing, hiding, renaming, reordering, resizing, conditional display, metric selection, chart range selection, preview, revision history, compare, and export. Include blocks for metadata, input manifest, metrics, Gamma map, profile, DVH, trend, comparisons, BED/EQD2, fractionation, re-irradiation scenario, notes, and provenance.
14. QA Protocol Library must show protocol catalog, filters, source, internal/reference labels, rules, metrics, version timeline, version diff, and create-new-version interaction.
15. Biological Toolkit must be a separate top-level workspace with its own overview and quick cards. It must not automatically link to QA cases, patient cases, RT Plans, prescriptions, PACS, or clinical orders.
16. Biological Toolkit pages must include: BED & EQD2 calculator, BED/EQD2 graph by total dose D, treatment-plan comparison, dose-limit library, treatment protocol library, knowledge library, detailed multi-course re-irradiation calculator, fraction compensation calculator, calculation history, and independent calculation report.
17. BED/EQD2 screens must show D, n, d, alpha/beta, tissue/OAR/target, formula, model, source, assumptions, result units, warnings, chart, and export.
18. Re-irradiation must use a detailed multi-course editor with course cards/timeline, dates/intervals, dose/fractions, tissue/OAR/target, alpha/beta and sources, recovery assumptions, repopulation/volume/heterogeneity assumptions when supported, spatial registration status, scalar vs spatial mode, comparison of scenarios, warnings, limitations, and independent export. If registration is missing, clearly show: “Scalar comparison only — chưa thực hiện cộng liều theo không gian.” Do not make it look like a prescription or automated treatment recommendation.
19. Fraction compensation must show original schedule, completed fractions, delivered dose, interruption/missing fractions, remaining fractions, total treatment time, scenarios, BED/EQD2, assumptions, warnings, and the banner: “Đây là scenario/proposal để thảo luận chuyên môn, không phải prescription.”
20. Include activity/history timeline with user, time, object, action, version, and links. This is provenance/audit display, not role-based access control.

Create all important states: initial loading, skeleton, empty organization, empty folder, empty search, upload progress, retry, validating, valid, warning, invalid, analysis queued/running/succeeded/failed, export states, session expired, network unavailable, and server error. Use clear Vietnamese microcopy. Never expose stack traces, tokens, service keys, database credentials, or real patient identifiers.

Create desktop layouts at 1440px and 1280px, tablet layouts at 1024px and 768px, and mobile layouts around 390–430px. Make tables responsive, charts readable, and report/Gamma viewers usable with touch. Include keyboard navigation, visible focus, accessible contrast, non-color status labels, and data-table alternatives for charts.

Use only synthetic data such as “Bệnh viện Demo”, “Elekta Evo - Linac 01”, “PSQA-2026-001”, “reference_dose_demo.dcm”, and “measurement_demo.json”. Mark demo values as “Synthetic demo data” or “Illustrative calculation”.

Deliver: sitemap, screen map, high-fidelity screens, responsive variants, clickable prototypes for QA upload, Gamma, Machine QA/trend, Report Builder, BED/EQD2, plan comparison, re-irradiation, and remote access; design tokens; component inventory; all UI states; Vietnamese copy; route-to-screen map; API-field mapping; and a developer handoff document. The generated design/code is a reference for frontend implementation; do not make production runtime depend on Google Stitch.
```

---

## 15. Ghi chú handoff cho frontend

- Mỗi màn hình phải được map tới một route và một workflow.
- Mỗi field phải có data type, unit, required/optional và validation message.
- Mỗi action phải có success, loading, error và retry behavior.
- Mỗi chart phải có data source, unit, legend, empty state và export behavior.
- Mỗi report block phải có block type, config schema, preview state và revision behavior.
- Mỗi cảnh báo phải link tới input/result liên quan.
- Design revision phải được lưu cùng ngày, người thay đổi và lý do.
- Không dùng code export của Stitch mà chưa review accessibility, responsive behavior, API integration và security boundary.

---

## 16. Nguồn yêu cầu

- `business-analysis.md`: yêu cầu và workflow nghiệp vụ.
- `technical.md`: ranh giới hệ thống, API, dữ liệu và deployment.
- `plan.md`: phase triển khai và tiêu chí nghiệm thu.
- Google Stitch overview: <https://blog.google/innovation-and-ai/models-and-research/google-labs/stitch-ai-ui-design/>
