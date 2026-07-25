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
MIN_ARTICLES = 21
SOURCE_LINK_PATTERN = re.compile(
    r'href="https://(?:doi\.org/|pubmed\.ncbi\.nlm\.nih\.gov/|etheses\.whiterose\.ac\.uk/|research-repository\.uwa\.edu\.au/)',
    re.I,
)
SOURCE_HEADING_PATTERN = re.compile(
    r'<h2>(?:المصدر الأصلي|السجل الأصلي|السجل الجامعي|السجل الجامعي الأصلي)</h2>',
    re.I,
)
LIMITATION_HEADING_PATTERN = re.compile(
    r'<h2>[^<]*(?:حدود|قيود|الحذر)[^<]*</h2>',
    re.I,
)
KNOWN_MARKERS = {
    "peer-led-adolescent-mental-health-2025.html": ("7,060", "لم يجد التحليل التلوي آثارًا دالة", "ست دراسات من أصل سبع"),
    "adhd-school-social-skills-meta-analysis-2026.html": ("10.1177/10870547251364578", "40905635", "0.09"),
    "intensive-community-care-adolescents-2026.html": ("10.1016/j.jaac.2026.01.006", "41580120", "16,546"),
    "neurodivergent-university-mental-health-interventions-2026.html": ("10.1038/s44184-026-00196-4", "41741588", "37 دراسة"),
    "thesis-autism-heterogeneity-research-2025.html": ("38156", "51 ورقة", "حتى 1 مارس 2028"),
    "thesis-autistic-camouflaging-mental-health-2025.html": ("10.26182/pez7-d531", "دراسة مقطعية", "دراسة طولية"),
    "thesis-sensory-processing-adhd-autism-2026.html": ("38725", "3 دراسات تجريبية", "حتى 6 مايو 2027"),
    "autism-social-functioning-meta-analysis-2026.html": ("10.1038/s41562-026-02457-w", "2,622 دراسة", "−0.744"),
    "autism-ssri-children-meta-analysis-2026.html": ("10.1177/11795565261442820", "606 مشاركين", "GRADE"),
    "adhd-screen-time-meta-analysis-2026.html": ("10.1080/24694193.2026.2640837", "235,283", "يقين منخفض"),
    "adhd-technology-interventions-meta-analysis-2026.html": ("10.1080/01942638.2026.2689070", "0.24", "I² = 68.3%"),
    "adhd-physical-fitness-meta-analysis-2026.html": ("10.1016/j.arcped.2026.105583", "1,814", "−0.46"),
    "autism-sleep-disorders-prevalence-meta-analysis-2026.html": ("10.1186/s12888-026-08191-x", "60.0%", "I² = 98.8%"),
}


def article_files() -> list[Path]:
    pages = sorted(path for path in SOURCE.glob("*-20*.html") if path.name != "index.html")
    if len(pages) < MIN_ARTICLES:
        raise SystemExit(f"Magazine requires at least {MIN_ARTICLES} research pages, found {len(pages)}")
    return pages


def load_methodology() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    if data.get("status") != "internally-reviewed" or data.get("risk_level") != "low":
        raise SystemExit("Magazine methodology must remain internally reviewed and low risk")
    return data


def validate_source_tree(pages: list[Path]) -> dict[str, str]:
    for name in ("index.html", "research.css"):
        if not (SOURCE / name).is_file():
            raise SystemExit(f"Missing magazine source file: {name}")

    index = (SOURCE / "index.html").read_text(encoding="utf-8")
    expected_count = len(pages)
    required_index = (
        '<html lang="ar" dir="rtl">',
        '<h1>المجلة والأبحاث</h1>',
        '<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/magazine/">',
        'application/ld+json',
        'research.css',
        f'"numberOfItems":{expected_count}',
    )
    missing = [marker for marker in required_index if marker not in index]
    if missing:
        raise SystemExit(f"Magazine index contract failed: {missing}")
    if index.count('class="card"') != expected_count:
        raise SystemExit(
            f"Magazine index must expose {expected_count} cards, found {index.count('class=\"card\"')}"
        )

    hashes: dict[str, str] = {}
    for path in pages:
        filename = path.name
        text = path.read_text(encoding="utf-8")
        required = (
            '<html lang="ar" dir="rtl">',
            '<meta name="description"',
            f'<link rel="canonical" href="{URL}{filename}">',
            '<link rel="stylesheet" href="research.css">',
            '<h1>',
        )
        absent = [marker for marker in required if marker not in text]
        absent.extend(marker for marker in KNOWN_MARKERS.get(filename, ()) if marker not in text)
        if absent:
            raise SystemExit(f"Research article contract failed for {filename}: {absent}")
        if not SOURCE_HEADING_PATTERN.search(text):
            raise SystemExit(f"Research article lacks an approved original-source heading: {filename}")
        if not LIMITATION_HEADING_PATTERN.search(text):
            raise SystemExit(f"Research article lacks a limitations or caution section: {filename}")
        if len(re.findall(r"<h1\b", text, flags=re.I)) != 1:
            raise SystemExit(f"Research article must contain exactly one H1: {filename}")
        if not SOURCE_LINK_PATTERN.search(text):
            raise SystemExit(f"Research article lacks an approved original-source link: {filename}")
        if any(term in text for term in ("يشخّص", "علاج مضمون", "نتائج مؤكدة للجميع")):
            raise SystemExit(f"Unsupported clinical claim in {filename}")
        if index.count(f'href="{filename}"') < 2:
            raise SystemExit(f"Magazine index must expose article twice: {filename}")
        if URL + filename not in index:
            raise SystemExit(f"Magazine JSON-LD does not include article: {filename}")
        hashes[filename] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return hashes


def publish_files(site: Path, pages: list[Path]) -> None:
    target = site / "magazine"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE / "index.html", target / "index.html")
    shutil.copy2(SOURCE / "research.css", target / "research.css")
    for path in pages:
        shutil.copy2(path, target / path.name)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def write_sitemaps(site: Path, reviewed_at: str, pages: list[Path]) -> dict[str, object]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    urls = [URL, *(URL + path.name for path in pages)]
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
            if target_url not in existing:
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
    pages = article_files()
    hashes = validate_source_tree(pages)
    publish_files(site, pages)
    sitemap = write_sitemaps(site, data["reviewed_at"], pages)
    report = {
        "version": CONTRACT,
        "page": "magazine/index.html",
        "url": URL,
        "methodology_published": True,
        "research_summaries_published": len(pages),
        "articles": [path.name for path in pages],
        "source_sha256": hashes,
        "review_status": data["status"],
        "risk_level": data["risk_level"],
        "unwired_research_pages": 0,
        "source_heading_contract": "article-or-official-repository",
        "limitations_contract": "limitations-or-cautions-required",
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
