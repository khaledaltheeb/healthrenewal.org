from __future__ import annotations
import re, unittest, xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'; WORK=ROOT/'assessments'/'global-measures'/'workspace'/'index.html'; SITEMAP=ROOT/'sitemap-global-measures.xml'; NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
class WorkspaceDiscoveryWave10Test(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.global_html=GLOBAL.read_text(encoding='utf-8'); cls.work=WORK.read_text(encoding='utf-8'); cls.xml=SITEMAP.read_text(encoding='utf-8')
 def test_global_gateway_preserves_wave10_minimum_and_workspace_links(self):
  m=re.search(r'<strong>(\d+) أداة/بطارية فعلية حاليًا</strong>',self.global_html); self.assertIsNotNone(m); self.assertGreaterEqual(int(m.group(1)),28)
  for route in ('/assessments/global-measures/workspace/','/assessments/global-measures/tool-finder/','/assessments/global-measures/print-packets/','/assessments/global-measures/measurement-record/'): self.assertIn(route,self.global_html)
 def test_workspace_wires_runtime_components(self):
  for route in ('/assessments/global-measures/tool-finder/','/assessments/global-measures/print-packets/','/assessments/global-measures/measurement-record/','/sectors/rehabilitation/measures/#rights-sheet','/sectors/rehabilitation/measures/arabic-readiness/'): self.assertIn(route,self.work)
 def test_sitemap_discovers_workspace_pages_once(self):
  urls=[el.text for el in ET.fromstring(self.xml).findall('s:url/s:loc',NS)]
  for url in ('https://healthrenewal.org/assessments/global-measures/workspace/','https://healthrenewal.org/assessments/global-measures/tool-finder/','https://healthrenewal.org/assessments/global-measures/print-packets/','https://healthrenewal.org/assessments/global-measures/measurement-record/'): self.assertEqual(urls.count(url),1)
if __name__=='__main__': unittest.main()
