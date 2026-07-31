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
    def new_site(self, prefix: str) -> Path:
        site = Path(tempfile.mkdtemp(prefix=prefix))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        shutil.copy2(ROOT / "robots.txt", site / "robots.txt")
        return site

    def test_routes_point_to_published_trust_page(self) -> None:
        self.assertEqual(module.TRUST_ROUTES["methodology"], f"{module.BASE_PATH}/trust/")
        self.assertEqual(
            module.TRUST_ROUTES["information_evaluation"],
            f"{module.BASE_PATH}/trust/#evidence",
        )
        trust = (ROOT / "trust/index.html").read_text(encoding="utf-8")
        self.assertIn('id="evidence"', trust)

    def test_generated_youth_pages_use_unified_trust_routes(self) -> None:
        site = self.new_site("youth-trust-v354-")
        report = module.publish(site)
        self.assertEqual(report["status"], "passed")
        pages = sorted((site / "sectors" / "youth").rglob("index.html"))
        self.assertEqual(len(pages), 21)

        combined = "\n".join(path.read_text(encoding="utf-8") for path in pages)
        self.assertNotIn("/editorial-methodology/", combined)
        self.assertNotIn("/evaluate-mental-health-information/", combined)
        self.assertIn(module.TRUST_ROUTES["methodology"], combined)
        self.assertIn(module.TRUST_ROUTES["information_evaluation"], combined)

    def test_production_output_contains_compatibility_aliases(self) -> None:
        site = self.new_site("youth-aliases-v354-")
        module.publish(site)
        aliases = {
            "editorial-methodology": module.TRUST_ROUTES["methodology"],
            "evaluate-mental-health-information": module.TRUST_ROUTES["information_evaluation"],
        }
        for slug, target in aliases.items():
            path = site / slug / "index.html"
            self.assertTrue(path.is_file(), slug)
            source = path.read_text(encoding="utf-8")
            self.assertIn('content="0;url=', source)
            self.assertIn(target, source)
            self.assertIn('name="robots" content="noindex,follow"', source)
            self.assertEqual(source.count("<h1"), 1)

    def test_publication_remains_idempotent(self) -> None:
        site = self.new_site("youth-trust-idempotence-v354-")
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
