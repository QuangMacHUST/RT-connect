# Bằng chứng P7-W04 — ánh xạ tọa độ ảnh an toàn

- Ngày kiểm tra: 2026-09-16.
- Phạm vi: tiện ích ánh xạ điểm của vùng điều chỉnh ảnh trên máy phát triển.
- Tọa độ con trỏ được đổi từ khung hiển thị sang kích thước ảnh gốc trước khi gửi cho Pylinac.
- Điểm bấm ngoài mép trái/trên được giới hạn về `0`; điểm bấm ngoài mép phải/dưới được giới hạn về kích thước ảnh gốc. Không gửi tọa độ của vùng hiển thị trình duyệt cho bộ tính.
- Hỗ trợ cả tọa độ điểm ảnh và tọa độ chuẩn hóa từ `0` đến `1`; trường hợp khung ảnh hoặc kích thước ảnh không hợp lệ không tạo tọa độ.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa dữ liệu staging; hồ sơ `dailyQA` được bảo toàn.

## Kết quả kiểm tra

Tại `apps/web`:

- Kiểm tra kiểu — đạt.
- Kiểm tra quy tắc mã nguồn — đạt, không cảnh báo.
- Kiểm thử riêng `MachineQAPage.test.tsx` — đạt **6/6**.
- Toàn bộ kiểm thử giao diện — đạt **55/55**.
- Bản dựng sản xuất — đạt; chỉ còn cảnh báo kích thước gói JavaScript lớn hơn 500 kB.

Đây là cổng kiểm tra ánh xạ tọa độ local cho P7-W04. Các ROI chuyên biệt của từng lớp Pylinac, ánh xạ/ghép cặp trực quan theo từng ảnh và kiểm chứng tương tác trên staging vẫn còn mở.
