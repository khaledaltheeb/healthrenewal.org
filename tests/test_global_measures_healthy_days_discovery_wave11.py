from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
GLOBAL=ROOT/'assessments'/'global-measures'/'index.html'
HUB=ROOT/'assessments'/'general-health-measures'/'index.html'
CAT=ROOT/'content'/'global-measures-v1'/'catalog.json'
SITEMAP=ROOT/'sitemap-global-measures.xml'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}

class HealthyDaysDiscoveryWave11Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g=GLOBAL.read_text(encoding='utf-8')
        cls.h=HUB.read_text(encoding='utf-8')
        cls.cat=json.loads(CAT.read_text(encoding='utf-8'))
        cls.x=SITEMAP.read_text(encoding='utf-8')

    def test_current_count_is_29(self):
        self.assertIn('29 أداة/بطارية فعلية حاليًا',self.g)
        self.assertEqual(self.cat['actual_tool_count'],29)
        self.assertEqual(len(self.cat['tools']),29)

    def test_healthy_days_is_actual_unique_catalog_entry(self):
        rows=[x for x in self.cat['tools'] if x['id']=='healthy-days']
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertTrue(row['actual']);self.assertTrue(row['printable'])
        self.assertEqual(row['route'],'/assessments/general-health-measures/healthy-days/')
        self.assertIn('general-health',row['domain'])
        self.assertIn('health-related-quality-of-life',row['domain'])

    def test_gateway_and_hub_link_tool(self):
        self.assertIn('/assessments/general-health-measures/',self.g)
        self.assertIn('/assessments/general-health-measures/healthy-days/',self.g)
        self.assertIn('/assessments/general-health-measures/healthy-days/',self.h)

    def test_sitemap_discovers_general_health_once(self):
        urls=[e.text for e in ET.fromstring(self.x).findall('s:url/s:loc',NS)]
        for url in ('https://healthrenewal.org/assessments/general-health-measures/','https://healthrenewal.org/assessments/general-health-measures/healthy-days/'):
            self.assertEqual(urls.count(url),1)

if __name__=='__main__':unittest.main()
