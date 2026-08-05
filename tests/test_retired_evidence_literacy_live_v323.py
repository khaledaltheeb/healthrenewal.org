from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/verify-evidence-literacy-library-live-v323.yml"


class RetainedEvidenceLiteracyLiveV323Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_historical_workflow_is_retained(self) -> None:
        self.assertTrue(WORKFLOW.exists())
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("archived manual verifier", self.text)

    def test_obsolete_automatic_triggers_are_disabled(self) -> None:
        self.assertNotIn("workflow_run:", self.text)
        self.assertNotIn("schedule:", self.text)
        self.assertNotIn("pull_request:", self.text)

    def test_removed_report_is_not_a_runtime_dependency(self) -> None:
        self.assertNotIn("api/evidence-literacy-library-v322.json", self.text)
        self.assertIn("sitemap-library.xml", self.text)
        self.assertIn("deployment.json", self.text)

    def test_manual_verifier_keeps_semantic_publication_checks(self) -> None:
        for marker in (
            "library/evidence-literacy/",
            "how-to-read-systematic-review",
            "certainty-of-evidence-and-recommendations",
            "study-designs-bias-and-causality",
            "appraise-clinical-guideline",
            "BreadcrumbList",
            "canonical",
        ):
            self.assertIn(marker, self.text)


if __name__ == "__main__":
    unittest.main()
