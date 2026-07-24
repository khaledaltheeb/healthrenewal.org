from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v24" / "daily-tools-learning-paths-ar.json"
SITE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
BANNED = ("يشخص", "تشخيصك", "يعالج نهائيًا", "مضمون", "بديل عن الطبيب", "درجة الاكتئاب", "درجة القلق")
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SLEEP_SLUG = "sleep-wind-down-plan"
DESIGN_CONTRACT = 219


def norm(value: str) -> str:
    return re.sub(r"[\W_]+", "", value, flags=re.UNICODE).lower()


def relative_luminance(value: str) -> float:
    value = value.lstrip("#")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    light, dark = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    tools = data["tools"]
    paths = data["paths"]
    assert len(tools) == 8 and len(paths) == 4

    slugs = [item["slug"] for item in tools + paths]
    titles = [norm(item["title"]) for item in tools + paths]
    assert len(slugs) == len(set(slugs))
    assert len(titles) == len(set(titles))
    assert all(re.fullmatch(r"[a-z0-9-]+", slug) for slug in slugs)

    source_blob = DATA.read_text(encoding="utf-8").lower()
    assert not any(item in source_blob for item in BANNED)
    assert all(len(tool["steps"]) >= 4 and len(tool["save_fields"]) >= 3 and tool["safety"] for tool in tools)
    tool_slugs = {tool["slug"] for tool in tools}
    assert all(len(path["days"]) >= 5 and set(path["related_tools"]) <= tool_slugs for path in paths)
    sleep_context_paths = [path for path in paths if SLEEP_SLUG in path["related_tools"]]
    assert len(sleep_context_paths) >= 2, [path["slug"] for path in sleep_context_paths]

    sources = data["sources"]
    assert len(sources) >= 4 and all(source["url"].startswith("https://") for source in sources)
    assert len({source["publisher"] for source in sources}) >= 2

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
        assert all(path.exists() for path in expected), [str(path) for path in expected if not path.exists()]

        for page in expected:
            text = page.read_text(encoding="utf-8")
            assert text.count("<h1>") == 1
            assert 'rel="canonical"' in text
            assert "application/ld+json" in text
            assert 'dir="rtl"' in text
            assert f'data-design="marshmallow-v{DESIGN_CONTRACT}"' in text
            assert "--mint:#e5faf5" in text and "--rose:#fff0f5" in text and "--lilac:#f2edff" in text
            assert "--peach:#fff0e8" in text and "--butter:#fff8d8" in text
            assert "text-shadow" not in text.lower()
            assert "rgba(0,0,0" not in text.replace(" ", "").lower()
            assert not any(item in text.lower() for item in BANNED)

        for tool in tools:
            text = (SITE / "daily-tools" / tool["slug"] / "index.html").read_text(encoding="utf-8")
            assert "localStorage" in text and "لا تُرسل البيانات إلى خادم" in text

        sleep_href = f"/pterminology-site/daily-tools/{SLEEP_SLUG}/"
        center = (SITE / "daily-tools" / "index.html").read_text(encoding="utf-8")
        assert center.count(f'href="{sleep_href}"') == 1
        assert center.count("أداة تفاعلية محلية") == 8
        assert "ألوانًا هادئة مع نص داكن واضح وحدود وظلال فاتحة" in center

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
        assert '"url":"https://khaledaltheeb.github.io/pterminology-site/daily-tools/"' in homepage
        assert '"url":"https://khaledaltheeb.github.io/pterminology-site/learning-paths/"' in homepage

        report = json.loads((SITE / "api" / "daily-tools-v24.json").read_text(encoding="utf-8"))
        assert report == {
            "version": 24,
            "design_contract": DESIGN_CONTRACT,
            "tools": 8,
            "paths": 4,
            "pages": 14,
            "local_only": True,
            "marshmallow_palette": True,
            "dark_text_box_shadow": False,
            "homepage_linked": True,
        }

        child = ET.parse(SITE / "sitemap-tools-paths.xml").getroot()
        assert child.tag == f"{{{NS}}}urlset"
        child_urls = child.findall(f"{{{NS}}}url")
        assert len(child_urls) == 14 and all(item.find(f"{{{NS}}}loc") is not None for item in child_urls)
        sleep_url = "https://khaledaltheeb.github.io/pterminology-site/daily-tools/sleep-wind-down-plan/"
        assert sum(
            1
            for item in child_urls
            if item.find(f"{{{NS}}}loc") is not None and item.find(f"{{{NS}}}loc").text == sleep_url
        ) == 1

        sitemap_index = ET.parse(SITE / "sitemap.xml").getroot()
        assert sitemap_index.tag == f"{{{NS}}}sitemapindex"
        target = "https://khaledaltheeb.github.io/pterminology-site/sitemap-tools-paths.xml"
        matches = [
            item.text
            for item in sitemap_index.findall(f"{{{NS}}}sitemap/{{{NS}}}loc")
            if item.text == target
        ]
        assert len(matches) == 1, matches

    print(
        json.dumps(
            {
                "tools": 8,
                "paths": 4,
                "unique_slugs": True,
                "unique_titles": True,
                "non_diagnostic": True,
                "sources": len(sources),
                "sleep_context_paths": len(sleep_context_paths),
                "design_contract": DESIGN_CONTRACT,
                "minimum_contrast_ratio": min(ratios.values()),
                "contrast_ratios": ratios,
                "production_checked": bool(SITE),
                "homepage_linked": bool(SITE),
                "sitemap_namespaces_checked": bool(SITE),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
