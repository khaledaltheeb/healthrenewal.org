from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
REQUIRED_LINKS = (
    "start-here/", "encyclopedia/", "tips/", "care-guides/", "special-needs/",
    "assessment-lab/", "cognitive-lab/", "sectors/family/", "sectors/child/",
    "sectors/home/", "daily-tools/", "learning-paths/", "provider-assessment-demo/",
    "comparisons/", "library/", "guided-assessment/", "hubs/", "assessments/",
    "cognitive-tests/", "trust/", "partners/", "api/",
)
REQUIRED_FILES = (
    "manifest.webmanifest", "opensearch.xml", "assets/brand/logo-mark.svg",
    "assets/brand/logo.svg", "assets/brand/social-card.svg", "api/index.html",
    "api/v1/platform.json", "api/v1/specialists-partners.json",
    "api/v1/openapi.json", "api/v1/courses.schema.json", "api/v1/courses.example.json",
)
FORBIDDEN_OPERATIONAL_COPY = (
    "خطة نمو قابلة للقياس", "هدف معلن للموسوعة النفسية العربية",
    "هدف أدنى لكل مسار رئيسي", "خط أساس المصدر الحالي",
    "يُحسب العدد من حزمة الإنتاج", "لا نشر قبل البوابات", "قيد الإعداد", "قيد التوسع",
)


class StrictHTMLParser(HTMLParser):
    pass


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    StrictHTMLParser().feed(source)
    assert 'lang="ar"' in source and 'dir="rtl"' in source
    assert BRAND in source
    assert SLOGAN in source
    assert "الاسم المؤسس: مصطلحات علم النفس" in source
    assert "ثلاثين شرحًا" not in source
    assert "2,000+" in source and "200" in source and "16" in source and "93" in source
    assert "data-special-needs-v73" in source
    assert '<a class="btn secondary" href="care-guides/">أدلة التعامل مع الحالات</a>' in source
    for phrase in ("مكتبة المقارنات النفسية", "المكتبة الأكاديمية العربية", "الأدوات النفسية التفاعلية", "مسارات التعلم القصيرة"):
        assert phrase in source
    assert source.count("data-daily-tools-v219") == 1
    assert source.count("data-learning-paths-v219") == 1
    assert source.count("data-daily-tools-journey-v219") == 1
    assert source.count('href="daily-tools/"') >= 3
    assert source.count('href="learning-paths/"') >= 3
    for phrase in FORBIDDEN_OPERATIONAL_COPY:
        assert phrase not in source
    assert len(re.findall(r"<h1\b", source)) == 1
    assert len(re.findall(r"<h2\b", source)) >= 5
    assert len(re.findall(r"<h3\b", source)) >= 24
    assert 'href="#main"' in source and 'id="main"' in source
    assert 'color-scheme" content="light"' in source
    assert "background:#071827" not in source and "background:#000" not in source
    for link in REQUIRED_LINKS:
        assert f'href="{link}"' in source, link
    for relative_path in REQUIRED_FILES:
        assert (ROOT / relative_path).is_file(), relative_path

    description = re.search(r'<meta name="description" content="([^"]+)"', source)
    assert description and 120 <= len(description.group(1)) <= 220
    keywords = re.search(r'<meta name="keywords" content="([^"]+)"', source)
    assert keywords
    keyword_items = [item.strip() for item in keywords.group(1).split(",") if item.strip()]
    assert len(keyword_items) >= 28
    assert {"الصحة النفسية", "علم النفس", "التربية الدامجة", "المكتبة النفسية", "مقارنات نفسية", "الاختبارات النفسية", "أدوات نفسية تفاعلية", "أدوات تنظيم التوتر", "أدوات متابعة النوم", "مسارات تعلم الصحة النفسية"}.issubset(keyword_items)

    for required_meta in (
        '<link rel="manifest" href="/pterminology-site/manifest.webmanifest">',
        '<link rel="icon" href="/pterminology-site/assets/brand/logo-mark.svg" type="image/svg+xml">',
        '<link rel="search" type="application/opensearchdescription+xml"',
        '<link rel="sitemap" type="application/xml" href="https://khaledaltheeb.github.io/pterminology-site/sitemap.xml">',
        '<meta property="og:image" content="https://khaledaltheeb.github.io/pterminology-site/assets/brand/social-card.svg">',
        '<meta name="twitter:image" content="https://khaledaltheeb.github.io/pterminology-site/assets/brand/social-card.svg">',
    ):
        assert required_meta in source

    structured = re.search(r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL)
    assert structured
    graph = json.loads(structured.group(1)).get("@graph", [])
    website = next(node for node in graph if node.get("@type") == "WebSite")
    organization = next(node for node in graph if node.get("@type") == "Organization")
    collection = next(node for node in graph if node.get("@type") == "CollectionPage")
    assert website.get("name") == BRAND and website.get("potentialAction", {}).get("@type") == "SearchAction"
    assert organization.get("name") == BRAND and organization.get("slogan") == SLOGAN
    assert "مصطلحات علم النفس" in organization.get("alternateName", [])
    assert organization.get("logo", {}).get("url", "").endswith("/assets/brand/logo-mark.svg")
    parts = collection.get("hasPart", [])
    assert any(part.get("@type") == "WebAPI" for part in parts)
    part_urls = {part.get("url") for part in parts}
    for url in (
        "https://khaledaltheeb.github.io/pterminology-site/comparisons/",
        "https://khaledaltheeb.github.io/pterminology-site/library/",
        "https://khaledaltheeb.github.io/pterminology-site/guided-assessment/",
        "https://khaledaltheeb.github.io/pterminology-site/daily-tools/",
        "https://khaledaltheeb.github.io/pterminology-site/learning-paths/",
    ):
        assert url in part_urls

    manifest = load_json("manifest.webmanifest")
    platform = load_json("api/v1/platform.json")
    specialists = load_json("api/v1/specialists-partners.json")
    openapi = load_json("api/v1/openapi.json")
    course_schema = load_json("api/v1/courses.schema.json")
    course_example = load_json("api/v1/courses.example.json")
    assert manifest.get("name") == BRAND
    assert manifest.get("dir") == "rtl" and manifest.get("lang") == "ar"
    assert platform.get("apiVersion") == "1.1.0"
    resources = platform.get("resources", [])
    assert any(item.get("id") == "specialists-partners" for item in resources)
    assert platform.get("endpoints", {}).get("specialistsPartners", "").endswith("/api/v1/specialists-partners.json")
    assert specialists.get("id") == "specialists-partners"
    assert specialists.get("publicationRules", {}).get("requiresWrittenPublicationConsent") is True
    assert specialists.get("publicationRules", {}).get("paidRankingAllowed") is False
    assert openapi.get("openapi") == "3.1.0"
    assert course_schema["properties"]["authorization"]["properties"]["status"]["const"] == "authorized"
    assert course_example["authorization"]["status"] == "authorized"
    assert course_example["courses"][0]["rights"]["metadataReuse"] is True
    assert course_example["courses"][0]["rights"]["contentReuse"] is False

    print(json.dumps({
        "status": "passed", "contract": "institutional-home-discovery-seo-v323",
        "brand": BRAND, "slogan": SLOGAN, "required_links": len(REQUIRED_LINKS),
        "required_files": len(REQUIRED_FILES), "description_chars": len(description.group(1)),
        "keyword_items": len(keyword_items), "jsonld_nodes": len(graph),
        "h1": len(re.findall(r"<h1\b", source)), "h2": len(re.findall(r"<h2\b", source)),
        "h3": len(re.findall(r"<h3\b", source)), "specialists_partners_api": True,
        "api_version": platform["apiVersion"], "openapi": openapi["openapi"],
        "lab_tool_count": 93, "light_palette": True,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
