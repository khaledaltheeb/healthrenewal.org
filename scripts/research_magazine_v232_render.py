#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter

from research_magazine_v232_core import (
    BASE,
    MAGAZINE_URL,
    STYLE,
    article_url,
    doi_url,
    esc,
    pubmed_url,
    render_schema,
)


def render_article(item: dict) -> str:
    canonical = article_url(item)
    description = item["summary_ar"][:220].rstrip()
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(item["title_ar"])} | المجلة البحثية العربية</title>
<meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{canonical}"><meta name="color-scheme" content="light">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:url" content="{canonical}">
<meta property="og:title" content="{esc(item["title_ar"])}"><meta property="og:description" content="{esc(description)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(item["title_ar"])}">
<script type="application/ld+json">{render_schema(item)}</script><style>{STYLE}</style></head>
<body><a class="skip" href="#content">انتقل إلى المحتوى</a>
<header class="site-head"><strong>منصة الصحة النفسية وذوي الاحتياجات الخاصة</strong>
<nav aria-label="التنقل الرئيسي"><a href="/pterminology-site/">الرئيسية</a><a href="/pterminology-site/magazine/">المجلة البحثية</a><a href="/pterminology-site/trust/">الثقة والمنهجية</a></nav></header>
<main id="content">
<nav aria-label="مسار الصفحة"><a href="/pterminology-site/">الرئيسية</a> ← <a href="/pterminology-site/magazine/">المجلة</a> ← ملخص دراسة</nav>
<article>
<header class="panel"><p class="meta"><span class="tag">{esc(item["topic"])}</span><span class="tag">{esc(item["study_type"])}</span><span class="tag">{esc(item["year"])}</span></p>
<h1>{esc(item["title_ar"])}</h1><p class="original" lang="en">{esc(item["title_original"])}</p>
<p><strong>{esc(item["journal"])}</strong> · DOI: <bdi>{esc(item["doi"])}</bdi> · PMID: <bdi>{esc(item["pmid"])}</bdi></p></header>
<section class="panel"><h2>الملخص العربي الأصلي</h2><p>{esc(item["summary_ar"])}</p></section>
<section class="panel"><h2>سؤال الدراسة والمنهج</h2><p>{esc(item["methods_ar"])}</p></section>
<section class="panel"><h2>قراءة نقدية وحدود الدليل</h2><p>{esc(item["limitations_ar"])}</p></section>
<section class="panel"><h2>ماذا تعني النتيجة عمليًا؟</h2><p>{esc(item["implications_ar"])}</p></section>
<section class="panel"><h2>المصدر الأصلي والتحقق</h2><p>هذه صياغة عربية تحريرية جديدة وليست ترجمة حرفية للملخص المحمي. راجع النص الأصلي وبيانات الفهرسة قبل الاقتباس الأكاديمي.</p>
<p class="source-links"><a rel="noopener noreferrer external" href="{esc(doi_url(item))}">فتح المصدر الأصلي عبر DOI</a>
<a rel="noopener noreferrer external" href="{esc(pubmed_url(item))}">فتح سجل PubMed</a></p>
<p>تاريخ تحقق بيانات المصدر: 25 يوليو 2026. نوع المراجعة: تحرير داخلي، دون ادعاء اعتماد خارجي.</p></section>
<section class="notice" aria-label="تنبيه مهني"><h2>حدود الاستخدام</h2><p>هذا الملخص للتثقيف العام ولا يشخّص حالة ولا يحدد علاجًا فرديًا ولا يبرر تغيير دواء أو خطة علاج. القرارات الشخصية تحتاج مختصًا مؤهلًا يعرف السياق الصحي الكامل.</p></section>
</article></main>
<footer class="site-foot"><p><strong>معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</strong></p><p><a href="/pterminology-site/citation/">سياسة الاقتباس</a> · <a href="/pterminology-site/sources/">المصادر</a> · <a href="/pterminology-site/trust/">الثقة والمنهجية</a></p></footer>
</body></html>'''


def render_index(data: dict) -> str:
    summaries = sorted(data["summaries"], key=lambda item: (item["published_at"], item["title_ar"]), reverse=True)
    counts = Counter(item["topic"] for item in summaries)
    topic_links = "".join(
        f'<li><a href="#topic-{index}">{esc(topic)}</a> <span class="tag">{count}</span></li>'
        for index, (topic, count) in enumerate(sorted(counts.items()), 1)
    )
    sections = []
    for index, topic in enumerate(sorted(counts), 1):
        cards = []
        for item in [entry for entry in summaries if entry["topic"] == topic]:
            cards.append(
                f'''<article class="study-card"><p class="meta"><span class="tag">{esc(item["study_type"])}</span><span class="tag">{esc(item["year"])}</span></p>
<h3>{esc(item["title_ar"])}</h3><p>{esc(item["summary_ar"][:260].rstrip())}…</p>
<p><strong>{esc(item["journal"])}</strong> · PMID <bdi>{esc(item["pmid"])}</bdi></p>
<a href="research/{esc(item["slug"])}/">قراءة الملخص النقدي الكامل</a></article>'''
            )
        sections.append(f'<section class="panel" id="topic-{index}"><h2>{esc(topic)}</h2><div class="grid">{"".join(cards)}</div></section>')
    collection_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "مجلة الصحة النفسية والبحث العلمي",
        "description": "ملخصات عربية نقدية لأبحاث حديثة محكمة مع روابط DOI وPubMed وحدود منهجية واضحة.",
        "url": MAGAZINE_URL,
        "inLanguage": "ar",
        "dateModified": data["verified_at"],
        "numberOfItems": len(summaries),
        "hasPart": [
            {"@type": "ScholarlyArticle", "name": item["title_ar"], "url": article_url(item)}
            for item in summaries
        ],
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>مجلة الصحة النفسية والبحث العلمي | ملخصات عربية نقدية</title>
<meta name="description" content="مكتبة عربية لملخصات أبحاث الصحة النفسية الحديثة من 2025 و2026، مع DOI وPubMed وشرح المنهج والقيود وما تعنيه النتائج عمليًا.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{MAGAZINE_URL}">
<meta name="color-scheme" content="light"><meta property="og:type" content="website"><meta property="og:locale" content="ar_AR">
<meta property="og:url" content="{MAGAZINE_URL}"><meta property="og:title" content="مجلة الصحة النفسية والبحث العلمي">
<meta property="og:description" content="ملخصات عربية أصلية ودقيقة لأبحاث حديثة مع المصدر الأصلي وقراءة نقدية.">
<meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{json.dumps(collection_schema, ensure_ascii=False, separators=(",", ":"))}</script>
<style>{STYLE}</style></head><body><a class="skip" href="#content">انتقل إلى المحتوى</a>
<header class="site-head"><strong>منصة الصحة النفسية وذوي الاحتياجات الخاصة</strong>
<nav aria-label="التنقل الرئيسي"><a href="/pterminology-site/">الرئيسية</a><a href="/pterminology-site/encyclopedia/">الموسوعة</a><a href="/pterminology-site/care-guides/">أدلة التعامل</a><a href="/pterminology-site/trust/">الثقة والمنهجية</a></nav></header>
<main id="content"><header class="panel"><h1>مجلة الصحة النفسية والبحث العلمي</h1>
<p class="lead">ملخصات عربية تحريرية للأبحاث المحكمة الحديثة. تعرض كل صفحة سؤال الدراسة ومنهجها وقيودها وما يمكن استنتاجه، ثم تربط مباشرةً بسجل PubMed والمصدر الأصلي عبر DOI.</p>
<p class="progress">الدفعة المنشورة: {len(summaries)} ملخصًا من هدف تحريري يبلغ {data["target_pages"]} صفحة.</p></header>
<section class="notice"><h2>كيف نقرأ هذه المواد؟</h2><p>لا ننسخ الملخصات المنشورة ولا نحول الارتباط إلى سببية أو الدلالة الإحصائية إلى فائدة مؤكدة. كل مادة تثقيفية، وتظهر حدود الوصول والمراجعة والتطبيق بوضوح.</p></section>
<section class="panel"><h2>التصنيفات الحالية</h2><ul>{topic_links}</ul></section>
{"".join(sections)}
<section class="panel"><h2>عقد النشر العلمي</h2><p>تدخل المادة بعد التحقق من DOI وPMID ونوع الدراسة والسكان والمنهج والقيود. تبقى المراجعة داخلية ما لم يوجد اسم مراجع خارجي مؤهل وسجل مراجعة قابل للتدقيق.</p></section>
</main><footer class="site-foot"><p><strong>معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</strong></p>
<p><a href="/pterminology-site/citation/">سياسة الاقتباس</a> · <a href="/pterminology-site/sources/">المصادر</a> · <a href="/pterminology-site/trust/">الثقة والمنهجية</a></p></footer></body></html>'''
