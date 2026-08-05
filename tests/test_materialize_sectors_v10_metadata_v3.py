from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "materialize_sectors_v10_metadata_v3.py"
SPEC = importlib.util.spec_from_file_location("materialize_sectors_v10_metadata_v3", SCRIPT_PATH)
assert SPEC and SPEC.loader
metadata = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = metadata
SPEC.loader.exec_module(metadata)


class MaterializeSectorsV10MetadataTests(unittest.TestCase):
    def test_clinical_anxiety_metadata_is_visible_and_semantic(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source_path = root / "content" / "sectors-v10" / "clinical-anxiety.json"
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        item = metadata.base.PublicationItem(
            source_path=source_path,
            payload=payload,
            category="mental-health",
            route="evidence-guides/clinical-anxiety/",
        )
        page = metadata.render_page(item)

        self.assertIn('<html lang="ar" dir="rtl">', page)
        self.assertIn('<meta name="viewport"', page)
        self.assertIn('@media print', page)
        self.assertIn('@media (prefers-reduced-motion:reduce)', page)
        self.assertIn(
            '<link rel="canonical" href="https://healthrenewal.org/evidence-guides/clinical-anxiety/">',
            page,
        )
        self.assertIn('"@type":["MedicalWebPage","CollectionPage"]', page)
        self.assertIn('"mainEntityOfPage"', page)
        self.assertIn("هذه الصفحة للتثقيف ولا تثبت تشخيصًا", page)
        self.assertIn("أسئلة عملية للتحضير والمتابعة", page)
        self.assertIn("سجل المنهج والتحقق", page)
        self.assertIn("الادعاءات التي جرى فحصها", page)
        self.assertIn("روابط داخلية ذات صلة", page)
        self.assertIn('/daily-tools/medical-visit-preparation/', page)
        self.assertIn("حالة المراجعة: internally-reviewed", page)
        self.assertNotIn("ادعاء شراكة", page)

    def test_rejects_external_internal_link(self) -> None:
        self.assertIsNone(metadata._internal_href("https://example.com/path"))
        self.assertIsNone(metadata._internal_href("//example.com/path"))
        self.assertEqual(metadata._internal_href("/mental-health/"), "/mental-health/")


if __name__ == "__main__":
    unittest.main()
