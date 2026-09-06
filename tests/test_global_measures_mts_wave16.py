from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'modified-tardieu-scale'/'index.html';JS=PAGE.with_name('mts.js');REG=ROOT/'content'/'global-measures-v1'/'modified-tardieu-scale.json'
class ModifiedTardieuWave16Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'))
 def test_core_velocity_and_angle_model(self):
  for text in ('V1','V2','V3','R1','R2','R2−R1'):self.assertIn(text,self.html)
  self.assertTrue(self.reg['calculation']['r2_minus_r1']);self.assertTrue(self.reg['calculation']['requires_same_joint_axis_and_angle_convention'])
 def test_multi_muscle_sheet_and_runtime(self):
  for text in ('العضلة/المجموعة','المفصل والحركة','نسخة QMR','Clonus ث','الألم أو الملاحظة'):self.assertIn(text,self.html+self.js)
  self.assertIn('for(let i=0;i<8;i++)addRow()',self.js);self.assertIn('const d=r2-r1',self.js);self.assertIn('addRow()',self.js)
 def test_no_fake_global_total_or_cross_version_conversion(self):
  self.assertFalse(self.reg['instrument']['aggregate_across_muscles']);self.assertIsNone(self.reg['instrument']['global_total_score']);self.assertFalse(self.reg['calculation']['qmr_version_conversion']);self.assertTrue(self.reg['calculation']['qmr_is_not_summed']);self.assertNotIn('reduce(',self.js);self.assertIn('لا يوجد «مجموع MTS كلي»',self.html);self.assertIn('لا تحوّل 0–4 إلى 0–5',self.html)
 def test_rights_are_conservative_not_public_domain_claim(self):
  self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');self.assertIn('Free لا يساوي Public Domain',self.html);self.assertIn('ورقة تسجيل وحساب أصلية من روافد',self.html)
 def test_arabic_not_overclaimed(self):
  self.assertFalse(self.reg['arabic']['validated_arabic_form_identified_in_this_review']);self.assertFalse(self.reg['arabic']['claim_official_translation']);self.assertIn('لا نصف هذا النص بأنه ترجمة عربية متحققة أو رسمية',self.html)
 def test_interpretation_guardrails(self):
  for text in ('لا تعمم MDC/SEM','لا تستنتج المشي من الاختبار','MAS وMTS ليستا بديلين كاملين','السرعة جزء من القياس'):self.assertIn(text,self.html)
if __name__=='__main__':unittest.main()
