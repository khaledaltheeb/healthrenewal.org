from __future__ import annotations
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts"/"publish_special_needs_protocols_v326.py"
spec=importlib.util.spec_from_file_location("protocols_v326",SCRIPT)
mod=importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

class SpecialNeedsProtocolsV326Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp(prefix="special-needs-v326-"))
        (self.tmp/"special-needs").mkdir(parents=True)
        (self.tmp/"api").mkdir()
        (self.tmp/"special-needs"/"index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>مركز ذوي الاحتياجات الخاصة</h1></main></body></html>',
            encoding="utf-8")
        (self.tmp/"sitemap-special-needs.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/special-needs/</loc></url></urlset>',
            encoding="utf-8")
    def tearDown(self):
        shutil.rmtree(self.tmp,ignore_errors=True)

    def test_source_contract(self):
        data=mod.load(); protocols=mod.validate(data)
        self.assertEqual(len(protocols),50)
        self.assertEqual(len(data["sources"]),51)
        self.assertEqual([p["number"] for p in protocols],list(range(1,51)))
        self.assertEqual(len({p["slug"] for p in protocols}),50)
        self.assertFalse(data["review_status"].endswith("completed"))
        serialized=json.dumps(data,ensure_ascii=False)
        self.assertNotRegex(serialized,mod.BANNED)
        for p in protocols:
            self.assertGreaterEqual(len(p["source_ids"]),4)
            self.assertGreaterEqual(len(p["assessment"]),5)
            self.assertGreaterEqual(len(p["targeted"]),5)
            self.assertGreaterEqual(len(p["outcomes"]),5)

    def test_publication_depth_discovery_and_idempotence(self):
        first=mod.publish(self.tmp)
        self.assertEqual(first["protocol_count"],50)
        self.assertEqual(first["generated_page_count"],51)
        self.assertGreaterEqual(first["minimum_words"],1200)
        self.assertGreaterEqual(first["minimum_citations"],6)
        self.assertFalse(first["external_clinical_review_completed"])
        index=self.tmp/"special-needs"/"protocols"/"index.html"
        self.assertEqual(index.read_text(encoding="utf-8").count("فتح البروتوكول الكامل"),50)
        pages=list((self.tmp/"special-needs"/"protocols").glob("*/index.html"))
        self.assertEqual(len(pages),50)
        hub=(self.tmp/"special-needs"/"index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count(mod.START),1)
        before={p.relative_to(self.tmp).as_posix():p.read_bytes() for p in self.tmp.rglob("*") if p.is_file()}
        second=mod.publish(self.tmp)
        after={p.relative_to(self.tmp).as_posix():p.read_bytes() for p in self.tmp.rglob("*") if p.is_file()}
        self.assertEqual(first["protocol_slugs"],second["protocol_slugs"])
        self.assertEqual(before,after)
        urls=[(n.text or "").strip() for n in ET.parse(self.tmp/"sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")]
        self.assertEqual(len([u for u in urls if "/special-needs/protocols/" in u]),51)
        for slug in first["protocol_slugs"]:
            u=f"https://healthrenewal.org/special-needs/protocols/{slug}/"
            self.assertEqual(urls.count(u),1)
            text=(self.tmp/"special-needs"/"protocols"/slug/"index.html").read_text(encoding="utf-8")
            self.assertEqual(text.count("<h1"),1)
            self.assertGreaterEqual(len(re.findall(r"<h2\b",text)),11)
            self.assertIn("المراجعة الخارجية السريرية المستقلة لم تكتمل",text)
            self.assertNotRegex(text,mod.BANNED)

if __name__=="__main__":
    unittest.main()
