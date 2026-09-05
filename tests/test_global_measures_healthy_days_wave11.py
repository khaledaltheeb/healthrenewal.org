from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "assessments" / "general-health-measures" / "index.html"
PAGE = ROOT / "assessments" / "general-health-measures" / "healthy-days" / "index.html"
JS = PAGE.with_name("healthy-days.js")
REGISTRY = ROOT / "content" / "global-measures-v1" / "cdc-healthy-days.json"


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k == "id" and v:
                self.ids.append(v)


def assert_unique(testcase, html):
    p = IdParser(); p.feed(html)
    testcase.assertEqual({x for x in p.ids if p.ids.count(x) > 1}, set())


class HealthyDaysWave11Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub = HUB.read_text(encoding="utf-8")
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.js = JS.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_pages_are_rtl_indexable_and_ids_unique(self):
        for html in (self.hub, self.page):
            self.assertIn('<html lang="ar" dir="rtl">', html)
            self.assertIn('index,follow', html)
            assert_unique(self, html)

    def test_general_health_has_five_categories(self):
        self.assertEqual(len(re.findall(r'name="general"', self.page)), 5)
        for value in ("excellent", "very-good", "good", "fair", "poor"):
            self.assertIn(f'value="{value}"', self.page)

    def test_three_day_counts_are_bounded_zero_to_thirty(self):
        for field in ("hd-physical", "hd-mental", "hd-limited"):
            self.assertRegex(self.page, rf'id="{field}"[^>]*type="number"[^>]*min="0"[^>]*max="30"')
        self.assertIn("Number.isInteger(n)", self.js)
        self.assertIn("n<0||n>30", self.js)

    def test_healthy_days_formula_caps_overlap_at_30(self):
        self.assertIn("Math.min(30,p+m)", self.js)
        self.assertIn("healthy=30-unhealthy", self.js)
        self.assertIn("p+m>30", self.js)
        self.assertIn("طُبق سقف 30", self.js)

    def test_activity_limitation_is_not_double_counted(self):
        self.assertIn("لا تدخل في حساب Healthy Days", self.js)
        self.assertIn("يبقى هذا المؤشر منفصلًا", self.page)
        self.assertNotIn("Math.min(30,p+m+l)", self.js)
        self.assertFalse(self.registry["components"]["activity_limitation_days"]["included_in_unhealthy_days_index"])

    def test_missing_physical_or_mental_blocks_derived_scores(self):
        self.assertIn("p===null||m===null", self.js)
        self.assertIn("أكمل يومي الصحة الجسدية والنفسية", self.js)

    def test_registry_formula_and_non_diagnostic_contract(self):
        self.assertEqual(self.registry["derived_indices"]["unhealthy_days"], "min(30, physically_unhealthy_days + mentally_unhealthy_days)")
        self.assertEqual(self.registry["derived_indices"]["healthy_days"], "30 - unhealthy_days")
        self.assertFalse(self.registry["diagnostic_by_score_alone"])
        self.assertIn("US-federal-government", self.registry["rights"]["status"])
        self.assertFalse(self.registry["rights"]["third_party_assets_reproduced"])
        self.assertFalse(self.registry["rights"]["cdc_logo_reproduced"])
        self.assertIn("no Arabic psychometric validation", self.registry["arabic_status"])

    def test_sources_and_no_diagnostic_claim(self):
        self.assertIn("https://www.cdc.gov/hrqol/methods.htm", self.page)
        self.assertIn("https://www.cdc.gov/other/agencymaterials.html", self.page)
        self.assertIn("لا تستخدم الأداة لتشخيص", self.page)


if __name__ == "__main__":
    unittest.main()
