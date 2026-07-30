#!/usr/bin/env python3
"""Safety wrapper for source-publication parity v342.

The v342 policy remains authoritative. This wrapper hardens three implementation
edges before invoking it:

1. A missing nested route inside an existing public section is merged into that
   route only; the existing top-level production section is never deleted.
2. Shared assets may be copied from an absent source section, but HTML is copied
   only for routes explicitly declared by a source sitemap.
3. Robots directives are parsed regardless of HTML attribute order.
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


def ignore_html(_directory: str, names: list[str]) -> list[str]:
    """Keep shared assets while excluding undeclared HTML from bulk copies."""
    return [name for name in names if name.lower().endswith((".html", ".htm"))]


def copy_assets_then_exact_route(src_dir: Path, dst_dir: Path, src_page: Path, dst_page: Path) -> None:
    dst_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True, ignore=ignore_html)
    dst_page.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_page, dst_page)


def incremental_copy_public_surface(source_root: Path, site_root: Path, route: str) -> list[str]:
    src = core.source_path(source_root, route)
    if not src.is_file():
        return []

    parts = Path(route.rstrip("/")).parts
    if route.endswith("/") and parts:
        top = parts[0]
        src_top = source_root / top
        dst_top = site_root / top
        dst = core.output_path(site_root, route)

        # For a wholly absent section, copy all non-HTML assets and then only the
        # current sitemap-declared page. Subsequent declared routes add their own
        # exact HTML files without exposing drafts or unlisted documents.
        if src_top.is_dir() and not dst_top.exists():
            copy_assets_then_exact_route(src_top, dst_top, src, dst)
            return [top + "/"]

        # For an existing section, merge assets from only the missing route
        # subtree and copy that route's exact declared HTML page.
        src_route_dir = source_root / route.rstrip("/")
        dst_route_dir = site_root / route.rstrip("/")
        if src_route_dir.is_dir():
            copy_assets_then_exact_route(src_route_dir, dst_route_dir, src, dst)
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
