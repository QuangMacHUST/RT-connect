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
from typing import Literal

RENDERER_VERSION = "report-renderer-0.1"
ExportFormat = Literal["JSON", "CSV", "PDF", "PNG"]
SUPPORTED_EXPORT_FORMATS: frozenset[str] = frozenset({"JSON", "CSV", "PDF", "PNG"})


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
    for key in (
        "report_key",
        "revision_number",
        "title",
        "source_type",
        "source_id",
        "content_sha256",
        "renderer_version",
    ):
        writer.writerow(("report", key, _csv_value(snapshot.get(key))))
    for block in _blocks(snapshot):
        if not _is_visible(block):
            continue
        block_id = _string(block.get("stable_block_id"), "")
        block_type = _string(block.get("block_type"), "")
        label = _csv_value(block.get("label"))
        config = _csv_value(block.get("config", {}))
        binding = _csv_value(block.get("source_binding", {}))
        writer.writerow(("block", f"{block_id}:type", _csv_value(block_type)))
        writer.writerow(("block", f"{block_id}:label", label))
        writer.writerow(("block", f"{block_id}:config", config))
        writer.writerow(("block", f"{block_id}:source_binding", binding))
    return stream.getvalue().encode("utf-8")


def _render_pdf(
    snapshot: Mapping[str, object],
) -> tuple[bytes, str, str, list[str]]:
    lines = [
        "RT-CONNECT REPORT",
        _string(snapshot.get("title"), "Untitled report"),
        f"Source: {_string(snapshot.get('source_type'), 'CUSTOM')}",
        f"Revision: {_string(snapshot.get('revision_number'), '—')}",
        f"Content SHA-256: {_string(snapshot.get('content_sha256'), '—')}",
    ]
    visible_blocks = [block for block in _blocks(snapshot) if _is_visible(block)]
    lines.append(f"Visible blocks: {len(visible_blocks)}")
    for block in visible_blocks[:24]:
        lines.append(
            f"• {_string(block.get('label'), 'Unnamed')} "
            f"[{_string(block.get('block_type'), 'BLOCK')}]"
        )
    warnings: list[str] = []
    if any(any(ord(character) > 255 for character in line) for line in lines):
        warnings.append("PDF fallback font cannot represent all Unicode characters.")
    payload = _pdf_document(lines)
    return payload, "application/pdf", "pdf", warnings


def _pdf_document(lines: Sequence[str]) -> bytes:
    """Build a small valid PDF without executing templates or external tools."""

    stream_lines = ["BT", "/F1 12 Tf", "50 760 Td"]
    for index, line in enumerate(lines):
        if index:
            stream_lines.append("0 -18 Td")
        safe = line.encode("latin-1", errors="replace").decode("latin-1")
        escaped = safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_lines.append(f"({escaped}) Tj")
    stream_lines.append("ET")
    content = "\n".join(stream_lines).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n"
        + content
        + b"\nendstream",
    ]
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

    return b"\x89PNG\r\n\x1a\n" + chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ) + chunk(b"IDAT", zlib.compress(bytes(raw), level=9)) + chunk(b"IEND", b"")


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
