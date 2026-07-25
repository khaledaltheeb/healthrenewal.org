#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import publish_special_needs_guides_v209 as publisher

ORIGINAL_UPSERT = publisher.upsert_urlset
ORIGINAL_HUB_CARDS = publisher.hub_cards
ORIGINAL_LINK_HUB = publisher.link_hub
MAIN_SITEMAP_MODE = "urlset"

BATCH_HEADINGS = {
    209: "أدلة التربية الدامجة والوصول والمشاركة",
    210: "أدلة التدخل المبكر والمهارات اليومية",
    211: "أدلة الحركة والحماية والانتقال إلى الرشد",
    212: "أدلة التعليم واختيار الخدمات والمشاركة المجتمعية",
}
CURRENT_SOURCE_MARKER = '<section><h2>مصادر الوحدة الحالية</h2>'
LEGACY_RESOURCE_MARKER = '<div class="resources">'


def marker_version() -> int:
    match = re.search(r"special-needs-guides-v(\d+):start", publisher.START)
    if not match:
        raise SystemExit(f"Unsupported special-needs guide marker: {publisher.START}")
    return int(match.group(1))


def compatible_hub_cards(guides: list[dict[str, Any]]) -> str:
    version = marker_version()
    heading = BATCH_HEADINGS.get(version, "أدلة عملية موسعة")
    cards = "".join(
        f'''<article class="card resource"><h3>{publisher.esc(guide["title"])}</h3>
        <p>{publisher.esc(guide["description"])}</p>
        <a class="button secondary" href="{publisher.BASE_PATH}special-needs/{publisher.esc(guide["slug"])}/">فتح الدليل العملي</a></article>'''
        for guide in guides
    )
    return (
        publisher.START
        + f'<section class="guide-batch" data-guide-batch="{version}" '
        + f'aria-labelledby="guide-batch-title-{version}"><h2 id="guide-batch-title-{version}">{publisher.esc(heading)}</h2>'
        + f'<div class="cards">{cards}</div></section>'
        + publisher.END
    )


def compatible_link_hub(site: Path, guides: list[dict[str, Any]]) -> None:
    hub = site / "special-needs" / "index.html"
    if not hub.is_file():
        raise SystemExit("Special-needs hub must exist before guide linking")

    text = hub.read_text(encoding="utf-8")
    payload = compatible_hub_cards(guides)
    has_start = publisher.START in text
    has_end = publisher.END in text
    if has_start != has_end:
        raise SystemExit("Special-needs hub contains an incomplete guide batch marker")

    if has_start:
        pattern = re.escape(publisher.START) + r".*?" + re.escape(publisher.END)
        text, count = re.subn(pattern, payload, text, count=1, flags=re.S)
        if count != 1:
            raise SystemExit("Special-needs guide block replacement was ambiguous")
    elif LEGACY_RESOURCE_MARKER in text:
        text = text.replace(LEGACY_RESOURCE_MARKER, LEGACY_RESOURCE_MARKER + payload, 1)
    elif CURRENT_SOURCE_MARKER in text:
        text = text.replace(CURRENT_SOURCE_MARKER, payload + CURRENT_SOURCE_MARKER, 1)
    elif text.count("</main>") == 1:
        text = text.replace("</main>", payload + "</main>", 1)
    else:
        raise SystemExit(
            "Special-needs hub has no supported guide insertion point: "
            "expected legacy resources, current sources section, or one main closing tag"
        )

    if text.count(publisher.START) != 1 or text.count(publisher.END) != 1:
        raise SystemExit("Special-needs guide batch markers must remain unique")
    for guide in guides:
        route = f'{publisher.BASE_PATH}special-needs/{guide["slug"]}/'
        if text.count(route) != 1:
            raise SystemExit(f"Special-needs guide route must appear once in its batch: {route}")

    hub.write_text(text, encoding="utf-8")


# Install the hub compatibility at import time. v210-v212 import this module
# before delegating to the shared v209 renderer, so every batch uses the same
# idempotent insertion contract while retaining its own START/END markers.
publisher.hub_cards = compatible_hub_cards
publisher.link_hub = compatible_link_hub


def compatible_upsert(path: Path, urls: list[str], modified: str) -> None:
    global MAIN_SITEMAP_MODE
    if path.name != "sitemap.xml" or not path.is_file():
        ORIGINAL_UPSERT(path, urls, modified)
        return

    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    tree = ET.parse(path)
    root = tree.getroot()
    mode = root.tag.rsplit("}", 1)[-1]
    MAIN_SITEMAP_MODE = mode

    if mode == "urlset":
        ORIGINAL_UPSERT(path, urls, modified)
        return
    if mode != "sitemapindex":
        raise SystemExit(f"Unsupported main sitemap root: {mode}")

    child_url = f"{publisher.BASE}/sitemap-special-needs.xml"
    existing = {
        node.text
        for node in root.findall(f"{{{ns}}}sitemap/{{{ns}}}loc")
        if node.text
    }
    if child_url not in existing:
        node = ET.SubElement(root, f"{{{ns}}}sitemap")
        ET.SubElement(node, f"{{{ns}}}loc").text = child_url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = modified
        tree.write(path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict[str, Any]:
    global MAIN_SITEMAP_MODE
    MAIN_SITEMAP_MODE = "urlset"
    publisher.upsert_urlset = compatible_upsert
    try:
        report = publisher.publish(site)
    finally:
        publisher.upsert_urlset = ORIGINAL_UPSERT

    report["main_sitemap_mode"] = MAIN_SITEMAP_MODE
    report["hub_layout_contract"] = 221
    report_path = site / "api" / "special-needs-guides-v209.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
