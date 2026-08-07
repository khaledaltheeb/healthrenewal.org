import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "caregiver-foundations" / "professional-visit-and-shared-decision-plan.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def flatten(value):
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value)


def test_metadata_contract():
    data = load_data()
    meta = data["metadata"]
    assert meta["canonical"] == "https://healthrenewal.org/learning-paths/caregiver-foundations/"
    assert meta["language"] == "ar"
    assert meta["direction"] == "rtl"
    assert meta["verified_at"] == "2026-08-07"
    assert meta["next_review"] >= "2027-02-01"
    assert "مراجعة" in meta["review_status"]
    assert set(data["schema"]) == {"Article", "HowTo", "FAQPage"}


def test_workflow_is_substantive_and_keeps_person_voice_distinct():
    data = load_data()
    workflow = data["workflow"]
    assert len(workflow) >= 8
    assert len({step["id"] for step in workflow}) == len(workflow)
    for step in workflow:
        assert len(step["method"]) >= 140
        assert len(step["questions"]) >= 5
        assert len(step["record_fields"]) >= 6
        assert len(step["quality_marker"]) >= 50
    text = flatten(data)
    for phrase in ["صوت الشخص", "قلق الأسرة", "وسيلة التواصل", "التيسيرات", "خط الأساس", "عدم اليقين"]:
        assert phrase in text


def test_shared_decision_elements_are_explicit():
    text = flatten(load_data())
    required = [
        "الخيارات",
        "الفوائد",
        "الأضرار",
        "الأعباء",
        "عدم التغيير",
        "وقت",
        "المراجعة",
        "ما يهم الشخص",
        "من المسؤول",
    ]
    for phrase in required:
        assert phrase in text


def test_one_page_brief_is_focused():
    brief = load_data()["one_page_brief"]
    assert len(brief["sections"]) >= 8
    assert "صفحة واحدة" in brief["rule"]
    text = " ".join(brief["sections"])
    for phrase in ["خط الأساس", "التيسيرات", "الخيارات", "المراجعة"]:
        assert phrase in text


def test_red_flags_cover_safety_consent_privacy_and_medication():
    flags = load_data()["red_flags"]
    assert len(flags) >= 12
    text = " ".join(flags)
    for phrase in [
        "تنفس",
        "تغير صحي مفاجئ",
        "الموافقة",
        "وسيلة التواصل",
        "الصمت",
        "الأضرار",
        "بيانات حساسة",
        "دواء",
        "المراجعة",
    ]:
        assert phrase in text


def test_no_diagnostic_treatment_or_endorsement_claims():
    text = flatten(load_data())
    forbidden_claims = [
        "معتمد من منظمة الصحة العالمية",
        "معتمد من NICE",
        "بالتعاون الرسمي مع منظمة الصحة العالمية",
        "تشخيص نهائي",
        "يضمن العلاج",
        "يضمن الشفاء",
    ]
    for claim in forbidden_claims:
        assert claim not in text
    assert "لا تقدم تشخيصًا" in text
    assert "تعليمات دوائية" in text


def test_internal_links_are_contextual_and_local():
    links = load_data()["internal_links"]
    assert len(links) >= 6
    urls = {item["url"] for item in links}
    assert "/learning-paths/caregiver-foundations/" in urls
    assert "/daily-tools/medical-visit-preparation/" in urls
    assert "/learning-paths/" in urls
    assert "/special-needs/" in urls
    assert "/source-registry/" in urls
    assert "/trust/" in urls
    assert all(url.startswith("/") for url in urls)
    assert all(len(item["reason"]) >= 30 for item in links)


def test_source_registry_uses_official_sources_and_scoped_use_notes():
    sources = load_data()["source_registry"]
    assert len(sources) >= 5
    urls = {source["url"] for source in sources}
    assert "https://www.nice.org.uk/guidance/ng197/chapter/Recommendations" in urls
    assert "https://www.who.int/publications/i/item/9789240048836" in urls
    assert "https://www.who.int/publications/i/item/9789240048973" in urls
    assert "https://www.who.int/publications/i/item/9789240120983" in urls
    assert "https://www.who.int/publications/i/item/9789240101517" in urls
    assert all(source["date"] <= "2026-08-07" for source in sources)
    assert all(len(source["supports"]) >= 60 for source in sources)
    assert all(len(source["use_note"]) >= 80 for source in sources)
    publishers = {source["publisher"] for source in sources}
    assert "National Institute for Health and Care Excellence" in publishers
    assert "World Health Organization" in publishers


def test_rights_and_local_adaptation_disclosure():
    rights = load_data()["rights_and_disclosure"]
    assert "مؤلف للموقع" in rights["originality"]
    assert "لا يعاد نشر" in rights["copyright_boundary"]
    assert "لا توجد شراكة" in rights["endorsement"]
    assert "لا تقدم تشخيصًا" in rights["professional_boundary"]
    assert "مراجعة تخصصية" in rights["local_adaptation"]


def test_faq_is_practical_and_preserves_professional_boundary():
    faq = load_data()["faq"]
    assert len(faq) >= 6
    for item in faq:
        assert len(item["question"]) >= 25
        assert len(item["answer"]) >= 120
    text = flatten(faq)
    assert "تشخيص" in text
    assert "الطوارئ" in text
    assert "القرار المشترك" in text
