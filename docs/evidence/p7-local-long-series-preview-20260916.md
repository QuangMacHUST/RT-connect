# Bằng chứng P7-W04 — xem trước chuỗi DICOM dài — 2026-09-16

## Phạm vi

- Không tạo, sửa, đánh giá, lưu trữ, khôi phục hoặc xóa hồ sơ QA nào.
- Không thay đổi nội dung phép phân tích Pylinac; chỉ mở rộng vùng xem trước để người thực hiện chọn ảnh/lát cần thao tác tay.
- Hồ sơ `dailyQA` và toàn bộ dữ liệu liên kết được giữ nguyên.

## Thay đổi đã thực hiện

- Tuyến thông tin xem trước và tuyến lấy ảnh cho phép chọn tới 2.048 ảnh/lát, thay cho giới hạn cũ là 32.
- Với chuỗi tối đa 32 ảnh/lát, giao diện vẫn dùng danh sách chọn quen thuộc.
- Với chuỗi dài hơn 32 ảnh/lát, giao diện dùng ô nhập số từ 1 đến tổng số ảnh/lát, tránh tạo danh sách dài gây khó sử dụng.
- Chỉ số gửi đến máy chủ vẫn là chỉ số bắt đầu từ 0; người dùng chỉ nhìn thấy số ảnh/lát bắt đầu từ 1.
- Khi nhập số ngoài khoảng cho phép, giao diện tự đưa về ảnh/lát đầu hoặc cuối gần nhất; máy chủ vẫn kiểm tra biên trước khi đọc tệp.

## Kiểm thử

- `tests/test_artifacts.py`: **12/12** đạt.
- Ca mới tạo bộ tệp ZIP gồm 33 ảnh DICOM tổng hợp, xác nhận:
  - thông tin xem trước trả tổng số 33 ảnh;
  - ảnh thứ 33 có thể được lấy và dựng thành PNG;
  - không cần tạo một danh sách giao diện 33 mục để chọn ảnh cuối.
- Toàn bộ kiểm thử máy chủ: **đạt 100%**.
- Toàn bộ kiểm thử giao diện: **53/53** đạt.
- Kiểm tra mã giao diện, kiểm tra kiểu và bản dựng sản xuất: **đạt**.

## Giới hạn còn lại

- Giới hạn an toàn hiện tại là 2.048 ảnh/lát cho một vùng xem trước; phép phân tích Pylinac vẫn dùng tệp đầu vào đầy đủ theo hợp đồng của từng bài.
- Chưa dùng tệp commissioning hoặc tệp bệnh nhân thật; cần phê duyệt dữ liệu và đối chiếu chuyên môn trước khi dùng lâm sàng.
- Chưa đóng P7-W04 vì còn các cổng ROI riêng, ánh xạ tọa độ theo từng ảnh và kiểm tra tương tác staging cho đầy đủ nhóm bài.

## Mã nguồn

- Bản thay đổi: `4a8bfd9` — `feat: support long dicom preview series`.
