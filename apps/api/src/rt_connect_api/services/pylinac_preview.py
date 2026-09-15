"""Render a safe, authenticated image preview for Pylinac input artifacts."""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
from pylinac.core.image import load  # type: ignore[import-untyped]


class PylinacPreviewError(ValueError):
    """Raised when an input cannot be rendered as a 2D preview."""


_IMAGE_SUFFIXES = {".bmp", ".dcm", ".dicom", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}
MAX_PREVIEW_IMAGES = 32


def _safe_zip_member(info: zipfile.ZipInfo) -> bool:
    """Reject directories and path traversal before reading a ZIP member."""

    if info.is_dir():
        return False
    member = Path(info.filename)
    return not member.is_absolute() and ".." not in member.parts


def _zip_candidates(source: Path) -> list[zipfile.ZipInfo]:
    try:
        archive = zipfile.ZipFile(source)
    except (OSError, zipfile.BadZipFile) as exc:
        raise PylinacPreviewError("Bộ tệp ZIP không thể mở để xem trước.") from exc
    with archive:
        members = [info for info in archive.infolist() if _safe_zip_member(info)]
    preferred = [
        info for info in members if Path(info.filename).suffix.lower() in _IMAGE_SUFFIXES
    ]
    return preferred or members


def _load_source(source: Path, image_index: int, max_bytes: int) -> object:
    if source.suffix.lower() != ".zip":
        return load(source)

    candidates = _zip_candidates(source)
    if not candidates:
        raise PylinacPreviewError("Bộ tệp ZIP không có ảnh để xem trước.")
    if image_index >= len(candidates):
        raise PylinacPreviewError("Số thứ tự ảnh xem trước không tồn tại trong bộ tệp.")
    member = candidates[image_index]
    if member.file_size > max_bytes:
        raise PylinacPreviewError("Ảnh xem trước vượt quá giới hạn an toàn.")
    file_descriptor, extracted_name = tempfile.mkstemp(
        suffix=Path(member.filename).suffix or ".dcm"
    )
    os.close(file_descriptor)
    extracted = Path(extracted_name)
    try:
        with (
            zipfile.ZipFile(source) as archive,
            extracted.open("wb") as target,
            archive.open(member) as payload,
        ):
            copied = 0
            while chunk := payload.read(1024 * 1024):
                copied += len(chunk)
                if copied > max_bytes:
                    raise PylinacPreviewError("Ảnh xem trước vượt quá giới hạn an toàn.")
                target.write(chunk)
        return load(extracted)
    finally:
        extracted.unlink(missing_ok=True)


def preview_image_count(source: Path) -> int:
    """Return the bounded number of selectable images or frames in a source."""

    if source.suffix.lower() == ".zip":
        return min(len(_zip_candidates(source)), MAX_PREVIEW_IMAGES)
    try:
        image = load(source)
        array = np.asarray(getattr(image, "array", image))
    except Exception as exc:  # Pylinac and pydicom expose several exception types.
        raise PylinacPreviewError(
            "Không thể đọc số ảnh trong tệp đầu vào. Hãy kiểm tra đúng định dạng."
        ) from exc
    if array.ndim == 2:
        return 1
    if array.ndim == 3 and array.shape[0] > 0:
        return min(int(array.shape[0]), MAX_PREVIEW_IMAGES)
    raise PylinacPreviewError("Tệp không chứa chuỗi ảnh hai chiều để xem trước.")


def _two_dimensional_array(image: object, image_index: int) -> np.ndarray:
    array = np.asarray(getattr(image, "array", image))
    if array.ndim == 2:
        if image_index:
            raise PylinacPreviewError("Ảnh này chỉ có một lát để xem trước.")
        return array
    if array.ndim == 3:
        if image_index >= array.shape[0]:
            raise PylinacPreviewError("Số thứ tự lát xem trước không tồn tại.")
        return np.asarray(array[image_index])
    raise PylinacPreviewError("Tệp không chứa ảnh hai chiều để xem trước.")


def render_preview(
    source: Path,
    *,
    image_index: int = 0,
    max_bytes: int = 104_857_600,
) -> bytes:
    """Render one DICOM/image/ZIP member without exposing source metadata."""

    try:
        image = _load_source(source, image_index, max_bytes)
        frame_index = image_index if source.suffix.lower() != ".zip" else 0
        array = _two_dimensional_array(image, frame_index)
    except PylinacPreviewError:
        raise
    except Exception as exc:  # Pylinac and pydicom expose several exception types.
        raise PylinacPreviewError(
            "Không thể tạo ảnh xem trước từ tệp đầu vào. Hãy kiểm tra đúng định dạng."
        ) from exc

    values = np.asarray(array, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise PylinacPreviewError("Ảnh đầu vào không có giá trị điểm ảnh hợp lệ.")
    low, high = np.percentile(finite, [1, 99])
    if not np.isfinite(low) or not np.isfinite(high) or low == high:
        low, high = float(np.min(finite)), float(np.max(finite))
    if low == high:
        high = low + 1

    figure, axis = plt.subplots(figsize=(8, 8), dpi=120)
    try:
        axis.imshow(values, cmap="gray", vmin=low, vmax=high, origin="upper")
        axis.set_axis_off()
        figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        output = BytesIO()
        figure.savefig(output, format="png", dpi=120, pad_inches=0)
        return output.getvalue()
    finally:
        plt.close(figure)
