from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "apply_structured_data_v332.py"
SPEC = importlib.util.spec_from_file_location("structured_data_v332", MODULE_PATH)
assert SPEC and SPEC.loader
schema = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = schema
SPEC.loader.exec_module(schema)


class StructuredDataV332Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, body: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def managed_payload(self, path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        matches = re.findall(
            r'<script type="application/ld\+json" data-pterminology-schema="v332">\s*(.*?)\s*</script>',
            text,
            re.S,
        )
        self.assertEqual(len(matches), 1)
        return json.loads(matches[0])

    @staticmethod
    def types(payload: dict) -> set[str]:
        return set(schema.walk_types(payload))

    def test_medical_condition_requires_explicit_opt_in_and_codes(self) -> None:
        explicit = self.write(
            "special-needs/autism/index.html",
            """<html lang='ar'><head><title>اضطراب طيف التوحد</title>
            <meta name='description' content='دليل عربي موثق حول الحالة.'>
            <meta name='schema:type' content='MedicalCondition'>
            <meta name='medical-code' content='6A02'>
            <meta name='medical-coding-system' content='ICD-11'>
            <meta name='medical-symptoms' content='اختلافات التواصل، أنماط متكررة'>
            </head><body><h1>اضطراب طيف التوحد</h1></body></html>""",
        )
        generic = self.write(
            "special-needs/inclusive-support/index.html",
            """<html lang='ar'><head><title>الدعم الدامج</title>
            <meta name='description' content='دليل للدعم الدامج دون تحويله إلى تشخيص.'>
            </head><body><h1>الدعم الدامج</h1></body></html>""",
        )
        report = schema.process(self.root, "https://example.test/", strict=True)
        self.assertEqual(report["medical_condition_pages"], 1)
        payload = self.managed_payload(explicit)
        condition = next(node for node in payload["@graph"] if node.get("@type") == "MedicalCondition")
        self.assertEqual(condition["code"]["codeValue"], "6A02")
        self.assertEqual(condition["code"]["codingSystem"], "ICD-11")
        self.assertNotIn("MedicalCondition", self.types(self.managed_payload(generic)))

    def test_faq_schema_uses_only_visible_details_content(self) -> None:
        page = self.write(
            "encyclopedia/anxiety/index.html",
            """<html lang='ar'><head><title>القلق</title><meta name='description' content='شرح القلق.'></head>
            <body><h1>القلق</h1><details><summary>متى أطلب المساعدة؟</summary>
            <p>اطلب المساعدة عندما يستمر الأثر أو يعطل الحياة اليومية.</p></details></body></html>""",
        )
        schema.process(self.root, "https://example.test/", strict=True)
        payload = self.managed_payload(page)
        faq = next(node for node in payload["@graph"] if node.get("@type") == "FAQPage")
        entity = faq["mainEntity"][0]
        self.assertEqual(entity["name"], "متى أطلب المساعدة؟")
        self.assertIn("يعطل الحياة اليومية", entity["acceptedAnswer"]["text"])

    def test_reviewer_is_not_invented_or_emitted_when_not_visible(self) -> None:
        page = self.write(
            "encyclopedia/sleep/index.html",
            """<html lang='ar'><head><title>النوم</title>
            <meta name='description' content='دليل النوم.'><meta name='reviewed-by' content='اسم غير ظاهر'>
            </head><body><h1>النوم</h1><p>محتوى تثقيفي.</p></body></html>""",
        )
        schema.process(self.root, "https://example.test/", strict=True)
        payload = self.managed_payload(page)
        webpage = next(node for node in payload["@graph"] if str(node.get("@type", "")).endswith("WebPage"))
        self.assertNotIn("reviewedBy", webpage)

    def test_article_and_source_citation_are_classified_without_claiming_original_research(self) -> None:
        page = self.write(
            "magazine/critical-reading/index.html",
            """<html lang='ar'><head><title>قراءة نقدية</title><meta name='description' content='قراءة نقدية عربية.'>
            <meta name='article:published_time' content='2026-07-28'></head><body><h1>قراءة نقدية</h1>
            <a href='https://doi.org/10.1000/example'>الدراسة الأصلية</a></body></html>""",
        )
        schema.process(self.root, "https://example.test/", strict=True)
        payload = self.managed_payload(page)
        article = next(node for node in payload["@graph"] if node.get("@type") == "Article")
        self.assertEqual(article["datePublished"], "2026-07-28")
        self.assertEqual(article["citation"], ["https://doi.org/10.1000/example"])
        self.assertNotIn("MedicalScholarlyArticle", self.types(payload))

    def test_interactive_pages_get_web_application(self) -> None:
        page = self.write(
            "daily-tools/breathing/index.html",
            """<html lang='ar'><head><title>أداة التنفس</title><meta name='description' content='أداة عملية.'></head>
            <body><h1>أداة التنفس</h1><form><input><button>ابدأ</button></form></body></html>""",
        )
        schema.process(self.root, "https://example.test/", strict=True)
        payload = self.managed_payload(page)
        app = next(node for node in payload["@graph"] if node.get("@type") == "WebApplication")
        self.assertEqual(app["offers"]["price"], "0")
        self.assertEqual(app["offers"]["priceCurrency"], "JOD")

    def test_second_run_is_byte_idempotent(self) -> None:
        page = self.write(
            "index.html",
            "<html lang='ar'><head><title>الرئيسية</title><meta name='description' content='الصفحة الرئيسية.'></head><body><h1>الرئيسية</h1></body></html>",
        )
        schema.process(self.root, "https://example.test/", strict=True)
        first = page.read_bytes()
        schema.process(self.root, "https://example.test/", strict=True)
        second = page.read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(second.count(b'data-pterminology-schema="v332"'), 1)

    def test_invalid_legacy_jsonld_is_removed_without_corrupting_managed_graph(self) -> None:
        page = self.write(
            "terms/example/index.html",
            """<html lang='ar'><head><title>مثال</title><meta name='description' content='صفحة مثال.'>
            <script type='application/ld+json'>{invalid json}</script></head><body><h1>مثال</h1></body></html>""",
        )
        report = schema.process(self.root, "https://example.test/", strict=True)
        self.assertEqual(len(report["invalid_existing_jsonld_removed"]), 1)
        self.assertNotIn("{invalid json}", page.read_text(encoding="utf-8"))
        self.assertIn("WebSite", self.types(self.managed_payload(page)))


if __name__ == "__main__":
    unittest.main()
