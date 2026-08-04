import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "audits" / "sitemap-coverage-2026-08-04.md"


def test_sitemap_coverage_audit_records_reproducible_counts_and_required_contract() -> None:
    source = REPORT.read_text(encoding="utf-8")

    for required_measurement in (
        "`indexable_pages`: 212",
        "`primary_sitemap_urls`: 212",
        "`preserved_custom_domain_sitemaps`: 0",
    ):
        assert required_measurement in source

    for required_field in (
        "`indexable_html_pages`",
        "`sitemap_urls`",
        "`missing_from_sitemaps`",
        "`orphan_sitemap_urls`",
        "`excluded_with_reason`",
    ):
        assert required_field in source

    assert "الفشل المغلق" in source
    assert "Artifact الإنتاجي" in source
