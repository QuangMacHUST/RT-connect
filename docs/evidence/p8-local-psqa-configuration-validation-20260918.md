# Kiểm tra tham số PSQA ngay trên biểu mẫu — 2026-09-18

## Phạm vi

Biểu mẫu PSQA kiểm tra trước khi gửi lượt phân tích sang máy chủ và Pylinac:

- chênh lệch liều lớn hơn 0 và không vượt quá 100%;
- DTA lớn hơn 0 mm;
- ngưỡng liều thấp và ngưỡng đạt trong khoảng 0–100%;
- giới hạn Gamma trong khoảng 1–10;
- số khoảng biểu đồ là số nguyên từ 2 đến 100;
- hệ số tinh chỉnh một chiều là số nguyên từ 1 đến 10;
- không cho tạo lượt Gamma ba chiều mới.

Các trường người dùng cần nhập vẫn hiển thị rõ “Chênh lệch liều (%)” và “DTA (mm)”. Pylinac chịu trách nhiệm engine Gamma; lớp mới chỉ kiểm tra biểu mẫu và khóa thao tác gửi khi dữ liệu chưa hợp lệ.

## Trường hợp chạy đúng

- Cấu hình mặc định 3%/3 mm, ngưỡng 10%, ngưỡng đạt 95%, giới hạn Gamma 2, 10 khoảng biểu đồ và hệ số 3 được chấp nhận.
- Cấu hình hợp lệ không xuất hiện cảnh báo và có thể đi tiếp tới bước tạo lượt phân tích khi tệp đầu vào cũng đủ điều kiện.

## Trường hợp lỗi và phục hồi

- Giá trị trống, không hữu hạn, bằng 0 hoặc âm ở chênh lệch liều/DTA bị báo ngay.
- Ngưỡng ngoài 0–100%, giới hạn Gamma ngoài 1–10 bị báo ngay.
- Số khoảng biểu đồ hoặc hệ số tinh chỉnh không phải số nguyên hay ngoài miền bị báo ngay.
- Nếu người dùng nhập cấu hình ba chiều mới, biểu mẫu giải thích giới hạn Pylinac và không gửi tác vụ.
- Khi có lỗi, nút bắt đầu bị khóa; không tạo lượt chạy, không sửa lịch sử và không tác động hồ sơ `dailyQA`.

## Kiểm thử

- Kiểm thử riêng: **7/7 đạt**.
- Toàn bộ kiểm thử giao diện: **78/78 đạt**.
- Kiểm tra kiểu, lint và bản dựng sản phẩm: đạt.
- Bản dựng còn cảnh báo kích thước gói JavaScript đã tồn tại từ trước; không có lỗi biên dịch.

## Giới hạn bằng chứng

Đây là bằng chứng local cho biên nhập liệu, chưa phải bằng chứng Gamma chạy thật trên staging, chưa thay thế kiểm thử hàng đợi/hủy/thử lại, đối chiếu độc lập hoặc nghiệm thu chuyên môn. Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ `dailyQA`.

