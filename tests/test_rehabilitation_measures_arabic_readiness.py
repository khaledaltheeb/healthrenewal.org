from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "sectors" / "rehabilitation" / "measures" / "arabic-readiness" / "index.html"
JS = PAGE.with_name("readiness.js")
REGISTRY = ROOT / "content" / "rehabilitation-measures-v1" / "arabic-readiness.json"
HUB_JS = ROOT / "sectors" / "rehabilitation" / "measures" / "app.js"
SITEMAP = ROOT / "sitemap-rehabilitation-measures.xml"

ALLOWED_STATES = {
    "rawafid-operational",
    "validated-source-ready",
    "validated-form-access-pending",
    "owner-controlled",
    "evidence-limited",
}

class ArabicReadinessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        cls.js = JS.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.instruments = cls.registry["instruments"]

    def test_matrix_is_substantial_and_unique(self):
        self.assertGreaterEqual(len(self.instruments), 24)
        ids = [x["id"] for x in self.instruments]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({"rmdq24", "pdi", "bbs", "lefs", "quickdash", "eq5d", "whodas", "koos12", "sppb"}.issubset(ids))

    def test_every_record_has_three_gate_information(self):
        for item in self.instruments:
            self.assertIn(item["arabic_state"], ALLOWED_STATES, item["id"])
            self.assertTrue(item.get("arabic_validation"), item["id"])
            self.assertTrue(item.get("rights"), item["id"])
            self.assertTrue(str(item.get("source", "")).startswith("https://"), item["id"])
            self.assertTrue(item.get("publication"), item["id"])

    def test_fixed_item_validated_tools_are_fail_closed(self):
        # Arabic validation is not sufficient to classify a fixed-item PROM as a Rawafid full worksheet.
        fixed_item_ids = {"rmdq24", "pdi", "bbs", "mini-bestest", "lefs", "odi", "ndi", "quickdash", "eq5d", "whodas", "whoqol-bref", "sf36v2", "koos12", "hoos", "womac", "moca"}
        by_id = {x["id"]: x for x in self.instruments}
        for instrument_id in fixed_item_ids:
            self.assertNotEqual(by_id[instrument_id]["publication"], "full-operational-worksheet", instrument_id)

    def test_public_domain_does_not_bypass_exact_arabic_source_gate(self):
        by_id = {x["id"]: x for x in self.instruments}
        self.assertEqual(by_id["rmdq24"]["arabic_state"], "validated-form-access-pending")
        self.assertIn("public domain", by_id["rmdq24"]["rights"].lower())
        self.assertEqual(by_id["pdi"]["arabic_state"], "validated-form-access-pending")
        self.assertIn("public domain", by_id["pdi"]["rights"].lower())

    def test_owner_controlled_distribution_is_explicit(self):
        by_id = {x["id"]: x for x in self.instruments}
        self.assertEqual(by_id["quickdash"]["publication"], "official-owner-link-only")
        self.assertEqual(by_id["eq5d"]["publication"], "official-owner-link-only")
        self.assertEqual(by_id["moca"]["publication"], "official-owner-only")

    def test_version_sensitive_findings_are_preserved(self):
        by_id = {x["id"]: x for x in self.instruments}
        self.assertIn("20-item", by_id["lefs"]["arabic_validation"])
        self.assertIn("15-item", by_id["lefs"]["arabic_validation"])
        self.assertIn("KOOS-12", by_id["koos12"]["name"])
        self.assertIn("HOOS-12", by_id["hoos"]["rights"])

    def test_page_explains_validation_is_not_republication_permission(self):
        self.assertIn("Validated in Arabic", self.html)
        self.assertIn("Publish full Arabic form", self.html)
        self.assertIn("Free", self.html)
        self.assertIn("Public Domain", self.html)
        self.assertIn("FULL / OFFICIAL LINK / HOLD", self.html)

    def test_filter_runtime_and_discovery(self):
        self.assertIn("data-readiness-row", self.html)
        self.assertIn("readiness-search", self.js)
        route = "/sectors/rehabilitation/measures/arabic-readiness/"
        self.assertIn(route, HUB_JS.read_text(encoding="utf-8"))
        self.assertIn("https://healthrenewal.org" + route, SITEMAP.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
