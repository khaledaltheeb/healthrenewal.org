#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ensure_special_needs_publication_v1.py"
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("special_needs_inventory", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

FAMILY_ROOT = '''<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8">
<title>دليل الأسرة للأشخاص ذوي الاحتياجات الخاصة | 64 دليلًا للرعاية والدعم</title>
<meta name="description" content="مرجع عربي منهجي للأسرة يضم 64 دليلًا عمليًا للحالات النمائية والعصبية والحركية والحسية والوراثية">
<meta property="og:title" content="دليل الأسرة للرعاية والدعم — 64 حالة">
<meta property="og:description" content="مسار عملي من فهم الحالة إلى التقييم والخطة والمتابعة والاستقلال عبر 64 دليلًا أسريًا.">
<link rel="canonical" href="https://healthrenewal.org/family-guide/">
</head><body><main>
<p>يضم الإصدار الحالي 64 دليلًا مترابطًا مع مسارات التقييم والخدمات.</p>
<section class="section alt" id="conditions"><p class="kicker">64 دليلًا منشورًا وقابلًا للتوسع</p></section>
<section class="section" id="tools"><div><h2>أدوات</h2></div></section>
</main></body></html>'''


class FamilyToolsProductionWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name) / "_site"
        self.site.mkdir(parents=True)
        family = self.site / "family-guide"
        family.mkdir(parents=True)
        (family / "index.html").write_text(FAMILY_ROOT, encoding="utf-8")

        # Keep this focused on the family-tools wiring. Capability repair has
        # its own contract and only runs when fewer than 155 pages are present.
        for index in range(module.MINIMUM_COUNTS["capability_pages"]):
            page = self.site / "capabilities" / f"fixture-{index:03d}" / "index.html"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text("<!doctype html><html><body><h1>fixture</h1></body></html>", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_full_artifact_rebuilds_all_fifteen_tools_from_source(self) -> None:
        result = module.repair_missing_generated_families(self.site, ROOT)
        self.assertEqual(
            result["actions"],
            ["publish_family_guide_special_education_tools_v1.py"],
        )
        self.assertEqual(result["after"]["family_tools"], 15)

        hub = self.site / "family-guide" / "tools" / "index.html"
        self.assertTrue(hub.is_file())
        self.assertIn("15 صفحة موسعة", hub.read_text(encoding="utf-8"))

        report_path = self.site / "api" / "family-guide-special-education-tools-v1.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["tool_count"], 15)
        self.assertEqual(report["generated_pages"], 16)
        self.assertGreaterEqual(report["minimum_page_words"], 1200)

    def test_rebuild_is_deterministic_and_runs_even_when_snapshot_exists(self) -> None:
        first = module.repair_missing_generated_families(self.site, ROOT)
        hub_path = self.site / "family-guide" / "tools" / "index.html"
        first_hub = hub_path.read_text(encoding="utf-8")
        second = module.repair_missing_generated_families(self.site, ROOT)
        second_hub = hub_path.read_text(encoding="utf-8")

        self.assertEqual(first["after"]["family_tools"], 15)
        self.assertEqual(second["before"]["family_tools"], 15)
        self.assertEqual(second["after"]["family_tools"], 15)
        self.assertEqual(
            second["actions"],
            ["publish_family_guide_special_education_tools_v1.py"],
        )
        self.assertEqual(first_hub, second_hub)

    def test_source_checkout_is_never_materialized(self) -> None:
        result = module.repair_missing_generated_families(ROOT, ROOT)
        self.assertEqual(result["actions"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
