import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "self-advocacy" / "meeting-preparation-checklist.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_meeting_checklist_core_metadata():
    data = load_data()
    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"]
    assert data["next_review_at"]
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema_types"]))


def test_meeting_checklist_is_practical_and_complete():
    data = load_data()
    assert len(data["before_meeting"]) >= 5
    assert len(data["during_meeting"]) >= 5
    assert len(data["after_meeting"]) >= 5
    assert len(data["red_flags"]) >= 8
    assert len(data["outcome_measures"]) >= 6
    assert len(data["faq"]) >= 3
    assert len(data["internal_links"]) >= 4

    questions = []
    for item in data["before_meeting"]:
        questions.extend(item.get("questions", []))
    assert len(questions) >= 8
    assert all(question.strip().endswith("؟") for question in questions)


def test_meeting_checklist_protects_will_and_preferences():
    data = load_data()
    text = json.dumps(data, ensure_ascii=False)
    required_terms = [
        "إرادة الشخص",
        "الرفض",
        "التردد",
        "وسيلة التواصل",
        "تضارب المصالح",
        "التظلم",
        "تغيير رأيه",
    ]
    for term in required_terms:
        assert term in text

    prohibited_terms = [
        "معاقين",
        "فاقد الأهلية تلقائيًا",
        "شراكة مع منظمة الصحة العالمية",
        "معتمد من الأمم المتحدة",
    ]
    for term in prohibited_terms:
        assert term not in text


def test_meeting_checklist_source_and_rights_contract():
    data = load_data()
    sources = data["sources"]
    assert len(sources) >= 2
    for source in sources:
        assert source["id"]
        assert source["organization"]
        assert source["title"]
        assert source["url"].startswith("https://")
        assert source["source_type"].startswith("official_")
        assert source["rights"] == "link-cite-and-original-summary-only"
        assert source["verified_at"]

    disclosure = data["rights_and_disclosures"]
    assert disclosure["content_origin"] == "original_arabic_editorial_content"
    assert disclosure["partnership_claim"] == "none"
    assert disclosure["endorsement_claim"] == "none"
    assert disclosure["external_review_completed"] is False


def test_internal_links_are_absolute_site_paths():
    data = load_data()
    for link in data["internal_links"]:
        assert link["href"].startswith("/")
        assert not link["href"].startswith("//")
        assert link["label"].strip()
