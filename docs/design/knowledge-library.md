# Thiết kế thư viện kiến thức — UX1.3

Ngày đối chiếu: 2026-09-13. Nguồn yêu cầu: [nghiệp vụ](../../business-analysis.md) v1.3, [kỹ thuật](../../technical-specification.md) v2.3, [kế hoạch](../../plan.md) v5.3.

## 1. Nguồn thiết kế và phạm vi

Đã dùng MCP Google Stitch, không chỉ viết lời nhắc cho người dùng tự gửi. Dự án [RT-connect trên Stitch](https://stitch.withgoogle.com/projects/14242591911141046021), mã nội bộ `14242591911141046021`; bộ nhận diện `assets/105b9f4e25334bbcbc6c94d588ee29f9` phiên bản 1. Các mã này chỉ phục vụ người triển khai, không đưa lên giao diện.

Chỉ gửi yêu cầu bố cục và nội dung tổng hợp minh họa; không tải phác đồ bệnh viện thật, dữ liệu bệnh nhân hay thông tin đăng nhập lên Stitch. Không thay hoặc xóa các màn cũ không thuộc phạm vi yêu cầu. Thiết kế không phải mã ứng dụng đã triển khai.

## 2. Bố cục chốt

- Năm mục: Trang chủ; Kiểm tra chất lượng máy; Công cụ sinh học; Thư viện kiến thức; Đơn vị và thiết bị.
- Màu xanh đậm #0F2744, xanh ngọc #0D9488, nền #F8FAFC, thẻ trắng viền nhẹ; giữ đồng bộ các màn.
- Chữ Inter, nội dung 14px, tiêu đề 22–24px, nhãn phụ 12px; nút cao 32–36px. Không thu nhỏ toàn trang để giả đạt yêu cầu gọn.
- Kích thước triển khai cần kiểm: 1366×768 và 1440×900, mức thu phóng 100%; vẫn dùng được bàn phím và thu phóng 200%. Màn nhỏ xếp lại vùng, không cắt nút.
- Hai phạm vi là hai thẻ “Nội bộ đơn vị” và “Cộng đồng”; trong mỗi phạm vi có hai nhóm “Kiểm tra chất lượng máy” và “Phác đồ điều trị”.
- Trang tra cứu có ô tìm, bộ lọc nhóm/chủ đề/bệnh viện nguồn/năm, danh sách ngắn và truy cập nhanh; vùng kết quả cuộn riêng khi cần.
- Soạn bài có trường tiêu đề/tóm tắt, trình soạn trực quan, tệp, nguồn, tự lưu, xem trước và các thao tác đăng rõ phạm vi.
- Màn đọc có mục lục, nội dung/PDF, nguồn/phiên bản và bài liên quan; người ngoài đơn vị không thấy nút sửa/xóa.
- Quản lý bài có đang sử dụng/nháp/lưu trữ/thùng rác, tìm, khôi phục và xóa; khôi phục luôn về nội bộ.
- Tất cả chữ do ứng dụng tạo đều bằng tiếng Việt. PDF/tên bài nguồn do người dùng tải lên giữ nguyên ngôn ngữ gốc; không tự dịch nội dung chuyên môn.

## 3. Nhật ký tạo và đối chiếu

Lần yêu cầu đầu cho màn “Tra cứu nội bộ” trả lỗi dịch vụ không khả dụng. Không lặp lại cùng lệnh. Lần kiểm ban đầu chưa thấy màn; lần kiểm sau phát hiện tác vụ phía Stitch đã hoàn tất và lấy được màn `76eba3d3589142f6b8f20c829044fa55`. Ghi nhận màn đã tạo được sau lỗi phản hồi, không ghi thất bại vĩnh viễn.

| Màn tạo ban đầu | Mã màn | Bản xem trước | Mã giao diện Stitch |
| :--- | :--- | :--- | :--- |
| Thư viện kiến thức — Soạn và chia sẻ bài | `44c11dcce6d74496a92887d6f51d3cfe` | [Xem ảnh](https://lh3.googleusercontent.com/aida/AEtjO1UZFSG4hIdOg_LJlgasbiBT8XernZqiXu5T01ZqzAeCdNp4VQ1CZliuKSb3WMOiBVY4uM-rg51MO-bufI0FDPSnIP7z6oD8lRUqBEgVvuMMoSKPTwSOV5CP2qI7gWanMSjjXndgqkywL0Jl4F9bnDSITE1IBmgYaWQd8xE9COsu7cfUiddbnFIQNj3VPdGAzRBQtpj-bezUnaT71cLWYKm8D6CBB09JT1bf9wYvq0RldXwf0Ec5Eo_bn4M_) | [Mã thiết kế](https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2U4MjAyMmNjYjNiZTRkMGZiYzZmNmM4ZTU3Nzk2MzZiEgsSBxDr8oOythAYAZIBJAoKcHJvamVjdF9pZBIWQhQxNDI0MjU5MTkxMTE0MTA0NjAyMQ&filename=&opi=96797242) |
| Thư viện kiến thức — Đọc bài và tài liệu | `906ddf911c4d47f088a44f956d349c1a` | [Xem ảnh](https://lh3.googleusercontent.com/aida/AEtjO1W1_bbfO_XUINvX72WM4Vm3Rg0jtgkHrlaO-L0IpeAGF2pl3Qq4Lgn5HWRU2FueblzWNk0M5aLlmckloTsUB-253qleGCGRfjZp_zwNA0DpK7Hbeor9qW7tj4V6H5lhkBhM3lGf95_GYUDk7UPLKuFL_zbWfJUmLnELOq0sutIdIuiwvRPj-GbqvnuRD_-_4E5AvQGv894DpQeHTlUvsHtYTPuo2Hrgmi8FhhTbVgxUNShi1z8AM6HBExkT) | [Mã thiết kế](https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzJjMmJlNDIyYmFiZTRlNDA5YWEzZmMxOTgzZmQ1OWJhEgsSBxDr8oOythAYAZIBJAoKcHJvamVjdF9pZBIWQhQxNDI0MjU5MTkxMTE0MTA0NjAyMQ&filename=&opi=96797242) |
| Thư viện kiến thức — Cộng đồng và tra cứu | `0d0c934645364a2988bbbc2fe6a325ec` | [Xem ảnh](https://lh3.googleusercontent.com/aida/AEtjO1VIQ4jnSPXXmmDRF6uM5kt7U5hqbqNj5bnCpmwt8SQgyU3EJz4kA27vJHmC0d5Cz55yFWPLRv92Aey7j6uXf4kvF-ZcfnGf_QnPhBD76K_4jVSjnIB2viwTEDJfyyCiDk7lthj4EQOj5hkXf_IFScsI5t8msO3EP3tZBleF_IWKkai4ja7YNhdLI_IL5XTgM1ZL2tAhxMiQxBTnKI68yZoWEGdB_32L--XOCTSC6FhOeXIbnFsguq8MB8gg) | [Mã thiết kế](https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2QwZTQ3YWZiMDI1YTQwZDU4MzViOTg5ZjU2ZGQyODBhEgsSBxDr8oOythAYAZIBJAoKcHJvamVjdF9pZBIWQhQxNDI0MjU5MTkxMTE0MTA0NjAyMQ&filename=&opi=96797242) |
| Thư viện kiến thức — Tra cứu nội bộ | `76eba3d3589142f6b8f20c829044fa55` | [Xem ảnh](https://lh3.googleusercontent.com/aida/AEtjO1WeIYDZPGJOewlL6dAbjGdkbrRZYuolUdTsmJ1R499N_dcyZeP3lBXK_zTrf_wUOUOT8Y7oBxZNT5bGPGuUq5ktroMXrpHeeX48xKs8PBVgFGvYa60atBNQIjBEwK5pASYfS0A6PljhN3uuOmg-JeedH9idXPa4LK7byqZi7XPV_adlAlwe5zcK4yvlnFnp93N_GlNDFkhYOsgNLxczw5hkdjHyf8pYit94sKY-zAycx-5bcJziIDn_KlGh) | [Mã thiết kế](https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzJmZGNjYTY1MTQyNDQ5YzZhMDBhZDhjZDAwZDU2MWRiEgsSBxDr8oOythAYAZIBJAoKcHJvamVjdF9pZBIWQhQxNDI0MjU5MTkxMTE0MTA0NjAyMQ&filename=&opi=96797242) |
| Thư viện kiến thức — Bài của đơn vị | `849cc29c39fe45e8917d4984321ac0c4` | [Xem ảnh](https://lh3.googleusercontent.com/aida/AEtjO1VETMuMn2TjeZ_EGjFxSmZBrCLqXIs0f3KSxInAKFFEO8xAtDpKtzVtt0lzvAngdyHasxpF429QCUOJ3bfP_vfDf4-RHAp4ZsEKM7Isqy1jtGVRFKYxhHl8XYnQN25WP_QZw9i6P1Oa119uOHv5PSquc1W3JslwNWb-JvlM4GvCIODXCplKmbWauE4Ds-oWq6mo298Yh5QSAiXYzBZ_wvRXImRDIpYINdHcajURySlO1rDgdpBFgnaj7Tev) | [Mã thiết kế](https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzBkYTRiY2M4MGQ0MzQ1MGRiMTdmMDBhYmVmNDNkMWNlEgsSBxDr8oOythAYAZIBJAoKcHJvamVjdF9pZBIWQhQxNDI0MjU5MTkxMTE0MTA0NjAyMQ&filename=&opi=96797242) |

Đã đối chiếu chữ trong mã giao diện của cả năm màn; xem ảnh thu nhỏ của màn soạn và màn đọc. Ảnh phân phối chỉ ở cỡ thu nhỏ, không dùng để kết luận đã đạt độ đọc chữ hoặc vừa màn hình thật.

Lượt soạn/đọc đầu tự thêm thuật ngữ tiếng Anh, nội dung hướng dẫn chưa có nguồn, nhãn đã thẩm định và ngưỡng kiểm tra minh họa. Đã yêu cầu Stitch bỏ chúng, thay bằng nội dung mô tả bố cục và nhãn chưa bổ sung nguồn. Không đưa các đoạn đó vào dữ liệu mẫu của ứng dụng.

Stitch đã xác nhận sửa hai màn soạn/đọc kèm thao tác thay nội dung. Tuy nhiên lần lấy lại màn và tải mã với yêu cầu không dùng bộ nhớ đệm vẫn thấy nhãn thẩm định/ngưỡng cũ, chưa thấy đoạn thay thế. **Chưa xác minh được việc đồng bộ chỉnh sửa vào tệp xuất.** Không xem thông báo hoàn tất của dịch vụ là bằng chứng tệp xuất đã sửa.

Đã yêu cầu sửa hai màn tra cứu để bỏ nhãn thẩm định, quy tắc áp dụng chung không nguồn, từ tiếng Anh và phiên bản phần mềm. Màn quản lý đã tạo thành công; yêu cầu sửa nhóm thứ ba “Tài liệu tham khảo” về loại bài, sửa câu tự dọn mọi tệp sau 30 ngày thành dọn có kiểm tham chiếu. Mọi tệp xuất cần đối chiếu lại trước khi chuyển vào ứng dụng.

Kiểm cuối ngày 2026-09-13: cả ba lượt sửa (hai màn soạn/đọc, hai màn tra cứu, một màn quản lý) đều được Stitch xác nhận. Đã lấy lại thông tin và tải lại mã của cả năm màn, kết quả vẫn là nội dung trước chỉnh sửa:

| Màn | Điểm còn thấy trong tệp xuất |
| :--- | :--- |
| Tra cứu nội bộ | Nhãn đã thẩm định; chưa có đoạn minh họa thay thế |
| Cộng đồng và tra cứu | Cụm “tâm điểm đẳng liều”; chưa có đoạn thay thế |
| Soạn và chia sẻ bài | Nội dung thuật ngữ cũ; chưa có đoạn thay thế |
| Đọc bài và tài liệu | Nhãn thẩm định, ngưỡng 1.0 mm và thuật ngữ cũ |
| Bài của đơn vị | Câu tự dọn vĩnh viễn vẫn còn; chưa có điều kiện giữ tệp đang được tham chiếu |

Trạng thái bàn giao thiết kế: **đã tạo năm bản bố cục; chưa nghiệm thu bản sửa xuất từ Stitch**. Không tiếp tục lặp lệnh sửa giống nhau. Khi triển khai P11, đối chiếu lại bản xuất; nếu dịch vụ vẫn không đồng bộ thì áp đúng nội dung/điều kiện trong nghiệp vụ và đặc tả vào mã ứng dụng, không dùng nguyên văn bản minh họa cũ.

Các phần phải sửa khi triển khai, kể cả nếu Stitch chưa đồng bộ:

- Chỉ hai nhóm chuyên môn; “Tài liệu tham khảo” là loại bài, không phải nhóm thứ ba.
- Không có ngưỡng, quy trình hoặc nhãn đã thẩm định do công cụ thiết kế tự tạo.
- Bài minh họa dùng chữ trung tính; bỏ từ tiếng Anh, “tâm điểm đẳng liều” và đoạn yêu cầu phê duyệt còn sót.
- Dọn sau 30 ngày vẫn kiểm tham chiếu; không hứa xóa mọi PDF. Khôi phục về nội bộ.
- Người chưa có đơn vị đọc được cộng đồng; nút soạn/quản lý dẫn tới thiết lập đơn vị phù hợp, không chặn phần cộng đồng.
- Chữ phụ dưới 12px trong một số mã Stitch phải tăng theo đặc tả; tệp thiết kế cao 2048px không chứng minh giao diện vừa màn hình.

## 4. Yêu cầu tương tác khi lập trình P11

| Tác vụ | Phản hồi trên giao diện | Điều kiện kiểm chứng |
| :--- | :--- | :--- |
| Đổi nội bộ/cộng đồng | Giữ nhóm và từ khóa phù hợp, lấy lại kết quả đúng phạm vi | Không mang số đếm/đoạn trích nội bộ sang cộng đồng |
| Viết/sửa | Báo đang lưu/đã lưu/chưa lưu; không mất phần đang gõ khi lỗi mạng | Chỉ báo đã lưu sau xác nhận máy chủ; xung đột có cách xử lý |
| Tải PDF | Tiến độ và lỗi theo từng tệp; cho xem tệp hợp lệ | Không dùng tệp hỏng/mật khẩu; PDF ảnh được đọc dù chưa tìm được chữ |
| Chia sẻ | Xem trước bản người ngoài sẽ thấy; chọn từng tệp | Bản nháp, ghi chú và tệp không chọn không bị mang theo |
| Sửa sau chia sẻ | Có nháp mới, bản cộng đồng giữ nguyên | Chỉ cập nhật khi người dùng chủ động chọn |
| Thu hồi | Nhãn nội bộ và bỏ khỏi nơi đọc cộng đồng | Yêu cầu mới tới bài, PDF, hình, tìm kiếm và dấu trang bị chặn |
| Lưu bài | Dấu trang cá nhân, không sao chép quyền | Thu hồi không giữ nội dung riêng trong dấu trang |
| Lưu trữ/xóa | Cho thấy tác động, đưa đúng mục quản lý | Không tự tái xuất bản khi khôi phục |
| Thiếu tổ chức | Đọc được cộng đồng sau đăng nhập | Nút soạn nội bộ dẫn tới thiết lập/tham gia đơn vị, không vòng lỗi |

Màn thông thường không hiện mã bản ghi, JSON, đường dẫn lưu trữ, phiên bản bộ tính hoặc quy chế dài như tài liệu kỹ thuật. Quy tắc ở bảng này phải kiểm phía máy chủ, không chỉ ẩn nút.

## 5. Lời nhắc đã gửi và cách tiếp nối

Các yêu cầu đã gửi đều dùng bộ nhận diện trên. Phần mô tả cốt lõi của bốn màn:

- Tra cứu cộng đồng: khối tìm tài liệu giống cổng tài liệu tham khảo, hai phạm vi/hai nhóm, bộ lọc, 5–6 hàng kết quả và truy cập nhanh; không hiện tài liệu nội bộ của nơi khác.
- Soạn và chia sẻ: trình soạn, nguồn và hai PDF; bảng chia sẻ chọn một tệp, tệp còn lại giữ nội bộ.
- Đọc bài/PDF: người thuộc đơn vị khác, chỉ đọc một bản chia sẻ và một PDF đã chọn, mục lục/trình đọc/nguồn.
- Bài của đơn vị: các thẻ quản lý, đang xem thùng rác, khôi phục bài về nội bộ; không thêm vai trò người duyệt.

Yêu cầu sửa đã gửi: bỏ nhãn thẩm định/phê duyệt, ngưỡng và quy trình do AI tự viết; dùng nội dung trung tính chưa bổ sung nguồn; thay các từ tiếng Anh trong bài minh họa bằng tiếng Việt; bỏ phiên bản phần mềm và rút ngắn hộp giải thích quyền.

Stitch còn gợi ý xem chế độ bài viết, lọc phác đồ, thiết kế cho máy tính bảng/điện thoại, trang giới thiệu và trang đơn vị. Phần thuộc thư viện đã nằm trong P11/P16; không tự mở rộng sang trang khác trong đợt này. Bản cho thiết bị nhỏ và các trạng thái tải/trống/lỗi vẫn phải kiểm lúc triển khai.

## 6. Phần chưa được nghiệm thu

- Chưa có giao diện ứng dụng mới kết nối bài viết/PDF/tìm kiếm thật trong đợt này.
- Chưa kiểm bố cục thật ở hai kích thước chuẩn, bàn phím, trình đọc PDF, tự lưu hay thu hồi qua trình duyệt.
- Không coi các nút trong mã Stitch là chức năng đã hoạt động hoặc nội dung minh họa là nguồn kiến thức.
- P0 bàn giao hướng thiết kế và các thiếu sót đã biết; P11 chịu trách nhiệm sửa chi tiết, xây tương tác và kiểm nghiệm trước khi đóng giai đoạn.
