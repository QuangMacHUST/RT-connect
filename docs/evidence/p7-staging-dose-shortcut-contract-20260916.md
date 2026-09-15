# P7-W04 — phân tích liều chỉ hiện với bài có hợp đồng liều trên staging

**Ngày kiểm tra:** 2026-09-16  
**Môi trường:** staging  
**Mã nguồn web:** `e647840` — `fix: only expose dose analysis for dose QA`  
**Phạm vi:** kiểm tra giao diện chỉ đọc; không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ.

## Mục tiêu

Nút mở không gian phân tích liều chỉ được hiển thị khi loại bài QA đang mở có hợp đồng đầu vào liều. Không suy luận từ việc hồ sơ tình cờ có thêm tệp RTDOSE hoặc RTSTRUCT phục vụ bài khác.

## Kết quả kiểm tra

1. Mở khu vực **Kiểm tra chất lượng máy**: danh mục hiển thị `64/64` bài.
2. Chọn hồ sơ **P11 E2E Synthetic QA 20260910 B7C3**, loại **Kiểm tra sao**:
   - Khu vực **Tệp đầu vào** vẫn hiển thị vì bài Starshot cần ảnh.
   - Nút **Mở phân tích liều cho bài này** không xuất hiện.
   - Tệp RTDOSE đã có trong hồ sơ không làm thay đổi điều kiện hiển thị.
3. Chọn hồ sơ **P6 Staging Upload Smoke**, loại **Phân tích Gamma PSQA hai chiều**:
   - Nút **Mở phân tích liều cho bài này** xuất hiện.
   - Hướng dẫn yêu cầu một RTDOSE và một RTSTRUCT được hiển thị.
   - Trạng thái kiểm tra tệp được hiển thị trong cùng khu vực.

## Kết luận

Hợp đồng hiển thị đã đúng với nghiệp vụ: bài QA hình ảnh như Starshot không mở nhầm phân tích liều, còn PSQA vẫn giữ đúng lối vào phân tích liều. Thay đổi chỉ ảnh hưởng điều kiện hiển thị phía web; không thay đổi dữ liệu QA staging.

## Giới hạn còn lại

Đây là kiểm tra điều kiện hiển thị trên staging, chưa đóng P7-W04. Vẫn còn cần kiểm thử ROI chuyên biệt, ánh xạ tọa độ theo từng ảnh của bài nhiều ảnh, lựa chọn ảnh ngoài giới hạn xem trước và nghiệm thu đầy đủ các bài Pylinac.
