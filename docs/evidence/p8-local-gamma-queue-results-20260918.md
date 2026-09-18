# Bằng chứng cục bộ P8-W03 — hàng đợi và kết quả Gamma

- Ngày kiểm tra: 2026-09-18
- Phạm vi: `P8-W03`
- Môi trường: cục bộ, bộ dữ liệu tổng hợp và hàng đợi thử nghiệm
- Engine: Pylinac cho phép tính Gamma mới; các kết quả Gamma ba chiều cũ chỉ được xem lại

## Kết quả

Bộ `apps/api/tests/test_gamma.py` đạt **15/15**. Các ca đã kiểm tra gồm:

- lưới giống nhau cho kết quả đạt chuẩn;
- sai khác hệ tọa độ, biến đổi và dữ liệu không hợp lệ bị chặn trước khi tính;
- phép tính một chiều và hai chiều giữ đúng ngưỡng liều, khoảng cách, vùng so sánh và độ bao phủ;
- điểm Gamma cao bị đánh dấu theo giới hạn, không làm sai mẫu số;
- bài phân tích được đưa vào hàng đợi với trạng thái `QUEUED`;
- hủy trước khi tiến trình nền nhận việc chuyển sang `CANCELLED`, ghi cảnh báo và có thể gọi lại an toàn;
- gửi lại cùng khóa lặp trả lại đúng bài đã có;
- dùng cùng khóa cho dữ liệu khác bị từ chối;
- bài PSQA không nhận đầu vào JSON kỹ thuật;
- giới hạn tài nguyên được kiểm tra trước khi đưa việc vào hàng đợi.

## Giới hạn bằng chứng

Đây là bằng chứng cục bộ cho hợp đồng API, bộ tính và các trạng thái hàng đợi. Chưa coi đây là nghiệm thu staging: vẫn cần tạo một bài PSQA tổng hợp trên staging, quan sát tiến trình nền thật, thử hủy/thử lại, kiểm tra kết quả một chiều/hai chiều, bản đồ, biểu đồ, lịch sử và ma trận lỗi mạng/worker. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA` trong ca này.
