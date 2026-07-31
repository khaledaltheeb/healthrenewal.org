from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.finalize_semantic_structure_v237 import ERROR_MARKER, finalize, heading_jumps, parse


class SemanticStructureV237Tests(unittest.TestCase):
    def write_page(self, site: Path, relative: str, body: str, *, title: str = "اختبار") -> Path:
        page = site / relative
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{title}</title></head><body>{body}</body></html>',
            encoding="utf-8",
        )
        return page

    def test_nested_heading_subtree_and_error_page_are_normalized_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            index = self.write_page(
                site,
                "index.html",
                '<main><h1>الرئيسي</h1><h3 class="card">الأول</h3><h3>الثاني</h3>'
                '<h4 id="detail">تفصيل</h4><h2>قسم مستقل</h2>'
                '<script>window.sample = "<h6>نص برمجي</h6>";</script></main>',
            )
            error = self.write_page(
                site,
                "404.html",
                "<main><h1>الصفحة غير موجودة</h1><h3>روابط مقترحة</h3></main>",
                title="الصفحة غير موجودة | مصطلحات علم النفس",
            )

            first = finalize(site)
            self.assertEqual(first["status"], "passed")
            self.assertEqual(first["pages_scanned"], 2)
            self.assertEqual(first["heading_pages_updated"], 2)
            self.assertEqual(first["heading_tags_updated"], 4)
            self.assertEqual(first["remaining_heading_jumps"], 0)
            self.assertTrue(first["error_page_jsonld_added"])
            self.assertTrue(first["error_page_jsonld_present"])
            self.assertEqual(first["error_page_marker_count"], 1)

            index_text = index.read_text(encoding="utf-8")
            error_text = error.read_text(encoding="utf-8")
            self.assertEqual(parse(index_text).heading_levels, [1, 2, 2, 3, 2])
            self.assertEqual(parse(error_text).heading_levels, [1, 2])
            self.assertEqual(heading_jumps(parse(index_text).heading_levels), [])
            self.assertIn('<h2 class="card">الأول</h2>', index_text)
            self.assertIn('<h3 id="detail">تفصيل</h3>', index_text)
            self.assertIn('window.sample = "<h6>نص برمجي</h6>";', index_text)
            self.assertEqual(error_text.count(ERROR_MARKER), 1)

            blocks = parse(error_text).jsonld_blocks
            self.assertEqual(len(blocks), 1)
            schema = json.loads(blocks[0])
            self.assertEqual(schema["@type"], "WebPage")
            self.assertEqual(schema["url"], "https://healthrenewal.org/404.html")
            self.assertEqual(schema["inLanguage"], "ar")

            index_before = index_text
            error_before = error_text
            second = finalize(site)
            self.assertEqual(second["status"], "passed")
            self.assertEqual(second["heading_pages_updated"], 0)
            self.assertEqual(second["heading_tags_updated"], 0)
            self.assertFalse(second["error_page_jsonld_added"])
            self.assertEqual(second["error_page_marker_count"], 1)
            self.assertEqual(index.read_text(encoding="utf-8"), index_before)
            self.assertEqual(error.read_text(encoding="utf-8"), error_before)

    def test_existing_valid_jsonld_is_preserved_without_marker_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            error = site / "404.html"
            error.write_text(
                '<!doctype html><html lang="ar" dir="rtl"><head><title>غير موجود</title>'
                '<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>'
                '</head><body><main><h1>غير موجود</h1><h2>العودة</h2></main></body></html>',
                encoding="utf-8",
            )

            report = finalize(site)
            self.assertEqual(report["status"], "passed")
            self.assertFalse(report["error_page_jsonld_added"])
            self.assertTrue(report["error_page_jsonld_present"])
            self.assertEqual(report["error_page_marker_count"], 0)
            self.assertNotIn(ERROR_MARKER, error.read_text(encoding="utf-8"))

    def test_error_page_without_head_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            (site / "404.html").write_text(
                '<html lang="ar" dir="rtl"><body><h1>غير موجود</h1><h3>عودة</h3></body></html>',
                encoding="utf-8",
            )
            with self.assertRaises(SystemExit):
                finalize(site)


if __name__ == "__main__":
    unittest.main()
