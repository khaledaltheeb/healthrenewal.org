import json, tempfile, unittest
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parent
SCRIPT=ROOT.parent/'scripts'/'publish_special_needs_knowledge_wave002.py'
spec=importlib.util.spec_from_file_location('pub',SCRIPT)
pub=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)
pub.CATALOG=ROOT.parent/'content'/'v501'/'bootstrap'/'manifest.json.gz.b64'

class TestWave(unittest.TestCase):
    def test_manifest_pool(self):
        import base64,gzip
        d=json.loads(gzip.decompress(base64.b64decode(pub.CATALOG.read_text(encoding='ascii'))).decode('utf-8'))
        self.assertEqual(d['target_page_count'],100)
        self.assertGreaterEqual(len(d['candidates']),140)
        self.assertEqual(len({x['id'] for x in d['candidates']}),len(d['candidates']))

    def test_publish_100(self):
        with tempfile.TemporaryDirectory() as td:
            site=Path(td)
            (site/'special-needs').mkdir()
            (site/'special-needs/index.html').write_text('<html lang="ar" dir="rtl"><main><h1>ذوو الاحتياجات الخاصة</h1></main></html>',encoding='utf-8')
            for title,route in [('تأخر الكلام عند الأطفال','existing/speech-delay'),('التقييم النفسي التربوي','existing/assessment')]:
                p=site/route/'index.html'
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(f'<html><h1>{title}</h1></html>',encoding='utf-8')
            r=pub.publish(site)
            self.assertEqual(r['page_count'],100)
            self.assertEqual(r['unique_routes'],100)
            self.assertGreaterEqual(r['minimum_word_count'],1300)
            self.assertTrue((site/'api/special-needs-knowledge-wave002.json').is_file())
            hub=site/'special-needs/knowledge/index.html'
            self.assertTrue(hub.is_file())
            hub_text=hub.read_text(encoding='utf-8')
            self.assertIn('CollectionPage',hub_text)
            self.assertIn('ItemList',hub_text)
            for p in r['pages'][:5]:
                s=(site/p['route'].strip('/')/'index.html').read_text(encoding='utf-8')
                self.assertIn('canonical',s)
                self.assertIn('FAQPage',s)
                self.assertIn('مكتبة روافد المعرفية',s)

if __name__=='__main__':
    unittest.main()
