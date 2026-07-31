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
BASE = "https://healthrenewal.org"
LEGACY_BASE = "https://khaledaltheeb.github.io/pterminology-site"
ALIASES = (
    "editorial-methodology",
    "evaluate-mental-health-information",
)
PUBLIC_ROUTE = "guides/source-citation-and-update-transparency"


class FinalizeTrustGuideAliasesV354Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="trust-alias-v355-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        for route in (*ALIASES, PUBLIC_ROUTE, "trust", "magazine", "api"):
            (site / route).mkdir(parents=True, exist_ok=True)
        for route in (*ALIASES, PUBLIC_ROUTE):
            (site / route / "index.html").write_text(
                '<!doctype html><html><head><meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="{LEGACY_BASE}/{route}/"></head>'
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
            f"<url><loc>{LEGACY_BASE}/{route}/</loc></url>"
            for route in (*ALIASES, PUBLIC_ROUTE)
        )
        sitemap = f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'
        (site / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        (site / "sitemap-trust-guides.xml").write_text(sitemap, encoding="utf-8")
        report = {
            "version": 201,
            "status": "built-not-published",
            "pages": [
                {
                    "key": "editorial",
                    "path": "editorial-methodology/index.html",
                    "url": f"{LEGACY_BASE}/editorial-methodology/",
                },
                {
                    "key": "evaluate",
                    "path": "evaluate-mental-health-information/index.html",
                    "url": f"{LEGACY_BASE}/evaluate-mental-health-information/",
                },
                {
                    "key": "citation",
                    "path": PUBLIC_ROUTE + "/index.html",
                    "url": f"{LEGACY_BASE}/{PUBLIC_ROUTE}/",
                },
            ],
        }
        (site / "api/trust-guides-v201.json").write_text(
            json.dumps(report, ensure_ascii=False), encoding="utf-8"
        )
        return site

    def run_finalizer(self, site: Path) -> dict:
        completed = subprocess.run(
            ["python3", str(SCRIPT), str(site)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def sitemap_urls(self, path: Path) -> list[str]:
        root = ET.parse(path).getroot()
        return [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]

    def test_restores_aliases_and_prunes_public_discovery(self) -> None:
        site = self.make_site()
        result = self.run_finalizer(site)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["version"], 355)
        self.assertEqual(result["canonical_origin"], BASE)

        for route in ALIASES:
            text = (site / route / "index.html").read_text(encoding="utf-8")
            self.assertEqual(text.count("data-legacy-path-alias="), 1)
            self.assertEqual(text.count('name="robots" content="noindex,follow"'), 1)
            self.assertEqual(text.count(f'rel="canonical" href="{BASE}/trust/"'), 1)
            self.assertEqual(text.count('http-equiv="refresh" content="0;url=/trust/"'), 1)
            self.assertIn('href="/trust/"', text)
            self.assertNotIn("/pterminology-site/", text)
            self.assertNotIn("khaledaltheeb.github.io", text)

        citation = (site / PUBLIC_ROUTE / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/magazine/"', citation)
        self.assertNotIn("/pterminology-site/", citation)
        self.assertNotIn("khaledaltheeb.github.io", citation)

        for name in ("sitemap.xml", "sitemap-trust-guides.xml"):
            urls = self.sitemap_urls(site / name)
            self.assertEqual(urls, [f"{BASE}/{PUBLIC_ROUTE}/"])
            self.assertFalse(any("khaledaltheeb.github.io" in url for url in urls))
            self.assertFalse(any("/pterminology-site/" in url for url in urls))

        for route in ("trust", "magazine"):
            text = (site / route / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("editorial-methodology/", text)
            self.assertNotIn("evaluate-mental-health-information/", text)
            self.assertIn(PUBLIC_ROUTE + "/", text)
            self.assertNotIn("/pterminology-site/", text)

        report = json.loads((site / "api/trust-guides-v201.json").read_text(encoding="utf-8"))
        contract = report["publication_contract"]
        self.assertEqual(contract["canonical_origin"], BASE)
        self.assertEqual(contract["public_page_count"], 1)
        self.assertEqual(contract["alias_page_count"], 2)
        self.assertFalse(contract["aliases_indexable"])
        self.assertEqual(contract["legacy_origins_remaining"], 0)
        states = {page["key"]: page["publication_status"] for page in report["pages"]}
        self.assertEqual(states["editorial"], "compatibility-alias")
        self.assertEqual(states["evaluate"], "compatibility-alias")
        self.assertEqual(states["citation"], "public")
        self.assertTrue(all(str(page["url"]).startswith(BASE) for page in report["pages"]))

    def test_is_idempotent(self) -> None:
        site = self.make_site()
        self.run_finalizer(site)
        tracked = {
            path: (site / path).read_bytes()
            for path in (
                "editorial-methodology/index.html",
                "evaluate-mental-health-information/index.html",
                PUBLIC_ROUTE + "/index.html",
                "sitemap.xml",
                "sitemap-trust-guides.xml",
                "trust/index.html",
                "magazine/index.html",
                "api/trust-guides-v201.json",
            )
        }
        self.run_finalizer(site)
        second = {path: (site / path).read_bytes() for path in tracked}
        self.assertEqual(tracked, second)


if __name__ == "__main__":
    unittest.main()
