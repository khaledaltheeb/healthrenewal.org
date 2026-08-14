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
        self.assertIn('href="/"', homepage)
        self.assertIn('href="/care-guides/"', homepage)
        self.assertNotIn('/pterminology-site/', homepage)
        self.assertEqual(existing.count("<header"), 1)
        self.assertEqual(existing.count("<footer"), 1)
        for relative in (
            "editorial-methodology/index.html",
            "evaluate-mental-health-information/index.html",
            "guides/source-citation-and-update-transparency/index.html",
            "magazine/index.html",
            "magazine/adhd-rhythmic-music-game-rct-2026.html",
            "magazine/autism-aspen-low-resource-parent-intervention-rct-2026.html",
            "magazine/neurodevelopmental-disabilities-navigator-act-parent-stress-rct-2026.html",
            "magazine/adolescent-mental-health-artemis-cluster-rct-2026.html",
            "magazine/autism-parents-mbsr-depression-anxiety-stress-rct-2026.html",
            "magazine/grieving-adolescents-alba-app-rct-2026.html",
            "magazine/adolescent-school-guided-narrative-writing-cluster-rct-2026.html",
            "magazine/autism-mentorship-program-pilot-rct-2026.html",
            "magazine/college-digital-cbt-guided-self-help-rct-2026.html",
            "magazine/feed.xml",
        ):
            self.assertTrue((site / relative).is_file(), relative)
        for relative in (
            "editorial-methodology/index.html",
            "evaluate-mental-health-information/index.html",
        ):
            alias = (site / relative).read_text(encoding="utf-8")
            self.assertIn("data-legacy-path-alias=", alias)
            self.assertIn('name="robots" content="noindex,follow"', alias)
            self.assertIn('rel="canonical" href="https://healthrenewal.org/trust/"', alias)
            self.assertIn('http-equiv="refresh" content="0;url=/trust/"', alias)
            self.assertEqual(alias.count('data-platform-shell="header"'), 1)
            self.assertEqual(alias.count('data-platform-shell="footer"'), 1)
        index = (site / "magazine/index.html").read_text(encoding="utf-8")
        self.assertIn('"numberOfItems":79', index)
        self.assertEqual(index.count('class="card"'), 79)
        self.assertIn("الهدف المرحلي 100 قراءة", index)
        self.assertIn('<link rel="canonical" href="https://healthrenewal.org/magazine/">', index)
        article = (site / "magazine/autism-interventions-meta-analysis-2026.html").read_text(encoding="utf-8")
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/magazine/autism-interventions-meta-analysis-2026.html">',
            article,
        )
        self.assertNotIn("khaledaltheeb.github.io/pterminology-site", article)
        report = json.loads((site / "api/platform-identity-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["pages"], 85)
        self.assertEqual(report["headers_added"], 3)
        self.assertEqual(report["footers_added"], 3)
        self.assertEqual(report["styles_added"], 3)
        self.assertGreaterEqual(report["language_replacements"], 4)
        self.assertTrue(report["trust_guides_published"])
        self.assertFalse(report["section_directory_refreshed_after_trust_guides"])
        self.assertFalse(report["publication_surface_refreshed_after_trust_guides"])
        self.assertTrue(report["magazine_published"])
        self.assertEqual(report["magazine_pages"], 79)
        self.assertEqual(report["magazine_unwired_pages"], 0)
        self.assertEqual(report["magazine_report"], "api/magazine-v201.json")
        self.assertEqual(report["remaining_banned_pages"], [])
        self.assertEqual(report["missing_header_pages"], [])
        self.assertEqual(report["missing_footer_pages"], [])
        magazine = json.loads((site / "api/magazine-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(magazine["version"], 316)
        self.assertEqual(magazine["canonical_origin"], "https://healthrenewal.org")
        self.assertEqual(magazine["legacy_origins_remaining"], 0)
        self.assertEqual(magazine["research_summaries_published"], 79)
        self.assertEqual(magazine["target_research_summaries"], 100)
        self.assertEqual(magazine["remaining_to_target"], 21)
        self.assertEqual(magazine["unwired_research_pages"], 0)
        self.assertEqual(magazine["sitemap"]["child_urls"], 80)
        self.assertEqual(magazine["rss_contract"], "latest-twenty-sorted-by-datePublished")

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
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        first = (tools / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-tools-design="marshmallow-v245"', first)
        self.assertIn("class='existing-tools-page tools-marshmallow-v245'", first)
        self.assertEqual(first.count("tools-marshmallow-v245-style"), 1)
        for color in ("--tm-mint:#e5faf5", "--tm-rose:#fff0f5", "--tm-lilac:#f2edff"):
            self.assertIn(color, first)
        self.assertIn("color:var(--tm-ink)!important", first)
        self.assertIn("background:var(--tm-lilac)!important;color:#4a315f!important", first)
        self.assertIn("prefers-color-scheme:dark", first)
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        second = (tools / "index.html").read_text(encoding="utf-8")
        self.assertEqual(first, second)

    def test_is_idempotent(self) -> None:
        site = self.make_site()
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        first = (site / "index.html").read_text(encoding="utf-8")
        first_magazine = (site / "magazine/index.html").read_text(encoding="utf-8")
        first_feed = (site / "magazine/feed.xml").read_text(encoding="utf-8")
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        second = (site / "index.html").read_text(encoding="utf-8")
        second_magazine = (site / "magazine/index.html").read_text(encoding="utf-8")
        second_feed = (site / "magazine/feed.xml").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(first_magazine, second_magazine)
        self.assertEqual(first_feed, second_feed)
        magazine_report = json.loads((site / "api/magazine-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(magazine_report["version"], 316)
        self.assertEqual(magazine_report["canonical_origin"], "https://healthrenewal.org")
        self.assertEqual(magazine_report["legacy_origins_remaining"], 0)
        self.assertEqual(magazine_report["research_summaries_published"], 79)
        self.assertEqual(magazine_report["target_research_summaries"], 100)
        self.assertEqual(magazine_report["sitemap"]["child_urls"], 80)
        self.assertEqual(magazine_report["rss_contract"], "latest-twenty-sorted-by-datePublished")


if __name__ == "__main__":
    unittest.main()
