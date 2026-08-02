#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
COURSE_DATA = ROOT / "content" / "v73" / "special-needs-executable-instructions-ar.json"
PRODUCTION_MANIFEST = ROOT / "content" / "v221" / "special-needs-guides-production-manifest-ar.json"
UPDATED = "2026-07-25"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
FOUNDING_NAME = "مصطلحات علم النفس"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    course = json.loads(COURSE_DATA.read_text(encoding="utf-8"))
    manifest = json.loads(PRODUCTION_MANIFEST.read_text(encoding="utf-8"))
    paths = manifest.get("source_files", [])
    if manifest.get("version") != 221 or manifest.get("status") != "production-integrated":
        raise SystemExit("Special-needs production manifest is not integrated")
    if len(paths) != 25 or len(paths) != len(set(paths)):
        raise SystemExit("Special-needs hub requires twenty-five unique production guide sources")
    missing = [path for path in paths if not (ROOT / path).is_file()]
    if missing:
        raise SystemExit(f"Missing special-needs source files: {missing}")
    if course.get("review_status") != "needs-external-review":
        raise SystemExit("The legacy course must retain its honest review status")
    return course, manifest


def load_guide_slugs(manifest: dict[str, Any]) -> set[str]:
    slugs: set[str] = set()
    for relative in manifest["source_files"]:
        data = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        slug = data.get("slug")
        if not slug or slug in slugs:
            raise SystemExit(f"Invalid or duplicate guide slug in {relative}")
        slugs.add(slug)
    return slugs


def source_cards() -> str:
    sources = [
        (
            "منظمة الصحة العالمية",
            "الإنصاف الصحي وإزالة الحواجز داخل الأنظمة الصحية",
            "https://www.who.int/initiatives/disability-health-equity-initiative/overview",
        ),
        (
            "منظمة الصحة العالمية",
            "دليل عمل لإدماج احتياجات الأشخاص في الحوكمة والتخطيط والمتابعة الصحية",
            "https://www.who.int/publications/i/item/9789240101517",
        ),
        (
            "الأمم المتحدة",
            "نص الاتفاقية الدولية ومواد الإتاحة والتعليم والمشاركة والوصول إلى المعلومات",
            "https://www.un.org/esa/socdev/enable/rights/convtexte.htm",
        ),
        (
            "اليونسكو",
            "الإدماج في التعليم وإزالة الحواجز من المناهج والبيئة وطرائق التدريس",
            "https://www.unesco.org/en/inclusion-education",
        ),
        (
            "اليونيسف",
            "التعليم الدامج ودعم مشاركة الأطفال في المدرسة والمجتمع",
            "https://www.unicef.org/education/inclusive-education",
        ),
        (
            "مبادرة إتاحة الويب W3C",
            "مبادئ المحتوى القابل للإدراك والتشغيل والفهم والمتوافق مع التقنيات المساندة",
            "https://www.w3.org/WAI/fundamentals/accessibility-principles/",
        ),
        (
            "الجمعية الأمريكية للنطق واللغة والسمع",
            "مدخل مهني للتواصل المعزز والبديل ووسائل التواصل المتعددة",
            "https://www.asha.org/public/speech/disorders/aac/",
        ),
    ]
    return "".join(
        f'<li><a href="{e(url)}" rel="noopener noreferrer">{e(org)} — {e(topic)}</a></li>'
        for org, topic, url in sources
    )


def path_cards(slugs: set[str]) -> tuple[str, list[dict[str, Any]]]:
    paths = [
        (
            "التواصل والوصول إلى المعلومات",
            "ابدأ هنا عندما تكون الأولوية لفهم الرسائل والتعبير عن الاحتياجات واختيار وسيلة تواصل ثابتة تعمل في المنزل والمدرسة والمجتمع.",
            "aac-daily-communication-access",
            "فتح دليل التواصل المعزز والبديل",
        ),
        (
            "التعلّم والتربية الدامجة",
            "خطط عملية لتعديل التعليمات والواجبات والمواد والبيئة الصفية، مع مؤشرات قابلة للملاحظة بدل الأحكام العامة.",
            "inclusive-classroom-adjustments-plan",
            "فتح خطة التكييفات الصفية",
        ),
        (
            "المهارات اليومية والاستقلال",
            "بناء المهارة خطوة بخطوة وتحديد مستوى المساعدة ثم خفضها تدريجيًا، مع تعميم المهارة في أكثر من مكان وشخص.",
            "adaptive-skills-stepwise-teaching",
            "فتح دليل تعليم المهارات اليومية",
        ),
        (
            "التنظيم الحسي والانتقالات",
            "فهم العلاقة بين البيئة والمهمة والاستجابة، وتقليل المفاجآت، وتجربة تعديل واحد واضح قبل إضافة تعديلات متعددة.",
            "sensory-regulation-daily-environment-plan",
            "فتح خطة التنظيم الحسي",
        ),
        (
            "الأسرة ومقدم الرعاية",
            "تنظيم المسؤوليات، حماية طاقة مقدم الرعاية، دعم الإخوة، وتحويل التعاون مع المدرسة إلى خطة مشتركة قابلة للمتابعة.",
            "caregiver-wellbeing-sustainable-support-plan",
            "فتح خطة استدامة دعم مقدم الرعاية",
        ),
        (
            "الحماية والحقوق والمشاركة",
            "خطط للسلامة والخصوصية والاستجابة للتنمر أو الاستغلال، مع توثيق الوقائع والإحالة إلى الجهات المحلية المختصة عند الحاجة.",
            "safeguarding-bullying-abuse-response-plan",
            "فتح دليل الحماية والاستجابة",
        ),
        (
            "السمع والبصر والحركة",
            "تحديد الحاجز الوظيفي داخل المهمة والبيئة، ثم اختيار دعم يرفع المشاركة بدل الاكتفاء بوصف الحالة أو الأداة.",
            "vision-access-orientation-learning",
            "فتح دليل الوصول البصري والحركة",
        ),
        (
            "الانتقال إلى الرشد والعمل",
            "بدء التخطيط مبكرًا للمهارات والاختيارات والتجارب الواقعية والعمل والمشاركة المجتمعية، مع صوت مباشر للشخص في القرارات.",
            "transition-adulthood-employment-independence",
            "فتح دليل الانتقال والاستقلال",
        ),
    ]
    missing = [slug for _, _, slug, _ in paths if slug not in slugs]
    if missing:
        raise SystemExit(f"Hub pathways reference missing guides: {missing}")
    cards = "".join(
        f'''<article class="path-card"><h3>{e(title)}</h3><p>{e(description)}</p>
        <a href="{BASE_PATH}special-needs/{e(slug)}/">{e(label)}</a></article>'''
        for title, description, slug, label in paths
    )
    item_list = [
        {
            "@type": "ListItem",
            "position": index,
            "name": title,
            "url": f"{BASE}/special-needs/{slug}/",
        }
        for index, (title, _, slug, _) in enumerate(paths, 1)
    ]
    return cards, item_list


def faq_data() -> list[tuple[str, str]]:
    return [
        (
            "من أين أبدأ إذا كانت الاحتياجات متعددة؟",
            "ابدأ بالمشكلة الأكثر تأثيرًا في الأمان أو التواصل أو المشاركة اليومية، وحدد موقفًا واحدًا يمكن ملاحظته. جرّب دعمًا واحدًا لمدة مناسبة، وسجل ما تغيّر قبل الانتقال إلى خطة أوسع.",
        ),
        (
            "هل تكفي صفحة واحدة للحكم على الحالة أو اختيار الخدمة؟",
            "لا. صفحات المركز للتثقيف وتنظيم الأسئلة والخطوات، وليست أداة تشخيص أو قرار أهلية. القرار المهني يحتاج تاريخًا وظيفيًا وتقييمًا مناسبًا للسياق ومشاركة الشخص والأسرة والجهات ذات الصلة.",
        ),
        (
            "كيف أعرف أن التعديل مفيد؟",
            "حدد مؤشرًا قبل التطبيق مثل زمن البدء أو عدد التذكيرات أو القدرة على إكمال خطوة أو طلب استراحة. قارن النتيجة في أكثر من موقف، واسأل الشخص عن الراحة والاختيار، ولا تعتمد على الانطباع وحده.",
        ),
        (
            "هل الهدف هو جعل الشخص يتصرف مثل الآخرين؟",
            "الهدف هو زيادة الأمان والفهم والاختيار والاستقلال والمشاركة، لا فرض مظهر موحد للسلوك. بعض الفروق لا تحتاج إلى إلغاء، بينما تحتاج الحواجز المؤذية أو المانعة للمشاركة إلى تعديل.",
        ),
        (
            "متى نحتاج إلى تقييم متخصص؟",
            "عندما تكون الصعوبة مستمرة أو متزايدة أو تؤثر بوضوح في التعلم أو التواصل أو الحركة أو النوم أو الأمان أو المشاركة، أو عندما لا تنجح التعديلات البسيطة، يلزم التواصل مع مختص مؤهل وخدمة محلية مناسبة.",
        ),
        (
            "كيف أختار مركزًا أو مقدم خدمة؟",
            "اطلب أهدافًا وظيفية واضحة، طريقة قياس التقدم، سياسة حماية وخصوصية، مشاركة الأسرة والشخص، مؤهلات موثقة، وآلية للشكاوى. تجنب الوعود المطلقة والبرامج التي ترفض شرح أساليبها أو نتائجها.",
        ),
        (
            "كيف نحافظ على الخصوصية عند التعاون مع المدرسة أو المركز؟",
            "شارك الحد الأدنى اللازم من المعلومات، وحدد من يحتاج إليها ولماذا، واستخدم وصفًا وظيفيًا بدل الأوصاف الجارحة، واحفظ السجلات الحساسة بطريقة آمنة، واطلب موافقة الشخص متى كان ذلك ممكنًا.",
        ),
        (
            "ماذا نفعل في موقف خطر أو إساءة محتملة؟",
            "أعط الأولوية للأمان الفوري، ولا تحقق بطريقة تضغط على الشخص أو تلقنه الإجابة. وثق الوقائع كما قيلت، واطلب دعم الطوارئ أو الحماية أو الخدمات المختصة في بلدك وفق مستوى الخطر.",
        ),
    ]


def faq_html(items: list[tuple[str, str]]) -> str:
    return "".join(
        f'<details><summary>{e(question)}</summary><p>{e(answer)}</p></details>'
        for question, answer in items
    )


def structured_data(item_list: list[dict[str, Any]], faqs: list[tuple[str, str]], guide_count: int) -> str:
    canonical = f"{BASE}/special-needs/"
    graph: list[dict[str, Any]] = [
        {
            "@type": "Organization",
            "@id": f"{BASE}/#organization",
            "name": BRAND,
            "alternateName": [FOUNDING_NAME, "Psychology Terminology"],
            "url": f"{BASE}/",
            "logo": {"@type": "ImageObject", "url": f"{BASE}/assets/brand/logo-mark.svg"},
        },
        {
            "@type": "WebSite",
            "@id": f"{BASE}/#website",
            "name": BRAND,
            "url": f"{BASE}/",
            "inLanguage": "ar",
            "publisher": {"@id": f"{BASE}/#organization"},
        },
        {
            "@type": "CollectionPage",
            "@id": f"{canonical}#page",
            "name": "مركز ذوي الاحتياجات الخاصة والتربية الدامجة",
            "description": "مركز عربي مؤسسي يضم أدلة عملية للتواصل والتعليم الدامج والمهارات اليومية والأسرة والحماية والوصول والاستقلال.",
            "url": canonical,
            "inLanguage": "ar",
            "dateModified": UPDATED,
            "isPartOf": {"@id": f"{BASE}/#website"},
            "publisher": {"@id": f"{BASE}/#organization"},
            "mainEntity": {"@id": f"{canonical}#pathways"},
            "numberOfItems": guide_count,
            "about": [
                {"@type": "Thing", "name": "ذوو الاحتياجات الخاصة"},
                {"@type": "Thing", "name": "التربية الدامجة"},
                {"@type": "Thing", "name": "التدخل المبكر"},
                {"@type": "Thing", "name": "التواصل المعزز والبديل"},
                {"@type": "Thing", "name": "التكنولوجيا المساندة"},
            ],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"},
                {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": canonical},
            ],
        },
        {
            "@type": "ItemList",
            "@id": f"{canonical}#pathways",
            "name": "مسارات مركز ذوي الاحتياجات الخاصة",
            "numberOfItems": len(item_list),
            "itemListElement": item_list,
        },
        {
            "@type": "FAQPage",
            "@id": f"{canonical}#faq",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": question,
                    "acceptedAnswer": {"@type": "Answer", "text": answer},
                }
                for question, answer in faqs
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def render(course: dict[str, Any], manifest: dict[str, Any]) -> str:
    slugs = load_guide_slugs(manifest)
    guide_count = len(slugs)
    paths, item_list = path_cards(slugs)
    faqs = faq_data()
    schema = structured_data(item_list, faqs, guide_count)
    canonical = f"{BASE}/special-needs/"
    title = "ذوو الاحتياجات الخاصة والتربية الدامجة | أدلة عربية عملية"
    description = "مركز عربي مؤسسي يضم 25 دليلًا عمليًا للتواصل والتعليم الدامج والمهارات اليومية والأسرة والحماية والوصول والاستقلال، بمنهج واضح ومصادر أصلية."
    keywords = (
        "ذوو الاحتياجات الخاصة,الأشخاص ذوو الاحتياجات الخاصة,التربية الدامجة,التربية الخاصة,"
        "التدخل المبكر,اضطراب طيف التوحد,فرط الحركة وتشتت الانتباه,صعوبات التعلم,متلازمة داون,"
        "التواصل المعزز والبديل,AAC,التكنولوجيا المساندة,المهارات التكيفية,المهارات اليومية,"
        "الخطة التعليمية الفردية,تكييفات صفية,دعم الأسرة,مقدم الرعاية,التنظيم الحسي,"
        "الوصول السمعي,الوصول البصري,الحماية من التنمر,الانتقال إلى الرشد,الاستقلال,الدمج المدرسي"
    )
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="keywords" content="{e(keywords)}">
<meta name="author" content="{e(BRAND)}">
<meta name="application-name" content="{e(BRAND)}">
<meta name="subject" content="التربية الدامجة ودعم الأشخاص ذوي الاحتياجات الخاصة وأسرهم">
<meta name="audience" content="الأشخاص والأسر والمعلمون ومقدمو الرعاية والمختصون ومقدمو الخدمات">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="googlebot" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="bingbot" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="theme-color" content="#075f5b">
<meta name="color-scheme" content="light">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="ar" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<link rel="icon" href="{BASE_PATH}assets/brand/logo-mark.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{BASE_PATH}assets/brand/logo-mark.svg">
<link rel="search" type="application/opensearchdescription+xml" title="البحث في المنصة" href="{BASE_PATH}opensearch.xml">
<link rel="sitemap" type="application/xml" href="{BASE}/sitemap-special-needs.xml">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_AR">
<meta property="og:site_name" content="{e(BRAND)}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:image" content="{BASE}/assets/brand/social-card.svg">
<meta property="og:image:alt" content="شعار منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{BASE}/assets/brand/social-card.svg">
<meta name="twitter:image:alt" content="شعار منصة الصحة النفسية وذوي الاحتياجات الخاصة">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#103e43;--muted:#4e6d71;--brand:#075f5b;--brand2:#08776e;--accent:#823353;--line:#c5e3df;--mint:#effbf8;--pink:#fff1f6;--lilac:#f3f0ff;--peach:#fff5ed;--white:#fff;--shadow:0 16px 42px rgba(16,76,76,.10)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9;background:linear-gradient(145deg,#fff,var(--mint) 55%,var(--lilac))}}
a{{color:#056a64}}a:focus-visible,summary:focus-visible{{outline:3px solid #0a8179;outline-offset:4px}}.wrap{{width:min(1220px,92%);margin:auto}}
.skip{{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px 14px;border:2px solid var(--brand);border-radius:12px;z-index:99}}.skip:focus{{right:8px}}
.site-header{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}.header-inner{{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:11px 0}}
.brand{{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);font-weight:900}}.brand img{{width:52px;height:52px}}.brand span{{display:grid;line-height:1.35}}.brand small{{color:var(--muted)}}
.nav{{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end}}.nav a{{font-weight:800;text-decoration:none;padding:7px 9px;border-radius:9px}}.nav a:hover{{background:var(--mint)}}
.hero{{padding:58px 0 26px}}.hero-grid{{display:grid;grid-template-columns:1.15fr .85fr;gap:24px;align-items:stretch}}.eyebrow{{color:var(--accent);font-weight:900;margin:0}}h1{{font-size:clamp(2.25rem,6vw,4.8rem);line-height:1.15;margin:.12em 0}}h2{{font-size:clamp(1.65rem,4vw,2.55rem);line-height:1.3;margin:.15em 0}}h3{{line-height:1.45;color:#703049}}.lead{{font-size:1.16rem;color:var(--muted)}}
.panel,.path-card,.metric,.step,.quality-card,.faq-wrap,section.content{{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:21px;padding:20px;box-shadow:var(--shadow)}}
.hero-aside{{background:linear-gradient(145deg,var(--pink),var(--mint),var(--lilac))}}.hero-aside ul{{padding-right:1.2rem}}.actions{{display:flex;gap:9px;flex-wrap:wrap;margin-top:18px}}.button{{display:inline-block;text-decoration:none;font-weight:900;padding:11px 15px;border-radius:13px;background:linear-gradient(135deg,#67d6cc,#a9ebdf);color:#103f42;border:1px solid #55bfb7}}.button.secondary{{background:#fff;border-color:var(--line)}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:18px}}.metric strong{{display:block;font-size:1.8rem;color:var(--accent)}}.section{{padding:34px 0}}.section-intro{{max-width:920px;color:var(--muted)}}
.path-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.path-card{{display:flex;flex-direction:column}}.path-card p{{color:var(--muted);flex:1}}.path-card:nth-child(4n+1){{background:linear-gradient(145deg,#fff,var(--pink))}}.path-card:nth-child(4n+2){{background:linear-gradient(145deg,#fff,var(--mint))}}.path-card:nth-child(4n+3){{background:linear-gradient(145deg,#fff,var(--lilac))}}.path-card:nth-child(4n){{background:linear-gradient(145deg,#fff,var(--peach))}}
.steps,.quality-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.step strong{{display:inline-grid;place-items:center;width:36px;height:36px;border-radius:50%;background:var(--brand);color:#fff}}.step p,.quality-card p{{color:var(--muted)}}
.notice{{border-right:6px solid var(--accent);background:var(--pink);padding:18px 20px;border-radius:16px;margin:18px 0}}.positive{{border-right-color:var(--brand2);background:var(--mint)}}
.table-wrap{{overflow:auto;border-radius:16px}}table{{width:100%;border-collapse:collapse;background:#fff}}caption{{text-align:right;font-weight:900;font-size:1.1rem;padding:12px}}th,td{{border:1px solid #badbd6;padding:11px;text-align:right;vertical-align:top}}th{{background:#e9f8f5}}
.guide-intro{{background:linear-gradient(145deg,#fff,var(--mint))}}.guide-batch{{padding:28px 0}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card,.resource{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px;box-shadow:var(--shadow);display:flex;flex-direction:column}}.card p,.resource p{{color:var(--muted);flex:1}}
details{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px 15px;margin:9px 0}}summary{{cursor:pointer;font-weight:900;color:#663047}}details p{{color:var(--muted)}}.sources li{{margin:.75rem 0}}footer{{border-top:1px solid var(--line);margin-top:38px;padding:28px 0 48px;color:var(--muted)}}
@media(max-width:1050px){{.path-grid,.steps,.quality-grid{{grid-template-columns:repeat(2,1fr)}}.metrics{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:760px){{.header-inner{{align-items:flex-start;flex-direction:column}}.nav{{display:grid;grid-template-columns:repeat(2,1fr);width:100%}}.hero-grid{{grid-template-columns:1fr}}.path-grid,.steps,.quality-grid,.cards{{grid-template-columns:1fr}}.metrics{{grid-template-columns:1fr 1fr}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}*{{animation:none!important;transition:none!important}}}}@media(prefers-contrast:more){{:root{{--line:#557b78;--muted:#2c5155}}.panel,.path-card,.metric,.step,.quality-card,section.content{{box-shadow:none}}}}
@media print{{.site-header,.skip,.actions{{display:none!important}}body{{background:#fff}}.panel,.path-card,.metric,.step,.quality-card,section.content,.card,.resource{{box-shadow:none;break-inside:avoid}}a{{color:#000;text-decoration:underline}}}}
</style>
</head>
<body>
<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a>
<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="{BASE_PATH}"><img src="{BASE_PATH}assets/brand/logo-mark.svg" alt=""><span>{e(BRAND)}<small>{e(SLOGAN)}</small></span></a>
<nav class="nav" aria-label="التنقل الرئيسي"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}care-guides/">أدلة التعامل</a><a aria-current="page" href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a><a href="{BASE_PATH}sectors/child/">الطفل</a><a href="{BASE_PATH}sectors/family/">الأسرة</a><a href="{BASE_PATH}assessment-lab/">منصة التقييم</a><a href="{BASE_PATH}trust/">الثقة والمنهجية</a></nav>
</div></header>
<main id="main">
<section class="hero"><div class="wrap hero-grid">
<div><p class="eyebrow">مركز معرفي وعملي متكامل</p><h1>ذوو الاحتياجات الخاصة والتربية الدامجة</h1>
<p class="lead">مركز عربي منظم يساعد الشخص والأسرة والمعلم ومقدم الرعاية ومقدم الخدمة على الانتقال من المعلومات العامة إلى سؤال واضح وخطة دعم قابلة للتجربة والمتابعة. ينطلق المركز من الكرامة والاختيار والمشاركة وإزالة الحواجز، ويعرض الأدلة بحسب الحاجة اليومية لا بحسب الملصق وحده.</p>
<div class="actions"><a class="button" href="#start">ابدأ حسب حاجتك</a><a class="button secondary" href="#guides">تصفح الأدلة العملية</a><a class="button secondary" href="#method">اقرأ المنهجية</a></div>
<div class="metrics" aria-label="ملخص المركز"><div class="metric"><strong>{guide_count}</strong><span>دليلًا عمليًا منشورًا</span></div><div class="metric"><strong>8</strong><span>مسارات بداية واضحة</span></div><div class="metric"><strong>5</strong><span>دفعات محتوى مترابطة</span></div><div class="metric"><strong>7</strong><span>مراجع مؤسسية أصلية</span></div></div></div>
<aside class="panel hero-aside" aria-label="ما الذي يقدمه المركز؟"><h2>ما الذي ستجده هنا؟</h2><ul><li>خطط للتواصل والتعليم والمهارات اليومية والانتقالات.</li><li>قوائم تحقق للأسرة والمدرسة ومقدمي الخدمات.</li><li>نماذج متابعة قابلة للطباعة ومؤشرات بسيطة لقياس الأثر.</li><li>حدود مهنية واضحة تمنع التشخيص الذاتي والوعود المطلقة.</li><li>روابط مباشرة إلى المصادر الأصلية والمنهجية التحريرية.</li></ul><div class="notice"><strong>مهم:</strong> المحتوى تثقيفي وتنظيمي، ولا يستبدل التقييم المتخصص أو خدمات الطوارئ أو الأنظمة المحلية.</div></aside>
</div></section>
<section class="section" id="start"><div class="wrap"><p class="eyebrow">نقطة البداية</p><h2>ابدأ حسب الحاجة الأكثر تأثيرًا الآن</h2><p class="section-intro">قد يجتمع أكثر من احتياج في الوقت نفسه. اختر المسار الذي يؤثر مباشرة في الأمان أو الفهم أو التواصل أو التعلم أو المشاركة، ثم انتقل إلى الأدلة المرتبطة بدل محاولة تطبيق تغييرات كثيرة دفعة واحدة.</p><div class="path-grid">{paths}</div></div></section>
<section class="section"><div class="wrap"><p class="eyebrow">طريقة الاستخدام</p><h2>من الملاحظة إلى خطة دعم قابلة للمراجعة</h2><div class="steps"><article class="step"><strong>1</strong><h3>صف الموقف</h3><p>اكتب ما يحدث ومتى وأين ومع من، وما المهمة المطلوبة، دون تفسير النية أو وصف الشخصية.</p></article><article class="step"><strong>2</strong><h3>حدد الحاجز</h3><p>افحص الفهم واللغة والحواس والبيئة والألم والنوم والضغط وطول المهمة والمواد المتاحة قبل اختيار الحل.</p></article><article class="step"><strong>3</strong><h3>جرّب تعديلًا واحدًا</h3><p>اختر دعمًا محددًا، وحدد من سيطبقه ومدة التجربة ومؤشر النجاح، مع الحفاظ على اختيار الشخص وراحته.</p></article><article class="step"><strong>4</strong><h3>راجع وقرر</h3><p>قارن ما قبل وما بعد، واسأل الشخص والأسرة والفريق، ثم ثبّت التعديل أو عدله أو اطلب تقييمًا أوسع.</p></article></div></div></section>
<section class="section"><div class="wrap"><h2>مصفوفة قرار سريعة</h2><p class="section-intro">هذه المصفوفة لا تعطي تشخيصًا. وظيفتها تنظيم الخطوة التالية وتقليل العشوائية في اختيار الأدوات أو الخدمات.</p><div class="table-wrap"><table><caption>السؤال الأول والخطوة الأنسب</caption><thead><tr><th>ما الذي تلاحظه؟</th><th>ابدأ بـ</th><th>اطلب دعمًا متخصصًا عندما</th></tr></thead><tbody><tr><td>صعوبة متكررة في التعبير أو فهم الرسائل</td><td>دليل التواصل المعزز والبديل، ومراجعة طريقة عرض التعليمات والوقت المتاح للاستجابة.</td><td>تؤثر الصعوبة في الأمان أو الاحتياجات الأساسية أو المشاركة، أو تظهر خسارة في مهارات سابقة.</td></tr><tr><td>رفض أو انسحاب أو توتر داخل مهمة محددة</td><td>وصف المهمة والبيئة والحمل الحسي وطول التعليمات، ثم تجربة تعديل واحد قابل للقياس.</td><td>يتكرر الضرر أو الخطر، أو لا يمكن تحديد السبب، أو لا تنجح التعديلات البسيطة.</td></tr><tr><td>تأخر في مهارة يومية أو حاجة إلى مساعدة كبيرة</td><td>تحليل المهارة إلى خطوات، وتحديد مستوى المساعدة، وتعليم خطوة واحدة ثم تعميمها.</td><td>توجد صعوبات واسعة في أكثر من مجال أو أثر واضح على الصحة أو الأمان أو الاستقلال.</td></tr><tr><td>ضعف المشاركة في الصف أو الواجبات</td><td>خطة تكييفات صفية وواجبات، مع مؤشرات مثل زمن البدء وعدد التذكيرات ونسبة الإكمال.</td><td>تستمر الفجوة رغم التعديلات، أو توجد حاجة إلى تقييم تعليمي أو لغوي أو نمائي أوسع.</td></tr><tr><td>شكوى من مركز أو خدمة أو برنامج</td><td>قائمة جودة مقدم الخدمة: الأهداف، القياس، الخصوصية، المؤهلات، الشكاوى، ومشاركة الشخص.</td><td>توجد إساءة أو إهمال أو تقييد أو سرية غير مبررة أو منع للأسرة والشخص من المعلومات.</td></tr></tbody></table></div></div></section>
<section class="section"><div class="wrap"><div class="notice positive"><h2>الكرامة واللغة ليستا إضافة شكلية</h2><p>استخدم اسم الشخص وتفضيله اللغوي، وافصل بين الإنسان والحالة، وركز على الحاجز والدعم المطلوب. لا تفترض أن عدم الكلام يعني عدم الفهم، ولا تشترط التواصل البصري، ولا تجعل الطاعة أو إخفاء الفروق هدفًا بحد ذاته. المشاركة الحقيقية تعني إتاحة الخيارات ووقت المعالجة ووسيلة التعبير المناسبة.</p></div></div></section>
<section class="section"><div class="wrap"><h2>معايير جودة الخطة أو الخدمة</h2><p class="section-intro">قبل اعتماد خطة منزلية أو مدرسية أو خدمة، افحص العناصر التالية. غياب عنصر واحد لا يحسم الجودة، لكن تراكم الغموض والوعود غير القابلة للقياس علامة تستحق التوقف.</p><div class="quality-grid"><article class="quality-card"><h3>هدف وظيفي واضح</h3><p>يصف ما الذي سيتحسن في التواصل أو التعلم أو الاستقلال أو الأمان، لا مجرد إكمال جلسات أو خفض سلوك دون فهم وظيفته.</p></article><article class="quality-card"><h3>خط أساس ومؤشر</h3><p>توجد طريقة بسيطة لمعرفة الوضع قبل الخطة وما الذي سيعد تحسنًا، مع مراجعة دورية وتوثيق مفهوم للأسرة والشخص.</p></article><article class="quality-card"><h3>مشاركة واختيار</h3><p>يسمع الفريق رأي الشخص ويعرض بدائل ويحترم الرفض والراحة والخصوصية، ويشرح القرارات بلغة مفهومة.</p></article><article class="quality-card"><h3>سلامة وحدود</h3><p>توجد سياسة واضحة للحماية والشكاوى والخصوصية والطوارئ، ولا تقدم وعود شفاء أو نتائج مضمونة أو ضغطًا لشراء خدمات إضافية.</p></article></div></div></section>
<section class="section" id="guides"><div class="wrap"><div class="panel guide-intro"><p class="eyebrow">المكتبة التطبيقية</p><h2>الأدلة العملية المتخصصة</h2><p>تضم المكتبة خمس دفعات مترابطة تغطي التواصل والوصول والتعليم الدامج والتدخل المبكر والمهارات اليومية والحركة والحماية والتنظيم الحسي والانتقال إلى الرشد وجودة الخدمات والطوارئ الأسرية. كل دليل يتضمن شرحًا، قائمة تحقق، أخطاء شائعة، قالب عمل، ومصادر أصلية.</p></div>
<section><h2>مصادر الوحدة الحالية</h2><p>يبني المركز مبادئه العامة على مصادر مؤسسية أصلية. إدراج الرابط لا يعني أن الجهة راجعت المنصة أو اعتمدت محتواها.</p><ul class="sources">{source_cards()}</ul></section>
</div></section>
<section class="section" id="method"><div class="wrap"><h2>المنهجية التحريرية وحدود الاستخدام</h2><div class="quality-grid"><article class="quality-card"><h3>الوظيفة قبل الملصق</h3><p>يبدأ الدليل من المشاركة والمهمة والبيئة والاحتياج، ولا يفترض أن الاسم التشخيصي يحدد وحده الدعم المناسب.</p></article><article class="quality-card"><h3>مصادر أصلية</h3><p>تفضّل المنصة الهيئات الدولية والمعايير المهنية والوثائق الأصلية، وتوضح وظيفة كل مصدر بدل استخدام روابط للزينة.</p></article><article class="quality-card"><h3>مراجعة صادقة</h3><p>الأدلة الحالية خضعت لمراجعة داخلية منظمة، والمراجعة الخارجية المتخصصة موصى بها ولم تُعرض على أنها مكتملة.</p></article><article class="quality-card"><h3>لا تشخيص ولا وصف علاج</h3><p>المحتوى لا يحدد أهلية الخدمات ولا يغير دواء أو جرعة ولا يقدم تفسيرًا قانونيًا موحدًا، ويحث على الخدمات المحلية عند الحاجة.</p></article></div><div class="notice"><strong>حالة المراجعة:</strong> مراجعة داخلية مع توصية بمراجعة خارجية متخصصة. <strong>آخر تحديث للمركز:</strong> <time datetime="{UPDATED}">{UPDATED}</time>.</div></div></section>
<section class="section"><div class="wrap faq-wrap"><p class="eyebrow">أسئلة متكررة</p><h2>إجابات تساعد على اتخاذ خطوة أكثر دقة</h2>{faq_html(faqs)}</div></section>
<section class="section"><div class="wrap"><div class="notice"><h2>متى تكون الأولوية للأمان؟</h2><p>عند وجود خطر مباشر، إصابة، فقدان مفاجئ في مهارات أو وعي، صعوبة تنفس، عنف، إساءة محتملة، استغلال، ضياع، أو عجز عن تلبية احتياج أساسي، لا تنتظر إكمال خطة تعليمية. استخدم رقم الطوارئ والخدمات الصحية أو الحماية المختصة في بلدك بحسب طبيعة الخطر.</p></div></div></section>
</main>
<footer><div class="wrap"><p><strong>{e(BRAND)}</strong> — {e(SLOGAN)}</p><p><a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}care-guides/">أدلة التعامل</a> · <a href="{BASE_PATH}partners/">الشركاء والشفافية</a> · <a href="{BASE_PATH}api/">واجهة البيانات</a></p><p>© 2026 {e(FOUNDING_NAME)}. محتوى تثقيفي منظم يحترم الخصوصية والكرامة ولا يستبدل الخدمات المحلية المتخصصة.</p></div></footer>
</body></html>'''


def sync_robots(site: Path) -> bool:
    path = site / "robots.txt"
    child = f"Sitemap: {BASE}/sitemap-special-needs.xml"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
    else:
        text = "User-agent: *\nAllow: /\n"
    lines = [line.rstrip() for line in text.splitlines()]
    lines = [line for line in lines if line != child]
    lines.append(child)
    normalized = "\n".join(lines).strip() + "\n"
    changed = not path.is_file() or path.read_text(encoding="utf-8") != normalized
    path.write_text(normalized, encoding="utf-8")
    return changed


def validate_output(source: str, guide_count: int) -> dict[str, int]:
    required = [
        '<html lang="ar" dir="rtl">',
        '<meta name="keywords"',
        '<meta name="googlebot"',
        '<meta name="bingbot"',
        'hreflang="ar"',
        'hreflang="x-default"',
        'property="og:image"',
        'name="twitter:image"',
        '"@type": "CollectionPage"',
        '"@type": "ItemList"',
        '"@type": "FAQPage"',
        '<section><h2>مصادر الوحدة الحالية</h2>',
        f'<strong>{guide_count}</strong><span>دليلًا عمليًا منشورًا</span>',
        'الطوارئ المحلية',
        'مراجعة داخلية',
    ]
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise SystemExit(f"Enhanced special-needs hub is missing markers: {missing}")
    if source.count("<h1") != 1:
        raise SystemExit("Enhanced special-needs hub must contain exactly one H1")
    h2 = len(re.findall(r"<h2\b", source))
    h3 = len(re.findall(r"<h3\b", source))
    if h2 < 10 or h3 < 20:
        raise SystemExit(f"Enhanced special-needs hierarchy is too shallow: h2={h2}, h3={h3}")
    if BANNED.search(source):
        raise SystemExit("Prohibited person-label language remains in enhanced hub")
    if any(token in source for token in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "eval(", "new Function(")):
        raise SystemExit("Unsafe or network runtime detected in enhanced hub")
    return {"h1": 1, "h2": h2, "h3": h3}


def publish(site: Path) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    hub = site / "special-needs" / "index.html"
    if not hub.is_file():
        raise SystemExit("Legacy special-needs publisher must run before v235 hub enhancement")
    course, manifest = load_inputs()
    source = render(course, manifest)
    counts = validate_output(source, len(manifest["source_files"]))
    hub.write_text(source, encoding="utf-8")
    robots_changed = sync_robots(site)
    report = {
        "version": 235,
        "status": "production-integrated",
        "route": "special-needs/index.html",
        "guide_count": len(manifest["source_files"]),
        "pathway_count": 8,
        "faq_count": len(faq_data()),
        "source_count": 7,
        "review_status": "internally-reviewed",
        "external_review": "recommended-not-completed",
        "seo": {
            "canonical": True,
            "hreflang": ["ar", "x-default"],
            "robots": True,
            "googlebot": True,
            "bingbot": True,
            "keywords": True,
            "open_graph": True,
            "twitter_card": True,
            "structured_data": ["Organization", "WebSite", "CollectionPage", "BreadcrumbList", "ItemList", "FAQPage"],
        },
        "accessibility": {
            "skip_link": True,
            "keyboard_focus": True,
            "reduced_motion": True,
            "high_contrast": True,
            "print_styles": True,
            "javascript_required": False,
        },
        "inclusive_language_gate": True,
        "robots_child_sitemap_changed": robots_changed,
        **counts,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-hub-v235.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
