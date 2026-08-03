#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "content" / "v209" / "special-needs-guides-manifest-ar.json"
GUIDE_DIR = ROOT / "content" / "v209" / "special-needs-guides"
BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
BRAND = "منصة روافد"
SLOGAN = "للعافية النفسية والدمج والتمكين"
START = "<!-- special-needs-guides-v209:start -->"
END = "<!-- special-needs-guides-v209:end -->"
ALLOWED_HOSTS = {
    "www.unicef.org",
    "social.desa.un.org",
    "www.asha.org",
    "www.who.int",
    "www.w3.org",
}
BANNED = re.compile(r"(?<!\w)(?:المعاقين|معاقين|المعاقون|معاقون|المعاقة|معاقة|المعاق|معاق)(?!\w)")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def words(value: object) -> int:
    return len(re.findall(r"[\w\u0600-\u06FF]+", json.dumps(value, ensure_ascii=False), flags=re.UNICODE))


def load_data() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    guides = []
    for slug in manifest.get("guide_slugs", []):
        path = GUIDE_DIR / f"{slug}.json"
        if not path.is_file():
            raise SystemExit(f"Missing v209 guide file: {path}")
        guide = json.loads(path.read_text(encoding="utf-8"))
        if guide.get("slug") != slug:
            raise SystemExit(f"Guide slug mismatch in {path}: {guide.get('slug')} != {slug}")
        guides.append(guide)
    return {**manifest, "guides": guides}


def validate(data: dict[str, Any]) -> None:
    required = {"version", "batch", "status", "reviewed_at", "title", "description", "guides", "sources"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing batch fields: {sorted(missing)}")
    if data["version"] != 209 or len(data["guides"]) != 5:
        raise SystemExit("v209 must contain exactly five guides")
    if data["status"] != "internally-reviewed":
        raise SystemExit("Batch must retain an honest internally-reviewed status")
    slugs = [guide["slug"] for guide in data["guides"]]
    if len(slugs) != len(set(slugs)):
        raise SystemExit("Guide slugs must be unique")
    for guide in data["guides"]:
        for key in (
            "slug", "title", "description", "category", "audiences", "review_status",
            "external_review", "professional_limits", "when_to_seek_help", "intro",
            "sections", "checklist", "common_mistakes", "template", "source_ids"
        ):
            if key not in guide:
                raise SystemExit(f"Missing {key} in {guide.get('slug')}")
        if guide["review_status"] != "internally-reviewed":
            raise SystemExit(f"Dishonest review state in {guide['slug']}")
        if not 90 <= len(guide["description"]) <= 180:
            raise SystemExit(f"Meta description length invalid in {guide['slug']}: {len(guide['description'])}")
        if words(guide) < 750:
            raise SystemExit(f"Guide is too thin: {guide['slug']} ({words(guide)} words)")
        if len(guide["sections"]) < 5 or any(len(section.get("paragraphs", [])) < 3 for section in guide["sections"]):
            raise SystemExit(f"Guide sections are incomplete: {guide['slug']}")
        if len(guide["checklist"]) < 7 or len(guide["common_mistakes"]) < 5 or len(guide["template"]) < 8:
            raise SystemExit(f"Guide tools are incomplete: {guide['slug']}")
        if len(guide["source_ids"]) < 2:
            raise SystemExit(f"Guide requires at least two sources: {guide['slug']}")
        for source_id in guide["source_ids"]:
            if source_id not in data["sources"]:
                raise SystemExit(f"Unknown source {source_id} in {guide['slug']}")
    serialized = json.dumps(data, ensure_ascii=False)
    if BANNED.search(serialized):
        raise SystemExit("Prohibited person-label language remains in v209 content")
    for source_id, source in data["sources"].items():
        parsed = urlparse(source["url"])
        if parsed.scheme != "https" or parsed.netloc not in ALLOWED_HOSTS:
            raise SystemExit(f"Unapproved source host for {source_id}: {source['url']}")


def schema(guide: dict[str, Any], citations: list[dict[str, Any]]) -> str:
    canonical = f"{BASE}/special-needs/{guide['slug']}/"
    graph = [
        {
            "@type": "Article",
            "headline": guide["title"],
            "description": guide["description"],
            "inLanguage": "ar",
            "url": canonical,
            "dateModified": guide["reviewed_at"],
            "mainEntityOfPage": canonical,
            "publisher": {"@type": "Organization", "name": BRAND, "url": BASE + "/"},
            "articleSection": guide["category"],
            "audience": [{"@type": "Audience", "audienceType": audience} for audience in guide["audiences"]],
            "citation": [source["url"] for source in citations],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة والتربية الدامجة", "item": BASE + "/special-needs/"},
                {"@type": "ListItem", "position": 3, "name": guide["title"], "item": canonical},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def render_guide(guide: dict[str, Any], citations: list[dict[str, Any]]) -> str:
    canonical = f"{BASE}/special-needs/{guide['slug']}/"
    intro = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in guide["intro"])
    sections = "".join(
        f'''<section class="content-section"><h2>{esc(section["heading"])}</h2>
        {''.join(f'<p>{esc(paragraph)}</p>' for paragraph in section["paragraphs"])}</section>'''
        for section in guide["sections"]
    )
    checklist = "".join(f"<li>{esc(item)}</li>" for item in guide["checklist"])
    mistakes = "".join(f"<li>{esc(item)}</li>" for item in guide["common_mistakes"])
    template = "".join(f'<li><span>{esc(item)}</span><span class="write-line" aria-hidden="true"></span></li>' for item in guide["template"])
    sources = "".join(
        f'''<li><a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(source["organization"])} — {esc(source["title"])}</a>
        <p>{esc(source["use"])}</p></li>'''
        for source in citations
    )
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(guide["title"])} | {BRAND}</title>
<meta name="description" content="{esc(guide["description"])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="theme-color" content="#08766e"><meta name="color-scheme" content="light">
<link rel="canonical" href="{canonical}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<meta property="og:type" content="article"><meta property="og:locale" content="ar_AR">
<meta property="og:site_name" content="{BRAND}"><meta property="og:title" content="{esc(guide["title"])}">
<meta property="og:description" content="{esc(guide["description"])}"><meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(guide["title"])}">
<meta name="twitter:description" content="{esc(guide["description"])}">
<script type="application/ld+json">{schema(guide, citations)}</script>
<style>
:root{{--ink:#173f45;--muted:#4f7073;--brand:#08766e;--accent:#93466b;--line:#c5e5e1;--soft:#ebfbf8;--pink:#fff1f6;--lilac:#f2efff;--white:#fff;--shadow:0 15px 42px rgba(28,93,91,.10)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.95;color:var(--ink);background:linear-gradient(145deg,#fff,var(--soft),var(--lilac))}}
a{{color:#076b65}}a:focus-visible{{outline:3px solid #168f88;outline-offset:3px}}.wrap{{width:min(1040px,92%);margin:auto}}
.skip{{position:absolute;right:-9999px}}.skip:focus{{right:10px;top:10px;background:#fff;padding:10px;z-index:30}}
header{{display:flex;justify-content:space-between;gap:15px;align-items:center;padding:16px 0;border-bottom:1px solid var(--line)}}.brand{{font-weight:900;text-decoration:none;color:var(--ink)}}
nav{{display:flex;gap:8px;flex-wrap:wrap}}nav a{{font-weight:800;text-decoration:none;padding:7px 9px;border-radius:10px}}
.hero{{padding:52px 0 24px}}.eyebrow{{color:var(--accent);font-weight:900}}h1{{font-size:clamp(2rem,5.5vw,4rem);line-height:1.25;margin:.2em 0}}h2{{line-height:1.45;color:var(--accent)}}
.lead{{font-size:1.15rem;color:var(--muted)}}.meta{{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}}.tag{{background:#fff;border:1px solid var(--line);padding:7px 10px;border-radius:999px;font-weight:800}}
.notice,.content-section,.tool,.sources{{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:20px;padding:22px;box-shadow:var(--shadow);margin:16px 0}}
.notice{{border-right:6px solid var(--accent);background:var(--pink)}}.content-section:nth-of-type(even){{background:linear-gradient(145deg,#fff,var(--soft))}}
.tools{{display:grid;grid-template-columns:1fr 1fr;gap:15px}}.tool h2{{margin-top:0}}li{{margin:.65rem 0}}.write-line{{display:block;border-bottom:1px dashed #729b9c;height:1.2rem}}
.sources p{{margin:.2rem 0;color:var(--muted)}}footer{{border-top:1px solid var(--line);margin-top:34px;padding:26px 0 45px;color:var(--muted)}}
@media(max-width:760px){{header{{align-items:flex-start;flex-direction:column}}.tools{{grid-template-columns:1fr}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}@media print{{nav,.skip{{display:none!important}}body{{background:#fff}}.notice,.content-section,.tool,.sources{{box-shadow:none;break-inside:avoid}}}}
</style></head><body><a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a><div class="wrap">
<header><a class="brand" href="{BASE_PATH}">{BRAND}<br><small>{SLOGAN}</small></a>
<nav aria-label="التنقل الرئيسي"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}special-needs/">مركز ذوي الاحتياجات الخاصة</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}care-guides/">أدلة التعامل</a></nav></header>
<main id="main"><article><section class="hero"><p class="eyebrow">{esc(guide["category"])}</p><h1>{esc(guide["title"])}</h1>
<p class="lead">{esc(guide["description"])}</p><div class="meta"><span class="tag">مراجعة داخلية</span><span class="tag">آخر تحديث: {esc(guide["reviewed_at"])}</span><span class="tag">{esc(" · ".join(guide["audiences"]))}</span></div>
{intro}<div class="notice"><strong>حدود الاستخدام:</strong> {esc(guide["professional_limits"])}</div></section>
{sections}
<section class="tools" aria-label="أدوات التطبيق"><div class="tool"><h2>قائمة التحقق</h2><ul>{checklist}</ul></div>
<div class="tool"><h2>أخطاء شائعة</h2><ul>{mistakes}</ul></div></section>
<section class="tool"><h2>قالب عمل قابل للطباعة</h2><ol>{template}</ol></section>
<section class="notice"><h2>متى نطلب مساعدة متخصصة؟</h2><p>{esc(guide["when_to_seek_help"])}</p></section>
<section class="sources"><h2>المصادر والمنهج</h2><p>هذه المصادر تدعم الإطار العام ولا تعني أن الجهات المذكورة راجعت المنصة أو اعتمدت المادة.</p><ul>{sources}</ul>
<p><strong>حالة المراجعة:</strong> مراجعة داخلية؛ المراجعة الخارجية المتخصصة موصى بها ولم تُدعَ على أنها مكتملة.</p></section>
</article></main><footer><p><strong>{BRAND}</strong> — {SLOGAN}</p>
<p><a href="{BASE_PATH}special-needs/">العودة إلى المركز</a> · <a href="{BASE_PATH}trust/">الثقة والمنهجية</a> · <a href="{BASE_PATH}partners/">الشركاء والشفافية</a></p></footer></div></body></html>'''


def upsert_urlset(path: Path, urls: list[str], modified: str) -> None:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    if path.is_file():
        tree = ET.parse(path)
        root = tree.getroot()
        if root.tag.rsplit("}", 1)[-1] != "urlset":
            raise SystemExit(f"Expected urlset sitemap: {path}")
    else:
        root = ET.Element(f"{{{ns}}}urlset")
        tree = ET.ElementTree(root)
    existing = {node.text for node in root.findall(f"{{{ns}}}url/{{{ns}}}loc") if node.text}
    for url in urls:
        if url in existing:
            continue
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = modified
        ET.SubElement(node, f"{{{ns}}}changefreq").text = "monthly"
        ET.SubElement(node, f"{{{ns}}}priority").text = "0.82"
    tree.write(path, encoding="utf-8", xml_declaration=True)


def hub_cards(guides: list[dict[str, Any]]) -> str:
    cards = "".join(
        f'''<article class="resource"><h3>{esc(guide["title"])}</h3><p>{esc(guide["description"])}</p>
        <a class="button secondary" href="{BASE_PATH}special-needs/{esc(guide["slug"])}/">فتح الدليل العملي</a></article>'''
        for guide in guides
    )
    return START + cards + END


def link_hub(site: Path, guides: list[dict[str, Any]]) -> None:
    hub = site / "special-needs" / "index.html"
    if not hub.is_file():
        raise SystemExit("Special-needs hub must exist before v209 linking")
    text = hub.read_text(encoding="utf-8")
    payload = hub_cards(guides)
    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), payload, text, flags=re.S)
    else:
        marker = '<div class="resources">'
        if marker not in text:
            raise SystemExit("Special-needs hub resources container is missing")
        text = text.replace(marker, marker + payload, 1)
    hub.write_text(text, encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    data = load_data()
    validate(data)
    generated: list[str] = []
    urls: list[str] = []
    for guide in data["guides"]:
        citations = [data["sources"][source_id] for source_id in guide["source_ids"]]
        target = site / "special-needs" / guide["slug"] / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_guide(guide, citations), encoding="utf-8")
        generated.append(target.relative_to(site).as_posix())
        urls.append(f"{BASE}/special-needs/{guide['slug']}/")
    upsert_urlset(site / "sitemap-special-needs.xml", urls, data["reviewed_at"])
    upsert_urlset(site / "sitemap.xml", urls, data["reviewed_at"])
    link_hub(site, data["guides"])
    report = {
        "version": 209,
        "status": "built-not-published",
        "batch": data["batch"],
        "guide_count": len(data["guides"]),
        "generated_page_count": len(generated),
        "generated_pages": generated,
        "guide_files": [f"content/v209/special-needs-guides/{guide['slug']}.json" for guide in data["guides"]],
        "source_count": len(data["sources"]),
        "review_status": data["status"],
        "external_review": data["external_review"],
        "sitemap_urls": len(urls),
        "hub_linked": True,
        "minimum_source_words": min(words(guide) for guide in data["guides"]),
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "special-needs-guides-v209.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
