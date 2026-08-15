#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

SITE = "https://healthrenewal.org"
SUPABASE = "https://ghljwfwqsyfnthvlzxjy.supabase.co"
SUPABASE_KEY = "sb_publishable__GMG8aQnofuk_6RLm3UfUg_fIzuSzSs"
ROOT = Path(__file__).resolve().parents[1]
SLUGS = [
    "aac-core-fringe-vocabulary-arabic",
    "aac-arabic-grid-design",
    "aac-autism-guide",
    "aac-multilingual-arabic-family-languages",
]


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def fetch_records() -> list[dict]:
    query = urllib.parse.urlencode({
        "select": "slug,title,excerpt,body_json,seo_title,seo_description,canonical_url,robots_index,robots_follow,published_at,updated_at,primary_keyword,secondary_keywords,semantic_terms,author_display_name,references_json,schema_json",
        "slug": "in.(" + ",".join(SLUGS) + ")",
        "status": "eq.published",
    })
    request = urllib.request.Request(
        f"{SUPABASE}/rest/v1/content?{query}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        rows = json.loads(response.read().decode("utf-8"))
    by_slug = {row["slug"]: row for row in rows}
    missing = [slug for slug in SLUGS if slug not in by_slug]
    if missing:
        raise SystemExit(f"Missing published AAC rows: {missing}")
    return [by_slug[slug] for slug in SLUGS]


def block_html(block: dict) -> str:
    kind = block.get("type")
    if kind == "heading":
        level = max(2, min(4, int(block.get("level", 2))))
        return f"<h{level}>{esc(block.get('text'))}</h{level}>"
    if kind == "paragraph":
        return f"<p>{esc(block.get('text'))}</p>"
    if kind == "list":
        tag = "ol" if block.get("ordered") else "ul"
        items = "".join(f"<li>{esc(item)}</li>" for item in block.get("items", []))
        return f"<{tag}>{items}</{tag}>"
    if kind == "faq":
        items = "".join(
            f"<details><summary>{esc(item.get('question'))}</summary><p>{esc(item.get('answer'))}</p></details>"
            for item in block.get("items", [])
        )
        return f'<div class="faq">{items}</div>'
    if kind == "table":
        headers = block.get("headers") or []
        rows = block.get("rows") or []
        head = "".join(f"<th>{esc(x)}</th>" for x in headers)
        body = "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in rows)
        return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    return ""


def faq_items(row: dict) -> list[dict]:
    result: list[dict] = []
    for block in (row.get("body_json") or {}).get("blocks", []):
        if block.get("type") == "faq":
            result.extend(block.get("items") or [])
    return result


def article_schema(row: dict) -> dict:
    canonical = SITE + row["canonical_url"]
    refs = row.get("references_json") or []
    graph: list[dict] = [
        {
            "@type": "Article",
            "headline": row["title"],
            "description": row.get("seo_description") or row.get("excerpt") or "",
            "inLanguage": "ar",
            "datePublished": (row.get("published_at") or "")[:10],
            "dateModified": (row.get("updated_at") or row.get("published_at") or "")[:10],
            "mainEntityOfPage": canonical,
            "citation": [r.get("url") for r in refs if isinstance(r, dict) and r.get("url")],
            "author": {"@type": "Organization", "name": row.get("author_display_name") or "منصة روافد"},
            "publisher": {"@type": "Organization", "name": "منصة روافد"},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": SITE + "/"},
                {"@type": "ListItem", "position": 2, "name": "أدلة الرعاية", "item": SITE + "/care-guides/"},
                {"@type": "ListItem", "position": 3, "name": "التواصل المعزز والبديل AAC", "item": SITE + "/care-guides/aac/"},
                {"@type": "ListItem", "position": 4, "name": row["title"], "item": canonical},
            ],
        },
    ]
    faqs = faq_items(row)
    if faqs:
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": item.get("question", ""), "acceptedAnswer": {"@type": "Answer", "text": item.get("answer", "")}}
                for item in faqs
            ],
        })
    return {"@context": "https://schema.org", "@graph": graph}


STYLE = """body{font-family:Tahoma,Arial,sans-serif;line-height:1.95;color:#173f45;background:#f7fbfa;margin:0}main{width:min(980px,92%);margin:auto;padding:30px 0 68px}header,section,aside{background:#fff;border:1px solid #cfe7e3;border-radius:20px;padding:24px;margin:16px 0}h1{font-size:clamp(2rem,5vw,3.2rem);line-height:1.35}h2{color:#075f5b;margin-top:2rem}h3{color:#246c68}a{color:#075f5b}li{margin:.5rem 0}.meta{color:#527174}.faq details{border-top:1px solid #dbeceb;padding:12px 0}.faq summary{font-weight:700;cursor:pointer}.sources li{margin:.7rem 0}.related{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.related a{display:block;border:1px solid #d4e8e5;border-radius:14px;padding:14px;text-decoration:none;background:#fbfefd}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%}th,td{border:1px solid #d5e8e5;padding:10px;text-align:right}@media(max-width:600px){header,section,aside{padding:18px}}"""


def render_article(row: dict, all_rows: list[dict]) -> str:
    canonical = SITE + row["canonical_url"]
    title = row.get("seo_title") or row["title"]
    description = row.get("seo_description") or row.get("excerpt") or ""
    body = "".join(block_html(block) for block in (row.get("body_json") or {}).get("blocks", []))
    refs = row.get("references_json") or []
    refs_html = "".join(
        f'<li><a href="{esc(ref.get("url"))}" rel="noopener noreferrer">{esc(ref.get("title") or ref.get("publisher") or "المصدر")}</a>'
        + (f' — {esc(ref.get("publisher"))}' if ref.get("publisher") else "") + "</li>"
        for ref in refs if isinstance(ref, dict) and ref.get("url")
    )
    related = "".join(
        f'<a href="{esc(other["canonical_url"])}">{esc(other["title"])}</a>'
        for other in all_rows if other["slug"] != row["slug"]
    )
    schema = json.dumps(article_schema(row), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)} | منصة روافد</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1"><link rel="canonical" href="{esc(canonical)}"><meta property="og:type" content="article"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta name="twitter:card" content="summary"><script type="application/ld+json">{schema}</script><link rel="stylesheet" href="/assets/css/theme-v10.css"><style>{STYLE}</style></head><body><main><header><p><a href="/care-guides/">أدلة الرعاية</a> ← <a href="/care-guides/aac/">التواصل المعزز والبديل AAC</a></p><h1>{esc(row['title'])}</h1><p>{esc(row.get('excerpt') or description)}</p><p class="meta">آخر مراجعة للمصادر والبنية: 2026-08-15. محتوى تثقيفي عام، ولا يغني عن التقييم الفردي لدى مختص مؤهل عند الحاجة.</p></header><section>{body}</section><section><h2>المصادر والمراجع</h2><ol class="sources">{refs_html}</ol></section><aside><h2>صفحات مرتبطة في مركز AAC</h2><div class="related"><a href="/care-guides/aac/">مركز AAC العربي</a>{related}</div></aside><aside><p><a href="/disclaimer/">إخلاء المسؤولية والتنبيهات</a> · <a href="/care-guides/">العودة إلى أدلة الرعاية</a></p></aside></main></body></html>'''


def render_hub(rows: list[dict]) -> str:
    cards = "".join(f'<article><h2><a href="{esc(row["canonical_url"])}">{esc(row["title"])}</a></h2><p>{esc(row.get("seo_description") or row.get("excerpt") or "")}</p></article>' for row in rows)
    schema = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "مركز التواصل المعزز والبديل AAC", "description": "مركز عربي علمي للتواصل المعزز والبديل AAC", "inLanguage": "ar", "url": SITE + "/care-guides/aac/"}, ensure_ascii=False)
    hub_style = STYLE + ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}.grid article{background:#fff;border:1px solid #cfe7e3;border-radius:20px;padding:20px}"
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>التواصل المعزز والبديل AAC: مركز روافد العربي</title><meta name="description" content="مركز عربي علمي شامل للتواصل المعزز والبديل AAC يغطي المفردات وتصميم الأنظمة والتوحد والعربية والتعدد اللغوي بمصادر موثوقة وأدلة عملية."><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1"><link rel="canonical" href="{SITE}/care-guides/aac/"><script type="application/ld+json">{schema}</script><link rel="stylesheet" href="/assets/css/theme-v10.css"><style>{hub_style}</style></head><body><main><header><p><a href="/care-guides/">أدلة الرعاية</a></p><h1>مركز التواصل المعزز والبديل AAC</h1><p>مسار عربي موسع لفهم التواصل المعزز والبديل واختياره وتصميمه واستخدامه في الحياة اليومية، مع اهتمام خاص باللغة العربية واللهجات والتعدد اللغوي والمدرسة والاستقلال وحقوق المستخدم.</p><p class="meta">آخر تحديث: 2026-08-15.</p></header><section><h2>الصفحات المرجعية المنشورة</h2><p>المركز مبني حول نوايا بحث مستقلة ومتكاملة، مع ربط داخلي يمنع تكرار الموضوع نفسه في صفحات متنافسة.</p></section><div class="grid">{cards}</div><section><h2>منهج المركز</h2><p>لا يروّج المركز لجهاز أو تطبيق بعينه. الاختيار يبدأ من وظيفة التواصل، وقدرات الوصول، واللغة، والبيئة، وشركاء التواصل. وستُستكمل الصفحات بالتقييم والنمذجة وPECS وأجهزة توليد الكلام والقراءة والكتابة والوصول الحركي والنظر والمدرسة والرعاية الصحية والطوارئ.</p></section><section><p><a href="/care-guides/">العودة إلى أدلة الرعاية</a> · <a href="/disclaimer/">إخلاء المسؤولية والتنبيهات</a></p></section></main></body></html>'''


def ensure_main_sitemap(urls: list[str]) -> None:
    path = ROOT / "sitemap.xml"
    text = path.read_text(encoding="utf-8")
    additions = "".join(f"  <url>\n    <loc>{url}</loc>\n    <lastmod>2026-08-15</lastmod>\n  </url>\n" for url in urls if f"<loc>{url}</loc>" not in text)
    if additions:
        text = text.replace("</urlset>", additions + "</urlset>")
        path.write_text(text, encoding="utf-8")


def ensure_hub_link() -> None:
    path = ROOT / "care-guides" / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    if 'href="/care-guides/aac/"' in text:
        return
    block = '<section id="aac-center-link"><h2>التواصل المعزز والبديل AAC</h2><p>مركز عربي متخصص في تقييم واختيار وتصميم واستخدام AAC، مع مسارات للتوحد والعربية والتعدد اللغوي.</p><p><a href="/care-guides/aac/">استكشف مركز AAC</a></p></section>'
    if "</main>" in text:
        text = text.replace("</main>", block + "</main>", 1)
    else:
        text = text.replace("</body>", block + "</body>", 1)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    rows = fetch_records()
    target = ROOT / "care-guides" / "aac"
    target.mkdir(parents=True, exist_ok=True)
    (target / "index.html").write_text(render_hub(rows), encoding="utf-8")
    urls = [SITE + "/care-guides/aac/"]
    for row in rows:
        canonical = row["canonical_url"]
        match = re.fullmatch(r"/care-guides/aac/([a-z0-9-]+)/", canonical)
        if not match:
            raise SystemExit(f"Unexpected canonical: {canonical}")
        folder = target / match.group(1)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(render_article(row, rows), encoding="utf-8")
        urls.append(SITE + canonical)
    sitemap = "<?xml version='1.0' encoding='utf-8'?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n" + "".join(f"  <url><loc>{url}</loc><lastmod>2026-08-15</lastmod></url>\n" for url in urls) + "</urlset>\n"
    (ROOT / "sitemap-aac.xml").write_text(sitemap, encoding="utf-8")
    robots = ROOT / "robots.txt"
    robots_text = robots.read_text(encoding="utf-8")
    aac_sitemap = f"Sitemap: {SITE}/sitemap-aac.xml"
    if aac_sitemap not in robots_text:
        robots.write_text(robots_text.rstrip() + "\n" + aac_sitemap + "\n", encoding="utf-8")
    ensure_main_sitemap(urls)
    ensure_hub_link()
    print(json.dumps({"materialized": [row["canonical_url"] for row in rows], "hub": "/care-guides/aac/", "sitemap": "/sitemap-aac.xml"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
