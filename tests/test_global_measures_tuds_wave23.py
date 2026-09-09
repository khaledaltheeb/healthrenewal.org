from __future__ import annotations
import json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'timed-up-and-down-stairs'/'index.html';JS=PAGE.with_name('tuds.js');REG=ROOT/'content'/'global-measures-v1'/'timed-up-and-down-stairs.json';CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json';LIB=ROOT/'sectors'/'rehabilitation'/'measures'/'app.js';MAP=ROOT/'sitemap-rehabilitation-measures.xml';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class TudsWave23Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.cat=json.loads(CAT.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'));cls.lib=LIB.read_text(encoding='utf-8');cls.xml=MAP.read_text(encoding='utf-8')
 def test_protocol_is_not_hardcoded_to_one_staircase(self):
  p=self.reg['protocol_identity'];self.assertFalse(p['universal_stair_count']);self.assertTrue(p['longitudinal_comparison_requires_same_protocol_identity']);self.assertTrue(p['do_not_convert_to_seconds_per_step_as_a_standardized_equivalent']);
  for key in ('step_count_each_direction','riser_height','tread_depth','rail_policy_and_use','footwear','orthosis','timing_start_rule','top_turn_rule','timing_stop_rule'):self.assertIn(key,p['required_fields'])
  self.assertIn('لا يوجد عدد درجات عالمي واحد',self.html);self.assertIn('لا «ثواني/درجة» كمعادل معياري',self.html)
 def test_score_is_time_but_not_testable_is_not_zero(self):
  s=self.reg['scoring'];self.assertTrue(s['standardized_total_requires_testable_status']);self.assertTrue(s['not_testable_or_safety_stop_is_not_zero_seconds']);self.assertTrue(s['no_universal_diagnostic_cutoff']);self.assertIn("if(status!=='testable')",self.js);self.assertIn('غير قابل للاختبار — لا تسجل صفر ثانية',self.js);self.assertIn('Not Testable ≠ 0 ثانية',self.html)
 def test_protocol_completion_guard(self):
  for text in ("'#tuds-steps'","'#tuds-riser'","'#tuds-tread'","'#tuds-rail-policy'","'#tuds-start-rule'","'#tuds-turn-rule'","'#tuds-stop-rule'","'#tuds-pace'"):self.assertIn(text,self.js)
  self.assertIn('هوية البروتوكول الأساسية موثقة',self.js);self.assertIn('لا تعتبر المقارنة الطولية مكافئة',self.js)
 def test_evidence_preserves_protocol_specificity(self):
  self.assertEqual(self.reg['measurement']['original_2004']['doi'],'10.1097/01.PEP.0000127564.08922.6A');self.assertEqual(self.reg['measurement']['cp_2022']['doi'],'10.1186/s43161-022-00104-9');self.assertIn('10-step',self.reg['measurement']['cp_2022']['protocol_example']);self.assertIn('not a universal',self.reg['measurement']['cp_2022']['protocol_example']);self.assertIn('العمر والطول والوزن',self.html)
 def test_rights_and_arabic_fail_closed(self):
  self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');self.assertFalse(self.reg['arabic']['validated_or_authorized_arabic_form_verified']);self.assertFalse(self.reg['arabic']['claim_official_translation']);row=next(x for x in self.audit['current_library'] if x['id']=='tuds');self.assertEqual(row['decision'],'operational-sheet-only')
 def test_tool_40_in_catalog_library_and_sitemap(self):
  self.assertEqual(self.cat['actual_tool_count'],40);self.assertEqual(len(self.cat['tools']),40);row=next(x for x in self.cat['tools'] if x['id']=='tuds');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/timed-up-and-down-stairs/');self.assertIn('no universal stair count',row['score']);self.assertIn("tuds='/sectors/rehabilitation/measures/timed-up-and-down-stairs/'",self.lib);urls=[e.text for e in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/sectors/rehabilitation/measures/timed-up-and-down-stairs/'),1)
 def test_local_only_and_structured_page(self):
  self.assertNotIn('fetch(',self.js);self.assertNotIn('localStorage',self.js);self.assertIn('application/ld+json',self.html);self.assertIn('data-pt-normalized="2.0.0"',self.html);self.assertIn('rel="canonical" href="https://healthrenewal.org/sectors/rehabilitation/measures/timed-up-and-down-stairs/"',self.html)
if __name__=='__main__':unittest.main()
