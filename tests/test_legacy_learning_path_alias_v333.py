from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "audit_full_site_v16.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_full_site_alias_v333", AUDITOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LegacyLearningPathAliasV333Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()
        self.temp = tempfile.TemporaryDirectory(prefix="legacy-alias-v333-")
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name).resolve()
        self.module.SITE = self.site
        self.target = self.site / "learning-paths/new-path/index.html"
        self.target.parent.mkdir(parents=True)
        self.target.write_text("<html></html>", encoding="utf-8")
        self.alias = self.site / "learning-paths/old-path/index.html"
        self.alias.parent.mkdir(parents=True)

    def write_alias(
        self,
        *,
        robots: str = "noindex,follow",
        refresh: str = "/learning-paths/new-path/",
        canonical: str = "https://healthrenewal.org/learning-paths/new-path/",
    ) -> None:
        self.alias.write_text(
            "<!doctype html>"
            '<html lang="ar" dir="rtl" data-legacy-path-alias="v100"><head>'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>تم تحديث مسار التعلم</title><meta name="robots" content="{robots}">'
            f'<meta http-equiv="refresh" content="0;url={refresh}">'
            f'<link rel="canonical" href="{canonical}">'
            '</head><body><main><h1>تم تحديث هذا المسار</h1>'
            f'<a href="{refresh}">فتح المسار</a></main></body></html>',
            encoding="utf-8",
        )

    def test_valid_alias_is_explicit_noindex_internal_redirect(self) -> None:
        self.write_alias()
        parser = self.module.parse_page(self.alias)
        is_alias, target, errors = self.module.legacy_alias_contract(self.alias, parser)
        self.assertTrue(is_alias)
        self.assertEqual(target, "learning-paths/new-path/index.html")
        self.assertEqual(errors, [])

    def test_alias_rejects_indexing_and_target_mismatch(self) -> None:
        self.write_alias(
            robots="index,follow",
            canonical="https://healthrenewal.org/learning-paths/other-path/",
        )
        parser = self.module.parse_page(self.alias)
        is_alias, _, errors = self.module.legacy_alias_contract(self.alias, parser)
        self.assertTrue(is_alias)
        self.assertTrue(any("robots contract" in item for item in errors))
        self.assertTrue(any("refresh/canonical mismatch" in item for item in errors))

    def test_normal_page_is_not_treated_as_alias(self) -> None:
        parser = self.module.parse_page(self.target)
        is_alias, target, errors = self.module.legacy_alias_contract(self.target, parser)
        self.assertFalse(is_alias)
        self.assertIsNone(target)
        self.assertEqual(errors, [])

    def test_release_gate_uses_v100_report_not_historical_counts(self) -> None:
        workflow = (ROOT / ".github/workflows/validate-all-labs-v22.yml").read_text(encoding="utf-8")
        self.assertIn("report['tools'] == 100", workflow)
        self.assertIn("report['paths'] == 10", workflow)
        self.assertIn("report['pages'] == 112", workflow)
        self.assertNotIn('daily-tools -name index.html | wc -l)" -eq 9', workflow)
        self.assertNotIn('learning-paths -name index.html | wc -l)" -eq 5', workflow)


if __name__ == "__main__":
    unittest.main()
