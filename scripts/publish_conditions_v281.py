#!/usr/bin/env python3
"""Publish v281 and enforce production SEO across the capabilities library."""
from __future__ import annotations

import argparse, base64, hashlib, html, json, os, re, zlib
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content/v281/conditions-50-ar.json.zlib.b64"
BASE = "https://healthrenewal.org/"
SOCIAL_IMAGE = BASE + "assets/brand/rawafid-social-card.jpg"
SITEMAP = "sitemap-capabilities-v281.xml"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
BRIDGE_START, BRIDGE_END = "<!-- capabilities-v281:start -->", "<!-- capabilities-v281:end -->"
ET.register_namespace("", NS)
REQUIRED_FIELDS = {
    "rank", "slug", "title_ar", "title_en", "category", "cause", "pattern",
    "medical_focus", "diagnosis", "care", "safety", "opportunity", "source_title", "source_url",
}


def e(v: Any) -> str: return html.escape(str(v), quote=True)
def words(text: str) -> list[str]: return re.findall(r"[\u0600-\u06ffA-Za-z0-9]+", re.sub(r"<[^>]+>", " ", text))
def lastmod() -> str:
    v = os.environ.get("CAPABILITIES_LASTMOD", "").strip()
    return v if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else date.today().isoformat()


def load() -> dict[str, Any]:
    encoded = DATA.read_text(encoding="ascii").strip(); encoded += "=" * (-len(encoded) % 4)
    data = json.loads(zlib.decompress(base64.b64decode(encoded)).decode("utf-8"))
    items = data.get("conditions")
    if data.get("version") != 281 or not isinstance(items, list) or len(items) != 50:
        raise ValueError("v281 payload must contain exactly 50 conditions")
    if [x.get("rank") for x in items] != list(range(101, 151)): raise ValueError("v281 ranks must be 101..150")
    slugs = [x.get("slug") for x in items]
    if len(set(slugs)) != 50 or not all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(x)) for x in slugs):
        raise ValueError("v281 slugs must be unique and URL-safe")
    for item in items:
        if set(item) != REQUIRED_FIELDS: raise ValueError(f"invalid fields for {item.get('slug')}")
        if item["category"] not in data.get("categories", {}): raise ValueError(f"unknown category: {item['slug']}")
        if not item["source_url"].startswith("https://"): raise ValueError(f"invalid source URL: {item['slug']}")
    return data


def ul(items: list[str]) -> str: return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in items) + "</ul>"
def section(title: str, content: str) -> str: return f"<section><h2>{e(title)}</h2>{content}</section>"
def sources(data: dict[str, Any]) -> str:
    return "<ul>" + "".join(
        f'<li><a href="{e(s["url"])}" rel="noopener noreferrer">{e(s["publisher"])} — {e(s["title"])}</a></li>'
        for s in data.get("common_sources", [])
    ) + "</ul>"


def description_for(title: str) -> str:
    return f"دليل عربي موثق عن {title} يشرح السمات والتقييم والمتابعة والرعاية والأمان والتواصل والتكييفات العملية، مع مصادر مباشرة وحدود واضحة للمعلومات."


def title_for(title: str) -> str:
    v = f"{title}: التشخيص والرعاية | روافد"
    if len(v) <= 68: return v
    v = f"{title} | روافد"
    return v if len(v) <= 78 else title


def layout(title: str, desc: str, canonical: str, body: str, schema: dict[str, Any], page_type: str = "article") -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<link rel="canonical" href="{e(canonical)}"><link rel="alternate" hreflang="ar" href="{e(canonical)}"><link rel="alternate" hreflang="x-default" href="{e(canonical)}">
<meta property="og:type" content="{page_type}"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="روافد"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:url" content="{e(canonical)}"><meta property="og:image" content="{SOCIAL_IMAGE}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="روافد — منصة عربية للصحة النفسية والتربية الدامجة">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{SOCIAL_IMAGE}">
<link rel="stylesheet" href="/assets/css/capabilities-v280.css"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script></head><body>
<a class="skip" href="#main">تخطَّ إلى المحتوى</a><header class="site-header"><div class="shell"><a href="/">روافد</a><nav aria-label="التنقل الرئيسي"><a href="/special-needs/">مركز ذوي الاحتياجات الخاصة</a><a href="/capabilities/">أدلة القدرات</a><a href="/capabilities/expanded/">الحالات النادرة</a></nav></div></header>
<main id="main" class="shell">{body}</main><footer class="site-footer"><div class="shell"><p>محتوى تثقيفي داخلي المراجعة، وليس تشخيصًا أو وصفة علاجية فردية.</p><a href="/trust/">الثقة والمنهجية</a></div></footer></body></html>'''


def condition_page(data: dict[str, Any], c: dict[str, Any]) -> str:
    cat, canonical = data["categories"][c["category"]], BASE + "capabilities/" + c["slug"] + "/"
    desc = description_for(c["title_ar"])
    generic = {
        "baseline": "يُسجل خط أساس وظيفي قابل للمقارنة في التواصل والحركة والتعلم والمشاركة، مع توثيق الألم والنوم والتعب والبيئة ومقدار المساعدة حتى لا تختلط القدرة بعوامل الوصول.",
        "uncertainty": "الوصف المرجعي يحدد النمط المعروف في الأدلة ولا يعني ظهور كل سمة لدى كل شخص، ولا يسمح اسم التشخيص وحده بالتنبؤ بالذكاء أو الاستقلال أو وسيلة التواصل أو المهنة المستقبلية.",
        "measurement": "يُقاس الأثر بالدقة والاستقلال والراحة والتعب والرغبة وقابلية التكرار والتعميم عبر أكثر من يوم وبيئة، مع تغيير عامل واحد كل مرة وإيقاف التجربة عند الألم أو الضغط.",
    }
    blocks = [
        section("الخلاصة التنفيذية", f"<p>{e(c['pattern'])}</p><p>{generic['baseline']}</p>"),
        section("الوصف المرجعي للحالة", f"<p>{e(c['pattern'])}</p><p>{generic['uncertainty']}</p>"),
        section("السبب والآلية المعروفة", f"<p>{e(c['cause'])}</p><p>تفسير السبب يوضح ما تثبته النتيجة وما لا تتنبأ به؛ فالنتيجة الجينية أو العصبية أو الاستقلابية لا تحدد وحدها مستوى الفهم أو المشاركة.</p>"),
        section("العلامات والتباين الفردي", f"<p>{e(c['pattern'])}</p><p>أي تغير مفاجئ عن خط الأساس يستلزم البحث عن الألم والعدوى واضطراب النوم والنوبات وفقد السمع أو البصر وآثار العلاج قبل وصفه بأنه تغير سلوكي ثابت.</p>"),
        section("مسار التشخيص والتقييم", f"<p>{e(c['diagnosis'])}</p>" + ul(["إنشاء خط زمني نمائي وصحي وعائلي موثق.", "تفسير الفحص التخصصي داخل السياق السريري.", "قياس التواصل والحركة والبلع والسمع والبصر والنوم عند صلتها بالأداء.", "تسجيل خط أساس وظيفي قابل للمقارنة.", "شرح عدم اليقين وحدود التنبؤ بلغة مفهومة."])),
        section("المراقبة الصحية والوقاية", f"<p>{e(c['medical_focus'])}</p><p>تتحول المتابعة إلى جدول يحدد المسؤول والتوقيت وما يستدعي مراجعة مبكرة، ولا يضاف فحص أو تدخل لمجرد وجود التشخيص دون عرض أو إرشاد يبرره.</p>"),
        section("العلاج والتدخل المثبت أو المقبول", f"<p>{e(c['care'])}</p>" + ul(["معالجة المخاطر والألم والنوم والتغذية أولًا.", "اختيار هدف وظيفي ذي معنى ومؤشر قياس واضح.", "تجربة تكييف واحد وتسجيل أثره.", "تدريب المهارة في سياقها الحقيقي واختبار انتقالها.", "الاستمرار أو التعديل أو التوقف بقرار مشترك قائم على البيانات."])),
        section("خطة عملية للأسرة", ul(cat["family_actions"]) + f"<p>{generic['baseline']}</p>"),
        section("خطة مقدم الخدمة", ul(cat["provider_actions"]) + "<p>يوثق مقدم الخدمة دور كل شخص وأداة ويمنع نسبة استجابة الشريك إلى الشخص، ثم يراجع جودة الاختيار والاستقلال والتكرار والتعميم.</p>"),
        section("التواصل والتعليم والوصول", ul(cat["accommodations"]) + "<p>يبقى التواصل المعزز والبديل متاحًا حتى مع وجود بعض الكلام، لأن التعبير عن الألم والرفض والأسئلة المعقدة والقرار قد يحتاج قناة أوسع وأكثر ثباتًا.</p>"),
        section("القدرات المحتملة وكيف تُختبر", f"<p>{e(c['opportunity'])}</p><p>{generic['measurement']}</p>" + ul(["صياغة فرضية محددة قابلة للنفي.", "مقارنة نسختين متكافئتين من المهمة.", "القياس عبر أكثر من يوم.", "تغيير عامل واحد فقط.", "إيقاف الفرضية إذا لم تخدم هدفًا يهم الشخص."])),
        section("تجارب صغيرة آمنة", ul(["جلسة قصيرة تناسب الطاقة مع إشارة توقف متفق عليها.", "مقارنة قنوات عرض أو استجابة بديلة حسب الحالة.", "إعادة التجربة في يوم آخر لتقليل أثر التعب العابر.", "مشاركة النتيجة مع الشخص والأسرة قبل القرار طويل المدى."]) + f"<p>{generic['measurement']}</p>"),
        section("أفكار إبداعية خارج الصندوق", ul(cat["creative"])),
        section("ما الذي يجب تجنبه؟", ul(["اختزال الشخص في التشخيص أو التنبؤ بذكائه من اسم الحالة.", "تغيير دواء أو جرعة أو حمية أو مكمل استنادًا إلى الصفحة.", "إجبار الكلام أو التواصل البصري أو المشي عند وجود وسيلة أكثر أمانًا.", "اعتبار الألم أو النوبات أو التدهور نقطة قوة.", "ادعاء اعتماد سريري خارجي غير موجود.", "نشر بيانات الشخص أو صوره دون موافقة واضحة."])),
        section("علامات الخطر ومتى نطلب المساعدة", f"<p>{e(c['safety'])}</p><p>عند الاشتباه بطارئ تُتبع خطة الفريق وخدمات الطوارئ المحلية. هذه الصفحة لا تحدد جرعات ولا تستبدل التقييم المباشر.</p>"),
        section("أسئلة شائعة عن الدليل", "<h3>هل يحدد التشخيص مستوى الذكاء أو الاستقلال؟</h3><p>لا. يحتاج ذلك إلى تقييم وظيفي مباشر ومتكرر في البيئات الفعلية.</p><h3>هل يمكن استخدام الصفحة لتغيير علاج؟</h3><p>لا. أي تغيير علاجي أو دوائي أو غذائي يحتاج إلى الفريق السريري المسؤول.</p><h3>كيف نعرف أن التكييف مفيد؟</h3><p>بمقارنة الاستقلال والدقة والراحة والتعب والمشاركة قبل التكييف وبعده عبر أكثر من موقف.</p>"),
        section("المصدر المباشر وحدود الدليل", f'<p><a href="{e(c["source_url"])}" rel="noopener noreferrer">{e(c["source_title"])}</a></p>{sources(data)}<p><strong>حالة المراجعة:</strong> {e(data["review_status"])}</p>'),
    ]
    body = f'<nav aria-label="مسار التنقل" class="breadcrumbs"><a href="/">الرئيسية</a> ← <a href="/capabilities/">أدلة القدرات</a> ← <a href="/capabilities/expanded/">الحالات النادرة</a></nav><article><header class="hero"><p class="eyebrow">الحالة رقم {c["rank"]} · {e(cat["label"])}</p><h1>{e(c["title_ar"])}</h1><p lang="en">{e(c["title_en"])}</p><p class="lead">{e(desc)}</p><div class="notice"><strong>حدود الدليل:</strong> {e(data["scope_note"])}</div></header>{"".join(blocks)}</article>'
    schema = {"@context": "https://schema.org", "@graph": [
        {"@type": "MedicalWebPage", "@id": canonical + "#page", "url": canonical, "name": c["title_ar"], "headline": c["title_ar"], "description": desc, "inLanguage": "ar", "dateModified": lastmod(), "isPartOf": {"@type": "CollectionPage", "url": BASE + "capabilities/expanded/"}, "author": {"@type": "Organization", "name": "روافد", "url": BASE}, "publisher": {"@type": "Organization", "name": "روافد", "url": BASE}, "citation": [c["source_url"]] + [s["url"] for s in data.get("common_sources", [])]},
        {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE}, {"@type": "ListItem", "position": 2, "name": "أدلة القدرات", "item": BASE + "capabilities/"}, {"@type": "ListItem", "position": 3, "name": "الحالات النادرة", "item": BASE + "capabilities/expanded/"}, {"@type": "ListItem", "position": 4, "name": c["title_ar"], "item": canonical}]},
    ]}
    page = layout(title_for(c["title_ar"]), desc, canonical, body, schema)
    if len(words(page)) < 1300: raise AssertionError((c["slug"], len(words(page))))
    return page


def index_page(data: dict[str, Any]) -> str:
    canonical, desc = BASE + "capabilities/expanded/", "50 دليلًا عربيًا موثقًا لحالات ومتلازمات نادرة، تغطي السمات والتشخيص والمتابعة والرعاية والأمان والتواصل والتكييفات مع مصادر مباشرة."
    cards = "".join(f'<article class="card"><p class="eyebrow">#{x["rank"]}</p><h2><a href="/capabilities/{e(x["slug"])}/">{e(x["title_ar"])}</a></h2><p lang="en">{e(x["title_en"])}</p><p>{e(x["pattern"])}</p></article>' for x in data["conditions"])
    body = f'<nav aria-label="مسار التنقل" class="breadcrumbs"><a href="/">الرئيسية</a> ← <a href="/capabilities/">أدلة القدرات</a></nav><header class="hero"><p class="eyebrow">الإصدار 281</p><h1>{e(data["title"])}</h1><p class="lead">{e(desc)}</p><div class="notice"><strong>حدود الدليل:</strong> {e(data["scope_note"])}</div></header>' + section("منهجية الدفعة", ul(["لكل حالة مصدر مباشر موثوق.", "لا توجد جرعات أو تشخيص آلي أو ادعاء اعتماد خارجي.", "القدرات فرضيات فردية قابلة للاختبار.", "كل صفحة تشمل الأسرة ومقدم الخدمة والمراقبة والأمان."])) + section("الحالات الخمسون", f'<div class="grid">{cards}</div>')
    schema = {"@context": "https://schema.org", "@graph": [{"@type": "CollectionPage", "url": canonical, "name": data["title"], "description": desc, "inLanguage": "ar", "dateModified": lastmod(), "hasPart": [{"@type": "MedicalWebPage", "url": BASE + "capabilities/" + x["slug"] + "/", "name": x["title_ar"]} for x in data["conditions"]]}, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE}, {"@type": "ListItem", "position": 2, "name": "أدلة القدرات", "item": BASE + "capabilities/"}, {"@type": "ListItem", "position": 3, "name": "الحالات النادرة", "item": canonical}]}]}
    return layout("50 حالة ومتلازمة نادرة: أدلة عربية موثقة | روافد", desc, canonical, body, schema, "website")


def inject_bridge(path: Path) -> None:
    if not path.is_file(): return
    text = path.read_text(encoding="utf-8")
    block = f'{BRIDGE_START}<section class="capabilities-v281-bridge"><h2>50 دليلًا إضافيًا للحالات النادرة</h2><p>دفعة منهجية غير مكررة تشمل متلازمات نمائية عصبية واضطرابات صرعية واستقلابية.</p><a href="/capabilities/expanded/">استعرض الدفعة الجديدة</a></section>{BRIDGE_END}'
    text = re.sub(re.escape(BRIDGE_START) + r".*?" + re.escape(BRIDGE_END), "", text, flags=re.S)
    text = text.replace("</main>", block + "</main>", 1) if "</main>" in text else text.replace("</body>", block + "</body>", 1)
    path.write_text(text, encoding="utf-8")


def write_sitemap(root: Path, data: dict[str, Any]) -> list[str]:
    urls = [BASE + "capabilities/expanded/"] + [BASE + "capabilities/" + x["slug"] + "/" for x in data["conditions"]]
    out = ET.Element(f"{{{NS}}}urlset")
    for url in urls:
        node = ET.SubElement(out, f"{{{NS}}}url"); ET.SubElement(node, f"{{{NS}}}loc").text = url; ET.SubElement(node, f"{{{NS}}}lastmod").text = lastmod()
    ET.ElementTree(out).write(root / SITEMAP, encoding="utf-8", xml_declaration=True)
    return urls


def clean_subject(h1: str) -> str: return re.sub(r"^بروتوكول اكتشاف وتنمية القدرات:\s*", "", h1).strip() or h1
def h1_of(text: str) -> str:
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.I | re.S)
    return re.sub(r"<[^>]+>", " ", html.unescape(m.group(1))).strip() if m else ""
def upsert_meta(text: str, attr: str, key: str, value: str) -> str:
    text = re.sub(rf'<meta\b[^>]*\b{attr}=["\']{re.escape(key)}["\'][^>]*>', "", text, flags=re.I)
    return text.replace("</head>", f'<meta {attr}="{e(key)}" content="{e(value)}">\n</head>', 1)
def upsert_title(text: str, value: str) -> str:
    if re.search(r"<title\b", text, re.I): return re.sub(r"<title\b[^>]*>.*?</title>", f"<title>{e(value)}</title>", text, count=1, flags=re.I | re.S)
    return text.replace("</head>", f"<title>{e(value)}</title>\n</head>", 1)
def upsert_canonical(text: str, url: str) -> str:
    tag = f'<link rel="canonical" href="{e(url)}">'
    if re.search(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', text, re.I): return re.sub(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', tag, text, count=1, flags=re.I)
    return text.replace("</head>", tag + "\n</head>", 1)


def route_for(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix(); rel = rel[:-10] if rel.endswith("index.html") else rel.removesuffix(".html")
    route = "/" + rel.lstrip("/"); return route if route.endswith("/") else route + "/"
def canonical_for(root: Path, path: Path) -> str: return BASE + route_for(root, path).lstrip("/")


def seo_title(route: str, h1: str) -> str:
    fixed = {"/capabilities/": "القدرات والاحتياجات الخاصة: 150 دليلًا موثقًا | روافد", "/capabilities/registry/": "سجل 150 حالة ومتلازمة: أدلة القدرات | روافد", "/capabilities/expanded/": "50 حالة ومتلازمة نادرة: أدلة عربية موثقة | روافد"}
    if route in fixed: return fixed[route]
    subject = clean_subject(h1) if h1 else "أدلة القدرات"; v = f"{subject} | روافد"; return v if len(v) <= 78 else subject
def seo_description(route: str, h1: str) -> str:
    fixed = {"/capabilities/": "مكتبة عربية موثقة لفهم القدرات والاحتياجات لدى 150 حالة ومتلازمة، مع التقييم الوظيفي والتواصل والتكييفات والرعاية ومصادر علمية مباشرة.", "/capabilities/registry/": "سجل موسوعي يضم 150 حالة ومتلازمة مع روابط مباشرة إلى أدلة عربية موثقة حول السمات والتقييم والرعاية والتواصل والتكييفات والقدرات المحتملة.", "/capabilities/expanded/": "50 دليلًا عربيًا موثقًا لحالات ومتلازمات نادرة، تغطي السمات والتشخيص والمتابعة والرعاية والأمان والتواصل والتكييفات مع مصادر مباشرة."}
    if route in fixed: return fixed[route]
    return description_for(clean_subject(h1) if h1 else "الحالة")


def ensure_breadcrumb(text: str, route: str, h1: str) -> str:
    if '"@type": "BreadcrumbList"' in text or '"@type":"BreadcrumbList"' in text: return text
    parts = [x for x in route.strip("/").split("/") if x]; labels = {"capabilities": "أدلة القدرات", "registry": "سجل الحالات", "expanded": "الحالات النادرة"}; items = [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE}]; current = ""
    for pos, part in enumerate(parts, 2): current += part + "/"; items.append({"@type": "ListItem", "position": pos, "name": h1 if pos == len(parts) + 1 and h1 else labels.get(part, part.replace("-", " ")), "item": BASE + current})
    tag = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}, ensure_ascii=False) + "</script>"
    return text.replace("</head>", tag + "\n</head>", 1)


def normalize_page(root: Path, path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if "</head>" not in text: return False
    original = text; text = text.replace("https://khaledaltheeb.github.io/pterminology-site/", BASE).replace("/pterminology-site/", "/")
    route = route_for(root, path)
    if route == "/capabilities/registry/": text = text.replace("100 حالة", "150 حالة")
    h1, canonical = h1_of(text), canonical_for(root, path); title, desc = seo_title(route, h1), seo_description(route, h1)
    text = upsert_title(text, title); text = upsert_canonical(text, canonical)
    for attr, key, value in [("name", "description", desc), ("name", "robots", "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"), ("property", "og:type", "website" if route in {"/capabilities/", "/capabilities/registry/", "/capabilities/expanded/"} else "article"), ("property", "og:locale", "ar_AR"), ("property", "og:site_name", "روافد"), ("property", "og:title", title), ("property", "og:description", desc), ("property", "og:url", canonical), ("property", "og:image", SOCIAL_IMAGE), ("property", "og:image:width", "1200"), ("property", "og:image:height", "630"), ("property", "og:image:alt", "روافد — منصة عربية للصحة النفسية والتربية الدامجة"), ("name", "twitter:card", "summary_large_image"), ("name", "twitter:title", title), ("name", "twitter:description", desc), ("name", "twitter:image", SOCIAL_IMAGE)]: text = upsert_meta(text, attr, key, value)
    text = ensure_breadcrumb(text, route, h1)
    if text != original: path.write_text(text, encoding="utf-8", newline="\n")
    return text != original


def normalize_sitemaps(root: Path) -> dict[str, int]:
    changed = entries = 0
    for name in ("sitemap.xml", "sitemap-capabilities.xml", "sitemap-capabilities-v281.xml"):
        path = root / name
        if not path.is_file(): continue
        try: tree = ET.parse(path)
        except ET.ParseError: continue
        top = tree.getroot()
        if top.tag.rsplit("}", 1)[-1] != "urlset": continue
        dirty = False
        for node in list(top):
            loc = node.find(f"{{{NS}}}loc")
            if loc is None or not loc.text: continue
            new = loc.text.replace("https://khaledaltheeb.github.io/pterminology-site/", BASE)
            if new != loc.text: loc.text, dirty = new, True
            if new.startswith(BASE + "capabilities/"):
                entries += 1; lm = node.find(f"{{{NS}}}lastmod")
                if lm is None: lm = ET.SubElement(node, f"{{{NS}}}lastmod"); dirty = True
                if lm.text != lastmod(): lm.text, dirty = lastmod(), True
        if dirty: tree.write(path, encoding="utf-8", xml_declaration=True); changed += 1
    index = root / "sitemap-index.xml"
    if index.is_file():
        try:
            tree = ET.parse(index); top = tree.getroot(); existing = {x.findtext(f"{{{NS}}}loc") for x in top.findall(f"{{{NS}}}sitemap")}; dirty = False
            for name in ("sitemap.xml", "sitemap-capabilities.xml", "sitemap-capabilities-v281.xml"):
                target = BASE + name
                if (root / name).is_file() and target not in existing:
                    node = ET.SubElement(top, f"{{{NS}}}sitemap"); ET.SubElement(node, f"{{{NS}}}loc").text = target; ET.SubElement(node, f"{{{NS}}}lastmod").text = lastmod(); dirty = True
            if dirty: tree.write(index, encoding="utf-8", xml_declaration=True); changed += 1
        except ET.ParseError: pass
    return {"sitemap_files_changed": changed, "capability_url_entries": entries}


def normalize_robots(root: Path) -> bool:
    path = root / "robots.txt"
    if not path.is_file(): return False
    original = path.read_text(encoding="utf-8", errors="replace"); lines = [x for x in original.splitlines() if not x.lower().startswith("sitemap:")]; lines += ["", "Sitemap: https://healthrenewal.org/sitemap-index.xml", "Sitemap: https://healthrenewal.org/sitemap.xml", "Sitemap: https://healthrenewal.org/sitemap-capabilities.xml", "Sitemap: https://healthrenewal.org/sitemap-capabilities-v281.xml"]; text = "\n".join(lines).rstrip() + "\n"
    if text != original: path.write_text(text, encoding="utf-8", newline="\n"); return True
    return False


def enforce_seo(root: Path) -> dict[str, Any]:
    pages = sorted((root / "capabilities").rglob("*.html")) if (root / "capabilities").is_dir() else []; processed = changed = skipped = 0; failures = {}
    for path in pages:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if "</head>" not in raw: skipped += 1; continue
        processed += 1; changed += int(normalize_page(root, path)); text = path.read_text(encoding="utf-8", errors="replace"); issues = []
        for marker in ('rel="canonical"', 'name="description"', 'property="og:image"', 'name="twitter:image"', 'summary_large_image'):
            if marker not in text: issues.append(marker)
        if '"@type": "BreadcrumbList"' not in text and '"@type":"BreadcrumbList"' not in text: issues.append("BreadcrumbList")
        if "/pterminology-site/" in text or "khaledaltheeb.github.io/pterminology-site" in text: issues.append("legacy_internal_origin")
        m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.I)
        if not m or len(html.unescape(m.group(1)).strip()) < 110: issues.append("short_meta_description")
        if issues: failures[path.relative_to(root).as_posix()] = issues
    sitemap = normalize_sitemaps(root); robots = normalize_robots(root)
    if failures: raise AssertionError(json.dumps(failures, ensure_ascii=False, indent=2))
    return {"status": "passed", "pages_found": len(pages), "pages_processed": processed, "pages_changed": changed, "pages_skipped_without_head": skipped, "legacy_internal_origin_occurrences": 0, "social_image": SOCIAL_IMAGE, "lastmod": lastmod(), "robots_changed": robots, **sitemap}


def publish(root: Path | str) -> dict[str, Any]:
    data, root = load(), Path(root); expanded = root / "capabilities/expanded"; expanded.mkdir(parents=True, exist_ok=True); (expanded / "index.html").write_text(index_page(data), encoding="utf-8")
    hashes, counts = set(), {}
    for c in data["conditions"]:
        d = root / "capabilities" / c["slug"]; d.mkdir(parents=True, exist_ok=True); page = condition_page(data, c); digest = hashlib.sha256(re.sub(r"\s+", " ", page).encode()).hexdigest()
        if digest in hashes: raise AssertionError(f"duplicate generated page: {c['slug']}")
        hashes.add(digest); counts[c["slug"]] = len(words(page)); (d / "index.html").write_text(page, encoding="utf-8")
    inject_bridge(root / "capabilities/index.html"); inject_bridge(root / "special-needs/index.html"); urls = write_sitemap(root, data); seo = enforce_seo(root)
    api = root / "api"; api.mkdir(exist_ok=True); materialized = api / "capabilities-v281-source.json"; materialized.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); (api / "capabilities-seo-v1.json").write_text(json.dumps(seo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_urls = [x["source_url"] for x in data["conditions"]]; report = {"version": 281, "status": "passed", "condition_count": 50, "detail_page_count": 50, "generated_page_count": 51, "sitemap_url_count": len(urls), "source_count": len(source_urls), "unique_source_count": len(set(source_urls)), "minimum_page_word_count": min(counts.values()), "maximum_page_word_count": max(counts.values()), "materialized_source_sha256": hashlib.sha256(materialized.read_bytes()).hexdigest(), "external_clinical_review_completed": False, "diagnostic_automation": False, "seo": seo, "slugs": [x["slug"] for x in data["conditions"]]}
    (api / "capabilities-v281.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(json.dumps(report, ensure_ascii=False)); return report


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("root", type=Path); args = p.parse_args(); publish(args.root)

if __name__ == "__main__": main()
