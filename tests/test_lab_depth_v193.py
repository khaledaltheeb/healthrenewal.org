import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "content" / "v193" / "lab-depth-contract-ar.json"
SCRIPT = ROOT / "scripts" / "enrich_lab_content_v193.py"

spec = importlib.util.spec_from_file_location("lab_depth_v193", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    @property
    def word_count(self):
        return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(self.parts)))


def fixture_page(definition: dict, kind: str) -> str:
    payload = json.dumps(definition, ensure_ascii=False).replace("</", "<\\/")
    title = definition["title"]
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title><meta name="description" content="قصير"><meta name="twitter:card" content="summary"><link rel="canonical" href="https://healthrenewal.org/{kind}-lab/sample/"><link rel="manifest" href="/manifest.webmanifest"><script type="application/json" id="lab-definition">{payload}</script></head><body><main><section><h1>{title}</h1><p>مقدمة.</p><div data-v12-lab="{kind}"></div></section><footer>النهاية</footer></main></body></html>'''


class LabDepthV193Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def make_site(self, root: Path):
        assessment = root / "assessment-lab" / "sample" / "index.html"
        cognitive = root / "cognitive-lab" / "sample" / "index.html"
        assessment.parent.mkdir(parents=True)
        cognitive.parent.mkdir(parents=True)
        assessment.write_text(
            fixture_page(
                {
                    "slug": "sample",
                    "title": "متابعة نموذجية",
                    "category": "المتابعة اليومية",
                    "summary": "متابعة أربعة محاور يومية.",
                    "period": "الأسبوع الماضي",
                    "score_type": "monitor",
                    "questions": [
                        "النوم: كان هذا الجانب صعبًا أو أثر في يومي",
                        "الطاقة: كان هذا الجانب صعبًا أو أثر في يومي",
                        "التركيز: احتجت إلى دعم إضافي في هذا الجانب",
                        "الوظيفة اليومية: أريد متابعة تغير هذا الجانب",
                    ],
                },
                "assessment",
            ),
            encoding="utf-8",
        )
        cognitive.write_text(
            fixture_page(
                {
                    "slug": "sample",
                    "title": "الانتباه النموذجي",
                    "category": "الانتباه",
                    "summary": "مهمة تدريبية في الانتباه.",
                    "mode": "الانتباه",
                    "stages": 5,
                    "trials_per_stage": 6,
                },
                "cognitive",
            ),
            encoding="utf-8",
        )
        return assessment, cognitive

    def test_contract_sources_and_safety_boundaries(self):
        self.assertEqual(self.contract["status"], "internally-reviewed")
        self.assertEqual(self.contract["risk_level"], "moderate")
        self.assertEqual(self.contract["scope"]["assessment_pages"], 40)
        self.assertEqual(self.contract["scope"]["cognitive_pages"], 48)
        sources = self.contract["sources"]
        self.assertGreaterEqual(len(sources), 6)
        self.assertEqual(len({item["id"] for item in sources}), len(sources))
        self.assertEqual(len({item["url"] for item in sources}), len(sources))
        for source in sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIsInstance(source["year"], int)
            self.assertRegex(source["verified_at"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(source["claims_supported"])
            self.assertIn(source["source_type"], {"primary_research", "official_guideline", "public_health_authority", "institutional_fact_sheet"})
        text = CONTRACT.read_text(encoding="utf-8")
        for marker in ["لا تثبت تشخيصًا", "ليست اختبار ذكاء", "لا يبرر ادعاء الوقاية من الخرف", "خدمات الطوارئ المحلية"]:
            self.assertIn(marker, text)
        for forbidden in ["معتمد سريريًا لكل الفئات", "يشخص الاكتئاب نهائيًا", "يرفع الذكاء", "يمنع الخرف", "مراجعة طبيب مكتملة"]:
            self.assertNotIn(forbidden, text)

    def test_enrichment_depth_metadata_schema_links_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            assessment, cognitive = self.make_site(site)
            report = module.enrich(site)
            self.assertEqual(report["status"], "built-not-published")
            self.assertEqual(report["total_pages_enriched"], 2)
            first = {path: path.read_text(encoding="utf-8") for path in (assessment, cognitive)}
            for path, page in first.items():
                self.assertEqual(page.count(module.HEAD_START), 1)
                self.assertEqual(page.count(module.BODY_START), 1)
                self.assertEqual(page.count("<h1>"), 1)
                self.assertIn('name="twitter:title"', page)
                self.assertIn('name="twitter:description"', page)
                self.assertIn('"@type": "FAQPage"', page)
                self.assertIn('/privacy/', page)
                self.assertNotIn('content="قصير"', page)
                parser = VisibleText()
                parser.feed(page)
                self.assertGreaterEqual(parser.word_count, self.contract["scope"]["minimum_visible_words"], path)
            self.assertIn("لا تستخدم عينة معيارية", first[assessment])
            self.assertIn("ليست اختبار ذكاء", first[cognitive])
            module.enrich(site)
            second = {path: path.read_text(encoding="utf-8") for path in (assessment, cognitive)}
            self.assertEqual(first, second)
            api = json.loads((site / "api" / "lab-depth-v193.json").read_text(encoding="utf-8"))
            self.assertEqual(api["status"], "built-not-published")
            self.assertNotEqual(api["status"], "published")

    def test_self_harm_item_adds_visible_emergency_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            page = site / "assessment-lab" / "phq" / "index.html"
            page.parent.mkdir(parents=True)
            page.write_text(
                fixture_page(
                    {
                        "slug": "phq",
                        "title": "فحص نموذج أمان",
                        "category": "مقياس موثق",
                        "summary": "عرض بنود الأعراض.",
                        "period": "الأسبوعان الماضيان",
                        "score_type": "phq9",
                        "questions": ["أفكار بأن الموت أفضل أو أفكار في إيذاء النفس"],
                    },
                    "assessment",
                ),
                encoding="utf-8",
            )
            module.enrich(site)
            text = page.read_text(encoding="utf-8")
            self.assertIn("تنبيه أمان مهم", text)
            self.assertIn("خدمات الطوارئ المحلية", text)
            self.assertIn("The PHQ-9", text)
            self.assertIn("Depression and Suicide Risk", text)


if __name__ == "__main__":
    unittest.main()
