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
    def _clinical_item(self):
        root = Path(__file__).resolve().parents[1]
        source_path = root / "content" / "sectors-v10" / "clinical-anxiety.json"
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        return metadata.PublicationItem(
            source_path=source_path,
            payload=payload,
            category="mental-health",
            route="evidence-guides/clinical-anxiety/",
        )

    def test_v3_is_exact_nonduplicating_compatibility_entrypoint(self) -> None:
        item = self._clinical_item()
        v3_page = metadata.render_page(item)
        compat_page = metadata.compat.render_page(item)
        self.assertEqual(v3_page, compat_page)
        self.assertEqual(v3_page.count('id="governance"'), 1)
        self.assertEqual(v3_page.count('id="practical-questions"'), 1)
        self.assertEqual(v3_page.count('id="related-links"'), 1)

    def test_clinical_anxiety_metadata_is_visible_and_semantic(self) -> None:
        page = metadata.render_page(self._clinical_item())

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
        self.assertIn("أسئلة عملية قبل التقييم أو المتابعة", page)
        self.assertIn("حالة المراجعة ومنهجية المصادر", page)
        self.assertIn("المحاور التي تم التحقق منها", page)
        self.assertIn("مسارات مرتبطة داخل المنصة", page)
        self.assertIn('/daily-tools/medical-visit-preparation/', page)
        self.assertIn("مراجعة تحريرية داخلية", page)
        self.assertIn("مراجعة خارجية موصى بها ولم تكتمل", page)
        self.assertNotIn("شراكة مع منظمة الصحة العالمية", page)

    def test_declared_canonical_must_match_publication_route(self) -> None:
        item = self._clinical_item()
        metadata.validate_source(item.source_path, item.payload)
        item.payload["canonical"] = "https://healthrenewal.org/mental-health/clinical-anxiety/"
        with self.assertRaises(metadata.PublicationError):
            metadata.validate_source(item.source_path, item.payload)


if __name__ == "__main__":
    unittest.main()
