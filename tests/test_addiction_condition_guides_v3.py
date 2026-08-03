from __future__ import annotations
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUGS = (
    "alcohol-use-disorder","opioid-use-disorder","stimulant-use-disorder",
    "cannabis-use-disorder","nicotine-tobacco-dependence",
    "sedative-benzodiazepine-use-disorder","gambling-related-harms",
    "gaming-disorder","inhalant-use-disorder",
    "polysubstance-use-and-overdose-risk",
)
AUDIENCES = ("person","family","trainer","community","clinician")
BANNED = ("جرعة:", "تناول حبة", "خفض الجرعة بنسبة", "اضمن الشفاء", "انسحاب منزلي آمن للجميع")
NS = {"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}

def test_condition_guides_v3_contract() -> None:
    manifest = json.loads((ROOT/"addiction/editorial-manifest-v3.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "3.0.0"
    assert manifest["counts"]["condition_pages"] == 10
    assert manifest["counts"]["protocol_modules"] == 100
    assert manifest["counts"]["audience_pathways"] == 5
    assert manifest["safety"]["individual_dosing"] is False
    combined = []
    for slug in SLUGS:
        path = ROOT/"addiction"/slug/"index.html"
        assert path.is_file(), slug
        text = path.read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in text
        assert "<title>" in text and 'name="description"' in text
        assert 'rel="canonical"' in text and "<h1>" in text
        assert 'type="application/ld+json"' in text
        assert text.count('class="protocol"') == 10, slug
        assert "متى تصبح الحالة طارئة؟" in text
        for audience in AUDIENCES:
            assert f"/addiction/audiences/{audience}/" in text
        combined.append(text)
    joined = "\n".join(combined)
    assert not [x for x in BANNED if x in joined]
    assert not list(ROOT.glob("content/addiction/*.b64"))
    assert not (ROOT/"scripts/materialize_addiction_condition_guides_v2.py").exists()

def test_addiction_hub_and_sitemap_v3() -> None:
    hub = (ROOT/"addiction/index.html").read_text(encoding="utf-8")
    for slug in SLUGS:
        assert f"/addiction/{slug}/" in hub
    for audience in AUDIENCES:
        assert f"/addiction/audiences/{audience}/" in hub
    assert "/addiction/conditions/" in hub
    assert "/addiction/methodology/" in hub
    tree = ET.parse(ROOT/"sitemap-addiction.xml").getroot()
    urls = [n.text for n in tree.findall("s:url/s:loc", NS)]
    assert len(urls) == 24
    assert len(urls) == len(set(urls))
    for slug in SLUGS:
        assert f"https://healthrenewal.org/addiction/{slug}/" in urls
    for audience in AUDIENCES:
        assert f"https://healthrenewal.org/addiction/audiences/{audience}/" in urls
    report = json.loads((ROOT/"api/addiction-condition-guides-v3.json").read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert report["conditionPages"] == 10
    assert report["detailedProtocols"] == 100
    assert report["safety"]["noIndividualDosing"] is True
