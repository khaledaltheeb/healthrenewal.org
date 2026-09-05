from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "assessments" / "mental-health-screeners" / "index.html"
PHQ = ROOT / "assessments" / "mental-health-screeners" / "phq-9" / "index.html"
PHQ_JS = PHQ.with_name("phq9.js")
GAD = ROOT / "assessments" / "mental-health-screeners" / "gad-7" / "index.html"
GAD_JS = GAD.with_name("gad7.js")
REGISTRY = ROOT / "content" / "global-measures-v1" / "mental-health-open-screeners.json"

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.ids=[]
    def handle_starttag(self, tag, attrs):
        for k,v in attrs:
            if k=="id" and v: self.ids.append(v)

def unique_ids(testcase, html):
    p=IdParser(); p.feed(html)
    testcase.assertEqual({x for x in p.ids if p.ids.count(x)>1}, set())

class MentalHealthWave4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub=HUB.read_text(encoding="utf-8")
        cls.phq=PHQ.read_text(encoding="utf-8")
        cls.phq_js=PHQ_JS.read_text(encoding="utf-8")
        cls.gad=GAD.read_text(encoding="utf-8")
        cls.gad_js=GAD_JS.read_text(encoding="utf-8")
        cls.registry=json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_pages_are_arabic_rtl_indexable_and_unique(self):
        for html in (self.hub,self.phq,self.gad):
            self.assertIn('<html lang="ar" dir="rtl">',html)
            self.assertIn('index,follow',html)
            unique_ids(self,html)

    def test_phq9_has_nine_items_and_complete_only_scoring(self):
        for name in ['phq1','phq2i','phq3','phq4','phq5','phq6','phq7','phq8','phq9']:
            self.assertEqual(len(re.findall(fr'name="{name}"',self.phq)),4)
        self.assertIn('complete=vals.every',self.phq_js)
        self.assertIn("vals.reduce((a,b)=>a+b,0)",self.phq_js)
        self.assertIn('slice(0,2)',self.phq_js)
        self.assertIn('— / 27',self.phq_js)

    def test_phq9_safety_is_independent_from_total(self):
        self.assertIn('id="phq-safety"',self.phq)
        self.assertIn('item9!==null&&item9>0',self.phq_js)
        self.assertIn("$('#phq-safety').hidden=!safety",self.phq_js)
        self.assertIn('بند 9 يُراجع مستقلاً عن المجموع',self.phq)
        self.assertNotIn('خطر منخفض لأن المجموع',self.phq)

    def test_gad7_has_seven_items_and_complete_only_scoring(self):
        for name in ['gad1','gad2i','gad3','gad4','gad5','gad6','gad7']:
            self.assertEqual(len(re.findall(fr'name="{name}"',self.gad)),4)
        self.assertIn('complete=vals.every',self.gad_js)
        self.assertIn("vals.reduce((a,b)=>a+b,0)",self.gad_js)
        self.assertIn('slice(0,2)',self.gad_js)
        self.assertIn('— / 21',self.gad_js)

    def test_neither_page_claims_score_is_diagnosis(self):
        self.assertIn('لا يثبت تشخيص',self.phq)
        self.assertIn('لا تثبت',self.gad)
        self.assertIn('الفحص لا يثبت تشخيصًا',self.phq_js)
        self.assertIn('الفحص لا يثبت تشخيصًا',self.gad_js)

    def test_registry_separates_copyright_from_permission(self):
        self.assertEqual({m['id'] for m in self.registry['measures']},{'phq-9','gad-7'})
        for measure in self.registry['measures']:
            rights=measure['rights']
            self.assertEqual(rights['status'],'copyrighted-permissive-use')
            self.assertEqual(rights['copyright_holder'],'Pfizer Inc.')
            self.assertFalse(rights['permission_required_to_reproduce'])
            self.assertFalse(rights['permission_required_to_translate'])
            self.assertFalse(rights['permission_required_to_display'])
            self.assertFalse(rights['permission_required_to_distribute'])
            self.assertFalse(measure['diagnostic_by_score_alone'])
            self.assertEqual(measure['rawafid_arabic_status'],'independent-operational-Arabic-rendering')
        self.assertNotIn('Public domain',self.phq)
        self.assertNotIn('Public domain',self.gad)
        self.assertIn('© Pfizer',self.phq)
        self.assertIn('© Pfizer',self.gad)

    def test_phq9_specific_safety_contract_in_registry(self):
        phq=next(m for m in self.registry['measures'] if m['id']=='phq-9')
        self.assertEqual(phq['safety']['item'],9)
        self.assertIn('total score must not determine suicide risk',phq['safety']['rule'])

    def test_hub_links_both_tools_and_correct_rights_model(self):
        self.assertIn('/assessments/mental-health-screeners/phq-9/',self.hub)
        self.assertIn('/assessments/mental-health-screeners/gad-7/',self.hub)
        self.assertIn('Free ≠ Public Domain',self.hub)
        self.assertIn('© Pfizer',self.hub)

if __name__=='__main__':
    unittest.main()
