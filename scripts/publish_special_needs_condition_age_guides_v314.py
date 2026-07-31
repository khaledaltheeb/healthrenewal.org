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
CONTENT = ROOT / "content" / "v314" / "special-needs-condition-age-guides-ar.json"
BASE = "https://healthrenewal.org/"
BP = "/"
VERSION = 314
MARKER = "data-condition-age-guides-v314"
PARENT_INSERT = '<section class="source-area" id="sources">'
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Invalid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"JSON object required: {path}")
    return payload


def is_https(url: str) -> bool:
    parsed = urlparse(str(url))
    return parsed.scheme == "https" and bool(parsed.netloc)


def validate_payload(payload: dict) -> list[dict]:
    if payload.get("version") != VERSION or payload.get("language") != "ar":
        raise SystemExit("Age-guide manifest contract failed")
    if payload.get("review_status") != "internally-reviewed-external-clinical-review-required":
        raise SystemExit("Age-guide review status must remain honest")
    guides = payload.get("guides")
    if not isinstance(guides, list) or len(guides) != 2:
        raise SystemExit("Exactly two age guides are required")
    slugs = {guide.get("slug") for guide in guides}
    parents = {guide.get("parent_slug") for guide in guides}
    if slugs != {"autism-signs-by-age", "down-syndrome-health-by-age"}:
        raise SystemExit(f"Unexpected guide routes: {slugs}")
    if parents != {"autism", "down-syndrome"}:
        raise SystemExit(f"Unexpected parent routes: {parents}")

    source_ids: set[str] = set()
    source_urls: set[str] = set()
    for guide in guides:
        serialized = json.dumps(guide, ensure_ascii=False)
        if BANNED.search(serialized):
            raise SystemExit(f"Banned terminology in {guide.get('slug')}")
        if len(guide.get("stages", [])) != 4:
            raise SystemExit(f"Each age guide must contain four stages: {guide.get('slug')}")
        if len(guide.get("urgent", [])) < 3 or len(guide.get("actions", [])) < 4:
            raise SystemExit(f"Safety or action depth failed: {guide.get('slug')}")
        sources = guide.get("sources")
        if not isinstance(sources, list) or len(sources) < 3:
            raise SystemExit(f"Source depth failed: {guide.get('slug')}")
        index: dict[str, dict] = {}
        for source in sources:
            sid = str(source.get("id", "")).strip()
            url = str(source.get("url", "")).strip()
            if not sid or sid in source_ids or sid in index:
                raise SystemExit(f"Duplicate or empty source id: {sid}")
            if not is_https(url) or url in source_urls:
                raise SystemExit(f"Invalid or duplicate source URL: {url}")
            if source.get("level") not in {"S1", "S2", "S3", "S4", "S5"}:
                raise SystemExit(f"Invalid source level: {sid}")
            if not all(str(source.get(key, "")).strip() for key in ("organization", "title", "reviewed")):
                raise SystemExit(f"Incomplete source: {sid}")
            index[sid] = source
            source_ids.add(sid)
            source_urls.add(url)
        stage_ids: set[str] = set()
        used: set[str] = set()
        for stage in guide["stages"]:
            stage_id = str(stage.get("id", "")).strip()
            refs = stage.get("source_ids", [])
            if not stage_id or stage_id in stage_ids:
                raise SystemExit(f"Invalid stage id: {guide.get('slug')}/{stage_id}")
            if len(stage.get("points", [])) < 5 or not refs or any(ref not in index for ref in refs):
                raise SystemExit(f"Invalid stage evidence: {guide.get('slug')}/{stage_id}")
            stage_ids.add(stage_id)
            used.update(refs)
        unused = sorted(set(index) - used)
        if unused:
            raise SystemExit(f"Unused guide sources: {guide.get('slug')}/{unused}")
    return guides


CSS = """
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;font-family:Tahoma,Arial,sans-serif;color:#153f43;background:#f4fbf9;line-height:1.9}a{color:#066a64}.wrap{width:min(1120px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;padding:9px;z-index:50}header{background:#123f43;color:#fff}.head{display:flex;justify-content:space-between;align-items:center;gap:14px;padding:12px 0}.brand,.head a{color:#fff;text-decoration:none;font-weight:800}nav{display:flex;gap:12px;flex-wrap:wrap}.hero{padding:54px 0 30px;background:linear-gradient(135deg,#e7f8f4,#fff)}h1{font-size:clamp(2rem,5vw,4rem);line-height:1.25;margin:.2em 0}h2{font-size:clamp(1.4rem,3vw,2rem);line-height:1.4}.lead{font-size:1.08rem;color:#46686b}.notice,.stage,.panel,.sources{background:#fff;border:1px solid #c9e1de;border-radius:18px;padding:20px;box-shadow:0 12px 28px #123f4312}.notice{border-right:6px solid #8a3156}.grid{display:grid;grid-template-columns:260px 1fr;gap:20px;padding:30px 0}.toc{position:sticky;top:16px;align-self:start}.toc a{display:block;padding:6px 0;border-bottom:1px solid #e3efed;text-decoration:none}.stack{display:grid;gap:16px}.kicker{font-weight:900;color:#8a3156}.urgent{border-right:6px solid #a32626;background:#fff4f4}.actions{border-right:6px solid #08776f}.sources li{margin:1rem 0}.level{display:inline-block;background:#e7f8f4;border-radius:8px;padding:1px 7px;font-weight:900}.back{display:inline-block;background:#b9eee5;color:#123f43;text-decoration:none;font-weight:900;padding:9px 14px;border-radius:11px}footer{margin-top:30px;padding:26px 0;border-top:1px solid #c9e1de;color:#527174}@media(max-width:800px){.head,.grid{display:block}.head nav{margin-top:10px}.toc{position:static;margin-bottom:16px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{header,.skip,.toc{display:none}.grid{display:block}.stage,.panel,.sources{box-shadow:none}}
"""


def schema(guide: dict, payload: dict) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    parent = f"{BASE}/special-needs/{guide['parent_slug']}/"
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
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
                {"@type": "ListItem", "position": 3, "name": guide["parent_slug"], "item": parent},
                {"@type": "ListItem", "position": 4, "name": guide["short_title"], "item": url},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def render_guide(guide: dict, payload: dict) -> str:
    url = f"{BASE}/special-needs/{guide['slug']}/"
    parent_path = f"{BP}special-needs/{guide['parent_slug']}/"
    toc = "".join(f'<a href="#{e(stage["id"])}">{e(stage["title"])}</a>' for stage in guide["stages"])
    stages = []
    for stage in guide["stages"]:
        refs = " ".join(f'<a href="#source-{e(ref)}">[{e(ref)}]</a>' for ref in stage["source_ids"])
        points = "".join(f"<li>{e(point)}</li>" for point in stage["points"])
        stages.append(
            f'<section class="stage" id="{e(stage["id"])}"><p class="kicker">مرحلة عمرية</p>'
            f'<h2>{e(stage["title"])}</h2><p>{e(stage["summary"])}</p><ul>{points}</ul><p>{refs}</p></section>'
        )
    urgent = "".join(f"<li>{e(item)}</li>" for item in guide["urgent"])
    actions = "".join(f"<li>{e(item)}</li>" for item in guide["actions"])
    sources = "".join(
        f'<li id="source-{e(source["id"])}"><span class="level">{e(source["level"])}</span> '
        f'<b>{e(source["id"])} — {e(source["organization"])}</b>: '
        f'<a href="{e(source["url"])}" rel="noopener noreferrer">{e(source["title"])}</a> '
        f'<small>تاريخ المصدر أو مراجعته المسجل: {e(source["reviewed"])}</small></li>'
        for source in guide["sources"]
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(guide['title'])}</title><meta name="description" content="{e(guide['meta_description'])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{url}"><link rel="alternate" hreflang="ar" href="{url}"><link rel="alternate" hreflang="x-default" href="{url}"><meta property="og:type" content="article"><meta property="og:url" content="{url}"><meta property="og:title" content="{e(guide['title'])}"><meta property="og:description" content="{e(guide['meta_description'])}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema(guide,payload)}</script><style>{CSS}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى</a><header><div class="wrap head"><a class="brand" href="{BP}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav><a href="{BP}">الرئيسية</a><a href="{BP}special-needs/">المركز</a><a href="{parent_path}">الدليل الشامل</a></nav></div></header><main id="main"><section class="hero"><div class="wrap"><p class="kicker">دليل عملي مرتبط بالعمر</p><h1>{e(guide['short_title'])}</h1><p class="lead">{e(guide['lead'])}</p><p class="notice"><b>تنبيه:</b> {e(guide['warning'])}</p><p><a class="back" href="{parent_path}">العودة إلى الدليل العلمي الشامل</a></p></div></section><div class="wrap grid"><aside class="panel toc"><h2>محتويات الصفحة</h2>{toc}<a href="#urgent">مؤشرات عاجلة</a><a href="#actions">خطوات عملية</a><a href="#sources">المراجع</a></aside><article class="stack">{''.join(stages)}<section class="panel urgent" id="urgent"><h2>مؤشرات تستدعي تحركًا سريعًا</h2><ul>{urgent}</ul></section><section class="panel actions" id="actions"><h2>خطوات عملية للأسرة والفريق</h2><ol>{actions}</ol></section><section class="sources" id="sources"><h2>المراجع الأصلية</h2><ol>{sources}</ol><p><b>حالة المراجعة:</b> إعداد ومراجعة داخلية؛ لم تكتمل مراجعة سريرية خارجية مستقلة. آخر مراجعة {e(payload['reviewed_at'])}، والمراجعة التالية {e(payload['next_review_due'])}.</p></section></article></div></main><footer><div class="wrap"><p>محتوى تثقيفي لا يقدم تشخيصًا أو خطة علاج فردية. استخدم خدمات الطوارئ المحلية عند الخطر.</p></div></footer></body></html>'''


def parent_block(guide: dict) -> str:
    return (
        f'<section class="section" {MARKER} data-age-guide="{e(guide["slug"])}">'
        f'<div class="wrap"><p class="kicker">دليل مرتبط بالعمر</p><h2>{e(guide["short_title"])}</h2>'
        f'<p>{e(guide["meta_description"])}</p><a class="btn" href="{BP}special-needs/{e(guide["slug"])}/">فتح الدليل العمري</a></div></section>'
    )


def patch_parent(site: Path, guide: dict) -> None:
    path = site / "special-needs" / guide["parent_slug"] / "index.html"
    if not path.is_file():
        raise SystemExit(f"Missing parent condition page: {path}")
    text = path.read_text(encoding="utf-8")
    block = parent_block(guide)
    pattern = rf'<section class="section" {MARKER} data-age-guide="{re.escape(guide["slug"])}">.*?</section>'
    if re.search(pattern, text, flags=re.S):
        text, count = re.subn(pattern, block, text, count=1, flags=re.S)
    else:
        if text.count(PARENT_INSERT) != 1:
            raise SystemExit(f"Parent insertion point failed: {path}")
        text = text.replace(PARENT_INSERT, block + PARENT_INSERT, 1)
        count = 1
    if count != 1 or text.count(f'data-age-guide="{guide["slug"]}"') != 1:
        raise SystemExit(f"Parent age-guide idempotence failed: {path}")
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
        for key, value in {"loc": url, "lastmod": updated, "changefreq": "monthly", "priority": "0.88"}.items():
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
        if page.count("<h1") != 1 or page.count('class="stage"') != 4 or BANNED.search(page):
            raise SystemExit(f"Rendered age-guide contract failed: {target}")
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
        "stage_count": sum(len(guide["stages"]) for guide in guides),
        "source_count": sum(len(guide["sources"]) for guide in guides),
        "urgent_item_count": sum(len(guide["urgent"]) for guide in guides),
        "parent_links_added": len(guides),
        "sitemap_registered": True,
        "reviewed_at": payload["reviewed_at"],
        "next_review_due": payload["next_review_due"],
        "content_source": CONTENT.relative_to(ROOT).as_posix(),
    }
    (site / "api").mkdir(parents=True, exist_ok=True)
    (site / "api" / "special-needs-condition-age-guides-v314.json").write_text(
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
