#!/usr/bin/env python3
"""Publish reference assets for the outside-the-box section.

This publisher preserves the v301 evidence standard in generated production output,
publishes its machine-readable contract, and renders the v254 instrument registry as
an accessible institutional page without reproducing protected test content.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENTS_PATH = ROOT / "content" / "v254" / "outside-the-box-instruments-ar.json"
CONDITIONS_PATH = ROOT / "content" / "v254" / "outside-the-box-conditions-ar.json"
EVIDENCE_PAGE = ROOT / "outside-the-box" / "evidence-standard" / "index.html"
EVIDENCE_API = ROOT / "api" / "outside-the-box-evidence-standard-v301.json"

BASE = "https://healthrenewal.org/"
BASE_PATH = "/"
UPDATED = "2026-07-27"
VERSION = 303


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def load_data() -> tuple[dict[str, Any], dict[str, Any]]:
    instruments = json.loads(INSTRUMENTS_PATH.read_text(encoding="utf-8"))
    conditions = json.loads(CONDITIONS_PATH.read_text(encoding="utf-8"))
    if instruments.get("version") != 254:
        raise ValueError("Instrument registry source version must be 254")
    if not instruments.get("clusters") or not instruments.get("universal"):
        raise ValueError("Instrument registry is empty")
    if set(instruments["clusters"]) != set(conditions["clusters"]):
        raise ValueError("Instrument and condition clusters are not aligned")
    for group, tools in instruments["clusters"].items():
        if len(tools) < 4:
            raise ValueError(f"Instrument group {group} has fewer than four tools")
        for tool in tools:
            expected = {"name", "owner", "use", "access", "caution"}
            if set(tool) != expected or not all(str(tool[key]).strip() for key in expected):
                raise ValueError(f"Malformed instrument in group {group}")
    return instruments, conditions


def render_tool(tool: dict[str, Any], index: int) -> str:
    return f"""<article class="ir-tool">
<div class="ir-tool-head"><span>{index}</span><h3>{e(tool['name'])}</h3></div>
<dl>
<div><dt>المالك أو الجهة</dt><dd>{e(tool['owner'])}</dd></div>
<div><dt>الاستخدام المقصود</dt><dd>{e(tool['use'])}</dd></div>
<div><dt>الوصول والترخيص</dt><dd>{e(tool['access'])}</dd></div>
<div><dt>حدود التفسير</dt><dd>{e(tool['caution'])}</dd></div>
</dl></article>"""


def render_instruments_page(instruments: dict[str, Any], conditions: dict[str, Any]) -> str:
    cluster_titles = {
        key: value["title"] for key, value in conditions["clusters"].items()
    }
    universal = "".join(
        render_tool(tool, index)
        for index, tool in enumerate(instruments["universal"], start=1)
    )
    sections = []
    item_list = []
    position = 0
    for cluster_key, tools in instruments["clusters"].items():
        cards = []
        for local_index, tool in enumerate(tools, start=1):
            position += 1
            cards.append(render_tool(tool, local_index))
            item_list.append(
                {
                    "@type": "ListItem",
                    "position": position,
                    "name": tool["name"],
                }
            )
        sections.append(
            f"""<section class="ir-section" id="{e(cluster_key)}"><div class="ir-wrap">
<p class="ir-kicker">عائلة وظيفية</p><h2>{e(cluster_titles[cluster_key])}</h2>
<p class="ir-intro">تُختار الأداة وفق سؤال الإحالة والعمر واللغة والغرض والمؤهل والترخيص، وتُدمج مع التاريخ والملاحظة والأداء الوظيفي.</p>
<div class="ir-grid">{''.join(cards)}</div></div></section>"""
        )
    total_cluster_tools = sum(len(tools) for tools in instruments["clusters"].values())
    total_tools = len(instruments["universal"]) + total_cluster_tools
    nav = "".join(
        f'<a href="#{e(key)}">{e(cluster_titles[key])}</a>'
        for key in instruments["clusters"]
    )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "headline": instruments["title"],
        "inLanguage": "ar",
        "dateModified": UPDATED,
        "url": BASE + "outside-the-box/instruments/",
        "about": [
            "القياس النفسي والتربوي",
            "التقييم الوظيفي",
            "حقوق الاختبارات",
            "التكييف اللغوي والثقافي",
        ],
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": total_cluster_tools,
            "itemListElement": item_list,
        },
    }
    return f"""<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>سجل أدوات التقييم المؤسسي | مسارات 100 حالة</title>
<meta name="description" content="سجل مؤسسي عربي لأسماء أدوات التقييم وأغراضها وترخيصها وحدود تفسيرها عبر عائلات حالات ذوي الاحتياجات الخاصة، دون نشر بنود محمية.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{BASE}outside-the-box/instruments/">
<script type="application/ld+json">{compact_json(schema)}</script>
<style>
:root{{--ink:#143f43;--muted:#536f73;--brand:#08766f;--plum:#7b3156;--line:#b9ddd7;--mint:#ebfaf7;--pink:#fff1f6;--amber:#fff7d8;--shadow:0 15px 38px rgba(16,78,76,.10)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.8;background:linear-gradient(145deg,#fff,#f4fffc 52%,#faf7ff)}}a{{color:#056a63}}a:focus-visible{{outline:3px solid #0b8f87;outline-offset:3px}}.ir-wrap{{width:min(1220px,92%);margin:auto}}.ir-skip{{position:absolute;right:-9999px;top:8px;background:#fff;border:2px solid var(--brand);border-radius:12px;padding:10px 14px;z-index:99}}.ir-skip:focus{{right:8px}}
header{{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}.ir-head{{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:11px 0}}.ir-brand{{font-weight:900;text-decoration:none;color:var(--ink)}}.ir-nav{{display:flex;gap:7px;flex-wrap:wrap}}.ir-nav a{{padding:7px 9px;border-radius:10px;text-decoration:none;font-weight:800}}.ir-nav a:hover,.ir-nav a[aria-current="page"]{{background:var(--mint)}}
.ir-hero{{padding:56px 0 34px;border-bottom:1px solid var(--line);background:radial-gradient(circle at 86% 18%,rgba(92,207,196,.22),transparent 31%),radial-gradient(circle at 12% 82%,rgba(164,113,199,.14),transparent 30%)}}h1{{font-size:clamp(2.15rem,6vw,4.6rem);line-height:1.13;margin:.12em 0}}.ir-kicker{{margin:0;color:var(--plum);font-weight:900}}.ir-lead,.ir-intro,.ir-tool dd{{color:var(--muted)}}.ir-lead{{max-width:920px;font-size:1.15rem}}.ir-notice{{margin:20px 0;border:1px solid var(--line);border-right:5px solid var(--plum);border-radius:15px;background:var(--pink);padding:15px 18px}}.ir-warning{{border-right-color:#a06a00;background:var(--amber)}}
.ir-metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:24px}}.ir-metrics div{{border:1px solid var(--line);border-radius:17px;background:#fff;padding:14px;box-shadow:var(--shadow)}}.ir-metrics strong{{display:block;color:var(--plum);font-size:1.7rem}}.ir-index{{padding:25px 0;background:#fff;border-bottom:1px solid var(--line)}}.ir-index nav{{display:flex;gap:8px;flex-wrap:wrap}}.ir-index a{{border:1px solid var(--line);border-radius:999px;background:var(--mint);padding:6px 10px;text-decoration:none;font-weight:800}}
.ir-section{{padding:38px 0}}.ir-section:nth-of-type(even){{background:rgba(235,250,247,.55)}}.ir-section h2{{font-size:clamp(1.65rem,4vw,2.55rem);margin:.15em 0}}.ir-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.ir-tool{{border:1px solid var(--line);border-radius:20px;background:#fff;padding:19px;box-shadow:var(--shadow)}}.ir-tool-head{{display:flex;align-items:flex-start;gap:10px}}.ir-tool-head span{{width:34px;height:34px;flex:0 0 auto;display:grid;place-items:center;border-radius:50%;border:1px solid var(--line);background:var(--mint);color:var(--brand);font-weight:900}}.ir-tool h3{{margin:.15em 0;color:var(--plum)}}dl{{margin:12px 0 0}}dl div{{display:grid;grid-template-columns:minmax(125px,.35fr) 1fr;gap:10px;border-top:1px solid var(--line);padding:9px 0}}dt{{font-weight:900}}dd{{margin:0}}footer{{border-top:1px solid var(--line);padding:30px 0 46px;background:rgba(255,255,255,.75)}}
@media(max-width:850px){{.ir-head{{align-items:flex-start;flex-direction:column}}.ir-grid{{grid-template-columns:1fr}}.ir-metrics{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:560px){{.ir-nav{{overflow:auto;flex-wrap:nowrap;max-width:100%}}.ir-nav a{{white-space:nowrap}}.ir-metrics{{grid-template-columns:1fr}}dl div{{grid-template-columns:1fr;gap:2px}}}}
</style></head><body>
<a class="ir-skip" href="#main">تجاوز إلى المحتوى</a>
<header><div class="ir-wrap ir-head"><a class="ir-brand" href="{BASE_PATH}">منصة الصحة النفسية وذوي الاحتياجات الخاصة</a><nav class="ir-nav" aria-label="التنقل"><a href="../">المسارات المئة</a><a href="../methodology/">المنهجية</a><a aria-current="page" href="./">سجل الأدوات</a><a href="../evidence-standard/">معيار الأدلة</a><a href="../ten-plan-methodology/">الخطط العشر</a></nav></div></header>
<main id="main"><section class="ir-hero"><div class="ir-wrap"><p class="ir-kicker">سجل مرجعي لحقوق الأدوات وحدود تفسيرها</p><h1>{e(instruments['title'])}</h1><p class="ir-lead">يعرض السجل الأسماء والأغراض والقيود المهنية فقط، ويربط اختيار الأداة بسؤال واضح وتقييم متعدد المصادر وأداء الشخص في حياته الفعلية.</p>
<div class="ir-notice"><strong>حالة المراجعة:</strong> {e(instruments['review_status'])}.</div><div class="ir-notice ir-warning"><strong>حقوق الأدوات:</strong> {e(instruments['rights_notice'])}</div>
<div class="ir-metrics"><div><strong>{total_tools}</strong><span>إجراء وأداة مسجلة</span></div><div><strong>{len(instruments['clusters'])}</strong><span>عائلة وظيفية</span></div><div><strong>{len(instruments['universal'])}</strong><span>إجراءات مشتركة</span></div><div><strong>0</strong><span>بنود أو مفاتيح تصحيح منشورة</span></div></div></div></section>
<section class="ir-index"><div class="ir-wrap"><p class="ir-kicker">انتقال سريع</p><nav aria-label="عائلات سجل الأدوات">{nav}</nav></div></section>
<section class="ir-section"><div class="ir-wrap"><p class="ir-kicker">إجراءات مشتركة غير حاسمة تشخيصيًا</p><h2>خط البداية قبل اختيار مقياس متخصص</h2><div class="ir-grid">{universal}</div></div></section>
{''.join(sections)}</main><footer><div class="ir-wrap"><p>لا تُستنتج حالة أو أهلية أو خطة علاج من اسم أداة أو درجة منفردة. يلزم مستخدم مؤهل، ونسخة مرخصة، وتحقق لغوي وثقافي، وتكامل مع التاريخ والملاحظة والأداء الوظيفي.</p></div></footer></body></html>"""


def register_url(sitemap_path: Path, url_value: str, priority: str) -> None:
    if not sitemap_path.is_file():
        raise ValueError("Missing outside-the-box sitemap")
    tree = ET.parse(sitemap_path)
    root = tree.getroot()
    existing = {
        (node.text or "").strip()
        for node in root.findall("{*}url/{*}loc")
        if node.text
    }
    if url_value not in existing:
        node = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = url_value
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod").text = UPDATED
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}changefreq").text = "monthly"
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}priority").text = priority
    tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)


def validate(site: Path, instruments: dict[str, Any], report: dict[str, Any]) -> None:
    evidence_page = site / "outside-the-box/evidence-standard/index.html"
    evidence_api = site / "api/outside-the-box-evidence-standard-v301.json"
    registry_page = site / "outside-the-box/instruments/index.html"
    registry_api = site / "api/outside-the-box-reference-assets-v303.json"
    for path in (evidence_page, evidence_api, registry_page, registry_api):
        if not path.is_file() or path.stat().st_size < 100:
            raise ValueError(f"Missing reference asset: {path}")
    page = registry_page.read_text(encoding="utf-8")
    for marker in (
        instruments["title"],
        instruments["rights_notice"],
        instruments["review_status"],
        "المالك أو الجهة",
        "الاستخدام المقصود",
        "الوصول والترخيص",
        "حدود التفسير",
        "0</strong><span>بنود أو مفاتيح تصحيح منشورة",
    ):
        if marker not in page:
            raise ValueError(f"Instrument registry page is missing marker: {marker}")
    for tool in instruments["universal"]:
        if tool["name"] not in page:
            raise ValueError(f"Universal instrument is missing: {tool['name']}")
    for tools in instruments["clusters"].values():
        for tool in tools:
            if tool["name"] not in page:
                raise ValueError(f"Cluster instrument is missing: {tool['name']}")
    sitemap_urls = {
        (node.text or "").strip()
        for node in ET.parse(site / "sitemap-outside-the-box.xml")
        .getroot()
        .findall("{*}url/{*}loc")
        if node.text
    }
    expected = {
        BASE + "outside-the-box/evidence-standard/",
        BASE + "outside-the-box/instruments/",
    }
    if not expected.issubset(sitemap_urls):
        raise ValueError("Reference pages are absent from outside-the-box sitemap")
    if report["protected_test_items_published"]:
        raise ValueError("Reference publisher must never publish protected test items")


def publish(site: Path) -> dict[str, Any]:
    site = site.resolve()
    if not site.is_dir():
        raise ValueError(f"Missing site output: {site}")
    instruments, conditions = load_data()
    if not EVIDENCE_PAGE.is_file() or not EVIDENCE_API.is_file():
        raise ValueError("Evidence standard source assets are missing")

    evidence_target = site / "outside-the-box/evidence-standard"
    evidence_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EVIDENCE_PAGE, evidence_target / "index.html")

    api_target = site / "api"
    api_target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(EVIDENCE_API, api_target / EVIDENCE_API.name)

    registry_target = site / "outside-the-box/instruments"
    registry_target.mkdir(parents=True, exist_ok=True)
    registry_target.joinpath("index.html").write_text(
        render_instruments_page(instruments, conditions), encoding="utf-8"
    )

    sitemap = site / "sitemap-outside-the-box.xml"
    register_url(sitemap, BASE + "outside-the-box/evidence-standard/", "0.9")
    register_url(sitemap, BASE + "outside-the-box/instruments/", "0.8")

    total_tools = len(instruments["universal"]) + sum(
        len(tools) for tools in instruments["clusters"].values()
    )
    report = {
        "version": VERSION,
        "reviewed_at": UPDATED,
        "status": "passed",
        "evidence_standard_version": 301,
        "instrument_registry_source_version": instruments["version"],
        "instrument_count": total_tools,
        "cluster_count": len(instruments["clusters"]),
        "protected_test_items_published": False,
        "scoring_keys_published": False,
        "normative_tables_published": False,
        "external_clinical_review_completed": False,
        "urls": {
            "evidence_standard": BASE + "outside-the-box/evidence-standard/",
            "instrument_registry": BASE + "outside-the-box/instruments/",
            "evidence_api": BASE + "api/outside-the-box-evidence-standard-v301.json",
        },
    }
    api_target.joinpath("outside-the-box-reference-assets-v303.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    validate(site, instruments, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    report = publish(args.site)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
