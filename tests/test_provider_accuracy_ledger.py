from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from scripts.verify_provider_accuracy_ledger import validate


ROOT = Path(__file__).resolve().parents[1]


class ProviderAccuracyLedgerTests(unittest.TestCase):
    def test_repository_contract_passes(self) -> None:
        report = validate(ROOT)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["fieldLevelEvidenceRequired"])
        self.assertFalse(report["sensitiveDocumentsPublic"])

    def test_published_profile_cannot_bypass_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for relative in (
                "specialists-partners/data/providers.json",
                "specialists-partners/data/verification-ledger.json",
                "specialists-partners/data/verification-ledger.schema.json",
                "api/v1/specialists-partners.json",
                "api/v1/platform.json",
            ):
                source = ROOT / relative
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())

            providers_path = target / "specialists-partners/data/providers.json"
            providers = json.loads(providers_path.read_text(encoding="utf-8"))
            providers["providers"] = [{
                "id": "example-provider",
                "publicationStatus": "published",
                "verification": {"status": "verified"},
                "consent": {"publicProfileApproved": True},
            }]
            providers_path.write_text(json.dumps(providers), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "lacks verified ledger record"):
                validate(target)

    def test_expired_review_cannot_support_publication(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            for relative in (
                "specialists-partners/data/providers.json",
                "specialists-partners/data/verification-ledger.json",
                "specialists-partners/data/verification-ledger.schema.json",
                "api/v1/specialists-partners.json",
                "api/v1/platform.json",
            ):
                source = ROOT / relative
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())

            providers_path = target / "specialists-partners/data/providers.json"
            providers = json.loads(providers_path.read_text(encoding="utf-8"))
            providers["providers"] = [{
                "id": "expired-provider",
                "publicationStatus": "published",
                "verification": {"status": "verified"},
                "consent": {"publicProfileApproved": True},
            }]
            providers_path.write_text(json.dumps(providers), encoding="utf-8")

            ledger_path = target / "specialists-partners/data/verification-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["records"] = [{
                "providerId": "expired-provider",
                "reviewStatus": "verified",
                "reviewedAt": date.today().isoformat(),
                "reviewerRole": "إدارة التحقق",
                "reviewedFields": [{
                    "field": "displayName",
                    "result": "verified",
                    "evidenceTypes": ["identity"],
                    "evidenceRefs": ["private:identity:example"],
                    "checkedAt": date.today().isoformat(),
                }],
                "evidenceSummary": {"publicSources": 0, "privateDocuments": 1, "independentSources": 0},
                "nextReviewAt": (date.today() - timedelta(days=1)).isoformat(),
                "correctionStatus": "none",
            }]
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "verification has expired"):
                validate(target)


if __name__ == "__main__":
    unittest.main()
