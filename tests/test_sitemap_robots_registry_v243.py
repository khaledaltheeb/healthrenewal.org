from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_provider_condition_discovery_v238_compat.py"
BASE = "https://healthrenewal.org"


def load_module():
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location("sitemap_registry_v243", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load sitemap registry module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SitemapRobotsRegistryV243Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="sitemap-robots-registry-v243-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        self.module = load_module()
        (self.site / "robots.txt").write_text(
            "User-agent: *\n"
            "Allow: /\n"
            f"Sitemap: {BASE}/sitemap.xml\n"
            f"Sitemap: {BASE}/sitemap-special-needs.xml\n"
            f"Sitemap: {BASE}/sitemap-special-needs.xml\n",
            encoding="utf-8",
        )
        (self.site / "sitemap-provider-assessment.xml").write_text("<urlset/>", encoding="utf-8")
        (self.site / "sitemap-special-needs.xml").write_text("<urlset/>", encoding="utf-8")

    def test_registers_each_existing_discovery_sitemap_exactly_once(self) -> None:
        first = self.module.sync_discovery_sitemaps(self.site)
        second = self.module.sync_discovery_sitemaps(self.site)
        robots = (self.site / "robots.txt").read_text(encoding="utf-8")

        self.assertEqual(first, ["sitemap-provider-assessment.xml", "sitemap-special-needs.xml"])
        self.assertEqual(second, first)
        self.assertEqual(robots.count(f"Sitemap: {BASE}/sitemap-provider-assessment.xml"), 1)
        self.assertEqual(robots.count(f"Sitemap: {BASE}/sitemap-special-needs.xml"), 1)
        self.assertEqual(robots.count(f"Sitemap: {BASE}/sitemap.xml"), 1)
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)

    def test_skips_missing_sitemap_without_inventing_route(self) -> None:
        (self.site / "sitemap-special-needs.xml").unlink()
        registered = self.module.sync_discovery_sitemaps(self.site)
        robots = (self.site / "robots.txt").read_text(encoding="utf-8")

        self.assertEqual(registered, ["sitemap-provider-assessment.xml"])
        self.assertEqual(robots.count(f"Sitemap: {BASE}/sitemap-provider-assessment.xml"), 1)
        self.assertEqual(robots.count(f"Sitemap: {BASE}/sitemap-special-needs.xml"), 0)


if __name__ == "__main__":
    unittest.main()
