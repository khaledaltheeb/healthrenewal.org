import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "data" / "publishing" / "thoth-schema-contract.json"


class ThothEnumMappingContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.enums = cls.contract["verified_enums"]
        cls.mapping = cls.contract["safe_local_mappings"]

    def assert_mapping_values_are_verified(self, mapping_key: str, enum_key: str):
        values = set(self.mapping[mapping_key].values())
        verified = set(self.enums[enum_key])
        self.assertLessEqual(values, verified, f"{mapping_key} has values outside {enum_key}: {values - verified}")

    def test_every_automatic_mapping_targets_verified_thoth_values(self):
        for mapping_key, enum_key in (
            ("work_type", "workType"),
            ("work_status", "workStatus"),
            ("publication_format", "publicationType"),
            ("language", "languageCode"),
            ("locale", "localeCode"),
            ("language_relation", "languageRelation"),
            ("subject_scheme", "subjectType"),
            ("contributor_role", "contributionType"),
            ("accessibility_standard", "accessibilityStandard"),
        ):
            with self.subTest(mapping=mapping_key, enum=enum_key):
                self.assert_mapping_values_are_verified(mapping_key, enum_key)

    def test_publisher_location_is_verified(self):
        self.assertIn(self.mapping["publisher_full_text_location"], self.enums["locationPlatform"])
        self.assertEqual(self.mapping["publisher_full_text_location"], "PUBLISHER_WEBSITE")

    def test_sha256_algorithm_is_verified(self):
        self.assertIn("SHA256", self.enums["checksumAlgorithm"])

    def test_locally_used_language_and_locale_values_are_pinned(self):
        self.assertEqual(set(self.mapping["language"].values()), {"ARA", "ENG"})
        self.assertEqual(set(self.mapping["locale"].values()), {"AR", "EN"})
        self.assertLessEqual({"ARA", "ENG"}, set(self.enums["languageCode"]))
        self.assertLessEqual({"AR", "EN"}, set(self.enums["localeCode"]))

    def test_ambiguous_types_remain_outside_automatic_mapping(self):
        auto = set(self.mapping["work_type"])
        manual = set(self.mapping["work_type_requires_editorial_mapping"])
        forbidden = set(self.mapping["work_type_forbidden_pending_thoth_confirmation"])
        self.assertTrue(auto.isdisjoint(manual))
        self.assertTrue(auto.isdisjoint(forbidden))
        self.assertTrue(manual.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
