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

import validate_special_needs_provider_directory_v308 as governance


class SpecialNeedsProviderDirectoryV308Tests(unittest.TestCase):
    def config(self) -> dict:
        return json.loads(governance.PROVIDERS.read_text(encoding="utf-8"))

    def valid_provider(self) -> dict:
        provider = copy.deepcopy(self.config()["example_not_published"])
        provider.update(
            {
                "id": "provider-valid-001",
                "name_ar": "مركز نمو موثق",
                "phone_display": "+962 79 000 0000",
                "phone_uri": "+962790000000",
                "verification_status": "verified",
                "verified_at": "2026-07-01",
                "last_contact_verified_at": "2026-07-20",
                "verification_expires_at": "2027-01-20",
                "verification_evidence": ["https://example.org/registry/provider-valid-001"],
                "registration_authority": "السجل المهني التجريبي",
                "registration_reference": "REG-001",
                "listing_disclosure": "editorial",
                "sponsored": False,
                "published": True,
            }
        )
        return provider

    def test_empty_editable_directory_passes_and_writes_machine_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp) / "site"
            site.mkdir()
            report = governance.publish(site, today=date(2026, 7, 27))
            self.assertEqual(report["version"], 308)
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["record_count"], 0)
            self.assertEqual(report["published_count"], 0)
            self.assertFalse(report["sponsored_publication_enabled"])
            api = json.loads((site / "api" / "special-needs-provider-governance-v308.json").read_text(encoding="utf-8"))
            self.assertEqual(api["status_counts"]["verified"], 0)

    def test_current_verified_editorial_provider_can_publish(self) -> None:
        data = self.config()
        data["providers"] = [self.valid_provider()]
        report = governance.validate_provider_data(data, today=date(2026, 7, 27))
        self.assertEqual(report["published_count"], 1)
        self.assertEqual(report["sponsored_count"], 0)
        self.assertEqual(report["status_counts"]["verified"], 1)

    def test_expired_provider_cannot_remain_published(self) -> None:
        data = self.config()
        provider = self.valid_provider()
        provider["verification_expires_at"] = "2026-07-26"
        data["providers"] = [provider]
        with self.assertRaises(SystemExit):
            governance.validate_provider_data(data, today=date(2026, 7, 27))

    def test_sponsored_listing_requires_explicit_matching_disclosure(self) -> None:
        data = self.config()
        provider = self.valid_provider()
        provider["sponsored"] = True
        provider["listing_disclosure"] = "editorial"
        data["providers"] = [provider]
        with self.assertRaises(SystemExit):
            governance.validate_provider_data(data, today=date(2026, 7, 27))

    def test_even_matching_sponsored_record_is_blocked_until_public_label_renderer_exists(self) -> None:
        data = self.config()
        provider = self.valid_provider()
        provider["sponsored"] = True
        provider["listing_disclosure"] = "sponsored"
        data["providers"] = [provider]
        with self.assertRaises(SystemExit):
            governance.validate_provider_data(data, today=date(2026, 7, 27))

    def test_published_provider_requires_registration_and_verification_evidence(self) -> None:
        data = self.config()
        provider = self.valid_provider()
        provider["verification_evidence"] = []
        provider["registration_reference"] = ""
        data["providers"] = [provider]
        with self.assertRaises(SystemExit):
            governance.validate_provider_data(data, today=date(2026, 7, 27))


if __name__ == "__main__":
    unittest.main()
