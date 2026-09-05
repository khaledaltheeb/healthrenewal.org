from __future__ import annotations
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'modified-rankin-scale'/'index.html';JS=PAGE.with_name('mrs.js');REG=ROOT/'content'/'global-measures-v1'/'modified-rankin-scale.json'
class ModifiedRankinWave15Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'))
 def test_all_seven_grades_present_once(self):
  self.assertEqual(len(re.findall(r'name="mrs"',self.html)),7)
  for g in range(7):self.assertIn(f'name="mrs" value="{g}"',self.html);self.assertIn(f'<span class="mrs-grade">{g}</span>',self.html)
 def test_single_selection_and_score(self):self.assertIn("document.querySelector('input[name=\"mrs\"]:checked')",self.js);self.assertIn('/ 6',self.js);self.assertNotIn('reduce(',self.js)
 def test_ordinal_not_interval_and_no_universal_cutoff(self):self.assertEqual(self.reg['instrument']['scale_type'],'ordinal');self.assertFalse(self.reg['instrument']['global_cutoff']);self.assertFalse(self.reg['instrument']['mean_for_individual_longitudinal_interpretation']);self.assertIn('لا متوسط فردي',self.html);self.assertIn('لا cutoff عالمي',self.html)
 def test_context_fields_exist(self):
  for text in ('تاريخ السكتة/الحدث','نقطة القياس','mRS قبل السكتة','ما المعلومات التي استند إليها التصنيف؟'):self.assertIn(text,self.html)
 def test_rights_are_public_domain_original_not_structured_variant(self):self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertEqual(self.reg['eprovide']['copyright'],'Public Domain');self.assertTrue(self.reg['instrument']['structured_mrs_is_separate']);self.assertIn('Structured mRS ومقابلات التدريب أدوات توحيد منفصلة',self.html)
 def test_arabic_not_overclaimed(self):self.assertFalse(self.reg['arabic']['validated_arabic_translation_identified_in_this_review']);self.assertFalse(self.reg['arabic']['claim_structured_mrs']);self.assertFalse(self.reg['arabic']['claim_official_translation']);self.assertIn('صياغة تشغيلية عربية',self.html);self.assertIn('ليست «النسخة العربية المتحققة»',self.html)
 def test_method_reference(self):self.assertEqual(self.reg['methodology']['pmid'],'3363593')
if __name__=='__main__':unittest.main()
