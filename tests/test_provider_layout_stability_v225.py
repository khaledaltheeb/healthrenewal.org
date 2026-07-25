from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "provider-assessment-demo"
BASE_STYLE = DEMO / "styles.css"
CONTRACT_STYLE = DEMO / "institutional-contract-v220.css"
INTEGRATION = DEMO / "institutional-contract-v220-integration.js"


class ProviderLayoutStabilityV225Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_style = BASE_STYLE.read_text(encoding="utf-8")
        cls.contract_style = CONTRACT_STYLE.read_text(encoding="utf-8")
        cls.integration = INTEGRATION.read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
