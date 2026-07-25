from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PUBLISHER = load_module(
    "public_api_discovery_v229",
    ROOT / "scripts" / "publish_public_api_v215.py",
)
AUDITOR = load_module(
    "orphan_audit_developers_v229",
    ROOT / "scripts" / "audit_orphan_pages_v197.py",
)


class DevelopersDiscoveryV229Tests(unittest.TestCase):
    def make_site(self, root: Path) -> tuple[Path, Path, Path]:
        site = root / "site"
        site.mkdir()
        (site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><body>'
            '<main><h1>الصفحة الرئيسية</h1></main>'
            '<footer><div class="footer-links"><a href="api/">API</a></div></footer>'
            '</body></html>',
            encoding="utf-8",
        )
        (site / "api" / "v1").mkdir(parents=True)
        (site / "api" / "index.html").write_text(
            '<a href="../../">الرئيسية</a>', encoding="utf-8"
        )
        manifest = root / "manifest.json"
        imported = root / "imported.json"
        manifest.write_text(
            json.dumps(
                {"schema_version": 215, "policy": "deny-by-default", "sources": []}
            ),
            encoding="utf-8",
        )
        imported.write_text(
            json.dumps(
                {
                    "schema_version": 215,
                    "status": "no-approved-sources",
                    "sources_processed": 0,
                    "courses": [],
                }
            ),
            encoding="utf-8",
        )
        return site, manifest, imported

    def test_publisher_exposes_developers_once_and_maps_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site, manifest, imported = self.make_site(Path(temp))
            first = PUBLISHER.publish(site, manifest, imported)
            second = PUBLISHER.publish(site, manifest, imported)
            homepage = (site / "index.html").read_text(encoding="utf-8")
            self.assertEqual(homepage.count(PUBLISHER.HOME_LINK_MARKER), 1)
            self.assertIn('href="developers/"', homepage)
            self.assertTrue((site / "developers" / "index.html").is_file())
            self.assertTrue((site / "sitemap-developers.xml").is_file())
            self.assertTrue(first["developers_homepage_link_added"])
            self.assertFalse(second["developers_homepage_link_added"])
            report = AUDITOR.audit(site, require_gateways=False)
            self.assertNotIn("developers/", report["critical_orphans"])
            self.assertNotIn("developers/", report["critical_unmapped"])

    def test_required_gateway_fails_when_developers_page_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site, manifest, imported = self.make_site(Path(temp))
            PUBLISHER.publish(site, manifest, imported)
            (site / "developers" / "index.html").unlink()
            report = AUDITOR.audit(site, require_gateways=True)
            self.assertEqual(report["status"], "failed")
            self.assertIn("developers/", report["missing_gateways"])

    def test_publisher_fails_without_footer_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            site, manifest, imported = self.make_site(Path(temp))
            (site / "index.html").write_text(
                '<!doctype html><html lang="ar"><body><main></main></body></html>',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                PUBLISHER.PublicApiError, "footer links container is missing"
            ):
                PUBLISHER.publish(site, manifest, imported)


if __name__ == "__main__":
    unittest.main()
