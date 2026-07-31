#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import html
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v324" / "autism-clinical-pathways-ar.json.gz"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
BP = "/pterminology-site/"
VERSION = 324
PARENT_MARKER = "data-autism-clinical-pathways-v324"
PARENT_INSERT = '<section class="source-area" id="sources">'
EXPECTED = (
    "autism-comprehensive-assessment-differential-diagnosis",
    "autism-late-diagnosis-adults-women-masking",
    "autism-aac-assessment-implementation",
    "autism-unsafe-unproven-treatments",
)
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
        raw = gzip.decompress(CONTENT.read_bytes())
        payload = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid compressed v324 content: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("v324 payload must be a JSON object")
    return payload


def is_https(url: str) -> bool:
    parsed = urlparse(str(url))
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_payload(payload: dict) -> list[dict]:
    if payload.get("version") != VERSION or payload.get("language") != "ar":
        raise SystemExit("Autism clinical pathways manifest contract failed")
    if payload.get("review_status") != "internally-reviewed-external-clinical-review-required":
        raise SystemExit("External clinical review status must remain explicit")
    guides = payload.get("guides")
    if not isinstance(guides, list) or len(guides) != 4:
        raise SystemExit("Exactly four v324 autism guides are required")
    if tuple(guide.get("slug") for guide in guides) != EXPECTED:
        raise SystemExit("v324 autism routes or order are incomplete")

    all_urls: set[str] = set()
    for guide in guides:
        slug = str(guide.get("slug", "")).strip()
        serialized = json.dumps(guide, ensure_ascii=False)
        if guide.get("parent_slug") != "autism" or BANNED.search(serialized):
            raise SystemExit(f"Identity or language contract failed: {slug}")
        sections = guide.get("sections")
        sources = guide.get("sources")
        if not isinstance(sections, list) or len(sections) != 7:
            raise SystemExit(f"Each v324 guide needs seven sections: {slug}")
        if not isinstance(sources, list) or len(sources) < 6:
            raise SystemExit(f"Each v324 guide needs at least six sources: {slug}")
        if len(guide.get("action_steps", [])) != 6 or len(guide.get("urgent", [])) != 3:
            raise SystemExit(f"Action or urgent contract failed: {slug}")

        source_index: dict[str, dict] = {}
        local_urls: set[str] = set()
        for source in sources:
            sid = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            if not sid or sid in source_index:
                raise SystemExit(f"Duplicate or empty source id: {slug}/{sid}")
            if not is_https(url) or url in local_urls:
                raise SystemExit(f"Invalid or duplicate source URL: {slug}/{url}")
            if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid evidence level: {slug}/{sid}")
            if not all(str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
                raise SystemExit(f"Incomplete source metadata: {slug}/{sid}")
            source_index[sid] = source
            local_urls.add(url)
            all_urls.add(url)

        used: set[str] = set()
        section_ids: set[str] = set()
        for section in sections:
            section_id = str(section.get("id", "")).strip()
            refs = section.get("source_ids", [])
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Duplicate or empty section: {slug}/{section_id}")
            if len(section.get("paragraphs", [])) != 2 or len(section.get("checkpoints", [])) != 4:
                raise SystemExit(f"Section depth contract failed: {slug}/{section_id}")
            if not refs or any(ref not in source_index for ref in refs):
                raise SystemExit(f"Section evidence contract failed: {slug}/{section_id}")
            section_ids.add(section_id)
            used.update(refs)
        if set(source_index) != used:
            raise SystemExit(f"Every declared source must be used: {slug}/{sorted(set(source_index) - used)}")

    if len(all_urls) < 17:
        raise SystemExit("v324 needs broad and non-duplicative evidence coverage")
    combined = json.dumps(guides, ensure_ascii=False)
    required = (
        "التقييم الشامل ليس جلسة واحدة ولا درجة في أداة",
        "التمويه مفهوم بحثي متطور وليس اختبارًا تشخيصيًا مستقلًا",
        "التواصل المعزز والبديل ليس حلًا أخيرًا بعد فشل الكلام",
        "الاستخلاب أو السيكريتين أو الأكسجين عالي الضغط",
    )
    missing = [phrase for phrase in required if phrase not in combined]
    if missing:
        raise SystemExit(f"Conceptual safety boundaries are missing: {missing}")
    return guides


CSS = """
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#173f43;background:#f4faf9;line-height:1.95}a{color:#075f59}.wrap{width:min(1160px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;color:#132f33;padding:10px;z-index:100}header{background:#123e43;color:#fff}.head{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:12px 0}.head a{color:#fff;text-decoration:none;font-weight:800}nav{display:flex;gap:12px;flex-wrap:wrap}.hero{padding:58px 0 34px;background:linear-gradient(135deg,#e6f7f3,#fff4f7)}h1{font-size:clamp(2rem,5vw,3.9rem);line-height:1.24;margin:.2em 0}h2{font-size:clamp(1.38rem,3vw,2.05rem);line-height:1.45}h3{line-height:1.5}.lead{font-size:1.1rem;color:#385b60}.notice,.section-card,.panel,.sources{background:#fff;border:1px solid #c8e1de;border-radius:18px;padding:21px;box-shadow:0 12px 28px #123e4312}.notice{border-right:6px solid #8a3156}.grid{display:grid;grid-template-columns:275px 1fr;gap:20px;padding:30px 0}.toc{position:sticky;top:16px;align-self:start;max-height:calc(100vh - 32px);overflow:auto}.toc a{display:block;padding:6px 0;border-bottom:1px solid #e2efed;text-decoration:none}.stack{display:grid;gap:17px}.kicker{font-weight:900;color:#7b294d}.checks{background:#edf9f6;border-radius:13px;padding:12px 18px}.actions{border-right:6px solid #08776f}.urgent{border-right:6px solid #a32626;background:#fff5f5}.sources li{margin:1rem 0;border-bottom:1px solid #e0eeeb;padding-bottom:.8rem}.level{display:inline-block;background:#e7f8f4;border-radius:8px;padding:1px 7px;font-weight:900}.back{display:inline-block;background:#b9eee5;color:#123f43;text-decoration:none;font-weight:900;padding:9px 14px;border-radius:11px}a:focus-visible{outline:3px solid #8a3156;outline-offset:3px}footer{margin-top:30px;padding:28px 0;border-top:1px solid #c9e1de;color:#4a6a6e}@media(max-width:820px){.head,.grid{display:block}.head nav{margin-top:10px}.toc{position:static;max-height:none;margin-bottom:16px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header,.skip,.toc{display:none}.grid{display:block}.section-card,.panel,.sources{box-shadow:none}a{color:#111;text-decoration:underline}}
"""


def schema(guide: dict, payload: dict) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    parent = f"{BASE}/special-needs/autism/"
    graph = [
        {
            "@type": "MedicalWebPage",
            "@id": url + "#page",
            "url": url,
            "name": guide["title"],
            "description": guide["meta_description"],
            "inLanguage": "ar",
            "dateModified": payload["reviewed_at"],
            "isPartOf": {"@id": parent + "#page"},
            "about": {"@type": "MedicalCondition", "name": "Autism"},
            "citation": [source["url"] for source in guide["sources"]],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
                {"@type": "ListItem", "position": 3, "name": "التوحد", "item": parent},
                {"@type": "ListItem", "position": 4, "name": guide["short_title"], "item": url},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def render(guide: dict, payload: dict) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    parent_path = f"{BP}special-needs/autism/"
    toc = "".join(f'<a href="#{e(section["id"])}">{e(section["title"])}</a>' for section in guide["sections"])
    sections: list[str] = []
    for section in guide["sections"]:
        paragraphs = "".join(f"<p>{e(paragraph)}</p>" for paragraph in section["paragraphs"])
        checkpoints = "".join(f"<li>{e(item)}</li>" for item in section["checkpoints"])
        refs = " ".join(f'<a href="#source-{e(ref)}">[{e(ref)}]</a>' for ref in section["source_ids"])
        sections.append(
            f'<section class="section-card" id="{e(section["id"])}"><p class="kicker">محور سريري موثق</p>'
            f'<h2>{e(section["title"])}</h2>{paragraphs}<div class="checks"><h3>أسئلة تحقق</h3><ul>{checkpoints}</ul></div><p>{refs}</p></section>'
        )
    actions = "".join(f"<li>{e(item)}</li>" for item in guide["action_steps"])
    urgent = "".join(f"<li>{e(item)}</li>" for item in guide["urgent"])
    sources = "".join(
        f'<li id="source-{e(source["id"])}"><span class="level">{e(source["level"])}</span> '
        f'<b>{e(source["id"])} — {e(source["organization"])}</b>: '
        f'<a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["title"])}</a> '
        f'<small>تاريخ المراجعة المسجل: {e(source["reviewed"])}</small></li>'
        for source in guide["sources"]
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(guide['title'])}</title><meta name="description" content="{e(guide['meta_description'])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}"><meta property="og:type" content="article"><meta property="og:url" content="{url}"><meta property="og:title" content="{e(guide['title'])}"><meta property="og:description" content="{e(guide['meta_description'])}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema(guide,payload)}</script><style>{CSS}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head"><a href="{BP}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav><a href="{BP}special-needs/">المركز</a><a href="{parent_path}">دليل التوحد</a><a href="{BP}trust/">المنهجية</a></nav></div></header><main id="main"><section class="hero"><div class="wrap"><p class="kicker">مسار علمي متقدم للتوحد</p><h1>{e(guide['short_title'])}</h1><p class="lead">{e(guide['lead'])}</p><p class="notice"><b>حد مهني وسلامة:</b> {e(guide['warning'])}</p><p><a class="back" href="{parent_path}">العودة إلى دليل التوحد</a></p></div></section><div class="wrap grid"><aside class="panel toc"><h2>المحتويات</h2>{toc}<a href="#actions">خطوات عملية</a><a href="#urgent">متى يلزم التحرك العاجل؟</a><a href="#sources">المراجع</a></aside><article class="stack">{''.join(sections)}<section class="panel actions" id="actions"><h2>خطوات عملية</h2><ol>{actions}</ol></section><section class="panel urgent" id="urgent"><h2>متى يلزم التحرك العاجل؟</h2><ul>{urgent}</ul></section><section class="sources" id="sources"><h2>المراجع المستخدمة</h2><ol>{sources}</ol><p><b>حالة المراجعة:</b> مراجعة داخلية بتاريخ {e(payload['reviewed_at'])}. لم تكتمل مراجعة سريرية خارجية مستقلة، والمراجعة التالية مقررة في {e(payload['next_review_due'])}.</p></section></article></div></main><footer><div class="wrap"><p>المحتوى للتثقيف والتنظيم ولا يستبدل التقييم أو العلاج الفردي.</p></div></footer></body></html>'''


def update_parent(site: Path, guides: list[dict]) -> int:
    path = site / "special-needs" / "autism" / "index.html"
    if not path.is_file():
        raise SystemExit("Missing autism parent page for v324 links")
    source = path.read_text(encoding="utf-8")
    pattern = rf'<section\b[^>]*{PARENT_MARKER}[^>]*>.*?</section>'
    cards = "".join(
        f'<article class="condition-card"><h3>{e(guide["short_title"])}</h3><p>{e(guide["meta_description"])}</p>'
        f'<a href="{BP}special-needs/{e(guide["slug"])}/">فتح الدليل المتقدم</a></article>'
        for guide in guides
    )
    block = f'<section class="source-area" {PARENT_MARKER}="related-guides"><h2>مسارات سريرية متقدمة</h2><div class="condition-grid">{cards}</div></section>'
    if re.search(pattern, source, flags=re.I | re.S):
        updated, count = re.subn(pattern, block, source, count=1, flags=re.I | re.S)
    elif PARENT_INSERT in source:
        updated = source.replace(PARENT_INSERT, block + PARENT_INSERT, 1)
        count = 1
    else:
        raise SystemExit("Unable to insert v324 autism links")
    if count != 1 or updated.count(PARENT_MARKER) != 1:
        raise SystemExit("v324 autism parent-link idempotence failed")
    path.write_text(updated, encoding="utf-8")
    return len(guides)


def q(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def update_sitemap(site: Path, guides: list[dict], reviewed: str) -> None:
    path = site / "sitemap-special-needs.xml"
    if not path.is_file():
        raise SystemExit("Missing special-needs sitemap")
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree = ET.parse(path)
    root = tree.getroot()
    for guide in guides:
        url = f"{BASE}/special-needs/{guide['slug']}/"
        rows = [row for row in root.findall("{*}url") if (row.findtext("{*}loc") or "").strip() == url]
        if len(rows) > 1:
            raise SystemExit(f"Duplicate v324 sitemap URL: {url}")
        row = rows[0] if rows else ET.SubElement(root, q(root, "url"))
        values = {"loc": url, "lastmod": reviewed, "changefreq": "monthly", "priority": "0.88"}
        for key, value in values.items():
            node = row.find(f"{{*}}{key}")
            if node is None:
                node = ET.SubElement(row, q(root, key))
            node.text = value
    tree.write(path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict:
    payload = read_payload()
    guides = validate_payload(payload)
    base_dir = site / "special-needs"
    page_reports: list[dict] = []
    for guide in guides:
        source = render(guide, payload)
        target = base_dir / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        page_words = words(source)
        if page_words < 1250 or source.count("<h1") != 1 or source.count('class="section-card"') != 7:
            raise SystemExit({"v324_page_depth_failed": {"slug": guide["slug"], "words": page_words}})
        if BANNED.search(source):
            raise SystemExit(f"Banned terminology rendered in {guide['slug']}")
        page_reports.append({
            "slug": guide["slug"],
            "path": target.relative_to(site).as_posix(),
            "words": page_words,
            "sections": 7,
            "sources": len(guide["sources"]),
        })
    parent_links = update_parent(site, guides)
    update_sitemap(site, guides, payload["reviewed_at"])
    report = {
        "version": VERSION,
        "status": "passed",
        "guide_count": len(guides),
        "guide_slugs": [guide["slug"] for guide in guides],
        "generated_pages": [item["path"] for item in page_reports],
        "minimum_guide_words": min(item["words"] for item in page_reports),
        "total_guide_words": sum(item["words"] for item in page_reports),
        "section_count": sum(item["sections"] for item in page_reports),
        "source_count": sum(item["sources"] for item in page_reports),
        "action_step_count": sum(len(guide["action_steps"]) for guide in guides),
        "urgent_item_count": sum(len(guide["urgent"]) for guide in guides),
        "parent_links_added": parent_links,
        "sitemap_registered": True,
        "external_clinical_review_completed": False,
        "review_status": payload["review_status"],
        "reviewed_at": payload["reviewed_at"],
        "next_review_due": payload["next_review_due"],
        "content_source": CONTENT.relative_to(ROOT).as_posix(),
        "pages": page_reports,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "autism-clinical-pathways-v324.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
