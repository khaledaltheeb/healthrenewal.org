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

from scripts.publish_daily_tools_v24_core import DESIGN_CONTRACT
from scripts.daily_tools_v100 import CATALOG_CONTRACT, load_data

SITE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
BANNED = ("يشخص", "تشخيصك", "يعالج نهائيًا", "مضمون", "بديل عن الطبيب", "درجة الاكتئاب", "درجة القلق")
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SLEEP_SLUG = "sleep-wind-down-plan"
SEO_CONTRACT = 219


def norm(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()


def relative_luminance(value: str) -> float:
    value = value.lstrip("#")
    channels = [int(value[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    light, dark = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def main() -> None:
    data = load_data()
    tools, paths, categories, sources = data["tools"], data["paths"], data["categories"], data["sources"]
    assert len(tools) >= CATALOG_CONTRACT, len(tools)
    assert len(categories) >= 10 and len(paths) >= 10
    assert data.get("catalog_contract") == CATALOG_CONTRACT

    slugs = [item["slug"] for item in tools + paths]
    titles = [norm(item["title"]) for item in tools + paths]
    assert len(slugs) == len(set(slugs))
    assert len(titles) == len(set(titles))
    assert all(re.fullmatch(r"[a-z0-9-]+", slug) for slug in slugs)

    source_ids = {source["id"] for source in sources}
    category_ids = {category["id"] for category in categories}
    tool_slugs = {tool["slug"] for tool in tools}
    category_counts = Counter(tool["category_id"] for tool in tools)
    assert set(category_counts) == category_ids
    assert min(category_counts.values()) >= 8, category_counts
    assert all(len(tool["steps"]) >= 4 and len(tool["save_fields"]) >= 3 and tool["safety"] for tool in tools)
    assert all(tool["category_id"] in category_ids and set(tool["source_ids"]) <= source_ids for tool in tools)
    assert all(len(path["days"]) >= 5 and set(path["related_tools"]) <= tool_slugs for path in paths)
    assert len(sources) >= 12 and len({source["publisher"] for source in sources}) >= 5
    assert all(source["url"].startswith("https://") for source in sources)
    assert all(source.get("source_type") and source.get("verified_at") and source.get("status") == "current" and source.get("claims_supported") for source in sources)

    source_blob = json.dumps(data, ensure_ascii=False).lower()
    assert not any(item in source_blob for item in BANNED)

    palette_pairs = {
        "ink_on_rose": ("#173f45", "#fff0f5"), "ink_on_mint": ("#173f45", "#e5faf5"),
        "ink_on_lilac": ("#173f45", "#f2edff"), "ink_on_peach": ("#173f45", "#fff0e8"),
        "ink_on_butter": ("#173f45", "#fff8d8"), "berry_on_rose": ("#5b2946", "#fff0f5"),
        "brand_on_mint": ("#075f5b", "#e5faf5"),
    }
    ratios = {name: round(contrast_ratio(*pair), 2) for name, pair in palette_pairs.items()}
    assert all(value >= 4.5 for value in ratios.values()), ratios

    if SITE:
        expected = (
            [SITE / "daily-tools/index.html", SITE / "learning-paths/index.html"]
            + [SITE / "daily-tools" / tool["slug"] / "index.html" for tool in tools]
            + [SITE / "learning-paths" / path["slug"] / "index.html" for path in paths]
        )
        assert all(path.exists() for path in expected), [str(path) for path in expected if not path.exists()]
        required_metadata = (
            'rel="canonical"', 'name="keywords"', 'name="robots"', 'rel="manifest"', 'rel="icon"',
            'rel="search"', 'rel="sitemap"', 'property="og:image"', 'name="twitter:card"',
            'name="twitter:image"', "application/ld+json",
        )
        for page in expected:
            text = page.read_text(encoding="utf-8")
            assert text.count("<h1>") == 1, page
            assert 'dir="rtl"' in text, page
            assert f'data-design="marshmallow-v{DESIGN_CONTRACT}"' in text, page
            assert f'data-seo="institutional-v{SEO_CONTRACT}"' in text, page
            dedicated_sleep = page == SITE / "daily-tools" / SLEEP_SLUG / "index.html" and "data-sleep-log" in text
            if not dedicated_sleep:
                assert f'data-catalog="daily-tools-v{CATALOG_CONTRACT}"' in text, page
            assert all(marker in text for marker in required_metadata), page
            assert text.count('<meta name="description"') == 1, page
            assert text.count('<link rel="canonical"') == 1, page
            assert "--mint:#e5faf5" in text and "--rose:#fff0f5" in text and "--lilac:#f2edff" in text, page
            assert "--peach:#fff0e8" in text and "--butter:#fff8d8" in text, page
            assert "text-shadow" not in text.lower(), page
            assert "rgba(0,0,0" not in text.replace(" ", "").lower(), page
            assert not any(item in text.lower() for item in BANNED), page

        center = (SITE / "daily-tools/index.html").read_text(encoding="utf-8")
        assert center.count("<article data-tool-card") == len(tools)
        assert "data-tool-search" in center and "data-category-select" in center
        assert "مصادر" in center
        assert f"{len(tools)} أداة نفسية وتربوية يومية" in center

        for tool in tools:
            text = (SITE / "daily-tools" / tool["slug"] / "index.html").read_text(encoding="utf-8")
            assert "لا تُرسل البيانات إلى خادم" in text
            if tool["slug"] == SLEEP_SLUG and "data-sleep-log" in text:
                assert "data-export-json" in text and "data-delete-sleep" in text
                assert "sleep-log-v49.js" in text and "غير تشخيص" in text
            else:
                assert "localStorage" in text
                assert "data-step-progress" in text and "تصدير JSON" in text
                assert "مصادر المنهج الخاصة بهذه الأداة" in text
                assert not any(marker in text for marker in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon"))

        homepage = (SITE / "index.html").read_text(encoding="utf-8")
        assert homepage.count('href="daily-tools/"') >= 2
        assert homepage.count('href="learning-paths/"') >= 2
        assert homepage.count("data-daily-tools-v219") == 1
        assert homepage.count("data-learning-paths-v219") == 1
        assert f"{len(tools)} أداة عربية عملية" in homepage

        report = json.loads((SITE / "api/daily-tools-v24.json").read_text(encoding="utf-8"))
        assert report["catalog_contract"] == CATALOG_CONTRACT
        assert report["tools"] == len(tools)
        assert report["categories"] == len(categories)
        assert report["paths"] == len(paths)
        assert report["pages"] == len(tools) + len(paths) + 2
        assert report["local_only"] is True and report["search_and_filters"] is True
        assert report["per_tool_sources"] is True and report["homepage_linked"] is True

        child = ET.parse(SITE / "sitemap-tools-paths.xml").getroot()
        assert child.tag == f"{{{NS}}}urlset"
        child_urls = child.findall(f"{{{NS}}}url")
        assert len(child_urls) == report["pages"]
        assert all(item.find(f"{{{NS}}}loc") is not None for item in child_urls)

        sitemap_index = ET.parse(SITE / "sitemap.xml").getroot()
        assert sitemap_index.tag == f"{{{NS}}}sitemapindex"
        target = "https://healthrenewal.org/sitemap-tools-paths.xml"
        matches = [item.text for item in sitemap_index.findall(f"{{{NS}}}sitemap/{{{NS}}}loc") if item.text == target]
        assert len(matches) == 1

    print(json.dumps({
        "tools": len(tools), "categories": len(categories), "paths": len(paths), "sources": len(sources),
        "unique_slugs": True, "unique_titles": True, "non_diagnostic": True,
        "minimum_tools_per_category": min(category_counts.values()),
        "design_contract": DESIGN_CONTRACT, "seo_contract": SEO_CONTRACT,
        "catalog_contract": CATALOG_CONTRACT, "minimum_contrast_ratio": min(ratios.values()),
        "production_checked": bool(SITE), "homepage_linked": bool(SITE), "sitemap_namespaces_checked": bool(SITE),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
