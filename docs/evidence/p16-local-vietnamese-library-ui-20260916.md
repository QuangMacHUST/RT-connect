# Bằng chứng P16 — giao diện thư viện kiến thức thuần tiếng Việt

- Ngày kiểm tra: 2026-09-16.
- Phạm vi: giao diện thư viện kiến thức trên máy phát triển; không thay đổi dữ liệu staging.
- Đã chuyển tên loại bài, trạng thái, loại nguồn, trạng thái nguồn, công cụ sử dụng, lịch sử, so sánh và thông báo thao tác sang tiếng Việt.
- Người dùng không còn thấy mã bài viết nội bộ, mã phiên bản kỹ thuật, mã băm, mã liên kết bài gốc hoặc trạng thái nội bộ. Khóa nội bộ của bài viết được sinh tự động từ tên bài và chỉ giữ ở phía hệ thống.
- Đã bỏ vùng nhập hàng loạt dạng JSON, vùng nhập nội dung/căn cứ dạng JSON và vùng xem kết quả kỹ thuật dạng JSON. Người dùng nhập nội dung bài viết, bối cảnh áp dụng và ghi chú nguồn bằng biểu mẫu thông thường.
- Tải xuống giao diện chỉ còn bảng dữ liệu phục vụ người dùng; không còn nút tải JSON.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ staging; hồ sơ `dailyQA` và dữ liệu liên kết được bảo toàn.

## Kết quả kiểm tra

Tại `apps/web`:

- `npm.cmd run typecheck` — đạt.
- `npm.cmd run lint` — đạt, không có cảnh báo.
- `npm.cmd run test -- --run` — đạt **54/54** kiểm thử trong 14 tệp.
- `npm.cmd run build` — đạt. Công cụ dựng chỉ còn cảnh báo kích thước gói JavaScript lớn hơn 500 kB, không phải lỗi biên dịch.

Đây là bằng chứng cải tiến giao diện local cho P16/P11, chưa đóng toàn bộ P11 hoặc P16. Các cổng dữ liệu thật, phạm vi nội bộ/cộng đồng, tệp PDF, nguồn trích dẫn, đối chiếu chuyên môn và kiểm chứng staging vẫn phải hoàn thành theo `plan.md`.
