from __future__ import annotations

import xml.etree.ElementTree as ET
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'
HUB=ROOT/'assessments'/'substance-use-screeners'/'index.html'
SITEMAP=ROOT/'sitemap-global-measures.xml'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}

class TapsDiscoveryWave9Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_html=GLOBAL.read_text(encoding='utf-8')
        cls.hub=HUB.read_text(encoding='utf-8')
        cls.xml=SITEMAP.read_text(encoding='utf-8')

    def test_global_gateway_count_and_taps_card(self):
        self.assertIn('28 أداة/بطارية فعلية',self.global_html)
        self.assertIn('/assessments/substance-use-screeners/',self.global_html)
        self.assertIn('NIDA TAPS',self.global_html)
        self.assertIn('لا يوجد مجموع إدمان كلي',self.global_html)

    def test_taps_hub_links_both_parts(self):
        self.assertIn('/assessments/substance-use-screeners/taps-1/',self.hub)
        self.assertIn('/assessments/substance-use-screeners/taps-2/',self.hub)
        self.assertIn('Public Domain',self.hub)

    def test_sitemap_discovers_taps_once(self):
        root=ET.fromstring(self.xml)
        urls=[el.text for el in root.findall('s:url/s:loc',NS)]
        for url in (
            'https://healthrenewal.org/assessments/substance-use-screeners/',
            'https://healthrenewal.org/assessments/substance-use-screeners/taps-1/',
            'https://healthrenewal.org/assessments/substance-use-screeners/taps-2/',
        ):
            self.assertEqual(urls.count(url),1)

    def test_addiction_alias_is_not_indexed(self):
        alias=ROOT/'sectors'/'addiction-recovery'/'index.html'
        if alias.exists():
            html=alias.read_text(encoding='utf-8')
            self.assertIn('noindex,follow',html)
            self.assertIn('/sectors/addiction/',html)

if __name__=='__main__':unittest.main()
