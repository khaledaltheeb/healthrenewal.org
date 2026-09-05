from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HUB=ROOT/'assessments'/'distress-screeners'/'index.html'
K6=ROOT/'assessments'/'distress-screeners'/'k6'/'index.html'
K6_JS=K6.with_name('k6.js')
K10=ROOT/'assessments'/'distress-screeners'/'k10'/'index.html'
K10_JS=K10.with_name('k10.js')
REGISTRY=ROOT/'content'/'global-measures-v1'/'kessler-distress-scales.json'

class IdParser(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True); self.ids=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k=='id' and v:self.ids.append(v)

def assert_unique(testcase,html):
    p=IdParser();p.feed(html);testcase.assertEqual({x for x in p.ids if p.ids.count(x)>1},set())

class KesslerWave7Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub=HUB.read_text(encoding='utf-8');cls.k6=K6.read_text(encoding='utf-8');cls.k6_js=K6_JS.read_text(encoding='utf-8');cls.k10=K10.read_text(encoding='utf-8');cls.k10_js=K10_JS.read_text(encoding='utf-8');cls.registry=json.loads(REGISTRY.read_text(encoding='utf-8'))

    def test_pages_rtl_indexable_unique(self):
        for html in (self.hub,self.k6,self.k10):
            self.assertIn('<html lang="ar" dir="rtl">',html);self.assertIn('index,follow',html);assert_unique(self,html)

    def test_k6_six_items_five_responses_and_complete_only(self):
        for n in range(1,7):self.assertEqual(len(re.findall(fr'name="k6_{n}"',self.k6)),5)
        self.assertIn('length:6',self.k6_js);self.assertIn('answered<6',self.k6_js);self.assertIn('/ 24',self.k6_js);self.assertIn('total>=13',self.k6_js)
        self.assertIn('لا يُعامل كتشخيص أو cut-off عربي عام',self.k6_js)

    def test_k10_ten_items_five_responses_and_no_universal_band(self):
        for n in range(1,11):self.assertEqual(len(re.findall(fr'name="k10_{n}"',self.k10)),5)
        self.assertIn('length:10',self.k10_js);self.assertIn('answered<10',self.k10_js);self.assertIn('/ 40',self.k10_js)
        self.assertIn('لا تطبق روافد cut-off أو تصنيف شدة عالميًا',self.k10_js)
        self.assertIn('10–50',self.k10);self.assertIn('0–40',self.k10)

    def test_a11y_labels_generated(self):
        self.assertIn('wireA11y()',self.k6_js);self.assertIn("setAttribute('aria-label'",self.k6_js)
        self.assertIn('wireA11y()',self.k10_js);self.assertIn("setAttribute('aria-label'",self.k10_js)

    def test_rights_and_official_arabic_sources(self):
        self.assertIn('الاستخدام دون إذن رسمي',self.hub)
        self.assertIn('الاستخدام غير المقيّد',self.hub)
        records={x['id']:x for x in self.registry['measures']}
        self.assertEqual(set(records),{'k6','k10'})
        self.assertIn('free and no formal permission',self.registry['rights_policy'])
        self.assertIn('Arabic_K6.pdf',records['k6']['official_arabic_pdf'])
        self.assertIn('Arabic_K10.pdf',records['k10']['official_arabic_pdf'])
        self.assertFalse(records['k6']['diagnostic_by_score_alone']);self.assertFalse(records['k10']['diagnostic_by_score_alone'])
        self.assertFalse(records['k10']['universal_cutoff'])

    def test_arabic_evidence_preserved(self):
        records={x['id']:x for x in self.registry['measures']}
        self.assertEqual(records['k6']['arabic_evidence']['cronbach_alpha'],0.81)
        self.assertEqual(records['k10']['arabic_evidence']['cronbach_alpha'],0.88)
        self.assertEqual(records['k6']['arabic_evidence']['sample_n'],234)

if __name__=='__main__':unittest.main()
