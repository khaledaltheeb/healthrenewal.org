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

core.ROOT = ROOT
core.BASE_PUBLISHER = ROOT / "scripts/publish_outside_the_box_v254.py"
core.TEN_PUBLISHER = ROOT / "scripts/publish_outside_the_box_ten_plans_v302.py"
core.REFERENCE_PUBLISHER = ROOT / "scripts/publish_outside_the_box_reference_assets_v303.py"
core.REVIEW_PUBLISHER = ROOT / "scripts/publish_outside_the_box_review_governance_v305.py"
core.AUDITOR = ROOT / "scripts/audit_outside_the_box_quality_v306.py"


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
