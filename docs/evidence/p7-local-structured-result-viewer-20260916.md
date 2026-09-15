# P7-W04 — Trình xem nhóm chỉ số Pylinac

- **Môi trường:** local
- **Thời điểm:** 2026-09-16
- **Phạm vi:** hiển thị kết quả lồng nhau trong `result_snapshot.metrics` bằng nhóm và dòng dễ đọc.
- **Bài kiểm thử riêng:** `npm.cmd test -- src/pages/MachineQAPage.test.tsx` — **9/9 đạt**.
- **Hồi quy giao diện:** `npm.cmd test -- --run` — **58/58 đạt**.
- **Kiểm tra bổ sung:** `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run build` — đều đạt.

## Điều đã kiểm chứng

1. Nhóm chỉ số lồng nhau được hiển thị bằng nhãn dễ đọc, không buộc người dùng xem cấu trúc kỹ thuật.
2. Giá trị số được định dạng theo tiếng Việt và các nhóm mảng/đối tượng được trình bày thành các dòng hoặc thẻ dễ quét.
3. Các trường tên tệp, mã hồ sơ, mã lượt chạy, mã đối tượng, mã bệnh nhân và đường dẫn không được hiển thị.
4. Bảng chuyên biệt Winston–Lutz nhiều bi vẫn được dùng riêng; nhóm `image_details` và `bb_arrangement` được loại khỏi phần hiển thị chung để không lặp lại.
5. Thành phần chỉ đọc kết quả đã lưu; không có phép tính hoặc ghi dữ liệu mới ở trình xem.

## Giới hạn

Đây là kiểm chứng giao diện local, chưa phải bằng chứng staging hoặc nghiệm thu lâm sàng. Các cổng còn mở của P7 gồm fixture commissioning cho những lớp còn thiếu, đối chiếu độc lập từng chỉ số, ROI chuyên biệt, ánh xạ tọa độ đa ảnh, kiểm chứng tương tác trên staging và VERIFY/HANDOFF.
