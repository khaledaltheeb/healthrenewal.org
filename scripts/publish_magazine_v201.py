#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v192" / "platform-institutional-foundation-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
URL = BASE + "/magazine/"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def load_data() -> dict:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    if data.get("status") != "internally-reviewed" or data.get("risk_level") != "low":
        raise SystemExit("Magazine methodology must remain internally reviewed and low risk")
    magazine = data.get("magazine") or {}
    required = {"title", "description", "summary", "sections", "publication_checklist"}
    missing = required - set(magazine)
    if missing:
        raise SystemExit(f"Missing magazine fields: {sorted(missing)}")
    return data


def render(data: dict) -> str:
    magazine = data["magazine"]
    sections = "".join(
        f'<section><h2>{esc(section["heading"])}</h2>'
        + "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
        + "</section>"
        for section in magazine["sections"]
    )
    checklist = "".join(f"<li>{esc(item)}</li>" for item in magazine["publication_checklist"])
    sources = "".join(
        f'<li><a rel="noopener" href="{esc(source["url"])}">{esc(source["title"])}</a> — '
        f'{esc(source["publisher"])} ({esc(source["year"])})</li>'
        for source in data.get("sources", [])
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": magazine["title"],
        "description": magazine["description"],
        "url": URL,
        "inLanguage": "ar",
        "dateModified": data["reviewed_at"],
        "isPartOf": {
            "@type": "WebSite",
            "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
            "url": BASE + "/",
        },
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(magazine["title"])} | منصة الصحة النفسية وذوي الاحتياجات الخاصة</title>
<meta name="description" content="{esc(magazine["description"])}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{URL}"><meta name="color-scheme" content="light">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(magazine["title"])}"><meta property="og:description" content="{esc(magazine["description"])}"><meta property="og:url" content="{URL}">
<meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>:root{{--ink:#173f45;--muted:#4f7074;--line:#c7e7e3;--soft:#f4fbfa;--brand:#08736d}}*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;color:var(--ink);line-height:1.9;background:#fff}}a{{color:#086e69}}header,footer{{padding:18px max(4vw,20px);background:var(--soft);border-color:var(--line)}}header{{border-bottom:1px solid var(--line)}}footer{{border-top:1px solid var(--line);margin-top:40px}}nav{{display:flex;gap:12px;flex-wrap:wrap}}main{{max-width:1000px;margin:auto;padding:34px max(4vw,20px)}}h1,h2{{line-height:1.35}}.lead{{font-size:1.13rem;color:var(--muted)}}section{{border:1px solid var(--line);border-radius:16px;padding:20px;margin:18px 0}}.status{{background:#fff8e6;border-color:#ead7a2}}li{{margin:.5rem 0}}a:focus-visible{{outline:3px solid #805600;outline-offset:4px}}@media print{{header nav{{display:none}}section{{break-inside:avoid}}}}</style>
</head><body>
<header><strong>منصة الصحة النفسية وذوي الاحتياجات الخاصة</strong><nav aria-label="التنقل الرئيسي"><a href="/pterminology-site/">الرئيسية</a><a href="/pterminology-site/encyclopedia/">الموسوعة</a><a href="/pterminology-site/care-guides/">أدلة التعامل</a><a href="/pterminology-site/trust/">الثقة والمنهجية</a></nav></header>
<main><h1>{esc(magazine["title"])}</h1><p class="lead">{esc(magazine["summary"])}</p>
<section class="status"><h2>حالة النشر الحالية</h2><p><strong>هذه الصفحة تنشر المنهج والعقد التحريري.</strong> تُضاف الملخصات البحثية الفعلية في طبقة النشر v232 بعد نجاح فحص المصدر الأولي والحقوق والدقة والسلامة والروابط.</p></section>
{sections}
<section><h2>قائمة فحص كل مادة علمية</h2><ol>{checklist}</ol></section>
<section><h2>المصادر المؤسسة للمنهج</h2><ul>{sources}</ul></section>
<section><h2>حالة المراجعة</h2><p>مراجعة داخلية منخفضة المخاطر. آخر تحقق موثق: {esc(data["reviewed_at"])}. لا تدعي الصفحة مراجعة اختصاصية خارجية أو اعتمادًا مؤسسيًا لم يحدث.</p></section>
</main><footer><p><strong>معرفة تحترم الإنسان. دعم يوسّع الإمكانات.</strong></p><p><a href="/pterminology-site/partners/">الشركاء والشفافية</a> · <a href="/pterminology-site/trust/">الثقة والمنهجية</a></p></footer>
</body></html>'''


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def write_sitemaps(site: Path, reviewed_at: str) -> dict[str, object]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    child = site / "sitemap-magazine.xml"
    root = ET.Element(f"{{{ns}}}urlset")
    node = ET.SubElement(root, f"{{{ns}}}url")
    ET.SubElement(node, f"{{{ns}}}loc").text = URL
    ET.SubElement(node, f"{{{ns}}}lastmod").text = reviewed_at
    ET.SubElement(node, f"{{{ns}}}changefreq").text = "weekly"
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)

    main_path = site / "sitemap.xml"
    if not main_path.is_file():
        raise SystemExit("Main sitemap is missing")
    tree = ET.parse(main_path)
    main = tree.getroot()
    mode = local_name(main.tag)
    changed = False
    if mode == "urlset":
        existing = {(item.text or "").strip() for item in main.findall("{*}url/{*}loc")}
        if URL not in existing:
            item = ET.SubElement(main, qualify(main, "url"))
            ET.SubElement(item, qualify(main, "loc")).text = URL
            changed = True
    elif mode == "sitemapindex":
        child_url = BASE + "/sitemap-magazine.xml"
        existing = {(item.text or "").strip() for item in main.findall("{*}sitemap/{*}loc")}
        if child_url not in existing:
            item = ET.SubElement(main, qualify(main, "sitemap"))
            ET.SubElement(item, qualify(main, "loc")).text = child_url
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {mode}")
    if changed:
        tree.write(main_path, encoding="utf-8", xml_declaration=True)
    return {"main_mode": mode, "main_changed": changed, "child_urls": 1}


def publish(site: Path) -> dict[str, object]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    data = load_data()
    target = site / "magazine" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data), encoding="utf-8")
    sitemap = write_sitemaps(site, data["reviewed_at"])
    report = {
        "version": 201,
        "page": "magazine/index.html",
        "url": URL,
        "methodology_published": True,
        "research_summaries_published": 0,
        "review_status": data["status"],
        "risk_level": data["risk_level"],
        "sitemap": sitemap,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "magazine-v201.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def publish_complete_magazine(site: Path) -> dict[str, object]:
    publish(site)
    from publish_research_magazine_v232 import publish as publish_research
    return publish_research(site)


if __name__ == "__main__":
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    publish_complete_magazine(output)
