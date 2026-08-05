import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "family-guide/assistive-technology-selection/index.html"
RECORD = ROOT / "data/institutional-resources/pacer-assistive-technology.json"


def test_page_and_rights_record_exist() -> None:
    assert PAGE.is_file()
    assert RECORD.is_file()


def test_rights_record_is_complete_and_conservative() -> None:
    data = json.loads(RECORD.read_text(encoding="utf-8"))
    assert data["organization"] == "PACER Center"
    assert data["rights_classification"] == "translation-permitted"
    assert data["verified_at"] == "2026-08-05"
    assert data["next_review_due"] > data["verified_at"]
    assert data["review_status"] == "internal-editorial-review"
    assert "No partnership" in data["relationship_disclosure"]
    prohibited = " ".join(data["prohibited_uses"]).lower()
    for term in ("logo", "partnership", "minnesota", "copying"):
        assert term in prohibited
    assert all(url.startswith("https://www.pacer.org/") for url in data["official_urls"])


def test_page_has_required_metadata_schema_and_arabic_contract() -> None:
    html = PAGE.read_text(encoding="utf-8")
    required = (
        '<html lang="ar" dir="rtl">',
        '<link rel="canonical" href="https://healthrenewal.org/family-guide/assistive-technology-selection/">',
        'type="application/ld+json"',
        '"@type":"HowTo"',
        'id="main-content"',
        '@media print',
        'prefers-reduced-motion:reduce',
        'PACER Center',
        'لا توجد شراكة أو مصادقة أو مراجعة خارجية',
        'Minnesota',
        '/verified-resources/',
        '/family-guide/',
    )
    for token in required:
        assert token in html
    assert html.count("<h1>") == 1
    assert len(re.findall(r"<h2", html)) >= 7
    assert len(re.findall(r"<li>", html)) >= 25


def test_page_avoids_high_risk_or_misleading_claims() -> None:
    html = PAGE.read_text(encoding="utf-8")
    forbidden = (
        "شريك PACER",
        "معتمد من PACER",
        "مراجعة PACER",
        "أفضل جهاز",
        "مضمون النتائج",
        "يستبدل التقييم",
        "شعار PACER",
    )
    for phrase in forbidden:
        assert phrase not in html
    assert "لا تستبدل تقييم" in html
    assert "لا تعدّل كرسيًا متحركًا" in html


def test_external_links_are_secure_and_no_pacer_assets_are_embedded() -> None:
    html = PAGE.read_text(encoding="utf-8")
    external = re.findall(r'href="(https?://[^"]+)"', html)
    assert external
    assert all(url.startswith("https://") for url in external)
    assert not re.search(r'<img[^>]+(?:pacer|pacer\.org)', html, re.IGNORECASE)
