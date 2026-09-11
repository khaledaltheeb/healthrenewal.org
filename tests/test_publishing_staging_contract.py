import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "publishing"
STAGING_BUILDER = ROOT / "scripts" / "build_publishing_staging.py"
SITEMAP_SCRIPT = ROOT / "scripts" / "publish_complete_sitemap_v360.py"
THOTH_STAGE = BASE / "thoth-staging.json"
TRANSLATION_QUEUE = BASE / "translation-queue.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublishingStagingContractTest(unittest.TestCase):
    def test_generated_staging_is_current(self):
        subprocess.run(
            [sys.executable, str(STAGING_BUILDER), "--check"],
            cwd=ROOT,
            check=True,
        )

    def test_thoth_stage_is_internal_readiness_only(self):
        data = load(THOTH_STAGE)
        self.assertEqual(data["publisher"], "Health Renewal / Rawafid")
        self.assertEqual(data["purpose"], "internal-readiness-staging")
        self.assertEqual(data["external_payload_status"], "not-a-thoth-api-payload")
        self.assertEqual(data["literary_policy"], "hold-for-thoth-confirmation")
        self.assertEqual(data["candidate_count"], len(data["candidates"]))
        for item in data["candidates"]:
            self.assertNotEqual(item["record_type"], "discovery-only")
            self.assertNotIn(item["work_type"], {"literary-fiction", "literary-nonfiction"})
            self.assertTrue(item["local_canonical"].startswith("https://healthrenewal.org/open-books/"))

    def test_translation_queue_has_explicit_readiness_state(self):
        data = load(TRANSLATION_QUEUE)
        self.assertEqual(data["publisher"], "Health Renewal / Rawafid")
        self.assertEqual(data["purpose"], "authorized-arabic-translation-workflow")
        self.assertEqual(data["record_count"], len(data["records"]))
        for item in data["records"]:
            self.assertIn("ready_for_publication", item)
            self.assertIsInstance(item["blocked_reasons"], list)
            self.assertEqual(item["target"]["language"], "ar")

    def test_publishing_hubs_are_sitemap_discoverable(self):
        module = load_module(SITEMAP_SCRIPT, "rawafid_complete_sitemap")
        urls, discovery = module.discover(ROOT)
        self.assertIn("https://healthrenewal.org/publishing/", urls)
        self.assertIn("https://healthrenewal.org/open-books/", urls)
        self.assertGreater(discovery["html_files_discovered"], 0)


if __name__ == "__main__":
    unittest.main()
