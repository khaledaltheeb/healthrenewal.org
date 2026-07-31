from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_youth_sector_v353.py"
SOURCE = ROOT / "content" / "v353" / "youth-sector-ar.json"

spec = importlib.util.spec_from_file_location("youth_sector_v353", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class YouthSectorSourceV353Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_source_inventory_is_complete_and_official(self) -> None:
        module.validate_source(self.data)
        self.assertEqual(self.data["version"], 353)
        self.assertEqual(len(self.data["guides"]), 16)
        self.assertEqual(len(self.data["collections"]), 4)
        self.assertGreaterEqual(len(self.data["sources"]), 14)
        allowed_hosts = {
            "www.who.int",
            "www.unicef.org",
            "www.nice.org.uk",
            "www.cdc.gov",
            "www.unesco.org",
            "www.hhs.gov",
        }
        for source in self.data["sources"]:
            parsed = urlparse(source["url"])
            self.assertEqual(parsed.scheme, "https", source)
            self.assertIn(parsed.hostname, allowed_hosts, source)

    def test_each_guide_has_unique_content_and_three_sources(self) -> None:
        slugs = [guide["slug"] for guide in self.data["guides"]]
        titles = [guide["title"] for guide in self.data["guides"]]
        summaries = [guide["summary"] for guide in self.data["guides"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(len(titles), len(set(titles)))
        self.assertEqual(len(summaries), len(set(summaries)))
        for guide in self.data["guides"]:
            self.assertGreaterEqual(len(guide["sources"]), 3, guide["slug"])
            for field in ("signals", "assessment", "actions", "avoid", "questions"):
                self.assertGreaterEqual(len(guide[field]), 4, (guide["slug"], field))


class YouthSectorPublisherV353Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="youth-sector-v353-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        shutil.copy2(ROOT / "robots.txt", self.site / "robots.txt")

    def test_publishes_twenty_one_deep_indexable_pages(self) -> None:
        report = module.publish(self.site)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["pages_published"], 21)
        self.assertEqual(report["guide_pages"], 16)
        self.assertEqual(report["collection_pages"], 4)
        self.assertGreaterEqual(report["institutional_sources"], 14)
        self.assertGreaterEqual(report["hub_words"], 1800)
        self.assertGreaterEqual(report["minimum_collection_words"], 700)
        self.assertGreaterEqual(report["minimum_guide_words"], 900)
        self.assertEqual(report["unique_canonicals"], 21)
        self.assertEqual(report["structural_errors"], [])
        self.assertEqual(report["banned_terms_present"], [])

        hub = (self.site / "sectors/youth/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count("<h1"), 1)
        self.assertEqual(hub.count('rel="canonical"'), 1)
        self.assertIn('"@type":"CollectionPage"', hub)
        self.assertIn('"@type":"ItemList"', hub)
        self.assertIn("ستة عشر دليلًا غنيًا", hub)
        self.assertIn("مراجعة تحريرية ومنهجية داخلية", hub)

        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        for guide in data["guides"]:
            page = (
                self.site / "sectors" / "youth" / guide["slug"] / "index.html"
            ).read_text(encoding="utf-8")
            self.assertEqual(page.count("<h1"), 1, guide["slug"])
            self.assertEqual(page.count('rel="canonical"'), 1, guide["slug"])
            self.assertNotIn("noindex", page.lower(), guide["slug"])
            self.assertIn('"Article","MedicalWebPage"', page, guide["slug"])
            self.assertIn("ما يقوله الدليل وما لا يقوله", page, guide["slug"])
            self.assertIn("متى تصبح الاستجابة عاجلة؟", page, guide["slug"])
            self.assertGreaterEqual(page.count("فتح المصدر الرسمي"), 3, guide["slug"])
            self.assertIn("<header", page, guide["slug"])
            self.assertIn("<footer", page, guide["slug"])

        robots = (self.site / "robots.txt").read_text(encoding="utf-8")
        self.assertEqual(robots.count(module.ROBOTS_MARKER), 1)
        self.assertIn("Allow: /sectors/youth/", robots)
        evidence = json.loads(
            (self.site / "api/youth-sector-v353.json").read_text(encoding="utf-8")
        )
        self.assertEqual(evidence, report)

    def test_publication_is_idempotent(self) -> None:
        module.publish(self.site)
        before = {
            path.relative_to(self.site): path.read_bytes()
            for path in self.site.rglob("*")
            if path.is_file() and path.name != module.REPORT_NAME
        }
        second = module.publish(self.site)
        after = {
            path.relative_to(self.site): path.read_bytes()
            for path in self.site.rglob("*")
            if path.is_file() and path.name != module.REPORT_NAME
        }
        self.assertEqual(before, after)
        self.assertFalse(second["robots_updated"])

    def test_rejects_incomplete_guide_inventory(self) -> None:
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        data["guides"].pop()
        with self.assertRaisesRegex(ValueError, "requires_16_guides"):
            module.validate_source(data)


if __name__ == "__main__":
    unittest.main()
