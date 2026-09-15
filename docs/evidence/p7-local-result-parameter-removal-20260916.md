# P7-W04 — hiển thị tham số đã bỏ trong diff lịch sử — local — 2026-09-16

## Phạm vi

Trình xem kết quả QA máy phải cho người dùng biết đầy đủ thay đổi giữa lượt đang xem và lượt ngay trước: tham số mới thêm, tham số được sửa và tham số đã bỏ. Không hiển thị mã nội bộ hay dữ liệu kỹ thuật không cần thiết.

## Hành vi đã kiểm tra

- Khi lượt mới có thêm tham số, giao diện hiển thị `Mới thêm`.
- Khi lượt mới không còn tham số của lượt trước, giao diện hiển thị `Đã bỏ`.
- Khi giá trị thay đổi, giao diện hiển thị giá trị trước và sau bằng nhãn tiếng Việt.
- Khi không có thay đổi, giao diện hiển thị `Không có thay đổi thông số.`.
- Kết quả, đánh giá và lịch sử gốc chỉ được đọc; không có thao tác sửa hoặc xóa trong luồng này.

## Kiểm thử

- Kiểm thử giao diện: **52/52** đạt.
- Lint: đạt.
- Kiểm tra kiểu: đạt.
- Bản dựng sản xuất: đạt.

## Kết luận

P7-W04 đã được bổ sung đầy đủ diff thêm/sửa/bỏ ở lớp hiển thị lịch sử. Đây là một lát cắt UX local; P7-W04 vẫn còn cổng kiểm chứng tương tác staging, ROI chuyên biệt và ánh xạ đa ảnh.
