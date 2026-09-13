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

    def run_identity(self, site: Path) -> None:
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)

    def test_replaces_labels_adds_shell_and_publishes_recursive_magazine(self) -> None:
        site = self.make_site()
        self.run_identity(site)

        homepage = (site / "index.html").read_text(encoding="utf-8")
        existing = (site / "nested/index.html").read_text(encoding="utf-8")
        for rejected in ("المعاقين", ">معاق<", "معاقة", "المعاقة"):
            self.assertNotIn(rejected, homepage + existing)
        self.assertIn("ذوي الاحتياجات الخاصة", homepage)
        self.assertIn('data-platform-shell="header"', homepage)
        self.assertIn('data-platform-shell="footer"', homepage)
        self.assertEqual(existing.count("<header"), 1)
        self.assertEqual(existing.count("<footer"), 1)

        index = (site / "magazine/index.html").read_text(encoding="utf-8")
        self.assertIn('<link rel="canonical" href="https://healthrenewal.org/magazine/">', index)
        self.assertIn('<link rel="stylesheet" href="research.css">', index)
        self.assertIn("قراءة الدراسة الكاملة", index)
        self.assertNotIn("javascript:void", index.lower())
        self.assertTrue((site / "magazine/feed.xml").is_file())
        self.assertTrue(
            (site / "magazine/pediatric-oncology/theses/bridging-gap-hct-success-troullioud-lucas-2026/index.html").is_file()
        )

        identity = json.loads((site / "api/platform-identity-v201.json").read_text(encoding="utf-8"))
        compat = json.loads((site / "api/magazine-v201.json").read_text(encoding="utf-8"))
        current = json.loads((site / "api/magazine-v202.json").read_text(encoding="utf-8"))
        bibliography = json.loads((site / "api/magazine-bibliography-verification-v202.json").read_text(encoding="utf-8"))

        self.assertTrue(identity["magazine_published"])
        self.assertEqual(identity["magazine_unwired_pages"], 0)
        self.assertEqual(identity["magazine_pages"], current["published_study_pages"])
        self.assertGreaterEqual(current["published_study_pages"], 193)
        self.assertEqual(current["index_cards"], current["published_study_pages"])
        self.assertEqual(current["wired_study_pages"], current["published_study_pages"])
        self.assertEqual(current["missing_source_pages"], 0)
        self.assertEqual(current["validation"]["noindex_pages"], 0)
        self.assertEqual(current["validation"]["duplicate_canonical_urls"], 0)
        self.assertEqual(compat["version"], 316)
        self.assertEqual(compat["publisher_contract"], 202)
        self.assertEqual(compat["research_summaries_published"], current["published_study_pages"])
        self.assertEqual(compat["target_research_summaries"], 500)
        self.assertEqual(compat["unwired_research_pages"], 0)
        self.assertEqual(compat["missing_source_pages"], 0)
        summary = bibliography["summary"]
        self.assertEqual(summary["verified_source_pages"], current["published_study_pages"])
        self.assertEqual(summary["source_pages_still_requiring_manual_review"], 0)

    def test_tools_page_uses_marshmallow_contrast(self) -> None:
        site = self.make_site()
        tools = site / "tools"
        tools.mkdir()
        (tools / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>الأدوات</title>'
            '<style>.tool-card{background:#000;color:#fff}.badge{background:#111;color:#fff}</style>'
            "</head><body class='existing-tools-page'><main><section class=\"tools-grid\"><article class=\"tool-card\">"
            '<h1>الأدوات</h1><p>وصف الأداة</p><span class="badge">متاح</span>'
            '</article></section></main></body></html>',
            encoding="utf-8",
        )
        self.run_identity(site)
        first = (tools / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-tools-design="marshmallow-v245"', first)
        self.assertIn("class='existing-tools-page tools-marshmallow-v245'", first)
        self.assertEqual(first.count("tools-marshmallow-v245-style"), 1)
        self.run_identity(site)
        second = (tools / "index.html").read_text(encoding="utf-8")
        self.assertEqual(first, second)

    def test_is_idempotent(self) -> None:
        site = self.make_site()
        self.run_identity(site)
        first_home = (site / "index.html").read_text(encoding="utf-8")
        first_magazine = (site / "magazine/index.html").read_text(encoding="utf-8")
        first_feed = (site / "magazine/feed.xml").read_text(encoding="utf-8")
        first_report = json.loads((site / "api/magazine-v201.json").read_text(encoding="utf-8"))
        self.run_identity(site)
        self.assertEqual(first_home, (site / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(first_magazine, (site / "magazine/index.html").read_text(encoding="utf-8"))
        self.assertEqual(first_feed, (site / "magazine/feed.xml").read_text(encoding="utf-8"))
        second_report = json.loads((site / "api/magazine-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(first_report["research_summaries_published"], second_report["research_summaries_published"])
        self.assertEqual(second_report["publisher_contract"], 202)
        self.assertEqual(second_report["unwired_research_pages"], 0)


if __name__ == "__main__":
    unittest.main()
