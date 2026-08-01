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
SPEC = importlib.util.spec_from_file_location("publish_magazine_v316", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MagazineResearchV316Tests(unittest.TestCase):
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
        self.assertEqual(len(pages), 79)
        self.assertEqual(MODULE.CONTRACT, 316)
        self.assertEqual(MODULE.TARGET_ARTICLES, 100)
        dates = [MODULE.article_date(path) for path in pages]
        self.assertEqual(dates, sorted(dates, reverse=True))

        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(report["version"], 316)
            self.assertEqual(report["research_summaries_published"], 79)
            self.assertEqual(report["target_research_summaries"], 100)
            self.assertEqual(report["remaining_to_target"], 21)
            self.assertTrue(report["continuous_publication_policy"])
            self.assertEqual(len(report["articles"]), 79)
            self.assertEqual(report["sitemap"]["child_urls"], 80)
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
            self.assertEqual(len(urls), 80)
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
            self.assertEqual(parsedate_to_datetime(feed_root.findtext("./channel/lastBuildDate")), feed_dates[0])

            saved = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["research_summaries_published"], 79)
            self.assertEqual(saved["target_research_summaries"], 100)
            self.assertEqual(set(saved["articles"]), {path.name for path in pages})

    def test_publish_is_idempotent_for_content_assets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            first = MODULE.publish(site)
            tracked = [site / "sitemap-magazine.xml", site / "magazine/index.html", site / "magazine/feed.xml"]
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
        self.assertIn('"numberOfItems":79', index)
        self.assertIn("79 قراءة علمية مستقلة", index)
        self.assertIn("الهدف المرحلي 100 قراءة", index)
        self.assertIn("المتبقي 21", index)
        self.assertIn('type="application/rss+xml"', index)
        self.assertEqual(index.count('class="card"'), 79)
        self.assertEqual(index.count('"@type":"ScholarlyArticle"'), 79)
        self.assertEqual(index.count('"datePublished"'), 79)
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
            "neurodevelopmental-disabilities-navigator-act-parent-stress-rct-2026.html": ("10.1002/aur.70282", "42187205", "d=0.84", "d=0.38", "لم تظهر فروق مهمة"),
            "adolescent-mental-health-artemis-cluster-rct-2026.html": ("10.1001/jamapsychiatry.2026.0603", "42054038", "OR=1.47", "p=0.10", "−0.87"),
            "autism-parents-mbsr-depression-anxiety-stress-rct-2026.html": ("10.1016/j.pedn.2026.05.008", "42166881", "96 والدًا ووالدة", "لم يظهر فرق دال"),
            "grieving-adolescents-alba-app-rct-2026.html": ("10.2196/94777", "42459115", "d=0.64", "لم يظهر أثر على النمو الشخصي"),
            "adolescent-school-guided-narrative-writing-cluster-rct-2026.html": ("10.1186/s12916-026-04816-w", "41888870", "211 طالبًا", "d=−0.22", "لم تظهر فروق دالة في الاكتئاب"),
            "autism-mentorship-program-pilot-rct-2026.html": ("10.1007/s10803-026-07272-w", "41774317", "24 مراهقًا", "23 جلسة أسبوعية", "الفاعلية النفسية: مؤشرات أولية فقط"),
            "college-digital-cbt-guided-self-help-rct-2026.html": ("10.1038/s41562-026-02454-z", "42098266", "6205 طلاب", "OR=0.77", "74.4%"),
        }
        for filename, markers in checks.items():
            text = (ROOT / "magazine" / filename).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text, filename)
            self.assertIn("<h2>المصدر الأصلي</h2>", text)
            self.assertIn('href="https://doi.org/', text)
            self.assertTrue(any(term in text for term in ("حدود", "الحذر", "قيود")))
            self.assertRegex(text, r'"datePublished":"2026-\d{2}-\d{2}"')
            if filename == "grieving-adolescents-alba-app-rct-2026.html":
                self.assertIn("<!-- pt-platform-shell:v1 -->", text)
                self.assertIn('data-pt-normalized="1.1.0"', text)
                self.assertIn('href="../copyright/"', text)
                self.assertIn('../assets/platform/platform-core.css?v=1.1.0', text)
                self.assertIn('../assets/platform/platform-core.js?v=1.1.0', text)


if __name__ == "__main__":
    unittest.main()
