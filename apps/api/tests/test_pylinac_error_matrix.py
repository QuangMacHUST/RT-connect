from __future__ import annotations

from pathlib import Path

import pytest

from rt_connect_api.services.pylinac_adapter import (
    PylinacAdapterError,
    execute_pylinac,
)


@pytest.mark.parametrize(
    "catalog_key",
    [
        "CATPHAN_503",
        "CATPHAN_504",
        "CATPHAN_600",
        "CATPHAN_604",
        "CATPHAN_700",
        "ACR_CT_464",
        "ACR_MRI_LARGE",
        "ACR_MRI_MEDIUM",
        "CHEESE_TOMO",
        "CHEESE_CIRS_062M",
        "GE_HELIOS",
        "QUART_DVT",
        "QUART_HYPERSIGHT",
    ],
)
def test_zip_phantom_families_reject_non_zip_before_engine(
    tmp_path: Path, catalog_key: str
) -> None:
    source = tmp_path / f"{catalog_key.lower()}.dcm"
    source.write_bytes(b"not-a-zip")

    with pytest.raises(PylinacAdapterError) as error:
        execute_pylinac(catalog_key, source, {})

    assert error.value.code == "PYLINAC_INPUT_FORMAT_INVALID"


@pytest.mark.parametrize(
    ("catalog_key", "parameters"),
    [
        ("ACR_MRI_LARGE", {"low_contrast_method": ""}),
        ("CHEESE_TOMO", {"roi_config": {"1": {"density": True}}}),
        ("QUART_DVT", {"roll_slice_offset": "not-a-number"}),
    ],
)
def test_phantom_families_reject_invalid_special_parameters(
    tmp_path: Path, catalog_key: str, parameters: dict[str, object]
) -> None:
    source = tmp_path / f"{catalog_key.lower()}.zip"
    source.write_bytes(b"zip-placeholder")

    with pytest.raises(PylinacAdapterError) as error:
        execute_pylinac(catalog_key, source, parameters)

    assert error.value.code == "PYLINAC_PARAMETER_INVALID"
