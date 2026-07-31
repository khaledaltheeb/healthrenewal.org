from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v192" / "platform-institutional-foundation-ar.json"
BASE_URL = "https://healthrenewal.org/"
SITEMAP_NAME = "sitemap-institutional-foundation.xml"
START = "<!-- institutional-footer-v192:start -->"
END = "<!-- institutional-footer-v192:end -->"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_content() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    required = {"platform_name", "short_name", "legacy_name", "mission", "magazine", "partners", "footer", "sources", "status", "reviewed_at", "risk_level"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing institutional fields: {sorted(missing)}")
    if data["status"] != "internally-reviewed" or data["risk_level"] != "low":
        raise SystemExit("Institutional foundation must remain internally-reviewed and low-risk")
    return data


def schemas(data: dict, page: dict, page_type: str) -> str:
    canonical = f'{BASE_URL}/{page["slug"]}/'
    graph = [
        {
            "@type": "Organization",
            "@id": f"{BASE_URL}/#organization",
            "name": data["platform_name"],
            "alternateName": [data["legacy_name"], data["short_name"]],
            "url": f"{BASE_URL}/",
        },
        {
            "@type": page_type,
            "@id": f"{canonical}#page",
            "url": canonical,
            "name": page["title"],
            "description": page["description"],
            "inLanguage": "ar",
            "dateModified": data["reviewed_at"],
            "isPartOf": {"@type": "WebSite", "@id": f"{BASE_URL}/#website", "name": data["platform_name"]},
            "publisher": {"@id": f"{BASE_URL}/#organization"},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE_URL}/"},
                {"@type": "ListItem", "position": 2, "name": page["title"], "item": canonical},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)


def render_sections(sections: list[dict]) -> str:
    return "".join(
        f'<section class="institutional-card"><h2>{esc(section["heading"])}</h2>'
        + "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
        + "</section>"
        for section in sections
    )


def render_page(data: dict, page: dict, page_type: str, extra: str) -> str:
    canonical = f'{BASE_URL}/{page["slug"]}/'
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(page["title"])} | {esc(data["short_name"])}</title>
<meta name="description" content="{esc(page["description"])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{canonical}"><meta name="color-scheme" content="light">
<meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:url" content="{canonical}"><meta property="og:title" content="{esc(page["title"])}"><meta property="og:description" content="{esc(page["description"])}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(page["title"])}"><meta name="twitter:description" content="{esc(page["description"])}">
<script type="application/ld+json">{schemas(data, page, page_type)}</script>
<style>:root{{--ink:#173f45;--muted:#496d70;--surface:#fff;--soft:#eef9f7;--line:#b9ddd8;--accent:#075d64;--gold:#805600}}*{{box-sizing:border-box}}body{{margin:0;background:#f8fbfa;color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}}a{{color:var(--accent);font-weight:700}}a:focus-visible,input:focus-visible{{outline:3px solid #805600;outline-offset:4px}}.skip{{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px;border:2px solid var(--accent)}}.skip:focus{{right:8px}}main{{width:min(980px,92%);margin:auto;padding:36px 0 64px}}nav{{margin-bottom:24px}}header,.institutional-card,.notice{{background:var(--surface);border:1px solid var(--line);border-radius:18px;padding:22px;margin:16px 0}}h1{{font-size:clamp(2rem,5vw,3.4rem);line-height:1.25}}h2{{font-size:clamp(1.35rem,3vw,2rem);line-height:1.4}}.lead{{font-size:1.12rem;color:var(--muted)}}.notice{{border-inline-start:6px solid var(--gold)}}li{{margin:.55rem 0}}@media print{{.skip,nav{{display:none}}body{{background:#fff}}main{{width:100%;padding:0}}header,.institutional-card,.notice{{break-inside:avoid;border-color:#777}}}}</style></head>
<body><a class="skip" href="#content">انتقل إلى المحتوى</a><main id="content"><nav aria-label="مسار الصفحة"><a href="/">الرئيسية</a> ← {esc(page["title"])}</nav>
<header><p>{esc(data["platform_name"])}</p><h1>{esc(page["title"])}</h1><p class="lead">{esc(page["summary"])}</p></header>
{render_sections(page["sections"])}{extra}
<section class="notice"><h2>حالة الصفحة وحدودها</h2><p>الحالة التحريرية: مراجعة داخلية منخفضة المخاطر. آخر تحقق: {esc(data["reviewed_at"])}. لا توجد دعوى مراجعة اختصاصية خارجية أو اعتماد رسمي.</p></section>
</main></body></html>'''


def magazine_extra(data: dict) -> str:
    checklist = "".join(f"<li>{esc(item)}</li>" for item in data["magazine"]["publication_checklist"])
    sources = "".join(
        f'<li><a rel="noopener" href="{esc(source["url"])}">{esc(source["title"])}</a> — {esc(source["publisher"])} ({esc(source["year"])})</li>'
        for source in data["sources"]
    )
    return f'''<section class="institutional-card"><h2>حالة النشر الحالية</h2><p>لم تُنشر في هذه الحزمة ملخصات دراسات منفردة بعد. تبدأ المجلة بالمنهج والعقد التحريري، ثم تدخل كل دراسة في Queue مستقلة ولا تظهر كمنشورة قبل فحص المصدر والبوابات والنسخة الحية.</p></section>
<section class="institutional-card"><h2>قائمة فحص كل ملخص علمي</h2><ol>{checklist}</ol></section>
<section class="institutional-card"><h2>مصادر بناء المنهج</h2><ul>{sources}</ul></section>'''


def partners_extra() -> str:
    return '''<section class="institutional-card"><h2>السجل المعلن حاليًا</h2><p><strong>المانحون المعلنون:</strong> لا يوجد.</p><p><strong>الشركاء الرسميون المعلنون:</strong> لا يوجد.</p><p><strong>المراجعون الخارجيون المعلنون:</strong> لا يوجد.</p><p>هذه العبارات مقصودة لمنع الإيحاء بعلاقات غير موثقة، وستتغير فقط بعد اتفاق وموافقة وإفصاح قابل للتدقيق.</p></section>'''


def footer_fragment(data: dict) -> str:
    footer = data["footer"]
    links = " · ".join(f'<a href="{esc(item["href"])}">{esc(item["label"])}</a>' for item in footer["links"])
    return f'''{START}<section class="institutional-footer-v192" aria-label="معلومات المنصة والحقوق"><style>.institutional-footer-v192{{margin-top:2rem;padding:1.5rem;border-top:2px solid #b9ddd8;background:#f8fbfa;color:#173f45;line-height:1.8}}.institutional-footer-v192 a{{color:#075d64;font-weight:700}}.institutional-footer-v192 p{{max-width:1100px;margin:.55rem auto}}</style><p><strong>{esc(data["platform_name"])}</strong> — الاسم المؤسس: {esc(data["legacy_name"])}.</p><p>{esc(footer["copyright"])}</p><p>{esc(footer["medical_notice"])}</p><p>{esc(footer["transparency_notice"])}</p><p>{links}</p></section>{END}'''


def inject_footer(path: Path, fragment: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if re.match(r"^(google-site-verification|msvalidate\.01|p:domain_verify)", text.strip(), re.I):
        return False
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), "", text, flags=re.S)
    if "</footer>" in text:
        text = text.replace("</footer>", fragment + "</footer>", 1)
    elif "</body>" in text:
        text = text.replace("</body>", f'<footer aria-label="تذييل المنصة">{fragment}</footer></body>', 1)
    else:
        text += f'<footer aria-label="تذييل المنصة">{fragment}</footer>'
    path.write_text(text, encoding="utf-8")
    return True


def update_homepage(path: Path, data: dict) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<title>.*?</title>", f'<title>{esc(data["platform_name"])} | معرفة عربية موثقة وعملية</title>', text, count=1, flags=re.S)
    text = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(data["mission"])}">', text, count=1)
    text = re.sub(r'(<meta property="og:title" content=")[^"]*(">)', rf'\1{esc(data["platform_name"])}\2', text, count=1)
    text = re.sub(r'(<meta name="twitter:title" content=")[^"]*(">)', rf'\1{esc(data["platform_name"])}\2', text, count=1)
    text = text.replace('class="brand" href="./">مصطلحات علم النفس</a>', f'class="brand" href="./">{esc(data["short_name"])}</a>', 1)
    if 'href="magazine/"' not in text:
        text = text.replace('</nav></header>', '<a href="magazine/">المجلة</a><a href="partners/">الشركاء</a></nav></header>', 1)
    path.write_text(text, encoding="utf-8")


def publish(site: Path) -> dict:
    data = load_content()
    outputs = []
    magazine = site / data["magazine"]["slug"] / "index.html"
    partners = site / data["partners"]["slug"] / "index.html"
    for output in (magazine, partners):
        output.parent.mkdir(parents=True, exist_ok=True)
    magazine.write_text(render_page(data, data["magazine"], "CollectionPage", magazine_extra(data)), encoding="utf-8")
    partners.write_text(render_page(data, data["partners"], "AboutPage", partners_extra()), encoding="utf-8")
    outputs.extend([magazine, partners])
    update_homepage(site / "index.html", data)
    fragment = footer_fragment(data)
    injected = sum(1 for path in site.rglob("*.html") if inject_footer(path, fragment))
    urls = [f'{BASE_URL}/{data["magazine"]["slug"]}/', f'{BASE_URL}/{data["partners"]["slug"]}/']
    sitemap = site / SITEMAP_NAME
    sitemap.write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join(f'<url><loc>{url}</loc><lastmod>{data["reviewed_at"]}</lastmod></url>' for url in urls) + '</urlset>\n', encoding="utf-8")
    report = {
        "status": "built-not-published",
        "version": 192,
        "pages": ["/magazine/", "/partners/"],
        "footer_pages": injected,
        "sitemap": f"/{SITEMAP_NAME}",
        "platform_name": data["platform_name"],
        "review": data["status"],
        "risk_level": data["risk_level"],
        "declared_partners": 0,
        "declared_donors": 0,
        "published_research_summaries": 0,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "institutional-foundation-v192.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
