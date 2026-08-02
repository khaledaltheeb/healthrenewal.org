from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

HOST = "healthrenewal.org"
LEGACY_HOST = "khaledaltheeb.github.io"
LEGACY_BASE_PATH = "/pterminology-site/"
BASE_PATH = "/"
BASE_URL = f"https://{HOST}"
VERSION = 198
REPORT_RELATIVE = Path("api/internal-base-paths-v198.json")
TEXT_SUFFIXES = {
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".webmanifest",
    ".js",
    ".mjs",
    ".css",
    ".svg",
    ".txt",
}
ROUTE_REPAIRS = (
    {
        "missing": "/guides/evaluate-mental-health-information/",
        "fallback": "/trust/",
        "text": {
            "دليل تقييم معلومات الصحة النفسية": "مركز الثقة ومنهجية تقييم المحتوى",
        },
    },
    {
        "missing": "/search/",
        "fallback": "/encyclopedia/",
        "text": {
            "ابحث في الموقع": "ابحث في الموسوعة",
        },
    },
    {
        "missing": "/blog/",
        "fallback": "/tips/",
        "text": {
            "أريد قراءة تحليل أعمق": "أريد قراءة توجيهات ومقالات مبسطة",
            "استخدم المدونة للمقالات التحليلية وتبسيط الدراسات وتصحيح المفاهيم، مع فصل واضح بين الدليل والرأي.": "استخدم قسم النصائح والمحتوى التثقيفي لقراءة شروح مبسطة وروابط إلى المصادر والأدلة ذات الصلة.",
            "استعرض المقالات": "استعرض النصائح والمحتوى التثقيفي",
        },
    },
)

ABSOLUTE_INTERNAL_RE = re.compile(
    r"(?P<prefix>(?:https?:)?//)"
    r"(?P<host>"
    + re.escape(HOST)
    + r"|"
    + re.escape(LEGACY_HOST)
    + r")"
    + r"(?P<path>/[^\s\"'<>)]*)?",
    re.IGNORECASE,
)
# Match only complete URL values that still carry the retired GitHub Pages
# project prefix. Root-relative URLs are the canonical form on healthrenewal.org.
QUOTED_LEGACY_RE = re.compile(
    r"(?P<quote>[\"'])(?P<path>/pterminology-site(?:/"
    r"[A-Za-z0-9._~!$&()*+,;=:@%/?#-]*)?)(?=(?P=quote))"
)
UNQUOTED_LEGACY_ATTRIBUTE_RE = re.compile(
    r"(?P<prefix>\b(?:href|src|action|poster|data)\s*=\s*)"
    r"(?P<path>/pterminology-site(?:/[^\s>]+)?)",
    re.IGNORECASE,
)
LEGACY_CSS_URL_RE = re.compile(
    r"(?P<prefix>url\(\s*)(?P<path>/pterminology-site(?:/[^\s)]+)?)(?P<suffix>\s*\))",
    re.IGNORECASE,
)


def normalize_absolute(match: re.Match[str]) -> str:
    path = match.group("path") or "/"
    legacy_root = LEGACY_BASE_PATH.rstrip("/")
    if path == legacy_root:
        path = "/"
    elif path.startswith(LEGACY_BASE_PATH):
        path = path[len(legacy_root) :]
    return BASE_URL + path


def normalize_legacy_path(path: str) -> str:
    legacy_root = LEGACY_BASE_PATH.rstrip("/")
    if path == legacy_root:
        return "/"
    return path[len(legacy_root) :]


def normalize_text(text: str) -> tuple[str, int]:
    replacements = 0

    def replace_absolute(match: re.Match[str]) -> str:
        nonlocal replacements
        original = match.group(0)
        fixed = normalize_absolute(match)
        if fixed != original:
            replacements += 1
        return fixed

    text = ABSOLUTE_INTERNAL_RE.sub(replace_absolute, text)

    def replace_quoted_legacy(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return f'{match.group("quote")}{normalize_legacy_path(match.group("path"))}'

    text = QUOTED_LEGACY_RE.sub(replace_quoted_legacy, text)

    def replace_unquoted_legacy(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return f'{match.group("prefix")}{normalize_legacy_path(match.group("path"))}'

    text = UNQUOTED_LEGACY_ATTRIBUTE_RE.sub(replace_unquoted_legacy, text)

    def replace_legacy_css(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return (
            f'{match.group("prefix")}{normalize_legacy_path(match.group("path"))}'
            f'{match.group("suffix")}'
        )

    text = LEGACY_CSS_URL_RE.sub(replace_legacy_css, text)
    return text, replacements


def route_target(site: Path, route: str) -> Path:
    relative = route.removeprefix(BASE_PATH).lstrip("/")
    target = site / relative
    if route.endswith("/"):
        target = target / "index.html"
    return target


def active_route_repairs(site: Path) -> list[dict[str, object]]:
    active: list[dict[str, object]] = []
    for repair in ROUTE_REPAIRS:
        missing = str(repair["missing"])
        fallback = str(repair["fallback"])
        if not route_target(site, missing).exists() and route_target(site, fallback).exists():
            active.append(repair)
    return active


def repair_missing_routes(
    text: str,
    repairs: list[dict[str, object]],
) -> tuple[str, int, dict[str, int]]:
    total = 0
    counts: dict[str, int] = {}
    for repair in repairs:
        missing = str(repair["missing"])
        fallback = str(repair["fallback"])
        route_count = 0
        absolute_old = BASE_URL + missing
        absolute_new = BASE_URL + fallback
        occurrences = text.count(absolute_old)
        if occurrences:
            text = text.replace(absolute_old, absolute_new)
            total += occurrences
            route_count += occurrences

        # At the production root, replace only complete URL values. A raw
        # replacement of /blog/, for example, would corrupt JavaScript regexes.
        for quote in ('"', "'"):
            old = quote + missing + quote
            new = quote + fallback + quote
            occurrences = text.count(old)
            if occurrences:
                text = text.replace(old, new)
                total += occurrences
                route_count += occurrences
        attribute_re = re.compile(
            r"(?P<prefix>\b(?:href|src|action|poster|data)\s*=\s*)"
            + re.escape(missing)
            + r"(?=[\s>])",
            re.IGNORECASE,
        )
        text, occurrences = attribute_re.subn(
            lambda match: match.group("prefix") + fallback,
            text,
        )
        total += occurrences
        route_count += occurrences
        for old, new in dict(repair.get("text", {})).items():
            occurrences = text.count(old)
            if occurrences:
                text = text.replace(old, new)
                total += occurrences
        counts[missing] = route_count
    return text, total, counts


def text_files(site: Path) -> Iterable[Path]:
    report_path = site / REPORT_RELATIVE
    for path in sorted(site.rglob("*")):
        if path == report_path:
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def bad_references(text: str, repairs: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for match in ABSOLUTE_INTERNAL_RE.finditer(text):
        path = match.group("path") or "/"
        if match.group("host").lower() != HOST or path == LEGACY_BASE_PATH.rstrip("/") or path.startswith(LEGACY_BASE_PATH):
            errors.append(match.group(0))
    errors.extend(match.group(0) for match in QUOTED_LEGACY_RE.finditer(text))
    errors.extend(match.group(0) for match in UNQUOTED_LEGACY_ATTRIBUTE_RE.finditer(text))
    errors.extend(match.group(0) for match in LEGACY_CSS_URL_RE.finditer(text))
    for repair in repairs:
        missing = str(repair["missing"])
        if BASE_URL + missing in text:
            errors.append(BASE_URL + missing)
        if any(quote + missing + quote in text for quote in ('"', "'")):
            errors.append(missing)
        attribute_re = re.compile(
            r"\b(?:href|src|action|poster|data)\s*=\s*"
            + re.escape(missing)
            + r"(?=[\s>])",
            re.IGNORECASE,
        )
        if attribute_re.search(text):
            errors.append(missing)
    return sorted(set(errors))


def normalize_site(site: Path, *, check_only: bool = False) -> dict[str, object]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")

    repairs = active_route_repairs(site)
    scanned = 0
    changed_files: list[str] = []
    replacements = 0
    missing_route_replacements = 0
    route_repair_counts: dict[str, int] = {str(item["missing"]): 0 for item in repairs}
    decode_skipped: list[str] = []

    for path in text_files(site):
        scanned += 1
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            decode_skipped.append(path.relative_to(site).as_posix())
            continue
        normalized, count = normalize_text(original)
        normalized, route_count, per_route = repair_missing_routes(normalized, repairs)
        replacements += count + route_count
        missing_route_replacements += route_count
        for route, value in per_route.items():
            route_repair_counts[route] = route_repair_counts.get(route, 0) + value
        if normalized != original:
            changed_files.append(path.relative_to(site).as_posix())
            if not check_only:
                path.write_text(normalized, encoding="utf-8")

    remaining: list[dict[str, object]] = []
    for path in text_files(site):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        refs = bad_references(text, repairs)
        if refs:
            remaining.append(
                {
                    "file": path.relative_to(site).as_posix(),
                    "references": refs[:20],
                    "count": len(refs),
                }
            )

    report: dict[str, object] = {
        "version": VERSION,
        "status": "passed" if not remaining else "failed",
        "host": HOST,
        "required_base_path": BASE_PATH,
        "files_scanned": scanned,
        "files_changed": len(changed_files),
        "changed_files": changed_files,
        "replacements": replacements,
        "missing_route_replacements": missing_route_replacements,
        "active_route_repairs": [
            {"missing": item["missing"], "fallback": item["fallback"]}
            for item in repairs
        ],
        "route_repair_counts": route_repair_counts,
        "decode_skipped": decode_skipped,
        "remaining_error_files": len(remaining),
        "remaining_errors": remaining,
        "example_fixed": {
            "legacy_project_route": "/pterminology-site/care-guides/",
            "correct_route": "/care-guides/",
        },
    }

    if not check_only:
        output = site / REPORT_RELATIVE
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    report = normalize_site(args.site.resolve(), check_only=args.check_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit("Internal links remain invalid after base-path and destination repair")


if __name__ == "__main__":
    main()
