# P7-W03 — triển khai cổng xác thực đầu vào trên staging

Ngày kiểm tra: 2026-09-15  
Mã nguồn kỳ vọng: `783f8b5dd34ebf6963d864db78f5d4aac6cdc4f2`  
Lược đồ kỳ vọng: `20260914_0023`  
API: `https://gleaming-cooperation-staging.up.railway.app`  
Web: `https://rt-connect-web-staging-staging.up.railway.app`

## Kết quả kiểm tra công khai

- Bộ kiểm tra exact-SHA đạt **16/16**, không có kiểm tra thất bại.
- API trả `health=ok`, `ready=ready`, đúng mã nguồn kỳ vọng và đúng lược đồ `20260914_0023`.
- OpenAPI vẫn có tuyến xem trước CT và các tuyến thành viên/lời mời tổ chức.
- Các tuyến thành viên/lời mời khi chưa xác thực hoặc dùng mã không hợp lệ đều trả `401`.
- Web trả `200 OK`; gói giao diện tải được, có dấu hiệu của chức năng xem trước CT và luồng thành viên/lời mời; dấu hiệu phiên bản kỳ vọng có trong gói.

## Phạm vi và giới hạn

Đây là bằng chứng API/web/phiên bản trên staging sau khi nhánh được triển khai tự động. Nó xác nhận mã sửa cổng `data_status=VALID` đã tới staging, nhưng chưa chứng minh người dùng đã chạy thành công từng bài Pylinac với tệp thật trên staging. Còn cần kiểm chứng đăng nhập, tải–kiểm tra–phân tích theo từng nhóm bài, fixture chuẩn/commissioning, đối chiếu độc lập và các cổng VERIFY/HANDOFF của P7.
