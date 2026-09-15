# Bằng chứng P7 — ma trận tệp mẫu Pylinac 3.47.0

- Ngày kiểm tra: 2026-09-15
- Môi trường: máy phát triển, wheel Pylinac 3.47.0 đã khóa
- Phạm vi: gọi trực tiếp `execute_pylinac`, lấy structured result và ảnh overlay; không ghi dữ liệu staging
- Kết luận: các dòng dưới đây đạt lát cắt `LOCAL_VERIFIED_SLICE`, không phải nghiệm thu lâm sàng

Ma trận này hiện đã được mã hóa thành kiểm thử hồi quy tại
`apps/api/tests/test_pylinac_official_demo_matrix.py`. Lệnh kiểm tra thu thập
36 trường hợp và lần chạy ngày 2026-09-15 đạt **36/36**. Bài VMAT được giải nén
từ tệp mẫu ZIP thành đúng cặp ảnh; Dynalog được dựng từ đúng cặp A/B; bài IBA
truyền SSD 1395 mm theo metadata của tệp mẫu. Kiểm thử không coi các bài chưa
có tệp mẫu chính thức là đạt và không thay thế đối chiếu độc lập hoặc dữ liệu
commissioning.

## Kết quả chạy thật

| Bài | Tệp mẫu | Engine | Số nhóm chỉ số | Kích thước overlay |
|---|---|---:|---:|---:|
| Picket Fence | `AS1200.dcm` | `PicketFence` | 20 | 162086 byte |
| Starshot | `starshot.tif` | `Starshot` | 9 | 54560 byte |
| Winston–Lutz | `winston_lutz.zip` | `WinstonLutz` | 26 | 224167 byte |
| VMAT DRGS | `drgs.zip` | `DRGS` | 10 | 87326 byte |
| VMAT DRMLC | `drmlc.zip` | `DRMLC` | 10 | 71352 byte |
| VMAT DRCS | `drcs.zip` | `DRCS` | 12 | 79710 byte |
| CatPhan 503 | `CatPhan503.zip` | `CatPhan503` | 11 | 87296 byte |
| CatPhan 504 | `CatPhan504.zip` | `CatPhan504` | 11 | 94234 byte |
| CatPhan 600 | `CatPhan600.zip` | `CatPhan600` | 11 | 78777 byte |
| CatPhan 604 | `CatPhan604.zip` | `CatPhan604` | 11 | 87592 byte |
| TomoCheese | `TomoCheese.zip` | `TomoCheese` | 27 | 204408 byte |
| Quart DVT | `quart.zip` | `QuartDVT` | 10 | 73206 byte |
| Nhãn Quart HyperSight | `quart.zip` | `QuartDVT` | 10 | 73206 byte |
| Leeds TOR | `leeds.dcm` | `LeedsTOR` | 12 | 73719 byte |
| Leeds TOR Blue | `leeds.dcm` | `LeedsTORBlue` | 12 | 80677 byte |
| Standard Imaging QC-3 | `qc3.dcm` | `StandardImagingQC3` | 12 | 72539 byte |
| Standard Imaging QC-kV | `SI-QC-kV.dcm` | `StandardImagingQCkV` | 12 | 81471 byte |
| Las Vegas | `lasvegas.dcm` | `LasVegas` | 12 | 90038 byte |
| Elekta Las Vegas | `elekta_las_vegas.dcm` | `ElektaLasVegas` | 12 | 91113 byte |
| Doselab MC2 MV | `Doselab_MV.dcm` | `DoselabMC2MV` | 12 | 67273 byte |
| Doselab MC2 kV | `Doselab_kV.dcm` | `DoselabMC2kV` | 12 | 61789 byte |
| SNC MV | `SNC-MV.dcm` | `SNCMV` | 12 | 67448 byte |
| SNC MV 12510 | `SNC_MV_12510.dcm` | `SNCMV12510` | 12 | 70421 byte |
| SNC kV | `SNC-kV.dcm` | `SNCkV` | 12 | 68084 byte |
| PTW EPID QC | `PTW-EPID-QC.dcm` | `PTWEPIDQC` | 12 | 71460 byte |
| IBA Primus A | `iba_primus.dcm` | `IBAPrimusA` | 12 | 69332 byte |
| Standard Imaging FC-2 | `fc2.dcm` | `StandardImagingFC2` | 9 | 69586 byte |
| IMT L-RAD | `imtlrad.dcm` | `IMTLRad` | 9 | 62609 byte |
| Doselab RLf | `Doselab_RLf.dcm` | `DoselabRLf` | 9 | 74041 byte |
| PTW Iso-Align | `ptw_isoalign.dcm` | `IsoAlign` | 9 | 70908 byte |
| SNC FSQA | `FSQA_15x15.dcm` | `SNCFSQA` | 9 | 93852 byte |
| ACR Digital Mammography | `ACRDigitalMammography.dcm` | `ACRDigitalMammography` | 12 | 130576 byte |
| Field Profile Analysis | `AS1200.dcm` | `FieldProfileAnalysis` | 9 | 54772 byte |
| Field Analysis legacy | `AS1200.dcm` | `FieldAnalysis` | 42 | 57977 byte |
| Dynalog | `AQA.dlg` + `BQA.dlg` | `Dynalog` | 10 | 9221 byte |
| Trajectory Log 2.1 | `Tlog.bin` | `TrajectoryLog` | 13 | 8500 byte |

## Kiểm tra thật chín bài hạt nhân bằng dữ liệu tổng hợp

Để kiểm tra đường chạy trong thời gian chưa có đủ tệp mẫu hạt nhân chính thức
ở môi trường cục bộ, kiểm thử hồi quy đã dựng các tệp DICOM hạt nhân tổng hợp
không chứa dữ liệu bệnh nhân. Chín tệp/luồng được đưa qua đúng
`execute_pylinac` và đúng wheel `3.47.0`, không thay thế bằng bộ tính tự viết:

| Bài | Kết quả | Ảnh minh họa | Ghi chú |
|---|---|---:|---|
| Tốc độ đếm cực đại | Đạt | Không có | 7 nhóm chỉ số |
| Độ đồng nhất phẳng | Đạt | Có | 16 nhóm chỉ số |
| Tâm quay | Đạt | Có | 5 nhóm chỉ số |
| Độ phân giải cắt lớp | Đạt, có cảnh báo từ thư viện | Không có | 9 nhóm chỉ số |
| Độ nhạy đơn giản | Đạt | Không có | 10 nhóm chỉ số; đồng vị Tc-99m |
| Độ phân giải bốn vạch | Đạt | Có | 11 nhóm chỉ số |
| Độ phân giải bốn góc | Đạt | Có | 4 nhóm chỉ số |
| Độ đồng nhất cắt lớp | Đạt, có cảnh báo từ thư viện | Không có | 10 nhóm chỉ số |
| Độ tương phản cắt lớp | Đạt | Có | 5 nhóm chỉ số |

Lệnh kiểm tra: `python -m pytest apps/api/tests/test_pylinac_nuclear_engine.py --no-cov -q` → **1 passed**. Đây là bằng chứng bộ điều hợp đã gọi được đủ chín lớp Pylinac và giữ được hợp đồng kết quả; dữ liệu tổng hợp không thay thế cho kiểm định bằng dữ liệu chạy máy đại diện, đối chiếu độc lập từng chỉ số hoặc nghiệm thu staging.

## Kiểm tra thật hai bài đóng góp bằng dữ liệu tổng hợp

Hai bài đóng góp đã được đưa qua đúng `execute_pylinac` của RT-CONNECT bằng
dữ liệu không có thông tin bệnh nhân. Fixture Quasar được tạo từ bản sao tạm
của ảnh FC-2 chính thức rồi bổ sung bốn điểm chuẩn trung tâm để đáp ứng yêu
cầu năm điểm của lớp `QuasarLightRadScaling`; fixture Jaw là ảnh DICOM
`RTIMAGE` hình chữ nhật tổng hợp.

| Bài | Lớp engine | Nguồn kết quả | Số nhóm chỉ số | Ảnh minh họa |
|---|---|---|---:|---|
| Quasar Light và Rad Scaling | `QuasarLightRadScaling` | `results_data()` | 9 | Có |
| Độ vuông góc của jaw | `JawOrthogonality` | `results()` | 4 | Có |

Lệnh kiểm tra: `python -m pytest apps/api/tests/test_pylinac_contrib_engine.py --no-cov -q` → **2 passed**. Kiểm thử này xác nhận đường gọi engine, ánh xạ kết quả và dựng ảnh minh họa; không phải dữ liệu chuẩn của phantom Quasar/Jaw và không thay thế đối chiếu độc lập, dữ liệu commissioning hoặc nghiệm thu staging.

## Kiểm tra thật năm bài hiệu chuẩn bằng số đo tổng hợp

Năm lớp hiệu chuẩn không nhận tệp ảnh; RT-CONNECT đưa bộ số đo tổng hợp qua
đúng constructor của Pylinac và ánh xạ các thuộc tính kết quả công khai. Các
giá trị chỉ dùng để kiểm tra đường chạy phần mềm, không phải số liệu hiệu
chuẩn của máy.

| Bài | Lớp engine | Số nhóm chỉ số | Ảnh minh họa |
|---|---|---:|---|
| TG-51 photon | `TG51Photon` | 9 | Không áp dụng |
| TG-51 electron phiên bản cũ | `TG51ElectronLegacy` | 11 | Không áp dụng |
| TG-51 electron hiện hành | `TG51ElectronModern` | 10 | Không áp dụng |
| TRS-398 photon | `TRS398Photon` | 8 | Không áp dụng |
| TRS-398 electron | `TRS398Electron` | 10 | Không áp dụng |

Lệnh kiểm tra: `python -m pytest apps/api/tests/test_pylinac_calibration_engine.py --no-cov -q` → **6 passed** (5 đường chạy đúng và 1 trường hợp thiếu PDD10 bị chặn ở biên nhập liệu). Cổng này xác nhận engine và ánh xạ thuộc tính; vẫn cần số đo được phê duyệt, đối chiếu độc lập với bộ tính/biên bản hiệu chuẩn, kiểm lỗi miền vật lý và kiểm chứng staging.

## Mã kiểm tra

- Luồng dùng thư mục tạm để giải nén các gói ZIP; dữ liệu tạm được dọn sau khi chạy.
- Mỗi bài phải qua cùng một lớp chuyển đổi đang được API sử dụng, không gọi riêng một đường tắt chỉ dành cho kiểm thử.
- Các bài hiệu chuẩn không có overlay; RT-CONNECT chỉ lưu snapshot các thuộc tính công khai do Pylinac trả về và không tự suy diễn kết luận an toàn liều.
- Kết quả phải có lớp engine đúng với registry, structured result không rỗng và overlay khi lớp Pylinac cung cấp ảnh phân tích.
- Starshot sử dụng `sid = 1000 mm`, vì tệp TIFF không chứa thẻ khoảng cách nguồn–ảnh.
- Dynalog không có overlay ảnh; bộ chuyển đổi lưu các chỉ số MLC và biểu đồ lỗi khi Pylinac tạo được tệp biểu đồ.
- Nhãn Quart HyperSight dùng cùng bộ tính `QuartDVT` vì lớp HyperSight cũ trong Pylinac không còn nhận đúng đường dẫn đầu vào. Đây là một nhãn tương thích, không phải một engine thứ hai; lần chạy thử thực tế có 3 cảnh báo tương thích của thư viện nhưng vẫn trả kết quả và overlay hợp lệ.
- Các mã băm tệp mẫu dùng để truy nguyên tại máy kiểm tra:
  - `AS1200.dcm`: `37A82228FC7593776DC70A818E12C82F8BC8198EFA98FD4E3E77C5E051AB3CD2`
  - `starshot.tif`: `6DD29760B6E88EDAB1C5C70E38BC2A3D0338B004106B32903B2E869FF25EED70`
  - `winston_lutz.zip`: `708FB3031016F9AB44609B229BFC25AB51430CB40B349E611959444E70CA73B0`
  - `drgs.zip`: `27C5EC196770B039EE4FA22A371823ED73489773714331511BD094192673DD01`
  - `drmlc.zip`: `E0562F19732A0DA114129861E9BAE84DE37AB7C76B3F10F5225E138BF09373B7`
  - `drcs.zip`: `14D41A4C8699C01F9331F78E224FA74C24BCCFC169AF55E2D09F4ECF45311DED`
  - `CatPhan503.zip`: `83FCCAE60B9870E60FB63D4F6417DDFD4FBF299A87AB92F2DC01CBCCE5A23A86`
  - `CatPhan504.zip`: `1FF32F478F684B236E9091C21A215248D5A463602850D7121D85E9A48F89533F`
  - `CatPhan600.zip`: `B47F2518C03A1C660DFEDAD02D6764B78824B47EEBCB9B9284231BF205F3CF5C`
  - `CatPhan604.zip`: `9E9B1D8D8E913D37F26A7F8A1A5113FFC2A3F91B7E9DE35E413B108B539C4613`
  - `TomoCheese.zip`: `6194850866C86C8A5257A79ACE4F140C66AA782773E12DF84A56FEB736327AD7`
  - `quart.zip`: `037181977F6B98E86DEAE3D4D08B79B242A7989F0438F050DD289FD38FD3CDC5`
  - `leeds.dcm`: `663A46369619A3A25FC5C99A8B29189F2FA19BF86183318233846AFFD7C3B306`
  - `fc2.dcm`: `5F9D991930849D7D50C04E4E82F1374766B6767A01B9C0AA5DD55945A417D89D`
  - `qc3.dcm`: `32EB20446EC6589EE7C7541C0E4809413358A9D6B2DE857B144286A8D57D9BE3`
  - `SI-QC-kV.dcm`: `60CB788BC64DF5A996E06A34339ADDB512BE86D42D9DFB8F48546786B5BE430E`
  - `lasvegas.dcm`: `C7889A36348ED58891F01C31B59A34BACDA380E3B854C94E1691A311BD462A78`
  - `elekta_las_vegas.dcm`: `753F6ABED670D60BE21C859EFDE00BE42CFD6710B4BC0C5AD0668C07181A2BC5`
  - `Doselab_MV.dcm`: `B940FA17209E48CD5A38E9F72AED2F2AA5C97E894F496BC6E0476D1B49B0E228`
  - `Doselab_kV.dcm`: `F8CF7C1F432A0DBF5CD9063E6F36D9E9F4E40E0D9A60C1BC857E4C9E00D82399`
  - `SNC-MV.dcm`: `F6CA0887918AFCEB9A861C9CB361810A5E8CAC29EB664A66932F0B3B4E6822D6`
  - `SNC_MV_12510.dcm`: `41BE005358A99076E1C43C5B83CA1524C7E487AB967A41669B555D937C4BC917`
  - `SNC-kV.dcm`: `F2ED3138B2C62F290198867F5AC463F1BF0436C7CFF25E5F4B3A2CD8492D77A4`
  - `PTW-EPID-QC.dcm`: `550316EA117ACBCA2C95A58B0F2FF172CC979AA923A0EE5917C2FB590E8E3563`
  - `iba_primus.dcm`: `0315FE36AA94C7CFAC2C45125EAF6B506B89E5FE6B4C67FC0E302D5CD678C65B`
  - `imtlrad.dcm`: `F1F6B08B270B96A3E61682538832020C7FABA026ABCDA3DAE1571C1818B617E7`
  - `Doselab_RLf.dcm`: `1C293EA17620820EC924C7B234A8C59842CE2B7BA316E059299A336E00C34686`
  - `ptw_isoalign.dcm`: `096E15E5C55BB0E2F29C0CF99ACBC2DA13A0E6713766ED8753C0FAD1393D53F2`
  - `FSQA_15x15.dcm`: `79808BC765E8832D450648C305CC0005A10819FBFD84416713F2D589DD7426FC`
  - `ACRDigitalMammography.dcm`: `894ACFA0EDC90E7C665973906FCE7F7E146BD32F8CE0AFC086DDED35665A60A0`

## Đối chiếu tên lớp danh mục

Các tên lớp trong danh mục đã được đối chiếu với tên biểu tượng runtime của registry. Lần đối chiếu này phát hiện và sửa các tên hiển thị nội bộ bị lệch ở ACR, CIRS, GE Helios, các bài ảnh phẳng và hàm Gamma; phiên bản danh mục tăng lên `pylinac-3.47.0-rt-connect-1.3`. Kiểm thử registry hiện buộc mọi tên lớp/hàm trong danh mục phải khớp biểu tượng của wheel đã khóa.

## Phạm vi còn mở

- CatPhan 700 chưa có tệp mẫu chính thức tương thích trong bộ tệp cục bộ.
- ACR CT/MRI, CIRS 062M, GE Helios và CatPhan 700 vẫn cần fixture riêng. Hai bài đóng góp đã có smoke test engine bằng fixture tổng hợp; vẫn cần tệp mẫu/commissioning đại diện, đối chiếu từng chỉ số, kiểm lỗi đặc trưng và staging. Chín bài hạt nhân cũng đã chạy qua đúng bộ chuyển đổi bằng dữ liệu tổng hợp hợp lệ nhưng vẫn cần các cổng tương tự. Toàn bộ 19 biến thể ảnh phẳng đã chạy qua đúng bộ chuyển đổi bằng tệp mẫu chính thức của Pylinac; vẫn cần đối chiếu staging riêng. Nhãn HyperSight đã có đường chạy tương thích local bằng `QuartDVT`, nhưng vẫn cần kiểm tra hiển thị và staging riêng.
- Cần đối chiếu từng chỉ số với kỳ vọng của bộ kiểm thử Pylinac, kiểm lỗi đầu vào, kiểm tài nguyên và chạy lại trên staging trước khi đóng gói tương ứng.
