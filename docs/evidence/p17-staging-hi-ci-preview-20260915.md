# P17 — bản xem trước HI/CI trên staging

Ngày kiểm tra: 2026-09-15  
Môi trường: staging  
Phạm vi: kiểm tra giao diện và tuyến xem trước DVH; không phải nghiệm thu lâm sàng.

## Bản triển khai

- Bản web sửa thứ tự ưu tiên kết quả xem trước: `e7b3150`; bản tiếp theo sửa nhãn và nguồn hiển thị của trạng thái chưa lưu: `8324540`.
- Bản máy chủ chứa bộ tính HI/CI: `319da9c`.
- Triển khai web Railway: `be7f670f-033d-44c6-8fa3-8df7ce7deeb8`, trạng thái `SUCCESS`.
- Tuyến sẵn sàng máy chủ trả HTTP 200, lược đồ `20260914_0023`.
- Trang DVH staging trả HTTP 200.

## Thao tác đã kiểm tra

1. Mở hồ sơ thử nghiệm tổng hợp đã có RTDOSE và RTSTRUCT hợp lệ.
2. Chọn “Chỉ số phù hợp RTOG ở mức 95%”.
3. Nhập liều kê đơn `6 Gy`, phù hợp với khoảng liều của fixture.
4. Bấm “Kiểm tra và xem trước”, không bấm “Tính và lưu kết quả”.

## Kết quả quan sát được

- Hiển thị thông báo “Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.”
- Khu vực “CHỈ SỐ KẾ HOẠCH” hiển thị “Chỉ số phù hợp RTOG ở mức 95%”, giá trị `0,7500` và trạng thái “Đã tính”.
- Bản xem trước mới được hiển thị dù hồ sơ đã có kết quả DVH lưu trước đó.
- Khu vực kết quả hiển thị rõ “Bản xem trước · chưa lưu”; khu vực nguồn hiển thị “Bản xem trước chưa lưu” và nói rõ chưa tạo lần tính mới. Thời điểm của kết quả cũ không còn bị trình bày như thời điểm của bản xem trước.
- Lịch sử vẫn hiển thị đúng 2 lần tính cũ; thao tác xem trước không tạo thêm lần tính.
- Không hiển thị mã công thức, mã lượt tính, chuỗi băm, tên tệp kỹ thuật hoặc dữ liệu JSON.
- Với liều kê đơn `60 Gy`, giao diện trả “Chưa đủ dữ liệu” vì fixture không có thể tích liều 95% lớn hơn 0; hệ thống không suy đoán giá trị. Đây là kiểm tra lỗi dữ liệu hợp lệ, không phải lỗi triển khai.

## Kiểm tra mã nguồn trước khi triển khai

- Kiểm thử giao diện: `46/46` đạt.
- Kiểm tra lint: đạt.
- Kiểm tra kiểu: đạt.
- Bản dựng giao diện: đạt; cảnh báo kích thước gói lớn hơn 500 kB vẫn là cảnh báo tối ưu hóa, không phải lỗi bản dựng.
- Kiểm tra khoảng trắng thay đổi: đạt.

## Giới hạn và bước còn mở

- Đây là fixture tổng hợp trên staging, chưa phải xác nhận dữ liệu lâm sàng.
- Cần đối chiếu với một oracle độc lập đã được phê duyệt và xác nhận với physicist cách xác định thể tích liều 95% cho CI.
- Cần bổ sung nguồn tiêu chí theo bệnh cảnh, phác đồ và phiên bản tài liệu trước khi đánh giá đạt/không đạt.
- P17-VERIFY và P17-HANDOFF vẫn mở.
- Hồ sơ `dailyQA`, lịch sử kết quả, tệp liên quan và điểm xu hướng không bị xóa hoặc thay đổi trong lần kiểm tra này.
