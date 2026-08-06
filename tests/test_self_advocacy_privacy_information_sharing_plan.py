import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "self-advocacy" / "privacy-and-information-sharing-plan.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_contract_metadata_and_review_state():
    data = load_data()
    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] > data["verified_at"]
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema_types"]))


def test_workflow_is_practical_and_complete():
    data = load_data()
    workflow = data["workflow"]
    assert len(workflow) >= 7
    assert [item["step"] for item in workflow] == list(range(1, len(workflow) + 1))
    question_count = sum(len(item.get("questions", [])) for item in workflow)
    assert question_count >= 24
    assert all(item.get("title") and item.get("quality_marker") for item in workflow)


def test_privacy_safeguards_are_explicit():
    data = load_data()
    text = json.dumps(data, ensure_ascii=False)
    required = [
        "أقل قدر لازم",
        "تقليل البيانات",
        "سحب موافقته",
        "تضارب المصالح",
        "تصحيح",
        "الاعتراض",
        "مدة الحفظ",
        "دون موافقة",
        "وسيلة التواصل",
    ]
    for phrase in required:
        assert phrase in text
    assert len(data["red_flags"]) >= 9
    assert len(data["quick_checklist"]) >= 8


def test_professional_limits_and_no_false_endorsement():
    data = load_data()
    text = json.dumps(data, ensure_ascii=False)
    assert len(data["professional_limits"]) >= 5
    assert "لا يمثل استشارة قانونية" in text
    assert "لا توجد شراكة" in data["rights_and_disclosures"]["partnership"]
    prohibited = ["معتمد من منظمة الصحة العالمية", "بشراكة مع الأمم المتحدة", "مصدق رسميًا"]
    for phrase in prohibited:
        assert phrase not in text


def test_sources_are_official_and_claim_scoped():
    data = load_data()
    sources = data["sources"]
    assert len(sources) >= 2
    assert any("ohchr" in source["url"] for source in sources)
    assert any("who.int" in source["url"] for source in sources)
    for source in sources:
        assert source["title"]
        assert source["publisher"]
        assert source["url"].startswith("https://")
        assert source["claims_supported"]
        assert "use" in source


def test_internal_links_and_faq_are_present():
    data = load_data()
    assert len(data["internal_links"]) >= 4
    assert all(link.startswith("/") and link.endswith("/") for link in data["internal_links"])
    assert len(data["faq"]) >= 4
    assert all(item["question"].endswith("؟") and item["answer"] for item in data["faq"])


def test_language_avoids_stigmatizing_term():
    data = load_data()
    text = json.dumps(data, ensure_ascii=False)
    assert "معاقين" not in text
    assert "المعاق" not in text
