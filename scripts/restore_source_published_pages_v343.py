#!/usr/bin/env python3
"""Safety wrapper for source-publication parity v342.

The v342 policy remains authoritative. This wrapper hardens two implementation
edges before invoking it:

1. A missing nested route inside an existing public section is merged into that
   route only; the existing top-level production section is never deleted.
2. Robots directives are parsed regardless of HTML attribute order.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import restore_source_published_pages_v342 as core

META_RE = re.compile(r"<meta\b[^>]*>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*([\"'])(.*?)\2", re.I | re.S)


def hardened_is_blocked_html(path: Path) -> tuple[bool, str | None]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    for marker in core.BLOCK_MARKERS:
        if marker.lower() in lowered:
            return True, marker
    for tag in META_RE.findall(text):
        attrs = {name.lower(): value.strip() for name, _quote, value in ATTR_RE.findall(tag)}
        if attrs.get("name", "").lower() == "robots" and "noindex" in attrs.get("content", "").lower():
            return True, "noindex"
    return False, None


def incremental_copy_public_surface(source_root: Path, site_root: Path, route: str) -> list[str]:
    src = core.source_path(source_root, route)
    if not src.is_file():
        return []

    parts = Path(route.rstrip("/")).parts
    if route.endswith("/") and parts:
        top = parts[0]
        src_top = source_root / top
        dst_top = site_root / top

        # A wholly absent section needs its shared assets, data and nested pages.
        if src_top.is_dir() and not dst_top.exists():
            shutil.copytree(src_top, dst_top)
            return [top + "/"]

        # For an existing section, merge only the missing route subtree. Never
        # remove or replace the production section that already passed its gates.
        src_route_dir = source_root / route.rstrip("/")
        dst_route_dir = site_root / route.rstrip("/")
        if src_route_dir.is_dir():
            dst_route_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_route_dir, dst_route_dir, dirs_exist_ok=True)
            return [route]

    dst = core.output_path(site_root, route)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return [route]


def main() -> int:
    core.is_blocked_html = hardened_is_blocked_html
    core.copy_public_surface = incremental_copy_public_surface
    return core.main()


if __name__ == "__main__":
    sys.exit(main())
