# P7-W03 — hợp đồng hồ sơ đầu vào theo liên kết chạy thật — staging — 2026-09-16

## Mục tiêu

Bảo đảm cổng kiểm tra đầu vào của máy chủ dùng đúng `input_profile` của liên kết Pylinac đang chạy, không chỉ dựa vào `input_kind` của danh mục giao diện. Khi danh mục và bộ điều hợp bị sửa lệch, kiểm thử phải phát hiện trước khi bản phát hành được chấp nhận.

## Bản phát hành

- Nhánh: `codex/p4-org-site-machine`
- Mã nguồn: `dee1b679f9ed349c11198c6a37e89c27b3a7921f`
- Triển khai API: `65c84afd-e083-4ac1-9dc3-5ce68ea4d847`, `SUCCESS`
- Triển khai giao diện: `5e642c30-7e8a-4bfa-a827-a5e001e1319b`, `SUCCESS`
- Phiên bản Pylinac khóa: `3.47.0`
- Số liên kết khả dụng: `63/63`
- Lược đồ cơ sở dữ liệu: `20260914_0023`

## Kết quả kiểm tra

- Kiểm tra hồ sơ đầu vào giữa danh mục và liên kết chạy thật: `0` sai lệch.
- Kiểm tra inventory biểu tượng công khai của Pylinac: đạt, không thiếu, không thừa, không có biểu tượng chưa gắn liên kết.
- Kiểm thử tập trung registry và Pylinac: đạt toàn bộ.
- Kiểm thử API toàn bộ: chạy đến `100%`, không có lỗi.
- Ruff: đạt.
- Kiểm tra hợp đồng kế hoạch: `passed=true`, `phase_count=21`, `acceptance_scenario_count=264`, `failed_check_count=0`.
- Kiểm tra công khai sau triển khai: `passed=true`, `failed_check_count=0`; health, ready, version, OpenAPI, biên giới xác thực, trang web và gói giao diện đều đạt.

## Hành vi được bảo vệ

- Bài ảnh, chuỗi ảnh, chuỗi DICOM và bài hạt nhân sử dụng đúng hồ sơ đầu vào chạy thật để từ chối RTDOSE, RTSTRUCT, RTPLAN hoặc số đo trước khi gọi Pylinac.
- Bài hiệu chuẩn và bài biên dạng không bị áp quy tắc ảnh không phù hợp với hồ sơ riêng của chúng.
- Không tạo lượt chạy, không tạo lịch sử mới và không thay đổi tệp khi đầu vào bị từ chối.
- Hồ sơ `dailyQA`, lịch sử QA, tệp liên quan và điểm xu hướng được giữ nguyên; không thực hiện xóa vĩnh viễn.

## Kết luận

Cổng hợp đồng hồ sơ đầu vào đã được bảo vệ ở danh mục, registry và API, đồng thời đã lên staging đúng mã nguồn. Đây là một phần của P7-W03; P7 vẫn chưa đóng vì còn fixture đại diện/commissioning, đối chiếu độc lập từng chỉ số, kiểm lỗi đặc trưng, xác nhận chuyên môn, kiểm chứng tương tác đầy đủ và VERIFY/HANDOFF.
