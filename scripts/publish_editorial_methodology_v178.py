from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v178" / "editorial-methodology-ar.json"
BASE = "https://healthrenewal.org/"


def render() -> str:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    sections = "".join(
        f'<section><h2>{escape(section["heading"])}</h2>'
        + "".join(f"<p>{escape(p)}</p>" for p in section["paragraphs"])
        + "</section>"
        for section in data["sections"]
    )
    links = "".join(
        f'<li><a href="{escape(item["href"])}">{escape(item["title"])}</a></li>'
        for item in data["related_links"]
    )
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "@id": f"{BASE}/editorial-methodology/#article",
                "headline": data["title"],
                "description": data["description"],
                "inLanguage": "ar",
                "dateModified": data["reviewed_at"],
                "mainEntityOfPage": f"{BASE}/editorial-methodology/",
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": "منهجية المحتوى", "item": f"{BASE}/editorial-methodology/"},
                ],
            },
        ],
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(data["title"])}</title><meta name="description" content="{escape(data["description"])}">
<link rel="canonical" href="{BASE}/editorial-methodology/"><meta name="robots" content="index,follow">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{escape(data["title"])}"><meta property="og:description" content="{escape(data["description"])}"><meta property="og:url" content="{BASE}/editorial-methodology/">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{escape(data["title"])}"><meta name="twitter:description" content="{escape(data["description"])}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>body{{font-family:system-ui;line-height:1.9;margin:0;background:#fbfaf6;color:#17333a}}main{{max-width:900px;margin:auto;padding:32px 18px}}header,section,aside{{background:#fff;border:1px solid #d8e3df;border-radius:16px;padding:22px;margin:16px 0}}a{{color:#075d64;font-weight:700}}.status{{border-inline-start:5px solid #a27617}}@media print{{nav,.skip{{display:none}}body{{background:#fff}}}}</style></head>
<body><a class="skip" href="#content">تجاوز إلى المحتوى</a><main id="content"><nav><a href="/">الرئيسية</a> ← منهجية المحتوى</nav>
<header><p>الشفافية والتحرير</p><h1>{escape(data["title"])}</h1><p>{escape(data["description"])}</p></header>
<aside class="status"><h2>حالة هذه الصفحة</h2><p>مراجعة داخلية بتاريخ {escape(data["reviewed_at"])}. لا تدعي مراجعة اختصاصي خارجي أو اعتمادًا مهنيًا.</p></aside>
{sections}<aside><h2>مسارات مرتبطة</h2><ul>{links}</ul></aside>
<footer><p>آخر مراجعة: {escape(data["reviewed_at"])}</p></footer></main></body></html>'''


def main() -> None:
    target = SITE / "editorial-methodology" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(), encoding="utf-8")
    sitemap = SITE / "sitemap-editorial-methodology.xml"
    sitemap.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}/editorial-methodology/</loc></url></urlset>\n',
        encoding="utf-8",
    )
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "editorial-methodology-v178.json").write_text(
        json.dumps({"page": "/editorial-methodology/", "sitemap": "/sitemap-editorial-methodology.xml", "status": "built-not-published"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
