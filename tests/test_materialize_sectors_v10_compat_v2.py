from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "materialize_sectors_v10_compat_v2.py"
SPEC = importlib.util.spec_from_file_location("materialize_sectors_v10_compat_v2", SCRIPT_PATH)
assert SPEC and SPEC.loader
compat = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = compat
SPEC.loader.exec_module(compat)


class MaterializeSectorsV10CompatTests(unittest.TestCase):
    def test_normalizes_structured_reference_records(self) -> None:
        payload = {
            "sources": [
                {
                    "publisher": "World Health Organization",
                    "title": "Official guidance",
                    "url": "https://www.who.int/example",
                },
                {"title": "NICE guidance", "href": "https://www.nice.org.uk/example"},
            ],
            "articles": [],
        }
        compat.normalize_payload(payload)
        self.assertEqual(
            payload["sources"][0]["name"],
            "World Health Organization — Official guidance",
        )
        self.assertEqual(payload["sources"][1]["name"], "NICE guidance")
        self.assertEqual(payload["sources"][1]["url"], "https://www.nice.org.uk/example")

    def test_normalizes_comparison_article_without_fabricating_claims(self) -> None:
        payload = {
            "sources": [],
            "articles": [
                {
                    "title": "مقارنة عملية",
                    "comparison_axes": [
                        {"axis": "السياق", "first": "وصف أول", "second": "وصف ثان"},
                        {"axis": "المدة", "first": "مدة أولى", "second": "مدة ثانية"},
                        {"axis": "الأثر", "first": "أثر أول", "second": "أثر ثان"},
                    ],
                }
            ],
        }
        compat.normalize_payload(payload)
        article = payload["articles"][0]
        self.assertEqual(len(article["signals"]), 3)
        self.assertIn("السياق", article["signals"][0])
        self.assertEqual(len(article["phrases"]), 2)
        self.assertIn("لن نحسم", article["phrases"][0])

    def test_preserves_official_legal_term_but_rejects_prohibited_word(self) -> None:
        self.assertNotIn("ذوي الإعاقة", compat.base.UNWANTED_TERMS)
        self.assertIn("معاقين", compat.base.UNWANTED_TERMS)
        self.assertIn("المعاقين", compat.base.UNWANTED_TERMS)

    def _make_reviewed_repo(self) -> Path:
        root = Path(tempfile.mkdtemp())
        content_root = root / compat.base.CONTENT_DIR
        content_root.mkdir(parents=True)
        for name in compat.RELEASED_MANUAL_REVIEW_SOURCES:
            (content_root / name).write_text("{}\n", encoding="utf-8")

        ledger_path = root / compat.REVIEW_LEDGER
        ledger_path.parent.mkdir(parents=True)
        ledger = {
            "schemaVersion": 1,
            "reviewedAt": "2026-08-04",
            "reviewType": "internal-editorial-and-source-structure-review",
            "clinicalReviewClaimed": False,
            "releasedSources": [
                {
                    "path": f"content/sectors-v10/{name}",
                    "decision": "publish-educational-content",
                    "reason": "Complete educational source structure.",
                }
                for name in sorted(compat.RELEASED_MANUAL_REVIEW_SOURCES)
            ],
        }
        ledger_path.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return root

    def test_editorial_release_requires_exact_nonclinical_ledger(self) -> None:
        root = self._make_reviewed_repo()
        self.assertEqual(
            compat.validated_editorial_release(root),
            compat.RELEASED_MANUAL_REVIEW_SOURCES,
        )

        ledger_path = root / compat.REVIEW_LEDGER
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        ledger["clinicalReviewClaimed"] = True
        ledger_path.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(compat.base.PublicationError):
            compat.validated_editorial_release(root)

    def test_editorial_release_fails_when_released_source_is_missing(self) -> None:
        root = self._make_reviewed_repo()
        missing_name = sorted(compat.RELEASED_MANUAL_REVIEW_SOURCES)[0]
        (root / compat.base.CONTENT_DIR / missing_name).unlink()
        with self.assertRaises(compat.base.PublicationError):
            compat.validated_editorial_release(root)


if __name__ == "__main__":
    unittest.main()
