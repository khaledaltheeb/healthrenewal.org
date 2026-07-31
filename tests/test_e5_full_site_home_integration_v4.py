#!/usr/bin/env python3
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FullSiteE5HomeIntegrationTests(unittest.TestCase):
    def test_global_shell_routes_home_search_to_e5(self) -> None:
        shell = (ROOT / "assets/platform/platform-core.js").read_text(encoding="utf-8")
        self.assertIn("['البحث الذكي', 'ai-search/']", shell)
        self.assertIn("action: url('ai-search/')", shell)
        self.assertIn("multilingual-e5-small", shell)
        self.assertIn("text: 'ابحث بذكاء'", shell)

    def test_public_search_and_contact_pages_are_indexable(self) -> None:
        builder = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")
        excluded_parts = builder.split("EXCLUDED_PARTS = {", 1)[1].split("}", 1)[0]
        excluded_files = builder.split("EXCLUDED_FILES = {", 1)[1].split("}", 1)[0]
        self.assertNotIn('"ai-search"', excluded_parts)
        self.assertNotIn('"contact.html"', excluded_files)
        self.assertIn('"ai-search": "البحث الذكي"', builder)
        self.assertIn("seen_page_hashes: set[tuple[str, str]]", builder)
        self.assertIn("dedupe_key = (url, content_hash)", builder)

    def test_remote_builder_writes_a_fail_closed_coverage_report(self) -> None:
        remote = (ROOT / "scripts/build_remote_semantic_search_index.py").read_text(encoding="utf-8")
        self.assertIn("--minimum-indexed-ratio", remote)
        self.assertIn('output / "coverage.json"', remote)
        self.assertIn('"indexCoverageRatio"', remote)
        self.assertIn('if not coverage["passed"]', remote)
        self.assertIn("indexed_source_paths", remote)

    def test_workflow_requires_complete_production_coverage(self) -> None:
        workflow = (ROOT / ".github/workflows/semantic-search-index.yml").read_text(encoding="utf-8")
        self.assertIn("'**/*.html'", workflow)
        self.assertIn("assets/platform/platform-core.js", workflow)
        self.assertIn("tests/test_e5_full_site_home_integration_v4.py", workflow)
        self.assertIn("--minimum-success-ratio 1.0", workflow)
        self.assertIn("--minimum-indexed-ratio 1.0", workflow)
        self.assertIn("coverage['passed'] is True", workflow)


if __name__ == "__main__":
    unittest.main()