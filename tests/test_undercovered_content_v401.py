from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_undercovered_content_v401.py"


def load_publisher():
    spec = importlib.util.spec_from_file_location("publish_undercovered_content_v401", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load v401 publisher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UndercoveredContentV401Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publisher = load_publisher()

    def make_site(self, root: Path) -> None:
        for hub_path in self.publisher.HUB_PATHS.values():
            target = root / hub_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>Hub</h1></main></body></html>',
                encoding="utf-8",
            )
        namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
        for name in (
            "sitemap-special-needs.xml",
            "sitemap-family-special-needs.xml",
            "sitemap-family-learning-paths.xml",
            "sitemap-family-main.xml",
        ):
            (root / name).write_text(
                f'<?xml version="1.0" encoding="utf-8"?><urlset xmlns="{namespace}"></urlset>',
                encoding="utf-8",
            )

    def test_catalog_contract(self) -> None:
        catalog = json.loads(
            (ROOT / "content" / "v401" / "undercovered-content-ar.json").read_text(encoding="utf-8")
        )
        self.assertEqual(catalog["version"], 401)
        self.assertEqual(catalog["status"], "internally-reviewed")
        self.assertFalse(catalog["external_specialist_review_completed"])
        self.assertEqual(len(catalog["pages"]), 100)
        self.assertEqual(
            catalog["distribution"],
            {"special-needs": 60, "learning-paths": 15, "child": 10, "family": 8, "home": 7},
        )
        self.publisher.validate_catalog()

    def test_publish_one_hundred_deep_pages_and_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            self.make_site(site)
            report = self.publisher.publish(site)

            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["page_count"], 100)
            self.assertEqual(report["unique_routes"], 100)
            self.assertGreaterEqual(report["minimum_words"], 1200)
            self.assertGreaterEqual(report["minimum_h2"], 15)
            self.assertGreaterEqual(report["minimum_citations"], 3)
            self.assertGreater(report["total_words"], 190000)
            self.assertFalse(report["external_specialist_review_completed"])

            for route in report["routes"]:
                page = site / route / "index.html"
                self.assertTrue(page.is_file(), route)
                source = page.read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', source)
                self.assertIn("حدود الاستخدام", source)
                self.assertIn("متى نطلب مساعدة متخصصة؟", source)
                self.assertIn("المراجعة الخارجية المتخصصة موصى بها", source)
                self.assertNotRegex(source, self.publisher.FORBIDDEN)

            expected_sitemap_counts = {
                "sitemap-special-needs.xml": 60,
                "sitemap-family-special-needs.xml": 60,
                "sitemap-family-learning-paths.xml": 15,
                "sitemap-family-main.xml": 25,
            }
            for filename, expected in expected_sitemap_counts.items():
                root = ET.parse(site / filename).getroot()
                locations = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
                self.assertEqual(len(locations), expected)
                self.assertEqual(len(locations), len(set(locations)))

            for section, hub_path in self.publisher.HUB_PATHS.items():
                hub = (site / hub_path).read_text(encoding="utf-8")
                self.assertIn(f"undercovered-content-v401-{section}:start", hub)
                self.assertEqual(
                    hub.count('class="card"'),
                    self.publisher.EXPECTED_DISTRIBUTION[section],
                )

            api = json.loads((site / "api" / "undercovered-content-v401.json").read_text(encoding="utf-8"))
            self.assertEqual(api["page_count"], 100)
            self.assertTrue(all(api["quality_gates"].values()))

    def test_repeated_publish_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            self.make_site(site)
            first = self.publisher.publish(site)
            second = self.publisher.publish(site)
            self.assertEqual(first["routes"], second["routes"])
            for hub_path in self.publisher.HUB_PATHS.values():
                hub = (site / hub_path).read_text(encoding="utf-8")
                self.assertEqual(hub.count("undercovered-content-v401-"), 2)


if __name__ == "__main__":
    unittest.main()
