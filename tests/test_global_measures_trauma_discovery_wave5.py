from __future__ import annotations
import re, unittest, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'; TRAUMA=ROOT/'assessments'/'trauma-measures'/'index.html'; MENTAL=ROOT/'assessments'/'mental-health-screeners'/'index.html'; SITEMAP=ROOT/'sitemap-global-measures.xml'; NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class TraumaDiscoveryWave5Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.global_html=GLOBAL.read_text(encoding='utf-8'); cls.trauma_html=TRAUMA.read_text(encoding='utf-8'); cls.mental_html=MENTAL.read_text(encoding='utf-8'); cls.xml=SITEMAP.read_text(encoding='utf-8')
 def test_gateway_preserves_wave5_minimum_and_routes(self):
  m=re.search(r'<strong>(\d+) أداة/بطارية فعلية حاليًا</strong>',self.global_html); self.assertIsNotNone(m); self.assertGreaterEqual(int(m.group(1)),21)
  self.assertIn('/assessments/trauma-measures/',self.global_html); self.assertIn('PC‑PTSD‑5 وPCL‑5',self.global_html); self.assertIn('Official Link Only',self.global_html)
 def test_trauma_hub_is_professional_not_self_diagnosis(self):
  self.assertIn('Professional / research use',self.trauma_html); self.assertIn('المختصين الصحيين المؤهلين والباحثين',self.trauma_html); self.assertIn('/assessments/trauma-measures/pc-ptsd-5/',self.trauma_html); self.assertIn('/assessments/trauma-measures/pcl-5/',self.trauma_html)
 def test_global_sitemap_has_trauma_routes_once(self):
  urls=[el.text for el in ET.fromstring(self.xml).findall('s:url/s:loc',NS)]
  for url in ('https://healthrenewal.org/assessments/trauma-measures/','https://healthrenewal.org/assessments/trauma-measures/pc-ptsd-5/','https://healthrenewal.org/assessments/trauma-measures/pcl-5/'): self.assertEqual(urls.count(url),1)
 def test_no_public_dass_route_is_discovered(self):
  self.assertNotIn('/assessments/mental-health-screeners/dass-21/',self.xml); self.assertNotIn('/assessments/mental-health-screeners/dass-21/',self.mental_html); self.assertIn('https://dass.psy.unsw.edu.au/Arabic/Arabic.htm',self.mental_html)
if __name__=='__main__': unittest.main()
