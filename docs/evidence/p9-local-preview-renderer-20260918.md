# P9-W03 — xem trước dùng cùng bộ dựng với tệp xuất

Ngày kiểm tra: 2026-09-18  
Phạm vi: bản xem trước của một bản báo cáo đã lưu; không thay đổi hồ sơ QA và không xóa dữ liệu.

## Kết quả

- API có tuyến xem trước yêu cầu xác thực và kiểm tra đúng `report_key`, bản báo cáo, bản chỉnh sửa và phạm vi đơn vị trước khi dựng.
- Tuyến này lấy đúng bản chụp bất biến, gọi chính `render_report` và trả ảnh PNG; vì vậy bản xem trước và tệp PNG xuất không có hai cách tính nội dung khác nhau.
- Khi bản chụp có lớp phủ Pylinac, cùng lớp phủ được dùng trong bản xem trước như khi xuất PDF/PNG. Cảnh báo thiếu lớp phủ được truyền qua tiêu đề phản hồi, không làm thay đổi bản chụp.
- Giao diện chỉ hiển thị bản xem trước của bản đã lưu. Nếu người dùng vừa chỉnh sửa, giao diện yêu cầu lưu bản mới trước khi cập nhật ảnh; bản cũ không bị ghi đè.
- Không hiển thị mã nội bộ, dữ liệu JSON, đường dẫn kho lưu trữ hoặc thông tin kỹ thuật trong giao diện. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## Cổng kiểm tra cục bộ

- `tests/test_reports.py` và `tests/test_pylinac_qa.py`: **51/51 đạt**; riêng `test_reports.py`: **11/11 đạt**.
- Kiểm thử giao diện và máy khách: **16 tệp, 81 phép thử đạt**.
- Mypy phần API báo cáo, Ruff, kiểm tra kiểu, lint và bản dựng sản phẩm: **đạt**.
- Kiểm thử tuyến xem trước xác nhận ảnh PNG hợp lệ, kích thước 720×400 và bản chụp báo cáo không bị thay đổi.

## Giới hạn còn mở

Chưa kiểm thử phiên có đăng nhập trên staging để tạo lượt Pylinac thật, mở trình biên soạn, đối chiếu trực quan xem trước với PDF/PNG và đóng VERIFY/HANDOFF P9. Bảng nghiệp vụ dài qua nhiều trang vẫn cần cổng riêng.
