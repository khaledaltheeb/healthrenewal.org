from __future__ import annotations

import json,re,unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HUB=ROOT/'assessments'/'wellbeing-somatic-screeners'/'index.html'; PHQ4=ROOT/'assessments'/'wellbeing-somatic-screeners'/'phq-4'/'index.html'; PHQ4_JS=PHQ4.with_name('phq4.js'); PHQ15=ROOT/'assessments'/'wellbeing-somatic-screeners'/'phq-15'/'index.html'; PHQ15_JS=PHQ15.with_name('phq15.js'); WHO5=ROOT/'assessments'/'wellbeing-somatic-screeners'/'who-5'/'index.html'; WHO5_JS=WHO5.with_name('who5.js'); REGISTRY=ROOT/'content'/'global-measures-v1'/'wellbeing-somatic-open-tools.json'
class IdParser(HTMLParser):
 def __init__(self): super().__init__(convert_charrefs=True); self.ids=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k=='id' and v:self.ids.append(v)
def assert_unique(testcase,html):
 p=IdParser();p.feed(html);testcase.assertEqual({x for x in p.ids if p.ids.count(x)>1},set())
class WellbeingSomaticWave6Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.hub=HUB.read_text(encoding='utf-8');cls.phq4=PHQ4.read_text(encoding='utf-8');cls.phq4_js=PHQ4_JS.read_text(encoding='utf-8');cls.phq15=PHQ15.read_text(encoding='utf-8');cls.phq15_js=PHQ15_JS.read_text(encoding='utf-8');cls.who5=WHO5.read_text(encoding='utf-8');cls.who5_js=WHO5_JS.read_text(encoding='utf-8');cls.registry=json.loads(REGISTRY.read_text(encoding='utf-8'))
 def test_pages_rtl_indexable_unique(self):
  for html in (self.hub,self.phq4,self.phq15,self.who5): self.assertIn('<html lang="ar" dir="rtl">',html);self.assertIn('index,follow',html);assert_unique(self,html)
 def test_phq4_exact_structure_and_scoring(self):
  for n in range(1,5):self.assertEqual(len(re.findall(fr'name="q{n}"',self.phq4)),4)
  for s in ('v.every(x=>x!==null)','const gad=v[0]+v[1],phq=v[2]+v[3]','gad>=3','phq>=3','total<=2','total<=5','total<=8','لا يثبت ذلك تشخيصًا'):self.assertIn(s,self.phq4_js)
 def test_phq15_exact_structure_and_na_policy(self):
  for n in range(1,16):self.assertEqual(len(re.findall(fr'name="p15_{n}"',self.phq15)),4 if n==4 else 3)
  for s in ('value="na"',"item4na=vals[3]==='na'",'/ 28 (14 بندًا)','لا تُطبق نقاط القطع 5/10/15','numeric.length!==15','لا تحدد الدرجة سبب الأعراض'):self.assertIn(s,self.phq15 if s=='value="na"' else self.phq15_js)
 def test_phq15_a11y_labels_generated(self):self.assertIn('wireA11y()',self.phq15_js);self.assertIn("setAttribute('aria-label'",self.phq15_js)
 def test_who5_exact_items_direction_and_formula(self):
  for n in range(1,6):self.assertEqual(len(re.findall(fr'name="w{n}"',self.who5)),6)
  for s in ('answered<5','pct=raw*4','raw<13','لا يثبت تشخيصًا'):self.assertIn(s,self.who5_js)
  self.assertIn('الأرقام الأعلى رفاهًا أفضل',self.who5)
 def test_who5_open_license_and_translation_disclaimer(self):
  for s in ('CC BY‑NC‑SA 3.0 IGO','ترجمة/صياغة عربية من روافد وليست ترجمة أنشأتها WHO','لا يعني عرض الأداة أن WHO تعتمد روافد','لا ينبغي استخدام شعار WHO'):self.assertIn(s,self.who5)
  self.assertNotIn('assets/who-logo',self.who5.lower())
 def test_registry_rights_and_no_fake_diagnosis(self):
  records={x['id']:x for x in self.registry['measures']};self.assertEqual(set(records),{'phq-4','phq-15','who-5'})
  for key in ('phq-4','phq-15'):
   rights=records[key]['rights'];self.assertEqual(rights['status'],'copyrighted-permissive-use');self.assertEqual(rights['copyright_holder'],'Pfizer Inc.');self.assertFalse(rights['permission_required_to_reproduce']);self.assertFalse(rights['permission_required_to_translate']);self.assertFalse(records[key]['diagnostic_by_score_alone'])
  self.assertTrue(records['phq-15']['menstrual_item']['may_be_not_applicable'])
  self.assertEqual(records['who-5']['rights']['status'],'CC-BY-NC-SA-3.0-IGO');self.assertTrue(records['who-5']['rights']['share_alike_required']);self.assertFalse(records['who-5']['rights']['commercial_use']);self.assertEqual(records['who-5']['direction'],'higher-is-better');self.assertEqual(records['who-5']['percentage_score_formula'],'raw * 4')
 def test_phq4_page_does_not_claim_no_copyright(self):
  self.assertNotIn('Copyright: No',self.phq4);self.assertIn('© Pfizer',self.phq4);self.assertIn('عدم الحاجة إلى إذن',self.phq4)
if __name__=='__main__':unittest.main()
