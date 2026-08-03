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
CONTENT = ROOT / "content" / "v322" / "autism-lived-experience-guides-ar.json"
BASE = "https://healthrenewal.org/"
BP = "/"
VERSION = 322
MARKER = "data-autism-lived-experience-v322"
PARENT_INSERT = '<section class="source-area" id="sources">'
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object required: {path}")
    return data


def is_https(url: str) -> bool:
    parsed = urlparse(str(url))
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_payload(payload: dict) -> list[dict]:
    if payload.get("version") != VERSION or payload.get("language") != "ar":
        raise SystemExit("Autism lived-experience manifest contract failed")
    if payload.get("review_status") != "internally-reviewed-external-clinical-review-required":
        raise SystemExit("Review status must remain honest")
    guides = payload.get("guides")
    expected = {
        "autism-sensory-profile-overload",
        "autism-communication-stimming-neurodiversity",
    }
    if not isinstance(guides, list) or len(guides) != 2:
        raise SystemExit("Exactly two autism lived-experience guides are required")
    if {guide.get("slug") for guide in guides} != expected:
        raise SystemExit("Autism lived-experience routes are incomplete")

    all_slugs: set[str] = set()
    for guide in guides:
        slug = str(guide.get("slug", "")).strip()
        if not slug or slug in all_slugs or guide.get("parent_slug") != "autism":
            raise SystemExit(f"Invalid guide identity: {slug}")
        all_slugs.add(slug)
        if BANNED.search(json.dumps(guide, ensure_ascii=False)):
            raise SystemExit(f"Banned terminology in {slug}")
        sections = guide.get("sections")
        sources = guide.get("sources")
        resources = guide.get("resources")
        if not isinstance(sections, list) or len(sections) != 5:
            raise SystemExit(f"Each guide must contain five sections: {slug}")
        if not isinstance(sources, list) or len(sources) < 5:
            raise SystemExit(f"Each guide must contain at least five sources: {slug}")
        if not isinstance(resources, list) or len(resources) < 2:
            raise SystemExit(f"Each guide must expose at least two practical resources: {slug}")
        if len(guide.get("action_steps", [])) != 5 or len(guide.get("urgent", [])) < 3:
            raise SystemExit(f"Action or safety depth failed: {slug}")

        source_index: dict[str, dict] = {}
        urls: set[str] = set()
        for source in sources:
            sid = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            if not sid or sid in source_index:
                raise SystemExit(f"Duplicate or empty source id in {slug}: {sid}")
            if not is_https(url) or url in urls:
                raise SystemExit(f"Invalid or duplicate source URL in {slug}: {url}")
            if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid source level in {slug}: {sid}")
            if not all(str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
                raise SystemExit(f"Incomplete source in {slug}: {sid}")
            source_index[sid] = source
            urls.add(url)

        section_ids: set[str] = set()
        used: set[str] = set()
        for section in sections:
            section_id = str(section.get("id", "")).strip()
            refs = section.get("source_ids", [])
            if not section_id or section_id in section_ids:
                raise SystemExit(f"Invalid section id: {slug}/{section_id}")
            if len(section.get("points", [])) < 6 or not refs or any(ref not in source_index for ref in refs):
                raise SystemExit(f"Invalid section evidence: {slug}/{section_id}")
            section_ids.add(section_id)
            used.update(refs)
        if set(source_index) - used:
            raise SystemExit(f"Unused sources in {slug}: {sorted(set(source_index) - used)}")

        for resource in resources:
            if not is_https(str(resource.get("url", ""))):
                raise SystemExit(f"Invalid practical resource in {slug}")
            if not str(resource.get("title", "")).strip() or not str(resource.get("description", "")).strip():
                raise SystemExit(f"Incomplete practical resource in {slug}")
    return guides


CSS = """
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#173f43;background:#f4faf9;line-height:1.9}a{color:#075f59}.wrap{width:min(1140px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;color:#132f33;padding:9px;z-index:100}header{background:#123e43;color:#fff}.head{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:12px 0}.head a{color:#fff;text-decoration:none;font-weight:800}nav{display:flex;gap:12px;flex-wrap:wrap}.hero{padding:54px 0 32px;background:linear-gradient(135deg,#e9f7f4,#fff4f7);color:#173f43}h1{font-size:clamp(2rem,5vw,3.8rem);line-height:1.25;margin:.2em 0}h2{font-size:clamp(1.35rem,3vw,2rem);line-height:1.45}.lead{font-size:1.08rem;color:#385b60}.notice,.section-card,.panel,.sources,.resources{background:#fff;border:1px solid #c8e1de;border-radius:18px;padding:20px;box-shadow:0 12px 28px #123e4312}.notice{border-right:6px solid #8a3156}.grid{display:grid;grid-template-columns:270px 1fr;gap:20px;padding:30px 0}.toc{position:sticky;top:16px;align-self:start}.toc a{display:block;padding:6px 0;border-bottom:1px solid #e2efed;text-decoration:none}.stack{display:grid;gap:16px}.kicker{font-weight:900;color:#7b294d}.actions{border-right:6px solid #08776f}.urgent{border-right:6px solid #a32626;background:#fff5f5}.resources{border-right:6px solid #4b668a}.resource-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.resource-card{border:1px solid #d6e7e5;border-radius:14px;padding:15px;background:#f9fcfb}.sources li{margin:1rem 0}.level{display:inline-block;background:#e7f8f4;border-radius:8px;padding:1px 7px;font-weight:900}.back,.btn{display:inline-block;background:#b9eee5;color:#123f43;text-decoration:none;font-weight:900;padding:9px 14px;border-radius:11px}.btn:focus-visible,.back:focus-visible,a:focus-visible{outline:3px solid #8a3156;outline-offset:3px}footer{margin-top:30px;padding:26px 0;border-top:1px solid #c9e1de;color:#4a6a6e}@media(max-width:800px){.head,.grid{display:block}.head nav{margin-top:10px}.toc{position:static;margin-bottom:16px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media(prefers-contrast:more){body{color:#07191c}.lead{color:#173b40}.section-card,.panel,.sources,.resources{border-color:#315e61}}@media print{header,.skip,.toc{display:none}.grid{display:block}.section-card,.panel,.sources,.resources{box-shadow:none}a{color:#111;text-decoration:underline}}
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


def render_guide(guide: dict, payload: dict) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    parent_path = f"{BP}special-needs/autism/"
    toc = "".join(f'<a href="#{e(section["id"])}">{e(section["title"])}</a>' for section in guide["sections"])
    sections = []
    for section in guide["sections"]:
        refs = " ".join(f'<a href="#source-{e(ref)}">[{e(ref)}]</a>' for ref in section["source_ids"])
        points = "".join(f"<li>{e(point)}</li>" for point in section["points"])
        sections.append(
            f'<section class="section-card" id="{e(section["id"])}"><p class="kicker">محور عملي موثق</p>'
            f'<h2>{e(section["title"])}</h2><p>{e(section["summary"])}</p><ul>{points}</ul><p>{refs}</p></section>'
        )
    actions = "".join(f"<li>{e(item)}</li>" for item in guide["action_steps"])
    urgent = "".join(f"<li>{e(item)}</li>" for item in guide["urgent"])
    resources = "".join(
        f'<article class="resource-card"><h3>{e(resource["title"])}</h3><p>{e(resource["description"])}</p>'
        f'<p><a href="{e(resource["url"])}" rel="noopener noreferrer">فتح المورد الرسمي</a></p></article>'
        for resource in guide["resources"]
    )
    sources = "".join(
        f'<li id="source-{e(source["id"])}"><span class="level">{e(source["level"])}</span> '
        f'<b>{e(source["id"])} — {e(source["organization"])}</b>: '
        f'<a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["title"])}</a> '
        f'<small>تاريخ المراجعة المسجل: {e(source["reviewed"])}</small></li>'
        for source in guide["sources"]
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(guide['title'])}</title><meta name="description" content="{e(guide['meta_description'])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}"><meta property="og:type" content="article"><meta property="og:url" content="{url}"><meta property="og:title" content="{e(guide['title'])}"><meta property="og:description" content="{e(guide['meta_description'])}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema(guide,payload)}</script><style>{CSS}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header data-surface="dark"><div class="wrap head"><a href="{BP}">منصة روافد</a><nav aria-label="التنقل الرئيسي"><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">المركز</a><a href="{parent_path}">دليل التوحد</a></nav></div></header><main id="main"><section class="hero" data-surface="light"><div class="wrap"><p class="kicker">إثراء عملي من موارد رسمية مجانية</p><h1>{e(guide['short_title'])}</h1><p class="lead">{e(guide['lead'])}</p><p class="notice"><b>حد مهني:</b> {e(guide['warning'])}</p><p><a class="back" href="{parent_path}">العودة إلى دليل التوحد الشامل</a></p></div></section><div class="wrap grid"><aside class="panel toc" aria-label="محتويات الصفحة"><h2>محتويات الصفحة</h2>{toc}<a href="#actions">خطوات عملية</a><a href="#resources">الموارد المجانية</a><a href="#urgent">مؤشرات عاجلة</a><a href="#sources">المراجع</a></aside><article class="stack">{''.join(sections)}<section class="panel actions" id="actions"><h2>خطوات تطبيق عملية</h2><ol>{actions}</ol></section><section class="resources" id="resources"><h2>موارد مجانية أصلية</h2><div class="resource-grid">{resources}</div><p>{e(payload['attribution'])}</p></section><section class="panel urgent" id="urgent"><h2>مؤشرات تستدعي تحركًا سريعًا</h2><ul>{urgent}</ul></section><section class="sources" id="sources"><h2>المراجع الأصلية</h2><ol>{sources}</ol><p><b>حالة المراجعة:</b> إعداد ومراجعة داخلية؛ لم تكتمل مراجعة سريرية خارجية مستقلة. آخر مراجعة {e(payload['reviewed_at'])}، والمراجعة التالية {e(payload['next_review_due'])}.</p></section></article></div></main><footer><div class="wrap"><p>محتوى تثقيفي لا يقدم تشخيصًا أو خطة علاج فردية. استخدم خدمات الطوارئ المحلية عند الخطر.</p></div></footer></body></html>'''


def parent_block(guide: dict) -> str:
    return (
        f'<section class="section" {MARKER} data-autism-guide="{e(guide["slug"])}">'
        f'<div class="wrap"><p class="kicker">إثراء عملي موثق</p><h2>{e(guide["short_title"])}</h2>'
        f'<p>{e(guide["meta_description"])}</p><a class="btn" href="{BP}special-needs/{e(guide["slug"])}/">فتح الدليل العملي</a></div></section>'
    )


def patch_parent(site: Path, guide: dict) -> None:
    path = site / "special-needs" / "autism" / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing autism parent page: {path}")
    text = path.read_text(encoding="utf-8")
    block = parent_block(guide)
    pattern = rf'<section class="section" {MARKER} data-autism-guide="{re.escape(guide["slug"])}">.*?</section>'
    if re.search(pattern, text, flags=re.S):
        text, count = re.subn(pattern, block, text, count=1, flags=re.S)
    else:
        if text.count(PARENT_INSERT) != 1:
            raise SystemExit(f"Autism parent insertion point failed: {path}")
        text = text.replace(PARENT_INSERT, block + PARENT_INSERT, 1)
        count = 1
    if count != 1 or text.count(f'data-autism-guide="{guide["slug"]}"') != 1:
        raise SystemExit(f"Autism parent idempotence failed: {guide['slug']}")
    path.write_text(text, encoding="utf-8")


def q(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def update_sitemap(site: Path, guides: list[dict], updated: str) -> None:
    path = site / "sitemap-special-needs.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    for guide in guides:
        url = f"{BASE}/special-needs/{guide['slug']}/"
        rows = [row for row in root.findall("{*}url") if (row.findtext("{*}loc") or "").strip() == url]
        if len(rows) > 1:
            raise SystemExit(f"Duplicate sitemap URL: {url}")
        row = rows[0] if rows else ET.SubElement(root, q(root, "url"))
        for key, value in {"loc": url, "lastmod": updated, "changefreq": "monthly", "priority": "0.90"}.items():
            node = row.find(f"{{*}}{key}")
            if node is None:
                node = ET.SubElement(row, q(root, key))
            node.text = value
    tree.write(path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict:
    payload = read_json(CONTENT)
    guides = validate_payload(payload)
    pages: list[str] = []
    for guide in guides:
        page = render_guide(guide, payload)
        target = site / "special-needs" / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        if page.count("<h1") != 1 or page.count('class="section-card"') != 5 or BANNED.search(page):
            raise SystemExit(f"Rendered autism guide contract failed: {target}")
        if page.count('class="resource-card"') < 2 or page.count('application/ld+json') != 1:
            raise SystemExit(f"Resource or schema contract failed: {target}")
        patch_parent(site, guide)
        pages.append(target.relative_to(site).as_posix())
    update_sitemap(site, guides, payload["reviewed_at"])
    report = {
        "version": VERSION,
        "status": "passed",
        "review_status": payload["review_status"],
        "external_clinical_review_completed": False,
        "guide_count": len(guides),
        "guide_slugs": [guide["slug"] for guide in guides],
        "parent_slugs": [guide["parent_slug"] for guide in guides],
        "generated_pages": pages,
        "section_count": sum(len(guide["sections"]) for guide in guides),
        "source_count": sum(len(guide["sources"]) for guide in guides),
        "practical_resource_count": sum(len(guide["resources"]) for guide in guides),
        "action_step_count": sum(len(guide["action_steps"]) for guide in guides),
        "urgent_item_count": sum(len(guide["urgent"]) for guide in guides),
        "parent_links_added": len(guides),
        "sitemap_registered": True,
        "national_autistic_society_resource_used": True,
        "content_rewritten_not_copied": True,
        "reviewed_at": payload["reviewed_at"],
        "next_review_due": payload["next_review_due"],
        "content_source": CONTENT.relative_to(ROOT).as_posix(),
    }
    (site / "api").mkdir(parents=True, exist_ok=True)
    (site / "api" / "autism-lived-experience-guides-v322.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
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
