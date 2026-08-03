from pathlib import Path
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def test_addiction_core_pages_exist_and_are_indexable():
    expected = [
        ROOT / "addiction" / "index.html",
        ROOT / "addiction" / "protocol-atlas" / "index.html",
        ROOT / "addiction" / "withdrawal-safety" / "index.html",
        ROOT / "addiction" / "recovery-roadmap" / "index.html",
        ROOT / "addiction" / "family-guide" / "index.html",
        ROOT / "addiction" / "sources" / "index.html",
    ]
    for page in expected:
        assert page.exists(), page
        text = page.read_text(encoding="utf-8")
        assert '<html lang="ar" dir="rtl">' in text
        assert '<link rel="canonical"' in text
        assert 'name="robots" content="index,follow' in text
        assert "platform-core.css" in text


def test_protocol_atlas_contains_exactly_one_hundred_protocols():
    text = (ROOT / "addiction" / "protocol-atlas" / "index.html").read_text(encoding="utf-8")
    assert text.count('class="protocol"') == 100
    for anchor in [
        "alcohol", "opioids", "stimulants", "cannabis", "sedatives",
        "nicotine", "gambling", "gaming", "inhalants", "poly",
    ]:
        assert f'id="{anchor}"' in text


def test_machine_readable_index_matches_atlas_contract():
    data = json.loads((ROOT / "api" / "v1" / "addiction-center.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "addiction-center-v1"
    assert data["protocol_total"] == 100
    assert data["reference_count"] >= 50
    assert len(data["condition_groups"]) == 10
    assert len(data["core_pages"]) == 6
    assert all(item["protocol_count"] == 10 for item in data["condition_groups"])
    assert (ROOT / data["governance_document"]).exists()


def test_addiction_sitemap_and_index_are_valid():
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    sitemap_root = ET.parse(ROOT / "sitemap-addiction.xml").getroot()
    locs = [node.text for node in sitemap_root.findall("s:url/s:loc", ns)]
    assert len(locs) == 6
    assert len(locs) == len(set(locs))
    assert all(url.startswith("https://healthrenewal.org/addiction/") for url in locs)
    assert "https://healthrenewal.org/addiction/family-guide/" in locs

    index_root = ET.parse(ROOT / "sitemap-index.xml").getroot()
    sitemap_locs = [node.text for node in index_root.findall("s:sitemap/s:loc", ns)]
    assert "https://healthrenewal.org/sitemap-addiction.xml" in sitemap_locs


def test_medical_safety_guardrails():
    forbidden = [
        "علاج مضمون",
        "شفاء مضمون",
        "أوقف الدواء فورًا",
        "جدول جرعات ذاتي",
        "لا حاجة للطبيب",
    ]
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "addiction").glob("**/index.html")
    )
    assert "تنبيه طبي" in combined or "تثقيف" in combined
    assert not any(term in combined for term in forbidden)
    assert "لا يوقف الكحول أو البنزوديازيبين" in combined
    assert "الديتوكس" in combined or "إزالة السموم" in combined


def test_sources_registry_has_at_least_fifty_entries():
    text = (ROOT / "addiction" / "sources" / "index.html").read_text(encoding="utf-8")
    assert text.count('class="source"') >= 50
    for authority in ["WHO", "UNODC", "SAMHSA", "NIDA", "ASAM", "NICE", "CDC", "VA/DoD"]:
        assert authority in text


def test_editorial_governance_defines_five_roles():
    text = (ROOT / "docs" / "addiction-editorial-governance.md").read_text(encoding="utf-8")
    for role in [
        "باحث الأدلة والمراجع",
        "منسق هندسة المعرفة",
        "مراجع السلامة السريرية",
        "المحرر العربي وإزالة الوصمة",
        "مسؤول SEO والنشر والاكتشاف الآلي",
    ]:
        assert role in text
