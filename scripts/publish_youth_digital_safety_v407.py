#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

VERSION = 407
BASE = "https://healthrenewal.org"
REVIEWED_AT = "2026-09-04"
ROOT = Path(__file__).resolve().parents[1]
HUB_ROUTE = "sectors/youth/digital-safety/"
HUB_URL = f"{BASE}/{HUB_ROUTE}"
YOUTH_ROUTE = "sectors/youth/"
YOUTH_URL = f"{BASE}/{YOUTH_ROUTE}"
YOUTH_SITEMAP = "sitemap-sector-youth.xml"
SITEMAP_INDEX = "sitemap-index.xml"
HUB_TEMPLATE = ROOT / HUB_ROUTE / "index.html"

FEATURE_BLOCK = '''<section class="hub-feature" aria-labelledby="digital-safety-title" style="background:linear-gradient(135deg,#e6f6f1,#fff);border:1px solid #d2e1dc;border-inline-start:7px solid #0b8f92;border-radius:18px;padding:1.2rem;margin:1.2rem 0 2rem"><span class="tag">قسم متخصص</span><h2 id="digital-safety-title">السلامة الرقمية وحماية الأطفال واليافعين</h2><p>مركز يجمع التنمر والعنف الرقمي، الابتزاز والاستغلال، الصور والمحتوى الحميمي، الخصوصية والهوية، المحتوى الضار، الألعاب والمنصات، الأبوة الرقمية، وحفظ الأدلة والإبلاغ. يبدأ بما حدث للمستخدم ثم يوجهه إلى مسار الاستجابة المناسب بدل تكرار الأدلة الموجودة.</p><p><a href="digital-safety/"><strong>فتح قسم السلامة الرقمية ←</strong></a></p></section>'''


def _jsonld_with_has_part(source: str) -> str:
    match = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', source, re.S)
    if not match:
        raise ValueError("Youth hub is missing JSON-LD")
    payload = json.loads(match.group(2))
    if payload.get("@type") != "CollectionPage":
        raise ValueError("Unexpected youth hub JSON-LD type")
    payload.setdefault("@id", f"{YOUTH_URL}#page")
    payload["hasPart"] = {
        "@type": "CollectionPage",
        "name": "السلامة الرقمية وحماية الأطفال واليافعين",
        "url": HUB_URL,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return source[: match.start(2)] + encoded + source[match.end(2) :]


def _inject_parent_hub_link(source: str) -> str:
    if 'href="digital-safety/"' not in source:
        marker = '<section><h2>الأدلة المنشورة</h2>'
        if marker not in source:
            raise ValueError("Unable to locate youth guides marker")
        source = source.replace(marker, FEATURE_BLOCK + marker, 1)
    source = _jsonld_with_has_part(source)
    sentence = "يضم المركز 15 دليلًا طويلًا، كل منها يوضح التقييم الوظيفي وخط الأساس وخطوات التطبيق ومؤشرات القرار وحدود السلامة والمصادر."
    replacement = "يضم المركز 15 دليلًا طويلًا، إضافة إلى مركز متخصص للسلامة الرقمية وحماية الأطفال واليافعين."
    source = source.replace(sentence, replacement, 1)
    return source


def _ensure_youth_sitemap(site: Path) -> int:
    path = site / YOUTH_SITEMAP
    tree = ET.parse(path)
    root = tree.getroot()
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    existing: list[str] = []
    for url_node in root.findall("{*}url"):
        loc = url_node.find("{*}loc")
        if loc is not None and loc.text:
            existing.append(loc.text.strip())
            if loc.text.strip() == YOUTH_URL:
                lastmod = url_node.find("{*}lastmod")
                if lastmod is None:
                    lastmod = ET.SubElement(url_node, f"{{{ns}}}lastmod")
                lastmod.text = REVIEWED_AT
    if HUB_URL not in existing:
        node = ET.Element(f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = HUB_URL
        ET.SubElement(node, f"{{{ns}}}lastmod").text = REVIEWED_AT
        root.insert(1, node)
    ET.register_namespace("", ns)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
    if len(urls) != len(set(urls)):
        raise ValueError("Duplicate URLs in youth sitemap")
    if HUB_URL not in urls:
        raise ValueError("Digital safety hub missing from youth sitemap")
    return len(urls)


def _ensure_sitemap_index(site: Path) -> bool:
    path = site / SITEMAP_INDEX
    if not path.is_file():
        return False
    tree = ET.parse(path)
    root = tree.getroot()
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    target = f"{BASE}/{YOUTH_SITEMAP}"
    for sitemap in root.findall("{*}sitemap"):
        loc = sitemap.find("{*}loc")
        if loc is not None and (loc.text or "").strip() == target:
            lastmod = sitemap.find("{*}lastmod")
            if lastmod is None:
                lastmod = ET.SubElement(sitemap, f"{{{ns}}}lastmod")
            lastmod.text = REVIEWED_AT
            ET.register_namespace("", ns)
            ET.indent(tree, space="  ")
            tree.write(path, encoding="utf-8", xml_declaration=True)
            return True
    node = ET.SubElement(root, f"{{{ns}}}sitemap")
    ET.SubElement(node, f"{{{ns}}}loc").text = target
    ET.SubElement(node, f"{{{ns}}}lastmod").text = REVIEWED_AT
    ET.register_namespace("", ns)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return True


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not HUB_TEMPLATE.is_file():
        raise FileNotFoundError(HUB_TEMPLATE)

    target_hub = site / HUB_ROUTE / "index.html"
    target_hub.parent.mkdir(parents=True, exist_ok=True)
    if target_hub.resolve() != HUB_TEMPLATE.resolve():
        shutil.copy2(HUB_TEMPLATE, target_hub)

    youth_index = site / YOUTH_ROUTE / "index.html"
    if not youth_index.is_file():
        raise FileNotFoundError(youth_index)
    parent = _inject_parent_hub_link(youth_index.read_text(encoding="utf-8"))
    youth_index.write_text(parent, encoding="utf-8")

    sitemap_count = _ensure_youth_sitemap(site)
    index_registered = _ensure_sitemap_index(site)

    report = {
        "version": VERSION,
        "status": "passed",
        "hub_route": HUB_ROUTE,
        "hub_url": HUB_URL,
        "parent_route": YOUTH_ROUTE,
        "sitemap": YOUTH_SITEMAP,
        "sitemap_count": sitemap_count,
        "sitemap_index_registered": index_registered,
        "rights_boundary": "no-partnership-or-endorsement-claim-before-explicit-permission",
        "reviewed_at": REVIEWED_AT,
    }
    api = site / "api" / "youth-digital-safety-v407.json"
    api.parent.mkdir(parents=True, exist_ok=True)
    api.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish the durable youth digital-safety hub v407 after the v406 youth build.")
    parser.add_argument("site", nargs="?", type=Path, default=ROOT)
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
