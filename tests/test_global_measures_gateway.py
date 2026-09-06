from __future__ import annotations
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PAGE=ROOT/'assessments'/'global-measures'/'index.html';SITEMAP=ROOT/'sitemap-global-measures.xml';CATALOG=ROOT/'content'/'global-measures-v1'/'catalog.json';AUDIT=ROOT/'content'/'global-measures-v1'/'rmd-eprovide-rights-audit.json'
ROUTES=('/sectors/rehabilitation/measures/','/sectors/rehabilitation/measures/berg-balance-scale/','/sectors/rehabilitation/measures/modified-ashworth-scale/','/sectors/rehabilitation/measures/modified-tardieu-scale/','/sectors/rehabilitation/measures/modified-rankin-scale/','/assessments/mental-health-screeners/','/assessments/trauma-measures/','/assessments/wellbeing-somatic-screeners/','/assessments/distress-screeners/','/assessments/geriatric-measures/','/assessments/substance-use-screeners/','/assessments/general-health-measures/','/assessments/global-measures/workspace/','/assessments/global-measures/tool-finder/','/assessments/global-measures/print-packets/','/assessments/global-measures/measurement-record/')
class GlobalMeasuresGatewayTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.html=PAGE.read_text(encoding='utf-8');cls.sitemap=SITEMAP.read_text(encoding='utf-8');cls.catalog=json.loads(CATALOG.read_text(encoding='utf-8'));cls.audit=json.loads(AUDIT.read_text(encoding='utf-8'))
 def test_identity_and_metadata(self):self.assertIn('المقاييس وأدوات التقييم المستخدمة عالميًا',self.html);self.assertIn('rel="canonical" href="https://healthrenewal.org/assessments/global-measures/"',self.html);self.assertIn('name="robots" content="index,follow',self.html);self.assertEqual(self.html.count('<h1>'),1)
 def test_all_current_core_routes_are_linked(self):
  for route in ROUTES:self.assertIn(f'href="{route}"',self.html,route)
 def test_gateway_count_matches_machine_catalog(self):
  m=re.search(r'<strong>(\d+) أداة/بطارية فعلية حاليًا</strong>',self.html);self.assertIsNotNone(m);self.assertEqual(int(m.group(1)),self.catalog['actual_tool_count']);self.assertEqual(self.catalog['actual_tool_count'],33);self.assertEqual(len(self.catalog['tools']),33);self.assertIn('Berg Balance Scale',self.html);self.assertIn('Modified Ashworth Scale',self.html);self.assertIn('Modified Tardieu Scale',self.html);self.assertIn('Modified Rankin Scale',self.html);self.assertIn('21 أداة/بطارية',self.html)
 def test_rmd_rights_model_is_explicit(self):
  self.assertIn('RMD لا يملك الأدوات',self.html);self.assertIn('Cost + Cost Description',self.html);self.assertIn('Free لا تعني Public Domain',self.html);self.assertIn('operational-sheet-only',self.html);self.assertIn('rule_2',self.audit['method']);self.assertIn('Free does not mean Public Domain',self.audit['method']['rule_2'])
  mts=next(x for x in self.audit['current_library'] if x['id']=='mts');self.assertEqual(mts['decision'],'operational-sheet-only');self.assertEqual(mts['rmd_cost'],'Free');self.assertIn('no sufficiently authoritative explicit Public Domain',mts['rights_source']);self.assertIn('no validated or official Arabic MTS',mts['arabic_state'])
 def test_owner_controlled_and_unresolved_examples_are_conservative(self):
  decisions={x['id']:x['decision'] for x in self.audit['priority_candidates']}
  for key in ('odi','ndi','quickdash','eq5d5l','isi','zbi','fma'):self.assertEqual(decisions[key],'official-link-only')
  self.assertEqual(decisions['rmdq24'],'hold-exact-arabic');self.assertEqual(decisions['fac'],'hold-rights')
 def test_gateway_is_discoverable(self):self.assertEqual(self.sitemap.count('https://healthrenewal.org/assessments/global-measures/'),1)
if __name__=='__main__':unittest.main()
