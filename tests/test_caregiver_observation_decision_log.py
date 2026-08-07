import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "caregiver-foundations" / "observation-decision-log.json"


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
    data = load_data()
    workflow = data["workflow"]
    assert len(workflow) >= 8
    assert len({step["id"] for step in workflow}) == len(workflow)
    for step in workflow:
        assert len(step["method"]) >= 120
        assert len(step["questions"]) >= 5
        assert len(step["record_fields"]) >= 5
        assert len(step["quality_marker"]) >= 35


def test_person_voice_safety_and_caregiver_wellbeing_are_explicit():
    text = flatten(load_data())
    required = [
        "صوت الشخص",
        "القبول",
        "الرفض",
        "وسيلة التواصل",
        "الاستقلال",
        "مقدم الرعاية",
        "إرهاق",
        "الألم",
        "الحماية",
        "الطوارئ",
        "الخصوصية",
    ]
    for phrase in required:
        assert phrase in text


def test_no_compliance_only_or_diagnostic_framing():
    text = flatten(load_data())
    assert "لا إلى إثبات الطاعة" in text
    assert "ليس" in text or "لا يقدّم تشخيصًا" in text
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


def test_internal_links_are_contextual_and_local():
    links = load_data()["internal_links"]
    assert len(links) >= 5
    urls = {item["url"] for item in links}
    assert "/learning-paths/caregiver-foundations/" in urls
    assert "/special-needs/" in urls
    assert "/source-registry/" in urls
    assert "/trust/" in urls
    assert all(url.startswith("/") for url in urls)


def test_source_registry_uses_primary_official_sources_and_dates():
    sources = load_data()["source_registry"]
    assert len(sources) >= 5
    urls = {source["url"] for source in sources}
    assert "https://www.who.int/publications/i/item/9789240048836" in urls
    assert "https://www.who.int/publications/i/item/9789240120983" in urls
    assert "https://www.who.int/publications/i/item/9789240101517" in urls
    assert all(source["publisher"] == "World Health Organization" for source in sources)
    assert all(source["date"] <= "2026-08-07" for source in sources)
    assert all(len(source["supports"]) >= 2 for source in sources)
    assert all(len(source["use_note"]) >= 45 for source in sources)


def test_rights_and_endorsement_disclosure():
    rights = load_data()["rights_and_disclosure"]
    assert "مؤلف للموقع" in rights["originality"]
    assert "لا يعاد نشر" in rights["copyright_boundary"]
    assert "لا توجد شراكة" in rights["endorsement"]
    assert "مراجعة تخصصية" in rights["local_adaptation"]


def test_weekly_review_forces_a_single_next_decision():
    review = load_data()["weekly_review"]
    assert len(review["questions"]) >= 7
    assert set(review["decision_options"]) >= {
        "استمرار",
        "تعديل عنصر واحد",
        "إيقاف",
        "طلب تقييم أوسع",
        "تصعيد سلامة أو حماية",
    }


def test_red_flags_cover_core_failure_modes():
    flags = load_data()["red_flags"]
    assert len(flags) >= 10
    text = " ".join(flags)
    for phrase in ["الصمت", "وسيلة التواصل", "بيانات حساسة", "الضيق", "مقدم الرعاية", "تراجع صحي"]:
        assert phrase in text
