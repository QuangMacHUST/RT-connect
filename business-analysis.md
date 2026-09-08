# TÀI LIỆU PHÂN TÍCH NGHIỆP VỤ

## Dự án RT-CONNECT

- **Tên sản phẩm:** RT-CONNECT
- **Phạm vi:** Website quản lý QA xạ trị, thư viện QA protocol, Biological Toolkit và thư viện kiến thức điều trị
- **Đối tượng sử dụng:** Bác sĩ xạ trị, kỹ sư vật lý xạ trị và các thành viên chuyên môn trong bệnh viện/tổ chức
- **Phiên bản tài liệu:** 0.8 — catalogue tính năng, workflow, ngoại lệ, phục hồi và tiêu chí nghiệm thu theo P0–P20 (2026-09-08)
- **Trạng thái sản phẩm:** Chưa phải hệ thống được thẩm định để sử dụng lâm sàng

Tài liệu này mô tả nghiệp vụ, nhu cầu người dùng, quy trình, quy tắc và tiêu chí nghiệm thu. Kiến trúc nằm trong `technical-specification.md`; hợp đồng hành vi, dữ liệu, lỗi và thuật toán chi tiết nằm trong `specification.md`; trình tự, testcase và tiêu chí đóng từng phase nằm trong `plan.md`. Catalogue yêu cầu chi tiết v0.8 tại mục 21 phân biệt target cần triển khai với evidence đã có. Ma trận nghiệp vụ không phải là tuyên bố hệ thống đã sẵn sàng lâm sàng; trạng thái thực thi phải đọc từ `implementation-progress.md` và gate tương ứng trong `plan.md`.

---

## 1. Định hướng và nguyên tắc sản phẩm

RT-CONNECT có hai khu vực chính:

1. **QA Management:** lưu trữ, phân tích, xem report, tạo report tùy chỉnh và theo dõi trend của các bài QA xạ trị.
2. **Biological Toolkit và Knowledge Library:** thực hiện các phép tính BED/EQD2, so sánh phác đồ, phân tích re-irradiation scenario và tra cứu kiến thức điều trị độc lập với các ca QA hoặc ca bệnh lâm sàng.

Trong cùng một organization, bác sĩ, kỹ sư và thành viên chuyên môn được sử dụng nghiệp vụ ngang nhau. Tài liệu này không xây dựng phân cấp bác sĩ–kỹ sư hoặc phân quyền theo từng hành động. Lịch sử, version và provenance chỉ nhằm giúp người dùng biết nội dung được tạo ra như thế nào, không nhằm hạn chế quyền sử dụng của thành viên trong organization.

RT-CONNECT không tự thay thế đánh giá chuyên môn, không tự sửa prescription, RT Plan, TPS hoặc PACS và không tự phát hành clinical order.

---

## 2. Bối cảnh và vấn đề cần giải quyết

### 2.1. Hiện trạng nghiệp vụ

Các bài QA, report, protocol và phép tính sinh học thường được lưu rải rác trong nhiều thư mục, máy tính hoặc phần mềm khác nhau. Điều này gây khó khăn khi cần:

- Tìm lại report của một máy hoặc một thời điểm.
- Biết bài QA nào đã thực hiện và bài nào còn thiếu.
- So sánh kết quả giữa các tháng hoặc giữa các máy.
- Xem lại cách tính và tham số đã dùng.
- Tạo report theo mẫu riêng của từng bệnh viện.
- Liên kết DICOM và dữ liệu đo thành một hồ sơ QA hoàn chỉnh.
- Chia sẻ QA protocol, protocol điều trị, hướng dẫn contouring và tiêu chí OAR.
- Tra cứu paper, guideline và giả định của các phép tính BED/EQD2.
- So sánh các phác đồ hoặc các kịch bản re-irradiation một cách có hệ thống.

### 2.2. Vấn đề của cách quản lý chỉ bằng file

- Tên file không đủ thể hiện machine, loại QA, protocol và phiên bản.
- Kết quả cũ có thể bị sửa hoặc ghi đè mà không biết nội dung trước đó.
- Khó phát hiện trend xấu nếu chỉ xem từng report riêng lẻ.
- File DICOM và file kết quả đo có thể không được liên kết thành một QA case hoàn chỉnh.
- Report thường cố định, khó thêm hoặc bớt dòng, bảng và biểu đồ.
- Protocol nội bộ dễ lỗi thời hoặc mất nguồn tham chiếu.
- Các phép tính sinh học nằm ở nhiều file riêng, thiếu lịch sử, giả định và khả năng so sánh.

---

## 3. Mục tiêu nghiệp vụ

### 3.1. Mục tiêu tổng quát

Xây dựng một website giúp bệnh viện quản lý tập trung các bài QA, report, protocol, thư viện kiến thức và công cụ tính liều sinh học; kết quả phải có thể giải thích, tra cứu và tái hiện được từ dữ liệu đầu vào.

### 3.2. Mục tiêu cụ thể

- Upload file DICOM và dữ liệu đo của bài QA.
- Quản lý QA theo organization, site/hospital, machine, folder, năm, loại QA và chu kỳ Daily/Monthly/Annual.
- Cho phép user tự tạo folder và đặt tên tự do giống cách quản lý thư mục trên máy tính.
- Chạy các phân tích QA phù hợp với từng loại workflow.
- Kiểm tra dữ liệu đầu vào trước khi phân tích.
- Import/export file, kết quả, report và lịch sử.
- Xem lại report cũ và các revision.
- So sánh các lần đo và theo dõi trend.
- Tùy chỉnh report bằng cách thêm, bớt, ẩn, đổi tên, sắp xếp các dòng, bảng, biểu đồ, phân tích và nhận xét.
- Lưu QA protocol và các rule theo từng phiên bản.
- Cung cấp một Biological Toolkit độc lập với QA case và ca bệnh.
- Tính BED, EQD2, so sánh phác đồ, bù fraction và re-irradiation scenario.
- Cung cấp đồ thị BED/EQD2 theo tổng liều D.
- Cung cấp bảng giới hạn liều theo bệnh lý, mô và OAR kèm nguồn tham khảo.
- Lưu protocol điều trị, phác đồ điều trị và kiến thức lý thuyết trong khu vực Biological Toolkit.
- Bảo đảm mọi thay đổi có thể truy ngược tới user, thời gian, nội dung và phiên bản.
- Cho phép các thành viên chuyên môn truy cập hệ thống từ xa bằng website qua kết nối HTTPS.

---

## 4. Phạm vi sản phẩm

### 4.1. Phạm vi chung

1. Tài khoản user và organization.
2. Cây quản lý organization → site/hospital → machine.
3. Folder và kho lưu trữ bài QA.
4. QA case Daily, Monthly, Annual và Custom.
5. Upload/import file DICOM `.dcm` và dữ liệu QA liên quan.
6. Phân tích QA trên website.
7. Xem và so sánh kết quả.
8. Trend dashboard.
9. Report viewer và Report Builder.
10. QA protocol library.
11. Biological Toolkit độc lập.
12. Thư viện protocol điều trị, phác đồ và knowledge library trong Biological Toolkit.
13. Lịch sử thay đổi, version và audit trail.

### 4.2. Kênh truy cập từ xa

RT-CONNECT được phát hành dưới dạng website có URL để các thành viên chuyên môn truy cập từ xa bằng trình duyệt desktop hoặc mobile. Truy cập từ xa là yêu cầu về khả năng kết nối và phát hành sản phẩm, không làm phát sinh phân cấp bác sĩ–kỹ sư hoặc phân quyền theo từng hành động.

Phạm vi truy cập:

- Người dùng truy cập giao diện web và các API cần thiết qua HTTPS.
- Các thành viên trong cùng organization sử dụng các chức năng nghiệp vụ ngang nhau như đã nêu ở mục 5.2.
- Dữ liệu QA, artifact, report và scenario vẫn được gắn với organization để tránh truy vấn nhầm dữ liệu giữa các tổ chức.
- Database, worker, queue và DICOM gateway là hạ tầng phía sau, không phải dịch vụ nghiệp vụ public. Object storage giữ bucket private; browser được tải file qua signed URL ngắn hạn sau khi xác minh organization.
- Nếu chia sẻ nội dung kiến thức hoặc protocol ra ngoài organization trong tương lai, đó sẽ là một yêu cầu sản phẩm riêng; không mặc định mở dữ liệu QA hoặc dữ liệu có định danh cho người dùng ẩn danh.

### 4.3. Clinical MVP

Clinical MVP tập trung vào:

- QA archive.
- Machine QA Daily/Monthly/Annual.
- PSQA Gamma.
- Phân tích kết quả và trend.
- Report tùy chỉnh.
- Provenance và lịch sử revision.

Biological Toolkit được phát triển như một khu vực riêng, không gắn mặc định với các case QA hoặc ca bệnh.

### 4.4. Phạm vi mở rộng

- Visual Dose Review trên anatomy.
- DVH/Plan Review.
- Phân tích structure-level từ RTDOSE và RTSTRUCT.
- Các phương pháp phân tích QA khác ngoài Gamma.
- Import dữ liệu từ nhiều thiết bị đo và phần mềm bên ngoài.

### 4.5. Ngoài phạm vi tự động hóa

- Thay thế TPS, PACS hoặc bệnh án điện tử.
- Chỉnh sửa treatment plan, prescription, MLC hoặc thông số máy điều trị.
- Tự động gửi đề xuất bù liều hoặc re-irradiation vào TPS.
- Tự động phát hành clinical order.
- Tự động đưa ra quyết định điều trị.
- Tự động liên kết Biological Toolkit với một ca bệnh hoặc QA case nếu user không chủ động chọn dữ liệu.

### 4.6. Nguồn thiết kế giao diện và ràng buộc triển khai đã thống nhất

Các quyết định sau là baseline sản phẩm tại ngày 2026-09-04:

- Google Stitch project `RT-connect` là nguồn thiết kế trực quan đang hoạt động. Project ID là `14242591911141046021`.
- Thiết kế được truy xuất trực tiếp qua MCP Google Stitch; repository không còn duy trì `UI-UX.md` như một nguồn yêu cầu song song.
- `business-analysis.md` vẫn là nguồn yêu cầu nghiệp vụ. Màn hình hoặc code do Stitch tạo không được tự thay đổi quy tắc nghiệp vụ trong tài liệu này.
- Railway là nền tảng triển khai backend server và PostgreSQL của RT-CONNECT.
- Supabase chỉ cung cấp Authentication/Identity/Session; Supabase không phải database nghiệp vụ của RT-CONNECT.
- Website phải truy cập được từ xa qua HTTPS sau khi hoàn tất release production.
- Token Railway, khóa MCP, database credential và các secret triển khai không phải dữ liệu nghiệp vụ, không xuất hiện trên giao diện người dùng và không được ghi vào tài liệu hoặc source code.

Stitch hiện có bốn màn hình sản phẩm đang hoạt động làm thiết kế tham chiếu:

| Mã | Màn hình hiện có | Khu vực nghiệp vụ |
| :--- | :--- | :--- |
| UI-01 | Trang chủ - Home Dashboard | Tổng quan và điều hướng |
| UI-02 | Kho lưu trữ QA & Thư mục | Folder, QA archive và QA case |
| UI-03 | Phân tích PSQA Gamma Workspace | Upload/validation/Gamma/result |
| UI-04 | Trình biên soạn Báo cáo - Report Builder Studio | Report Builder, preview và export |

Bốn thiết kế Biological Toolkit cũ đã được user loại khỏi canvas hoạt động vì không đồng nhất với bốn màn hình trên. MCP vẫn có thể trả các instance cũ ở trạng thái `hidden`; các instance này là legacy/deprecated, không được dùng làm nguồn thiết kế, không được tự khôi phục và không được giữ Screen ID cũ trong mapping triển khai. Biological Toolkit Overview, BED/EQD2, so sánh phác đồ và Re-irradiation phải được tạo lại lần lượt trong cùng project Stitch, dùng Design System `Clinical Precision Interface` và bốn màn hình đang hoạt động làm chuẩn.

Bốn màn hình đang hoạt động chưa phải toàn bộ sản phẩm. Các module chưa có màn hình riêng như đăng nhập, organization/site/machine, QA case detail, upload/validation chi tiết, Machine QA checklist, trend, QA Protocol Library, Biological Toolkit, dose-limit/knowledge library, report history và trạng thái lỗi hệ thống vẫn phải được thiết kế khi phase tương ứng bắt đầu. Việc chưa có screen trên Stitch không làm yêu cầu nghiệp vụ đó biến mất.

### 4.7. Danh mục module và kết quả nghiệp vụ phải bàn giao

| Mã module | Module | Kết quả nghiệp vụ hoàn chỉnh |
| :--- | :--- | :--- |
| MOD-00 | Identity và Organization Context | User đăng nhập bằng Supabase Auth, vào đúng organization và không truy vấn chéo organization |
| MOD-01 | Home Dashboard | User thấy machine, QA gần đây, cảnh báo, job và lối vào các khu vực chính |
| MOD-02 | Organization, Site và Machine | Tạo và quản lý đúng hierarchy; machine giữ định danh ổn định khi đổi tên |
| MOD-03 | QA Archive, Folder và QA Case | Quản lý folder lồng nhau, tìm kiếm, tạo case, di chuyển/archive mà không mất lịch sử |
| MOD-04 | Artifact, Upload và Validation | Upload giữ nguyên file, tạo checksum, Input Manifest và kết quả validation có thể giải thích |
| MOD-05 | Machine QA | Tạo checklist Daily/Monthly/Annual/Custom, nhập metric, áp rule và tạo trend point |
| MOD-06 | PSQA Gamma | Chạy Gamma end-to-end từ RTDOSE + measurement, lưu map, metric, warning, configuration và provenance |
| MOD-07 | Report Builder | Tạo report tùy chỉnh, revision, preview và export tái hiện được từ snapshot |
| MOD-08 | Trend | Xem lịch sử theo machine/metric/time, baseline, tolerance, action level và drill-down về nguồn |
| MOD-09 | QA Protocol Library | Tạo, sao chép, version hóa protocol/rule/reference mà không cập nhật ngược report cũ |
| MOD-10 | Biological Hub | Điều hướng, history, source và report độc lập cho toàn bộ Biological Toolkit |
| MOD-11 | BED/EQD2 | Tính, giải thích, lưu lịch sử và vẽ đồ thị theo tổng liều D |
| MOD-12 | So sánh phác đồ | So sánh hai hoặc nhiều phác đồ bằng bảng/đồ thị và ghi rõ khác biệt context/model |
| MOD-13 | Re-irradiation và bù fraction | Tính nhiều course, recovery/no-recovery, khoảng thời gian, scenario và cảnh báo giới hạn |
| MOD-14 | Dose Limit, Treatment Protocol và Knowledge Library | Tra cứu, tạo version, dẫn nguồn và dùng nội dung như công cụ tính toán/kiến thức độc lập |
| MOD-15 | Visual Dose và DVH/Plan Review | Xem dose trên anatomy và tính metric structure khi input geometry hợp lệ |
| MOD-16 | Audit, vận hành và truy cập từ xa | Theo dõi lineage/revision, backup/restore, monitoring và sử dụng website ổn định qua HTTPS |

Một module chỉ được coi là hoàn thành khi người dùng thực hiện được workflow từ giao diện đến dữ liệu/kết quả cuối, có trạng thái rỗng/đang xử lý/lỗi/cảnh báo, có lịch sử cần thiết và đạt tiêu chí nghiệm thu của module. Một ảnh giao diện, một API riêng lẻ hoặc một deployment thành công chưa đủ để đóng module.

---

## 5. Người dùng và nguyên tắc sử dụng

### 5.1. Nhóm người dùng nghiệp vụ

| Nhóm người dùng | Mục đích sử dụng |
| :--- | :--- |
| Kỹ sư vật lý xạ trị | Nhập dữ liệu QA, phân tích, theo dõi trend, tạo report và xây dựng protocol |
| Bác sĩ xạ trị | Xem report, xem protocol/phác đồ, sử dụng Biological Toolkit và knowledge library |
| Thành viên chuyên môn khác | Sử dụng dữ liệu, report và công cụ trong organization |

### 5.2. Quyền sử dụng ngang nhau

Trong cùng một organization, các thành viên được sử dụng ngang nhau các chức năng nghiệp vụ:

- Xem dữ liệu của organization.
- Tạo folder và QA case.
- Upload/import file.
- Chạy phân tích.
- Xem và export kết quả.
- Tạo/chỉnh report.
- Tạo/chỉnh QA protocol.
- Tạo/chỉnh nội dung Biological Toolkit và knowledge library.
- Ghi nhận nhận xét, scenario và lịch sử tính toán.

`doctor` và `physicist` chỉ mô tả chuyên môn của user, không tạo ra quyền cao thấp trong sản phẩm.

### 5.2.1. Khởi tạo organization lần đầu

- Supabase Auth xác thực identity trước; RT-CONNECT không tự tạo quyền truy cập dữ liệu chỉ từ việc đăng nhập.
- Nếu identity hợp lệ nhưng chưa có membership đang hoạt động, hệ thống hiển thị màn hình khởi tạo thay vì hiển thị dữ liệu organization.
- Người dùng đầu tiên có thể nhập tên bệnh viện/organization trên màn hình khởi tạo để tạo organization và được gắn membership đầu tiên.
- Identity đã có membership không được tạo thêm organization theo cùng luồng khởi tạo, tránh tạo nhiều context không rõ ràng.
- Membership chỉ xác định phạm vi organization; không tạo role hierarchy hoặc quyền hành động khác nhau giữa bác sĩ, kỹ sư và thành viên chuyên môn.
- Sau khi organization được tạo, người dùng tiếp tục thiết lập site/hospital và machine trong module Organization / Site / Machine.

### 5.3. Trách nhiệm giải trình bằng lịch sử

Hệ thống tự lưu:

- Người tạo.
- Người sửa.
- Người chạy phân tích.
- Người thay đổi cấu hình.
- Người tạo report.
- Người export.
- Thời gian và organization context.
- Nội dung trước và sau khi sửa.
- Lý do sửa nếu user nhập lý do.

Lịch sử không bị mất khi user đổi tên, di chuyển hoặc archive folder, QA case, report, protocol hoặc scenario.

---

## 6. Cấu trúc nghiệp vụ của tổ chức

### 6.1. Hierarchy bắt buộc cho QA

```text
Organization
└── Site/Hospital
    └── Machine
        └── QA Case
            ├── Folder/Classification
            ├── Input Files
            ├── Analysis Results
            ├── Reports
            └── Trend Points
```

Một organization có thể có nhiều site/hospital. Một site/hospital có thể có nhiều machine. Một machine có nhiều QA case theo loại và chu kỳ khác nhau.

### 6.2. Ý nghĩa các thành phần

#### Organization

Đơn vị dữ liệu độc lập, thường là bệnh viện hoặc tổ chức có nhiều cơ sở.

#### Site/Hospital

Cơ sở, bệnh viện, campus hoặc đơn vị trực thuộc organization.

#### Machine

Máy điều trị hoặc thiết bị QA thuộc một site. Machine là đơn vị chính để xem lịch sử và trend. Machine phải có định danh ổn định để các lần đổi tên không làm tách trend.

#### QA Case

Một lần thực hiện hoặc một bộ hồ sơ QA. QA case cho biết machine, loại QA, thời điểm, protocol, file đầu vào, kết quả phân tích và report liên quan.

#### Folder

Không gian phân loại do user tạo, có thể đặt tên tự do và có folder con giống hệ thống file trên máy tính.

---

## 7. Folder và kho lưu trữ QA

### 7.1. Mục tiêu

User có thể tổ chức dữ liệu theo cách quen thuộc như quản lý thư mục trên máy tính, đồng thời vẫn tìm kiếm được bằng thuộc tính nghiệp vụ.

### 7.2. Ví dụ cách tổ chức

```text
Site A
└── Machine 1
    ├── 2026
    │   ├── Daily QA
    │   ├── Monthly QA
    │   └── Annual QA
    ├── PSQA
    ├── Research
    └── Archived Reports
```

### 7.3. Yêu cầu nghiệp vụ

- User có thể tạo folder.
- User có thể đặt tên, đổi tên, di chuyển và tạo folder con.
- Folder có thể tổ chức theo năm, machine, loại QA, project hoặc cách riêng của bệnh viện.
- Một QA case có một vị trí lưu trữ chính trong folder.
- Có thể tìm kiếm bằng site, machine, QA type, protocol, thời gian và trạng thái dữ liệu.
- Có thể xem report mới nhất và toàn bộ report revision trong folder.
- Có thể archive folder hoặc case nhưng không làm mất lịch sử.
- Có thể export danh sách folder, QA case và report.
- Folder của organization được nhìn thấy bởi các thành viên trong cùng organization.

### 7.4. Chu kỳ QA

Hệ thống hỗ trợ:

- Daily QA.
- Monthly QA.
- Annual QA.
- Custom QA.

Mỗi chu kỳ có thể gắn với machine, loại test, protocol, thời điểm dự kiến và ghi nhận hoàn thành. Chu kỳ giúp theo dõi hồ sơ và trend, không tự thay thế kết luận của người chuyên môn.

---

## 8. Các loại workflow QA

Khi tạo QA case, user chọn đúng mục đích sử dụng. Hệ thống chỉ yêu cầu các file phù hợp với workflow đó.

### 8.1. Machine QA Daily/Monthly/Annual

Mục đích là ghi nhận phép đo và đánh giá QA của máy hoặc thiết bị.

- Dữ liệu đo là đầu vào chính.
- RTDOSE chỉ cần khi bài QA có bước đối chiếu liều bằng DICOM.
- RTSTRUCT không bắt buộc.
- Có thể dùng protocol Daily, Monthly, Annual hoặc Custom.
- Kết quả được đưa vào trend của đúng machine.

### 8.2. PSQA Gamma

Mục đích là so sánh liều tham chiếu với liều đo hoặc liều đối chiếu.

- RTDOSE là file DICOM bắt buộc trong workflow PSQA của RT-CONNECT.
- Dữ liệu đo/đối chiếu là bắt buộc.
- RTPLAN có thể được user đưa vào khi cần kiểm tra isocenter, beam hoặc field-by-field.
- RTSTRUCT không bắt buộc cho gamma phantom/plane thông thường.
- Kết quả lưu pass rate, gamma map, tham số, thông tin dữ liệu và cảnh báo.

### 8.3. Visual Dose Review

Mục đích là xem trực quan phân bố liều trên hình ảnh giải phẫu.

- RTDOSE là đầu vào liều.
- CT cần khi muốn xem liều trên anatomy.
- RTSTRUCT là tùy chọn.
- RTSTRUCT được dùng khi user muốn xem OAR/PTV hoặc liên hệ liều với cấu trúc.
- Nếu chỉ xem dose plane hoặc dose grid, không bắt buộc RTSTRUCT.

### 8.4. DVH/Plan Review

Mục đích là đánh giá dose–structure và các metric target/OAR.

- RTDOSE bắt buộc.
- RTSTRUCT bắt buộc.
- CT được dùng khi cần xem trực quan.
- Kết quả gồm DVH, metric, giới hạn, margin và trạng thái kết quả.

### 8.5. Biological Toolkit

Biological Toolkit là workflow độc lập, không thuộc QA case và không gắn mặc định với ca bệnh.

- Có thể nhập dữ liệu fraction bằng tay.
- Có thể nhập nhiều course để so sánh hoặc tạo re-irradiation scenario.
- Có thể dùng dữ liệu dose/structure do user chủ động đưa vào khu vực Biological Toolkit.
- Kết quả chỉ là phép tính, đồ thị, scenario hoặc tài liệu tham khảo.
- Không tự tạo prescription, clinical order hoặc thay đổi RT Plan.

---

## 9. Upload, import và quản lý dữ liệu QA

### 9.1. Yêu cầu chung

- User có thể upload file `.dcm` và file kết quả QA được hỗ trợ.
- User biết file nào đã upload, ai upload và file thuộc QA case nào.
- Hệ thống thông báo file thiếu, file lỗi hoặc file không phù hợp với workflow.
- File được liên kết với machine, QA case, protocol và report nếu có.
- File gốc không bị thay đổi khi tạo kết quả hoặc report mới.
- Có thể import kết quả đã phân tích từ bên ngoài nếu đúng định dạng được hỗ trợ.
- Có thể export file, kết quả, report và lịch sử.

### 9.2. Trạng thái dữ liệu file

- `UPLOADED`: đã đưa lên hệ thống.
- `VALIDATING`: đang kiểm tra.
- `VALID`: đủ điều kiện sử dụng.
- `WARNING`: có cảnh báo nhưng user có thể tiếp tục xem xét.
- `INVALID`: không được dùng để tạo kết luận phân tích hợp lệ.
- `ARCHIVED`: được lưu lịch sử, không dùng mặc định cho case mới.

Các trạng thái trên mô tả tình trạng dữ liệu file, không tạo ra phân cấp user hoặc quy trình phân quyền.

### 9.3. File gốc và dữ liệu dẫn xuất

- File gốc được lưu nguyên trạng.
- Mọi dữ liệu chuẩn hóa, chuyển đổi hoặc kết quả phân tích được lưu như dữ liệu dẫn xuất.
- Dữ liệu dẫn xuất phải liên kết với file nguồn và cấu hình đã dùng.
- Khi user sửa metadata hoặc chạy lại phân tích, hệ thống tạo revision/dữ liệu dẫn xuất mới thay vì âm thầm thay đổi file nguồn.
- Mỗi file và kết quả có checksum để kiểm tra tính toàn vẹn.

### 9.4. DICOM và thông tin định danh

Khi xử lý dữ liệu có thông tin bệnh nhân, user phải biết dữ liệu đó thuộc study, series, machine và workflow nào. Dữ liệu demo hoặc test nên dùng dữ liệu giả lập hoặc đã ẩn danh.

---

## 10. Kiểm tra đầu vào và liên kết DICOM

### 10.1. Input Manifest

Mỗi lần phân tích phải có bản mô tả đầu vào gồm:

- File name và checksum.
- Modality và SOP Instance UID.
- Study Instance UID và Series Instance UID.
- Frame of Reference UID nếu có.
- Machine, phantom, detector hoặc thiết bị đo nếu có.
- Reference dataset và comparison dataset.
- Protocol version.
- Thời điểm upload và thời điểm đo.
- Đơn vị, dose scaling và các thông tin cần thiết để diễn giải dữ liệu.

### 10.2. Kiểm tra liên kết và hình học

Hệ thống phải kiểm tra khi workflow yêu cầu:

- Dữ liệu có đúng modality không.
- Dose grid có hợp lệ không.
- Kích thước, spacing, origin và orientation có phù hợp không.
- Frame of Reference và các instance tham chiếu có nhất quán không.
- RTDOSE có liên hệ đúng với CT, RTSTRUCT hoặc RTPLAN không.
- Dữ liệu reference và comparison có cùng quy ước tọa độ hoặc có thông tin alignment phù hợp không.
- Có thiếu giá trị, NaN, giá trị ngoài miền hoặc sai kích thước không.

Nếu không đủ thông tin để diễn giải an toàn, hệ thống phải báo thiếu hoặc không hợp lệ thay vì tự đoán đơn vị, cột dữ liệu hoặc cách ghép file.

### 10.3. Dữ liệu đo ngoài DICOM

Kết quả đo từ ngoài hệ thống phải dùng định dạng được mô tả rõ. Đối với measurement Gamma, RT-CONNECT sử dụng contract `gamma.measurement.v1`; dữ liệu JSON/CSV mơ hồ không được tự động đoán cột hoặc đơn vị.

---

## 11. Phân tích QA

### 11.1. Nguyên tắc

Kết quả phân tích phải liên kết với:

- QA case.
- Machine.
- File đầu vào.
- Protocol.
- Cấu hình phân tích.
- Người thực hiện.
- Thời điểm.
- Phiên bản engine hoặc phương pháp tính.

### 11.2. Gamma Index

User có thể chọn preset hoặc tự tùy chỉnh cấu hình Gamma. Các nhóm cấu hình gồm:

- Dose difference.
- Distance-to-agreement.
- Absolute hoặc relative dose.
- Global hoặc local normalization.
- Reference dose level.
- Dose threshold.
- Pass threshold.
- 2D hoặc 3D.
- Per-field hoặc composite.
- ROI/mask.
- Alignment và shift.
- Isocenter plane.
- Search distance.
- Interpolation/resampling.
- Maximum output gamma.

Khi cấu hình Gamma thay đổi, cấu hình mới được lưu cùng kết quả mới. Không chỉ lưu `3%/3 mm` hoặc `2%/2 mm` mà bỏ qua các tham số còn lại.

### 11.3. DVH và plan scoring

Hệ thống có thể:

- Tính DVH theo structure.
- So sánh metric thực tế với tiêu chí protocol.
- Hiển thị actual, limit, margin và status.
- Phân loại `PASS`, `FAIL`, `REVIEW_REQUIRED`, `INVALID_INPUT`, `NOT_APPLICABLE`.
- Cho phép bệnh viện tự định nghĩa rule theo protocol version.
- Link metric đến report, protocol và file liên quan.

### 11.4. Kết quả và cảnh báo

Một kết quả không chỉ là một con số. Kết quả phải cho biết:

```text
Metric → Giá trị thực tế → Đơn vị → Giới hạn → Margin → Trạng thái → Giải thích → Nguồn
```

`PASS` chỉ có nghĩa là đạt rule đã chọn; không phải xác nhận an toàn tuyệt đối.

### 11.5. Phân tích lại

- User có thể chạy lại analysis với cấu hình khác.
- Kết quả cũ không bị xóa.
- Mỗi lần chạy lại lưu input, cấu hình, phiên bản engine, thời gian và kết quả riêng.
- User có thể so sánh các lần chạy.

### 11.6. Bộ test tính toán

Trong giai đoạn phát triển, các engine phân tích phải đạt bộ test đã xác định trước, gồm:

- Gamma 2D/3D.
- Global/local.
- Absolute/relative.
- Grid khác nhau.
- Dịch chuyển có kiểm soát.
- Vùng dose thấp.
- Biên trường.
- Dữ liệu lỗi hoặc thiếu.
- DVH trên hình học chuẩn.
- BED/EQD2 với các bộ giá trị đã biết.

Dataset thật của bệnh viện có thể được dùng trong giai đoạn pilot và vận hành để phát hiện trường hợp thực tế, cải tiến workflow và cập nhật engine. Mỗi thay đổi làm thay đổi kết quả phải tạo phiên bản mới và chạy lại bộ test.

---

## 12. Report và Report Builder

### 12.1. Xem report

User có thể:

- Xem report mới nhất của QA case.
- Xem report cũ.
- Xem các revision.
- So sánh hai report hoặc hai lần đo.
- Xem input, protocol và cấu hình đã tạo report.
- Export report.

### 12.2. Tùy chỉnh report toàn diện

User được toàn quyền tùy chỉnh report bằng các thành phần nghiệp vụ:

- Tiêu đề.
- Thông tin organization/site/machine.
- Thông tin QA case.
- Thông tin file đầu vào.
- Bảng metric.
- Actual/limit/margin/status.
- Gamma map.
- Dose profile.
- DVH.
- Trend chart.
- Bảng so sánh.
- BED/EQD2.
- Fractionation scenario.
- Re-irradiation proposal.
- Nhận xét của user.
- Lịch sử thay đổi.
- Thông tin người tạo và thời gian tạo.

User có thể:

- Thêm, bớt, ẩn và di chuyển block.
- Đổi tên label và tiêu đề.
- Chọn metric xuất hiện.
- Chọn khoảng thời gian của trend chart.
- Chọn điều kiện hiển thị block.
- Tạo template riêng cho từng mục đích.
- Dùng report như tài liệu phân tích, tổng hợp hoặc trình bày theo cách riêng của bệnh viện.

RT-CONNECT không áp đặt một mẫu report bắt buộc và không giới hạn người dùng trong việc tùy chỉnh nội dung report.

### 12.3. Revision và tái hiện report

Toàn quyền tùy chỉnh không đồng nghĩa với mất lịch sử. Khi report hoặc template được sửa:

- Hệ thống tạo revision mới.
- Revision cũ vẫn được xem lại.
- Snapshot lưu input, protocol, analysis configuration và template đã dùng.
- Report cũ tái hiện đúng nội dung tại thời điểm được tạo.
- User biết report có thay đổi gì so với revision trước.

### 12.4. Export

User có thể export:

- Report.
- Bảng metric.
- Gamma map.
- DVH và profile.
- Trend chart.
- Dữ liệu phân tích.
- Lịch sử revision.
- Biological calculation report độc lập.

---

## 13. Trend và so sánh QA

### 13.1. Mục tiêu

Trend giúp user xem sự thay đổi của kết quả theo thời gian và phát hiện dấu hiệu cần kiểm tra thêm.

### 13.2. Các chiều theo dõi

- Organization.
- Site/hospital.
- Machine.
- Phòng máy.
- Loại QA.
- Daily/Monthly/Annual/Custom.
- Energy/mode.
- Detector/array/film.
- Phantom.
- Protocol version.
- Người thực hiện.
- Khoảng thời gian.

### 13.3. Tính năng

- Xem trend theo một machine.
- So sánh nhiều machine trong cùng site hoặc organization.
- So sánh Daily, Monthly và Annual.
- Chọn baseline.
- Hiển thị tolerance/action level.
- Hiển thị outlier nhưng không tự xóa.
- Gắn sự kiện bảo trì, thay detector hoặc thay protocol.
- Đi từ một điểm trend về QA case và report gốc.
- Export dữ liệu trend.

---

## 14. QA Protocol Library

### 14.1. Các nhóm nội dung

- Protocol QA máy.
- Protocol PSQA.
- Protocol Daily/Monthly/Annual.
- Protocol kiểm tra detector, phantom và thiết bị đo.
- Protocol phân tích Gamma.
- Protocol DVH/Plan Review.
- Paper/guideline/reference liên quan đến QA.

### 14.2. Protocol nội bộ

Bệnh viện có thể:

- Tạo protocol mới.
- Sao chép protocol tham khảo thành bản nội bộ.
- Tùy chỉnh test, metric và giới hạn.
- Gắn lý do thay đổi.
- Gắn nguồn paper hoặc guideline.
- Lưu người biên soạn và thời điểm.
- Tạo phiên bản mới khi cập nhật.
- Giữ nguyên protocol cũ cho report đã sử dụng.

Protocol tham khảo không tự động trở thành protocol áp dụng. User phải biết đâu là nội dung tham khảo và đâu là protocol nội bộ.

---

## 15. Biological Toolkit độc lập

### 15.1. Nguyên tắc

Biological Toolkit là một tab/khu vực riêng trong RT-CONNECT. Nó là công cụ tính toán và tra cứu, không phải một phần của QA case hoặc treatment workflow.

- Không tự lấy dữ liệu từ ca QA hoặc ca bệnh.
- Không tự sửa RT Plan, prescription, TPS hoặc PACS.
- Không tạo clinical order.
- Không hiển thị kết quả như prescription.
- User chủ động nhập dữ liệu hoặc chọn dataset riêng trong tab này.
- Có thể export một calculation report độc lập.
- Calculation report không tự gắn vào report QA hoặc hồ sơ ca bệnh.

### 15.2. Các khu vực chính

- BED & EQD2.
- Đồ thị BED/EQD2 theo tổng liều D.
- So sánh hai hoặc nhiều phác đồ điều trị.
- Re-irradiation scenario.
- Bù gián đoạn hoặc thiếu fraction.
- So sánh fractionation schedule.
- Bảng giới hạn liều theo bệnh lý và OAR.
- Protocol điều trị và phác đồ điều trị.
- Alpha/beta library.
- Paper/guideline/knowledge library.
- DVH biological view khi user chủ động cung cấp RTDOSE/RTSTRUCT.
- Lịch sử tính toán.

### 15.3. BED và EQD2

Với mô hình LQ cơ bản:

\[
BED = nd\left(1+\frac{d}{\alpha/\beta}\right)
\]

\[
EQD2 = \frac{BED}{1+\frac{2}{\alpha/\beta}}
\]

User phải nhìn thấy:

- Số fraction `n`.
- Liều mỗi fraction `d`.
- Tổng liều `D`.
- Alpha/beta.
- Đơn vị.
- Mô hình.
- Nguồn tham khảo.
- Giả định của lần tính.

### 15.4. Đồ thị BED/EQD2 theo tổng liều D

User có thể:

- Chọn alpha/beta.
- Chọn số fraction.
- Thay đổi tổng liều D.
- Xem BED và EQD2 tương ứng.
- Hiển thị nhiều đường cong cho nhiều alpha/beta.
- So sánh mô hình của target và OAR.
- Đọc giá trị tại một điểm trên đồ thị.
- Export đồ thị và dữ liệu.

### 15.5. So sánh hai phác đồ điều trị

User có thể nhập hai hoặc nhiều phác đồ, mỗi phác đồ gồm:

- Tên phác đồ.
- Bệnh lý hoặc clinical scenario.
- Tổng liều.
- Số fraction.
- Liều mỗi fraction.
- Thời gian điều trị nếu có.
- Mô hoặc OAR được dùng để tính.
- Alpha/beta.
- Nguồn tham khảo.

Kết quả gồm:

- BED của từng phác đồ.
- EQD2 của từng phác đồ.
- Chênh lệch BED/EQD2.
- Bảng so sánh.
- Đồ thị so sánh.
- Cảnh báo khi hai phác đồ không phù hợp để so sánh trực tiếp.

### 15.6. Bảng giới hạn liều theo bệnh lý

Bảng giới hạn liều có thể được tổ chức theo:

- Bệnh lý.
- Vị trí giải phẫu.
- Mục tiêu điều trị.
- Kỹ thuật xạ trị.
- OAR hoặc target.
- Metric.
- Giới hạn.
- Số fraction.
- Alpha/beta nếu có.
- Nguồn paper/guideline.
- Mức độ bằng chứng.
- Điều kiện áp dụng.
- Ngày cập nhật.

Mỗi giới hạn phải cho biết là giá trị tham khảo, giá trị nội bộ hay giá trị user nhập. Bảng này phục vụ tính toán và tra cứu, không tự trở thành prescription hoặc clinical order.

### 15.7. Protocol điều trị, phác đồ điều trị và knowledge library

Một nội dung điều trị trong Biological Toolkit có thể gồm:

- Tên bệnh lý.
- Phân nhóm bệnh.
- Vị trí giải phẫu.
- Clinical scenario.
- Phác đồ tham khảo.
- Tổng liều và số fraction.
- Hướng dẫn contour target/OAR.
- Hướng dẫn lập kế hoạch.
- Tiêu chí target/OAR.
- Alpha/beta tham khảo.
- Công thức và lý thuyết liên quan.
- Paper/guideline.
- DOI/URL.
- Tóm tắt nội bộ.
- Mức độ bằng chứng.
- Giới hạn áp dụng.
- Ngày cập nhật.

Nội dung trong khu vực này là knowledge và công cụ hỗ trợ tính toán. Nó không tự liên kết với QA case, bệnh nhân, RTPLAN hoặc treatment course.

### 15.8. Re-irradiation scenario

Re-irradiation Calculator phải cho phép user:

- Nhập nhiều course.
- Ghi ngày hoặc khoảng thời gian giữa các course.
- Nhập tổng liều, số fraction và liều mỗi fraction của từng course.
- Chọn mô, OAR hoặc target.
- Chọn alpha/beta cho từng mô.
- Ghi nguồn alpha/beta.
- Nhập recovery assumption nếu muốn dùng.
- So sánh không recovery và có recovery.
- So sánh nhiều scenario.
- Tính BED/EQD2 từng course.
- Tính tổng BED/EQD2 theo scenario.
- Hiển thị chênh lệch giữa các phương án.
- Hiển thị cảnh báo khi thiếu thời gian, volume, structure hoặc giả định cần thiết.
- Lưu và export scenario.

Khi user cung cấp RTDOSE/RTSTRUCT riêng cho Biological Toolkit, hệ thống có thể hỗ trợ phân tích theo structure. Nếu muốn cộng liều theo không gian, dữ liệu phải có thông tin hình học hoặc registration phù hợp; nếu không đủ thông tin, hệ thống chỉ thực hiện so sánh scalar và ghi rõ giới hạn.

Kết quả re-irradiation luôn được hiển thị dưới dạng scenario hoặc calculation estimate. Hệ thống không tự chọn phương án cuối cùng, không tự sửa prescription và không tự gửi dữ liệu sang TPS/PACS.

### 15.9. Bù fraction và gián đoạn điều trị

Tool phải phân biệt:

- Lịch ban đầu.
- Số fraction đã thực hiện.
- Liều đã thực hiện.
- Fraction bị thiếu hoặc gián đoạn.
- Fraction còn lại.
- Tổng thời gian điều trị.
- Các phương án thay thế.

Kết quả là các scenario để so sánh. User có thể đưa scenario vào calculation report độc lập.

### 15.10. Lịch sử và giải thích

Mỗi lần tính phải lưu:

- Input.
- Mô hình.
- Alpha/beta.
- Nguồn tham khảo.
- Scenario.
- Người thực hiện.
- Thời gian.
- Kết quả.
- Cảnh báo.
- Phiên bản công thức hoặc engine.

---

## 16. Version, provenance và lịch sử

### 16.1. Đối tượng có version

- File artifact.
- Analysis configuration.
- Analysis result.
- Report template.
- Report.
- QA protocol.
- QA protocol rule.
- Biological scenario.
- Biological knowledge content.
- Treatment protocol reference.

### 16.2. Nguyên tắc version

- Không ghi đè file gốc.
- Không làm mất kết quả cũ.
- Không thay đổi protocol cũ đã được dùng trong report.
- Có thể tạo revision mới từ revision cũ.
- User có thể xem nội dung trước và sau.
- User có thể biết lý do thay đổi nếu lý do được ghi nhận.
- Report cũ tái hiện đúng dữ liệu, protocol và cấu hình tại thời điểm tạo.
- Thay đổi công thức hoặc engine tạo phiên bản mới.

---

## 17. Quy tắc nghiệp vụ chính

| Mã | Quy tắc |
| :--- | :--- |
| BR-001 | User chỉ xem và sử dụng dữ liệu của organization mà mình là thành viên. |
| BR-002 | Trong cùng organization, bác sĩ, kỹ sư và thành viên chuyên môn có quyền sử dụng nghiệp vụ ngang nhau. |
| BR-003 | QA case theo máy đi qua organization → site/hospital → machine → QA case. |
| BR-004 | QA case phải gắn với đúng machine để đưa vào trend. |
| BR-005 | User được tạo folder và đặt tên theo cách riêng của organization. |
| BR-006 | QA case và report không bị mất khi folder được đổi tên, di chuyển hoặc archive. |
| BR-007 | PSQA Gamma bắt buộc có RTDOSE và dữ liệu đo/đối chiếu. |
| BR-008 | RTSTRUCT không bắt buộc trong PSQA Gamma phantom/plane thông thường. |
| BR-009 | RTSTRUCT bắt buộc khi workflow cần DVH theo OAR/target. |
| BR-010 | Gamma configuration được lưu cùng analysis result. |
| BR-011 | Report liên kết được với input, protocol và analysis configuration. |
| BR-012 | Mọi chỉnh sửa report tạo revision mới và không làm mất revision cũ. |
| BR-013 | Protocol đã dùng cho report cũ không bị cập nhật ngược. |
| BR-014 | Alpha/beta phải có nguồn hoặc được đánh dấu là user override. |
| BR-015 | Fraction compensation chỉ tạo scenario/proposal, không tự tạo prescription. |
| BR-016 | Re-irradiation chỉ tạo scenario/calculation estimate tham khảo. |
| BR-017 | Biological Toolkit là tab độc lập, không tự liên kết với QA case hoặc ca bệnh. |
| BR-018 | Re-irradiation không tự sửa RT Plan, TPS hoặc PACS. |
| BR-019 | Mọi thay đổi được ghi user, thời gian, nội dung và version. |
| BR-020 | Không làm mất audit history, report revision, protocol version hoặc calculation history. |
| BR-021 | `PASS` chỉ phản ánh rule của protocol đã chọn, không phải kết luận an toàn tuyệt đối. |
| BR-022 | Dữ liệu Gamma mơ hồ về cột, đơn vị hoặc geometry không được tự động đoán. |
| BR-023 | Khi cấu hình hoặc engine thay đổi, analysis result mới được lưu riêng. |
| BR-024 | Biological Toolkit có thể tính và xuất report độc lập nhưng không tạo clinical order. |
| BR-025 | Bộ test tính toán là căn cứ nghiệm thu ban đầu của engine; dataset thật được dùng cho pilot và cải tiến tiếp theo. |
| BR-026 | RT-CONNECT có thể được truy cập từ xa qua website/HTTPS bởi các thành viên của organization; yêu cầu này không tạo phân cấp hoặc quyền theo từng hành động. |
| BR-027 | Google Stitch là nguồn thiết kế trực quan; business-analysis.md mới là nguồn quy tắc nghiệp vụ và tiêu chí nghiệm thu. |
| BR-028 | Việc xóa `UI-UX.md` không xóa requirement; screen còn thiếu phải được bổ sung trên Stitch trong phase của module tương ứng. |
| BR-029 | Supabase chỉ quản lý identity/session; dữ liệu nghiệp vụ, QA, report, protocol, audit và Biological Toolkit nằm trong PostgreSQL của Railway. |
| BR-030 | Browser không được nhận Railway token, database credential, Supabase service-role key hoặc secret triển khai. |
| BR-031 | Mỗi module phải được nghiệm thu theo workflow end-to-end, không chỉ bằng ảnh Stitch, component tĩnh, API đơn lẻ hoặc deploy thành công. |
| BR-032 | Mỗi screen Stitch được triển khai phải map được tới module, route, dữ liệu, event, trạng thái và tiêu chí nghiệm thu tương ứng. |
| BR-033 | Release production phải đi qua staging, migration, backup/restore, remote smoke test và rollback evidence trước khi được coi là hoàn tất. |
| BR-034 | Identity đã xác thực nhưng chưa có membership phải được đưa vào luồng khởi tạo organization, không được xem dữ liệu organization như anonymous user. |
| BR-035 | Luồng khởi tạo organization gắn identity hiện tại làm thành viên đầu tiên và không tạo action-level role hierarchy. |

---

## 18. Tiêu chí nghiệm thu nghiệp vụ

### 18.1. Organization và machine

- Identity mới đăng nhập được hướng dẫn tạo organization nếu chưa có membership.
- Tạo organization thành công phải tạo đồng thời `UserIdentity`, `OrganizationMembership` và organization context.
- Sau khi tạo organization, user có thể tạo site/hospital và machine trong cùng workflow.
- Identity đã có organization context không được tạo thêm organization qua luồng khởi tạo lần đầu.

- Tạo được một organization có nhiều site/hospital.
- Một site/hospital tạo được nhiều machine.
- QA case luôn hiển thị đúng site và machine.
- Machine giữ được trend khi tên hiển thị thay đổi.
- Trend của Machine A không trộn với Machine B.

### 18.2. Folder và QA archive

- User tạo được folder và folder con.
- User đổi tên hoặc di chuyển folder mà không làm mất QA case.
- Có thể lọc Daily/Monthly/Annual.
- Có thể tìm report theo năm, site, machine, loại QA và protocol.
- Có thể xem report mới nhất và các revision cũ.
- Có thể archive mà vẫn xem lại lịch sử.

### 18.3. DICOM workflow

- PSQA không cho chạy khi thiếu RTDOSE.
- PSQA không bị chặn chỉ vì thiếu RTSTRUCT.
- Visual Dose Review cho phép xem RTSTRUCT khi user muốn đánh giá OAR/PTV.
- DVH review yêu cầu RTDOSE và RTSTRUCT.
- Biological scalar calculation có thể chạy khi chỉ có dữ liệu fraction.
- Hệ thống phát hiện sai hoặc thiếu UID, geometry, grid, đơn vị và liên kết reference.
- File gốc không bị thay đổi sau khi import hoặc phân tích.

### 18.4. Gamma và QA analysis

- User chọn được preset Gamma.
- User thay đổi được các tham số được cho phép.
- Cấu hình Gamma được lưu lại và xem lại trong report.
- Kết quả có pass rate, map, cảnh báo và trạng thái.
- Có thể chạy lại analysis với cấu hình khác mà không xóa kết quả cũ.
- Contract `gamma.measurement.v1` được kiểm tra trước khi chạy.
- Dữ liệu JSON/CSV mơ hồ bị từ chối hoặc yêu cầu user bổ sung thông tin.

### 18.5. Bộ test engine

- Bộ test Gamma 2D/3D đạt kết quả mong đợi.
- Bộ test global/local và absolute/relative đạt kết quả mong đợi.
- Bộ test grid, shift, dose thấp và biên trường đạt kết quả mong đợi.
- Bộ test dữ liệu lỗi trả về cảnh báo hoặc invalid phù hợp.
- Bộ test DVH chuẩn đạt kết quả mong đợi.
- Bộ test BED/EQD2 đạt kết quả mong đợi.
- Mỗi thay đổi engine đều chạy lại bộ test.

### 18.6. Report

- User tạo được report từ template.
- User thêm, bớt, ẩn, đổi tên và sắp xếp block.
- User chọn được metric, biểu đồ và khoảng thời gian trend.
- Report có thể export.
- Report revision lưu đúng nội dung, user và thời gian.
- Report cũ tái hiện đúng dữ liệu và protocol đã dùng.
- Có thể export calculation report độc lập từ Biological Toolkit.

### 18.7. QA Protocol Library

- User tạo được QA protocol nội bộ.
- Có thể tạo version mới mà không thay đổi version cũ.
- Protocol có nguồn tham chiếu.
- Rule QA được lưu theo protocol version.
- Report cũ vẫn giữ đúng protocol version đã sử dụng.

### 18.8. Biological Toolkit

- BED/EQD2 được tính đúng với bộ test đã xác định.
- Có đồ thị BED/EQD2 theo tổng liều D.
- User so sánh được hai hoặc nhiều phác đồ điều trị.
- User tạo được scenario bù fraction.
- User tạo được re-irradiation scenario nhiều course.
- Có thể chọn alpha/beta và ghi nguồn.
- Có thể nhập recovery assumption và hiển thị giả định.
- Có bảng giới hạn liều theo bệnh lý/OAR kèm nguồn.
- Có protocol điều trị, phác đồ điều trị và knowledge library riêng.
- Biological Toolkit không tự liên kết với QA case hoặc ca bệnh.
- Scenario không tự động thay đổi prescription hoặc RT Plan.
- Lịch sử tính toán hiển thị đầy đủ input, model, alpha/beta, source, user và thời gian.

### 18.9. Dataset thật và cải tiến

- Giai đoạn phát triển được nghiệm thu bằng bộ test/reference dataset.
- Có thể đưa dataset thật vào giai đoạn pilot/vận hành.
- Trường hợp thực tế phát hiện lỗi được lưu thành test case mới.
- Bản sửa engine hoặc workflow tạo version mới và không làm mất kết quả cũ.

### 18.10. Truy cập web từ xa

- Website mở được từ một mạng bên ngoài hạ tầng triển khai.
- HTTPS và domain hoạt động đúng.
- Thành viên đăng nhập được và sử dụng các chức năng nghiệp vụ ngang nhau trong organization.
- Organization không truy vấn lẫn dữ liệu.
- Upload artifact, chạy analysis, xem report và export hoạt động qua mạng ngoài.
- Biological Toolkit vẫn hoạt động độc lập với QA case.
- Mất kết nối hoặc refresh browser không làm mất artifact hoặc tạo analysis trùng.
- Database, queue, worker và DICOM gateway không mở public; object storage không cho anonymous bucket access, nhưng signed HTTPS download đúng scope được phép.

### 18.11. Nghiệm thu theo module và Google Stitch

- MOD-00 đến MOD-16 có owner, dependency, input, output và tiêu chí đóng module trong `plan.md`.
- Mỗi module có route/màn hình tương ứng trên Stitch hoặc được ghi rõ là module nền không cần screen riêng.
- Bốn application screen đang hoạt động được giữ bằng screen ID ổn định; màn hình mới phải ghi Screen ID sau khi tạo. Instance Biological cũ ở trạng thái hidden/deprecated không được dùng trong mapping module.
- Screen mới được tạo trong đúng Google Stitch project `RT-connect`, dùng dữ liệu giả lập và có trạng thái loading, empty, error, warning và success phù hợp.
- Frontend triển khai được đối chiếu với screenshot/HTML/design tokens từ Stitch nhưng hành vi phải theo API contract và quy tắc nghiệp vụ.
- Không xem resource tài liệu hoặc ảnh asset mà Stitch liệt kê như một application screen.
- Module có tác vụ bất đồng bộ chỉ hoàn thành khi refresh/mất kết nối tạm thời không tạo job hoặc result trùng.
- Module có dữ liệu version/revision chỉ hoàn thành khi phiên bản cũ vẫn xem hoặc tái hiện được.
- Module chỉ được đưa lên production sau khi pass trên staging và có remote smoke test phù hợp.

---

## 19. Trình tự phát triển

Trình tự chi tiết nằm trong `plan.md`. Ở mức nghiệp vụ, sản phẩm được bàn giao theo các release stream sau:

### Stream A — Nền tảng có thể phát triển và truy cập trên staging

- Baseline yêu cầu, mapping Stitch và module traceability.
- Repository, test harness và CI.
- Railway staging, PostgreSQL và backend shell.
- Supabase Auth và organization context.
- Application shell, Home Dashboard và navigation.

### Stream B — Clinical MVP theo từng module hoàn chỉnh

1. Organization/Site/Machine và QA Archive/Folder/QACase.
2. Artifact upload, checksum, DICOM validation và Input Manifest.
3. Machine QA và metric/rule engine.
4. PSQA Gamma.
5. Report Builder/revision/export.
6. Trend.
7. QA Protocol Library.

Mỗi module được đưa lên staging ngay khi hoàn thành để người dùng có thể kiểm tra workflow từ xa; không chờ tới cuối dự án mới kiểm tra deployment.

### Stream C — Biological Toolkit theo từng module độc lập

1. Biological Hub và calculation history.
2. BED/EQD2 và đồ thị theo tổng liều D.
3. So sánh phác đồ.
4. Re-irradiation và bù fraction.
5. Dose-limit table, treatment protocol và knowledge library.
6. Calculation report độc lập.

### Stream D — Phân tích DICOM mở rộng

- Visual Dose Review.
- DVH/Plan Review.
- Structure-level biological view khi user chủ động cung cấp dataset.
- Các measurement/vendor adapter và DICOM gateway mở rộng.

### Stream E — Hardening, pilot và production remote access

- Integrated/golden/E2E test.
- Performance, worker reliability và tenant isolation.
- Dataset thật trong pilot và bổ sung regression case.
- Domain, HTTPS, migration, backup/restore, monitoring và rollback.
- Public production URL chỉ sau khi staging/pilot đạt tiêu chí release.
- Public frontend/API; PostgreSQL, queue, worker và DICOM gateway private. Object storage dùng authenticated access hoặc signed HTTPS URL có hạn, không public bucket.

---

## 20. Kết luận nghiệp vụ

RT-CONNECT là hệ thống quản lý và phân tích QA xạ trị kết hợp một Biological Toolkit độc lập. Các thành viên chuyên môn trong cùng organization được sử dụng nghiệp vụ ngang nhau; tài liệu không xây dựng phân cấp bác sĩ–kỹ sư hoặc phân quyền theo hành động.

Clinical MVP tập trung vào Machine QA, PSQA Gamma, report, trend, input validation và provenance. Biological Toolkit được tổ chức thành tab riêng, phục vụ tính toán BED/EQD2, đồ thị, so sánh phác đồ, giới hạn liều, protocol điều trị, knowledge library và re-irradiation scenario mà không gắn mặc định với QA case hoặc ca bệnh.

`specification.md`, `technical-specification.md` và `plan.md` được xây dựng từ các yêu cầu, quy tắc và tiêu chí nghiệm thu trong tài liệu này. Google Stitch cung cấp thiết kế trực quan; Railway và Supabase cung cấp hạ tầng đã chọn; không nguồn nào trong số đó được tự thay thế hoặc làm mất requirement nghiệp vụ.


## 21. Catalogue tính năng chi tiết và hợp đồng nghiệp vụ v0.8

Bổ sung ngày 2026-09-08 theo yêu cầu chi tiết hóa toàn bộ dự án. Các mục 1–20 giữ bối cảnh; mục 21 làm rõ hành vi, ngoại lệ, phục hồi và phạm vi nghiệm thu. `specification.md` v1.2 quy định hợp đồng hành vi/dữ liệu chi tiết; `plan.md` v2.2 quy định task, workflow, test, evidence và exit gate theo P0–P20. Kiến trúc nền tiếp tục tham chiếu `technical-specification.md`.

### 21.1. Các quyết định sản phẩm giữ nguyên

- Thành viên cùng organization ngang quyền; không thêm cấp phê duyệt bác sĩ/kỹ sư hay action roles. Membership là ranh giới dữ liệu và xác định tổ chức của tài khoản.
- User được tùy chỉnh toàn bộ report. Không có canonical block bắt buộc, không ép report giữ cảnh báo/label hoặc lịch sử. Lịch sử nguồn được giữ ở hệ thống để xem lại; việc ẩn block không sửa kết quả engine gốc.
- Không thêm vòng đời phê duyệt QA case/report. Trạng thái file, lưu nháp, export và job chỉ diễn tả tiến trình kỹ thuật. PASS/FAIL là kết quả rule, không phải quyền thao tác.
- Biological Toolkit, re-irradiation và bù fraction là công cụ tính toán/scenario riêng. Bảng dose limits và protocol điều trị là thư viện tham khảo, không tự gắn vào hồ sơ QA hay bệnh nhân.
- Nghiệm thu phát triển bằng test/golden/reference dataset đã mô tả. Pilot/dataset thực tế thuộc P18 và cải tiến P20; không bổ sung phase pháp luật/FDI hoặc quy trình commissioning ngoài lựa chọn đã thống nhất. PASS kiểm thử chỉ chứng minh phạm vi được kiểm thử.
- P17 có thể không chặn phát hành R1 sớm, nhưng phải hoàn tất trong mục tiêu toàn dự án P0–P19. Spatial re-irradiation không mặc định nằm trong P15 scalar; chỉ công bố capability khi có hợp đồng transform, dữ liệu và test tương ứng.
- Những yêu cầu chi tiết mới như invitation, restore và sửa đồng thời là phần còn phải triển khai/xác minh; sự hiện diện trong tài liệu không có nghĩa code đã có.

### 21.2. Hành vi chung người dùng cần thấy

| Tình huống | Hành vi nghiệp vụ phải có |
| :--- | :--- |
| Mới vào trang | Có tiêu đề, context tổ chức, trạng thái tải và hành động chính đúng module. |
| Chưa có dữ liệu | Hiển thị rỗng đúng nghĩa và hướng dẫn bước đầu; không bịa dữ liệu minh họa trong workspace thật. |
| Nhập sai | Đánh dấu field, giữ input hợp lệ, mô tả cần sửa gì; không đổi số hoặc đơn vị ngầm. |
| Đang lưu/tính/export | Chỉ rõ thao tác đang chạy; job đã nhận có ID/history, tiếp tục được sau refresh. |
| Mất mạng sau gửi | Phân biệt chưa gửi với chưa biết kết quả; kiểm tra thao tác đã lưu trước khi tạo lại. |
| Hai người sửa | Báo xung đột phiên bản, cho xem bản mới/copy draft; không ghi đè im lặng. |
| Lỗi dịch vụ | Hết chờ trong thời gian xác định, có retry và mã hỗ trợ; không hiện stack trace hoặc mật khẩu. |
| Kết quả vượt giới hạn | Hiển thị FAIL/WARNING cùng actual/limit; đây là kết quả tính hợp lệ, khác lỗi không tính được. |
| Đổi tên/di chuyển/archive | ID nguồn và history giữ nguyên; có màn hình tìm lại dữ liệu archived. |
| Đổi protocol/model/template | Tạo version/result/revision mới; bản cũ không lấy dữ liệu live thay cho snapshot. |
| Thao tác chuyên sâu chưa hỗ trợ | Nêu capability chưa có, không hiển thị điều khiển hoạt động mà engine bỏ qua. |
| Hủy/đóng tab | Đóng tab không ngầm hủy job đã nhận; hủy tác vụ chỉ được cung cấp nếu backend có contract riêng. |

### 21.3. Tính năng theo phase và module

Mã FR-Pxx-yy là yêu cầu có thể truy vết. Các phase nền tảng/triển khai cũng có FR về khả năng vận hành; đây không phải tab nghiệp vụ mới. Mỗi nhóm có workflow và dữ liệu tối thiểu; các biến thể chạy đúng/lỗi/cách phục hồi được định danh TC-Pxx-Syy/Eyy trong plan.

#### P0 — Baseline, phạm vi và truy vết

**Module:** MOD-00–MOD-16. **Mục tiêu người dùng:** Một baseline tài liệu thống nhất, mọi yêu cầu có phase và tiêu chí kiểm chứng.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P00-01 | Duy trì cùng một phạm vi sản phẩm giữa nghiệp vụ, hợp đồng hành vi và kế hoạch. |
| FR-P00-02 | Mỗi tính năng có mã và điều kiện nghiệm thu đo được. |
| FR-P00-03 | Giữ bằng chứng cũ theo thời điểm, không biến lịch sử thành trạng thái hiện tại. |
| FR-P00-04 | Quản lý thay đổi yêu cầu có tác động, dependency và kiểm thử liên quan. |

**Thông tin tối thiểu:** Phiên bản tài liệu; BR/MOD/FR; route; API operation; test ID; trạng thái evidence; design project/screen/version.

**Luồng chính:** Đọc nghiệp vụ và các quyết định đã thống nhất. → Đối chiếu source, route, migration, test và evidence cũ. → Gắn requirement vào module, phase và test case. → Ghi khác biệt giữa requirement và code thành gap có owner. → Khóa baseline tài liệu và chọn gói công việc chưa đạt đầu tiên.

**Nghiệm thu nhóm:** 100% FR trong catalogue được gán phase/test; không còn xung đột phạm vi chưa có quyết định.

#### P1 — Runtime local, repository và CI

**Module:** MOD-16. **Mục tiêu người dùng:** Clone sạch có thể build, migrate, chạy và kiểm thử theo hướng dẫn.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P01-01 | Khởi động lặp lại được trên máy mới. |
| FR-P01-02 | Nhận biết hệ thống sẵn sàng hay thiếu thành phần. |
| FR-P01-03 | Phân biệt cấu hình local với staging/production. |
| FR-P01-04 | Có bộ kiểm thử tự động trước khi bàn giao thay đổi. |

**Thông tin tối thiểu:** Python/Node version; lockfiles; API/web build SHA; schema head; môi trường local; tên biến cấu hình.

**Luồng chính:** Chuẩn bị runtime theo lockfile. → Khởi động PostgreSQL, Redis và object storage local. → Chạy migration và seed synthetic. → Build web/API; kiểm tra health và route. → Chạy CI trên commit tương ứng, lưu kết quả và hướng dẫn khởi động.

**Nghiệm thu nhóm:** Clean setup và restart pass; CI bắt buộc xanh; migration DB rỗng/upgrade có evidence.

#### P2 — Railway staging, PostgreSQL và nền tảng Supabase Auth

**Module:** MOD-00, MOD-16. **Mục tiêu người dùng:** API staging, database và xác minh identity hoạt động với cấu hình đúng môi trường.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P02-01 | Truy cập staging từ xa qua HTTPS. |
| FR-P02-02 | Đăng nhập được xác minh bởi Supabase đúng môi trường. |
| FR-P02-03 | Dữ liệu nghiệp vụ nằm trong PostgreSQL Railway. |
| FR-P02-04 | Phân biệt lỗi process, migration, database và identity. |

**Thông tin tối thiểu:** Project/environment/service IDs; branch/SHA; Dockerfile/root; PORT; API URL; DB service reference; issuer/audience/JWKS; Auth redirect allowlist.

**Luồng chính:** Đối chiếu service ID và môi trường. → Cấu hình DB reference, PORT và Auth staging. → Build đúng source; chạy pre-deploy migration. → Xác nhận liveness, DB connectivity và schema revision riêng. → Dùng token staging kiểm tra API; lưu deployment manifest không secret.

**Nghiệm thu nhóm:** Đúng source và environment; health, schema, JWT hợp lệ/lỗi pass; không dùng production DB cho smoke staging.

#### P3 — App Shell, đăng nhập, onboarding và Home Dashboard

**Module:** MOD-00, MOD-01. **Mục tiêu người dùng:** Bác sĩ/kỹ sư đăng nhập, vào đúng organization và hiểu trạng thái công việc.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P03-01 | Đăng nhập, đăng xuất, recovery và quay lại trang đang làm. |
| FR-P03-02 | Onboarding organization khi identity hợp lệ chưa có membership. |
| FR-P03-03 | Dashboard machine, QA gần đây, cảnh báo và job theo tổ chức. |
| FR-P03-04 | Điều hướng nhất quán, dùng được bằng bàn phím và trên màn hình nhỏ. |

**Thông tin tối thiểu:** Email/identity; return path nội bộ; organization context; widget counters/recent QA/jobs; loading/empty/error; module availability.

**Luồng chính:** Mở URL hoặc deep-link. → Đăng nhập/khôi phục session và bootstrap identity. → Nếu chưa thuộc tổ chức, tạo organization đầu tiên; nếu đã có thì vào workspace. → Hiển thị dashboard dữ liệu thật và thao tác nhanh. → Logout hoặc hết session thì dọn cache và quay lại đúng luồng đăng nhập.

**Nghiệm thu nhóm:** Happy path, first-use, expiry, offline, deep-link và logout cache tests pass trên staging.

#### P4 — Organization, Site, Machine và thành viên ngang hàng

**Module:** MOD-02. **Mục tiêu người dùng:** Quản lý cấu trúc bệnh viện, thiết bị và đưa đồng nghiệp vào đúng tổ chức.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P04-01 | Tạo, sửa, tìm và archive/restore site/machine. |
| FR-P04-02 | Machine có định danh ổn định qua đổi tên và sự kiện bảo trì. |
| FR-P04-03 | Thêm thành viên bằng lời mời có xác thực; mọi thành viên có chức năng ngang nhau. |
| FR-P04-04 | Xem lịch sử thay đổi hierarchy và thành viên, không mất hồ sơ QA. |

**Thông tin tối thiểu:** Organization name/timezone; site name/code; machine stable ID/name/code/manufacturer/model/energy/mode/status; membership identity/status; revision.

**Luồng chính:** Mở quản lý organization. → Tạo site, tạo machine thuộc site. → Đổi tên/thông tin máy và xem history. → Mời đồng nghiệp bằng luồng nhận lời mời xác thực vào đúng tổ chức. → Archive/restore đối tượng và kiểm tra QA/trend cũ còn đúng định danh.

**Nghiệm thu nhóm:** Hai identity cùng organization dùng được nghiệp vụ; isolate organization khác; rename/archive/restore/concurrent edit pass.

#### P5 — QA Archive, Folder và QA Case

**Module:** MOD-03. **Mục tiêu người dùng:** Tổ chức hồ sơ như cây thư mục và tìm đúng case bằng metadata.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P05-01 | Tạo cây folder lồng nhau, đổi tên và di chuyển về root hoặc folder khác. |
| FR-P05-02 | Tạo case Daily/Monthly/Annual/Custom, phân loại theo machine và ngày thực hiện. |
| FR-P05-03 | Tìm/lọc/sắp xếp/phân trang kết hợp; giữ filter trong URL. |
| FR-P05-04 | Archive/restore không mất input, analysis, report và audit. |

**Thông tin tối thiểu:** Folder name/parent/path/revision; case title/type/cycle/performed_at/site/machine/folder/protocol reference/tags/note; include_archived; search filters.

**Luồng chính:** Tạo cây folder và chọn vị trí. → Tạo case đúng site/machine/cycle/thời điểm. → Tìm bằng text và kết hợp filter, mở deep-link. → Rename/move subtree hoặc chuyển case. → Archive/restore và xem lại case/run/report theo ID cũ.

**Nghiệm thu nhóm:** Nested move, archive/restore, combined search, cross-scope và deep-link tests có evidence.

#### P6 — Upload, Artifact, Manifest và Validation

**Module:** MOD-04. **Mục tiêu người dùng:** Lưu nguyên byte, phân loại đúng và giải thích dữ liệu có dùng được cho workflow hay không.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P06-01 | Upload từng file và hàng đợi nhiều file có trạng thái riêng. |
| FR-P06-02 | Phân biệt file trùng byte/type/role và file cùng tên khác nội dung. |
| FR-P06-03 | Input Manifest có geometry, đơn vị và nguồn để truy nguyên. |
| FR-P06-04 | Validation chi tiết, download nguyên bản và xem lịch sử validation/derived file. |

**Thông tin tối thiểu:** Filename/type/media type/size/SHA256; artifact ID; logical roles; SOP/Study/Series/Frame UIDs; grid/scaling/units; detector/phantom/acquisition; validator version/findings.

**Luồng chính:** Chọn case và file, type/role; hiển thị tên và kích thước trước gửi. → Upload có progress; server kiểm size/checksum và lưu object. → Commit artifact + manifest; hiển thị thành công hoặc duplicate rõ ràng. → Validate nội dung và liên kết dataset; xem findings theo field. → Download file, xác nhận checksum; retry hoặc tạo derived revision khi cần sửa.

**Nghiệm thu nhóm:** Real browser upload→validate→download checksum, duplicate/type/role, interrupted upload và storage failure tests pass.

#### P7 — Machine QA checklist, rule engine và history

**Module:** MOD-05. **Mục tiêu người dùng:** Nhập phép đo, áp protocol đã chọn, xem kết quả và so sánh các lần QA.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P07-01 | Checklist theo Daily/Monthly/Annual/Custom có protocol version. |
| FR-P07-02 | Lưu nháp phép đo, ghi N/A có lý do và đính kèm dữ liệu. |
| FR-P07-03 | Rule range/min/max/deviation với actual, limit, margin, trạng thái và giải thích. |
| FR-P07-04 | Rerun/compare giữ nguyên kết quả cũ và liên kết trend. |

**Thông tin tối thiểu:** Protocol version/rules; metric key/value/unit/required/N-A reason; baseline/tolerance/action; notes/artifact; measurement revision; result actual/limit/margin/status.

**Luồng chính:** Tạo run từ case và protocol version. → Nhập metric, unit và ghi chú; lưu draft. → Validate required/unit/baseline; evaluate một snapshot. → Xem từng metric và kết quả tổng, drill-down về rule. → Rerun tạo lượt mới; compare; đưa metric tương thích vào trend.

**Nghiệm thu nhóm:** Boundary PASS/WARNING/FAIL/N-A, unit/baseline errors và rerun/projection uniqueness đều pass.

#### P8 — PSQA Gamma, RTDOSE, worker và kết quả 2D/3D

**Module:** MOD-06. **Mục tiêu người dùng:** Chạy PSQA từ RTDOSE + comparison qua worker, giữ cấu hình và kết quả tái hiện được.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P08-01 | PSQA bắt buộc RTDOSE và comparison; ENGINE_TEST JSON-only phải được phân biệt rõ. |
| FR-P08-02 | Gamma 2D/3D với tham số đầy đủ và preflight giải thích lỗi/cảnh báo. |
| FR-P08-03 | Job bất đồng bộ có progress, retry, timeout và kết quả tồn tại sau reconnect. |
| FR-P08-04 | Map, histogram, thống kê, dose profile, comparison và nguồn dữ liệu/cấu hình. |

**Thông tin tối thiểu:** Workflow PSQA hoặc ENGINE_TEST; reference/evaluation artifact+role; 2D/3D; DD mode/value; DTA; global/local; threshold/reference level; alignment/frame; interpolation/search/max gamma; ROI; field/composite; run/attempt/engine.

**Luồng chính:** Chọn RTDOSE reference và comparison validated; optional RTPLAN/RTSTRUCT theo mục đích. → Preflight units/geometry/config/profile và ước lượng tài nguyên. → Enqueue idempotent, lưu input/config/engine snapshot; theo dõi trạng thái qua refresh. → Worker claim/heartbeat/tính/lưu result rồi ack. → Xem map/histogram/pass rate/profiles; compare, rerun config mới hoặc retry lỗi hạ tầng.

**Quy tắc nghiệp vụ bổ sung:** PSQA mặc định chỉ nhận reference là DICOM RTDOSE đã validated; comparison là measurement hợp lệ hoặc RTDOSE hợp lệ. JSON-only chỉ được chạy khi người dùng chọn rõ `ENGINE_TEST`, và kết quả phải mang nhãn engineering test, không được tự hiển thị như một kết quả PSQA clinical. `FULL_ROI` không được loại điểm reference thiếu candidate khỏi mẫu số; nếu thiếu coverage thì kết quả phải báo không hợp lệ/pass rate không có giá trị. `OVERLAP_ONLY` là lựa chọn explicit và phải hiển thị tỷ lệ coverage cùng số điểm loại. `max_gamma` là cận tìm kiếm; điểm vượt cận là censored/non-passing, không được hiển thị như một gamma exact. Mỗi lần retry có attempt riêng; worker cũ không được ghi đè kết quả sau khi mất lease. Các quy tắc này không tạo phân cấp hay quyền phê duyệt giữa bác sĩ và kỹ sư.

**Nghiệm thu nhóm:** Tất cả profile được công bố có golden/error tests; RTDOSE+measurement 3D staging, worker crash/retry/concurrency và large workload đạt budget.

#### P9 — Report Builder, revision, preview và export

**Module:** MOD-07. **Mục tiêu người dùng:** Người dùng tùy chỉnh toàn bộ report và xem lại đúng bản từng xuất.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P09-01 | Toàn quyền bố cục, block, label, metric, chart, điều kiện hiển thị và ghi chú. |
| FR-P09-02 | Lưu template/version và report revision, compare trước/sau. |
| FR-P09-03 | Preview và export đa định dạng với tiếng Việt và bảng dài. |
| FR-P09-04 | Truy nguyên nguồn riêng trên màn hình history; report không bị ép block bắt buộc. |

**Thông tin tối thiểu:** Report/title/source refs; template version; block stable IDs/type/label/order/visible/config; notes; revision; render options/font/locale; export format/status/hash.

**Luồng chính:** Chọn case/run hoặc tạo calculation report trong namespace Biological. → Chọn template, thêm/xóa/ẩn/đổi tên/sắp xếp block. → Preview từ snapshot và lưu revision. → Xuất PDF/PNG/CSV/JSON; theo dõi render job. → Mở revision cũ, compare hoặc tạo revision mới, tải đúng artifact đã render.

**Nghiệm thu nhóm:** Tùy chỉnh đầy đủ, old revision reproducibility, tiếng Việt/bảng dài, concurrent edit và render retry pass.

#### P10 — Trend, baseline và sự kiện bảo trì

**Module:** MOD-08. **Mục tiêu người dùng:** Theo dõi phép đo tương thích theo thời gian và drill-down đúng nguồn.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P10-01 | Trend theo máy, metric và chu kỳ với bộ lọc nghiệp vụ. |
| FR-P10-02 | Baseline, tolerance/action và mốc bảo trì/version protocol. |
| FR-P10-03 | So sánh nhiều máy khi metric/unit/context tương thích. |
| FR-P10-04 | Drill-down nguồn, xem outlier và export đúng dữ liệu đang chọn. |

**Thông tin tối thiểu:** Machine/metric/time range/timezone; unit/energy/detector/phantom/protocol/QA cycle; baseline source/effective time; tolerance/action; maintenance events; raw/aggregate series.

**Luồng chính:** Chọn machine, metric và khoảng thời gian. → Chọn filter và nhóm tương thích. → Hiển thị điểm raw, baseline/limits và maintenance markers. → Chọn điểm để mở case/run/report nguồn. → Export cùng bộ lọc, timezone và phương pháp aggregate.

**Nghiệm thu nhóm:** Không trộn máy/unit; baseline/outlier/timezone/filter/export/drill-down và rebuild pass.

#### P11 — QA Protocol Library và rule version

**Module:** MOD-09. **Mục tiêu người dùng:** Tạo và dùng protocol nội bộ có version mà không đổi ngược kết quả cũ.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P11-01 | Library tìm theo QA type/machine/cycle/từ khóa. |
| FR-P11-02 | Tạo/clone protocol nội bộ và chỉnh rule/limits/baseline. |
| FR-P11-03 | Version comparison và nguồn tham khảo độc lập nội dung nội bộ. |
| FR-P11-04 | Áp dụng explicit version cho run mới, giữ version đã dùng trước. |

**Thông tin tối thiểu:** Protocol code/title/type/cycle/applicability; version/changelog; rule key/type/unit/baseline/limits/required; reference citation/source type; archive flag.

**Luồng chính:** Tìm protocol hoặc tạo mới/clone tham khảo. → Sửa rule và applicability; xem ví dụ rule trên sample. → Lưu version nội bộ với nguồn và ghi chú. → Chọn version cho Machine QA/Gamma mới. → So sánh version và mở report cũ để xác nhận snapshot.

**Nghiệm thu nhóm:** Create/clone/version/use/archive và report-old-version tests pass; R1 còn gap phải ghi riêng.

#### P12 — Biological Hub và calculation history độc lập

**Module:** MOD-10. **Mục tiêu người dùng:** Có không gian tính toán riêng với scenario/history/report không cần case QA.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P12-01 | Hub điều hướng BED/EQD2, comparison, tái xạ, bù fraction và library. |
| FR-P12-02 | Scenario/history tìm theo tên, công cụ, mô và thời gian. |
| FR-P12-03 | Clone scenario để thử giả định khác mà giữ kết quả cũ. |
| FR-P12-04 | Report độc lập và nguồn/assumption luôn tra lại được. |

**Thông tin tối thiểu:** Scenario name/type/tissue/context/source/assumptions; scenario revision; calculation model/version/input/result; search/history/bookmark.

**Luồng chính:** Vào tab Biological Toolkit. → Chọn công cụ hoặc mở scenario cũ. → Nhập dữ liệu thủ công hoặc dataset riêng do user chọn. → Lưu scenario và calculation revision. → Mở lại, clone hoặc export calculation report độc lập.

**Nghiệm thu nhóm:** Không automatic QA linkage; scenario save/reopen/clone/history/export và scoped errors pass.

#### P13 — BED, EQD2 và đồ thị theo tổng liều

**Module:** MOD-11. **Mục tiêu người dùng:** Tính LQ minh bạch, kiểm tính nhất quán và export đồ thị/data từ cùng snapshot.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P13-01 | Tính BED/EQD2 từ D/n/d nhất quán, giải thích phép tính. |
| FR-P13-02 | Chọn mô/alpha-beta hoặc user override có provenance. |
| FR-P13-03 | Đồ thị theo D, nhiều alpha-beta, marker và bảng số liệu. |
| FR-P13-04 | Lưu/clone/reopen/export kết quả và graph độc lập. |

**Thông tin tối thiểu:** D [Gy], n nguyên dương, d [Gy/fraction], alpha/beta [Gy], tissue/source/user override; input pair; graph Dmin/Dmax/step, fixed-n hoặc fixed-d, point limit.

**Luồng chính:** Chọn hai input độc lập D/n/d và alpha/beta có nguồn/override. → Kiểm consistency và hiển thị công thức/input đã chuẩn hóa. → Tính BED/EQD2, hiển thị đủ precision và unit. → Chọn curve mode/range/alpha-beta list và xem table/marker. → Lưu calculation/graph snapshot và export.

**Nghiệm thu nhóm:** Known answers/invalid/curve equality/history/export pass; limits/model assumptions có nguồn hoặc user-defined.

#### P14 — So sánh phác đồ xạ trị

**Module:** MOD-12. **Mục tiêu người dùng:** So sánh các phương án fractionation một cách nhất quán về mô, model và context.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P14-01 | So sánh hai hoặc nhiều phương án điều trị, mỗi phương án giữ input riêng. |
| FR-P14-02 | Chọn baseline và xem chênh lệch tuyệt đối/phần trăm. |
| FR-P14-03 | Hiển thị khác biệt context/model/alpha-beta để tránh so sánh sai nghĩa. |
| FR-P14-04 | Lưu comparison, clone và export bảng/đồ thị. |

**Thông tin tối thiểu:** 2–10 phương án ban đầu; name, D/n/d, tissue/alpha-beta/source/model; baseline option; disease/context/technique/time; absolute/% deltas.

**Luồng chính:** Tạo hai phương án hoặc clone từ library/calculation. → Chọn mô/model và phương án baseline. → Validate từng phương án và compatibility giữa các phương án. → Tính bảng BED/EQD2, delta và chart. → Lưu comparison snapshot; clone thêm phương án và export.

**Nghiệm thu nhóm:** Known delta, zero baseline, mismatched context và baseline reorder/delete tests pass.

#### P15 — Re-irradiation, recovery và bù fraction

**Module:** MOD-13. **Mục tiêu người dùng:** Tính scenario nhiều course và các lịch thay thế với giả định rõ ràng.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P15-01 | Nhiều course theo thời gian, BED/EQD2 từng mô và tổng scalar. |
| FR-P15-02 | So sánh no-recovery/recovery với từng giả định, source và sensitivity. |
| FR-P15-03 | Bù fraction phân biệt kế hoạch ban đầu, đã thực hiện và các phần còn lại do user nhập. |
| FR-P15-04 | Scenario clone/history/export; không tự chọn prescription và không coi scalar là cộng liều theo không gian. |

**Thông tin tối thiểu:** Course IDs/date ranges/D/n/d hoặc fraction list; tissue dose metric/unit/alpha-beta; recovery per prior course/evaluation time/source; no-recovery comparator; planned/delivered/remaining fractions; interruption duration; optional time model.

**Luồng chính:** Chọn Re-irradiation hoặc Fraction Compensation trong toolkit. → Nhập các course/đã thực hiện và phương án dự kiến cho đúng mô. → Chọn no-recovery hoặc recovery explicit; xác nhận thời gian nếu model cần. → Tính từng course và cumulative scalar/alternative schedule. → So sánh scenario, sensitivity và export assumptions/result; spatial chỉ khi contract dữ liệu đủ.

**Nghiệm thu nhóm:** No-recovery/recovery, nonuniform fractions, missing time/context, compensation schedule và independent export pass; spatial không giả lập.

#### P16 — Dose limits, phác đồ điều trị và Knowledge Library

**Module:** MOD-14. **Mục tiêu người dùng:** Tra cứu và tái sử dụng nội dung có nguồn, context và version trong công cụ tính toán.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P16-01 | Bảng giới hạn liều theo bệnh lý/fractionation/OAR/metric và nguồn. |
| FR-P16-02 | Protocol điều trị, phác đồ, hướng dẫn contour/planning ở mức kiến thức. |
| FR-P16-03 | Knowledge/formula/alpha-beta library với search, tag và phiên bản. |
| FR-P16-04 | Chọn áp dụng vào calculator explicit; giữ source/override và lịch sử. |

**Thông tin tối thiểu:** Disease/subtype/anatomy/intent/technique/fractions; tissue/OAR; metric Dmax/Dmean/Dxcc/Vx/operator/limit/unit; source type/citation/DOI/URL/version/date/evidence/applicability; content/alpha-beta/model.

**Luồng chính:** Lọc bệnh lý, kỹ thuật, fractions, mô và metric. → Mở entry để xem nguồn và phạm vi áp dụng. → Tạo nội dung nội bộ hoặc clone, chỉnh và lưu version. → User chọn dùng entry vào calculator, review values/source. → Cập nhật library hoặc archive, mở lại calculation cũ giữ source version.

**Nghiệm thu nhóm:** Filter/context/source/version/import/override pass; không seed bảng giới hạn lâm sàng không nguồn.

#### P17 — Visual Dose, DVH và structure review

**Module:** MOD-15. **Mục tiêu người dùng:** Xem dose trên geometry đúng và tính DVH/metric có volume, unit, coverage.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P17-01 | Dose plane/grid không bắt CT; anatomy overlay cần CT tương thích. |
| FR-P17-02 | DVH theo structure với actual/limit/margin và protocol đã chọn. |
| FR-P17-03 | Mapping structure thủ công theo ROI ID, kiểm coverage và xem contour. |
| FR-P17-04 | Report/plot export, history và dataset riêng trong Biological khi user chọn. |

**Thông tin tối thiểu:** RTDOSE/RTSTRUCT/CT refs; Frame/series/contour UIDs; patient LPS geometry; ROI ID/name mapping; rasterization/resampling method; dose bins/volume weights/coverage; Dmean/Dx/Vx.

**Luồng chính:** Chọn dataset: dose-only hoặc dose+CT; DVH cần dose+structures. → Preflight frame/geometry/reference/coverage. → Chọn ROI, manual mapping và rasterization/resampling. → Worker tạo DVH, metric, coverage/uncertainty và overlay. → Review slices/curve/metric, lưu snapshot và report.

**Nghiệm thu nhóm:** Geometry, uniform/box/sphere/holes/coverage, Dx/Vx units và staging DVH E2E pass. P17 bắt buộc cho mục tiêu toàn dự án, tùy chọn chỉ cho R1 sớm.

#### P18 — Kiểm thử tích hợp, độ bền và pilot

**Module:** MOD-16. **Mục tiêu người dùng:** Chứng minh các module phối hợp đúng, phục hồi được và có evidence cho release candidate.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P18-01 | Workflow liên module được kiểm thử có traceability. |
| FR-P18-02 | Hệ thống phục hồi sau mất mạng, process restart và dependency failure. |
| FR-P18-03 | Đo hiệu năng/tải/cost theo cấu hình thực tế. |
| FR-P18-04 | Pilot findings thành regression cases và bản sửa có version. |

**Thông tin tối thiểu:** Release manifest; workload/fixture versions; test IDs; failure injection; expected/observed; latency/memory/job counts; restore time/checksum; pilot issue severity.

**Luồng chính:** Khóa release candidate và data fixtures. → Chạy E2E các hành trình R1/R2/R3. → Thử offline/restart/concurrency/backup-restore trong staging. → Đo hiệu năng và ghi chi phí với workload cụ thể. → Pilot dữ liệu được phép; biến lỗi thành regression; chốt candidate đạt gate.

**Nghiệm thu nhóm:** Toàn bộ MUST tests pass, không còn SEV0/1; restore/rollback/performance evidence; remaining limitations không vi phạm exit scope.

#### P19 — Production website và truy cập từ xa

**Module:** MOD-16. **Mục tiêu người dùng:** Phát hành đúng release qua HTTPS và xác nhận hành trình người dùng ở production.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P19-01 | Website production HTTPS truy cập từ mạng ngoài. |
| FR-P19-02 | Đăng nhập, upload, job, report/download và toolkit hoạt động từ xa. |
| FR-P19-03 | Release có version đầy đủ và xử lý lỗi rõ cho người dùng. |
| FR-P19-04 | Rollback/maintenance giữ dữ liệu và phục hồi dịch vụ. |

**Thông tin tối thiểu:** Approved RC SHA/image digests; API/web/worker/renderer/schema/engine versions; env service IDs; domain/TLS/CORS/Auth URLs; backups; rollback image/schema compatibility.

**Luồng chính:** Đối chiếu release manifest và production configuration. → Backup, kiểm restore point rồi chạy migration compatible. → Deploy các service đúng candidate và public build config production. → Kiểm health/schema/queue/Auth rồi remote E2E có synthetic data. → Ghi release/monitoring; rollback nếu gate lỗi theo điều kiện đã định.

**Nghiệm thu nhóm:** HTTPS + remote workflows + Auth + private dependencies + versions + backup/rollback/alerts đều kiểm chứng.

#### P20 — Gói vận hành ban đầu và cải tiến liên tục

**Module:** MOD-16. **Mục tiêu người dùng:** Bàn giao cách theo dõi, khôi phục và cập nhật hệ thống sau release.

| Requirement | Tính năng phải bàn giao |
| :--- | :--- |
| FR-P20-01 | Theo dõi uptime, lỗi, backlog, storage và chi phí. |
| FR-P20-02 | Backup/restore và quy trình ứng phó incident có người phụ trách. |
| FR-P20-03 | Hướng dẫn sử dụng/troubleshooting theo lỗi người dùng gặp. |
| FR-P20-04 | Cải tiến có regression, version và lịch sử release. |

**Thông tin tối thiểu:** Owner/contact; monitoring thresholds; backup schedule/retention/restore drill; cost budget; incident severity; release notes; engine version; maintenance calendar.

**Luồng chính:** Thiết lập monitor và backup schedule đã chọn. → Thử một alert và một restore để xác nhận runbook dùng được. → Bàn giao hướng dẫn thường ngày và xử lý sự cố. → Triage bug/dataset mới thành issue + regression. → Release maintenance qua staging với manifest và ghi kết quả.

**Nghiệm thu nhóm:** Gói vận hành ban đầu có config thực, alert test, backup+restore evidence và người phụ trách; vận hành liên tục không có trạng thái hoàn tất vĩnh viễn.

### 21.4. Phạm vi biến thể bắt buộc

- Mọi chức năng lưu dữ liệu: dữ liệu hợp lệ, thiếu required, sai type/format, biên min/max, dữ liệu trùng, stale revision, mất mạng trước/sau commit, record archived và truy cập khác organization.
- Mọi phép tính: known answer; input không hợp lệ; đơn vị; precision; zero/negative/nonfinite; thay config/model; mẫu số 0; không có điểm/volume hợp lệ; lưu/mở lại; so sánh và export.
- Mọi job: accepted/queued/running/completed/failed, worker restart, duplicate dispatch, deadline, retry, nguồn thay đổi, mất dependency và kết quả hiển thị sau reconnect.
- Mọi library: search/filter/no match, create/clone/version, nguồn thiếu/hỏng, giá trị nội bộ/override, áp dụng explicit và giữ source version cũ.
- Mọi trang: loading, empty, populated, error, offline, validation, success và khả năng bàn phím; warning/long-running chỉ khi áp dụng.

Không thể liệt kê hữu hạn mọi tổ hợp lỗi có thể xuất hiện. Baseline này bao phủ các nhóm lỗi đã nhận diện; mỗi bug mới phải được gắn requirement, testcase và regression trước khi đóng. Không gọi danh sách là bằng chứng hệ thống không còn lỗi.

### 21.5. Ma trận nghiệp vụ chi tiết theo phase

Mục này biến catalogue FR thành một hành trình có thể quan sát được từ góc nhìn bác sĩ, kỹ sư và thành viên chuyên môn. “Chạy đúng” nghĩa là dữ liệu hợp lệ đi hết luồng và kết quả được lưu đúng nguồn. “Lỗi” được chia thành lỗi dữ liệu, lỗi trạng thái, lỗi dependency, lỗi lưu trữ, lỗi đồng thời hoặc lỗi phạm vi tổ chức. Với mọi lỗi, giao diện phải giữ dữ liệu người dùng còn hợp lệ, chỉ rõ bước cần sửa và cho phép retry an toàn; không được đổi số, đơn vị, source hoặc kết quả một cách âm thầm. Mã testcase chi tiết nằm trong `plan.md` và mã contract nằm trong `specification.md`.

| Phase | Năng lực người dùng phải nhận được | Workflow chạy đúng | Lỗi/ngõ rẽ phải hỗ trợ | Kết quả và bất biến nghiệp vụ |
| :--- | :--- | :--- | :--- | :--- |
| P0 | Hiểu phạm vi, module, requirement và trạng thái evidence của dự án | Đọc baseline → tra FR/MOD/phase → đối chiếu source/design/evidence → ghi gap → chọn công việc tiếp theo | Tài liệu mâu thuẫn, screen đã xóa, evidence thiếu, sai project/environment | Không sửa lịch sử để làm đẹp trạng thái; mọi FR có mã, owner, dependency, acceptance và đường truy vết |
| P1 | Có cách khởi động và kiểm thử nhất quán trên máy phát triển | Chuẩn bị runtime → khởi động database/queue/storage → migrate/seed dữ liệu synthetic → chạy API/web → chạy test/build | Thiếu dependency, lockfile lệch, port bận, migration fail, thiếu env, build hoặc OpenAPI lệch | Chỉ gọi hệ thống ready khi process, database schema và contract đều đạt; secret không xuất hiện trong log |
| P2 | Có website staging truy cập từ xa với hạ tầng đúng môi trường | Chọn Railway environment → deploy API/worker → chạy migration → kiểm health và schema → xác minh Supabase Auth → lưu release manifest | Source/root sai, driver database sai, process không listen, DB thiếu schema, JWT/JWKS lỗi, config drift | Railway PostgreSQL là nơi lưu dữ liệu nghiệp vụ; Supabase là identity; database/queue/worker không mở public; staging không dùng DB production |
| P3 | Đăng nhập và vào đúng workspace mà không mất deep-link | Mở URL → đăng nhập hoặc recovery → bootstrap identity → tạo organization đầu tiên nếu chưa có membership → vào dashboard → logout/expiry | Sai credential, recovery link hết hạn, session/JWKS lỗi, chưa có membership, Vite Auth config thiếu, API/CORS/offline | Không tự gắn user vào organization khác; cache cũ phải bị dọn khi đổi identity; dashboard chỉ hiển thị dữ liệu server đã scope |
| P4 | Quản lý organization, site, machine và mời thành viên; mọi thành viên cùng tổ chức dùng nghiệp vụ ngang nhau | Tạo site/machine → cập nhật thông tin → xem history → mời identity → archive/restore → kiểm tra liên kết QA | Code machine trùng, parent không còn active, sửa đồng thời, invitation sai/hết hạn, xóa thành viên cuối, không biết kết quả mutation | Stable ID không đổi khi rename; không partial update; không thêm phân cấp bác sĩ/kỹ sư hoặc action approval; retry mutation phải idempotent |
| P5 | Quản lý QA Archive giống cây thư mục của máy tính | Tạo folder lồng nhau → tạo case theo machine/cycle → tìm/lọc/sắp xếp/phân trang → move/rename → archive/restore | Move vào chính nó hoặc con cháu, tên trùng cùng parent, parent archive, machine/site sai, trang ngoài phạm vi, restore đụng tên | Cây cũ và case cũ vẫn nguyên khi mutation fail; move subtree atomic; filter/deep-link không làm mất organization scope |
| P6 | Đưa file vào case, biết file có thể dùng cho workflow nào và tải lại nguyên bản | Chọn case/type/role → upload một hoặc nhiều file → progress/checksum → lưu object và metadata → tạo Input Manifest → validate → download | File thiếu/rỗng/quá lớn, upload gián đoạn, object store hoặc DB fail, duplicate, declared type sai nội dung, DICOM thiếu UID/geometry/unit, link hết hạn | Bytes bất biến và checksum round-trip; duplicate phải phân biệt vật lý và logical role; file invalid không được đi vào engine; object mồ côi phải reconcile |
| P7 | Thực hiện Machine QA theo protocol version và xem kết quả giải thích được | Chọn cycle/protocol → nhập metric hoặc N/A có lý do → lưu draft → validate → evaluate snapshot → xem actual/limit/margin/status → rerun/compare | Metric thiếu, unit sai, NaN, baseline 0, autosave xung đột, double submit, protocol archive | Result chỉ được tạo từ snapshot hợp lệ; PASS/WARNING/FAIL là kết quả rule, không phải quyền; rerun không sửa result cũ và trend không nhân đôi |
| P8 | Chạy PSQA Gamma 2D/3D từ input hợp lệ và theo dõi job | Chọn RTDOSE/reference/comparison → preflight profile, frame, unit, config và resource → enqueue → worker lease/heartbeat → tính/lưu → ack → xem map/histogram/profile → retry/rerun/compare | Thiếu RTDOSE hoặc comparison, geometry/frame/unit không tương thích, config unsupported, không có evaluated points, local reference 0, Redis lỗi, worker chết/OOM/lease hết, DICOM/codec unsupported, quá resource, source đổi | PSQA phải có RTDOSE; JSON-only phải mang nhãn ENGINE_TEST; FULL_ROI không bỏ no-candidate khỏi mẫu số; OVERLAP_ONLY phải nêu coverage; max gamma phải nêu censoring; worker cũ không ghi đè |
| P9 | Tùy chỉnh toàn bộ report theo cách trình bày của người dùng | Chọn source hoặc tạo report Biological → chọn template → thêm/xóa/ẩn/đổi tên/sắp xếp block → preview → lưu revision snapshot → export → mở history/download | Revision conflict, source thiếu, nội dung nguy hiểm, renderer fail, format không hỗ trợ, storage/link fail, idempotency key xung đột | User được toàn quyền bố cục, kể cả ẩn warning/provenance khỏi layout; hệ thống vẫn giữ source lineage ngoài layout; revision cũ và file export cũ không đổi |
| P10 | Theo dõi trend theo machine, metric và bối cảnh tương thích | Chọn machine/metric/time → lọc compatibility → xem raw hoặc aggregate → xem baseline/limit/maintenance marker → drill-down source → export | Unit/context không tương thích, ngày sai, không có data, baseline 0, projection duplicate, source archived | Không nối các series khác nghĩa; aggregate giữ count/extrema và nhãn; marker không sửa QA result; điểm cũ luôn mở đúng case/run/report |
| P11 | Xây dựng QA protocol nội bộ có version và nguồn | Tìm hoặc clone protocol → sửa rule/applicability → kiểm sample → lưu version → dùng cho run mới → compare | Rule min/max sai, version/key trùng, thiếu reference, chọn version archive, engine không hỗ trợ rule | Version đã dùng được giữ immutable; clone deep-copy child; run cũ giữ rule/limit cũ; protocol tham khảo không tự thành protocol áp dụng |
| P12 | Có một Biological Hub riêng, không phụ thuộc QA case hoặc patient record | Vào tab Biological → chọn tool → nhập scenario/context → lưu revision → tính hoặc chờ module → xem history → clone/export | Scenario khác organization, tự mang QA context sai, sửa đồng thời, model version không còn, route/module chưa sẵn sàng | Scenario và calculation là namespace riêng; không bắt buộc QACase; mọi input/model/assumption được lưu cùng revision; module chưa có không được hiện nút giả |
| P13 | Tính BED/EQD2 và xem đồ thị theo tổng liều D | Nhập D/n/d và alpha-beta → kiểm nhất quán → tính BED/EQD2 → chọn range/step → vẽ curve/table/marker → lưu/export | n không nguyên hoặc không dương, alpha-beta sai, D khác n*d, số non-finite, curve range/step sai, thiếu nguồn alpha-beta, persistence fail | Không tự thay n, d, D hoặc alpha-beta; precision/unit nhất quán; đường cong là dataset có input snapshot, không chỉ là ảnh; kết quả cũ không đổi khi sửa draft |
| P14 | So sánh 2–10 phương án điều trị trên cùng bối cảnh | Tạo options → nhập fractionation/model/tissue → chọn baseline → calculate absolute và percent delta → chart/table → reorder/clone/export | Thiếu options, baseline 0, option invalid, khác context, xóa baseline, vượt giới hạn | Delta % không xác định phải là null và có lý do; không dùng 0 thay missing; toàn bộ options dùng cùng revision/context; không truncate im lặng |
| P15 | Phân tích re-irradiation và bù fraction chi tiết trong tab scenario riêng | Nhập course/date/dose/fraction list → chọn tissue/alpha-beta → chọn recovery/no-recovery và thời điểm đánh giá → xem cumulative scalar/sensitivity → nhập interruption → xem các phương án bù fraction → export | Thiếu interval, recovery ngoài phạm vi/không nguồn, khác tissue/alpha-beta, lịch delivered/planned sai, spatial registration thiếu, thiếu OAR dose, interruption overlap, số fraction không nguyên | Hiển thị assumptions, source và độ nhạy; tách scalar khỏi spatial accumulation; không giả lập voxel dose khi thiếu registration; bù fraction là estimate để người dùng đánh giá, không tự sửa treatment record hoặc phát hành prescription |
| P16 | Tra cứu và quản lý dose limits, treatment protocol, phác đồ và knowledge library | Lọc theo bệnh lý/mô/OAR/metric → xem source/applicability → tạo/clone/version → import hoặc gắn citation → chọn explicit trong scenario | Thiếu nguồn, unit sai, link hỏng, row import lỗi/duplicate, không phù hợp bệnh cảnh, content/script nguy hiểm | Published version immutable; citation và applicability đi cùng calculation snapshot; entry không nguồn phải gắn user-defined/internal; không tự sinh PASS/FAIL lâm sàng |
| P17 | Xem dose, profile, structure và DVH khi dữ liệu hình học đủ | Chọn RTDOSE/RTSTRUCT/image → validate Frame/ROI/grid → overlay → tính DVH/profile → xem bảng/đồ thị → export | Thiếu RTSTRUCT hoặc CT, frame mismatch, ROI rỗng, contour ngoài grid, contour hỏng, codec/oblique unsupported | Dose-only fallback có nhãn; không vẽ overlay sai frame; coverage phải hiển thị; ROI thiếu dose không được gán 0 hoặc kết luận full-ROI |
| P18 | Chứng minh toàn bộ candidate chạy bền trên dataset đại diện trước pilot | Chạy clean release → integration matrix → golden/error → concurrency/failure injection → load → backup/restore → pilot feedback → regression | Golden lệch, restore thiếu object, duplicate replay, vượt budget, dataset không supported, evidence sai SHA | Giữ candidate và dữ liệu lỗi để điều tra; issue gắn input/hash/expected/observed; không sửa expected để ép PASS; không còn SEV0/SEV1 trước promote |
| P19 | Truy cập website production từ mạng ngoài với phiên bản đồng bộ | Chọn release candidate → backup point → promote API/web/worker/schema → cấu hình domain/TLS/CORS/Auth → remote E2E → rollback rehearsal | DNS/TLS chưa ready, public build config sai, migration fail, web/API lệch version, health 200 nhưng workflow fail, resource vượt budget | Public URL chỉ là một phần exit; phải có service SHA/schema/engine manifest, Auth, workflow, private dependencies, backup và rollback evidence; giữ last-good khi gate fail |
| P20 | Vận hành sau release bằng monitor, backup, runbook và vòng cải tiến | Đặt threshold/owner → test alert → chạy backup/restore drill → bàn giao guide → triage incident/dataset → regression → maintenance release | Backup fail/quá retention, alert không nhận, storage/capacity thấp, engine đổi kết quả, incident lặp lại | Không xóa last-good backup; maintenance không rewrite history; thay engine tạo version/diff; mọi incident lặp lại phải có root cause và regression, không chỉ restart |

### 21.6. Quy tắc phản hồi lỗi dùng chung cho mọi phase

Để workflow nhất quán, mọi chức năng phải phân biệt sáu loại trạng thái sau:

1. **Input invalid:** người dùng có thể sửa dữ liệu; hệ thống giữ các trường hợp lệ và hiển thị lỗi tại trường gây ra lỗi.
2. **State conflict:** dữ liệu đã thay đổi hoặc đã archive; hệ thống tải bản hiện tại, giữ draft và cho copy/retry, không ghi đè im lặng.
3. **Dependency unavailable:** database, queue, object storage, Auth hoặc renderer không sẵn sàng; hệ thống lưu trạng thái chưa hoàn tất nếu đã nhận request, retry có giới hạn và hiển thị mã tương quan.
4. **Persistence uncertain:** client mất kết nối sau khi gửi; giao diện phải cho kiểm tra operation/idempotency trước khi gửi lại, không tạo record hoặc job trùng.
5. **Scope/context invalid:** object, machine, source, tissue, unit hoặc Frame of Reference không thuộc context đang chọn; hệ thống từ chối hoặc tách series, không đoán và không lộ dữ liệu context khác.
6. **Valid calculation with warning:** phép tính hoàn tất nhưng có coverage, censoring, font, assumption hoặc applicability warning; kết quả vẫn được đánh dấu theo đúng trạng thái cảnh báo, khác với lỗi không tính được.

Mỗi màn hình phải có trạng thái loading, empty, populated, warning, error, retry và offline phù hợp. Không dùng màu sắc đơn độc để truyền đạt PASS/FAIL, không để spinner vô hạn, không hiển thị stack trace/secret và không biến HTTP 200 thành kết quả nghiệp vụ. Danh sách trong mục 21.5 là baseline kiểm thử hiện tại; khi phát hiện lỗi mới, bổ sung FR/testcase/regression và cập nhật cả ba tài liệu nghiệp vụ, specification và plan.
