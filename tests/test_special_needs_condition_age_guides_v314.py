from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_special_needs_condition_age_guides_v314 as age314


class SpecialNeedsConditionAgeGuidesV314Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "site"
        for parent in ("autism", "down-syndrome"):
            target = site / "special-needs" / parent / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                '<!doctype html><html lang="ar" dir="rtl"><body><main>'
                '<section><h1>الدليل الشامل</h1></section>'
                '<section class="source-area" id="sources"><h2>المراجع</h2></section>'
                '</main></body></html>',
                encoding="utf-8",
            )
        (site / "sitemap-special-needs.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://healthrenewal.org/special-needs/autism/</loc></url>'
            '<url><loc>https://healthrenewal.org/special-needs/down-syndrome/</loc></url>'
            '</urlset>',
            encoding="utf-8",
        )
        return site

    @staticmethod
    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_publish_generates_two_evidence_bounded_age_guides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = age314.publish(site)

            self.assertEqual(report["version"], 314)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["guide_count"], 2)
            self.assertEqual(report["stage_count"], 8)
            self.assertEqual(report["source_count"], 7)
            self.assertEqual(report["parent_links_added"], 2)
            self.assertFalse(report["external_clinical_review_completed"])
            self.assertEqual(report["next_review_due"], "2027-01-27")

            expected = {
                "autism-signs-by-age": {
                    "parent": "autism",
                    "title": "علامات التوحد حسب العمر",
                    "minimum_urgent": 3,
                },
                "down-syndrome-health-by-age": {
                    "parent": "down-syndrome",
                    "title": "متابعة صحة متلازمة داون حسب العمر",
                    "minimum_urgent": 5,
                },
            }
            for slug, spec in expected.items():
                page_path = site / "special-needs" / slug / "index.html"
                self.assertTrue(page_path.is_file())
                page = page_path.read_text(encoding="utf-8")
                self.assertEqual(page.count("<h1"), 1)
                self.assertEqual(page.count('class="stage"'), 4)
                self.assertIn("MedicalWebPage", page)
                self.assertIn("BreadcrumbList", page)
                self.assertIn(spec["title"], page)
                self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", page)
                self.assertIn("2027-01-27", page)
                self.assertIsNone(age314.BANNED.search(page))
                parent = (site / "special-needs" / spec["parent"] / "index.html").read_text(encoding="utf-8")
                self.assertEqual(parent.count(f'data-age-guide="{slug}"'), 1)
                self.assertEqual(parent.count(f'/special-needs/{slug}/'), 1)

            autism = (site / "special-needs" / "autism-signs-by-age" / "index.html").read_text(encoding="utf-8")
            down = (site / "special-needs" / "down-syndrome-health-by-age" / "index.html").read_text(encoding="utf-8")
            for sid in ("AU1", "AU2", "AU3", "AU4"):
                self.assertIn(f'id="source-{sid}"', autism)
            for sid in ("DSA1", "DSA2", "DSA3"):
                self.assertIn(f'id="source-{sid}"', down)

            api = json.loads(
                (site / "api" / "special-needs-condition-age-guides-v314.json").read_text(encoding="utf-8")
            )
            self.assertEqual(api["guide_slugs"], ["autism-signs-by-age", "down-syndrome-health-by-age"])
            self.assertEqual(api["content_source"], "content/v314/special-needs-condition-age-guides-ar.json")

            locations = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            for slug in expected:
                url = f"{age314.BASE}/special-needs/{slug}/"
                self.assertEqual(locations.count(url), 1)
            self.assertEqual(len(locations), len(set(locations)))

    def test_publication_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            age314.publish(site)
            tracked = [
                site / "special-needs" / "autism" / "index.html",
                site / "special-needs" / "down-syndrome" / "index.html",
                site / "special-needs" / "autism-signs-by-age" / "index.html",
                site / "special-needs" / "down-syndrome-health-by-age" / "index.html",
                site / "sitemap-special-needs.xml",
                site / "api" / "special-needs-condition-age-guides-v314.json",
            ]
            before = [self.digest(path) for path in tracked]
            second = age314.publish(site)
            after = [self.digest(path) for path in tracked]
            self.assertEqual(second["guide_count"], 2)
            self.assertEqual(before, after)

    def test_manifest_rejects_unknown_or_unused_sources(self) -> None:
        payload = age314.read_json(age314.CONTENT)
        payload["guides"][0]["sources"].append(
            {
                "id": "AUX",
                "organization": "Example",
                "title": "Unused source",
                "url": "https://example.org/unused",
                "level": "S5",
                "reviewed": "2026-01-01",
            }
        )
        with self.assertRaises(SystemExit):
            age314.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
