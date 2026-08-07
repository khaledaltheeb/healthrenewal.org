import json
from pathlib import Path

SOURCE = Path("learning-paths/caregiver-foundations/respiratory-change-and-infection-observation-support-plan.json")


def load():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_file_is_rich_arabic_original_content():
    data = load()
    assert SOURCE.exists()
    assert data["metadata"]["language"] == "ar"
    assert data["metadata"]["direction"] == "rtl"
    assert data["metadata"]["verified_at"] == "2026-08-07"
    assert len(SOURCE.read_text(encoding="utf-8")) > 18000
    assert len(data["principles"]) >= 12


def test_methodology_has_eight_actionable_stages_and_questions():
    data = load()
    assert len(data["stages"]) == 8
    assert sum(len(stage["questions"]) for stage in data["stages"]) >= 48
    for stage in data["stages"]:
        assert stage["id"]
        assert stage["title"]
        assert len(stage["method"]) >= 100
        assert len(stage["questions"]) >= 6
        assert stage["output"]


def test_safety_contract_blocks_diagnosis_drug_and_device_changes():
    data = load()
    text = json.dumps(data, ensure_ascii=False)
    required = [
        "لا تشخّص",
        "لا تبدأ",
        "لا تغيّر تدفق الأكسجين",
        "لا تستخدم مقياس التأكسج كبديل",
        "لا تؤخر الطوارئ",
        "خدمات الطوارئ المحلية",
        "صعوبة تنفس",
        "المضادات الحيوية لا تعالج العدوى الفيروسية",
    ]
    for phrase in required:
        assert phrase in text


def test_observation_decision_and_review_structures_are_complete():
    data = load()
    assert len(data["observation_record"]["fields"]) >= 14
    assert len(data["decision_matrix"]) == 4
    assert len(data["red_flags"]) >= 12
    assert len(data["weekly_review"]) >= 12
    assert len(data["faq"]) >= 8
    assert len(data["internal_links"]) >= 7
    assert len(data["professional_boundaries"]) >= 7


def test_metadata_schema_and_source_governance():
    data = load()
    metadata = data["metadata"]
    assert metadata["canonical"] == "https://healthrenewal.org/learning-paths/caregiver-foundations/"
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema"]))
    assert "مراجعة" in metadata["review_status"]
    assert len(data["source_log"]) >= 7
    official_hosts = ("who.int", "cdc.gov", "nice.org.uk")
    for source in data["source_log"]:
        assert source["source"]
        assert source["type"]
        assert source["checked"] == "2026-08-07"
        assert source["use"]
        assert source["scope_limit"]
        assert any(host in source["url"] for host in official_hosts)
    assert "لا يعني شراكة أو اعتمادًا" in data["copyright_and_independence"]


def test_internal_links_stay_within_known_caregiver_bundle():
    data = load()
    for link in data["internal_links"]:
        assert link["path"].startswith("./")
        assert ".." not in link["path"]
        assert link["reason"]
