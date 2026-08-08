import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "learning-paths" / "caregiver-foundations" / "sensory-environment-and-routine-adjustment-plan.json"


def load_source():
    with SOURCE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def flatten(value):
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value)


def test_metadata_and_schema_contract():
    data = load_source()
    meta = data["metadata"]
    assert meta["language"] == "ar"
    assert meta["direction"] == "rtl"
    assert meta["canonical"] == "https://healthrenewal.org/learning-paths/caregiver-foundations/"
    assert meta["verified_at"] == "2026-08-07"
    assert meta["review_status"]
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema"]))


def test_methodological_depth_and_practical_questions():
    data = load_source()
    workflow = data["workflow"]
    assert len(workflow) >= 8
    assert all(step.get("method") for step in workflow)
    assert all(len(step.get("questions", [])) >= 5 for step in workflow)
    assert sum(len(step.get("questions", [])) for step in workflow) >= 40
    assert len(data["weekly_review"]) >= 8
    assert len(data["faq"]) >= 5
    assert len(data["red_flags"]) >= 10


def test_person_voice_safety_and_non_compliance_outcomes():
    text = flatten(load_source())
    required = [
        "صوت الشخص",
        "طلب الاستراحة",
        "التوقف",
        "المشاركة",
        "الراحة",
        "الاستقلال",
        "الألم",
        "التقييم الصحي",
        "لا تعتبر",
    ]
    for phrase in required:
        assert phrase in text
    assert "الامتثال" in text
    assert "العزل" in text


def test_professional_boundaries_and_no_unverified_endorsement():
    data = load_source()
    text = flatten(data)
    assert data["professional_boundary"]
    assert "ليست تقييمًا تشخيصيًا" in data["professional_boundary"]
    assert "لا توجد شراكة أو رعاية أو اعتماد أو مراجعة خارجية مثبتة" in text
    banned_claims = [
        "معتمد من منظمة الصحة العالمية",
        "معتمد من NICE",
        "بالتعاون مع منظمة الصحة العالمية",
        "شريك رسمي لمنظمة الصحة العالمية",
    ]
    for claim in banned_claims:
        assert claim not in text


def test_source_log_uses_primary_or_official_sources_and_scope_notes():
    data = load_source()
    sources = data["source_log"]
    assert len(sources) >= 5
    urls = [source["url"] for source in sources]
    assert any("who.int" in url for url in urls)
    assert any("nice.org.uk" in url for url in urls)
    assert any("un.org" in url for url in urls)
    assert all(source.get("use") for source in sources)
    assert any(source.get("last_reviewed") == "2025-09-05" for source in sources)


def test_internal_links_are_site_relative_and_known_routes():
    data = load_source()
    links = [item["url"] for item in data["internal_links"]]
    assert "/learning-paths/caregiver-foundations/" in links
    assert "/special-needs/practical/hospital-communication-passport/" in links
    assert all(link.startswith("/") and not link.startswith("//") for link in links)


def test_experiment_card_prevents_unstructured_intervention_stacking():
    data = load_source()
    card = data["experiment_card"]
    assert len(card["fields"]) >= 8
    text = flatten(data)
    assert "تعديلًا واحدًا" in text or "تعديل واحد" in text
    assert "قابلًا للعكس" in text
    assert "موعد المراجعة" in text


def test_json_is_valid_utf8_arabic_content():
    raw = SOURCE.read_text(encoding="utf-8")
    assert len(raw) > 10000
    assert any("\u0600" <= ch <= "\u06ff" for ch in raw)
    json.loads(raw)
