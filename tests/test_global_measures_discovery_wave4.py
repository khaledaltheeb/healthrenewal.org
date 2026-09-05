from __future__ import annotations

import xml.etree.ElementTree as ET
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = ROOT / "assessments" / "global-measures" / "index.html"
MENTAL = ROOT / "assessments" / "mental-health-screeners" / "index.html"
SITEMAP_GLOBAL = ROOT / "sitemap-global-measures.xml"
SITEMAP_REHAB = ROOT / "sitemap-rehabilitation-measures.xml"
SITEMAP_INDEX = ROOT / "sitemap-index.xml"

NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class GlobalMeasuresDiscoveryWave4Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_html = GLOBAL.read_text(encoding="utf-8")
        cls.mental_html = MENTAL.read_text(encoding="utf-8")
        cls.global_xml = SITEMAP_GLOBAL.read_text(encoding="utf-8")
        cls.rehab_xml = SITEMAP_REHAB.read_text(encoding="utf-8")
        cls.index_xml = SITEMAP_INDEX.read_text(encoding="utf-8")

    def test_global_gateway_reports_current_actual_tool_count(self):
        self.assertIn('19 أداة/بطارية فعلية', self.global_html)
        self.assertIn('/assessments/mental-health-screeners/', self.global_html)
        self.assertIn('PHQ‑9 وGAD‑7', self.global_html)

    def test_mental_health_hub_links_both_full_tools(self):
        self.assertIn('/assessments/mental-health-screeners/phq-9/', self.mental_html)
        self.assertIn('/assessments/mental-health-screeners/gad-7/', self.mental_html)
        self.assertIn('الفحص ≠ التشخيص', self.mental_html)

    def test_global_sitemap_is_valid_and_complete(self):
        root = ET.fromstring(self.global_xml)
        urls = {el.text for el in root.findall('s:url/s:loc', NS)}
        expected = {
            'https://healthrenewal.org/assessments/global-measures/',
            'https://healthrenewal.org/assessments/mental-health-screeners/',
            'https://healthrenewal.org/assessments/mental-health-screeners/phq-9/',
            'https://healthrenewal.org/assessments/mental-health-screeners/gad-7/',
        }
        self.assertEqual(urls, expected)

    def test_global_gateway_is_not_duplicated_in_rehab_sitemap(self):
        self.assertNotIn('https://healthrenewal.org/assessments/global-measures/', self.rehab_xml)
        self.assertIn('https://healthrenewal.org/sectors/rehabilitation/measures/', self.rehab_xml)

    def test_sitemap_index_registers_global_measures_once(self):
        self.assertEqual(self.index_xml.count('https://healthrenewal.org/sitemap-global-measures.xml'), 1)


if __name__ == '__main__':
    unittest.main()
