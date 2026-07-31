import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v188" / "caregiver-wellbeing-ar.json"
SCRIPT = ROOT / "scripts" / "publish_caregiver_wellbeing_v188.py"
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"

spec = importlib.util.spec_from_file_location("caregiver_wellbeing_v188", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class CaregiverWellbeingV188Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTENT.read_text(encoding="utf-8"))

    def test_depth_safety_and_nonclinical_boundaries(self):
        self.assertEqual(self.data["status"], "internally-reviewed")
        self.assertEqual(self.data["risk_level"], "moderate")
        self.assertGreaterEqual(len(self.data["sections"]), 7)
        self.assertGreaterEqual(len(self.data["two_week_checklist"]), 8)
        self.assertGreaterEqual(len(self.data["support_plan"]), 5)
        limits = self.data["professional_limits"]
        for marker in ["لا يشخّص", "لا يستبدل", "الطوارئ المحلية"]:
            self.assertIn(marker, limits)

    def test_language_prevents_blame_coercion_and_self_diagnosis(self):
        text = json.dumps(self.data, ensure_ascii=False)
        for marker in ["الشعور بالذنب", "لا تستخدم الخوف", "مشاركة", "الخصوصية", "الاختبارات العامة"]:
            self.assertIn(marker, text)
        self.assertNotIn("عليك التحمل", text)
        self.assertNotIn("تشخيص مؤكد", text)

    def test_sources_follow_evidence_contract(self):
        sources = self.data["sources"]
        self.assertEqual(len(sources), 3)
        self.assertEqual(len({item["id"] for item in sources}), 3)
        self.assertEqual(len({item["url"] for item in sources}), 3)
        allowed = {"official_guideline", "public_health_authority", "institutional_fact_sheet"}
        for source in sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIsInstance(source["year"], int)
            self.assertIn(source["source_type"], allowed)
            self.assertEqual(source["status"], "current")
            self.assertTrue(source["claims_supported"])
            self.assertRegex(source["verified_at"], r"^20\d{2}-\d{2}-\d{2}$")

    def test_build_has_seo_schema_print_links_and_sitemap(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            for relative in ["special-needs/index.html", "audiences/family/index.html"]:
                path = site / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('<html lang="ar" dir="rtl"><main><h1>مركز</h1></main></html>', encoding="utf-8")
            output = module.publish(site)
            page = output.read_text(encoding="utf-8")
            self.assertEqual(page.count("<h1>"), 1)
            for marker in ['rel="canonical"', 'name="robots" content="index,follow"', 'name="twitter:card"', '"@type": "Article"', '"@type": "BreadcrumbList"', '@media print']:
                self.assertIn(marker, page)
            href = "/special-needs/caregiver-wellbeing/"
            self.assertIn(href, (site / "special-needs/index.html").read_text(encoding="utf-8"))
            self.assertIn(href, (site / "audiences/family/index.html").read_text(encoding="utf-8"))
            sitemap = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            self.assertEqual(sitemap.count("https://healthrenewal.org" + href), 1)
            report = json.loads((site / "api" / "caregiver-wellbeing-v188.json").read_text(encoding="utf-8"))
            self.assertEqual(report["sitemap"], f"/{module.SITEMAP_NAME}")

    def test_production_pipeline_invokes_publisher_and_registers_sitemap_once(self):
        text = APPLY.read_text(encoding="utf-8")
        inclusive = 'run_publisher("publish_inclusive_disability_language_v186.py")'
        caregiver = 'run_publisher("publish_caregiver_wellbeing_v188.py")'
        sitemap = 'register_sitemap("sitemap-caregiver-wellbeing.xml")'
        self.assertEqual(text.count(caregiver), 1)
        self.assertEqual(text.count(sitemap), 1)
        self.assertLess(text.index(inclusive), text.index(caregiver))
        self.assertLess(text.index(caregiver), text.index(sitemap))
        self.assertIn('"caregiver_wellbeing_publisher": 188', text)
        self.assertIn('"caregiver_wellbeing_sitemap_sync": 189', text)

    def test_build_is_idempotent_and_explicitly_not_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            hub = site / "special-needs" / "index.html"
            hub.parent.mkdir(parents=True)
            hub.write_text('<html lang="ar" dir="rtl"><main></main></html>', encoding="utf-8")
            module.publish(site)
            first = hub.read_text(encoding="utf-8")
            first_sitemap = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            module.publish(site)
            self.assertEqual(first, hub.read_text(encoding="utf-8"))
            self.assertEqual(first_sitemap, (site / module.SITEMAP_NAME).read_text(encoding="utf-8"))
            report = json.loads((site / "api" / "caregiver-wellbeing-v188.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")
            self.assertNotEqual(report["status"], "published")


if __name__ == "__main__":
    unittest.main()
