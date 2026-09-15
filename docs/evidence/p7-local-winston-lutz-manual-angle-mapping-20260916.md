# Bằng chứng P7-W04 — nhập góc thủ công theo từng ảnh cho Winston–Lutz một bia

- Ngày kiểm tra: 2026-09-16.
- Phạm vi: giao diện và bộ điều hợp Pylinac của bài Winston–Lutz một bia.
- Giao diện cho phép chọn một trong ba cách lấy góc: đọc từ thông tin DICOM, đọc từ tên tệp hoặc nhập theo thứ tự ảnh trong bộ ZIP.
- Với chế độ nhập tay, giao diện lấy số ảnh từ tuyến thông tin xem trước, hiển thị các dòng “Ảnh 1”, “Ảnh 2”… và không đưa tên tệp kỹ thuật vào màn hình. Mỗi dòng yêu cầu đủ góc máy, góc chuẩn trực và góc bàn.
- Máy chủ dùng cùng thứ tự thành viên ảnh an toàn của bộ ZIP để tạo `axis_mapping` cho Pylinac. Nếu số dòng không khớp số ảnh, một góc không phải số hoặc vừa bật đọc tên tệp vừa nhập tay, lượt phân tích bị từ chối trước khi gọi engine.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; hồ sơ `dailyQA` được bảo toàn.

## Kết quả kiểm tra

Tại `apps/api`:

- Kiểm thử Winston–Lutz liên quan — đạt **6/6**.
- Kiểm tra quy tắc mã nguồn — đạt.

Tại `apps/web`:

- Kiểm tra kiểu — đạt.
- Kiểm tra quy tắc mã nguồn — đạt.
- Bản dựng sản xuất — đạt.

Đây là bằng chứng hợp đồng giao diện–máy chủ cho nhập góc thủ công. Chưa có nghĩa là toàn bộ P7 đã hoàn thành; vẫn cần fixture đại diện được phê duyệt, đối chiếu độc lập, kiểm thử tương tác staging và nghiệm thu chuyên môn.
