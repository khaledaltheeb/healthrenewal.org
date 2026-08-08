import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "learning-paths" / "caregiver-foundations" / "sleep-routine-observation-and-support-plan.json"


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
    assert len(data["sleep_log"]["fields"]) >= 12
    assert len(data["decision_matrix"]) >= 4
    assert len(data["weekly_review"]) >= 10
    assert len(data["red_flags"]) >= 12
    assert len(data["faq"]) >= 8


def test_sleep_assessment_and_health_differential_are_explicit():
    text = flatten(load_source())
    required = [
        "بدء النوم",
        "الاستيقاظات الليلية",
        "القيلولة",
        "النعاس النهاري",
        "الألم",
        "الشخير",
        "توقف تنفس",
        "الأدوية",
        "البيئة",
        "خط الأساس",
        "أسبوعين",
        "مقدم الرعاية",
    ]
    for phrase in required:
        assert phrase in text


def test_plan_rejects_unsupervised_medication_and_coercive_sleep_management():
    text = flatten(load_source())
    assert "لا تغيّر دواءً موصوفًا" in text
    assert "الميلاتونين" in text
    assert "اختصاصًا ومراجعة" in text
    assert "التقييد" in text
    assert "الحرمان" in text
    assert "اختبار طاعة" in text


def test_professional_boundaries_and_emergency_escalation():
    data = load_source()
    boundary = data["professional_boundary"]
    text = flatten(data)
    assert "ليست تقييمًا تشخيصيًا" in boundary
    assert "ليست وصفة دوائية" in boundary
    assert "خدمات الطوارئ المحلية" in boundary
    assert "علامات التنفس" in text
    assert "إحالة متخصصة" in text
    assert "لا توجد شراكة أو رعاية أو اعتماد أو مراجعة خارجية مثبتة" in text
    banned_claims = [
        "معتمد من NICE",
        "معتمد من منظمة الصحة العالمية",
        "بالتعاون مع NICE",
        "شريك رسمي لمنظمة الصحة العالمية",
    ]
    for claim in banned_claims:
        assert claim not in text


def test_source_log_has_recent_review_and_official_sources():
    sources = load_source()["source_log"]
    assert len(sources) >= 6
    urls = [source["url"] for source in sources]
    assert sum("nice.org.uk" in url for url in urls) >= 2
    assert sum("who.int" in url for url in urls) >= 3
    assert any("pubmed.ncbi.nlm.nih.gov/39932204" in url for url in urls)
    assert any(source.get("published") == "2025-07-01" for source in sources)
    assert any(source.get("published") == "2026-05-07" for source in sources)
    assert any(source.get("reviewed") == "2025-09-05" for source in sources)
    assert all(source.get("use") for source in sources)
    assert all(source.get("verified_at") == "2026-08-07" for source in sources)


def test_internal_links_are_relative_and_cover_related_routes():
    links = [item["url"] for item in load_source()["internal_links"]]
    assert "/learning-paths/caregiver-foundations/" in links
    assert "/sectors/family/guides/caregiver-load-review/" in links
    assert "/magazine/neurodevelopmental-sleep-family-wellbeing-review-2026.html" in links
    assert "/sectors/family/guides/family-emergency-plan/" in links
    assert "/special-needs/practical/shared-support-plan/" in links
    assert all(link.startswith("/") and not link.startswith("//") for link in links)


def test_json_is_valid_utf8_and_substantive():
    raw = SOURCE.read_text(encoding="utf-8")
    assert len(raw) > 12000
    assert any("\u0600" <= ch <= "\u06ff" for ch in raw)
    json.loads(raw)
