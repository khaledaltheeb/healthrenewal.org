from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "assessments" / "global-measures" / "index.html"
SITEMAP = ROOT / "sitemap-rehabilitation-measures.xml"
HUB_JS = ROOT / "sectors" / "rehabilitation" / "measures" / "app.js"

ROUTES = [
    "/sectors/rehabilitation/measures/",
    "/sectors/rehabilitation/measures/performance/",
    "/sectors/rehabilitation/measures/sppb/",
    "/sectors/rehabilitation/measures/arabic-readiness/",
    "/assessments/",
    "/assessment-lab/",
]

class GlobalMeasuresGatewayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.sitemap = SITEMAP.read_text(encoding="utf-8")
        cls.hub_js = HUB_JS.read_text(encoding="utf-8")

    def test_identity_and_metadata(self):
        self.assertIn("المقاييس وأدوات التقييم المستخدمة عالميًا", self.html)
        self.assertIn('rel="canonical" href="https://healthrenewal.org/assessments/global-measures/"', self.html)
        self.assertIn('name="robots" content="index,follow', self.html)
        self.assertEqual(self.html.count("<h1>"), 1)

    def test_all_core_routes_are_linked(self):
        for route in ROUTES:
            self.assertIn(f'href="{route}"', self.html, route)

    def test_gateway_states_actual_tool_count(self):
        self.assertIn("15 أداة/بطارية فعلية", self.html)
        self.assertIn("7 أوراق إضافية", self.html)
        self.assertIn("24 أداة مدققة عربيًا", self.html)

    def test_rights_and_science_distinctions_are_explicit(self):
        self.assertIn("صلاحية المقياس", self.html)
        self.assertIn("صحة النسخة العربية", self.html)
        self.assertIn("حق إعادة النشر", self.html)
        self.assertIn("MDC", self.html)
        self.assertIn("MCID", self.html)
        self.assertIn("FULL أو OFFICIAL LINK أو HOLD", self.html)

    def test_gateway_is_discoverable(self):
        absolute = "https://healthrenewal.org/assessments/global-measures/"
        self.assertIn(absolute, self.sitemap)
        self.assertIn("/assessments/global-measures/", self.hub_js)

if __name__ == "__main__":
    unittest.main()
