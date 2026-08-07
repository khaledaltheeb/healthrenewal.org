import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "learning-paths" / "caregiver-foundations" / "caregiver-support-network-and-respite-plan.json"


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


def test_person_voice_privacy_and_safety_are_explicit():
    text = flatten(load_source())
    required = [
        "صوت الشخص",
        "القبول أو الرفض",
        "التوقف",
        "الخصوصية",
        "وسيلة التواصل",
        "العزل",
        "التقييد",
        "الأدوية",
        "الطوارئ",
        "الحماية",
    ]
    for phrase in required:
        assert phrase in text


def test_respite_is_not_overclaimed_as_universally_effective():
    text = flatten(load_source())
    assert "ليست متجانسة" in text
    assert "لا توجد مدة واحدة" in text
    assert "لا تُقدّم الخطة وعودًا بنتيجة ثابتة" in text
    assert "الاستراحة ليست انسحابًا من المسؤولية" in text


def test_handover_card_and_network_design_are_operational():
    data = load_source()
    assert len(data["handover_card"]["fields"]) >= 10
    text = flatten(data)
    assert "أقل قدر من المعلومات" in text
    assert "داعم" in text
    assert "خطة بديلة" in text
    assert "مهمة حرجة" in text
    assert "استراحة فعلية" in text


def test_professional_boundaries_and_no_unverified_endorsement():
    data = load_source()
    text = flatten(data)
    boundary = data["professional_boundary"]
    assert "ليست تقييمًا تشخيصيًا" in boundary
    assert "لا استشارة قانونية أو طبية فردية" in boundary
    assert "القانون المحلي" in boundary
    assert "لا توجد شراكة أو رعاية أو اعتماد أو مراجعة خارجية مثبتة" in text
    banned_claims = [
        "معتمد من منظمة الصحة العالمية",
        "معتمد من NICE",
        "بالتعاون مع منظمة الصحة العالمية",
        "شريك رسمي لمنظمة الصحة العالمية",
    ]
    for claim in banned_claims:
        assert claim not in text


def test_source_log_has_recent_official_and_systematic_review_sources():
    data = load_source()
    sources = data["source_log"]
    assert len(sources) >= 6
    urls = [source["url"] for source in sources]
    assert sum("who.int" in url for url in urls) >= 2
    assert sum("nice.org.uk" in url for url in urls) >= 3
    assert any("pubmed.ncbi.nlm.nih.gov" in url for url in urls)
    assert any(source.get("published") == "2026-05-07" for source in sources)
    assert any(source.get("published") == "2025-06-26" for source in sources)
    assert all(source.get("use") for source in sources)
    assert all(source.get("verified_at") == "2026-08-07" for source in sources)


def test_internal_links_are_relative_and_cover_related_family_routes():
    data = load_source()
    links = [item["url"] for item in data["internal_links"]]
    assert "/learning-paths/caregiver-foundations/" in links
    assert "/sectors/family/guides/caregiver-load-review/" in links
    assert "/sectors/family/guides/family-emergency-plan/" in links
    assert "/special-needs/practical/shared-support-plan/" in links
    assert all(link.startswith("/") and not link.startswith("//") for link in links)


def test_json_is_valid_utf8_and_substantive():
    raw = SOURCE.read_text(encoding="utf-8")
    assert len(raw) > 12000
    assert any("\u0600" <= ch <= "\u06ff" for ch in raw)
    json.loads(raw)
