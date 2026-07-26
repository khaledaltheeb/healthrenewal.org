from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.daily_tools_v275 import load_catalog

SITE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
BANNED = (
    "يشخص", "تشخيصك", "يعالج نهائيًا", "مضمون", "بديل عن الطبيب",
    "درجة الاكتئاب", "درجة القلق", "معاقين", "المعاقين", "معاق",
)
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SLEEP_SLUG = "sleep-wind-down-plan"
DESIGN_CONTRACT = 219
SEO_CONTRACT = 219
CONTENT_CONTRACT = 275
EXPECTED_TOOLS = 100
EXPECTED_PATHS = 4
EXPECTED_CATEGORIES = 10
EXPECTED_PAGES = EXPECTED_TOOLS + EXPECTED_PATHS + 2
ALLOWED_SOURCE_HOSTS = {
    "www.who.int", "who.int", "www.unicef.org", "unicef.org",
    "www.cdc.gov", "cdc.gov", "www.nhlbi.nih.gov", "nhlbi.nih.gov",
    "www.nice.org.uk", "nice.org.uk",
}


def norm(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()


def relative_luminance(value: str) -> float:
    value = value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    light, dark = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (light + 0.05) / (dark + 0.05)


def visible_text(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def validate_data(data: dict) -> dict:
    assert data["version"] == 24
    assert data["catalog_version"] == 25
    assert data["content_contract"] == CONTENT_CONTRACT
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["reviewed_at"])
    assert data["reviewed_at"] <= date.today().isoformat()

    tools = data["tools"]
    paths = data["paths"]
    categories = data["categories"]
    sources = data["sources"]
    assert len(tools) == EXPECTED_TOOLS, len(tools)
    assert len(paths) == EXPECTED_PATHS, len(paths)
    assert len(categories) == EXPECTED_CATEGORIES, len(categories)
    assert len(sources) >= 12, len(sources)

    category_ids = {item["id"] for item in categories}
    source_ids = {item["id"] for item in sources}
    assert len(category_ids) == len(categories)
    assert len(source_ids) == len(sources)

    slugs = [item["slug"] for item in tools + paths]
    titles = [norm(item["title"]) for item in tools + paths]
    assert len(slugs) == len(set(slugs))
    assert len(titles) == len(set(titles))
    assert all(re.fullmatch(r"[a-z0-9-]+", slug) for slug in slugs)
    assert [tool["id"] for tool in tools] == list(range(1, EXPECTED_TOOLS + 1))

    source_blob = json.dumps(data, ensure_ascii=False).lower()
    assert not any(item in source_blob for item in BANNED), [
        item for item in BANNED if item in source_blob
    ]

    tool_slugs = {tool["slug"] for tool in tools}
    required_tool_keys = {
        "id", "slug", "title", "intent", "category", "audience", "duration",
        "when_to_use", "steps", "review_questions", "save_fields",
        "interpretation", "next_steps", "avoid", "safety", "source_ids",
        "reviewed_at", "evidence_note", "related_tools",
    }
    for tool in tools:
        assert required_tool_keys <= set(tool), (tool["slug"], required_tool_keys - set(tool))
        assert tool["category"] in category_ids
        assert 1 <= len(tool["audience"]) <= 4
        assert len(tool["when_to_use"]) >= 3
        assert len(tool["steps"]) >= 5
        assert len(tool["review_questions"]) >= 3
        assert len(tool["save_fields"]) >= 4
        assert len(tool["interpretation"]) >= 3
        assert len(tool["next_steps"]) >= 3
        assert len(tool["avoid"]) >= 3
        assert len(tool["source_ids"]) >= 2
        assert set(tool["source_ids"]) <= source_ids
        assert len(tool["related_tools"]) >= 2
        assert set(tool["related_tools"]) <= tool_slugs
        assert tool["slug"] not in tool["related_tools"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", tool["reviewed_at"])
        assert len(tool["intent"]) >= 45
        assert len(tool["evidence_note"]) >= 90
        assert len(tool["safety"]) >= 70

    counts = Counter(tool["category"] for tool in tools)
    assert set(counts) == category_ids
    assert min(counts.values()) >= 7, counts
    assert max(counts.values()) <= 12, counts

    for path in paths:
        assert len(path["days"]) >= 5
        assert 2 <= len(path["related_tools"]) <= 6
        assert set(path["related_tools"]) <= tool_slugs

    for source in sources:
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https"
        assert parsed.hostname in ALLOWED_SOURCE_HOSTS, source["url"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["checked_at"])
        assert source["checked_at"] <= date.today().isoformat()
        assert 1990 <= int(source["year"]) <= date.today().year
        assert len(source["scope"]) >= 45

    sleep_context_paths = [path for path in paths if SLEEP_SLUG in path["related_tools"]]
    assert len(sleep_context_paths) >= 2

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

    return {
        "tools": tools,
        "paths": paths,
        "categories": categories,
        "sources": sources,
        "sleep_context_paths": sleep_context_paths,
        "ratios": ratios,
        "counts": counts,
    }


def validate_site(data: dict, state: dict) -> None:
    assert SITE is not None
    tools = state["tools"]
    paths = state["paths"]
    expected = (
        [SITE / "daily-tools" / "index.html", SITE / "learning-paths" / "index.html"]
        + [SITE / "daily-tools" / tool["slug"] / "index.html" for tool in tools]
        + [SITE / "learning-paths" / path["slug"] / "index.html" for path in paths]
    )
    assert len(expected) == EXPECTED_PAGES
    assert all(path.exists() for path in expected), [
        str(path) for path in expected if not path.exists()
    ]

    required_metadata = (
        'rel="canonical"', 'name="keywords"', 'name="robots"',
        'rel="manifest"', 'rel="icon"', 'rel="search"', 'rel="sitemap"',
        'property="og:image"', 'name="twitter:card"', 'name="twitter:image"',
        "application/ld+json",
    )
    for page in expected:
        text = page.read_text(encoding="utf-8")
        assert text.count("<h1>") == 1, page
        assert 'lang="ar"' in text and 'dir="rtl"' in text, page
        assert 'name="viewport"' in text, page
        assert f'data-design="marshmallow-v{DESIGN_CONTRACT}"' in text, page
        assert f'data-seo="institutional-v{SEO_CONTRACT}"' in text, page
        is_sleep_page = page == SITE / "daily-tools" / SLEEP_SLUG / "index.html"
        if not (is_sleep_page and "sleep-log-v49.js" in text):
            assert f'data-tools-content="v{CONTENT_CONTRACT}"' in text, page
        assert all(marker in text for marker in required_metadata), page
        assert text.count('<meta name="description"') == 1, page
        assert text.count('<link rel="canonical"') == 1, page
        assert "--mint:#e5faf5" in text and "--rose:#fff0f5" in text, page
        assert "--lilac:#f2edff" in text and "--peach:#fff0e8" in text, page
        assert "--butter:#fff8d8" in text, page
        assert "text-shadow" not in text.lower(), page
        assert "rgba(0,0,0" not in text.replace(" ", "").lower(), page
        assert "@media print" in text, page
        assert "@media(max-width:700px)" in text, page
        assert not any(item in text.lower() for item in BANNED), page
        schema = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
        assert schema, page
        json.loads(schema.group(1))

    center = (SITE / "daily-tools" / "index.html").read_text(encoding="utf-8")
    assert center.count("<article data-tool-card") == EXPECTED_TOOLS
    assert "100 أداة نفسية وتنظيمية يومية" in center
    assert "data-tool-search" in center and "data-tool-category" in center
    assert "data-result-count" in center and "data-tool-grid" in center
    assert "تظهر ${count} أداة من أصل ${cards.length}" in center
    assert len(visible_text(center)) >= 10000

    sleep_runtime_path = SITE / "assets" / "sleep-log-v49.js"
    generic_required = (
        "متى تفيد هذه الأداة؟", "خطوات الاستخدام المنهجي", "أسئلة المراجعة",
        "كيف تقرأ ما سجلته؟", "ما الخطوة التالية؟", "ما يجب تجنبه",
        "السلامة ومتى تطلب المساعدة", "الأساس المنهجي وحدوده",
        "تاريخ التحقق والمراجعة", "أدوات مرتبطة",
    )
    for tool in tools:
        page = SITE / "daily-tools" / tool["slug"] / "index.html"
        text = page.read_text(encoding="utf-8")
        assert "لا تُرسل البيانات إلى خادم" in text, tool["slug"]
        if tool["slug"] == SLEEP_SLUG and "sleep-log-v49.js" in text:
            assert sleep_runtime_path.is_file(), sleep_runtime_path
            runtime = sleep_runtime_path.read_text(encoding="utf-8")
            assert "localStorage" in runtime
            assert not any(marker in runtime for marker in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon"))
        else:
            assert "localStorage" in text, tool["slug"]
            assert all(marker in text for marker in generic_required), tool["slug"]
            assert len(visible_text(text)) >= 1800, (tool["slug"], len(visible_text(text)))
        assert sum(text.count(source["url"]) for source in state["sources"]) >= 2

    sleep_href = f"/pterminology-site/daily-tools/{SLEEP_SLUG}/"
    assert center.count(f'href="{sleep_href}"') == 1
    contextual = []
    for path in paths:
        page = (SITE / "learning-paths" / path["slug"] / "index.html").read_text(encoding="utf-8")
        if f'href="{sleep_href}"' in page:
            contextual.append(path["slug"])
    assert len(contextual) >= 2, contextual

    homepage = (SITE / "index.html").read_text(encoding="utf-8")
    assert homepage.count('href="daily-tools/"') >= 2
    assert homepage.count('href="learning-paths/"') >= 2
    assert homepage.count("data-daily-tools-v219") == 1
    assert homepage.count("data-learning-paths-v219") == 1
    assert "100 أداة نفسية وتنظيمية يومية" in homepage
    assert '"url":"https://khaledaltheeb.github.io/pterminology-site/daily-tools/"' in homepage

    report = json.loads((SITE / "api" / "daily-tools-v24.json").read_text(encoding="utf-8"))
    assert report["version"] == 24
    assert report["catalog_version"] == 25
    assert report["content_contract"] == CONTENT_CONTRACT
    assert report["design_contract"] == DESIGN_CONTRACT
    assert report["tools"] == EXPECTED_TOOLS
    assert report["categories"] == EXPECTED_CATEGORIES
    assert report["paths"] == EXPECTED_PATHS
    assert report["pages"] == EXPECTED_PAGES
    assert report["sources"] == len(state["sources"])
    assert report["local_only"] is True
    assert report["rich_guidance"] is True
    assert report["search_and_filter"] is True
    assert report["homepage_linked"] is True
    assert json.loads((SITE / "api" / "daily-tools-v25.json").read_text(encoding="utf-8")) == report

    child = ET.parse(SITE / "sitemap-tools-paths.xml").getroot()
    assert child.tag == f"{{{NS}}}urlset"
    child_urls = child.findall(f"{{{NS}}}url")
    assert len(child_urls) == EXPECTED_PAGES, len(child_urls)
    locs = [
        item.find(f"{{{NS}}}loc").text
        for item in child_urls
        if item.find(f"{{{NS}}}loc") is not None
    ]
    assert len(locs) == len(set(locs))
    assert len([url for url in locs if "/daily-tools/" in url]) == EXPECTED_TOOLS + 1

    sitemap_index = ET.parse(SITE / "sitemap.xml").getroot()
    assert sitemap_index.tag == f"{{{NS}}}sitemapindex"
    target = "https://khaledaltheeb.github.io/pterminology-site/sitemap-tools-paths.xml"
    matches = [
        item.text
        for item in sitemap_index.findall(f"{{{NS}}}sitemap/{{{NS}}}loc")
        if item.text == target
    ]
    assert len(matches) == 1, matches

    broken = []
    for page in expected:
        text = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="(/pterminology-site/(?:daily-tools|learning-paths)/[^"#?]*)"', text):
            relative = href.removeprefix("/pterminology-site/").strip("/")
            target_path = SITE / relative / "index.html"
            if not target_path.exists():
                broken.append((str(page), href))
    assert not broken, broken[:10]


def main() -> None:
    data = load_catalog()
    state = validate_data(data)
    if SITE:
        validate_site(data, state)
    print(json.dumps(
        {
            "tools": len(state["tools"]),
            "categories": len(state["categories"]),
            "paths": len(state["paths"]),
            "pages": EXPECTED_PAGES,
            "sources": len(state["sources"]),
            "category_distribution": dict(state["counts"]),
            "unique_slugs": True,
            "unique_titles": True,
            "non_diagnostic": True,
            "rich_methodology": True,
            "local_only": True,
            "sleep_context_paths": len(state["sleep_context_paths"]),
            "design_contract": DESIGN_CONTRACT,
            "seo_contract": SEO_CONTRACT,
            "content_contract": CONTENT_CONTRACT,
            "minimum_contrast_ratio": min(state["ratios"].values()),
            "contrast_ratios": state["ratios"],
            "production_checked": bool(SITE),
            "homepage_linked": bool(SITE),
            "sitemap_namespaces_checked": bool(SITE),
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
