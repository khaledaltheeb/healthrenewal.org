from __future__ import annotations

import xml.etree.ElementTree as ET
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'
HUB=ROOT/'assessments'/'geriatric-measures'/'index.html'
SITEMAP=ROOT/'sitemap-global-measures.xml'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}

class GeriatricDiscoveryWave8Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_html=GLOBAL.read_text(encoding='utf-8');cls.hub=HUB.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8')

    def test_global_gateway_count_and_path(self):
        self.assertIn('27 أداة/بطارية فعلية',self.global_html)
        self.assertIn('/assessments/geriatric-measures/',self.global_html)
        self.assertIn('GDS‑15 + Mini‑Cog الرسمي',self.global_html)

    def test_hub_links_gds_and_official_minicog(self):
        self.assertIn('/assessments/geriatric-measures/gds-15/',self.hub)
        self.assertIn('ARABIC-Standardized-Mini-Cog-in-Arabic.pdf',self.hub)
        self.assertNotIn('/assessments/geriatric-measures/mini-cog/',self.hub)

    def test_sitemap_has_only_actual_geriatric_page_routes(self):
        root=ET.fromstring(self.xml);urls=[el.text for el in root.findall('s:url/s:loc',NS)]
        for url in ('https://healthrenewal.org/assessments/geriatric-measures/','https://healthrenewal.org/assessments/geriatric-measures/gds-15/'):
            self.assertEqual(urls.count(url),1)
        self.assertFalse(any('mini-cog' in (u or '') for u in urls))

if __name__=='__main__':unittest.main()
