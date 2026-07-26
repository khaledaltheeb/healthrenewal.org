from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/deepen_assessment_cognitive_hubs_v233.py'
spec = importlib.util.spec_from_file_location('advanced_v233', SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def page(title: str, body_words: int = 210, robots: str = 'index,follow') -> str:
    body = ' '.join(['محتوى'] * body_words)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{title}</title><meta name="description" content="وصف قصير"><meta name="robots" content="{robots}"></head><body><main><h1>{title}</h1><p>{body}</p><div id="interactive-root"></div></main><script src="runtime.js" defer></script></body></html>'''


class AdvancedContentDepthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        pages = {
            'assessment-lab/worry-cycle/index.html': 'متابعة دائرة القلق',
            'assessment-lab/autism-family-load/index.html': 'دعم الأسرة مع التوحد',
            'cognitive-lab/digit-span-backward/index.html': 'مدى الأرقام العكسي',
            'cognitive-lab/mental-rotation/index.html': 'التدوير الذهني',
            'hubs/path-001/index.html': 'القلق: التعريف والمفهوم',
            'hubs/path-002/index.html': 'القلق: التقييم النفسي',
            'library/index.html': 'المكتبة الأكاديمية',
            'library/research/index.html': 'دليل قراءة الأبحاث',
        }
        for rel, title in pages.items():
            target = self.site / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page(title), encoding='utf-8')

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_deepens_all_four_content_types(self) -> None:
        report = module.run(self.site)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['target_pages'], 8)
        self.assertEqual(report['counts_by_kind'], {'assessment': 2, 'cognitive': 2, 'hub': 2, 'library': 2})
        self.assertEqual(report['remaining_below_minimum'], 0)
        self.assertEqual(report['duplicate_generated_blocks'], 0)
        for row in report['pages']:
            text = (self.site / row['path']).read_text(encoding='utf-8')
            self.assertGreaterEqual(module.visible_words(text), row['minimum_words'])
            self.assertIn(module.START, text)
            self.assertIn('id="interactive-root"', text)
            self.assertIn('runtime.js', text)

    def test_content_is_specialized_by_type(self) -> None:
        module.run(self.site)
        assessment = (self.site / 'assessment-lab/worry-cycle/index.html').read_text(encoding='utf-8')
        cognitive = (self.site / 'cognitive-lab/digit-span-backward/index.html').read_text(encoding='utf-8')
        hub = (self.site / 'hubs/path-001/index.html').read_text(encoding='utf-8')
        library = (self.site / 'library/index.html').read_text(encoding='utf-8')
        self.assertIn('نقطة القطع', assessment)
        self.assertIn('أثر التدريب', cognitive)
        self.assertIn('افصل بين الملاحظة والتفسير', hub)
        self.assertIn('الدلالة ليست الأهمية', library)
        self.assertIn('testingstandards.net', assessment + cognitive)
        self.assertIn('cochrane.org', hub + library)

    def test_is_idempotent_and_rich_pages_stay_unchanged(self) -> None:
        rich = self.site / 'assessment-lab/rich/index.html'
        rich.parent.mkdir(parents=True, exist_ok=True)
        rich.write_text(page('صفحة غنية', body_words=900), encoding='utf-8')
        before_rich = rich.read_text(encoding='utf-8')
        expected_rich, _ = module.publish_contract(
            before_rich,
            'assessment-lab/rich/index.html',
        )
        module.run(self.site)
        path = self.site / 'cognitive-lab/mental-rotation/index.html'
        first = path.read_text(encoding='utf-8')
        rich_after_first = rich.read_text(encoding='utf-8')
        second = module.run(self.site)
        self.assertEqual(first, path.read_text(encoding='utf-8'))
        self.assertEqual(expected_rich, rich_after_first)
        self.assertEqual(rich_after_first, rich.read_text(encoding='utf-8'))
        self.assertNotIn(module.START, rich_after_first)
        self.assertEqual(
            module.visible_words(before_rich),
            module.visible_words(rich_after_first),
        )
        self.assertGreaterEqual(second['already_enriched_pages'], 8)
        self.assertGreaterEqual(second['sufficient_pages'], 1)


if __name__ == '__main__':
    unittest.main()
