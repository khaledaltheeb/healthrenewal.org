from __future__ import annotations

import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'modified-ashworth-scale'/'index.html';JS=PAGE.with_name('mas.js');REG=ROOT/'content'/'global-measures-v1'/'modified-ashworth-scale.json'
class ModifiedAshworthWave14Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'))
 def test_all_six_grade_criteria_are_present(self):
  for grade in ('0','1','1+','2','3','4'):self.assertIn(f'<strong>{grade}</strong>',self.html)
  self.assertIn('أقل من نصف',self.html);self.assertIn('معظم مدى الحركة',self.html);self.assertIn('صلب/جامد',self.html)
 def test_recording_sheet_supports_multiple_muscles(self):
  for text in ('العضلة/المجموعة','المفصل/الحركة','وضع المريض','البداية → النهاية','الألم/تيبس','إضافة صف قياس'):self.assertIn(text,self.html)
  self.assertIn('for(let i=0;i<8;i++)addRow()',self.js)
 def test_no_invalid_total_or_numeric_conversion_of_one_plus(self):
  self.assertFalse(self.reg['instrument']['aggregate_across_muscles']);self.assertIsNone(self.reg['instrument']['total_score']);self.assertIn('لا يوجد مجموع نهائي',self.html);self.assertIn('لا يحوّل 1+ إلى «2»',self.html);self.assertNotIn('reduce((a,b)=>a+b',self.js)
 def test_rmd_and_eprovide_rights_are_precise(self):
  self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertEqual(self.reg['eprovide']['copyright'],'Public Domain');self.assertIn('public domain',self.reg['eprovide']['conditions_of_use'].lower());self.assertIn('Public Domain',self.html)
 def test_arabic_is_not_claimed_as_official_translation(self):
  self.assertFalse(self.reg['arabic']['validated_arabic_form_found_in_this_review']);self.assertFalse(self.reg['arabic']['claim_official_mapi_translation']);self.assertIn('صياغة عربية تشغيلية',self.html);self.assertIn('لا ندعي أنها ترجمة عربية معتمدة من Mapi',self.html)
 def test_scientific_limitations_are_visible(self):
  for text in ('MAS لا تقيس «التشنج» وحده بصورة نقية','الثبات داخل الفاحص غالبًا أفضل','لا توجد سرعة معيارية واحدة','Tardieu قد يضيف معلومات'):self.assertIn(text,self.html)
 def test_primary_and_methodology_references(self):self.assertEqual(self.reg['primary_reference']['pmid'],'3809245');self.assertEqual(self.reg['methodology_reference']['pmid'],'10498344')
if __name__=='__main__':unittest.main()
