# Bằng chứng P7 — ma trận tệp mẫu Pylinac 3.47.0

- Ngày kiểm tra: 2026-09-15
- Môi trường: máy phát triển, wheel Pylinac 3.47.0 đã khóa
- Phạm vi: gọi trực tiếp `execute_pylinac`, lấy structured result và ảnh overlay; không ghi dữ liệu staging
- Kết luận: các dòng dưới đây đạt lát cắt `LOCAL_VERIFIED_SLICE`, không phải nghiệm thu lâm sàng

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
| Leeds TOR | `leeds.dcm` | `LeedsTOR` | 12 | 73719 byte |
| Standard Imaging FC-2 | `fc2.dcm` | `StandardImagingFC2` | 9 | 69586 byte |
| Field Profile Analysis | `AS1200.dcm` | `FieldProfileAnalysis` | 9 | 54772 byte |
| Field Analysis legacy | `AS1200.dcm` | `FieldAnalysis` | 42 | 57977 byte |
| Dynalog | `AQA.dlg` + `BQA.dlg` | `Dynalog` | 10 | 9221 byte |
| Trajectory Log 2.1 | `Tlog.bin` | `TrajectoryLog` | 13 | 8500 byte |

## Mã kiểm tra

- Luồng dùng thư mục tạm để giải nén các gói ZIP; dữ liệu tạm được dọn sau khi chạy.
- Mỗi bài phải qua cùng một lớp chuyển đổi đang được API sử dụng, không gọi riêng một đường tắt chỉ dành cho kiểm thử.
- Kết quả phải có lớp engine đúng với registry, structured result không rỗng và overlay khi lớp Pylinac cung cấp ảnh phân tích.
- Starshot sử dụng `sid = 1000 mm`, vì tệp TIFF không chứa thẻ khoảng cách nguồn–ảnh.
- Dynalog không có overlay ảnh; bộ chuyển đổi lưu các chỉ số MLC và biểu đồ lỗi khi Pylinac tạo được tệp biểu đồ.
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

## Phạm vi còn mở

- CatPhan 700 chưa có tệp mẫu chính thức tương thích trong bộ tệp cục bộ.
- ACR CT/MRI, CIRS 062M, GE Helios, Quart HyperSight, 17 biến thể ảnh phẳng còn lại, chín bài hạt nhân và hai bài đóng góp cần fixture riêng.
- Cần đối chiếu từng chỉ số với kỳ vọng của bộ kiểm thử Pylinac, kiểm lỗi đầu vào, kiểm tài nguyên và chạy lại trên staging trước khi đóng gói tương ứng.
