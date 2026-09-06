from __future__ import annotations
import json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'functional-reach-test'/'index.html';JS=PAGE.with_name('frt.js');REG=ROOT/'content'/'global-measures-v1'/'functional-reach-test.json';CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json';LIB=ROOT/'sectors'/'rehabilitation'/'measures'/'app.js';SITEMAP=ROOT/'sitemap-rehabilitation-measures.xml';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class FunctionalReachWave22Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.cat=json.loads(CAT.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'));cls.lib=LIB.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8')
 def test_protocol_versions_are_explicit(self):
  self.assertTrue(self.reg['rmd']['protocol_conflict_requires_version_recording']);self.assertEqual(self.reg['rmd']['current_page_protocol']['practice_trials'],2);self.assertEqual(self.reg['rmd']['current_page_protocol']['scored_trials'],3);self.assertEqual(self.reg['rmd']['legacy_rmd_hosted_pdf_protocol']['total_trials'],3);self.assertIn('2 practice + 3 scored',json.dumps(self.reg));self.assertIn('محاولتين تدريب ثم 3 محاولات اختبار',self.html);self.assertIn('3 محاولات إجمالًا ومتوسط آخر محاولتين',self.html)
 def test_runtime_is_fail_closed_by_protocol(self):
  self.assertIn("protocol==='current'?[1,2,3]:[1,2]",self.js);self.assertIn("if(protocol==='other')",self.js);self.assertIn('يلزم 3 محاولات اختبار صالحة',self.js);self.assertIn('بروتوكول آخر',self.js);self.assertIn("*2.54",self.js)
 def test_invalid_base_or_safety_trials_are_not_used(self):
  self.assertTrue(self.reg['procedure_model']['step_or_loss_of_fixed_base_invalidates_trial']);self.assertIn('خطوة/تحركت قاعدة الارتكاز',self.html);self.assertIn('فقد توازن/أوقف للسلامة',self.html);self.assertIn("value==='صالح'",self.js)
 def test_rights_are_conservative(self):
  self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertTrue(self.reg['rights']['rmd_cde_copyright_notice']);self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');row=next(x for x in self.audit['current_library'] if x['id']=='frt');self.assertEqual(row['decision'],'operational-sheet-only');self.assertIn('NINDS CDE Notice of Copyright',row['rmd_cost_description']);self.assertIn('rule_8',self.audit['method'])
 def test_no_universal_cutoff_and_population_specific_mdc(self):
  self.assertTrue(self.reg['scoring']['no_universal_fall_risk_cutoff']);self.assertTrue(self.reg['scoring']['population_specific_norms_and_mdc']);self.assertIn('لا cutoff عالمي للسقوط',self.html);self.assertEqual(self.reg['measurement_properties']['original_study']['clinical_apparatus_day_to_day_icc'],0.81)
 def test_arabic_not_overclaimed(self):
  self.assertFalse(self.reg['arabic']['validated_or_official_arabic_form_identified_in_this_review']);self.assertFalse(self.reg['arabic']['claim_official_translation']);self.assertIn('لا تدعي ترجمة عربية رسمية',self.html)
 def test_tool_39_integration(self):
  self.assertEqual(self.cat['actual_tool_count'],39);self.assertEqual(len(self.cat['tools']),39);row=next(x for x in self.cat['tools'] if x['id']=='frt');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/functional-reach-test/');self.assertEqual(row['rights_state'],'rmd-free-ninds-cde-copyright-operational-sheet-only');self.assertIn("frt='/sectors/rehabilitation/measures/functional-reach-test/'",self.lib);self.assertIn('FRT: الوصول الأمامي وحدود الثبات',self.lib);urls=[e.text for e in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/sectors/rehabilitation/measures/functional-reach-test/'),1)
if __name__=='__main__':unittest.main()
