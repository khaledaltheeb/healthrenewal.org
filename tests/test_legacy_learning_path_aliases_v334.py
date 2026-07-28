from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "repair_legacy_learning_path_aliases_v334.py"
SPEC = importlib.util.spec_from_file_location("repair_legacy_learning_path_aliases_v334", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LegacyLearningPathAliasesV334Tests(unittest.TestCase):
    def make_site(self) -> Path:
        root = Path(tempfile.mkdtemp())
        for alias in MODULE.ALIASES:
            target = root / "learning-paths" / alias.target_slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("<!doctype html><html lang='ar' dir='rtl'><title>target</title></html>", encoding="utf-8")
            source = root / "learning-paths" / alias.source_slug / "index.html"
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("<html><title>تم تحديث مسار التعلم</title></html>", encoding="utf-8")
        return root

    def test_repairs_all_aliases_with_unique_self_canonicals(self) -> None:
        site = self.make_site()
        report = MODULE.repair(site, MODULE.DEFAULT_SITE_BASE, strict=True)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["aliases_written"], 4)
        titles = set()
        descriptions = set()
        for alias in MODULE.ALIASES:
            page = site / "learning-paths" / alias.source_slug / "index.html"
            text = page.read_text(encoding="utf-8")
            source_url = f"{MODULE.DEFAULT_SITE_BASE}learning-paths/{alias.source_slug}/"
            target_url = f"{MODULE.DEFAULT_SITE_BASE}learning-paths/{alias.target_slug}/"
            self.assertIn(MODULE.MARKER, text)
            self.assertIn('name="robots" content="noindex,follow', text)
            self.assertIn(f'rel="canonical" href="{source_url}"', text)
            self.assertIn(f'http-equiv="refresh" content="0; url={target_url}"', text)
            self.assertIn(f'href="{target_url}"', text)
            self.assertIn('property="og:title"', text)
            self.assertIn('property="og:description"', text)
            titles.add(alias.title)
            descriptions.add(alias.description)
        self.assertEqual(len(titles), 4)
        self.assertEqual(len(descriptions), 4)

    def test_second_run_is_idempotent(self) -> None:
        site = self.make_site()
        first = MODULE.repair(site, MODULE.DEFAULT_SITE_BASE, strict=True)
        snapshots = {
            alias.source_slug: (site / "learning-paths" / alias.source_slug / "index.html").read_bytes()
            for alias in MODULE.ALIASES
        }
        second = MODULE.repair(site, MODULE.DEFAULT_SITE_BASE, strict=True)
        self.assertEqual(first["aliases_changed"], 4)
        self.assertEqual(second["aliases_changed"], 0)
        for alias in MODULE.ALIASES:
            current = (site / "learning-paths" / alias.source_slug / "index.html").read_bytes()
            self.assertEqual(current, snapshots[alias.source_slug])

    def test_strict_mode_rejects_missing_target(self) -> None:
        site = self.make_site()
        missing = site / "learning-paths" / MODULE.ALIASES[0].target_slug / "index.html"
        missing.unlink()
        with self.assertRaises(SystemExit):
            MODULE.repair(site, MODULE.DEFAULT_SITE_BASE, strict=True)
        report = json.loads(
            (site / "api" / "legacy-learning-path-aliases-v334.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["status"], "failed")
        self.assertTrue(report["errors"])


if __name__ == "__main__":
    unittest.main()
