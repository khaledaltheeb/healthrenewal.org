from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
POPULATIONS = (
    "homelessness-housing-instability",
    "justice-reentry",
    "refugees-displacement-complex-trauma",
    "injection-related-infections-integrated-care",
    "complex-medical-conditions",
    "rural-remote-limited-resources",
)
EMERGING = (
    "caffeine-excessive-use-withdrawal",
    "psychedelic-hallucinogen-related-harms",
    "dissociative-drug-related-harms",
    "anabolic-steroid-performance-drug-misuse",
    "prescription-medicine-misuse",
    "compulsive-sexual-behaviour",
    "problematic-internet-social-media-use",
    "compulsive-buying-financial-behaviour",
)
BANNED = (
    r"\b\d+(?:\.\d+)?\s*(?:mg|ملغ|مغ)\b",
    r"خفض الجرعة بنسبة",
    r"تناول حبة",
    r"شفاء مضمون",
    r"انسحاب منزلي آمن للجميع",
    r"علاج ما بعد الدورة.{0,30}(?:جرعة|جدول)",
)
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_v4_pages_are_structured_indexable_and_bounded():
    combined = []
    for section, slugs in (("populations", POPULATIONS), ("emerging", EMERGING)):
        for slug in slugs:
            text = read(f"addiction/{section}/{slug}/index.html")
            assert '<html lang="ar" dir="rtl">' in text
            assert '<meta name="robots" content="index,follow' in text
            assert '<link rel="canonical"' in text
            assert 'application/ld+json' in text
            assert 'data-pt-normalized="1.1.0"' in text
            assert text.count('class="protocol"') == 10, slug
            assert "الطوارئ أولًا" in text
            assert "حالة التصنيف والحدود" in text
            combined.append(text)
    joined = "\n".join(combined)
    for pattern in BANNED:
        assert not re.search(pattern, joined, re.I | re.S), pattern


def test_emerging_pages_state_classification_boundaries():
    csbd = read("addiction/emerging/compulsive-sexual-behaviour/index.html")
    internet = read("addiction/emerging/problematic-internet-social-media-use/index.html")
    buying = read("addiction/emerging/compulsive-buying-financial-behaviour/index.html")
    caffeine = read("addiction/emerging/caffeine-excessive-use-withdrawal/index.html")
    assert "اضطرابات التحكم بالاندفاع" in csbd
    assert "لا توجد فئة عامة واحدة" in internet
    assert "التصنيف كاضطراب مستقل غير موحد" in buying
    assert "لا يعني شرب القهوة المعتاد" in caffeine


def test_v4_evidence_resolves_and_unsettled_claims_require_review():
    registry = json.loads(read("data/addiction-evidence/source-registry-v4.json"))
    mapping = json.loads(read("data/addiction-evidence/claim-source-map-v4.json"))
    source_ids = {item["id"] for item in registry["sources"]}
    assert len(source_ids) == 12
    assert all(item["url"].startswith("https://") for item in registry["sources"])
    assert len(mapping["claims"]) == 28
    assert mapping["coverage"]["unmapped_high_risk_claims"] == 0
    external = 0
    for claim in mapping["claims"]:
        assert claim["source_ids"]
        assert set(claim["source_ids"]) <= source_ids, claim["id"]
        assert claim["affected_routes"]
        assert claim["safety_flags"]
        if claim["publication_status"] == "external-clinical-review-required":
            external += 1
    assert external >= 4


def test_v4_api_and_sitemap_contract():
    api = json.loads(read("api/v1/addiction-center.json"))
    assert api["program_status"] == "expanded-foundation-v4"
    assert api["population_layer_status"] == "complete-v1"
    assert api["emerging_layer_status"] == "complete-v1"
    assert api["population_page_count"] == 13
    assert api["emerging_page_count"] == 9
    assert api["structured_reference_count"] >= 36
    assert api["mapped_claim_count"] >= 70

    root = ET.parse(ROOT / "sitemap-addiction.xml").getroot()
    urls = [node.text for node in root.findall("s:url/s:loc", NS)]
    assert len(urls) == 66
    assert len(urls) == len(set(urls))
    assert "https://healthrenewal.org/addiction/emerging/" in urls
    for slug in POPULATIONS:
        assert f"https://healthrenewal.org/addiction/populations/{slug}/" in urls
    for slug in EMERGING:
        assert f"https://healthrenewal.org/addiction/emerging/{slug}/" in urls


def test_v4_report_is_truthful_and_non_self_writing():
    report = json.loads(read("api/addiction-expansion-v4.json"))
    assert report["newPopulationGuides"] == 6
    assert report["newEmergingGuides"] == 8
    assert report["newStructuredSources"] == 12
    assert report["newMappedClaims"] == 28
    assert report["sitemapRoutes"] == 66
    assert report["safety"]["hiddenPayload"] is False
    assert report["safety"]["selfWritingWorkflow"] is False
