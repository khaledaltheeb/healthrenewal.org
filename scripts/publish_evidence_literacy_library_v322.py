#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import publish_evidence_literacy_library_v322_core as core
from publish_academic_library_v326 import publish as publish_academic_library
from publish_evidence_literacy_library_v322_core import *  # noqa: F401,F403

ROOT = Path(__file__).resolve().parents[1]
SPECIAL_NEEDS_SITEMAP = ROOT / "sitemap-special-needs.xml"
STATIC_PAGES = {
    "trust": {
        "source": ROOT / "trust" / "index.html",
        "minimum_words": 1100,
        "canonical": 'rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/trust/"',
        "review_phrase": "لم تكتمل مراجعة خارجية مستقلة",
    },
    "start-here": {
        "source": ROOT / "start-here" / "index.html",
        "minimum_words": 900,
        "canonical": 'rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/start-here/"',
        "review_phrase": "المعلومات التثقيفية تساعد على الفهم",
    },
    "special-needs": {
        "source": ROOT / "special-needs" / "index.html",
        "minimum_words": 1300,
        "canonical": 'rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/special-needs/"',
        "review_phrase": "الاحتياج لا يلغي القدرة",
    },
}


def publish_static_page(site: Path, slug: str, contract: dict) -> int:
    source_path = contract["source"]
    if not source_path.is_file():
        raise SystemExit(f"Missing institutional source page: {source_path}")
    target = site / slug / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    source = target.read_text(encoding="utf-8")
    page_words = core.words(source)
    if page_words < int(contract["minimum_words"]) or source.count("<h1") != 1:
        raise SystemExit({"institutional_page_depth_failed": {"slug": slug, "words": page_words}})
    if contract["canonical"] not in source:
        raise SystemExit(f"Institutional page canonical contract failed: {slug}")
    if "application/ld+json" not in source or contract["review_phrase"] not in source:
        raise SystemExit(f"Institutional page structure or boundary disclosure failed: {slug}")
    if core.BANNED.search(source):
        raise SystemExit(f"Banned terminology rendered in institutional page: {slug}")
    return page_words


def publish_special_needs_sitemap(site: Path) -> None:
    if not SPECIAL_NEEDS_SITEMAP.is_file():
        raise SystemExit(f"Missing special-needs sitemap source: {SPECIAL_NEEDS_SITEMAP}")
    target = site / "sitemap-special-needs.xml"
    shutil.copy2(SPECIAL_NEEDS_SITEMAP, target)
    root = ET.parse(target).getroot()
    if root.tag.rsplit("}", 1)[-1] != "urlset":
        raise SystemExit("Special-needs sitemap must be a urlset")
    urls = [
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if node.text
    ]
    expected = "https://khaledaltheeb.github.io/pterminology-site/special-needs/"
    if urls.count(expected) != 1 or len(urls) != len(set(urls)):
        raise SystemExit("Special-needs sitemap foundation contract failed")


def trim_academic_sitemap_to_new_entries(site: Path) -> int:
    path = site / "sitemap-library-academic-v326.xml"
    if not path.is_file():
        raise SystemExit(f"Missing academic sitemap: {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    if root.tag.rsplit("}", 1)[-1] != "urlset":
        raise SystemExit("Academic library sitemap must be a urlset")

    already_registered = {
        "https://khaledaltheeb.github.io/pterminology-site/library/",
        "https://khaledaltheeb.github.io/pterminology-site/library/branches/",
        "https://khaledaltheeb.github.io/pterminology-site/library/therapies/",
        "https://khaledaltheeb.github.io/pterminology-site/library/research/",
    }
    removed: set[str] = set()
    for node in list(root.findall("{*}url")):
        loc = node.find("{*}loc")
        url = (loc.text or "").strip() if loc is not None else ""
        if url in already_registered:
            root.remove(node)
            removed.add(url)

    urls = [
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if node.text
    ]
    if removed != already_registered:
        raise SystemExit({"academic_sitemap_expected_duplicates_not_found": sorted(already_registered - removed)})
    if len(urls) != 80 or len(urls) != len(set(urls)):
        raise SystemExit({"academic_sitemap_entry_contract_failed": {"count": len(urls), "unique": len(set(urls))}})
    if any(url.count("/") < 6 for url in urls):
        raise SystemExit("Academic sitemap contains a non-entry route")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return len(urls)


def restore_evidence_library_parent_contract(site: Path) -> None:
    path = site / "library" / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing academic library index: {path}")
    source = path.read_text(encoding="utf-8")
    marker = core.PARENT_MARKER

    footer_link = f' · <a href="{core.BP}library/evidence-literacy/">الثقافة العلمية</a>'
    if footer_link in source:
        source = source.replace(footer_link, "", 1)

    section_needle = '<section class="wrap grid">'
    section_replacement = f'<section class="wrap grid" {marker}>'
    if marker not in source:
        if source.count(section_needle) != 1:
            raise SystemExit({"evidence_parent_section_contract_failed": source.count(section_needle)})
        source = source.replace(section_needle, section_replacement, 1)

    evidence_url = f'{core.BP}library/evidence-literacy/'
    if source.count(marker) != 1 or source.count(evidence_url) != 1:
        raise SystemExit(
            {
                "evidence_parent_contract_failed": {
                    "markers": source.count(marker),
                    "links": source.count(evidence_url),
                }
            }
        )
    path.write_text(source, encoding="utf-8")


def ensure_academic_seo_keyword_seed(site: Path) -> None:
    path = site / "library" / "therapies" / "psychoeducation" / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing psychoeducation entry: {path}")
    source = path.read_text(encoding="utf-8")
    marker = 'name="keywords"'
    keyword_tag = (
        '<meta name="keywords" content="برامج التثقيف النفسي المنظمة, '
        'خطة الوقاية من الانتكاس, دعم الأسرة في العلاج النفسي">'
    )
    if marker not in source:
        if source.count("</head>") != 1:
            raise SystemExit("Psychoeducation page must contain exactly one closing head tag")
        source = source.replace("</head>", keyword_tag + "</head>", 1)
        path.write_text(source, encoding="utf-8")
    updated = path.read_text(encoding="utf-8")
    if updated.count(marker) != 1 or "برامج التثقيف النفسي المنظمة" not in updated:
        raise SystemExit("Psychoeducation SEO keyword seed contract failed")


def publish(site: Path) -> dict:
    static_words = {
        slug: publish_static_page(site, slug, contract)
        for slug, contract in STATIC_PAGES.items()
    }
    publish_special_needs_sitemap(site)
    report = core.publish(site)
    core.update_sitemap(site, ["/trust/", "/start-here/"], report["reviewed_at"])

    academic = publish_academic_library(site)
    expected_sections = {"branches": 25, "therapies": 27, "research": 28}
    if academic.get("version") != 326 or academic.get("status") != "passed":
        raise SystemExit({"invalid_academic_library_v326": academic})
    if academic.get("sections") != expected_sections:
        raise SystemExit({"academic_library_section_contract_failed": academic})
    if academic.get("total_entries") != 80 or academic.get("generated_pages") != 84:
        raise SystemExit({"academic_library_inventory_failed": academic})
    if int(academic.get("minimum_page_words", 0)) < 180:
        raise SystemExit({"academic_library_depth_failed": academic})
    academic_sitemap_entries = trim_academic_sitemap_to_new_entries(site)
    restore_evidence_library_parent_contract(site)
    ensure_academic_seo_keyword_seed(site)

    report.update(
        {
            "trust_page_published": True,
            "trust_page_path": "trust/index.html",
            "trust_page_words": static_words["trust"],
            "trust_page_review_status": "internally-reviewed-external-methodology-review-required",
            "trust_page_sitemap_registered": True,
            "start_here_page_published": True,
            "start_here_page_path": "start-here/index.html",
            "start_here_page_words": static_words["start-here"],
            "start_here_page_sitemap_registered": True,
            "special_needs_hub_published": True,
            "special_needs_hub_path": "special-needs/index.html",
            "special_needs_hub_words": static_words["special-needs"],
            "special_needs_hub_review_status": "internally-reviewed-external-specialist-review-required",
            "special_needs_sitemap_published": True,
            "academic_library_version": academic["version"],
            "academic_library_review_status": academic["review_status"],
            "academic_library_sections": academic["sections"],
            "academic_library_total_entries": academic["total_entries"],
            "academic_library_generated_pages": academic["generated_pages"],
            "academic_library_minimum_page_words": academic["minimum_page_words"],
            "academic_library_source_registry": academic["source_registry"],
            "academic_library_sitemap": academic["sitemap"],
            "academic_library_sitemap_entries": academic_sitemap_entries,
            "evidence_library_parent_marker_preserved": True,
            "academic_library_seo_keyword_seeded": True,
        }
    )
    api_path = site / "api" / "evidence-literacy-library-v322.json"
    api_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing site directory: {args.site}")
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
