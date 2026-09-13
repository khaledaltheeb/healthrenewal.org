#!/usr/bin/env python3
"""Audit Rawafid magazine study pages without destructive changes.

The audit recursively discovers scientific pages, extracts source identifiers,
classifies source quality, and evaluates two content contracts:

* core contract: enough structure to be a usable study summary;
* gold contract: the complete editorial structure required for a finished
  Rawafid scientific page.

The detector is intentionally semantic. Arabic pages are not marked incomplete
merely because a heading says ``حدود الدليل`` instead of ``القيود`` or
``التصميم والعينة`` instead of ``تصميم الدراسة``. Systematic reviews can also
satisfy the sample contract by reporting their included studies/trials.

No page is edited, moved, hidden, deleted, or changed to noindex by this tool.
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

# These are known collection/hub pages, not study records. Keeping the list
# explicit avoids misclassifying hubs simply because they contain citations.
KNOWN_COLLECTION_INDEXES = {
    "index.html",
    "pediatric-oncology/index.html",
    "pediatric-oncology/studies/index.html",
    "pediatric-oncology/theses/index.html",
}

YEAR_RE = re.compile(r"(?:19|20)\d{2}")
PMID_SLUG_RE = re.compile(r"(?:^|[-_])(\d{7,9})$")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
PMID_TEXT_RE = re.compile(r"\bPMID\s*[:#]?\s*(\d{5,10})\b", re.IGNORECASE)
PUBMED_URL_RE = re.compile(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{5,10})", re.IGNORECASE)
NOINDEX_RE = re.compile(r"<meta\b[^>]*name=[\"']robots[\"'][^>]*content=[\"'][^\"']*noindex", re.I)
SCHOLARLY_RE = re.compile(r"[\"']@type[\"']\s*:\s*[\"']ScholarlyArticle[\"']", re.I)

# Common publisher route suffixes accidentally captured after a DOI URL.
# The rule is deliberately conservative and only strips them from DOI-looking
# values after extraction, not arbitrary URLs.
DOI_ROUTE_SUFFIX_RE = re.compile(r"/(?:full|abstract|pdf|epdf|html)$", re.I)

SECTION_GROUPS: dict[str, tuple[str, ...]] = {
    "research_question": (
        "سؤال الدراسة", "سؤال البحث", "السؤال البحثي", "ماذا بحثت هذه الدراسة",
        "الهدف من الدراسة", "هدف الدراسة", "research question", "objective", "aim",
    ),
    "design": (
        "تصميم الدراسة", "تصميم البحث", "التصميم والعينة", "تصميم الدراسة والعينة",
        "المنهج", "المنهجية", "منهجية الدراسة", "نوع الدراسة", "طريقة الدراسة",
        "مراجعة منهجية", "تحليل تلوي", "تجربة عشوائية", "دراسة عشوائية",
        "دراسة رصدية", "دراسة أترابية", "دراسة مقطعية", "دراسة نوعية",
        "study design", "methods", "methodology", "systematic review", "meta-analysis",
        "randomized", "randomised", "cohort", "cross-sectional", "qualitative study",
    ),
    "sample": (
        "العينة", "التصميم والعينة", "تصميم الدراسة والعينة", "المشاركون", "المرضى",
        "الأطفال المشاركون", "الأسر المشاركة", "الدراسات المشمولة", "الدراسات المدرجة",
        "التجارب المشمولة", "included studies", "included trials", "participants", "sample",
        "population", "patients",
    ),
    "exposure_or_intervention": (
        "التدخل", "التدخلات", "التعرض", "المقارنة", "المجموعة الضابطة", "العلاج المقارن",
        "intervention", "exposure", "comparator", "comparison", "control group",
    ),
    "results": (
        "النتائج", "النتيجة الرئيسية", "النتائج الرئيسية", "أبرز النتائج", "ماذا وجدت الدراسة",
        "results", "findings", "outcomes", "main outcome",
    ),
    "interpretation": (
        "تفسير النتائج", "التفسير", "ماذا تعني النتائج", "قراءة النتائج", "المناقشة",
        "interpretation", "discussion", "what the results mean",
    ),
    "limitations": (
        "القيود", "حدود الدراسة", "حدود الدليل", "حدود البحث", "الحذر المنهجي",
        "محددات الدراسة", "نقاط الضعف", "عدم اليقين", "مصادر التحيز", "خطر التحيز",
        "limitations", "cautions", "methodological caution", "bias", "uncertainty",
    ),
    "generalizability": (
        "قابلية التعميم", "حدود التعميم", "هل يمكن تعميم", "التعميم", "السياق المحلي",
        "generalizability", "generalisability", "external validity", "transferability",
    ),
    "rawafid_reading": (
        "قراءة روافد", "تعليق روافد", "تحليل روافد", "تقييم روافد", "من منظور روافد",
        "rawafid reading", "rawafid analysis",
    ),
    "practical_implications": (
        "الدلالات العملية", "التطبيق العملي", "ماذا يعني ذلك عملي", "ماذا تعني النتائج عملي",
        "للممارسة", "للممارسين", "للأسر", "practical implications", "clinical implications",
        "implications for practice",
    ),
    "not_proven": (
        "ما لا تثبته الدراسة", "ما الذي لا تثبته الدراسة", "لا تثبت الدراسة", "لا يثبت هذا البحث",
        "لا تعني النتيجة", "لا تكفي هذه الدراسة", "what this study does not prove", "does not prove",
    ),
    "references": (
        "المراجع", "المصدر الأصلي", "المصادر", "سجل الدراسة", "السجل الجامعي",
        "النص الأصلي", "references", "original source", "citation", "repository record",
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
    "etheses.whiterose.ac.uk",
    "repo.lib.duth.gr",
    "unige.iris.cineca.it",
    "edoc.ub.uni-muenchen.de",
    "uu.nl",
    "repository.ubn.ru.nl",
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
        self.headings: list[str] = []
        self._text_parts: list[str] = []
        self._title_parts: list[str] = []
        self._h1_parts: list[str] = []
        self._heading_parts: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._in_heading = False
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
        if tag == "h1":
            self._in_h1 = True
        if tag in {"h1", "h2", "h3", "h4"}:
            self._in_heading = True
            self._heading_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag == "h1":
            self._in_h1 = False
        if tag in {"h1", "h2", "h3", "h4"} and self._in_heading:
            heading = " ".join(self._heading_parts).strip()
            if heading:
                self.headings.append(heading)
            self._heading_parts = []
            self._in_heading = False

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
        if self._in_heading:
            self._heading_parts.append(value)

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
    value = html_unescape(value).strip().rstrip(".,;:)]}\u3002\"'")
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^doi\s*:\s*", "", value, flags=re.IGNORECASE)
    value = DOI_ROUTE_SUFFIX_RE.sub("", value)
    return value.lower()


def html_unescape(value: str) -> str:
    # Avoid importing the whole html module merely for entities commonly seen
    # inside href attributes.
    return value.replace("&amp;", "&").replace("&#x2F;", "/").replace("&#47;", "/")


def normalize_url(url: str) -> str:
    return html_unescape(url).strip()


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
    return any(token in lower for token in ("/article/", "/doi/", "/journal/", "/research/", "/publication/", "/handle/", "/eprint/"))


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
    rel_posix = rel.as_posix().lower()
    if rel_posix in KNOWN_COLLECTION_INDEXES:
        return True
    rel_parts = {part.lower() for part in rel.parts[:-1]}
    return path.name.lower() in UTILITY_BASENAMES or bool(rel_parts & UTILITY_DIR_PARTS)


def _index_has_study_signals(path: Path) -> bool:
    if path.name.lower() != "index.html":
        return True
    if _is_utility_path(path):
        return False
    parent_slug = path.parent.name.lower()
    if YEAR_RE.search(parent_slug) or PMID_SLUG_RE.search(parent_slug):
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    # A single nested page carrying article schema plus an identifier is a study
    # even if its slug has no year. Collection hubs are explicitly excluded.
    has_identifier = bool(DOI_RE.search(text) or PMID_TEXT_RE.search(text) or PUBMED_URL_RE.search(text))
    return bool(SCHOLARLY_RE.search(text) and has_identifier)


def discover_pages() -> list[Path]:
    if not MAGAZINE.exists():
        return []
    pages: list[Path] = []
    for path in MAGAZINE.rglob("*.html"):
        if _is_utility_path(path):
            continue
        if path.name.lower() == "index.html" and not _index_has_study_signals(path):
            continue
        pages.append(path)
    return sorted(pages, key=lambda p: p.relative_to(MAGAZINE).as_posix())


def discover_unclassified_nested_indexes() -> list[Path]:
    if not MAGAZINE.exists():
        return []
    candidates: list[Path] = []
    for path in MAGAZINE.rglob("index.html"):
        if _is_utility_path(path):
            continue
        if not _index_has_study_signals(path):
            candidates.append(path)
    return sorted(candidates, key=lambda p: p.relative_to(MAGAZINE).as_posix())


def _contains_any(normalized: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in normalized for term in terms)


def _numeric_sample_signal(normalized: str) -> bool:
    # Participant counts and evidence-unit counts used by primary studies,
    # qualitative syntheses, systematic reviews and meta-analyses.
    arabic_or_latin_digits = r"[0-9٠-٩]{1,6}"
    nouns = (
        r"طفل(?:اً|ا|ًا)?|أطفال|مشارك(?:اً|ا|ون|ين)?|مري(?:ض|ضة|ضًا|ضا)|مرضى|"
        r"أسرة|أسر|والد(?:اً|ا|ين)?|والدة|دراسة|دراسات|تجربة|تجارب|بحث|أبحاث|"
        r"participant(?:s)?|patient(?:s)?|child(?:ren)?|famil(?:y|ies)|stud(?:y|ies)|trial(?:s)?"
    )
    count_then_noun = re.search(rf"\b{arabic_or_latin_digits}\s+(?:{nouns})\b", normalized, re.I)
    n_equals = re.search(r"\bn\s*[=:]\s*[0-9]{1,6}\b", normalized, re.I)
    included = re.search(rf"(?:شملت|ضم(?:ت|ت الدراسة)|تضمنت|included|included studies|included trials)[^.!?؟]{{0,80}}{arabic_or_latin_digits}", normalized, re.I)
    return bool(count_then_noun or n_equals or included)


def _results_signal(normalized: str) -> bool:
    if _contains_any(normalized, SECTION_GROUPS["results"]):
        return True
    # Common quantitative reporting patterns. This is only a fallback and does
    # not replace the need for an explicit results section in the gold contract.
    return bool(re.search(r"(?:p\s*[<=>]\s*0?\.\d+|95%\s*(?:ci|فاصل)|(?:or|hr|rr|md|smd)\s*[=:])", normalized, re.I))


def _limitations_signal(normalized: str) -> bool:
    if _contains_any(normalized, SECTION_GROUPS["limitations"]):
        return True
    caution_patterns = (
        r"لا\s+(?:يمكن|يجوز)\s+تعميم",
        r"لا\s+تثبت",
        r"لا\s+يثبت",
        r"لا\s+تكفي",
        r"صغر\s+العينة",
        r"حجم\s+العينة\s+(?:صغير|محدود)",
        r"دون\s+تعمية",
        r"مفتوحة\s+(?:التسمية|العلامة)",
        r"single[- ]center",
        r"small sample",
    )
    return any(re.search(pattern, normalized, re.I) for pattern in caution_patterns)


def section_presence(text: str, *, has_source_evidence: bool = False) -> dict[str, bool]:
    normalized = " ".join(text.lower().split())
    presence = {
        name: _contains_any(normalized, terms)
        for name, terms in SECTION_GROUPS.items()
    }
    presence["sample"] = presence["sample"] or _numeric_sample_signal(normalized)
    presence["results"] = presence["results"] or _results_signal(normalized)
    presence["limitations"] = presence["limitations"] or _limitations_signal(normalized)
    if has_source_evidence:
        presence["references"] = True
    return presence


def extract_identifiers(raw_html: str, parser: PageParser) -> tuple[list[str], list[str]]:
    doi_candidates = list(DOI_RE.findall(raw_html))
    for link in parser.links:
        if "doi.org/" in link.lower():
            doi_candidates.append(link)
    for key in ("citation_doi", "dc.identifier", "dc.identifier.doi"):
        value = parser.meta.get(key)
        if value:
            doi_candidates.append(value)
    dois = unique(
        normalize_doi(value)
        for value in doi_candidates
        if DOI_RE.search(value)
    )

    pmids = list(PMID_TEXT_RE.findall(parser.text))
    pmids.extend(PUBMED_URL_RE.findall(raw_html))
    for key in ("citation_pmid", "pmid"):
        value = parser.meta.get(key, "")
        if value.isdigit():
            pmids.append(value)
    return dois, unique(pmids)


def source_urls(parser: PageParser) -> tuple[list[str], list[str]]:
    external = unique(
        normalize_url(url)
        for url in parser.links
        if is_external_http(normalize_url(url))
    )
    probable = [url for url in external if is_probable_source_url(url)]
    return external, unique(probable)


def canonical_for(path: Path, parser: PageParser) -> str:
    if parser.canonical:
        return parser.canonical
    rel = path.relative_to(ROOT).as_posix()
    if rel.endswith("index.html"):
        rel = rel[: -len("index.html")]
    return f"https://healthrenewal.org/{rel.lstrip('/')}"


def title_for(path: Path, parser: PageParser) -> str:
    title = parser.title.strip()
    if title:
        return title
    if path.name.lower() == "index.html":
        return path.parent.name.replace("-", " ").strip()
    return path.stem.replace("-", " ").strip()


CORE_SECTIONS = {"design", "sample", "results", "limitations", "references"}
GOLD_SECTIONS = {
    "research_question",
    "design",
    "sample",
    "exposure_or_intervention",
    "results",
    "interpretation",
    "limitations",
    "generalizability",
    "rawafid_reading",
    "practical_implications",
    "not_proven",
    "references",
}


@dataclass
class PageAudit:
    path: str
    url: str
    title: str
    content_sha256: str
    word_count: int
    heading_count: int
    doi: list[str]
    pmid: list[str]
    source_urls: list[str]
    external_urls: list[str]
    sections: dict[str, bool]
    missing_sections: list[str]
    missing_core_sections: list[str]
    missing_gold_sections: list[str]
    source_contract: str
    page_contract: str
    gold_contract: str
    bibliographic_verification: str
    noindex: bool
    issues: list[str]


def audit_page(path: Path) -> PageAudit:
    raw = path.read_bytes()
    raw_html = raw.decode("utf-8", errors="replace")
    parser = PageParser()
    parser.feed(raw_html)

    dois, pmids = extract_identifiers(raw_html, parser)
    external_urls, probable_sources = source_urls(parser)
    has_source_evidence = bool(dois or pmids or probable_sources)
    sections = section_presence(parser.text, has_source_evidence=has_source_evidence)
    missing_sections = [name for name, present in sections.items() if not present]
    missing_core = sorted(CORE_SECTIONS & set(missing_sections))
    missing_gold = sorted(GOLD_SECTIONS & set(missing_sections))
    words = re.findall(r"[\w\u0600-\u06FF]+", parser.text, flags=re.UNICODE)

    if dois or pmids:
        source_contract = "identifier_present"
    elif probable_sources:
        source_contract = "source_url_only"
    else:
        source_contract = "missing_source"

    page_contract = "complete" if not missing_core and len(words) >= 500 else "incomplete"
    gold_contract = "complete" if not missing_gold and len(words) >= 700 and source_contract != "missing_source" else "incomplete"
    noindex = bool(NOINDEX_RE.search(raw_html))

    issues: list[str] = []
    if source_contract == "missing_source":
        issues.append("no_original_source_identifier_or_probable_source_url")
    elif source_contract == "source_url_only":
        issues.append("source_url_requires_bibliographic_verification")
    if not dois and not pmids:
        issues.append("no_doi_or_pmid")
    if len(words) < 500:
        issues.append("thin_content_under_500_words")
    elif len(words) < 700:
        issues.append("below_gold_depth_700_words")
    if noindex:
        issues.append("published_page_contains_noindex")
    issues.extend(f"missing_core_section:{name}" for name in missing_core)
    issues.extend(f"missing_gold_section:{name}" for name in missing_gold)

    return PageAudit(
        path=path.relative_to(ROOT).as_posix(),
        url=canonical_for(path, parser),
        title=title_for(path, parser),
        content_sha256=hashlib.sha256(raw).hexdigest(),
        word_count=len(words),
        heading_count=len(parser.headings),
        doi=dois,
        pmid=pmids,
        source_urls=probable_sources,
        external_urls=external_urls,
        sections=sections,
        missing_sections=missing_sections,
        missing_core_sections=missing_core,
        missing_gold_sections=missing_gold,
        source_contract=source_contract,
        page_contract=page_contract,
        gold_contract=gold_contract,
        bibliographic_verification="pending",
        noindex=noindex,
        issues=issues,
    )


def build_manifest() -> dict:
    pages = discover_pages()
    unclassified = discover_unclassified_nested_indexes()
    audits = [audit_page(path) for path in pages]

    core_complete = [a for a in audits if a.page_contract == "complete" and a.source_contract != "missing_source"]
    gold_complete = [a for a in audits if a.gold_contract == "complete"]
    missing_source = [a for a in audits if a.source_contract == "missing_source"]
    source_url_only = [a for a in audits if a.source_contract == "source_url_only"]
    incomplete = [a for a in audits if a.page_contract != "complete"]
    noindex_pages = [a for a in audits if a.noindex]

    missing_core_counts = {
        section: sum(section in a.missing_core_sections for a in audits)
        for section in sorted(CORE_SECTIONS)
    }
    missing_gold_counts = {
        section: sum(section in a.missing_gold_sections for a in audits)
        for section in sorted(GOLD_SECTIONS)
    }

    return {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "magazine/**/*.html recursive; known collections excluded; nested year/PMID/schema study routes included",
        "policy": {
            "destructive_changes": False,
            "published_pages_must_remain_indexable": True,
            "bibliographic_verification_required_before_gold_publication": True,
            "semantic_section_detection": True,
            "systematic_reviews_use_included_studies_as_evidence_sample": True,
            "source_contract_values": ["identifier_present", "source_url_only", "missing_source"],
            "bibliographic_verification_initial_state": "pending",
        },
        "summary": {
            "study_pages": len(audits),
            "core_complete_with_source": len(core_complete),
            "gold_complete_before_bibliographic_verification": len(gold_complete),
            "incomplete_pages": len(incomplete),
            "missing_source": len(missing_source),
            "source_url_only": len(source_url_only),
            "identifier_present": sum(1 for a in audits if a.source_contract == "identifier_present"),
            "bibliographically_verified": 0,
            "unclassified_nested_indexes": len(unclassified),
            "noindex_pages": len(noindex_pages),
            "missing_core_section_counts": missing_core_counts,
            "missing_gold_section_counts": missing_gold_counts,
        },
        "unclassified_nested_indexes": [p.relative_to(ROOT).as_posix() for p in unclassified],
        "pages": [asdict(a) for a in audits],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--strict", action="store_true", help="Fail if any study violates the gold publication contract")
    args = ap.parse_args()

    if not MAGAZINE.exists():
        print(f"ERROR: magazine directory not found: {MAGAZINE}", file=sys.stderr)
        return 3

    manifest = build_manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = manifest["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    try:
        shown = args.output.relative_to(ROOT)
    except ValueError:
        shown = args.output
    print(f"Wrote {shown}")

    strict_gaps = (
        summary["gold_complete_before_bibliographic_verification"] != summary["study_pages"]
        or summary["missing_source"]
        or summary["source_url_only"]
        or summary["unclassified_nested_indexes"]
        or summary["noindex_pages"]
    )
    return 2 if args.strict and strict_gaps else 0


if __name__ == "__main__":
    raise SystemExit(main())
