from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
POPULATIONS = (
    "adolescents-young-adults","pregnancy-postpartum","older-adults",
    "co-occurring-mental-health","chronic-pain","disability-special-needs",
)
TOOLS = (
    "family-first-conversation-plan","family-boundaries-plan",
    "overdose-emergency-plan","lapse-relapse-response-plan",
    "treatment-provider-checklist","discharge-follow-up-plan",
)
BANNED = (
    "جرعة:", " ملغ", " mg ", "تناول حبة", "خفض الجرعة بنسبة",
    "علاج مضمون", "شفاء مضمون", "انسحاب منزلي آمن للجميع",
)
NS = {"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}

def test_population_guides_contract():
    combined = []
    for slug in POPULATIONS:
        path = ROOT / "addiction" / "populations" / slug / "index.html"
        assert path.is_file(), slug
        text = path.read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in text
        assert '<link rel="canonical"' in text
        assert 'type="application/ld+json"' in text
        assert "<h1>" in text and "الطوارئ أولًا" in text
        assert text.count('class="protocol"') == 10, slug
        assert "للأسرة ومقدم الرعاية" in text
        assert "المراجع المحورية" in text
        combined.append(text)
    joined = "\n".join(combined)
    assert not [term for term in BANNED if term in joined]

def test_practical_tools_contract():
    combined = []
    for slug in TOOLS:
        path = ROOT / "addiction" / "tools" / slug / "index.html"
        assert path.is_file(), slug
        text = path.read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in text
        assert '<link rel="canonical"' in text
        assert 'type="application/ld+json"' in text
        assert "حدود الأداة" in text and "نموذج التعبئة" in text
        assert text.count('class="step"') == 10, slug
        assert "طباعة الأداة" in text
        combined.append(text)
    joined = "\n".join(combined)
    assert not [term for term in BANNED if term in joined]

def test_evidence_traceability_contract():
    base_registry = json.loads((ROOT/"data/addiction-evidence/source-registry.json").read_text(encoding="utf-8"))
    supplement = json.loads((ROOT/"data/addiction-evidence/source-registry-wave-cde-v1.json").read_text(encoding="utf-8"))
    claim_map = json.loads((ROOT/"data/addiction-evidence/claim-source-map-v2.json").read_text(encoding="utf-8"))
    source_ids = {x["id"] for x in base_registry["sources"]} | {x["id"] for x in supplement["sources"]}
    assert len(supplement["sources"]) >= 8
    assert len(claim_map["claims"]) >= 18
    assert claim_map["coverage"]["unmapped_high_risk_claims"] == 0
    for claim in claim_map["claims"]:
        assert claim["source_ids"]
        assert set(claim["source_ids"]) <= source_ids, claim["id"]
        assert claim["affected_routes"]
        assert claim["confidence"] in {"moderate","moderate-high","high"}

def test_discovery_and_report_contract():
    tree = ET.parse(ROOT/"sitemap-addiction.xml").getroot()
    urls = [n.text for n in tree.findall("s:url/s:loc", NS)]
    assert len(urls) == len(set(urls))
    for slug in POPULATIONS:
        assert f"https://healthrenewal.org/addiction/populations/{slug}/" in urls
    for slug in TOOLS:
        assert f"https://healthrenewal.org/addiction/tools/{slug}/" in urls
    assert "https://healthrenewal.org/addiction/populations/" in urls
    assert "https://healthrenewal.org/addiction/tools/" in urls
    report = json.loads((ROOT/"api/addiction-expansion-wave-cde-v1.json").read_text(encoding="utf-8"))
    assert report["populationGuides"] == 6
    assert report["practicalTools"] == 6
    assert report["claimCount"] >= 18
    assert report["safety"]["hiddenPayload"] is False
    assert report["safety"]["selfWritingWorkflow"] is False
