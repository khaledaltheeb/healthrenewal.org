import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "learning-paths" / "self-advocacy" / "decision-support-workbook.json"


def load_workbook():
    return json.loads(WORKBOOK.read_text(encoding="utf-8"))


def test_workbook_metadata_and_review_governance():
    data = load_workbook()
    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] == "2027-02-06"
    assert {"HowTo", "FAQPage", "Article"}.issubset(set(data["schema_types"]))


def test_workbook_has_complete_six_step_supported_decision_flow():
    data = load_workbook()
    steps = data["workbook"]
    assert [item["step"] for item in steps] == [1, 2, 3, 4, 5, 6]
    assert len({item["title"] for item in steps}) == 6
    for item in steps:
        assert len(item["questions"]) >= 4
        assert len(item["record"]) >= 4
        assert item["goal"].strip()
        assert item["quality_indicator"].strip()


def test_workbook_protects_will_preferences_and_communication():
    data = load_workbook()
    text = json.dumps(data, ensure_ascii=False)
    required = [
        "الإرادة",
        "التفضيلات",
        "وسيلة التواصل",
        "الرفض",
        "تضارب المصالح",
        "البديل الأقل تقييدًا",
        "تغيير رأيه",
        "التظلم",
    ]
    for phrase in required:
        assert phrase in text


def test_workbook_has_actionable_checklist_and_outcome_measures():
    data = load_workbook()
    assert len(data["rapid_checklist"]) >= 9
    assert len(data["outcome_measures"]) >= 6
    for item in data["outcome_measures"]:
        assert item["indicator"].strip()
        assert item["measure"].strip()


def test_workbook_internal_links_are_root_relative_and_unique():
    data = load_workbook()
    hrefs = [item["href"] for item in data["internal_links"]]
    assert len(hrefs) == len(set(hrefs))
    assert len(hrefs) >= 4
    assert all(href.startswith("/") and href.endswith("/") for href in hrefs)


def test_source_log_is_claim_scoped_and_rights_safe():
    data = load_workbook()
    assert len(data["source_log"]) >= 2
    for source in data["source_log"]:
        assert source["title"].strip()
        assert source["publisher"].strip()
        assert source["source_type"].strip()
        assert source["year"] >= 2014
        assert len(source["claims_supported"]) >= 2
        assert source["use"] == "link-cite-and-original-arabic-summary-only"
        assert source["status"] == "current"
        assert source["verified_at"] == "2026-08-06"

    rights = data["rights"]
    assert rights["copy_policy"] == "original-arabic-synthesis"
    assert rights["restricted_text_copied"] is False
    assert rights["partnership_claimed"] is False
    assert rights["endorsement_claimed"] is False
    assert rights["external_review_claimed"] is False


def test_workbook_avoids_stigmatizing_terminology():
    text = WORKBOOK.read_text(encoding="utf-8")
    banned = ["المعاقين", "المعاق", "عديم الأهلية تلقائيًا"]
    for phrase in banned:
        assert phrase not in text
