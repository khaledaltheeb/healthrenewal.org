from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "assessments" / "trauma-measures" / "index.html"
PC = ROOT / "assessments" / "trauma-measures" / "pc-ptsd-5" / "index.html"
PC_JS = PC.with_name("pcptsd5.js")
PCL = ROOT / "assessments" / "trauma-measures" / "pcl-5" / "index.html"
PCL_JS = PCL.with_name("pcl5.js")
MENTAL = ROOT / "assessments" / "mental-health-screeners" / "index.html"
REGISTRY = ROOT / "content" / "global-measures-v1" / "trauma-and-policy-restricted.json"


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.ids=[]
    def handle_starttag(self, tag, attrs):
        for k,v in attrs:
            if k=='id' and v: self.ids.append(v)


def assert_unique(testcase, html):
    p=IdParser(); p.feed(html)
    testcase.assertEqual({x for x in p.ids if p.ids.count(x)>1}, set())


class TraumaWave5Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub=HUB.read_text(encoding='utf-8')
        cls.pc=PC.read_text(encoding='utf-8')
        cls.pc_js=PC_JS.read_text(encoding='utf-8')
        cls.pcl=PCL.read_text(encoding='utf-8')
        cls.pcl_js=PCL_JS.read_text(encoding='utf-8')
        cls.mental=MENTAL.read_text(encoding='utf-8')
        cls.registry=json.loads(REGISTRY.read_text(encoding='utf-8'))

    def test_pages_are_rtl_and_ids_unique(self):
        for html in (self.hub,self.pc,self.pcl):
            self.assertIn('<html lang="ar" dir="rtl">',html)
            self.assertIn('index,follow',html)
            assert_unique(self,html)

    def test_pcptsd5_has_exposure_gate_and_five_items(self):
        self.assertIn('name="pc-exposure"',self.pc)
        for n in range(1,6):
            self.assertEqual(len(re.findall(fr'name="pc{n}"',self.pc)),2)
        self.assertIn("exposure==='no'",self.pc_js)
        self.assertIn("$('#pc-total').textContent='0 / 5'",self.pc_js)
        self.assertIn("total>=4",self.pc_js)
        self.assertIn('لا يثبت التشخيص',self.pc_js)

    def test_pcl5_has_20_items_five_responses_each(self):
        for n in range(1,21):
            self.assertEqual(len(re.findall(fr'name="pcl{n}"',self.pcl)),5)
        self.assertIn('Array.from({length:20}',self.pcl_js)
        self.assertIn('answered===20',self.pcl_js)
        self.assertIn('sumRange(vals,1,5)',self.pcl_js)
        self.assertIn('sumRange(vals,6,7)',self.pcl_js)
        self.assertIn('sumRange(vals,8,14)',self.pcl_js)
        self.assertIn('sumRange(vals,15,20)',self.pcl_js)

    def test_pcl5_does_not_auto_provisionally_diagnose(self):
        self.assertIn('لا تنفذ خوارزمية «تشخيص محتمل» تلقائيًا',self.pcl)
        self.assertNotIn('provisional=true',self.pcl_js)
        self.assertNotIn('DSM-5 diagnostic rule',self.pcl_js)
        self.assertIn('31–33',self.pcl)
        self.assertIn('خصوصية منخفضة',self.pcl)

    def test_pcl5_accessibility_labels_generated(self):
        self.assertIn('wireA11y()',self.pcl_js)
        self.assertIn("setAttribute('aria-label'",self.pcl_js)
        self.assertIn("responseLabels",self.pcl_js)

    def test_risk_item_is_review_not_suicide_inference(self):
        self.assertIn('const risky=vals[15]',self.pcl_js)
        self.assertIn('لا يقيس خطر الانتحار بصورة كافية',self.pcl)
        self.assertNotIn('انتحار مؤكد',self.pcl)

    def test_rights_registry(self):
        records={x['id']:x for x in self.registry['measures']}
        for mid in ('pc-ptsd-5','pcl-5'):
            self.assertEqual(records[mid]['rights']['status'],'public-domain-not-copyrighted')
            self.assertIn('qualified health professionals and researchers',records[mid]['rights']['intended_users'])
        self.assertFalse(records['pcl-5']['provisional_diagnostic_algorithm_in_rawafid_ui'])
        self.assertFalse(records['pcl-5']['arabic']['official_va_translation'])

    def test_dass21_is_policy_link_only_not_public_test(self):
        dass=next(x for x in self.registry['measures'] if x['id']=='dass-21')
        self.assertEqual(dass['type'],'official-link-only-on-public-web')
        self.assertFalse(dass['rights']['open_public_web_or_app_administration'])
        self.assertTrue(dass['arabic']['official_translation_available'])
        self.assertIn('Official Link Only',self.mental)
        self.assertIn('https://dass.psy.unsw.edu.au/Arabic/Arabic.htm',self.mental)
        self.assertNotIn('/assessments/mental-health-screeners/dass-21/',self.mental)


if __name__=='__main__':
    unittest.main()
