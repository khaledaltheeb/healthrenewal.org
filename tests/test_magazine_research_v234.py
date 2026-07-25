from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_magazine_v201.py"
SPEC = importlib.util.spec_from_file_location("publish_magazine_v234", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MagazineResearchV234Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        site.mkdir()
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
            encoding="utf-8",
        )
        return site

    def test_publishes_nine_verified_articles_and_sitemap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(report["version"], 234)
            self.assertEqual(report["research_summaries_published"], 9)
            self.assertEqual(len(report["articles"]), 9)
            self.assertEqual(report["sitemap"]["child_urls"], 10)

            magazine = site / "magazine"
            self.assertTrue((magazine / "index.html").is_file())
            self.assertTrue((magazine / "research.css").is_file())
            for filename in report["articles"]:
                text = (magazine / filename).read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', text)
                self.assertIn("المصدر الأصلي", text)
                self.assertIn("حدود الدليل", text)

            sitemap = ET.parse(site / "sitemap-magazine.xml").getroot()
            urls = [node.text for node in sitemap.findall("{*}url/{*}loc")]
            self.assertEqual(len(urls), 10)
            self.assertEqual(len(urls), len(set(urls)))
            self.assertIn(MODULE.URL, urls)
            for filename in report["articles"]:
                self.assertIn(MODULE.URL + filename, urls)

            saved = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["research_summaries_published"], 9)
            self.assertEqual(set(saved["articles"]), set(report["articles"]))
            self.assertEqual(len(saved["source_sha256"]), 9)

    def test_publish_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            first = MODULE.publish(site)
            sitemap_before = (site / "sitemap-magazine.xml").read_bytes()
            index_before = (site / "magazine" / "index.html").read_bytes()
            second = MODULE.publish(site)
            self.assertEqual(first["source_sha256"], second["source_sha256"])
            self.assertEqual(sitemap_before, (site / "sitemap-magazine.xml").read_bytes())
            self.assertEqual(index_before, (site / "magazine" / "index.html").read_bytes())

    def test_peer_led_summary_reports_null_findings(self) -> None:
        text = (ROOT / "magazine" / "peer-led-adolescent-mental-health-2025.html").read_text(encoding="utf-8")
        self.assertIn("لم يجد التحليل التلوي آثارًا دالة", text)
        self.assertIn("7,060", text)
        self.assertIn("ست دراسات من أصل سبع", text)
        self.assertNotIn("قد تُظهر فوائد لبعض مؤشرات الرفاه", text)

    def test_current_2026_sources_are_in_contract(self) -> None:
        expected = {
            "artemis-adolescent-mental-health-stigma-2026.html": ("10.1001/jamapsychiatry.2026.0603", "42054038"),
            "autism-behavioral-domains-network-meta-analysis-2026.html": ("10.1186/s13034-026-01132-2", "42469874"),
            "autism-emotion-regulation-interventions-2026.html": ("10.1016/j.cpr.2026.102764", "42224908"),
            "autism-interventions-meta-analysis-2026.html": ("10.1038/s44220-026-00652-2", "149 تجربة"),
        }
        contracted = {item["file"] for item in MODULE.ARTICLES}
        for filename, markers in expected.items():
            self.assertIn(filename, contracted)
            text = (ROOT / "magazine" / filename).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text)

    def test_index_exposes_every_article_twice(self) -> None:
        index = (ROOT / "magazine" / "index.html").read_text(encoding="utf-8")
        self.assertIn('"hasPart"', index)
        for item in MODULE.ARTICLES:
            self.assertGreaterEqual(index.count(f'href="{item["file"]}"'), 2)
            self.assertIn(MODULE.URL + item["file"], index)


if __name__ == "__main__":
    unittest.main()
