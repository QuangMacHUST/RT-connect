"""Deterministic renderers for immutable RT-CONNECT report snapshots.

The first renderer deliberately has no network or template execution surface.  A
report is rendered from the already persisted snapshot, not by reading the live
Gamma/Machine QA rows again.  This makes preview/export reproducible and keeps
custom report content from becoming executable HTML or a server-side template.
"""

from __future__ import annotations

import csv
import io
import json
import struct
import zlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from fontTools.ttLib import TTFont  # type: ignore[import-untyped]

RENDERER_VERSION = "report-renderer-0.2"
ExportFormat = Literal["JSON", "CSV", "PDF", "PNG"]
SUPPORTED_EXPORT_FORMATS: frozenset[str] = frozenset({"JSON", "CSV", "PDF", "PNG"})
_PDF_FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "DejaVuSans.ttf"
_PDF_FONT_NAME = "RTConnectDejaVuSans"


class ReportRenderError(ValueError):
    """Raised when a persisted report snapshot cannot be rendered safely."""


def canonical_json(value: object) -> bytes:
    """Return stable UTF-8 JSON suitable for hashing and JSON export."""

    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ReportRenderError("Report snapshot contains a non-JSON value") from exc
    return encoded.encode("utf-8")


def render_report(
    snapshot: Mapping[str, object], export_format: ExportFormat
) -> tuple[bytes, str, str, list[str]]:
    """Render one immutable snapshot as bytes, media type, extension and warnings."""

    if export_format not in SUPPORTED_EXPORT_FORMATS:
        raise ReportRenderError(f"Unsupported report export format: {export_format}")
    if export_format == "JSON":
        return canonical_json(snapshot) + b"\n", "application/json", "json", []
    if export_format == "CSV":
        return _render_csv(snapshot), "text/csv; charset=utf-8", "csv", []
    if export_format == "PDF":
        return _render_pdf(snapshot)
    return _render_png(snapshot), "image/png", "png", []


def _render_csv(snapshot: Mapping[str, object]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n")
    writer.writerow(("section", "key", "value"))
    writer.writerow(("báo cáo", "tiêu đề", _csv_value(snapshot.get("title"))))
    writer.writerow(("báo cáo", "loại báo cáo", _source_label(snapshot.get("source_type"))))
    for block in _blocks(snapshot):
        if not _is_visible(block):
            continue
        label = _csv_value(block.get("label"))
        content = " ".join(_block_content(block, _source_payload(snapshot)))
        writer.writerow(("phần báo cáo", label, _csv_value(content)))
    return stream.getvalue().encode("utf-8")


def _render_pdf(
    snapshot: Mapping[str, object],
) -> tuple[bytes, str, str, list[str]]:
    lines = [
        "BÁO CÁO KIỂM TRA CHẤT LƯỢNG",
        _string(snapshot.get("title"), "Báo cáo chưa đặt tên"),
        f"Loại báo cáo: {_source_label(snapshot.get('source_type'))}",
    ]
    payload = _source_payload(snapshot)
    source_name = _source_display_name(payload)
    if source_name:
        lines.append(f"Bài kiểm tra: {source_name}")
    source_status = _status_label(_first_value(payload, "overall_status", "status"))
    if source_status:
        lines.append(f"Đánh giá: {source_status}")
    visible_blocks = [block for block in _blocks(snapshot) if _is_visible(block)]
    if not visible_blocks:
        lines.append("Chưa chọn nội dung hiển thị.")
    for block in visible_blocks[:24]:
        lines.append("")
        lines.append(f"• {_string(block.get('label'), 'Phần báo cáo')}")
        content = _block_content(block, payload)
        lines.extend(content[:12] or ["Nội dung sẽ được lấy từ kết quả đã chọn."])
    pdf_payload = _pdf_document(lines)
    return pdf_payload, "application/pdf", "pdf", []


def _pdf_document(lines: Sequence[str]) -> bytes:
    """Build a deterministic multi-page PDF with one shared Unicode font."""

    normalized_lines = tuple(_normalize_pdf_line(line) for line in lines) or ("",)
    font_data, cmap, metrics = _load_pdf_font()
    codepoints = sorted({ord(character) for line in normalized_lines for character in line})
    page_lines = [
        normalized_lines[index : index + 39] for index in range(0, len(normalized_lines), 39)
    ]
    page_count = len(page_lines)
    shared_start = 3 + page_count * 2
    type0_id = shared_start
    cmap_id = shared_start + 1
    cid_font_id = shared_start + 2
    descriptor_id = shared_start + 3
    cidmap_id = shared_start + 4
    fontfile_id = shared_start + 5

    cid_to_gid = bytearray(65536 * 2)
    width_entries: list[str] = []
    for codepoint in codepoints:
        glyph_name = cmap.get(codepoint, ".notdef")
        glyph_id = metrics["glyph_ids"].get(glyph_name, 0)
        struct.pack_into(">H", cid_to_gid, codepoint * 2, glyph_id)
        advance_width = metrics["widths"].get(glyph_name, metrics["default_width"])
        width_entries.append(
            f"{codepoint} [{round(advance_width * 1000 / metrics['units_per_em'])}]"
        )

    descriptor_bbox = " ".join(str(value) for value in metrics["font_bbox"])
    descriptor = (
        f"<< /Type /FontDescriptor /FontName /{_PDF_FONT_NAME} /Flags 32 "
        f"/FontBBox [{descriptor_bbox}] /ItalicAngle 0 "
        f"/Ascent {metrics['ascent']} /Descent {metrics['descent']} "
        f"/CapHeight {metrics['cap_height']} /StemV 80 /FontFile2 {fontfile_id} 0 R >>"
    ).encode("ascii")
    cid_font = (
        f"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /{_PDF_FONT_NAME} "
        f"/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
        f"/FontDescriptor {descriptor_id} 0 R /DW {metrics['default_width']} "
        f"/W [{' '.join(width_entries)}] /CIDToGIDMap {cidmap_id} 0 R >>"
    ).encode("ascii")
    type0_font = (
        f"<< /Type /Font /Subtype /Type0 /BaseFont /{_PDF_FONT_NAME} "
        f"/Encoding /Identity-H /DescendantFonts [{cid_font_id} 0 R] "
        f"/ToUnicode {cmap_id} 0 R >>"
    ).encode("ascii")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",
    ]
    page_ids: list[int] = []
    for index, chunk in enumerate(page_lines):
        page_id = 3 + index * 2
        content_id = page_id + 1
        page_ids.append(page_id)
        page_content = _pdf_page_content(chunk)
        objects.extend(
            [
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Resources << /ProcSet [/PDF /Text] /Font << /F1 {type0_id} 0 R >> >> "
                    f"/Contents {content_id} 0 R >>"
                ).encode("ascii"),
                _pdf_stream_object(page_content),
            ]
        )
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii")
    objects.extend(
        [
            type0_font,
            _pdf_stream_object(_pdf_to_unicode_cmap(codepoints)),
            cid_font,
            descriptor,
            _pdf_stream_object(bytes(cid_to_gid)),
            _pdf_stream_object(font_data, extra=f"/Length1 {len(font_data)}".encode("ascii")),
        ]
    )
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode("ascii"))
        document.extend(obj)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(document)


def _pdf_page_content(lines: Sequence[str]) -> bytes:
    stream_lines = ["BT", "/F1 12 Tf", "50 760 Td"]
    for index, line in enumerate(lines):
        if index:
            stream_lines.append("0 -18 Td")
        stream_lines.append(f"<{line.encode('utf-16-be').hex().upper()}> Tj")
    stream_lines.append("ET")
    return "\n".join(stream_lines).encode("ascii")


def _normalize_pdf_line(line: str) -> str:
    """Keep text in the BMP, which is the CID range used by Identity-H here."""

    return "".join(character if ord(character) <= 0xFFFF else "\ufffd" for character in line)


def _load_pdf_font() -> tuple[bytes, dict[int, str], dict[str, Any]]:
    if not _PDF_FONT_PATH.is_file():
        raise ReportRenderError(f"PDF Unicode font is unavailable: {_PDF_FONT_PATH.name}")
    font_data = _PDF_FONT_PATH.read_bytes()
    font = TTFont(io.BytesIO(font_data), recalcBBoxes=False, recalcTimestamp=False)
    try:
        cmap = font.getBestCmap() or {}
        head = font["head"]
        hhea = font["hhea"]
        os2 = font["OS/2"]
        units_per_em = int(head.unitsPerEm)
        scale = 1000 / units_per_em
        widths = {name: int(value[0]) for name, value in font["hmtx"].metrics.items()}
        glyph_ids = {name: int(font.getGlyphID(name)) for name in widths}
        font_bbox = tuple(
            round(value * scale) for value in (head.xMin, head.yMin, head.xMax, head.yMax)
        )
        ascent = round(max(int(hhea.ascent), int(os2.sTypoAscender)) * scale)
        descent = round(min(int(hhea.descent), int(os2.sTypoDescender)) * scale)
        cap_height = round(int(getattr(os2, "sCapHeight", os2.sTypoAscender)) * scale)
        default_width = round(widths.get(".notdef", units_per_em) * scale)
        metrics: dict[str, Any] = {
            "units_per_em": units_per_em,
            "widths": widths,
            "glyph_ids": glyph_ids,
            "default_width": default_width,
            "font_bbox": font_bbox,
            "ascent": ascent,
            "descent": descent,
            "cap_height": cap_height,
        }
        return font_data, cmap, metrics
    finally:
        font.close()


def _pdf_stream_object(data: bytes, *, extra: bytes = b"") -> bytes:
    compressed = zlib.compress(data, level=9)
    prefix = b"<< " + extra + b" /Length " + str(len(compressed)).encode("ascii")
    return prefix + b" /Filter /FlateDecode >>\nstream\n" + compressed + b"\nendstream"


def _pdf_to_unicode_cmap(codepoints: Sequence[int]) -> bytes:
    lines = [
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin",
        "begincmap",
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
        "/CMapName /Adobe-Identity-UCS def",
        "/CMapType 2 def",
        "1 begincodespacerange",
        "<0000><FFFF>",
        "endcodespacerange",
    ]
    mappings = [f"<{codepoint:04X}> <{codepoint:04X}>" for codepoint in codepoints]
    for start in range(0, len(mappings), 100):
        chunk = mappings[start : start + 100]
        lines.append(f"{len(chunk)} beginbfchar")
        lines.extend(chunk)
        lines.append("endbfchar")
    lines.extend(
        [
            "endcmap",
            "CMapName currentdict /CMap defineresource pop",
            "end",
            "end",
        ]
    )
    return "\n".join(lines).encode("ascii")


def _render_png(snapshot: Mapping[str, object]) -> bytes:
    """Build a deterministic overview PNG for previews and lightweight exports."""

    width, height = 720, 400
    pixels = bytearray(width * height * 3)

    def fill(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
        for y in range(max(0, y0), min(height, y1)):
            start = (y * width + max(0, x0)) * 3
            end = (y * width + min(width, x1)) * 3
            row = bytes(color) * max(0, min(width, x1) - max(0, x0))
            pixels[start:end] = row

    fill(0, 0, width, height, (245, 248, 251))
    fill(0, 0, width, 72, (16, 48, 79))
    fill(32, 104, width - 32, 170, (255, 255, 255))
    fill(32, 194, width - 32, 360, (255, 255, 255))
    blocks = [block for block in _blocks(snapshot) if _is_visible(block)]
    bar_count = min(len(blocks), 12)
    for index in range(bar_count):
        bar_height = 12 + ((index * 17) % 88)
        x0 = 64 + index * 50
        fill(x0, 330 - bar_height, x0 + 28, 330, (23, 145, 160))
    return _png_rgb(width, height, bytes(pixels))


def _source_label(value: object) -> str:
    labels = {
        "CUSTOM": "Báo cáo tùy chỉnh",
        "QA_CASE": "Bài kiểm tra chất lượng máy",
        "MACHINE_QA": "Kết quả kiểm tra máy",
        "GAMMA": "Phân tích PSQA",
        "DVH": "Phân tích liều và thể tích",
        "BIOLOGICAL": "Công cụ sinh học",
    }
    return labels.get(_string(value, "CUSTOM"), "Báo cáo kiểm tra chất lượng")


def _source_payload(snapshot: Mapping[str, object]) -> Mapping[str, object]:
    source_snapshot = snapshot.get("source_snapshot")
    if not isinstance(source_snapshot, Mapping):
        return {}
    payload = source_snapshot.get("payload")
    return payload if isinstance(payload, Mapping) else {}


def _source_display_name(payload: Mapping[str, object]) -> str | None:
    for key in ("title", "name", "qa_type", "scenario_type"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_value(payload: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    result = payload.get("result_snapshot")
    if isinstance(result, Mapping):
        for key in keys:
            value = result.get(key)
            if value not in (None, ""):
                return value
    return None


def _status_label(value: object) -> str | None:
    if value in (None, ""):
        return None
    labels = {
        "PASS": "Đạt",
        "PASSED": "Đạt",
        "WARNING": "Cảnh báo",
        "FAIL": "Không đạt",
        "FAILED": "Không đạt",
        "PENDING": "Đang chờ",
        "QUEUED": "Đang chờ",
        "RUNNING": "Đang chạy",
        "PROCESSING": "Đang xử lý",
        "COMPLETED": "Đã hoàn tất",
        "CANCELLED": "Đã hủy",
        "CANCELED": "Đã hủy",
    }
    return labels.get(str(value).upper(), "Đã ghi nhận")


def _block_content(block: Mapping[str, object], payload: Mapping[str, object]) -> list[str]:
    config = block.get("config")
    if isinstance(config, Mapping):
        content = config.get("content")
        if isinstance(content, str) and content.strip():
            return [line.strip() for line in content.splitlines() if line.strip()]

    block_type = _string(block.get("block_type"), "")
    if block_type == "METADATA":
        performed_at = payload.get("performed_at") or payload.get("created_at")
        if isinstance(performed_at, str) and performed_at:
            return [f"Thời điểm ghi nhận: {performed_at[:10]}"]
    if block_type == "METRICS":
        return _metric_lines(payload)
    if block_type == "WARNING":
        warnings = payload.get("warning_snapshot") or payload.get("error_snapshot")
        if isinstance(warnings, list) and warnings:
            return [f"Có {len(warnings)} cảnh báo hoặc nội dung cần xem lại."]
        return ["Không ghi nhận cảnh báo."]
    if block_type == "PROVENANCE":
        return ["Kết quả được lấy từ bản chụp đã lưu cùng báo cáo."]
    if block_type in {"GAMMA_MAP", "DOSE_PROFILE", "DVH", "IMAGE"}:
        return ["Hình phân tích sẽ được đính kèm khi kết quả có dữ liệu hình ảnh."]
    return []


def _metric_lines(payload: Mapping[str, object]) -> list[str]:
    result = payload.get("result_snapshot")
    if not isinstance(result, Mapping):
        result = payload
    allowed = (
        ("pass_rate", "Tỷ lệ đạt"),
        ("coverage_percent", "Độ bao phủ"),
        ("max_gamma", "Gamma lớn nhất"),
        ("mean_gamma", "Gamma trung bình"),
        ("dose_difference_percent", "Chênh lệch liều"),
        ("dta_mm", "Khoảng cách DTA"),
        ("roi_number", "Vùng quan tâm"),
    )
    lines: list[str] = []
    for key, label in allowed:
        value = result.get(key)
        if value not in (None, ""):
            lines.append(f"{label}: {_string(value, '—')}")
    measurements = payload.get("measurements")
    if isinstance(measurements, list):
        for index, measurement in enumerate(measurements[:12], start=1):
            if not isinstance(measurement, Mapping):
                continue
            value = measurement.get("value")
            unit = measurement.get("unit")
            if value not in (None, ""):
                suffix = f" {unit}" if isinstance(unit, str) and unit else ""
                lines.append(f"Chỉ số {index}: {_string(value, '—')}{suffix}")
    return lines


def _png_rgb(width: int, height: int, pixels: bytes) -> bytes:
    raw = bytearray()
    row_size = width * 3
    for row in range(height):
        raw.append(0)
        raw.extend(pixels[row * row_size : (row + 1) * row_size])

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), level=9))
        + chunk(b"IEND", b"")
    )


def _blocks(snapshot: Mapping[str, object]) -> list[Mapping[str, object]]:
    raw = snapshot.get("blocks")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def _is_visible(block: Mapping[str, object]) -> bool:
    return block.get("is_visible", True) is not False


def _string(value: object, fallback: str) -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        return value
    return str(value)


def _csv_value(value: object) -> str:
    if isinstance(value, (dict, list, tuple)):
        result = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        result = _string(value, "")
    if result.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + result
    return result
