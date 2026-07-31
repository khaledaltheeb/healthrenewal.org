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
    "start-here/",
    "encyclopedia/",
    "tips/",
    "care-guides/",
    "special-needs/",
    "assessment-lab/",
    "cognitive-lab/",
    "sectors/family/",
    "sectors/child/",
    "sectors/home/",
    "daily-tools/",
    "learning-paths/",
    "provider-assessment-demo/",
    "comparisons/",
    "library/",
    "guided-assessment/",
    "hubs/",
    "assessments/",
    "cognitive-tests/",
    "trust/",
    "partners/",
    "api/",
)
REQUIRED_FILES = (
    "manifest.webmanifest",
    "opensearch.xml",
    "assets/brand/logo-mark.svg",
    "assets/brand/logo.svg",
    "assets/brand/social-card.svg",
    "api/index.html",
    "api/v1/platform.json",
    "api/v1/openapi.json",
    "api/v1/courses.schema.json",
    "api/v1/courses.example.json",
)
FORBIDDEN_OPERATIONAL_COPY = (
    "خطة نمو قابلة للقياس",
    "هدف معلن للموسوعة النفسية العربية",
    "هدف أدنى لكل مسار رئيسي",
    "خط أساس المصدر الحالي",
    "يُحسب العدد من حزمة الإنتاج",
    "لا نشر قبل البوابات",
    "قيد الإعداد",
    "قيد التوسع",
)


class StrictHTMLParser(HTMLParser):
    pass


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    StrictHTMLParser().feed(source)

    assert 'lang="ar"' in source and 'dir="rtl"' in source
    assert BRAND in source, "Homepage is missing the unified platform name"
    assert SLOGAN in source, "Homepage is missing the approved slogan"
    assert "الاسم المؤسس: مصطلحات علم النفس" in source, "Founding name must remain visible"
    assert "ثلاثين شرحًا" not in source, "Homepage contains obsolete 30-item claim"
    assert "2,000+" in source, "Homepage must expose the production-backed encyclopedia scale"
    assert "200" in source, "Homepage must expose the production-backed hub count"
    assert "16" in source and "93" in source, "Homepage is missing verified platform inventory"
    assert "data-special-needs-v73" in source, "Special-needs publisher contract is missing"
    assert '<a class="btn secondary" href="care-guides/">أدلة التعامل مع الحالات</a>' in source
    assert "مكتبة المقارنات النفسية" in source, "Comparisons collection is not visibly described"
    assert "المكتبة الأكاديمية العربية" in source, "Academic library is not visibly described"
    assert "الأدوات النفسية التفاعلية" in source, "Interactive tools are not visibly described"
    assert "مسارات التعلم القصيرة" in source, "Learning paths are not visibly described"
    assert source.count("data-daily-tools-v219") == 1, "Interactive tools card must be unique"
    assert source.count("data-learning-paths-v219") == 1, "Learning paths card must be unique"
    assert source.count("data-daily-tools-journey-v219") == 1, "Interactive-tools journey hint must be unique"
    assert source.count('href="daily-tools/"') >= 3, "Daily tools need navigation, card and footer discovery"
    assert source.count('href="learning-paths/"') >= 3, "Learning paths need navigation, card and footer discovery"
    for phrase in FORBIDDEN_OPERATIONAL_COPY:
        assert phrase not in source, f"Operational planning copy leaked to users: {phrase}"

    assert len(re.findall(r"<h1\b", source)) == 1, "Homepage must contain exactly one h1"
    assert len(re.findall(r"<h2\b", source)) >= 5, "Homepage needs structured H2 sections"
    assert len(re.findall(r"<h3\b", source)) >= 24, "Homepage needs discoverable H3 cards"
    assert 'href="#main"' in source, "Missing skip link"
    assert 'id="main"' in source, "Missing main landmark target"
    assert 'color-scheme" content="light"' in source, "Homepage must declare light color scheme"
    assert "background:#071827" not in source and "background:#000" not in source, "Dark homepage regression"

    for link in REQUIRED_LINKS:
        assert f'href="{link}"' in source, f"Missing primary discovery link: {link}"
    for relative_path in REQUIRED_FILES:
        assert (ROOT / relative_path).is_file(), f"Missing institutional asset: {relative_path}"

    description = re.search(r'<meta name="description" content="([^"]+)"', source)
    assert description and 120 <= len(description.group(1)) <= 220
    keywords = re.search(r'<meta name="keywords" content="([^"]+)"', source)
    assert keywords, "Missing thematic keyword metadata"
    keyword_items = [item.strip() for item in keywords.group(1).split(",") if item.strip()]
    assert len(keyword_items) >= 28, "Homepage keyword coverage is too narrow"
    assert {
        "الصحة النفسية",
        "علم النفس",
        "التربية الدامجة",
        "المكتبة النفسية",
        "مقارنات نفسية",
        "الاختبارات النفسية",
        "أدوات نفسية تفاعلية",
        "أدوات تنظيم التوتر",
        "أدوات متابعة النوم",
        "مسارات تعلم الصحة النفسية",
    }.issubset(keyword_items)

    for required_meta in (
        '<link rel="manifest" href="/manifest.webmanifest">',
        '<link rel="icon" href="/assets/brand/logo-mark.svg" type="image/svg+xml">',
        '<link rel="search" type="application/opensearchdescription+xml"',
        '<link rel="sitemap" type="application/xml" href="https://healthrenewal.org/sitemap.xml">',
        '<meta property="og:image" content="https://healthrenewal.org/assets/brand/social-card.svg">',
        '<meta name="twitter:image" content="https://healthrenewal.org/assets/brand/social-card.svg">',
    ):
        assert required_meta in source, f"Missing homepage discovery metadata: {required_meta}"

    structured = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL
    )
    assert structured, "Missing JSON-LD"
    payload = json.loads(structured.group(1))
    graph = payload.get("@graph", [])
    website = next(node for node in graph if node.get("@type") == "WebSite")
    organization = next(node for node in graph if node.get("@type") == "Organization")
    collection = next(node for node in graph if node.get("@type") == "CollectionPage")
    assert website.get("name") == BRAND
    assert website.get("potentialAction", {}).get("@type") == "SearchAction"
    assert organization.get("name") == BRAND
    assert organization.get("slogan") == SLOGAN
    assert "مصطلحات علم النفس" in organization.get("alternateName", [])
    assert organization.get("logo", {}).get("url", "").endswith("/assets/brand/logo-mark.svg")
    parts = collection.get("hasPart", [])
    assert any(part.get("@type") == "WebAPI" for part in parts)
    part_urls = {part.get("url") for part in parts}
    assert "https://healthrenewal.org/comparisons/" in part_urls
    assert "https://healthrenewal.org/library/" in part_urls
    assert "https://healthrenewal.org/guided-assessment/" in part_urls
    assert "https://healthrenewal.org/daily-tools/" in part_urls
    assert "https://healthrenewal.org/learning-paths/" in part_urls

    manifest = load_json("manifest.webmanifest")
    platform = load_json("api/v1/platform.json")
    openapi = load_json("api/v1/openapi.json")
    course_schema = load_json("api/v1/courses.schema.json")
    course_example = load_json("api/v1/courses.example.json")
    assert manifest.get("name") == BRAND
    assert manifest.get("dir") == "rtl" and manifest.get("lang") == "ar"
    api_version = str(platform.get("apiVersion", ""))
    assert re.fullmatch(r"1\.\d+\.\d+", api_version), (
        f"Platform API must remain compatible with the supported 1.x semantic-version contract: {api_version!r}"
    )
    assert openapi.get("openapi") == "3.1.0"
    assert course_schema["properties"]["authorization"]["properties"]["status"]["const"] == "authorized"
    assert course_example["authorization"]["status"] == "authorized"
    assert course_example["courses"][0]["rights"]["metadataReuse"] is True
    assert course_example["courses"][0]["rights"]["contentReuse"] is False

    print(
        json.dumps(
            {
                "status": "passed",
                "contract": "institutional-home-discovery-seo-v220",
                "brand": BRAND,
                "slogan": SLOGAN,
                "required_links": len(REQUIRED_LINKS),
                "required_files": len(REQUIRED_FILES),
                "description_chars": len(description.group(1)),
                "keyword_items": len(keyword_items),
                "jsonld_nodes": len(graph),
                "h1": len(re.findall(r"<h1\b", source)),
                "h2": len(re.findall(r"<h2\b", source)),
                "h3": len(re.findall(r"<h3\b", source)),
                "comparisons_linked": True,
                "library_linked": True,
                "guided_assessment_linked": True,
                "daily_tools_linked": True,
                "learning_paths_linked": True,
                "interactive_tools_discovery_contract": 220,
                "operational_copy_hidden": True,
                "api_version": api_version,
                "openapi": openapi["openapi"],
                "lab_tool_count": 93,
                "light_palette": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
