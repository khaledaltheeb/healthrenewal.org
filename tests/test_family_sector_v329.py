from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import verify_family_sector_v329 as verifier  # noqa: E402


class FamilySectorV329Tests(unittest.TestCase):
    def test_complete_sector_passes(self) -> None:
        report = verifier.validate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(len(report["pages"]), 4)
        for page in report["pages"]:
            self.assertEqual(page["status"], "passed", page)
            self.assertEqual(page["h1"], 1, page)

    def _mutation(self, name: str, old: str, new: str) -> dict[str, object]:
        source = verifier.PAGES[name].read_text(encoding="utf-8")
        self.assertIn(old, source)
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "index.html"
            candidate.write_text(source.replace(old, new, 1), encoding="utf-8")
            return verifier.validate_page(name, candidate)

    def test_rejects_removed_violence_boundary(self) -> None:
        result = self._mutation("index", "العنف والإساءة والسيطرة تحتاج مسار سلامة مستقلًا", "تنبيه عام")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("missing marker" in error for error in result["errors"]), result)

    def test_rejects_guaranteed_treatment_claim(self) -> None:
        result = self._mutation("library", "هذه المكتبة لا تقدم تشخيصًا للأسرة", "هذه المكتبة تقدم علاج مضمون للأسرة")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("banned pattern" in error for error in result["errors"]), result)

    def test_rejects_broken_canonical(self) -> None:
        result = self._mutation("assessment", verifier.CANONICALS["assessment"], "https://example.com/wrong/")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("canonical mismatch" in error for error in result["errors"]), result)

    def test_rejects_removed_family_therapy_boundary(self) -> None:
        result = self._mutation("interventions", "العلاج الأسري ليس مناسبًا تلقائيًا", "العلاج الأسري مناسب دائمًا")
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("missing marker" in error for error in result["errors"]), result)


if __name__ == "__main__":
    unittest.main()
