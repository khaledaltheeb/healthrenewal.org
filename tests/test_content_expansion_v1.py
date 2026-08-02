#!/usr/bin/env python3
"""Regression gate for the evidence-guided 100-page content expansion."""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "data/content-expansion-v1.json").read_text(encoding="utf-8"))
REPORT_PATH = ROOT / "reports/content-expansion-v1.json"

ALLOWED_SOURCE_HOSTS = {
    "www.who.int", "www.ohchr.org", "www.unicef.org", "www.unesco.org",
    "www.asha.org", "www.resna.org", "www.nice.org.uk",
}


def word_count(markup: str) -> int:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", markup, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return len(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", text))


def normalized_body(markup: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", markup, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    assert REPORT_PATH.exists(), "Generator report is missing"
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["pageCount"] == 100
    assert report["distribution"] == MANIFEST["distribution"]
    assert len(report["pages"]) == 100

    paths = [item["path"] for item in report["pages"]]
    urls = [item["url"] for item in report["pages"]]
    titles = [item["title"] for item in report["pages"]]
    assert len(set(paths)) == len(set(urls)) == len(set(titles)) == 100

    observed = Counter(item["sector"] for item in report["pages"])
    assert dict(observed) == MANIFEST["distribution"]
    minimum_words = int(MANIFEST["minimum_page_words"])
    fingerprints: set[str] = set()
    sitemap_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.glob("sitemap*.xml") if path.is_file()
    )
    assert sitemap_text.strip(), "No sitemap XML files were generated"

    required_anchors = (
        'id="scope"', 'id="framework"', 'id="questions"', 'id="baseline"',
        'id="implementation"', 'id="environment"', 'id="communication"',
        'id="team"', 'id="measurement"', 'id="errors"', 'id="safety"',
        'id="plan"', 'id="checklist"', 'id="faq"', 'id="sources"',
    )

    for item in report["pages"]:
        path = ROOT / item["path"]
        assert path.exists(), item["path"]
        markup = path.read_text(encoding="utf-8")
        lowered = markup.lower()
        assert '<html lang="ar" dir="rtl">' in markup
        assert "<main" in lowered and "<article" in lowered
        assert markup.count("<h1") == 1
        assert '<link rel="canonical"' in lowered
        assert "application/ld+json" in lowered
        assert 'data-content-expansion="v1"' in markup
        assert "محتوى تثقيفي" in markup
        assert "لا تدّعي مراجعة سريرية خارجية" in markup
        assert "معاقين" not in markup
        assert "يحتاج عرض" not in markup
        assert "<noscript" not in lowered
        assert word_count(markup) >= minimum_words, (item["path"], word_count(markup))
        assert item["url"] in sitemap_text, f"Missing from sitemap: {item['url']}"

        source_block = re.search(r'id="sources".*?</section>', markup, flags=re.I | re.S)
        assert source_block, item["path"]
        hrefs = list(dict.fromkeys(re.findall(r'href=[\'\"](https://[^\'\"]+)[\'\"]', source_block.group(0))))
        assert len(hrefs) >= 4, (item["path"], hrefs)
        for href in hrefs:
            assert urlparse(href).netloc.lower() in ALLOWED_SOURCE_HOSTS, (item["path"], href)

        body = normalized_body(markup)
        fingerprint = body[:1200] + body[-1200:]
        assert fingerprint not in fingerprints, f"Duplicate page body: {item['path']}"
        fingerprints.add(fingerprint)
        for anchor in required_anchors:
            assert anchor in markup, (item["path"], anchor)

        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', markup, flags=re.I | re.S
        )
        assert blocks
        for block in blocks:
            json.loads(html.unescape(block))

    required_hubs = {
        "special-needs/guides/index.html": 70,
        "care-guides/evidence-guided/index.html": 12,
        "learning-paths/evidence-guided/index.html": 8,
        "comparisons/disability-support/index.html": 6,
        "daily-tools/disability-support/index.html": 4,
    }
    for relative, expected_count in required_hubs.items():
        path = ROOT / relative
        assert path.exists(), relative
        markup = path.read_text(encoding="utf-8")
        assert markup.count("<article>") == expected_count, (relative, markup.count("<article>"))

    for relative in (
        "special-needs/index.html", "care-guides/index.html", "learning-paths/index.html",
        "comparisons/index.html", "daily-tools/index.html",
    ):
        path = ROOT / relative
        if path.exists():
            markup = path.read_text(encoding="utf-8")
            assert markup.count("<!-- content-expansion-v1:start -->") == 1
            assert markup.count("<!-- content-expansion-v1:end -->") == 1

    assert report["minimumObservedWords"] >= minimum_words
    assert report["averageWords"] >= minimum_words
    print(json.dumps({
        "passed": True, "pages": report["pageCount"],
        "distribution": report["distribution"],
        "minimumWords": report["minimumObservedWords"],
        "averageWords": report["averageWords"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
