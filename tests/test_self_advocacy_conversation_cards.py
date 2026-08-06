import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "learning-paths" / "self-advocacy" / "conversation-cards.json"


def load_cards():
    return json.loads(CARDS.read_text(encoding="utf-8"))


def test_cards_metadata_and_review_governance():
    data = load_cards()
    assert data["page"] == "/learning-paths/self-advocacy/"
    assert data["canonical"] == "https://healthrenewal.org/learning-paths/self-advocacy/"
    assert data["language"] == "ar"
    assert data["direction"] == "rtl"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] == "2027-02-06"
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema_types"]))


def test_cards_cover_complete_supported_decision_conversation():
    data = load_cards()
    assert [card["id"] for card in data["cards"]] == [
        "prepare",
        "define-decision",
        "compare-options",
        "express-choice",
        "check-influence",
        "review",
    ]
    for card in data["cards"]:
        assert card["title"].strip()
        assert card["purpose"].strip()
        assert len(card["prompts_for_person"]) >= 4
        assert len(card["prompts_for_supporter"]) >= 3
        assert len(card["record"]) >= 4
        assert card["quality_indicator"].strip()


def test_cards_protect_refusal_access_and_independent_support():
    text = json.dumps(load_cards(), ensure_ascii=False)
    required = [
        "وسيلة التواصل",
        "الرفض",
        "التردد",
        "تغيير رأيه",
        "تضارب المصالح",
        "دعم مستقل",
        "الإكراه",
        "التظلم",
    ]
    for phrase in required:
        assert phrase in text


def test_cards_include_red_flags_faq_and_internal_links():
    data = load_cards()
    assert len(data["red_flags"]) >= 8
    assert len(data["faq"]) >= 4
    for item in data["faq"]:
        assert item["question"].strip()
        assert item["answer"].strip()

    hrefs = [item["href"] for item in data["internal_links"]]
    assert len(hrefs) >= 5
    assert len(hrefs) == len(set(hrefs))
    assert all(href.startswith("/") and href.endswith("/") for href in hrefs)


def test_cards_source_log_is_claim_scoped_and_rights_safe():
    data = load_cards()
    assert len(data["source_log"]) >= 3
    for source in data["source_log"]:
        assert source["title"].strip()
        assert source["publisher"].strip()
        assert source["source_type"].strip()
        assert source["year"] >= 2014
        assert len(source["claims_supported"]) >= 2
        assert source["use"] == "link-cite-and-original-arabic-summary-only"
        assert source["status"] == "current"
        assert source["verified_at"] == "2026-08-06"
        assert source["url"].startswith("https://")

    rights = data["rights"]
    assert rights["copy_policy"] == "original-arabic-synthesis"
    assert rights["restricted_text_copied"] is False
    assert rights["partnership_claimed"] is False
    assert rights["endorsement_claimed"] is False
    assert rights["external_review_claimed"] is False


def test_cards_avoid_stigmatizing_or_overclaiming_language():
    text = CARDS.read_text(encoding="utf-8")
    banned = [
        "المعاقين",
        "المعاق",
        "عديم الأهلية تلقائيًا",
        "معتمد من منظمة الصحة العالمية",
        "شريك للأمم المتحدة",
    ]
    for phrase in banned:
        assert phrase not in text
