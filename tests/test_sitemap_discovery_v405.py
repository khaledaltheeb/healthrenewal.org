from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rebuild_sitemap_discovery_v405.py"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
BASE = "https://healthrenewal.org"


def load_builder():
    spec = importlib.util.spec_from_file_location("rebuild_sitemap_discovery_v405", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load sitemap discovery v405")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_urlset(path: Path, urls: list[str]) -> None:
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{NS}}}url")
        location = ET.SubElement(node, f"{{{NS}}}loc")
        location.text = url
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


class SitemapDiscoveryV405Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()

    def make_site(self, root: Path) -> list[str]:
        routes = [f"special-needs/practical/guide-{index:03d}/" for index in range(100)]
        urls = [f"{BASE}/{route}" for route in routes]
        (root / "api").mkdir(parents=True, exist_ok=True)
        (root / "api/undercovered-content-v401.json").write_text(
            json.dumps(
                {
                    "status": "passed",
                    "page_count": 100,
                    "routes": routes,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        write_urlset(root / "sitemap.xml", [f"{BASE}/"])
        write_urlset(root / "sitemap-special-needs.xml", urls)
        write_urlset(root / "sitemap-family-special-needs.xml", urls[:60])
        write_urlset(root / "sitemap-family-learning-paths.xml", [f"{BASE}/learning-paths/example/"])
        write_urlset(root / "sitemap-family-main.xml", [f"{BASE}/sectors/child/guides/example/"])
        write_urlset(root / "sitemap-library.xml", [f"{BASE}/library/"])
        (root / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        return routes

    def test_publish_builds_complete_index_and_robots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            self.make_site(site)
            report = self.builder.publish(site)

            self.assertEqual(report["version"], 405)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["undercovered_routes_exposed"], 100)
            self.assertEqual(report["undercovered_routes_missing"], [])
            self.assertGreaterEqual(report["sitemap_count"], 6)
            self.assertTrue(all(report["quality_gates"].values()))

            index = ET.parse(site / "sitemap-index.xml").getroot()
            locations = [
                (node.text or "").strip()
                for node in index.findall("{*}sitemap/{*}loc")
            ]
            self.assertEqual(len(locations), len(set(locations)))
            self.assertIn(f"{BASE}/sitemap-special-needs.xml", locations)
            self.assertIn(f"{BASE}/sitemap-family-special-needs.xml", locations)
            self.assertIn(f"{BASE}/sitemap-family-learning-paths.xml", locations)
            self.assertIn(f"{BASE}/sitemap-family-main.xml", locations)
            self.assertIn(f"{BASE}/sitemap-library.xml", locations)

            robots = (site / "robots.txt").read_text(encoding="utf-8")
            self.assertIn(f"Sitemap: {BASE}/sitemap-index.xml", robots)
            self.assertIn(f"Sitemap: {BASE}/sitemap.xml", robots)

    def test_repeated_publish_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            self.make_site(site)
            first = self.builder.publish(site)
            index_first = (site / "sitemap-index.xml").read_bytes()
            robots_first = (site / "robots.txt").read_bytes()
            report_first = (site / "api/sitemap-discovery-v405.json").read_bytes()

            second = self.builder.publish(site)
            self.assertEqual(first, second)
            self.assertEqual(index_first, (site / "sitemap-index.xml").read_bytes())
            self.assertEqual(robots_first, (site / "robots.txt").read_bytes())
            self.assertEqual(report_first, (site / "api/sitemap-discovery-v405.json").read_bytes())

    def test_invalid_required_sitemap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            self.make_site(site)
            (site / "sitemap-special-needs.xml").write_text("<broken>", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.builder.publish(site)


if __name__ == "__main__":
    unittest.main()
