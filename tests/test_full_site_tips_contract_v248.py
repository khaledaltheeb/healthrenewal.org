from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SCRIPT = SCRIPTS / "audit_full_site_i18n_v72.py"
BROWSER_AUDIT = SCRIPTS / "browser_audit_v16.mjs"
spec = importlib.util.spec_from_file_location("audit_i18n_v72_tips", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PracticalTipsFullAuditV248Tests(unittest.TestCase):
    def write_tips_contract(self, site: Path, **overrides) -> dict:
        report = {
            "version": 237,
            "status": "passed",
            "guide_count": 100,
            "preserved_existing_guides": 20,
            "new_guides": 80,
            "pillar_count": 10,
            "category_count": 29,
            "minimum_required_words": 700,
            "minimum_after_words": 812,
            "remaining_below_minimum": 0,
            "missing_or_failed": 0,
            "duplicate_slugs": 0,
            "duplicate_titles": 0,
            "sitemap_urls": 111,
            "core_sections_compatibility": "passed",
            "compatibility_pages": 100,
            "unique_titles": 100,
            "unique_descriptions": 100,
            "topic_depth_status": "passed",
            "topic_depth_pages": 10,
            "minimum_topic_characters": 3100,
            "search_contract": "local-normalized-filter-v248",
            "search_cards": 100,
        }
        report.update(overrides)
        api = site / "api"
        api.mkdir(parents=True, exist_ok=True)
        (api / "practical-tips-v237.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )
        return report

    def fake_legacy(self, site: Path, errors: list[str]):
        class FakeLegacy:
            SITE = site

            @staticmethod
            def main() -> int:
                report = {
                    "version": 16,
                    "section_counts": {"tips": 111},
                    "error_count": len(errors),
                    "errors": list(errors),
                }
                api = site / "api"
                api.mkdir(parents=True, exist_ok=True)
                (api / "full-site-audit-v16.json").write_text(
                    json.dumps(report, ensure_ascii=False), encoding="utf-8"
                )
                if errors:
                    raise SystemExit("\n".join(errors))
                return 0

        return FakeLegacy

    def test_valid_v237_contract_upgrades_only_the_obsolete_count(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            contract = self.write_tips_contract(site)
            obsolete = "Unexpected HTML count for tips: 111 != 21"
            legacy = self.fake_legacy(site, [obsolete])
            result, report = module.run_legacy_with_practical_tips_upgrade(legacy, contract)
            self.assertEqual(result, 0)
            self.assertEqual(report["error_count"], 0)
            self.assertEqual(report["errors"], [])
            self.assertEqual(report["tips_contract_version"], 237)
            self.assertEqual(report["expected_tips_html"], 111)
            self.assertEqual(report["tips_guides"], 100)
            self.assertEqual(report["tips_topic_pages"], 10)
            self.assertEqual(report["tips_sitemap_urls"], 111)

    def test_unrelated_audit_error_is_never_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            contract = self.write_tips_contract(site)
            errors = [
                "Unexpected HTML count for tips: 111 != 21",
                "Thin content in tips/topics/sleep/index.html: 900 < 1800",
            ]
            legacy = self.fake_legacy(site, errors)
            with self.assertRaises(SystemExit):
                module.run_legacy_with_practical_tips_upgrade(legacy, contract)

    def test_wrong_tip_count_is_never_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            contract = self.write_tips_contract(site)

            class WrongCountLegacy:
                SITE = site

                @staticmethod
                def main() -> int:
                    report = {
                        "version": 16,
                        "section_counts": {"tips": 110},
                        "error_count": 1,
                        "errors": ["Unexpected HTML count for tips: 110 != 21"],
                    }
                    api = site / "api"
                    api.mkdir(parents=True, exist_ok=True)
                    (api / "full-site-audit-v16.json").write_text(
                        json.dumps(report), encoding="utf-8"
                    )
                    raise SystemExit("wrong count")

            with self.assertRaises(SystemExit):
                module.run_legacy_with_practical_tips_upgrade(WrongCountLegacy, contract)

    def test_invalid_report_is_rejected_before_audit_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            site = Path(temporary_directory)
            self.write_tips_contract(site, topic_depth_pages=9)
            with self.assertRaises(SystemExit):
                module.load_practical_tips_contract(site)

    def test_browser_audit_uses_the_published_tip_contract_and_search(self) -> None:
        source = BROWSER_AUDIT.read_text(encoding="utf-8")
        self.assertIn("practical-tips-v237.json", source)
        self.assertIn("expectedGuides: 100", source)
        self.assertIn("expectedGuides: 20", source)
        self.assertIn("totalTips !== practicalTipsContract.expectedGuides", source)
        self.assertIn("practicalTipsContract,", source)
        self.assertIn("local-normalized-filter-v248", source)
        self.assertIn("data-practical-tips-search-status", source)
        self.assertIn("tips/topics/sleep/", source)
        self.assertNotIn("totalTips !== 20", source)


if __name__ == "__main__":
    unittest.main()
