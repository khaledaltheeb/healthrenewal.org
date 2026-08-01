#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v73" / "special-needs-executable-instructions-ar.json"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://healthrenewal.org"
BASE_PATH = "/"


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


CSS = '''
:root{--ink:#173f45;--muted:#4b6e71;--line:#c7e8e3;--accent:#08776e;--accent2:#8b3f64;--pink:#fff0f6;--mint:#eafff5;--turq:#e7fbf8;--lilac:#f0edff;--white:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:var(--ink);background:linear-gradient(145deg,#fff9fc,var(--turq),var(--lilac))}
a{color:#086e69}.wrap{width:min(1120px,92%);margin:auto}.skip{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px 14px;border:2px solid var(--accent);border-radius:12px;z-index:99}.skip:focus{right:8px}
header,section,article{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:22px;padding:clamp(18px,4vw,34px);margin:16px 0;box-shadow:0 16px 42px rgba(42,119,118,.09)}
header{background:linear-gradient(135deg,var(--pink),var(--turq),var(--lilac))}.nav,.actions{display:flex;gap:10px;flex-wrap:wrap}.nav a,.button{display:inline-block;padding:10px 14px;border:1px solid #7fb8b1;border-radius:13px;background:#fff;text-decoration:none;font-weight:800}
h1{font-size:clamp(2rem,5.5vw,3.8rem);line-height:1.28;margin:.2em 0}h2{color:var(--accent2)}h3{color:var(--accent)}.lead{font-size:1.12rem;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{display:flex;flex-direction:column}.card p{flex:1;color:var(--muted)}
.notice{border-right:6px solid var(--accent2);background:var(--pink)}.review{border-right:6px solid var(--accent);background:var(--mint)}.example{background:#fffaf0;border:1px solid #ead9aa;border-radius:15px;padding:14px;margin:10px 0}
table{width:100%;border-collapse:collapse}th,td{border:1px solid #b9d8d4;padding:9px;text-align:right;vertical-align:top}.print-card{border:2px dashed var(--accent);background:#fff}
footer{padding:28px 0 48px;color:var(--muted)}a:focus-visible{outline:3px solid #1b6cff;outline-offset:4px}
@media(max-width:850px){.grid,.cards{grid-template-columns:1fr}.nav{display:grid}}@media print{.nav,.actions,.skip{display:none!important}body{background:#fff}header,section,article{box-shadow:none;break-inside:avoid}.print-card{break-inside:auto}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''.strip()


def head(title: str, description: str, canonical: str, schema: dict[str, Any]) -> str:
    schema_json = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    return f'''<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="theme-color" content="#72d8cf">
<meta name="color-scheme" content="light">
<link rel="canonical" href="{e(canonical)}">
<link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<meta property="og:type" content="article">
<meta property="og:locale" content="ar_AR">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(description)}">
<script type="application/ld+json">{schema_json}</script>
<style>{CSS}</style>
</head>'''


def nav() -> str:
    return f'''<nav class="nav" aria-label="التنقل الرئيسي">
<a href="{BASE_PATH}">الرئيسية</a>
<a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a>
<a href="{BASE_PATH}sectors/family/">الأسرة</a>
<a href="{BASE_PATH}care-guides/">أدلة التعامل</a>
<a href="{BASE_PATH}encyclopedia/">الموسوعة</a>
<a href="{BASE_PATH}trust/">الثقة والمنهج</a>
</nav>'''


def source_list(data: dict[str, Any]) -> str:
    items = []
    for source in data["sources"]:
        items.append(
            f'<li><a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["organization"])} — {e(source["title"])}</a>'
            f'<br><span>{e(source["use"])}</span> <small>(تم الوصول: {e(source["accessed_at"])})</small></li>'
        )
    return "<ul>" + "".join(items) + "</ul>"


def common_schema(data: dict[str, Any], canonical: str, name: str, page_type: str) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": page_type,
                "name": name,
                "description": data["summary"],
                "inLanguage": "ar",
                "url": canonical,
                "dateModified": data["reviewed_at"],
                "isPartOf": {"@type": "WebSite", "name": "مصطلحات علم النفس", "url": BASE + "/"},
                "citation": [source["url"] for source in data["sources"]],
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
                    {"@type": "ListItem", "position": 3, "name": name, "item": canonical},
                ],
            },
        ],
    }


def render_center(data: dict[str, Any]) -> str:
    canonical = BASE + "/special-needs/"
    title = "ذوو الاحتياجات الخاصة والتربية الدامجة | مصطلحات علم النفس"
    description = "مركز عربي منظم للمعلومات والأدلة والأدوات الموجهة للأشخاص ذوي الاحتياجات الخاصة وأسرهم ومعلميهم ومقدمي الخدمات، مع قواعد للكرامة والسلامة والمصادر."
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "مركز ذوي الاحتياجات الخاصة والتربية الدامجة",
        "description": description,
        "inLanguage": "ar",
        "url": canonical,
        "dateModified": data["reviewed_at"],
        "hasPart": [{"@type": "Course", "name": data["title_ar"], "url": BASE + "/special-needs/" + data["slug"] + "/"}],
    }
    return f'''<!doctype html><html lang="ar" dir="rtl">{head(title, description, canonical, schema)}<body>
<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a><div class="wrap">{nav()}<main id="main">
<header><p><strong>قسم أساسي في المنصة</strong></p><h1>ذوو الاحتياجات الخاصة والتربية الدامجة</h1>
<p class="lead">معلومات عملية للأشخاص ذوي الاحتياجات الخاصة وذوي احتياجات الدعم الإضافية، وللأسر والمعلمين ومقدمي الرعاية والخدمات. يبنى القسم على الكرامة والمشاركة واللغة غير الوصمية وإزالة الحواجز، لا على الشفقة أو اختزال الإنسان في تشخيص.</p>
<p><strong>آخر مراجعة:</strong> <time datetime="{e(data["reviewed_at"])}">{e(data["reviewed_at"])}</time></p></header>
<section class="notice"><h2>الحدود المهنية</h2><p>{e(data["professional_limits"])}</p><p>حالة المادة الحالية: تحتاج مراجعة خارجية متخصصة، ولا توجد دعوى اعتماد أو مراجعة سريرية.</p></section>
<section><h2>المسارات التي سيغطيها المركز</h2><div class="cards">
<article class="card"><h3>التربية الدامجة</h3><p>تكييف التعليمات والواجبات والبيئة الصفية وطرق المشاركة، مع قياس الأثر بدل الحكم على شخصية الطالب.</p><a href="{BASE_PATH}special-needs/{e(data["slug"])}/">فتح الوحدة المنشورة</a></article>
<article class="card"><h3>التواصل والإتاحة</h3><p>التواصل البديل والمعزز، السمع والبصر، اللغة المبسطة، المواد القابلة للقراءة، واحترام طريقة التواصل المفضلة.</p><a href="{BASE_PATH}special-needs/">استكشاف موارد التواصل والإتاحة</a></article>
<article class="card"><h3>الأسرة ومقدم الرعاية</h3><p>خطط يومية، انتقالات، نوم، تعليم، حماية من الاستغلال، دعم الإخوة، وتوزيع المسؤوليات دون إلقاء العبء على شخص واحد.</p><a href="{BASE_PATH}care-guides/">فتح الأدلة الأسرية العملية</a></article>
<article class="card"><h3>الحقوق والحماية</h3><p>مبادئ عامة للسلامة والموافقة والخصوصية والتنمر والإساءة، مع تجنب تقديم تفسير قانوني موحد لجميع البلدان.</p><a href="{BASE_PATH}trust/">قراءة منهج الثقة</a></article>
</div></section>
<section class="review"><h2>أول وحدة منشورة</h2><h3>{e(data["title_ar"])}</h3><p>{e(data["summary"])}</p><p><a class="button" href="{BASE_PATH}special-needs/{e(data["slug"])}/">الدخول إلى الوحدة</a></p></section>
<section><h2>مصادر الوحدة الحالية</h2>{source_list(data)}</section>
</main><footer><p>© مصطلحات علم النفس — محتوى تثقيفي منظم، لا يستبدل التقييم والخدمات المحلية المتخصصة.</p></footer></div></body></html>'''


def render_course(data: dict[str, Any]) -> str:
    slug = data["slug"]
    canonical = BASE + f"/special-needs/{slug}/"
    title = data["title_ar"] + " | مصطلحات علم النفس"
    schema = common_schema(data, canonical, data["title_ar"], "Course")
    schema["@graph"][0].update({
        "provider": {"@type": "Organization", "name": "مصطلحات علم النفس", "url": BASE + "/"},
        "educationalLevel": data["age_groups"],
        "timeRequired": data["duration"],
        "learningResourceType": "وحدة تدريبية",
    })
    outcomes = "".join(f"<li>{e(item)}</li>" for item in data["learning_outcomes"])
    principles = "".join(f'<article><h3>{e(item["principle"])}</h3><p>{e(item["explanation"])}</p></article>' for item in data["core_principles"])
    units = "".join(
        f'<article class="card"><h3>الوحدة {unit["number"]}: {e(unit["title"])}</h3><p>{e(unit["explanation"][0])}</p><a href="{BASE_PATH}special-needs/{e(slug)}/unit-{unit["number"]}/">فتح الوحدة</a></article>'
        for unit in data["units"]
    )
    scenarios = "".join(
        f'<article><h3>موقف تطبيقي</h3><p><strong>الموقف:</strong> {e(item["scenario"])}</p><p><strong>الاستجابة الأنسب:</strong> {e(item["best_response"])}</p><p><strong>ما يجب تجنبه:</strong> {e(item["avoid"])}</p></article>'
        for item in data["scenario_assessment"]
    )
    fields = "".join(f"<li>{e(item)}</li>" for item in data["printable"]["fields"])
    help_items = "".join(f"<li>{e(item)}</li>" for item in data["when_to_seek_help"])
    notes = "".join(f"<li>{e(item)}</li>" for item in data["editorial_notes"])
    return f'''<!doctype html><html lang="ar" dir="rtl">{head(title, data["summary"], canonical, schema)}<body>
<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a><div class="wrap">{nav()}<main id="main">
<header><p><strong>{e(data["center"])}</strong></p><h1>{e(data["title_ar"])}</h1><p class="lead">{e(data["summary"])}</p>
<p><strong>الجمهور:</strong> {e("، ".join(data["audiences"]))}</p><p><strong>المدة:</strong> {e(data["duration"])}</p>
<p><strong>آخر مراجعة:</strong> <time datetime="{e(data["reviewed_at"])}">{e(data["reviewed_at"])}</time> — <strong>الحالة:</strong> تحتاج مراجعة خارجية متخصصة.</p></header>
<section class="notice"><h2>الغرض والحدود</h2><p>{e(data["professional_limits"])}</p><p>لا تنسب كل صعوبة في بدء المهمة أو الانتقال إلى ADHD أو صعوبة تعلم. راجع الفهم واللغة والألم والمرض والنوم والحواس والبيئة والضغط والتنمر والتواصل.</p></section>
<section><h2>نواتج التعلم</h2><ul>{outcomes}</ul></section>
<section><h2>المبادئ الأساسية</h2><div class="grid">{principles}</div></section>
<section><h2>الوحدات الثلاث</h2><div class="cards">{units}</div></section>
<section><h2>مواقف تطبيقية</h2>{scenarios}</section>
<section class="print-card"><h2>{e(data["printable"]["title"])}</h2><p>{e(data["printable"]["instructions"])}</p><ul>{fields}</ul><p class="actions"><button type="button" onclick="window.print()">طباعة البطاقة</button></p></section>
<section class="review"><h2>متى يلزم دعم إضافي؟</h2><ul>{help_items}</ul></section>
<section><h2>المصادر</h2>{source_list(data)}</section>
<section><h2>ملاحظات تحريرية</h2><ul>{notes}</ul></section>
</main><footer><p><a href="{BASE_PATH}special-needs/">العودة إلى مركز ذوي الاحتياجات الخاصة</a></p></footer></div></body></html>'''


def render_unit(data: dict[str, Any], unit: dict[str, Any]) -> str:
    slug = data["slug"]
    number = unit["number"]
    canonical = BASE + f"/special-needs/{slug}/unit-{number}/"
    page_title = f'الوحدة {number}: {unit["title"]} | مصطلحات علم النفس'
    description = unit["explanation"][0]
    schema = common_schema(data, canonical, f'الوحدة {number}: {unit["title"]}', "LearningResource")
    objectives = "".join(f"<li>{e(item)}</li>" for item in unit["objectives"])
    explanation = "".join(f"<p>{e(item)}</p>" for item in unit["explanation"])
    practice = "".join(f"<li>{e(item)}</li>" for item in unit["practice"])
    checklist = "".join(f"<li>{e(item)}</li>" for item in unit["checklist"])
    extras = ""
    if unit.get("before_after_examples"):
        rows = "".join(f'<tr><td>{e(item["before"])}</td><td>{e(item["after"])}</td></tr>' for item in unit["before_after_examples"])
        extras += f'<section><h2>أمثلة قبل وبعد</h2><div style="overflow:auto"><table><thead><tr><th>عبارة عامة</th><th>صياغة قابلة للتنفيذ</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    if unit.get("worked_example"):
        steps = "".join(f"<li>{e(item)}</li>" for item in unit["worked_example"]["steps"])
        extras += f'<section><h2>مثال محلول: {e(unit["worked_example"]["task"])}</h2><ol>{steps}</ol></section>'
    if unit.get("transition_protocol"):
        steps = "".join(f"<li>{e(item)}</li>" for item in unit["transition_protocol"])
        extras += f'<section><h2>بروتوكول الانتقال</h2><ol>{steps}</ol></section>'
    if unit.get("feedback_examples"):
        examples = "".join(f'<div class="example">{e(item)}</div>' for item in unit["feedback_examples"])
        extras += f'<section><h2>أمثلة للتغذية الراجعة</h2>{examples}</section>'
    prev_link = f'{BASE_PATH}special-needs/{slug}/unit-{number-1}/' if number > 1 else f'{BASE_PATH}special-needs/{slug}/'
    next_link = f'{BASE_PATH}special-needs/{slug}/unit-{number+1}/' if number < len(data["units"]) else f'{BASE_PATH}special-needs/{slug}/'
    return f'''<!doctype html><html lang="ar" dir="rtl">{head(page_title, description, canonical, schema)}<body>
<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a><div class="wrap">{nav()}<main id="main">
<header><p><strong>{e(data["title_ar"])}</strong></p><h1>الوحدة {number}: {e(unit["title"])}</h1><p class="lead">{e(description)}</p>
<p><strong>آخر مراجعة:</strong> <time datetime="{e(data["reviewed_at"])}">{e(data["reviewed_at"])}</time></p></header>
<section class="notice"><h2>قبل البدء</h2><p>{e(data["professional_limits"])}</p></section>
<section><h2>الأهداف</h2><ul>{objectives}</ul></section>
<section><h2>الشرح العملي</h2>{explanation}</section>
{extras}
<section><h2>تطبيق عملي</h2><ol>{practice}</ol></section>
<section class="review"><h2>قائمة تحقق غير تشخيصية</h2><ul>{checklist}</ul></section>
<section><h2>المصادر المرتبطة</h2>{source_list(data)}</section>
<div class="actions"><a class="button" href="{e(prev_link)}">السابق</a><a class="button" href="{BASE_PATH}special-needs/{e(slug)}/">فهرس الوحدة</a><a class="button" href="{e(next_link)}">التالي</a></div>
</main><footer><p>لا تستخدم نتائج التطبيق لتشخيص الطالب أو لتحديد أهليته القانونية للخدمات.</p></footer></div></body></html>'''


def validate(data: dict[str, Any]) -> None:
    required = {"version", "slug", "title_ar", "summary", "reviewed_at", "review_status", "professional_limits", "units", "sources"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing content fields: {sorted(missing)}")
    if data["review_status"] != "needs-external-review":
        raise SystemExit("The recovered course must retain an honest external-review status")
    if len(data["units"]) != 3:
        raise SystemExit("Expected exactly three complete units")
    if len(data["sources"]) < 4:
        raise SystemExit("Expected at least four institutional sources")
    if len({unit["number"] for unit in data["units"]}) != 3:
        raise SystemExit("Unit numbers must be unique")
    if any(not source["url"].startswith("https://") for source in data["sources"]):
        raise SystemExit("All sources must use HTTPS")


def patch_homepage(site: Path, data: dict[str, Any]) -> dict[str, bool]:
    path = site / "index.html"
    text = path.read_text(encoding="utf-8")
    nav_link = '<a href="special-needs/">ذوو الاحتياجات الخاصة</a>'
    nav_added = False
    card_added = False
    if nav_link not in text:
        marker = '<a href="sectors/family/">الأسرة</a>'
        if marker not in text:
            raise SystemExit("Homepage family navigation marker missing")
        text = text.replace(marker, marker + nav_link, 1)
        nav_added = True
    if 'data-special-needs-v73' not in text:
        pattern = re.compile(r'(<article class="card"><h3>الأسرة والطفل</h3>.*?</article>)', re.S)
        card = (
            '<article class="card" data-special-needs-v73><h3>ذوو الاحتياجات الخاصة</h3>'
            '<p>مركز أساسي للأشخاص ذوي الاحتياجات الخاصة وأسرهم ومعلميهم ومقدمي الخدمات: تعليم دامج، تواصل، حماية، أدوات وأدلة عملية.</p>'
            '<a href="special-needs/">دخول المركز</a></article>'
        )
        text, count = pattern.subn(r"\1" + card, text, count=1)
        if count != 1:
            raise SystemExit("Homepage family card marker missing")
        card_added = True
    path.write_text(text, encoding="utf-8")
    return {"nav_added": nav_added, "card_added": card_added}


def write_sitemap(site: Path, data: dict[str, Any]) -> tuple[int, str]:
    urls = [BASE + "/special-needs/", BASE + f'/special-needs/{data["slug"]}/']
    urls += [BASE + f'/special-needs/{data["slug"]}/unit-{unit["number"]}/' for unit in data["units"]]
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    child = site / "sitemap-special-needs.xml"
    root = ET.Element(f"{{{ns}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = data["reviewed_at"]
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "monthly"
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)

    main = site / "sitemap.xml"
    tree = ET.parse(main)
    root = tree.getroot()
    local = root.tag.rsplit("}", 1)[-1]
    if local == "sitemapindex":
        target = BASE + "/sitemap-special-needs.xml"
        existing = {node.text for node in root.findall(f"{{{ns}}}sitemap/{{{ns}}}loc") if node.text}
        if target not in existing:
            entry = ET.SubElement(root, f"{{{ns}}}sitemap")
            ET.SubElement(entry, f"{{{ns}}}loc").text = target
        mode = "sitemapindex"
    elif local == "urlset":
        existing = {node.text for node in root.findall(f"{{{ns}}}url/{{{ns}}}loc") if node.text}
        for url in urls:
            if url not in existing:
                entry = ET.SubElement(root, f"{{{ns}}}url")
                ET.SubElement(entry, f"{{{ns}}}loc").text = url
        mode = "urlset"
    else:
        raise SystemExit(f"Unsupported sitemap root: {local}")
    tree.write(main, encoding="utf-8", xml_declaration=True)
    return len(urls), mode


def publish(site: Path = SITE) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    validate(data)
    center = site / "special-needs"
    course = center / data["slug"]
    center.mkdir(parents=True, exist_ok=True)
    course.mkdir(parents=True, exist_ok=True)
    (center / "index.html").write_text(render_center(data), encoding="utf-8")
    (course / "index.html").write_text(render_course(data), encoding="utf-8")
    generated = ["special-needs/index.html", f'special-needs/{data["slug"]}/index.html']
    for unit in data["units"]:
        target = course / f'unit-{unit["number"]}'
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(render_unit(data, unit), encoding="utf-8")
        generated.append(f'special-needs/{data["slug"]}/unit-{unit["number"]}/index.html')
    homepage = patch_homepage(site, data)
    sitemap_urls, sitemap_mode = write_sitemap(site, data)
    report = {
        "version": 73,
        "center": "special-needs",
        "generated_pages": generated,
        "generated_page_count": len(generated),
        "course_count": 1,
        "unit_count": len(data["units"]),
        "source_count": len(data["sources"]),
        "review_status": data["review_status"],
        "homepage": homepage,
        "sitemap_urls": sitemap_urls,
        "sitemap_mode": sitemap_mode,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-v73.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    publish()
