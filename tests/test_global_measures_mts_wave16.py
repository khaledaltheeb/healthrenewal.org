from __future__ import annotations
import json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'modified-tardieu-scale'/'index.html';JS=PAGE.with_name('mts.js');REG=ROOT/'content'/'global-measures-v1'/'modified-tardieu-scale.json';CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json';LIB=ROOT/'sectors'/'rehabilitation'/'measures'/'app.js';SITEMAP=ROOT/'sitemap-rehabilitation-measures.xml';PACKETS=ROOT/'assessments'/'global-measures'/'print-packets'/'index.html';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class ModifiedTardieuWave16Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.catalog=json.loads(CAT.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'));cls.lib=LIB.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8');cls.packets=PACKETS.read_text(encoding='utf-8')
 def test_core_velocity_and_angle_model(self):
  for text in ('V1','V2','V3','R1','R2','R2−R1'):self.assertIn(text,self.html)
  self.assertTrue(self.reg['calculation']['r2_minus_r1']);self.assertTrue(self.reg['calculation']['requires_same_joint_axis_and_angle_convention'])
 def test_multi_muscle_sheet_and_runtime(self):
  for text in ('العضلة/المجموعة','المفصل والحركة','نسخة QMR','Clonus ث','الألم أو الملاحظة'):self.assertIn(text,self.html+self.js)
  self.assertIn('for(let i=0;i<8;i++)addRow()',self.js);self.assertIn('const d=r2-r1',self.js);self.assertNotIn('reduce(',self.js)
 def test_no_fake_global_total_or_cross_version_conversion(self):
  self.assertFalse(self.reg['instrument']['aggregate_across_muscles']);self.assertIsNone(self.reg['instrument']['global_total_score']);self.assertFalse(self.reg['calculation']['qmr_version_conversion']);self.assertTrue(self.reg['calculation']['qmr_is_not_summed']);self.assertIn('لا يوجد «مجموع MTS كلي»',self.html);self.assertIn('لا تحوّل 0–4 إلى 0–5',self.html)
 def test_rights_are_conservative_not_public_domain_claim(self):
  self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');self.assertIn('Free لا يساوي Public Domain',self.html);self.assertIn('ورقة تسجيل وحساب أصلية من روافد',self.html)
  row=next(x for x in self.audit['current_library'] if x['id']=='mts');self.assertEqual(row['decision'],'operational-sheet-only');self.assertEqual(row['rmd_cost'],'Free');self.assertIn('no sufficiently authoritative explicit Public Domain',row['rights_source'])
 def test_arabic_not_overclaimed(self):
  self.assertFalse(self.reg['arabic']['validated_arabic_form_identified_in_this_review']);self.assertFalse(self.reg['arabic']['claim_official_translation']);self.assertIn('لا نصف هذا النص بأنه ترجمة عربية متحققة أو رسمية',self.html)
 def test_interpretation_guardrails(self):
  for text in ('لا تعمم MDC/SEM','لا تستنتج المشي من الاختبار','MAS وMTS ليستا بديلين كاملين','السرعة جزء من القياس'):self.assertIn(text,self.html)
 def test_catalog_library_packet_and_sitemap_integration(self):
  self.assertEqual(self.catalog['actual_tool_count'],33);self.assertEqual(len(self.catalog['tools']),33);row=next(x for x in self.catalog['tools'] if x['id']=='mts');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/modified-tardieu-scale/');self.assertEqual(row['rights_state'],'rmd-free-operational-sheet-rights-not-public-domain-verified');self.assertIn("mts='/sectors/rehabilitation/measures/modified-tardieu-scale/'",self.lib);self.assertIn('MTS: R1 / R2 / R2−R1 مع السرعة',self.lib);self.assertIn('MTS — R1/R2',self.packets);self.assertIn('لا تطبق MAS وMTS معًا تلقائيًا',self.packets);urls=[e.text for e in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/sectors/rehabilitation/measures/modified-tardieu-scale/'),1)
 def test_future_candidate_gates_are_conservative(self):
  rows={x['id']:x for x in self.audit['priority_candidates']};self.assertEqual(rows['fma']['decision'],'official-link-only');self.assertEqual(rows['fac']['decision'],'hold-rights');self.assertEqual(rows['rmdq24']['decision'],'hold-exact-arabic')
if __name__=='__main__':unittest.main()
