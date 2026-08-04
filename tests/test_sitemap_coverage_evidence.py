import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "api" / "audits" / "sitemap-coverage-2026-08-04.json"


def test_sitemap_coverage_evidence_is_machine_readable_and_fail_closed() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert payload["status"] == "observed-gap"
    assert payload["generatorReportVersion"] == 305
    assert payload["indexablePagesReported"] == 212
    assert payload["primarySitemapUrlsReported"] == 212
    assert payload["preservedCustomDomainSitemaps"] == 0
    assert payload["mergePolicy"] == "fail-closed-on-unexplained-coverage-gap"

    required = {
        "indexable_html_pages",
        "sitemap_urls",
        "missing_from_sitemaps",
        "orphan_sitemap_urls",
        "excluded_with_reason",
    }
    assert set(payload["requiredCompletionFields"]) == required
