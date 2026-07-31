from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sitemap_urls(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    urls = [
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if (node.text or "").strip()
    ]
    if len(urls) != len(set(urls)):
        raise AssertionError(f"Duplicate care-guide sitemap URLs: {path}")
    return urls


def main() -> None:
    report = read_json(SITE / "api/care-guides-v21.json")
    enhanced = read_json(SITE / "api/care-guides-v234.json")
    linked = read_json(SITE / "api/care-guides-homepage-v21.json")
    identity = read_json(SITE / "api/platform-identity-v201.json")
    targets = read_json(SITE / "api/content-targets-v201.json")

    expected_guides = report["guides"]
    expected_pages = report["pages"]
    expected_urls = report["sitemap_urls"]
    actual_pages = sum(1 for _ in (SITE / "care-guides").rglob("index.html"))
    parsed_urls = sitemap_urls(SITE / "sitemap-care-guides.xml")
    actual_urls = len(parsed_urls)

    assert expected_guides >= 1, report
    assert expected_pages == expected_guides + 1, report
    assert expected_urls == expected_pages, report
    assert actual_pages == expected_pages, (actual_pages, report)
    assert actual_urls == expected_urls, (actual_urls, report, parsed_urls)
    assert all(url.startswith("https://healthrenewal.org/care-guides/") for url in parsed_urls), parsed_urls
    assert report["all_have_sources"] and report["all_have_unique_titles"]
    assert enhanced["status"] == "passed" and enhanced["published_pages"] == expected_pages, enhanced
    assert enhanced["sitemap_urls"] == expected_urls and enhanced["pages_with_keywords"] == expected_pages, enhanced
    assert enhanced["pages_with_faq_schema"] == expected_pages and enhanced["pages_with_single_h1"] == expected_pages, enhanced
    assert enhanced["specialist_review_gate_preserved"] and not enhanced["duplicate_ids"], enhanced
    assert linked["care_guides_linked"] and linked["navigation_link"] and linked["hero_link"]
    assert "sitemap-care-guides.xml" in (SITE / "sitemap.xml").read_text(encoding="utf-8")
    assert 'href="care-guides/"' in (SITE / "index.html").read_text(encoding="utf-8")
    assert identity["remaining_banned_pages"] == [], identity
    assert identity["missing_header_pages"] == [], identity
    assert identity["missing_footer_pages"] == [], identity
    assert targets["targets"]["care_guides"]["published_count"] == expected_guides, targets["targets"]["care_guides"]

    pages = sorted((SITE / "care-guides").glob("*/index.html"))
    assert len(pages) == expected_guides, (len(pages), report)
    titles: set[str] = set()
    descriptions: set[str] = set()
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert len(re.findall(r"<h1(?:\s|>)", text, re.I)) == 1, page
        assert "application/ld+json" in text and "HowTo" in text and "Article" in text, page
        assert "FAQPage" in text and "care-toc" in text, page
        assert "مصادر مؤسسية للمراجعة" in text, page
        assert "خدمات الطوارئ المحلية" in text or "مساعدة عاجلة" in text, page
        title_match = re.search(r"<title>(.*?)</title>", text, re.S)
        description_match = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
        assert title_match and description_match, page
        title = title_match.group(1)
        description = description_match.group(1)
        assert title not in titles and description not in descriptions, page
        titles.add(title)
        descriptions.add(description)

    result = {
        "version": 235,
        "status": "passed",
        "guides": len(pages),
        "pages": actual_pages,
        "sitemap_urls": actual_urls,
        "sitemap_parser": "xml-namespace-aware",
        "unique_titles": len(titles),
        "unique_descriptions": len(descriptions),
        "identity_pages": identity["pages"],
        "specialist_review_gate_preserved": enhanced["specialist_review_gate_preserved"],
        "external_specialist_review_completed": False,
    }
    output = SITE / "api/care-guides-publication-verification-v234.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
