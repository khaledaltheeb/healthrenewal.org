import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_publishing_core.py"
STAGING = ROOT / "scripts" / "build_publishing_staging.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def base_book():
    return {
        "title": {"primary": "اختبار جاهزية البيانات الوصفية"},
        "contributors": [{"name": "Author Name", "roles": ["author"]}],
        "publication": {
            "publication_date": "2026-09-11",
            "formats": [
                {
                    "format": "pdf",
                    "media_type": "application/pdf",
                    "access_status": "open",
                    "access_url": "https://healthrenewal.org/open-books/test/book.pdf",
                    "isbn": "9780000000000",
                }
            ],
        },
        "identifiers": {"doi": None},
        "subjects": [{"scheme": "Thema", "value": "Psychology"}],
        "rights": {
            "text_license": {
                "name": "CC BY 4.0",
                "url": "https://creativecommons.org/licenses/by/4.0/",
            }
        },
        "publisher": {
            "name": "Health Renewal / Rawafid",
            "url": "https://healthrenewal.org/",
        },
    }


class PublishingMetadataReadinessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = load_module(VALIDATOR, "publishing_validator_readiness_test")
        cls.staging = load_module(STAGING, "publishing_staging_readiness_test")

    def assert_same_blockers(self, book, expected):
        validator_blockers = self.validator.metadata_essential_blockers(book)
        staging_blockers = self.staging.metadata_essential_blockers(book)
        self.assertEqual(validator_blockers, staging_blockers)
        self.assertEqual(set(validator_blockers), set(expected))

    def test_complete_minimum_metadata_has_no_blockers(self):
        self.assert_same_blockers(base_book(), [])

    def test_publication_date_is_derived_requirement(self):
        book = base_book()
        book["publication"]["publication_date"] = None
        self.assert_same_blockers(book, ["missing-publication-date"])

    def test_open_full_text_url_is_derived_requirement(self):
        book = base_book()
        book["publication"]["formats"][0]["access_url"] = None
        self.assert_same_blockers(book, ["missing-open-full-text-url"])

    def test_doi_or_isbn_is_required(self):
        book = base_book()
        book["identifiers"]["doi"] = None
        book["publication"]["formats"][0]["isbn"] = None
        self.assert_same_blockers(book, ["missing-persistent-identifier"])

    def test_subject_license_and_publisher_are_not_workflow_flags(self):
        book = base_book()
        book["subjects"] = []
        book["rights"]["text_license"]["url"] = ""
        book["publisher"]["name"] = "Other Publisher"
        self.assert_same_blockers(
            book,
            [
                "missing-subject-metadata",
                "missing-license-metadata",
                "invalid-publisher-metadata",
            ],
        )


if __name__ == "__main__":
    unittest.main()
