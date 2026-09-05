from __future__ import annotations
import json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LEDGER=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json';CATALOG=ROOT/'content'/'global-measures-v1'/'catalog.json';PAGE=ROOT/'assessments'/'global-measures'/'rights-audit'/'index.html';JS=PAGE.with_name('audit.js');SITEMAP=ROOT/'sitemap-global-measures.xml';PHQ=ROOT/'assessments'/'mental-health-screeners'/'phq-9'/'index.html';GAD=ROOT/'assessments'/'mental-health-screeners'/'gad-7'/'index.html';NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class RmdEprovideRightsAuditWave12Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.ledger=json.loads(LEDGER.read_text(encoding='utf-8'));cls.catalog=json.loads(CATALOG.read_text(encoding='utf-8'));cls.page=PAGE.read_text(encoding='utf-8');cls.js=JS.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8');cls.phq=PHQ.read_text(encoding='utf-8');cls.gad=GAD.read_text(encoding='utf-8')
 def test_method_comes_from_rmd_cost_then_rights_source(self):
  m=self.ledger['method'];self.assertIn('RMD instrument summary',m['rule_1']);self.assertIn('Free does not mean Public Domain',m['rule_2']);self.assertIn('Mapi Research Trust/ePROVIDE',m['rule_3']);self.assertIn('three separate gates',m['rule_4'])
 def test_grip_proves_cost_is_not_copyright(self):
  row=next(x for x in self.ledger['current_library'] if x['id']=='grip');self.assertEqual(row['rmd_cost'],'Not Free');self.assertIn('Dynamometer',row['rmd_cost_description']);self.assertIn('equipment cost',row['copyright_state']);self.assertEqual(row['decision'],'operational-sheet-only')
 def test_phq_gad_copyright_and_permission_are_separate(self):
  for key in ('phq9','gad7'):
   row=next(x for x in self.catalog['tools'] if x['id']==key);self.assertEqual(row['rights_state'],'pfizer-copyright-permission-not-required')
  for html in (self.phq,self.gad):self.assertIn('© Pfizer',html);self.assertNotIn('Public domain',html);self.assertIn('لا يلزم إذن',html)
 def test_rmdq_is_not_retranslated_or_released_early(self):
  row=next(x for x in self.ledger['priority_candidates'] if x['id']=='rmdq24');self.assertEqual(row['decision'],'hold-exact-arabic');self.assertIn('public domain',row['rights_state']);self.assertIn('exact validated MSA',row['next_action']);self.assertNotIn('rmdq24',{x['id'] for x in self.catalog['tools']})
 def test_owner_controlled_priority_tools_cannot_be_full(self):
  rows={x['id']:x for x in self.ledger['priority_candidates']}
  for key in ('odi','ndi','quickdash','eq5d5l','isi','zbi'):self.assertEqual(rows[key]['decision'],'official-link-only');self.assertNotIn(rows[key]['decision'],('full-ok','full-ok-with-attribution'))
 def test_wave12_minimum_is_preserved_as_catalog_grows(self):
  self.assertGreaterEqual(self.catalog['actual_tool_count'],29);self.assertGreaterEqual(len(self.catalog['tools']),29);self.assertEqual(len({x['id'] for x in self.catalog['tools']}),len(self.catalog['tools']));self.assertIn('healthy-days',{x['id'] for x in self.catalog['tools']})
 def test_audit_page_uses_single_ledger(self):self.assertIn('/content/global-measures-v1/rmd-eprovide-rights-audit.json',self.js);self.assertIn('RMD Cost ≠ reproduction rights',self.page);self.assertIn('RMDQ‑24 حالة خاصة',self.page);self.assertIn('OPERATIONAL SHEET',self.page);self.assertNotIn('localStorage',self.js)
 def test_sitemap_discovers_audit_once(self):
  urls=[el.text for el in ET.fromstring(self.xml).findall('s:url/s:loc',NS)];self.assertEqual(urls.count('https://healthrenewal.org/assessments/global-measures/rights-audit/'),1)
if __name__=='__main__':unittest.main()
