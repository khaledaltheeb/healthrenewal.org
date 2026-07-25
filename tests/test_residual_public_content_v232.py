from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/enrich_residual_public_pages_v232.py'
spec = importlib.util.spec_from_file_location('residual_v232', SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def page(title: str, robots: str = 'index,follow', body: str = 'محتوى قصير') -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{title}</title><meta name="description" content="وصف قصير"><meta name="robots" content="{robots}"></head><body><main><h1>{title}</h1><p>{body}</p></main></body></html>'''


class ResidualPublicContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        paths = {
            'about/index.html': 'عن المنصة',
            'methodology/index.html': 'المنهجية',
            'privacy/index.html': 'الخصوصية',
            'downloads/index.html': 'التنزيلات',
            'tools/daily-term/index.html': 'مصطلح اليوم',
            'tools/favorites/index.html': 'المفضلة',
            'tools/quiz/index.html': 'اختبار المصطلحات',
            'letters/alef/index.html': 'فهرس حرف الألف',
            'letters/index.html': 'فهرس الحروف العربية',
            'english-index/a/index.html': 'English index A',
            'english-index/index.html': 'الفهرس الإنجليزي',
            '404.html': 'الصفحة غير موجودة',
        }
        for rel, title in paths.items():
            target = self.site / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(title), encoding='utf-8')
        private = self.site / 'letters/private/index.html'
        private.parent.mkdir(parents=True)
        private.write_text(page('صفحة خاصة', robots='noindex'), encoding='utf-8')

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_enriches_all_index_and_utility_targets(self) -> None:
        report = module.run(self.site)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['target_pages'], 13)
        self.assertEqual(report['enriched_pages'], 12)
        self.assertEqual(report['skipped_noindex_pages'], 1)
        self.assertEqual(report['remaining_below_minimum'], 0)
        self.assertEqual(report['duplicate_generated_blocks'], 0)
        for row in report['pages']:
            text = (self.site / row['path']).read_text(encoding='utf-8')
            if row['status'] == 'skipped_noindex':
                self.assertNotIn(module.START, text)
                continue
            self.assertIn(module.START, text)
            self.assertGreaterEqual(module.visible_words(text), row['minimum_words'])

    def test_is_idempotent(self) -> None:
        module.run(self.site)
        path = self.site / 'methodology/index.html'
        first = path.read_text(encoding='utf-8')
        second = module.run(self.site)
        self.assertEqual(first, path.read_text(encoding='utf-8'))
        self.assertEqual(second['already_enriched_pages'], 12)

    def test_methodology_privacy_and_tools_have_specific_content(self) -> None:
        module.run(self.site)
        method = (self.site / 'methodology/index.html').read_text(encoding='utf-8')
        privacy = (self.site / 'privacy/index.html').read_text(encoding='utf-8')
        quiz = (self.site / 'tools/quiz/index.html').read_text(encoding='utf-8')
        self.assertIn('المراجعات المنهجية', method)
        self.assertIn('الصدق والثبات', method)
        self.assertIn('التخزين المحلي', privacy)
        self.assertIn('الجهاز المشترك', privacy)
        self.assertIn('لا يقيس الذكاء', quiz)
        self.assertNotIn('شفاء مضمون', method + privacy + quiz)


if __name__ == '__main__':
    unittest.main()
