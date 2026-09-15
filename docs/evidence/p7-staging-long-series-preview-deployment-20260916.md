# Bằng chứng triển khai P7-W04 — xem trước chuỗi DICOM dài trên staging — 2026-09-16

## Kiểm tra công khai chỉ đọc

- Bản phát hành `bef977739fcc32d472c5342c3905b6c9d32d755e` đã được Railway triển khai cho cả giao diện và máy chủ staging.
- `health` trả `200` với trạng thái hoạt động.
- `ready` trả `200` với trạng thái sẵn sàng và lược đồ `20260914_0023`.
- Phiên bản máy chủ nhận đúng `bef977739fcc32d472c5342c3905b6c9d32d755e`, môi trường `staging`.
- OpenAPI vẫn có tuyến xem trước ảnh và các tuyến thành viên/lời mời tổ chức.
- Các tuyến bảo vệ khi không có phiên xác thực đều trả `401`.
- Trang web và gói JavaScript tải thành công; kiểm tra công khai đạt **14/14**.

## Phạm vi an toàn

- Chỉ đọc trạng thái phát hành và giao diện QA; không tải lên tệp, không chạy phép phân tích, không tạo hồ sơ, không lưu trữ/khôi phục và không xóa `dailyQA`.
- Việc kiểm tra tệp ZIP 33 ảnh DICOM được thực hiện ở máy chủ cục bộ; staging chỉ xác nhận bản phát hành và hợp đồng tuyến. Cần một tệp được phê duyệt nếu muốn nghiệm thu tương tác chuỗi dài trực tiếp trên staging.
- Việc triển khai thành công không thay thế đối chiếu Pylinac, commissioning hoặc nghiệm thu lâm sàng.
