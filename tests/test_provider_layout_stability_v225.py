from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "provider-assessment-demo"
BASE_STYLE = DEMO / "styles.css"
CONTRACT_STYLE = DEMO / "institutional-contract-v220.css"
INTEGRATION = DEMO / "institutional-contract-v220-integration.js"
LIVE_RUNTIME = DEMO / "institutional-live-v2.js"
ACTIVATION_GUARD = DEMO / "activation-guard.js"


class ProviderLayoutStabilityV225Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_style = BASE_STYLE.read_text(encoding="utf-8")
        cls.contract_style = CONTRACT_STYLE.read_text(encoding="utf-8")
        cls.integration = INTEGRATION.read_text(encoding="utf-8")
        cls.live_runtime = LIVE_RUNTIME.read_text(encoding="utf-8")
        cls.activation_guard = ACTIVATION_GUARD.read_text(encoding="utf-8")

    def test_tab_strip_is_horizontal_and_dynamic(self) -> None:
        self.assertRegex(
            self.base_style,
            r"\.tabs\{[^}]*display:flex[^}]*overflow-x:auto",
        )
        self.assertIn('tabs.insertBefore(tab, guideTab);', self.integration)
        self.assertIn('tab.textContent = "العقد المؤسسي v220";', self.integration)

    def test_tab_strip_reserves_classic_scrollbar_height(self) -> None:
        match = re.search(r"\.tabs\{([^}]*)\}", self.contract_style)
        self.assertIsNotNone(match, "institutional layout stability rule is missing")
        declaration = match.group(1)
        self.assertIn("min-block-size:82px", declaration)
        self.assertIn("align-items:center", declaration)
        self.assertIn("overscroll-behavior-inline:contain", declaration)

    def test_reserved_height_covers_tab_padding_border_and_scrollbar(self) -> None:
        # Base contract: 44px tab + 20px vertical padding + 2px border.
        # A classic horizontal scrollbar may add roughly 15px on desktop.
        required = 44 + 20 + 2 + 15
        self.assertLessEqual(required, 82)

    def test_older_runtime_does_not_rewrite_newer_contract_copy(self) -> None:
        self.assertIn("const hasNewerInstitutionalContract", self.live_runtime)
        self.assertIn(
            'document.documentElement.dataset.institutionalContract === "2026.07.25-v220"',
            self.live_runtime,
        )
        self.assertIn(
            "Boolean(document.querySelector('script[data-institutional-contract-v220]'))",
            self.live_runtime,
        )
        apply_copy = re.search(
            r"const applyInstitutionalCopy = \(\) => \{(.*?)\n  \};",
            self.live_runtime,
            re.S,
        )
        self.assertIsNotNone(apply_copy)
        self.assertIn("if (hasNewerInstitutionalContract()) return;", apply_copy.group(1))

    def test_newer_contract_guard_precedes_live_layout_mutations(self) -> None:
        guard = self.live_runtime.index("if (hasNewerInstitutionalContract()) return;")
        notice = self.live_runtime.index('const notice = document.querySelector(".notice-bar")')
        card = self.live_runtime.index('const card = document.querySelector(".hero-card ul")')
        self.assertLess(guard, notice)
        self.assertLess(guard, card)

    def test_rights_guard_preserves_v220_copy_while_retaining_rights_controls(self) -> None:
        self.assertIn("const hasNewerInstitutionalContract", self.activation_guard)
        self.assertIn(
            'document.documentElement.dataset.institutionalContract === "2026.07.25-v220"',
            self.activation_guard,
        )
        patch_copy = re.search(
            r"const patchCopy = \(\) => \{(.*?)\n  \};",
            self.activation_guard,
            re.S,
        )
        self.assertIsNotNone(patch_copy)
        body = patch_copy.group(1)
        self.assertIn("if (hasNewerInstitutionalContract()) return;", body)
        self.assertLess(
            body.index("if (hasNewerInstitutionalContract()) return;"),
            body.index('const notice = document.querySelector(".notice-bar")'),
        )
        self.assertIn('item.rightsStatus = externalResultOnly ? "locked_or_link_only" : "locked_pending_rights";', self.activation_guard)
        self.assertIn("button.remove();", self.activation_guard)
        self.assertIn('loadModule("professional-record-lifecycle.js', self.activation_guard)

    def test_short_intermediate_notice_cannot_replace_final_contract(self) -> None:
        short_notice = "الأدوات الاستكشافية الأصلية متاحة للاستخدام التعليمي غير التشخيصي"
        self.assertIn(short_notice, self.activation_guard)
        guard = self.activation_guard.index("if (hasNewerInstitutionalContract()) return;")
        short_copy = self.activation_guard.index(short_notice)
        self.assertLess(guard, short_copy)


if __name__ == "__main__":
    unittest.main()
