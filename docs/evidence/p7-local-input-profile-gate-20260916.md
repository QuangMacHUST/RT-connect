# P7-W03 — cổng tương thích loại đầu vào Pylinac — 2026-09-16

## Vấn đề được phát hiện

Ở bài **Kiểm tra sao**, giao diện trước đây chỉ lọc theo loại lưu trữ `DICOM` hoặc `IMAGE`. Vì vậy một tệp RTDOSE đã được kiểm tra hợp lệ vẫn có thể xuất hiện như ảnh đầu vào, dù không phải ảnh phân tích của Starshot.

## Thay đổi

- Máy chủ bổ sung cổng tương thích loại đầu vào sau bước kiểm tra `VALID`.
- Các bài ảnh, cặp ảnh, chuỗi ảnh, chuỗi DICOM và bài hạt nhân từ chối RTDOSE, RTSTRUCT, RTPLAN và số đo.
- Giao diện dùng cùng quy tắc để không đưa các tệp đó vào danh sách chọn ảnh.
- Nếu một trình duyệt cũ vẫn gửi lựa chọn sai, máy chủ trả lỗi `PYLINAC_INPUT_PROFILE_MISMATCH` trước khi gọi Pylinac và không tạo lượt lịch sử.

## Kiểm thử

- API: trường hợp tệp RTDOSE đã `VALID` nhưng chọn cho Starshot bị chặn; engine không được gọi; lịch sử vẫn bằng 0.
- Ma trận lỗi Pylinac và các kiểm thử API liên quan: **49/49 đạt**.
- Giao diện: kiểm thử toàn bộ **50/50 đạt**; kiểm thử nhãn và bộ lọc loại đầu vào xác nhận RTDOSE/RTSTRUCT/RTPLAN không được coi là ảnh Pylinac.
- Lint và kiểm tra kiểu giao diện đạt.

## Giới hạn

Đây là kiểm thử local cho cổng tương thích loại tệp. Cần triển khai exact-SHA lên staging, mở lại bài Starshot có tệp RTDOSE hiện có để xác nhận tệp không còn trong danh sách, sau đó mới kiểm tra bằng ảnh Starshot đại diện. Không dùng bằng chứng này để tuyên bố P7 đã nghiệm thu lâm sàng.

Không có dữ liệu staging nào bị xóa; hồ sơ `dailyQA`, lịch sử liên quan và xu hướng được giữ nguyên.
