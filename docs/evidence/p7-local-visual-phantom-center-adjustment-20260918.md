# Chọn tâm phantom trực tiếp theo thang đo DICOM — 2026-09-18

## Phạm vi

Lát cắt P7-W04 bổ sung thao tác chọn hoặc kéo tâm phantom trên vùng xem trước cho các nhóm:

- CatPhan;
- ACR CT và ACR MRI;
- TomoCheese và CIRS 062M;
- GE Helios;
- Quart DVT và Quart HyperSight.

Người dùng có thể chọn điểm trên ảnh. RT-CONNECT lấy khoảng lệch của điểm đó so với tâm ảnh, quy đổi bằng thang đo điểm ảnh DICOM và gửi điều chỉnh ngang/dọc theo milimét vào hợp đồng Pylinac. Pylinac vẫn là engine phân tích duy nhất; phần giao diện không tự phân tích ảnh.

## Quy tắc an toàn

- Điểm ngoài mép ảnh được giới hạn về biên hợp lệ trước khi quy đổi.
- API xem trước chỉ trả số ảnh, chiều rộng, chiều cao và thang đo điểm ảnh cần cho giao diện.
- Không trả thẻ DICOM, tên tệp, đường dẫn kho, chuỗi băm hoặc mã nội bộ cho giao diện.
- Nếu không đọc được thang đo vật lý, giao diện không tự đoán milimét; người dùng phải nhập điều chỉnh bằng ô số.
- Việc chọn tâm không tự tạo lượt phân tích, không sửa lịch sử và không tác động hồ sơ `dailyQA`.

## Kiểm thử

- Kiểm tra ánh xạ tâm, giới hạn điểm ngoài mép và trường hợp thiếu thang đo: đạt.
- Kiểm tra hợp đồng thông tin xem trước và API artifact: đạt.
- Toàn bộ kiểm thử giao diện: **74/74 đạt**.
- Kiểm tra kiểu, lint và bản dựng sản phẩm: đạt.
- Có cảnh báo kích thước gói JavaScript đã tồn tại từ trước trong bản dựng; không phải lỗi biên dịch hay lỗi kiểm thử.

## Giới hạn bằng chứng

Đây là bằng chứng kiểm tra local cho thao tác giao diện và quy đổi tọa độ. Chưa thể coi là nghiệm thu lâm sàng, chưa thay thế fixture phantom được phê duyệt, đối chiếu độc lập hoặc kiểm tra chuyên môn. Bước tiếp theo là dựng lại API, giao diện và tiến trình nền trên staging từ cùng một commit, sau đó kiểm tra parity công khai; kiểm tra tương tác có đăng nhập trên staging cần được thực hiện riêng khi có bộ fixture đại diện.

