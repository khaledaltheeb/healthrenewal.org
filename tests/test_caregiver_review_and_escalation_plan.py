import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "caregiver-foundations" / "review-and-escalation-plan.json"


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


def test_workflow_is_substantive_and_actionable():
    workflow = load_data()["workflow"]
    assert len(workflow) >= 8
    assert len({step["id"] for step in workflow}) == len(workflow)
    for step in workflow:
        assert len(step["method"]) >= 120
        assert len(step["questions"]) >= 5
        assert len(step["record_fields"]) >= 5
        assert len(step["quality_marker"]) >= 45


def test_decision_matrix_covers_all_required_outcomes():
    matrix = load_data()["decision_matrix"]
    decisions = {item["decision"] for item in matrix}
    assert decisions >= {
        "استمرار",
        "تعديل عنصر واحد",
        "تقليل الدعم تدريجيًا",
        "إيقاف",
        "طلب تقييم أوسع",
        "تصعيد سلامة أو حماية",
    }
    for item in matrix:
        assert len(item["when"]) >= 55
        assert len(item["next_action"]) >= 45


def test_person_voice_function_and_wellbeing_are_explicit():
    text = flatten(load_data())
    required = [
        "صوت الشخص",
        "القبول",
        "الرفض",
        "وسيلة التواصل",
        "المشاركة",
        "الاستقلال",
        "الراحة",
        "مقدم الرعاية",
        "الإرهاق",
        "الألم",
        "الحماية",
        "الطوارئ",
        "الخصوصية",
    ]
    for phrase in required:
        assert phrase in text


def test_no_compliance_only_diagnostic_or_endorsement_framing():
    text = flatten(load_data())
    assert "لا تكتفي" in text or "لا يُختزل" in text
    forbidden_claims = [
        "معتمد من منظمة الصحة العالمية",
        "بالتعاون الرسمي مع منظمة الصحة العالمية",
        "شريك منظمة الصحة العالمية",
        "تشخيص نهائي",
        "يضمن العلاج",
        "يضمن الشفاء",
    ]
    for claim in forbidden_claims:
        assert claim not in text


def test_weekly_review_forces_one_next_decision_and_stop_rule():
    review = load_data()["weekly_review"]
    assert len(review["questions"]) >= 9
    assert set(review["decision_options"]) >= {
        "استمرار",
        "تعديل عنصر واحد",
        "تقليل الدعم تدريجيًا",
        "إيقاف",
        "طلب تقييم أوسع",
        "تصعيد سلامة أو حماية",
    }
    text = " ".join(review["questions"])
    assert "شرط الإيقاف" in text or "التصعيد" in text


def test_red_flags_cover_core_failure_modes():
    flags = load_data()["red_flags"]
    assert len(flags) >= 12
    text = " ".join(flags)
    for phrase in [
        "تغير صحي مفاجئ",
        "التنفس",
        "إساءة",
        "وسيلة التواصل",
        "الصمت",
        "الانسحاب",
        "بيانات حساسة",
        "مقدم الرعاية",
        "تشخيص",
    ]:
        assert phrase in text


def test_internal_links_are_contextual_and_local():
    links = load_data()["internal_links"]
    assert len(links) >= 6
    urls = {item["url"] for item in links}
    assert "/learning-paths/caregiver-foundations/" in urls
    assert "/learning-paths/" in urls
    assert "/special-needs/" in urls
    assert "/source-registry/" in urls
    assert "/trust/" in urls
    assert all(url.startswith("/") for url in urls)


def test_source_registry_uses_official_primary_sources_and_current_dates():
    sources = load_data()["source_registry"]
    assert len(sources) >= 5
    urls = {source["url"] for source in sources}
    assert "https://www.who.int/publications/i/item/9789240048836" in urls
    assert "https://www.who.int/publications/i/item/9789240048973" in urls
    assert "https://www.who.int/publications/i/item/9789240120983" in urls
    assert "https://www.who.int/publications/i/item/B09617" in urls
    assert "https://www.who.int/publications/i/item/9789240101517" in urls
    assert all(source["publisher"] == "World Health Organization" for source in sources)
    assert all(source["date"] <= "2026-08-07" for source in sources)
    assert all(len(source["supports"]) >= 45 for source in sources)
    assert all(len(source["use_note"]) >= 60 for source in sources)


def test_rights_and_local_adaptation_disclosure():
    rights = load_data()["rights_and_disclosure"]
    assert "مؤلف للموقع" in rights["originality"]
    assert "لا يعاد نشر" in rights["copyright_boundary"]
    assert "لا توجد شراكة" in rights["endorsement"]
    assert "مراجعة تخصصية" in rights["local_adaptation"]


def test_faq_is_practical_and_not_diagnostic():
    faq = load_data()["faq"]
    assert len(faq) >= 5
    for item in faq:
        assert len(item["question"]) >= 20
        assert len(item["answer"]) >= 100
    text = flatten(faq)
    assert "تشخيص" in text
    assert "المشاركة" in text
