# P7 — cổng tương thích loại đầu vào Pylinac trên staging — 2026-09-16

## Phạm vi

Kiểm tra bản sửa không cho bài phân tích ảnh nhận nhầm tệp liều, cấu trúc RT, kế hoạch xạ trị hoặc số đo chỉ vì tệp đã ở trạng thái hợp lệ. Hồ sơ thử nghiệm `dailyQA` và các dữ liệu liên quan không bị xóa, khôi phục, sửa hoặc tạo mới trong lần kiểm tra này.

## Bản phát hành được kiểm tra

- Nhánh: `codex/p4-org-site-machine`
- Mã nguồn: `02c51f3404a0c7ef509b752c96c0d1738b830db3`
- Triển khai API: `d8b6d51b-142e-4456-b99b-a2c87c65b3ec` — `SUCCESS`
- Triển khai giao diện: `6a2b5752-f23f-4194-856b-8f870c182b3c` — `SUCCESS`
- Lược đồ cơ sở dữ liệu: `20260914_0023`

## Kiểm tra bên ngoài

- API `health`: `200`, trạng thái sẵn sàng.
- API `ready`: `200`, trạng thái `ready`, lược đồ đúng `20260914_0023`.
- API `version`: trả đúng mã nguồn `02c51f3`, môi trường `staging`.
- Kiểm tra công khai và đối chiếu cấu hình Railway đều đạt, không có lỗi.

## Kiểm tra giao diện đã đăng nhập

Mở lại bài **Kiểm tra sao** trong hồ sơ staging đã có sẵn tệp liều RTDOSE hợp lệ:

- Khu vực chọn ảnh không còn liệt kê tệp RTDOSE.
- Giao diện hiển thị không có ảnh phù hợp để chọn, đúng với loại bài phân tích ảnh.
- Khu vực tệp vẫn giữ hồ sơ RTDOSE hợp lệ để không làm mất dữ liệu đã tải.
- Lịch sử Kiểm tra sao vẫn là `0`; không có lượt phân tích mới được tạo.
- Không gọi thao tác tải lên, xóa, lưu trữ, khôi phục hay xóa vĩnh viễn.

## Kết luận

Cổng tương thích loại đầu vào đã được triển khai và kiểm tra trên staging. Máy chủ từ chối lựa chọn sai loại trước khi gọi Pylinac; giao diện đồng thời loại lựa chọn sai để người dùng không gặp đường chạy không hợp lệ. Đây là cổng an toàn đầu vào, chưa phải nghiệm thu toàn bộ P7: vẫn cần ảnh Starshot đại diện, đối chiếu kết quả với chuẩn độc lập, xác nhận chuyên môn, báo cáo PDF và VERIFY/HANDOFF P7.
