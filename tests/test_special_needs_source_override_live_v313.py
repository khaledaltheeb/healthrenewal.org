from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verify-special-needs-source-override-live-v313.yml"


class SpecialNeedsSourceOverrideLiveV313Tests(unittest.TestCase):
    def test_workflow_contract_is_complete_and_scoped(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        required = (
            'name: Verify special-needs ASHA source override live v313',
            'workflows: ["Deploy validated main to GitHub Pages"]',
            'MINIMUM_SHA: c3b20e228bc541009887ead3f61603f64d7df27b',
            'special-needs/autism/',
            'special-needs/down-syndrome/',
            'special-needs-condition-hubs-v302.json',
            'special-needs-condition-source-maintenance-v310.json',
            'special-needs-guides-v221.json',
            'https://apps.asha.org/EvidenceMaps/Maps/LandingPage/990772a6-9cd8-4203-a76c-6ccd91eac874',
            'Augmentative and Alternative Communication (AAC) Evidence Map',
            'content/v312/special-needs-condition-source-url-overrides.json',
            'source_url_override_count',
            'sitemap-special-needs.xml',
        )
        missing = [marker for marker in required if marker not in text]
        self.assertEqual(missing, [])
        self.assertIn("github.event_name != 'pull_request'", text)
        self.assertIn("maintenance_overdue", text)
        self.assertIn("obsolete_paths_present", text)

    def test_all_three_failed_asha_paths_are_explicitly_rejected(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        failed = (
            'https://www.asha.org/Practice-Portal/Professional-Issues/Augmentative-and-Alternative-Communication/',
            'https://www.asha.org/practice-portal/professional-issues/augmentative-and-alternative-communication/',
            'https://www.asha.org/NJC/AAC/',
        )
        for url in failed:
            self.assertIn(url, text)


if __name__ == "__main__":
    unittest.main()
