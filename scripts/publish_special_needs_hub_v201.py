#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v201" / "special-needs-hub-ar.json"
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
OUTSIDE_BOX_START = "<!-- outside-the-box-v254:start -->"
OUTSIDE_BOX_END = "<!-- outside-the-box-v254:end -->"

RESOURCE_CANDIDATES = (
    ("executable-instructions-adhd-learning-difficulties", "من التعليمات العامة إلى خطوات قابلة للتنفيذ", "وحدة عملية لتجزئة التعليمات والواجبات والانتقالات ودعم الطلاب في الصف والمنزل."),
    ("inclusive-language-disability", "دليل اللغة الدامجة والمحترمة", "مرجع للأسرة والمعلم والكاتب لاختيار لغة دقيقة تحترم تفضيل الشخص وتصف الحواجز دون وصم."),
    ("caregiver-wellbeing", "صحة مقدم الرعاية", "خطة عملية لملاحظة الضغط وتوزيع المسؤوليات وطلب الدعم وحماية استمرارية الرعاية."),
    ("accessible-arabic-digital-content", "المحتوى العربي الرقمي الأكثر إتاحة", "إرشادات للعناوين والروابط والصور والنماذج ولوحة المفاتيح وقارئات الشاشة."),
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def validate(data: dict[str, Any]) -> None:
    required = {"title", "description", "review_status", "reviewed_at", "professional_limits", "intro", "pathways", "sources"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing special-needs hub fields: {sorted(missing)}")
    if data["review_status"] != "internally-reviewed":
        raise SystemExit("Special-needs hub must retain an honest internally-reviewed status")
    if len(data["pathways"]) != 16:
        raise SystemExit(f"Expected 16 complete pathways, found {len(data['pathways'])}")
    if len({item["id"] for item in data["pathways"]}) != len(data["pathways"]):
        raise SystemExit("Special-needs pathway IDs must be unique")
    if len(data["sources"]) < 4:
        raise SystemExit("Expected at least four authoritative sources")
    for item in data["pathways"]:
        if len(item.get("actions", [])) < 4 or len(item.get("audiences", [])) < 2:
            raise SystemExit(f"Incomplete pathway: {item.get('id')}")
    if any(not source["url"].startswith("https://") for source in data["sources"]):
        raise SystemExit("All special-needs hub sources must use HTTPS")


def existing_resources(site: Path) -> list[dict[str, str]]:
    result = []
    for slug, title, description in RESOURCE_CANDIDATES:
        target = site / "special-needs" / slug / "index.html"
        if target.is_file():
            result.append({"slug": slug, "title": title, "description": description})
    return result


def schemas(data: dict[str, Any], resources: list[dict[str, str]]) -> str:
    canonical = BASE + "/special-needs/"
    graph = [
        {
            "@type": "CollectionPage",
            "name": data["title"],
            "description": data["description"],
            "inLanguage": "ar",
            "url": canonical,
            "dateModified": data["reviewed_at"],
            "publisher": {"@type": "Organization", "name": BRAND, "url": BASE + "/"},
            "hasPart": [
                {"@type": "WebPage", "name": item["title"], "url": canonical + "#" + item["id"]}
                for item in data["pathways"]
            ] + [
                {"@type": "Article", "name": item["title"], "url": canonical + item["slug"] + "/"}
                for item in resources
            ],
            "citation": [source["url"] for source in data["sources"]],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": data["title"], "item": canonical},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def render(data: dict[str, Any], resources: list[dict[str, str]]) -> str:
    canonical = BASE + "/special-needs/"
    intro = "".join(f"<p>{esc(item)}</p>" for item in data["intro"])
    cards = "".join(
        f'''<article class="path-card" data-search="{esc(item['title'] + ' ' + ' '.join(item['keywords']) + ' ' + ' '.join(item['audiences']))}">
        <p class="audience">{esc(' · '.join(item['audiences']))}</p><h2><a href="#{esc(item['id'])}">{esc(item['title'])}</a></h2><p>{esc(item['summary'])}</p><a class="text-link" href="#{esc(item['id'])}">فتح المسار التفصيلي</a></article>'''
        for item in data["pathways"]
    )
    sections = "".join(
        f'''<section class="detail" id="{esc(item['id'])}"><div><p class="eyebrow">مسار مصنف</p><h2>{esc(item['title'])}</h2><p>{esc(item['summary'])}</p><p><strong>يخدم:</strong> {esc('، '.join(item['audiences']))}</p></div><div><h3>ابدأ بهذه الخطوات</h3><ol>{''.join(f'<li>{esc(action)}</li>' for action in item['actions'])}</ol><p class="keywords"><strong>كلمات المسار:</strong> {esc('، '.join(item['keywords']))}</p></div></section>'''
        for item in data["pathways"]
    )
    resource_html = "".join(
        f'''<article class="resource"><h3>{esc(item['title'])}</h3><p>{esc(item['description'])}</p><a class="button secondary" href="{BASE_PATH}special-needs/{esc(item['slug'])}/">فتح المادة المنشورة</a></article>'''
        for item in resources
    ) or '<p class="notice">لا توجد مواد فرعية منشورة في هذه الحزمة بعد. يظهر هذا التنبيه فقط عندما تكون ملفات المواد غير موجودة فعلًا.</p>'
    sources = "".join(
        f'''<li><a href="{esc(source['url'])}" rel="noopener noreferrer">{esc(source['organization'])} — {esc(source['title'])}</a><br><span>{esc(source['use'])}</span></li>'''
        for source in data["sources"]
    )
    outside_box = f'''{OUTSIDE_BOX_START}
<section class="section" data-outside-the-box-v254 aria-labelledby="outside-the-box-title"><p class="eyebrow">لمقدم الخدمة</p><h2 id="outside-the-box-title">أفكار خارج الصندوق</h2>
<p>مئة مسار مؤسسي تربط تحديد الحالة والاختبارات المناسبة والتقييم الوظيفي بثلاث أفكار ذات جرعة وقياس وقاعدة توقف، ثم جدول متابعة وإعادة تقييم وخطة بديلة.</p>
<div class="outside-box-resources-v254"><article class="outside-box-resource-v254"><h3>الدليل الكامل للحالات</h3><p>ترتيب تخطيطي يبدأ بالحالات الأعلى حضورًا ثم ينتقل إلى الحالات النادرة، مع بيان حدود المقارنة والانتشار.</p><a class="button" href="{BASE_PATH}outside-the-box/">تصفح 100 حالة</a></article>
<article class="outside-box-resource-v254"><h3>المنهجية ومصفوفة المتابعة</h3><p>حقوق الاختبارات، حدود النقل إلى العربية، وسجل BTR‑ICF المحلي غير التشخيصي.</p><a class="button secondary" href="{BASE_PATH}outside-the-box/methodology/">قراءة المنهجية</a> <a class="button secondary" href="{BASE_PATH}outside-the-box/monitoring-matrix/">فتح المصفوفة</a></article></div>
</section>
{OUTSIDE_BOX_END}'''
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(data['title'])} | {BRAND}</title><meta name="description" content="{esc(data['description'])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><meta name="theme-color" content="#0b6b66"><meta name="color-scheme" content="light"><link rel="canonical" href="{canonical}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{esc(data['title'])}"><meta property="og:description" content="{esc(data['description'])}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(data['title'])}"><meta name="twitter:description" content="{esc(data['description'])}"><script type="application/ld+json">{schemas(data, resources)}</script>
<style>:root{{--ink:#173f45;--muted:#4c7073;--line:#c6e5e1;--brand:#08766e;--accent:#9b456d;--soft:#e9fbf8;--pink:#fff0f6;--lilac:#f1edff;--white:#fff;--shadow:0 16px 42px rgba(34,107,105,.10)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:var(--ink);background:linear-gradient(145deg,#fff,var(--soft),var(--lilac))}}a{{color:#076a64}}a:focus-visible,input:focus-visible{{outline:3px solid #168f88;outline-offset:3px}}.wrap{{width:min(1180px,92%);margin:auto}}.skip{{position:absolute;right:-9999px}}.skip:focus{{right:10px;top:10px;background:#fff;padding:10px;z-index:20}}.site-header{{display:flex;justify-content:space-between;gap:16px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}}.brand{{font-weight:900;text-decoration:none;color:var(--ink)}}nav{{display:flex;gap:9px;flex-wrap:wrap}}nav a{{font-weight:800;text-decoration:none;padding:7px 9px;border-radius:10px}}.hero{{padding:58px 0 24px}}.eyebrow{{color:var(--accent);font-weight:900}}h1{{font-size:clamp(2.2rem,6vw,4.6rem);line-height:1.22;margin:.15em 0}}.lead{{font-size:1.15rem;color:var(--muted);max-width:930px}}.notice{{border-right:6px solid var(--accent);background:var(--pink);padding:17px 20px;border-radius:16px}}.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}.stat,.path-card,.detail,.resource,.outside-box-resource-v254,.sources{{background:rgba(255,255,255,.95);border:1px solid var(--line);border-radius:20px;padding:20px;box-shadow:var(--shadow)}}.stat strong{{display:block;font-size:1.7rem;color:var(--accent)}}.toolbar{{display:flex;gap:10px;align-items:end;flex-wrap:wrap;margin:20px 0}}.field{{display:grid;gap:6px;flex:1;min-width:250px}}.field span{{font-weight:900}}input{{border:1px solid #9ecdc7;border-radius:13px;padding:12px;font:inherit}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.path-card{{display:flex;flex-direction:column}}.path-card:nth-child(3n+1){{background:linear-gradient(145deg,#fff,var(--pink))}}.path-card:nth-child(3n+2){{background:linear-gradient(145deg,#fff,var(--soft))}}.path-card:nth-child(3n){{background:linear-gradient(145deg,#fff,var(--lilac))}}.path-card h2{{font-size:1.25rem;margin:.25em 0}}.path-card p{{color:var(--muted)}}.audience{{font-size:.85rem;font-weight:800}}.text-link{{margin-top:auto;font-weight:900}}.section{{padding:36px 0}}.detail{{display:grid;grid-template-columns:.8fr 1.2fr;gap:24px;margin:16px 0;scroll-margin-top:20px}}.detail h2{{color:var(--accent)}}.detail h3{{color:var(--brand)}}.keywords{{color:var(--muted)}}.resources,.outside-box-resources-v254{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}.button{{display:inline-block;text-decoration:none;font-weight:900;padding:10px 14px;border-radius:12px;background:var(--brand);color:#fff}}.button.secondary{{background:#fff;color:var(--brand);border:1px solid var(--line)}}.sources li{{margin:12px 0}}footer{{border-top:1px solid var(--line);padding:30px 0 50px;color:var(--muted)}}[hidden]{{display:none!important}}@media(max-width:900px){{.grid,.stats,.detail,.resources,.outside-box-resources-v254{{grid-template-columns:1fr}}.site-header{{align-items:flex-start;flex-direction:column}}}}@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}@media print{{nav,.toolbar,.skip{{display:none!important}}body{{background:#fff}}.path-card,.detail,.resource,.outside-box-resource-v254,.sources,.stat{{box-shadow:none;break-inside:avoid}}}}</style></head><body>
<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a><div class="wrap"><header class="site-header"><a class="brand" href="{BASE_PATH}">{BRAND}<br><small>{SLOGAN}</small></a><nav aria-label="التنقل الرئيسي"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}start-here/">ابدأ من هنا</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}care-guides/">أدلة التعامل</a><a href="{BASE_PATH}provider-assessment-demo/">منصة التقييم</a></nav></header><main id="main">
<section class="hero"><p class="eyebrow">مركز أساسي واسع ومصنف</p><h1>{esc(data['title'])}</h1><p class="lead">{esc(data['description'])}</p>{intro}<div class="notice"><strong>حدود الاستخدام:</strong> {esc(data['professional_limits'])}<br><strong>حالة المراجعة:</strong> مراجعة داخلية؛ المراجعة الخارجية المتخصصة موصى بها ولم تُدعَ على أنها مكتملة.</div></section>
<section class="stats" aria-label="حجم المركز"><article class="stat"><strong>{len(data['pathways'])}</strong><span>مسارًا رئيسيًا</span></article><article class="stat"><strong>{len(resources)}</strong><span>مواد فرعية موجودة فعليًا</span></article><article class="stat"><strong>{len(data['sources'])}</strong><span>مصادر مؤسسية</span></article><article class="stat"><strong>RTL + WCAG</strong><span>بنية عربية وإتاحة</span></article></section>
<section class="section" aria-labelledby="paths-title"><p class="eyebrow">ابدأ من السؤال أو المجال</p><h2 id="paths-title">المسارات الرئيسية</h2><p>استخدم البحث لتصفية العناوين والجمهور والكلمات المرتبطة. كل بطاقة تنتقل إلى شرح وخطوات عملية داخل الصفحة، لذلك لا توجد تبويبات فارغة أو روابط وعود.</p><div class="toolbar"><label class="field"><span>البحث داخل المركز</span><input id="hub-search" type="search" placeholder="التربية الدامجة، التواصل، الحماية، العمل..."></label><button class="button secondary" id="clear-search" type="button">مسح البحث</button></div><div class="grid" id="path-grid">{cards}</div></section>
<section class="section" aria-labelledby="details-title"><p class="eyebrow">تفاصيل قابلة للاستخدام</p><h2 id="details-title">دليل كل مسار</h2>{sections}</section>
{outside_box}
<section class="section" aria-labelledby="resources-title"><p class="eyebrow">مواد موجودة في حزمة الإنتاج</p><h2 id="resources-title">أدلة ووحدات مرتبطة</h2><div class="resources">{resource_html}</div></section>
<section class="section sources" aria-labelledby="sources-title"><h2 id="sources-title">المصادر والمنهج</h2><p>تُستخدم المصادر لبناء الإطار العام ولا تعني أن الجهات المذكورة تراجع المنصة أو تعتمد محتواها.</p><ul>{sources}</ul><p><strong>آخر مراجعة داخلية:</strong> <time datetime="{esc(data['reviewed_at'])}">{esc(data['reviewed_at'])}</time>.</p></section>
</main><footer><p><strong>{BRAND}</strong> — {SLOGAN}</p><p><a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}partners/">الشركاء والشفافية</a> · <a href="{BASE_PATH}special-needs/inclusive-language-disability/">اللغة الدامجة</a></p></footer></div>
<script>const input=document.getElementById('hub-search'),cards=[...document.querySelectorAll('[data-search]')],clear=document.getElementById('clear-search');function filter(){{const q=input.value.trim().toLowerCase();cards.forEach(card=>card.hidden=q&&!card.dataset.search.toLowerCase().includes(q));}}input.addEventListener('input',filter);clear.addEventListener('click',()=>{{input.value='';filter();input.focus();}});</script></body></html>'''


def ensure_sitemap(site: Path, modified: str) -> None:
    sitemap = site / "sitemap-special-needs.xml"
    canonical = BASE + "/special-needs/"
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    if sitemap.is_file():
        tree = ET.parse(sitemap)
        root = tree.getroot()
    else:
        root = ET.Element(f"{{{ns}}}urlset")
        tree = ET.ElementTree(root)
    urls = {node.text for node in root.findall(f"{{{ns}}}url/{{{ns}}}loc") if node.text}
    if canonical not in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = canonical
        ET.SubElement(node, f"{{{ns}}}lastmod").text = modified
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "weekly"
        ET.SubElement(node, f"{{{ns}}}priority").text = "0.95"
    tree.write(sitemap, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> Path:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    validate(data)
    resources = existing_resources(site)
    output = site / "special-needs" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data, resources), encoding="utf-8")
    ensure_sitemap(site, data["reviewed_at"])
    report = {
        "version": 201,
        "status": "built-not-published",
        "pathways": len(data["pathways"]),
        "existing_resources": len(resources),
        "resources": resources,
        "review_status": data["review_status"],
        "external_review": data["external_review"],
        "source_count": len(data["sources"]),
        "placeholder_phrases": [],
        "output": "special-needs/index.html"
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-hub-v201.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing site directory: {args.site}")
    output = publish(args.site.resolve())
    print(json.dumps({"status": "built-not-published", "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
