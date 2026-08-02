#!/usr/bin/env python3
"""Render every source-registry record as indexable static HTML."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "source-registry" / "index.html"
REGISTRY = ROOT / "api" / "source-registry.json"
START = "<!-- source-registry-static-v2:start -->"
END = "<!-- source-registry-static-v2:end -->"


def source_card(source: dict[str, object]) -> str:
    name = html.escape(str(source.get("name") or "مصدر رسمي"))
    name_ar = html.escape(str(source.get("name_ar") or name))
    url = html.escape(str(source.get("url") or ""), quote=True)
    category = html.escape(str(source.get("category") or "مصدر مؤسسي"))
    intended_use = html.escape(str(source.get("intended_use") or "مرجع مرشح قيد التحقق."))
    return (
        '<article class="source">'
        '<div class="tags"><span class="tag pending">مرشح قيد التحقق</span>'
        f'<span class="tag">{category}</span></div>'
        f'<h3><a href="{url}" rel="external noopener">{name_ar}</a></h3>'
        f'<p class="latin" lang="en">{name}</p>'
        f"<p>{intended_use}</p>"
        f'<a class="official" href="{url}" rel="external noopener">الموقع الرسمي</a>'
        "</article>"
    )


def main() -> None:
    markup = PAGE.read_text(encoding="utf-8")
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if not isinstance(sources, list) or len(sources) != 50:
        raise SystemExit("Source registry must contain exactly 50 records")

    marker_pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        flags=re.DOTALL,
    )
    markup = marker_pattern.sub("", markup)
    existing_urls = set(re.findall(r'href="(https://[^"]+)"', markup))
    missing = [
        source
        for source in sources
        if isinstance(source, dict) and str(source.get("url") or "") not in existing_urls
    ]
    cards = "\n".join(source_card(source) for source in missing)
    generated = (
        f"{START}\n"
        '<section aria-labelledby="expanded-source-registry-title">'
        '<h2 id="expanded-source-registry-title">مصادر إضافية في السجل الموسع</h2>'
        f'<div class="grid">\n{cards}\n</div></section>\n'
        f"{END}\n"
    )
    anchor = '<section class="api-box">'
    if anchor not in markup:
        raise SystemExit("Source registry API section is missing")
    markup = markup.replace(anchor, generated + anchor, 1)

    replacements = {
        "يضم 25 مصدرًا": "يضم 50 مصدرًا",
        "25 مصدرًا رسميًا": "50 مصدرًا رسميًا",
        '"numberOfItems":25': '"numberOfItems":50',
        '"dateModified":"2026-07-30"': '"dateModified":"2026-08-02"',
    }
    for old, new in replacements.items():
        markup = markup.replace(old, new)

    if re.search(r'<meta\b[^>]*\bname\s*=\s*["\']keywords["\']', markup, re.I):
        raise SystemExit("Obsolete meta keywords must not be published")
    if markup.count('<article class="source">') != 50:
        raise SystemExit(
            f"Expected 50 static source cards, found {markup.count('<article class=\"source\">')}"
        )
    if "khaledaltheeb.github.io/pterminology-site" in markup:
        raise SystemExit("Legacy project-path URL remains in source registry")

    PAGE.write_text(markup, encoding="utf-8")
    print(json.dumps({"sources": 50, "new_static_cards": len(missing)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
