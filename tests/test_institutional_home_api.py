import importlib.util
import json
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class InstitutionalHomeApiTests(unittest.TestCase):
    def test_homepage_is_user_facing_and_has_one_h1(self):
        page = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("<h1>"), 1)
        self.assertIn("assets/brand/logo-mark.svg", page)
        self.assertIn("api/v1/openapi.json", page)
        for internal_phrase in (
            "خطة نمو قابلة للقياس",
            "هدف معلن للموسوعة",
            "خط أساس المصدر الحالي",
            "يُحسب العدد من حزمة الإنتاج",
            "لا نشر قبل البوابات",
        ):
            self.assertNotIn(internal_phrase, page)

    def test_homepage_inventory_sync_accepts_previous_public_count(self):
        script_path = ROOT / "scripts" / "apply_homepage_v20.py"
        spec = importlib.util.spec_from_file_location("apply_homepage_v20", script_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        previous_card = (
            '<article class="stat"><strong>88</strong><span>'
            "مقياسًا وأداة وقدرة معرفية في المختبرات الحالية بحدود استخدام واضحة."
            "</span></article>"
        )
        synchronized = module.synchronize_homepage_lab_inventory(previous_card)
        self.assertIn("<strong>93</strong>", synchronized)
        self.assertNotIn("<strong>88</strong>", synchronized)

    def test_homepage_report_preserves_inventory_field_compatibility(self):
        publisher = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"lab_inventory_updated": True', publisher)
        self.assertIn('"lab_inventory_metadata_updated": True', publisher)

    def test_public_special_needs_publisher_has_no_operational_copy(self):
        publisher = (ROOT / "scripts" / "publish_special_needs_v73.py").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "قيد الإعداد المنظم",
            "قيد التوسع",
            "الأشخاص ذوي الإعاقة",
        ):
            self.assertNotIn(phrase, publisher)
        self.assertIn("استكشاف موارد التواصل والإتاحة", publisher)
        self.assertIn("فتح الأدلة الأسرية العملية", publisher)

    def test_manifest_and_api_documents_are_valid_json(self):
        paths = (
            "manifest.webmanifest",
            "api/v1/platform.json",
            "api/v1/openapi.json",
            "api/v1/courses.schema.json",
            "api/v1/courses.example.json",
        )
        documents = {}
        for relative_path in paths:
            with self.subTest(path=relative_path):
                documents[relative_path] = json.loads(
                    (ROOT / relative_path).read_text(encoding="utf-8")
                )

        self.assertEqual(documents["api/v1/openapi.json"]["openapi"], "3.1.0")
        self.assertEqual(
            documents["api/v1/courses.schema.json"]["properties"]["authorization"]["properties"]["status"]["const"],
            "authorized",
        )
        self.assertTrue(
            documents["api/v1/courses.example.json"]["courses"][0]["rights"]["metadataReuse"]
        )
        self.assertFalse(
            documents["api/v1/courses.example.json"]["courses"][0]["rights"]["contentReuse"]
        )

    def test_brand_and_search_xml_are_well_formed(self):
        for relative_path in (
            "assets/brand/logo-mark.svg",
            "assets/brand/logo.svg",
            "assets/brand/social-card.svg",
            "opensearch.xml",
        ):
            with self.subTest(path=relative_path):
                ET.parse(ROOT / relative_path)


if __name__ == "__main__":
    unittest.main()
