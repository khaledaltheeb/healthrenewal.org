from __future__ import annotations

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_youth_sector_v353.py"

spec = importlib.util.spec_from_file_location("youth_sector_v353_routes", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class YouthTrustRoutesV354Tests(unittest.TestCase):
    def test_routes_point_to_published_trust_page(self) -> None:
        self.assertEqual(module.TRUST_ROUTES["methodology"], f"{module.BASE_PATH}/trust/")
        self.assertEqual(
            module.TRUST_ROUTES["information_evaluation"],
            f"{module.BASE_PATH}/trust/#evidence",
        )
        trust = (ROOT / "trust/index.html").read_text(encoding="utf-8")
        self.assertIn('id="evidence"', trust)

    def test_generated_pages_have_no_retired_routes(self) -> None:
        site = Path(tempfile.mkdtemp(prefix="youth-trust-v354-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        shutil.copy2(ROOT / "robots.txt", site / "robots.txt")

        report = module.publish(site)
        self.assertEqual(report["status"], "passed")
        pages = sorted((site / "sectors" / "youth").rglob("index.html"))
        self.assertEqual(len(pages), 21)

        combined = "\n".join(path.read_text(encoding="utf-8") for path in pages)
        self.assertNotIn("/editorial-methodology/", combined)
        self.assertNotIn("/evaluate-mental-health-information/", combined)
        self.assertIn(module.TRUST_ROUTES["methodology"], combined)
        self.assertIn(module.TRUST_ROUTES["information_evaluation"], combined)

    def test_publication_remains_idempotent(self) -> None:
        site = Path(tempfile.mkdtemp(prefix="youth-trust-idempotence-v354-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        shutil.copy2(ROOT / "robots.txt", site / "robots.txt")

        module.publish(site)
        before = {
            path.relative_to(site): path.read_bytes()
            for path in site.rglob("*")
            if path.is_file() and path.name != module.REPORT_NAME
        }
        module.publish(site)
        after = {
            path.relative_to(site): path.read_bytes()
            for path in site.rglob("*")
            if path.is_file() and path.name != module.REPORT_NAME
        }
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
