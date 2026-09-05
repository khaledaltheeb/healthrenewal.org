from __future__ import annotations
import re, unittest, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'; HUB=ROOT/'assessments'/'geriatric-measures'/'index.html'; SITEMAP=ROOT/'sitemap-global-measures.xml'; NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class GeriatricDiscoveryWave8Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.global_html=GLOBAL.read_text(encoding='utf-8'); cls.hub=HUB.read_text(encoding='utf-8'); cls.xml=SITEMAP.read_text(encoding='utf-8')
 def test_global_gateway_preserves_wave8_minimum_and_path(self):
  m=re.search(r'<strong>(\d+) أداة/بطارية فعلية حاليًا</strong>',self.global_html); self.assertIsNotNone(m); self.assertGreaterEqual(int(m.group(1)),27)
  self.assertIn('/assessments/geriatric-measures/',self.global_html); self.assertIn('GDS‑15 وMini‑Cog',self.global_html)
 def test_hub_links_gds_and_official_minicog(self):
  self.assertIn('/assessments/geriatric-measures/gds-15/',self.hub); self.assertIn('ARABIC-Standardized-Mini-Cog-in-Arabic.pdf',self.hub); self.assertNotIn('/assessments/geriatric-measures/mini-cog/',self.hub)
 def test_sitemap_has_only_actual_geriatric_routes(self):
  urls=[el.text for el in ET.fromstring(self.xml).findall('s:url/s:loc',NS)]
  for url in ('https://healthrenewal.org/assessments/geriatric-measures/','https://healthrenewal.org/assessments/geriatric-measures/gds-15/'): self.assertEqual(urls.count(url),1)
  self.assertFalse(any('mini-cog' in (u or '') for u in urls))
if __name__=='__main__': unittest.main()
