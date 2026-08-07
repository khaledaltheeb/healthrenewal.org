import json
from pathlib import Path

CONTENT = Path("learning-paths/caregiver-foundations/skin-integrity-pressure-moisture-support-plan.json")


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
    assert len(d["principles"]) >= 12
    assert len(d["stages"]) >= 8
    assert sum(len(x["questions"]) for x in d["stages"]) >= 48
    assert len(d["skin_log_fields"]) >= 14
    assert len(d["decision_matrix"]) >= 4
    assert len(d["red_flags"]) >= 12
    assert len(d["weekly_review"]) >= 12
    assert len(d["faq"]) >= 8


def test_safety_boundaries_are_explicit():
    text = json.dumps(load(), ensure_ascii=False)
    for phrase in [
        "لا تشخيص منزلي لقرحة الضغط",
        "لا تستخدم التدليك أو الفرك",
        "لا تبدأ مضادًا حيويًا",
        "لا تحاول إزالة نسيج ميت",
        "لا تُجبر الشخص على تغيير الوضعية بالقوة",
        "خدمات الطوارئ المحلية",
        "لا تعني شراكة أو اعتمادًا",
    ]:
        assert phrase in text


def test_sources_are_current_official_and_scope_limited():
    d = load()
    assert len(d["sources"]) >= 6
    urls = [s["url"] for s in d["sources"]]
    assert sum("nice.org.uk" in u for u in urls) >= 3
    assert any("who.int" in u for u in urls)
    assert sum("pubmed.ncbi.nlm.nih.gov" in u for u in urls) >= 2
    assert all(u.startswith("https://") for u in urls)
    nice = [s for s in d["sources"] if "nice.org.uk" in s["url"]]
    assert any("المملكة المتحدة" in s["scope"] for s in nice)
    assert any(s["date"].startswith("2026") for s in d["sources"])


def test_internal_links_connect_related_caregiver_packages():
    links = load()["internal_links"]
    assert len(links) >= 7
    assert all(x["url"].startswith("/") for x in links)
    assert any("mobility-transfer-and-fall" in x["url"] for x in links)
    assert any("bowel-bladder-toileting" in x["url"] for x in links)
    assert any("health-change-and-pain-triage" in x["url"] for x in links)
    assert any("communication-passport" in x["url"] for x in links)


def test_original_arabic_content_not_placeholder():
    text = CONTENT.read_text(encoding="utf-8")
    assert len(text) > 20000
    banned = ["Lorem ipsum", "TODO", "PLACEHOLDER", "baseline content"]
    assert not any(x in text for x in banned)
    assert text.count("الجلد") >= 35
    assert text.count("الضغط") >= 30
    assert text.count("الخطة") >= 10
