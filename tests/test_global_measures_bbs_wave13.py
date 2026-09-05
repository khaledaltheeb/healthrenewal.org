from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'sectors'/'rehabilitation'/'measures'/'berg-balance-scale'/'index.html'
JS=PAGE.with_name('bbs.js')
REG=ROOT/'content'/'global-measures-v1'/'berg-balance-scale.json'
CAT=ROOT/'content'/'global-measures-v1'/'catalog.json'
AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json'
LIB_JS=ROOT/'sectors'/'rehabilitation'/'measures'/'app.js'
SITEMAP=ROOT/'sitemap-rehabilitation-measures.xml'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}

class BergBalanceScaleWave13Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.html=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.reg=json.loads(REG.read_text(encoding='utf-8'));cls.catalog=json.loads(CAT.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'));cls.lib_js=LIB_JS.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8')
 def test_fourteen_items_each_have_five_scores(self):
  for i in range(1,15):
   self.assertEqual(len(re.findall(fr'name="bbs{i}"',self.html)),5,f'item {i}')
   for score in range(5):self.assertIn(f'name="bbs{i}" value="{score}"',self.html)
 def test_scoring_is_complete_only_and_max_56(self):
  self.assertIn('done===14',self.js);self.assertIn("vals.reduce((a,b)=>a+b,0)",self.js);self.assertIn('— / 56',self.js);self.assertIn('لا يظهر مجموع نهائي قبل اكتمال جميع البنود',self.html)
 def test_rmd_rights_and_cost_are_precise(self):
  self.assertEqual(self.reg['rmd']['cost'],'Free');self.assertEqual(self.reg['rmd']['cost_description'],'Cost of equipment only');self.assertEqual(self.reg['rights']['instrument_status'],'public-domain');self.assertIn('RMD/NINDS CDE',self.reg['rights']['basis']);self.assertIn('Public Domain',self.html)
  row=next(x for x in self.audit['current_library'] if x['id']=='bbs');self.assertEqual(row['rmd_cost'],'Free');self.assertEqual(row['decision'],'full-ok');self.assertIn('equipment',row['rmd_cost_description'].lower());self.assertIn('public-domain',row['rights_source'].lower())
 def test_arabic_provenance_is_not_overclaimed(self):
  self.assertEqual(self.reg['arabic_evidence'][0]['pmid'],'26890426');self.assertEqual(self.reg['arabic_evidence'][0]['sample_n'],82);self.assertEqual(set(self.reg['arabic_evidence'][0]['countries']),{'Jordan','Saudi Arabia'});self.assertIn('لا ندعي أنها النص الحرفي',self.html);self.assertIn('operational-Arabic-rendering-not-claimed-identical',self.reg['rawafid_arabic_status'])
 def test_no_universal_cutoff_is_asserted(self):
  self.assertFalse(self.reg['instrument']['global_fall_cutoff']);self.assertIn('لا يوجد تفسير عالمي واحد',self.html);self.assertIn('لا تحول 45 أو 47',self.html)
 def test_safety_and_protocol_are_explicit(self):
  for text in ('السلامة قبل الدرجة','15–20 دقيقة','ساعة توقيت','كرسي بساندي ذراعين','أدنى فئة تنطبق'):self.assertIn(text,self.html)
 def test_catalog_and_library_navigation_include_bbs(self):
  self.assertEqual(self.catalog['actual_tool_count'],30);row=next(x for x in self.catalog['tools'] if x['id']=='bbs');self.assertEqual(row['route'],'/sectors/rehabilitation/measures/berg-balance-scale/');self.assertEqual(row['score'],'0-56');self.assertEqual(row['rights_state'],'rmd-free-public-domain-ninds')
  self.assertIn("bbs='/sectors/rehabilitation/measures/berg-balance-scale/'",self.lib_js);self.assertIn('BBS: مقياس بيرغ الكامل 0–56',self.lib_js)
 def test_sitemap_discovers_bbs_once(self):
  urls=[e.text for e in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/sectors/rehabilitation/measures/berg-balance-scale/'),1)
 def test_route_and_canonical(self):
  self.assertIn('https://healthrenewal.org/sectors/rehabilitation/measures/berg-balance-scale/',self.html);self.assertEqual(self.reg['rawafid_route'],'/sectors/rehabilitation/measures/berg-balance-scale/')
if __name__=='__main__':unittest.main()
