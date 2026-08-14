import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'publish_special_needs_knowledge_core_v1.py'
spec = importlib.util.spec_from_file_location('knowledge_core', SCRIPT)
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


class KnowledgeCoreV1Test(unittest.TestCase):
    def test_source_contract(self):
        self.assertGreaterEqual(len(pub.TOPICS), 20)
        self.assertEqual(len({x['slug'] for x in pub.TOPICS}), len(pub.TOPICS))
        self.assertEqual(len({x['title'] for x in pub.TOPICS}), len(pub.TOPICS))
        for topic in pub.TOPICS:
            self.assertGreaterEqual(len(topic['points']), 6)
            self.assertGreaterEqual(len(topic['steps']), 5)
            self.assertGreaterEqual(len(topic['faq']), 4)
            self.assertGreaterEqual(len(topic['sources']), 1)
            for sid in topic['sources']:
                self.assertIn(sid, pub.SOURCES)
                self.assertTrue(pub.SOURCES[sid]['url'].startswith('https://'))

    def test_publish_exactly_twenty_with_quality(self):
        with tempfile.TemporaryDirectory() as td:
            site = Path(td)
            (site / 'special-needs').mkdir(parents=True)
            (site / 'special-needs' / 'index.html').write_text(
                '<html lang="ar" dir="rtl"><head><title>ذوو الاحتياجات الخاصة</title></head><body><h1>ذوو الاحتياجات الخاصة</h1></body></html>',
                encoding='utf-8',
            )
            report = pub.publish(site)
            self.assertEqual(report['status'], 'passed')
            self.assertEqual(report['page_count'], 20)
            self.assertEqual(report['unique_routes'], 20)
            self.assertGreaterEqual(report['minimum_word_count'], 650)
            self.assertEqual(len(report['pages']), 20)
            self.assertTrue((site / 'special-needs' / 'knowledge-core' / 'index.html').is_file())
            self.assertTrue((site / 'api' / 'special-needs-knowledge-core-v1.json').is_file())
            for page in report['pages']:
                path = site / page['route'].strip('/') / 'index.html'
                text = path.read_text(encoding='utf-8')
                self.assertIn('<link rel="canonical"', text)
                self.assertIn('FAQPage', text)
                self.assertIn('BreadcrumbList', text)
                self.assertIn('المراجع الأصلية المستخدمة', text)
                self.assertNotIn('noindex', text)

    def test_existing_route_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            site = Path(td)
            (site / 'special-needs').mkdir(parents=True)
            (site / 'special-needs' / 'index.html').write_text('<html><h1>المركز</h1></html>', encoding='utf-8')
            first = pub.TOPICS[0]
            existing = site / 'special-needs' / first['slug'] / 'index.html'
            existing.parent.mkdir(parents=True)
            existing.write_text('<html><head><title>صفحة قائمة</title></head><body><h1>صفحة قائمة</h1><p>KEEP-ME</p></body></html>', encoding='utf-8')
            report = pub.publish(site)
            self.assertEqual(existing.read_text(encoding='utf-8').count('KEEP-ME'), 1)
            self.assertTrue(any(x['slug'] == first['slug'] for x in report['skipped']))
            self.assertLess(report['page_count'], 20 if len(pub.TOPICS) == 20 else 21)

    def test_report_is_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            site = Path(td)
            (site / 'special-needs').mkdir(parents=True)
            (site / 'special-needs' / 'index.html').write_text('<html><h1>المركز</h1></html>', encoding='utf-8')
            pub.publish(site)
            payload = json.loads((site / 'api' / 'special-needs-knowledge-core-v1.json').read_text(encoding='utf-8'))
            self.assertEqual(payload['schemaVersion'], 1)
            self.assertEqual(payload['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
