import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "i18n" / "v72" / "homepage.json"
PUBLISHER = ROOT / "scripts" / "publish_homepage_i18n_v72.py"
AUDITOR = ROOT / "scripts" / "audit_site_integrity_v13.py"
APPLY_HOMEPAGE = ROOT / "scripts" / "apply_homepage_v20.py"
SOURCE_HOME = ROOT / "index.html"
BASE = "https://healthrenewal.org"


class HomepageI18nV72Tests(unittest.TestCase):
    def build_fixture(self, sitemap_root: str = "sitemapindex") -> Path:
        temp = Path(tempfile.mkdtemp(prefix="homepage-i18n-v72-"))
        shutil.copy2(SOURCE_HOME, temp / "index.html")
        if sitemap_root == "sitemapindex":
            sitemap = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<sitemap><loc>{BASE}/sitemap-core.xml</loc></sitemap>'
                "</sitemapindex>\n"
            )
        else:
            sitemap = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f'<url><loc>{BASE}/</loc></url>'
                "</urlset>\n"
            )
        (temp / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        return temp

    def run_publisher(self, site: Path) -> None:
        subprocess.run(
            ["python3", str(PUBLISHER), str(site)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_translation_contract_is_complete_and_honest(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(data["entity_id"], "page.home")
        self.assertEqual(data["source_locale"], "ar")
        required = set(data["required_fields"])
        for locale in ("en", "es"):
            page = data["locales"][locale]
            self.assertEqual(page["status"], "translated")
            self.assertTrue(required.issubset(page))
            self.assertTrue(all(page[field] for field in required))
            self.assertFalse(page["verification"]["human_review_recorded"])
            self.assertEqual(len(page["sections"]["cards"]), 6)
            self.assertEqual(len(page["sections"]["quality"]), 4)
        serialized = json.dumps(data, ensure_ascii=False).lower()
        self.assertNotIn("linguistically-reviewed", serialized)
        self.assertNotIn("scientifically-reviewed", serialized)

    def test_production_homepage_pipeline_invokes_i18n_publisher(self):
        pipeline = APPLY_HOMEPAGE.read_text(encoding="utf-8")
        self.assertIn("publish_homepage_i18n_v72.py", pipeline)
        self.assertIn('"homepage_i18n_publisher": 72', pipeline)

    def test_integrity_auditor_uses_route_specific_language_contracts(self):
        spec = importlib.util.spec_from_file_location("audit_site_integrity_v13", AUDITOR)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.expected_language_direction("index.html"), ("ar", "rtl"))
        self.assertEqual(module.expected_language_direction("encyclopedia/index.html"), ("ar", "rtl"))
        self.assertEqual(module.expected_language_direction("en/index.html"), ("en", "ltr"))
        self.assertEqual(module.expected_language_direction("en/guides/index.html"), ("en", "ltr"))
        self.assertEqual(module.expected_language_direction("es/index.html"), ("es", "ltr"))

    def test_publisher_generates_indexable_accessible_pages(self):
        site = self.build_fixture("sitemapindex")
        self.addCleanup(shutil.rmtree, site, True)
        self.run_publisher(site)

        for locale in ("en", "es"):
            path = site / locale / "index.html"
            self.assertTrue(path.is_file())
            text = path.read_text(encoding="utf-8")
            self.assertIn(f'<html lang="{locale}" dir="ltr">', text)
            self.assertEqual(text.count("<h1>"), 1)
            self.assertGreaterEqual(text.count("<h2"), 3)
            self.assertEqual(text.count("<h3>"), 6)
            self.assertIn(f'<link rel="canonical" href="{BASE}/{locale}/">', text)
            for code in ("ar", "en", "es", "x-default"):
                self.assertEqual(text.count(f'hreflang="{code}"'), 1)
            self.assertIn('rel="manifest"', text)
            self.assertIn('application/ld+json', text)
            self.assertIn('name="robots"', text)
            self.assertTrue("self-diagnosis" in text or "autodiagnóstico" in text)
            self.assertIn("YouTube", text)
            self.assertIn("Instagram", text)

        arabic = (site / "index.html").read_text(encoding="utf-8")
        self.assertEqual(arabic.count("data-i18n-switcher-v72"), 1)
        for code in ("ar", "en", "es", "x-default"):
            self.assertEqual(arabic.count(f'hreflang="{code}"'), 1)

        sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(sitemap.count("sitemap-i18n.xml"), 1)
        i18n_sitemap = (site / "sitemap-i18n.xml").read_text(encoding="utf-8")
        self.assertEqual(i18n_sitemap.count("<url>"), 2)
        self.assertEqual(i18n_sitemap.count(f"{BASE}/en/"), 1)
        self.assertEqual(i18n_sitemap.count(f"{BASE}/es/"), 1)

        report = json.loads((site / "api" / "homepage-i18n-v72.json").read_text(encoding="utf-8"))
        self.assertEqual(report["generated_page_count"], 2)
        self.assertEqual(report["locales"], ["en", "es"])
        self.assertEqual(report["sitemap_mode"], "sitemapindex")
        self.assertFalse(report["human_review_claimed"])

    def test_publisher_is_idempotent(self):
        site = self.build_fixture("sitemapindex")
        self.addCleanup(shutil.rmtree, site, True)
        self.run_publisher(site)
        self.run_publisher(site)
        arabic = (site / "index.html").read_text(encoding="utf-8")
        sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(arabic.count("data-i18n-switcher-v72"), 1)
        self.assertEqual(arabic.count('hreflang="en"'), 1)
        self.assertEqual(sitemap.count("sitemap-i18n.xml"), 1)

    def test_urlset_fallback_adds_locale_urls_without_mixing_roots(self):
        site = self.build_fixture("urlset")
        self.addCleanup(shutil.rmtree, site, True)
        self.run_publisher(site)
        sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("<urlset", sitemap)
        self.assertNotIn("<sitemap>", sitemap)
        self.assertEqual(sitemap.count(f"{BASE}/en/"), 1)
        self.assertEqual(sitemap.count(f"{BASE}/es/"), 1)
        report = json.loads((site / "api" / "homepage-i18n-v72.json").read_text(encoding="utf-8"))
        self.assertEqual(report["sitemap_mode"], "urlset")


if __name__ == "__main__":
    unittest.main()
