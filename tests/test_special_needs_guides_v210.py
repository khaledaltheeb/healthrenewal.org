from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content" / "v210" / "special-needs-guides-manifest-ar.json"
GUIDE_DIR = ROOT / "content" / "v210" / "special-needs-guides"
PUBLISHER = ROOT / "scripts" / "publish_special_needs_guides_v210.py"
BASE = "https://healthrenewal.org"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


class SpecialNeedsGuidesV210Tests(unittest.TestCase):
    def load(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        guides = {
            slug: json.loads((GUIDE_DIR / f"{slug}.json").read_text(encoding="utf-8"))
            for slug in manifest["guide_slugs"]
        }
        return manifest, guides

    def make_site(self, *, sitemap_index: bool = False) -> Path:
        site = Path(tempfile.mkdtemp(prefix="special-needs-v210-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "special-needs").mkdir(parents=True)
        (site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main>'
            '<section><div class="resources"></div></section></main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            encoding="utf-8",
        )
        if sitemap_index:
            main = (
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                '<sitemap><loc>https://healthrenewal.org/sitemap-core.xml</loc></sitemap>'
                '</sitemapindex>'
            )
        else:
            main = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        (site / "sitemap.xml").write_text(main, encoding="utf-8")
        return site

    def run_publisher(self, site: Path) -> dict:
        completed = subprocess.run(
            ["python3", str(PUBLISHER), str(site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads((site / "api/special-needs-guides-v210.json").read_text(encoding="utf-8"))

    def test_sources_are_complete_deep_and_authoritative(self) -> None:
        manifest, guides = self.load()
        self.assertEqual(manifest["version"], 210)
        self.assertEqual(len(guides), 5)
        self.assertEqual(len(guides), len(set(guides)))
        for source in manifest["sources"].values():
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.netloc, {"www.who.int", "www.unicef.org", "www.aaidd.org"})
        for slug, guide in guides.items():
            self.assertEqual(guide["slug"], slug)
            self.assertEqual(guide["review_status"], "internally-reviewed")
            self.assertEqual(guide["external_review"], "recommended-not-completed")
            self.assertGreaterEqual(len(guide["sections"]), 5)
            self.assertTrue(all(len(section["paragraphs"]) >= 3 for section in guide["sections"]))
            self.assertGreaterEqual(len(guide["checklist"]), 7)
            self.assertGreaterEqual(len(guide["common_mistakes"]), 5)
            self.assertGreaterEqual(len(guide["template"]), 8)
            self.assertGreaterEqual(len(guide["source_ids"]), 2)
            source_words = len(re.findall(r"[\w\u0600-\u06ff]+", json.dumps(guide, ensure_ascii=False)))
            self.assertGreaterEqual(source_words, 750, (slug, source_words))
            self.assertGreaterEqual(len(guide["description"]), 90)
            self.assertLessEqual(len(guide["description"]), 180)
            self.assertIsNone(BANNED.search(json.dumps(guide, ensure_ascii=False)), slug)

    def test_publishes_five_searchable_pages_and_is_idempotent(self) -> None:
        site = self.make_site()
        first = self.run_publisher(site)
        second = self.run_publisher(site)
        self.assertEqual(first["guide_count"], 5)
        self.assertEqual(second["generated_page_count"], 5)
        self.assertGreaterEqual(first["minimum_source_words"], 750)
        hub = (site / "special-needs/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count("<!-- special-needs-guides-v210:start -->"), 1)
        self.assertEqual(hub.count("<!-- special-needs-guides-v210:end -->"), 1)
        for slug in json.loads(MANIFEST.read_text(encoding="utf-8"))["guide_slugs"]:
            page = (site / "special-needs" / slug / "index.html").read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', page)
            self.assertIn('rel="canonical"', page)
            self.assertIn("application/ld+json", page)
            self.assertIn("منصة الصحة النفسية وذوي الاحتياجات الخاصة", page)
            self.assertIn("متى نطلب مساعدة متخصصة؟", page)
            self.assertIsNone(BANNED.search(page), slug)
            parser = TextParser()
            parser.feed(page)
            visible_words = re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts))
            self.assertGreaterEqual(len(visible_words), 850, (slug, len(visible_words)))
        tree = ET.parse(site / "sitemap-special-needs.xml")
        locs = [node.text for node in tree.findall("sm:url/sm:loc", NS)]
        v210_locs = [loc for loc in locs if loc and any(slug in loc for slug in json.loads(MANIFEST.read_text(encoding="utf-8"))["guide_slugs"])]
        self.assertEqual(len(v210_locs), 5)
        self.assertEqual(len(v210_locs), len(set(v210_locs)))

    def test_preserves_sitemapindex_and_links_child_sitemap_once(self) -> None:
        site = self.make_site(sitemap_index=True)
        self.run_publisher(site)
        self.run_publisher(site)
        tree = ET.parse(site / "sitemap.xml")
        self.assertEqual(tree.getroot().tag.rsplit("}", 1)[-1], "sitemapindex")
        locs = [node.text for node in tree.findall("sm:sitemap/sm:loc", NS)]
        child = f"{BASE}/sitemap-special-needs.xml"
        self.assertEqual(locs.count(child), 1)


if __name__ == "__main__":
    unittest.main()
