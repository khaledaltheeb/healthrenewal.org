#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
TODAY = date.today().isoformat()

CATEGORY_DEFS = {
    "family-parenting": {
        "name": "الأسرة والتربية",
        "intro": "خطط عملية للروتين والتواصل والاجتماعات الأسرية والخلافات اليومية، مع حماية كرامة الطفل والبالغ.",
        "audience": "الأسر ومقدمو الرعاية",
        "keywords": ["الصحة النفسية للأسرة", "التربية الإيجابية", "التواصل الأسري"],
    },
    "children-teens": {
        "name": "الأطفال والمراهقون",
        "intro": "أدلة لفهم القلق والحزن والمدرسة والتنمر والحوار مع المراهقين دون وصم أو تشخيص سريع.",
        "audience": "الأهل والمعلمون والمرشدون",
        "keywords": ["الصحة النفسية للطفل", "الصحة النفسية للمراهق", "إرشاد الوالدين"],
    },
    "stress-regulation": {
        "name": "التوتر وتنظيم الانفعال",
        "intro": "مهارات لتقليل التصعيد، تنظيم اليوم، التعامل مع التفكير الزائد، وبناء تعافٍ تدريجي قابل للقياس.",
        "audience": "الأفراد والأسر",
        "keywords": ["إدارة التوتر", "تنظيم الانفعال", "المرونة النفسية"],
    },
    "sleep-digital": {
        "name": "النوم والتوازن الرقمي",
        "intro": "إرشادات للنوم الصحي، استخدام الأجهزة، الخصوصية والسلامة الرقمية، وتأثير الروتين الليلي في المزاج.",
        "audience": "الأفراد والأسر",
        "keywords": ["تحسين النوم", "التوازن الرقمي", "الصحة النفسية الرقمية"],
    },
    "relationships": {
        "name": "التواصل والعلاقات",
        "intro": "أدوات للاستماع والحدود والإصلاح بعد الخلاف وإعادة الاتصال الاجتماعي دون سيطرة أو إهانة.",
        "audience": "الأفراد والأزواج والأسر",
        "keywords": ["التواصل الصحي", "الحدود النفسية", "حل الخلافات"],
    },
    "women-perinatal": {
        "name": "صحة المرأة وما حول الولادة",
        "intro": "دعم نفسي عملي للمرأة، مع عناية خاصة بفترة ما بعد الولادة وتوزيع العبء وطلب المساعدة المبكر.",
        "audience": "النساء والأسر ومقدمو الرعاية",
        "keywords": ["الصحة النفسية للمرأة", "ما بعد الولادة", "العناية النفسية"],
    },
    "work-study": {
        "name": "العمل والدراسة",
        "intro": "خطط للتركيز والامتحانات وحدود العمل وإدارة العبء دون تحويل الإنتاجية إلى استنزاف.",
        "audience": "الطلاب والموظفون",
        "keywords": ["ضغط الدراسة", "الصحة النفسية في العمل", "التركيز"],
    },
    "caregivers-inclusion": {
        "name": "مقدمو الرعاية والاحتياجات الخاصة",
        "intro": "أدلة تراعي الاستدامة، الاختلافات الحسية، الانتقالات، وتوسيع المشاركة للأشخاص ذوي الاحتياجات الخاصة.",
        "audience": "الأسر والمعلمون ومقدمو الخدمات",
        "keywords": ["مقدمو الرعاية", "الأشخاص ذوو الاحتياجات الخاصة", "التربية الدامجة"],
    },
    "help-safety": {
        "name": "طلب المساعدة والسلامة",
        "intro": "متى تكفي الخطوة الذاتية، ومتى يلزم مختص، وكيف تستعد للجلسة، وماذا تفعل عند خطر أو أزمة.",
        "audience": "الجمهور العام والأسر",
        "keywords": ["طلب المساعدة النفسية", "السلامة النفسية", "اختيار المختص"],
    },
}

LEGACY_CATEGORY_MAP = {
    "الروتين اليومي": "family-parenting",
    "النوم": "sleep-digital",
    "التواصل": "relationships",
    "الضغط النفسي": "stress-regulation",
    "العلاقات": "relationships",
    "الطفل": "children-teens",
    "المرأة": "women-perinatal",
    "الرقمية": "sleep-digital",
    "الخلاف": "relationships",
    "المراهق": "children-teens",
    "مقدمو الرعاية": "caregivers-inclusion",
    "الفقد": "stress-regulation",
    "الأسرة": "family-parenting",
    "الدراسة": "work-study",
    "البيئة المنزلية": "family-parenting",
    "طلب المساعدة": "help-safety",
    "التعافي": "stress-regulation",
    "العافية": "stress-regulation",
}

SOURCES = [
    {
        "name": "منظمة الصحة العالمية — الصحة النفسية",
        "url": "https://www.who.int/health-topics/mental-health",
        "note": "مرجع للمفاهيم العامة، عوامل الحماية والخطر، وحدود الدعم الذاتي.",
    },
    {
        "name": "منظمة الصحة العالمية — التعامل مع الضغط",
        "url": "https://www.who.int/news-room/questions-and-answers/item/stress",
        "note": "إرشادات عملية للروتين والنوم والحركة والتواصل وتقليل الحمل الإخباري.",
    },
    {
        "name": "منظمة الصحة العالمية — التدخلات النفسية للمساعدة الذاتية",
        "url": "https://www.who.int/teams/mental-health-and-substance-use/treatment-care/Psychological-interventions/psychological-self-help-interventions",
        "note": "إطار للمساعدة الذاتية المنظمة ضمن رعاية متدرجة، لا كبديل شامل عن الخدمات.",
    },
    {
        "name": "منظمة الصحة العالمية — الرعاية الذاتية للصحة والرفاه",
        "url": "https://www.who.int/health-topics/self-care",
        "note": "تأكيد أن الرعاية الذاتية تكمل النظام الصحي ولا تستبدله.",
    },
    {
        "name": "يونيسف للوالدية — الصحة النفسية والرفاه",
        "url": "https://www.unicef.org/parenting/mental-health-and-well-being",
        "note": "محتوى موجه للأسرة حول صحة الطفل ومقدم الرعاية والمحادثات الصعبة.",
    },
    {
        "name": "يونيسف للوالدية — الحوار مع الطفل حول الصحة النفسية",
        "url": "https://www.unicef.org/parenting/mental-health/how-to-talk-to-kids-mental-health",
        "note": "مبادئ للاستماع والشراكة وتقليل ردود الفعل التي تغلق الحوار.",
    },
]

STATIC_PAGES = {
    "how-to-use": {
        "title": "كيف تستخدم أدلة النصائح النفسية؟",
        "description": "طريقة منهجية لاختيار الدليل المناسب، تحويله إلى خطة صغيرة، وقياس الأثر دون تشخيص ذاتي أو تطبيق جامد.",
    },
    "methodology": {
        "title": "منهجية إعداد ومراجعة النصائح النفسية",
        "description": "سياسة التحرير والمصادر والسلامة واللغة والإتاحة والتحديث في قسم النصائح النفسية العملية.",
    },
    "help-now": {
        "title": "متى تحتاج إلى مساعدة عاجلة؟",
        "description": "علامات الخطر والخطوات الأولى لطلب مساعدة عاجلة عند تهديد السلامة أو التدهور الشديد.",
    },
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value)).strip()


def truncate(value: str, limit: int = 158) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip(" ،؛:-") + "…"


def ul(items: list[str], class_name: str = "") -> str:
    cls = f' class="{esc(class_name)}"' if class_name else ""
    return f"<ul{cls}>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def category_for_legacy(category: str) -> str:
    return LEGACY_CATEGORY_MAP.get(category, "stress-regulation")


def default_goals(guide: dict) -> list[str]:
    return [
        f"فهم الموقف المرتبط بـ«{guide['title']}» دون وصم أو استنتاج تشخيصي سريع.",
        "اختيار خطوة صغيرة يمكن تنفيذها ومراجعتها بدل محاولة تغيير كل شيء دفعة واحدة.",
        "معرفة مؤشرات التحسن وحدود المساعدة الذاتية والوقت المناسب لطلب دعم مهني.",
    ]


def default_faq(guide: dict) -> list[list[str]]:
    return [
        [
            "هل يجب تطبيق جميع الخطوات في يوم واحد؟",
            "لا. اختر خطوة واحدة منخفضة العبء، ثبتها، ثم أضف خطوة أخرى بحسب العمر والقدرة والسياق.",
        ],
        [
            "هل هذا الدليل يغني عن المختص؟",
            f"لا. دليل «{guide['title']}» للتثقيف والتنظيم الأولي، ويجب طلب تقييم فردي عند استمرار التعطل أو وجود خطر.",
        ],
    ]


def default_keywords(guide: dict, category_slug: str) -> list[str]:
    category = CATEGORY_DEFS[category_slug]
    return [
        guide["title"],
        guide["category"],
        *category["keywords"],
        "نصائح نفسية",
        "الصحة النفسية",
        "مصطلحات علم النفس",
    ]


def load_guides() -> list[dict]:
    base = json.loads((ROOT / "content/sectors-v10/tips.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "content/v15/tips-details-v15.json").read_text(encoding="utf-8"))
    supplement = json.loads((ROOT / "content/v234/tips-guides-supplement-ar.json").read_text(encoding="utf-8"))

    guides: list[dict] = []
    for item in base.get("guides", []):
        detail = details.get(item["slug"])
        if not detail:
            raise SystemExit(f"Missing v15 detail for {item['slug']}")
        merged = {**item, **detail}
        category_slug = category_for_legacy(merged["category"])
        merged.update(
            {
                "category_slug": category_slug,
                "audience": CATEGORY_DEFS[category_slug]["audience"],
                "goals": default_goals(merged),
                "faq": default_faq(merged),
                "keywords": default_keywords(merged, category_slug),
                "source_generation": "legacy-enriched-v234",
            }
        )
        guides.append(merged)

    for item in supplement.get("guides", []):
        item = dict(item)
        item["source_generation"] = "new-v234"
        guides.append(item)

    slugs = [g["slug"] for g in guides]
    if len(guides) != 36:
        raise SystemExit(f"Expected 36 guides, found {len(guides)}")
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Duplicate guide slugs")
    unknown = sorted({g["category_slug"] for g in guides} - set(CATEGORY_DEFS))
    if unknown:
        raise SystemExit(f"Unknown category slugs: {unknown}")
    return guides


def step_explanation(step: str) -> str:
    step = clean_text(step)
    if any(word in step for word in ("اكتب", "سجل", "دوّن", "راجع", "احفظ")):
        return (
            f"حوّل «{step}» إلى سجل مختصر يذكر الموقف والوقت والأثر وما حدث بعده. "
            "استخدم السجل لاكتشاف الاتجاهات، لا لمراقبة نفسك بصورة قهرية أو إصدار حكم من حادثة واحدة."
        )
    if any(word in step for word in ("اسأل", "استمع", "أخبر", "اشرح", "قل", "اعترف")):
        return (
            f"عند تنفيذ «{step}» استخدم جملة واحدة ونبرة هادئة، ثم اترك وقتًا للرد. "
            "لخّص ما فهمته قبل تقديم الحل، وتجنب الأسئلة المتلاحقة التي تجعل الحوار شبيهًا بالتحقيق."
        )
    if any(word in step for word in ("حدد", "ثبت", "ضع", "اتفق", "اختر", "قسم")):
        return (
            f"اجعل «{step}» محددًا: من المسؤول، متى يبدأ، وما الحد الأدنى المقبول. "
            "كلما كانت الخطة قابلة للملاحظة والمراجعة قل الجدل وزادت فرصة استمرارها."
        )
    if any(word in step for word in ("خفف", "قلل", "أبعد", "أغلق", "تجنب", "لا")):
        return (
            f"طبّق «{step}» تدريجيًا مع بديل واضح بدل المنع المجرد. "
            "راقب الأثر عدة أيام، وعدّل الشدة إذا أدى التغيير إلى ضغط إضافي أو عزل غير مقصود."
        )
    if any(word in step for word in ("اطلب", "شارك", "وزع", "صعّد", "تواصل")):
        return (
            f"صغ «{step}» كطلب عملي يحدد المهمة والشخص والوقت. "
            "الطلب المحدد أسهل في التنفيذ والمتابعة من عبارات عامة، ويكشف مبكرًا إن كانت الموارد غير كافية."
        )
    return (
        f"ابدأ بـ«{step}» في موقف منخفض الضغط، وكررها قبل الانتقال إلى موقف أصعب. "
        "عدّل الأسلوب بحسب العمر والقدرة واللغة والبيئة، ولا تعتبر عدم النجاح من المحاولة الأولى دليلًا على فشل الخطة."
    )


def head(title: str, description: str, canonical: str, keywords: list[str], schema: dict, page_type: str = "article") -> str:
    description = truncate(description)
    key_text = ", ".join(dict.fromkeys(clean_text(x) for x in keywords if clean_text(x)))
    schema_text = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)} | {esc(BRAND)}</title>
<meta name="description" content="{esc(description)}">
<meta name="keywords" content="{esc(key_text)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="author" content="{esc(BRAND)}">
<meta name="application-name" content="{esc(BRAND)}">
<meta name="theme-color" content="#075f5b">
<meta name="color-scheme" content="light">
<meta name="generator" content="Tips Publisher v234">
<link rel="canonical" href="{esc(canonical)}">
<link rel="alternate" hreflang="ar" href="{esc(canonical)}">
<link rel="alternate" hreflang="x-default" href="{esc(canonical)}">
<link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<link rel="icon" href="{BASE_PATH}assets/brand/logo-mark.svg" type="image/svg+xml">
<link rel="stylesheet" href="{BASE_PATH}assets/css/tips-v234.css?v=234">
<meta property="og:type" content="{esc(page_type)}">
<meta property="og:locale" content="ar_AR">
<meta property="og:site_name" content="{esc(BRAND)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{BASE}assets/brand/social-card.svg">
<meta property="og:image:alt" content="هوية {esc(BRAND)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{BASE}assets/brand/social-card.svg">
<script type="application/ld+json">{schema_text}</script>
</head>"""


def site_header() -> str:
    return f"""<a class="skip-link" href="#main-content">تجاوز إلى المحتوى</a>
<header class="tips-shell__header" data-platform-shell="header">
<div class="tips-wrap tips-shell__inner">
<a class="tips-brand" href="{BASE_PATH}" aria-label="الرئيسية">
<span class="tips-brand__mark" aria-hidden="true">ن</span>
<span>{BRAND}<small>معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</small></span>
</a>
<nav class="tips-nav" aria-label="التنقل الرئيسي">
<a href="{BASE_PATH}tips/">النصائح</a>
<a href="{BASE_PATH}tips/how-to-use/">طريقة الاستخدام</a>
<a href="{BASE_PATH}tips/methodology/">المنهجية</a>
<a href="{BASE_PATH}tips/help-now/">المساعدة العاجلة</a>
<a href="{BASE_PATH}encyclopedia/">الموسوعة</a>
</nav>
</div>
</header>"""


def site_footer() -> str:
    return f"""<footer class="tips-shell__footer" data-platform-shell="footer">
<div class="tips-wrap tips-footer-grid">
<section><h2>عن القسم</h2><p>أدلة تثقيفية عملية لا تقدّم تشخيصًا فرديًا ولا وصفة علاجية موحدة.</p></section>
<section><h2>روابط أساسية</h2><p><a href="{BASE_PATH}trust/">الثقة والمنهجية العامة</a> · <a href="{BASE_PATH}partners/">الشفافية والشركاء</a> · <a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a></p></section>
<section><h2>السلامة</h2><p>عند خطر مباشر على النفس أو الآخرين، اتصل بخدمات الطوارئ المحلية أو اذهب إلى أقرب قسم طوارئ.</p></section>
</div>
</footer>"""


def breadcrumb(items: list[tuple[str, str]]) -> str:
    body = "".join(f'<li><a href="{esc(url)}">{esc(name)}</a></li>' for name, url in items[:-1])
    body += f'<li aria-current="page">{esc(items[-1][0])}</li>'
    return f'<nav class="breadcrumbs" aria-label="مسار الصفحة"><ol>{body}</ol></nav>'


def source_list() -> str:
    return "".join(
        f'<li><a href="{esc(item["url"])}" rel="noopener noreferrer">{esc(item["name"])}</a><p>{esc(item["note"])}</p></li>'
        for item in SOURCES
    )


def organization_schema() -> dict:
    return {
        "@type": "Organization",
        "@id": BASE + "#organization",
        "name": BRAND,
        "alternateName": "مصطلحات علم النفس",
        "url": BASE,
        "logo": {"@type": "ImageObject", "url": BASE + "assets/brand/logo-mark.svg"},
        "sameAs": [
            "https://www.instagram.com/pterminology/",
            "https://www.youtube.com/@psychology-term",
        ],
    }


def website_schema() -> dict:
    return {
        "@type": "WebSite",
        "@id": BASE + "#website",
        "name": BRAND,
        "url": BASE,
        "inLanguage": "ar",
        "publisher": {"@id": BASE + "#organization"},
    }


def guide_schema(guide: dict, canonical: str) -> dict:
    steps = [
        {
            "@type": "HowToStep",
            "position": index + 1,
            "name": step,
            "text": step_explanation(step),
        }
        for index, step in enumerate(guide["tips"])
    ]
    faq = [
        {
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        }
        for question, answer in guide["faq"]
    ]
    return {
        "@context": "https://schema.org",
        "@graph": [
            organization_schema(),
            website_schema(),
            {
                "@type": "Article",
                "@id": canonical + "#article",
                "headline": guide["title"],
                "description": guide["summary"],
                "inLanguage": "ar",
                "dateModified": TODAY,
                "mainEntityOfPage": canonical,
                "author": {"@id": BASE + "#organization"},
                "publisher": {"@id": BASE + "#organization"},
                "about": [
                    {"@type": "Thing", "name": guide["category"]},
                    {"@type": "Audience", "audienceType": guide["audience"]},
                ],
                "isPartOf": {"@id": BASE + "tips/#collection"},
            },
            {
                "@type": "HowTo",
                "@id": canonical + "#howto",
                "name": guide["title"],
                "description": guide["summary"],
                "inLanguage": "ar",
                "step": steps,
            },
            {
                "@type": "FAQPage",
                "@id": canonical + "#faq",
                "mainEntity": faq,
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "النصائح", "item": BASE + "tips/"},
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": CATEGORY_DEFS[guide["category_slug"]]["name"],
                        "item": BASE + "tips/categories/" + guide["category_slug"] + "/",
                    },
                    {"@type": "ListItem", "position": 4, "name": guide["title"], "item": canonical},
                ],
            },
        ],
    }


def related_guides(guide: dict, guides: list[dict]) -> list[dict]:
    same = [item for item in guides if item["slug"] != guide["slug"] and item["category_slug"] == guide["category_slug"]]
    other = [item for item in guides if item["slug"] != guide["slug"] and item not in same]
    return (same + other)[:3]


def guide_page(guide: dict, guides: list[dict]) -> str:
    canonical = BASE + "tips/" + guide["slug"] + "/"
    category = CATEGORY_DEFS[guide["category_slug"]]
    goals = "".join(f"<article class='tips-mini-card'><h3>هدف {index}</h3><p>{esc(goal)}</p></article>" for index, goal in enumerate(guide["goals"], 1))
    steps = "".join(
        f"""<article class="tips-step">
<span class="tips-step__number" aria-hidden="true">{index}</span>
<div><h3>{esc(step)}</h3><p>{esc(step_explanation(step))}</p></div>
</article>"""
        for index, step in enumerate(guide["tips"], 1)
    )
    faq = "".join(
        f"<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>"
        for question, answer in guide["faq"]
    )
    related = "".join(
        f"""<article class="tips-card"><span class="tips-badge">{esc(item["category"])}</span>
<h3><a href="{BASE_PATH}tips/{esc(item["slug"])}/">{esc(item["title"])}</a></h3>
<p>{esc(item["summary"])}</p></article>"""
        for item in related_guides(guide, guides)
    )
    keywords = default_keywords(guide, guide["category_slug"]) if not guide.get("keywords") else guide["keywords"]
    schema = guide_schema(guide, canonical)
    return head(guide["title"], guide["summary"], canonical, keywords, schema) + f"""<body>
{site_header()}
<main id="main-content">
<div class="tips-wrap">
{breadcrumb([("الرئيسية", BASE_PATH), ("النصائح", BASE_PATH + "tips/"), (category["name"], BASE_PATH + "tips/categories/" + guide["category_slug"] + "/"), (guide["title"], canonical)])}
<section class="tips-hero tips-hero--guide">
<div class="tips-kicker"><span class="tips-badge">{esc(category["name"])}</span><span class="tips-badge">{esc(guide["audience"])}</span><span class="tips-badge">مراجعة {TODAY}</span></div>
<h1>{esc(guide["title"])}</h1>
<p class="tips-lead">{esc(guide["summary"])}</p>
<div class="tips-actions"><a class="tips-button" href="#plan">ابدأ الخطة</a><a class="tips-button tips-button--secondary" href="{BASE_PATH}tips/how-to-use/">طريقة الاستخدام الآمن</a></div>
</section>
<aside class="tips-alert" aria-labelledby="safety-title"><h2 id="safety-title">قبل أن تبدأ</h2><p>هذا الدليل للتثقيف والتنظيم الأولي، وليس تشخيصًا أو بديلًا عن رعاية مهنية فردية. عدّل الخطوات بحسب العمر والقدرة والسياق، وأوقف أي خطوة تزيد الخطر أو الضيق بشدة.</p></aside>
<div class="tips-layout">
<article class="tips-article">
<section><h2>متى يفيد هذا الدليل؟</h2><p>{esc(guide["when"])}</p><p>ابدأ بعد التأكد من عدم وجود خطر مباشر أو مشكلة طبية عاجلة. الهدف هو تحسين الوظيفة والأمان والتواصل، لا إلغاء كل شعور مزعج أو فرض هدوء كامل.</p></section>
<section><h2>الأهداف العملية</h2><div class="tips-grid tips-grid--3">{goals}</div></section>
<section><h2>المبدأ الذي تقوم عليه الخطة</h2><p>التغيير النفسي والسلوكي عادة تراكمي. الخطوات الصغيرة الواضحة، والمتابعة على عدة أيام، والتعديل حسب الاستجابة أكثر فائدة من التعليمات الكثيرة أو الوعود السريعة. الرعاية الذاتية المنظمة تكمل الخدمات الصحية ولا تستبدلها.</p></section>
<section id="plan"><h2>خطة التنفيذ خطوة بخطوة</h2><div class="tips-steps">{steps}</div></section>
<section><h2>جملة جاهزة للاستخدام</h2><blockquote>{esc(guide["script"])}</blockquote><p>استخدم الجملة كنقطة بداية، ثم عدّلها بحيث تبقى قصيرة ومحترمة ومحددة. تجنب الشرح الطويل أثناء التصعيد.</p></section>
<section><h2>ما الذي يجب تجنبه؟</h2><p>{esc(guide["avoid"])}</p></section>
<section><h2>كيف تتابع التحسن؟</h2><p>{esc(guide["success"])}</p>
<div class="tips-checklist"><h3>ورقة متابعة مختصرة</h3>{ul(["ما الموقف المحدد الذي نعمل عليه؟","ما الخطوة الواحدة التي سنجربها؟","متى سنراجع أثرها؟","ما علامة التحسن القابلة للملاحظة؟"], "tips-checklist__list")}</div>
</section>
<section class="tips-danger"><h2>متى تطلب مساعدة مهنية أو عاجلة؟</h2><p>{esc(guide["seek_help"])}</p><p><strong>عند خطر مباشر على النفس أو الآخرين، أو فقدان شديد للاتصال بالواقع، أو تدهور صحي حاد: استخدم خدمات الطوارئ المحلية فورًا.</strong></p></section>
<section><h2>أسئلة شائعة</h2><div class="tips-faq">{faq}</div></section>
<section><h2>مصادر موثوقة للتوسع</h2><p>هذه المصادر تدعم المبادئ العامة للقسم. لا يعني إدراجها أن كل خطوة تناسب كل شخص أو أنها بديل عن التقييم الفردي.</p><ol class="tips-sources">{source_list()}</ol></section>
</article>
<aside class="tips-sidebar" aria-label="معلومات الدليل">
<section><h2>ملخص سريع</h2><dl><dt>الفئة</dt><dd>{esc(category["name"])}</dd><dt>الجمهور</dt><dd>{esc(guide["audience"])}</dd><dt>عدد الخطوات</dt><dd>{len(guide["tips"])}</dd><dt>نوع المحتوى</dt><dd>تثقيف ودعم عملي</dd></dl></section>
<section><h2>أدلة مرتبطة</h2><div class="tips-related">{related}</div></section>
<section><h2>روابط آمنة</h2><p><a href="{BASE_PATH}tips/help-now/">علامات الخطر والمساعدة العاجلة</a></p><p><a href="{BASE_PATH}tips/methodology/">منهجية التحرير والمراجعة</a></p></section>
</aside>
</div>
</div>
</main>
{site_footer()}
</body></html>"""


def collection_schema(title: str, description: str, canonical: str, items: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            organization_schema(),
            website_schema(),
            {
                "@type": "CollectionPage",
                "@id": canonical + "#collection",
                "name": title,
                "description": description,
                "url": canonical,
                "inLanguage": "ar",
                "isPartOf": {"@id": BASE + "#website"},
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": len(items),
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": index + 1,
                            "name": item["title"],
                            "url": BASE + "tips/" + item["slug"] + "/",
                        }
                        for index, item in enumerate(items)
                    ],
                },
            },
        ],
    }


def guide_cards(guides: list[dict]) -> str:
    return "".join(
        f"""<article class="tips-card" data-guide data-category="{esc(guide["category_slug"])}" data-search="{esc(" ".join([guide["title"], guide["summary"], guide["category"], guide["audience"], *guide.get("keywords", [])]))}">
<span class="tips-badge">{esc(CATEGORY_DEFS[guide["category_slug"]]["name"])}</span>
<h2><a href="{BASE_PATH}tips/{esc(guide["slug"])}/">{esc(guide["title"])}</a></h2>
<p>{esc(guide["summary"])}</p>
<ul class="tips-card__meta"><li>{esc(guide["audience"])}</li><li>{len(guide["tips"])} خطوات</li></ul>
<a class="tips-text-link" href="{BASE_PATH}tips/{esc(guide["slug"])}/">فتح الدليل الكامل</a>
</article>"""
        for guide in guides
    )


def index_page(guides: list[dict]) -> str:
    canonical = BASE + "tips/"
    description = "مكتبة عربية مؤسسية تضم 36 دليلًا نفسيًا عمليًا للأسرة والطفل والمرأة والعمل والنوم والعلاقات ومقدمي الرعاية، مع منهجية ومصادر وحدود سلامة."
    counts = Counter(g["category_slug"] for g in guides)
    category_cards = "".join(
        f"""<article class="tips-category-card">
<span class="tips-stat">{counts[slug]} أدلة</span>
<h2><a href="{BASE_PATH}tips/categories/{slug}/">{esc(meta["name"])}</a></h2>
<p>{esc(meta["intro"])}</p>
<a class="tips-text-link" href="{BASE_PATH}tips/categories/{slug}/">استعراض الفئة</a>
</article>"""
        for slug, meta in CATEGORY_DEFS.items()
    )
    filters = "".join(
        f'<button type="button" class="tips-filter" data-filter="{slug}">{esc(meta["name"])}</button>'
        for slug, meta in CATEGORY_DEFS.items()
    )
    schema = collection_schema("النصائح النفسية العملية", description, canonical, guides)
    return head(
        "النصائح النفسية العملية",
        description,
        canonical,
        ["نصائح نفسية", "الصحة النفسية", "إرشاد أسري", "الصحة النفسية للطفل", "النوم", "التوتر", "العلاقات", "مقدمو الرعاية"],
        schema,
        "website",
    ) + f"""<body>
{site_header()}
<main id="main-content">
<div class="tips-wrap">
<section class="tips-hero">
<p class="tips-eyebrow">مكتبة تطبيقية عربية موثقة</p>
<h1>النصائح النفسية العملية</h1>
<p class="tips-lead">ليست شعارات سريعة ولا تشخيصًا ذاتيًا. هذه مكتبة من <strong>{len(guides)} دليلًا</strong> ضمن <strong>{len(CATEGORY_DEFS)} فئات</strong>، تشرح متى تستخدم الخطة، وكيف تنفذها، وما الذي تتجنبه، وكيف تتابع التحسن، ومتى تحتاج إلى مختص.</p>
<div class="tips-actions"><a class="tips-button" href="#all-guides">استعرض الأدلة</a><a class="tips-button tips-button--secondary" href="{BASE_PATH}tips/how-to-use/">ابدأ بطريقة صحيحة</a></div>
<div class="tips-stats"><div><strong>{len(guides)}</strong><span>دليلًا عمليًا</span></div><div><strong>{len(CATEGORY_DEFS)}</strong><span>فئات موضوعية</span></div><div><strong>{len(SOURCES)}</strong><span>مراجع مؤسسية</span></div><div><strong>0</strong><span>تشخيصات آلية</span></div></div>
</section>
<section class="tips-priority-grid" aria-label="روابط البدء">
<a href="{BASE_PATH}tips/how-to-use/"><strong>كيف تستخدم الدليل؟</strong><span>اختيار خطوة، قياس أثر، وتجنب التطبيق الجامد.</span></a>
<a href="{BASE_PATH}tips/methodology/"><strong>كيف نراجع المحتوى؟</strong><span>المصادر والسلامة والإتاحة والتحديث.</span></a>
<a class="tips-priority-grid__danger" href="{BASE_PATH}tips/help-now/"><strong>هل يوجد خطر الآن؟</strong><span>علامات تستدعي مساعدة عاجلة.</span></a>
</section>
<section class="tips-section"><div class="tips-section__head"><div><p class="tips-eyebrow">التنظيم الموضوعي</p><h2>اختر الفئة الأقرب إلى الموقف</h2></div><p>التصنيف حسب الحاجة والموقف، لا حسب افتراض تشخيص.</p></div><div class="tips-grid tips-grid--3">{category_cards}</div></section>
<section class="tips-section" id="all-guides">
<div class="tips-section__head"><div><p class="tips-eyebrow">البحث والتصفية</p><h2>جميع الأدلة</h2></div><p id="tips-results" aria-live="polite">{len(guides)} نتيجة</p></div>
<label class="tips-search-label" for="tips-search">ابحث بعنوان أو موقف أو جمهور</label>
<input class="tips-search" id="tips-search" type="search" placeholder="مثال: النوم، المراهق، التوتر، مقدم الرعاية">
<div class="tips-filters" aria-label="تصفية الفئات"><button type="button" class="tips-filter is-active" data-filter="all">الكل</button>{filters}</div>
<div class="tips-grid tips-grid--3" id="tips-guide-grid">{guide_cards(guides)}</div>
<p class="tips-empty" id="tips-empty" hidden>لا توجد نتائج مطابقة. جرّب كلمة أوسع أو اختر فئة أخرى.</p>
</section>
<section class="tips-section tips-section--soft"><h2>حدود القسم</h2><div class="tips-grid tips-grid--3">
<article class="tips-mini-card"><h3>لا تشخيص</h3><p>لا نستنتج اضطرابًا من موقف أو نتيجة أداة، ولا نقدم علاجًا مضمونًا.</p></article>
<article class="tips-mini-card"><h3>لا وصفات دوائية</h3><p>لا ننصح ببدء دواء أو إيقافه أو تعديل جرعته؛ ذلك للطبيب الواصف.</p></article>
<article class="tips-mini-card"><h3>الأمان أولًا</h3><p>الخطر المباشر أو التدهور الحاد ينتقل إلى الطوارئ أو الرعاية المهنية، لا إلى تجربة نصائح إضافية.</p></article>
</div></section>
</div>
</main>
{site_footer()}
<script>
(()=>{{"use strict";
const input=document.getElementById("tips-search");
const cards=[...document.querySelectorAll("[data-guide]")];
const filters=[...document.querySelectorAll("[data-filter]")];
const result=document.getElementById("tips-results");
const empty=document.getElementById("tips-empty");
let active="all";
function normalize(value){{return (value||"").toLocaleLowerCase("ar").replace(/[\u064B-\u065F\u0670]/g,"").trim();}}
function apply(){{
 const query=normalize(input.value);
 let shown=0;
 cards.forEach(card=>{{
   const matchesCategory=active==="all"||card.dataset.category===active;
   const matchesText=!query||normalize(card.dataset.search).includes(query);
   card.hidden=!(matchesCategory&&matchesText);
   if(!card.hidden)shown++;
 }});
 result.textContent=shown+" نتيجة";
 empty.hidden=shown!==0;
}}
filters.forEach(button=>button.addEventListener("click",()=>{{
 active=button.dataset.filter;
 filters.forEach(item=>item.classList.toggle("is-active",item===button));
 apply();
}}));
input.addEventListener("input",apply);
}})();
</script>
</body></html>"""


def category_page(slug: str, guides: list[dict]) -> str:
    meta = CATEGORY_DEFS[slug]
    selected = [guide for guide in guides if guide["category_slug"] == slug]
    canonical = BASE + "tips/categories/" + slug + "/"
    description = f"{meta['intro']} تضم الفئة {len(selected)} أدلة عربية عملية مع خطوات ومؤشرات تقدم وحدود لطلب المساعدة."
    schema = collection_schema(meta["name"], description, canonical, selected)
    return head(meta["name"], description, canonical, [*meta["keywords"], "نصائح نفسية", "الصحة النفسية"], schema, "website") + f"""<body>
{site_header()}
<main id="main-content"><div class="tips-wrap">
{breadcrumb([("الرئيسية", BASE_PATH), ("النصائح", BASE_PATH + "tips/"), (meta["name"], canonical)])}
<section class="tips-hero"><p class="tips-eyebrow">فئة موضوعية · {len(selected)} أدلة</p><h1>{esc(meta["name"])}</h1><p class="tips-lead">{esc(meta["intro"])}</p><p><strong>الجمهور الأساسي:</strong> {esc(meta["audience"])}</p></section>
<section class="tips-section"><h2>كيف تختار دليلًا من هذه الفئة؟</h2><p>اختر الصفحة التي تصف الموقف الحالي بأكبر قدر من الدقة. لا تجمع عدة خطط في الوقت نفسه؛ ابدأ بخطوة واحدة، وحدد موعدًا للمراجعة، وانتقل إلى المساعدة المهنية عندما يكون التعطل أو الخطر أكبر من قدرة الإرشاد العام.</p></section>
<section class="tips-section"><h2>أدلة {esc(meta["name"])}</h2><div class="tips-grid tips-grid--3">{guide_cards(selected)}</div></section>
<section class="tips-section tips-section--soft"><h2>انتقل إلى فئة أخرى</h2><div class="tips-link-cloud">{"".join(f'<a href="{BASE_PATH}tips/categories/{other}/">{esc(info["name"])}</a>' for other, info in CATEGORY_DEFS.items() if other != slug)}</div></section>
</div></main>
{site_footer()}
</body></html>"""


def static_schema(title: str, description: str, canonical: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@graph": [
            organization_schema(),
            website_schema(),
            {
                "@type": "Article",
                "headline": title,
                "description": description,
                "url": canonical,
                "inLanguage": "ar",
                "dateModified": TODAY,
                "author": {"@id": BASE + "#organization"},
                "publisher": {"@id": BASE + "#organization"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "النصائح", "item": BASE + "tips/"},
                    {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
                ],
            },
        ],
    }


def how_to_use_page() -> str:
    meta = STATIC_PAGES["how-to-use"]
    body = f"""<section class="tips-section"><h2>1. حدّد الموقف لا التشخيص</h2><p>اكتب ما يحدث الآن: متى يبدأ، من يتأثر، وما الوظيفة المتعطلة. لا تبدأ بعبارة «لديه اضطراب كذا» ما لم يوجد تقييم مهني موثق.</p></section>
<section class="tips-section"><h2>2. اختر هدفًا واحدًا</h2>{ul(["تقليل مدة التصعيد","تحسين خطوة في الروتين","زيادة تواصل آمن","الوصول إلى مساعدة مهنية"], "tips-checklist__list")}</section>
<section class="tips-section"><h2>3. طبّق خطوة صغيرة</h2><p>اختر خطوة يمكن تنفيذها خلال اليوم أو الأسبوع. حدد الشخص والوقت والمدة والبديل عند التعثر.</p></section>
<section class="tips-section"><h2>4. راقب الأثر لا الانطباع فقط</h2><p>دوّن مؤشرًا بسيطًا مثل عدد مرات التذكير، وقت النوم، مدة الخلاف، أو حضور المدرسة. راجع الاتجاه بعد عدة أيام.</p></section>
<section class="tips-section"><h2>5. عدّل أو توقف</h2><p>إذا لم تتحسن الوظيفة، أو زاد الضيق، أو ظهر خطر، فلا تكرر الخطة نفسها بعناد. انتقل إلى تقييم مهني أو مسار أكثر أمانًا.</p></section>
<section class="tips-section tips-section--soft"><h2>قاعدة عملية</h2><blockquote>دليل واحد، هدف واحد، خطوة واحدة، مؤشر واحد، وموعد مراجعة واضح.</blockquote></section>"""
    return static_page("how-to-use", meta, body)


def methodology_page() -> str:
    meta = STATIC_PAGES["methodology"]
    body = f"""<section class="tips-section"><h2>نطاق المحتوى</h2><p>القسم يقدم تثقيفًا نفسيًا وإرشادات تنظيم أولي للأسرة والفرد ومقدم الرعاية. لا يقدم تشخيصًا فرديًا، ولا وصفات دوائية، ولا بديلًا عن خدمات الطوارئ أو العلاج.</p></section>
<section class="tips-section"><h2>هرم المصادر</h2>{ul(["منظمات صحية وحقوقية دولية موثوقة","إرشادات وطنية أو مهنية رسمية","مراجعات منهجية وأبحاث محكمة عند الحاجة","خبرة تطبيقية تصاغ بحذر ولا تقدم كحقيقة مطلقة"], "tips-checklist__list")}</section>
<section class="tips-section"><h2>قواعد التحرير</h2>{ul(["لغة تحترم الإنسان وتصف الحاجة دون وصم","فصل المعلومة العامة عن التوصية الفردية","إظهار علامات الخطر وحدود المساعدة الذاتية","أهداف وخطوات ومؤشرات قابلة للملاحظة","روابط داخلية وصفية وبيانات منظمة قابلة للفهرسة"], "tips-checklist__list")}</section>
<section class="tips-section"><h2>الإتاحة والجودة التقنية</h2><p>يستخدم القسم اتجاهًا عربيًا صحيحًا، عناوين هرمية، روابط قابلة للوحة المفاتيح، تباينًا واضحًا، تصميمًا متجاوبًا، وضع طباعة، ودعم تقليل الحركة.</p></section>
<section class="tips-section"><h2>المراجعة والتحديث</h2><p>تحمل الصفحات تاريخ تعديل، ويخرج الناشر تقريرًا آليًا بعدد الصفحات والفئات والمصادر والبيانات الوصفية. يجب أن تمنع الاختبارات العناوين المكررة، والروابط الداخلية الخاطئة، والصفحات الرقيقة، وغياب بيانات السلامة.</p></section>
<section class="tips-section"><h2>المصادر المؤسسية الحالية</h2><ol class="tips-sources">{source_list()}</ol></section>"""
    return static_page("methodology", meta, body)


def help_now_page() -> str:
    meta = STATIC_PAGES["help-now"]
    body = f"""<section class="tips-danger"><h2>استخدم مساعدة عاجلة الآن عند وجود:</h2>{ul(["خطر مباشر على النفس أو الآخرين","محاولة إيذاء أو خطة أو وسيلة متاحة","فقدان شديد للاتصال بالواقع أو ارتباك حاد","عنف أو تهديد أو استغلال مستمر","تدهور صحي حاد أو جرعة زائدة أو فقد وعي","عجز عن رعاية الاحتياجات الأساسية مع خطر واضح"], "tips-checklist__list")}</section>
<section class="tips-section"><h2>الخطوات الأولى</h2><ol><li>ابق مع الشخص إذا كان ذلك آمنًا.</li><li>أبعد الوسائل الخطرة دون تعريض نفسك للخطر.</li><li>اتصل بخدمات الطوارئ المحلية أو توجّه إلى أقرب قسم طوارئ.</li><li>أخبر شخصًا بالغًا موثوقًا ولا تحمل السر وحدك.</li><li>قدّم معلومات واضحة: الموقع، نوع الخطر، وما تم فعله.</li></ol></section>
<section class="tips-section"><h2>ما الذي لا تفعله؟</h2>{ul(["لا تعد بالسرية عند وجود خطر","لا تجادل الشخص لإثبات أن مشاعره غير منطقية","لا تتركه وحده أثناء خطر وشيك","لا تعطه دواءً غير موصوف","لا تعتمد على نصيحة إلكترونية بدل الطوارئ"], "tips-checklist__list")}</section>
<section class="tips-section tips-section--soft"><h2>بعد زوال الخطر المباشر</h2><p>رتب متابعة مهنية، واكتب خطة أمان، وحدد من يتواصل مع من، وما العلامات المبكرة، وكيف تحفظ الأدوية والوسائل الخطرة بصورة آمنة.</p></section>"""
    return static_page("help-now", meta, body)


def static_page(slug: str, meta: dict, body: str) -> str:
    canonical = BASE + "tips/" + slug + "/"
    schema = static_schema(meta["title"], meta["description"], canonical)
    return head(meta["title"], meta["description"], canonical, [meta["title"], "نصائح نفسية", "الصحة النفسية", "السلامة النفسية"], schema) + f"""<body>
{site_header()}
<main id="main-content"><div class="tips-wrap">
{breadcrumb([("الرئيسية", BASE_PATH), ("النصائح", BASE_PATH + "tips/"), (meta["title"], canonical)])}
<section class="tips-hero"><p class="tips-eyebrow">دليل مؤسسي للقسم</p><h1>{esc(meta["title"])}</h1><p class="tips-lead">{esc(meta["description"])}</p></section>
<article class="tips-article tips-article--standalone">{body}</article>
</div></main>
{site_footer()}
</body></html>"""


def write_page(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_sitemap(site: Path, urls: list[str]) -> None:
    root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for url in urls:
        node = ET.SubElement(root, "url")
        ET.SubElement(node, "loc").text = url
        ET.SubElement(node, "lastmod").text = TODAY
        ET.SubElement(node, "changefreq").text = "monthly"
        ET.SubElement(node, "priority").text = "0.90" if url == BASE + "tips/" else "0.76"
    target = site / "sitemap-tips.xml"
    ET.ElementTree(root).write(target, encoding="utf-8", xml_declaration=True)

    sitemap_index = site / "sitemap.xml"
    if sitemap_index.exists():
        text = sitemap_index.read_text(encoding="utf-8")
        sitemap_url = BASE + "sitemap-tips.xml"
        if sitemap_url not in text:
            if "<sitemapindex" in text and "</sitemapindex>" in text:
                text = text.replace("</sitemapindex>", f"<sitemap><loc>{sitemap_url}</loc><lastmod>{TODAY}</lastmod></sitemap></sitemapindex>")
            sitemap_index.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")

    guides = load_guides()
    tips = site / "tips"
    if tips.exists():
        shutil.rmtree(tips)
    tips.mkdir(parents=True)

    css_source = ROOT / "content/v234/tips-v234.css"
    css_target = site / "assets/css/tips-v234.css"
    css_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(css_source, css_target)

    write_page(tips / "index.html", index_page(guides))
    write_page(tips / "how-to-use/index.html", how_to_use_page())
    write_page(tips / "methodology/index.html", methodology_page())
    write_page(tips / "help-now/index.html", help_now_page())

    urls = [
        BASE + "tips/",
        BASE + "tips/how-to-use/",
        BASE + "tips/methodology/",
        BASE + "tips/help-now/",
    ]
    for slug in CATEGORY_DEFS:
        write_page(tips / "categories" / slug / "index.html", category_page(slug, guides))
        urls.append(BASE + "tips/categories/" + slug + "/")
    for guide in guides:
        write_page(tips / guide["slug"] / "index.html", guide_page(guide, guides))
        urls.append(BASE + "tips/" + guide["slug"] + "/")

    write_sitemap(site, urls)

    export = {
        "version": 234,
        "updated": TODAY,
        "title": "النصائح النفسية العملية",
        "description": "أدلة عربية عملية منظمة حسب الموقف، مع خطوات ومؤشرات تقدم وحدود سلامة.",
        "guide_count": len(guides),
        "category_count": len(CATEGORY_DEFS),
        "page_count": len(urls),
        "categories": [
            {
                "slug": slug,
                **meta,
                "guide_count": sum(guide["category_slug"] == slug for guide in guides),
                "url": BASE + "tips/categories/" + slug + "/",
            }
            for slug, meta in CATEGORY_DEFS.items()
        ],
        "guides": [
            {
                "slug": guide["slug"],
                "title": guide["title"],
                "category": guide["category"],
                "category_slug": guide["category_slug"],
                "audience": guide["audience"],
                "summary": guide["summary"],
                "url": BASE + "tips/" + guide["slug"] + "/",
                "keywords": guide.get("keywords", []),
            }
            for guide in guides
        ],
        "sources": SOURCES,
        "safety": {
            "diagnostic": False,
            "medication_advice": False,
            "urgent_help_page": BASE + "tips/help-now/",
        },
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "tips-v234.json").write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
    api_v1 = api / "v1"
    api_v1.mkdir(parents=True, exist_ok=True)
    (api_v1 / "tips.json").write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")

    pages = list(tips.rglob("index.html"))
    min_words = min(len(re.findall(r"[\u0600-\u06FF]+", re.sub(r"<[^>]+>", " ", page.read_text(encoding="utf-8")))) for page in pages)
    report = {
        "version": 234,
        "status": "built-not-published",
        "guide_count": len(guides),
        "legacy_guides_enriched": sum(g["source_generation"] == "legacy-enriched-v234" for g in guides),
        "new_guides": sum(g["source_generation"] == "new-v234" for g in guides),
        "category_count": len(CATEGORY_DEFS),
        "static_pages": len(STATIC_PAGES),
        "page_count": len(pages),
        "sitemap_urls": len(urls),
        "source_count": len(SOURCES),
        "minimum_rendered_arabic_words": min_words,
        "metadata": {
            "canonical": True,
            "hreflang": True,
            "robots": True,
            "keywords": True,
            "open_graph": True,
            "twitter_cards": True,
            "structured_data": ["Organization", "WebSite", "CollectionPage", "ItemList", "Article", "HowTo", "FAQPage", "BreadcrumbList"],
        },
        "accessibility": {
            "rtl": True,
            "skip_link": True,
            "keyboard_focus": True,
            "reduced_motion": True,
            "print_styles": True,
        },
        "robots_txt": (site / "robots.txt").exists(),
        "sitemap": "sitemap-tips.xml",
        "api": ["api/tips-v234.json", "api/v1/tips.json"],
    }
    (api / "tips-audit-v234.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
