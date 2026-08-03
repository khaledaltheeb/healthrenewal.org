from __future__ import annotations

from datetime import date
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_program_is_truthfully_marked_as_foundation():
    index = load_json("api/v1/addiction-center.json")
    assert index["program_status"] == "foundation-draft"
    assert "لا يمثل اكتمال" in index["publication_claim"]
    assert index["protocol_total"] == 100
    assert index["reference_count"] >= 50
    assert index["structured_reference_count"] >= 12


def test_governance_contracts_are_linked_and_exist():
    index = load_json("api/v1/addiction-center.json")
    for field in (
        "governance_document",
        "safety_contract",
        "information_architecture",
        "structured_source_registry",
    ):
        assert (ROOT / index[field]).is_file(), field

    next_wave = index["required_next_wave"]
    assert next_wave["independent_condition_pages"] == 10
    assert next_wave["family_guides"] >= 12
    assert next_wave["practical_tools"] >= 12
    assert next_wave["special_population_guides"] >= 12
    assert next_wave["claim_source_map_required"] is True
    assert next_wave["external_clinical_review_required_for_accreditation_claim"] is True


def test_structured_source_registry_is_reviewable():
    registry = load_json("data/addiction-evidence/source-registry.json")
    sources = registry["sources"]
    assert len(sources) >= 12
    identifiers = [item["id"] for item in sources]
    assert len(identifiers) == len(set(identifiers))

    required_fields = set(registry["required_fields"])
    verified_on = date.fromisoformat(registry["verified_on"])
    authorities = set()
    for source in sources:
        assert required_fields.issubset(source), source.get("id")
        assert source["url"].startswith("https://")
        assert date.fromisoformat(source["verified_on"]) <= verified_on
        assert date.fromisoformat(source["next_review_on"]) > verified_on
        assert source["topics"]
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
