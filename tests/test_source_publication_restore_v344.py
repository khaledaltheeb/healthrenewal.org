from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import restore_source_published_pages_v343 as restore  # noqa: E402


class SourcePublicationRestoreV344Tests(unittest.TestCase):
    def test_existing_section_is_not_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            site = root / "site"
            (source / "section/missing").mkdir(parents=True)
            (source / "section/missing/index.html").write_text("<html>restored</html>", encoding="utf-8")
            (source / "section/missing/data.js").write_text("const restored=true", encoding="utf-8")
            (site / "section").mkdir(parents=True)
            existing = site / "section/existing-production.txt"
            existing.write_text("keep", encoding="utf-8")

            copied = restore.incremental_copy_public_surface(source, site, "section/missing/")

            self.assertEqual(copied, ["section/missing/"])
            self.assertEqual(existing.read_text(encoding="utf-8"), "keep")
            self.assertTrue((site / "section/missing/index.html").is_file())
            self.assertTrue((site / "section/missing/data.js").is_file())

    def test_absent_section_copies_assets_but_only_declared_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            site = root / "site"
            (source / "family-guide/draft").mkdir(parents=True)
            (source / "family-guide/index.html").write_text("<html>public</html>", encoding="utf-8")
            (source / "family-guide/draft/index.html").write_text(
                '<html><meta name="robots" content="noindex">draft</html>', encoding="utf-8"
            )
            (source / "family-guide/family-guide.css").write_text("body{}", encoding="utf-8")
            (source / "family-guide/draft/data.js").write_text("const draftAsset=true", encoding="utf-8")

            copied = restore.incremental_copy_public_surface(source, site, "family-guide/")

            self.assertEqual(copied, ["family-guide/"])
            self.assertTrue((site / "family-guide/index.html").is_file())
            self.assertTrue((site / "family-guide/family-guide.css").is_file())
            self.assertTrue((site / "family-guide/draft/data.js").is_file())
            self.assertFalse((site / "family-guide/draft/index.html").exists())

    def test_noindex_is_detected_in_any_attribute_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first.html"
            second = root / "second.html"
            public = root / "public.html"
            first.write_text('<meta name="robots" content="noindex,follow">', encoding="utf-8")
            second.write_text('<meta content="max-snippet:-1,noindex" name="robots">', encoding="utf-8")
            public.write_text('<meta content="index,follow" name="robots">', encoding="utf-8")

            self.assertEqual(restore.hardened_is_blocked_html(first), (True, "noindex"))
            self.assertEqual(restore.hardened_is_blocked_html(second), (True, "noindex"))
            self.assertEqual(restore.hardened_is_blocked_html(public), (False, None))


if __name__ == "__main__":
    unittest.main()
