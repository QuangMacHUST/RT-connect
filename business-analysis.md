# TÀI LIỆU PHÂN TÍCH NGHIỆP VỤ

## Dự án RT-CONNECT

- **Tên sản phẩm:** RT-CONNECT
- **Phạm vi:** Website quản lý QA xạ trị, thư viện QA protocol, Biological Toolkit và thư viện kiến thức điều trị
- **Đối tượng sử dụng:** Bác sĩ xạ trị, kỹ sư vật lý xạ trị và các thành viên chuyên môn trong bệnh viện/tổ chức
- **Phiên bản tài liệu:** 0.6 — bổ sung luồng khởi tạo organization cho identity đã xác thực nhưng chưa có membership
- **Trạng thái sản phẩm:** Chưa phải hệ thống được thẩm định để sử dụng lâm sàng

Tài liệu này mô tả nghiệp vụ, nhu cầu người dùng, quy trình, quy tắc và tiêu chí nghiệm thu. Các quyết định về framework, database, server, cấu trúc source code và cách triển khai được mô tả trong `technical-specification.md`; trình tự thực hiện và tiêu chí đóng từng module được mô tả trong `plan.md`.

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
- Database, object storage, worker, queue và DICOM gateway là thành phần hạ tầng phía sau, không phải các dịch vụ public độc lập.
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
- Database, object storage, queue, worker và DICOM gateway không bị mở thành các endpoint public độc lập.

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
- Chỉ public frontend/API; PostgreSQL, object storage, queue, worker và DICOM gateway không public trực tiếp.

---

## 20. Kết luận nghiệp vụ

RT-CONNECT là hệ thống quản lý và phân tích QA xạ trị kết hợp một Biological Toolkit độc lập. Các thành viên chuyên môn trong cùng organization được sử dụng nghiệp vụ ngang nhau; tài liệu không xây dựng phân cấp bác sĩ–kỹ sư hoặc phân quyền theo hành động.

Clinical MVP tập trung vào Machine QA, PSQA Gamma, report, trend, input validation và provenance. Biological Toolkit được tổ chức thành tab riêng, phục vụ tính toán BED/EQD2, đồ thị, so sánh phác đồ, giới hạn liều, protocol điều trị, knowledge library và re-irradiation scenario mà không gắn mặc định với QA case hoặc ca bệnh.

`technical-specification.md` và `plan.md` phải tiếp tục được xây dựng từ các yêu cầu, quy tắc và tiêu chí nghiệm thu trong tài liệu này. Google Stitch cung cấp thiết kế trực quan; Railway và Supabase cung cấp hạ tầng đã chọn; không nguồn nào trong số đó được tự thay thế hoặc làm mất requirement nghiệp vụ.
