import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"
SCRIPT = ROOT / "scripts" / "build_thoth_upload_plan.py"
PLAN = BASE / "thoth-upload-plan.json"
CONTRACT = BASE / "thoth-schema-contract.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    sys.path.insert(0, str(path.parent))
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def sample_book():
    return {
        "id": "test-monograph",
        "slug": "test-monograph",
        "record_type": "rawafid-original",
        "work_type": "scholarly-monograph",
        "title": {
            "primary": "كتاب اختباري",
            "primary_language": "ar",
            "subtitle": "لاختبار الربط الآمن",
        },
        "language": "ar",
        "original_language": None,
        "abstract": "ملخص اختباري للتحقق من خطة الربط فقط.",
        "publisher": {
            "name": "Health Renewal / Rawafid",
            "short_name": "Rawafid",
            "url": "https://healthrenewal.org/",
            "imprint": "Rawafid",
        },
        "contributors": [
            {
                "name": "Khaled Altheeb",
                "given_name": "Khaled",
                "family_name": "Altheeb",
                "roles": ["author"],
                "main_contribution": True,
                "orcid": None,
                "website": None,
            }
        ],
        "publication": {
            "status": "published",
            "publication_date": "2026-09-11",
            "edition": "1",
            "formats": [
                {
                    "format": "pdf",
                    "media_type": "application/pdf",
                    "isbn": "9780306406157",
                    "access_url": "https://healthrenewal.org/open-books/test-monograph/book.pdf",
                    "access_status": "open",
                    "checksum_sha256": None,
                }
            ],
        },
        "identifiers": {"doi": "10.1234/rawafid.test", "work_id": None},
        "subjects": [
            {"scheme": "Thema", "code": "JM", "value": "Psychology", "language": "en"}
        ],
        "rights": {
            "rights_record_id": "rights-test-monograph",
            "copyright_holder": "Health Renewal / Rawafid",
            "text_license": {
                "name": "CC BY 4.0",
                "url": "https://creativecommons.org/licenses/by/4.0/",
            },
            "cover_rights_status": "no-cover",
            "translation_record_id": None,
        },
        "review": {"model": "scholarly-peer-review", "status": "completed", "statement_url": None},
        "accessibility": {
            "status": "validated",
            "statement_url": "https://healthrenewal.org/accessibility/",
            "conforms_to": ["WCAG 2.2 AA"],
            "access_modes": ["textual"],
            "features": [],
            "hazards": [],
        },
        "workflow": {
            "current_state": "ready-for-thoth",
            "gates": {
                "rights": "passed",
                "editorial": "passed",
                "scientific": "passed",
                "accessibility": "passed",
                "metadata": "passed",
                "files": "passed",
            },
            "updated_at": "2026-09-11",
        },
        "thoth": {"eligibility": "eligible", "upload_allowed": True, "reason": "test only"},
        "provenance": {"created_at": "2026-09-11", "updated_at": "2026-09-11", "source": "rawafid-original"},
        "public_visibility": True,
    }


class ThothUploadPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module(SCRIPT, "thoth_upload_plan_test")
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_committed_plan_is_current_and_non_executable(self):
        subprocess.run([sys.executable, str(SCRIPT), "--check"], cwd=ROOT, check=True)
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        self.assertFalse(plan["execution_enabled"])
        self.assertFalse(plan["transmission_permitted"])
        self.assertEqual(plan["credential_inputs"], [])
        serialized = json.dumps(plan).lower()
        self.assertNotIn("auth.thoth.pub/ui/login/user/invite", serialized)
        self.assertNotIn("bearer ", serialized)
        self.assertNotIn("thoth_pat=", serialized)

    def test_verified_monograph_maps_without_metadata_blockers(self):
        result = self.module.map_book(sample_book(), self.contract)
        self.assertTrue(result["ready_for_offline_template_review"], result["blockers"])
        self.assertFalse(result["transmission_permitted"])
        operations = result["operations"]
        work = next(item for item in operations if item["operation"] == "createWork")
        self.assertEqual(work["data"]["workType"], "MONOGRAPH")
        self.assertEqual(work["data"]["workStatus"], "ACTIVE")
        self.assertEqual(work["data"]["doi"], "https://doi.org/10.1234/rawafid.test")
        language = next(item for item in operations if item["operation"] == "createLanguage")
        self.assertEqual(language["data"]["languageCode"], "ARA")
        self.assertEqual(language["data"]["languageRelation"], "ORIGINAL")
        publication = next(item for item in operations if item["operation"] == "createPublication")
        self.assertEqual(publication["data"]["publicationType"], "PDF")
        self.assertEqual(publication["data"]["accessibilityStandard"], "WCAG22AA")
        location = next(item for item in operations if item["operation"] == "createLocation")
        self.assertEqual(location["data"]["locationPlatform"], "PUBLISHER_WEBSITE")

    def test_ambiguous_work_type_is_blocked_not_guessed(self):
        book = sample_book()
        book["work_type"] = "handbook"
        result = self.module.map_book(book, self.contract)
        self.assertIn("work-type-requires-explicit-mapping:handbook", result["blockers"])
        self.assertFalse(result["ready_for_offline_template_review"])

    def test_print_format_is_blocked_until_binding_is_explicit(self):
        book = sample_book()
        book["publication"]["formats"][0]["format"] = "print"
        result = self.module.map_book(book, self.contract)
        self.assertIn("format-1-requires-explicit-thoth-publication-type:print", result["blockers"])

    def test_contributor_family_name_and_main_role_are_never_inferred(self):
        book = sample_book()
        book["contributors"][0]["family_name"] = None
        book["contributors"][0]["main_contribution"] = None
        result = self.module.map_book(book, self.contract)
        self.assertIn("contributor-1-missing-verified-family-name", result["blockers"])
        self.assertIn("contributor-1-missing-main-contribution-decision", result["blockers"])

    def test_invalid_identifiers_are_blocked(self):
        book = sample_book()
        book["identifiers"]["doi"] = "not-a-doi"
        book["publication"]["formats"][0]["isbn"] = "9780000000000"
        result = self.module.map_book(book, self.contract)
        self.assertIn("invalid-doi", result["blockers"])
        self.assertIn("format-1-invalid-isbn13", result["blockers"])


if __name__ == "__main__":
    unittest.main()
