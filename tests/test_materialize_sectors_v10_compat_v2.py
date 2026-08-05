from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "materialize_sectors_v10_compat_v2.py"
SPEC = importlib.util.spec_from_file_location("materialize_sectors_v10_compat_v2", SCRIPT_PATH)
assert SPEC and SPEC.loader
compat = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compat
SPEC.loader.exec_module(compat)


class MaterializeSectorsV10CompatTests(unittest.TestCase):
    def test_normalizes_structured_reference_records(self) -> None:
        payload = {
            "sources": [
                {
                    "publisher": "World Health Organization",
                    "title": "Official guidance",
                    "url": "https://www.who.int/example",
                },
                {"title": "NICE guidance", "href": "https://www.nice.org.uk/example"},
            ],
            "articles": [],
        }
        compat.normalize_payload(payload)
        self.assertEqual(
            payload["sources"][0]["name"],
            "World Health Organization — Official guidance",
        )
        self.assertEqual(payload["sources"][1]["name"], "NICE guidance")
        self.assertEqual(payload["sources"][1]["url"], "https://www.nice.org.uk/example")

    def test_normalizes_comparison_article_without_fabricating_claims(self) -> None:
        payload = {
            "sources": [],
            "articles": [
                {
                    "title": "مقارنة عملية",
                    "comparison_axes": [
                        {"axis": "السياق", "first": "وصف أول", "second": "وصف ثان"},
                        {"axis": "المدة", "first": "مدة أولى", "second": "مدة ثانية"},
                        {"axis": "الأثر", "first": "أثر أول", "second": "أثر ثان"},
                    ],
                }
            ],
        }
        compat.normalize_payload(payload)
        article = payload["articles"][0]
        self.assertEqual(len(article["signals"]), 3)
        self.assertIn("السياق", article["signals"][0])
        self.assertEqual(len(article["phrases"]), 2)
        self.assertIn("لن نحسم", article["phrases"][0])

    def test_preserves_official_legal_term_but_rejects_prohibited_word(self) -> None:
        self.assertNotIn("ذوي الإعاقة", compat.base.UNWANTED_TERMS)
        self.assertIn("معاقين", compat.base.UNWANTED_TERMS)
        self.assertIn("المعاقين", compat.base.UNWANTED_TERMS)

    def test_renders_governance_schema_questions_and_internal_links(self) -> None:
        payload = {
            "key": "clinical-anxiety",
            "title": "اضطرابات القلق والوسواس: فهم سريري آمن",
            "subtitle": "محتوى عربي أصيل يشرح الفروق ويربط التوعية بالتقييم المهني.",
            "description": "وصف مخصص غني لمحركات البحث وللقارئ.",
            "canonical": "https://healthrenewal.org/evidence-guides/clinical-anxiety/",
            "schema_types": ["MedicalWebPage", "CollectionPage"],
            "review_status": "internally-reviewed",
            "external_review": "recommended-not-completed",
            "safety_level": "sensitive",
            "reviewed_at": "2026-08-06",
            "verified_at": "2026-08-06",
            "next_review_due": "2027-02-06",
            "professional_boundary": "هذه الصفحة للتثقيف ولا تثبت تشخيصًا.",
            "disclaimer": "هذه الصفحة للتثقيف ولا تثبت تشخيصًا.",
            "sources": [
                {
                    "name": "WHO — Anxiety disorders",
                    "url": "https://www.who.int/example",
                    "publisher": "World Health Organization",
                    "type": "official-fact-sheet",
                    "verified_at": "2026-08-06",
                    "use": "التعريف والأثر الوظيفي",
                },
                {
                    "name": "NICE guidance",
                    "url": "https://www.nice.org.uk/example",
                    "publisher": "NICE",
                    "type": "clinical-guideline",
                    "verified_at": "2026-08-06",
                    "use": "التقييم والرعاية",
                },
            ],
            "source_log": {
                "method": "مراجعة مصادر رسمية وصياغة عربية أصلية.",
                "claims_checked": ["الفرق بين النوبة والاضطراب"],
                "limitations": "تحتاج التوصيات إلى تكييف محلي.",
            },
            "articles": [
                {
                    "slug": "panic-versus-disorder",
                    "title": "الفرق بين النوبة والاضطراب",
                    "summary": "ملخص عربي اختباري طويل يوضح الفرق والسياق والحدود المهنية بطريقة عملية واضحة وآمنة.",
                    "signals": ["علامة أولى", "علامة ثانية", "علامة ثالثة"],
                    "steps": ["خطوة أولى", "خطوة ثانية", "خطوة ثالثة", "خطوة رابعة"],
                    "questions": ["ما مدة الأعراض؟", "ما أثرها الوظيفي؟"],
                    "phrases": ["صياغة أولى", "صياغة ثانية"],
                    "avoid": "تجنب التشخيص الذاتي والطمأنة المطلقة.",
                },
                {
                    "slug": "prepare-for-assessment",
                    "title": "التحضير للتقييم",
                    "summary": "ملخص عربي اختباري ثان يشرح الاستعداد للموعد وتسجيل الأعراض والأسئلة دون ادعاء تشخيص.",
                    "signals": ["موقف أول", "موقف ثان", "موقف ثالث"],
                    "steps": ["إجراء أول", "إجراء ثان", "إجراء ثالث", "إجراء رابع"],
                    "questions": ["ما الأدوية المستخدمة؟", "ما عوامل السلامة؟"],
                    "phrases": ["عبارة أولى", "عبارة ثانية"],
                    "avoid": "تجنب إخفاء المعلومات المهمة عن المختص.",
                },
            ],
            "internal_links": [
                "/mental-health/",
                "/daily-tools/medical-visit-preparation/",
                "https://external.example/",
            ],
        }
        compat.validate_source(Path("clinical-anxiety.json"), payload)
        item = compat.base.PublicationItem(
            Path("clinical-anxiety.json"),
            payload,
            compat.base.classify(payload),
            "evidence-guides/clinical-anxiety/",
        )
        document = compat.render_page(item)
        self.assertIn('<html lang="ar" dir="rtl">', document)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/evidence-guides/clinical-anxiety/">',
            document,
        )
        self.assertIn("MedicalWebPage", document)
        self.assertIn("CollectionPage", document)
        self.assertIn("وصف مخصص غني لمحركات البحث", document)
        self.assertIn("حالة المراجعة ومنهجية المصادر", document)
        self.assertIn("مراجعة خارجية موصى بها ولم تكتمل", document)
        self.assertIn("أسئلة عملية قبل التقييم أو المتابعة", document)
        self.assertIn("مسارات مرتبطة داخل المنصة", document)
        self.assertIn('href="/mental-health/"', document)
        self.assertNotIn('href="https://external.example/"', document)
        self.assertIn("هذه الصفحة للتثقيف ولا تثبت تشخيصًا", document)
        self.assertIn("@media print", document)
        self.assertIn("@media(max-width:640px)", document)
        self.assertNotIn("معاقين", document)

    def test_rejects_declared_canonical_that_does_not_match_public_route(self) -> None:
        payload = {
            "key": "canonical-test",
            "title": "دليل اختباري كامل",
            "subtitle": "محتوى عربي اختباري يوضح الغرض والحدود والخطوات العملية بوضوح كاف.",
            "canonical": "https://healthrenewal.org/wrong-route/",
            "sources": [
                {"name": "WHO", "url": "https://www.who.int/example"},
                {"name": "NICE", "url": "https://www.nice.org.uk/example"},
            ],
            "articles": [
                {
                    "slug": "first-topic",
                    "title": "المحور الأول",
                    "summary": "هذا ملخص عربي اختباري طويل بما يكفي لتوضيح الفكرة والسياق والحدود بصورة عملية وآمنة.",
                    "signals": ["أ", "ب", "ج"],
                    "steps": ["أ", "ب", "ج", "د"],
                    "phrases": ["أ", "ب"],
                    "avoid": "تجنب التعميم والتشخيص الذاتي.",
                },
                {
                    "slug": "second-topic",
                    "title": "المحور الثاني",
                    "summary": "هذا ملخص عربي اختباري ثان يشرح التنفيذ والمتابعة والتقييم الحذر دون تقديم قرار فردي.",
                    "signals": ["أ", "ب", "ج"],
                    "steps": ["أ", "ب", "ج", "د"],
                    "phrases": ["أ", "ب"],
                    "avoid": "تجنب الضغط والإكراه والتسرع.",
                },
            ],
        }
        with self.assertRaises(compat.base.PublicationError):
            compat.validate_source(Path("canonical-test.json"), payload)

    def _make_reviewed_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        content_root = root / compat.base.CONTENT_DIR
        content_root.mkdir(parents=True)
        for name in compat.RELEASED_MANUAL_REVIEW_SOURCES:
            (content_root / name).write_text("{}\n", encoding="utf-8")

        ledger_path = root / compat.REVIEW_LEDGER
        ledger_path.parent.mkdir(parents=True)
        ledger = {
            "schemaVersion": 1,
            "reviewedAt": "2026-08-04",
            "reviewType": "internal-editorial-and-source-structure-review",
            "clinicalReviewClaimed": False,
            "releasedSources": [
                {
                    "path": f"content/sectors-v10/{name}",
                    "decision": "publish-educational-content",
                    "reason": "Complete educational source structure.",
                }
                for name in sorted(compat.RELEASED_MANUAL_REVIEW_SOURCES)
            ],
        }
        ledger_path.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return root

    def test_editorial_release_requires_exact_nonclinical_ledger(self) -> None:
        root = self._make_reviewed_repo()
        self.assertEqual(
            compat.validated_editorial_release(root),
            compat.RELEASED_MANUAL_REVIEW_SOURCES,
        )

        ledger_path = root / compat.REVIEW_LEDGER
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger["clinicalReviewClaimed"] = True
        ledger_path.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(compat.base.PublicationError):
            compat.validated_editorial_release(root)

    def test_editorial_release_fails_when_released_source_is_missing(self) -> None:
        root = self._make_reviewed_repo()
        missing_name = sorted(compat.RELEASED_MANUAL_REVIEW_SOURCES)[0]
        (root / compat.base.CONTENT_DIR / missing_name).unlink()
        with self.assertRaises(compat.base.PublicationError):
            compat.validated_editorial_release(root)


if __name__ == "__main__":
    unittest.main()
