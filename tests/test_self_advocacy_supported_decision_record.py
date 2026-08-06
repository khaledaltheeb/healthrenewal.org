import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "learning-paths" / "self-advocacy" / "supported-decision-record.json"


def load_record():
    with RECORD.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_supported_decision_record_metadata_and_review_contract():
    data = load_record()
    assert data["id"] == "self-advocacy-supported-decision-record-v1"
    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] > data["verified_at"]
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema_types"]))


def test_supported_decision_record_is_operational_and_complete():
    data = load_record()
    sections = data["record_sections"]
    assert len(sections) >= 8
    assert [section["order"] for section in sections] == list(range(1, len(sections) + 1))
    assert sum(len(section["questions"]) for section in sections) >= 24
    assert all(section["record_fields"] for section in sections)
    assert len(data["quality_checks"]) >= 8
    assert len(data["red_flags"]) >= 6
    assert len(data["faq"]) >= 3


def test_supported_decision_record_protects_will_preferences_and_access():
    data = load_record()
    corpus = json.dumps(data, ensure_ascii=False)
    required = [
        "إرادة الشخص",
        "تضارب المصالح",
        "وسيلة التواصل",
        "التيسيرات",
        "الرفض",
        "التردد",
        "تغيير القرار",
        "عدم اليقين",
        "الدعم المستقل",
    ]
    for phrase in required:
        assert phrase in corpus
    assert "اعتبار الصمت" in corpus
    assert "تسجيل رأي الداعم على أنه رأي الشخص" in corpus


def test_supported_decision_record_has_internal_links_and_source_governance():
    data = load_record()
    links = data["internal_links"]
    assert len(links) >= 5
    assert all(link.startswith("/") for link in links)
    assert "/trust/" in links
    assert "/source-registry/" in links

    sources = data["sources"]
    assert len(sources) >= 2
    assert all(source["url"].startswith("https://") for source in sources)
    assert all(source["verified_at"] == "2026-08-06" for source in sources)
    assert all(source["use"] and source["limits"] for source in sources)

    disclosure = data["rights_and_disclosure"]
    assert "صياغة عربية أصلية" in disclosure["content_origin"]
    assert "لا توجد شراكة" in disclosure["partnership_claim"]
    assert "حقوق المواد الأصلية" in disclosure["source_usage"]


def test_supported_decision_record_avoids_unverified_authority_claims_and_stigma():
    text = RECORD.read_text(encoding="utf-8")
    forbidden = [
        "معتمد من منظمة الصحة العالمية",
        "معتمد من الأمم المتحدة",
        "شريك رسمي",
        "مراجعة خارجية مكتملة",
        "المعاقين",
    ]
    for phrase in forbidden:
        assert phrase not in text
