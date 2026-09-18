# P9-W02/P09-W03 — renderer báo cáo không lộ thông tin kỹ thuật

Ngày kiểm tra: 2026-09-18  
Phạm vi: renderer PDF/CSV từ bản chụp báo cáo; không thay đổi hồ sơ QA và không xóa dữ liệu.

## Kết quả

- PDF hiển thị tiêu đề tiếng Việt, loại báo cáo bằng nhãn nghiệp vụ, tên bài kiểm tra và đánh giá đã được chuyển ngữ.
- PDF tôn trọng phần đang hiển thị; phần bị ẩn không được đưa vào tài liệu.
- PDF dài được tự động chia thành nhiều trang, dùng chung một bộ font và giữ thứ tự phần báo cáo.
- Ghi chú người dùng trong phần văn bản được đưa vào PDF thay vì chỉ hiển thị tên phần.
- Các phần chỉ số, cảnh báo, thông tin bài kiểm tra, nguồn và hình phân tích có nội dung tóm tắt an toàn; không đẩy mã hồ sơ, mã lần chạy, mã nguồn, bản chụp cấu hình hoặc mã băm lên tài liệu dành cho người dùng.
- CSV dành cho người dùng chỉ còn tiêu đề, loại báo cáo, nhãn phần và nội dung; không xuất cấu hình thô hoặc liên kết nguồn kỹ thuật.
- Tệp dữ liệu JSON vẫn tồn tại ở lớp giao tiếp nội bộ để bảo toàn tương thích máy–máy; giao diện người dùng không còn cung cấp lựa chọn này.

## Cổng kiểm tra cục bộ

- Kiểm thử `test_reports.py`: **11/11 đạt**, gồm đường đi từ lượt Pylinac có ảnh lớp phủ tới tệp PDF và PNG cùng tuyến xem trước bản đã lưu.
- Kiểm tra quy tắc mã nguồn trên renderer và kiểm thử: **đạt**.
- Kiểm tra kiểu renderer: **đạt**.
- Kiểm tra Unicode tiếng Việt, ẩn phần, chia nhiều trang, tính xác định, loại bỏ dòng phiên bản/mã băm kỹ thuật và nhúng ảnh phân tích RGB vào PDF: **đạt**.

## Giới hạn còn mở

Lát cắt này chưa dựng bảng nghiệp vụ nhiều trang, chưa kiểm tra hiển thị trực quan có đăng nhập trên staging và chưa chạy VERIFY/HANDOFF. Vì vậy P09-W02/P09-W03 và toàn bộ P9 vẫn mở; không được dùng bằng chứng này để tuyên bố sẵn sàng lâm sàng.
