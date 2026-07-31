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
MANIFEST = ROOT / "content" / "v209" / "special-needs-guides-manifest-ar.json"
GUIDE_DIR = ROOT / "content" / "v209" / "special-needs-guides"
PUBLISHER = ROOT / "scripts" / "publish_special_needs_guides_v209_compat.py"
BASE = "https://healthrenewal.org"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def visible_words(text: str) -> int:
    parser = VisibleText()
    parser.feed(text)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts)))


class SpecialNeedsGuidesV209Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="special-needs-guides-v209-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "special-needs").mkdir(parents=True)
        (site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>المركز</title></head>'
            '<body><main><section><div class="resources"></div></section></main></body></html>',
            encoding="utf-8",
        )
        sitemap = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>'
        (site / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        (site / "sitemap-special-needs.xml").write_text(sitemap, encoding="utf-8")
        return site

    def publish(self, site: Path) -> None:
        completed = subprocess.run(
            ["python3", str(PUBLISHER), str(site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_sources_are_complete_deep_and_authoritatively_sourced(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], 209)
        self.assertEqual(manifest["status"], "internally-reviewed")
        self.assertEqual(manifest["external_review"], "recommended-not-completed")
        self.assertEqual(len(manifest["guide_slugs"]), 5)
        self.assertEqual(len(set(manifest["guide_slugs"])), 5)
        self.assertGreaterEqual(len(manifest["sources"]), 8)
        allowed = {"www.unicef.org", "social.desa.un.org", "www.asha.org", "www.who.int", "www.w3.org"}
        for source in manifest["sources"].values():
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.netloc, allowed)
            self.assertTrue(source["use"].strip())

        all_text = json.dumps(manifest, ensure_ascii=False)
        for slug in manifest["guide_slugs"]:
            path = GUIDE_DIR / f"{slug}.json"
            self.assertTrue(path.is_file(), path)
            guide = json.loads(path.read_text(encoding="utf-8"))
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
            all_text += json.dumps(guide, ensure_ascii=False)
        self.assertIsNone(BANNED.search(all_text))

    def test_publisher_generates_five_deep_accessible_seo_pages(self) -> None:
        site = self.make_site()
        self.publish(site)
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for slug in manifest["guide_slugs"]:
            page = site / "special-needs" / slug / "index.html"
            self.assertTrue(page.is_file(), page)
            text = page.read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', text)
            self.assertEqual(len(re.findall(r"<h1\b", text)), 1)
            self.assertEqual(text.count('rel="canonical"'), 1)
            self.assertIn('application/ld+json', text)
            self.assertIn('property="og:title"', text)
            self.assertIn('name="twitter:card"', text)
            self.assertIn('<header>', text)
            self.assertIn('<footer>', text)
            self.assertIn("حدود الاستخدام", text)
            self.assertIn("متى نطلب مساعدة متخصصة؟", text)
            self.assertGreaterEqual(visible_words(text), 850, (slug, visible_words(text)))
            self.assertIsNone(BANNED.search(text))

        report = json.loads((site / "api/special-needs-guides-v209.json").read_text(encoding="utf-8"))
        self.assertEqual(report["guide_count"], 5)
        self.assertEqual(report["generated_page_count"], 5)
        self.assertEqual(report["source_count"], 9)
        self.assertGreaterEqual(report["minimum_source_words"], 750)
        self.assertTrue(report["hub_linked"])
        self.assertEqual(report["status"], "built-not-published")

    def test_hub_and_sitemaps_are_idempotent_and_duplicate_free(self) -> None:
        site = self.make_site()
        self.publish(site)
        first = (site / "special-needs/index.html").read_text(encoding="utf-8")
        self.publish(site)
        second = (site / "special-needs/index.html").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(second.count("special-needs-guides-v209:start"), 1)
        self.assertEqual(second.count("special-needs-guides-v209:end"), 1)
        self.assertEqual(second.count("فتح الدليل العملي"), 5)

        for sitemap_name in ("sitemap.xml", "sitemap-special-needs.xml"):
            root = ET.parse(site / sitemap_name).getroot()
            urls = [node.text for node in root.findall("sm:url/sm:loc", NS)]
            expected = [
                f"{BASE}/special-needs/{slug}/"
                for slug in json.loads(MANIFEST.read_text(encoding="utf-8"))["guide_slugs"]
            ]
            self.assertEqual(len(urls), len(set(urls)))
            for url in expected:
                self.assertEqual(urls.count(url), 1)

    def test_main_sitemapindex_registers_child_without_flattening(self) -> None:
        site = self.make_site()
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://healthrenewal.org/sitemap-core.xml</loc></sitemap>'
            '</sitemapindex>',
            encoding="utf-8",
        )
        self.publish(site)
        main = ET.parse(site / "sitemap.xml").getroot()
        self.assertEqual(main.tag.rsplit("}", 1)[-1], "sitemapindex")
        locations = [node.text for node in main.findall("sm:sitemap/sm:loc", NS)]
        self.assertIn(f"{BASE}/sitemap-core.xml", locations)
        self.assertEqual(locations.count(f"{BASE}/sitemap-special-needs.xml"), 1)
        report = json.loads((site / "api/special-needs-guides-v209.json").read_text(encoding="utf-8"))
        self.assertEqual(report["main_sitemap_mode"], "sitemapindex")


if __name__ == "__main__":
    unittest.main()
