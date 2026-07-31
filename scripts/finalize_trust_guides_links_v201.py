#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ORIGIN = "https://healthrenewal.org"
LEGACY_ORIGINS = (
    "https://khaledaltheeb.github.io/pterminology-site",
    "http://khaledaltheeb.github.io/pterminology-site",
)
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
CANONICAL_RE = re.compile(
    r'<link\b(?=[^>]*\brel\s*=\s*(["\'])[^"\']*\bcanonical\b[^"\']*\1)[^>]*>',
    re.I | re.S,
)
REFRESH_RE = re.compile(
    r'<meta\b(?=[^>]*\bhttp-equiv\s*=\s*(["\'])refresh\1)[^>]*>',
    re.I | re.S,
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _custom_url(value: str) -> str:
    normalized = value.strip()
    for origin in LEGACY_ORIGINS:
        normalized = normalized.replace(origin, CANONICAL_ORIGIN)
    normalized = normalized.replace("/pterminology-site/", "/")
    normalized = normalized.replace(f"{CANONICAL_ORIGIN}//", f"{CANONICAL_ORIGIN}/")
    return normalized


def _normalize_public_text(text: str) -> str:
    updated = text
    for origin in LEGACY_ORIGINS:
        updated = updated.replace(origin, CANONICAL_ORIGIN)
    updated = updated.replace("/pterminology-site/", "/")
    updated = updated.replace('href="/blog/"', 'href="/magazine/"')
    updated = updated.replace("href='/blog/'", "href='/magazine/'")
    updated = updated.replace(f"{CANONICAL_ORIGIN}//", f"{CANONICAL_ORIGIN}/")
    return updated


def _normalize_alias_source(text: str, canonical_route: str) -> str:
    updated = _normalize_public_text(text)
    canonical = f"{CANONICAL_ORIGIN}{canonical_route}"
    canonical_tag = f'<link rel="canonical" href="{canonical}">'
    refresh_tag = f'<meta http-equiv="refresh" content="0;url={canonical_route}">'

    if CANONICAL_RE.search(updated):
        updated = CANONICAL_RE.sub(canonical_tag, updated, count=1)
    else:
        updated, count = re.subn(
            r"\s*</head\s*>",
            "\n" + canonical_tag + "\n</head>",
            updated,
            count=1,
            flags=re.I,
        )
        if count != 1:
            raise SystemExit("Compatibility alias source is missing </head>")

    if REFRESH_RE.search(updated):
        updated = REFRESH_RE.sub(refresh_tag, updated, count=1)
    else:
        updated, count = re.subn(
            r"\s*</head\s*>",
            "\n" + refresh_tag + "\n</head>",
            updated,
            count=1,
            flags=re.I,
        )
        if count != 1:
            raise SystemExit("Compatibility alias source is missing </head>")
    return updated


def _remove_alias_urls(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {"removed": 0, "normalized": 0}
    tree = ET.parse(path)
    root = tree.getroot()
    removed = 0
    normalized_count = 0
    if _local_name(root.tag) == "urlset":
        for node in list(root):
            if _local_name(node.tag) != "url":
                continue
            loc = next((child for child in node if _local_name(child.tag) == "loc"), None)
            value = (loc.text or "").strip() if loc is not None else ""
            normalized = _custom_url(value)
            if any(normalized.endswith(route) for route in ALIAS_ROUTES):
                root.remove(node)
                removed += 1
                continue
            if loc is not None and normalized != value:
                loc.text = normalized
                normalized_count += 1
    if removed or normalized_count:
        ET.indent(root, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)
    return {"removed": removed, "normalized": normalized_count}


def _remove_alias_discovery_links(site: Path) -> tuple[list[str], list[str]]:
    changed: list[str] = []
    remaining: list[str] = []
    route_pattern = "|".join(re.escape(route.lstrip("/")) for route in ALIAS_ROUTES)
    item_re = re.compile(
        rf'<li>\s*<a\b[^>]*href=(["\'])(?:/pterminology-site)?/(?:{route_pattern})\1[^>]*>.*?</a>\s*</li>',
        re.I | re.S,
    )
    for relative in DISCOVERY_TARGETS:
        path = site / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        updated = _normalize_public_text(item_re.sub("", text))
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(relative)
        if any(route in updated for route in ALIAS_ROUTES):
            remaining.append(relative)
    return changed, remaining


def _restore_alias_pages(site: Path) -> list[str]:
    restored: list[str] = []
    for relative, canonical_route in ALIAS_TARGETS.items():
        source = ROOT / relative
        if not source.is_file():
            raise SystemExit(f"Missing repository alias source: {relative}")
        text = _normalize_alias_source(source.read_text(encoding="utf-8"), canonical_route)
        required = (
            "data-legacy-path-alias=",
            'name="robots" content="noindex,follow"',
            f'href="{CANONICAL_ORIGIN}{canonical_route}"',
            f'content="0;url={canonical_route}"',
        )
        missing = [marker for marker in required if marker not in text]
        if missing:
            raise SystemExit(f"Invalid compatibility alias source {relative}: {missing}")
        if any(origin in text for origin in LEGACY_ORIGINS) or "/pterminology-site/" in text:
            raise SystemExit(f"Legacy origin or base path remains in compatibility alias: {relative}")
        destination = site / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        restored.append(relative)
    return restored


def _validate_alias_pages(site: Path) -> None:
    for relative, canonical_route in ALIAS_TARGETS.items():
        text = (site / relative).read_text(encoding="utf-8")
        if text.count("data-legacy-path-alias=") != 1:
            raise SystemExit(f"Alias marker missing or duplicated: {relative}")
        if text.count('name="robots" content="noindex,follow"') != 1:
            raise SystemExit(f"Alias robots contract failed: {relative}")
        if text.count(f'href="{CANONICAL_ORIGIN}{canonical_route}"') != 1:
            raise SystemExit(f"Alias canonical contract failed: {relative}")
        if text.count(f'content="0;url={canonical_route}"') != 1:
            raise SystemExit(f"Alias redirect contract failed: {relative}")
        if any(origin in text for origin in LEGACY_ORIGINS) or "/pterminology-site/" in text:
            raise SystemExit(f"Alias legacy-origin contract failed: {relative}")


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
        updated = _normalize_public_text(text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed_pages.append(relative)
        if any(origin in updated for origin in LEGACY_ORIGINS) or "/pterminology-site/" in updated:
            remaining_legacy.append(relative)
    if remaining_legacy:
        raise SystemExit(f"Legacy origins remain in trust guides: {remaining_legacy}")

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
        if isinstance(page.get("url"), str):
            page["url"] = _custom_url(str(page["url"]))
        if relative in ALIAS_TARGETS:
            page["publication_status"] = "compatibility-alias"
            page["indexable"] = False
            page["canonical_route"] = ALIAS_TARGETS[relative]
            page["canonical_url"] = CANONICAL_ORIGIN + ALIAS_TARGETS[relative]
        elif relative == PUBLIC_TARGET:
            page["publication_status"] = "public"
            page["indexable"] = True

    previous_compatibility = report.get("link_compatibility", {})
    previous_changed = (
        previous_compatibility.get("changed_pages", [])
        if isinstance(previous_compatibility, dict)
        else []
    )
    stable_changed_pages = sorted(
        {
            str(item)
            for item in [*previous_changed, *changed_pages]
            if isinstance(item, str) and item
        }
    )
    report["link_compatibility"] = {
        "legacy_blog_route": "/blog/",
        "active_route": "/magazine/",
        "changed_pages": stable_changed_pages,
        "remaining_legacy_links": [],
    }
    report["publication_contract"] = {
        "canonical_origin": CANONICAL_ORIGIN,
        "public_pages": [PUBLIC_TARGET],
        "compatibility_aliases": sorted(ALIAS_TARGETS),
        "public_page_count": 1,
        "alias_page_count": len(ALIAS_TARGETS),
        "aliases_indexable": False,
        "aliases_in_sitemaps": False,
        "aliases_in_discovery": False,
        "legacy_origins_remaining": 0,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "version": 355,
        "changed_pages": changed_pages,
        "normalized_pages": stable_changed_pages,
        "restored_aliases": restored_aliases,
        "public_pages": [PUBLIC_TARGET],
        "sitemap_alias_urls": sitemap_pruned,
        "discovery_pages_changed": discovery_changed,
        "remaining_legacy_links": [],
        "remaining_alias_discovery_links": [],
        "canonical_origin": CANONICAL_ORIGIN,
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
