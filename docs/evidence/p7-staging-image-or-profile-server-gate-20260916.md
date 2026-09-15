# P7-W03 — cổng máy chủ cho bài ảnh hoặc biên dạng — staging — 2026-09-16

## Phạm vi

Bảo đảm máy chủ không chỉ dựa vào bộ lọc của giao diện. Hai bài **Phân tích biên dạng trường** có hồ sơ đầu vào `IMAGE_OR_PROFILE`; khi một tệp RTDOSE, RTSTRUCT hoặc RTPLAN đã ở trạng thái hợp lệ nhưng được gửi vào bài này, máy chủ phải từ chối trước khi gọi Pylinac.

## Bản phát hành

- Nhánh: `codex/p4-org-site-machine`
- Mã nguồn API: `3348524e5b98f1462f19450bfe3db9620f053cb1`
- Triển khai API: `SUCCESS`
- Lược đồ cơ sở dữ liệu: `20260914_0023`

## Bằng chứng kiểm tra

- API `health`: `200`, trạng thái hoạt động.
- API `ready`: `200`, trạng thái sẵn sàng.
- API `version`: trả đúng mã nguồn `3348524` và môi trường `staging`.
- Kiểm tra công khai staging: đạt toàn bộ, `failed_check_count=0`.
- Kiểm tra toàn bộ API cục bộ: đạt, không có kiểm thử thất bại.
- Kiểm thử riêng Pylinac: `49/49` đạt.
- Ruff: đạt.

## Hành vi được bảo vệ

- Tệp sai loại bị chặn bằng lỗi `PYLINAC_INPUT_PROFILE_MISMATCH` trước khi gọi engine.
- Không tạo lượt lịch sử mới khi đầu vào sai loại.
- Quy tắc áp dụng cho Starshot, các bài ảnh, bài chuỗi ảnh, bài hạt nhân và cả hai bài `IMAGE_OR_PROFILE`.
- Tệp đã tải và hồ sơ thử nghiệm `dailyQA` không bị sửa hoặc xóa trong kiểm tra.

## Kết luận

Cổng tương thích đầu vào hiện được bảo vệ ở cả giao diện và máy chủ. Đây là một phần của P7-W03; P7 vẫn chưa đóng vì còn cần ma trận fixture đại diện, đối chiếu độc lập, xác nhận chuyên môn, báo cáo PDF và VERIFY/HANDOFF.
