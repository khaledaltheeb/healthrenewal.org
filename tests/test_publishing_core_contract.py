import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"


class PublishingCoreContractTest(unittest.TestCase):
    def test_core_files_exist(self):
        for path in (
            BASE / "publisher.json",
            BASE / "catalog.json",
            BASE / "schemas" / "book-record.schema.json",
            BASE / "schemas" / "rights-record.schema.json",
            BASE / "schemas" / "translation-record.schema.json",
            ROOT / "api" / "v1" / "open-books.json",
            ROOT / "publishing" / "index.html",
            ROOT / "open-books" / "index.html",
        ):
            self.assertTrue(path.is_file(), str(path))

    def test_role_model_is_explicit(self):
        data = json.loads((BASE / "publisher.json").read_text(encoding="utf-8"))
        roles = data["roles"]
        self.assertTrue(roles["own_original_works"]["allowed"])
        self.assertTrue(roles["licensed_translations"]["allowed"])
        self.assertEqual(roles["authorized_co_management"]["allowed"], "conditional")
        self.assertEqual(data["thoth"]["literary_work_policy"], "hold_for_thoth_confirmation")

    def test_book_schema_separates_record_types(self):
        schema = json.loads((BASE / "schemas" / "book-record.schema.json").read_text(encoding="utf-8"))
        values = schema["properties"]["record_type"]["enum"]
        self.assertEqual(set(values), {"rawafid-original", "licensed-translation", "authorized-co-managed", "discovery-only"})

    def test_rights_schema_requires_thoth_cc0_acknowledgement(self):
        schema = json.loads((BASE / "schemas" / "rights-record.schema.json").read_text(encoding="utf-8"))
        self.assertIn("thoth_metadata_cc0_acknowledged", schema["required"])

    def test_public_pages_are_indexable_and_canonical(self):
        for route in ("publishing", "open-books"):
            html = (ROOT / route / "index.html").read_text(encoding="utf-8")
            self.assertIn('name="robots" content="index,follow', html)
            self.assertIn(f"https://healthrenewal.org/{route}/", html)
            self.assertNotIn("noindex", html.lower())
            self.assertEqual(html.lower().count("<h1"), 1)

    def test_builder_and_validator_pass(self):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_publishing_catalog.py"), "--check"], cwd=ROOT, check=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_publishing_core.py")], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
