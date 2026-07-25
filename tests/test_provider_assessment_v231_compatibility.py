from __future__ import annotations

import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "provider-assessment-demo" / "institutional-contract-v231-compat.js"
LOADER = ROOT / "provider-assessment-demo" / "institutional-contract-v220.js"


class ProviderAssessmentV231CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.loader = LOADER.read_text(encoding="utf-8")

    def test_progressive_draft_does_not_block_legacy_record_save(self) -> None:
        self.assertIn("يمكن حفظ السجل كمسودة ناقصة", self.script)
        self.assertIn("control.required = false", self.script)
        self.assertIn("غير موثق بعد", self.script)
        self.assertIn('documentationState: "progressive_draft_allowed"', self.script)

    def test_contract_is_attached_only_to_a_new_record(self) -> None:
        self.assertIn("previous", self.script)
        self.assertIn("job.before.has(record.recordId)", self.script)
        self.assertIn("if (!created)", self.script)
        self.assertIn("delete record[key]", self.script)
        self.assertIn("institutionalV220", self.script)

    def test_strict_quality_audit_keeps_ten_decisive_gates(self) -> None:
        for token in (
            "completionStatus", "validityStatus", "limitations", "reviewer",
            "الموافقة والسلامة", "التوصيات والحدود", "المراجع وموعد المراجعة",
        ):
            self.assertIn(token, self.script)
        self.assertIn("passed * 10", self.script)

    def test_legacy_original_ids_are_mapped_without_catalog_duplication(self) -> None:
        self.assertIn('"communication-pathway": "communication-participation"', self.script)
        self.assertIn("ALIASES[data.assessmentId]", self.script)
        self.assertIn("tool(data.assessmentId)", self.script)
        self.assertNotIn("PA_DEMO_DATA.explorers.push", self.script)
        self.assertNotIn('"ADOS-2":', self.script)

    def test_mixed_legacy_and_current_sessions_remain_available(self) -> None:
        self.assertIn("filter((id) => tool(id))", self.script)
        self.assertIn("hasLegacySession", self.script)
        self.assertIn("ensureLegacyPanels(force = false)", self.script)
        self.assertIn("ensureLegacyPanels(true)", self.script)
        self.assertIn("setTimeout(() => ensureLegacyPanels(true), 0)", self.script)

    def test_legacy_flow_preserves_expected_public_contract(self) -> None:
        for token in (
            "data-progress-plan-form", "data-edit-progress-plan",
            "data-export-progress-plans", "auditTrail",
            "original-license-safe-tools-only",
            "جاهز للمراجعة المهنية",
        ):
            self.assertIn(token, self.script)

    def test_loader_preserves_lazy_loading_and_chains_compatibility(self) -> None:
        self.assertIn('import("./institutional-contract-v220-integration.js")', self.loader)
        self.assertIn('.then(() => import("./institutional-contract-v231-compat.js"))', self.loader)
        self.assertIn("fallbackTimer", self.loader)
        self.assertIn("PA_LOAD_INSTITUTIONAL_V220", self.loader)
        self.assertIn("compatibilityRelease", self.loader)

    def test_javascript_parses(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        for path in (SCRIPT, LOADER):
            subprocess.run([node, "--check", str(path)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
