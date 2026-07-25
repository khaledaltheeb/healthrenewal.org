from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.publish_institutional_header_v233 import (
    LANGUAGE_LINKS,
    SECTION_LINKS,
    publish,
    validate,
)


LEGACY_PAGE = """<!doctype html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><title>اختبار</title></head>
<body>
<a class="skip" href="#main">تجاوز إلى المحتوى</a>
<header aria-label="الترويسة الرئيسية"><div class="wrap header-inner"><a class="brand" href="./">المنصة</a><nav class="nav" aria-label="التنقل الرئيسي"><a href="encyclopedia/">الموسوعة</a></nav></div></header>
<main id="main"><h1>صفحة اختبار</h1></main>
</body>
</html>
"""


class InstitutionalHeaderV233Tests(unittest.TestCase):
    def test_publisher_replaces_legacy_header_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            index = site / "index.html"
            index.write_text(LEGACY_PAGE, encoding="utf-8")

            first = publish(site)
            first_text = index.read_text(encoding="utf-8")
            second = publish(site)
            second_text = index.read_text(encoding="utf-8")

            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertEqual(first_text, second_text)
            self.assertEqual(first_text.count("data-institutional-header-v233"), 1)
            self.assertEqual(first_text.count('id="institutional-header-v233-styles"'), 1)
            self.assertEqual(first_text.count("<details"), 2)
            self.assertEqual(first_text.count("<summary"), 2)
            self.assertNotIn('<nav class="nav"', first_text)

            report = json.loads(
                (site / "api" / "institutional-header-v233.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["section_links"], len(SECTION_LINKS))
            self.assertEqual(report["language_links"], len(LANGUAGE_LINKS))
            self.assertEqual(report["dropdowns"], 2)

    def test_all_requested_sections_and_languages_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            index = site / "index.html"
            index.write_text(LEGACY_PAGE, encoding="utf-8")
            publish(site)
            text = index.read_text(encoding="utf-8")
            report = validate(text)

            self.assertEqual(len(SECTION_LINKS), 12)
            self.assertEqual(
                {label for label, *_ in LANGUAGE_LINKS},
                {"العربية", "English", "Español"},
            )
            self.assertEqual(report["status"], "passed")
            self.assertIn('@media(max-width:900px)', text)
            self.assertIn('@media(max-width:520px)', text)
            self.assertIn('@media(prefers-reduced-motion:reduce)', text)
            self.assertIn('aria-current="page"', text)


if __name__ == "__main__":
    unittest.main()
