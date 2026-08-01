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
NEW_ARTICLE = "universal-digital-mental-health-youth-systematic-review-2026.html"


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
        article_count = len(pages)
        self.assertGreaterEqual(article_count, 80)
        self.assertIn(NEW_ARTICLE, {path.name for path in pages})
        self.assertGreaterEqual(MODULE.CONTRACT, 315)
        self.assertEqual(MODULE.TARGET_ARTICLES, 100)
        dates = [MODULE.article_date(path) for path in pages]
        self.assertEqual(dates, sorted(dates, reverse=True))

        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(report["version"], MODULE.CONTRACT)
            self.assertEqual(report["research_summaries_published"], article_count)
            self.assertEqual(report["target_research_summaries"], 100)
            self.assertEqual(report["remaining_to_target"], max(0, 100 - article_count))
            self.assertTrue(report["continuous_publication_policy"])
            self.assertEqual(len(report["articles"]), article_count)
            self.assertEqual(report["sitemap"]["child_urls"], article_count + 1)
            self.assertEqual(report["robots"]["rss_items"], min(20, article_count))
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
            self.assertEqual(len(urls), article_count + 1)
            self.assertEqual(len(urls), len(set(urls)))
            for path in pages:
                self.assertIn(MODULE.URL + path.name, urls)

            feed_root = ET.parse(magazine / "feed.xml").getroot()
            items = feed_root.findall("./channel/item")
            self.assertEqual(len(items), min(20, article_count))
            feed_links = [item.findtext("link") for item in items]
            self.assertEqual(feed_links, [MODULE.URL + path.name for path in pages[:20]])
            feed_dates = [parsedate_to_datetime(item.findtext("pubDate")) for item in items]
            self.assertEqual(feed_dates, sorted(feed_dates, reverse=True))
            self.assertEqual(parsedate_to_datetime(feed_root.findtext("./channel/lastBuildDate")), feed_dates[0])

            saved = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["research_summaries_published"], article_count)
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
        article_count = len(pages)
        index = MODULE.render_index(pages)
        self.assertIn(f'"numberOfItems":{article_count}', index)
        self.assertIn(f"{article_count} قراءة علمية مستقلة", index)
        self.assertIn("الهدف المرحلي 100 قراءة", index)
        self.assertIn(f"المتبقي {max(0, 100 - article_count)}", index)
        self.assertIn('type="application/rss+xml"', index)
        self.assertEqual(index.count('class="card"'), article_count)
        self.assertEqual(index.count('"@type":"ScholarlyArticle"'), article_count)
        self.assertEqual(index.count('"datePublished"'), article_count)
        card_positions = [index.index(f'href="{path.name}"') for path in pages]
        self.assertEqual(card_positions, sorted(card_positions))
        for path in pages:
            self.assertGreaterEqual(index.count(f'href="{path.name}"'), 2)
            self.assertIn(MODULE.URL + path.name, index)

    def test_new_systematic_review_contract(self) -> None:
        text = (ROOT / "magazine" / NEW_ARTICLE).read_text(encoding="utf-8")
        for marker in (
            "10.1038/s41746-026-03044-z",
            "INPLASY202490026",
            "57 دراسة",
            "43973",
            "9 من أصل 16",
            "آثار صغيرة",
            "منخفضة اليقين",
            "https://healthrenewal.org/magazine/",
            "<h2>المصدر الأصلي</h2>",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("khaledaltheeb.github.io", text)
        self.assertEqual(text.lower().count("<h1"), 1)
        self.assertIn('"datePublished":"2026-07-27"', text)
        self.assertIn("حدود", text)
        self.assertIn("لا تستبدل التقييم أو العلاج", text)


if __name__ == "__main__":
    unittest.main()
