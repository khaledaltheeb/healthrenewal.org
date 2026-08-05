from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content" / "v337" / "special-needs-guides" / "cornelia-de-lange-syndrome.json"
PUBLISHER = ROOT / "scripts" / "publish_special_needs_cdls_v337.py"
GOVERNANCE = ROOT / "special-needs" / "conditions" / "cornelia-de-lange-syndrome" / "source-verification.json"


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


def test_publisher_contract_covers_discovery_schema_and_api() -> None:
    source = PUBLISHER.read_text(encoding="utf-8")
    for marker in (
        'site / "special-needs" / data["slug"] / "index.html"',
        'sitemap-special-needs.xml',
        'special-needs-cdls-v337.json',
        'shared.render_guide',
        'shared.link_hub',
        'canonical_url',
        'external_review_completed": False',
        'DOI: 10.1038/s41576-018-0031-0',
        'PMID: 29995837',
        'PMCID: PMC7136165',
    ):
        assert marker in source
    assert 'BASE = "https://healthrenewal.org"' in source
    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source


def test_no_competing_manual_public_route_is_created() -> None:
    assert not (ROOT / "special-needs" / "cornelia-de-lange-syndrome" / "index.html").exists()
    data = load()
    assert data["slug"].count("cornelia") == 1
