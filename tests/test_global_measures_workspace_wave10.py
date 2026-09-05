from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'content'/'global-measures-v1'/'catalog.json'
WORK=ROOT/'assessments'/'global-measures'/'workspace'/'index.html'
FINDER=ROOT/'assessments'/'global-measures'/'tool-finder'/'index.html'
FINDER_JS=FINDER.with_name('finder.js')
PACKETS=ROOT/'assessments'/'global-measures'/'print-packets'/'index.html'
RECORD=ROOT/'assessments'/'global-measures'/'measurement-record'/'index.html'
RECORD_JS=RECORD.with_name('record.js')

class IdParser(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True); self.ids=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k=='id' and v: self.ids.append(v)

def unique(testcase,html):
    p=IdParser();p.feed(html);testcase.assertEqual({x for x in p.ids if p.ids.count(x)>1},set())

class WorkspaceWave10Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads(CAT.read_text(encoding='utf-8'))
        cls.work=WORK.read_text(encoding='utf-8'); cls.finder=FINDER.read_text(encoding='utf-8'); cls.finder_js=FINDER_JS.read_text(encoding='utf-8')
        cls.packets=PACKETS.read_text(encoding='utf-8'); cls.record=RECORD.read_text(encoding='utf-8'); cls.record_js=RECORD_JS.read_text(encoding='utf-8')

    def test_catalog_has_exact_current_actual_unique_tools(self):
        tools=self.catalog['tools']; n=self.catalog['actual_tool_count']
        self.assertEqual(n,29); self.assertEqual(len(tools),n)
        self.assertEqual(len({x['id'] for x in tools}),n); self.assertEqual(len({x['route'] for x in tools}),n)
        self.assertIn('healthy-days',{x['id'] for x in tools})
        for t in tools:
            self.assertTrue(t['actual']); self.assertTrue(t['printable']); self.assertTrue(t['rights_state']); self.assertTrue(t['domain']); self.assertTrue(t['population']); self.assertTrue(t['score']); self.assertTrue(t['route'].startswith('/'))

    def test_external_only_are_not_counted_actual(self):
        externals=self.catalog['official_link_only']; self.assertEqual({x['id'] for x in externals},{'dass21','minicog'})
        self.assertTrue({x['id'] for x in self.catalog['tools']}.isdisjoint({x['id'] for x in externals}))

    def test_workspace_and_finder_are_rtl_indexable_unique(self):
        for html in (self.work,self.finder,self.packets,self.record):
            self.assertIn('<html lang="ar" dir="rtl">',html); self.assertIn('index,follow',html); unique(self,html)

    def test_finder_uses_single_catalog_and_no_diagnostic_engine(self):
        self.assertIn('/content/global-measures-v1/catalog.json',self.finder_js); self.assertIn('filter(x=>x.actual===true)',self.finder_js)
        self.assertIn('لا يشخّص',self.finder); self.assertNotIn('diagnose(',self.finder_js.lower()); self.assertNotIn('fetch("/api',self.finder_js.lower()); self.assertIn('navigator.clipboard',self.finder_js)

    def test_packets_reduce_redundancy_and_preserve_sequences(self):
        self.assertIn('قاعدة تقليل العبء',self.packets); self.assertIn('لا تستخدم 6MWT و2MWT معًا عادةً دون سبب',self.packets)
        self.assertIn('استخدم PHQ‑4 إذا كان المطلوب فحصًا فائق الاختصار',self.packets); self.assertIn('ابدأ بـTAPS‑1',self.packets); self.assertIn('لا تجمع درجات المواد المختلفة',self.packets); self.assertIn('Mini‑Cog العربي الرسمي',self.packets)

    def test_record_requires_protocol_identity_for_direct_comparison(self):
        self.assertIn("const keys=['tool','version','language','period','unit']",self.record_js); self.assertIn('protocolChanged',self.record_js); self.assertIn('assistChanged',self.record_js)
        self.assertIn('غير قابل للمقارنة مباشرة',self.record_js); self.assertIn('قابل بحذر',self.record_js); self.assertIn('قابل للمقارنة بروتوكوليًا',self.record_js)

    def test_record_exports_local_json_csv_without_server_storage(self):
        self.assertIn('new Blob',self.record_js); self.assertIn('rawafid-measurement-record.json',self.record_js); self.assertIn('rawafid-measurement-record.csv',self.record_js)
        self.assertNotIn('fetch(',self.record_js); self.assertNotIn('localStorage',self.record_js); self.assertIn('لا توجد قاعدة بيانات خلف هذا النموذج',self.record)

    def test_workspace_links_runtime_tools(self):
        for route in ('/assessments/global-measures/tool-finder/','/assessments/global-measures/print-packets/','/assessments/global-measures/measurement-record/'):
            self.assertIn(route,self.work)

if __name__=='__main__': unittest.main()
