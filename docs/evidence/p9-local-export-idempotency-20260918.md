# Bằng chứng cục bộ P9-W04 — xuất lặp theo bản chụp

- Ngày kiểm tra: 2026-09-18
- Phạm vi: `P9-W04`
- Môi trường: cục bộ, SQLite thử nghiệm và kho đối tượng trong bộ kiểm thử
- Engine: `report-renderer-0.4`

## Kết quả

Kiểm thử `test_report_exports_are_deterministic_idempotent_and_downloadable` đạt. Một bản báo cáo đã lưu được xuất ở đủ bốn định dạng được hỗ trợ: JSON, CSV, PDF và PNG. Mỗi lần xuất có khóa lặp riêng; gửi lại đúng khóa và đúng định dạng trả lại cùng công việc đã hoàn tất thay vì tạo tệp thứ hai.

Kiểm thử cũng xác nhận:

- tệp được lưu theo bản chụp bản báo cáo và bộ dựng;
- tải lại trả đúng hàm băm, kiểu tệp và kích thước đã ghi nhận;
- dùng lại khóa cho định dạng khác bị từ chối với `EXPORT_IDEMPOTENCY_CONFLICT`;
- lỗi lưu thông tin công việc dọn tệp đã dựng để lần thử lại không tạo bản mồ côi;
- lỗi dọn tệp được trả về tín hiệu đối soát, không bị che giấu;
- không có thao tác xóa vĩnh viễn hồ sơ QA trong kiểm thử này.

## Giới hạn bằng chứng

Đây là bằng chứng cục bộ cho hợp đồng xuất và phục hồi. Chưa dùng phiên đăng nhập staging để mở lịch sử của một báo cáo thật, tải lại cả PDF/PNG từ giao diện và đối chiếu với bản xem trước. Việc xóa vĩnh viễn không thuộc phạm vi sản phẩm hiện tại; hồ sơ QA được giữ lại hoặc lưu trữ theo quyết định nghiệp vụ.
