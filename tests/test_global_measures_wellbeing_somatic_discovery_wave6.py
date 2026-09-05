from __future__ import annotations
import re, unittest, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'; HUB=ROOT/'assessments'/'wellbeing-somatic-screeners'/'index.html'; SITEMAP=ROOT/'sitemap-global-measures.xml'; NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class WellbeingSomaticDiscoveryWave6Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.global_html=GLOBAL.read_text(encoding='utf-8'); cls.hub=HUB.read_text(encoding='utf-8'); cls.xml=SITEMAP.read_text(encoding='utf-8')
 def test_global_gateway_preserves_wave6_minimum_and_path(self):
  m=re.search(r'<strong>(\d+) أداة/بطارية فعلية حاليًا</strong>',self.global_html); self.assertIsNotNone(m); self.assertGreaterEqual(int(m.group(1)),24)
  self.assertIn('/assessments/wellbeing-somatic-screeners/',self.global_html); self.assertIn('PHQ‑4 وPHQ‑15 وWHO‑5',self.global_html)
 def test_hub_links_all_three_tools(self):
  for route in ('/assessments/wellbeing-somatic-screeners/phq-4/','/assessments/wellbeing-somatic-screeners/phq-15/','/assessments/wellbeing-somatic-screeners/who-5/'): self.assertIn(route,self.hub)
 def test_global_sitemap_discovers_hub_and_tools_once(self):
  urls=[el.text for el in ET.fromstring(self.xml).findall('s:url/s:loc',NS)]
  for url in ('https://healthrenewal.org/assessments/wellbeing-somatic-screeners/','https://healthrenewal.org/assessments/wellbeing-somatic-screeners/phq-4/','https://healthrenewal.org/assessments/wellbeing-somatic-screeners/phq-15/','https://healthrenewal.org/assessments/wellbeing-somatic-screeners/who-5/'): self.assertEqual(urls.count(url),1)
 def test_who5_not_counted_as_who_endorsed_translation(self): self.assertIn('WHO‑5',self.global_html); self.assertNotIn('ترجمة WHO العربية الرسمية',self.global_html)
if __name__=='__main__': unittest.main()
