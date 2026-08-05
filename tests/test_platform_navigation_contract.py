import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "accessibility" / "platform-navigation-contract.json"
JS = ROOT / "assets" / "platform" / "platform-core.js"
CSS = ROOT / "assets" / "platform" / "platform-core.css"


class PlatformNavigationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.js = JS.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")

    def test_contract_is_rtl_and_bound_to_issue_900(self):
        self.assertEqual(self.contract["issue"], 900)
        self.assertEqual(self.contract["language"], "ar")
        self.assertEqual(self.contract["direction"], "rtl")

    def test_skip_link_and_unique_main_target_are_centralized(self):
        skip = self.contract["skipLink"]
        main = self.contract["mainLandmark"]
        self.assertTrue(skip["required"])
        self.assertTrue(skip["mustBeFirstFocusable"])
        self.assertEqual(skip["targetId"], main["id"])
        self.assertEqual(main["requiredCount"], 1)
        self.assertIn("main.id = 'main-content'", self.js)
        self.assertIn("class: 'pt-skip-link'", self.js)
        self.assertIn("body.prepend(skip)", self.js)

    def test_focus_indicator_meets_contract(self):
        focus = self.contract["focus"]
        self.assertGreaterEqual(focus["minimumOutlineWidthPx"], 3)
        self.assertGreaterEqual(focus["minimumOutlineOffsetPx"], 2)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("outline: 3px solid var(--pt-focus)", self.css)
        self.assertIn("outline-offset: 4px", self.css)

    def test_skip_link_becomes_visible_on_focus(self):
        self.assertTrue(self.contract["skipLink"]["visibleOnFocus"])
        self.assertIn(".pt-skip-link:focus", self.css)
        self.assertIn("top: 12px", self.css)

    def test_breadcrumb_contract_is_semantic_not_textual(self):
        breadcrumbs = self.contract["breadcrumbs"]
        self.assertEqual(breadcrumbs["container"]["element"], "nav")
        self.assertEqual(breadcrumbs["listElement"], "ol")
        self.assertEqual(breadcrumbs["currentItemUsesAriaCurrent"], "page")
        self.assertTrue(breadcrumbs["decorativeSeparatorsAreAriaHidden"])
        self.assertTrue(self.contract["negativeRules"]["forbidTextSeparatorsAnnouncedByScreenReaders"])

    def test_mobile_print_zoom_and_reduced_motion_are_explicit(self):
        responsive = self.contract["responsive"]
        self.assertEqual(responsive["minimumViewportWidthPx"], 320)
        self.assertTrue(responsive["preventUnnecessaryHorizontalScroll"])
        self.assertTrue(responsive["supportsPrint"])
        self.assertTrue(responsive["supportsReducedMotion"])
        self.assertEqual(self.contract["focus"]["mustRemainVisibleAtZoom"], [200, 400])

    def test_negative_rules_prevent_local_regressions(self):
        rules = self.contract["negativeRules"]
        self.assertTrue(rules["forbidLocalBreadcrumbCss"])
        self.assertTrue(rules["forbidDuplicateMainIds"])
        self.assertTrue(rules["forbidHiddenSkipLinkOnFocus"])


if __name__ == "__main__":
    unittest.main()
