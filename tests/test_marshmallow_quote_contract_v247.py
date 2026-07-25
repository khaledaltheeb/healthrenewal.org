from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enforce_platform_identity_v201.py"
SPEC = importlib.util.spec_from_file_location("platform_identity_v201", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class MarshmallowQuoteContractV247Tests(unittest.TestCase):
    def test_single_quoted_body_class_is_preserved_and_accepted(self) -> None:
        source = (
            "<!doctype html><html data-tools-design='legacy'><head><title>الأدوات</title></head>"
            "<body class='existing-shell'><main><h1>الأدوات</h1></main></body></html>"
        )

        updated, changed = MODULE.ensure_tools_marshmallow(source)

        self.assertTrue(changed)
        self.assertIn("data-tools-design='marshmallow-v245'", updated)
        self.assertIn("class='existing-shell tools-marshmallow-v245'", updated)
        self.assertTrue(MODULE._tag_has_class(updated, "body", "tools-marshmallow-v245"))
        MODULE.validate_tools_marshmallow_contract(updated)

        repeated, repeated_changed = MODULE.ensure_tools_marshmallow(updated)
        self.assertFalse(repeated_changed)
        self.assertEqual(updated, repeated)

    def test_double_quoted_body_class_is_accepted(self) -> None:
        source = (
            '<!doctype html><html data-tools-design="marshmallow-v245"><head>'
            f'{MODULE.TOOLS_MARSHMALLOW_STYLE}</head>'
            '<body class="existing-shell tools-marshmallow-v245"><main></main></body></html>'
        )

        MODULE.validate_tools_marshmallow_contract(source)
        repeated, changed = MODULE.ensure_tools_marshmallow(source)
        self.assertFalse(changed)
        self.assertEqual(source, repeated)

    def test_attribute_spacing_and_class_order_are_semantic(self) -> None:
        source = (
            "<!doctype html><html data-tools-design = 'marshmallow-v245'><head>"
            f"{MODULE.TOOLS_MARSHMALLOW_STYLE}</head>"
            "<body class = 'tools-marshmallow-v245 existing-shell'><main></main></body></html>"
        )

        MODULE.validate_tools_marshmallow_contract(source)
        self.assertTrue(MODULE._tag_has_class(source, "body", "tools-marshmallow-v245"))

    def test_missing_body_class_is_rejected(self) -> None:
        source = (
            '<!doctype html><html data-tools-design="marshmallow-v245"><head>'
            f'{MODULE.TOOLS_MARSHMALLOW_STYLE}</head><body><main></main></body></html>'
        )

        with self.assertRaisesRegex(SystemExit, "body class tools-marshmallow-v245"):
            MODULE.validate_tools_marshmallow_contract(source)


if __name__ == "__main__":
    unittest.main()
