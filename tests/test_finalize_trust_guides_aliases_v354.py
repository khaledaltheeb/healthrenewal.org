from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "finalize_trust_guides_links_v201.py"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
ALIASES = (
    "editorial-methodology",
    "evaluate-mental-health-information",
)
PUBLIC_ROUTE = "guides/source-citation-and-update-transparency"


class FinalizeTrustGuideAliasesV354Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="trust-alias-v354-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        for route in (*ALIASES, PUBLIC_ROUTE, "trust", "magazine", "api"):
            (site / route).mkdir(parents=True, exist_ok=True)
        for route in (*ALIASES, PUBLIC_ROUTE):
            (site / route / "index.html").write_text(
                '<!doctype html><html><head><meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="{BASE}/{route}/"></head>'
                '<body><main><a href="/pterminology-site/blog/">المجلة</a></main></body></html>',
                encoding="utf-8",
            )
        links = "".join(
            f'<li><a href="/pterminology-site/{route}/">{route}</a></li>'
            for route in (*ALIASES, PUBLIC_ROUTE)
        )
        for route in ("trust", "magazine"):
            (site / route / "index.html").write_text(
                f'<html><body><main><section class="trust-guides-v201"><ul>{links}</ul></section></main></body></html>',
                encoding="utf-8",
            )
        urls = "".join(
            f"<url><loc>{BASE}/{route}/</loc></url>" for route in (*ALIASES, PUBLIC_ROUTE)
        )
        sitemap = f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
        (site / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        (site / "sitemap-trust-guides.xml").write_text(sitemap, encoding="utf-8")
        report = {
            "version": 201,
            "status": "built-not-published",
            "pages": [
                {"key": "editorial", "path": "editorial-methodology/index.html"},
                {"key": "evaluate", "path": "evaluate-mental-health-information/index.html"},
                {"key": "citation", "path": PUBLIC_ROUTE + "/index.html"},
            ],
        }
        (site / "api/trust-guides-v201.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )
        return site

    def run_finalizer(self, site: Path) -> None:
        completed = subprocess.run(
            ["python3", str(SCRIPT), str(site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def sitemap_urls(self, path: Path) -> list[str]:
        root = ET.parse(path).getroot()
        return [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]

    def test_restores_aliases_and_prunes_public_discovery(self) -> None:
        site = self.make_site()
        self.run_finalizer(site)

        for route in ALIASES:
            text = (site / route / "index.html").read_text(encoding="utf-8")
            self.assertIn("data-legacy-path-alias=", text)
            self.assertIn('name="robots" content="noindex,follow"', text)
            self.assertIn('/pterminology-site/trust/', text)
            self.assertNotIn('/pterminology-site/blog/', text)

        citation = (site / PUBLIC_ROUTE / "index.html").read_text(encoding="utf-8")
        self.assertIn('/pterminology-site/magazine/', citation)
        self.assertNotIn('/pterminology-site/blog/', citation)

        for name in ("sitemap.xml", "sitemap-trust-guides.xml"):
            urls = self.sitemap_urls(site / name)
            self.assertEqual(urls, [f"{BASE}/{PUBLIC_ROUTE}/"])

        for route in ("trust", "magazine"):
            text = (site / route / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("editorial-methodology/", text)
            self.assertNotIn("evaluate-mental-health-information/", text)
            self.assertIn(PUBLIC_ROUTE + "/", text)

        report = json.loads((site / "api/trust-guides-v201.json").read_text(encoding="utf-8"))
        contract = report["publication_contract"]
        self.assertEqual(contract["public_page_count"], 1)
        self.assertEqual(contract["alias_page_count"], 2)
        self.assertFalse(contract["aliases_indexable"])
        states = {page["key"]: page["publication_status"] for page in report["pages"]}
        self.assertEqual(states["editorial"], "compatibility-alias")
        self.assertEqual(states["evaluate"], "compatibility-alias")
        self.assertEqual(states["citation"], "public")

    def test_is_idempotent(self) -> None:
        site = self.make_site()
        self.run_finalizer(site)
        first = {
            path: (site / path).read_bytes()
            for path in (
                "editorial-methodology/index.html",
                "evaluate-mental-health-information/index.html",
                "sitemap.xml",
                "sitemap-trust-guides.xml",
                "trust/index.html",
                "magazine/index.html",
            )
        }
        self.run_finalizer(site)
        second = {path: (site / path).read_bytes() for path in first}
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
