from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content" / "v337" / "special-needs-guides" / "cornelia-de-lange-syndrome.json"
PUBLISHER = ROOT / "scripts" / "publish_special_needs_cdls_v337.py"
GOVERNANCE = ROOT / "special-needs" / "conditions" / "cornelia-de-lange-syndrome" / "source-verification.json"
sys.path.insert(0, str(ROOT / "scripts"))
import publish_special_needs_cdls_v337 as publisher  # noqa: E402


def load() -> dict:
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_source_truth_is_deep_unique_and_honest() -> None:
    data = load()
    serialized = json.dumps(data, ensure_ascii=False)
    assert data["slug"] == "cornelia-de-lange-syndrome"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["rights_classification"] == "link-cite-and-original-summary-only"
    assert len(data["sections"]) >= 10
    assert all(len(section["paragraphs"]) >= 3 for section in data["sections"])
    assert len(data["practical_tips"]) >= 20
    assert len(data["avoid"]) >= 8
    assert len(re.findall(r"[\w\u0600-\u06ff]+", serialized)) >= 1400
    assert "معاقين" not in serialized
    assert "دواء أو جرعة" in data["professional_limits"]
    assert "لا يشخّص" in data["professional_limits"]


def test_sources_identifiers_rights_and_dates_are_preserved() -> None:
    data = load()
    sources = {source["id"]: source for source in data["sources"]}
    assert {"genereviews-2026", "international-consensus-2018", "orphanet-199", "nord-2023"} <= set(sources)
    consensus = sources["international-consensus-2018"]
    assert consensus["doi"] == "10.1038/s41576-018-0031-0"
    assert consensus["pmid"] == "29995837"
    assert consensus["pmcid"] == "PMC7136165"
    assert all(source["url"].startswith("https://") for source in sources.values())
    assert all(source["verified_at"] == "2026-08-05" for source in sources.values())
    governance = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
    assert governance["rights_and_attribution"]["classification"] == data["rights_classification"]
    assert governance["publication_requirements"]["canonical_path"] == "/special-needs/conditions/cornelia-de-lange-syndrome/"
    assert governance["status"]["publication_status"] == "production-source-wired"


def test_publisher_contract_uses_single_existing_canonical_route() -> None:
    source = PUBLISHER.read_text(encoding="utf-8")
    for marker in (
        'site / "special-needs" / "conditions" / data["slug"] / "index.html"',
        'sitemap-special-needs.xml',
        'special-needs-cdls-v337.json',
        'shared.render_guide',
        'canonical_url',
        'external_review_completed": False',
        'single_canonical_route": True',
        'DOI: 10.1038/s41576-018-0031-0',
        'PMID: 29995837',
        'PMCID: PMC7136165',
    ):
        assert marker in source
    assert 'BASE = "https://healthrenewal.org"' in source
    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source


def test_publisher_materializes_page_hub_sitemaps_and_api(tmp_path: Path) -> None:
    site = tmp_path / "site"
    (site / "special-needs").mkdir(parents=True)
    (site / "special-needs" / "index.html").write_text(
        '<!doctype html><html lang="ar" dir="rtl"><body><main><section><h2>مصادر الوحدة الحالية</h2></section></main></body></html>',
        encoding="utf-8",
    )
    (site / "sitemap-special-needs.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
        encoding="utf-8",
    )
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
        encoding="utf-8",
    )

    report = publisher.publish(site)
    canonical_path = site / "special-needs" / "conditions" / "cornelia-de-lange-syndrome" / "index.html"
    competing_path = site / "special-needs" / "cornelia-de-lange-syndrome" / "index.html"
    assert canonical_path.is_file()
    assert not competing_path.exists()
    page = canonical_path.read_text(encoding="utf-8")
    canonical = "https://healthrenewal.org/special-needs/conditions/cornelia-de-lange-syndrome/"
    assert f'<link rel="canonical" href="{canonical}">' in page
    assert "https://healthrenewal.org/special-needs/cornelia-de-lange-syndrome/" not in page
    assert "DOI: 10.1038/s41576-018-0031-0" in page
    assert canonical in (site / "sitemap-special-needs.xml").read_text(encoding="utf-8")
    assert "/special-needs/conditions/cornelia-de-lange-syndrome/" in (site / "special-needs" / "index.html").read_text(encoding="utf-8")
    api = json.loads((site / "api" / "special-needs-cdls-v337.json").read_text(encoding="utf-8"))
    assert api == report
    assert report["status"] == "passed"
    assert report["generated_page"] == "special-needs/conditions/cornelia-de-lange-syndrome/index.html"
    assert report["single_canonical_route"] is True
