from __future__ import annotations
import re, unittest, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'; HUB=ROOT/'assessments'/'distress-screeners'/'index.html'; SITEMAP=ROOT/'sitemap-global-measures.xml'; NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class KesslerDiscoveryWave7Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.global_html=GLOBAL.read_text(encoding='utf-8'); cls.hub=HUB.read_text(encoding='utf-8'); cls.xml=SITEMAP.read_text(encoding='utf-8')
 def test_global_gateway_preserves_wave7_minimum_and_route(self):
  m=re.search(r'<strong>(\d+) أداة/بطارية فعلية حاليًا</strong>',self.global_html); self.assertIsNotNone(m); self.assertGreaterEqual(int(m.group(1)),26)
  self.assertIn('/assessments/distress-screeners/',self.global_html); self.assertIn('K6 وK10',self.global_html)
 def test_hub_links_both_tools_and_official_source(self):
  self.assertIn('/assessments/distress-screeners/k6/',self.hub); self.assertIn('/assessments/distress-screeners/k10/',self.hub); self.assertIn('rckessler.scholars.harvard.edu/k10-and-k6-scales',self.hub)
 def test_sitemap_discovers_distress_hub_and_tools_once(self):
  urls=[el.text for el in ET.fromstring(self.xml).findall('s:url/s:loc',NS)]
  for url in ('https://healthrenewal.org/assessments/distress-screeners/','https://healthrenewal.org/assessments/distress-screeners/k6/','https://healthrenewal.org/assessments/distress-screeners/k10/'): self.assertEqual(urls.count(url),1)
if __name__=='__main__': unittest.main()
