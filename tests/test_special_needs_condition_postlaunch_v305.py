from __future__ import annotations

import copy
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


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SpecialNeedsConditionPostlaunchV305Tests(unittest.TestCase):
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
        config = postlaunch305.load_config()
        links = [*config["common_guides"]]
        for slug in postlaunch305.SLUGS:
            links.extend(config["conditions"][slug]["related_guides"])
        for href in {item["href"] for item in links}:
            target = postlaunch305.route_target(site, href)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                '<!doctype html><html lang="ar" dir="rtl"><body><main><h1>دليل عملي</h1></main></body></html>',
                encoding="utf-8",
            )
        return site

    def test_postlaunch_layer_adds_navigation_links_meta_and_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            condition302.publish(site)
            report = postlaunch305.publish(site)

            self.assertEqual(report["version"], 305)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["condition_slugs"], ["autism", "down-syndrome"])
            self.assertEqual(report["related_link_count"], 16)
            self.assertTrue(report["visible_breadcrumbs"])
            self.assertTrue(report["provider_policy_visible"])

            config = postlaunch305.load_config()
            for slug in postlaunch305.SLUGS:
                page = (site / "special-needs" / slug / "index.html").read_text(encoding="utf-8")
                self.assertEqual(page.count(f"{postlaunch305.META_MARKER}:start"), 1)
                self.assertEqual(page.count(f"{postlaunch305.BREADCRUMB_MARKER}:start"), 1)
                self.assertEqual(page.count(f"{postlaunch305.CONTENT_MARKER}:start"), 1)
                self.assertEqual(page.count(f"{postlaunch305.STYLE_MARKER}:start"), 1)
                self.assertIn('name="twitter:card" content="summary_large_image"', page)
                self.assertIn('aria-label="مسار التنقل"', page)
                self.assertIn('aria-current="page"', page)
                self.assertIn('id="provider-listing-policy"', page)
                self.assertIn(":focus-visible", page)
                self.assertEqual(page.count("<h1"), 1)
                ids = re.findall(r'\bid="([^"]+)"', page)
                self.assertEqual(len(ids), len(set(ids)))
                links = [*config["conditions"][slug]["related_guides"], *config["common_guides"]]
                for item in links:
                    self.assertEqual(page.count(f'href="{item["href"]}"'), 1)

            api = json.loads(
                (site / "api" / "special-needs-condition-postlaunch-v305.json").read_text(encoding="utf-8")
            )
            self.assertEqual(api["related_link_count"], 16)
            self.assertEqual(len(api["pages"]), 2)

    def test_postlaunch_publication_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            condition302.publish(site)
            first = postlaunch305.publish(site)
            tracked = [
                site / "special-needs" / "autism" / "index.html",
                site / "special-needs" / "down-syndrome" / "index.html",
                site / "api" / "special-needs-condition-postlaunch-v305.json",
            ]
            before = [digest(path) for path in tracked]
            second = postlaunch305.publish(site)
            after = [digest(path) for path in tracked]
            self.assertEqual(first["related_link_count"], second["related_link_count"])
            self.assertEqual(before, after)

    def test_missing_related_route_blocks_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            condition302.publish(site)
            missing = site / "special-needs" / "provider-center-quality-selection-checklist" / "index.html"
            missing.unlink()
            with self.assertRaises(SystemExit):
                postlaunch305.publish(site)

    def test_unexpected_cross_condition_duplicate_is_rejected(self) -> None:
        original_config_path = postlaunch305.CONFIG
        with tempfile.TemporaryDirectory() as tmp:
            config = copy.deepcopy(postlaunch305.load_config())
            config["conditions"]["down-syndrome"]["related_guides"].append(
                copy.deepcopy(config["conditions"]["autism"]["related_guides"][0])
            )
            path = Path(tmp) / "invalid-postlaunch.json"
            path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
            postlaunch305.CONFIG = path
            try:
                with self.assertRaises(SystemExit):
                    postlaunch305.load_config()
            finally:
                postlaunch305.CONFIG = original_config_path


if __name__ == "__main__":
    unittest.main()
