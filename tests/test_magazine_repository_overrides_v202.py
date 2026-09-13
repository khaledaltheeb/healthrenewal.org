from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "apply_magazine_repository_overrides_v202.py"
OVERRIDES = ROOT / "data" / "magazine-source-overrides-v202.json"

spec = importlib.util.spec_from_file_location("magazine_repo_overrides", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class MagazineRepositoryOverridesV202Tests(unittest.TestCase):
    def test_registry_uses_only_explicit_https_authoritative_records(self) -> None:
        records = mod.load_overrides(OVERRIDES)
        self.assertEqual(len(records), 4)
        for path, record in records.items():
            self.assertTrue(path.startswith("magazine/"))
            self.assertEqual(record["verification_status"], "verified_repository")
            self.assertTrue(record["source_url"].startswith("https://"))
            self.assertIn(record["source_type"], {"university_repository", "institutional_repository"})
            self.assertTrue(record["verified_title"])
            self.assertTrue(record["institution"])

    def test_override_converts_manual_repository_source_to_verified(self) -> None:
        records = mod.load_overrides(OVERRIDES)
        path = "magazine/thesis-autism-heterogeneity-research-2025.html"
        report = {
            "summary": {},
            "pages": [
                {
                    "path": path,
                    "bibliographic_verification": "source_url_manual_review",
                    "primary_source": None,
                    "doi_records": [],
                    "pmid_records": [],
                }
            ],
        }
        merged = mod.apply_overrides(report, {path: records[path]})
        page = merged["pages"][0]
        self.assertEqual(page["bibliographic_verification"], "verified_repository")
        self.assertEqual(page["primary_source"]["kind"], "repository")
        self.assertEqual(page["primary_source"]["status"], "verified")
        self.assertEqual(merged["summary"]["repository_verified_pages"], 1)
        self.assertEqual(merged["summary"]["verified_source_pages"], 1)
        self.assertEqual(merged["summary"]["source_pages_still_requiring_manual_review"], 0)

    def test_repository_override_can_cover_non_resolving_reported_doi(self) -> None:
        records = mod.load_overrides(OVERRIDES)
        path = "magazine/pediatric-oncology/theses/bioethical-legal-dilemmas-terminal-pediatric-oncology-chatzioglou-2026/index.html"
        report = {
            "summary": {},
            "pages": [
                {
                    "path": path,
                    "bibliographic_verification": "missing_or_unverified_source",
                    "primary_source": None,
                    "doi_records": [
                        {"doi": "10.26257/heal.duth.20963", "status": "unverified"}
                    ],
                    "pmid_records": [],
                }
            ],
        }
        merged = mod.apply_overrides(report, {path: records[path]})
        self.assertEqual(merged["pages"][0]["bibliographic_verification"], "verified_repository")
        self.assertEqual(merged["summary"]["unresolved_identifier_pages_covered_by_repository"], 1)


if __name__ == "__main__":
    unittest.main()
