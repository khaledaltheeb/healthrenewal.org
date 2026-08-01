from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts import build_html_sitemap_contract_v2 as contract


class HtmlSitemapContractV2Tests(unittest.TestCase):
    def test_retains_html_pages_and_excludes_json_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sitemap.xml"
            output = root / "html.xml"
            source.write_text(
                '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://healthrenewal.org/</loc></url>
  <url><loc>https://healthrenewal.org/guide/</loc></url>
  <url><loc>https://healthrenewal.org/article.html</loc></url>
  <url><loc>https://healthrenewal.org/api/registry.json</loc></url>
</urlset>''',
                encoding="utf-8",
            )
            old_root = contract.DEFAULT_ROOT
            try:
                contract.DEFAULT_ROOT = root
                report = contract.build(source, output, ("https://healthrenewal.org/",))
            finally:
                contract.DEFAULT_ROOT = old_root

            self.assertEqual(4, report["source_urls"])
            self.assertEqual(3, report["html_urls"])
            self.assertEqual(1, report["non_html_resources"])
            urls = [node.text for node in ET.parse(output).getroot().findall("{*}url/{*}loc")]
            self.assertEqual(
                [
                    "https://healthrenewal.org/",
                    "https://healthrenewal.org/article.html",
                    "https://healthrenewal.org/guide/",
                ],
                urls,
            )

    def test_rejects_ambiguous_extensionless_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sitemap.xml"
            source.write_text(
                '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://healthrenewal.org/ambiguous</loc></url>
</urlset>''',
                encoding="utf-8",
            )
            old_root = contract.DEFAULT_ROOT
            try:
                contract.DEFAULT_ROOT = root
                with self.assertRaises(SystemExit):
                    contract.build(source, root / "html.xml", ("https://healthrenewal.org/",))
            finally:
                contract.DEFAULT_ROOT = old_root


if __name__ == "__main__":
    unittest.main()
