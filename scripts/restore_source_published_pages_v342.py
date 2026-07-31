#!/usr/bin/env python3
"""Restore source-backed public routes omitted from a validated production artifact.

Only URLs explicitly declared in root-level source sitemap files are eligible. HTML
marked noindex, draft-unpublished, or needs-specialist-review is never restored.
The script preserves byte-stamped critical production files and writes a machine-
readable parity report.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_PATH = "/"
BASE_URL = "https://healthrenewal.org/"
CRITICAL_FILES = ("index.html", "sitemap.xml", "manifest.webmanifest", "sw.js")
BLOCK_MARKERS = (
    "draft-unpublished",
    "needs-specialist-review",
    "pt-publication-status=draft",
    'data-publication-status="draft"',
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
ROBOTS_RE = re.compile(
    r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\']([^"\']*)["\']',
    re.I,
)
END_MAIN_RE = re.compile(r"</main\s*>", re.I)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def route_for_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc != "khaledaltheeb.github.io":
        return None
    path = unquote(parsed.path)
    if not path.startswith(BASE_PATH):
        return None
    route = path[len(BASE_PATH) :].lstrip("/")
    return route


def output_path(root: Path, route: str) -> Path:
    if not route:
        return root / "index.html"
    if route.endswith("/"):
        return root / route / "index.html"
    return root / route


def source_path(root: Path, route: str) -> Path:
    if not route:
        return root / "index.html"
    if route.endswith("/"):
        return root / route / "index.html"
    return root / route


def is_blocked_html(path: Path) -> tuple[bool, str | None]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()
    for marker in BLOCK_MARKERS:
        if marker.lower() in lowered:
            return True, marker
    robots = ROBOTS_RE.search(text)
    if robots and "noindex" in robots.group(1).lower():
        return True, "noindex"
    return False, None


def parse_sitemap(path: Path) -> list[str]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise RuntimeError(f"Invalid sitemap {path}: {exc}") from exc
    return [
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if (node.text or "").strip()
    ]


def title_for(path: Path, fallback: str) -> str:
    if path.suffix.lower() != ".html":
        return fallback
    match = TITLE_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return fallback
    title = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
    return title or fallback


def insert_before_main_end(path: Path, block: str, marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    match = END_MAIN_RE.search(text)
    if match:
        text = text[: match.start()] + block + text[match.start() :]
    else:
        text += block
    path.write_text(text, encoding="utf-8")


def copy_public_surface(source_root: Path, site_root: Path, route: str) -> list[str]:
    src = source_path(source_root, route)
    if not src.is_file():
        return []
    parts = Path(route.rstrip("/")).parts
    copied: list[str] = []
    if route.endswith("/") and parts:
        top = parts[0]
        src_top = source_root / top
        dst_top = site_root / top
        if src_top.is_dir():
            if dst_top.exists():
                shutil.rmtree(dst_top)
            shutil.copytree(src_top, dst_top)
            copied.append(top + "/")
            return copied
    dst = output_path(site_root, route)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(route)
    return copied


def append_sitemap_to_robots(site_root: Path, sitemap_name: str) -> None:
    robots = site_root / "robots.txt"
    text = robots.read_text(encoding="utf-8") if robots.exists() else "User-agent: *\nAllow: /\n"
    line = f"Sitemap: {BASE_URL}{sitemap_name}"
    lines = [item.rstrip() for item in text.splitlines()]
    if line not in lines:
        text = text.rstrip() + "\n" + line + "\n"
        robots.write_text(text, encoding="utf-8")


def add_static_discovery(site_root: Path, restored_html: list[str]) -> None:
    grouped: dict[str, list[str]] = defaultdict(list)
    for route in restored_html:
        parts = Path(route.rstrip("/")).parts
        if not parts:
            continue
        grouped[parts[0]].append(route)

    gateways: list[tuple[str, str]] = []
    for top, routes in sorted(grouped.items()):
        gateway = site_root / top / "index.html"
        if not gateway.is_file():
            continue
        links = []
        for route in sorted(set(routes)):
            if route.rstrip("/") == top:
                continue
            target = output_path(site_root, route)
            label = title_for(target, route)
            href = BASE_PATH + route
            links.append(f'<li><a href="{html.escape(href, quote=True)}">{html.escape(label)}</a></li>')
        if links:
            marker = "source-publication-parity-v342:directory"
            block = (
                f'<!-- {marker}:start -->\n'
                '<section class="section" data-source-publication-parity-v342="directory">'
                '<div class="wrap"><p class="kicker">دليل الصفحات المنشورة</p>'
                '<h2>جميع الصفحات المتاحة في هذا القسم</h2>'
                '<p>روابط HTML مباشرة لضمان الوصول دون الاعتماد على JavaScript.</p>'
                f'<ul class="source-publication-directory">{"".join(links)}</ul>'
                '</div></section>\n'
                f'<!-- {marker}:end -->\n'
            )
            insert_before_main_end(gateway, block, marker)
        gateways.append((top, title_for(gateway, top)))

    if not gateways:
        return
    directory = site_root / "sections" / "index.html"
    if not directory.is_file():
        directory = site_root / "special-needs" / "index.html"
    if not directory.is_file():
        raise RuntimeError("No institutional directory page is available for restored gateways")
    marker = "source-publication-parity-v342:gateways"
    links = "".join(
        f'<li><a href="{BASE_PATH}{html.escape(top, quote=True)}/">{html.escape(label)}</a></li>'
        for top, label in gateways
    )
    block = (
        f'<!-- {marker}:start -->\n'
        '<section class="section" data-source-publication-parity-v342="gateways">'
        '<div class="wrap"><p class="kicker">صفحات مستعادة من مصدر النشر</p>'
        '<h2>أقسام عامة متاحة</h2>'
        f'<ul>{links}</ul></div></section>\n'
        f'<!-- {marker}:end -->\n'
    )
    insert_before_main_end(directory, block, marker)


def validate_local_refs(site_root: Path, routes: list[str]) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    attr_re = re.compile(r'(?:href|src)=["\']([^"\']+)["\']', re.I)
    for route in routes:
        page = output_path(site_root, route)
        if page.suffix.lower() != ".html" or not page.is_file():
            continue
        text = page.read_text(encoding="utf-8", errors="replace")
        for ref in attr_re.findall(text):
            if not ref or ref.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:", "javascript:")):
                continue
            clean = ref.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            if clean.startswith(BASE_PATH):
                candidate_route = clean[len(BASE_PATH) :]
                target = output_path(site_root, candidate_route) if clean.endswith("/") else site_root / candidate_route
            elif clean.startswith("/"):
                continue
            else:
                target = (page.parent / unquote(clean)).resolve()
                try:
                    target.relative_to(site_root.resolve())
                except ValueError:
                    continue
                if clean.endswith("/"):
                    target = target / "index.html"
            if not target.exists():
                missing.append({"page": route, "reference": ref})
    return missing


def restore(source_root: Path, site_root: Path, report_path: Path) -> dict[str, object]:
    if not site_root.is_dir():
        raise RuntimeError(f"Production artifact does not exist: {site_root}")
    critical_before = {name: sha256(site_root / name) for name in CRITICAL_FILES}

    sitemap_files = sorted(source_root.glob("sitemap-*.xml"))
    candidates: dict[str, dict[str, str]] = {}
    skipped_blocked: list[dict[str, str]] = []
    missing_source: list[dict[str, str]] = []
    contributing_sitemaps: set[Path] = set()

    for sitemap in sitemap_files:
        for url in parse_sitemap(sitemap):
            route = route_for_url(url)
            if route is None:
                continue
            src = source_path(source_root, route)
            if not src.is_file():
                continue
            if src.suffix.lower() == ".html":
                blocked, reason = is_blocked_html(src)
                if blocked:
                    skipped_blocked.append({"route": route, "reason": str(reason), "sitemap": sitemap.name})
                    continue
            candidates.setdefault(route, {"url": url, "sitemap": sitemap.name})

    initially_missing = [route for route in candidates if not output_path(site_root, route).is_file()]
    copied_surfaces: set[str] = set()
    for route in initially_missing:
        copied = copy_public_surface(source_root, site_root, route)
        if not copied:
            missing_source.append({"route": route, "sitemap": candidates[route]["sitemap"]})
            continue
        copied_surfaces.update(copied)
        contributing_sitemaps.add(source_root / candidates[route]["sitemap"])

    for route in initially_missing:
        src = source_path(source_root, route)
        dst = output_path(site_root, route)
        if src.is_file() and not dst.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for sitemap in sorted(contributing_sitemaps):
        shutil.copy2(sitemap, site_root / sitemap.name)
        append_sitemap_to_robots(site_root, sitemap.name)

    restored = [route for route in initially_missing if output_path(site_root, route).is_file()]
    restored_html = [route for route in restored if output_path(site_root, route).suffix.lower() == ".html"]
    add_static_discovery(site_root, restored_html)

    remaining_missing = [route for route in candidates if not output_path(site_root, route).is_file()]
    broken_refs = validate_local_refs(site_root, restored_html)
    critical_after = {name: sha256(site_root / name) for name in CRITICAL_FILES}
    critical_changed = [name for name in CRITICAL_FILES if critical_before[name] != critical_after[name]]

    report: dict[str, object] = {
        "version": 342,
        "status": "passed" if not remaining_missing and not broken_refs and not critical_changed else "failed",
        "source_sitemaps_scanned": len(sitemap_files),
        "source_backed_public_routes": len(candidates),
        "initially_missing_routes": len(initially_missing),
        "restored_routes": len(restored),
        "restored_html_routes": len(restored_html),
        "restored_top_level_surfaces": sorted(copied_surfaces),
        "restored_sitemaps": sorted(path.name for path in contributing_sitemaps),
        "remaining_missing_routes": remaining_missing,
        "blocked_routes_not_restored": skipped_blocked,
        "source_mapping_failures": missing_source,
        "broken_local_references": broken_refs,
        "critical_files_unchanged": not critical_changed,
        "critical_files_changed": critical_changed,
        "routes": restored,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise RuntimeError(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_root", type=Path)
    parser.add_argument("--source-root", type=Path, default=Path("."))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    site_root = args.site_root.resolve()
    source_root = args.source_root.resolve()
    report_path = args.report or site_root / "api" / "source-publication-parity-v342.json"
    report = restore(source_root, site_root, report_path.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
