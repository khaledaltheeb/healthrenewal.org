import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/'scripts/enrich_thin_content_v222.py';spec=importlib.util.spec_from_file_location('depth',SCRIPT);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
PAGE='<!doctype html><html lang="ar" dir="rtl"><head><meta name="robots" content="index,follow"><title>{0}</title></head><body><main><h1>{0}</h1><p>{1}</p></main></body></html>'
class ContentDepthV222Tests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.site=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def page(self,r,t,b='نص قصير'):
  p=self.site/r;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(PAGE.format(t,b),encoding='utf-8');return p
 def test_expands_comparison_with_method_and_sources(self):
  p=self.page('comparisons/a/index.html','الفرق بين القلق والخوف');r=m.run(self.site);x=p.read_text(encoding='utf-8');self.assertEqual(r['status'],'passed');self.assertIn('منهجية المقارنة',x);self.assertIn('9789240077263',x);self.assertGreaterEqual(m.words(' '.join(m.parse(x).txt)),m.POL['comparisons'][1])
 def test_assessment_includes_psychometric_contract(self):
  p=self.page('assessments/a/index.html','مقياس استكشافي');self.assertEqual(m.run(self.site)['status'],'passed');x=p.read_text(encoding='utf-8');self.assertIn('الصدق والثبات',x);self.assertIn('testingstandards.net',x);self.assertIn('cosmin.nl',x)
 def test_is_idempotent(self):
  p=self.page('library/a/index.html','قراءة الأبحاث');m.run(self.site);x=p.read_text(encoding='utf-8');m.run(self.site);self.assertEqual(x,p.read_text(encoding='utf-8'));self.assertEqual(x.count(m.START),1)
 def test_skips_noindex_and_non_arabic(self):
  p=self.page('comparisons/private/index.html','خاص');p.write_text(p.read_text(encoding='utf-8').replace('index,follow','noindex'),encoding='utf-8');e=self.page('en/library/index.html','English');e.write_text(e.read_text(encoding='utf-8').replace('lang="ar" dir="rtl"','lang="en" dir="ltr"'),encoding='utf-8');self.assertEqual(m.run(self.site)['enriched_pages'],0);self.assertNotIn(m.START,p.read_text(encoding='utf-8'));self.assertNotIn(m.START,e.read_text(encoding='utf-8'))
 def test_rich_page_is_not_modified(self):
  p=self.page('library/rich/index.html','غني',' '.join(['معلومة']*500));x=p.read_text(encoding='utf-8');r=m.run(self.site);self.assertEqual(x,p.read_text(encoding='utf-8'));self.assertEqual(r['sufficient_pages'],1)
 def test_report_has_no_remaining_short_pages(self):
  self.page('special-needs/a/index.html','دعم المشاركة');self.page('daily-tools/a/index.html','سجل يومي');r=m.run(self.site);saved=json.loads((self.site/'api/content-depth-v222.json').read_text(encoding='utf-8'));self.assertEqual(r['remaining_below_minimum'],0);self.assertEqual(saved['status'],'passed');self.assertTrue((self.site/'assets/css/content-depth-v222.css').is_file())
if __name__=='__main__':unittest.main()