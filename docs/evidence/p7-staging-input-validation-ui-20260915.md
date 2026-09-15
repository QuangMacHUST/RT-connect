# P7 — kiểm chứng giao diện cổng đầu vào Pylinac trên staging

- **Ngày kiểm chứng:** 2026-09-15
- **Mã nguồn staging:** `ffad35305fa8a30d33ec052a793d85b0a28112d4`
- **Lược đồ API:** `20260914_0023`
- **Môi trường:** staging, hồ sơ tổng hợp không chứa dữ liệu người bệnh
- **Phạm vi:** kiểm chứng giao diện cổng đầu vào trên trang bài **Kiểm tra sao**

## Quan sát

1. Danh mục QA mở được bài **Kiểm tra sao** và trang chuyên biệt hiển thị đúng
   khu vực tệp đầu vào.
2. Trang hiển thị phần **Kiểm tra đầu vào** với thông báo mọi tệp phải được
   kiểm tra hợp lệ trước khi gọi Pylinac.
3. Tệp hiện có `gamma-rtdose-v1-smoke.dcm` được hiển thị là **Hợp lệ**; nút
   kiểm tra lại chuyển sang trạng thái đã hợp lệ.
4. Khu vực lịch sử hiển thị chưa có kết quả, đúng với trạng thái hồ sơ trước
   khi chạy bài.
5. Không có mã hồ sơ, mã tệp hoặc dữ liệu JSON được hiển thị trong giao diện.

## Giới hạn của bằng chứng

Tệp hiện có là RTDOSE tổng hợp dùng cho kiểm thử dữ liệu liều, không phải ảnh
Starshot. Vì vậy không bấm **Bắt đầu phân tích** trong lần kiểm chứng này để
không tạo một lượt Pylinac sai loại. Bằng chứng này chỉ đóng lát cắt giao diện
và trạng thái `VALID`; nó không đóng chạy engine Starshot, fixture đại diện,
đối chiếu độc lập hoặc nghiệm thu toàn bộ P7 trên staging.

## Đối chiếu triển khai

Bộ xác minh công khai `scripts/verify-public-deployment.ps1` chạy sau cùng một
commit đạt **16/16**, API và giao diện cùng nhận mã nguồn nêu trên, API sẵn sàng
và lược đồ đúng. Đây là bằng chứng parity/runtime, không phải tuyên bố sẵn sàng
lâm sàng.
