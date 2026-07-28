from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from seo_agent_fleet_v334_hardened import SiteContext, run_fleet  # noqa: E402

PROJECT_BASE = "https://example.com/project/"
ROOT_BASE = "https://example.com/"


def page(*, lang: str = "en", direction: str = "ltr", canonical: str, body: str, links: str = "") -> str:
    return f'''<!doctype html><html lang="{lang}" dir="{direction}"><head>
    <title>Evidence based mental health reference</title>
    <meta name="description" content="A reliable evidence based reference with clear guidance, citations, safety boundaries, and useful structured information for readers.">
    <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
    <link rel="canonical" href="{canonical}">
    <script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage","url":"{canonical}"}}</script>
    </head><body><main><h1>Evidence based mental health reference</h1><p>{body}</p>{links}</main></body></html>'''


class HardenedFleetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        body = " ".join(["Reliable clinical education content for readers and professionals"] * 25)
        (self.root / "section").mkdir()
        (self.root / "index.html").write_text(
            page(canonical=PROJECT_BASE, body=body, links='<a href="section/index.html">Section</a><a href="data.csv">Data</a>'),
            encoding="utf-8",
        )
        (self.root / "section" / "index.html").write_text(
            page(canonical=PROJECT_BASE + "section/", body=body, links='<a href="../">Home</a>'),
            encoding="utf-8",
        )
        (self.root / "data.csv").write_text("name,value\na,1\n", encoding="utf-8")
        (self.root / "sitemap.xml").write_text(
            f'''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>{PROJECT_BASE}</loc></url><url><loc>{PROJECT_BASE}section/</loc></url><url><loc>{PROJECT_BASE}data.csv</loc></url></urlset>''',
            encoding="utf-8",
        )
        (self.root / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\nSitemap: {PROJECT_BASE}sitemap.xml\n",
            encoding="utf-8",
        )
        (self.root / "llms.txt").write_text(
            f"# Reference\n\nCanonical site: {PROJECT_BASE}\n\nSitemap: {PROJECT_BASE}sitemap.xml\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_project_path_robots_is_reported_as_non_authoritative(self) -> None:
        report = run_fleet(SiteContext.load(self.root, PROJECT_BASE))
        matches = [f for f in report.findings if f.code == "ROBOTS_SUBPATH_NON_AUTHORITATIVE"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].severity, "info")
        self.assertEqual(matches[0].evidence, ROOT_BASE + "robots.txt")

    def test_existing_csv_and_explicit_index_route_are_not_broken(self) -> None:
        report = run_fleet(SiteContext.load(self.root, PROJECT_BASE))
        self.assertFalse(any(f.code == "BROKEN_INTERNAL_LINK" for f in report.findings), report.to_json())

    def test_existing_non_html_sitemap_resource_is_not_stale(self) -> None:
        report = run_fleet(SiteContext.load(self.root, PROJECT_BASE))
        self.assertFalse(any(f.code == "SITEMAP_STALE_URL" for f in report.findings), report.to_json())

    def test_small_arabic_navigation_does_not_relabel_english_page(self) -> None:
        source = self.root / "section" / "index.html"
        text = source.read_text(encoding="utf-8").replace(
            "</main>", "<nav>الرئيسية المكتبة تواصل معنا</nav></main>"
        )
        source.write_text(text, encoding="utf-8")
        report = run_fleet(SiteContext.load(self.root, PROJECT_BASE))
        self.assertFalse(any(f.code in {"LANG_CONTENT_MISMATCH", "RTL_MISSING"} and f.path == "section/index.html" for f in report.findings), report.to_json())


if __name__ == "__main__":
    unittest.main(verbosity=2)
