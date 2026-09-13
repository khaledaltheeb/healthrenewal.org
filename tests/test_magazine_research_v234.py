from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_magazine_v202.py"
SPEC = importlib.util.spec_from_file_location("publish_magazine_v202_tests", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MagazineResearchV202Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        site.mkdir()
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
            encoding="utf-8",
        )
        return site

    def test_recursive_inventory_index_and_feed_cover_all_studies(self) -> None:
        records, manifest = MODULE.article_records()
        expected = len(records)
        self.assertGreaterEqual(expected, 193)
        self.assertEqual(MODULE.CONTRACT, 202)
        self.assertEqual(MODULE.TARGET_ARTICLES, 500)
        self.assertEqual(manifest["summary"]["study_pages"], expected)
        self.assertEqual(manifest["summary"]["missing_source"], 0)
        self.assertEqual(manifest["summary"]["noindex_pages"], 0)
        self.assertEqual(manifest["summary"]["unclassified_nested_indexes"], 0)
        self.assertTrue(any("/" in record.relative_path for record in records))
        self.assertTrue(
            any(
                record.relative_path
                == "pediatric-oncology/theses/bridging-gap-hct-success-troullioud-lucas-2026/index.html"
                for record in records
            )
        )
        dates = [record.date_published for record in records]
        self.assertEqual(dates, sorted(dates, reverse=True))

        index = MODULE.render_index(records, manifest)
        self.assertEqual(index.count('class="card"'), expected)
        self.assertEqual(index.count('class="read"'), expected)
        self.assertIn(f'"numberOfItems":{expected}', index)
        self.assertIn('<link rel="stylesheet" href="research.css">', index)
        self.assertNotIn("javascript:void", index.lower())
        for record in records:
            self.assertGreaterEqual(index.count(f'href="{record.url}"'), 2, record.relative_path)

        feed = MODULE.render_feed(records)
        root = ET.fromstring(feed)
        items = root.findall("./channel/item")
        self.assertEqual(len(items), min(MODULE.FEED_LIMIT, expected))
        self.assertEqual(
            [item.findtext("link") for item in items],
            [record.url for record in records[: MODULE.FEED_LIMIT]],
        )
        feed_dates = [parsedate_to_datetime(item.findtext("pubDate")) for item in items]
        self.assertEqual(feed_dates, sorted(feed_dates, reverse=True))
        self.assertEqual(parsedate_to_datetime(root.findtext("./channel/lastBuildDate")), feed_dates[0])

    def test_v202_publisher_preserves_nested_routes_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            first = MODULE.publish(site)
            self.assertGreaterEqual(first["published_study_pages"], 193)
            self.assertEqual(first["published_study_pages"], first["index_cards"])
            self.assertEqual(first["published_study_pages"], first["wired_study_pages"])
            self.assertEqual(first["unwired_research_pages"], 0)
            self.assertEqual(first["missing_source_pages"], 0)
            self.assertEqual(first["validation"]["noindex_pages"], 0)
            self.assertEqual(first["validation"]["duplicate_canonical_urls"], 0)
            self.assertTrue(
                (
                    site
                    / "magazine/pediatric-oncology/theses/bridging-gap-hct-success-troullioud-lucas-2026/index.html"
                ).is_file()
            )
            tracked = [
                site / "sitemap-magazine.xml",
                site / "magazine/index.html",
                site / "magazine/feed.xml",
            ]
            before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            second = MODULE.publish(site)
            after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            self.assertEqual(before, after)
            self.assertEqual(first["published_study_pages"], second["published_study_pages"])
            urls = [
                node.text
                for node in ET.parse(site / "sitemap-magazine.xml").getroot().findall("{*}url/{*}loc")
            ]
            self.assertEqual(len(urls), first["published_study_pages"] + 1)
            self.assertEqual(len(urls), len(set(urls)))

    def test_recent_primary_studies_keep_primary_sources_results_and_limits(self) -> None:
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
            "college-digital-cbt-guided-self-help-rct-2026.html": ("10.1038/s41562-026-02454-z", "42098266", "6205 طلاب", "OR=0.77", "74.4%"),
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
