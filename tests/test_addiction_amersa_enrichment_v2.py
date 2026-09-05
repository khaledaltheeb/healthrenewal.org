import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITEMAP = ROOT / "sitemap-addiction-amersa.xml"
MANIFEST = ROOT / "api/addiction-amersa-enrichment-v2.json"
REGISTRIES = [
    ROOT / "data/addiction-evidence/source-registry-amersa-v1.json",
    ROOT / "data/addiction-evidence/source-registry-amersa-wave2-v1.json",
]
CLAIM_MAPS = [
    ROOT / "data/addiction-evidence/claim-source-map-amersa-v1.json",
    ROOT / "data/addiction-evidence/claim-source-map-amersa-wave2-v1.json",
]

WAVE2_ROUTES = [
    "/addiction/professional-education/climate-disaster-continuity/",
    "/addiction/professional-education/stigma-identity/",
    "/addiction/professional-education/telehealth-oud-access/",
    "/addiction/professional-education/primary-care-integration/",
]


def route_to_path(route: str) -> Path:
    return ROOT / route.strip("/") / "index.html"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifest_counts_match_structured_files():
    manifest = load_json(MANIFEST)
    source_count = sum(len(load_json(p)["sources"]) for p in REGISTRIES)
    claim_count = sum(len(load_json(p)["claims"]) for p in CLAIM_MAPS)
    assert source_count == 17
    assert claim_count == 15
    assert manifest["structured_source_count"] == source_count
    assert manifest["mapped_claim_count"] == claim_count
    assert manifest["public_route_count"] == len(manifest["public_routes"]) == 10
    assert len(set(manifest["public_routes"])) == 10


def test_all_claim_sources_exist_across_declared_registries():
    source_ids = set()
    for registry_path in REGISTRIES:
        registry = load_json(registry_path)
        source_ids.update(source["id"] for source in registry["sources"])
    assert len(source_ids) == 17
    for map_path in CLAIM_MAPS:
        claim_map = load_json(map_path)
        for claim in claim_map["claims"]:
            assert claim["source_ids"], claim["id"]
            assert set(claim["source_ids"]).issubset(source_ids), claim["id"]


def test_wave2_claims_mark_evidence_limits():
    claim_map = load_json(CLAIM_MAPS[1])
    for claim in claim_map["claims"]:
        if "qualitative" in claim["evidence_type"]:
            assert "qualitative-evidence" in claim["safety_flags"]
            assert claim["confidence"] == "moderate"
    rules = claim_map["rules"]
    assert rules["qualitative_studies_cannot_be_promoted_to_universal_guidelines"] is True
    assert rules["diagnostic_reclassification_prohibited_from_single_study"] is True
    assert rules["country_specific_regulation_requires_local_verification"] is True
    assert rules["no_dosing_claims"] is True
    assert rules["no_amersa_endorsement_claim"] is True


def test_sitemap_has_all_manifest_routes_once():
    manifest = load_json(MANIFEST)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(SITEMAP).getroot()
    urls = [node.text for node in root.findall("s:url/s:loc", ns)]
    assert len(urls) == 10
    assert len(urls) == len(set(urls))
    expected = {"https://healthrenewal.org" + route for route in manifest["public_routes"]}
    assert set(urls) == expected


def test_wave2_pages_are_indexable_canonical_and_source_grounded():
    for route in WAVE2_ROUTES:
        path = route_to_path(route)
        assert path.exists(), route
        html = path.read_text(encoding="utf-8")
        assert '<meta name="robots" content="index,follow' in html
        assert f'<link rel="canonical" href="https://healthrenewal.org{route}">' in html
        assert "AMERSA" in html or "Substance Use &amp; Addiction Journal" in html
        assert "2026" in html
        assert "آخر مراجعة: 5 سبتمبر 2026" in html


def test_wave2_pages_do_not_publish_dosing_instructions_or_endorsement_claims():
    forbidden_endorsement = [
        "معتمد من AMERSA",
        "اعتمدت AMERSA روافد",
        "endorsed by AMERSA",
        "AMERSA-approved Rawafid",
    ]
    dose_pattern = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|ml|mL)\b", re.IGNORECASE)
    for route in WAVE2_ROUTES:
        html = route_to_path(route).read_text(encoding="utf-8")
        assert not dose_pattern.search(html), route
        for phrase in forbidden_endorsement:
            assert phrase not in html, (route, phrase)


def test_local_regulation_guardrails_present_where_needed():
    climate = route_to_path(WAVE2_ROUTES[0]).read_text(encoding="utf-8")
    telehealth = route_to_path(WAVE2_ROUTES[2]).read_text(encoding="utf-8")
    assert "القانون" in climate and "محلي" in climate
    assert "الأنظمة" in telehealth and "المحلي" in telehealth
    assert "الولايات المتحدة" in telehealth


def test_amersa_sitemap_registered_in_sitemap_index():
    index_text = (ROOT / "sitemap-index.xml").read_text(encoding="utf-8")
    assert "https://healthrenewal.org/sitemap-addiction-amersa.xml" in index_text
