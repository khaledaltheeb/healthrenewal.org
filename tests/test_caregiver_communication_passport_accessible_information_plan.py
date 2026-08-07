import json
from pathlib import Path

CONTENT = Path("learning-paths/caregiver-foundations/communication-passport-and-accessible-information-plan.json")


def load():
    return json.loads(CONTENT.read_text(encoding="utf-8"))


def test_required_metadata_and_schema():
    d = load()
    m = d["metadata"]
    assert m["language"] == "ar"
    assert m["direction"] == "rtl"
    assert m["canonical"] == "https://healthrenewal.org/learning-paths/caregiver-foundations/"
    assert m["verified_at"] == "2026-08-07"
    assert {"Article", "HowTo", "FAQPage"} <= set(d["schema"])
    assert "مراجعة" in m["review_status"]


def test_methodological_depth():
    d = load()
    assert len(d["principles"]) >= 10
    assert len(d["stages"]) >= 8
    assert sum(len(x["questions"]) for x in d["stages"]) >= 48
    assert len(d["passport_fields"]) >= 14
    assert len(d["decision_matrix"]) >= 4
    assert len(d["red_flags"]) >= 12
    assert len(d["weekly_review"]) >= 10
    assert len(d["faq"]) >= 8


def test_rights_and_safety_boundaries_are_explicit():
    text = json.dumps(load(), ensure_ascii=False)
    for phrase in [
        "غياب الكلام المنطوق لا يساوي غياب الفهم",
        "لا تقييم للأهلية",
        "لا سحب لجهاز",
        "لا اعتبار الصمت",
        "خدمات الطوارئ",
        "لا تعني شراكة أو اعتمادًا",
    ]:
        assert phrase in text


def test_sources_are_official_and_scoped():
    d = load()
    assert len(d["sources"]) >= 5
    urls = [s["url"] for s in d["sources"]]
    assert any("who.int" in u for u in urls)
    assert any("nice.org.uk" in u for u in urls)
    assert sum("england.nhs.uk" in u for u in urls) >= 2
    assert any("un.org" in u for u in urls)
    assert all(u.startswith("https://") for u in urls)
    notes = " ".join(s["use_note"] for s in d["sources"])
    assert "إنجلترا" in notes
    assert "لا تُعمم" in notes


def test_internal_links_are_contextual_and_local():
    d = load()
    links = d["internal_links"]
    assert len(links) >= 5
    assert all(x["url"].startswith("/") for x in links)
    text = " ".join(x["url"] for x in links)
    assert "professional-visit-and-shared-decision-plan" in text
    assert "daily-choice-and-supported-participation-plan" in text
    assert "health-change-and-pain-triage" in text


def test_original_arabic_content_not_placeholder():
    text = CONTENT.read_text(encoding="utf-8")
    assert len(text) > 15000
    banned = ["Lorem ipsum", "TODO", "PLACEHOLDER", "baseline content"]
    assert not any(x in text for x in banned)
    assert text.count("التواصل") >= 35
    assert text.count("الشخص") >= 35
