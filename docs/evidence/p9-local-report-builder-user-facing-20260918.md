# P9-W01 — trình biên soạn báo cáo theo ngôn ngữ nghiệp vụ

Ngày kiểm tra: 2026-09-18  
Phạm vi: giao diện trình biên soạn báo cáo, không thay đổi hồ sơ QA và không xóa dữ liệu.

## Kết quả

- Người dùng chọn bài kiểm tra và kết quả bằng tên nghiệp vụ; giao diện không hiển thị mã bài, mã lần chạy, mã nguồn, mã mẫu hoặc mã phiên bản nội bộ.
- Các phần báo cáo có thể đổi tên, ẩn/hiện, sắp xếp, xóa khỏi bản đang soạn và thêm ghi chú bằng biểu mẫu tiếng Việt.
- Các loại nguồn, loại phần, trạng thái kết quả, trạng thái mẫu và định dạng tệp xuất được chuyển thành nhãn tiếng Việt.
- Giao diện không còn hiển thị cấu hình thô, bản chụp JSON, chuỗi mã nguồn hoặc mã lỗi kỹ thuật. Tệp dữ liệu JSON vẫn được giữ ở lớp giao tiếp nội bộ khi hệ thống cần, nhưng không còn là lựa chọn xuất cho người dùng trên màn hình này.
- Trạng thái kết quả không xác định được hiển thị là “Đã ghi nhận”, không đẩy chuỗi kỹ thuật lên giao diện.
- Mỗi lần lưu vẫn tạo bản báo cáo mới từ bản chụp nguồn; thay đổi kết quả gốc không âm thầm sửa bản đã lưu.

## Cổng kiểm tra cục bộ

- Kiểm thử giao diện riêng: **2/2 đạt**.
- Toàn bộ giao diện: **16/16 tệp, 80/80 phép thử đạt**.
- Kiểm tra kiểu: **đạt**.
- Kiểm tra quy tắc mã nguồn: **đạt**.
- Bản dựng sản phẩm: **đạt**.
- Kiểm tra khoảng trắng thay đổi: **đạt**.

## Giới hạn còn mở

Đây là `LOCAL_VERIFIED_SLICE` cho trải nghiệm biên tập và lựa chọn nguồn. P09-W01 chưa đóng toàn bộ P9: còn hợp đồng bản chụp/bố cục, trình dựng PDF có hình chú thích thật, font tiếng Việt qua trang, tính bất biến khi xuất và kiểm tra có đăng nhập trên staging. Không được dùng bằng chứng này để tuyên bố sản phẩm đã sẵn sàng lâm sàng.
