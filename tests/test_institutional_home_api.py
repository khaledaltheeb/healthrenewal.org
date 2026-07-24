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
