# RT-CONNECT — Phân tích nghiệp vụ

**Phiên bản tài liệu:** 1.3
**Ngày cập nhật:** 2026-09-13
**Mốc yêu cầu:** UX1.3 — thư viện nội bộ/cộng đồng, giao diện tiếng Việt và triển khai tuần tự.
**Tài liệu triển khai:** technical-specification.md v2.3; plan.md v5.3; [danh mục pylinac](docs/pylinac-qa-catalog.md) v1.1.

## 1. Mục đích và hiệu lực

RT-CONNECT là ứng dụng web phục vụ bác sĩ và kỹ sư xạ trị: thực hiện và lưu kết quả QA, lập báo cáo, theo dõi thay đổi, tính toán sinh học đơn giản và tra cứu kiến thức có nguồn. Người dùng không cần biết lập trình, định dạng dữ liệu nội bộ hoặc cấu trúc cơ sở dữ liệu.

Bản này thay thế toàn bộ cách tổ chức sản phẩm ở bản 0.27. Bản trước được giữ tại [lịch sử tài liệu](docs/history/pre-ux-20260912/business-analysis.md). Lịch sử kiểm thử là bằng chứng cho phiên bản được thử, không tự động chứng minh các yêu cầu mới đã hoàn thành.

Thứ tự giải quyết mâu thuẫn: yêu cầu mới của người dùng → bản nghiệp vụ này → đặc tả kỹ thuật 2.3 → kế hoạch 5.3 → danh mục pylinac 1.1. Đây là yêu cầu sản phẩm; trạng thái phần mềm đã làm được đến đâu ghi riêng trong sổ tiến độ.

### 1.1. Những quyết định đã chốt

- Giữ chức năng đăng nhập, đơn vị, cơ sở, thiết bị và thành viên hiện có; cải tiến cách trình bày.
- Thành viên trong cùng đơn vị ngang quyền; không thêm vai trò bác sĩ/kỹ sư, người duyệt, quy trình xin duyệt hay phê duyệt báo cáo bắt buộc.
- Giữ dữ liệu riêng giữa các đơn vị. Việc xác định một người thuộc đơn vị nào không phải phân cấp chức danh.
- Thư viện có hai phạm vi “Nội bộ đơn vị” và “Cộng đồng”; mỗi phạm vi đều chứa hai nhóm nội dung “Kiểm tra chất lượng máy” và “Phác đồ điều trị”. Bài và tệp tải lên mặc định nội bộ; chỉ phiên bản được người dùng chủ động chia sẻ mới xuất hiện với tài khoản đơn vị khác.
- “Cộng đồng” là toàn bộ tài khoản RT-CONNECT đã đăng nhập, kể cả tài khoản chưa tham gia đơn vị. Không yêu cầu người dùng trở thành thành viên bệnh viện khác để đọc phần được chia sẻ.
- Toàn bộ nhãn do ứng dụng tạo dùng tiếng Việt; thực hiện xong và nghiệm thu từng giai đoạn trước khi bắt đầu giai đoạn kế tiếp.
- QA là luồng chọn bài → nhập số liệu hoặc tệp phù hợp → phân tích → đánh giá → lưu → xem lại hoặc xuất PDF.
- Báo cáo, lịch sử và xu hướng thuộc QA máy; không phải ba sản phẩm người dùng phải chuyển qua lại.
- Thư viện hướng dẫn QA khác với phần cài đặt thông số thực thi một bài QA.
- Công cụ sinh học độc lập với hồ sơ bệnh nhân và bài QA; mở công cụ là tính được, không bắt tạo hồ sơ hay kịch bản trước.
- Người dùng toàn quyền chọn nội dung, dòng kết quả, bố cục và hình minh họa trong PDF.
- Không thêm phạm vi pháp luật/FDI hoặc một dự án commissioning bắt buộc vào yêu cầu này. Có kiểm thử tính toán, đối chiếu dữ liệu và phản hồi thực tế; không suy diễn “đạt kiểm thử” thành đảm bảo cho mọi quyết định điều trị.
- Pylinac là engine chính thức cho toàn bộ bài QA và phép tính mà phiên bản đã khóa cung cấp; không còn là lựa chọn ưu tiên hoặc engine tùy chọn. RT-CONNECT sở hữu giao diện, kiểm tra đầu vào, tham số, thao tác tay trên ảnh, lịch sử, đánh giá, xu hướng và báo cáo.

### 1.2. Nguyên tắc sử dụng pylinac

- Phạm vi bắt buộc bao gồm đủ 16 họ mô-đun chính, toàn bộ biến thể công khai và các bài QA công khai trong `contrib/One-Offs` có trong phiên bản pylinac runtime đã khóa; chi tiết ở [danh mục QA pylinac](docs/pylinac-qa-catalog.md). Không được đóng P7 chỉ bằng Picket Fence, Winston–Lutz và Starshot.
- Danh mục phải ghi rõ bài nào “Phân tích bằng pylinac” và bài nào chỉ “Nhập số liệu”. Một capability pylinac chưa được ánh xạ giao diện hoặc chưa có adapter không bị loại khỏi phạm vi; nó phải được theo dõi là chưa triển khai và P7 chưa hoàn thành.
- Người dùng không nhìn thấy class, hàm, JSON kết quả hoặc traceback của pylinac. Họ vẫn thao tác bằng tên bài, trường nhập, hình ảnh và kết luận tiếng Việt.
- Pylinac chịu trách nhiệm tính toán. RT-CONNECT không tự viết lại thuật toán tương đương cho capability pylinac đã có; chỉ chuyển input/đơn vị/hình học theo contract, trình bày kết quả và lưu provenance. Đánh giá cuối “Đạt/Cảnh báo/Không đạt” vẫn do người dùng chọn theo cài đặt của đơn vị.
- Bộ xuất PDF của pylinac không thay thế yêu cầu báo cáo RT-CONNECT: PDF của RT-CONNECT phải tùy chỉnh được từng dòng, cột và lớp hình.
- Các bài nhập số liệu/checklist không có engine tương ứng, phép tính sinh học, quản lý lịch sử và nội dung thư viện vẫn dùng thành phần phù hợp của RT-CONNECT; không gắn nhãn pylinac cho các phần này.
- Phiên bản/hash pylinac phải được khóa. Kiểm thử adapter xác nhận RT-CONNECT truyền đúng input/tham số và giữ đúng kết quả pylinac; không dùng test để thay đổi quyết định chọn engine.

### 1.3. Phạm vi đợt thiết kế lại

Ưu tiên thực hiện: giao diện gọn; khung QA nhập tay; triển khai lần lượt toàn bộ danh mục pylinac; PSQA; lịch sử có xóa/khôi phục; PDF tùy chỉnh; công cụ sinh học một trang; thư viện hai nhánh. Thứ tự triển khai không làm mô-đun xếp sau trở thành tùy chọn.

“Giống myQA” được hiểu là trải nghiệm theo danh mục bài kiểm tra, dữ liệu đầu vào phù hợp, phân tích và báo cáo. Không đồng nghĩa sao chép giao diện, hỗ trợ mọi tệp độc quyền hay tự tuyên bố tương đương toàn bộ thuật toán của một sản phẩm thương mại. Danh mục khả năng hỗ trợ phải nêu rõ từng bài và từng định dạng.

## 2. Người dùng và mô hình làm việc

Một người có thể thuộc nhiều đơn vị; chọn đơn vị bằng tên quen thuộc. Mỗi đơn vị có cơ sở, máy xạ trị và thành viên. Các thành viên đều có thể tạo/sửa bài, đánh giá kết quả, tạo PDF, quản lý nội dung tham khảo và xóa/khôi phục trong phạm vi đơn vị.

Không tạo quy trình trạng thái phê duyệt lâm sàng. Chỉ dùng trạng thái tác vụ cần thiết như “Chưa lưu”, “Đang tải”, “Đang phân tích”, “Đã lưu”, “Không thể phân tích”, “Trong thùng rác”. Trạng thái chạy khác với kết luận “Đạt / Cảnh báo / Không đạt”.

Mọi thay đổi quan trọng lưu người thực hiện và thời điểm ở bên trong hệ thống. Không bắt người dùng thao tác với nhật ký hoặc thông tin kỹ thuật để hoàn thành công việc.

## 3. Cấu trúc điều hướng mới

Thanh điều hướng chính chỉ gồm năm mục:

| Mục tiếng Việt | Nội dung | Hành động chính |
| :--- | :--- | :--- |
| Trang chủ | Bài gần đây, việc đang làm, bộ chọn máy, lối tắt | Bắt đầu bài QA, mở công cụ |
| Kiểm tra chất lượng máy | Danh mục bài kiểm tra, lịch sử, xu hướng; kiểm tra kế hoạch điều trị là nhóm bài bên trong | Thực hiện bài kiểm tra |
| Công cụ sinh học | BED/EQD2, so sánh, tái xạ, bù buổi chiếu, giới hạn liều, hệ số α/β | Tính hoặc tra cứu |
| Thư viện kiến thức | Nội bộ đơn vị và Cộng đồng; mỗi phạm vi có Kiểm tra chất lượng máy và Phác đồ điều trị | Tìm, đọc, viết bài và lưu tài liệu |
| Đơn vị và thiết bị | Đơn vị, cơ sở, máy, thành viên | Quản lý thông tin đã có |

Trợ giúp, tài khoản, đăng xuất và trạng thái dịch vụ nằm trong trình đơn tài khoản. Không hiển thị mã mô-đun, giai đoạn phát triển, thông báo kỹ thuật hoặc số phiên bản phần mềm trên trang làm việc thường ngày. Phiên bản tài liệu chuyên môn vẫn hiển thị vì giúp người đọc chọn đúng tài liệu.

“QA máy” trong các tài liệu kỹ thuật được hiển thị là “Kiểm tra chất lượng máy”. Bài PSQA được ghi “Kiểm tra kế hoạch điều trị”; tên chuẩn chuyên môn như Picket Fence, Winston–Lutz, Starshot có tên tiếng Việt giải thích và tên gốc trong phần tra cứu chuyên môn.

### 3.1. Giao diện gọn trong một màn hình

- Kiểm tra thiết kế ở 1366 × 768 và 1440 × 900, mức thu phóng 100%.
- Nội dung thường 14 px; bảng kết quả 13–14 px; tiêu đề trang 22–24 px; chữ phụ tối thiểu 12 px. Không thu toàn bộ chữ xuống mức khó đọc để đạt chỉ tiêu.
- Giảm khoảng trắng, chiều cao thẻ, khẩu hiệu và đoạn giới thiệu lặp lại. Dùng bảng gọn và vùng chi tiết thay vì nhiều thẻ lớn xếp dọc.
- Đăng nhập; phần tổng quan đơn vị; biểu mẫu QA cơ bản; phép tính BED/EQD2 cơ bản: nhãn, trường chính, kết quả chính và nút thao tác nằm trong khung màn hình chuẩn.
- Danh sách dài, tài liệu PDF, bảng nhiều dòng và ảnh phóng to được cuộn trong vùng nội dung có chủ đích. Không hứa ép tài liệu dài vào một màn hình.
- Giữ bộ lọc và nút lưu/tính/xuất dễ tiếp cận. Không có nhiều vùng cuộn lồng nhau khó điều khiển.
- Khi phóng to chữ 200% hoặc dùng màn hình nhỏ, cho phép dàn lại và cuộn trang; không cắt nút hay nội dung.
- Thao tác bàn phím, trạng thái lấy nét, nhãn đơn vị và chữ chỉ kết luận phải rõ. Không chỉ dựa vào màu đỏ/vàng/xanh.

### 3.2. Quy tắc ngôn ngữ

Đợt này chỉ cung cấp giao diện tiếng Việt. Nhãn điều hướng, biểu mẫu, lời nhắc, trạng thái, lỗi, trợ giúp, trình đọc PDF, trình soạn bài và báo cáo đều dùng tiếng Việt có dấu. Không có nút đổi ngôn ngữ chưa hoàn thiện. Tên riêng, tên bài báo và nội dung PDF gốc được giữ nguyên theo tài liệu; hệ thống không tự dịch hoặc sửa tệp nguồn. Ký hiệu chuyên môn như Gy, mm, BED, EQD2 và PDF được giữ khi cần đọc đúng số liệu.

Dùng “Đơn vị”, “Cơ sở”, “Máy xạ trị”, “Lịch sử”, “Báo cáo”, “Xu hướng”, “Tải lên”, “Đang phân tích”, “Thử lại”. Không dùng nhãn như “Thêm site”, “Import JSON”, “Report Builder”, “Job đang chạy”, “Bù fraction”.

Tên khoa học riêng như Picket Fence, Winston–Lutz, Starshot và các ký hiệu QA, DICOM, BED, EQD2, PTV, HI, CI, Gy, mm được giữ khi cần, kèm giải thích tiếng Việt ngắn. Tên đơn vị do người dùng nhập và tiêu đề nguyên bản của nguồn tham khảo không bắt buộc dịch.

### 3.3. Không yêu cầu kiến thức kỹ thuật

Không có ô nhập JSON, thao tác nhập/xuất tệp JSON, mã hồ sơ nội bộ, UUID, đường dẫn lưu trữ, mã hàng đợi hay dấu kiểm dữ liệu thô trong giao diện và PDF thường dùng. Chọn máy, bài và tài liệu bằng tên; xác nhận bằng tên bài + máy + thời gian. Mã kỹ thuật vẫn được quản lý nội bộ để phần mềm hoạt động.

Không lấy tên bệnh nhân hoặc mã bệnh nhân từ DICOM rồi tự đưa vào lịch sử/PDF. Tên bài PSQA do người dùng chủ động đặt; thông tin chuyên môn cần thiết được chọn có ý thức.

## 4. Trang chủ, đăng nhập và đơn vị

### 4.1. Trang chủ

Hiển thị tên đơn vị nhỏ gọn, máy đang chọn, nút “Thực hiện bài QA”, lối tắt “Công cụ sinh học” và “Thư viện kiến thức”. Bảng gần đây gồm tên bài, máy, thời điểm, kết luận và nút mở. Có trạng thái đang phân tích và mục cần xem lại khi thực sự có dữ liệu.

Không hiển thị số liệu giả khi chưa có bài. Không dùng thẻ trống lớn để giải thích kế hoạch phát triển. Chưa có máy thì đưa đúng lối tắt tạo máy; chưa có bài thì mời chọn một bài.

### 4.2. Đăng nhập và cơ cấu

Giữ cách xác thực và liên kết đơn vị đã hoạt động. Phân biệt rõ hết phiên, chưa vào đơn vị, mất kết nối và lỗi máy chủ; mỗi lỗi có hành động phù hợp. Không báo “không có tổ chức” khi thực tế không gọi được dịch vụ.

Trong “Đơn vị và thiết bị”, dùng các thẻ nội bộ “Đơn vị”, “Cơ sở và máy”, “Thành viên”. Không xếp tất cả biểu mẫu dài nối tiếp. Danh sách và vùng sửa cạnh nhau trên máy tính; tạo/sửa bằng khung nhỏ. Khi hai người cùng sửa, báo dữ liệu đã thay đổi và cho tải lại; không âm thầm ghi đè.

## 5. QA máy — danh mục và đầu vào

### 5.1. Ba cách thực hiện

1. **Nhập số liệu đã đo:** nhập giá trị, đơn vị, ngày đo, thiết bị đo và ghi chú; có thể ghi nguồn đo từ myQA. Không bắt tệp DICOM.
2. **Phân tích ảnh:** tải ảnh thuộc định dạng được bài hỗ trợ, kiểm tra khả năng dùng ảnh và thang đo, chạy phân tích, xem ảnh có chú thích.
3. **Phân tích liều:** chọn liều tham chiếu và dữ liệu đo/đối chiếu đúng vai trò; tính Gamma hoặc DVH tùy bài.

Một bài có nhiều cách thực hiện chỉ khi khai báo rõ. Nếu chọn “Nhập kết quả từ phần mềm khác”, hiển thị đúng là số liệu do người dùng nhập; không sinh bản đồ phân tích giả và không gọi là kết quả RT-CONNECT tự tính.

### 5.2. Danh mục khả năng cần có

| Nhóm bài | Bài/biến thể bắt buộc | Kiểu đầu vào/giao diện |
| :--- | :--- | :--- |
| Calibration | TG-51 photon/electron legacy/electron modern; TRS-398 photon/electron | Biểu mẫu số đo theo protocol; kết quả hệ số và dose/MU do pylinac tính |
| Starshot | Gantry, collimator, MLC hoặc bàn điều trị | Ảnh/film; có giao diện chọn tâm, bán kính và tham số nhận tia |
| VMAT | DRGS, DRMLC, DRCS | Cặp ảnh trường mở/điều biến; chọn tolerance, ROI/segment/offset |
| CatPhan | 503, 504, 600, 604 của bản runtime đã khóa | Chuỗi CT/CBCT; chọn lát gốc, chỉnh tâm/ROI/góc/scale |
| ACR Phantoms | ACR CT 464, MRI Large, MRI Medium | Chuỗi DICOM; chọn lát/module và điều chỉnh hình học được hỗ trợ |
| Cheese Phantoms | TomoCheese, CIRS 062M | Chuỗi DICOM; ROI mật độ/HU và đường đáp ứng |
| GE Helios | GE Helios CT Daily | Chuỗi DICOM; contrast scale, phân giải, noise, uniformity, low contrast |
| Quart | Quart DVT và biến thể/alias còn tồn tại trong bản khóa | Chuỗi DICOM; HU, hình học, uniformity, CNR/SNR và ROI |
| Log Analyzer | Dynalog; Trajectory Log 2.1/3.0/4.0, `.bin`/`.txt` khi hỗ trợ | Trục actual/expected/difference, MLC, fluence và Gamma log |
| Picket Fence | Toàn bộ MLC/profile được bản khóa hỗ trợ | Ảnh; chọn model MLC, orientation, crop, sag/offset và tolerance |
| Winston–Lutz | Một bi/một trường | Bộ ảnh/góc; BB–CAX, isocenter/axis plots và hình overlay |
| Winston–Lutz Multi-Target | Multi-target/multi-field công khai | Bộ ảnh + form cấu hình BB/field, tọa độ và mapping; không dùng file cấu hình thô |
| Planar Imaging | Tất cả phantom kV/MV, light/rad và ACR mammography công khai | Ảnh; override tâm/góc/kích thước/SSD/ROI/invert theo phantom |
| Field Profile Analysis | Mọi metric profile công khai | Ảnh/profile; chọn manual/beam/geometric center, vị trí, width, normalization, edge, metrics |
| Field Analysis | Mô-đun cũ còn trong bản khóa | Giao diện đầy đủ để tương thích; bài mới mặc định dùng Field Profile Analysis |
| Nuclear | Max count rate, planar uniformity, center of rotation, tomographic resolution, simple sensitivity, four-bar, quadrant, tomographic uniformity, tomographic contrast | Form riêng từng phép thử; DICOM, frame/ROI/threshold và số liệu hoạt độ/thời gian khi cần |
| One-Offs/Contrib QA | Quasar Light/Rad Scaling; Jaw Orthogonality | Form/thao tác ảnh theo đúng class; ghi rõ nguồn “Mô-đun đóng góp”, khóa phiên bản và có kiểm thử riêng |
| PSQA Gamma | Gamma 1D/2D do pylinac công bố | Liều tham chiếu + đối chiếu; bắt buộc có ô “Chênh lệch liều (%)” và “DTA (mm)”, normalization và ngưỡng liều thấp |
| QA nhập tay và bài tự đặt | Hằng định đầu ra, laser, bàn, liên động, kiểm tra an toàn và biểu mẫu đơn vị | Số liệu/checklist/NA/ảnh đính kèm; không yêu cầu DICOM nếu bài không cần |
| DVH và chỉ số kế hoạch | RTDOSE + RTSTRUCT; CT khi hiển thị/hình học yêu cầu | Công cụ bổ sung trong kết quả PSQA; không gắn nhãn là phép tính pylinac nếu pylinac không cung cấp |

Danh sách class/phantom, điều khiển tay, kết quả và ranh giới Gamma đầy đủ nằm ở [danh mục QA pylinac](docs/pylinac-qa-catalog.md). Không dùng một nút chọn tùy ý rồi gửi mọi tệp vào cùng bộ phân tích. Mỗi bài công bố đầu vào hỗ trợ, số ảnh, trường bắt buộc, phép tính và giới hạn phân tích.

Trang mặc định lọc bài phù hợp máy/thiết bị đang chọn để không làm người dùng rối; bộ lọc “Tất cả bài pylinac” vẫn cho thấy đầy đủ danh mục. Một bài chưa triển khai hiển thị là “Đang xây dựng” trong chế độ quản lý phạm vi, không được trình bày như đã phân tích được và không được bỏ khỏi kế hoạch.

### 5.3. Danh mục bài và cài đặt

Tìm theo tên, nhóm, loại đầu vào và tần suất. Có bài thường dùng và nhớ máy vừa chọn. Mỗi thẻ/bảng bài nêu tên, mô tả một dòng, đầu vào cần chuẩn bị và nút bắt đầu.

“Cài đặt bài QA” gồm chỉ số, đơn vị, chuẩn so sánh, khoảng đạt/cảnh báo, cách tổng hợp, trường bắt buộc và mẫu báo cáo. Có biểu mẫu trực quan; mọi thành viên ngang quyền sửa. Thay đổi cài đặt tạo phiên bản mới cho lần sau, không đổi kết quả đã lưu.

Tần suất ngày/tháng/năm là thuộc tính để lọc và đặt lịch kiểm tra, không phải hệ thống phê duyệt. Hướng dẫn lý thuyết là liên kết đọc từ thư viện; sửa nội dung thư viện không tự đổi ngưỡng đang dùng.

## 6. QA máy — luồng thực hiện và kết luận

### 6.1. Luồng chuẩn

1. Chọn máy và bài. Hệ thống tạo vùng làm việc tự động; không có bước nhập mã hồ sơ.
2. Nhập số liệu hoặc tải đúng tệp được yêu cầu.
3. Hệ thống kiểm tra từng trường/tệp; lỗi xuất hiện ngay vị trí cần sửa.
4. Nhấn “Phân tích” khi có tính toán; bài nhập số liệu dùng “Tính kết quả” hoặc “Lưu kết quả” phù hợp.
5. Xem bảng chỉ số và ảnh/biểu đồ. Mở tùy chọn chuyên sâu nếu cần.
6. Chọn đánh giá của người thực hiện: “Đạt”, “Cảnh báo”, “Không đạt”; ghi chú nếu cần.
7. Lưu. Có thể mở lịch sử, xem xu hướng hoặc chọn “Xuất PDF” ngay tại kết quả.

Không yêu cầu chọn lại máy/đơn vị ở mỗi bước. Chuyển tab không làm mất trường đã nhập. Đóng trang khi chưa lưu có nhắc nhở.

### 6.2. Tính toán và đánh giá của người dùng

- Kết quả đo/tính là giá trị gốc; gợi ý đánh giá theo cài đặt được lưu riêng.
- Đánh giá cuối do người dùng chọn, không cần người duyệt hoặc phân quyền. Khi khác gợi ý, có chỗ ghi lý do, không tạo thủ tục phê duyệt.
- Hiển thị riêng “Theo tiêu chí đã chọn” và “Đánh giá của người thực hiện” khi cần phân biệt; không sửa giá trị đo để khớp kết luận.
- Không đủ dữ liệu không đồng nghĩa đạt. Nếu không tính được, ghi “Chưa đủ dữ liệu” hoặc “Không thể phân tích” ở phần tính toán; vẫn có thể lưu nhận xét/đánh giá thủ công với nguồn gốc rõ.
- “Không áp dụng” ở một dòng phải khác giá trị 0 và khác “Đạt”. Dòng bắt buộc thiếu dữ liệu không được tự bỏ khỏi mẫu số.
- Biên ngưỡng, dấu bằng, đơn vị, chuẩn và quy tắc tổng hợp được mô tả trong cài đặt; hệ thống không tự suy ra ngưỡng lâm sàng chung.

### 6.3. Phân tích ảnh phải có nội dung hữu ích

- Picket Fence: chọn lá/vạch để xem sai lệch; đánh dấu lá vượt ngưỡng ngay trên ảnh.
- Winston–Lutz: bảng từng góc và ảnh chồng tâm bi–tâm trường; không suy ra đồng tâm ba chiều từ một ảnh không đủ thông tin.
- Starshot: ảnh gốc, đường giao tia, tâm tính được, vòng tròn và chú giải bán kính/đường kính. Ẩn/hiện lớp phân tích; phóng to không làm sai thang đo.
- Field Profile/Field Analysis: cho chọn tâm/vị trí profile trên ảnh, độ rộng vùng lấy mẫu và các metric; lựa chọn trên ảnh và ô số phải đồng bộ.
- Các phantom Planar/CT/CBCT/MRI: hiển thị lát/ảnh, tâm, góc và ROI; cho điều chỉnh đúng các tham số mà class pylinac tương ứng hỗ trợ.
- PSQA: luôn hiển thị chênh lệch liều (%), DTA (mm), dữ liệu tham chiếu/đo, chuẩn hóa, ngưỡng liều thấp, vùng tính, tỷ lệ và vùng không tính được.
- Nếu chỉnh vùng chọn, tâm khởi tạo hoặc thang đo: chạy lại và lưu lần tính mới; không thay kết quả cũ âm thầm.

Toàn bộ 16 họ mô-đun chính cùng `QuasarLightRadScaling` và `JawOrthogonality` trong `contrib/One-Offs` dùng pylinac thông qua lớp tích hợp RT-CONNECT. Mỗi capability có form, input profile, tham số, result mapping, overlay và lỗi riêng; RT-CONNECT không thay thuật toán pylinac bằng phép tính tự viết. Hai bài contrib vẫn bắt buộc nhưng phải hiển thị đúng nguồn và có fixture/contract test riêng vì upstream không bảo đảm độ ổn định như các mô-đun chính. Tham khảo [tổng quan pylinac](https://pylinac.readthedocs.io/en/latest/), [One-Offs/Contrib](https://pylinac.readthedocs.io/en/latest/contrib.html) và [danh mục ánh xạ RT-CONNECT](docs/pylinac-qa-catalog.md).

Pylinac hiện công bố Gamma 1D và 2D, không có Gamma 3D trong danh mục công khai. Vì đã chốt pylinac là engine, PSQA mới chỉ cho chạy 1D/2D; Gamma 3D lịch sử của engine cũ ở chế độ chỉ đọc và ghi đúng nguồn engine, không mạo nhận là pylinac.

### 6.4. Dữ liệu sai và khôi phục

| Tình huống | Hành vi người dùng nhìn thấy |
| :--- | :--- |
| Thiếu giá trị hoặc nhập chữ vào ô số | Chỉ đúng ô, giữ các ô khác, hướng dẫn sửa |
| Sai đơn vị/thang đo | Yêu cầu xác nhận/chọn đơn vị; không tự suy ra mm từ pixel |
| Ảnh không đúng loại hoặc không nhận được vạch/bi/trường | Nêu lý do dễ hiểu, cho thay ảnh/chọn thiết lập được hỗ trợ |
| Bộ ảnh thiếu góc cho phép tính tổng hợp | Vẫn xem kết quả từng ảnh hợp lệ; chỉ số tổng hợp không có thì ghi rõ |
| Tệp hỏng, quá lớn hoặc tải gián đoạn | Thử lại tệp lỗi, không bắt nhập lại cả bài |
| Tính toán lâu, mất mạng hoặc đóng mở lại | Xem trạng thái thật và mở tiếp; không tạo nhiều lần tính do bấm lặp |
| Liều/hình học không tương thích | Không ghép tự động; yêu cầu chọn đúng dữ liệu hoặc cấu hình chuyển đổi được hỗ trợ |
| Máy đã ngừng dùng | Xem lịch sử bình thường; nhắc chọn máy đang dùng trước khi tạo bài mới |
| Người khác sửa cùng bài | Thông báo xung đột, giữ bản đang nhập để đối chiếu |
| Không có tiêu chí đánh giá | Hiện chỉ số và cho đánh giá thủ công; không tạo gợi ý đạt giả |

## 7. Lịch sử, xóa và xu hướng trong QA máy

### 7.1. Lịch sử

Bảng lọc theo máy, bài, ngày đo, người thực hiện, kết luận và nguồn dữ liệu. Hiện tên dễ nhận biết, thời điểm, số chỉ số cần xem, không hiện mã hồ sơ. Có thể phân nhóm bằng thư mục lồng nhau, đổi tên/di chuyển tự do nhưng không bắt tạo thư mục trước khi chạy bài.

Mở một bài xem lại số liệu gốc, cài đặt lúc tính, đánh giá, lần tính, ảnh và các bản PDF đã tạo. Tên máy hoặc tiêu chí thay đổi sau đó không làm biến đổi bản đã lưu. Có thể chọn “Làm lại từ bài này” để tạo lần mới.

### 7.2. Xóa và khôi phục

Có nút “Xóa” tại lịch sử và chi tiết, cả chọn nhiều. Xác nhận bằng tên bài, máy, thời gian và số mục; không bắt gõ ID. Mặc định đưa vào “Thùng rác”, loại khỏi danh sách chính và xu hướng. Có thể mở thùng rác, khôi phục hoặc “Xóa vĩnh viễn” với xác nhận rõ phạm vi.

Không tự xóa vĩnh viễn sau một số ngày chưa được đơn vị lựa chọn. Khi xóa phải chỉ rõ tệp/PDF/lần tính nào đi cùng, tệp nào còn được bài khác sử dụng. Không xóa tệp dùng chung và không xóa chéo đơn vị. Bài đang chạy phải được dừng hoặc xử lý kết quả hoàn thành muộn để không tự xuất hiện trở lại.

PDF đã tải về máy người dùng không thể thu hồi từ máy đó; thông báo ngắn trong xác nhận xóa vĩnh viễn. Nhật ký kỹ thuật tối thiểu có thể giữ dấu sự kiện xóa, không giữ lại toàn bộ kết quả qua một “bản sao bí mật”.

### 7.3. Xu hướng

Nằm trong thẻ “Xu hướng” của QA máy; từ kết quả mở đúng chỉ số, máy và loại bài. Hiện điểm đo, đường chuẩn/ngưỡng, sự kiện bảo trì khi có. Bấm điểm mở bài gốc.

Không trộn chỉ số khác đơn vị, cách tính, kỹ thuật đo hoặc thang đánh giá mà không phân nhóm. Phân biệt xu hướng giá trị đo với tỷ lệ đánh giá do người thực hiện chọn. Xóa/khôi phục bài cập nhật biểu đồ; không có dữ liệu thì nêu trạng thái trống, không tạo đường giả.

## 8. PDF từ kết quả QA

Từ bài đã lưu chọn “Xuất PDF”. Một vùng xem trước và một vùng lựa chọn nội dung, không phải chuyển sang một phân hệ báo cáo riêng.

Người dùng được:

- Chọn từng dòng chỉ số và từng cột; đổi thứ tự, nhãn hiển thị và số chữ số thập phân.
- Chọn có/không hiển thị tiêu chí, gợi ý máy tính, đánh giá người thực hiện, nhận xét.
- Chọn ảnh gốc, lớp phân tích, biểu đồ, chú thích; ví dụ hình vòng tròn và độ lệch tâm của Starshot.
- Ẩn/hiện toàn bộ phần, đổi bố cục, logo, tiêu đề, chân trang, khổ giấy, hướng giấy.
- Lưu mẫu dùng lại, nhân bản hoặc sửa mẫu cho từng loại bài và xuất bản PDF mới.
- Tải lại đúng PDF trước đây hoặc dựng bản mới từ kết quả được chọn.

Không bắt buộc một khối báo cáo “chuẩn” không thể ẩn. Tùy chỉnh báo cáo không được sửa ngầm số đo và ý nghĩa phép tính đã lưu. Một trường ghi đè bằng lời là nội dung người dùng, không biến thành chỉ số máy tính.

Bản PDF phải khớp xem trước, đúng tiếng Việt có dấu, công thức/đơn vị và ảnh đọc được. Không có dòng JSON, ID nội bộ, đường dẫn lưu trữ hay chữ kỹ thuật gỡ lỗi. Tên tệp dựa trên bài + máy + ngày, loại ký tự không hợp lệ.

Lỗi xuất PDF phải giữ lựa chọn; thử lại không tạo nhiều bản ngoài ý muốn. Nếu người dùng ẩn hết nội dung, báo “Chưa chọn nội dung để xuất”, không tải một tệp trắng.

## 9. Công cụ sinh học — một trang, tính đơn giản trước

### 9.1. Cách trình bày chung

Một trang có các thẻ lựa chọn “BED và EQD2”, “So sánh phác đồ”, “Tái xạ”, “Bù buổi chiếu”, “Giới hạn liều”, “Hệ số α/β”. Chỉ hiển thị công cụ đang chọn, không xếp cả sáu biểu mẫu dọc trang.

Bên trái nhập liệu; bên phải kết quả ngắn gọn, bảng hoặc đồ thị. Có nút “Xóa dữ liệu nhập”, “Tính”, “Xem công thức”, “Nguồn tham khảo”. Tùy chọn nâng cao đóng mặc định. Không bắt tên kịch bản, mã ca, đợt điều trị đã lưu hoặc chọn bệnh nhân.

Có thể lưu phép tính sau khi tính, đặt tên tự nhiên; đây là tiện ích tùy chọn. Giữ dữ liệu khi đổi thẻ trong phiên, không chia sẻ nhầm giữa đơn vị. Các phép tính không tự chèn vào bài QA hoặc báo cáo QA.

### 9.2. BED và EQD2

Nhập tổng liều D, số buổi n, hệ số α/β; liều mỗi buổi d được tính và hiển thị. Có thể chuyển sang nhập d và n, khi đó D được tính. Không cho ba trường D/n/d mâu thuẫn.

Kết quả chính BED, EQD2 và thông số đã dùng. Nguồn α/β có thể chọn từ bảng hoặc tự nhập; tự nhập được ghi là giá trị do người dùng chọn. Công thức cơ bản và đơn vị có thể mở để xem.

Đồ thị theo tổng liều phải chọn rõ một trong hai cách: giữ nguyên số buổi n hoặc giữ nguyên liều mỗi buổi d. Các điểm ứng với số buổi nguyên được phân biệt với đường minh họa liên tục. Không âm thầm thay cả n và d.

### 9.3. So sánh hai phác đồ

Hai cột A/B: tên tùy chọn, tổng liều, số buổi, liều mỗi buổi và α/β chung cho cùng mô/đích đánh giá. Hiển thị chênh lệch D, BED, EQD2 bằng bảng/biểu đồ đơn giản.

Không xếp hạng “phác đồ tốt hơn” chỉ dựa BED/EQD2. Nếu dùng α/β hoặc đích đánh giá khác nhau thì không tự kết luận tương đương; giao diện nêu khác biệt. Có nút đổi vị trí A/B và sao chép A sang B.

### 9.4. Tái xạ

Mặc định hai đợt, có thể thêm đợt. Mỗi đợt nhập liều tại cùng cơ quan/điểm đánh giá hoặc cùng loại chỉ số, số buổi và α/β. Không coi tổng liều kê đơn là liều cơ quan nguy cấp.

Hiển thị BED/EQD2 từng đợt và tổng vô hướng với giả định chung. Hồi phục và khoảng cách thời gian nằm trong tùy chọn nâng cao; mặc định không tự giảm liều cũ theo thời gian. Nếu người dùng đặt tỷ lệ hồi phục, hiển thị rõ giá trị và nguồn/giả định.

Không gọi tổng các Dmax ở các vị trí khác nhau là liều tích lũy không gian. Chưa có đăng ký ảnh và cộng liều theo voxel thì không hiển thị bản đồ cộng liều hay cam kết giới hạn cơ quan đã được đáp ứng. Ghi chú ngắn “Ước tính theo thông số và giả định đã chọn”, không chiếm một thẻ cảnh báo lớn trên toàn trang.

### 9.5. Bù buổi chiếu

Nhập phác đồ ban đầu, số buổi đã thực hiện, liều thực tế, gián đoạn nếu biết và phương án phần còn lại. Hiển thị tổng liều, BED/EQD2 dự kiến so với ban đầu. Có thể giải một ẩn như liều mỗi buổi còn lại khi người dùng chọn mục tiêu tương đương.

Mặc định so sánh phân liều bằng mô hình cơ bản. Hiệu chỉnh theo thời gian chỉ bật khi nhập đủ tham số và nguồn; không tự suy ra tham số từ tên bệnh. Không phát hành lịch điều trị hay đề nghị tăng liều tự động.

### 9.6. Giới hạn liều và hệ số α/β

Tra cứu ngay trong trang công cụ bằng bệnh cảnh, cơ quan, mục tiêu đánh giá, kiểu phân liều và nguồn. Cùng dữ liệu với thư viện kiến thức, không duy trì một bảng liều riêng dễ lệch nhau.

Bảng α/β có cơ quan/mô, loại đáp ứng hoặc mục tiêu nghiên cứu, giá trị/khoảng, đơn vị Gy, bối cảnh, nguồn, năm/phiên bản và ghi chú. Một cơ quan có thể có nhiều ước lượng; không bắt gộp thành một “giá trị đúng” duy nhất.

Không có dữ liệu phù hợp thì ghi “Chưa có tài liệu phù hợp”, không điền giá trị phỏng đoán. Chọn giá trị để tính phải giữ nguồn và bối cảnh; thay tài liệu thư viện không âm thầm đổi phép tính đã lưu.

## 10. Thư viện kiến thức — hai phạm vi, hai nhóm nội dung

### 10.1. Cấu trúc như một cổng tri thức

Thư viện là nơi đọc bài, tìm tài liệu, viết hướng dẫn và lưu PDF. Đầu trang có tiêu đề ngắn, ô tìm kiếm lớn, nút “Viết bài” và “Tải tài liệu”. Hai thẻ “Nội bộ đơn vị” và “Cộng đồng” quyết định phạm vi đang xem; mỗi thẻ có hai nhóm “Kiểm tra chất lượng máy” và “Phác đồ điều trị”. Chủ đề, loại tài liệu, bệnh cảnh, bệnh viện và năm là bộ lọc, không phải các thư viện rời nhau.

Vùng danh sách hiển thị tiêu đề, tóm tắt một dòng, nhóm, đơn vị cung cấp, ngày cập nhật, phiên bản tài liệu và số tệp. Chọn được kiểu danh sách hoặc thẻ. Mặc định sắp xếp theo độ phù hợp khi có từ khóa, theo mới cập nhật khi không có từ khóa. Có phân trang và giữ bộ lọc khi quay lại từ bài đọc.

Cột truy cập nhanh gồm “Bài đã lưu”, “Bài của đơn vị”, “Bản nháp”, “Đã lưu trữ”, “Thùng rác”. Bài dài có mục lục, liên kết đến từng đề mục, phần nguồn và các tệp đính kèm. Nhãn nguồn bệnh viện luôn gần tiêu đề; thư viện không gộp hai phác đồ cùng bệnh thành một phác đồ mặc định.

### 10.2. Ai thấy và sửa nội dung

| Nội dung/hành động | Thành viên đơn vị sở hữu | Tài khoản đơn vị khác | Tài khoản chưa có đơn vị | Chưa đăng nhập |
| :--- | :--- | :--- | :--- | :--- |
| Bản nháp, bài/tệp nội bộ, lịch sử sửa nội bộ | Đọc, viết, sửa ngang nhau | Không thấy | Không thấy | Không thấy |
| Bản đã chia sẻ trong Cộng đồng | Đọc; chỉnh bản nguồn và đăng bản cập nhật | Đọc và lưu dấu trang | Đọc và lưu dấu trang | Đăng nhập trước |
| Chia sẻ, cập nhật, thu hồi chia sẻ | Mọi thành viên đang hoạt động của đơn vị sở hữu | Không sửa/xóa bài nguồn | Không sửa/xóa bài nguồn | Không thực hiện |
| Lưu trữ, xóa, khôi phục bài nguồn | Mọi thành viên đang hoạt động của đơn vị sở hữu | Không thực hiện | Không thực hiện | Không thực hiện |
| Bài đã lưu | Mỗi người quản lý danh sách dấu trang của mình | Tương tự, khi bài còn được chia sẻ | Tương tự | Không thấy |
| Tải PDF | Tệp nội bộ của đơn vị và tệp được đính kèm bản chia sẻ | Chỉ tệp trong bản chia sẻ đang có hiệu lực | Tương tự | Không tải |

Đơn vị sở hữu dữ liệu khác với bệnh viện được nhắc tới trong bài. Nhập tên một bệnh viện vào nguồn tham khảo không tạo quyền đọc tài liệu của bệnh viện đó. Người tham gia nhiều đơn vị chỉ soạn và quản lý tài liệu trong đơn vị đang chọn; chuyển đơn vị phải giữ bản nháp ở đúng nơi, không mang bản nháp sang đơn vị mới.

Không thêm chức danh người duyệt hay quyền hành động theo bác sĩ/kỹ sư. Quyền chỉnh sửa của đồng nghiệp cùng đơn vị vẫn ngang nhau. Bài cộng đồng thuộc đơn vị nguồn; các đơn vị khác không được sửa hoặc xóa bản nguồn.

### 10.3. Viết, chỉnh sửa và đăng bài

1. Chọn “Viết bài”, chọn nhóm nội dung và nhập tiêu đề. Bản nháp ban đầu luôn ở “Nội bộ đơn vị”.
2. Soạn bằng trình biên tập trực quan: đề mục, đoạn văn, chữ đậm/nghiêng, danh sách, bảng, hình, chú thích, công thức, liên kết và trích dẫn. Có hoàn tác/làm lại; không yêu cầu nhập mã hoặc JSON.
3. Khai báo tóm tắt, chủ đề, nguồn, bệnh viện áp dụng, bệnh cảnh và tệp đính kèm. Bài hướng dẫn tự viết có thể ghi “Biên soạn tại đơn vị”, tên người biên soạn và ngày; không bắt phải có DOI.
4. Tự lưu sau khi dừng nhập, báo “Đang lưu”, “Đã lưu lúc …” hoặc “Chưa lưu được”. Có nút lưu chủ động và khôi phục bản nháp khi mở lại.
5. “Đăng trong đơn vị” đưa phiên bản đã chọn vào mục nội bộ; đồng nghiệp mở ngay, không có bước duyệt.
6. “Chia sẻ cộng đồng” mở bản xem trước chỉ gồm tiêu đề, nội dung và các tệp được chọn để chia sẻ. Nút cuối ghi đúng “Đăng lên cộng đồng”. Đây là lựa chọn phạm vi của người đăng.
7. Sửa bài đã đăng tạo bản nháp mới trong đơn vị. Người ngoài tiếp tục thấy đúng bản đã chia sẻ trước đó cho tới khi người trong đơn vị chọn “Cập nhật bản chia sẻ”.
8. Lịch sử sửa cho thành viên đơn vị xem ai thay đổi, thời điểm và khác biệt. Khôi phục một bản cũ tạo bản nháp mới, không xóa lịch sử và không tự đăng lại ra cộng đồng.

Các trường hợp bài viết không có PDF, tài liệu chỉ có PDF và bài kèm nhiều PDF/hình đều hợp lệ. Tài liệu chỉ có PDF cần tên, nhóm, mô tả ngắn, nguồn và phạm vi; không bắt viết lại cả nội dung PDF.

### 10.4. Chia sẻ và thu hồi chính xác

Bản chia sẻ là một bản chụp riêng của phiên bản và danh sách tệp do người đăng chọn. Bản nháp, ghi chú nội bộ, lịch sử sửa, tệp không chọn và số lượng tài liệu nội bộ không đi theo bài cộng đồng. Có thể chia sẻ bài diễn giải mà giữ PDF nguồn trong đơn vị; lúc đó người đọc chỉ thấy trích dẫn được người đăng chủ động đưa vào phần chia sẻ, không thấy tên/đường dẫn của tệp riêng.

Không mặc định chọn tất cả tệp khi đăng cộng đồng. Các trích dẫn, hình trong bài và liên kết tới tệp cần thuộc bản chia sẻ hoặc là liên kết bên ngoài đã nhập. Nếu bài chứa tham chiếu đến tệp nội bộ chưa chọn, chỉ rõ vị trí để người viết bỏ liên kết, dùng trích dẫn văn bản hoặc chọn chia sẻ tệp trước khi đăng.

“Ngừng chia sẻ” giữ bài nguồn trong đơn vị và bỏ bản chia sẻ khỏi tìm kiếm, trang đọc, gợi ý và các lần tải tệp mới của cộng đồng. Dấu trang của người khác hiển thị “Bài viết không còn được chia sẻ”, không tiếp tục giữ tiêu đề/tóm tắt riêng trong danh sách. Dữ liệu đã được một người tải xuống hoặc đọc trước đó không thể thu hồi khỏi thiết bị của họ; lời nhắc ngắn này chỉ xuất hiện trong thao tác chia sẻ/thu hồi liên quan.

Bản nháp của bản cập nhật không xuất hiện trong cộng đồng. Đăng hoặc cập nhật bị lỗi không thay thế nửa chừng bản đang đọc. Nhấn đăng nhiều lần do mạng chậm không sinh nhiều bài cộng đồng.

### 10.5. Tải lên, đọc và lưu PDF

Tải lên bằng chọn tệp hoặc kéo thả, có danh sách chờ, tiến độ theo tệp, hủy và thử lại riêng từng tệp. Kiểm loại và dung lượng trước khi gửi; tệp trùng chỉ được cảnh báo trong phạm vi đơn vị được phép xem. Không tiết lộ đơn vị khác đang có cùng tài liệu.

Trình đọc có mục lục bài, hình thu nhỏ các trang PDF, chuyển trang, nhập số trang, phóng to/thu nhỏ, tìm trong PDF và tải xuống. Dùng nhãn tiếng Việt. Hiển thị tên nguồn, phiên bản và số trang đang đọc; tệp gốc giữ nguyên ngôn ngữ/nội dung.

PDF có văn bản cho phép tìm nội dung và mở đúng trang chứa từ khóa. PDF là ảnh vẫn xem/tải được; hiển thị “Tệp này chưa có lớp văn bản để tìm bên trong”. Nhận dạng chữ là công việc bổ sung có thể chạy nền, không chặn đăng bài bằng thông tin mô tả và không tự biến số đọc từ ảnh thành tiêu chí liều.

Đổi PDF tạo phiên bản tệp mới; bản cũ còn được dùng bởi phiên bản đã lưu. Các hình thu nhỏ, nội dung tìm kiếm và tệp tải phải dùng cùng phạm vi với phiên bản bài chứa chúng.

### 10.6. Tìm kiếm và dấu trang

Tìm có dấu/không dấu, tên bài, từ đồng nghĩa được quản lý, tác giả, cơ sở cung cấp, tên tệp và văn bản PDF trích được. Tìm “dong tam” vẫn trả nội dung “đồng tâm” trong phạm vi đang xem. Đoạn trích và đánh dấu từ tìm được lấy từ đúng phiên bản đang được phép đọc.

Bộ lọc gồm phạm vi, nhóm, chủ đề, loại bài/PDF, bệnh viện nguồn, bệnh cảnh, cơ quan, kỹ thuật, phân liều, năm và thời điểm cập nhật. Lọc phạm vi được thực hiện trước khi tính số kết quả, gợi ý từ khóa, danh sách bệnh viện hay chủ đề. Cộng đồng không hiện dấu hiệu rằng một đơn vị có bài nội bộ khớp từ khóa.

“Lưu bài” là dấu trang cá nhân để đọc lại, không sao chép tệp hay mở rộng quyền đọc. “Đã lưu trữ” là trạng thái bài của đơn vị; hai khái niệm hiển thị tách nhau. So sánh hai bài phải kiểm quyền của từng nguồn và giữ nhãn bệnh viện/phiên bản ở mỗi cột.

### 10.7. Lưu trữ, xóa và khôi phục

“Lưu trữ bài” đưa bài ra khỏi danh mục đang sử dụng, thu hồi bản cộng đồng nếu có và giữ nội dung trong “Đã lưu trữ” của đơn vị. “Đưa vào thùng rác” ẩn bài, tệp và bản chia sẻ khỏi nơi đọc/tìm kiếm thông thường; người thao tác thấy trước tác động và có thể khôi phục.

Khôi phục từ lưu trữ hoặc thùng rác đưa bài về nội bộ, không tự đăng lại cộng đồng. Tên hoặc vị trí trùng được xử lý bằng biểu mẫu lựa chọn; không ghi đè một bài khác.

Thùng rác giữ mặc định 30 ngày trước khi đủ điều kiện dọn. Xóa vĩnh viễn chỉ thực hiện cho bài trong thùng rác, nêu rõ không khôi phục bằng ứng dụng. Tệp còn được một phiên bản hợp lệ hoặc kết quả đã lưu tham chiếu không bị xóa vật lý nhầm; phần đã dùng trong kết quả trước đó vẫn giữ bản chụp của kết quả đó trong phạm vi của kết quả.

### 10.8. Nội dung Kiểm tra chất lượng máy

Mỗi bài hướng dẫn có tên, mục đích, máy/kỹ thuật/phantom áp dụng, dụng cụ, chuẩn bị, thao tác thu dữ liệu, phương pháp phân tích, công thức và đơn vị, cách đọc hình/kết quả, tiêu chí đánh giá theo nguồn, hạn chế và tài liệu tham khảo.

Mở hướng dẫn từ bài kiểm tra rồi quay lại không mất số liệu. Bài đọc có hình, bảng và liên kết trang/mục của nguồn. Đọc, sửa hoặc chia sẻ bài không tự cập nhật ngưỡng thực thi hoặc kết quả kiểm tra cũ.

### 10.9. Nội dung Phác đồ điều trị theo bệnh viện

| Nhóm thông tin | Trường cần thể hiện |
| :--- | :--- |
| Nguồn và phạm vi | Đơn vị sở hữu; bệnh viện có phác đồ; tác giả, tài liệu, năm/phiên bản, trang/mục; phạm vi nội bộ/cộng đồng |
| Bệnh cảnh | Vị trí bệnh, mô học, giai đoạn/nguy cơ, mục đích, hậu phẫu/chưa phẫu thuật/tái phát, đối tượng áp dụng và loại trừ |
| Xạ trị | Kỹ thuật, thể tích đích, tổng liều, số buổi, liều mỗi buổi, tăng liều/tăng liều đồng thời, nhịp điều trị |
| Phối hợp | Vai trò và thời điểm hóa trị, phẫu thuật hoặc phương thức khác theo nguồn; ghi rõ phần chưa có |
| Bao phủ đích | PTV, D95/D98/D2 hoặc V95/V100 theo nguồn; đơn vị, chuẩn hóa, mục tiêu và mức chấp nhận |
| Cơ quan nguy cấp | Cơ quan, Dmax/Dmean/Dx/Vx, tham số x và đơn vị, ngưỡng, phân liều, bối cảnh, ưu tiên/ngoại lệ có nguồn |
| HI và CI | Tên định nghĩa/công thức, thể tích/mức liều sử dụng, tiêu chí đánh giá và nguồn |
| Lưu ý lập kế hoạch | Điểm nóng/lạnh, vùng nối trường, chuyển động/hô hấp, tư thế và lưu ý theo bệnh cảnh |

Bệnh viện A và B có thể có phác đồ khác nhau cho cùng bệnh, kể cả cùng phân liều. Không gộp dựa trên tên bệnh. Mỗi phác đồ giữ nguồn, bối cảnh và phiên bản riêng. Người ngoài chỉ tra được phác đồ của A khi A đã chia sẻ phiên bản tương ứng.

Ví dụ “vú đã phẫu thuật 107%, vú chưa phẫu thuật 105%” là nhu cầu lưu các quy ước khác nhau. Chưa xác minh nguồn; không dùng 105%/107% làm mặc định. Cần bệnh viện, tài liệu, tình huống, định nghĩa liều tối đa và liều chuẩn hóa khi đưa vào bảng tham khảo.

Giới hạn liều và hệ số α/β là bảng có nguồn bên trong thư viện, dùng chung với Công cụ sinh học. Chỉ đưa số liệu sang công cụ khi người dùng chọn; giá trị trong PDF chưa đối chiếu không tự trở thành tham số tính. Bài bị thu hồi chia sẻ không còn được chọn cho phép tính mới ở đơn vị khác; phép tính đã lưu giữ giá trị và trích dẫn đã dùng, không mở quyền đọc tiếp toàn bộ bài nguồn.

### 10.10. Phạm vi tuyển tập

Theo dõi tài liệu đã có và còn thiếu theo bệnh viện/bệnh cảnh: vú, đầu cổ, phổi, tuyến tiền liệt, phụ khoa, trực tràng/hậu môn, thần kinh trung ương, gan, tiêu hóa, tiết niệu, lymphoma, di căn và nhóm do người dùng bổ sung.

Mỗi dòng có nguồn dự kiến, đã có/chưa có, phần đã trích và phần cần bổ sung. Không sao chép nội dung nội bộ bệnh viện sang cộng đồng để lấp phần thiếu. Hoàn thành chức năng thư viện được nghiệm thu với dữ liệu tổng hợp; tuyển tập tài liệu thật chỉ được mô tả theo những nguồn thực tế đã có.

## 11. Yêu cầu liên kết và tính nhất quán

- Một chỉ số QA có tên, định nghĩa, đơn vị và kiểu đầu vào; báo cáo và xu hướng dùng cùng kết quả đã lưu.
- Thay chuẩn/ngưỡng ảnh hưởng bài mới, không thay bài cũ.
- Sửa đánh giá người dùng không sửa chỉ số máy tính. Xu hướng phân biệt được hai loại.
- Thay nguồn α/β/giới hạn liều không thay phép tính cũ; người dùng chủ động tính lại.
- Xóa bài loại kết quả khỏi nơi tìm kiếm và xu hướng; khôi phục trả về đúng bài một lần.
- Thư viện hướng dẫn cung cấp kiến thức; áp dụng một giá trị vào cài đặt/công cụ là hành động rõ ràng.
- Tệp và phiên bản nội bộ vẫn tồn tại để truy xuất đúng, nhưng không xuất hiện như công việc phải làm của bác sĩ/kỹ sư.

## 12. Ma trận yêu cầu và giai đoạn

Mỗi mã FR-UX1 dưới đây thuộc mốc mới; không dùng kiểm thử cùng số ở bản cũ để tự đóng yêu cầu.

| Giai đoạn | Yêu cầu nghiệp vụ | Đầu ra người dùng hoặc nền tảng |
| :--- | :--- | :--- |
| P0 | FR-UX1-P00-01 | Chốt cấu trúc năm mục, phạm vi và bản đồ chuyển đổi |
| P1 | FR-UX1-P01-01 | Nền hiện có chạy lại được, không làm mất dữ liệu khi cải tiến |
| P2 | FR-UX1-P02-01 | Truy cập từ xa và xác thực đúng môi trường |
| P3 | FR-UX1-P03-01 | Đăng nhập/trang chủ gọn, điều hướng và tiếng Việt nhất quán |
| P4 | FR-UX1-P04-01 | Đơn vị/cơ sở/máy/thành viên gọn, ngang quyền |
| P5 | FR-UX1-P05-01 | Danh mục, bắt đầu bài, lịch sử, xóa và khôi phục |
| P6 | FR-UX1-P06-01 | Đúng loại đầu vào; không bắt DICOM cho nhập tay |
| P7 | FR-UX1-P07-01 | QA nhập tay, toàn bộ 16 họ mô-đun/biến thể chính và các bài QA contrib công khai của bản pylinac runtime đã khóa |
| P8 | FR-UX1-P08-01 | PSQA có RTDOSE/dữ liệu đối chiếu, form ΔD (%) + DTA (mm), Gamma pylinac 1D/2D |
| P9 | FR-UX1-P09-01 | PDF tùy chỉnh ngay từ kết quả, hình phân tích thật |
| P10 | FR-UX1-P10-01 | Xu hướng gắn với lịch sử và định nghĩa chỉ số |
| P11 | FR-UX1-P11-01 | Thư viện nội bộ/cộng đồng, hai nhóm kiến thức, soạn/sửa bài, PDF, tìm kiếm, lưu bài, lưu trữ/xóa/khôi phục; hướng dẫn tách cài đặt bài |
| P12 | FR-UX1-P12-01 | Trang công cụ sinh học hợp nhất, tính không cần lưu trước |
| P13 | FR-UX1-P13-01 | BED/EQD2, đồ thị D và nguồn α/β |
| P14 | FR-UX1-P14-01 | So sánh hai phác đồ đơn giản |
| P15 | FR-UX1-P15-01 | Tái xạ và bù buổi chiếu đơn giản, giả định có thể mở |
| P16 | FR-UX1-P16-01 | Biểu mẫu phác đồ theo bệnh viện/bệnh cảnh, giới hạn liều và α/β có nguồn; kế thừa phạm vi nội bộ/cộng đồng của P11 |
| P17 | FR-UX1-P17-01 | DVH/chỉ số kế hoạch là phần trong PSQA |
| P18 | FR-UX1-P18-01 | Kiểm thử trọn luồng và nghiệm thu sử dụng thực tế |
| P19 | FR-UX1-P19-01 | Phát hành từ xa đúng bản và không làm mất dữ liệu |
| P20 | FR-UX1-P20-01 | Hướng dẫn gọn, nhận phản hồi và mở rộng có theo dõi |

## 13. Ma trận nghiệm thu xuyên suốt

| Mã | Tiêu chí phải chứng minh |
| :--- | :--- |
| B01 | Năm mục chính; không còn báo cáo/xu hướng/các phép tính sinh học thành mục chính riêng |
| B02 | Giao diện gọn ở hai kích thước chuẩn; thao tác chính không cần cuộn trang dài |
| B03 | Không trộn ngôn ngữ hệ thống; không JSON/ID kỹ thuật trong màn hình/PDF thông thường |
| B04 | Thành viên ngang quyền, dữ liệu các đơn vị vẫn tách biệt |
| B05 | Danh mục có phân biệt nhập tay, ảnh, liều; nhập tay không cần DICOM |
| B06 | Đủ 16 họ chính, biến thể và bài QA contrib công khai của pylinac khóa phiên bản, có phân tích/kết quả/giao diện thật; PSQA dùng Gamma pylinac 1D/2D với ΔD (%) và DTA (mm) |
| B07 | Chỉ số máy tính và đánh giá người dùng độc lập, thiếu dữ liệu không giả thành đạt |
| B08 | Lịch sử mở lại được, xóa/khôi phục có hiệu lực với xu hướng và tệp |
| B09 | PDF chọn được từng dòng/cột/ảnh và khớp xem trước; không có khối bắt buộc không thể ẩn |
| B10 | Sáu công cụ sinh học ở cùng trang, nhập/tính đơn giản, không cần hồ sơ QA |
| B11 | Hai nhóm kiến thức trong cả nội bộ/cộng đồng; phác đồ có bệnh viện/bệnh cảnh, PTV, HI/CI, phối hợp điều trị và nguồn |
| B12 | Bảng α/β/giới hạn liều truy được nguồn, không dùng ví dụ chưa xác minh làm mặc định |
| B13 | Nội bộ không lộ cho đơn vị khác; chia sẻ có chủ đích theo phiên bản/tệp; thu hồi có hiệu lực với tìm kiếm, bài đã lưu và yêu cầu tải mới |
| B14 | Soạn/sửa bài, PDF, tìm không dấu, lưu bài, lưu trữ, thùng rác và khôi phục qua giao diện tiếng Việt; không biểu mẫu JSON |

Không tài liệu nào có thể liệt kê mọi lỗi chưa từng gặp. Các nhóm lỗi trong tài liệu kỹ thuật và từng giai đoạn là mức bao phủ bắt buộc; lỗi mới phải bổ sung ca kiểm thử hồi quy cùng cách phục hồi.
