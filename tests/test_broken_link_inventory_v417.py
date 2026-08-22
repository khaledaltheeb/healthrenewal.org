from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("broken_links_v417", ROOT / "scripts/inventory_broken_links_v417.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class TestBrokenLinkInventoryV417(unittest.TestCase):
    def test_groups_repeated_missing_target_and_suggests_existing_route(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"guides"/"existing").mkdir(parents=True)
            (root/"guides"/"existing"/"index.html").write_text("<html><head></head><body>ok</body></html>",encoding="utf-8")
            for name in ("a","b"):
                d=root/name; d.mkdir()
                d.joinpath("index.html").write_text('<html><body><a href="/guides/exsting/">x</a></body></html>',encoding="utf-8")
            result=mod.build(root)
            self.assertEqual(result["summary"]["broken_targets"],1)
            self.assertEqual(result["items"][0]["occurrences"],2)
            self.assertIn("/guides/existing",result["items"][0]["suggested_existing_routes"])

    def test_ignores_fragment_external_and_existing_links(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"index.html").write_text('<html><body><a href="#x">x</a><a href="https://who.int">w</a><a href="/">home</a></body></html>',encoding="utf-8")
            result=mod.build(root)
            self.assertEqual(result["summary"]["broken_occurrences"],0)


if __name__ == "__main__": unittest.main()
