#!/usr/bin/env python3
"""Apply one deterministic shared platform shell to production HTML pages.

The migration preserves page content and local navigation. It normalizes only
shared platform assets, rights metadata and body markers. The transformation is
idempotent by construction: existing platform asset tags are removed from the
head and one canonical set is inserted in a stable location.
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
SHELL_VERSION = "1.2.0"
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
    r"[ \t]*<script\b[^>]*\bsrc\s*=\s*([\"'])[^\"']*assets/platform/platform-core\.js\?v=[^\"']*\1[^>]*>\s*</script>[ \t]*(?:\r?\n)?",
    re.IGNORECASE,
)
PLATFORM_CSS_RE = re.compile(
    r"[ \t]*<link\b[^>]*\bhref\s*=\s*([\"'])[^\"']*assets/platform/platform-core\.css\?v=[^\"']*\1[^>]*>[ \t]*(?:\r?\n)?",
    re.IGNORECASE,
)
MARKER_RE = re.compile(r"[ \t]*<!--\s*pt-platform-shell:v1\s*-->[ \t]*(?:\r?\n)?", re.IGNORECASE)


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


def canonical_head_injection(path: Path, root: Path, head: str) -> str:
    prefix = relative_prefix(path, root)
    lowered = head.lower()
    items: list[str] = []

    # Rights metadata comes before the shell marker. Pages that receive these
    # tags for the first time therefore have the same ordering on every later
    # pass; their existing editorial metadata remains untouched.
    if 'name="copyright"' not in lowered and "name='copyright'" not in lowered:
        items.append('<meta name="copyright" content="© 2026 Khaled Altheeb — منصة روافد">')
    if 'name="rights"' not in lowered and "name='rights'" not in lowered:
        items.append('<meta name="rights" content="All rights reserved">')
    if 'rel="license"' not in lowered and "rel='license'" not in lowered:
        items.append(f'<link rel="license" href="{prefix}copyright/">')

    items.append(MARKER)
    items.append(
        f'<link rel="stylesheet" href="{prefix}assets/platform/platform-core.css?v={SHELL_VERSION}">'
    )
    if enhancer_allowed(path, root):
        items.append(
            f'<script defer src="{prefix}assets/platform/platform-core.js?v={SHELL_VERSION}"></script>'
        )
    return "\n".join(items)


def normalize_head(source: str, path: Path, root: Path) -> tuple[str, bool]:
    match = HEAD_CLOSE_RE.search(source)
    if not match:
        return source, False

    head = source[: match.start()]
    tail = source[match.end() :]

    # Remove every previous shared-shell marker/asset. This avoids duplicate
    # tags on pages that already carried platform assets before migration.
    head = MARKER_RE.sub("", head)
    head = PLATFORM_CSS_RE.sub("", head)
    head = PLATFORM_SCRIPT_RE.sub("", head)
    head = head.rstrip()

    injection = canonical_head_injection(path, root, head)
    normalized = f"{head}\n{injection}\n</head>{tail}"
    return normalized, True


def normalize_source(source: str, path: Path, root: Path) -> tuple[str, str | None]:
    normalized, has_body = normalize_body(source, path, root)
    if not has_body:
        return source, "missing <body>"

    normalized, has_head = normalize_head(normalized, path, root)
    if not has_head:
        return source, "missing </head>"
    return normalized, None


def normalize_file(path: Path, root: Path, *, check_only: bool) -> Result:
    relative = path.relative_to(root).as_posix()
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return Result(relative, "error", f"not UTF-8: {exc}")

    normalized, problem = normalize_source(original, path, root)
    if problem:
        # Historical fragments without a complete document shell remain
        # untouched and are reported rather than destructively rewritten.
        return Result(relative, "skipped", problem)

    if normalized == original:
        return Result(relative, "current")
    if check_only:
        return Result(relative, "needs-update", "platform shell drift")

    path.write_text(normalized, encoding="utf-8", newline="\n")
    detail = (
        "removed optional enhancer for strict application runtime"
        if not enhancer_allowed(path, root)
        else "updated stable platform shell"
    )
    return Result(relative, "updated", detail)


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
