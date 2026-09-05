from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "sectors" / "rehabilitation" / "measures" / "sppb" / "index.html"
JS = PAGE.with_name("sppb.js")
REGISTRY = ROOT / "content" / "rehabilitation-measures-v1" / "sppb.json"
SITEMAP = ROOT / "sitemap-rehabilitation-measures.xml"
HUB_JS = ROOT / "sectors" / "rehabilitation" / "measures" / "app.js"

class SPPBTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.js = JS.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_metadata_and_rights(self):
        self.assertIn('https://healthrenewal.org/sectors/rehabilitation/measures/sppb/', self.html)
        self.assertEqual(self.registry["rights"]["permission_required"], False)
        self.assertEqual(self.registry["rights"]["royalty_required"], False)
        self.assertEqual(self.registry["rights"]["nih_copyright_field"], "No")
        self.assertTrue(self.registry["full_reproduction"])

    def test_three_components_and_total_are_present(self):
        for section in ('id="balance"', 'id="gait"', 'id="chair"', 'id="total"'):
            self.assertIn(section, self.html)
        self.assertIn('id="sppb-total"', self.html)
        self.assertEqual(self.registry["score_range"], [0, 12])

    def test_balance_hierarchy_scoring(self):
        self.assertIn("if(side<10)return 0", self.js)
        self.assertIn("if(semi<10)return 1", self.js)
        self.assertIn("if(tandem>=10)return 4", self.js)
        self.assertIn("if(tandem>=3)return 3", self.js)
        self.assertIn("return 2", self.js)

    def test_gait_thresholds(self):
        self.assertIn("t<=3.61?4:t<=4.65?3:t<=6.52?2:1", self.js)
        self.assertIn("t<=4.81?4:t<=6.20?3:t<=8.70?2:1", self.js)
        self.assertIn("Math.min(...vals)", self.js)

    def test_chair_thresholds(self):
        self.assertIn("t<=11.19?4:t<=13.69?3:t<=16.69?2:t<=60?1:0", self.js)
        self.assertIn("sppb-chair-arms", self.js)
        self.assertIn("sppb-chair-unable", self.js)

    def test_total_requires_all_components(self):
        self.assertIn("b!==null&&g!==null&&c!==null?b+g.score+c.score:null", self.js)

    def test_print_and_clear_controls(self):
        self.assertIn('id="sppb-print"', self.html)
        self.assertIn('id="sppb-clear"', self.html)
        self.assertIn("window.print()", self.js)

    def test_arabic_validation_claim_is_fail_closed(self):
        self.assertIn("ليست دراسة تكييف لغوي/سيكومتري عربية مستقلة", self.html)
        self.assertIn("not an independently psychometrically validated Arabic translation", self.registry["arabic_status"])

    def test_discovery_contract(self):
        route = "/sectors/rehabilitation/measures/sppb/"
        self.assertIn(route, HUB_JS.read_text(encoding="utf-8"))
        self.assertIn("https://healthrenewal.org" + route, SITEMAP.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
