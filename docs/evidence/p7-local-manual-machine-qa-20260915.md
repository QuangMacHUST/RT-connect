# Bằng chứng P7 — QA nhập số đo

## Phạm vi

Kiểm tra lát cắt QA nhập số đo của P7 trên môi trường cục bộ, gồm bảng nhiều chỉ số, tiêu chí đánh giá, ghi chú theo số đo, không áp dụng có lý do, lưu bản chụp quy trình và bảo vệ dữ liệu ngoài quy trình.

## Kết quả

- `apps/api/tests/test_machine_qa.py`: **9/9 đạt**.
- Ruff cho API và bộ kiểm thử: **đạt**.
- Toàn bộ giao diện sau thay đổi: kiểm tra kiểu, lint và **39/39 bài** đạt.
- Toàn bộ API sau thay đổi: **277 bài đạt**; bộ kiểm thử riêng P7 sau thay đổi đạt 9/9.

## Điều đã kiểm chứng

- Bảng nhập nhiều giá trị sử dụng quy trình đã chọn, không yêu cầu tệp DICOM.
- Quy tắc `RANGE`, `MAX`, `MIN`, `ABSOLUTE_DEVIATION`, `PERCENT_DEVIATION` và `NA` được đánh giá đúng.
- Giá trị thiếu bắt buộc, sai đơn vị, biên cảnh báo/không đạt và đánh dấu không áp dụng có lý do được xử lý riêng.
- Ghi chú theo từng số đo được giữ trong bản nháp và bản kết quả.
- Số đo không thuộc quy trình bị từ chối khi đánh giá, không được đưa vào kết quả hoặc xu hướng.
- Quy trình mẫu và các nhãn hiển thị chính đã chuyển sang tiếng Việt.

## Giới hạn

Đây là cổng `LOCAL_VERIFIED_SLICE`. Chưa phải nghiệm thu staging cho P7; các gói Pylinac còn thiếu fixture chuẩn, khung kết quả/canvas dùng chung và ma trận kiểm thử toàn bộ capability vẫn tiếp tục mở.
