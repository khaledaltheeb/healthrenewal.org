#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VERSION = 322
REPORT_NAME = "section-content-depth-v322.json"
EXCLUDED_PARTS = {".git", "node_modules", "vendor", "tests", "test-results", "coverage"}
FAMILIES = (
    ("home", lambda p: p == "index.html"),
    ("encyclopedia", lambda p: p.startswith("encyclopedia/")),
    ("comparisons", lambda p: p.startswith("comparisons/")),
    ("library", lambda p: p.startswith("library/")),
    ("care-guides", lambda p: p.startswith("care-guides/")),
    ("tips", lambda p: p.startswith("tips/")),
    ("special-needs", lambda p: p.startswith("special-needs/")),
    ("child", lambda p: p.startswith("sectors/child/")),
    ("family", lambda p: p.startswith("sectors/family/")),
    ("home-sector", lambda p: p.startswith("sectors/home/")),
    ("women", lambda p: p.startswith("sectors/women/")),
    ("magazine", lambda p: p.startswith("magazine/")),
    ("daily-tools", lambda p: p.startswith("daily-tools/")),
    ("learning-paths", lambda p: p.startswith("learning-paths/")),
    ("hubs", lambda p: p.startswith("hubs/")),
    ("assessment", lambda p: p.startswith(("assessment-lab/", "provider-assessment-demo/", "guided-assessment/"))),
    ("cognitive", lambda p: p.startswith("cognitive-lab/")),
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.parts: list[str] = []
        self.h1 = 0
        self.h2 = 0
        self.canonical = 0
        self.jsonld = 0
        self.external_https = 0
        self.source_markers = 0
        self.noindex = False
        self.in_script_jsonld = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {str(key).lower(): value or "" for key, value in attrs}
        self.stack.append(tag)
        if tag == "h1":
            self.h1 += 1
        elif tag == "h2":
            self.h2 += 1
        elif tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical += 1
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.jsonld += 1
            self.in_script_jsonld = True
        elif tag == "a":
            href = values.get("href", "")
            if href.startswith("https://") and "khaledaltheeb.github.io" not in href:
                self.external_https += 1
        elif tag in {"section", "div", "aside", "ol"}:
            combined = " ".join(values.values()).lower()
            if any(marker in combined for marker in ("source", "sources", "reference", "references", "citation", "المراجع", "المصادر")):
                self.source_markers += 1
        elif tag == "meta" and values.get("name", "").lower() in {"robots", "googlebot"}:
            if "noindex" in values.get("content", "").lower():
                self.noindex = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script":
            self.in_script_jsonld = False
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.in_script_jsonld or any(tag in self.stack for tag in ("style", "svg", "template", "noscript")):
            return
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.parts.append(value)

    @property
    def words(self) -> int:
        return len(re.findall(r"[\w\u0600-\u06ff]+", " ".join(self.parts), flags=re.UNICODE))


def family_for(relative: str) -> str:
    for name, predicate in FAMILIES:
        if predicate(relative):
            return name
    return "other"


def iter_pages(site: Path):
    for path in sorted(site.rglob("index.html")):
        relative = path.relative_to(site)
        if any(part in EXCLUDED_PARTS or part.startswith(".") for part in relative.parts):
            continue
        yield path, relative.as_posix()


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def audit(site: Path) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    all_pages: list[dict[str, Any]] = []
    for path, relative in iter_pages(site):
        source = path.read_text(encoding="utf-8", errors="strict")
        parser = PageParser()
        parser.feed(source)
        item = {
            "path": relative,
            "family": family_for(relative),
            "words": parser.words,
            "h1": parser.h1,
            "h2": parser.h2,
            "canonical": parser.canonical,
            "jsonld": parser.jsonld,
            "external_https": parser.external_https,
            "source_markers": parser.source_markers,
            "noindex": parser.noindex,
        }
        all_pages.append(item)
        grouped[item["family"]].append(item)

    sections: list[dict[str, Any]] = []
    for family, pages in grouped.items():
        indexable = [page for page in pages if not page["noindex"]]
        word_values = [page["words"] for page in indexable]
        short_threshold = 500 if family in {"daily-tools", "assessment", "cognitive"} else 700
        short_pages = sorted(
            ({"path": page["path"], "words": page["words"]} for page in indexable if page["words"] < short_threshold),
            key=lambda item: (item["words"], item["path"]),
        )
        missing_sources = [page["path"] for page in indexable if page["external_https"] == 0 and page["source_markers"] == 0]
        structural = [
            page["path"]
            for page in indexable
            if page["h1"] != 1 or page["canonical"] != 1 or page["jsonld"] == 0
        ]
        sections.append(
            {
                "family": family,
                "page_count": len(pages),
                "indexable_page_count": len(indexable),
                "minimum_words": min(word_values) if word_values else 0,
                "median_words": int(statistics.median(word_values)) if word_values else 0,
                "p25_words": percentile(word_values, 0.25),
                "maximum_words": max(word_values) if word_values else 0,
                "short_threshold": short_threshold,
                "short_page_count": len(short_pages),
                "missing_source_evidence_count": len(missing_sources),
                "structural_issue_count": len(structural),
                "priority_score": round(
                    (len(short_pages) * 4 + len(missing_sources) * 2 + len(structural) * 6)
                    / max(1, len(indexable)),
                    3,
                ),
                "shortest_pages": short_pages[:20],
                "missing_source_evidence": sorted(missing_sources)[:20],
                "structural_issues": sorted(structural)[:20],
            }
        )
    sections.sort(key=lambda item: (-item["priority_score"], item["median_words"], item["family"]))

    evidence_pages = [page for page in all_pages if page["path"].startswith("library/evidence-literacy/")]
    expected_evidence = {
        "library/evidence-literacy/index.html",
        "library/evidence-literacy/how-to-read-systematic-review/index.html",
        "library/evidence-literacy/certainty-of-evidence-and-recommendations/index.html",
        "library/evidence-literacy/study-designs-bias-and-causality/index.html",
        "library/evidence-literacy/appraise-clinical-guideline/index.html",
    }
    found_evidence = {page["path"] for page in evidence_pages}
    if found_evidence != expected_evidence:
        raise SystemExit({"evidence_literacy_audit_routes": {"expected": sorted(expected_evidence), "found": sorted(found_evidence)}})
    if any(page["h1"] != 1 or page["canonical"] != 1 or page["jsonld"] == 0 for page in evidence_pages):
        raise SystemExit("Evidence-literacy pages failed structural audit")
    guide_pages = [page for page in evidence_pages if page["path"] != "library/evidence-literacy/index.html"]
    if min(page["words"] for page in guide_pages) < 900:
        raise SystemExit("Evidence-literacy guide depth fell below 900 words")

    report = {
        "version": VERSION,
        "status": "passed",
        "html_index_pages_scanned": len(all_pages),
        "family_count": len(sections),
        "sections_ranked": sections,
        "highest_priority_sections": [section["family"] for section in sections[:10]],
        "evidence_literacy_page_count": len(evidence_pages),
        "evidence_literacy_minimum_guide_words": min(page["words"] for page in guide_pages),
        "evidence_literacy_structural_issues": 0,
        "measurement_note": "Priority scores identify candidate review areas; they do not by themselves prove that a page is clinically or educationally inadequate.",
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Missing site directory: {args.site}")
    print(json.dumps(audit(args.site.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
