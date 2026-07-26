from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "finalize_practical_tips_search_v248.py"
spec = importlib.util.spec_from_file_location("tips_search_visibility_v248", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PracticalTipsSearchVisibilityV248Tests(unittest.TestCase):
    def make_site(self, root: Path, cards: int = 100) -> Path:
        site = root / "site"
        (site / "tips").mkdir(parents=True)
        (site / "api").mkdir(parents=True)
        rendered_cards = "".join(
            f'<article class="tip237-card" data-search="دليل {index}">دليل {index}</article>'
            for index in range(cards)
        )
        (site / "tips/index.html").write_text(
            "<!doctype html><html lang=\"ar\" dir=\"rtl\"><head><title>النصائح</title></head>"
            f"<body><main>{rendered_cards}</main></body></html>",
            encoding="utf-8",
        )
        (site / "api/practical-tips-v237.json").write_text(
            json.dumps(
                {
                    "version": 237,
                    "status": "passed",
                    "guide_count": 100,
                    "search_contract": "local-normalized-filter-v248",
                    "search_cards": 100,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return site

    def test_injects_important_hidden_rule_and_updates_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            report = module.finalize(site)
            source = (site / "tips/index.html").read_text(encoding="utf-8")
            self.assertEqual(source.count(module.STYLE_START), 1)
            self.assertEqual(source.count(module.STYLE_END), 1)
            self.assertEqual(source.count(f'id="{module.STYLE_ID}"'), 1)
            self.assertIn("[data-search][hidden]{display:none!important}", source)
            self.assertEqual(report["search_visibility_contract"], module.CONTRACT)
            self.assertEqual(report["search_visibility_cards"], 100)

    def test_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            module.finalize(site)
            first = (site / "tips/index.html").read_text(encoding="utf-8")
            first_report = (site / "api/practical-tips-v237.json").read_text(encoding="utf-8")
            module.finalize(site)
            second = (site / "tips/index.html").read_text(encoding="utf-8")
            second_report = (site / "api/practical-tips-v237.json").read_text(encoding="utf-8")
            self.assertEqual(first, second)
            self.assertEqual(first_report, second_report)

    def test_rejects_wrong_card_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory), cards=99)
            with self.assertRaises(RuntimeError):
                module.finalize(site)

    def test_rejects_invalid_publisher_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            report_path = site / "api/practical-tips-v237.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["search_cards"] = 99
            report_path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                module.finalize(site)


if __name__ == "__main__":
    unittest.main()
