from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
GUIDES = (
    "children-siblings-safety", "violence-coercion-safety",
    "financial-debt-protection", "treatment-engagement-without-coercion",
    "post-overdose-discharge-support", "family-recovery-caregiver-wellbeing",
)
TOOLS = (
    "child-safety-trusted-adult-plan", "family-financial-exposure-map",
    "medication-household-safety-inventory", "family-treatment-communication-log",
    "family-30-90-day-support-agreement", "caregiver-wellbeing-plan",
)
BANNED = (
    r"\b\d+(?:\.\d+)?\s*(?:mg|ملغ|مغ)\b", r"خفض الجرعة بنسبة",
    r"تناول حبة", r"شفاء مضمون", r"احتجزه حتى", r"اضربه",
    r"الطفل مسؤول عن", r"انسحاب منزلي آمن للجميع",
)
NS = {"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}


def test_family_guides_are_safe_and_structured():
    combined = []
    for slug in GUIDES:
        path = ROOT/"addiction"/"family-guides"/slug/"index.html"
        assert path.is_file(), slug
        text = path.read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in text
        assert '<link rel="canonical"' in text
        assert 'type="application/ld+json"' in text
        assert "<h1>" in text and "المراجع المحورية" in text
        assert text.count('class="protocol"') == 10, slug
        combined.append(text)
    joined = "\n".join(combined)
    for pattern in BANNED:
        assert not re.search(pattern, joined, re.I | re.S), pattern
    assert "الإدمان قد يزيد الخطر لكنه لا يبرر" in joined
    assert "الطفل ليس مراقبًا" in joined


def test_new_family_tools_are_printable_and_bounded():
    combined = []
    for slug in TOOLS:
        path = ROOT/"addiction"/"tools"/slug/"index.html"
        assert path.is_file(), slug
        text = path.read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in text
        assert '<link rel="canonical"' in text
        assert '"@type":"HowTo"' in text
        assert "حدود الأداة" in text and "نموذج التعبئة" in text
        assert text.count('class="step"') == 10, slug
        assert "طباعة الأداة" in text
        combined.append(text)
    joined = "\n".join(combined)
    for pattern in BANNED:
        assert not re.search(pattern, joined, re.I | re.S), pattern


def test_family_evidence_map_resolves_all_sources():
    registries = (
        "data/addiction-evidence/source-registry.json",
        "data/addiction-evidence/source-registry-wave-cde-v1.json",
        "data/addiction-evidence/source-registry-family-v2.json",
    )
    source_ids = set()
    for relative in registries:
        data = json.loads((ROOT/relative).read_text(encoding="utf-8"))
        source_ids.update(item["id"] for item in data["sources"])
    mapping = json.loads((ROOT/"data/addiction-evidence/claim-source-map-family-v2.json").read_text(encoding="utf-8"))
    assert len(mapping["claims"]) == 12
    assert mapping["coverage"]["unmapped_high_risk_claims"] == 0
    for claim in mapping["claims"]:
        assert claim["source_ids"]
        assert set(claim["source_ids"]) <= source_ids, claim["id"]
        assert claim["affected_routes"]
        assert claim["confidence"] in {"moderate", "moderate-high", "high"}


def test_family_routes_api_and_sitemap_contract():
    tree = ET.parse(ROOT/"sitemap-addiction.xml").getroot()
    urls = [node.text for node in tree.findall("s:url/s:loc", NS)]
    assert len(urls) >= 51
    assert len(urls) == len(set(urls))
    assert "https://healthrenewal.org/addiction/family-guides/" in urls
    for slug in GUIDES:
        assert f"https://healthrenewal.org/addiction/family-guides/{slug}/" in urls
    for slug in TOOLS:
        assert f"https://healthrenewal.org/addiction/tools/{slug}/" in urls
    api = json.loads((ROOT/"api/v1/addiction-center.json").read_text(encoding="utf-8"))
    assert api["program_status"] in {"expanded-foundation-v3", "expanded-foundation-v4"}
    assert api["family_specialized_layer_status"] == "complete-v1"
    assert api["tools_layer_status"] == "complete-v1"
    assert api["family_guide_page_count"] == 7
    assert api["tool_page_count"] == 13
    assert api["mapped_claim_count"] >= 42
    report = json.loads((ROOT/"api/addiction-family-specialized-v2.json").read_text(encoding="utf-8"))
    assert report["specializedFamilyGuides"] == 6
    assert report["newTools"] == 6
    assert report["safety"]["hiddenPayload"] is False
