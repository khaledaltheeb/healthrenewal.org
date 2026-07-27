#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import publish_evidence_literacy_library_v322_core as core
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


def publish(site: Path) -> dict:
    static_words = {
        slug: publish_static_page(site, slug, contract)
        for slug, contract in STATIC_PAGES.items()
    }
    publish_special_needs_sitemap(site)
    report = core.publish(site)
    core.update_sitemap(site, ["/trust/", "/start-here/"], report["reviewed_at"])
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
