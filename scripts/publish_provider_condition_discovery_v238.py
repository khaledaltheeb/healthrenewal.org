#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VERSION = 238
UPDATED = "2026-07-25"
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
EXPECTED_CONDITIONS = 20
SITEMAP_NAME = "sitemap-provider-assessment.xml"
DIRECTORY_START = "<!-- provider-condition-discovery-v238:directory:start -->"
DIRECTORY_END = "<!-- provider-condition-discovery-v238:directory:end -->"
GATEWAY_START = "<!-- provider-condition-discovery-v238:gateway:start -->"
GATEWAY_END = "<!-- provider-condition-discovery-v238:gateway:end -->"
STYLE_MARKER = "data-provider-condition-discovery-v238-style"
SCHEMA_MARKER = "data-provider-condition-discovery-v238-schema"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", SITEMAP_NS)


class TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.parts.append(data)


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def title_from_source(source: str, slug: str) -> str:
    parser = TitleParser()
    parser.feed(source)
    title = " ".join(" ".join(parser.parts).split())
    if not title:
        raise ValueError(f"Missing title for provider condition: {slug}")
    return title.split("|", 1)[0].strip()


def remove_marker_block(source: str, start: str, end: str) -> str:
    source = re.sub(
        rf"\s*{re.escape(start)}.*?{re.escape(end)}\s*",
        "\n",
        source,
        flags=re.S,
    )
    return re.sub(r"\n{3,}", "\n\n", source)


def insert_before_closing(source: str, closing: str, block: str) -> str:
    if closing not in source:
        raise ValueError(f"Missing insertion point: {closing}")
    prefix, suffix = source.split(closing, 1)
    return prefix.rstrip() + "\n" + block.strip() + "\n" + closing + suffix.lstrip("\n")


def replace_marker_block(source: str, start: str, end: str, block: str) -> str:
    source = remove_marker_block(source, start, end)
    if "</main>" in source:
        return insert_before_closing(source, "</main>", block)
    if "</body>" in source:
        return insert_before_closing(source, "</body>", block)
    raise ValueError("Missing page insertion point")


def discover_conditions(site: Path) -> list[dict[str, str]]:
    root = site / "provider-assessment-demo" / "conditions"
    if not root.is_dir():
        raise ValueError(f"Missing provider condition directory: {root}")
    records: list[dict[str, str]] = []
    for page in sorted(root.glob("*/index.html")):
        slug = page.parent.name
        source = page.read_text(encoding="utf-8")
        canonical = f"{BASE}/provider-assessment-demo/conditions/{slug}/"
        if canonical not in source:
            raise ValueError(f"Missing canonical for provider condition: {slug}")
        if "noindex" in source.lower():
            raise ValueError(f"Provider condition must be indexable: {slug}")
        if len(re.findall(r"<h1\b", source, flags=re.I)) != 1:
            raise ValueError(f"Provider condition must contain exactly one H1: {slug}")
        records.append({"slug": slug, "title": title_from_source(source, slug), "url": canonical})
    if len(records) != EXPECTED_CONDITIONS:
        raise ValueError(f"Expected {EXPECTED_CONDITIONS} provider conditions, found {len(records)}")
    if len({record["slug"] for record in records}) != EXPECTED_CONDITIONS:
        raise ValueError("Duplicate provider condition slugs")
    return records


def directory_style() -> str:
    return f'''<style {STYLE_MARKER}>
.provider-condition-discovery-v238{{margin:2rem 0;padding:clamp(1rem,3vw,2rem);border:1px solid #b8ddd7;border-radius:24px;background:#f5fcfa}}
.provider-condition-discovery-v238 h2{{color:#075f5b}}
.provider-condition-discovery-v238__grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}}
.provider-condition-discovery-v238__grid article{{padding:1rem;border:1px solid #d4e9e5;border-radius:16px;background:#fff}}
.provider-condition-discovery-v238__grid h3{{margin-top:0;color:#74304f}}
.provider-condition-discovery-v238__grid a{{font-weight:800}}
.provider-condition-discovery-v238__gateway{{margin:2rem 0;padding:1.25rem;border:1px solid #b8ddd7;border-radius:18px;background:#effbf8}}
@media(max-width:900px){{.provider-condition-discovery-v238__grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
@media(max-width:620px){{.provider-condition-discovery-v238__grid{{grid-template-columns:1fr}}}}
</style>'''


def item_list_schema(records: list[dict[str, str]]) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "مسارات التقييم حسب الحالة",
        "numberOfItems": len(records),
        "itemListElement": [
            {"@type": "ListItem", "position": index, "name": record["title"], "url": record["url"]}
            for index, record in enumerate(records, 1)
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json" {SCHEMA_MARKER}>{encoded}</script>'


def render_directory(records: list[dict[str, str]]) -> str:
    cards = "".join(
        f'''<article><h3>{escape(record["title"])}</h3>
<p>مدخل مهني منظم يوضح نطاق التقييم ومصادر المعلومات والتكييفات وحدود تفسير النتائج.</p>
<a href="{escape(record["slug"])}/">فتح مسار {escape(record["title"])}</a></article>'''
        for record in records
    )
    return f'''{DIRECTORY_START}
<section class="provider-condition-discovery-v238" id="provider-condition-directory" aria-labelledby="provider-condition-directory-title">
<h2 id="provider-condition-directory-title">مسارات التقييم حسب الحالة</h2>
<p>روابط ثابتة وقابلة للفهرسة إلى المسارات العشرين. تُستخدم الصفحات لتنظيم سؤال الإحالة والفريق والمصادر والخطوات، ولا تحول أي أداة منفردة إلى تشخيص.</p>
<div class="provider-condition-discovery-v238__grid">{cards}</div>
</section>
{DIRECTORY_END}'''


def render_gateway() -> str:
    return f'''{GATEWAY_START}
<section class="provider-condition-discovery-v238__gateway" aria-labelledby="provider-training-gateway-title">
<h2 id="provider-training-gateway-title">أكاديمية التقييم المهني</h2>
<p>مساقات عملية للمراكز ومقدمي الخدمة حول اختيار الحزمة، الموافقة والخصوصية، التكييفات، دمج النتائج، التوثيق، التقارير، السلامة وضبط الجودة.</p>
<p><a href="training/">فتح أكاديمية التقييم المهني</a></p>
</section>
{GATEWAY_END}'''


def inject_directory_page(site: Path, records: list[dict[str, str]]) -> None:
    path = site / "provider-assessment-demo" / "conditions" / "index.html"
    if not path.is_file():
        raise ValueError(f"Missing provider condition index: {path}")
    source = path.read_text(encoding="utf-8")
    source = re.sub(rf'\s*<style\s+{re.escape(STYLE_MARKER)}.*?</style>\s*', "\n", source, flags=re.S)
    source = re.sub(
        rf'\s*<script\s+type=["\']application/ld\+json["\']\s+{re.escape(SCHEMA_MARKER)}.*?</script>\s*',
        "\n",
        source,
        flags=re.S,
    )
    if "</head>" not in source:
        raise ValueError("Provider condition index is missing </head>")
    source = insert_before_closing(source, "</head>", directory_style() + item_list_schema(records))
    source = replace_marker_block(source, DIRECTORY_START, DIRECTORY_END, render_directory(records))
    path.write_text(source, encoding="utf-8")


def inject_gateway_page(site: Path) -> None:
    path = site / "provider-assessment-demo" / "index.html"
    if not path.is_file():
        raise ValueError(f"Missing provider assessment gateway: {path}")
    source = path.read_text(encoding="utf-8")
    source = replace_marker_block(source, GATEWAY_START, GATEWAY_END, render_gateway())
    path.write_text(source, encoding="utf-8")


def qname(name: str) -> str:
    return f"{{{SITEMAP_NS}}}{name}"


def write_provider_sitemap(site: Path, records: list[dict[str, str]], lastmod: str) -> list[str]:
    urls = [
        f"{BASE}/provider-assessment-demo/",
        f"{BASE}/provider-assessment-demo/conditions/",
        *[record["url"] for record in records],
        f"{BASE}/provider-assessment-demo/training/",
    ]
    root = ET.Element(qname("urlset"))
    for url in urls:
        node = ET.SubElement(root, qname("url"))
        ET.SubElement(node, qname("loc")).text = url
        ET.SubElement(node, qname("lastmod")).text = lastmod
        ET.SubElement(node, qname("changefreq")).text = "monthly"
        ET.SubElement(node, qname("priority")).text = "0.85" if url.endswith("/conditions/") else "0.75"
    ET.ElementTree(root).write(site / SITEMAP_NAME, encoding="utf-8", xml_declaration=True)
    return urls


def sync_robots(site: Path) -> None:
    path = site / "robots.txt"
    child = f"Sitemap: {BASE}/{SITEMAP_NAME}"
    if path.is_file():
        lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
    else:
        lines = ["User-agent: *", "Allow: /"]
    lines = [line for line in lines if line != child]
    lines.append(child)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def validate(site: Path, records: list[dict[str, str]], urls: list[str]) -> dict[str, Any]:
    gateway = (site / "provider-assessment-demo" / "index.html").read_text(encoding="utf-8")
    directory = (site / "provider-assessment-demo" / "conditions" / "index.html").read_text(encoding="utf-8")
    training_path = site / "provider-assessment-demo" / "training" / "index.html"
    if not training_path.is_file():
        raise ValueError("Missing provider training page")
    training = training_path.read_text(encoding="utf-8")
    if f"{BASE}/provider-assessment-demo/training/" not in training or "noindex" in training.lower():
        raise ValueError("Provider training page indexability contract failed")
    if gateway.count(GATEWAY_START) != 1 or gateway.count('href="training/"') != 1:
        raise ValueError("Provider gateway link contract failed")
    if gateway.count('href="conditions/"') < 1:
        raise ValueError("Provider condition gateway link is missing")
    if directory.count(DIRECTORY_START) != 1:
        raise ValueError("Provider condition directory marker contract failed")
    if directory.count(STYLE_MARKER) != 1 or directory.count(SCHEMA_MARKER) != 1:
        raise ValueError("Provider condition directory metadata contract failed")
    missing = [record["slug"] for record in records if directory.count(f'href="{record["slug"]}/"') != 1]
    if missing:
        raise ValueError(f"Provider condition links are missing or duplicated: {missing}")
    sitemap = ET.parse(site / SITEMAP_NAME).getroot()
    locations = [(node.text or "").strip() for node in sitemap.findall("{*}url/{*}loc") if node.text]
    if locations != urls or len(locations) != len(set(locations)):
        raise ValueError("Provider condition sitemap route contract failed")
    robots = (site / "robots.txt").read_text(encoding="utf-8")
    if robots.count(f"Sitemap: {BASE}/{SITEMAP_NAME}") != 1:
        raise ValueError("Robots provider sitemap contract failed")
    return {
        "version": VERSION,
        "status": "passed",
        "condition_count": len(records),
        "gateway_links": 1,
        "directory_links": len(records),
        "training_links": 1,
        "sitemap_routes": len(urls),
        "robots_sitemap_registered": True,
        "root_sitemap_unchanged": True,
        "static_html_discovery": True,
        "javascript_required_for_discovery": False,
    }


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ValueError(f"Missing site directory: {site}")
    root_sitemap = site / "sitemap.xml"
    before = root_sitemap.read_bytes() if root_sitemap.is_file() else None
    records = discover_conditions(site)
    inject_directory_page(site, records)
    inject_gateway_page(site)
    urls = write_provider_sitemap(site, records, UPDATED)
    sync_robots(site)
    if before is not None and root_sitemap.read_bytes() != before:
        raise ValueError("Provider discovery publisher changed the root sitemap")
    report = validate(site, records, urls)
    output = site / "api" / "provider-condition-discovery-v238.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
