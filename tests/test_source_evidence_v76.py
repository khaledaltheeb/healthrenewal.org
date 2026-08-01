from __future__ import annotations

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

import audit_source_evidence_v76 as audit  # noqa: E402


REGISTRY_SOURCE = {
    "id": "who-adolescent-mental-health",
    "name": "Adolescent mental health",
    "organization": "World Health Organization",
    "url": "https://www.who.int/news-room/fact-sheets/detail/adolescent-mental-health",
    "type": "institutional fact sheet",
    "scope": "Mental-health risks, protective factors and service responses.",
}


class SourceEvidenceV76Tests(unittest.TestCase):
    def write_payload(self, root: Path, payload: dict) -> Path:
        path = root / "content" / "sample.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_resolved_registry_reference_is_contract_ready(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_payload(
                root,
                {
                    "sources": [REGISTRY_SOURCE],
                    "guides": [
                        {
                            "slug": "example",
                            "sources": ["who-adolescent-mental-health"],
                        }
                    ],
                },
            )
            records, findings = audit.audit_file(path, root, date(2026, 7, 31))
            self.assertFalse([item for item in findings if item.severity == "error"])
            formats = [item["record_format"] for item in records]
            self.assertIn("central-registry-object", formats)
            self.assertIn("central-registry-reference", formats)
            self.assertTrue(all(item["contract_ready"] for item in records))

    def test_unknown_registry_reference_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.write_payload(
                root,
                {
                    "sources": [REGISTRY_SOURCE],
                    "guides": [{"sources": ["missing-source-id"]}],
                },
            )
            _, findings = audit.audit_file(path, root, date(2026, 7, 31))
            self.assertTrue(
                any(item.code == "non-https-source" for item in findings),
                findings,
            )

    def test_duplicate_registry_id_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            duplicate = {**REGISTRY_SOURCE, "url": "https://example.org/duplicate"}
            path = self.write_payload(
                root,
                {"sources": [REGISTRY_SOURCE, duplicate], "guides": []},
            )
            _, findings = audit.audit_file(path, root, date(2026, 7, 31))
            self.assertTrue(
                any(item.code == "duplicate-registry-source-id" for item in findings),
                findings,
            )

    def test_invalid_registry_url_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invalid = {**REGISTRY_SOURCE, "url": "http://example.org/source"}
            path = self.write_payload(root, {"sources": [invalid]})
            _, findings = audit.audit_file(path, root, date(2026, 7, 31))
            self.assertTrue(
                any(item.code == "non-https-source" for item in findings),
                findings,
            )


if __name__ == "__main__":
    unittest.main()
