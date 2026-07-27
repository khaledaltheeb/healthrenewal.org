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


class WilliamsPraderWilliIntegrationV324Tests(unittest.TestCase):
    def valid_report(self) -> dict:
        return {
            "version": 324,
            "status": "passed",
            "cluster_slug": "genetic-developmental-syndromes",
            "base_condition_count": 3,
            "added_condition_count": 2,
            "total_condition_count": 5,
            "added_condition_slugs": ["williams-syndrome", "prader-willi-syndrome"],
            "all_condition_slugs": [
                "rett-syndrome",
                "fragile-x-syndrome",
                "angelman-syndrome",
                "williams-syndrome",
                "prader-willi-syndrome",
            ],
            "generated_pages": [
                "special-needs/genetic-developmental-syndromes/index.html",
                "special-needs/williams-syndrome/index.html",
                "special-needs/prader-willi-syndrome/index.html",
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
            "content_source": "content/v324/williams-prader-willi-guides-ar.json",
        }

    def test_integrates_second_batch_without_overwriting_v323_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "api").mkdir()
            original_site = diagnose.SITE
            diagnose.SITE = site
            try:
                report = {
                    "condition_hubs": {
                        "new_genetic_developmental_conditions": {"version": 323, "condition_count": 3}
                    },
                    "additional_condition_page_count": 3,
                    "new_condition_guides_contract": 323,
                }
                integrated = diagnose.integrate_extended_conditions(report, self.valid_report())
            finally:
                diagnose.SITE = original_site

            self.assertEqual(integrated["additional_condition_page_count"], 3)
            self.assertEqual(integrated["second_condition_batch_page_count"], 2)
            self.assertEqual(integrated["total_new_condition_page_count"], 5)
            self.assertEqual(integrated["expanded_condition_guides_contract"], 324)
            saved = json.loads((site / "api" / "special-needs-guides-v221.json").read_text(encoding="utf-8"))
            expansion = saved["condition_hubs"]["williams_prader_willi_expansion"]
            self.assertEqual(expansion["added_condition_slugs"], ["williams-syndrome", "prader-willi-syndrome"])
            self.assertEqual(expansion["total_condition_count"], 5)
            self.assertFalse(expansion["external_clinical_review_completed"])

    def test_rejects_shallow_overreviewed_or_unwired_expansion(self) -> None:
        shallow = self.valid_report()
        shallow["minimum_condition_words"] = 100
        with self.assertRaises(SystemExit):
            diagnose.integrate_extended_conditions({}, shallow)

        overreviewed = self.valid_report()
        overreviewed["external_clinical_review_completed"] = True
        with self.assertRaises(SystemExit):
            diagnose.integrate_extended_conditions({}, overreviewed)

        unwired = self.valid_report()
        unwired["sitemap_registered"] = False
        with self.assertRaises(SystemExit):
            diagnose.integrate_extended_conditions({}, unwired)


if __name__ == "__main__":
    unittest.main()
