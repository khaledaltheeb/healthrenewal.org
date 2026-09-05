from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HUB=ROOT/'assessments'/'substance-use-screeners'/'index.html'
P1=ROOT/'assessments'/'substance-use-screeners'/'taps-1'/'index.html'
P1JS=P1.with_name('taps1.js')
P2=ROOT/'assessments'/'substance-use-screeners'/'taps-2'/'index.html'
P2JS=P2.with_name('taps2.js')
REGISTRY=ROOT/'content'/'global-measures-v1'/'taps-substance-use.json'

class IdParser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.ids=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k=='id' and v:self.ids.append(v)

def unique(testcase,html):
    p=IdParser();p.feed(html);testcase.assertEqual({x for x in p.ids if p.ids.count(x)>1},set())

class TapsWave9Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub=HUB.read_text(encoding='utf-8');cls.p1=P1.read_text(encoding='utf-8');cls.p1js=P1JS.read_text(encoding='utf-8');cls.p2=P2.read_text(encoding='utf-8');cls.p2js=P2JS.read_text(encoding='utf-8');cls.registry=json.loads(REGISTRY.read_text(encoding='utf-8'))

    def test_pages_are_rtl_indexable_unique(self):
        for html in (self.hub,self.p1,self.p2):self.assertIn('<html lang="ar" dir="rtl">',html);self.assertIn('index,follow',html);unique(self,html)

    def test_part1_has_four_domains_five_frequency_options(self):
        for n in range(1,5):self.assertEqual(len(re.findall(fr'name="t{n}"',self.p1)),5)
        self.assertEqual(self.p1.count('data-domain='),4)
        self.assertIn('id="alcohol-threshold"',self.p1)
        self.assertIn('5 مشروبات أو أكثر',self.p1)
        self.assertIn('4 مشروبات أو أكثر',self.p1)
        self.assertIn("vals[i]!=='never'",self.p1js)
        self.assertNotIn('overallScore',self.p1js)

    def test_part1_requires_complete_answers_and_threshold(self):
        self.assertIn('answered<4||!threshold',self.p1js)
        self.assertIn('لا إحالة تلقائية',self.p1js)
        self.assertIn('أي استخدام غير «أبدًا» يحتاج متابعة في TAPS‑2',self.p1js)

    def test_part2_has_nine_substance_domains_and_no_cross_substance_total(self):
        expected={'tobacco':3,'alcohol':4,'cannabis':3,'stimulants':3,'heroin':3,'rx-opioid':3,'sedative':3,'rx-stimulant':3,'other':1}
        for domain,max_score in expected.items():
            self.assertIn(f'data-domain="{domain}"',self.p2)
            self.assertIn(f'data-max="{max_score}"',self.p2)
        self.assertEqual(self.p2.count('class="card taps-domain"'),9)
        self.assertNotIn('درجة إدمان كلية',self.p2js)
        self.assertNotIn('grandTotal',self.p2js)

    def test_part2_scores_complete_domain_only(self):
        self.assertIn('vals.some(v=>v===null)',self.p2js)
        self.assertIn("vals.filter(v=>v==='yes').length",self.p2js)
        self.assertIn('لا تعتمد الدرجة قبل الإكمال',self.p2js)
        self.assertIn('درجة 1',self.p2js)
        self.assertIn('لا يمثل تشخيصًا تلقائيًا',self.p2js)

    def test_a11y_and_safety(self):
        self.assertIn('wireA11y()',self.p1js);self.assertIn("setAttribute('aria-label'",self.p1js)
        self.assertIn('wireA11y()',self.p2js);self.assertIn("setAttribute('aria-label'",self.p2js)
        self.assertIn('لا تقيس شدة الانسحاب',self.p2)
        self.assertIn('لا تطلب من الشخص إيقاف دواء موصوف',self.p2)

    def test_registry_contract(self):
        self.assertEqual(self.registry['rights']['status'],'public-domain')
        self.assertFalse(self.registry['part1']['overall_numeric_score'])
        self.assertFalse(self.registry['part2']['overall_numeric_score'])
        self.assertFalse(self.registry['part2']['interpretation']['diagnostic_by_score_alone'])
        self.assertFalse(self.registry['part2']['interpretation']['cross_substance_total_allowed'])
        self.assertEqual(self.registry['part2']['domains']['alcohol']['range'],[0,4])
        self.assertEqual(self.registry['part2']['domains']['other-drugs']['range'],[0,1])

if __name__=='__main__':unittest.main()
