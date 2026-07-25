from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import publish_institutional_pages_v232 as publisher

BASE_PAGE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{title}</title></head><body><main><h1>{title}</h1><p>مقدمة موجزة للصفحة المؤسسية الحالية.</p></main></body></html>'''


class InstitutionalPagesV232Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.site = Path(self.temp.name) / "site"
        self.site.mkdir()
        for slug, data in publisher.PAGES.items():
            target = self.site / slug / "index.html"
            target.parent.mkdir(parents=True)
            target.write_text(BASE_PAGE.format(title=data["title"]), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_publishes_eight_complete_pages(self) -> None:
        report = publisher.publish(self.site)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["page_count"], 8)
        self.assertGreaterEqual(report["minimum_after_words"], 190)
        self.assertGreaterEqual(report["minimum_added_words"], 220)
        self.assertTrue(report["light_marshmallow_design"])
        self.assertFalse(report["text_shadow_used"])
        for item in report["pages"]:
            text = (self.site / item["route"].strip("/") / "index.html").read_text(encoding="utf-8")
            self.assertEqual(text.count(publisher.START), 1)
            self.assertEqual(text.count(publisher.END), 1)
            self.assertEqual(text.count(publisher.STYLE_MARKER), 1)
            self.assertNotIn("text-shadow", text)
            self.assertIsNone(publisher.BANNED.search(text))

    def test_is_idempotent(self) -> None:
        publisher.publish(self.site)
        before = {slug: hashlib.sha256((self.site / slug / "index.html").read_bytes()).hexdigest() for slug in publisher.PAGES}
        publisher.publish(self.site)
        after = {slug: hashlib.sha256((self.site / slug / "index.html").read_bytes()).hexdigest() for slug in publisher.PAGES}
        self.assertEqual(before, after)

    def test_each_page_has_distinct_contract_and_links(self) -> None:
        publisher.publish(self.site)
        required = {"about": "ما الذي تقدمه المنصة؟", "methodology": "هرم المصادر", "privacy": "الأدوات والتخزين المحلي", "downloads": "فحوص قبل الاستيراد", "media-kit": "استخدام الشعار والمواد", "stats": "وحدة العد", "citation": "الاستشهاد ببيانات أو API", "sources": "مطابقة المصدر للادعاء"}
        for slug, phrase in required.items():
            text = (self.site / slug / "index.html").read_text(encoding="utf-8")
            self.assertIn(phrase, text)
            self.assertGreaterEqual(text.count(f'href="{publisher.BASE_PATH}'), 3)
            self.assertIn('aria-label="روابط مرتبطة بهذه الصفحة"', text)

    def test_report_is_written_and_has_no_duplicates(self) -> None:
        publisher.publish(self.site)
        path = self.site / "api" / "institutional-pages-v232.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(report["version"], 232)
        self.assertEqual(len(report["routes"]), len(set(report["routes"])))
        self.assertEqual(report["routes"], [f"/{slug}/" for slug in publisher.PAGES])

    def test_rejects_missing_page_and_unbalanced_marker(self) -> None:
        (self.site / "about" / "index.html").unlink()
        with self.assertRaises(SystemExit):
            publisher.publish(self.site)
        target = self.site / "about" / "index.html"
        target.write_text(BASE_PAGE.format(title="عن المنصة").replace("</main>", publisher.START + "</main>"), encoding="utf-8")
        with self.assertRaises(SystemExit):
            publisher.publish(self.site)


if __name__ == "__main__":
    unittest.main()
