from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "sync_public_api_discovery_v219.py"
spec = importlib.util.spec_from_file_location("sync_public_api_discovery_v219", SCRIPT)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class PublicApiDiscoverySyncTests(unittest.TestCase):
    def test_synchronizes_endpoint_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site"
            api = site / "api" / "v1"
            report_dir = root / ".build" / "reports"
            api.mkdir(parents=True)
            report_dir.mkdir(parents=True)
            (api / "openapi.json").write_text(
                json.dumps(
                    {
                        "openapi": "3.1.0",
                        "paths": {
                            "/api/v1/health.json": {"get": {}},
                            "/api/v1/content-index.json": {"get": {}},
                            "/api/v1/taxonomy.json": {"get": {}},
                        },
                    }
                ),
                encoding="utf-8",
            )
            report_path = report_dir / "public-api-v215.json"
            report_path.write_text(
                json.dumps({"schema_version": 215, "endpoints": 1}),
                encoding="utf-8",
            )

            result = module.sync(root, site, "published")
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(result["endpoints"], 3)
            self.assertEqual(report["endpoints"], 3)
            self.assertTrue(report["content_discovery"])
            self.assertEqual(report["content_discovery_schema_version"], 219)
            self.assertEqual(report["content_discovery_stage"], "published")
            self.assertEqual(
                report["content_discovery_paths"],
                ["/api/v1/content-index.json", "/api/v1/taxonomy.json"],
            )

    def test_rejects_missing_report_and_missing_openapi_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site = root / "site"
            api = site / "api" / "v1"
            api.mkdir(parents=True)
            (api / "openapi.json").write_text(
                json.dumps({"openapi": "3.1.0", "paths": {}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(module.PublicApiDiscoverySyncError, "public-api-v215.json is missing"):
                module.sync(root, site, "prepared")

            report_dir = root / ".build" / "reports"
            report_dir.mkdir(parents=True)
            (report_dir / "public-api-v215.json").write_text(
                json.dumps({"schema_version": 215}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(module.PublicApiDiscoverySyncError, "OpenAPI paths are missing"):
                module.sync(root, site, "prepared")

    def test_rejects_unknown_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(module.PublicApiDiscoverySyncError, "unsupported stage"):
                module.sync(Path(tmp), Path(tmp), "unknown")


if __name__ == "__main__":
    unittest.main()
