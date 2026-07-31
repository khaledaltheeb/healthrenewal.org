from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import publish_special_needs_expansion_v322 as publisher


class SpecialNeedsExpansionV322Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.site = Path(self.temp.name) / "site"
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "api").mkdir()
        (self.site / "special-needs/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>المركز</h1></main></body></html>',
            encoding="utf-8",
        )
        (self.site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'
            + publisher.BASE + '/special-needs/</loc></url></urlset>', encoding="utf-8")
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>'
            + publisher.BASE + '/sitemap-special-needs.xml</loc></sitemap></sitemapindex>', encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_source_contract(self) -> None:
        guides = publisher.validate_payload(publisher.read_json(publisher.CONTENT))
        self.assertEqual({g["slug"] for g in guides}, publisher.EXPECTED_SLUGS)
        self.assertTrue(all(len(g["sections"]) == 8 and len(g["sources"]) >= 4 for g in guides))
        self.assertFalse(publisher.BANNED.search(json.dumps(guides, ensure_ascii=False)))

    def test_publish_depth_discovery_and_idempotence(self) -> None:
        publisher.publish(self.site)
        report = publisher.publish(self.site)
        self.assertEqual((report["guide_count"], report["section_count"], report["source_count"]), (5, 40, 25))
        self.assertGreaterEqual(report["minimum_rendered_words"], 1200)
        self.assertGreaterEqual(report["minimum_h2"], 11)
        self.assertGreaterEqual(report["minimum_citations"], 4)
        hub = (self.site / "special-needs/index.html").read_text(encoding="utf-8")
        self.assertEqual(hub.count(publisher.MARKER_START), 1)
        for slug in publisher.EXPECTED_SLUGS:
            self.assertEqual(hub.count(f"/special-needs/{slug}/"), 2)
            page = (self.site / "special-needs" / slug / "index.html").read_text(encoding="utf-8")
            self.assertEqual(page.count("<h1"), 1)
            self.assertGreaterEqual(len(re.findall(r"<h2\b", page)), 11)
            self.assertGreaterEqual(publisher.visible_words(page), 1200)
            self.assertFalse(any(token in page for token in publisher.FORBIDDEN_RUNTIME))
        urls = [(n.text or "").strip() for n in ET.parse(self.site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")]
        self.assertTrue(all(urls.count(f"{publisher.BASE}/special-needs/{slug}/") == 1 for slug in publisher.EXPECTED_SLUGS))

    def test_deployment_digest_refresh(self) -> None:
        files = {"index.html": "<h1>root</h1>", "manifest.webmanifest": "{}", "sw.js": "const x=1;"}
        for name, content in files.items():
            (self.site / name).write_text(content, encoding="utf-8")
        (self.site / "sitemap.xml").write_text(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'
            + publisher.BASE + '/</loc></url></urlset>', encoding="utf-8")
        names = ("index.html", "sitemap.xml", "manifest.webmanifest", "sw.js")
        (self.site / "deployment.json").write_text(json.dumps({
            "schema_version": 29, "commit": "0" * 40, "pwa_pages": 1,
            "artifacts": {name: {"sha256": "stale", "bytes": 0} for name in names},
        }), encoding="utf-8")
        self.assertTrue(publisher.publish(self.site)["deployment_evidence_refreshed"])
        evidence = json.loads((self.site / "deployment.json").read_text(encoding="utf-8"))["artifacts"]
        for name in names:
            target = self.site / name
            self.assertEqual(evidence[name]["sha256"], hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual(evidence[name]["bytes"], target.stat().st_size)


if __name__ == "__main__":
    unittest.main()
