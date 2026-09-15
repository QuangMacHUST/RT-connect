# Bằng chứng P7/P8/P17 — nhãn dữ liệu QA theo ngôn ngữ người dùng

## Phạm vi

Lát cắt này tiếp tục P7/P8 sau khi tạm dừng hướng xóa vĩnh viễn hồ sơ. Không hồ sơ, kết quả, tệp đầu vào hoặc điểm xu hướng nào bị xóa hay thay đổi.

## Thay đổi

- Bổ sung bộ quy tắc nhãn dùng chung cho dữ liệu QA: số đo, tệp liều RTDOSE, cấu trúc RT, ảnh CT, kế hoạch xạ trị, bộ ảnh nhiều lớp, nhật ký máy, ảnh DICOM và ảnh kiểm tra.
- Các trang Picket Fence, Starshot, Winston–Lutz, Winston–Lutz nhiều bi, VMAT, phân tích trường, CatPhan, bài hạt nhân, bài đóng góp và ảnh phẳng chỉ hiển thị nhãn nghiệp vụ.
- Kho lưu trữ QA không còn hiển thị tên tệp gốc hoặc dung lượng kỹ thuật trong bảng tệp; hàng đợi tải lên hiển thị “Tệp được chọn” theo thứ tự.
- Màn hình DVH không còn hiển thị tên tệp, chuỗi băm hoặc mã kỹ thuật khi chọn RTDOSE, RTSTRUCT và CT.
- Màn hình kết quả DVH không còn hiển thị mã lượt tính, dấu vết đầu vào, chuỗi băm, mã nguồn giới hạn hoặc nút xuất JSON; người dùng chỉ thấy trạng thái, vùng, độ bao phủ, thời điểm và nút “Tải bảng số liệu”.
- Lịch sử DVH hiển thị theo “Lần tính 1”, “Lần tính 2” thay cho mã kỹ thuật; đánh giá giới hạn dùng nhãn nguồn tiếng Việt và không đưa mã nội bộ ra giao diện.
- Tên tệp vẫn được giữ trong dữ liệu nội bộ để lọc đúng loại đầu vào và phục vụ bộ tính Pylinac; thay đổi này chỉ tác động lớp trình bày.

## Kiểm chứng cục bộ

- Kiểm thử giao diện: **44/44**.
- Lint: đạt.
- Kiểm tra kiểu TypeScript: đạt.
- Bản dựng sản xuất: đạt.
- Có kiểm thử riêng bảo đảm nhãn không làm lộ chuỗi `json` hoặc tên tệp kỹ thuật.

## Ranh giới nghiệm thu

Đã triển khai lát cắt giao diện lên staging ở bản `3833783` và kiểm tra bằng trình duyệt có đăng nhập trên hồ sơ DVH staging. Bằng chứng chi tiết: [nhãn DVH trên staging](p17-staging-dvh-user-facing-labels-20260915.md). Đây chỉ là parity giao diện; P7/P8/P17 và các cổng VERIFY/HANDOFF vẫn chưa hoàn tất.
