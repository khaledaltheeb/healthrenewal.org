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
    "provider-assessment-demo/",
    "trust/",
    "partners/",
    "developers/",
)
FORBIDDEN_PUBLIC_PLANNING = (
    "خطة نمو قابلة للقياس",
    "الأهداف الدنيا للمحتوى",
    "هدف معلن للموسوعة النفسية العربية",
    "هدف أدنى لكل مسار رئيسي",
    "هدف توسع",
    "العدد الحالي يثبت",
    "ما سيتم إنجازه",
    "قيد الإعداد",
    "قيد التوسع",
)


class StrictHTMLParser(HTMLParser):
    pass


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    StrictHTMLParser().feed(source)

    assert 'lang="ar"' in source and 'dir="rtl"' in source
    assert BRAND in source, "Homepage is missing the unified platform name"
    assert SLOGAN in source, "Homepage is missing the approved slogan"
    assert "مصطلحات علم النفس — الاسم المؤسس" in source, "Founding name must remain visible"
    assert "ثلاثين شرحًا" not in source, "Homepage contains obsolete 30-item claim"
    assert "2000+" not in source, "Homepage must use exact verified inventory, not plus notation"
    leaked = [phrase for phrase in FORBIDDEN_PUBLIC_PLANNING if phrase in source]
    assert not leaked, f"Internal planning language leaked to the public homepage: {leaked}"

    assert len(re.findall(r"<h1\b", source)) == 1, "Homepage must contain exactly one h1"
    assert len(re.findall(r"<h2\b", source)) >= 4, "Homepage needs structured H2 sections"
    assert len(re.findall(r"<h3\b", source)) >= 12, "Homepage needs discoverable H3 cards"
    assert 'href="#main"' in source, "Missing skip link"
    assert 'id="main"' in source, "Missing main landmark target"
    assert 'color-scheme" content="light"' in source, "Homepage must declare light color scheme"
    assert "background:#071827" not in source and "background:#000" not in source, "Dark homepage regression"

    for link in REQUIRED_LINKS:
        assert f'href="{link}"' in source, f"Missing primary discovery link: {link}"

    institutional_markers = (
        'assets/logo-mark-v215.svg',
        'assets/logo-card-v215.svg',
        'rel="icon"',
        'property="og:image"',
        'name="twitter:image"',
        'type="application/json"',
        'api/v1/catalog.json',
        'meta name="keywords"',
    )
    for marker in institutional_markers:
        assert marker in source, f"Missing institutional homepage marker: {marker}"

    description = re.search(r'<meta name="description" content="([^"]+)"', source)
    assert description and 100 <= len(description.group(1)) <= 240
    keywords = re.search(r'<meta name="keywords" content="([^"]+)"', source)
    assert keywords, "Missing thematic keywords metadata"
    keyword_terms = [item.strip() for item in keywords.group(1).split(",") if item.strip()]
    assert 8 <= len(keyword_terms) <= 20, keyword_terms
    assert len(keyword_terms) == len(set(keyword_terms)), "Duplicate keyword terms"

    structured = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL
    )
    assert structured, "Missing JSON-LD"
    payload = json.loads(structured.group(1))
    graph = payload.get("@graph", [])
    assert any(node.get("@type") == "WebSite" and node.get("name") == BRAND for node in graph)
    assert any(node.get("@type") == "CollectionPage" for node in graph)
    assert any(node.get("@type") == "Organization" and node.get("name") == BRAND for node in graph)
    organization = next(node for node in graph if node.get("@type") == "Organization")
    assert SLOGAN == organization.get("slogan")
    assert "مصطلحات علم النفس" in organization.get("alternateName", [])
    assert organization.get("logo", {}).get("url", "").endswith("logo-mark-v215.svg")

    print(
        json.dumps(
            {
                "status": "passed",
                "brand": BRAND,
                "slogan": SLOGAN,
                "required_links": len(REQUIRED_LINKS),
                "description_chars": len(description.group(1)),
                "keyword_terms": len(keyword_terms),
                "jsonld_nodes": len(graph),
                "h1": len(re.findall(r"<h1\b", source)),
                "h2": len(re.findall(r"<h2\b", source)),
                "h3": len(re.findall(r"<h3\b", source)),
                "planning_leaks": 0,
                "institutional_logo": True,
                "developers_api_linked": True,
                "light_palette": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
