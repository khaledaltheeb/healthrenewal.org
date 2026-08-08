#!/usr/bin/env python3
"""Finalize the upgraded Quick Information corpus without rebuilding old templates.

This pass is intentionally narrow: it operates on the already-current 250 pages,
updates truthful modification metadata after the material long-form revision,
updates the section sitemap lastmod values, and records a deterministic report.
It never changes datePublished and never replaces article content.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECTION = ROOT / "quick-info"
API_PATH = ROOT / "api" / "v1" / "quick-info.json"
SITEMAP_PATH = ROOT / "sitemap-quick-info.xml"
REPORT_PATH = ROOT / "reports" / "quick-info-upgrade-finalization.json"

EXPECTED_COUNT = 250
MODIFIED_DATE = "2026-08-08"
MODIFIED_ISO = "2026-08-08T13:00:00+03:00"
MODIFIED_AR = "8 أغسطس 2026"

META_MODIFIED_RE = re.compile(
    r'<meta\s+property=["\']article:modified_time["\']\s+content=["\'][^"\']+["\']\s*/?>',
    re.IGNORECASE,
)
JSON_MODIFIED_RE = re.compile(r'"dateModified"\s*:\s*"\d{4}-\d{2}-\d{2}"')
UPDATE_PILL_RE = re.compile(r'<span\s+class=["\']pill["\']>تحديث:[^<]*</span>')
PUBLISH_PILL_RE = re.compile(r'(<span\s+class=["\']pill["\']>نشر:[^<]*</span>)')


def patch_page(path: Path) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    before = source

    replacement_meta = (
        f'<meta property="article:modified_time" content="{MODIFIED_ISO}">'
    )
    if META_MODIFIED_RE.search(source):
        source = META_MODIFIED_RE.sub(replacement_meta, source, count=1)
    else:
        source = source.replace("</head>", replacement_meta + "</head>", 1)

    if JSON_MODIFIED_RE.search(source):
        source = JSON_MODIFIED_RE.sub(
            f'"dateModified":"{MODIFIED_DATE}"', source, count=1
        )

    updated_pill = f'<span class="pill">تحديث: {MODIFIED_AR}</span>'
    if UPDATE_PILL_RE.search(source):
        source = UPDATE_PILL_RE.sub(updated_pill, source, count=1)
    elif PUBLISH_PILL_RE.search(source):
        source = PUBLISH_PILL_RE.sub(r"\1" + updated_pill, source, count=1)

    if source != before:
        path.write_text(source, encoding="utf-8", newline="\n")

    checks = {
        "metaModified": MODIFIED_ISO in source,
        "jsonLdModified": f'"dateModified":"{MODIFIED_DATE}"' in source,
        "visibleModified": f"تحديث: {MODIFIED_AR}" in source,
        "publishedDatePreserved": '"datePublished":"2026-08-04"' in source,
    }
    return {"changed": source != before, "checks": checks}


def update_api() -> dict[str, object]:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if payload.get("count") != EXPECTED_COUNT or len(items) != EXPECTED_COUNT:
        raise SystemExit(f"Expected {EXPECTED_COUNT} API items, found {len(items)}")
    payload["generatedAt"] = MODIFIED_ISO
    API_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"count": len(items), "generatedAt": payload["generatedAt"]}


def update_sitemap() -> dict[str, object]:
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    ET.register_namespace("image", "http://www.google.com/schemas/sitemap-image/1.1")
    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = root.findall("sm:url", ns)
    if len(urls) != EXPECTED_COUNT + 1:
        raise SystemExit(f"Expected {EXPECTED_COUNT + 1} sitemap URLs, found {len(urls)}")
    locations: list[str] = []
    for node in urls:
        loc = node.find("sm:loc", ns)
        lastmod = node.find("sm:lastmod", ns)
        if loc is None or not (loc.text or "").strip():
            raise SystemExit("Sitemap URL without loc")
        locations.append((loc.text or "").strip())
        if lastmod is None:
            lastmod = ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        lastmod.text = MODIFIED_DATE
    if len(locations) != len(set(locations)):
        raise SystemExit("Duplicate URL in sitemap-quick-info.xml")
    tree.write(SITEMAP_PATH, encoding="utf-8", xml_declaration=True)
    return {"urls": len(urls), "lastmod": MODIFIED_DATE, "unique": True}


def main() -> None:
    payload = json.loads(API_PATH.read_text(encoding="utf-8"))
    items = payload.get("items", [])
    if len(items) != EXPECTED_COUNT:
        raise SystemExit(f"Expected {EXPECTED_COUNT} items, found {len(items)}")

    failures: list[str] = []
    changed = 0
    page_results: list[dict[str, object]] = []
    for item in items:
        page = SECTION / item["slug"] / "index.html"
        if not page.is_file():
            failures.append(f"missing page: {item['slug']}")
            continue
        result = patch_page(page)
        if result["changed"]:
            changed += 1
        checks = result["checks"]
        assert isinstance(checks, dict)
        missing = [key for key, ok in checks.items() if not ok]
        if missing:
            failures.append(f"{item['slug']}: {', '.join(missing)}")
        page_results.append({"slug": item["slug"], **result})

    api_result = update_api()
    sitemap_result = update_sitemap()
    report = {
        "version": "1.0.0",
        "status": "passed" if not failures else "failed",
        "pagesExpected": EXPECTED_COUNT,
        "pagesChecked": len(page_results),
        "pagesChanged": changed,
        "modifiedDate": MODIFIED_DATE,
        "modifiedIso": MODIFIED_ISO,
        "datePublishedPreserved": not any("publishedDatePreserved" in f for f in failures),
        "api": api_result,
        "sitemap": sitemap_result,
        "failures": failures,
        "pages": page_results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "pages"}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit("\n".join(failures[:50]))


if __name__ == "__main__":
    main()
