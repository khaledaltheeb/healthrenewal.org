from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import audit_source_depth_gap_v231 as audit


def arabic_words(count: int) -> str:
    return ' '.join(f'كلمة{index}' for index in range(count))


def page(body: str, *, robots: str = 'index,follow', lang: str = 'ar') -> str:
    return (
        f'<!doctype html><html lang="{lang}" dir="rtl"><head><title>عنوان الصفحة</title>'
        f'<meta name="robots" content="{robots}"></head><body><main><h1>عنوان الصفحة</h1>'
        f'{body}</main></body></html>'
    )


class SourceDepthGapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.site = self.root / 'site'
        self.repo = self.root / 'repo'
        self.site.mkdir()
        (self.repo / 'scripts').mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, relative: str, source: str) -> None:
        target = self.site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding='utf-8')

    def test_detects_source_gap_and_infers_publisher(self) -> None:
        (self.repo / 'scripts/publish_trust_center_v201.py').write_text(
            'target = site / "trust" / "index.html"\nrender = True\n', encoding='utf-8'
        )
        body = (
            f'<p>{arabic_words(40)}</p>{audit.START}'
            f'<section><p>{arabic_words(250)}</p></section>{audit.END}'
        )
        self.write('trust/index.html', page(body))
        report = audit.audit(self.site, self.repo)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['source_gap_count'], 1)
        gap = report['gaps'][0]
        self.assertEqual(gap['route'], '/trust/')
        self.assertLess(gap['source_words'], gap['production_words'])
        self.assertIn('scripts/publish_trust_center_v201.py', gap['producer_candidates'])

    def test_reports_unhandled_thin_page_as_failure(self) -> None:
        self.write('library/index.html', page(f'<p>{arabic_words(30)}</p>'))
        report = audit.audit(self.site)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['unhandled_thin_count'], 1)

    def test_skips_noindex_and_non_arabic(self) -> None:
        self.write('library/noindex/index.html', page('قصير', robots='noindex,follow'))
        self.write('library/en/index.html', page('short', lang='en'))
        report = audit.audit(self.site)
        self.assertEqual(report['eligible_pages'], 0)
        self.assertEqual(report['skipped_noindex'], 1)
        self.assertEqual(report['skipped_non_arabic'], 1)

    def test_rejects_unbalanced_markers(self) -> None:
        self.write('comparisons/index.html', page(f'<p>{arabic_words(250)}</p>{audit.START}<section>ناقص</section>'))
        report = audit.audit(self.site)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['malformed_marker_count'], 1)

    def test_includes_institutional_routes_and_writes_reports(self) -> None:
        body = f'<p>{arabic_words(50)}</p>{audit.START}<section><p>{arabic_words(240)}</p></section>{audit.END}'
        self.write('methodology/index.html', page(body))
        report = audit.audit(self.site)
        json_path, md_path = self.root / 'report.json', self.root / 'report.md'
        audit.write_report(report, json_path, md_path)
        loaded = json.loads(json_path.read_text(encoding='utf-8'))
        self.assertEqual(loaded['version'], 231)
        self.assertEqual(loaded['gaps'][0]['minimum_words'], 230)
        self.assertIn('/methodology/', md_path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
