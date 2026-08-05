from __future__ import annotations

import json
import unittest
from pathlib import Path


AUDIT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "recovery-audits"
    / "content-version-audit-2026-08-06.json"
)


class ContentVersionRecoveryAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    def test_policy_forbids_loss_and_wholesale_legacy_workflows(self) -> None:
        policy = self.audit["policy"]
        self.assertTrue(policy["preferLongestCompleteVersion"])
        self.assertTrue(policy["mergeUniqueUsefulMaterial"])
        self.assertFalse(policy["deleteOrShortenContent"])
        self.assertFalse(policy["importLegacyDeploymentWorkflows"])

    def test_every_compared_path_has_a_reasoned_decision(self) -> None:
        compared = []
        for branch in self.audit["auditedBranches"]:
            self.assertTrue(branch["branch"])
            self.assertTrue(branch["disposition"])
            self.assertTrue(branch["reason"])
            for item in branch.get("comparedPaths", []):
                self.assertTrue(item["path"])
                self.assertTrue(item["decision"])
                self.assertGreaterEqual(len(item["reason"]), 40)
                compared.append(item["path"])
        self.assertEqual(len(compared), self.audit["summary"]["pathsCompared"])
        self.assertEqual(len(compared), len(set(compared)))

    def test_no_legacy_deployment_workflow_is_marked_for_import(self) -> None:
        workflow_decisions = []
        for branch in self.audit["auditedBranches"]:
            for item in branch.get("comparedPaths", []):
                if item["path"].startswith(".github/workflows/"):
                    workflow_decisions.append(item["decision"])
        self.assertEqual(workflow_decisions, ["do-not-import", "do-not-import"])

    def test_summary_is_consistent(self) -> None:
        summary = self.audit["summary"]
        self.assertEqual(summary["branchesAudited"], len(self.audit["auditedBranches"]))
        self.assertEqual(summary["contentFilesRestored"], 0)
        self.assertFalse(summary["contentLossDetected"])
        self.assertEqual(summary["unsafeLegacyWorkflowsRejected"], 2)
        self.assertGreaterEqual(len(summary["nextCandidates"]), 3)


if __name__ == "__main__":
    unittest.main()
