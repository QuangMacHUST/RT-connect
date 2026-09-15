# Bằng chứng P7/P8 — nhãn dữ liệu QA theo ngôn ngữ người dùng

## Phạm vi

Lát cắt này tiếp tục P7/P8 sau khi tạm dừng hướng xóa vĩnh viễn hồ sơ. Không hồ sơ, kết quả, tệp đầu vào hoặc điểm xu hướng nào bị xóa hay thay đổi.

## Thay đổi

- Bổ sung bộ quy tắc nhãn dùng chung cho dữ liệu QA: số đo, tệp liều RTDOSE, cấu trúc RT, ảnh CT, kế hoạch xạ trị, bộ ảnh nhiều lớp, nhật ký máy, ảnh DICOM và ảnh kiểm tra.
- Các trang Picket Fence, Starshot, Winston–Lutz, Winston–Lutz nhiều bi, VMAT, phân tích trường, CatPhan, bài hạt nhân, bài đóng góp và ảnh phẳng chỉ hiển thị nhãn nghiệp vụ.
- Kho lưu trữ QA không còn hiển thị tên tệp gốc hoặc dung lượng kỹ thuật trong bảng tệp; hàng đợi tải lên hiển thị “Tệp được chọn” theo thứ tự.
- Màn hình DVH không còn hiển thị tên tệp, chuỗi băm hoặc mã kỹ thuật khi chọn RTDOSE, RTSTRUCT và CT.
- Tên tệp vẫn được giữ trong dữ liệu nội bộ để lọc đúng loại đầu vào và phục vụ bộ tính Pylinac; thay đổi này chỉ tác động lớp trình bày.

## Kiểm chứng cục bộ

- Kiểm thử giao diện: **43/43**.
- Lint: đạt.
- Kiểm tra kiểu TypeScript: đạt.
- Bản dựng sản xuất: đạt.
- Có kiểm thử riêng bảo đảm nhãn không làm lộ chuỗi `json` hoặc tên tệp kỹ thuật.

## Ranh giới nghiệm thu

Đây là lát cắt UX cục bộ. Cần triển khai giao diện lên staging và kiểm tra bằng trình duyệt với các nhóm bài có tệp thật trước khi ghi nhận parity staging. P7/P8 và cổng VERIFY/HANDOFF vẫn chưa hoàn tất.
