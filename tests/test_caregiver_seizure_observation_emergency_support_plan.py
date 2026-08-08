import json
from pathlib import Path

CONTENT = Path("learning-paths/caregiver-foundations/seizure-observation-and-emergency-support-plan.json")


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
    assert len(d["event_log_fields"]) >= 16
    assert len(d["decision_matrix"]) >= 4
    assert len(d["red_flags"]) >= 12
    assert len(d["weekly_review"]) >= 10
    assert len(d["faq"]) >= 8


def test_safety_boundaries_are_explicit():
    text = json.dumps(load(), ensure_ascii=False)
    for phrase in [
        "لا تشخيص منزلي",
        "لا بدء أو إيقاف أو تغيير جرعة دواء مضاد للنوبات",
        "لا تقييد الشخص",
        "لا تضع ملعقة أو أصابع أو أي جسم في فم الشخص",
        "خدمات الطوارئ المحلية",
        "5 دقائق",
        "لا تعني الإحالة إلى WHO أو NICE أو CDC",
    ]:
        assert phrase in text


def test_sources_are_official_current_and_scope_limited():
    d = load()
    assert len(d["sources"]) >= 6
    urls = [s["url"] for s in d["sources"]]
    assert any("who.int" in u for u in urls)
    assert sum("nice.org.uk" in u for u in urls) >= 4
    assert any("cdc.gov" in u for u in urls)
    assert all(u.startswith("https://") for u in urls)
    nice = [s for s in d["sources"] if "nice.org.uk" in s["url"]]
    assert all("2025-01-30" == s["date"] for s in nice)
    assert any("المملكة المتحدة" in s["scope"] for s in nice)


def test_internal_links_connect_related_caregiver_packages():
    d = load()
    links = d["internal_links"]
    assert len(links) >= 6
    assert all(x["url"].startswith("/") for x in links)
    assert any("health-change-and-pain-triage" in x["url"] for x in links)
    assert any("medication-safety-and-care-transition-plan" in x["url"] for x in links)
    assert any("sleep-routine-observation-and-support-plan" in x["url"] for x in links)
    assert any("communication-passport-and-accessible-information-plan" in x["url"] for x in links)


def test_original_arabic_content_not_placeholder():
    text = CONTENT.read_text(encoding="utf-8")
    assert len(text) > 18000
    banned = ["Lorem ipsum", "TODO", "PLACEHOLDER", "baseline content"]
    assert not any(x in text for x in banned)
    assert text.count("النوبة") >= 30
    assert text.count("الخطة") >= 15
    assert text.count("الطوارئ") >= 10
