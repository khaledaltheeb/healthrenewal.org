from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
AUDIENCE_ROUTES = {
    "gateway": "addiction/audiences/index.html",
    "person": "addiction/audiences/person/index.html",
    "family": "addiction/audiences/family/index.html",
    "trainer": "addiction/audiences/trainer/index.html",
    "community": "addiction/audiences/community/index.html",
    "clinician": "addiction/audiences/clinician/index.html",
}
BASE_URL = "https://healthrenewal.org/"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_all_audience_pages_are_static_arabic_and_indexable():
    for key, path in AUDIENCE_ROUTES.items():
        html = read(path)
        assert '<html lang="ar" dir="rtl">' in html, (key, "rtl")
        assert html.count("<h1") == 1, (key, "h1")
        assert '<meta name="description"' in html, (key, "description")
        assert '<meta name="robots" content="index,follow' in html, (key, "robots")
        expected = BASE_URL + path.removesuffix("index.html")
        assert f'<link rel="canonical" href="{expected}">' in html, (key, "canonical")
        assert 'application/ld+json' in html, (key, "schema")
        assert '/assets/addiction/audience-hubs.css?v=1.0.0' in html, (key, "css")


def test_gateway_links_every_role_with_visible_html_cards():
    gateway = read(AUDIENCE_ROUTES["gateway"])
    for role in ("person", "family", "trainer", "community", "clinician"):
        route = f'/addiction/audiences/{role}/'
        assert route in gateway, role
        assert re.search(r'<article class="card">.*?' + re.escape(route), gateway, re.S), role
    assert 'numberOfItems":5' in gateway


def test_center_links_gateway_and_all_five_audiences():
    center = read("addiction/index.html")
    for suffix in ("", "person/", "family/", "trainer/", "community/", "clinician/"):
        assert f'/addiction/audiences/{suffix}' in center, suffix
    assert "5 مسارات جمهور" in center


def test_high_risk_pages_include_emergency_boundaries():
    common_markers = ("الاختلاجات", "الانتحار", "الطوارئ")
    for role in ("person", "family", "clinician"):
        html = read(AUDIENCE_ROUTES[role])
        for marker in common_markers:
            assert marker in html, (role, marker)
    person = read(AUDIENCE_ROUTES["person"])
    family = read(AUDIENCE_ROUTES["family"])
    clinician = read(AUDIENCE_ROUTES["clinician"])
    assert "صعوبة التنفس" in person
    assert "صعوبة التنفس" in family
    assert "صعوبة التنفس" in clinician or "تثبيط التنفس" in clinician
    assert "لا توقف الكحول أو البنزوديازيبينات فجأة" in person
    assert "لا تحاول احتجاز شخص عنيف" in family


def test_trainer_page_enforces_non_clinical_scope():
    html = read(AUDIENCE_ROUTES["trainer"])
    for marker in ("لا يشخّص", "لا يصف دواءً", "لا يدير انسحابًا", "الإحالة الدافئة", "الإشراف"):
        assert marker in html, marker


def test_community_and_clinician_pages_cover_institutional_quality():
    community = read(AUDIENCE_ROUTES["community"])
    clinician = read(AUDIENCE_ROUTES["clinician"])
    for marker in ("البيانات والإنذار المبكر", "خفض الضرر", "المدرسة والجامعة", "مكان العمل", "الإعلام المسؤول"):
        assert marker in community, marker
    for marker in ("التقييم الأولي متعدد المجالات", "اختيار مستوى الرعاية", "العلاج الدوائي", "الأمراض المصاحبة", "تدقيق جودة الخدمة"):
        assert marker in clinician, marker


def test_forbidden_self_dosing_patterns_are_absent():
    forbidden = (
        r"\b\d+(?:\.\d+)?\s*(?:mg|ملغ|مغ)\b",
        r"اخفض.{0,20}\d+\s*%",
        r"جدول خفض.{0,40}\d+",
        r"جرعة منزلية",
        r"انسحاب منزلي آمن للجميع",
        r"شفاء مضمون",
    )
    for key, path in AUDIENCE_ROUTES.items():
        html = read(path)
        for pattern in forbidden:
            assert not re.search(pattern, html, re.I | re.S), (key, pattern)


def test_sitemap_contains_all_audience_routes_without_duplicates():
    tree = ET.parse(ROOT / "sitemap-addiction.xml")
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [node.text for node in tree.findall("s:url/s:loc", ns)]
    assert len(locs) == len(set(locs))
    for path in AUDIENCE_ROUTES.values():
        assert BASE_URL + path.removesuffix("index.html") in locs


def test_api_exposes_five_distinct_audiences_and_gateway():
    data = json.loads(read("api/v1/addiction-center.json"))
    assert data["audience_gateway"] == BASE_URL + "addiction/audiences/"
    assert data["audience_page_count"] == 6
    audiences = data["audiences"]
    assert len(audiences) == 5
    ids = [item["id"] for item in audiences]
    assert ids == ["person", "family", "trainer", "community", "clinician"]
    assert len({item["route"] for item in audiences}) == 5
    assert data["program_status"] in {
        "foundation-draft", "expanded-foundation-v2", "expanded-foundation-v3"
    }
    assert "لا يمثل اكتمال" in data["publication_claim"]
    assert data["audience_layer_status"] == "complete-v1"
