from __future__ import annotations

import html
import json
import re
from datetime import date
from typing import Any

BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
TODAY = date.today().isoformat()

SECTION_LABELS = {
    "understanding": "فهم الحالة دون وصم",
    "what_the_person_may_feel": "ما الذي قد يشعر به الشخص من الداخل؟",
    "strengths_and_differences": "نقاط القوة والفروق الفردية",
    "first_minutes": "الخطوات الأولى",
    "observe": "ما الذي نراقبه؟",
    "assessment_questions": "أسئلة تساعد على فهم الموقف",
    "communication_plan": "خطة التواصل",
    "conversation_plan": "خطة بدء الحوار",
    "conversation_steps": "خطوات الحوار",
    "sensory_plan": "خطة التنظيم الحسي",
    "do": "ما الذي يمكن فعله؟",
    "avoid": "ما الذي ينبغي تجنبه؟",
    "daily_plan": "خطة الحياة اليومية",
    "home_plan": "خطة الدعم في المنزل",
    "school_plan": "خطة الدعم في المدرسة",
    "family_plan": "خطة الأسرة",
    "workload_map": "خريطة عبء الرعاية",
    "plan": "خطة عملية مستدامة",
    "homework_protocol": "بروتوكول الواجبات وبدء المهام",
    "transition_protocol": "بروتوكول الانتقالات والتغيير",
    "meltdown_protocol": "بروتوكول الانهيار والتصعيد",
    "wandering_protocol": "بروتوكول الخروج أو الضياع",
    "emotion_protocol": "بروتوكول الانفعال والتصعيد",
    "sleep_plan": "خطة النوم",
    "food_plan": "خطة الطعام والتغذية",
    "medication_awareness": "السلامة الدوائية وحدود دور الأسرة",
    "when_to_seek_help": "متى نطلب مساعدة مهنية؟",
    "warning_signs": "إشارات الخطر أو التدهور",
    "caregiver_plan": "خطة مقدم الرعاية",
    "questions_for_professional": "أسئلة مقترحة للموعد المهني",
}
SECTION_ORDER = tuple(SECTION_LABELS)

CORE_CATEGORY_BY_SLUG = {
    "support-person-in-distress": "immediate-support",
    "family-support-depression": "mood-and-severe",
    "child-emotional-change": "life-stages",
    "support-psychosis-family": "mood-and-severe",
    "grief-support": "family-care",
    "caregiver-self-care-boundaries": "family-care",
    "adhd-family-practical-guide": "life-stages",
    "autism-family-practical-guide": "life-stages",
}
CORE_SHORT_TITLE = {
    "support-person-in-distress": "مساندة شخص في ضيق",
    "family-support-depression": "دعم الأسرة مع الاكتئاب",
    "child-emotional-change": "تغير مزاج الطفل",
    "support-psychosis-family": "الاشتباه بأعراض ذهانية",
    "grief-support": "المساندة في الحداد",
    "caregiver-self-care-boundaries": "حدود مقدم الرعاية",
    "adhd-family-practical-guide": "دليل الأسرة لـ ADHD",
    "autism-family-practical-guide": "دليل الأسرة للتوحد",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)

def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def words(value: str) -> int:
    return len(re.findall(r"[\u0600-\u06ffA-Za-z0-9]+", value))

def json_script(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

def valid_date(value: object) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))

def normalize_guide(raw: dict[str, Any]) -> dict[str, Any]:
    guide = dict(raw)
    slug = guide["slug"]
    guide.setdefault("category", CORE_CATEGORY_BY_SLUG.get(slug, "family-care"))
    guide.setdefault("short_title", CORE_SHORT_TITLE.get(slug, guide["title"]))
    guide.setdefault("search_intent", [])
    guide.setdefault("audience", [])
    guide.setdefault("external_specialist_review", False)
    return guide

def category_map(expansion: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {item["id"]: item for item in expansion["categories"]}

def keyword_text(guide: dict[str, Any], category_label: str) -> str:
    values = [
        guide["title"], guide.get("short_title", ""), category_label,
        *guide.get("search_intent", []), *guide.get("audience", []),
        "الصحة النفسية", "دعم الأسرة", "مقدمو الرعاية", "مصطلحات علم النفس"
    ]
    return compact("، ".join(dict.fromkeys(v for v in values if v)))[:480]

def head(title: str, description: str, canonical: str, keywords: str, schema: dict[str, Any], *, page_type: str = "article", modified: str = "") -> str:
    modified_meta = f'<meta property="article:modified_time" content="{esc(modified)}">' if valid_date(modified) else ""
    return (
        '<!doctype html><html lang="ar" dir="rtl"><head>'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        f'<title>{esc(title)} | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>'
        f'<meta name="description" content="{esc(description)}">'
        f'<meta name="keywords" content="{esc(keywords)}">'
        '<meta name="author" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">'
        '<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">'
        '<meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">'
        '<meta name="referrer" content="strict-origin-when-cross-origin">'
        '<meta name="theme-color" content="#0b6f69"><meta name="color-scheme" content="light">'
        f'<link rel="canonical" href="{esc(canonical)}">'
        f'<link rel="alternate" hreflang="ar" href="{esc(canonical)}">'
        f'<link rel="alternate" hreflang="x-default" href="{esc(canonical)}">'
        f'<link rel="manifest" href="{BASE_PATH}manifest.webmanifest">'
        f'<meta property="og:type" content="{esc(page_type)}"><meta property="og:locale" content="ar_AR">'
        '<meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">'
        f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}">'
        f'<meta property="og:url" content="{esc(canonical)}">{modified_meta}'
        '<meta name="twitter:card" content="summary"><meta name="twitter:site" content="@pterminology">'
        f'<meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}">'
        f'<link rel="stylesheet" href="{BASE_PATH}assets/care-guides-v234.css"><script type="application/ld+json">{json_script(schema)}</script></head>'
    )

def list_section(key: str, items: list[str], index: int) -> str:
    section_id = f"section-{index}"
    danger = key in {"warning_signs", "when_to_seek_help"}
    css = "care234__section care234__section--danger" if danger else "care234__section"
    rows = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f'<section id="{section_id}" class="{css}"><h2>{esc(SECTION_LABELS[key])}</h2><ul>{rows}</ul></section>'

def howto_steps(guide: dict[str, Any]) -> list[dict[str, Any]]:
    keys = ("first_minutes", "do", "communication_plan", "conversation_plan", "plan", "family_plan", "home_plan", "school_plan")
    result: list[dict[str, Any]] = []
    for key in keys:
        for item in guide.get(key, []):
            result.append({"@type": "HowToStep", "position": len(result) + 1, "name": compact(item)[:110], "text": item})
    return result[:24]

def guide_schema(guide: dict[str, Any], canonical: str, category_label: str) -> dict[str, Any]:
    modified = guide.get("reviewed_at") if valid_date(guide.get("reviewed_at")) else TODAY
    citations = [source["url"] for source in guide["sources"]]
    faq = [
        {"@type": "Question", "name": "هل هذا الدليل يشخّص الحالة؟", "acceptedAnswer": {"@type": "Answer", "text": "لا. الدليل للتثقيف والدعم العام ولا يقدّم تشخيصًا أو علاجًا فرديًا."}},
        {"@type": "Question", "name": "متى تصبح الاستجابة عاجلة؟", "acceptedAnswer": {"@type": "Answer", "text": guide.get("emergency_note", "عند وجود خطر مباشر أو عجز عن البقاء بأمان استخدم خدمات الطوارئ المحلية.")}},
        {"@type": "Question", "name": "كيف تستخدم الأسرة هذا الدليل؟", "acceptedAnswer": {"@type": "Answer", "text": "اختَر خطوة صغيرة تناسب الموقف، واتفق مع الشخص على حدود الدعم، واطلب تقييمًا مهنيًا عندما تستمر الصعوبة أو تتدهور الوظيفة."}},
    ]
    article = {
        "@type": "Article",
        "@id": canonical + "#article",
        "url": canonical,
        "headline": guide["title"],
        "description": guide["summary"],
        "inLanguage": "ar",
        "dateModified": modified,
        "isPartOf": {"@id": BASE + "care-guides/#collection"},
        "author": {"@type": "Organization", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة", "url": BASE},
        "publisher": {"@type": "Organization", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة", "url": BASE},
        "about": {"@type": "Thing", "name": category_label},
        "audience": [{"@type": "Audience", "audienceType": item} for item in guide.get("audience", [])],
        "citation": citations,
        "keywords": guide.get("search_intent", []),
    }
    medical_page = {
        "@type": "MedicalWebPage",
        "@id": canonical + "#webpage",
        "url": canonical,
        "name": guide["title"],
        "description": guide["summary"],
        "inLanguage": "ar",
        "dateModified": modified,
        "mainEntity": {"@id": canonical + "#article"},
        "isPartOf": {"@id": BASE + "care-guides/#collection"},
    }
    graph: list[dict[str, Any]] = [
        medical_page,
        article,
        {
            "@type": "BreadcrumbList",
            "@id": canonical + "#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "أدلة الرعاية والدعم", "item": BASE + "care-guides/"},
                {"@type": "ListItem", "position": 3, "name": guide["title"], "item": canonical},
            ],
        },
        {"@type": "FAQPage", "@id": canonical + "#faq", "mainEntity": faq},
    ]
    steps = howto_steps(guide)
    if steps:
        graph.append({
            "@type": "HowTo", "@id": canonical + "#howto", "name": guide["title"],
            "description": guide["summary"], "inLanguage": "ar", "url": canonical, "step": steps,
        })
    return {"@context": "https://schema.org", "@graph": graph}

def index_schema(expansion: dict[str, Any], guides: list[dict[str, Any]]) -> dict[str, Any]:
    canonical = BASE + "care-guides/"
    items = [
        {"@type": "ListItem", "position": idx, "url": canonical + g["slug"] + "/", "name": g["title"]}
        for idx, g in enumerate(guides, 1)
    ]
    faq = [
        {"@type": "Question", "name": "هل أدلة الرعاية تشخّص الحالات؟", "acceptedAnswer": {"@type": "Answer", "text": "لا. الأدلة للتثقيف والدعم العام، ولا تستبدل التقييم المهني."}},
        {"@type": "Question", "name": "كيف أختار الدليل المناسب؟", "acceptedAnswer": {"@type": "Answer", "text": "ابدأ بالموقف الحالي أو الفئة المستفيدة، ثم استخدم البحث والتصنيفات واقرأ إشارات الخطر أولًا."}},
        {"@type": "Question", "name": "ماذا أفعل عند وجود خطر مباشر؟", "acceptedAnswer": {"@type": "Answer", "text": "استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة، ولا تعتمد على صفحة ويب لإدارة الخطر."}},
    ]
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage", "@id": canonical + "#collection", "url": canonical,
                "name": expansion["title"], "description": "مكتبة عربية منظمة لأدلة الرعاية والدعم النفسي العملي.",
                "inLanguage": "ar", "dateModified": expansion["reviewed_at"],
                "isPartOf": {"@type": "WebSite", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة", "url": BASE},
                "hasPart": [{"@id": canonical + g["slug"] + "/#article"} for g in guides],
            },
            {"@type": "ItemList", "@id": canonical + "#guides", "numberOfItems": len(items), "itemListElement": items},
            {
                "@type": "BreadcrumbList", "@id": canonical + "#breadcrumb",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "أدلة الرعاية والدعم", "item": canonical},
                ],
            },
            {"@type": "FAQPage", "@id": canonical + "#faq", "mainEntity": faq},
        ],
    }
