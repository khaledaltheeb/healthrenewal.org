from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v24" / "daily-tools-learning-paths-ar.json"
BASE = "https://healthrenewal.org/"
PATH = "/"
TODAY = date.today().isoformat()
DESIGN_CONTRACT = 219

STYLE = r"""
:root{
  color-scheme:light;
  --ink:#173f45;--muted:#4d686b;--brand:#075f5b;--berry:#5b2946;
  --mint:#e5faf5;--mint-line:#b8e4db;--rose:#fff0f5;--rose-line:#f1bfd2;
  --lilac:#f2edff;--lilac-line:#d7caf4;--peach:#fff0e8;--peach-line:#f2cbbb;
  --butter:#fff8d8;--butter-line:#e7d98d;--white:#fff;--focus:#8a3a00;
  --shadow-mint:0 16px 34px rgba(102,190,171,.20),0 5px 12px rgba(102,190,171,.10);
  --shadow-rose:0 16px 34px rgba(205,129,160,.18),0 5px 12px rgba(205,129,160,.09);
  --shadow-lilac:0 16px 34px rgba(151,128,205,.17),0 5px 12px rgba(151,128,205,.08)
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:var(--ink);background:linear-gradient(140deg,#fffafd 0%,var(--mint) 46%,var(--lilac) 100%)}
main{width:min(1080px,92%);margin:auto;padding:28px 0 64px}
header,section,article{border-radius:26px;padding:clamp(18px,4vw,36px);margin:16px 0}
header{background:linear-gradient(135deg,var(--rose),var(--mint),var(--lilac));border:2px solid var(--mint-line);box-shadow:var(--shadow-mint)}
section{background:rgba(255,255,255,.94);border:2px solid #d7ebe7;box-shadow:var(--shadow-mint)}
article{display:flex;flex-direction:column;background:var(--white);border:2px solid var(--mint-line);box-shadow:var(--shadow-mint)}
.grid article:nth-child(5n+1){background:linear-gradient(145deg,#fff,var(--rose));border-color:var(--rose-line);box-shadow:var(--shadow-rose)}
.grid article:nth-child(5n+2){background:linear-gradient(145deg,#fff,var(--mint));border-color:var(--mint-line);box-shadow:var(--shadow-mint)}
.grid article:nth-child(5n+3){background:linear-gradient(145deg,#fff,var(--lilac));border-color:var(--lilac-line);box-shadow:var(--shadow-lilac)}
.grid article:nth-child(5n+4){background:linear-gradient(145deg,#fff,var(--peach));border-color:var(--peach-line);box-shadow:0 16px 34px rgba(211,151,119,.16)}
.grid article:nth-child(5n){background:linear-gradient(145deg,#fff,var(--butter));border-color:var(--butter-line);box-shadow:0 16px 34px rgba(190,166,72,.15)}
h1{font-size:clamp(2rem,5vw,3.6rem);line-height:1.25;margin:.2em 0}
h2{color:var(--berry);line-height:1.35}
p,li{overflow-wrap:anywhere}
a{color:var(--brand);text-underline-offset:.22em}
nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
nav a,.button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:9px 15px;border:2px solid var(--mint-line);border-radius:15px;text-decoration:none;background:linear-gradient(145deg,#fff,var(--mint));color:var(--ink);font-weight:900;box-shadow:0 6px 0 #d6eee9,0 11px 22px rgba(102,190,171,.13)}
nav a:nth-child(2n),.button:nth-of-type(2n){background:linear-gradient(145deg,#fff,var(--rose));border-color:var(--rose-line);box-shadow:0 6px 0 #f5dce6,0 11px 22px rgba(205,129,160,.12)}
nav a:hover,.button:hover{transform:translateY(-1px)}
.tool-kicker{display:inline-flex;width:fit-content;padding:4px 11px;border-radius:999px;background:var(--lilac);color:#4a315f;border:1px solid var(--lilac-line);font-weight:900;font-size:.88rem}
label{font-weight:800;color:var(--ink)}
input,textarea{width:100%;min-height:46px;padding:11px 12px;border:2px solid #91c7be;border-radius:13px;background:#fff;color:var(--ink);font:inherit}
textarea{min-height:100px;resize:vertical}
input:focus,textarea:focus{border-color:var(--brand);box-shadow:0 0 0 4px rgba(7,95,91,.14)}
.note{border-right:7px solid #c74776;background:var(--rose);border-color:var(--rose-line);box-shadow:var(--shadow-rose)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.grid article p{flex:1;color:var(--muted)}
.status{color:var(--brand);font-weight:900}
:focus-visible{outline:3px solid var(--focus);outline-offset:4px}
@media(max-width:640px){nav{display:grid}.grid{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;transition:none!important}nav a:hover,.button:hover{transform:none}}
@media(prefers-contrast:more){header,section,article,nav a,.button,input,textarea{border-color:currentColor;box-shadow:none}}
"""


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def shell(title: str, description: str, canonical: str, schema: dict, body: str) -> str:
    structured = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html><html lang="ar" dir="rtl" data-design="marshmallow-v{DESIGN_CONTRACT}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | مصطلحات علم النفس</title><meta name="description" content="{e(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="theme-color" content="#e5faf5"><meta name="color-scheme" content="light"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(canonical)}"><script type="application/ld+json">{structured}</script><style>{STYLE}</style></head><body>{body}</body></html>'''


def nav() -> str:
    return (
        f'<nav aria-label="التنقل"><a href="{PATH}">الرئيسية</a>'
        f'<a href="{PATH}daily-tools/">الأدوات التفاعلية</a>'
        f'<a href="{PATH}learning-paths/">مسارات التعلم</a>'
        f'<a href="{PATH}care-guides/">أدلة التعامل</a></nav>'
    )


def source_list(data: dict) -> str:
    return "<ul>" + "".join(
        f'<li><a rel="noopener noreferrer" href="{e(source["url"])}">'
        f'{e(source["publisher"])} — {e(source["title"])} ({source["year"]})</a></li>'
        for source in data["sources"]
    ) + "</ul>"


def save_form(tool: dict) -> str:
    fields = "".join(
        f'<p><label>{e(field)}<input data-field="{e(field)}"></label></p>'
        for field in tool["save_fields"]
    )
    return f'''<section><h2>سجل شخصي على هذا الجهاز</h2><p>لا تُرسل البيانات إلى خادم. احفظ أقل قدر ممكن وتجنب كتابة معلومات تعريفية حساسة.</p><form data-tool="{e(tool['slug'])}">{fields}<button type="button" class="button" onclick="saveTool(this.form)">حفظ محلي</button> <button type="button" class="button" onclick="clearTool(this.form)">مسح</button><p aria-live="polite" class="status"></p></form></section><script>function key(f){{return 'pt-v24-'+f.dataset.tool}}function saveTool(f){{let o={{}};f.querySelectorAll('[data-field]').forEach(x=>o[x.dataset.field]=x.value);localStorage.setItem(key(f),JSON.stringify(o));f.querySelector('.status').textContent='تم الحفظ على هذا الجهاز.'}}function clearTool(f){{localStorage.removeItem(key(f));f.reset();f.querySelector('.status').textContent='تم المسح.'}}document.querySelectorAll('form[data-tool]').forEach(f=>{{try{{let o=JSON.parse(localStorage.getItem(key(f))||'{{}}');f.querySelectorAll('[data-field]').forEach(x=>x.value=o[x.dataset.field]||'')}}catch(e){{}}}})</script>'''


def add_homepage_jsonld(text: str) -> str:
    match = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', text, re.S)
    if not match:
        raise SystemExit("Homepage JSON-LD is missing")
    payload = json.loads(match.group(2))
    graph = payload.get("@graph", [])
    collection = next(
        (item for item in graph if item.get("@type") == "CollectionPage" and item.get("@id", "").endswith("#home")),
        None,
    )
    if not collection:
        raise SystemExit("Homepage CollectionPage JSON-LD is missing")
    parts = collection.setdefault("hasPart", [])
    additions = (
        {"@type": "CollectionPage", "name": "الأدوات النفسية التفاعلية اليومية", "url": BASE + "daily-tools/"},
        {"@type": "CollectionPage", "name": "مسارات تعلم الصحة النفسية", "url": BASE + "learning-paths/"},
    )
    urls = {item.get("url") for item in parts if isinstance(item, dict)}
    for item in additions:
        if item["url"] not in urls:
            parts.append(item)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return text[: match.start(2)] + encoded + text[match.end(2) :]


def link_homepage() -> bool:
    home = SITE / "index.html"
    if not home.is_file():
        raise SystemExit("Homepage output is missing before daily-tools publication")
    text = home.read_text(encoding="utf-8")

    if 'href="daily-tools/"' not in text:
        nav_marker = '<a href="provider-assessment-demo/">منصة التقييم</a>'
        if nav_marker not in text:
            raise SystemExit("Homepage navigation insertion point is missing")
        text = text.replace(
            nav_marker,
            '<a href="daily-tools/">أدوات تفاعلية</a><a href="learning-paths/">مسارات التعلم</a>' + nav_marker,
            1,
        )

    if 'data-daily-tools-v219' not in text:
        card_marker = '<a href="cognitive-tests/">فتح المهام</a></article>'
        if card_marker not in text:
            raise SystemExit("Homepage advanced-card insertion point is missing")
        new_cards = (
            '<article class="card" data-daily-tools-v219><h3>الأدوات النفسية التفاعلية</h3>'
            '<p>ثماني أدوات يومية للتنظيم والمتابعة المحلية في التوتر والنوم والأسرة والفقد والحدود، دون تشخيص أو إرسال البيانات إلى خادم.</p>'
            '<a href="daily-tools/">فتح الأدوات التفاعلية</a></article>'
            '<article class="card" data-learning-paths-v219><h3>مسارات التعلم القصيرة</h3>'
            '<p>أربعة مسارات مترابطة تحول المعرفة إلى خطة أيام وأدوات عملية قابلة للمراجعة.</p>'
            '<a href="learning-paths/">فتح مسارات التعلم</a></article>'
        )
        text = text.replace(card_marker, card_marker + new_cards, 1)

    keyword_match = re.search(r'(<meta name="keywords" content=")([^"]*)(">)', text)
    if keyword_match:
        items = [item.strip() for item in keyword_match.group(2).split(",") if item.strip()]
        for value in ("أدوات نفسية تفاعلية", "أدوات تنظيم التوتر", "مسارات تعلم الصحة النفسية"):
            if value not in items:
                items.append(value)
        text = text[: keyword_match.start(2)] + ",".join(items) + text[keyword_match.end(2) :]

    text = add_homepage_jsonld(text)
    home.write_text(text, encoding="utf-8")
    return (
        text.count('href="daily-tools/"') >= 2
        and text.count('href="learning-paths/"') >= 2
        and text.count("data-daily-tools-v219") == 1
    )


def publish(data: dict) -> None:
    output = SITE / "daily-tools"
    output.mkdir(parents=True, exist_ok=True)
    cards = "".join(
        f'<article><span class="tool-kicker">أداة تفاعلية محلية</span><h2>{e(tool["title"])}</h2>'
        f'<p>{e(tool["intent"])}</p><p><strong>المدة:</strong> {e(tool["duration"])}</p>'
        f'<a class="button" href="{PATH}daily-tools/{e(tool["slug"])}/">فتح الأداة</a></article>'
        for tool in data["tools"]
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "الأدوات النفسية التفاعلية اليومية",
        "inLanguage": "ar",
        "url": BASE + "daily-tools/",
        "hasPart": [
            {"@type": "WebApplication", "name": tool["title"], "url": BASE + "daily-tools/" + tool["slug"] + "/"}
            for tool in data["tools"]
        ],
    }
    index_body = (
        f'<main>{nav()}<header><span class="tool-kicker">تصميم مارشملو متباين</span>'
        f'<h1>أدوات نفسية تفاعلية يومية</h1><p>{e(data["disclaimer"])}</p>'
        '<p>تعمل الأدوات داخل المتصفح، وتستخدم ألوانًا هادئة مع نص داكن واضح وحدود وظلال فاتحة لا تحيط الكلمات بإطار داكن.</p>'
        f'</header><div class="grid">{cards}</div><section><h2>المصادر</h2>{source_list(data)}</section></main>'
    )
    (output / "index.html").write_text(
        shell(
            "أدوات نفسية تفاعلية يومية عملية",
            "أدوات تنظيمية عربية تفاعلية غير تشخيصية للتوتر والنوم والأسرة والفقد والحدود، تعمل محليًا بتصميم مارشملو واضح ومتباين.",
            BASE + "daily-tools/",
            schema,
            index_body,
        ),
        encoding="utf-8",
    )

    for tool in data["tools"]:
        directory = output / tool["slug"]
        directory.mkdir(parents=True, exist_ok=True)
        canonical = BASE + "daily-tools/" + tool["slug"] + "/"
        steps = "".join(f"<li>{e(step)}</li>" for step in tool["steps"])
        tool_schema = {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebApplication",
                    "name": tool["title"],
                    "description": tool["intent"],
                    "applicationCategory": "HealthApplication",
                    "operatingSystem": "Any",
                    "inLanguage": "ar",
                    "url": canonical,
                },
                {
                    "@type": "HowTo",
                    "name": tool["title"],
                    "step": [
                        {"@type": "HowToStep", "position": index + 1, "text": step}
                        for index, step in enumerate(tool["steps"])
                    ],
                },
            ],
        }
        help_guidance = '<section class="note"><h2>متى تطلب المساعدة؟</h2><p>هذه الأداة للتنظيم والمتابعة وليست تشخيصًا. اطلب مساعدة مختص مؤهل إذا استمرت الصعوبة، عطلت حياتك اليومية، أو أثارت النتيجة قلقًا لديك. عند وجود خطر فوري على النفس أو الآخرين تواصل مع خدمات الطوارئ المحلية فورًا.</p></section>'
        body = (
            f'<main>{nav()}<header><span class="tool-kicker">أداة تفاعلية تنظيمية غير تشخيصية</span>'
            f'<h1>{e(tool["title"])}</h1><p>{e(tool["intent"])}</p>'
            f'<p><strong>المدة:</strong> {e(tool["duration"])}</p></header>'
            f'<section><h2>الخطوات</h2><ol>{steps}</ol></section>{save_form(tool)}'
            f'<section class="note"><h2>السلامة</h2><p>{e(tool["safety"])}</p><p>{e(data["disclaimer"])}</p></section>'
            f'{help_guidance}<section><h2>مصادر المنهج</h2>{source_list(data)}</section></main>'
        )
        (directory / "index.html").write_text(
            shell(tool["title"], tool["intent"], canonical, tool_schema, body),
            encoding="utf-8",
        )

    paths = SITE / "learning-paths"
    paths.mkdir(parents=True, exist_ok=True)
    path_cards = "".join(
        f'<article><span class="tool-kicker">مسار تعلم تفاعلي</span><h2>{e(path["title"])}</h2>'
        f'<p>{e(path["goal"])}</p><a class="button" href="{PATH}learning-paths/{e(path["slug"])}/">بدء المسار</a></article>'
        for path in data["paths"]
    )
    path_index_body = (
        f'<main>{nav()}<header><span class="tool-kicker">تعلم قصير قابل للتطبيق</span>'
        f'<h1>مسارات تعلم قصيرة</h1><p>{e(data["disclaimer"])}</p></header>'
        f'<div class="grid">{path_cards}</div></main>'
    )
    (paths / "index.html").write_text(
        shell(
            "مسارات تعلم الصحة النفسية",
            "مسارات عربية قصيرة مترابطة للتعلم والتطبيق دون تشخيص ذاتي.",
            BASE + "learning-paths/",
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": "مسارات تعلم الصحة النفسية", "inLanguage": "ar"},
            path_index_body,
        ),
        encoding="utf-8",
    )

    for path in data["paths"]:
        directory = paths / path["slug"]
        directory.mkdir(parents=True, exist_ok=True)
        days = "".join(f'<li><strong>اليوم {index + 1}:</strong> {e(day)}</li>' for index, day in enumerate(path["days"]))
        links = "".join(
            f'<li><a href="{PATH}daily-tools/{e(slug)}/">'
            f'{e(next(tool["title"] for tool in data["tools"] if tool["slug"] == slug))}</a></li>'
            for slug in path["related_tools"]
        )
        path_schema = {
            "@context": "https://schema.org",
            "@type": "Course",
            "name": path["title"],
            "description": path["goal"],
            "inLanguage": "ar",
            "provider": {"@type": "Organization", "name": "مصطلحات علم النفس"},
        }
        path_body = (
            f'<main>{nav()}<header><span class="tool-kicker">مسار تثقيفي تفاعلي غير علاجي</span>'
            f'<h1>{e(path["title"])}</h1><p>{e(path["goal"])}</p></header>'
            f'<section><h2>خطة الأيام</h2><ol>{days}</ol></section>'
            f'<section><h2>أدوات مرتبطة</h2><ul>{links}</ul></section>'
            f'<section class="note"><p>{e(data["disclaimer"])}</p></section></main>'
        )
        (directory / "index.html").write_text(
            shell(path["title"], path["goal"], BASE + "learning-paths/" + path["slug"] + "/", path_schema, path_body),
            encoding="utf-8",
        )

    urls = (
        [BASE + "daily-tools/"]
        + [BASE + "daily-tools/" + tool["slug"] + "/" for tool in data["tools"]]
        + [BASE + "learning-paths/"]
        + [BASE + "learning-paths/" + path["slug"] + "/" for path in data["paths"]]
    )
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{namespace}}}url")
        ET.SubElement(node, f"{{{namespace}}}loc").text = url
        ET.SubElement(node, f"{{{namespace}}}lastmod").text = TODAY
        ET.SubElement(node, f"{{{namespace}}}changefreq").text = "monthly"
    ET.ElementTree(root).write(SITE / "sitemap-tools-paths.xml", encoding="utf-8", xml_declaration=True)

    sitemap = ET.parse(SITE / "sitemap.xml")
    sitemap_root = sitemap.getroot()
    target = BASE + "sitemap-tools-paths.xml"
    existing = {node.text for node in sitemap_root.findall(f"{{{namespace}}}sitemap/{{{namespace}}}loc") if node.text}
    if target not in existing:
        node = ET.SubElement(sitemap_root, f"{{{namespace}}}sitemap")
        ET.SubElement(node, f"{{{namespace}}}loc").text = target
    sitemap.write(SITE / "sitemap.xml", encoding="utf-8", xml_declaration=True)

    homepage_linked = link_homepage()
    api = SITE / "api"
    api.mkdir(exist_ok=True)
    (api / "daily-tools-v24.json").write_text(
        json.dumps(
            {
                "version": 24,
                "design_contract": DESIGN_CONTRACT,
                "tools": len(data["tools"]),
                "paths": len(data["paths"]),
                "pages": len(urls),
                "local_only": True,
                "marshmallow_palette": True,
                "dark_text_box_shadow": False,
                "homepage_linked": homepage_linked,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    if not SITE.exists():
        raise SystemExit("Missing site output")
    publish(json.loads(DATA.read_text(encoding="utf-8")))
