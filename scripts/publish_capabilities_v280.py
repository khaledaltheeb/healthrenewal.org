#!/usr/bin/env python3
"""Publish the evidence-bounded capabilities library (v280).

The section does not treat illness, pain, crisis, or disability as a gift.
It turns possible strengths into person-specific, falsifiable hypotheses and
tests them with accessible tasks, safety limits, and shared decisions.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "v280" / "capabilities-100-ar.json"
CSS_PATH = ROOT / "assets" / "css" / "capabilities-v280.css"
JS_PATH = ROOT / "assets" / "js" / "capabilities-v280.js"

VERSION = 280
UPDATED = "2026-07-26"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_ORIGIN = "https://khaledaltheeb.github.io"
BASE_PATH = "/pterminology-site/"
SECTION = "capabilities"
SITEMAP_NAME = "sitemap-capabilities.xml"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
BRIDGE_START = "<!-- capabilities-v280:start -->"
BRIDGE_END = "<!-- capabilities-v280:end -->"


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def ul(items: Iterable[str], class_name: str = "") -> str:
    cls = f' class="{e(class_name)}"' if class_name else ""
    return f"<ul{cls}>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"


def source_map(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in data["sources"]}


def load_and_validate() -> dict[str, Any]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise ValueError("Capabilities source must declare Arabic version 280")
    if data.get("external_review_completed") is not False:
        raise ValueError("External review must remain false until independently documented")
    if "المراجعة السريرية" not in data.get("review_status", ""):
        raise ValueError("Review status must disclose the external clinical review boundary")

    conditions = data.get("conditions", [])
    if len(conditions) != 100:
        raise ValueError(f"Exactly 100 conditions are required, found {len(conditions)}")
    if [item.get("rank") for item in conditions] != list(range(1, 101)):
        raise ValueError("Condition ranks must be contiguous from 1 through 100")
    slugs = [item.get("slug", "") for item in conditions]
    if len(slugs) != len(set(slugs)):
        raise ValueError("Condition slugs must be unique")
    for slug in slugs:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"Unsafe condition slug: {slug}")

    categories = data.get("categories", {})
    routes = data.get("evidence_routes", {})
    required_condition_keys = {
        "rank",
        "slug",
        "title_ar",
        "title_en",
        "category",
        "evidence_route",
        "first_wave_guide",
    }
    for condition in conditions:
        missing = required_condition_keys - set(condition)
        if missing:
            raise ValueError(
                f"Condition {condition.get('rank')} missing: {sorted(missing)}"
            )
        if condition["category"] not in categories:
            raise ValueError(f"Unknown category: {condition['category']}")
        if condition["evidence_route"] not in routes:
            raise ValueError(f"Unknown evidence route: {condition['evidence_route']}")

    sources = data.get("sources", [])
    if len(sources) < 20:
        raise ValueError("At least 20 verified institutional or research sources are required")
    source_ids = [item.get("id") for item in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Source ids must be unique")
    for source in sources:
        if not str(source.get("url", "")).startswith("https://"):
            raise ValueError(f"Source must use HTTPS: {source.get('id')}")
        if source.get("status") != "current":
            raise ValueError(f"Only current sources may support v280: {source.get('id')}")

    guides = data.get("guides", [])
    if len(guides) != 5:
        raise ValueError(f"Exactly five complete first-wave guides are required, found {len(guides)}")
    guide_slugs = [item.get("slug") for item in guides]
    flagged = [
        item["slug"] for item in conditions if item.get("first_wave_guide") is True
    ]
    if guide_slugs != flagged:
        raise ValueError("Guide order must match the five first-wave registry entries")
    condition_slugs = set(slugs)
    required_guide_keys = {
        "slug",
        "title",
        "evidence_label",
        "evidence_summary",
        "do_not_assume",
        "health_first",
        "hypotheses",
        "adaptations",
        "twelve_week_plan",
        "source_ids",
    }
    for guide in guides:
        missing = required_guide_keys - set(guide)
        if missing:
            raise ValueError(f"Guide {guide.get('slug')} missing: {sorted(missing)}")
        if guide["slug"] not in condition_slugs:
            raise ValueError(f"Guide has no registry entry: {guide['slug']}")
        if len(guide["hypotheses"]) < 4:
            raise ValueError(f"Guide needs four testable hypotheses: {guide['slug']}")
        for hypothesis in guide["hypotheses"]:
            expected = {"name", "claim", "microtrial", "support", "measure", "stop_rule"}
            if set(hypothesis) != expected:
                raise ValueError(
                    f"Guide hypothesis contract is incomplete: {guide['slug']}"
                )
        unknown = set(guide["source_ids"]) - set(source_ids)
        if unknown:
            raise ValueError(f"Unknown guide sources in {guide['slug']}: {sorted(unknown)}")

    protocol = data.get("protocol", {})
    if len(protocol.get("stages", [])) != 9:
        raise ValueError("The universal protocol must have exactly nine stages")
    if [item.get("number") for item in protocol["stages"]] != list(range(1, 10)):
        raise ValueError("Protocol stages must be ordered from 1 through 9")
    if len(protocol.get("minimum_measures", [])) < 7:
        raise ValueError("The protocol needs a multidimensional minimum measurement set")
    if len(protocol.get("stop_rules", [])) < 5:
        raise ValueError("The protocol needs explicit stop rules")
    return data


def breadcrumbs(items: list[tuple[str, str | None]]) -> tuple[str, dict[str, Any]]:
    html_parts: list[str] = []
    schema_items: list[dict[str, Any]] = []
    for position, (label, path) in enumerate(items, start=1):
        if path:
            html_parts.append(f'<a href="{e(path)}">{e(label)}</a>')
        else:
            html_parts.append(f'<span aria-current="page">{e(label)}</span>')
        schema_items.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": label,
            **({"item": BASE_ORIGIN + path} if path else {}),
            }
        )
    return (
        '<nav class="cap-breadcrumb" aria-label="مسار الصفحة">'
        + '<span aria-hidden="true">←</span>'.join(html_parts)
        + "</nav>",
        {"@type": "BreadcrumbList", "itemListElement": schema_items},
    )


def page_shell(
    *,
    title: str,
    description: str,
    canonical_path: str,
    main: str,
    schema_nodes: list[dict[str, Any]],
    current: str = "",
) -> str:
    canonical = BASE + canonical_path.lstrip("/")
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Organization",
                "@id": BASE + "#organization",
                "name": BRAND,
                "url": BASE,
            },
            {
                "@type": "WebSite",
                "@id": BASE + "#website",
                "name": BRAND,
                "url": BASE,
                "inLanguage": "ar",
                "publisher": {"@id": BASE + "#organization"},
            },
            *schema_nodes,
        ],
    }
    nav_items = [
        ("الرئيسية", BASE_PATH),
        ("مركز ذوي الاحتياجات الخاصة", BASE_PATH + "special-needs/"),
        ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
        ("سجل الحالات المئة", BASE_PATH + SECTION + "/registry/"),
        ("البروتوكول العملي", BASE_PATH + SECTION + "/protocol/"),
        ("المنهجية", BASE_PATH + SECTION + "/methodology/"),
        ("الثقة", BASE_PATH + "trust/"),
    ]
    nav = "".join(
        f'<a{" aria-current=\"page\"" if label == current else ""} '
        f'href="{e(url)}">{e(label)}</a>'
        for label, url in nav_items
    )
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{e(title)} | {e(BRAND)}</title>
<meta name="description" content="{e(description)}">
<meta name="keywords" content="ذوو الاحتياجات الخاصة، نقاط القوة الفردية، التأهيل، المشاركة، ICF، تكييف البيئة، قرار مشترك">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{e(canonical)}">
<link rel="alternate" hreflang="ar" href="{e(canonical)}">
<link rel="alternate" hreflang="x-default" href="{e(canonical)}">
<link rel="icon" href="{BASE_PATH}assets/brand/logo-mark.svg">
<link rel="stylesheet" href="{BASE_PATH}assets/css/capabilities-v280.css">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_AR">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{BASE}assets/brand/social-card.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<meta name="twitter:image" content="{BASE}assets/brand/social-card.svg">
<script type="application/ld+json">{compact_json(schema)}</script>
<script defer src="{BASE_PATH}assets/js/capabilities-v280.js"></script>
</head>
<body class="cap-page">
<a class="cap-skip" href="#main">تجاوز إلى المحتوى الرئيسي</a>
<header class="cap-header"><div class="cap-wrap cap-header-inner">
<a class="cap-brand" href="{BASE_PATH}"><img src="{BASE_PATH}assets/brand/logo-mark.svg" alt=""><span>{e(BRAND)}<small>{e(SLOGAN)}</small></span></a>
<nav class="cap-nav" aria-label="التنقل الرئيسي">{nav}</nav>
</div></header>
<main id="main">{main}</main>
<footer class="cap-footer"><div class="cap-wrap">
<p><strong>{e(BRAND)}</strong> — {e(SLOGAN)}</p>
<p><a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}special-needs/">المركز الدامج</a> · <a href="{BASE_PATH}outside-the-box/">أفكار خارج الصندوق</a></p>
<p>محتوى تثقيفي وتخطيطي، لا يشخّص ولا يصف علاجًا فرديًا ولا يستبدل الرعاية المهنية أو خطة الطوارئ.</p>
</div></footer>
</body>
</html>
"""


def review_banner(data: dict[str, Any]) -> str:
    return (
        '<aside class="cap-review" aria-label="حالة المراجعة">'
        "<strong>حالة المراجعة:</strong> "
        + e(data["review_status"])
        + ". <span>لا توجد مصادقة أو مراجعة خارجية مستقلة مسجلة لهذا الإصدار.</span>"
        "</aside>"
    )


def render_hub(data: dict[str, Any]) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [("الرئيسية", BASE_PATH), ("لنرتقي بقدراتهم", None)]
    )
    category_counts = Counter(item["category"] for item in data["conditions"])
    route_counts = Counter(item["evidence_route"] for item in data["conditions"])
    guide_by_slug = {item["slug"]: item for item in data["guides"]}
    guide_cards = []
    condition_by_slug = {item["slug"]: item for item in data["conditions"]}
    for slug, guide in guide_by_slug.items():
        condition = condition_by_slug[slug]
        route = data["evidence_routes"][condition["evidence_route"]]["label"]
        guide_cards.append(
            f"""<article class="cap-card cap-guide-card">
<span class="cap-kicker">{e(route)}</span>
<h3>{e(guide["title"])}</h3>
<p>{e(guide["evidence_label"])}</p>
<a class="cap-text-link" href="{e(slug)}/">اقرأ الخريطة العملية <span aria-hidden="true">←</span></a>
</article>"""
        )
    category_cards = "".join(
        f'<article class="cap-stat"><strong>{category_counts[key]}</strong>'
        f"<span>{e(label)}</span></article>"
        for key, label in data["categories"].items()
    )
    route_cards = "".join(
        f'<article class="cap-route"><h3>{e(route["label"])}</h3>'
        f"<p>{e(route['meaning'])}</p><strong>{route_counts[key]} حالة</strong></article>"
        for key, route in data["evidence_routes"].items()
    )
    main = f"""
<section class="cap-hero"><div class="cap-wrap">
{crumbs}
<p class="cap-eyebrow">مشروع بحثي تطبيقي يحترم الاختلاف ولا يجمّل المعاناة</p>
<h1>{e(data["title"])}</h1>
<p class="cap-lead">{e(data["subtitle"])}</p>
<blockquote>{e(data["core_statement"])}</blockquote>
<div class="cap-actions">
<a class="cap-button" href="registry/">استعرض الحالات المئة</a>
<a class="cap-button cap-button-secondary" href="protocol/">استخدم بروتوكول الاكتشاف</a>
</div>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="start-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">الإصدار الأول</p><h2 id="start-title">ماذا نُشر فعلًا؟</h2></div>
<p>السجل يحدد نطاق البحث كله، بينما الأدلة الخمسة التالية مكتملة ببروتوكولات وقياسات ومصادر. لا تُقدّم بقية الحالات على أنها أدلة تفصيلية مكتملة.</p></div>
<div class="cap-stats">
<article class="cap-stat"><strong>100</strong><span>حالة في سجل بحثي منظم</span></article>
<article class="cap-stat"><strong>5</strong><span>خرائط عملية مفصلة في هذه الموجة</span></article>
<article class="cap-stat"><strong>9</strong><span>مراحل في البروتوكول المشترك</span></article>
<article class="cap-stat"><strong>{len(data["sources"])}</strong><span>مصدرًا مؤسسيًا أو بحثيًا موثقًا</span></article>
</div>
<div class="cap-grid cap-grid-guides">{''.join(guide_cards)}</div>
</section>
<section class="cap-section cap-soft" aria-labelledby="routes-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">حدود الادعاء</p><h2 id="routes-title">ستة مسارات للدليل، لا عبارة واحدة عن «الموهبة»</h2></div>
<p>كل حالة تسلك طريقًا مختلفًا: أحيانًا يوجد دليل ناشئ على نمط قوة سياقي، وأحيانًا لا يوجد إلا واجب كشف القدرة الفردية أو إزالة الحاجز، وأحيانًا تكون الأولوية للاستقرار.</p></div>
<div class="cap-grid cap-grid-routes">{route_cards}</div>
<p><a class="cap-text-link" href="methodology/">اقرأ كيف نمنع التعميم والمبالغة <span aria-hidden="true">←</span></a></p>
</section>
<section class="cap-section" aria-labelledby="coverage-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">تغطية متوازنة</p><h2 id="coverage-title">توزيع الحالات المئة</h2></div>
<p>{e(data["selection_method"]["not_a_ranking"])}</p></div>
<div class="cap-stats cap-stats-six">{category_cards}</div>
</section>
<section class="cap-section cap-callout" aria-labelledby="promise-title">
<div><p class="cap-eyebrow">الوعد الأخلاقي</p><h2 id="promise-title">لا نبحث عن قيمة الشخص في تشخيصه</h2>
<p>{e(data["scope_note"])}</p></div>
<a class="cap-button cap-button-secondary" href="methodology/">الميثاق العلمي والتحريري</a>
</section>
</div>
"""
    return page_shell(
        title=data["title"],
        description=data["subtitle"],
        canonical_path=SECTION + "/",
        main=main,
        current="لنرتقي بقدراتهم",
        schema_nodes=[
            {
                "@type": "CollectionPage",
                "@id": BASE + SECTION + "/#page",
                "url": BASE + SECTION + "/",
                "name": data["title"],
                "description": data["subtitle"],
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "isPartOf": {"@id": BASE + "#website"},
            },
            crumb_schema,
        ],
    )


def render_methodology(data: dict[str, Any]) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            ("المنهجية", None),
        ]
    )
    source_by_id = source_map(data)
    foundation_ids = [
        "who-icf-2001",
        "who-rehabilitation-2024",
        "un-crpd-article-26",
        "un-crpd-article-27",
        "nice-shared-decision-ng197",
        "kang-person-centered-goals-2022",
    ]
    sources = "".join(
        f'<li><a href="{e(source_by_id[key]["url"])}" rel="noopener">'
        f'{e(source_by_id[key]["publisher"])} — {e(source_by_id[key]["title"])}</a> '
        f'({e(source_by_id[key]["year"])})</li>'
        for key in foundation_ids
    )
    routes = "".join(
        f'<article class="cap-route" id="{e(key)}"><h3>{e(item["label"])}</h3>'
        f"<p>{e(item['meaning'])}</p></article>"
        for key, item in data["evidence_routes"].items()
    )
    main = f"""
<section class="cap-page-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">ميثاق الدليل واللغة</p>
<h1>كيف نبحث عن القدرة من دون صناعة أسطورة عن المرض؟</h1>
<p class="cap-lead">نبدأ من الشخص وأهدافه وأدائه، ونضع لكل ادعاء سقفًا يساوي قوة الدليل. قصة نجاح تلهم سؤالًا؛ لا تثبت قاعدة.</p>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="selection-title">
<h2 id="selection-title">{e(data["selection_method"]["title"])}</h2>
{ul(data["selection_method"]["criteria"], "cap-check-list")}
<p class="cap-note"><strong>تنبيه:</strong> {e(data["selection_method"]["not_a_ranking"])}</p>
</section>
<section class="cap-section cap-soft" aria-labelledby="route-title">
<h2 id="route-title">مسارات الدليل الستة</h2>
<p>يظهر المسار في سجل الحالات وفي رأس كل دليل مفصل، كي لا تُقرأ فرضية فردية كأنها حقيقة جماعية.</p>
<div class="cap-grid cap-grid-routes">{routes}</div>
</section>
<section class="cap-section" aria-labelledby="rules-title">
<h2 id="rules-title">قواعد التحرير واتخاذ القرار</h2>
<div class="cap-grid cap-grid-three">
<article class="cap-card"><h3>ما الذي نقبله؟</h3>{ul([
        "نتائج مراجعات منهجية وإرشادات رسمية وبحوث محكّمة مع بيان حدودها.",
        "خبرة الشخص المعاشة بوصفها دليلًا على تفضيله وتجربته، لا على جميع أفراد التشخيص.",
        "تجارب مهام صغيرة قابلة للتكرار والقياس والتوقف.",
        "تقنية مساندة أو تعديل بيئي يكشف القدرة من دون إلغاء حق الشخص."
    ])}</article>
<article class="cap-card"><h3>ما الذي نرفضه؟</h3>{ul([
        "القول إن كل حالة هبة أو إن كل شخص يملك موهبة مرتبطة بتشخيصه.",
        "تحويل الألم أو الذهان أو الهوس أو النوبات أو الحرمان من النوم إلى ميزة.",
        "اختيار مهنة من اسم الحالة أو قصة شخص ناجح.",
        "إخفاء الضرر أو العلاج المطلوب كي تبدو الرسالة إيجابية."
    ])}</article>
<article class="cap-card"><h3>ما الذي يجب توثيقه؟</h3>{ul([
        "صوت الشخص وموافقته وطريقة التواصل وإشارات التوقف.",
        "المهمة والسياق والتكييف وخط الأساس ومدة التجربة.",
        "الجودة والاستقلال والتعب والألم والرغبة والتعميم.",
        "ما لم ينجح وما تغيّر ولماذا اتُخذ قرار الاستمرار أو التوقف."
    ])}</article>
</div>
</section>
<section class="cap-section cap-soft" aria-labelledby="translation-title">
<h2 id="translation-title">من الدراسة إلى توصية عملية</h2>
<ol class="cap-process">
<li><strong>سؤال محدد:</strong> ما القدرة أو الحاجز الذي نريد فهمه؟</li>
<li><strong>أفضل دليل متاح:</strong> إرشاد أو مراجعة، ثم دراسة فردية عند الحاجة.</li>
<li><strong>فحص الانطباق:</strong> العمر، اللغة، شدة الاحتياج، السياق، وقيود الدراسة.</li>
<li><strong>فرضية فردية:</strong> صياغة يمكن أن تثبت أو تُرفض.</li>
<li><strong>تجربة آمنة:</strong> مهمة حقيقية وتكييف واحد أو أكثر وقياس متعدد الأبعاد.</li>
<li><strong>قرار مشترك:</strong> استمرار أو تعديل أو توقف وفق البيانات ورأي الشخص.</li>
</ol>
</section>
<section class="cap-section" aria-labelledby="foundation-title">
<h2 id="foundation-title">الأساس المرجعي للمنهج</h2>
<p>يعتمد الإطار على الأداء والمشاركة والبيئة، وعلى التأهيل المتمحور حول الشخص والقرار المشترك والحقوق. التفاصيل الخاصة بكل حالة تظهر في مصادر دليلها.</p>
<ol class="cap-sources">{sources}</ol>
</section>
</div>
"""
    return page_shell(
        title="المنهجية العلمية لمشروع لنرتقي بقدراتهم",
        description="ميثاق يمنع تعميم نقاط القوة، ويفصل بين الدليل والخبرة والفرضية الفردية، ويوثق حدود المراجعة.",
        canonical_path=SECTION + "/methodology/",
        main=main,
        current="المنهجية",
        schema_nodes=[
            {
                "@type": "WebPage",
                "@id": BASE + SECTION + "/methodology/#page",
                "url": BASE + SECTION + "/methodology/",
                "name": "المنهجية العلمية لمشروع لنرتقي بقدراتهم",
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "isPartOf": {"@id": BASE + "#website"},
            },
            crumb_schema,
        ],
    )


def render_protocol(data: dict[str, Any]) -> str:
    protocol = data["protocol"]
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            ("البروتوكول العملي", None),
        ]
    )
    stages = "".join(
        f"""<article class="cap-stage">
<span class="cap-stage-number" aria-hidden="true">{stage["number"]}</span>
<div><h3>المرحلة {stage["number"]}: {e(stage["title"])}</h3>
{ul(stage["actions"])}
<p class="cap-output"><strong>المخرج:</strong> {e(stage["output"])}</p></div>
</article>"""
        for stage in protocol["stages"]
    )
    worksheet_rows = "".join(
        f"<tr><th scope=\"row\">{number}. {e(stage['title'])}</th>"
        "<td></td><td></td><td></td></tr>"
        for number, stage in enumerate(protocol["stages"], start=1)
    )
    main = f"""
<section class="cap-page-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">أداة تخطيط غير تشخيصية</p>
<h1>{e(protocol["title"])}</h1>
<p class="cap-lead">مسار من الأمان وصوت الشخص إلى تجربة صغيرة وقرار قابل للمراجعة. لا يقيس «قيمة» الإنسان ولا يتنبأ بمهنته.</p>
<div class="cap-actions"><button class="cap-button cap-print-button" type="button" data-cap-print>طباعة البروتوكول</button>
<a class="cap-button cap-button-secondary" href="../registry/">اختيار حالة من السجل</a></div>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="principles-title">
<h2 id="principles-title">مبادئ لا يجوز تجاوزها</h2>
{ul(protocol["principles"], "cap-check-list")}
</section>
<section class="cap-section cap-soft" aria-labelledby="stages-title">
<h2 id="stages-title">المراحل التسع</h2>
<div class="cap-stages">{stages}</div>
</section>
<section class="cap-section" aria-labelledby="measure-title">
<div class="cap-grid cap-grid-two">
<article><h2 id="measure-title">الحد الأدنى للقياس</h2>{ul(protocol["minimum_measures"], "cap-measure-list")}</article>
<article class="cap-danger"><h2>قواعد التوقف</h2>{ul(protocol["stop_rules"])}</article>
</div>
</section>
<section class="cap-section cap-worksheet" aria-labelledby="worksheet-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">ورقة عمل قابلة للطباعة</p><h2 id="worksheet-title">سجل قرار واحد</h2></div>
<p>استخدم سطرًا واحدًا موجزًا لكل مرحلة. لا تسجل بيانات تعريفية أو صحية أكثر مما يلزم، واحفظ الورقة وفق سياسة الخصوصية في مؤسستك.</p></div>
<div class="cap-form-grid">
<label>اسم الهدف لا اسم التشخيص<input aria-label="اسم الهدف" type="text"></label>
<label>تاريخ البداية<input aria-label="تاريخ البداية" type="text"></label>
<label>طريقة موافقة الشخص أو رفضه<input aria-label="طريقة الموافقة أو الرفض" type="text"></label>
<label>موعد المراجعة<input aria-label="موعد المراجعة" type="text"></label>
</div>
<div class="cap-table-wrap"><table><thead><tr><th>المرحلة</th><th>ما عرفناه</th><th>ما سنجرّبه أو نعدّله</th><th>الدليل والقرار</th></tr></thead>
<tbody>{worksheet_rows}</tbody></table></div>
<div class="cap-grid cap-grid-two cap-signoff">
<label>رأي الشخص في الاستمرار أو التعديل أو التوقف<textarea aria-label="رأي الشخص"></textarea></label>
<label>قواعد التوقف الخاصة بهذه التجربة<textarea aria-label="قواعد التوقف الخاصة"></textarea></label>
</div>
</section>
</div>
"""
    return page_shell(
        title="بروتوكول اكتشاف وتنمية القدرة",
        description="بروتوكول عملي من تسع مراحل لاختبار القدرات الفردية بأمان وقياس الاستقلال والرضا والتعب والتعميم.",
        canonical_path=SECTION + "/protocol/",
        main=main,
        current="البروتوكول العملي",
        schema_nodes=[
            {
                "@type": "HowTo",
                "@id": BASE + SECTION + "/protocol/#howto",
                "url": BASE + SECTION + "/protocol/",
                "name": protocol["title"],
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "step": [
                    {
                        "@type": "HowToStep",
                        "position": stage["number"],
                        "name": stage["title"],
                        "text": " ".join(stage["actions"]),
                    }
                    for stage in protocol["stages"]
                ],
            },
            crumb_schema,
        ],
    )


def render_registry(data: dict[str, Any]) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            ("سجل الحالات المئة", None),
        ]
    )
    guide_slugs = {item["slug"] for item in data["guides"]}
    cards: list[str] = []
    for condition in data["conditions"]:
        route = data["evidence_routes"][condition["evidence_route"]]
        category = data["categories"][condition["category"]]
        link = (
            f'<a class="cap-text-link" href="../{e(condition["slug"])}/">'
            'الدليل التفصيلي المنشور <span aria-hidden="true">←</span></a>'
            if condition["slug"] in guide_slugs
            else '<span class="cap-registry-only">مدرج في سجل البحث والمنهج</span>'
        )
        cards.append(
            f"""<article class="cap-condition" data-cap-condition
 data-slug="{e(condition["slug"])}"
 data-category="{e(condition["category"])}"
 data-route="{e(condition["evidence_route"])}"
 data-search="{e(condition["title_ar"])} {e(condition["title_en"])}">
<div class="cap-condition-top"><span class="cap-rank">{condition["rank"]:02d}</span>
<span class="cap-route-badge">{e(route["label"])}</span></div>
<h2>{e(condition["title_ar"])}</h2>
<p lang="en" dir="ltr">{e(condition["title_en"])}</p>
<small>{e(category)}</small>{link}
</article>"""
        )
    category_options = "".join(
        f'<option value="{e(key)}">{e(label)}</option>'
        for key, label in data["categories"].items()
    )
    route_options = "".join(
        f'<option value="{e(key)}">{e(item["label"])}</option>'
        for key, item in data["evidence_routes"].items()
    )
    main = f"""
<section class="cap-page-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">نطاق بحث منظم لا ترتيب للقيمة</p>
<h1>سجل الحالات المئة</h1>
<p class="cap-lead">اختيرت الحالات لأنها قد تُخفي قدرة بسبب حاجز في التعلم أو التواصل أو الحركة أو الصحة أو المشاركة. وجود الحالة في السجل لا يعني أن لها فائدة أو نمط موهبة ثابتًا.</p>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="filter-title">
<h2 id="filter-title">ابحث وصفِّ السجل</h2>
<form class="cap-filters" data-cap-filters>
<label>بحث بالاسم العربي أو الإنجليزي
<input type="search" data-cap-search autocomplete="off" placeholder="مثال: التوحد أو cerebral palsy"></label>
<label>المجال<select data-cap-category><option value="">كل المجالات</option>{category_options}</select></label>
<label>مسار الدليل<select data-cap-route><option value="">كل مسارات الدليل</option>{route_options}</select></label>
<button type="reset" class="cap-reset" data-cap-reset>مسح المرشحات</button>
</form>
<p class="cap-result-status" role="status" aria-live="polite"><strong data-cap-count>100</strong> حالة ظاهرة من 100.</p>
<div class="cap-registry" data-cap-registry>{''.join(cards)}</div>
<p class="cap-empty" data-cap-empty hidden>لا توجد نتيجة مطابقة. جرّب كلمة أو مرشحًا آخر.</p>
</section>
</div>
"""
    return page_shell(
        title="سجل الحالات المئة — لنرتقي بقدراتهم",
        description="سجل بحثي قابل للبحث يضم مئة حالة موزعة بحسب المجال ومسار الدليل من دون تعميم موهبة أو اختزال الشخص.",
        canonical_path=SECTION + "/registry/",
        main=main,
        current="سجل الحالات المئة",
        schema_nodes=[
            {
                "@type": "CollectionPage",
                "@id": BASE + SECTION + "/registry/#page",
                "url": BASE + SECTION + "/registry/",
                "name": "سجل الحالات المئة",
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "mainEntity": {
                    "@type": "ItemList",
                    "numberOfItems": 100,
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": item["rank"],
                            "name": item["title_ar"],
                        }
                        for item in data["conditions"]
                    ],
                },
            },
            crumb_schema,
        ],
    )


def render_sources(data: dict[str, Any], ids: list[str]) -> str:
    sources = source_map(data)
    return "".join(
        f'<li id="source-{e(key)}"><a href="{e(sources[key]["url"])}" rel="noopener">'
        f'{e(sources[key]["publisher"])} — {e(sources[key]["title"])}</a> '
        f'({e(sources[key]["year"])}؛ تحقق {e(sources[key]["verified_at"])})</li>'
        for key in ids
    )


def render_guide(data: dict[str, Any], guide: dict[str, Any]) -> str:
    condition = next(
        item for item in data["conditions"] if item["slug"] == guide["slug"]
    )
    route = data["evidence_routes"][condition["evidence_route"]]
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("لنرتقي بقدراتهم", BASE_PATH + SECTION + "/"),
            (condition["title_ar"], None),
        ]
    )
    hypotheses = "".join(
        f"""<article class="cap-hypothesis">
<h3>{index}. {e(item["name"])}</h3>
<dl>
<div><dt>الفرضية المحدودة</dt><dd>{e(item["claim"])}</dd></div>
<div><dt>تجربة مهمة صغيرة</dt><dd>{e(item["microtrial"])}</dd></div>
<div><dt>الدعم أو التكييف</dt><dd>{e(item["support"])}</dd></div>
<div><dt>ما الذي نقيسه؟</dt><dd>{e(item["measure"])}</dd></div>
<div class="cap-stop"><dt>متى نتوقف أو نعيد الصياغة؟</dt><dd>{e(item["stop_rule"])}</dd></div>
</dl></article>"""
        for index, item in enumerate(guide["hypotheses"], start=1)
    )
    plan = "".join(
        f'<li><span>{index}</span><p>{e(item)}</p></li>'
        for index, item in enumerate(guide["twelve_week_plan"], start=1)
    )
    measure_items = data["protocol"]["minimum_measures"]
    stop_items = data["protocol"]["stop_rules"]
    source_html = render_sources(data, guide["source_ids"])
    main = f"""
<section class="cap-page-hero cap-guide-hero"><div class="cap-wrap">
{crumbs}<p class="cap-eyebrow">الدليل التفصيلي {condition["rank"]:02d} من سجل المئة</p>
<h1>{e(guide["title"])}</h1>
<p class="cap-lead">{e(guide["evidence_label"])}</p>
<div class="cap-evidence-chip"><strong>{e(route["label"])}</strong><span>{e(route["meaning"])}</span></div>
</div></section>
<div class="cap-wrap">
{review_banner(data)}
<section class="cap-section" aria-labelledby="evidence-title">
<h2 id="evidence-title">ماذا يقول الدليل، وماذا لا يقول؟</h2>
{ul(guide["evidence_summary"], "cap-evidence-list")}
</section>
<section class="cap-section cap-soft" aria-labelledby="assume-title">
<div class="cap-grid cap-grid-two">
<article><h2 id="assume-title">لا تفترض</h2>{ul(guide["do_not_assume"], "cap-cross-list")}</article>
<article class="cap-health"><h2>الصحة والأمان أولًا</h2>{ul(guide["health_first"])}</article>
</div>
</section>
<section class="cap-section" aria-labelledby="hypothesis-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">اختبار لا تصنيف</p><h2 id="hypothesis-title">فرضيات قدرة قابلة للدحض</h2></div>
<p>هذه ليست صفات لازمة للحالة. اختر فرضية واحدة فقط إذا وافق عليها الشخص وكانت ذات معنى له، ثم اختبرها في أكثر من يوم.</p></div>
<div class="cap-hypotheses">{hypotheses}</div>
</section>
<section class="cap-section cap-soft" aria-labelledby="adapt-title">
<div class="cap-grid cap-grid-two">
<article><h2 id="adapt-title">تكييفات تكشف القدرة</h2>{ul(guide["adaptations"], "cap-check-list")}</article>
<article><h2>قياس النجاح كاملًا</h2>{ul(measure_items, "cap-measure-list")}</article>
</div>
</section>
<section class="cap-section" aria-labelledby="plan-title">
<div class="cap-section-heading"><div><p class="cap-eyebrow">دورة أولى قابلة للتعديل</p><h2 id="plan-title">خطة 12 أسبوعًا</h2></div>
<p>الأسابيع إطار مراجعة لا وصفة علاج. يحدد الفريق المؤهل الجرعة والوسيلة، ويستطيع الشخص التوقف في أي وقت.</p></div>
<ol class="cap-timeline">{plan}</ol>
</section>
<section class="cap-section cap-danger" aria-labelledby="stop-title">
<h2 id="stop-title">قواعد توقف عامة</h2>{ul(stop_items)}
<p>تُضاف إليها قواعد خاصة بالحالة وبالشخص وخطة الطوارئ المعتمدة لدى فريقه.</p>
</section>
<section class="cap-section" aria-labelledby="sources-title">
<h2 id="sources-title">المصادر التي تسند هذا الدليل</h2>
<ol class="cap-sources">{source_html}</ol>
<p class="cap-note">تاريخ التحقق يعني مراجعة الرابط وبيانات المصدر، ولا يعني اعتماد المحتوى من الجهة الناشرة للمصدر.</p>
</section>
<nav class="cap-next" aria-label="خطوات تالية">
<a href="../protocol/">استخدم ورقة البروتوكول</a>
<a href="../registry/">ارجع إلى سجل الحالات المئة</a>
</nav>
</div>
"""
    return page_shell(
        title=guide["title"],
        description=guide["evidence_label"],
        canonical_path=SECTION + "/" + guide["slug"] + "/",
        main=main,
        schema_nodes=[
            {
                "@type": "Article",
                "@id": BASE + SECTION + "/" + guide["slug"] + "/#article",
                "url": BASE + SECTION + "/" + guide["slug"] + "/",
                "headline": guide["title"],
                "description": guide["evidence_label"],
                "inLanguage": "ar",
                "dateModified": UPDATED,
                "publisher": {"@id": BASE + "#organization"},
                "citation": [
                    source_map(data)[key]["url"] for key in guide["source_ids"]
                ],
            },
            crumb_schema,
        ],
    )


def write_page(site: Path, route: str, body: str) -> Path:
    target = site / SECTION / route / "index.html" if route else site / SECTION / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


def gateway_block(context: str) -> str:
    copy = {
        "home": (
            "لنرتقي بقدراتهم",
            "سجل بحثي من 100 حالة، وبروتوكول عملي، وخمسة أدلة أولى تكشف القدرة من دون تجميل المرض أو تعميم الموهبة.",
        ),
        "special-needs": (
            "من الاحتياج إلى فرصة قابلة للقياس",
            "اكتشف قسم «لنرتقي بقدراتهم»: صوت الشخص أولًا، تعديل الحواجز، وتجارب صغيرة تقيس الاستقلال والرضا والسلامة.",
        ),
        "outside-the-box": (
            "طبقة تكميلية لاختبار القدرات",
            "بعد التقييم الوظيفي، استخدم بروتوكول «لنرتقي بقدراتهم» لصياغة فرضيات محدودة واختبارها بدل تحويل التشخيص إلى مهنة.",
        ),
    }[context]
    return f"""{BRIDGE_START}
<style data-capabilities-v280-bridge>
.capabilities-v280-bridge{{margin:2rem auto;padding:1.4rem;border:1px solid #bfded7;border-radius:20px;background:#f5fbf8;color:#173f3a;box-shadow:0 8px 24px rgba(23,63,58,.08)}}.capabilities-v280-bridge h2{{margin:.15rem 0 .55rem;color:#154f49}}.capabilities-v280-bridge p{{max-width:72ch}}.capabilities-v280-bridge a{{display:inline-block;margin-top:.35rem;padding:.72rem 1rem;border-radius:999px;background:#0f766e;color:#fff;text-decoration:none;font-weight:800}}.capabilities-v280-bridge a:focus-visible{{outline:3px solid #d4a72c;outline-offset:3px}}
</style>
<section class="capabilities-v280-bridge" aria-labelledby="capabilities-v280-{e(context)}-title">
<p><strong>لنرتقي بقدراتهم</strong> · 100 حالة · 5 أدلة تفصيلية · بروتوكول من 9 مراحل</p>
<h2 id="capabilities-v280-{e(context)}-title">{e(copy[0])}</h2>
<p>{e(copy[1])}</p>
<a href="{BASE_PATH}{SECTION}/">ادخل إلى القسم</a>
</section>
{BRIDGE_END}"""


def patch_gateway(path: Path, context: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing gateway page: {path}")
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        re.escape(BRIDGE_START) + r".*?" + re.escape(BRIDGE_END),
        flags=re.DOTALL,
    )
    block = gateway_block(context)
    matches = pattern.findall(text)
    if matches:
        if len(matches) != 1:
            raise ValueError(f"Duplicate capability gateway markers: {path}")
        updated = pattern.sub(block, text)
        path.write_text(updated, encoding="utf-8")
        return
    if "</main>" in text:
        text = text.replace("</main>", block + "\n</main>", 1)
    elif "</body>" in text:
        text = text.replace("</body>", block + "\n</body>", 1)
    else:
        raise ValueError(f"Gateway lacks main/body closing tag: {path}")
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")


def write_sitemap(site: Path, paths: list[str]) -> None:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for index, path in enumerate(paths):
        item = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(item, f"{{{SITEMAP_NS}}}loc").text = BASE + path
        ET.SubElement(item, f"{{{SITEMAP_NS}}}lastmod").text = UPDATED
        ET.SubElement(item, f"{{{SITEMAP_NS}}}changefreq").text = (
            "monthly" if index < 4 else "yearly"
        )
        ET.SubElement(item, f"{{{SITEMAP_NS}}}priority").text = (
            "0.9" if index == 0 else "0.8"
        )
    ET.ElementTree(root).write(
        site / SITEMAP_NAME, encoding="utf-8", xml_declaration=True
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def register_root_sitemap(site: Path, paths: list[str]) -> None:
    sitemap_index = site / "sitemap.xml"
    if not sitemap_index.is_file():
        raise FileNotFoundError("Missing root sitemap.xml")
    tree = ET.parse(sitemap_index)
    root = tree.getroot()
    root_type = local_name(root.tag)
    if root_type == "sitemapindex":
        target = BASE + SITEMAP_NAME
        existing = {
            (node.text or "").strip()
            for node in root.findall("{*}sitemap/{*}loc")
            if node.text
        }
        if target not in existing:
            item = ET.SubElement(root, qualify(root, "sitemap"))
            ET.SubElement(item, qualify(root, "loc")).text = target
    elif root_type == "urlset":
        existing = {
            (node.text or "").strip()
            for node in root.findall("{*}url/{*}loc")
            if node.text
        }
        for path in paths:
            target = BASE + path
            if target in existing:
                continue
            item = ET.SubElement(root, qualify(root, "url"))
            ET.SubElement(item, qualify(root, "loc")).text = target
            existing.add(target)
    else:
        raise ValueError(f"Unsupported sitemap root: {root_type}")
    tree.write(sitemap_index, encoding="utf-8", xml_declaration=True)


def register_robots(site: Path) -> None:
    path = site / "robots.txt"
    if not path.is_file():
        raise FileNotFoundError("Missing robots.txt")
    line = f"Sitemap: {BASE}{SITEMAP_NAME}"
    lines = [item.rstrip() for item in path.read_text(encoding="utf-8").splitlines()]
    lines = [item for item in lines if item != line]
    lines.append(line)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    data = load_and_validate()
    if not site.is_dir():
        raise FileNotFoundError(f"Missing site output: {site}")
    for source in (CSS_PATH, JS_PATH):
        if not source.is_file():
            raise FileNotFoundError(f"Missing capability asset: {source}")

    write_page(site, "", render_hub(data))
    write_page(site, "methodology", render_methodology(data))
    write_page(site, "protocol", render_protocol(data))
    write_page(site, "registry", render_registry(data))
    for guide in data["guides"]:
        write_page(site, guide["slug"], render_guide(data, guide))

    asset_css = site / "assets" / "css"
    asset_js = site / "assets" / "js"
    asset_css.mkdir(parents=True, exist_ok=True)
    asset_js.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CSS_PATH, asset_css / CSS_PATH.name)
    shutil.copy2(JS_PATH, asset_js / JS_PATH.name)

    patch_gateway(site / "index.html", "home")
    patch_gateway(site / "special-needs" / "index.html", "special-needs")
    patch_gateway(site / "outside-the-box" / "index.html", "outside-the-box")

    paths = [
        SECTION + "/",
        SECTION + "/methodology/",
        SECTION + "/protocol/",
        SECTION + "/registry/",
        *[SECTION + "/" + item["slug"] + "/" for item in data["guides"]],
    ]
    write_sitemap(site, paths)
    register_root_sitemap(site, paths)
    register_robots(site)

    report = {
        "version": VERSION,
        "status": "passed",
        "updated_at": UPDATED,
        "condition_count": len(data["conditions"]),
        "detailed_guide_count": len(data["guides"]),
        "generated_page_count": len(paths),
        "sitemap_url_count": len(paths),
        "protocol_stage_count": len(data["protocol"]["stages"]),
        "source_count": len(data["sources"]),
        "external_clinical_review_completed": False,
        "diagnostic_automation": False,
        "condition_implies_strength": False,
        "stability_first_routes": sum(
            item["evidence_route"] == "stability-first"
            for item in data["conditions"]
        ),
        "review_status": data["review_status"],
        "conditions": data["conditions"],
        "guides": [
            {
                "slug": item["slug"],
                "title": item["title"],
                "source_ids": item["source_ids"],
            }
            for item in data["guides"]
        ],
        "sources": data["sources"],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "capabilities-v280.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    args = parser.parse_args()
    report = publish(args.site.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
