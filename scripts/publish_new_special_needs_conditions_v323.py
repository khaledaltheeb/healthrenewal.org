#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v323" / "new-special-needs-conditions-ar.json"
BASE = "https://healthrenewal.org/"
BP = "/"
VERSION = 323
HUB_MARKER = "data-genetic-developmental-v323"
HUB_INSERT = '<section class="section" id="method">'
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
UNSUPPORTED = re.compile(r"(?:علاج مضمون|شفاء مضمون|يشخّصك|يغني عن الطبيب|نتائج مؤكدة للجميع)")
EXPECTED = ("rett-syndrome", "fragile-x-syndrome", "angelman-syndrome")
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"

CSS = '''
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#173f43;background:#f5faf9;line-height:1.9}
a{color:#075f5a}.wrap{width:min(1160px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;color:#173f43;padding:10px;z-index:50}
header{background:#123e43;color:#fff}.head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:12px 0}.head a{color:#fff;text-decoration:none;font-weight:800}nav{display:flex;gap:12px;flex-wrap:wrap}
.hero{background:linear-gradient(135deg,#e7f6f3,#fff);padding:56px 0 34px;border-bottom:1px solid #c9e1de}h1{font-size:clamp(2rem,5vw,4rem);line-height:1.25;margin:.2em 0}h2{font-size:clamp(1.4rem,3vw,2rem);line-height:1.45}h3{line-height:1.5}
.eyebrow,.kicker{font-weight:900;color:#7b2d55}.lead{font-size:1.08rem;color:#355e61;max-width:78ch}.warning,.review,.card,.panel,.section-card,.sources,.faq,.myth{background:#fff;border:1px solid #c9e1de;border-radius:18px;padding:20px;box-shadow:0 12px 28px #123e4312}
.warning{border-right:6px solid #a32626;background:#fff5f5}.review{border-right:6px solid #a87510;background:#fffaf0}.facts,.cards,.related{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.fact{background:#e8f7f4;border-radius:16px;padding:16px}
.layout{display:grid;grid-template-columns:270px 1fr;gap:22px;padding:30px 0}.toc{position:sticky;top:16px;align-self:start}.toc a{display:block;padding:7px 0;border-bottom:1px solid #e2efed;text-decoration:none}.stack{display:grid;gap:18px}
.section-card ul,.panel ul,.panel ol{padding-right:1.3rem}.refs{font-size:.94rem}.actions{border-right:6px solid #08776f}.urgent{border-right:6px solid #a32626}.myths{display:grid;gap:12px}.myth strong{display:block;color:#7b2d55}.faqs{display:grid;gap:12px}.faq summary{font-weight:900;cursor:pointer}.sources li{margin:1rem 0}.level{display:inline-block;background:#e7f8f4;border-radius:8px;padding:1px 7px;font-weight:900}
.btn{display:inline-block;background:#0b6b64;color:#fff;text-decoration:none;font-weight:900;padding:10px 15px;border-radius:12px}.btn:focus,.btn:hover{background:#084c48}.cluster-table{width:100%;border-collapse:collapse}.cluster-table th,.cluster-table td{border:1px solid #c9e1de;padding:12px;text-align:right;vertical-align:top}.cluster-table th{background:#e8f7f4}
footer{margin-top:30px;padding:28px 0;border-top:1px solid #c9e1de;color:#4b6d70}
@media(max-width:850px){.head,.layout{display:block}.head nav{margin-top:10px}.toc{position:static;margin-bottom:18px}.facts,.cards,.related{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{header,.skip,.toc,.btn{display:none}.layout{display:block}.section-card,.panel,.sources,.faq,.myth,.review{box-shadow:none}}
'''


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_payload() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("v323 content must be an object")
    return data


def is_https(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_payload(data: dict) -> list[dict]:
    if data.get("version") != VERSION or data.get("language") != "ar":
        raise SystemExit("v323 identity contract failed")
    if data.get("review_status") != "internally-reviewed-external-clinical-review-required":
        raise SystemExit("v323 review state must remain honest")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("reviewed_at", ""))):
        raise SystemExit("v323 reviewed_at is invalid")
    guides = data.get("guides")
    if not isinstance(guides, list) or len(guides) != 3:
        raise SystemExit("v323 requires exactly three condition guides")
    if tuple(guide.get("slug") for guide in guides) != EXPECTED:
        raise SystemExit("v323 condition routes are incomplete or out of order")
    serialized = json.dumps(data, ensure_ascii=False)
    if BANNED.search(serialized) or UNSUPPORTED.search(serialized):
        raise SystemExit("v323 contains banned terminology or unsupported promises")

    for guide in guides:
        required_text = ("title", "short_title", "english_name", "meta_description", "lead", "warning")
        if any(not str(guide.get(key, "")).strip() for key in required_text):
            raise SystemExit(f"Incomplete guide identity: {guide.get('slug')}")
        if len(guide.get("key_facts", [])) < 5:
            raise SystemExit(f"Insufficient key facts: {guide['slug']}")
        sections = guide.get("sections")
        sources = guide.get("sources")
        if not isinstance(sections, list) or len(sections) != 7:
            raise SystemExit(f"Each condition needs seven sections: {guide['slug']}")
        if not isinstance(sources, list) or len(sources) < 6:
            raise SystemExit(f"Each condition needs at least six sources: {guide['slug']}")
        if len(guide.get("action_steps", [])) < 8 or len(guide.get("urgent", [])) < 6:
            raise SystemExit(f"Action or urgent depth failed: {guide['slug']}")
        if len(guide.get("myths", [])) < 5 or len(guide.get("faqs", [])) < 5:
            raise SystemExit(f"Myth or FAQ depth failed: {guide['slug']}")

        source_index: dict[str, dict] = {}
        local_urls: set[str] = set()
        for source in sources:
            sid = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            if not sid or sid in source_index:
                raise SystemExit(f"Duplicate source id in {guide['slug']}: {sid}")
            if not is_https(url) or url in local_urls:
                raise SystemExit(f"Invalid or duplicate source URL in {guide['slug']}: {url}")
            if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid source level: {guide['slug']}/{sid}")
            if any(not str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
                raise SystemExit(f"Incomplete source: {guide['slug']}/{sid}")
            source_index[sid] = source
            local_urls.add(url)

        section_ids: set[str] = set()
        used: set[str] = set()
        for section in sections:
            section_id = str(section.get("id", "")).strip()
            refs_list = section.get("source_ids", [])
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Invalid section id: {guide['slug']}/{section_id}")
            if not str(section.get("title", "")).strip() or not str(section.get("summary", "")).strip():
                raise SystemExit(f"Incomplete section: {guide['slug']}/{section_id}")
            if len(section.get("points", [])) < 5 or not refs_list or any(ref not in source_index for ref in refs_list):
                raise SystemExit(f"Section evidence contract failed: {guide['slug']}/{section_id}")
            section_ids.add(section_id)
            used.update(refs_list)
        if set(source_index) - used:
            raise SystemExit(f"Unused sources in {guide['slug']}: {sorted(set(source_index) - used)}")
    return guides


def schema_page(guide: dict, data: dict) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    cluster = f"{BASE}/special-needs/{data['cluster']['slug']}/"
    graph = [
        {"@type": "MedicalWebPage", "@id": url + "#page", "url": url, "name": guide["title"],
         "description": guide["meta_description"], "inLanguage": "ar", "dateModified": data["reviewed_at"],
         "isPartOf": {"@id": cluster + "#collection"},
         "about": {"@type": "MedicalCondition", "name": guide["short_title"], "alternateName": guide["english_name"]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
            {"@type": "ListItem", "position": 3, "name": "المتلازمات النمائية والجينية", "item": cluster},
            {"@type": "ListItem", "position": 4, "name": guide["short_title"], "item": url}]},
        {"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": row["q"], "acceptedAnswer": {"@type": "Answer", "text": row["a"]}}
            for row in guide["faqs"]
        ]},
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def refs(ids: list[str]) -> str:
    return " ".join(f'<a href="#source-{e(sid)}">[{e(sid)}]</a>' for sid in ids)


def render_condition(guide: dict, data: dict, guides: list[dict]) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    cluster_path = f"{BP}special-needs/{data['cluster']['slug']}/"
    toc = "".join(f'<a href="#{e(section["id"])}">{e(section["title"])}</a>' for section in guide["sections"])
    facts = "".join(f'<div class="fact">{e(item)}</div>' for item in guide["key_facts"])
    sections = []
    for section in guide["sections"]:
        points = "".join(f"<li>{e(point)}</li>" for point in section["points"])
        sections.append(
            f'<section class="section-card" id="{e(section["id"])}"><p class="kicker">محور علمي وعملي</p>'
            f'<h2>{e(section["title"])}</h2><p>{e(section["summary"])}</p><ul>{points}</ul>'
            f'<p class="refs"><strong>المراجع المرتبطة بالمحور:</strong> {refs(section["source_ids"])}</p></section>'
        )
    actions = "".join(f"<li>{e(item)}</li>" for item in guide["action_steps"])
    urgent = "".join(f"<li>{e(item)}</li>" for item in guide["urgent"])
    myths = "".join(
        f'<div class="myth"><strong>الاعتقاد: {e(row["claim"])}</strong><span>التصحيح: {e(row["correction"])}</span></div>'
        for row in guide["myths"]
    )
    faqs = "".join(f'<details class="faq"><summary>{e(row["q"])}</summary><p>{e(row["a"])}</p></details>' for row in guide["faqs"])
    sources = "".join(
        f'<li id="source-{e(s["id"])}"><span class="level">{e(s["level"])}</span> '
        f'<strong>{e(s["id"])} — {e(s["organization"])}</strong>: '
        f'<a href="{e(s["url"])}" rel="noopener noreferrer">{e(s["title"])}</a> '
        f'<small>تاريخ المصدر أو آخر مراجعة مسجل: {e(s["reviewed"])}</small></li>'
        for s in guide["sources"]
    )
    related = "".join(
        f'<article class="card"><h3>{e(other["short_title"])}</h3><p>{e(other["meta_description"])}</p>'
        f'<a href="{BP}special-needs/{e(other["slug"])}/">فتح الدليل</a></article>'
        for other in guides if other["slug"] != guide["slug"]
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(guide["title"])}</title>
<meta name="description" content="{e(guide["meta_description"])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{url}"><link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}">
<meta property="og:type" content="article"><meta property="og:url" content="{url}"><meta property="og:title" content="{e(guide["title"])}">
<meta property="og:description" content="{e(guide["meta_description"])}"><meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{schema_page(guide, data)}</script><style>{CSS}</style></head>
<body data-condition-guide-v323="{e(guide["slug"])}"><a class="skip" href="#main">انتقل إلى المحتوى</a>
<header><div class="wrap head"><a href="{BP}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">ذوو الاحتياجات الخاصة</a><a href="{cluster_path}">المتلازمات النمائية والجينية</a></nav></div></header>
<main id="main"><section class="hero"><div class="wrap"><p class="eyebrow">دليل حالة جديد - مراجعة داخلية موثقة</p>
<h1>{e(guide["short_title"])}</h1><p class="lead">{e(guide["lead"])}</p><div class="warning"><strong>حدود وسلامة:</strong> {e(guide["warning"])}</div></div></section>
<section class="wrap" aria-labelledby="facts-title"><h2 id="facts-title">خمس حقائق تأسيسية</h2><div class="facts">{facts}</div></section>
<div class="wrap layout"><aside class="panel toc"><h2>محتويات الدليل</h2>{toc}<a href="#actions">خطة عمل</a><a href="#urgent">مؤشرات عاجلة</a><a href="#myths">تصحيح مفاهيم</a><a href="#faqs">أسئلة شائعة</a><a href="#sources">المراجع</a></aside>
<article class="stack">{''.join(sections)}
<section class="panel actions" id="actions"><h2>خطة عمل منظمة للأسرة والفريق</h2><ol>{actions}</ol></section>
<section class="panel urgent" id="urgent"><h2>مؤشرات تستدعي تحركًا سريعًا</h2><ul>{urgent}</ul></section>
<section class="panel" id="myths"><h2>مفاهيم شائعة تحتاج تصحيحًا</h2><div class="myths">{myths}</div></section>
<section class="panel" id="faqs"><h2>أسئلة شائعة</h2><div class="faqs">{faqs}</div></section>
<section class="review"><h2>حالة التحرير والمراجعة</h2><p>أُعدت الصفحة وراجعت داخليًا من حيث البنية والمصادر والحدود المهنية. لم تكتمل مراجعة سريرية خارجية مستقلة، ولذلك لا تُعرض الصفحة بوصفها بروتوكولًا علاجيًا فرديًا. تاريخ المراجعة: {e(data["reviewed_at"])}، والمراجعة التالية المستهدفة: {e(data["next_review_due"])}.</p></section>
<section class="sources" id="sources"><h2>المراجع الأصلية والموثوقة</h2><ol>{sources}</ol></section>
<section class="panel"><h2>أدلة مرتبطة</h2><div class="related">{related}</div><p><a class="btn" href="{cluster_path}">العودة إلى مركز المتلازمات النمائية والجينية</a></p></section>
</article></div></main><footer><div class="wrap">المعلومة العلمية نقطة بداية لتنظيم الرعاية والتعلم والمشاركة، وليست بديلًا عن التقييم الفردي أو خطة الطوارئ المحلية.</div></footer></body></html>'''


def cluster_schema(data: dict, guides: list[dict]) -> str:
    url = f"{BASE}/special-needs/{data['cluster']['slug']}/"
    graph = [
        {"@type": "CollectionPage", "@id": url + "#collection", "url": url, "name": data["cluster"]["title"],
         "description": data["cluster"]["meta_description"], "inLanguage": "ar", "dateModified": data["reviewed_at"],
         "hasPart": [{"@type": "MedicalWebPage", "url": f"{BASE}/special-needs/{g['slug']}/", "name": g["short_title"]} for g in guides]},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
            {"@type": "ListItem", "position": 3, "name": "المتلازمات النمائية والجينية", "item": url}]},
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def render_cluster(data: dict, guides: list[dict]) -> str:
    cluster = data["cluster"]
    url = f"{BASE}/special-needs/{cluster['slug']}/"
    cards = "".join(
        f'<article class="card"><p class="kicker">{e(g["english_name"])}</p><h2>{e(g["short_title"])}</h2>'
        f'<p>{e(g["meta_description"])}</p><ul>{"".join(f"<li>{e(x)}</li>" for x in g["key_facts"][:3])}</ul>'
        f'<a class="btn" href="{BP}special-needs/{e(g["slug"])}/">فتح الدليل الشامل</a></article>'
        for g in guides
    )
    principles = "".join(f"<li>{e(item)}</li>" for item in cluster["principles"])
    rows = "".join(f'<tr><th>{e(g["short_title"])}</th><td>{e(g["lead"])}</td><td>{e(g["key_facts"][0])}</td></tr>' for g in guides)
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(cluster["title"])}</title><meta name="description" content="{e(cluster["meta_description"])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{url}">
<link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}">
<script type="application/ld+json">{cluster_schema(data, guides)}</script><style>{CSS}</style></head>
<body data-condition-cluster-v323="true"><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head">
<a href="{BP}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">ذوو الاحتياجات الخاصة</a></nav></div></header>
<main id="main"><section class="hero"><div class="wrap"><p class="eyebrow">مركز جديد للحالات غير المغطاة سابقًا</p><h1>المتلازمات النمائية والجينية</h1>
<p class="lead">{e(cluster["lead"])}</p><div class="review"><strong>حالة المراجعة:</strong> مراجعة تحريرية داخلية؛ المراجعة السريرية الخارجية لم تكتمل بعد.</div></div></section>
<section class="wrap"><h2>الأدلة المنشورة في الدفعة الأولى</h2><div class="cards">{cards}</div></section>
<section class="wrap panel"><h2>منهج قراءة الحالة وبناء الخطة</h2><ol>{principles}</ol>
<p>يبدأ المسار بتأكيد التشخيص وآليته عندما يكون الفحص الجيني جزءًا من الحالة، ثم يوثق خط الأساس الصحي والنمائي والتواصلي، وبعد ذلك يحول النتائج إلى أهداف وظيفية قابلة للقياس. التوصيات العامة لا تساوي خطة فردية، ولا تُستخدم ندرة الحالة لتبرير تجاهل الألم أو النوم أو الصحة النفسية أو التواصل.</p></section>
<section class="wrap panel"><h2>خريطة الفروق الأولية</h2><div style="overflow:auto"><table class="cluster-table"><thead><tr><th>الحالة</th><th>الصورة العامة</th><th>نقطة تشخيصية محورية</th></tr></thead><tbody>{rows}</tbody></table></div></section>
<section class="wrap panel"><h2>ما الذي سيُضاف لاحقًا؟</h2><p>تتوسع السلسلة على دفعات مستقلة إلى متلازمة ويليامز ومتلازمة برادر-ويلي وحالات نمائية وجينية أخرى بعد التحقق من عدم وجود صفحة مكررة، وفحص المصادر، وبناء ناشر واختبارات واكتشاف وفهرسة لكل مسار.</p></section>
</main><footer><div class="wrap">تاريخ المراجعة: {e(data["reviewed_at"])} - موعد المراجعة المستهدف: {e(data["next_review_due"])}</div></footer></body></html>'''


def text_words(page: str) -> int:
    plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S | re.I)
    plain = html.unescape(re.sub(r"<[^>]+>", " ", plain))
    return len(re.findall(r"[\u0600-\u06FF]+|[A-Za-z0-9]+", plain))


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def update_sitemap(site: Path, data: dict, guides: list[dict]) -> None:
    path = site / "sitemap-special-needs.xml"
    if not path.is_file():
        raise SystemExit(f"Missing special-needs sitemap: {path}")
    ET.register_namespace("", NS)
    tree = ET.parse(path)
    root = tree.getroot()
    urls = [f"{BASE}/special-needs/{data['cluster']['slug']}/"] + [f"{BASE}/special-needs/{g['slug']}/" for g in guides]
    for target in urls:
        matches = [row for row in root.findall("{*}url") if (row.findtext("{*}loc") or "").strip() == target]
        if len(matches) > 1:
            raise SystemExit(f"Duplicate sitemap URL: {target}")
        row = matches[0] if matches else ET.SubElement(root, qualify(root, "url"))
        values = {"loc": target, "lastmod": data["reviewed_at"], "changefreq": "monthly", "priority": "0.90"}
        for key, value in values.items():
            node = row.find(f"{{*}}{key}")
            if node is None:
                node = ET.SubElement(row, qualify(root, key))
            node.text = value
    tree.write(path, encoding="utf-8", xml_declaration=True)


def hub_block(data: dict, guides: list[dict]) -> str:
    links = "".join(
        f'<article class="quality-card"><h3>{e(g["short_title"])}</h3><p>{e(g["meta_description"])}</p>'
        f'<a href="{BP}special-needs/{e(g["slug"])}/">فتح الدليل</a></article>'
        for g in guides
    )
    return f'''<section class="section" {HUB_MARKER} aria-labelledby="genetic-developmental-title"><div class="wrap">
<p class="eyebrow">حالات جديدة موثقة</p><h2 id="genetic-developmental-title">المتلازمات النمائية والجينية</h2>
<p class="section-intro">{e(data["cluster"]["lead"])}</p><div class="quality-grid">{links}</div>
<p><a class="btn" href="{BP}special-needs/{e(data["cluster"]["slug"])}/">فتح مركز المتلازمات النمائية والجينية</a></p></div></section>'''


def patch_hub(site: Path, data: dict, guides: list[dict]) -> None:
    path = site / "special-needs" / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing generated special-needs hub: {path}")
    source = path.read_text(encoding="utf-8")
    block = hub_block(data, guides)
    pattern = rf'<section class="section" {HUB_MARKER}.*?</section>'
    if re.search(pattern, source, flags=re.S):
        source, count = re.subn(pattern, block, source, count=1, flags=re.S)
    else:
        if source.count(HUB_INSERT) != 1:
            raise SystemExit("Special-needs hub insertion marker failed")
        source = source.replace(HUB_INSERT, block + HUB_INSERT, 1)
        count = 1
    if count != 1 or source.count(HUB_MARKER) != 1:
        raise SystemExit("Special-needs hub v323 idempotence failed")
    path.write_text(source, encoding="utf-8")


def publish(site: Path) -> dict:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    data = read_payload()
    guides = validate_payload(data)
    cluster_page = render_cluster(data, guides)
    cluster_target = site / "special-needs" / data["cluster"]["slug"] / "index.html"
    cluster_target.parent.mkdir(parents=True, exist_ok=True)
    cluster_target.write_text(cluster_page, encoding="utf-8")

    generated = [cluster_target.relative_to(site).as_posix()]
    word_counts = {"cluster": text_words(cluster_page)}
    for guide in guides:
        page = render_condition(guide, data, guides)
        words = text_words(page)
        if words < 1350:
            raise SystemExit(f"Condition page is not sufficiently deep: {guide['slug']}={words}")
        if page.lower().count("<h1") != 1 or page.count('class="section-card"') != 7:
            raise SystemExit(f"Rendered structure failed: {guide['slug']}")
        if "MedicalWebPage" not in page or "FAQPage" not in page or BANNED.search(page):
            raise SystemExit(f"Rendered metadata or language failed: {guide['slug']}")
        target = site / "special-needs" / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        generated.append(target.relative_to(site).as_posix())
        word_counts[guide["slug"]] = words

    patch_hub(site, data, guides)
    update_sitemap(site, data, guides)
    report = {
        "version": VERSION,
        "status": "passed",
        "review_status": data["review_status"],
        "external_clinical_review_completed": False,
        "cluster_slug": data["cluster"]["slug"],
        "condition_count": len(guides),
        "condition_slugs": [g["slug"] for g in guides],
        "generated_pages": generated,
        "source_count": sum(len(g["sources"]) for g in guides),
        "section_count": sum(len(g["sections"]) for g in guides),
        "faq_count": sum(len(g["faqs"]) for g in guides),
        "minimum_condition_words": min(word_counts[g["slug"]] for g in guides),
        "word_counts": word_counts,
        "hub_link_added": True,
        "sitemap_registered": True,
        "reviewed_at": data["reviewed_at"],
        "next_review_due": data["next_review_due"],
        "content_source": CONTENT.relative_to(ROOT).as_posix(),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "new-special-needs-conditions-v323.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
