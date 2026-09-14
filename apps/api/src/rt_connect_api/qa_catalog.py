"""Versioned user-facing catalogue for the QA tests supported by RT-CONNECT.

The catalogue is deliberately source-controlled instead of being editable data.
It is the contract between the QA menu, the input wizard and the future pylinac
adapters.  A definition can be visible before its adapter is released; the UI
must then show it as "Đang chuẩn bị" and must not pretend that analysis exists.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from pydantic import BaseModel, Field


class QATestDefinition(BaseModel):
    """A catalogue entry; keys are internal and are never rendered to users."""

    key: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=240)
    family: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    input_kind: str = Field(min_length=1, max_length=40)
    required_inputs: list[str]
    manual_controls: list[str]
    engine_name: str
    engine_class: str | None = None
    source_tier: str
    implementation_status: str
    is_legacy: bool = False
    supports_manual_adjustment: bool = False


class QATestDefinitionCollection(BaseModel):
    items: list[QATestDefinition]
    total: int
    catalogue_version: str


def _item(
    key: str,
    name: str,
    family: str,
    description: str,
    input_kind: str,
    required_inputs: tuple[str, ...],
    manual_controls: tuple[str, ...] = (),
    *,
    engine_class: str | None = None,
    source_tier: str = "PYLINAC_CORE",
    implementation_status: str = "PLANNED",
    is_legacy: bool = False,
    supports_manual_adjustment: bool = False,
) -> dict[str, object]:
    return {
        "key": key,
        "name": name,
        "family": family,
        "description": description,
        "input_kind": input_kind,
        "required_inputs": list(required_inputs),
        "manual_controls": list(manual_controls),
        "engine_name": "pylinac" if source_tier != "MANUAL" else "RT-CONNECT",
        "engine_class": engine_class,
        "source_tier": source_tier,
        "implementation_status": implementation_status,
        "is_legacy": is_legacy,
        "supports_manual_adjustment": supports_manual_adjustment,
    }


_CATALOG: tuple[dict[str, object], ...] = (
    _item(
        "MANUAL_MACHINE_QA",
        "Nhập số đo kiểm tra máy",
        "Nhập số đo",
        "Nhập các số đo đã thực hiện trên thiết bị và đánh giá theo bộ tiêu chí đã chọn.",
        "MEASUREMENT",
        ("Số đo", "Bộ tiêu chí"),
        ("Giá trị đo", "Đơn vị", "Ghi chú"),
        source_tier="MANUAL",
        implementation_status="READY",
    ),
    _item(
        "CALIBRATION_TG51_PHOTON",
        "Hiệu chuẩn TG-51 photon",
        "Hiệu chuẩn",
        "Tính toán hiệu chuẩn chùm photon theo bộ số đo đầu vào.",
        "MEASUREMENT",
        ("Số đo buồng ion hóa", "Điều kiện môi trường", "Hệ số hiệu chuẩn"),
        ("Nhiệt độ", "Áp suất", "Điện áp", "PDD hoặc TPR"),
        engine_class="TG51Photon",
    ),
    _item(
        "CALIBRATION_TG51_ELECTRON_LEGACY",
        "Hiệu chuẩn TG-51 electron phiên bản cũ",
        "Hiệu chuẩn",
        "Tính toán hiệu chuẩn chùm electron theo giao diện số đo.",
        "MEASUREMENT",
        ("Số đo buồng ion hóa", "Điều kiện môi trường", "Hệ số hiệu chuẩn"),
        ("Năng lượng", "Độ sâu", "Điện áp"),
        engine_class="TG51ElectronLegacy",
    ),
    _item(
        "CALIBRATION_TG51_ELECTRON_MODERN",
        "Hiệu chuẩn TG-51 electron hiện hành",
        "Hiệu chuẩn",
        "Tính toán hiệu chuẩn electron theo giao diện số đo và bộ thông số đã chọn.",
        "MEASUREMENT",
        ("Số đo buồng ion hóa", "Điều kiện môi trường", "Hệ số hiệu chuẩn"),
        ("Năng lượng", "Độ sâu", "Điện áp"),
        engine_class="TG51ElectronModern",
    ),
    _item(
        "CALIBRATION_TRS398_PHOTON",
        "Hiệu chuẩn TRS-398 photon",
        "Hiệu chuẩn",
        "Tính toán hiệu chuẩn photon theo giao diện số đo và phiên bản engine đã khóa.",
        "MEASUREMENT",
        ("Số đo buồng ion hóa", "Điều kiện môi trường", "Hệ số hiệu chuẩn"),
        ("Năng lượng", "Độ sâu", "Điện áp"),
        engine_class="TRS398Photon",
    ),
    _item(
        "CALIBRATION_TRS398_ELECTRON",
        "Hiệu chuẩn TRS-398 electron",
        "Hiệu chuẩn",
        "Tính toán hiệu chuẩn electron theo giao diện số đo và phiên bản engine đã khóa.",
        "MEASUREMENT",
        ("Số đo buồng ion hóa", "Điều kiện môi trường", "Hệ số hiệu chuẩn"),
        ("Năng lượng", "Độ sâu", "Điện áp"),
        engine_class="TRS398Electron",
    ),
    _item(
        "STARSHOT",
        "Kiểm tra sao",
        "Độ chính xác hình học",
        "Đánh giá độ ổn định tâm quay từ ảnh tia sao.",
        "IMAGE",
        ("Ảnh DICOM hoặc ảnh có thang đo",),
        ("Chọn tâm", "Bán kính", "Ngưỡng tìm đỉnh", "Độ rộng nửa cực đại", "Dung sai"),
        engine_class="Starshot",
        implementation_status="READY",
        supports_manual_adjustment=True,
    ),
    _item(
        "VMAT_DRGS",
        "Kiểm tra VMAT DRGS",
        "VMAT",
        "So sánh ảnh trường mở và ảnh trường điều biến theo bài DRGS.",
        "IMAGE_PAIR",
        ("Ảnh trường mở", "Ảnh trường điều biến"),
        ("Dung sai", "Vùng quan tâm", "Độ lệch"),
        engine_class="DRGS",
        implementation_status="READY",
        supports_manual_adjustment=True,
    ),
    _item(
        "VMAT_DRMLC",
        "Kiểm tra VMAT DRMLC",
        "VMAT",
        "So sánh ảnh trường mở và ảnh trường điều biến theo bài DRMLC.",
        "IMAGE_PAIR",
        ("Ảnh trường mở", "Ảnh trường điều biến"),
        ("Dung sai", "Vùng quan tâm", "Độ lệch"),
        engine_class="DRMLC",
        implementation_status="READY",
        supports_manual_adjustment=True,
    ),
    _item(
        "VMAT_DRCS",
        "Kiểm tra VMAT DRCS",
        "VMAT",
        "So sánh ảnh trường mở và ảnh trường điều biến theo bài DRCS.",
        "IMAGE_PAIR",
        ("Ảnh trường mở", "Ảnh trường điều biến"),
        ("Dung sai", "Vùng quan tâm", "Độ lệch"),
        engine_class="DRCS",
        implementation_status="READY",
        supports_manual_adjustment=True,
    ),
    _item(
        "CATPHAN_503",
        "Kiểm tra CatPhan 503",
        "Ảnh CT/CBCT",
        "Phân tích hình học, số HU, độ đồng nhất và độ phân giải của CatPhan 503.",
        "DICOM_SERIES",
        ("Chuỗi DICOM CT hoặc CBCT",),
        ("Chọn lát", "Tâm phantom", "Góc", "Kích thước vùng quan tâm", "Giá trị HU tham chiếu"),
        engine_class="CatPhan503",
        supports_manual_adjustment=True,
    ),
    _item(
        "CATPHAN_504",
        "Kiểm tra CatPhan 504",
        "Ảnh CT/CBCT",
        "Phân tích các mô-đun có trong CatPhan 504.",
        "DICOM_SERIES",
        ("Chuỗi DICOM CT hoặc CBCT",),
        ("Chọn lát", "Tâm phantom", "Góc", "Kích thước vùng quan tâm"),
        engine_class="CatPhan504",
        supports_manual_adjustment=True,
    ),
    _item(
        "CATPHAN_600",
        "Kiểm tra CatPhan 600",
        "Ảnh CT/CBCT",
        "Phân tích các mô-đun có trong CatPhan 600.",
        "DICOM_SERIES",
        ("Chuỗi DICOM CT hoặc CBCT",),
        ("Chọn lát", "Tâm phantom", "Góc", "Kích thước vùng quan tâm"),
        engine_class="CatPhan600",
        supports_manual_adjustment=True,
    ),
    _item(
        "CATPHAN_604",
        "Kiểm tra CatPhan 604",
        "Ảnh CT/CBCT",
        "Phân tích các mô-đun có trong CatPhan 604.",
        "DICOM_SERIES",
        ("Chuỗi DICOM CT hoặc CBCT",),
        ("Chọn lát", "Tâm phantom", "Góc", "Kích thước vùng quan tâm"),
        engine_class="CatPhan604",
        supports_manual_adjustment=True,
    ),
    _item(
        "ACR_CT_464",
        "Kiểm tra phantom ACR CT 464",
        "Phantom ACR",
        "Phân tích các mô-đun của phantom ACR CT 464.",
        "DICOM_SERIES",
        ("Chuỗi DICOM CT",),
        ("Chọn lát", "Tâm phantom", "Vùng quan tâm"),
        engine_class="ACRCT464",
        supports_manual_adjustment=True,
    ),
    _item(
        "ACR_MRI_LARGE",
        "Kiểm tra phantom ACR MRI lớn",
        "Phantom ACR",
        "Phân tích phantom MRI ACR kích thước lớn.",
        "DICOM_SERIES",
        ("Chuỗi DICOM MRI",),
        ("Chọn lát", "Tâm phantom", "Vùng quan tâm"),
        engine_class="ACRMriLarge",
        supports_manual_adjustment=True,
    ),
    _item(
        "ACR_MRI_MEDIUM",
        "Kiểm tra phantom ACR MRI vừa",
        "Phantom ACR",
        "Phân tích phantom MRI ACR kích thước vừa.",
        "DICOM_SERIES",
        ("Chuỗi DICOM MRI",),
        ("Chọn lát", "Tâm phantom", "Vùng quan tâm"),
        engine_class="ACRMriMedium",
        supports_manual_adjustment=True,
    ),
    _item(
        "CHEESE_TOMO",
        "Kiểm tra phantom TomoCheese",
        "Phantom đo liều",
        "Phân tích các vùng mật độ và đường đáp ứng của TomoCheese.",
        "DICOM_SERIES",
        ("Chuỗi DICOM phantom",),
        ("Chọn lát", "Điều chỉnh vùng quan tâm", "Giá trị tham chiếu"),
        engine_class="TomoCheese",
        supports_manual_adjustment=True,
    ),
    _item(
        "CHEESE_CIRS_062M",
        "Kiểm tra phantom CIRS 062M",
        "Phantom đo liều",
        "Phân tích các vùng mật độ và đường đáp ứng của CIRS 062M.",
        "DICOM_SERIES",
        ("Chuỗi DICOM phantom",),
        ("Chọn lát", "Điều chỉnh vùng quan tâm", "Giá trị tham chiếu"),
        engine_class="Cirs062M",
        supports_manual_adjustment=True,
    ),
    _item(
        "GE_HELIOS",
        "Kiểm tra CT GE Helios hằng ngày",
        "Phantom CT",
        "Phân tích thang tương phản, nhiễu, độ đồng nhất và tương phản thấp.",
        "DICOM_SERIES",
        ("Chuỗi DICOM phantom",),
        ("Chọn lát", "Điều chỉnh vùng quan tâm", "Ngưỡng"),
        engine_class="GECatPhan",
        supports_manual_adjustment=True,
    ),
    _item(
        "QUART_DVT",
        "Kiểm tra phantom Quart DVT",
        "Phantom CT",
        "Phân tích số HU, hình học, độ đồng nhất và tỷ số tương phản trên Quart DVT.",
        "DICOM_SERIES",
        ("Chuỗi DICOM CT hoặc CBCT",),
        ("Chọn lát", "Tâm phantom", "Vùng quan tâm"),
        engine_class="QuartDVT",
        supports_manual_adjustment=True,
    ),
    _item(
        "QUART_HYPERSIGHT",
        "Kiểm tra phantom Quart HyperSight",
        "Phantom CT",
        "Phân tích biến thể Quart HyperSight khi phiên bản engine đã khóa còn hỗ trợ.",
        "DICOM_SERIES",
        ("Chuỗi DICOM CT hoặc CBCT",),
        ("Chọn lát", "Tâm phantom", "Vùng quan tâm"),
        engine_class="QuartHyperSight",
        supports_manual_adjustment=True,
    ),
    _item(
        "LOG_DYNALOG",
        "Phân tích tệp Dynalog Varian",
        "Tệp nhật ký máy",
        "Đọc cặp tệp nhật ký Dynalog và hiển thị sai lệch chuyển động của lá.",
        "LOG_PAIR",
        ("Cặp tệp Dynalog",),
        ("Ngưỡng sai lệch", "Lọc chùm tia", "Chọn biểu đồ"),
        engine_class="Dynalog",
        supports_manual_adjustment=True,
    ),
    _item(
        "LOG_TRAJECTORY_2_1",
        "Phân tích Trajectory Log 2.1",
        "Tệp nhật ký máy",
        "Đọc tệp Trajectory Log 2.1 và hiển thị actual, expected và sai lệch.",
        "LOG",
        ("Tệp Trajectory Log",),
        ("Ngưỡng sai lệch", "Chọn chùm tia", "Chọn biểu đồ"),
        engine_class="TrajectoryLog",
        supports_manual_adjustment=True,
    ),
    _item(
        "LOG_TRAJECTORY_3",
        "Phân tích Trajectory Log 3",
        "Tệp nhật ký máy",
        "Đọc tệp Trajectory Log 3 và hiển thị actual, expected và sai lệch.",
        "LOG",
        ("Tệp Trajectory Log",),
        ("Ngưỡng sai lệch", "Chọn chùm tia", "Chọn biểu đồ"),
        engine_class="TrajectoryLog",
        supports_manual_adjustment=True,
    ),
    _item(
        "LOG_TRAJECTORY_4",
        "Phân tích Trajectory Log 4",
        "Tệp nhật ký máy",
        "Đọc tệp Trajectory Log 4 và hiển thị actual, expected và sai lệch.",
        "LOG",
        ("Tệp Trajectory Log",),
        ("Ngưỡng sai lệch", "Chọn chùm tia", "Chọn biểu đồ"),
        engine_class="TrajectoryLog",
        supports_manual_adjustment=True,
    ),
    _item(
        "PICKET_FENCE",
        "Kiểm tra hàng rào lá",
        "Độ chính xác MLC",
        "Phân tích vị trí lá và vạch trên ảnh trường Picket Fence.",
        "IMAGE",
        ("Ảnh DICOM EPID hoặc ảnh có thang đo",),
         ("Hướng ảnh", "Cắt ảnh", "Mẫu MLC", "Dung sai", "Dung sai hành động", "Độ võng"),
         engine_class="PicketFence",
         supports_manual_adjustment=True,
         implementation_status="READY",
     ),
    _item(
        "WINSTON_LUTZ",
        "Kiểm tra Winston–Lutz",
        "Độ chính xác hình học",
        "Phân tích khoảng cách giữa bi chuẩn và trục trường theo từng góc.",
        "IMAGE_SERIES",
        ("Bộ ảnh Winston–Lutz",),
        ("Ánh xạ góc", "Hệ tọa độ", "Nhận diện bi", "Nhận diện trường"),
        engine_class="WinstonLutz",
        implementation_status="READY",
        supports_manual_adjustment=True,
    ),
    _item(
        "WINSTON_LUTZ_MULTI_TARGET",
        "Kiểm tra Winston–Lutz nhiều bi nhiều trường",
        "Độ chính xác hình học",
        "Ghép nhiều bi và nhiều trường để đánh giá từng mục tiêu và tổng hợp.",
        "IMAGE_SERIES",
        ("Bộ ảnh nhiều bi và nhiều trường",),
        ("Ghép bi với trường", "Ánh xạ góc", "Hệ tọa độ", "Ngưỡng nhận diện"),
        engine_class="WinstonLutzMultiTargetMultiField",
        implementation_status="READY",
        supports_manual_adjustment=True,
    ),
)


_PLANAR_VARIANTS: tuple[tuple[str, str, str], ...] = (
    ("LEEDS_TOR_18", "Leeds TOR 18", "Leeds TOR 18"),
    ("LEEDS_TOR_BLUE", "Leeds TOR Blue", "Leeds TOR Blue"),
    ("STANDARD_IMAGING_QC3", "Standard Imaging QC-3", "StandardImagingQC3"),
    ("STANDARD_IMAGING_QC_KV", "Standard Imaging QC-kV", "StandardImagingQCKV"),
    ("LAS_VEGAS", "Las Vegas", "LasVegas"),
    ("ELEKTA_LAS_VEGAS", "Elekta Las Vegas", "ElektaLasVegas"),
    ("DOSELAB_MC2_MV", "Doselab MC2 MV", "DoselabMC2MV"),
    ("DOSELAB_MC2_KV", "Doselab MC2 kV", "DoselabMC2KV"),
    ("SNC_MV", "SNC MV", "SNCVMV"),
    ("SNC_MV_12510", "SNC MV 12510", "SNCVMV12510"),
    ("SNC_KV", "SNC kV", "SNCVKv"),
    ("PTW_EPID_QC", "PTW EPID QC", "PTWEPIDQC"),
    ("IBA_PRIMUS_A", "IBA Primus A", "IBAPrimusA"),
    ("STANDARD_IMAGING_FC2", "Standard Imaging FC-2", "StandardImagingFC2"),
    ("IMT_LRAD", "IMT L-RAD", "IMTLRAD"),
    ("DOSELAB_RLF", "Doselab RLf", "DoselabRLf"),
    ("PTW_ISO_ALIGN", "PTW Iso-Align", "PTWIsoAlign"),
    ("SNC_FSQA", "SNC FSQA", "SNCFSQA"),
    ("ACR_DIGITAL_MAMMOGRAPHY", "ACR Digital Mammography", "ACRDigitalMammography"),
)


_NUCLEAR_VARIANTS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("MCR", "Tốc độ đếm cực đại", "MaxCountRate", ("Ảnh hoặc chuỗi DICOM", "Thời lượng frame")),
    ("PU", "Độ đồng nhất phẳng", "PlanarUniformity", ("Ảnh hoặc chuỗi DICOM", "Vùng quan tâm")),
    ("COR", "Tâm quay", "CenterOfRotation", ("Bộ ảnh quay", "Thang đo")),
    ("TR", "Độ phân giải cắt lớp", "TomographicResolution", ("Dữ liệu SPECT",)),
    ("SS", "Độ nhạy đơn giản", "SimpleSensitivity", ("Ảnh phantom", "Hoạt độ", "Thời gian")),
    ("FBR", "Độ phân giải bốn vạch", "FourBarResolution", ("Ảnh phantom", "Thang đo")),
    ("QR", "Độ phân giải bốn góc", "QuadrantResolution", ("Ảnh phantom", "Vùng quan tâm")),
    ("TU", "Độ đồng nhất cắt lớp", "TomographicUniformity", ("Dữ liệu SPECT", "Khoảng frame")),
    (
        "TC",
        "Độ tương phản cắt lớp",
        "TomographicContrast",
        ("Dữ liệu SPECT", "Cấu hình vùng quan tâm"),
    ),
)


def _build_catalog() -> tuple[dict[str, object], ...]:
    items = list(_CATALOG)
    for key, name, engine_class in _PLANAR_VARIANTS:
        items.append(
            _item(
                f"PLANAR_{key}",
                f"Kiểm tra ảnh phẳng {name}",
                "Ảnh phẳng",
                f"Phân tích chất lượng ảnh phẳng bằng bài {name}.",
                "IMAGE",
                ("Ảnh DICOM hoặc định dạng được hỗ trợ",),
                ("Tâm phantom", "Góc", "Vùng quan tâm", "Thang đo", "Đảo ảnh"),
                engine_class=engine_class,
                supports_manual_adjustment=True,
            )
        )
    items.extend(
        [
            _item(
                "FIELD_PROFILE_ANALYSIS",
                "Phân tích biên dạng trường",
                "Phân tích trường",
                "Đo độ rộng trường, độ phẳng, đối xứng và vùng penumbra từ biên dạng.",
                "IMAGE_OR_PROFILE",
                ("Ảnh trường hoặc dữ liệu biên dạng",),
                ("Vị trí biên dạng", "Độ rộng dải lấy mẫu", "Chuẩn hóa", "Chỉ số"),
                engine_class="FieldProfileAnalysis",
                implementation_status="READY",
                supports_manual_adjustment=True,
            ),
            _item(
                "FIELD_ANALYSIS_LEGACY",
                "Phân tích trường phiên bản cũ",
                "Phân tích trường",
                "Mở và phân tích dữ liệu theo mô-đun cũ để giữ tương thích hồ sơ lịch sử.",
                "IMAGE_OR_PROFILE",
                ("Ảnh trường hoặc dữ liệu biên dạng",),
                ("Vị trí biên dạng", "Độ rộng dải lấy mẫu", "Chuẩn hóa", "Chỉ số"),
                engine_class="FieldAnalysis",
                is_legacy=True,
                implementation_status="READY",
                supports_manual_adjustment=True,
            ),
        ]
    )
    for suffix, name, engine_class, required_inputs in _NUCLEAR_VARIANTS:
        items.append(
            _item(
                f"NUCLEAR_{suffix}",
                f"Kiểm tra hạt nhân {name.lower()}",
                "Kiểm tra hạt nhân",
                f"Thực hiện phép thử {name} theo dữ liệu và thông số đầu vào phù hợp.",
                "NUCLEAR",
                required_inputs,
                ("Khung ảnh", "Vùng quan tâm", "Ngưỡng", "Thang đo"),
                engine_class=engine_class,
                supports_manual_adjustment=True,
            )
        )
    items.extend(
        [
            _item(
                "CONTRIB_QUASAR_LIGHT_RAD_SCALING",
                "Quasar Light và Rad Scaling",
                "Mô-đun đóng góp",
                "Phân tích Quasar Light và Rad Scaling theo mô-đun đóng góp của pylinac.",
                "IMAGE",
                ("Ảnh phantom",),
                ("Đảo ảnh", "FWXM", "Ngưỡng biên bi"),
                engine_class="QuasarLightRadScaling",
                source_tier="PYLINAC_CONTRIB",
                supports_manual_adjustment=True,
            ),
            _item(
                "CONTRIB_JAW_ORTHOGONALITY",
                "Độ vuông góc của jaw",
                "Mô-đun đóng góp",
                "Đánh giá bốn cạnh trường và độ vuông góc theo mô-đun đóng góp của pylinac.",
                "IMAGE",
                ("Ảnh trường",),
                ("Ngưỡng cạnh", "Chọn bốn cạnh", "Hiển thị góc"),
                engine_class="JawOrthogonality",
                source_tier="PYLINAC_CONTRIB",
                supports_manual_adjustment=True,
            ),
            _item(
                "PSQA_GAMMA_1D",
                "Phân tích Gamma PSQA một chiều",
                "PSQA",
                "So sánh biên dạng liều đo và tham chiếu với chênh lệch liều "
                "và DTA do người dùng nhập.",
                "PROFILE_PAIR",
                ("Biên dạng liều tham chiếu", "Biên dạng liều đo", "Chênh lệch liều", "DTA"),
                ("Chuẩn hóa", "Ngưỡng liều thấp", "Vùng tính"),
                engine_class="profile.gamma_1d",
                supports_manual_adjustment=True,
            ),
            _item(
                "PSQA_GAMMA_2D",
                "Phân tích Gamma PSQA hai chiều",
                "PSQA",
                "So sánh ảnh liều tham chiếu và ảnh liều đo với thông số DTA, "
                "chênh lệch liều và ngưỡng.",
                "IMAGE_PAIR",
                ("Ảnh liều tham chiếu", "Ảnh liều đo", "Chênh lệch liều", "DTA"),
                ("Chuẩn hóa", "Ngưỡng liều thấp", "Vùng tính", "Nội suy"),
                engine_class="image.gamma_2d",
                supports_manual_adjustment=True,
            ),
        ]
    )
    return tuple(items)


QA_TEST_CATALOG: Final[tuple[QATestDefinition, ...]] = tuple(
    QATestDefinition.model_validate(item) for item in _build_catalog()
)
CATALOGUE_VERSION: Final[str] = "pylinac-3.47.0-rt-connect-1.0"


def get_qa_test_definition(key: str) -> QATestDefinition | None:
    normalized = key.strip().upper()
    return next((item for item in QA_TEST_CATALOG if item.key == normalized), None)


def catalogue_mapping() -> Mapping[str, QATestDefinition]:
    return {item.key: item for item in QA_TEST_CATALOG}
