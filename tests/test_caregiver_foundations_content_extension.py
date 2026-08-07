import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "learning-paths" / "caregiver-foundations" / "content-extension.json"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def flatten_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from flatten_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from flatten_strings(item)


def test_metadata_and_review_contract():
    data = load_data()
    meta = data["metadata"]
    assert meta["canonical"] == "https://healthrenewal.org/learning-paths/caregiver-foundations/"
    assert meta["language"] == "ar"
    assert meta["direction"] == "rtl"
    assert meta["verified_at"] == "2026-08-07"
    assert meta["next_review"] > meta["verified_at"]
    assert "مراجعة" in meta["review_status"]
    assert {"Article", "HowTo", "FAQPage"}.issubset(set(data["schema"]))


def test_content_is_substantive_and_family_specific():
    data = load_data()
    stages = data["stages"]
    assert len(stages) >= 6
    assert sum(len(stage["questions"]) for stage in stages) >= 30
    assert len(data["principles"]) >= 8
    assert len(data["weekly_review_card"]["fields"]) >= 10
    assert len(data["caregiver_wellbeing"]["questions"]) >= 4
    text = "\n".join(flatten_strings(data))
    for term in ("الأسرة", "الشخص", "التواصل", "المشاركة", "خط أساس", "مقدم الرعاية"):
        assert term in text
    assert len(text) > 9000


def test_person_voice_safety_and_professional_limits_are_explicit():
    data = load_data()
    text = "\n".join(flatten_strings(data))
    for phrase in (
        "صوت الشخص",
        "القبول أو الرفض",
        "لا يشخّص",
        "لا تحدد علاجًا فرديًا",
        "سحب وسيلة تواصل",
        "خطر مباشر",
        "الطوارئ",
        "لا تقدم الصفحة استشارة قانونية",
    ):
        assert phrase in text


def test_internal_links_are_absolute_site_paths_and_core_destinations_exist_in_contract():
    data = load_data()
    links = data["internal_links"]
    assert len(links) >= 4
    hrefs = {item["href"] for item in links}
    assert "/learning-paths/self-advocacy/" in hrefs
    assert "/special-needs/" in hrefs
    assert "/source-registry/" in hrefs
    assert "/trust/" in hrefs
    assert all(href.startswith("/") and ".." not in href for href in hrefs)


def test_source_log_uses_official_sources_with_claim_scopes_and_verification_dates():
    data = load_data()
    sources = data["source_log"]
    assert len(sources) >= 4
    assert sum(1 for s in sources if s["organization"] == "World Health Organization") >= 2
    assert any("UNICEF" in s["organization"] for s in sources)
    for source in sources:
        assert source["url"].startswith("https://")
        assert source["verified_at"] == "2026-08-07"
        assert len(source["claim_scope"]) >= 60
        assert source["type"]


def test_no_unverified_partnership_or_accreditation_claim():
    data = load_data()
    disclosure = data["rights_and_independence"]["no_endorsement"]
    assert "لا توجد شراكة" in disclosure
    assert "اعتماد" in disclosure
    assert "مراجعة خارجية" in disclosure
    text = "\n".join(flatten_strings(data))
    forbidden = ("معتمد من منظمة الصحة العالمية", "بالشراكة مع منظمة الصحة العالمية", "معتمد من اليونيسف")
    assert not any(term in text for term in forbidden)


def test_originality_and_rights_note_present():
    data = load_data()
    rights = data["rights_and_independence"]
    assert "عربي أصلي" in rights["originality"]
    assert "لا تعيد" in rights["source_rights"]
    assert len(data["faq"]) >= 5
