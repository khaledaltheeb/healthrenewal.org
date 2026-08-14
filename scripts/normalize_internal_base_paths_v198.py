from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

DEFAULT_SITE_BASE = "https://khaledaltheeb.github.io/pterminology-site/"
VERSION = 198
REPORT_RELATIVE = Path("api/internal-base-paths-v198.json")
TEXT_SUFFIXES = {".html", ".htm", ".xml", ".json", ".webmanifest", ".js", ".mjs", ".css", ".svg", ".txt"}
ROUTE_REPAIRS = (
    {"missing": "/guides/evaluate-mental-health-information/", "fallback": "/trust/", "text": {"دليل تقييم معلومات الصحة النفسية": "مركز الثقة ومنهجية تقييم المحتوى"}},
    {"missing": "/search/", "fallback": "/encyclopedia/", "text": {"ابحث في الموقع": "ابحث في الموسوعة"}},
    {"missing": "/blog/", "fallback": "/tips/", "text": {
        "أريد قراءة تحليل أعمق": "أريد قراءة توجيهات ومقالات مبسطة",
        "استخدم المدونة للمقالات التحليلية وتبسيط الدراسات وتصحيح المفاهيم، مع فصل واضح بين الدليل والرأي.": "استخدم قسم النصائح والمحتوى التثقيفي لقراءة شروح مبسطة وروابط إلى المصادر والأدلة ذات الصلة.",
        "استعرض المقالات": "استعرض النصائح والمحتوى التثقيفي",
    }},
)

HOST = ""
BASE_PATH = "/"
BASE_URL = ""
ABSOLUTE_INTERNAL_RE: re.Pattern[str]
QUOTED_ROOT_RE: re.Pattern[str]
UNQUOTED_ATTRIBUTE_RE: re.Pattern[str]
CSS_URL_RE: re.Pattern[str]


def configure_site_base(site_base: str) -> None:
    global HOST, BASE_PATH, BASE_URL
    global ABSOLUTE_INTERNAL_RE, QUOTED_ROOT_RE, UNQUOTED_ATTRIBUTE_RE, CSS_URL_RE
    parsed = urlparse(site_base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid site base URL: {site_base!r}")
    if parsed.query or parsed.fragment:
        raise ValueError(f"Site base URL must not include query or fragment: {site_base!r}")
    HOST = parsed.netloc
    raw_path = parsed.path or "/"
    BASE_PATH = "/" if raw_path.strip("/") == "" else f"/{raw_path.strip('/')}/"
    BASE_URL = f"{parsed.scheme}://{HOST}{BASE_PATH.rstrip('/')}"
    ABSOLUTE_INTERNAL_RE = re.compile(r"(?P<prefix>(?:https?:)?//)" + re.escape(HOST) + r"(?P<path>/[^\s\"'<>)]*)?", re.IGNORECASE)
    if BASE_PATH == "/":
        QUOTED_ROOT_RE = re.compile(r"(?!x)x")
        UNQUOTED_ATTRIBUTE_RE = re.compile(r"(?!x)x")
        CSS_URL_RE = re.compile(r"(?!x)x")
    else:
        base_segment = re.escape(BASE_PATH.strip("/"))
        QUOTED_ROOT_RE = re.compile(rf"(?P<quote>[\"'])(?P<path>/(?!/|{base_segment}(?:/|(?=[\"']))|[?#])[A-Za-z0-9._~!$&()*+,;=:@%/?#-]*)(?=(?P=quote))")
        UNQUOTED_ATTRIBUTE_RE = re.compile(rf"(?P<prefix>\b(?:href|src|action|poster|data)\s*=\s*)(?P<path>/(?!/|{base_segment}(?:/|\b)|[?#])[^\s>]+)", re.IGNORECASE)
        CSS_URL_RE = re.compile(rf"(?P<prefix>url\(\s*)(?P<path>/(?!/|{base_segment}(?:/|\b)|[?#])[^\s)]+)(?P<suffix>\s*\))", re.IGNORECASE)


configure_site_base(DEFAULT_SITE_BASE)


def normalize_absolute(match: re.Match[str]) -> str:
    path = match.group("path") or "/"
    if path == "/":
        return BASE_URL + "/"
    if BASE_PATH != "/" and path == BASE_PATH.rstrip("/"):
        return BASE_URL
    if BASE_PATH != "/" and path.startswith(BASE_PATH):
        return "https://" + HOST + path
    return BASE_URL + path


def normalize_text(text: str) -> tuple[str, int]:
    replacements = 0
    def replace_absolute(match: re.Match[str]) -> str:
        nonlocal replacements
        original = match.group(0); fixed = normalize_absolute(match)
        if fixed != original: replacements += 1
        return fixed
    text = ABSOLUTE_INTERNAL_RE.sub(replace_absolute, text)
    def replace_quoted(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return f'{match.group("quote")}{BASE_PATH}{match.group("path").lstrip("/")}'
    text = QUOTED_ROOT_RE.sub(replace_quoted, text)
    def replace_unquoted(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return f'{match.group("prefix")}{BASE_PATH}{match.group("path").lstrip("/")}'
    text = UNQUOTED_ATTRIBUTE_RE.sub(replace_unquoted, text)
    def replace_css(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return f'{match.group("prefix")}{BASE_PATH}{match.group("path").lstrip("/")}{match.group("suffix")}'
    return CSS_URL_RE.sub(replace_css, text), replacements


def route_target(site: Path, route: str) -> Path:
    relative = route.removeprefix(BASE_PATH).lstrip("/")
    target = site / relative
    return target / "index.html" if route.endswith("/") else target


def active_route_repairs(site: Path) -> list[dict[str, object]]:
    return [repair for repair in ROUTE_REPAIRS if not route_target(site, str(repair["missing"])).exists() and route_target(site, str(repair["fallback"])).exists()]


def repair_missing_routes(text: str, repairs: list[dict[str, object]]) -> tuple[str, int, dict[str, int]]:
    total = 0; counts: dict[str, int] = {}
    for repair in repairs:
        missing = str(repair["missing"]); fallback = str(repair["fallback"])
        variants = ((BASE_URL + missing, BASE_URL + fallback), (BASE_PATH + missing.lstrip("/"), BASE_PATH + fallback.lstrip("/")))
        route_count = 0
        for old, new in variants:
            occurrences = text.count(old)
            if occurrences:
                text = text.replace(old, new); total += occurrences; route_count += occurrences
        for old, new in dict(repair.get("text", {})).items():
            occurrences = text.count(old)
            if occurrences:
                text = text.replace(old, new); total += occurrences
        counts[missing] = route_count
    return text, total, counts


def text_files(site: Path) -> Iterable[Path]:
    report_path = site / REPORT_RELATIVE
    for path in sorted(site.rglob("*")):
        if path != report_path and path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def bad_references(text: str, repairs: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    if BASE_PATH != "/":
        for match in ABSOLUTE_INTERNAL_RE.finditer(text):
            path = match.group("path") or "/"
            if path == "/" or not (path == BASE_PATH.rstrip("/") or path.startswith(BASE_PATH)):
                errors.append(match.group(0))
    errors.extend(match.group(0) for match in QUOTED_ROOT_RE.finditer(text))
    errors.extend(match.group(0) for match in UNQUOTED_ATTRIBUTE_RE.finditer(text))
    errors.extend(match.group(0) for match in CSS_URL_RE.finditer(text))
    for repair in repairs:
        missing = str(repair["missing"])
        for variant in (BASE_URL + missing, BASE_PATH + missing.lstrip("/")):
            if variant in text: errors.append(variant)
    return sorted(set(errors))


def normalize_site(site: Path, *, check_only: bool = False, site_base: str = DEFAULT_SITE_BASE) -> dict[str, object]:
    configure_site_base(site_base)
    if not site.is_dir(): raise SystemExit(f"Missing site directory: {site}")
    repairs = active_route_repairs(site)
    scanned = 0; changed_files: list[str] = []; replacements = 0; missing_route_replacements = 0
    route_repair_counts: dict[str, int] = {str(item["missing"]): 0 for item in repairs}; decode_skipped: list[str] = []
    for path in text_files(site):
        scanned += 1
        try: original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            decode_skipped.append(path.relative_to(site).as_posix()); continue
        normalized, count = normalize_text(original)
        normalized, route_count, per_route = repair_missing_routes(normalized, repairs)
        replacements += count + route_count; missing_route_replacements += route_count
        for route, value in per_route.items(): route_repair_counts[route] = route_repair_counts.get(route, 0) + value
        if normalized != original:
            changed_files.append(path.relative_to(site).as_posix())
            if not check_only: path.write_text(normalized, encoding="utf-8")
    remaining: list[dict[str, object]] = []
    for path in text_files(site):
        try: text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        refs = bad_references(text, repairs)
        if refs: remaining.append({"file": path.relative_to(site).as_posix(), "references": refs[:20], "count": len(refs)})
    report: dict[str, object] = {
        "version": VERSION, "status": "passed" if not remaining else "failed", "host": HOST,
        "site_base": site_base, "required_base_path": BASE_PATH, "files_scanned": scanned,
        "files_changed": len(changed_files), "changed_files": changed_files, "replacements": replacements,
        "missing_route_replacements": missing_route_replacements,
        "active_route_repairs": [{"missing": item["missing"], "fallback": item["fallback"]} for item in repairs],
        "route_repair_counts": route_repair_counts, "decode_skipped": decode_skipped,
        "remaining_error_files": len(remaining), "remaining_errors": remaining,
        "example_fixed": {"missing_prefix_route": "/care-guides/", "correct_route": BASE_PATH + "care-guides/"},
    }
    if not check_only:
        output = site / REPORT_RELATIVE; output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--site-base", default=os.environ.get("SITE_BASE", DEFAULT_SITE_BASE), help="Deployment base URL; SITE_BASE is honored when present, otherwise the legacy GitHub Pages contract is used.")
    args = parser.parse_args()
    report = normalize_site(args.site.resolve(), check_only=args.check_only, site_base=args.site_base)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed": raise SystemExit("Internal links remain invalid after base-path and destination repair")


if __name__ == "__main__":
    main()
