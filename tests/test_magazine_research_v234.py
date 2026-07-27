from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_magazine_v201.py"
SPEC = importlib.util.spec_from_file_location("publish_magazine_v313", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MagazineResearchV313Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        site.mkdir()
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
            encoding="utf-8",
        )
        return site

    def test_publishes_every_discovered_article_rss_and_sitemap(self) -> None:
        pages = MODULE.article_files()
        self.assertEqual(len(pages), 65)
        self.assertEqual(MODULE.CONTRACT, 313)
        self.assertEqual(MODULE.TARGET_ARTICLES, 100)
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(report["version"], 313)
            self.assertEqual(report["research_summaries_published"], 65)
            self.assertEqual(report["target_research_summaries"], 100)
            self.assertEqual(report["remaining_to_target"], 35)
            self.assertTrue(report["continuous_publication_policy"])
            self.assertEqual(len(report["articles"]), 65)
            self.assertEqual(report["sitemap"]["child_urls"], 66)
            self.assertEqual(report["robots"]["rss_items"], 20)
            self.assertEqual(report["unwired_research_pages"], 0)

            magazine = site / "magazine"
            for path in pages:
                text = (magazine / path.name).read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', text)
                self.assertEqual(text.lower().count("<h1"), 1)
                self.assertTrue(any(heading in text for heading in ("المصدر الأصلي", "السجل الأصلي", "السجل الجامعي")))
                self.assertTrue(any(term in text for term in ("حدود", "قيود", "الحذر")))

            urls = [node.text for node in ET.parse(site / "sitemap-magazine.xml").getroot().findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), 66)
            self.assertEqual(len(urls), len(set(urls)))
            for path in pages:
                self.assertIn(MODULE.URL + path.name, urls)

            items = ET.parse(magazine / "feed.xml").getroot().findall("./channel/item")
            self.assertEqual(len(items), 20)
            feed_links = [item.findtext("link") for item in items]
            self.assertEqual(len(feed_links), len(set(feed_links)))
            for path in pages[:20]:
                self.assertIn(MODULE.URL + path.name, feed_links)

            saved = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["research_summaries_published"], 65)
            self.assertEqual(saved["target_research_summaries"], 100)
            self.assertEqual(set(saved["articles"]), {path.name for path in pages})

    def test_publish_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            first = MODULE.publish(site)
            tracked = [
                site / "sitemap-magazine.xml",
                site / "magazine/index.html",
                site / "magazine/feed.xml",
                site / "api/magazine-v201.json",
            ]
            before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            second = MODULE.publish(site)
            after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(before, after)

    def test_generated_index_is_dynamic(self) -> None:
        pages = MODULE.article_files()
        index = MODULE.render_index(pages)
        self.assertIn('"numberOfItems":65', index)
        self.assertIn("65 قراءة علمية مستقلة", index)
        self.assertIn("الهدف المرحلي 100 قراءة", index)
        self.assertIn("المتبقي 35", index)
        self.assertIn('type="application/rss+xml"', index)
        self.assertEqual(index.count('class="card"'), 65)
        self.assertEqual(index.count('"@type":"ScholarlyArticle"'), 65)
        self.assertNotIn("ستون قراءة", index)
        for path in pages:
            self.assertGreaterEqual(index.count(f'href="{path.name}"'), 2)
            self.assertIn(MODULE.URL + path.name, index)

    def test_new_batch_has_primary_sources_results_and_limits(self) -> None:
        checks = {
            "adhd-baduanjin-response-inhibition-rct-2026.html": ("10.1016/j.ridd.2026.105277", "41936141", "90 طفلًا"),
            "autism-structured-interactive-play-screening-cohort-2026.html": ("10.1186/s12888-026-08274-9", "42464217", "0.915"),
            "adolescent-depression-one-step-back-rct-2026.html": ("10.1016/j.eclinm.2026.103971", "42232686", "d=0.61"),
            "latinx-adolescent-suicidal-behavior-cbt-rct-2026.html": ("10.1080/15374416.2026.2687880", "42413031", "RR=0.50"),
            "adhd-personalized-neurofeedback-sham-rct-2026.html": ("10.1111/jcpp.70188", "42324882", "80.7%"),
        }
        for filename, markers in checks.items():
            text = (ROOT / "magazine" / filename).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text, filename)
            self.assertIn("<h2>المصدر الأصلي</h2>", text)
            self.assertIn('href="https://doi.org/', text)
            self.assertTrue(any(term in text for term in ("حدود", "الحذر", "قيود")))


if __name__ == "__main__":
    unittest.main()
