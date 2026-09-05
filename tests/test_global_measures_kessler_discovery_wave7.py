from __future__ import annotations

import xml.etree.ElementTree as ET
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'
HUB=ROOT/'assessments'/'distress-screeners'/'index.html'
SITEMAP=ROOT/'sitemap-global-measures.xml'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}

class KesslerDiscoveryWave7Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_html=GLOBAL.read_text(encoding='utf-8');cls.hub=HUB.read_text(encoding='utf-8');cls.xml=SITEMAP.read_text(encoding='utf-8')

    def test_global_gateway_count_and_distress_route(self):
        self.assertIn('26 أداة/بطارية فعلية',cls:=self.global_html)
        self.assertIn('/assessments/distress-screeners/',cls)
        self.assertIn('Kessler K6 وK10',cls)

    def test_hub_links_both_tools_and_official_source(self):
        self.assertIn('/assessments/distress-screeners/k6/',self.hub)
        self.assertIn('/assessments/distress-screeners/k10/',self.hub)
        self.assertIn('rckessler.scholars.harvard.edu/k10-and-k6-scales',self.hub)

    def test_sitemap_discovers_distress_hub_and_tools_once(self):
        root=ET.fromstring(self.xml);urls=[el.text for el in root.findall('s:url/s:loc',NS)]
        for url in (
            'https://healthrenewal.org/assessments/distress-screeners/',
            'https://healthrenewal.org/assessments/distress-screeners/k6/',
            'https://healthrenewal.org/assessments/distress-screeners/k10/',
        ):
            self.assertEqual(urls.count(url),1)

if __name__=='__main__':unittest.main()
