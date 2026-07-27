from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

VERSION = 2
DETAIL_COUNT = 2000
TOPIC_COUNT = 100
FACET_COUNT = 20

FACET_GROUPS = (
    (
        "الفهم الأساسي",
        "ابدأ بالمعنى والعلامات والعوامل والفروق قبل الانتقال إلى أي تدخل.",
        ("definition", "signs", "factors", "differential"),
    ),
    (
        "التقييم والتدخل المهني",
        "مسارات لفهم جمع المعلومات وخيارات الدعم المهني وحدود كل تدخل.",
        ("assessment", "psychotherapy", "cbt", "early"),
    ),
    (
        "الدعم والتكيف والعلاقات",
        "خطوات عملية ودور الأسرة والعلاقات والوقاية دون تحويل الصفحة إلى تشخيص أو وصفة.",
        ("self_help", "coping", "prevention", "family", "relationships"),
    ),
    (
        "العمر والبيئة وجودة الحياة",
        "كيف يتغير الفهم باختلاف المرحلة العمرية والمدرسة والعمل والحياة اليومية.",
        ("children", "adolescents", "adults", "older", "work", "school", "quality"),
    ),
)

QUICK_KEYS = ("definition", "signs", "assessment", "differential", "self_help", "family")

TOPIC_CSS = r'''
/* v2 — topic-first encyclopedia architecture */
.ency-topic-v2{width:min(1180px,calc(100% - 24px));margin:auto;padding:18px 0 64px;color:#17383d}
.ency-topic-v2__hero{padding:clamp(26px,5vw,58px);border-radius:32px;background:linear-gradient(130deg,#ffe3ee,#d9f8f3,#eee8ff);box-shadow:0 18px 52px rgba(57,125,128,.13);margin-bottom:22px}
.ency-topic-v2__hero h1{font-size:clamp(2rem,5vw,3.8rem);line-height:1.22;margin:.18em 0}.ency-topic-v2__hero p{max-width:82ch;line-height:1.9;color:#3f6268}
.ency-topic-v2__meta,.ency-topic-v2__actions{display:flex;gap:9px;flex-wrap:wrap;align-items:center}.ency-topic-v2__badge{display:inline-flex;align-items:center;min-height:34px;padding:6px 11px;border-radius:999px;background:#fff;border:1px solid #cce4e1;color:#174b52;font-weight:800}
.ency-topic-v2__button{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:9px 15px;border-radius:13px;background:#116d69;color:#fff!important;text-decoration:none;font-weight:900}.ency-topic-v2__button--secondary{background:#fff;color:#116d69!important;border:1px solid #9ed4cf}
.ency-topic-v2__section{margin-top:20px;padding:clamp(20px,4vw,38px);border:1px solid #cce5e1;border-radius:26px;background:rgba(255,255,255,.97);box-shadow:0 12px 34px rgba(57,125,128,.08)}
.ency-topic-v2__section h2{margin-top:0;color:#174b52}.ency-topic-v2__section p,.ency-topic-v2__section li{line-height:1.95}
.ency-topic-v2__grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(250px,100%),1fr));gap:14px}.ency-topic-v2__card{padding:19px;border-radius:20px;background:linear-gradient(145deg,#fff,#f0fbf9);border:1px solid #cce5e1}.ency-topic-v2__card:nth-child(3n+2){background:linear-gradient(145deg,#fff,#fff0f6)}.ency-topic-v2__card:nth-child(3n){background:linear-gradient(145deg,#fff,#f1edff)}
.ency-topic-v2__card h2,.ency-topic-v2__card h3{margin:.3rem 0}.ency-topic-v2__card p{color:#567176}.ency-topic-v2__card a{font-weight:900}.ency-topic-v2__card small{display:block;color:#667d81;margin-top:7px}
.ency-topic-v2__route-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr));gap:10px;padding:0;list-style:none}.ency-topic-v2__route-list a{display:block;height:100%;padding:14px 15px;border-radius:15px;background:#f5fbfa;border:1px solid #cce5e1;text-decoration:none;font-weight:900}.ency-topic-v2__route-list span{display:block;margin-top:4px;color:#60797e;font-size:.9rem;font-weight:500}
.ency-topic-v2__search{display:grid;grid-template-columns:2fr 1fr;gap:10px;margin-top:20px}.ency-topic-v2__search input,.ency-topic-v2__search select{width:100%;min-height:48px;padding:12px 14px;border:1px solid #a9cfcb;border-radius:14px;background:#fff;color:#17383d;font:inherit}
.ency-topic-v2__crumbs{margin:7px 0 17px;color:#5a7479;font-size:.93rem}.ency-topic-v2__crumbs a{color:#126c73}.ency-topic-v2__notice{padding:17px 19px;border-radius:18px;background:linear-gradient(135deg,#fff4cb,#e2f8f3);border:1px solid #d7dfb5}.ency-topic-v2__sources{background:#f3fbfa}
.ency-topic-v2__count{font-size:1.15rem}.ency-topic-v2 [hidden]{display:none!important}
@media(max-width:700px){.ency-topic-v2{width:calc(100% - 14px)}.ency-topic-v2__hero,.ency-topic-v2__section{border-radius:21px;padding:20px}.ency-topic-v2__search{grid-template-columns:1fr}}
'''


def append_stylesheet(head_markup: str, base: str) -> str:
    return head_markup + f'<link rel="stylesheet" href="{base}assets/css/encyclopedia-topic-hubs-v2.css">'


def unique_domain_groups(items: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    order: list[str] = []
    for item in items:
        domain = item["domain_ar"]
        if domain not in grouped:
            order.append(domain)
        grouped[domain].append(item)
    return [(domain, grouped[domain]) for domain in order]


def facet_map(group: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {item["facet"]["key"]: item for item in group}


def detail_href(base: str, item: dict[str, Any]) -> str:
    return f'{base}encyclopedia/{item["slug"]}/'


def topic_href(base: str, domain_index: int) -> str:
    return f"{base}hubs/topic-{domain_index:03d}/"


def route_link(builder: Any, item: dict[str, Any], *, with_focus: bool = True) -> str:
    focus = (
        f'<span>{builder.esc(item["facet"]["focus"])}</span>'
        if with_focus
        else ""
    )
    return (
        f'<li><a href="{detail_href(builder.BASE, item)}">'
        f'{builder.esc(item["facet"]["ar"])}{focus}</a></li>'
    )


def topic_schema(builder: Any, domain: str, group: list[dict[str, Any]], description: str) -> dict[str, Any]:
    first = group[0]
    canonical = topic_href(builder.BASE, first["domain_index"])
    citations = [url for _, url in builder.choose_sources(domain, "definition", first["category"])]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": canonical + "#page",
                "name": f"{domain}: الدليل المرجعي المتكامل",
                "description": description,
                "url": canonical,
                "inLanguage": "ar",
                "numberOfItems": len(group),
                "dateModified": builder.TODAY,
                "citation": citations,
                "hasPart": [detail_href(builder.BASE, item) for item in group],
            },
            {
                "@type": "DefinedTerm",
                "@id": canonical + "#term",
                "name": domain,
                "alternateName": first["domain_en"],
                "description": builder.profile_for(domain, first["category"])["definition"],
                "url": canonical,
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": builder.BASE},
                    {"@type": "ListItem", "position": 2, "name": "الموسوعة", "item": builder.BASE + "encyclopedia/"},
                    {"@type": "ListItem", "position": 3, "name": domain, "item": canonical},
                ],
            },
        ],
    }


def render_topic_hub(builder: Any, domain: str, group: list[dict[str, Any]]) -> str:
    if len(group) != FACET_COUNT:
        raise SystemExit(f"Topic {domain} must expose {FACET_COUNT} facets, found {len(group)}")
    first = group[0]
    category = first["category"]
    profile = builder.profile_for(domain, category)
    mapped = facet_map(group)
    if set(mapped) != {facet["key"] for facet in builder.FACETS}:
        raise SystemExit(f"Topic facet contract mismatch: {domain}")

    description = (
        f"دليل عربي متكامل عن {domain} يبدأ بالتعريف والعلامات والعوامل، ثم ينظم التقييم "
        "والدعم والعمر والأسرة والتعليم والعمل وجودة الحياة في مسار واحد."
    )
    path = f'hubs/topic-{first["domain_index"]:03d}/'
    schema = topic_schema(builder, domain, group, description)
    head = append_stylesheet(
        builder.head(
            f"{domain}: الدليل المرجعي المتكامل | منصة الصحة النفسية",
            description,
            path,
            schema,
            [domain, first["domain_en"], category, "دليل نفسي", "الصحة النفسية"],
        ),
        builder.BASE,
    )
    quick_cards = "".join(
        '<article class="ency-topic-v2__card">'
        f'<h2><a href="{detail_href(builder.BASE, mapped[key])}">{builder.esc(mapped[key]["facet"]["ar"])}</a></h2>'
        f'<p>{builder.esc(mapped[key]["facet"]["focus"])}</p>'
        "</article>"
        for key in QUICK_KEYS
    )
    grouped_routes = "".join(
        '<section class="ency-topic-v2__section">'
        f"<h2>{builder.esc(title)}</h2><p>{builder.esc(intro)}</p>"
        '<ul class="ency-topic-v2__route-list">'
        + "".join(route_link(builder, mapped[key]) for key in keys)
        + "</ul></section>"
        for title, intro, keys in FACET_GROUPS
    )
    observations = "".join(f"<li>{builder.esc(value)}</li>" for value in profile["observations"])
    distinctions = "".join(f"<li>{builder.esc(value)}</li>" for value in profile["distinctions"])
    sources = builder.choose_sources(domain, "definition", category)
    source_markup = builder.source_links(sources)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>{head}</head><body>
<main class="ency-topic-v2" data-topic-hub-v2="true" data-topic-index="{first['domain_index']}">
<nav class="ency-topic-v2__crumbs" aria-label="مسار التنقل"><a href="{builder.BASE}">الرئيسية</a> ← <a href="{builder.BASE}encyclopedia/">الموسوعة</a> ← {builder.esc(domain)}</nav>
<header class="ency-topic-v2__hero">
<div class="ency-topic-v2__meta"><span class="ency-topic-v2__badge">{builder.esc(category)}</span><span class="ency-topic-v2__badge">20 مسارًا تفصيليًا</span><span class="ency-topic-v2__badge">مراجعة: {builder.TODAY}</span></div>
<h1>{builder.esc(domain)}: الدليل المرجعي المتكامل</h1><p lang="en" dir="ltr">{builder.esc(first['domain_en'])}</p><p>{builder.esc(profile['definition'])}</p>
<div class="ency-topic-v2__actions"><a class="ency-topic-v2__button" href="{detail_href(builder.BASE, mapped['definition'])}">ابدأ بالتعريف</a><a class="ency-topic-v2__button ency-topic-v2__button--secondary" href="{detail_href(builder.BASE, mapped['assessment'])}">انتقل إلى التقييم</a><a class="ency-topic-v2__button ency-topic-v2__button--secondary" href="{builder.BASE}encyclopedia/all/">كل الصفحات التفصيلية</a></div>
</header>
<section class="ency-topic-v2__section"><h2>ابدأ من السؤال الأقرب لحاجتك</h2><p>هذه المسارات الستة هي نقاط الدخول الأساسية. بقية الزوايا منظمة أسفلها بحسب الفهم والتقييم والدعم والعمر والسياق.</p><div class="ency-topic-v2__grid">{quick_cards}</div></section>
<section class="ency-topic-v2__section"><h2>ملخص متكامل قبل التوسع</h2><div class="ency-topic-v2__grid"><article class="ency-topic-v2__card"><h3>ما الذي نلاحظه؟</h3><ul>{observations}</ul></article><article class="ency-topic-v2__card"><h3>ما الذي يمنع الخلط؟</h3><ul>{distinctions}</ul></article><article class="ency-topic-v2__card"><h3>قاعدة تفسير</h3><p>لا يكفي عرض واحد أو اختبار واحد أو صفحة إلكترونية للحكم على {builder.esc(domain)}. تُفهم الصورة عبر السياق والمدة والشدة والأثر والمعلومات المتعددة.</p></article></div></section>
{grouped_routes}
<section class="ency-topic-v2__section"><h2>متى تصبح المساعدة المهنية أولوية؟</h2><ul><li>عند استمرار الضيق أو التعطيل أو اتساعه عبر أكثر من مجال.</li><li>عند تغير مفاجئ في السلوك أو النوم أو الإدراك أو القدرة على الرعاية الذاتية.</li><li>عند وجود خطر على السلامة أو أفكار إيذاء النفس أو الآخرين أو فقد الاتصال بالواقع.</li><li>عندما تتداخل الصورة مع حالة طبية أو دوائية أو نمائية أو تحتاج إلى تشخيص تفريقي.</li></ul><div class="ency-topic-v2__notice"><strong>في الخطر المباشر:</strong> اطلب مساعدة الطوارئ المحلية أو تواصل فورًا مع خدمة صحية مؤهلة. لا تنتظر نتيجة أداة إلكترونية.</div></section>
<section class="ency-topic-v2__section"><h2>استعد للموعد بطريقة منظمة</h2><ol><li>دوّن وقت البداية والتغير عن الوضع المعتاد.</li><li>سجّل التكرار والشدة والمواقف التي تزيد أو تخفف الصعوبة.</li><li>حدد الأثر على النوم والدراسة والعمل والعلاقات والرعاية الذاتية.</li><li>اجمع قائمة الأدوية والحالات الصحية والملاحظات من البيئات المهمة عند الحاجة.</li><li>اكتب سؤالين أو ثلاثة تريد أن يجيب عنها التقييم بدل طلب حكم عام.</li></ol></section>
<section class="ency-topic-v2__section ency-topic-v2__sources"><h2>مصادر مؤسسية للمراجعة</h2><p>تُستخدم هذه المصادر للتوسع والتحقق، وقد تتغير التوصيات والصفحات بمرور الوقت.</p><ul>{source_markup}</ul></section>
<aside class="ency-topic-v2__section ency-topic-v2__notice"><strong>حدود الدليل:</strong> محتوى تثقيفي منظم، وليس تشخيصًا فرديًا أو وصفة علاجية أو بديلًا عن الطبيب أو الأخصائي المرخص.</aside>
</main><script src="{builder.BASE}assets/js/app-v10.js" defer></script><script src="{builder.BASE}assets/js/lab-v12.js" defer></script></body></html>'''


def render_topic_index(builder: Any, domain_groups: list[tuple[str, list[dict[str, Any]]]]) -> str:
    categories = sorted({group[0]["category"] for _, group in domain_groups})
    cards = "".join(
        '<article class="ency-topic-v2__card topic-item" '
        f'data-category="{builder.esc(group[0]["category"])}" '
        f'data-q="{builder.esc(builder.normalize(domain + " " + group[0]["domain_en"] + " " + group[0]["category"]))}">'
        f'<span class="ency-topic-v2__badge">{builder.esc(group[0]["category"])}</span>'
        f'<h2><a href="{topic_href(builder.BASE, group[0]["domain_index"])}">{builder.esc(domain)}</a></h2>'
        f'<p lang="en" dir="ltr">{builder.esc(group[0]["domain_en"])}</p>'
        f'<p>{builder.esc(builder.profile_for(domain, group[0]["category"])["definition"])}</p>'
        '<small>دليل متكامل + 20 مسارًا تفصيليًا</small></article>'
        for domain, group in domain_groups
    )
    options = "".join(f'<option value="{builder.esc(value)}">{builder.esc(value)}</option>' for value in categories)
    description = "موسوعة عربية منظمة حول مئة موضوع نفسي ونمائي وعلاجي؛ لكل موضوع دليل مرجعي متكامل وعشرون مسارًا تفصيليًا للتوسع."
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "الموسوعة النفسية العربية",
        "description": description,
        "url": builder.BASE + "encyclopedia/",
        "numberOfItems": len(domain_groups),
        "inLanguage": "ar",
        "hasPart": [topic_href(builder.BASE, group[0]["domain_index"]) for _, group in domain_groups],
    }
    head = append_stylesheet(
        builder.head(
            "الموسوعة النفسية العربية | منصة الصحة النفسية",
            description,
            "encyclopedia/",
            schema,
            ["الموسوعة النفسية", "مصطلحات علم النفس", "الصحة النفسية", "ذوو الاحتياجات الخاصة"],
        ),
        builder.BASE,
    )
    script = '''<script>(()=>{const q=document.querySelector('#topic-q'),c=document.querySelector('#topic-category'),n=document.querySelector('#topic-count'),items=[...document.querySelectorAll('.topic-item')];function run(){const s=q.value.trim().toLowerCase(),cv=c.value;let count=0;for(const item of items){const ok=(!s||item.dataset.q.includes(s))&&(!cv||item.dataset.category===cv);item.hidden=!ok;if(ok)count++}n.textContent=count}q.addEventListener('input',run);c.addEventListener('change',run);run()})()</script>'''
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>{head}</head><body><main class="ency-topic-v2" data-encyclopedia-index-v2="true"><header class="ency-topic-v2__hero"><div class="ency-topic-v2__meta"><span class="ency-topic-v2__badge">100 موضوع مرجعي</span><span class="ency-topic-v2__badge">2,000 صفحة تفصيلية محفوظة</span></div><h1>الموسوعة النفسية العربية</h1><p>ابدأ بالموضوع الكامل بدل الغرق في قائمة من الزوايا المتساوية. يجمع كل مركز التعريف والعلامات والعوامل والتقييم والدعم ومراحل العمر والأسرة والتعليم والعمل وجودة الحياة.</p><p class="ency-topic-v2__count"><strong id="topic-count">100</strong> موضوع ظاهر. <a href="{builder.BASE}encyclopedia/all/">فتح فهرس الصفحات التفصيلية البالغ عددها 2,000</a>.</p><div class="ency-topic-v2__search"><input id="topic-q" type="search" placeholder="ابحث باسم الموضوع بالعربية أو الإنجليزية" aria-label="البحث في موضوعات الموسوعة"><select id="topic-category" aria-label="تصفية حسب التصنيف"><option value="">كل التصنيفات</option>{options}</select></div></header><section class="ency-topic-v2__grid" aria-label="الموضوعات المرجعية">{cards}</section></main>{script}<script src="{builder.BASE}assets/js/app-v10.js" defer></script><script src="{builder.BASE}assets/js/lab-v12.js" defer></script></body></html>'''


def render_detail_archive(builder: Any, items: list[dict[str, Any]]) -> str:
    cards = "".join(
        '<article class="ency-topic-v2__card detail-item" '
        f'data-domain="{builder.esc(item["domain_ar"])}" data-category="{builder.esc(item["category"])}" '
        f'data-q="{builder.esc(builder.normalize(item["ar"] + " " + item["en"] + " " + item["category"]))}">'
        f'<span class="ency-topic-v2__badge">{builder.esc(item["category"])}</span>'
        f'<h2><a href="{detail_href(builder.BASE, item)}">{builder.esc(item["ar"])}</a></h2>'
        f'<p lang="en" dir="ltr">{builder.esc(item["en"])}</p></article>'
        for item in items
    )
    domains = []
    seen: set[str] = set()
    for item in items:
        if item["domain_ar"] not in seen:
            domains.append(item["domain_ar"])
            seen.add(item["domain_ar"])
    categories = sorted({item["category"] for item in items})
    domain_options = "".join(f'<option value="{builder.esc(value)}">{builder.esc(value)}</option>' for value in domains)
    category_options = "".join(f'<option value="{builder.esc(value)}">{builder.esc(value)}</option>' for value in categories)
    description = "الفهرس الكامل للصفحات التفصيلية في الموسوعة النفسية: ألفا صفحة تغطي مئة موضوع وعشرين زاوية لكل موضوع."
    schema = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "فهرس الصفحات التفصيلية", "description": description, "url": builder.BASE + "encyclopedia/all/", "numberOfItems": len(items), "inLanguage": "ar"}
    head = append_stylesheet(builder.head("كل صفحات الموسوعة التفصيلية | منصة الصحة النفسية", description, "encyclopedia/all/", schema, ["فهرس علم النفس", "الموسوعة النفسية", "مصطلحات علم النفس"]), builder.BASE)
    script = '''<script>(()=>{const q=document.querySelector('#detail-q'),d=document.querySelector('#detail-domain'),c=document.querySelector('#detail-category'),n=document.querySelector('#detail-count'),items=[...document.querySelectorAll('.detail-item')];function run(){const s=q.value.trim().toLowerCase(),dv=d.value,cv=c.value;let count=0;for(const item of items){const ok=(!s||item.dataset.q.includes(s))&&(!dv||item.dataset.domain===dv)&&(!cv||item.dataset.category===cv);item.hidden=!ok;if(ok)count++}n.textContent=count}q.addEventListener('input',run);d.addEventListener('change',run);c.addEventListener('change',run);run()})()</script>'''
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>{head}</head><body><main class="ency-topic-v2" data-detail-archive-v2="true"><nav class="ency-topic-v2__crumbs"><a href="{builder.BASE}">الرئيسية</a> ← <a href="{builder.BASE}encyclopedia/">الموسوعة</a> ← كل الصفحات</nav><header class="ency-topic-v2__hero"><h1>كل صفحات الموسوعة التفصيلية</h1><p>هذا الفهرس مخصص للتعمق والمقارنة الدقيقة. للقراءة الأولى، ابدأ من <a href="{builder.BASE}encyclopedia/">الموضوعات المرجعية المئة</a>.</p><p><strong id="detail-count">2000</strong> صفحة ظاهرة.</p><div class="ency-topic-v2__search"><input id="detail-q" type="search" placeholder="ابحث بالعربية أو الإنجليزية" aria-label="البحث في الصفحات التفصيلية"><select id="detail-domain" aria-label="تصفية حسب الموضوع"><option value="">كل الموضوعات</option>{domain_options}</select><select id="detail-category" aria-label="تصفية حسب التصنيف"><option value="">كل التصنيفات</option>{category_options}</select></div></header><section class="ency-topic-v2__grid">{cards}</section></main>{script}<script src="{builder.BASE}assets/js/app-v10.js" defer></script><script src="{builder.BASE}assets/js/lab-v12.js" defer></script></body></html>'''


def render_hubs_index(builder: Any, domain_groups: list[tuple[str, list[dict[str, Any]]]], items: list[dict[str, Any]]) -> str:
    topic_cards = "".join(
        '<article class="ency-topic-v2__card"><span class="ency-topic-v2__badge">موضوع مرجعي</span>'
        f'<h2><a href="{topic_href(builder.BASE, group[0]["domain_index"])}">{builder.esc(domain)}</a></h2>'
        f'<p>{builder.esc(builder.profile_for(domain, group[0]["category"])["definition"])}</p></article>'
        for domain, group in domain_groups
    )
    angle_cards = "".join(
        '<article class="ency-topic-v2__card"><span class="ency-topic-v2__badge">زاوية مقارنة</span>'
        f'<h2><a href="{builder.BASE}hubs/angle-{index:03d}/">{builder.esc(facet["ar"])}</a></h2>'
        f'<p>{builder.esc(facet["focus"])}</p></article>'
        for index, facet in enumerate(builder.FACETS, 1)
    )
    categories = sorted({item["category"] for item in items})
    cross_facets = [builder.FACETS[index] for index in (0, 1, 3, 5, 7, 10, 15, 19)]
    combos = [(category, facet) for category in categories for facet in cross_facets][:80]
    path_cards = "".join(
        '<article class="ency-topic-v2__card"><span class="ency-topic-v2__badge">مسار تطبيقي</span>'
        f'<h2><a href="{builder.BASE}hubs/path-{index:03d}/">{builder.esc(category)}: {builder.esc(facet["ar"])}</a></h2>'
        f'<p>{builder.esc(facet["focus"])}</p></article>'
        for index, (category, facet) in enumerate(combos, 1)
    )
    description = "مراكز الموسوعة مرتبة إلى مئة موضوع مرجعي، وعشرين زاوية مقارنة، وثمانين مسارًا تطبيقيًا حسب التصنيف."
    schema = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "المراكز الموضوعية النفسية", "description": description, "url": builder.BASE + "hubs/", "numberOfItems": 200, "inLanguage": "ar"}
    head = append_stylesheet(builder.head("المراكز الموضوعية النفسية | منصة الصحة النفسية", description, "hubs/", schema, ["مراكز علم النفس", "الموسوعة النفسية", "المقارنات النفسية"]), builder.BASE)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head>{head}</head><body><main class="ency-topic-v2" data-hubs-index-v2="true"><header class="ency-topic-v2__hero"><h1>المراكز الموضوعية النفسية</h1><p>ثلاث طبقات واضحة: ابدأ بموضوع مرجعي متكامل، استخدم زوايا المقارنة عند دراسة مفهوم عبر موضوعات متعددة، وانتقل إلى المسارات التطبيقية عند البحث داخل تصنيف محدد.</p><div class="ency-topic-v2__meta"><span class="ency-topic-v2__badge">100 موضوع</span><span class="ency-topic-v2__badge">20 زاوية مقارنة</span><span class="ency-topic-v2__badge">80 مسارًا تطبيقيًا</span></div></header><section class="ency-topic-v2__section"><h2>الموضوعات المرجعية المئة</h2><p>هذه هي نقطة الدخول الأساسية للقارئ.</p><div class="ency-topic-v2__grid">{topic_cards}</div></section><section class="ency-topic-v2__section"><h2>زوايا المقارنة العشرون</h2><p>تقارن زاوية واحدة عبر مئة موضوع.</p><div class="ency-topic-v2__grid">{angle_cards}</div></section><section class="ency-topic-v2__section"><h2>المسارات التطبيقية الثمانون</h2><p>تجمع موضوعات التصنيف الواحد من زاوية عملية محددة.</p><div class="ency-topic-v2__grid">{path_cards}</div></section></main><script src="{builder.BASE}assets/js/app-v10.js" defer></script><script src="{builder.BASE}assets/js/lab-v12.js" defer></script></body></html>'''


def add_archive_to_sitemap(builder: Any) -> None:
    sitemap = builder.SITE / "sitemap-hubs.xml"
    if not sitemap.is_file():
        raise SystemExit("sitemap-hubs.xml is missing before topic-hub publication")
    tree = ET.parse(sitemap)
    root = tree.getroot()
    namespace = root.tag.split("}", 1)[0] + "}" if root.tag.startswith("{") else ""
    existing = {(node.text or "").strip() for node in root.findall("{*}url/{*}loc")}
    target = builder.BASE + "encyclopedia/all/"
    if target not in existing:
        item = ET.SubElement(root, namespace + "url")
        ET.SubElement(item, namespace + "loc").text = target
        ET.SubElement(item, namespace + "lastmod").text = builder.TODAY
        tree.write(sitemap, encoding="utf-8", xml_declaration=True)


def verify_output(builder: Any, domain_groups: list[tuple[str, list[dict[str, Any]]]], items: list[dict[str, Any]]) -> dict[str, Any]:
    topic_pages = sorted((builder.SITE / "hubs").glob("topic-*/index.html"))
    if len(topic_pages) != TOPIC_COUNT:
        raise SystemExit(f"Expected {TOPIC_COUNT} topic hubs, found {len(topic_pages)}")
    for page in topic_pages:
        text = page.read_text(encoding="utf-8")
        if text.count("<h1") != 1 or 'data-topic-hub-v2="true"' not in text:
            raise SystemExit(f"Invalid topic hub structure: {page}")
        concept_links = set(re.findall(r'href="[^"]*/encyclopedia/(concept-\d{4})/"', text))
        if len(concept_links) != FACET_COUNT:
            raise SystemExit(f"Topic hub must link all {FACET_COUNT} detail pages: {page} ({len(concept_links)})")
    index = (builder.SITE / "encyclopedia" / "index.html").read_text(encoding="utf-8")
    archive = (builder.SITE / "encyclopedia" / "all" / "index.html").read_text(encoding="utf-8")
    if index.count('class="ency-topic-v2__card topic-item"') != TOPIC_COUNT:
        raise SystemExit("Primary encyclopedia index must expose exactly 100 topic cards")
    if archive.count('class="ency-topic-v2__card detail-item"') != DETAIL_COUNT:
        raise SystemExit("Detail archive must expose exactly 2000 detail cards")
    if len(domain_groups) != TOPIC_COUNT or len(items) != DETAIL_COUNT:
        raise SystemExit("Topic or detail count changed unexpectedly")
    return {
        "version": VERSION,
        "status": "passed",
        "primary_navigation": "topic-first",
        "topic_hubs": len(topic_pages),
        "facets_per_topic": FACET_COUNT,
        "detail_pages_preserved": len(items),
        "primary_index_cards": index.count('class="ency-topic-v2__card topic-item"'),
        "detail_archive_cards": archive.count('class="ency-topic-v2__card detail-item"'),
        "topic_groups": [title for title, _, _ in FACET_GROUPS],
        "archive_route": builder.BASE + "encyclopedia/all/",
        "generated": builder.TODAY,
    }


def publish(builder: Any) -> dict[str, Any]:
    if not builder.SITE.is_dir():
        raise SystemExit(f"Site directory not found: {builder.SITE}")
    items = builder.entries()
    domain_groups = unique_domain_groups(items)
    if len(items) != DETAIL_COUNT or len(domain_groups) != TOPIC_COUNT:
        raise SystemExit({"unexpected_encyclopedia_shape": {"items": len(items), "topics": len(domain_groups)}})

    builder.write(builder.SITE / "assets/css/encyclopedia-topic-hubs-v2.css", TOPIC_CSS)
    for domain, group in domain_groups:
        target = builder.SITE / "hubs" / f'topic-{group[0]["domain_index"]:03d}' / "index.html"
        builder.write(target, render_topic_hub(builder, domain, group))

    builder.write(builder.SITE / "encyclopedia" / "index.html", render_topic_index(builder, domain_groups))
    builder.write(builder.SITE / "encyclopedia" / "all" / "index.html", render_detail_archive(builder, items))
    builder.write(builder.SITE / "hubs" / "index.html", render_hubs_index(builder, domain_groups, items))
    add_archive_to_sitemap(builder)

    report = verify_output(builder, domain_groups, items)
    builder.write(
        builder.SITE / "api" / "encyclopedia-topic-hubs-v2.json",
        json.dumps(report, ensure_ascii=False, indent=2),
    )
    return report


if __name__ == "__main__":
    raise SystemExit("Import this publisher from scripts/run_encyclopedia_v13.py so it uses the active builder contract")
