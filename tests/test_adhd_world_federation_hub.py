from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org/"
PAGES = {
    "adhd/index.html": BASE + "adhd/",
    "adhd/federation-guide/index.html": BASE + "adhd/federation-guide/",
    "adhd/consensus/index.html": BASE + "adhd/consensus/",
    "adhd/transfer-of-care/index.html": BASE + "adhd/transfer-of-care/",
    "adhd/language-guide/index.html": BASE + "adhd/language-guide/",
    "adhd/adult-coaching/index.html": BASE + "adhd/adult-coaching/",
    "adhd/expert-questions/index.html": BASE + "adhd/expert-questions/",
    "adhd/practice-guidelines/index.html": BASE + "adhd/practice-guidelines/",
    "adhd/sources-and-rights/index.html": BASE + "adhd/sources-and-rights/",
}
REQUIRED = (
    '<html lang="ar" dir="rtl">',
    "<title>",
    'name="description"',
    'rel="canonical"',
    'name="robots"',
    'type="application/ld+json"',
    "World Federation",
)
BANNED_CLINICAL_FRAGMENTS = (
    "تناول حبة",
    "زد الجرعة",
    "اخفض الجرعة",
    "جرعة يومية مقدارها",
    "ملغ يوميًا",
    "mg daily",
)


def test_adhd_hub_pages_are_complete_attributed_and_safe() -> None:
    combined: list[str] = []
    for relative, canonical in PAGES.items():
        path = ROOT / relative
        assert path.is_file(), relative
        text = path.read_text(encoding="utf-8")
        assert all(marker in text for marker in REQUIRED), relative
        assert f'rel="canonical" href="{canonical}"' in text, relative
        assert "لا" in text and ("اعتماد" in text or "تأييد" in text or "تشخيص" in text), relative
        combined.append(text)

    joined = "\n".join(combined)
    assert not [fragment for fragment in BANNED_CLINICAL_FRAGMENTS if fragment.casefold() in joined.casefold()]
    assert len(re.findall(r"https://www\.adhd-federation\.org/", joined)) >= 12


def test_adhd_manifest_and_sitemaps_match_publication() -> None:
    manifest_path = ROOT / "api/adhd-world-federation-resources.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "published"
    assert manifest["permission"]["date"] == "2026-08-03"
    assert manifest["permission"]["reviewedOrEndorsedByFederation"] is False
    assert manifest["permission"]["logoUseAuthorized"] is False
    assert len(manifest["pages"]) == 10
    assert len(manifest["sources"]) >= 13
    assert manifest["safety"]["individualPrescribing"] is False
    assert manifest["safety"]["doseInstructionsPublished"] is False

    sitemap = ROOT / "sitemap-adhd.xml"
    tree = ET.parse(sitemap)
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = {node.text for node in tree.findall("s:url/s:loc", namespace)}
    expected = {item["url"] for item in manifest["pages"]}
    assert locations == expected

    index_tree = ET.parse(ROOT / "sitemap-index.xml")
    index_locations = {node.text for node in index_tree.findall("s:sitemap/s:loc", namespace)}
    assert BASE + "sitemap-adhd.xml" in index_locations


def test_internal_adhd_links_resolve_to_static_targets() -> None:
    href_pattern = re.compile(r'href="(/adhd/(?:[a-z0-9-]+/)?|/care-guides/adhd-family-practical-guide/)"')
    known = {
        "/adhd/": ROOT / "adhd/index.html",
        "/care-guides/adhd-family-practical-guide/": ROOT / "care-guides/adhd-family-practical-guide/index.html",
    }
    for relative in PAGES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        for href in href_pattern.findall(text):
            if href not in known:
                known[href] = ROOT / href.strip("/") / "index.html"
            assert known[href].is_file(), (relative, href)
