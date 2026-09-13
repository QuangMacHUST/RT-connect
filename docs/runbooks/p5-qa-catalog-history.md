# Phiếu kiểm chứng P5 — danh mục QA và lịch sử

## Mục đích

Kiểm tra trên staging rằng người dùng có thể bắt đầu bài từ danh mục, xem lại hồ sơ cũ, lưu trữ/khôi phục và chỉ xóa vĩnh viễn khi không còn kết quả, tệp hoặc báo cáo liên quan.

P5 chỉ được đóng sau khi có bằng chứng staging. Việc danh mục hiển thị đủ bài pylinac không có nghĩa mọi bài đã có bộ tích hợp chạy được.

## Chuẩn bị

1. Dùng một tổ chức staging đã có ít nhất một cơ sở, một máy đang hoạt động và một thành viên.
2. Không dùng dữ liệu người bệnh thật. Chỉ dùng dữ liệu tổng hợp hoặc số đo đã được cho phép.
3. Ghi lại mã bản dựng ở trang trạng thái hệ thống, không chụp hoặc sao chép bí mật truy cập.

## Kiểm tra giao diện

### Danh mục và bắt đầu bài

1. Mở **Kiểm tra chất lượng máy**.
2. Xác nhận danh mục có các nhóm bài nhập số đo, hình ảnh, liều và các nhóm pylinac khác; không hiển thị chuỗi JSON hay mã kỹ thuật trong nội dung dành cho người dùng.
3. Chọn bài **Nhập số đo kiểm tra máy**, chọn cơ sở, máy, thư mục tùy chọn, nhập tên và thời điểm rồi bấm **Bắt đầu bài kiểm tra**.
4. Bấm lại khi mạng chậm hoặc tải lại trang; chỉ có một hồ sơ được tạo.
5. Chọn một bài đang chuẩn bị; nút bắt đầu phải bị khóa và phải nói rõ bài chưa sẵn sàng, không được báo đã phân tích.

### Lịch sử, hồ sơ cũ và thư mục

1. Mở hồ sơ vừa tạo từ lịch sử và xác nhận tên bài, loại bài, chu kỳ, thời điểm, cơ sở và máy vẫn đúng.
2. Đổi tên thư mục hoặc chuyển thư mục; mở lại hồ sơ và xác nhận hồ sơ không đổi.
3. Nếu có hồ sơ cũ chưa phân loại, chọn loại bài phù hợp từ danh sách; không được tự gắn loại nếu người dùng chưa chọn.

### Lưu trữ, khôi phục và xóa vĩnh viễn

1. Lưu trữ một hồ sơ không có kết quả/tệp/báo cáo liên quan; hồ sơ biến mất khỏi danh sách thường và xuất hiện trong thùng rác.
2. Khôi phục hồ sơ; hồ sơ xuất hiện lại trong lịch sử.
3. Lưu trữ rồi xóa vĩnh viễn hồ sơ không có liên kết; giao diện báo đã xóa và hồ sơ không còn trong thùng rác.
4. Với hồ sơ có kết quả, tệp, báo cáo hoặc xu hướng, thử xóa vĩnh viễn; hệ thống phải từ chối, nêu lý do dễ hiểu và không xóa dữ liệu liên quan.
5. Thử bấm lưu trữ, khôi phục và xóa vĩnh viễn hai lần; lần sau phải an toàn, không tạo bản ghi hoặc thông báo sai.

## Kiểm tra lỗi bắt buộc

- Mất mạng sau khi bấm bắt đầu: tải lại không tạo hồ sơ trùng.
- Mất mạng khi lưu trữ/khôi phục: hiển thị trạng thái chưa chắc chắn, tải lại để đối chiếu, không tự báo thành công.
- Hai cửa sổ cùng thao tác với một hồ sơ: không được làm mất cập nhật của cửa sổ còn lại.
- Hồ sơ thuộc tổ chức khác: không được đọc, sửa, lưu trữ hoặc xóa.
- Máy hoặc thư mục đã lưu trữ: không cho tạo bài mới vào đó.
- Có tác vụ nền đang chạy: phải từ chối hoặc dừng theo chính sách đã công bố; không để tác vụ tự hồi sinh hồ sơ đã xóa.

## Điều kiện đạt

- Tất cả kiểm tra trên có kết quả và ảnh chụp màn hình không chứa dữ liệu người bệnh, bí mật truy cập hoặc mã nội bộ.
- Có bản ghi API/readiness cùng bản dựng với giao diện.
- Không có mất tệp, kết quả, báo cáo, xu hướng hoặc thay đổi chéo tổ chức.
- Gửi bằng chứng cho người phụ trách dự án để cập nhật P5-VERIFY và P5-HANDOFF; khi đó mới mở P6.
