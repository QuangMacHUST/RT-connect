# Bằng chứng P7 — Winston–Lutz nhiều bi với bộ mẫu chính thức

Ngày kiểm tra: 2026-09-16  
Phạm vi: kiểm tra đường chạy bộ điều hợp Pylinac local, không phải nghiệm thu lâm sàng.

## Kết quả

- Tệp mẫu: `SNC_MTWL_demo.zip`, bộ mẫu chính thức đi kèm Pylinac 3.47.0.
- Dữ liệu đầu vào: 19 ảnh DICOM, cấu hình 6 bi chuẩn theo `BBArrangement.DEMO` của Pylinac.
- Đường chạy: `execute_pylinac("WINSTON_LUTZ_MULTI_TARGET", ...)` → `WinstonLutzMultiTargetMultiField` → `from_zip()` → `analyze()`.
- Kết quả cấu trúc: 14 nhóm chỉ số, có `bb_arrangement`, vector dịch chuyển bi, sai lệch trường–bi lớn nhất/trung bình/trung vị và chi tiết từng ảnh.
- Ảnh minh họa: tạo thành công ảnh PNG overlay, kích thước 278.462 byte trong lần chạy kiểm tra trực tiếp.
- Ma trận hồi quy tệp mẫu chính thức: **37/37** trường hợp đạt.

## Ý nghĩa đối với sản phẩm

RT-CONNECT đã chứng minh được đường chạy thật của bài Winston–Lutz nhiều bi bằng dữ liệu chính thức của Pylinac. Giao diện RT-CONNECT vẫn chịu trách nhiệm thu thập cấu hình bi, trường, tọa độ và các lựa chọn phân tích; Pylinac chịu trách nhiệm đọc ảnh, phân tích và trả kết quả/ảnh minh họa.

## Giới hạn còn mở

- Chưa phải đối chiếu độc lập từng chỉ số với phần mềm chuẩn hoặc phép tính do chuyên gia vật lý y khoa xác nhận.
- Chưa kiểm chứng ánh xạ góc thủ công theo từng ảnh và trường hợp dữ liệu thực tế của từng máy.
- Chưa kiểm chứng thao tác tương ứng trên staging với bộ dữ liệu được phê duyệt.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa bất kỳ hồ sơ staging nào; hồ sơ `dailyQA` được giữ nguyên.

Vì vậy, bằng chứng này chỉ cập nhật độ bao phủ fixture của P7-W03; không đánh dấu hoàn thành P7 hoặc thay thế bước kiểm định chuyên môn.
