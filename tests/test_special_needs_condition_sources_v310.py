from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_special_needs_condition_sources_v310 as source310


class SpecialNeedsConditionSourcesV310Tests(unittest.TestCase):
    def test_existing_condition_sources_pass_metadata_and_traceability_audit(self) -> None:
        report = source310.audit(today=date(2026, 7, 27))
        self.assertEqual(report["version"], 310)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["condition_slugs"], ["autism", "down-syndrome"])
        self.assertEqual(report["source_count"], 17)
        self.assertGreaterEqual(report["distinct_host_count"], 3)
        for condition in report["conditions"]:
            self.assertGreaterEqual(condition["source_count"], 5)
            self.assertGreaterEqual(condition["distinct_host_count"], 3)
            self.assertEqual(condition["overdue_source_ids"], [])
            self.assertTrue(all(value > 0 for value in condition["source_usage"].values()))

    def test_report_is_written_for_the_publication_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            site.mkdir()
            report = source310.publish(site, today=date(2026, 7, 27))
            api = json.loads(
                (site / "api" / "special-needs-condition-source-maintenance-v310.json").read_text(encoding="utf-8")
            )
            self.assertEqual(api, report)
            self.assertEqual(api["source_count"], 17)

    def test_tracking_parameter_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            source310.validate_url("https://example.org/guideline?utm_source=test", "A1")

    def test_shortened_source_url_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            source310.validate_url("https://bit.ly/example", "D1")

    def test_stale_orphaned_source_is_rejected(self) -> None:
        original_files = source310.CONDITION_FILES
        with tempfile.TemporaryDirectory() as tmp:
            payload = copy.deepcopy(json.loads(original_files[0].read_text(encoding="utf-8")))
            orphan = copy.deepcopy(payload["sources"][0])
            orphan["id"] = "A99"
            orphan["url"] = "https://example.org/orphaned-old-guideline"
            orphan["organization"] = "Example institution"
            orphan["title"] = "Old orphaned guideline"
            orphan["reviewed"] = "2020-01-01"
            payload["sources"].append(orphan)
            path = Path(tmp) / "autism.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            source310.CONDITION_FILES = (path, original_files[1])
            try:
                with self.assertRaises(SystemExit):
                    source310.audit(today=date(2026, 7, 27))
            finally:
                source310.CONDITION_FILES = original_files


if __name__ == "__main__":
    unittest.main()
