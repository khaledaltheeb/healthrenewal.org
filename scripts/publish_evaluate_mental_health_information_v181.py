from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v181" / "evaluate-mental-health-information-ar.json"
BASE = "https://healthrenewal.org/"
ROUTE = "/evaluate-mental-health-information/"


def render() -> str:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    sections = "".join(
        f'<section><h2>{escape(section["heading"])}</h2>'
        + "".join(f"<p>{escape(p)}</p>" for p in section["paragraphs"])
        + "</section>"
        for section in data["sections"]
    )
    checklist = "".join(f"<li>{escape(item)}</li>" for item in data["decision_checklist"])
    red_flags = "".join(f"<li>{escape(item)}</li>" for item in data["red_flags"])
    sources = "".join(
        f'<li><a href="{escape(item["url"])}" rel="noopener noreferrer">{escape(item["publisher"])} — {escape(item["title"])}</a></li>'
        for item in data["sources"]
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
                "@id": f"{BASE}{ROUTE}#article",
                "headline": data["title"],
                "description": data["description"],
                "inLanguage": "ar",
                "dateModified": data["reviewed_at"],
                "mainEntityOfPage": f"{BASE}{ROUTE}",
                "citation": [item["url"] for item in data["sources"]],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": "تقييم المعلومات النفسية", "item": f"{BASE}{ROUTE}"},
                ],
            },
        ],
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(data["title"])}</title><meta name="description" content="{escape(data["description"])}">
<link rel="canonical" href="{BASE}{ROUTE}"><meta name="robots" content="index,follow">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{escape(data["title"])}"><meta property="og:description" content="{escape(data["description"])}"><meta property="og:url" content="{BASE}{ROUTE}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{escape(data["title"])}"><meta name="twitter:description" content="{escape(data["description"])}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>body{{font-family:system-ui;line-height:1.9;margin:0;background:#f7faf9;color:#17333a}}main{{max-width:920px;margin:auto;padding:32px 18px}}header,section,aside{{background:#fff;border:1px solid #d8e3df;border-radius:16px;padding:22px;margin:16px 0}}a{{color:#075d64;font-weight:700}}.note{{border-inline-start:5px solid #a27617}}.danger{{border-inline-start:5px solid #9d2d2d}}@media print{{nav,.skip{{display:none}}body{{background:#fff}}}}</style></head>
<body><a class="skip" href="#content">تجاوز إلى المحتوى</a><main id="content"><nav><a href="/">الرئيسية</a> ← تقييم المعلومات النفسية</nav>
<header><p>دليل التحقق الرقمي</p><h1>{escape(data["title"])}</h1><p>{escape(data["summary"])}</p></header>
<aside class="note"><h2>حدود الاستخدام</h2><p>هذا الدليل يساعد على تقييم جودة المعلومات، ولا يشخّص حالة ولا يستبدل تقييمًا مهنيًا. لا تبدأ دواءً أو توقفه أو تغيّر جرعته اعتمادًا على محتوى الإنترنت.</p></aside>
{sections}
<section><h2>قائمة قرار قبل الثقة أو المشاركة</h2><ol>{checklist}</ol></section>
<aside class="danger"><h2>إشارات تستدعي التوقف والتحقق</h2><ul>{red_flags}</ul></aside>
<section><h2>مصادر مؤسسية للمراجعة</h2><ul>{sources}</ul></section>
<aside><h2>مسارات مرتبطة</h2><ul>{links}</ul></aside>
<footer><p>آخر مراجعة داخلية: {escape(data["reviewed_at"])}</p></footer></main></body></html>'''


def main() -> None:
    target = SITE / ROUTE.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(), encoding="utf-8")
    (SITE / "sitemap-evaluate-mental-health-information.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}{ROUTE}</loc></url></urlset>\n',
        encoding="utf-8",
    )
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "evaluate-mental-health-information-v181.json").write_text(
        json.dumps({"page": ROUTE, "sitemap": "/sitemap-evaluate-mental-health-information.xml", "status": "built-not-published"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
