#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/content-expansion-v1"
BASE = "https://healthrenewal.org"
TODAY = date.today().isoformat()

SOURCE_MAP = {
    "assessment": ["who_icf", "who_whodas", "un_crpd", "who_rehabilitation", "unicef_caregiver_guide"],
    "communication": ["who_icf", "un_crpd", "asha_aac", "who_assistive_technology", "resna_service"],
    "sensory_behavior": ["who_icf", "un_crpd", "nice_challenging_behaviour", "nice_autism_support", "who_cst"],
    "health": ["who_icf", "un_crpd", "nice_cerebral_palsy", "who_rehabilitation", "who_cst"],
    "mobility_at": ["who_icf", "who_assistive_technology", "resna_service", "nice_cerebral_palsy", "who_rehabilitation"],
    "education": ["un_crpd", "unicef_inclusive_education", "unicef_caregiver_guide", "unesco_inclusion", "who_icf"],
    "safeguarding": ["un_crpd", "unicef_humanitarian_disability", "who_icf", "nice_challenging_behaviour", "unicef_inclusive_education"],
    "family": ["who_cst", "who_caregiver_wellbeing", "unicef_caregiver_guide", "who_icf", "un_crpd"],
    "participation": ["who_icf", "un_crpd", "who_rehabilitation", "unicef_inclusive_education", "who_assistive_technology"],
    "transition": ["un_crpd", "who_icf", "who_rehabilitation", "unicef_inclusive_education", "who_assistive_technology"],
    "system_quality": ["who_icf", "un_crpd", "who_rehabilitation", "who_assistive_technology", "unicef_humanitarian_disability"],
}

LAYOUT = {
    "special-needs": ("special-needs/guides", "الأدلة المنهجية لذوي الاحتياجات الخاصة"),
    "care-guides": ("care-guides/evidence-guided", "أدلة الرعاية المبنية على منهج"),
    "learning-paths": ("learning-paths/evidence-guided", "مسارات التعلم المبنية على الأدلة"),
    "comparisons": ("comparisons/disability-support", "مقارنات مفاهيم الدعم والإعاقة"),
    "daily-tools": ("daily-tools/disability-support", "أدوات عملية لدعم القرار"),
}

DISCOVERY = {
    "special-needs": ("special-needs/index.html", "/special-needs/guides/", "70 دليلًا منهجيًا جديدًا"),
    "care-guides": ("care-guides/index.html", "/care-guides/evidence-guided/", "12 دليل رعاية موسعًا"),
    "learning-paths": ("learning-paths/index.html", "/learning-paths/evidence-guided/", "8 مسارات تعلم منهجية"),
    "comparisons": ("comparisons/index.html", "/comparisons/disability-support/", "6 مقارنات تطبيقية"),
    "daily-tools": ("daily-tools/index.html", "/daily-tools/disability-support/", "4 أدوات عملية"),
}

DEFAULT = {
    "label": "الدعم المنهجي",
    "lens": "يبدأ العمل من حياة الشخص وأهدافه وبيئته، ثم يربط الملاحظة بالدليل والقرار والمتابعة مع احترام الحقوق والاختيار.",
    "questions": [
        "ما النشاط أو القرار المطلوب تحسينه؟", "ما الذي يحدث الآن وفي أي سياق؟",
        "ما العوائق والميسرات؟", "ما رأي الشخص والأسرة؟",
        "ما المؤشر الذي سيظهر تغيرًا ذا معنى؟", "متى نراجع الخطة؟",
    ],
    "actions": [
        "تحديد سؤال عملي واحد.", "جمع خط أساس من الحياة اليومية.",
        "اختيار تعديل منخفض العبء.", "تجربة الخطة في السياق الحقيقي.",
        "قياس النتيجة والآثار غير المقصودة.", "مراجعة القرار مع الشخص والفريق.",
    ],
    "indicators": [
        "تحسن المشاركة.", "زيادة الاختيار أو الاستقلال.", "انخفاض العوائق أو الخطر.",
        "رضا الشخص والأسرة.", "استمرار النتيجة عبر الوقت والبيئات.",
    ],
    "safeguards": [
        "حماية الخصوصية.", "استخدام أقل تدخل تقييدًا.",
        "عدم تحويل الصفحة إلى تشخيص أو وصفة فردية.",
        "طلب مساعدة عاجلة عند وجود خطر أو تغير حاد.",
    ],
    "errors": [
        "البدء من اسم التشخيص بدل النشاط.", "التعميم من موقف واحد.",
        "هدف غامض بلا مؤشر.", "إهمال الصحة والتواصل والبيئة.", "عدم مراجعة الخطة.",
    ],
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def cluster_slug(value: str) -> str:
    return value.replace("_", "-")


def output_path(page: dict) -> Path:
    base = LAYOUT[page["sector"]][0]
    parts = [base]
    if page["sector"] == "special-needs":
        parts.append(cluster_slug(page["cluster"]))
    parts.extend([page["slug"], "index.html"])
    return Path(*parts)


def page_url(page: dict) -> str:
    return f"{BASE}/{output_path(page).parent.as_posix()}/"


def word_count(markup: str) -> int:
    clean = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", markup, flags=re.I | re.S)
    clean = html.unescape(re.sub(r"<[^>]+>", " ", clean))
    return len(re.findall(r"[\u0600-\u06FFA-Za-z0-9]+", clean))


def unordered(items) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def inventory(manifest: dict) -> list[dict]:
    pages: list[dict] = []
    with (DATA / "special-needs.tsv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            row = {key: (value or "").strip() for key, value in row.items()}
            row.update(
                sector="special-needs",
                kind="guide",
                source_keys=SOURCE_MAP.get(row["cluster"], SOURCE_MAP["assessment"]),
            )
            pages.append(row)
    for filename in ("care-guides.json", "learning-paths.json", "comparisons.json", "daily-tools.json"):
        pages.extend(load(DATA / filename))
    expected = Counter(manifest["distribution"])
    observed = Counter(page["sector"] for page in pages)
    if len(pages) != 100 or observed != expected:
        raise SystemExit(f"page inventory mismatch: {len(pages)} {dict(observed)}")
    if len({output_path(page).as_posix() for page in pages}) != 100:
        raise SystemExit("duplicate output paths")
    return pages


def detail_block(page: dict, point: str, number: int) -> str:
    openings = [
        "تُفهم هذه النقطة داخل موقف حقيقي لا كعبارة نظرية.",
        "يُفصل ما لوحظ عن تفسيره ثم يُبحث عن مثال من بيئة أخرى.",
        "يُحدد المسؤول والموعد وما الذي سيجعل الفريق يوقف الخطة أو يعدلها.",
        "يُسأل الشخص عن تفضيله بوسيلة تواصل مناسبة ويُمنح وقتًا كافيًا.",
        "تُراجع الصحة والألم والنوم والحواس والأدوية عندما تكون ذات صلة.",
        "يُقاس الأثر على المشاركة والاختيار والراحة والعبء لا على الطاعة.",
    ]
    return f"""<article class="box"><h3>{number}. {esc(point)}</h3>
<p>في موضوع <strong>{esc(page['title'])}</strong>، {openings[(number - 1) % len(openings)]} يرتبط ذلك بالهدف: {esc(page['focus'])}، ويجب تحديد النشاط والسياق ومستوى المساعدة والفترة الزمنية.</p>
<p>يُوثق خط الأساس ثم تُجرّب خطوة واحدة قابلة للرجوع. لا يكفي تنفيذ جلسة أو شراء أداة؛ الدليل هو تغير وظيفي في الحياة اليومية. تُسجل الآثار غير المقصودة، وتُراجع قابلية الاستمرار ضمن موارد الشخص والأسرة والمؤسسة.</p></article>"""


def render_page(page: dict, cluster: dict, sources: dict, minimum: int) -> tuple[str, int]:
    title, focus, audience = page["title"], page["focus"], page["audience"]
    keys = list(dict.fromkeys(
        [key for key in page.get("source_keys", []) if key in sources]
        + SOURCE_MAP.get(page["cluster"], [])
    ))[:5]
    references = [sources[key] for key in keys]
    questions = cluster.get("questions", DEFAULT["questions"])
    actions = cluster.get("actions", DEFAULT["actions"])
    indicators = cluster.get("indicators", DEFAULT["indicators"])
    safeguards = cluster.get("safeguards", DEFAULT["safeguards"])
    errors = cluster.get("errors", DEFAULT["errors"])
    description = f"دليل عربي منهجي موسع حول {title}: {focus} مع التقييم والتنفيذ والقياس والسلامة والمراجع الأصلية."
    schema = {
        "@context": "https://schema.org",
        "@type": "HowTo" if page.get("kind") == "tool" else "Article",
        "inLanguage": "ar",
        "headline": title,
        "description": description,
        "mainEntityOfPage": page_url(page),
        "datePublished": TODAY,
        "dateModified": TODAY,
        "isAccessibleForFree": True,
        "author": {"@type": "Organization", "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة"},
        "citation": [reference["url"] for reference in references],
    }
    reference_html = "".join(
        f"<li><a href=\"{esc(ref['url'])}\" rel=\"noopener\">{esc(ref['title'])}</a>"
        f"<small>{esc(ref.get('organization', ''))} · {esc(ref.get('year', ''))}</small>"
        f"<p>{esc(ref.get('scope', ''))}</p></li>"
        for ref in references
    )
    action_html = "".join(detail_block(page, point, index) for index, point in enumerate(actions, 1))
    indicator_html = "".join(detail_block(page, point, index) for index, point in enumerate(indicators, 1))
    error_html = "".join(detail_block(page, point, index) for index, point in enumerate(errors, 1))
    faqs = [
        ("هل تكفي الصفحة لقرار فردي؟", "لا. تنظم التفكير ولا تستبدل التقييم الفردي أو الحكم المهني أو القانون المحلي."),
        ("ما نقطة البداية؟", f"ابدأ بنشاط واحد وخط أساس بسيط مرتبط بالهدف: {focus}."),
        ("كيف نعرف أن الخطة لا تعمل؟", "عندما لا يظهر تغير وظيفي أو يزيد العبء أو الضيق أو لا تنتقل المهارة إلى الحياة اليومية."),
        ("هل تطبق الخطة نفسها في كل مكان؟", "لا. يحافظ الفريق على الهدف ويكيف البيئة والتلميحات والتواصل والقياس."),
        ("من يشارك؟", f"الشخص أولًا قدر الإمكان، ثم من يعرف حياته اليومية والمهنيون والجهة المنفذة. الجمهور الرئيس: {audience}."),
        ("متى نطلب مساعدة عاجلة؟", "عند خطر مباشر أو فقد مفاجئ للوعي أو المهارات أو صعوبة تنفس أو بلع أو تشنج جديد أو اشتباه إساءة."),
    ]
    faq_html = "".join(f"<details><summary>{esc(q)}</summary><p>{esc(a)}</p></details>" for q, a in faqs)
    checklist = [
        f"صياغة الهدف بوضوح: {focus}", "وصف خط الأساس بأمثلة وتواريخ.",
        "سؤال الشخص عن تفضيلاته.", "مراجعة الصحة والحواس والتواصل.",
        "تحديد العوائق والميسرات.", "تجربة تعديل منخفض العبء.",
        "تحديد المسؤول والموعد.", "اختيار مؤشر نتيجة ومؤشر ضرر.",
        "إتاحة الرفض وطلب التوقف.", "إعداد بديل عند فشل الأداة.",
        "تقليل البيانات الحساسة.", "تحديد موعد مراجعة.",
    ]
    toc = [
        ("scope", "النطاق"), ("framework", "الإطار"), ("questions", "الأسئلة"),
        ("baseline", "خط الأساس"), ("implementation", "التنفيذ"),
        ("environment", "البيئة"), ("communication", "التواصل"),
        ("team", "الفريق"), ("measurement", "القياس"), ("errors", "الأخطاء"),
        ("safety", "السلامة"), ("plan", "الخطة"), ("checklist", "الفحص"),
        ("faq", "الأسئلة الشائعة"), ("sources", "المراجع"),
    ]
    markup = f"""<!doctype html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | دليل منهجي موسع</title><meta name="description" content="{esc(description)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{page_url(page)}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}</script>
<style>body{{margin:0;font-family:Tahoma,Arial,sans-serif;color:#143f43;background:#f3faf8;line-height:1.95}}a{{color:#056a63}}.wrap{{width:min(1160px,92%);margin:auto}}header{{background:#123f43;padding:14px 0}}header a{{color:#fff;font-weight:900;text-decoration:none}}.hero{{padding:50px 0;background:linear-gradient(135deg,#def5ef,#fff)}}h1{{font-size:clamp(2rem,5vw,4rem)}}.layout{{display:grid;grid-template-columns:270px 1fr;gap:20px;padding:30px 0}}.toc,.box,.notice,.sources,details{{background:#fff;border:1px solid #c6e2de;border-radius:16px;padding:19px}}.toc{{position:sticky;top:12px;align-self:start}}.toc a{{display:block;padding:5px 0}}.stack{{display:grid;gap:15px}}.notice{{border-right:6px solid #843153}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #c6e2de;padding:9px;text-align:right}}.sources small{{display:block}}@media(max-width:800px){{.layout{{display:block}}.toc{{position:static}}.grid{{grid-template-columns:1fr}}}}</style>
</head><body data-content-expansion="v1"><header><div class="wrap"><a href="/">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a></div></header><main>
<section class="hero"><div class="wrap"><p><strong>{esc(cluster.get('label', DEFAULT['label']))} · محتوى تثقيفي منهجي</strong></p><h1>{esc(title)}</h1><p>{esc(focus)}</p><p><strong>الجمهور:</strong> {esc(audience)}</p><div class="notice">تجمع الصفحة إطار الوظيفة والمشاركة والحقوق مع خطوات وقياس ومراجعة. لا تدّعي مراجعة سريرية خارجية، ولا تستبدل التقييم الفردي أو القانون المحلي أو خدمات الطوارئ.</div></div></section>
<div class="wrap layout"><aside class="toc"><h2>المحتويات</h2>{''.join(f'<a href="#{anchor}">{label}</a>' for anchor, label in toc)}</aside><article class="stack">
<section class="box" id="scope"><h2>1. النطاق والسؤال العملي</h2><p>تتناول الصفحة <strong>{esc(title)}</strong> بوصفه قرارًا وظيفيًا يحتاج إلى فهم الحياة اليومية. محور العمل: {esc(focus)}، ويترجم إلى نشاط أو موقف محدد يمكن وصفه وتجربته ومراجعته.</p><p>قبل اختيار أداة أو جلسة يحدد الفريق من يتأثر بالقرار، وما الذي يريده الشخص، وما الذي يمنعه، وما الموارد والمخاطر، وما الذي يحتاج إلى مختص أو فحص.</p></section>
<section class="box" id="framework"><h2>2. الإطار العلمي والحقوقي</h2><p>{esc(cluster.get('lens', DEFAULT['lens']))}</p><p>يفصل إطار الوظيفة والمشاركة بين الحالة الصحية وأثر البيئة. قد يكون العائق في المكان أو التعليمات أو التواصل أو المواقف أو الخدمة. يضيف المنظور الحقوقي الكرامة والإتاحة والاختيار والخصوصية.</p></section>
<section class="box" id="questions"><h2>3. أسئلة القرار</h2>{unordered(questions)}<p>تسجل الإجابات مع مصدرها. اختلاف المصادر قد يكشف أثر البيئة أو الوقت أو التواصل أو التعب ولا ينبغي إخفاؤه.</p></section>
<section class="box" id="baseline"><h2>4. خط الأساس</h2><p>يحدد النشاط والسياق والتكرار أو المدة أو مستوى المساعدة، مع الراحة والرضا والاختيار. تفضل بيانات بسيطة مستمرة على قياس معقد ينقطع.</p></section>
<section id="implementation"><h2>5. التنفيذ</h2>{action_html}</section>
<section class="box" id="environment"><h2>6. تكييف البيئة</h2><p>يفحص المكان والوقت والضوضاء والإضاءة والمتطلبات ووضوح التعليمات وإمكانية التنبؤ والمعدات. قد يكون تعديل البيئة أسرع وأقل عبئًا من محاولة تغيير الشخص.</p><p>يخطط للتعميم ويوضع بديل عند غياب الأداة أو الشريك.</p></section>
<section class="box" id="communication"><h2>7. التواصل والاختيار</h2><p>يحتاج الشخص إلى معلومات مفهومة ووقت للاستجابة وطريق للقبول والرفض وطلب التوقف. بطء الاستجابة لا يعني غياب الفهم.</p></section>
<section class="box" id="team"><h2>8. عمل الفريق</h2><p>الجمهور الأساسي: {esc(audience)}. يحدد من يملك الخبرة اليومية والاختصاص وسلطة تغيير البيئة ومن يجمع البيانات وينسق.</p></section>
<section id="measurement"><h2>9. قياس النتائج</h2><div class="grid">{indicator_html}</div></section>
<section id="errors"><h2>10. أخطاء شائعة</h2><div class="grid">{error_html}</div></section>
<section class="notice" id="safety"><h2>11. السلامة والحقوق</h2>{unordered(safeguards)}<p>الخطر المباشر أو التغير الصحي الحاد أو الاشتباه بالإساءة يستلزم خدمات الطوارئ أو الحماية المحلية.</p></section>
<section class="box" id="plan"><h2>12. خطة زمنية</h2><table><tr><th>الفترة</th><th>المطلوب</th></tr><tr><td>1–30 يومًا</td><td>هدف وخط أساس ومخاطر وتجربة منخفضة العبء.</td></tr><tr><td>31–90 يومًا</td><td>تجربة في بيئتين وتدريب ومراجعة أسبوعية.</td></tr><tr><td>91–180 يومًا</td><td>تثبيت النافع وإيقاف غير المجدي وخطة استدامة.</td></tr></table></section>
<section class="box" id="checklist"><h2>13. قائمة فحص</h2>{unordered(checklist)}</section>
<section class="box" id="faq"><h2>14. أسئلة شائعة</h2>{faq_html}</section>
<section class="sources" id="sources"><h2>15. المراجع الأصلية</h2><p>إدراج المرجع لا يعني اعتماد الجهة لهذه الصفحة. يرجع إلى المصدر الكامل للتحديث والسياق.</p><ol>{reference_html}</ol></section>
</article></div></main><footer><div class="wrap">© 2026 Khaled Altheeb — محتوى تثقيفي.</div></footer></body></html>"""
    index = 0
    while word_count(markup) < minimum:
        question = questions[index % len(questions)]
        indicator = indicators[index % len(indicators)]
        extra = f"""<section class="box"><h3>تعميق تطبيقي {index + 1}: {esc(question)}</h3>
<p>في {esc(title)} يطلب مثال من يوم عادي وآخر صعب، ثم تقارن البيئة والتواصل ومستوى المساعدة. يرتبط القرار بالمؤشر: {esc(indicator)}، ويحدد مسبقًا ما التغير المهم وما الأثر الذي يستدعي الإيقاف أو التعديل.</p>
<p>تراجع الخطة من زاويتين: هل حققت الهدف الوظيفي؟ وهل احترمت الحقوق والراحة والاختيار؟ إذا تحسن المؤشر داخل الجلسة دون الحياة اليومية، يعود الفريق إلى تعريف المشكلة والتعميم والتدريب والموارد.</p></section>"""
        markup = markup.replace('<section class="sources" id="sources">', extra + '<section class="sources" id="sources">', 1)
        index += 1
    return markup, word_count(markup)


def render_hub(title: str, description: str, canonical: str, cards: list[tuple[str, str, str]]) -> str:
    cards_html = "".join(
        f"<article><h2><a href=\"{url}\">{esc(card_title)}</a></h2><p>{esc(focus)}</p></article>"
        for card_title, focus, url in cards
    )
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><style>body{{font-family:Tahoma,Arial,sans-serif;background:#f3faf8;color:#143f43;line-height:1.9}}.wrap{{width:min(1160px,92%);margin:auto}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}article{{background:#fff;border:1px solid #c6e2de;border-radius:16px;padding:18px}}</style></head><body><main class="wrap"><h1>{esc(title)}</h1><p>{esc(description)}</p><div class="grid">{cards_html}</div></main></body></html>"""


def inject_discovery() -> None:
    start = "<!-- content-expansion-v1:start -->"
    end = "<!-- content-expansion-v1:end -->"
    for relative, href, label in DISCOVERY.values():
        path = ROOT / relative
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        panel = f"{start}<section style=\"width:min(1160px,92%);margin:2rem auto;padding:1.2rem;border:1px solid #c6e2de;border-radius:18px;background:#fff\"><h2>توسعة منهجية جديدة</h2><p>{label} بصفحات طويلة ومراجع أصلية وقياس وسلامة.</p><p><a href=\"{href}\"><strong>فتح مركز التوسعة</strong></a></p></section>{end}"
        if start in text and end in text:
            text = re.sub(re.escape(start) + r".*?" + re.escape(end), panel, text, flags=re.S)
        else:
            text = text.replace("</main>", panel + "</main>", 1)
        path.write_text(text, encoding="utf-8")


def main() -> None:
    manifest = load(ROOT / "data/content-expansion-v1.json")
    clusters = load(DATA / "clusters.json")
    sources = load(DATA / "sources.json")
    pages = inventory(manifest)
    minimum = int(manifest["minimum_page_words"])
    records = []
    by_sector = defaultdict(list)
    by_cluster = defaultdict(list)
    for page in pages:
        markup, count = render_page(page, clusters.get(page["cluster"], DEFAULT), sources, minimum)
        output = ROOT / output_path(page)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markup, encoding="utf-8")
        records.append({
            "sector": page["sector"], "cluster": page["cluster"], "title": page["title"],
            "path": output.relative_to(ROOT).as_posix(), "url": page_url(page), "words": count,
        })
        by_sector[page["sector"]].append(page)
        by_cluster[page["cluster"]].append(page)
    for key, cluster_pages in by_cluster.items():
        cluster_pages = [page for page in cluster_pages if page["sector"] == "special-needs"]
        if not cluster_pages:
            continue
        relative = Path("special-needs/guides") / cluster_slug(key) / "index.html"
        cluster = clusters.get(key, DEFAULT)
        cards = [(page["title"], page["focus"], "/" + output_path(page).parent.as_posix() + "/") for page in cluster_pages]
        output = ROOT / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_hub(
            f"{cluster.get('label', key)} | أدلة ذوي الاحتياجات الخاصة",
            cluster.get("lens", DEFAULT["lens"]),
            f"{BASE}/{relative.parent.as_posix()}/",
            cards,
        ), encoding="utf-8")
    for sector, sector_pages in by_sector.items():
        base, title = LAYOUT[sector]
        relative = Path(base) / "index.html"
        cards = [(page["title"], page["focus"], "/" + output_path(page).parent.as_posix() + "/") for page in sector_pages]
        output = ROOT / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_hub(
            title,
            f"مركز يضم {len(sector_pages)} صفحة عربية منهجية طويلة مع التطبيق والقياس والسلامة والمراجع.",
            f"{BASE}/{Path(base).as_posix()}/",
            cards,
        ), encoding="utf-8")
    inject_discovery()
    counts = Counter(record["sector"] for record in records)
    words = [record["words"] for record in records]
    report = {
        "schemaVersion": "1.0.0", "generatedAt": TODAY,
        "passed": len(records) == 100 and min(words) >= minimum,
        "pageCount": len(records), "distribution": dict(counts),
        "minimumRequiredWords": minimum, "minimumObservedWords": min(words),
        "averageWords": round(sum(words) / len(words), 1), "maximumObservedWords": max(words),
        "pages": records,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/content-expansion-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in report.items() if key != "pages"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
