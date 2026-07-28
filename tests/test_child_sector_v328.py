from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_child_sector_v328 as verifier  # noqa: E402


class ChildSectorV328Tests(unittest.TestCase):
    def test_complete_sector_passes(self) -> None:
        report = verifier.validate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(len(report["pages"]), 4)
        for page in report["pages"]:
            self.assertEqual(page["h1"], 1, page)
            self.assertEqual(page["status"], "passed", page)

    def _mutated_page(self, name: str, old: str, new: str) -> dict[str, object]:
        original = verifier.PAGES[name]
        source = original.read_text(encoding="utf-8")
        self.assertIn(old, source)
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "index.html"
            candidate.write_text(source.replace(old, new, 1), encoding="utf-8")
            return verifier.validate_page(name, candidate)

    def test_rejects_removed_urgent_boundary(self) -> None:
        result = self._mutated_page(
            "index",
            "الخطر المباشر يسبق التصفح",
            "تنبيه عام",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("missing marker" in error for error in result["errors"]), result)

    def test_rejects_self_diagnosis_language(self) -> None:
        result = self._mutated_page(
            "library",
            "هذه المكتبة ليست قائمة تشخيص ذاتي",
            "هذه المكتبة تقدم تشخيص ذاتي مؤكد",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("banned pattern" in error for error in result["errors"]), result)

    def test_rejects_broken_canonical(self) -> None:
        result = self._mutated_page(
            "assessment",
            verifier.CANONICALS["assessment"],
            "https://example.com/wrong/",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("canonical mismatch" in error for error in result["errors"]), result)

    def test_rejects_missing_intervention_boundary(self) -> None:
        result = self._mutated_page(
            "interventions",
            "قاعدة منع الضرر",
            "ملاحظة إضافية",
        )
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("missing marker" in error for error in result["errors"]), result)


if __name__ == "__main__":
    unittest.main()
