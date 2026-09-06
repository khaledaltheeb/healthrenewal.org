from __future__ import annotations
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'functional-ambulation-category'/'index.html';JS=PAGE.with_name('fac.js');REG=ROOT/'content'/'global-measures-v1'/'functional-ambulation-category.json'
class FunctionalAmbulationCategoryWave17Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'))
 def test_six_categories_single_choice(self):
  self.assertEqual(len(re.findall(r'name="fac"',self.html)),6)
  for g in range(6):self.assertIn(f'name="fac" value="{g}"',self.html);self.assertIn(f'<span class="fac-grade">{g}</span>',self.html)
 def test_ordinal_no_average_or_total(self):
  self.assertEqual(self.reg['instrument']['scale_type'],'ordinal');self.assertFalse(self.reg['instrument']['average_for_individual_interpretation']);self.assertIsNone(self.reg['instrument']['global_total_score']);self.assertNotIn('reduce(',self.js);self.assertIn('رتبي وليس فاصلًا',self.html)
 def test_human_assistance_is_primary_and_device_separate(self):
  self.assertTrue(self.reg['instrument']['human_assistance_is_primary_construct']);self.assertFalse(self.reg['instrument']['walking_aid_determines_category']);self.assertIn('المساعدة البشرية/الإشراف المطلوبان',self.html);self.assertIn('جهاز/دعامة المشي',self.html)
 def test_fac_below_three_not_testable_rule(self):
  self.assertIn('if(v<3)',self.js);self.assertIn('Not Testable',self.js);self.assertIn('FAC أقل من 3',self.html);self.assertIn('10MWT و6MWT وDGI',self.html);self.assertIn('بدل إعطائها صفرًا',self.html)
 def test_rights_are_operational_not_public_domain_claim(self):
  self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');self.assertIn('لم نتحقق من تصريح مالك واضح',self.html);self.assertIn('إعادة صياغة تشغيلية مستقلة من روافد',self.html)
 def test_arabic_not_overclaimed(self):
  self.assertFalse(self.reg['arabic']['validated_arabic_fac_form_identified_in_this_review']);self.assertFalse(self.reg['arabic']['claim_official_translation']);self.assertIn('لا ندعي أن هذه الصياغة نسخة عربية متحققة أو معتمدة',self.html)
if __name__=='__main__':unittest.main()
