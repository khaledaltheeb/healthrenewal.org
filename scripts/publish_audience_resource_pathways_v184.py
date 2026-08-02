from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v184" / "audience-resource-pathways-ar.json"
BASE = "https://healthrenewal.org"
BASE_PATH = "/"


def e(value: Any) -> str:
    return escape(str(value), quote=True)


CSS = """
:root{--ink:#173f45;--muted:#4b6e71;--line:#c7e8e3;--accent:#08776e;--accent2:#8b3f64;--pink:#fff0f6;--mint:#eafff5;--turq:#e7fbf8;--lilac:#f0edff;--white:#fff;--yellow:#fff8d9}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:var(--ink);background:linear-gradient(145deg,#fff9fc,var(--turq),var(--lilac))}a{color:#086e69}.wrap{width:min(1120px,92%);margin:auto}.skip{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px 14px;border:2px solid var(--accent);border-radius:12px;z-index:99}.skip:focus{right:8px}.nav,.actions{display:flex;gap:10px;flex-wrap:wrap}.nav a,.button{display:inline-block;padding:10px 14px;border:1px solid #7fb8b1;border-radius:13px;background:#fff;text-decoration:none;font-weight:800}header,section,article{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:22px;padding:clamp(18px,4vw,34px);margin:16px 0;box-shadow:0 16px 42px rgba(42,119,118,.09)}header{background:linear-gradient(135deg,var(--pink),var(--turq),var(--lilac))}h1{font-size:clamp(2rem,5.5vw,3.8rem);line-height:1.28;margin:.2em 0}h2{color:var(--accent2)}h3{color:var(--accent)}.lead{font-size:1.12rem;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{display:flex;flex-direction:column}.card p{flex:1;color:var(--muted)}.notice{border-right:6px solid var(--accent2);background:var(--pink)}.review{border-right:6px solid var(--accent);background:var(--mint)}.visual{border-top:12px solid var(--accent);background:linear-gradient(180deg,#fff,var(--yellow))}.number{display:inline-grid;place-items:center;width:2.2rem;height:2.2rem;border:2px solid var(--accent);border-radius:50%;font-weight:900;margin-left:.5rem}.worksheet{background:#fff}.prompt{border:1px dashed #6ea9a2;border-radius:14px;padding:14px;margin:12px 0}.lines{height:5.5rem;background:repeating-linear-gradient(to bottom,transparent 0,transparent 1.65rem,#b9d8d4 1.68rem,#b9d8d4 1.72rem)}.check{display:flex;gap:.7rem;align-items:flex-start}.check input{inline-size:1.2rem;block-size:1.2rem;margin-top:.45rem}footer{padding:28px 0 48px;color:var(--muted)}a:focus-visible,input:focus-visible{outline:3px solid #1b6cff;outline-offset:4px}@media(max-width:850px){.grid,.cards{grid-template-columns:1fr}.nav{display:grid}}@media print{.nav,.actions,.skip,.no-print{display:none!important}body{background:#fff}header,section,article{box-shadow:none;break-inside:avoid}.worksheet{border:0;padding:0}.prompt{break-inside:avoid}.lines{height:7rem}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
""".strip()


def internal_href(href: str) -> str:
    if href.startswith("https://"):
        return href
    return BASE_PATH + href.lstrip("/")


def head(title: str, description: str, canonical: str, page_type: str = "WebPage") -> str:
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": page_type,
                "name": title,
                "description": description,
                "inLanguage": "ar",
                "url": canonical,
                "dateModified": "2026-07-23",
                "isPartOf": {"@type": "WebSite", "name": "مصطلحات علم النفس", "url": BASE + "/"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                    {"@type": "ListItem", "position": 2, "name": title, "item": canonical},
                ],
            },
        ],
    }
    schema_json = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    return f'''<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title><meta name="description" content="{e(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#72d8cf"><meta name="color-scheme" content="light"><link rel="canonical" href="{e(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:url" content="{e(canonical)}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(description)}"><script type="application/ld+json">{schema_json}</script><style>{CSS}</style></head>'''


def nav() -> str:
    return f'''<nav class="nav" aria-label="التنقل الرئيسي"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}start-here/">ابدأ من هنا</a><a href="{BASE_PATH}audiences/">المسارات</a><a href="{BASE_PATH}resources/">المواد العملية</a><a href="{BASE_PATH}resources/infographics/">الإنفوجرافيك</a><a href="{BASE_PATH}terms/">القاموس</a><a href="{BASE_PATH}special-needs/">ذوو الإعاقة</a><a href="{BASE_PATH}trust/">الثقة والمنهج</a></nav>'''


def shell(title: str, description: str, canonical: str, body: str, page_type: str = "WebPage") -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl">{head(title, description, canonical, page_type)}<body><a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a><div class="wrap">{nav()}<main id="main">{body}</main><footer><p>مصطلحات علم النفس — محتوى تثقيفي منظم، لا يستبدل التقييم أو العلاج أو خدمات الطوارئ المحلية.</p></footer></div></body></html>'''


def render_audience_index(data: dict[str, Any]) -> str:
    cards = "".join(
        f'<article class="card"><h2>{e(item["title"])}</h2><p>{e(item["summary"])}</p><a class="button" href="{BASE_PATH}audiences/{e(item["slug"])}/">فتح المسار</a></article>'
        for item in data["audiences"]
    )
    formats = "".join(
        f'<article class="card"><h3>{e(item["title"])}</h3><p>{e(item["summary"])}</p><a href="{e(internal_href("/resources/" if item["id"] == "plain-language" else item["href"]))}">فتح القسم</a></article>'
        for item in data["content_formats"]
    )
    body = f'''<header><p><strong>خمسة مسارات واضحة</strong></p><h1>{e(data["title"])}</h1><p class="lead">{e(data["description"])}</p><p><strong>آخر مراجعة:</strong> <time datetime="{e(data["reviewed_at"])}">{e(data["reviewed_at"])}</time></p></header><section><h2>اختر حسب دورك</h2><div class="grid">{cards}</div></section><section><h2>اختر شكل المحتوى</h2><div class="cards">{formats}</div></section><section class="notice"><h2>حدود الاستخدام</h2><p>{e(data["safety_note"])}</p></section>'''
    return shell(data["title"], data["description"], BASE + "/audiences/", body, "CollectionPage")


def render_audience_page(data: dict[str, Any], audience: dict[str, Any]) -> str:
    goals = "".join(f"<li>{e(item)}</li>" for item in audience["goals"])
    routes = "".join(
        f'<article class="card"><h2>{e(route["label"])}</h2><p>انتقل إلى هذا القسم عندما يتطابق مع هدفك الحالي، ثم استخدم الروابط الداخلية بدل فتح صفحات كثيرة متشابهة.</p><a class="button" href="{e(internal_href(route["href"]))}">فتح القسم</a></article>'
        for route in audience["routes"]
    )
    body = f'''<header><p><strong>مسار مستخدم</strong></p><h1>{e(audience["title"])}</h1><p class="lead">{e(audience["summary"])}</p></header><section><h2>ما الذي يساعدك هذا المسار على إنجازه؟</h2><ul>{goals}</ul></section><section><h2>الخطوات المقترحة</h2><div class="grid">{routes}</div></section><section class="notice"><h2>قبل استخدام المحتوى</h2><p>{e(data["safety_note"])}</p></section>'''
    canonical = BASE + f'/audiences/{audience["slug"]}/'
    return shell(audience["title"] + " | مصطلحات علم النفس", audience["summary"], canonical, body)


def render_resources_index(data: dict[str, Any]) -> str:
    formats = "".join(
        f'<article class="card"><h2>{e(item["title"])}</h2><p>{e(item["summary"])}</p><a class="button" href="{e(internal_href(item["href"]))}">فتح القسم</a></article>'
        for item in data["content_formats"]
    )
    plain = "".join(f"<li>{e(item)}</li>" for item in data["plain_language_contract"]["required_blocks"])
    dictionary = "".join(f"<li>{e(item)}</li>" for item in data["dictionary_contract"]["required_fields"])
    body = f'''<header><p><strong>مكتبة المواد العملية</strong></p><h1>الشرح المبسط والقاموس والإنفوجرافيك وأوراق العمل</h1><p class="lead">مواد منظمة تساعد القارئ والأسرة والمعلم والطالب والمختص على الوصول إلى الشكل المناسب من المحتوى دون خلط التثقيف بالتشخيص.</p></header><section><h2>الأقسام</h2><div class="grid">{formats}</div></section><section><h2>عقد الشرح المبسط</h2><ul>{plain}</ul></section><section><h2>عقد القاموس العربي–الإنجليزي</h2><ul>{dictionary}</ul><p>{e(data["dictionary_contract"]["publication_rule"])}</p></section><section class="notice"><h2>حدود الاستخدام</h2><p>{e(data["safety_note"])}</p></section>'''
    return shell("المواد العملية | مصطلحات علم النفس", data["description"], BASE + "/resources/", body, "CollectionPage")


def render_infographic_index(data: dict[str, Any]) -> str:
    cards = "".join(
        f'<article class="card visual"><h2>{e(item["title"])}</h2><p>{e(item["summary"])}</p><a class="button" href="{BASE_PATH}resources/infographics/{e(item["slug"])}/">فتح الإنفوجرافيك</a></article>'
        for item in data["infographics"]
    )
    body = f'''<header><p><strong>إنفوجرافيك نصي قابل للطباعة</strong></p><h1>إنفوجرافيك الصحة النفسية</h1><p class="lead">بطاقات عالية التباين تعمل على الهاتف والطباعة وقارئات الشاشة، ولا تعتمد على اللون وحده لنقل المعنى.</p></header><section><div class="grid">{cards}</div></section><section class="notice"><h2>حدود الاستخدام</h2><p>{e(data["safety_note"])}</p></section>'''
    return shell("إنفوجرافيك الصحة النفسية | مصطلحات علم النفس", "إنفوجرافيك عربي مبسط وقابل للطباعة حول التثقيف النفسي والدعم والموثوقية.", BASE + "/resources/infographics/", body, "CollectionPage")


def render_infographic(data: dict[str, Any], item: dict[str, Any]) -> str:
    blocks = "".join(f'<article class="visual"><h2><span class="number">{index}</span>{e(text)}</h2></article>' for index, text in enumerate(item["items"], 1))
    body = f'''<header><p><strong>إنفوجرافيك تثقيفي</strong></p><h1>{e(item["title"])}</h1><p class="lead">{e(item["summary"])}</p><div class="actions no-print"><button class="button" type="button" onclick="window.print()">طباعة أو حفظ PDF</button></div></header><section aria-label="نقاط الإنفوجرافيك">{blocks}</section><section class="notice"><h2>حدود الاستخدام</h2><p>{e(data["safety_note"])}</p></section>'''
    canonical = BASE + f'/resources/infographics/{item["slug"]}/'
    return shell(item["title"] + " | مصطلحات علم النفس", item["summary"], canonical, body, "LearningResource")


def render_worksheet_index(data: dict[str, Any]) -> str:
    audience_titles = {item["id"]: item["title"] for item in data["audiences"]}
    cards = "".join(
        f'<article class="card"><p><strong>{e(audience_titles[item["audience"]])}</strong></p><h2>{e(item["title"])}</h2><p>{e(item["purpose"])}</p><a class="button" href="{BASE_PATH}resources/worksheets/{e(item["slug"])}/">فتح الورقة</a></article>'
        for item in data["worksheets"]
    )
    body = f'''<header><p><strong>نماذج عملية غير تشخيصية</strong></p><h1>أوراق عمل للصحة النفسية والدعم</h1><p class="lead">خمس أوراق قابلة للطباعة، واحدة لكل مسار مستخدم، تساعد على تنظيم الملاحظة والسؤال والخطوة التالية.</p></header><section><div class="grid">{cards}</div></section><section class="notice"><h2>حدود الاستخدام</h2><p>{e(data["safety_note"])}</p></section>'''
    return shell("أوراق عمل الصحة النفسية | مصطلحات علم النفس", "أوراق عمل عربية قابلة للطباعة للشخص والأسرة والمعلم والطالب والمختص، دون درجات تشخيصية.", BASE + "/resources/worksheets/", body, "CollectionPage")


def render_worksheet(data: dict[str, Any], item: dict[str, Any]) -> str:
    prompts = "".join(
        f'<div class="prompt"><label class="check"><input type="checkbox" aria-label="تمت مراجعة السؤال {index}"><strong>{index}. {e(prompt)}</strong></label><div class="lines" aria-hidden="true"></div></div>'
        for index, prompt in enumerate(item["prompts"], 1)
    )
    body = f'''<header><p><strong>ورقة عمل قابلة للطباعة</strong></p><h1>{e(item["title"])}</h1><p class="lead">{e(item["purpose"])}</p><div class="actions no-print"><button class="button" type="button" onclick="window.print()">طباعة أو حفظ PDF</button></div></header><section class="worksheet"><h2>الأسئلة</h2><form>{prompts}</form></section><section class="notice"><h2>حدود الاستخدام</h2><p>{e(data["safety_note"])}</p><p>لا تضع اسمًا كاملًا أو بيانات هوية أو معلومات لا ترغب في حفظها على الورقة.</p></section>'''
    canonical = BASE + f'/resources/worksheets/{item["slug"]}/'
    return shell(item["title"] + " | مصطلحات علم النفس", item["purpose"], canonical, body, "LearningResource")


def validate(data: dict[str, Any]) -> None:
    required = {"version", "title", "description", "status", "reviewed_at", "audiences", "content_formats", "plain_language_contract", "dictionary_contract", "disability_content_rules", "infographics", "worksheets", "safety_note"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing source fields: {sorted(missing)}")
    if data["version"] != 184 or data["status"] != "internally-reviewed":
        raise SystemExit("Unexpected version or review status")
    audience_ids = [item["id"] for item in data["audiences"]]
    if audience_ids != ["person", "family", "teacher", "student", "professional"]:
        raise SystemExit("Audience paths must match the five approved roles in order")
    if len({item["slug"] for item in data["audiences"]}) != 5:
        raise SystemExit("Audience slugs must be unique")
    if len(data["content_formats"]) != 4 or len(data["infographics"]) < 3 or len(data["worksheets"]) != 5:
        raise SystemExit("Incomplete resource architecture")
    if {item["audience"] for item in data["worksheets"]} != set(audience_ids):
        raise SystemExit("Every audience must have exactly one worksheet")
    if any(len(item["prompts"]) < 5 for item in data["worksheets"]):
        raise SystemExit("Each worksheet needs at least five prompts")
    all_routes = [route["href"] for item in data["audiences"] for route in item["routes"]]
    if any(not route.startswith("/") for route in all_routes):
        raise SystemExit("Internal audience routes must be root-relative in source data")


def patch_start_here(site: Path) -> bool:
    path = site / "start-here" / "index.html"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    marker = 'data-audience-pathways-v184'
    if marker in text:
        return False
    cards = "".join(
        f'<a class="button" href="{BASE_PATH}audiences/{slug}/">{label}</a>'
        for slug, label in [
            ("person", "شخص"), ("family", "أسرة"), ("teacher", "معلم"), ("student", "طالب"), ("professional", "مختص")
        ]
    )
    block = f'<section {marker}><h2>اختر المسار حسب دورك</h2><p>خمسة مسارات تربط الشرح والقاموس والإنفوجرافيك وأوراق العمل بالاحتياج الفعلي.</p><div class="actions">{cards}<a class="button" href="{BASE_PATH}resources/">المواد العملية</a></div></section>'
    if "</footer>" in text:
        text = text.replace("<footer>", block + "<footer>", 1)
    else:
        text = text.replace("</main>", block + "</main>", 1)
    path.write_text(text, encoding="utf-8")
    return True


def patch_homepage(site: Path) -> bool:
    path = site / "index.html"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    marker = 'data-audience-pathways-v184'
    if marker in text:
        return False
    links = "".join(
        f'<a class="btn secondary" href="audiences/{slug}/">{label}</a>'
        for slug, label in [
            ("person", "شخص"), ("family", "أسرة"), ("teacher", "معلم"), ("student", "طالب"), ("professional", "مختص")
        ]
    )
    block = f'<section class="section" {marker}><h2>اختر المسار حسب دورك</h2><p class="section-intro">ابدأ من دورك للوصول إلى الشرح المبسط والقاموس والإنفوجرافيك وأوراق العمل المناسبة.</p><div class="actions">{links}<a class="btn" href="resources/">المواد العملية</a></div></section>'
    text = text.replace("</main>", block + "</main>", 1)
    path.write_text(text, encoding="utf-8")
    return True


def write_sitemap(site: Path, data: dict[str, Any], urls: list[str]) -> str:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    child = site / "sitemap-audiences-resources.xml"
    root = ET.Element(f"{{{ns}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = data["reviewed_at"]
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "monthly"
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)

    main = site / "sitemap.xml"
    if not main.is_file():
        return "absent"
    tree = ET.parse(main)
    main_root = tree.getroot()
    local = main_root.tag.rsplit("}", 1)[-1]
    if local == "sitemapindex":
        target = BASE + "/sitemap-audiences-resources.xml"
        existing = {node.text for node in main_root.findall(f"{{{ns}}}sitemap/{{{ns}}}loc") if node.text}
        if target not in existing:
            entry = ET.SubElement(main_root, f"{{{ns}}}sitemap")
            ET.SubElement(entry, f"{{{ns}}}loc").text = target
    elif local == "urlset":
        existing = {node.text for node in main_root.findall(f"{{{ns}}}url/{{{ns}}}loc") if node.text}
        for url in urls:
            if url not in existing:
                entry = ET.SubElement(main_root, f"{{{ns}}}url")
                ET.SubElement(entry, f"{{{ns}}}loc").text = url
    else:
        raise SystemExit(f"Unsupported sitemap root: {local}")
    tree.write(main, encoding="utf-8", xml_declaration=True)
    return local


def publish(site: Path = SITE) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate(data)
    generated: list[str] = []

    def write(relative: str, html: str) -> None:
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        generated.append(relative)

    write("audiences/index.html", render_audience_index(data))
    for audience in data["audiences"]:
        write(f'audiences/{audience["slug"]}/index.html', render_audience_page(data, audience))
    write("resources/index.html", render_resources_index(data))
    write("resources/infographics/index.html", render_infographic_index(data))
    for item in data["infographics"]:
        write(f'resources/infographics/{item["slug"]}/index.html', render_infographic(data, item))
    write("resources/worksheets/index.html", render_worksheet_index(data))
    for item in data["worksheets"]:
        write(f'resources/worksheets/{item["slug"]}/index.html', render_worksheet(data, item))

    urls = [BASE + "/" + path.removesuffix("index.html") for path in generated]
    sitemap_mode = write_sitemap(site, data, urls)
    report = {
        "version": 184,
        "status": "built-not-published",
        "audience_paths": len(data["audiences"]),
        "content_formats": len(data["content_formats"]),
        "infographics": len(data["infographics"]),
        "worksheets": len(data["worksheets"]),
        "generated_pages": generated,
        "generated_page_count": len(generated),
        "homepage_patched": patch_homepage(site),
        "start_here_patched": patch_start_here(site),
        "sitemap_mode": sitemap_mode,
        "review_status": data["status"],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "audience-resource-pathways-v184.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    publish()
