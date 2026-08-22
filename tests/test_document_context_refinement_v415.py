from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("refine_v415", ROOT / "scripts/refine_document_context_v415.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class TestDocumentContextRefinementV415(unittest.TestCase):
    def test_fragment_is_not_penalized_for_page_shell_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "content" / "fragment.html"
            p.parent.mkdir(parents=True)
            p.write_text('<section><h2>دليل عملي</h2><p>' + ('محتوى عربي مفيد ' * 60) + '</p></section>', encoding='utf-8')
            report = {"version": 414, "visual_audit": {}, "research_dossiers": [], "upgrade_queue": [{
                "path": "content/fragment.html", "route": "content/fragment.html", "score": 62, "priority": 50,
                "risk": "standard", "authoritative_sources": 0, "broken_internal_links": 0, "missing_alt": 0,
                "findings": ["missing_lang", "missing_rtl", "missing_title", "missing_description", "missing_h1", "missing_jsonld", "canonical_count_not_one"]
            }]}
            refined, _ = mod.refine(root, report)
            page = refined["upgrade_queue"][0]
            self.assertEqual(page["artifact_type"], "editorial-fragment")
            self.assertFalse(set(page["findings"]) & mod.PAGE_ONLY_FINDINGS)
            self.assertEqual(page["score"], 100)

    def test_navigation_cancer_link_does_not_make_travel_page_high_risk(self):
        html = '''<html><head><title>Accessible travel planning</title></head><body>
        <header><nav><a href="/cancer/">Cancer support</a></nav></header>
        <main><h1>Accessible travel planning</h1><p>Plan transport, accessibility and accommodation.</p></main>
        <footer>Medication safety | cancer | seizure</footer></body></html>'''
        self.assertFalse(mod.is_high_risk(html, "guides/accessible-travel-planning/", "document"))

    def test_main_clinical_content_remains_high_risk(self):
        html = '<html><head><title>Guide</title></head><body><main><h1>سلامة الدواء</h1><p>سلامة الدواء لدى الطفل</p></main></body></html>'
        self.assertTrue(mod.is_high_risk(html, "guide/", "document"))

    def test_full_document_is_detected(self):
        self.assertEqual(mod.classify_document('<!doctype html><html><head></head><body></body></html>'), 'document')
        self.assertEqual(mod.classify_document('<section><h2>Part</h2></section>'), 'editorial-fragment')


if __name__ == '__main__':
    unittest.main()
