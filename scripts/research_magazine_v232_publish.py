#!/usr/bin/env python3
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from research_magazine_v232_core import BASE, CONTENT, MAGAZINE_URL, SITEMAP_NAME, article_url, load_data
from research_magazine_v232_render import render_article, render_index


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def write_sitemap(site: Path, data: dict) -> dict[str, object]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    urls = [MAGAZINE_URL] + [article_url(item) for item in data["summaries"]]
    root = ET.Element(f"{{{ns}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = data["verified_at"]
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "monthly" if url != MAGAZINE_URL else "weekly"
    child = site / SITEMAP_NAME
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)

    main_path = site / "sitemap.xml"
    if not main_path.is_file():
        raise SystemExit("Main sitemap is missing")
    tree = ET.parse(main_path)
    main = tree.getroot()
    mode = local_name(main.tag)
    changed = False
    if mode == "sitemapindex":
        child_url = BASE + "/" + SITEMAP_NAME
        existing = {(node.text or "").strip() for node in main.findall("{*}sitemap/{*}loc")}
        if child_url not in existing:
            item = ET.SubElement(main, qualify(main, "sitemap"))
            ET.SubElement(item, qualify(main, "loc")).text = child_url
            changed = True
    elif mode == "urlset":
        existing = {(node.text or "").strip() for node in main.findall("{*}url/{*}loc")}
        for url in urls:
            if url in existing:
                continue
            item = ET.SubElement(main, qualify(main, "url"))
            ET.SubElement(item, qualify(main, "loc")).text = url
            existing.add(url)
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {mode}")
    if changed:
        tree.write(main_path, encoding="utf-8", xml_declaration=True)
    return {"main_mode": mode, "main_changed": changed, "urls": len(urls)}


def publish(site: Path, content_path: Path = CONTENT) -> dict[str, object]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    data = load_data(content_path)
    magazine = site / "magazine"
    research = magazine / "research"
    research.mkdir(parents=True, exist_ok=True)
    (magazine / "index.html").write_text(render_index(data), encoding="utf-8")
    pages = []
    for item in data["summaries"]:
        target = research / item["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_article(item), encoding="utf-8")
        pages.append(str(target.relative_to(site)).replace("\\", "/"))
    sitemap = write_sitemap(site, data)
    topics = dict(sorted(Counter(item["topic"] for item in data["summaries"]).items()))
    years = dict(sorted(Counter(str(item["year"]) for item in data["summaries"]).items()))
    report = {
        "version": 232,
        "status": "published-to-build",
        "review_status": data["status"],
        "risk_level": data["risk_level"],
        "verified_at": data["verified_at"],
        "target_pages": data["target_pages"],
        "published_pages": len(pages),
        "index": "magazine/index.html",
        "pages": pages,
        "topics": topics,
        "years": years,
        "source_policy": "DOI and PubMed required; original Arabic editorial summaries; no copied abstracts",
        "sitemap": sitemap,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "research-magazine-v232.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    legacy_report = api / "magazine-v201.json"
    if legacy_report.is_file():
        legacy = json.loads(legacy_report.read_text(encoding="utf-8"))
        legacy["research_summaries_published"] = len(pages)
        legacy["research_publisher"] = 232
        legacy["research_report"] = "/api/research-magazine-v232.json"
        legacy_report.write_text(
            json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report
