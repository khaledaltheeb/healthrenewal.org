import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "learning-paths" / "caregiver-foundations" / "daily-choice-and-supported-participation-plan.json"


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


def test_methodological_depth_and_questions():
    data = load_source()
    workflow = data["workflow"]
    assert len(workflow) >= 8
    assert all(step.get("method") for step in workflow)
    assert all(len(step.get("questions", [])) >= 6 for step in workflow)
    assert sum(len(step["questions"]) for step in workflow) >= 48
    assert len(data["weekly_review"]) >= 10
    assert len(data["red_flags"]) >= 12
    assert len(data["faq"]) >= 6
    assert len(data["decision_record"]["fields"]) >= 10


def test_supported_choice_and_refusal_are_explicit():
    text = flatten(load_source())
    required = [
        "الاختيار",
        "الرفض",
        "التوقف",
        "وسيلة التواصل",
        "تضارب المصلحة",
        "تغيير رأيه",
        "الخصوصية",
        "الكرامة",
        "التخمين",
        "التهديد",
    ]
    for phrase in required:
        assert phrase in text


def test_plan_rejects_coercion_and_false_consent():
    text = flatten(load_source())
    assert "اختيارات زائفة" in text
    assert "اعتبار الصمت موافقة" in text
    assert "سحب وسيلة التواصل" in text
    assert "الحرمان" in text
    assert "استسلام لا موافقة" in text


def test_professional_legal_and_medical_boundaries():
    data = load_source()
    boundary = data["professional_boundary"]
    text = flatten(data)
    assert "ليست تقييمًا تشخيصيًا" in boundary
    assert "القدرة القانونية" in boundary
    assert "القانون المحلي" in boundary
    assert "القرارات الطبية والمالية والقانونية" in boundary
    assert "الطوارئ أو الحماية المحلية" in boundary
    assert "لا توجد شراكة أو رعاية أو اعتماد أو مراجعة خارجية مثبتة" in text
    banned_claims = [
        "معتمد من منظمة الصحة العالمية",
        "معتمد من الأمم المتحدة",
        "بالتعاون مع منظمة الصحة العالمية",
        "شريك رسمي لمنظمة الصحة العالمية",
    ]
    for claim in banned_claims:
        assert claim not in text


def test_source_log_has_recent_official_and_primary_rights_sources():
    data = load_source()
    sources = data["source_log"]
    assert len(sources) >= 7
    urls = [source["url"] for source in sources]
    assert sum("who.int" in url for url in urls) >= 4
    assert sum("un.org" in url for url in urls) >= 3
    assert any(source.get("published") == "2026-05-07" for source in sources)
    assert any(source.get("published") == "2025-07-10" for source in sources)
    assert any("Article 12" in source.get("title", "") for source in sources)
    assert any("General Comment No. 1" in source.get("title", "") for source in sources)
    assert all(source.get("use") for source in sources)
    assert all(source.get("verified_at") == "2026-08-07" for source in sources)


def test_internal_links_are_relative_and_cover_related_family_routes():
    data = load_source()
    links = [item["url"] for item in data["internal_links"]]
    assert "/learning-paths/caregiver-foundations/" in links
    assert "/special-needs/practical/shared-support-plan/" in links
    assert "/sectors/family/guides/family-emergency-plan/" in links
    assert "/sectors/family/guides/caregiver-load-review/" in links
    assert all(link.startswith("/") and not link.startswith("//") for link in links)


def test_json_is_valid_utf8_and_substantive():
    raw = SOURCE.read_text(encoding="utf-8")
    assert len(raw) > 12000
    assert any("\u0600" <= ch <= "\u06ff" for ch in raw)
    json.loads(raw)
