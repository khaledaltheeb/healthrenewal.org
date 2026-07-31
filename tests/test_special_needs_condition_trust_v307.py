from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_special_needs_condition_hubs_v302 as condition302
import publish_special_needs_condition_postlaunch_v305 as postlaunch305
import publish_special_needs_condition_trust_v307 as trust307


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpecialNeedsConditionTrustV307Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "site"
        (site / "special-needs").mkdir(parents=True)
        (site / "special-needs" / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body><main>'
            '<section class="section" id="method"><h2>المنهجية</h2></section>'
            '</main></body></html>',
            encoding="utf-8",
        )
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/special-needs/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        link_config = postlaunch305.load_config()
        links = [*link_config["common_guides"]]
        for slug in postlaunch305.SLUGS:
            links.extend(link_config["conditions"][slug]["related_guides"])
        for href in {item["href"] for item in links}:
            target = postlaunch305.route_target(site, href)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('<!doctype html><html lang="ar"><body><h1>دليل</h1></body></html>', encoding="utf-8")
        condition302.publish(site)
        postlaunch305.publish(site)
        return site

    def test_trust_layer_adds_visible_faq_schema_review_cycle_and_source_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = trust307.publish(site)
            self.assertEqual(report["version"], 307)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["condition_slugs"], ["autism", "down-syndrome"])
            self.assertEqual(report["faq_count"], 8)
            self.assertTrue(report["faq_schema_visible_match"])
            self.assertFalse(report["external_clinical_review_completed"])

            config = trust307.load_config()
            for slug in trust307.SLUGS:
                page = (site / "special-needs" / slug / "index.html").read_text(encoding="utf-8")
                self.assertEqual(page.count(f"{trust307.STYLE_MARKER}:start"), 1)
                self.assertEqual(page.count(f"{trust307.SCHEMA_MARKER}:start"), 1)
                self.assertEqual(page.count(f"{trust307.CONTENT_MARKER}:start"), 1)
                self.assertIn('"@type": "FAQPage"', page)
                self.assertIn('id="quality-and-faq"', page)
                self.assertIn(config["next_review_due"], page)
                ids = re.findall(r'\bid="([^"]+)"', page)
                self.assertEqual(len(ids), len(set(ids)))
                for faq in config["conditions"][slug]["faqs"]:
                    self.assertEqual(page.count(f'id="{faq["id"]}"'), 1)
                    self.assertEqual(page.count(faq["question"]), 2)
                    for source_id in faq["source_ids"]:
                        self.assertIn(f'href="#{source_id}"', page)

            api = json.loads((site / "api" / "special-needs-condition-trust-v307.json").read_text(encoding="utf-8"))
            self.assertEqual(api["faq_count"], 8)
            self.assertEqual(api["next_review_due"], "2027-01-27")

    def test_trust_publication_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            trust307.publish(site)
            tracked = [
                site / "special-needs" / "autism" / "index.html",
                site / "special-needs" / "down-syndrome" / "index.html",
                site / "api" / "special-needs-condition-trust-v307.json",
            ]
            before = [digest(path) for path in tracked]
            trust307.publish(site)
            after = [digest(path) for path in tracked]
            self.assertEqual(before, after)

    def test_missing_referenced_source_anchor_blocks_faq_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            path = site / "special-needs" / "autism" / "index.html"
            page = path.read_text(encoding="utf-8").replace('id="A9"', 'id="AX"', 1)
            path.write_text(page, encoding="utf-8")
            with self.assertRaises(SystemExit):
                trust307.publish(site)


if __name__ == "__main__":
    unittest.main()
