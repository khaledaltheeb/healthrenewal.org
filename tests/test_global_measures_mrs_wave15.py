from __future__ import annotations
import json,re,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'modified-rankin-scale'/'index.html';JS=PAGE.with_name('mrs.js');REG=ROOT/'content'/'global-measures-v1'/'modified-rankin-scale.json';CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json';LIB_JS=ROOT/'sectors'/'rehabilitation'/'measures'/'app.js';SITEMAP=ROOT/'sitemap-rehabilitation-measures.xml';PACKETS=ROOT/'assessments'/'global-measures'/'print-packets'/'index.html';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class ModifiedRankinWave15Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.catalog=json.loads(CAT.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'));cls.lib_js=LIB_JS.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8');cls.packets=PACKETS.read_text(encoding='utf-8')
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
 def test_catalog_and_rights_ledger_register_mrs_as_tool_32(self):
  self.assertEqual(self.catalog['actual_tool_count'],32);self.assertEqual(len(self.catalog['tools']),32);row=next(x for x in self.catalog['tools'] if x['id']=='mrs');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/modified-rankin-scale/');self.assertEqual(row['rights_state'],'rmd-free-eprovide-public-domain-original-scale');rights=next(x for x in self.audit['current_library'] if x['id']=='mrs');self.assertEqual(rights['decision'],'full-ok');self.assertEqual(rights['rmd_cost'],'Free');self.assertIn('Public Domain',rights['rights_source'])
 def test_library_packet_and_sitemap_discover_mrs(self):
  self.assertIn("mrs='/sectors/rehabilitation/measures/modified-rankin-scale/'",self.lib_js);self.assertIn('mRS: الإعاقة والاعتماد الوظيفي 0–6 بعد السكتة',self.lib_js);self.assertIn('حزمة نتائج السكتة والمتابعة الوظيفية',self.packets);self.assertIn('/sectors/rehabilitation/measures/modified-rankin-scale/',self.packets);urls=[e.text for e in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/sectors/rehabilitation/measures/modified-rankin-scale/'),1)
if __name__=='__main__':unittest.main()
