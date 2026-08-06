import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "institutional-resources" / "thoth-open-books-discovery.json"
PAGE = ROOT / "resources" / "open-books-discovery" / "index.html"


class ThothOpenBooksDiscoveryContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(DATA.read_text(encoding="utf-8"))
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_governance_files_exist(self):
        self.assertTrue(DATA.is_file())
        self.assertTrue(PAGE.is_file())

    def test_rights_classification_is_metadata_only(self):
        self.assertEqual(self.record["classification"], "open-license-metadata")
        self.assertEqual(self.record["license"]["metadata"], "CC0-1.0")
        boundary = self.record["license"]["important_boundary"]
        self.assertIn("لا يثبت تلقائيًا", boundary)
        prohibited = " ".join(self.record["permission_scope"]["prohibited"])
        for phrase in ("إنشاء Health Renewal كناشر", "الأغلفة", "النصوص الكاملة", "ادعاء شراكة"):
            self.assertIn(phrase, prohibited)

    def test_official_sources_are_https_and_thoth_first_party(self):
        resources = self.record["official_resources"]
        self.assertGreaterEqual(len(resources), 4)
        for resource in resources:
            self.assertTrue(resource["url"].startswith("https://thoth.pub/"))

    def test_record_contract_requires_legal_and_freshness_fields(self):
        required = set(self.record["record_contract"]["required_fields"])
        expected = {
            "title", "publisher", "landing_page", "work_identifier",
            "license_url", "license_verified_on", "metadata_source_url",
            "publisher_source_url", "access_status", "review_status",
        }
        self.assertTrue(expected.issubset(required))
        rules = " ".join(self.record["record_contract"]["quality_rules"])
        self.assertIn("لا يُعرض زر تنزيل", rules)
        self.assertIn("لا تستخدم صورة غلاف", rules)
        self.assertIn("لا تُستنتج الجودة العلمية", rules)

    def test_review_and_attribution_are_truthful(self):
        self.assertEqual(
            self.record["verification"]["status"],
            "internally-reviewed-not-externally-endorsed",
        )
        self.assertTrue(self.record["attribution"]["no_partnership_claim"])
        self.assertFalse(self.record["attribution"]["logo_use"])
        self.assertEqual(
            self.record["publication"]["canonical"],
            "https://healthrenewal.org/resources/open-books-discovery/",
        )

    def test_page_metadata_and_schema(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', self.html)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/resources/open-books-discovery/">',
            self.html,
        )
        self.assertIn('"@type": "HowTo"', self.html)
        self.assertIn('"@type": "BreadcrumbList"', self.html)
        self.assertIn('"@type": "WebPage"', self.html)
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)

    def test_page_explains_metadata_does_not_license_book(self):
        required_phrases = (
            "رخصة CC0 لسجل البيانات لا تعني",
            "صفحة الناشر أو الكتاب الأصلية",
            "لا تنشئ ناشرًا باسم طرف آخر",
            "لا توجد شراكة أو عضوية أو مراجعة خارجية",
            "الترخيص المفتوح لا يساوي الدقة العلمية",
        )
        for phrase in required_phrases:
            self.assertIn(phrase, self.html)

    def test_accessibility_mobile_print_and_reduced_motion(self):
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('id="main-content"', self.html)
        self.assertIn(':focus-visible', self.html)
        self.assertIn('@media (max-width: 38rem)', self.html)
        self.assertIn('@media print', self.html)
        self.assertIn('prefers-reduced-motion: reduce', self.html)
        self.assertNotIn('user-scalable=no', self.html)
        self.assertNotIn('maximum-scale=1', self.html)

    def test_internal_links_and_official_external_links(self):
        for path in ("/resources/", "/research/", "/accessibility/", "/about/editorial-policy/"):
            self.assertIn(f'href="{path}"', self.html)
        for url in (
            "https://thoth.pub/docs/policies/terms-thoth-metadata",
            "https://thoth.pub/books",
            "https://thoth.pub/publishers",
            "https://creativecommons.org/publicdomain/zero/1.0/",
        ):
            self.assertIn(f'href="{url}"', self.html)

    def test_no_logo_image_or_partnership_claim(self):
        self.assertNotRegex(self.html, r"<img\b")
        forbidden = ("شريك رسمي", "معتمد من Thoth", "بالتعاون مع Thoth")
        for phrase in forbidden:
            self.assertNotIn(phrase, self.html)


if __name__ == "__main__":
    unittest.main()
