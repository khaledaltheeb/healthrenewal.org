from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from audit_publication_surface_v322 import (  # noqa: E402
    PublicationSurfaceError,
    REQUIRED_HOME_ROUTES,
    audit,
)
from publish_section_directory_v322 import (  # noqa: E402
    ADDITIONS,
    COMPATIBILITY_ALIAS_ROUTES,
    REQUIRED_DIRECTORY_ROUTES,
)


class PublicationSurfaceAuditTests(unittest.TestCase):
    def build_site(self, *, omit_home: str | None = None, omit_directory: str | None = None) -> Path:
        temp = Path(tempfile.mkdtemp())
        routes = set(REQUIRED_HOME_ROUTES)
        routes.discard("sections/")
        for route in routes:
            folder = temp / route
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "index.html").write_text(
                f'<!doctype html><html lang="ar"><head><meta name="robots" content="index,follow"></head><body><main><h1>{route}</h1></main></body></html>',
                encoding="utf-8",
            )

        home_routes = sorted(REQUIRED_HOME_ROUTES - ({omit_home} if omit_home else set()))
        links = "".join(f'<a href="{route}">{route}</a>' for route in home_routes)
        (temp / "index.html").write_text(
            f'<!doctype html><html><head></head><body data-publication-surface="v322"><main>{links}</main></body></html>',
            encoding="utf-8",
        )
        directory_routes = sorted(routes - ({omit_directory} if omit_directory else set()))
        directory_links = "".join(f'<a href="../{route}">{route}</a>' for route in directory_routes)
        (temp / "sections").mkdir(parents=True, exist_ok=True)
        (temp / "sections/index.html").write_text(
            f"<!doctype html><html><body><main>{directory_links}</main></body></html>", encoding="utf-8"
        )
        api = temp / "api/v1"
        api.mkdir(parents=True, exist_ok=True)
        (api / "section-directory.json").write_text(
            json.dumps({"items": [{"route": route} for route in directory_routes]}), encoding="utf-8"
        )
        return temp

    def test_complete_surface_passes(self) -> None:
        site = self.build_site()
        report = audit(site)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["specialists_partners_visible"])
        self.assertEqual(report["missing_critical_home"], [])
        self.assertEqual(report["missing_from_directory"], [])

    def test_hidden_critical_route_fails(self) -> None:
        site = self.build_site(omit_home="specialists-partners/")
        with self.assertRaises(PublicationSurfaceError):
            audit(site)
        report = json.loads((site / "api/publication-surface-v322.json").read_text(encoding="utf-8"))
        self.assertIn("specialists-partners/", report["missing_critical_home"])

    def test_public_route_missing_from_directory_fails(self) -> None:
        site = self.build_site(omit_directory="outside-the-box/")
        with self.assertRaises(PublicationSurfaceError):
            audit(site)
        report = json.loads((site / "api/publication-surface-v322.json").read_text(encoding="utf-8"))
        self.assertIn("outside-the-box/", report["missing_from_directory"])

    def test_broken_home_link_fails(self) -> None:
        site = self.build_site()
        path = site / "index.html"
        path.write_text(path.read_text(encoding="utf-8").replace("</main>", '<a href="missing-route/">مفقود</a></main>'), encoding="utf-8")
        with self.assertRaises(PublicationSurfaceError):
            audit(site)
        report = json.loads((site / "api/publication-surface-v322.json").read_text(encoding="utf-8"))
        self.assertIn("missing-route/", report["broken_home_links"])

    def test_retired_trust_routes_are_noindex_compatibility_aliases(self) -> None:
        expected = {
            "editorial-methodology/",
            "evaluate-mental-health-information/",
        }
        self.assertEqual(COMPATIBILITY_ALIAS_ROUTES, expected)
        self.assertTrue(expected.isdisjoint(ADDITIONS))
        self.assertTrue(expected.isdisjoint(REQUIRED_DIRECTORY_ROUTES))

        for route in expected:
            source = (ROOT / route / "index.html").read_text(encoding="utf-8")
            self.assertIn('content="noindex,follow"', source)
            self.assertIn('href="https://khaledaltheeb.github.io/pterminology-site/trust/', source)
            self.assertIn('/pterminology-site/trust/', source)


if __name__ == "__main__":
    unittest.main()
