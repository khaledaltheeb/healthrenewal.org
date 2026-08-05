from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OBSOLETE_WORKFLOW = (
    ROOT / ".github/workflows/verify-evidence-literacy-library-live-v323.yml"
)


class RetiredEvidenceLiteracyLiveV323Tests(unittest.TestCase):
    def test_obsolete_live_verifier_is_not_reintroduced(self) -> None:
        """The v323 verifier targeted a generated report no longer shipped by main."""
        self.assertFalse(
            OBSOLETE_WORKFLOW.exists(),
            "Do not restore the stale v323 verifier without restoring its production artifact contract.",
        )

    def test_no_workflow_references_removed_v322_report(self) -> None:
        workflow_dir = ROOT / ".github/workflows"
        offenders: list[str] = []
        marker = "api/evidence-literacy-library-v322.json"
        for pattern in ("*.yml", "*.yaml"):
            for path in workflow_dir.glob(pattern):
                if marker in path.read_text(encoding="utf-8"):
                    offenders.append(path.name)

        self.assertEqual(
            [],
            sorted(offenders),
            "A workflow still depends on the removed v322 live report artifact.",
        )


if __name__ == "__main__":
    unittest.main()
