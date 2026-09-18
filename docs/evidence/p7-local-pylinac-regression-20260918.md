# Hồi quy Pylinac toàn bộ nhóm hiện có — 2026-09-18

## Phạm vi

Đã chạy bằng Python 3.14.5 trong môi trường khóa của API các nhóm:

- hiệu chuẩn;
- bài đóng góp;
- ma trận lỗi;
- bộ điều hợp Gamma;
- bài hạt nhân;
- ma trận tệp mẫu chính thức;
- API Pylinac;
- registry và ma trận độ phủ.

Lệnh thực thi là:

```text
python -m pytest apps/api/tests/test_pylinac_calibration_engine.py apps/api/tests/test_pylinac_contrib_engine.py apps/api/tests/test_pylinac_error_matrix.py apps/api/tests/test_pylinac_gamma_adapter.py apps/api/tests/test_pylinac_nuclear_engine.py apps/api/tests/test_pylinac_official_demo_matrix.py apps/api/tests/test_pylinac_qa.py apps/api/tests/test_pylinac_registry.py
```

## Kết quả

- **139/139 kiểm thử đạt**.
- 4 cảnh báo, đều là cảnh báo tương thích từ Starlette/httpx và cảnh báo thay đổi nhiệt độ tham chiếu của Pylinac TRS-398; không có kiểm thử thất bại.
- Không tạo, sửa, lưu trữ, khôi phục hoặc xóa hồ sơ staging; hồ sơ `dailyQA` không bị chạm tới.

## Giới hạn bằng chứng

Đây là bằng chứng hồi quy engine và hợp đồng local. Kết quả không được gọi là commissioning hoặc nghiệm thu lâm sàng. Các fixture ACR, CIRS 062M, GE Helios, CatPhan 700, Trajectory Log 3/4, fixture chuẩn cho Nuclear/Contrib, đối chiếu độc lập từng chỉ số và kiểm chứng thao tác xác thực trên staging vẫn là các cổng mở của P7.
