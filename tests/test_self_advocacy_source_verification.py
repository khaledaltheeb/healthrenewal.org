import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "learning-paths/self-advocacy/index.html"
RECORD = ROOT / "learning-paths/self-advocacy/source-verification.json"


def load_record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_page_and_governance_contract():
    data = load_record()
    html = PAGE.read_text(encoding="utf-8")

    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] > data["verified_at"]
    assert len(data["professional_limits"]) >= 250

    assert '<html lang="ar" dir="rtl">' in html or '<html lang="ar" dir="rtl"' in html
    assert '<link rel="canonical" href="https://healthrenewal.org/learning-paths/self-advocacy/">' in html
    assert "<h1>مسار المناصرة الذاتية واتخاذ القرار</h1>" in html
    assert "@media print" in html or "platform-core.css" in html
    assert "المراجعة الخارجية المتخصصة موصى بها" in html


def test_claims_resolve_to_current_sources():
    data = load_record()
    sources = {source["id"]: source for source in data["sources"]}

    assert len(data["editorial_claims"]) >= 4
    assert len(data["practice_questions"]) >= 8
    assert len(data["editorial_findings"]) >= 2

    for claim in data["editorial_claims"]:
        assert len(claim["claim"]) >= 80
        assert claim["source_ids"]
        assert set(claim["source_ids"]).issubset(sources)

    allowed_types = {
        "official_human_rights_interpretation",
        "official_technical_guidance",
        "official_fact_sheet",
    }
    for source in sources.values():
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https"
        assert parsed.netloc in {"www.ohchr.org", "www.who.int"}
        assert source["source_type"] in allowed_types
        assert source["verified_at"] == data["verified_at"]
        assert source["claims_supported"]
        assert source["rights"] == "link-cite-and-original-summary-only"


def test_decision_support_workflow_is_actionable():
    data = load_record()
    workflow = data["decision_support_workflow"]

    assert len(workflow) >= 6
    assert [item["step"] for item in workflow] == list(range(1, len(workflow) + 1))
    assert all(len(item["title"]) >= 8 for item in workflow)
    assert all(len(item["practice"]) >= 80 for item in workflow)

    joined = " ".join(item["practice"] for item in workflow)
    for term in ["الرفض", "التواصل", "البدائل", "تضارب المصالح", "التظلم"]:
        assert term in joined


def test_accessibility_findings_block_merge_until_remediated():
    audit = load_record()["semantic_accessibility_audit"]

    assert audit["status"] == "remediation-required-before-merge"
    assert {"section-labeling", "skip-link", "keyboard", "rtl", "mobile", "print"}.issubset(audit["scope"])
    assert len(audit["confirmed_findings"]) >= 2
    assert all(item["merge_blocking"] is True for item in audit["confirmed_findings"])
    assert any(item["ownership"] == "page-local" for item in audit["confirmed_findings"])
    assert any(item["ownership"] == "shared-css" for item in audit["confirmed_findings"])
    assert audit["unconfirmed_findings"]


def test_rights_and_safeguarding_limits_are_explicit():
    data = load_record()
    joined = " ".join(data["non_claims"] + [data["professional_limits"]])

    required_terms = [
        "لا توجد شراكة",
        "لا يقرر",
        "لا يبرر الإكراه",
        "وسيلة التواصل",
        "القانون المحلي",
    ]
    for term in required_terms:
        assert term in joined


def test_no_restricted_or_stigmatizing_term():
    text = RECORD.read_text(encoding="utf-8") + PAGE.read_text(encoding="utf-8")
    assert "معاقين" not in text
