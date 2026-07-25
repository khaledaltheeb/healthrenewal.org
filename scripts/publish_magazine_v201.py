#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v192" / "platform-institutional-foundation-ar.json"
SOURCE = ROOT / "magazine"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
URL = BASE + "/magazine/"
CONTRACT = 234

ARTICLES = (
    {
        "file": "mobile-stress-interventions-2025.html",
        "doi": "10.1038/s41562-025-02162-0",
        "evidence": ("63 تجربة", "20,454"),
    },
    {
        "file": "school-resilience-children-2025.html",
        "doi": "10.3389/fpsyt.2025.1594658",
        "pmid": "40458775",
        "evidence": ("مراجعة منهجية", "تجارب عشوائية"),
    },
    {
        "file": "youth-stigma-interventions-2025.html",
        "pmid": "39813031",
        "evidence": ("10–24", "التجارب العشوائية"),
    },
    {
        "file": "developmental-disabilities-school-support-2025.html",
        "doi": "10.1111/tmi.70000",
        "pmid": "40556074",
        "evidence": ("الدول منخفضة ومتوسطة الدخل", "حدود الدليل"),
    },
    {
        "file": "peer-led-adolescent-mental-health-2025.html",
        "doi": "10.1038/s41598-025-01053-8",
        "pmid": "40355577",
        "evidence": ("7,060", "لم يجد التحليل التلوي آثارًا دالة"),
    },
)


def load_methodology() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    if data.get("status") != "internally-reviewed" or data.get("risk_level") != "low":
        raise SystemExit("Magazine methodology must remain internally reviewed and low risk")
    return data


def validate_source_tree() -> dict[str, str]:
    required_files = ["index.html", "research.css", *(item["file"] for item in ARTICLES)]
    missing = [name for name in required_files if not (SOURCE / name).is_file()]
    if missing:
        raise SystemExit(f"Missing magazine source files: {missing}")

    index = (SOURCE / "index.html").read_text(encoding="utf-8")
    index_required = (
        '<html lang="ar" dir="rtl">',
        '<h1>المجلة والأبحاث</h1>',
        '<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/magazine/">',
        'application/ld+json',
        'research.css',
        'لا تُقدَّم النتائج بوصفها تشخيصًا',
    )
    absent = [marker for marker in index_required if marker not in index]
    if absent:
        raise SystemExit(f"Magazine index contract failed: {absent}")

    hashes: dict[str, str] = {}
    for item in ARTICLES:
        filename = item["file"]
        text = (SOURCE / filename).read_text(encoding="utf-8")
        canonical = f'<link rel="canonical" href="{URL}{filename}">'
        required = [
            '<html lang="ar" dir="rtl">',
            '<meta name="description"',
            canonical,
            '<link rel="stylesheet" href="research.css">',
            '<h1>',
            'المصدر الأصلي',
            'حدود الدليل',
        ]
        required.extend(item.get("evidence", ()))
        if item.get("doi"):
            required.extend((item["doi"], f'https://doi.org/{item["doi"]}'))
        if item.get("pmid"):
            required.append(item["pmid"])
        absent = [marker for marker in required if marker not in text]
        if absent:
            raise SystemExit(f"Research article contract failed for {filename}: {absent}")
        if len(re.findall(r"<h1\b", text, flags=re.I)) != 1:
            raise SystemExit(f"Research article must contain exactly one H1: {filename}")
        if any(term in text for term in ("يشخّص", "علاج مضمون", "نتائج مؤكدة للجميع")):
            raise SystemExit(f"Unsupported clinical claim in {filename}")
        if index.count(f'href="{filename}"') < 2:
            raise SystemExit(f"Magazine index does not expose article card and action: {filename}")
        hashes[filename] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return hashes


def publish_files(site: Path) -> None:
    target = site / "magazine"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "research.css", *(item["file"] for item in ARTICLES)):
        shutil.copy2(SOURCE / name, target / name)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def write_sitemaps(site: Path, reviewed_at: str) -> dict[str, object]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    urls = [URL, *(URL + item["file"] for item in ARTICLES)]
    child = site / "sitemap-magazine.xml"
    root = ET.Element(f"{{{ns}}}urlset")
    for target_url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = target_url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = reviewed_at
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "weekly"
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)

    main_path = site / "sitemap.xml"
    if not main_path.is_file():
        raise SystemExit("Main sitemap is missing")
    tree = ET.parse(main_path)
    main = tree.getroot()
    mode = local_name(main.tag)
    changed = False
    if mode == "urlset":
        existing = {(node.text or "").strip() for node in main.findall("{*}url/{*}loc")}
        for target_url in urls:
            if target_url in existing:
                continue
            item = ET.SubElement(main, qualify(main, "url"))
            ET.SubElement(item, qualify(main, "loc")).text = target_url
            existing.add(target_url)
            changed = True
    elif mode == "sitemapindex":
        child_url = BASE + "/sitemap-magazine.xml"
        existing = {(node.text or "").strip() for node in main.findall("{*}sitemap/{*}loc")}
        if child_url not in existing:
            item = ET.SubElement(main, qualify(main, "sitemap"))
            ET.SubElement(item, qualify(main, "loc")).text = child_url
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {mode}")
    if changed:
        tree.write(main_path, encoding="utf-8", xml_declaration=True)
    return {"main_mode": mode, "main_changed": changed, "child_urls": len(urls)}


def publish(site: Path) -> dict[str, object]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    data = load_methodology()
    hashes = validate_source_tree()
    publish_files(site)
    sitemap = write_sitemaps(site, data["reviewed_at"])
    report = {
        "version": CONTRACT,
        "page": "magazine/index.html",
        "url": URL,
        "methodology_published": True,
        "research_summaries_published": len(ARTICLES),
        "articles": [item["file"] for item in ARTICLES],
        "source_sha256": hashes,
        "review_status": data["status"],
        "risk_level": data["risk_level"],
        "sitemap": sitemap,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "magazine-v201.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    publish(Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve())
