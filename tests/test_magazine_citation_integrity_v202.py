from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "repair_magazine_citation_integrity_v202.py"
SOURCE = ROOT / "magazine"

spec = importlib.util.spec_from_file_location("magazine_citation_repair", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class MagazineCitationIntegrityV202Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.magazine = Path(self.tmp.name) / "magazine"
        for rel_path in mod.REPAIRS:
            src = SOURCE / rel_path
            dst = self.magazine / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_known_citation_repairs_are_narrow_and_idempotent(self) -> None:
        report = mod.apply_repairs(self.magazine)
        self.assertEqual(report["changed_pages"], 2)
        self.assertEqual(report["rules"], 6)

        family = (
            self.magazine
            / "pediatric-oncology/studies/family-resilience-childhood-cancer-qualitative-synthesis-2026/index.html"
        ).read_text(encoding="utf-8")
        self.assertIn("10.3389/fpsyt.2026.1856540", family)
        self.assertNotIn("10.3389/fpsyt.2026.1856540/full", family)

        hct = (
            self.magazine
            / "pediatric-oncology/theses/bridging-gap-hct-success-troullioud-lucas-2026/index.html"
        ).read_text(encoding="utf-8")
        for wrong in (
            "10.1182/bloodadvances.2024013302",
            "10.1002/pbc.31048",
            "10.3389/fimmu.2023.1163408",
            "دراسة Frontiers in Immunology لعام 2023 المرتبطة بالمؤلف",
            "دراسة Pediatric Blood &amp; Cancer لعام 2024 المرتبطة بالأطروحة",
        ):
            self.assertNotIn(wrong, hct)
        for correct in (
            "10.1038/s41409-023-02121-1",
            "10.3389/fonc.2023.1221782",
            "10.1016/j.jcyt.2023.05.012",
            "دراسة Cytotherapy لعام 2023 المرتبطة بالمؤلف",
            "دراسة Frontiers in Oncology لعام 2023 المرتبطة بالأطروحة",
        ):
            self.assertIn(correct, hct)

        second = mod.apply_repairs(self.magazine)
        self.assertEqual(second["changed_pages"], 0)
        self.assertTrue(all(item["status"] == "already_correct" for item in second["results"]))


if __name__ == "__main__":
    unittest.main()
