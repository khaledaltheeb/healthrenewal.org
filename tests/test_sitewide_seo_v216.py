import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enhance_sitewide_seo_v216.py"


def load_module():
    spec = importlib.util.spec_from_file_location("enhance_sitewide_seo_v216", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load SEO module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SitewideSeoV216Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.site = Path(self.temp.name)
        self.module = load_module()
        self.module.SITE = self.site

    def tearDown(self):
        self.temp.cleanup()

    def write_page(self, relative: str, head: str, body: str) -> Path:
        path = self.site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'<!doctype html><html lang="ar" dir="rtl"><head>{head}</head>'
            f'<body><main>{body}</main></body></html>',
            encoding="utf-8",
        )
        return path

    def test_enriches_article_and_is_idempotent(self):
        page = self.write_page(
            "encyclopedia/anxiety/index.html",
            "<meta charset=\"utf-8\"><title>القلق | مصطلحات علم النفس</title>"
            "<meta name=\"description\" content=\"شرح عربي منظم للقلق وأثره وخيارات الدعم.\">",
            "<h1>القلق</h1><p>محتوى مفيد.</p>",
        )
        changed, result = self.module.enrich_page(page)
        self.assertTrue(changed)
        self.assertEqual(result["status"], "modified")
        source = page.read_text(encoding="utf-8")
        self.assertIn('name="keywords"', source)
        self.assertIn('property="og:title"', source)
        self.assertIn('name="twitter:card" content="summary_large_image"', source)
        self.assertIn('property="article:tag"', source)
        self.assertIn('type="application/ld+json"', source)
        self.assertIn(
            'href="https://healthrenewal.org/encyclopedia/anxiety/"',
            source,
        )

        changed_again, result_again = self.module.enrich_page(page)
        self.assertFalse(changed_again)
        self.assertEqual(result_again["status"], "unchanged")
        stable = page.read_text(encoding="utf-8")
        self.assertEqual(stable.count('name="keywords"'), 1)
        self.assertEqual(stable.count('property="og:title"'), 1)
        self.assertEqual(stable.count('name="twitter:title"'), 1)
        self.assertEqual(stable.count('rel="canonical"'), 1)
        self.assertEqual(stable.count('type="application/ld+json"'), 1)

    def test_augments_existing_keywords_without_duplication(self):
        page = self.write_page(
            "special-needs/inclusive-education/index.html",
            "<title>التربية الدامجة | مصطلحات علم النفس</title>"
            "<meta name=\"description\" content=\"دليل عملي للتربية الدامجة.\">"
            "<meta name=\"keywords\" content=\"التربية الدامجة, الدعم الأسري\">",
            "<h1>التربية الدامجة</h1>",
        )
        self.module.enrich_page(page)
        source = page.read_text(encoding="utf-8")
        keyword_match = re.search(
            r'<meta name="keywords" content="([^"]+)"', source
        )
        self.assertIsNotNone(keyword_match)
        keywords = [item.strip() for item in keyword_match.group(1).split(",")]
        self.assertGreaterEqual(len(keywords), 5)
        self.assertEqual(len(keywords), len({item.casefold() for item in keywords}))
        self.assertIn("ذوو الاحتياجات الخاصة", keywords)
        self.assertLessEqual(len(keyword_match.group(1)), 480)

    def test_generic_collection_still_receives_five_precise_terms(self):
        page = self.write_page(
            "comparisons/comparison-001/index.html",
            "<title>الفرق بين القلق والخوف | مصطلحات علم النفس</title>"
            "<meta name=\"description\" content=\"مقارنة توضيحية بين القلق والخوف.\">",
            "<h1>الفرق بين القلق والخوف</h1>",
        )
        self.module.enrich_page(page)
        source = page.read_text(encoding="utf-8")
        keyword_match = re.search(
            r'<meta name="keywords" content="([^"]+)"', source
        )
        self.assertIsNotNone(keyword_match)
        keywords = [item.strip() for item in keyword_match.group(1).split(",")]
        self.assertGreaterEqual(len(keywords), 5)
        self.assertIn("التثقيف النفسي", keywords)

    def test_arabic_comma_headlines_are_serialization_stable(self):
        cases = (
            (
                "provider-assessment-demo/index.html",
                "منصة التقييم والسجل المهني | منصة الصحة النفسية وذوي الاحتياجات الخاصة",
                "منصة تقييم ذوي الاحتياجات الخاصة, المقاييس النفسية, التقييم المهني, سجل الحالات, التقارير المهنية, السلوك التكيفي, تقييم التوحد, صعوبات التعلم, التربية الخاصة",
                "أنشئ حالة، نفّذ جلسات، وسجّل التقييمات والفحوص والتقارير المهنية في مسار واحد.",
            ),
            (
                "provider-assessment-demo/professional-console.html",
                "السجل المهني للمقاييس والفحوص | منصة التقييم",
                "السجل المهني, المقاييس النفسية, تقييم ذوي الاحتياجات الخاصة, توثيق نتائج الاختبارات, التقارير المهنية",
                "اختر المقياس أو الفحص، اربطه بالحالة، ووثّق التطبيق والنتيجة والتقرير.",
            ),
        )
        for relative, title, existing_keywords, h1 in cases:
            with self.subTest(relative=relative):
                page = self.write_page(
                    relative,
                    f"<title>{title}</title>"
                    "<meta name=\"description\" content=\"وصف مهني منظم للصفحة.\">"
                    f"<meta name=\"keywords\" content=\"{existing_keywords}\">",
                    f"<h1>{h1}</h1>",
                )
                changed, _ = self.module.enrich_page(page)
                self.assertTrue(changed)
                first_output = page.read_text(encoding="utf-8")
                changed_again, result_again = self.module.enrich_page(page)
                self.assertFalse(changed_again)
                self.assertEqual(result_again["status"], "unchanged")
                self.assertEqual(page.read_text(encoding="utf-8"), first_output)
                keyword_match = re.search(
                    r'<meta name="keywords" content="([^"]+)"', first_output
                )
                self.assertIsNotNone(keyword_match)
                self.assertNotIn("،", keyword_match.group(1))

    def test_repairs_missing_title_description_and_canonical(self):
        page = self.write_page(
            "care-guides/sleep/index.html",
            "<meta charset=\"utf-8\">",
            "<h1>دليل النوم الصحي</h1>",
        )
        self.module.enrich_page(page)
        source = page.read_text(encoding="utf-8")
        self.assertIn("<title>دليل النوم الصحي", source)
        self.assertIn('name="description"', source)
        self.assertIn('rel="canonical"', source)
        self.assertIn('name="robots"', source)

    def test_noindex_page_is_not_modified(self):
        page = self.write_page(
            "private/index.html",
            "<title>خاص</title><meta name=\"robots\" content=\"noindex,nofollow\">",
            "<h1>خاص</h1>",
        )
        original = page.read_text(encoding="utf-8")
        changed, result = self.module.enrich_page(page)
        self.assertFalse(changed)
        self.assertEqual(result["status"], "skipped_noindex")
        self.assertEqual(page.read_text(encoding="utf-8"), original)

    def test_google_verification_file_is_skipped(self):
        path = self.site / "google644f1f7a8b7aaa2b.html"
        path.write_text("google-site-verification: token", encoding="utf-8")
        original = path.read_text(encoding="utf-8")
        changed, result = self.module.enrich_page(path)
        self.assertFalse(changed)
        self.assertEqual(result["status"], "skipped_special")
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_generated_schema_is_valid_json(self):
        page = self.write_page(
            "tips/breathing/index.html",
            "<title>تمرين التنفس | مصطلحات علم النفس</title>"
            "<meta name=\"description\" content=\"خطوات عملية لتمرين التنفس.\">",
            "<h1>تمرين التنفس</h1>",
        )
        self.module.enrich_page(page)
        source = page.read_text(encoding="utf-8")
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', source, re.S
        )
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        self.assertEqual(payload["@type"], "Article")
        self.assertGreaterEqual(len(payload["keywords"]), 5)

    def test_production_pipeline_wires_enricher_and_verifier(self):
        pipeline = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(
            encoding="utf-8"
        )
        enhancer = 'run_publisher("enhance_sitewide_seo_v216.py")'
        verifier = 'run_publisher("verify_sitewide_seo_v216.py")'
        health_gate = 'run_publisher("enforce_health_publication_gate_v192.py")'
        self.assertIn('"sitewide_seo_publisher": 216', pipeline)
        self.assertIn(enhancer, pipeline)
        self.assertIn(verifier, pipeline)
        self.assertIn(health_gate, pipeline)
        self.assertLess(pipeline.index(enhancer), pipeline.index(verifier))
        self.assertLess(pipeline.index(verifier), pipeline.index(health_gate))


if __name__ == "__main__":
    unittest.main()
