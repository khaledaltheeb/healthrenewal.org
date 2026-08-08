import json
from pathlib import Path

CONTENT = Path("learning-paths/caregiver-foundations/emotional-distress-behavior-change-and-deescalation-support-plan.json")


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
    assert len(d["care_plan_fields"]) >= 12
    assert len(d["decision_matrix"]) >= 4
    assert len(d["red_flags"]) >= 12
    assert len(d["weekly_review"]) >= 10
    assert len(d["professional_boundaries"]) >= 8
    assert len(d["faq"]) >= 8


def test_deescalation_and_professional_boundaries_are_explicit():
    text = json.dumps(load(), ensure_ascii=False)
    for phrase in [
        "السلوك الملاحظ معلومة وليس تشخيصًا",
        "لا تشخيص منزلي",
        "لا استخدام التقييد الجسدي",
        "خدمات الطوارئ المحلية",
        "وسيلة التواصل",
        "لا تعني شراكة أو اعتمادًا",
    ]:
        assert phrase in text


def test_sources_are_official_and_scoped():
    d = load()
    assert len(d["sources"]) >= 6
    urls = [s["url"] for s in d["sources"]]
    assert sum("who.int" in u for u in urls) >= 2
    assert sum("nice.org.uk" in u for u in urls) >= 2
    assert all(s.get("scope_note") for s in d["sources"])
    assert all(u.startswith("https://") for u in urls)
    assert any("قيد التطوير" in s["type"] for s in d["sources"])


def test_internal_links_connect_health_communication_and_sensory_paths():
    d = load()
    links = d["internal_links"]
    assert len(links) >= 6
    assert all(x["url"].startswith("/") for x in links)
    assert any("health-change-and-pain-triage" in x["url"] for x in links)
    assert any("communication-passport" in x["url"] for x in links)
    assert any("sensory-environment" in x["url"] for x in links)
    assert any("medication-safety" in x["url"] for x in links)


def test_original_arabic_content_not_placeholder():
    text = CONTENT.read_text(encoding="utf-8")
    assert len(text) > 15000
    banned = ["Lorem ipsum", "TODO", "PLACEHOLDER", "baseline content"]
    assert not any(x in text for x in banned)
    assert text.count("الضيق") >= 12
    assert text.count("التقييد") >= 6
    assert text.count("التواصل") >= 10
