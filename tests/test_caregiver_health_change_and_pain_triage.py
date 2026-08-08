import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "caregiver-foundations" / "health-change-and-pain-triage.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def flatten(value):
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value)


def test_metadata_and_schema_contract():
    data = load_data()
    meta = data["metadata"]
    assert meta["canonical"] == "https://healthrenewal.org/learning-paths/caregiver-foundations/"
    assert meta["language"] == "ar"
    assert meta["direction"] == "rtl"
    assert meta["verified_at"] == "2026-08-07"
    assert meta["next_review"] >= "2027-02-01"
    assert "مراجعة" in meta["review_status"]
    assert set(data["schema"]) == {"Article", "HowTo", "FAQPage"}


def test_workflow_is_substantive_and_separates_observation_from_diagnosis():
    data = load_data()
    workflow = data["workflow"]
    assert len(workflow) >= 8
    assert len({step["id"] for step in workflow}) == len(workflow)
    for step in workflow:
        assert len(step["method"]) >= 180
        assert len(step["questions"]) >= 5
        assert len(step["record_fields"]) >= 6
        assert len(step["quality_marker"]) >= 65
    text = flatten(data)
    for phrase in ["خط الأساس", "صوت الشخص", "الألم", "وسيلة التواصل", "فرضية", "التقييم"]:
        assert phrase in text


def test_emergency_stop_and_red_flags_are_explicit():
    data = load_data()
    text = flatten(data)
    flags = data["red_flags"]
    assert len(flags) >= 12
    for phrase in [
        "تنفس",
        "وعي",
        "بلع",
        "نزيف",
        "تشنج",
        "تسمم",
        "ألم شديد",
        "تدهور سريع",
        "فقد قدرة",
        "إساءة",
    ]:
        assert phrase in text
    assert "لا تستكمل السجل" in text
    assert "الطوارئ" in text


def test_silence_does_not_rule_out_pain_and_communication_is_supported():
    text = flatten(load_data())
    assert "الصمت" in text
    assert "لا يساوي غياب الألم" in text
    assert "وسيلة التواصل" in text
    assert "تواصل بديل" in text
    assert "كلمات الشخص أو إشاراته" in text


def test_no_home_diagnosis_or_medication_changes():
    text = flatten(load_data())
    assert "دون تشخيص منزلي" in text
    assert "لا توقف دواءً موصوفًا" in text
    assert "لا تقدم تشخيصًا" in text
    assert "تعليمات دوائية" in text
    forbidden = [
        "غيّر الجرعة",
        "أوقف الدواء فورًا",
        "تشخيص نهائي",
        "يضمن الشفاء",
        "يضمن العلاج",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_decision_matrix_has_four_distinct_levels():
    matrix = load_data()["decision_matrix"]
    assert len(matrix) == 4
    levels = {row["level"] for row in matrix}
    assert levels == {"مراقبة قصيرة", "اتصال صحي", "رعاية عاجلة أو طوارئ", "حماية"}
    for row in matrix:
        assert len(row["when"]) >= 70
        assert len(row["action"]) >= 45


def test_internal_links_are_contextual_local_and_useful():
    links = load_data()["internal_links"]
    assert len(links) >= 6
    urls = {item["url"] for item in links}
    assert "/learning-paths/caregiver-foundations/" in urls
    assert "/daily-tools/medical-visit-preparation/" in urls
    assert "/special-needs/" in urls
    assert "/learning-paths/" in urls
    assert "/source-registry/" in urls
    assert "/trust/" in urls
    assert all(url.startswith("/") for url in urls)
    assert all(len(item["reason"]) >= 35 for item in links)


def test_sources_are_official_scoped_and_recently_verified():
    sources = load_data()["source_registry"]
    assert len(sources) >= 5
    urls = {source["url"] for source in sources}
    assert "https://www.nice.org.uk/guidance/ng11/chapter/recommendations" in urls
    assert "https://www.nice.org.uk/guidance/ng54/chapter/Recommendations" in urls
    assert "https://www.nice.org.uk/guidance/ng96/chapter/recommendations" in urls
    assert "https://www.who.int/publications/i/item/9789240048973" in urls
    assert "https://www.who.int/publications/i/item/9789240120983" in urls
    assert all(source["date"] <= "2026-08-07" for source in sources)
    assert all(len(source["supports"]) >= 90 for source in sources)
    assert all(len(source["use_note"]) >= 100 for source in sources)
    publishers = {source["publisher"] for source in sources}
    assert "National Institute for Health and Care Excellence" in publishers
    assert "World Health Organization" in publishers


def test_rights_disclosure_and_no_false_endorsement():
    data = load_data()
    rights = data["rights_and_disclosure"]
    assert "مؤلف للموقع" in rights["originality"]
    assert "لا يعاد نشر" in rights["copyright_boundary"]
    assert "لا توجد شراكة" in rights["endorsement"]
    assert "لا تقدم تشخيصًا" in rights["professional_boundary"]
    assert "مراجعة تخصصية" in rights["local_adaptation"]
    text = flatten(data)
    forbidden_claims = [
        "معتمد من منظمة الصحة العالمية",
        "معتمد من NICE",
        "بالتعاون الرسمي مع منظمة الصحة العالمية",
        "اعتماد خارجي مكتمل",
    ]
    for claim in forbidden_claims:
        assert claim not in text


def test_faq_is_practical_and_preserves_boundaries():
    faq = load_data()["faq"]
    assert len(faq) >= 6
    for item in faq:
        assert len(item["question"]) >= 25
        assert len(item["answer"]) >= 140
    text = flatten(faq)
    for phrase in ["الألم", "دواء", "الطوارئ", "تشخيص", "التقييم"]:
        assert phrase in text
