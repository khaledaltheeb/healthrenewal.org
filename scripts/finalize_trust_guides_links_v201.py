#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_BLOG = 'href="/pterminology-site/blog/"'
MAGAZINE = 'href="/pterminology-site/magazine/"'
PUBLIC_TARGET = "guides/source-citation-and-update-transparency/index.html"
ALIAS_TARGETS = {
    "editorial-methodology/index.html": "/trust/",
    "evaluate-mental-health-information/index.html": "/trust/",
}
ALIAS_ROUTES = {
    "/editorial-methodology/",
    "/evaluate-mental-health-information/",
}
DISCOVERY_TARGETS = (
    "trust/index.html",
    "magazine/index.html",
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _remove_alias_urls(path: Path) -> int:
    if not path.is_file():
        return 0
    tree = ET.parse(path)
    root = tree.getroot()
    removed = 0
    if _local_name(root.tag) == "urlset":
        for node in list(root):
            if _local_name(node.tag) != "url":
                continue
            loc = next((child for child in node if _local_name(child.tag) == "loc"), None)
            value = (loc.text or "").strip() if loc is not None else ""
            if any(value.endswith(route) for route in ALIAS_ROUTES):
                root.remove(node)
                removed += 1
    if removed:
        tree.write(path, encoding="utf-8", xml_declaration=True)
    return removed


def _remove_alias_discovery_links(site: Path) -> tuple[list[str], list[str]]:
    changed: list[str] = []
    remaining: list[str] = []
    route_pattern = "|".join(re.escape(route.lstrip("/")) for route in ALIAS_ROUTES)
    item_re = re.compile(
        rf'<li>\s*<a\b[^>]*href=(["\'])/pterminology-site/(?:{route_pattern})\1[^>]*>.*?</a>\s*</li>',
        re.I | re.S,
    )
    for relative in DISCOVERY_TARGETS:
        path = site / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        updated = item_re.sub("", text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(relative)
        if any(f'/pterminology-site/{route.lstrip("/")}' in updated for route in ALIAS_ROUTES):
            remaining.append(relative)
    return changed, remaining


def _restore_alias_pages(site: Path) -> list[str]:
    restored: list[str] = []
    for relative, canonical_route in ALIAS_TARGETS.items():
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit(f"Missing repository alias source: {relative}")
        text = source.read_text(encoding="utf-8")
        required = (
            "data-legacy-path-alias=",
            'name="robots" content="noindex,follow"',
            f'href="https://khaledaltheeb.github.io/pterminology-site{canonical_route}"',
            f'content="0;url=/pterminology-site{canonical_route}"',
        )
        missing = [marker for marker in required if marker not in text]
        if missing:
            raise SystemExit(f"Invalid compatibility alias source {relative}: {missing}")
        destination = site / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        restored.append(relative)
    return restored


def _validate_alias_pages(site: Path) -> None:
    for relative, canonical_route in ALIAS_TARGETS.items():
        text = (site / relative).read_text(encoding="utf-8")
        if text.count("data-legacy-path-alias=") != 1:
            raise SystemExit(f"Alias marker missing or duplicated: {relative}")
        if 'name="robots" content="noindex,follow"' not in text:
            raise SystemExit(f"Alias robots contract failed: {relative}")
        if f'href="https://khaledaltheeb.github.io/pterminology-site{canonical_route}"' not in text:
            raise SystemExit(f"Alias canonical contract failed: {relative}")
        if f'content="0;url=/pterminology-site{canonical_route}"' not in text:
            raise SystemExit(f"Alias redirect contract failed: {relative}")


def finalize(site: Path) -> dict[str, object]:
    generated_targets = (*ALIAS_TARGETS.keys(), PUBLIC_TARGET)
    missing_pages = [relative for relative in generated_targets if not (site / relative).is_file()]
    if missing_pages:
        raise SystemExit(f"Missing generated trust-guide pages: {missing_pages}")

    changed_pages: list[str] = []
    remaining_legacy: list[str] = []
    for relative in generated_targets:
        path = site / relative
        text = path.read_text(encoding="utf-8")
        updated = text.replace(LEGACY_BLOG, MAGAZINE)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed_pages.append(relative)
        if LEGACY_BLOG in updated:
            remaining_legacy.append(relative)
    if remaining_legacy:
        raise SystemExit(f"Legacy blog links remain in trust guides: {remaining_legacy}")

    restored_aliases = _restore_alias_pages(site)
    _validate_alias_pages(site)
    discovery_changed, discovery_remaining = _remove_alias_discovery_links(site)
    if discovery_remaining:
        raise SystemExit(f"Alias discovery links remain in public pages: {discovery_remaining}")

    sitemap_pruned = {
        "sitemap-trust-guides.xml": _remove_alias_urls(site / "sitemap-trust-guides.xml"),
        "sitemap.xml": _remove_alias_urls(site / "sitemap.xml"),
    }

    report_path = site / "api" / "trust-guides-v201.json"
    if not report_path.is_file():
        raise SystemExit("Missing trust-guides-v201 report before link finalization")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    pages = report.get("pages", [])
    for page in pages:
        if not isinstance(page, dict):
            continue
        relative = str(page.get("path", ""))
        if relative in ALIAS_TARGETS:
            page["publication_status"] = "compatibility-alias"
            page["indexable"] = False
            page["canonical_route"] = ALIAS_TARGETS[relative]
        elif relative == PUBLIC_TARGET:
            page["publication_status"] = "public"
            page["indexable"] = True
    report["link_compatibility"] = {
        "legacy_blog_route": "/blog/",
        "active_route": "/magazine/",
        "changed_pages": changed_pages,
        "remaining_legacy_links": [],
    }
    report["publication_contract"] = {
        "public_pages": [PUBLIC_TARGET],
        "compatibility_aliases": sorted(ALIAS_TARGETS),
        "public_page_count": 1,
        "alias_page_count": len(ALIAS_TARGETS),
        "aliases_indexable": False,
        "aliases_in_sitemaps": False,
        "aliases_in_discovery": False,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "version": 354,
        "changed_pages": changed_pages,
        "restored_aliases": restored_aliases,
        "public_pages": [PUBLIC_TARGET],
        "sitemap_alias_urls_removed": sitemap_pruned,
        "discovery_pages_changed": discovery_changed,
        "remaining_legacy_links": [],
        "remaining_alias_discovery_links": [],
        "active_route": "/magazine/",
        "alias_target": "/trust/",
        "status": "passed",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not target.is_dir():
        raise SystemExit(f"Missing site directory: {target}")
    finalize(target)
