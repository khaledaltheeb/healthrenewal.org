from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import build_conditions_v281_data as builder_v281
from scripts import enforce_sitewide_heading_intent_v2 as semantic
from scripts import publish_capabilities_v280 as publisher_v280
from scripts import publish_conditions_v281 as publisher_v281


class GeneratedArtifactHeadingIntentV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="sitewide-generated-v2-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        for route, heading in (
            ("", "الرئيسية"),
            ("special-needs", "مركز ذوي الاحتياجات الخاصة"),
            ("outside-the-box", "أفكار خارج الصندوق"),
        ):
            directory = self.site / route
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "index.html").write_text(
                '<!doctype html><html lang="ar" dir="rtl"><head>'
                '<meta name="robots" content="index,follow">'
                '<meta name="description" content="صفحة اختبار لحزمة النشر.">'
                f'<title>{heading}</title></head><body><main><h1>{heading}</h1>'
                '<h2>المحتوى</h2></main></body></html>',
                encoding="utf-8",
            )
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<sitemap><loc>https://example.test/sitemap-core.xml</loc></sitemap>'
            '</sitemapindex>',
            encoding="utf-8",
        )
        (self.site / "robots.txt").write_text(
            "User-agent: *\nAllow: /\n",
            encoding="utf-8",
        )

    def test_v280_and_v281_artifacts_meet_the_same_semantic_contract(self) -> None:
        report_v280 = publisher_v280.publish(self.site)
        self.assertEqual(104, report_v280["generated_page_count"])

        statuses_280, changed_280, unsupported_280 = semantic.collect(
            self.site,
            self.site / "sitemap-capabilities.xml",
            ("https://healthrenewal.org/",),
            write=True,
        )
        self.assertEqual([], unsupported_280)
        self.assertTrue(changed_280)
        self.assertFalse(any(item.error for item in statuses_280))
        final_280, remaining_280, _ = semantic.collect(
            self.site,
            self.site / "sitemap-capabilities.xml",
            ("https://healthrenewal.org/",),
            write=False,
        )
        self.assertEqual([], remaining_280)
        self.assertEqual(104, len(final_280))
        self.assertTrue(all(item.h1 == 1 for item in final_280))
        self.assertTrue(all(item.h2 >= 1 and item.h3 >= 1 for item in final_280))
        self.assertTrue(all(item.questions >= item.minimum_questions for item in final_280))

        payload = self.site / "conditions-50-ar.json.zlib.b64"
        builder_v281.build(payload)
        original_data = publisher_v281.DATA
        try:
            publisher_v281.DATA = payload
            report_v281 = publisher_v281.publish(self.site)
        finally:
            publisher_v281.DATA = original_data
        self.assertEqual(51, report_v281["generated_page_count"])

        statuses_281, changed_281, unsupported_281 = semantic.collect(
            self.site,
            self.site / "sitemap-capabilities-v281.xml",
            ("https://healthrenewal.org/",),
            write=True,
        )
        self.assertEqual([], unsupported_281)
        self.assertTrue(changed_281)
        self.assertFalse(any(item.error for item in statuses_281))
        final_281, remaining_281, _ = semantic.collect(
            self.site,
            self.site / "sitemap-capabilities-v281.xml",
            ("https://healthrenewal.org/",),
            write=False,
        )
        self.assertEqual([], remaining_281)
        self.assertEqual(51, len(final_281))
        self.assertEqual(50, sum(item.kind == "capability_condition" for item in final_281))
        self.assertTrue(all(item.h1 == 1 for item in final_281))
        self.assertTrue(all(item.h2 >= 1 and item.h3 >= 1 for item in final_281))
        self.assertTrue(all(item.questions >= item.minimum_questions for item in final_281))

        all_capability_pages = list((self.site / "capabilities").rglob("index.html"))
        self.assertEqual(155, len(all_capability_pages))
        for path in all_capability_pages:
            source = path.read_text(encoding="utf-8")
            self.assertEqual(1, source.count("<h1"), path)
            self.assertIn("<h2", source, path)
            self.assertIn("<h3", source, path)
            self.assertNotIn("معاقين", source, path)


if __name__ == "__main__":
    unittest.main()
