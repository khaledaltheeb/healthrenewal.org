import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "learning-paths/self-advocacy/content-extension.json"


def load_extension():
    return json.loads(EXTENSION.read_text(encoding="utf-8"))


def test_metadata_and_review_contract():
    data = load_extension()

    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] > data["verified_at"]
    assert {"Article", "FAQPage", "HowTo"}.issubset(data["schema_types"])
    assert len(data["professional_limits"]) >= 300


def test_scenarios_are_specific_and_actionable():
    data = load_extension()
    scenarios = data["decision_scenarios"]

    assert len(scenarios) >= 5
    assert len({item["id"] for item in scenarios}) == len(scenarios)

    for scenario in scenarios:
        assert len(scenario["title"]) >= 12
        assert len(scenario["situation"]) >= 80
        assert len(scenario["questions"]) >= 3
        assert all(len(question) >= 45 for question in scenario["questions"])
        assert len(scenario["safe_action"]) >= 100
        assert len(scenario["measure"]) >= 70
        assert len(scenario["escalation"]) >= 80

    joined = " ".join(
        " ".join(
            [
                item["title"],
                item["situation"],
                *item["questions"],
                item["safe_action"],
                item["measure"],
                item["escalation"],
            ]
        )
        for item in scenarios
    )
    for term in [
        "التيسير",
        "الرفض",
        "التظلم",
        "تضارب المصالح",
        "وسيلة التواصل",
        "الحماية",
    ]:
        assert term in joined


def test_practice_questions_and_faq_cover_decision_safeguards():
    data = load_extension()

    assert len(data["practice_questions"]) >= 8
    assert all(len(question) >= 55 for question in data["practice_questions"])
    assert len(data["faq"]) >= 4
    assert all(len(item["question"]) >= 20 for item in data["faq"])
    assert all(len(item["answer"]) >= 80 for item in data["faq"])

    joined = " ".join(data["practice_questions"])
    for term in ["القرار", "الرفض", "البدائل", "تضارب المصالح", "التظلم"]:
        assert term in joined


def test_internal_links_are_site_local_and_descriptive():
    links = load_extension()["internal_links"]

    assert len(links) >= 4
    for link in links:
        parsed = urlparse(link["href"])
        assert not parsed.scheme
        assert not parsed.netloc
        assert link["href"].startswith("/")
        assert link["href"].endswith("/")
        assert len(link["label"]) >= 8
        assert len(link["purpose"]) >= 35


def test_source_log_uses_official_sources_and_original_summary_rights():
    sources = load_extension()["source_log"]

    assert len(sources) >= 3
    allowed_hosts = {"www.ohchr.org", "www.who.int"}
    allowed_types = {
        "official_human_rights_interpretation",
        "official_technical_guidance",
        "official_easy_read_guidance",
    }

    for source in sources:
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https"
        assert parsed.netloc in allowed_hosts
        assert source["source_type"] in allowed_types
        assert source["verified_at"] == "2026-08-06"
        assert len(source["claims_supported"]) >= 3
        assert source["rights"] == "link-cite-and-original-summary-only"


def test_no_partnership_claim_or_restricted_term():
    data = load_extension()
    text = EXTENSION.read_text(encoding="utf-8")
    non_claims = " ".join(data["non_claims"])

    assert "لا توجد شراكة" in non_claims
    assert "لا تقرر الأهلية القانونية" in non_claims
    assert "لا تبرر الإكراه" in non_claims
    assert "معاقين" not in text
