import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "learning-paths" / "caregiver-foundations" / "bowel-bladder-toileting-observation-and-support-plan.json"


def load_source():
    with SOURCE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def flatten(value):
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value)


def test_metadata_schema_and_review_contract():
    data = load_source()
    meta = data["metadata"]
    assert meta["language"] == "ar"
    assert meta["direction"] == "rtl"
    assert meta["canonical"] == "https://healthrenewal.org/learning-paths/caregiver-foundations/"
    assert meta["verified_at"] == "2026-08-07"
    assert meta["next_review"] == "2027-02-07"
    assert meta["review_status"]
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema"]))


def test_methodological_depth_and_decision_support():
    data = load_source()
    workflow = data["workflow"]
    assert len(workflow) >= 8
    assert all(step.get("method") for step in workflow)
    assert all(len(step.get("questions", [])) >= 6 for step in workflow)
    assert sum(len(step["questions"]) for step in workflow) >= 48
    assert len(data["bowel_bladder_log"]["fields"]) >= 14
    assert len(data["decision_matrix"]) >= 4
    assert len(data["weekly_review"]) >= 10
    assert len(data["red_flags"]) >= 12
    assert len(data["faq"]) >= 8


def test_health_access_and_dignity_are_explicit():
    text = flatten(load_source())
    required = [
        "الإمساك",
        "المثانة",
        "التبول",
        "الإخراج",
        "الألم",
        "خط الأساس",
        "السوائل",
        "الخصوصية",
        "الوصول",
        "غير عقابية",
        "مقدم الرعاية",
        "الجلد",
    ]
    for phrase in required:
        assert phrase in text


def test_plan_rejects_fluid_restriction_and_unsupervised_treatment():
    text = flatten(load_source())
    assert "حرمان السوائل" in text
    assert "تجنب خفض السوائل عمدًا" in text
    assert "لا تبدأ ملينًا" in text
    assert "مضادًا حيويًا" in text
    assert "حقنة شرجية" in text
    assert "قسطرة" in text
    assert "العقاب" in text
    assert "الإذلال" in text


def test_professional_boundaries_and_emergency_escalation():
    data = load_source()
    boundary = data["professional_boundary"]
    text = flatten(data)
    assert "ليست تقييمًا تشخيصيًا" in boundary
    assert "لا تستبدل الطبيب" in boundary
    assert "خدمات الطوارئ المحلية" in boundary
    assert "تغير عصبي جديد" in text
    assert "عدم القدرة على التبول" in text
    assert "لا توجد شراكة أو رعاية أو اعتماد أو مراجعة خارجية مثبتة" in text
    banned_claims = [
        "معتمد من NICE",
        "معتمد من منظمة الصحة العالمية",
        "بالتعاون مع NICE",
        "شريك رسمي لمنظمة الصحة العالمية",
    ]
    for claim in banned_claims:
        assert claim not in text


def test_source_log_has_official_and_current_sources():
    sources = load_source()["source_log"]
    assert len(sources) >= 7
    urls = [source["url"] for source in sources]
    assert sum("nice.org.uk" in url for url in urls) >= 4
    assert sum("who.int" in url for url in urls) >= 3
    assert any(source.get("published") == "2026-05-07" for source in sources)
    assert any(source.get("published") == "2026-01-26" for source in sources)
    assert any(source.get("updated") == "2025-11" for source in sources)
    assert all(source.get("use") for source in sources)
    assert all(source.get("verified_at") == "2026-08-07" for source in sources)


def test_internal_links_are_relative_and_cover_related_routes():
    links = [item["url"] for item in load_source()["internal_links"]]
    assert "/learning-paths/caregiver-foundations/" in links
    assert "/learning-paths/caregiver-foundations/health-change-and-pain-triage.json" in links
    assert "/learning-paths/caregiver-foundations/eating-drinking-swallowing-observation-and-support-plan.json" in links
    assert "/sectors/family/guides/caregiver-load-review/" in links
    assert "/sectors/family/guides/family-emergency-plan/" in links
    assert all(link.startswith("/") and not link.startswith("//") for link in links)


def test_json_is_valid_utf8_and_substantive():
    raw = SOURCE.read_text(encoding="utf-8")
    assert len(raw) > 12000
    assert any("\u0600" <= ch <= "\u06ff" for ch in raw)
    json.loads(raw)
