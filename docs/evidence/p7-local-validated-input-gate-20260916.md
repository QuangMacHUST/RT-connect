# P7 — Cổng tệp hợp lệ trước khi phân tích Pylinac

Ngày kiểm tra: 2026-09-16  
Phạm vi: giao diện QA máy, các bài phân tích dùng tệp Pylinac  
Môi trường: máy phát triển  
Mục tiêu: không cho phép chạy bộ tính với tệp chưa được kiểm tra hợp lệ.

## Thay đổi đã kiểm tra

- Bổ sung quy tắc dùng chung để xác nhận trạng thái `VALID` của tệp được chọn.
- Bài dùng một tệp chỉ mở nút phân tích khi đúng tệp đang chọn đã hợp lệ.
- Bài dùng nhiều tệp, gồm Winston–Lutz nhiều bi, nhật ký máy và bài hạt nhân, chỉ mở nút phân tích khi toàn bộ tệp được chọn đã hợp lệ.
- Tệp `WARNING`, `INVALID`, `VALIDATING`, chưa kiểm tra hoặc không còn tồn tại trong danh sách vẫn được giữ lại để người dùng kiểm tra lại; không bị âm thầm loại bỏ.
- Bài hiệu chuẩn nhập số liệu không có tệp vẫn giữ luồng riêng, không bị chặn bởi cổng tệp.

## Kiểm thử

- Hàm kiểm tra cổng đầu vào: đạt các ca tệp hợp lệ, cảnh báo, danh sách rỗng, tệp thiếu và kết hợp nhiều tệp.
- Kiểm thử giao diện: **56/56**.
- Kiểm tra kiểu: đạt.
- Kiểm tra quy tắc mã nguồn: đạt.
- Bản dựng sản xuất: đạt; còn cảnh báo kích thước gói JavaScript hiện hữu, không làm bản dựng thất bại.
- Kiểm tra hợp đồng kế hoạch: `passed=true`, `failed_check_count=0`, 21 giai đoạn và 264 kịch bản.

## Ranh giới xác nhận

Đây là bằng chứng cổng giao diện và hợp đồng local. Chưa ghi nhận kiểm chứng thao tác đã đăng nhập trên staging cho toàn bộ các bài, chưa thay thế đối chiếu bằng bộ mẫu chuẩn/commissioning và chưa phải nghiệm thu lâm sàng.

Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging trong lần kiểm tra này. Hồ sơ `dailyQA` và các dữ liệu liên quan được bảo toàn.
