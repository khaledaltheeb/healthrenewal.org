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

ROOT_TEMPLATE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>دليل الأسرة للأشخاص ذوي الاحتياجات الخاصة | 64 دليلًا للرعاية والدعم</title><meta name="description" content="مرجع عربي منهجي للأسرة يضم 64 دليلًا عمليًا للحالات النمائية والعصبية والحركية والحسية والوراثية"><meta property="og:title" content="دليل الأسرة للرعاية والدعم — 64 حالة"><meta property="og:description" content="مسار عملي من فهم الحالة إلى التقييم والخطة والمتابعة والاستقلال عبر 64 دليلًا أسريًا."><link rel="canonical" href="https://healthrenewal.org/family-guide/"></head><body><main><p>يضم الإصدار الحالي 64 دليلًا مترابطًا مع مسارات التقييم والخدمات.</p><section class="section alt" id="conditions"><p class="kicker">64 دليلًا منشورًا وقابلًا للتوسع</p></section><section class="section" id="tools"><div><h2>أدوات</h2></div></section></main></body></html>'''

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

    def test_parent_page_links_hub_and_uses_polished_copy(self):
        root = (self.site / "family-guide/index.html").read_text(encoding="utf-8")
        self.assertIn('href="tools/"', root)
        self.assertIn("15 أداة موسعة", root)
        self.assertGreaterEqual(root.count('class="tool-card"'), 6)
        self.assertIn("64 دليل حالة و15 أداة عملية تغطي الاحتياجات", root)
        self.assertIn("64 دليل حالة و15 أداة أسرية", root)
        self.assertIn("مجموعة مترابطة من 64 دليل حالة و15 أداة", root)
        self.assertIn("مجموعة منشورة وقابلة للتوسع: 64 دليل حالة و15 أداة", root)
        self.assertIn("دليل الأسرة للرعاية والدعم — 64 دليل حالة و15 أداة", root)
        for phrase in module.BAD_ROOT_COPY:
            self.assertNotIn(phrase, root)

    def test_materializer_repairs_previously_generated_copy(self):
        generated = ROOT_TEMPLATE.replace("64 دليلًا عمليًا للحالات", "64 دليل حالة و15 أداة عمليًا للحالات")
        generated = generated.replace("64 دليلًا أسريًا", "64 دليل حالة و15 أداة أسريًا")
        generated = generated.replace("64 دليلًا مترابطًا", "64 دليل حالة و15 أداة مترابطًا")
        generated = generated.replace("64 دليلًا منشورًا وقابلًا", "64 دليل حالة و15 أداة منشورًا وقابلًا")
        generated = generated.replace("دليل الأسرة للرعاية والدعم — 64 حالة", "دليل الأسرة للرعاية والدعم — 64 حالة")
        root_path = self.site / "family-guide/index.html"
        root_path.write_text(generated, encoding="utf-8")
        module.publish(self.site, CONTENT)
        root = root_path.read_text(encoding="utf-8")
        self.assertIn("مجموعة مترابطة من 64 دليل حالة و15 أداة", root)
        self.assertIn("مجموعة منشورة وقابلة للتوسع: 64 دليل حالة و15 أداة", root)
        for phrase in module.BAD_ROOT_COPY:
            self.assertNotIn(phrase, root)

    def test_source_keys_and_urls_are_valid(self):
        sources = self.payload["sources"]
        for tool in self.payload["tools"]:
            self.assertGreaterEqual(len(tool["source_refs"]), 4)
            for key in tool["source_refs"]:
                self.assertIn(key, sources)
                self.assertRegex(sources[key]["url"], r"^https://")

if __name__ == "__main__":
    unittest.main(verbosity=2)
