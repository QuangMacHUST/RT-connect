# RT-CONNECT — Danh mục QA sử dụng pylinac

**Phiên bản danh mục:** 1.1  
**Ngày đối chiếu:** 2026-09-13  
**Phạm vi:** toàn bộ 16 họ mô-đun QA chính, các phép QA trong `contrib/One-Offs` và Gamma 1D/2D được tài liệu pylinac công bố; dùng làm hợp đồng cho `business-analysis.md` v1.3, `technical-specification.md` v2.3 và `plan.md` v5.3. Nội dung danh mục 1.1 không thay đổi trong đợt mở rộng thư viện UX1.3.

## 1. Quyết định nền tảng

Pylinac là engine tính toán chính thức cho mọi bài và phép tính mà phiên bản pylinac đã khóa cung cấp, gồm cả QA `contrib/One-Offs`. RT-CONNECT không viết lại công thức hoặc thuật toán tương đương để thay pylinac trong những capability đó.

RT-CONNECT chịu trách nhiệm:

- danh mục bài, lựa chọn theo loại thiết bị và biểu mẫu tiếng Việt;
- nhận tệp/số liệu, kiểm tra định dạng, đơn vị, hình học và giới hạn tài nguyên trước khi gọi engine;
- giao diện ảnh để người dùng chọn tâm, vị trí profile, vùng quan tâm, lát cắt, góc, kích thước hoặc tham số khác mà API pylinac cho phép;
- chuyển tham số có đơn vị của người dùng sang đúng contract của pylinac và lưu lại phép chuyển đổi;
- chuẩn hóa `results_data()` hoặc kết quả có cấu trúc sang bảng chỉ số, lớp hình học và biểu đồ của RT-CONNECT;
- lưu lịch sử, đánh giá Đạt/Cảnh báo/Không đạt của người thực hiện, xu hướng và PDF tùy chỉnh.

Không đưa tên class, JSON, traceback hoặc mã nội bộ lên giao diện. Tự động nhận dạng là mặc định; thao tác tay nằm trong mục “Điều chỉnh”. Mỗi lần thay đổi điều chỉnh và bấm phân tích tạo một run mới; tệp gốc và kết quả cũ không bị sửa.

## 2. Mốc phiên bản và cách bảo đảm “đầy đủ”

Tài liệu `latest` đang hiển thị pylinac 3.48.0, trong khi bản phát hành PyPI mới nhất được đối chiếu ngày 2026-09-12 là 3.47.0 và yêu cầu Python từ 3.10. Runtime chỉ được dùng gói phát hành đã khóa chính xác phiên bản và hash; không cài từ nhánh tài liệu `latest`.

Danh mục triển khai không được duy trì bằng trí nhớ. Khi thêm hoặc nâng phiên bản pylinac, pipeline phải:

1. cài đúng wheel/hash trong image dựng lại được;
2. lấy inventory class/module công khai từ phiên bản đã cài và so với registry đã kiểm soát trong source;
3. fail build nếu pylinac thêm/bỏ/đổi capability nhưng chưa có quyết định ánh xạ giao diện;
4. chạy contract test cho input, tham số, `results_data()`, hình minh họa và lỗi của từng capability;
5. lưu `pylinac_version`, wheel hash, module/class, adapter version và tham số phân tích trong snapshot của run.

Như vậy “đầy đủ” nghĩa là không bỏ sót capability công khai của **phiên bản runtime đã khóa**, không phải tự động bật code chưa được ánh xạ khi tài liệu `latest` thay đổi.

## 3. Toàn bộ 16 họ mô-đun chính và QA đóng góp

| Mã gói | Họ mô-đun pylinac | Bài/biến thể phải có trong RT-CONNECT | Đầu vào chính | Kết quả và giao diện trọng tâm |
| :--- | :--- | :--- | :--- | :--- |
| P07-CAL | Calibration | TG-51 photon; TG-51 electron legacy; TG-51 electron modern; TRS-398 photon; TRS-398 electron | Biểu mẫu số đo, buồng ion hóa, nhiệt độ/áp suất, điện áp, hệ số, PDD/TPR và MU theo class | Form theo protocol; hệ số trung gian; dose/MU; đơn vị; không dùng JSON. Ghi đúng phiên bản protocol pylinac thực thi. |
| P07-STAR | Starshot | Starshot gantry, collimator, MLC hoặc bàn điều trị theo cùng engine | Một ảnh hoặc bộ ảnh DICOM EPID; film quét có DPI/scale | Ảnh gốc, tia, tâm, vòng tròn wobble, bán kính/đường kính. Cho bấm hoặc kéo tâm khởi tạo, chỉnh radius, tolerance, FWHM, đảo ảnh và ngưỡng tìm đỉnh. |
| P07-VMAT | VMAT | DRGS; DRMLC; DRCS | Cặp ảnh trường mở và ảnh điều biến | Độ lệch từng segment/ROI, độ lệch lớn nhất, ảnh vùng đo. Form chọn loại bài, tolerance, ROI/segment và offset theo API. |
| P07-CT | CatPhan | CatPhan 503; 504; 600; 604 của bản phát hành đã khóa | Chuỗi DICOM CT/CBCT hoặc ZIP | HU tuyến tính, hình học, độ dày lát, đồng nhất/NPS, MTF, tương phản thấp theo module có mặt. Cho chọn lát gốc và chỉnh x/y/góc/kích thước ROI/scaling/giá trị HU kỳ vọng. |
| P07-ACR | ACR Phantoms | ACR CT 464; ACR MRI Large; ACR MRI Medium | Chuỗi DICOM CT hoặc MRI phù hợp phantom | Hình học, độ đồng nhất, độ phân giải, độ dày lát, low contrast và các module theo model. Có chọn lát gốc, chỉnh tâm/vùng và xem từng lát/module. |
| P07-CHEESE | Cheese Phantoms | TomoCheese; CIRS 062M | Chuỗi DICOM phantom | Các ROI mật độ/HU và đường đáp ứng. Có chọn lát gốc, chỉnh ROI, giá trị tham chiếu và xem đường density. |
| P07-HELIOS | GE Helios CT Daily QA | GE Helios CT Daily | Chuỗi DICOM phantom | Contrast scale, độ phân giải tương phản cao, noise, uniformity và low contrast. Có chọn lát gốc, chỉnh vị trí/ROI và xem từng module. |
| P07-QUART | Quart | Quart DVT; alias/biến thể HyperSight chỉ hiển thị khi còn trong phiên bản đã khóa | Chuỗi DICOM CT/CBCT | HU, hình học, đồng nhất, CNR/SNR và chi tiết model. Có chọn lát gốc, chỉnh vị trí/ROI và xem từng module. |
| P07-LOG | Log Analyzer | Varian Dynalog; Trajectory Log 2.1, 3.0, 4.0; tệp `.bin` và `.txt` khi class hỗ trợ | Cặp Dynalog hoặc Trajectory Log | Trục actual/expected/difference, MLC, beam hold, fluence và Gamma log. Vì pylinac không tự đặt kết luận cuối cho log, RT-CONNECT cho chọn metric/tiêu chí và đánh giá người dùng. |
| P07-PF | Picket Fence | Picket Fence theo MLC/profile được pylinac hỗ trợ | Ảnh EPID DICOM hoặc định dạng ảnh có scale hợp lệ | Sai lệch lá/picket, mean/max, lá vượt tolerance/action tolerance, histogram và overlay. Cho chỉnh MLC model, orientation, crop, sag/offset, tolerance và vùng/phép nhận vạch theo API. |
| P07-WL | Winston–Lutz | Winston–Lutz một bi/một trường theo bộ ảnh | Bộ ảnh DICOM/ảnh có scale và góc | BB–CAX từng ảnh, vector/khoảng cách, isocenter/axis plots khi bộ góc đủ, gợi ý dịch bàn nếu dùng. Cho sửa metadata góc/tọa độ và tham số nhận trường/bi mà API hỗ trợ. |
| P07-WLMT | Winston–Lutz Multi-Target | WinstonLutzMultiTargetMultiField và cấu hình multi-target/multi-field công khai | Bộ ảnh nhiều bi/nhiều trường và cấu hình hình học | Ghép cặp field–BB, sai lệch từng target/field, tổng hợp và overlay. UI nhập/điều chỉnh cấu hình BB/field, hệ tọa độ, góc và mapping; không bắt người dùng sửa tệp cấu hình thô. |
| P07-PLANAR | Planar Imaging | Toàn bộ phantom ở mục 4 | Một ảnh DICOM/XIM/TIFF/JPG khi class và profile hỗ trợ | High/low contrast, MTF/rMTF, uniformity, ROI và kết quả riêng phantom. Canvas cho override tâm, góc, kích thước, SSD, x/y/góc, ROI-size/scaling và đảo ảnh theo class. |
| P07-FPA | Field Profile Analysis | FieldProfileAnalysis và toàn bộ metric profile công khai | Ảnh trường hoặc dữ liệu profile được bộ đọc hỗ trợ | Field width, penumbra, flatness, symmetry, FFF top và metric đã chọn. UI chọn manual/beam/geometric center, click vị trí profile, x/y width, normalization, edge type và metric. |
| P07-FA | Field Analysis | FieldAnalysis legacy còn có trong phiên bản đã khóa | Ảnh EPID hoặc dữ liệu SNC Profiler được hỗ trợ | Profile dọc/ngang, field width, penumbra, flatness/symmetry theo protocol. Hiển thị nhãn “Mô-đun cũ”; tạo bài mới mặc định dùng Field Profile Analysis, nhưng vẫn có UI đầy đủ để mở dữ liệu/cấu hình cũ. |
| P07-NUCLEAR | Nuclear | Toàn bộ 9 phép thử ở mục 5 | DICOM gamma camera/SPECT và số liệu hoạt độ/thời gian khi bài yêu cầu | Bảng/ảnh/profile/ROI theo phép thử. Form riêng từng bài, chọn frame/ROI/threshold và tham số đo; không trộn thành một upload form chung. |
| P07-CONTRIB | One-Offs/Contrib QA | Quasar Light/Rad Scaling; Jaw Orthogonality | Ảnh phantom hoặc trường mở theo class | Form invert/FWXM/BB-edge threshold cho Quasar; ảnh cạnh jaw và bốn giá trị góc cho Jaw Orthogonality. Ghi rõ “mô-đun đóng góp” vì upstream không bảo đảm ổn định như core. |

Các module phụ `Core`, `Image Generator` và `Plan Generator` không phải bài QA độc lập trong sidebar; chúng được dùng nội bộ để đọc ảnh, chuyển tọa độ hoặc tạo fixture. `One-Offs` có hai phép QA nêu trên nên vẫn được đưa vào danh mục. `Gamma` và profile/image metrics là capability mức thấp, được RT-CONNECT bọc thành PSQA, log QA hoặc phân tích trường theo mục 6.

## 4. Toàn bộ biến thể Planar Imaging

Registry Planar Imaging phải chứa mọi class công khai sau nếu class đó tồn tại trong wheel đã khóa:

| Nhóm | Biến thể |
| :--- | :--- |
| Chất lượng ảnh kV/MV | Leeds TOR 18; Leeds TOR Blue; Standard Imaging QC-3; Standard Imaging QC-kV; Las Vegas; Elekta Las Vegas; Doselab MC2 MV; Doselab MC2 kV; SNC MV; SNC MV 12510; SNC kV; PTW EPID QC; IBA Primus A |
| Trường sáng–trường xạ | Standard Imaging FC-2; IMT L-RAD; Doselab RLf; PTW Iso-Align; SNC FSQA |
| Nhũ ảnh | ACR Digital Mammography |

Danh mục thường dùng lọc theo loại thiết bị đang chọn. Ví dụ, bài nhũ ảnh không xuất hiện trong nhóm máy xạ trị nhưng vẫn tìm được khi chọn “Tất cả bài pylinac” hoặc thiết bị phù hợp; không xóa capability khỏi registry.

## 5. Toàn bộ phép thử Nuclear

| Mã con | Phép thử | Trường giao diện tối thiểu |
| :--- | :--- | :--- |
| P07-NUCLEAR-MCR | Maximum Count Rate | Tệp, thời lượng frame/profile, đơn vị tốc độ đếm; biểu đồ tổng đếm theo frame |
| P07-NUCLEAR-PU | Planar Uniformity | UFOV, CFOV, window size, threshold; integral/differential uniformity và overlay vùng |
| P07-NUCLEAR-COR | Center of Rotation | Bộ ảnh quay, scale; độ lệch x/y theo mm và đồ thị |
| P07-NUCLEAR-TR | Tomographic Resolution | Dữ liệu SPECT; FWHM/FWTM x/y/z và profile |
| P07-NUCLEAR-SS | Simple Sensitivity | Ảnh phantom, ảnh nền tùy chọn, hoạt độ, nuclide, thời gian; cps và sensitivity |
| P07-NUCLEAR-FBR | Four-Bar Resolution | Separation, ROI width, scale; FWHM/FWTM và pixel-size difference |
| P07-NUCLEAR-QR | Quadrant Resolution | ROI/scale; MTF, FWHM và lp/mm theo quadrant |
| P07-NUCLEAR-TU | Tomographic Uniformity | Frame range, UFOV/CFOV, threshold; uniformity và center/border ratio |
| P07-NUCLEAR-TC | Tomographic Contrast | Cấu hình sphere/ROI và baseline; contrast theo sphere và ảnh chú thích |

## 6. PSQA Gamma dùng pylinac

### 6.1. Giao diện bắt buộc

Ở chế độ cơ bản, người dùng luôn thấy:

- “Liều tham chiếu” và “Dữ liệu đo/đối chiếu”;
- “Chênh lệch liều (%)”;
- “Khoảng cách DTA (mm)”;
- “Chuẩn hóa: toàn cục/cục bộ”;
- “Ngưỡng liều thấp (%)”;
- “Ngưỡng chấp nhận tỷ lệ đạt (%)” của đơn vị;
- nút “Kiểm tra dữ liệu” và “Phân tích”.

Vùng “Điều chỉnh” chứa absolute/relative khi profile thực sự hỗ trợ, ROI, nội suy/resampling, gamma cap, hướng/plane và thông tin hiệu chuẩn. Không để hai tham số dose difference và DTA ẩn trong JSON hoặc cài đặt kỹ thuật.

### 6.2. Ranh giới engine hiện hành

Pylinac công bố `profile.gamma_1d` và `image.gamma_2d`; danh mục công khai hiện không có Gamma 3D. Vì quyết định sản phẩm là pylinac chịu trách nhiệm engine, run PSQA mới chỉ được công bố cho 1D/2D đã ánh xạ. Không dùng engine 3D tự viết của RT-CONNECT để gắn nhãn “pylinac”.

Đối với Gamma 2D, pylinac nhận khoảng cách theo số phần tử/pixel. RT-CONNECT phải kiểm spacing, đưa hai grid về cùng không gian đã công bố và chuyển DTA từ mm sang số phần tử theo một profile xác định. Nếu không biểu diễn đúng tiêu chí mm bằng grid/step đã chọn thì dừng trước khi chạy, không làm tròn âm thầm. Snapshot lưu DTA người dùng nhập, spacing trước/sau, phép resampling và giá trị truyền cho pylinac.

Kết quả Gamma 3D đã lưu từ engine RT-CONNECT cũ vẫn được mở ở chế độ chỉ đọc với nhãn nguồn engine thật. Mở lại không tính lại; tạo run 3D mới bị vô hiệu hóa cho đến khi pylinac phát hành capability tương ứng hoặc người dùng thay đổi quyết định engine bằng một revision tài liệu mới.

## 7. Hợp đồng thao tác tay trên ảnh

Canvas ảnh dùng cùng một hệ tọa độ chuẩn hóa cho mọi bài:

1. Hiển thị ảnh gốc, scale, orientation và lớp phân tích tự động.
2. Nút “Điều chỉnh” mở các control đúng capability; không hiển thị tham số không được pylinac class đó nhận.
3. Điểm/tâm/ROI/profile có thể click, kéo hoặc nhập số; ô số và overlay đồng bộ hai chiều.
4. Trước khi chạy lại, hiển thị tóm tắt thay đổi và đơn vị; không âm thầm dùng tọa độ màn hình sau zoom/pan.
5. Gửi tọa độ trong hệ ảnh gốc hoặc hệ mà adapter đã công bố; lưu cả transform hiển thị và tham số engine.
6. Kết quả mới là run mới, có thể so sánh với run tự động trước đó.

Nhóm điều khiển tối thiểu:

| Nhóm bài | Điều khiển người dùng |
| :--- | :--- |
| Starshot | Chọn/kéo tâm khởi tạo; radius; ngưỡng peak; tolerance; FWHM; recursive/invert khi hỗ trợ |
| Field Profile/Field Analysis | Chọn centering; click vị trí profile; độ rộng dải lấy mẫu x/y; edge/normalization/metric/protocol |
| Planar Imaging | Chọn/kéo tâm phantom; góc; kích thước; SSD; x/y/angle adjustment; ROI-size/scaling; invert |
| CatPhan/ACR/Cheese/Helios/Quart | Chọn lát gốc; x/y/góc; ROI/scale; chọn module/lát để xem; giá trị tham chiếu được class cho phép |
| Picket Fence | Orientation; crop; MLC model; tolerance/action tolerance; sag/offset; các profile/leaf/picket cần xem |
| Winston–Lutz | Ánh xạ góc; hệ tọa độ; tham số nhận BB/field; cấu hình BB/field của multi-target |
| VMAT | Loại DRGS/DRMLC/DRCS; tolerance; segment/ROI configuration và offset |
| Nuclear | Frame/range, UFOV/CFOV, ROI, threshold, scale, activity/nuclide/time tùy bài |
| Contrib/One-Offs | Quasar: invert, FWXM, BB edge threshold; Jaw Orthogonality: ảnh trường và overlay bốn cạnh/góc |

## 8. Kết quả, đánh giá và PDF

- Giá trị do pylinac tính là kết quả engine, không bị sửa theo đánh giá người dùng.
- `results_data()` có cấu trúc là nguồn ánh xạ chính; chuỗi `results()` hoặc PDF pylinac không phải dữ liệu máy chuẩn của RT-CONNECT.
- Kết luận gợi ý theo tolerance/configuration và đánh giá Đạt/Cảnh báo/Không đạt của người dùng là hai trường riêng.
- Mỗi metric có key ổn định của RT-CONNECT, nhãn tiếng Việt, định nghĩa, đơn vị, module/class pylinac và version.
- Overlay/biểu đồ có thể ẩn/hiện trong UI và chọn đưa vào PDF; PDF RT-CONNECT không bị giới hạn bởi layout `publish_pdf()` của pylinac.
- Nếu pylinac không trả một kết luận cuối, như Log Analyzer, RT-CONNECT không tự bịa PASS; chỉ tính rule mà người dùng đã cấu hình và lưu đánh giá riêng.

## 9. Nguồn đối chiếu

- [Tổng quan và 16 mô-đun chính](https://pylinac.readthedocs.io/en/latest/)
- [Calibration TG-51/TRS-398](https://pylinac.readthedocs.io/en/latest/calibration_docs.html)
- [Starshot](https://pylinac.readthedocs.io/en/latest/starshot_docs.html)
- [VMAT](https://pylinac.readthedocs.io/en/latest/vmat_docs.html)
- [CatPhan](https://pylinac.readthedocs.io/en/latest/cbct.html)
- [ACR](https://pylinac.readthedocs.io/en/latest/acr.html)
- [Cheese](https://pylinac.readthedocs.io/en/latest/cheese.html)
- [GE Helios](https://pylinac.readthedocs.io/en/latest/helios.html)
- [Quart](https://pylinac.readthedocs.io/en/latest/quart.html)
- [Log Analyzer](https://pylinac.readthedocs.io/en/latest/log_analyzer.html)
- [Picket Fence](https://pylinac.readthedocs.io/en/latest/picketfence.html)
- [Winston–Lutz](https://pylinac.readthedocs.io/en/latest/winston_lutz.html)
- [Winston–Lutz Multi-Target](https://pylinac.readthedocs.io/en/latest/winston_lutz_multi.html)
- [Planar Imaging](https://pylinac.readthedocs.io/en/latest/planar_imaging.html)
- [Field Profile Analysis](https://pylinac.readthedocs.io/en/latest/field_profile_analysis.html)
- [Field Analysis](https://pylinac.readthedocs.io/en/latest/field_analysis.html)
- [Nuclear](https://pylinac.readthedocs.io/en/latest/nuclear.html)
- [One-Offs/Contrib](https://pylinac.readthedocs.io/en/latest/contrib.html)
- [Gói phát hành pylinac trên PyPI](https://pypi.org/project/pylinac/)

Lưu ý đặc thù phải hiển thị đúng theo phiên bản engine: tài liệu Calibration của pylinac hiện cảnh báo chưa tích hợp các thay đổi liên quan của bản sửa đổi TRS-398 năm 2024; RT-CONNECT không được gắn nhãn kết quả là “TRS-398 2024” khi engine chưa thực hiện revision đó. Field Analysis được tài liệu pylinac đánh dấu sẽ bị thay thế bởi Field Profile Analysis; RT-CONNECT vẫn giữ trong danh mục đầy đủ để đọc/chạy dữ liệu tương thích, nhưng hướng người dùng tạo bài mới bằng mô-đun mới.

Tài liệu upstream mô tả `contrib/One-Offs` là các phân tích được cung cấp nguyên trạng, có thể chưa được kiểm thử hoặc ổn định như các mô-đun chính. RT-CONNECT vẫn triển khai `QuasarLightRadScaling` và `JawOrthogonality` bằng chính pylinac theo quyết định engine đã chốt, nhưng phải khóa phiên bản/hash, gắn nhãn nguồn “Mô-đun đóng góp”, có fixture và contract test riêng, đồng thời không âm thầm chuyển sang thuật toán tự viết nếu API thay đổi.
