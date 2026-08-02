#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import html
import itertools
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "data/content-expansion-v1.json").read_text(encoding="utf-8"))
REPORT_PATH = ROOT / "reports/content-expansion-v1.json"
ALLOWED_SOURCE_HOSTS = {
    "www.who.int", "www.ohchr.org", "www.unicef.org", "www.unesco.org",
    "www.asha.org", "www.resna.org", "www.nice.org.uk", "www.w3.org",
    "udlguidelines.cast.org",
}
ALLOWED_DIFF_PATTERNS = (
    ".github/workflows/generate-content-expansion-v1.yml",
    "api/v1/content-expansion-v1.json",
    "care-guides/index.html", "care-guides/evidence-guided/**",
    "comparisons/index.html", "comparisons/disability-support/**",
    "daily-tools/index.html", "daily-tools/disability-support/**",
    "data/content-expansion-v1.json", "data/content-expansion-v1/**",
    "content/family-guide-special-education-tools-v1/**",
    "content/v406/women-youth-expansion-ar.json",
    "reports/source-evidence-contract-v1.json",
    "reports/sitemap-duplicate-ownership-v1.json",
    "scripts/migrate_source_reference_contract_v1.py",
    "scripts/fix_sitemap_duplicate_ownership_v1.py",
    "scripts/family_tools_v1_render.py",
    "scripts/publish_family_guide_special_education_tools_v1.py",
    "scripts/publish_women_youth_v406.py",
    "tests/test_family_guide_special_education_tools_v1.py",
    "sitemap-family-main.xml",
    "sitemap-family-sectors.xml",
    "learning-paths/index.html", "learning-paths/evidence-guided/**",
    "reports/content-expansion-v1.json",
    "scripts/generate_content_expansion_v1.py",
    "scripts/create_content_expansion_root_hubs_v1.py",
    "scripts/update_content_expansion_sitemaps_v1.py",
    "special-needs/index.html", "special-needs/guides/**",
    "tests/test_content_expansion_v1.py",
    "sitemap-family-special-needs.xml", "sitemap-family-care-guides.xml",
    "sitemap-family-learning-paths.xml", "sitemap-family-comparisons.xml",
    "sitemap-family-tools.xml", "sitemap-index.xml",
)


def word_count(markup: str) -> int:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", markup, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return len(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", text))


def tokens(markup: str) -> list[str]:
    text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", markup, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", text.lower())


def shingles(markup: str, size: int = 5) -> set[tuple[str, ...]]:
    words = tokens(markup)
    return {tuple(words[index:index + size]) for index in range(max(0, len(words) - size + 1))}


def run_lines(command: list[str]) -> list[str]:
    result = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_diff_scope() -> list[str]:
    # Validate files written by this generator in the current checkout. A PR can
    # legitimately contain other independently validated work (for example a
    # consolidated release), so the complete branch diff is not the generator's
    # mutation scope.
    changed = set(run_lines(["git", "diff", "--name-only"]))
    changed.update(run_lines(["git", "ls-files", "--others", "--exclude-standard"]))
    ordered = sorted(changed)
    unexpected = [
        path for path in ordered
        if not any(fnmatch.fnmatch(path, pattern) for pattern in ALLOWED_DIFF_PATTERNS)
    ]
    assert not unexpected, f"Unexpected files outside expansion scope: {unexpected[:20]}"
    return ordered


def normalize_citations(value) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def main() -> None:
    assert REPORT_PATH.exists(), "Generator report is missing"
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["pageCount"] == 100
    assert report["distribution"] == MANIFEST["distribution"]
    assert len(report["pages"]) == 100
    assert report.get("topicSpecificLayer") is True
    assert report.get("officialEvidenceLayer") is True
    assert report.get("officialEvidenceProfiles"), "Official evidence profile distribution is missing"

    paths = [item["path"] for item in report["pages"]]
    urls = [item["url"] for item in report["pages"]]
    titles = [item["title"] for item in report["pages"]]
    assert len(set(paths)) == len(set(urls)) == len(set(titles)) == 100
    assert dict(Counter(item["sector"] for item in report["pages"])) == MANIFEST["distribution"]

    sitemap_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ROOT.glob("sitemap*.xml") if path.is_file()
    )
    assert sitemap_text.strip()
    minimum_words = int(MANIFEST["minimum_page_words"])
    page_shingles: list[tuple[str, set[tuple[str, ...]]]] = []
    required_anchors = (
        'id="scope"', 'id="framework"', 'id="questions"', 'id="baseline"',
        'id="implementation"', 'id="environment"', 'id="communication"',
        'id="team"', 'id="measurement"', 'id="errors"', 'id="safety"',
        'id="plan"', 'id="checklist"', 'id="faq"', 'id="official-evidence"',
        'id="sources"',
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
        assert "<noscript" not in lowered
        assert word_count(markup) >= minimum_words, (item["path"], word_count(markup))
        assert item["url"] in sitemap_text, f"Missing from sitemap: {item['url']}"
        for anchor in required_anchors:
            assert anchor in markup, (item["path"], anchor)

        source_block = re.search(r'id="sources".*?</section>', markup, flags=re.I | re.S)
        assert source_block, item["path"]
        hrefs = list(dict.fromkeys(re.findall(r'href=[\'\"](https://[^\'\"]+)[\'\"]', source_block.group(0))))
        assert len(hrefs) >= 4, (item["path"], hrefs)
        for href in hrefs:
            assert urlparse(href).netloc.lower() in ALLOWED_SOURCE_HOSTS, (item["path"], href)

        profiles = item.get("evidenceProfiles") or []
        official_urls = item.get("officialEvidenceSources") or []
        assert profiles, f"No official evidence profile: {item['path']}"
        assert official_urls, f"No official evidence sources: {item['path']}"
        assert 'data-evidence-profiles="' in markup
        assert "official-evidence-profile-v1:start" in markup
        assert "official-evidence-profile-v1:end" in markup
        evidence_block = re.search(r'id="official-evidence".*?</section>', markup, flags=re.I | re.S)
        assert evidence_block, item["path"]
        evidence_hrefs = set(re.findall(r'href=[\'\"](https://[^\'\"]+)[\'\"]', evidence_block.group(0)))
        assert set(official_urls).issubset(evidence_hrefs), (item["path"], official_urls, evidence_hrefs)
        for href in official_urls:
            assert urlparse(href).netloc.lower() in ALLOWED_SOURCE_HOSTS, (item["path"], href)

        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', markup, flags=re.I | re.S)
        assert blocks
        structured_citations: set[str] = set()
        for block in blocks:
            payload = json.loads(html.unescape(block))
            if isinstance(payload, dict):
                structured_citations.update(normalize_citations(payload.get("citation")))
        assert set(official_urls).issubset(structured_citations), (
            item["path"], official_urls, sorted(structured_citations)
        )
        page_shingles.append((item["path"], shingles(markup)))

    maximum_similarity = 0.0
    maximum_pair = ("", "")
    for (left_path, left), (right_path, right) in itertools.combinations(page_shingles, 2):
        if not left or not right:
            continue
        score = len(left & right) / len(left | right)
        if score > maximum_similarity:
            maximum_similarity = score
            maximum_pair = (left_path, right_path)
    assert maximum_similarity < 0.78, (
        "Pages are too textually similar", round(maximum_similarity, 4), maximum_pair
    )

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

    for relative in ("care-guides/index.html", "comparisons/index.html", "daily-tools/index.html"):
        path = ROOT / relative
        assert path.exists(), f"Missing root hub: {relative}"
        markup = path.read_text(encoding="utf-8")
        assert '<link rel="canonical"' in markup.lower()
        assert "application/ld+json" in markup.lower()

    changed = validate_diff_scope()
    assert report["minimumObservedWords"] >= minimum_words
    assert report["averageWords"] >= minimum_words
    print(json.dumps({
        "passed": True, "pages": report["pageCount"],
        "distribution": report["distribution"],
        "minimumWords": report["minimumObservedWords"],
        "averageWords": report["averageWords"],
        "officialEvidenceProfiles": report["officialEvidenceProfiles"],
        "maximumFiveGramJaccard": round(maximum_similarity, 4),
        "mostSimilarPair": maximum_pair,
        "changedFileCount": len(changed),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
