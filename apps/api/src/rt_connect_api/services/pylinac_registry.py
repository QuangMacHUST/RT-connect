"""Runtime inventory and provenance boundary for the locked pylinac wheel.

The catalogue is user-facing, while this registry is the execution contract.
Every non-manual catalogue entry must resolve to a real pylinac class/function
in the installed wheel before an adapter can expose it as executable.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, TypedDict

from rt_connect_api.qa_catalog import QA_TEST_CATALOG, QATestDefinition

PYLINAC_VERSION: Final[str] = "3.47.0"
PYLINAC_WHEEL_SHA256: Final[str] = (
    "7a99ec70a0242fa645882152fb5aa012f176b943a78339a3a18c15c953331b68"
)


@dataclass(frozen=True)
class RuntimeBinding:
    catalog_key: str
    import_path: str
    symbol_kind: str
    input_profile: str
    module_family: str


@dataclass(frozen=True)
class PylinacCapability:
    catalog_key: str
    display_name: str
    module_family: str
    import_path: str
    symbol_kind: str
    input_profile: str
    source_tier: str
    runtime_available: bool
    has_analyze: bool
    has_results_data: bool
    resolution_error: str | None


class CapabilitySummary(TypedDict):
    catalog_key: str
    display_name: str
    module_family: str
    import_path: str
    symbol_kind: str
    input_profile: str
    source_tier: str
    runtime_available: bool
    has_analyze: bool
    has_results_data: bool
    resolution_error: str | None


class RegistrySummary(TypedDict):
    catalogue_version: str
    pylinac_version: str
    wheel_sha256: str
    package_fingerprint: str
    total_bindings: int
    runtime_available: int
    unresolved_catalog_keys: list[str]
    capabilities: list[CapabilitySummary]


def _class(key: str, path: str, profile: str, family: str) -> RuntimeBinding:
    return RuntimeBinding(key, path, "class", profile, family)


def _function(key: str, path: str, profile: str, family: str) -> RuntimeBinding:
    return RuntimeBinding(key, path, "function", profile, family)


RUNTIME_BINDINGS: Final[tuple[RuntimeBinding, ...]] = (
    _class(
        "CALIBRATION_TG51_PHOTON",
        "pylinac.calibration.tg51.TG51Photon",
        "measurement",
        "Calibration",
    ),
    _class(
        "CALIBRATION_TG51_ELECTRON_LEGACY",
        "pylinac.calibration.tg51.TG51ElectronLegacy",
        "measurement",
        "Calibration",
    ),
    _class(
        "CALIBRATION_TG51_ELECTRON_MODERN",
        "pylinac.calibration.tg51.TG51ElectronModern",
        "measurement",
        "Calibration",
    ),
    _class(
        "CALIBRATION_TRS398_PHOTON",
        "pylinac.calibration.trs398.TRS398Photon",
        "measurement",
        "Calibration",
    ),
    _class(
        "CALIBRATION_TRS398_ELECTRON",
        "pylinac.calibration.trs398.TRS398Electron",
        "measurement",
        "Calibration",
    ),
    _class("STARSHOT", "pylinac.starshot.Starshot", "image", "Starshot"),
    _class("VMAT_DRGS", "pylinac.vmat.DRGS", "image_pair", "VMAT"),
    _class("VMAT_DRMLC", "pylinac.vmat.DRMLC", "image_pair", "VMAT"),
    _class("VMAT_DRCS", "pylinac.vmat.DRCS", "image_pair", "VMAT"),
    _class("CATPHAN_503", "pylinac.ct.CatPhan503", "dicom_series", "CatPhan"),
    _class("CATPHAN_504", "pylinac.ct.CatPhan504", "dicom_series", "CatPhan"),
    _class("CATPHAN_600", "pylinac.ct.CatPhan600", "dicom_series", "CatPhan"),
    _class("CATPHAN_604", "pylinac.ct.CatPhan604", "dicom_series", "CatPhan"),
    _class("CATPHAN_700", "pylinac.ct.CatPhan700", "dicom_series", "CatPhan"),
    _class("ACR_CT_464", "pylinac.acr.ACRCT", "dicom_series", "ACR"),
    _class("ACR_MRI_LARGE", "pylinac.acr.ACRMRILarge", "dicom_series", "ACR"),
    _class("ACR_MRI_MEDIUM", "pylinac.acr.ACRMRIMedium", "dicom_series", "ACR"),
    _class("CHEESE_TOMO", "pylinac.cheese.TomoCheese", "dicom_series", "Cheese"),
    _class("CHEESE_CIRS_062M", "pylinac.cheese.CIRS062M", "dicom_series", "Cheese"),
    _class("GE_HELIOS", "pylinac.helios.GEHeliosCTDaily", "dicom_series", "GE Helios"),
    _class("QUART_DVT", "pylinac.quart.QuartDVT", "dicom_series", "Quart"),
    _class("QUART_HYPERSIGHT", "pylinac.quart.HypersightQuartDVT", "dicom_series", "Quart"),
    _class("LOG_DYNALOG", "pylinac.log_analyzer.Dynalog", "log_pair", "Log Analyzer"),
    _class("LOG_TRAJECTORY_2_1", "pylinac.log_analyzer.TrajectoryLog", "log", "Log Analyzer"),
    _class("LOG_TRAJECTORY_3", "pylinac.log_analyzer.TrajectoryLog", "log", "Log Analyzer"),
    _class("LOG_TRAJECTORY_4", "pylinac.log_analyzer.TrajectoryLog", "log", "Log Analyzer"),
    _class("PICKET_FENCE", "pylinac.picketfence.PicketFence", "image", "Picket Fence"),
    _class("WINSTON_LUTZ", "pylinac.winston_lutz.WinstonLutz", "image_series", "Winston–Lutz"),
    _class(
        "WINSTON_LUTZ_MULTI_TARGET",
        "pylinac.winston_lutz.WinstonLutzMultiTargetMultiField",
        "image_series",
        "Winston–Lutz Multi-Target",
    ),
    _class("PLANAR_LEEDS_TOR_18", "pylinac.planar_imaging.LeedsTOR", "image", "Planar Imaging"),
    _class(
        "PLANAR_LEEDS_TOR_BLUE", "pylinac.planar_imaging.LeedsTORBlue", "image", "Planar Imaging"
    ),
    _class(
        "PLANAR_STANDARD_IMAGING_QC3",
        "pylinac.planar_imaging.StandardImagingQC3",
        "image",
        "Planar Imaging",
    ),
    _class(
        "PLANAR_STANDARD_IMAGING_QC_KV",
        "pylinac.planar_imaging.StandardImagingQCkV",
        "image",
        "Planar Imaging",
    ),
    _class("PLANAR_LAS_VEGAS", "pylinac.planar_imaging.LasVegas", "image", "Planar Imaging"),
    _class(
        "PLANAR_ELEKTA_LAS_VEGAS",
        "pylinac.planar_imaging.ElektaLasVegas",
        "image",
        "Planar Imaging",
    ),
    _class(
        "PLANAR_DOSELAB_MC2_MV", "pylinac.planar_imaging.DoselabMC2MV", "image", "Planar Imaging"
    ),
    _class(
        "PLANAR_DOSELAB_MC2_KV", "pylinac.planar_imaging.DoselabMC2kV", "image", "Planar Imaging"
    ),
    _class("PLANAR_SNC_MV", "pylinac.planar_imaging.SNCMV", "image", "Planar Imaging"),
    _class("PLANAR_SNC_MV_12510", "pylinac.planar_imaging.SNCMV12510", "image", "Planar Imaging"),
    _class("PLANAR_SNC_KV", "pylinac.planar_imaging.SNCkV", "image", "Planar Imaging"),
    _class("PLANAR_PTW_EPID_QC", "pylinac.planar_imaging.PTWEPIDQC", "image", "Planar Imaging"),
    _class("PLANAR_IBA_PRIMUS_A", "pylinac.planar_imaging.IBAPrimusA", "image", "Planar Imaging"),
    _class(
        "PLANAR_STANDARD_IMAGING_FC2",
        "pylinac.planar_imaging.StandardImagingFC2",
        "image",
        "Planar Imaging",
    ),
    _class("PLANAR_IMT_LRAD", "pylinac.planar_imaging.IMTLRad", "image", "Planar Imaging"),
    _class("PLANAR_DOSELAB_RLF", "pylinac.planar_imaging.DoselabRLf", "image", "Planar Imaging"),
    _class("PLANAR_PTW_ISO_ALIGN", "pylinac.planar_imaging.IsoAlign", "image", "Planar Imaging"),
    _class("PLANAR_SNC_FSQA", "pylinac.planar_imaging.SNCFSQA", "image", "Planar Imaging"),
    _class(
        "PLANAR_ACR_DIGITAL_MAMMOGRAPHY",
        "pylinac.planar_imaging.ACRDigitalMammography",
        "image",
        "Planar Imaging",
    ),
    _class(
        "FIELD_PROFILE_ANALYSIS",
        "pylinac.field_profile_analysis.FieldProfileAnalysis",
        "image_or_profile",
        "Field Profile Analysis",
    ),
    _class(
        "FIELD_ANALYSIS_LEGACY",
        "pylinac.field_analysis.FieldAnalysis",
        "image_or_profile",
        "Field Analysis",
    ),
    _class("NUCLEAR_MCR", "pylinac.nuclear.MaxCountRate", "nuclear", "Nuclear"),
    _class("NUCLEAR_PU", "pylinac.nuclear.PlanarUniformity", "nuclear", "Nuclear"),
    _class("NUCLEAR_COR", "pylinac.nuclear.CenterOfRotation", "nuclear", "Nuclear"),
    _class("NUCLEAR_TR", "pylinac.nuclear.TomographicResolution", "nuclear", "Nuclear"),
    _class("NUCLEAR_SS", "pylinac.nuclear.SimpleSensitivity", "nuclear", "Nuclear"),
    _class("NUCLEAR_FBR", "pylinac.nuclear.FourBarResolution", "nuclear", "Nuclear"),
    _class("NUCLEAR_QR", "pylinac.nuclear.QuadrantResolution", "nuclear", "Nuclear"),
    _class("NUCLEAR_TU", "pylinac.nuclear.TomographicUniformity", "nuclear", "Nuclear"),
    _class("NUCLEAR_TC", "pylinac.nuclear.TomographicContrast", "nuclear", "Nuclear"),
    _class(
        "CONTRIB_QUASAR_LIGHT_RAD_SCALING",
        "pylinac.contrib.quasar.QuasarLightRadScaling",
        "image",
        "One-Offs/Contrib QA",
    ),
    _class(
        "CONTRIB_JAW_ORTHOGONALITY",
        "pylinac.contrib.orthogonality.JawOrthogonality",
        "image",
        "One-Offs/Contrib QA",
    ),
    _function("PSQA_GAMMA_1D", "pylinac.core.gamma.gamma_1d", "profile_pair", "Gamma"),
    _function("PSQA_GAMMA_2D", "pylinac.core.gamma.gamma_2d", "image_pair", "Gamma"),
)

_BINDINGS_BY_KEY: Final[dict[str, RuntimeBinding]] = {
    binding.catalog_key: binding for binding in RUNTIME_BINDINGS
}


def _resolve(path: str) -> tuple[Any | None, str | None]:
    module_name, symbol_name = path.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
        return getattr(module, symbol_name), None
    except (AttributeError, ImportError, ModuleNotFoundError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _definition_by_key() -> dict[str, QATestDefinition]:
    return {definition.key: definition for definition in QA_TEST_CATALOG}


def _package_fingerprint() -> str:
    distribution = importlib.metadata.distribution("pylinac")
    digest = hashlib.sha256()
    root = Path(str(distribution.locate_file("pylinac")))
    for path in sorted(root.rglob("*.py")):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


@lru_cache(maxsize=1)
def installed_pylinac_version() -> str:
    return importlib.metadata.version("pylinac")


@lru_cache(maxsize=1)
def package_fingerprint() -> str:
    return _package_fingerprint()


@lru_cache(maxsize=1)
def resolve_capabilities() -> tuple[PylinacCapability, ...]:
    definitions = _definition_by_key()
    capabilities: list[PylinacCapability] = []
    for binding in RUNTIME_BINDINGS:
        definition = definitions[binding.catalog_key]
        symbol, error = _resolve(binding.import_path)
        is_class = isinstance(symbol, type)
        has_analyze = bool(is_class and hasattr(symbol, "analyze"))
        has_results_data = bool(is_class and hasattr(symbol, "results_data"))
        capabilities.append(
            PylinacCapability(
                catalog_key=binding.catalog_key,
                display_name=definition.name,
                module_family=binding.module_family,
                import_path=binding.import_path,
                symbol_kind=binding.symbol_kind,
                input_profile=binding.input_profile,
                source_tier=definition.source_tier,
                runtime_available=symbol is not None,
                has_analyze=has_analyze,
                has_results_data=has_results_data,
                resolution_error=error,
            )
        )
    return tuple(capabilities)


def unresolved_catalog_keys() -> tuple[str, ...]:
    resolved = {
        capability.catalog_key
        for capability in resolve_capabilities()
        if capability.runtime_available
    }
    return tuple(
        definition.key
        for definition in QA_TEST_CATALOG
        if definition.engine_name == "pylinac" and definition.key not in resolved
    )


def runtime_binding(catalog_key: str) -> RuntimeBinding | None:
    """Return the execution binding for a catalogue key, if it is registered."""

    return _BINDINGS_BY_KEY.get(catalog_key)


def resolve_runtime_symbol(catalog_key: str) -> tuple[Any | None, str | None]:
    """Resolve one registered symbol without exposing import details to callers."""

    binding = runtime_binding(catalog_key)
    if binding is None:
        return None, f"No runtime binding is registered for {catalog_key}."
    return _resolve(binding.import_path)


def registry_summary() -> RegistrySummary:
    capabilities = resolve_capabilities()
    unresolved = unresolved_catalog_keys()
    capability_summaries: list[CapabilitySummary] = [
        {
            "catalog_key": item.catalog_key,
            "display_name": item.display_name,
            "module_family": item.module_family,
            "import_path": item.import_path,
            "symbol_kind": item.symbol_kind,
            "input_profile": item.input_profile,
            "source_tier": item.source_tier,
            "runtime_available": item.runtime_available,
            "has_analyze": item.has_analyze,
            "has_results_data": item.has_results_data,
            "resolution_error": item.resolution_error,
        }
        for item in capabilities
    ]
    return {
        "catalogue_version": "pylinac-3.47.0-rt-connect-1.1",
        "pylinac_version": installed_pylinac_version(),
        "wheel_sha256": PYLINAC_WHEEL_SHA256,
        "package_fingerprint": package_fingerprint(),
        "total_bindings": len(capabilities),
        "runtime_available": sum(item.runtime_available for item in capabilities),
        "unresolved_catalog_keys": list(unresolved),
        "capabilities": capability_summaries,
    }
