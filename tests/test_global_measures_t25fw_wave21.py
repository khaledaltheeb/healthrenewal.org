from __future__ import annotations
import json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'timed-25-foot-walk'/'index.html';JS=PAGE.with_name('t25fw.js');REG=ROOT/'content'/'global-measures-v1'/'timed-25-foot-walk.json';CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json';LIB=ROOT/'sectors'/'rehabilitation'/'measures'/'app.js';REHAB=ROOT/'sitemap-rehabilitation-measures.xml';GLOBAL=ROOT/'sitemap-global-measures.xml';PACKET=ROOT/'assessments'/'global-measures'/'print-packets'/'multiple-sclerosis-performance'/'index.html';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class Timed25FootWalkWave21Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.cat=json.loads(CAT.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'));cls.lib=LIB.read_text(encoding='utf-8');cls.rehab=REHAB.read_text(encoding='utf-8');cls.global_map=GLOBAL.read_text(encoding='utf-8');cls.packet=PACKET.read_text(encoding='utf-8')
 def test_core_rmd_protocol(self):
  self.assertEqual(self.reg['instrument']['course_feet'],25);self.assertEqual(self.reg['instrument']['course_meters'],7.62);self.assertEqual(self.reg['instrument']['trials'],2);self.assertEqual(self.reg['instrument']['score'],'mean seconds of two valid trials');self.assertTrue(self.reg['instrument']['assistive_device_allowed']);self.assertIn('25 قدمًا (7.62 م)',self.html);self.assertIn('متوسط الزمنين الصالحين',self.html)
 def test_standard_score_requires_two_valid_trials_and_standard_distance(self):
  for text in ("course==='25'","s1==='قابل للاختبار'","s2==='قابل للاختبار'","t1!==null&&t2!==null","const mean=(t1+t2)/2"):self.assertIn(text,self.js)
  self.assertIn('لا توجد درجة معيارية',self.js);self.assertIn('عدم القدرة على الإكمال',self.html);self.assertIn('لا يتحول إلى 0 ثانية',self.html)
 def test_msfc_context_is_not_overclaimed(self):
  self.assertTrue(self.reg['msfc_context']['component_of_msfc']);self.assertTrue(self.reg['msfc_context']['do_not_compute_msfc_z_score_without_reference_population_and_full_protocol']);self.assertIn('T25FW مكوّن واحد',self.html);self.assertIn('لا تحوّل متوسط T25FW مباشرة إلى «درجة MSFC»',self.html);self.assertIn('لا تسمِّ هذه الحزمة MSFC كاملًا',self.packet);self.assertIn('لا تحسب Z-score أو Composite',self.packet)
 def test_rights_and_arabic_are_conservative(self):
  self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');self.assertFalse(self.reg['arabic']['claim_official_translation']);row=next(x for x in self.audit['current_library'] if x['id']=='t25fw');self.assertEqual(row['decision'],'operational-sheet-only');self.assertEqual(row['rmd_cost'],'Free');self.assertIn('MSFC record form',row['copyright_state'])
 def test_reference_values_are_context_not_cutoffs(self):
  self.assertTrue(self.reg['scoring']['no_universal_cutoff']);self.assertTrue(self.reg['scoring']['change_thresholds_population_specific']);self.assertEqual(self.reg['measurement_properties']['rmd_ms_median_seconds'],4.4);self.assertEqual(self.reg['measurement_properties']['rmd_ms_interrater_icc'],0.942);self.assertIn('للسياق لا للتشخيص',self.html)
 def test_tool_38_integration(self):
  self.assertEqual(self.cat['actual_tool_count'],38);self.assertEqual(len(self.cat['tools']),38);row=next(x for x in self.cat['tools'] if x['id']=='t25fw');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/timed-25-foot-walk/');self.assertEqual(row['rights_state'],'rmd-free-operational-sheet-msfc-manual-not-reproduced');self.assertIn("t25='/sectors/rehabilitation/measures/timed-25-foot-walk/'",self.lib);rurls=[e.text for e in ET.fromstring(self.rehab).findall('s:url/s:loc',NS)];self.assertEqual(rurls.count('https://healthrenewal.org/sectors/rehabilitation/measures/timed-25-foot-walk/'),1);gurls=[e.text for e in ET.fromstring(self.global_map).findall('s:url/s:loc',NS)];self.assertEqual(gurls.count('https://healthrenewal.org/assessments/global-measures/print-packets/multiple-sclerosis-performance/'),1)
 def test_ms_packet_separates_components(self):
  for text in ('T25FW','9HPT','ليس MSFC الكامل','لا تخلط T25FW مع 10MWT','لا تخلط BBT و9HPT'):self.assertIn(text,self.packet)
if __name__=='__main__':unittest.main()
