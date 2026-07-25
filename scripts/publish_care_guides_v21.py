from __future__ import annotations

import html
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA_FILES = [
    ROOT / "content/v18/care-guides-ar.json",
    ROOT / "content/v18/care-guides-adhd-ar.json",
    ROOT / "content/v18/care-guides-autism-ar.json",
]
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
TODAY = date.today().isoformat()
BLOCKED_REVIEW_STATUSES = {"needs-specialist-review"}
SITE_NAME = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SOCIAL_IMAGE = BASE + "assets/brand/social-card.svg"
LOGO = BASE + "assets/brand/logo-mark.svg"

SECTION_LABELS = {
    "understanding": "فهم الحالة دون وصم",
    "what_the_person_may_feel": "ما الذي قد يشعر به الشخص من الداخل؟",
    "strengths_and_differences": "نقاط القوة والفروق الفردية",
    "communication_plan": "خطة التواصل",
    "sensory_plan": "خطة التنظيم الحسي",
    "do": "ما الذي يمكنك فعله؟",
    "avoid": "ما الذي ينبغي تجنبه؟",
    "home_plan": "خطة الدعم في المنزل",
    "school_plan": "خطة الدعم في المدرسة",
    "homework_protocol": "بروتوكول الواجبات وبدء المهام",
    "transition_protocol": "بروتوكول الانتقالات والتغيير",
    "meltdown_protocol": "بروتوكول الانهيار والتصعيد",
    "wandering_protocol": "بروتوكول الخروج أو الضياع",
    "emotion_protocol": "بروتوكول الانفعال والتصعيد",
    "sleep_plan": "خطة النوم",
    "food_plan": "خطة الطعام والتغذية",
    "medication_awareness": "التوعية الدوائية وحدود دور الأسرة",
    "when_to_seek_help": "متى نطلب مساعدة مهنية؟",
    "caregiver_plan": "خطة مقدم الرعاية",
    "observe": "ما الذي نراقبه؟",
    "conversation_steps": "خطوات الحوار",
    "plan": "خطة عملية مستدامة",
    "warning_signs": "إشارات الاستنزاف أو الخطر",
}

SECTION_INTROS = {
    "understanding": "افهم السياق والنمط الوظيفي قبل الحكم على السلوك أو اختزاله في صفة شخصية.",
    "what_the_person_may_feel": "هذه احتمالات لبناء التعاطف، وليست افتراضًا أن جميع الأشخاص يعيشون التجربة نفسها.",
    "strengths_and_differences": "حدّد القدرات والاهتمامات والبيئات التي يظهر فيها الأداء الأفضل، لا الصعوبات وحدها.",
    "communication_plan": "استخدم تواصلًا واضحًا وقصيرًا ومحترمًا يترك للشخص مساحة للتعبير عن تفضيلاته.",
    "sensory_plan": "راقب أثر الصوت والضوء والازدحام والملمس والحركة، وعدّل البيئة تدريجيًا.",
    "do": "اختر خطوة أو خطوتين قابلتين للقياس وراجع أثرهما قبل توسيع الخطة.",
    "avoid": "قد تزيد هذه الممارسات الضغط أو الوصم أو الصراع حتى عندما تكون النية مساعدة الشخص.",
    "home_plan": "حوّل الدعم إلى روتين متوقع واتفاقات واضحة بدل المواجهة والتذكير المستمر.",
    "school_plan": "اتفقوا على أهداف ومسؤوليات ومؤشرات مراجعة بسيطة بين الأسرة والمدرسة.",
    "homework_protocol": "قلّل تكلفة بدء المهمة وتنظيمها بدل تحويل الواجب إلى اختبار للعلاقة الأسرية.",
    "transition_protocol": "اجعل الانتقال متوقعًا ومجزأً ومدعومًا بإشارات بصرية أو زمنية.",
    "meltdown_protocol": "أثناء التصعيد قدّم السلامة وتقليل المثيرات، وأجّل النقاش إلى ما بعد الهدوء.",
    "wandering_protocol": "اكتب خطة وقاية واستجابة مشتركة تحترم الكرامة ولا تعتمد على شخص واحد.",
    "emotion_protocol": "اعترف بالشعور مع وضع حدود واضحة للسلوك المؤذي.",
    "sleep_plan": "راجع النوم ضمن الصورة الكاملة واطلب تقييمًا عند استمرار المشكلة أو أثرها الوظيفي.",
    "food_plan": "تجنب الصراع حول الطعام واطلب تقييمًا عند فقدان الوزن أو الاختناق أو التقييد الشديد.",
    "medication_awareness": "راقب وتواصل والتزم بالخطة؛ لا تعدّل الدواء أو الجرعة دون الطبيب.",
    "when_to_seek_help": "اطلب دعمًا مهنيًا عندما تستمر الصعوبة أو تتسع أو تعطل الحياة اليومية.",
    "caregiver_plan": "استدامة الرعاية تتطلب حدودًا وراحة وتقاسمًا للمهام.",
    "observe": "سجّل المدة والتكرار والسياق والأثر بدل الاعتماد على الانطباع العام.",
    "conversation_steps": "اجعل الحوار بابًا للفهم والاتفاق، لا استجوابًا أو محاضرة.",
    "plan": "اجعل الخطة محددة ومرنة وموزعة المسؤوليات، وراجعها ببيانات بسيطة.",
    "warning_signs": "هذه العلامات تعني أن الخطة تحتاج دعمًا أو تخفيفًا أو إعادة توزيع.",
}

GUIDE_FAQS = [
    ("هل يكفي هذا الدليل للتشخيص أو العلاج؟", "لا. الدليل تثقيفي ولا يستبدل التقييم أو التشخيص أو العلاج أو خطة الطوارئ الفردية."),
    ("كيف أختار أول خطوة؟", "ابدأ بالأكثر تأثيرًا في السلامة أو الوظيفة، واختر إجراءً واحدًا يمكن ملاحظته ومراجعته."),
    ("ماذا أفعل إذا لم تنجح الخطة؟", "راجع السياق والتوقعات والنوم والمثيرات، واطلب تقييمًا مهنيًا عند استمرار التعطل أو ازدياد الشدة."),
]
HUB_FAQS = [
    ("لمن صُممت أدلة التعامل؟", "للأفراد والأسر والأصدقاء والمعلمين ومقدمي الرعاية الذين يحتاجون دعمًا عمليًا آمنًا."),
    ("هل الأدلة بديل عن الطبيب أو المعالج؟", "لا. هي للتثقيف وتنظيم الدعم والاستعداد للحوار المهني، وليست تشخيصًا أو علاجًا فرديًا."),
    ("كيف أتعامل مع حالة طارئة؟", "عند الخطر المباشر أو الوشيك استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة."),
    ("كيف تُختار المصادر؟", "تُفضّل الإرشادات المؤسسية والمهنية الموثوقة، وتُعرض الروابط الأصلية وحدود الاستخدام."),
]

STYLE = """
:root{--ink:#103e43;--muted:#526f73;--brand:#075f5b;--accent:#8b315c;--mist:#effaf8;--mint:#ddf7ef;--lilac:#f3f0ff;--pink:#fff0f6;--cream:#fffaf3;--danger:#fff1f3;--line:#c4e1dd;--shadow:0 18px 54px rgba(15,83,80,.11)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:linear-gradient(145deg,#fff,var(--mist) 48%,var(--lilac));color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}a{color:#066b65}a:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #0a8b82;outline-offset:4px}.skip{position:fixed;right:-9999px;top:8px;z-index:1000;background:#fff;padding:10px 16px;border:2px solid var(--brand);border-radius:12px;font-weight:900}.skip:focus{right:8px}.site-head{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}.head-in{width:min(1220px,94%);margin:auto;display:flex;align-items:center;justify-content:space-between;gap:18px;padding:10px 0}.brand{display:flex;align-items:center;gap:10px;color:var(--ink);text-decoration:none}.brand span{display:grid;line-height:1.35}.brand small{color:var(--muted)}.nav{display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end}.nav a{text-decoration:none;font-weight:800;padding:7px 9px;border-radius:10px}.nav a:hover,.nav a[aria-current=page]{background:var(--mist)}.wrap{width:min(1120px,92%);margin:auto;padding:24px 0 70px}.crumbs ol{display:flex;gap:7px;flex-wrap:wrap;list-style:none;padding:0;margin:8px 0 18px;color:var(--muted)}.crumbs li:not(:last-child)::after{content:'←';margin-inline-start:7px}.hero,.section,.sources{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:24px;padding:clamp(20px,4vw,38px);box-shadow:var(--shadow);margin:18px 0}.hero{background:linear-gradient(135deg,var(--pink),var(--mist),var(--lilac));overflow:hidden}.eyebrow,.kicker{color:var(--accent);font-weight:900;margin:0}.hero h1{font-size:clamp(2.1rem,5.6vw,4rem);line-height:1.25;margin:.18em 0;max-width:22ch}.lead,.section p,.card p{color:var(--muted)}.lead{max-width:82ch;font-size:1.12rem}.actions,.tags{display:flex;gap:9px;flex-wrap:wrap;margin-top:16px}.btn{display:inline-block;text-decoration:none;padding:10px 16px;border-radius:13px;background:linear-gradient(135deg,#67d6cc,#a9ebdf);border:1px solid #55bfb7;color:#103f42;font-weight:900;font:inherit;cursor:pointer}.btn.alt{background:#fff;border-color:var(--line)}.tag{padding:6px 11px;border-radius:999px;background:var(--mint);font-weight:800;font-size:.93rem}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:22px}.stat{background:rgba(255,255,255,.82);border:1px solid var(--line);border-radius:17px;padding:15px}.stat strong{display:block;color:var(--accent);font-size:1.55rem}.section h2,.sources h2{margin:.1em 0 .35em;font-size:clamp(1.55rem,3.5vw,2.25rem)}.section li{margin:.62rem 0}.danger{background:linear-gradient(145deg,#fff,var(--danger));border-color:#e9a2b7}.notice{border-right:6px solid var(--accent);background:var(--pink);border-radius:17px;padding:18px 20px;margin:18px 0}.emergency{border-right:6px solid #ba2f58;background:var(--danger);border-radius:20px;padding:21px;margin:18px 0;color:#651f36;font-weight:800}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.grid.two{grid-template-columns:repeat(2,1fr)}.card{background:#fff;border:1px solid var(--line);border-radius:19px;padding:19px;display:flex;flex-direction:column}.card:nth-child(4n+1){background:linear-gradient(145deg,#fff,var(--pink))}.card:nth-child(4n+2){background:linear-gradient(145deg,#fff,var(--mist))}.card:nth-child(4n+3){background:linear-gradient(145deg,#fff,var(--lilac))}.card:nth-child(4n){background:linear-gradient(145deg,#fff,var(--cream))}.card h3{margin:.1em 0 .3em;color:#71304f}.card p{flex:1}.card a{font-weight:900}.toc ul{columns:2;gap:28px}.toc li{break-inside:avoid}.timeline{counter-reset:step;display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.timeline article{background:#fff;border:1px solid var(--line);border-radius:18px;padding:19px}.timeline article:before{counter-increment:step;content:counter(step);display:grid;place-items:center;width:34px;height:34px;border-radius:50%;background:var(--brand);color:#fff;font-weight:900}.table{width:100%;border-collapse:collapse;background:#fff}.table th,.table td{padding:12px;border:1px solid var(--line);vertical-align:top;text-align:right}.table th{background:var(--mist)}.worksheet td{height:54px}.faq details{border:1px solid var(--line);border-radius:14px;padding:12px 15px;margin:10px 0;background:#fff}.faq summary{cursor:pointer;font-weight:900;color:#71304f}.small{color:var(--muted);font-size:.94rem}.footer{border-top:1px solid var(--line);background:#fff;padding:34px max(4%,calc((100% - 1120px)/2))}.foot-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.footer h2{font-size:1.15rem}.footer p,.footer li{color:var(--muted)}@media(max-width:900px){.head-in{align-items:flex-start;flex-direction:column}.nav{justify-content:flex-start}.grid,.stats,.timeline,.foot-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:650px){.wrap{width:94%}.nav{display:grid;grid-template-columns:1fr 1fr;width:100%}.nav a{text-align:center}.grid,.grid.two,.stats,.timeline,.foot-grid{grid-template-columns:1fr}.toc ul{columns:1}.table{display:block;overflow-x:auto}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{animation:none!important;transition:none!important}}@media print{.site-head,.skip,.actions,.footer{display:none!important}body{background:#fff}.wrap{width:100%;padding:0}.hero,.section,.sources{box-shadow:none;break-inside:avoid}a{color:#000;text-decoration:none}}
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def word_count(value: str) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", value, flags=re.UNICODE))


def keywords(values: list[str]) -> str:
    result: list[str] = []
    for value in values + ["أدلة التعامل النفسي", "دعم الأسرة", "مقدمو الرعاية", "الصحة النفسية", "طلب المساعدة المهنية"]:
        item = " ".join(str(value).split()).strip(" ،,")
        if item and item not in result:
            result.append(item)
    return ",".join(result[:28])


def header() -> str:
    links = [("", "الرئيسية"), ("care-guides/", "أدلة التعامل"), ("encyclopedia/", "الموسوعة"), ("special-needs/", "ذوو الاحتياجات الخاصة"), ("magazine/", "المجلة والأبحاث"), ("assessment-lab/", "المقاييس")]
    nav = "".join(f'<a href="{BASE_PATH}{href}"{(" aria-current=\"page\"" if href == "care-guides/" else "")}>{label}</a>' for href, label in links)
    return f'<a class="skip" href="#main-content">انتقل إلى المحتوى</a><header class="site-head"><div class="head-in"><a class="brand" href="{BASE_PATH}"><img src="{BASE_PATH}assets/brand/logo-mark.svg" alt="" width="48" height="48"><span><strong>منصة الصحة النفسية</strong><small>معرفة تحترم الإنسان</small></span></a><nav class="nav" aria-label="التنقل الرئيسي">{nav}</nav></div></header>'


def footer() -> str:
    return f'<footer class="footer"><div class="foot-grid"><section><h2>عن أدلة التعامل</h2><p>محتوى عربي ينظم الدعم اليومي وحدود دور الأسرة ومقدم الرعاية والوصول إلى المساعدة المهنية.</p></section><section><h2>روابط مؤسسية</h2><ul><li><a href="{BASE_PATH}trust/">الثقة والمنهجية</a></li><li><a href="{BASE_PATH}about/">عن المنصة</a></li><li><a href="{BASE_PATH}api/">واجهة البيانات</a></li><li><a href="{BASE_PATH}sitemap.xml">خريطة الموقع</a></li></ul></section><section><h2>تنبيه صحي</h2><p>لا يقدم المحتوى تشخيصًا أو علاجًا فرديًا. عند الخطر المباشر استخدم خدمات الطوارئ المحلية.</p></section></div><p>© {date.today().year} {SITE_NAME}. جميع الحقوق محفوظة.</p></footer>'


def faq_markup(items: list[tuple[str, str]], heading: str) -> str:
    details = "".join(f'<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>' for q, a in items)
    return f'<section class="section faq"><h2>{esc(heading)}</h2>{details}</section>'


def faq_schema(items: list[tuple[str, str]]) -> dict:
    return {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in items]}


def head(title: str, description: str, canonical: str, schema: dict, page_keywords: list[str], page_type: str, modified: str) -> str:
    structured = json.dumps({"@context": "https://schema.org", "@graph": schema}, ensure_ascii=False).replace("</", "<\\/")
    article = f'<meta property="article:modified_time" content="{esc(modified)}">' if page_type == "article" else ""
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)} | {SITE_NAME}</title><meta name="description" content="{esc(description)}"><meta name="keywords" content="{esc(keywords(page_keywords))}"><meta name="author" content="{SITE_NAME}"><meta name="publisher" content="{SITE_NAME}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="googlebot" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="referrer" content="strict-origin-when-cross-origin"><meta name="theme-color" content="#075f5b"><meta name="color-scheme" content="light"><link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="ar" href="{esc(canonical)}"><link rel="alternate" hreflang="x-default" href="{esc(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><link rel="icon" href="{BASE_PATH}assets/brand/logo-mark.svg" type="image/svg+xml"><link rel="apple-touch-icon" href="{BASE_PATH}assets/brand/logo-mark.svg"><link rel="sitemap" type="application/xml" href="{BASE}sitemap-care-guides.xml"><meta property="og:type" content="{page_type}"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{SITE_NAME}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta property="og:image" content="{SOCIAL_IMAGE}"><meta property="og:image:alt" content="هوية {SITE_NAME}">{article}<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}"><meta name="twitter:description" content="{esc(description)}"><meta name="twitter:image" content="{SOCIAL_IMAGE}"><script type="application/ld+json">{structured}</script><style>{STYLE}</style></head>'''


def guide_schema(guide: dict, canonical: str) -> list[dict]:
    steps: list[dict] = []
    for key in ("do", "communication_plan", "conversation_steps", "plan", "caregiver_plan", "home_plan", "school_plan"):
        for item in guide.get(key, []):
            steps.append({"@type": "HowToStep", "position": len(steps) + 1, "name": item, "text": item})
    graph: list[dict] = [{"@type": "Article", "@id": canonical + "#article", "headline": guide["title"], "description": guide["summary"], "inLanguage": "ar", "dateModified": guide.get("reviewed_at", TODAY), "mainEntityOfPage": {"@type": "WebPage", "@id": canonical}, "image": SOCIAL_IMAGE, "keywords": guide.get("search_intent", []), "author": {"@type": "Organization", "name": SITE_NAME, "url": BASE}, "publisher": {"@type": "Organization", "name": SITE_NAME, "url": BASE, "logo": {"@type": "ImageObject", "url": LOGO}}, "citation": [source["url"] for source in guide["sources"]]}]
    if steps:
        graph.append({"@type": "HowTo", "name": guide["title"], "description": guide["summary"], "inLanguage": "ar", "url": canonical, "step": steps})
    graph.extend([{"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE}, {"@type": "ListItem", "position": 2, "name": "أدلة التعامل", "item": BASE + "care-guides/"}, {"@type": "ListItem", "position": 3, "name": guide["title"], "item": canonical}]}, faq_schema(GUIDE_FAQS)])
    return graph


def guide_page(guide: dict) -> str:
    canonical = BASE + "care-guides/" + guide["slug"] + "/"
    rendered: list[str] = []
    toc: list[str] = []
    for key, label in SECTION_LABELS.items():
        items = guide.get(key)
        if not items:
            continue
        rows = "".join(f"<li>{esc(item)}</li>" for item in items)
        rendered.append(f'<section id="section-{key}" class="section{(" danger" if key in {"when_to_seek_help", "warning_signs"} else "")}"><p class="kicker">محور عملي</p><h2>{esc(label)}</h2><p>{esc(SECTION_INTROS.get(key, "استخدم هذه النقاط كإطار مرن يناسب عمر الشخص وسياقه وخطته المهنية."))}</p><ul>{rows}</ul></section>')
        toc.append(f'<li><a href="#section-{key}">{esc(label)}</a></li>')
    audience = "".join(f'<span class="tag">{esc(item)}</span>' for item in guide.get("audience", []))
    sources = "".join(f'<li><a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(source["publisher"])} — {esc(source["title"])} ({esc(source["year"])})</a></li>' for source in guide["sources"])
    emergency = guide.get("emergency_note", "")
    first_do = (guide.get("do") or guide.get("plan") or guide.get("conversation_steps") or ["اختر خطوة واحدة محددة وراقب أثرها."])[0]
    first_avoid = (guide.get("avoid") or guide.get("warning_signs") or ["تجنب التشخيص من الإنترنت أو الضغط أو الوعود غير القابلة للتنفيذ."])[0]
    first_help = (guide.get("when_to_seek_help") or ([emergency] if emergency else ["اطلب مساعدة مهنية عند استمرار التعطل أو ظهور خطر."]))[0]
    cards = f'<article class="card"><p class="kicker">ابدأ الآن</p><h3>خطوة أولى آمنة</h3><p>{esc(first_do)}</p></article><article class="card"><p class="kicker">تجنب</p><h3>ممارسة قد تزيد الضغط</h3><p>{esc(first_avoid)}</p></article><article class="card"><p class="kicker">صعّد الدعم</p><h3>متى لا ننتظر؟</h3><p>{esc(first_help)}</p></article>'
    reviewed = guide.get("reviewed_at", TODAY)
    body = f'''<body>{header()}<main id="main-content" class="wrap"><nav class="crumbs" aria-label="مسار الصفحة"><ol><li><a href="{BASE_PATH}">الرئيسية</a></li><li><a href="{BASE_PATH}care-guides/">أدلة التعامل</a></li><li aria-current="page">{esc(guide['title'])}</li></ol></nav><header class="hero"><p class="eyebrow">دليل عملي غير تشخيصي</p><h1>{esc(guide['title'])}</h1><p class="lead">{esc(guide['summary'])}</p><div class="tags">{audience}</div><div class="stats"><div class="stat"><strong>{len(rendered)}</strong><span>محاور عملية</span></div><div class="stat"><strong>{sum(len(guide.get(k, [])) for k in SECTION_LABELS)}</strong><span>نقاط تطبيقية</span></div><div class="stat"><strong>{len(guide['sources'])}</strong><span>مصادر أصلية</span></div><div class="stat"><strong>{len(guide.get('audience', []))}</strong><span>فئات مستفيدة</span></div></div><div class="actions"><a class="btn" href="#action-plan">ابدأ بخطة التطبيق</a><a class="btn alt" href="#sources">راجع المصادر</a><button class="btn alt" type="button" onclick="window.print()">طباعة الدليل</button></div><p class="small">آخر تحديث تقني: <time datetime="{esc(reviewed)}">{esc(reviewed)}</time>. لا توجد مراجعة اختصاصية بشرية موثقة ما لم يُذكر خلاف ذلك.</p></header><aside class="notice"><strong>طريقة الاستخدام:</strong> اختر خطوة واحدة قابلة للقياس وحدد موعدًا لمراجعة أثرها. لا تطبق جميع التوصيات دفعة واحدة.</aside><section class="section"><h2>الخلاصة التنفيذية</h2><div class="grid">{cards}</div></section><nav class="section toc" aria-label="محتويات الدليل"><h2>محتويات الدليل</h2><ul>{''.join(toc)}<li><a href="#action-plan">خطة التطبيق والمتابعة</a></li><li><a href="#worksheet">ورقة متابعة</a></li><li><a href="#sources">المصادر والمنهجية</a></li></ul></nav>{''.join(rendered)}<aside class="emergency" role="alert"><strong>عند الخطر أو التدهور الحاد:</strong> {esc(emergency or 'استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة عند وجود خطر مباشر أو وشيك.')}</aside><section id="action-plan" class="section"><p class="kicker">تحويل المعرفة إلى ممارسة</p><h2>خطة تطبيق من ثلاث مراحل</h2><div class="timeline"><article><h3>خلال 24 ساعة</h3><p>حدد المشكلة الأكثر تأثيرًا وسجّل خط الأساس والسياق.</p></article><article><h3>خلال 7 أيام</h3><p>طبّق التعديل بثبات وراقب التكرار والشدة والوظيفة.</p></article><article><h3>عند المراجعة</h3><p>استمر عند التحسن، وعدّل الخطة أو اطلب تقييمًا عند التعطل.</p></article></div></section><section id="worksheet" class="section"><h2>ورقة متابعة قابلة للطباعة</h2><p>استخدمها لتحديد الأنماط ومشاركة ملاحظات موضوعية، لا لإصدار تشخيص.</p><table class="table worksheet"><thead><tr><th>التاريخ والسياق</th><th>ما الذي سبق الموقف؟</th><th>الاستجابة</th><th>النتيجة والتعلم</th></tr></thead><tbody><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td></td><td></td></tr></tbody></table></section>{faq_markup(GUIDE_FAQS, 'أسئلة شائعة')}<section id="sources" class="sources"><p class="kicker">شفافية المصدر</p><h2>مصادر مؤسسية للمراجعة</h2><ul>{sources}</ul><p class="small">المصادر تبني إطارًا تثقيفيًا عامًا وقد تحتاج الإرشادات إلى تكييف فردي. الدليل لا يستبدل التقييم أو العلاج.</p><div class="actions"><a class="btn alt" href="{BASE_PATH}care-guides/">بقية الأدلة</a><a class="btn alt" href="{BASE_PATH}trust/">منهجية الثقة</a></div></section></main>{footer()}</body></html>'''
    return head(guide["title"], guide["summary"], canonical, guide_schema(guide, canonical), list(guide.get("search_intent", [])) + list(guide.get("audience", [])) + [guide["title"]], "article", reviewed) + body


def category(guide: dict) -> str:
    text = f"{guide.get('slug', '')} {guide.get('title', '')} {' '.join(guide.get('audience', []))}"
    if any(token in text for token in ("طفل", "مراهق", "ADHD", "الأسرة")):
        return "الأسرة والطفل"
    if any(token in text for token in ("الرعاية", "مقدم", "حدود")):
        return "استدامة الرعاية"
    if any(token in text for token in ("ذهان", "ضيق", "اكتئاب", "سلامة")):
        return "الدعم النفسي والسلامة"
    if any(token in text for token in ("فقد", "حداد")):
        return "الفقد والتكيف"
    return "الدعم اليومي"


def index_page(data: dict) -> str:
    canonical = BASE + "care-guides/"
    guides = data["guides"]
    groups: dict[str, list[dict]] = {}
    for guide in guides:
        groups.setdefault(category(guide), []).append(guide)
    category_sections: list[str] = []
    category_links: list[str] = []
    for index, (name, items) in enumerate(groups.items(), 1):
        category_links.append(f'<a class="btn alt" href="#category-{index}">{esc(name)} ({len(items)})</a>')
        cards = "".join(f'<article class="card"><p class="kicker">{esc(name)}</p><h3>{esc(guide["title"])}</h3><p>{esc(guide["summary"])}</p><div class="tags">{"".join(f"<span class=\"tag\">{esc(a)}</span>" for a in guide.get("audience", [])[:3])}</div><p><a href="{BASE_PATH}care-guides/{esc(guide["slug"])}/">فتح الدليل الكامل ←</a></p></article>' for guide in items)
        category_sections.append(f'<section id="category-{index}" class="section"><p class="kicker">مسار موضوعي</p><h2>{esc(name)}</h2><div class="grid">{cards}</div></section>')
    sources = {source["url"] for guide in guides for source in guide.get("sources", [])}
    audiences = {item for guide in guides for item in guide.get("audience", [])}
    policy = data.get("editorial_policy", {})
    requirements = "".join(f"<li>{esc(item)}</li>" for item in policy.get("review_requirements", []))
    exclusions = "".join(f"<li>{esc(item)}</li>" for item in policy.get("not_for", []))
    description = "أدلة عربية عملية ومنهجية لدعم الأسرة والأصدقاء والمعلمين ومقدمي الرعاية، مع خطوات قابلة للتطبيق، علامات طلب المساعدة، مصادر أصلية، وخطط متابعة قابلة للطباعة."
    item_list = [{"@type": "ListItem", "position": i, "url": canonical + guide["slug"] + "/", "name": guide["title"]} for i, guide in enumerate(guides, 1)]
    schema = [{"@type": "CollectionPage", "@id": canonical + "#collection", "name": data["title"], "description": description, "url": canonical, "inLanguage": "ar", "publisher": {"@type": "Organization", "name": SITE_NAME, "url": BASE, "logo": {"@type": "ImageObject", "url": LOGO}}, "mainEntity": {"@type": "ItemList", "numberOfItems": len(guides), "itemListElement": item_list}, "hasPart": [{"@type": "Article", "name": guide["title"], "url": canonical + guide["slug"] + "/"} for guide in guides]}, {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE}, {"@type": "ListItem", "position": 2, "name": "أدلة التعامل", "item": canonical}]}, faq_schema(HUB_FAQS)]
    body = f'''<body>{header()}<main id="main-content" class="wrap"><nav class="crumbs" aria-label="مسار الصفحة"><ol><li><a href="{BASE_PATH}">الرئيسية</a></li><li aria-current="page">أدلة التعامل</li></ol></nav><header class="hero"><p class="eyebrow">مركز الأدلة العملية والدعم اليومي</p><h1>{esc(data['title'])}</h1><p class="lead">{esc(description)}</p><div class="actions"><a class="btn" href="#guide-library">استعرض الأدلة</a><a class="btn alt" href="#decision-matrix">حدد مستوى الاستجابة</a><a class="btn alt" href="#methodology">راجع المنهجية</a></div><div class="stats"><div class="stat"><strong>{len(guides)}</strong><span>أدلة أساسية منشورة</span></div><div class="stat"><strong>{len(groups)}</strong><span>مسارات موضوعية</span></div><div class="stat"><strong>{len(sources)}</strong><span>روابط مصادر أصلية</span></div><div class="stat"><strong>{len(audiences)}</strong><span>فئات مستفيدة</span></div></div></header><aside class="notice"><strong>قبل أن تبدأ:</strong> الأدلة للتثقيف وتنظيم الدعم وليست تشخيصًا أو وصفة علاجية. عند الخطر المباشر استخدم خدمات الطوارئ المحلية.</aside><section class="section"><p class="kicker">ابدأ من حاجتك</p><h2>ثلاثة أسئلة تقودك إلى الخطوة الصحيحة</h2><div class="grid"><article class="card"><h3>هل توجد مشكلة سلامة الآن؟</h3><p>عند الخطر المباشر أو فقدان شديد للاتصال بالواقع انتقل إلى مساعدة عاجلة.</p></article><article class="card"><h3>هل المشكلة مستمرة أو معطلة؟</h3><p>عند استمرارها أو أثرها في النوم والدراسة والعمل والعلاقات استعد لتقييم مهني.</p></article><article class="card"><h3>هل تحتاج خطة يومية؟</h3><p>اختر دليلًا واحدًا وخطوة قابلة للقياس وسجّل أثرها قبل إضافة تدخلات.</p></article></div></section><section id="decision-matrix" class="section"><p class="kicker">مصفوفة قرار</p><h2>متى نراقب، ومتى نحجز موعدًا، ومتى نتصرف فورًا؟</h2><table class="table"><thead><tr><th>المستوى</th><th>مؤشرات عامة</th><th>الإجراء</th></tr></thead><tbody><tr><td><strong>دعم ومراقبة</strong></td><td>تغير محدود وقصير دون خطر أو تعطّل واضح.</td><td>طبّق خطوة واحدة وراقب المدة والسياق والأثر.</td></tr><tr><td><strong>تقييم قريب</strong></td><td>استمرار الصعوبة أو تأثيرها في الوظائف اليومية.</td><td>احجز تقييمًا وجهّز ملاحظات موضوعية والأدوية والسياقات.</td></tr><tr><td><strong>استجابة عاجلة</strong></td><td>خطر مباشر أو خطة أذى أو ارتباك شديد أو عجز أساسي.</td><td>استخدم خدمات الطوارئ المحلية أو جهة صحية عاجلة.</td></tr></tbody></table></section><section id="guide-library" class="section"><p class="kicker">مكتبة الأدلة</p><h2>تصفح حسب المسار الموضوعي</h2><div class="actions">{''.join(category_links)}</div></section>{''.join(category_sections)}<section id="methodology" class="section"><p class="kicker">الحوكمة التحريرية</p><h2>كيف نبني ونراجع الأدلة؟</h2><div class="grid two"><article class="card"><h3>الغرض</h3><p>{esc(policy.get('purpose', 'تثقيف ودعم عملي غير تشخيصي.'))}</p><h3>متطلبات المراجعة</h3><ul>{requirements}</ul></article><article class="card"><h3>ما لا تقدمه الأدلة</h3><ul>{exclusions}</ul><h3>بوابة السلامة</h3><p>يُحجب أي دليل يحتاج مراجعة اختصاصية موثقة، ولا يُدرج في الفهرس أو خريطة الموقع.</p></article></div></section><section class="section"><h2>معايير الجودة</h2><div class="grid"><article class="card"><h3>لغة تحترم الإنسان</h3><p>لا وصم ولا لوم ولا اختزال للشخص في تشخيص.</p></article><article class="card"><h3>خطوات قابلة للتنفيذ</h3><p>إجراءات محددة يمكن تطبيقها ومراجعة أثرها.</p></article><article class="card"><h3>حدود مهنية واضحة</h3><p>فصل التثقيف عن التشخيص والعلاج والطوارئ.</p></article><article class="card"><h3>مصادر أصلية</h3><p>روابط مباشرة إلى جهات مؤسسية وإرشادات مهنية.</p></article><article class="card"><h3>مسار للتصعيد</h3><p>تمييز المراقبة عن التقييم القريب والاستجابة العاجلة.</p></article><article class="card"><h3>متابعة قابلة للطباعة</h3><p>توثيق السياق والاستجابة والنتيجة ومشاركتها مع المختص.</p></article></div></section>{faq_markup(HUB_FAQS, 'أسئلة شائعة عن أدلة التعامل')}<section class="section"><h2>أقسام مرتبطة</h2><div class="grid"><article class="card"><h3>الموسوعة النفسية</h3><p>لفهم الحالات والفروق الأساسية.</p><a href="{BASE_PATH}encyclopedia/">فتح الموسوعة ←</a></article><article class="card"><h3>مركز ذوي الاحتياجات الخاصة</h3><p>للتربية الدامجة والمشاركة والاستقلال.</p><a href="{BASE_PATH}special-needs/">فتح المركز ←</a></article><article class="card"><h3>المجلة والأبحاث</h3><p>لقراءات الأبحاث الحديثة والقيود المنهجية.</p><a href="{BASE_PATH}magazine/">فتح المجلة ←</a></article></div></section></main>{footer()}</body></html>'''
    search_terms = [intent for guide in guides for intent in guide.get("search_intent", [])] + list(groups)
    return head(data["title"], description, canonical, schema, search_terms, "website", TODAY) + body


def extension_urls() -> list[str]:
    path = SITE / "sitemap-care-guides.xml"
    if not path.is_file():
        return []
    root = ET.parse(path).getroot()
    urls: list[str] = []
    for node in root.findall("{*}url/{*}loc"):
        url = (node.text or "").strip()
        relative = url.removeprefix(BASE).strip("/")
        if url.startswith(BASE + "care-guides/") and url != BASE + "care-guides/" and (SITE / relative / "index.html").is_file():
            urls.append(url)
    return sorted(set(urls))


def update_sitemaps(guides: list[dict]) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    urls = list(dict.fromkeys([BASE + "care-guides/"] + [BASE + "care-guides/" + guide["slug"] + "/" for guide in guides] + extension_urls()))
    urlset = ET.Element("urlset", xmlns=namespace)
    for url in urls:
        node = ET.SubElement(urlset, "url")
        ET.SubElement(node, "loc").text = url
        ET.SubElement(node, "lastmod").text = TODAY
        ET.SubElement(node, "changefreq").text = "monthly"
        ET.SubElement(node, "priority").text = "0.90" if url == BASE + "care-guides/" else "0.80"
    ET.ElementTree(urlset).write(SITE / "sitemap-care-guides.xml", encoding="utf-8", xml_declaration=True)
    index = SITE / "sitemap.xml"
    tree = ET.parse(index)
    root = tree.getroot()
    target = BASE + "sitemap-care-guides.xml"
    if target not in {node.text for node in root.findall("{*}sitemap/{*}loc") if node.text}:
        sitemap = ET.SubElement(root, "sitemap")
        ET.SubElement(sitemap, "loc").text = target
    tree.write(index, encoding="utf-8", xml_declaration=True)
    return len(urls)


def validate_guide(guide: dict) -> None:
    if not guide.get("title") or not guide.get("slug") or not guide.get("summary"):
        raise SystemExit("Every care guide must have a title, slug and summary")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", guide["slug"]):
        raise SystemExit(f"Invalid care-guide slug: {guide['slug']}")
    if len(guide["summary"]) < 70 or len(guide.get("audience", [])) < 2 or len(guide.get("search_intent", [])) < 3:
        raise SystemExit(f"Guide {guide['slug']} lacks depth, audience or search intent")
    if len(guide.get("sources", [])) < 2:
        raise SystemExit(f"Guide {guide['slug']} must have at least two sources")
    for source in guide["sources"]:
        parsed = urlparse(source.get("url", ""))
        if parsed.scheme != "https" or not parsed.netloc:
            raise SystemExit(f"Guide {guide['slug']} contains a non-HTTPS source")


def validate_rendered(output: Path, guides: list[dict]) -> dict[str, object]:
    hub = (output / "index.html").read_text(encoding="utf-8")
    required_hub = ('id="decision-matrix"', 'id="guide-library"', 'id="methodology"', 'class="footer"', '"@type": "CollectionPage"', '"@type": "ItemList"', '<meta name="keywords"', '<meta name="googlebot"', "sitemap-care-guides.xml")
    if missing := [token for token in required_hub if token not in hub]:
        raise SystemExit(f"Institutional care-guide hub contract failed: {missing}")
    counts: list[int] = []
    for guide in guides:
        text = (output / guide["slug"] / "index.html").read_text(encoding="utf-8")
        required = ('class="crumbs"', 'id="action-plan"', 'id="worksheet"', "مصادر مؤسسية للمراجعة", '"@type": "Article"', '"@type": "BreadcrumbList"', '<meta property="og:image"', "خدمات الطوارئ المحلية")
        if missing := [token for token in required if token not in text]:
            raise SystemExit(f"Institutional guide contract failed for {guide['slug']}: {missing}")
        if text.count("<h1>") != 1:
            raise SystemExit(f"Guide {guide['slug']} must contain exactly one H1")
        counts.append(word_count(re.sub(r"<[^>]+>", " ", text)))
    return {"experience_version": 235, "hub_h1": hub.count("<h1>"), "hub_h2": hub.count("<h2"), "hub_cards": hub.count('class="card"'), "hub_structured_types": ["CollectionPage", "ItemList", "BreadcrumbList", "FAQPage"], "guide_count_validated": len(guides), "minimum_rendered_guide_words": min(counts) if counts else 0, "all_guides_have_printable_worksheet": True, "all_guides_have_visible_breadcrumbs": True, "all_guides_have_social_metadata": True, "all_guides_have_keyword_metadata": True, "robots_directives": "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"}


def main() -> None:
    if not SITE.exists():
        raise SystemExit(f"Missing site output: {SITE}")
    primary = json.loads(DATA_FILES[0].read_text(encoding="utf-8"))
    all_guides = list(primary.get("guides", []))
    for path in DATA_FILES[1:]:
        all_guides.extend(json.loads(path.read_text(encoding="utf-8")).get("guides", []))
    if len(all_guides) != 8:
        raise SystemExit(f"Expected 8 validated source guides, found {len(all_guides)}")
    if len({guide["slug"] for guide in all_guides}) != len(all_guides):
        raise SystemExit("Duplicate care-guide slugs")
    for guide in all_guides:
        validate_guide(guide)
    blocked = [guide for guide in all_guides if guide.get("review_status") in BLOCKED_REVIEW_STATUSES]
    guides = [guide for guide in all_guides if guide not in blocked]
    blocked_slugs = [guide["slug"] for guide in blocked]
    primary["guides"] = guides
    output = SITE / "care-guides"
    output.mkdir(parents=True, exist_ok=True)
    for guide in blocked:
        shutil.rmtree(output / guide["slug"], ignore_errors=True)
    (output / "index.html").write_text(index_page(primary), encoding="utf-8")
    for guide in guides:
        page = output / guide["slug"] / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(guide_page(guide), encoding="utf-8")
    sitemap_url_count = update_sitemaps(guides)
    published_guide_count = max(0, sitemap_url_count - 1)
    page_count = len(list(output.rglob("index.html")))
    if page_count != sitemap_url_count:
        raise SystemExit(f"Care-guide page/sitemap mismatch: pages={page_count}, sitemap_urls={sitemap_url_count}")
    sitemap_text = (SITE / "sitemap-care-guides.xml").read_text(encoding="utf-8")
    remaining = [slug for slug in blocked_slugs if BASE + "care-guides/" + slug + "/" in sitemap_text or (output / slug / "index.html").exists()]
    if remaining:
        raise SystemExit(f"Blocked specialist-review guides remain: {remaining}")
    experience = validate_rendered(output, guides)
    autism = next(guide for guide in all_guides if guide["slug"] == "autism-family-practical-guide")
    report = {"version": 194, "publication_gate_version": 194, "source_guides": len(all_guides), "guides": published_guide_count, "core_guides": len(all_guides), "published_core_guides": len(guides), "pages": page_count, "sitemap_urls": sitemap_url_count, "extension_guides_preserved": max(0, published_guide_count - len(guides)), "all_have_sources": True, "all_have_unique_titles": len({guide["title"] for guide in all_guides}) == len(all_guides), "blocked_review_statuses": sorted(BLOCKED_REVIEW_STATUSES), "blocked_review_guides": len(blocked), "blocked_review_slugs": blocked_slugs, "needs_specialist_review_published": False, "autism_published": "autism-family-practical-guide" not in blocked_slugs, "autism_guide_sections": sum(1 for key in SECTION_LABELS if autism.get(key)), "autism_guide_source_count": len(autism["sources"]), "autism_review_status": autism.get("review_status"), "autism_human_specialist_review_claimed": False}
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-v21.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (api / "care-guides-institutional-v235.json").write_text(json.dumps(experience, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"publication": report, "institutional_experience": experience}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
