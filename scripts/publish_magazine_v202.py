#!/usr/bin/env python3
"""Publish the Rawafid magazine from the real recursive study tree.

v202 is intentionally non-destructive:
- copies the complete magazine source tree to the build output;
- never deletes or hides an existing published study;
- discovers study pages recursively through the v202 source audit;
- preserves each page's canonical URL and nested route;
- generates the main magazine index, RSS and sitemap from the same records;
- reports incomplete/unverified pages instead of silently dropping them.

Bibliographic verification is optional at build time. When a verification JSON
from `verify_magazine_bibliography_v202.py` is supplied, its authoritative
status is exposed in the index/API. Without it, identifiers are explicitly
shown as pending verification rather than being called verified.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "magazine"
AUDIT_SCRIPT = ROOT / "scripts" / "audit_magazine_sources_v202.py"
BASE = "https://healthrenewal.org"
URL = BASE + "/magazine/"
API_NAME = "magazine-v202.json"
FEED_LIMIT = 20
TARGET_ARTICLES = 500
CONTRACT = 202
ROBOTS_PATTERN = re.compile(r'<meta\s+[^>]*name=["\']robots["\'][^>]*>', re.I)
DATE_JSONLD_RE = re.compile(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', re.I)
DATE_META_RE = re.compile(
    r'<meta\s+(?=[^>]*(?:property|name)=["\'](?:article:published_time|datePublished|date)["\'])[^>]*content=["\']([^"\']+)["\'][^>]*>',
    re.I,
)
DESCRIPTION_RE = re.compile(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', re.I | re.S)
LEAD_RE = re.compile(r'<p\s+class=["\'](?:lead|lede|summary)["\'][^>]*>(.*?)</p>', re.I | re.S)
P_RE = re.compile(r'<p(?:\s[^>]*)?>(.*?)</p>', re.I | re.S)
H1_RE = re.compile(r'<h1\b[^>]*>(.*?)</h1>', re.I | re.S)
CANONICAL_RE = re.compile(
    r'<link\b(?=[^>]*\brel\s*=\s*(["\'])[^"\']*\bcanonical\b[^"\']*\1)[^>]*\bhref\s*=\s*(["\'])(.*?)\2[^>]*>',
    re.I | re.S,
)
YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def load_audit_module():
    spec = importlib.util.spec_from_file_location("rawafid_magazine_audit_v202", AUDIT_SCRIPT)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to import {AUDIT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def plain_text(fragment: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", fragment, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return html.unescape(re.sub(r"\s+", " ", value)).strip()


def description_from_html(text: str) -> str:
    for pattern in (DESCRIPTION_RE, LEAD_RE, P_RE):
        match = pattern.search(text)
        if match:
            value = plain_text(match.group(1))
            if value:
                return value[:360]
    return "قراءة عربية نقدية للدراسة الأصلية، تشمل المنهج والنتائج والقيود والمصدر."


def date_from_html(path: Path, text: str) -> str:
    match = DATE_JSONLD_RE.search(text)
    if match:
        return match.group(1)
    match = DATE_META_RE.search(text)
    if match:
        value = match.group(1)[:10]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return value
    for candidate in (path.stem, path.parent.name):
        year_match = YEAR_RE.search(candidate)
        if year_match:
            return f"{year_match.group(0)}-01-01"
    return "1970-01-01"


def canonical_from_html(path: Path, text: str) -> str:
    match = CANONICAL_RE.search(text)
    if match:
        candidate = html.unescape(match.group(3)).strip()
        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https"} and parsed.netloc.lower() in {"healthrenewal.org", "www.healthrenewal.org"}:
            return candidate.replace("https://www.healthrenewal.org", BASE).replace("http://healthrenewal.org", BASE)
    rel = path.relative_to(ROOT).as_posix()
    if rel.endswith("/index.html"):
        return BASE + "/" + rel[: -len("index.html")]
    return BASE + "/" + rel


def source_kind(page: dict[str, Any]) -> str:
    if page.get("doi") and page.get("pmid"):
        return "DOI + PMID"
    if page.get("doi"):
        return "DOI"
    if page.get("pmid"):
        return "PMID"
    if page.get("source_urls"):
        return "سجل/مصدر أصلي"
    return "المصدر يحتاج استكمالًا"


def load_verification(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    pages = data.get("pages") if isinstance(data, dict) else None
    if not isinstance(pages, list):
        return {}
    return {str(item.get("path")): item for item in pages if isinstance(item, dict) and item.get("path")}


def verification_status(page: dict[str, Any], verification: dict[str, dict[str, Any]]) -> str:
    item = verification.get(str(page.get("path")))
    if item:
        return str(item.get("bibliographic_verification") or "pending")
    if page.get("doi") or page.get("pmid"):
        return "identifier_present_verification_pending"
    if page.get("source_urls"):
        return "source_url_manual_review"
    return "missing_source"


def quality_label(page_contract: str, bibliographic_status: str) -> tuple[str, str]:
    source_verified = bibliographic_status == "verified_identifier"
    if page_contract == "complete" and source_verified:
        return "موثقة ومكتملة", "verified"
    if source_verified:
        return "المصدر موثق · الصفحة تحتاج استكمالًا", "review"
    if bibliographic_status in {"identifier_present_verification_pending", "resolvable_identifier_manual_metadata_review"}:
        return "المعرّف موجود · التحقق جارٍ", "pending"
    if bibliographic_status == "source_url_manual_review":
        return "المصدر يحتاج مطابقة يدوية", "pending"
    return "المصدر/البنية تحتاج استكمالًا", "gap"


@dataclass
class Article:
    source_path: str
    relative_path: str
    url: str
    title: str
    description: str
    date_published: str
    page_contract: str
    source_contract: str
    bibliographic_status: str
    source_kind: str
    doi: list[str]
    pmid: list[str]
    source_urls: list[str]
    word_count: int
    missing_sections: list[str]
    quality_label: str
    quality_class: str


def article_records(verification_path: Path | None = None) -> tuple[list[Article], dict[str, Any]]:
    audit = load_audit_module()
    manifest = audit.build_manifest()
    verification = load_verification(verification_path)
    records: list[Article] = []
    for page in manifest["pages"]:
        path = ROOT / str(page["path"])
        text = path.read_text(encoding="utf-8", errors="replace")
        title = str(page.get("title") or "").strip()
        if not title:
            h1 = H1_RE.search(text)
            title = plain_text(h1.group(1)) if h1 else path.stem.replace("-", " ")
        status = verification_status(page, verification)
        label, quality_class = quality_label(str(page.get("page_contract")), status)
        records.append(
            Article(
                source_path=str(page["path"]),
                relative_path=path.relative_to(SOURCE).as_posix(),
                url=canonical_from_html(path, text),
                title=title,
                description=description_from_html(text),
                date_published=date_from_html(path, text),
                page_contract=str(page.get("page_contract")),
                source_contract=str(page.get("source_contract")),
                bibliographic_status=status,
                source_kind=source_kind(page),
                doi=[str(x) for x in page.get("doi") or []],
                pmid=[str(x) for x in page.get("pmid") or []],
                source_urls=[str(x) for x in page.get("source_urls") or []],
                word_count=int(page.get("word_count") or 0),
                missing_sections=[str(x) for x in page.get("missing_sections") or []],
                quality_label=label,
                quality_class=quality_class,
            )
        )
    records.sort(key=lambda item: (item.date_published, item.url), reverse=True)
    return records, manifest


def validate_records(records: list[Article]) -> dict[str, Any]:
    if not records:
        raise SystemExit("Magazine v202 discovered zero study pages")
    urls = [record.url for record in records]
    duplicate_urls = sorted({url for url in urls if urls.count(url) > 1})
    if duplicate_urls:
        raise SystemExit(f"Duplicate magazine canonical URLs: {duplicate_urls[:10]}")

    noindex: list[str] = []
    canonical_issues: list[str] = []
    h1_issues: list[str] = []
    for record in records:
        path = SOURCE / record.relative_path
        text = path.read_text(encoding="utf-8", errors="replace")
        robots = ROBOTS_PATTERN.findall(text)
        if any("noindex" in value.lower() for value in robots):
            noindex.append(record.relative_path)
        parsed = urlparse(record.url)
        if parsed.scheme != "https" or parsed.netloc != "healthrenewal.org":
            canonical_issues.append(record.relative_path)
        if len(re.findall(r"<h1\b", text, flags=re.I)) != 1:
            h1_issues.append(record.relative_path)
    if noindex:
        raise SystemExit(f"Published magazine study pages must not contain noindex: {noindex[:10]}")
    if canonical_issues:
        raise SystemExit(f"Magazine canonical contract failed: {canonical_issues[:10]}")
    if h1_issues:
        raise SystemExit(f"Magazine study pages must contain exactly one H1: {h1_issues[:10]}")
    return {
        "noindex_pages": 0,
        "duplicate_canonical_urls": 0,
        "single_h1_contract": True,
    }


def render_index(records: list[Article], manifest: dict[str, Any]) -> str:
    verified = sum(1 for item in records if item.quality_class == "verified")
    identifier_present = sum(1 for item in records if item.doi or item.pmid)
    gaps = sum(1 for item in records if item.quality_class == "gap")
    cards: list[str] = []
    for item in records:
        identifiers: list[str] = []
        if item.doi:
            identifiers.append("DOI: " + html.escape(item.doi[0]))
        if item.pmid:
            identifiers.append("PMID: " + html.escape(item.pmid[0]))
        source_line = " · ".join(identifiers) if identifiers else html.escape(item.source_kind)
        cards.append(
            f'''<article class="card" data-quality="{html.escape(item.quality_class)}">
  <div class="meta"><span>{html.escape(item.date_published)}</span><span>{html.escape(item.source_kind)}</span></div>
  <h2><a href="{html.escape(item.url, quote=True)}">{html.escape(item.title)}</a></h2>
  <p>{html.escape(item.description)}</p>
  <div class="source-line">{source_line}</div>
  <div class="quality {html.escape(item.quality_class)}">{html.escape(item.quality_label)}</div>
  <a class="read" href="{html.escape(item.url, quote=True)}">قراءة الدراسة الكاملة</a>
</article>'''
        )
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "المجلة والأبحاث | منصة روافد",
        "url": URL,
        "inLanguage": "ar",
        "numberOfItems": len(records),
        "hasPart": [
            {
                "@type": "ScholarlyArticle",
                "headline": item.title,
                "url": item.url,
                "datePublished": item.date_published,
            }
            for item in records
        ],
    }
    unclassified = int(manifest.get("summary", {}).get("unclassified_nested_indexes") or 0)
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>المجلة والأبحاث | روافد</title>
<meta name="description" content="قراءات عربية منهجية للدراسات والأبحاث والرسائل الجامعية، مع المصدر الأصلي والمنهج والنتائج والقيود والدلالة العملية.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{URL}">
<link rel="alternate" type="application/rss+xml" title="خلاصة المجلة والأبحاث" href="{URL}feed.xml">
<link rel="stylesheet" href="research.css">
<script type="application/ld+json">{html.escape(json.dumps(schema, ensure_ascii=False, separators=(",", ":")), quote=False)}</script>
<style>
.audit-summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}}
.audit-summary>div{{background:#fff;border:1px solid #d7eae7;border-radius:14px;padding:14px}}
.audit-summary strong{{display:block;font-size:1.35rem}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}}
.card{{background:#fff;border:1px solid #d7eae7;border-radius:18px;padding:18px;display:flex;flex-direction:column;gap:10px}}
.card h2{{font-size:1.12rem;line-height:1.65;margin:0}}
.meta{{display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;font-size:.85rem;opacity:.78}}
.source-line{{font-size:.88rem;overflow-wrap:anywhere}}
.quality{{font-weight:700;font-size:.88rem}}
.quality.verified{{color:#0b6b47}} .quality.pending,.quality.review{{color:#765100}} .quality.gap{{color:#8a2635}}
.read{{margin-top:auto;font-weight:800}}
</style>
</head>
<body>
<a class="skip" href="#main">تجاوز إلى المحتوى</a>
<header><div class="wrap header-inner"><a class="brand" href="/">منصة روافد</a><nav aria-label="التنقل الرئيسي"><a href="/">الرئيسية</a><a href="/encyclopedia/">الموسوعة</a><a href="/special-needs/">ذوو الاحتياجات الخاصة</a><a href="/magazine/" aria-current="page">المجلة والأبحاث</a></nav></div></header>
<main id="main"><section class="hero"><div class="wrap">
<p class="eyebrow">مرصد روافد للأدلة العلمية</p>
<h1>المجلة والأبحاث</h1>
<p class="lead">كل عنوان في هذا الفهرس مرتبط بصفحة مستقلة. يميّز سجل الجودة بين وجود المعرّف، التحقق الببليوغرافي، واكتمال التحليل حتى لا يُعرض وجود DOI وحده باعتباره مراجعة مكتملة.</p>
<div class="audit-summary" aria-label="ملخص جودة المجلة">
<div><strong>{len(records)}</strong><span>صفحة دراسة مكتشفة</span></div>
<div><strong>{identifier_present}</strong><span>تحتوي DOI أو PMID</span></div>
<div><strong>{verified}</strong><span>موثقة ومكتملة وفق تقرير التحقق المرفق</span></div>
<div><strong>{gaps}</strong><span>تحتاج مصدرًا أو استكمالًا</span></div>
</div>
{f'<p class="notice">هناك {unclassified} ملفات index متداخلة غير مصنفة آليًا؛ بقيت منشورة ولم تُحذف، وهي مدرجة للمراجعة في تقرير v202.</p>' if unclassified else ''}
</div></section>
<section class="wrap"><div class="cards">{''.join(cards)}</div></section>
</main>
<footer><div class="wrap"><p>منصة روافد · قراءة علمية عربية مع إحالة إلى المصدر الأصلي.</p></div></footer>
</body></html>'''


def rss_date(value: str) -> str:
    try:
        dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
    return format_datetime(dt)


def render_feed(records: list[Article]) -> str:
    items: list[str] = []
    for item in records[:FEED_LIMIT]:
        items.append(
            f'''    <item>
      <title>{html.escape(item.title)}</title>
      <link>{html.escape(item.url)}</link>
      <guid isPermaLink="true">{html.escape(item.url)}</guid>
      <pubDate>{rss_date(item.date_published)}</pubDate>
      <description>{html.escape(item.description)}</description>
    </item>'''
        )
    latest = rss_date(records[0].date_published if records else "1970-01-01")
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>المجلة والأبحاث | منصة روافد</title>
    <link>{URL}</link>
    <description>قراءات عربية نقدية للدراسات الأصلية والمراجعات والرسائل الجامعية.</description>
    <language>ar</language>
    <atom:link href="{URL}feed.xml" rel="self" type="application/rss+xml"/>
    <lastBuildDate>{latest}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
'''


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    return root.tag.split("}", 1)[0] + "}" + name if root.tag.startswith("{") else name


def write_sitemaps(site: Path, records: list[Article]) -> dict[str, Any]:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    urls = list(dict.fromkeys([URL, *(item.url for item in records)]))
    child = site / "sitemap-magazine.xml"
    root = ET.Element(f"{{{ns}}}urlset")
    date_by_url = {item.url: item.date_published for item in records}
    for target_url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = target_url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = date_by_url.get(target_url, datetime.now(timezone.utc).date().isoformat())
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
        existing = {(node.text or "").strip() for node in main.findall("{*}url/{*}loc")}
        for target_url in urls:
            if target_url not in existing:
                item = ET.SubElement(main, qualify(main, "url"))
                ET.SubElement(item, qualify(main, "loc")).text = target_url
                existing.add(target_url)
                changed = True
    elif mode == "sitemapindex":
        child_url = BASE + "/sitemap-magazine.xml"
        existing = {(node.text or "").strip() for node in main.findall("{*}sitemap/{*}loc")}
        if child_url not in existing:
            item = ET.SubElement(main, qualify(main, "sitemap"))
            ET.SubElement(item, qualify(main, "loc")).text = child_url
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {mode}")
    if changed:
        tree.write(main_path, encoding="utf-8", xml_declaration=True)
    return {"main_mode": mode, "main_changed": changed, "child_urls": len(urls)}


def copy_source_tree(site: Path) -> Path:
    target = site / "magazine"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, target, dirs_exist_ok=True)
    return target


def publish(site: Path, verification_path: Path | None = None) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    records, manifest = article_records(verification_path)
    validation = validate_records(records)
    target = copy_source_tree(site)
    (target / "index.html").write_text(render_index(records, manifest), encoding="utf-8")
    feed = render_feed(records)
    ET.fromstring(feed)
    (target / "feed.xml").write_text(feed, encoding="utf-8")
    sitemap = write_sitemaps(site, records)

    indexed_urls = {item.url for item in records}
    verified = sum(1 for item in records if item.quality_class == "verified")
    complete_structure = sum(1 for item in records if item.page_contract == "complete")
    missing_source = sum(1 for item in records if item.source_contract == "missing_source")
    api_records = [asdict(item) for item in records]
    report: dict[str, Any] = {
        "version": CONTRACT,
        "page": "magazine/index.html",
        "url": URL,
        "discovery_contract": "recursive-study-tree-path-aware",
        "non_destructive": True,
        "published_study_pages": len(records),
        "index_cards": len(records),
        "wired_study_pages": sum(1 for item in records if item.url in indexed_urls),
        "unwired_research_pages": 0,
        "structurally_complete_pages": complete_structure,
        "bibliographically_verified_and_complete": verified,
        "identifier_present_pages": sum(1 for item in records if item.doi or item.pmid),
        "missing_source_pages": missing_source,
        "unclassified_nested_indexes": manifest.get("unclassified_nested_indexes", []),
        "target_research_summaries": TARGET_ARTICLES,
        "remaining_to_target": max(0, TARGET_ARTICLES - len(records)),
        "robots_contract": "published-study-pages-must-not-be-noindex",
        "validation": validation,
        "rss_items": min(FEED_LIMIT, len(records)),
        "sitemap": sitemap,
        "articles": api_records,
    }
    api_dir = site / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / API_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "articles"}, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("site", nargs="?", default="_site", type=Path)
    ap.add_argument("--verification", type=Path, default=None)
    args = ap.parse_args()
    publish(args.site.resolve(), args.verification.resolve() if args.verification else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
