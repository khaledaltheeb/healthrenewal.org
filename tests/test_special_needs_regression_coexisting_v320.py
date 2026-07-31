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

import publish_special_needs_regression_coexisting_v320 as regression320


class SpecialNeedsRegressionCoexistingV320Tests(unittest.TestCase):
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

    def test_publish_generates_two_bounded_regression_guides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            report = regression320.publish(site)

            self.assertEqual(report["version"], 320)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["guide_count"], 2)
            self.assertEqual(report["section_count"], 10)
            self.assertEqual(report["source_count"], 11)
            self.assertEqual(report["action_step_count"], 10)
            self.assertEqual(report["urgent_item_count"], 6)
            self.assertEqual(report["parent_links_added"], 2)
            self.assertTrue(report["sitemap_registered"])
            self.assertTrue(report["dsrd_consensus_limit_visible"])
            self.assertTrue(report["dementia_baseline_limit_visible"])
            self.assertTrue(report["diagnostic_overshadowing_guard"])
            self.assertFalse(report["external_clinical_review_completed"])
            self.assertEqual(report["next_review_due"], "2027-01-27")

            expected = {
                "autism-coexisting-conditions-sudden-change": {
                    "parent": "autism",
                    "source_ids": ("AC1", "AC2", "AC3", "AC4", "AC5"),
                    "required": (
                        "التغير الجديد ليس سمة ثابتة من سمات التوحد",
                        "لا يجوز تفسير الألم أو الاكتئاب أو الصرع أو الإساءة",
                        "منع حجب التشخيص",
                        "لا تواجه المشتبه به بطريقة تعرض الشخص لمزيد من الخطر",
                    ),
                },
                "down-syndrome-regression-dementia-urgent-changes": {
                    "parent": "down-syndrome",
                    "source_ids": ("DR1", "DR2", "DR3", "DR4", "DR5", "DR6"),
                    "required": (
                        "DSRD إطار سريري ناشئ مبني جزئيًا على إجماع خبراء",
                        "لا يملك اختبارًا حاسمًا واحدًا",
                        "بدء أعراض متعددة خلال أقل من 12 أسبوعًا",
                        "لا يساوي تلقائيًا تشخيص الخرف السريري",
                        "لا تطلب قائمة ثابتة من الفحوص للجميع",
                        "بدء تحرٍ سنوي منظم عن ألزهايمر من عمر 40 عامًا",
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
                self.assertIsNone(regression320.BANNED.search(page))
                for phrase in spec["required"]:
                    self.assertIn(phrase, page)
                for sid in spec["source_ids"]:
                    self.assertIn(f'id="source-{sid}"', page)

                parent = (site / "special-needs" / spec["parent"] / "index.html").read_text(encoding="utf-8")
                self.assertEqual(parent.count(f'data-regression-guide="{slug}"'), 1)
                self.assertEqual(parent.count(f'/special-needs/{slug}/'), 1)

            api = json.loads(
                (site / "api" / "special-needs-regression-coexisting-v320.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                api["guide_slugs"],
                ["autism-coexisting-conditions-sudden-change", "down-syndrome-regression-dementia-urgent-changes"],
            )
            self.assertEqual(api["content_source"], "content/v320/special-needs-regression-coexisting-ar.json")

            locations = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-special-needs.xml").getroot().findall("{*}url/{*}loc")
                if node.text
            ]
            for slug in expected:
                self.assertEqual(locations.count(f"{regression320.BASE}/special-needs/{slug}/"), 1)
            self.assertEqual(len(locations), len(set(locations)))

    def test_publication_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make_site(Path(tmp))
            regression320.publish(site)
            tracked = [
                site / "special-needs" / "autism" / "index.html",
                site / "special-needs" / "down-syndrome" / "index.html",
                site / "special-needs" / "autism-coexisting-conditions-sudden-change" / "index.html",
                site / "special-needs" / "down-syndrome-regression-dementia-urgent-changes" / "index.html",
                site / "sitemap-special-needs.xml",
                site / "api" / "special-needs-regression-coexisting-v320.json",
            ]
            before = [self.digest(path) for path in tracked]
            second = regression320.publish(site)
            after = [self.digest(path) for path in tracked]
            self.assertEqual(second["guide_count"], 2)
            self.assertEqual(before, after)

    def test_manifest_rejects_missing_dsrd_limit_or_unused_source(self) -> None:
        payload = regression320.read_json(regression320.CONTENT)
        payload["guides"][1]["warning"] = "تحذير عام لا يوضح حدود الدليل."
        with self.assertRaises(SystemExit):
            regression320.validate_payload(payload)

        payload = regression320.read_json(regression320.CONTENT)
        payload["guides"][0]["sources"].append(
            {
                "id": "ACX",
                "organization": "Example",
                "title": "Unused",
                "url": "https://example.org/unused-v320",
                "level": "S5",
                "reviewed": "2026-01-01",
            }
        )
        with self.assertRaises(SystemExit):
            regression320.validate_payload(payload)


if __name__ == "__main__":
    unittest.main()
