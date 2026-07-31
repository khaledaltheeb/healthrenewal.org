from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from normalize_social_previews_v334 import (  # noqa: E402
    ASSET_PATH,
    is_svg_url,
    normalize_tree,
    rewrite_meta_tag,
)

BASE = "https://healthrenewal.org/"


class SocialPreviewNormalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_svg_detection_ignores_query_and_case(self) -> None:
        self.assertTrue(is_svg_url("https://example.com/card.SVG?v=2"))
        self.assertFalse(is_svg_url("https://example.com/card.png?v=2"))

    def test_rewrites_only_social_meta_svg(self) -> None:
        replacement = BASE + ASSET_PATH
        tag = '<meta property="og:image" content="https://example.com/card.svg">'
        updated, changed = rewrite_meta_tag(tag, replacement)
        self.assertTrue(changed)
        self.assertIn(replacement, updated)
        ordinary = '<meta name="description" content="card.svg">'
        self.assertEqual(rewrite_meta_tag(ordinary, replacement), (ordinary, False))

    def test_tree_normalization_writes_1200x630_png_and_preserves_content_images(self) -> None:
        page = self.root / "index.html"
        page.write_text(
            '''<!doctype html><html><head>
            <meta property="og:image" content="https://example.com/a.svg">
            <meta name="twitter:image" content="/b.SVG?x=1">
            <meta property="og:image:alt" content="منصة الصحة النفسية">
            </head><body><img src="/illustration.svg" alt="رسم"></body></html>''',
            encoding="utf-8",
        )
        report = normalize_tree(self.root, BASE)
        self.assertEqual(report.html_files_scanned, 1)
        self.assertEqual(report.html_files_changed, 1)
        self.assertEqual(report.meta_tags_changed, 2)
        output = page.read_text(encoding="utf-8")
        expected = BASE + ASSET_PATH
        self.assertEqual(output.count(expected), 2)
        self.assertIn('src="/illustration.svg"', output)
        png = (self.root / ASSET_PATH).read_bytes()
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", png[16:24])
        self.assertEqual((width, height), (1200, 630))
        self.assertTrue((self.root / "api" / "social-preview-normalization-v334.json").exists())

    def test_second_run_is_idempotent(self) -> None:
        page = self.root / "index.html"
        page.write_text('<meta property="og:image" content="/card.svg">', encoding="utf-8")
        first = normalize_tree(self.root, BASE)
        second = normalize_tree(self.root, BASE)
        self.assertEqual(first.meta_tags_changed, 1)
        self.assertEqual(second.meta_tags_changed, 0)
        self.assertEqual(second.html_files_changed, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
