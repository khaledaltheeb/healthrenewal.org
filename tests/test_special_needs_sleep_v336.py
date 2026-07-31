from __future__ import annotations

import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import publish_special_needs_sleep_v336 as publisher  # noqa: E402


class SpecialNeedsSleepSupportV336Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        (site / "special-needs").mkdir(parents=True)
        (site / "api").mkdir(parents=True)
        (site / "special-needs" / "index.html").write_text(
            "<!doctype html><html lang='ar' dir='rtl'><head><title>ذوو الاحتياجات الخاصة</title></head>"
            "<body><main><h1>ذوو الاحتياجات الخاصة</h1><div class=\"resources\"></div></main></body></html>",
            encoding="utf-8",
        )
        sitemap = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/special-needs/</loc></url>'
            '</urlset>'
        )
        (site / "sitemap-special-needs.xml").write_text(sitemap, encoding="utf-8")
        (site / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        return site

    def test_source_contract(self) -> None:
        data = publisher.load_data()
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertGreaterEqual(publisher.words(data), 900)
        self.assertEqual(data["review_status"], "internally-reviewed")
        self.assertEqual(data["external_review"], "recommended-not-completed")
        self.assertEqual(len(data["sources"]), 4)
        self.assertNotIn("معاقين", serialized)

    def test_publish_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site = self.make_site(Path(temp))
            report = publisher.publish(site)
            self.assertEqual(report["status"], "passed")
            self.assertTrue(report["medication_boundary_visible"])
            self.assertTrue(report["sleep_apnoea_escalation_visible"])
            self.assertTrue(report["two_week_sleep_log_visible"])
            page = site / report["generated_page"]
            html = page.read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', html)
            self.assertIn("الشخير", html)
            self.assertIn("توقف التنفس", html)
            self.assertIn("10.1542/peds.2012-0900I", json.dumps(publisher.load_data(), ensure_ascii=False))
            self.assertNotIn("معاقين", html)
            self.assertIn(report["canonical_url"], html)
            self.assertNotIn("healthrenewal.org//", html)
            hub_html = (site / "special-needs" / "index.html").read_text(encoding="utf-8")
            self.assertIn("special-needs-guides-v336:start", hub_html)
            canonical_path = urlparse(report["canonical_url"]).path
            self.assertIn(f'href="{canonical_path}"', hub_html)

            root = ET.parse(site / "sitemap-special-needs.xml").getroot()
            urls = [node.text for node in root.findall("{*}url/{*}loc") if node.text]
            self.assertIn(report["canonical_url"], urls)
            self.assertEqual(len(urls), len(set(urls)))

            api = json.loads((site / "api" / "special-needs-sleep-support-v336.json").read_text(encoding="utf-8"))
            self.assertEqual(api["source_count"], 4)
            self.assertFalse(api["external_clinical_review_completed"])


if __name__ == "__main__":
    unittest.main()
