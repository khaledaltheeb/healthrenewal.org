from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "materialize_sectors_v10_compat_v4.py"
SOURCE_PATH = ROOT / "content" / "sectors-v10" / "clinical-anxiety.json"
SPEC = importlib.util.spec_from_file_location(
    "materialize_sectors_v10_compat_v4", SCRIPT_PATH
)
assert SPEC and SPEC.loader
v4 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = v4
SPEC.loader.exec_module(v4)


class MaterializeSectorsV10CompatV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    def test_rich_clinical_source_is_complete_and_governed(self) -> None:
        articles = self.source["articles"]
        self.assertEqual(len(articles), 5)
        self.assertEqual(
            {article["slug"] for article in articles},
            {
                "anxiety-normal-response-versus-disorder",
                "panic-attack-versus-panic-disorder",
                "ocd-versus-intrusive-thoughts",
                "treatment-options-and-shared-decisions",
                "urgent-assessment-and-safety",
            },
        )
        self.assertTrue(
            all(len(article.get("assessment_questions", [])) >= 5 for article in articles)
        )
        self.assertTrue(all(len(article.get("signals", [])) >= 5 for article in articles))
        self.assertTrue(all(len(article.get("steps", [])) >= 5 for article in articles))
        self.assertEqual(
            {source["id"] for source in self.source["sources"]},
            {
                "who-anxiety",
                "nice-cg113",
                "nice-cg31",
                "who-mhgap-2023",
                "nimh-panic",
                "nimh-ocd",
            },
        )
        self.assertTrue(all(source["url"].startswith("https://") for source in self.source["sources"]))
        self.assertEqual(self.source["review_status"], "internally-reviewed")
        self.assertEqual(self.source["external_review"], "recommended-not-completed")
        self.assertIn("لا تبدأ دواءً", self.source["disclaimer"])

    def test_v4_normalizes_without_discarding_rich_fields(self) -> None:
        payload = copy.deepcopy(self.source)
        original_questions = {
            article["slug"]: list(article["assessment_questions"])
            for article in payload["articles"]
        }
        v4.normalize_payload(payload)

        for article in payload["articles"]:
            self.assertEqual(
                article["questions"], original_questions[article["slug"]]
            )
            self.assertEqual(
                article["assessment_questions"], original_questions[article["slug"]]
            )
        self.assertEqual(
            payload["internal_links"],
            [
                "/daily-tools/medical-visit-preparation/",
                "/assessment-lab/",
                "/mental-health/",
                "/safety/",
            ],
        )
        self.assertEqual(
            payload["_internal_link_labels"]["/assessment-lab/"],
            "مختبر التقييمات النفسية الآمنة",
        )
        self.assertIsInstance(payload["source_log"]["limitations"], str)
        self.assertIn(
            "لا توجد مراجعة خارجية موثقة",
            payload["source_log"]["limitations"],
        )

    def test_legacy_family_route_is_canonicalized_without_losing_label(self) -> None:
        payload = {
            "articles": [],
            "internal_links": [
                "/family/",
                {"label": "دليل الأسرة", "url": "/family/"},
                "/services/",
            ],
        }
        v4.normalize_payload(payload)

        self.assertNotIn("/family/", payload["internal_links"])
        self.assertEqual(payload["internal_links"].count("/sectors/family/"), 2)
        self.assertIn("/services/", payload["internal_links"])
        self.assertEqual(
            payload["_internal_link_labels"]["/sectors/family/"],
            "دليل الأسرة",
        )

    def test_validation_and_rendering_publish_all_five_units(self) -> None:
        payload = copy.deepcopy(self.source)
        v4.validate_source(SOURCE_PATH, payload)
        item = v4.PublicationItem(
            source_path=SOURCE_PATH,
            payload=payload,
            category=v4.base.classify(payload),
            route="evidence-guides/clinical-anxiety/",
        )
        page = v4.render_page(item)

        self.assertIn('<html lang="ar" dir="rtl">', page)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/evidence-guides/clinical-anxiety/">',
            page,
        )
        self.assertIn('"MedicalWebPage"', page)
        self.assertIn('"CollectionPage"', page)
        self.assertEqual(page.count('id="practical-questions"'), 1)
        self.assertEqual(page.count('id="governance"'), 1)
        self.assertEqual(page.count('id="related-links"'), 1)
        for article in self.source["articles"]:
            self.assertIn(article["title"], page)
            self.assertIn(article["assessment_questions"][0], page)
        self.assertIn("مختبر التقييمات النفسية الآمنة", page)
        self.assertIn("خطة التعامل مع الأزمات", page)
        self.assertIn("هذه الصفحة للتثقيف العام ولا تثبت تشخيصًا", page)
        self.assertIn("مراجعة خارجية موصى بها ولم تكتمل", page)
        self.assertIn("علامات الخطر التي تستلزم تصعيدًا عاجلًا", page)
        self.assertNotIn("معاقين", page)
        self.assertNotIn("شراكة مع منظمة الصحة العالمية", page)

    def test_canonical_mismatch_remains_blocking(self) -> None:
        payload = copy.deepcopy(self.source)
        payload["canonical"] = "https://healthrenewal.org/wrong-route/"
        with self.assertRaises(v4.PublicationError):
            v4.validate_source(SOURCE_PATH, payload)


if __name__ == "__main__":
    unittest.main()
