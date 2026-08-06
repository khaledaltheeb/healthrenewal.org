from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from site_base_path_v1 import normalize_site_base_path


class SiteBasePathV1Tests(unittest.TestCase):
    def test_root_domain_never_becomes_protocol_relative(self) -> None:
        for value in (
            "https://healthrenewal.org",
            "https://healthrenewal.org/",
            "https://healthrenewal.org//",
            "/",
            "",
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_site_base_path(value), "/")

    def test_subpath_is_normalized_once(self) -> None:
        self.assertEqual(
            normalize_site_base_path("https://example.org/platform/"),
            "/platform/",
        )
        self.assertEqual(normalize_site_base_path("/platform//"), "/platform/")

    def test_wrappers_preserve_legacy_sources_and_override_buggy_global(self) -> None:
        previous = os.environ.get("SITE_BASE")
        os.environ["SITE_BASE"] = "https://healthrenewal.org/"
        try:
            for module_name, wrapper_name, legacy_name in (
                (
                    "expand_v12_direct_wrapper_test",
                    "expand_v12_direct.py",
                    "expand_v12_direct_legacy_v1.py",
                ),
                (
                    "complete_core_sections_v15_wrapper_test",
                    "complete_core_sections_v15.py",
                    "complete_core_sections_v15_legacy_v1.py",
                ),
            ):
                wrapper = SCRIPTS / wrapper_name
                legacy = SCRIPTS / legacy_name
                self.assertTrue(legacy.is_file(), legacy)
                self.assertGreater(legacy.stat().st_size, wrapper.stat().st_size)
                spec = importlib.util.spec_from_file_location(module_name, wrapper)
                self.assertIsNotNone(spec)
                self.assertIsNotNone(spec.loader)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                self.assertEqual(module.legacy.BASE_PATH, "/")
        finally:
            if previous is None:
                os.environ.pop("SITE_BASE", None)
            else:
                os.environ["SITE_BASE"] = previous


if __name__ == "__main__":
    unittest.main()
