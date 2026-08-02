#!/usr/bin/env python3
"""Apply the shared platform shell to every production HTML page.

The migration is deliberately idempotent. Existing pages keep their content and
local navigation; the script adds shared presentation assets, rights metadata,
and stable body markers. It can operate on the repository source tree or on the
generated ``_site`` production artifact.

When the target is a generated artifact, the script also copies the platform
runtime and public governance pages into that artifact before normalization.
Pages with strict single-runtime application contracts receive the shared CSS
and rights metadata but not the optional platform JavaScript enhancer.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
MARKER = "<!-- pt-platform-shell:v1 -->"
SHELL_VERSION = "1.1.0"
EXCLUDED_PARTS = {
    ".git",
    ".github",
    "_site",
    "node_modules",
    "vendor",
    "fixtures",
    "snapshots",
    "coverage",
    "reports",
}
RUNTIME_DIRECTORIES = (
    Path("assets/platform"),
    Path("copyright"),
    Path("platform"),
)
NO_ENHANCER_PATHS = {
    "provider-assessment-demo/professional-console.html",
}

HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.IGNORECASE)
BODY_OPEN_RE = re.compile(r"<body\b(?P<attrs>[^>]*)>", re.IGNORECASE)
CLASS_RE = re.compile(r"\bclass\s*=\s*([\"'])(?P<value>.*?)\1", re.IGNORECASE | re.DOTALL)
DATA_ATTR_RE_TEMPLATE = r"\s+{name}\s*=\s*([\"']).*?\1"
PLATFORM_SCRIPT_RE = re.compile(
    r"\s*<script\b[^>]*\bsrc\s*=\s*([\"'])[^\"']*assets/platform/platform-core\.js\?v=[^\"']*\1[^>]*>\s*</script>\s*",
    re.IGNORECASE,
)
PLATFORM_CSS_RE = re.compile(
    r"<link\b[^>]*\bhref\s*=\s*([\"'])[^\"']*assets/platform/platform-core\.css\?v=[^\"']*\1[^>]*>",
    re.IGNORECASE,
)


@dataclass
class Result:
    path: str
    status: str
    detail: str = ""


def copy_platform_runtime(root: Path) -> dict[str, object]:
    """Copy shell assets and public governance pages into generated artifacts."""

    repository_root = DEFAULT_ROOT.resolve()
    target_root = root.resolve()
    copied_files: list[str] = []

    if target_root == repository_root:
        return {
            "source": str(repository_root),
            "target": str(target_root),
            "copied": False,
            "files": copied_files,
        }

    for relative_directory in RUNTIME_DIRECTORIES:
        source_directory = repository_root / relative_directory
        if not source_directory.is_dir():
            raise SystemExit(f"Platform runtime source not found: {source_directory}")

        for source in sorted(source_directory.rglob("*")):
            if not source.is_file():
                continue
            relative_file = source.relative_to(repository_root)
            destination = target_root / relative_file
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.is_file() and destination.read_bytes() == source.read_bytes():
                continue
            shutil.copy2(source, destination)
            copied_files.append(relative_file.as_posix())

    return {
        "source": str(repository_root),
        "target": str(target_root),
        "copied": bool(copied_files),
        "files": copied_files,
    }


def production_html_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.html")):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        yield path


def relative_prefix(path: Path, root: Path) -> str:
    depth = len(path.relative_to(root).parent.parts)
    return "../" * depth


def enhancer_allowed(path: Path, root: Path) -> bool:
    return path.relative_to(root).as_posix() not in NO_ENHANCER_PATHS


def is_home_page(path: Path, root: Path) -> bool:
    return path.relative_to(root).as_posix() == "index.html"


def set_data_attribute(attrs: str, name: str, value: str) -> str:
    pattern = re.compile(DATA_ATTR_RE_TEMPLATE.format(name=re.escape(name)), re.IGNORECASE | re.DOTALL)
    replacement = f' {name}="{value}"'
    if pattern.search(attrs):
        return pattern.sub(replacement, attrs, count=1)
    return attrs + replacement


def remove_data_attribute(attrs: str, name: str) -> str:
    pattern = re.compile(DATA_ATTR_RE_TEMPLATE.format(name=re.escape(name)), re.IGNORECASE | re.DOTALL)
    return pattern.sub("", attrs)


def head_injection(path: Path, root: Path, source: str) -> str:
    prefix = relative_prefix(path, root)
    items = [MARKER]

    lowered = source.lower()
    if 'name="copyright"' not in lowered and "name='copyright'" not in lowered:
        items.append(
            '<meta name="copyright" content="© 2026 Khaled Altheeb — منصة الصحة النفسية وذوي الاحتياجات الخاصة">'
        )
    if 'name="rights"' not in lowered and "name='rights'" not in lowered:
        items.append('<meta name="rights" content="All rights reserved">')
    if 'rel="license"' not in lowered and "rel='license'" not in lowered:
        items.append(f'<link rel="license" href="{prefix}copyright/">')

    items.append(
        f'<link rel="stylesheet" href="{prefix}assets/platform/platform-core.css?v={SHELL_VERSION}">'
    )
    if enhancer_allowed(path, root):
        items.append(
            f'<script defer src="{prefix}assets/platform/platform-core.js?v={SHELL_VERSION}"></script>'
        )
    return "\n".join(items) + "\n"


def normalize_head_assets(source: str, path: Path, root: Path) -> str:
    """Keep asset versions and optional enhancer presence aligned with the page contract."""

    prefix = relative_prefix(path, root)
    css = f'<link rel="stylesheet" href="{prefix}assets/platform/platform-core.css?v={SHELL_VERSION}">'
    css_seen = False

    def replace_css(match: re.Match[str]) -> str:
        nonlocal css_seen
        if css_seen:
            return ""
        css_seen = True
        return css

    source = PLATFORM_CSS_RE.sub(replace_css, source)
    if not css_seen:
        source = HEAD_CLOSE_RE.sub(css + "\n</head>", source, count=1)

    script = f'<script defer src="{prefix}assets/platform/platform-core.js?v={SHELL_VERSION}"></script>'
    script_seen = False

    def replace_script(match: re.Match[str]) -> str:
        nonlocal script_seen
        if script_seen or not enhancer_allowed(path, root):
            return ""
        script_seen = True
        raw = match.group(0)
        leading = raw[: len(raw) - len(raw.lstrip())]
        trailing = raw[len(raw.rstrip()) :]
        return leading + script + trailing

    source = PLATFORM_SCRIPT_RE.sub(replace_script, source)
    if enhancer_allowed(path, root):
        if not script_seen:
            source = HEAD_CLOSE_RE.sub(script + "\n</head>", source, count=1)
    return source


def normalize_body(source: str, path: Path, root: Path) -> tuple[str, bool]:
    match = BODY_OPEN_RE.search(source)
    if not match:
        return source, False

    attrs = match.group("attrs")
    class_match = CLASS_RE.search(attrs)
    if class_match:
        classes = class_match.group("value").split()
        if "pt-platform" not in classes:
            classes.append("pt-platform")
        quote = class_match.group(1)
        replacement = f"class={quote}{' '.join(classes)}{quote}"
        attrs = attrs[: class_match.start()] + replacement + attrs[class_match.end() :]
    else:
        attrs = f'{attrs} class="pt-platform"'

    attrs = set_data_attribute(attrs, "data-pt-normalized", SHELL_VERSION)
    attrs = set_data_attribute(
        attrs,
        "data-pt-enhancer",
        "true" if enhancer_allowed(path, root) else "false",
    )
    if is_home_page(path, root):
        attrs = set_data_attribute(attrs, "data-pt-home", "true")
    else:
        attrs = remove_data_attribute(attrs, "data-pt-home")

    opening = f"<body{attrs}>"
    return source[: match.start()] + opening + source[match.end() :], True


def normalize_file(path: Path, root: Path, *, check_only: bool) -> Result:
    relative = path.relative_to(root).as_posix()
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Result(relative, "error", f"not UTF-8: {exc}")

    if MARKER in original:
        normalized, has_body = normalize_body(original, path, root)
        if not has_body:
            return Result(relative, "error", "missing <body>")
        normalized = normalize_head_assets(normalized, path, root)
        if normalized == original:
            return Result(relative, "current")
        if check_only:
            return Result(relative, "needs-update", "platform shell drift")
        path.write_text(normalized, encoding="utf-8", newline="\n")
        detail = "removed optional enhancer for strict application runtime" if not enhancer_allowed(path, root) else "updated stable platform shell"
        return Result(relative, "updated", detail)

    if not HEAD_CLOSE_RE.search(original):
        return Result(relative, "skipped", "missing </head>")

    normalized, has_body = normalize_body(original, path, root)
    if not has_body:
        return Result(relative, "skipped", "missing <body>")

    injection = head_injection(path, root, normalized)
    normalized = HEAD_CLOSE_RE.sub(injection + "</head>", normalized, count=1)
    normalized = normalize_head_assets(normalized, path, root)

    if check_only:
        return Result(relative, "needs-update")

    path.write_text(normalized, encoding="utf-8", newline="\n")
    return Result(relative, "updated")


def build_report(
    results: list[Result],
    *,
    root: Path,
    check_only: bool,
    runtime: dict[str, object],
) -> dict[str, object]:
    counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

    processed = sum(counts.get(name, 0) for name in ("current", "updated", "needs-update"))
    return {
        "schema_version": 1,
        "shell_version": SHELL_VERSION,
        "status": "passed" if counts.get("error", 0) == 0 else "failed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "check" if check_only else "write",
        "root": str(root),
        "runtime": runtime,
        "html_pages_seen": len(results),
        "html_pages_normalized_or_current": processed,
        "counts": counts,
        "results": [asdict(result) for result in results],
    }


def write_report(report: dict[str, object], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=DEFAULT_ROOT,
        type=Path,
        help="site root to normalize; defaults to the repository root",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report pages that need migration without modifying them",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="do not write a normalization report",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        help="custom report path; defaults to <root>/reports/platform-normalization.json",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR site root not found: {root}", file=sys.stderr)
        return 2

    runtime = copy_platform_runtime(root)
    results = [normalize_file(path, root, check_only=args.check) for path in production_html_files(root)]
    report = build_report(results, root=root, check_only=args.check, runtime=runtime)
    if not args.no_report:
        report_path = args.report_path or (root / "reports" / "platform-normalization.json")
        write_report(report, report_path.resolve())

    counts = report["counts"]
    print(json.dumps(counts, ensure_ascii=False, sort_keys=True))

    errors = [result for result in results if result.status == "error"]
    pending = [result for result in results if result.status == "needs-update"]
    if errors:
        for result in errors:
            print(f"ERROR {result.path}: {result.detail}", file=sys.stderr)
        return 2
    if args.check and pending:
        for result in pending[:50]:
            print(f"NEEDS_UPDATE {result.path}", file=sys.stderr)
        if len(pending) > 50:
            print(f"... and {len(pending) - 50} more", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
