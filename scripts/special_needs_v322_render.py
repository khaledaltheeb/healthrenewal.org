#!/usr/bin/env python3
from __future__ import annotations

from special_needs_v322_core import *

def render_guide(guide: dict[str, Any], payload: dict[str, Any]) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    toc = "".join(f'<a href="#{e(section["id"])}">{e(section["title"])}</a>' for section in guide["sections"])
    sections_html: list[str] = []
    for section in guide["sections"]:
        paragraphs = "".join(f"<p>{e(item)}</p>" for item in section["paragraphs"])
        checkpoints = "".join(f"<li>{e(item)}</li>" for item in section["checkpoints"])
        refs = " ".join(f'<a href="#source-{e(ref)}">[{e(ref)}]</a>' for ref in section["source_ids"])
        sections_html.append(
            f'<section class="section-card" id="{e(section["id"])}">'
            f'<p class="kicker">محور علمي وعملي</p><h2>{e(section["title"])}</h2>'
            f'<p><strong>{e(section["summary"])}</strong></p>{paragraphs}'
            f'<div class="checkpoints"><h3>نقاط تحقق عملية</h3><ul>{checkpoints}</ul></div>'
            f'<p class="refs"><strong>المراجع المرتبطة:</strong> {refs}</p></section>'
        )
    actions = "".join(f"<li>{e(item)}</li>" for item in guide["action_steps"])
    urgent = "".join(f"<li>{e(item)}</li>" for item in guide["urgent"])
    sources = "".join(
        f'<li id="source-{e(source["id"])}"><span class="level">{e(source["level"])}</span> '
        f'<strong>{e(source["id"])} — {e(source["organization"])}</strong>: '
        f'<a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["title"])}</a> '
        f'<small>تاريخ النشر أو المراجعة المسجل: {e(source["reviewed"])}</small></li>'
        for source in guide["sources"]
    )
    audiences = "، ".join(e(item) for item in guide["audiences"])
    related_url = f"{BP}special-needs/{e(guide['related_path_slug'])}/"
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(guide["title"])}</title>
<meta name="description" content="{e(guide["meta_description"])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="googlebot" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="ar" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<link rel="icon" href="{BP}assets/brand/logo-mark.svg" type="image/svg+xml">
<meta property="og:type" content="article">
<meta property="og:locale" content="ar_AR">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(guide["title"])}">
<meta property="og:description" content="{e(guide["meta_description"])}">
<meta property="og:image" content="{BASE}/assets/brand/rawafid-social-card.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(guide["title"])}">
<meta name="twitter:description" content="{e(guide["meta_description"])}">
<script type="application/ld+json">{page_schema(guide, payload)}</script>
<!-- pt-platform-shell:v1 -->
<meta name="copyright" content="© 2026 Khaled Altheeb — منصة روافد">
<meta name="rights" content="All rights reserved">
<link rel="license" href="{BP}copyright/">
<link rel="stylesheet" href="{BP}assets/platform/platform-core.css?v=1.1.0">
<script defer src="{BP}assets/platform/platform-core.js?v=1.1.0"></script>
<style>{CSS}</style>
</head>
<body class="pt-platform" data-pt-normalized="1.1.0" data-pt-enhancer="true" data-special-needs-expansion-v322>
<a class="skip" href="#main">انتقل إلى المحتوى</a>
<header><div class="wrap head"><a href="{BP}">منصة روافد</a><nav aria-label="التنقل"><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">المركز</a><a href="{BP}methodology/">المنهجية</a><a href="{BP}trust/">الثقة والمصادر</a></nav></div></header>
<main id="main">
<section class="hero"><div class="wrap"><p class="eyebrow">{e(guide["category"])}</p><h1>{e(guide["short_title"])}</h1><p class="lead">{e(guide["lead"])}</p><div class="notice"><strong>حدود الاستخدام:</strong> {e(guide["warning"])}</div><p><a class="button" href="{related_url}">فتح الخطة العملية المرتبطة</a><a class="button" href="{BP}special-needs/">العودة إلى المركز</a></p></div></section>
<div class="wrap grid">
<aside class="panel toc"><h2>محتويات الدليل</h2>{toc}<a href="#actions">خطة العمل</a><a href="#urgent">مؤشرات عاجلة</a><a href="#sources">المصادر والمنهج</a></aside>
<article class="stack">
<section class="panel"><h2>لمن أُعد هذا الدليل؟</h2><p>{audiences}</p><p>استخدم الصفحة لتنظيم الأسئلة والأهداف والتعاون مع الفريق، وليس للحكم على شخص أو تقرير الأهلية أو وصف علاج فردي.</p></section>
{''.join(sections_html)}
<section class="panel actions" id="actions"><h2>خطة عمل من ست خطوات</h2><ol>{actions}</ol></section>
<section class="panel urgent" id="urgent"><h2>مؤشرات تستدعي تحركًا عاجلًا</h2><ul>{urgent}</ul><p>عند الخطر المباشر استخدم خدمات الطوارئ المحلية. لا تعتمد على هذه الصفحة لتقدير شدة الحالة عن بُعد.</p></section>
<section class="sources" id="sources"><h2>المصادر والمنهج وحدود المراجعة</h2><p>بُنيت المحاور على إرشادات ومصادر مؤسسية أصلية وإجماع مهني منشور. رُبط كل محور بمعرفات مراجع ظاهرة لتسهيل التدقيق والعودة إلى النص الأصلي. الترجمة والشرح العربيان تحليليان وليسا ترجمة معتمدة من الجهات الناشرة.</p><ol>{sources}</ol><div class="review"><strong>حالة المراجعة:</strong> مراجعة تحريرية ومنهجية داخلية؛ المراجعة الخارجية المتخصصة موصى بها ولم تكتمل. آخر مراجعة: {e(payload["reviewed_at"])}. المراجعة التالية المستهدفة: {e(payload["next_review_due"])}.</div></section>
</article></div></main>
<footer><div class="wrap"><p>محتوى تثقيفي لا يقدم تشخيصًا أو وصفة علاجية أو قرار أهلية. تُراعى الأنظمة والخدمات المحلية ومشاركة الشخص والأسرة.</p></div></footer>
</body></html>'''


def remove_existing_block(source: str) -> str:
    pattern = re.compile(re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END), re.S)
    return pattern.sub("", source)


def hub_block(guides: list[dict[str, Any]], payload: dict[str, Any]) -> str:
    cards = "".join(
        f'''<article class="snv322-card"><p class="snv322-kicker">{e(guide["category"])}</p>
        <h3>{e(guide["short_title"])}</h3><p>{e(guide["meta_description"])}</p>
        <a href="{BP}special-needs/{e(guide["slug"])}/">فتح الدليل العلمي الموسع</a></article>'''
        for guide in guides
    )
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "@id": f"{BASE}/special-needs/#condition-guides-v322",
        "name": "أدلة الحالات الممتدة عبر مراحل العمر",
        "numberOfItems": len(guides),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": guide["short_title"],
                "url": f"{BASE}/special-needs/{guide['slug']}/",
            }
            for index, guide in enumerate(guides, 1)
        ],
    }
    schema = json.dumps(item_list, ensure_ascii=False).replace("</", "<\\/")
    return f'''{MARKER_START}
<style data-special-needs-expansion-v322-style>
.snv322{{margin:34px auto;padding:26px;background:linear-gradient(135deg,#effbf8,#fff2f6);border:1px solid #c6e1de;border-radius:24px}}
.snv322-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin-top:18px}}
.snv322-card{{background:#fff;border:1px solid #c6e1de;border-radius:18px;padding:18px;box-shadow:0 10px 26px rgba(18,63,67,.08)}}
.snv322-card h3{{line-height:1.45;color:#703049}}.snv322-card a{{font-weight:900}}.snv322-kicker{{font-weight:900;color:#823353}}
</style>
<section class="content snv322" id="condition-guides-v322" aria-labelledby="condition-guides-v322-title">
<p class="snv322-kicker">دفعة علمية موسعة — إصدار 322</p>
<h2 id="condition-guides-v322-title">أدلة الحالات عبر مراحل العمر</h2>
<p>خمس صفحات مرجعية جديدة تربط التعريف الدقيق بالتقييم والحالات المصاحبة والدعم في البيت والمدرسة والعمل، مع خطوات عملية ومؤشرات سلامة ومراجع أصلية. لا تقدم الصفحات تشخيصًا ذاتيًا أو خطة علاج فردية.</p>
<div class="snv322-grid">{cards}</div>
<p><small>مراجعة داخلية بتاريخ {e(payload["reviewed_at"])}؛ المراجعة الخارجية المتخصصة موصى بها ولم تكتمل.</small></p>
<script type="application/ld+json">{schema}</script>
</section>
{MARKER_END}'''


def inject_hub(site: Path, guides: list[dict[str, Any]], payload: dict[str, Any]) -> int:
    path = site / "special-needs" / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing special-needs hub: {path}")
    source = remove_existing_block(path.read_text(encoding="utf-8"))
    block = hub_block(guides, payload)
    anchor = "</main>"
    if anchor not in source:
        raise SystemExit("Special-needs hub has no closing main element")
    source = source.replace(anchor, block + "\n" + anchor, 1)
    path.write_text(source, encoding="utf-8")
    rendered = path.read_text(encoding="utf-8")
    if rendered.count(MARKER_START) != 1 or rendered.count(MARKER_END) != 1:
        raise SystemExit("Hub block is not idempotent")
    missing = [guide["slug"] for guide in guides if f"{BP}special-needs/{guide['slug']}/" not in rendered]
    if missing:
        raise SystemExit(f"Hub is missing v322 links: {missing}")
    return len(guides)
