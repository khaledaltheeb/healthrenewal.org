import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v186" / "inclusive-disability-language-ar.json"
SCRIPT = ROOT / "scripts" / "publish_inclusive_disability_language_v186.py"
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"

spec = importlib.util.spec_from_file_location("inclusive_language_v186", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class InclusiveDisabilityLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTENT.read_text(encoding="utf-8"))

    def test_content_depth_and_nonclinical_boundaries(self):
        self.assertEqual(self.data["status"], "internally-reviewed")
        self.assertGreaterEqual(len(self.data["principles"]), 6)
        self.assertGreaterEqual(len(self.data["replace_examples"]), 8)
        self.assertGreaterEqual(len(self.data["context_checklist"]), 8)
        self.assertGreaterEqual(len(self.data["contexts"]), 4)
        limits = self.data["professional_limits"]
        for marker in ["ليس", "تشخيص", "تفضيل الشخص"]:
            self.assertIn(marker, limits)

    def test_language_avoids_pity_and_forced_euphemisms(self):
        text = json.dumps(self.data, ensure_ascii=False)
        for marker in ["الشفقة", "البطولة", "من ذوي الهمم", "يستخدم كرسيًا متحركًا", "الموافقة"]:
            self.assertIn(marker, text)
        self.assertNotIn("الأبطال الخارقون", text)
        self.assertNotIn("رغم معاناته انتصر", text)

    def test_sources_are_official_unique_and_contract_ready(self):
        sources = self.data["sources"]
        self.assertGreaterEqual(len(sources), 3)
        urls = [item["url"] for item in sources]
        ids = [item["id"] for item in sources]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(len(ids), len(set(ids)))
        allowed_types = {"official_guideline", "public_health_authority"}
        for source in sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIn(source["publisher"], {"United Nations", "World Health Organization", "OHCHR"})
            self.assertIsInstance(source["year"], int)
            self.assertRegex(source["verified_at"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertIn(source["source_type"], allowed_types)
            self.assertEqual(source["status"], "current")
            self.assertTrue(source["claims_supported"])
            self.assertTrue(source["supports"])

    def test_build_has_seo_schema_rtl_contextual_links_and_sitemap(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            for relative, title in [
                ("special-needs/index.html", "ذوو الاحتياجات"),
                ("audiences/family/index.html", "الأسرة"),
                ("audiences/teacher/index.html", "المعلم"),
            ]:
                path = site / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'<html lang="ar" dir="rtl"><main><h1>{title}</h1></main></html>', encoding="utf-8")
            output = module.publish(site)
            html = output.read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', html)
            self.assertEqual(html.count("<h1>"), 1)
            self.assertIn('<link rel="canonical"', html)
            self.assertIn('name="robots" content="index,follow"', html)
            self.assertIn('name="twitter:card"', html)
            self.assertIn('"@type": "Article"', html)
            self.assertIn('"@type": "BreadcrumbList"', html)
            self.assertIn('property="og:title"', html)
            self.assertIn("citation", html)
            href = "/special-needs/inclusive-language-disability/"
            canonical = "https://healthrenewal.org" + href
            for relative in ["special-needs/index.html", "audiences/family/index.html", "audiences/teacher/index.html"]:
                self.assertIn(href, (site / relative).read_text(encoding="utf-8"))
            sitemap = site / module.SITEMAP_NAME
            self.assertTrue(sitemap.is_file())
            self.assertEqual(sitemap.read_text(encoding="utf-8").count(canonical), 1)
            report = json.loads((site / "api" / "inclusive-disability-language-v186.json").read_text(encoding="utf-8"))
            self.assertEqual(report["sitemap"], f"/{module.SITEMAP_NAME}")

    def test_production_pipeline_invokes_after_audience_paths_and_registers_sitemap(self):
        text = APPLY.read_text(encoding="utf-8")
        start_here = 'run_publisher("publish_start_here_v176.py")'
        inclusive = 'run_publisher("publish_inclusive_disability_language_v186.py")'
        sitemap = 'register_sitemap("sitemap-inclusive-disability-language.xml")'
        self.assertEqual(text.count(inclusive), 1)
        self.assertEqual(text.count(sitemap), 1)
        self.assertLess(text.index(start_here), text.index(inclusive))
        self.assertLess(text.index(inclusive), text.index(sitemap))
        self.assertIn('"inclusive_disability_language_publisher": 186', text)
        self.assertIn('"inclusive_disability_language_sitemap_sync": 187', text)

    def test_build_is_idempotent_and_not_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            hub = site / "special-needs" / "index.html"
            hub.parent.mkdir(parents=True)
            hub.write_text('<html lang="ar" dir="rtl"><main></main></html>', encoding="utf-8")
            module.publish(site)
            first = hub.read_text(encoding="utf-8")
            first_sitemap = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            module.publish(site)
            second = hub.read_text(encoding="utf-8")
            second_sitemap = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            self.assertEqual(first, second)
            self.assertEqual(first_sitemap, second_sitemap)
            report = json.loads((site / "api" / "inclusive-disability-language-v186.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")
            self.assertNotEqual(report["status"], "published")


# Production publication gate regression coverage.
if __name__ == "__main__":
    unittest.main()
