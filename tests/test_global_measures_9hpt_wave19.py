from __future__ import annotations
import json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'nine-hole-peg-test'/'index.html';JS=PAGE.with_name('9hpt.js');REG=ROOT/'content'/'global-measures-v1'/'nine-hole-peg-test.json';CAT=ROOT/'content'/'global-measures-v1'/'catalog.json';SITEMAP=ROOT/'sitemap-rehabilitation-measures.xml';GATE=ROOT/'assessments'/'global-measures'/'index.html';WORK=ROOT/'assessments'/'global-measures'/'workspace'/'index.html';FINDER=ROOT/'assessments'/'global-measures'/'tool-finder'/'index.html';PACKET=ROOT/'assessments'/'global-measures'/'print-packets'/'upper-limb-dexterity'/'index.html';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class NineHolePegWave19Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.catalog=json.loads(CAT.read_text(encoding='utf-8'));cls.xml=SITEMAP.read_text(encoding='utf-8');cls.gate=GATE.read_text(encoding='utf-8');cls.work=WORK.read_text(encoding='utf-8');cls.finder=FINDER.read_text(encoding='utf-8');cls.packet=PACKET.read_text(encoding='utf-8')
 def test_core_standardized_task(self):
  self.assertEqual(self.reg['apparatus']['holes'],9);self.assertEqual(self.reg['apparatus']['pegs'],9);self.assertEqual(self.reg['apparatus']['peg_diameter_mm'],7);self.assertEqual(self.reg['apparatus']['peg_length_mm'],32);self.assertIn('بدأ المؤقت عند لمس أول وتد',self.html)
 def test_each_hand_stays_separate(self):
  self.assertFalse(self.reg['instrument']['aggregate_across_hands']);self.assertTrue(self.reg['instrument']['hands_scored_separately']);self.assertIn('اليد اليمنى',self.html);self.assertIn('اليد اليسرى',self.html);self.assertNotIn('right+left',self.js.lower())
 def test_runtime_and_qc(self):
  for text in ('Math.min(...trials)','done===5','أفضل زمن','المتوسط'):self.assertIn(text,self.js)
  for text in ('نفس اللوح','حاوية الأوتاد','بدأ المؤقت','محاولات التدريب'):self.assertIn(text,self.html)
 def test_rights_and_arabic_are_conservative(self):
  self.assertEqual(self.reg['rmd']['cost'],'Not Free');self.assertFalse(self.reg['rights']['instrument_public_domain_verified']);self.assertEqual(self.reg['rights']['rawafid_decision'],'operational-sheet-only');self.assertFalse(self.reg['arabic']['validated_or_official_arabic_form_identified_in_this_review']);self.assertFalse(self.reg['arabic']['claim_official_translation']);self.assertIn('ليس حكم copyright',self.html)
 def test_measurement_guardrails(self):
  self.assertTrue(self.reg['measurement']['practice_effect_warning']);self.assertTrue(self.reg['measurement']['population_specific_norms']);self.assertTrue(self.reg['measurement']['do_not_apply_one_global_cutoff']);self.assertTrue(self.reg['measurement']['do_not_convert_noncompletion_to_zero_unless_protocol_study_explicitly_requires_it']);self.assertIn('عدم الإكمال ليس صفرًا تلقائيًا',self.html)
 def test_tool_36_catalog_and_discovery(self):
  self.assertEqual(self.catalog['actual_tool_count'],36);self.assertEqual(len(self.catalog['tools']),36);row=next(x for x in self.catalog['tools'] if x['id']=='9hpt');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/nine-hole-peg-test/');self.assertEqual(row['rights_state'],'rmd-not-free-equipment-operational-sheet-rights-not-public-domain-verified');self.assertIn('36 أداة/بطارية فعلية حاليًا',self.gate);self.assertIn('36 أداة/بطارية فعلية',self.work);self.assertIn('36 actual tools',self.finder);urls=[e.text for e in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/sectors/rehabilitation/measures/nine-hole-peg-test/'),1)
 def test_upper_limb_packet_separates_constructs(self):
  for text in ('Grip Strength','BBT','9HPT','PSFS','لا تجمع Grip + BBT + 9HPT + PSFS','لا تستخدم BBT بدل 9HPT'):self.assertIn(text,self.packet)
if __name__=='__main__':unittest.main()
