#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import consolidate_duplicate_pages_v1 as consolidation


class CrossSurfaceDuplicateConsolidationTest(unittest.TestCase):
    def test_provider_demo_fragments_are_not_injected_into_public_condition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            target = site / "special-needs/conditions/global-developmental-delay/index.html"
            alias = site / "provider-assessment-demo/conditions/global-developmental-delay/index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            alias.parent.mkdir(parents=True, exist_ok=True)

            original_target = "<html><head><title>التأخر النمائي الشامل</title></head><body><main><h1>الدليل العام</h1><p>محتوى عام موثوق يبقى في مساره العام دون خلط بسياق المنصة المهنية.</p></main></body></html>"
            alias_html = """<html><head><title>دليل مهني تجريبي</title></head><body><main>
<p>هذه فقرة مهنية تجريبية طويلة بما يكفي لتبدو فريدة أثناء المقارنة وتحتوي رابطًا نسبيًا خاصًا بسياق المنصة المهنية <a href=\"../../center-guide.html\">دليل المركز</a> ولا يجوز نقلها إلى المسار العام.</p>
</main></body></html>"""
            target.write_text(original_target, encoding="utf-8")
            alias.write_text(alias_html, encoding="utf-8")

            result = consolidation.consolidate(site, report={})

            public_html = target.read_text(encoding="utf-8")
            alias_after = alias.read_text(encoding="utf-8")
            self.assertEqual(public_html, original_target)
            self.assertNotIn("center-guide.html", public_html)
            self.assertNotIn("merged-duplicate-content", public_html)
            self.assertIn("/special-needs/conditions/global-developmental-delay/", alias_after)
            self.assertEqual(result["duplicateRoutesConsolidated"], 1)
            self.assertEqual(result["mergedUniqueSections"], 0)
            self.assertEqual(result["consolidated"][0]["mergedUniqueFragments"], 0)
            self.assertEqual(
                result["consolidated"][0]["reason"],
                "cross-surface alias canonicalized without fragment transfer",
            )


if __name__ == "__main__":
    unittest.main()
