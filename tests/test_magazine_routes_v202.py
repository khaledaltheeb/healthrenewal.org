from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_magazine_v202.py"
SOURCE = ROOT / "magazine"
SOURCE_SITEMAP = ROOT / "sitemap.xml"

spec = importlib.util.spec_from_file_location("publish_magazine_v202_test", PUBLISHER)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class MagazineRoutesV202Tests(unittest.TestCase):
    def fixture(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="magazine-v202-"))
        shutil.copy2(SOURCE_SITEMAP, site / "sitemap.xml")
        self.addCleanup(shutil.rmtree, site, True)
        return site

    def test_recursive_publisher_keeps_nested_studies_and_builds_one_index(self) -> None:
        site = self.fixture()
        report = mod.publish(site)

        self.assertGreater(report["published_study_pages"], 79)
        self.assertEqual(report["index_cards"], report["published_study_pages"])
        self.assertEqual(report["wired_study_pages"], report["published_study_pages"])
        self.assertEqual(report["unwired_research_pages"], 0)
        self.assertTrue(report["non_destructive"])
        self.assertEqual(report["validation"]["noindex_pages"], 0)
        self.assertEqual(report["validation"]["duplicate_canonical_urls"], 0)

        nested_rel = Path("pediatric-oncology/theses/cd28-car-t-t-all-farber-2026/index.html")
        self.assertTrue((site / "magazine" / nested_rel).is_file())
        self.assertEqual(
            (site / "magazine" / nested_rel).read_bytes(),
            (SOURCE / nested_rel).read_bytes(),
            "Publisher must preserve the existing nested study page byte-for-byte",
        )

        index = (site / "magazine" / "index.html").read_text(encoding="utf-8")
        farber_url = "https://healthrenewal.org/magazine/pediatric-oncology/theses/cd28-car-t-t-all-farber-2026/"
        self.assertIn(f'href="{farber_url}"', index)
        self.assertEqual(index.count('class="card"'), report["index_cards"])
        self.assertNotIn("noindex", index.lower())

        output_html = list((site / "magazine").rglob("*.html"))
        source_html = list(SOURCE.rglob("*.html"))
        self.assertGreaterEqual(len(output_html), len(source_html))

    def test_sitemap_contains_every_discovered_study_canonical_once(self) -> None:
        site = self.fixture()
        report = mod.publish(site)
        tree = ET.parse(site / "sitemap-magazine.xml")
        urls = [(node.text or "").strip() for node in tree.getroot().findall("{*}url/{*}loc")]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(len(urls), report["sitemap"]["child_urls"])
        self.assertEqual(len(urls), report["published_study_pages"] + 1)
        for article in report["articles"]:
            self.assertEqual(urls.count(article["url"]), 1, article["source_path"])

    def test_api_report_exposes_source_and_completeness_without_false_verification(self) -> None:
        site = self.fixture()
        report = mod.publish(site)
        api = json.loads((site / "api" / "magazine-v202.json").read_text(encoding="utf-8"))
        self.assertEqual(api["version"], 202)
        self.assertEqual(api["published_study_pages"], report["published_study_pages"])
        self.assertEqual(len(api["articles"]), api["published_study_pages"])
        self.assertTrue(any(article["doi"] for article in api["articles"]))
        self.assertTrue(any(article["relative_path"].endswith("/index.html") for article in api["articles"]))
        self.assertTrue(
            all(
                article["bibliographic_status"] != "verified_identifier"
                for article in api["articles"]
            ),
            "Without an authoritative verification report, identifiers must remain pending",
        )

    def test_quality_label_requires_both_complete_structure_and_verified_source(self) -> None:
        self.assertEqual(mod.quality_label("complete", "verified_identifier"), ("موثقة ومكتملة", "verified"))
        self.assertEqual(
            mod.quality_label("incomplete", "verified_identifier"),
            ("المصدر موثق · الصفحة تحتاج استكمالًا", "review"),
        )
        self.assertEqual(
            mod.quality_label("complete", "identifier_present_verification_pending")[1],
            "pending",
        )


if __name__ == "__main__":
    unittest.main()
