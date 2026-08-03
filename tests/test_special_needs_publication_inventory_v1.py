from __future__ import annotations

import runpy
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "ensure_special_needs_publication_v1.py"


class SpecialNeedsPublicationInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = runpy.run_path(str(MODULE), run_name="special_needs_inventory_test")
        cls.minimums = dict(cls.ns["MINIMUM_COUNTS"])

    def test_minimum_contract_covers_all_required_families(self):
        self.assertEqual(
            self.minimums,
            {
                "capability_pages": 155,
                "capability_condition_pages": 150,
                "special_needs_practical_guides": 60,
                "family_condition_guides": 64,
                "family_tools": 15,
                "learning_paths": 15,
                "child_guides": 10,
                "family_guides": 8,
                "home_guides": 7,
            },
        )

    def test_validate_counts_fails_closed_on_one_missing_page(self):
        counts = dict(self.minimums)
        counts["special_needs_practical_guides"] -= 1
        failures = self.ns["validate_counts"](counts)
        self.assertEqual(
            failures,
            {"special_needs_practical_guides": {"actual": 59, "minimum": 60}},
        )

    def test_collect_inventory_counts_real_route_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            samples = {
                "capabilities/autism/index.html": "capability_pages",
                "special-needs/practical/example/index.html": "special_needs_practical_guides",
                "family-guide/conditions/example/index.html": "family_condition_guides",
                "family-guide/tools/example/index.html": "family_tools",
                "learning-paths/example/index.html": "learning_paths",
                "sectors/child/guides/example/index.html": "child_guides",
                "sectors/family/guides/example/index.html": "family_guides",
                "sectors/home/guides/example/index.html": "home_guides",
            }
            for relative in samples:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("<h1>test</h1>", encoding="utf-8")
            inventory = self.ns["collect_inventory"](root)
            for key in samples.values():
                self.assertEqual(inventory.counts[key], 1, key)
            self.assertEqual(inventory.counts["capability_condition_pages"], 1)

    def test_source_checkout_is_never_materialized_by_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            result = self.ns["repair_missing_generated_families"](root, root)
            self.assertEqual(result["actions"], [])


if __name__ == "__main__":
    unittest.main()
