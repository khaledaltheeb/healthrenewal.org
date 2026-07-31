from __future__ import annotations

import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
RELEASE_DATE = "2026-07-25"
ENHANCEMENT_VERSION = 234
SITE = Path("_site").resolve()
CATEGORY_RULES = (
    (
        "crisis",
        "الأزمات والسلامة",
        ("ضيق", "ذهان", "خطر", "أزمة", "انتحار", "إيذاء", "psychosis", "distress", "crisis"),
    ),
    (
        "children",
        "الأطفال والمراهقون",
        ("طفل", "مراهق", "مدرس", "school", "child", "teen", "adolescent"),
    ),
    (
        "neurodevelopment",
        "الاختلافات النمائية والتنظيم",
        ("توحد", "فرط الحركة", "انتباه", "autism", "adhd", "sensory", "نمائي"),
    ),
    (
        "services",
        "اختيار الخدمات والمختصين",
        ("مختص", "معالج", "مركز", "خدمة", "professional", "provider", "therapy"),
    ),
    (
        "caregivers",
        "الأسرة ومقدمو الرعاية",
        ("أسرة", "عائلة", "مقدم الرعاية", "family", "caregiver", "carer"),
    ),
)

HUB_FAQS = (
    (
        "هل تعطي هذه الأدلة تشخيصًا؟",
        "لا. الأدلة تقدم تثقيفًا وخطوات دعم عامة، ولا تحل محل التقييم الفردي لدى مختص مؤهل.",
    ),
    (
        "كيف أختار الدليل المناسب؟",
        "ابدأ بالموقف أو الفئة التي تصف احتياجك، ثم اقرأ حدود الدليل وإشارات طلب المساعدة قبل تطبيق أي خطوة.",
    ),
    (
        "متى أتوقف عن استخدام الدليل وأطلب مساعدة عاجلة؟",
        "عند وجود خطر مباشر، أو تهديد للنفس أو الآخرين، أو فقدان شديد للاتصال بالواقع، أو تدهور حاد في الوظيفة؛ استخدم خدمات الطوارئ المحلية فورًا.",
    ),
    (
        "هل يمكن مشاركة الدليل مع المدرسة أو مقدم الخدمة؟",
        "نعم بعد مراعاة موافقة الشخص وخصوصيته، واستخدام الدليل كنقطة تنظيم للأسئلة والخطوات لا كتشخيص أو خطة علاج مستقلة.",
    ),
)

def esc(value: object) -> str:
    return html.escape(str(value), quote=True)

def plain(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()

def meta_content(text: str, name: str) -> str:
    pattern = rf'<meta\s+(?:name|property)="{re.escape(name)}"\s+content="([^"]*)"'
    match = re.search(pattern, text, flags=re.I)
    return html.unescape(match.group(1)).strip() if match else ""

def title_from_page(text: str) -> str:
    match = re.search(r"<h1(?:\s[^>]*)?>(.*?)</h1>", text, flags=re.I | re.S)
    if match:
        return plain(match.group(1))
    match = re.search(r"<title>(.*?)</title>", text, flags=re.I | re.S)
    return plain(match.group(1)).split("|")[0].strip() if match else "دليل عملي"

def category_for(title: str, slug: str, description: str) -> tuple[str, str]:
    haystack = f"{title} {slug} {description}".lower()
    for key, label, words in CATEGORY_RULES:
        if any(word.lower() in haystack for word in words):
            return key, label
    return "daily", "الدعم النفسي اليومي"

def keywords_for(title: str, search_intent: list[str] | None = None) -> str:
    values = [
        title,
        "أدلة التعامل النفسي",
        "دعم الصحة النفسية",
        "إرشادات الأسرة",
        "مقدمو الرعاية",
        "التعامل مع الاضطرابات النفسية",
        "الدعم النفسي الأولي",
        "متى أطلب مساعدة نفسية",
        "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
        "مصطلحات علم النفس",
    ]
    values.extend(search_intent or [])
    return ", ".join(dict.fromkeys(item.strip() for item in values if item and item.strip()))[:700]

def faq_items(title: str) -> list[tuple[str, str]]:
    return [
        (
            f"هل يكفي دليل «{title}» لتحديد التشخيص؟",
            f"لا. دليل «{title}» للتثقيف وتنظيم الدعم والملاحظة، ولا يحدد تشخيصًا ولا يستبدل تقييمًا فرديًا لدى مختص مؤهل.",
        ),
        (
            f"كيف أبدأ بتطبيق دليل «{title}» دون ضغط؟",
            f"اختر خطوة واحدة آمنة من دليل «{title}»، واتفق عليها مع الشخص قدر الإمكان، ثم راقب أثرها ووثّق ما يساعد وما يزيد الضيق.",
        ),
        (
            f"متى أطلب مساعدة مهنية أثناء استخدام دليل «{title}»؟",
            f"اطلب تقييمًا مهنيًا عندما تستمر الصعوبة أو تتزايد أو تؤثر بوضوح في النوم أو الدراسة أو العمل أو العلاقات أو العناية بالنفس. عند الخطر المباشر استخدم خدمات الطوارئ المحلية.",
        ),
        (
            f"كيف أحافظ على خصوصية الشخص في موضوع «{title}»؟",
            f"شارك أقل قدر لازم من المعلومات، واحصل على الموافقة متى كان ذلك ممكنًا، ولا تتجاوز الخصوصية إلا لحماية السلامة عند وجود خطر جدي ومباشر.",
        ),
    ]

def faq_schema(title: str, items: list[tuple[str, str]], canonical: str) -> dict:
    return {
        "@type": "FAQPage",
        "@id": canonical + "#faq",
        "name": f"أسئلة شائعة حول {title}",
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in items
        ],
    }

def head(title: str, description: str, canonical: str, schema: str, keywords: str, page_type: str = "article") -> str:
    safe_title = esc(title)
    safe_desc = esc(description)
    safe_canonical = esc(canonical)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{safe_title} | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title><meta name="description" content="{safe_desc}"><meta name="keywords" content="{esc(keywords)}"><meta name="author" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta name="publisher" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="bingbot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="referrer" content="strict-origin-when-cross-origin"><meta name="format-detection" content="telephone=no"><meta name="theme-color" content="#075f5b"><meta name="color-scheme" content="light"><link rel="canonical" href="{safe_canonical}"><link rel="alternate" hreflang="ar" href="{safe_canonical}"><link rel="alternate" hreflang="x-default" href="{safe_canonical}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><link rel="stylesheet" href="{BASE_PATH}assets/css/theme-v10.css"><link rel="stylesheet" href="{BASE_PATH}assets/css/marshmallow-v12.css"><link rel="stylesheet" href="{BASE_PATH}assets/css/care-guides-v234.css"><meta property="og:type" content="{esc(page_type)}"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة"><meta property="og:title" content="{safe_title}"><meta property="og:description" content="{safe_desc}"><meta property="og:url" content="{safe_canonical}"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{safe_title}"><meta name="twitter:description" content="{safe_desc}"><meta property="article:section" content="أدلة التعامل والرعاية"><meta property="article:modified_time" content="{RELEASE_DATE}"><script type="application/ld+json">{schema}</script></head>'''

def support_sections(title: str, related: list[tuple[str, str]] | None = None) -> str:
    items = faq_items(title)
    faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in items)
    related_html = ""
    if related:
        links = "".join(f'<li><a href="{esc(url)}">{esc(name)}</a></li>' for name, url in related)
        related_html = f'<section class="care-panel care-related" aria-labelledby="care-related-title"><h2 id="care-related-title">أدلة مرتبطة قد تساعدك</h2><ul>{links}</ul></section>'
    return f'''
<section class="care-panel" aria-labelledby="care-use-title"><h2 id="care-use-title">طريقة استخدام الدليل في موقف واقعي</h2><ol class="care-steps"><li>حدّد الموقف المحدد المرتبط بـ«{esc(title)}» بدل محاولة حل كل شيء دفعة واحدة.</li><li>ابدأ بالاستماع والملاحظة، ثم اختر خطوة آمنة واحدة يقبلها الشخص قدر الإمكان.</li><li>اتفق على علامة واضحة لمعرفة إن كانت الخطوة مفيدة أو تزيد الضيق.</li><li>دوّن ما حدث قبل الموقف وأثناءه وبعده دون أوصاف جارحة أو استنتاجات تشخيصية.</li><li>راجع الخطة مع مختص عندما تستمر الصعوبة أو تتعطل الحياة اليومية.</li></ol></section>
<section class="care-panel" aria-labelledby="care-follow-title"><h2 id="care-follow-title">سجل متابعة مختصر قابل للطباعة</h2><p>يساعد هذا السجل على تنظيم ملاحظات «{esc(title)}» دون تحويلها إلى حكم على الشخص أو تشخيص.</p><div class="care-table-wrap"><table class="care-table"><thead><tr><th>التاريخ والموقف</th><th>ما الذي سبق الموقف؟</th><th>الخطوة الداعمة</th><th>النتيجة</th><th>ما الذي نعدله؟</th></tr></thead><tbody><tr><td>________</td><td>________</td><td>________</td><td>________</td><td>________</td></tr><tr><td>________</td><td>________</td><td>________</td><td>________</td><td>________</td></tr></tbody></table></div></section>
<section class="care-panel" aria-labelledby="care-professional-title"><h2 id="care-professional-title">أسئلة مفيدة عند مقابلة المختص</h2><div class="care-checklist"><div class="care-check">ما التفسير المهني المحتمل، وما المعلومات الناقصة قبل أي استنتاج؟</div><div class="care-check">ما الأهداف الواقعية ذات الأولوية في موضوع «{esc(title)}»؟</div><div class="care-check">ما الخيارات المبنية على الدليل، وما فوائد كل خيار ومخاطره؟</div><div class="care-check">كيف نقيس التحسن الوظيفي لا مجرد تغير الأعراض؟</div><div class="care-check">ما خطة التصرف عند التدهور أو ظهور خطر؟</div><div class="care-check">متى نراجع الخطة، ومن المسؤول عن كل خطوة؟</div></div></section>
<section class="care-panel care-method" aria-labelledby="care-rights-title"><h2 id="care-rights-title">مبادئ تحمي الكرامة والخصوصية</h2><ul><li>استخدم لغة تصف الموقف ولا تختزل الإنسان في حالة أو سلوك.</li><li>اطلب الموافقة قبل مشاركة المعلومات متى كان ذلك ممكنًا.</li><li>قدم خيارات واضحة بدل الأوامر والتهديد.</li><li>افصل بين دعم السلامة وبين السيطرة على قرارات الشخص.</li><li>راجع الاحتياجات الفردية والثقافية واللغوية وإمكانية الوصول.</li></ul></section>
{related_html}<section class="care-panel care-faq" aria-labelledby="care-faq-title"><h2 id="care-faq-title">أسئلة شائعة</h2>{faq}</section>'''

@dataclass(frozen=True)
class GuideMeta:
    slug: str
    title: str
    description: str
    canonical: str
    category: str
    category_label: str
    search_text: str

def guide_meta_from_page(path: Path) -> GuideMeta:
    text = path.read_text(encoding="utf-8")
    slug = path.parent.name
    title = title_from_page(text)
    description = meta_content(text, "description") or f"دليل عملي حول {title}."
    canonical = meta_content(text, "og:url") or BASE + "care-guides/" + slug + "/"
    category, category_label = category_for(title, slug, description)
    search_text = plain(f"{title} {description} {slug} {category_label}")
    return GuideMeta(slug, title, description, canonical, category, category_label, search_text)

def enhance_extension_page(path: Path, all_meta: list[GuideMeta]) -> None:
    text = path.read_text(encoding="utf-8")
    if 'data-care-guides-v234="1"' in text:
        return
    title = title_from_page(text)
    slug = path.parent.name
    canonical = meta_content(text, "og:url") or BASE + "care-guides/" + slug + "/"
    description = meta_content(text, "description") or f"دليل عملي موثق حول {title}."
    category, category_label = category_for(title, slug, description)
    related = [
        (item.title, BASE_PATH + "care-guides/" + item.slug + "/")
        for item in all_meta
        if item.slug != slug and (item.category == category or len(all_meta) < 4)
    ][:3]

    headings: list[tuple[str, str]] = []
    sequence = 0

    def add_id(match: re.Match[str]) -> str:
        nonlocal sequence
        attrs = match.group(1) or ""
        inner = match.group(2)
        if re.search(r"\bid=", attrs):
            id_match = re.search(r'\bid="([^"]+)"', attrs)
            section_id = id_match.group(1) if id_match else f"extension-section-{sequence + 1}"
        else:
            sequence += 1
            section_id = f"extension-section-{sequence}"
            attrs += f' id="{section_id}"'
        headings.append((section_id, plain(inner)))
        return f"<h2{attrs}>{inner}</h2>"

    text = re.sub(r"<h2([^>]*)>(.*?)</h2>", add_id, text, flags=re.I | re.S)
    additions = [
        f'<meta name="keywords" content="{esc(keywords_for(title))}">',
        '<meta name="author" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">',
        '<meta name="publisher" content="منصة الصحة النفسية وذوي الاحتياجات الخاصة">',
        '<meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">',
        '<meta name="bingbot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">',
        f'<meta property="article:section" content="أدلة التعامل والرعاية"><meta property="article:modified_time" content="{RELEASE_DATE}">',
        f'<link rel="stylesheet" href="{BASE_PATH}assets/css/care-guides-v234.css">',
    ]
    if not re.search(r'<link\s+[^>]*rel=["\']canonical["\']', text, flags=re.I):
        additions.append(f'<link rel="canonical" href="{esc(canonical)}">')
    if 'hreflang="ar"' not in text:
        additions.append(f'<link rel="alternate" hreflang="ar" href="{esc(canonical)}"><link rel="alternate" hreflang="x-default" href="{esc(canonical)}">')
    if not meta_content(text, "description"):
        additions.append(f'<meta name="description" content="{esc(description)}">')
    if not meta_content(text, "robots"):
        additions.append('<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">')
    if not meta_content(text, "og:url"):
        additions.append(f'<meta property="og:url" content="{esc(canonical)}">')
    if not meta_content(text, "og:title"):
        additions.append(f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR">')
    if not meta_content(text, "twitter:card"):
        additions.append(f'<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}">')
    structured = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebPage", "name": title, "description": description, "url": canonical, "inLanguage": "ar", "dateModified": RELEASE_DATE},
                faq_schema(title, faq_items(title), canonical),
            ],
        },
        ensure_ascii=False,
    ).replace("</", r"<\/")
    additions.append(f'<script type="application/ld+json">{structured}</script>')
    text = text.replace("</head>", "".join(additions) + "</head>", 1)
    def enhance_body(match: re.Match[str]) -> str:
        attrs = match.group(1) or ""
        if 'data-care-guides-v234=' not in attrs:
            attrs += ' data-care-guides-v234="1"'
        return f'<body{attrs}><a class="care-skip" href="#main-content">تجاوز إلى المحتوى</a>'

    text = re.sub(r"<body([^>]*)>", enhance_body, text, count=1, flags=re.I)
    if 'id="main-content"' not in text:
        def add_main_id(match: re.Match[str]) -> str:
            attrs = match.group(1) or ""
            if re.search(r"\bid\s*=", attrs, flags=re.I):
                return f'<main{attrs}>'
            return f'<main{attrs} id="main-content">'
        text = re.sub(r"<main([^>]*)>", add_main_id, text, count=1, flags=re.I)
    toc_rows = "".join(f'<li><a href="#{esc(section_id)}">{esc(label)}</a></li>' for section_id, label in headings if label)
    toc = f'<aside class="care-alert" role="note"><strong>قبل البدء</strong> استخدم دليل «{esc(title)}» لتنظيم الدعم والأسئلة، لا للتشخيص أو تغيير العلاج. عند الخطر المباشر استخدم خدمات الطوارئ المحلية.</aside><nav class="care-toc" aria-labelledby="extension-toc-title"><h2 id="extension-toc-title">محتويات الدليل</h2><ol>{toc_rows}<li><a href="#care-use-title">طريقة الاستخدام</a></li><li><a href="#care-faq-title">الأسئلة الشائعة</a></li></ol></nav>'
    if "</header>" in text:
        text = text.replace("</header>", "</header>" + toc, 1)
    else:
        text = re.sub(r"(<h1[^>]*>.*?</h1>)", r"\1" + toc, text, count=1, flags=re.I | re.S)
    text = text.replace("</main>", support_sections(title, related) + "</main>", 1)
    path.write_text(text, encoding="utf-8")

def hub_schema(guides: list[GuideMeta]) -> str:
    canonical = BASE + "care-guides/"
    graph = [
        {
            "@type": "CollectionPage",
            "@id": canonical + "#collection",
            "name": "أدلة التعامل والرعاية النفسية والأسرية",
            "description": "مكتبة عربية منظمة من الأدلة العملية لدعم الأفراد والأسر ومقدمي الرعاية، مع مسارات سلامة ومصادر مؤسسية وحدود واضحة للاستخدام.",
            "url": canonical,
            "inLanguage": "ar",
            "dateModified": RELEASE_DATE,
            "hasPart": [{"@type": "Article", "name": item.title, "url": item.canonical} for item in guides],
        },
        {
            "@type": "ItemList",
            "@id": canonical + "#guides",
            "name": "فهرس أدلة التعامل والرعاية",
            "numberOfItems": len(guides),
            "itemListElement": [
                {"@type": "ListItem", "position": position, "name": item.title, "url": item.canonical}
                for position, item in enumerate(guides, start=1)
            ],
        },
        {
            "@type": "BreadcrumbList",
            "@id": canonical + "#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                {"@type": "ListItem", "position": 2, "name": "أدلة التعامل والرعاية", "item": canonical},
            ],
        },
        faq_schema("أدلة التعامل والرعاية النفسية والأسرية", list(HUB_FAQS), canonical),
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")

def index_page(guides: list[GuideMeta]) -> str:
    canonical = BASE + "care-guides/"
    categories = sorted({(item.category, item.category_label) for item in guides}, key=lambda pair: pair[1])
    cards = "".join(
        f'''<article class="care-card" data-care-card data-category="{esc(item.category)}" data-search="{esc(item.search_text)}"><div class="care-tags"><span class="care-tag">{esc(item.category_label)}</span></div><h2><a href="{BASE_PATH}care-guides/{esc(item.slug)}/">{esc(item.title)}</a></h2><p>{esc(item.description)}</p><a class="care-button care-button--primary" href="{BASE_PATH}care-guides/{esc(item.slug)}/">فتح الدليل الكامل</a></article>'''
        for item in guides
    )
    filters = '<button type="button" data-care-filter="all" aria-pressed="true">كل الأدلة</button>' + "".join(
        f'<button type="button" data-care-filter="{esc(key)}" aria-pressed="false">{esc(label)}</button>'
        for key, label in categories
    )
    faq = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in HUB_FAQS)
    description = "مكتبة عربية مؤسسية لأدلة التعامل والرعاية النفسية والأسرية: خطوات عملية، سلامة، خصوصية، اختيار المختص، ومصادر موثوقة دون تشخيص ذاتي."
    body = f'''<body data-care-guides-v234="1"><a class="care-skip" href="#main-content">تجاوز إلى المحتوى</a><main class="care-v21" id="main-content" data-care-library><header class="care-v21__hero"><nav class="care-v21__nav" aria-label="التنقل داخل المنصة"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a><a href="{BASE_PATH}assessment-lab/">منصة التقييم</a><a href="{BASE_PATH}tips/">النصائح</a></nav><p class="care-v21__eyebrow">مكتبة الرعاية والدعم العملي</p><h1>أدلة التعامل والرعاية النفسية والأسرية</h1><p>مكتبة منظمة تساعد الفرد والأسرة ومقدم الرعاية على فهم الموقف، واختيار خطوة آمنة، والاستعداد للمحادثة مع المختص. المحتوى تثقيفي، خالٍ من الوصم، ولا يقدم تشخيصًا أو علاجًا فرديًا.</p><div class="care-stat-grid"><div class="care-stat"><strong>{len(guides)}</strong><span>دليلًا منشورًا</span></div><div class="care-stat"><strong>{len(categories)}</strong><span>مسارات موضوعية</span></div><div class="care-stat"><strong>100%</strong><span>فهرسة وبيانات منظمة</span></div><div class="care-stat"><strong>واضح</strong><span>حدود الاستخدام والسلامة</span></div></div></header><aside class="care-alert" role="alert"><strong>عند وجود خطر مباشر أو وشيك</strong> لا تعتمد على أي دليل عام. ابقَ مع الشخص إذا كان ذلك آمنًا، وأبعد وسائل الأذى إن أمكن دون تعريض نفسك للخطر، واتصل بخدمات الطوارئ المحلية أو جهة صحية عاجلة.</aside><section class="care-panel" aria-labelledby="start-title"><h2 id="start-title">ابدأ من احتياجك، لا من اسم التشخيص</h2><div class="care-paths"><article class="care-path"><h3>موقف عاجل أو تصعيد</h3><p>ابدأ بإشارات السلامة، وخفّض المثيرات، وحدد متى يلزم التصعيد إلى جهة صحية عاجلة.</p></article><article class="care-path"><h3>دعم شخص أو أسرة</h3><p>اختر دليل التواصل والدعم الذي يحافظ على الكرامة والاستقلال ويمنع الضغط واللوم.</p></article><article class="care-path"><h3>طفل أو مراهق</h3><p>ركز على المدة والأثر في المدرسة والنوم والعلاقات، وتعاون مع البالغين المسؤولين ضمن حدود الخصوصية.</p></article><article class="care-path"><h3>اختيار مختص أو خدمة</h3><p>جهّز أسئلتك عن المؤهلات والمنهج والخصوصية والرسوم وخطة المتابعة قبل اتخاذ القرار.</p></article></div></section><section class="care-panel" aria-labelledby="use-title"><h2 id="use-title">كيف تستخدم الأدلة بطريقة منهجية؟</h2><ol class="care-steps"><li>حدد المشكلة الوظيفية أو الموقف الذي تريد التعامل معه.</li><li>اقرأ قسم ما ينبغي فعله وما ينبغي تجنبه وإشارات طلب المساعدة.</li><li>اختر خطوة واحدة تناسب الشخص والسياق وقدرته الحالية.</li><li>اتفق على موعد قصير للمراجعة بدل الاستمرار في خطة غير مفيدة.</li><li>انقل ملاحظاتك إلى المختص بلغة وصفية دون تشخيص أو مبالغة.</li></ol></section><section class="care-panel" aria-labelledby="library-title"><h2 id="library-title">استكشف مكتبة الأدلة</h2><p>ابحث بكلمة مثل: طفل، اكتئاب، توحد، أسرة، مختص، ضيق، أو اختر مسارًا موضوعيًا.</p><div class="care-search"><label><span class="care-v21__small">ابحث في العناوين والملخصات</span><input type="search" data-care-search autocomplete="off" placeholder="اكتب احتياجك أو الموقف" aria-describedby="care-results-status"></label><a class="care-button" href="#care-methodology">كيف نراجع المحتوى؟</a></div><div class="care-filter" role="group" aria-label="تصفية الأدلة حسب المسار">{filters}</div><p id="care-results-status" data-care-status aria-live="polite"></p><noscript><p class="care-noscript">البحث التفاعلي يحتاج JavaScript، وجميع الأدلة ظاهرة أدناه ويمكن فتحها مباشرة.</p></noscript><div class="care-grid">{cards}</div><p class="care-empty" data-care-empty hidden>لا توجد نتيجة مطابقة. جرّب كلمة أوسع أو اعرض كل الأدلة.</p></section><section class="care-panel" aria-labelledby="principles-title"><h2 id="principles-title">مبادئ الرعاية التي تعتمدها المكتبة</h2><div class="care-checklist"><div class="care-check"><strong>الكرامة أولًا:</strong> وصف الاحتياج دون اختزال الإنسان في حالة.</div><div class="care-check"><strong>الموافقة والمشاركة:</strong> إشراك الشخص في القرارات بقدر استطاعته.</div><div class="care-check"><strong>أقل تدخل لازم:</strong> دعم الاستقلال بدل السيطرة أو التبعية.</div><div class="care-check"><strong>سلامة قابلة للتصعيد:</strong> فصل الدعم العام عن الطوارئ والرعاية المتخصصة.</div><div class="care-check"><strong>إتاحة وتكييف:</strong> مراعاة اللغة والتواصل والحساسية والبيئة.</div><div class="care-check"><strong>مراجعة مستمرة:</strong> تعديل الخطة وفق الأثر الوظيفي والملاحظات.</div></div></section><section class="care-panel care-method" id="care-methodology" aria-labelledby="method-title"><h2 id="method-title">المنهجية التحريرية وضبط الجودة</h2><p>تُبنى الأدلة على مصادر مؤسسية وإرشادات مهنية متاحة، ثم تُراجع بنيويًا للتأكد من وجود هدف واضح، وخطوات قابلة للتطبيق، ومحاذير، وإشارات طلب المساعدة، وحدود تمنع التشخيص الذاتي أو استبدال الرعاية الفردية.</p><ul><li>فصل المحتوى التثقيفي عن التشخيص والعلاج.</li><li>ربط كل دليل بمصادر أصلية يمكن للقارئ مراجعتها.</li><li>استخدام لغة عربية مباشرة تحترم الشخص وتبتعد عن الوصم.</li><li>إظهار حالة المراجعة وتاريخ التحديث وعدم ادعاء مراجعة اختصاصية غير موثقة.</li><li>فحص العناوين والوصف والروابط والبيانات المنظمة وخريطة الموقع.</li></ul><p class="care-v21__small">آخر تحديث بنيوي للمكتبة: {RELEASE_DATE}. المراجعة الاختصاصية الخارجية المستقلة مطلوبة قبل اعتبار أي دليل بروتوكولًا مهنيًا.</p></section><section class="care-panel" aria-labelledby="limits-title"><h2 id="limits-title">ما الذي لا تفعله هذه الأدلة؟</h2><ul><li>لا تثبت وجود اضطراب ولا تنفيه.</li><li>لا توصي ببدء دواء أو إيقافه أو تعديل جرعته.</li><li>لا تستبدل خطة الأمان أو التقييم الطبي أو النفسي الفردي.</li><li>لا تمنح الأسرة أو مقدم الرعاية حق تجاوز خصوصية الشخص دون سبب سلامة جدي.</li><li>لا تنطبق آليًا على كل الأعمار والثقافات والظروف الصحية.</li></ul></section><section class="care-panel care-faq" aria-labelledby="hub-faq-title"><h2 id="hub-faq-title">أسئلة شائعة عن المكتبة</h2>{faq}</section><section class="care-panel" aria-labelledby="sources-policy-title"><h2 id="sources-policy-title">سياسة المصادر والتحديث</h2><p>تفضّل المكتبة المصادر الحكومية والدولية والإرشادات المهنية والجامعية الأصلية. يُحفظ رابط المصدر وسنة النشر أو المراجعة داخل كل دليل، ويجب تحديث الدليل عندما تتغير الإرشادات أو تظهر مشكلة سلامة أو دقة أو إتاحة.</p><p><a class="care-button care-button--primary" href="{BASE_PATH}trust/">مراجعة صفحة الثقة والحوكمة</a></p></section></main><script src="{BASE_PATH}assets/js/care-guides-v234.js" defer></script></body></html>'''
    return head(
        "أدلة التعامل والرعاية النفسية والأسرية",
        description,
        canonical,
        hub_schema(guides),
        keywords_for("أدلة التعامل والرعاية النفسية والأسرية", ["كيف أتعامل مع شخص مكتئب", "دعم الأسرة", "إرشادات مقدم الرعاية", "اختيار المعالج النفسي"]),
        page_type="website",
    ) + body

def copy_assets() -> None:
    pairs = (
        (ROOT / "assets/css/care-guides-v234.css", SITE / "assets/css/care-guides-v234.css"),
        (ROOT / "assets/js/care-guides-v234.js", SITE / "assets/js/care-guides-v234.js"),
    )
    for source, target in pairs:
        if not source.is_file():
            raise SystemExit(f"Missing care-guide asset source: {source.relative_to(ROOT)}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def refresh_care_sitemap() -> int:
    path = SITE / "sitemap-care-guides.xml"
    if not path.is_file():
        raise SystemExit("Missing sitemap-care-guides.xml")
    tree = ET.parse(path)
    root = tree.getroot()
    urls = root.findall("{*}url")
    for node in urls:
        loc = node.find("{*}loc")
        if loc is None or not (loc.text or "").strip():
            raise SystemExit("Care-guide sitemap contains an empty URL")
        lastmod = node.find("{*}lastmod")
        if lastmod is None:
            lastmod = ET.SubElement(node, "lastmod")
        lastmod.text = RELEASE_DATE
        changefreq = node.find("{*}changefreq")
        if changefreq is None:
            changefreq = ET.SubElement(node, "changefreq")
        changefreq.text = "monthly"
        priority = node.find("{*}priority")
        if priority is None:
            priority = ET.SubElement(node, "priority")
        priority.text = "0.92" if (loc.text or "").rstrip("/").endswith("care-guides") else "0.82"
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return len(urls)


def write_robots() -> None:
    text = "\n".join(
        (
            "User-agent: *",
            "Allow: /",
            "Disallow: /api/",
            f"Sitemap: {BASE}sitemap.xml",
            f"Sitemap: {BASE}sitemap-care-guides.xml",
            "",
        )
    )
    (SITE / "robots.txt").write_text(text, encoding="utf-8")


def enhance(site: Path | str) -> dict[str, object]:
    global SITE
    SITE = Path(site).resolve()
    output = SITE / "care-guides"
    legacy_path = SITE / "api/care-guides-v21.json"
    if not output.is_dir() or not legacy_path.is_file():
        raise SystemExit("Care-guide core publication must finish before v234 enhancement")
    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    if legacy.get("needs_specialist_review_published") is not False:
        raise SystemExit("Specialist-review safety gate is not confirmed")

    guide_paths = sorted(output.glob("*/index.html"))
    if not guide_paths:
        raise SystemExit("No published care-guide pages found")
    initial_meta = [guide_meta_from_page(path) for path in guide_paths]
    for path in guide_paths:
        enhance_extension_page(path, initial_meta)
    all_meta = [guide_meta_from_page(path) for path in guide_paths]
    (output / "index.html").write_text(index_page(all_meta), encoding="utf-8")
    copy_assets()
    write_robots()
    sitemap_urls = refresh_care_sitemap()

    hub_text = (output / "index.html").read_text(encoding="utf-8")
    guide_texts = [path.read_text(encoding="utf-8") for path in guide_paths]
    page_texts = [hub_text, *guide_texts]
    page_count = len(page_texts)
    duplicate_ids: dict[str, list[str]] = {}
    for path, text in [(output / "index.html", hub_text), *zip(guide_paths, guide_texts)]:
        ids = re.findall(r'\bid="([^"]+)"', text)
        repeated = sorted({item for item in ids if ids.count(item) > 1})
        if repeated:
            duplicate_ids[str(path.relative_to(SITE))] = repeated

    report = {
        "version": ENHANCEMENT_VERSION,
        "status": "passed",
        "release_date": RELEASE_DATE,
        "published_guides": len(guide_paths),
        "published_pages": page_count,
        "sitemap_urls": sitemap_urls,
        "hub_sections": 8,
        "categories": len({item.category for item in all_meta}),
        "guide_pages_with_toc": sum("care-toc" in text for text in guide_texts),
        "pages_with_keywords": sum('name="keywords"' in text for text in page_texts),
        "pages_with_faq_schema": sum("FAQPage" in text for text in page_texts),
        "pages_with_canonical": sum('rel="canonical"' in text for text in page_texts),
        "pages_with_single_h1": sum(len(re.findall(r"<h1(?:\s|>)", text, flags=re.I)) == 1 for text in page_texts),
        "search_asset": (SITE / "assets/js/care-guides-v234.js").is_file(),
        "style_asset": (SITE / "assets/css/care-guides-v234.css").is_file(),
        "robots_sitemaps": (SITE / "robots.txt").read_text(encoding="utf-8").count("Sitemap:"),
        "blocked_term_occurrences": sum(text.count("معاقين") for text in page_texts),
        "duplicate_ids": duplicate_ids,
        "specialist_review_gate_preserved": legacy.get("needs_specialist_review_published") is False,
        "external_specialist_review_completed": False,
    }
    required_equal = (
        "pages_with_keywords",
        "pages_with_faq_schema",
        "pages_with_canonical",
        "pages_with_single_h1",
    )
    if sitemap_urls != page_count or any(report[key] != page_count for key in required_equal):
        raise SystemExit(f"Care-guide publication parity or SEO contract failed: {report}")
    if report["guide_pages_with_toc"] != len(guide_paths) or duplicate_ids:
        raise SystemExit(f"Care-guide accessibility/navigation contract failed: {report}")
    if report["blocked_term_occurrences"]:
        raise SystemExit(f"Non-inclusive terminology found in care guides: {report}")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-v234.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report
