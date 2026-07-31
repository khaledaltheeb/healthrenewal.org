from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.verify_special_needs_deployment_v236 import BASE, BATCHES, V214_SLUGS, verify

SHA = "a" * 40
SLUGS = [f"guide-{index:02d}" for index in range(20)] + list(V214_SLUGS)


class SpecialNeedsDeploymentV236Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="special-needs-deploy-v236-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        (self.site / "api").mkdir(parents=True)
        (self.site / "special-needs").mkdir(parents=True)
        (self.site / "deployment.json").write_text(
            json.dumps({"schema_version": 29, "commit": SHA}), encoding="utf-8"
        )
        report = {
            "version": 221,
            "status": "passed",
            "production_status": "integrated",
            "batches": list(BATCHES),
            "batch_count": 5,
            "guide_count": 25,
            "guide_slugs": SLUGS,
            "production_source_file_count": 25,
            "review_status": "internally-reviewed",
            "external_review_completed": False,
            "external_review": "recommended-not-completed",
        }
        (self.site / "api/special-needs-guides-v221.json").write_text(
            json.dumps(report), encoding="utf-8"
        )
        markers = "".join(
            f"<!-- special-needs-guides-v{version}:start --><!-- special-needs-guides-v{version}:end -->"
            for version in BATCHES
        )
        links = "".join(
            f'<a href="/special-needs/{slug}/">{slug}</a>' for slug in SLUGS
        )
        (self.site / "special-needs/index.html").write_text(
            f"<!doctype html><html lang='ar'><head><meta name='robots' content='index,follow'></head><body><h1>المركز</h1>{markers}{links}</body></html>",
            encoding="utf-8",
        )
        ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
        ET.register_namespace("", ns)
        root = ET.Element(f"{{{ns}}}urlset")
        for slug in SLUGS:
            url = ET.SubElement(root, f"{{{ns}}}url")
            ET.SubElement(url, f"{{{ns}}}loc").text = f"{BASE}/special-needs/{slug}/"
        ET.ElementTree(root).write(self.site / "sitemap-special-needs.xml", encoding="utf-8", xml_declaration=True)
        for slug in SLUGS:
            path = self.site / "special-needs" / slug / "index.html"
            path.parent.mkdir(parents=True)
            path.write_text(
                "<!doctype html><html lang='ar'><head>"
                "<meta name='robots' content='index,follow'>"
                f"<link rel='canonical' href='{BASE}/special-needs/{slug}/'>"
                f"</head><body><h1>{slug}</h1></body></html>",
                encoding="utf-8",
            )

    def test_artifact_contract_verifies_all_twenty_five_pages(self) -> None:
        report = verify(self.site, "artifact", SHA)
        self.assertEqual(report["guide_count"], 25)
        self.assertEqual(report["all_guide_pages_verified"], 25)
        self.assertFalse(report["external_review_completed"])

    def test_live_contract_requires_only_fifth_batch_pages(self) -> None:
        for slug in SLUGS:
            if slug not in V214_SLUGS:
                shutil.rmtree(self.site / "special-needs" / slug)
        report = verify(self.site, "live", SHA)
        self.assertEqual(report["v214_pages_verified"], 5)
        self.assertIsNone(report["all_guide_pages_verified"])

    def test_duplicate_hub_link_is_rejected(self) -> None:
        hub = self.site / "special-needs/index.html"
        text = hub.read_text(encoding="utf-8")
        route = "/special-needs/guide-00/"
        hub.write_text(text + f'<a href="{route}">duplicate</a>', encoding="utf-8")
        with self.assertRaisesRegex(AssertionError, "duplicate guide links"):
            verify(self.site, "artifact", SHA)

    def test_wrong_deployment_sha_is_rejected(self) -> None:
        with self.assertRaisesRegex(AssertionError, "does not match expected SHA"):
            verify(self.site, "artifact", "b" * 40)

    def test_dishonest_external_review_state_is_rejected(self) -> None:
        path = self.site / "api/special-needs-guides-v221.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["external_review_completed"] = True
        path.write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(AssertionError, "report contract mismatch"):
            verify(self.site, "artifact", SHA)


if __name__ == "__main__":
    unittest.main()
