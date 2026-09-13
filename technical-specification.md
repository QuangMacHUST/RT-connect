# RT-CONNECT — Đặc tả kỹ thuật

**Phiên bản:** 2.3
**Ngày:** 2026-09-13
**Mốc yêu cầu:** UX1.3.
**Nguồn:** business-analysis.md v1.3; **kế hoạch:** plan.md v5.3; **danh mục bộ tính:** [docs/pylinac-qa-catalog.md](docs/pylinac-qa-catalog.md) v1.1.

## 1. Hiệu lực, hiện trạng và phạm vi thay đổi

Bản này thay thế đặc tả 1.30, lưu tại [bản trước](docs/history/pre-ux-20260912/technical-specification.md). Mọi thiết kế bên dưới là đích triển khai UX1, trừ đoạn ghi rõ là đã quan sát trong mã. Không đồng nhất tài liệu mục tiêu với chức năng đã phát hành.

Đã quan sát trong mã ngày 2026-09-12:

- Ứng dụng web có nhiều tuyến riêng cho kho QA, báo cáo, xu hướng, hướng dẫn QA và các trang sinh học. Đây là cấu trúc cần chuyển đổi.
- Backend có mô hình đơn vị/cơ sở/máy, hồ sơ QA, tệp, lần phân tích Gamma/DVH/QA nhập số liệu, báo cáo, xu hướng và công cụ sinh học.
- Bộ dựng báo cáo hiện có kết xuất từ dữ liệu chụp tại lúc tạo báo cáo; tái sử dụng nguyên tắc này.
- Chưa thấy bộ tích hợp toàn bộ danh mục pylinac trong các dịch vụ phân tích hiện có. Không được đóng P7 mới bằng bài nhập tay, ba bài ảnh ví dụ hoặc chỉ một phần danh mục.
- Nền sử dụng React/TypeScript/Vite, FastAPI, SQLAlchemy/Alembic, psycopg 3, PostgreSQL, hàng đợi Redis và lưu trữ đối tượng tương thích S3. Supabase phục vụ xác thực.
- requirements.lock của API hiện dùng Python 3.14 và chưa có pylinac. Quyết định UX1.2 chọn pylinac làm engine chính thức cho mọi capability pylinac cung cấp; phiên bản phát hành phải được khóa cùng hash và có worker runtime tương thích.

Không thay đổi nhà cung cấp nền tảng: Railway chạy backend và PostgreSQL; Supabase chỉ làm xác thực. Không chuyển dữ liệu nghiệp vụ sang Supabase. Đợt viết tài liệu không xác nhận cấu hình Railway đang chạy hoặc tự triển khai thay đổi.

## 2. Kiến trúc mục tiêu

### 2.1. Ranh giới thành phần

| Thành phần | Trách nhiệm |
| :--- | :--- |
| Web | Biểu mẫu tiếng Việt, điều hướng gọn, hiển thị ảnh/kết quả, xem trước PDF, tra cứu |
| API | Kiểm tra phiên/đơn vị, giao dịch nghiệp vụ, hợp đồng dữ liệu, kiểm tra đầu vào |
| Bộ tính QA nhập tay/sinh học | Hàm xác định, kiểm tra đơn vị và miền giá trị, không tự truy cập hồ sơ bệnh nhân |
| Pylinac QA worker | Toàn bộ 16 họ mô-đun chính/biến thể, QA `contrib/One-Offs` của bản pylinac đã khóa và Gamma 1D/2D |
| Bộ xử lý liều kế thừa RT-CONNECT | Chỉ đọc kết quả Gamma 3D cũ và chạy DVH nếu hợp đồng còn hiệu lực; không tạo Gamma mới mang nhãn pylinac |
| Bộ xuất báo cáo | Kết xuất PDF từ bản chụp nội dung + tài nguyên cố định |
| PostgreSQL trên Railway | Dữ liệu nghiệp vụ, phiên bản, kết quả, nhật ký, trạng thái tác vụ |
| Redis | Điều phối công việc dài; không phải nơi duy nhất giữ trạng thái nghiệp vụ |
| Kho S3 riêng tư | Tệp gốc, ảnh phân tích và PDF; truy cập qua kiểm tra phạm vi và liên kết giới hạn thời gian |
| Supabase Auth | Đăng nhập, phiên và định danh; không lưu bảng QA/phác đồ của sản phẩm |

Các bộ tính không dựa vào LLM để tạo giá trị số. Nội dung tri thức là bản ghi có nguồn; không tự sinh ngưỡng từ mô hình ngôn ngữ.

### 2.2. Đơn vị và thành viên ngang quyền

Mọi truy vấn dữ liệu riêng bắt đầu với phạm vi organization_id xác định từ phiên hợp lệ và tư cách thành viên đang hoạt động. Không lấy tài nguyên toàn cục theo ID rồi mới xét phạm vi ở cuối. Tác vụ nền nhận phạm vi và kiểm tra lại khi ghi kết quả. Nhánh thư viện cộng đồng có hàm đọc riêng: yêu cầu định danh Supabase hợp lệ và chỉ truy vấn bản chia sẻ đang hiệu lực; không bắt tư cách thành viên đơn vị nguồn hoặc đơn vị đang chọn. Không mở rộng truy vấn riêng thành phép OR đọc mọi hàng public trong bảng nguồn.

Không thêm ma trận vai trò/action permission. Mọi thành viên hoạt động trong một đơn vị dùng cùng chức năng. Quyền truy cập dữ liệu đơn vị khác, phiên hết hạn và giới hạn kỹ thuật của dịch vụ vẫn được kiểm soát.

Cơ chế optimistic concurrency dùng revision/ETag để chống ghi đè đồng thời; đây là bảo toàn dữ liệu, không phải phê duyệt.

## 3. Hợp đồng giao diện

### 3.1. Thành phần bố cục

- AppShell: sidebar 200–216 px, thanh trên 48–56 px, nội dung dùng chiều cao khả dụng của 100dvh.
- Văn bản 14 px; bảng 13–14 px; tiêu đề 22–24 px; nhịp khoảng cách 8/12/16 px.
- Nút trên máy tính cao 32–36 px; vùng chạm thiết bị cảm ứng khoảng 44 px. Nhãn có thể xuống dòng khi cần.
- CompactPage: tiêu đề ngắn + thanh tác vụ + vùng dữ liệu. Bỏ thẻ mô tả phát triển, khẩu hiệu dài và min-height lớn không có nội dung.
- SplitPane: biểu mẫu và kết quả, danh sách và chi tiết, hoặc xem trước và lựa chọn báo cáo.
- AdvancedDisclosure: tùy chọn nâng cao đóng mặc định, giữ giá trị khi đóng.
- DataTable: tiêu đề cố định, phân trang, lọc; không tải toàn bộ lịch sử vào bộ nhớ.
- Không khóa chiều cao khiến lỗi xác thực hoặc trợ giúp bị cắt; ở zoom 200% chuyển sang bố cục một cột có cuộn.

Mỗi màn cần trạng thái đang tải, chưa có dữ liệu, có dữ liệu, nhập sai, mất kết nối và hoàn tất. Không dùng màn trắng làm trạng thái chờ.

### 3.2. Tuyến đích và chuyển hướng tương thích

Các đường dẫn là nội bộ kỹ thuật, không phải nhãn người dùng. Tên QA/cơ quan/máy luôn dùng thuộc tính hiển thị.

| Tuyến đích | Nội dung | Tuyến cũ cần xử lý |
| :--- | :--- | :--- |
| /app | Trang chủ gọn | Giữ đường dẫn |
| /app/organization | Đơn vị và thiết bị với thẻ nội bộ | Giữ liên kết cũ tới cơ sở/máy |
| /app/qa | Danh mục, lịch sử, xu hướng | Kho QA chuyển thành thẻ Lịch sử |
| /app/qa/results/:resultId | Kết quả và các lần tính | /app/qa/cases/:caseId/* phải tra quan hệ cũ, không đổi ID bằng chuỗi |
| /app/qa/results/:resultId/report | Xem trước/chỉnh PDF của kết quả | /app/reports dẫn tới đúng báo cáo/bài nếu có ngữ cảnh, không có thì vào Lịch sử |
| /app/qa?tab=trends | Xu hướng, lọc theo máy/bài/chỉ số | /app/trend giữ bộ lọc còn hợp lệ |
| /app/biological?tool=... | Một trong sáu công cụ | Các đường dẫn BED/compare/re-irradiation/fraction-compensation chuyển đúng công cụ |
| /app/knowledge?section=qa | Thư viện QA máy | /app/qa-protocols vào phần tham khảo, không vào trình tạo bài |
| /app/knowledge?section=treatment | Thư viện phác đồ | /app/biological/knowledge chuyển vào nhánh này |
| /app/knowledge?scope=organization&section=qa | Thư viện nội bộ, cần đơn vị đang chọn | Mặc định dữ liệu nội bộ khi chuyển tuyến cũ |
| /app/knowledge?scope=community&section=treatment | Thư viện cộng đồng, chỉ yêu cầu đăng nhập | Định danh chưa có đơn vị vẫn truy cập được |
| /app/knowledge/articles/:articleId | Bài của đơn vị, mục lục và các phiên bản nội bộ | Tra chủ sở hữu từ phiên; không dùng tham số làm quyền |
| /app/knowledge/community/:publicationId | Bản chia sẻ có hiệu lực, chỉ nội dung được chọn | Không mở trực tiếp bản nguồn nội bộ |
| /app/knowledge/write; /app/knowledge/articles/:articleId/edit | Viết bài, tải PDF, sửa bản nháp | Biểu mẫu tiếng Việt, cần đơn vị sở hữu |
| /app/knowledge/manage?view=drafts\|archived\|trash | Bản nháp, lưu trữ, thùng rác của đơn vị | Dấu trang cá nhân ở view=saved, không đổi quyền đọc |
| /app/system/status | Trạng thái hỗ trợ | Giữ tuyến nhưng đưa vào menu tài khoản |

Tuyến mới là hợp đồng đề xuất; phải cập nhật route registry khi triển khai P3. Bảo toàn lịch sử trình duyệt, nút quay lại, bộ lọc và liên kết sâu. Tài nguyên đã xóa trả trang “Bài đã được chuyển vào thùng rác” khi người truy cập đúng đơn vị; tài nguyên không thuộc phạm vi không tiết lộ sự tồn tại.

### 3.3. Ngôn ngữ và nội dung không kỹ thuật

Dùng khóa thông điệp tập trung và duy nhất ngôn ngữ vi cho giao diện đợt này: trình đơn, kiểm tra trường nhập, trạng thái, lỗi, trình đọc PDF, soạn bài và báo cáo. Không có lựa chọn tiếng Anh trong giao diện. Mã lỗi chưa biết nhận thông báo chung tiếng Việt; không đưa thông báo gốc của thư viện ra ngoài. Tệp nguồn tiếng nước ngoài và tên tài liệu giữ nguyên nội dung; các nút quanh tệp vẫn tiếng Việt.

Mã lỗi, UUID, checksum, storage key, engine version vẫn nằm trong hợp đồng máy và log. UI bình thường chỉ nhận/hiển thị mô tả thân thiện, trường cần sửa, khả năng thử lại. Không có ô JSON, nút tải JSON hoặc ID hồ sơ trong bảng/PDF. Trợ giúp chẩn đoán cho vận hành là đường riêng, không trở thành bảng “chi tiết” của kết quả thường dùng.

Tên khoa học, viết tắt và tên nguồn nguyên bản là ngoại lệ có kiểm soát. Ảnh chụp màn hình kiểm thử phải kiểm cả trạng thái lỗi và bảng trống, không chỉ trang đẹp.

## 4. Mô hình nghiệp vụ đích và chuyển đổi dữ liệu

Tên ở cột kỹ thuật không xuất hiện trên giao diện. Bổ sung dần qua migration, không xóa bảng cũ ngay.

| Thực thể đích | Trường/cấu trúc chính | Quan hệ với hiện trạng |
| :--- | :--- | :--- |
| QATestDefinition | key nội bộ, nhãn dịch, nhóm, input_modes, chỉ số, hướng dẫn, khả năng engine | Danh mục mới, tách khỏi tài liệu QA |
| QATestConfigurationVersion | đơn vị/máy/bài, fields, tiêu chí, đơn vị, profile ảnh, version | Tái sử dụng/migrate phần thực thi trong QAProtocolVersion/Rule |
| QAAttempt | đơn vị, máy, bài, tên, thời gian đo, nguồn, ghi chú, revision, deleted_at | QACase cũ có thể là lớp lưu trữ phía dưới; adapter tránh mất liên kết |
| MeasurementRow | metric_key, value/boolean/NA, unit, nguồn, uncertainty tùy chọn | Chuẩn hóa QA nhập tay |
| AnalysisRun | attempt, engine/profile version, input snapshot, config snapshot, status, result | Lớp giao diện chung trên các run chuyên biệt hiện có |
| AssessmentRevision | run/attempt, người dùng, thời điểm, Đạt/Cảnh báo/Không đạt, ghi chú | Lưu riêng với machine-suggested assessment |
| ImageAnalysisArtifact | ảnh nền, hệ tọa độ, lớp hình học, nhãn, thumbnail | Mới cho QA ảnh; dùng Artifact hiện có |
| ReportRevision | nguồn run/assessment, layout snapshot, locale, render version, tệp | Giữ mô hình snapshot hiện có, mở rộng bộ chọn dòng/ảnh |
| TrendPoint | run, metric definition/version, value/unit, máy, phép đo, visibility | Tái sử dụng; bổ sung tác động xóa/khôi phục |
| KnowledgeArticle / KnowledgeArticleRevision | chủ sở hữu, QA/TREATMENT, bản nháp/nội bộ, nội dung và tệp theo phiên bản | Chuyển dữ liệu thư viện cũ về nội bộ; tách quy trình tính khỏi bài đọc |
| KnowledgePublication | chủ sở hữu, bản chia sẻ bất biến, các tệp được chọn, phiên bản quyền truy cập | Cộng đồng đọc riêng bản chia sẻ; không nối lấy toàn bộ bản nguồn |
| KnowledgeAsset / KnowledgeRevisionAsset | đối tượng tệp riêng tư, nội dung trích, hình thu nhỏ, liên kết phiên bản | Bộ lưu tệp thư viện riêng; không dùng chung quyền đọc với tệp ca QA |
| KnowledgeBookmark | định danh người lưu, tham chiếu nội bộ/cộng đồng | Dấu trang cá nhân; không sao chép nội dung hoặc cấp thêm quyền |
| TreatmentContext | bệnh, giai đoạn, bệnh viện, sau mổ, mục tiêu, kỹ thuật, phân liều | Bối cảnh bắt buộc khi áp dụng nguồn |
| DoseConstraint | organ, metric, tham số, comparator, limit, unit, normalization, context, source version | Không coi là số liều chung cho cơ quan |
| AlphaBetaEntry | mô/đáp ứng, value/range Gy, context, source version | Dùng chung thư viện và công cụ |
| CalculationWorksheet | loại công cụ, tên tùy chọn, input/result/source snapshot | Chỉ tạo khi người dùng lưu; không bắt BiologicalScenario trước khi tính |
| DeletionRecord | target, phạm vi tệp, deleted_by/time, restore/purge status | Xóa mềm và dọn vật lý có kiểm soát |

Ràng buộc: mọi thực thể riêng của đơn vị có khóa phạm vi; tham chiếu nguồn/phiên bản bất biến cho kết quả đã lưu. Một tệp dùng chung có quan hệ tham chiếu; dọn tệp chỉ khi không còn tham chiếu hợp lệ.

Nội dung thiếu nguồn không được migrate thành “đã xác minh”. Dữ liệu lịch sử chỉ có rule thì chuyển sang cài đặt bài; chỉ có bài viết thì chuyển thư viện; trộn cả hai thì tách, giữ liên kết nguồn gốc và báo những dòng cần đối chiếu.

## 5. Hợp đồng API và lỗi

### 5.1. Nguyên tắc chung

Prefix /api/v1. Dưới đây là API đích; có thể dùng adapter trên API hiện tại trong chuyển tiếp, nhưng phải có kiểm thử tương thích.

Mỗi yêu cầu ghi dữ liệu gồm schema version nội bộ, đơn vị đã kiểm tra, dữ liệu đã chuẩn hóa và expected_revision nếu sửa. Yêu cầu tạo/chạy/xuất dùng khóa idempotency; cùng khóa+cùng dữ liệu trả cùng kết quả, cùng khóa+khác dữ liệu trả xung đột.

| Nhóm | API đích tiêu biểu | Ý nghĩa |
| :--- | :--- | :--- |
| Bài QA | GET /qa-test-definitions; GET/PUT /qa-test-configurations/... | Danh mục và cài đặt thực thi, không phải thư viện |
| Lượt thực hiện | POST/GET /qa-attempts; GET/PATCH /qa-attempts/:id | Tạo theo tên bài/máy; cập nhật có revision |
| Nhập dữ liệu | PUT /qa-attempts/:id/measurements; POST .../uploads | Số liệu thủ công hoặc đăng ký tải tệp |
| Kiểm tra và chạy | POST .../validate; POST .../runs; GET /analysis-runs/:id | Kiểm tra input, tạo run, xem trạng thái |
| Đánh giá | POST /qa-attempts/:id/assessments | Lưu đánh giá của người thực hiện độc lập |
| Lịch sử và xóa | GET /qa-history; DELETE /qa-attempts/:id; POST .../restore; POST .../purge | Phân trang, xóa mềm, khôi phục, xóa vĩnh viễn |
| Báo cáo | POST /qa-attempts/:id/report-previews; POST .../reports | Cùng snapshot cho preview và xuất |
| Xu hướng | GET /qa-trends | Lọc tương thích định nghĩa, cursor và giới hạn truy vấn |
| Thư viện nội bộ | /organizations/:organizationId/knowledge/articles và tài nguyên con | Viết, sửa, đăng nội bộ, tệp, chia sẻ và quản lý bài; chi tiết mục 11 |
| Thư viện cộng đồng | GET /knowledge/community và /knowledge/community/:publicationId | Chỉ bản chia sẻ hiệu lực; định danh đăng nhập là đủ để đọc |
| Tra cứu | GET /knowledge/references với scope rõ ràng | Giới hạn/αβ dùng cùng quy tắc phạm vi với bài và công cụ |
| Tính nhanh | POST /biological/calculate; POST /biological/compare | Hàm không tạo hồ sơ/lịch sử bắt buộc |
| Lưu tùy chọn | POST /biological/worksheets | Lưu kết quả sau khi người dùng chọn lưu |

API dùng JSON nội bộ là bình thường; cấm đưa JSON thành phương thức thao tác của người dùng. Không truyền secret hoặc access token qua query string.

### 5.2. Hợp đồng operation tối thiểu

Mỗi operation ghi rõ: actor đã xác thực; scope; input/miền giá trị; precondition; thay đổi trong transaction; postcondition; idempotency; xung đột revision; side effect; timeout; lỗi có thể thử lại; cách phục hồi; thử nghiệm thành công và thất bại.

Upload hoàn tất không đồng nghĩa phân tích hoàn tất. HTTP nhận công việc dài trả trạng thái chờ và polling/subscription có giới hạn; tắt trang không hủy việc trừ khi người dùng chọn hủy.

### 5.3. Error/recovery record chuẩn

Lỗi máy gồm code, field_errors nếu có, retryable, correlation_id nội bộ; không gửi stack trace, SQL, token, DICOM header thô. UI ánh xạ sang thông báo và thao tác:

| HTTP/nhóm lỗi | Hành vi UI | Phục hồi |
| :--- | :--- | :--- |
| 401 / hết phiên | “Phiên đăng nhập đã hết hạn” | Làm mới phiên một lần; thất bại thì đăng nhập, giữ bản nháp không nhạy cảm đúng phạm vi |
| 403 / không thuộc đơn vị | “Bạn chưa tham gia đơn vị này” | Chọn đơn vị/lời mời; không gọi là lỗi mạng |
| 404 / không thấy | “Không tìm thấy nội dung” | Về lịch sử; không tiết lộ tài nguyên ngoài phạm vi |
| 409 / revision hoặc khóa chạy trùng khác dữ liệu | Nêu dữ liệu đã thay đổi | Tải mới, so sánh; không tự ghi đè |
| 413 / tệp quá lớn | Nêu giới hạn dung lượng | Đổi tệp; không lặp vô hạn |
| 415 / loại dữ liệu không hỗ trợ | Nêu loại bài/tệp được hỗ trợ | Chọn đúng tệp hoặc nhập số liệu |
| 422 / dữ liệu không hợp lệ | Lỗi theo trường và đơn vị | Giữ phần hợp lệ; sửa rồi tính lại |
| 429 / quá nhiều tác vụ | Nêu đang chờ hoặc thử sau | Backoff có giới hạn, không tạo thêm job |
| Timeout/502/503/504 | “Dịch vụ chưa phản hồi” | Cho thử lại, kiểm trạng thái run trước khi gửi mới |
| Phân tích không hội tụ/không tìm được đối tượng | Lý do theo bài, không có kết quả giả | Xem ảnh, chỉnh tham số có hỗ trợ, tạo run mới |
| PDF không dựng được/tệp chưa có | Giữ lựa chọn báo cáo | Thử lại cùng snapshot |
| Tài nguyên đã xóa | Nêu thùng rác nếu đúng scope | Khôi phục hoặc quay lại lịch sử |

Lỗi mới phải bổ sung vào danh mục và test hồi quy; không tuyên bố liệt kê hữu hạn là mọi lỗi có thể xảy ra.

## 6. Nhập số liệu và dữ liệu ảnh/liều

### 6.1. QA nhập tay

Field schema: số hữu hạn/boolean/enum/NA; đơn vị; số chữ số hiển thị; miền giá trị; bắt buộc; nguồn đo; công thức trong danh sách cho phép. Chấp nhận dấu phẩy thập phân ở giao diện vi, chuẩn hóa trước API; không tự hiểu dấu phân cách hàng nghìn mơ hồ.

Rule dùng toán tử có kiểu và đơn vị; không chạy JavaScript/Python/SQL từ nội dung người dùng. Khoảng đạt và cảnh báo phải có thứ tự nhất quán, định nghĩa dấu bằng, quy tắc thiếu dữ liệu và tổng hợp. Baseline bằng 0 không được dùng làm mẫu số sai lệch phần trăm.

Các công thức đo có tên/phiên bản: ví dụ sai lệch tuyệt đối, phần trăm so với chuẩn, trung bình, độ lệch chuẩn theo định nghĩa đã chọn. Độ phẳng/đối xứng không chỉ có một định nghĩa chung; phải chọn định nghĩa trước khi tính.

### 6.2. Upload và Input Manifest

Chọn vai trò tệp trước khi chạy: ảnh QA, liều tham chiếu, liều đo/đối chiếu, cấu trúc, ảnh giải phẫu. Tên mở rộng .dcm/.dicom không chứng minh nội dung hợp lệ.

Manifest nội bộ gồm hash, kích thước, loại thực, SOP/Study/Series/Frame of Reference UID khi có, modality, đơn vị, scaling, spacing, origin, orientation, grid, máy và quan hệ tham chiếu, phiên bản bộ đọc, validation. Không đưa manifest thô lên UI.

Giới hạn upload, số tệp, pixel/voxel, nén giải nén, thời gian parse và bộ nhớ phải được khai báo theo profile và kiểm trước/cả trong xử lý. Tệp lỗi hoặc nén không hỗ trợ trả lỗi rõ; không sửa tệp gốc.

RTDOSE phải dùng DoseUnits/DoseGridScaling và hình học đúng; không chỉ kiểm modality. Dữ liệu GY và RELATIVE là các ngữ nghĩa khác nhau; chuyển cGy từ định dạng đo cần ghi hệ số và xác nhận. Hướng dẫn nguồn: [DICOM RT Dose Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_C.8.8.3.html).

### 6.3. Hình học và thang đo

Mọi ảnh có hệ tọa độ gốc, orientation, phép biến đổi hiển thị và đơn vị. Xoay/lật khi xem không làm đổi kết quả phân tích. Chuyển pixel sang mm theo metadata hoặc hiệu chuẩn được nhập rõ; lưu vị trí mặt phẳng đo và cách chiếu về mặt phẳng đánh giá.

Ảnh chụp EPID và film quét có cách hiệu chuẩn khác nhau. Chỉ hỗ trợ ảnh PNG/TIFF khi profile chấp nhận và đủ DPI/scale/calibration; không coi mọi ảnh màn hình là dữ liệu đo.

CT không thay cho ảnh cổng chụp của Picket Fence. RTSTRUCT không thay cho dữ liệu đo Gamma. RTDOSE không phải ảnh grayscale chưa scaling. Dữ liệu cùng bệnh nhân nhưng khác Frame of Reference không tự được coi đã đăng ký.

## 7. Bộ phân tích QA ảnh và PSQA

### 7.1. Adapter chung

Hợp đồng adapter gồm `validate_inputs → prepare_supported_input → invoke_pylinac → map_results_data → build_overlay → summarize`. `prepare_supported_input` chỉ chuẩn hóa định dạng/đơn vị/hình học theo contract đã công bố; không thay thuật toán phân tích. `map_results_data` chỉ ánh xạ tên và cấu trúc; không tính lại metric mà pylinac đã trả. Kết quả chứa `metric_key`, `definition_version`, value, unit, calculability, suggested status, warnings, geometry, input/config snapshot và tài nguyên minh họa.

Pylinac là engine bắt buộc cho toàn bộ capability mà bản runtime đã khóa cung cấp. Việc kiểm dependency xác định pylinac chạy chung process hay trong `qa-image-worker`; không phải vòng tuyển chọn lại engine. Tài liệu chính thức hiện liệt kê 16 mô-đun chính và nhóm `contrib/One-Offs`; [trang PyPI](https://pypi.org/project/pylinac/) là nguồn gói phát hành, [tài liệu pylinac](https://pylinac.readthedocs.io/en/latest/) là nguồn API và [tài liệu contrib](https://pylinac.readthedocs.io/en/latest/contrib.html) là nguồn hai bài đóng góp.

Tại ngày 2026-09-12, PyPI công bố pylinac 3.47.0 và Python từ 3.10, trong khi trang tài liệu `latest` hiển thị 3.48.0. Mốc khóa runtime đầu tiên là wheel 3.47.0 cùng SHA-256 của wheel; bước P07-W02 phải xác minh cài/import/fixture trên runtime thực. Nếu dependency con chưa tương thích Python 3.14 hoặc footprint xung đột API, chạy `qa-image-worker` bằng phiên bản Python tương thích với pylinac; không thay pylinac bằng engine khác và không hạ runtime API.

RT-CONNECT dùng Anti-Corruption Layer để không lưu trực tiếp object/JSON riêng của pylinac:

- `PylinacAdapter` nhận input manifest + machine/test profile + điều chỉnh người dùng, gọi đúng class/`analyze` của registry và chuyển `results_data()` sang `AnalysisRun` chung.
- Adapter không tự tính lại metric pylinac. Các phép tính bổ sung chỉ được phép nếu là capability pylinac mức thấp được gọi rõ ràng và snapshot ghi đúng hàm/module/version.
- `engine_name=pylinac`, `pylinac_version`, wheel hash, adapter version, module/class, tham số analyze và hash input được lưu trong snapshot. Kết quả cũ không bị tính lại khi nâng phiên bản.
- Lỗi/thông báo của pylinac được ánh xạ sang error code ổn định và tiếng Việt; stack trace chỉ ở log đã khử dữ liệu.
- PDF/PNG do pylinac tạo có thể dùng cho chẩn đoán phát triển, không dùng làm báo cáo chính. Renderer RT-CONNECT dựng từ structured metrics và overlay đã chuẩn hóa.
- `PylinacCapabilityRegistry` phải bao phủ mọi class/capability công khai thuộc 16 họ mô-đun chính và các bài QA `contrib/One-Offs` trong wheel đã khóa. Build fail nếu inventory runtime khác registry mà chưa có quyết định migration.
- Capability đã có trong pylinac nhưng adapter/UI chưa xong mang trạng thái kỹ thuật `NOT_IMPLEMENTED`; nó không biến mất khỏi phạm vi và P7 không được đóng.

### 7.2. Ma trận engine bắt buộc

Ma trận chi tiết class/biến thể/đầu vào/UI nằm ở [danh mục QA pylinac](docs/pylinac-qa-catalog.md). Registry kỹ thuật tối thiểu phải có đủ 16 họ chính sau và mọi bài QA public trong `contrib/One-Offs`:

| Capability family | Class/biến thể bắt buộc trong registry phiên bản 3.47.0 | Loại giao diện |
| :--- | :--- | :--- |
| Calibration | `TG51Photon`, `TG51ElectronLegacy`, `TG51ElectronModern`, `TRS398Photon`, `TRS398Electron` | Form số đo theo protocol; bảng hệ số/dose |
| Starshot | `Starshot` | Canvas chọn tâm/radius và tham số analyze |
| VMAT | `DRGS`, `DRMLC`, `DRCS` | Cặp ảnh, ROI/segment/tolerance |
| CatPhan | `CatPhan503`, `CatPhan504`, `CatPhan600`, `CatPhan604` | Chuỗi ảnh, origin slice, module/ROI adjustments |
| ACR | `ACRCT`, `ACRMRILarge`, `ACRMRIMedium` | Chuỗi ảnh, slice/module/ROI adjustments |
| Cheese | `TomoCheese`, `CIRS062M` | Chuỗi ảnh, density/HU ROI |
| GE Helios | `GEHeliosCTDaily` | Chuỗi ảnh, module/ROI controls |
| Quart | `QuartDVT`; alias/biến thể HyperSight nếu còn public trong wheel | Chuỗi ảnh, origin/module/ROI controls |
| Log Analyzer | Dynalog và Trajectory Log 2.1/3.0/4.0 qua loader công khai | Upload log, chọn trục/fluence/Gamma log |
| Picket Fence | `PicketFence` + MLC/profile public | Canvas leaf/picket, tolerance/crop/orientation/sag |
| Winston–Lutz | `WinstonLutz`, `WinstonLutz2D` khi là kết quả con công khai | Bộ ảnh, góc, BB/field, axis plots |
| Winston–Lutz Multi-Target | `WinstonLutzMultiTargetMultiField` | Cấu hình BB/field có form, không raw config |
| Planar Imaging | Leeds/Leeds Blue, SI QC-3/QC-kV, Las Vegas/Elekta, Doselab MC2 MV/kV, SNC MV/MV12510/kV, PTW EPID QC, IBA Primus A, SI FC-2, IMT L-RAD, Doselab RLf, IsoAlign, SNC FSQA, ACR Digital Mammography | Canvas center/angle/size/ROI/SSD/invert theo class |
| Field Profile Analysis | `FieldProfileAnalysis` + metrics profile public | Click vị trí profile, centering/width/edge/normalization/metrics |
| Field Analysis | `FieldAnalysis` legacy | UI tương thích; bài mới mặc định dùng Field Profile Analysis |
| Nuclear | `MaxCountRate`, `PlanarUniformity`, `CenterOfRotation`, `TomographicResolution`, `SimpleSensitivity`, `FourBarResolution`, `QuadrantResolution`, `TomographicUniformity`, `TomographicContrast` | Form riêng từng phép thử, frame/ROI/threshold/scale/activity |
| One-Offs/Contrib QA | `QuasarLightRadScaling`, `JawOrthogonality` | Quasar: invert/FWXM/BB-edge threshold; Jaw: ảnh trường và bốn góc/cạnh. Gắn nhãn nguồn contrib và contract test riêng |

`Core`, `Image Generator` và `Plan Generator` không là bài QA độc lập; chúng hỗ trợ input/fixture/biến đổi. `One-Offs` có hai bài QA công khai nên phải được ánh xạ, nhưng metadata `source_tier=PYLINAC_CONTRIB` và cảnh báo tương thích không được bỏ. Gamma 1D/2D là capability mức thấp dùng trong P8. Field Analysis vẫn được đưa vào registry vì người dùng yêu cầu toàn bộ danh mục, nhưng UI nêu đây là mô-đun cũ và dùng Field Profile Analysis làm mặc định mới theo cảnh báo deprecation của tài liệu pylinac.

Calibration phải lưu đúng protocol implementation. Tài liệu pylinac hiện cảnh báo chưa tích hợp các thay đổi liên quan của revision TRS-398 năm 2024; UI/result không được gắn nhãn “TRS-398 2024” nếu runtime chưa thực hiện revision đó.

### 7.3. Gamma

Run PSQA mới dùng `pylinac.profile.gamma_1d` hoặc `pylinac.image.gamma_2d`. RTDOSE tham chiếu và measurement/comparison là hai vai trò; nhiều RTDOSE phải chọn rõ. Bộ đọc định dạng đo có registry phiên bản; import CSV nếu hỗ trợ dùng wizard ghép cột/đơn vị và xem trước bảng, không bắt sửa JSON.

Schema giao diện cơ bản:

| Trường UI | Trường nội bộ | Quy tắc |
| :--- | :--- | :--- |
| Chênh lệch liều (%) | `dose_difference_percent` | Số hữu hạn >0; truyền vào `dose_to_agreement`; không cho nhập mơ hồ Gy/% trong cùng ô |
| Khoảng cách DTA (mm) | `distance_to_agreement_mm` | Số hữu hạn >0; hiển thị mm cho người dùng |
| Chuẩn hóa | `global_dose` | Toàn cục/cục bộ; giá trị local zero phải được xử lý theo contract pylinac và ghi warning/error |
| Ngưỡng liều thấp (%) | `dose_threshold_percent` | Miền profile công bố; số điểm bị loại và mẫu số phải hiển thị |
| Gamma tối đa | `gamma_cap_value` | Nâng cao; không được dùng để biến điểm fail thành pass |
| Ngưỡng tỷ lệ đạt (%) | `pass_rate_target_percent` | Rule đánh giá RT-CONNECT, không phải input thay đổi map Gamma |

Pylinac `gamma_2d` nhận DTA theo số phần tử/pixel, không nhận trực tiếp mm. `PylinacPsqaAdapter` phải:

1. kiểm hai dataset có cùng đại lượng, orientation và vùng chồng lấp;
2. resample về `analysis_spacing_mm` được profile công bố;
3. tính `distance_elements = distance_to_agreement_mm / analysis_spacing_mm`;
4. chỉ gọi pylinac khi giá trị này biểu diễn được bằng số phần tử mà API nhận trong tolerance đã định; nếu không thì trả `GAMMA_DTA_GRID_INCOMPATIBLE`, không làm tròn âm thầm;
5. lưu spacing trước/sau, transform/resampling, DTA mm và giá trị phần tử đã truyền vào snapshot.

Lưu normalization, threshold denominator, per-field/composite, detector/phantom, thời điểm đo, transform, resampling và phạm vi chồng lấp. Không tự đăng ký dịch ảnh để làm đẹp tỷ lệ; mọi transform phải được người dùng chọn hoặc profile khai báo và hiện thông tin.

Tài liệu pylinac hiện công bố Gamma 1D và 2D, không công bố Gamma 3D. Do đó:

- `PylinacCapabilityRegistry` chỉ quảng bá `GAMMA_1D` và `GAMMA_2D` cho run mới;
- API từ chối yêu cầu 3D mới bằng `PYLINAC_GAMMA_3D_UNAVAILABLE`, không fallback âm thầm sang engine cũ;
- kết quả Gamma 3D cũ của `gamma-nd-p8.2` vẫn đọc/xuất được với provenance engine cũ và không tự tính lại;
- DVH tiếp tục ở P17 như capability RT-CONNECT riêng, không gắn nhãn pylinac.

### 7.4. Giao diện tham số và thao tác tay

Web không gửi tọa độ màn hình trực tiếp. Canvas lưu transform giữa ảnh gốc và viewport; click/drag được đổi về tọa độ ảnh gốc hoặc hệ tọa độ mà adapter công bố. Zoom, pan, rotate hiển thị không làm đổi kết quả khi người dùng chưa xác nhận điều chỉnh.

Mỗi capability khai báo `ui_parameter_schema` có nhãn tiếng Việt, kiểu, đơn vị, miền, default từ profile máy, mức cơ bản/nâng cao và ánh xạ chính xác sang tham số pylinac. Không tạo form chung bằng cách đổ JSON schema thô lên màn hình.

Các control bắt buộc gồm:

- Starshot: chọn/kéo `start_point`, radius, min peak height, tolerance, FWHM, recursive và invert khi class hỗ trợ;
- Field Profile/Field Analysis: centering manual/beam/geometric, click `position`, x/y width, normalization, edge type, metrics/protocol;
- Planar Imaging: center/angle/size override, SSD, x/y/angle adjustment, ROI size/scaling, invert theo class;
- CatPhan/ACR/Cheese/Helios/Quart: origin slice, module/lát, tâm/x/y/góc, ROI/scale và giá trị tham chiếu class cho phép;
- Picket Fence, Winston–Lutz, multi-target, VMAT và Nuclear: đúng control được liệt kê trong catalog/registry, không dùng raw file cấu hình.

Phân tích tự động là run thứ nhất. Nếu người dùng chỉnh tâm/ROI/profile/góc/scale rồi chạy lại, tạo run mới trỏ cùng input hash và lưu parameter diff; không overwrite run tự động. Overlay server trả primitive có hệ tọa độ và style semantic; frontend dựng thống nhất và PDF dùng cùng primitive.

### 7.5. Tác vụ, thử lại và tính bền vững

Trạng thái nội bộ: QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED. Kết luận QA là trường khác. Tác vụ có timeout, heartbeat, cancellation, retry hữu hạn, deduplication và lưu lỗi. Outbox/hàng đợi hiện có được tái sử dụng.

Trước ghi kết quả kiểm tra attempt chưa bị xóa, scope và revision phù hợp. Job chạy chậm sau khi người dùng xóa không được tạo lại bài hoặc điểm xu hướng. Nếu upload hoặc output ghi dở, có tiến trình dọn orphan an toàn và có thể thử lại.

## 8. Kết quả, lịch sử, xóa và báo cáo

### 8.1. Lưu kết quả và đánh giá

Run thành công chụp input/config/definition version. Sửa số liệu tạo run mới, không ghi đè run thành công. AssessmentRevision lưu user conclusion riêng; mọi thành viên đều dùng cùng API. Thay nhãn báo cáo không thay metric key hoặc phép tính.

Run thất bại không có giá trị giả. Người dùng có thể lưu bản nhập/nhận xét mà không có run thành công; PDF nếu chọn chỉ xuất đúng nội dung hiện có.

### 8.2. Xóa mềm, khôi phục và xóa vĩnh viễn

DELETE đánh dấu deleted_at và ghi deletion record trong transaction, đồng thời tạo sự kiện loại khỏi trend/search. Xóa nhiều có danh sách kết quả từng mục và không báo thành công toàn bộ khi một mục xung đột.

Restore bỏ dấu xóa một lần và rebuild projection idempotent. Nếu máy/thư mục cũ ngừng hoạt động, vẫn khôi phục được bài lịch sử; không tự kích hoạt lại máy.

Purge hiển thị trước phạm vi run/report/tệp, yêu cầu xác nhận trực tiếp. Kiểm tra references, hủy job, bỏ quyền cấp signed URL mới, dọn dữ liệu/tệp theo tiến trình retry; chỉ báo xóa vĩnh viễn xong khi phần bắt buộc đã dọn. Signed URL đã cấp có thể còn hiệu lực tới hết TTL; không hứa thu hồi tức thì nếu hạ tầng không hỗ trợ. PDF đã tải ra ngoài không thu hồi được.

Giữ tombstone tối thiểu cho sự kiện và chống retry tái tạo; không giữ toàn bộ nội dung đã purge trong audit. Backup theo lịch có chính sách lưu giữ riêng được công bố; restore backup phải áp dụng deletion ledger để tránh phục hồi dữ liệu đã xóa không có chủ đích.

### 8.3. Overlay ảnh

Lưu ảnh gốc và lớp hình học độc lập: đường, điểm, vòng tròn, vector, nhãn, hệ tọa độ, thang đo. UI và renderer dùng chung dữ liệu, không chụp màn hình giả làm kết quả.

Starshot hỗ trợ ảnh + spokes + center + circle + chú giải; PDF cho chọn từng nhóm lớp. Với WL/PF tương tự cho bi/trường hoặc lá/vạch. Kiểm thử ảnh xoay/lật/crop, zoom và tỷ lệ PDF không lệch tọa độ.

### 8.4. Bộ dựng PDF toàn quyền bố cục

Report layout có danh sách khối, dòng/cột hiển thị, label override, precision, figure layer selection, notes, logo, header/footer, page settings. Mọi khối đều có thể ẩn; không có canonical block bắt buộc.

Snapshot gồm run/assessment/source version, layout và locale; renderer không truy bảng kết quả mới nhất khi dựng lại. Preview và export dùng cùng layout engine, font và snapshot. Có thể dựng lại từ snapshot hoặc tải nguyên tệp cũ; phiên bản mới của template không thay bản PDF đã phát hành.

Không chạy HTML/script/template code từ người dùng; escape nội dung và hạn chế tài nguyên ảnh. Tệp không chứa JSON/raw IDs dù dữ liệu snapshot máy có các trường đó. Chữ tiếng Việt, ký hiệu α/β, công thức, bảng qua trang, hình có chú giải đều được kiểm.

Ẩn mọi khối dẫn đến lỗi chọn nội dung; ảnh đang xử lý không được thay bằng hình giả. Bấm xuất nhiều lần cùng snapshot/layout/renderer dùng cùng namespace idempotency; thay layout hoặc renderer phải tạo bản tương ứng.

## 9. Xu hướng

Lọc theo organization, máy, bài, metric_key + definition_version, đơn vị, kỹ thuật đo/profile và khoảng ngày. Tách series khi đổi định nghĩa hoặc điều kiện đo không tương thích; nếu hiển thị cùng đồ thị phải có chú giải.

Giá trị số lấy từ run được chọn; assessment trend lấy từ đánh giá người dùng. Chọn điểm mở đúng kết quả. Baseline/ngưỡng và bảo trì có phiên bản/thời điểm; không thay dữ liệu lịch sử khi sửa baseline.

Cursor pagination và giới hạn số điểm; downsampling có metadata và không làm mất điểm cực trị cần xem. Xóa/restore/reanalysis/update assessment cập nhật projection idempotent; kiểm query budget. Không có điểm thì trả series rỗng, không trả giá trị 0 giả.

## 10. Công cụ sinh học

### 10.1. Hợp đồng tính không cần hồ sơ

UI có một route/container và sáu panel. Endpoint tính nhận cấu trúc typed theo tool, trả kết quả/đơn vị/giả định/source references, không bắt worksheet_id/case_id/organization scenario trước khi tính. Vẫn yêu cầu phiên hợp lệ khi ứng dụng đang ở chế độ thành viên.

Không ghi lịch sử cho mỗi lần nhấn phím. Tính bằng nút hoặc debounce hợp lý; lưu khi người dùng chọn. Dữ liệu nháp trong phiên được tách theo đơn vị, xóa khi đăng xuất và không đặt trong URL.

### 10.2. BED/EQD2 và đồ thị

Đặt a = α/β > 0 (Gy), n nguyên dương, D ≥ 0 (Gy), d = D/n.

- BED = n·d·(1 + d/a).
- EQD2 = BED / (1 + 2/a).
- Nhiều đoạn phân liều: tính BED từng đoạn với cùng mô hình/đích rồi cộng; không dùng liều mỗi buổi trung bình nếu các đoạn khác nhau.
- Giữ n khi vẽ theo D: BED(D) = D·(1 + D/(n·a)).
- Giữ d: BED(D) = D·(1 + d/a), n = D/d; chỉ các điểm có n nguyên là phác đồ rời rạc hợp lệ.
- EQD2 theo D áp dụng cùng mẫu số; miền D không âm, giới hạn số điểm và nhãn đơn vị.

Mô hình LQ và ý nghĩa α/β tham khảo [tài liệu đào tạo sinh học bức xạ IAEA](https://www-pub.iaea.org/MTCD/Publications/PDF/TCS-42_web.pdf). Các công thức trên là hợp đồng tính cơ bản, không lựa chọn thông số điều trị cho bệnh nhân.

Bộ số kiểm thử toán học, không phải phác đồ khuyến nghị: D=60, n=30, a=10 → d=2, BED=72, EQD2=60; D=50, n=25, a=3 → BED=83.333333…, EQD2=50. a=0, n=0, n không nguyên, NaN/Infinity hoặc liều âm trả lỗi.

### 10.3. So sánh

Tính A và B độc lập bằng cùng engine. Chênh lệch tuyệt đối và phần trăm chỉ tính khi mẫu số khác 0; B=0 thì phần trăm phải có định nghĩa/không khả dụng, không Infinity. α/β chung cho cùng đích là mặc định; nếu khác, không xuất kết luận tương đương đơn giản.

### 10.4. Tái xạ

Mỗi course có dose_metric, vị trí/cơ quan/đích đánh giá, D/n hoặc các đoạn, a, ngày tùy chọn, nguồn. Chỉ tổng hợp trực tiếp khi cùng a, mô hình và ngữ nghĩa tương thích; dữ liệu không tương thích hiển thị từng đợt, không tạo tổng có vẻ chính xác.

Chế độ cơ bản: BED_sum = Σ BED_i, EQD2_sum = BED_sum/(1+2/a). Đây là tổng vô hướng theo giả định đã chọn, không phải spatial accumulation.

Tùy chọn hồi phục: người dùng nhập r_i ∈ [0,1] cho từng đợt trước; residual_BED = Σ(1-r_i)·BED_i. Đợt mới không áp dụng hồi phục của đợt cũ. Mặc định r_i=0; thời gian giữa đợt không tự sinh r_i. Hiển thị cả tổng chưa hiệu chỉnh và tổng theo giả định.

Không dùng giới hạn từ thư viện khi sai phân liều, metric hoặc bối cảnh; không tính “liều còn được phép chiếu” từ một Dmax khác vị trí mà không nêu giả định.

### 10.5. Bù buổi chiếu

Ghi riêng planned schedule, delivered segments, remaining candidate. BED_delivered tính từ số buổi/liều thực tế, không từ phần trăm hoàn thành. So sánh tổng đề xuất với planned.

Giải một ẩn theo mục tiêu BED_rem và m buổi còn lại: m·d·(1+d/a)=BED_rem. Nghiệm không âm d=(-a+sqrt(a²+4a·BED_rem/m))/2 khi a>0, m nguyên dương, BED_rem≥0. Không tự làm tròn lên để khuyến nghị liều; hiển thị nghiệm và sai khác khi người dùng nhập giá trị làm tròn.

Nếu có hiệu chỉnh thời gian phải có model id, đơn vị, K/Tk hoặc tham số tương ứng và nguồn, kiểm không áp dụng hai lần. Thiếu thông số thì chỉ chạy mô hình cơ bản và ghi “Chưa tính ảnh hưởng thời gian”. Không dùng mặc định K/Tk từ tên bệnh.

### 10.6. Nguồn α/β và giới hạn liều

Nguồn được gắn reference_version_id; dữ liệu hiển thị có tên tác giả/tài liệu, năm và trang/mục. Người dùng chọn một giá trị từ nhiều nguồn hoặc tự nhập. Một range không tự lấy trung điểm nếu chưa chọn.

Dose constraint biểu diễn metric có tham số: D0.03cc khác Dmax; D95% khác V95%; %Rx khác Gy. Bảng tham khảo dùng một nguồn với thư viện; bộ nhớ đệm tách phạm vi/đơn vị/bản chia sẻ/access_epoch/phiên bản/bối cảnh/ngôn ngữ. Kiểm quyền hiện thời trước khi trả dữ liệu đã lưu đệm; cập nhật hoặc thu hồi phải có hiệu lực với yêu cầu mới theo mục 11.

## 11. Thư viện kiến thức

### 11.1. Hai phạm vi đọc và quyền sở hữu

`scope=organization` yêu cầu phiên hợp lệ và thành viên trong đơn vị đang chọn; `scope=community` chỉ yêu cầu phiên hợp lệ, gồm người chưa có đơn vị. Các tuyến cộng đồng phải nằm ngoài thành phần giao diện chặn người thiếu đơn vị. Viết bài cần chọn một đơn vị mà người viết đang là thành viên.

Nhóm nội dung `QA|TREATMENT` độc lập với phạm vi đọc; bảng α/β, giới hạn và nguồn là nội dung con. `owner_organization_id` lấy từ phiên và tuyến ghi đã kiểm tra. `source_hospital_name` chỉ là thông tin xuất xứ, không cấp quyền. Tất cả thành viên đang hoạt động trong đơn vị chủ sở hữu sửa, chia sẻ, lưu trữ, xóa và khôi phục ngang nhau.

Các hàm đọc nội bộ và cộng đồng riêng biệt. Cộng đồng không được tuần tự hóa đối tượng ORM nguồn rồi chỉ bỏ vài trường sau đó. Định nghĩa kiểu trả về riêng cho `CommunityArticle`, danh sách tệp và trích đoạn; không có bản nháp, nhật ký nội bộ, khóa lưu trữ hoặc email cá nhân. Xử lý tìm kiếm, bộ lọc, số lượng, ảnh thu nhỏ, so sánh, bảng α/β, tải tệp và lịch sử đều dùng cùng chính sách này.

### 11.2. Mô hình bài, bản sửa và bản chia sẻ

| Thực thể | Dữ liệu tối thiểu | Ràng buộc |
| :--- | :--- | :--- |
| KnowledgeArticle | chủ sở hữu, nhóm, tên ổn định, bản nháp hiện tại, bản nội bộ hiện tại, trạng thái, revision | Khóa theo đơn vị; trạng thái ACTIVE/ARCHIVED/TRASHED; tên hiển thị không làm khóa quyền |
| KnowledgeArticleRevision | số phiên bản, tiêu đề, tóm tắt, nội dung trình soạn, văn bản tìm kiếm, nguồn, người sửa, thời điểm | Phiên bản đã đăng bất biến; bản nháp có expected_revision; không trả lịch sử nội bộ ra cộng đồng |
| KnowledgePublication | khóa chia sẻ ổn định, chủ sở hữu, current_snapshot_id, access_epoch, withdrawn_at | Chỉ có một bản đang đọc cho mỗi bài; thu hồi tăng access_epoch trong cùng giao dịch |
| KnowledgePublicationSnapshot | nội dung chia sẻ, nguồn/bối cảnh chia sẻ, source_revision_id nội bộ, attachment_manifest | Nội dung độc lập; không tự lấy bản nguồn mới nhất; không chứa tệp/hình chưa chọn |
| KnowledgeAsset | chủ sở hữu, loại tệp, kích thước, hash nội bộ, storage_key, scan_status, extraction_status | Đối tượng riêng tư; không đặt bucket public; không khử trùng lặp xuyên đơn vị để lộ sự tồn tại |
| KnowledgeRevisionAsset / PublicationAsset | quan hệ phiên bản và tệp, thứ tự, chú thích, trang | Tham chiếu nội bộ và danh sách tệp được chia sẻ độc lập |
| KnowledgeBookmark | identity_id, loại tham chiếu, khóa bài/bản chia sẻ | Duy nhất theo người/đích; mỗi lần xem kiểm quyền lại, không lưu bản sao nội dung vào dấu trang |
| KnowledgeReference | phiên bản nguồn, bệnh viện/bệnh cảnh, liều/αβ có kiểu, trích dẫn/trang | P11 tạo hợp đồng cơ sở; P16 hoàn thiện bảng/phác đồ; phạm vi kế thừa bài/bản chia sẻ |

Lịch sử phép tính được phép giữ giá trị và trích dẫn đã sử dụng theo bản chụp hiện có. Dấu trang, bộ nhớ đệm và liên kết bài không được dùng bản chụp đó để mở lại toàn văn nguồn đã thu hồi.

Mỗi lần đăng/cập nhật dùng idempotency key cùng expected_revision. Giao dịch khóa hàng bài và bản chia sẻ; ghi bản chụp, danh sách tệp, con trỏ hiện tại và sự kiện cập nhật chỉ mục trong cùng giao dịch. Cùng khóa/cùng nội dung trả cùng kết quả; khác nội dung trả 409. Nếu chuẩn bị tệp thất bại thì giữ bản chia sẻ cũ, không công bố một phần.

### 11.3. Hợp đồng thao tác và tuyến

Tiền tố `/api/v1`. Ký hiệu `/organizations/:organizationId/knowledge/articles/:articleId` viết gọn thành `/org-article` trong bảng này; không phải đường dẫn thực cần tạo.

| Thao tác | Tuyến thực hoặc hậu tố | Điều kiện và kết quả |
| :--- | :--- | :--- |
| Danh sách nội bộ/tạo bài | GET/POST /organizations/:organizationId/knowledge/articles | Thành viên đơn vị; tạo bản nháp nội bộ, không có tác động cộng đồng |
| Đọc/sửa nháp | GET /org-article; PATCH /org-article/draft | Kiểm phạm vi từ truy vấn đầu; expected_revision để chống ghi đè |
| Phiên bản và phục hồi | GET /org-article/revisions; POST /org-article/revisions/:revisionId/restore | Chỉ đơn vị chủ sở hữu; phục hồi tạo nháp mới |
| Đăng nội bộ | POST /org-article/publish-internal | Chốt bản sửa làm bản nội bộ hiện tại |
| Xem trước chia sẻ | POST /org-article/publication-preview | Nhận phiên bản, danh sách tệp được chọn; kiểm hình/trích dẫn không dẫn tệp riêng |
| Đăng/cập nhật cộng đồng | POST /org-article/publications | Giao dịch chốt bản chia sẻ; không tự chia sẻ tệp mới |
| Thu hồi | POST /org-article/publication/withdraw | Tăng access_epoch, vô hiệu hóa truy cập mới đồng bộ, cập nhật chỉ mục |
| Lưu trữ/xóa/khôi phục | POST /org-article/archive; DELETE /org-article; POST /org-article/restore | Thu hồi bản chia sẻ khi lưu trữ/xóa; khôi phục nội bộ |
| Dọn vĩnh viễn | POST /org-article/purge | Chỉ TRASHED, kiểm tham chiếu trước khi dọn tệp; lặp yêu cầu không dọn nhầm |
| Đọc cộng đồng | GET /knowledge/community; GET /knowledge/community/:publicationId | Phiên hợp lệ, bản chia sẻ còn hiệu lực; không cần đơn vị |
| Khởi tạo tải tệp | POST /org-article/assets/uploads | Kiểm đơn vị/bản nháp/giới hạn; cấp phiên tải riêng cho tệp, không đổi phạm vi bài |
| Hoàn tất tải | POST /org-article/assets/uploads/:uploadId/complete | Đối chiếu kích thước/hash/loại thực tế; gọi lặp không nhân bản tệp; chỉ đính kèm khi hợp lệ |
| Trạng thái và thử trích chữ lại | GET /org-article/assets/:assetId; POST /org-article/assets/:assetId/extraction-retry | Trạng thái theo tệp; tác vụ thử lại có giới hạn, không tải lại PDF khi chỉ lỗi trích chữ |
| Gỡ tệp khỏi nháp | DELETE /org-article/draft/assets/:assetId | expected_revision; chỉ gỡ quan hệ nháp, không xóa tệp của bản đã chia sẻ/phiên bản cũ |
| Tệp nội bộ | GET /org-article/assets/:assetId/content | Kiểm quan hệ tệp–phiên bản–đơn vị |
| Tệp cộng đồng | GET /knowledge/community/:publicationId/assets/:assetId/content | Kiểm manifest và access_epoch; không dùng quyền nội bộ của trình duyệt để đoán tệp |
| Dấu trang | GET/POST /me/knowledge-bookmarks; DELETE /me/knowledge-bookmarks/:bookmarkId | Chỉ người sở hữu; tài nguyên không đọc được trả nhãn chung |
| Tìm nguồn số liệu | GET /knowledge/references?scope=... | Cùng ràng buộc truy cập, phiên bản/bệnh viện/bối cảnh bắt buộc khi chọn |

Lỗi 401 là hết phiên. Yêu cầu ngoài phạm vi tài nguyên nhận 404 không tiết lộ tên. 409 là bản đã thay đổi, đăng lặp khác nội dung hoặc bài đã bị thu hồi. 413 là quá dung lượng, 415 là không đúng loại tệp, 422 là dữ liệu/quan hệ tệp không hợp lệ, 429/503 có thời gian thử lại phù hợp. Thông báo người dùng đều bằng tiếng Việt.

### 11.4. Soạn bài và tự lưu

Trình soạn trực quan hỗ trợ đề mục, đoạn, đậm/nghiêng, danh sách, bảng, hình/chú thích, công thức và liên kết nguồn. Dữ liệu cấu trúc chỉ ở bên trong. Chọn thành phần biên tập tương thích React hiện tại khi triển khai P11; không thêm dịch vụ soạn thảo trả phí.

API làm sạch nội dung theo tập phần tử/thuộc tính cho phép; bỏ script, handler, iframe và liên kết không an toàn. Ảnh trong bài là tài nguyên do ứng dụng quản lý; nguồn URL bên ngoài chỉ hiện liên kết, không tự tải phía máy chủ. Điều này áp dụng cả nội dung dán từ phần mềm soạn văn bản.

Tự lưu sau 2 giây không gõ và khi rời trường; nút Lưu dùng cùng luồng. Mỗi nháp có revision; một người sửa trong hai thẻ hoặc hai đồng nghiệp cùng sửa nhận 409, hiển thị bản của mình và bản trên máy chủ để chọn tiếp tục. Không cần đồng biên tập thời gian thực trong đợt này.

Nếu mất mạng, giữ nội dung đang gõ trong bộ nhớ trang và nêu “Chưa lưu được”; cho thử lại, ngăn điều hướng âm thầm mất phần chưa lưu. Bản đã được máy chủ xác nhận mở lại được sau khi đăng nhập. Không hứa khôi phục phần chưa từng lưu khi trình duyệt đóng đột ngột. Xóa bộ nhớ của đơn vị cũ khi đổi đơn vị/đăng xuất sau khi đã xử lý phần chưa lưu.

Đọc bài cộng đồng đang sửa chỉ thấy snapshot hiện tại. Xem trước cộng đồng dùng đúng bộ ánh xạ sẽ đăng, không lấy bản đọc nội bộ rồi che tệp bằng CSS.

### 11.5. Tệp PDF, ảnh và chỉ mục nội dung

Luồng tệp riêng cho thư viện: đăng ký tải → kiểm dung lượng/loại → tải đối tượng riêng tư → xác minh nội dung và hash → sẵn sàng đính kèm → trích văn bản/hình thu nhỏ. Mặc định PDF tối đa 50 MiB/tệp, ảnh PNG/JPEG 10 MiB, tối đa 20 tệp/bài và 200 MiB/bài; giới hạn được cấu hình phía máy chủ và trả về biểu mẫu. Không nhận DICOM qua thư viện kiến thức.

Kiểm chữ ký tệp thực, PDF rỗng/hỏng/mã hóa, ảnh vượt giới hạn pixel và phần nhúng chủ động. PDF có mật khẩu trả lỗi để người dùng chuẩn bị bản đọc được; PDF là ảnh vẫn có thể xem/tải với `extraction_status=NO_TEXT`. Trích văn bản không thành công không xóa PDF hợp lệ. Tác vụ trích tối đa số trang/tài nguyên theo cấu hình, có hủy/thử lại và không làm nghẽn tác vụ QA.

Trình đọc PDF có thanh công cụ tiếng Việt, số trang, phóng to, tìm chữ khi có lớp văn bản; nhận dạng chữ tự động chưa là điều kiện đóng P11. Bảng liều/αβ phải được người dùng nhập hoặc đối chiếu qua biểu mẫu, không tự chuyển kết quả nhận dạng thành số liệu có hiệu lực.

Tệp gốc, hình thu nhỏ và văn bản trích đều là dữ liệu cần kiểm phạm vi. Trình đọc dùng tuyến API có xác thực, hỗ trợ Range khi PDF cần. Không trả URL S3 dùng được ngoài kiểm soát vào HTML/bản cộng đồng; máy chủ có thể dùng URL ký ngắn hạn nội bộ để lấy đối tượng. Phản hồi bài/tệp dùng `Cache-Control: private, no-store`, không ghi nội dung vào bộ nhớ đệm công cộng hoặc bộ lưu ngoại tuyến.

Thu hồi chặn yêu cầu đọc/tải mới ngay sau khi giao dịch hoàn tất, kể cả Range tiếp theo; luồng truyền đang diễn ra kiểm hủy theo thiết kế phục vụ tệp. Không cam kết thu hồi các byte đã truyền hoặc bản người dùng đã tải xong. Kiểm quyền lại ngay trước khi bắt đầu trả nội dung; tác vụ nền cũ phải kiểm epoch trước khi ghi kết quả khả kiến.

### 11.6. Tìm kiếm có dấu/không dấu

Dùng PostgreSQL hiện có: cột văn bản chuẩn hóa có dấu/không dấu, tìm toàn văn với cấu hình phù hợp và `pg_trgm` khi cần tên gần đúng. `unaccent` loại dấu, `pg_trgm` hỗ trợ độ tương tự và chỉ mục tìm kiếm; cần kiểm riêng đ/Đ, Unicode tổ hợp và ký hiệu liều. Không gọi khả năng này là phân tích ngôn ngữ tiếng Việt hoàn chỉnh. Nguồn kỹ thuật: [unaccent](https://www.postgresql.org/docs/current/unaccent.html), [pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html).

Ưu tiên tiêu đề → từ khóa/chủ đề → tóm tắt → nội dung bài → tên/văn bản PDF; trọng số công bố và có bộ ví dụ. Trả đoạn trích kèm trang PDF nếu chỉ mục có vị trí trang. Tìm trong đúng phạm vi trước khi tính tổng, nhóm, gợi ý hoặc xếp hạng; cộng đồng chỉ dùng snapshot đang hiệu lực. Không đưa bản nháp mới vào chỉ mục cộng đồng.

Chỉ mục lưu source revision và access_epoch; truy vấn vẫn nối kiểm bản chia sẻ hiện tại nên hàng cũ trong hàng đợi không gây rò nội dung. Hệ thống ghi sự kiện trong giao dịch và tác vụ cập nhật chỉ mục xử lý lặp an toàn. Sau lưu có thể tìm ngay bằng tiêu đề trên bảng chính; trích văn bản nền hiện trạng thái đang xử lý.

Phân trang 20 mục, tối đa 100; câu tìm tối đa 200 ký tự; chống yêu cầu liên tục bằng khoảng chờ 300 ms hoặc nút Tìm kiếm. Khóa lưu bộ nhớ theo người/đơn vị/phạm vi/bộ lọc/phiên bản, hủy yêu cầu đang chờ khi đổi phạm vi. Mục tiêu đo P95 ≤ 2 giây với 10.000 bài và 100.000 trang trích trên môi trường thử ghi rõ; không suy thành cam kết mọi quy mô.

### 11.7. Phác đồ, nguồn và liên kết công cụ

`TreatmentContext` giữ bệnh, giai đoạn/nguy cơ, tình trạng sau mổ, mục đích, bệnh viện nguồn, kỹ thuật, phân liều và phối hợp điều trị. P11 tạo cấu trúc nguồn cơ sở và dữ liệu có kiểu để P13/P15 sử dụng mà không phụ thuộc mã P16 chưa làm. P16 hoàn thiện biên tập phác đồ, các đoạn tăng liều/SIB, bảng cơ quan và so sánh nguồn.

HI/CI có tên định nghĩa, công thức, tham số, đơn vị và nguồn. Không xem HI=(D2-D98)/D50 và HI=D5/D95 là cùng một định nghĩa; không gộp CI theo RTOG với Paddick. Không tạo ngưỡng HI/CI, α/β hoặc 105%/107% không nguồn.

Nguồn số liệu từ bài nội bộ chỉ được dùng trong đơn vị đó. Nguồn từ cộng đồng phải nằm trong snapshot có hiệu lực. Tạo phép tính mới kiểm quyền lại, lưu giá trị và trích dẫn đã chọn. Nguồn bị thu hồi không làm thay đổi phép tính đã lưu và không cấp quyền đọc toàn văn nguồn từ phép tính đó.

Migrate dữ liệu thư viện/rule cũ có bảng đối chiếu: phần thực thi thuộc cài đặt bài P7, phần hướng dẫn thuộc bài đọc. Mọi bài/tệp cũ mặc định nội bộ. Trạng thái cũ `PUBLISHED` chỉ có nghĩa đã đăng nội bộ, tuyệt đối không được suy thành công khai cộng đồng.

### 11.8. Lưu trữ, thùng rác và kiểm thử bắt buộc

Lưu trữ hoặc xóa bài cập nhật trạng thái nội bộ và thu hồi publication trong một giao dịch. Đăng/cập nhật đồng thời với xóa/thu hồi phải có expected_revision và khóa hàng chung, không để tác vụ cũ đăng lại sau xóa. Khôi phục chỉ về nội bộ; nút đăng cộng đồng vẫn là một thao tác mới.

Thùng rác mặc định 30 ngày. Dọn vật lý chạy sau khi kiểm mọi tham chiếu còn hiệu lực, gồm phiên bản đã lưu trong kết quả; tham chiếu giữ lại bản chụp tối thiểu, không giữ cửa đọc cộng đồng. Xóa tệp mồ côi có danh sách cụ thể và nhật ký. Sao lưu không thay thế thao tác khôi phục bằng ứng dụng.

Bộ kiểm thử P11/P16 tối thiểu gồm: hai thành viên A ngang quyền, một thành viên B, một định danh chưa có đơn vị và khách; hai bản cùng tên/khác đơn vị; bài nội bộ có PDF trùng hash; bản cộng đồng chỉ có một trong hai tệp; sửa nháp sau đăng; thu hồi khi chỉ mục/trình đọc còn cũ; gợi ý/số đếm; link tệp trực tiếp; dấu trang; đổi đơn vị; tranh chấp đăng–xóa; HTML không an toàn; PDF quá lớn/hỏng/ảnh/mã hóa; khôi phục về nội bộ; tệp còn tham chiếu và nguồn cho công cụ. Kiểm cả mã trả về và nội dung thật được hiển thị.

## 12. DVH và chỉ số kế hoạch

Nằm trong kết quả PSQA, không thêm mục điều hướng chính. Tái sử dụng engine có giới hạn tài nguyên, bộ kiểm hình học và oracle hiện có sau khi đối chiếu contract mới.

RTDOSE/RTSTRUCT phải liên kết đúng; CT bắt buộc khi công cụ cần anatomy overlay hoặc reconstruction/profile yêu cầu, không bắt CT vô điều kiện cho mọi phép tính DVH có đủ hình học khác.

Xác định dose sampling, voxel/contour inclusion, đơn vị cc/% và Gy/%Rx. ROI rỗng/ngoài lưới/thiếu contour/không hỗ trợ cấu trúc không được cho đường DVH giả. Dxx/Vxx và HI/CI phải có đủ tham số định nghĩa; thiếu thì nêu không tính được. Không tự dùng ngưỡng từ phác đồ không cùng bệnh cảnh.

## 13. Triển khai Railway, xác thực Supabase và vận hành

### 13.1. Sổ cấu hình hai môi trường

Mỗi môi trường ghi service web/API/worker/PostgreSQL/Redis/storage, nguồn branch, root, build/start/predeploy, config path hiệu lực, health path, domain, target port và release SHA. Chỉ lưu tên biến hoặc giá trị công khai cần thiết; không commit secret.

| Cấu hình | Nguyên tắc |
| :--- | :--- |
| DATABASE_URL | API và Alembic dùng cùng hàm chuẩn hóa postgresql:// hoặc postgres:// → postgresql+psycopg://; giữ nguyên user/password/host/query |
| Supabase | Web dùng URL và publishable key đúng môi trường; backend kiểm issuer/audience/JWKS phù hợp cấu hình |
| VITE_* | Nếu Vite dùng build-time env, phải truyền khi build web và rebuild khi đổi; không chỉ thêm vào API |
| CORS/redirect | Cho phép đúng web origin; redirect xác thực trỏ về web tương ứng, không về API |
| API startup | Lắng nghe 0.0.0.0 và PORT của Railway; không cố định localhost |
| Migrations | Chạy Alembic predeploy đúng root; không bỏ migration để che lỗi thiếu driver |
| Health/readiness | /api/v1/health cho tiến trình; /api/v1/ready cho phụ thuộc bắt buộc; kiểm theo deployment mới, không chỉ URL trỏ bản cũ |
| Config-as-code | Nếu dùng /apps/api/railway.toml, kiểm file có trong source được build và cấu hình hiệu lực; không suy luận từ một ô UI trống |
| Storage | Tệp riêng tư, endpoint/bucket đúng môi trường; không dùng ổ tạm container làm nguồn tệp duy nhất |
| Worker | Cùng schema/output contract với API, giới hạn RAM/CPU/concurrency theo phép đo |

Production và staging dùng DB/storage riêng. DATABASE_URL dạng driver khác nhau không có nghĩa hai phiên bản PostgreSQL khác nhau; URI cần được chuẩn hóa đồng nhất cả runtime và migration.

Sổ môi trường phải phân biệt cấu hình mong muốn với quan sát trực tiếp có timestamp. Không gọi URL public hoạt động là bằng chứng mọi endpoint nghiệp vụ hoặc migration mới đã chạy.

### 13.2. Release manifest và rollback

Manifest nội bộ gồm Git SHA, image digest nếu có, migration, web/API/worker versions, engine profile versions, renderer, biến công khai cần khớp và test evidence. Không đưa manifest thành màn hình cho bác sĩ/kỹ sư.

Triển khai staging trước; thử đường mới + dữ liệu lịch sử; promote cùng artifact khi phù hợp. Migration theo expand → backfill có kiểm → chuyển consumer → chỉ dọn legacy trong đợt riêng. Rollback web/API phải xét schema backward compatibility; không downgrade DB mù hoặc xóa bảng để quay lui.

Giữ các [runbook vận hành](deployment/railway/production-runbook.md) và công cụ kiểm tra hiện có; cập nhật nội dung tương thích UX1 khi bước triển khai thực sự diễn ra. Chi phí gói Railway không được hiểu là toàn bộ dịch vụ/backup/worker luôn nằm trong một mức tiền cố định; đo tài nguyên và báo chi phí trước khi mở rộng hạ tầng.

## 14. Kiểm thử và bằng chứng

Mỗi test UX1 dùng namespace mới TC-UX1-Pxx-S/E; không dùng nhãn PASS của bản trước để đóng UI/engine mới.

| Lớp | Phạm vi |
| :--- | :--- |
| Unit | Chuẩn hóa URL, đơn vị, rule boundaries, công thức sinh học, formatter ngôn ngữ |
| Engine | Fixture cho đủ 16 họ pylinac/biến thể chính, QA contrib trong registry, hình học scale/rotate/shift, ảnh lỗi, adapter fidelity, Gamma 1D/2D và DVH oracle |
| API/DB | Scope ngay từ lookup, transaction/revision/idempotency, delete/restore, version snapshots |
| Worker/storage | Retry, crash, timeout, job hoàn thành sau xóa, orphan cleanup, signed URL hết hạn |
| Web | Compact layout, bàn phím, không JSON/ID, locale hoàn chỉnh, các trạng thái lỗi/empty/loading |
| PDF | Trích text, render ảnh, đối chiếu preview, dấu tiếng Việt, lớp phân tích và trang dài |
| E2E | Chọn bài → nhập đúng loại → phân tích → tự đánh giá → lịch sử → PDF → xóa/khôi phục → xu hướng |
| Môi trường | URL và SHA đúng, auth/DB/upload/worker/render chạy xuyên suốt staging rồi production |

Bộ fixture phải có ít nhất một happy path và các lỗi đặc trưng cho từng capability công khai trong `PylinacCapabilityRegistry`; PF/WL/Starshot có sai lệch biết trước, thang đo thay đổi, ảnh đảo/thiếu/đa đối tượng, ngưỡng sát biên. Contract test đối chiếu adapter với `results_data()` trực tiếp cùng input/tham số/version; không tự lấy output của lần chạy đang kiểm làm expected và không kiểm lại bằng cách viết bản sao thuật toán pylinac.

Các số BED kiểm chứng trong mục 10 là test toán học. Test không thay việc đơn vị đánh giá tính phù hợp của dữ liệu/giả định cho mục đích thực tế.

## 15. Liên kết giai đoạn và tiêu chí bàn giao

| Giai đoạn | Hợp đồng kỹ thuật chính |
| :--- | :--- |
| P0 | Hiệu lực UX1, crosswalk và cấu trúc điều hướng |
| P1 | Runtime/CI, baseline nguồn và kiểm hồi quy |
| P2 | Cấu hình Railway/Supabase và kiểm URL driver chung |
| P3 | AppShell/locale/routes/redirects |
| P4 | Compact quản lý đơn vị, revision và scope |
| P5 | QATestDefinition, QAAttempt, history/delete/restore |
| P6 | Typed inputs, manifest và validation |
| P7 | Manual QA + PylinacAdapter cho đủ 16 họ/biến thể chính và QA contrib public trong runtime + UI tham số/thao tác tay + overlays |
| P8 | PSQA form ΔD (%) và DTA (mm) + Gamma pylinac 1D/2D + queue; 3D kế thừa chỉ đọc |
| P9 | Snapshot/layout/renderer/PDF |
| P10 | Trend projection/query và tương thích chỉ số |
| P11 | KnowledgeArticle/Revision/PublicationSnapshot/Asset/Bookmark; phạm vi nội bộ/cộng đồng, PDF, tìm kiếm, thu hồi, cài đặt thực thi tách bài hướng dẫn |
| P12 | Tool hub và stateless calculation |
| P13 | BED/EQD2/graph/source selection |
| P14 | Comparison contract |
| P15 | Reirradiation/compensation assumptions |
| P16 | TreatmentContext/DoseConstraint/AlphaBetaEntry; nguồn theo bệnh viện và phiên bản, kế thừa kiểm quyền P11 trên mọi nguồn tham chiếu |
| P17 | DVH/ROI/metric definition trong PSQA |
| P18 | Kiểm trọn luồng, giao diện, lỗi/phục hồi; đọc chéo đơn vị, chia sẻ/thu hồi PDF và truy cập từ bài đã lưu |
| P19 | Release manifest và chuyển dữ liệu phát hành |
| P20 | Runbooks, phản hồi và độ bao phủ nội dung |

Bàn giao gồm thay đổi mã nguồn, chuyển dữ liệu nếu có, tình huống kiểm thử/đầu vào/kỳ vọng/thực tế, ảnh giao diện/PDF thích hợp, giới hạn hỗ trợ, trạng thái kiểm tại máy/môi trường thử/môi trường chính và bước còn thiếu. [Đặc tả cũ](docs/history/pre-ux-20260912/specification.md) chỉ để tra cứu khi không xung đột với UX1.3; không quyết định menu hoặc luồng mới.
