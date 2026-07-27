from __future__ import annotations

import unittest

from scripts.verify_specialists_partners_import_template import EXPECTED_HEADERS, validate_text


class SpecialistsPartnersImportTemplateTests(unittest.TestCase):
    def valid_csv(self) -> str:
        header = ",".join(EXPECTED_HEADERS)
        values = {name: "" for name in EXPECTED_HEADERS}
        values.update(
            {
                "id": "example-slug",
                "entityType": "professional",
                "location.country": "Jordan",
                "location.city": "Amman",
                "verification.status": "pending",
                "publicationStatus": "draft",
                "consent.publicProfileApproved": "false",
            }
        )
        row = ",".join(values[name] for name in EXPECTED_HEADERS)
        return f"{header}\n{row}\n"

    def test_valid_nested_template_passes(self) -> None:
        report = validate_text(self.valid_csv())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["header_count"], len(EXPECTED_HEADERS))
        self.assertTrue(report["nested_consent"])

    def test_flattened_consent_header_is_rejected(self) -> None:
        text = self.valid_csv().replace("consent.publicProfileApproved", "publicProfileApproved")
        with self.assertRaisesRegex(AssertionError, "nested JSON contract"):
            validate_text(text)

    def test_example_cannot_claim_consent(self) -> None:
        text = self.valid_csv().replace(",false,\n", ",true,2026-07-27\n")
        with self.assertRaisesRegex(AssertionError, "must not imply publication consent"):
            validate_text(text)


if __name__ == "__main__":
    unittest.main()
