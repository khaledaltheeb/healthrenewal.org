import json
from pathlib import Path

CONTENT = Path("learning-paths/caregiver-foundations/heat-hydration-and-temperature-safety-plan.json")


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
    assert len(d["heat_log_fields"]) >= 14
    assert len(d["decision_matrix"]) >= 4
    assert len(d["red_flags"]) >= 12
    assert len(d["weekly_review"]) >= 12
    assert len(d["faq"]) >= 8


def test_safety_boundaries_are_explicit():
    text = json.dumps(load(), ensure_ascii=False)
    for phrase in [
        "لا تشخّص الجفاف",
        "لا توقف دواء",
        "لا تُلغِ تقييد السوائل",
        "لا تُجبر شخصًا لديه مشكلة بلع",
        "خدمات الطوارئ المحلية",
        "لا تترك الأدوية أو الأجهزة في سيارة ساخنة",
        "لا تمنع وسيلة تواصل",
        "لا تعني شراكة أو اعتمادًا",
    ]:
        assert phrase in text


def test_sources_are_official_current_and_scope_limited():
    d = load()
    assert len(d["sources"]) >= 7
    urls = [s["url"] for s in d["sources"]]
    assert sum("who.int" in u for u in urls) >= 2
    assert sum("cdc.gov" in u for u in urls) >= 2
    assert sum("nice.org.uk" in u for u in urls) >= 2
    assert any("pubmed.ncbi.nlm.nih.gov" in u for u in urls)
    assert all(u.startswith("https://") for u in urls)
    nice = [s for s in d["sources"] if "nice.org.uk" in s["url"]]
    assert all("المملكة المتحدة" in s["scope"] for s in nice)
    assert any(s["date"].startswith("2026") for s in d["sources"])


def test_internal_links_connect_related_packages():
    links = load()["internal_links"]
    assert len(links) >= 7
    assert all(x["url"].startswith("/") for x in links)
    assert any("medication-safety" in x["url"] for x in links)
    assert any("eating-drinking-swallowing" in x["url"] for x in links)
    assert any("health-change-and-pain-triage" in x["url"] for x in links)
    assert any("communication-passport" in x["url"] for x in links)


def test_original_arabic_content_not_placeholder():
    text = CONTENT.read_text(encoding="utf-8")
    assert len(text) > 20000
    banned = ["Lorem ipsum", "TODO", "PLACEHOLDER", "baseline content"]
    assert not any(x in text for x in banned)
    assert text.count("الحر") >= 35
    assert text.count("السوائل") >= 15
    assert text.count("الأدوية") >= 15
