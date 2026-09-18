# Bằng chứng P8 — đầu vào Gamma một chiều Pylinac — kiểm tra cục bộ

- Ngày kiểm tra: 2026-09-18.
- Phạm vi: cho phép tệp đo liều `gamma.measurement.v1` có lưới một chiều đi qua bước xác thực và giữ đúng trục `x` trước khi đưa vào Gamma Pylinac.
- Sửa lỗi: bộ xác thực tệp trước đây chỉ cho phép lưới hai hoặc ba chiều, trong khi engine Pylinac và giao diện đã hỗ trợ Gamma một chiều.
- Kiểm tra thành công: lưới `[4]`, khoảng cách `[1.0]`, gốc `[0.0]`, trục `x`, dữ liệu liều tổng hợp hợp lệ được xác thực là `VALID` và được nạp thành mảng một chiều.
- Kiểm tra hình học: hai hồ sơ một chiều cùng kích thước, khoảng cách và gốc tọa độ được chấp nhận trước bước đưa vào hàng đợi.
- Kiểm thử Pylinac liên quan: toàn bộ nhóm kiểm thử Gamma, DICOM, worker và bộ chuyển đổi Pylinac đều đạt.
- Kiểm tra kiểu mã và lint các tệp bị ảnh hưởng đạt.
- Giới hạn: đây là bằng chứng cục bộ; staging hiện chưa có cặp dữ liệu đo liều một chiều đã xác thực để chạy thật. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`; không xóa vĩnh viễn hồ sơ nào.
