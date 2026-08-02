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
BASE = "https://healthrenewal.org"
BASE_PATH = "/"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
SITEMAP_NAME = "sitemap-trust-guides.xml"

EDITORIAL_PATH = ROOT / "content" / "v178" / "editorial-methodology-ar.json"
EVALUATE_PATH = ROOT / "content" / "v181" / "evaluate-mental-health-information-ar.json"
CITATION_PATH = ROOT / "content" / "v191" / "source-citation-guide-ar.json"

ROUTES = {
    "editorial": "editorial-methodology",
    "evaluate": "evaluate-mental-health-information",
    "citation": "guides/source-citation-and-update-transparency",
}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Content source must be an object: {path}")
    return data


def validate_sources(data: dict[str, Any], label: str) -> None:
    sources = data.get("sources", [])
    for source in sources:
        required = {"publisher", "title", "url"}
        missing = required - set(source)
        if missing:
            raise SystemExit(f"{label} source missing fields: {sorted(missing)}")
        if not str(source["url"]).startswith("https://"):
            raise SystemExit(f"{label} source must use HTTPS")


def load_content() -> dict[str, dict[str, Any]]:
    editorial = load_json(EDITORIAL_PATH)
    evaluate = load_json(EVALUATE_PATH)
    citation = load_json(CITATION_PATH)
    for label, data in (("editorial", editorial), ("evaluate", evaluate), ("citation", citation)):
        required = {"title", "description", "reviewed_at", "status", "sections"}
        missing = required - set(data)
        if missing:
            raise SystemExit(f"{label} content missing fields: {sorted(missing)}")
        if data["status"] != "internally-reviewed":
            raise SystemExit(f"{label} must retain an internally-reviewed status")
        if len(data["sections"]) < 6:
            raise SystemExit(f"{label} must contain at least six substantial sections")
        validate_sources(data, label)
    if evaluate.get("risk_level") != "moderate":
        raise SystemExit("Evaluate-information guide must retain its declared moderate risk")
    if citation.get("risk_level") != "low":
        raise SystemExit("Citation guide must retain its declared low risk")
    return {"editorial": editorial, "evaluate": evaluate, "citation": citation}


def internal_href(raw: str) -> str:
    value = str(raw).strip()
    if value.startswith(("https://", "http://", "mailto:", "tel:", "#")):
        return value
    if value == "/guides/evaluate-mental-health-information/":
        value = "/evaluate-mental-health-information/"
    return BASE_PATH + value.lstrip("/")


def site_header() -> str:
    return f'''<header class="site-header"><a class="brand" href="{BASE_PATH}"><span aria-hidden="true">ن</span><span>{BRAND}<small>{SLOGAN}</small></span></a><nav aria-label="التنقل الرئيسي"><a href="{BASE_PATH}start-here/">ابدأ من هنا</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}care-guides/">أدلة التعامل</a><a href="{BASE_PATH}magazine/">المجلة</a><a href="{BASE_PATH}trust/">الثقة والمنهجية</a></nav></header>'''


def site_footer() -> str:
    return f'''<footer class="site-footer"><p><strong>{BRAND}</strong> — {SLOGAN}</p><p>المحتوى للتثقيف والدعم العام، ولا يستبدل التقييم أو الرعاية المهنية الفردية.</p><p><a href="{BASE_PATH}partners/">الشركاء والشفافية</a> · <a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}">الرئيسية</a></p></footer>'''


def render_sections(data: dict[str, Any]) -> str:
    return "".join(
        f'<section class="card"><h2>{esc(section["heading"])}</h2>'
        + "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
        + "</section>"
        for section in data["sections"]
    )


def render_links(items: list[dict[str, Any]], label_key: str = "title") -> str:
    return "".join(
        f'<li><a href="{esc(internal_href(item["href"]))}">{esc(item[label_key])}</a></li>'
        for item in items
    )


def render_sources(data: dict[str, Any]) -> str:
    sources = data.get("sources", [])
    if not sources:
        return ""
    rows = []
    for source in sources:
        year = f' ({esc(source["year"])})' if source.get("year") else ""
        claims = source.get("claims_supported", [])
        claim_html = ""
        if claims:
            claim_html = "<ul>" + "".join(f"<li>{esc(claim)}</li>" for claim in claims) + "</ul>"
        rows.append(
            f'<li><a rel="noopener noreferrer" href="{esc(source["url"])}">{esc(source["publisher"])} — {esc(source["title"])}</a>{year}{claim_html}</li>'
        )
    return '<section class="card sources"><h2>المصادر وما تدعمه</h2><ul>' + "".join(rows) + "</ul></section>"


def page_schema(data: dict[str, Any], canonical: str) -> str:
    article: dict[str, Any] = {
        "@type": "Article",
        "@id": canonical + "#article",
        "headline": data["title"],
        "description": data["description"],
        "inLanguage": "ar",
        "dateModified": data["reviewed_at"],
        "mainEntityOfPage": canonical,
        "author": {"@type": "Organization", "name": BRAND, "url": BASE + "/"},
        "publisher": {"@type": "Organization", "name": BRAND, "url": BASE + "/"},
    }
    if data.get("sources"):
        article["citation"] = [source["url"] for source in data["sources"]]
    breadcrumb = {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": data["title"], "item": canonical},
        ],
    }
    return json.dumps({"@context": "https://schema.org", "@graph": [article, breadcrumb]}, ensure_ascii=False).replace("</", "<\\/")


def render_page(data: dict[str, Any], route: str, body: str, eyebrow: str, limits: str) -> str:
    canonical = f"{BASE}/{route}/"
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(data["title"])} | {BRAND}</title><meta name="description" content="{esc(data["description"])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><meta name="color-scheme" content="light"><meta name="theme-color" content="#08736d"><link rel="canonical" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{esc(data["title"])}"><meta property="og:description" content="{esc(data["description"])}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(data["title"])}"><meta name="twitter:description" content="{esc(data["description"])}"><script type="application/ld+json">{page_schema(data, canonical)}</script>
<style>:root{{--ink:#173f45;--muted:#4f7074;--line:#c8e7e3;--soft:#f3fbfa;--pink:#fff1f7;--lilac:#f2efff;--brand:#08736d;--gold:#805600}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:var(--ink);background:linear-gradient(145deg,#fff,var(--soft),var(--lilac))}}a{{color:#086e69}}a:focus-visible,input:focus-visible{{outline:3px solid #168f88;outline-offset:3px}}.skip{{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px;z-index:50}}.skip:focus{{right:8px}}.site-header,.site-footer{{padding:16px max(4vw,18px);background:rgba(255,255,255,.96);border-color:var(--line)}}.site-header{{display:flex;justify-content:space-between;gap:14px;align-items:center;border-bottom:1px solid var(--line)}}.brand{{display:flex;gap:10px;align-items:center;text-decoration:none;color:var(--ink);font-weight:900}}.brand>span:first-child{{display:grid;place-items:center;width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#dffaf7,#eee9ff);border:1px solid #a9dcd6}}.brand>span:last-child{{display:grid;line-height:1.35}}.brand small{{color:var(--muted)}}nav{{display:flex;gap:8px;flex-wrap:wrap}}nav a{{font-weight:800;text-decoration:none;padding:6px 8px;border-radius:9px}}main{{width:min(1020px,92%);margin:auto;padding:38px 0 64px}}.hero,.card,.notice{{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:18px;padding:22px;margin:16px 0}}.hero{{background:linear-gradient(145deg,#fff,var(--pink))}}.eyebrow{{color:#99466e;font-weight:900}}h1{{font-size:clamp(2rem,5vw,3.7rem);line-height:1.25;margin:.2em 0}}h2{{line-height:1.4}}.lead{{font-size:1.13rem;color:var(--muted)}}.notice{{border-inline-start:6px solid var(--gold)}}.danger{{border-inline-start-color:#9d2d2d;background:#fff4f4}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid var(--line);padding:12px;text-align:start;vertical-align:top}}.checklist li{{margin:.55rem 0}}.site-footer{{border-top:1px solid var(--line)}}@media(max-width:760px){{.site-header{{align-items:flex-start;flex-direction:column}}table,thead,tbody,tr,th,td{{display:block}}thead{{position:absolute;left:-9999px}}td{{border-top:0}}}}@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}@media print{{nav,.skip,.checklist input{{display:none!important}}body{{background:#fff}}main{{width:100%;padding:0}}.hero,.card,.notice{{break-inside:avoid;border-color:#777}}}}</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a>{site_header()}<main id="main"><article><header class="hero"><p class="eyebrow">{esc(eyebrow)}</p><h1>{esc(data["title"])}</h1><p class="lead">{esc(data.get("summary") or data["description"])}</p></header><aside class="notice"><h2>حالة الصفحة وحدودها</h2><p>{esc(limits)}</p><p><strong>المراجعة:</strong> داخلية بتاريخ <time datetime="{esc(data["reviewed_at"])}">{esc(data["reviewed_at"])}</time>. لا توجد دعوى مراجعة اختصاصية خارجية أو اعتماد رسمي.</p></aside>{body}</article></main>{site_footer()}</body></html>'''


def editorial_body(data: dict[str, Any]) -> str:
    links = render_links(data.get("related_links", []))
    return render_sections(data) + f'<section class="card"><h2>مسارات مرتبطة</h2><ul>{links}</ul></section>'


def evaluate_body(data: dict[str, Any]) -> str:
    checklist = "".join(f"<li>{esc(item)}</li>" for item in data["decision_checklist"])
    flags = "".join(f"<li>{esc(item)}</li>" for item in data["red_flags"])
    links = render_links(data.get("related_links", []))
    return (
        render_sections(data)
        + f'<section class="card checklist"><h2>قائمة قرار قبل الثقة أو المشاركة</h2><ol>{checklist}</ol></section>'
        + f'<aside class="notice danger"><h2>إشارات تستدعي التوقف والتحقق</h2><ul>{flags}</ul></aside>'
        + render_sources(data)
        + f'<section class="card"><h2>مسارات مرتبطة</h2><ul>{links}</ul></section>'
    )


def citation_body(data: dict[str, Any]) -> str:
    checklist = "".join(
        f'<li><input id="citation-check-{index}" type="checkbox" aria-label="بند التحقق رقم {index}"><label for="citation-check-{index}">{esc(item)}</label></li>'
        for index, item in enumerate(data["checklist"], start=1)
    )
    examples = "".join(
        f'<tr><td>{esc(item["avoid"])}</td><td>{esc(item["prefer"])}</td></tr>'
        for item in data["examples"]
    )
    links = render_links(data.get("internal_links", []), label_key="label")
    return (
        render_sections(data)
        + f'<section class="card checklist"><h2>قائمة تحقق قبل النشر</h2><ol>{checklist}</ol></section>'
        + f'<section class="card"><h2>أمثلة تحريرية قبل وبعد</h2><table><thead><tr><th>صياغة تحتاج مراجعة</th><th>بديل أدق</th></tr></thead><tbody>{examples}</tbody></table></section>'
        + f'<section class="card"><h2>مسارات مرتبطة</h2><ul>{links}</ul></section>'
        + render_sources(data)
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def write_sitemaps(site: Path, pages: list[dict[str, str]]) -> dict[str, object]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    child = site / SITEMAP_NAME
    root = ET.Element(f"{{{ns}}}urlset")
    for page in pages:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = page["url"]
        ET.SubElement(node, f"{{{ns}}}lastmod").text = page["reviewed_at"]
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "monthly"
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)

    main_path = site / "sitemap.xml"
    if not main_path.is_file():
        raise SystemExit("Main sitemap is missing")
    tree = ET.parse(main_path)
    main = tree.getroot()
    mode = local_name(main.tag)
    changed = False
    if mode == "urlset":
        existing = {(node.text or "").strip() for node in main.findall("{*}url/{*}loc")}
        for page in pages:
            if page["url"] in existing:
                continue
            node = ET.SubElement(main, qualify(main, "url"))
            ET.SubElement(node, qualify(main, "loc")).text = page["url"]
            existing.add(page["url"])
            changed = True
    elif mode == "sitemapindex":
        child_url = BASE + "/" + SITEMAP_NAME
        existing = {(node.text or "").strip() for node in main.findall("{*}sitemap/{*}loc")}
        if child_url not in existing:
            node = ET.SubElement(main, qualify(main, "sitemap"))
            ET.SubElement(node, qualify(main, "loc")).text = child_url
            changed = True
    else:
        raise SystemExit(f"Unsupported main sitemap root: {mode}")
    if changed:
        tree.write(main_path, encoding="utf-8", xml_declaration=True)
    return {"name": SITEMAP_NAME, "url_count": len(pages), "main_mode": mode, "main_changed": changed}


def add_discovery_links(site: Path, pages: list[dict[str, str]]) -> dict[str, bool]:
    block = '<section class="trust-guides-v201"><h2>أدلة الشفافية والتحقق</h2><ul>' + "".join(
        f'<li><a href="{BASE_PATH}{page["route"]}/">{esc(page["title"])}</a></li>' for page in pages
    ) + "</ul></section>"
    changed: dict[str, bool] = {}
    for relative in ("trust/index.html", "magazine/index.html"):
        path = site / relative
        if not path.is_file():
            changed[relative] = False
            continue
        text = path.read_text(encoding="utf-8")
        if "trust-guides-v201" in text:
            changed[relative] = False
            continue
        if "</main>" not in text:
            raise SystemExit(f"Discovery target has no main element: {relative}")
        path.write_text(text.replace("</main>", block + "</main>", 1), encoding="utf-8")
        changed[relative] = True
    return changed


def publish(site: Path) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    content = load_content()
    definitions = [
        {
            "key": "editorial",
            "route": ROUTES["editorial"],
            "eyebrow": "الشفافية والتحرير",
            "limits": "هذه الصفحة تشرح دورة العمل التحريرية والتقنية، ولا تعني أن كل مادة راجعها اختصاصي خارجي.",
            "body": editorial_body(content["editorial"]),
        },
        {
            "key": "evaluate",
            "route": ROUTES["evaluate"],
            "eyebrow": "دليل التحقق الرقمي",
            "limits": "هذا الدليل يساعد على تقييم جودة المعلومات، ولا يشخّص حالة ولا يستبدل تقييمًا مهنيًا. لا تبدأ دواءً أو توقفه أو تغيّر جرعته اعتمادًا على محتوى الإنترنت.",
            "body": evaluate_body(content["evaluate"]),
        },
        {
            "key": "citation",
            "route": ROUTES["citation"],
            "eyebrow": "الاستشهاد والتحديث",
            "limits": content["citation"]["professional_limits"],
            "body": citation_body(content["citation"]),
        },
    ]
    pages: list[dict[str, str]] = []
    for definition in definitions:
        data = content[definition["key"]]
        route = definition["route"]
        target = site / route / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            render_page(data, route, definition["body"], definition["eyebrow"], definition["limits"]),
            encoding="utf-8",
        )
        pages.append({
            "key": definition["key"],
            "route": route,
            "path": route + "/index.html",
            "url": f"{BASE}/{route}/",
            "title": str(data["title"]),
            "reviewed_at": str(data["reviewed_at"]),
            "status": str(data["status"]),
            "risk_level": str(data.get("risk_level", "not-declared")),
        })
    sitemap = write_sitemaps(site, pages)
    discovery = add_discovery_links(site, pages)
    report = {
        "version": 201,
        "status": "built-not-published",
        "page_count": len(pages),
        "pages": pages,
        "sitemap": sitemap,
        "discovery_links": discovery,
        "external_specialist_review_claimed": False,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "trust-guides-v201.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    publish(target)
