"""Explicit fixture coverage for every locked Pylinac capability.

The runtime inventory proves that a symbol exists and is bound to the adapter.
This matrix records the stronger question: what kind of evidence can currently
exercise that capability.  It deliberately does not call a synthetic fixture
"commissioning" and does not make an unavailable official demo look complete.
"""

from __future__ import annotations

from typing import Final, Literal, TypedDict

FixtureStatus = Literal[
    "OFFICIAL_DEMO",
    "SYNTHETIC_CONTRACT",
    "COMMISSIONING_REQUIRED",
]


class FixtureCoverage(TypedDict):
    status: FixtureStatus
    reference: str
    note: str


_OFFICIAL_DEMO = "Bộ tệp mẫu chính thức Pylinac 3.47.0"
_SYNTHETIC_CONTRACT = "Bộ mẫu tổng hợp không có dữ liệu bệnh nhân"
_COMMISSIONING = "Chưa có bộ tệp commissioning được phê duyệt trong môi trường hiện tại"


def _official(filename: str) -> FixtureCoverage:
    return {
        "status": "OFFICIAL_DEMO",
        "reference": filename,
        "note": _OFFICIAL_DEMO,
    }


def _synthetic(note: str = _SYNTHETIC_CONTRACT) -> FixtureCoverage:
    return {
        "status": "SYNTHETIC_CONTRACT",
        "reference": "fixture tổng hợp nội bộ",
        "note": note,
    }


def _commissioning(note: str = _COMMISSIONING) -> FixtureCoverage:
    return {
        "status": "COMMISSIONING_REQUIRED",
        "reference": "fixture commissioning cần bổ sung",
        "note": note,
    }


FIXTURE_COVERAGE: Final[dict[str, FixtureCoverage]] = {
    "CALIBRATION_TG51_PHOTON": _commissioning("Cần số đo chuẩn TG-51 photon và đối chiếu độc lập."),
    "CALIBRATION_TG51_ELECTRON_LEGACY": _commissioning(
        "Cần số đo chuẩn TG-51 electron phiên bản cũ và đối chiếu độc lập."
    ),
    "CALIBRATION_TG51_ELECTRON_MODERN": _commissioning(
        "Cần số đo chuẩn TG-51 electron phiên bản mới và đối chiếu độc lập."
    ),
    "CALIBRATION_TRS398_PHOTON": _commissioning(
        "Cần số đo chuẩn TRS-398 photon và đối chiếu độc lập."
    ),
    "CALIBRATION_TRS398_ELECTRON": _commissioning(
        "Cần số đo chuẩn TRS-398 electron và đối chiếu độc lập."
    ),
    "STARSHOT": _official("starshot.tif"),
    "VMAT_DRGS": _official("drgs.zip"),
    "VMAT_DRMLC": _official("drmlc.zip"),
    "VMAT_DRCS": _official("drcs.zip"),
    "CATPHAN_503": _official("CatPhan503.zip"),
    "CATPHAN_504": _official("CatPhan504.zip"),
    "CATPHAN_600": _official("CatPhan600.zip"),
    "CATPHAN_604": _official("CatPhan604.zip"),
    "CATPHAN_700": _commissioning("Cần chuỗi DICOM CatPhan 700 và đối chiếu theo từng mô-đun."),
    "ACR_CT_464": _commissioning("Cần chuỗi DICOM phantom ACR CT 464."),
    "ACR_MRI_LARGE": _commissioning("Cần bộ ảnh phantom ACR MRI lớn."),
    "ACR_MRI_MEDIUM": _commissioning("Cần bộ ảnh phantom ACR MRI vừa."),
    "CHEESE_TOMO": _official("TomoCheese.zip"),
    "CHEESE_CIRS_062M": _commissioning("Cần chuỗi DICOM phantom CIRS 062M."),
    "GE_HELIOS": _commissioning("Cần chuỗi DICOM phantom GE Helios."),
    "QUART_DVT": _official("quart.zip"),
    "QUART_HYPERSIGHT": _official("quart.zip"),
    "LOG_DYNALOG": _official("AQA.dlg + BQA.dlg"),
    "LOG_TRAJECTORY_2_1": _official("Tlog.bin"),
    "LOG_TRAJECTORY_3": _commissioning("Cần tệp Trajectory Log 3 được xác nhận tương thích."),
    "LOG_TRAJECTORY_4": _commissioning("Cần tệp Trajectory Log 4 được xác nhận tương thích."),
    "PICKET_FENCE": _official("AS1200.dcm"),
    "WINSTON_LUTZ": _official("winston_lutz.zip"),
    "WINSTON_LUTZ_MULTI_TARGET": _official("SNC_MTWL_demo.zip"),
    "PLANAR_LEEDS_TOR_18": _official("leeds.dcm"),
    "PLANAR_LEEDS_TOR_BLUE": _official("leeds.dcm"),
    "PLANAR_STANDARD_IMAGING_QC3": _official("qc3.dcm"),
    "PLANAR_STANDARD_IMAGING_QC_KV": _official("SI-QC-kV.dcm"),
    "PLANAR_LAS_VEGAS": _official("lasvegas.dcm"),
    "PLANAR_ELEKTA_LAS_VEGAS": _official("elekta_las_vegas.dcm"),
    "PLANAR_DOSELAB_MC2_MV": _official("Doselab_MV.dcm"),
    "PLANAR_DOSELAB_MC2_KV": _official("Doselab_kV.dcm"),
    "PLANAR_SNC_MV": _official("SNC-MV.dcm"),
    "PLANAR_SNC_MV_12510": _official("SNC_MV_12510.dcm"),
    "PLANAR_SNC_KV": _official("SNC-kV.dcm"),
    "PLANAR_PTW_EPID_QC": _official("PTW-EPID-QC.dcm"),
    "PLANAR_IBA_PRIMUS_A": _official("iba_primus.dcm"),
    "PLANAR_STANDARD_IMAGING_FC2": _official("fc2.dcm"),
    "PLANAR_IMT_LRAD": _official("imtlrad.dcm"),
    "PLANAR_DOSELAB_RLF": _official("Doselab_RLf.dcm"),
    "PLANAR_PTW_ISO_ALIGN": _official("ptw_isoalign.dcm"),
    "PLANAR_SNC_FSQA": _official("FSQA_15x15.dcm"),
    "PLANAR_ACR_DIGITAL_MAMMOGRAPHY": _official("ACRDigitalMammography.dcm"),
    "FIELD_PROFILE_ANALYSIS": _official("AS1200.dcm"),
    "FIELD_ANALYSIS_LEGACY": _official("AS1200.dcm"),
    "NUCLEAR_MCR": _synthetic(),
    "NUCLEAR_PU": _synthetic(),
    "NUCLEAR_COR": _synthetic(),
    "NUCLEAR_TR": _synthetic(),
    "NUCLEAR_SS": _synthetic(),
    "NUCLEAR_FBR": _synthetic(),
    "NUCLEAR_QR": _synthetic(),
    "NUCLEAR_TU": _synthetic(),
    "NUCLEAR_TC": _synthetic(),
    "CONTRIB_QUASAR_LIGHT_RAD_SCALING": _synthetic("Cần phantom chuẩn để xác nhận nghiệp vụ."),
    "CONTRIB_JAW_ORTHOGONALITY": _synthetic("Cần ảnh commissioning để xác nhận nghiệp vụ."),
    "PSQA_GAMMA_1D": _synthetic("Chưa thay thế bộ đo commissioning."),
    "PSQA_GAMMA_2D": _synthetic("Chưa thay thế bộ đo commissioning."),
}


def fixture_coverage_diff(registered_keys: set[str]) -> dict[str, list[str]]:
    """Return missing or stale capability entries without silently defaulting."""

    covered_keys = set(FIXTURE_COVERAGE)
    return {
        "missing_catalog_keys": sorted(registered_keys - covered_keys),
        "unexpected_catalog_keys": sorted(covered_keys - registered_keys),
    }


def fixture_coverage_counts() -> dict[str, int]:
    counts: dict[str, int] = {
        "OFFICIAL_DEMO": 0,
        "SYNTHETIC_CONTRACT": 0,
        "COMMISSIONING_REQUIRED": 0,
    }
    for item in FIXTURE_COVERAGE.values():
        counts[item["status"]] += 1
    return counts
