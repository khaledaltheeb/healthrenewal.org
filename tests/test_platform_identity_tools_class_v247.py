from __future__ import annotations

import unittest

from scripts import enforce_platform_identity_v201 as identity


class PlatformIdentityToolsClassV247Tests(unittest.TestCase):
    def test_existing_single_quoted_body_classes_are_canonicalized(self) -> None:
        source = "<html><body class='legacy page-shell'><main></main></body></html>"
        updated, changed = identity._add_class_to_body(source, "tools-marshmallow-v245")
        self.assertTrue(changed)
        self.assertIn(
            'class="tools-marshmallow-v245 legacy page-shell"',
            updated,
        )
        self.assertNotIn("class='", updated)

        second, second_changed = identity._add_class_to_body(
            updated,
            "tools-marshmallow-v245",
        )
        self.assertFalse(second_changed)
        self.assertEqual(second, updated)

    def test_wrapper_patches_the_production_base_function(self) -> None:
        self.assertIs(identity._base._add_class_to_body, identity._add_class_to_body)

    def test_body_without_class_gets_canonical_marker(self) -> None:
        source = '<html><body data-page="tools"><main></main></body></html>'
        updated, changed = identity._add_class_to_body(source, "tools-marshmallow-v245")
        self.assertTrue(changed)
        self.assertIn(
            '<body data-page="tools" class="tools-marshmallow-v245">',
            updated,
        )


if __name__ == "__main__":
    unittest.main()
