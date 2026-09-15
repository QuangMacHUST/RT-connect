# Bằng chứng P17 — nhãn kết quả DVH trên staging

## Phạm vi

Kiểm tra chỉ đọc trên staging sau khi triển khai bản `3833783`. Mục tiêu là xác nhận lớp trình bày DVH không đưa mã kỹ thuật hoặc tên tệp ra cho người dùng. Không tạo kết quả mới, không tải lên tệp mới và không xóa hoặc sửa hồ sơ nào; hồ sơ `dailyQA` và toàn bộ dữ liệu liên quan được giữ nguyên.

## Kiểm tra công khai

- Giao diện staging: `https://rt-connect-web-staging-staging.up.railway.app/` trả HTTP 200.
- Gói giao diện tải thành công và chứa các nhãn nghiệp vụ `Tệp liều RTDOSE`, `Tải bảng số liệu` và `Lần tính`.
- API readiness: `https://gleaming-cooperation-staging.up.railway.app/api/v1/ready` trả HTTP 200, trạng thái `ready`, lược đồ `20260914_0023`.
- Deployment giao diện Railway: `242a008c-2703-4220-b66a-5dddb586b1ad`, trạng thái `SUCCESS`.

## Kiểm tra bằng trình duyệt đã đăng nhập

Trên hồ sơ DVH staging `P6 Staging Upload Smoke`, màn hình hiển thị:

- `Tệp liều RTDOSE 1/2` cho dữ liệu liều.
- `Cấu trúc RT` cho cấu trúc.
- `Ảnh CT` cho lớp phủ giải phẫu tùy chọn.
- `Vùng số 1 · 1 đường viền` cho vùng cấu trúc.
- `Tải bảng số liệu` thay cho nút xuất JSON/CSV kỹ thuật.
- `Lần tính 1`, `Lần tính 2`, `Đủ vùng tính` và `Đã ghi nhận` trong lịch sử.
- Kết quả giới hạn dùng `Cần xem lại`, `D95`, `Thư viện sinh học` và không hiển thị mã nguồn giới hạn.

Không còn thấy trong cây truy cập của màn hình: mã lượt tính, dấu vết đầu vào, chuỗi băm, mã nguồn giới hạn, tên tệp gốc hoặc nút `JSON`. Các mã định danh vẫn được giữ trong dữ liệu nội bộ để mở đúng kết quả và bảo toàn provenance; chúng không được trình bày cho người dùng.

## Ranh giới nghiệm thu

Đây là bằng chứng parity giao diện của lát cắt P17. Nó không đóng P17-VERIFY/HANDOFF và không thay thế kiểm chứng engine DVH, kiểm tra hình học/ROI, HI/CI, tải lớn, tính bền vững kết quả hoặc xuất báo cáo PDF.
