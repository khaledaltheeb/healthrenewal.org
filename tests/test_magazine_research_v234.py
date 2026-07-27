from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_magazine_v201.py"
SPEC = importlib.util.spec_from_file_location("publish_magazine_v315", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MagazineResearchV315Tests(unittest.TestCase):
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
        self.assertEqual(len(pages), 72)
        self.assertEqual(MODULE.CONTRACT, 315)
        self.assertEqual(MODULE.TARGET_ARTICLES, 100)
        dates = [MODULE.article_date(path) for path in pages]
        self.assertEqual(dates, sorted(dates, reverse=True))

        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(report["version"], 315)
            self.assertEqual(report["research_summaries_published"], 72)
            self.assertEqual(report["target_research_summaries"], 100)
            self.assertEqual(report["remaining_to_target"], 28)
            self.assertTrue(report["continuous_publication_policy"])
            self.assertEqual(len(report["articles"]), 72)
            self.assertEqual(report["sitemap"]["child_urls"], 73)
            self.assertEqual(report["robots"]["rss_items"], 20)
            self.assertEqual(report["unwired_research_pages"], 0)
            self.assertEqual(report["index_contract"], "generated-from-discovered-articles-sorted-by-datePublished")
            self.assertEqual(report["rss_contract"], "latest-twenty-sorted-by-datePublished")
            self.assertEqual(report["article_dates"], {path.name: MODULE.article_date(path) for path in pages})

            magazine = site / "magazine"
            for path in pages:
                text = (magazine / path.name).read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', text)
                self.assertEqual(text.lower().count("<h1"), 1)
                self.assertTrue(any(heading in text for heading in ("المصدر الأصلي", "السجل الأصلي", "السجل الجامعي")))
                self.assertTrue(any(term in text for term in ("حدود", "قيود", "الحذر")))

            urls = [node.text for node in ET.parse(site / "sitemap-magazine.xml").getroot().findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), 73)
            self.assertEqual(len(urls), len(set(urls)))
            for path in pages:
                self.assertIn(MODULE.URL + path.name, urls)

            feed_root = ET.parse(magazine / "feed.xml").getroot()
            items = feed_root.findall("./channel/item")
            self.assertEqual(len(items), 20)
            feed_links = [item.findtext("link") for item in items]
            self.assertEqual(feed_links, [MODULE.URL + path.name for path in pages[:20]])
            feed_dates = [parsedate_to_datetime(item.findtext("pubDate")) for item in items]
            self.assertEqual(feed_dates, sorted(feed_dates, reverse=True))
            self.assertEqual(
                parsedate_to_datetime(feed_root.findtext("./channel/lastBuildDate")),
                feed_dates[0],
            )

            saved = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["research_summaries_published"], 72)
            self.assertEqual(saved["target_research_summaries"], 100)
            self.assertEqual(set(saved["articles"]), {path.name for path in pages})

    def test_publish_is_idempotent_for_content_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            first = MODULE.publish(site)
            tracked = [
                site / "sitemap-magazine.xml",
                site / "magazine/index.html",
                site / "magazine/feed.xml",
            ]
            before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            second = MODULE.publish(site)
            after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(before, after)
            self.assertTrue(first["sitemap"]["main_changed"])
            self.assertFalse(second["sitemap"]["main_changed"])

    def test_generated_index_is_dynamic_and_chronological(self) -> None:
        pages = MODULE.article_files()
        index = MODULE.render_index(pages)
        self.assertIn('"numberOfItems":72', index)
        self.assertIn("72 قراءة علمية مستقلة", index)
        self.assertIn("الهدف المرحلي 100 قراءة", index)
        self.assertIn("المتبقي 28", index)
        self.assertIn('type="application/rss+xml"', index)
        self.assertEqual(index.count('class="card"'), 72)
        self.assertEqual(index.count('"@type":"ScholarlyArticle"'), 72)
        self.assertEqual(index.count('"datePublished"'), 72)
        self.assertNotIn("ستون قراءة", index)
        card_positions = [index.index(f'href="{path.name}"') for path in pages]
        self.assertEqual(card_positions, sorted(card_positions))
        for path in pages:
            self.assertGreaterEqual(index.count(f'href="{path.name}"'), 2)
            self.assertIn(MODULE.URL + path.name, index)

    def test_scientific_batches_have_primary_sources_results_and_limits(self) -> None:
        checks = {
            "adhd-baduanjin-response-inhibition-rct-2026.html": ("10.1016/j.ridd.2026.105277", "41936141", "90 طفلًا"),
            "autism-structured-interactive-play-screening-cohort-2026.html": ("10.1186/s12888-026-08274-9", "42464217", "0.915"),
            "adolescent-depression-one-step-back-rct-2026.html": ("10.1016/j.eclinm.2026.103971", "42232686", "d=0.61"),
            "latinx-adolescent-suicidal-behavior-cbt-rct-2026.html": ("10.1080/15374416.2026.2687880", "42413031", "RR=0.50"),
            "adhd-personalized-neurofeedback-sham-rct-2026.html": ("10.1111/jcpp.70188", "42324882", "80.7%"),
            "autism-lets-play-caregiver-mediated-rct-2026.html": ("10.1007/s10803-026-07396-z", "42405995", "لم تظهر فروق دالة"),
            "autism-parent-reflective-functioning-rct-2026.html": ("10.1002/aur.70301", "42394366", "249 والدًا ووالدة"),
            "cerebral-palsy-participate-cp-leisure-rct-2026.html": ("10.1542/peds.2025-075162", "42425531", "2.75"),
            "down-syndrome-dual-task-exergaming-cognition-rct-2026.html": ("10.1016/j.psychsport.2026.103190", "42309334", "η²=0.31"),
            "adhd-dexamphetamine-methylphenidate-randomized-2026.html": ("10.1111/jpc.70487", "42415397", "−1.44"),
            "adhd-rhythmic-music-game-rct-2026.html": ("10.3389/fpubh.2026.1808386", "42145502", "−46.1"),
            "autism-aspen-low-resource-parent-intervention-rct-2026.html": ("10.3389/fpsyt.2026.1795918", "42404716", "50%", "p=0.026"),
        }
        for filename, markers in checks.items():
            text = (ROOT / "magazine" / filename).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text, filename)
            self.assertIn("<h2>المصدر الأصلي</h2>", text)
            self.assertIn('href="https://doi.org/', text)
            self.assertTrue(any(term in text for term in ("حدود", "الحذر", "قيود")))
            self.assertRegex(text, r'"datePublished":"2026-\d{2}-\d{2}"')

        aspen = (ROOT / "magazine" / "autism-aspen-low-resource-parent-intervention-rct-2026.html").read_text(encoding="utf-8")
        self.assertIn('data-pt-normalized="1.1.0"', aspen)
        self.assertIn('assets/platform/platform-core.css?v=1.1.0', aspen)
        self.assertIn('assets/platform/platform-core.js?v=1.1.0', aspen)
        self.assertIn('<meta name="copyright"', aspen)
        self.assertIn('<link rel="license" href="../copyright/">', aspen)


if __name__ == "__main__":
    unittest.main()
