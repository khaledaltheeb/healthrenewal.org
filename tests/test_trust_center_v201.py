from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_trust_center_v201.py"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
LINK = '<a href="trust/">الثقة والمنهجية</a>'


class TrustCenterV201Tests(unittest.TestCase):
    def make_site(self, *, footer_has_trust: bool = False) -> Path:
        site = Path(tempfile.mkdtemp(prefix="trust-v201-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        footer_links = '<a href="partners/">الشركاء</a>' + (LINK if footer_has_trust else "")
        site.joinpath("index.html").write_text(
            f'''<!doctype html><html lang="ar" dir="rtl"><head><title>الرئيسية</title></head><body>
<header><div class="header-inner"><nav class="nav" aria-label="التنقل الرئيسي"><a href="encyclopedia/">الموسوعة</a></nav></div></header>
<main><h1>الرئيسية</h1></main>
<footer><div class="footer-links">{footer_links}</div></footer>
</body></html>''',
            encoding="utf-8",
        )
        site.joinpath("sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.test/</loc></url></urlset>',
            encoding="utf-8",
        )
        return site

    def run_publisher(self, site: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), str(site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_integrates_new_homepage_semantically_and_updates_brand(self) -> None:
        site = self.make_site()
        completed = self.run_publisher(site)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        homepage = site.joinpath("index.html").read_text(encoding="utf-8")
        trust = site.joinpath("trust/index.html").read_text(encoding="utf-8")
        self.assertEqual(homepage.count(LINK), 2)
        self.assertIn('<nav class="nav" aria-label="التنقل الرئيسي">', homepage)
        self.assertIn('<div class="footer-links">', homepage)
        self.assertIn(BRAND, trust)
        self.assertIn(SLOGAN, trust)
        self.assertIn("الاسم المؤسس: مصطلحات علم النفس", trust)
        self.assertIn('href="#main"', trust)
        self.assertIn('id="main"', trust)
        report = json.loads(site.joinpath("api/trust-center-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["version"], 201)
        self.assertTrue(report["semantic_homepage_integration"])
        self.assertTrue(report["navigation_link_added"])
        self.assertTrue(report["footer_link_added"])
        sitemap = site.joinpath("sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("/trust/", sitemap)

    def test_adds_navigation_link_when_footer_already_contains_trust(self) -> None:
        site = self.make_site(footer_has_trust=True)
        completed = self.run_publisher(site)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        homepage = site.joinpath("index.html").read_text(encoding="utf-8")
        self.assertEqual(homepage.count(LINK), 2)
        header = homepage.split("</header>", 1)[0]
        footer = homepage.split("<footer", 1)[1]
        self.assertIn(LINK, header)
        self.assertEqual(footer.count(LINK), 1)
        report = json.loads(site.joinpath("api/trust-center-v201.json").read_text(encoding="utf-8"))
        self.assertTrue(report["navigation_link_added"])
        self.assertFalse(report["footer_link_added"])

    def test_is_idempotent_for_homepage_links(self) -> None:
        site = self.make_site()
        first = self.run_publisher(site)
        self.assertEqual(first.returncode, 0, first.stderr)
        homepage_first = site.joinpath("index.html").read_text(encoding="utf-8")
        second = self.run_publisher(site)
        self.assertEqual(second.returncode, 0, second.stderr)
        homepage_second = site.joinpath("index.html").read_text(encoding="utf-8")
        self.assertEqual(homepage_first, homepage_second)
        self.assertEqual(homepage_second.count(LINK), 2)
        report = json.loads(site.joinpath("api/trust-center-v201.json").read_text(encoding="utf-8"))
        self.assertFalse(report["navigation_link_added"])
        self.assertFalse(report["footer_link_added"])


if __name__ == "__main__":
    unittest.main()
