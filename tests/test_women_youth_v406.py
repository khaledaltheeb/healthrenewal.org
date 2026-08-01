from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_women_youth_v406.py"


def load_publisher():
    spec = importlib.util.spec_from_file_location("publish_women_youth_v406", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load v406 publisher")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class WomenYouthV406Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publisher = load_publisher()

    def test_catalog_contract(self) -> None:
        catalog = self.publisher.load_catalog()
        self.publisher.validate_catalog(catalog)
        self.assertEqual(catalog["version"], 406)
        self.assertEqual(catalog["distribution"], {"women": 15, "youth": 15})
        self.assertEqual(len(catalog["pages"]), 30)
        self.assertFalse(catalog["external_specialist_review_completed"])

    def test_publish_generates_thirty_deep_specialized_pages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            report = self.publisher.publish(site)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["page_count"], 30)
            self.assertEqual(report["hub_count"], 2)
            self.assertEqual(report["distribution"], {"women": 15, "youth": 15})
            self.assertEqual(report["unique_routes"], 30)
            self.assertGreaterEqual(report["minimum_words"], 1800)
            self.assertGreaterEqual(report["minimum_h2"], 18)
            self.assertGreaterEqual(report["minimum_citations"], 3)
            self.assertGreaterEqual(report["minimum_topic_mentions"], 16)
            self.assertEqual(report["specialized_safety_pages"], 30)
            self.assertTrue(all(report["quality_gates"].values()))

            for route in report["routes"]:
                source = (site / route / "index.html").read_text(encoding="utf-8")
                self.assertIn('data-content-engine="v406"', source)
                self.assertIn("حدود الاستخدام والقرار الآمن", source)
                self.assertIn('class="notice topic-check"', source)
                self.assertIn("المراجعة الخارجية المتخصصة موصى بها", source)
                self.assertNotRegex(source, self.publisher.FORBIDDEN)
                for phrase in self.publisher.GENERIC_PHRASES:
                    self.assertNotIn(phrase, source)

            for section, expected in (("women", 15), ("youth", 15)):
                hub = (site / "sectors" / section / "index.html").read_text(encoding="utf-8")
                self.assertIn('data-content-engine="v406"', hub)
                self.assertEqual(hub.count('class="card"'), expected)
                sitemap = ET.parse(site / self.publisher.SITEMAPS[section]).getroot()
                urls = [(node.text or "").strip() for node in sitemap.findall("{*}url/{*}loc")]
                self.assertEqual(len(urls), expected + 1)
                self.assertEqual(len(urls), len(set(urls)))

    def test_repeated_publish_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            first = self.publisher.publish(site)
            tracked = [
                site / first["routes"][0] / "index.html",
                site / first["routes"][-1] / "index.html",
                site / "sectors/women/index.html",
                site / "sectors/youth/index.html",
                site / "sitemap-sector-women.xml",
                site / "sitemap-sector-youth.xml",
                site / "api/women-youth-expansion-v406.json",
            ]
            before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            second = self.publisher.publish(site)
            after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            self.assertEqual(first, second)
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
