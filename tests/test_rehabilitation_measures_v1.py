from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "sectors" / "rehabilitation" / "measures" / "index.html"
CSS = PAGE.with_name("measures.css")
JS = PAGE.with_name("app.js")
REGISTRY = ROOT / "content" / "rehabilitation-measures-v1" / "registry.json"

FULL_IDS = {
    "tug",
    "chair-stand-30",
    "four-stage-balance",
    "10mwt",
    "5xsts",
    "nprs",
    "psfs",
}

class IdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key == "id" and value:
                self.ids.append(value)

class RehabilitationMeasuresV1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.js = JS.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.measures = cls.registry["measures"]

    def test_core_files_exist_and_page_is_indexable(self) -> None:
        self.assertTrue(PAGE.is_file())
        self.assertTrue(CSS.is_file())
        self.assertTrue(JS.is_file())
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertIn('rel="canonical" href="https://healthrenewal.org/sectors/rehabilitation/measures/"', self.html)
        self.assertIn('name="robots" content="index,follow', self.html)
        self.assertEqual(len(re.findall(r"<h1\b", self.html, flags=re.I)), 1)

    def test_html_ids_are_unique(self) -> None:
        parser = IdParser()
        parser.feed(self.html)
        duplicates = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        self.assertEqual(duplicates, [])

    def test_registry_has_substantial_unique_catalog(self) -> None:
        self.assertGreaterEqual(len(self.measures), 35)
        ids = [m["id"] for m in self.measures]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(FULL_IDS.issubset(set(ids)))
        for m in self.measures:
            self.assertTrue(str(m.get("core_source", "")).startswith("https://"), m["id"])
            self.assertIn(m["status"], {
                "full-work-sheet", "public-domain-link", "owner-link-only", "verify-before-reproduction"
            })

    def test_full_reproduction_is_fail_closed(self) -> None:
        actual_full = {m["id"] for m in self.measures if m.get("full_reproduction") is True}
        self.assertEqual(actual_full, FULL_IDS)
        for m in self.measures:
            if m["status"] in {"owner-link-only", "verify-before-reproduction", "public-domain-link"}:
                self.assertFalse(m.get("full_reproduction"), m["id"])
                self.assertTrue(m.get("rights_basis"), m["id"])

    def test_every_registry_measure_is_discoverable_on_page(self) -> None:
        page_lower = self.html.lower()
        missing = []
        for m in self.measures:
            name = m["name"].lower()
            acronym = str(m.get("acronym", "")).lower()
            if name not in page_lower and (not acronym or acronym not in page_lower):
                missing.append(m["id"])
        self.assertEqual(missing, [])

    def test_all_seven_live_worksheets_have_print_and_clear_controls(self) -> None:
        page_section_ids = {
            "tug": "tug",
            "chair-stand-30": "chair-stand-30",
            "four-stage-balance": "four-stage-balance",
            "10mwt": "walk-10m",
            "5xsts": "fts",
            "nprs": "nprs",
            "psfs": "psfs",
        }
        for registry_id, page_id in page_section_ids.items():
            self.assertIn(f'id="{page_id}"', self.html, registry_id)
            self.assertIn(f'data-print="{page_id}"', self.html, registry_id)
            self.assertIn(f'data-clear="{page_id}"', self.html, registry_id)

    def test_governance_and_longitudinal_templates_exist(self) -> None:
        self.assertIn('id="rights-sheet"', self.html)
        self.assertIn('id="serial-tracker"', self.html)
        self.assertIn('Mapi Research Trust', self.html)
        self.assertIn('Rehabilitation Measures Database', self.html)
        self.assertIn('MDC', self.html)
        self.assertIn('MCID', self.html)
        self.assertIn('لا تُعد أي درجة تشخيصًا', self.html)

    def test_blank_numeric_inputs_do_not_become_zero(self) -> None:
        self.assertIn("String(el.value).trim()===''", self.js)
        self.assertIn(".psfs-score').map(el=>String(el.value).trim()===''?null:Number(el.value))", self.js)

    def test_scoring_runtime_contains_expected_formulas(self) -> None:
        self.assertIn("const speed=distance/mean", self.js)
        self.assertIn("Math.min(...vals)", self.js)
        self.assertIn("vals.reduce((a,b)=>a+b,0)/vals.length", self.js)
        self.assertIn("window.print()", self.js)
        self.assertIn("data-catalog-card", self.html)

    def test_print_contract_prints_only_selected_sheet(self) -> None:
        self.assertIn(".measure{display:none!important}", self.css)
        self.assertIn(".measure.print-target{display:block!important", self.css)
        self.assertIn("@media print", self.css)

if __name__ == "__main__":
    unittest.main()
