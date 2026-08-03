from __future__ import annotations

from datetime import date
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
KEBAB_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_program_is_truthfully_marked_as_foundation():
    index = load_json("api/v1/addiction-center.json")
    assert index["program_status"] in {
        "foundation-draft",
        "expanded-foundation-v2",
    }
    assert "لا يمثل اكتمال" in index["publication_claim"]
    assert "اعتماد سريري خارجي" in index["publication_claim"]
    assert index["protocol_total"] == 100
    assert index["reference_count"] >= 50
    assert index["structured_reference_count"] >= 12
    assert index["mapped_claim_count"] >= 12
    assert index["claim_source_map_status"] in {
        "foundation-partial",
        "expanded-partial-v2",
    }


def test_governance_contracts_are_linked_and_exist():
    index = load_json("api/v1/addiction-center.json")
    for field in (
        "governance_document",
        "safety_contract",
        "information_architecture",
        "structured_source_registry",
        "claim_source_map",
    ):
        assert (ROOT / index[field]).is_file(), field

    for optional_field in (
        "supplemental_source_registry",
        "expansion_report",
    ):
        if optional_field in index:
            assert (ROOT / index[optional_field]).is_file(), optional_field

    next_wave = index["required_next_wave"]
    if "independent_condition_pages" in next_wave:
        assert next_wave["independent_condition_pages"] == 10
        assert next_wave["family_guides"] >= 12
        assert next_wave["practical_tools"] >= 12
        assert next_wave["special_population_guides"] >= 12
        assert next_wave["claim_source_map_required"] is True
    else:
        assert index.get("condition_layer_status") == "complete-v1"
        assert next_wave["additional_family_guides"] >= 6
        assert next_wave["additional_practical_tools"] >= 6
        assert next_wave["additional_special_population_guides"] >= 6
        assert next_wave["additional_substance_and_behavior_guides"] >= 8
        assert next_wave["regional_legal_localization_required"] is True
    assert next_wave["external_clinical_review_required_for_accreditation_claim"] is True


def test_structured_source_registry_is_reviewable():
    registry = load_json("data/addiction-evidence/source-registry.json")
    sources = registry["sources"]
    assert len(sources) >= 12
    identifiers = [item["id"] for item in sources]
    assert len(identifiers) == len(set(identifiers))
    assert all(KEBAB_ID.fullmatch(identifier) for identifier in identifiers)

    required_fields = set(registry["required_fields"])
    verified_on = date.fromisoformat(registry["verified_on"])
    authorities = set()
    for source in sources:
        assert required_fields.issubset(source), source.get("id")
        assert source["url"].startswith("https://")
        assert date.fromisoformat(source["verified_on"]) <= verified_on
        assert date.fromisoformat(source["next_review_on"]) > verified_on
        assert source["topics"]
        assert source["name"] == source["title"]
        assert source["organization"] == source["authority"]
        authorities.add(source["authority"])

    assert {
        "World Health Organization",
        "World Health Organization and United Nations Office on Drugs and Crime",
        "Substance Abuse and Mental Health Services Administration",
        "American Society of Addiction Medicine",
        "National Institute for Health and Care Excellence",
        "U.S. Department of Veterans Affairs and Department of Defense",
        "Centers for Disease Control and Prevention",
    }.issubset(authorities)


def test_claim_map_resolves_every_source_id_and_declares_gaps():
    registry = load_json("data/addiction-evidence/source-registry.json")
    source_ids = {source["id"] for source in registry["sources"]}
    claim_map = load_json("data/addiction-evidence/claim-source-map.json")
    claims = claim_map["claims"]
    assert len(claims) >= 12

    claim_ids = [claim["id"] for claim in claims]
    assert len(claim_ids) == len(set(claim_ids))
    assert all(KEBAB_ID.fullmatch(identifier) for identifier in claim_ids)

    for claim in claims:
        assert claim["statement_ar"].strip()
        assert claim["source_ids"]
        assert set(claim["source_ids"]).issubset(source_ids), claim["id"]
        assert claim["publication_status"] in {
            "draft",
            "approved-for-general-education",
            "external-clinical-review-required",
        }
        assert claim["safety_flags"]

    gap_domains = {gap["domain"] for gap in claim_map["coverage_gaps"]}
    assert {"cannabis-use-disorder", "gaming-disorder", "inhalant-use-disorder"}.issubset(gap_domains)


def test_safety_contract_contains_non_negotiable_guardrails():
    text = (ROOT / "docs/addiction-safety-contract.md").read_text(encoding="utf-8")
    for required in (
        "لا يقدم الموقع خطة انسحاب منزلية شخصية",
        "لا إيقاف مفاجئ",
        "إزالة السموم وحدها ليست علاجًا كافيًا",
        "جرعة بداية أو زيادة أو إيقاف لشخص بعينه",
        "العلاج القسري",
        "external-clinical-review-required",
    ):
        assert required in text

    for forbidden_claim in ("نضمن الشفاء", "شفاء مضمون", "جدول جرعات ذاتي"):
        assert forbidden_claim not in text


def test_information_architecture_defines_ten_independent_condition_routes():
    text = (ROOT / "docs/addiction-information-architecture.md").read_text(encoding="utf-8")
    routes = (
        "/addiction/alcohol-use-disorder/",
        "/addiction/opioid-use-disorder/",
        "/addiction/stimulant-use-disorder/",
        "/addiction/cannabis-use-disorder/",
        "/addiction/sedative-benzodiazepine-use/",
        "/addiction/nicotine-tobacco-dependence/",
        "/addiction/gambling-related-harms/",
        "/addiction/gaming-disorder/",
        "/addiction/inhalant-use-disorder/",
        "/addiction/polysubstance-use/",
    )
    for route in routes:
        assert route in text
    assert "كل صفحة حالة مستقلة تتضمن بالترتيب" in text
    assert "نموذج عشرة بروتوكولات لكل فئة" in text


def test_robots_exposes_canonical_sitemap_index():
    robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
    expected = "Sitemap: https://healthrenewal.org/sitemap-index.xml"
    assert expected in robots
    assert robots.count(expected) == 1
