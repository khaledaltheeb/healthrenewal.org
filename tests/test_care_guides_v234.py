from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://khaledaltheeb.github.io/pterminology-site/"


class CareGuidesV234Tests(unittest.TestCase):
    def test_institutional_publication_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="care-v234-") as temp:
            site = Path(temp)
            extension = site / "care-guides/extension-guide/index.html"
            extension.parent.mkdir(parents=True)
            (site / "api").mkdir()
            extension.write_text(
                '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
                '<title>دليل اختيار المختص</title><meta name="description" content="دليل عملي لاختيار المختص.">'
                f'<meta property="og:url" content="{BASE}care-guides/extension-guide/">'
                '<script type="application/ld+json">{"@type":"Article","x":"HowTo"}</script></head>'
                '<body><main id="legacy-main"><header><h1>دليل اختيار المختص</h1></header>'
                '<section><h2>الخصوصية</h2><p>محتوى.</p></section>'
                '<section><h2>مصادر مؤسسية للمراجعة</h2><p>خدمات الطوارئ المحلية.</p></section>'
                '</main></body></html>', encoding="utf-8"
            )
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<sitemap><loc>{BASE}sitemap-main.xml</loc></sitemap></sitemapindex>', encoding="utf-8"
            )
            (site / "sitemap-care-guides.xml").write_text(
                '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<url><loc>{BASE}care-guides/</loc></url>'
                f'<url><loc>{BASE}care-guides/extension-guide/</loc></url></urlset>', encoding="utf-8"
            )
            run = subprocess.run(
                [sys.executable, "scripts/publish_care_guides_v21.py", str(site)],
                cwd=ROOT, text=True, capture_output=True, check=False
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            legacy = json.loads((site / "api/care-guides-v21.json").read_text(encoding="utf-8"))
            report = json.loads((site / "api/care-guides-v234.json").read_text(encoding="utf-8"))
            self.assertEqual(report["version"], 234)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["published_pages"], legacy["pages"])
            self.assertEqual(report["sitemap_urls"], legacy["sitemap_urls"])
            self.assertEqual(report["pages_with_keywords"], legacy["pages"])
            self.assertEqual(report["pages_with_faq_schema"], legacy["pages"])
            self.assertEqual(report["pages_with_canonical"], legacy["pages"])
            self.assertEqual(report["pages_with_single_h1"], legacy["pages"])
            self.assertEqual(report["guide_pages_with_toc"], legacy["guides"])
            self.assertFalse(report["duplicate_ids"])
            self.assertTrue(report["specialist_review_gate_preserved"])
            self.assertEqual(report["blocked_term_occurrences"], 0)
            self.assertTrue((site / "assets/css/care-guides-v234.css").is_file())
            self.assertTrue((site / "assets/js/care-guides-v234.js").is_file())
            hub = (site / "care-guides/index.html").read_text(encoding="utf-8")
            for token in ("data-care-library", "CollectionPage", "ItemList", "FAQPage", "المنهجية التحريرية وضبط الجودة"):
                self.assertIn(token, hub)
            for page in sorted((site / "care-guides").glob("*/index.html")):
                text = page.read_text(encoding="utf-8")
                for token in ('data-care-guides-v234="1"', 'name="keywords"', 'rel="canonical"', "FAQPage", "care-toc"):
                    self.assertIn(token, text, page)
                ids = re.findall(r'\bid="([^"]+)"', text)
                self.assertEqual(len(ids), len(set(ids)), page)
            robots = (site / "robots.txt").read_text(encoding="utf-8")
            self.assertIn(f"Sitemap: {BASE}sitemap-care-guides.xml", robots)
            self.assertIn("Disallow: /pterminology-site/api/", robots)


if __name__ == "__main__":
    unittest.main()
