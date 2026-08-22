#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v412", ROOT / "scripts" / "stage_safe_structural_fixes_v412.py")
assert SPEC and SPEC.loader
V412 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V412)


class SafeStructuralFixesV412Tests(unittest.TestCase):
    def test_arabic_metadata_is_staged_without_touching_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "site"
            stage = Path(tmp) / "stage"
            root.mkdir()
            source = root / "index.html"
            source.write_text("<html><head><meta property=\"og:description\" content=\"وصف عربي موثوق موجود مسبقا داخل الصفحة للاستخدام فقط كنسخة مطابقة\"></head><body><h1>دليل الدعم النفسي</h1><p>" + ("محتوى عربي مفيد " * 80) + "</p></body></html>", encoding="utf-8")
            before = source.read_bytes()
            plan = {"items": [{"path": "index.html", "route": "", "risk": "standard", "gate": "ready-for-safe-autofix", "findings": ["missing_lang", "missing_rtl", "missing_title", "canonical_count_not_one", "missing_description"], "actions": {"safe_autofix": []}}]}
            result = V412.build_staging(root, plan, stage)
            staged = (stage / "index.html").read_text(encoding="utf-8")
            self.assertTrue(result["source_unchanged"])
            self.assertEqual(source.read_bytes(), before)
            self.assertIn('lang="ar"', staged)
            self.assertIn('dir="rtl"', staged)
            self.assertIn("<title>دليل الدعم النفسي</title>", staged)
            self.assertIn('rel="canonical" href="https://healthrenewal.org/"', staged)
            self.assertIn('name="description"', staged)

    def test_high_risk_page_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "site"
            stage = Path(tmp) / "stage"
            root.mkdir()
            source = root / "cancer.html"
            html = "<html><head></head><body><h1>سرطان الأطفال</h1></body></html>"
            source.write_text(html, encoding="utf-8")
            plan = {"items": [{"path": "cancer.html", "route": "cancer", "risk": "high", "gate": "blocked-specialist-review", "findings": ["missing_title", "canonical_count_not_one"], "actions": {"safe_autofix": [{"code": "missing_title"}]}}]}
            result = V412.build_staging(root, plan, stage)
            self.assertEqual((stage / "cancer.html").read_text(encoding="utf-8"), html)
            self.assertEqual(result["summary"]["staged_changed"], 0)

    def test_ambiguous_language_is_not_guessed(self):
        html = "<html><head></head><body><h1>ABC عربي</h1></body></html>"
        self.assertIsNone(V412.infer_lang(html))


if __name__ == "__main__":
    unittest.main()
