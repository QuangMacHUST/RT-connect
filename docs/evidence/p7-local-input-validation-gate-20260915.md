# P7-W03 — cổng tệp đã kiểm tra trước khi chạy Pylinac

Ngày kiểm tra: 2026-09-15  
Phạm vi: `PylinacQARun` và luồng giao diện QA máy  
Phiên bản bộ tính: Pylinac 3.47.0

## Kết quả

| Trường hợp | Kết quả mong đợi | Kết quả thực tế |
| --- | --- | --- |
| Tệp DICOM đã qua kiểm tra và có trạng thái `VALID` | Được tạo lượt chạy và gọi engine | Đạt; lượt chạy lưu kết quả và ảnh minh họa |
| Tệp còn `UPLOADED`/chưa kiểm tra | Dừng trước khi gọi engine, không tạo lượt chạy | Đạt; trả `PYLINAC_INPUT_NOT_VALIDATED` |
| Bài hiệu chuẩn không có tệp | Vẫn nhận số đo và gọi engine | Đạt; kiểm thử hồi quy không bị ảnh hưởng |
| Tệp ZIP chứa chuỗi DICOM | Kiểm tra được container và ít nhất một thành viên DICOM đọc được | Đạt; ZIP hợp lệ chuyển sang `VALID` |
| Tệp ảnh PNG/JPEG/TIFF hoặc DICOM ảnh | Kiểm tra được header/kích thước tối thiểu trước khi chạy | Đạt; ảnh hợp lệ chuyển sang `VALID` |
| Tệp nhật ký máy `.dlg`/`.bin`/`.tlog`/`.txt` | Kiểm tra phần mở rộng và nội dung không rỗng | Đạt; nhật ký hợp lệ chuyển sang `VALID` |

## Lệnh kiểm tra

```text
apps/api/.venv/Scripts/python.exe -m pytest -q tests/test_pylinac_qa.py -k "persists_input_result_overlay or rejects_unvalidated_input or calibration_run"
apps/api/.venv/Scripts/python.exe -m pytest -q tests/test_artifacts.py -k "pylinac_container_image_and_log_inputs"
apps/api/.venv/Scripts/python.exe -m ruff check src/rt_connect_api/api/pylinac_qa.py tests/test_pylinac_qa.py
apps/api/.venv/Scripts/python.exe -m pytest -q
apps/web/npm.cmd run typecheck
apps/web/npm.cmd run lint
apps/web/npm.cmd run test -- --run
apps/web/npm.cmd run build
```

Kết quả: kiểm thử mục tiêu Pylinac **3/3**, kiểm thử đường xác thực ZIP/ảnh/nhật ký **1/1**, toàn bộ kiểm thử API đạt, giao diện **12/12 tệp và 40/40 kiểm thử**, kiểm tra kiểu/lint/bản dựng đạt. Bản dựng vẫn có cảnh báo kích thước gói JavaScript đã biết.

## Giới hạn

Cổng này chứng minh dữ liệu chưa kiểm tra không thể đi vào engine và các dạng đầu vào mà giao diện Pylinac đang dùng có đường xác thực tương ứng. Kiểm tra ảnh/ZIP hiện là preflight tối thiểu về định dạng, khả năng đọc và kích thước; Pylinac vẫn chịu trách nhiệm phân tích nội dung và RT-CONNECT không tự tính lại chỉ số. Cổng này chưa thay thế fixture chuẩn hoặc commissioning, đối chiếu độc lập từng chỉ số, kiểm thử lỗi nội dung DICOM và kiểm chứng trên staging; vì vậy không đóng P7.
