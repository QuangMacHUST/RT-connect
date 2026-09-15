# P7 — Đối chiếu chỉ số lõi với bộ mẫu chính thức Pylinac

## Phạm vi

Kiểm tra hồi quy local cho các chỉ số lõi mà RT-CONNECT lấy ra từ bộ điều hợp Pylinac. Mỗi trường được so với giá trị tham chiếu cố định của tệp mẫu chính thức trong wheel Pylinac `3.47.0`; mục tiêu là phát hiện ánh xạ sai hoặc thay đổi âm thầm trong bộ điều hợp.

Đây là kiểm tra hợp đồng với phiên bản Pylinac đã khóa, không phải một bộ tính độc lập, không thay thế commissioning, không thay thế đối chiếu với phần mềm chuẩn của cơ sở và không phải bằng chứng sẵn sàng lâm sàng.

## Kết quả

Kiểm thử `tests/test_pylinac_official_demo_matrix.py -k core_metric --no-cov -q` đạt **20/20**.

Các nhóm đã được kiểm tra:

- Picket Fence: sai số lớn nhất của lá chuẩn trực.
- Winston–Lutz một bi: khoảng cách lớn nhất giữa tâm tia và bi.
- Winston–Lutz nhiều bi: khoảng cách lớn nhất giữa trường và bi.
- VMAT DRGS, DRMLC và DRCS: sai lệch lớn nhất theo phần trăm.
- Phân tích biên dạng trường: độ phẳng theo trục ngang và dọc.
- Phân tích trường kiểu cũ: độ phẳng ngang và dọc trong nhóm kết quả giao thức.
- CatPhan 503, 504, 600 và 604: khả năng nhìn tương phản thấp.
- TomoCheese và Quart DVT: góc nghiêng phantom.
- Leeds TOR, Las Vegas, SNC MV và ACR Digital Mammography: độ đồng nhất, CNR hoặc điểm nhóm hạt.

Các giá trị được kiểm tra bằng `pytest.approx` với sai số tuyệt đối và tương đối `1e-7`. Bài DRCS được lấy lại từ chính wheel đang khóa trong lần chạy này; không sử dụng lại giá trị của một fixture hoặc phiên bản cũ.

## Ranh giới còn lại

- Chưa có fixture đại diện hoặc fixture commissioning được cơ sở phê duyệt cho toàn bộ các họ bài.
- Chưa có oracle độc lập đã được phê duyệt để xác nhận phép tính trên dữ liệu lâm sàng hoặc dữ liệu máy thật.
- Chưa chạy tương tác đầy đủ trên staging cho toàn bộ các nhóm bài.
- Chưa đóng P7-W03, P7-W04 hoặc cổng VERIFY/HANDOFF của P7.

Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; hồ sơ `dailyQA` được bảo toàn.
