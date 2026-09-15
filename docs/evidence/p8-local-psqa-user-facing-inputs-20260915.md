# P8 — Giao diện đầu vào PSQA không lộ tệp kỹ thuật — local — 2026-09-15

## Kết quả

- Trang phân tích PSQA chỉ đưa vào danh sách lựa chọn các dữ liệu đã kiểm tra hợp lệ gồm tệp liều RTDOSE và dữ liệu đo.
- Tệp có loại kỹ thuật `JSON` bị loại khỏi danh sách PSQA, dù vẫn được giữ trong kho để phục vụ dữ liệu kế thừa hoặc kiểm thử kỹ thuật phù hợp.
- Nhãn hiển thị được đổi thành `Tệp liều RTDOSE`, `Tệp liều RTDOSE 1/2` hoặc `Dữ liệu đo liều`; người dùng không nhìn thấy tên tệp `.json`, mã hồ sơ hay mã nội bộ trong hai ô chọn liều.
- Quy tắc này chỉ thay đổi lớp trình bày của luồng PSQA. Cổng API vẫn giữ kiểm tra loại dữ liệu, vai trò, trạng thái hợp lệ và hình học trước khi đưa bài vào hàng chờ.

## Kiểm tra

- Bộ kiểm thử giao diện: **13 tệp kiểm thử / 42 kiểm thử đạt**.
- Kiểm tra riêng nhãn đầu vào: xác nhận dữ liệu đo có tên kỹ thuật `.json` vẫn hiển thị là `Dữ liệu đo liều`; hai tệp RTDOSE trùng tên được phân biệt bằng số thứ tự thân thiện.
- Kiểm tra quy tắc mã nguồn: đạt.
- Kiểm tra kiểu TypeScript: đạt.
- Bản dựng giao diện sản xuất: đạt; còn cảnh báo kích thước gói JavaScript hiện hữu của Vite, không phải lỗi biên dịch.

## Ranh giới

Đây là lát cắt UX cục bộ cho P8-W02, chưa đóng P8. Các cổng còn mở gồm đối chiếu hình học trên bộ fixture PSQA đại diện, hàng đợi và lỗi phục hồi trên staging, tài nguyên lớn, kết quả 1D/2D thực tế bằng Pylinac, lịch sử/báo cáo/xu hướng và VERIFY/HANDOFF.
