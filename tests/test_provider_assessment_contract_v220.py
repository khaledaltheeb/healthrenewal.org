from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "provider-assessment-demo"
INDEX = DEMO / "index.html"
SCRIPT = DEMO / "institutional-contract-v220.js"
MODULES = [DEMO / name for name in ("institutional-contract-v220-core.js", "institutional-contract-v220-ui.js", "institutional-contract-v220-plans.js", "institutional-contract-v220-integration.js")]
STYLE = DEMO / "institutional-contract-v220.css"
MANIFEST = DEMO / "institutional-contract-v220.json"


class ProviderAssessmentContractV220Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.script = "\n".join(path.read_text(encoding="utf-8") for path in MODULES)
        cls.style = STYLE.read_text(encoding="utf-8")
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_release_is_wired_after_existing_runtime(self) -> None:
        self.assertIn('data-release="2026.07.25-v220"', self.index)
        self.assertIn('institutional-contract-v220.css?v=20260725-v220', self.index)
        existing = self.index.index('<script src="institutional-live-v2.js')
        contract = self.index.index('<script src="institutional-contract-v220.js')
        self.assertLess(existing, contract)
        self.assertIn('data-institutional-contract-v220="2026.07.25-v220"', self.index)

    def test_exploratory_contract_covers_all_functional_categories(self) -> None:
        for key in (
            "development", "communication", "attention", "learning",
            "adaptive", "sensory", "motor", "emotional",
        ):
            self.assertIn(f"{key}: {{", self.script)
        for field in (
            "purpose", "decisionUse", "domains", "dataSources", "confounders",
            "redFlags", "repeatInterval", "referenceWindow", "scoring",
            "interpretation", "missingData", "accessibility", "governance",
        ):
            self.assertIn(field, self.script)

    def test_professional_contract_is_rights_gated_and_does_not_unlock_materials(self) -> None:
        self.assertIn("بطاقة أداة مهنية دون مواد محمية", self.script)
        self.assertIn("لا تعرض بنودًا أو تعليمات تصحيح أو معايير أو محتوى محميًا", self.script)
        self.assertIn("rightsStatus", self.script)
        self.assertNotIn('rightsStatus = "open"', self.script)
        self.assertNotIn('item.status = "open"', self.script)
        self.assertNotIn("unlockProfessional", self.script)

    def test_case_plan_has_ten_quality_gates_and_versioning(self) -> None:
        for token in (
            "assessmentPlans", "auditPlan", "score: passed * 10", "supersedes",
            "auditTrail", "status_changed", "reviewDate", "consentStatus",
            "assentStatus", "safetyReview", "languageContext", "accessibility",
            "explorerIds", "professionalCategories",
        ):
            self.assertIn(token, self.script)
        self.assertEqual(len(self.manifest["qualityGates"]), 10)

    def test_professional_record_requires_validity_sources_limits_and_review(self) -> None:
        for field in (
            "referralPurpose", "decisionUseV220", "validityStatus", "completionStatus",
            "normativeFit", "crossSourceAgreement", "consentV220", "riskReview",
            "reviewerV220", "reviewDateV220", "sourcesSettings",
            "accommodationsDeviations", "functionalSynthesis",
            "recommendationsV220", "limitationsV220",
        ):
            self.assertIn(f'name="{field}"', self.script)
        self.assertIn("documentationQuality", self.script)
        self.assertIn("institutional_contract_attached", self.script)

    def test_manifest_exposes_machine_readable_contract(self) -> None:
        self.assertEqual(self.manifest["id"], "institutional-assessment-contract-v220")
        self.assertEqual(self.manifest["release"], "2026.07.25-v220")
        self.assertFalse(self.manifest["storage"]["serverAuthentication"])
        self.assertFalse(self.manifest["storage"]["cloudSynchronization"])
        self.assertEqual(
            self.manifest["interoperability"]["runtimeGlobal"],
            "PA_INSTITUTIONAL_CONTRACT_V220",
        )
        self.assertEqual(len(self.manifest["authoritativeDesignReferences"]), 3)

    def test_accessibility_and_responsive_contract_styles_exist(self) -> None:
        for token in (
            "institutional-v220-check", "institutional-v220-multiselect",
            "institutional-v220-score", "institutional-v220-gate",
            "@media(max-width:760px)", "focus-visible",
        ):
            self.assertIn(token, self.style)

    def test_javascript_parses(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not installed")
        for path in [SCRIPT, *MODULES]:
            subprocess.run([node, "--check", str(path)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
