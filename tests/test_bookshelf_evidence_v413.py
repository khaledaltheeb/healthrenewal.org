#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("v413", ROOT / "scripts" / "build_bookshelf_evidence_v413.py")
assert SPEC and SPEC.loader
V413 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V413)


class BookshelfEvidenceV413Tests(unittest.TestCase):
    def test_build_keeps_candidates_explicitly_unverified(self):
        candidate = {"book_id": "123", "title": "Reference", "url": "https://www.ncbi.nlm.nih.gov/books/123/", "verification_status": "candidate-only"}
        with patch.object(V413, "bookshelf_search", return_value=([candidate], None)):
            result = V413.build([{"path": "guide.html", "query": "child psychology"}], 5)
        self.assertEqual(result["summary"]["candidate_books"], 1)
        item = result["items"][0]
        self.assertEqual(item["bookshelf"][0]["verification_status"], "candidate-only")
        self.assertGreaterEqual(len(item["verification_checklist"]), 8)
        self.assertIn("not automatic proof", item["policy"])

    def test_empty_queries_are_skipped(self):
        result = V413.build([{"path": "x.html", "query": ""}], 5)
        self.assertEqual(result["summary"]["dossiers"], 0)


if __name__ == "__main__":
    unittest.main()
