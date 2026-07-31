#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v322" / "evidence-literacy-library-ar.json"
BASE = "https://healthrenewal.org/"
BP = "/"
VERSION = 322
PARENT_MARKER = 'data-evidence-literacy-library-v322="parent-link"'
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "svg", "template", "noscript"}:
            self.hidden.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        if self.hidden and self.hidden[-1] == tag.lower():
            self.hidden.pop()

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            value = re.sub(r"\s+", " ", data).strip()
            if value:
                self.parts.append(value)


def words(source: str) -> int:
    parser = VisibleText()
    parser.feed(source)
    return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(parser.parts), flags=re.UNICODE))


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_payload() -> dict:
    try:
        payload = json.loads(CONTENT.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid evidence-literacy JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("Evidence-literacy payload must be an object")
    return payload


def validate(payload: dict) -> tuple[list[dict], dict[str, dict]]:
    if payload.get("version") != VERSION or payload.get("language") != "ar":
        raise SystemExit("Evidence-literacy manifest contract failed")
    if payload.get("review_status") != "internally-reviewed-external-methodology-review-required":
        raise SystemExit("Evidence-literacy review status must remain explicit")
    guides = payload.get("guides")
    sources = payload.get("sources")
    if not isinstance(guides, list) or len(guides) != 4:
        raise SystemExit("Exactly four evidence-literacy guides are required")
    expected = {
        "how-to-read-systematic-review",
        "certainty-of-evidence-and-recommendations",
        "study-designs-bias-and-causality",
        "appraise-clinical-guideline",
    }
    if {guide.get("slug") for guide in guides} != expected:
        raise SystemExit("Evidence-literacy routes are incomplete")
    if not isinstance(sources, list) or len(sources) < 12:
        raise SystemExit("Evidence-literacy source depth is insufficient")

    source_index: dict[str, dict] = {}
    urls: set[str] = set()
    for source in sources:
        sid = str(source.get("id", "")).strip()
        url = str(source.get("url", "")).strip()
        parsed = urlparse(url)
        if not sid or sid in source_index:
            raise SystemExit(f"Duplicate or empty source id: {sid}")
        if parsed.scheme != "https" or not parsed.netloc or url in urls:
            raise SystemExit(f"Invalid or duplicate source URL: {url}")
        if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
            raise SystemExit(f"Invalid source level: {sid}")
        if not all(str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
            raise SystemExit(f"Incomplete source metadata: {sid}")
        source_index[sid] = source
        urls.add(url)

    used: set[str] = set()
    for guide in guides:
        serialized = json.dumps(guide, ensure_ascii=False)
        if BANNED.search(serialized):
            raise SystemExit(f"Banned terminology in {guide.get('slug')}")
        if len(guide.get("sections", [])) != 6:
            raise SystemExit(f"Each guide must have six sections: {guide.get('slug')}")
        if len(guide.get("red_flags", [])) != 5 or len(guide.get("action_steps", [])) != 5:
            raise SystemExit(f"Action/red-flag contract failed: {guide.get('slug')}")

        declared_order = [str(sid).strip() for sid in guide.get("source_ids", [])]
        if any(not sid or sid not in source_index for sid in declared_order):
            raise SystemExit(f"Guide source declaration failed: {guide.get('slug')}")
        if len(declared_order) != len(set(declared_order)):
            raise SystemExit(f"Duplicate guide source declaration: {guide.get('slug')}")

        section_ids: set[str] = set()
        section_used: set[str] = set()
        for section in guide["sections"]:
            section_id = str(section.get("id", "")).strip()
            refs = {str(sid).strip() for sid in section.get("source_ids", [])}
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Duplicate section id: {guide.get('slug')}/{section_id}")
            if len(section.get("paragraphs", [])) != 2 or len(section.get("checks", [])) != 4:
                raise SystemExit(f"Section depth failed: {guide.get('slug')}/{section_id}")
            if not refs or any(not sid or sid not in source_index for sid in refs):
                raise SystemExit(f"Section evidence failed: {guide.get('slug')}/{section_id}")
            section_ids.add(section_id)
            section_used.update(refs)

        if len(section_used) < 5:
            raise SystemExit(f"Guide source depth failed: {guide.get('slug')}")
        effective_order = [sid for sid in declared_order if sid in section_used]
        effective_order.extend(sid for sid in source_index if sid in section_used and sid not in effective_order)
        guide["source_ids"] = effective_order
        used.update(section_used)

    unused = sorted(set(source_index) - used)
    if unused:
        raise SystemExit(f"Unused evidence-literacy sources: {unused}")

    combined = json.dumps(guides, ensure_ascii=False)
    required_boundaries = (
        "المراجعة المنهجية ليست قوية لمجرد اسمها",
        "يقين الدليل يجيب عن مقدار الثقة",
        "الارتباط يعني أن متغيرين يتحركان معًا",
        "الإفصاح وحده ليس إدارة",
        "التقرير الكامل وفق إرشاد مناسب يسهل التقييم، لكنه لا يصلح تصميمًا ضعيفًا",
    )
    missing = [phrase for phrase in required_boundaries if phrase not in combined]
    if missing:
        raise SystemExit(f"Evidence-literacy conceptual boundaries missing: {missing}")
    return guides, source_index


STYLE = """
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#153f43;background:#f5faf9;line-height:1.9}a{color:#076a63}.wrap{width:min(1160px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;padding:10px;z-index:20}header{background:#123f43;color:#fff}.head{display:flex;justify-content:space-between;gap:16px;align-items:center;padding:13px 0}.head a{color:#fff;text-decoration:none;font-weight:800}.nav{display:flex;gap:12px;flex-wrap:wrap}.hero{background:linear-gradient(135deg,#e4f7f2,#fff);padding:56px 0 32px}h1{font-size:clamp(2rem,5vw,4rem);line-height:1.22;margin:.15em 0}h2{font-size:clamp(1.4rem,3vw,2rem);line-height:1.4}.lead{font-size:1.08rem;color:#47696c}.kicker{font-weight:900;color:#8a3156}.notice,.card,.section-card,.panel,.sources{background:#fff;border:1px solid #c8e2de;border-radius:18px;padding:21px;box-shadow:0 12px 28px #123f4312}.notice{border-right:6px solid #8a3156}.cards{display:grid;grid-template-columns:repeat(2,1fr);gap:17px;padding:30px 0}.card{display:flex;flex-direction:column}.card p{flex:1}.button{display:inline-block;text-decoration:none;font-weight:900;background:#b9eee5;color:#123f43;padding:9px 14px;border-radius:11px}.layout{display:grid;grid-template-columns:270px 1fr;gap:20px;padding:30px 0}.toc{position:sticky;top:16px;align-self:start}.toc a{display:block;padding:6px 0;border-bottom:1px solid #e2efed;text-decoration:none}.stack{display:grid;gap:17px}.checks{background:#effaf8;border-radius:13px;padding:12px 18px}.flags{border-right:6px solid #a32626;background:#fff4f4}.actions{border-right:6px solid #08776f}.sources li{margin:1rem 0}.level{display:inline-block;background:#e7f8f4;border-radius:8px;padding:1px 7px;font-weight:900}footer{margin-top:30px;border-top:1px solid #c8e2de;padding:28px 0;color:#527174}@media(max-width:800px){.head,.layout{display:block}.nav{margin-top:10px}.cards{grid-template-columns:1fr}.toc{position:static;margin-bottom:16px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header,.skip,.toc{display:none}.layout{display:block}.card,.section-card,.panel,.sources{box-shadow:none}}
"""


def schema_page(guide: dict, payload: dict) -> str:
    url = f"{BASE}/library/evidence-literacy/{guide['slug']}/"
    graph = [
        {
            "@type": "Article",
            "@id": url + "#article",
            "headline": guide["title"],
            "description": guide["meta_description"],
            "url": url,
            "inLanguage": "ar",
            "dateModified": payload["reviewed_at"],
            "isPartOf": {"@id": f"{BASE}/library/evidence-literacy/#collection"},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "المكتبة", "item": BASE + "/library/"},
                {"@type": "ListItem", "position": 3, "name": "الثقافة العلمية", "item": BASE + "/library/evidence-literacy/"},
                {"@type": "ListItem", "position": 4, "name": guide["short_title"], "item": url},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def source_rows(ids: list[str], source_index: dict[str, dict]) -> str:
    return "".join(
        f'<li id="source-{e(sid)}"><span class="level">{e(source_index[sid]["level"])}</span> '
        f'<b>{e(source_index[sid]["organization"])}</b>: '
        f'<a href="{e(source_index[sid]["url"])}" rel="noopener noreferrer">{e(source_index[sid]["title"])}</a> '
        f'<small>تاريخ المراجعة المسجل: {e(source_index[sid]["reviewed"])}</small></li>'
        for sid in ids
    )


def render_page(guide: dict, payload: dict, source_index: dict[str, dict]) -> str:
    canonical = f"{BASE}/library/evidence-literacy/{guide['slug']}/"
    toc = "".join(f'<a href="#{e(section["id"])}">{e(section["title"])}</a>' for section in guide["sections"])
    sections: list[str] = []
    for section in guide["sections"]:
        paragraphs = "".join(f"<p>{e(paragraph)}</p>" for paragraph in section["paragraphs"])
        checks = "".join(f"<li>{e(item)}</li>" for item in section["checks"])
        refs = " ".join(f'<a href="#source-{e(sid)}">[{e(sid)}]</a>' for sid in section["source_ids"])
        sections.append(
            f'<section class="section-card" id="{e(section["id"])}"><p class="kicker">محور التقييم</p>'
            f'<h2>{e(section["title"])}</h2>{paragraphs}<div class="checks"><h3>أسئلة فحص</h3><ul>{checks}</ul></div><p>{refs}</p></section>'
        )
    flags = "".join(f"<li>{e(item)}</li>" for item in guide["red_flags"])
    actions = "".join(f"<li>{e(item)}</li>" for item in guide["action_steps"])
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(guide['title'])}</title><meta name="description" content="{e(guide['meta_description'])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ar" href="{canonical}"><link rel="alternate" hreflang="x-default" href="{canonical}"><meta property="og:type" content="article"><meta property="og:url" content="{canonical}"><meta property="og:title" content="{e(guide['title'])}"><meta property="og:description" content="{e(guide['meta_description'])}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema_page(guide,payload)}</script><style>{STYLE}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head"><a href="{BP}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav class="nav"><a href="{BP}library/">المكتبة</a><a href="{BP}library/evidence-literacy/">الثقافة العلمية</a><a href="{BP}trust/">المنهجية</a></nav></div></header><main id="main"><section class="hero"><div class="wrap"><p class="kicker">المكتبة الأكاديمية — الثقافة العلمية</p><h1>{e(guide['short_title'])}</h1><p class="lead">{e(guide['lead'])}</p><p class="notice"><b>حد الاستخدام:</b> هذا الدليل يساعد على قراءة البحث ولا يحول القارئ إلى مراجع منهجي مستقل، ولا يستبدل التقييم المتخصص أو القرار الصحي الفردي.</p></div></section><div class="wrap layout"><aside class="panel toc"><h2>المحتويات</h2>{toc}<a href="#red-flags">إشارات تحذير</a><a href="#actions">خمس خطوات</a><a href="#sources">المراجع</a></aside><article class="stack">{''.join(sections)}<section class="panel flags" id="red-flags"><h2>إشارات تحذير في القراءة أو الاستنتاج</h2><ul>{flags}</ul></section><section class="panel actions" id="actions"><h2>مسار قراءة عملي</h2><ol>{actions}</ol></section><section class="sources" id="sources"><h2>المراجع المنهجية الأصلية</h2><ol>{source_rows(guide['source_ids'], source_index)}</ol><p><b>حالة المراجعة:</b> إعداد ومراجعة داخلية، ولم تكتمل مراجعة خارجية مستقلة من متخصص في منهجية البحث. آخر مراجعة {e(payload['reviewed_at'])}، والمراجعة التالية {e(payload['next_review_due'])}.</p></section></article></div></main><footer><div class="wrap"><p>يجب قراءة النتائج مع حجم الأثر وعدم اليقين والسياق، لا من العنوان أو الدلالة الإحصائية وحدهما.</p></div></footer></body></html>'''


def render_hub(payload: dict, guides: list[dict], source_index: dict[str, dict]) -> str:
    hub = payload["hub"]
    canonical = f"{BASE}/library/evidence-literacy/"
    cards = "".join(
        f'<article class="card"><p class="kicker">دليل منهجي</p><h2>{e(guide["short_title"])}</h2><p>{e(guide["meta_description"])}</p><a class="button" href="{BP}library/evidence-literacy/{e(guide["slug"])}/">فتح الدليل</a></article>'
        for guide in guides
    )
    source_ids = list(source_index)
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "@id": canonical + "#collection",
            "url": canonical,
            "name": hub["title"],
            "description": hub["meta_description"],
            "inLanguage": "ar",
            "dateModified": payload["reviewed_at"],
            "hasPart": [
                {"@type": "Article", "name": guide["title"], "url": f"{canonical}{guide['slug']}/"}
                for guide in guides
            ],
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(hub['title'])} | المكتبة الأكاديمية</title><meta name="description" content="{e(hub['meta_description'])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ar" href="{canonical}"><link rel="alternate" hreflang="x-default" href="{canonical}"><meta property="og:type" content="website"><meta property="og:url" content="{canonical}"><meta property="og:title" content="{e(hub['title'])}"><meta property="og:description" content="{e(hub['meta_description'])}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema}</script><style>{STYLE}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head"><a href="{BP}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav class="nav"><a href="{BP}library/">المكتبة</a><a href="{BP}trust/">منهج المصادر</a></nav></div></header><main id="main"><section class="hero"><div class="wrap"><p class="kicker">المكتبة الأكاديمية</p><h1>{e(hub['title'])}</h1><p class="lead">{e(hub['lead'])}</p><p class="notice"><b>قاعدة منهجية:</b> جودة التقرير لا تساوي بالضرورة جودة الدراسة، ووجود تحليل تلوي لا يضمن يقينًا مرتفعًا، وقوة التوصية لا تساوي درجة يقين الدليل.</p></div></section><section class="wrap"><div class="cards">{cards}</div><section class="section-card"><h2>خريطة القراءة المنهجية</h2><p>ابدأ بتحديد السؤال ونوع الدراسة، ثم افحص اختيار المشاركين والقياس والبيانات المفقودة وخطر التحيز. بعد ذلك اقرأ حجم الأثر وفاصل الثقة، وراجع يقين الدليل لكل نتيجة، وافصل بين استنتاج المراجعة والتوصية التي تحتاج قيمًا وموارد وسياقًا. عند قراءة إرشاد سريري، افحص استقلال اللجنة وتعارض المصالح وتاريخ البحث وخطة التحديث وإمكان التطبيق المحلي.</p><p>لا تستخدم القوائم كآلة تمنح الدراسة درجة نهائية. القائمة تساعد على اكتشاف المعلومات الناقصة والأسئلة التي تحتاج حكمًا منهجيًا. وقد يكون التقرير كاملًا وفق PRISMA أو STROBE لكنه يبقى معرضًا لتحيز جوهري؛ كما قد يكون البحث مفيدًا رغم قيود معلنة إذا كانت الخلاصة متناسبة مع عدم اليقين.</p></section><section class="sources"><h2>المرجع المنهجي للمكتبة</h2><ol>{source_rows(source_ids, source_index)}</ol><p>آخر مراجعة داخلية {e(payload['reviewed_at'])}. المراجعة المنهجية الخارجية المستقلة غير مكتملة، والمراجعة التالية {e(payload['next_review_due'])}.</p></section></section></main><footer><div class="wrap"><p>المحتوى تعليمي ويهدف إلى تحسين فهم الأدلة، لا إصدار أحكام مهنية نهائية على الدراسات أو الإرشادات.</p></div></footer></body></html>'''


def ensure_library_parent(site: Path) -> None:
    path = site / "library" / "index.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    block = f'''<section class="section" {PARENT_MARKER}><div class="wrap"><p class="kicker">مسار أكاديمي جديد</p><h2>الثقافة العلمية وقراءة الدليل</h2><p>أربعة أدلة مطولة لفهم المراجعات المنهجية وتصاميم الدراسات ويقين الدليل والإرشادات السريرية.</p><a href="{BP}library/evidence-literacy/">فتح مكتبة الثقافة العلمية</a></div></section>'''
    if path.is_file():
        source = path.read_text(encoding="utf-8")
        pattern = rf'<section\b[^>]*{re.escape(PARENT_MARKER)}[^>]*>.*?</section>'
        if re.search(pattern, source, flags=re.I | re.S):
            updated, count = re.subn(pattern, block, source, count=1, flags=re.I | re.S)
        elif re.search(r"</main\s*>", source, flags=re.I):
            updated, count = re.subn(r"</main\s*>", block + "</main>", source, count=1, flags=re.I)
        else:
            updated, count = re.subn(r"</body\s*>", block + "</body>", source, count=1, flags=re.I)
        if count != 1:
            raise SystemExit("Unable to link evidence-literacy collection from library parent")
        if updated.count(PARENT_MARKER) != 1:
            raise SystemExit("Duplicate evidence-literacy parent marker")
        path.write_text(updated, encoding="utf-8")
        return
    canonical = f"{BASE}/library/"
    path.write_text(
        f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>المكتبة الأكاديمية للصحة النفسية</title><meta name="description" content="مكتبة عربية للمصادر والقراءة المنهجية في الصحة النفسية والبحث العلمي."><meta name="robots" content="index,follow"><link rel="canonical" href="{canonical}"><style>{STYLE}</style></head><body><header><div class="wrap head"><a href="{BP}">المنصة</a></div></header><main><section class="hero"><div class="wrap"><h1>المكتبة الأكاديمية للصحة النفسية</h1><p class="lead">مصادر وأدلة تساعد القارئ على الوصول إلى المعرفة وتقييمها وتطبيقها بحدود واضحة.</p></div></section>{block}</main><footer><div class="wrap"><p>محتوى تثقيفي موثق.</p></div></footer></body></html>''',
        encoding="utf-8",
    )


def q(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def update_sitemap(site: Path, routes: list[str], reviewed: str) -> None:
    path = site / "sitemap-library.xml"
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    if path.is_file():
        tree = ET.parse(path)
        root = tree.getroot()
    else:
        root = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
        tree = ET.ElementTree(root)
    for route in routes:
        url = f"{BASE}{route}"
        rows = [row for row in root.findall("{*}url") if (row.findtext("{*}loc") or "").strip() == url]
        if len(rows) > 1:
            raise SystemExit(f"Duplicate library sitemap URL: {url}")
        row = rows[0] if rows else ET.SubElement(root, q(root, "url"))
        values = {"loc": url, "lastmod": reviewed, "changefreq": "monthly", "priority": "0.82"}
        for key, value in values.items():
            node = row.find(f"{{*}}{key}")
            if node is None:
                node = ET.SubElement(row, q(root, key))
            node.text = value
    tree.write(path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict:
    payload = read_payload()
    guides, source_index = validate(payload)
    ensure_library_parent(site)
    base_dir = site / "library" / "evidence-literacy"
    base_dir.mkdir(parents=True, exist_ok=True)
    hub = render_hub(payload, guides, source_index)
    (base_dir / "index.html").write_text(hub, encoding="utf-8")
    page_reports: list[dict] = []
    for guide in guides:
        source = render_page(guide, payload, source_index)
        target = base_dir / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        page_words = words(source)
        if page_words < 900 or source.count("<h1") != 1 or source.count('class="section-card"') != 6:
            raise SystemExit({"evidence_literacy_page_depth_failed": {"slug": guide["slug"], "words": page_words}})
        if BANNED.search(source):
            raise SystemExit(f"Banned terminology rendered in {guide['slug']}")
        page_reports.append({"slug": guide["slug"], "path": target.relative_to(site).as_posix(), "words": page_words, "sections": 6, "sources": len(guide["source_ids"])})
    hub_words = words(hub)
    if hub_words < 500:
        raise SystemExit({"evidence_literacy_hub_too_short": hub_words})
    routes = ["/library/evidence-literacy/"] + [f"/library/evidence-literacy/{guide['slug']}/" for guide in guides]
    update_sitemap(site, routes, payload["reviewed_at"])
    report = {
        "version": VERSION,
        "status": "passed",
        "review_status": payload["review_status"],
        "external_methodology_review_completed": False,
        "guide_count": len(guides),
        "guide_slugs": [guide["slug"] for guide in guides],
        "generated_page_count": len(guides) + 1,
        "hub_words": hub_words,
        "minimum_guide_words": min(item["words"] for item in page_reports),
        "total_guide_words": sum(item["words"] for item in page_reports),
        "section_count": sum(item["sections"] for item in page_reports),
        "source_count": len(source_index),
        "parent_link_added": True,
        "sitemap_registered": True,
        "reviewed_at": payload["reviewed_at"],
        "next_review_due": payload["next_review_due"],
        "pages": page_reports,
        "content_source": CONTENT.relative_to(ROOT).as_posix(),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "evidence-literacy-library-v322.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing site directory: {args.site}")
    print(json.dumps(publish(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
