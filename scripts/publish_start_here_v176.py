from __future__ import annotations

import json
import subprocess
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v176" / "start-here-ar.json"
BASE = "https://healthrenewal.org/"


def render() -> str:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    cards = "".join(
        f'<article class="card"><h2>{escape(item["title"])}</h2>'
        f'<p>{escape(item["summary"])}</p>'
        f'<a href="{escape(item["href"])}">{escape(item["label"])}</a></article>'
        for item in data["sections"]
    )
    steps = "".join(f"<li>{escape(item)}</li>" for item in data["decision_steps"])
    rules = "".join(f"<li>{escape(item)}</li>" for item in data["quality_rules"])
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebPage",
                "@id": f"{BASE}/start-here/#webpage",
                "url": f"{BASE}/start-here/",
                "name": data["title"],
                "description": data["description"],
                "inLanguage": "ar",
                "dateModified": data["reviewed_at"],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"},
                    {"@type": "ListItem", "position": 2, "name": "ابدأ من هنا", "item": f"{BASE}/start-here/"},
                ],
            },
        ],
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(data["title"])}</title><meta name="description" content="{escape(data["description"])}">
<link rel="canonical" href="{BASE}/start-here/"><meta name="robots" content="index,follow">
<meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{escape(data["title"])}"><meta property="og:description" content="{escape(data["description"])}"><meta property="og:url" content="{BASE}/start-here/">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{escape(data["title"])}"><meta name="twitter:description" content="{escape(data["description"])}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>body{{font-family:system-ui;line-height:1.8;margin:0;background:#fbfaf6;color:#17333a}}main{{max-width:1100px;margin:auto;padding:32px 18px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}.card,section{{background:white;border:1px solid #d8e3df;border-radius:16px;padding:20px}}a{{color:#075d64;font-weight:700}}.notice{{border-inline-start:5px solid #a27617}}.actions{{display:flex;gap:10px;flex-wrap:wrap}}.button{{display:inline-block;padding:10px 14px;border:1px solid #7fb8b1;border-radius:13px;background:#fff;text-decoration:none;font-weight:800}}@media print{{nav,.no-print{{display:none}}body{{background:white}}}}</style></head>
<body><a class="no-print" href="#content">تجاوز إلى المحتوى</a><main id="content"><nav><a href="/">الرئيسية</a> ← ابدأ من هنا</nav>
<header><p>بوابة توجيهية</p><h1>{escape(data["title"])}</h1><p>{escape(data["description"])}</p></header>
<div class="grid">{cards}</div><section><h2>كيف تختار نقطة البداية؟</h2><ol>{steps}</ol></section>
<section class="notice"><h2>حدود الاستخدام</h2><ul>{rules}</ul><p>هذه الصفحة تنظّم الوصول إلى المحتوى ولا تقدم تشخيصًا أو خطة علاج شخصية.</p></section>
<footer><p>آخر مراجعة: {escape(data["reviewed_at"])}</p></footer></main></body></html>'''


def main() -> None:
    target = SITE / "start-here" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(), encoding="utf-8")
    sitemap = SITE / "sitemap-start-here.xml"
    sitemap.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}/start-here/</loc></url></urlset>\n', encoding="utf-8")
    homepage = SITE / "index.html"
    if homepage.exists():
        text = homepage.read_text(encoding="utf-8")
        marker = '<a href="start-here/">ابدأ من هنا</a>'
        if marker not in text:
            text = text.replace("</main>", f'<section id="start-here"><h2>لا تعرف من أين تبدأ؟</h2><p>اختر المسار الأنسب لسؤالك بدل التنقل بين صفحات متشابهة.</p>{marker}</section></main>', 1)
            homepage.write_text(text, encoding="utf-8")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "start-here-v176.json").write_text(json.dumps({"page": "/start-here/", "sitemap": "/sitemap-start-here.xml", "status": "built-not-published"}, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "publish_audience_resource_pathways_v184.py"), str(SITE)],
        check=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "finalize_audience_resource_pathways_v184.py"), str(SITE)],
        check=True,
    )


if __name__ == "__main__":
    main()
