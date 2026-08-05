from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "ensure_special_needs_publication_v1.py"
SPEC = importlib.util.spec_from_file_location("ensure_special_needs_publication_v1", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load publication contract: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SpecialNeedsPublicationRepairTests(unittest.TestCase):
    def _inventory(self, **overrides: int):
        counts = dict(MODULE.MINIMUM_COUNTS)
        counts.update(overrides)
        return MODULE.Inventory(counts=counts, routes={}, missing_roots=[])

    def test_condition_deficit_triggers_repair_even_when_total_is_sufficient(self) -> None:
        inventory = self._inventory(
            capability_pages=MODULE.MINIMUM_COUNTS["capability_pages"],
            capability_condition_pages=MODULE.MINIMUM_COUNTS["capability_condition_pages"] - 1,
        )
        self.assertTrue(MODULE._capability_repair_required(inventory))

    def test_v281_payload_is_built_before_publish_and_removed_afterward(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary) / "repo"
            site_root = Path(temporary) / "site"
            repo_root.mkdir()
            site_root.mkdir()
            payload = repo_root / MODULE.V281_PAYLOAD_PATH
            calls: list[tuple[str, tuple[str, ...]]] = []

            def fake_run(_repo_root: Path, script_name: str, *args: str | Path) -> None:
                calls.append((script_name, tuple(str(argument) for argument in args)))
                if script_name == "build_conditions_v281_data.py":
                    payload.parent.mkdir(parents=True, exist_ok=True)
                    payload.write_bytes(b"generated-payload")

            with patch.object(MODULE, "_run_script", side_effect=fake_run):
                actions = MODULE._publish_v281_conditions(repo_root, site_root)

            self.assertEqual(
                actions,
                ["build_conditions_v281_data.py", "publish_conditions_v281.py"],
            )
            self.assertEqual(
                calls,
                [
                    ("build_conditions_v281_data.py", ()),
                    ("publish_conditions_v281.py", (str(site_root),)),
                ],
            )
            self.assertFalse(payload.exists())

    def test_preexisting_v281_payload_is_restored_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary) / "repo"
            site_root = Path(temporary) / "site"
            payload = repo_root / MODULE.V281_PAYLOAD_PATH
            payload.parent.mkdir(parents=True, exist_ok=True)
            site_root.mkdir()
            payload.write_bytes(b"original-payload")

            def fake_run(_repo_root: Path, script_name: str, *args: str | Path) -> None:
                del args
                if script_name == "build_conditions_v281_data.py":
                    payload.write_bytes(b"replacement-payload")

            with patch.object(MODULE, "_run_script", side_effect=fake_run):
                MODULE._publish_v281_conditions(repo_root, site_root)

            self.assertEqual(payload.read_bytes(), b"original-payload")

    def test_child_failure_reports_script_stdout_and_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary)
            script = repo_root / "scripts" / "broken.py"
            script.parent.mkdir()
            script.write_text("raise SystemExit(7)\n", encoding="utf-8")
            completed = subprocess.CompletedProcess(
                args=[sys.executable, str(script)],
                returncode=7,
                stdout="builder context\n",
                stderr="precise failure\n",
            )

            with patch.object(MODULE.subprocess, "run", return_value=completed):
                with self.assertRaises(RuntimeError) as raised:
                    MODULE._run_script(repo_root, "broken.py")

            message = str(raised.exception)
            self.assertIn("broken.py failed with exit code 7", message)
            self.assertIn("builder context", message)
            self.assertIn("precise failure", message)

    def test_full_repair_sequence_is_ordered_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo_root = Path(temporary) / "repo"
            site_root = Path(temporary) / "site"
            repo_root.mkdir()
            site_root.mkdir()
            before = self._inventory(capability_condition_pages=0)
            after = self._inventory()

            with (
                patch.object(MODULE, "collect_inventory", side_effect=[before, after]),
                patch.object(MODULE, "_run_script") as run_script,
                patch.object(
                    MODULE,
                    "_publish_v281_conditions",
                    return_value=[
                        "build_conditions_v281_data.py",
                        "publish_conditions_v281.py",
                    ],
                ) as publish_conditions,
            ):
                result = MODULE.repair_missing_generated_families(site_root, repo_root)

            self.assertEqual(
                result["actions"],
                [
                    "publish_capabilities_v280.py",
                    "build_conditions_v281_data.py",
                    "publish_conditions_v281.py",
                    "publish_family_guide_special_education_tools_v1.py",
                ],
            )
            self.assertEqual(run_script.call_count, 2)
            self.assertEqual(
                run_script.call_args_list[0].args,
                (repo_root.resolve(), "publish_capabilities_v280.py", site_root.resolve()),
            )
            self.assertEqual(
                run_script.call_args_list[1].args,
                (
                    repo_root.resolve(),
                    "publish_family_guide_special_education_tools_v1.py",
                    site_root.resolve(),
                ),
            )
            publish_conditions.assert_called_once_with(repo_root.resolve(), site_root.resolve())


if __name__ == "__main__":
    unittest.main()
