import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "guides/accessible-travel-planning/index.html"
REGISTRY = ROOT / "data/institutional-resources/enat-accessible-travel.json"


class EnatAccessibleTravelContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.data = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_governance_and_rights_are_explicit(self):
        self.assertEqual(self.data["classification"], "link-and-attribution-only")
        prohibited = set(self.data["prohibited"])
        self.assertIn("use_enat_logo", prohibited)
        self.assertIn("claim_membership_partnership_endorsement_or_certification", prohibited)
        self.assertIn("copy_or_republish_protected_content", prohibited)
        self.assertEqual(self.data["verified_at"], "2026-08-05")
        self.assertRegex(self.data["next_review_at"], r"^2026-\d{2}-\d{2}$")

    def test_official_sources_use_https_and_are_unique(self):
        urls = [item["url"] for item in self.data["sources"]]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(url.startswith("https://") for url in urls))
        self.assertTrue(any("accessibletourism.org" in url for url in urls))
        self.assertTrue(any("pantou.org" in url for url in urls))

    def test_page_has_core_metadata_and_schema(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertIn('rel="canonical" href="https://healthrenewal.org/guides/accessible-travel-planning/"', self.html)
        self.assertIn('application/ld+json', self.html)
        self.assertIn('"@type":"Guide"', self.html)
        self.assertIn('"inLanguage":"ar"', self.html)

    def test_page_has_practical_depth_and_scope_limits(self):
        required = [
            "أسئلة الإقامة قبل الحجز",
            "أسئلة النقل والمطار",
            "الأدوية والأجهزة والطوارئ",
            "سجل تحقق قبل الدفع",
            "لا يضمن إتاحة أي وجهة",
            "لا تغيّر جرعة",
        ]
        for phrase in required:
            self.assertIn(phrase, self.html)
        self.assertGreaterEqual(len(re.findall(r"<li>", self.html)), 25)

    def test_accessibility_print_and_reduced_motion_contracts(self):
        self.assertIn('aria-label="مسار الصفحة"', self.html)
        self.assertIn('aria-labelledby="sources-heading"', self.html)
        self.assertIn('@media print', self.html)
        self.assertIn('prefers-reduced-motion:reduce', self.html)
        self.assertNotIn('target="_blank"', self.html)

    def test_no_brand_or_partnership_claim(self):
        lowered = self.html.lower()
        self.assertNotIn("<img", lowered)
        self.assertNotIn("شريك مع enat", lowered)
        self.assertNotIn("معتمد من enat", lowered)
        self.assertIn("ولا تعني شراكة أو اعتمادًا", self.html)


if __name__ == "__main__":
    unittest.main()
