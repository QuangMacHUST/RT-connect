# RT-CONNECT — Kế hoạch triển khai theo giai đoạn

Phiên bản: **5.3**
Ngày: **2026-09-13**
Mốc yêu cầu: **UX1.3**.
Nguồn duy nhất của phạm vi: [business-analysis.md](business-analysis.md) v1.3.
Hợp đồng kỹ thuật: [technical-specification.md](technical-specification.md) v2.3.
Danh mục engine bắt buộc: [docs/pylinac-qa-catalog.md](docs/pylinac-qa-catalog.md) v1.1.

## 1. Cách dùng kế hoạch này

Kế hoạch tổ chức lại sản phẩm theo trải nghiệm bác sĩ/kỹ sư, không chỉ đổi tên menu. Năm mục chính là Trang chủ, QA máy, Công cụ sinh học, Thư viện kiến thức, Đơn vị và thiết bị. Đăng nhập và cơ cấu hiện có được giữ chức năng, làm gọn giao diện.

Trong Kiểm tra chất lượng máy: Danh mục → thực hiện bài → kết quả → lịch sử/PDF/xu hướng. Có nhập số liệu không cần DICOM, phân tích ảnh và phân tích liều. Công cụ sinh học có sáu công cụ cùng trang. Thư viện có hai phạm vi Nội bộ đơn vị/Cộng đồng; mỗi phạm vi có hai nhóm Kiểm tra chất lượng máy/Phác đồ điều trị. Toàn bộ giao diện đợt này dùng tiếng Việt.

Bản 4.25 được giữ ở [lịch sử](docs/history/pre-ux-20260912/plan.md). Giữ mã P0–P20 để tra cứu, nhưng nội dung thay đổi phải nghiệm thu lại. Mã test mới dùng TC-UX1-Pxx-Sxx/Exx; không dùng test cùng số của mốc cũ để tự đóng mốc mới.

### 1.1. Điều không làm trong đợt này

- Không thêm vai trò/phê duyệt vào thao tác của thành viên; giữ scope dữ liệu đơn vị.
- Không duy trì Report Builder/Trend/QA Protocols/BED/EQD2/Tái xạ thành hàng dài trên thanh điều hướng.
- Không bắt người dùng nhập ID, JSON, mã module/phase hoặc tạo scenario để tính nhanh.
- Không đưa công cụ sinh học vào hồ sơ bệnh nhân/bài QA.
- Không dùng ví dụ 105%/107% hoặc số α/β không nguồn làm mặc định.
- Không thêm yêu cầu pháp luật/FDI hoặc dự án commissioning bắt buộc. Có kiểm thử thuật toán và phản hồi dữ liệu thực theo profile; không tuyên bố đạt mọi mục đích lâm sàng chỉ từ test.
- Không tự tạo thêm dịch vụ trả phí, môi trường hoặc đổi nhà cung cấp chỉ để hoàn thành giao diện.

### 1.2. Hiện trạng làm đầu vào, không phải trạng thái hoàn thành UX1

| Nhóm | Đã quan sát trong repository | Phần UX1 cần làm |
| :--- | :--- | :--- |
| Đăng nhập/đơn vị/cơ cấu | Có mã và được người dùng chấp nhận chức năng | Giảm cỡ chữ/khoảng trắng, chia thẻ và kiểm hồi quy |
| Kho QA, run, tệp | Có mô hình và luồng cơ sở | Danh mục theo bài; xóa/khôi phục; tránh bước nhập hồ sơ kỹ thuật |
| QA nhập tay, Gamma, DVH | Có dịch vụ/tính toán và test cũ | Gắn vào workspace chung, test lại input/profile và UX |
| Danh mục pylinac | Chưa có dependency/registry/adapter toàn bộ 16 họ chính và QA contrib công khai | Dùng pylinac làm engine chính thức, khóa version/hash và triển khai đủ mọi capability trong registry runtime |
| PDF/xu hướng | Có nền snapshot/render/projection | Editor theo bài, chọn từng dòng/ảnh, overlays và delete propagation |
| Sinh học | Có nhiều page/scenario/engine | Một trang tính nhanh, lưu tùy chọn, source drawer |
| Thư viện | Có bài tham khảo theo đơn vị, biểu mẫu kỹ thuật; chưa có bản chia sẻ cộng đồng riêng | Cổng đọc/soạn bài, PDF, tìm kiếm, nội bộ/cộng đồng, thu hồi, lưu trữ/xóa và nguồn dùng chung |
| Railway/Supabase | Có cấu hình/runbook/lịch sử triển khai | Đối chiếu khi phát hành, không suy ra trạng thái live từ evidence cũ |

Không reset dữ liệu hoặc xóa code đã có để làm lại toàn bộ. Tái sử dụng phần đúng và viết adapter/migration cho phần chuyển đổi.

## 2. Thứ tự thực thi và các điểm kiểm tra

### 2.1. Thứ tự bắt buộc, hoàn thành từng giai đoạn

Thực hiện đúng chuỗi: P0 → P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8 → P9 → P10 → P11 → P12 → P13 → P14 → P15 → P16 → P17 → P18 → P19 → P20.

Chỉ một giai đoạn được ghi “Đang thực hiện” tại một thời điểm. Không mở công việc sản phẩm của giai đoạn sau khi giai đoạn hiện tại còn điều kiện đóng chưa đạt. Công việc đọc tài liệu và thiết kế trong P0 phục vụ hợp đồng chung; không được ghi là đã triển khai các giai đoạn sau.

Trong một giai đoạn: kiểm đầu vào → dữ liệu và giao diện máy chủ → giao diện người dùng → chạy đúng → lỗi và phục hồi → ghi bằng chứng → bàn giao. Có thể chạy đồng thời các phép kiểm độc lập của chính giai đoạn đó, nhưng không bắt đầu giai đoạn khác.

P1/P2 phải được kiểm lại theo hiện trạng; kết quả lịch sử chỉ giúp xác định phần tái sử dụng. P3 trở đi chỉ mở khi giai đoạn trước đã ghi đủ điều kiện đóng. Khi có lỗi của nền cũ cản giai đoạn hiện tại, sửa lỗi đó ngay trong giai đoạn hiện tại và ghi phạm vi ảnh hưởng; không mở nhiều giai đoạn để né lỗi.

Các phụ thuộc trước đây hướng tới tương lai được xử lý dứt điểm: P7 tự xây phần cài đặt chạy và hợp đồng tài nguyên báo cáo, không chờ P11 hoặc P9; P8 chuẩn bị dữ liệu xuất và điểm xu hướng, P9/P10 mới nghiệm thu hai chức năng đó. P11 xây kho bài, nguồn và dữ liệu α/β cơ sở để P13/P15 dùng; P16 hoàn thiện phác đồ và tích hợp các bảng chuyên biệt. P12 đóng phần khung sáu công cụ và lưu dữ liệu nhập, không dùng việc P13–P16 chưa làm để tự khóa vòng phụ thuộc.

Nếu thiếu dữ liệu thật, dùng dữ liệu tổng hợp để nghiệm thu chức năng, ghi riêng tuyển tập chưa có. Nếu cần thông tin bắt buộc để hoàn thành chức năng hiện tại thì ghi chính xác điểm thiếu, giữ nguyên giai đoạn hiện tại; không bỏ qua điều kiện rồi chuyển bước.

### 2.2. Trạng thái công việc và bàn giao

| Trạng thái trong sổ tiến độ | Ý nghĩa | Chuyển tiếp |
| :--- | :--- | :--- |
| Chưa bắt đầu | Chưa mở gói theo thứ tự | Chỉ mở khi giai đoạn liền trước đã hoàn thành |
| Đang thực hiện | Giai đoạn duy nhất đang xây và kiểm | Chạy gói còn thiếu, sửa lỗi trong phạm vi |
| Đang chờ thông tin | Thiếu đầu vào cụ thể không thể tự xác minh | Giữ giai đoạn; tiếp tục việc độc lập bên trong nếu có |
| Hoàn thành | Đủ đầu ra, tình huống nghiệm thu, bằng chứng và bàn giao | Mở đúng giai đoạn kế tiếp |

Mỗi giai đoạn có mã W01–W04, VERIFY và HANDOFF; có thể chia nhỏ nhưng giữ mã cha. Bằng chứng có mức “Máy phát triển”, “Môi trường thử” hoặc “Đã phát hành” và mã phiên bản nguồn; trạng thái hoàn thành là theo đầu ra đã định của giai đoạn. Giai đoạn chức năng P3–P17 cần dữ liệu lưu thật và kiểm tích hợp tương ứng trên máy phát triển; P2 cần đối chiếu hai môi trường, P18 tổng kiểm, P19 mới đóng triển khai từ xa. Không gọi một giai đoạn đã phát hành nếu chỉ kiểm trên máy phát triển.

P7 bắt buộc đủ P07-CAL, P07-STAR, P07-VMAT, P07-CT, P07-ACR, P07-CHEESE, P07-HELIOS, P07-QUART, P07-LOG, P07-PF, P07-WL, P07-WLMT, P07-PLANAR, P07-FPA, P07-FA, P07-NUCLEAR và P07-CONTRIB. Thực hiện lần lượt các gói trong thứ tự chi tiết P7; bài nhập số liệu không thay cho gói pylinac.

Trước khi đánh dấu “Hoàn thành”, ghi: đầu ra thực tế; gói đã làm; kiểm thử và kết quả thật; tệp/ảnh bằng chứng; thay đổi dữ liệu; lỗi còn mở có ảnh hưởng hay không; bước kế tiếp đúng một mã giai đoạn. Mỗi lần tiếp tục, đọc điểm bàn giao và làm gói đầu tiên chưa xong trong giai đoạn hiện tại.

### 2.3. Điểm kiểm tra G0–G7

| Điểm | Nội dung | Khi nào |
| :--- | :--- | :--- |
| G0 | Ba tài liệu/traceability thống nhất, lịch sử được giữ | P0 |
| G1 | Baseline nguồn/runtime/DB tests tái lập | P1/P2 |
| G2 | Năm mục, compact, tiếng Việt nhất quán, không JSON/ID | P3/P4 và mỗi page mới |
| G3 | Đúng đầu vào, engine thật, chỉ số và đánh giá độc lập | P5–P8/P17 |
| G4 | Lịch sử/xóa/restore/PDF/trend cùng dữ liệu | P5/P9/P10 |
| G5 | Sinh học tính nhanh, thư viện hai nhánh có nguồn | P11–P16 |
| G6 | E2E/UX/fault/migration/khôi phục đúng bản | P18 |
| G7 | Release manifest, URL thật và bàn giao | P19/P20 |

Các điểm này là kiểm tra phần mềm, không đặt thêm vai trò người duyệt trong ứng dụng.

### 2.4. Chuẩn kiểm thử dùng chung

Mỗi TC có precondition, dữ liệu/fixture, bước thực hiện, kết quả mong đợi, actual, evidence, SHA, môi trường và thời điểm. Các mô tả S/E trong từng phase là acceptance scenarios phải được chuyển thành test cụ thể khi triển khai.

Các nhóm lỗi áp dụng cho mọi operation liên quan: validation/biên/đơn vị, không có dữ liệu, trùng yêu cầu, đồng thời, scope, hết phiên, mất mạng, dependency timeout, dữ liệu cũ, xóa/restore, ngôn ngữ/bố cục và giới hạn tài nguyên. Không lặp test không liên quan chỉ để tăng số lượng.

Không cam kết danh sách hữu hạn là tất cả lỗi có thể có. Lỗi mới từ người dùng phải tạo testcase hồi quy và cập nhật phase liên quan. Một test được tính PASS chỉ khi có kết quả kết thúc; không bỏ qua collection error hay task treo.

### 2.5. Nghiệm thu trải nghiệm đo được

- 1366×768 và 1440×900 ở100%: đăng nhập, panel cơ bản của đơn vị/QA/BED có trường chính/nút/kết quả chính trong khung; danh sách dài có cuộn nội bộ hợp lý.
- 200% và màn hình nhỏ: reflow không mất nút/nhãn; không ép không-cuộn bằng cách cắt nội dung.
- 14px thân bài, bảng13–14px, tiêu đề22–24px; chữ phụ không dưới12px.
- Từ QA máy tới biểu mẫu bài: tối đa ba lựa chọn chính sau khi có đơn vị, không bắt mã hồ sơ; PDF mẫu mặc định từ kết quả: mở và tải.
- Bảng QA hiển thị tên bài/máy/thời điểm; không JSON/UUID/module code.
- Mọi menu/error/empty/loading/PDF nhất quán locale; tên khoa học và nguồn nguyên bản là ngoại lệ.
- Ngân sách hiệu năng ban đầu ở dữ liệu thử công bố: thao tác không tính nặng phản hồi nhìn thấy trong300ms; tải trang dữ liệu thường P95≤2s và lưu metadata P95≤2s trên cấu hình/network thử. Ghi cách đo; không áp SLA2s cho engine Gamma/DVH. Job dài phải có tiến độ/trạng thái và timeout theo profile.

## 3. Ma trận chuyển đổi phạm vi cũ sang UX1

| Phần cũ | Đích UX1 | Dữ liệu/code phải giữ | Giai đoạn |
| :--- | :--- | :--- | :--- |
| QA Archive/Folder/Case | QA máy: Danh mục và Lịch sử | Case/files/runs/folders và liên kết | P5/P6 |
| Machine QA checklist | QA nhập tay + engine ảnh riêng | Rule/manual history, không mạo nhận phân tích ảnh | P7 |
| Gamma Workspace | Bài PSQA bên trong QA máy | Gamma inputs/config/runs | P8 |
| Report Builder | PDF trong kết quả | Snapshot/template/report cũ | P9 |
| Trend | Thẻ Xu hướng trong QA máy | Points/baseline/maintenance | P10 |
| QA Protocol Library | Hướng dẫn → thư viện QA; rules → cài đặt bài | Phân loại/backfill giữ phiên bản | P11/P7 |
| Biological Hub và trang riêng | Một trang sáu công cụ | Engine/scenario cũ mở qua adapter worksheet | P12–P15 |
| Biological Knowledge | Thư viện Phác đồ; bảng nguồn dùng chung | Entries/sources/version cũ | P16 |
| Visual Dose/DVH | Chi tiết PSQA | ROI/run/geometry và kết quả | P17 |
| MOD/phase/status kỹ thuật trên sidebar | Bỏ khỏi giao diện thường dùng | Thông tin debug giữ nội bộ | P3 |

## P0 — Chốt mốc UX1 và chuyển đổi tài liệu

**Đầu vào/phụ thuộc:** Không có. Đọc yêu cầu mới trước mọi công việc sản phẩm.
**Phạm vi:** FR-UX1-P00-01; B01–B14. Giữ lịch sử bản cũ, thay cấu trúc đích và giữ số P0–P20.
**Trạng thái UX1.3:** Hoàn thành gói yêu cầu/tài liệu và bàn giao hướng thiết kế ngày 2026-09-13. Chưa triển khai các giai đoạn ứng dụng; bản xuất Stitch còn điểm chưa đồng bộ đã ghi trong sổ thiết kế, phải sửa/kiểm tại P11.

### Trình tự triển khai P0

1. Đọc yêu cầu mới; đối chiếu ba tài liệu và danh mục pylinac, thống nhất hai phạm vi thư viện.
2. Lập hợp đồng bài/PDF/chia sẻ và thiết kế trên Stitch bằng dữ liệu minh họa.
3. Rà liên kết, chuyển đặc tả cũ sang lịch sử, dọn tệp sinh lại được và ghi danh sách.
4. Kiểm tài liệu, ghi kết quả thiết kế thật hoặc lỗi dịch vụ; chốt hợp đồng để P1 bắt đầu.

**Điểm chuyển bước:** Chỉ mở P1 sau khi gói VERIFY và HANDOFF của P0 đạt đúng điều kiện bên dưới.

### Luồng thao tác P0

1. Đối chiếu phản hồi từng mục với màn hình/mã hiện có; phân biệt chức năng giữ nguyên, sửa giao diện và engine cần viết mới.
2. Lập bản đồ yêu cầu → hợp đồng kỹ thuật → giai đoạn/test; đánh dấu tài liệu cũ chỉ để tham khảo.
3. Đặt phiên bản UX1 và ưu tiên; cập nhật sổ tiến độ, không sửa các evidence cũ thành bằng chứng cho yêu cầu mới.

### Gói công việc P0

- [x] P00-W01 — Viết nghiệp vụ 1.3, đặc tả 2.3, kế hoạch 5.3; giữ đủ danh mục pylinac 1.1 và bổ sung thư viện hai phạm vi.
- [x] P00-W02 — Đánh dấu specification/registry cũ; bổ sung bộ kiểm tra cấu trúc và test phủ định cho tài liệu/danh mục pylinac.
- [x] P00-W03 — Chốt đủ 16 họ mô-đun chính/biến thể và QA contrib công khai của pylinac, UI thao tác tay và ranh giới Gamma; tách công việc nội dung thư viện khỏi phát triển chức năng.
- [x] P00-W04 — Chốt chuỗi P0–P20 tuần tự, đối chiếu Stitch, lưu yêu cầu thiết kế và sổ dọn tệp; bảo toàn lịch sử và liên kết.
- [x] P00-VERIFY — Đạt 516 điều kiện cấu trúc, 15 phép thử bộ kiểm; 21 giai đoạn/260 tình huống được mô tả. Kiểm liên kết và giữ nội dung lịch sử; thiết kế có năm màn, phần chưa đồng bộ tệp xuất ghi riêng. Bằng chứng: docs/evidence/ux1-3-planning-contract-20260913.json.
- [x] P00-HANDOFF — Điểm bàn giao UX1.3 ở đầu implementation-progress.md; không sửa mã ứng dụng/triển khai, không nhầm thiết kế với sản phẩm. Bước tiếp theo duy nhất là P1; phần tinh chỉnh và kiểm tương tác thư viện thuộc P11.

### Trường hợp chạy đúng P0

- TC-UX1-P00-S01 — Ba tài liệu thống nhất đúng năm mục chính và sáu công cụ sinh học; mỗi yêu cầu của người dùng có nơi triển khai.
- TC-UX1-P00-S02 — Mỗi P0–P20 có công việc, workflow, S/E test và điều kiện đóng; old evidence truy được nguyên bản.
- TC-UX1-P00-S03 — Bộ kiểm tra tài liệu đạt trên bản đúng và thất bại khi cố tình bỏ phase/tiêu chí bắt buộc.

### Trường hợp lỗi và phục hồi P0

- TC-UX1-P00-E01 — Tài liệu cũ quy định menu khác → đánh dấu hết hiệu lực phần xung đột; không kết hợp hai thiết kế.
- TC-UX1-P00-E02 — Không tìm thấy bằng chứng cũ → ghi chưa xác minh, không tự đánh dấu đã làm.
- TC-UX1-P00-E03 — Có thay đổi chưa commit của người dùng → giữ nguyên; không reset hay ghi đè để làm sạch.

### Bất biến và điều kiện đóng P0

Ba tài liệu được kiểm tra và bảng truy vết đủ; đây chỉ đóng gói yêu cầu, không đóng các phase ứng dụng.

## P1 — Giữ nền runtime và kiểm hồi quy

**Đầu vào/phụ thuộc:** P0 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P01-01; B04. Giữ ứng dụng hiện có chạy được trong quá trình đổi UX.
**Trạng thái UX1 hiện tại:** `LOCAL_VERIFIED_SLICE`; chưa đóng phase vì chưa có bản source candidate đồng bộ lên staging.

### Trình tự triển khai P1

1. Ghi phiên bản nguồn, cấu trúc dữ liệu, môi trường Python/Node và các lệnh chạy đang có.
2. Cài từ tệp khóa; chạy đăng nhập, API, giao diện và các bộ kiểm hồi quy nền.
3. Tái hiện lỗi đã có nếu gặp, sửa đúng nguyên nhân; ghi tệp thay đổi và dữ liệu được giữ.
4. Bàn giao bộ lệnh chạy được, kết quả nền và danh sách cấu hình cần đối chiếu ở P2.

**Điểm chuyển bước:** Chỉ mở P2 sau khi gói VERIFY và HANDOFF của P1 đạt đúng điều kiện bên dưới.

### Luồng thao tác P1

1. Ghi branch/SHA, trạng thái file và phiên bản runtime thực tế; không đọc/hiển thị secret.
2. Khởi động nền local theo runbook hiện có, kiểm DB migration và các phép thử đã có.
3. Thiết lập kiểm tra tài liệu, unit/API/web build và lưu kết quả với mã nguồn cụ thể.

### Gói công việc P1

- [x] P01-W01 — Chụp baseline mã, schema và các test hiện có; phân biệt kết quả cũ với run mới.
- [x] P01-W02 — Bổ sung kiểm tra UX1 vào CI, giữ kiểm thử bảo toàn dữ liệu và tenant scope.
- [x] P01-W03 — Chuẩn hóa scripts local/Windows, timeout có thể cấu hình, kiểm exit code và khử dữ liệu nhạy cảm trong log.
- [x] P01-W04 — Lập mẫu evidence theo test/SHA/môi trường/input/expected/actual; chia nhóm test khi cần và lưu exit code.
- [x] P01-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA: [evidence P1](docs/evidence/p1-foundation-recheck-20260913-7a7e4ec.json).
- [x] P01-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P1

- TC-UX1-P01-S01 — Cài theo lockfile, build web và chạy API/test collection không cần sửa môi trường máy bằng tay.
- TC-UX1-P01-S02 — Migration từ DB trống tới head và mở DB đã có dữ liệu đều đạt.
- TC-UX1-P01-S03 — Test được chạy tới completion; tổng số nhóm bằng collection nếu dùng chạy phân nhóm.

### Trường hợp lỗi và phục hồi P1

- TC-UX1-P01-E01 — Thiếu dependency hoặc không tương thích Python → báo package/phiên bản, chọn phương án tương thích trước khi đổi lock.
- TC-UX1-P01-E02 — Port đang dùng → xác định tiến trình/dịch vụ, không khởi động chồng.
- TC-UX1-P01-E03 — Test treo hoặc mất phiên → giữ handle và log; không gọi PASS nếu chưa có kết quả kết thúc.
- TC-UX1-P01-E04 — Migration/schema không khớp → dừng ghi dữ liệu, sửa migration và chạy lại trên bản sao.

### Bất biến và điều kiện đóng P1

Có baseline local/CI tái lập, không thay đổi hành vi hiện có ngoài phạm vi UX1; chưa coi local PASS là staging PASS.

## P2 — Cấu hình Railway và Supabase nhất quán

**Đầu vào/phụ thuộc:** P1 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P02-01; B04. Tận dụng cấu hình đã có, kiểm khi triển khai thay đổi liên quan.
**Trạng thái UX1 hiện tại:** `STAGING_VERIFIED`; P3 đã đủ điều kiện bàn giao và mở P4.

**Trạng thái thực thi 2026-09-13:** `STAGING_VERIFIED`, P2 đóng cho chuỗi phát triển.
Staging đã có cấu hình hiệu lực, health/readiness, phiên Supabase thật, trang tổ chức đọc dữ
liệu và web/API cùng mã nguồn `7a7e4ec`. Production hiện chỉ có dịch vụ API nền cũ, chưa có
gói web/worker/Auth đồng bộ; đây là cổng phát hành production của P19, không phải lý do
chặn việc bắt đầu xây dựng giao diện và nghiệp vụ ở P3. Ô config-as-code trống
(`railwayConfigFile=null`) là trạng thái hợp lệ của cấu hình Railway hiện tại; không coi việc
mất đường dẫn `/apps/api/railway.toml` là lỗi nếu cài đặt hiệu lực đã đúng.

### Trình tự triển khai P2

1. Đọc cấu hình Railway đang hiệu lực ở môi trường thử/vận hành, so với đường dẫn mã và bản triển khai.
2. Kiểm chuỗi kết nối dùng psycopg 3 trong ứng dụng lẫn Alembic; kiểm di chuyển dữ liệu trước triển khai.
3. Đối chiếu Supabase, địa chỉ web/API, CORS, chuyển hướng đăng nhập; thử hết phiên và thiếu đơn vị.
4. Ghi sổ cấu hình không có bí mật, kết quả kiểm kết nối và hướng xử lý lỗi; bàn giao P3.

**Điểm chuyển bước:** Chỉ mở P3 sau khi gói VERIFY và HANDOFF của P2 đạt đúng điều kiện bên dưới.

### Luồng thao tác P2

1. Lập sổ cấu hình mong muốn/hiệu lực riêng cho web, API, worker và DB từng môi trường.
2. Kiểm normalization DATABASE_URL dùng chung runtime/Alembic và biến Vite ở lúc build web.
3. Kiểm health/ready rồi auth bootstrap thật của đúng bản triển khai; ghi SHA và thời điểm.

### Gói công việc P2

- [x] P02-W01 — Tập trung URL normalizer; test postgres://, postgresql://, postgresql+psycopg:// và giữ nguyên thông tin kết nối.
- [x] P02-W02 — Đối chiếu Railway branch/root/build/start/predeploy/PORT và trạng thái config-as-code hiệu lực; ghi giá trị không chứa secret.
- [x] P02-W03 — Đối chiếu staging web Supabase URL/publishable key, API issuer/JWKS, CORS và redirect đúng origin; ghi production thiếu cấu hình tương ứng.
- [x] P02-W04 — Cập nhật runbook health/readiness, giới hạn retry và kiểm chứng predeploy migration.
- [x] P02-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA. Staging đạt parity sau triển khai API; production gap được ghi thành cổng P19.
- [x] P02-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo. P3 được mở; production chỉ được phát hành sau packet và kiểm tra P19.

### Trường hợp chạy đúng P2

- TC-UX1-P02-S01 — Cả dạng postgresql:// và postgresql+psycopg:// dùng psycopg 3 cho API lẫn Alembic.
- TC-UX1-P02-S02 — Web đúng môi trường đăng nhập và gọi API/DB được; migration đã chạy trên deployment mới.
- TC-UX1-P02-S03 — Sổ cấu hình thể hiện rõ Railway PostgreSQL/backend, Supabase Auth; không dùng DB Supabase cho nghiệp vụ.

### Trường hợp lỗi và phục hồi P2

- TC-UX1-P02-E01 — No module named psycopg2 → kiểm URL trong Alembic, không thêm driver khác để che sự thiếu nhất quán.
- TC-UX1-P02-E02 — Vite thiếu env → rebuild web với giá trị build-time, không chỉ redeploy API.
- TC-UX1-P02-E03 — Health thất bại dù URL public cũ sống → kiểm instance mới/PORT/start log, không bỏ health để đánh dấu xong.
- TC-UX1-P02-E04 — Config path hiển thị mất hoặc root sai → đối chiếu effective config/source, không bắt người dùng nhập lại vô hạn.
- TC-UX1-P02-E05 — Sai CORS/issuer/redirect → sửa đúng service; không mở wildcard có credentials hoặc tắt xác thực.

### Bất biến và điều kiện đóng P2

Staging có sổ cấu hình, kiểm chứng công khai và phiên tổ chức thật theo đúng mã nguồn ứng viên.
Production có sổ hiện trạng và khoảng thiếu; không phát hành production, không suy đoán hoặc
mở rộng dịch vụ có phí trước P19.

## P3 — Thiết kế gọn, điều hướng, đăng nhập và trang chủ

**Đầu vào/phụ thuộc:** P2 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P03-01; B01/B02/B03. Đây là bước sản phẩm làm tiếp đầu tiên sau tài liệu.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P3

1. Dùng bộ thiết kế chung; chốt nhãn năm mục và thang chữ 14px, bố cục 1366×768/1440×900.
2. Làm khung điều hướng, đăng nhập, trang chủ và trạng thái tải/rỗng/lỗi; tuyến cộng đồng chỉ chặn thiếu đăng nhập.
3. Thay nhãn trộn tiếng Anh, kiểm liên kết cũ, quay lại, bàn phím và thu phóng 200%.
4. Chụp các màn hình thật, kiểm hợp đồng điều hướng và đăng nhập; giai đoạn sau nhận khung đã dùng được.

**Điểm chuyển bước:** Chỉ mở P4 sau khi gói VERIFY và HANDOFF của P3 đạt đúng điều kiện bên dưới.

### Luồng thao tác P3

1. Dùng Stitch project RT-connect làm tham chiếu phong cách; kiểm lại danh sách màn hình trước khi dùng, không dựa ảnh đã xóa.
2. Thiết kế khung năm mục, trang chủ/đăng nhập và biến thể hai kích thước chuẩn.
3. Triển khai layout/locale/redirect cũ; chạy các trạng thái đăng nhập và xem gần đây bằng dữ liệu thật.

### Gói công việc P3

- [x] P03-W01 — Thiết kế token chữ/khoảng cách/thẻ/bảng; tạo AppShell, CompactPage, SplitPane và trạng thái dùng chung. `LOCAL_VERIFIED_SLICE`.
- [x] P03-W02 — Dịch nhãn chung và luồng đăng nhập sang tiếng Việt, bỏ MOD/Pxx/ID/API/JSON khỏi giao diện điều hướng và trạng thái nền tảng. Nhãn nghiệp vụ của từng mô-đun tiếp tục được kiểm tại phase tương ứng; `LOCAL_VERIFIED_SLICE`.
- [x] P03-W03 — Giữ auth flow; phân biệt chưa vào đơn vị, hết phiên, mất mạng; đưa trạng thái dịch vụ vào menu tài khoản. `LOCAL_VERIFIED_SLICE`.
- [x] P03-W04 — Tạo đúng năm mục, trang chủ gọn và chuyển hướng URL cũ; kiểm keyboard, back/forward, deep link. `LOCAL_VERIFIED_SLICE`.
- [x] P03-VERIFY — Kiểm local đạt lint, typecheck, Vitest 22/22, production build và Playwright 9/9 ở hai kích thước 1366×768/1440×900 cùng ba cấu hình trình duyệt; kiểm staging công khai đạt 17/17 và trình duyệt staging tải đúng trang chủ/điều hướng năm mục. Evidence: `docs/evidence/p3-local-ui-20260913.json`, `docs/evidence/p3-staging-verified-20260913-dcf463c.json`, `docs/evidence/p3-staging-public-verifier-20260913-dcf463c.json`.
- [x] P03-HANDOFF — Cập nhật `implementation-progress.md`, route registry và trạng thái bàn giao; không thay dữ liệu nghiệp vụ, không phát hành production. Bước kế tiếp duy nhất là P4.

### Trường hợp chạy đúng P3

- TC-UX1-P03-S01 — Ở 1366×768 và 1440×900, đăng nhập và hành động chính trang chủ nằm trong màn hình, không có thẻ giới thiệu cao dư thừa.
- TC-UX1-P03-S02 — Người đã đăng nhập đúng đơn vị vào được trang chủ; người mới nhận hướng dẫn đúng bước còn thiếu.
- TC-UX1-P03-S03 — Mọi trạng thái lỗi/trống/đang tải tiếng Việt; nguồn/tên riêng là ngoại lệ được liệt kê.
- TC-UX1-P03-S04 — Liên kết cũ mở nội dung tương đương, nút quay lại không mắc vòng chuyển hướng.

### Trường hợp lỗi và phục hồi P3

- TC-UX1-P03-E01 — API không phản hồi → trạng thái lỗi có thử lại, không màn trắng hoặc quay tải mãi.
- TC-UX1-P03-E02 — Locale thiếu khóa → chặn release ngôn ngữ đó, không fallback tiếng Anh lẫn tiếng Việt.
- TC-UX1-P03-E03 — Zoom 200%/màn nhỏ → chuyển cột và cho cuộn, không ẩn nút hoặc ép chữ nhỏ hơn.
- TC-UX1-P03-E04 — Stitch không truy cập được → ghi nguồn thiết kế thiếu, tiếp tục bản thiết kế local theo BA; không coi màn cũ cao 4000px là chuẩn.
- TC-UX1-P03-E05 — Auth callback/session recovery lỗi → thông báo đúng nguyên nhân, không xóa tài khoản hoặc membership.

### Bất biến và điều kiện đóng P3

Ảnh/AX kiểm thử giao diện đăng nhập, hai viewport, route/auth tests, bộ kiểm local và kiểm công khai staging đạt B01–B03 trong
các bằng chứng P3. Source ứng viên `d288d669f264747bd0430e9f085255d0910592ab` đã đồng bộ API/web/worker staging và được kiểm lại.
P3 được đóng ở mức `STAGING_VERIFIED`; production vẫn là cổng riêng của P19.

## P4 — Đơn vị, cơ sở, thiết bị và thành viên gọn

**Đầu vào/phụ thuộc:** P3 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P04-01; B02/B03/B04. Không thiết kế lại phân quyền.
**Trạng thái hiện tại:** `STAGING_VERIFIED_SLICE`; lát cắt giao diện đã được kiểm trên staging, chưa đóng P4.

Evidence hiện tại: `docs/evidence/p4-local-organization-ui-20260913-8a1fe44.json`, `docs/evidence/p4-local-machine-creation-20260913.json`, `docs/evidence/p4-local-organization-api-20260913.json`, `docs/evidence/p4-staging-verified-20260913-8a1fe44.json`, `docs/evidence/p4-staging-public-verifier-20260913-e8c4323.json` và `docs/evidence/p4-staging-public-verifier-20260913-9d95f89.json`. Bằng chứng mới nhất xác nhận bản sửa biểu mẫu, source parity và triển khai đồng bộ ba dịch vụ trên staging; lát cắt này không thay cho kiểm xung đột hai danh tính, vòng đời lưu trữ/khôi phục hoặc bàn giao P4.

### Trình tự triển khai P4

1. Chuyển phần đơn vị/cơ sở/máy/thành viên thành thẻ và biểu mẫu gọn, giữ tên người dùng quen thuộc.
2. Đối chiếu các thao tác hiện có với máy chủ; định danh kỹ thuật tự tạo bên trong.
3. Thử hai đồng nghiệp cùng sửa, đổi đơn vị, ngừng dùng/khôi phục máy và lời mời hết hạn.
4. Bàn giao cơ cấu gọn cùng danh sách máy/đơn vị cho bộ chọn ở P5.

**Điểm chuyển bước:** Chỉ mở P5 sau khi gói VERIFY và HANDOFF của P4 đạt đúng điều kiện bên dưới.

### Luồng thao tác P4

1. Chọn Đơn vị và thiết bị, mở thẻ Đơn vị/Cơ sở và máy/Thành viên.
2. Chọn dòng để sửa cạnh danh sách; tạo cơ sở/máy hoặc mời đồng nghiệp bằng biểu mẫu nhỏ.
3. Lưu và nhận phản hồi ngay dòng; dữ liệu cũ và bài lịch sử vẫn truy cập được.

### Gói công việc P4

- [x] P04-W01 — Đưa biểu mẫu dài thành các thẻ và khung sửa gọn; giảm tiêu đề/khoảng trắng. `STAGING_VERIFIED_SLICE`.
- [x] P04-W02 — Dịch nhãn, trạng thái, lời mời và lỗi; mã kỹ thuật vẫn được giữ ở lớp dữ liệu nhưng không hiển thị trong bảng và thông tin thường dùng. `STAGING_VERIFIED_SLICE`.
- [x] P04-W03 — Giữ tính ngang quyền và scope; kiểm sửa đồng thời theo revision. `LOCAL_VERIFIED_SLICE`; 16/16 kiểm thử API P4 đạt với danh tính giả lập.
- [x] P04-W04 — Kiểm ngừng dùng/khôi phục máy, chuyển đơn vị và tác động tới bộ chọn máy/QA lịch sử. `LOCAL_VERIFIED_SLICE` cho vòng đời API; kiểm bộ chọn/lịch sử trên staging vẫn mở.
- [ ] P04-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P04-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P4

- TC-UX1-P04-S01 — Sửa tên đơn vị, thêm máy và xem thành viên không cần cuộn qua toàn bộ các biểu mẫu khác.
- TC-UX1-P04-S02 — Hai thành viên dùng được cùng thao tác; không hiện vai trò duyệt/quản trị nghiệp vụ mới.
- TC-UX1-P04-S03 — Máy ngừng dùng vẫn có lịch sử, không xuất hiện mặc định cho bài mới.

### Trường hợp lỗi và phục hồi P4

- TC-UX1-P04-E01 — Tên trống/trùng theo phạm vi → lỗi ngay trường, không mất form.
- TC-UX1-P04-E02 — Hai người lưu cùng revision → báo xung đột và giữ bản nhập để đối chiếu.
- TC-UX1-P04-E03 — Lời mời hết hạn/đã dùng/sai email → thông báo khác nhau và cách xử lý; không tạo membership trùng.
- TC-UX1-P04-E04 — Chuyển đơn vị → xóa cache/draft sai scope, không lộ máy/dữ liệu của đơn vị trước.
- TC-UX1-P04-E05 — Ngừng dùng cơ sở có máy/bài → xác nhận tác động, không xóa dây chuyền lịch sử.

### Bất biến và điều kiện đóng P4

Chức năng đã được người dùng chấp nhận vẫn hoạt động, layout gọn và kiểm hồi quy scope/revision đạt. P4 chỉ được đóng sau khi lát cắt cục bộ và staging được nối với hai danh tính thật, kiểm vòng đời trên trình duyệt và xác nhận tác động tới bộ chọn/lịch sử QA.

## P5 — Danh mục QA, bắt đầu bài, lịch sử và xóa

**Đầu vào/phụ thuộc:** P4 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P05-01; B05/B08. Thay kho hồ sơ làm điểm bắt đầu bằng danh mục bài.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P5

1. Lập danh mục toàn bộ bài pylinac và bài nhập số liệu, loại tệp và trạng thái khả dụng chính xác.
2. Dựng danh mục, bắt đầu bài, bản nháp và lịch sử trên dữ liệu thật; chuyển liên kết ca cũ.
3. Làm thùng rác/khôi phục, kiểm tác vụ đang chạy và quan hệ tệp/kết quả còn tham chiếu.
4. Bàn giao dữ liệu và điều hướng lịch sử; bộ nhập P6 nhận được đúng loại bài và đơn vị.

**Điểm chuyển bước:** Chỉ mở P6 sau khi gói VERIFY và HANDOFF của P5 đạt đúng điều kiện bên dưới.

### Luồng thao tác P5

1. Chọn QA máy → Danh mục; lọc bài và máy, thấy rõ loại đầu vào.
2. Bấm thực hiện để tự tạo lượt làm việc; đặt tên tự nhiên tùy chọn, không nhập ID.
3. Lưu/mở lại từ Lịch sử; lọc, xếp thư mục tùy chọn, xóa/khôi phục hoặc xóa vĩnh viễn có xác nhận.

### Gói công việc P5

- [ ] P05-W01 — Tạo QATestDefinition/capability registry và adapter trên QACase; seed đầy đủ các nhóm trong BA, ghi đúng manual/automatic.
- [ ] P05-W02 — Làm danh mục, bắt đầu bài, lưu nháp và lịch sử phân trang; giữ folder lồng nhau nhưng không bắt dùng.
- [ ] P05-W03 — Triển khai soft delete, trash/restore, purge có reference check và xử lý job đang chạy.
- [ ] P05-W04 — Backfill dữ liệu cũ, giữ URL/tệp/report/run; kiểm projection lịch sử và tính idempotent.
- [ ] P05-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P05-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P5

- TC-UX1-P05-S01 — Bắt đầu một bài trong tối đa ba lựa chọn chính từ QA máy sau khi đã chọn đơn vị; không có form mã hồ sơ.
- TC-UX1-P05-S02 — Lọc/mở đúng bài và lần tính cũ; đổi tên/di chuyển thư mục không làm mất tệp/kết quả.
- TC-UX1-P05-S03 — Xóa loại khỏi lịch sử và xu hướng; khôi phục đúng một lần; chọn nhiều có kết quả từng mục.
- TC-UX1-P05-S04 — Purge chỉ dọn dữ liệu/tệp thuộc phạm vi đã xác nhận và không còn dùng chung.

### Trường hợp lỗi và phục hồi P5

- TC-UX1-P05-E01 — Bấm tạo/xóa/restore lặp do mạng → cùng yêu cầu không tạo bản trùng.
- TC-UX1-P05-E02 — Bài chưa phân loại sau migration → hiển thị lịch sử cũ, không ép vào engine sai; cho gắn loại phù hợp.
- TC-UX1-P05-E03 — Xóa khi worker chạy → dừng hoặc từ chối publication sau xóa, không tự hồi sinh bài.
- TC-UX1-P05-E04 — Storage purge lỗi → giữ trạng thái đang dọn/có thể thử lại, không báo đã xóa vĩnh viễn.
- TC-UX1-P05-E05 — Tệp còn dùng bởi bài khác → không dọn tệp chung; xác nhận nêu phạm vi.
- TC-UX1-P05-E06 — Mất mạng/409 khi xóa nhiều → hiển thị từng mục đã xóa/chưa xóa, không yêu cầu người dùng đoán.

### Bất biến và điều kiện đóng P5

Danh mục đúng đầu vào, dữ liệu cũ mở được, trash/restore/purge và liên kết lịch sử có test DB/worker/storage; không coi chỉ xóa hàng trên UI là đạt.

## P6 — Đầu vào theo bài và kiểm tra dữ liệu

**Đầu vào/phụ thuộc:** P5 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P06-01; B05/B06. Không dùng một upload form chung cho mọi bài.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P6

1. Định nghĩa đầu vào từng bài theo danh mục đã chốt; kiểm số lượng, loại tệp, đơn vị và hình học.
2. Làm chọn tệp/tải lại theo tệp, xem trước ảnh, nhập thông số và ghép cột bảng khi định dạng hỗ trợ.
3. Kiểm ảnh sai loại, tệp hỏng, thiếu thang đo, grid/vai trò liều, quá dung lượng và mất mạng.
4. Bàn giao bộ dữ liệu hợp lệ/lỗi và hợp đồng tham số đã chuẩn hóa cho P7.

**Điểm chuyển bước:** Chỉ mở P7 sau khi gói VERIFY và HANDOFF của P6 đạt đúng điều kiện bên dưới.

### Luồng thao tác P6

1. Bài nhập tay hiển thị số/đơn vị; bài ảnh hiển thị ảnh được hỗ trợ; PSQA hiển thị vai trò liều tham chiếu và đo.
2. Tải nhiều tệp, xem thumbnail/metadata cần thiết bằng nhãn dễ hiểu; xác nhận scale/role còn thiếu.
3. Kiểm tra dữ liệu; sửa từng lỗi trước khi chạy, giữ phần đã tải hợp lệ.

### Gói công việc P6

- [ ] P06-W01 — Typed input schemas theo test/input_mode và trình dựng form không JSON.
- [ ] P06-W02 — Upload có progress/retry, manifest nội bộ, checksum/type/size và signed URL đúng scope.
- [ ] P06-W03 — Validation DICOM/hình học/thang đo/vai trò và bộ đọc measurement registry; wizard ghép cột nếu hỗ trợ bảng.
- [ ] P06-W04 — Giới hạn tài nguyên parse và dọn upload dở; lỗi localized theo trường/tệp.
- [ ] P06-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P06-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P6

- TC-UX1-P06-S01 — Bài nhập tay hoàn thành mà không có file; số đo 0 và NA được phân biệt.
- TC-UX1-P06-S02 — Mỗi capability pylinac chỉ nhận số tệp/loại/profile được registry của class cho phép; scale, spacing và điều chỉnh đã nhập được giữ cùng input snapshot.
- TC-UX1-P06-S03 — PSQA chọn đúng RTDOSE reference/comparison; upload trùng nhận biết mà không đổi dữ liệu gốc.
- TC-UX1-P06-S04 — Tải bị gián đoạn có thể thử đúng tệp lỗi, không mất các trường đã nhập.

### Trường hợp lỗi và phục hồi P6

- TC-UX1-P06-E01 — Đổi đuôi file thành DICOM nhưng bytes sai → từ chối theo nội dung.
- TC-UX1-P06-E02 — Sai modality/Frame of Reference/shape/dose scaling → không chạy; chỉ đúng dữ liệu cần thay.
- TC-UX1-P06-E03 — Thiếu SID/spacing/scale của profile → yêu cầu bổ sung có đơn vị, không suy ra tùy tiện.
- TC-UX1-P06-E04 — NaN/Infinity/liều âm/baseline0 khi chia → validation trước khi engine chạy.
- TC-UX1-P06-E05 — File nén quá lớn/codec không hỗ trợ/quá RAM → fail có kiểm soát, không làm chết API.
- TC-UX1-P06-E06 — CT/RTSTRUCT dùng nhầm vai trò dữ liệu đo → nêu loại đầu vào cần có; không coi đủ vì đã upload DICOM.

### Bất biến và điều kiện đóng P6

Input contract cho từng bài, fixture hợp lệ/lỗi và giới hạn tài nguyên đã thử; manifest không xuất hiện thô trong giao diện.

## P7 — QA nhập tay và toàn bộ danh mục pylinac

**Đầu vào/phụ thuộc:** P6 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P07-01; B05/B06/B07. P7 cũ chỉ có checklist/rule và ba ví dụ ảnh không đủ đóng P7 UX1.3.
**Trạng thái UX1.3 lúc lập kế hoạch:** yêu cầu mới; toàn bộ gói dưới đây ở trạng thái Chưa bắt đầu cho đến khi có evidence mới đúng phiên bản pylinac đã khóa.

Pylinac là engine đã chọn, không còn bước so sánh để quyết định có dùng hay không. Kiểm tương thích chỉ quyết định đặt dependency trong API hay `qa-image-worker`. P7 chỉ hoàn thành khi registry runtime bao phủ đủ 16 họ mô-đun chính, toàn bộ class/biến thể và các bài QA `contrib/One-Offs` công khai của wheel đã khóa.

### Trình tự triển khai P7

1. Làm P07-W01 cho nhập số liệu; khóa pylinac ở W02, xây registry và PylinacAdapter ở W03, rồi khung ảnh/kết quả W04.
2. Lần lượt hoàn thiện P07-PF → P07-WL → P07-STAR → P07-WLMT → P07-VMAT → P07-FPA → P07-FA; từng gói có biểu mẫu, chọn tâm/vùng, kết quả và thử lỗi riêng.
3. Tiếp tục P07-PLANAR → P07-CT → P07-ACR → P07-CHEESE → P07-HELIOS → P07-QUART → P07-CAL → P07-LOG → P07-NUCLEAR → P07-CONTRIB; không bỏ biến thể còn công khai.
4. Đối chiếu toàn bộ registry với bản pylinac khóa; bàn giao kết quả/lịch sử và dữ liệu dựng PDF. P9 mới hoàn thiện giao diện xuất PDF; P7 không chờ P9.

**Điểm chuyển bước:** Chỉ mở P8 sau khi gói VERIFY và HANDOFF của P7 đạt đúng điều kiện bên dưới.

### Luồng thao tác P7

1. Chọn loại thiết bị/máy; danh mục mặc định lọc bài phù hợp, còn “Tất cả bài pylinac” hiển thị đủ coverage.
2. Chọn bài; RT-CONNECT mở đúng form số đo/tệp, tham số cơ bản và hướng dẫn chuẩn bị.
3. Tải dữ liệu hoặc nhập số; preflight kiểm định dạng, scale, số ảnh, metadata, đơn vị và giới hạn trước khi enqueue.
4. Chạy tự động bằng đúng class pylinac; xem metric, biểu đồ và overlay chuẩn hóa từ `results_data()`.
5. Nếu cần, mở “Điều chỉnh”, click/kéo tâm/ROI/profile hoặc nhập tham số class hỗ trợ; xác nhận và tạo run mới.
6. Chọn đánh giá của người thực hiện độc lập với metric; lưu vào lịch sử, so sánh run, xuất PDF hoặc xem xu hướng.

### Gói công việc P7

- [ ] P07-W01 — QA nhập tay: bảng nhiều giá trị, checklist/NA, công thức có kiểu, chuẩn/ngưỡng trực quan và kết luận riêng; không yêu cầu DICOM khi bài không cần.
- [ ] P07-W02 — Khóa wheel pylinac 3.47.0 và SHA-256 trong lock/image; xác minh runtime/dependency. Nếu API Python 3.14 không tương thích, tạo `qa-image-worker` với Python tương thích; không đổi sang engine khác.
- [ ] P07-W03 — Phát triển `PylinacCapabilityRegistry` + `PylinacAdapter`; inventory wheel phải khớp registry đủ 16 họ chính, QA contrib công khai, class/variant, input profile, parameter schema, result mapping, overlay, error và fixture.
- [ ] P07-W04 — Xây result viewer/canvas chung: auto run, điều chỉnh bằng click/drag hoặc form, parameter diff, run mới, lớp ảnh/biểu đồ, đánh giá và persist history.
- [ ] P07-CAL — Calibration: TG-51 photon/electron legacy/electron modern và TRS-398 photon/electron; form theo protocol, factors/dose; ghi rõ pylinac chưa nhận revision TRS-398 2024 nếu bản khóa chưa có.
- [ ] P07-STAR — Starshot: gantry/collimator/MLC/couch; UI chọn `start_point`, radius, peak/tolerance/FWHM/recursive/invert; tâm/tia/wobble overlay.
- [ ] P07-VMAT — VMAT: DRGS, DRMLC, DRCS; cặp ảnh open/dynamic, tolerance, segment/ROI/offset và deviation overlay.
- [ ] P07-CT — CatPhan 503/504/600/604; chuỗi/ZIP DICOM, origin slice, CTP module, HU/scaling/thickness/uniformity/MTF/low contrast/NPS và ROI adjustments.
- [ ] P07-ACR — ACR CT 464, MRI Large, MRI Medium; module/slice/ROI controls và toàn bộ structured results công khai.
- [ ] P07-CHEESE — TomoCheese và CIRS 062M; origin/ROI/reference density controls và density/HU outputs.
- [ ] P07-HELIOS — GE Helios CT Daily; contrast scale, high contrast resolution, noise, uniformity, low contrast và điều chỉnh module/ROI.
- [ ] P07-QUART — Quart DVT và alias/biến thể HyperSight còn public trong wheel; HU/geometry/uniformity/CNR/SNR và module controls.
- [ ] P07-LOG — Dynalog và Trajectory Log 2.1/3.0/4.0, `.bin`/`.txt` theo class; axis/MLC/hold/fluence/Gamma log và rule đánh giá do đơn vị chọn.
- [ ] P07-PF — Picket Fence: MLC/profile registry, orientation/crop/sag/offset/tolerance/action tolerance, leaf/picket metrics, histogram và overlay.
- [ ] P07-WL — Winston–Lutz một target: angle/coordinate mapping, BB/CAX từng ảnh, isocenter/axis plots và couch shift khi phù hợp.
- [ ] P07-WLMT — Winston–Lutz Multi-Target/Multi-Field: form cấu hình BB/field/tọa độ/mapping và ghép cặp/overlay; không bắt tệp cấu hình thô.
- [ ] P07-PLANAR — Toàn bộ Planar Imaging: Leeds/Blue, SI QC-3/QC-kV, Las Vegas/Elekta, Doselab MC2 MV/kV, SNC MV/MV12510/kV, PTW EPID QC, IBA Primus A, SI FC-2, IMT L-RAD, Doselab RLf, IsoAlign, SNC FSQA, ACR Digital Mammography.
- [ ] P07-FPA — Field Profile Analysis: manual/beam/geometric center, click position, x/y width, normalization, edge type và toàn bộ profile metrics công khai.
- [ ] P07-FA — Field Analysis legacy: UI tương thích EPID/SNC Profiler và protocol cũ; nhãn mô-đun cũ, bài mới mặc định FPA nhưng không loại capability khỏi catalog.
- [ ] P07-NUCLEAR — Nuclear: max count rate, planar uniformity, center of rotation, tomographic resolution, simple sensitivity, four-bar, quadrant, tomographic uniformity và tomographic contrast; form riêng từng phép thử.
- [ ] P07-CONTRIB — One-Offs/Contrib: `QuasarLightRadScaling` và `JawOrthogonality`; dùng chính pylinac, form/thao tác ảnh theo từng class, gắn nhãn “Mô-đun đóng góp”, lưu source tier/version/hash và có fixture/contract test độc lập.
- [ ] P07-VERIFY — Chạy toàn bộ TC-UX1-P07, inventory-diff test và matrix `class × input profile × parameter mode × result/overlay/error`; lưu actual/evidence theo SHA, wheel hash và environment.
- [ ] P07-HANDOFF — Cập nhật tiến độ từng package/class, migration/API/UI, fixture coverage, giới hạn còn mở và version/hash pylinac; không ghi P7 DONE nếu còn một capability công khai chưa xử lý.

### Trường hợp chạy đúng P7

- TC-UX1-P07-S01 — QA nhập tay sát biên ngưỡng đạt/cảnh báo/không đạt đúng rule; phần trăm so chuẩn, số 0 và NA không lẫn.
- TC-UX1-P07-S02 — Registry quét wheel đã khóa và ánh xạ đủ đúng 16 họ chính, mọi class/variant và QA contrib công khai; không có capability bị bỏ im lặng.
- TC-UX1-P07-S03 — P07-CAL: mỗi class TG-51/TRS-398 nhận form đúng trường/đơn vị và adapter trả đúng `results_data()`/properties công khai; nhãn protocol/version chính xác.
- TC-UX1-P07-S04 — P07-STAR: auto run và run chọn tâm tay dùng đúng `start_point`; overlay tâm/tia/vòng tròn theo tọa độ ảnh gốc và tạo hai lịch sử riêng.
- TC-UX1-P07-S05 — P07-VMAT: DRGS/DRMLC/DRCS tự nhận đúng cặp open/dynamic; ROI/segment/deviation và tolerance khớp kết quả pylinac.
- TC-UX1-P07-S06 — P07-CT: CatPhan 503/504/600/604 đi qua chuỗi ảnh, module metrics và origin/ROI adjustment; run chỉnh tay không overwrite run auto.
- TC-UX1-P07-S07 — P07-ACR: CT 464/MRI Large/MRI Medium mở đúng module/lát, structured metrics và overlays theo model.
- TC-UX1-P07-S08 — P07-CHEESE: TomoCheese/CIRS 062M trả đúng ROI HU/density và đường response; reference adjustment có snapshot.
- TC-UX1-P07-S09 — P07-HELIOS: đủ contrast scale/resolution/noise/uniformity/low contrast và ảnh module được chọn.
- TC-UX1-P07-S10 — P07-QUART: Quart DVT và biến thể còn public chạy đúng module/result; alias deprecated không tạo hai lịch sử giả cho một capability.
- TC-UX1-P07-S11 — P07-LOG: Dynalog và Trajectory Log 2.1/3.0/4.0 hợp lệ hiển thị actual/expected/difference, MLC/hold/fluence/Gamma; không tự gán kết luận khi chưa có rule.
- TC-UX1-P07-S12 — P07-PF: ảnh sai lệch biết trước trả chỉ số từng leaf/picket, histogram và overlay; MLC/profile khác không dùng nhầm.
- TC-UX1-P07-S13 — P07-WL: mỗi ảnh có vector BB–CAX; bộ góc đủ mới hiện tổng hợp/axis phù hợp, bộ thiếu vẫn trình bày đúng phần tính được.
- TC-UX1-P07-S14 — P07-WLMT: cấu hình nhiều BB/field qua form được ánh xạ đúng; kết quả ghép cặp và overlay không đảo target.
- TC-UX1-P07-S15 — P07-PLANAR: từng phantom/class trong catalog nhận đúng profile, các override tâm/góc/kích thước/ROI phản ánh trên run mới và kết quả tương ứng.
- TC-UX1-P07-S16 — P07-FPA: click vị trí profile đồng bộ ô số, centering/width/edge/normalization/metrics được truyền đúng và biểu đồ khớp structured result.
- TC-UX1-P07-S17 — P07-FA: dữ liệu legacy vẫn mở/chạy bằng class legacy, có nhãn mô-đun cũ; tạo bài mới mặc định đưa người dùng sang FPA.
- TC-UX1-P07-S18 — P07-NUCLEAR: đủ chín phép thử chạy fixture tương ứng; form/metric/ảnh không bị trộn giữa các phép thử.
- TC-UX1-P07-S19 — Cùng input/profile/tham số/version, adapter metric khớp gọi pylinac trực tiếp trong precision mapping đã định; RT-CONNECT không tính lại metric.
- TC-UX1-P07-S20 — Đổi đánh giá người dùng không đổi chỉ số; chọn lại tham số tạo lần tính mới; lịch sử và dữ liệu bàn giao cho P9 giữ đúng bộ tính/lớp/phiên bản/hàm băm và điều chỉnh; chức năng xuất PDF nghiệm thu tại P9.
- TC-UX1-P07-S21 — P07-CONTRIB: Quasar Light/Rad Scaling và Jaw Orthogonality chạy fixture riêng bằng đúng class pylinac, nhận đúng tham số UI, overlay/metric khớp `results_data()` và lưu nhãn nguồn contrib.

### Trường hợp lỗi và phục hồi P7

- TC-UX1-P07-E01 — Inventory wheel thêm/bỏ/đổi class nhưng registry chưa xử lý → build/release fail với diff có tên; không tự ẩn capability.
- TC-UX1-P07-E02 — Wheel/hash runtime khác lock hoặc worker import lỗi → readiness capability fail, job không được nhận; không fallback sang engine tự viết.
- TC-UX1-P07-E03 — Tệp đúng đuôi nhưng sai loại/số ảnh/model phantom/log version → lỗi ở preflight theo bài, giữ dữ liệu để thay đúng input.
- TC-UX1-P07-E04 — Click/kéo tâm/ROI/profile ngoài ảnh, NaN hoặc transform sau zoom sai → chặn run và đưa control về vị trí hợp lệ; không gửi tọa độ viewport như ảnh gốc.
- TC-UX1-P07-E05 — Starshot thiếu tia/scale sai/ảnh đảo không phù hợp → hiển thị lỗi pylinac đã ánh xạ, cho chỉnh tham số được hỗ trợ; không trả mm giả.
- TC-UX1-P07-E06 — PF thiếu picket/leaf, contrast thấp hoặc MLC profile sai → không gán leaf mất là đạt; cho đổi profile/crop và tạo run mới.
- TC-UX1-P07-E07 — WL thiếu góc/BB/field hoặc multi-target mapping không khớp → giữ kết quả từng ảnh tính được, không dựng tổng hợp/3D không đủ dữ liệu.
- TC-UX1-P07-E08 — Chuỗi CatPhan/ACR/Cheese/Helios/Quart thiếu module, UID lẫn series, lát trùng hoặc origin sai → nêu module/slice cần sửa, không ghép series tùy tiện.
- TC-UX1-P07-E09 — Planar phantom sát mép, sai orientation/inversion/SSD hoặc chọn nhầm model → dừng/cảnh báo theo class; override phải hiện rõ và tạo run mới.
- TC-UX1-P07-E10 — Calibration thiếu hệ số, sai đơn vị hoặc chọn TRS-398 2024 trong khi engine chưa hỗ trợ → không tính; hướng người dùng sửa và ghi đúng revision khả dụng.
- TC-UX1-P07-E11 — Log hỏng/CRC/version không hỗ trợ hoặc chỉ có một file Dynalog → không tạo fluence/Gamma giả; nêu tệp còn thiếu.
- TC-UX1-P07-E12 — Nuclear thiếu background/activity/time khi phép thử cần, frame/ROI không hợp lệ → lỗi đúng trường, không dùng default ngầm.
- TC-UX1-P07-E13 — Manual rule range chồng lấn/baseline 0/công thức không có đơn vị → không lưu cấu hình không nhất quán.
- TC-UX1-P07-E14 — Engine timeout/OOM/dependency crash → run FAILED có error code, input giữ để retry có hạn; không treo vô hạn hoặc nhân đôi result.
- TC-UX1-P07-E15 — Người dùng đánh giá Đạt khi engine thất bại → chỉ lưu đánh giá thủ công kèm trạng thái “Không thể phân tích”; không sinh metric PASS.
- TC-UX1-P07-E16 — API/result shape của một bài contrib thay đổi hoặc upstream bỏ class → inventory/contract test chặn release và nêu đúng capability; không ẩn bài, không fallback sang thuật toán tự viết và run cũ vẫn mở theo snapshot.

### Bất biến và điều kiện đóng P7

P7 chỉ đóng khi mọi gói P07-CAL…P07-CONTRIB và bài nhập tay có bằng chứng riêng; danh mục thực thi không còn bài chưa ánh xạ; mọi biểu mẫu/điều chỉnh/kết quả không lộ JSON/ID. Chỉ số và hình đã có hợp đồng để P9 xuất PDF, chưa yêu cầu PDF ở P7. Có tên trong danh mục, cài được pylinac hoặc chỉ chạy ba bài PF/WL/Starshot đều không đủ.

## P8 — PSQA và Gamma trong QA máy

**Đầu vào/phụ thuộc:** P7 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P08-01; B05/B06/B07. PSQA là nhóm bài, không màn hình độc lập trong sidebar.
**Trạng thái UX1.3 lúc lập kế hoạch:** yêu cầu mới. Engine 2D/3D cũ là dữ liệu kế thừa, không tự đóng Gamma pylinac.

### Trình tự triển khai P8

1. Nhận dữ liệu liều/vai trò P6 và bộ tích hợp pylinac P7; ánh xạ Gamma 1D/2D và chuyển DTA từ mm.
2. Làm biểu mẫu Chênh lệch liều (%), DTA (mm), chuẩn hóa, ngưỡng liều thấp và xem trước vùng tính.
3. Chạy tác vụ, hủy/thử lại, xem bản đồ/biểu đồ và vùng không tính được; kết quả Gamma 3D cũ chỉ đọc.
4. Bàn giao kết quả PSQA và dữ liệu báo cáo/xu hướng; P9/P10 hoàn thiện hai giao diện sử dụng dữ liệu này.

**Điểm chuyển bước:** Chỉ mở P9 sau khi gói VERIFY và HANDOFF của P8 đạt đúng điều kiện bên dưới.

### Luồng thao tác P8

1. Chọn PSQA, máy, liều tham chiếu và dữ liệu đo/đối chiếu; kiểm vai trò, đơn vị, dimension, spacing và hình học.
2. Điền “Chênh lệch liều (%)”, “Khoảng cách DTA (mm)”, chuẩn hóa, ngưỡng liều thấp và ngưỡng tỷ lệ đạt; ROI/resampling/gamma cap nằm trong “Điều chỉnh”.
3. RT-CONNECT chuyển DTA mm sang contract phần tử của pylinac theo profile spacing công bố; hiển thị tóm tắt trước khi enqueue.
4. Chạy `gamma_1d` hoặc `gamma_2d`, theo dõi tiến độ, xem tỷ lệ/map/profile/phân bố, chọn đánh giá và lưu.

### Gói công việc P8

- [ ] P08-W01 — `PylinacPsqaAdapter` cho `profile.gamma_1d`/`image.gamma_2d`; giữ input gốc, geometry validation, resampling và provenance.
- [ ] P08-W02 — Form luôn hiện ΔD (%), DTA (mm), global/local, low-dose threshold và pass-rate target; nâng cao có ROI/resampling/gamma cap và profile định dạng đo.
- [ ] P08-W03 — Queue status/retry/cancel và kết quả 1D/2D gồm map/profile, histogram, pass rate, evaluated/excluded/invalid counts và cảnh báo vùng không đánh giá.
- [ ] P08-W04 — Lịch sử/tính lại và dữ liệu cho PDF P9, xu hướng P10; kết quả nhập từ phần mềm khác có nhãn riêng; Gamma 3D cũ chỉ đọc với nguồn bộ tính, API mới từ chối 3D.
- [ ] P08-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P08-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P8

- TC-UX1-P08-S01 — Màn hình cơ bản hiển thị và bắt buộc ΔD (%) + DTA (mm); nhập 3%/3mm được lưu đúng như người dùng thấy.
- TC-UX1-P08-S02 — Profile Gamma 1D hợp lệ trả vector Gamma/pass rate khớp gọi `gamma_1d` trực tiếp cùng input/tham số/version.
- TC-UX1-P08-S03 — Hai plane 2D hợp lệ trả map/pass rate khớp `gamma_2d`; DTA mm được chuyển thành số phần tử đúng theo spacing snapshot.
- TC-UX1-P08-S04 — Global/local và low-dose threshold đúng mẫu số; evaluated/excluded/invalid counts hiển thị và cộng đúng tổng.
- TC-UX1-P08-S05 — Resampling được người dùng/profile chọn tạo grid chung, lưu spacing/transform và không thay file gốc.
- TC-UX1-P08-S06 — Mất trang rồi mở lại vẫn theo dõi đúng run; nhấn chạy lặp cùng idempotency không nhân đôi job.
- TC-UX1-P08-S07 — Nhập tỷ lệ Gamma từ phần mềm khác lưu như số liệu nhập, không sinh map hoặc gắn nhãn pylinac.
- TC-UX1-P08-S08 — Mở kết quả Gamma 3D lịch sử vẫn thấy đúng engine `gamma-nd-p8.2`, cấu hình và ảnh cũ; không tự tính lại bằng pylinac.

### Trường hợp lỗi và phục hồi P8

- TC-UX1-P08-E01 — Chỉ có RTDOSE hoặc chỉ có CT/RTSTRUCT → chỉ thiếu comparison, không chạy Gamma.
- TC-UX1-P08-E02 — Relative dose không có calibration mà chọn absolute → yêu cầu dữ liệu phù hợp.
- TC-UX1-P08-E03 — Sai origin/orientation/grid/Frame of Reference hoặc vùng chồng lấp rỗng → không tự alignment để nâng pass rate.
- TC-UX1-P08-E04 — NaN/ngoài miền/cutoff loại hết điểm → không tính 100% đạt.
- TC-UX1-P08-E05 — Redis/worker lỗi hoặc completion sau delete → retry có hạn và scope/tombstone check, không kết quả trùng.
- TC-UX1-P08-E06 — ΔD hoặc DTA rỗng/0/âm/NaN, nhập nhầm dấu thập phân → lỗi ngay trường, giữ tệp đã chọn.
- TC-UX1-P08-E07 — DTA mm chia spacing không biểu diễn được bằng contract phần tử của `gamma_2d` → `GAMMA_DTA_GRID_INCOMPATIBLE`; không làm tròn âm thầm.
- TC-UX1-P08-E08 — Người dùng yêu cầu Gamma 3D mới → `PYLINAC_GAMMA_3D_UNAVAILABLE`, giải thích phiên bản engine chỉ có 1D/2D; không fallback engine cũ.
- TC-UX1-P08-E09 — Registry/hàm pylinac đổi signature hoặc result shape → contract test chặn release; run cũ vẫn mở từ snapshot.
- TC-UX1-P08-E10 — Pass-rate target bị thay đổi sau tính → chỉ cập nhật gợi ý đánh giá ở revision mới; map/metric Gamma không bị tính lại hoặc sửa.

### Bất biến và điều kiện đóng P8

Gamma pylinac 1D/2D chạy thật; biểu mẫu ΔD/DTA, ánh xạ tham số, đổi mm sang phần tử, tác vụ/lỗi, đánh giá/lịch sử và dữ liệu cho P9/P10 đạt. PDF và xu hướng đóng tại P9/P10. Không quảng bá Gamma 3D mới và không suy từ một mẫu thử sang mọi định dạng đo.

## P9 — PDF tùy chỉnh ngay tại kết quả

**Đầu vào/phụ thuộc:** P8 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P09-01; B03/B09. Không còn Report Builder là mục chính.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P9

1. Nhận chỉ số và hình có lớp phân tích từ P7/P8; dựng bộ chọn dòng/cột/hình theo bài.
2. Dùng cùng bản chụp cho xem trước và PDF; thêm phông chữ tiếng Việt và bảng qua trang.
3. Kiểm ẩn mọi khối, đổi nhãn, hình tâm/đường/vùng, trang dài, lỗi dựng PDF và tải lại bản cũ.
4. Bàn giao PDF thực khớp xem trước, không lộ mã kỹ thuật và không đổi chỉ số nguồn.

**Điểm chuyển bước:** Chỉ mở P10 sau khi gói VERIFY và HANDOFF của P9 đạt đúng điều kiện bên dưới.

### Luồng thao tác P9

1. Mở bài đã lưu → Xuất PDF; thấy preview và các phần có thể chọn.
2. Chọn dòng/cột/ảnh/lớp phân tích, nhãn, ghi chú, tiêu đề/logo/khổ giấy; lưu mẫu nếu muốn.
3. Xem trước rồi tải PDF; sau này mở lại đúng bản hoặc tạo bản mới.

### Gói công việc P9

- [ ] P09-W01 — Tích hợp editor theo ngữ cảnh kết quả, bộ chọn từng dòng/cột/ảnh, mọi khối đều ẩn được.
- [ ] P09-W02 — Mở rộng snapshot/layout/render contract, định dạng số/locale, tránh chỉnh metric gốc qua template.
- [ ] P09-W03 — Renderer dùng ảnh+overlays thật, font tiếng Việt, bảng qua trang, preview cùng engine.
- [ ] P09-W04 — Export idempotency theo snapshot/layout/renderer và history tải lại, deletion propagation.
- [ ] P09-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P09-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P9

- TC-UX1-P09-S01 — Ẩn/chọn/sắp xếp dòng hoặc thay nhãn không đổi giá trị đã lưu và PDF đúng lựa chọn.
- TC-UX1-P09-S02 — Starshot PDF có thể hiện đường tia/tâm/vòng tròn, hoặc chỉ ảnh gốc theo người dùng.
- TC-UX1-P09-S03 — Đổi mẫu sau khi xuất không đổi PDF cũ; tải lại bytes cùng bản nếu tệp còn tồn tại.
- TC-UX1-P09-S04 — Xuất mẫu mặc định từ kết quả trong hai thao tác: mở PDF và tải; tùy chỉnh không phải bước bắt buộc.

### Trường hợp lỗi và phục hồi P9

- TC-UX1-P09-E01 — Ẩn toàn bộ nội dung → báo chưa chọn nội dung, không tải PDF trắng.
- TC-UX1-P09-E02 — Ảnh thiếu/font lỗi/dữ liệu quá dài → báo đúng lỗi hoặc xuống trang; không tràn/cắt âm thầm.
- TC-UX1-P09-E03 — Bấm xuất lặp/mất mạng → dùng idempotency, giữ lựa chọn.
- TC-UX1-P09-E04 — HTML/script trong ghi chú/logo nguồn ngoài → escape/chặn thực thi, không chạy mã người dùng.
- TC-UX1-P09-E05 — Bài đã bị xóa khi render → kiểm tombstone, không phát hành bản mới ngoài phạm vi.
- TC-UX1-P09-E06 — Hình preview và PDF dùng scale khác → test hình thất bại, sửa transform chung.

### Bất biến và điều kiện đóng P9

PDF thực được render và kiểm cả text/ảnh, không JSON/ID, chữ Việt đúng, mọi block tùy chọn; không chỉ test download trả HTTP200.

## P10 — Xu hướng theo máy và bài, gắn lịch sử

**Đầu vào/phụ thuộc:** P9 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P10-01; B07/B08. Xu hướng là thẻ trong QA máy.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P10

1. Đưa Xu hướng vào khu kiểm tra; lọc theo máy/bài/chỉ số và phiên bản định nghĩa.
2. Xây chuỗi số liệu, chuẩn so sánh, dấu bảo trì và liên kết từ điểm đến kết quả.
3. Kiểm phân tích lại, xóa/khôi phục, sửa đánh giá, khác đơn vị và dữ liệu lớn.
4. Bàn giao biểu đồ có xuất PDF và đối chiếu được mọi điểm với lịch sử.

**Điểm chuyển bước:** Chỉ mở P11 sau khi gói VERIFY và HANDOFF của P10 đạt đúng điều kiện bên dưới.

### Luồng thao tác P10

1. Từ QA máy hoặc một kết quả mở Xu hướng, giữ máy/bài/chỉ số.
2. Chọn khoảng ngày/chuẩn so sánh; xem giá trị, sự kiện bảo trì và định nghĩa.
3. Bấm điểm mở bài; xóa/khôi phục bài làm series cập nhật đúng.

### Gói công việc P10

- [ ] P10-W01 — Chuyển TrendPage thành panel, deep link/filter và trạng thái rỗng.
- [ ] P10-W02 — Chuẩn hóa series theo metric definition/unit/profile; phân tách giá trị đo và đánh giá người dùng.
- [ ] P10-W03 — Projection rebuild idempotent cho reanalysis/delete/restore/assessment; baseline có version.
- [ ] P10-W04 — Phân trang/giới hạn truy vấn/downsampling, overlay bảo trì và chọn xuất biểu đồ.
- [ ] P10-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P10-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P10

- TC-UX1-P10-S01 — Từ kết quả mở đúng chỉ số và điểm; các đơn vị/phương pháp khác không bị trộn vô danh.
- TC-UX1-P10-S02 — Thay baseline chỉ đổi đường so sánh phù hợp, không sửa số đo cũ.
- TC-UX1-P10-S03 — Xóa/restore nhiều lần không để điểm ma/trùng; reanalysis có chính sách chọn run rõ.
- TC-UX1-P10-S04 — Danh sách lớn đáp ứng ngân sách truy vấn và hiển thị extrema cần xem.

### Trường hợp lỗi và phục hồi P10

- TC-UX1-P10-E01 — Không có điểm → trạng thái trống, không vẽ 0 giả.
- TC-UX1-P10-E02 — Metric đổi đơn vị/definition → tách series hoặc yêu cầu chọn, không nối liền gây hiểu nhầm.
- TC-UX1-P10-E03 — Projection cập nhật chậm → hiện đang cập nhật và thử lại có hạn, không báo đã xóa nhưng vẫn coi điểm hợp lệ.
- TC-UX1-P10-E04 — Baseline thiếu/0 không phù hợp → không tính phần trăm chia0.
- TC-UX1-P10-E05 — Sai scope hoặc khoảng ngày quá lớn → từ chối/giới hạn có thông báo, không quét toàn DB.

### Bất biến và điều kiện đóng P10

Điểm trend truy ngược đúng bài, xóa/restore và phiên bản tiêu chí đã thử; không còn mục Xu hướng riêng ở sidebar.

## P11 — Thư viện nội bộ, cộng đồng, bài viết và PDF

**Đầu vào/phụ thuộc:** P10 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P11-01; B11/B13/B14. Nền dùng chung cho cả hai nhóm nội dung; P16 hoàn thiện phác đồ chuyên biệt.
**Trạng thái UX1.3 lúc lập kế hoạch:** Chưa bắt đầu.

### Trình tự triển khai P11

1. Làm W01/W02 trước: dữ liệu, chuyển bản cũ về nội bộ, hai tuyến đọc và chính sách tệp/kết quả tìm.
2. Làm W03/W04/W05: tra cứu, viết bài/tự lưu, PDF; chạy từ nhập đến đăng nội bộ trước.
3. Làm W06/W07/W08: đăng bản chia sẻ chọn tệp, cập nhật/thu hồi và thùng rác; thử hai đơn vị ở từng bước.
4. Làm W09/W10, chạy toàn bộ tình huống P11, đo tìm kiếm; bàn giao cổng thư viện và nguồn cơ sở cho P12.

**Điểm chuyển bước:** Chỉ mở P12 sau khi gói VERIFY và HANDOFF của P11 đạt đúng điều kiện bên dưới.

### Luồng thao tác P11

1. Đăng nhập, chọn Nội bộ đơn vị hoặc Cộng đồng; người chưa có đơn vị vẫn đọc Cộng đồng.
2. Chọn nhóm, tìm có/không dấu, lọc nguồn/loại/chủ đề, đọc bài với mục lục và PDF.
3. Thành viên đơn vị viết bài hoặc tải tài liệu, tự lưu nháp, xem trước và đăng trong đơn vị.
4. Chọn Chia sẻ cộng đồng, chọn từng tệp và xem trước bản chia sẻ; đăng bằng nút nêu rõ phạm vi.
5. Sửa bài tạo nháp nội bộ; cập nhật cộng đồng khi chủ động đăng phiên bản mới.
6. Lưu bài để đọc lại; thu hồi chia sẻ, lưu trữ hoặc xóa/khôi phục trong phạm vi đơn vị nguồn.

### Gói công việc P11

- [ ] P11-W01 — Tạo bài/phiên bản/bản chia sẻ/tệp/dấu trang/nguồn cơ sở; chuyển dữ liệu thư viện cũ về nội bộ, tách quy tắc chạy sang cài đặt P7; ghi số lượng và ánh xạ phiên bản.
- [ ] P11-W02 — Hai tuyến đọc riêng và kiểm phạm vi ngay từ truy vấn: đơn vị, cộng đồng, bản nháp, lịch sử, hình, trích đoạn, số đếm, bộ lọc, so sánh và dữ liệu nguồn số.
- [ ] P11-W03 — Trang tra cứu kiểu cổng tri thức, hai phạm vi/hai nhóm, tìm kiếm có dấu/không dấu, danh sách/thẻ/phân trang, mục lục và dấu trang.
- [ ] P11-W04 — Soạn trực quan, bảng/hình/công thức/trích dẫn, tự lưu, đăng nội bộ, sửa đồng thời và phục hồi phiên bản thành nháp.
- [ ] P11-W05 — Tải PDF/ảnh, kiểm loại/dung lượng, tiến độ theo tệp, trình đọc tiếng Việt, trích văn bản và hình thu nhỏ có cùng phạm vi.
- [ ] P11-W06 — Xem trước/đăng/cập nhật bản chia sẻ; chọn rõ tệp; chặn tham chiếu nội bộ chưa chọn; xử lý nhấn lặp và lỗi giữa giao dịch.
- [ ] P11-W07 — Thu hồi tức thời với yêu cầu mới; chặn cả đường dẫn PDF, ảnh thu nhỏ và trang đã lưu; tác vụ chỉ mục cũ không được đăng lại.
- [ ] P11-W08 — Lưu trữ/thùng rác/khôi phục nội bộ, thời hạn 30 ngày, dọn vật lý có kiểm tham chiếu và tác động dấu trang.
- [ ] P11-W09 — Nguồn có bệnh viện/bối cảnh/phiên bản; cấu trúc α/β và giới hạn cơ sở để P13/P15 dùng; không chờ giao diện phác đồ P16.
- [ ] P11-W10 — Gắn hướng dẫn vào bài kiểm tra mà không đổi quy tắc chạy; mọi chữ hệ thống trên màn đọc/soạn/tệp/lỗi bằng tiếng Việt.
- [ ] P11-VERIFY — Thực hiện toàn bộ tình huống bên dưới với hai đơn vị A/B, hai thành viên A, một thành viên B, một người chưa có đơn vị và khách; kiểm nội dung thật và tệp.
- [ ] P11-HANDOFF — Ghi bằng chứng phạm vi, đăng/thu hồi, sửa/khôi phục, PDF/tìm kiếm và chuyển dữ liệu; chỉ mở P12 khi P11 đạt.

### Trường hợp chạy đúng P11

- TC-UX1-P11-S01 — Hai thành viên A cùng tạo/sửa/đăng/thu hồi một bài của A; không có vai trò người duyệt.
- TC-UX1-P11-S02 — A tải bài kèm PDF; trước chia sẻ chỉ thành viên A tìm, đọc và tải được.
- TC-UX1-P11-S03 — A chia sẻ bản có một trong hai PDF; B và người chưa có đơn vị đọc đúng nội dung và đúng một PDF được chọn.
- TC-UX1-P11-S04 — A sửa nháp sau chia sẻ; B vẫn đọc bản đang chia sẻ; khi A cập nhật thì nội dung/tệp thay đổi đồng bộ.
- TC-UX1-P11-S05 — Tìm “dong tam” khớp “đồng tâm”; lọc nguồn/nhóm giữ lại khi vào bài rồi quay lại; số đếm theo đúng phạm vi.
- TC-UX1-P11-S06 — Bài chỉ có văn bản, chỉ có PDF hoặc có nhiều tệp đều lưu và đăng được với thông tin tối thiểu.
- TC-UX1-P11-S07 — PDF có văn bản tìm được từ và mở đúng trang; PDF ảnh xem được với trạng thái chưa tìm được bên trong.
- TC-UX1-P11-S08 — Nháp đã tự lưu mở lại đúng sau đăng nhập; khôi phục phiên bản cũ tạo nháp mới và giữ lịch sử.
- TC-UX1-P11-S09 — Dấu trang thuộc cá nhân; A thu hồi thì dấu trang của B chỉ còn nhãn bài không được chia sẻ, không còn nội dung nguồn.
- TC-UX1-P11-S10 — Lưu trữ/xóa thu hồi bản cộng đồng; khôi phục đưa bài về nội bộ và cần chọn chia sẻ lại.
- TC-UX1-P11-S11 — Dữ liệu cũ có trạng thái PUBLISHED chuyển thành đăng nội bộ; không có PDF cũ tự xuất hiện cộng đồng.
- TC-UX1-P11-S12 — Mở hướng dẫn từ bài kiểm tra rồi quay lại giữ dữ liệu; sửa hướng dẫn không thay ngưỡng hay kết quả cũ.
- TC-UX1-P11-S13 — Cùng bệnh viện nguồn nhưng khác đơn vị sở hữu không cấp thêm quyền; người nhiều đơn vị đổi nơi làm việc không mang nháp theo.
- TC-UX1-P11-S14 — Đăng cùng khóa nhiều lần chỉ tạo một bản; lỗi chuẩn bị tệp giữ nguyên bản chia sẻ trước đó.
- TC-UX1-P11-S15 — Tệp được nhiều phiên bản tham chiếu vẫn mở từ bản hợp lệ sau khi xóa một bài; không xóa nhầm đối tượng.
- TC-UX1-P11-S16 — Tìm kiếm tiêu đề phản hồi trong ngân sách đã định; văn bản PDF xuất hiện sau xử lý nền và không ảnh hưởng tác vụ QA.

### Trường hợp lỗi và phục hồi P11

- TC-UX1-P11-E01 — B đoán đường dẫn bài/phiên bản/PDF/ảnh thu nhỏ của A chưa chia sẻ → 404; không trả tiêu đề, số trang hay vị trí tệp.
- TC-UX1-P11-E02 — Khách mở cộng đồng hoặc tệp → yêu cầu đăng nhập; người có phiên nhưng chưa có đơn vị vẫn đọc được cộng đồng.
- TC-UX1-P11-E03 — B gọi sửa/xóa/thu hồi bản của A → bị từ chối phía máy chủ; nội dung A không đổi.
- TC-UX1-P11-E04 — Gợi ý, tổng kết quả, bộ lọc bệnh viện hoặc đoạn trích lấy từ nháp/nguồn nội bộ → kiểm thử không đạt; sửa truy vấn trước khi phát hành.
- TC-UX1-P11-E05 — Phiên hết hạn lúc lưu/tải → giữ phần đang gõ trong trang, yêu cầu đăng nhập lại, không gửi bài sang đơn vị khác.
- TC-UX1-P11-E06 — Hai người sửa cùng revision → 409 và chọn cách hợp nhất; không tự ghi đè.
- TC-UX1-P11-E07 — Mất mạng khi tự lưu → báo chưa lưu và thử lại; không hiện “Đã lưu” khi máy chủ chưa xác nhận.
- TC-UX1-P11-E08 — PDF quá lớn/rỗng/hỏng/mật khẩu hoặc ảnh quá giới hạn → lỗi theo tệp, tệp hợp lệ khác tiếp tục; không xóa bản cũ.
- TC-UX1-P11-E09 — PDF ảnh không trích được chữ hoặc xử lý quá thời gian → vẫn xem PDF hợp lệ, nêu thiếu tìm kiếm nội dung, cho thử lại.
- TC-UX1-P11-E10 — Nội dung dán có script/liên kết nguy hiểm → làm sạch hoặc báo trường cần sửa; bản xem trước và bản đọc có cùng quy tắc.
- TC-UX1-P11-E11 — Chia sẻ bài chứa ảnh/trích dẫn dẫn tới tệp nội bộ chưa chọn → chỉ rõ liên kết; sửa hoặc chọn tệp trước khi đăng, không lộ tên tệp ở bản cộng đồng.
- TC-UX1-P11-E12 — A thu hồi khi B còn trang cũ hoặc URL PDF → yêu cầu đọc/tải mới bị chặn; chỉ mục hoặc bộ nhớ đệm cũ không mở lại dữ liệu.
- TC-UX1-P11-E13 — Xóa/thu hồi và đăng đồng thời → khóa phiên bản chặn tác vụ đến sau; không tự tái công bố bài đã xóa.
- TC-UX1-P11-E14 — So sánh hai tài liệu khi một nguồn không còn được đọc → chỉ giữ nguồn hợp lệ, không hiển thị đoạn cũ từ nguồn bị thu hồi.
- TC-UX1-P11-E15 — Tệp trùng của đơn vị B được cảnh báo cho A → không đạt; chỉ kiểm trùng trong đơn vị A.
- TC-UX1-P11-E16 — Yêu cầu dọn bài chưa vào thùng rác hoặc tệp còn tham chiếu → không xóa vật lý; nêu lý do tại đơn vị sở hữu.
- TC-UX1-P11-E17 — Chuyển dữ liệu cũ không xác định hướng dẫn/quy tắc → giữ bản gốc, liệt kê đối chiếu; không tự đặt công khai.
- TC-UX1-P11-E18 — Thiếu nguồn/không có bài khớp → hiển thị chưa có tài liệu và nút bổ sung đúng nơi; không tạo số liệu hay kết quả giả.

### Bất biến và điều kiện đóng P11

Hai phạm vi dùng được xuyên suốt đọc, tìm, tệp, sửa, đăng, thu hồi và thùng rác; cùng đơn vị ngang quyền, khác đơn vị chỉ đọc bản chia sẻ. Giao diện tiếng Việt, tự lưu và PDF có bằng chứng thật. Không đóng P11 bằng việc chỉ thêm một cột public hoặc hai thẻ giao diện. Nhóm Phác đồ đã dùng được như bài/PDF trong P11; phần biểu mẫu chuyên biệt và bảng nguồn đầy đủ thuộc P16.

## P12 — Một trang công cụ sinh học, tính trước lưu sau

**Đầu vào/phụ thuộc:** P11 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P12-01; B02/B03/B10. Chỉ một mục điều hướng chính.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P12

1. Dùng khung P3 và nguồn P11 để dựng trang sáu công cụ với một vùng đang mở.
2. Thêm trạng thái nhập tạm, thao tác tính và lưu tùy chọn; nối bộ tính sẵn có khi hợp đồng phù hợp.
3. Giữ trường nhập khi chuyển công cụ, xử lý chưa có nguồn và đổi đơn vị; phần chưa làm có nhãn rõ.
4. Nghiệm thu khung/đường dẫn/lưu dữ liệu nhập; mở P13 để hoàn thiện phép tính đầu tiên.

**Điểm chuyển bước:** Chỉ mở P13 sau khi gói VERIFY và HANDOFF của P12 đạt đúng điều kiện bên dưới.

### Luồng thao tác P12

1. Mở Công cụ sinh học, chọn một trong sáu công cụ.
2. Nhập ở panel trái, xem kết quả phải; đổi công cụ giữ dữ liệu trong phiên.
3. Mở tùy chọn nâng cao nếu cần, lưu phép tính và đặt tên sau khi đã tính.

### Gói công việc P12

- [ ] P12-W01 — BiologicalToolHub với sáu panel, một active panel và kích thước compact.
- [ ] P12-W02 — Endpoint tính không bắt scenario/case, adapter reuse engine hiện có.
- [ ] P12-W03 — State nháp theo phiên/đơn vị và lưu worksheet tùy chọn; không lưu mỗi phím gõ.
- [ ] P12-W04 — Chuyển route cũ, tách hoàn toàn QA/patient selector, lỗi localized và source drawer.
- [ ] P12-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P12-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P12

- TC-UX1-P12-S01 — Mở BED/EQD2 nhập/tính được ngay, không tạo kịch bản hay chọn hồ sơ.
- TC-UX1-P12-S02 — Sáu công cụ hiện như bộ chọn gọn, không sáu trang dài liên tiếp.
- TC-UX1-P12-S03 — Chuyển panel rồi quay lại giữ giá trị; đăng xuất/chuyển đơn vị không lộ draft cũ.
- TC-UX1-P12-S04 — Lưu tùy chọn rồi mở lại đúng input/result/source snapshot.

### Trường hợp lỗi và phục hồi P12

- TC-UX1-P12-E01 — Không có nguồn thư viện → vẫn tự nhập giá trị có nhãn người dùng chọn, không chặn mọi phép tính.
- TC-UX1-P12-E02 — Tắt advanced → không mất giá trị nhưng nhãn kết quả vẫn nêu giả định nâng cao đang dùng.
- TC-UX1-P12-E03 — Lỗi lưu sau tính → kết quả còn trên màn hình, cho lưu lại; không bắt tính từ đầu.
- TC-UX1-P12-E04 — Đường dẫn sinh học cũ → mở panel phù hợp, không trang404.
- TC-UX1-P12-E05 — Chưa triển khai tool → không trả phép tính giả; mốc bàn giao đầy đủ phải hoàn thành P13–P16.

### Bất biến và điều kiện đóng P12

Hub gọn và stateless contract đạt; P12 shell không tự đóng các engine P13–P16.

## P13 — BED/EQD2, đồ thị theo tổng liều và hệ số α/β

**Đầu vào/phụ thuộc:** P12 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P13-01; B10/B12.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P13

1. Làm biểu mẫu D/n/d nhất quán và lựa chọn nguồn α/β từ cấu trúc P11.
2. Tích hợp bộ tính BED/EQD2, đồ thị theo tổng liều ở hai chế độ giữ số buổi/giữ liều mỗi buổi.
3. Đối chiếu bộ giá trị đã biết, miền sai, làm tròn, số buổi nguyên và nguồn bị thu hồi.
4. Bàn giao phép tính, đồ thị và trang đã lưu mở lại đúng; P14 tái sử dụng bộ tính.

**Điểm chuyển bước:** Chỉ mở P14 sau khi gói VERIFY và HANDOFF của P13 đạt đúng điều kiện bên dưới.

### Luồng thao tác P13

1. Nhập D+n hoặc d+n; chọn mô/α/β từ nguồn hoặc tự nhập.
2. Tính, xem BED/EQD2 và công thức trong khung nhỏ.
3. Mở đồ thị D, chọn giữ n hoặc giữ d; lưu phép tính nếu muốn.

### Gói công việc P13

- [ ] P13-W01 — Typed form không cho D/n/d mâu thuẫn, đơn vị và parse số theo locale.
- [ ] P13-W02 — Engine LQ với unit/golden tests và precision, segments khi cần.
- [ ] P13-W03 — Đồ thị hai chế độ giữ n/giữ d, phân biệt điểm n nguyên và đường minh họa.
- [ ] P13-W04 — Nguồn α/β/uncertainty range, source snapshot và worksheet lưu tùy chọn.
- [ ] P13-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P13-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P13

- TC-UX1-P13-S01 — D60,n30,a10 → BED72/EQD260; D50,n25,a3 → BED83.333333…/EQD250 theo tolerance số học đã định.
- TC-UX1-P13-S02 — Đổi chế độ nhập cập nhật đại lượng phụ thuộc nhất quán.
- TC-UX1-P13-S03 — Đồ thị giữ n cong theo biểu thức, giữ d tuyến tính; điểm phác đồ nguyên được đánh dấu.
- TC-UX1-P13-S04 — Chọn nguồn cụ thể ghi đúng tác giả/năm/mô/đáp ứng, không tự chọn trung điểm range.

### Trường hợp lỗi và phục hồi P13

- TC-UX1-P13-E01 — n=0/n không nguyên/a=0/liều âm/NaN/Infinity → lỗi đúng trường, không giá trị vô cực; số buổi nguyên lẻ vẫn hợp lệ.
- TC-UX1-P13-E02 — D=0 → kết quả0 hợp lệ theo miền công cụ; không chia0 ở biểu đồ hoặc so sánh.
- TC-UX1-P13-E03 — D/n/d không đồng nhất khi nhập API → từ chối hoặc chỉ chấp nhận cặp authoritative đã định.
- TC-UX1-P13-E04 — Nguồn α/β khác mục tiêu/mô → yêu cầu chọn lại hoặc tự nhập có ghi chú.
- TC-UX1-P13-E05 — Đồ thị quá nhiều điểm → giới hạn/tái lấy mẫu có thông báo, không khóa trình duyệt.

### Bất biến và điều kiện đóng P13

Test công thức/đồ thị/locale/source và màn hình một công cụ gọn đạt; không thêm cơ chế khuyến nghị phác đồ.

## P14 — So sánh hai phác đồ đơn giản

**Đầu vào/phụ thuộc:** P13 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P14-01; B10.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P14

1. Tạo hai biểu mẫu tên tự chọn, sao chép/hoán đổi và chung thông tin nguồn cần thiết.
2. Dùng kết quả P13 để tính khác biệt tuyệt đối/phần trăm, nêu rõ mẫu số.
3. Kiểm không chia cho 0, khác α/β/định nghĩa, thông tin thiếu và cập nhật nguồn.
4. Bàn giao bảng/biểu đồ cạnh nhau và phiên bản lưu được; không tự xếp tốt/xấu.

**Điểm chuyển bước:** Chỉ mở P15 sau khi gói VERIFY và HANDOFF của P14 đạt đúng điều kiện bên dưới.

### Luồng thao tác P14

1. Nhập A/B trên cùng trang với α/β chung cho đích đang xem.
2. Bấm so sánh để thấy D/BED/EQD2 và chênh lệch.
3. Sao chép hoặc đổi vị trí hai phác đồ; lưu khi cần.

### Gói công việc P14

- [ ] P14-W01 — Hai form gọn đồng cấu trúc, tên tự chọn và nút copy/swap.
- [ ] P14-W02 — Dùng chung engine BED, chênh lệch tuyệt đối/phần trăm có mẫu số rõ.
- [ ] P14-W03 — Bảng/biểu đồ cạnh nhau, thông tin α/β và nguồn; không rank tốt/xấu tự động.
- [ ] P14-W04 — Kiểm lưu/mở lại/sửa phiên bản, biểu đồ và số làm tròn nhất quán.
- [ ] P14-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P14-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P14

- TC-UX1-P14-S01 — A=B cho chênh lệch0; swap đổi dấu chênh lệch theo định nghĩa.
- TC-UX1-P14-S02 — A/B d=2 thì EQD2 bằng tổng liều của từng phác đồ theo mô hình cơ bản.
- TC-UX1-P14-S03 — Copy A sang B không liên kết hai draft khiến sửa B đổi A.
- TC-UX1-P14-S04 — Tính không cần lưu hai scenario trước.

### Trường hợp lỗi và phục hồi P14

- TC-UX1-P14-E01 — Một bên chưa đủ → giữ bên còn lại và chỉ lỗi thiếu.
- TC-UX1-P14-E02 — α/β hoặc đích khác nhau → không gắn nhãn tương đương chung, chỉ so sánh có bối cảnh.
- TC-UX1-P14-E03 — Mẫu số0 → không hiển thị Infinity/% giả.
- TC-UX1-P14-E04 — Tổng nhiều đoạn khác phân liều → tính từng đoạn, không thay bằng liều trung bình.
- TC-UX1-P14-E05 — Thay nguồn khi mở lại → giữ snapshot cũ cho tới lúc người dùng tính lại.

### Bất biến và điều kiện đóng P14

Tính A/B đúng, UI gọn và không diễn giải chênh BED thành lựa chọn điều trị tốt hơn.

## P15 — Tái xạ và bù buổi chiếu với giả định rõ

**Đầu vào/phụ thuộc:** P14 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P15-01; B10/B12. Hai panel trong cùng công cụ sinh học, không hồ sơ QA.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P15

1. Hoàn thiện tái xạ trước: nhiều đợt, cùng mô/định nghĩa, tổng chưa hiệu chỉnh và giả định hồi phục khi bật.
2. Hoàn thiện bù buổi chiếu sau: đã thực hiện/còn lại, mục tiêu tương đương và giải một ẩn.
3. Kiểm nguồn từ P11, thời gian/giá trị âm, thiếu giả định, không có nghiệm và làm tròn.
4. Bàn giao hai công cụ gọn, tính/mở lại đúng và giữ giả định; không chờ giao diện chuyên biệt P16.

**Điểm chuyển bước:** Chỉ mở P16 sau khi gói VERIFY và HANDOFF của P15 đạt đúng điều kiện bên dưới.

### Luồng thao tác P15

1. Tái xạ: nhập hai đợt cùng mô/metric, xem từng đợt và tổng vô hướng; thêm đợt nếu cần.
2. Bù buổi chiếu: nhập kế hoạch, thực tế đã chiếu và phần còn lại; so sánh hoặc giải một ẩn đã chọn.
3. Chỉ mở hồi phục/hiệu chỉnh thời gian khi muốn dùng; hiển thị giả định trong kết quả.

### Gói công việc P15

- [ ] P15-W01 — Tái xạ: courses/segments, kiểm cùng a/metric/context, tổng chưa hiệu chỉnh và residual khi có r.
- [ ] P15-W02 — Bù buổi chiếu: delivered/planned/remaining riêng, giải một ẩn và đối chiếu mục tiêu.
- [ ] P15-W03 — Advanced time/recovery parameters có nguồn/đơn vị, mặc định không hồi phục và không time correction.
- [ ] P15-W04 — UI hai panel gọn, lưu source/model snapshot; tests riêng cho hai loại công cụ.
- [ ] P15-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P15-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P15

- TC-UX1-P15-S01 — r=0 giữ tổng gốc; r=1 chỉ loại contribution đợt được chọn, không trừ liều đợt mới.
- TC-UX1-P15-S02 — Tái xạ nhiều đoạn tính theo từng đoạn; hiển thị rõ đây là tổng vô hướng.
- TC-UX1-P15-S03 — Phương án không gián đoạn/không đổi có kết quả bằng kế hoạch ban đầu.
- TC-UX1-P15-S04 — Thay nghiệm giải vào phương trình BED phần còn lại khớp mục tiêu trong tolerance; hiển thị sai khác khi làm tròn.

### Trường hợp lỗi và phục hồi P15

- TC-UX1-P15-E01 — a/metric/cơ quan giữa đợt không tương thích → xem từng đợt, không cộng chung sai nghĩa.
- TC-UX1-P15-E02 — Dmax khác vị trí → không gọi là cumulative spatial dose hay kết luận an toàn cơ quan.
- TC-UX1-P15-E03 — r<0 hoặc >1/ngày không hợp lệ → lỗi từng trường.
- TC-UX1-P15-E04 — Số buổi còn lại0 hoặc BED còn lại âm → không giải liều dương giả; nêu mục tiêu không khả dụng.
- TC-UX1-P15-E05 — Thiếu K/Tk khi bật thời gian → yêu cầu nhập đủ hoặc tắt; không tự điền từ tên bệnh.
- TC-UX1-P15-E06 — Nghiệm đề xuất vượt miền mô hình/profile → nêu giới hạn, không tự khuyến nghị lịch tăng liều.

### Bất biến và điều kiện đóng P15

Hai bộ test tái xạ/bù riêng đạt; kết quả nêu mô hình và giả định nhưng không chiếm màn hình bằng cảnh báo lớn; không sinh lịch điều trị tự động.

## P16 — Phác đồ điều trị, giới hạn liều, α/β và nguồn

**Đầu vào/phụ thuộc:** P15 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P16-01; B11/B12/B13/B14. Tách hoàn thành chức năng với độ đầy đủ tuyển tập.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P16

1. Nhận cổng bài/PDF/phạm vi P11 và các công cụ P13–P15; mở rộng biểu mẫu phác đồ theo bệnh viện.
2. Làm bảng thể tích đích/cơ quan/HI/CI, phối hợp điều trị và nguồn trang cụ thể.
3. Nối giới hạn/αβ vào công cụ; thử cùng bệnh khác bệnh viện, nội bộ/cộng đồng và thu hồi nguồn.
4. Nghiệm thu chức năng bằng dữ liệu tổng hợp; ghi riêng nguồn thật đã có/còn thiếu; bàn giao P17.

**Điểm chuyển bước:** Chỉ mở P17 sau khi gói VERIFY và HANDOFF của P16 đạt đúng điều kiện bên dưới.

### Luồng thao tác P16

1. Mở nhánh Phác đồ điều trị; lọc bệnh cảnh/bệnh viện/phân liều.
2. Đọc phác đồ với liều, phối hợp điều trị, PTV, OAR, HI/CI, lưu ý và nguồn.
3. Tra giới hạn/α/β từ toolkit hoặc đọc nguồn; thêm/sửa bằng form và bảng, so sánh các nguồn.

### Gói công việc P16

- [ ] P16-W01 — Schema source/version/TreatmentContext/DoseConstraint/AlphaBeta và form đủ trường BA.
- [ ] P16-W02 — Mở rộng tìm kiếm, trình đọc nguồn, bảng/biểu mẫu và phiên bản trên nền P11; kiểm phạm vi cả bảng số, nguồn trích dẫn và so sánh; không trình nhập JSON.
- [ ] P16-W03 — Dùng chung giới hạn/α/β với công cụ sinh học; chỉ chọn nguồn được phép đọc, lưu giá trị/trích dẫn đã dùng; thu hồi chặn chọn mới nhưng không sửa phép tính cũ.
- [ ] P16-W04 — Lập coverage register theo bệnh/bệnh viện, nhập nguồn thực đã có, đánh dấu phần thiếu; không seed số ví dụ như dữ liệu chuẩn.
- [ ] P16-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P16-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P16

- TC-UX1-P16-S01 — Một phác đồ mẫu có nguồn thực lưu đủ bối cảnh, D/n, phối hợp mổ/hóa trị, PTV, OAR, định nghĩa HI/CI và trang trích dẫn.
- TC-UX1-P16-S02 — Hai bệnh viện có quy ước khác tồn tại cạnh nhau; chọn đúng bối cảnh trước khi áp dụng.
- TC-UX1-P16-S03 — Giới hạn/α/β ở toolkit giống bản nguồn trong thư viện, không có hai bảng tự lệch.
- TC-UX1-P16-S04 — Sửa nguồn tạo phiên bản mới, lịch sử phép tính/báo cáo vẫn truy bản cũ.
- TC-UX1-P16-S05 — Coverage phân biệt chưa có nguồn/thiếu trường/đã đối chiếu, không quảng bá đầy đủ mọi viện.
- TC-UX1-P16-S06 — A/B có phác đồ cùng bệnh nhưng khác bệnh cảnh; chỉ phác đồ A đã chia sẻ xuất hiện cạnh nguồn B, mỗi bên giữ bệnh viện và phiên bản.
- TC-UX1-P16-S07 — Thu hồi bài cộng đồng loại giới hạn/α/β khỏi chọn nguồn mới của B; phép tính B đã lưu giữ giá trị và trích dẫn, không mở tiếp PDF đã thu hồi.
- TC-UX1-P16-S08 — Sửa phác đồ nội bộ không đổi bảng số cộng đồng tới khi chủ động cập nhật bản chia sẻ.

### Trường hợp lỗi và phục hồi P16

- TC-UX1-P16-E01 — 105%/107% hoặc α/β không nguồn → không seed mặc định; yêu cầu nguồn khi đưa vào bảng tham khảo đã xác minh.
- TC-UX1-P16-E02 — Dmax so với D0.03cc, %Rx so Gy, HI khác công thức → không xem như cùng chỉ số.
- TC-UX1-P16-E03 — PDF scan/OCR số mờ → đánh dấu chưa đối chiếu và cho sửa trực quan, không tự dùng số đó làm constraint.
- TC-UX1-P16-E04 — Nguồn hỏng/hết truy cập/trùng phiên bản → giữ citation và báo trạng thái, không mất lịch sử.
- TC-UX1-P16-E05 — Tài liệu của đơn vị khác/chưa chủ động chia sẻ → không hiện trong tìm kiếm chung.
- TC-UX1-P16-E06 — Thiếu tài liệu bệnh viện → hoàn thiện chức năng trước, liệt kê nguồn cần người dùng bổ sung; không bịa tuyển tập.
- TC-UX1-P16-E07 — Bảng tham số/số đếm/tóm tắt làm lộ phác đồ nội bộ dù tuyến đọc bài đã chặn → không đạt; áp cùng phạm vi P11.
- TC-UX1-P16-E08 — Đang so sánh thì một nguồn bị thu hồi → yêu cầu mới không trả nguồn đó; không lưu bản so sánh mới bằng dữ liệu trái phạm vi.
- TC-UX1-P16-E09 — Đổi bệnh viện nguồn bị hiểu thành chuyển quyền sở hữu → không thay phạm vi ngầm; quyền vẫn theo đơn vị sở hữu bài.

### Bất biến và điều kiện đóng P16

Chức năng hai nhánh và bảng dùng chung đạt; gói nội dung chỉ đóng với danh mục nguồn/bệnh cảnh cụ thể đã đối chiếu. Không bắt đủ mọi bệnh viện mới được bàn giao phần mềm.

## P17 — DVH và chỉ số kế hoạch trong PSQA

**Đầu vào/phụ thuộc:** P16 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P17-01; B06/B11. Không mở thêm mục chính.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P17

1. Nhận hình học P6, kết quả PSQA P8 và nguồn theo bối cảnh P16; tích hợp DVH tại kết quả.
2. Làm bộ chọn cấu trúc, D/V có đơn vị, công thức HI/CI và đưa hình/chỉ số vào PDF.
3. Đối chiếu thể tích/liều chuẩn, khác khung tham chiếu, thiếu cấu trúc và vượt tài nguyên.
4. Bàn giao kết quả mở lại đúng, nguồn không vượt phạm vi, biểu đồ và PDF đã kiểm.

**Điểm chuyển bước:** Chỉ mở P18 sau khi gói VERIFY và HANDOFF của P17 đạt đúng điều kiện bên dưới.

### Luồng thao tác P17

1. Trong bài PSQA chọn xem liều/DVH, chọn RTDOSE/RTSTRUCT và CT khi profile cần.
2. Chọn cấu trúc, chỉ số và định nghĩa HI/CI; xem DVH/hình và dữ liệu đơn vị rõ.
3. Lưu lần phân tích, chọn dòng/hình cho PDF, mở nguồn tiêu chí khi cần.

### Gói công việc P17

- [ ] P17-W01 — Gắn DVH engine hiện có vào result workspace chung, chuyển route cũ.
- [ ] P17-W02 — Kiểm quan hệ hình học/ROI, sampling/cc/% và D/V definitions.
- [ ] P17-W03 — HI/CI có formula identifier/parameters, thiếu dữ liệu không tính; source contextual matching.
- [ ] P17-W04 — Kiểm workload lớn, oracle, run persistence và selection PDF.
- [ ] P17-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P17-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P17

- TC-UX1-P17-S01 — Fixture hình học chuẩn cho DVH/Dxx/Vxx khớp phép kiểm độc lập.
- TC-UX1-P17-S02 — Hiển thị cc/% và Gy/%Rx chuyển đúng khi đủ thông tin chuẩn hóa.
- TC-UX1-P17-S03 — ROI/metric chọn ở kết quả xuất đúng trong PDF.
- TC-UX1-P17-S04 — Thiếu CT không chặn phép tính mà profile đủ hình học cho phép; chế độ cần CT báo đúng yêu cầu.

### Trường hợp lỗi và phục hồi P17

- TC-UX1-P17-E01 — RTSTRUCT sai Frame of Reference/ROI rỗng/ngoài lưới → không đường DVH giả.
- TC-UX1-P17-E02 — Không có liều kê đơn mà chọn %Rx → yêu cầu chuẩn hóa, không tự đoán.
- TC-UX1-P17-E03 — HI/CI thiếu Dxx/thể tích hoặc định nghĩa khác → không đánh giá đạt theo ngưỡng khác.
- TC-UX1-P17-E04 — Voxel/contour vượt budget → dừng có kiểm soát và giữ input.
- TC-UX1-P17-E05 — Dose accumulation/registration chưa hỗ trợ → không sinh bản đồ cộng liều bằng phép cộng mảng sai geometry.

### Bất biến và điều kiện đóng P17

DVH thuộc PSQA, hình học/chỉ số/phạm vi tài nguyên kiểm chứng; không tự đánh giá phác đồ chỉ bằng HI/CI không nguồn.

## P18 — Kiểm thử trọn luồng và nghiệm thu trải nghiệm

**Đầu vào/phụ thuộc:** P17 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P18-01; B01–B14.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P18

1. Lập ma trận các giai đoạn đã hoàn thành, chạy toàn luồng đăng nhập → bài kiểm tra → PDF → lịch sử.
2. Chạy luồng thư viện A/B: tải nội bộ → đăng một tệp → sửa nháp → thu hồi → xóa/khôi phục; kiểm tìm kiếm/PDF cũ.
3. Kiểm sáu công cụ, ngôn ngữ mọi trạng thái, hai kích thước màn hình, mất mạng và tác vụ lỗi.
4. Ghi lỗi theo mức ảnh hưởng, sửa và chạy lại phần liên quan; chỉ bàn giao P19 khi không còn lỗi chặn phạm vi.

**Điểm chuyển bước:** Chỉ mở P19 sau khi gói VERIFY và HANDOFF của P18 đạt đúng điều kiện bên dưới.

### Luồng thao tác P18

1. Chạy ma trận người dùng từ đăng nhập tới QA/PDF/xóa/khôi phục và công cụ/thư viện.
2. Dùng fixture tổng hợp, phép tính biết trước, test lỗi; thêm dữ liệu thực khi người dùng cung cấp đúng mục đích.
3. Đo bố cục/thao tác, ghi lỗi tái hiện, sửa rồi kiểm hồi quy ảnh hưởng.

### Gói công việc P18

- [ ] P18-W01 — Unit/API/DB/engine/worker tests bao phủ từng TC-UX1; kiểm artifact thực, không chỉ status code.
- [ ] P18-W02 — Browser E2E ở1366×768/1440×900/zoom200%, keyboard và quét nhãn JSON/ID/ngôn ngữ.
- [ ] P18-W03 — PDF text+render visual tests và toàn bộ manual + 16 họ pylinac chính + QA contrib + Gamma 1D/2D; lấy coverage trực tiếp từ registry để không bỏ class/variant.
- [ ] P18-W04 — Fault injection mất mạng/worker crash/retry/delete/concurrency, restore trên bản thử và ghi giới hạn kết quả.
- [ ] P18-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P18-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P18

- TC-UX1-P18-S01 — B01–B14 có bằng chứng mới; người dùng không phải thao tác JSON/mã kỹ thuật.
- TC-UX1-P18-S02 — QA nhập tay, mọi capability pylinac trong registry và PSQA 1D/2D đi trọn chuỗi input→run→điều chỉnh→đánh giá→lịch sử/PDF/xóa/restore; metric và hình nhất quán.
- TC-UX1-P18-S03 — Sáu công cụ mở/tính/tra nguồn tại một trang và không liên kết QA.
- TC-UX1-P18-S04 — Kiểm hồi quy scope, phiên bản, PDF cũ và restore dữ liệu đạt.
- TC-UX1-P18-S05 — Hai phiên A/B đi trọn soạn → PDF → chia sẻ một tệp → B tìm/đọc/lưu → A sửa/thu hồi → B bị chặn yêu cầu mới; hai người cùng A sửa ngang quyền.
- TC-UX1-P18-S06 — Người chưa có đơn vị đăng nhập đọc được cộng đồng, không bị chuyển vòng về lỗi tổ chức.

### Trường hợp lỗi và phục hồi P18

- TC-UX1-P18-E01 — Một phase cũ PASS nhưng UX mới không test → chưa đạt UX1.
- TC-UX1-P18-E02 — UI gọn nhờ cắt nút/chữ quá nhỏ hoặc zoom out → không đạt, sửa layout.
- TC-UX1-P18-E03 — Một test treo/collection thiếu → ghi chưa kết thúc, không gộp vào tổng PASS.
- TC-UX1-P18-E04 — Ảnh thật khác profile fixture → ghi unsupported hoặc bổ sung profile/test, không sửa expected cho khớp tùy tiện.
- TC-UX1-P18-E05 — Lỗi mới từ thử thực tế → tạo regression test rồi sửa; không coi feedback là commissioning toàn bộ sản phẩm.
- TC-UX1-P18-E06 — Tệp/ảnh thu nhỏ/đoạn trích/số đếm còn lộ sau thu hồi do bộ nhớ đệm hoặc tác vụ cũ → chưa đạt; kiểm lại bằng phiên B và yêu cầu mới.

### Bất biến và điều kiện đóng P18

Có ma trận test cùng SHA/môi trường, lỗi còn mở và giới hạn hỗ trợ rõ; không tuyên bố hoàn hảo hoặc đủ mọi tình huống chỉ vì suite xanh.

## P19 — Phát hành website và chuyển dữ liệu từ xa

**Đầu vào/phụ thuộc:** P18 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P19-01; B01–B14 trên release được công bố.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P19

1. Đối chiếu cấu hình và bản nguồn, tạo bản sao dữ liệu cùng bước khôi phục đã thử.
2. Triển khai trên môi trường thử: chuyển dữ liệu mặc định nội bộ, kiểm giao diện/API/tác vụ cùng phiên bản.
3. Kiểm trọn luồng với tài khoản thử và tệp tổng hợp; sau khi đạt thì phát hành cùng bộ mã lên vận hành.
4. Kiểm lại địa chỉ thật, thu hồi chia sẻ, nguồn và dữ liệu cũ; ghi phương án quay lui cùng sổ cấu hình.

**Điểm chuyển bước:** Chỉ mở P20 sau khi gói VERIFY và HANDOFF của P19 đạt đúng điều kiện bên dưới.

### Luồng thao tác P19

1. Tạo manifest bản phát hành và backup có kiểm tra khả năng khôi phục; migration mở rộng tương thích.
2. Deploy staging đúng web/API/worker, backfill dữ liệu cũ, chạy smoke các luồng vừa đổi.
3. Chuyển bản đã kiểm chứng sang production trong phạm vi được phép, kiểm lại domain/auth/data/worker/PDF và giữ phương án quay lui.

### Gói công việc P19

- [ ] P19-W01 — Sổ môi trường cập nhật branch/root/config/predeploy/health/PORT, biến Vite và DB driver không chứa secret.
- [ ] P19-W02 — Migration expand/backfill/verify, routes redirect và snapshot compatibility; không drop legacy trong cùng bước.
- [ ] P19-W03 — Staging smoke end-to-end và manifest exact SHA cho web/API/worker/schema/engine/renderer.
- [ ] P19-W04 — Production rollout, kiểm từ xa, rollback tương thích schema và runbook khôi phục có evidence.
- [ ] P19-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P19-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P19

- TC-UX1-P19-S01 — Web/API/worker đúng release tương thích, ready và luồng QA/PDF/công cụ chạy từ URL thực.
- TC-UX1-P19-S02 — Dữ liệu cũ mở được và số lượng/liên kết sau chuyển khớp; thùng rác không tự phục hồi.
- TC-UX1-P19-S03 — Reload deep link không404, login redirect về đúng web, không env của staging tràn production.
- TC-UX1-P19-S04 — Rollback application đã thử trên schema tương thích, không mất dữ liệu mới.

### Trường hợp lỗi và phục hồi P19

- TC-UX1-P19-E01 — Deployment active nhưng bản cũ phục vụ → so SHA/manifest, không đánh dấu xong dựa trạng thái Online.
- TC-UX1-P19-E02 — Migration fail → giữ phiên bản trước, sửa nguyên nhân; không bỏ predeploy hoặc xóa DB.
- TC-UX1-P19-E03 — Web env thiếu/health sai/CORS sai → sửa đúng service và build, không tắt kiểm tra để đi tiếp.
- TC-UX1-P19-E04 — Thiếu quyền backup/provider hoặc tăng chi phí cần quyết định → báo đúng bước cần người dùng, tiếp tục công việc local khác; không thử mutation vô hạn.
- TC-UX1-P19-E05 — Backfill lỗi/mất liên kết → dừng chuyển consumer, khôi phục từ phương án đã thử.
- TC-UX1-P19-E06 — Rollback schema destructive → không thực hiện downgrade mù, dùng forward fix hoặc phục hồi có kế hoạch.

### Bất biến và điều kiện đóng P19

Release thật có manifest và smoke theo URL/phiên bản; phạm vi chưa hoàn thành ghi rõ. Không coi public health200 là nghiệm thu nghiệp vụ.

## P20 — Hướng dẫn, phản hồi và mở rộng danh mục

**Đầu vào/phụ thuộc:** P19 đã hoàn thành và có bàn giao; các hợp đồng liên quan xem mục kỹ thuật tương ứng.
**Phạm vi:** FR-UX1-P20-01; B01–B14 được duy trì.
**Trạng thái UX1 lúc lập kế hoạch:** yêu cầu mới; chưa được tính là hoàn thành từ evidence cũ.

### Trình tự triển khai P20

1. Viết hướng dẫn tiếng Việt bằng màn hình đã phát hành, gồm nội bộ/cộng đồng, PDF và thu hồi.
2. Bàn giao cách theo dõi tác vụ, sao lưu/khôi phục và cấu hình đang có.
3. Ghi phản hồi có bước tái hiện, tác động và giai đoạn chịu trách nhiệm; sửa theo đợt mới.
4. Đóng đợt khi hướng dẫn và bàn giao đủ; nguồn bệnh viện còn thiếu được theo dõi riêng với xuất xứ rõ.

**Điểm chuyển bước:** Đóng đợt triển khai sau khi đủ điều kiện P20.

### Luồng thao tác P20

1. Bàn giao hướng dẫn ngắn theo tác vụ thực: làm bài, đọc kết quả, xuất PDF, xóa/khôi phục, tính và tra nguồn.
2. Nhận phản hồi có màn hình/bài/profile và bước tái hiện, không yêu cầu người dùng thu JSON.
3. Ưu tiên lỗi/cải tiến/nguồn thư viện; thêm bài tự động hoặc định dạng mới bằng capability+fixture+test riêng.

### Gói công việc P20

- [ ] P20-W01 — Hướng dẫn tiếng Việt theo năm mục và sáu công cụ, ảnh giao diện đúng bản.
- [ ] P20-W02 — Runbook backup/restore/monitoring/queue/storage và sổ cấu hình, người liên hệ vận hành không thành role hạn chế chức năng.
- [ ] P20-W03 — Danh sách lỗi/ý kiến có reproduction, ảnh hưởng, phase/test liên quan; cập nhật tiến độ theo evidence.
- [ ] P20-W04 — Coverage nguồn điều trị/QA và backlog engine mở rộng theo danh mục BA, giới hạn phạm vi từng gói.
- [ ] P20-VERIFY — Chạy các TC-UX1 dưới đây và nhóm lỗi dùng chung có liên quan; lưu actual/evidence theo SHA.
- [ ] P20-HANDOFF — Cập nhật tiến độ, dữ liệu/migration/tuyến bị tác động, giới hạn hỗ trợ và bước tiếp theo.

### Trường hợp chạy đúng P20

- TC-UX1-P20-S01 — Người không lập trình làm được các tác vụ qua hướng dẫn mà không dùng ID/JSON.
- TC-UX1-P20-S02 — Một lỗi người dùng được tái hiện bằng test và sửa không phá luồng khác.
- TC-UX1-P20-S03 — Thêm nguồn hoặc engine mới không thay số/kết quả đã lưu.
- TC-UX1-P20-S04 — Thông tin backup và khôi phục được kiểm tra theo lịch do đơn vị chọn, không chỉ có file hướng dẫn.

### Trường hợp lỗi và phục hồi P20

- TC-UX1-P20-E01 — Phản hồi thiếu dữ kiện → hỏi đúng bài/máy/thời điểm, không yêu cầu gửi token/hồ sơ nhạy cảm rộng.
- TC-UX1-P20-E02 — Nguồn hết hạn/thay phiên bản → đánh dấu và bổ sung, giữ citation cũ.
- TC-UX1-P20-E03 — Bài mới vượt profile/định dạng hiện có → ghi gói mới cần phát triển, không đặt nhãn tự động ngay.
- TC-UX1-P20-E04 — Sự cố production → thực hiện runbook có thẩm quyền, ghi phạm vi ảnh hưởng và kết quả; không tự xoá dữ liệu để làm khỏe.
- TC-UX1-P20-E05 — Mục tiêu 'mọi bài/mọi bệnh viện' không có danh sách → duy trì coverage có tên, không tuyên bố hoàn tất vô hạn.

### Bất biến và điều kiện đóng P20

Gói bàn giao ban đầu và cơ chế phản hồi có người nhận, nguồn/capability có danh mục. Công việc vận hành định kỳ không có nghĩa goal phát triển phải chạy vô hạn.

## 4. Ma trận bao phủ yêu cầu người dùng

| Mã | Yêu cầu | Phase chứng minh | Bằng chứng tối thiểu |
| :--- | :--- | :--- | :--- |
| B01 | Hợp nhất điều hướng | P3/P5/P9/P10/P12/P11/P16 | Route/menu tests, ảnh năm mục |
| B02 | Gọn trong màn hình, chữ nhỏ hợp lý | P3/P4/P7/P9/P12/P18 | Ảnh hai viewport, zoom200%, keyboard |
| B03 | Một ngôn ngữ; không JSON/ID | P3–P18 | UI/error/empty scan + text PDF |
| B04 | Ngang quyền, dữ liệu riêng theo đơn vị | P2/P4/P5/P18 | Hai member cùng thao tác, cross-tenant rejection |
| B05 | Đúng bài/đúng đầu vào, manual không DICOM | P5/P6/P7 | Catalog matrix và ba input modes |
| B06 | Đủ 16 họ/biến thể chính và QA contrib public của pylinac; Gamma 1D/2D với ΔD và DTA | P7/P8/P17 | Runtime inventory, class matrix, adapter-fidelity, metrics+overlays+run history |
| B07 | Tách metric và đánh giá người dùng | P7/P8/P10 | Override test, invalid/no-result test |
| B08 | Lịch sử có xóa/khôi phục | P5/P9/P10/P18 | DB/storage/jobs/trends deletion test |
| B09 | PDF tùy chỉnh từng dòng/ảnh | P9/P18 | Preview/PDF text+render, hide all blocks test |
| B10 | Sinh học một trang, tính nhanh | P12–P15 | Sáu panels, tính trước lưu, không case selector |
| B11 | Hai nhánh kiến thức đầy đủ cấu trúc | P11/P16/P17 | Form/schema/source/context/HI/CI tests |
| B12 | α/β/giới hạn nguồn rõ, không seed ví dụ | P13/P15/P16 | Shared reference version tests, content register |
| B13 | Nội bộ/cộng đồng, chia sẻ/thu hồi theo bản và tệp | P11/P16/P18/P19 | Hai đơn vị, người chưa có đơn vị; kiểm bài/PDF/tìm kiếm sau thu hồi |
| B14 | Soạn bài, PDF, tìm kiếm, lưu bài và thùng rác | P11/P16/P18 | Tự lưu/xung đột/phiên bản/tìm không dấu/đọc tệp/khôi phục nội bộ |

## 5. Gói thiết kế Google Stitch

Dùng project RT-connect qua MCP khi bắt đầu giai đoạn thiết kế. Danh sách screen lưu trong evidence là ảnh chụp tại thời điểm cũ; phải đọc lại trước khi chọn màn hình, không gọi những hình biological đã xóa là nguồn đang hoạt động.

Thiết kế theo cùng token màu/chữ/bảng/spacing với khung mới; không tạo mỗi mô-đun thành một phong cách. Không copy nguyên màn hình quá cao làm tiêu chuẩn.

| Gói thiết kế | Màn hình/trạng thái phải có | Nơi nghiệm thu |
| :--- | :--- | :--- |
| DS-01 | AppShell năm mục, đăng nhập, trang chủ, menu tài khoản | P3 |
| DS-02 | Đơn vị/cơ sở/máy/thành viên dạng thẻ, form nhỏ | P4 |
| DS-03 | Danh mục QA, lịch sử, thùng rác, chọn bài và input modes | P5/P6 |
| DS-04 | Hệ thống form/canvas/result dùng chung; màn hình đại diện cho đủ 16 họ pylinac chính và QA contrib, thao tác chọn tâm/ROI/profile và PSQA ΔD+DTA | P7/P8 |
| DS-05 | Chọn dòng/cột/hình và preview PDF; xu hướng drill-down | P9/P10 |
| DS-06 | Công cụ sinh học sáu panel cùng trang, advanced đóng | P12–P15 |
| DS-07A | Tra cứu với hai phạm vi/hai nhóm, bộ lọc và truy cập nhanh | P11 |
| DS-07B | Đọc bài/PDF, mục lục, trích dẫn, bài đã lưu và nguồn | P11/P16 |
| DS-07C | Soạn bài, tự lưu, chọn tệp và xem trước bản chia sẻ | P11 |
| DS-07D | Bài của đơn vị, nháp, lưu trữ, thùng rác và khôi phục | P11 |
| DS-08 | DVH trong kết quả PSQA, ROI/metric selection | P17 |

Mỗi gói có trạng thái tải/trống/lỗi/thành công, hai kích thước chuẩn, lựa chọn nâng cao và thao tác quay lại. Mã màn/phiên bản/hàm băm chỉ lưu nội bộ. Stitch tạo thiết kế, không thay mã ứng dụng, bộ tính, kiểm thử hay nguồn kiến thức. Đợt UX1.3 đã gửi yêu cầu tạo màn thư viện trong project RT-connect theo yêu cầu người dùng. [Sổ thiết kế thư viện](docs/design/knowledge-library.md) ghi màn tạo được, lỗi dịch vụ, phần đã kiểm và phần còn phải đối chiếu; không lấy lời tự đánh giá của Stitch làm bằng chứng đạt giao diện.

## 6. Chuyển dữ liệu và phát hành không mất lịch sử

1. P0/P1: lập inventory bảng/run/tệp/report và bản đồ liên kết; dữ liệu cũ giữ nguyên.
2. P5/P7/P11/P16: thêm schema mới; backfill có dry run/count/checksum nội bộ; các bản ghi khó phân loại đưa danh sách đối chiếu.
3. P3–P17: adapter đọc lịch sử cũ, routes redirect và UI mới; không bỏ truy cập cũ trước khi có đường tương đương.
4. P18: test migration dữ liệu nhỏ/lớn, file references, snapshot PDF và rollback consumer.
5. P19: backup/restore evidence, staging, promote artifact, kiểm manifest/migration/URLs. Không tự drop legacy trong bước đầu.
6. P20: dọn phần cũ thành gói riêng sau đối chiếu; xóa dữ liệu vật lý phải có phạm vi rõ.

Không cập nhật “cài đặt mới nhất” vào run cũ. Không migrate rule executable thành paper hoặc biến paper thành ngưỡng tự chạy. Không làm mất liên kết dữ liệu có trong thùng rác.

## 7. Sổ cấu hình phải cập nhật khi thực sự triển khai

Tách bảng **mong muốn** và **đã quan sát**, có thời điểm/commit/service. Không đặt token/password/DATABASE_URL đầy đủ vào plan.

Các trường bắt buộc:

- Môi trường, project/service names hoặc ID nội bộ chỉ trong tài liệu vận hành.
- Web/API/worker branch và release SHA; root directory và config-as-code path thực sự hiệu lực.
- Builder/Dockerfile, build command, start command, predeploy migration, PORT, health và readiness.
- Tên biến Supabase/Vite/CORS, trạng thái có/thiếu và nguồn lấy; không lộ secret.
- PostgreSQL/Redis/storage binding riêng môi trường; URL normalizer thống nhất runtime/Alembic.
- Public domains, auth redirect, target port, schema head và engine/renderer contract.
- Backup/restore procedure thực hiện được, quyền provider đã kiểm, dung lượng/concurrency và chi phí đo được.

Cấu hình đã quyết định: PostgreSQL và backend trên Railway; Supabase Auth. Không tái tranh luận chuyển DB sang Supabase. Không bỏ healthcheck hoặc migration chỉ vì một deploy đang lỗi. Chẩn đoán đúng instance/phiên bản trước khi yêu cầu người dùng chỉnh.

## 8. Bàn giao và cách tiếp tục để không lạc hướng

Mỗi lần thực thi đọc phần đầu ba tài liệu này và điểm bàn giao mới nhất trong implementation-progress.md; chọn giai đoạn đầu tiên chưa hoàn thành theo thứ tự P0 → P20, làm tới kiểm chứng và bàn giao; không nhảy giai đoạn theo độ thuận tiện.

Checkpoint tối thiểu ghi:

- Phiên bản UX1 và package đang làm.
- Mã nguồn/môi trường thực sự đã thử.
- File/route/schema/engine thay đổi và test S/E tương ứng.
- Bằng chứng ảnh/PDF/expected/actual; những test chưa chạy hoặc chưa kết thúc.
- Phần còn thiếu và bước tiếp theo có thể làm ngay.
- Chỉ hỏi người dùng khi thật sự thiếu lựa chọn/nguồn/quyền cần thiết; không hỏi lại quyết định đã chốt.

Trạng thái UX1.3 và bằng chứng kiểm tài liệu nằm ở đầu implementation-progress.md. Đợt này cập nhật tài liệu và thiết kế Stitch, không triển khai ứng dụng. Phần P0 còn thiếu phải đóng trước, sau đó P1 → P2 → P3 và lần lượt tới P20; không nhảy thẳng P3/P4 từ bằng chứng cũ. Kết quả kiểm trước đây vẫn giữ trong lịch sử, không tự thay các ca kiểm UX1.3.

Các [runbook](deployment/railway/production-runbook.md), [gói vận hành ban đầu](docs/runbooks/p20-initial-operations-package.md) và [tiến độ](implementation-progress.md) được tiếp tục dùng khi không xung đột với ba bản mới; khi triển khai package liên quan phải cập nhật chúng với cấu hình thực tế.

## 9. Định nghĩa hoàn thành toàn đợt UX1

- Năm mục chính đúng thiết kế, sử dụng tiếng Việt nhất quán và bố cục gọn được người dùng đánh giá lại.
- QA nhập tay, đủ 16 họ/biến thể chính và QA contrib public của pylinac trong runtime registry, cùng PSQA Gamma 1D/2D chạy thật; lịch sử/xóa/restore/PDF/trend đi liền nhau.
- Công cụ sinh học một trang gồm đủ sáu công cụ; nguồn α/β và giới hạn được truy ngược.
- Thư viện hai nhánh hoạt động, cấu trúc phác đồ đủ trường, tuyển tập đã nhập có coverage/source rõ.
- Dữ liệu cũ được bảo toàn hoặc xử lý xóa đúng ý người dùng; không mất qua migration.
- P18/P19 chứng minh đúng bản phần mềm, có giới hạn hỗ trợ và các tồn đọng được công bố.
- Bàn giao P20 có hướng dẫn/cấu hình/khôi phục/tiếp nhận lỗi; không lấy văn bản kế hoạch “hoàn hảo” làm bằng chứng sản phẩm đã hoàn hảo.
