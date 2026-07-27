import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.audit_source_evidence_v75 import audit_repository


class SourceEvidenceAuditTests(unittest.TestCase):
    def make_repo(self, payloads):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for relative, payload in payloads.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return temp, root

    def test_legacy_record_is_warning_not_error(self):
        temp, root = self.make_repo(
            {
                "content/guide.json": {
                    "sources": [
                        {
                            "publisher": "World Health Organization",
                            "title": "Guidance",
                            "url": "https://www.who.int/example",
                            "year": 2025,
                        }
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["legacy_object_records"], 1)
        self.assertEqual(report["warning_count"], 1)

    def test_url_only_legacy_source_is_warning_not_error(self):
        temp, root = self.make_repo(
            {
                "content/sector.json": {
                    "sources": [
                        "https://www.who.int/example",
                        "https://www.unicef.org/example",
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["legacy_url_records"], 2)
        self.assertEqual(report["warning_count"], 2)
        self.assertTrue(all(item["url"] for item in report["records"]))

    def test_name_url_legacy_object_is_warning_not_error(self):
        temp, root = self.make_repo(
            {
                "content/sector.json": {
                    "sources": [
                        {
                            "name": "WHO — Mental health guidance",
                            "url": "https://www.who.int/example",
                        }
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["legacy_name_url_records"], 1)
        self.assertIn("legacy-name-url-source", {item["code"] for item in report["warnings"]})

    def test_numeric_string_year_is_legacy_warning(self):
        temp, root = self.make_repo(
            {
                "content/guide.json": {
                    "sources": [
                        {
                            "publisher": "World Health Organization",
                            "title": "Guidance",
                            "url": "https://www.who.int/example",
                            "year": "2025",
                        }
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertEqual(report["error_count"], 0)
        codes = {item["code"] for item in report["warnings"]}
        self.assertIn("legacy-year-string", codes)
        self.assertIn("legacy-source-record", codes)

    def test_contract_ready_record_passes(self):
        temp, root = self.make_repo(
            {
                "data/evidence.json": {
                    "references": [
                        {
                            "id": "who-example-guidance",
                            "publisher": "World Health Organization",
                            "title": "Guidance",
                            "url": "https://www.who.int/example",
                            "year": 2025,
                            "source_type": "official_guideline",
                            "verified_at": "2026-07-20",
                            "claims_supported": ["definition", "help-seeking"],
                            "status": "current",
                        }
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["contract_ready_records"], 1)
        self.assertEqual(report["warning_count"], 0)

    def test_traceable_summary_contract_passes(self):
        temp, root = self.make_repo(
            {
                "content/condition.json": {
                    "sections": [{"id": "definition", "source_ids": ["A1"]}],
                    "sources": [
                        {
                            "id": "A1",
                            "organization": "منظمة الصحة العالمية",
                            "title": "Autism fact sheet",
                            "url": "https://www.who.int/example",
                            "level": "S1",
                            "reviewed": "2026-07-20",
                        }
                    ],
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["warning_count"], 0)
        self.assertEqual(report["contract_ready_records"], 1)
        self.assertEqual(report["traceable_summary_records"], 1)
        self.assertEqual(report["records"][0]["publisher"], "منظمة الصحة العالمية")
        self.assertEqual(report["records"][0]["year"], 2026)

    def test_traceable_summary_rejects_invalid_level_and_future_review(self):
        temp, root = self.make_repo(
            {
                "content/condition.json": {
                    "sources": [
                        {
                            "id": "a1",
                            "organization": "Example",
                            "title": "Guidance",
                            "url": "https://example.org/guidance",
                            "level": "S9",
                            "reviewed": "2027-01-01",
                        }
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("invalid-summary-source-id", codes)
        self.assertIn("invalid-evidence-level", codes)
        self.assertIn("future-reviewed-date", codes)

    def test_contract_ready_record_rejects_string_year(self):
        temp, root = self.make_repo(
            {
                "data/evidence.json": {
                    "references": [
                        {
                            "id": "who-example-guidance",
                            "publisher": "World Health Organization",
                            "title": "Guidance",
                            "url": "https://www.who.int/example",
                            "year": "2025",
                            "source_type": "official_guideline",
                            "verified_at": "2026-07-20",
                            "claims_supported": ["definition"],
                            "status": "current",
                        }
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertIn("invalid-year", {item["code"] for item in report["errors"]})

    def test_unsafe_and_duplicate_sources_fail(self):
        bad = {
            "publisher": "Example",
            "title": "Bad source",
            "url": "http://example.com/source",
            "year": 2099,
        }
        temp, root = self.make_repo({"content/bad.json": {"citations": [bad, dict(bad)]}})
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("non-https-source", codes)
        self.assertIn("implausible-year", codes)
        self.assertIn("duplicate-source-url", codes)

    def test_non_https_url_only_source_fails(self):
        temp, root = self.make_repo({"content/bad-url.json": {"sources": ["http://example.com/source"]}})
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertIn("non-https-source", {item["code"] for item in report["errors"]})

    def test_partial_advanced_metadata_fails(self):
        temp, root = self.make_repo(
            {
                "content/partial.json": {
                    "sources": [
                        {
                            "publisher": "NICE",
                            "title": "Guideline",
                            "url": "https://www.nice.org.uk/guidance/example",
                            "year": 2024,
                            "source_type": "official_guideline",
                        }
                    ]
                }
            }
        )
        self.addCleanup(temp.cleanup)
        report = audit_repository(root, today=date(2026, 7, 22))
        self.assertIn("partial-advanced-contract", {item["code"] for item in report["errors"]})


if __name__ == "__main__":
    unittest.main()
