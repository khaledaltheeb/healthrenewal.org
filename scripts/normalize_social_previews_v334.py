#!/usr/bin/env python3
"""Normalize social-preview images in a generated static-site tree.

SVG remains suitable for on-page illustrations, but social preview consumers are
more consistently compatible with a 1200x630 raster image. This post-build step
creates a deterministic PNG using only Python's standard library and replaces
only OpenGraph/Twitter image meta tags that currently point to SVG files.
"""
from __future__ import annotations

import argparse
import binascii
import json
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from urllib.parse import urljoin, urlparse

VERSION = 334
WIDTH = 1200
HEIGHT = 630
ASSET_PATH = "assets/social-card-v334.png"
META_TAG_RE = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
ATTR_RE = re.compile(
    r"(?P<name>[A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    re.DOTALL,
)

FONT: dict[str, tuple[str, ...]] = {
    " ": ("00000",) * 7,
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
}


@dataclass(slots=True)
class Report:
    version: int
    generated_at: str
    site_root: str
    base_url: str
    asset: str
    html_files_scanned: int
    html_files_changed: int
    meta_tags_changed: int
    status: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2) + "\n"


def normalize_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {value!r}")
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if not path.endswith("/"):
        path += "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def is_svg_url(value: str) -> bool:
    return urlparse(value.strip()).path.lower().endswith(".svg")


def rewrite_meta_tag(tag: str, replacement_url: str) -> tuple[str, bool]:
    attrs = {match.group("name").lower(): match for match in ATTR_RE.finditer(tag)}
    marker = attrs.get("property") or attrs.get("name")
    content = attrs.get("content")
    if marker is None or content is None:
        return tag, False
    if marker.group("value").strip().lower() not in {
        "og:image",
        "og:image:url",
        "twitter:image",
        "twitter:image:src",
    }:
        return tag, False
    if not is_svg_url(content.group("value")):
        return tag, False
    start, end = content.span("value")
    return tag[:start] + replacement_url + tag[end:], True


def _set_pixel(canvas: bytearray, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        index = (y * WIDTH + x) * 3
        canvas[index : index + 3] = bytes(color)


def _fill_rect(canvas: bytearray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    x0, x1 = max(0, x0), min(WIDTH, x1)
    y0, y1 = max(0, y0), min(HEIGHT, y1)
    row = bytes(color) * max(0, x1 - x0)
    for y in range(y0, y1):
        start = (y * WIDTH + x0) * 3
        canvas[start : start + len(row)] = row


def _line(canvas: bytearray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], width: int = 1) -> None:
    dx, sx = abs(x1 - x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1 - y0), 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        radius = max(0, width // 2)
        _fill_rect(canvas, x0 - radius, y0 - radius, x0 + radius + 1, y0 + radius + 1, color)
        if x0 == x1 and y0 == y1:
            return
        twice = 2 * error
        if twice >= dy:
            error += dy
            x0 += sx
        if twice <= dx:
            error += dx
            y0 += sy


def _circle(canvas: bytearray, cx: int, cy: int, radius: int, color: tuple[int, int, int], *, filled: bool = True, thickness: int = 2) -> None:
    outer = radius * radius
    inner = max(0, radius - thickness) ** 2
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            distance = (x - cx) ** 2 + (y - cy) ** 2
            if distance <= outer and (filled or distance >= inner):
                _set_pixel(canvas, x, y, color)


def _draw_text(canvas: bytearray, x: int, y: int, text: str, scale: int, color: tuple[int, int, int]) -> None:
    cursor = x
    for character in text.upper():
        glyph = FONT.get(character, FONT[" "])
        for row_index, row in enumerate(glyph):
            for column_index, bit in enumerate(row):
                if bit == "1":
                    _fill_rect(canvas, cursor + column_index * scale, y + row_index * scale, cursor + (column_index + 1) * scale, y + (row_index + 1) * scale, color)
        cursor += 6 * scale


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", binascii.crc32(chunk_type + data) & 0xFFFFFFFF)


def build_social_card_png() -> bytes:
    canvas = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        vertical = y / max(1, HEIGHT - 1)
        for x in range(WIDTH):
            horizontal = x / max(1, WIDTH - 1)
            color = (int(7 + 8 * vertical), int(22 + 28 * horizontal + 12 * vertical), int(39 + 35 * horizontal + 18 * vertical))
            _set_pixel(canvas, x, y, color)

    gold = (226, 184, 91)
    teal = (95, 200, 190)
    pale = (237, 242, 239)
    muted = (183, 207, 215)
    panel = (7, 22, 37)
    _fill_rect(canvas, 48, 48, WIDTH - 48, HEIGHT - 48, panel)
    for offset in range(4):
        _line(canvas, 48 + offset, 48 + offset, WIDTH - 49 - offset, 48 + offset, gold)
        _line(canvas, 48 + offset, HEIGHT - 49 - offset, WIDTH - 49 - offset, HEIGHT - 49 - offset, gold)
        _line(canvas, 48 + offset, 48 + offset, 48 + offset, HEIGHT - 49 - offset, gold)
        _line(canvas, WIDTH - 49 - offset, 48 + offset, WIDTH - 49 - offset, HEIGHT - 49 - offset, gold)

    cx, cy = 190, 315
    _circle(canvas, cx, cy, 92, gold, filled=False, thickness=5)
    nodes = [(cx - 48, cy - 18), (cx - 18, cy - 58), (cx + 20, cy - 42), (cx + 50, cy - 4), (cx + 22, cy + 35), (cx - 28, cy + 48), (cx - 58, cy + 18), (cx, cy)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 0), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7)]
    for first, second in edges:
        _line(canvas, *nodes[first], *nodes[second], teal, width=4)
    for x, y in nodes:
        _circle(canvas, x, y, 8, gold)

    _draw_text(canvas, 440, 170, "MENTAL HEALTH", 8, pale)
    _draw_text(canvas, 440, 270, "SPECIAL NEEDS PLATFORM", 5, gold)
    _fill_rect(canvas, 440, 370, 1100, 374, teal)
    _draw_text(canvas, 440, 420, "EVIDENCE  CARE  KNOWLEDGE", 3, muted)
    _draw_text(canvas, 820, 525, "PTERMINOLOGY", 4, gold)

    scanlines = bytearray()
    stride = WIDTH * 3
    for y in range(HEIGHT):
        scanlines.append(0)
        start = y * stride
        scanlines.extend(canvas[start : start + stride])
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header) + _png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9)) + _png_chunk(b"IEND", b"")


def normalize_tree(site_root: Path, base_url: str) -> Report:
    root = site_root.resolve()
    if not root.is_dir():
        raise ValueError(f"Site root is not a directory: {root}")
    base_url = normalize_base_url(base_url)
    asset = root / ASSET_PATH
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(build_social_card_png())
    replacement_url = urljoin(base_url, ASSET_PATH)

    scanned = changed_files = changed_tags = 0
    for path in sorted(root.rglob("*.html")):
        if any(part.startswith(".") or part in {"node_modules", "scripts", "tests"} for part in path.relative_to(root).parts[:-1]):
            continue
        scanned += 1
        source = path.read_text(encoding="utf-8")
        local_changes = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal local_changes
            updated, changed = rewrite_meta_tag(match.group(0), replacement_url)
            if changed:
                local_changes += 1
            return updated

        output = META_TAG_RE.sub(replace, source)
        if local_changes:
            path.write_text(output, encoding="utf-8")
            changed_files += 1
            changed_tags += local_changes

    report = Report(version=VERSION, generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(), site_root=str(root), base_url=base_url, asset=ASSET_PATH, html_files_scanned=scanned, html_files_changed=changed_files, meta_tags_changed=changed_tags, status="passed")
    report_path = root / "api" / "social-preview-normalization-v334.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report.to_json(), encoding="utf-8")
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_root", nargs="?", default="_site")
    parser.add_argument("--base-url", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = normalize_tree(Path(args.site_root), args.base_url)
    print(report.to_json(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
