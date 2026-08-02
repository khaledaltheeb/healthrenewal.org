from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.validate_source_rights_registry import validate_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "api" / "source-rights-registry.json"


class SourceRightsRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_published_registry_is_valid(self) -> None:
        self.assertEqual(validate_registry(self.registry), [])

    def test_duplicate_source_id_is_rejected(self) -> None:
        candidate = deepcopy(self.registry)
        duplicate = deepcopy(candidate["sources"][0])
        duplicate["official_url"] = "https://example.org/duplicate-source"
        candidate["sources"].append(duplicate)

        errors = validate_registry(candidate)
        self.assertTrue(any("Duplicate source id" in error for error in errors))

    def test_link_only_source_cannot_allow_copying(self) -> None:
        candidate = deepcopy(self.registry)
        source = next(
            item for item in candidate["sources"] if item["rights_status"] == "link_only"
        )
        source["permissions"]["copy"] = "allowed"

        errors = validate_registry(candidate)
        self.assertTrue(any("link_only cannot mark copy=allowed" in error for error in errors))

    def test_open_reuse_requires_named_licence(self) -> None:
        candidate = deepcopy(self.registry)
        source = next(
            item for item in candidate["sources"] if item["rights_status"] == "open_reuse"
        )
        source["licence"]["name"] = None

        errors = validate_registry(candidate)
        self.assertTrue(any("open_reuse requires a named licence" in error for error in errors))

    def test_relationship_claim_cannot_be_promoted_to_partner(self) -> None:
        candidate = deepcopy(self.registry)
        candidate["sources"][0]["relationship_status"] = "partner"

        errors = validate_registry(candidate)
        self.assertTrue(
            any("independent_source_not_partner" in error for error in errors)
        )

    def test_permission_enum_is_closed(self) -> None:
        candidate = deepcopy(self.registry)
        candidate["sources"][0]["permissions"]["translate"] = "probably_allowed"

        errors = validate_registry(candidate)
        self.assertTrue(any("invalid value" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
