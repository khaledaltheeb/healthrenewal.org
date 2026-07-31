from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import publish_section_directory_v322 as directory


class SectionDirectoryCompatibilityAliasesV322Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.site = Path(tempfile.mkdtemp(prefix="section-alias-v322-"))
        self.addCleanup(lambda: shutil.rmtree(self.site, ignore_errors=True))
        for route in directory.COMPATIBILITY_ALIAS_ROUTES:
            path = self.site / route / "index.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "<!doctype html><html><head>"
                f'<title>{route}</title>'
                '<meta name="robots" content="index,follow">'
                f'<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/{route}">'
                f'<meta property="og:url" content="https://khaledaltheeb.github.io/pterminology-site/{route}">'
                "</head><body><main><h1>Compatibility page</h1></main></body></html>",
                encoding="utf-8",
            )
        self._write_urlset(
            "sitemap.xml",
            [
                "https://healthrenewal.org/trust/",
                "https://healthrenewal.org/editorial-methodology/",
                "https://khaledaltheeb.github.io/pterminology-site/evaluate-mental-health-information/",
            ],
        )
        self._write_urlset(
            "sitemap-trust-guides.xml",
            [
                "https://healthrenewal.org/editorial-methodology/",
                "https://healthrenewal.org/evaluate-mental-health-information/",
                "https://healthrenewal.org/guides/source-citation-and-update-transparency/",
            ],
        )
        index = ET.Element("sitemapindex", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        node = ET.SubElement(index, "sitemap")
        ET.SubElement(node, "loc").text = "https://healthrenewal.org/sitemap-trust-guides.xml"
        ET.ElementTree(index).write(self.site / "sitemap-index.xml", encoding="utf-8", xml_declaration=True)

    def _write_urlset(self, filename: str, urls: list[str]) -> None:
        root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for url in urls:
            node = ET.SubElement(root, "url")
            ET.SubElement(node, "loc").text = url
        ET.ElementTree(root).write(self.site / filename, encoding="utf-8", xml_declaration=True)

    def _digest(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _locations(self, path: Path) -> list[str]:
        tree = ET.parse(path)
        return [(node.text or "").strip() for node in tree.findall(".//{*}url/{*}loc") if node.text]

    def test_aliases_are_noindex_canonicalized_and_pruned_from_urlsets(self) -> None:
        report = directory.normalize_compatibility_aliases(self.site)
        self.assertEqual(report["existing"], sorted(directory.COMPATIBILITY_ALIAS_ROUTES))
        self.assertEqual(report["canonical"], "https://healthrenewal.org/trust/")
        self.assertTrue(report["noindex_follow"])
        self.assertEqual(report["sitemap_files_changed"], 2)
        self.assertEqual(report["sitemap_urls_removed"], 4)

        for route in directory.COMPATIBILITY_ALIAS_ROUTES:
            source = (self.site / route / "index.html").read_text(encoding="utf-8")
            self.assertEqual(source.count(directory.ALIAS_MARKER), 1)
            self.assertEqual(source.count('name="robots" content="noindex,follow"'), 1)
            self.assertEqual(source.count('rel="canonical" href="https://healthrenewal.org/trust/"'), 1)
            self.assertEqual(source.count('property="og:url" content="https://healthrenewal.org/trust/"'), 1)
            self.assertNotIn('name="robots" content="index,follow"', source)

        for sitemap in (self.site / "sitemap.xml", self.site / "sitemap-trust-guides.xml"):
            locations = self._locations(sitemap)
            self.assertFalse(any(directory._is_alias_url(url) for url in locations), locations)
        self.assertEqual(
            self._locations(self.site / "sitemap.xml"),
            ["https://healthrenewal.org/trust/"],
        )
        self.assertEqual(
            self._locations(self.site / "sitemap-trust-guides.xml"),
            ["https://healthrenewal.org/guides/source-citation-and-update-transparency/"],
        )

    def test_normalization_is_idempotent(self) -> None:
        directory.normalize_compatibility_aliases(self.site)
        tracked = [
            *(self.site / route / "index.html" for route in sorted(directory.COMPATIBILITY_ALIAS_ROUTES)),
            self.site / "sitemap.xml",
            self.site / "sitemap-trust-guides.xml",
            self.site / "sitemap-index.xml",
        ]
        before = [self._digest(path) for path in tracked]
        second = directory.normalize_compatibility_aliases(self.site)
        after = [self._digest(path) for path in tracked]
        self.assertEqual(before, after)
        self.assertEqual(second["sitemap_files_changed"], 0)
        self.assertEqual(second["sitemap_urls_removed"], 0)

    def test_missing_alias_pages_are_allowed(self) -> None:
        shutil.rmtree(self.site / "editorial-methodology")
        report = directory.normalize_compatibility_aliases(self.site)
        self.assertEqual(report["existing"], ["evaluate-mental-health-information/"])
        self.assertEqual(report["sitemap_urls_removed"], 4)


if __name__ == "__main__":
    unittest.main()
