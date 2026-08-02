from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DeploymentSchemaV353Tests(unittest.TestCase):
    def test_stamp_uses_schema_30_and_complete_deployer_is_canonical(self) -> None:
        stamp_path = ROOT / "scripts/stamp_deployment_v29.py"
        tree = ast.parse(stamp_path.read_text(encoding="utf-8"))
        assignments = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "DEPLOYMENT_SCHEMA_VERSION"
        }
        self.assertEqual(assignments["DEPLOYMENT_SCHEMA_VERSION"], 30)

        deploy = (ROOT / ".github/workflows/deploy-complete-pages-with-ai-search.yml").read_text(encoding="utf-8")
        self.assertIn("name: Deploy complete generated site", deploy)
        self.assertIn("actions/deploy-pages@v4", deploy)
        self.assertIn("path: _site", deploy)

    def test_legacy_overlay_consumers_accept_29_and_30_during_migration(self) -> None:
        scripts = (
            "verify_home_sector_deployment_v238.py",
            "verify_child_sector_deployment_v240.py",
            "verify_women_sector_deployment_v245.py",
            "verify_special_needs_deployment_v236.py",
            "verify_special_needs_hub_live_v241.py",
            "special_needs_v322_publish.py",
        )
        for name in scripts:
            source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("not in {29, 30}", source, name)

        for workflow in (
            "deploy-validated-main.yml",
            "one-shot-validated-pages-v323.yml",
        ):
            source = (ROOT / ".github/workflows" / workflow).read_text(encoding="utf-8")
            self.assertIn("Retired partial Pages publisher", source, workflow)
            self.assertNotIn("actions/deploy-pages@", source, workflow)
            self.assertNotIn("pages: write", source, workflow)


if __name__ == "__main__":
    unittest.main()
