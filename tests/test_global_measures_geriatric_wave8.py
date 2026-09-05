from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HUB=ROOT/'assessments'/'geriatric-measures'/'index.html'
GDS=ROOT/'assessments'/'geriatric-measures'/'gds-15'/'index.html'
GDS_JS=GDS.with_name('gds15.js')
REGISTRY=ROOT/'content'/'global-measures-v1'/'geriatric-mood-cognition.json'

class IdParser(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.ids=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k=='id' and v:self.ids.append(v)

def unique(testcase,html):
    p=IdParser();p.feed(html);testcase.assertEqual({x for x in p.ids if p.ids.count(x)>1},set())

class GeriatricWave8Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub=HUB.read_text(encoding='utf-8');cls.gds=GDS.read_text(encoding='utf-8');cls.gds_js=GDS_JS.read_text(encoding='utf-8');cls.registry=json.loads(REGISTRY.read_text(encoding='utf-8'))

    def test_pages_rtl_indexable_unique(self):
        for html in (self.hub,self.gds):self.assertIn('<html lang="ar" dir="rtl">',html);self.assertIn('index,follow',html);unique(self,html)

    def test_gds_has_15_yes_no_items_and_explicit_scoring_key(self):
        for n in range(1,16):self.assertEqual(len(re.findall(fr'name="g{n}"',self.gds)),2)
        self.assertEqual(self.gds.count('data-depression-answer='),15)
        self.assertIn('answered<15',self.gds_js)
        self.assertIn('v===row.dataset.depressionAnswer',self.gds_js)
        self.assertIn('/ 15',self.gds_js)

    def test_gds_keeps_two_threshold_references_separate(self):
        self.assertIn('total>5',self.gds_js)
        self.assertIn('total>=8',self.gds_js)
        self.assertIn('لا يثبت ذلك تشخيصًا',self.gds_js)
        self.assertIn('7/8',self.gds)
        self.assertIn('أكثر من 5',self.gds)

    def test_rights_registry_distinguishes_full_vs_official_link(self):
        records={x['id']:x for x in self.registry['measures']}
        self.assertEqual(records['gds-15']['rights']['status'],'public-domain')
        self.assertFalse(records['gds-15']['diagnostic_by_score_alone'])
        self.assertFalse(records['gds-15']['cognitive_screen'])
        self.assertFalse(records['mini-cog']['rawafid_public_form'])
        self.assertFalse(records['mini-cog']['rights']['modification_without_permission'])
        self.assertEqual(records['mini-cog']['rawafid_action'],'official-Arabic-form-link-only-no-modified-copy')

    def test_mini_cog_official_arabic_link_only_in_hub(self):
        self.assertIn('Official Arabic Form · Professional Use',self.hub)
        self.assertIn('ARABIC-Standardized-Mini-Cog-in-Arabic.pdf',self.hub)
        self.assertNotIn('/assessments/geriatric-measures/mini-cog/',self.hub)

if __name__=='__main__':unittest.main()
