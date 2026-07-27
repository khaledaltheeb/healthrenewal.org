#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "v324" / "protection-safeguarding"
MANIFEST = CONTENT_DIR / "manifest-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
BP = "/pterminology-site/"
VERSION = 324
MARKER = "data-protection-safeguarding-v324"
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")
EXPECTED_SLUGS = [
    "safeguarding-risk-assessment-and-prevention",
    "recognizing-abuse-neglect-and-diagnostic-overshadowing",
    "accessible-safeguarding-reporting-and-first-line-response",
    "disability-inclusive-school-bullying-response",
    "safeguarding-in-services-centres-and-residential-care",
    "financial-exploitation-coercion-and-supported-decision-making",
]

def e(value: object) -> str:
    return html.escape(str(value), quote=True)

def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"JSON object required: {path}")
    return value

def load_payload() -> dict:
    payload = read_json(MANIFEST)
    slugs = payload.get("guide_slugs")
    if not isinstance(slugs, list) or slugs != EXPECTED_SLUGS:
        raise SystemExit("Protection safeguarding manifest must list the six expected guide slugs")
    payload["guides"] = [read_json(CONTENT_DIR / "guides" / f"{slug}.json") for slug in slugs]
    return payload


def is_https(url: str) -> bool:
    parsed = urlparse(str(url))
    return parsed.scheme == "https" and bool(parsed.netloc)

def visible_words(value: object) -> int:
    text = json.dumps(value, ensure_ascii=False)
    return len(re.findall(r"[\w\u0600-\u06FF]+", text))

def validate_payload(payload: dict) -> tuple[list[dict], dict[str, dict]]:
    if payload.get("version") != VERSION or payload.get("language") != "ar":
        raise SystemExit("Protection cluster version/language contract failed")
    if payload.get("review_status") != "internally-reviewed-external-safeguarding-review-required":
        raise SystemExit("Protection cluster review status must remain honest")
    if not all(str(payload.get(k, "")).strip() for k in ("reviewed_at", "next_review_due")):
        raise SystemExit("Protection cluster review dates are required")
    sources = payload.get("sources")
    guides = payload.get("guides")
    if not isinstance(sources, list) or len(sources) < 10:
        raise SystemExit("At least ten institutional sources are required")
    if not isinstance(guides, list) or [g.get("slug") for g in guides] != EXPECTED_SLUGS:
        raise SystemExit("Six ordered protection routes are required")
    source_index: dict[str, dict] = {}
    urls: set[str] = set()
    for source in sources:
        sid = str(source.get("id", "")).strip()
        url = str(source.get("url", "")).strip()
        if not sid or sid in source_index or not is_https(url) or url in urls:
            raise SystemExit(f"Invalid or duplicate source: {sid}/{url}")
        if not all(str(source.get(k, "")).strip() for k in ("organization", "title", "level", "use")):
            raise SystemExit(f"Incomplete source metadata: {sid}")
        source_index[sid] = source
        urls.add(url)
    used: set[str] = set()
    for guide in guides:
        if BANNED.search(json.dumps(guide, ensure_ascii=False)):
            raise SystemExit(f"Banned terminology in {guide.get('slug')}")
        if visible_words(guide) < 620:
            raise SystemExit(f"Protection guide is too thin: {guide.get('slug')} ({visible_words(guide)} source words)")
        sections = guide.get("sections")
        if not isinstance(sections, list) or len(sections) != 5:
            raise SystemExit(f"Exactly five analytical sections required: {guide.get('slug')}")
        if len(guide.get("urgent", [])) < 3 or len(guide.get("checklist", [])) < 6:
            raise SystemExit(f"Urgent/checklist depth failed: {guide.get('slug')}")
        section_ids: set[str] = set()
        for section in sections:
            section_id = str(section.get("id", "")).strip()
            refs = section.get("source_ids")
            paragraphs = section.get("paragraphs")
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Duplicate section id: {guide.get('slug')}/{section_id}")
            if not isinstance(paragraphs, list) or len(paragraphs) < 2:
                raise SystemExit(f"Section depth failed: {guide.get('slug')}/{section_id}")
            if not isinstance(refs, list) or not refs or any(ref not in source_index for ref in refs):
                raise SystemExit(f"Section evidence failed: {guide.get('slug')}/{section_id}")
            section_ids.add(section_id)
            used.update(refs)
    unused = sorted(set(source_index) - used)
    if unused:
        raise SystemExit(f"Unused protection sources: {unused}")
    return guides, source_index

CSS = '''
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#173f43;background:#f4faf9;line-height:1.95}a{color:#075f59}.wrap{width:min(1160px,92%);margin:auto}.skip{position:absolute;inset-inline-start:-9999px}.skip:focus{inset-inline-start:8px;top:8px;background:#fff;color:#102f34;padding:10px;z-index:99}header{background:#123e43;color:#fff}.head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:13px 0}.head a{color:#fff;text-decoration:none;font-weight:800}nav{display:flex;gap:12px;flex-wrap:wrap}.hero{padding:58px 0 34px;background:linear-gradient(135deg,#dcf4ef,#fff7fb);color:#173f43}h1{font-size:clamp(2rem,5vw,3.7rem);line-height:1.3;margin:.2em 0}h2{font-size:clamp(1.35rem,3vw,2rem);line-height:1.45}.lead{font-size:1.08rem;color:#365e62}.notice,.section-card,.panel,.sources{background:#fff;border:1px solid #c7dfdc;border-radius:18px;padding:21px;box-shadow:0 12px 28px #123e4312}.notice{border-inline-start:6px solid #913c5d}.layout{display:grid;grid-template-columns:270px 1fr;gap:22px;padding:32px 0}.toc{position:sticky;top:16px;align-self:start}.toc a{display:block;padding:7px 0;border-bottom:1px solid #e0eeec;text-decoration:none}.stack{display:grid;gap:18px}.kicker{font-weight:900;color:#7c2d50}.urgent{border-inline-start:6px solid #a32626;background:#fff5f5}.check{border-inline-start:6px solid #08776f}.sources li{margin:1rem 0}.source-level{display:inline-block;background:#e4f6f2;border-radius:8px;padding:1px 7px;font-weight:900}.back{display:inline-block;background:#b7ece3;color:#123f43;text-decoration:none;font-weight:900;padding:10px 15px;border-radius:11px}.related{display:flex;gap:10px;flex-wrap:wrap}.related a{background:#edf7f5;border:1px solid #c7dfdc;border-radius:10px;padding:7px 10px;text-decoration:none}.cluster-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin-top:18px}.cluster-card{background:#fff;border:1px solid #c7dfdc;border-radius:15px;padding:16px}.cluster-card a{font-weight:900}footer{margin-top:34px;padding:28px 0;border-top:1px solid #c7dfdc;color:#527174}@media(max-width:820px){.head,.layout{display:block}.head nav{margin-top:10px}.toc{position:static;margin-bottom:18px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media(prefers-contrast:more){a{text-decoration:underline}.notice,.section-card,.panel,.sources{border-width:2px;box-shadow:none}}@media print{header,.skip,.toc{display:none}.layout{display:block}.section-card,.panel,.sources{box-shadow:none;break-inside:avoid}a{color:#000}}
'''

def schema(guide: dict, payload: dict) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    graph = [
        {"@type":"Article","@id":url+"#article","url":url,"headline":guide["title"],"description":guide["meta_description"],"inLanguage":"ar","dateModified":payload["reviewed_at"],"isPartOf":{"@id":f"{BASE}/special-needs/#protection-safeguarding"},"publisher":{"@type":"Organization","name":"منصة الصحة النفسية وذوي الاحتياجات الخاصة"}},
        {"@type":"BreadcrumbList","itemListElement":[
            {"@type":"ListItem","position":1,"name":"الرئيسية","item":BASE+"/"},
            {"@type":"ListItem","position":2,"name":"ذوو الاحتياجات الخاصة","item":BASE+"/special-needs/"},
            {"@type":"ListItem","position":3,"name":"الحماية ومنع الاستغلال","item":BASE+"/special-needs/#protection-safeguarding"},
            {"@type":"ListItem","position":4,"name":guide["short_title"],"item":url},
        ]},
    ]
    return json.dumps({"@context":"https://schema.org","@graph":graph}, ensure_ascii=False).replace("</","<\\/")

def render_page(guide: dict, payload: dict, source_index: dict[str, dict]) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    toc = "".join(f'<a href="#{e(s["id"])}">{e(s["title"])}</a>' for s in guide["sections"])
    sections_html = []
    used = []
    for section in guide["sections"]:
        used.extend(section["source_ids"])
        paragraphs = "".join(f"<p>{e(p)}</p>" for p in section["paragraphs"])
        refs = " ".join(f'<a href="#source-{e(sid)}">[{e(sid)}]</a>' for sid in section["source_ids"])
        sections_html.append(f'<section class="section-card" id="{e(section["id"])}"><p class="kicker">محور حماية مؤسسي</p><h2>{e(section["title"])}</h2><p><strong>{e(section["summary"])}</strong></p>{paragraphs}<p>{refs}</p></section>')
    urgent = "".join(f"<li>{e(item)}</li>" for item in guide["urgent"])
    checklist = "".join(f"<li>{e(item)}</li>" for item in guide["checklist"])
    source_rows = []
    for sid in dict.fromkeys(used):
        source = source_index[sid]
        source_rows.append(f'<li id="source-{e(sid)}"><span class="source-level">{e(source["level"])}</span> <b>{e(sid)} — {e(source["organization"])}</b>: <a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["title"])}</a><p>{e(source["use"])}</p></li>')
    related = "".join(f'<a href="{BP}special-needs/{e(slug)}/">{e(slug.replace("-", " "))}</a>' for slug in guide.get("related_routes", []))
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(guide["title"])}</title><meta name="description" content="{e(guide["meta_description"])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}"><meta property="og:type" content="article"><meta property="og:url" content="{url}"><meta property="og:title" content="{e(guide["title"])}"><meta property="og:description" content="{e(guide["meta_description"])}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema(guide,payload)}</script><style>{CSS}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head"><a href="{BP}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">المركز</a><a href="{BP}special-needs/#protection-safeguarding">مسار الحماية</a></nav></div></header><main id="main"><section class="hero"><div class="wrap"><p class="kicker">الحماية ومنع الإساءة والاستغلال</p><h1>{e(guide["short_title"])}</h1><p class="lead">{e(guide["lead"])}</p><p class="notice"><b>الحدود المهنية:</b> {e(guide["professional_limits"])}</p><p><a class="back" href="{BP}special-needs/#protection-safeguarding">العودة إلى مسار الحماية</a></p></div></section><div class="wrap layout"><aside class="panel toc"><h2>محتويات الصفحة</h2>{toc}<a href="#urgent">مؤشرات عاجلة</a><a href="#checklist">قائمة مراجعة</a><a href="#sources">المراجع</a></aside><article class="stack">{''.join(sections_html)}<section class="panel urgent" id="urgent"><h2>مؤشرات تستدعي تحركًا عاجلًا</h2><ul>{urgent}</ul></section><section class="panel check" id="checklist"><h2>قائمة مراجعة تنفيذية</h2><ul>{checklist}</ul></section><section class="panel"><h2>أدلة مترابطة</h2><div class="related">{related}</div></section><section class="sources" id="sources"><h2>المراجع الأصلية المستخدمة</h2><ol>{''.join(source_rows)}</ol><p><b>حالة المراجعة:</b> مراجعة داخلية؛ لم تكتمل مراجعة خارجية مستقلة من متخصص في الحماية. آخر مراجعة {e(payload["reviewed_at"])}، والمراجعة التالية {e(payload["next_review_due"])}.</p></section></article></div></main><footer><div class="wrap"><p>محتوى تثقيفي مؤسسي لا يحل محل القانون أو التحقيق أو التقييم الفردي. عند الخطر استخدم خدمات الطوارئ والحماية المحلية.</p></div></footer></body></html>'''

def cluster_block(guides: list[dict]) -> str:
    card_style = "background:#fff;border:1px solid #c7dfdc;border-radius:15px;padding:16px"
    cards = "".join(
        f'<article class="cluster-card" style="{card_style}"><h3>{e(g["short_title"])}</h3>'
        f'<p>{e(g["meta_description"])}</p>'
        f'<a style="font-weight:900" href="{BP}special-needs/{e(g["slug"])}/">فتح الدليل المتخصص</a></article>'
        for g in guides
    )
    return (
        f'<div {MARKER} class="protection-safeguarding-v324" style="margin:1.25rem 0">'
        '<h3>المسار المؤسسي المتقدم للحماية</h3>'
        '<p>ستة أدلة مترابطة تنقل القسم من التحذير العام إلى الوقاية والحوكمة والاستجابة والمتابعة، دون تكرار دليل الحماية الأساسي أو الأمان الرقمي.</p>'
        f'<div class="cluster-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin-top:1rem">{cards}</div></div>'
    )

def patch_parent(site: Path, guides: list[dict]) -> None:
    path = site / "special-needs" / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing special-needs parent page: {path}")
    text = path.read_text(encoding="utf-8")
    block = cluster_block(guides)
    existing = re.compile(rf'<div {MARKER}\b.*?</div></div>', re.S)
    if existing.search(text):
        text = existing.sub(block, text, count=1)
    else:
        section_open = re.search(r'<section\b[^>]*\bid=["\']protection-safeguarding["\'][^>]*>', text, re.I)
        if not section_open:
            raise SystemExit("Missing #protection-safeguarding insertion anchor")
        pos = section_open.end()
        text = text[:pos] + block + text[pos:]
    if text.count(MARKER) != 1:
        raise SystemExit("Protection cluster parent marker idempotence failed")
    for guide in guides:
        if text.count(f'/special-needs/{guide["slug"]}/') != 1:
            raise SystemExit(f"Protection parent link count failed: {guide['slug']}")
    path.write_text(text, encoding="utf-8")

def sitemap_tag(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name

def update_sitemap(site: Path, guides: list[dict], updated: str) -> None:
    path = site / "sitemap-special-needs.xml"
    if not path.is_file():
        raise SystemExit(f"Missing special-needs sitemap: {path}")
    tree = ET.parse(path)
    root = tree.getroot()
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    expected = {f"{BASE}/special-needs/{g['slug']}/" for g in guides}
    for row in list(root.findall("{*}url")):
        if (row.findtext("{*}loc") or "").strip() in expected:
            root.remove(row)
    for guide in guides:
        row = ET.SubElement(root, sitemap_tag(root, "url"))
        for key, value in {"loc":f"{BASE}/special-needs/{guide['slug']}/","lastmod":updated,"changefreq":"monthly","priority":"0.88"}.items():
            ET.SubElement(row, sitemap_tag(root, key)).text = value
    tree.write(path, encoding="utf-8", xml_declaration=True)

def publish(site: Path) -> dict:
    payload = load_payload()
    guides, source_index = validate_payload(payload)
    for guide in guides:
        shutil.rmtree(site / "special-needs" / guide["slug"], ignore_errors=True)
    (site / "api" / "protection-safeguarding-cluster-v324.json").unlink(missing_ok=True)
    generated = []
    rendered_words = {}
    for guide in guides:
        page = render_page(guide, payload, source_index)
        target = site / "special-needs" / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        words = len(re.findall(r"[\w\u0600-\u06FF]+", re.sub(r"<[^>]+>", " ", page)))
        if page.count("<h1") != 1 or page.count('class="section-card"') != 5 or words < 650:
            raise SystemExit(f"Rendered protection guide contract failed: {target}/{words}")
        generated.append(target.relative_to(site).as_posix())
        rendered_words[guide["slug"]] = words
    patch_parent(site, guides)
    update_sitemap(site, guides, payload["reviewed_at"])
    report = {
        "version":VERSION,"status":"passed","review_status":payload["review_status"],
        "external_safeguarding_review_completed":False,"guide_count":len(guides),
        "guide_slugs":[g["slug"] for g in guides],"generated_pages":generated,
        "section_count":sum(len(g["sections"]) for g in guides),"source_count":len(source_index),
        "minimum_source_words":min(visible_words(g) for g in guides),
        "minimum_rendered_words":min(rendered_words.values()),
        "urgent_item_count":sum(len(g["urgent"]) for g in guides),
        "checklist_item_count":sum(len(g["checklist"]) for g in guides),
        "parent_anchor":payload["cluster"]["anchor"],"parent_links_added":len(guides),
        "sitemap_registered":True,"reviewed_at":payload["reviewed_at"],
        "next_review_due": payload["next_review_due"],
        "content_source": MANIFEST.relative_to(ROOT).as_posix(),
        "guide_source_files": [str((CONTENT_DIR / "guides" / f"{slug}.json").relative_to(ROOT)) for slug in payload["guide_slugs"]],
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "protection-safeguarding-cluster-v324.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    site = parser.parse_args().site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
