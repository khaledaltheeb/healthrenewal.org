from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SLUGS = (
    "alcohol-use-disorder",
    "opioid-use-disorder",
    "stimulant-use-disorder",
    "cannabis-use-disorder",
    "nicotine-tobacco-dependence",
    "sedative-benzodiazepine-use-disorder",
    "gambling-related-harms",
    "gaming-disorder",
    "inhalant-use-disorder",
    "polysubstance-use-and-overdose-risk",
)

def test_condition_guides_are_visible_complete_and_safe():
    manifest = json.loads((ROOT / "addiction/editorial-manifest-v3.json").read_text(encoding="utf-8"))
    assert manifest["condition_count"] == 10
    assert manifest["protocol_total"] == 100
    assert manifest["safety"]["individual_doses"] is False
    forbidden = (" mg ", " ملغ", "جرعة:", "خفض الجرعة بنسبة", "أوقف الدواء فورًا")
    for slug in SLUGS:
        path = ROOT / "addiction" / slug / "index.html"
        assert path.is_file(), path
        text = path.read_text(encoding="utf-8")
        for marker in ('<html lang="ar" dir="rtl">', '<link rel="canonical"', '<h1>', "الطوارئ أولًا", "عشرة مسارات رعاية مترابطة", "دور الأسرة", "المراجع المحورية"):
            assert marker in text, (path, marker)
        assert text.count("<li><strong>") == 10, path
        assert not any(term in text for term in forbidden), path

def test_condition_discovery_contract():
    index = (ROOT / "addiction/conditions/index.html").read_text(encoding="utf-8")
    for slug in SLUGS:
        assert f'/addiction/{slug}/' in index
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(ROOT / "sitemap-addiction.xml").getroot()
    urls = [node.text for node in root.findall("s:url/s:loc", ns)]
    assert len(urls) == len(set(urls))
    for slug in SLUGS:
        assert f"https://healthrenewal.org/addiction/{slug}/" in urls
    assert "https://healthrenewal.org/addiction/conditions/" in urls
    assert "https://healthrenewal.org/addiction/methodology/" in urls
    report = json.loads((ROOT / "api/addiction-condition-guides-v3.json").read_text(encoding="utf-8"))
    assert report == {
        "schemaVersion": 3,
        "status": "generated",
        "conditionPages": 10,
        "protocolTotal": 100,
        "visibleStaticFiles": True,
        "hiddenPayload": False,
        "selfWritingWorkflow": False,
    }
