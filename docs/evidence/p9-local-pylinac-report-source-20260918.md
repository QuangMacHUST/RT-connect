# P9-W01 — đưa kết quả Pylinac vào trình biên soạn báo cáo

Ngày kiểm tra: 2026-09-18  
Phạm vi: chọn kết quả Pylinac làm nguồn báo cáo; không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

## Kết quả

- API nhận nguồn `PYLINAC_QA`, kiểm tra `source_id` trong đúng đơn vị và chụp lại tên bài, nhóm bài, trạng thái đánh giá, tham số, kết quả, cảnh báo, lỗi và liên kết lớp phủ của lượt phân tích.
- Giao diện trình bày một loại nguồn mới là **Phân tích QA bằng Pylinac**. Người dùng chọn bài kiểm tra theo tên hiển thị rồi chọn lần phân tích theo tên bài, số lần và trạng thái; không hiển thị mã hồ sơ, mã lượt chạy hay dữ liệu JSON.
- Lớp chụp nguồn giữ `overlay_artifact_id`; khi người dùng chọn phần hình, trình dựng PDF lấy đúng tệp dẫn xuất trong cùng đơn vị, giải mã ảnh an toàn và nhúng vào trang đầu. Nếu thiếu ảnh, tệp văn bản vẫn được xuất kèm cảnh báo rõ ràng.
- Kiểm thử tích hợp tạo lượt hiệu chuẩn Pylinac tổng hợp có ảnh, dùng lượt đó làm nguồn báo cáo, xuất PDF và xác nhận snapshot/lớp phủ được giữ nguyên: **10/10** kiểm thử `tests/test_reports.py` đạt.
- Kiểm tra Ruff và mypy cho API báo cáo đạt; toàn bộ giao diện đạt **16/16 tệp và 80/80 phép thử**.

## Giới hạn còn mở

Lát cắt này chưa kiểm chứng phiên có đăng nhập trên staging, chưa nhúng lớp phủ vào PNG và chưa đối chiếu xem trước với tài liệu xuất. P9 vẫn mở; kết quả này không phải bằng chứng sẵn sàng lâm sàng.
