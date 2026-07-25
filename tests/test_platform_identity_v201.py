from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enforce_platform_identity_v201.py"


class PlatformIdentityV201Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="platform-identity-v201-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "nested").mkdir()
        (site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>الرئيسية</title></head>'
            '<body><main><h1>خدمات المعاقين</h1><p>دعم معاق وأسرته، ودعم معاقة وأسرتها.</p></main></body></html>',
            encoding="utf-8",
        )
        (site / "nested/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>صفحة</title></head><body>'
            '<header><nav>تنقل</nav></header><main><h1>صفحة قائمة</h1><p>المعاقة تحتاج إلى دعم ملائم.</p></main><footer>تذييل</footer></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            encoding="utf-8",
        )
        return site

    def test_replaces_labels_adds_shell_and_publishes_magazine(self) -> None:
        site = self.make_site()
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        homepage = (site / "index.html").read_text(encoding="utf-8")
        existing = (site / "nested/index.html").read_text(encoding="utf-8")
        for rejected in ("المعاقين", ">معاق<", "معاقة", "المعاقة"):
            self.assertNotIn(rejected, homepage + existing)
        self.assertIn("ذوي الاحتياجات الخاصة", homepage)
        self.assertIn("شخص من ذوي الاحتياجات الخاصة", homepage)
        self.assertIn("شخص من ذوي الاحتياجات الخاصة", existing)
        self.assertIn('data-platform-shell="header"', homepage)
        self.assertIn('data-platform-shell="footer"', homepage)
        self.assertEqual(existing.count("<header"), 1)
        self.assertEqual(existing.count("<footer"), 1)
        for relative in (
            "editorial-methodology/index.html",
            "evaluate-mental-health-information/index.html",
            "guides/source-citation-and-update-transparency/index.html",
            "magazine/index.html",
            "magazine/aya-cancer-digital-mental-health-meta-analysis-2026.html",
            "magazine/down-syndrome-adult-medical-care-systematic-review-2026.html",
        ):
            self.assertTrue((site / relative).is_file(), relative)
        index = (site / "magazine/index.html").read_text(encoding="utf-8")
        self.assertIn('"numberOfItems":50', index)
        self.assertEqual(index.count('class="card"'), 50)
        report = json.loads((site / "api/platform-identity-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["pages"], 56)
        self.assertEqual(report["headers_added"], 1)
        self.assertEqual(report["footers_added"], 1)
        self.assertGreaterEqual(report["language_replacements"], 4)
        self.assertTrue(report["trust_guides_published"])
        self.assertTrue(report["magazine_published"])
        self.assertEqual(report["magazine_pages"], 50)
        self.assertEqual(report["magazine_unwired_pages"], 0)
        self.assertEqual(report["magazine_report"], "api/magazine-v201.json")
        self.assertEqual(report["remaining_banned_pages"], [])
        self.assertEqual(report["missing_header_pages"], [])
        self.assertEqual(report["missing_footer_pages"], [])
        magazine = json.loads((site / "api/magazine-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(magazine["research_summaries_published"], 50)
        self.assertEqual(magazine["unwired_research_pages"], 0)
        self.assertEqual(magazine["sitemap"]["child_urls"], 51)

    def test_is_idempotent(self) -> None:
        site = self.make_site()
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        first = (site / "index.html").read_text(encoding="utf-8")
        first_magazine = (site / "magazine/index.html").read_text(encoding="utf-8")
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        second = (site / "index.html").read_text(encoding="utf-8")
        second_magazine = (site / "magazine/index.html").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(first_magazine, second_magazine)
        self.assertEqual(second.count('data-platform-shell="header"'), 1)
        self.assertEqual(second.count('data-platform-shell="footer"'), 1)
        self.assertEqual(second.count("platform-shell-v201-style"), 1)
        trust_report = json.loads((site / "api/trust-guides-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(trust_report["page_count"], 3)
        magazine_report = json.loads((site / "api/magazine-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(magazine_report["research_summaries_published"], 50)
        self.assertEqual(magazine_report["sitemap"]["child_urls"], 51)


if __name__ == "__main__":
    unittest.main()
