from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.publish_learning_paths_v326 import REQUIRED_EXISTING_SLUGS, load_catalog

TOOLS_DATA = ROOT / "content" / "v24" / "daily-tools-learning-paths-ar.json"
SITE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
BANNED = (
    "تشخيصك",
    "يعالج نهائيًا",
    "مضمون",
    "بديل عن الطبيب",
    "درجة الاكتئاب",
    "درجة القلق",
)
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
DESIGN_CONTRACT = 219
SEO_CONTRACT = 326

def norm(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).casefold()

def relative_luminance(value: str) -> float:
    value = value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

def contrast_ratio(foreground: str, background: str) -> float:
    light, dark = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)

def main() -> None:
    tools_data = json.loads(TOOLS_DATA.read_text(encoding="utf-8"))
    tools = tools_data["tools"]
    catalog = load_catalog()
    paths = catalog["paths"]
    categories = catalog["categories"]
    sources = catalog["sources"]

    assert len(tools) == 8
    assert len(paths) == 100
    assert len(categories) == 10
    assert len(sources) >= 20

    category_ids = {item["id"] for item in categories}
    source_ids = {item["id"] for item in sources}
    tool_slugs = {item["slug"] for item in tools}
    counts = Counter(path["category"] for path in paths)
    assert set(counts) == category_ids
    assert set(counts.values()) == {10}, counts

    slugs = [path["slug"] for path in paths]
    titles = [norm(path["title"]) for path in paths]
    ids = [path["id"] for path in paths]
    assert len(slugs) == len(set(slugs)) == 100
    assert len(titles) == len(set(titles)) == 100
    assert len(ids) == len(set(ids)) == 100
    assert REQUIRED_EXISTING_SLUGS <= set(slugs)
    assert all(re.fullmatch(r"[a-z0-9-]+", slug) for slug in slugs)

    source_blob = "\n".join(
        file.read_text(encoding="utf-8")
        for file in (ROOT / "content" / "v326" / "learning-paths").glob("*.json")
    ).casefold()
    assert not any(item.casefold() in source_blob for item in BANNED)

    for path in paths:
        assert path["category"] in category_ids
        assert len(path["outcomes"]) >= 3
        assert len(path["modules"]) == 5
        assert len(path["checklist"]) >= 5
        assert len(path["faq"]) >= 3
        assert len(path["source_ids"]) >= 2
        assert set(path["source_ids"]) <= source_ids
        assert set(path["related_tools"]) <= tool_slugs
        assert path["safety"] and path["seek_help"] and path["reviewed"]
        for position, module in enumerate(path["modules"], start=1):
            assert module["position"] == position
            assert module["title"] and module["objective"] and module["explanation"]
            assert len(module["key_points"]) >= 3
            assert module["application"]
            assert len(module["knowledge_check"]) >= 2

    assert all(source["url"].startswith("https://") for source in sources)
    assert len({source["publisher"] for source in sources}) >= 6

    palette_pairs = {
        "ink_on_rose": ("#173f45", "#fff0f5"),
        "ink_on_mint": ("#173f45", "#e5faf5"),
        "ink_on_lilac": ("#173f45", "#f2edff"),
        "ink_on_peach": ("#173f45", "#fff0e8"),
        "ink_on_butter": ("#173f45", "#fff8d8"),
        "berry_on_rose": ("#5b2946", "#fff0f5"),
        "brand_on_mint": ("#075f5b", "#e5faf5"),
    }
    ratios = {name: round(contrast_ratio(*pair), 2) for name, pair in palette_pairs.items()}
    assert all(value >= 4.5 for value in ratios.values()), ratios

    if SITE:
        expected = (
            [SITE / "daily-tools" / "index.html", SITE / "learning-paths" / "index.html"]
            + [SITE / "daily-tools" / tool["slug"] / "index.html" for tool in tools]
            + [SITE / "learning-paths" / path["slug"] / "index.html" for path in paths]
        )
        assert len(expected) == 110
        assert all(page.is_file() for page in expected), [str(page) for page in expected if not page.is_file()]

        required_metadata = (
            'rel="canonical"',
            'name="keywords"',
            'name="robots"',
            'rel="manifest"',
            'rel="icon"',
            'rel="search"',
            'rel="sitemap"',
            'property="og:image"',
            'name="twitter:card"',
            'name="twitter:image"',
            "application/ld+json",
        )
        for page in expected:
            text = page.read_text(encoding="utf-8")
            assert text.count("<h1>") == 1, page
            assert 'dir="rtl"' in text, page
            assert f'data-design="marshmallow-v{DESIGN_CONTRACT}"' in text, page
            assert f'data-seo="institutional-v{SEO_CONTRACT}"' in text, page
            assert all(marker in text for marker in required_metadata), page
            assert text.count('<meta name="description"') == 1, page
            assert text.count('<link rel="canonical"') == 1, page
            assert "text-shadow" not in text.casefold(), page
            assert "rgba(0,0,0" not in text.replace(" ", "").casefold(), page
            assert not any(item.casefold() in text.casefold() for item in BANNED), page

        center = (SITE / "learning-paths" / "index.html").read_text(encoding="utf-8")
        assert center.count('class="path-card"') == 100
        assert center.count('class="filter-button"') == 11
        assert "500</strong> وحدة تعلم" in center
        assert "29</strong> مرجعًا مؤسسيًا" in center
        assert "fetch(" not in center and "XMLHttpRequest" not in center and "sendBeacon" not in center

        for path in paths:
            page = (SITE / "learning-paths" / path["slug"] / "index.html").read_text(encoding="utf-8")
            assert page.count('class="module"') == 5, path["slug"]
            assert "<h2>نتائج التعلم</h2>" in page
            assert "<h2>المراجع المؤسسية الخاصة بالمسار</h2>" in page
            assert "<h2>السلامة وحدود المسار</h2>" in page
            assert '"@type":"Course"' in page
            assert '"@type":"BreadcrumbList"' in page
            assert '"@type":"FAQPage"' in page
            internal_links = page.count('href="/pterminology-site/')
            assert internal_links >= 7, (path["slug"], internal_links)

        homepage = (SITE / "index.html").read_text(encoding="utf-8")
        assert homepage.count("data-learning-paths-v219") == 1
        assert "مئة مسار تعلم مؤسسي" in homepage

        report = json.loads((SITE / "api" / "daily-tools-v24.json").read_text(encoding="utf-8"))
        assert report["learning_paths_catalog_version"] == 326
        assert report["tools"] == 8
        assert report["paths"] == 100
        assert report["path_categories"] == 10
        assert report["path_sources"] == len(sources)
        assert report["pages"] == 110
        assert report["local_only"] is True

        child = ET.parse(SITE / "sitemap-tools-paths.xml").getroot()
        assert child.tag == f"{{{NS}}}urlset"
        child_urls = child.findall(f"{{{NS}}}url")
        assert len(child_urls) == 110
        locations = [item.find(f"{{{NS}}}loc").text for item in child_urls]
        assert len(locations) == len(set(locations))
        assert BASE_URL + "learning-paths/" in locations
        for slug in REQUIRED_EXISTING_SLUGS:
            assert BASE_URL + "learning-paths/" + slug + "/" in locations

        sitemap_index = ET.parse(SITE / "sitemap.xml").getroot()
        assert sitemap_index.tag == f"{{{NS}}}sitemapindex"
        target = BASE_URL + "sitemap-tools-paths.xml"
        matches = [
            item.text
            for item in sitemap_index.findall(f"{{{NS}}}sitemap/{{{NS}}}loc")
            if item.text == target
        ]
        assert len(matches) == 1, matches

    print(json.dumps({
        "tools": 8,
        "paths": 100,
        "categories": 10,
        "paths_per_category": 10,
        "modules": 500,
        "sources": len(sources),
        "unique_slugs": True,
        "existing_urls_preserved": sorted(REQUIRED_EXISTING_SLUGS),
        "seo_contract": SEO_CONTRACT,
        "minimum_contrast_ratio": min(ratios.values()),
        "production_checked": bool(SITE),
    }, ensure_ascii=False))

BASE_URL = "https://khaledaltheeb.github.io/pterminology-site/"

if __name__ == "__main__":
    main()
