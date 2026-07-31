#!/usr/bin/env python3
"""Publish the evidence-guided provider pathway library (v254).

The publisher intentionally separates:
* licensed/qualified-user assessment instruments (names and purposes only);
* an original, non-diagnostic monitoring record;
* educational protocol options that require individual professional judgment.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
INSTRUMENTS_PATH = ROOT / "content" / "v254" / "outside-the-box-instruments-ar.json"
CSS_PATH = ROOT / "assets" / "css" / "outside-the-box-v254.css"
JS_PATH = ROOT / "assets" / "js" / "outside-the-box-v254.js"

VERSION = 254
UPDATED = "2026-07-26"
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
SECTION = "outside-the-box"
SITEMAP_NAME = "sitemap-outside-the-box.xml"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
REVIEW_LABEL = "مراجعة منهجية داخلية؛ المراجعة السريرية الخارجية مطلوبة قبل ادعاء الاعتماد"

BRIDGE_START = "<!-- outside-the-box-v254:start -->"
BRIDGE_END = "<!-- outside-the-box-v254:end -->"
STYLE_MARKER = "<!-- outside-the-box-v254:style -->"


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def ul(items: Iterable[str], class_name: str = "") -> str:
    cls = f' class="{e(class_name)}"' if class_name else ""
    return f"<ul{cls}>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ul>"


def ordered(items: Iterable[str]) -> str:
    return "<ol>" + "".join(f"<li>{e(item)}</li>" for item in items) + "</ol>"


def dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def load_and_validate() -> tuple[dict[str, Any], dict[str, Any]]:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    instruments = json.loads(INSTRUMENTS_PATH.read_text(encoding="utf-8"))

    if data.get("version") != VERSION or instruments.get("version") != VERSION:
        raise ValueError("Outside-the-box source version must be 254")
    if data.get("language") != "ar" or instruments.get("language") != "ar":
        raise ValueError("Outside-the-box sources must declare Arabic")

    conditions = data.get("conditions", [])
    if len(conditions) != 100:
        raise ValueError(f"Exactly 100 conditions are required, found {len(conditions)}")
    ranks = [item.get("rank") for item in conditions]
    if ranks != list(range(1, 101)):
        raise ValueError("Condition ranks must be ordered and contiguous from 1 through 100")
    slugs = [item.get("slug", "") for item in conditions]
    if len(slugs) != len(set(slugs)):
        raise ValueError("Condition slugs must be unique")
    bad_slugs = [slug for slug in slugs if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)]
    if bad_slugs:
        raise ValueError(f"Unsafe condition slugs: {bad_slugs}")

    sources = data.get("sources", {})
    clusters = data.get("clusters", {})
    protocols = data.get("protocols", {})
    if len(sources) < 25 or len(clusters) < 10 or len(protocols) < 20:
        raise ValueError("Institutional source, cluster, or protocol coverage is incomplete")
    if set(clusters) != set(instruments.get("clusters", {})):
        raise ValueError("Every clinical cluster must have a matching assessment instrument registry")

    for key, source in sources.items():
        if not str(source.get("url", "")).startswith("https://"):
            raise ValueError(f"Source must use HTTPS: {key}")
    required_condition_keys = {
        "rank",
        "slug",
        "title_ar",
        "title_en",
        "cluster",
        "status",
        "prevalence_tier",
        "prevalence_note",
        "focus",
        "assessment_extras",
        "protocol_keys",
        "outcome_goal",
        "alternative",
        "source_keys",
        "reference_url",
    }
    for condition in conditions:
        missing = required_condition_keys - set(condition)
        if missing:
            raise ValueError(f"Condition {condition.get('rank')} is missing fields: {sorted(missing)}")
        if condition["cluster"] not in clusters:
            raise ValueError(f"Unknown cluster in condition {condition['rank']}")
        if condition["prevalence_tier"] not in "ABCDE":
            raise ValueError(f"Unknown prevalence tier in condition {condition['rank']}")
        if len(condition["focus"]) != 3 or len(condition["assessment_extras"]) != 3:
            raise ValueError(f"Condition {condition['rank']} needs three focus and assessment items")
        if len(condition["protocol_keys"]) != 3:
            raise ValueError(f"Condition {condition['rank']} needs three protocol options")
        if len(condition["source_keys"]) < 2:
            raise ValueError(f"Condition {condition['rank']} needs at least two direct sources")
        unknown_sources = [key for key in condition["source_keys"] if key not in sources]
        unknown_protocols = [key for key in condition["protocol_keys"] if key not in protocols]
        if unknown_sources or unknown_protocols:
            raise ValueError(
                f"Condition {condition['rank']} has unknown sources/protocols: "
                f"{unknown_sources + unknown_protocols}"
            )
        if not condition["reference_url"].startswith("https://"):
            raise ValueError(f"Condition reference must use HTTPS: {condition['rank']}")
    return data, instruments


def condition_source_keys(data: dict[str, Any], condition: dict[str, Any]) -> list[str]:
    cluster = data["clusters"][condition["cluster"]]
    keys: list[str] = [*condition["source_keys"], *cluster["source_keys"]]
    for protocol_key in condition["protocol_keys"]:
        keys.extend(data["protocols"][protocol_key]["source_keys"])
    return dedupe(keys)


def breadcrumbs(items: list[tuple[str, str | None]]) -> tuple[str, dict[str, Any]]:
    parts = []
    schema_items = []
    for position, (label, url) in enumerate(items, start=1):
        if url:
            parts.append(f'<a href="{e(url)}">{e(label)}</a>')
        else:
            parts.append(f'<span aria-current="page">{e(label)}</span>')
        schema_items.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": label,
                **({"item": BASE.rstrip("/") + url} if url else {}),
            }
        )
    return (
        '<nav class="otb-breadcrumb" aria-label="مسار الصفحة">'
        + '<span aria-hidden="true">←</span>'.join(parts)
        + "</nav>",
        {
            "@type": "BreadcrumbList",
            "itemListElement": schema_items,
        },
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
        ("أفكار خارج الصندوق", BASE_PATH + SECTION + "/"),
        ("منهجية القسم", BASE_PATH + SECTION + "/methodology/"),
        ("مصفوفة المتابعة", BASE_PATH + SECTION + "/monitoring-matrix/"),
        ("منصة مقدم الخدمة", BASE_PATH + "provider-assessment-demo/"),
        ("الثقة", BASE_PATH + "trust/"),
    ]
    nav_parts = []
    for label, url in nav_items:
        current_attr = ' aria-current="page"' if label == current else ""
        nav_parts.append(f'<a{current_attr} href="{e(url)}">{e(label)}</a>')
    nav = "".join(nav_parts)
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | {e(BRAND)}</title>
<meta name="description" content="{e(description)}">
<meta name="keywords" content="ذوو الاحتياجات الخاصة، مقدم الخدمة، تقييم وظيفي، ICF، متابعة الاستجابة، تدخل قائم على الدليل">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="googlebot" content="index,follow">
<meta name="bingbot" content="index,follow">
<link rel="canonical" href="{e(canonical)}">
<link rel="alternate" hreflang="ar" href="{e(canonical)}">
<link rel="alternate" hreflang="x-default" href="{e(canonical)}">
<link rel="icon" href="{BASE_PATH}assets/brand/logo-mark.svg">
<link rel="stylesheet" href="{BASE_PATH}assets/css/outside-the-box-v254.css">
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
<script defer src="{BASE_PATH}assets/js/outside-the-box-v254.js"></script>
</head>
<body class="otb-page">
<a class="otb-skip" href="#main">تجاوز إلى المحتوى الرئيسي</a>
<header class="otb-header"><div class="otb-wrap otb-header-inner">
<a class="otb-brand" href="{BASE_PATH}"><img src="{BASE_PATH}assets/brand/logo-mark.svg" alt=""><span>{e(BRAND)}<small>{e(SLOGAN)}</small></span></a>
<nav class="otb-nav" aria-label="التنقل الرئيسي">{nav}</nav>
</div></header>
<main id="main">{main}</main>
<footer class="otb-footer"><div class="otb-wrap">
<p><strong>{e(BRAND)}</strong> — {e(SLOGAN)}</p>
<p><a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}special-needs/">المركز الدامج</a> · <a href="{BASE_PATH}provider-assessment-demo/">منصة مقدم الخدمة</a></p>
<p>المحتوى للتخطيط والتثقيف المهني؛ لا يشخّص، ولا يغيّر دواءً أو خطة طبية، ولا يستبدل الحكم المهني الفردي أو أنظمة بلدك.</p>
</div></footer>
</body>
</html>
"""


def source_list(data: dict[str, Any], keys: Iterable[str]) -> str:
    cards = []
    for key in dedupe(keys):
        source = data["sources"][key]
        cards.append(
            '<li class="otb-source">'
            f'<a href="{e(source["url"])}" target="_blank" rel="noopener noreferrer">'
            f'<strong>{e(source["organization"])}</strong> — {e(source["title"])}</a>'
            f'<p>{e(source["use"])}</p></li>'
        )
    return '<ol class="otb-source-list">' + "".join(cards) + "</ol>"


def render_hub(data: dict[str, Any]) -> str:
    conditions = data["conditions"]
    tiers = data["ranking_method"]["tiers"]
    cluster_options = "".join(
        f'<option value="{e(key)}">{e(value["title"])}</option>'
        for key, value in data["clusters"].items()
    )
    tier_legend = "".join(
        f'<li><strong>{e(key)}</strong><span>{e(label)}</span></li>' for key, label in tiers.items()
    )
    cards = []
    for condition in conditions:
        cluster = data["clusters"][condition["cluster"]]
        searchable = " ".join(
            [
                condition["title_ar"],
                condition["title_en"],
                cluster["title"],
                *condition["focus"],
            ]
        )
        cards.append(
            f"""<article class="otb-condition-card" data-condition-card
 data-cluster="{e(condition["cluster"])}" data-tier="{e(condition["prevalence_tier"])}"
 data-search="{e(searchable.casefold())}">
<div class="otb-rank"><span>ترتيب تخطيطي</span><strong>{condition["rank"]}</strong></div>
<div><p class="otb-kicker">الفئة {e(condition["prevalence_tier"])} · {e(cluster["title"])}</p>
<h3><a href="{e(condition["slug"])}/">{e(condition["title_ar"])}</a></h3>
<p class="otb-en" lang="en" dir="ltr">{e(condition["title_en"])}</p>
<p>{e(condition["prevalence_note"])}</p>
<div class="otb-tags">{"".join(f"<span>{e(item)}</span>" for item in condition["focus"])}</div>
<a class="otb-text-link" href="{e(condition["slug"])}/">فتح المسار الكامل ←</a></div>
</article>"""
        )
    crumbs, crumb_schema = breadcrumbs(
        [("الرئيسية", BASE_PATH), ("أفكار خارج الصندوق", None)]
    )
    description = (
        "مكتبة مؤسسية لمقدم الخدمة تضم 100 مسار للحالات الأكثر حضورًا ثم الأندر، "
        "من تحديد الحاجة إلى التقييم والبروتوكول والمتابعة وإعادة القرار."
    )
    main = f"""
<section class="otb-hero"><div class="otb-wrap">
{crumbs}
<div class="otb-hero-grid"><div>
<p class="otb-eyebrow">مختبر قرار لمقدم الخدمة · الإصدار 254</p>
<h1>أفكار خارج الصندوق</h1>
<p class="otb-lead">مئة مسار مترابط ينقل مقدم الخدمة من <strong>تحديد الحالة والاحتياج</strong> إلى اختبار الفرضيات، وبناء خط أساس، واختيار بروتوكول قابل للقياس، ثم اتخاذ قرار استمرار أو تعديل أو إحالة. الفكرة ليست وصفة موحدة؛ بل دورة قرار تحترم الشخص والسياق والدليل.</p>
<div class="otb-actions"><a class="otb-button" href="#conditions">اختر الحالة</a><a class="otb-button secondary" href="methodology/">اقرأ المنهجية العلمية</a><a class="otb-button secondary" href="monitoring-matrix/">افتح مصفوفة المتابعة</a></div>
</div><aside class="otb-panel">
<h2>العقد العلمي المختصر</h2>
<ul class="otb-checks"><li>ICF: الوظيفة والمشاركة والبيئة، لا الملصق وحده.</li><li>ثلاث نقاط خط أساس على الأقل قبل نسبة التغير للتدخل.</li><li>أداة رسمية مرخصة ومستخدم مؤهل عند الحاجة.</li><li>تدخل واحد أو حزمة محددة مع جرعة ومؤشر وقاعدة توقف.</li><li>النتائج المتوقعة نقاط قرار وليست وعودًا.</li></ul>
<p class="otb-review"><strong>حالة المراجعة:</strong> {e(REVIEW_LABEL)}.</p>
</aside></div>
<div class="otb-metrics" aria-label="ملخص القسم"><div><strong>100</strong><span>حالة ومسار</span></div><div><strong>{len(data["clusters"])}</strong><span>عائلة احتياج</span></div><div><strong>{len(data["protocols"])}</strong><span>بروتوكول خيار</span></div><div><strong>{len(data["sources"])}</strong><span>مصدرًا مؤسسيًا</span></div></div>
</div></section>
<section class="otb-section"><div class="otb-wrap">
<p class="otb-eyebrow">كيف يعمل القسم؟</p><h2>سبع بوابات، وقرار موثق عند كل بوابة</h2>
<div class="otb-seven">
<article><strong>1</strong><h3>تحديد الحالة</h3><p>فرضية عمل، نقاط قوة، سياق، وما لا يزال مجهولًا.</p></article>
<article><strong>2</strong><h3>اختبار مناسب</h3><p>فرز، أداة رسمية، ملاحظة وظيفية، وفحوص تفريقية.</p></article>
<article><strong>3</strong><h3>تقييم متكامل</h3><p>تثليث الأدلة بدل تفسير درجة واحدة.</p></article>
<article><strong>4</strong><h3>فكرة وبروتوكول</h3><p>خطوات وجرعة ومقياس وقاعدة إيقاف.</p></article>
<article><strong>5</strong><h3>متوقع مسؤول</h3><p>اتجاه ونقطة قرار دون ضمان مقدار التحسن.</p></article>
<article><strong>6</strong><h3>مراقبة زمنية</h3><p>الأسبوع 0 و2 و6 و12 و24.</p></article>
<article><strong>7</strong><h3>إعادة تقييم</h3><p>وصلنا؟ ما العائق؟ وما البديل؟</p></article>
</div></div></section>
<section class="otb-section otb-soft"><div class="otb-wrap">
<div class="otb-split"><div><p class="otb-eyebrow">ترتيب مسؤول</p><h2>لماذا هو «تخطيطي» لا جدول انتشار قطعي؟</h2>
<p>{e(data["scope_note"])}</p>{ul(data["ranking_method"]["rules"], "otb-checks")}</div>
<aside class="otb-panel"><h3>فئات الانتشار</h3><ul class="otb-tier-legend">{tier_legend}</ul></aside></div>
</div></section>
<section class="otb-section" id="conditions"><div class="otb-wrap">
<p class="otb-eyebrow">الدليل الكامل</p><h2>تصفح 100 حالة من الأكثر حضورًا إلى الأندر</h2>
<p>البحث والتصفية يعملان داخل جهازك. الروابط المئة موجودة في HTML حتى تبقى قابلة للوصول دون JavaScript.</p>
<form class="otb-filters" data-condition-filters role="search">
<label>ابحث باسم الحالة أو المجال<input type="search" data-condition-search placeholder="مثال: اللغة، السمع، التوحد"></label>
<label>عائلة الاحتياج<select data-condition-cluster><option value="">كل العائلات</option>{cluster_options}</select></label>
<label>فئة الانتشار<select data-condition-tier><option value="">كل الفئات</option>{"".join(f'<option value="{t}">{t}</option>' for t in tiers)}</select></label>
<button type="reset" class="otb-button secondary">إعادة الضبط</button>
</form>
<p class="otb-results" aria-live="polite" data-condition-results>100 حالة ظاهرة</p>
<div class="otb-condition-grid" data-condition-grid>{"".join(cards)}</div>
<div class="otb-empty" data-condition-empty hidden>لا توجد نتيجة مطابقة. جرّب كلمة أوسع أو أزل أحد المرشحات.</div>
</div></section>
<section class="otb-section otb-soft"><div class="otb-wrap">
<h2>مصادر الإطار العام</h2>
<p>تظهر المصادر الخاصة بكل حالة داخل مسارها. هذه المراجع تشرح الهيكل الذي يجمع الوظيفة، والهدف الفردي، ودراسة الحالة الواحدة، والتعليم الدامج.</p>
{source_list(data, ["who-icf", "who-rehab", "wwc-scd", "scribe", "gas", "dec", "udl", "unicef-inclusive", "nice-complex"])}
</div></section>"""
    item_list = {
        "@type": "ItemList",
        "name": "مسارات أفكار خارج الصندوق — 100 حالة",
        "numberOfItems": 100,
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": condition["rank"],
                "name": condition["title_ar"],
                "url": BASE + SECTION + "/" + condition["slug"] + "/",
            }
            for condition in conditions
        ],
    }
    page_schema = {
        "@type": "CollectionPage",
        "@id": BASE + SECTION + "/#page",
        "url": BASE + SECTION + "/",
        "name": "أفكار خارج الصندوق",
        "description": description,
        "inLanguage": "ar",
        "isPartOf": {"@id": BASE + "#website"},
        "dateModified": UPDATED,
        "publisher": {"@id": BASE + "#organization"},
    }
    return page_shell(
        title="أفكار خارج الصندوق — 100 مسار لمقدم الخدمة",
        description=description,
        canonical_path=SECTION + "/",
        main=main,
        schema_nodes=[page_schema, item_list, crumb_schema],
        current="أفكار خارج الصندوق",
    )


def render_instrument_registry(
    instruments: dict[str, Any], cluster_key: str | None = None
) -> str:
    rows = list(instruments["universal"])
    if cluster_key:
        rows.extend(instruments["clusters"][cluster_key])
    body = "".join(
        "<tr>"
        f'<th scope="row">{e(item["name"])}<small>{e(item["owner"])}</small></th>'
        f'<td>{e(item["use"])}</td><td>{e(item["access"])}</td>'
        f'<td>{e(item["caution"])}</td></tr>'
        for item in rows
    )
    return f"""<div class="otb-table-wrap"><table class="otb-table">
<caption>أسماء وأغراض فقط — استخدم النسخة الأصلية وشروط صاحب الأداة</caption>
<thead><tr><th>الأداة/الإجراء</th><th>الغرض</th><th>الوصول والمؤهل</th><th>حد التفسير</th></tr></thead>
<tbody>{body}</tbody></table></div>"""


def render_methodology(data: dict[str, Any], instruments: dict[str, Any]) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("أفكار خارج الصندوق", BASE_PATH + SECTION + "/"),
            ("المنهجية", None),
        ]
    )
    cluster_rows = "".join(
        f'<tr><th scope="row">{e(cluster["title"])}</th>'
        f'<td>{e("، ".join(cluster["functional_domains"]))}</td>'
        f'<td>{e("، ".join(cluster["team"]))}</td>'
        f'<td><a href="#registry-{e(key)}">أمثلة الأدوات</a></td></tr>'
        for key, cluster in data["clusters"].items()
    )
    registries = "".join(
        f'<section class="otb-subsection" id="registry-{e(key)}"><h3>{e(cluster["title"])}</h3>'
        f'{render_instrument_registry(instruments, key)}</section>'
        for key, cluster in data["clusters"].items()
    )
    description = (
        "المنهجية العلمية والحوكمة وحقوق الاختبارات ومراقبة الاستجابة التي تحكم "
        "مئة مسار في قسم أفكار خارج الصندوق."
    )
    main = f"""
<section class="otb-page-hero"><div class="otb-wrap">{crumbs}
<p class="otb-eyebrow">العقد العلمي والحوكمة</p><h1>كيف بُني القسم؟</h1>
<p class="otb-lead">منهج قرار متعدد المصادر يربط ICF والتقييم الشامل ودراسة الحالة الواحدة بالأهداف الفردية. لا تُسوّى جودة الدليل بين الحالات، ولا تتحول أداة فرز أو سجل متابعة إلى تشخيص.</p>
<div class="otb-notice"><strong>حالة النشر:</strong> {e(data["review_status"])}.</div>
</div></section>
<section class="otb-section"><div class="otb-wrap">
<h2>1. سؤال الحالة يسبق اسم الاختبار</h2>
<div class="otb-cards-3">
<article class="otb-card"><h3>ما القرار؟</h3><p>تشخيص تفريقي، أهلية خدمة، تخطيط تدخل، مراقبة تقدم، أو فحص سلامة؟ تختلف الأداة باختلاف القرار.</p></article>
<article class="otb-card"><h3>لمن وفي أي سياق؟</h3><p>العمر، اللغة، الثقافة، طريقة التواصل، الحواس، الحركة، التعب، والبيئة قد تغيّر صلاحية الإجراء وتفسيره.</p></article>
<article class="otb-card"><h3>ما الحد الأدنى من الأدلة؟</h3><p>مقابلة وملاحظة وقياس معياري أو وظيفي مناسب، مع مصدرين أو سياقين عند إمكان ذلك، ثم تفسير فريق مؤهل.</p></article>
</div>
<h2>2. تسلسل التقييم المؤسسي</h2>
<ol class="otb-process">
<li><strong>الرضا والموافقة:</strong> اشرح الغرض والحقوق والخصوصية وحق التوقف بطريقة يمكن للشخص الوصول إليها.</li>
<li><strong>الفرز والسلامة:</strong> افحص الألم، وفقد المهارات، والسمع والبصر، والنوم، والدواء، والخطر قبل تفسير السلوك.</li>
<li><strong>تحديد الفرضيات:</strong> اكتب ما يرجح وما يعارض وما لا يزال مجهولًا، ولا تثبت تشخيصًا من الانطباع.</li>
<li><strong>الأداة الرسمية:</strong> اختر نسخة مرخصة ذات دليل ملاءمة للعمر واللغة والغرض، وبيد مستخدم مؤهل.</li>
<li><strong>التقييم الوظيفي:</strong> راقب نشاطًا ذا معنى في أكثر من سياق، وسجل الحواجز والتيسيرات والمساعدة.</li>
<li><strong>تثليث الأدلة:</strong> حل التناقضات بين الاختبار والمقابلة والملاحظة بدل متوسطتها آليًا.</li>
<li><strong>قرار مشترك:</strong> وثق النتيجة وحدودها والخطة وموعد المراجعة ومسؤول كل إجراء.</li>
</ol>
<h2>3. عائلات الاحتياج والفريق</h2>
<div class="otb-table-wrap"><table class="otb-table"><caption>خريطة التقييم بحسب العائلة الوظيفية</caption>
<thead><tr><th>العائلة</th><th>مجالات الوظيفة</th><th>الفريق المحتمل</th><th>السجل</th></tr></thead>
<tbody>{cluster_rows}</tbody></table></div>
</div></section>
<section class="otb-section otb-soft"><div class="otb-wrap">
<h2>4. كيف نختبر «فكرة خارج الصندوق» دون مبالغة؟</h2>
<div class="otb-evidence-grid">
<article class="otb-panel"><h3>خط الأساس</h3><p>ثلاث نقاط مستقلة على الأقل تحت إجراء ثابت، ويفضل سياقان عندما يكون التعميم هدفًا. سجّل الفرص والنجاح المستقل والتلميح والوقت والعبء.</p></article>
<article class="otb-panel"><h3>المتغير المحدد</h3><p>غيّر عنصرًا واحدًا أو حزمة معلنة، وحدد الجرعة والمنفذ ودرجة الالتزام. لا تنسب الأثر لتدخل غامض متعدد التغييرات.</p></article>
<article class="otb-panel"><h3>القياس المتكرر</h3><p>استعمل مسبارًا متكافئًا ووتيرة تناسب تغير المهارة. اقرأ المستوى والاتجاه والتباين وفورية الأثر والتعميم.</p></article>
<article class="otb-panel"><h3>قاعدة القرار</h3><p>استمر عند فائدة ذات معنى وقبول جيد وسلامة. عدّل عند تنفيذ ضعيف أو اتجاه مسطح. أوقف وأحل عند ضرر أو تدهور أو إشارة طبية.</p></article>
</div>
<p class="otb-callout">هذا تطبيق محافظ لمبادئ دراسات الحالة الواحدة وSCRIBE. لا يدّعي أن تجربة خدمة واحدة تعادل تجربة عشوائية، ولا يسمح بتعميم نتيجة شخص على الجميع.</p>
<h2>5. مستويات الهدف الفردي</h2>
<div class="otb-table-wrap"><table class="otb-table"><caption>سلم هدف فردي يُملأ قبل التدخل</caption>
<thead><tr><th>المستوى</th><th>الوصف</th><th>قاعدة الصياغة</th></tr></thead><tbody>
<tr><th scope="row">−2</th><td>خط الأساس أو تدهور محدد مسبقًا</td><td>سلوك قابل للملاحظة، سياق، مساعدة، وتكرار.</td></tr>
<tr><th scope="row">−1</th><td>تحسن أقل من المستوى المستهدف</td><td>فرق واحد واضح عن −2.</td></tr>
<tr><th scope="row">0</th><td>المستوى المستهدف المتفق عليه</td><td>واقعي وذو معنى، وليس وعدًا زمنيًا.</td></tr>
<tr><th scope="row">+1</th><td>أكثر من المتوقع</td><td>فرق واحد واضح عن 0.</td></tr>
<tr><th scope="row">+2</th><td>أكثر بكثير من المتوقع</td><td>لا يصاغ كسقف لإمكانات الشخص.</td></tr>
</tbody></table></div>
<p>تُستخدم المستويات لوصف بلوغ هدف فردي، مع الاعتراف بأن جودة القياس تعتمد على صياغة الفريق. لا تسمى «مقياسًا عالميًا مقننًا» ولا تجمع آليًا لإصدار تشخيص.</p>
</div></section>
<section class="otb-section"><div class="otb-wrap">
<h2>6. حقوق الاختبارات وحدود النقل إلى العربية</h2>
<div class="otb-notice warning"><strong>قاعدة ملزمة:</strong> {e(instruments["rights_notice"])}</div>
<p>الترجمة اللغوية وحدها لا تنشئ نسخة مقننة. يلزم إذن صاحب الحقوق، وترجمة وتكييف ثقافي منهجي، ودراسة خصائص القياس ومعايير مناسبة قبل تفسير الدرجات معيارياً. إذا لم تتوافر نسخة مناسبة، يصرح المختص بالحدود ويقوي الملاحظة الوظيفية والعينات الطبيعية ولا يخترع معيارًا.</p>
{render_instrument_registry(instruments)}
<h2>7. السجل الموسع حسب عائلة الحالة</h2>
{registries}
</div></section>
<section class="otb-section otb-soft"><div class="otb-wrap">
<h2>8. حوكمة الدليل والتحديث</h2>
<ul class="otb-checks">
<li>مصدر مؤسسي أو مراجعة محكمة لكل مبدأ عام، ومصدر خاص بالحالة كلما توافر.</li>
<li>تاريخ مراجعة ظاهر، ورقم إصدار، وسجل آلة قابل للتدقيق في API.</li>
<li>فصل واضح بين دليل مباشر، وتطبيق منقول، وتجربة وظيفية فردية.</li>
<li>لا ادعاء اعتماد أو جائزة أو مراجعة خارجية قبل حدوثه وتوثيقه.</li>
<li>المراجعة القادمة تشمل اختصاصيين عربًا، وأشخاصًا ذوي خبرة معاشة، وأسرًا، وخبراء قياس وحقوق.</li>
</ul>
<h2>المراجع المؤسسة للمنهج</h2>
{source_list(data, ["who-icf", "who-rehab", "wwc-scd", "scribe", "gas", "dec", "udl", "nice-complex", "unicef-inclusive"])}
</div></section>"""
    schema = {
        "@type": "TechArticle",
        "@id": BASE + SECTION + "/methodology/#page",
        "url": BASE + SECTION + "/methodology/",
        "headline": "منهجية أفكار خارج الصندوق",
        "description": description,
        "inLanguage": "ar",
        "dateModified": UPDATED,
        "isPartOf": {"@id": BASE + "#website"},
        "publisher": {"@id": BASE + "#organization"},
        "citation": [data["sources"][key]["url"] for key in data["sources"]],
    }
    return page_shell(
        title="منهجية أفكار خارج الصندوق",
        description=description,
        canonical_path=SECTION + "/methodology/",
        main=main,
        schema_nodes=[schema, crumb_schema],
        current="منهجية القسم",
    )


def render_protocol_card(
    protocol_key: str,
    protocol: dict[str, Any],
    focus: str,
    index: int,
) -> str:
    return f"""<article class="otb-protocol">
<div class="otb-protocol-head"><span>الفكرة {index}</span><h3>{e(protocol["title"])}</h3></div>
<p><strong>الهدف المرتبط بالحالة:</strong> {e(focus)}</p>
<p><strong>صلة الفكرة بالدليل:</strong> {e(protocol["evidence_relation"])}</p>
<h4>خطوات التنفيذ</h4>{ordered(protocol["steps"])}
<dl class="otb-specs">
<div><dt>الجرعة الابتدائية</dt><dd>{e(protocol["dose"])}</dd></div>
<div><dt>مؤشر القياس</dt><dd>{e(protocol["measure"])}</dd></div>
<div><dt>قاعدة التوقف/التصعيد</dt><dd>{e(protocol["stop_rule"])}</dd></div>
</dl>
<p class="otb-code">رمز البروتوكول: <code>{e(protocol_key)}</code></p>
</article>"""


def render_condition_page(
    data: dict[str, Any],
    instruments: dict[str, Any],
    condition: dict[str, Any],
    previous: dict[str, Any] | None,
    following: dict[str, Any] | None,
) -> str:
    cluster = data["clusters"][condition["cluster"]]
    protocols = [
        (key, data["protocols"][key]) for key in condition["protocol_keys"]
    ]
    source_keys = condition_source_keys(data, condition)
    canonical_path = f"{SECTION}/{condition['slug']}/"
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("أفكار خارج الصندوق", BASE_PATH + SECTION + "/"),
            (condition["title_ar"], None),
        ]
    )
    protocol_cards = "".join(
        render_protocol_card(key, protocol, condition["focus"][index - 1], index)
        for index, (key, protocol) in enumerate(protocols, start=1)
    )
    team_rows = "".join(
        f"<tr><th scope=\"row\">{index}</th><td>{e(member)}</td>"
        f"<td>{e(condition['focus'][(index - 1) % 3])}</td>"
        "<td>يوثق التنفيذ والنتيجة والعبء في موعد المراجعة.</td></tr>"
        for index, member in enumerate(cluster["team"], start=1)
    )
    adjacent = []
    if previous:
        adjacent.append(
            f'<a class="otb-prev" href="../{e(previous["slug"])}/">السابق: '
            f'{e(previous["title_ar"])} <span>#{previous["rank"]}</span></a>'
        )
    if following:
        adjacent.append(
            f'<a class="otb-next" href="../{e(following["slug"])}/">التالي: '
            f'{e(following["title_ar"])} <span>#{following["rank"]}</span></a>'
        )
    description = (
        f"مسار مؤسسي لمقدم الخدمة حول {condition['title_ar']}: تحديد وتقييم واختبارات "
        "وبروتوكولات وتوقعات ومتابعة وإعادة قرار."
    )
    main = f"""
<section class="otb-page-hero otb-condition-hero"><div class="otb-wrap">
{crumbs}
<div class="otb-condition-heading"><div>
<p class="otb-eyebrow">الحالة {condition["rank"]} من 100 · الفئة {e(condition["prevalence_tier"])}</p>
<h1>{e(condition["title_ar"])}</h1>
<p class="otb-en" lang="en" dir="ltr">{e(condition["title_en"])}</p>
<p class="otb-lead">{e(condition["status"])}</p>
</div><aside class="otb-rank-large"><span>ترتيب تخطيطي</span><strong>{condition["rank"]}</strong><small>ليس أولوية علاجية فردية</small></aside></div>
<div class="otb-notice"><strong>الانتشار:</strong> {e(condition["prevalence_note"])} الرتبة تساعد في ترتيب المكتبة فقط؛ اختلاف الأعمار والبلدان والتعريفات يمنع المقارنة الرقمية المباشرة دائمًا.</div>
<div class="otb-notice warning"><strong>حد الاستخدام:</strong> هذا المسار لا يُشخّص الحالة ولا يحدد أهلية خدمة، ولا يُطبّق بدل تقييم فردي يقوده مختص مؤهل.</div>
<div class="otb-tags">{"".join(f"<span>{e(item)}</span>" for item in condition["focus"])}</div>
</div></section>
<nav class="otb-local-nav" aria-label="مراحل مسار الحالة"><div class="otb-wrap">
<a href="#identify">1 التحديد</a><a href="#test">2 الاختبار</a><a href="#evaluate">3 التقييم</a><a href="#protocols">4 الأفكار</a><a href="#expected">5 المتوقع</a><a href="#timeline">6 المتابعة</a><a href="#reassess">7 إعادة التقييم</a>
</div></nav>
<section class="otb-section" id="identify"><div class="otb-wrap">
<p class="otb-eyebrow">البوابة الأولى</p><h2>تحديد الحالة وصياغة السؤال</h2>
<div class="otb-cards-3">
<article class="otb-card"><h3>تعريف العمل</h3><p>{e(condition["status"])}</p><p>تُسجل كفرضية أو تشخيص موثق مع مصدره وتاريخه، ولا يستنتج التشخيص من هذه الصفحة.</p></article>
<article class="otb-card"><h3>الأثر الذي سنختبره</h3>{ul(condition["focus"])}</article>
<article class="otb-card"><h3>الفريق المحتمل</h3>{ul(cluster["team"])}</article>
</div>
<h3>أسئلة الدخول الإلزامية</h3>
<ol class="otb-process compact">
<li>ما الذي يريده الشخص أو الأسرة أن يصبح ممكنًا في الحياة اليومية؟</li>
<li>ما المهارة أو الموقف المحدد، وفي أي بيئة ومع أي شركاء؟</li>
<li>ما نقاط القوة ووسيلة التواصل والاختيارات والتهيئات الناجحة الآن؟</li>
<li>هل توجد نتيجة تشخيصية موثقة، أم أن المطلوب فرز وإحالة وتشخيص تفريقي؟</li>
<li>هل طرأ فقد مفاجئ، ألم، تغير دوائي، خطر، أو عائق وصول يجب أن يسبق الخطة؟</li>
</ol>
<div class="otb-alert"><h3>ما يجب استبعاده أو تفسيره أولًا</h3>{ul(cluster["rule_out"])}</div>
</div></section>
<section class="otb-section otb-soft" id="test"><div class="otb-wrap">
<p class="otb-eyebrow">البوابة الثانية</p><h2>اختبار الحالة باختبارات مناسبة</h2>
<div class="otb-assessment-grid">
<article class="otb-panel"><h3>أ. تقييم أولي</h3>{ul(cluster["initial_assessment"])}</article>
<article class="otb-panel"><h3>ب. تقييم شامل</h3>{ul(cluster["comprehensive_assessment"])}</article>
<article class="otb-panel"><h3>ج. إضافات خاصة بهذه الحالة</h3>{ul(condition["assessment_extras"])}</article>
<article class="otb-panel"><h3>د. مجالات الأداء</h3>{ul(cluster["functional_domains"])}</article>
</div>
<h3>أمثلة أدوات وإجراءات دولية لهذه العائلة</h3>
{render_instrument_registry(instruments, condition["cluster"])}
<div class="otb-notice warning"><strong>حقوق وصدق القياس:</strong> {e(instruments["rights_notice"])} لا تنقل معيارًا أجنبيًا إلى العربية لمجرد ترجمة البنود، ولا تفسر الدرجة خارج العمر واللغة والغرض اللذين تسمح بهما النسخة.</div>
</div></section>
<section class="otb-section" id="evaluate"><div class="otb-wrap">
<p class="otb-eyebrow">البوابة الثالثة</p><h2>تقييم الحالة وتثبيت خط الأساس</h2>
<div class="otb-split"><div>
<h3>تثليث الأدلة</h3><p>يلزم أن تتقاطع ثلاثة أنواع من المعلومات قبل القرار: ما يبلغه الشخص/الأسرة، وما يظهر في مهمة حقيقية، وما تقيسه أداة أو إجراء مناسب. إذا تعارضت، يُبحث سبب التعارض ولا تؤخذ «متوسطات» تخفيه.</p>
<ul class="otb-checks"><li>درجة أو وصف الأداة مع حدود الثقة والملاءمة.</li><li>عينة وظيفية في سياقين عندما يكون التعميم هدفًا.</li><li>اختيار الشخص ورضاه والعبء الواقع عليه وعلى الأسرة.</li><li>المتغيرات الطبية والبيئية والتعليم السابق.</li></ul>
</div><aside class="otb-panel"><h3>خط الأساس المقترح</h3>{ul(cluster["baseline"])}<p><strong>الحد الأدنى:</strong> ثلاث نقاط مستقلة قبل التدخل تحت شروط موثقة، ما لم تفرض السلامة بدء الدعم فورًا.</p></aside></div>
<h3>سجل BTR‑ICF الأصلي غير التشخيصي</h3>
<p>يسجل لكل مسبار: عدد الفرص، والنجاح المستقل، والنجاح مع تلميح، ونوع التلميح، والوقت/الكمون أو التكرار، والسياق، وجودة التنفيذ، والعبء أو الأثر السلبي، وتعليق الشخص. هو سجل متابعة ابتكرته المنصة لهيكلة البيانات؛ ليس مقياسًا مقننًا ولا يملك نقاط قطع تشخيصية.</p>
<div class="otb-actions"><a class="otb-button" href="../monitoring-matrix/?condition={e(condition["slug"])}">فتح السجل لهذه الحالة</a><a class="otb-button secondary" href="../methodology/#registry-{e(condition["cluster"])}">مراجعة سجل الأدوات</a></div>
</div></section>
<section class="otb-section otb-soft" id="protocols"><div class="otb-wrap">
<p class="otb-eyebrow">البوابة الرابعة</p><h2>الأفكار المناسبة والبروتوكولات</h2>
<p>هذه خيارات اختبار مهني، وليست حزمة إلزامية. ابدأ بالخيار الأكثر اتصالًا بالهدف وبأقل عبء، وثبّت ما تغير حتى يمكن تفسير الاستجابة.</p>
<div class="otb-protocol-grid">{protocol_cards}</div>
<h3>جدول التنفيذ والمسؤولية</h3>
<div class="otb-table-wrap"><table class="otb-table"><caption>من يفعل ماذا؟ يخصص الفريق الخانات قبل البدء</caption>
<thead><tr><th>#</th><th>الدور</th><th>المحور الأولي</th><th>دليل الإنجاز</th></tr></thead><tbody>{team_rows}</tbody></table></div>
</div></section>
<section class="otb-section" id="expected"><div class="otb-wrap">
<p class="otb-eyebrow">البوابة الخامسة</p><h2>ما المتوقع من الحالة؟</h2>
<div class="otb-outcome"><h3>الهدف الوظيفي المقترح للتخصيص</h3><p>{e(condition["outcome_goal"])}</p></div>
<p>يحوّل الفريق العبارة السابقة إلى هدف يحدد <strong>السلوك والسياق ومستوى المساعدة ومؤشر الأداء والمدة</strong>. المتوقع العلمي هو الوصول إلى نقطة قرار أو اتجاه قابل للتفسير ضمن مدة محددة؛ أما مقدار التحسن الفردي فلا يُضمن.</p>
<div class="otb-table-wrap"><table class="otb-table"><caption>المستوى المتوقع بوصفه مستوى قرار، لا وعد نتيجة</caption>
<thead><tr><th>المرحلة</th><th>المستوى المتوقع</th><th>ما الذي يثبت الوصول؟</th></tr></thead><tbody>
<tr><th scope="row">تهيئة</th><td>هدف واحد قابل للرصد وخط أساس صالح</td><td>تعريف تشغيلي + 3 نقاط + موافقة + خطة سلامة.</td></tr>
<tr><th scope="row">قابلية التطبيق</th><td>الخطة مفهومة ومقبولة ويمكن تنفيذها</td><td>توثيق الجرعة وجودة التنفيذ والعبء دون ضرر.</td></tr>
<tr><th scope="row">إشارة استجابة</th><td>اتجاه أولي أو دليل واضح على غياب الاتجاه</td><td>قياسات متكررة متكافئة، لا انطباع جلسة واحدة.</td></tr>
<tr><th scope="row">فائدة وظيفية</th><td>تغير ذو معنى في النشاط أو المشاركة</td><td>هدف GAS فردي محدد مسبقًا + تقرير الشخص + عينة حقيقية.</td></tr>
<tr><th scope="row">تعميم/استدامة</th><td>استخدام المهارة أو الدعم مع شريك/مكان آخر</td><td>مسبار صيانة وتعميم مع دعم أقل أو عبء أقل.</td></tr>
</tbody></table></div>
</div></section>
<section class="otb-section otb-soft" id="timeline"><div class="otb-wrap">
<p class="otb-eyebrow">البوابة السادسة</p><h2>الجدول الزمني لمراقبة الاستجابة</h2>
<div class="otb-table-wrap"><table class="otb-table otb-timeline"><caption>نقاط مراجعة افتراضية تعدّل حسب العمر والخطر وطبيعة المهارة</caption>
<thead><tr><th>الوقت</th><th>المطلوب</th><th>المتوقع المسؤول</th><th>قرار الفريق</th></tr></thead><tbody>
<tr><th scope="row">الأسبوع 0</th><td>موافقة، فحوص سلامة، هدف، 3 نقاط خط أساس، وتدريب المنفذ.</td><td>بيانات قابلة للمقارنة وخطة ذات جرعة وقاعدة توقف.</td><td>ابدأ، أو أحل/أكمل التقييم قبل البدء.</td></tr>
<tr><th scope="row">الأسبوع 2</th><td>افحص القبول والعبء وجودة التنفيذ والآثار غير المرغوبة.</td><td>قابلية تنفيذ؛ لا يشترط تحسن سريري بعد.</td><td>ثبت الإجراء، بسّطه، أو أوقفه للسلامة.</td></tr>
<tr><th scope="row">الأسبوع 6</th><td>اقرأ المستوى والاتجاه والتباين وقارنها بخط الأساس.</td><td>إشارة استجابة قابلة للرؤية أو غياب استجابة موثق.</td><td>استمر، زد الدقة/الجرعة، اختبر بديلًا، أو أعد الفرضية.</td></tr>
<tr><th scope="row">الأسبوع 12</th><td>أعد المهمة الوظيفية وهدف GAS، واسأل الشخص والأسرة، واختبر سياقًا ثانيًا.</td><td>فائدة ذات معنى أو سبب محدد لعدم بلوغها.</td><td>ثبّت، عمّم، غيّر البروتوكول، أو أحل لتقييم أوسع.</td></tr>
<tr><th scope="row">الأسبوع 24</th><td>مسبار صيانة وتعميم ومراجعة الأجهزة والحقوق وخطة الانتقال.</td><td>استدامة مع أقل مساعدة فعالة، أو خطة دعم طويلة المدى.</td><td>خفف المتابعة، حافظ، أو افتح دورة قرار جديدة.</td></tr>
</tbody></table></div>
<p class="otb-callout">في حالة الخطر أو التدهور أو فقد المهارة لا ينتظر الفريق موعد الجدول. الانتقال إلى الإحالة الطبية أو مسار الحماية فوري بحسب الحالة والنظام المحلي.</p>
</div></section>
<section class="otb-section" id="reassess"><div class="otb-wrap">
<p class="otb-eyebrow">البوابة السابعة</p><h2>إعادة التقييم: هل وصلنا؟ وما العائق والخطة البديلة؟</h2>
<div class="otb-reassess-grid">
<article class="otb-card"><h3>هل وصلنا إلى المنشود؟</h3><ul><li>هل تحقق المستوى المحدد مسبقًا؟</li><li>هل يراه الشخص مفيدًا ومقبولًا؟</li><li>هل ظهر في مهمة وسياق حقيقيين؟</li><li>هل يمكن الحفاظ عليه دون عبء غير مقبول؟</li></ul></article>
<article class="otb-card"><h3>حلل العائق</h3><ul><li>فرضية أو هدف غير دقيق.</li><li>أداة أو معيار غير ملائم للغة/الوصول.</li><li>جرعة أو جودة تنفيذ غير كافية.</li><li>ألم أو نوم أو سمع أو بصر أو دواء.</li><li>الخطة لا تعكس اختيار الشخص أو بيئته.</li></ul></article>
<article class="otb-card"><h3>الخطة البديلة الخاصة</h3><p>{e(condition["alternative"])}</p><p>غيّر متغيرًا واحدًا، أعد خط الأساس عند تغير الهدف، وحدد موعد قرار جديدًا.</p></article>
</div>
<div class="otb-alert"><h3>مؤشرات تستلزم إيقاف المسار أو تصعيده</h3>{ul(cluster["urgent_flags"])}<p>عند خطر مباشر أو وشيك استخدم خدمات الطوارئ أو الصحة أو الحماية المحلية المناسبة؛ هذه الصفحة لا تحدد رقم بلدك.</p></div>
<h3>مراجع هذه الحالة والمنهج</h3>
{source_list(data, source_keys)}
<p class="otb-direct-source"><a href="{e(condition["reference_url"])}" target="_blank" rel="noopener noreferrer">فتح المرجع المباشر الخاص بالحالة أو قاعدة الحالة ↗</a></p>
<div class="otb-notice"><strong>تاريخ المراجعة الداخلية:</strong> <time datetime="{UPDATED}">{UPDATED}</time>. <strong>المراجعة الخارجية:</strong> لم تكتمل ولم يُدعَ اعتماد المسار. يلزم فحص المحتوى من مختص الحالة ومختص قياس وممثل خبرة معاشة قبل اعتماده كسياسة مؤسسة.</div>
<nav class="otb-adjacent" aria-label="الحالات السابقة والتالية">{"".join(adjacent)}</nav>
</div></section>"""
    page_schema = {
        "@type": "MedicalWebPage",
        "@id": BASE + canonical_path + "#page",
        "url": BASE + canonical_path,
        "name": f"مسار مقدم الخدمة: {condition['title_ar']}",
        "description": description,
        "inLanguage": "ar",
        "dateModified": UPDATED,
        "lastReviewed": UPDATED,
        "isPartOf": {"@id": BASE + SECTION + "/#page"},
        "publisher": {"@id": BASE + "#organization"},
        "audience": {
            "@type": "ProfessionalAudience",
            "audienceType": "مقدمو الخدمات المؤهلون",
        },
        "about": {
            "@type": "MedicalCondition",
            "name": condition["title_ar"],
            "alternateName": condition["title_en"],
        },
        "citation": [
            *[data["sources"][key]["url"] for key in source_keys],
            condition["reference_url"],
        ],
    }
    return page_shell(
        title=f"{condition['title_ar']} — مسار مقدم الخدمة",
        description=description,
        canonical_path=canonical_path,
        main=main,
        schema_nodes=[page_schema, crumb_schema],
    )


def render_monitoring_matrix(data: dict[str, Any]) -> str:
    crumbs, crumb_schema = breadcrumbs(
        [
            ("الرئيسية", BASE_PATH),
            ("أفكار خارج الصندوق", BASE_PATH + SECTION + "/"),
            ("مصفوفة المتابعة", None),
        ]
    )
    options = "".join(
        f'<option value="{e(item["slug"])}">{item["rank"]}. {e(item["title_ar"])}</option>'
        for item in data["conditions"]
    )
    description = (
        "سجل محلي غير تشخيصي لمراقبة خط الأساس والاستجابة والعبء وجودة التنفيذ "
        "عبر أسابيع 0 و2 و6 و12 و24."
    )
    main = f"""
<section class="otb-page-hero"><div class="otb-wrap">{crumbs}
<p class="otb-eyebrow">BTR‑ICF v254 · سجل أصلي غير تشخيصي</p><h1>مصفوفة مراقبة الاستجابة</h1>
<p class="otb-lead">أداة توثيق محلية تساعد مقدم الخدمة على مقارنة فرص متكافئة عبر الزمن، وربط الأداء بالسياق والتلميح وجودة التنفيذ وقبول الشخص. لا تصدر تشخيصًا أو توصية آلية أو نقطة قطع.</p>
<div class="otb-notice privacy"><strong>خصوصيتك:</strong> الحفظ داخل متصفح هذا الجهاز فقط عبر التخزين المحلي، ولا توجد مزامنة أو إرسال إلى خادم. استخدم رمز حالة غير كاشف، ولا تدخل اسمًا أو رقمًا وطنيًا أو معلومات صحية لا تحتاجها.</div>
</div></section>
<section class="otb-section"><div class="otb-wrap">
<h2>1. أنشئ إطار المتابعة</h2>
<form class="otb-form" data-plan-form>
<div class="otb-form-grid">
<label>رمز حالة غير كاشف<input name="case_code" maxlength="24" autocomplete="off" placeholder="مثال: EDU-024" required></label>
<label>الحالة أو المسار<select name="condition" data-plan-condition required><option value="">اختر الحالة</option>{options}</select></label>
<label>تاريخ بدء خط الأساس<input name="start_date" type="date" required></label>
<label class="span-2">الهدف الوظيفي المحدد<input name="target" maxlength="180" placeholder="من سيفعل ماذا، أين، وبأي مستوى مساعدة؟" required></label>
</div>
<button class="otb-button" type="submit">إنشاء التواريخ</button>
</form>
<div class="otb-table-wrap"><table class="otb-table"><caption>مواعيد القرار المحسوبة من تاريخ البداية</caption>
<thead><tr><th>النقطة</th><th>التاريخ</th><th>السؤال الحاكم</th><th>الدليل المطلوب</th></tr></thead><tbody>
<tr><th scope="row">الأسبوع 0</th><td data-plan-date="0">—</td><td>هل خط الأساس صالح والخطة آمنة؟</td><td>3 نقاط على الأقل، موافقة، تعريف، جرعة، وقاعدة توقف.</td></tr>
<tr><th scope="row">الأسبوع 2</th><td data-plan-date="2">—</td><td>هل يمكن تنفيذ الخطة بقبول وعبء مناسبين؟</td><td>جودة تنفيذ، قبول/رفض، عبء، وآثار غير مرغوبة.</td></tr>
<tr><th scope="row">الأسبوع 6</th><td data-plan-date="6">—</td><td>هل توجد إشارة استجابة؟</td><td>المستوى والاتجاه والتباين عبر قياسات متكافئة.</td></tr>
<tr><th scope="row">الأسبوع 12</th><td data-plan-date="12">—</td><td>هل تحقق تغير وظيفي ذو معنى؟</td><td>مهمة حقيقية، هدف فردي، تقرير الشخص، وسياق ثانٍ.</td></tr>
<tr><th scope="row">الأسبوع 24</th><td data-plan-date="24">—</td><td>هل استمر الأثر وتعمم؟</td><td>مسبار صيانة وتعميم وعبء طويل المدى.</td></tr>
</tbody></table></div>
</div></section>
<section class="otb-section otb-soft"><div class="otb-wrap">
<h2>2. أضف مسبارًا واحدًا</h2>
<form class="otb-form" data-record-form>
<div class="otb-form-grid">
<label>التاريخ<input name="date" type="date" required></label>
<label>المرحلة<select name="phase" required><option value="baseline">خط الأساس</option><option value="intervention">تطبيق</option><option value="generalization">تعميم</option><option value="maintenance">صيانة</option></select></label>
<label>السياق<input name="context" maxlength="80" placeholder="الصف، المنزل، المجتمع…" required></label>
<label>عدد الفرص<input name="opportunities" type="number" min="0" max="999" inputmode="numeric" required></label>
<label>نجاح مستقل<input name="independent" type="number" min="0" max="999" inputmode="numeric" required></label>
<label>نجاح مع تلميح<input name="prompted" type="number" min="0" max="999" inputmode="numeric" required></label>
<label>نوع التلميح<input name="prompt_type" maxlength="60" placeholder="بصري، لفظي، نمذجة…"></label>
<label>زمن/كمون بالدقائق<input name="duration" type="number" min="0" max="1440" step="0.1" inputmode="decimal"></label>
<label>تكرار السلوك المستهدف<input name="frequency" type="number" min="0" max="9999" inputmode="numeric"></label>
<label>جودة التنفيذ %<input name="fidelity" type="number" min="0" max="100" inputmode="numeric" required></label>
<label>العبء/الضيق 0–4<select name="burden" required><option value="0">0 — لا يُلاحظ</option><option value="1">1 — خفيف</option><option value="2">2 — متوسط</option><option value="3">3 — مرتفع</option><option value="4">4 — شديد/أوقف وراجع</option></select></label>
<label>موقف الشخص<select name="assent" required><option value="accepted">موافق/متقبل</option><option value="unclear">غير واضح — حسّن الإتاحة</option><option value="declined">رفض/طلب التوقف</option></select></label>
<label class="span-2">ملاحظة مختصرة بلا بيانات تعريفية<textarea name="notes" maxlength="300" rows="3" placeholder="ما التغيير الوحيد؟ هل ظهر أثر غير مرغوب؟"></textarea></label>
</div>
<div class="otb-actions"><button class="otb-button" type="submit">حفظ السجل محليًا</button><button class="otb-button secondary" type="reset">مسح الحقول</button></div>
</form>
<div class="otb-notice warning" data-record-warning hidden role="alert"></div>
</div></section>
<section class="otb-section"><div class="otb-wrap">
<div class="otb-section-heading"><div><h2>3. السجلات المحفوظة</h2><p data-storage-status aria-live="polite">لم يُحمّل أي سجل بعد.</p></div>
<div class="otb-actions"><button class="otb-button secondary" type="button" data-export-json>تصدير JSON</button><button class="otb-button secondary" type="button" data-export-csv>تصدير CSV</button><button class="otb-button secondary" type="button" data-print>طباعة</button><button class="otb-button danger" type="button" data-clear-records>حذف السجلات المحلية</button></div></div>
<div class="otb-table-wrap"><table class="otb-table"><caption>سجل BTR‑ICF؛ معدل الاستقلال وصفي داخل الحالة فقط</caption>
<thead><tr><th>التاريخ</th><th>المرحلة</th><th>السياق</th><th>الفرص</th><th>مستقل</th><th>مع تلميح</th><th>معدل الاستقلال</th><th>التنفيذ</th><th>العبء</th><th>القبول</th><th>حذف</th></tr></thead>
<tbody data-records-body><tr data-empty-row><td colspan="11">لا توجد سجلات محفوظة.</td></tr></tbody></table></div>
</div></section>
<section class="otb-section otb-soft"><div class="otb-wrap">
<h2>4. قواعد القراءة واتخاذ القرار</h2>
<div class="otb-cards-3">
<article class="otb-card"><h3>معدل الاستقلال</h3><p><code>النجاح المستقل ÷ الفرص × 100</code>. لا تحسبه عندما تختلف الفرص أو المهمة جذريًا، ولا تقارنه بمعيار تشخيصي.</p></article>
<article class="otb-card"><h3>جودة التنفيذ</h3><p>انخفاض النتيجة مع تنفيذ ضعيف لا يثبت فشل الفكرة. أصلح التدريب أو بسّط الخطوات ثم اجمع نقاطًا جديدة.</p></article>
<article class="otb-card"><h3>القبول والعبء</h3><p>التحسن الشكلي لا يبرر الضيق أو الرفض. العبء 4 أو طلب التوقف يفعّل قاعدة الإيقاف والمراجعة.</p></article>
</div>
<div class="otb-table-wrap"><table class="otb-table"><caption>مصفوفة قرار لا خوارزمية تشخيص</caption>
<thead><tr><th>نمط البيانات</th><th>التفسير المحتمل</th><th>الخطوة التالية</th></tr></thead><tbody>
<tr><td>اتجاه مفيد + تنفيذ جيد + قبول</td><td>الفكرة مرشحة للاستمرار لهذه الحالة.</td><td>اختبر التعميم أو خفف التلميح تدريجيًا.</td></tr>
<tr><td>مسطح + تنفيذ ضعيف</td><td>لا يمكن الحكم على الفكرة بعد.</td><td>أصلح التنفيذ واجمع نقاطًا متكررة.</td></tr>
<tr><td>مسطح + تنفيذ جيد</td><td>هدف أو فرضية أو جرعة غير مناسبة محتملة.</td><td>أعد التقييم وغيّر متغيرًا واحدًا.</td></tr>
<tr><td>تباين شديد حسب السياق</td><td>عامل بيئي أو شريك أو وصول يؤثر.</td><td>قارن السياقات تحت شروط موثقة.</td></tr>
<tr><td>تدهور أو عبء شديد أو رفض</td><td>إشارة سلامة أو عدم ملاءمة.</td><td>أوقف، افحص السبب، وأحل عند الحاجة.</td></tr>
</tbody></table></div>
<h2>5. حدود السجل</h2>
<ul class="otb-checks"><li>لم يخضع BTR‑ICF لدراسة صدق أو ثبات أو معايير؛ لذلك لا يسمى اختبارًا أو مقياسًا مقننًا.</li><li>لا يجمع الحقول في درجة كلية، ولا ينتج «طبيعي/غير طبيعي»، ولا يحدد أهلية خدمة.</li><li>لا يستبدل الأداة الرسمية أو الفحص الطبي أو الحكم المهني أو تقرير الشخص.</li><li>التصدير ملف محلي؛ مسؤولية حفظه وحمايته وحذفه تقع على المستخدم والمؤسسة.</li></ul>
<div class="otb-actions"><a class="otb-button secondary" href="../methodology/">العودة إلى المنهجية</a><a class="otb-button secondary" href="../">اختيار مسار حالة</a></div>
</div></section>"""
    schema = {
        "@type": "WebApplication",
        "@id": BASE + SECTION + "/monitoring-matrix/#app",
        "url": BASE + SECTION + "/monitoring-matrix/",
        "name": "مصفوفة مراقبة الاستجابة BTR-ICF",
        "description": description,
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Web",
        "browserRequirements": "يعمل محليًا في متصفح حديث",
        "inLanguage": "ar",
        "dateModified": UPDATED,
        "isPartOf": {"@id": BASE + "#website"},
        "publisher": {"@id": BASE + "#organization"},
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
    }
    return page_shell(
        title="مصفوفة مراقبة الاستجابة BTR‑ICF",
        description=description,
        canonical_path=SECTION + "/monitoring-matrix/",
        main=main,
        schema_nodes=[schema, crumb_schema],
        current="مصفوفة المتابعة",
    )


def replace_marker_block(source: str, block: str, *, before: str = "</main>") -> str:
    pattern = re.compile(
        r"[ \t]*"
        + re.escape(BRIDGE_START)
        + r".*?"
        + re.escape(BRIDGE_END)
        + r"[ \t]*\n?",
        re.DOTALL,
    )
    source = pattern.sub("", source)
    if before not in source:
        raise ValueError(f"Cannot integrate outside-the-box block; missing marker {before}")
    return source.replace(before, block + "\n" + before, 1)


def ensure_stylesheet(source: str) -> str:
    source = source.replace(
        STYLE_MARKER
        + f'<link rel="stylesheet" href="{BASE_PATH}assets/css/outside-the-box-v254.css">',
        "",
    )
    if "</head>" not in source:
        raise ValueError("Cannot integrate outside-the-box stylesheet; missing </head>")
    link = (
        STYLE_MARKER
        + f'<link rel="stylesheet" href="{BASE_PATH}assets/css/outside-the-box-v254.css">'
    )
    return source.replace("</head>", link + "</head>", 1)


def patch_integration_pages(site: Path) -> dict[str, bool]:
    homepage = site / "index.html"
    special = site / "special-needs" / "index.html"
    provider = site / "provider-assessment-demo" / "index.html"
    for path in (homepage, special, provider):
        if not path.is_file():
            raise ValueError(f"Missing integration page: {path}")

    home_text = homepage.read_text(encoding="utf-8")
    home_text = re.sub(
        r'<a data-outside-the-box-v254-nav[^>]*>.*?</a>',
        "",
        home_text,
        flags=re.DOTALL,
    )
    nav_link = (
        '<a data-outside-the-box-v254-nav href="outside-the-box/">'
        "أفكار خارج الصندوق</a>"
    )
    nav_match = re.search(r'(<nav class="nav"[^>]*>)(.*?)(</nav>)', home_text, re.DOTALL)
    if not nav_match:
        raise ValueError("Homepage primary navigation was not found")
    home_text = (
        home_text[: nav_match.start()]
        + nav_match.group(1)
        + nav_match.group(2)
        + nav_link
        + nav_match.group(3)
        + home_text[nav_match.end() :]
    )
    home_block = f"""{BRIDGE_START}
<section class="section" data-outside-the-box-v254 aria-labelledby="outside-the-box-home-title">
<p class="eyebrow">قرار مهني قائم على الدليل</p>
<h2 id="outside-the-box-home-title">أفكار خارج الصندوق: 100 مسار من التقييم إلى قياس الأثر</h2>
<p class="section-intro">قسم لمقدم الخدمة يربط تحديد الحالة والاختبارات الملائمة والتقييم الوظيفي بثلاثة بروتوكولات قابلة للتجربة، وجدول متابعة في الأسابيع 0 و2 و6 و12 و24، ثم قرار الاستمرار أو التعديل أو الإحالة.</p>
<div class="cards"><article class="card"><h3>مئة حالة مرتبة تخطيطيًا</h3><p>تبدأ بالحالات الأعلى حضورًا في خدمات الطفولة والتعليم والتأهيل، ثم تنتقل إلى الحالات النادرة دون ادعاء مقارنة انتشار زائفة.</p><a href="outside-the-box/">فتح الدليل الكامل</a></article>
<article class="card"><h3>منهجية وحقوق اختبار</h3><p>يفصل القسم بين الأدوات المرخصة وسجل المتابعة الأصلي غير التشخيصي، ويبين حدود اللغة والتقنين والمستخدم المؤهل.</p><a href="outside-the-box/methodology/">قراءة العقد العلمي</a></article>
<article class="card"><h3>مصفوفة متابعة محلية</h3><p>تخطيط التواريخ وتسجيل الفرص والاستقلال والتلميحات والقبول وجودة التنفيذ بلا إرسال البيانات إلى خادم.</p><a href="outside-the-box/monitoring-matrix/">فتح المصفوفة</a></article></div>
</section>
{BRIDGE_END}"""
    home_text = replace_marker_block(home_text, home_block)
    homepage.write_text(home_text, encoding="utf-8")

    special_text = special.read_text(encoding="utf-8")
    special_block = f"""{BRIDGE_START}
<section class="section" data-outside-the-box-v254><div class="wrap">
<div class="panel"><p class="eyebrow">لمقدم الخدمة</p><h2>أفكار خارج الصندوق</h2>
<p>انتقل من دليل الاحتياج إلى مسار مؤسسي كامل: تحديد الحالة، الاختبارات المناسبة، التقييم، ثلاث أفكار ببروتوكولات وقواعد توقف، المتوقع المسؤول، جدول متابعة، ثم إعادة التقييم والخطة البديلة.</p>
<div class="actions"><a class="button" href="{BASE_PATH}outside-the-box/">تصفح 100 حالة</a><a class="button secondary" href="{BASE_PATH}outside-the-box/methodology/">المنهجية والاختبارات</a><a class="button secondary" href="{BASE_PATH}outside-the-box/monitoring-matrix/">مصفوفة المتابعة</a></div>
</div></div></section>
{BRIDGE_END}"""
    special_text = replace_marker_block(special_text, special_block)
    special.write_text(special_text, encoding="utf-8")

    provider_text = ensure_stylesheet(provider.read_text(encoding="utf-8"))
    provider_block = f"""{BRIDGE_START}
<section class="otb-bridge" data-outside-the-box-v254 aria-labelledby="outside-the-box-provider-title">
<div><p class="otb-eyebrow">الخطوة التالية بعد التقييم</p><h2 id="outside-the-box-provider-title">حوّل النتائج إلى تجربة دعم قابلة للقياس</h2>
<p>مئة مسار لمقدم الخدمة تجمع التقييم الشامل والبروتوكول والجرعة وقاعدة التوقف وجدول القرار والخطة البديلة. لا تنقل إجابات الاختبار ولا تصدر تشخيصًا آليًا.</p></div>
<div class="otb-actions"><a class="otb-button" href="{BASE_PATH}outside-the-box/">فتح أفكار خارج الصندوق</a><a class="otb-button secondary" href="{BASE_PATH}outside-the-box/monitoring-matrix/">فتح سجل المتابعة</a></div>
</section>
{BRIDGE_END}"""
    provider_text = replace_marker_block(provider_text, provider_block)
    provider.write_text(provider_text, encoding="utf-8")
    return {
        "homepage": True,
        "special_needs_hub": True,
        "provider_assessment": True,
    }


def write_sitemap(site: Path, conditions: list[dict[str, Any]]) -> list[str]:
    urls = [
        BASE + SECTION + "/",
        BASE + SECTION + "/methodology/",
        BASE + SECTION + "/monitoring-matrix/",
        *[BASE + SECTION + "/" + item["slug"] + "/" for item in conditions],
    ]
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for index, url in enumerate(urls):
        node = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(node, f"{{{SITEMAP_NS}}}loc").text = url
        ET.SubElement(node, f"{{{SITEMAP_NS}}}lastmod").text = UPDATED
        ET.SubElement(node, f"{{{SITEMAP_NS}}}changefreq").text = (
            "weekly" if index < 3 else "monthly"
        )
        ET.SubElement(node, f"{{{SITEMAP_NS}}}priority").text = (
            "0.90" if index == 0 else "0.75"
        )
    ET.ElementTree(root).write(
        site / SITEMAP_NAME, encoding="utf-8", xml_declaration=True
    )
    return urls


def register_root_sitemap(site: Path, urls: list[str]) -> str:
    path = site / "sitemap.xml"
    if not path.is_file():
        raise ValueError("Missing root sitemap")
    tree = ET.parse(path)
    root = tree.getroot()
    root_type = root.tag.rsplit("}", 1)[-1]
    namespace = root.tag.split("}", 1)[0].lstrip("{") if root.tag.startswith("{") else SITEMAP_NS
    ET.register_namespace("", namespace)

    def q(name: str) -> str:
        return f"{{{namespace}}}{name}"

    if root_type == "sitemapindex":
        target = BASE + SITEMAP_NAME
        current = [
            (node.text or "").strip()
            for node in root.findall("{*}sitemap/{*}loc")
            if node.text
        ]
        if target not in current:
            item = ET.SubElement(root, q("sitemap"))
            ET.SubElement(item, q("loc")).text = target
        mode = "child-sitemap"
    elif root_type == "urlset":
        current = {
            (node.text or "").strip()
            for node in root.findall("{*}url/{*}loc")
            if node.text
        }
        for url in urls:
            if url in current:
                continue
            item = ET.SubElement(root, q("url"))
            ET.SubElement(item, q("loc")).text = url
            current.add(url)
        mode = "expanded-urlset"
    else:
        raise ValueError(f"Unsupported root sitemap type: {root_type}")
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return mode


def sync_robots(site: Path) -> None:
    path = site / "robots.txt"
    target = f"Sitemap: {BASE}{SITEMAP_NAME}"
    if path.is_file():
        lines = [line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()]
    else:
        lines = ["User-agent: *", "Allow: /"]
    lines = [line for line in lines if line != target]
    lines.append(target)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def copy_assets(site: Path) -> None:
    for source, destination in (
        (CSS_PATH, site / "assets" / "css" / CSS_PATH.name),
        (JS_PATH, site / "assets" / "js" / JS_PATH.name),
    ):
        if not source.is_file():
            raise ValueError(f"Missing outside-the-box asset: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def validate_published(
    site: Path,
    data: dict[str, Any],
    urls: list[str],
    integration: dict[str, bool],
) -> dict[str, Any]:
    root = site / SECTION
    pages = sorted(root.rglob("index.html"))
    if len(pages) != 103:
        raise ValueError(f"Expected 103 outside-the-box pages, found {len(pages)}")
    bad_h1 = [
        path.relative_to(site).as_posix()
        for path in pages
        if len(re.findall(r"<h1\b", path.read_text(encoding="utf-8"))) != 1
    ]
    if bad_h1:
        raise ValueError(f"Pages must contain exactly one H1: {bad_h1[:5]}")
    required_markers = [
        "هذا المسار لا يُشخّص",
        "قاعدة التوقف",
        "الأسبوع 12",
        "المراجعة الخارجية",
        "application/ld+json",
        'rel="canonical"',
    ]
    bad_conditions = []
    for condition in data["conditions"]:
        path = root / condition["slug"] / "index.html"
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in required_markers if marker not in text]
        if missing:
            bad_conditions.append((condition["slug"], missing))
    if bad_conditions:
        raise ValueError(f"Incomplete condition pages: {bad_conditions[:3]}")

    hub = (root / "index.html").read_text(encoding="utf-8")
    missing_links = [
        item["slug"]
        for item in data["conditions"]
        if hub.count(f'href="{item["slug"]}/"') != 2
    ]
    if missing_links:
        raise ValueError(f"Hub static link contract failed: {missing_links[:5]}")
    sitemap_urls = [
        (node.text or "").strip()
        for node in ET.parse(site / SITEMAP_NAME).getroot().findall("{*}url/{*}loc")
        if node.text
    ]
    if sitemap_urls != urls or len(sitemap_urls) != len(set(sitemap_urls)):
        raise ValueError("Outside-the-box sitemap is incomplete, duplicated, or out of order")
    robots = (site / "robots.txt").read_text(encoding="utf-8")
    if robots.count(f"Sitemap: {BASE}{SITEMAP_NAME}") != 1:
        raise ValueError("robots.txt outside-the-box sitemap registration failed")
    for path in (
        site / "index.html",
        site / "special-needs" / "index.html",
        site / "provider-assessment-demo" / "index.html",
    ):
        text = path.read_text(encoding="utf-8")
        if text.count(BRIDGE_START) != 1 or text.count(BRIDGE_END) != 1:
            raise ValueError(f"Integration marker contract failed: {path}")
    generated_text = "\n".join(path.read_text(encoding="utf-8") for path in pages)
    banned = ["معاقين", "شفاء مضمون", "اعتماد عالمي مكتمل", "جائزة مضمونة"]
    found = [term for term in banned if term in generated_text]
    if found:
        raise ValueError(f"Unsafe or stigmatizing claims detected: {found}")
    runtime = (site / "assets" / "js" / JS_PATH.name).read_text(encoding="utf-8")
    network_markers = ["fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket"]
    found_network = [item for item in network_markers if item in runtime]
    if found_network:
        raise ValueError(f"Monitoring runtime must be local-only: {found_network}")
    return {
        "version": VERSION,
        "status": "passed",
        "review_status": data["review_status"],
        "external_clinical_review_completed": False,
        "condition_count": len(data["conditions"]),
        "cluster_count": len(data["clusters"]),
        "protocol_count": len(data["protocols"]),
        "source_count": len(data["sources"]),
        "generated_page_count": len(pages),
        "sitemap_url_count": len(urls),
        "static_condition_links": 100,
        "single_h1_pages": len(pages),
        "integration": integration,
        "local_only_monitoring": True,
        "diagnostic_automation": False,
        "proprietary_test_items_published": False,
        "original_tracker_validated_scale": False,
    }


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ValueError(f"Missing site directory: {site}")
    data, instruments = load_and_validate()
    copy_assets(site)
    section_root = site / SECTION
    section_root.mkdir(parents=True, exist_ok=True)
    (section_root / "index.html").write_text(render_hub(data), encoding="utf-8")
    methodology = section_root / "methodology"
    methodology.mkdir(parents=True, exist_ok=True)
    (methodology / "index.html").write_text(
        render_methodology(data, instruments), encoding="utf-8"
    )
    matrix = section_root / "monitoring-matrix"
    matrix.mkdir(parents=True, exist_ok=True)
    (matrix / "index.html").write_text(
        render_monitoring_matrix(data), encoding="utf-8"
    )
    conditions = data["conditions"]
    for index, condition in enumerate(conditions):
        target = section_root / condition["slug"]
        target.mkdir(parents=True, exist_ok=True)
        previous = conditions[index - 1] if index else None
        following = conditions[index + 1] if index + 1 < len(conditions) else None
        (target / "index.html").write_text(
            render_condition_page(data, instruments, condition, previous, following),
            encoding="utf-8",
        )

    integration = patch_integration_pages(site)
    urls = write_sitemap(site, conditions)
    sitemap_mode = register_root_sitemap(site, urls)
    sync_robots(site)
    report = validate_published(site, data, urls, integration)
    report["root_sitemap_mode"] = sitemap_mode
    report["ranking_method"] = data["ranking_method"]
    report["routes"] = {
        "hub": BASE + SECTION + "/",
        "methodology": BASE + SECTION + "/methodology/",
        "monitoring_matrix": BASE + SECTION + "/monitoring-matrix/",
    }
    report["conditions"] = [
        {
            "rank": item["rank"],
            "slug": item["slug"],
            "title_ar": item["title_ar"],
            "title_en": item["title_en"],
            "cluster": item["cluster"],
            "prevalence_tier": item["prevalence_tier"],
            "focus": item["focus"],
            "protocol_keys": item["protocol_keys"],
            "source_keys": condition_source_keys(data, item),
            "url": BASE + SECTION + "/" + item["slug"] + "/",
        }
        for item in conditions
    ]
    report["sources"] = data["sources"]
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    output = api / "outside-the-box-v254.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    loaded = json.loads(output.read_text(encoding="utf-8"))
    if loaded["condition_count"] != 100 or len(loaded["conditions"]) != 100:
        raise ValueError("Outside-the-box API contract failed")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
