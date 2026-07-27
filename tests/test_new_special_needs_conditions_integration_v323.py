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


class NewSpecialNeedsConditionsIntegrationV323Tests(unittest.TestCase):
    def test_diagnostic_entrypoint_integrates_v323_report_honestly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "api").mkdir()
            original_site = diagnose.SITE
            diagnose.SITE = site
            try:
                report = {"condition_hubs": {}, "guide_count": 25}
                conditions = {
                    "version": 323,
                    "status": "passed",
                    "cluster_slug": "genetic-developmental-syndromes",
                    "condition_count": 3,
                    "condition_slugs": ["rett-syndrome", "fragile-x-syndrome", "angelman-syndrome"],
                    "generated_pages": [
                        "special-needs/genetic-developmental-syndromes/index.html",
                        "special-needs/rett-syndrome/index.html",
                        "special-needs/fragile-x-syndrome/index.html",
                        "special-needs/angelman-syndrome/index.html",
                    ],
                    "source_count": 19,
                    "section_count": 21,
                    "faq_count": 15,
                    "minimum_condition_words": 1900,
                    "hub_link_added": True,
                    "sitemap_registered": True,
                    "reviewed_at": "2026-07-27",
                    "next_review_due": "2027-01-27",
                    "external_clinical_review_completed": False,
                    "content_source": "content/v323/new-special-needs-conditions-ar.json",
                }
                integrated = diagnose.integrate_new_conditions(report, conditions)
            finally:
                diagnose.SITE = original_site

            self.assertEqual(integrated["new_condition_guides_contract"], 323)
            self.assertEqual(integrated["additional_condition_page_count"], 3)
            saved = json.loads((site / "api" / "special-needs-guides-v221.json").read_text(encoding="utf-8"))
            self.assertEqual(
                saved["condition_hubs"]["new_genetic_developmental_conditions"]["condition_slugs"],
                conditions["condition_slugs"],
            )
            self.assertFalse(
                saved["condition_hubs"]["new_genetic_developmental_conditions"]["external_clinical_review_completed"]
            )

    def test_integration_rejects_shallow_or_overreviewed_pages(self) -> None:
        base = {
            "version": 323,
            "status": "passed",
            "cluster_slug": "genetic-developmental-syndromes",
            "condition_count": 3,
            "condition_slugs": ["rett-syndrome", "fragile-x-syndrome", "angelman-syndrome"],
            "generated_pages": [],
            "source_count": 19,
            "section_count": 21,
            "faq_count": 15,
            "minimum_condition_words": 100,
            "hub_link_added": True,
            "sitemap_registered": True,
            "reviewed_at": "2026-07-27",
            "next_review_due": "2027-01-27",
            "external_clinical_review_completed": False,
            "content_source": "content/v323/new-special-needs-conditions-ar.json",
        }
        with self.assertRaises(SystemExit):
            diagnose.integrate_new_conditions({}, base)

        base["minimum_condition_words"] = 1900
        base["external_clinical_review_completed"] = True
        with self.assertRaises(SystemExit):
            diagnose.integrate_new_conditions({}, base)


if __name__ == "__main__":
    unittest.main()
