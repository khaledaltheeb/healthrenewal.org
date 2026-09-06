from __future__ import annotations
import json,unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';WORK=ROOT/'assessments'/'global-measures'/'workspace'/'index.html';FINDER=ROOT/'assessments'/'global-measures'/'tool-finder'/'index.html';FINDER_JS=FINDER.with_name('finder.js');PACKETS=ROOT/'assessments'/'global-measures'/'print-packets'/'index.html';RECORD=ROOT/'assessments'/'global-measures'/'measurement-record'/'index.html';RECORD_JS=RECORD.with_name('record.js')
class IdParser(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.ids=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k=='id' and v:self.ids.append(v)
def unique(t,h):p=IdParser();p.feed(h);t.assertEqual({x for x in p.ids if p.ids.count(x)>1},set())
class WorkspaceWave10Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.catalog=json.loads(CAT.read_text(encoding='utf-8'));cls.work=WORK.read_text(encoding='utf-8');cls.finder=FINDER.read_text(encoding='utf-8');cls.finder_js=FINDER_JS.read_text(encoding='utf-8');cls.packets=PACKETS.read_text(encoding='utf-8');cls.record=RECORD.read_text(encoding='utf-8');cls.record_js=RECORD_JS.read_text(encoding='utf-8')
 def test_catalog_current_count_and_unique_routes(self):
  tools=self.catalog['tools'];n=self.catalog['actual_tool_count'];self.assertEqual(n,35);self.assertEqual(len(tools),35);self.assertEqual(len({x['id'] for x in tools}),35);self.assertEqual(len({x['route'] for x in tools}),35)
  ids={x['id'] for x in tools};self.assertTrue({'healthy-days','bbs','bbt','mas','mts','mrs','fac'}.issubset(ids));bbt=next(x for x in tools if x['id']=='bbt');self.assertIn('no bilateral total',bbt['score']);self.assertEqual(bbt['rights_state'],'rmd-not-free-equipment-operational-sheet-rights-not-public-domain-verified')
  for t in tools:self.assertTrue(t['actual'] and t['printable'] and t['rights_state'] and t['domain'] and t['population'] and t['score'] and t['route'].startswith('/'))
 def test_external_only_are_not_counted_actual(self):
  externals=self.catalog['official_link_only'];self.assertEqual({x['id'] for x in externals},{'dass21','minicog'});self.assertTrue({x['id'] for x in self.catalog['tools']}.isdisjoint({x['id'] for x in externals}))
 def test_workspace_and_finder_are_rtl_indexable_unique(self):
  for h in (self.work,self.finder,self.packets,self.record):self.assertIn('<html lang="ar" dir="rtl">',h);self.assertIn('index,follow',h);unique(self,h)
  self.assertIn('35 أداة/بطارية فعلية',self.work);self.assertIn('35 actual tools',self.finder);self.assertIn('BBT',self.work);self.assertIn('BBT',self.finder)
 def test_finder_uses_single_catalog_and_no_diagnostic_engine(self):
  self.assertIn('/content/global-measures-v1/catalog.json',self.finder_js);self.assertIn('filter(x=>x.actual===true)',self.finder_js);self.assertIn('لا يشخّص',self.finder);self.assertNotIn('diagnose(',self.finder_js.lower());self.assertNotIn('fetch("/api',self.finder_js.lower());self.assertIn('navigator.clipboard',self.finder_js)
 def test_packets_retain_redundancy_and_bbt_guards(self):
  for text in ('قاعدة تقليل العبء','FAC — استقلالية المشي','Not Testable','حزمة الطرف العلوي والبراعة اليدوية','BBT — البراعة اليدوية الإجمالية','Grip Strength — القوة','لا تعتبر القوة والبراعة الشيء نفسه','لا تجمع اليدين في مجموع BBT','MTS — R1/R2','لا تجمع درجات المواد المختلفة'):self.assertIn(text,self.packets)
 def test_record_protocol_identity_and_local_export(self):
  for text in ("const keys=['tool','version','language','period','unit']",'protocolChanged','assistChanged','غير قابل للمقارنة مباشرة','قابل بحذر','قابل للمقارنة بروتوكوليًا','new Blob','rawafid-measurement-record.json','rawafid-measurement-record.csv'):self.assertIn(text,self.record_js)
  self.assertNotIn('fetch(',self.record_js);self.assertNotIn('localStorage',self.record_js);self.assertIn('لا توجد قاعدة بيانات خلف هذا النموذج',self.record)
 def test_workspace_links_runtime_tools(self):
  for route in ('/assessments/global-measures/tool-finder/','/assessments/global-measures/print-packets/','/assessments/global-measures/measurement-record/'):self.assertIn(route,self.work)
if __name__=='__main__':unittest.main()
