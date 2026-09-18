# RT-CONNECT IMPLEMENTATION PROGRESS

## P8-W02 — chặn trước cấu hình Gamma không tương thích — local và staging — 2026-09-18

- Đã bổ sung cùng một lớp preflight ở máy chủ và giao diện cho phép kiểm tra trước khi tạo lượt phân tích: số chiều 1D/2D, shape, spacing, gốc tọa độ, điểm ảnh vuông và DTA phải là bội số nguyên của spacing đối với Gamma hai chiều.
- Metadata đo và RTDOSE được chuẩn hóa về cùng trục mà bộ điều hợp Pylinac sử dụng; lỗi được hiển thị bằng tiếng Việt, không hiển thị khóa nội bộ hay dữ liệu kỹ thuật cho người dùng. Nút bắt đầu bị khóa khi cấu hình không thể chạy an toàn.
- API `apps/api/tests/test_gamma.py` đạt **21/21**; kiểm thử giao diện riêng đạt **8/8**; kiểm tra kiểu, lint và bản dựng giao diện đạt.
- Railway staging đã phục vụ đồng bộ API, giao diện và worker từ mã `a686905c592955b4fc6a52945e42cd70bb75d21e`; cổng công khai đạt **16/16**, health/readiness `200`, lược đồ `20260914_0023` và biên xác thực đạt. Bằng chứng: [cổng công khai staging](docs/evidence/p8-staging-public-gamma-preflight-20260918.json).
- Kiểm tra có đăng nhập trên hồ sơ tổng hợp staging xác nhận cấu hình hai chiều với đầu vào không phải hai lưới hai chiều hiện cảnh báo ngay, nút bắt đầu bị khóa và không tạo lượt mới trong lần kiểm tra. Kiểm tra lại với hai tệp RTDOSE không cùng điều kiện hai chiều vẫn bị chặn trước hàng đợi. Bằng chứng: [preflight Gamma staging](docs/evidence/p8-staging-gamma-preflight-20260918.json).
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`; yêu cầu xóa vĩnh viễn được giữ ngoài phạm vi. Đây là cổng preflight và parity, chưa đóng toàn bộ P8 vì vẫn còn ma trận chạy Pylinac thật, hàng đợi, lịch sử và bàn giao P9/P10.

## P9-W01 — tải trình biên soạn báo cáo trên staging — kiểm tra chỉ đọc — 2026-09-18

- Phiên staging có đăng nhập đã tải được trang “Trình biên soạn báo cáo”, lịch sử có 4 báo cáo và các lựa chọn nguồn gồm kết quả kiểm tra máy, phân tích QA bằng Pylinac, phân tích PSQA, phân tích liều và thể tích cùng công cụ sinh học.
- Các loại phần báo cáo gồm bản đồ Gamma, biên dạng liều, đường cong liều–thể tích, hình phân tích, cảnh báo và nguồn phiên bản; giao diện chính không hiện tệp JSON hoặc mã nội bộ.
- Đây chỉ là `STAGING_READONLY_LOAD`; chưa lưu bản sửa đổi, chưa xuất PDF/PNG và chưa đối chiếu lịch sử tải lại. Bằng chứng: [trình biên soạn báo cáo staging](docs/evidence/p9-staging-report-builder-readonly-20260918.json).
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`; yêu cầu xóa vĩnh viễn vẫn ngoài phạm vi.

## P8-W03 — Gamma hai chiều Pylinac chạy thật trên staging — đã kiểm tra lát cắt — 2026-09-18

- Đã sửa bộ kiểm tra DICOM để chấp nhận đúng trường hợp RTDOSE một lớp có `GridFrameOffsetVector` được thư viện DICOM đọc thành một giá trị đơn; bổ sung kiểm thử hồi quy và toàn bộ nhóm Gamma/DICOM đạt **45/45**.
- Staging đã chạy mã `c55a1a0cc33a41356325e5c31c589e3e7a5bf5ae`; hai tệp RTDOSE tổng hợp hai chiều được kiểm tra hợp lệ, cấu hình 3%/3 mm được mở và lượt phân tích được đưa vào hàng đợi bằng Pylinac.
- Lượt chạy hoàn tất với kết luận **Đạt**, tỷ lệ đạt **100%**, 4/4 điểm đạt, 0 điểm không đạt, 0 điểm loại khỏi tính toán, bao phủ 1 và Gamma P95 **0,083**. Đây là bằng chứng chạy thật cho lát cắt Gamma hai chiều, không phải dữ liệu mô phỏng giao diện.
- Bằng chứng: [Gamma hai chiều Pylinac staging](docs/evidence/p8-staging-gamma-2d-pylinac-20260918.json).
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`; không thực hiện xóa vĩnh viễn. P8 vẫn chưa đóng toàn bộ vì ma trận hàng đợi/lỗi, lịch sử–tính lại và bàn giao P9/P10 còn mở.

## P8-W03 — mở đúng cổng đầu vào Gamma một chiều Pylinac — đã kiểm tra cục bộ — 2026-09-18

- Đã sửa bộ xác thực tệp đo liều để chấp nhận lưới một chiều `[n]` với trục `x`; trước đây cổng này chỉ cho phép lưới hai hoặc ba chiều nên chặn sai nhánh Gamma một chiều dù engine và giao diện đã hỗ trợ.
- Kiểm thử hồi quy xác nhận tệp đo liều một chiều hợp lệ đi qua xác thực, nạp đúng dạng mảng một chiều và hai hồ sơ một chiều cùng hình học được chấp nhận trước khi đưa vào hàng đợi.
- Toàn bộ nhóm kiểm thử Gamma/DICOM/worker/bộ chuyển đổi Pylinac đạt, lint các tệp bị ảnh hưởng đạt. Bằng chứng: [đầu vào Gamma một chiều Pylinac cục bộ](docs/evidence/p8-local-gamma-1d-pylinac-20260918.md).
- Staging chưa chạy lát cắt một chiều vì hồ sơ hiện tại chưa có cặp dữ liệu đo liều một chiều đã xác thực; không tạo thêm lượt chạy trong bước này. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`; không xóa vĩnh viễn hồ sơ nào.

## P07-CT — kiểm tra tham số CatPhan ngay trên biểu mẫu — đã kiểm tra local — 2026-09-16

- Biểu mẫu năm bài CatPhan nay chặn dung sai HU, ngưỡng CNR, dung sai độ dày và hệ số kích thước vùng không phải số hoặc âm; lát gốc tùy chọn phải là số nguyên không âm; các điều chỉnh hình học phải là số hữu hạn.
- Lỗi hiện ngay trên biểu mẫu và nút phân tích bị khóa; máy chủ Pylinac vẫn là nơi kiểm tra cuối cùng và chịu trách nhiệm tính toán.
- Kiểm thử riêng và toàn bộ giao diện đạt **69/69**, kiểm tra kiểu, lint và bản dựng sản xuất đạt. Cảnh báo gói JavaScript lớn hơn 500 kB vẫn là cảnh báo hiệu năng đã có từ trước.
- Đây là hoàn thiện biên nhập liệu local cho P07-CT, chưa thay thế fixture CatPhan 700, đối chiếu từng mô-đun, kiểm lỗi đặc trưng hoặc kiểm chứng staging. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P07-CT — triển khai kiểm tra tham số CatPhan lên staging — đã kiểm tra — 2026-09-16

- API, giao diện và tiến trình nền staging đã được dựng lại từ cùng commit `f1bbd9b966895e65f9132813d75d3f0d91159a38`.
- Bộ xác minh công khai đạt **16/16**; health/readiness 200, lược đồ `20260914_0023`, OpenAPI, biên xác thực và gói web đúng mốc nguồn đều đạt.
- Đây là parity triển khai và kiểm tra hợp đồng công khai, chưa phải chạy CatPhan bằng fixture commissioning có đăng nhập. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Bằng chứng: [staging kiểm tra tham số CatPhan](docs/evidence/p7-staging-catphan-form-validation-20260916.json).

## P07-VMAT — kiểm tra tham số ngay trên biểu mẫu — đã kiểm tra local — 2026-09-16

- Biểu mẫu ba bài VMAT nay chặn dung sai không phải số hoặc âm, chiều rộng/chiều dài đoạn phân tích không dương và, riêng DRCS, khoảng cách xuyên tâm lớn hơn nhỏ nhất.
- Lỗi hiện ngay trong biểu mẫu và nút phân tích bị khóa; quy tắc này bổ sung cho cổng máy chủ, không tính lại hoặc thay thế Pylinac.
- Kiểm thử riêng và toàn bộ giao diện đạt **68/68**, kiểm tra kiểu, lint và bản dựng sản xuất đạt. Cảnh báo gói JavaScript lớn hơn 500 kB vẫn là cảnh báo hiệu năng đã có từ trước.
- Đây là hoàn thiện biên nhập liệu local cho P07-VMAT, chưa thay thế ma trận fixture, đối chiếu độc lập, lựa chọn ROI/offset đầy đủ hoặc kiểm chứng staging. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P07-VMAT — triển khai kiểm tra tham số lên staging — đã kiểm tra — 2026-09-16

- API, giao diện và tiến trình nền staging đã được dựng lại từ cùng commit `17a5f91bb0665a04d323dd49d55113975dbcd4e2`.
- Bộ xác minh công khai đạt **16/16**; health/readiness 200, lược đồ `20260914_0023`, OpenAPI, biên xác thực và gói web đúng mốc nguồn đều đạt.
- Đây là parity triển khai và kiểm tra hợp đồng công khai, chưa phải chạy ba bài VMAT bằng bộ tệp commissioning có đăng nhập. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Bằng chứng: [staging kiểm tra tham số VMAT](docs/evidence/p7-staging-vmat-form-validation-20260916.json).

## P07-STAR — trình bày tâm và các tia của bài Kiểm tra sao — đã kiểm tra local — 2026-09-16

- Trình xem kết quả bài Kiểm tra sao nay có bảng riêng cho tâm vùng giao nhau, đường kính, bán kính, dung sai, kết luận của Pylinac và từng góc tia đã nhận diện.
- Ảnh phân tích vẫn được mở riêng để xem trực quan tâm, đường tia và vòng tròn; bảng chỉ trình bày nhãn nghiệp vụ tiếng Việt, không hiện khóa kỹ thuật, phiên bản, tên tệp hoặc dữ liệu JSON.
- Kiểm thử giao diện toàn bộ đạt **67/67**, kiểm tra kiểu, lint và bản dựng sản xuất đạt. Cảnh báo gói JavaScript lớn hơn 500 kB vẫn là cảnh báo hiệu năng đã có từ trước.
- Đây là hoàn thiện lớp trình bày local cho P07-STAR, chưa thay thế đối chiếu độc lập, fixture commissioning, kiểm lỗi đặc trưng hoặc kiểm chứng staging có đăng nhập. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P07-STAR — triển khai trình xem kết quả lên staging — đã kiểm tra — 2026-09-16

- API, giao diện và tiến trình nền staging đã được dựng lại từ cùng commit `63c480ea29e871b05f537a554fba1cdbd8b96296`.
- Bộ xác minh công khai đạt **16/16**; health/readiness 200, lược đồ `20260914_0023`, OpenAPI, biên xác thực và gói web đúng mốc nguồn đều đạt.
- Đây là parity triển khai và kiểm tra hợp đồng công khai, chưa phải chạy bài Kiểm tra sao bằng tệp commissioning có đăng nhập. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Bằng chứng: [staging trình xem Kiểm tra sao](docs/evidence/p7-staging-starshot-result-viewer-20260916.json).

## P07-LOG — kiểm tra cặp Dynalog và tệp Trajectory trước khi gọi Pylinac — đã kiểm tra local — 2026-09-16

- Bộ chọn tệp Dynalog nay chỉ chấp nhận đúng một tệp DLG bắt đầu bằng A và một tệp DLG bắt đầu bằng B. Tệp DLG thứ hai không đúng cặp sẽ bị báo lỗi ngay trên biểu mẫu.
- Bộ chọn Trajectory Log nay yêu cầu đúng một tệp BIN hoặc TLOG; nếu có tệp thứ hai thì chỉ được là TXT mô tả. Không thể vô tình gửi hai tệp nhị phân khiến bộ tính chọn tệp theo thứ tự tên.
- API và bộ điều hợp Pylinac lặp lại cùng quy tắc, vì vậy yêu cầu gửi trực tiếp hoặc yêu cầu cũ từ giao diện đều được chặn cùng một cách.
- Kiểm thử giao diện đạt **16/16**, kiểm thử nhóm Pylinac đạt **39/39**, kiểm tra kiểu, lint giao diện và bản dựng đạt. Một cảnh báo kích thước gói JavaScript vẫn còn từ trước và không ảnh hưởng kết quả.
- Đây là cổng hợp đồng đầu vào local, chưa đóng P07-LOG: Trajectory 3/4 vẫn cần fixture đại diện, Gamma nhật ký cần kiểm tra ổn định, và còn cần chạy staging có đăng nhập bằng bộ tệp được phê duyệt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P07-LOG — Gamma fluence Dynalog bằng bộ mẫu chính thức — đã kiểm tra local — 2026-09-16

- Hồi quy gọi trực tiếp `AQA.dlg/BQA.dlg` của Pylinac `3.47.0` với Gamma fluence, dung sai liều `2,0%` và dung sai khoảng cách `2,0 mm`.
- Pylinac trả bản đồ kích thước `60 × 4000`, có `240000` điểm hợp lệ; giá trị Gamma cực đại và trung bình đều hữu hạn, không âm và cực đại không nhỏ hơn trung bình.
- Đây là kiểm tra đường Gamma Dynalog thật trên bộ mẫu chính thức. Trajectory Log 3/4 vẫn chưa có fixture đại diện; chưa coi P07-LOG là hoàn thành và chưa tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P07-LOG — triển khai cổng chọn tệp lên staging — đã kiểm tra — 2026-09-16

- Railway staging đã phục vụ commit `43fc158bbac34c93127cf27a633881f620e67056` cho cả API và giao diện.
- Bộ xác minh công khai đạt **16/16**; health/readiness 200, lược đồ `20260914_0023`, API và giao diện cùng mã nguồn, gói giao diện có dấu hiệu kiểm tra tổ chức và cổng QA mới.
- Đây là parity triển khai và biên chưa xác thực, chưa phải nghiệm thu Dynalog/Trajectory bằng tệp được phê duyệt hoặc đóng P07-LOG. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P07-WL — trình bày véc-tơ CAX–bi theo từng ảnh — đã kiểm tra local — 2026-09-16

- Kết quả Winston–Lutz một bia nay có bảng riêng theo từng ảnh, đọc trực tiếp từ nhóm snapshot Pylinac dạng góc máy/góc chuẩn trực/góc bàn, khoảng cách CAX–bi, véc-tơ CAX–bi và khoảng cách CAX–EPID.
- Khóa kết quả kỹ thuật kiểu `G…B…P…` không hiển thị cho người dùng; bảng chỉ dùng số thứ tự ảnh và không hiển thị tên tệp hoặc mã nội bộ.
- Kiểm thử giao diện trang kết quả đạt **17/17**, kiểm tra kiểu và lint đạt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Đây là lát cắt trình bày kết quả local, chưa đóng P07-WL: đối chiếu độc lập, ma trận fixture commissioning, điều chỉnh trực quan theo từng ảnh nếu Pylinac hỗ trợ và kiểm chứng staging tương tác vẫn mở.

## P07-WL — triển khai trình xem véc-tơ lên staging — đã kiểm tra — 2026-09-16

- Railway đã dựng lại API, worker và giao diện từ mốc `12650737b0b0c7a8de3f7773bfc2e5d27be4cab2`.
- Bộ xác minh công khai đạt **16/16**; health/readiness 200, lược đồ `20260914_0023`, API và giao diện cùng mã nguồn, gói giao diện mới được phục vụ.
- Đây là parity triển khai và biên chưa xác thực, chưa chạy Winston–Lutz có đăng nhập bằng bộ ảnh được phê duyệt và chưa đóng P07-WL. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-W04 — chọn lát gốc trực quan cho nhóm phantom CT — đã kiểm tra local — 2026-09-16

- Vùng xem trước dùng chung nay có thể điều khiển từ biểu mẫu cha: CatPhan, ACR và nhóm Cheese/Helios/Quart đồng bộ lát người dùng chọn vào `origin_slice` trước khi gọi Pylinac.
- Chuỗi ngắn vẫn dùng danh sách lát; chuỗi dài vẫn dùng ô nhập số theo giới hạn xem trước hiện hành. Khi đổi tệp, vùng chọn được tạo lại để không giữ lựa chọn của tệp trước.
- Việc chọn lát không giả định tâm tuyệt đối của phantom. Các điều chỉnh ngang/dọc/góc vẫn đi qua đúng tham số mà Pylinac công khai hỗ trợ; nếu cần chỉnh tâm, người thực hiện vẫn nhập điều chỉnh theo mm trong biểu mẫu.
- Kiểm tra kiểu, lint, bản dựng và toàn bộ giao diện đạt **58/58**. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; hồ sơ `dailyQA` được giữ nguyên.
- Đây là hoàn thiện một phần P7-W04, chưa phải nghiệm thu phantom, chưa thay thế fixture chuẩn/commissioning, đối chiếu độc lập hoặc kiểm chứng staging.

## P7-W04 — triển khai chọn lát gốc trực quan trên staging — đã kiểm tra — 2026-09-16

- API và giao diện staging đã cùng phục vụ commit `02c154238dbaac047634f50ff31e4638f9b6eda9`; mốc đồng bộ trong API buộc tiến trình nền tái dựng theo cùng source revision.
- Cổng kiểm tra công khai exact-SHA đạt **16/16**; health/readiness, lược đồ `20260914_0023`, OpenAPI, ranh giới chưa xác thực và dấu hiệu vùng xem trước đều đạt.
- Đây là kiểm tra parity triển khai, chưa chạy phân tích bằng phantom được phê duyệt và chưa đóng P7-W04/P7. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; hồ sơ `dailyQA` được giữ nguyên.
- Bằng chứng: [staging chọn lát gốc trực quan](docs/evidence/p7-staging-visual-origin-slice-deployment-20260916.json).

## P7-W04 — nhập góc thủ công theo từng ảnh cho Winston–Lutz một bia — đã kiểm tra local — 2026-09-16

- Bài Winston–Lutz một bia nay có ba cách lấy góc: đọc từ thông tin DICOM, đọc từ tên tệp hoặc nhập theo thứ tự ảnh.
- Khi chọn nhập tay, giao diện tự đếm bộ ZIP và tạo đúng một dòng cho mỗi ảnh, chỉ hiển thị “Ảnh 1”, “Ảnh 2”…; không hiển thị tên tệp kỹ thuật. Nút phân tích chỉ mở khi đủ ba góc dạng số cho mọi ảnh.
- Máy chủ kiểm tra ánh xạ tay, ghép theo đúng thứ tự thành viên ảnh an toàn trong ZIP và chặn số dòng không khớp hoặc đồng thời chọn đọc tên tệp. Pylinac nhận `axis_mapping` trực tiếp qua bộ khởi tạo chuẩn, không có thuật toán thay thế.
- Kiểm thử riêng đạt **6/6** (bốn ca trước đó của Winston–Lutz và hai ca mới), kiểm tra kiểu, lint và bản dựng giao diện đạt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; hồ sơ `dailyQA` được bảo toàn.
- Đây là hoàn thiện hợp đồng nhập góc, chưa phải nghiệm thu kết quả lâm sàng. Ma trận fixture đại diện, đối chiếu độc lập, điều chỉnh trực quan theo từng ảnh và kiểm chứng staging vẫn còn mở.
- Bằng chứng: kiểm thử `apps/api/tests/test_pylinac_qa.py -k "winston_lutz_adapter"` và bản mã nguồn trên nhánh hiện tại.

## P7-W04 — triển khai nhập góc Winston–Lutz một bia trên staging — đã kiểm tra — 2026-09-16

- Staging đã phục vụ cùng commit `eb0a87417d16364dd62a986efa62e9038bd54c86` với mã đã kiểm tra local; API và gói giao diện cùng nhận đúng bản phát hành.
- Cổng kiểm tra công khai exact-SHA đạt **16/16**; health/readiness, lược đồ `20260914_0023`, OpenAPI, biên giới xác thực và gói giao diện đều đạt.
- Đây là kiểm tra parity và phát hành, chưa chạy phân tích bằng tệp QA thật trên staging. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ; `dailyQA` được bảo toàn.
- Bằng chứng: [staging nhập góc Winston–Lutz một bia](docs/evidence/p7-staging-winston-lutz-manual-angle-deployment-20260916.json).

## P7-W03/W04 — triển khai cổng tệp hợp lệ lên staging — đã kiểm tra staging — 2026-09-16

- Railway đã dựng lại API, web và tiến trình nền từ cùng commit `905fbda295ca8554417382f8a292891f6c3df573` sau khi bổ sung mốc đồng bộ dưới thư mục dịch vụ.
- Kiểm tra exact-SHA công khai đạt **16/16**; API và gói web cùng báo đúng phiên bản commit, readiness trả lược đồ `20260914_0023`, các tuyến công khai và biên giới chưa xác thực đạt.
- Đây mới là kiểm tra phát hành/cổng đầu vào; chưa chạy phân tích trên tệp staging, chưa đóng ma trận fixture P7 và chưa phải nghiệm thu lâm sàng. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; `dailyQA` được bảo toàn.
- Bằng chứng: [exact-SHA staging cho cổng tệp hợp lệ](docs/evidence/p7-staging-validated-input-gate-20260916.json).

## P7-W03/W04 — chỉ chạy phân tích với tệp đã kiểm tra hợp lệ — đã kiểm tra local — 2026-09-16

- Đã áp dụng cổng trạng thái `VALID` cho toàn bộ bài Pylinac có tệp đầu vào: tệp ảnh, bộ ảnh nén, cặp nhật ký, bài hạt nhân và mô-đun đóng góp. Bài hiệu chuẩn nhập số liệu vẫn không cần tệp.
- Tệp chưa kiểm tra hoặc có cảnh báo không bị xóa khỏi danh sách; người dùng vẫn có nút kiểm tra lại. Nút phân tích chỉ mở khi mọi tệp đang chọn hợp lệ.
- Kiểm thử giao diện đạt **56/56**, kiểm tra kiểu, lint, bản dựng và hợp đồng kế hoạch đều đạt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; `dailyQA` được bảo toàn.
- Đây là cổng an toàn local, chưa đóng kiểm chứng staging toàn bộ bài, fixture chuẩn, đối chiếu độc lập hoặc nghiệm thu lâm sàng.
- Bằng chứng: [cổng tệp hợp lệ trước khi phân tích](docs/evidence/p7-local-validated-input-gate-20260916.md).

## P7-W04 — giới hạn tọa độ chọn điểm theo ảnh gốc — đã kiểm tra local — 2026-09-16

- Tách phép đổi tọa độ con trỏ thành tiện ích dùng chung. Điểm bấm/kéo được đổi theo kích thước ảnh gốc, giới hạn an toàn khi nằm ngoài mép và hỗ trợ cả tọa độ điểm ảnh lẫn tọa độ chuẩn hóa.
- Kiểm thử riêng đạt **6/6**, toàn bộ giao diện đạt **55/55**, kiểm tra kiểu, lint và bản dựng sản xuất đạt; lint không còn cảnh báo.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; `dailyQA` được bảo toàn.
- Đây là cổng an toàn tọa độ local, chưa đóng ROI chuyên biệt, ánh xạ trực quan theo từng ảnh hoặc kiểm chứng staging của P7-W04.
- Bằng chứng: [ánh xạ tọa độ ảnh an toàn](docs/evidence/p7-local-coordinate-clamp-20260916.md).

## P16/P11 — thư viện kiến thức thuần tiếng Việt, không lộ JSON và mã kỹ thuật — đã kiểm tra local — 2026-09-16

- Biểu mẫu thư viện đã chuyển sang tiếng Việt: người dùng chọn loại bài, nhập tên, mô tả, bối cảnh mặt bệnh, tiêu chí, nguồn và nội dung bài viết bằng các trường dễ hiểu; khóa nội bộ được sinh tự động ở phía hệ thống.
- Đã ẩn mã bài viết, mã băm, liên kết bài gốc, phiên bản kỹ thuật, trạng thái nội bộ và vùng xem dữ liệu dạng JSON. Phần so sánh và lịch sử chỉ hiển thị tên bài, phiên bản, trạng thái và thời điểm cần thiết.
- Vùng đưa tài liệu vào công cụ chỉ cho chọn công cụ và hiển thị thông báo dễ hiểu; không cho người dùng nhập phần ghi đè dạng JSON. Nút tải xuống chỉ còn bảng dữ liệu.
- Kiểm tra kiểu, lint, bản dựng và giao diện đạt **54/54**. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; `dailyQA` được bảo toàn.
- Đây là cổng trải nghiệm local, chưa phải hoàn thành toàn bộ thư viện. Phạm vi nội bộ/cộng đồng, bài viết và tệp PDF, quyền chia sẻ, nguồn thật và kiểm chứng staging còn mở theo P11/P16.
- Bằng chứng: [giao diện thư viện kiến thức thuần tiếng Việt](docs/evidence/p16-local-vietnamese-library-ui-20260916.md).

## P7-W04 — cô lập lịch sử theo bài QA — đã kiểm tra local — 2026-09-16

- Các trang bài QA không còn dùng chung toàn bộ lịch sử trong hồ sơ; lịch sử và kết quả mới nhất được lọc theo đúng bài đang mở, bao phủ Picket Fence, Starshot, Winston–Lutz, VMAT, phân tích trường, CatPhan, phantom và ảnh phẳng.
- Kiểm thử tiện ích và toàn bộ giao diện đạt **54/54**; kiểm tra kiểu, lint và bản dựng sản xuất đạt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ staging; `dailyQA` được bảo toàn.
- Đây là cổng đúng đắn local cho kết quả/lịch sử; còn kiểm chứng thao tác staging, ROI chuyên biệt và ánh xạ đa ảnh theo P7-W04.
- Bằng chứng: [cô lập lịch sử theo bài QA](docs/evidence/p7-local-history-isolation-20260916.md).

## P7-W03 — đối chiếu chỉ số lõi với bộ mẫu chính thức — đã kiểm tra local — 2026-09-16

- Bổ sung kiểm thử hồi quy cho 20 chỉ số lõi của Picket Fence, Winston–Lutz một bi, Winston–Lutz nhiều bi, ba biến thể VMAT, bốn bài CatPhan, TomoCheese, Quart DVT, phân tích ảnh phẳng, phân tích biên dạng trường và phân tích trường kiểu cũ.
- Các giá trị được giữ làm tham chiếu cố định từ wheel Pylinac `3.47.0`; lần chạy `-k core_metric` đạt **20/20**. Bài DRCS được lấy giá trị trực tiếp từ wheel hiện tại để tránh dùng nhầm số liệu của fixture hoặc phiên bản cũ.
- Đây là đối chiếu hợp đồng giữa bộ điều hợp và phiên bản engine đã khóa, chưa phải oracle độc lập hoặc nghiệm thu lâm sàng. Toàn bộ fixture đại diện, kiểm lỗi đặc trưng, staging và xác nhận chuyên môn của P7 vẫn còn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ staging; `dailyQA` được bảo toàn.
- Bằng chứng: [đối chiếu chỉ số lõi Pylinac](docs/evidence/p7-local-official-core-metric-reference-20260916.md).

## P14/P15 — giao diện thuần tiếng Việt và ẩn chi tiết kỹ thuật — đã kiểm tra local — 2026-09-16

- Trang so sánh phác đồ đã đổi toàn bộ nhãn thao tác, trạng thái, bảng kết quả, lịch sử và thông báo sang tiếng Việt; người dùng chỉ thấy tên phương án, thời điểm và số liệu cần thiết.
- Đã ẩn mã nội bộ của phương án, kết quả, bản cập nhật, dấu kiểm tra và mã lỗi khỏi giao diện; các mã này vẫn được giữ bên trong để liên kết và truy xuất an toàn.
- Giao diện so sánh chỉ còn tải bảng kết quả; không còn hiển thị lựa chọn tải dữ liệu dạng JSON. Phần tái xạ và bù phân liều cũng ẩn lựa chọn JSON, Việt hóa phần tóm tắt kết quả và dùng cách gọi “đợt điều trị”, “mô hoặc cơ quan”, “phương án”.
- Kiểm tra giao diện đạt **53/53**, kiểm tra kiểu, lint và bản dựng sản xuất đạt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ staging; `dailyQA` được bảo toàn.
- Đây là cải tiến trải nghiệm và bảo vệ người dùng khỏi chi tiết kỹ thuật; các cổng nghiệm thu P14/P15 về số học, nguồn, dữ liệu thật và xác nhận chuyên môn vẫn còn mở theo `plan.md`.

## UX — thu gọn thẻ xác thực và danh mục QA — đã kiểm tra local — 2026-09-16

- Thẻ đăng nhập/chưa có đơn vị được thu gọn theo chiều dọc và mở rộng vừa đủ theo chiều ngang để hai lựa chọn tham gia bằng lời mời và tạo đơn vị dễ xem hơn trong một màn hình lớn.
- Danh mục bài QA dùng ba cột ở màn hình rộng, hai cột ở màn hình trung bình và một cột ở màn hình hẹp; thẻ bài kiểm tra giảm khoảng đệm nhưng vẫn giữ nhãn, trạng thái và vùng bấm rõ ràng.
- Kiểm thử giao diện đạt **53/53**, lint, kiểm tra kiểu và bản dựng sản xuất đạt. Không thay đổi dữ liệu, không tạo hồ sơ và không thao tác xóa/lưu trữ/khôi phục `dailyQA`.
- Đây là cải tiến hiển thị local; cần kiểm tra trực tiếp staging ở các kích thước 1366×768 và 1440×900 trước khi ghi nhận parity.

## P7-W03 — bộ mẫu chính thức Winston–Lutz nhiều bi — đã kiểm tra local — 2026-09-16

- Đã đưa `SNC_MTWL_demo.zip` vào ma trận tệp mẫu chính thức. Bộ mẫu có 19 ảnh DICOM và được phân tích bằng cấu hình sáu bi chuẩn theo ví dụ chính thức của Pylinac.
- Đường chạy qua `execute_pylinac` trả đúng lớp `WinstonLutzMultiTargetMultiField`, 14 nhóm chỉ số và ảnh overlay PNG; ma trận tệp mẫu chính thức đạt **37/37**.
- Đây là bằng chứng engine và fixture local, không phải xác nhận kết quả lâm sàng. Còn mở đối chiếu độc lập từng chỉ số, ánh xạ góc thủ công theo từng ảnh, kiểm thử lỗi đặc trưng và kiểm chứng staging.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; hồ sơ `dailyQA` được bảo toàn.
- Bằng chứng: [Winston–Lutz nhiều bi với bộ mẫu chính thức](docs/evidence/p7-local-winston-lutz-multi-target-official-demo-20260916.md).

## P7-WLMT — nhập góc thủ công theo thứ tự ảnh — đã kiểm tra local — 2026-09-16

- Bài Winston–Lutz nhiều bi nay có ba cách lấy góc: đọc từ thông tin ảnh, đọc từ tên tệp hoặc nhập theo thứ tự ảnh.
- Khi chọn nhập tay, giao diện chỉ hiển thị “Ảnh 1”, “Ảnh 2”… và tự tạo đủ dòng theo số ảnh trong bộ ZIP; không hiển thị tên tệp kỹ thuật hay cấu hình thô. Nút phân tích chỉ mở khi cả ba góc của mọi ảnh đều là số hợp lệ.
- Máy chủ kiểm tra ánh xạ tay, ghép theo đúng thứ tự thành viên ảnh an toàn trong ZIP và chặn trường hợp số dòng không khớp hoặc vừa bật đọc tên tệp vừa nhập tay. Kiểm thử riêng đạt **4/4**; toàn bộ nhóm hồi quy Pylinac đạt **109/109**; Ruff, kiểm tra kiểu, lint, bản dựng và giao diện đạt.
- Giá trị ánh xạ trong lịch sử được rút gọn thành “đã nhập góc cho N ảnh”, nhưng vẫn giữ đầy đủ dữ liệu để đối chiếu nội bộ.
- Đây là hoàn thiện luồng nhập góc, không phải nghiệm thu kết quả lâm sàng. Còn mở ghép cặp/điều chỉnh trực quan theo từng ảnh, đối chiếu độc lập, fixture thực tế và kiểm chứng staging.

## P7-W04 — chọn ảnh/lát trong chuỗi DICOM dài — đã kiểm tra local — 2026-09-16

- Mở giới hạn xem trước từ 32 lên 2.048 ảnh/lát trong phạm vi an toàn. Chuỗi ngắn vẫn dùng danh sách; chuỗi dài dùng ô nhập số từ 1 đến tổng số ảnh/lát để tránh một danh sách cuộn quá dài.
- Kiểm thử máy chủ thêm ca ZIP 33 ảnh DICOM tổng hợp, xác nhận ảnh thứ 33 có thể xem; toàn bộ kiểm thử máy chủ đạt 100%, giao diện đạt **53/53**, lint, kiểm tra kiểu và bản dựng đạt.
- Bản `bef9777` đã được Railway triển khai cho cả máy chủ và giao diện staging; kiểm tra công khai chỉ đọc đạt **14/14**, health/readiness, lược đồ, biên giới xác thực và gói web đều đạt.
- Không chạy phân tích, không tạo hồ sơ mới và không thao tác xóa/lưu trữ/khôi phục hồ sơ `dailyQA`.
- Bằng chứng: [xem trước chuỗi DICOM dài](docs/evidence/p7-local-long-series-preview-20260916.md) và [triển khai xem trước chuỗi dài trên staging](docs/evidence/p7-staging-long-series-preview-deployment-20260916.md). P7-W04 vẫn mở các cổng ROI riêng, ánh xạ tọa độ theo từng ảnh và kiểm tra tương tác chuỗi dài với tệp được phê duyệt.

## P7-W04 — chỉ hiện phân tích liều cho bài có hợp đồng liều — đã kiểm tra staging — 2026-09-16

- Khu vực QA không còn suy luận quyền mở phân tích liều từ các tệp RTDOSE/RTSTRUCT đang nằm trong hồ sơ. Vì một hồ sơ có thể chứa tệp phục vụ bài khác, nút này nay chỉ xuất hiện khi loại bài QA yêu cầu đầu vào liều, như PSQA.
- Trên staging, hồ sơ Starshot vẫn hiện khu vực tệp ảnh nhưng không còn nút phân tích liều; hồ sơ PSQA vẫn hiện nút và hướng dẫn RTDOSE/RTSTRUCT. Danh mục hiển thị `64/64` bài.
- Kiểm thử giao diện đạt **53/53**, lint, kiểm tra kiểu và bản dựng sản xuất đều đạt. Bản web `e647840` triển khai thành công; kiểm tra chỉ đọc không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Bằng chứng: [điều kiện phân tích liều trên staging](docs/evidence/p7-staging-dose-shortcut-contract-20260916.md). P7-W04 vẫn mở các cổng ROI, tọa độ đa ảnh, lựa chọn ảnh ngoài giới hạn xem trước và nghiệm thu đầy đủ.

## P7-W04 — diff lịch sử hiển thị tham số đã bỏ — đã kiểm tra local — 2026-09-16

- Trình xem kết quả nay đối chiếu hợp của lượt hiện tại và lượt ngay trước, nên hiển thị đủ tham số mới thêm, thay đổi và đã bỏ bằng nhãn `Mới thêm`, `Đã bỏ` hoặc giá trị trước/sau.
- Kiểm thử giao diện đạt **52/52**, lint, kiểm tra kiểu và bản dựng sản xuất đều đạt; luồng chỉ đọc lịch sử, không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Bằng chứng: [diff tham số đã bỏ trong lịch sử](docs/evidence/p7-local-result-parameter-removal-20260916.md). Cần triển khai và kiểm tra trình duyệt staging trước khi ghi nhận parity.

## P7-W03 — hợp đồng hồ sơ đầu vào theo liên kết chạy thật — đã kiểm tra staging — 2026-09-16

- Cổng máy chủ nay dùng `input_profile` của liên kết Pylinac thay vì suy ra lại từ danh mục giao diện; registry có kiểm thử phát hiện lệch giữa `input_kind` và hồ sơ thực thi cho toàn bộ 63 capability.
- Bản `dee1b67` đã triển khai thành công cho API và giao diện staging; API `health/ready/version`, kiểm tra công khai và lược đồ hiện hành đều đạt.
- Kiểm tra registry không có sai lệch hồ sơ đầu vào; kiểm thử API toàn bộ chạy đến 100% không lỗi; Ruff và kiểm tra hợp đồng kế hoạch đều đạt.
- Bằng chứng: [hợp đồng hồ sơ đầu vào theo liên kết chạy thật trên staging](docs/evidence/p7-staging-runtime-input-profile-contract-20260916.md). P7 vẫn mở các cổng fixture, đối chiếu độc lập, xác nhận chuyên môn, PDF và VERIFY/HANDOFF.

## P7-W03 — cổng máy chủ IMAGE_OR_PROFILE — đã kiểm tra staging — 2026-09-16

- Máy chủ nay áp dụng cùng cổng tương thích cho `IMAGE_OR_PROFILE`; bài Phân tích biên dạng trường cũng từ chối RTDOSE, RTSTRUCT và RTPLAN trước khi gọi Pylinac, không phụ thuộc vào bộ lọc trình duyệt.
- Bản API `3348524` đã triển khai thành công; kiểm tra công khai staging đạt `failed_check_count=0`, readiness đạt và toàn bộ kiểm thử API cục bộ không có lỗi.
- Kiểm thử Pylinac liên quan đạt **49/49**, Ruff đạt; không tạo lịch sử mới và không động tới hồ sơ `dailyQA`.
- Bằng chứng: [cổng máy chủ IMAGE_OR_PROFILE trên staging](docs/evidence/p7-staging-image-or-profile-server-gate-20260916.md). P7 vẫn mở các cổng fixture, đối chiếu độc lập, xác nhận chuyên môn, PDF và VERIFY/HANDOFF.

## P7-W04 — trạng thái rỗng vùng điều chỉnh ảnh — đã kiểm tra staging — 2026-09-16

- Khi bài Kiểm tra sao không có ảnh phù hợp để chọn, vùng điều chỉnh nay hiển thị “Chọn ảnh để bật vùng điều chỉnh.” thay vì “Đang tải ảnh xem trước…” vô hạn.
- Nút bắt đầu phân tích bị khóa khi chưa có đầu vào ảnh; tệp RTDOSE hợp lệ vẫn được giữ nguyên trong hồ sơ và lịch sử vẫn là `0`.
- Kiểm thử riêng đạt **3/3**; toàn bộ giao diện đạt **51/51**; lint, kiểm tra kiểu và bản dựng sản xuất đạt. Kiểm tra trình duyệt staging sau triển khai xác nhận đúng trạng thái rỗng.
- Bằng chứng: [trạng thái rỗng vùng điều chỉnh trên staging](docs/evidence/p7-staging-empty-adjustment-state-20260916.md). Không có dữ liệu staging nào bị tạo, sửa, lưu trữ, khôi phục hoặc xóa.

## P7-W03 — cổng tương thích loại đầu vào Pylinac — đã kiểm tra staging — 2026-09-16

- Bản `02c51f3404a0c7ef509b752c96c0d1738b830db3` đã triển khai thành công cho cả API và giao diện staging; kiểm tra công khai và đối chiếu cấu hình Railway đều không có lỗi.
- Trên bài Kiểm tra sao đang có tệp RTDOSE hợp lệ, giao diện không còn đưa tệp đó vào bộ chọn ảnh; khu vực tệp vẫn giữ nguyên tệp đã tải và lịch sử vẫn là `0`.
- Kiểm tra chỉ đọc: không tạo lượt Pylinac, không tải lên, không sửa, không lưu trữ, không khôi phục và không xóa hồ sơ `dailyQA` hay dữ liệu liên quan.
- Bằng chứng: [cổng tương thích loại đầu vào Pylinac trên staging](docs/evidence/p7-staging-input-profile-gate-20260916.md). P7 vẫn mở các cổng fixture Starshot đại diện, đối chiếu độc lập, xác nhận chuyên môn, PDF và VERIFY/HANDOFF.

## Quyết định phạm vi dữ liệu — 2026-09-16

- Dừng công việc xóa vĩnh viễn hồ sơ thử nghiệm theo yêu cầu mới. `dailyQA`, lịch sử QA, tệp liên quan và điểm xu hướng được bảo toàn; không tiếp tục thiết kế hoặc chạy luồng xóa cho mục tiêu này.
- Các công việc tiếp theo ưu tiên hoàn thiện cổng đầu vào, phân tích Pylinac, lịch sử, báo cáo, thư viện kiến thức và công cụ sinh học theo đúng thứ tự trong `plan.md`.

## P7-W03 — cổng tương thích loại đầu vào Pylinac — lát cắt cục bộ — 2026-09-16

- Bài phân tích ảnh không còn nhận nhầm RTDOSE, RTSTRUCT, RTPLAN hoặc số đo chỉ vì tệp đã ở trạng thái hợp lệ. Máy chủ chặn trước khi gọi Pylinac; giao diện cũng loại các tệp này khỏi danh sách chọn ảnh.
- Kiểm thử API liên quan đạt **49/49**; giao diện đạt **50/50**, lint và kiểm tra kiểu đạt. Trường hợp RTDOSE hợp lệ chọn cho Starshot không tạo lịch sử mới.
- Bằng chứng: [cổng tương thích loại đầu vào Pylinac](docs/evidence/p7-local-input-profile-gate-20260916.md). Cần triển khai exact-SHA và kiểm tra lại trên staging; không xóa hoặc sửa hồ sơ `dailyQA`.

## P7-W04 — cảnh báo Pylinac theo đúng lịch sử — lát cắt cục bộ — 2026-09-15

- Trình xem kết quả QA máy đã được khóa hồi quy: cảnh báo do Pylinac nằm trong vùng riêng, không làm đổi đánh giá của người thực hiện và đi cùng đúng lượt lịch sử đang xem.
- Kiểm thử riêng đạt **2/2**; toàn bộ giao diện đạt **49/49**, cùng lint, kiểm tra kiểu và bản dựng sản xuất.
- Đây chỉ là bằng chứng local; chạy Pylinac thật trên staging, PDF và VERIFY/HANDOFF P7 vẫn mở. Không tạo, sửa hoặc xóa dữ liệu staging; hồ sơ `dailyQA` và lịch sử liên quan được giữ nguyên.
- Bằng chứng: [cảnh báo Pylinac và lịch sử](docs/evidence/p7-local-result-warning-history-20260915.md).

## P17-W03 — bản xem trước HI/CI trên staging — 2026-09-15

- Sau khi dừng hướng xóa vĩnh viễn hồ sơ, đã triển khai bản web `e7b3150` và kiểm tra trực tiếp trên staging; triển khai Railway `be7f670f-033d-44c6-8fa3-8df7ce7deeb8` đạt `SUCCESS`.
- Luồng chọn “Chỉ số phù hợp RTOG ở mức 95%”, nhập liều kê đơn `6 Gy` và bấm “Kiểm tra và xem trước” hiển thị bản xem trước mới với giá trị `0,7500`, trạng thái “Đã tính”. Không bấm lưu, không tạo lần tính mới.
- Lịch sử hồ sơ vẫn giữ nguyên 2 lần tính cũ; giao diện không hiển thị mã nội bộ, JSON hay tên tệp kỹ thuật. Khi dùng `60 Gy`, dữ liệu thiếu thể tích liều 95% được báo “Chưa đủ dữ liệu”, không suy đoán.
- Bản web `8324540` tiếp tục sửa nhãn kết quả để phân biệt rõ “Bản xem trước · chưa lưu” với kết quả đã lưu; không còn hiển thị thời điểm lưu cũ như thể thuộc bản xem trước mới. Kiểm thử hồi quy DVH đạt **7/7**.
- Bằng chứng: [bản xem trước HI/CI trên staging](docs/evidence/p17-staging-hi-ci-preview-20260915.md). P17-W03 đã có kiểm tra staging cho lát cắt xem trước, nhưng vẫn mở cổng oracle độc lập, xác nhận chuyên môn và nguồn tiêu chí theo bối cảnh.

## P17-W02/P17-W03 — chỉ số HI/CI trong DVH — lát cắt cục bộ — 2026-09-15

- Đã nối máy chủ DVH với bốn công thức được chọn rõ: `(D2 − D98) / D50`, `D5 / D95`, chỉ số phù hợp RTOG 95% và chỉ số phù hợp Paddick 95%. Mỗi công thức giữ riêng tên định nghĩa, công thức, tham số, đơn vị, trạng thái và nguồn dữ liệu.
- Giao diện cho phép chọn HI/CI ngay trong tham số tính toán. Khi chọn CI, ô liều kê đơn mới xuất hiện và thao tác bị chặn nếu chưa nhập liều dương hợp lệ; thiếu dữ liệu hình học/liều trả trạng thái “Chưa đủ dữ liệu”, không suy đoán và không tự sinh ngưỡng đạt/không đạt.
- Khu vực kết quả chỉ hiển thị nhãn nghiệp vụ, công thức toán học, giá trị và trạng thái; không hiển thị mã công thức, mã lần tính, chuỗi băm hoặc JSON. Không thao tác xóa hồ sơ `dailyQA` hay dữ liệu liên quan.
- Kiểm thử máy chủ DVH đạt **22/22**, kiểm thử giao diện DVH đạt **6/6**, Ruff, kiểm tra kiểu và bản dựng giao diện đạt. Bằng chứng: [chỉ số HI/CI cục bộ](docs/evidence/p17-local-hi-ci-20260915.md).
- Đây mới là lát cắt local của P17-W02/P17-W03; còn đối chiếu oracle độc lập, xác nhận cách tính CI với physicist, nguồn tiêu chí theo bệnh cảnh, kiểm thử dữ liệu thật trên staging và VERIFY/HANDOFF P17.

## P17 — tinh giản kết quả DVH cho người dùng — lát cắt cục bộ — 2026-09-15

- Tiếp tục triển khai theo kế hoạch sau khi dừng hướng xóa vĩnh viễn; hồ sơ `dailyQA`, các kết quả liên quan và điểm xu hướng không bị xóa hoặc thay đổi.
- Khu vực kết quả DVH nay chỉ hiển thị trạng thái, vùng, độ bao phủ, thời điểm và thông tin nguồn ở dạng nhãn nghiệp vụ. Mã lượt tính, dấu vết đầu vào, chuỗi băm, mã nguồn giới hạn và dữ liệu kỹ thuật không còn xuất hiện trên giao diện.
- Thay nút xuất JSON bằng “Tải bảng số liệu”; xuất bảng CSV vẫn giữ nguyên dữ liệu cần thiết cho người dùng chuyên môn mà không đưa cấu trúc kỹ thuật ra màn hình.
- Lịch sử DVH hiển thị “Lần tính 1/2/…”; nguồn giới hạn và chỉ số được dịch sang nhãn dễ hiểu. Kiểm thử giao diện đạt **44/44**, lint, kiểm tra kiểu và bản dựng sản xuất đạt.
- Đã đẩy giao diện lên staging ở bản `3833783`; kiểm tra trình duyệt có đăng nhập trên hồ sơ DVH staging xác nhận các nhãn “Tệp liều RTDOSE”, “Cấu trúc RT”, “Ảnh CT”, “Tải bảng số liệu”, “Lần tính 1/2” và không còn mã lượt tính, dấu vết đầu vào, chuỗi băm hoặc mã nguồn giới hạn. Bằng chứng: [nhãn DVH trên staging](docs/evidence/p17-staging-dvh-user-facing-labels-20260915.md). Đây chỉ là parity giao diện; P17-VERIFY/HANDOFF vẫn mở.

## P7/P8 — tinh giản nhãn dữ liệu QA và DVH — lát cắt cục bộ — 2026-09-15

- Đã dừng hướng xóa vĩnh viễn hồ sơ theo quyết định mới; dữ liệu `dailyQA`, lịch sử, tệp liên quan và điểm xu hướng được giữ nguyên.
- Bổ sung bộ nhãn nghiệp vụ dùng chung cho toàn bộ màn hình Pylinac và kho lưu trữ QA. Người dùng chỉ thấy “Ảnh kiểm tra”, “Bộ ảnh nhiều lớp”, “Nhật ký máy”, “Tệp liều RTDOSE”, “Cấu trúc RT”, “Ảnh CT” và các nhãn tương ứng; không thấy tên `.json`, `.dcm`, tên tệp gốc, chuỗi băm hoặc mã nội bộ.
- Màn hình DVH cũng đã bỏ tên tệp và chuỗi băm khỏi các lựa chọn RTDOSE, RTSTRUCT và CT. Việc lọc định dạng vẫn thực hiện nội bộ, không thay đổi dữ liệu đầu vào hay hợp đồng Pylinac.
- Kiểm thử giao diện đạt **43/43**, lint, kiểm tra kiểu và bản dựng sản xuất đạt. Bằng chứng: [nhãn dữ liệu QA theo ngôn ngữ người dùng](docs/evidence/p7-p8-user-facing-artifact-labels-20260915.md).
- Đây là lát cắt local; cần triển khai giao diện lên staging để kiểm tra lại bằng trình duyệt. P7/P8 và VERIFY/HANDOFF vẫn mở.

## P8-W02 — tinh giản đầu vào PSQA — lát cắt cục bộ — 2026-09-15

- Trang phân tích PSQA không còn đưa tệp JSON kỹ thuật vào danh sách lựa chọn. Chỉ tệp RTDOSE và dữ liệu đo đã kiểm tra hợp lệ mới được phép xuất hiện trong luồng chọn liều.
- Nhãn tệp được trình bày theo ngữ nghĩa nghiệp vụ: `Tệp liều RTDOSE`, `Tệp liều RTDOSE 1/2` và `Dữ liệu đo liều`. Tên tệp gốc, phần mở rộng JSON và mã nội bộ không xuất hiện trong lựa chọn hoặc phần tóm tắt đầu vào.
- Kiểm thử riêng đạt; bộ kiểm thử giao diện đạt **42/42**, lint và kiểm tra kiểu đạt, bản dựng sản xuất đạt. Bằng chứng: [P8 giao diện đầu vào PSQA](docs/evidence/p8-local-psqa-user-facing-inputs-20260915.md).
- Đây là lát cắt UX local cho P8-W02. P8 vẫn mở các cổng đối chiếu hình học, hàng đợi staging, lỗi phục hồi, tài nguyên lớn, kết quả 1D/2D bằng Pylinac và VERIFY/HANDOFF.

## P8-W02 — xác nhận nhãn đầu vào PSQA trên staging — 2026-09-15

- Phiên trình duyệt staging mới đã xác nhận bốn lựa chọn đầu vào được trình bày bằng ngữ nghĩa nghiệp vụ: hai tệp liều RTDOSE và hai dữ liệu đo liều. Tên `.json`, tên tệp kỹ thuật và mã nội bộ không xuất hiện.
- Các trường chênh lệch liều, DTA, ngưỡng, chuẩn hóa, phạm vi so sánh và giới hạn Gamma vẫn hiển thị; trạng thái đầu vào hợp lệ. Lần kiểm tra chỉ đọc, không tạo Gamma run mới và không thay đổi hồ sơ/tệp đã lưu.
- Bằng chứng: [nhãn đầu vào PSQA trên staging](docs/evidence/p8-staging-psqa-input-labels-20260915.md). Railway đã triển khai web thành công; API/worker không bị dựng lại vì không có thay đổi mã nguồn tương ứng.

## P2/P7 — sửa lệch schema readiness trên staging — 2026-09-15

- Kiểm tra công khai trước khi sửa phát hiện API staging trả health `200` nhưng readiness `503`: cơ sở dữ liệu đã ở migration `20260914_0023`, còn API vẫn kỳ vọng `20260913_0022`. Đây là lỗi lệch mốc cấu hình, không phải lỗi healthcheck.
- Đã đồng bộ mốc hiện hành sang `20260914_0023` trong cấu hình API, tệp môi trường mẫu, Docker Compose và kiểm thử readiness; kiểm thử health/migration đạt **22/22**. Commit sửa: `fba3add`.
- Đã đẩy đúng nhánh staging và Railway dựng lại API. Kiểm tra công khai sau triển khai đạt **16/16** ở bản `fba3addd0c4d865714c2e7d310429e8e54fd7031`; readiness trả `200/ready`, schema đúng `20260914_0023`, không có lỗi biên giới xác thực hoặc tuyến OpenAPI. Bằng chứng: [staging readiness recheck](docs/evidence/p7-staging-readiness-recheck-20260915-fba3add.json).
- Từ nay mỗi thay đổi migration phải cập nhật đồng thời migration mới nhất, `Settings.schema_revision`, `.env.example`, Docker Compose, kiểm thử health và kiểm tra public staging; không dùng lại mốc cũ chỉ vì deployment vẫn báo thành công.
- Sau khi đẩy commit `6fb3e4ea6646d46d5b60a8ede375edbca0444fec`, API và web staging đã cùng nhận đúng mã nguồn; bộ xác minh công khai đạt **16/16**, readiness `200/ready`, lược đồ `20260914_0023` và bundle web chứa thay đổi result viewer. Bằng chứng: [staging public recheck P7-W04](docs/evidence/p7-staging-public-recheck-20260915-6fb3e4e.json).

## P7-W04 — hiển thị ảnh phân tích ngay trong kết quả — lát cắt cục bộ — 2026-09-15

- `PylinacResultPanel` đã hiển thị ảnh overlay ngay trong trang kết quả thay vì chỉ mở một cửa sổ mới. Người dùng có thể mở/ẩn ảnh, xem chú thích tiếng Việt và khi chuyển sang lượt lịch sử khác thì ảnh cũ không bị dùng nhầm cho lượt mới.
- Đường tải ảnh dùng URL tạm thời của kho lưu trữ, giữ nguyên nguồn ảnh và không tạo bản sao hay thay đổi kết quả đã lưu. Lỗi tải ảnh vẫn hiện qua thông báo thao tác; trạng thái đang tải khóa nút để tránh gọi trùng.
- Kiểm thử giao diện đạt **40/40**, lint đạt, kiểm tra kiểu đạt và bản dựng sản xuất đạt. Đây là phần cải thiện result viewer của P7-W04; canvas chuỗi/đa ảnh, ROI chuyên biệt, fixture đại diện và staging vẫn còn mở.

## P7-W04 — xem trước DICOM/ZIP và chọn tâm Picket Fence — lát cắt cục bộ — 2026-09-15

- Bổ sung tuyến xem trước có xác thực cho artifact đầu vào. API kiểm tra lại phạm vi tổ chức, đọc DICOM hoặc thành viên ảnh an toàn trong ZIP, rồi chỉ trả PNG pixel; không trả thẻ DICOM, đường dẫn object storage hay mã nội bộ cho giao diện.
- Thành viên ZIP có đường dẫn tuyệt đối hoặc chứa `..` bị loại trước khi đọc; chỉ số ảnh được giới hạn; tệp tạm trên Windows được đóng trước khi Pylinac đọc để tránh lỗi khóa tệp. Giao diện dùng blob URL có thu hồi khi thay đổi tệp, vì vậy không để lại URL xem trước trong bộ nhớ trình duyệt.
- Canvas dùng chung của Starshot, Field Profile/Field Analysis và Planar Imaging nay không còn phụ thuộc URL tải xuống dạng tệp đính kèm. Picket Fence được bổ sung chọn tâm trục bằng nhấn/kéo hoặc nhập đủ tọa độ ngang/dọc; nếu chỉ nhập một tọa độ thì bị chặn trước khi gọi API.
- Kiểm thử artifact đạt **13/13**, gồm DICOM, ZIP hợp lệ, ZIP có thành viên lồng nhau, ZIP có đường dẫn nguy hiểm, chỉ số ảnh thứ hai, chỉ số ảnh thiếu và thông tin số ảnh/lát; Ruff, lint và typecheck đạt. Bằng chứng: [xem trước đầu vào Pylinac](docs/evidence/p7-local-pylinac-input-preview-20260915.json). Đây là lát cắt local của W04, chưa đóng canvas ROI chuyên biệt, ánh xạ thao tác cho từng bài, ma trận fixture, staging tương tác hoặc VERIFY/HANDOFF P7.

## P7-W04 — chọn ảnh/lát trong bộ tệp nhiều ảnh — lát cắt cục bộ — 2026-09-15

- Bổ sung tuyến thông tin xem trước để máy chủ xác định số ảnh trong DICOM nhiều khung hoặc số thành viên DICOM trong ZIP; số lượng được giới hạn ở 32 ảnh/lát đầu tiên để tránh tạo danh sách không kiểm soát. Tất cả truy cập vẫn kiểm tra phạm vi tổ chức và đọc qua kho tệp riêng.
- Vùng điều chỉnh dùng bộ chọn “Ảnh hoặc lát đang xem”. Khi đổi tệp, vùng này được tạo lại theo tệp mới, lát được đặt về ảnh đầu tiên và tọa độ đã chọn không bị giữ nhầm giữa hai tệp. Khi máy chủ không đọc được số lượng, ảnh đầu tiên vẫn có thể thử xem trước và người dùng nhận hướng dẫn nhập tọa độ bằng tay.
- Kiểm thử máy chủ đạt **13/13**, web đạt **41/41**, lint, kiểm tra kiểu và bản dựng sản xuất đạt. Cảnh báo kích thước gói JavaScript lớn hơn 500 kB vẫn là việc tối ưu riêng. Lát cắt này chưa đóng vùng ROI chuyên biệt, ánh xạ tọa độ theo từng ảnh cho các bài có nhiều ảnh, kiểm chứng tệp staging đại diện hoặc VERIFY/HANDOFF P7.

## P7-W04 — parity triển khai xem trước đầu vào trên staging — 2026-09-15

- Sau khi Railway hoàn tất cập nhật trễ của dịch vụ API, kiểm tra công khai exact-SHA đã đạt **15/15** trên staging. API và giao diện cùng nhận bản `7ed6ebf9b1064f4250efddf733446c1f5b8a9028`; health/readiness trả `200`, phiên bản đúng, lược đồ đúng `20260914_0023`, OpenAPI có tuyến xem trước DICOM/ZIP và tuyến thành viên/lời mời, các tuyến yêu cầu xác thực trả `401`, giao diện và gói web chứa đúng dấu hiệu bản phát hành.
- Bằng chứng: [kiểm tra staging P7-W04 sau khi cập nhật](docs/evidence/p7-staging-public-recheck-20260915-7ed6ebf-pass.json). Đây là cổng parity và khả năng phát hành của tuyến xem trước; chưa phải kiểm chứng tương tác chọn tâm/ROI bằng tệp staging thật cho từng nhóm bài, chưa đóng P7-W04 và chưa đóng VERIFY/HANDOFF P7.

## P7-W04 — bộ chọn ảnh/lát đã lên staging — 2026-09-15

- Bản `68d2202504c344ac2830f6ce09fba53ea2f34b2a` đã được Railway triển khai đồng bộ cho API và giao diện staging. Kiểm tra công khai exact-SHA đạt **15/15**; API `health/readiness/version`, lược đồ `20260914_0023`, OpenAPI, các tuyến yêu cầu xác thực và gói web đều đạt.
- Bằng chứng: [kiểm tra staging bộ chọn ảnh/lát](docs/evidence/p7-staging-public-recheck-20260915-68d2202.json). Đây là cổng triển khai và hợp đồng tuyến xem trước; vẫn cần kiểm tra trình duyệt có đăng nhập với bộ tệp nhiều ảnh thực tế, đối chiếu tọa độ theo từng bài và hoàn tất VERIFY/HANDOFF P7.
- Kiểm tra trình duyệt staging đã mở bài Kiểm tra sao có tệp DICOM nhiều khung: tệp báo Hợp lệ, vùng điều chỉnh hiển thị hai lựa chọn ảnh/lát `#1` và `#2`, lịch sử vẫn rỗng; không chạy phân tích và không tạo dữ liệu mới. Bằng chứng: [giao diện bộ chọn ảnh/lát staging](docs/evidence/p7-staging-multi-image-preview-ui-20260915.json). Đây mới là xác nhận hiển thị, chưa đối chiếu tọa độ theo từng lát trong phép phân tích.

## P7 — kiểm tra hồi quy sau cổng inventory — lát cắt cục bộ — 2026-09-15

- Bộ kiểm thử backend tập trung cho registry, adapter QA, hạt nhân, contrib và hiệu chuẩn đạt **tất cả kiểm thử**; riêng nhóm registry đạt 5/5. Ruff và mypy strict trên phần registry/adapter thay đổi đều đạt.
- Bộ kiểm thử giao diện đạt **12/12 tệp kiểm thử, 40/40 kiểm thử**, kiểm tra kiểu TypeScript đạt và bản dựng sản xuất hoàn tất. Bản dựng có cảnh báo kích thước gói JavaScript lớn hơn ngưỡng tối ưu, nhưng không có lỗi biên dịch hoặc lỗi kiểm thử.
- Bổ sung chặn đầu vào không phải ZIP cho CatPhan trước khi gọi Pylinac; kiểm thử CatPhan 503/700 cùng đường lỗi định dạng đạt. Bằng chứng tổng hợp: [kiểm tra P7 cục bộ](docs/evidence/p7-local-validation-20260915.json).
- Toàn bộ nhóm kiểm thử có tên `test_pylinac_*.py` hiện thu thập **104 ca** và chạy đạt **104/104**. Trong đó ma trận tệp mẫu chính thức đạt 36/36, ma trận lỗi đạt 16/16, năm bài hiệu chuẩn đạt 6/6, hai bài đóng góp đạt 2/2, nhóm Gamma đạt 6/6, nhóm hạt nhân đạt 1/1, registry đạt 5/5 và các hợp đồng adapter còn lại đạt 32/32. Lệnh kiểm tra: `python -m pytest tests/test_pylinac_*.py --no-cov -q` (trên PowerShell cần truyền danh sách tệp, không dùng ký tự đại diện trực tiếp). Cảnh báo thư viện phụ thuộc vẫn xuất hiện nhưng không có lỗi kiểm thử.
- Đây là cổng hồi quy cục bộ, không thay thế fixture chuẩn/commissioning, đối chiếu chỉ số độc lập, kiểm thử staging hoặc nghiệm thu lâm sàng; P7 vẫn mở.

## P7-W03 — ma trận lỗi phantom/chuỗi — lát cắt cục bộ — 2026-09-15

- Đã thêm `tests/test_pylinac_error_matrix.py` cho 13 capability CatPhan, ACR, Cheese, GE Helios và Quart. Tất cả đều từ chối tệp không phải ZIP bằng `PYLINAC_INPUT_FORMAT_INVALID` trước khi khởi tạo engine.
- Ba trường hợp tham số đặc thù cũng được kiểm tra: phương pháp tương phản MRI rỗng, mật độ ROI không hợp lệ và dịch lát Quart không phải số. Cả ba đều trả `PYLINAC_PARAMETER_INVALID`, không làm phát sinh lượt phân tích lỗi mơ hồ.
- Kết quả ma trận đạt **16/16**. Đây mới là phần kiểm lỗi định dạng/tham số cục bộ; lỗi nội dung DICOM, thiếu module, UID lẫn, fixture chuẩn và staging vẫn mở. Bằng chứng: [ma trận lỗi Pylinac](docs/evidence/p7-local-pylinac-error-matrix-20260915.json).

## P7-W03 — đối chiếu inventory công khai của Pylinac — lát cắt cục bộ — 2026-09-15

- Đã bổ sung `pylinac_inventory_diff()` để quét các lớp/hàm phân tích công khai của wheel Pylinac 3.47.0, loại rõ lớp nền, lớp kết quả và lớp ảnh nội bộ, rồi đối chiếu với registry RT-CONNECT. HyperSight được ghi nhận là alias tương thích của `QuartDVT`; ba phiên bản Trajectory Log dùng chung một lớp runtime nhưng vẫn là ba capability logic riêng.
- Inventory hiện đạt **61 đường dẫn biểu tượng công khai**, tương ứng **63 capability logic** trong danh mục; `missing_symbols`, `unexpected_symbols` và `unbound_symbols` đều rỗng. Kiểm thử `test_pylinac_registry.py` đạt **5/5**, Ruff và mypy strict trên tệp thay đổi đạt.
- Đây là cổng ánh xạ runtime của P7-W03, chưa đóng P7: fixture chuẩn/commissioning, đối chiếu từng chỉ số, ma trận lỗi, giao diện đầy đủ và staging vẫn cần hoàn tất. Bằng chứng: [inventory Pylinac](docs/evidence/p7-local-pylinac-inventory-20260915.json).

## P7-CAL — năm bài hiệu chuẩn gọi engine thật — lát cắt cục bộ — 2026-09-15

- Đã bổ sung kiểm thử hồi quy `apps/api/tests/test_pylinac_calibration_engine.py` cho `TG51Photon`, `TG51ElectronLegacy`, `TG51ElectronModern`, `TRS398Photon` và `TRS398Electron`. Bộ số đo tổng hợp được đưa qua đúng `execute_pylinac`; không dùng tệp ảnh hoặc bộ tính thay thế.
- Cả năm đường chạy trả các thuộc tính công khai đúng hợp đồng, không tạo overlay vì các lớp hiệu chuẩn không có ảnh phân tích. Kiểm thử thiếu `measured_pdd10` cũng được bổ sung để chặn lỗi ở biên nhập liệu thay vì để engine phát sinh lỗi mơ hồ.
- Kiểm thử thật đạt **6/6** (5 đường chạy đúng, 1 trường hợp lỗi đầu vào). Đây là `LOCAL_VERIFIED_SLICE`, không phải số liệu hiệu chuẩn/commissioning. Còn mở: dữ liệu được phê duyệt, đối chiếu độc lập kết quả, kiểm lỗi miền vật lý, kiểm thử giao diện đầy đủ và staging.
- Bằng chứng: [ma trận Pylinac P7](docs/evidence/p7-local-pylinac-demo-matrix-20260915.md).

## P7-CONTRIB — hai bài đóng góp gọi engine thật — lát cắt cục bộ — 2026-09-15

- Đã bổ sung kiểm thử hồi quy `apps/api/tests/test_pylinac_contrib_engine.py` cho `QuasarLightRadScaling` và `JawOrthogonality`, đưa cả hai bài qua đúng `execute_pylinac` của RT-CONNECT với Pylinac 3.47.0.
- Quasar dùng bản sao tạm của ảnh FC-2 chính thức, bổ sung bốn điểm chuẩn trung tâm để đáp ứng hợp đồng năm điểm của engine; Jaw dùng ảnh DICOM `RTIMAGE` hình chữ nhật tổng hợp. Cả hai đều trả kết quả không rỗng và tạo ảnh minh họa; Quasar dùng `results_data()`, Jaw dùng `results()` theo API công khai của Pylinac.
- Kiểm thử thật đạt **2/2**. Đây là `LOCAL_VERIFIED_SLICE`, không phải dữ liệu chuẩn/commissioning hay nghiệm thu lâm sàng. Còn mở: fixture đại diện, đối chiếu độc lập từng chỉ số, ma trận lỗi thiếu cạnh/ảnh không phù hợp, kiểm thử giao diện đầy đủ và staging.
- Bằng chứng: [ma trận Pylinac P7](docs/evidence/p7-local-pylinac-demo-matrix-20260915.md).

## P7-NUCLEAR — đủ chín bài hạt nhân gọi engine thật bằng fixture tổng hợp — lát cắt cục bộ — 2026-09-15

- Đã bổ sung kiểm thử hồi quy `apps/api/tests/test_pylinac_nuclear_engine.py`, dựng DICOM hạt nhân tổng hợp không có dữ liệu bệnh nhân và đưa đủ chín bài trong registry qua đúng `execute_pylinac`: tốc độ đếm cực đại, độ đồng nhất phẳng, tâm quay, độ phân giải cắt lớp, độ nhạy đơn giản, độ phân giải bốn vạch, độ phân giải bốn góc, độ đồng nhất cắt lớp và độ tương phản cắt lớp.
- Kiểm thử thật đạt **1/1**, trong đó cả chín lần gọi bộ tính đều trả structured result không rỗng; các lớp có khả năng vẽ đã tạo ảnh minh họa. Một số cảnh báo phụ thuộc hiện hành của Pylinac vẫn được giữ trong kết quả, không bị biến thành lỗi và không bị che giấu.
- Đây là `LOCAL_VERIFIED_SLICE`: đã chứng minh đường gọi engine và hợp đồng kết quả cho toàn bộ chín lớp, nhưng fixture tổng hợp không thay thế dữ liệu mẫu đại diện/commissioning. Còn mở: tệp mẫu chính thức hoặc dữ liệu được phê duyệt, đối chiếu từng chỉ số với kỳ vọng độc lập, ma trận lỗi, kiểm thử giao diện đầy đủ và staging.
- Bằng chứng: [ma trận Pylinac P7](docs/evidence/p7-local-pylinac-demo-matrix-20260915.md). Cổng tiếp theo vẫn là hoàn thiện các nhóm P7 còn thiếu fixture, sau đó chạy P07-VERIFY/HANDOFF.

## P7-PLANAR — ma trận 19 biến thể ảnh phẳng — lát cắt cục bộ — 2026-09-15

- Đã tải tệp mẫu chính thức từ kho `pylinac_demo_files` cho toàn bộ 19 biến thể ảnh phẳng và chạy từng bài qua đúng `execute_pylinac` của RT-CONNECT. Cả 19 bài đều trả structured result và ảnh overlay: Leeds TOR/Blue, Standard Imaging QC-3/QC-kV, Las Vegas/Elekta, Doselab MC2 MV/kV, SNC MV/MV12510/kV, SNC kV, PTW EPID QC, IBA Primus A, Standard Imaging FC-2, IMT L-RAD, Doselab RLf, PTW Iso-Align, SNC FSQA và ACR Digital Mammography.
- Bài IBA Primus A cần tham số `SSD = 1395 mm` theo tệp mẫu; thông tin này đã được ghi vào hợp đồng kiểm thử, không đặt làm mặc định im lặng cho dữ liệu người dùng. Kết quả/engine/overlay và số cảnh báo từng bài đã được ghi trong [ma trận tệp mẫu Pylinac](docs/evidence/p7-local-pylinac-demo-matrix-20260915.md).
- Trong cùng lát cắt, danh mục được đồng bộ tên lớp runtime thật cho ACR, CIRS, GE Helios, ảnh phẳng và hàm Gamma; phiên bản danh mục tăng lên `pylinac-3.47.0-rt-connect-1.3`, và kiểm thử registry buộc mọi tên lớp/hàm khớp symbol trong wheel đã khóa.
- Đây là `LOCAL_VERIFIED_SLICE`; P07-PLANAR vẫn mở cho đối chiếu từng module theo kỳ vọng upstream, kiểm lỗi riêng, kiểm giao diện trên staging và kiểm các nhóm P7 còn thiếu fixture.

## P7-W03 — xử lý tương thích nhãn HyperSight — lát cắt cục bộ — 2026-09-15

- Khi chạy thử trực tiếp, lớp HyperSight cũ của Pylinac không nhận đường dẫn tệp theo hợp đồng hiện hành. Vì Pylinac đã chuyển phần xử lý tương ứng sang `QuartDVT`, danh mục và bộ đăng ký nay giữ nhãn HyperSight cho người dùng nhưng gọi đúng bộ tính `QuartDVT` được hỗ trợ; không tự viết công thức thay thế và không tạo hai loại lịch sử phân tích.
- Tệp mẫu chính thức `quart.zip` đã chạy qua chính `execute_pylinac` với nhãn `QUART_HYPERSIGHT`: engine trả về `QuartDVT`, 10 nhóm chỉ số, ảnh overlay 73.206 byte và 3 cảnh báo tương thích từ thư viện. Cảnh báo được giữ lại trong kết quả, không biến thành lỗi phân tích.
- Kiểm tra đạt: ruff, mypy 53/53 tệp nguồn và 6 kiểm thử nhóm Quart/registry. Đây là `LOCAL_VERIFIED_SLICE`; vẫn cần đối chiếu từng mô-đun, kiểm thử hiển thị nhãn, kiểm tra lỗi đầu vào và staging trước khi đóng P07-QUART/P7.

## P7-W04 — hiển thị cảnh báo engine trong kết quả — lát cắt cục bộ — 2026-09-15

- Trình xem kết quả QA máy nay đọc `warning_snapshot` của từng lượt Pylinac và hiển thị riêng dưới mục “Cảnh báo từ bộ tính”, kèm nhắc người thực hiện xem xét trước khi đánh giá. Cảnh báo không bị gộp thành lỗi, không bị bỏ qua và không thay đổi kết luận do người thực hiện chọn.
- Lịch sử vẫn hiển thị cùng một snapshot của lượt đang xem; khi mở lại lượt cũ, cảnh báo đi theo đúng lượt đó. Không hiển thị mã nội bộ hoặc cấu trúc dữ liệu thô cho người dùng.
- Đây là `LOCAL_VERIFIED_SLICE`; cần bổ sung kiểm thử giao diện có cảnh báo, kiểm thử staging và kiểm tra PDF để đóng P07-W04.

## P7-W03 — sửa tương thích ảnh phẳng với Pylinac 3.47.0 — lát cắt cục bộ — 2026-09-15

- Bộ chuyển đổi ảnh phẳng đã gọi đúng `plot_analyzed_image(show=False)` của Pylinac 3.47.0. Trước đó nó gọi nhầm `plot()`, khiến `LeedsTOR` phân tích được nhưng bị báo lỗi khi dựng ảnh minh họa vì lớp này không có phương thức đó.
- Kiểm tra engine thật bằng tệp mẫu chính thức đã đạt: `LeedsTOR` với `leeds.dcm` và `StandardImagingFC2` với `fc2.dcm`; cả hai trả structured result và ảnh overlay. Kiểm thử adapter đã được cập nhật để khóa đúng hợp đồng renderer mới.
- Đây là `LOCAL_VERIFIED_SLICE`; 17 biến thể ảnh phẳng còn lại vẫn cần fixture riêng, đối chiếu kết quả/overlay, kiểm thử lỗi và staging. Cảnh báo tương thích từ dependency không được che khuất lỗi phân tích và không được dùng làm bằng chứng nghiệm thu lâm sàng.

## P7-W03 — đồng bộ phiên bản danh mục trong API — lát cắt cục bộ — 2026-09-15

- API registry nay lấy trực tiếp hằng phiên bản từ danh mục thay vì lặp lại một chuỗi riêng. Sau khi CatPhan700 nâng danh mục lên 1.2, tuyến khả năng Pylinac và bản tóm tắt phát hành cùng trả đúng `pylinac-3.47.0-rt-connect-1.2`.
- Kiểm thử registry đã xác nhận phiên bản API khớp hằng danh mục; không thay đổi số bài, phép tính hoặc dữ liệu staging.
- Đây là sửa đồng bộ hợp đồng `LOCAL_VERIFIED_SLICE`; P7-W03 vẫn mở vì còn ma trận fixture và đối chiếu engine thật cho các nhóm chưa có dữ liệu.

## P7-W03 — bổ sung CatPhan700 theo inventory Pylinac 3.47.0 — lát cắt cục bộ — 2026-09-15

- Đối chiếu các lớp phân tích công khai của mô-đun CT trong wheel `pylinac 3.47.0` phát hiện `CatPhan700` chưa có trong danh mục dù là một biến thể phantom cụ thể. Đã bổ sung bài này vào danh mục, runtime registry, adapter CatPhan, kiểm tra đầu vào ZIP, tuyến giao diện và điều hướng.
- Danh mục hiện hành **1.2** là **64 bài**: 1 bài nhập số đo và 63 bài Pylinac. CatPhan hiện gồm 503, 504, 600, 604 và 700. Đây là bổ sung phạm vi; chưa có fixture CatPhan700 để tuyên bố engine đã chạy thật.
- Kiểm tra local đã xác nhận registry phân giải **63/63** liên kết Pylinac, danh mục không trùng khóa và giao diện vẫn dựng được. Cổng hợp đồng tài liệu đạt `passed=true`, 0 lỗi; kiểm thử phủ định đạt 15/15; hồi quy máy chủ đầy đủ đạt 100%. P7-W03/P07-CT/P07-VERIFY vẫn mở cho đến khi có fixture, đối chiếu kết quả từng mô-đun và kiểm chứng staging.

## P7-W04 — canvas thao tác tâm dùng chung — lát cắt cục bộ — 2026-09-15

- Khung điều chỉnh ảnh dùng chung đã nhận thêm chế độ tọa độ chuẩn hóa 0–1 cho Field Profile/Field Analysis và được dùng ở chế độ chọn vị trí thủ công; Planar Imaging dùng cùng khung ở chế độ tọa độ điểm ảnh để chọn tâm phantom. Starshot tiếp tục dùng cùng thành phần cho tâm bắt đầu.
- Giao diện chỉ mở khung ảnh khi bài có tệp ảnh đã chọn; các bài không cần tệp không xuất hiện vùng tải hoặc vùng chọn ảnh. Mọi điểm chọn được đồng bộ hai chiều với ô nhập và chỉ được đưa vào lần phân tích mới, không sửa kết quả đã lưu.
- Cổng local đạt: kiểm tra kiểu, lint, 40/40 bài kiểm thử giao diện và bản dựng sản xuất. Cảnh báo kích thước gói JavaScript vẫn là cảnh báo đã biết.
- Đây là `LOCAL_VERIFIED_SLICE`; P07-W04 vẫn mở vì chưa có canvas cho chuỗi/đa ảnh, ROI/lớp ảnh chuyên biệt và chưa có kiểm chứng thao tác thật trên staging. Không coi đây là nghiệm thu P7.

## P8-W02/W03 — cấu hình Gamma và hủy hàng chờ — lát cắt cục bộ — 2026-09-15

- API bổ sung tuyến hủy Gamma theo phạm vi đơn vị. Chỉ lượt `QUEUED` hoặc `RETRYING` mới được hủy; lượt đang chạy không bị dừng cưỡng bức để giữ nguyên cơ chế thuê và rào chắn worker. Hủy được ghi thành trạng thái kết thúc `CANCELLED`, lưu cảnh báo cho người dùng, đánh dấu các ý định gửi tương ứng là đã hủy và ghi nhật ký thao tác.
- Worker kiểm tra trạng thái trước khi nhận thông điệp, vì vậy thông điệp Redis cũ của lượt đã hủy được xác nhận an toàn mà không tạo lượt chạy, kết quả hoặc lần thử mới. Lượt đã hủy được trả lại ổn định khi người dùng mở lại lịch sử.
- Biểu mẫu Gamma hiển thị thêm phép nội suy đang được khóa ở “trên lưới đã kiểm tra”, số khoảng biểu đồ và hệ số tinh chỉnh một chiều. Hệ số chỉ truyền vào Pylinac Gamma 1D; biểu đồ dùng số khoảng đã chọn; không bật nội suy hoặc đổi lưới âm thầm.
- Cổng local đạt: kiểm thử API Gamma và worker tập trung **26/26**, Ruff, kiểm tra kiểu, lint giao diện, kiểm thử giao diện **40/40**, kiểm tra kiểu và bản dựng sản xuất. Cảnh báo kích thước gói JavaScript vẫn là cảnh báo đã biết.
- Đây là `LOCAL_VERIFIED_SLICE`; P08-W02, P08-W03, P08-VERIFY và P08-HANDOFF vẫn mở vì chưa có kiểm chứng hàng đợi thật trên staging, chạy lại sau lỗi, hủy đồng thời với worker và đối chiếu độc lập toàn bộ kết quả.

## P7-W01 — QA nhập số đo — lát cắt cục bộ — 2026-09-15

- Đã hoàn thiện bảng nhập số đo theo quy trình: giữ các tiêu chí `RANGE`, `MAX`, `MIN`, `ABSOLUTE_DEVIATION`, `PERCENT_DEVIATION` và `NA`; cho phép đánh dấu không áp dụng kèm lý do; thêm ghi chú riêng cho từng số đo; kết luận của bộ tiêu chí vẫn tách khỏi đánh giá của người thực hiện.
- Quy trình mẫu và nhãn chính đã được dịch sang tiếng Việt. API từ chối số đo không nằm trong quy trình đang dùng để tránh lưu hoặc đưa dữ liệu ngoài hợp đồng vào kết quả/xu hướng.
- Cổng local đạt: **9/9** kiểm thử `test_machine_qa.py`, Ruff, kiểm tra kiểu, lint và **39/39** bài kiểm thử giao diện. Bằng chứng: [QA nhập số đo](docs/evidence/p7-local-manual-machine-qa-20260915.md).
- Đây là `LOCAL_VERIFIED_SLICE`; chưa nghiệm thu staging và không làm thay đổi tình trạng các gói Pylinac còn thiếu fixture chuẩn, canvas dùng chung, ma trận kết quả và P7-VERIFY/HANDOFF.

Tài liệu hiện hành: `business-analysis.md` v1.3,
`technical-specification.md` v2.3 và `plan.md` v5.3 — mốc UX1.3.
`docs/history/pre-ux-20260912/specification.md` v1.29 là hợp đồng kế thừa, không ghi đè yêu cầu mới.

## P7-W03 — chín bài Nuclear của Pylinac — lát cắt hợp đồng và engine local — 2026-09-15

- Commit `dad50d9593f5a4fcdd22140d6892a5716691ec00` đã bổ sung đủ chín lớp Nuclear công khai vào bộ điều hợp và giao diện: tốc độ đếm cực đại, độ đồng nhất phẳng, tâm quay, độ phân giải cắt lớp, độ nhạy đơn giản, độ phân giải bốn vạch, độ phân giải bốn góc, độ đồng nhất cắt lớp và độ tương phản cắt lớp.
- Mỗi bài có biểu mẫu riêng, kiểm tệp DICOM, kiểm số lượng tệp, kiểm miền tham số và ánh xạ kết quả từ `results_data()` của đúng lớp Pylinac. `SimpleSensitivity` nhận ảnh phantom và ảnh nền tùy chọn; không dùng ảnh nền ngầm. Các bài có ảnh minh họa gọi phương thức vẽ công khai của Pylinac; lỗi riêng ở bước vẽ được lưu thành cảnh báo, không làm mất kết quả đo.
- Cổng local đạt: 26/26 kiểm thử API nhóm Pylinac, ruff trên các tệp thay đổi, mypy 52/52 tệp nguồn, lint giao diện, kiểm tra kiểu và bản dựng sản xuất. Bằng chứng: [P7 hợp đồng chín bài hạt nhân](docs/evidence/p7-local-nuclear-contract-20260915.json).
- Kiểm thử hồi quy mới `apps/api/tests/test_pylinac_nuclear_engine.py` đã dựng fixture DICOM tổng hợp không có dữ liệu bệnh nhân và gọi thật đủ chín lớp qua `execute_pylinac`, đạt **1/1**; các lớp có khả năng vẽ đã tạo ảnh minh họa. Đây là `LOCAL_VERIFIED_SLICE` cho đường chạy engine và hợp đồng kết quả, chưa phải nghiệm thu bằng dữ liệu máy: fixture DICOM chuẩn/commissioning, đối chiếu từng lớp, ma trận lỗi, kiểm thử giao diện và staging vẫn mở. P7-W03, P07-NUCLEAR, P07-VERIFY và P07-HANDOFF vẫn mở.

## P7-W03 — hai bài One-Offs/Contrib của Pylinac — lát cắt hợp đồng và engine local — 2026-09-15

- Commit `2a46f67cf60f28cda541d1d513f95403a15c4509` đã bổ sung hai bài đóng góp công khai: `QuasarLightRadScaling` và `JawOrthogonality`. Cả hai được mở trực tiếp từ danh mục QA, nhận một ảnh, lưu lịch sử và cho phép người thực hiện đánh giá riêng.
- Quasar có biểu mẫu `normalize`, đảo ảnh, FWXM và ngưỡng cạnh biên; adapter gọi đúng `analyze()` và `results_data()`. Jaw không có `results_data()` trong Pylinac 3.47.0 nên adapter gọi đúng `analyze()` và `results()`, sau đó lấy ảnh từ `plot_analyzed_image()`. Không có logic thay thế hoặc kết luận tự động ngoài kết quả engine.
- Cổng local đạt: 28/28 kiểm thử API nhóm Pylinac, ruff trên các tệp thay đổi, mypy 52/52 tệp nguồn, lint giao diện, kiểm tra kiểu và bản dựng sản xuất. Bằng chứng: [P7 hợp đồng hai bài đóng góp](docs/evidence/p7-local-contrib-contract-20260915.json).
- Kiểm thử hồi quy `apps/api/tests/test_pylinac_contrib_engine.py` đã đưa cả hai lớp qua `execute_pylinac` bằng fixture tổng hợp không có dữ liệu bệnh nhân và đạt **2/2**; Quasar dùng bản sao tạm của ảnh FC-2 chính thức có bổ sung bốn điểm chuẩn, còn Jaw dùng ảnh DICOM `RTIMAGE` hình chữ nhật. Đây là `LOCAL_VERIFIED_SLICE` cho đường gọi engine và hợp đồng kết quả, chưa phải dữ liệu chuẩn/commissioning. Chưa có đối chiếu độc lập trên fixture đại diện, ma trận lỗi đầy đủ hoặc kiểm chứng staging. P07-CONTRIB, P7-W03, P07-VERIFY và P07-HANDOFF vẫn mở.

## UX1.3 — Thư viện nội bộ/cộng đồng và triển khai tuần tự — 2026-09-13

- Phạm vi đợt: hoàn thiện nền giao diện UX1.3 theo kế hoạch tuần tự; tài liệu, thiết kế Google Stitch và dọn tệp thừa được giữ làm đầu vào, không thay dữ liệu Railway/Supabase trong slice này.
- Bài nội bộ chỉ thành viên đơn vị đọc/sửa; thành viên ngang quyền. Bản chia sẻ cộng đồng có nội dung và tệp được chọn rõ ràng; người dùng đã đăng nhập, kể cả chưa có đơn vị, được đọc. Sửa nháp không sửa bản cộng đồng; thu hồi chặn truy cập mới cả bài, PDF, hình, tìm kiếm và dấu trang.
- Bổ sung soạn trực quan/tự lưu/phiên bản/xung đột, PDF và trích văn bản, tìm tiếng Việt không dấu, nguồn theo bệnh viện, lưu bài, lưu trữ, thùng rác 30 ngày và khôi phục về nội bộ.
- Giữ pylinac là bộ tính chính thức cho đủ danh mục, giao diện tham số/chọn tâm thuộc RT-CONNECT; không rút P7 còn ba ví dụ.
- Kế hoạch có 21 giai đoạn P0–P20 theo đúng thứ tự, 264 tình huống nghiệm thu. Mỗi giai đoạn có trình tự triển khai, luồng thao tác, gói việc, trường hợp đúng/lỗi/phục hồi, kiểm chứng và bàn giao. Không mở giai đoạn sau khi giai đoạn trước chưa đóng.
- Thiết kế mới và kết quả đối chiếu ghi tại [sổ thiết kế thư viện](docs/design/knowledge-library.md); không lấy số liệu/nội dung minh họa của Stitch làm nguồn chuyên môn.
- Đã chuyển đặc tả cũ khỏi thư mục gốc vào lịch sử, sửa các liên kết đang có hiệu lực và thêm bản đồ tài liệu vào README. Bản lưu nghiệp vụ/kỹ thuật/kế hoạch cũ và bằng chứng triển khai vẫn được giữ nguyên.
- Dọn tệp: đã bỏ bản đặc tả trùng nguồn ở thư mục gốc bằng cách chuyển vào lịch sử, không mất nội dung. Các thư mục nhớ đệm `.mypy_cache`, `.pytest_cache`, `.ruff_cache` đã nhận diện là có thể tạo lại nhưng thao tác xóa bị môi trường chặn; chúng vẫn được giữ, không ghi nhận đã xóa. Không xóa mã, tệp khóa, `.env`, mẫu thử hoặc bằng chứng còn được tham chiếu.
- Kiểm chứng UX1.3: đạt 516/516 điều kiện, 21 giai đoạn/264 tình huống được mô tả; 15/15 phép thử bộ kiểm tài liệu đạt, gồm bỏ phụ thuộc giai đoạn trước. Bằng chứng: `docs/evidence/ux1-3-planning-contract-20260913.json`. Đây không phải 264 kiểm thử ứng dụng đã chạy. Kiểm 41 liên kết cục bộ không có liên kết hỏng; phần thân đặc tả đã chuyển đối chiếu khớp bản Git.
- Stitch đã tạo năm màn: nội bộ, cộng đồng/tra cứu, soạn/chia sẻ, đọc bài/PDF, bài của đơn vị/thùng rác. Cả ba lượt sửa năm màn được dịch vụ xác nhận; kiểm cuối bằng lấy lại màn và tải mã mới vẫn nhận nội dung cũ. Sổ thiết kế ghi từng điểm chưa đồng bộ; chỉ coi năm bố cục là bản thiết kế ban đầu, chưa nghiệm thu giao diện hoặc bản sửa xuất từ Stitch.
- P0 hoàn thành gói yêu cầu/tài liệu và bàn giao hướng thiết kế; kiểm giao diện thật thuộc P11. Không coi bố cục Stitch là chứng minh chức năng đã chạy. Việc xóa nhớ đệm bị chặn được ghi rõ, không ảnh hưởng hợp đồng triển khai.
- P1 đã đạt `LOCAL_VERIFIED` trên HEAD `7a7e4ec`: API 204/204, web 9 tệp/20 phép thử, lint/typecheck/build, migration SQL và Compose full smoke đều đạt. Evidence: `docs/evidence/p1-foundation-recheck-20260913-7a7e4ec.json`. Đã sửa bộ kiểm manifest để dirty working tree tạo gate đúng và làm script P1 fail-closed; CI đã kiểm hợp đồng UX1.
- P2 đã đạt `STAGING_VERIFIED` và mở P3: effective settings, psycopg 3/Alembic, CORS/Supabase/Auth session, health/readiness, web/API exact SHA parity và organization readback staging đều đạt. Evidence: [effective settings](docs/evidence/p2-railway-effective-settings-20260913.json), [public recheck trước triển khai API](docs/evidence/p2-staging-public-recheck-20260913.json), [public recheck sau triển khai API](docs/evidence/p2-staging-public-recheck-20260913-after-api-deploy.json), [authenticated browser](docs/evidence/p2-staging-authenticated-browser-20260913-7a7e4ec.json).
- Production hiện chỉ có API nền cũ, chưa có web/worker/Auth packet đồng bộ; evidence: [production foundation gap](docs/evidence/p2-production-foundation-gap-20260913.json). Đây là cổng phát hành phải hoàn tất ở P19, không chặn P3–P18 xây dựng và kiểm thử trên local/staging.
- P3 đã bắt đầu và đạt `LOCAL_VERIFIED_SLICE` với giao diện gọn, điều hướng năm mục và tiếng Việt ở luồng nền; giữ nguyên cổng production cho P19.
- P4 đã đạt `STAGING_VERIFIED_AND_HANDOFF_COMPLETE`: thẻ đơn vị, cơ sở/máy cạnh nhau, thành viên/lời mời thu gọn; lint, typecheck, Vitest **27/27**, production build PASS, hồi quy API tổ chức và kho QA đạt; lưu trữ/khôi phục máy giữ nguyên lịch sử và tệp cũ. Kiểm trực tiếp staging bằng hai phiên đã xác nhận đọc chung, thao tác ngang quyền và xung đột khi lưu cùng phiên bản; lời mời/mã mời và mục lưu trữ/khôi phục theo phiếu kiểm chứng đã được người dùng nghiệm thu. Evidence tổng hợp mới nhất: [P4 final acceptance](docs/evidence/p4-staging-final-acceptance-20260913-2257.json), [đọc lại hai phiên](docs/evidence/p4-staging-two-session-readback-20260913-2250.json), [phiếu kiểm chứng staging](docs/runbooks/p4-kiem-chung-hai-tai-khoan-staging.md). P4 đã đóng; P5 là bước tiếp theo duy nhất theo thứ tự.
- Sau khi rà soát trải nghiệm thực tế, trang QA máy đã được tinh giản ở commit mới nhất của nhánh: toàn bộ nhãn hiển thị là tiếng Việt, không còn hiện mã bài/tệp, mã kiểm tra tệp hoặc trạng thái kỹ thuật thô; loại bài kiểm tra và chu kỳ dùng nhãn thân thiện nhưng vẫn gửi đúng giá trị nội bộ. Luồng kiểm tra tệp và phân tích liều cũng đã được Việt hóa; các trạng thái bài kiểm tra `OPEN`, `IN_REVIEW` và `CANCELLED` cũng đã có nhãn tiếng Việt. Kiểm thử giao diện đạt **27/27**, lint/typecheck/build PASS; sau khi đồng bộ API, web và tiến trình nền staging, public verifier đạt **16/16** với cùng commit và schema `20260911_0020`. Đây là nền giao diện đã được P4 nghiệm thu; phần nghiệp vụ QA đầy đủ tiếp tục được triển khai từ P5–P10.
- Đã sửa luồng tài khoản chưa có đơn vị: máy chủ có tuyến tra cứu lời mời đang chờ theo email Supabase đã xác thực, giao diện tự hiển thị tên đơn vị và nút “Tham gia”, đồng thời có ô dán mã mời dự phòng. Mã bản ghi nội bộ không hiển thị; thao tác tham gia không đi qua tuyến tạo đơn vị. Kiểm thử mới: API tổ chức **18/18**, giao diện **29/29**, lint/typecheck/build PASS. Kiểm trực tiếp staging, mã mời dự phòng và các trường hợp lời mời đã được người dùng nghiệm thu; bằng chứng tổng hợp ở [P4 final acceptance](docs/evidence/p4-staging-final-acceptance-20260913-2257.json). P4 đã đóng.
- Kiểm chứng staging bổ sung vòng đời máy: lưu trữ `Synthetic QA Linac` làm máy biến mất khỏi bộ chọn bài mới nhưng không làm mất hai bài QA lịch sử hoặc tệp RTDOSE; khôi phục làm máy xuất hiện lại và lịch sử vẫn nguyên vẹn. Bằng chứng: [lưu trữ/khôi phục máy staging](docs/evidence/p4-staging-machine-archive-restore-20260913-392f4d9.json). Đây là lát cắt một phiên, chưa thay cho kiểm hai phiên độc lập, mã mời dự phòng và bàn giao P4.
- Bộ kiểm thử API đầy đủ chạy trong container Docker có đủ phụ thuộc và Git đạt **207/207**, không có bài thất bại; bằng chứng: [API regression Docker](docs/evidence/p4-api-regression-docker-20260913-4d17189.json). Lần chạy dùng kho mã chỉ đọc và tắt bao phủ mã nguồn để tránh ghi tệp kiểm thử, nên đây là kiểm hồi quy cục bộ, không thay cho các cổng staging của P4.
- Bổ sung hồi quy giao diện cho luồng lời mời: nếu không tải được danh sách lời mời thì vẫn hiện ô nhập mã; mã không hợp lệ hiển thị lỗi và không tạo đơn vị mới. Toàn bộ web đạt **12/12 tệp, 31/31 bài**, lint và typecheck PASS; bằng chứng: [web invitation fallback](docs/evidence/p4-web-invite-fallback-20260913.json). Đây là kiểm thử cục bộ, chưa thay cho kiểm hai danh tính thật trên staging.
- Kiểm chứng trực tiếp hai phiên staging ngày 2026-09-13: cả hai phiên đọc được cùng đơn vị, cơ sở, máy và hai bài QA lịch sử; khi phiên A lưu trước, phiên B lưu dữ liệu cũ nhận lỗi xung đột và giữ nội dung đang nhập; tên máy đã được khôi phục về giá trị ban đầu. Người dùng xác nhận hai phiên lần lượt là `trinhhuyvu@gmail.com` và `quangmacdang@gmail.com`; giao diện không hiển thị email phiên hiện tại nên bằng chứng không ghi mã phiên hay mã truy cập. Bằng chứng: [đọc lại hai phiên staging](docs/evidence/p4-staging-two-session-readback-20260913-2250.json). Sau đó người dùng xác nhận đã nghiệm thu hài lòng luồng mã mời và mục lưu trữ/khôi phục; P4 được đóng ở `docs/evidence/p4-staging-final-acceptance-20260913-2257.json`.
- P5 đã được triển khai ở mức `LOCAL_VERIFIED_SLICE`: danh mục có 63 bài theo sổ pylinac, trong đó bài nhập số đo là bài sẵn sàng đầu tiên và các bài còn lại hiện rõ nhưng bị khóa cho đến khi có bộ tích hợp tương ứng; giao diện danh mục, bắt đầu bài, lịch sử, hồ sơ cũ chưa phân loại, lưu trữ/khôi phục/thùng rác và xóa vĩnh viễn đã nối với API thật. Migration `20260913_0021` và `20260913_0022` đã nâng thành công; nhóm P5 đạt 28/28, ruff đạt, giao diện đạt typecheck/lint, kiểm tra riêng QA 3/3 và bản dựng sản xuất. Toàn bộ bộ kiểm thử giao diện hiện có 29/31 bài đạt; 2 bài lời mời tổ chức lỗi điều hướng và không thuộc thay đổi P5 lần này. Bằng chứng: [P5 kiểm tra cục bộ](docs/evidence/p5-local-verification-20260913.json). Ba bài kiểm thử bản kê phát hành vẫn không chạy trong ảnh Docker vì ảnh không có Git; đây là giới hạn môi trường, không được ghi thành đạt. P5 chưa đóng và P6 chưa mở cho đến khi có nghiệm thu staging.
- Sau phản hồi giao diện ngày 2026-09-14, trang QA máy đã chuyển sang danh mục thẻ hiện trực tiếp theo nhóm thay cho danh sách chọn dài; vẫn hiện đủ 63 bài, khóa bài chưa sẵn sàng và có tìm nhanh. Khu vực tệp đầu vào chỉ hiện với bài cần tệp; lối tắt phân tích liều chỉ hiện với bài PSQA/liều hoặc hồ sơ có RTDOSE/RTSTRUCT hợp lệ; bài nhập số đo không còn bị kèm vùng tệp. Bố cục thư mục/lịch sử được mở rộng theo chiều ngang khả dụng. Trang Công cụ sinh học bỏ thẻ thư viện kiến thức đặt nhầm, giảm khoảng trắng, Việt hóa nhãn và không còn hiển thị nội dung giả dạng JSON. Kiểm tra riêng trang QA đạt 3/3; typecheck, lint và bản dựng sản xuất đạt. Toàn bộ giao diện hiện còn 2 ca kiểm thử lời mời tổ chức lỗi điều hướng (`SessionErrorPage`), không liên quan đến ba tệp giao diện của thay đổi này; cần xử lý riêng trước khi ghi nhận lại toàn bộ bộ kiểm thử giao diện.
- Kiểm chứng giao diện xác thực trên staging ở bản `544a40c1a6ca6697f8b951002411ed97484ff59d`: danh mục QA 63/63 và tìm “hàng rào lá” còn 1/63; hồ sơ cũ chưa phân loại vẫn mở được; hồ sơ tổng hợp `P6 Staging Upload Smoke` đã được lưu trữ, xuất hiện trong thùng rác, khôi phục và xuất hiện lại trong lịch sử. Bài nhập số đo không hiện vùng tệp/phân tích liều. Trang Công cụ sinh học hiển thị gọn năm công cụ và không còn thẻ thư viện kiến thức. Bằng chứng: [P5 giao diện staging](docs/evidence/p5-staging-authenticated-ui-20260914.json). P5 vẫn chưa đóng vì chưa chạy xóa vĩnh viễn có kiểm soát và kiểm lỗi mạng/tiến trình nền trên staging.
- Sau khi ổn định môi trường chạy kiểm thử bằng tiến trình tách riêng và chờ đúng các cập nhật bất đồng bộ, toàn bộ kiểm thử giao diện đạt **12/12 tệp, 31/31 bài**; typecheck, lint và bản dựng sản xuất tiếp tục đạt. Đây là bằng chứng cục bộ cho bản mã hiện tại, không thay thế các cổng nghiệm thu staging còn mở của P5.
- Cổng phụ thuộc pylinac ngày 2026-09-14: `pylinac==3.47.0` import được trong môi trường API; khóa cài đặt đã bổ sung toàn bộ phụ thuộc trực tiếp/phụ trợ, `pydicom` đồng bộ về `2.4.5` theo yêu cầu của pylinac, `pip check` và cài đặt thử từ khóa đều đạt. Dockerfile API dựng thành công; staging API nhận đúng commit `df4210b` và trả health/readiness tốt. Toàn bộ API, ruff, mypy nghiêm ngặt và web 32/32 tiếp tục đạt. Bằng chứng: `docs/evidence/p5-pylinac-dependency-recheck-20260914.json`. Đây là kiểm tra chuẩn bị cho P7, chưa phải bằng chứng các adapter/bài QA pylinac đã chạy; P5 vẫn giữ các cổng staging xóa vĩnh viễn, lỗi mạng và tiến trình nền.
- Cập nhật P5 sau khi kiểm tra lại cơ chế xóa: commit `57c08e7` làm yêu cầu xóa vĩnh viễn có tính lặp an toàn; nếu yêu cầu được gửi lại sau khi lần đầu thành công, máy chủ trả trạng thái đã xóa trong đúng đơn vị thay vì báo lỗi không tìm thấy. Kiểm thử kho QA riêng và toàn bộ API đều đạt; ruff và mypy đạt. Bằng chứng: [xóa lặp an toàn cục bộ](docs/evidence/p5-purge-idempotency-local-20260914.json). Đây vẫn chỉ là bằng chứng cục bộ; chưa thay cho kiểm thử lỗi mạng, tiến trình nền và thao tác xóa có kiểm soát trên staging.
- Commit `aaada4e` tiếp tục làm sạch trang chi tiết nhập số đo: toàn bộ tiêu đề, trạng thái, bảng chỉ số, nguồn quy trình và thông báo lỗi hiển thị bằng tiếng Việt; mã lượt, mã chỉ số và cấu hình dạng JSON không còn được đưa ra giao diện. Kiểm thử giao diện vẫn đạt **12/12 tệp, 32/32 bài**, typecheck và lint đạt. Đây là hoàn thiện trải nghiệm P5/P7 nền, chưa phải bằng chứng bộ tích hợp pylinac đã chạy.
- Bổ sung hồi quy bảo vệ xóa tại commit kiểm thử tiếp theo: hồ sơ có tác vụ Gamma đang chờ cũng bị từ chối xóa vĩnh viễn và vẫn giữ nguyên; nhóm kiểm thử kho QA đạt **8/8**, toàn bộ API, ruff và mypy đạt. Bằng chứng đã cập nhật trong [xóa lặp an toàn cục bộ](docs/evidence/p5-purge-idempotency-local-20260914.json). Đây vẫn là kiểm thử cục bộ, không thay cho kiểm tra tác vụ nền thật trên staging.
- Kiểm chứng staging có thể hoàn tác ngày 2026-09-14: hồ sơ tổng hợp `P6 Staging Upload Smoke` được lưu trữ, đọc lại trong thùng rác, khôi phục và xuất hiện lại trong danh sách chính; các liên kết đầu vào vẫn còn. Không thực hiện xóa vĩnh viễn vì đó là thao tác xóa dữ liệu cần xác nhận ngay trước hành động. Bằng chứng: [vòng đời staging có thể hoàn tác](docs/evidence/p5-staging-reversible-lifecycle-20260914.json). P5 vẫn mở các cổng từ chối hồ sơ có liên kết, xóa hồ sơ thử riêng không liên kết, lỗi mạng và tiến trình nền.
- Sau khi bổ sung kiểm thử lỗi mất mạng cho `ApiClient`, toàn bộ giao diện đạt **12/12 tệp, 33/33 bài**; typecheck, lint và bản dựng sản xuất đạt. Bản dựng còn cảnh báo kích thước gói JavaScript lớn hơn ngưỡng khuyến nghị, nhưng không có lỗi biên dịch hay kiểm thử.
- Bổ sung kiểm thử trạng thái tác vụ Gamma đang chạy: bộ kiểm tra purge vẫn đếm đây là liên kết của hồ sơ, nên không cho xóa vĩnh viễn khi worker đang giữ lượt xử lý. Nhóm `test_gamma_worker.py` đạt **7/7**, nhóm `test_qa_archive.py` đạt **8/8**, ruff đạt; bằng chứng: [xóa và liên kết cục bộ](docs/evidence/p5-purge-idempotency-local-20260914.json). Cổng staging tương ứng vẫn mở.
- Hồi quy toàn bộ sau thay đổi phạm vi thùng rác: toàn bộ bộ kiểm thử máy chủ chạy đạt; giao diện đạt **12/12 tệp, 34/34 bài**, kiểm tra kiểu đạt và không phát sinh lỗi hồi quy. Cảnh báo duy nhất của bản dựng là kích thước gói JavaScript lớn hơn ngưỡng khuyến nghị, đã được ghi nhận như việc tối ưu hiệu năng riêng.
- Kiểm chứng staging xóa vĩnh viễn có kiểm soát ngày 2026-09-14: đã tạo một hồ sơ thử nghiệm tổng hợp riêng, không tải tệp và không chạy phân tích; sau khi lưu trữ, xác nhận xóa vĩnh viễn đúng hồ sơ đó. Tải lại trang rồi mở thùng rác xác nhận hồ sơ tạm không còn; `dailyQA` vẫn còn vì máy chủ đã từ chối đúng do có dữ liệu liên quan; P6 Staging Upload Smoke và P11 E2E Synthetic QA 20260910 B7C3 vẫn còn. Evidence: [xóa hồ sơ không liên kết trên staging](docs/evidence/p5-staging-unreferenced-purge-20260914.json). Đây là lát cắt staging đã PASS, chưa đóng P5: các kiểm tra từ chối hồ sơ có liên kết khi thao tác thật, tiến trình nền và toàn vẹn dữ liệu sau toàn bộ vòng đời vẫn mở; lỗi mạng đã đạt cho lát cắt đọc.
- Sửa lỗi hiển thị thùng rác ở P5: khi máy chủ trả cả hồ sơ đang mở và đã lưu trữ cho truy vấn có `include_archived`, API nay hỗ trợ bộ lọc `archived_only` và giao diện truyền bộ lọc này khi mở thùng rác; thùng rác chỉ hiện hồ sơ đã lưu trữ và đếm đúng số dòng hiển thị, kể cả khi dữ liệu vượt giới hạn một trang. Kiểm thử máy chủ đạt **8/8**, kiểm thử giao diện đạt **4/4**, typecheck, Ruff, mypy và bản dựng sản xuất đạt (còn cảnh báo kích thước gói JavaScript đã biết). Bản web/API `336be85` đã lên staging; kiểm tra trực tiếp xác nhận danh sách chính tải được, thùng rác chỉ hiện `dailyQA` đã lưu trữ, không hiện P6/P11 đang mở. Evidence: [lọc thùng rác staging](docs/evidence/p5-staging-trash-filter-20260914.json).
- Bổ sung thao tác nhiều mục cho lịch sử QA ở bản `75f86df`: chọn từng bài hoặc tất cả bài đang hiển thị; đưa vào thùng rác, khôi phục và xóa vĩnh viễn. Xóa vĩnh viễn nhiều bài chỉ hỏi một lần với tên từng bài; mỗi yêu cầu vẫn đi qua kiểm tra liên kết riêng và giao diện nêu rõ bài đã xử lý/chưa xử lý cùng lý do. Kiểm chứng cục bộ đạt **5/5** bài riêng cho QA, **4/4** bài kiểm tra máy khách, toàn bộ giao diện **12/12 tệp, 36/36 bài**, typecheck, lint và bản dựng sản xuất đạt. Evidence: [thao tác nhiều mục cục bộ](docs/evidence/p5-local-batch-history-actions-20260914.json). Chưa thao tác nhiều mục trên staging; P5-VERIFY/P5-HANDOFF vẫn mở.
- Bổ sung bài kiểm thử riêng cho trường hợp báo cáo trỏ về hồ sơ QA: hồ sơ đã lưu trữ nhưng còn báo cáo bị máy chủ từ chối xóa với `QA_CASE_REFERENCED`, số lượng báo cáo được nêu đúng và hồ sơ vẫn giữ nguyên. Nhóm `test_qa_archive.py` hiện đạt **9/9**; bằng chứng: [bảo vệ tham chiếu báo cáo](docs/evidence/p5-local-report-reference-guard-20260914.json). Đây là bổ sung cục bộ; kiểm chứng staging tương ứng vẫn cần xác nhận ngay trước thao tác xóa.
- Bổ sung xem trước xóa vĩnh viễn ở API và giao diện tại commit `a2245f1`: bước đọc chỉ trả tên bài, cơ sở, máy, thời điểm, trạng thái lưu trữ và nhóm liên kết; bài còn liên kết bị chặn trước khi hiện hộp xác nhận, bài đủ điều kiện mới được hỏi xác nhận đầy đủ. Máy chủ vẫn kiểm tra lại ở yêu cầu xóa. Kiểm thử kho QA đạt **9/9**, giao diện đạt **12/12 tệp, 37/37 bài**, typecheck, lint, bản dựng, Ruff và mypy đều đạt. Bằng chứng: [xem trước xóa cục bộ](docs/evidence/p5-local-purge-preview-20260914.json). Thao tác staging chưa thay đổi dữ liệu.
- Kiểm chứng xem trước xóa chỉ đọc trên staging đạt: hồ sơ `dailyQA` đã lưu trữ nhưng còn 2 kết quả kiểm tra máy và 6 điểm xu hướng nên bị chặn, giao diện xác nhận dữ liệu được giữ nguyên và không gửi yêu cầu xóa. Bằng chứng: [xem trước xóa hồ sơ có liên kết trên staging](docs/evidence/p5-staging-linked-case-purge-preview-20260914.json). Đây là kiểm chứng staging an toàn, chưa đóng lỗi mạng, tiến trình nền và toàn vẹn dữ liệu.
- Kiểm chứng tiến trình nền Gamma thật trên staging đạt ngày 2026-09-14: forced revalidation phát hiện fixture đo 3D cũ thiếu `coordinate_frame`; bản fixture hợp lệ được tải lại đúng loại/vai trò, preflight chuyển `VALID`, sau đó Gamma 3D được enqueue qua API thật và worker Redis Streams lưu run `aa563fac…` ở trạng thái `COMPLETED/PASS`, 8/8 điểm, coverage `1`, P95 `0`, attempt `1`, engine `gamma-nd-p8.2`. Bằng chứng: [Gamma worker staging](docs/evidence/p5-staging-gamma-worker-20260914.json). Cổng còn lại của P5 là gửi yêu cầu xóa thật cho `dailyQA` có liên kết và đối chiếu toàn vẹn sau khi máy chủ từ chối.
- Bổ sung kiểm thử hồi quy hàng đợi tệp ở commit `d6980d9`: loại và vai trò mới được áp dụng cho tệp đang chờ trước khi tải lên, không làm thay đổi tệp đã tải hoặc tệp của hồ sơ khác; **9/9** kiểm thử, lint và production build đạt. Bằng chứng: [hàng đợi tệp](docs/evidence/p5-local-upload-queue-metadata-20260914.json). Bản web đã được Railway staging triển khai và gói JavaScript công khai chứa thông báo hành vi mới.
- Kiểm chứng lỗi mạng trên staging đạt ở bản `667e94d`: khi API bị chặn, giao diện hiển thị lỗi kết nối và nút “Thử lại”; sau khi khôi phục kết nối, bấm thử lại tải đủ danh mục 63 bài cùng lịch sử, không ghi dữ liệu. Bằng chứng: [thử lại sau lỗi mạng trên staging](docs/evidence/p5-staging-network-retry-20260914.json). Cổng lỗi mạng đã đạt cho lát cắt đọc; tiến trình nền đang chạy và toàn vẹn dữ liệu staging vẫn mở.
- Quan sát chỉ đọc tiến trình nền staging ở bản `a04e2ec`: dịch vụ triển khai thành công, worker khởi động bằng Redis Streams và không có lỗi khởi động. Chưa tạo lượt phân tích mới nên trường hợp worker đang xử lý một hồ sơ vẫn `NOT_RUN`; không dùng quan sát khởi động để đóng cổng. Bằng chứng: [quan sát tiến trình nền staging](docs/evidence/p5-staging-worker-observation-20260914.json).
- Sau commit `27e89f2`, API, giao diện và tiến trình nền staging đều triển khai thành công với cùng mã nguồn; bộ kiểm tra công khai đạt **16/16**, phiên bản API khớp đầy đủ và lược đồ `20260913_0022`. Bằng chứng: [P5 public recheck 27e89f2](docs/evidence/p5-staging-public-recheck-20260914-27e89f2.json). Đây là cổng parity/runtime, không thay thế kiểm tra lỗi mạng, tiến trình nền khi thao tác thật và toàn vẹn dữ liệu sau toàn bộ vòng đời.
- Kiểm tra không ghi dữ liệu trên staging sau khi triển khai bản web `75f86df`: lịch sử có cột chọn, chọn một bài hiện thanh thao tác và số lượng đã chọn, bỏ chọn trả giao diện về trạng thái ban đầu. Không bấm lưu trữ/khôi phục/xóa trong lượt kiểm tra này. Evidence: [chọn nhiều trên staging](docs/evidence/p5-staging-batch-selection-20260914.json). Các ca xử lý nhiều mục thật, lỗi mạng và xung đột đồng thời vẫn là cổng P5-VERIFY chưa đóng.
- Kiểm tra chỉ đọc mới nhất ngày 2026-09-14: Railway staging đang chạy đúng ba dịch vụ trong cùng môi trường, đúng thư mục gốc/Dockerfile, lệnh nâng cơ sở dữ liệu và healthcheck; không có biến bí mật bị ghi vào bằng chứng. API, web và worker cùng chạy bản `cc02bf0`, lược đồ `20260913_0022`; health, readiness, version, OpenAPI, kiểm tra chưa xác thực và web bundle đều đạt. Evidence: [cấu hình Railway hiệu lực](docs/evidence/p5-railway-effective-settings-20260914.json), [kiểm tra công khai bản cc02bf0](docs/evidence/p5-staging-public-recheck-20260914-cc02bf0.json). Đây là cổng triển khai, không thay thế kiểm thử xác thực các trường hợp xóa hồ sơ có liên kết, lỗi mạng và tác vụ nền trên staging.
- Bổ sung kiểm thử toàn vẹn xóa cục bộ: khi xóa vĩnh viễn một hồ sơ không liên kết trong thư mục có hồ sơ khác, hồ sơ bên cạnh và thư mục chứa vẫn còn nguyên; nhóm kiểm thử P5 hiện đạt **30/30**. Đây là bằng chứng bảo vệ dữ liệu dùng chung, chưa thay thế kiểm thử tương ứng trên staging.
- Hồi quy toàn bộ sau kiểm thử toàn vẹn P5: API đạt **217/217**, giao diện đạt **12/12 tệp, 37/37 bài**, kiểm thử tập trung kho QA và worker đạt **17/17**, Ruff đạt. Chỉ còn cảnh báo deprecation của bộ kiểm thử Starlette/httpx và cảnh báo tài nguyên đã có trong bộ kiểm thử; không có lỗi. Evidence: [P5 local regression](docs/evidence/p5-local-regression-20260914-99d68f6.json).
- Kiểm tra giao diện staging chỉ đọc sau đó: danh mục QA hiển thị đủ **63/63 bài**, lịch sử chính có hai hồ sơ đang mở, thùng rác chỉ có hồ sơ `dailyQA` đã lưu trữ; không khôi phục, không xóa và không làm thay đổi dữ liệu. Evidence: [thùng rác staging chỉ đọc](docs/evidence/p5-staging-trash-readonly-20260914.json).
- Kiểm tra parity sau khi ghi nhận hồi quy phát hiện một độ lệch: API staging vẫn ở bản `99d68f6` trong khi gói web đã dựng từ commit tài liệu mới hơn; health/readiness vẫn đạt nhưng kiểm tra SHA web thất bại đúng một mục. Đã sửa bằng mốc theo dõi trong cả thư mục API và web ở commit `f608f27`; cần chờ ba dịch vụ dựng lại rồi kiểm tra lại, không dùng kết quả cũ để tuyên bố parity đạt. Evidence lỗi: [staging parity mismatch](docs/evidence/p5-staging-public-recheck-20260914-99d68f6.json).
- Đã chờ Railway dựng lại sau mốc theo dõi và chạy lại kiểm tra công khai: exact-SHA verifier đạt **16/16**, API, web và worker cùng bản `db97b0e`, cùng lược đồ `20260913_0022`; health, readiness, OpenAPI, bảo vệ truy cập chưa xác thực và dấu hiệu giao diện đều đạt. Evidence: [P5 staging parity PASS](docs/evidence/p5-staging-public-recheck-20260914-db97b0e.json). Khi có thay đổi tài liệu/bằng chứng mới, phải lặp lại cơ chế mốc theo dõi trước khi gọi đó là ứng viên hiện hành.
- Kiểm tra lại ứng viên staging `3701b65` sau khi cập nhật toàn bộ hồ sơ bằng chứng: exact-SHA verifier tiếp tục đạt **16/16**, API, web và worker cùng commit, cùng lược đồ `20260913_0022`; không có lỗi health, readiness, OpenAPI hay bảo vệ truy cập. Evidence: [P5 staging parity recheck](docs/evidence/p5-staging-public-recheck-20260914-3701b65.json).
- Bổ sung hồi quy P5 tại commit `9b95615`: hồ sơ đã lưu trữ nhưng còn một tệp đầu vào chưa phân tích bị xem trước là không đủ điều kiện, yêu cầu xóa vĩnh viễn bị từ chối và hồ sơ vẫn đọc được. API đạt **218/218**, giao diện đạt **12/12 tệp, 37/37 bài**, Ruff đạt; bằng chứng: [bảo vệ tệp đầu vào](docs/evidence/p5-local-input-artifact-purge-guard-20260914.json). Đây là kiểm chứng cục bộ; từ chối hồ sơ có liên kết trong phiên staging vẫn cần được kiểm tra khi có xác nhận thao tác tương ứng.
- Ứng viên staging `2d6b7c8` sau đó đã được Railway dựng lại đồng bộ; kiểm tra công khai đạt **15/15**, API/web nhận cùng bản phát hành, lược đồ `20260913_0022`, health/readiness/OpenAPI và các bảo vệ truy cập chưa xác thực đều đạt. Bằng chứng: [P5 staging public recheck](docs/evidence/p5-staging-public-recheck-20260914-2d6b7c8.json). Đây chỉ là cổng parity/runtime, chưa đóng các ca xóa hồ sơ có liên kết, lỗi mạng và tiến trình nền.
- Recheck công khai ứng viên `860c9f7` đạt **15/15**, không lỗi, sau khi dựng lại mốc parity tài liệu; API/web cùng phiên bản và lược đồ `20260913_0022`, health/readiness/OpenAPI và các bảo vệ truy cập chưa xác thực đều đạt. Bằng chứng: [P5 staging public recheck](docs/evidence/p5-staging-public-recheck-20260914-860c9f7.json). Đây chỉ là cổng parity/runtime, chưa đóng các ca xóa hồ sơ có liên kết, lỗi mạng và tiến trình nền.
- Sau khi bộ kiểm tra triển khai được đẩy lên, Railway đã dựng lại API, web và worker cùng mã `517600d1f7a46597030af949bc3c3c46c3079a49`; kiểm tra công khai hiện hành đạt **16/16**, lược đồ `20260913_0022`, health/readiness/version/OpenAPI và các tuyến bảo vệ truy cập đều đạt. Bằng chứng: [P5 staging public recheck hiện hành](docs/evidence/p5-staging-public-recheck-20260914-517600d.json). Đây là cổng parity/runtime, không đóng các cổng từ chối hồ sơ có liên kết khi thao tác thật, tiến trình nền khi chạy phân tích và toàn vẹn dữ liệu sau toàn bộ vòng đời.
- P6 đã đạt `STAGING_VERIFIED_AND_HANDOFF_COMPLETE` ở source `6615820`: đối chiếu kho lưu trữ không có vật mồ côi hoặc tệp thiếu (`27/27` đối tượng), tải xuống có chữ ký trả đúng byte/tên tệp, và toàn bộ cổng local/public đạt. Evidence: `docs/evidence/p6-staging-storage-integrity-reconciliation-20260914.json`, `docs/evidence/p6-staging-verification-handoff-20260914.json`, `docs/evidence/p6-staging-public-recheck-20260914-6615820.json`. P7 là giai đoạn duy nhất đang mở.
- P7 bắt đầu sau bàn giao P6 ở source `ec741a2`: registry đã ánh xạ và phân giải `62/62` capability pylinac của danh mục, wheel `3.47.0` có SHA-256 cố định trong khóa riêng, ảnh API kiểm hash bằng `--require-hashes`, API có tuyến trạng thái capability theo phạm vi tổ chức. Bằng chứng: [registry pylinac local](docs/evidence/p7-local-pylinac-registry-20260914.json). Đây mới là `LOCAL_VERIFIED_SLICE` cho P07-W02 và phần registry của W03; `PylinacAdapter`, fixture/contract test và toàn bộ bài chạy thật vẫn chưa đóng.
- Lát cắt P7 tiếp theo đã được triển khai ở commit `5f89646d5ad9b983a6e6b2717c48143963660467`: `PylinacQARun` và migration `20260914_0023` lưu snapshot tham số, tệp đầu vào, kết quả, đánh giá riêng và overlay; adapter thật hiện chạy Picket Fence và Starshot bằng Pylinac `3.47.0`, không có fallback. Picket Fence đã smoke bằng `AS1200.dcm` (PASS, 100% lá đạt, overlay 162086 byte); Starshot đã smoke bằng `starshot.tif` với SID 1000 (PASS, đường kính lệch 0.3290 mm, overlay 54560 byte). Giao diện Starshot hỗ trợ SID/DPI, bán kính, dung sai và tâm X/Y nhập tay; cả hai lưu lịch sử và cho mở ảnh phân tích. API 4 kiểm thử Pylinac và web 39/39 đạt, Ruff/mypy/typecheck/lint đạt. Bằng chứng: [P7 local Picket Fence và Starshot](docs/evidence/p7-local-picket-starshot-20260914.json). Đây vẫn là `LOCAL_VERIFIED_SLICE`; 60 capability còn lại, canvas dùng chung, fixture/contract matrix, staging và P7-VERIFY/HANDOFF chưa hoàn tất.
- Lát cắt Winston–Lutz tiếp theo đã được nối vào cùng hợp đồng P7: adapter gọi trực tiếp `WinstonLutz.from_zip()`/`analyze()`/`results_data()`/`plot_images()`, yêu cầu đúng một tệp ZIP, lưu ảnh phân tích, kết quả và đánh giá riêng; giao diện có SID/DPI, kích thước bi, ngưỡng nhận diện, góc tham chiếu, chế độ đọc góc từ DICOM hoặc tên tệp và các tùy chọn trường mở/dịch chuyển ảo. Kiểm thử giả lập Pylinac đạt, kiểm tra thật với `winston_lutz.zip` của Pylinac 3.47.0 đạt (17 ảnh, chỉ số sai lệch trục–bi lớn nhất 1.2352 mm, ảnh phân tích 224167 byte); mặc định giao diện đọc góc từ siêu dữ liệu DICOM vì bộ mẫu không mã hóa góc trong tên tệp. Đây vẫn là `LOCAL_VERIFIED_SLICE`, chưa triển khai staging và chưa đóng P07-WL/P07-VERIFY/HANDOFF.
- Lát cắt P07-WLMT tiếp theo đã được nối vào cùng hợp đồng: adapter gọi trực tiếp `WinstonLutzMultiTargetMultiField.from_zip()`/`analyze()`/`results_data()`/`plot_images()`, dựng `BBConfig` từ bảng cấu hình người dùng, lưu kết quả/đánh giá/ảnh tổng hợp và từ chối ZIP sai định dạng hoặc cấu hình bi thiếu trường. Giao diện có bảng sáu bi có thể sửa tên, ba độ lệch không gian, kích thước bi và bán kính trường; có SID/DPI, khoảng cách nhận diện, trường mở, bi mật độ thấp và lựa chọn nguồn góc. Kiểm tra thật với `SNC_MTWL_demo.zip` của Pylinac 3.47.0 đạt (19 ảnh, 6 bi, sai lệch trường–bi lớn nhất 0.9430 mm, ảnh 278462 byte); API đạt 8/8, Ruff/mypy/lint/typecheck/build đạt. Đây vẫn là `LOCAL_VERIFIED_SLICE`, chưa có ánh xạ góc thủ công theo từng tệp, ma trận fixture đầy đủ, staging và P07-VERIFY/HANDOFF.
- Lát cắt P07-VMAT tiếp theo đã nối ba lớp `DRGS`, `DRMLC`, `DRCS` vào cùng hợp đồng Pylinac: API yêu cầu đúng hai ảnh DICOM, giữ thứ tự ảnh mở/ảnh điều biến, truyền dung sai và kích thước đoạn; DRCS nhận thêm khoảng cách xuyên tâm chuẩn trực. Adapter gọi trực tiếp engine, lấy `results_data()` và `plot_analyzed_image()`, lưu kết quả/đánh giá/overlay; giao diện cho chọn cặp ảnh, tham số và xem lịch sử. Kiểm tra thật bằng bộ mẫu Pylinac 3.47.0 đạt: DRGS sai lệch lớn nhất 1.7786% (engine cảnh báo theo dung sai mẫu), DRMLC 0.8179%, DRCS 1.0775%; ảnh phân tích lần lượt 87326, 71352 và 81479 byte. API 10/10, Ruff/mypy/lint/typecheck/build đạt. Đây vẫn là `LOCAL_VERIFIED_SLICE`, chưa có ma trận fixture đầy đủ, canvas chung, staging và P07-VERIFY/HANDOFF.
- Lát cắt P07-FPA/FA tiếp theo nối `FieldProfileAnalysis` và `FieldAnalysis` legacy vào cùng hợp đồng Pylinac: API yêu cầu một ảnh đầu vào; giao diện cho chọn tâm trường, vị trí, độ rộng, chuẩn hóa và phương pháp nhận biên, còn bài legacy có thêm quy trình và nội suy. Adapter gọi trực tiếp `analyze()`/`results_data()`/hàm dựng ảnh của Pylinac, lưu chỉ số, đánh giá và overlay. Kiểm tra thật với `AS1200.dcm` đạt: FPA có độ phẳng X 44.7702%, Y 26.4415%, overlay 54772 byte; FA legacy có độ phẳng ngang 44.7802%, dọc 20.2947%, overlay 57977 byte. API 12/12, Ruff/mypy/lint/typecheck/build đạt. Bằng chứng: [P7 local biên dạng trường](docs/evidence/p7-local-field-profile-20260914.json). Đây vẫn là `LOCAL_VERIFIED_SLICE`, chưa có ma trận fixture đầy đủ, canvas chung, staging và P07-VERIFY/HANDOFF.
- Lát cắt P07-CT tiếp theo nối bốn lớp `CatPhan503`, `CatPhan504`, `CatPhan600`, `CatPhan604` vào hợp đồng Pylinac: API yêu cầu đúng một tệp ZIP DICOM, truyền đúng dung sai HU/CNR/độ dày, lát gốc và các điều chỉnh phantom; giao diện chọn bộ ảnh, tham số và mở overlay/lịch sử. Contract test API đạt 13/13, Ruff/mypy/lint/typecheck/build đạt. Môi trường Pylinac 3.47.0 hiện không có fixture CatPhan để chạy engine thật, vì vậy chưa ghi chỉ số giả, chưa tạo evidence engine cho P07-CT và chưa triển khai staging.
- Lát cắt P07-PLANAR tiếp theo nối đủ 19 biến thể ảnh phẳng vào adapter Pylinac: các nhóm Leeds/Las Vegas/SNC/EPID dùng tham số tương thích chung, nhóm FC-2 có `fwxm`/ngưỡng biên, ACR Digital Mammography có tham số sợi/đốm riêng. API yêu cầu đúng một ảnh; giao diện chọn ảnh, tâm, góc, vùng quan tâm, đảo ảnh và ngưỡng; kết quả/đánh giá/overlay/lịch sử được lưu theo cùng hợp đồng. Contract test API đạt 14/14, Ruff/mypy/lint/typecheck/build đạt. Môi trường Pylinac 3.47.0 hiện không có fixture ảnh phẳng chuẩn để chạy engine thật, vì vậy chưa tạo evidence engine cho P07-PLANAR, chưa đối chiếu từng structured result và chưa triển khai staging.
- Lát cắt P07-ACR tiếp theo nối đủ ba lớp `ACRCT`, `ACRMRILarge`, `ACRMRIMedium` vào adapter Pylinac: API yêu cầu đúng một tệp ZIP chuỗi DICOM; giao diện có hiệu chỉnh lát gốc, tâm, góc, kích thước vùng và thang đo, chỉ hiện số lần vọng/ngưỡng tương phản thấp cho MRI; kết quả, đánh giá, overlay và lịch sử dùng cùng hợp đồng Pylinac. Contract test ACR, Ruff, mypy, lint, typecheck và bản dựng đạt. Môi trường Pylinac 3.47.0 hiện không có fixture ACR để chạy engine thật, vì vậy chưa tạo evidence engine cho P07-ACR, chưa đối chiếu từng module structured result và chưa triển khai staging.
- Lát cắt P07-CHEESE/P07-HELIOS/P07-QUART tiếp theo nối hai lớp Cheese (`TomoCheese`, `CIRS062M`), `GEHeliosCTDaily`, `QuartDVT` và `HypersightQuartDVT` vào adapter Pylinac. API yêu cầu đúng một tệp ZIP chuỗi DICOM; giao diện có điều chỉnh lát/tâm/góc/vùng, mật độ tham chiếu ROI tùy chọn cho Cheese, cùng dung sai HU/thang đo/độ dày/CNR và dịch lát cho Quart. Kết quả, đánh giá, overlay và lịch sử dùng cùng hợp đồng. Contract test, Ruff, mypy, lint, typecheck và bản dựng đạt; môi trường hiện không có fixture của các phantom này nên chưa có evidence engine thật, chưa đối chiếu module kết quả và chưa triển khai staging.
- Lát cắt P07-CAL tiếp theo mở đủ năm bài hiệu chuẩn TG-51 photon/electron legacy/electron hiện hành và TRS-398 photon/electron. Giao diện chỉ nhập số đo, không hiện khu vực tệp; adapter gọi trực tiếp constructor và thuộc tính kết quả công khai của đúng lớp Pylinac, hỗ trợ nhiều lần đọc, hệ số hiệu chỉnh, liều trên MU, lịch sử và đánh giá riêng. Contract test, API không tệp đầu vào, Ruff, mypy nguồn, lint, typecheck và bản dựng đạt. Kiểm thử hồi quy sau đó đã đưa cả năm lớp qua engine thật bằng số đo tổng hợp và bổ sung chặn thiếu PDD10 tại biên nhập liệu. Chưa có số đo chuẩn/commissioning cho từng lớp, chưa đối chiếu độc lập kết quả và chưa kiểm chứng staging; các lớp hiệu chuẩn không có `results_data()`/overlay như nhóm ảnh nên P7 dùng hợp đồng thuộc tính công khai và P9 dựng báo cáo sau.

### P3 — giao diện gọn, điều hướng và đăng nhập — staging verified — 2026-09-13

- Đã tạo `AppShell`, `CompactPage` và `SplitPane`; thanh điều hướng chỉ còn năm mục chính: Trang chủ, QA máy, Công cụ sinh học, Thư viện kiến thức và Đơn vị và thiết bị. Mã mô-đun không còn hiển thị trên thanh bên.
- Đã làm gọn trang chủ, luồng đăng nhập, khôi phục truy cập, nhận lời mời, tạo đơn vị đầu tiên và trạng thái dịch vụ; các trạng thái chính dùng tiếng Việt, không hiển thị mã định danh kỹ thuật trong giao diện thường dùng.
- Liên kết cũ `/app/biological/knowledge` chuyển về `/app/knowledge`; bố cục hai cột tự chuyển một cột ở màn hình nhỏ.
- Kiểm chứng local: lint PASS, typecheck PASS, Vitest **22/22**, Playwright **9/9** trên hai kích thước 1366×768/1440×900 và ba cấu hình trình duyệt, production build PASS; AX trang đăng nhập và kiểm năm mục PASS.
- Đã commit/push source `dcf463c28dd64dcfa68a6fdf8c17cf40e623a2dc`; API, web và worker staging đều triển khai thành công cùng source. Public verifier staging đạt **17/17**, browser staging tải đúng trang chủ thật và điều hướng năm mục bằng tiếng Việt.
- Evidence: [local](docs/evidence/p3-local-ui-20260913.json), [phase staging](docs/evidence/p3-staging-verified-20260913-dcf463c.json), [public verifier](docs/evidence/p3-staging-public-verifier-20260913-dcf463c.json). P3 đã `STAGING_VERIFIED`; P4 được mở.

Các mục UX1.2 và cũ hơn bên dưới là lịch sử; thứ tự tiếp tục và phạm vi mới do UX1.3 ở trên quyết định.

## UX1.2 — Toàn bộ danh mục pylinac là phạm vi bắt buộc — 2026-09-13

- Đợt này chỉ viết lại tài liệu, không sửa giao diện/engine, không commit/push/deploy và không cập nhật dữ liệu Railway/Stitch.
- Năm mục chính: Trang chủ, QA máy, Công cụ sinh học, Thư viện kiến thức, Đơn vị và thiết bị. Báo cáo/lịch sử/xu hướng nằm trong QA; sáu phép tính/tra cứu sinh học cùng một trang.
- Giữ đăng nhập/cơ cấu và thành viên ngang quyền; yêu cầu mới tập trung compact layout, tiếng Việt nhất quán, không JSON/ID kỹ thuật, xóa/khôi phục lịch sử, PDF chọn dòng/ảnh.
- P7 UX1.2 bắt buộc đủ 16 họ mô-đun chính, mọi class/biến thể và các bài QA `contrib/One-Offs` công khai của wheel pylinac đã khóa; Picket Fence/Winston–Lutz/Starshot chỉ còn là ba package trong danh mục, không phải điều kiện đóng đầy đủ.
- Pylinac là engine chính thức, không còn là lựa chọn ưu tiên. RT-CONNECT giữ form, validation, parameter mapping, thao tác click/drag tâm/ROI/profile, result mapping, lịch sử, đánh giá, overlay và PDF; không viết lại metric pylinac đã cung cấp.
- P8 mới dùng Gamma pylinac 1D/2D với ô Chênh lệch liều (%) và DTA (mm). Gamma 3D `gamma-nd-p8.2` là evidence/engine kế thừa chỉ đọc, không tự đóng P8 UX1.2 và không được gắn nhãn pylinac.
- Danh mục chi tiết và nguồn: `docs/pylinac-qa-catalog.md` v1.1. Mọi cập nhật pylinac phải inventory-diff registry và fail build nếu có capability chưa ánh xạ.
- Trạng thái P0 tài liệu: LOCAL_VERIFIED trên working tree UX1.2 từ HEAD `7a7e4ec`, chưa commit. Verifier đạt 471/471 điều kiện, 21 phase và 226 acceptance scenarios; 14/14 test verifier đạt, gồm kiểm tra phủ định khi hạ version catalog hoặc bỏ module family, bài contrib khỏi plan/catalog hay bỏ PylinacAdapter. Evidence: `docs/evidence/ux1-planning-contract-20260913.json`. Đây không phải 226 test ứng dụng đã chạy.
- Checkpoint UX1.1 trước đó đạt 423 điều kiện/21 phase/193 tình huống và 11 test verifier; evidence cũ vẫn giữ nhưng đã bị UX1.2 thay phạm vi.
- Bước thực thi tiếp theo: P3/P4 khung gọn → P5/P6 catalog/input framework → P07-W02/W03 runtime+registry → các package P07-CAL…P07-CONTRIB → P8/P9/P10.
- Bản ba tài liệu trước UX1 giữ nguyên trong `docs/history/pre-ux-20260912/`. Các checkpoint bên dưới là lịch sử theo SHA và không tự đóng testcase TC-UX1.

## P0/P18 — partitioned backend regression — PASS, monolithic runner anomaly documented — 2026-09-11 / `249a8ba`

- Collection hiện tại có **204 test trong 31 file**. Ba nhóm chạy độc lập đều trả `EXIT_CODE=0`: core/artifact/biological/DVH `44`, Gamma/worker/health/machine/migration `59`, organization/integration/biological/report/Auth `101`; tổng **204/204 PASS**.
- Lệnh monolithic trước đó dừng ở marker khoảng 35% mà không có summary hoặc exit code, nên không được tính PASS; đã ghi anomaly này trong evidence và rerun toàn bộ collection theo partition.
- Evidence: [p0-p18-backend-regression-20260911-249a8ba.json](docs/evidence/p0-p18-backend-regression-20260911-249a8ba.json). Đây là `LOCAL_VERIFIED`; không thay staging/production fault, provider backup/restore, rollback, alert, pilot hoặc clinical-readiness evidence.

## P18-W00 — local integrated release-candidate journeys — PASS, remote gates open — 2026-09-11 / `4ecfae8`

- Chạy lại `apps/api/.venv/Scripts/python.exe -m pytest -q --no-cov tests/test_p18_integration.py` trên working tree sạch, kết quả **2/2 PASS**.
- `TC-P18-S01` đi qua session bootstrap → organization/folder/case → Machine QA seed/evaluate → hai measurement artifact upload/validate → Gamma queue/idempotent replay/worker completion → report snapshot/export/download hash → trend/rebuild idempotency.
- `TC-P18-S02` đi qua Biological library publish/use → scenario → hai BED/EQD2 calculation → comparison → re-irradiation → Biological report; assertion trực tiếp rằng report thuộc namespace `BIOLOGICAL_TOOLKIT` và không có `qa_case_id`.
- Evidence: [p18-local-integrated-20260911-4ecfae8.json](docs/evidence/p18-local-integrated-20260911-4ecfae8.json). Đây là `LOCAL_VERIFIED` support evidence; không thay staging authenticated E2E, browser/device matrix, fault/resource, provider backup/restore, pilot hoặc production/clinical-readiness gate.

## P18-W03a — local PostgreSQL/MinIO backup-restore recheck — PASS, remote gate open — 2026-09-11

- Sau khi khởi động Compose `postgres`/`minio`, rebuild API image để chứa migration `20260911_0020`, chạy migration head và seed foundation synthetic, harness `scripts/verify-local-backup-restore.py` đạt `passed=true`.
- PostgreSQL custom dump `170,081` bytes; source/restored row counts và canonical row fingerprints khớp. Object inventory có `1` fixture RTDOSE tổng hợp, source/restored inventory hash cùng `47907db468eda5722eb292cb55cd6be4f10a1e6e70568315ba63daedcdabfc2f`; database/bucket tạm đã cleanup thành công.
- Evidence mới: [p18-local-backup-restore-20260911.json](docs/evidence/p18-local-backup-restore-20260911.json). Đây là `LOCAL_VERIFIED` support path; không thay Railway provider backup/restore, staging RPO/RTO, rollback hoặc production gate. Lần chạy trước khi Compose sẵn sàng được giữ trong evidence riêng và không tính PASS.

## P18/P19/P20 — Railway provider backup inspection — gate open — 2026-09-11

- Railway GraphQL read-only introspection thành công và hiển thị các surface `volumeInstanceBackupList`, `volumeInstanceBackupScheduleList`, `volumeInstancePitrRestoreEstimate` và `deploymentSnapshot`.
- PostgreSQL staging volume instance `a3380835-08d5-409a-8d46-cd15931445b4` và production volume instance `56d3e3cf-8540-44f1-b2eb-8fc53fbd590f` đều `READY`, nhưng cả hai trả `backup_count=0` và `backup_schedule_count=0`.
- Không gọi mutation, không tạo backup/schedule/restore. Trạng thái là `PROVIDER_BACKUP_NOT_CONFIGURED`; volume `READY` không được hiểu là có backup.
- Evidence: [p18-p20-railway-backup-capability-20260911.json](docs/evidence/p18-p20-railway-backup-capability-20260911.json). Next exact action là chọn retention/schedule có chủ đích, cấu hình provider rồi đọc lại schedule + backup ID trước restore drill.

## P20-W02 — backup schedule authority check — external permission required — 2026-09-11

- Đã thử mutation `volumeInstanceBackupScheduleUpdate` với `DAILY` trên PostgreSQL staging, nhưng Railway trả `Not Authorized` cho cả `RAILWAY_ACCOUNT_TOKEN` và `RAILWAY_PROJECT_TOKEN`.
- Read-back ngay sau đó xác nhận không có side effect: `backup_schedule_count=0`, `backup_count=0`, volume vẫn giữ nguyên. Không retry mutation thêm.
- Evidence: [p20-railway-backup-schedule-authority-20260911.json](docs/evidence/p20-railway-backup-schedule-authority-20260911.json). Next exact action: cấp quyền volume-backup hoặc thao tác schedule trong Railway dashboard; sau đó chạy verifier read-only và tiếp tục restore drill.

## P20-W01 — current staging operational probes — public verified slice — 2026-09-11 / `f938fd7`

- `scripts/verify-operational-probes.ps1` đã đọc đúng staging API `https://gleaming-cooperation-staging.up.railway.app` và web `https://rt-connect-web-staging-staging.up.railway.app` trên candidate source SHA `f938fd7541fbe5c8086f12e2e0cfe3cd74dd6418`.
- Health, readiness, schema parity, exact version và web `/app` đều PASS; API/web trả HTTP 200, schema `20260911_0020`, `failed_check_count=0`.
- Queue metrics được ghi `NOT_RUN` vì không truyền session access token; không được suy diễn thành worker PASS. Alert delivery, provider backup/restore, authenticated E2E và rollback vẫn mở.
- Evidence: [p20-staging-operational-probes-20260911-f938fd7.json](docs/evidence/p20-staging-operational-probes-20260911-f938fd7.json). Đây là public operational probe evidence, không phải P20 DONE hoặc clinical-readiness evidence.

## P8-W03 — deterministic Gamma workload benchmark — local verified slice — 2026-09-11 / `4cf0164`

- `scripts/benchmark-p8-gamma.py` chạy engine `gamma-nd-p8.2` trên hai grid 3D tổng hợp giống nhau `8×16×16` (2,048 voxel), 2 lần lặp, GRID/3D, DTA `3 mm`, max γ `2` và candidate budget `50,000`.
- Kết quả: median `3.183637 s`, min `3.059931 s`, max `3.307343 s`; Python-traced peak allocation tối đa `2,023,628 bytes`. Oracle giữ `PASS`, `2,048/2,048` evaluated/passing, pass rate `100%`, max gamma `0`, `0` censored và `0` no-candidate.
- Evidence: [p8-local-gamma-workload-20260911-4cf0164.json](docs/evidence/p8-local-gamma-workload-20260911-4cf0164.json). Đây là local deterministic workload/oracle evidence; Windows host không cung cấp process-RSS/cgroup gate trong script này, nên không được coi là staging capacity hoặc clinical commissioning.
- P8 vẫn mở staging crash-after-durable-commit-before-ACK, bounded retry/dead-letter/failure injection, large-input/resource budget trên Railway, oracle promotion/convergence và release-manifest evidence.

## P0/P19/P20 — planning contract and staging parity — verified slice — 2026-09-11 / `65268c7`

- `scripts/verify-planning-contract.py` đã được đồng bộ với revision hiện hành: business `0.27`, specification `1.29`, technical `1.30`, plan `4.25`. Verifier đạt `passed=true`, `failed_check_count=0`, đủ `21` phase, FR mapping, S/E sections, work packages, B01–B12, G0–G7 và support artifacts. Evidence: [p0-planning-contract-20260911-65268c7.json](docs/evidence/p0-planning-contract-20260911-65268c7.json).
- Railway staging API, web và worker đều `SUCCESS` trên cùng source SHA đầy đủ `65268c7026609e711a57d5abd9e0ee22835f1e98`. Deployment IDs lần lượt là `e047284a-c130-4caf-b53c-8552f14e535d`, `db98ad77-ad6a-43c4-b7d5-9399c93f5416` và `cb620b5d-af67-4753-893f-994d4600393d`; `/api/v1/version` và `/api/v1/ready` trả đúng SHA/schema `20260911_0020`, web root trả HTTP 200.
- Đây là planning/source/runtime parity evidence; không đóng các authenticated mutation, worker fault/resource, provider backup/restore, rollback, pilot hoặc clinical readiness gates. Browser connector hiện không trả inventory hợp lệ nên không dùng browser smoke để suy ra các gate đó.

## P19-W01 — redacted staging release manifest — integrity verified / promotion blocked — 2026-09-11 / `25a3620`

- Manifest [release-manifest-staging-25a3620.json](docs/evidence/release-manifest-staging-25a3620.json) được tạo từ deployment metadata thật của API/web/worker, ba service cùng SHA `25a36208f8abcbc05598bd263723ec15060a43b5`, schema `20260911_0020`, hai synthetic fixture hash và test evidence local/staging.
- `--verify-manifest` trả `valid=true`, `error_count=0`, `service_sha_parity=true`, `release_gate=ELIGIBLE`; `manifest_sha256=bc240e4bf4109b3fd4f09d106e2b2b2b5c0000feb7309f28246528f5a148843a`.
- `ELIGIBLE` ở đây chỉ là integrity/source-parity gate của candidate staging. Manifest vẫn ghi rõ production promotion bị chặn cho đến khi provider backup/restore, rollback, authenticated full E2E, fault/resource và handoff/pilot evidence đạt; không được hiểu là production release hoặc clinical readiness.

## P4-W03/P4-W04 — active-parent lifecycle — staging partial / local verified — 2026-09-11 / `42d1011`

- API P4 đã khóa quy tắc lifecycle theo parent đang active: organization archived không nhận site, machine hoặc invitation mới; site archived không nhận machine mới hoặc machine mutation; resource archived chỉ được khôi phục bằng mutation explicit `is_archived=false`. Restore organization là ngoại lệ có chủ đích cho active member để có đường phục hồi.
- Optimistic revision vẫn bắt buộc trên mọi hierarchy PATCH; parent và child được row-lock trong cùng transaction, stale update trả `409 REVISION_CONFLICT` mà không ghi đè. Local P4 suite **15/15**, full backend suite, Ruff, frontend typecheck/lint, Vitest **20/20** và production build đều PASS.
- API, web và worker staging deploy thành công cùng source SHA đầy đủ `42d10116762827a7cd703a87ce26e676037aeeb5`; `/api/v1/version` và `/api/v1/ready` trả đúng SHA/schema `20260911_0020`, web root trả HTTP 200. Evidence: [p4-active-parent-lifecycle-staging-20260911-42d1011.json](docs/evidence/p4-active-parent-lifecycle-staging-20260911-42d1011.json).
- RTDOSE tổng hợp đã được upload trước đó vào case `ed7ddbe5-811a-4463-a270-b0386f64644d`, manifest `VALID`, 898 bytes và SHA-256 khớp. Checkpoint này không upload lại fixture và không tạo Gamma/DVH run mới.
- Đây là `STAGING_PARTIAL`, không phải P4 DONE: authenticated two-identity concurrency, direct PostgreSQL/audit readback, browser lifecycle evidence và public verifier ổn định vẫn mở.

## P4-W03 — organization hierarchy optimistic revision — local verified slice — 2026-09-11 / `be84887`

- Migration `20260911_0020` thêm `revision` bắt đầu từ `1` cho `organizations`, `sites` và `machines`; schema/config/Compose/OpenAPI đã đồng bộ sang schema head mới. Mọi PATCH hierarchy bắt `expected_revision`; PostgreSQL dùng row lock, stale edit trả `409 REVISION_CONFLICT`, không overwrite và không tăng revision.
- Organization Management client gửi revision hiện tại khi đổi tên organization, sửa machine hoặc archive machine. Không thêm role/action permission; các thành viên vẫn ngang quyền trong cùng organization.
- API P4/migration/health/workspace đạt **36/36**, Ruff PASS; frontend typecheck/lint PASS và Vitest **20/20** (9 files). Evidence: [p4-local-optimistic-revision-20260911-be84887.json](docs/evidence/p4-local-optimistic-revision-20260911-be84887.json).
- Đây chỉ là `LOCAL_VERIFIED_SLICE`; staging migration/readiness, direct PostgreSQL row/audit readback, two-identity browser concurrency, active-parent/archive/restore và P4 full exit gate vẫn mở.

## P4-W03/P20 — staging rollout partial — 2026-09-11 / `a1b3e58`

- API, web và worker staging đều báo `SUCCESS` trên candidate `a1b3e588a352115d974e64d8b3b6daabaa596724`; API đã quan sát `schema_revision=20260911_0020` qua version/readiness probes.
- Browser đã tải đúng candidate build: `/app/qa` vẫn thấy fixture RTDOSE tổng hợp đã upload trước đó và `/app/organization` hiển thị organization, site và member context. Không upload lại fixture, không tạo Gamma/DVH run mới. Danh sách machine vẫn ở trạng thái loading tại thời điểm chụp nên chưa được ghi nhận PASS.
- Public verifier bounded retry chưa PASS: các kiểm tra còn lỗi là `api.openapi` và `web.public` do timeout/connection reset khi truyền response; readiness đạt 4/5 lần probe, một lần timeout. Vì vậy rollout này là `STAGING_PARTIAL`, không phải `STAGING_VERIFIED`.
- Evidence: [p4-staging-optimistic-revision-rollout-20260911-a1b3e58.json](docs/evidence/p4-staging-optimistic-revision-rollout-20260911-a1b3e58.json). Còn mở: authenticated stale PATCH với hai identity, direct PostgreSQL readback, machine route, ổn định public verifier và P4 full exit gate.

## P19/P20 — staging public delivery improvement — 2026-09-11 / `8a36435`

- Sau khi ghi nhận partial rollout, Nginx web đã bật gzip cho JS/CSS/JSON/SVG và cache bất biến cho asset có hash. Web build và `nginx -t` đều PASS; header public quan sát được `Content-Encoding: gzip`, `Cache-Control: public, max-age=31536000, immutable`, `Vary: Accept-Encoding`.
- API, web và worker staging đều `SUCCESS` trên cùng SHA `8a364359eb6e5be789f547d73efb469cfb76a093`; `/api/v1/version` và `/api/v1/ready` trả đúng SHA cùng schema `20260911_0020`. OpenAPI có lần đã đọc được đầy đủ các route CT preview và organization membership, nhưng việc truyền response lớn và web bundle vẫn dao động theo public edge.
- Verifier mới nhất chưa PASS trọn bộ; các check lỗi trong lần đó là `api.health`, `api.openapi`, `web.public` do timeout/connection reset. Vì vậy vẫn giữ trạng thái `STAGING_PARTIAL`, không tuyên bố public parity ổn định.
- Không upload lại RTDOSE tổng hợp, không tạo Gamma/DVH run mới và không chạm production. Evidence: [p20-staging-public-parity-20260911-8a36435.json](docs/evidence/p20-staging-public-parity-20260911-8a36435.json).

## P17-W06 — root-run DVH volume benchmark — local verified slice — 2026-09-11 / `183a4d2`

- Đã sửa runner `scripts/benchmark-p17-dvh.py` để tự thêm `apps/api/src` vào import path; benchmark chạy được từ repository root, không phụ thuộc working directory hay `PYTHONPATH` bên ngoài.
- Synthetic workload `64×128×128` (`1,048,576` voxel, không có dữ liệu bệnh nhân), engine `p17-dvh-1.1.0`, 3 lần lặp: elapsed median `1.0823655 s`, min `1.0765329 s`, max `1.0983356 s`, peak Python-traced allocation `69,235,550 bytes`. Oracle giữ `Dmin=1 Gy`, `Dmean=2.5 Gy`, `Dmax=4 Gy`, volume `12,582.912 cc` và selected voxel count đầy đủ.
- Regression liên quan đạt **33/33 PASS**, Ruff PASS. RSS process không đo được trên host Windows nên `performance_gate=NOT_ASSESSED`; đây là bằng chứng runner/oracle và local volume measurement, chưa phải staging capacity/resource gate. Evidence: [p17-local-volume-benchmark-20260911-183a4d2.json](docs/evidence/p17-local-volume-benchmark-20260911-183a4d2.json).

## P4-W02 — no-membership onboarding route regression — local verified slice — 2026-09-11

- Home Dashboard now has a regression test for the real staging failure boundary: when `/session/bootstrap` returns `ORGANIZATION_MEMBERSHIP_REQUIRED`, the user is redirected to `/auth/session-error`, where the existing first-organization onboarding form can create the initial organization and return to `/app`.
- The test also asserts that Dashboard is not requested before an organization context exists. Frontend full checks passed: lint, typecheck and Vitest **20/20** across **9 files**.
- This closes only the local routing regression. It does not prove a real Supabase identity can create an organization in staging, invitation acceptance, two-identity parity, or direct PostgreSQL/audit evidence; those P4 staging gates remain open.

## P0-W03 — live Stitch screen registry — verified snapshot — 2026-09-11

- Stitch project `RT-connect` (`14242591911141046021`) được query live qua MCP và trả **10 resource**: 8 application screen gồm Auth (4), Home, QA Archive, Gamma Workspace, Report Builder; cùng 2 image asset là logo và avatar.
- Không có application screen live cho Organization/Site/Machine hoặc Biological Toolkit. Bốn Biological resource cũ vẫn được coi là hidden/legacy, không được tự gán vào route và không được khôi phục chỉ để làm đủ số lượng màn hình.
- Registry có ID/title/device/dimension và cờ HTML/screenshot trong [stitch-screen-registry-20260911.json](docs/evidence/stitch-screen-registry-20260911.json). Đây là evidence của design inventory; mapping component/API/FR, tạo screen còn thiếu và visual/accessibility acceptance vẫn là việc mở của P0/P3/P4/P12–P15.

## P20-W01 — staging source parity after Stitch registry documentation — verified — 2026-09-11 / `c0a8b82`

- Railway staging đã được đồng bộ sau khi web/worker tự deploy commit tài liệu nhưng API chưa tự chạy theo watch pattern. API được deploy bổ sung có kiểm soát; API deployment `0c1af92e-852d-4abf-a847-7a08fa6a4a4f`, web `6ef433a8-5c77-47a4-9239-c09a4bc8d5db`, worker `c0c938aa-7250-4caa-9a03-9e466eeb6b23` đều `SUCCESS` và cùng source SHA `c0a8b82edeb4bdbc3461e6df6182a894f7c90208`.
- Public verifier đạt **15/15 PASS**, gồm health/readiness, schema `20260909_0019`, exact API version, OpenAPI CT preview + member/invitation routes, unauthenticated 401 boundary, web index/bundle, UI markers và exact source marker. Evidence: [p20-staging-public-parity-20260911-c0a8b82.json](docs/evidence/p20-staging-public-parity-20260911-c0a8b82.json).
- Đây là source/runtime parity evidence trên staging; không đóng P20 hay các gate authenticated workflow, worker fault/resource, backup/restore, rollback, pilot hoặc clinical readiness.

## P20-W01 — final public parity checkpoint before continued implementation — verified — 2026-09-11 / `67f189c`

- Sau khi đồng bộ API với web/worker, cả ba service staging đều `SUCCESS` trên source SHA `67f189c242882c711b0ccf13f7b104672322bbcf`: API `f6b8a385-86c5-4b0f-84bc-0364eb5a32e1`, web `8770486b-7ffb-43c4-9538-4066ce7a11c9`, worker `329b7fe2-3d1a-44d4-89c8-0b6f81dd3198`.
- Public verifier đạt **15/15 PASS** và schema `20260909_0019`; bằng chứng đầy đủ được lưu tại [p20-staging-public-parity-20260911-67f189c.json](docs/evidence/p20-staging-public-parity-20260911-67f189c.json).
- Quy tắc đã xác nhận: docs-only commit có thể làm web/worker tự deploy trong khi API giữ source cũ vì watch pattern; trước mỗi checkpoint phải đọc exact SHA từng service và deploy API cùng commit nếu cần. Đây là parity gate, không phải bằng chứng P20 DONE hoặc clinical readiness.

## P06 — signed artifact download filename contract — local verified — 2026-09-11 / current worktree

- API `GET /api/v1/artifacts/{artifact_id}/download` hiện trả thêm `filename` và truyền `response-content-disposition` vào signed URL. Filename được lấy ở basename, loại bỏ path separator, quote, CR/LF và control character; filename rỗng/hỏng dùng fallback xác định từ artifact ID. Object key, bytes và SHA-256 không thay đổi.
- Regression `apps/api/tests/test_artifacts.py` đạt **7/7 PASS**, gồm filename bình thường, filename multipart có ký tự nguy hiểm và header readback trên in-memory storage. OpenAPI đã được sinh lại để schema `DownloadResponse` yêu cầu `filename`; frontend client đã validate trường này.
- Ruff, strict mypy, frontend lint, typecheck và Vitest **8 files / 19 tests** đã PASS trong slice này. Full backend suite cần chạy lại sau khi commit để release-manifest test không còn cố ý chặn vì `WORKING_TREE_DIRTY`.
- Đây là `LOCAL_VERIFIED_SLICE`, chưa đóng P06-W04/P06-VERIFY/P06-HANDOFF. Staging cần deploy đúng commit rồi đọc lại response header, tải fixture RTDOSE đã tồn tại và re-hash byte; không upload thêm fixture, không tạo Gamma run mới và không chạm production trong checkpoint này. Tham chiếu kế hoạch: `plan.md v4.25`.

## P06/P20 — signed filename contract deployed and RTDOSE readback — staging verified slice — 2026-09-11 / `1984c04`

- API `4dd93fe1-7103-4f53-8f67-9b508328e33f`, web `c394f01e-43ad-4844-9333-aebb16e880c0` và worker `fb58047b-e511-43bf-9754-4fc33f5e3be6` đều `SUCCESS`, cùng source SHA đầy đủ `1984c04ccce438cf1eaed9008a247eea517ca103`. Public verifier đạt **15/15 PASS**, health/readiness/version, schema `20260909_0019`, OpenAPI/Auth boundary và web exact-SHA marker đều PASS. Evidence: [p20-staging-public-parity-20260911-1984c04.json](docs/evidence/p20-staging-public-parity-20260911-1984c04.json).
- Browser đã tải read-only artifact `gamma-rtdose-v1-smoke.dcm` đã tồn tại trong case `ed7ddbe5-811a-4463-a270-b0386f64644d`; file quan sát `Unconfirmed 485528.crdownload` có 898 bytes và SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, khớp fixture và artifact server. Edge vẫn giữ hậu tố `.crdownload`, vì vậy final filename/header readback độc lập qua browser chưa được đánh dấu PASS. Evidence: [p06-staging-rtdose-download-20260911-1984c04.json](docs/evidence/p06-staging-rtdose-download-20260911-1984c04.json).
- Đây là `STAGING_VERIFIED_SLICE`: không upload lại fixture, không tạo Gamma run/report mới và không chạm production. P06-W04/P06-VERIFY/P06-HANDOFF vẫn mở cho queue fault/retry có chủ ý, storage reconciliation, header readback ở provider và release/handoff evidence.

## P01 — clean Docker foundation re-verification — local verified — 2026-09-11 / `7d0cd51`

- `scripts/verify-p1.ps1 -WithContainers` đã chạy trên checkout sạch: backend **199 passed**, Ruff PASS, strict mypy PASS trên 47 source files, Alembic SQL render đến schema `20260909_0019` PASS; frontend lint/typecheck/Vitest **19/19**/8 files và production build PASS.
- Compose đã build và khởi động PostgreSQL, Redis, MinIO, API, worker và web ở trạng thái healthy; `alembic upgrade head`, seed synthetic, kiểm tra machine persistence qua PostgreSQL, API `/health`, API `/ready` và web `/health` đều PASS. Script đã cleanup container, network và named volumes test.
- Evidence: [p1-local-docker-verification-20260911-7d0cd51.json](docs/evidence/p1-local-docker-verification-20260911-7d0cd51.json). Đây là local foundation evidence; không đóng các gate authenticated staging, provider fault, backup/restore, rollback, release, pilot hoặc production/clinical readiness.

## P06 — staging RTDOSE signed-download round-trip — verified content / filename open — 2026-09-11 / `67cc42d`

- Từ case staging `ed7ddbe5-811a-4463-a270-b0386f64644d`, Download đã trả đủ 898 bytes của `gamma-rtdose-v1-smoke.dcm`; SHA-256 của content tải về khớp fixture gốc `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`.
- Edge giữ file ở tên `Unconfirmed 912860.crdownload` trong thời gian quan sát dù content đã đủ và hash khớp. Vì vậy content/hash round-trip là **PASS**, còn browser final filename rename là **UNVERIFIED**; không dùng filename để phủ nhận hoặc khẳng định tính đúng của content.
- Evidence: [p06-staging-rtdose-download-20260911-67cc42d.json](docs/evidence/p06-staging-rtdose-download-20260911-67cc42d.json). Đây là read-only download của fixture đã được cho phép; không upload, thay thế, xóa fixture hoặc tạo Gamma run.

## P12/P09 — Biological scenario to report integration — local verified — 2026-09-11

- API `POST /api/v1/organizations/{org}/reports` now resolves a `BIOLOGICAL` source by `scenario_id` inside the requested organization, reads the current `BiologicalScenarioRevision`, and pins scenario metadata plus the full scenario snapshot into `ReportRevision.source_snapshot`. Missing scenario/revision fails closed with `REPORT_SOURCE_UNAVAILABLE`; the initial lookup carries organization scope.
- Added regression coverage for current-revision snapshotting and an out-of-scope organization probe: focused report tests **8/8 PASS**. Existing generic biological report behavior remains covered.
- Biological Hub now has `Tạo report` for each scenario. The authenticated mutation opens `/app/reports?reportKey=...`; Report Builder selects the requested report from query state and clears that state when starting a new report.
- Frontend gates after this slice: lint, typecheck, Vitest **19/19**, and production build **PASS**. Build emits the existing Vite chunk-size advisory only.
- This is `LOCAL_VERIFIED_SLICE`, not P12/P09 staging completion. Staging report creation, PostgreSQL row/snapshot readback, refresh after source revision change, export/render evidence, complete negative matrix, and release manifest remain open. No additional RTDOSE was uploaded and no Gamma run/report was created on staging in this checkpoint.

## P08 — API transform/provenance fail-closed regression — local verified — 2026-09-11

- Bổ sung preflight kiểm tra `transform_to_reference` trước khi enqueue: ma trận 4×4 phải finite, đúng hướng/đơn vị, và transform của reference/evaluation phải giống nhau trong sai số `1e-9`. RTDOSE DICOM native được biểu diễn rõ bằng identity transform; transform non-identity vẫn fail-closed vì chưa có adapter đã kiểm thử.
- Bổ sung kiểm tra provenance SHA-256 ở engine: giá trị phải là chuỗi 64 ký tự hexadecimal, không chấp nhận chuỗi bất kỳ chỉ có độ dài 64.
- Regression test cho transform mismatch, measurement thiếu transform và provenance SHA-256 không phải hexadecimal đều fail đúng mã lỗi. Focused Gamma/DICOM/artifact/worker: **31/31 PASS**; Ruff và strict mypy: **PASS**. Full backend được chạy trong lúc worktree dirty và chỉ còn các test release-manifest cố ý chặn với `WORKING_TREE_DIRTY`; sẽ xác nhận lại release gate sau khi commit trên worktree sạch.
- Đây vẫn chỉ là local implementation evidence. Không upload thêm fixture RTDOSE, không tạo Gamma run mới và không nâng P08/P20 thành DONE; các gate staging geometry-negative, worker fault/retry/resource, oracle promotion, release và clinical readiness vẫn mở theo `plan.md`.

## P20-W01/P08 — staging parity after P8 implementation candidate — verified checkpoint — 2026-09-11 / `d64e64b`

- Sau khi push candidate `d64e64ba5ac2f17b91d35c231a70092a81101a9c` lên nhánh `codex/p4-org-site-machine`, API và web staging đã phục vụ đúng candidate đó; API `/api/v1/health`, `/api/v1/ready`, `/api/v1/version` đều trả hợp lệ, schema `20260909_0019` giữ đúng. Đây là checkpoint trước commit docs tiếp theo `20d34ba`.
- `scripts/verify-public-deployment.ps1` với exact SHA và schema đạt **15/15 PASS**, gồm public health/readiness/version, schema parity, OpenAPI CT preview + organization membership/invitation, unauthenticated 401 boundary, web index/bundle, UI markers và exact source marker. Evidence: [p20-staging-public-smoke-20260911-d64e64b.json](docs/evidence/p20-staging-public-smoke-20260911-d64e64b.json).
- Fixture RTDOSE tổng hợp đã được người dùng cho phép và đã tồn tại một lần trong case `ed7ddbe5-811a-4463-a270-b0386f64644d`; không tạo bản trùng, không upload thêm artifact và không tạo Gamma run mới trong checkpoint này. Evidence upload/readback: [p06-staging-rtdose-upload-20260911.json](docs/evidence/p06-staging-rtdose-upload-20260911.json).
- Đây là `STAGING_VERIFIED_SLICE` cho deployment/public contract. Không suy diễn thành authenticated P8 Gamma run, worker parity, queue/resource/fault matrix, storage reconciliation, backup/restore, rollback, pilot hoặc clinical readiness; các gate đó vẫn mở theo `plan.md`.

## P08 — coordinate-frame/axis-order/transform contract — local verified — 2026-09-11 / `23b88d0`

- Gamma measurement mới phải khai `PATIENT_LPS` hoặc `IEC_PHANTOM`, frame ID, canonical axis order, transform `SOURCE_TO_REFERENCE` bằng ma trận finite 4×4 và provenance type/version/SHA-256. RTDOSE thiếu `FrameOfReferenceUID` bị từ chối; DICOM native identity được phân biệt với legacy grid.
- API preflight kiểm basis/frame ID/axis order/transform compatibility trước enqueue; engine snapshot physical frame trong kết quả. Transform non-identity hiện chưa có adapter nên fail-closed; không auto-align, đổi trục hoặc suy luận từ tên file. JSON legacy chỉ giữ cho cặp ENGINE_TEST cũ và không được trộn vào PSQA với DICOM/explicit measurement.
- Evidence: focused Gamma/DICOM/artifact/worker **30/30 PASS**, full backend **195 passed**, strict mypy/Ruff PASS, independent oracle **6/6 PASS**, local Compose Redis/worker verifier `passed=true`. Files: `docs/evidence/p8-independent-gamma-oracle-20260911.json`, `docs/evidence/p8-local-redis-worker-smoke-20260911.json`.
- Đây là local implementation evidence trên synthetic fixture. Staging vẫn phải deploy đúng candidate, revalidate input đã tồn tại, kiểm negative geometry/axis/transform/scale, queue/resource và public parity; chưa upload thêm RTDOSE, chưa tạo Gamma run mới và chưa nâng P08 thành DONE.

## P07 — Machine QA revision/idempotency hardening — local verified — 2026-09-11 / `c6348c3`

- Evaluate hiện nhận `expected_revision` tùy chọn để không phá caller cũ; UI chính gửi revision mà API trả về sau autosave. Revision lệch trên DRAFT trả `MACHINE_QA_REVISION_CONFLICT` và không chạy rule engine.
- PostgreSQL finalize dùng row-lock để chỉ một transaction chuyển run sang trạng thái terminal. Evaluate lại run `COMPLETED` trả snapshot cũ, không tạo `TrendPoint` thứ hai; seed protocol lặp lại không tạo protocol/rule mới. Snapshot run giữ `p11.protocol-snapshot.v1` với source, capability và đầy đủ rule fields.
- Local checks: `test_machine_qa.py` + `test_trend.py` **15/15 PASS**, Ruff, mypy, web lint/typecheck và planning verifier **21 phase / 0 lỗi**. Evidence: [p07-machine-qa-revision-20260911-c6348c3.json](docs/evidence/p07-machine-qa-revision-20260911-c6348c3.json).
- Chỉ đóng local slice P07-W01/W02/W04. Authenticated staging mutation/concurrency, full S/E/C, release handoff và production/clinical gates vẫn mở.

## P07 — staging source parity/public smoke — 2026-09-11 / `093fe98`

- Sau khi push candidate `093fe987ffac835eb04cc98c570d6a659c4a21fe`, public verifier đạt `15/15`, `failed_check_count=0`; API health/readiness/version, schema `20260909_0019`, OpenAPI route và unauthenticated organization boundary đều PASS; web index/bundle và exact-SHA marker cũng PASS.
- Đây chỉ là bằng chứng API/web public đang phục vụ đúng source candidate. Không suy diễn thành authenticated Machine QA mutation, stale revision conflict, double-submit/concurrent PostgreSQL, worker parity, full P07 S/E/C hoặc clinical readiness.
- Evidence: [p07-staging-public-parity-20260911-093fe98.json](docs/evidence/p07-staging-public-parity-20260911-093fe98.json).

## P19 — effective-settings verifier URL normalization — local verified — 2026-09-11

- `scripts/verify-railway-effective-settings.ps1` hiện chuẩn hóa `ExpectedApiBaseUrl` từ API origin hoặc origin đã có `/api/v1` thành contract base URL của web client; không còn false negative khi người vận hành truyền origin thuần.
- Chạy read-only trên staging bằng origin thuần sau sửa: `passed=True`, `failed_check_count=0`; không ghi secret hoặc giá trị database URL vào output.
- Quy tắc vận hành: `VITE_API_BASE_URL` phải là public API HTTPS origin kèm `/api/v1`, còn `CORS_ALLOWED_ORIGINS` chỉ là web origin; hai giá trị không được hoán đổi.

## P08 — Gamma local regression và independent oracle — local verified — 2026-09-11 / `8ea19f4`

- Recheck hiện hành đạt `23 tests passed` cho Gamma API/engine/DICOM/worker; independent oracle đạt `6/6` case, planning verifier đạt `21 phase / 0 lỗi`.
- Phạm vi đã kiểm lại gồm 2D/3D, RTDOSE GY + `DoseGridScaling`, từ chối orientation không hỗ trợ, dose unit không hợp lệ và spacing không dương, coverage, max-gamma censoring, PSQA preflight/resource limit, lease/fencing, terminal replay, bounded retry/ACK recovery và oracle GRID/BILINEAR + GLOBAL/LOCAL + RELATIVE/ABSOLUTE.
- Evidence: [p08-local-regression-20260911-edf3daa.json](docs/evidence/p08-local-regression-20260911-edf3daa.json). P08 vẫn mở các gate staging fault/ACK/reclaim/dead-letter, large-input/resource budget, geometry/scale negative matrix, oracle promotion và release handoff.

## P08/P19 — current staging parity after DICOM validation hardening — staging verified slice — 2026-09-11 / `6769a85`

- Railway GraphQL readback xác nhận API, web và worker staging đều `SUCCESS`, cùng exact source SHA `6769a852b9c4f1d412e21cf0d9f0b288028e3b7c`; deployment IDs lần lượt `122ec654-970c-4192-8515-d83915f8c5dc`, `26b8a7a5-ea7c-4efc-8df9-4950c6891839` và `44888678-2a03-49a8-aa9f-7c832deb88b9`.
- Public verifier đạt `15/15`, `failed_check_count=0`, API version/schema `6769a85… / 20260909_0019`, web bundle exact-SHA và Auth boundary public đều PASS. Evidence: [p08-staging-parity-20260911-6769a85.json](docs/evidence/p08-staging-parity-20260911-6769a85.json).
- Đây là source/runtime parity slice cho hardening DICOM. Không tạo artifact/Gamma run/report mới; P08 vẫn mở authenticated mutation trên candidate này, fault/ACK/retry/dead-letter, large-input/resource, oracle promotion và release handoff.

## P06 — declared type và upload queue — local verified slice — 2026-09-11

- Artifact validator giữ declared `artifact_type` là hợp đồng chính: payload JSON được khai báo DICOM không đi vào measurement validator và trả `ARTIFACT_TYPE_MISMATCH`; test duplicate cùng checksum/type vẫn tái dùng artifact và thêm role thiếu theo organization scope.
- QA Archive đã chuyển từ upload đơn file sang queue theo case: có thể chọn nhiều file, snapshot `artifactType`/`logicalRole` lúc enqueue, upload tuần tự, giữ các file thành công khi một file lỗi và retry riêng file lỗi. Mỗi thao tác Download vẫn gọi API lấy URL mới thay vì giữ lại signed URL cũ.
- Local checks: backend `test_artifacts.py` `6 passed`; frontend lint, typecheck, Vitest `17/17` và production build PASS. Evidence: [p06-local-upload-queue-20260911.json](docs/evidence/p06-local-upload-queue-20260911.json).
- Đây là local implementation slice. Chưa đóng P06-W04/P06-VERIFY: staging browser queue với lỗi có chủ ý, storage fault/reconciliation, download byte re-hash và full S/E/C/release evidence còn phải thực hiện.

## P06-W04 — queue orchestration hardening — local verified — 2026-09-11 / `8c8f9bd`

- Tách điều phối upload queue khỏi `QAArchivePage`: batch dùng snapshot item, upload tuần tự, giữ success trước đó khi item sau lỗi, và retry chỉ nhận `FAILED` item thuộc case hiện hành; tránh stale lookup trong async state.
- Local checks trên commit `8c8f9bdb5fb903ebec80e0a3832e743b974398ee`: lint, typecheck, production build và Vitest `8 files / 19 tests` đều PASS. Evidence: [p06-local-upload-queue-helper-20260911.json](docs/evidence/p06-local-upload-queue-helper-20260911.json).
- Đây vẫn là local hardening slice; staging fault/retry có chủ ý, storage reconciliation, signed-download byte re-hash và full P06 S/E/C/release vẫn mở.

## P20-W01 — final documentation/runtime parity checkpoint — staging verified slice — 2026-09-11 / `06b818f`

- Sau khi ghi evidence, API `07f847c0-7e05-470a-a161-3758ca174302`, web `0bab32af-56cb-450d-9754-39c4f5b3847f` và worker `a37687b6-b192-44ab-9a47-7acb5f919d85` đều `SUCCESS` trên source SHA `06b818fc6edc0ebe4353c1fd018c519ccfc6f25f`.
- Public verifier đạt `15/15`, `failed_check_count=0`, schema `20260909_0019`; health/readiness/version, OpenAPI/Auth boundary và web bundle source marker đều PASS. Evidence: [p20-staging-public-parity-20260911-06b818f.json](docs/evidence/p20-staging-public-parity-20260911-06b818f.json).
- Mốc này thay thế checkpoint runtime `7ee71c8` về mặt current-candidate; không thay đổi kết luận rằng P06/P20 full fault, restore, rollback, alert và handoff vẫn mở.

## P06/P20 — authorized RTDOSE staging upload và current web parity — staging verified slice — 2026-09-11 / `0abba6e`

- Theo xác nhận trực tiếp của người dùng, fixture tổng hợp `docs/fixtures/gamma-rtdose-v1-smoke.dcm` (898 bytes, SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`) đã được upload một lần vào case `ed7ddbe5-811a-4463-a270-b0386f64644d` (`P11 E2E Synthetic QA 20260910 B7C3`) trên staging với `REFERENCE/DICOM`.
- UI xác nhận tạo artifact và input manifest; validate trả `VALID`, `0` lỗi, `0` cảnh báo; preflight hiện `1 RTDOSE · 0 RTSTRUCT · 0 CT VALID`. Không tạo QA run/report mới và không chạm production. Evidence: [p06-staging-rtdose-upload-20260911.json](docs/evidence/p06-staging-rtdose-upload-20260911.json).
- API `c57d438d-ab28-473f-8d2a-6da3499a3a59`, web `bfb89696-b666-48e3-8a3a-74c2e60cfde2` và worker `4617b9ab-771e-40fc-b351-5ac03c106191` đều `SUCCESS` trên cùng source SHA `0abba6e229208ac75a9657a9ffc962086553d01f`. Public verifier đạt `15/15`, schema `20260909_0019`, và web bundle đã chứa marker upload queue.
- Đây là `STAGING_VERIFIED_SLICE`, không đóng P06-W04/P06-VERIFY: queue fault/retry có chủ ý, storage fault/reconciliation, signed-download byte re-hash, full S/E/C và release/handoff vẫn mở.

## P06/P20 — queue hardening deployed and exact-SHA parity — staging verified slice — 2026-09-11 / `7ee71c8`

- Sau khi queue orchestration được harden local, API `6265b273-2f52-4bc1-a4c1-2803f4164a4b`, web `90b74c9d-e655-4024-9238-64d900c496d2` và worker `eb4f6c5e-034b-4775-8898-f63a7ef8ebc7` đều `SUCCESS` trên source SHA `7ee71c8a46cba67fde14516d2d566598f3313fc2`.
- Public verifier đạt `15/15`, `failed_check_count=0`, API version exact SHA, schema `20260909_0019`, OpenAPI/Auth boundary và web exact-SHA marker đều PASS. Evidence: [p20-staging-public-parity-20260911-7ee71c8.json](docs/evidence/p20-staging-public-parity-20260911-7ee71c8.json).
- Đây là parity/runtime evidence cho candidate mới; không thay thế staging queue fault/retry, signed-download byte re-hash, storage reconciliation hoặc full P06/P20 S/E/C.

## P20-W01 — Operational status auto-refresh — local verified — 2026-09-11 / `7df7cb8`

- Trang `/app/system/status` đã bổ sung polling 30 giây cho health, readiness, version và queue metrics khi có session; polling vẫn chạy khi tab ở nền.
- Khi đang refresh, UI giữ dữ liệu quan sát gần nhất và hiển thị `Đang cập nhật…`; khi không refresh, UI hiển thị thời điểm `dataUpdatedAt` gần nhất để tránh hiểu nhầm dashboard là dữ liệu realtime liên tục.
- Local evidence: test `7 files / 17 tests`, lint, typecheck và production build đều PASS. Evidence: [p20-local-status-auto-refresh-20260911-7df7cb8.json](docs/evidence/p20-local-status-auto-refresh-20260911-7df7cb8.json).
- Đây mới là `LOCAL_VERIFIED`; chưa phải staging deployment, authenticated queue probe hoặc alert delivery đến kênh vận hành thật. P20-W01 và các gate P20 khác vẫn mở.

## P20-W01 — Operational status auto-refresh — staging partial — 2026-09-11 / `3d764e4`

- API, web và worker staging đã được deploy cùng source SHA `3d764e40bcec98c229eb9992d4af85636c6cf784`; deployment tương ứng là API `3c94f3c7-fab0-464c-abb6-ea61fc0d9494`, web `6cff64bd-54d5-480b-bfc6-05c9e4a4c7d1`, worker `c9a87b51-e060-43ab-b6cb-bee7165dc0b3`, cả ba `SUCCESS`.
- `scripts/verify-public-deployment.ps1` với expected SHA và schema `20260909_0019` đạt `passed=true`, `failed_check_count=0`, `15/15` checks; health/readiness/version, OpenAPI/Auth boundary và web bundle exact-SHA đều PASS. Evidence: [p20-staging-status-refresh-public-20260911-3d764e4.json](docs/evidence/p20-staging-status-refresh-public-20260911-3d764e4.json).
- Đây là `STAGING_PARTIAL`: chứng minh candidate đã lên đúng source và public contract, không chứng minh authenticated queue metrics, alert delivery, backup/restore, rollback hoặc production readiness. P20-W01 vẫn mở.

## P18/P20 — Phân biệt terminal failure counter với active outage — staging readback — 2026-09-11 / `1e97663`

- Status page staging đọc được Redis `available/configured`, stream `11`, pending `0`, cùng `failed=2`. Đối chiếu Gamma history cho thấy hai run FAILED là các negative validation path đã lưu: `d902d9c0-3b15-4367-8df9-ca0a6274c3f3` (`2D` với evaluation grid `3D`) và `e33968e2-1ac3-4db7-953f-4e97f78b2d0e` (reference/evaluation khác dimensionality); cả hai trả `GAMMA_DIMENSIONALITY_MISMATCH` đúng expected contract.
- UI và runbook đã đổi cách diễn đạt thành `failed (terminal history)` và yêu cầu mở error snapshot/attempt trước khi triage. Không retry, xóa hoặc reset hai run này; chúng là evidence negative test, không phải sự cố worker mới.
- Đây là readback/semantics evidence, chưa phải alert delivery, fault injection hoặc full P18 recovery gate.

## P20-W01 — Operational probe và schema-parity check — staging partial — 2026-09-11 / `3102119`

- Đã bổ sung `scripts/verify-operational-probes.ps1`, một probe fail-closed có thể chạy lại với đúng `ApiBaseUrl`, `WebBaseUrl`, release SHA và schema revision. Probe đọc riêng `/api/v1/health`, `/api/v1/ready`, `/api/v1/version`, kiểm schema parity, kiểm web `/app` và dò secret marker trong HTML; queue metrics chỉ chạy khi caller chủ động cung cấp access token và token không được ghi vào output.
- Chạy trên staging candidate `31021192c5dd4b726d8da2183d7e01d26d4e0df2` với schema `20260909_0019`: `passed=true`, `failed_check_count=0`, health/readiness/version/web và secret-marker checks đều PASS. Queue probe ghi `NOT_RUN` có chủ đích vì lần chạy public không cung cấp session token. Evidence: [p20-staging-operational-probes-20260911-3102119.json](docs/evidence/p20-staging-operational-probes-20260911-3102119.json).
- Negative control với expected version cố ý sai trả exit code `1`, `passed=false` và chỉ fail `api.version.expected`; chứng minh probe không biến source drift thành PASS. Alert tới kênh thật, authenticated queue probe, backup/restore provider, owner handoff và các gate P20 còn lại vẫn chưa đóng.

## P17/P19 — RTDOSE authorization + CT overlay recheck — staging partial — 2026-09-11 / `3e46479`

- Người dùng đã xác nhận cho phép sử dụng/upload fixture RTDOSE tổng hợp trong case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`. Fixture `gamma-rtdose-v1-smoke.dcm` đã tồn tại, `RTDOSE/VALID`, checksum local và prefix trên UI khớp (`ca5c9168eb9b...`); hệ thống không tạo artifact trùng.
- Commit `3e46479c8784cebdc5fd4c41e865645b3da9ac63` đã được deploy exact SHA cho API, web và worker; ba deployment đều `SUCCESS`. Public verifier đạt `15/15`, `failed_check_count=0`, schema `20260909_0019`, health/ready/version/OpenAPI/Auth boundary và web source marker đều khớp: [p19-staging-public-recheck-20260911-3e46479.json](docs/evidence/p19-staging-public-recheck-20260911-3e46479.json).
- Browser authenticated sau reload đọc đúng build `3e46479`, preflight `2 dose · 1 structure`, RTDOSE fixture đang được chọn, RTSTRUCT/ROI `#1 · P17_TARGET` và saved DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` vẫn `COMPLETED`; không tạo run/artifact mới.
- CT preview trên candidate mới hiển thị lát cắt `#1` ở trạng thái `LPS LINKED`, overlay `NEAREST_NEIGHBOR_IN_PATIENT_LPS`, ROI và crosshair dose-grid center. Kiểm tra lát cắt `#3` cho `NO DOSE OVERLAP` với cảnh báo rõ ràng và overlay rỗng, sau đó đưa lại về lát cắt hợp lệ. Evidence: [p17-staging-rtdose-ct-browser-recheck-20260911-3e46479.json](docs/evidence/p17-staging-rtdose-ct-browser-recheck-20260911-3e46479.json).
- Đây là staging authenticated readback/compatibility evidence, chưa đóng toàn bộ P17/P19. Full negative/fault/resource/volume, independent-oracle promotion, two-identity mutation E2E, provider restore, rollback, alert/owner handoff, browser filename finalization và production promotion vẫn mở.

## P17/P19 — final current-candidate parity and RTDOSE readback — staging partial — 2026-09-10 / `19857bd`

- Commit `19857bd8515bfbc86835527aadc145278b837dc3` đã được deploy thành công đồng thời cho API, web và worker staging. Deployment IDs là API `60c4bcde-2ddc-4b6a-b586-d51385926c1c`, web `7cd043f4-854d-4399-bdb3-dd2ff0639003` và worker `74c69765-7440-4953-9e30-21338b31fe2d`; cả ba `SUCCESS` và cùng source SHA.
- Public verifier theo exact SHA đạt `15/15`, `failed_check_count=0`, API health/ready/version, schema `20260909_0019`, OpenAPI, Auth boundary và web bundle marker đều PASS: [p19-staging-public-recheck-20260910-19857bd.json](docs/evidence/p19-staging-public-recheck-20260910-19857bd.json).
- Browser authenticated sau reload đọc đúng build `19857bd`, case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`, preflight `2 dose · 1 structure`, RTDOSE `gamma-rtdose-v1-smoke.dcm` `VALID` với SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, RTSTRUCT/ROI `#1 · P17_TARGET`, saved DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` và result SHA `cf2799b8afeafa68cf60a330eac9adff123cca5c7ceacfc0eab78132b0c0359c` giữ nguyên. Không tạo run/artifact mới và không upload trùng: [p17-staging-rtdose-authenticated-recheck-20260910-19857bd.json](docs/evidence/p17-staging-rtdose-authenticated-recheck-20260910-19857bd.json).
- Planning contract sau khi sửa expected versions của verifier đạt `passed=true`, `failed_check_count=0`, đủ 21 phase; evidence được giữ tại [p0-planning-contract-20260910-e5197ce.json](docs/evidence/p0-planning-contract-20260910-e5197ce.json).
- Đây vẫn là current-candidate parity/readback partial. P17/P19/P20 còn mở các gate full negative/fault/resource/volume, two-identity mutation E2E, provider backup/restore, rollback, alert/owner handoff, pilot và production promotion.

## P17/P19 — current candidate parity and RTDOSE authenticated recheck — staging partial — 2026-09-10 / `e5197ce`

- Sau khi commit tài liệu `e5197ce4634f93b81267479d9b68382e97f7e4e9` được push, web staging tự nhận candidate mới trong khi API/worker vẫn phục vụ `380012e`; public verifier với expected `380012e` đã bắt đúng drift ở `web.bundle.expected_version` (`1` lỗi). Evidence drift được giữ tại [p19-staging-public-recheck-20260910.json](docs/evidence/p19-staging-public-recheck-20260910.json).
- Đã yêu cầu redeploy có kiểm soát API, web và worker staging cùng SHA `e5197ce`; deployment mới lần lượt là API `d3e6c135-6602-420e-9609-d4ba9098e5fe`, web `b670b3de-cecc-473c-960b-58a7374fb1da` và worker `675a146e-cace-4c63-bf28-fdf7eca25bef`, đều `SUCCESS`. Không xóa database/object và không tạo lại fixture.
- Public verifier sau khi đồng bộ đạt `15/15`, `failed_check_count=0`, API version/readiness và web bundle cùng `e5197ce`, schema `20260909_0019`: [p19-staging-public-recheck-20260910-e5197ce.json](docs/evidence/p19-staging-public-recheck-20260910-e5197ce.json).
- Authenticated browser trên đúng candidate `e5197ce` mở lại case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`: preflight `2 dose · 1 structure`, RTDOSE `gamma-rtdose-v1-smoke.dcm` `VALID` với SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, RTSTRUCT hợp lệ, ROI `#1 · P17_TARGET`, DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` và result SHA `cf2799b8afeafa68cf60a330eac9adff123cca5c7ceacfc0eab78132b0c0359c` được đọc lại; không tạo run/artifact mới và không upload trùng. Evidence: [p17-staging-rtdose-authenticated-recheck-20260910-e5197ce.json](docs/evidence/p17-staging-rtdose-authenticated-recheck-20260910-e5197ce.json).
- Đây là parity và authenticated readback partial gate. P17/P19 vẫn mở full negative/fault/resource/volume, two-identity mutation E2E, provider backup/restore, rollback, alert/owner handoff và production promotion.

## P9 — PDF Unicode renderer correction — local verified / staging revalidation required — 2026-09-10

- Visual inspection of the previous staging PDF export found corrupted Vietnamese glyphs (`?`) even though the payload had a valid PDF header. This was treated as a release-blocking visual defect, not as a cosmetic warning.
- The renderer is now `report-renderer-0.2`: it embeds the pinned `DejaVuSans.ttf` asset, emits a Type0/CIDFontType2 Unicode font with `Identity-H` encoding, `ToUnicode` mapping and deterministic CID-to-GID mapping. `fonttools==4.63.0` is pinned in both `pyproject.toml` and `requirements.lock`.
- Local evidence: focused report suite `7 passed`, Ruff pass, strict mypy pass, wheel build pass, wheel inspection confirms `rt_connect_api/assets/DejaVuSans.ttf` is packaged, and Poppler visual inspection shows Vietnamese title/block text without fallback replacement.
- This correction is not yet a staging release. The new commit must be deployed to API/web/worker with exact-SHA parity; Report Builder must regenerate PDF/PNG/JSON/CSV from the staging DVH report, and the new PDF must be rendered and visually inspected before P9 can advance beyond partial verification. Existing staging evidence remains historical and is not silently rewritten.
- Local checkpoint evidence was followed by staging revalidation below; the public exact-SHA record is [p9-staging-unicode-public-smoke-20260910-380012e.json](docs/evidence/p9-staging-unicode-public-smoke-20260910-380012e.json).

## P9 — renderer-aware export idempotency correction — local verified / staging revalidation required — 2026-09-10

- Sau khi API chạy `report-renderer-0.2`, browser Report Builder cũ dùng lại key `report-{revision}-{format}` và nhận `EXPORT_IDEMPOTENCY_CONFLICT` với export cũ của renderer `0.1`. Đây là lỗi namespace tương thích khi renderer đổi phiên bản.
- Frontend đã thêm namespace ngẫu nhiên theo phiên trang vào idempotency key; cùng phiên vẫn replay đúng, nhưng lần tải trang sau renderer migration không bị khóa bởi export cũ. Server fingerprint và conflict semantics vẫn giữ nguyên.
- Local evidence: web lint, typecheck, Vitest `17/17` và production build pass. Commit này phải được deploy exact SHA cho web (và đồng bộ API/worker theo release policy) trước khi tạo lại export. Chưa ghi staging export mới và chưa đóng P9 visual gate.

## P9/P19 — renderer 0.2 + idempotency namespace — staging verified partial — 2026-09-10 / `380012e`

- API, web và worker staging đã chạy đồng bộ exact SHA `380012ed3f2140efd4f1560c2f627176831e495f`, schema `20260909_0019`; public verifier đạt `15/15`, `failed_check_count=0`. Deployment IDs lần lượt là API `a3d68476-d635-4c6d-9b6a-8ee6f338096f`, web `29f2ce35-2e49-415c-911e-e5184bcd074b`, worker `00aaaca7-1ba4-4089-a920-b56448e2dbfe`.
- Browser reload nhận build mới, mở report `P17 staging bound DVH report` rev 1 từ DVH run `d8230d1d-badd-4c0c-b044-dcc4434215a6` và tạo bốn export mới: JSON `15,582` bytes, CSV `1,190`, PDF `382,747`, PNG `2,243`. JSON/CSV parse pass và ghi renderer `report-renderer-0.2`; PDF header/EOF, embedded Unicode font, ToUnicode, UTF-16 stream check và visual inspection pass; PNG signature pass.
- PDF staging đã được render thành PNG bằng Poppler và kiểm tra trực quan: `P17 staging bound DVH report`, `DVH và đánh giá giới hạn explicit`, `Cảnh báo và trạng thái review` đều hiển thị đúng tiếng Việt, không còn `?`. Report revision và DVH run không bị mutation; RTDOSE `gamma-rtdose-v1-smoke.dcm` chỉ được reuse, không upload trùng.
- Evidence chi tiết: [p9-staging-unicode-export-20260910-380012e.json](docs/evidence/p9-staging-unicode-export-20260910-380012e.json). Đây là `STAGING_UNICODE_EXPORT_CONTENT_AND_VISUAL_PARTIAL`; `.crdownload` là giới hạn quan sát filename của CUA harness, còn storage fault/retry, provider restore, rollback, full P18/P19 và production promotion vẫn mở.

## P17/P19 — current staging DVH export content verification — partial verified — 2026-09-10 / `c11fca0`

- Trên web build `c11fca0451f0a16d3bdf178383d7a8f45889e770`, authenticated browser mở lại case tổng hợp `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`, preflight `VALID`, saved run `d8230d1d-badd-4c0c-b044-dcc4434215a6`, engine `p17-dvh-1.1.0` và result SHA `cf2799b8afeafa68cf60a330eac9adff123cca5c7ceacfc0eab78132b0c0359c`.
- JSON export tải được `24,673` bytes, parse thành công, `run_id` và `result_sha256` khớp provenance UI. CSV export tải được `15,901` bytes, parse thành công với `25` rows và đủ section `input/result/warning`.
- Edge/CUA giữ hậu tố tạm `.crdownload`; đây là giới hạn quan sát của harness, không phải nội dung export thiếu. Bằng chứng content-level completion được ghi tại [p17-p19-staging-dvh-export-current-20260910-c11fca.json](docs/evidence/p17-p19-staging-dvh-export-current-20260910-c11fca.json). Không tuyên bố filename rename độc lập, production readiness, backup/restore, rollback hoặc full P18/P19.

## P9/P19 — current staging Report Builder export content verification — partial verified — 2026-09-10 / `bd47925`

- API/web/worker staging đã được đồng bộ exact SHA `bd4792505acea66113953f1d525e571cbe8ca155`; public verifier đạt `15/15`, schema `20260909_0019`. Deployment IDs: API `0ffdee7b-ff82-47a5-966c-304b046a6728`, web `02c59a4c-d78c-4cb5-b790-2462566ec715`, worker `11124466-d67f-4d6e-975c-a6090a35f112`.
- Browser đã chọn revision hiện có `P17 staging bound DVH report`, rev 1, source run `d8230d1d-badd-4c0c-b044-dcc4434215a6`, không lưu revision mới. Bốn export đều được tạo: JSON `15,582` bytes parse PASS; CSV `1,190` bytes parse PASS/27 rows; PDF `1,046` bytes có magic `%PDF`; PNG `2,243` bytes có signature PNG.
- JSON content giữ `report_key`, `source_id`, `source_type=DVH`, renderer `report-renderer-0.1` và `content_sha256` đúng revision. Evidence: [p9-p19-staging-report-export-current-20260910-bd47925.json](docs/evidence/p9-p19-staging-report-export-current-20260910-bd47925.json). `.crdownload` filename rename, visual human review, provider fault/retry, backup/restore và production gate vẫn mở.

## P8/P18/P19 — authenticated Gamma staging mutation E2E — partial verified — 2026-09-10 / `1badb66`

- Trên web build `1badb6616d1a68f7178b2aefd10c71adc95a826b`, phiên authenticated đã reuse fixture RTDOSE/VALID `gamma-rtdose-v1-smoke.dcm` trong case tổng hợp `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`; không upload bản sao. Evaluation là `gamma-measurement-3d-v1-smoke.json`; preflight hiển thị `VALID`.
- Negative path: cấu hình `2D / FULL_ROI / max_gamma=2` với evaluation grid 3D tạo run `d902d9c0-3b15-4367-8df9-ca0a6274c3f3`, `FAILED`, mã `GAMMA_DIMENSIONALITY_MISMATCH`; không phát sinh PASS giả.
- Positive path: đổi dimensionality sang `3D` rồi submit tạo run `86cc4d5e-4a87-4dcb-a6f5-94c125029c60`, `COMPLETED/PASS`, attempt `1`, 8/8 điểm, coverage `1`, Gamma P95 `0`, engine `gamma-nd-p8.2`; kết quả hiển thị lại trên UI sau mutation qua API/worker thật.
- Evidence: [p8-p19-staging-authenticated-gamma-e2e-20260910-1badb66.json](docs/evidence/p8-p19-staging-authenticated-gamma-e2e-20260910-1badb66.json). Đây là `STAGING_AUTHENTICATED_MUTATION_E2E_GAMMA` cho một identity/case; không đóng two-identity membership/invitation, direct PostgreSQL/Redis/object assertion, full staging fault/resource, provider restore, rollback, alert hoặc production promotion.

## P18 — staging API restart/recovery subtest — partial verified — 2026-09-10 / `135a24f`

- API staging được yêu cầu redeploy có kiểm soát cùng SHA `135a24faf4e2659b8c4fe9a98920efb357b392bc`, không xóa database/object. Probe đầu tiên sau yêu cầu trả `ready`, schema `20260909_0019`, version đúng SHA; public verifier sau propagation đạt `15/15`, `failed_check_count=0`.
- Browser authenticated reload route Gamma trên cùng case giữ API thật, build `135a24f…`, RTDOSE reference, measurement evaluation và `PREFLIGHT VALID`. Evidence: [p18-staging-api-restart-recovery-20260910-135a24f.json](docs/evidence/p18-staging-api-restart-recovery-20260910-135a24f.json).
- Đây là `STAGING_PARTIAL_API_RESTART_RECOVERY`; chưa phải API in-flight crash/ack test và không đóng DB/Redis/storage/renderer fault injection, restore, rollback hoặc full P18.

## P19-W01 — current staging release manifest — support evidence verified — 2026-09-10 / `9f8378c`

- Manifest redacted `staging-9f8378c` dùng deployment ID thật của API `db38336d-649e-4e05-baa8-2c669d486c2b`, web `d00e2ac1-d16b-41a6-88ae-48f9185a7608` và worker `07068c3e-15af-439f-a837-e565e90b2f84`; source SHA ba service cùng `9f8378c171f8b220f3c5b4159f505479bcd662c0`, schema `20260909_0019`, fixture hash và engine/renderer version đều được ghi.
- `scripts/create-release-manifest.py --verify-manifest` trả `valid=true`, `error_count=0`, `service_sha_parity=true`: [release-manifest-staging-9f8378c.json](docs/evidence/release-manifest-staging-9f8378c.json).
- Manifest ghi rõ production promotion bị chặn bởi provider backup/restore/rollback chưa có; `release_gate=ELIGIBLE` chỉ là integrity/source-parity gate của manifest staging, không phải P19 DONE-v2.

## P19 — staging exact-SHA public parity after P18 documentation packet — partial verified — 2026-09-10 / `8dffbb9`

- API, web và worker staging đã được yêu cầu deploy cùng source SHA `8dffbb9f48906131e99143f11b14d2abecd9a233`; public verifier kiểm tra exact SHA và schema `20260909_0019` đạt `15/15 PASS`, `failed_check_count=0`.
- Các assertion PASS gồm health/readiness/version, OpenAPI CT preview và membership/invitation, unauthenticated organization boundary `401`, web index/bundle, CT/membership markers và source SHA marker. Evidence: [p19-staging-public-smoke-20260910-8dffbb9.json](docs/evidence/p19-staging-public-smoke-20260910-8dffbb9.json).
- Đây là `STAGING_SOURCE_PARITY_AND_PUBLIC_SMOKE`, không nâng P19 thành DONE-v2: authenticated remote E2E, direct PostgreSQL/Redis/object evidence, fault/resource, backup/restore, rollback rehearsal, alert/owner handoff và production promotion vẫn mở.

## P19 — effective settings and authenticated remote readback — partial verified — 2026-09-10 / `3e79f48`

- `scripts/verify-railway-effective-settings.ps1` đọc Railway GraphQL bằng token chỉ trong bộ nhớ, kiểm tra API/web/worker cùng environment/service IDs, root/Dockerfile/healthcheck/pre-deploy/start command, required variable names, forbidden secret/browser-database names, private DB/Redis host classification, external S3 endpoint classification, CORS origin, Vite API/Auth values và worker không có public-domain variable. Kết quả `passed=true`, `failed_check_count=0`; report không chứa secret/database URL/patient data: [p19-railway-effective-settings-20260910.json](docs/evidence/p19-railway-effective-settings-20260910.json).
- Browser Edge với authenticated session đã đọc `/app/organization`, `/app/qa`, case DVH, `/app/reports`, `/app/biological` và `/app/system/status` trên build `3e79f488...`; DVH deep-link/reload giữ run `d8230d1d...`, D95 `5.200 Gy`, input RTDOSE/RTSTRUCT và warning CT dose-native. Evidence: [p19-staging-authenticated-remote-readback-20260910-3e79f48.json](docs/evidence/p19-staging-authenticated-remote-readback-20260910-3e79f48.json).
- Status page vẫn hiển thị `failed=1` ở Gamma queue counter lịch sử; readback không che giấu hoặc reset counter. Đây là tín hiệu để P18 fault/incident triage tiếp tục, không được diễn giải là toàn bộ queue đã PASS. P19 vẫn thiếu two-identity/mutation E2E, export/download, rollback, alert/restore và production promotion.

## P18 — staging worker restart/recovery subtest — partial verified — 2026-09-10 / `1c0210c`

- Worker staging được redeploy cùng commit hiện hành để mô phỏng restart có kiểm soát; Railway deployment `b007ed76-f3c6-4ba8-b70d-9001503ad9db` báo `SUCCESS`, metadata giữ root `/apps/api`, start `python -m rt_connect_api.worker`, không healthcheck/pre-deploy.
- Trước/sau trên `/app/system/status`, health `OK`, readiness `READY`, schema `20260909_0019`, schema parity `MATCH`, Redis `available/configured`, stream `9`, pending `0`; không upload, calculation, report hoặc database/object deletion. Evidence: [p18-staging-worker-restart-recovery-20260910-1c0210c.json](docs/evidence/p18-staging-worker-restart-recovery-20260910-1c0210c.json).
- Đây chỉ là `STAGING_PARTIAL_RESTART_RECOVERY`; API/DB/Redis/storage/renderer fault injection, retry/dead-letter, restore plan execution, volume/failure budget và full P18 regression/pilot vẫn mở.

## P8/P18 — local Redis worker reliability recheck — verified locally — 2026-09-10 / `3fe1db2`

- Sau khi service Redis trong `docker-compose.yml` được khởi động lại, `scripts/verify-local-gamma-queue.py` chạy trên commit `3fe1db2ab3139dec97090d0660278e419c8c6177` đạt `passed=true`; evidence: [p8-local-redis-worker-smoke-20260910.json](docs/evidence/p8-local-redis-worker-smoke-20260910.json).
- Happy path, duplicate dispatch/terminal replay, ACK failure recovery (`pending 1 → 0`, durable result giữ nguyên, không tạo attempt thứ hai), bounded retry/dead-letter sau 3 output và malformed-message quarantine đều PASS; stream/key/bucket/database tạm được cleanup.
- Đây là `LOCAL_COMPOSE_REDIS_WORKER`, không thay cho staging fault injection, resource/large-input, Railway provider backup/restore, pilot hoặc production release gate.

## P13 — staging BED/EQD2 calculation, immutable readback and export — partial verified — 2026-09-10 / `b712a383`

- Trên web build `b712a383fb806188c794481720e7051e89168fe4`, browser authenticated đã chọn scenario SAVED `P12_STAGING_BIO_SCENARIO_E21`, revision `3` (`e3bcce19-d769-4873-b0e6-45a82e66ee32`) và validate-only thành công trước khi lưu snapshot.
- Known-answer fixture `D=60 Gy`, `n=30`, `d=2 Gy/fx`, `alpha/beta=10 Gy` cho snapshot `COMPLETED`: `BED=72 Gy10`, `EQD2=60 Gy`; model `biological.bed-eqd2`, version `p13-lq-1.0.0`, chart dataset `303` points, checksum `0d9dff8f381ca6dd3066d0606ea2a8ad452bcd47c25e5fa300bddf8d866c4c19`. Snapshot ID `12ba1966-e214-414a-a7a2-d6155fc856d8`; idempotency key `p13-a3dfbcd2-d9f9-4d46-affc-3c718df0ca88`.
- Fresh browser tab đọc lại đúng build, scenario revision, trạng thái `COMPLETED`, BED/EQD2, model và checksum dataset. Export JSON và CSV đều trả toast thành công. Negative `D=61` với `n=30`, `d=2` bị chặn bằng `FRACTIONATION_INCONSISTENT` trên hai field, validate-only không tạo snapshot.
- Evidence: [p13-staging-bed-eqd2-20260910-b712.json](docs/evidence/p13-staging-bed-eqd2-20260910-b712.json). RTDOSE tổng hợp đã được người dùng cho phép nhưng artifact đã tồn tại trong case staging và được reuse; không upload trùng, không gắn biological calculation với QA case.
- Đây là `STAGING_PARTIAL_PASS`, chưa phải `DONE-v2`: direct PostgreSQL/checksum, cross-organization scope, idempotency replay/conflict, đầy đủ S/E/C/fault, release manifest và production parity vẫn mở. Filename completion của browser download vẫn `UNVERIFIED` do harness giữ đuôi tạm.

## P14 — staging same-context comparison, negative context guard and export — partial verified — 2026-09-10 / `46121fe`

- Trên build `46121fe90d3161253b4ee181b70463f6c738e619`, browser authenticated đã dùng hai P13 snapshot cùng scenario `45550fa4-b635-4d9f-90bb-e0d2cd77c531`, revision `e3bcce19-d769-4873-b0e6-45a82e66ee32`, tissue/model context: `70 Gy/35×2` (`ed85e343-687b-4385-a7da-e909458cece5`) và `60 Gy/30×2` (`12ba1966-e214-414a-a7a2-d6155fc856d8`). Validate-only pass không mutation.
- Comparison `57c90796-22a4-4c44-80c8-99934a479b1d` lưu `COMPLETED`, model `biological.plan-comparison · p14-comparison-1.0.0`, baseline `option-a`: `BED=84/EQD2=70`; option B: `BED=72/EQD2=60`, delta `-12 Gy/-14,286%` và `-10 Gy/-14,286%`, result checksum `42885d2c53744a93afed582ba364b1a5b02ebe24cc953ea781d48d13d172927d`.
- Fresh tab đọc lại kết quả và history `4` comparison; JSON/CSV export pass. Negative context mismatch khi chọn snapshot khác scenario/revision/tissue bị chặn bằng `COMPARISON_CONTEXT_MISMATCH`, không tạo snapshot. Evidence: [p14-staging-browser-20260910-46121fe.json](docs/evidence/p14-staging-browser-20260910-46121fe.json).
- Đây là `STAGING_PARTIAL_PASS`: direct PostgreSQL/scope, idempotency replay/conflict, đầy đủ S/E/C/fault, release manifest và production gates vẫn mở; filename completion download vẫn `UNVERIFIED`.

## P15 — staging re-irradiation and fraction compensation — partial verified — 2026-09-10 / `8d20fc2`

- Trên build `8d20fc2bf7d38985875b0ed1a2eaa826bf30586c`, re-irradiation đã validate→save→fresh readback với scenario revision `e3bcce19-d769-4873-b0e6-45a82e66ee32`; run `68c005dc-5a56-4d87-b7e6-1101a470307e` `COMPLETED`, model `biological.re-irradiation · p15-lq-reirradiation-1.0.0`, checksum `b871ba88a1120e35637732f95ad6367cca843fd6eaffb0c4553ca44bb486fd8c`, synthetic OAR tổng `BED=133.3333 Gy3`, `EQD2=80 Gy`, sensitivity recovery và trạng thái `SPATIAL UNAVAILABLE` đọc đúng.
- Fraction compensation đã validate→save→fresh readback; run `1b7b5cec-0170-409d-81fd-58e1237e2059` `COMPLETED`, model `biological.fraction-compensation · p15-lq-compensation-1.0.0`, checksum `a3067598239035f549c55a70c07f3741f4771f2e5f020dfb1908b33ebd272dd0`. Delivered prefix `2` fraction được khóa; standard còn lại `BED=12/EQD2=10`, alternative `BED=12.2/EQD2=10.1667`, delta BED `+0.2`.
- JSON/CSV export của cả hai operation pass. Spatial request trả warning `SPATIAL_ACCUMULATION_UNAVAILABLE` và không tạo snapshot; delivered prefix không khớp bị chặn bằng `FRACTION_SCHEDULE_INVALID` và không tạo snapshot. Evidence: [p15-staging-browser-20260910-8d20fc2.json](docs/evidence/p15-staging-browser-20260910-8d20fc2.json).
- Đây là `STAGING_PARTIAL_PASS`: direct PostgreSQL/scope, idempotency replay/conflict, đầy đủ S/E/C/fault, release manifest và production gates vẫn mở; spatial accumulation vẫn cố ý `UNAVAILABLE`, filename completion download vẫn `UNVERIFIED`.

## P16 — staging Knowledge Library explicit-use boundary and export — partial verified — 2026-09-10 / `8db01c9`

- Trên build `8db01c982d7169cb250f5bf070c558bab408b7ee`, Knowledge Library đọc lại entry `STAGING_P16_D95_20260910 · v1`, `DOSE_LIMIT`, `PUBLISHED · rev 2`, `UNVERIFIED`, context synthetic `P17_TARGET`, `D95 MIN 5 Gy`, content SHA `818d74572b3ca7eb6c1f8ccd43721448a99dfa8488dcaac774ba1b9f9adde85b`.
- Explicit-use với target `P17_DVH` và override hợp lệ `lower_limit=4.5` tạo snapshot prefix `d5f37a51275f4116248c…`, hiển thị `USER_OVERRIDE` và thông báo chưa tự động áp dụng vào calculator. Export JSON/CSV pass; fresh readback giữ entry `PUBLISHED` và counts `1/1/0`.
- Override field không được hỗ trợ bị chặn bằng `KNOWLEDGE_CONTENT_INVALID`, không tạo snapshot. Evidence: [p16-staging-browser-20260910-8db01c9.json](docs/evidence/p16-staging-browser-20260910-8db01c9.json).
- Đây là `STAGING_PARTIAL_PASS`: direct DB/scope, complete lifecycle/import/clone/compare matrix, P17 current-release binding, fault/idempotency, release manifest và production gates vẫn mở; reference `UNVERIFIED` không được diễn giải thành guideline/clinical approval.

## P17 — current staging RTDOSE/DVH readback after P16 — partial verified — 2026-09-10 / `8db01c9`

- Browser read-only recheck trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đọc được hai RTDOSE, một RTSTRUCT; fixture `gamma-rtdose-v1-smoke.dcm` `RTDOSE/VALID`, SHA-256 đầy đủ `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, đã tồn tại trước readback và không upload/duplicate artifact.
- Run `d8230d1d-badd-4c0c-b044-dcc4434215a6` được đọc lại `FULL`, ROI `#1 · P17_TARGET`, `D95=5.200 Gy`, limit `MIN 5 Gy`, margin `+0.200 Gy`, `explicit_selection=true`, `auto_applied=false`; trạng thái vẫn `REVIEW_REQUIRED` vì source library chưa `AVAILABLE` và CT không được chọn. Không tạo run mới.
- Evidence: [p17-staging-current-readback-20260910-8db01c9.json](docs/evidence/p17-staging-current-readback-20260910-8db01c9.json). Đây là `STAGING_PARTIAL_PASS`; direct DB/scope, full error/fault/resource/volume, cloud report/release và clinical source review vẫn mở.

## P19 — staging exact-SHA public verifier after P13 evidence — partial verified — 2026-09-10 / `796e078`

- API, web và worker staging đều deploy thành công từ exact source SHA `796e078af7ff66f4a1f8645061183859420bf785`; deployment IDs lần lượt `02c0d58d-c892-4834-a3ac-26364586bdfa`, `e56ac637-d30c-4ef6-8cc7-46c76da5024f` và `ca73840b-56e6-4a47-a415-69cfe9c1af21`.
- Public verifier đạt `15/15 PASS`, `failed_check_count=0`; `/health`, `/ready`, `/version`, schema `20260909_0019`, OpenAPI, membership boundary, web index/bundle và source marker đều khớp. Evidence: [p19-staging-public-smoke-20260910-796e078.json](docs/evidence/p19-staging-public-smoke-20260910-796e078.json).
- Đây chỉ là public contract/source-parity sub-gate. Authenticated E2E đầy đủ, private DB/Redis, fault/retry, backup/restore, rollback, alerting và production promotion vẫn mở.

## P12 — staging Biological scenario lifecycle and report integration — partial verified — 2026-09-10 / `e21ad4b`

- Trên web build `e21ad4b7f46aa990ae0bf0d7915b4199e66d62b4`, browser authenticated đã validate scenario tổng hợp mà không tạo mutation; tạo `P12_STAGING_BIO_SCENARIO_E21` ở `DRAFT rev 1`, sửa thành `DRAFT rev 2`, lưu thành `SAVED rev 3`, rồi fresh navigation đọc lại đủ history `3/2/1` cùng snapshot context.
- Clone tạo key `P12_STAGING_BIO_SCENARIO_E21_COPY_8BBA0AF2`; archive chuyển clone sang `ARCHIVED rev 2`. Bộ lọc archived mặc định ẩn clone và khi bật filter đọc lại đúng trạng thái archived. Negative `REFERENCE` thiếu `source_reference` bị chặn bằng `BIOLOGICAL_CONTEXT_INVALID`, không tạo mutation.
- P12-W04 report integration đã chạy: Report Builder lưu report `P12 Biological renderer staging` rev 1 với `source_type=BIOLOGICAL`, source ID `45550fa4-b635-4d9f-90bb-e0d2cd77c531`, block `BIOLOGICAL` và snapshot SHA-256 `f7867b11e05095c049dedf153f39db958828722b7761b185da223b53ff492ce0`; fresh readback giữ source/revision/block và hiển thị export JSON/CSV/PDF/PNG. Evidence: `docs/evidence/p12-staging-browser-20260910-e21ad4b.json`.
- Đây là `STAGING_PARTIAL_PASS`, không phải `DONE-v2`: direct PostgreSQL row/checksum, cross-organization negative probe, đầy đủ S/E/C, resource/provider fault, release manifest và production/rollback vẫn mở. Không có patient data hoặc QA run mới.

## P18 — local backup/restore support recheck — verified locally, staging gate open — 2026-09-10

- `scripts/verify-local-backup-restore.py` đã được bổ sung timeout cho từng lệnh Docker Compose và cơ chế dừng process tree trên Windows. Mục đích là khi Docker CLI/daemon không phản hồi, verifier phải trả evidence có giới hạn thay vì treo vô hạn.
- Lần chạy với `--command-timeout-seconds 10` trả về đúng `passed=false`; lỗi là `Docker Compose command timed out after 10s: ps --services --filter status=running`. `restore_database=null`, `restore_bucket=null`, không tạo restore resource và không có dump/object content được lưu. Evidence: `docs/evidence/p18-local-backup-restore-timeout-20260910.json`.
- Sau khi Docker Desktop/Linux engine được khôi phục, chạy lại với `--command-timeout-seconds 30` đạt `passed=true`: dump `169,924` bytes, row counts/fingerprints khớp, object inventory nguồn/đích đều `0` và hash khớp, database/bucket tạm được cleanup. Evidence: `docs/evidence/p18-local-backup-restore-20260910.json`.
- Evidence timeout trước đó vẫn giữ nguyên để chứng minh verifier fail-closed khi daemon không phản hồi: `docs/evidence/p18-local-backup-restore-timeout-20260910.json`.
- Trạng thái hiện tại là `LOCAL_VERIFIED` cho P18-W03a support path; provider backup/restore, RPO/RTO staging/production, fault injection, pilot/regression, rollback và P18/P20 release gates vẫn mở. Next exact action là kiểm provider restore drill trên candidate được phép, không dùng local PASS để suy ra remote PASS.

## P10 Trend — baseline/maintenance lifecycle controls — local verified — 2026-09-10

- Bổ sung client contract `PATCH /trend-baselines/{baseline_id}` ở web và một panel lifecycle thật trên Trend workspace. Người dùng có thể đọc toàn bộ baseline versions, sửa name/tolerance/action level/effective-to, archive version và giữ `expected_version`; version conflict được hiển thị qua cùng structured-error path, không ghi đè silent.
- Bổ sung maintenance revision panel: sửa marker, archive marker và gửi `expected_revision`; các field thời gian được chuyển lại ISO trước khi gọi API, còn lịch sử revision vẫn do API làm nguồn sự thật.
- Frontend regression mới: `TrendPage.test.tsx` kiểm chứng save baseline với version `2` và archive maintenance với revision `3`; toàn bộ web suite **17/17 PASS**, typecheck, ESLint và production build PASS. Vite vẫn còn cảnh báo chunk >500 kB, không phải lỗi release.
- Đây là `LOCAL_VERIFIED` cho UI/client lifecycle slice. Chưa được coi là staging evidence: cần staging deploy exact-SHA, authenticated edit/archive, stale revision `409`, reload/readback và kiểm tra không rewrite các điểm trend lịch sử.

## P10 Trend — staging baseline/maintenance lifecycle — partial verified — 2026-09-10 / `7343189`

- Candidate `734318947b8ae51c9eebc5275e76e6bdc6478d18` đã được mở trên staging bằng browser đã xác thực tại `/app/trend`. Workspace đọc được `4` baseline versions, `2` maintenance markers trước thao tác, `7` raw points và `4` compatible series.
- Baseline version `4` được sửa với `expected_version=4`, đổi tên thành `P10 lifecycle baseline 7343189`; UI trả toast thành công. Sau thao tác không tạo, xóa hoặc rewrite trend point nào.
- Maintenance marker `P10 baseline maintenance smoke` được archive với `expected_revision=1`; sau reload marker có revision `2`, status `ARCHIVED`, active marker count giảm từ `2` xuống `1`.
- Kiểm thử optimistic concurrency trên marker `Staging QA maintenance smoke`: tab thắng lưu title `Staging QA maintenance concurrent winner` với revision `2`; tab giữ revision cũ `1` bị từ chối bằng `MAINTENANCE_REVISION_CONFLICT`, và title stale không được ghi. Reload xác nhận title thắng vẫn là nguồn sự thật.
- Evidence: `docs/evidence/p10-staging-lifecycle-20260910-7343189.json`. Đây là `STAGING_PARTIAL_PASS`: visual/accessibility, complete P10 S/E/C, large-series, effective-time/rebuild, provider fault/resource, release manifest và production/rollback evidence vẫn mở; P10 chưa `DONE`.

## P19 — staging exact-SHA public smoke after P10 evidence — 2026-09-10 / `6df4ed5`

- Sau khi push packet P10, API, web và worker staging đã được yêu cầu deploy cùng source SHA `6df4ed581be91f193fe1a07c0fc3ef23c18d70c0`. Public verifier kiểm tra candidate thực tế: `15/15 PASS`, `failed_check_count=0`, API version và web bundle cùng exact SHA, schema `20260909_0019`, `/health` `ok`, `/ready` `ready`, OpenAPI routes và unauthenticated organization boundary đều đúng.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260910-6df4ed5.json`. Đây chỉ là public contract/source-parity evidence cho staging; không đóng P19 vì authenticated remote E2E, private dependency, backup/restore, rollback, alert và production promotion vẫn chưa có bằng chứng.

## P11 — staging protocol library and Machine QA consumer readback — partial verified — 2026-09-10 / `27bf051`

- Trên candidate `27bf051`, QA Protocol Library đọc được `3` version không archive; filter archived đọc lại `5` version gồm `STAGING_P11_E2E_B7C3 v1` và `STAGING_P11_QA v1` ở trạng thái `ARCHIVED`. Detail ACTIVE `MACHINE_QA_BASELINE v1` hiển thị revision `1`, `3` rule, source `USER_DEFINED` và applicability `{}`.
- Trên cùng candidate, Machine QA case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đọc đúng protocol ACTIVE, source/revision/rule count và thông báo đã pin protocol snapshot. Hai run lịch sử vẫn `COMPLETED/PASS`, không tạo run mới, không upload fixture và không thay đổi protocol trong lần kiểm tra.
- Evidence: `docs/evidence/p11-staging-consumer-browser-20260910-27bf051.json`. Đây là authenticated consumer readback `STAGING_PARTIAL_PASS`; full P11 S/E/C, cross-consumer recheck, direct DB lineage, release and production gates vẫn mở.

## P8 — staging RTDOSE/Gamma read-only recheck — partial verified — 2026-09-10 / `c9bdfe9`

- Trên candidate `c9bdfe9`, Gamma workspace của case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đọc đúng workflow `PSQA_GAMMA`, fixture reference `gamma-rtdose-v1-smoke.dcm` với fingerprint `ca5c9168…`, evaluation `gamma-measurement-3d-v1-smoke.json` với fingerprint `3ca7a85e…` và trạng thái `PREFLIGHT VALID`.
- Existing run đang chọn là `ENGINE_TEST`, không phải run PSQA 3D mới: `COMPLETED`, engine `gamma-nd-p8.2`, `4/4` điểm đạt, coverage `1`, gamma P95 `0.0708333…`, target `95%`; history hiển thị cả một run `FAILED` để truy vết. Lần recheck không tạo run và không upload fixture.
- Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-c9bdfe9.json`. Đây là read-only partial evidence; không suy ra từ đó rằng PSQA 3D, worker fault/retry, resource gate, independent oracle hay P8 release đã đóng.

## P8 — staging PSQA Gamma 3D synthetic E2E — partial verified — 2026-09-10 / `37130ec`

- Trên candidate `37130ec`, đã chạy đúng một job `PSQA_GAMMA` 3D bằng RTDOSE `gamma-rtdose-v1-smoke.dcm` và measurement `gamma-measurement-3d-v1-smoke.json` đã có sẵn trong case staging. Queue acknowledgement được hiển thị; run `1ac9b02b-3b06-4351-9ee7-fc100ba91bd2` kết thúc `COMPLETED/PASS`, engine `gamma-nd-p8.2`, `8/8` điểm đạt, coverage `1`, gamma P95 `0`.
- Lịch sử tăng lên `10` run và run failed cũ vẫn còn hiển thị; không tạo artifact mới và không upload lại RTDOSE. Đây là staging synthetic E2E happy path, không phải bằng chứng fault/retry/resource/clinical commissioning.
- Evidence: `docs/evidence/p8-staging-psqa-gamma-3d-20260910-37130ec.json`. P8 vẫn mở các gate âm tính, crash-after-commit/ack, bounded retry/dead-letter, workload lớn, independent oracle, release và production.

## P8 — staging RTDOSE_REQUIRED negative input — partial verified — 2026-09-10 / `37130ec`

- Với profile `PSQA_GAMMA`, chọn JSON `gamma-reference-v1-smoke.json` làm Reference bị chặn trước queue bằng trạng thái `PROFILE INPUT MISSING`, message yêu cầu RTDOSE DICOM `VALID`; nút enqueue bị disable.
- Khôi phục lại `gamma-rtdose-v1-smoke.dcm` làm Reference đưa preflight về `PREFLIGHT VALID`, nút enqueue hoạt động và history vẫn giữ `10` run; negative test không tạo mutation.
- Evidence: `docs/evidence/p8-staging-negative-rtdose-required-20260910-37130ec.json`. Đây mới là negative input slice; geometry/frame/dose-scaling, worker fault/retry/resource và release gates vẫn mở.

## P19 — final staging public verifier packet before next handoff — 2026-09-10 / `9fb58ac`

- Exact-SHA public verifier trên candidate `9fb58acadc78938022ffc308181625e0f1596386` đạt `15/15 PASS`, `failed_check_count=0`; API version, web bundle marker và ba service release SHA được kiểm theo candidate, schema `20260909_0019`.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260910-9fb58ac.json`. Phạm vi chỉ là public contract/source parity; P19 vẫn mở authenticated remote E2E đầy đủ, private DB/Redis, backup/restore, rollback, alert và production promotion.

## P10 — staging negative/accessibility recheck — partial verified — 2026-09-10 / `a30e365`

- Trên candidate `a30e365`, Trend workspace đã được đọc bằng accessibility tree: lifecycle tables/actions, filter controls, source links và error/empty/retry states đều có semantic text/controls đọc được.
- Đã kiểm trực tiếp ba negative case bằng browser authenticated: effective interval sai bị chặn với `TREND_BASELINE_INVALID`; metric không tồn tại trả `TREND_EMPTY` với `0` point/series và không zero-fill; timezone sai trả `TREND_TIMEZONE_INVALID` cùng retry. Sau khi khôi phục filter, readback vẫn giữ `7` raw points, `4` series, `4` baselines và `1` active maintenance marker, không có mutation phát sinh từ negative test.
- Evidence: `docs/evidence/p10-staging-negative-accessibility-20260910-a30e365.json`. Accessibility đạt partial; screenshot visual review, full S/E/C/large-series/effective-time/rebuild và release/production gates vẫn mở.

## P10 Trend — staging export, drill-down và negative recheck — 2026-09-10 / `6426ceb`

- Candidate `6426ceb50665f1ceae01e011f2ee5bf6b8a16d65` đang có API/web cùng source SHA; API `/health`, `/ready`, `/version`, OpenAPI và web bundle đạt **15/15 public checks**, schema `20260909_0019`.
- Fresh authenticated browser mở `/app/trend`, đọc được `7` raw points, `4` compatible series, `3` baseline và `1` maintenance marker. Drill-down từ Trend về case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` mở đúng Machine QA source, run `COMPLETED/PASS`, protocol snapshot và source run đều đọc lại được.
- Export theo bộ lọc hiện tại đã được tải và parse: CSV `2,018` bytes, `7` records, có header và bucket lineage; JSON `15,064` bytes, parse được với `4` series, `aggregate=raw`, timezone `Asia/Ho_Chi_Minh`. SHA lần lượt `dfe34e256a0d58f0f790d7d4f04a2916f03402a151aa49cd05e39842d9814f75` và `e5ba525cc37696974fe384526472284adb4478aa4c1b988c79b01c3601d174a4`.
- Negative filter `metric_does_not_exist` trả `TREND_EMPTY`, `0` point/series và không zero-fill. Gộp theo ngày với `output_factor` giữ `2` series, `3` compatible points, mean/min/max `100%` và không trộn protocol context. Evidence: `docs/evidence/p10-staging-trend-browser-20260910-6426ceb.json`.
- Đây là `STAGING_PARTIAL`: browser vẫn quan sát hậu tố `.crdownload`, nên final filename completion, large-series benchmark, projection rebuild/baseline mutation, full S/E/C, fault, accessibility và release/production gates còn mở. Không tạo QA run mới, không upload artifact và không dùng dữ liệu bệnh nhân/PACS.
- Sau khi checkpoint được commit thành `05ff3d29e24cb15826e8335a5a66d6f4bd32f87b`, API/worker staging đã được redeploy đúng SHA để giữ parity với web; public verifier lại đạt **15/15 PASS**, schema `20260909_0019`. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-05ff3d2.json`.
- Trên đúng candidate `2a381ba78ade65e5468d730c46adc6856f7713b8`, Trend đã tạo được một baseline version synthetic cho `STAGING-LINAC-01/output_factor/%` (`100`, tolerance `2`, action level `3`); sau reload, baseline count tăng lên `4`, `7` raw points và `4` series vẫn còn nguyên, không có rewrite hồi tố. Evidence: `docs/evidence/p10-staging-baseline-lifecycle-20260910-2a381ba.json`. Đây mới là happy path create/readback; conflict/invalid/archive/concurrency và projection rebuild vẫn mở.

## P9 deterministic export filename — local verified — 2026-09-10 / `211d9f7`

- Signed report-export URLs now request a deterministic, header-safe `Content-Disposition` filename from the S3-compatible provider. The same contract is applied both when an export is created/replayed and when a download link is renewed; JSON/CSV/PDF/PNG object bytes, checksum, revision snapshot and idempotency behavior are unchanged.
- Local regression verifies all four formats and the download endpoint with `rt-connect-report-export-{export_job_id}.{extension}`. Backend full suite: **169 passed**; Ruff and strict mypy pass; frontend lint, typecheck, Vitest **15/15** and production build pass. Evidence: `docs/evidence/p9-export-filename-20260910-211d9f7.json`.
- This closes the implementation slice only. Staging signed-URL response headers, browser final filename, byte-level PDF/PNG visual review, provider fault/retry and release-manifest evidence remain open.

## P9 deterministic export filename — staging verified partial — 2026-09-10 / `fbbefd0`

- Candidate `fbbefd0d744dbb25bc36a0feaff887a853816a57` is running on staging API/web/worker; public verifier passes **15/15** with schema `20260909_0019`. Authenticated Report Builder loaded Build `fbbefd0…`, reopened report `3b51b1db…` revision 1 and created JSON `15,582`, CSV `1,190`, PDF `1,046` and PNG `2,243` byte exports without changing the report revision or rerunning DVH.
- Browser Downloads observed deterministic names with the new `rt-connect-report-export-{export_job_id}.{extension}` prefix for all four formats. JSON and CSV payloads were parsed; PDF header/EOF and PNG signature were verified; SHA-256 values and job IDs are recorded in `docs/evidence/p9-staging-export-filename-20260910-fbbefd0.json`.
- The browser kept the `.crdownload` suffix during observation, therefore final browser rename/completion is still `UNVERIFIED`. Visual PDF/PNG review, provider fault/retry and release-manifest closure remain open.

## RTDOSE authorization, P17 readback and P9 JSON export — staging verified — 2026-09-10 / `c17fe9a`

- Theo xác nhận của người dùng, fixture RTDOSE tổng hợp được phép dùng trong case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`. Kiểm tra lại trên candidate `c17fe9a1138da4b5b60fe8f070a0367e9e8a07f1` cho thấy `gamma-rtdose-v1-smoke.dcm` đã tồn tại đúng một artifact, checksum đầy đủ `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`, `RTDOSE/VALID`, đang được chọn cùng RTSTRUCT hợp lệ; không tạo artifact trùng.
- P17 giữ run `d8230d1d-badd-4c0c-b044-dcc4434215a6`, `COMPLETED`, `FULL`, `P17_TARGET`, `D95=5.200 Gy`, `MIN 5 Gy`, margin `+0.200 Gy`, nhưng status đánh giá vẫn là `REVIEW_REQUIRED` vì không chọn CT và nguồn giới hạn tổng hợp còn `UNVERIFIED`. Đây là kết quả đúng theo boundary staging, không phải clinical PASS.
- Report `P17 staging bound DVH report` (`3b51b1db-1a6c-437b-8e43-dbaf1e9b73e7`, revision 1) được mở lại từ danh sách, editor hydrate đúng `DVH`, source run và 5 block. JSON export `764f8147-3401-4643-a906-e165a1343168` đọc được source snapshot, RTDOSE checksum, limit-binding snapshot và content SHA trùng revision (`2599b891…`).
- Public verifier của candidate c17 đạt `15/15 PASS`, `failed_check_count=0`, schema `20260909_0019`; evidence chi tiết: `docs/evidence/p16-p17-p9-rt-dose-export-20260910-c17.json`.
- Slice này chỉ đóng thêm authenticated readback/export evidence. P17 full negative/fault/resource/oracle/release, P9 các định dạng export còn lại và các release/production gate vẫn mở.

## P16 → P17 → P9 explicit binding/report — staging verified — 2026-09-10 / `a55f7cc`

- Trên staging, đã dùng dữ liệu tổng hợp để tạo P16 `DOSE_LIMIT` entry `STAGING_P16_D95_20260910`, validate-only đúng schema rồi lưu DRAFT và publish revision 2. Entry giữ `D95 MIN 5 Gy`, `USER_DEFINED · UNVERIFIED`, content SHA-256 `818d7457…`; một payload applicability sai đã bị từ chối bằng `KNOWLEDGE_APPLICABILITY_INVALID` trước khi validate thành công.
- P16 không tự áp dụng vào calculator. Sau khi chọn rõ nguồn `P16 · DOSE_LIMIT đã publish`, P17 đã validate và lưu run `d8230d1d-badd-4c0c-b044-dcc4434215a6` trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`: `COMPLETED`, engine `p17-dvh-1.1.0`, ROI `#1 · P17_TARGET`, `D95=5.200 Gy`, limit `MIN 5 Gy`, margin `+0.200 Gy`, `explicit_selection=true`, `auto_applied=false`.
- Vì source còn `UNVERIFIED` và không chọn CT, trạng thái đúng là `REVIEW_REQUIRED` cùng hai warning tương ứng; không nâng thành PASS và không coi đây là prescription/clinical approval. History tăng từ 1 lên 2, run có input fingerprint `8f525a5e…` và result SHA `cf2799b8…`.
- P9 Report Builder đã lưu report revision 1 `P17 staging bound DVH report` từ đúng run mới, source type `DVH`, snapshot SHA `2599b891…`, 5 block tùy chỉnh (`TEXT`, `METRICS`, `PROVENANCE`, `DVH`, `WARNING`) và không rerun/mutate DVH. Evidence đầy đủ: `docs/evidence/p16-p17-staging-binding-report-20260910-a55f.json`.
- Trên cùng report revision, staging Report Builder đã tạo đủ bốn loại export: JSON `15.582` bytes, CSV `1.190` bytes, PDF `1.046` bytes và PNG `2.243` bytes. CSV payload đã đọc lại và khớp report key, revision, source run và content SHA; không tạo revision hoặc rerun DVH. Evidence: `docs/evidence/p9-staging-export-format-20260910-54516.json`.
- Đây là staging authenticated mutation/readback slice PASS. Direct PostgreSQL probe cho entry/run mới, export byte/final filename, full negative/fault/resource matrix, independent oracle promotion, release manifest và production promotion vẫn mở.

## P11 consumer snapshot — local verified, staging open — 2026-09-10

- Machine QA run mới pin `p11.protocol-snapshot.v1` ngay khi tạo hoặc rerun. Snapshot giữ protocol identity/family/version, `status_at_use`, revision, source type/reference/lineage, applicability, engine capability và toàn bộ rule/limit/action/reference snapshot.
- Evaluation sau khi protocol chuyển `ARCHIVED` vẫn dùng snapshot ACTIVE đã chấp nhận; thay đổi định nghĩa ngoài lifecycle archive bị chặn fail-closed bằng `MACHINE_QA_PROTOCOL_SNAPSHOT_MISMATCH`, không tạo metric/trend/result mới. Legacy run chưa có snapshot chỉ được nâng cấp ở lần evaluate đầu theo compatibility policy.
- Trend source context giữ `protocol_version_id`; Machine QA report giữ source snapshot; UI source panel đọc revision/source/applicability/rule count từ snapshot của run và workflow thường không còn seed synthetic protocol.
- Local focused regression `apps/api/tests/test_protocol_library.py`: **4/4 PASS** cho protocol snapshot, archive behavior, Trend lineage và report source. API changed files đã qua Ruff/mypy; web lint/typecheck/build sẽ được kiểm lại trên candidate tài liệu này.
- Local implementation evidence đã được đối chiếu với public staging candidate `907b9d256d221e628a7d5e0b2b578c52b7dd6c14`: Railway API, web và worker đều `SUCCESS` cùng source SHA; API `/apps/api`, web `/apps/web`, worker `/apps/api` với start `python -m rt_connect_api.worker` và không HTTP healthcheck. API `/health`, `/ready`, `/version`, OpenAPI và web bundle exact-SHA đạt **15/15 PASS**, schema `20260909_0019`; evidence `docs/evidence/p11-public-probe-907b9d2.json` và `docs/evidence/p11-railway-parity-20260910-907b9d2.json`. Đây chỉ là source/runtime/public-contract evidence; chưa chạy authenticated browser create/use/archive/old-history E2E, complete S/E/C, visual/accessibility hoặc release-manifest gate. Không upload fixture RTDOSE trùng và không tạo QA run mới trong case staging đã có fixture hợp lệ.
- Fresh authenticated browser trên đúng candidate `0e30ff1ba768494649d9ce6105dacac9c703a4d4` đã mở route Machine QA của case staging và đọc được protocol ACTIVE `MACHINE_QA_BASELINE` v1, source/revision/rule count/applicability, nhãn run đã pin snapshot, existing PASS run và history count 2. Workflow thường không còn hiển thị hành động seed synthetic; không tạo run hoặc thay đổi protocol trong lần kiểm tra này. Evidence read-only: `docs/evidence/p11-staging-consumer-browser-20260910.json`.
- Sau khi buộc API rebuild bằng watched-file marker, đúng candidate `4486eb49c9838c8d9fb68be5627e58312626e79b` đã có API/web/worker `SUCCESS` cùng SHA; public verifier đạt **15/15 PASS**, schema `20260909_0019`, và browser recheck lại Machine QA trên cùng build vẫn đọc được protocol ACTIVE, source/revision/rule count, consumer snapshot marker, existing PASS run/history 2 mà không tạo mutation. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-4486eb4.json`, `docs/evidence/p11-staging-consumer-browser-20260910-4486eb4.json`.
- Fresh authenticated staging lifecycle trên candidate `b7c3c4a2dfd85d86c1097448ca0deddf6d41147f` đã chạy bằng dữ liệu tổng hợp: tạo case `ed7ddbe5-811a-4463-a270-b0386f64644d`, validate-only protocol `STAGING_P11_E2E_B7C3` không side effect, lưu DRAFT revision 2, activate revision 3, clone version 2 DRAFT và compare (metadata diff 4, rule diff 1, child rule deep-copy/lineage), rồi tạo Machine QA run `bc652ee9-0d25-474e-a414-13d23c04a231` với `output_factor=100%`, đạt `COMPLETED/PASS`. Sau khi archive version 1, active list không còn version này nhưng reload run cũ vẫn giữ snapshot revision 3, 1 rule, source/applicability và PASS; không seed action hoặc fixture upload được dùng trong workflow này. Evidence: `docs/evidence/p11-staging-lifecycle-20260910-b7c3c4a.json`. Đây là happy-path S01-S10 slice; P11 vẫn mở cho E01-E17, concurrent/uncertain/scope-negative, các consumer recheck còn thiếu và release manifest.

## P10 Trend query budget — candidate staging parity/public smoke verified — 2026-09-10 / `f4197d8`

- P10 API có `TREND_MAX_RAW_POINTS` mặc định `10.000` và `TREND_MAX_AGGREGATE_SOURCE_POINTS` mặc định `100.000`; count-preflight chạy theo organization/filter trước khi materialize source rows và có kiểm tra lần hai sau context matching.
- Raw vượt budget trả HTTP 413 `TREND_QUERY_TOO_LARGE` với aggregate/matched_points/max_points; day/week trong aggregate budget được phép chạy nhưng thêm `TREND_AGGREGATED_LARGE_QUERY`; aggregate vượt budget cũng trả 413.
- CSV export aggregate không còn rỗng: mỗi bucket là `record_type=BUCKET`, giữ count/statistics/statuses và JSON-encoded source point/run IDs. Đây là local implementation slice; large-series workload 100.000 điểm/máy, staging p95, visual/accessibility và complete S/E/C vẫn mở.
- Regression local đã đạt `test_trend.py` **8/8 PASS**, full backend **185/185 PASS**, Ruff, strict mypy, web lint/typecheck, Vitest **14/14 PASS** và production build (chỉ còn cảnh báo bundle >500 kB).
- Candidate backend `a089d2adb103b106bce7d6c96112e3c426d7e8bb` đã deploy thành công với source parity; public verifier đạt **15/15 PASS**, schema `20260909_0019`. Evidence: `docs/evidence/p10-trend-query-budget-20260910-a089d2a.json`. Follow-up web bounded-error UX candidate `a7c1ad4622bbb57599127b96d9ef27451a715ca0` cũng đã rebuild API/web/worker cùng SHA và đạt **15/15 PASS**; evidence: `docs/evidence/p10-bounded-error-ux-20260910-a7c1ad4.json`.
- Candidate `f4197d82bd287112d1aafae44088678cd967cecf` tiếp tục rebuild API/web/worker cùng SHA sau khi sửa SQL context filtering để không materialize rộng trước khi lọc; public verifier đạt **15/15 PASS** và backend full suite **185/185 PASS**. Evidence: `docs/evidence/p10-sql-filtered-preflight-20260910-f4197d8.json`.
- Đây mới là source/runtime/public-contract evidence. Chưa có authenticated large-series benchmark, complete P10 S/E/C current-candidate, export/source revalidation sau refresh hoặc visual/accessibility evidence; P10 chưa đóng.
- Quyền upload RTDOSE đã được xác nhận, nhưng fixture tổng hợp đã tồn tại và `VALID` trong case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`; không tạo artifact trùng và không tạo QA run mới.

## P07 explicit N/A contract — local + staging candidate — 2026-09-10 / `902b757`

- Đã triển khai P07 explicit N/A end-to-end ở local: measurement có `is_not_applicable` và `na_reason`; N/A bắt buộc có lý do sau trim, không nhận giá trị số, metric có reason nhưng không bật N/A bị từ chối; quality status là `NA`, overall aggregation dùng `FAIL > REVIEW > WARNING > NA > PASS`, và metric N/A không tạo `TrendPoint`.
- Backend regression `apps/api/tests/test_machine_qa.py`: **6/6 PASS**; frontend lint, typecheck, Vitest và production build: **PASS**. Đây mới là `LOCAL_VERIFIED`; chưa dùng để khẳng định candidate staging mới đã phục vụ contract này.
- Tài liệu tại checkpoint đó đã đồng bộ: `business-analysis.md` v0.23, `specification.md` v1.22, `technical-specification.md` v1.21 và `plan.md` v4.13. Đây là evidence lịch sử của P07; revision hiện hành nằm ở phần P10 phía trên và sẽ được kiểm lại sau candidate mới.
- Case staging đã có fixture RTDOSE tổng hợp đúng từ trước và đã ở trạng thái `VALID`; theo xác nhận upload của người dùng, không tạo artifact RTDOSE trùng.
- Railway read-only deployment metadata xác nhận API `1e9e8ab9-ad4b-438a-b5be-bd068700a1c6`, web `2e49f01d-023c-47ac-bd58-b7866baa2e14` và worker `0c0d1c47-2c86-4924-9396-a53f2729aed5` đều `SUCCESS`, cùng source SHA đầy đủ `902b75729c97b6927465d70b93225d5702bdc83f` trên branch `codex/p4-org-site-machine`. API giữ `/apps/api`, pre-deploy `alembic upgrade head`, healthcheck `/api/v1/health`; worker giữ `/apps/api` và `python -m rt_connect_api.worker`, không dùng HTTP healthcheck; web giữ `/apps/web`.
- Public exact-SHA verifier đạt **15/15 checks PASS** với schema `20260909_0019`; evidence: `docs/evidence/p19-staging-public-smoke-20260910-902b757.json`. Đây là source/runtime/public-contract evidence; authenticated Machine QA N/A browser mutation, fault injection và production promotion chưa được ghi nhận.

## Documentation and implementation rebaseline — 2026-09-09

Revision hiện hành của bộ tài liệu là `business-analysis.md` v0.23, `specification.md` v1.22,
`technical-specification.md` v1.21 và `plan.md` v4.13. Dòng rebaseline lịch sử ngay dưới đây
giữ nguyên để truy vết; không dùng các phiên bản cũ đó làm authority.

`business-analysis.md` v0.21, `specification.md` v1.15, `technical-specification.md` v1.13 và `plan.md` v4.0 bổ sung feature-card/handoff, operation/error/evidence record, dependency graph, change-impact gate, state contract, testcase, workflow, error/recovery contract và gap từ source. Bản plan trước ở `docs/history/plan-v1.5.md`. Slice P6/P8/P9/P10/P11/P12/P13/P14/P15/P16/P17 đã được sửa và kiểm thử local; staging E2E chỉ được ghi cho những workflow đã kiểm trực tiếp đúng candidate.

Các trạng thái/evidence bên dưới giữ nguyên phạm vi lịch sử trừ những dòng được ghi rõ là checkpoint mới. Không tự kế thừa DONE sang gate v2: invitation/restore/concurrent edits, P8 crash/ack/bounded retry/resource-large-input, schema-readiness, staging Trend và staging Protocol consumer vẫn phải được đối soát theo plan §1.2–§1.6. Câu “only remaining gates” trong checkpoint cũ không còn là danh sách đầy đủ. Checkpoint trước đã xác minh browser staging P13/P14 trên candidate `31a5900`; PostgreSQL row query trực tiếp, organization-scope negative probe và release-manifest closure vẫn là gate riêng của các phase đó. P8 hiện đã có staging RTDOSE + measurement 3D browser smoke và local independent oracle 6/6; crash/ack/resource/release gates còn mở. P17 hiện đã có targeted PostgreSQL row/checksum/scope probe và object-storage byte re-hash cho case staging; immutable snapshot/fault/resource/release gates còn mở.

## Current staging candidate and RTDOSE permission recheck — 2026-09-10 / `4c9bc1b`

- Railway read-only deployment metadata xác nhận API `753fc39b-244b-4022-aafe-40e634becd49`, web `de98215c-fada-4c29-9867-f757ca37348c` và worker `25c26ce3-6a8c-450d-a641-22a90654d601` đều `SUCCESS`, cùng source SHA đầy đủ `4c9bc1bb4838e2864e605ab4fa69c698ecd0759e`; API/web/worker vẫn giữ đúng root và start contract trong runbook.
- Public verifier chạy lại với exact SHA `4c9bc1bb4838e2864e605ab4fa69c698ecd0759e` và schema `20260909_0019` đạt **15/15 checks PASS**. Kết quả gồm health/readiness/version, OpenAPI, organization boundary unauthenticated `401`, web bundle, CT/membership marker và source marker.
- Fresh authenticated browser trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` hiển thị build hiện hành, `2 dose · 1 structure`, RTDOSE `gamma-rtdose-v1-smoke.dcm` fingerprint `ca5c9168…` ở trạng thái `VALID`, RTSTRUCT `p17-rtstruct-v1-smoke.dcm` fingerprint `16a79df3…`, CT tùy chọn `0b1d3bfd…` và saved DVH run `8000ff9b…`. Người dùng đã cho phép upload fixture RTDOSE; vì fixture đúng đã tồn tại và đang được chọn nên **không upload bản trùng**.
- Full backend regression trên candidate local đạt **100% pass**; planning contract ghi nhận 21 phase và `failed_check_count=0`; worktree sạch trước khi tạo evidence packet.
- Manifest redacted của candidate này ở `docs/evidence/release-manifest-staging-4c9bc1b.json`; `--verify-manifest` trả `valid=true`, service SHA parity `true`, release gate `ELIGIBLE`. Manifest chỉ mô tả consistency của candidate staging đã kiểm; không biến public smoke hoặc fixture hiện hữu thành bằng chứng production promotion, backup/restore provider, fault injection hay clinical readiness.

## Latest staging parity before P09 export change — 2026-09-10 / `b4e2446`

- Sau khi ghi nhận public smoke của `ebf1e66`, commit tài liệu/parity `b4e24468149f070dd77b80e0d2ada3fa20445ce4` đã được Railway rebuild đồng bộ. API `d922b60f-a538-4853-b558-60657a1fefef`, web `e7802242-47bb-4f98-8053-e8b3a3e384b6` và worker `5e0a7920-96af-4dca-b936-af633a3293a1` đều `SUCCESS`, cùng branch `codex/p4-org-site-machine`, root tương ứng `/apps/api`, `/apps/web`, `/apps/api`.
- Public verifier với expected source SHA `b4e24468149f070dd77b80e0d2ada3fa20445ce4` và schema `20260909_0019` đạt **15/15 checks PASS**. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-b4e2446.json`.
- Fresh browser sau cache-bust xác nhận build `b4e24468149f070dd77b80e0d2ada3fa20445ce4`, API `OK`, schema `READY/MATCH`; case staging vẫn có fixture RTDOSE tổng hợp đã cho phép sử dụng, không tạo bản trùng. Đây là mốc runtime trước khi P09 export-compensation code được đưa vào candidate kế tiếp.

## Staging parity and public recheck — 2026-09-10 / `ebf1e66`

- Commit `ebf1e664c55974b6bc418ff05791edfa5ace93f7` đã được push lên branch `codex/p4-org-site-machine`. Railway read-only metadata xác nhận API, web và worker staging đều chạy đúng commit này và đều `SUCCESS`: API `44fba031-2fa2-4d3b-9d42-9b1055a7bafd`, web `d744b68c-7b1b-4b35-aa0e-02eaa89e8b71`, worker `5aab77bc-f1fd-4db2-90bc-8b6b6a9913bf`. API giữ `/apps/api`, healthcheck `/api/v1/health`, pre-deploy `alembic upgrade head`; worker giữ `/apps/api` và `python -m rt_connect_api.worker`, không dùng HTTP healthcheck.
- Ba image digest khác nhau theo vai trò nhưng source commit, branch và runtime `V2` khớp. API image là `sha256:ec5d709b41bc06091594ef349b4eba2598ee8be300a337a481b1a14f8f24cf7d`, web `sha256:edb959b6a7bc9d7ee4584bfe96fbe30d762524d2727ace5cea73c4f3f6415c44`, worker `sha256:8e4801d12ea48b98ed9b9507ff40b85fbf50b1c9316d300f08b97021e41732ad`.
- Public verifier với expected full source SHA `ebf1e664c55974b6bc418ff05791edfa5ace93f7` và schema `20260909_0019` đạt **15/15 checks PASS**: health/readiness, schema, `/version`, OpenAPI CT-preview và organization routes, unauthenticated membership/invitation `401`, web index/bundle, CT/membership markers và source marker. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-ebf1e66.json`.
- Fresh navigation có query bust cache tới `/app/system/status` hiển thị `Build ebf1e664c55974b6bc418ff05791edfa5ace93f7`, API `OK`, schema `READY/MATCH`, queue Redis available và environment `staging`. Fresh navigation tới case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` vẫn đọc được **2 RTDOSE**, **1 RTSTRUCT**, CT tổng hợp và saved DVH history; RTDOSE `gamma-rtdose-v1-smoke.dcm` với fingerprint `ca5c9168…` đã tồn tại nên theo xác nhận upload của người dùng không tạo artifact trùng.
- Lần kiểm tra đầu tiên truyền nhầm `ExpectedVersion=0.1.0-dev` nên verifier báo 1 mismatch có chủ ý; chạy lại với full commit SHA là kết quả PASS. Đây là lỗi tham số kiểm tra, không phải lỗi Railway deployment.
- **Evidence level:** `STAGING_SOURCE_PARITY_AND_PUBLIC_SMOKE`. P19 mới đóng thêm source/runtime/public-contract slice cho candidate này; release manifest mới, authenticated E2E trên candidate mới, production promotion, remote fault/restore, rollback rehearsal và clinical readiness vẫn mở.

## Current staging parity and P14 recheck — 2026-09-10 / `0c0b5ff`

- Railway read-only metadata xác nhận ba service staging đang chạy cùng source commit `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b`, branch `codex/p4-org-site-machine`, và đều `SUCCESS`: API deployment `3766889f-6ff6-4aa9-bee1-2df1ca865af0`, web deployment `0cdaeee3-75ca-4115-a1f3-b23b99d26c9f`, worker deployment `f4db4c55-8afe-44c3-9393-7bc1ad50e9e6`. Worker start command là `python -m rt_connect_api.worker`; deploy log xác nhận `queue_backend=redis_stream`, stream `rt-connect:gamma`, group `rt-connect-gamma`.
- Public exact-SHA verifier sau parity rebuild đạt **15/15 checks PASS** tại `docs/evidence/p19-staging-public-smoke-20260910-0c0b5ff.json`: health/readiness, schema `20260909_0019`, `/version`, OpenAPI, unauthenticated organization boundary `401`, web index/bundle, CT/membership markers và full source marker.
- Release manifest `docs/evidence/release-manifest-staging-0c0b5ff.json` đã được tạo từ working tree sạch của source snapshot `0c0b5ff`, `--verify-manifest` trả `valid=true`, `service_sha_parity=true`, `release_gate=ELIGIBLE`, manifest hash `c071601aae12a28bd99adc5324f8857a8fce4fc5c718c3dee3743125ec5b06ab`. Manifest hiện đã ghi thêm các staging test ID của P14/P15. Manifest chỉ chứng minh consistency của staging snapshot; production promotion, remote fault/restore, full E2E và clinical readiness vẫn mở.
- Trên đúng build `0c0b5ff`, P14 route `/app/biological/compare` đã chạy `Validate only` thành công với hai P13 snapshot cùng scenario revision `f9fafce0-e224-40b6-8b2a-a9952093f8dc`, sau đó lưu comparison `77045b33-117b-4f21-90ec-352cba2f4bf4`. Baseline `option-a` cho `D=60 Gy, n=30, d=2 Gy/fx, α/β=10 Gy` có `BED=72 Gy`, `EQD2=60 Gy`; `option-b` cho `D=70 Gy, n=35, d=2 Gy/fx` có `BED=84 Gy`, `EQD2=70 Gy`, chênh lệch `+12 Gy BED`, `+10 Gy EQD2`, `+16.667%`.
- Reload browser giữ `COMPLETED`, comparison ID, option order, baseline option ID, checksum và history count `3`; history được hiển thị là immutable. JSON/CSV export đã tạo payload parse được, lần lượt `6852` và `673` bytes với SHA-256 được ghi trong evidence, nhưng Edge giữ hậu tố `.crdownload`, nên final filename vẫn `UNVERIFIED`. Evidence đầy đủ: `docs/evidence/p14-staging-browser-20260910-0c0b5ff.json`.
- P15 Re-irradiation trên cùng build đã chạy no-recovery và recovery explicit. Với hai course `60 Gy/30 × 2 Gy`, recovery `r=0.5` cho prior course, snapshot `2f66676e-b5b2-4b76-aa9f-e226e9984bae` đạt `COMPLETED`, BED no-recovery `144`, BED with recovery `108`, EQD2 with recovery `90`; sensitivity `r=0/0.25/0.5/0.75/1` cho BED `144/126/108/90/72`. Spatial request chỉ trả warning/capability `SPATIAL_ACCUMULATION_UNAVAILABLE`, không tạo voxel result. Reload giữ history count `3`, checksum và recovery assumptions. Evidence: `docs/evidence/p15-staging-reirradiation-browser-20260910-0c0b5ff.json`.
- P15 Fraction Compensation cũng đã chạy: planned `[2,2,2,2,2] Gy`, delivered prefix `[2,2] Gy`, original remaining và alternative `[2.5,2.5,1] Gy` đều giữ prefix `UNCHANGED`; snapshot `7d805462-9b3f-497e-90e9-640b11b7c377` đạt `COMPLETED`, BED LQ `12` và `12.15`, ΔBED `0` và `+0.15`. Prefix sai `[2,3]` bị từ chối bằng `FRACTION_SCHEDULE_INVALID`, không tạo snapshot; khôi phục lại thì `VALIDATION_OK`. Reload giữ history count `2`; export payload parse được nhưng final filename vẫn `UNVERIFIED` do `.crdownload`. Evidence: `docs/evidence/p15-staging-fraction-compensation-browser-20260910-0c0b5ff.json`.
- Fixture RTDOSE tổng hợp trong case staging `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` đã được xác nhận tồn tại từ trước với SHA-256 `ca5c9168…`; không upload trùng, không tạo patient/PACS/treatment linkage. P8/P13 evidence mang source `d2a5a6b` vẫn là snapshot lịch sử; không dùng chúng để mô tả candidate `0c0b5ff` nếu chưa rerun workflow tương ứng.
- Một tab browser cũ từng hiển thị bundle `e1336b7…` do giữ nội dung/cache của deployment trước. Sau fresh navigation tới `/app/system/status` và P17 DVH, web hiện hành hiển thị build `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b`; chỉ quan sát sau fresh navigation mới được dùng làm evidence parity.
- Ghi chú parity: commit evidence ở root có thể làm web tự rebuild trong khi API bị watch-path bỏ qua. Vì vậy mọi release evidence tiếp theo phải đi kèm parity marker dưới `/apps/api` hoặc được chốt như artifact của candidate đã kiểm, sau đó chạy lại exact-SHA verifier; không push manifest-only rồi kết luận parity còn đúng.

## P20 local backup/restore recheck — 2026-09-10

- Chạy `scripts/verify-local-backup-restore.py` trên Docker Compose đang hoạt động với phạm vi `local-compose-only`; verifier không nhận endpoint Railway/S3 từ xa và không ghi lại dump hay object tạm sau khi kết thúc.
- PostgreSQL custom dump có `169,924` bytes, SHA-256 `53a4ae120f8d596ffcab26d7eb3df87e4e014340ee0576b9a3f871d302adbca1`; restore vào database disposable `rt_connect_restore_39c1fea08247` giữ nguyên row count và row fingerprint của 21 bảng được kiểm.
- Object inventory local có `0` object ở bucket nguồn và bucket restore; inventory hash hai phía cùng là `44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a`.
- Database restore và bucket restore đã được cleanup thành công (`database_dropped=true`, `bucket_removed=true`); toàn bộ report đạt `passed=true`. Evidence: `docs/evidence/p20-local-backup-restore-20260910.json`.
- **Evidence level:** `LOCAL_SUPPORT_ONLY`. Đây là bằng chứng kiểm tra tính đúng của script/restore path với database local hiện tại; chưa chứng minh backup provider Railway, RPO/RTO, restore staging/production, alerting hoặc owner handoff. P18/P20 vẫn chưa đóng.

## P06 local upload compensation recheck — 2026-09-10

- Bổ sung `delete_object` vào object-storage adapter. Sau khi object đã được ghi, nếu transaction `Artifact` + `InputManifest` + audit không commit thì API rollback database và xóa đúng object key vừa tạo; không xóa theo filename hoặc prefix.
- Nhánh metadata conflict tổng hợp trả lại lỗi gốc `ARTIFACT_CONFLICT`, object storage không còn object và danh sách case không có artifact mồ côi. Nhánh cleanup storage lỗi trả `ARTIFACT_PERSISTENCE_FAILED` HTTP 503, giữ signal để reconciliation; không trả success khi chưa có metadata durable.
- Regression `tests/test_artifacts.py` và `tests/test_error_contract.py`: **8 passed**; `Ruff` sau sửa line length và `mypy src`: **PASS**. Evidence chi tiết: `docs/evidence/p6-local-upload-compensation-20260910.json`.
- **Evidence level:** `LOCAL_VERIFIED` cho compensation path và memory storage double. Provider retention/inventory reconciliation, interrupted multipart trên network thật và staging failure injection vẫn mở; không dùng checkpoint này để kết luận P06 hoặc P18/P20 đã đóng.

## P09 local export compensation recheck — 2026-09-10

- Export report hiện commit claim `QUEUED` trước, render từ revision snapshot, ghi object, sau đó mới commit metadata `COMPLETED` cùng hash/size/media/warnings. Nếu commit metadata cuối thất bại, API rollback session và xóa đúng object key; nếu cleanup thất bại, API trả HTTP 503 `REPORT_EXPORT_PERSISTENCE_FAILED` với signal reconciliation và không phát signed URL.
- `tests/test_reports.py`, `tests/test_artifacts.py` và `tests/test_error_contract.py` đạt **14 passed**; nhánh retry cùng idempotency key sau compensation tạo đúng một export, còn nhánh cleanup failure giữ object để reconciliation nhưng không trả success. Ruff và mypy đều PASS.
- Evidence: `docs/evidence/p9-local-export-compensation-20260910.json`. **Evidence level:** `LOCAL_VERIFIED` cho transaction/compensation path với in-memory storage; provider/network fault injection, orphan inventory, retention, restore và visual export vẫn mở.

## P10 staging Trend read-only recheck — 2026-09-10 / `0c0b5ff`

- Fresh authenticated browser navigation tới `/app/trend` trên web build `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b` hiển thị `API THẬT`, organization context `Hong ngoc general hospital`, machine `STAGING-LINAC-01 · Synthetic QA Linac`, metric `output_factor`, aggregate `raw` và timezone `Asia/Ho_Chi_Minh`.
- Current projection readback hiển thị `6` compatible points thuộc `3` series (`flatness`, `output_factor`, `symmetry`), `3` baseline và `1` maintenance marker. Các series giữ riêng protocol/unit/context; source case links và raw values vẫn được hiển thị.
- Hai series `flatness` và `output_factor` có điểm `100 %`, `PASS`, baseline delta `0`; series `symmetry` hiển thị điểm `1 %`, `PASS · OUTLIER`, baseline delta `-99`, chứng minh UI không nuốt trạng thái outlier vào một PASS không có dấu hiệu.
- Lần kiểm tra chỉ đọc; không bấm `Rebuild projection`, không export và không tạo mutation. Evidence: `docs/evidence/p10-staging-trend-browser-20260910-0c0b5ff.json`.
- **Evidence level:** `STAGING_SMOKE_READ_ONLY`. P10 chưa đóng: projection rebuild, update/archive baseline UI, complete negative matrix, large-series budget, export-content/hash và visual/accessibility evidence vẫn mở.

## Staging parity rebuild and release manifest — 2026-09-10 / `d2a5a6b`

- Read-only Railway deployment metadata first exposed source drift: API remained on the `c6252f7` successful deployment while web/worker had accepted the later documentation commit. A harmless parity marker was therefore added below `/apps/api`; it does not change application behavior, but makes API and worker participate in the same Git-triggered candidate rebuild.
- Candidate `d2a5a6b22267d153f26764596b36c78118f67ffa` is now served by all three staging services. Deployment IDs are API `c53678dc-c2c4-4c7a-9e24-137b949a5ff7`, web `2a78dd8a-414f-4e75-ab2e-c9c0631579fc` and worker `4dc90da0-2745-4f95-9575-18ab1264b8c2`; each Railway deployment is `SUCCESS` and the worker remains configured with `python -m rt_connect_api.worker`.
- The public exact-SHA verifier reached **15/15 checks PASS**: health/readiness/version, schema `20260909_0019`, OpenAPI CT-preview and organization routes, unauthenticated membership/invitation boundary `401`, web index/bundle, CT/membership UI markers and bundle source marker. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-d2a5a6b.json`.
- Release manifest `docs/evidence/release-manifest-staging-d2a5a6b.json` records all three deployment IDs, the four synthetic DICOM/measurement fixture hashes, engine/renderer versions, local/staging test IDs and rollback reference. `--verify-manifest` returned `valid=true`; `service_sha_parity=true` and `release_gate=ELIGIBLE` apply only to this staging candidate's manifest consistency, not to production promotion or clinical readiness.
- P8 2D negative/recovery evidence on the same candidate is recorded in `docs/evidence/p8-staging-gamma-2d-20260910-d2a5a6b.json`: intentional PSQA 3D RTDOSE plus 2D measurement mismatch failed explicitly as `GAMMA_DIMENSIONALITY_MISMATCH` (`e33968e2…`), then compatible `ENGINE_TEST` 2D JSON fixtures completed `PASS` (`5b5711c6…`, `4/4`, coverage `1`, attempt `1`, engine `gamma-nd-p8.2`). No failed job was counted as a passing result.
- P13 authenticated browser evidence on the same candidate is recorded in `docs/evidence/p13-staging-bed-eqd2-browser-20260910-d2a5a6b.json`: the saved synthetic scenario used `D=60 Gy, n=30, d=2 Gy/fx, α/β=10 Gy`; validate-only returned `VALIDATION OK` without a database side effect, save returned `COMPLETED` with `BED=72 Gy` and `EQD2=60 Gy` (`8fda6eb8…`), and a reload preserved the newest snapshot with history count `3`. An intentional `D=61 Gy` mismatch returned `FRACTIONATION_INCONSISTENT` on the two dependent fields and did not create a snapshot; restoring `D=60 Gy` returned `VALIDATION OK`. This is independent biological-tool evidence, not a QA/patient linkage or clinical-readiness claim.
- This checkpoint closes the P19 source-parity/manifest sub-slice for staging. It does not close P4 two-identity Auth/PostgreSQL lifecycle, P8 staging crash/ACK/failure/resource/oracle promotion, P9–P18 remaining gates, P19 production remote E2E/rollback, or P20 real alert/backup/restore evidence.

## Latest staging candidate checkpoint — 2026-09-10 / `c6252f7`

- Candidate `c6252f7557a5c2c893c5e3082035884e9f26c882` đã được push lên branch `codex/p4-org-site-machine` và Railway tự triển khai cho API, web và worker staging. API `/api/v1/version` và `/api/v1/ready` trả đúng full SHA/schema `20260909_0019`; web bundle cũng chứa đúng source marker.
- Public verifier exact-SHA đạt **15/15 checks PASS** tại `docs/evidence/p19-staging-public-smoke-20260910-c6252f7.json`: health/readiness/version, OpenAPI CT preview và organization membership, unauthenticated boundary 401, web index/bundle, UI markers và source parity đều đạt.
- Worker deployment `031ceef2-1260-4b0a-8353-4c80d6ae31ee` hiển thị `Deployment successful`, commit `c6252f7557a5c2c893c5e3082035884e9f26c882`, branch `codex/p4-org-site-machine`, root `/apps/api`, start command `python -m rt_connect_api.worker`, trạng thái `Online`.
- Local peer-membership regression đạt **12/12** sau khi bổ sung identity thứ hai tổng hợp: peer nhận invitation, đọc cùng organization context và thực hiện cùng thao tác site/machine/member; không có nhánh action-role theo chức danh. Evidence: `docs/evidence/p4-local-peer-membership-20260910.json`.
- Fixture RTDOSE tổng hợp đã được người dùng xác nhận cho phép sử dụng trên case staging; fixture hợp lệ đã tồn tại nên không upload trùng. Gamma 3D run mới `1d5ee035-28e0-461a-8a3d-15fef6b883bd` đạt `COMPLETED/PASS`, `8/8`, trên worker Redis staging. Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-2b1846a.json`.
- Local Compose queue verifier v2 bổ sung ACK transport-failure injection: message sau durable `COMPLETED` vẫn pending, eventual ACK dọn pending, result/attempt không đổi. Evidence: `docs/evidence/p8-local-redis-worker-smoke-20260910-v2.json`; toàn bộ happy path, bounded retry/dead-letter, malformed quarantine và ACK recovery đều PASS.
- Checkpoint này chỉ nâng source/runtime confidence và ghi nhận evidence có thể truy vết. Nó **không** đóng P4 two-identity Supabase/PostgreSQL lifecycle, P8 crash sau durable commit trước ACK/failure injection/resource-large-input/oracle promotion, các gate P9–P18 còn mở, hoặc P19 production promotion.

## Current continuation checkpoint — 2026-09-10

- Fresh authenticated browser recheck trên candidate `ec50990395e9bb4b7182ff48c3b2a8e4b2eeb1ca` xác nhận route `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh` đang phục vụ đúng build; case vẫn giữ RTDOSE tổng hợp `ca5c9168…`, RTSTRUCT `16a79df3…`, CT `0b1d3bfd…`, ROI `#1 · P17_TARGET` và saved run `8000ff9b…`.
- CT frame `#1` tiếp tục trả `LPS LINKED` với overlay `NEAREST_NEIGHBOR_IN_PATIENT_LPS`; frame `#3` trả `NO DOSE OVERLAP` đúng warning contract. Không tạo upload, DVH run hoặc mutation mới trong lần recheck này. Evidence: `docs/evidence/p17-staging-browser-recheck-20260910-ec50990.json`.
- P16/P11 binding được kiểm tra read-only: staging hiện có **0** P16 `DOSE_LIMIT` entry; các protocol ACTIVE chỉ cung cấp metric `output_factor`, `flatness` và `staging_output`, chưa có metric DVH tương thích. Vì vậy binding gate vẫn mở và hệ thống vẫn giữ `NO AUTO-APPLY`.
- JSON export có payload hoàn chỉnh, parse/hash khớp run (`17,738` bytes); Edge/CUA giữ hậu tố `.crdownload`, nên browser final filename vẫn `UNVERIFIED` và không được diễn giải thành lỗi byte payload.
- Validate-only sau khi chọn CT tổng hợp trả `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ`, CT frame `#1` hiển thị `LPS LINKED` và overlay `NEAREST_NEIGHBOR_IN_PATIENT_LPS`; không tạo upload/run/mutation mới.
- P17-W06 local resource evidence mới `docs/evidence/p17-local-docker-workload-20260910.json` đạt `LOCAL_RESOURCE_GATE_PASS`: API container `1 CPU/768 MiB`, 2 job × 3 lần, 6/6 process peak RSS, max `127,086,592 bytes`, max elapsed `2.0811 s`, p95 `/health` `166.016 ms`, 0 probe error, engine/oracle nhất quán; cgroup v1 peak `385,990,656 bytes` là quan sát tích lũy từ lúc container start và vẫn được gắn `is_peak_rss=false`.
- Public verifier exact-SHA trên candidate `ec50990395e9bb4b7182ff48c3b2a8e4b2eeb1ca` pass **15/15**; API, worker và web staging cùng source/schema. Evidence: `docs/evidence/p19-staging-public-smoke-20260910-ec50990.json`. Probe accept invitation dùng POST không body để xác nhận auth boundary 401 trước validation; payload contract vẫn được test API kiểm. Đây là source-parity/public-boundary evidence, không phải production promotion hoặc clinical readiness.

## P4/P8 current staging candidate — 2026-09-10 / `2b1846a`

- Sau khi push các commit queue hardening và evidence lên `codex/p4-org-site-machine`, API, web và worker staging đều đã có deployment thành công từ full SHA `2b1846a44ca10091df3e043eb478f9ffb6b7bc3e`; API `/api/v1/version` và `/api/v1/ready` trả đúng SHA/schema `20260909_0019`, public smoke đạt **15/15** trong `docs/evidence/p19-staging-public-smoke-20260910-2b1846a.json`.
- Worker staging deployment `7fa7a9ba-c29d-4979-af97-e42f00dbb3f3` hiển thị commit `2b1846a44ca10091df3e043eb478f9ffb6b7bc3e`, start command `python -m rt_connect_api.worker`, trạng thái `Deployment successful`; logs xác nhận `queue_backend=redis_stream`, stream `rt-connect:gamma`, group `rt-connect-gamma`. API deployment là `d8a8dfc0-8562-4893-9fcd-4a6ba1137155`; web deployment là `eb08fb76-4ae3-4c3d-9193-56f111a9a6b7`.
- Authenticated browser `/app/organization` đã đọc được organization `Hong ngoc general hospital` `ACTIVE`, 1 site `Staging Synthetic Site`, 1 machine `STAGING-LINAC-01` và 1 active member ngang quyền; không tạo mutation trong lần kiểm tra. Evidence: `docs/evidence/p4-staging-auth-organization-browser-20260910-2b1846a.json`. Đây mới là read evidence của một identity, chưa đóng two-identity invitation lifecycle.
- Trên đúng candidate mới, RTDOSE `gamma-rtdose-v1-smoke.dcm` đã có sẵn nên không upload trùng; Gamma 3D synthetic run mới `1d5ee035-28e0-461a-8a3d-15fef6b883bd` đã đi qua enqueue → worker → persist và hiển thị `COMPLETED/PASS`, `8/8`, engine `gamma-nd-p8.2`, coverage `1`, P95 `0`. Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-2b1846a.json`.
- Local P4 peer-membership regression mới đạt `12/12`: identity nhận invitation có verified email, đọc cùng organization context và thực hiện cùng các thao tác site/machine/member; không có action-role branch. Evidence: `docs/evidence/p4-local-peer-membership-20260910.json`. Đây là local contract evidence, chưa thay cho hai tài khoản Supabase trên browser hoặc query PostgreSQL staging.
- Các evidence trên nâng source/runtime confidence của P4/P8 trên candidate hiện tại nhưng không đóng P4 two-identity/Auth/PostgreSQL lifecycle, P8 crash/ACK/failure injection/resource-large-input/oracle promotion hoặc P19 production promotion.

## P8 staging RTDOSE and independent-oracle continuation — 2026-09-10 / candidate `85ecb0e`

- Người dùng đã xác nhận cho phép upload fixture RTDOSE tổng hợp vào case staging. Kiểm tra read-only tại case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` cho thấy `gamma-rtdose-v1-smoke.dcm` đã tồn tại với UI hash prefix `ca5c9168…`; không upload trùng và không tạo artifact mới. Đây là cùng fixture synthetic đã được sử dụng cho các smoke trước, không có patient/PACS/treatment data.
- Gamma browser smoke trên candidate `85ecb0ebb025220a79cc82977049d2e16340efb0`: profile `PSQA_GAMMA`, RTDOSE reference `gamma-rtdose-v1-smoke.dcm`, measurement 3D evaluation `gamma-measurement-3d-v1-smoke.json`, `PREFLIGHT VALID`; run `df38e7d5-bb4b-4e2d-b949-2310acb1875c` `COMPLETED`, attempt `1`, engine `gamma-nd-p8.2`, `8/8` evaluated/passing, coverage `1`, P95 `0`, pass rate `100%` target `95%`. History vẫn hiển thị 6 completed runs; recheck không tạo run mới. Evidence: `docs/evidence/p8-staging-rtdose-browser-20260910-85ecb0e.json`.
- Script `scripts/verify-p8-independent-gamma-oracle.py` đã được kiểm bằng Ruff và chạy thành công. Oracle tự parse fixture contract, exhaustive GRID node và BILINEAR sampling lattice, sau đó đối chiếu public `calculate_gamma`; 6/6 case PASS, gồm 2D/3D, GRID/BILINEAR, GLOBAL/LOCAL, RELATIVE/ABSOLUTE, OVERLAP_ONLY và max-gamma censoring. Evidence: `docs/evidence/p8-independent-gamma-oracle.json`.
- `P8` vẫn chưa được đóng: local oracle không thay cho staging oracle promotion/commissioning; chưa có evidence staging cho worker crash sau durable commit trước ACK, bounded retry/dead-letter/failure injection, large-input/resource budget hoặc release manifest. Các gate này được giữ mở trong `plan.md`.

## P8 local Redis/worker queue smoke — 2026-09-10

- `docker-compose.yml` đã được bổ sung service `worker` riêng với cùng runtime contract với API: PostgreSQL, Redis, MinIO, Gamma lease/retry/resource settings. `docker compose config --quiet` PASS và container worker khởi động với `queue_backend=redis_stream`.
- `scripts/verify-local-gamma-queue.py` đã chạy thành công với `docs/evidence/p8-local-redis-worker-smoke-20260910.json`, `verification_level=LOCAL_COMPOSE_REDIS_WORKER`, `synthetic_only=true`, `passed=true` trên source commit `f8de071d171a017e5bb6124125414a4357cb5ddb` (evidence được ghi ở commit `a783c33`). Verifier tạo tài nguyên tạm và kiểm tra job `COMPLETED/PASS` 4/4, duplicate dispatch, terminal replay guard, storage failure bounded ở 3 attempts, dead-letter cho attempt cuối và Redis `pending_count=0` sau ACK.
- Kết quả này nâng P08-W03 từ `LOCAL_SLICE_ONLY` lên `LOCAL_COMPOSE_VERIFIED`, nhưng không nâng P8 thành `DONE-v2`: staging crash/ACK injection, staging resource/large-input, oracle promotion/convergence và release-manifest evidence vẫn mở.
- Reliability hardening tiếp theo đã được kiểm tra local: Redis entry malformed không còn làm parser ném lỗi rồi giữ poison message pending vô hạn. Worker phân loại `GAMMA_QUEUE_MESSAGE_INVALID`, ghi dead-letter diagnostic bounded (message id/reason/key summary, không copy payload value) và chỉ ACK sau khi quarantine thành công; terminal `FAILED` redelivery cũng thử dead-letter lại trước ACK. Đây là local contract/test evidence, chưa phải staging fault-injection evidence.
- Verifier integration của cùng checkpoint đã chạy malformed entry qua worker thật: `worker_completed`, `dead_letter_written`, `error_code`, `source_message_recorded`, `payload_value_not_copied` và `queue_acknowledged` đều PASS; Redis sau ACK có `pending_count=0`. Kết quả này chỉ mở rộng local Compose evidence, không đóng staging crash/ACK injection hoặc release gate.
- Verifier v2 chạy thêm ACK recovery probe trên worker/Redis thật của Compose: sau khi run đã durable `COMPLETED`, lần `XACK` đầu bị inject lỗi; pending count giữ `1`, lần ACK kế tiếp về `0`, `GammaRunAttempt` vẫn chỉ có một attempt và result không bị tính lại. Evidence: `docs/evidence/p8-local-redis-worker-smoke-20260910-v2.json` (`passed=true`). Đây là fault-injection local support, chưa thay staging crash sau commit trước ACK.

## P17 staging CT preview recheck — 2026-09-10 / candidate `85ecb0e`

- Trên case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`, fixture synthetic đã có sẵn: 2 RTDOSE VALID, 1 RTSTRUCT VALID, 1 CT VALID và ROI `#1 · P17_TARGET`. Không upload lại RTDOSE và không tạo run mới.
- Chọn CT `p17-ct-v1-smoke.dcm` rồi chạy `Validate & preview`: UI trả `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.` CT slice `#1` hiển thị `LPS LINKED`, `NEAREST_NEIGHBOR_IN_PATIENT_LPS`, ROI overlay đúng và crosshair tại dose grid center; saved run `8000ff9b…` giữ nguyên. Evidence: `docs/evidence/p17-staging-browser-recheck-20260910-85ecb0e.json`.
- Đây là authenticated browser read-only evidence trên candidate `85ecb0ebb025220a79cc82977049d2e16340efb0`; nó chỉ đóng thêm positive CT-preview/validate recheck, không đóng P17 binding P11/P16, failure/resource/volume, export filename hay release gate.

## P4 membership/invitation local slice — 2026-09-09

- Source working tree đã bổ sung migration `20260909_0018_organization_invitations`, `OrganizationInvitation`, partial unique index cho invitation PENDING theo organization/email, member list/toggle và các endpoint tạo/list/revoke/accept invitation.
- Contract giữ nguyên quyết định của người dùng: mọi active member trong cùng organization ngang quyền nghiệp vụ; không có action roles, owner/admin branch hoặc approval hierarchy. `is_active` chỉ là lifecycle/context state và không cho phép tắt member active cuối cùng.
- Invitation local contract: email trim/case-fold; token random 32 bytes chỉ trả ở response create; database chỉ lưu SHA-256; status `PENDING/ACCEPTED/REVOKED/EXPIRED`; accept kiểm verified email, organization archive, active context khác và hỗ trợ replay cùng token/cùng identity về cùng membership.
- Frontend đã có member/invitation panels trong `/app/organization` và public `/invite?token=...` route; login giữ return path nội bộ. Token không được đưa vào list/history/localStorage trong implementation slice.
- Local evidence mới: `test_organization.py` **9 passed**, `test_health.py` và `test_migration_contract.py` trong focused pack tổng **25 passed**, Ruff và strict mypy PASS; frontend lint/typecheck/**5 passed**/build PASS. Riêng `SessionErrorPage` onboarding có regression pack **3/3** tại `docs/evidence/p3-p4-frontend-onboarding-20260909.json`.
- Đây là `STAGING_DEPLOYED_AUTH_E2E_OPEN`, chưa phải `STAGING_VERIFIED`: candidate `2fcf065` đã lên branch staging; `/api/v1/ready` trả HTTP 200 với schema `20260909_0018`, `/api/v1/version` và web bundle cùng nhận diện `2fcf065`, `/api/v1/openapi.json` có member/invitation routes, và các route invitation/member mới trả HTTP 401 khi chưa xác thực. Còn phải kiểm Auth thật và hai identity trên browser, xác nhận PostgreSQL rows/hash/status/audit, replay/revoke/expiry/context/scope/concurrency/timeout trước khi đóng P04-W02/P04-W04/P04-VERIFY.

## P4 invitation lifecycle regression and staging parity — 2026-09-09

- Commit `38dec53d4e542bdf6c4f808283981b344cae3502` bổ sung regression cho hai nhánh còn thiếu ở local: invitation `REVOKED` là terminal, token revoked không accept được nhưng email có thể được mời lại; invitation quá hạn bị chuyển `EXPIRED`, token không accept được và email có thể được reissue. Token không được lưu trong list/closed projection.
- `apps/api/tests/test_organization.py` đạt **11 passed**; full backend suite trên clean tree đạt **172 passed**. Đây là local evidence cho contract revoke/expiry/reissue, không thay cho Auth thật, hai identity, PostgreSQL staging row/hash/audit hoặc concurrency evidence.
- Để tránh source drift do thay đổi chỉ trong `apps/api`, parity marker đã được đặt ở `apps/web/README.md`; Railway staging đã deploy API, worker và web cùng SHA `38dec53d4e542bdf6c4f808283981b344cae3502`, cả ba `SUCCESS`.
- Evidence công khai exact-SHA: `docs/evidence/p19-staging-public-smoke-20260909-38dec53.json` đạt **15/15 checks PASS**, schema `20260909_0019`; health/readiness/version, OpenAPI CT/member/invitation, unauthenticated boundary 401 và web bundle/source marker đều khớp. P4 Authenticated E2E vẫn `OPEN`.

## P4 staging deployment delta — 2026-09-09

- **Source/deploy:** candidate `2fcf065` đã được push lên `codex/p4-org-site-machine` và API/web/worker staging đều đã deploy từ candidate đó. API readiness hiện trả `status=ready`, schema `20260909_0018`; OpenAPI public trả HTTP 200 và chứa các operation `organizations/invitations` và `organizations/{organization_id}/members`.
- **Unauthenticated boundary:** `GET .../{organization_id}/members`, `GET .../{organization_id}/invitations` và `POST .../organizations/invitations/accept` đều trả HTTP 401 với envelope Auth phù hợp; chưa sử dụng dữ liệu bệnh nhân hay secret.
- **Web:** web root trả HTTP 200; bundle mới chứa marker giao diện `Nhận lời mời RT-CONNECT` và `Thành viên ngang quyền`, xác nhận route/UI P4 đã được build.
- **Config parity:** API `/api/v1/version`, web build label và Railway deployment metadata hiện cùng nhận diện `2fcf065`; staging version parity đã pass. Đây không thay cho release manifest production.
- **Evidence level:** `STAGING_DEPLOYED_AUTH_E2E_OPEN`. Chưa gọi `STAGING_VERIFIED` vì chưa có hai identity/Auth browser flow, direct PostgreSQL row/hash/status/audit query, replay/revoke/expiry/context/concurrency/timeout evidence.

- **Public smoke cập nhật:** `scripts/verify-public-deployment.ps1` đã chạy lại với timeout hữu hạn và bổ sung kiểm tra request thực tế không có Auth. Evidence `docs/evidence/p4-staging-public-smoke-20260909-2fcf065.json` ghi **14/14 checks PASS**: health/readiness HTTP 200, schema head `20260909_0018`, version `2fcf065`, OpenAPI có CT preview/member/invitation, ba route membership/invitation trả `401`, web/bundle và UI markers trả HTTP 200. Version parity đã đạt; Authenticated E2E vẫn mở.
- **Public smoke recheck trước đó:** chạy ngày 2026-09-09 với expected version `2fcf065` và schema `20260909_0018`; evidence `docs/evidence/p19-staging-public-smoke-20260909-current.json` đạt **15/15 checks PASS**. Đây là evidence lịch sử của candidate trước source-label fix, vẫn giữ để truy vết và không thay Authenticated E2E/DICOM upload/DVH run/DB row/release gate.

## P19 staging source-label recheck — 2026-09-09

- Candidate `62a7b5300e39b9e742bee0b7353ff86a559d4abe` đã được Railway staging deploy cho API/web; API `/api/v1/health` và `/api/v1/ready` đều HTTP 200 với `status=ok/ready`, schema `20260909_0018`, còn `/api/v1/version` trả đúng source SHA và environment `staging`.
- Web root và bundle mới (`assets/index-Dk9-li-i.js`) đều HTTP 200; bundle có nhúng source SHA. Browser `/app/system/status` hiển thị Build cùng SHA, `SẴN SÀNG`, API `OK`, `READY`, `MATCH`, queue `redis_stream · available · configured`, và organization runs đều bằng 0.
- Evidence: `docs/evidence/p19-staging-source-label-20260909.json`. Điều này đóng source-label API/web staging sub-gate của GAP-09; không chứng minh worker parity, Authenticated E2E, DICOM/DVH, direct PostgreSQL, rollback hoặc production promotion.

## P19 current public smoke after P17 snapshot regression — 2026-09-09

- Commit `71a110a74a2bf14fdc9b288b30decff807329b20` (snapshot regression test plus evidence/documentation) đã được Railway staging serve. `scripts/verify-public-deployment.ps1` chạy với expected version đầy đủ và schema head `20260909_0018` đạt **15/15 checks PASS**: health/readiness HTTP 200, version parity API, CT preview/member/invitation routes trong OpenAPI, ba unauthenticated boundary 401, web index/bundle HTTP 200, CT/membership UI markers và bundle chứa đúng source SHA.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260909-71a110a.json`. Đây là public deployment/source-parity evidence mới nhất; không thay Authenticated E2E, direct PostgreSQL/object probe của P17, worker parity, rollback hoặc production promotion.

## P19 current public smoke after DVH immutability guard — 2026-09-09

- Candidate `d04fb5a3561804bd3553b36886902e1c50b2f18f` đã được Railway staging phục vụ đồng thời cho API/web. `scripts/verify-public-deployment.ps1` với expected version đầy đủ và schema head `20260909_0019` đạt **15/15 checks PASS**: health/readiness HTTP 200, version parity, OpenAPI CT preview + membership/invitation routes, ba unauthenticated boundary 401, web index/bundle 200, CT/membership UI markers và bundle chứa đúng source SHA.
- Evidence: `docs/evidence/p19-staging-public-smoke-20260909-d04fb5a.json`. Đây là public source/schema parity mới nhất; không thay Authenticated E2E, direct PostgreSQL/object probe, immutable-trigger probe, worker parity, rollback hoặc production promotion.

## P19 current public smoke after explicit DVH source-binding UI — 2026-09-09

- Candidate `ddfb43458ab57caa50387880f0f0538af0eb5ca8` đã được Railway staging phục vụ đồng thời cho `Railway-API-staging`, `RT-connect-web-staging` và `RT-connect-gamma-worker-staging`; cả ba deployment đều `SUCCESS`, cùng source SHA và schema `20260909_0019`.
- `scripts/verify-public-deployment.ps1` chạy với exact source SHA và schema head đạt **15/15 checks PASS**: health/readiness/version, schema parity, OpenAPI CT preview + membership/invitation, unauthenticated boundary 401, web index/bundle, CT/membership markers và source SHA trong bundle. Evidence: `docs/evidence/p19-staging-public-smoke-20260909-ddfb434.json`.
- Frontend local trên candidate này đạt **5 test files / 14 tests PASS**, lint, typecheck và production build PASS. Vùng `OPTIONAL EXPLICIT BINDING` đã được expose trong DVH: mặc định không dùng P16/P11; chỉ gửi `limit_entry_id` hoặc `protocol_version_id + protocol_metric_key` khi người dùng chọn rõ nguồn.
- Browser staging đã reload route `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh`, hiển thị build `ddfb43458ab57caa50387880f0f0538af0eb5ca8`, `2 dose · 1 structure`, RTDOSE/RTSTRUCT/ROI và control P16/P11. Preview import một reference P16 tổng hợp trả `hợp lệ 1, loại 0`, nhưng chưa commit entry mới; vì vậy live P16/P11 evaluation vẫn mở và không được ghi thành PASS.
- Đây là public parity/UI evidence, không đóng P17 binding/report cloud, full negative/fault/resource/volume, browser download finalization, worker/release manifest, P4 authenticated lifecycle hoặc production promotion.

## P17 current-candidate negative-path recheck — 2026-09-09

- Trên candidate `dd14ef84f16c66bba45851d98d17f2954ef35fc7`, browser staging chọn RTDOSE cũ có UI hash prefix `544f355fa286…` và chạy `Validate & preview`. API/UI trả đúng `DVH_DOSE_UNITS_UNSUPPORTED` với thông báo yêu cầu `DoseUnits=GY`; đây là validate-only nên lịch sử vẫn có `1` run và không tạo bản ghi mới.
- Sau đó chọn lại RTDOSE tổng hợp hợp lệ với UI hash prefix `ca5c9168eb9b…`; validate trả `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.` Saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4` vẫn giữ nguyên, không có mutation hoặc duplicate run.
- Evidence redacted: `docs/evidence/p17-staging-negative-recheck-20260909-dd14ef8.json`. Đây là bằng chứng negative-path trên current candidate; không đóng các gate fault/resource/volume, P11/P16 binding, browser final filename, release manifest hoặc production promotion.

## P19 production public gap recheck — 2026-09-09

- Read-only probe tới `https://rt-connect-production.up.railway.app` trả `/health` HTTP 200 `status=ok` và `/ready` HTTP 200 `status=ready`, nhưng `/version` vẫn trả `version=0.1.0-dev`, `environment=development`, không có source SHA/schema revision; OpenAPI chỉ có 4 route nền tảng P1 và chưa có CT/membership/clinical routes.
- Railway metadata cho production API ghi deployment `2d94daa6-ecda-4cc0-aaca-c7afd16cfc8d`, branch `main`, commit `fae82738786ef92577dd389711591390f6761741`, `SUCCESS`. Đây là baseline cũ, không phải candidate staging `a39bfa9`.
- Evidence redacted: `docs/evidence/p19-production-public-gap-20260909.json`. Quyết định hiện tại là `PRODUCTION_PROMOTION_BLOCKED`; không suy diễn production-ready từ health/readiness HTTP 200. Không có login, upload, database mutation hoặc dữ liệu lâm sàng production trong probe.

## Current checkpoint

- **Goal:** Hoàn thiện RT-CONNECT theo `plan.md` từ P0 đến P19 và thiết lập baseline vận hành P20.
- **Current phase:** P8/P17 — Gamma RTDOSE worker verification và Visual Dose/DVH structure review đang chạy song song. P8 đã có staging browser RTDOSE + measurement 3D smoke và local independent oracle; P17 staging case đã có RTDOSE/RTSTRUCT/CT và đã qua browser saved-run/CT/export-content, targeted PostgreSQL row/checksum/scope probe cùng object-storage byte re-hash. Các gate P8 crash/ack/retry/resource-large-input/oracle promotion, P17 live binding/report cloud/fault/container-RSS/concurrency và release chưa đóng. Guard ORM + migration PostgreSQL `20260909_0019` đã được deploy và probe trên fixture transaction-local; local synthetic volume measurement đã có nhưng chưa phải performance gate. Song song, P4 invitation/member slice vẫn cần Authenticated E2E/DB lifecycle.
- **Current status:** IN_PROGRESS — candidate `85ecb0ebb025220a79cc82977049d2e16340efb0` có public exact-SHA 15/15; P8 browser run `df38e7d5…` `COMPLETED`, `8/8 PASS`, independent oracle local `6/6 PASS`; P17 browser recheck giữ nguyên case/run và kiểm CT frame positive/no-overlap. P16/P11 chưa có committed compatible reference nên live evaluation vẫn mở. P4 Auth/two-identity/DB lifecycle, P8/P9/P10/P11/P12/P13/P14/P15/P16/P17 closure và production release vẫn mở.
- **Latest P4 regression:** invitation lifecycle local pack đạt **11 passed** trên commit `38dec53d4e542bdf6c4f808283981b344cae3502`; full backend clean-tree suite đạt **172 passed**. Staging source parity của API/worker/web đã được kiểm bằng evidence `docs/evidence/p19-staging-public-smoke-20260909-38dec53.json`.
- **Last authoritative check:** sau commit `85ecb0e`, full backend suite trên tree sạch PASS; Ruff, strict mypy, planning-contract 21 phase, independent Gamma oracle 6/6, frontend lint/typecheck, **5 test files / 14 tests** và production build đều PASS. Public evidence hiện hành: `docs/evidence/p19-staging-public-smoke-20260910-85ecb0e.json` đạt **15/15** với API/worker/web cùng source/schema; không dùng public parity hoặc browser UI để suy ra P4 invitation lifecycle đã staging-verified.
- **Next exact step:** sau khi có quyền tạo một P16 reference tổng hợp staging, commit reference qua workflow Preview → Commit, chạy DVH validate/save với explicit `limit_entry_id`, rồi kiểm PostgreSQL source/evaluation hash, result `actual/limit/margin/status` và report source cloud. Nếu chưa tạo reference, tiếp tục đóng các gate độc lập: browser export finalization, full negative/fault/resource/volume assertions, release manifest và P18 integrated candidate. Không chuyển P17 sang `DONE-v2` chỉ từ run ID, `/ready`, trigger metadata hoặc direct positive row probe.

## P18/P19 implementation support — 2026-09-09

- `apps/api/tests/test_p18_integration.py` bổ sung local integrated pack `P18-W00`: hai hành trình đi qua FastAPI route thật, organization membership scope, nested QA case, artifact/object storage, Machine QA, Gamma worker boundary, report export, trend projection và Biological Toolkit. Kết quả hiện tại: **2 passed**; đây là `LOCAL_VERIFIED` support evidence, không thay staging/pilot/backup-restore.
- `apps/web/playwright.config.ts` bổ sung local `P18-W01a` trên commit `4f9028f`: Chromium desktop VN timezone, mobile VN timezone và desktop UTC; `npm run test:e2e` đạt **3 passed**. Đây chỉ là responsive/timezone support evidence; tenant/dataset/Auth matrix trên staging và remote browser vẫn mở.
- `scripts/verify-public-deployment.ps1` bổ sung verifier không dùng credential: kiểm HTTP health/readiness, schema revision, release version, OpenAPI CT preview/member/invitation routes, unauthenticated boundary, public web index/bundle, CT preview marker và build label; có thể ghi JSON evidence bằng `-OutputPath`. Lần chạy lịch sử staging ngày 2026-09-09 với schema `20260908_0017` đạt **10/10 checks**; lần chạy trước sau migration P4 trên candidate `311abed` đạt **14/14 checks** tại `docs/evidence/p4-staging-public-smoke-20260909.json`; lần chạy hiện hành trên candidate `2fcf065` cũng đạt **14/14 checks** tại `docs/evidence/p4-staging-public-smoke-20260909-2fcf065.json`. Script chỉ là public smoke tool, không thay authenticated E2E, rollback rehearsal hoặc production gate.
- `scripts/verify-local-backup-restore.py` bổ sung P18-W03a: local PostgreSQL custom dump và MinIO object inventory được restore vào database/bucket tạm, row/object inventory hash khớp, rồi cleanup database/bucket đạt. Evidence tại `docs/evidence/p18-local-backup-restore-20260909.json`; đây là local support, không thay provider backup/restore staging hoặc RPO/RTO.
- Evidence tương ứng được lưu tại `docs/evidence/p19-staging-public-smoke-20260909.json`; file chỉ chứa public URL, HTTP/result metadata, bundle hash và không chứa credential, database URL hay dữ liệu bệnh nhân.
- `docs/runbooks/p20-initial-operations-package.md` và `deployment/railway/production-runbook.md` bổ sung P20-W00 support artifact: vận hành, thresholds target, backup/restore, incident, maintenance, promotion/rollback và handoff template. Đây là tài liệu hỗ trợ `LOCAL_SUPPORT_ONLY`; alert thật, provider restore/RPO-RTO, owner handoff và production release vẫn chưa có evidence.
- `scripts/verify-planning-contract.py` bổ sung verifier fail-closed cho P0: kiểm bốn version tài liệu, cross-reference plan, đủ 21 phase P0–P20 trong BA/spec/plan, workflow/success/error/exit section, FR mapping, testcase S/E, B01–B12, G0–G7 và các support artifact. Evidence `docs/evidence/p0-planning-contract-20260909.json` đạt **pass=true, failed_check_count=0**; đây là consistency evidence, không phải runtime/clinical evidence.
- P20-W01 local support slice: `apps/web/src/api/client.ts` có `ready()` và `PlatformStatusPage.tsx` đọc riêng `/health`, `/ready`, `/version` cùng authenticated `/gamma/queue-metrics`. Dashboard hiện có đánh giá tổng hợp độc lập: chỉ `health=ok` + `ready=ready` + schema parity mới là `SẴN SÀNG`; readiness failure/schema mismatch là `CẦN XEM XÉT`, health failure là `API KHÔNG KHẢ DỤNG`, và từng probe vẫn hiển thị riêng. Local frontend **4 test files / 11 tests** (gồm schema mismatch), lint, typecheck và production build PASS; đây chưa phải alert delivery hoặc P20 exit evidence.
- P20-W01 staging smoke lịch sử: sau khi deploy web descendant `03802e7`, authenticated `/app/system/status` đã hiển thị riêng health `OK`, schema readiness `READY`, schema `20260908_0017`, API version `65dd52b` và queue `available/configured`. Đây là dashboard/readiness evidence của candidate cũ; public metadata candidate hiện tại đã được cập nhật ở P4 smoke, nhưng chưa có alert delivery tới kênh thật, backup/restore provider, owner handoff hoặc maintenance evidence nên P20 vẫn `LOCAL_SUPPORT_ONLY`.
- P19-W01 local support slice: `scripts/create-release-manifest.py` và `scripts/release_manifest.py` tạo/kiểm manifest redacted, hash fixture trong repository, kiểm secret-like value, tự tính lại source/service SHA parity và fail-closed theo gate; test `apps/api/tests/test_release_manifest.py` đạt **4 passed**. `manifest_sha256` chỉ là canonical integrity hash, không phải chữ ký chống giả mạo. Tool đã sẵn sàng cho release packet nhưng chưa có production manifest; metadata deployment/backup/remote E2E thật vẫn là gate P18/P19.

## Source documents read

| Source | Version | Status |
| :--- | :--- | :--- |
| `business-analysis.md` | 0.22 | Business source; detailed feature behavior/workflow/error/recovery/state matrix, business feature cards, P4 membership/invitation addendum, phase handoff and P0–P20 contracts |
| `specification.md` | 1.21 | Behavior/data/error/state/numeric contracts; process-RSS/resource-policy/API-responsiveness evidence for P17 Docker workload, operation/evidence record, change-impact/release manifest, P20 status/readiness surface and exact P4/P10/P11/P12/P13/P14/P15/P16/P17 contracts including binding/report/CT preview and malformed Redis quarantine-before-ACK |
| `technical-specification.md` | 1.20 | Architecture reference; Railway source-identifiable release metadata, bounded-context implementation addenda, P4 invitation schema/API, P8 Redis malformed-message quarantine, P17 process-RSS workload verifier/resource policy/API responsiveness, P20 status/readiness dashboard boundary, CT preview adapter, P18 local backup/restore support and cross-document execution references |
| `plan.md` | 4.12 | Phase/workflow/S-E/C/B tests, DoR/DoD, dependency graph, execution gates, execution ledger, full coverage matrix, P4 invitation/member work packages, P8 local worker/quarantine evidence, P17 local resource-gate checkpoint with process RSS/API responsiveness, P20 status/readiness dashboard package, binding/report/CT work packages, backup/restore support, local browser matrix, source-parity recovery rule, operations runbooks and staging gates |

## Phase status

Theo chuỗi thực thi UX1.3 trong `plan.md`, P6 đã hoàn tất `VERIFY` và `HANDOFF`; hiện chỉ P7 được mở. Các dòng P8–P20 bên dưới giữ lại bằng chứng triển khai hoặc kiểm thử của các lát cắt trước, không được hiểu là đã mở trong chuỗi UX1.3 hiện hành.

| Phase | Status | Evidence / next gate |
| :--- | :--- | :--- |
| P0 | DONE | Exit audit passed on 2026-09-05; baseline, traceability, module/route/environment registries and Railway failure issue recorded |
| P1 | DONE | Full local Compose build/health, in-container PostgreSQL migration, synthetic seed persistence, API readiness and web health passed on 2026-09-05 |
| P2 | FOUNDATION READY + LIVE SMOKE PASS | JWT contract, PostgreSQL, Railway staging/production deployment foundation, Supabase Auth configuration and public health/readiness smoke are evidenced; production promotion remains gated by later clinical modules |
| P3 | STAGING E2E PASS | Auth/API bootstrap, organization-scoped dashboard, first-use organization onboarding and protected web routes are deployed; authenticated staging session reached the real organization dashboard |
| P4 | STAGING VERIFIED + HANDOFF COMPLETE | Đơn vị/cơ sở/máy, thành viên ngang quyền, lời mời, xung đột hai phiên và lưu trữ/khôi phục máy đã được nghiệm thu trên staging; P5 được mở theo đúng thứ tự |
| P5 | STAGING VERIFIED + HANDOFF COMPLETE | Danh mục, lịch sử, lưu trữ/khôi phục, xóa hồ sơ tổng hợp riêng không liên kết, lỗi mạng lát cắt đọc và một lượt Gamma 3D thật qua worker staging đã được kiểm chứng. Tệp đo cũ thiếu `coordinate_frame` bị từ chối đúng; fixture mới được tải lại, xác thực hợp lệ và run `aa563fac…` đạt `COMPLETED/PASS`, 8/8, coverage 1, P95 0. Thao tác xóa hồ sơ liên kết `dailyQA` đã được xác nhận trên giao diện; xem trước staging phát hiện 2 kết quả kiểm tra máy và 6 điểm xu hướng, từ chối xóa, tải lại vẫn giữ nguyên hồ sơ và các liên kết. P5 đã bàn giao cho P6; các bài pylinac còn khóa vẫn thuộc P7/P8. Bằng chứng: `docs/evidence/p5-staging-gamma-worker-20260914.json`, `docs/evidence/p5-staging-unreferenced-purge-20260914.json`, `docs/evidence/p5-staging-linked-case-purge-rejection-20260914.json`, `docs/evidence/p5-staging-network-retry-20260914.json` |
| P6 | STAGING VERIFIED + HANDOFF COMPLETE | Provider reconciliation found `27` objects, `27` referenced objects, `0` orphan and `0` missing; signed download returned the expected bytes, filename and content disposition. The public 16/16 recheck matched API version `661582095dccb112af2a9c6bd541b1e4992f0568`; local API/web gates and the authenticated P6 readback passed. Evidence: `docs/evidence/p6-staging-storage-integrity-reconciliation-20260914.json`, `docs/evidence/p6-staging-verification-handoff-20260914.json`, `docs/evidence/p6-staging-public-recheck-20260914-6615820.json` |
| P7 | ACTIVE AFTER P6 HANDOFF / LOCAL VERIFIED SLICE | P07-W02 is locally closed: the API image enforces the `pylinac 3.47.0` wheel hash and the container inventory resolves `62/62` bindings. The capability endpoint is organization-scoped. P07-W03 remains open because the execution adapter, fixture matrix, structured result/overlay/error contracts and user-facing run workflow are not complete. Evidence: `docs/evidence/p7-local-pylinac-registry-20260914.json`; next gate is the first real adapter package, starting with P07-PF. |
| P8 | STAGING RTDOSE/MEASUREMENT 3D + LOCAL INDEPENDENT ORACLE PASS; FULL EXIT GATE OPEN | Migrations `20260907_0007` + reliability slice `20260908_0008`; organization/case-scoped preflight, PSQA/ENGINE_TEST profile, deterministic 2D/3D engine with standard-GY RTDOSE adapter, coverage/censor metrics, logical-role-aware artifact contract and database-fenced lease/attempt/outbox slice are implemented and locally tested. Latest staging candidate `c6252f7557a5c2c893c5e3082035884e9f26c882` has the authorized synthetic RTDOSE fixture and new Gamma 3D run `1d5ee035…` `COMPLETED/PASS`, `8/8`; independent oracle evidence has `6/6 PASS`. Staging crash/ack/bounded retry/dead-letter/resource/large-input and release gates remain open. |
| P9 | STAGING E2E PARTIAL / LOCAL VERIFIED | Report revision/export browser smoke on staging; recheck current candidate, visual/export failure gate remains |
| P10 | STAGING SMOKE PARTIAL / EXIT OPEN | Migration `20260908_0010`, API/UI slice, 7 focused tests and authenticated staging trend smoke pass; large-series, complete negative matrix, visual/accessibility and release evidence remain |
| P11 | LOCAL VERIFIED / STAGING OPEN | Migration `20260908_0011`, library API/UI and local `3/3`; staging browser/consumer snapshot and full S/E/C evidence remain |
| P12 | STAGING E2E PASS / EXIT OPEN | Migration `20260908_0012`, Biological Hub route/API/UI, staging browser create/validate/edit/save/clone/archive/history đã chạy trên dữ liệu tổng hợp; PostgreSQL state, refresh/reconnect, renderer integration và full S/E/C remain |
| P13 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0013`, BED/EQD2 browser validate→save hai snapshot, history readback, chart/table và export đã chạy trên staging; direct PostgreSQL checksum/no-QA-linkage query và release manifest còn mở |
| P14 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0014`; candidate `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b` đã chạy validate-only/no mutation, save, preview reorder không persist, refresh history và JSON/CSV payload parse; comparison `77045b33…`; direct PostgreSQL row/checksum và organization-scope negative probe còn mở, release-manifest test ID đã ghi |
| P15 | STAGING SMOKE VERIFIED / FINAL GATE OPEN | Migration `20260908_0015`; candidate `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b` đã chạy re-irradiation no-recovery/recovery/sensitivity/spatial-unavailable và fraction-compensation prefix/error recovery, refresh history và JSON/CSV payload parse; snapshots `2f66676e…`/`7d805462…`; same-key replay, direct PostgreSQL/scope, full S-E và final filename còn mở |
| P16 | STAGING SMOKE VERIFIED / EXIT OPEN | Migration `20260908_0016`, web build `9262bfd`; staging DRAFT/publish/archive, import row-level invalid, explicit-use snapshot đã pass; direct PostgreSQL/hash/scope, compare/history/export, full fault matrix và release evidence còn mở |
| P17 | STAGING IMMUTABILITY GUARD PASS / EXIT OPEN | Engine/API/UI/migration `20260908_0017`, ORM + database guard `20260909_0019`, bounded CT preview, explicit P11/P16 limit binding and DVH report-source local gates pass; staging `/ready`/`/version` match candidate `d04fb5a3561804bd3553b36886902e1c50b2f18f` and schema `20260909_0019`; target trigger exists, temporary probe rejects UPDATE/DELETE and retained run is untouched; browser RTDOSE/RTSTRUCT/CT run, export-content, direct PostgreSQL row/checksum/scope probe and object-storage byte re-hash pass; binding/report cloud, fault/volume and release evidence remain |
| P18 | LOCAL SUPPORT ONLY | `P18-W00` integrated API pack, `P18-W01a` local browser matrix và `P18-W03a` local backup/restore pass; authenticated tenant/dataset matrix, fault/load, provider restore/RPO/RTO và pilot remain open |
| P19 | SOURCE/SCHEMA STAGING VERIFIED / MANIFEST TOOL READY | API/web/worker source-label recheck trên candidate `0c0b5ff18d0ed62984ae9cb31a7d2aa227a2151b`; public smoke đạt 15/15 health/readiness/schema/version/OpenAPI/unauthenticated/web parity checks với schema `20260909_0019`; release manifest `docs/evidence/release-manifest-staging-0c0b5ff.json` verify `valid=true`, `service_sha_parity=true`, `release_gate=ELIGIBLE`. Authenticated E2E, promotion, remote fault/restore, DNS/TLS/Auth và rollback remain open |
| P20 | LOCAL SUPPORT ONLY | Initial operations and production rollback runbooks exist; alert, provider backup/restore, owner handoff and maintenance regression evidence remain open |

## Live Google Stitch evidence

- Project: `RT-connect`.
- Project ID: `14242591911141046021`.
- Visibility: `PUBLIC`.
- Device baseline: `DESKTOP`.
- Design System: `Clinical Precision Interface`, asset `105b9f4e25334bbcbc6c94d588ee29f9`.
- `list_screens` returned six active resources: four application screens plus logo and avatar.

| Active application screen | Screen ID | Module |
| :--- | :--- | :--- |
| Trang chủ - Home Dashboard | `70b9f1d256884221ae20e63b5244db11` | MOD-01 |
| Kho lưu trữ QA & Thư mục | `4c9ec57310fd404cbae3b53b0bab2368` | MOD-03 |
| Phân tích PSQA Gamma Workspace | `ffb87901b3194bd3aff8760c54c2f9f4` | MOD-04/MOD-06 |
| Trình biên soạn Báo cáo - Report Builder Studio | `a1478466ace843c5aaf9a15dfc58273e` | MOD-07 |
| Biological Toolkit — Independent Calculation Hub | `b32ef9de691f48449ec23e491a6b634d` | MOD-10/P12 |

`get_project` still exposes the four old Biological instances as `hidden`. They are deprecated and must not be restored or used as design-to-code sources. P12 now has a new active design source; P13–P15 will create new screens one at a time in the same project. P12 screenshot asset is `50e2c49b3ec743a59f9d99e8b13e694f` and the generated HTML asset is `d79a76c00dd64ea4a8d7384095860552`.

## Live Railway evidence — verified 2026-09-06

- Project: `prolific-learning` (`339f2c50-ddd7-491f-8c4e-da2a2d169502`).
- Production: environment `910dff25-75b6-42b2-bf6b-e2601ba9d7d2`, API `RT-connect`, PostgreSQL `Postgres`.
- Staging: environment `b0ab34e5-0ff4-479d-8232-659d175e9e2f`, API `gleaming-cooperation`, PostgreSQL `Postgres-Q1Hc`.
- API region in both environments: `us-west2`; the obsolete `sfo` alias was removed from API service configuration after blocking a production deployment.
- Production deployment `ec813793-4e29-4edb-b5d7-f323264da403`: `SUCCESS`, commit `c52b61412c1e1e65b7fca53d7e4d600f85a2dd7e`.
- Staging deployment `2b5270d1-9704-49b3-b3d8-0f8be130d02e`: `SUCCESS`, commit `9bf96e92f6853d5650312c5fcd82ff67a7f85c1b`.
- Both API services use `/apps/api`, `/apps/api/Dockerfile`, `PORT=8000`, `/api/v1/health` and `alembic upgrade head`.
- Public smoke: production and staging both returned HTTP 200 with `status=ok` from `/api/v1/health` and `status=ready` from `/api/v1/ready`; correlation IDs were present.
- PostgreSQL services retain their current persistent-volume region configuration; no database region migration was performed without backup/restore evidence.

## Live Railway storage evidence — verified 2026-09-07

- A persistent Railway S3-compatible storage bucket was deployed in the staging environment for P6 artifact objects; it is not the API container filesystem.
- The bucket was provisioned in Railway's default US West region and exposes an S3-compatible endpoint with automatic region handling. The six staging API variables required by `MinioObjectStorage` were configured without printing their secret values, and the API service was redeployed afterward.
- A direct non-PHI storage probe passed for both path-style and virtual-host-style addressing: put, get, presigned URL generation and delete all succeeded. The bucket remained empty after the probe.
- Staging API health and readiness remained HTTP 200 after the storage-variable redeploy. The remaining evidence is the authenticated web upload → validation → signed download smoke test using the repository fixture.

## Live Railway P8 queue evidence — verified 2026-09-08

- Staging Redis service `Redis` (`ca18f134-82fb-44a1-ac5c-cde76fb33882`) is online and connected to both the API and private `RT-connect-gamma-worker-staging` service.
- Worker deployment `fb446c0e-2a1b-4a17-88f3-aeb8b5318e3c` from commit `5ec12fb` is active and successful. Its deployment log records `Gamma worker starting queue_backend=redis_stream stream=rt-connect:gamma group=rt-connect-gamma` followed by `Gamma worker using Redis Streams queue`.
- After the worker restart, the authenticated Gamma Workspace submitted run `e084529d-6bb1-4119-ae0a-f4da7d371cac`; the run reached `COMPLETED`, `PASS`, 100% (4/4 evaluated and passing points), target 95%, excluded 0 and Gamma P95 `0.0708333333333318`.
- Redis console evidence for the same staging queue: `XLEN rt-connect:gamma = 2`; consumer group `rt-connect-gamma` has 2 consumers, `pending = 0`, `entries-read = 2` and `lag = 0`. This proves publish → claim → analysis completion → acknowledge for the current 2D synthetic scope. It does not by itself close the authenticated queue-metrics API, failure/retry or RTDOSE/3D commissioning gates.
- The deployed web Status page called the authenticated `/api/v1/gamma/queue-metrics` endpoint successfully and displayed `redis_stream · available · configured`, stream `2`, pending `0`, consumers `3`, and organization run counts queued/running/retrying/failed all `0`.

## Live Railway P8 failure/retry evidence — verified 2026-09-08

- The test used the existing valid synthetic reference/evaluation artifacts in QA case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24`; no patient data was used.
- To create a controlled staging failure, the private Gamma worker's object-storage bucket setting was temporarily pointed to a nonexistent staging-only bucket. The API accepted the job and run `26a54046-1f20-454c-b3f4-e766937f30d6` reached `FAILED`, progress `100%`, attempt `1`, with error `GAMMA_STORAGE_UNAVAILABLE` and message `Gamma input could not be read from object storage.`
- The real staging bucket setting was restored. Railway showed the worker Online with no staged variable changes remaining.
- From the authenticated Gamma Workspace, `Retry job` re-enqueued the same run. It reached `COMPLETED` / `PASS` at attempt `2`, with `100%` (4/4 evaluated and passing points), excluded `0` and Gamma P95 `0.0708333333333318`.
- This closes the live staging failure/retry/recovery evidence for the current 2D synthetic adapter. It does not close the RTDOSE/measurement, 3D, large-input or clinical commissioning gates.

## Live Railway P10 Trend evidence — verified 2026-09-08

- Commit `b8c7911` deployed the P10 API migration; public API `/api/v1/ready` returned `status=ready`, `schema_revision=20260908_0010`, and `/api/v1/version` returned `version=9262bfd`, `environment=staging`, `schema_revision=20260908_0010`.
- Web commit `d15738f` deployed successfully on `RT-connect-web-staging`; authenticated browser loaded `/app/trend` and showed Build `9262bfd`, `API THẬT`, six organization-scoped trend points and three compatible series for `Synthetic QA Linac`.
- Baseline workflow: a baseline with explicit effective time before the synthetic points was created and applied; flatness/output-factor displayed delta `0.0000`, while the deliberately mismatched symmetry value displayed `PASS · OUTLIER` and delta `-99.0000`. This is UI behavior evidence on synthetic data, not a clinical limit.
- Maintenance workflow: `Staging QA maintenance smoke` was created for the synthetic machine and appeared in the organization timeline as revision `1`, status `ACTIVE`; the trend point values were unchanged.
- Rebuild workflow: authenticated `Rebuild projection` returned `0` new and `6` existing points, demonstrating the current projection is idempotent for this staging dataset. Day aggregation displayed three buckets, each with count `2`, preserved min/max and two source runs.
- This evidence closes only the basic authenticated P10 staging smoke. Source drill-down/aggregate export download, large-series budget, full P10 S/E/C matrix, visual/accessibility review and P8/P9 remaining release gates must still be recorded before `DONE-v2`.

## Local P11 QA Protocol Library evidence — verified 2026-09-08

- Migration `20260908_0011_protocol_library.py` upgraded successfully on local PostgreSQL and is the current Alembic head. It adds protocol description/applicability/source/lineage/revision fields and rule references without changing the old P7 snapshot semantics.
- `tests/test_protocol_library.py` passed **3/3**. The focused suite covered validate-only with no mutation, create DRAFT, DRAFT edit with optimistic revision conflict, activation, immutable ACTIVE behavior, clone deep-copy and lineage, compare, archive, default archived filtering, organization scope and Machine QA active-only selection.
- Backend full suite passed **81/81**; Ruff and strict mypy passed. Frontend lint/typecheck/Vitest `1/1` and production build passed; the build emits only the known large-bundle warning.
- OpenAPI was regenerated after registering the P11 router. The P11 UI route is `/app/qa-protocols`; the API base surface is `/api/v1/organizations/{organization_id}/qa-protocols`.
- This is local evidence only. P11 staging still requires deployment with schema `20260908_0011`, authenticated browser lifecycle, active protocol consumed by a new Machine QA/Gamma run, old snapshot readback, negative scope/conflict/persistence/capability cases, and release-manifest evidence.

## Local P12 Biological Hub evidence — verified 2026-09-08

- Migration `20260908_0012_biological_scenarios.py` upgraded successfully on local PostgreSQL and is the current Alembic head. It adds organization-scoped `biological_scenarios`, append-only `biological_scenario_revisions` and the read model for `biological_calculation_runs` without a mandatory QA-case/patient relationship.
- P12 API routes are registered under `/api/v1/organizations/{organization_id}/biological`; validate-only, create DRAFT, DRAFT patch with optimistic revision, save to SAVED, clone with source lineage, archive, default archived filtering, revision history, summary/tools and scoped calculation reads are implemented.
- Focused `apps/api/tests/test_biological.py` passed; full backend suite passed after updating the expected schema revision to `20260908_0012`. Ruff/mypy passed, OpenAPI was regenerated, and frontend lint/typecheck/Vitest/build passed. The Vite build emits only the known large-bundle warning.
- The P12 web route is `/app/biological` and uses the generated Stitch screen `b32ef9de691f48449ec23e491a6b634d`. P13, P14, P15 and the local P16 Knowledge Library route are now available in source; the P16 staging/release gate is still open. The UI does not create fake calculation runs and does not link scenarios to QA cases automatically.
- P12 staging browser smoke: authenticated synthetic flow created `STAGING_P12_BIO`, validate-only returned no-mutation success, create/edit/save produced revisions, clone created `STAGING_P12_BIO_COPY_1D3A5958`, archive preserved history, and archived filtering displayed both states. PostgreSQL-state/query, refresh/reconnect, full negative matrix and P9 independent Biological report integration remain open.

## Local P13 BED/EQD2 evidence — verified 2026-09-08

- Migration `20260908_0013_bed_eqd2_calculations.py` upgraded successfully on local PostgreSQL; it adds nullable `idempotency_key` for legacy P12 read rows and an organization-scoped unique index for executable calculation retries. The API default/Compose example schema revision is `20260908_0013`.
- The pure engine `services/bed_eqd2_engine.py` implements finite/nonnegative/positive/integer validation, deterministic pair derivation, explicit `D ≈ n×d` tolerance, valid zero-dose handling, source/reference checks, fixed-n/fixed-d curve generation, duplicate-series/point-budget checks, unrounded LQ calculation and canonical chart checksum.
- P13 API routes are registered under `/api/v1/organizations/{organization_id}/biological`: validate-only, calculation create/replay, chart preview and JSON/CSV export. Every executable result stores scenario revision, raw/normalized input, source, curve, model key/version, result/table/chart checksum and idempotency identity; chart preview is non-persistent.
- The P13 UI route is `/app/biological/bed-eqd2`; it selects a SAVED scenario/revision, exposes fractionation/source/curve controls, displays primary values plus a synchronized chart/table/history, and labels the output as an independent estimate rather than QA/prescription. Stitch screen generation was attempted for the new route but the service returned unavailable; the UI therefore reuses the active Clinical Precision Interface design system and existing Biological Hub visual language.
- Focused P13 engine/API/biological tests passed **10/10**; full backend suite, Ruff, strict mypy, frontend lint, typecheck, Vitest **1/1**, production build and local PostgreSQL migration pass on the working tree candidate. The build emits only the known bundle-size warning.
- This is local evidence only. P13 staging still requires deploy on the candidate SHA, `/api/v1/ready` schema `20260908_0013`, authenticated browser validate→calculate→replay→chart preview→export, PostgreSQL snapshot/checksum/no-QA-linkage evidence, and release-manifest verification.

## Local P14 Plan Comparison evidence — verified 2026-09-08

- Migration `20260908_0014_plan_comparison.py` upgraded successfully on local PostgreSQL; `BiologicalComparisonRun` stores organization/scenario/revision scope, immutable ordered option/input/result snapshots, model/version, warning/error snapshots, idempotency key, actor and timestamps. The unique idempotency constraint is organization-scoped.
- P14 source resolution accepts only organization-scoped, `BED_EQD2` and `COMPLETED` P13 calculation snapshots. The pure engine compares 2–10 distinct options, validates common scenario/revision/tissue/model context, keeps alpha/beta mismatch as `COMPARISON_ALPHA_BETA_MISMATCH` warning with ranking disabled, computes signed absolute/percent delta and returns `null + BASELINE_ZERO` for a zero baseline denominator.
- API routes are registered under `/api/v1/organizations/{organization_id}/biological/comparisons`: validate-only, create/replay, list, detail, non-persistent chart reorder preview, clone and JSON/CSV export. Create/clone plus audit are transactional; retry with the same fingerprint returns the existing snapshot, while a different payload with the same key returns `COMPARISON_IDEMPOTENCY_CONFLICT`.
- The web route `/app/biological/compare` uses the active Clinical Precision Interface visual language. It has an empty state when fewer than two P13 snapshots exist, stable option IDs, baseline selector, compatibility notice, validate/save actions, result table, BED/EQD2 chart, non-persistent reorder preview, history, clone and export actions. It does not add QA/patient/TPS/PACS linkage.
- Focused P14 engine/API/biological tests passed **15/15**. Full backend pytest, Ruff, strict mypy, frontend lint, TypeScript typecheck, Vitest, Vite build and OpenAPI regenerate/check passed on the working tree candidate. Vite retains only the known bundle-size warning.
- This is local evidence only. P14 staging still requires the candidate deployment, readiness schema `20260908_0014`, two source P13 snapshots, authenticated browser validate→save/replay→refresh→reorder/clone/export flow, PostgreSQL row/fingerprint/checksum query and organization-scope negative check.

## Local P15 Re-irradiation/Fraction Compensation evidence — verified 2026-09-08

- Migration `20260908_0015_reirradiation.py` upgraded successfully on local PostgreSQL; Alembic reports `20260908_0015 (head)`. It creates `biological_reirradiation_runs` with organization/scenario/revision lineage, operation type, immutable input/result/warning/error snapshots, model/version, idempotency key, actor, timestamps and organization-scoped indexes/unique constraint.
- The pure P15 engine validates course roles, tissue/OAR dose rows, Gy units, finite numeric values, D/n/d or nonuniform schedules, alpha/beta provenance, recovery range/source, context mismatch, sensitivity, spatial capability and compensation prefix/alternative/interruption/time-model rules. It returns deterministic `result_sha256` snapshots and never produces voxel accumulation or prescription output.
- API routes are registered for validate-only, synchronous create/replay, list, detail and JSON/CSV export for both `REIRRADIATION` and `FRACTION_COMPENSATION`. Validate-only does not insert. Create commits run plus audit; same organization/key/fingerprint replays, different fingerprint conflicts, and persistence failures roll back.
- Frontend routes `/app/biological/re-irradiation` and `/app/biological/fraction-compensation` use the shared Clinical Precision Interface language. They expose saved scenario/revision selection, course×tissue matrix, recovery/sensitivity, planned/delivered prefix, alternatives, interruption/time model, validation, immutable result/history and export states. The page labels all outputs `SCENARIO / ESTIMATE ONLY`.
- Local verification: `tests/test_re_irradiation.py` **5/5**, `tests/test_re_irradiation_engine.py` **22/22**, full backend **133 passed**, Ruff, strict mypy, frontend lint/typecheck/build and OpenAPI regenerate/check passed. The Vite build retains only the existing bundle-size warning.
- This is local evidence only. Staging still requires the candidate deployment, schema/readiness check, authenticated browser workflow for both operations, remote export, direct PostgreSQL row/fingerprint/checksum, explicit out-of-organization negative probe and release manifest. P15 spatial accumulation remains intentionally unavailable.

## Local P16 Biological Knowledge Library evidence — verified 2026-09-08

- Migration `20260908_0016_biological_library.py` upgrades after `20260908_0015` and creates organization-scoped `biological_library_entries` with typed entry families, version uniqueness, clone lineage, optimistic revision, source status, JSON content/citation/applicability and content hash. The Biological bounded context remains independent from QA/patient/treatment records.
- Pure engine `services/biological_library_engine.py` normalizes key/context, validates dose-limit metric/operator/unit/volume/parameter, alpha/beta, source/citation, applicability and safe finite JSON; exact context matching does not treat missing values as wildcard and no external URL is fetched.
- API `api/biological_library.py` exposes validate-only, scoped list/detail/history, DRAFT create/patch, clone/publish/archive, compare, explicit-use snapshot, row-level import preview/commit and JSON/CSV export. Every organization read resolves membership before entity lookup; published entries are immutable and use snapshots pin source/version/hash/override.
- Frontend route `/app/biological/knowledge` provides search/filter, structured editor, validation/warnings, lifecycle/history/compare, import preview/commit, explicit target/override and export states. It reuses the active Clinical Precision Interface and is registered as MOD-14; P15 fraction compensation remains MOD-13.
- Local verification on the same working tree candidate: `tests/test_biological_library.py` **3/3**, full backend suite passed, Ruff, strict mypy, frontend lint/typecheck/Vitest/production build, migration head `20260908_0016` and OpenAPI regeneration/check passed. The Vite build retains only the known bundle-size warning.
- **Evidence level:** `STAGING_SMOKE_VERIFIED`. The authenticated staging browser route on web build `9262bfd` created `P16_STAGING_DMAX_0908` v1 (`DOSE_LIMIT`, `DMAX MAX 45 Gy`, content SHA-256 `9d6555e7403c698ab88a29f2d02f0683a2c24ac7cb772a1ff8bbed8bc2b7dd42`), published revision 2, created explicit-use snapshot `1de9704f6b061e354308…` with `DOSE_LIMIT_NOT_APPLICABLE` warning, and archived revision 3. Import preview reported 1 valid + 1 rejected row with `REQUEST_VALIDATION_FAILED`. Direct PostgreSQL row/hash/scope, compare/history/export, full negative/fault matrix and redacted release manifest remain open. Direct calculator prefill is intentionally a later integration package; explicit-use snapshot currently does not mutate P13–P15/P17.

## Live Railway P16 Biological Knowledge Library smoke evidence — verified 2026-09-08

- API staging `/api/v1/ready` returned HTTP 200 with `status=ready` and `schema_revision=20260908_0016`; the web route `https://rt-connect-web-staging-staging.up.railway.app/app/biological/knowledge` served Build `9262bfd` and exposed the P16 navigation item.
- Using the authenticated synthetic staging session, the browser created `P16_STAGING_DMAX_0908` as a `DOSE_LIMIT` with `DMAX MAX 45 Gy`, Lung cancer/Thorax/VMAT/Spinal cord context, and content SHA-256 `9d6555e7403c698ab88a29f2d02f0683a2c24ac7cb772a1ff8bbed8bc2b7dd42`. The UI/API reported DRAFT v1, then published it as revision 2 and displayed it as `PUBLISHED UNVERIFIED`.
- The import preview was exercised with two rows: one valid synthetic `DOSE_LIMIT` and one row without `entry_key`; the UI reported `Hợp lệ 1 · loại 1` and identified row 2 as `REQUEST_VALIDATION_FAILED`. No invalid row was committed.
- The published entry created explicit-use snapshot `1de9704f6b061e354308…` for `KNOWLEDGE_REFERENCE`; the UI reported `SOURCE_VALUES` and the expected `DOSE_LIMIT_NOT_APPLICABLE` warning, confirming no automatic application into P13–P15/P17. JSON/CSV/download/compare were not used as closure evidence in this smoke and remain to be checked.
- The synthetic entry was archived after the smoke, producing revision 3 and leaving the default active list empty; history/use snapshot remains retained. No patient identifier, QA case, TPS, PACS or clinical prescription was introduced.
- **Evidence level:** `STAGING_SMOKE_VERIFIED` only. P16 `DONE-v2` still requires direct Railway PostgreSQL row/version/hash query, explicit cross-organization negative probe, compare/history/export, full failure/persistence/reconnect matrix and a redacted deployment/config manifest. The browser smoke does not establish clinical validation or direct calculator binding.

## Live Railway P15 Biological smoke evidence — verified 2026-09-08

- Candidate `09acb90` deployed successfully to staging API deployment `008ec1d1-3215-44c7-9d64-fb06dc024e58`; the API readiness endpoint returned HTTP 200 with `schema_revision=20260908_0015`. The web bundle served the P15 routes `/app/biological/re-irradiation` and `/app/biological/fraction-compensation`.
- Re-irradiation browser flow used the saved synthetic scenario `Staging P12 Biological Scenario rev2 · STAGING_P12_BIO`, saved revision `3`, with prior/current courses `60 Gy / 30 fractions / 2 Gy` and alpha/beta `10 Gy`. Validate-only returned `valid` and did not create a snapshot. Save created snapshot `ebc07188-82f2-4d4d-b443-a86105efbc3f`, status `COMPLETED`, result checksum `c5d80c8a8a1250b4be683fcb7f2fb988545784e9b5d055e573627de843f88068`; the UI displayed no-recovery BED `144`, recovery BED `144` for `NONE`, and EQD2 `120`.
- After navigation/reload, the same re-irradiation snapshot remained in history with the same checksum. JSON export returned HTTP 200 and the UI reported a successful download. This demonstrates browser/API/readback/export for the scalar operation; it does not yet demonstrate same-key replay or direct SQL.
- Fraction-compensation browser flow used planned doses `[2,2,2,2,2]`, delivered prefix `[2,2]`, alternatives `[2,2,2]` and `[2.5,2.5,1]`, alpha/beta `10 Gy`. Validate-only did not mutate; save created snapshot `2e9f2767-daa4-4774-a48f-6f1ca47f8ad9`, status `COMPLETED`, result checksum `796fbc91e5b0cc2a7b3fc679c8acbbcd4026e9549858b1999dab407697ba86cf`. The UI showed planned BED `12`, two delivered prefix fractions locked, alternative deltas `0` and `0.15`, and warning `NO_REPOPULATION_CORRECTION` for the `NONE` time model.
- Fraction-compensation JSON and CSV export actions both returned HTTP 200 in the API console. The browser retained the result and history after the operation. Spatial accumulation was not requested as an available capability and no QA-case/patient/TPS/PACS linkage was created.
- **Evidence level:** `STAGING_SMOKE_VERIFIED` for deploy, readiness, authenticated validate-only/no-mutation, save, persisted readback and export of both operations. Still open before P15 `DONE-v2`: same-key idempotent replay, direct PostgreSQL aggregate/id/checksum query, explicit out-of-organization negative probe, full error/fault matrix, release manifest and any independent clinical/scientific validation required by intended use.

## Live Railway P13/P14 Biological smoke evidence — verified 2026-09-08

- Candidate: commit `31a5900`; API deployment `60f181b8-15b9-4377-be9f-7b0635a93127`; web deployment `bcac0a5e-ee4f-47b9-8b1e-40ac744a3a85`; web Build `9262bfd`; API `/api/v1/ready` reported schema `20260908_0014`. The browser used the authenticated staging URL `https://rt-connect-web-staging-staging.up.railway.app` and the existing synthetic organization/scenario only.
- P13 browser flow: the BED/EQD2 route created/read two immutable `COMPLETED` calculation snapshots in the same saved scenario revision `f9fafce0-e224-40b6-8b2a-a9952093f8dc`. Snapshot `4ca56a08-6929-472e-8740-fe15f4f439e6` used `D=60 Gy, n=30, d=2 Gy/fx, α/β=10 Gy`; snapshot `7c229a9c-dff2-4d2d-9eba-3a2bbd6acfbe` used `D=70 Gy, n=35, d=2 Gy/fx, α/β=10 Gy`. The second snapshot displayed `BED=84 Gy`, `EQD2=70 Gy`, history count `2`, and the route reloaded the persisted history after navigation.
- P14 `Validate only` returned `VALIDATION OK` and `Preview không ghi database`, with preview checksum `42885d2c53744a93afed582ba364b1a5b02ebe24cc953ea781d48d13d172927d`; history remained empty immediately before save. The comparison used stable options `option-a`/`option-b`, baseline `option-a`, and the two P13 snapshots above.
- P14 save created comparison `93e281f6-7c35-4f44-8af4-f280f3267c73`, status `COMPLETED`, model `biological.plan-comparison / p14-comparison-1.0.0`, result checksum `42885d2c53744a93afed582ba364b1a5b02ebe24cc953ea781d48d13d172927d`. The result table showed baseline `70 Gy / BED 84 / EQD2 70` and option B `60 Gy / BED 72 / EQD2 60`, with deltas `-12 Gy`, `-14.286%`, `-10 Gy`, `-14.286%`.
- P14 reorder preview returned `PREVIEW · NOT PERSISTED`; its presentation checksum was `81df25686dcf77e2a9237eec831ced5ce6913944c0480d4f720e1cd5367dfff0`, while persisted history retained checksum `42885d2c...` and baseline `option-a`. This demonstrates that presentation order is not used as the baseline and does not overwrite the saved result.
- Clone created `0cc43c7e-aa0f-4d76-bdc6-a3f05d4e5450` with name `P14 treatment plan comparison (clone)`, history count `2`, the same source option values and checksum `42885d2c...`. JSON and CSV export actions both returned the UI success message for the cloned persisted snapshot. A fresh navigation to the P14 route loaded both comparison rows from the API, confirming browser refresh/reconnect readback.
- Scope boundary: this smoke used only synthetic staging data and did not create any QA-case, patient, TPS or PACS linkage. It is browser/API smoke evidence, not a direct SQL query. Direct Railway PostgreSQL row/fingerprint/checksum verification, an explicit out-of-organization negative probe and the release manifest remain open before P13/P14 can be labeled `DONE-v2`.

## Historical Railway evidence (superseded)

> Snapshot superseded on 2026-09-06: staging and production now have separate API/PostgreSQL services, both deployments succeeded with `PORT=8000`, healthcheck `/api/v1/health`, pre-deploy `alembic upgrade head`, and public `/api/v1/health` plus `/api/v1/ready` returned HTTP 200. The older lines below are retained as historical P0/P2 evidence.

> Current deployment IDs: staging `bfc15784-6b59-418d-bba4-134f4a8154af` on `2754013`; production `85d1ba15-f45c-4958-8ebd-fcf09cbf75ef` on `a721cff` (runtime code from `5a5069f`).

- Project: `prolific-learning` (`339f2c50-ddd7-491f-8c4e-da2a2d169502`).
- Workspace: `Mạc Đăng Quang's Projects` (`53fb850d-a59c-4690-816f-01aea06f0645`).
- Only environment: `production` (`910dff25-75b6-42b2-bf6b-e2601ba9d7d2`).
- Only service: `RT-connect` (`9544c3e6-c8bd-4c29-b62e-c6172eb51af3`).
- Latest deployment: `FAILED`, deployment `b8037f6c-720c-407c-b5e4-34421358b4a3`, stopped.
- No service/custom domain and no Railway bucket were present in the status payload.
- Account and project token scopes were verified without printing token values.
- Railway CLI was not installed globally; `npx @railway/cli` version `5.49.1` was used read-only.
- Workspace usage query returned `UNAUTHORIZED`; exact billing/usage remains unavailable with the supplied token scope and must not be guessed.

Failed deployment root cause from build log: Railpack could not determine a build because the deployed commit contained only documents/static files and no `start.sh`, Dockerfile, Python/Node application manifest or supported runnable source. No redeploy was attempted.

## Repository evidence

- Repository contained only the four canonical Markdown files before P0 artifact creation.
- `.env` is Git-ignored and untracked.
- Secret values were not read into output; only key names were inventoried.
- User-owned deletions are preserved: `UI-UX.md`, `DESIGN.md`, `Biological-toolkit.html`.
- User-owned rename is preserved: `technical.md` → `technical-specification.md`.
- No reset, checkout or restoration of deleted files was performed.

## P0 deliverables

| Deliverable | Location | Status |
| :--- | :--- | :--- |
| Baseline snapshot | `docs/p0-baseline.md` | Verified |
| Traceability matrix | `docs/traceability-matrix.md` | Verified |
| Module registry | `docs/module-registry.md` | Verified |
| Route registry | `docs/route-registry.md` | Verified |
| Environment/secret inventory | `docs/environment-inventory.md` | Verified |
| Railway failed-deployment issue | `docs/issues/railway-failed-deployment.md` | Verified |

## Tests and checks

- P0 live Stitch project/screen/design-system check: PASS.
- Railway account-token project query: PASS.
- Railway project-token scope query: PASS.
- Railway status query: PASS.
- Railway failed deployment log retrieval: PASS.
- Railway workspace usage query: UNAVAILABLE (`UNAUTHORIZED`), recorded without guessing cost.
- Documentation consistency scan: PASS — source hashes equal recorded baseline; legacy hidden Biological IDs have no active mapping; all 17 modules occur in registry and traceability matrix.
- Secret scan: PASS — no `.env` value was found in tracked Markdown; inventory contains variable names only.
- Git diff check: PASS — only CRLF conversion notices were emitted; no whitespace error was reported.
- P0 exit audit: PASS — canonical technical filename, no UI-UX dependency, all four active application screens have owners, all other module screen gaps are explicit, Stitch/Railway IDs are recorded.
- P1 API pytest: PASS — 7 tests; FastAPI health/version/error/correlation contracts verified.
- P1 API quality: PASS — Ruff and strict mypy on 15 source files.
- P1 migration contract: PASS — Alembic revision `20260905_0001` renders PostgreSQL DDL successfully; up/down functions are present.
- P1 OpenAPI: PASS — generated contract at `docs/openapi.json` verifies reproducibly.
- P1 API process smoke: PASS — temporary local Uvicorn process returned `health=ok`, a correlation ID and version metadata; process was stopped and port released.
- P1 web quality: PASS — lint, TypeScript type check, 1 component test and production Vite build.
- P1 web E2E: PASS — 1 Playwright Chromium test against production preview build.
- P1 dependency checks: PASS — Python `pip check`; production Node `npm audit --omit=dev --audit-level=high` found no vulnerability.
- P1 source secret scan: PASS — no value from local `.env` appeared outside ignored environment files.
- P1 Compose verification: PASS — Docker Desktop Linux engine built the complete stack; all five services healthy; clean PostgreSQL migration, synthetic seed persistence, API readiness and web health passed. The scoped test stack and volumes were removed by the verifier.
- P2 JWT security contract: PASS — 17 API tests cover missing Bearer, missing configuration, valid asymmetric token, expiry, issuer, audience, role, signature and JWKS-client failure; Ruff and strict mypy pass. This is local cryptographic evidence, not a live Supabase sign-in result.
- P2 deployment preparation: PASS — `apps/api/railway.toml` now applies the baseline migration before deploy; staging Railway/Supabase variable contracts and runbooks are in `deployment/`.
- P2 Railway deployment foundation: PASS — effective settings were applied directly in staging and production; both deployments use `PORT=8000`, `/api/v1/health`, `alembic upgrade head`, and both public `/health` plus `/ready` smoke checks returned HTTP 200.
- P2 Railway permission audit: account token can read production status but `railway link`/environment mutation is rejected with `UNAUTHORIZED`; usage query is also unauthorized. No Railway resource was created or changed.
- The permission-audit snapshot above is historical; the current Railway service settings were successfully changed through the dashboard and are recorded in the superseding live evidence note above.
- P2 Railway source audit: the old failed deployment analyzed `aa5dce6`, but `origin/main` now points to `dc6ee79` and contains the API/web source. The deployment for `dc6ee79` was skipped because the GitHub secret-guard job failed; API and web jobs passed. The CI guard has been corrected to allow `.env.example` templates while rejecting private environment files and credentials.
- P2 post-change local regression: PASS — full `scripts/verify-p1.ps1 -WithContainers` completed after JWT, CORS and Railway manifest changes: 17 API tests, lint/type checks, migration SQL, web checks, five healthy Compose services, in-container migration, synthetic seed persistence, API readiness and web health. The scoped stack and test volumes were removed.
- P2 Stitch recheck: PASS — project `RT-connect` remains public with the Clinical Precision Interface design system, the four active QA application screens, and four hidden/deprecated Biological screen instances. No Stitch design was altered during P2.
- P3 design: Login screen `3b857ee77e7a434d8cfdcda32fd62cdb` generated in the active RT-connect Stitch project using the Clinical Precision Interface design system; no patient data or secret was sent to Stitch.
- P3 local implementation: PASS — `UserIdentity`/`OrganizationMembership`, session bootstrap and organization-scoped dashboard endpoints; migration `20260906_0002`; backend lint, strict mypy and 20 tests pass. Frontend Supabase session/auth routes, protected dashboard and API-backed empty/populated/error states lint/type-check/test/build successfully.
- P4 local implementation: PASS — migration `20260906_0003` adds organization/site/machine lifecycle fields and append-only audit events; all CRUD/list/archive mutations resolve organization scope from the verified identity before resource lookup. Rename preserves `stable_machine_id`; duplicate IDs and second ambiguous organization contexts return explicit conflicts. Backend Ruff, strict mypy and 26 tests pass; frontend organization management page, API client, lint, TypeScript check, Vitest and Vite build pass. No live Auth or staging P4 workflow has been claimed.
- P5 local implementation: PASS — migration `20260906_0004` adds nested organization folders and QA cases; folder rename/move/archive preserves QA case identity, archive does not hard-delete history, case references require an active site/machine/folder in the same organization, and searches support text, folder and QA-cycle filtering. Backend Ruff, strict mypy and 29 tests pass; frontend QA Archive route/API client, lint, TypeScript check, Vitest and Vite build pass. No live Auth or staging P5 workflow has been claimed.
- P6 local implementation: PASS — migration `20260907_0005` adds `artifacts`, `input_manifests` and `validation_runs`; MinIO/S3 storage port, byte-for-byte SHA-256 upload, duplicate detection, signed-download contract, metadata-first DICOM validation and `gamma.measurement.v1` validation are implemented. Focused artifact tests, full API regression, strict mypy, Ruff and frontend checks pass.
- P6 staging evidence: PARTIAL PASS — commit `5b6bf78` deployed successfully to `Railway-API-staging`; the live API exposes the artifact/upload/validation paths; the web staging bundle contains P6 upload UI; the authenticated dashboard, organization, site, machine, folder and QA case are reachable; the persistent Railway bucket is deployed and S3 operations pass. Live artifact upload/validation/download is pending the synthetic fixture selection in the browser.
- P6 authenticated staging evidence: PASS — the user-selected `docs/fixtures/gamma-measurement-v1-smoke.json` appeared as `gamma-measurement-v1-smoke.json` (572 bytes) in QA Archive; upload created the Input Manifest, validation displayed `VALID: 0 lỗi, 0 cảnh báo`, the artifact status changed to `VALID`, and the UI invoked its signed Download action.
- P7 local implementation: PASS — migration `20260907_0006` adds organization-scoped protocol versions/rules, `machine_qa_runs` and `trend_points`; the rule engine covers range/min/max/absolute or percent deviation and N/A, records missing/unit errors, snapshots protocol rules, prevents edits after evaluation, and projects numeric metrics to trend points. Focused P7 tests (3), full API regression (36), strict mypy, Ruff, OpenAPI regeneration/check, frontend lint/typecheck/test/build all pass.
- P7 staging evidence: PASS — deployments `483f1a30-af73-46ea-be9f-a70627802a3a` (API) and `b16a2e5c-f2ea-414e-9c92-d85bf1aea57c` (web) reported successful; authenticated Machine QA seeded `MACHINE_QA_BASELINE` v1, created run `9b18fa2f-7a02-4154-853a-270e890fcabe`, evaluated `100 / 1 / 100` as `PASS`, created rerun `5ac1a1c1-a985-4a40-97e4-0c8a8b6864c0`, evaluated it as `PASS`, and the compare table returned all three metric snapshots.
- P8 local implementation: PASS — migration `20260907_0007` adds `gamma_analysis_runs`; local unreleased migration `20260908_0008` adds fenced lease/attempt/outbox tables; preflight requires two organization/case-scoped validated artifacts; PSQA/ENGINE_TEST profile, idempotency, configuration/checksum/engine snapshots, coverage policy and max-gamma censoring are implemented. The deterministic 2D/3D engine supports the tested `gamma.measurement.v1` slice; result snapshots include map, histogram, pass rate/coverage metrics, percentiles and warnings; the worker persists heartbeat/progress/attempt/failure state. Redis Streams enqueue/claim/ack/reclaim and queue metrics remain available with DB polling fallback when `REDIS_URL` is absent. Full API suite (58), mypy/Ruff and frontend checks pass locally.
- P8 local RTDOSE/3D adapter: PASS — `gamma-nd-p8.2` accepts 2D/3D inline measurement JSON and axial IEC-aligned RTDOSE DICOM; the standard DICOM profile requires `DoseUnits=GY` with explicit `DoseGridScaling`, while JSON CGY conversion is an explicit extension. The adapter validates RTDOSE geometry/scaling and supports a mixed RTDOSE-reference plus measurement-evaluation 3D golden run. The focused adapter suite passed 3/3, including strict RTDOSE metadata validation; staging execution with a real uploaded RTDOSE + measurement pair, independent oracle and large-input behavior remain open.
- P8 staging infrastructure evidence: PASS — commit `310ec13` is deployed successfully to staging API (`d4991d54-2239-4c7d-a7bf-194c01cc4d66`) and web (`eff1f6ca-d9f1-4dec-aecd-955083ecd7ba`); a private `RT-connect-gamma-worker-staging` service (`a1e0c389-e527-4d4c-995e-2a48f4795dda`) uses `/apps/api`, `python -m rt_connect_api.worker`, no public domain and no HTTP healthcheck, with deployment `4c45c69a-457d-4e8f-b1d9-3deb8d48409b` reported `SUCCESS`. This proves infrastructure deployment only, not Gamma job completion.
- P8 authenticated staging golden smoke: PASS for the current 2D synthetic scope — after API deployment `e3d5a46b-7e8f-47fb-a65d-0c4e477c8f61` from commit `1ad0fc3`, `gamma-reference-v1-smoke.json` and `gamma-evaluation-v1-smoke.json` were uploaded as `JSON`, both validated `VALID` with 0 errors/0 warnings, and the private worker completed runs `9c607a9d-0698-4fc4-bf3f-0b50c3bc474f` and `dd82bdbd-c5af-4929-85fd-c4bea595cadd` with `COMPLETED`, `PASS`, `100%` (4/4 points), target `95%`, excluded `0`, and Gamma P95 `0.0708333333333318`. The second run was compared against the first; a full browser refresh restored both completed histories and the result snapshot.
- P8 corrective implementation: commit `1ad0fc3` makes artifact deduplication type-aware, preserves a manifest for a new logical role and makes readiness use the current app settings; commit `50c7917` adds `logical_roles` to artifact responses so Gamma can select Reference/Evaluation consistently after refresh. Backend `42/42`, Ruff, mypy and frontend typecheck/lint/test/build pass locally. The post-deploy browser smoke passed: after a full reload, Reference selected `gamma-reference-v1-smoke.json` and Evaluation selected `gamma-evaluation-v1-smoke.json`.
- P8 queue implementation: commit `4d09e64` adds `redis==6.4.0`, Redis Streams transport (`XREADGROUP`/`XAUTOCLAIM`/`XACK`), API dispatch and retry integration, authenticated `/api/v1/gamma/queue-metrics`, worker Redis mode and focused fake-client tests. Commit `5ec12fb` adds a non-secret worker startup log for the selected backend. Railway staging has a private `Redis` service and the API/worker service variables contain the private `REDIS_URL` reference; the deployed worker and live Redis-consumer smoke are now evidenced above.

## P17 Visual Dose / DVH local implementation evidence — verified 2026-09-09

- **Scope:** local synthetic DICOM only; no patient, PACS or clinical treatment data was used. This is implementation evidence, not clinical validation or production readiness.
- **Engine:** `apps/api/src/rt_connect_api/services/dose_dvh_engine.py` reads physical-dose RTDOSE in Gy with `DoseGridScaling`, normalizes single-frame z offsets, maps patient LPS coordinates using DICOM orientation, selects ROI by ROINumber, rasterizes closed polygons with parity, computes weighted Dmin/Dmean/Dmax/D(x)/V(x), coverage, cumulative curve, dose-native preview and deterministic result SHA. The same resource-bound path now validates `DVH_MAX_CT_PIXELS` for CT-backed DVH operations.
- **CT preview:** the bounded read-only path decodes single-file/supported multi-frame CT, applies HU and window/level semantics, selects CT/dose frames, maps dose and optional ROI masks with patient-LPS nearest-neighbor sampling, reports crosshair/mapping/valid-outside counts and a deterministic preview hash. It does not perform deformable registration, CT-series aggregation, spatial dose accumulation or a DB/job/report mutation.
- **API/storage:** migration `20260908_0017_dvh_analysis.py` adds immutable `dvh_analysis_runs`; `apps/api/src/rt_connect_api/api/dvh.py` provides scoped inputs, validate-only, save/replay, history/detail and JSON/CSV export plus the read-only `GET .../dvh/ct-preview` operation. Every saved run pins artifact/manifest IDs, byte checksums, normalized request, engine version, result/warning/error snapshots and actor; CT preview itself is not persisted as a run.
- **Web:** route `/app/qa/cases/:caseId/dvh` and QA Archive quick link provide input selection, ROI discovery, coverage policy, metric entry, validation preview, save, visual preview, CT frame/window/overlay controls, result/history/provenance and export. The route is case-specific and hidden from the global sidebar.
- **Local checks:** P17 DVH/CT engine/API/report-source/binding focused suite passed **28/28** (`14` DVH engine, `7` DVH API, `4` report-source, `3` Biological Library); the full backend suite passed **169 tests** with engine commit `cdf4372` (`p17-dvh-1.1.0`), được kiểm lại trên clean verification commit `50d890e`, cùng Ruff, strict mypy, frontend lint/typecheck/Vitest/build, migration và OpenAPI checks. The new oracle covers nonuniform slice thickness, volume-weighted Dmean/D(x)/V(x), and the pinned cumulative-DVH interpolation convention; the added regression confirms persisted detail/export remain snapshot-based after source-byte drift. Vite still reports the existing bundle-size warning; it is recorded as a performance follow-up, not treated as a functional pass. Evidence: `docs/evidence/p17-local-volume-weighted-dvh-20260909.json`.
- **P17-W06 local volume/concurrency checkpoint:** benchmark tổng hợp không có dữ liệu bệnh nhân với shape `64×128×128` (`1,048,576` voxel), ROI phủ toàn grid và bốn dose level `1–4 Gy` chạy trên `p17-dvh-1.1.0`; host có median `1.2667533 s`, max peak Python-traced allocation `69,235,606 bytes`; sau rebuild đúng source, API Docker container có median `0.8206198 s`, max peak traced `69,237,022 bytes`, `/health=ok`, `/ready=ready`, schema `20260909_0018`, oracle `Dmean=2.5 Gy`, `Dmin=1 Gy`, `Dmax=4 Gy`, selected volume `12,582.912 cc`. Verifier `scripts/verify-p17-docker-workload.ps1` chạy 2 job đồng thời × 3 lần; 6/6 kết quả giữ cùng engine/oracle, sampled container memory cao nhất `305,659,904 bytes` (291.5 MiB) qua 3 mẫu. Evidence `docs/evidence/p17-local-volume-benchmark-20260909.json`, `docs/evidence/p17-local-docker-volume-benchmark-20260909.json` và `docs/evidence/p17-local-docker-workload-20260909.json`; `performance_gate=NOT_ASSESSED`, vì sampled memory không phải peak RSS/service limit và fault/staging/API responsiveness chưa đo.
- **Local dependency checkpoint:** Docker PostgreSQL 17, Redis 7 và MinIO pinned image đã chạy; Alembic `upgrade head` lần đầu nâng `20260908_0017 → 20260909_0018`, lần chạy lặp lại không còn migration pending, `alembic current` xác nhận `20260909_0018 (head)`. Evidence: `docs/evidence/p1-p17-local-postgres-20260909.json`; không ghi connection string hoặc secret.
- **Configuration regression found and fixed:** Docker Compose từng parse `SCHEMA_REVISION: 20260909_0018` không nháy thành `202609090018`, làm `/api/v1/ready` báo `not_ready` dù DB đúng revision. Đã quote giá trị, thêm test `test_compose_keeps_schema_revision_as_the_exact_string`, recreate API container; readiness sau sửa trả `ready` với `20260909_0018`. Đây là lý do phải kiểm rendered effective config chứ không chỉ đọc file YAML.
- **Not yet evidenced:** deployment of this CT delta on staging, authenticated staging CT artifact upload and browser overlay, direct PostgreSQL row/checksum/scope query, object-storage drift/fault recovery, controlled container peak RSS/resource gate, full negative matrix, staging P11/P16 actual-limit binding/report source and an external/vendor/reference DVH oracle for arbitrary datasets. The committed-fixture independent oracle is now evidenced separately and remains local support only. Local 1M-voxel and 2-job Docker concurrency measurements are recorded separately and are not release gates.

## P17 independent known-answer oracle — local verified 2026-09-09

- `scripts/verify-p17-independent-dvh-oracle.py` validates the committed RTDOSE/RTSTRUCT fixture identity and calculates expected values outside the engine helpers before comparing the engine result. It checks 13 scalar/map comparisons covering selected voxel count, volume, Dmin/Dmean/Dmax, D2/D50/D95/D98 and V0/V5/V8/V20.
- Evidence `docs/evidence/p17-independent-dvh-oracle-20260909.json` records the dose/structure SHA-256 values, engine key/version, expected/observed metrics and all comparison outcomes; **13/13 PASS**. This is `LOCAL_INDEPENDENT_ORACLE_VERIFIED` for the known-answer fixture, not a generic vendor/reference oracle or a staging/clinical-release gate.

## P17 Docker cgroup memory observation — local support rerun 2026-09-09

- `scripts/verify-p17-docker-workload.ps1` now reads cgroup v1 `memory.current`, `memory.max_usage_in_bytes` and `memory.limit_in_bytes` when available, in addition to sparse `docker stats` samples. The rerun kept 2 concurrent jobs × 3 repeats, 6/6 identical engine/oracle results, `/health=ok`, `/ready=ready`, schema `20260909_0018`, and no patient data.
- The API container reported cgroup current `148,406,272` bytes and peak `367,915,008` bytes since container start; the local cgroup limit is unbounded/sentinel. These numbers are explicitly `is_peak_rss=false` and are not a performance pass. Evidence was refreshed at `docs/evidence/p17-local-docker-workload-20260909.json`; the contract wording is synchronized in `specification.md` v1.19, `technical-specification.md` v1.18 and `plan.md` v4.9.

## P17 explicit limit binding and Report Builder source — local candidate verified 2026-09-08

- `apps/api/src/rt_connect_api/services/dvh_limit_adapter.py` now provides the explicit boundary from P17 to P16 `DOSE_LIMIT` entries and P11 `ACTIVE` protocol rules. The adapter scopes the initial lookup by `organization_id`, rejects simultaneous sources, rejects override without a P16 source, validates P16 override fields, requires an explicit P11 metric rule, and never searches or auto-applies a different reference.
- The adapter evaluates supported DMIN/DMEAN/DMAX, Dx and Vx metrics against the already computed DVH result, checks request coverage of Dx/Vx and unit compatibility, preserves the pure engine hash as `engine_result_sha256`, and writes a separate binding/evaluation hash. Source warnings are preserved; `rule_status` is separate from display `status=REVIEW_REQUIRED`.
- `apps/api/src/rt_connect_api/api/reports.py` accepts a saved DVH run as `source_type=DVH` and snapshots it only when the run belongs to the current organization. `ReportBuilderPage.tsx` can select a QA case and its DVH history; report creation does not rerun DVH or resolve a different latest run.
- **Local evidence:** focused suite `26 passed` (13 DVH engine + 6 DVH API workflows + 4 report tests + 3 Biological Library tests), full backend suite `168 passed`, Ruff and strict mypy pass; frontend lint/typecheck/Vitest pass. Added coverage includes P16 D95 binding, P11 lowercase rule lookup, binding conflict, missing metric, invalid override, fail-closed DVH input discovery/validation when the manifest is pending, invalid, or does not match the artifact checksum, CT Frame of Reference mismatch, no-overlap read-only preview, CT resource guard, changed CT bytes, and the Compose schema-revision type regression.
- **Not yet evidenced:** authenticated browser selection of a real saved DVH run, PostgreSQL source/evaluation hash query, CT preview staging binding, resource/fault/volume gates and independent/reference DVH oracle. Deployment/readiness of the previous candidate is verified, but the local contract plus health/readiness are not a complete staging workflow or clinical-readiness claim.

## Live Railway P17 deployment/readiness evidence — verified 2026-09-08

- Staging API service `Railway-API-staging`, worker `RT-connect-gamma-worker-staging` and web service `RT-connect-web-staging` all redeployed from commit `a546bb15155baa6ce3b59a86d1f1e1240aaf6c5a` and report `SUCCESS`: API deployment `99daa470-cea3-4bd9-a265-6a13632e750d`, web deployment `fa69b146-1f4d-4972-83ec-c14a9bb11a6d`, worker deployment `b9d814d2-dd9d-4caa-9246-30fd377f0ae5`. The effective service roots remain `/apps/api` for API/worker and `/apps/web` for web; the existing API config-as-code path `/apps/api/railway.toml` is preserved.
- API `https://gleaming-cooperation-staging.up.railway.app/api/v1/health` returned HTTP 200 with correlation ID; `/api/v1/ready` returned HTTP 200 with `status=ready` and `schema_revision=20260908_0017`; `/api/v1/version` returned HTTP 200 with application build identifier `9262bfd` and the same schema revision. `/api/v1/openapi.json` returned HTTP 200 and exposed `limit_entry_id`, `protocol_version_id`, `protocol_metric_key`, `limit_override` and report `source_type=DVH`.
- Web `https://rt-connect-web-staging-staging.up.railway.app/` returned HTTP 200 and served the candidate bundle (`index-DOkYs2lH.js`, `index-Ks1ZYwE_.css`). Browser navigation can open `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh` and display the P17 workspace; authenticated saved-run selection is still pending because the case has no RTSTRUCT yet.
- The existing synthetic case currently exposes one valid RTDOSE and zero RTSTRUCT artifacts; the P17 controls therefore correctly show `1 dose · 0 structure` and keep `Validate & preview`/`Tính và lưu DVH run` disabled. This is an expected input-preflight state, not a server/deployment failure.
- The committed synthetic RTSTRUCT candidate is `docs/fixtures/p17-rtstruct-v1-smoke.dcm`, generated by `scripts/generate-p17-dvh-structure-fixture.py`. Local known-answer output is `FULL_ROI`, 4 selected voxels, mean `6.5 Gy`, D95 `5.20 Gy` under the volume-weighted piecewise-linear cumulative-DVH convention, SHA-256 `16a79df3129757d9df8b48bd095f0b4b70b24713ea5255e24719d46e6808d401`. It has not yet been uploaded to staging, so no staging DVH run ID is claimed here.

## P17 CT preview delta — staging deployment verified, CT data workflow pending — 2026-09-09

- **Implementation:** `apps/api/src/rt_connect_api/services/dose_dvh_engine.py` now accepts the configured CT pixel budget through both DVH validation/run and CT preview paths; `apps/api/src/rt_connect_api/api/dvh.py` exposes the read-only `GET .../dvh/ct-preview` contract. `apps/web/src/pages/DVHPage.tsx` renders CT grayscale/HU, dose/ROI overlays, frame/window controls and patient-LPS crosshair metadata.
- **Contract:** supported scope is a validated CT single file or supported multi-frame object with top-level geometry, same `FrameOfReferenceUID` as RTDOSE, single-channel MONOCHROME1/2, bounded preview pixels and nearest-neighbor overlay. CT series aggregation, Enhanced CT functional-group-only geometry, external/deformable registration and spatial accumulation remain unsupported.
- **Verification:** CT engine/API cases, full backend suite, Ruff, strict mypy, frontend lint/typecheck/Vitest/build, migration and OpenAPI checks passed on the working tree. The bundle-size warning remains a recorded performance follow-up.
- **Deployment state:** at the captured checkpoint, Railway API deployment `c5807acb-dd49-4279-8304-ecc95141543d` is `SUCCESS` from functional source `893ae2d46c197b80fc78e29cdea25ab19a54154c`; web `da3a82c5-8ec0-436c-a879-8acb118350a5` and worker `01191861-6bae-4b53-bef9-4aa41fc883b` are `SUCCESS` from documentation-only descendant `7c8ebe15152fb7017307c2ab2d337e051a04cfb4`. Public OpenAPI contains the CT route and the web bundle contains the CT controls. `/api/v1/version` still reports application build label `9262bfd`, so release metadata must later be made source-identifiable; do not treat the label alone as proof of source parity.
- **Next exact action:** use the committed synthetic CT/RTSTRUCT fixture only after the user confirms the browser file-selection step; upload and validate both in the staging case, then capture CT success S12–S16 and error/recovery E24–E30 evidence without using patient data.
- **Fixture readiness:** the committed CT fixture is now available at `docs/fixtures/p17-ct-v1-smoke.dcm`; its frame 1 is the positive overlay oracle and frame 2 is the explicit no-overlap oracle. The repository hash must be compared with the uploaded artifact manifest before any staging run is treated as evidence.

## P6/P17 Archive DVH preflight truthfulness — local verified 2026-09-09

- The QA Archive DVH shortcut no longer renders a static claim that `RTDOSE + RTSTRUCT` are already `VALID`. It now derives the banner from the current case artifact list and counts only `DICOM` artifacts whose `data_status` is `VALID`, split by `RTDOSE`, `RTSTRUCT` and `CT` modality.
- The empty/partial-input state is explicit: the staging case with one valid RTDOSE and zero RTSTRUCT is shown as `DVH preflight: 1 RTDOSE · 0 RTSTRUCT · 0 CT VALID`, with the DVH action remaining unavailable at the case workspace until the required inputs exist. The archive hint also states that RTDOSE and RTSTRUCT are required, CT is optional for anatomy overlay, and only validated DICOM artifacts participate in preflight.
- Loading and artifact-fetch failure have separate labels, so a transient API state is not presented as clinical input readiness. The summary helper is covered by frontend tests for valid/invalid/non-DICOM filtering and loading/error/ready labels.
- Local verification after the correction: ESLint PASS, TypeScript typecheck PASS, Vitest **8/8** PASS, production build PASS. The existing Vite bundle-size warning remains a performance follow-up only.
- **Staging runtime probe after push:** commit `558febf26335b3aa533989f0ceb9aebceee4ec6f` was pushed to the configured branch; the public web now serves bundle `assets/index-7zlr-Qxu.js` (SHA-256 `93b0fc4ce8e112b722babc9ea9f32330a281096e2fb4ab5f67dab2a65ab83c08`). Authenticated browser observation of case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` confirmed the dynamic partial-input label and absence of the old static claim. Evidence: `docs/evidence/p17-staging-archive-dvh-preflight-20260909.json`. This is a UI/runtime probe, not source-to-runtime release-manifest parity.
- This correction improves the evidence boundary but does not close P17: authenticated staging upload of the synthetic RTSTRUCT/CT, validation, DVH validate→save→replay→refresh/export, CT preview/overlay, direct database/hash/scope checks, fault/volume/resource gates and independent oracle remain open.

## Current blockers and required gates

The older Railway-history bullets below are retained as evidence of earlier incidents. The current gates are:

- The authenticated staging user and organization onboarding path are working. A fresh browser test should still be repeated after session expiry before treating the auth path as operationally stable.
- P8 current remaining gates: the 2D synthetic worker flow, Redis Streams claim/ack, queue-metrics API, result snapshot, compare and browser refresh persistence are evidenced, as is a controlled staging `FAILED → retry → COMPLETED` recovery. The local RTDOSE/3D/profile/coverage/fencing slice is tested, but migration `20260908_0008` deployment, authenticated staging execution with a real RTDOSE + measurement pair, independent oracle, crash/ack/bounded retry/resource evidence and large-input behavior remain open; P8 is not complete until those gates are implemented and verified or the plan scope is explicitly revised.
- The P7 branch has not been promoted to production. Production promotion remains blocked until Gamma/report/trend/protocol gates, backup and rollback evidence exist.

- Correction on 2026-09-05: both Railway tokens are present in root `.env` and authenticate successfully through the Railway API. Account-token access resolves project `prolific-learning`; project-token scope resolves its production environment. The earlier missing-token report was incorrect. Standard dotenv parsing supports spaces around `=` and quoted values.
- Supabase URL and publishable key are present as names but have empty values. This is the remaining Auth configuration dependency.
- Current Supabase project `RT-connect` is the production `main` branch. Preview branching requires a paid Supabase Pro upgrade, so it is not a suitable free staging isolation mechanism. Do not silently use that production Auth project as the formal staging identity plane; create a separate staging project or explicitly accept a documented temporary shared-auth exception.
- Actual credentials were found in `.env.example` and replaced with empty placeholders; the user's `.env` was preserved.
- Railway account token lacks the write scope needed to create/link staging and the usage scope needed to view costs. A project-write credential is required before any billable Railway resource can be provisioned.
- The current Railway production service has not deployed `dc6ee79`; it still reports the old failed deployment and the new deployment as skipped. After the CI fix is pushed and green, verify Railway sees `dc6ee79` before any staging/production deployment decision.
- The live Railway service metadata still reports `rootDirectory=null` and `dockerfilePath=null`. Configure `/apps/api` on a staging service/environment before testing the Railway Dockerfile; do not use the current production service as the P2 test target.

## Known limitations

- Production has not yet received the P6 artifact branch; promotion remains intentionally gated by the staging artifact E2E and later clinical-module gates.
- The earlier pre-upload checkpoint requiring an explicit synthetic RTSTRUCT upload is superseded by the verified P17 staging RTDOSE/RTSTRUCT/CT browser smoke below; it remains in this section only as historical context. No patient or clinical dataset was used.
- Four Biological designs must be regenerated in P12–P15.

## P17 staging RTDOSE/RTSTRUCT/CT browser smoke — verified 2026-09-09

- **Scope and authorization:** after explicit user confirmation, only the repository-generated synthetic RTDOSE fixture was uploaded to the existing staging case; the case already contained the synthetic RTSTRUCT and CT fixtures uploaded earlier. No patient, PACS or treatment dataset was used.
- **Artifact evidence:** case `8bc86303-c7e9-4e1a-b012-cfbe2a07ba24` exposes two valid RTDOSE artifacts, one valid RTSTRUCT and one valid CT. The selected RTDOSE is `gamma-rtdose-v1-smoke.dcm` with local SHA-256 `ca5c9168eb9b045e30a375edc6b76118efd754a35815c2860b17ca8944c4480b`; staging UI shows the matching prefix `ca5c9168eb9b045e…`. RTSTRUCT and CT UI prefixes match local fixture hashes `16a79df3129757d9…` and `0b1d3bfd6adf33f1…` respectively. Artifact IDs and the complete redacted evidence record are in `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`.
- **Fresh browser workflow:** the current web build `4b6423e5efe8fb10a9832bd66ed051f259ccb01b` (functional correction from `fbbfa812feaa164197259f83e581e9271a2df670`, followed by the evidence-only docs push) was loaded from the pushed branch. On fresh navigation to `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh`, the default valid RTSTRUCT automatically loads ROI `#1 · P17_TARGET · 1 contour`; `Validate & preview` and `Tính và lưu DVH run` are enabled. The saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4` reappears after refresh with engine `p17-dvh-1.1.0`, `FULL` coverage, 4 voxels, volume `0.004 cc`, Dmean `6.500 Gy`, D95 `5.200 Gy`, input fingerprint and result SHA preserved.
- **CT browser workflow:** selecting CT frame `#1` returns `LPS LINKED`, `NEAREST_NEIGHBOR_IN_PATIENT_LPS`, ROI `#1 · P17_TARGET`, and crosshair `dose grid center`. Selecting frame `#3` (`frame_index=2`, the repository's no-overlap oracle) returns `NO DOSE OVERLAP` and the expected warning that the selected CT slice does not intersect the RTDOSE grid; the dose overlay is empty. This confirms both the positive overlay and the bounded warning path on staging.
- **Negative validation workflow:** selecting the older staging RTDOSE with UI hash prefix `544f355fa286…` and running `Validate & preview` produced the expected `DVH_DOSE_UNITS_UNSUPPORTED` error because its dose units were not `GY`; history remained at one saved run and no new run was created. Restoring the newly uploaded RTDOSE with UI hash prefix `ca5c9168eb9b…` and validating again produced `Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.` This confirms the unit guard and the non-mutating validate-only path; the full P17 negative/fault/resource matrix remains open.
- **Direct PostgreSQL probe:** a read-only query executed inside the connected Railway staging API container returned the three artifact rows, three `input_manifests` rows and the saved DVH row for the case. All artifact/manifest/run organization and case scopes matched; all three artifacts and manifests were `VALID`; every manifest checksum matched its artifact SHA-256; the persisted run was `COMPLETED`, `p17-dvh-1.1.0`, with the expected dose/structure/CT IDs, request fingerprint and result SHA. Evidence is recorded in `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`; the follow-up object-storage byte re-hash and snapshot-field recheck also pass, while the stronger immutable-snapshot mutation guard remains open.
- **Snapshot recheck:** a second read-only query after the object re-hash returned the same DVH run fingerprint/result SHA, with `created_at == updated_at` and no mutation command issued. This is a direct persistence observation, not proof against privileged database tampering; the application-level source-drift/detail/export regression is covered by the local focused suite below.
- **Object-storage byte re-hash:** a read-only probe in the connected Railway staging API container downloaded the three case objects through the configured storage adapter. Observed byte sizes `898/866/842` and re-hashed SHA-256 values matched the corresponding artifact rows for RTDOSE/RTSTRUCT/CT; assertion `object_count=3`, `byte_rehash=True` passed. Evidence is recorded in `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`; this closes the object-byte integrity sub-gate only. The immutable-snapshot mutation guard and broader fault/resource/release gates remain open.
- **Frontend correction shipped with the smoke:** `apps/web/src/pages/DVHPage.tsx` now separates the initial input manifest from the structure-specific ROI request and renders `Chưa chọn CT` when the optional CT query is disabled; `apps/web/src/pages/DVHPage.test.tsx` pins both behaviors. Web typecheck, lint, Vitest **12/12** and production build pass; the existing Vite chunk-size warning remains a performance follow-up.
- **Export probe:** the JSON and CSV buttons were exercised for the saved run. The browser harness did not expose a download event, but both browser download contents were captured and parsed from the local Downloads directory: JSON `17,738` UTF-8 bytes, SHA-256 `9e1106e3a1e2a5e4964dd109f650c88ea9513d80ae1ec6b0d91b60014b656723`, valid JSON with matching run ID/input fingerprint/result SHA; CSV `10,478` UTF-8 bytes, SHA-256 `c626590dcb470d8d60a67d2f8d7a62c22928de40997d455c960ee22aeed15766`, 21 parsed rows with matching case/engine/result SHA. The browser harness retained the `.crdownload` suffix, so final filename finalization remains a browser/runtime observation rather than an application-content failure.
- **Boundary:** this closes the authenticated browser upload/validation/ROI/DVH/CT-preview, export-content, targeted direct PostgreSQL row/checksum/scope and object-storage byte-integrity sub-slices only. Immutable-snapshot mutation guard, full negative/fault/resource/volume gates, P11/P16 binding/report cloud evidence, browser finalization, release manifest and production promotion remain open. The older “fixture not uploaded” bullets above are historical checkpoints and are superseded by this section.
- **Local regression after this checkpoint:** the focused P17/P16/report/library suite (`test_dvh_engine.py`, `test_dvh.py`, `test_reports.py`, `test_biological_library.py`) passed **28 tests**, including saved-run detail/export stability after source-byte drift. This is local evidence and does not replace the staging fault/resource or release gates.

## P17/P19 latest source-parity and browser recheck — 2026-09-09

- Candidate `7a340b281f0bf8a91a5c72dc861c71c82009bce8` is now the current staging source-parity checkpoint. API, web and worker were redeployed from the documentation/source-parity commit; public verifier evidence `docs/evidence/p19-staging-public-smoke-20260909-7a340b2.json` reports **15/15 checks PASS**, schema `20260909_0019`, API version parity and web bundle/source marker parity.
- The authenticated browser was reloaded on that build at `/app/qa/cases/8bc86303-c7e9-4e1a-b012-cfbe2a07ba24/dvh`. It observed `2 dose · 1 structure`, the selected synthetic RTDOSE prefix `ca5c9168eb9b…`, selected synthetic RTSTRUCT/CT, ROI `#1 · P17_TARGET`, saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`, and CT overlay `LPS LINKED` / `NEAREST_NEIGHBOR_IN_PATIENT_LPS` with the expected crosshair. This is a recheck of the existing synthetic staging data, not a second upload.
- JSON/CSV export payloads were captured again from the browser Downloads directory. JSON (`17,738` bytes) parsed and matched the run/result SHA; CSV (`10,478` bytes, 21 rows) parsed and matched case/engine/result SHA. Both files remain `.crdownload` in the Edge/CUA harness, so final filename finalization is **UNVERIFIED**. The application-content sub-gate is PASS; the browser/runtime finalization observation remains open and is not silently promoted to PASS.
- Updated evidence: `docs/evidence/p17-staging-dvh-ct-browser-20260909.json` (`latest_runtime_recheck`) and `docs/evidence/p19-staging-public-smoke-20260909-7a340b2.json`. P17 remains `IN_PROGRESS`; remaining gates are browser finalization evidence, full negative/fault/resource/volume checks, binding/report staging evidence, worker/release manifest and production promotion.
- Report-source follow-up: Report Builder đã tạo revision 1 `P17 staging DVH report smoke` từ đúng saved run `8000ff9b-7a02-4cec-850e-e27e4fe50cc4`; snapshot SHA `fd99a61aed10191ae169155bfd645c02ef56ffda2ded03384efe43b22d01ea85`, input fingerprint và result SHA khớp run. JSON export object-storage document báo `10,536` bytes, renderer `report-renderer-0.1`, source ID và content SHA khớp; không rerun DVH và không mutation `DVHAnalysisRun`. Evidence nằm trong `report_builder_probe` của `docs/evidence/p17-staging-dvh-ct-browser-20260909.json`. P11/P16 limit/protocol binding vẫn chưa được gắn và tiếp tục là gate riêng.

## P17/P19 source-parity recovery — 2026-09-09

- Public verifier phát hiện drift sau commit `0098cf1`: web đã nhận docs-only descendant, còn API vẫn ở `7a340b…` do path filter; đây là deployment/source-parity drift, không phải lỗi case, database hay DVH.
- Đã đặt parity marker trong cả `apps/api/README.md` và `apps/web/README.md`, push candidate `b0263c932c740d4f36f19867241d5c1e07014765`, chờ Railway deploy đồng bộ và chạy lại verifier với schema `20260909_0019`.
- Kết quả public **15/15 PASS**; evidence `docs/evidence/p19-staging-public-smoke-20260909-b0263c9.json`. API `/health`, `/ready`, `/version`, OpenAPI và unauthenticated membership boundary PASS; web index/bundle, CT/membership marker và exact source marker PASS.
- Evidence drift trước sửa được giữ tại `docs/evidence/p19-staging-public-smoke-20260909-drift-0098cf1.json` để truy vết. Quy tắc kế hoạch mới: commit docs/root hoặc chỉ một service phải kèm parity marker/watch-path change hoặc deploy thủ công service còn lại, sau đó exact-SHA verifier mới được phép ghi `source parity PASS`.
- Fixture RTDOSE tổng hợp được upload theo xác nhận của người dùng từ trước và không upload lại trong lần recovery này; case vẫn giữ `2 RTDOSE · 1 RTSTRUCT · 1 CT`, saved run và report snapshot hiện có.
## P17 — local negative/resource regression checkpoint — 2026-09-11 / `f05508e`

- Chạy lại đúng source hiện tại `f05508ecb8ce7213eceaf4ac8bf9a0a71833a7e6`: `34/34` test trong `test_dvh.py`, `test_dvh_engine.py` và `test_migration_contract.py` PASS; các cảnh báo chỉ là deprecation/resource warnings, không có failure.
- Các nhánh đã được chạy gồm manifest/checksum/source drift, storage outage không tạo run, archived case, CT frame mismatch, CT no-overlap, CT resource limit, unsupported geometry và ORM immutability. Migration contract cũng xác nhận guard PostgreSQL được khai báo.
- Independent known-answer oracle chạy `13/13` comparison PASS với fixture RTDOSE/RTSTRUCT tổng hợp và engine `p17-dvh-1.1.0`.
- Evidence: [p17-local-negative-resource-20260911-f05508e.json](docs/evidence/p17-local-negative-resource-20260911-f05508e.json). Đây chỉ là `LOCAL_VERIFIED_SLICE`; chưa đóng staging PostgreSQL trigger probe, staging fault/resource/large-volume, provider restore, release hoặc production gate.
## P7-W03 — chặn chạy Pylinac khi tệp chưa được kiểm tra — lát cắt cục bộ — 2026-09-15

- API Pylinac nay yêu cầu mọi tệp đầu vào có trạng thái `VALID` trước khi tạo lượt phân tích. Tệp còn `UPLOADED`, `VALIDATING`, `WARNING` hoặc `INVALID` đều bị chặn tại preflight với thông báo hướng dẫn người dùng kiểm tra dữ liệu; bài hiệu chuẩn chỉ nhập số đo vẫn không bị ảnh hưởng.
- Kiểm thử hồi quy xác nhận hai nhánh: tệp DICOM đã kiểm tra hợp lệ được chạy và lưu kết quả/ảnh minh họa; tệp chưa kiểm tra bị từ chối trước khi gọi engine và không tạo lượt chạy rỗng. Cổng giao diện đã có thông báo tiếng Việt tương ứng.
- Đã bổ sung đường xác thực tối thiểu cho toàn bộ dạng tệp mà các bài Pylinac đang khai báo: ZIP phải có thành viên DICOM đọc được; ảnh PNG/JPEG/TIFF hoặc DICOM ảnh phải có header/kích thước hợp lệ; nhật ký `.dlg`/`.bin`/`.tlog`/`.txt` phải không rỗng. Các dạng CSV/PDF vẫn giữ cảnh báo “chưa có bộ kiểm tra nội dung” và không được đưa vào Pylinac nếu chưa có hợp đồng riêng. Bằng chứng: [cổng kiểm tra tệp Pylinac](docs/evidence/p7-local-input-validation-gate-20260915.md).
- Kiểm thử mục tiêu Pylinac đạt **3/3**, kiểm thử đường xác thực ZIP/ảnh/nhật ký đạt **1/1**; đây là cổng an toàn đầu vào của P7-W03, chưa thay thế fixture chuẩn/commissioning, đối chiếu chỉ số độc lập hoặc kiểm chứng staging. P7 vẫn mở.
- Sau khi đẩy commit `783f8b5`, staging tự triển khai và bộ kiểm tra công khai exact-SHA đạt **16/16**; API/web cùng nhận đúng mã nguồn và lược đồ `20260914_0023`. Bằng chứng: [P7 cổng đầu vào trên staging](docs/evidence/p7-staging-input-validation-gate-20260915.md). Đây chỉ là cổng parity triển khai, chưa phải kiểm chứng chạy từng bài Pylinac trên staging.

- Sau commit `ffad35305fa8a30d33ec052a793d85b0a28112d4`, API, giao diện và tiến trình nền staging đã được buộc dựng lại cùng nguồn; bộ xác minh công khai đạt **16/16**, API sẵn sàng với lược đồ `20260914_0023`. Trình duyệt staging mở bài Kiểm tra sao trên hồ sơ tổng hợp, hiển thị bảng kiểm tra đầu vào và báo tệp hiện có là **Hợp lệ**; lịch sử chưa có kết quả. Không chạy engine vì tệp đang có là RTDOSE tổng hợp, không phải fixture Starshot phù hợp. Bằng chứng: [giao diện cổng đầu vào Pylinac trên staging](docs/evidence/p7-staging-input-validation-ui-20260915.md). Đây là cổng UI/runtime và parity, chưa đóng chạy engine Starshot hay VERIFY/HANDOFF P7.

- Ma trận tệp mẫu chính thức Pylinac nay đã có kiểm thử hồi quy tự động tại `apps/api/tests/test_pylinac_official_demo_matrix.py`: **36/36** trường hợp đạt, bao gồm Picket Fence, Starshot, Winston–Lutz, ba bài VMAT, bốn CatPhan có mẫu, TomoCheese, hai nhãn Quart, 19 bài ảnh phẳng, Field Profile/Field Analysis, Dynalog và Trajectory Log 2.1. Kiểm thử dùng chính `execute_pylinac`, kiểm lớp engine, structured result và overlay; không ghi staging. Bằng chứng: [ma trận tệp mẫu tự động](docs/evidence/p7-local-pylinac-official-demo-matrix-20260915.json). Đây là tiến bộ của W03, chưa đóng W03 vì các capability không có mẫu chính thức, đối chiếu chỉ số, lỗi đặc trưng và staging vẫn mở.

## P7-W04 — giao diện tự kiểm tra đầu vào Pylinac — lát cắt cục bộ — 2026-09-15

- Các trang Pylinac chuyên biệt nay gọi kiểm tra dữ liệu ngay sau khi tải tệp; tệp mới chỉ được báo là sẵn sàng sau khi máy chủ trả trạng thái `VALID`. Nếu kiểm tra thất bại, thao tác phân tích không bị coi là đã sẵn sàng và thông báo tiếng Việt được giữ nguyên.
- Trình xem kết quả dùng lại một bảng nhỏ “Kiểm tra đầu vào” cho các tệp đang chọn. Tệp đã có trạng thái `UPLOADED`, `WARNING` hoặc `INVALID` có nút kiểm tra lại ngay tại trang; tệp `VALID` hiện rõ là hợp lệ. Người dùng không cần quay về kho lưu trữ và giao diện không hiển thị mã nội bộ.
- Áp dụng cho các nhóm Picket Fence, Starshot, Winston–Lutz, Winston–Lutz nhiều bi, VMAT, Field Analysis, CatPhan, ACR, Cheese/Quart/Helios, Log Analyzer, Nuclear, Contrib và Planar Imaging; bài hiệu chuẩn không có tệp nên không hiện bảng này.
- Kiểm tra kiểu, lint, **12/12 tệp và 40/40 kiểm thử giao diện**, cùng bản dựng sản xuất đạt. Đây là lát cắt UX local; cần kiểm thử trình duyệt trên staging với tệp hợp lệ và tệp lỗi, sau đó mới đưa vào P07-VERIFY/HANDOFF. P7 vẫn mở.

## P7-W04 — đối chiếu Winston–Lutz nhiều bi theo từng ảnh — lát cắt cục bộ — 2026-09-16

- Trình xem kết quả Pylinac nay nhận một hàm hiển thị chi tiết theo đúng lượt đang xem. Khi mở kết quả Winston–Lutz nhiều bi, giao diện hiển thị từng ảnh, ba góc máy, khoảng cách trường–bi của từng bi và sai lệch xoay bàn.
- Bảng lấy trực tiếp `image_details` và `bb_arrangement` từ kết quả Pylinac đã lưu; giao diện không tính lại chỉ số, không thay dấu thiếu bằng số 0 và không tự kết luận Đạt/Cảnh báo/Không đạt.
- Tên tệp kỹ thuật, mã lượt chạy và mã nội bộ không xuất hiện trong bảng; người dùng chỉ thấy “Ảnh 1”, “Ảnh 2”… và tên bi do họ đặt trong cấu hình.
- Kiểm thử giao diện `src/pages/MachineQAPage.test.tsx` đạt **8/8**, gồm ca mở bảng nhiều bi và xác nhận không rò rỉ tên tệp. Kiểm tra kiểu, lint và bản dựng tiếp tục được chạy sau thay đổi.
- Đây là lát cắt trình xem cục bộ, chưa đóng P7-W04. Còn kiểm chứng staging, ROI chuyên biệt, ánh xạ thao tác theo từng ảnh và đối chiếu với bộ ảnh commissioning được phê duyệt.

## P7-W04 — triển khai bảng Winston–Lutz nhiều bi lên staging — 2026-09-16

- Sau khi đồng bộ mốc dựng lại cho cả ba dịch vụ, API, tiến trình nền và giao diện staging cùng phục vụ mã `91519002e3a18fcfe4046d944826c40fc60cf708` với lược đồ `20260914_0023`.
- Bộ xác minh công khai đạt **16/16**: health/readiness/version, OpenAPI, biên giới xác thực, chỉ báo gói giao diện và dấu hiệu nguồn đều đạt. Bằng chứng: `docs/evidence/p7-staging-wlmt-detail-deployment-20260916.json`.
- Đây là bằng chứng triển khai và parity; chưa chạy phân tích Winston–Lutz nhiều bi bằng bộ ảnh commissioning trên staging, nên chưa đóng P7-W04 hoặc P7-VERIFY/HANDOFF. Không có thao tác tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-W04 — trình xem nhóm chỉ số Pylinac — lát cắt cục bộ — 2026-09-16

- Trình xem kết quả dùng chung nay hiển thị các nhóm chỉ số lồng nhau do Pylinac trả về dưới dạng các nhóm và dòng dễ đọc, áp dụng cho CatPhan, ACR, VMAT, biên dạng, hạt nhân, ảnh phẳng và các bài tương tự.
- Tên tệp, mã hồ sơ, mã lượt chạy, mã đối tượng, mã bệnh nhân và đường dẫn bị loại khỏi giao diện. Không hiển thị JSON, không tính lại chỉ số và không thay đổi kết quả gốc đã lưu; Winston–Lutz nhiều bi vẫn dùng bảng chuyên biệt theo từng ảnh/bi để tránh hiển thị trùng.
- Kiểm thử giao diện `src/pages/MachineQAPage.test.tsx` đạt **9/9**; toàn bộ giao diện đạt **58/58**, kiểm tra kiểu, lint và bản dựng sản xuất đạt. Bằng chứng: [trình xem nhóm chỉ số Pylinac](docs/evidence/p7-local-structured-result-viewer-20260916.md).
- Đây là lát cắt hiển thị local; ROI chuyên biệt, ánh xạ tọa độ đa ảnh, fixture commissioning, staging tương tác và VERIFY/HANDOFF P7 vẫn mở. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-W03 — ma trận độ phủ bộ mẫu Pylinac — lát cắt cục bộ — 2026-09-16

- Registry đã có trạng thái bằng chứng bắt buộc cho toàn bộ **63 capability** Pylinac đang khóa: **37 bộ mẫu chính thức**, **13 bộ mẫu tổng hợp kiểm hợp đồng** và **13 mục cần commissioning**. Mỗi mục đều có tên tham chiếu và ghi chú giới hạn; không dùng bộ mẫu tổng hợp để tuyên bố đã nghiệm thu.
- Phép đối chiếu registry–ma trận phát hiện được cả mục thiếu và mục thừa; kiểm thử `tests/test_pylinac_registry.py` đạt **8/8**, Ruff đạt trên ma trận, registry và kiểm thử. Bằng chứng: [ma trận độ phủ bộ mẫu Pylinac](docs/evidence/p7-local-fixture-coverage-matrix-20260916.md).
- Đây là cổng quản lý độ phủ và truy nguyên kiểm thử. Các bộ tệp CatPhan 700, ACR, CIRS 062M, GE Helios, Trajectory Log 3/4, số đo hiệu chuẩn, fixture Nuclear/Contrib chuẩn và đối chiếu độc lập vẫn cần bổ sung; P7-W03, P7-W04 và VERIFY/HANDOFF P7 vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`; yêu cầu xóa vĩnh viễn đã được bỏ qua theo quyết định mới nhất.

## P7-W03/W04 — hiển thị trạng thái bộ mẫu trong danh mục QA — staging verified — 2026-09-16

- API tổ chức nay trả trạng thái bằng chứng, nhãn tham chiếu và ghi chú giới hạn cho từng capability Pylinac; giao diện danh mục QA hiển thị nhãn tiếng Việt tương ứng và tổng độ phủ theo ba nhóm. Toàn bộ bài vẫn xuất hiện; nhãn “cần bộ mẫu thẩm định” không khóa bài và không được hiểu là nghiệm thu lâm sàng.
- Kiểm thử API registry đạt **8/8**, giao diện đạt **58/58**, kiểm tra kiểu, lint và bản dựng sản xuất đạt. Commit `226b5d2` đã triển khai đồng bộ API và giao diện staging; bộ xác minh công khai exact-SHA đạt **16/16**, readiness giữ lược đồ `20260914_0023`. Bằng chứng: [kiểm tra trạng thái bộ mẫu trên staging](docs/evidence/p7-staging-fixture-status-deployment-20260916.json).
- Mốc này chỉ đóng thêm cổng minh bạch độ phủ. Fixture commissioning, đối chiếu độc lập, ROI chuyên biệt, ánh xạ tọa độ đa ảnh, kiểm chứng tương tác staging của từng nhóm và VERIFY/HANDOFF P7 vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-W03 — hồi quy engine Pylinac toàn bộ nhóm hiện có — đã kiểm tra local — 2026-09-18

- Tám nhóm kiểm thử gồm hiệu chuẩn, bài đóng góp, ma trận lỗi, Gamma, hạt nhân, ma trận tệp mẫu chính thức, API Pylinac và registry đã chạy với môi trường khóa.
- Kết quả **139/139 đạt**, không có lỗi; có bốn cảnh báo tương thích từ Starlette/httpx và cảnh báo nhiệt độ tham chiếu TRS-398 của Pylinac.
- Bằng chứng: [hồi quy Pylinac toàn bộ nhóm hiện có](docs/evidence/p7-local-pylinac-regression-20260918.md). Đây là cổng hồi quy local, chưa đóng P07-W03 vì fixture commissioning, đối chiếu độc lập, lỗi đặc trưng và staging xác thực vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-CONTRIB — kiểm tra tham số bài đóng góp — lát cắt cục bộ — 2026-09-18

- Bài Quasar Light/Rad Scaling nay kiểm tra phần trăm FWXM trong khoảng 1–100 và ngưỡng cạnh biên lớn hơn 0 trước khi gửi yêu cầu tới Pylinac.
- Bài Jaw Orthogonality không bị áp thêm tham số kỹ thuật không thuộc hợp đồng; người dùng chỉ chọn ảnh rồi xem kết quả do Pylinac trả về.
- Lỗi hiển thị ngay bằng tiếng Việt và nút phân tích bị khóa trước khi gửi yêu cầu. Không có lượt chạy mới, không sửa lịch sử và không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong cổng này.
- Kiểm thử giao diện riêng đạt **5/5**, toàn bộ giao diện đạt **74/74**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Đây là `LOCAL_VERIFIED_SLICE` cho biên nhập liệu.
- P07-CONTRIB vẫn mở vì còn thiếu fixture ảnh chuẩn/commissioning, đối chiếu từng chỉ số, kiểm lỗi ảnh không phù hợp, kiểm chứng staging và nghiệm thu chuyên môn.

## P7-CONTRIB — parity triển khai staging — 2026-09-18

- API, giao diện và tiến trình nền staging đã dựng thành công cùng commit `8d3ee7d3ff83820447b0962de14f1e2270404f5c` sau khi thêm cổng kiểm tra tham số Quasar và Jaw.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều đạt, readiness giữ lược đồ `20260914_0023`, biên xác thực không bị mở và gói giao diện mới có mặt.
- Bằng chứng: [kiểm tra parity bài đóng góp trên staging](docs/evidence/p7-staging-contrib-form-validation-20260918.json). Đây là bằng chứng triển khai và hợp đồng giao diện, không phải chạy hai bài bằng ảnh chuẩn/commissioning; P07-CONTRIB vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-NUCLEAR — kiểm tra tham số chín bài hạt nhân — lát cắt cục bộ — 2026-09-18

- Các bài tốc độ đếm, độ đồng nhất, độ phân giải, độ nhạy, tâm quay và tương phản nay kiểm tra đúng trường số theo từng loại bài trước khi gửi Pylinac.
- Cổng kiểm tra bao phủ tỉ lệ vùng nhìn/ngưỡng trong miền hợp lệ, số khung nguyên và đúng thứ tự, bốn bề rộng vạch, sáu đường kính và sáu góc cầu, cửa sổ/số lát tìm kiếm, hoạt độ dương và đồng vị không trống.
- Lỗi hiển thị ngay bằng tiếng Việt và nút phân tích bị khóa trước khi gửi yêu cầu tới Pylinac. Không có lượt chạy mới, không sửa lịch sử và không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong cổng này.
- Kiểm thử giao diện riêng đạt **7/7**, toàn bộ giao diện đạt **73/73**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Đây là `LOCAL_VERIFIED_SLICE` cho biên nhập liệu.
- P07-NUCLEAR vẫn mở vì còn thiếu fixture DICOM chuẩn/commissioning, đối chiếu từng lớp kết quả, kiểm lỗi đặc trưng, kiểm chứng staging và nghiệm thu chuyên môn.

## P7-NUCLEAR — parity triển khai staging — 2026-09-18

- API, giao diện và tiến trình nền staging đã dựng thành công cùng commit `7ddedcbcaa072024118fbca4bc128658cb4e3a17` sau khi thêm cổng kiểm tra tham số chín bài hạt nhân.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều đạt, readiness giữ lược đồ `20260914_0023`, biên xác thực không bị mở và gói giao diện mới có mặt.
- Bằng chứng: [kiểm tra parity bài hạt nhân trên staging](docs/evidence/p7-staging-nuclear-form-validation-20260918.json). Đây là bằng chứng triển khai và hợp đồng giao diện, không phải chạy chín bài bằng bộ ảnh chuẩn/commissioning; P07-NUCLEAR vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-PLANAR — kiểm tra tham số biểu mẫu ảnh phẳng — lát cắt cục bộ — 2026-09-18

- Mười chín biến thể ảnh phẳng dùng cổng kiểm tra chung cho ngưỡng tương phản thấp, ngưỡng tương phản cao khi bài áp dụng, điều chỉnh tâm/góc và hệ số vùng/thang đo.
- Tâm ngang và tâm dọc có thể để tự động; nếu người dùng nhập thủ công thì phải nhập đủ cả hai và đều là số hữu hạn. Bài chụp tuyến vú không bị kiểm tra một ngưỡng tương phản cao không dùng trong hợp đồng của bài.
- Lỗi hiển thị ngay bằng tiếng Việt và nút phân tích bị khóa trước khi gửi yêu cầu tới Pylinac. Không có lượt chạy mới, không sửa lịch sử và không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong cổng này.
- Kiểm thử giao diện riêng đạt **5/5**, toàn bộ giao diện đạt **72/72**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Đây là `LOCAL_VERIFIED_SLICE` cho biên nhập liệu.
- P07-PLANAR vẫn mở vì còn thiếu fixture chuẩn/commissioning, đối chiếu từng mô-đun kết quả, kiểm lỗi đặc trưng, kiểm chứng staging và nghiệm thu chuyên môn.

## P7-PLANAR — parity triển khai staging — 2026-09-18

- API, giao diện và tiến trình nền staging đã dựng thành công cùng commit `27958d95309eb3a0d9d408dcefa35d2f774b655e` sau khi thêm cổng kiểm tra tham số 19 bài ảnh phẳng.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều đạt, readiness giữ lược đồ `20260914_0023`, biên xác thực không bị mở và gói giao diện mới có mặt.
- Bằng chứng: [kiểm tra parity ảnh phẳng trên staging](docs/evidence/p7-staging-planar-form-validation-20260918.json). Đây là bằng chứng triển khai và hợp đồng giao diện, không phải chạy 19 bài bằng bộ ảnh chuẩn/commissioning; P07-PLANAR vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-CHEESE/P7-HELIOS/P7-QUART — kiểm tra tham số biểu mẫu — lát cắt cục bộ — 2026-09-18

- Biểu mẫu TomoCheese, CIRS 062M, GE Helios CT hằng ngày, Quart DVT và Quart HyperSight dùng cổng kiểm tra chung cho lát gốc tùy chọn, điều chỉnh ngang/dọc/góc và các hệ số vùng/thang đo.
- Hai bài Cheese chỉ kiểm tra mật độ tham chiếu ROI khi người dùng nhập; bài Helios không bị áp thêm trường Quart; hai bài Quart kiểm tra dung sai HU, dung sai thang đo, dung sai độ dày, ngưỡng CNR và dịch lát tìm góc, trong đó dịch lát được phép âm.
- Lỗi hiển thị ngay bằng tiếng Việt và nút phân tích bị khóa trước khi gửi yêu cầu tới Pylinac. Không có lượt chạy mới, không sửa lịch sử và không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong cổng này.
- Kiểm thử giao diện riêng đạt **6/6**, toàn bộ giao diện đạt **71/71**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Đây là `LOCAL_VERIFIED_SLICE` cho biên nhập liệu.
- Các nhóm vẫn mở vì môi trường hiện tại còn thiếu fixture Cheese CIRS 062M/GE Helios/Quart được phê duyệt, đối chiếu từng mô-đun, kiểm lỗi đặc trưng, kiểm chứng staging và nghiệm thu chuyên môn.

## P7-CHEESE/P7-HELIOS/P7-QUART — parity triển khai staging — 2026-09-18

- API, giao diện và tiến trình nền staging đã dựng thành công cùng commit `71aaf91ce2c1ea6cf9b035eb403c1ff08fae5476` sau khi thêm cổng kiểm tra tham số phantom.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều đạt, readiness giữ lược đồ `20260914_0023`, biên xác thực không bị mở và gói giao diện mới có mặt.
- Bằng chứng: [kiểm tra parity nhóm phantom trên staging](docs/evidence/p7-staging-ct-phantom-form-validation-20260918.json). Đây là bằng chứng triển khai và hợp đồng giao diện, không phải chạy phantom bằng bộ ảnh chuẩn/commissioning; các gói P07 tương ứng vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-CAL/W04 — kiểm tra biểu mẫu hiệu chuẩn và sửa TRS-398 electron — đã kiểm tra cục bộ — 2026-09-16

- Đã bổ sung lớp kiểm tra giao diện riêng cho năm bài hiệu chuẩn TG-51/TRS-398. Biểu mẫu yêu cầu các thông tin truy nguyên của phép đo, kiểm tra số hữu hạn, miền tối thiểu và từng phần tử trong các trường nhiều số đọc; lỗi hiển thị bằng tiếng Việt trước khi gửi yêu cầu, không còn âm thầm bỏ qua phần nhập sai.
- Phát hiện và sửa lỗi ánh xạ ở bài TRS-398 electron: giao diện trước đây dùng tên trường `p_elec`, trong khi hợp đồng Pylinac/adapter yêu cầu `k_elec`; hai biến thể TRS-398 nay dùng đúng hệ số `k_elec`. Bộ gom tham số cũng chỉ gửi hệ số phù hợp với từng họ quy trình, không gửi hệ số ẩn còn lại làm tham số thừa. Tên các bài hiệu chuẩn cũng đã đổi sang nhãn nghiệp vụ tiếng Việt.
- Kiểm thử giao diện đạt **60/60**, kiểm tra kiểu đạt, lint đạt và bản dựng sản xuất đạt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Đây là `LOCAL_VERIFIED_SLICE` cho biên nhập liệu và ánh xạ giao diện. P07-CAL vẫn mở vì chưa có số đo chuẩn/commissioning, đối chiếu độc lập, kiểm lỗi miền vật lý và kiểm chứng staging; không được dùng lát cắt này để tuyên bố hiệu chuẩn lâm sàng.

## P7-WL/WLMT — chặn tham số hình học sai trước khi gọi Pylinac — lát cắt cục bộ — 2026-09-16

- Biểu mẫu Winston–Lutz và Winston–Lutz nhiều bi đã có lớp kiểm tra dùng chung cho khoảng cách nguồn–ảnh, mật độ điểm ảnh, kích thước bi, dung sai, khoảng cách nhận diện và các góc tham chiếu. Giá trị trống, không phải số, hoặc nằm ngoài miền cho phép hiện được báo bằng tiếng Việt và nút phân tích bị khóa.
- Bảng cấu hình nhiều bi kiểm tra tên bi, số lượng tối đa, độ lệch không gian, kích thước bi và bán kính trường của từng dòng. Bảng góc nhập tay kiểm tra đủ ba góc cho đúng số ảnh trước khi tạo yêu cầu; người dùng chỉ thấy số thứ tự ảnh, không thấy tên tệp kỹ thuật.
- Adapter máy chủ nay chặn kích thước bi Winston–Lutz bằng 0 trước khi gọi Pylinac, nhất quán với kiểm tra nhiều bi. Không có lượt chạy mới, không sửa lịch sử và không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong cổng này.
- Kiểm thử riêng giao diện đạt **13/13**, toàn bộ giao diện đạt **62/62**; kiểm thử máy chủ `test_pylinac_qa.py` đạt, Ruff và kiểm tra kiểu đạt. Đây là `LOCAL_VERIFIED_SLICE` cho biên nhập liệu, chưa đóng P07-WL/P07-WLMT vì còn fixture commissioning, đối chiếu độc lập, ánh xạ tọa độ theo từng ảnh và kiểm chứng tương tác staging.

## P7-LOG — kiểm tra dung sai Gamma fluence ở biểu mẫu — lát cắt cục bộ — 2026-09-16

- Khi người dùng bật “Tạo bản đồ Gamma fluence” trong bài Dynalog hoặc Trajectory Log, giao diện bắt buộc dung sai liều và dung sai khoảng cách là số hữu hạn lớn hơn 0. Khi tắt Gamma, hai trường không bị bắt buộc và không được gửi xuống máy chủ.
- Lỗi được hiển thị ngay dưới vùng tham số và nút phân tích bị khóa; quy tắc máy chủ hiện có tiếp tục là lớp bảo vệ cuối cùng trước khi gọi Pylinac. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong cổng này.
- Kiểm thử giao diện riêng đạt **14/14**, kiểm tra kiểu, lint và bản dựng sản xuất đạt; kiểm thử máy chủ Pylinac liên quan tiếp tục đạt. Đây là `LOCAL_VERIFIED_SLICE`, chưa đóng P07-LOG vì còn fixture Trajectory Log 3/4, kiểm tra Gamma log ổn định, fixture commissioning, đối chiếu độc lập và staging.

## P7-ACR — kiểm tra tham số biểu mẫu CT/MRI — lát cắt cục bộ — 2026-09-16

- Ba biểu mẫu ACR CT 464, ACR MRI lớn và ACR MRI vừa nay kiểm tra trước lát gốc tùy chọn phải là số nguyên không âm, các điều chỉnh ngang/dọc/góc phải là số hợp lệ, hệ số kích thước vùng và hệ số thang đo phải không âm.
- Khi chọn ACR MRI, số lần vọng phải là số nguyên từ 1 trở lên nếu được nhập; ngưỡng nhìn thấy tương phản thấp và hệ số kiểm tra hợp lý phải là số không âm. Khi chọn ACR CT, các trường riêng của MRI không tham gia kiểm tra và không ảnh hưởng tới khả năng bắt đầu phân tích.
- Lỗi được hiển thị ngay bằng tiếng Việt và nút phân tích bị khóa trước khi gửi yêu cầu tới Pylinac. Không có lượt chạy mới, không sửa lịch sử và không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong cổng này.
- Kiểm thử giao diện riêng đạt **5/5**, toàn bộ giao diện đạt **70/70**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Đây là `LOCAL_VERIFIED_SLICE` cho biên nhập liệu, chưa phải kiểm chứng kết quả ACR.
- ACR vẫn mở vì môi trường Pylinac hiện chưa có fixture ACR được phê duyệt; còn thiếu fixture chuẩn/commissioning, đối chiếu từng mô-đun kết quả, kiểm lỗi đặc trưng, kiểm chứng staging và nghiệm thu chuyên môn.

## P7-ACR — parity triển khai staging — 2026-09-18

- API, giao diện và tiến trình nền staging đã dựng thành công cùng commit `7df6c1857edb1aa8066cae6e69309f8ef91f323d` sau khi thêm cổng kiểm tra tham số ACR.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều đạt, readiness giữ lược đồ `20260914_0023`, biên xác thực không bị mở và gói giao diện mới có mặt.
- Bằng chứng: [kiểm tra parity ACR trên staging](docs/evidence/p7-staging-acr-form-validation-20260918.json). Đây là bằng chứng triển khai và hợp đồng giao diện, không phải chạy ACR bằng bộ ảnh chuẩn/commissioning; P07-ACR vẫn mở.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
## P7-W04 — chọn tâm phantom trực tiếp theo thang đo DICOM — đã kiểm tra local — 2026-09-18

- Vùng xem trước dùng chung cho CatPhan, ACR, TomoCheese, CIRS 062M, GE Helios và Quart nay hỗ trợ chọn/kéo tâm phantom trên ảnh thay vì chỉ nhập số. Điểm được chọn được quy đổi từ tâm ảnh sang điều chỉnh ngang/dọc theo milimét để gửi đúng tham số mà Pylinac công khai hỗ trợ.
- API thông tin xem trước chỉ trả số ảnh, chiều rộng, chiều cao và thang đo điểm ảnh; không trả thẻ DICOM, tên tệp, đường dẫn kho hoặc mã nội bộ. Nếu không đọc được thang đo vật lý, giao diện không suy diễn tọa độ và giữ ô nhập điều chỉnh bằng tay.
- Pylinac tiếp tục là engine duy nhất. RT-CONNECT chỉ phụ trách chọn điểm, quy đổi tọa độ, kiểm tra đầu vào và truyền tham số; không có thuật toán phân tích ảnh thay thế.
- Kiểm thử ánh xạ tâm, giới hạn điểm ngoài mép và trường hợp thiếu thang đo đạt; kiểm tra API artifact, toàn bộ giao diện đạt **74/74**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Bằng chứng: [chọn tâm phantom trực tiếp](docs/evidence/p7-local-visual-phantom-center-adjustment-20260918.md).
- Đây là `LOCAL_VERIFIED_SLICE`, chưa đóng P7-W04. Còn cần fixture phantom được phê duyệt, tương tác có đăng nhập trên staging, đối chiếu độc lập, kiểm tra các ROI chuyên biệt và nghiệm thu chuyên môn. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P7-W04 — parity triển khai chọn tâm phantom trên staging — đã kiểm tra — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại từ cùng commit `b49aaf3363480c0c6468c7f53eb8038b86b31bda`.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều `200`, lược đồ `20260914_0023`, tuyến thông tin xem trước và gói giao diện đều hiện diện.
- Bằng chứng: [parity chọn tâm phantom trên staging](docs/evidence/p7-staging-visual-phantom-center-adjustment-20260918.json). Đây là kiểm tra triển khai và biên công khai không cần đăng nhập, chưa phải chạy thao tác chọn tâm với fixture phantom được phê duyệt.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`. P7-W04 vẫn mở các cổng tương tác có đăng nhập, fixture đại diện, đối chiếu độc lập và nghiệm thu chuyên môn.

## P8-W02 — kiểm tra tham số PSQA ngay trên biểu mẫu — đã kiểm tra local — 2026-09-18

- Biểu mẫu PSQA đã có lớp kiểm tra dùng chung cho chênh lệch liều, DTA, ngưỡng liều thấp, ngưỡng đạt, giới hạn Gamma, số khoảng biểu đồ và hệ số tinh chỉnh một chiều. Dữ liệu không hữu hạn, bằng 0/âm, ngoài miền hoặc không phải số nguyên ở trường yêu cầu số nguyên đều bị báo ngay bằng tiếng Việt.
- Phân tích Gamma ba chiều mới bị chặn rõ ràng vì Pylinac hiện chỉ được dùng cho Gamma một chiều và hai chiều; kết quả Gamma ba chiều cũ vẫn giữ đúng quy tắc chỉ xem lại ở phần lịch sử.
- Khi còn lỗi, nút bắt đầu phân tích bị khóa nên không tạo tác vụ mới, không gọi máy chủ và không làm thay đổi lịch sử. Các trường “Chênh lệch liều (%)” và “DTA (mm)” vẫn là tham số người dùng nhập, được chuyển nguyên vẹn cho hợp đồng Pylinac sau khi hợp lệ.
- Kiểm thử riêng đạt **7/7**, toàn bộ giao diện đạt **78/78**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Bằng chứng: [kiểm tra tham số PSQA](docs/evidence/p8-local-psqa-configuration-validation-20260918.md).
- Đây là `LOCAL_VERIFIED_SLICE`, chưa đóng P08-W02. Còn cần chạy Gamma thật trên staging bằng dữ liệu hợp lệ, kiểm tra hàng đợi/hủy/thử lại và VERIFY/HANDOFF P8. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P8-W02 — parity triển khai cổng tham số PSQA trên staging — đã kiểm tra — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại từ cùng commit `e9f1b9a011b12c461f3d14b4bc060d29655f59d3`.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều `200`, lược đồ `20260914_0023` và gói giao diện mới đều hiện diện.
- Bằng chứng: [parity cổng tham số PSQA trên staging](docs/evidence/p8-staging-psqa-configuration-validation-20260918.json). Đây là kiểm tra triển khai và biên công khai chưa cần đăng nhập, chưa phải chạy Gamma thật với dữ liệu liều.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`. P08-W02 vẫn mở phần chạy Gamma thật, ma trận lỗi hàng đợi và VERIFY/HANDOFF.

## P9-W01 — trình biên soạn báo cáo theo ngôn ngữ nghiệp vụ — kiểm tra cục bộ — 2026-09-18

- Màn hình trình biên soạn báo cáo đã được thu gọn theo nghiệp vụ bác sĩ/kỹ sư: chọn bài kiểm tra và kết quả bằng tên hiển thị, chỉnh tiêu đề, nhãn, nội dung ghi chú, thứ tự và trạng thái hiển thị của từng phần.
- Đã loại khỏi giao diện mã báo cáo, mã nguồn, mã lần chạy, mã mẫu, bản chụp cấu hình và lựa chọn xuất JSON. Các trạng thái kết quả và định dạng tệp xuất được hiển thị thuần tiếng Việt; mã nội bộ chỉ còn ở lớp giao tiếp dữ liệu cần thiết.
- Không có thao tác tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong lát cắt này.
- Kiểm thử riêng đạt **2/2**, toàn bộ giao diện đạt **16/16 tệp và 80/80 phép thử**, kiểm tra kiểu, quy tắc mã nguồn, bản dựng sản phẩm và kiểm tra khoảng trắng đều đạt. Bằng chứng: [trình biên soạn báo cáo theo ngôn ngữ nghiệp vụ](docs/evidence/p9-local-report-builder-user-facing-20260918.md).
- Đây là `LOCAL_VERIFIED_SLICE`; P09-W01 vẫn mở vì còn cần dựng PDF/hình chú thích thực, kiểm tra bản chụp và xuất lặp, kiểm tra có đăng nhập trên staging, VERIFY và HANDOFF của P9.

## P9-W01 — parity triển khai trình biên soạn báo cáo trên staging — đã kiểm tra — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại cùng commit `67184c4698af0994084816c9422e6c7ce7cb0285`.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều `200`, lược đồ `20260914_0023`, tuyến thành viên/lời mời vẫn giữ biên xác thực và giao diện phục vụ đúng phiên bản.
- Bằng chứng: [parity trình biên soạn báo cáo trên staging](docs/evidence/p9-staging-report-builder-ux-20260918.json). Đây là kiểm tra triển khai và biên công khai, chưa phải phiên kiểm thử có đăng nhập để lưu báo cáo, mở lịch sử hoặc xuất PDF thật.
- P09-W01 vẫn mở các cổng bản chụp, trình dựng PDF/hình chú thích, xuất lặp và VERIFY/HANDOFF. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W02/P09-W03 — renderer báo cáo không lộ thông tin kỹ thuật — kiểm tra cục bộ — 2026-09-18

- Renderer PDF/CSV nay dùng nhãn nghiệp vụ tiếng Việt, đưa ghi chú người dùng vào tài liệu và loại bỏ mã hồ sơ, mã lần chạy, bản chụp cấu hình, mã băm và loại phần kỹ thuật khỏi nội dung dành cho người dùng. PDF có thể lấy lớp phủ ảnh dẫn xuất từ kết quả Pylinac và nhúng an toàn vào trang đầu.
- Phần ẩn không được render; phần chỉ số/cảnh báo/thông tin bài kiểm tra có tóm tắt an toàn. Font Unicode tiếng Việt tiếp tục được nhúng trong PDF.
- Kiểm thử `test_reports.py` đạt **10/10**, gồm kiểm tra PDF nhiều trang và xuất PDF có lớp phủ Pylinac; Ruff và mypy cho phần renderer đạt. Bằng chứng: [renderer báo cáo không lộ thông tin kỹ thuật](docs/evidence/p9-local-report-renderer-user-facing-20260918.md).
- Đây là `LOCAL_VERIFIED_SLICE`; còn thiếu ảnh PNG, bảng nghiệp vụ nhiều trang, đối chiếu preview–PDF, kiểm tra có đăng nhập trên staging và VERIFY/HANDOFF. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W02/P09-W03 — parity triển khai renderer báo cáo trên staging — đã kiểm tra — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại cùng commit `4a7988451f7b5e51445577eee86b2b7e1a4a528f`.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều `200`, lược đồ `20260914_0023`, biên xác thực thành viên/lời mời vẫn đúng và giao diện phục vụ đúng phiên bản.
- Bằng chứng: [parity renderer báo cáo trên staging](docs/evidence/p9-staging-report-renderer-20260918.json). Đây là kiểm tra triển khai và biên công khai, chưa phải phiên có đăng nhập để xuất tài liệu thật.
- P09-W02/P09-W03 vẫn mở các cổng ảnh phân tích thật, bảng nhiều trang, đối chiếu xem trước–PDF và VERIFY/HANDOFF. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W03 — PDF nhiều trang trên staging — đã kiểm tra parity — 2026-09-18

- Renderer nhiều trang đã được đưa lên cùng commit `1324aee08bc9479d4600b0d4ba5fff784a825112` cho API, giao diện và tiến trình nền staging.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đạt, lược đồ `20260914_0023`, giao diện và API cùng phục vụ đúng commit.
- Bằng chứng: [parity PDF nhiều trang trên staging](docs/evidence/p9-staging-report-renderer-pagination-20260918.json). Đây mới là source/runtime/public-boundary evidence; chưa phải kiểm thử có đăng nhập để xuất PDF từ hồ sơ thật.
- P09-W03 vẫn mở phần ảnh PNG, bảng nghiệp vụ dài và đối chiếu trực quan; PDF đã có lớp phủ ở cổng cục bộ nhưng chưa triển khai lát cắt này lên staging. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W01 — đưa kết quả Pylinac vào nguồn báo cáo — kiểm tra cục bộ — 2026-09-18

- Trình biên soạn báo cáo nay có thể chọn trực tiếp một lượt phân tích Pylinac theo tên bài và lần phân tích. Máy chủ chụp lại kết quả, cảnh báo, lỗi, trạng thái đánh giá và liên kết lớp phủ trong đúng phạm vi đơn vị.
- Giao diện không hiển thị mã hồ sơ, mã lượt chạy hoặc dữ liệu JSON; người dùng chỉ thấy tên bài, số lần phân tích và trạng thái bằng tiếng Việt. Pylinac vẫn là engine duy nhất; RT-CONNECT chỉ quản lý lựa chọn, kiểm tra phạm vi, snapshot và báo cáo.
- Kiểm thử tích hợp tạo lượt hiệu chuẩn Pylinac tổng hợp rồi dùng lượt đó làm nguồn báo cáo đạt **10/10**; toàn bộ giao diện đạt **16/16 tệp và 80/80 phép thử**, Ruff và mypy phần báo cáo đạt. Bằng chứng: [nguồn Pylinac cho báo cáo](docs/evidence/p9-local-pylinac-report-source-20260918.md).
- Lát cắt này chưa nhúng lớp phủ vào PDF/PNG, chưa kiểm thử có đăng nhập trên staging và chưa đối chiếu xem trước–tài liệu xuất. P09-W01/P09-W03 vẫn mở. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W01 — nguồn Pylinac cho báo cáo trên staging — đã kiểm tra parity — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại cùng commit `f70fab80de566010b3304ae2f88f301379bed815`.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều `200`, lược đồ `20260914_0023`, tuyến thành viên/lời mời vẫn giữ đúng biên xác thực và giao diện phục vụ đúng gói mới.
- Bằng chứng: [parity nguồn Pylinac cho báo cáo trên staging](docs/evidence/p9-staging-pylinac-report-source-20260918.json). Đây là bằng chứng nguồn/runtime/biên công khai; chưa phải phiên có đăng nhập để tạo báo cáo từ một lượt Pylinac thật.
- P09-W01 vẫn mở phần kiểm thử có đăng nhập, snapshot/hạ tầng xuất thực và VERIFY/HANDOFF; P09-W03 vẫn mở phần lấy lớp phủ vào PDF/PNG. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W03 — nhúng lớp phủ Pylinac vào PDF trên staging — đã kiểm tra parity — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại cùng commit `ab641714dbf82ad16ea2279620bb6edf57798311`.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều `200`, lược đồ `20260914_0023`, giao diện phục vụ đúng gói mới và biên thành viên/lời mời vẫn yêu cầu xác thực.
- Bằng chứng: [parity nhúng lớp phủ Pylinac vào PDF trên staging](docs/evidence/p9-staging-pylinac-overlay-pdf-20260918.json). Đây là bằng chứng triển khai và biên công khai; chưa phải phiên có đăng nhập để tạo lượt Pylinac và xuất PDF trên dữ liệu staging thật.
- PDF đã có đường đi cục bộ được kiểm thử với ảnh PNG hợp lệ; PNG xuất, bảng nghiệp vụ dài, đối chiếu xem trước–PDF và VERIFY/HANDOFF P9 vẫn mở. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W03 — nhúng lớp phủ Pylinac vào PDF và PNG — kiểm tra cục bộ — 2026-09-18

- Renderer báo cáo đã nâng lên `report-renderer-0.4`: cùng một tệp lớp phủ Pylinac được giải mã an toàn và đưa vào cả PDF lẫn PNG; PDF tiếp tục đặt ảnh ở trang đầu, PNG đặt ảnh trong vùng phân tích của bản xem trước/xuất nhẹ.
- Lượt xuất PNG kiểm tra đúng phạm vi đơn vị, dùng lại cơ chế cảnh báo `REPORT_OVERLAY_UNAVAILABLE` khi ảnh thiếu hoặc không đọc được, và không làm thay đổi bản chụp báo cáo bất biến. Không có đường dẫn tệp, mã nội bộ hoặc dữ liệu JSON trong tài liệu người dùng.
- Kiểm thử `test_reports.py` và `test_pylinac_qa.py` đạt **51/51**, riêng `test_reports.py` đạt **11/11**; Ruff, mypy phần báo cáo và kiểm tra khoảng trắng đều đạt. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.
- Đây là `LOCAL_VERIFIED_SLICE`; sau khi triển khai cần tạo lại bằng chứng parity staging theo đúng toàn bộ mã nguồn, rồi mới kiểm tra có đăng nhập để đối chiếu xem trước–PDF/PNG và đóng P09-W03. Bảng nghiệp vụ nhiều trang, xem trước bằng chính renderer xuất và VERIFY/HANDOFF P9 vẫn mở.

## P9-W03 — nhúng lớp phủ Pylinac vào PDF và PNG trên staging — đã kiểm tra parity — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại cùng commit `653d399e856a2901bd178fd18182924ffb03edf9`.
- Bộ xác minh công khai exact-SHA đạt **16/16**; health/readiness đều `200`, readiness giữ lược đồ `20260914_0023`, gói giao diện có mặt và các tuyến thành viên/lời mời vẫn yêu cầu xác thực.
- Bằng chứng: [parity lớp phủ Pylinac PDF/PNG trên staging](docs/evidence/p9-staging-pylinac-overlay-png-20260918.json). Đây là bằng chứng triển khai và biên công khai; chưa phải phiên có đăng nhập để tạo lượt Pylinac, mở trình biên soạn và xuất tài liệu trên dữ liệu staging thật.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`. P09-W03 vẫn mở bảng nghiệp vụ nhiều trang, đối chiếu xem trước–PDF/PNG, kiểm thử có đăng nhập và VERIFY/HANDOFF P9.

## P9-W03 — xem trước dùng cùng renderer với tệp xuất — kiểm tra cục bộ — 2026-09-18

- API đã có tuyến xem trước cho bản chỉnh sửa đã lưu; tuyến này lấy cùng bản chụp bất biến và gọi cùng `render_report` với đường xuất PNG/PDF. Giao diện hiển thị ảnh PNG do tuyến này trả về, không còn dựng một bản xem trước mô tả riêng cho bản đã lưu.
- Lớp phủ Pylinac được lấy theo đúng phạm vi đơn vị và dùng lại trong xem trước; bản chỉnh sửa chưa lưu được ghi chú rõ là cần lưu bản mới trước khi cập nhật ảnh.
- Kiểm thử `test_reports.py` và `test_pylinac_qa.py` đạt **51/51**, riêng `test_reports.py` đạt **11/11**; toàn bộ giao diện đạt **16 tệp và 81 phép thử**, kiểm tra kiểu, lint và bản dựng sản phẩm đạt. Bằng chứng: [xem trước cùng renderer](docs/evidence/p9-local-preview-renderer-20260918.md).
- Đây là `LOCAL_VERIFIED_SLICE`; chưa triển khai lát cắt này lên staging. Còn mở kiểm thử có đăng nhập, đối chiếu trực quan xem trước–PDF/PNG, bảng nghiệp vụ nhiều trang và VERIFY/HANDOFF P9. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P9-W03 — xem trước dùng cùng renderer với tệp xuất trên staging — đã kiểm tra parity — 2026-09-18

- API, giao diện và tiến trình nền staging đã được dựng lại cùng commit đầy đủ `02ff4c57d097a132c5c7e16901b7f29c356a2217`.
- Bộ xác minh công khai exact-SHA đạt **16/16**: health/readiness `200`, lược đồ `20260914_0023`, tuyến xem trước có trong OpenAPI, giao diện có điều khiển xem trước và mã phiên bản đúng với commit triển khai.
- Bằng chứng: [parity xem trước dùng cùng renderer trên staging](docs/evidence/p9-staging-preview-renderer-20260918.json). Đây là bằng chứng triển khai, hợp đồng công khai và biên xác thực; chưa phải phiên có đăng nhập để mở bản báo cáo staging, xem ảnh thật hoặc tải PDF/PNG thật.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`. P09-W03 vẫn mở bảng nghiệp vụ nhiều trang, đối chiếu trực quan xem trước–PDF/PNG, kiểm thử có đăng nhập và VERIFY/HANDOFF.

## P9-W04 — xuất lặp theo bản chụp và khôi phục sau lỗi lưu — cục bộ và parity staging — 2026-09-18

- Hợp đồng xuất hiện hỗ trợ JSON, CSV, PDF và PNG; cùng khóa idempotency trong cùng bản chụp trả lại đúng công việc đã có, còn dùng lại khóa cho định dạng khác bị từ chối `EXPORT_IDEMPOTENCY_CONFLICT`.
- Tệp xuất được lưu theo bản chụp bất biến, tải lại trả đúng hàm băm/kích thước và tên tệp nghiệp vụ; lỗi ghi metadata được bù trừ tệp tạm để có thể thử lại an toàn. Lỗi dọn dẹp được phát tín hiệu đối soát thay vì mất im lặng.
- Ba kiểm thử riêng cho P9-W04 đã đạt; toàn bộ `test_reports.py` đạt **11/11**, gồm cả bốn định dạng, lặp idempotency, xung đột khóa, tải lại và hai nhánh lỗi lưu/dọn dẹp. Không có thao tác xóa vĩnh viễn nào trong lát cắt này.
- Lịch sử tệp của từng bản báo cáo đã có tuyến máy chủ theo đúng bản sửa đổi, phân trang theo phạm vi đơn vị, và giao diện hiển thị tên tệp nghiệp vụ cùng nút “Tải lại” để lấy liên kết mới. Kiểm thử giao diện đạt **16 tệp và 82 phép thử**; kiểm tra kiểu, lint và bản dựng đạt.
- Sau khi dựng lại cả API, web và tiến trình nền staging, bộ xác minh công khai exact-SHA đạt **16/16** với mã nguồn đầy đủ `829f7575d0560c84ffd5a9ec2971effb73394181`, lược đồ `20260914_0023`, health/readiness `200`, OpenAPI, biên xác thực và gói giao diện đúng phiên bản. Bằng chứng: [lịch sử tệp báo cáo trên staging](docs/evidence/p9-staging-export-history-20260918.json).
- Đây là `STAGING_PARITY_VERIFIED`, chưa phải nghiệm thu nghiệp vụ đầy đủ: bộ kiểm tra công khai chưa đăng nhập để mở một bản báo cáo thật, xem lịch sử tệp và bấm “Tải lại”. P09-W04 vẫn mở phần kiểm tra có đăng nhập, đối chiếu liên kết tải và VERIFY/HANDOFF. Việc lan truyền xóa vĩnh viễn được giữ ngoài phạm vi theo quyết định sản phẩm hiện tại; hồ sơ QA chỉ dùng lưu trữ/khôi phục khi cần.

## P8-W03 — hàng đợi và kết quả Gamma — kiểm tra cục bộ — 2026-09-18

- Bộ `apps/api/tests/test_gamma.py` đạt **15/15**, bao phủ phép tính một chiều/hai chiều, kiểm tra hình học và vùng so sánh, ngưỡng/độ bao phủ, giới hạn tài nguyên, trạng thái `QUEUED`/`CANCELLED`, hủy lặp an toàn và khóa lặp.
- Pylinac là engine duy nhất cho phép tính Gamma mới; Gamma ba chiều cũ vẫn chỉ đọc. Giao diện đã có tiến độ, nút hủy khi còn chờ, thử lại khi lỗi và bảng kết quả bằng tiếng Việt.
- Bằng chứng: [hàng đợi và kết quả Gamma cục bộ](docs/evidence/p8-local-gamma-queue-results-20260918.md).
- Đây là `LOCAL_VERIFIED_SLICE`; P08-W03 vẫn mở bước chạy thật trên staging với worker, retry/cancel, kết quả 1D/2D, lịch sử và ma trận lỗi. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P8-W03 — Gamma một chiều Pylinac trên staging — đã kiểm tra happy path — 2026-09-18

- Sau commit backend `b45d1ff39a23d1962ce2c5ed9562c3433cc0dc9b` và web `dafd4d3`, giao diện staging đã cho phép đúng luồng một chiều: chọn hai tệp số đo hợp lệ, không yêu cầu RTDOSE tham chiếu; hướng dẫn và nhãn đều dùng tiếng Việt nghiệp vụ, không lộ tên tệp JSON hay mã nội bộ.
- Trên hồ sơ tổng hợp `P6 Staging Upload Smoke`, một lượt chạy `PSQA_GAMMA` bằng Pylinac `gamma_1d` đã hoàn tất với kết luận **Đạt**, tỷ lệ đạt **100%**, **4/4** điểm đạt, **0** điểm không đạt, **0** điểm loại khỏi tính toán, độ bao phủ **1**, Gamma P95 **0**. Bảng vị trí một chiều và biểu đồ phân bố hiển thị trên trang; lịch sử ghi nhận lượt chạy hoàn tất.
- Bằng chứng: [Gamma một chiều Pylinac staging](docs/evidence/p8-staging-gamma-1d-pylinac-20260918.json). API `/ready` tại thời điểm kiểm tra trả `ready`.
- Cổng này chỉ xác nhận happy path 1D trên staging với dữ liệu tổng hợp. P08-W03 vẫn mở queue retry/cancel, lỗi worker/Redis, ma trận đầu vào không hợp lệ, đối chiếu độc lập và VERIFY/HANDOFF; không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## P8-W03 — Kiểm chứng thử lại Gamma trên staging — 2026-09-18

- Không thực hiện xóa vĩnh viễn và không chạm hồ sơ `dailyQA`; chỉ dùng dữ liệu tổng hợp trong case staging `P6 Staging Upload Smoke`.
- Trên candidate API `b45d1ff` và web `dafd4d3`, mở một lượt Gamma một chiều đã lỗi trong lịch sử rồi bấm `Phân tích lại`. Giao diện hiển thị đã đưa bài vào hàng chờ; lần thực hiện tăng từ `1` lên `2`, trạng thái trung gian đạt `25%`, sau đó worker kết thúc `FAILED` với lỗi `Gamma một chiều cần đúng một khoảng cách điểm và một gốc tọa độ.`
- Kết quả lỗi không sinh `PASS`, không tạo snapshot kết quả mới và lịch sử vẫn giữ nguyên. Đây là staging evidence cho retry và lỗi đầu vào; không phải bằng chứng worker crash/ACK/dead-letter.
- Lượt tổng hợp chạy quá nhanh nên không giữ được trạng thái `QUEUED` hoặc `RETRYING` đủ lâu để bấm hủy trên trình duyệt. Hợp đồng hủy trước khi worker nhận việc vẫn đã đạt trong kiểm thử local tại `docs/evidence/p8-local-gamma-queue-results-20260918.md`.
- Bằng chứng: `docs/evidence/p8-staging-gamma-retry-20260918.json`. P08-W03 vẫn mở cho cổng hủy staging có kiểm soát, ma trận lỗi worker/Redis, giới hạn tài nguyên, oracle độc lập và VERIFY/HANDOFF.
