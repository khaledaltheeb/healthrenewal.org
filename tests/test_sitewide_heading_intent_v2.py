from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import enforce_sitewide_heading_intent_v2 as mod


class SitewideHeadingIntentV2Tests(unittest.TestCase):
    def make_site(self, page_html: str) -> tempfile.TemporaryDirectory[str]:
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        (root / "section").mkdir()
        (root / "section" / "index.html").write_text(page_html, encoding="utf-8")
        (root / "sitemap.xml").write_text(
            '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://healthrenewal.org/section/</loc></url>
</urlset>''',
            encoding="utf-8",
        )
        return directory

    def test_adds_h3_and_search_intent_questions(self) -> None:
        page = '''<!doctype html><html lang="ar" dir="rtl"><head>
<meta name="robots" content="index,follow"><meta name="description" content="وصف عربي يشرح القسم ومحتواه بوضوح.">
<title>قسم تجريبي</title></head><body><main><h1>القسم التجريبي</h1><h2>المحتوى</h2><p>محتوى واضح.</p></main></body></html>'''
        directory = self.make_site(page)
        old_root = mod.ROOT
        try:
            mod.ROOT = Path(directory.name)
            statuses, changes = mod.collect(write=True)
            self.assertEqual(1, len(changes))
            self.assertFalse(statuses[0].error)
            self.assertGreaterEqual(statuses[0].h3, 1)
            self.assertGreaterEqual(statuses[0].questions, 2)
            updated = (mod.ROOT / "section" / "index.html").read_text(encoding="utf-8")
            self.assertIn(mod.MARKER, updated)
            self.assertIn("<h3>", updated)
        finally:
            mod.ROOT = old_root
            directory.cleanup()

    def test_generation_is_idempotent(self) -> None:
        page = '''<!doctype html><html lang="ar" dir="rtl"><head>
<meta name="robots" content="index,follow"><meta name="description" content="وصف عربي يشرح القسم ومحتواه بوضوح.">
<title>قسم تجريبي</title></head><body><main><h1>القسم التجريبي</h1><h2>المحتوى</h2><p>محتوى واضح.</p></main></body></html>'''
        directory = self.make_site(page)
        old_root = mod.ROOT
        try:
            mod.ROOT = Path(directory.name)
            mod.collect(write=True)
            first = (mod.ROOT / "section" / "index.html").read_text(encoding="utf-8")
            statuses, changes = mod.collect(write=True)
            second = (mod.ROOT / "section" / "index.html").read_text(encoding="utf-8")
            self.assertEqual([], changes)
            self.assertEqual(first, second)
            self.assertFalse(statuses[0].error)
        finally:
            mod.ROOT = old_root
            directory.cleanup()

    def test_preserves_compliant_page(self) -> None:
        page = '''<!doctype html><html lang="ar" dir="rtl"><head>
<meta name="robots" content="index,follow"><meta name="description" content="وصف عربي يشرح القسم ومحتواه بوضوح.">
<title>قسم تجريبي</title></head><body><main><h1>القسم التجريبي</h1><h2>أسئلة</h2>
<h3>ماذا يقدم هذا القسم؟</h3><p>شرح.</p><h3>كيف أبدأ؟</h3><p>ابدأ هنا.</p></main></body></html>'''
        directory = self.make_site(page)
        old_root = mod.ROOT
        try:
            mod.ROOT = Path(directory.name)
            statuses, changes = mod.collect(write=False)
            self.assertEqual([], changes)
            self.assertFalse(statuses[0].error)
        finally:
            mod.ROOT = old_root
            directory.cleanup()

    def test_noindex_page_is_not_modified(self) -> None:
        page = '''<!doctype html><html lang="ar" dir="rtl"><head>
<meta name="robots" content="noindex,nofollow"><title>خاص</title></head>
<body><main><h1>خاص</h1></main></body></html>'''
        directory = self.make_site(page)
        old_root = mod.ROOT
        try:
            mod.ROOT = Path(directory.name)
            statuses, changes = mod.collect(write=True)
            self.assertEqual([], changes)
            self.assertFalse(statuses[0].indexable)
            self.assertFalse(statuses[0].error)
        finally:
            mod.ROOT = old_root
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
