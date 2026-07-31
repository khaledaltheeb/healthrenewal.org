from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish_magazine_v201.py"
SPEC = importlib.util.spec_from_file_location("publish_magazine_v355", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MagazineCustomDomainV355Tests(unittest.TestCase):
    def make_site(self, root: Path) -> Path:
        site = root / "_site"
        site.mkdir()
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
            encoding="utf-8",
        )
        return site

    def test_normalizes_legacy_and_custom_article_canonicals(self) -> None:
        filename = "example-2026.html"
        for origin in (MODULE.LEGACY_BASE, MODULE.BASE):
            source = (
                '<html><head><link rel="canonical" href="'
                + origin
                + "/magazine/"
                + filename
                + '"></head><body></body></html>'
            )
            normalized, _ = MODULE.normalize_article_canonical(source, filename)
            expected = f'<link rel="canonical" href="{MODULE.URL}{filename}">'
            self.assertEqual(normalized.count('rel="canonical"'), 1)
            self.assertIn(expected, normalized)
            self.assertNotIn(MODULE.LEGACY_BASE, normalized)

    def test_published_magazine_uses_only_custom_domain(self) -> None:
        self.assertEqual(MODULE.BASE, "https://healthrenewal.org")
        self.assertEqual(MODULE.URL, "https://healthrenewal.org/magazine/")
        pages = MODULE.article_files()
        with tempfile.TemporaryDirectory() as directory:
            site = self.make_site(Path(directory))
            report = MODULE.publish(site)
            self.assertEqual(
                report["canonical_contract"],
                "single-healthrenewal-custom-domain-canonical-per-published-page",
            )
            for page in pages:
                text = (site / "magazine" / page.name).read_text(encoding="utf-8")
                expected = f'<link rel="canonical" href="{MODULE.URL}{page.name}">'
                self.assertEqual(text.count('rel="canonical"'), 1, page.name)
                self.assertIn(expected, text, page.name)
                self.assertNotIn(MODULE.LEGACY_BASE, text, page.name)

            index = (site / "magazine/index.html").read_text(encoding="utf-8")
            feed = (site / "magazine/feed.xml").read_text(encoding="utf-8")
            sitemap_urls = [
                (node.text or "").strip()
                for node in ET.parse(site / "sitemap-magazine.xml").getroot().findall("{*}url/{*}loc")
            ]
            self.assertNotIn(MODULE.LEGACY_BASE, index + feed + "\n".join(sitemap_urls))
            self.assertTrue(all(url.startswith(MODULE.URL) for url in sitemap_urls))

    def test_rejects_missing_or_duplicate_canonical(self) -> None:
        with self.assertRaises(SystemExit):
            MODULE.normalize_article_canonical("<html></html>", "missing-2026.html")
        duplicate = (
            '<link rel="canonical" href="https://example.com/a">'
            '<link rel="canonical" href="https://example.com/b">'
        )
        with self.assertRaises(SystemExit):
            MODULE.normalize_article_canonical(duplicate, "duplicate-2026.html")


if __name__ == "__main__":
    unittest.main()
