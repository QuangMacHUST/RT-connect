# P7-W04 — lịch sử chỉ hiển thị đúng bài QA — kiểm tra local — 2026-09-16

## Vấn đề

Các trang bài QA dùng chung một tuyến lấy lịch sử. Nếu không lọc theo bài đang mở, kết quả của Starshot, Picket Fence, VMAT, CatPhan hoặc bài khác có thể bị dùng làm kết quả mới nhất của trang hiện tại.

## Thay đổi

- Bổ sung hàm lọc lịch sử dùng chung theo tên bài QA.
- Áp dụng bộ lọc cho Picket Fence, Starshot, Winston–Lutz một bi, Winston–Lutz nhiều bi, ba bài VMAT, hai bài phân tích trường, năm bài CatPhan, ba nhóm phantom và toàn bộ bài ảnh phẳng.
- Giữ nguyên thứ tự lịch sử do máy chủ trả về sau khi lọc; không sửa, xóa hoặc tạo lại lượt phân tích.
- Bài đang xem không còn lấy số liệu hoặc cảnh báo từ bài QA khác trong cùng hồ sơ.

## Kiểm thử

- Kiểm thử tiện ích: danh sách trộn Starshot/Picket Fence chỉ trả đúng bài được chọn; danh sách rỗng không gây lỗi.
- Toàn bộ giao diện: **54/54** đạt.
- Kiểm tra kiểu: đạt.
- Kiểm tra mã: đạt, không còn cảnh báo.
- Bản dựng sản xuất: đạt.

Đây là kiểm tra local cho tính đúng đắn của giao diện; cần xác nhận thao tác thật trên staging trước khi đóng P7-W04.

Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ staging; hồ sơ `dailyQA` được bảo toàn.
