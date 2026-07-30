from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.publish_academic_library_v326 import publish


class AcademicLibraryLegacyDiscoveryV353Tests(unittest.TestCase):
    def test_links_existing_numbered_entries_from_each_section_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            samples = {
                "branches": ("branches-01", "علم النفس الإكلينيكي"),
                "research": ("research-01", "الفرضية"),
                "therapies": ("therapies-01", "العلاج المعرفي السلوكي"),
            }
            for section, (slug, title) in samples.items():
                page = site / "library" / section / slug / "index.html"
                page.parent.mkdir(parents=True)
                page.write_text(
                    f'<!doctype html><html lang="ar"><body><main><h1>{title}</h1></main></body></html>',
                    encoding="utf-8",
                )

            report = publish(site)

            self.assertEqual(report["legacy_entries_linked"], 3)
            self.assertEqual(
                report["legacy_entries_by_section"],
                {"branches": 1, "therapies": 1, "research": 1},
            )
            for section, (slug, title) in samples.items():
                source = (site / "library" / section / "index.html").read_text(
                    encoding="utf-8"
                )
                self.assertIn("data-legacy-library-directory-v353", source)
                self.assertIn(f"/library/{section}/{slug}/", source)
                self.assertIn(title, source)


if __name__ == "__main__":
    unittest.main()
