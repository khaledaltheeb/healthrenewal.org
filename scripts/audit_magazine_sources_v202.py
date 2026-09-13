#!/usr/bin/env python3
"""Build a non-destructive source/completeness audit for Rawafid magazine pages.

The audit is intentionally additive: it never edits, moves, hides, or deletes a
published page. It recursively inspects magazine/**/*.html, extracts scientific
identifiers and external source links, evaluates the minimum study-page
contract, and writes a machine-readable manifest/report.

Exit codes:
  0 = report generated (default mode, even when gaps exist)
  2 = --strict was requested and one or more study pages are incomplete
  3 = magazine directory is missing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MAGAZINE = ROOT / "magazine"
DEFAULT_OUTPUT = ROOT / "data" / "magazine-source-manifest.json"

RAWAFID_HOSTS = {
    "healthrenewal.org",
    "www.healthrenewal.org",
    "rawafid-platform-staging.khaledaltheeb.workers.dev",
}

# Utility/listing pages are not scientific study records. Nested `index.html`
# files require special handling because Rawafid also uses directory-style URLs
# for individual studies. Study directories currently carry a publication year
# in their slug (for example `...-farber-2026/index.html`). Indexes that cannot
# be classified safely are surfaced separately instead of silently counted.
UTILITY_BASENAMES = {
    "search.html",
    "archive.html",
    "archives.html",
    "tags.html",
    "tag.html",
    "categories.html",
    "category.html",
    "about.html",
    "feed.html",
}
UTILITY_DIR_PARTS = {
    "assets",
    "css",
    "js",
    "images",
    "img",
    "page",
    "pages",
    "tag",
    "tags",
    "category",
    "categories",
    "archive",
    "archives",
}
YEAR_RE = re.compile(r"(?:19|20)\d{2}")

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
PMID_TEXT_RE = re.compile(r"\bPMID\s*[:#]?\s*(\d{5,10})\b", re.IGNORECASE)
PUBMED_URL_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{5,10})", re.IGNORECASE)

SECTION_GROUPS = {
    "research_question": (
        "سؤال الدراسة", "سؤال البحث", "research question", "objective", "aim",
    ),
    "design": (
        "تصميم الدراسة", "منهجية الدراسة", "نوع الدراسة", "study design", "methods", "methodology",
    ),
    "sample": (
        "العينة", "المشاركون", "participants", "sample", "population",
    ),
    "exposure_or_intervention": (
        "التدخل", "التعرض", "المقارنة", "intervention", "exposure", "comparator", "comparison",
    ),
    "results": (
        "النتائج", "النتائج الرئيسية", "results", "findings", "outcomes",
    ),
    "interpretation": (
        "تفسير النتائج", "التفسير", "interpretation", "discussion",
    ),
    "limitations": (
        "القيود", "محددات الدراسة", "نقاط الضعف", "limitations", "bias", "تحيز",
    ),
    "generalizability": (
        "قابلية التعميم", "التعميم", "generalizability", "generalisability", "external validity",
    ),
    "rawafid_reading": (
        "قراءة روافد", "تعليق روافد", "تحليل روافد", "rawafid reading", "rawafid analysis",
    ),
    "practical_implications": (
        "الدلالات العملية", "التطبيق العملي", "ماذا يعني عملي", "practical implications", "clinical implications",
    ),
    "not_proven": (
        "ما لا تثبته الدراسة", "لا تثبت الدراسة", "what this study does not prove", "does not prove",
    ),
    "references": (
        "المراجع", "المصدر الأصلي", "المصادر", "references", "original source", "citation",
    ),
}

SOURCE_HINT_HOSTS = (
    "doi.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "crossref.org",
    "nature.com",
    "sciencedirect.com",
    "springer.com",
    "springeropen.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "jamanetwork.com",
    "bmj.com",
    "thelancet.com",
    "oup.com",
    "academic.oup.com",
    "frontiersin.org",
    "plos.org",
    "journals.plos.org",
    "sagepub.com",
    "cambridge.org",
    "nejm.org",
    "cochranelibrary.com",
    "who.int",
    "unicef.org",
    "unesco.org",
    "nih.gov",
    "cdc.gov",
    "gov",
    "edu",
    "ac.uk",
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.canonical: str | None = None
        self.meta: dict[str, str] = {}
        self._text_parts: list[str] = []
        self._title_parts: list[str] = []
        self._h1_parts: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            href = attrs_d.get("href", "").strip()
            if href:
                self.links.append(href)
        elif tag == "link" and "canonical" in attrs_d.get("rel", "").lower():
            href = attrs_d.get("href", "").strip()
            if href:
                self.canonical = href
        elif tag == "meta":
            key = (attrs_d.get("name") or attrs_d.get("property") or "").strip().lower()
            value = attrs_d.get("content", "").strip()
            if key and value:
                self.meta[key] = value
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        value = " ".join(data.split())
        if not value:
            return
        self._text_parts.append(value)
        if self._in_title:
            self._title_parts.append(value)
        if self._in_h1:
            self._h1_parts.append(value)

    @property
    def text(self) -> str:
        return " ".join(self._text_parts)

    @property
    def title(self) -> str:
        h1 = " ".join(self._h1_parts).strip()
        if h1:
            return h1
        return " ".join(self._title_parts).strip()


def normalize_doi(value: str) -> str:
    value = value.strip().rstrip(".,;:)]}\u3002")
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi\s*:\s*", "", value, flags=re.IGNORECASE)
    return value.lower()


def normalize_url(url: str) -> str:
    return url.strip().replace("&amp;", "&")


def is_external_http(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return bool(host) and host not in RAWAFID_HOSTS


def is_probable_source_url(url: str) -> bool:
    if not is_external_http(url):
        return False
    host = (urlparse(url).hostname or "").lower()
    if any(host == hint or host.endswith("." + hint) for hint in SOURCE_HINT_HOSTS):
        return True
    lower = url.lower()
    return any(token in lower for token in ("/article/", "/doi/", "/journal/", "/research/", "/publication/"))


def unique(items: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _is_utility_path(path: Path) -> bool:
    rel = path.relative_to(MAGAZINE)
    rel_parts = {part.lower() for part in rel.parts[:-1]}
    return path.name.lower() in UTILITY_BASENAMES or bool(rel_parts & UTILITY_DIR_PARTS)


def _nested_index_is_study(path: Path) -> bool:
    if path.name.lower() != "index.html":
        return True
    rel = path.relative_to(MAGAZINE)
    if rel.as_posix().lower() == "index.html":
        return False
    return bool(YEAR_RE.search(path.parent.name))


def discover_pages() -> list[Path]:
    if not MAGAZINE.exists():
        return []
    pages: list[Path] = []
    for path in MAGAZINE.rglob("*.html"):
        if _is_utility_path(path):
            continue
        if path.name.lower() == "index.html" and not _nested_index_is_study(path):
            continue
        pages.append(path)
    return sorted(pages, key=lambda p: p.relative_to(MAGAZINE).as_posix())


def discover_unclassified_nested_indexes() -> list[Path]:
    if not MAGAZINE.exists():
        return []
    candidates: list[Path] = []
    for path in MAGAZINE.rglob("index.html"):
        rel = path.relative_to(MAGAZINE)
        if rel.as_posix().lower() == "index.html" or _is_utility_path(path):
            continue
        if not _nested_index_is_study(path):
            candidates.append(path)
    return sorted(candidates, key=lambda p: p.relative_to(MAGAZINE).as_posix())


def section_presence(text: str) -> dict[str, bool]:
    normalized = " ".join(text.lower().split())
    return {
        name: any(term.lower() in normalized for term in terms)
        for name, terms in SECTION_GROUPS.items()
    }


def extract_identifiers(html: str, parser: PageParser) -> tuple[list[str], list[str]]:
    doi_candidates = list(DOI_RE.findall(html))
    for link in parser.links:
        if "doi.org/" in link.lower():
            doi_candidates.append(link)
    for key in ("citation_doi", "dc.identifier", "dc.identifier.doi"):
        value = parser.meta.get(key)
        if value:
            doi_candidates.append(value)
    dois = unique(normalize_doi(v) for v in doi_candidates if DOI_RE.search(v))

    pmids = list(PMID_TEXT_RE.findall(parser.text))
    pmids.extend(PUBMED_URL_RE.findall(html))
    for key in ("citation_pmid", "pmid"):
        value = parser.meta.get(key, "")
        if value.isdigit():
            pmids.append(value)
    return dois, unique(pmids)


def source_urls(parser: PageParser) -> tuple[list[str], list[str]]:
    external = unique(normalize_url(u) for u in parser.links if is_external_http(normalize_url(u)))
    probable = [u for u in external if is_probable_source_url(u)]
    return external, unique(probable)


def canonical_for(path: Path, parser: PageParser) -> str:
    if parser.canonical:
        return parser.canonical
    rel = path.relative_to(ROOT).as_posix()
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    elif rel.endswith(".html"):
        rel = rel[: -len(".html")] + "/"
    return f"https://healthrenewal.org/{rel.lstrip('/')}"


def title_for(path: Path, parser: PageParser) -> str:
    title = parser.title.strip()
    if title:
        return title
    return path.parent.name.replace("-", " ").strip() if path.name == "index.html" else path.stem.replace("-", " ").strip()


@dataclass
class PageAudit:
    path: str
    url: str
    title: str
    content_sha256: str
    word_count: int
    doi: list[str]
    pmid: list[str]
    source_urls: list[str]
    external_urls: list[str]
    sections: dict[str, bool]
    missing_sections: list[str]
    source_contract: str
    page_contract: str
    bibliographic_verification: str
    issues: list[str]


def audit_page(path: Path) -> PageAudit:
    raw = path.read_bytes()
    html = raw.decode("utf-8", errors="replace")
    parser = PageParser()
    parser.feed(html)

    dois, pmids = extract_identifiers(html, parser)
    external_urls, probable_sources = source_urls(parser)
    sections = section_presence(parser.text)
    missing_sections = [name for name, present in sections.items() if not present]
    words = re.findall(r"[\w\u0600-\u06FF]+", parser.text, flags=re.UNICODE)

    if dois or pmids:
        source_contract = "identifier_present"
    elif probable_sources:
        source_contract = "source_url_only"
    else:
        source_contract = "missing_source"

    core_sections = {"design", "sample", "results", "limitations", "references"}
    core_missing = sorted(core_sections & set(missing_sections))
    page_contract = "complete" if not core_missing and len(words) >= 500 else "incomplete"

    issues: list[str] = []
    if source_contract == "missing_source":
        issues.append("no_original_source_identifier_or_probable_source_url")
    elif source_contract == "source_url_only":
        issues.append("source_url_requires_bibliographic_verification")
    if not dois and not pmids:
        issues.append("no_doi_or_pmid")
    if len(words) < 500:
        issues.append("thin_content_under_500_words")
    issues.extend(f"missing_section:{name}" for name in core_missing)

    return PageAudit(
        path=path.relative_to(ROOT).as_posix(),
        url=canonical_for(path, parser),
        title=title_for(path, parser),
        content_sha256=hashlib.sha256(raw).hexdigest(),
        word_count=len(words),
        doi=dois,
        pmid=pmids,
        source_urls=probable_sources,
        external_urls=external_urls,
        sections=sections,
        missing_sections=missing_sections,
        source_contract=source_contract,
        page_contract=page_contract,
        bibliographic_verification="pending",
        issues=issues,
    )


def build_manifest() -> dict:
    pages = discover_pages()
    unclassified = discover_unclassified_nested_indexes()
    audits = [audit_page(path) for path in pages]

    complete = [a for a in audits if a.page_contract == "complete" and a.source_contract != "missing_source"]
    missing_source = [a for a in audits if a.source_contract == "missing_source"]
    source_url_only = [a for a in audits if a.source_contract == "source_url_only"]
    incomplete = [a for a in audits if a.page_contract != "complete"]

    return {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "magazine/**/*.html (recursive; utility/collection indexes excluded; year-qualified nested study indexes included)",
        "policy": {
            "destructive_changes": False,
            "bibliographic_verification_required_before_complete_publication": True,
            "unclassified_nested_indexes_require_review": True,
            "source_contract_values": ["identifier_present", "source_url_only", "missing_source"],
            "bibliographic_verification_initial_state": "pending",
        },
        "summary": {
            "study_pages": len(audits),
            "structurally_complete_with_source": len(complete),
            "incomplete_pages": len(incomplete),
            "missing_source": len(missing_source),
            "source_url_only": len(source_url_only),
            "identifier_present": sum(1 for a in audits if a.source_contract == "identifier_present"),
            "bibliographically_verified": 0,
            "unclassified_nested_indexes": len(unclassified),
        },
        "unclassified_nested_indexes": [p.relative_to(ROOT).as_posix() for p in unclassified],
        "pages": [asdict(a) for a in audits],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--strict", action="store_true", help="Fail if any study page violates the minimum contract")
    args = ap.parse_args()

    if not MAGAZINE.exists():
        print(f"ERROR: magazine directory not found: {MAGAZINE}", file=sys.stderr)
        return 3

    manifest = build_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = manifest["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}")

    has_gaps = bool(
        summary["incomplete_pages"]
        or summary["missing_source"]
        or summary["source_url_only"]
        or summary["unclassified_nested_indexes"]
    )
    return 2 if args.strict and has_gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
