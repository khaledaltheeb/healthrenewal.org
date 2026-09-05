from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAY = ROOT / "sectors" / "rehabilitation" / "measures" / "stay-independent" / "index.html"
STAY_JS = STAY.with_name("stay-independent.js")
PDI = ROOT / "sectors" / "rehabilitation" / "measures" / "pdi" / "index.html"
PDI_JS = PDI.with_name("pdi.js")
REGISTRY = ROOT / "content" / "rehabilitation-measures-v1" / "questionnaires-wave3.json"
HUB_JS = ROOT / "sectors" / "rehabilitation" / "measures" / "app.js"
SITEMAP = ROOT / "sitemap-rehabilitation-measures.xml"


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.ids.append(value)


def assert_unique_ids(testcase: unittest.TestCase, html: str) -> None:
    parser = IdParser()
    parser.feed(html)
    dupes = {x for x in parser.ids if parser.ids.count(x) > 1}
    testcase.assertEqual(dupes, set())


class QuestionnairesWave3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stay = STAY.read_text(encoding="utf-8")
        cls.stay_js = STAY_JS.read_text(encoding="utf-8")
        cls.pdi = PDI.read_text(encoding="utf-8")
        cls.pdi_js = PDI_JS.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.hub_js = HUB_JS.read_text(encoding="utf-8")
        cls.sitemap = SITEMAP.read_text(encoding="utf-8")

    def test_pages_are_rtl_indexable_and_unique(self):
        for html in (self.stay, self.pdi):
            self.assertIn('<html lang="ar" dir="rtl">', html)
            self.assertIn('index,follow', html)
            assert_unique_ids(self, html)

    def test_stay_independent_has_exact_operational_structure(self):
        self.assertEqual(len(re.findall(r'class="form-row" data-weight=', self.stay)), 12)
        self.assertEqual(len(re.findall(r'data-weight="2"', self.stay)), 2)
        self.assertEqual(len(re.findall(r'data-weight="1"', self.stay)), 10)
        for n in range(1, 13):
            self.assertIn(f'name="si{n}"', self.stay)
        self.assertIn('4 فأكثر', self.stay)
        self.assertIn('صياغة تشغيلية عربية من روافد', self.stay)
        self.assertIn('ليست نسخًا حرفيًا', self.stay)

    def test_stay_runtime_requires_complete_form_and_preserves_cdc_rule(self):
        self.assertIn('answered===12', self.stay_js)
        self.assertIn("total>=4", self.stay_js)
        self.assertIn("key.fall===true", self.stay_js)
        self.assertIn("[key.fall,key.unsteady,key.worry].some(Boolean)", self.stay_js)
        self.assertIn('window.print()', self.stay_js)

    def test_pdi_has_seven_domains_and_no_fake_cutoff(self):
        self.assertEqual(len(re.findall(r'class="pdi-score"', self.pdi)), 7)
        for n in range(1, 8):
            self.assertIn(f'id="pdi{n}"', self.pdi)
        self.assertIn('0–70', self.pdi)
        self.assertIn('لا توجد نقاط قطع تجريبية معيارية متفق عليها', self.pdi)
        self.assertIn('صياغة تشغيلية عربية من روافد', self.pdi)
        self.assertNotIn('خفيف/متوسط/شديد تلقائي', self.pdi)

    def test_pdi_runtime_refuses_incomplete_total(self):
        self.assertIn('valid.length!==7', self.pdi_js)
        self.assertIn("values.filter", self.pdi_js)
        self.assertIn('valid.reduce((a,b)=>a+b,0)', self.pdi_js)
        self.assertIn('لا توجد نقطة قطع معيارية ثابتة', self.pdi_js)
        self.assertIn('window.print()', self.pdi_js)

    def test_registry_has_rights_and_arabic_evidence_separated(self):
        self.assertEqual({m['id'] for m in self.registry['measures']}, {'stay-independent', 'pdi'})
        stay = next(m for m in self.registry['measures'] if m['id'] == 'stay-independent')
        pdi = next(m for m in self.registry['measures'] if m['id'] == 'pdi')
        self.assertEqual(stay['rights']['source_status'], 'Public Domain')
        self.assertEqual(stay['scoring']['cdc_screen_threshold'], 4)
        self.assertEqual(stay['arabic_evidence']['test_retest_icc'], 0.96)
        self.assertTrue(pdi['rights']['source_status'].startswith('Public Domain'))
        self.assertEqual(pdi['scoring']['domains'], 7)
        self.assertFalse(pdi['scoring']['empirical_universal_cutoff'])
        self.assertEqual(pdi['arabic_evidence']['cronbach_alpha'], 0.91)

    def test_hub_and_sitemap_discover_both_pages(self):
        for route in (
            '/sectors/rehabilitation/measures/stay-independent/',
            '/sectors/rehabilitation/measures/pdi/',
        ):
            self.assertIn(route, self.hub_js)
            self.assertIn(f'https://healthrenewal.org{route}', self.sitemap)


if __name__ == '__main__':
    unittest.main()
