# P7-W04 — cảnh báo Pylinac và lịch sử kết quả — 2026-09-15

## Phạm vi

Lát cắt cục bộ kiểm tra trình xem kết quả QA máy. Mục tiêu là bảo đảm cảnh báo do Pylinac được hiển thị riêng, không bị biến thành lỗi hoặc tự động thay đổi đánh giá của người thực hiện, đồng thời cảnh báo đi cùng đúng lượt lịch sử.

## Kết quả

- Cảnh báo của bộ tính được hiển thị trong vùng riêng **Cảnh báo từ bộ tính**.
- Cảnh báo không làm đổi trạng thái đánh giá của người thực hiện; người dùng vẫn phải tự chọn Đạt, Cảnh báo, Cần xem lại hoặc Không đạt.
- Khi mở lại một lượt cũ, cảnh báo được lấy từ đúng lượt đang xem và không bị thay bằng cảnh báo của lượt mới nhất.
- Giao diện không hiển thị mã nội bộ, cấu trúc JSON hoặc tên trường kỹ thuật cho người dùng.
- Kiểm thử riêng `MachineQAPage.test.tsx`: **2/2 đạt**.
- Toàn bộ kiểm thử giao diện: **49/49 đạt**, gồm 14 tệp kiểm thử.
- Kiểm tra mã nguồn, kiểm tra kiểu và bản dựng sản xuất đều đạt; cảnh báo kích thước gói JavaScript lớn vẫn được ghi nhận như việc tối ưu riêng.

## Giới hạn bằng chứng

Đây là bằng chứng local cho quy tắc hiển thị và giữ lịch sử. Chưa dùng bằng chứng này để tuyên bố P7 hoàn tất. Còn cần chạy bằng một lượt Pylinac thật trên staging, kiểm tra PDF, đối chiếu kết quả độc lập với dữ liệu chuẩn và hoàn thành VERIFY/HANDOFF P7.

Không có dữ liệu staging nào bị tạo, sửa hoặc xóa trong kiểm thử này. Hồ sơ `dailyQA`, các kết quả liên quan và điểm xu hướng được giữ nguyên.
