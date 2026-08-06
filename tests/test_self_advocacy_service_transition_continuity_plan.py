import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "self-advocacy" / "service-transition-and-continuity-plan.json"


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


def test_workflow_is_complete_and_measurable():
    data = load_data()
    workflow = data["workflow"]
    assert len(workflow) >= 7
    assert [item["step"] for item in workflow] == list(range(1, len(workflow) + 1))
    assert sum(len(item.get("questions", [])) for item in workflow) >= 28
    assert all(item.get("title") and item.get("quality_marker") for item in workflow)
    assert len(workflow[-1]["outcome_measures"]) >= 6


def test_continuity_and_handover_safeguards_are_explicit():
    data = load_data()
    text = json.dumps(data, ensure_ascii=False)
    required = [
        "ما يجب ألا ينقطع",
        "أقل قدر لازم",
        "تأكيد الاستلام",
        "الخطة المؤقتة",
        "وسيلة التواصل",
        "التيسيرات",
        "فترة التداخل أو الفراغ",
        "30 و90 يومًا",
        "قناة التصعيد",
    ]
    for phrase in required:
        assert phrase in text
    assert len(data["red_flags"]) >= 10
    assert len(data["quick_checklist"]) >= 9


def test_professional_limits_and_no_false_endorsement():
    data = load_data()
    text = json.dumps(data, ensure_ascii=False)
    assert len(data["professional_limits"]) >= 5
    assert "لا يمثل خطة علاج فردية أو استشارة قانونية" in text
    assert "لا توجد شراكة" in data["rights_and_attribution"]["partnership_disclosure"]
    prohibited = [
        "معتمد من منظمة الصحة العالمية",
        "بشراكة مع الأمم المتحدة",
        "مصدق رسميًا",
    ]
    for phrase in prohibited:
        assert phrase not in text


def test_sources_are_official_and_claim_scoped():
    data = load_data()
    sources = data["source_log"]
    assert len(sources) >= 3
    assert any("ohchr.org" in source["url"] for source in sources)
    assert any("who.int" in source["url"] for source in sources)
    assert any("nice.org.uk" in source["url"] for source in sources)
    for source in sources:
        assert source["title"]
        assert source["publisher"]
        assert source["url"].startswith("https://")
        assert source["used_for"]
        assert source["limits"]


def test_internal_links_and_faq_are_present():
    data = load_data()
    assert len(data["internal_links"]) >= 5
    assert all(link.startswith("/") and link.endswith("/") for link in data["internal_links"])
    assert len(data["faq"]) >= 4
    assert all(item["question"].endswith("؟") and item["answer"] for item in data["faq"])


def test_language_avoids_stigmatizing_term():
    data = load_data()
    text = json.dumps(data, ensure_ascii=False)
    assert "معاقين" not in text
    assert "المعاق" not in text
