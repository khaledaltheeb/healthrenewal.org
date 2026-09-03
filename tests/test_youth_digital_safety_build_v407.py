from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V406_SCRIPT = ROOT / "scripts" / "publish_women_youth_v406.py"
V407_SCRIPT = ROOT / "scripts" / "publish_youth_digital_safety_v407.py"
HUB_URL = "https://healthrenewal.org/sectors/youth/digital-safety/"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class YouthDigitalSafetyBuildV407Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v406 = load_module("publish_women_youth_v406_build_test", V406_SCRIPT)
        cls.v407 = load_module("publish_youth_digital_safety_v407_build_test", V407_SCRIPT)

    def test_v407_restores_hub_after_clean_v406_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            base_report = self.v406.publish(site)
            self.assertEqual(base_report["status"], "passed")

            before = (site / "sectors/youth/index.html").read_text(encoding="utf-8")
            self.assertNotIn('href="digital-safety/"', before)
            before_map = ET.parse(site / "sitemap-sector-youth.xml").getroot()
            before_urls = [(node.text or "").strip() for node in before_map.findall("{*}url/{*}loc")]
            self.assertEqual(len(before_urls), 16)

            report = self.v407.publish(site)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["version"], 407)
            self.assertEqual(report["sitemap_count"], 17)
            self.assertFalse(report["sitemap_index_registered"])

            parent = (site / "sectors/youth/index.html").read_text(encoding="utf-8")
            self.assertIn('href="digital-safety/"', parent)
            self.assertIn("السلامة الرقمية وحماية الأطفال واليافعين", parent)
            self.assertEqual(parent.count('class="card"'), 15)
            self.assertIn('"hasPart":{"@type":"CollectionPage"', parent)

            hub = (site / "sectors/youth/digital-safety/index.html").read_text(encoding="utf-8")
            self.assertIn('data-content-engine="v407"', hub)
            self.assertIn("حالة الحقوق والمراجعة الخارجية", hub)

            root = ET.parse(site / "sitemap-sector-youth.xml").getroot()
            urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
            self.assertIn(HUB_URL, urls)
            self.assertEqual(len(urls), 17)
            self.assertEqual(len(urls), len(set(urls)))

    def test_v407_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            self.v406.publish(site)
            first = self.v407.publish(site)
            tracked = [
                site / "sectors/youth/index.html",
                site / "sectors/youth/digital-safety/index.html",
                site / "sitemap-sector-youth.xml",
                site / "api/youth-digital-safety-v407.json",
            ]
            before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            second = self.v407.publish(site)
            after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in tracked]
            self.assertEqual(first, second)
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
