import json
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

    def test_rights_and_sources(self):
        self.assertEqual(self.data["classification"], "link-and-attribution-only")
        self.assertIn("use_enat_logo", self.data["prohibited"])
        self.assertIn("claim_membership_partnership_endorsement_or_certification", self.data["prohibited"])
        urls = [source["url"] for source in self.data["sources"]]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(url.startswith("https://") for url in urls))

    def test_metadata_schema_rtl_and_accessibility(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('name="viewport"', self.html)
        self.assertIn('rel="canonical" href="https://healthrenewal.org/guides/accessible-travel-planning/"', self.html)
        self.assertIn('"@type":"Guide"', self.html)
        self.assertIn('aria-label="مسار الصفحة"', self.html)
        self.assertIn('aria-labelledby="sources-heading"', self.html)
        self.assertIn('@media print', self.html)
        self.assertIn('prefers-reduced-motion:reduce', self.html)

    def test_practical_depth_and_scope(self):
        for phrase in ["أسئلة الإقامة قبل الحجز", "أسئلة النقل والمطار", "الأدوية والأجهزة والطوارئ", "سجل تحقق قبل الدفع", "لا يضمن إتاحة أي وجهة", "لا تغيّر جرعة"]:
            self.assertIn(phrase, self.html)
        self.assertGreaterEqual(self.html.count("<li>"), 25)
        self.assertIn("ولا تعني شراكة أو اعتمادًا", self.html)
        self.assertNotIn("<img", self.html.lower())

if __name__ == "__main__":
    unittest.main()
