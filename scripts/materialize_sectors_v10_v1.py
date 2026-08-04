#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VERSION = 1
BASE_URL = "https://healthrenewal.org"
CONTENT_DIR = Path("content/sectors-v10")
OUTPUT_ROOT = Path("evidence-guides")
REPORT_PATH = Path("api/sectors-v10-publication-v1.json")

LEGACY_SOURCES = {
    "family.json",
    "child.json",
    "home.json",
    "women.json",
    "tips.json",
}
MANUAL_REVIEW_SOURCES = {
    "aac-home-school-guide.json",
    "inclusive-school-transition.json",
    "mental-health-foundations.json",
}
REQUIRED_SOURCE_FIELDS = ("key", "title", "subtitle", "sources", "articles")
UNWANTED_TERMS = (
    "معاقين",
    "المعاقين",
    "ذوي الإعاقة",
)
WORD_RE = re.compile(r"[\u0600-\u06FF0-9A-Za-z]+")
SAFE_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class PublicationItem:
    source_path: Path
    payload: dict[str, Any]
    category: str
    route: str


class PublicationError(ValueError):
    pass


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def visible_word_count(value: str) -> int:
    return len(WORD_RE.findall(value))


def _https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _review_is_blocked(payload: dict[str, Any]) -> bool:
    for key, value in payload.items():
        normalized = key.lower().replace("-", "_")
        if "review" not in normalized:
            continue
        if any(token in normalized for token in ("external", "specialist", "clinical")):
            if value is False:
                return True
            if isinstance(value, str) and value.strip().lower() in {
                "required",
                "pending",
                "outstanding",
                "not-completed",
                "not_completed",
            }:
                return True
    return False


def classify(payload: dict[str, Any]) -> str:
    value = " ".join(
        [
            str(payload.get("key", "")),
            str(payload.get("title", "")),
            str(payload.get("subtitle", "")),
        ]
    ).lower()
    inclusion_tokens = (
        "inclusive",
        "family",
        "caregiver",
        "sibling",
        "school",
        "puberty",
        "toileting",
        "personal-care",
        "transition",
        "decision-making",
        "pain-distress",
        "routines",
        "autism-adhd",
    )
    services_tokens = (
        "service-access",
        "screening-tools",
        "research-digital",
        "evidence-brief",
        "first-mental-health-appointment",
    )
    if any(token in value for token in inclusion_tokens):
        return "family-inclusion"
    if any(token in value for token in services_tokens):
        return "services-evidence"
    return "mental-health"


CATEGORY_LABELS = {
    "mental-health": "الصحة النفسية والفهم السريري الآمن",
    "family-inclusion": "الأسرة والدمج والاستقلال والحماية",
    "services-evidence": "الخدمات والأدلة وأدوات الفهم",
}


def validate_source(path: Path, payload: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_SOURCE_FIELDS if not payload.get(field)]
    if missing:
        raise PublicationError(f"{path}: missing required fields: {missing}")

    key = str(payload["key"]).strip()
    if not SAFE_SLUG_RE.fullmatch(key):
        raise PublicationError(f"{path}: invalid key/slug: {key!r}")

    combined = json.dumps(payload, ensure_ascii=False)
    present_unwanted = [term for term in UNWANTED_TERMS if term in combined]
    if present_unwanted:
        raise PublicationError(f"{path}: unwanted terminology: {present_unwanted}")

    sources = payload.get("sources")
    if not isinstance(sources, list) or len(sources) < 2:
        raise PublicationError(f"{path}: at least two sources are required")
    source_urls: list[str] = []
    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            raise PublicationError(f"{path}: source {index} must be an object")
        name = str(source.get("name", "")).strip()
        url = str(source.get("url", "")).strip()
        if not name or not _https_url(url):
            raise PublicationError(f"{path}: invalid source {index}")
        source_urls.append(url)
    if len(source_urls) != len(set(source_urls)):
        raise PublicationError(f"{path}: duplicate source URLs")

    articles = payload.get("articles")
    if not isinstance(articles, list) or len(articles) < 2:
        raise PublicationError(f"{path}: at least two complete articles are required")

    article_slugs: list[str] = []
    for index, article in enumerate(articles, 1):
        if not isinstance(article, dict):
            raise PublicationError(f"{path}: article {index} must be an object")
        slug = str(article.get("slug", "")).strip()
        title = str(article.get("title", "")).strip()
        summary = str(article.get("summary", "")).strip()
        signals = article.get("signals")
        steps = article.get("steps")
        phrases = article.get("phrases")
        avoid = str(article.get("avoid", "")).strip()
        if not SAFE_SLUG_RE.fullmatch(slug):
            raise PublicationError(f"{path}: invalid article slug: {slug!r}")
        if not title or visible_word_count(summary) < 10:
            raise PublicationError(f"{path}: article {slug} lacks a substantive title/summary")
        if not isinstance(signals, list) or len(signals) < 3:
            raise PublicationError(f"{path}: article {slug} needs at least three signals")
        if not isinstance(steps, list) or len(steps) < 4:
            raise PublicationError(f"{path}: article {slug} needs at least four steps")
        if not isinstance(phrases, list) or len(phrases) < 2:
            raise PublicationError(f"{path}: article {slug} needs at least two practical phrases")
        if visible_word_count(avoid) < 3:
            raise PublicationError(f"{path}: article {slug} needs a clear avoidance note")
        article_slugs.append(slug)
    if len(article_slugs) != len(set(article_slugs)):
        raise PublicationError(f"{path}: duplicate article slugs")


def load_items(repo_root: Path) -> tuple[list[PublicationItem], list[dict[str, str]]]:
    source_root = repo_root / CONTENT_DIR
    if not source_root.is_dir():
        raise PublicationError(f"Content directory not found: {source_root}")

    items: list[PublicationItem] = []
    skipped: list[dict[str, str]] = []
    keys: set[str] = set()

    for path in sorted(source_root.glob("*.json")):
        if path.name in LEGACY_SOURCES:
            skipped.append({"source": path.relative_to(repo_root).as_posix(), "reason": "legacy-already-published"})
            continue
        if path.name in MANUAL_REVIEW_SOURCES:
            skipped.append({"source": path.relative_to(repo_root).as_posix(), "reason": "manual-publication-review-required"})
            continue

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise PublicationError(f"{path}: JSON root must be an object")
        if _review_is_blocked(payload):
            skipped.append({"source": path.relative_to(repo_root).as_posix(), "reason": "declared-external-review-outstanding"})
            continue

        try:
            validate_source(path, payload)
        except PublicationError as exc:
            skipped.append(
                {
                    "source": path.relative_to(repo_root).as_posix(),
                    "reason": "quality-contract-rejected",
                    "detail": str(exc),
                }
            )
            continue
        key = str(payload["key"])
        if key in keys:
            raise PublicationError(f"Duplicate publication key: {key}")
        keys.add(key)
        category = classify(payload)
        route = f"{OUTPUT_ROOT.as_posix()}/{key}/"
        items.append(PublicationItem(path, payload, category, route))

    if len(items) < 20:
        raise PublicationError(f"Refusing an unexpectedly small publication set: {len(items)}")
    return items, skipped


def _list_items(values: list[Any], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{esc(value)}</li>" for value in values) + f"</{tag}>"


def render_page(item: PublicationItem) -> str:
    payload = item.payload
    title = str(payload["title"])
    subtitle = str(payload["subtitle"])
    reviewed_at = str(payload.get("reviewed_at") or "2026-08-04")
    canonical = f"{BASE_URL}/{item.route}"
    category_label = CATEGORY_LABELS[item.category]
    description = subtitle[:300]
    source_items = "".join(
        f'<li><a href="{esc(source["url"])}" rel="noopener noreferrer" target="_blank">{esc(source["name"])}</a></li>'
        for source in payload["sources"]
    )
    article_sections: list[str] = []
    toc_links: list[str] = []
    for index, article in enumerate(payload["articles"], 1):
        anchor = f"article-{index}"
        toc_links.append(f'<a href="#{anchor}">{index}. {esc(article["title"])}</a>')
        article_sections.append(
            f'''<section class="guide-section" id="{anchor}">
<h2>{index}. {esc(article["title"])}</h2>
<p class="summary">{esc(article["summary"])}</p>
<div class="guide-grid">
<article class="panel"><h3>علامات أو مواقف تستحق الانتباه</h3>{_list_items(article["signals"])}</article>
<article class="panel"><h3>خطوات عملية منخفضة المخاطر</h3>{_list_items(article["steps"], ordered=True)}</article>
</div>
<article class="panel phrases"><h3>صياغات عملية مقترحة</h3>{_list_items(article["phrases"])}</article>
<aside class="avoid"><h3>ما يجب تجنبه</h3><p>{esc(article["avoid"])}</p></aside>
</section>'''
        )

    disclaimer = str(
        payload.get("disclaimer")
        or "هذا الدليل للتثقيف وتنظيم الملاحظات ولا يقدّم تشخيصًا أو علاجًا فرديًا. عند خطر مباشر أو تدهور حاد أو عجز عن البقاء بأمان، تُطلب خدمات الطوارئ أو الحماية المحلية المناسبة."
    )
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Article",
                    "@id": canonical + "#article",
                    "url": canonical,
                    "headline": title,
                    "description": description,
                    "inLanguage": "ar",
                    "dateModified": reviewed_at,
                    "isAccessibleForFree": True,
                    "author": {"@type": "Organization", "name": "منصة روافد"},
                    "publisher": {"@type": "Organization", "name": "منصة روافد", "url": BASE_URL + "/"},
                    "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
                },
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE_URL + "/"},
                        {"@type": "ListItem", "position": 2, "name": "الأدلة المبنية على المصادر", "item": BASE_URL + "/" + OUTPUT_ROOT.as_posix() + "/"},
                        {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
                    ],
                },
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)} | منصة روافد</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/assets/brand/logo-mark.svg" type="image/svg+xml">
<meta property="og:type" content="article">
<meta property="og:locale" content="ar_AR">
<meta property="og:site_name" content="منصة روافد">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE_URL}/assets/brand/social-card.svg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{BASE_URL}/assets/brand/social-card.svg">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--bg:#f4f8f7;--ink:#14251f;--muted:#536760;--card:#fff;--line:#cfddd8;--accent:#086454;--soft:#e4f2ed;--warn:#8a4f0b}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}}
a{{color:#075d4d}}
.skip{{position:absolute;inset-inline-start:-9999px}}
.skip:focus{{inset-inline-start:1rem;top:1rem;background:#fff;padding:.7rem;z-index:10}}
header,main,footer{{max-width:1180px;margin:auto;padding:1rem clamp(1rem,3vw,2rem)}}
header{{display:flex;justify-content:space-between;gap:1rem;align-items:center;flex-wrap:wrap}}
nav a{{margin-inline-end:1rem}}
.hero{{background:linear-gradient(135deg,var(--soft),#fff8e9);border:1px solid var(--line);border-radius:24px;padding:clamp(1.3rem,4vw,3rem);margin-block:1rem 1.5rem}}
h1{{font-size:clamp(2rem,5vw,3.4rem);line-height:1.35;margin:.3rem 0 1rem}}
h2{{font-size:clamp(1.45rem,3vw,2rem);line-height:1.5;margin-top:2.4rem}}
h3{{line-height:1.55}}
.meta{{color:var(--muted)}}
.toc{{display:flex;gap:.55rem;flex-wrap:wrap;background:#fff;border:1px solid var(--line);border-radius:18px;padding:1rem}}
.toc a{{background:var(--soft);border-radius:999px;padding:.35rem .75rem;text-decoration:none}}
.guide-section{{scroll-margin-top:1rem}}
.guide-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:1rem}}
.panel,.avoid,.sources,.safety{{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:1rem 1.2rem;margin:1rem 0}}
.avoid,.safety{{border-inline-start:6px solid var(--warn)}}
.summary{{font-size:1.08rem}}
li{{margin:.35rem 0}}
footer{{color:var(--muted);border-top:1px solid var(--line);margin-top:2rem}}
@media (prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
@media print{{header,.toc,footer{{display:none}}body{{background:#fff}}.panel,.avoid,.sources,.safety,.hero{{break-inside:avoid}}}}
</style>
</head>
<body data-publication="sectors-v10-v1" data-source="{esc(item.source_path.name)}">
<a class="skip" href="#main">تجاوز إلى المحتوى الرئيسي</a>
<header>
<a href="/" aria-label="منصة روافد - الرئيسية"><strong>منصة روافد</strong></a>
<nav aria-label="التنقل الرئيسي"><a href="/start-here/">ابدأ هنا</a><a href="/evidence-guides/">الأدلة</a><a href="/special-needs/">ذوو الاحتياجات الخاصة</a><a href="/trust/">الثقة والمنهج</a></nav>
</header>
<main id="main">
<section class="hero">
<p><strong>{esc(category_label)}</strong></p>
<h1>{esc(title)}</h1>
<p>{esc(subtitle)}</p>
<p class="meta">آخر مراجعة للمصدر: {esc(reviewed_at)} · المصدر الداخلي: {esc(item.source_path.name)} · نسخة النشر: v{VERSION}</p>
</section>
<aside class="safety"><h2>حدود الاستخدام والسلامة</h2><p>{esc(disclaimer)}</p></aside>
<nav class="toc" aria-label="محتويات الدليل">{''.join(toc_links)}<a href="#sources">المصادر</a></nav>
{''.join(article_sections)}
<section class="sources" id="sources"><h2>المصادر المرجعية</h2><p>روابط أصلية أو مؤسسية استخدمها ملف المحتوى. إدراج المصدر لا يعني شراكة أو اعتمادًا خارجيًا للمنصة.</p><ul>{source_items}</ul></section>
</main>
<footer><p>منصة روافد — محتوى عربي تثقيفي قائم على المصادر، مع مراجعة وتصحيح مستمرين.</p></footer>
</body>
</html>
'''


def render_hub(items: list[PublicationItem]) -> str:
    grouped: dict[str, list[PublicationItem]] = {key: [] for key in CATEGORY_LABELS}
    for item in items:
        grouped[item.category].append(item)

    sections: list[str] = []
    for category, label in CATEGORY_LABELS.items():
        cards = "".join(
            f'''<article class="card"><h3><a href="/{esc(item.route)}">{esc(item.payload["title"])}</a></h3>
<p>{esc(item.payload["subtitle"])}</p>
<p class="meta">{len(item.payload["articles"])} محاور · {len(item.payload["sources"])} مصادر</p></article>'''
            for item in sorted(grouped[category], key=lambda value: str(value.payload["title"]))
        )
        if cards:
            sections.append(f'<section><h2>{esc(label)}</h2><div class="grid">{cards}</div></section>')

    canonical = f"{BASE_URL}/{OUTPUT_ROOT.as_posix()}/"
    description = f"بوابة منصة روافد للأدلة العربية المبنية على المصادر، وتضم {len(items)} دليلًا في الصحة النفسية والأسرة والدمج والخدمات."
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "@id": canonical,
            "url": canonical,
            "name": "الأدلة العربية المبنية على المصادر",
            "description": description,
            "inLanguage": "ar",
            "numberOfItems": len(items),
            "isPartOf": {"@type": "WebSite", "name": "منصة روافد", "url": BASE_URL + "/"},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>الأدلة العربية المبنية على المصادر | منصة روافد</title>
<meta name="description" content="{esc(description)}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/assets/brand/logo-mark.svg" type="image/svg+xml">
<meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة روافد">
<meta property="og:title" content="الأدلة العربية المبنية على المصادر"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{canonical}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--bg:#f4f8f7;--ink:#14251f;--muted:#536760;--card:#fff;--line:#cfddd8;--accent:#086454;--soft:#e4f2ed}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}}a{{color:#075d4d}}
header,main,footer{{max-width:1180px;margin:auto;padding:1rem clamp(1rem,3vw,2rem)}}header{{display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap}}
.hero{{background:linear-gradient(135deg,var(--soft),#fff8e9);border:1px solid var(--line);border-radius:24px;padding:clamp(1.3rem,4vw,3rem);margin-block:1rem 2rem}}
h1{{font-size:clamp(2rem,5vw,3.5rem);line-height:1.35}}h2{{margin-top:2.5rem}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}}
.card{{background:#fff;border:1px solid var(--line);border-radius:18px;padding:1rem 1.2rem}}.meta{{color:var(--muted)}}footer{{border-top:1px solid var(--line);margin-top:2rem;color:var(--muted)}}
</style>
</head>
<body data-publication="sectors-v10-v1">
<header><a href="/"><strong>منصة روافد</strong></a><nav aria-label="التنقل الرئيسي"><a href="/start-here/">ابدأ هنا</a> <a href="/special-needs/">ذوو الاحتياجات الخاصة</a> <a href="/trust/">الثقة والمنهج</a></nav></header>
<main>
<section class="hero"><p><strong>مكتبة عملية قابلة للتدقيق</strong></p><h1>الأدلة العربية المبنية على المصادر</h1><p>{esc(description)}</p><p class="meta">يُستبعد من النشر الآلي أي ملف يحتاج مراجعة خارجية أو لا يحقق عقد اكتمال المحتوى والمراجع والسلامة.</p></section>
{''.join(sections)}
</main>
<footer><p>منصة روافد — لا تُستخدم هذه الأدلة للتشخيص الذاتي أو بدل التقييم المهني.</p></footer>
</body>
</html>
'''


def write_publication(repo_root: Path, *, check: bool = False) -> dict[str, Any]:
    items, skipped = load_items(repo_root)
    generated: dict[Path, str] = {}
    for item in items:
        generated[repo_root / item.route / "index.html"] = render_page(item)
    generated[repo_root / OUTPUT_ROOT / "index.html"] = render_hub(items)

    category_counts = Counter(item.category for item in items)
    total_articles = sum(len(item.payload["articles"]) for item in items)
    total_sources = sum(len(item.payload["sources"]) for item in items)
    report = {
        "schemaVersion": VERSION,
        "status": "passed",
        "publisher": "materialize_sectors_v10_v1",
        "pageCount": len(items),
        "hubCount": 1,
        "articleCount": total_articles,
        "sourceReferenceCount": total_sources,
        "qualityRejectedCount": sum(1 for entry in skipped if entry["reason"] == "quality-contract-rejected"),
        "categoryCounts": dict(sorted(category_counts.items())),
        "routes": ["/" + item.route for item in items],
        "skipped": skipped,
        "qualityGates": {
            "minimumPages": len(items) >= 20,
            "allRoutesUnique": len(items) == len({item.route for item in items}),
            "allSourcesValidated": True,
            "manualReviewSourcesExcluded": all(
                any(entry["source"].endswith(name) for entry in skipped)
                for name in MANUAL_REVIEW_SOURCES
            ),
            "legacySourcesNotDuplicated": all(
                any(entry["source"].endswith(name) for entry in skipped)
                for name in LEGACY_SOURCES
            ),
        },
    }
    generated[repo_root / REPORT_PATH] = json.dumps(report, ensure_ascii=False, indent=2) + "\n"

    drift: list[str] = []
    for path, source in generated.items():
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != source:
                drift.append(path.relative_to(repo_root).as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")

    if check and drift:
        raise SystemExit(json.dumps({"materialization_drift": drift}, ensure_ascii=False))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize reviewed sectors-v10 sources as public Rawafid evidence guides.")
    parser.add_argument("repo_root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--check", action="store_true", help="Fail if generated files are missing or stale.")
    args = parser.parse_args()
    report = write_publication(args.repo_root.resolve(), check=args.check)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
