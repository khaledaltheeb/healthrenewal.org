#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

VERSION = 234
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
COMMENT_RE = re.compile(r"<!--\s*([a-z0-9_-]+-v\d+):(start|end)\s*-->", re.I)
LANG_RE = re.compile(r"<html\b[^>]*\blang=([\"'])(.*?)\1", re.I | re.S)
NOINDEX_RE = re.compile(
    r"<meta\b(?=[^>]*\bname=[\"']robots[\"'])(?=[^>]*\bcontent=[\"'][^\"']*noindex)",
    re.I | re.S,
)
MARKER_HINTS = ("content", "depth", "provider-condition", "residual", "advanced", "term")
EXCLUDED_PARTS = {".git", "node_modules", "vendor", "__pycache__", "assets", "api"}

GROUP_MINIMUMS: dict[str, int] = {
    "terms": 650,
    "assessment-lab": 750,
    "assessments": 750,
    "guided-assessment": 750,
    "cognitive-lab": 700,
    "cognitive-tests": 700,
    "hubs": 600,
    "library": 750,
    "comparisons": 220,
    "encyclopedia": 200,
    "care-guides": 225,
    "special-needs": 225,
    "tips": 225,
    "sectors": 225,
    "daily-tools": 225,
    "learning-paths": 225,
    "start-here": 190,
    "sections": 190,
    "trust": 230,
    "partners": 190,
    "developers": 190,
    "about": 220,
    "methodology": 230,
    "citation": 210,
    "privacy": 190,
    "sources": 220,
    "stats": 190,
    "downloads": 190,
    "media-kit": 190,
    "tools": 190,
    "letters": 190,
    "english-index": 190,
}


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.text: list[str] = []
        self.heading: list[str] = []
        self.title: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", data).strip()
        if not value:
            return
        if self.stack and self.stack[-1] == "title":
            self.title.append(value)
        if "h1" in self.stack:
            self.heading.append(value)
        if not any(tag in self.stack for tag in ("script", "style", "noscript", "svg", "template")):
            self.text.append(value)


def visible_text(source: str) -> tuple[str, str]:
    parser = VisibleTextParser()
    parser.feed(source)
    return " ".join(parser.text), " ".join(parser.heading or parser.title).strip()


def visible_words(source: str) -> int:
    text, _ = visible_text(source)
    return len(WORD_RE.findall(html.unescape(text)))


def is_content_marker(name: str) -> bool:
    normalized = name.lower()
    return any(hint in normalized for hint in MARKER_HINTS)


def strip_generated_content(source: str, route: str) -> tuple[str, Counter[str]]:
    matches = [match for match in COMMENT_RE.finditer(source) if is_content_marker(match.group(1))]
    if not matches:
        return source, Counter()

    output: list[str] = []
    stack: list[str] = []
    counts: Counter[str] = Counter()
    cursor = 0

    for match in matches:
        name = match.group(1).lower()
        kind = match.group(2).lower()
        if kind == "start":
            if not stack:
                output.append(source[cursor:match.start()])
            stack.append(name)
            counts[name] += 1
            continue
        if not stack:
            raise ValueError(f"{route}: closing marker without start: {name}")
        expected = stack.pop()
        if expected != name:
            raise ValueError(f"{route}: marker nesting mismatch: expected {expected}, found {name}")
        if not stack:
            cursor = match.end()

    if stack:
        raise ValueError(f"{route}: unclosed generated marker: {stack[-1]}")
    output.append(source[cursor:])
    return "".join(output), counts


def route_for(relative: Path) -> str:
    if relative.name == "index.html":
        parent = relative.parent.as_posix().strip(".")
        return "/" + (parent + "/" if parent else "")
    return "/" + relative.as_posix()


def group_for(relative: Path) -> str | None:
    if not relative.parts or relative.parts[0] == "index.html":
        return None
    if relative.parts[:2] == ("provider-assessment-demo", "conditions"):
        return "provider-conditions"
    return relative.parts[0]


def minimum_for(relative: Path, group: str) -> int:
    if group == "provider-conditions":
        return 900
    return GROUP_MINIMUMS.get(group, 180)


def producer_candidates(repository: Path | None, group: str, markers: Counter[str]) -> list[str]:
    if repository is None or not (repository / "scripts").is_dir():
        return []
    tokens = {group, group.replace("-", "_"), *markers.keys()}
    tokens.update(part for part in group.split("-") if len(part) >= 4)
    scored: list[tuple[int, str]] = []
    for path in (repository / "scripts").glob("*.py"):
        name = path.name.lower()
        if name.startswith(("audit_", "verify_", "test_")):
            continue
        try:
            source = path.read_text(encoding="utf-8").lower()
        except (OSError, UnicodeDecodeError):
            continue
        score = sum(source.count(token.lower()) for token in tokens if token)
        score += 5 if any(token.replace("-", "_") in name for token in tokens) else 0
        score += 3 if "enrich" in name or "deepen" in name or "publish" in name else 0
        if score:
            scored.append((score, path.relative_to(repository).as_posix()))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [path for _, path in scored[:5]]


def audit(site: Path, repository: Path | None = None) -> dict[str, Any]:
    if not site.is_dir():
        raise FileNotFoundError(f"Site directory not found: {site}")

    dependencies: list[dict[str, Any]] = []
    malformed: list[str] = []
    marker_totals: Counter[str] = Counter()
    group_totals: Counter[str] = Counter()
    scanned = eligible = skipped_noindex = skipped_non_arabic = 0

    for path in sorted(site.rglob("*.html")):
        relative = path.relative_to(site)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        scanned += 1
        source = path.read_text(encoding="utf-8", errors="replace")
        if NOINDEX_RE.search(source):
            skipped_noindex += 1
            continue
        lang = LANG_RE.search(source)
        if not lang or not lang.group(2).lower().startswith("ar"):
            skipped_non_arabic += 1
            continue
        eligible += 1
        route = route_for(relative)
        group = group_for(relative) or "other"
        try:
            origin, markers = strip_generated_content(source, route)
        except ValueError as exc:
            malformed.append(str(exc))
            continue
        if not markers:
            continue

        final_words = visible_words(source)
        origin_words = visible_words(origin)
        minimum = minimum_for(relative, group)
        _, title = visible_text(origin)
        marker_totals.update(markers)
        group_totals[group] += 1
        dependencies.append(
            {
                "route": route,
                "route_group": group,
                "title": title,
                "minimum_words": minimum,
                "origin_words": origin_words,
                "final_words": final_words,
                "generated_words": max(0, final_words - origin_words),
                "origin_below_minimum": origin_words < minimum,
                "markers": dict(sorted(markers.items())),
                "producer_candidates": producer_candidates(repository, group, markers),
            }
        )

    dependencies.sort(key=lambda item: (item["origin_words"], item["route"]))
    below = [item for item in dependencies if item["origin_below_minimum"]]
    return {
        "version": VERSION,
        "status": "passed" if not malformed else "failed",
        "pages_scanned": scanned,
        "eligible_pages": eligible,
        "skipped_noindex": skipped_noindex,
        "skipped_non_arabic": skipped_non_arabic,
        "generated_dependency_pages": len(dependencies),
        "origin_below_minimum_count": len(below),
        "origin_sufficient_count": len(dependencies) - len(below),
        "malformed_marker_count": len(malformed),
        "minimum_origin_words": min((item["origin_words"] for item in dependencies), default=None),
        "maximum_generated_words": max((item["generated_words"] for item in dependencies), default=0),
        "marker_counts": dict(sorted(marker_totals.items())),
        "route_group_counts": dict(sorted(group_totals.items())),
        "dependencies": dependencies,
        "malformed_markers": malformed,
    }


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# اعتماد الصفحات على كتل التوسعة v234",
        "",
        f"- الحالة: **{report['status']}**",
        f"- صفحات تحتوي كتل توسعة: **{report['generated_dependency_pages']}**",
        f"- أصول دون الحد المستهدف: **{report['origin_below_minimum_count']}**",
        f"- علامات غير سليمة: **{report['malformed_marker_count']}**",
        "",
        "## الأولويات",
        "",
    ]
    for item in report["dependencies"]:
        if not item["origin_below_minimum"]:
            continue
        producers = "، ".join(item["producer_candidates"]) or "غير محدد"
        marker_names = "، ".join(item["markers"])
        lines.append(
            f"- `{item['route']}` — الأصل {item['origin_words']} / {item['minimum_words']}، "
            f"الناتج {item['final_words']} كلمة — الكتل: {marker_names} — الناشر المحتمل: {producers}"
        )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--fail-on-malformed", action="store_true")
    args = parser.parse_args()

    site = args.site.resolve()
    repository = args.repository.resolve() if args.repository else None
    report = audit(site, repository)
    json_path = args.json_output or site / "api" / "source-origin-depth-v234.json"
    markdown_path = args.markdown_output or site / "api" / "source-origin-depth-v234.md"
    write_reports(report, json_path, markdown_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.fail_on_malformed and report["malformed_marker_count"]:
        return 1
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
