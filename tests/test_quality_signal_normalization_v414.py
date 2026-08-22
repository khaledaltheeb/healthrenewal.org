from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("normalize_v414", ROOT / "scripts/normalize_quality_signals_v414.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class TestQualitySignalNormalizationV414(unittest.TestCase):
    def test_generic_treatment_language_is_not_high_risk(self):
        self.assertFalse(mod.refined_high_risk("دليل لفهم التشخيص والعلاج والاضطراب النفسي", "guides/mental-health"))

    def test_explicit_medication_and_cancer_are_high_risk(self):
        self.assertTrue(mod.refined_high_risk("سلامة استخدام دواء لدى الطفل", "guide"))
        self.assertTrue(mod.refined_high_risk("دعم طفل مصاب بسرطان الدم", "guide"))

    def test_declared_english_removes_false_rtl_and_risk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "en" / "index.html"
            p.parent.mkdir(parents=True)
            p.write_text('<html lang="en"><body><h1>Mental health guide</h1><p>' + ('English practical guidance ' * 40) + ' العربية</p></body></html>', encoding="utf-8")
            report = {"version": 410, "visual_audit": {}, "research_dossiers": [], "upgrade_queue": [{
                "path": "en/index.html", "route": "en/", "score": 70, "priority": 60, "risk": "high",
                "authoritative_sources": 0, "broken_internal_links": 0, "missing_alt": 0,
                "findings": ["missing_rtl", "high_risk_without_authoritative_source"]
            }]}
            normalized, audit = mod.normalize(root, report)
            page = normalized["upgrade_queue"][0]
            self.assertEqual(page["risk"], "standard")
            self.assertNotIn("missing_rtl", page["findings"])
            self.assertNotIn("high_risk_without_authoritative_source", page["findings"])
            self.assertIn("no_authoritative_source", page["findings"])
            self.assertEqual(audit["summary"]["high_risk_after"], 0)

    def test_ownership_verification_file_is_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "google644f1f7a8b7aaa2b.html"
            p.write_text("google-site-verification: token", encoding="utf-8")
            report = {"version": 410, "visual_audit": {}, "research_dossiers": [], "upgrade_queue": [{
                "path": p.name, "route": p.name, "score": 40, "priority": 70, "risk": "standard",
                "authoritative_sources": 0, "broken_internal_links": 0, "missing_alt": 0, "findings": ["very_thin_content"]
            }]}
            normalized, audit = mod.normalize(root, report)
            self.assertEqual(normalized["upgrade_queue"], [])
            self.assertIn(p.name, audit["summary"]["excluded_non_content_files"])


if __name__ == "__main__":
    unittest.main()
