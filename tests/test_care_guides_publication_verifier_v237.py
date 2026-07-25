from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify_care_guides_publication_v234 import sitemap_locations


class CareGuidePublicationVerifierV237Tests(unittest.TestCase):
    def write_sitemap(self, text: str) -> Path:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        path = Path(temporary_directory.name) / "sitemap-care-guides.xml"
        path.write_text(text, encoding="utf-8")
        return path

    def test_default_namespace_is_counted_structurally(self) -> None:
        path = self.write_sitemap(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/care-guides/</loc></url>'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/care-guides/example/</loc></url>'
            '</urlset>'
        )
        self.assertEqual(
            sitemap_locations(path),
            [
                "https://khaledaltheeb.github.io/pterminology-site/care-guides/",
                "https://khaledaltheeb.github.io/pterminology-site/care-guides/example/",
            ],
        )

    def test_prefixed_namespace_is_counted_structurally(self) -> None:
        path = self.write_sitemap(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<ns0:urlset xmlns:ns0="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<ns0:url><ns0:loc>https://khaledaltheeb.github.io/pterminology-site/care-guides/</ns0:loc></ns0:url>'
            '<ns0:url><ns0:loc>https://khaledaltheeb.github.io/pterminology-site/care-guides/example/</ns0:loc></ns0:url>'
            '</ns0:urlset>'
        )
        self.assertEqual(len(sitemap_locations(path)), 2)

    def test_duplicate_urls_are_rejected(self) -> None:
        path = self.write_sitemap(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/care-guides/</loc></url>'
            '<url><loc>https://khaledaltheeb.github.io/pterminology-site/care-guides/</loc></url>'
            '</urlset>'
        )
        with self.assertRaises(AssertionError):
            sitemap_locations(path)

    def test_empty_and_out_of_scope_sitemaps_are_rejected(self) -> None:
        empty = self.write_sitemap('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>')
        with self.assertRaises(AssertionError):
            sitemap_locations(empty)

        external = self.write_sitemap(
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            '<url><loc>https://example.com/care-guides/</loc></url>'
            '</urlset>'
        )
        with self.assertRaises(AssertionError):
            sitemap_locations(external)


if __name__ == "__main__":
    unittest.main()
