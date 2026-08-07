import json
from pathlib import Path

CONTENT = Path("learning-paths/caregiver-foundations/oral-health-and-dental-visit-support-plan.json")


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
    assert len(d["principles"]) >= 8
    assert len(d["stages"]) >= 8
    assert sum(len(x["questions"]) for x in d["stages"]) >= 48
    assert len(d["visit_card_fields"]) >= 12
    assert len(d["decision_matrix"]) >= 4
    assert len(d["red_flags"]) >= 12
    assert len(d["faq"]) >= 8


def test_safety_boundaries_are_explicit():
    text = json.dumps(load(), ensure_ascii=False)
    for phrase in [
        "لا تشخيص منزلي",
        "لا بدء مضاد حيوي",
        "صعوبة تنفس",
        "خدمات الطوارئ",
        "لا استخدام التقييد",
        "لا تعني شراكة أو اعتمادًا",
    ]:
        assert phrase in text


def test_sources_are_primary_or_official():
    d = load()
    assert len(d["sources"]) >= 4
    urls = [s["url"] for s in d["sources"]]
    assert any("who.int" in u for u in urls)
    assert sum("nice.org.uk" in u for u in urls) >= 2
    assert all(u.startswith("https://") for u in urls)


def test_internal_links_stay_within_site_path():
    d = load()
    links = d["internal_links"]
    assert len(links) >= 4
    assert all(x["url"].startswith("/") for x in links)
    assert any("health-change-and-pain-triage" in x["url"] for x in links)
    assert any("professional-visit-and-shared-decision-plan" in x["url"] for x in links)


def test_original_arabic_content_not_placeholder():
    text = CONTENT.read_text(encoding="utf-8")
    assert len(text) > 12000
    banned = ["Lorem ipsum", "TODO", "PLACEHOLDER", "baseline content"]
    assert not any(x in text for x in banned)
    assert text.count("الأسرة") >= 8
