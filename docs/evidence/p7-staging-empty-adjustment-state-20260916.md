# P7-W04 — trạng thái rỗng của vùng điều chỉnh ảnh trên staging — 2026-09-16

## Mục tiêu

Khi bài Pylinac cần ảnh nhưng hồ sơ hiện tại không có ảnh phù hợp để chọn, giao diện phải nói rõ người dùng cần chọn ảnh; không được hiển thị trạng thái đang tải vô hạn.

## Bản phát hành

- Nhánh: `codex/p4-org-site-machine`
- Mã nguồn giao diện: `592dd0b`
- Triển khai giao diện staging: `SUCCESS`
- Bản API đang phục vụ vẫn đạt `health`, `ready` và `version`.

## Kết quả kiểm tra

Trên bài **Kiểm tra sao** trong hồ sơ staging đang có tệp RTDOSE hợp lệ nhưng không có ảnh Starshot phù hợp:

- Bộ chọn ảnh không liệt kê tệp RTDOSE.
- Vùng điều chỉnh hiển thị: **“Chọn ảnh để bật vùng điều chỉnh.”**
- Không còn hiển thị **“Đang tải ảnh xem trước…”** khi chưa chọn ảnh.
- Nút **“Bắt đầu phân tích”** bị khóa vì chưa có đầu vào phù hợp.
- Lịch sử Kiểm tra sao vẫn là `0`.
- Không tải lên, tạo phiên phân tích, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu.

## Kiểm thử cục bộ

- Kiểm thử giao diện riêng: `3/3` đạt.
- Toàn bộ kiểm thử giao diện: `14` tệp, `51/51` đạt.
- Lint, kiểm tra kiểu và bản dựng sản xuất đạt.

## Kết luận

Trạng thái rỗng của vùng điều chỉnh đã rõ ràng và không còn gây hiểu nhầm là hệ thống đang tải. Đây là một phần của P7-W04; chưa đóng toàn bộ P7 vì vẫn còn fixture đại diện, đối chiếu độc lập, kiểm tra chuyên môn, báo cáo PDF và VERIFY/HANDOFF.
