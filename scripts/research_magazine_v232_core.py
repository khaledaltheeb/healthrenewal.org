#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v232" / "research-magazine-manifest-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
MAGAZINE_URL = BASE + "/magazine/"
SITEMAP_NAME = "sitemap-magazine.xml"
REQUIRED_FIELDS = {
    "slug", "title_ar", "title_original", "topic", "study_type", "journal",
    "year", "pmid", "doi", "published_at", "summary_ar", "methods_ar",
    "limitations_ar", "implications_ar",
}
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PMID_RE = re.compile(r"^\d{7,9}$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
FORBIDDEN_CLAIMS = (
    "يشخّص هذا الملخص", "يشخص هذا الملخص", "غيّر دواءك",
    "أوقف دواءك", "علاج مضمون", "نتيجة حاسمة نهائية",
)


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def visible_words(value: str) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", value, re.UNICODE))


def load_data(path: Path = CONTENT) -> dict:
    if not path.is_file():
        raise SystemExit(f"Missing research data: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if "summaries" not in data:
        summaries: list[dict] = []
        batch_files = data.get("batch_files")
        if not isinstance(batch_files, list) or not batch_files:
            raise SystemExit("Research magazine manifest has no batch files")
        for relative in batch_files:
            batch_path = ROOT / str(relative)
            if not batch_path.is_file():
                raise SystemExit(f"Missing research batch: {batch_path}")
            batch = json.loads(batch_path.read_text(encoding="utf-8"))
            if batch.get("version") != 232 or not isinstance(batch.get("summaries"), list):
                raise SystemExit(f"Invalid research batch: {batch_path}")
            summaries.extend(batch["summaries"])
        data["summaries"] = summaries
    if data.get("version") != 232:
        raise SystemExit("Research magazine data must use version 232")
    if data.get("status") != "internally-reviewed":
        raise SystemExit("Research summaries must remain internally reviewed")
    if data.get("risk_level") != "moderate":
        raise SystemExit("Research summaries must retain moderate health-content risk")
    target = data.get("target_pages")
    if not isinstance(target, int) or target < 100:
        raise SystemExit("Research magazine target must be at least 100 pages")
    summaries = data.get("summaries")
    if not isinstance(summaries, list) or not summaries:
        raise SystemExit("Research summaries list is empty")

    unique_fields = ("slug", "pmid", "doi", "title_original")
    seen: dict[str, set[str]] = {field: set() for field in unique_fields}
    errors: list[str] = []
    for index, item in enumerate(summaries, 1):
        missing = REQUIRED_FIELDS - set(item)
        if missing:
            errors.append(f"item {index}: missing {sorted(missing)}")
            continue
        if not SLUG_RE.fullmatch(str(item["slug"])):
            errors.append(f"item {index}: invalid slug")
        if not PMID_RE.fullmatch(str(item["pmid"])):
            errors.append(f"item {index}: invalid PMID")
        if not DOI_RE.fullmatch(str(item["doi"])):
            errors.append(f"item {index}: invalid DOI")
        if item["year"] not in (2025, 2026):
            errors.append(f"item {index}: year outside current editorial window")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(item["published_at"])):
            errors.append(f"item {index}: invalid publication date")
        for field in ("title_ar", "topic", "summary_ar", "methods_ar", "limitations_ar", "implications_ar"):
            text = str(item[field]).strip()
            if not ARABIC_RE.search(text):
                errors.append(f"item {index}: {field} must contain Arabic")
        if visible_words(str(item["summary_ar"])) < 35:
            errors.append(f"item {index}: Arabic summary is too short")
        for field in ("methods_ar", "limitations_ar", "implications_ar"):
            if visible_words(str(item[field])) < 20:
                errors.append(f"item {index}: {field} is too short")
        combined = " ".join(str(item[field]) for field in REQUIRED_FIELDS if field in item)
        found = [phrase for phrase in FORBIDDEN_CLAIMS if phrase in combined]
        if found:
            errors.append(f"item {index}: unsafe claim(s) {found}")
        for field in unique_fields:
            normalized = str(item[field]).strip().lower()
            if normalized in seen[field]:
                errors.append(f"item {index}: duplicate {field}")
            seen[field].add(normalized)
    if errors:
        raise SystemExit("Research magazine validation failed:\n" + "\n".join(errors))
    return data


def article_url(item: dict) -> str:
    return f'{MAGAZINE_URL}research/{item["slug"]}/'


def doi_url(item: dict) -> str:
    return "https://doi.org/" + quote(str(item["doi"]), safe="/().-_")


def pubmed_url(item: dict) -> str:
    return f'https://pubmed.ncbi.nlm.nih.gov/{item["pmid"]}/'


def render_schema(item: dict) -> str:
    canonical = article_url(item)
    graph = [
        {
            "@type": "ScholarlyArticle",
            "@id": canonical + "#article",
            "headline": item["title_ar"],
            "alternativeHeadline": item["title_original"],
            "description": item["summary_ar"],
            "url": canonical,
            "mainEntityOfPage": canonical,
            "inLanguage": "ar",
            "datePublished": item["published_at"],
            "dateModified": "2026-07-25",
            "isBasedOn": doi_url(item),
            "citation": item["title_original"],
            "identifier": [
                {"@type": "PropertyValue", "propertyID": "DOI", "value": item["doi"]},
                {"@type": "PropertyValue", "propertyID": "PMID", "value": item["pmid"]},
            ],
            "about": item["topic"],
            "publisher": {
                "@type": "Organization",
                "@id": BASE + "/#organization",
                "name": "منصة الصحة النفسية وذوي الاحتياجات الخاصة",
                "url": BASE + "/",
            },
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                {"@type": "ListItem", "position": 2, "name": "المجلة البحثية", "item": MAGAZINE_URL},
                {"@type": "ListItem", "position": 3, "name": item["title_ar"], "item": canonical},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))


STYLE = r'''
:root{--ink:#183f45;--muted:#4d6f73;--line:#c2e4df;--soft:#f3fbf9;--card:#fff;--brand:#086d68;--gold:#775300;--alert:#fff8e5}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f9fcfb;color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}
a{color:var(--brand);text-underline-offset:.18em}a:focus-visible{outline:3px solid var(--gold);outline-offset:4px;border-radius:4px}
.skip{position:absolute;inset-inline-start:-9999px;top:8px;background:#fff;padding:10px;border:2px solid var(--brand);z-index:9}.skip:focus{inset-inline-start:8px}
.site-head,.site-foot{padding:18px max(4vw,20px);background:var(--soft);border-color:var(--line)}.site-head{border-bottom:1px solid var(--line)}.site-foot{border-top:1px solid var(--line);margin-top:42px}
nav{display:flex;gap:14px;flex-wrap:wrap}main{width:min(1080px,92%);margin:auto;padding:34px 0 64px}h1,h2,h3{line-height:1.35}h1{font-size:clamp(2rem,5vw,3.4rem)}h2{font-size:clamp(1.35rem,3vw,2rem)}
.lead{font-size:1.13rem;color:var(--muted)}.panel,.study-card,.notice{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:22px;margin:18px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:16px}.study-card{margin:0;display:flex;flex-direction:column}.study-card p{margin:.4rem 0}.study-card a:last-child{margin-top:auto}
.meta{display:flex;gap:8px;flex-wrap:wrap}.tag{display:inline-block;background:var(--soft);border:1px solid var(--line);border-radius:999px;padding:.15rem .65rem;font-size:.9rem}
.notice{background:var(--alert);border-color:#e5d39c;border-inline-start:6px solid var(--gold)}.source-links{display:flex;gap:14px;flex-wrap:wrap}
.original{direction:ltr;text-align:left;font-family:Arial,sans-serif;color:#365b60}.progress{font-weight:700;font-size:1.08rem}
@media print{.site-head nav,.skip{display:none}.panel,.study-card,.notice{break-inside:avoid;border-color:#777}body{background:#fff}main{width:100%}}
'''
