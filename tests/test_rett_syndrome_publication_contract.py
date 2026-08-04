from __future__ import annotations

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "special-needs/conditions/rett-syndrome/index.html"
EVIDENCE = ROOT / "special-needs/conditions/rett-syndrome/evidence.json"
HUB = ROOT / "special-needs/conditions/index.html"
SITEMAP = ROOT / "sitemap-rett-syndrome.xml"
INDEX = ROOT / "sitemap-index.xml"


class RettSyndromePublicationContract(unittest.TestCase):
    def test_files_exist(self):
        for path in (PAGE, EVIDENCE, HUB, SITEMAP, INDEX):
            self.assertTrue(path.is_file(), path)

    def test_page_contract(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"<h1\b", text, flags=re.I)), 1)
        self.assertIn('lang="ar"', text)
        self.assertIn('dir="rtl"', text)
        self.assertIn("https://healthrenewal.org/special-needs/conditions/rett-syndrome/", text)
        self.assertNotIn("khaledaltheeb.github.io", text)
        self.assertNotIn('name="keywords"', text.lower())
        for anchor in (
            'id="genetics"', 'id="diagnosis"', 'id="health"',
            'id="communication"', 'id="treatment"', 'id="trofinetide"',
            'id="transition"', 'id="evidence"', 'id="sources"'
        ):
            self.assertIn(anchor, text)
        self.assertGreaterEqual(len(re.findall(r"<li>", text)), 45)
        self.assertIn("MedicalWebPage", text)
        self.assertIn("FAQPage", text)
        self.assertIn("BreadcrumbList", text)

    def test_evidence_registry(self):
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "1.0.0")
        self.assertGreaterEqual(len(data["sources"]), 9)
        self.assertGreaterEqual(len(data["claim_register"]), 5)
        ids = {row["id"] for row in data["sources"]}
        self.assertEqual(len(ids), len(data["sources"]))
        for row in data["sources"]:
            self.assertTrue(row["url"].startswith("https://"))

    def test_sitemap_discovery(self):
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ET.fromstring(SITEMAP.read_text(encoding="utf-8"))
        urls = [n.text for n in root.findall("s:url/s:loc", ns)]
        self.assertIn("https://healthrenewal.org/special-needs/conditions/rett-syndrome/", urls)
        index = ET.fromstring(INDEX.read_text(encoding="utf-8"))
        maps = [n.text for n in index.findall("s:sitemap/s:loc", ns)]
        self.assertIn("https://healthrenewal.org/sitemap-rett-syndrome.xml", maps)


if __name__ == "__main__":
    unittest.main()
