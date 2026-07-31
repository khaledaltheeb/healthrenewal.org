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

import publish_special_needs_support_interventions_v318 as support318


class SpecialNeedsSupportInterventionsV318Tests(unittest.TestCase):
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

    def test_publish_generates_two_goal_based_support_guides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = support318.publish(site)

            self.assertEqual(report["version"], 318)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["guide_count"], 2)
            self.assertEqual(report["section_count"], 10)
            self.assertEqual(report["source_count"], 9)
            self.assertEqual(report["plan_step_count"], 10)
            self.assertEqual(report["urgent_item_count"], 6)
            self.assertEqual(report["parent_links_added"], 2)
            self.assertTrue(report["sitemap_registered"])
            self.assertFalse(report["external_clinical_review_completed"])
            self.assertEqual(report["next_review_due"], "2027-01-27")

            expected = {
                "autism-evidence-based-support-plan": {
                    "parent": "autism",
                    "source_ids": ("AI1", "AI2", "AI3", "AI4"),
                    "required": (
                        "ابدأ بهدف وظيفي لا باسم برنامج",
                        "لا توجد متطلبات مسبقة لاستخدام AAC",
                        "لا تستخدم الخلب أو الأكسجين عالي الضغط أو السيكريتين",
                        "إذا لم يتحقق تقدم ذي معنى",
                    ),
                },
                "down-syndrome-development-communication-independence": {
                    "parent": "down-syndrome",
                    "source_ids": ("DI1", "DI2", "DI3", "DI4", "DI5"),
                    "required": (
                        "لا يوجد علاج موحد لمتلازمة داون",
                        "لا توجد متطلبات مسبقة لـ AAC",
                        "الاستقلال ليس غياب الدعم",
                        "لا تفترض أنه جزء طبيعي من متلازمة داون",
                    ),
                },
            }
            for slug, spec in expected.items():
                page_path = site / "special-needs" / slug / "index.html"
                self.assertTrue(page_path.is_file())
                page = page_path.read_text(encoding="utf-8")
                self.assertEqual(page.count("<h1"), 1)
                self.assertEqual(page.count('class="section-card"'), 5)
                self.assertIn("MedicalWebPage", page)
                self.assertIn("BreadcrumbList", page)
                self.assertIn("لم تكتمل مراجعة سريرية خارجية مستقلة", page)
                self.assertIn("2027-01-27", page)
                self.assertIsNone(support318.BANNED.search(page))
                for phrase in spec["required"]:
                    self.assertIn(phrase, page)
                for sid in spec["source_ids"]:
                    self.assertIn(f'id="source-{sid}"', page)

                parent = (site / "special-needs" / spec["parent"] / "index.html").read_text(encoding="utf-8")
                self.assertEqual(parent.count(f'data-support-guide="{slug}"'), 1)
                self.assertEqual(parent.count(f'/special-needs/{slug}/'), 1)

            api = json.loads(
                (site / "api" / "special-needs-support-interventions-v318.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                api["guide_slugs"],
                ["autism-evidence-based-support-plan", "down-syndrome-development-communication-independence"],
            )
            self.assertEqual(api["content_source"], "content/v318/special-needs-support-interventions-ar.json")

            locations = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            for slug in expected:
                self.assertEqual(locations.count(f"{support318.BASE}/special-needs/{slug}/"), 1)
            self.assertEqual(len(locations), len(set(locations)))

    def test_publication_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            support318.publish(site)
            tracked = [
                site / "special-needs" / "autism" / "index.html",
                site / "special-needs" / "down-syndrome" / "index.html",
                site / "special-needs" / "autism-evidence-based-support-plan" / "index.html",
                site / "special-needs" / "down-syndrome-development-communication-independence" / "index.html",
                site / "sitemap-special-needs.xml",
                site / "api" / "special-needs-support-interventions-v318.json",
            ]
            before = [self.digest(path) for path in tracked]
            second = support318.publish(site)
            after = [self.digest(path) for path in tracked]
            self.assertEqual(second["guide_count"], 2)
            self.assertEqual(before, after)

    def test_manifest_rejects_unused_sources(self) -> None:
        payload = support318.read_json(support318.CONTENT)
        payload["guides"][0]["sources"].append(
            {
                "id": "AIX",
                "organization": "Example",
                "title": "Unused",
                "url": "https://example.org/unused-v318",
                "level": "S5",
                "reviewed": "2026-01-01",
            }
        )
        with self.assertRaises(SystemExit):
            support318.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
