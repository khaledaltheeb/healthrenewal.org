#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts/publish_tips_hub_v234.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"


class TipsV234Test(unittest.TestCase):
    def build(self) -> Path:
        temp = Path(tempfile.mkdtemp(prefix="tips-v234-"))
        (temp / "assets/brand").mkdir(parents=True)
        (temp / "robots.txt").write_text(
            "User-agent: *\nAllow: /\nSitemap: " + BASE + "sitemap.xml\n",
            encoding="utf-8",
        )
        (temp / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )
        subprocess.run([sys.executable, str(PUBLISHER), str(temp)], check=True)
        return temp

    def test_source_contract(self) -> None:
        supplemental = json.loads(
            (ROOT / "content/v234/tips-guides-supplement-ar.json").read_text(encoding="utf-8")
        )
        self.assertEqual(supplemental["version"], 234)
        self.assertEqual(len(supplemental["guides"]), 16)
        identity = (ROOT / "scripts/enforce_platform_identity_v201.py").read_text(encoding="utf-8")
        self.assertIn('run_script("publish_tips_hub_v234.py", site)', identity)
        slugs = [item["slug"] for item in supplemental["guides"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        for item in supplemental["guides"]:
            self.assertGreaterEqual(len(item["tips"]), 6)
            self.assertGreaterEqual(len(item["goals"]), 3)
            self.assertGreaterEqual(len(item["faq"]), 2)
            self.assertTrue(item["seek_help"])
            self.assertTrue(item["keywords"])

    def test_generated_section_is_complete_and_indexable(self) -> None:
        site = self.build()
        report = json.loads((site / "api/tips-audit-v234.json").read_text(encoding="utf-8"))
        export = json.loads((site / "api/v1/tips.json").read_text(encoding="utf-8"))

        self.assertEqual(report["guide_count"], 36)
        self.assertEqual(report["legacy_guides_enriched"], 20)
        self.assertEqual(report["new_guides"], 16)
        self.assertEqual(report["category_count"], 9)
        self.assertEqual(report["static_pages"], 3)
        self.assertEqual(report["page_count"], 49)
        self.assertEqual(report["sitemap_urls"], 49)
        self.assertGreaterEqual(report["minimum_rendered_arabic_words"], 100)
        self.assertTrue(report["robots_txt"])
        self.assertEqual(export["guide_count"], 36)
        self.assertFalse(export["safety"]["diagnostic"])
        self.assertFalse(export["safety"]["medication_advice"])

        pages = sorted((site / "tips").rglob("index.html"))
        self.assertEqual(len(pages), 49)
        titles: set[str] = set()
        descriptions: set[str] = set()
        canonicals: set[str] = set()
        banned = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
        for page in pages:
            text = page.read_text(encoding="utf-8")
            title = re.search(r"<title>(.*?)</title>", text, re.S)
            description = re.search(r'<meta name="description" content="([^"]+)"', text)
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', text)
            self.assertIsNotNone(title, page)
            self.assertIsNotNone(description, page)
            self.assertIsNotNone(canonical, page)
            self.assertNotIn(title.group(1), titles)
            self.assertNotIn(description.group(1), descriptions)
            self.assertNotIn(canonical.group(1), canonicals)
            titles.add(title.group(1))
            descriptions.add(description.group(1))
            canonicals.add(canonical.group(1))

            self.assertEqual(text.count("<h1"), 1, page)
            self.assertIn('<meta name="keywords"', text)
            self.assertIn('name="robots" content="index,follow', text)
            self.assertIn('property="og:title"', text)
            self.assertIn('name="twitter:card"', text)
            self.assertIn('hreflang="ar"', text)
            self.assertIn('hreflang="x-default"', text)
            self.assertIn('class="skip-link"', text)
            self.assertIn('data-platform-shell="header"', text)
            self.assertIn('data-platform-shell="footer"', text)
            self.assertNotRegex(text, banned)
            self.assertNotRegex(text, r'href="/(?!pterminology-site/|/)')
            self.assertNotRegex(text, r"\b(?:fetch|XMLHttpRequest|sendBeacon|WebSocket)\s*\(")

            scripts = re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', text, re.S
            )
            self.assertEqual(len(scripts), 1, page)
            parsed = json.loads(scripts[0])
            self.assertEqual(parsed["@context"], "https://schema.org")

        sitemap = ET.parse(site / "sitemap-tips.xml").getroot()
        locations = [node.text for node in sitemap.findall("{*}url/{*}loc")]
        self.assertEqual(len(locations), 49)
        self.assertEqual(len(locations), len(set(locations)))
        self.assertIn(BASE + "tips/", locations)
        self.assertIn(BASE + "tips/help-now/", locations)
        self.assertIn(BASE + "tips/categories/children-teens/", locations)
        self.assertIn(BASE + "tips/grounding-after-panic/", locations)

        root_sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
        self.assertEqual(root_sitemap.count(BASE + "sitemap-tips.xml"), 1)

    def test_idempotent_rebuild(self) -> None:
        site = self.build()
        first = (site / "tips/index.html").read_text(encoding="utf-8")
        subprocess.run([sys.executable, str(PUBLISHER), str(site)], check=True)
        second = (site / "tips/index.html").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(len(list((site / "tips").rglob("index.html"))), 49)


if __name__ == "__main__":
    unittest.main()
