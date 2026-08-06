import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "self-advocacy" / "reasonable-accommodation-request-plan.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_contract_and_review_metadata():
    data = load_data()
    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] == "2027-02-06"
    assert {"Article", "HowTo", "FAQPage"}.issubset(data["schema_types"])


def test_workflow_is_complete_and_practical():
    data = load_data()
    workflow = data["workflow"]
    assert len(workflow) >= 7
    assert [step["step"] for step in workflow] == list(range(1, len(workflow) + 1))
    assert all(step.get("title") and step.get("quality_marker") for step in workflow)
    question_count = sum(len(step.get("questions", [])) for step in workflow)
    assert question_count >= 20
    joined = json.dumps(data, ensure_ascii=False)
    for concept in ["الحاجز", "الخصوصية", "البدائل", "التنفيذ", "المراجعة", "التظلم"]:
        assert concept in joined


def test_professional_limits_and_safeguards():
    data = load_data()
    limits = " ".join(data["professional_limits"])
    assert "لا يمثل استشارة قانونية" in limits
    assert "أكثر مما يلزم" in limits
    assert len(data["red_flags"]) >= 8
    red_flags = " ".join(data["red_flags"])
    for safeguard in ["السجل الطبي الكامل", "دون أسباب", "يعزل الشخص", "معاقبة الشخص", "مشاركة المعلومات"]:
        assert safeguard in red_flags


def test_internal_links_and_sources():
    data = load_data()
    links = data["internal_links"]
    assert len(links) >= 5
    assert all(item["href"].startswith("/") and item["label"] for item in links)
    sources = data["sources"]
    assert len(sources) >= 3
    assert all(item["url"].startswith("https://") for item in sources)
    assert all(item.get("use") and item.get("scope_limit") for item in sources)
    publishers = {item["publisher"] for item in sources}
    assert "United Nations" in publishers
    assert "World Health Organization" in publishers


def test_rights_disclosure_and_language_safety():
    data = load_data()
    disclosure = data["rights_and_disclosure"]
    assert "صياغة عربية أصلية" in disclosure["content_origin"]
    assert "لا يتضمن" in disclosure["copyright"]
    assert "لا توجد شراكة" in disclosure["endorsement"]
    assert "قبل اعتبارها منشورة" in disclosure["editorial_note"]
    text = json.dumps(data, ensure_ascii=False)
    assert "معاقين" not in text
    assert "معاق" not in text
    assert "معتمد من منظمة" not in text
