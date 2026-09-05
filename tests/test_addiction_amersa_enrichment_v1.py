import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

PUBLIC_ROUTES = {
    "/addiction/professional-education/": ROOT / "addiction/professional-education/index.html",
    "/addiction/professional-education/perinatal-care/": ROOT / "addiction/professional-education/perinatal-care/index.html",
    "/addiction/professional-education/ipv-sud-safety/": ROOT / "addiction/professional-education/ipv-sud-safety/index.html",
    "/addiction/professional-education/older-adults-oud/": ROOT / "addiction/professional-education/older-adults-oud/index.html",
    "/addiction/professional-education/moud-peer-recovery/": ROOT / "addiction/professional-education/moud-peer-recovery/index.html",
    "/addiction/sources/amersa/": ROOT / "addiction/sources/amersa/index.html",
}


def test_public_routes_exist_and_are_indexable():
    for route, path in PUBLIC_ROUTES.items():
        assert path.exists(), route
        html = path.read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in html
        assert 'name="robots" content="index,follow' in html
        assert f'https://healthrenewal.org{route}' in html
        assert "AMERSA" in html


def test_amersa_registry_has_provenance_and_expected_sources():
    registry = json.loads((ROOT / "data/addiction-evidence/source-registry-amersa-v1.json").read_text(encoding="utf-8"))
    assert registry["status"] == "verified-institutional-sources"
    assert registry["verified_on"] == "2026-09-05"
    assert registry["provenance"]["organization"].startswith("Association for Multidisciplinary")
    ids = {source["id"] for source in registry["sources"]}
    required = {
        "amersa-education-2026",
        "amersa-core-competencies-2018",
        "grayken-screening-assessment-treatment-2026",
        "amersa-perinatal-toolkit-2026",
        "amersa-ipv-sud-toolkit-2026",
        "amersa-older-adult-oud-toolkit-2026",
        "amersa-moud-peer-toolkit-2026",
        "amersa-advocacy-2026",
        "saj-journal-2026",
    }
    assert required <= ids
    assert len(registry["sources"]) >= 11
    rules = registry["rules"]
    assert rules["do_not_imply_endorsement"] is True
    assert rules["no_public_dosing_extraction"] is True
    assert rules["local_legal_review_required_for_policy_translation"] is True


def test_claim_map_is_traceable_and_safe():
    registry = json.loads((ROOT / "data/addiction-evidence/source-registry-amersa-v1.json").read_text(encoding="utf-8"))
    source_ids = {source["id"] for source in registry["sources"]}
    claim_map = json.loads((ROOT / "data/addiction-evidence/claim-source-map-amersa-v1.json").read_text(encoding="utf-8"))
    assert len(claim_map["claims"]) >= 9
    for claim in claim_map["claims"]:
        assert claim["source_ids"]
        assert set(claim["source_ids"]) <= source_ids
        assert claim["affected_routes"]
        assert claim["publication_status"] == "approved-for-general-education"
        assert claim["confidence"] in {"moderate", "moderate-high", "high"}
    assert claim_map["rules"]["screening_does_not_equal_diagnosis"] is True
    assert claim_map["rules"]["do_not_imply_amersa_endorsement"] is True


def test_manifest_matches_public_routes_and_safety_contract():
    manifest = json.loads((ROOT / "api/addiction-amersa-enrichment-v1.json").read_text(encoding="utf-8"))
    assert manifest["correspondence_verified"] is True
    assert manifest["directly_referred_resource_families"] == 4
    assert manifest["structured_source_count"] >= 11
    assert manifest["mapped_claim_count"] >= 9
    assert set(manifest["public_routes"]) == set(PUBLIC_ROUTES)
    safety = manifest["safety_contract"]
    assert all(safety.values())


def test_amersa_sitemap_has_exact_unique_public_routes():
    root = ET.parse(ROOT / "sitemap-addiction-amersa.xml").getroot()
    locs = [node.text for node in root.findall("s:url/s:loc", NS)]
    expected = {f"https://healthrenewal.org{route}" for route in PUBLIC_ROUTES}
    assert set(locs) == expected
    assert len(locs) == len(set(locs)) == 6


def test_sitemap_index_registers_amersa_sitemap():
    root = ET.parse(ROOT / "sitemap-index.xml").getroot()
    locs = [node.text for node in root.findall("s:sitemap/s:loc", NS)]
    assert "https://healthrenewal.org/sitemap-addiction-amersa.xml" in locs


def test_source_dossier_disclaims_endorsement_and_us_policy_transfer():
    html = (ROOT / "addiction/sources/amersa/index.html").read_text(encoding="utf-8")
    assert "لا يعني أن AMERSA راجعت روافد أو اعتمدتها" in html
    assert "لا ننقل نصوص قوانين أو تنظيمات أمريكية" in html
    assert "https://amersa.org/education/" in html
    assert "https://amersa.org/advocacy/" in html
    assert "https://journals.sagepub.com/home/saj" in html


def test_clinical_modules_preserve_scope_boundaries():
    perinatal = (ROOT / "addiction/professional-education/perinatal-care/index.html").read_text(encoding="utf-8")
    ipv = (ROOT / "addiction/professional-education/ipv-sud-safety/index.html").read_text(encoding="utf-8")
    older = (ROOT / "addiction/professional-education/older-adults-oud/index.html").read_text(encoding="utf-8")
    peer = (ROOT / "addiction/professional-education/moud-peer-recovery/index.html").read_text(encoding="utf-8")
    assert "لا تتضمن جرعات" in perinatal
    assert "لا تُجرِ فرزًا للعنف بوجود الشريك" in ipv
    assert "لا جرعات أو جداول خفض" in older
    assert "لا يصف دواء" in peer
    assert "لا يوصي بجرعة" in peer
