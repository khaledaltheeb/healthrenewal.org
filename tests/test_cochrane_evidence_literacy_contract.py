import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/institutional-resources/cochrane-evidence-literacy.json"
PAGE = ROOT / "learning-paths/how-to-read-health-evidence/index.html"


class CochraneEvidenceLiteracyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_registry_has_governed_rights_and_dates(self):
        rights = self.registry["rights"]
        self.assertEqual(rights["classification"], "link-and-attribution-only")
        self.assertFalse(self.registry["provider"]["partnership_or_endorsement"])
        self.assertIn("copy_or_translate_course_content", rights["prohibited"])
        self.assertIn("use_logos_or_trademarks_as_affiliation", rights["prohibited"])
        self.assertRegex(self.registry["verification"]["verified_at"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertRegex(self.registry["verification"]["next_review_at"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(self.registry["verification"]["external_review"], "not-completed")

    def test_official_resources_are_https_and_cochrane_only(self):
        resources = self.registry["official_resources"]
        self.assertGreaterEqual(len(resources), 5)
        for resource in resources:
            self.assertTrue(resource["url"].startswith("https://"))
            self.assertRegex(resource["url"], r"^https://www\.cochrane\.org/")

    def test_page_has_unique_h1_rtl_canonical_and_learning_schema(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertEqual(len(re.findall(r"<h1\b", self.html, re.I)), 1)
        self.assertIn('rel="canonical" href="https://healthrenewal.org/learning-paths/how-to-read-health-evidence/"', self.html)
        self.assertIn('"@type":"LearningResource"', self.html)
        self.assertIn('id="main-content"', self.html)
        self.assertIn('aria-label="التنقل الرئيسي"', self.html)

    def test_page_teaches_core_evidence_literacy_dimensions(self):
        required = [
            "ما السؤال الحقيقي؟",
            "ما نوع الدليل؟",
            "ما حجم الأثر؟",
            "ما مقدار عدم اليقين؟",
            "ماذا عن الضرر والانسحاب؟",
            "هل تنطبق النتيجة هنا؟",
            "التمويل والتعارض",
            "ما الذي لا تثبته الدراسة",
        ]
        for phrase in required:
            self.assertIn(phrase, self.html)

    def test_page_links_to_originals_without_copy_or_affiliation_claims(self):
        required_urls = [item["url"] for item in self.registry["official_resources"]]
        for url in required_urls:
            self.assertIn(url, self.html)
        self.assertIn("لا توجد شراكة أو مصادقة أو صفة Affiliate", self.html)
        self.assertIn("لا نعيد نشر أو ترجمة مواد الدورات", self.html)
        forbidden = [
            "شريك Cochrane",
            "معتمد من Cochrane",
            "Cochrane Affiliate لدى منصة روافد",
            "شعار Cochrane",
        ]
        for phrase in forbidden:
            self.assertNotIn(phrase, self.html)

    def test_safety_and_print_contracts_are_visible(self):
        self.assertIn("لا يقدم تشخيصًا أو علاجًا فرديًا", self.html)
        self.assertIn("لا يحل محل التقييم أو المشورة الطبية الفردية", self.html)
        self.assertIn("@media print", self.html)
        self.assertIn("2026-11-05", REGISTRY.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
