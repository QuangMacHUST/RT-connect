# P7-W03 — Ma trận độ phủ bộ mẫu Pylinac

- **Môi trường:** local
- **Thời điểm:** 2026-09-16
- **Phiên bản engine:** Pylinac 3.47.0
- **Phạm vi:** toàn bộ 63 capability được registry đăng ký.
- **Kiểm thử:** `tests/test_pylinac_registry.py` — đạt toàn bộ 8 ca.
- **Rà soát mã:** Ruff đạt trên ma trận, registry và test.

## Phân loại hiện tại

| Trạng thái | Số capability | Ý nghĩa |
| --- | ---: | --- |
| Mẫu chính thức | 37 | Đã có tệp mẫu trong gói Pylinac và đã chạy qua bộ chuyển đổi tương ứng. |
| Mẫu tổng hợp kiểm hợp đồng | 13 | Chỉ xác nhận đường chạy, ánh xạ tham số/kết quả và giới hạn giao diện; không thay thế commissioning. |
| Cần commissioning | 13 | Chưa có bộ tệp hoặc số đo được phê duyệt trong môi trường hiện tại; không được coi là đã nghiệm thu. |

## Điều đã kiểm chứng

1. Mọi capability trong `RUNTIME_BINDINGS` đều có đúng một trạng thái bộ mẫu, tên tham chiếu và ghi chú giới hạn.
2. Registry phát hiện danh mục thiếu hoặc thừa bằng phép đối chiếu khóa; không tự gán mặc định im lặng.
3. Registry summary trả trạng thái bộ mẫu cho từng capability và tổng số theo ba nhóm.
4. Bài có mẫu tổng hợp vẫn được đánh dấu rõ là tổng hợp; dữ liệu này không được dùng để tuyên bố đã sẵn sàng lâm sàng.
5. Nhóm còn thiếu gồm các lớp cần dữ liệu riêng như CatPhan 700, ACR, CIRS 062M, GE Helios, Trajectory Log 3/4 và các số đo hiệu chuẩn; đây là công việc tiếp theo của P7-W03.

## Giới hạn

Ma trận này là cổng quản lý độ phủ kiểm thử, không phải bằng chứng commissioning, đối chiếu độc lập hay nghiệm thu lâm sàng. P7-W03 vẫn mở cho fixture đại diện, oracle độc lập, ma trận lỗi đặc trưng và kiểm chứng staging.
