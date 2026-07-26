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
        (site / "tips/example").mkdir(parents=True)
        (site / "api").mkdir(parents=True)
        (site / "assets/css").mkdir(parents=True)
        rendered_cards = "".join(
            f'<article class="tip237-card" data-search="دليل {index}"><span>تصنيف</span>دليل {index}</article>'
            for index in range(cards)
        )
        (site / "tips/index.html").write_text(
            "<!doctype html><html lang=\"ar\" dir=\"rtl\"><head><title>النصائح</title></head>"
            f"<body><main><div class=\"tip237-badges\"><span>100 دليل مؤسسي</span><span>10 مسارات</span></div>{rendered_cards}</main></body></html>",
            encoding="utf-8",
        )
        (site / "tips/example/index.html").write_text(
            "<!doctype html><html lang=\"ar\" dir=\"rtl\"><head><title>دليل</title></head>"
            "<body><main><div class=\"tip237-table-wrap\"><table><tr><td>مثال</td></tr></table></div>"
            "</main></body></html>",
            encoding="utf-8",
        )
        (site / "assets/css/practical-tips-v237.css").write_text(
            ":root{--tip237-ink:#123d42;--tip237-brand:#167f78}.tip237-badges span,.tip237-card>span{background:#e8e1ff}.tip237-card a{color:var(--tip237-brand)}\n",
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

    def test_injects_search_visibility_and_accessibility_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            report = module.finalize(site)
            source = (site / "tips/index.html").read_text(encoding="utf-8")
            css = (site / "assets/css/practical-tips-v237.css").read_text(encoding="utf-8")
            detail = (site / "tips/example/index.html").read_text(encoding="utf-8")
            self.assertEqual(source.count(module.STYLE_START), 1)
            self.assertEqual(source.count(module.STYLE_END), 1)
            self.assertEqual(source.count(f'id="{module.STYLE_ID}"'), 1)
            self.assertIn("[data-search][hidden]{display:none!important}", source)
            self.assertEqual(css.count(module.ACCESS_CSS_START), 1)
            self.assertEqual(css.count(module.ACCESS_CSS_END), 1)
            self.assertIn(f"--tip237-brand:{module.SAFE_BRAND}", css)
            self.assertIn(
                f".tip237-badges span,.tip237-card>span{{color:{module.SAFE_BADGE_TEXT}}}",
                css,
            )
            self.assertIn('tabindex="0"', detail)
            self.assertIn('role="region"', detail)
            self.assertIn(f'aria-label="{module.SCROLL_REGION_LABEL}"', detail)
            self.assertEqual(report["search_visibility_contract"], module.CONTRACT)
            self.assertEqual(report["search_visibility_cards"], 100)
            self.assertEqual(report["accessibility_contract"], module.ACCESS_CONTRACT)
            self.assertEqual(report["accessibility_link_color"], module.SAFE_BRAND)
            self.assertEqual(report["accessibility_badge_text_color"], module.SAFE_BADGE_TEXT)
            self.assertEqual(report["accessible_scroll_regions"], 1)

    def test_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = self.make_site(Path(temporary_directory))
            module.finalize(site)
            first = {
                path: (site / path).read_text(encoding="utf-8")
                for path in (
                    "tips/index.html",
                    "tips/example/index.html",
                    "assets/css/practical-tips-v237.css",
                    "api/practical-tips-v237.json",
                )
            }
            module.finalize(site)
            second = {
                path: (site / path).read_text(encoding="utf-8")
                for path in first
            }
            self.assertEqual(first, second)

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
