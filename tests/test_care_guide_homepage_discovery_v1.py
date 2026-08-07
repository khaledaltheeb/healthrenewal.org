from __future__ import annotations

import unittest

from scripts.link_care_guides_v21 import (
    ACTION_LINK,
    ACTION_MARKER,
    NAV_LINK,
    NAV_MARKER,
    ensure_homepage_care_guide_discovery,
)


class CareGuideHomepageDiscoveryTests(unittest.TestCase):
    def test_modern_semantic_links_are_preserved_without_mutation(self) -> None:
        source = (
            '<main><a class="journey" href="care-guides/">خطوات عملية</a>'
            '<article><a href="care-guides/">فتح الأدلة</a></article></main>'
        )
        updated, count, legacy_injected = ensure_homepage_care_guide_discovery(source)
        self.assertEqual(updated, source)
        self.assertEqual(count, 2)
        self.assertFalse(legacy_injected)

    def test_legacy_markers_remain_supported_as_fallback(self) -> None:
        source = f'<nav>{NAV_MARKER}</nav><div>{ACTION_MARKER}</div>'
        updated, count, legacy_injected = ensure_homepage_care_guide_discovery(source)
        self.assertEqual(count, 2)
        self.assertTrue(legacy_injected)
        self.assertEqual(updated.count(NAV_LINK), 1)
        self.assertEqual(updated.count(ACTION_LINK), 1)

    def test_missing_semantic_and_legacy_contract_fails_closed(self) -> None:
        with self.assertRaises(SystemExit):
            ensure_homepage_care_guide_discovery('<main><a href="tips/">نص حديث مختلف</a></main>')


if __name__ == "__main__":
    unittest.main()
