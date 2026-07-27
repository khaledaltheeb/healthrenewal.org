from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import diagnose_special_needs_guides_v221 as diagnose


class MowatWilsonKleefstraIntegrationV326Tests(unittest.TestCase):
    def valid_report(self) -> dict:
        return {
            "version": 326,
            "status": "passed",
            "cluster_slug": "genetic-developmental-syndromes",
            "previous_condition_count": 7,
            "added_condition_count": 2,
            "total_condition_count": 9,
            "added_condition_slugs": ["mowat-wilson-syndrome", "kleefstra-syndrome"],
            "all_condition_slugs": [
                "rett-syndrome",
                "fragile-x-syndrome",
                "angelman-syndrome",
                "williams-syndrome",
                "prader-willi-syndrome",
                "smith-magenis-syndrome",
                "pitt-hopkins-syndrome",
                "mowat-wilson-syndrome",
                "kleefstra-syndrome",
            ],
            "generated_pages": [
                "special-needs/genetic-developmental-syndromes/index.html",
                "special-needs/mowat-wilson-syndrome/index.html",
                "special-needs/kleefstra-syndrome/index.html",
            ],
            "source_count": 14,
            "section_count": 14,
            "faq_count": 10,
            "minimum_condition_words": 1800,
            "cluster_expanded": True,
            "hub_link_updated": True,
            "sitemap_registered": True,
            "reviewed_at": "2026-07-27",
            "next_review_due": "2027-01-27",
            "external_clinical_review_completed": False,
            "content_source": "content/v326/mowat-wilson-kleefstra-guides-ar.json",
        }

    def test_integrates_fourth_batch_and_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "api").mkdir()
            original_site = diagnose.SITE
            diagnose.SITE = site
            try:
                report = {
                    "condition_hubs": {
                        "new_genetic_developmental_conditions": {"version": 323, "condition_count": 3},
                        "williams_prader_willi_expansion": {"version": 324, "added_condition_count": 2},
                        "smith_magenis_pitt_hopkins_expansion": {"version": 325, "added_condition_count": 2},
                    },
                    "additional_condition_page_count": 3,
                    "second_condition_batch_page_count": 2,
                    "third_condition_batch_page_count": 2,
                    "total_new_condition_page_count": 7,
                    "new_condition_guides_contract": 323,
                    "expanded_condition_guides_contract": 324,
                    "third_condition_guides_contract": 325,
                }
                integrated = diagnose.integrate_fourth_conditions(report, self.valid_report())
            finally:
                diagnose.SITE = original_site

            self.assertEqual(integrated["additional_condition_page_count"], 3)
            self.assertEqual(integrated["second_condition_batch_page_count"], 2)
            self.assertEqual(integrated["third_condition_batch_page_count"], 2)
            self.assertEqual(integrated["fourth_condition_batch_page_count"], 2)
            self.assertEqual(integrated["total_new_condition_page_count"], 9)
            self.assertEqual(integrated["fourth_condition_guides_contract"], 326)
            saved = json.loads((site / "api" / "special-needs-guides-v221.json").read_text(encoding="utf-8"))
            expansion = saved["condition_hubs"]["mowat_wilson_kleefstra_expansion"]
            self.assertEqual(expansion["added_condition_slugs"], ["mowat-wilson-syndrome", "kleefstra-syndrome"])
            self.assertEqual(expansion["total_condition_count"], 9)
            self.assertFalse(expansion["external_clinical_review_completed"])

    def test_rejects_shallow_overreviewed_unwired_or_bad_count(self) -> None:
        shallow = self.valid_report()
        shallow["minimum_condition_words"] = 100
        with self.assertRaises(SystemExit):
            diagnose.integrate_fourth_conditions({}, shallow)

        overreviewed = self.valid_report()
        overreviewed["external_clinical_review_completed"] = True
        with self.assertRaises(SystemExit):
            diagnose.integrate_fourth_conditions({}, overreviewed)

        unwired = self.valid_report()
        unwired["sitemap_registered"] = False
        with self.assertRaises(SystemExit):
            diagnose.integrate_fourth_conditions({}, unwired)

        bad_count = self.valid_report()
        bad_count["total_condition_count"] = 8
        with self.assertRaises(SystemExit):
            diagnose.integrate_fourth_conditions({}, bad_count)


if __name__ == "__main__":
    unittest.main()
