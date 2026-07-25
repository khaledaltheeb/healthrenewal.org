from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import apply_homepage_v20 as entry


class HomepageHeaderIntegrationV233Tests(unittest.TestCase):
    def test_entrypoint_runs_existing_builder_before_header_publisher(self) -> None:
        calls: list[object] = []

        def build() -> None:
            calls.append("builder")

        def publish(site: object) -> dict[str, object]:
            calls.append(("header", site))
            return {"status": "passed", "version": 233}

        with patch.object(entry._base, "main", side_effect=build), patch.object(
            entry, "_publish_header", side_effect=publish
        ):
            entry.main()

        self.assertEqual(calls[0], "builder")
        self.assertEqual(calls[1], ("header", entry._base.SITE))

    def test_entrypoint_rejects_failed_header_report(self) -> None:
        with patch.object(entry._base, "main", return_value=None), patch.object(
            entry,
            "_publish_header",
            return_value={"status": "failed", "version": 233},
        ):
            with self.assertRaises(SystemExit):
                entry.main()

    def test_public_builder_contract_is_reexported(self) -> None:
        self.assertIs(entry.run_publisher, entry._base.run_publisher)
        self.assertIs(entry.restore_static_route, entry._base.restore_static_route)
        self.assertIs(entry.synchronize_homepage_lab_inventory, entry._base.synchronize_homepage_lab_inventory)
        self.assertEqual(entry.LAB_TOOL_COUNT, 93)


if __name__ == "__main__":
    unittest.main()
