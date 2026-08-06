import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "special-needs/practical/pain-communication/source-verification.json"
PAGE = ROOT / "special-needs/practical/pain-communication/index.html"


def load_record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_record_contract_and_review_dates():
    data = load_record()
    assert data["page"] == "/special-needs/practical/pain-communication/"
    assert data["canonical"] == "https://healthrenewal.org/special-needs/practical/pain-communication/"
    assert data["review_status"] == "internally-reviewed"
    assert data["external_review"] == "recommended-not-completed"
    assert data["verified_at"] == "2026-08-06"
    assert data["next_review_at"] > data["verified_at"]
    assert len(data["professional_limits"]) >= 180


def test_sources_are_official_or_professional_and_https():
    data = load_record()
    allowed_types = {"official_guideline", "professional_organization_resource"}
    allowed_statuses = {"current", "accessible-reference"}
    assert len(data["sources"]) >= 4
    for source in data["sources"]:
        assert source["source_type"] in allowed_types
        assert source["status"] in allowed_statuses
        assert source["verified_at"] == data["verified_at"]
        assert source["claims_supported"]
        assert source["rights"] == "link-and-summarize-only"
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https"
        assert parsed.netloc in {"www.nice.org.uk", "www.iasp-pain.org"}

        if source["id"] == "iasp-pain-communication":
            assert source["status"] == "accessible-reference"
            assert source["year"] is None
            assert source["publication_date"] == "not-displayed-on-source-page"
            assert "2014" in source["notes"]
            assert "limits_of_observation" not in source["claims_supported"]
        else:
            assert source["status"] == "current"
            assert isinstance(source["year"], int)


def test_claims_resolve_to_known_sources():
    data = load_record()
    known = {source["id"] for source in data["sources"]}
    assert len(data["editorial_claims"]) >= 4
    for item in data["editorial_claims"]:
        assert len(item["claim"]) >= 80
        assert item["source_ids"]
        assert set(item["source_ids"]) <= known

    iasp_claim = next(
        item for item in data["editorial_claims"]
        if item["source_ids"] == ["iasp-pain-communication"]
    )
    assert "لا يكفي وحده" not in iasp_claim["claim"]
    assert "السياق الاجتماعي" in iasp_claim["claim"]


def test_practice_questions_and_non_claims_are_substantive():
    data = load_record()
    assert len(data["practice_questions"]) >= 6
    assert all(question.endswith("؟") for question in data["practice_questions"])
    joined = " ".join(data["non_claims"])
    assert "لا توجد شراكة" in joined
    assert "لا يجوز تأخير التقييم العاجل" in joined
    assert "السلوك وحده" in joined


def test_visible_page_matches_canonical_and_professional_boundaries():
    html = PAGE.read_text(encoding="utf-8")
    data = load_record()
    assert f'rel="canonical" href="{data["canonical"]}"' in html
    assert '<html lang="ar" dir="rtl">' in html
    assert html.count("<h1>") == 1
    assert "ليست تشخيصًا فرديًا" in html
    assert "المراجعة الخارجية المتخصصة موصى بها" in html
    assert "@media print" in html
