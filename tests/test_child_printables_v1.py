from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "resources" / "child-printables"
CATALOG = json.loads((BASE / "catalog.json").read_text(encoding="utf-8"))


class ChildPrintablesV1Tests(unittest.TestCase):
    def test_catalog_contract(self):
        materials = CATALOG["materials"]
        self.assertEqual(CATALOG["schemaVersion"], 1)
        self.assertEqual(CATALOG["minimumLibraryContract"], 12)
        self.assertEqual(len(materials), 12)
        self.assertEqual(len({x["slug"] for x in materials}), 12)
        self.assertEqual(set(CATALOG["ages"]), {"0-3", "4-6", "7-9", "10-12", "13-15", "16-18"})
        self.assertEqual(set(CATALOG["levels"]), {"أساسي", "متوسط", "متقدم"})

    def test_hub_and_every_material_exist(self):
        hub = (BASE / "index.html").read_text(encoding="utf-8")
        self.assertIn('meta name="robots" content="index,follow', hub)
        self.assertIn("المواد المطبوعة للأطفال واليافعين", hub)
        for item in CATALOG["materials"]:
            path = BASE / item["slug"] / "index.html"
            self.assertTrue(path.is_file(), item["slug"])
            self.assertIn(f'href="{item["slug"]}/"', hub)

    def test_every_page_is_indexable_printable_and_complete(self):
        required = ["<h1", "طباعة / حفظ PDF", "آخر مراجعة داخلية", "المراجع", 'rel="canonical"', 'meta name="robots" content="index,follow']
        for item in CATALOG["materials"]:
            text = (BASE / item["slug"] / "index.html").read_text(encoding="utf-8")
            for token in required:
                self.assertIn(token, text, f"{item['slug']}: missing {token}")
            self.assertIn("../printables.css", text)
            self.assertNotIn("noindex", text.lower())
            self.assertGreater(len(re.sub(r"<[^>]+>", " ", text)), 900, item["slug"])

    def test_styles_have_mobile_and_a4_print_contract(self):
        css = (BASE / "printables.css").read_text(encoding="utf-8")
        self.assertIn("@media print", css)
        self.assertIn("@page", css)
        self.assertIn("size:A4", css.replace(" ", ""))
        self.assertIn("@media(max-width:620px)", css.replace(" ", ""))

    def test_sensitive_pages_have_explicit_safety_routes(self):
        for slug in ["after-hard-event-safety-support", "mood-energy-activity", "study-pressure-support-plan"]:
            text = (BASE / slug / "index.html").read_text(encoding="utf-8")
            self.assertIn('class="safety"', text)
            self.assertRegex(text, r"(خطر|إيذاء|طوارئ)")


if __name__ == "__main__":
    unittest.main()
