# P8 — Nhãn đầu vào PSQA trên staging — 2026-09-15

## Phạm vi kiểm tra

- Dịch vụ được kiểm tra: giao diện staging RT-CONNECT.
- Phiên kiểm tra: mở một trang phân tích PSQA mới sau khi Railway triển khai thành công bản sửa giao diện.
- Dữ liệu: hồ sơ tổng hợp staging đã tồn tại; không tải lên, thay thế hoặc xóa tệp nào.

## Kết quả quan sát

- Khu vực chọn liều hiển thị bốn lựa chọn nghiệp vụ: `Tệp liều RTDOSE 1`, `Tệp liều RTDOSE 2`, `Dữ liệu đo liều 1` và `Dữ liệu đo liều 2`.
- Không có tên tệp `.json`, tên tệp kỹ thuật, mã hồ sơ hoặc mã nội bộ trong danh sách lựa chọn và phần tóm tắt đầu vào.
- Trường `Chênh lệch liều (%)`, `DTA (mm)`, `Ngưỡng liều thấp (%)`, `Ngưỡng đạt (%)`, `Chuẩn hóa`, `Phạm vi so sánh`, `Giới hạn Gamma`, `Số khoảng biểu đồ` và `Hệ số tinh chỉnh một chiều` vẫn hiển thị đầy đủ.
- Dữ liệu được chọn mặc định gồm một tệp RTDOSE làm tham chiếu và dữ liệu đo liều làm đối chiếu; trạng thái hiển thị là `Đã kiểm tra hợp lệ`.
- Lịch sử cũ và kết quả Gamma 3D chỉ đọc vẫn còn nguyên. Không tạo thêm lượt phân tích trong lần kiểm tra giao diện này.

## Đối chiếu triển khai

- Railway ghi nhận lượt triển khai web `fix: hide technical JSON inputs in PSQA` ở trạng thái thành công.
- Tệp HTML public trỏ tới gói giao diện mới; gói này có nhãn `Dữ liệu đo liều` và không còn chuỗi tên tệp JSON kỹ thuật của bộ dữ liệu thử.
- API staging vẫn ở bản trước `68d2202…`, phù hợp với phạm vi thay đổi chỉ ở giao diện; không cần dựng lại API hoặc worker cho thay đổi này.

## Kết luận và giới hạn

Đạt cổng UX P8-W02 cho việc ẩn tệp kỹ thuật trên giao diện PSQA và đã kiểm chứng trên staging. P8 chưa hoàn thành toàn bộ: còn đối chiếu hình học bằng fixture đại diện, chạy Gamma 1D/2D thành công trên staging, hàng đợi/lỗi phục hồi, tài nguyên lớn, báo cáo/xu hướng và VERIFY/HANDOFF.
