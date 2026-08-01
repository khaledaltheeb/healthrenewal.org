from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "tests" / "support" / "outside_box_quality_audit_v306_core.py"
spec = importlib.util.spec_from_file_location(
    "outside_box_quality_audit_v306_core",
    CORE_PATH,
)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load outside-the-box quality audit test core")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class OutsideBoxQualityAuditV306(core.OutsideBoxQualityAuditV306):
    def setUp(self) -> None:
        super().setUp()
        for relative in ("assets/platform", "copyright"):
            source = ROOT / relative
            target = self.site / relative
            if not source.is_dir():
                self.fail(f"Missing platform fixture source: {source}")
            shutil.copytree(source, target, dirs_exist_ok=True)


if __name__ == "__main__":
    import unittest

    unittest.main()
