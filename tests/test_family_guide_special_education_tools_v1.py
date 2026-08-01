#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
import re
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "publish_family_guide_special_education_tools_v1.py"
sys.path.insert(0, str(ROOT / "scripts"))
CONTENT = ROOT / "content" / "family-guide-special-education-tools-v1"
spec = importlib.util.spec_from_file_location("special_ed_tools", GENERATOR)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)

ROOT_TEMPLATE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>دليل الأسرة | 64 دليلًا</title><meta name="description" content="دليل"><link rel="canonical" href="https://healthrenewal.org/family-guide/"></head><body><main><section class="section" id="tools"><div><h2>أدوات</h2></div></section></main></body></html>'''

class ToolPublishingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name)
        (self.site / "family-guide").mkdir(parents=True)
        (self.site / "family-guide/index.html").write_text(ROOT_TEMPLATE, encoding="utf-8")
        (self.site / "assets/platform").mkdir(parents=True)
        (self.site / "copyright").mkdir(parents=True)
        self.report = module.publish(self.site, CONTENT)
        self.payload = module.load_payload(CONTENT)

    def tearDown(self):
        self.tmp.cleanup()

    def test_contract_counts_and_depth(self):
        self.assertEqual(self.report["status"], "passed")
        self.assertEqual(self.report["tool_count"], 15)
        self.assertEqual(self.report["generated_pages"], 16)
        self.assertGreaterEqual(self.report["minimum_page_words"], 1200)
        self.assertGreaterEqual(self.report["hub_words"], 500)
        self.assertGreaterEqual(self.report["source_count"], 10)

    def test_every_tool_has_metadata_form_sources_and_static_card(self):
        hub = (self.site / "family-guide/tools/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count('class="tool-card"'), 15)
        for tool in self.payload["tools"]:
            slug = tool["slug"]
            path = self.site / "family-guide/tools" / slug / "index.html"
            self.assertTrue(path.is_file(), slug)
            source = path.read_text(encoding="utf-8")
            self.assertIn(f'<link rel="canonical" href="https://healthrenewal.org/family-guide/tools/{slug}/">', source)
            self.assertEqual(len(re.findall(r"<h1\b", source, re.I)), 1)
            self.assertIn('<meta name="robots" content="index,follow', source)
            self.assertIn('type="application/ld+json"', source)
            self.assertIn('class="card tool-form"', source)
            self.assertIn('onclick="window.print()"', source)
            self.assertGreaterEqual(source.count('class="source-card"'), 4)
            self.assertGreaterEqual(module.visible_words(source), 1200)
            self.assertIn(f'href="{slug}/"', hub)

    def test_parent_page_links_the_hub_and_featured_tools(self):
        root = (self.site / "family-guide/index.html").read_text(encoding="utf-8")
        self.assertIn('href="tools/"', root)
        self.assertIn("15 أداة موسعة", root)
        self.assertGreaterEqual(root.count('class="tool-card"'), 6)

    def test_source_keys_and_urls_are_valid(self):
        sources = self.payload["sources"]
        for tool in self.payload["tools"]:
            self.assertGreaterEqual(len(tool["sources"]), 4)
            for key in tool["sources"]:
                self.assertIn(key, sources)
                self.assertRegex(sources[key]["url"], r"^https://")

if __name__ == "__main__":
    unittest.main(verbosity=2)
