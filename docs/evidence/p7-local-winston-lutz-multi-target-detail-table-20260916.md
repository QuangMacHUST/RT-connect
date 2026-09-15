# Bằng chứng cục bộ P7 — Bảng đối chiếu Winston–Lutz nhiều bi

Ngày kiểm tra: 2026-09-16  
Phạm vi: P07-W04, trình xem kết quả Winston–Lutz nhiều bi  
Dữ liệu: kết quả tổng hợp do bộ kiểm thử tạo, không chứa dữ liệu bệnh nhân

## Đã thực hiện

- Bổ sung vùng chi tiết dùng chung cho trình xem Pylinac và hàm hiển thị theo từng lượt kết quả.
- Đọc `image_details` và `bb_arrangement` từ ảnh chụp kết quả Pylinac đã lưu; không tính lại khoảng cách ở giao diện.
- Hiển thị một dòng cho từng ảnh, các cột góc máy, góc chuẩn trực, góc bàn, khoảng cách trường–bi của từng bi và sai lệch xoay bàn.
- Chỉ hiển thị “Ảnh 1”, “Ảnh 2”…; không đưa tên tệp, mã lượt chạy hoặc mã nội bộ vào bảng.
- Khi người dùng mở một lượt cũ, bảng lấy dữ liệu từ chính lượt đó cùng với cảnh báo, chỉ số và ảnh phân tích của lượt đó.
- Ô không có bi tương ứng hiển thị dấu gạch ngang, không thay bằng số 0.

## Kiểm thử

Lệnh kiểm thử giao diện `src/pages/MachineQAPage.test.tsx` đạt **8/8**, trong đó có ca kiểm tra bảng Winston–Lutz nhiều bi. Kiểm tra kiểu, lint và bản dựng giao diện được chạy tiếp sau khi hoàn tất thay đổi.

## Giới hạn còn mở

Đây là bằng chứng giao diện cục bộ và không thay cho đối chiếu với bộ ảnh commissioning, kiểm tra tương tác trên staging hoặc nghiệm thu lâm sàng. Các khoảng cách và góc vẫn là kết quả của Pylinac; đánh giá Đạt/Cảnh báo/Không đạt vẫn do người thực hiện chọn.
