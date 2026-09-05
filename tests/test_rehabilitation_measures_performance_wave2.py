from __future__ import annotations

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "sectors" / "rehabilitation" / "measures" / "performance" / "index.html"
JS = PAGE.with_name("performance.js")
HUB_JS = ROOT / "sectors" / "rehabilitation" / "measures" / "app.js"
REGISTRY = ROOT / "content" / "rehabilitation-measures-v1" / "performance-wave2.json"
SITEMAP = ROOT / "sitemap-rehabilitation-measures.xml"
SITEMAP_INDEX = ROOT / "sitemap-index.xml"

EXPECTED = {
    "walk6": "six-minute-walk",
    "walk2": "two-minute-walk",
    "fsst": "four-square-step",
    "sls": "single-leg-stance",
    "step2": "two-minute-step",
    "step15": "step-test-15s",
    "grip": "grip-strength",
}

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id" and v:
                self.ids.append(v)

class PerformanceWave2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.js = JS.read_text(encoding="utf-8")
        cls.hub_js = HUB_JS.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.sitemap = SITEMAP.read_text(encoding="utf-8")
        cls.sitemap_index = SITEMAP_INDEX.read_text(encoding="utf-8")

    def test_files_and_metadata(self):
        self.assertTrue(PAGE.is_file())
        self.assertTrue(JS.is_file())
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('https://healthrenewal.org/sectors/rehabilitation/measures/performance/', self.html)
        self.assertIn('index,follow', self.html)

    def test_unique_ids(self):
        parser = IdParser(); parser.feed(self.html)
        dupes = {x for x in parser.ids if parser.ids.count(x) > 1}
        self.assertEqual(dupes, set())

    def test_all_seven_work_sheets_have_print_and_clear(self):
        for page_id in EXPECTED:
            self.assertIn(f'id="{page_id}"', self.html)
            self.assertIn(f'data-print="{page_id}"', self.html)
            self.assertIn(f'data-clear="{page_id}"', self.html)

    def test_registry_is_exact_and_fail_closed(self):
        measures = self.registry["measures"]
        self.assertEqual(len(measures), 7)
        self.assertEqual({m["id"] for m in measures}, set(EXPECTED.values()))
        for m in measures:
            self.assertEqual(m["status"], "full-recording-sheet")
            self.assertTrue(m["source"].startswith("https://www.sralab.org/rehabilitation-measures/"))
            self.assertTrue(m["rights_basis"])
            self.assertTrue(m["critical_protocol_fields"])

    def test_runtime_has_expected_calculations(self):
        self.assertIn("course*Math.max(0,laps)+(partial||0)", self.js)
        self.assertIn("Math.min(...vals)", self.js)
        self.assertIn("Math.max(...vals)", self.js)
        self.assertIn("vals.reduce((a,b)=>a+b,0)/vals.length", self.js)
        self.assertIn("window.print()", self.js)
        self.assertIn("String(e.value).trim()===''", self.js)

    def test_safety_and_protocol_consistency_are_explicit(self):
        self.assertIn("اختبار مجهود", self.html)
        self.assertIn("خطر السقوط", self.html)
        self.assertIn("لا تقارن", self.html)
        self.assertIn("نفس الجهاز", self.html)
        self.assertIn("المسار", self.html)

    def test_no_borg_scale_or_standardized_encouragement_script_copied(self):
        self.assertNotIn("6 7 8 9 10 11 12 13 14 15 16 17 18 19 20", self.html)
        self.assertNotIn("You are doing well. You have 5 minutes to go", self.html)

    def test_all_sources_are_present_on_page(self):
        for m in self.registry["measures"]:
            self.assertIn(m["source"], self.html)

    def test_performance_library_is_discoverable_from_hub_and_sitemaps(self):
        route = "/sectors/rehabilitation/measures/performance/"
        absolute = "https://healthrenewal.org" + route
        self.assertIn(route, self.hub_js)
        self.assertIn(absolute, self.sitemap)
        self.assertIn("https://healthrenewal.org/sectors/rehabilitation/measures/", self.sitemap)
        self.assertIn("https://healthrenewal.org/sitemap-rehabilitation-measures.xml", self.sitemap_index)

if __name__ == "__main__":
    unittest.main()
