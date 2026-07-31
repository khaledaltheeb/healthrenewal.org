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

    def test_every_public_search_contact_and_provider_page_is_indexable(self) -> None:
        builder = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")
        provider_sitemap = (ROOT / "sitemap-family-provider-platform.xml").read_text(encoding="utf-8")
        excluded_parts = builder.split("EXCLUDED_PARTS = {", 1)[1].split("}", 1)[0]
        excluded_files = builder.split("EXCLUDED_FILES = {", 1)[1].split("}", 1)[0]
        self.assertNotIn('"ai-search"', excluded_parts)
        self.assertNotIn('"contact.html"', excluded_files)
        self.assertNotIn('"professional-console.html"', excluded_files)
        self.assertIn("provider-assessment-demo/professional-console.html", provider_sitemap)
        self.assertIn('"ai-search": "البحث الذكي"', builder)
        self.assertIn("seen_page_hashes: set[tuple[str, str]]", builder)
        self.assertIn("dedupe_key = (url, content_hash)", builder)

    def test_dynamic_family_and_provider_condition_content_is_extracted(self) -> None:
        builder = (ROOT / "scripts/build_semantic_search_index.py").read_text(encoding="utf-8")
        remote = (ROOT / "scripts/build_remote_semantic_search_index.py").read_text(encoding="utf-8")
        family_html = (ROOT / "family-guide/conditions/adhd/index.html").read_text(encoding="utf-8")
        family_data = (ROOT / "family-guide/conditions/adhd/data.js").read_text(encoding="utf-8")
        provider_html = (ROOT / "provider-assessment-demo/conditions/adhd/index.html").read_text(encoding="utf-8")
        provider_data = (ROOT / "provider-assessment-demo/conditions/conditions-data-v1.js").read_text(encoding="utf-8")

        self.assertIn("family_payload_blocks", builder)
        self.assertIn("provider_payload_blocks", builder)
        self.assertIn("sidecar_data_blocks", builder)
        self.assertIn("structured_data_blocks", builder)
        self.assertIn("meta_description_blocks", builder)
        self.assertIn('basename == "data.js"', remote)
        self.assertIn('basename.startswith("conditions-data")', remote)
        self.assertIn("discover_index_data_assets", remote)

        self.assertIn('src="data.js', family_html)
        self.assertIn("برنامج تدريب والدين", family_data)
        self.assertIn("ما يجب تجنبه", builder)
        self.assertIn("conditions-data-v1.js", provider_html)
        self.assertIn("Conners 4", provider_data)
        self.assertIn("اختبار الأداء المستمر لا يشخّص منفردًا", provider_data)

    def test_remote_builder_writes_a_fail_closed_coverage_report(self) -> None:
        remote = (ROOT / "scripts/build_remote_semantic_search_index.py").read_text(encoding="utf-8")
        self.assertIn("--minimum-indexed-ratio", remote)
        self.assertIn('output / "coverage.json"', remote)
        self.assertIn('"indexCoverageRatio"', remote)
        self.assertIn('"dataAssetCount"', remote)
        self.assertIn('"failedDataAssetCount"', remote)
        self.assertIn('if not coverage["passed"]', remote)
        self.assertIn("indexed_source_paths", remote)
        self.assertIn("and not data_asset_failures", remote)

    def test_workflow_requires_complete_nonstarving_production_coverage(self) -> None:
        workflow = (ROOT / ".github/workflows/semantic-search-index.yml").read_text(encoding="utf-8")
        self.assertIn("'**/*.html'", workflow)
        self.assertIn("assets/platform/platform-core.js", workflow)
        self.assertIn("tests/test_e5_full_site_home_integration_v4.py", workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", workflow)
        self.assertIn("--minimum-success-ratio 1.0", workflow)
        self.assertIn("--minimum-indexed-ratio 1.0", workflow)
        self.assertIn("coverage['passed'] is True", workflow)
        self.assertIn("coverage['failedDataAssetCount'] == 0", workflow)
        self.assertIn("coverage['dataAssetCount'] == coverage['downloadedDataAssetCount']", workflow)


if __name__ == "__main__":
    unittest.main()