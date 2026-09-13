# Kiểm chứng P4 trên môi trường thử với hai tài khoản

Tài liệu này là phiếu chạy cuối cho P4 — Đơn vị, cơ sở, thiết bị và thành viên. Mục tiêu là xác nhận cùng một đơn vị có thể được sử dụng bởi hai đồng nghiệp, không tạo ra phân cấp thao tác, đồng thời việc lưu trữ máy vẫn giữ nguyên lịch sử kiểm tra chất lượng.

Không ghi mã mời, mật khẩu, mã truy cập, mã hồ sơ hoặc ảnh có dữ liệu người bệnh vào phiếu này. Chỉ ghi tên hiển thị, kết quả đạt/không đạt và ảnh chụp đã che thông tin nhạy cảm.

## Chuẩn bị

- Địa chỉ web thử: `https://rt-connect-web-staging-staging.up.railway.app`
- Tài khoản A: thành viên hiện tại của đơn vị thử.
- Tài khoản B: một tài khoản Supabase khác, dùng email thật của người được mời; mở bằng hồ sơ trình duyệt riêng hoặc cửa sổ riêng tư.
- Đơn vị A có ít nhất một cơ sở, một máy đang sử dụng và một bài kiểm tra chất lượng cũ gắn với máy đó.
- Không chạy trên môi trường vận hành. Không xóa vĩnh viễn dữ liệu và không tải tệp người bệnh.

Nếu chưa có tài khoản B, dừng ở bước chuẩn bị. Không tự tạo tài khoản bằng mật khẩu tạm và không dùng chung phiên đăng nhập của tài khoản A, vì như vậy không chứng minh được kiểm tra hai danh tính.

## Trình tự kiểm chứng

### 1. Kiểm tra tài khoản A

1. Đăng nhập bằng tài khoản A và mở **Đơn vị và thiết bị**.
2. Xác nhận nhìn thấy tên đơn vị, cơ sở và máy đang sử dụng.
3. Mở **QA máy**, kiểm tra máy đang sử dụng có trong bộ chọn bài mới và bài kiểm tra cũ vẫn mở được từ lịch sử.
4. Chụp một ảnh toàn màn hình đã che email, mã mời và mọi dữ liệu nhạy cảm.

Kết quả đạt: tài khoản A nhìn thấy đúng đơn vị, máy đang sử dụng và lịch sử cũ.

### 2. Mời và kích hoạt tài khoản B

1. Từ tài khoản A, mở thẻ **Mời đồng nghiệp** và nhập email của tài khoản B.
2. Tạo lời mời một lần. Chuyển mã mời cho B qua kênh riêng; không đưa mã vào Git, nhật ký triển khai hoặc ảnh chụp.
3. Đăng nhập tài khoản B trong hồ sơ trình duyệt riêng.
4. Dùng mã mời để tham gia đơn vị.
5. Mở **Đơn vị và thiết bị**, **QA máy** và **Thư viện kiến thức**.

Kết quả đạt: B nhìn thấy cùng đơn vị, cơ sở và máy; không xuất hiện màn hình yêu cầu chọn vai trò bác sĩ/kỹ sư hay xin quyền thao tác.

### 3. Kiểm tra dùng chung thao tác

1. Tài khoản A và B cùng mở thẻ chỉnh sửa tên hiển thị của một máy, nhưng chưa bấm lưu.
2. A lưu trước một thay đổi dễ nhận biết, ví dụ thêm hậu tố `- A`.
3. B lưu bản đang dùng trước đó.
4. Xác nhận B nhận thông báo xung đột phiên bản; nội dung B đã nhập vẫn còn để đối chiếu hoặc nhập lại.
5. Tải lại dữ liệu và xác nhận chỉ bản đã lưu trước được giữ.
6. Đổi lại tên hiển thị về tên thử ban đầu.

Kết quả đạt: xung đột được thông báo rõ ràng, không ghi đè âm thầm và không mất nội dung đang nhập. Hai tài khoản vẫn có cùng các thao tác nghiệp vụ.

### 4. Kiểm tra lưu trữ máy và lịch sử

1. Từ tài khoản A, mở **Đơn vị và thiết bị**.
2. Chọn **Lưu trữ** trên máy thử và xác nhận hộp thoại cảnh báo.
3. Từ tài khoản B, mở **QA máy** và bắt đầu một bài mới.
4. Xác nhận máy đã lưu trữ không còn nằm trong danh sách máy được chọn cho bài mới.
5. Từ lịch sử, mở bài kiểm tra cũ gắn với máy đã lưu trữ.
6. Xác nhận bài cũ, kết quả và tệp của bài vẫn mở được.
7. Từ tài khoản B, khôi phục máy.
8. Mở lại luồng bắt đầu bài mới và xác nhận máy xuất hiện trở lại.

Kết quả đạt: lưu trữ chỉ ngăn bài mới dùng máy đó; không xóa lịch sử. Khôi phục yêu cầu thao tác rõ ràng và đưa máy trở lại bộ chọn.

### 5. Kiểm tra cơ sở lưu trữ, nếu có dữ liệu thử phù hợp

Chỉ thực hiện nếu đơn vị có cơ sở thử riêng.

1. Tạo hoặc chọn một cơ sở không chứa dữ liệu cần giữ.
2. Lưu trữ cơ sở sau khi xác nhận cảnh báo.
3. Xác nhận máy thuộc cơ sở không được dùng để tạo bài mới.
4. Xác nhận dữ liệu lịch sử vẫn có thể đọc.
5. Khôi phục cơ sở và xác nhận máy hoạt động trở lại theo đúng trạng thái trước đó.

Không dùng thao tác này trên cơ sở thật đang chứa dữ liệu vận hành nếu chưa có thống nhất riêng.

## Ma trận kết quả

| Mã kiểm | Nội dung | Kết quả mong đợi | Kết quả thực tế | Bằng chứng |
| :--- | :--- | :--- | :--- | :--- |
| P4-S01 | Tài khoản A mở đơn vị, cơ sở, máy và lịch sử | Đúng dữ liệu, không phải cuộn qua biểu mẫu dài |  |  |
| P4-S02 | Tài khoản B tham gia cùng đơn vị | Cùng thao tác, không có phân cấp vai trò |  |  |
| P4-E01 | Tên trống hoặc trùng | Báo lỗi, giữ nguyên biểu mẫu |  |  |
| P4-E02 | Hai tài khoản lưu cùng phiên bản | Báo xung đột, giữ nội dung đang nhập |  |  |
| P4-E03 | Lời mời hết hạn, đã dùng hoặc sai email | Báo đúng nguyên nhân, không tạo thành viên trùng |  |  |
| P4-E04 | Đổi đơn vị hoặc phiên hết hạn | Không lộ dữ liệu của đơn vị trước |  |  |
| P4-E05 | Lưu trữ máy/cơ sở | Bài mới bị chặn, lịch sử cũ vẫn đọc được |  |  |

## Điều kiện đạt P4

P4 chỉ được ghi **Hoàn thành** khi:

- P4-S01 và P4-S02 đạt trên môi trường thử bằng hai tài khoản thật.
- P4-E02 được kiểm bằng hai phiên độc lập, không phải hai cửa sổ dùng chung phiên.
- P4-E05 xác nhận cả bộ chọn bài mới và lịch sử cũ.
- Không có lỗi làm lộ dữ liệu khác đơn vị, mất dữ liệu đang nhập hoặc xóa lịch sử ngoài ý muốn.
- Ghi mã nguồn đang chạy, thời điểm kiểm, trình duyệt, người thực hiện và liên kết ảnh bằng chứng đã che thông tin nhạy cảm.

Sau khi đủ điều kiện, cập nhật `plan.md` tại `P04-VERIFY` và `P04-HANDOFF`, rồi mới mở P5. Nếu thiếu tài khoản B hoặc thiếu bài kiểm tra cũ, giữ P4 ở trạng thái **Đang chờ thông tin**, không đánh dấu đạt.
