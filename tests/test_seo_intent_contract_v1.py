from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import audit_seo_intent_v1 as audit
from scripts import enhance_search_intent_v1 as enhance


class SeoIntentContractTests(unittest.TestCase):
    def test_priority_list_has_exactly_100_unique_canonical_urls(self) -> None:
        urls = audit.read_priority_urls()
        self.assertEqual(100, len(urls))
        self.assertEqual(100, len(set(urls)))
        self.assertTrue(all(url.startswith(audit.ORIGIN + "/") for url in urls))

    def test_family_faq_is_visible_and_schema_matches(self) -> None:
        condition = {
            "slug": "example",
            "title": "حالة تجريبية",
            "en": "Example condition",
            "classification": "حالة نمائية",
            "summary": "ملخص الحالة المنشور نفسه.",
            "signs": {"التواصل": ["علامة أولى"], "الحركة": ["علامة ثانية"]},
            "first_steps": ["خطوة أولى", "خطوة ثانية", "خطوة ثالثة"],
            "avoid": ["تجنب أول", "تجنب ثان", "تجنب ثالث"],
            "urgent": ["خطر مباشر"],
            "questions": ["كيف سنقيس التقدم؟"],
            "sources": [["مصدر", "https://example.org"]],
        }
        items = enhance.faq_for_family(condition)
        rendered = enhance.family_faq_html(condition)
        graph = enhance.family_graph(condition, "https://healthrenewal.org/family-guide/conditions/example/", "2026-08-01")
        self.assertGreaterEqual(len(items), 5)
        self.assertEqual(len(items), rendered.count('<article class="faq-item">'))
        faq = next(node for node in graph["@graph"] if node["@type"] == "FAQPage")
        self.assertEqual([q for q, _ in items], [item["name"] for item in faq["mainEntity"]])
        self.assertNotIn("<details>", rendered)

    def test_magazine_faq_uses_existing_article_content(self) -> None:
        source = """<!doctype html><html><body><main><article>
        <p class='lead'>سؤال الدراسة المنشور.</p><h1>عنوان الدراسة</h1>
        <section><h2>الخلاصة التنفيذية</h2><p>النتيجة المنشورة.</p></section>
        <section><h2>حدود الدليل</h2><ul><li>قيد منشور.</li></ul></section>
        <section><h2>الدلالة العملية</h2><p>تفسير عملي منشور.</p></section>
        </article></main></body></html>"""
        items = enhance.magazine_faq(source, "عنوان الدراسة")
        answers = " ".join(answer for _, answer in items)
        self.assertIn("سؤال الدراسة المنشور", answers)
        self.assertIn("النتيجة المنشورة", answers)
        self.assertIn("قيد منشور", answers)
        self.assertIn("تفسير عملي منشور", answers)

    def test_heading_jump_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = root / "index.html"
            page.write_text(
                """<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>
                <meta name='viewport' content='width=device-width'><title>عنوان عربي واضح ومتكامل</title>
                <meta name='description' content='وصف عربي واضح وموسع بدرجة كافية لشرح محتوى الصفحة للمستخدم قبل فتحها والانتقال إليها.'>
                <meta name='robots' content='index,follow'><link rel='canonical' href='https://healthrenewal.org/'>
                <script type='application/ld+json'>{"@context":"https://schema.org","@type":"WebPage"}</script></head>
                <body><a href='/a/'>أ</a><a href='/b/'>ب</a><a href='/c/'>ج</a><main><h1>الرئيسية</h1><h3>عنوان متجاوز</h3><p>""" + ("كلمة " * 150) + "</p></main></body></html>",
                encoding="utf-8",
            )
            old_root = audit.ROOT
            try:
                audit.ROOT = root
                result = audit.audit_html("https://healthrenewal.org/", page)
            finally:
                audit.ROOT = old_root
            self.assertIn("heading_jump", {finding.code for finding in result.findings if finding.severity == "error"})

    def test_report_is_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            summary = audit.write_report([], output, "priority")
            self.assertEqual(0, summary["pages"])
            self.assertEqual("sitewide-semantic-seo-search-intent-v1", json.loads(output.read_text(encoding="utf-8"))["summary"]["contract"])


if __name__ == "__main__":
    unittest.main()
