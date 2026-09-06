from __future__ import annotations
import json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'box-and-block-test'/'index.html';JS=PAGE.with_name('bbt.js');REG=ROOT/'content'/'global-measures-v1'/'box-and-block-test.json';CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json';LIB=ROOT/'sectors'/'rehabilitation'/'measures'/'app.js';SITEMAP=ROOT/'sitemap-rehabilitation-measures.xml';PACKETS=ROOT/'assessments'/'global-measures'/'print-packets'/'index.html';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class BoxAndBlockWave18Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.catalog=json.loads(CAT.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'));cls.lib=LIB.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8');cls.packets=PACKETS.read_text(encoding='utf-8')
 def test_core_protocol(self):
  for text in ('60 ثانية','53.7 × 25.4 × 8.5','150 مكعب','2.5 سم','اليد اليمنى','اليد اليسرى'):self.assertIn(text,self.html)
  self.assertEqual(self.reg['instrument']['fixed_duration_seconds'],60);self.assertEqual(self.reg['apparatus']['blocks_count'],150);self.assertEqual(self.reg['apparatus']['block_size_cm'],2.5)
 def test_each_hand_is_separate_and_no_bilateral_total(self):
  self.assertFalse(self.reg['instrument']['aggregate_across_hands']);self.assertTrue(self.reg['scoring']['hand_specific']);self.assertTrue(self.reg['scoring']['do_not_sum_right_and_left']);self.assertNotIn('reduce(',self.js);self.assertIn('لا تجمع نتيجة اليد اليمنى واليسرى',self.html)
 def test_runtime_validates_range_and_qc(self):
  self.assertIn('v>150',self.js);self.assertIn('done===4',self.js);self.assertIn('مكعب/دقيقة',self.js);self.assertIn('${done}/4 من عناصر الاتساق',self.js)
 def test_rights_model_separates_equipment_cost_from_copyright(self):
  self.assertEqual(self.reg['rmd']['cost'],'Not Free');self.assertIn('equipment cost',self.reg['rmd']['cost_description']);self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');self.assertIn('هذا لا يساوي تلقائيًا قيد Copyright',self.html)
 def test_measurement_guardrails(self):
  self.assertIn('MDC يقارب 5.5',self.html);self.assertIn('تغيير سطح المكعبات',self.html);self.assertIn('ليس اختبار دقة أصابع',self.html);self.assertEqual(self.reg['measurement_properties']['stroke_mdc_blocks_per_minute'],5.5)
 def test_arabic_not_overclaimed(self):
  self.assertFalse(self.reg['arabic']['validated_arabic_form_identified_in_this_review']);self.assertFalse(self.reg['arabic']['claim_official_translation']);self.assertIn('لا تدعي وجود «نسخة عربية رسمية»',self.html)
 def test_wave18_minimum_and_bbt_integration_are_preserved(self):
  self.assertGreaterEqual(self.catalog['actual_tool_count'],35);self.assertGreaterEqual(len(self.catalog['tools']),35);row=next(x for x in self.catalog['tools'] if x['id']=='bbt');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/box-and-block-test/');self.assertEqual(row['rights_state'],'rmd-not-free-equipment-operational-sheet-rights-not-public-domain-verified');rights=next(x for x in self.audit['current_library'] if x['id']=='bbt');self.assertEqual(rights['decision'],'operational-sheet-only');self.assertEqual(rights['rmd_cost'],'Not Free');urls=[e.text for e in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/sectors/rehabilitation/measures/box-and-block-test/'),1)
if __name__=='__main__':unittest.main()
