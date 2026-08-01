#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v176" / "choosing-mental-health-professional-ar.json"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
TARGET = SITE / "care-guides" / "choosing-mental-health-professional" / "index.html"
SITEMAP = SITE / "sitemap-care-guides.xml"


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


CSS = """
:root{--ink:#183f46;--muted:#4d6d72;--line:#c9e4e2;--accent:#0b756e;--accent2:#7a3e63;--bg:#f7fcfb;--soft:#eaf8f5;--warn:#fff3f5;--white:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:linear-gradient(145deg,#fff,var(--bg),#f6f1fb);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}
a{color:#086b66}.wrap{width:min(1080px,92%);margin:auto}.skip{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px 14px;border:2px solid var(--accent);z-index:99}.skip:focus{right:8px}
nav{display:flex;gap:10px;flex-wrap:wrap;padding:18px 0}nav a,.button{display:inline-block;padding:9px 13px;border:1px solid #8bbdb8;border-radius:12px;background:#fff;text-decoration:none;font-weight:700}
header,section,article{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:20px;padding:clamp(18px,4vw,32px);margin:15px 0;box-shadow:0 12px 34px rgba(30,95,94,.08)}
header{background:linear-gradient(135deg,#eefaf7,#fff3f8,#f3efff)}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.28;margin:.2em 0}h2{color:var(--accent2)}h3{color:var(--accent)}.lead{font-size:1.12rem;color:var(--muted)}
.notice{border-right:6px solid var(--accent2);background:var(--warn)}.good{border-right:6px solid var(--accent);background:var(--soft)}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.checklist li{margin:.45rem 0}.sources li{margin:.7rem 0}.meta{color:var(--muted);font-size:.95rem}
footer{padding:28px 0 45px;color:var(--muted)}a:focus-visible{outline:3px solid #135edb;outline-offset:4px}
@media(max-width:760px){.grid{grid-template-columns:1fr}nav{display:grid}}@media print{nav,.skip,.actions{display:none!important}body{background:#fff}header,section,article{box-shadow:none;break-inside:avoid}.checklist{break-inside:auto}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
""".strip()


def source_html(data: dict[str, Any]) -> str:
    rows = []
    for source in data["sources"]:
        rows.append(
            f'<li><a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["organization"])} — {e(source["title"])}</a>'
            f'<br><span>{e(source["use"])}</span> <small>(تم الوصول: {e(source["accessed_at"])})</small></li>'
        )
    return '<ul class="sources">' + "".join(rows) + "</ul>"


def render_section(section: dict[str, Any]) -> str:
    paragraphs = "".join(f"<p>{e(text)}</p>" for text in section.get("paragraphs", []))
    items = section.get("items", [])
    list_html = "<ul>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>" if items else ""
    return f'<section><h2>{e(section["heading"])}</h2>{paragraphs}{list_html}</section>'


def render(data: dict[str, Any]) -> str:
    canonical = BASE + "/care-guides/choosing-mental-health-professional/"
    howto_steps = [
        {
            "@type": "HowToStep",
            "position": index,
            "name": item,
            "text": item,
        }
        for index, item in enumerate(data["checklist"], start=1)
    ]
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "headline": data["title_ar"],
                "description": data["description"],
                "inLanguage": "ar",
                "url": canonical,
                "dateModified": data["reviewed_at"],
                "mainEntityOfPage": canonical,
                "isPartOf": {"@type": "WebSite", "name": "مصطلحات علم النفس", "url": BASE + "/"},
                "citation": [source["url"] for source in data["sources"]],
                "about": ["اختيار الأخصائي النفسي", "العلاج النفسي", "الصحة النفسية"],
            },
            {
                "@type": "HowTo",
                "name": "خطوات اختيار الأخصائي النفسي والاستعداد للتواصل الأول",
                "description": data["description"],
                "inLanguage": "ar",
                "url": canonical + "#checklist",
                "step": howto_steps,
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "أدلة التعامل", "item": BASE + "/care-guides/"},
                    {"@type": "ListItem", "position": 3, "name": data["title_ar"], "item": canonical},
                ],
            },
        ],
    }
    schema_json = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    links = "".join(f'<a href="{e(link["href"])}">{e(link["label"])}</a>' for link in data["internal_links"])
    checklist = "".join(f"<li>☐ {e(item)}</li>" for item in data["checklist"])
    sections = "".join(render_section(section) for section in data["sections"])
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(data["title_ar"])} | مصطلحات علم النفس</title>
<meta name="description" content="{e(data["description"])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="theme-color" content="#eaf8f5"><meta name="color-scheme" content="light">
<link rel="canonical" href="{e(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:url" content="{e(canonical)}">
<meta property="og:title" content="{e(data["title_ar"])}"><meta property="og:description" content="{e(data["description"])}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(data["title_ar"])}"><meta name="twitter:description" content="{e(data["description"])}">
<script type="application/ld+json">{schema_json}</script><style>{CSS}</style></head><body>
<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a><div class="wrap"><nav aria-label="التنقل الرئيسي">
<a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}care-guides/">أدلة التعامل</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}assessments/">المقاييس</a><a href="{BASE_PATH}trust/">الثقة والمنهج</a></nav>
<main id="main"><header><p><strong>دليل عملي لاتخاذ قرار منظم</strong></p><h1>{e(data["title_ar"])}</h1><p class="lead">{e(data["summary"])}</p>
<p class="meta"><strong>آخر مراجعة داخلية:</strong> <time datetime="{e(data["reviewed_at"])}">{e(data["reviewed_at"])}</time> · زمن القراءة التقريبي: {e(data["reading_minutes"])} دقيقة</p></header>
<section class="notice"><h2>حدود هذا الدليل</h2><p>{e(data["professional_limits"])}</p><p>لا توجد دعوى مراجعة خارجية أو اعتماد مهني لهذه الصفحة.</p></section>
{sections}
<section class="good checklist" id="checklist"><h2>قائمة تحقق قبل الحجز</h2><ul>{checklist}</ul><p class="actions"><button type="button" onclick="window.print()">طباعة القائمة</button></p></section>
<section><h2>روابط مرتبطة داخل المنصة</h2><div class="grid">{links}</div></section>
<section><h2>مصادر مؤسسية للمراجعة</h2>{source_html(data)}</section></main>
<footer><p>© مصطلحات علم النفس — محتوى تثقيفي لا يستبدل التقييم المهني أو خدمات الطوارئ المحلية.</p></footer></div></body></html>'''


def update_sitemap(url: str) -> None:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    if SITEMAP.exists():
        root = ET.parse(SITEMAP).getroot()
    else:
        root = ET.Element(f"{{{namespace}}}urlset")
    existing = {node.text for node in root.findall(f"{{{namespace}}}url/{{{namespace}}}loc")}
    if url not in existing:
        item = ET.SubElement(root, f"{{{namespace}}}url")
        ET.SubElement(item, f"{{{namespace}}}loc").text = url
        ET.SubElement(item, f"{{{namespace}}}lastmod").text = "2026-07-23"
    SITEMAP.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(SITEMAP, encoding="utf-8", xml_declaration=True)


def validate(data: dict[str, Any]) -> None:
    required = {"id", "slug", "title_ar", "description", "summary", "reviewed_at", "sections", "sources", "checklist"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"missing fields: {sorted(missing)}")
    if data["slug"] != "choosing-mental-health-professional":
        raise ValueError("unexpected slug")
    if len(data["description"]) < 120 or len(data["summary"]) < 120:
        raise ValueError("description or summary is too thin")
    if len(data["sections"]) < 9 or len(data["sources"]) < 4 or len(data["checklist"]) < 8:
        raise ValueError("guide depth contract failed")
    source_ids = [source["id"] for source in data["sources"]]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate source ids")
    if any(not source["url"].startswith("https://") for source in data["sources"]):
        raise ValueError("all sources must use HTTPS")


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate(data)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(render(data), encoding="utf-8")
    update_sitemap(BASE + "/care-guides/choosing-mental-health-professional/")
    print(json.dumps({"page": str(TARGET), "sitemap": str(SITEMAP), "sources": len(data["sources"]), "sections": len(data["sections"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
