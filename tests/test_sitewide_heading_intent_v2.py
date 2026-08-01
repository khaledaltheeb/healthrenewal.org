from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import enforce_sitewide_heading_intent_v2 as mod


class SitewideHeadingIntentV2Tests(unittest.TestCase):
    def make_site(
        self,
        page_html: str,
        *,
        base_url: str = "https://healthrenewal.org/",
        route: str = "section/",
        sitemap_name: str = "sitemap.xml",
    ) -> tempfile.TemporaryDirectory[str]:
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        destination = root / route / "index.html"
        destination.parent.mkdir(parents=True)
        destination.write_text(page_html, encoding="utf-8")
        (root / sitemap_name).write_text(
            f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{base_url}{route}</loc></url>
</urlset>''',
            encoding="utf-8",
        )
        return directory

    @staticmethod
    def basic_page(robots: str = "index,follow") -> str:
        return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<meta name="robots" content="{robots}"><meta name="description" content="وصف عربي يشرح القسم ومحتواه بوضوح.">
<title>قسم تجريبي</title></head><body><main><h1>القسم التجريبي</h1><h2>المحتوى</h2><p>محتوى واضح.</p></main></body></html>'''

    def test_adds_h3_and_search_intent_questions(self) -> None:
        directory = self.make_site(self.basic_page())
        root = Path(directory.name)
        try:
            statuses, changes, unsupported = mod.collect(
                root,
                root / "sitemap.xml",
                ("https://healthrenewal.org/",),
                write=True,
            )
            self.assertEqual([], unsupported)
            self.assertEqual(1, len(changes))
            self.assertFalse(statuses[0].error)
            updated_statuses, remaining, _ = mod.collect(
                root,
                root / "sitemap.xml",
                ("https://healthrenewal.org/",),
                write=False,
            )
            self.assertEqual([], remaining)
            self.assertGreaterEqual(updated_statuses[0].h3, 1)
            self.assertGreaterEqual(updated_statuses[0].questions, 2)
            updated = (root / "section" / "index.html").read_text(encoding="utf-8")
            self.assertIn(mod.MARKER, updated)
            self.assertIn("<h3>", updated)
        finally:
            directory.cleanup()

    def test_generation_is_idempotent_and_whitespace_clean(self) -> None:
        directory = self.make_site(self.basic_page())
        root = Path(directory.name)
        try:
            mod.collect(root, root / "sitemap.xml", ("https://healthrenewal.org/",), write=True)
            page = root / "section" / "index.html"
            first = page.read_text(encoding="utf-8")
            statuses, changes, _ = mod.collect(
                root,
                root / "sitemap.xml",
                ("https://healthrenewal.org/",),
                write=True,
            )
            second = page.read_text(encoding="utf-8")
            self.assertEqual([], changes)
            self.assertEqual(first, second)
            self.assertFalse(statuses[0].error)
            self.assertFalse(any(line.endswith((" ", "\t")) for line in second.splitlines()))
        finally:
            directory.cleanup()

    def test_preserves_compliant_page(self) -> None:
        page = '''<!doctype html><html lang="ar" dir="rtl"><head>
<meta name="robots" content="index,follow"><meta name="description" content="وصف عربي يشرح القسم ومحتواه بوضوح.">
<title>قسم تجريبي</title></head><body><main><h1>القسم التجريبي</h1><h2>أسئلة</h2>
<h3>ماذا يقدم هذا القسم؟</h3><p>شرح.</p><h3>كيف أبدأ؟</h3><p>ابدأ هنا.</p></main></body></html>'''
        directory = self.make_site(page)
        root = Path(directory.name)
        try:
            statuses, changes, unsupported = mod.collect(
                root,
                root / "sitemap.xml",
                ("https://healthrenewal.org/",),
                write=False,
            )
            self.assertEqual([], changes)
            self.assertEqual([], unsupported)
            self.assertFalse(statuses[0].error)
        finally:
            directory.cleanup()

    def test_noindex_page_is_not_modified(self) -> None:
        directory = self.make_site(self.basic_page("noindex,nofollow"))
        root = Path(directory.name)
        try:
            statuses, changes, _ = mod.collect(
                root,
                root / "sitemap.xml",
                ("https://healthrenewal.org/",),
                write=True,
            )
            self.assertEqual([], changes)
            self.assertFalse(statuses[0].indexable)
            self.assertFalse(statuses[0].error)
        finally:
            directory.cleanup()

    def test_custom_deployment_base_path_and_capability_question_floor(self) -> None:
        base = "https://khaledaltheeb.github.io/pterminology-site/"
        directory = self.make_site(
            self.basic_page(),
            base_url=base,
            route="capabilities/example-condition/",
            sitemap_name="sitemap-capabilities.xml",
        )
        root = Path(directory.name)
        try:
            statuses, changes, unsupported = mod.collect(
                root,
                root / "sitemap-capabilities.xml",
                (base,),
                write=True,
            )
            self.assertEqual([], unsupported)
            self.assertEqual(1, len(changes))
            final, remaining, _ = mod.collect(
                root,
                root / "sitemap-capabilities.xml",
                (base,),
                write=False,
            )
            self.assertEqual([], remaining)
            self.assertEqual("capability_condition", final[0].kind)
            self.assertEqual(5, final[0].minimum_questions)
            self.assertGreaterEqual(final[0].questions, 5)
            self.assertGreaterEqual(final[0].h3, 5)
        finally:
            directory.cleanup()

    def test_report_records_stable_state_and_applied_count(self) -> None:
        directory = self.make_site(self.basic_page())
        root = Path(directory.name)
        report = root / "report.json"
        try:
            statuses, changes, unsupported = mod.collect(
                root,
                root / "sitemap.xml",
                ("https://healthrenewal.org/",),
                write=True,
            )
            self.assertFalse(any(item.error for item in statuses))
            stable, remaining, unsupported = mod.collect(
                root,
                root / "sitemap.xml",
                ("https://healthrenewal.org/",),
                write=False,
            )
            self.assertEqual([], remaining)
            payload = mod.write_report(
                report,
                stable,
                applied=len(changes),
                unsupported=unsupported,
                root=root,
                sitemap=root / "sitemap.xml",
                base_urls=("https://healthrenewal.org/",),
            )
            self.assertEqual(1, payload["applied"])
            self.assertEqual(0, payload["changed"])
            self.assertEqual(0, payload["failed"])
            loaded = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(loaded["all_indexable_have_h3"])
            self.assertTrue(loaded["all_indexable_meet_question_floor"])
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
