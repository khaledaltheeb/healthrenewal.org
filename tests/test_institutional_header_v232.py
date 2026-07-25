from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.publish_institutional_header_v232 import publish


LEGACY = '''<!doctype html><html lang="ar" dir="rtl"><head><style>.wrap{width:min(1220px,92%);margin:auto}</style></head><body><header aria-label="الترويسة الرئيسية"><div class="wrap header-inner"><a class="brand" href="./">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav class="nav" aria-label="التنقل الرئيسي"><a href="start-here/">ابدأ من هنا</a></nav></div></header><main id="main"><h1>الرئيسية</h1></main></body></html>'''


class InstitutionalHeaderTests(unittest.TestCase):
    def test_publish_is_complete_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "index.html").write_text(LEGACY, encoding="utf-8")
            first = publish(site)
            second = publish(site)
            text = (site / "index.html").read_text(encoding="utf-8")
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertEqual(text.count("data-institutional-header-v232"), 1)
            self.assertEqual(text.count('id="institutional-header-v232-styles"'), 1)
            self.assertEqual(text.count("<details"), 2)
            self.assertEqual(text.count('class="sections-list"'), 1)
            self.assertEqual(text.count('class="language-list"'), 1)
            for label in (
                "ابدأ من هنا", "الموسوعة", "المقارنات", "المكتبة",
                "أدلة التعامل", "ذوو الاحتياجات الخاصة", "الطفل",
                "الأسرة", "العائلة", "منصة التقييم", "API",
                "الثقة والمنهجية", "العربية", "English", "Español",
            ):
                self.assertIn(label, text)
            report = json.loads((site / "api/institutional-header-v232.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["section_links"], 12)
            self.assertEqual(report["language_links"], 3)

    def test_missing_header_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            (site / "index.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")
            with self.assertRaises(SystemExit):
                publish(site)


if __name__ == "__main__":
    unittest.main()
