import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v190" / "accessible-arabic-digital-content-ar.json"
SCRIPT = ROOT / "scripts" / "publish_accessible_arabic_content_v190.py"
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"

spec = importlib.util.spec_from_file_location("accessible_arabic_content_v190", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class AccessibleArabicContentV190Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTENT.read_text(encoding="utf-8"))

    def test_depth_scope_and_low_risk_boundaries(self):
        self.assertEqual(self.data["status"], "internally-reviewed")
        self.assertEqual(self.data["risk_level"], "low")
        self.assertGreaterEqual(len(self.data["sections"]), 9)
        self.assertGreaterEqual(len(self.data["checklist"]), 10)
        self.assertGreaterEqual(len(self.data["examples"]), 6)
        limits = self.data["scope_limits"]
        for marker in ["ليس شهادة امتثال", "اختبار الإتاحة", "سياقه الفعلي"]:
            self.assertIn(marker, limits)

    def test_content_covers_core_accessibility_work(self):
        text = json.dumps(self.data, ensure_ascii=False)
        for marker in [
            "H1", "نصًا بديلًا", "ترجمة نصية", "لوحة المفاتيح", "موضع التركيز",
            "تسمية دائمة", "الحمل المعرفي", "قارئ الشاشة", "اختبار يدوي",
        ]:
            self.assertIn(marker, text)
        for forbidden in ["مضمون 100%", "شهادة WCAG", "يعالج الإعاقة", "اضغط هنا</a>"]:
            self.assertNotIn(forbidden, text)

    def test_sources_are_official_unique_and_contract_ready(self):
        sources = self.data["sources"]
        self.assertEqual(len(sources), 4)
        self.assertEqual(len({item["id"] for item in sources}), 4)
        self.assertEqual(len({item["url"] for item in sources}), 4)
        for source in sources:
            self.assertEqual(source["publisher"], "W3C Web Accessibility Initiative")
            self.assertTrue(source["url"].startswith("https://www.w3.org/WAI/"))
            self.assertIsInstance(source["year"], int)
            self.assertEqual(source["source_type"], "official_guideline")
            self.assertEqual(source["status"], "current")
            self.assertRegex(source["verified_at"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(source["claims_supported"])

    def test_build_has_seo_schema_rtl_print_and_contextual_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            for relative in [
                "special-needs/index.html",
                "audiences/teacher/index.html",
                "audiences/family/index.html",
            ]:
                path = site / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<html lang="ar" dir="rtl"><main><h1>مركز</h1></main></html>', encoding="utf-8")
            output = module.publish(site)
            page = output.read_text(encoding="utf-8")
            self.assertEqual(page.count("<h1>"), 1)
            for marker in [
                '<html lang="ar" dir="rtl">', 'rel="canonical"',
                'name="robots" content="index,follow"', 'name="twitter:card"',
                'property="og:title"', '"@type": "Article"',
                '"@type": "BreadcrumbList"', '"citation"', '@media print', ':focus-visible',
            ]:
                self.assertIn(marker, page)
            href = "/special-needs/accessible-arabic-digital-content/"
            for relative in [
                "special-needs/index.html",
                "audiences/teacher/index.html",
                "audiences/family/index.html",
            ]:
                self.assertIn(href, (site / relative).read_text(encoding="utf-8"))
            canonical = "https://healthrenewal.org" + href
            sitemap = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            self.assertEqual(sitemap.count(canonical), 1)

    def test_production_pipeline_invokes_after_existing_special_needs_guides(self):
        text = APPLY.read_text(encoding="utf-8")
        caregiver = 'run_publisher("publish_caregiver_wellbeing_v188.py")'
        accessible = 'run_publisher("publish_accessible_arabic_content_v190.py")'
        sitemap = 'register_sitemap("sitemap-accessible-arabic-content.xml")'
        self.assertEqual(text.count(accessible), 1)
        self.assertEqual(text.count(sitemap), 1)
        self.assertLess(text.index(caregiver), text.index(accessible))
        self.assertLess(text.index(accessible), text.index(sitemap))
        self.assertIn('"accessible_arabic_content_publisher": 190', text)
        self.assertIn('"accessible_arabic_content_sitemap_sync": 191', text)

    def test_build_is_idempotent_and_explicitly_not_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            for relative in ["special-needs/index.html", "audiences/teacher/index.html", "audiences/family/index.html"]:
                path = site / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<html lang="ar" dir="rtl"><main></main></html>', encoding="utf-8")
            module.publish(site)
            first = {
                relative: (site / relative).read_text(encoding="utf-8")
                for relative in ["special-needs/index.html", "audiences/teacher/index.html", "audiences/family/index.html"]
            }
            first_sitemap = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            module.publish(site)
            second = {
                relative: (site / relative).read_text(encoding="utf-8")
                for relative in ["special-needs/index.html", "audiences/teacher/index.html", "audiences/family/index.html"]
            }
            self.assertEqual(first, second)
            self.assertEqual(first_sitemap, (site / module.SITEMAP_NAME).read_text(encoding="utf-8"))
            report = json.loads((site / "api" / "accessible-arabic-digital-content-v190.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")
            self.assertNotEqual(report["status"], "published")
            self.assertEqual(report["risk_level"], "low")


if __name__ == "__main__":
    unittest.main()
