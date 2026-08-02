from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from publish_evidence_literacy_library_v322 import publish as publish_evidence_literacy

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("SITE_BASE", "https://healthrenewal.org/").rstrip("/") + "/"
BASE_PATH = urlparse(BASE).path.rstrip("/") + "/"
TODAY = date.today().isoformat()
SOURCES = [
    ("منظمة الصحة العالمية — التعامل مع الضغط", "https://www.who.int/news-room/questions-and-answers/item/stress"),
    ("منظمة الصحة العالمية — الرعاية الذاتية والصحة", "https://www.who.int/health-topics/self-care"),
    ("UNICEF Parenting — الصحة النفسية ورفاه الأسرة", "https://www.unicef.org/parenting/mental-health-and-well-being"),
    ("UNICEF Parenting — الحوار مع الطفل حول الصحة النفسية", "https://www.unicef.org/parenting/mental-health/how-to-talk-to-kids-mental-health"),
]

CURRENT_PUBLIC_TREES = (
    Path("special-needs/guides"),
    Path("special-needs/practical"),
)


def restore_current_public_trees() -> int:
    copied = 0
    for relative in CURRENT_PUBLIC_TREES:
        source = ROOT / relative
        if not source.is_dir():
            continue
        target = SITE / relative
        before = (
            {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file()}
            if target.is_dir()
            else set()
        )
        shutil.copytree(source, target, dirs_exist_ok=True)
        after = {
            path.relative_to(target).as_posix()
            for path in target.rglob("*")
            if path.is_file()
        }
        copied += len(after - before)
    return copied


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def explain_step(step: str) -> str:
    if any(word in step for word in ("سجل", "اكتب", "راجع", "تابع")):
        return f"حوّل «{step}» إلى ملاحظة قصيرة قابلة للمراجعة. اكتب ما حدث ووقته وأثره، ثم راجع الاتجاه بعد عدة أيام بدل الحكم من موقف واحد."
    if any(word in step for word in ("حدد", "ثبت", "خصص", "ضع", "اتفق")):
        return f"طبّق «{step}» بصيغة محددة: من المسؤول، ومتى يبدأ، وما المدة، وكيف ستعرفون أنه نجح. الوضوح يقلل الجدال والتذكير المتكرر."
    if any(word in step for word in ("اسأل", "استمع", "أعد", "اعترف", "اسمح")):
        return f"عند تنفيذ «{step}» ابدأ بنبرة هادئة، واترك وقتًا للإجابة، ثم لخّص ما فهمته قبل الانتقال إلى النصيحة أو القرار."
    if any(word in step for word in ("قلل", "خفف", "أبعد", "ألغ", "تجنب")):
        return f"نفّذ «{step}» تدريجيًا وحدد بديلًا واضحًا. إزالة السلوك وحدها قد تترك فراغًا يعيد المشكلة، بينما البديل يجعل التغيير قابلًا للاستمرار."
    if any(word in step for word in ("اطلب", "شارك", "وزع", "قدم")):
        return f"اجعل «{step}» طلبًا عمليًا لا عامًا: سمِّ المهمة والشخص والوقت. الطلب المحدد أسهل في القبول والمتابعة من عبارة مبهمة مثل ساعدني."
    return f"ابدأ بخطوة «{step}» في موقف واحد منخفض الضغط. كررها عدة مرات، ثم عدّلها وفق العمر والقدرة والسياق بدل تطبيقها كقاعدة جامدة."


def schema_for(guide: dict, canonical: str) -> str:
    steps = [{"@type": "HowToStep", "position": i + 1, "name": step, "text": explain_step(step)} for i, step in enumerate(guide["tips"])]
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "HowTo", "name": guide["title"], "description": guide["summary"], "inLanguage": "ar", "url": canonical, "step": steps},
        {"@type": "Article", "headline": guide["title"], "description": guide["summary"], "inLanguage": "ar", "dateModified": TODAY, "author": {"@type": "Organization", "name": "مصطلحات علم النفس"}, "publisher": {"@type": "Organization", "name": "مصطلحات علم النفس"}, "mainEntityOfPage": canonical},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
            {"@type": "ListItem", "position": 2, "name": "النصائح", "item": BASE + "tips/"},
            {"@type": "ListItem", "position": 3, "name": guide["title"], "item": canonical},
        ]}
    ]}
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def head(title: str, description: str, canonical: str, schema: str) -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{esc(title)} | مصطلحات علم النفس</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"><meta name="theme-color" content="#67d5cd"><meta name="color-scheme" content="light"><link rel="canonical" href="{esc(canonical)}"><link rel="alternate" hreflang="ar" href="{esc(canonical)}"><link rel="alternate" hreflang="x-default" href="{esc(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><link rel="stylesheet" href="{BASE_PATH}assets/css/theme-v10.css"><link rel="stylesheet" href="{BASE_PATH}assets/css/marshmallow-v12.css"><link rel="stylesheet" href="{BASE_PATH}assets/css/core-v15.css"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="مصطلحات علم النفس"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(canonical)}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema}</script></head>'''


def guide_page(guide: dict) -> str:
    canonical = BASE + "tips/" + guide["slug"] + "/"
    steps = "".join(f'<section class="tips-v15__step"><h3>{esc(step)}</h3><p>{esc(explain_step(step))}</p></section>' for step in guide["tips"])
    sources = "".join(f'<li><a href="{esc(url)}" rel="noopener noreferrer">{esc(name)}</a></li>' for name, url in SOURCES)
    return head(guide["title"], guide["summary"], canonical, schema_for(guide, canonical)) + f'''<body><main class="tips-v15"><header class="tips-v15__hero"><a href="{BASE_PATH}"><img src="{BASE_PATH}assets/logo.svg" alt="مصطلحات علم النفس" style="width:min(290px,82%);height:auto"></a><div class="tips-v15__meta"><span class="tips-v15__badge">{esc(guide['category'])}</span><span class="tips-v15__badge">دليل عملي موسع</span></div><h1>{esc(guide['title'])}</h1><p>{esc(guide['summary'])}</p><nav><a class="button" href="{BASE_PATH}tips/">كل النصائح</a> <a class="button" href="{BASE_PATH}assessment-lab/">المقاييس</a> <a class="button" href="{BASE_PATH}cognitive-lab/">القدرات</a></nav></header><section class="tips-v15__section"><h2>متى يفيد هذا الدليل؟</h2><p>{esc(guide['when'])}</p></section><section class="tips-v15__section"><h2>خطة التنفيذ خطوة بخطوة</h2><div class="tips-v15__steps">{steps}</div></section><section class="tips-v15__section"><h2>جملة جاهزة للاستخدام</h2><blockquote class="tips-v15__quote">{esc(guide['script'])}</blockquote></section><div class="tips-v15__grid"><section class="tips-v15__card"><h2>ما الذي يجب تجنبه؟</h2><p>{esc(guide['avoid'])}</p></section><section class="tips-v15__card"><h2>كيف تعرف أن الخطة تتحسن؟</h2><p>{esc(guide['success'])}</p></section><section class="tips-v15__card"><h2>متى تحتاج إلى مساعدة؟</h2><p>{esc(guide['seek_help'])}</p></section></div><section class="tips-v15__section"><h2>مصادر موثوقة للتوسع</h2><ul class="tips-v15__sources">{sources}</ul><p><small>المحتوى تثقيفي ولا يستبدل التقييم أو العلاج الفردي. في الخطر الفوري استخدم خدمات الطوارئ المحلية.</small></p></section></main><script src="{BASE_PATH}assets/js/app-v10.js" defer></script></body></html>'''


def index_page(guides: list[dict]) -> str:
    canonical = BASE + "tips/"
    cards = "".join(f'<article class="tips-v15__card" data-search="{esc(g["title"] + " " + g["category"] + " " + g["summary"])}"><span class="tips-v15__badge">{esc(g["category"])}</span><h2>{esc(g["title"])}</h2><p>{esc(g["summary"])}</p><a class="button" href="{BASE_PATH}tips/{esc(g["slug"])}/">فتح الدليل الكامل</a></article>' for g in guides)
    schema = json.dumps({"@context":"https://schema.org","@type":"CollectionPage","name":"النصائح النفسية العملية","description":"أدلة عربية موسعة قابلة للتطبيق للأسرة والطفل والمرأة والتعافي والنوم والعلاقات.","url":canonical,"inLanguage":"ar","hasPart":[{"@type":"HowTo","name":g["title"],"url":BASE+"tips/"+g["slug"]+"/"} for g in guides]}, ensure_ascii=False)
    return head("النصائح النفسية العملية", "أدلة عربية موسعة قابلة للتطبيق للأسرة والطفل والمرأة والتعافي والنوم والعلاقات، مع خطوات وجمل جاهزة ومؤشرات تقدم.", canonical, schema) + f'''<body><main class="tips-v15"><header class="tips-v15__hero"><a href="{BASE_PATH}"><img src="{BASE_PATH}assets/logo.svg" alt="مصطلحات علم النفس" style="width:min(300px,82%);height:auto"></a><h1>النصائح النفسية العملية</h1><p>ليست عبارات سريعة أو شعارات عامة. كل دليل يشرح متى تستخدم الخطة، وكيف تنفذها، وما الذي تتجنبه، وكيف تقيس التقدم، ومتى تطلب مساعدة مهنية.</p><input id="tips-search" class="tips-v15__search" type="search" placeholder="ابحث في النصائح والمواقف" aria-label="البحث في النصائح"><nav><a class="button" href="{BASE_PATH}assessment-lab/">المقاييس والمتابعة</a> <a class="button" href="{BASE_PATH}cognitive-lab/">القدرات والألعاب</a></nav></header><section id="tips-grid" class="tips-v15__grid">{cards}</section></main><script>const i=document.getElementById('tips-search'),c=[...document.querySelectorAll('[data-search]')];i?.addEventListener('input',()=>{{const v=i.value.trim().toLowerCase();c.forEach(x=>x.hidden=v&&!x.dataset.search.toLowerCase().includes(v));}});</script><script src="{BASE_PATH}assets/js/app-v10.js" defer></script></body></html>'''


def write_sitemap(guides: list[dict]) -> None:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.Element("urlset", xmlns=ns)
    for link, priority in [(BASE + "tips/", "0.90")] + [(BASE + "tips/" + g["slug"] + "/", "0.75") for g in guides]:
        node = ET.SubElement(root, "url")
        ET.SubElement(node, "loc").text = link
        ET.SubElement(node, "lastmod").text = TODAY
        ET.SubElement(node, "changefreq").text = "monthly"
        ET.SubElement(node, "priority").text = priority
    ET.ElementTree(root).write(SITE / "sitemap-tips.xml", encoding="utf-8", xml_declaration=True)
    index = SITE / "sitemap.xml"
    if index.exists():
        tree = ET.parse(index); current = [x.text for x in tree.getroot().findall("{*}sitemap/{*}loc")]
        target = BASE + "sitemap-tips.xml"
        if target not in current:
            node = ET.SubElement(tree.getroot(), "sitemap"); ET.SubElement(node, "loc").text = target
        tree.write(index, encoding="utf-8", xml_declaration=True)


def main() -> None:
    if not SITE.exists(): raise SystemExit(f"Missing site: {SITE}")
    base_data = json.loads((ROOT / "content/sectors-v10/tips.json").read_text(encoding="utf-8"))
    details = json.loads((ROOT / "content/v15/tips-details-v15.json").read_text(encoding="utf-8"))
    guides = []
    for base in base_data.get("guides", []):
        if base["slug"] not in details: raise SystemExit(f"Missing v15 details for {base['slug']}")
        guides.append({**base, **details[base["slug"]]})
    if len(guides) != 20: raise SystemExit(f"Expected 20 detailed guides, found {len(guides)}")
    (SITE / "assets/css").mkdir(parents=True, exist_ok=True); (SITE / "assets/js").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "content/v15/core-v15.css", SITE / "assets/css/core-v15.css")
    shutil.copy2(ROOT / "content/v15/lab-v15.js", SITE / "assets/js/lab-v12.js")
    tips = SITE / "tips"
    if tips.exists(): shutil.rmtree(tips)
    for guide in guides:
        path = tips / guide["slug"] / "index.html"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(guide_page(guide), encoding="utf-8")
    tips.mkdir(parents=True, exist_ok=True); (tips / "index.html").write_text(index_page(guides), encoding="utf-8")
    for root_name in ("assessment-lab", "cognitive-lab", "assessments", "cognitive-tests"):
        folder = SITE / root_name
        if not folder.exists(): continue
        for page in folder.rglob("*.html"):
            text = page.read_text(encoding="utf-8")
            text = re.sub(r"assets/js/lab-v12\.js(?:\?v=\d+)?", "assets/js/lab-v12.js?v=15", text)
            if "core-v15.css" not in text: text = text.replace("</head>", f'<link rel="stylesheet" href="{BASE_PATH}assets/css/core-v15.css"></head>', 1)
            page.write_text(text, encoding="utf-8")
    write_sitemap(guides)
    evidence = publish_evidence_literacy(SITE)
    if evidence.get("version") != 322 or evidence.get("status") != "passed":
        raise SystemExit({"invalid_evidence_literacy_v322": evidence})
    if evidence.get("guide_count") != 4 or int(evidence.get("minimum_guide_words", 0)) < 900:
        raise SystemExit({"insufficient_evidence_literacy_v322": evidence})
    restored_public_files = restore_current_public_trees()
    sw = SITE / "sw.js"
    if sw.exists(): sw.write_text(sw.read_text(encoding="utf-8").replace("pterminology-v14-performance", "pterminology-v15-core-sections"), encoding="utf-8")
    report = {
        "version": 15,
        "tips_guides": len(guides),
        "tips_min_steps": min(len(g["tips"]) for g in guides),
        "assessment_pages": len(list((SITE / "assessment-lab").glob("*/index.html"))),
        "cognitive_pages": len(list((SITE / "cognitive-lab").glob("*/index.html"))),
        "runtime_marker": "__PTERMINOLOGY_LAB_V15__",
        "color_answer_fixed": True,
        "evidence_literacy_version": evidence["version"],
        "evidence_literacy_guides": evidence["guide_count"],
        "evidence_literacy_minimum_words": evidence["minimum_guide_words"],
        "evidence_literacy_sources": evidence["source_count"],
        "restored_current_public_files": restored_public_files,
    }
    api = SITE / "api"; api.mkdir(exist_ok=True); (api / "core-sections-v15.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
