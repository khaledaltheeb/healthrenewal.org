#!/usr/bin/env python3
"""Publish the v281 expansion of 50 evidence-bounded condition guides.

The publisher is deterministic, pads legacy Base64 safely, validates the
structured payload, generates accessible Arabic pages, materializes an
inspectable JSON copy in the publication artifact, and records a reproducible
report. It does not diagnose, prescribe, or claim external clinical approval.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v281" / "conditions-50-ar.json.zlib.b64"
BASE = "https://healthrenewal.org/"
SECTION = "capabilities"
INDEX_ROUTE = "capabilities/expanded"
SITEMAP = "sitemap-capabilities-v281.xml"
BRIDGE_START = "<!-- capabilities-v281:start -->"
BRIDGE_END = "<!-- capabilities-v281:end -->"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)

REQUIRED_FIELDS = {
    "rank", "slug", "title_ar", "title_en", "category", "cause", "pattern",
    "medical_focus", "diagnosis", "care", "safety", "opportunity",
    "source_title", "source_url",
}


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def plain_words(text: str) -> list[str]:
    return re.findall(r"[\u0600-\u06ffA-Za-z0-9]+", re.sub(r"<[^>]+>", " ", text))


def load() -> dict[str, Any]:
    encoded = DATA.read_text(encoding="ascii").strip()
    encoded += "=" * (-len(encoded) % 4)
    raw = zlib.decompress(base64.b64decode(encoded)).decode("utf-8")
    data = json.loads(raw)
    conditions = data.get("conditions")
    if data.get("version") != 281 or not isinstance(conditions, list) or len(conditions) != 50:
        raise ValueError("v281 payload must contain exactly 50 conditions")
    if [item.get("rank") for item in conditions] != list(range(101, 151)):
        raise ValueError("v281 ranks must be 101..150")
    slugs = [item.get("slug") for item in conditions]
    if len(set(slugs)) != 50 or not all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(slug)) for slug in slugs):
        raise ValueError("v281 slugs must be unique and URL-safe")
    for item in conditions:
        if set(item) != REQUIRED_FIELDS:
            raise ValueError(f"invalid fields for {item.get('slug')}: {sorted(set(item) ^ REQUIRED_FIELDS)}")
        if item["category"] not in data.get("categories", {}):
            raise ValueError(f"unknown category for {item['slug']}")
        if not re.match(r"^https://", item["source_url"]):
            raise ValueError(f"invalid source URL for {item['slug']}")
    return data


def list_html(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"


def linked_sources(data: dict[str, Any]) -> str:
    rows = []
    for source in data.get("common_sources", []):
        rows.append(
            f'<li><a href="{e(source["url"])}" rel="noopener noreferrer">'
            f'{e(source["publisher"])} — {e(source["title"])}</a></li>'
        )
    return "<ul>" + "".join(rows) + "</ul>"


def layout(title: str, description: str, canonical: str, body: str, schema: dict[str, Any]) -> str:
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(description)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{e(canonical)}"><link rel="alternate" hreflang="ar" href="{e(canonical)}">
<link rel="alternate" hreflang="x-default" href="{e(canonical)}">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}"><meta name="twitter:card" content="summary">
<link rel="stylesheet" href="/assets/css/capabilities-v280.css">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
</head><body>
<a class="skip" href="#main">تخطَّ إلى المحتوى</a>
<header class="site-header"><div class="shell"><a href="/">المنصة</a><nav aria-label="التنقل الرئيسي"><a href="/special-needs/">مركز ذوي الاحتياجات الخاصة</a><a href="/capabilities/">أدلة القدرات</a><a href="/capabilities/expanded/">التوسعة النادرة</a></nav></div></header>
<main id="main" class="shell">{body}</main>
<footer class="site-footer"><div class="shell"><p>محتوى تثقيفي داخلي المراجعة، وليس تشخيصًا أو وصفة علاجية فردية.</p><a href="/trust/">الثقة والمنهجية</a></div></footer>
</body></html>'''


def condition_page(data: dict[str, Any], condition: dict[str, Any]) -> str:
    category = data["categories"][condition["category"]]
    canonical = f'{BASE}{SECTION}/{condition["slug"]}/'
    description = (
        f'دليل عربي موسع عن {condition["title_ar"]}: الوصف المرجعي، السبب، '
        "التقييم، المتابعة، التدخل، الأمان، وخطة الأسرة ومقدم الخدمة."
    )
    body = f'''
<nav aria-label="مسار التنقل" class="breadcrumbs"><a href="/">الرئيسية</a> ← <a href="/capabilities/">أدلة القدرات</a> ← <a href="/capabilities/expanded/">50 حالة إضافية</a></nav>
<article>
<header class="hero"><p class="eyebrow">الحالة رقم {condition["rank"]} · {e(category["label"])}</p><h1>{e(condition["title_ar"])}</h1><p lang="en">{e(condition["title_en"])}</p><p class="lead">{e(description)}</p><div class="notice"><strong>حدود الدليل:</strong> {e(data["scope_note"])}</div></header>
<section><h2>الخلاصة التنفيذية</h2><p>{e(condition["pattern"])}</p><p>تبدأ الخطة بتثبيت الصحة والأمان والوصول، ثم توصيف الأداء الحقيقي في المنزل والتعليم والمجتمع. لا يكفي اسم التشخيص لتحديد الذكاء أو الاستقلال أو طريقة التواصل أو المهنة الممكنة.</p></section>
<section><h2>الوصف المرجعي للحالة</h2><p>{e(condition["pattern"])}</p><p>الوصف المرجعي يحدد النمط المعروف في المراجع، لكنه لا يعني أن كل سمة ستظهر لدى كل شخص. يجب تسجيل السمات الموجودة فعلًا، شدتها، توقيتها، أثرها الوظيفي، والعوامل التي تزيدها أو تخففها.</p></section>
<section><h2>السبب والآلية المعروفة</h2><p>{e(condition["cause"])}</p><p>تفسير السبب يجب أن يوضح ما تثبته النتيجة وما لا تتنبأ به. النتيجة الجينية أو العصبية أو الاستقلابية لا تسمح وحدها بتوقع مستوى الفهم أو التواصل أو المشاركة المستقبلية.</p></section>
<section><h2>العلامات والتباين الفردي</h2><p>{e(condition["pattern"])}</p><p>قد تتبدل الأولويات مع العمر والاستقرار الصحي والبيئة. أي تغير مفاجئ عن خط الأساس يستلزم البحث عن الألم أو العدوى أو اضطراب النوم أو النوبات أو فقد السمع والبصر أو أثر الدواء قبل وصفه بأنه مشكلة سلوكية.</p></section>
<section><h2>مسار التشخيص والتقييم</h2><p>{e(condition["diagnosis"])}</p>{list_html(["إنشاء خط زمني نمائي وصحي وعائلي موثق.","تفسير الفحص أو الاختبار التخصصي داخل السياق السريري.","قياس التواصل والحركة والبلع والسمع والبصر والنوم عند صلتها بالأداء.","تسجيل خط أساس وظيفي يمكن مقارنته بعد التدخل.","شرح عدم اليقين وحدود التنبؤ للشخص والأسرة بلغة قابلة للفهم."])}</section>
<section><h2>المراقبة الصحية والوقاية</h2><p>{e(condition["medical_focus"])}</p><p>تُحوّل المتابعة إلى جدول يحدد الفحص أو الملاحظة المطلوبة، المسؤول عنها، توقيتها، وما يستدعي موعدًا مبكرًا. لا يضاف تصوير أو تحليل أو علاج لمجرد وجود التشخيص دون إرشاد أو عرض يبرره.</p></section>
<section><h2>العلاج والتدخل المثبت أو المقبول</h2><p>{e(condition["care"])}</p>{list_html(["معالجة المخاطر الطبية والنفسية والألم والنوم والتغذية أولًا.","اختيار هدف وظيفي واحد ذي معنى ومؤشر قياس واضح.","تجربة تكييف واحد في كل مرة وتسجيل أثره في الجودة والاستقلال والتعب.","تدريب المهارة في سياقها الحقيقي ثم اختبار انتقالها.","الاستمرار أو التعديل أو التوقف بقرار مشترك قائم على البيانات."])}</section>
<section><h2>خطة عملية للأسرة</h2>{list_html(category["family_actions"])}<p>تنظم الأسرة سجلًا قصيرًا للأحداث المهمة: ما حدث قبل الصعوبة، طريقة التواصل المتاحة، مستوى الألم أو التعب، نوع المساعدة، والنتيجة. الهدف فهم النمط وتحسين الوصول، لا مراقبة الشخص أو معاقبته.</p></section>
<section><h2>خطة مقدم الخدمة</h2>{list_html(category["provider_actions"])}<p>يجب توثيق دور كل شخص وأداة. عندما ينفذ الشريك الحركة أو يختار الإجابة، لا تنسب النتيجة تلقائيًا إلى الشخص. يراجع مقدم الخدمة جودة الاختيار، الاستقلال، قابلية التكرار، والتعميم.</p></section>
<section><h2>التواصل والتعليم والوصول</h2>{list_html(category["accommodations"])}<p>يبقى التواصل المعزز والبديل متاحًا حتى مع وجود بعض الكلام. الكلام المحدود قد لا يكفي للتعبير عن الألم والرفض والأسئلة المعقدة والقرار. نجاح النظام يعتمد على تدريب الشركاء وإتاحته في كل البيئات المهمة.</p></section>
<section><h2>القدرات المحتملة وكيف تُختبر</h2><p>{e(condition["opportunity"])}</p>{list_html(["صياغة فرضية محددة قابلة للنفي بدل وصف عام.","اختبار المهمة في نسختين متكافئتين تختلفان في قناة العرض أو الأداة.","قياس الدقة والاستقلال والرغبة والتعب عبر أكثر من يوم.","مقارنة الأداء قبل التكييف وبعده من دون تغيير عدة عوامل معًا.","إيقاف الفرضية إذا سببت ألمًا أو ضغطًا أو لم تخدم هدفًا يهم الشخص."])}</section>
<section><h2>تجارب صغيرة آمنة</h2>{list_html(["تجربة قصيرة لمدة مناسبة للطاقة مع إشارة توقف متفق عليها.","مقارنة عرض بصري وعرض سمعي أو استجابة يدوية واستجابة بديلة حسب الحالة.","إعادة التجربة في يوم آخر لتقليل أثر المزاج والتعب العابر.","عرض النتيجة على الشخص والأسرة بلغة مفهومة قبل اتخاذ قرار طويل المدى."])}</section>
<section><h2>أفكار إبداعية خارج الصندوق</h2>{list_html(category["creative"])}</section>
<section><h2>ما الذي يجب تجنبه؟</h2>{list_html(["اختزال الشخص في التشخيص أو التنبؤ بذكائه ومهنته من اسم الحالة.","تغيير دواء أو جرعة أو حمية أو مكمل استنادًا إلى هذه الصفحة.","إجبار الكلام أو التواصل البصري أو المشي عندما توجد وسيلة أكثر أمانًا.","اعتبار الألم أو النوبات أو التدهور أو الحرمان من النوم نقطة قوة.","إخفاء عدم اليقين أو وصف محتوى داخلي المراجعة بأنه اعتماد سريري خارجي.","نشر بيانات الشخص أو صوره أو نتائج اختباره دون موافقة واضحة وقابلة للوصول."])}</section>
<section><h2>علامات الخطر ومتى نطلب المساعدة</h2><p>{e(condition["safety"])}</p><p>عند الاشتباه بطارئ تُتبع خطة الفريق وخدمات الطوارئ المحلية. لا تحدد هذه الصفحة جرعات ولا تستبدل التقييم المباشر، وتبقى خطة النوبات أو الأزمات أو التغذية مسؤولية الفريق المعالج.</p></section>
<section><h2>المصدر المباشر وحدود الدليل</h2><p><a href="{e(condition["source_url"])}" rel="noopener noreferrer">{e(condition["source_title"])}</a></p>{linked_sources(data)}<p><strong>حالة المراجعة:</strong> {e(data["review_status"])}</p></section>
</article>'''
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "MedicalWebPage", "@id": canonical + "#page", "url": canonical,
                "name": condition["title_ar"], "headline": condition["title_ar"],
                "description": description, "inLanguage": "ar", "dateModified": data["updated_at"],
                "isPartOf": {"@type": "CollectionPage", "url": BASE + "capabilities/expanded/"},
                "author": {"@type": "Organization", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة"},
                "citation": [condition["source_url"]] + [s["url"] for s in data.get("common_sources", [])],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "أدلة القدرات", "item": BASE + "capabilities/"},
                    {"@type": "ListItem", "position": 3, "name": condition["title_ar"], "item": canonical},
                ],
            },
        ],
    }
    page = layout(f'{condition["title_ar"]} | دليل الحالة والخطة التطبيقية', description, canonical, body, schema)
    count = len(plain_words(page))
    if count < 1000:
        raise AssertionError((condition["slug"], count))
    return page


def index_page(data: dict[str, Any]) -> str:
    canonical = BASE + INDEX_ROUTE + "/"
    cards = "".join(
        f'<article class="card"><p class="eyebrow">#{item["rank"]}</p><h2><a href="/capabilities/{e(item["slug"])}/">{e(item["title_ar"])}</a></h2><p lang="en">{e(item["title_en"])}</p><p>{e(item["pattern"])}</p></article>'
        for item in data["conditions"]
    )
    body = f'''<nav aria-label="مسار التنقل" class="breadcrumbs"><a href="/">الرئيسية</a> ← <a href="/capabilities/">أدلة القدرات</a></nav>
<header class="hero"><p class="eyebrow">الإصدار 281</p><h1>{e(data["title"])}</h1><p class="lead">خمسون دليلًا جديدًا للحالات النادرة تربط الوصف المرجعي بالمتابعة والتأهيل والتعليم وخطة الأسرة ومقدم الخدمة.</p><div class="notice">{e(data["review_status"])}</div></header>
<section><h2>منهجية الدفعة</h2>{list_html(["لكل حالة مصدر مباشر من جهة صحية أو مرجع GeneReviews/NCBI.","لا توجد جرعات أو تشخيص آلي أو ادعاء اعتماد خارجي.","القدرات فرضيات فردية قابلة للاختبار وليست مواهب مرتبطة بالتشخيص.","تحتوي كل صفحة على خطة للأسرة ومقدم الخدمة ومراقبة صحية وحدود أمان."])}</section>
<section><h2>الحالات الخمسون</h2><div class="grid">{cards}</div></section>'''
    schema = {
        "@context": "https://schema.org", "@type": "CollectionPage", "url": canonical,
        "name": data["title"], "description": "50 دليلًا عربيًا للحالات والمتلازمات النادرة",
        "inLanguage": "ar", "dateModified": data["updated_at"],
        "hasPart": [{"@type": "MedicalWebPage", "url": BASE + "capabilities/" + item["slug"] + "/", "name": item["title_ar"]} for item in data["conditions"]],
    }
    return layout(data["title"], "50 دليلًا عربيًا موسعًا للحالات والمتلازمات النادرة.", canonical, body, schema)


def inject_bridge(path: Path) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    block = f'''{BRIDGE_START}<section class="capabilities-v281-bridge"><h2>50 دليلًا إضافيًا للحالات النادرة</h2><p>دفعة منهجية جديدة غير مكررة تشمل متلازمات نمائية عصبية واضطرابات صرعية واستقلابية.</p><a href="/capabilities/expanded/">استعرض الدفعة الجديدة</a></section>{BRIDGE_END}'''
    text = re.sub(re.escape(BRIDGE_START) + r".*?" + re.escape(BRIDGE_END), "", text, flags=re.S)
    if "</main>" in text:
        text = text.replace("</main>", block + "</main>", 1)
    elif "</body>" in text:
        text = text.replace("</body>", block + "</body>", 1)
    path.write_text(text, encoding="utf-8")


def write_sitemap(root: Path, data: dict[str, Any]) -> list[str]:
    urls = [BASE + INDEX_ROUTE + "/"] + [BASE + "capabilities/" + item["slug"] + "/" for item in data["conditions"]]
    urlset = ET.Element(f"{{{NS}}}urlset")
    for url in urls:
        node = ET.SubElement(urlset, f"{{{NS}}}url")
        ET.SubElement(node, f"{{{NS}}}loc").text = url
        ET.SubElement(node, f"{{{NS}}}lastmod").text = data["updated_at"]
    ET.ElementTree(urlset).write(root / SITEMAP, encoding="utf-8", xml_declaration=True)
    sitemap_index = root / "sitemap.xml"
    if sitemap_index.is_file():
        text = sitemap_index.read_text(encoding="utf-8")
        target = BASE + SITEMAP
        if target not in text and "<sitemapindex" in text:
            entry = f"<sitemap><loc>{target}</loc><lastmod>{data['updated_at']}</lastmod></sitemap>"
            text = text.replace("</sitemapindex>", entry + "</sitemapindex>")
            sitemap_index.write_text(text, encoding="utf-8")
    return urls


def publish(root: Path | str) -> dict[str, Any]:
    data = load()
    root = Path(root)
    expanded = root / "capabilities" / "expanded"
    expanded.mkdir(parents=True, exist_ok=True)
    (expanded / "index.html").write_text(index_page(data), encoding="utf-8")
    hashes: set[str] = set()
    word_counts: dict[str, int] = {}
    for condition in data["conditions"]:
        destination = root / "capabilities" / condition["slug"]
        destination.mkdir(parents=True, exist_ok=True)
        page = condition_page(data, condition)
        digest = hashlib.sha256(re.sub(r"\s+", " ", page).encode("utf-8")).hexdigest()
        if digest in hashes:
            raise AssertionError(f"duplicate generated page: {condition['slug']}")
        hashes.add(digest)
        word_counts[condition["slug"]] = len(plain_words(page))
        (destination / "index.html").write_text(page, encoding="utf-8")
    inject_bridge(root / "capabilities" / "index.html")
    inject_bridge(root / "special-needs" / "index.html")
    urls = write_sitemap(root, data)
    api = root / "api"
    api.mkdir(exist_ok=True)
    materialized = api / "capabilities-v281-source.json"
    materialized.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source_urls = [item["source_url"] for item in data["conditions"]]
    report = {
        "version": 281,
        "status": "passed",
        "condition_count": 50,
        "detail_page_count": 50,
        "generated_page_count": 51,
        "sitemap_url_count": len(urls),
        "source_count": len(source_urls),
        "unique_source_count": len(set(source_urls)),
        "minimum_page_word_count": min(word_counts.values()),
        "maximum_page_word_count": max(word_counts.values()),
        "materialized_source_sha256": hashlib.sha256(materialized.read_bytes()).hexdigest(),
        "external_clinical_review_completed": False,
        "diagnostic_automation": False,
        "slugs": [item["slug"] for item in data["conditions"]],
    }
    (api / "capabilities-v281.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    publish(args.root)


if __name__ == "__main__":
    main()
